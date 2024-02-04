import cv2 as cv
import mediapipe as mp
import numpy as np
import tensorflow as tf
import json
import matplotlib.pyplot as plt

txt_data = []
output_data = []
pr = None

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
    if printInfo: 
        print(f"Joint angles for frame {frame_number}:")

    for frameAngle in frameAngles:
        if printInfo: 
            print(f"{frameAngle}: {frameAngles[frameAngle]}")
        txt_data.append([frame_number, frameAngle, frameAngles[frameAngle]])
    if printInfo: 
        print("\n")

    return txt_data

def clean_data(txt_data, exerciseJoints, target, decimals, printInfo=True):
    joints = {}

    for e in exerciseJoints: 
        joints[e] = []
    for d in txt_data: 
        joints[d[1]].append(d[2])

    curSize = len(joints[exerciseJoints[0]])
    interval = (curSize-1)/target
    
    new_txt = []

    for n in range(target):
        for j in joints:
            ei = interval*n
            if printInfo:
                print(f'interval = {interval} \n\n n = {n} \n\n')
                print(f'v1 = {int(ei)} \n\n v2 = {int(ei)+1} \n\n')
                print(f'length of joints[j] = {len(joints[j])}')

            v1 = joints[j][int(ei)]
            v2 = joints[j][int(ei)+1]

            estVal = (v2-v1)*(ei%1)+v1
            new_txt.append([n, j, round(estVal,decimals)])
    if printInfo:
        print(f"Cleaned data: {new_txt}\n\n\n")
    return new_txt

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

def get_prediction(x_input, exercise, printInfo):
    pred = tf.constant([x_input])
    model = tf.keras.models.load_model(f'models/{exercise}.h5')
    if printInfo:
        print(model.summary())
    model_pred = model.predict(pred)
    return model_pred[0][0]

def send_prediction():
    global pr 
    return pr


def generate_frames(data):
    mp_drawing = mp.solutions.drawing_utils
    mp_pose = mp.solutions.pose

    f = open('static/data_info.json')
    dataOptions = json.load(f)
    joints = dataOptions["joints"]
    metadata = dataOptions["metadata"]
    f.close()

    global txt_data

    if 'exercise' in data:
        angles = dataOptions['exercises'][data['exercise']]['joints']
        frames = dataOptions['exercises'][data['exercise']]['frames']
        decimals = dataOptions['decimals']

    woActive = False
    if 'workout' in data:
        if data['workout']:
            woActive = True
        else:
            clean_txt_data = clean_data(txt_data, angles, frames, decimals, False)
            # plot_data(clean_txt_data, angles)
            input_data = [data[x] for x in metadata['x']] + [dp[2] for dp in clean_txt_data]
            pred = get_prediction(input_data, data['exercise'], False)
                
            global pr
            pr = pred

            txt_data = []


    cap = cv.VideoCapture(0)
    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    frame_number = 0
    while True:
        ret, frame = cap.read()

        if not ret:
            break

        image = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        image.flags.writeable = False

        results = pose.process(image)
            
        image.flags.writeable = True
        image = cv.cvtColor(image, cv.COLOR_RGB2BGR)

        lms = results.pose_landmarks

        if woActive:
            frameAngles = {}
            for angle in angles: 
                frameAngles[angle] = find_angle(*[lms.landmark[i] for i in joints[angle]])
            txt_data = append_angles(frameAngles, frame_number, txt_data, printInfo=False)
            frame_number += 1

        mp_drawing.draw_landmarks(image, lms, mp_pose.POSE_CONNECTIONS)

        ret, buffer = cv.imencode('.jpg', image)
        image = buffer.tobytes()

        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + image + b'\r\n')