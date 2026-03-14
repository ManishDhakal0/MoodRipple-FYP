# emotion_service.py
import cv2
import numpy as np
import json
import os
from tensorflow.keras.models import load_model

MODEL_PATH = "emotion_recognition_model_auto.h5"
CLASS_NAMES_PATH = "class_names.json"

model = None
labels = None
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def load_once():
    global model, labels
    if model is None:
        model = load_model(MODEL_PATH)
        with open(CLASS_NAMES_PATH, "r") as f:
            labels = json.load(f)

def process_frame(frame):
    load_once()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    emotion, confidence = None, None

    for (x, y, w, h) in faces:
        face = gray[y:y+h, x:x+w]
        face = cv2.resize(face, (48, 48))
        face = face.reshape(1, 48, 48, 1) / 255.0

        preds = model.predict(face, verbose=0)
        idx = np.argmax(preds)
        emotion = labels[idx]
        confidence = float(preds[0][idx] * 100)

        cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)
        cv2.putText(
            frame,
            f"{emotion} ({confidence:.1f}%)",
            (x, y-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0,255,0),
            2
        )
        break

    return frame, emotion, confidence
