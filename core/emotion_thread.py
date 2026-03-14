# core/emotion_thread.py
# Background thread: webcam capture + CNN emotion detection

import os
import json
import time
from collections import deque

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from core.constants import (
    MODEL_PATH, MODEL_FALLBACK, CLASS_NAMES_PATH, DEFAULT_LABELS,
    EMOTION_FILE, EXPORT_INTERVAL_SEC, VOTE_WINDOW_SEC,
    MIN_FACE_CONFIDENCE, MIN_STABLE_CONFIDENCE, EMOTION_GROUPS,
    EMOTION_TO_MOOD,
)


class EmotionDetectionThread(QThread):
    frame_ready    = pyqtSignal(np.ndarray)           # BGR frame for display
    emotion_ready  = pyqtSignal(str, float, str)      # emotion, confidence, mood
    scores_ready   = pyqtSignal(dict)                 # mood → normalised score (per-frame)
    status_changed = pyqtSignal(str, str)             # message, colour_hex

    def __init__(self):
        super().__init__()
        self.is_running   = False
        self.cap          = None
        self.model        = None
        self.face_cascade = None
        self.labels       = []
        self.pred_buffer  = deque(maxlen=5000)
        self.last_export  = 0.0

    # ── Load model (call before start()) ──────────────────────
    def load_model(self) -> bool:
        try:
            import tensorflow as tf

            path = MODEL_PATH if os.path.exists(MODEL_PATH) else (
                   MODEL_FALLBACK if os.path.exists(MODEL_FALLBACK) else None)
            if path is None:
                self.status_changed.emit("❌ No model file found (.h5).", "#e05555")
                return False

            self.status_changed.emit(f"Loading model…", "#9da8b4")
            self.model = tf.keras.models.load_model(path)
            self.status_changed.emit(f"✅ Model loaded.", "#1DB954")

            if os.path.exists(CLASS_NAMES_PATH):
                with open(CLASS_NAMES_PATH, "r", encoding="utf-8") as f:
                    self.labels = json.load(f)
            else:
                self.labels = DEFAULT_LABELS

            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            if self.face_cascade.empty():
                self.status_changed.emit("❌ Haar cascade failed to load.", "#e05555")
                return False

            return True
        except Exception as e:
            self.status_changed.emit(f"❌ {e}", "#e05555")
            return False

    # ── Thread body ───────────────────────────────────────────
    def run(self):
        if self.model is None or self.face_cascade is None:
            self.status_changed.emit("❌ Model not loaded.", "#e05555")
            return

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not self.cap.isOpened():
            self.status_changed.emit("❌ Cannot open camera.", "#e05555")
            return

        self.status_changed.emit("✅ Camera started.", "#1DB954")

        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=7, minSize=(30, 30)
            )

            best_emotion, best_conf, best_box = None, -1.0, None
            best_scores: dict = {}

            for (x, y, w, h) in faces:
                roi = gray[y:y+h, x:x+w]
                if roi.size == 0:
                    continue
                roi = cv2.equalizeHist(roi)
                roi = cv2.resize(roi, (48, 48))
                roi = roi.reshape(1, 48, 48, 1).astype(np.float32) / 255.0

                pred                   = self.model.predict(roi, verbose=0)
                emotion, conf, scores  = self._collapse(pred)

                if conf > best_conf:
                    best_conf, best_emotion, best_box = conf, emotion, (x, y, w, h)
                    best_scores = scores

            if best_box is not None and best_conf >= MIN_FACE_CONFIDENCE:
                x, y, w, h = best_box
                self.pred_buffer.append((time.time(), best_emotion, best_conf))
                if best_scores:
                    self.scores_ready.emit(best_scores)

                pct   = best_conf * 100
                color = (0, 210, 90) if pct > 60 else (0, 165, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)
                cv2.putText(frame, f"{best_emotion} ({pct:.0f}%)",
                            (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2)

            now = time.time()
            if (now - self.last_export) >= EXPORT_INTERVAL_SEC:
                emo, conf = self._stable_emotion()
                if emo and conf >= MIN_STABLE_CONFIDENCE:
                    self.last_export = now
                    self._export(emo, conf)

            self.frame_ready.emit(frame)
            time.sleep(0.03)

        if self.cap:
            self.cap.release()
        self.status_changed.emit("⏹ Camera stopped.", "#9da8b4")

    def stop(self):
        self.is_running = False
        self.wait()

    # ── Helpers ───────────────────────────────────────────────
    def _collapse(self, prediction):
        """Map 7-class CNN output → 3 mood-aligned classes using EMOTION_GROUPS."""
        raw    = prediction[0]
        scores = {}
        for target, sources in EMOTION_GROUPS.items():
            scores[target] = sum(
                float(raw[self.labels.index(src)]) * w
                for src, w in sources.items()
                if src in self.labels
            )
        best  = max(scores, key=scores.get)
        total = sum(scores.values()) or 1.0
        norm  = {k: v / total for k, v in scores.items()}
        return best, scores[best], norm

    def _stable_emotion(self):
        now    = time.time()
        recent = [(e, c) for ts, e, c in self.pred_buffer
                  if (now - ts) <= VOTE_WINDOW_SEC]
        if not recent:
            return None, None
        totals = {}
        counts = {}
        for e, c in recent:
            totals[e] = totals.get(e, 0.0) + c
            counts[e] = counts.get(e, 0)   + 1
        best = max(totals, key=totals.get)
        return best, totals[best] / counts[best]

    def _export(self, emotion: str, confidence: float):
        mood    = EMOTION_TO_MOOD.get(emotion, "focused")
        payload = {
            "emotion":        emotion,
            "confidence":     float(confidence),
            "timestamp_unix": int(time.time()),
        }
        tmp = EMOTION_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, EMOTION_FILE)
        self.emotion_ready.emit(emotion, confidence, mood)
