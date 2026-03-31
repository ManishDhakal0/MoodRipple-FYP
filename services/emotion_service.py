# services/emotion_service.py
# Standalone emotion inference helper (load-once, process frames).
# Used by scripts; the app itself uses core/emotion_thread.py.

import cv2
import numpy as np
import json

from tensorflow.keras.models import load_model

MODEL_PATH       = "emotion_recognition_model_auto.h5"
CLASS_NAMES_PATH = "class_names.json"

_model        = None
_labels       = None
_face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def _load_once():
    global _model, _labels
    if _model is None:
        _model = load_model(MODEL_PATH)
        with open(CLASS_NAMES_PATH, "r") as f:
            _labels = json.load(f)


def process_frame(frame):
    """Detect emotion in a BGR frame. Returns (annotated_frame, emotion, confidence)."""
    _load_once()
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(gray, 1.3, 5)

    emotion, confidence = None, None
    for (x, y, w, h) in faces:
        face = gray[y:y+h, x:x+w]
        face = cv2.resize(face, (48, 48))
        face = face.reshape(1, 48, 48, 1) / 255.0
        preds      = _model.predict(face, verbose=0)
        idx        = int(np.argmax(preds))
        emotion    = _labels[idx]
        confidence = float(preds[0][idx] * 100)
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(frame, f"{emotion} ({confidence:.1f}%)",
                    (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        break
    return frame, emotion, confidence
