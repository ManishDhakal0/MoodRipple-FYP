# realtime_face_detection.py

import cv2
import numpy as np
from tensorflow.keras.models import load_model
import json
import os
import time
from collections import deque

# -----------------------
# Settings
# -----------------------
REACTION_INTERVAL_SEC = 30           # 30 seconds (better UX)
VOTE_WINDOW_SEC = 10                 # look at last 10 sec for stable emotion
EXPORT_PATH = "latest_emotion.json"
MIN_FACE_CONFIDENCE = 0.45           # Ignore weak predictions
MIN_STABLE_CONFIDENCE = 0.50         # Only export if stable emotion is confident

REACTION_MAP = {
    "angry":    "😠 Take a breath. Let's cool it down.",
    "disgust":  "🤢 Okay… let's switch the vibe.",
    "fear":     "😨 You seem tense. Let's go calmer.",
    "happy":    "😊 Nice! Keep the energy up.",
    "neutral":  "😐 Steady mood. Balanced vibe.",
    "sad":      "😢 It's okay. Let's lift things gently.",
    "surprise": "😮 Ooh! Something caught your attention."
}

# -----------------------
# 1. Load Model and Class Names
# -----------------------
print("Loading model...")

if os.path.exists('emotion_recognition_model_auto.h5'):
    model = load_model('emotion_recognition_model_auto.h5')
    print("✓ Loaded best model (emotion_recognition_model_auto.h5)")
elif os.path.exists('emotion_model_final.h5'):
    model = load_model('emotion_model_final.h5')
    print("✓ Loaded final model (emotion_model_final.h5)")
else:
    print("❌ No model found! Please train the model first.")
    exit()

# Load class names
if os.path.exists('class_names.json'):
    with open('class_names.json', 'r') as f:
        emotion_labels = json.load(f)
    print(f"✓ Loaded class names: {emotion_labels}")
else:
    emotion_labels = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
    print(f"⚠ Using default class names: {emotion_labels}")

# -----------------------
# 2. Load Face Detector
# -----------------------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

# -----------------------
# Helper: Export for Spotify module
# -----------------------
def export_latest_emotion(emotion: str, confidence: float):
    payload = {
        "emotion": emotion,
        "confidence": float(confidence),
        "timestamp_unix": int(time.time())
    }
    # atomic-ish write: write temp then replace
    tmp_path = EXPORT_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, EXPORT_PATH)

# -----------------------
# Helper: Weighted voting for stable emotion
# -----------------------
def decide_stable_emotion(pred_buffer, window_sec: int):
    """
    Weighted voting: emotions with higher confidence count more
    Returns (emotion, avg_confidence) or (None, None)
    """
    now = time.time()
    recent = [(e, c) for (ts, e, c) in pred_buffer if (now - ts) <= window_sec]

    if not recent:
        return None, None

    # Weighted voting: sum confidence for each emotion
    emotion_scores = {}
    emotion_counts = {}
    
    for emotion, conf in recent:
        emotion_scores[emotion] = emotion_scores.get(emotion, 0.0) + conf
        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
    
    if not emotion_scores:
        return None, None
    
    # Pick emotion with highest total confidence score
    best_emotion = max(emotion_scores, key=emotion_scores.get)
    
    # Calculate average confidence for this emotion
    avg_conf = emotion_scores[best_emotion] / emotion_counts[best_emotion]
    
    return best_emotion, avg_conf

# -----------------------
# 3. Start Webcam Detection
# -----------------------
cap = cv2.VideoCapture(0)

# Increase camera resolution for better face detection
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("\n" + "="*60)
print("REAL-TIME EMOTION DETECTION - MoodRipple")
print("="*60)
print("\nPress 'Q' to quit")
print("Press 'S' to save screenshot\n")

screenshot_count = 0

# store recent predictions for stable voting
# (ts, emotion, confidence)
pred_buffer = deque(maxlen=5000)

last_reaction_time = 0.0
last_exported_emotion = None  # Track last exported to avoid duplicates
last_reaction_text = ""
last_reaction_overlay_until = 0.0

# FPS calculation
fps_start_time = time.time()
fps_frame_count = 0
current_fps = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to grab frame")
        break

    # FPS calculation
    fps_frame_count += 1
    if time.time() - fps_start_time >= 1.0:
        current_fps = fps_frame_count
        fps_frame_count = 0
        fps_start_time = time.time()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Improved face detection parameters
    faces = face_cascade.detectMultiScale(
        gray, 
        scaleFactor=1.1,
        minNeighbors=7,
        minSize=(30, 30),
        flags=cv2.CASCADE_SCALE_IMAGE
    )

    # Track best face in frame (highest confidence)
    best_emotion = None
    best_conf = -1.0
    best_box = None
    best_pred = None

    for (x, y, w, h) in faces:
        face_roi = gray[y:y+h, x:x+w]
        face_roi = cv2.resize(face_roi, (48, 48))
        face_roi = face_roi.reshape(1, 48, 48, 1) / 255.0

        prediction = model.predict(face_roi, verbose=0)
        emotion_idx = int(np.argmax(prediction))
        emotion = emotion_labels[emotion_idx]
        confidence = float(prediction[0][emotion_idx])

        if confidence > best_conf:
            best_conf = confidence
            best_emotion = emotion
            best_box = (x, y, w, h)
            best_pred = prediction[0]

    # If we found a face with good confidence, draw + buffer prediction
    if best_box is not None and best_conf >= MIN_FACE_CONFIDENCE:
        x, y, w, h = best_box

        # buffer it for stable decision
        pred_buffer.append((time.time(), best_emotion, best_conf))

        # draw rectangle
        conf_pct = best_conf * 100
        color = (0, 255, 0) if conf_pct > 60 else (0, 165, 255)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

        label = f"{best_emotion} ({conf_pct:.1f}%)"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(frame, (x, y - 35), (x + label_size[0], y), color, -1)
        cv2.putText(frame, label, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # show top 3 probabilities only (cleaner UI)
        top_3_idx = np.argsort(best_pred)[-3:][::-1]
        y_offset = y + h + 25
        for i in top_3_idx:
            emotion_text = f"{emotion_labels[i]}: {best_pred[i]*100:.1f}%"
            cv2.putText(frame, emotion_text, (x, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 20

    # -----------------------
    # 4. Export emotion every 30 seconds (or when emotion changes)
    # -----------------------
    now = time.time()
    if (now - last_reaction_time) >= REACTION_INTERVAL_SEC:
        chosen_emotion, chosen_conf = decide_stable_emotion(pred_buffer, VOTE_WINDOW_SEC)

        # Only export if confident enough AND different from last
        if (chosen_emotion is not None and 
            chosen_conf >= MIN_STABLE_CONFIDENCE):
            
            last_reaction_time = now

            # export emotion for Spotify controller module
            export_latest_emotion(chosen_emotion, chosen_conf)
            last_exported_emotion = chosen_emotion

            # print one reaction
            reaction = REACTION_MAP.get(chosen_emotion, f"Detected: {chosen_emotion}")
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
            print(f"\n[{timestamp_str}] ✅ MoodRipple Reaction: {reaction}")
            print(f"   -> Exported to {EXPORT_PATH}: emotion={chosen_emotion}, confidence={chosen_conf*100:.1f}%")

            # show big overlay for 3 seconds
            last_reaction_text = reaction
            last_reaction_overlay_until = now + 3

    # overlay reaction briefly after triggering
    if time.time() <= last_reaction_overlay_until and last_reaction_text:
        # Semi-transparent background for overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (frame.shape[1] - 10, 70), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        cv2.putText(frame, last_reaction_text, (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

    # Show FPS counter
    cv2.putText(frame, f"FPS: {current_fps}", (frame.shape[1] - 100, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Show frame
    cv2.imshow('MoodRipple - Real-time Emotion Detection', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        print("\n👋 Stopping detection...")
        break
    elif key == ord('s'):
        screenshot_count += 1
        filename = f'screenshot_{screenshot_count}.png'
        cv2.imwrite(filename, frame)
        print(f"📸 Screenshot saved: {filename}")

cap.release()
cv2.destroyAllWindows()
print("✓ Detection stopped.\n")