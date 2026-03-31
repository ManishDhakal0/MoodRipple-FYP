# core/emotion_thread.py
# Background thread: webcam capture + CNN emotion detection

import os
import sys
import json
import time
import traceback
from collections import deque

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from core.constants import (
    MODEL_PATH,
    MODEL_FALLBACK,
    CLASS_NAMES_PATH,
    DEFAULT_LABELS,
    EMOTION_FILE,
    EXPORT_INTERVAL_SEC,
    VOTE_WINDOW_SEC,
    MIN_FACE_CONFIDENCE,
    MIN_STABLE_CONFIDENCE,
    EMOTION_GROUPS,
    EMOTION_TO_MOOD,
)


def _log(msg: str):
    """Print to terminal with flush so it shows immediately in PowerShell."""
    print(f"[EmotionThread] {msg}", flush=True)


class EmotionDetectionThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)  # BGR frame for display
    emotion_ready = pyqtSignal(str, float, str)  # emotion, confidence, mood
    scores_ready = pyqtSignal(dict)  # mood → normalised score (per-frame)
    drowsy_ready = pyqtSignal(dict)  # drowsiness metrics dict
    status_changed = pyqtSignal(str, str)  # message, colour_hex

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.cap = None
        self.model = None
        self.face_cascade = None
        self.labels = []
        self.pred_buffer = deque(maxlen=5000)
        self.last_export = 0.0
        # Throttle counters — keep signal rate manageable
        self._frame_skip = 0  # emit frame_ready every 2nd frame → ~15 fps
        self._scores_skip = 0  # emit scores_ready only on change OR every 10 frames
        self._last_scores: dict = {}  # last emitted score values for change detection
        self._drowsy_skip = 0  # emit drowsy_ready every 5 frames or on change
        self._last_drowsy: bool = False
        self._infer_skip = 0  # run CNN only every 2nd frame
        self._last_best_emotion = None
        self._last_best_conf = -1.0
        self._last_best_box = None
        self._last_best_scores: dict = {}

        # Drowsiness detector (uses MediaPipe — graceful no-op if not installed)
        from core.drowsiness_detector import DrowsinessDetector

        self._drowsiness = DrowsinessDetector()
        if self._drowsiness.available:
            _log("MediaPipe Face Mesh loaded — drowsiness detection active.")
        else:
            _log(
                "mediapipe not installed — drowsiness detection disabled. Run: pip install mediapipe"
            )

    # ── Load model ────────────────────────────────────────────
    def load_model(self) -> bool:
        try:
            import tensorflow as tf

            _log(f"TensorFlow version: {tf.__version__}")

            path = (
                MODEL_PATH
                if os.path.exists(MODEL_PATH)
                else (MODEL_FALLBACK if os.path.exists(MODEL_FALLBACK) else None)
            )

            _log(f"Model path: {MODEL_PATH!r}  exists={os.path.exists(MODEL_PATH)}")
            _log(f"Working dir: {os.getcwd()!r}")

            if path is None:
                msg = "❌ No model file found (.h5)."
                _log(msg)
                self.status_changed.emit(msg, "#e05555")
                return False

            _log(f"Loading model from: {path!r} ...")
            self.status_changed.emit("Loading model…", "#9da8b4")
            self.model = tf.keras.models.load_model(path, compile=False)
            _log(f"Model loaded OK — input shape: {self.model.input_shape}")
            self.status_changed.emit("✅ Model loaded.", "#1DB954")

            if os.path.exists(CLASS_NAMES_PATH):
                with open(CLASS_NAMES_PATH, "r", encoding="utf-8") as f:
                    self.labels = json.load(f)
                _log(f"Labels loaded: {self.labels}")
            else:
                self.labels = DEFAULT_LABELS
                _log(f"class_names.json not found, using defaults: {self.labels}")

            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            _log(f"Cascade path: {cascade_path!r}")
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                msg = "❌ Haar cascade failed to load."
                _log(msg)
                self.status_changed.emit(msg, "#e05555")
                return False

            _log("Haar cascade loaded OK.")
            return True

        except Exception as e:
            msg = f"❌ Model load error: {e}"
            _log(msg)
            _log(traceback.format_exc())
            self.status_changed.emit(msg, "#e05555")
            return False

    # ── Thread body ───────────────────────────────────────────
    def run(self):
        _log("Thread started.")
        try:
            # Load model inside the thread so TF init stays off the GUI thread
            if self.model is None or self.face_cascade is None:
                if not self.load_model():
                    _log("load_model() failed — thread exiting.")
                    return

            _log("Opening camera (index 0)...")
            self.cap = cv2.VideoCapture(1)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            opened = self.cap.isOpened()
            _log(f"Camera opened: {opened}")

            if not opened:
                # Try index 1 as fallback
                _log("Camera index 0 failed, trying index 1...")
                self.cap.release()
                self.cap = cv2.VideoCapture(1)
                opened = self.cap.isOpened()
                _log(f"Camera index 1 opened: {opened}")

            if not opened:
                msg = "❌ Cannot open camera. Check it is connected and not used by another app."
                _log(msg)
                self.status_changed.emit(msg, "#e05555")
                return

            self.status_changed.emit("✅ Camera started.", "#1DB954")
            _log("Camera loop starting.")

            self._drowsiness.reset_session()

            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    continue

                # Convert once: BGR→RGB, then derive gray from RGB (avoids 2 full conversions)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)

                # ── Drowsiness detection (MediaPipe, RGB) ──────────────────
                drowsy_data = {}
                if self._drowsiness.available:
                    drowsy_data = self._drowsiness.process_frame(frame_rgb)
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=7, minSize=(30, 30)
                )

                self._infer_skip += 1
                if self._infer_skip % 2 == 0 and len(faces):
                    best_emotion, best_conf, best_box = None, -1.0, None
                    best_scores: dict = {}

                    for x, y, w, h in faces:
                        roi = gray[y : y + h, x : x + w]
                        if roi.size == 0:
                            continue
                        roi = cv2.equalizeHist(roi)
                        roi = cv2.resize(roi, (48, 48))
                        roi = roi.reshape(1, 48, 48, 1).astype(np.float32) / 255.0

                        pred = self.model.predict(roi, verbose=0)
                        emotion, conf, scores = self._collapse(pred)

                        if conf > best_conf:
                            best_conf, best_emotion, best_box = (
                                conf,
                                emotion,
                                (x, y, w, h),
                            )
                            best_scores = scores

                    # Cache result for skipped frames
                    self._last_best_emotion = best_emotion
                    self._last_best_conf = best_conf
                    self._last_best_box = best_box
                    self._last_best_scores = best_scores
                else:
                    # Reuse cached result
                    best_emotion = self._last_best_emotion
                    best_conf = self._last_best_conf
                    best_box = self._last_best_box
                    best_scores = self._last_best_scores

                if best_box is not None and best_conf >= MIN_FACE_CONFIDENCE:
                    x, y, w, h = best_box
                    self.pred_buffer.append((time.time(), best_emotion, best_conf))

                    pct = best_conf * 100
                    color = (0, 210, 90) if pct > 60 else (0, 165, 255)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)
                    cv2.putText(
                        frame,
                        f"{best_emotion} ({pct:.0f}%)",
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.85,
                        color,
                        2,
                    )

                # ── Drowsiness overlay — status badge only (no debug numbers) ─
                if drowsy_data.get("face_detected"):
                    is_d   = drowsy_data.get("is_drowsy",    False)
                    is_y   = drowsy_data.get("is_yawning",   False)
                    is_nod = drowsy_data.get("head_drooping", False)

                    if is_d:
                        badge_txt = "DROWSY"
                        drw_color = (0, 60, 255)
                    elif is_y:
                        badge_txt = "YAWNING"
                        drw_color = (0, 165, 255)
                    elif is_nod:
                        badge_txt = "HEAD NOD"
                        drw_color = (0, 200, 200)
                    else:
                        badge_txt = None
                        drw_color = (120, 200, 120)

                    if badge_txt:
                        h_frame = frame.shape[0]
                        cv2.putText(
                            frame, badge_txt,
                            (10, h_frame - 12),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, drw_color, 2,
                        )

                now = time.time()
                if (now - self.last_export) >= EXPORT_INTERVAL_SEC:
                    emo, conf = self._stable_emotion()
                    if emo and conf >= MIN_STABLE_CONFIDENCE:
                        self.last_export = now
                        self._export(emo, conf)

                # ── Frame throttle: ~15 fps (every 2nd frame) ─────────────
                self._frame_skip += 1
                if self._frame_skip % 2 == 0:
                    self.frame_ready.emit(frame)

                # ── Scores throttle: emit on significant change OR ~3 fps ─
                if best_scores:
                    self._scores_skip += 1
                    changed = any(
                        abs(best_scores.get(k, 0.0) - self._last_scores.get(k, 0.0))
                        > 0.04
                        for k in best_scores
                    )
                    if changed or self._scores_skip >= 10:
                        self.scores_ready.emit(best_scores)
                        self._last_scores = dict(best_scores)
                        self._scores_skip = 0

                # ── Drowsy throttle: emit on change OR every 5 frames ─────
                if drowsy_data.get("available") and drowsy_data.get("face_detected"):
                    self._drowsy_skip += 1
                    drowsy_changed = drowsy_data.get("is_drowsy") != self._last_drowsy
                    if drowsy_changed or self._drowsy_skip >= 5:
                        self.drowsy_ready.emit(drowsy_data)
                        self._last_drowsy = bool(drowsy_data.get("is_drowsy"))
                        self._drowsy_skip = 0

                time.sleep(0.03)

        except Exception as e:
            msg = f"❌ Detection error: {e}"
            _log(msg)
            _log(traceback.format_exc())
            self.status_changed.emit(msg, "#e05555")

        finally:
            if self.cap:
                self.cap.release()
                _log("Camera released.")
            self._drowsiness.close()
            self.status_changed.emit("⏹ Camera stopped.", "#9da8b4")
            _log("Thread finished.")

    def stop(self):
        self.is_running = False
        self.wait()

    # ── Helpers ───────────────────────────────────────────────
    def _collapse(self, prediction):
        raw = prediction[0]
        scores = {}
        for target, sources in EMOTION_GROUPS.items():
            scores[target] = sum(
                float(raw[self.labels.index(src)]) * w
                for src, w in sources.items()
                if src in self.labels
            )
        best = max(scores, key=scores.get)
        total = sum(scores.values()) or 1.0
        norm = {k: v / total for k, v in scores.items()}
        return best, scores[best], norm

    def _stable_emotion(self):
        now = time.time()
        recent = [
            (e, c) for ts, e, c in self.pred_buffer if (now - ts) <= VOTE_WINDOW_SEC
        ]
        if not recent:
            return None, None
        totals = {}
        counts = {}
        for e, c in recent:
            totals[e] = totals.get(e, 0.0) + c
            counts[e] = counts.get(e, 0) + 1
        best = max(totals, key=totals.get)
        return best, totals[best] / counts[best]

    def _export(self, emotion: str, confidence: float):
        # Drowsiness overrides mood to "drowsy" so auto-play picks energizing music
        mood = (
            "drowsy" if self._last_drowsy else EMOTION_TO_MOOD.get(emotion, "focused")
        )
        payload = {
            "emotion": emotion,
            "confidence": float(confidence),
            "timestamp_unix": int(time.time()),
            "mood": mood,
        }
        tmp = EMOTION_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, EMOTION_FILE)
        self.emotion_ready.emit(emotion, confidence, mood)
