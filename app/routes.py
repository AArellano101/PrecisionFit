import os
from flask import Flask, render_template, Response, request, jsonify
from webcam import generate_frames, send_prediction

app = Flask(__name__)

app_info = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/workout")
def workout():
    return render_template("workout.html")

@app.route('/video', methods=["GET"])
def get_video():
    print('Turning on webcam.')
    return Response(generate_frames(app_info), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get-model-response', methods=["GET"])
def get_model_response():
    return jsonify({"response": str(send_prediction())})

@app.route('/video', methods=["POST"])
def set_video():
    data = request.json
    method = data.get("method")
    try:
        if method == "start-workout":
            app_info['workout'] = True
            app_info['exercise'] = data.get("exercise")
        elif method == "end-workout":
            app_info['workout'] = False
    except Exception as e:
        return jsonify({"message": e})
    return jsonify({"message": f"Changed method to {method}."})

if __name__ == "__main__":
    app.run(debug=True)