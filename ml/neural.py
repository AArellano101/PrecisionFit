import pandas as pd
import numpy as np
import csv
import pyrebase
import json
import os
import tensorflow as tf
from copy import deepcopy
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

EPOCHS = 500

fbc = open('src/info/firebase_config.json')
firebaseConfig = json.load(fbc)
fbc.close()

f = open('src/info/data_creation_options.json')
d = json.load(f)
exerciseNames = list(d['exercises'].keys())
exercises = d['exercises']
metadata = d['metadata']
f.close()

# intialize firebase storage and rt db
firebase_app = pyrebase.initialize_app(firebaseConfig)


def main():
    # get what exercise 
    exercise = ""
    while exercise not in exerciseNames:
        exercise = input("Enter valid: ")

    storage = firebase_app.storage()

    data = storage.bucket.list_blobs(prefix=f"txt-files/{exercise}")
    inputNodes = 0

    print('Writing header...')
    with open(f'src/temp-storage/{exercise}.csv', 'w') as c:
        w = csv.writer(c)

        header = deepcopy(metadata['x'])
        x_nodes = (exercises[exercise]['frames']) * len(exercises[exercise]['joints'])

        for i in range(x_nodes):
            header.append(str(i))

        inputNodes = len(header)
        header.append(metadata['y'])

        w.writerow(header)

    for file in data:
        if file.name != f"txt-files/{exercise}/":
            fName = file.name.split('/')[-1]

            print(f'Writing data for file: {fName} ...')

            storage = firebase_app.storage()
            storage.download(file.name, os.path.abspath(f"src/temp-storage/{fName}.txt"))

            with open(f"src/temp-storage/{fName}.txt", "r") as f:
                csv_line = []

                keys = f.readline()[:-1].split(',')
                vals = f.readline()[:-1].split(',')

                ms = metadata['x']
                for x in ms:
                    ix = keys.index(str(x))
                    csv_line.append(vals[ix])

                csv_line += f.readline().split(',')

                csv_line.append(vals[keys.index(metadata['y'])])

            with open(f'src/temp-storage/{exercise}.csv', 'a') as c:
                w = csv.writer(c)
                w.writerow(csv_line)    

            os.remove(f"src/temp-storage/{fName}.txt")

    while True:
        if input('Start ML training? ') == 'yes':
            break

    ds = pd.read_csv(f'src/temp-storage/{exercise}.csv')

    dsx = ds.iloc[:, :-1].values
    dsy = ds.iloc[:, -1].values

    X_train, X_test, Y_train, Y_test = train_test_split(dsx, dsy, test_size=0.2, random_state=42)

    X_train = tf.constant(X_train, dtype=tf.float16)
    Y_train = tf.constant(Y_train, dtype=tf.float16)
    X_test = tf.constant(X_test, dtype=tf.float16)
    Y_test = tf.constant(Y_test, dtype=tf.float16)

    model = tf.keras.Sequential()

    model.add(tf.keras.layers.Dense(10, input_dim=inputNodes, activation='relu'))
    model.add(tf.keras.layers.Dense(1, activation='linear' ))

    model.compile(loss='mean_squared_error', optimizer='adam', metrics=['mean_squared_error'])

    model.fit(X_train, Y_train, epochs=EPOCHS, verbose=1)

    test_loss = model.evaluate(X_test, Y_test)
    print(f"Test Mean Squared Error: {test_loss[1]}")

    model.save(f"../app/models/{exercise}.h5")

if __name__ == '__main__':
    main()