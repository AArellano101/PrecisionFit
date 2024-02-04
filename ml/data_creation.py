import cv2 as cv
import mediapipe as mp
import numpy as np
import pyrebase
import os
import json
import matplotlib.pyplot as plt

def find_angle(a,b,c):
    a = (a.x, a.y)
    b = (b.x, b.y) 
    c = (c.x, c.y) 
    
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    
    if angle >180.0:
        angle = 360-angle
        
    return angle

def append_angles(frameAngles, frame_number, txt_data, printInfo=True):
    if printInfo: print(f"Joint angles for frame {frame_number}:")

    for frameAngle in frameAngles:
        if printInfo: print(f"{frameAngle}: {frameAngles[frameAngle]}")
        txt_data.append([frame_number, frameAngle, frameAngles[frameAngle]])
    if printInfo: print("\n")

def plot_data(data, exerciseJoints):
    xpoints = np.array(list(range(data[-1][0]+1)))
    ypoints = {}

    for e in exerciseJoints: ypoints[e] = np.array([])
    for d in data: ypoints[d[1]] = np.append(ypoints[d[1]], np.array([d[2]]))

    ng = len(exerciseJoints)
    figure, axis = plt.subplots(ng) 

    cr = 0
    for e in exerciseJoints:
        axis[cr].scatter(xpoints, ypoints[e])
        axis[cr].set_title(e)

        cr += 1 

    plt.show() 

def clean_data(txt_data, exerciseJoints, target, decimals):
    joints = {}

    for e in exerciseJoints: joints[e] = []
    for d in txt_data: joints[d[1]].append(d[2])

    curSize = len(joints[exerciseJoints[0]])
    interval = (curSize-1)/target
    
    new_txt = []

    for n in range(target):
        for j in joints:
            ei = interval*n
            
            v1 = joints[j][int(ei)]
            v2 = joints[j][int(ei)+1]

            # print(v1, v2, joints)
                
            estVal = (v2-v1)*(ei%1)+v1
            new_txt.append([n, j, round(estVal,decimals)])

    return new_txt

fbc = open('src/info/firebase_config.json')
firebaseConfig = json.load(fbc)
fbc.close()

# intialize firebase storage and rt db
firebase_app = pyrebase.initialize_app(firebaseConfig)
storage = firebase_app.storage()
db = firebase_app.database()

# mediapipe tools
mp_pose = mp.solutions.pose

# get pose landmarks filters
f = open('src/info/data_creation_options.json')
dataOptions = json.load(f)
exercises = list(dataOptions["exercises"].keys())
joints = dataOptions["joints"]
f.close()

def main():
    # get what exercise to create data for
    print("This is the data creation file.\n Options: pushup")
    exercise = ""
    while exercise not in exercises:
        exercise = input("Enter valid: ")

    # readable landmarks available here:
    # https://developers.google.com/static/mediapipe/images/solutions/pose_landmarks_index.png
    angles = dataOptions['exercises'][exercise]['joints']
    frames = dataOptions['exercises'][exercise]['frames']
    decimals = dataOptions['decimals']

    storage = firebase_app.storage()
    data = storage.bucket.list_blobs(prefix=f"videos/{exercise}")

    for file in data:
        if file.name != f"videos/{exercise}/":
            # get file metadata (gender, height, weight, etc.) from rt db
            filename = file.name.split('/')[-1].replace('.mp4', '')
            md = db.child(f"video-metadata/{exercise}/{filename}").get()
            mdps = md.each()
            metadata = { mdp.key() : mdp.val() for mdp in mdps}

            print(file.name + '\n\n')
            # download file into temp.mp4
            storage.download(file.name, os.path.abspath("src/temp/temp.mp4"))
            cap = cv.VideoCapture('src/temp/temp.mp4')
                
            # pose instance
            pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

            frame_number = 0
            txt_data = []

            while True:
                ret, frame = cap.read()

                if not ret:
                    break

                image = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
                image.flags.writeable = False

                results = pose.process(image)

                lms = results.pose_landmarks
                print(lms)

                frameAngles = {}
                for angle in angles: 
                    frameAngles[angle] = find_angle(*[lms.landmark[i] for i in joints[angle]])

                append_angles(frameAngles, frame_number, txt_data, printInfo=False)
                frame_number += 1

            clean_txt_data = clean_data(txt_data, angles, frames, decimals)
            # plot_data(clean_txt_data, dataOptions['exercises'][exercise]['joints'])

            # make sure output value is at the end
            gForm = metadata['goodForm']
            del metadata['goodForm']
            metadata['goodForm'] = gForm

            with open("src/temp/temp.txt", 'w', newline='') as f:
                f.write(','.join(list(metadata.keys())))
                f.write('\n')
                f.write(','.join(map(str, list(metadata.values()))))
                f.write('\n')
                f.write(','.join(str(dp[2]) for dp in clean_txt_data))

            storage.child(f'txt-files/{exercise}/{filename}').put('src/temp/temp.txt')

            os.remove("src/temp/temp.txt")

            # have to reinitialize storage every iteration due to flaw in pyrebase
            storage = firebase_app.storage()

    cap.release()

if __name__ == '__main__':
    main()