# core/drowsiness_detector.py
# Tier-2 drowsiness detection:
#   EAR (Eye Aspect Ratio) + PERCLOS
#   MAR (Mouth Aspect Ratio / yawn detection)
#   Head-pose pitch (nodding detection via 3D facial transform matrix)
# Requires:  pip install mediapipe
# Model auto-downloads to face_landmarker.task on first run (~3 MB).

import os
import time
import math
import urllib.request
import numpy as np

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "face_landmarker.task")
_MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)

# ── MediaPipe Face Mesh landmark indices ─────────────────────────────────────
# EAR formula: (||P2-P6|| + ||P3-P5||) / (2*||P1-P4||)
_L_EYE = [362, 385, 387, 263, 373, 380]
_R_EYE = [33,  160, 158, 133, 153, 144]

# MAR: vertical / horizontal mouth opening
_MOUTH_TOP    = 13
_MOUTH_BOTTOM = 14
_MOUTH_LEFT   = 78
_MOUTH_RIGHT  = 308

# ── Thresholds ────────────────────────────────────────────────────────────────
EAR_THRESH          = 0.25
MAR_THRESH          = 0.60
PERCLOS_WINDOW      = 60      # frames
PERCLOS_THRESH      = 0.65
YAWN_MIN_FRAMES     = 18
HEAD_NOD_THRESH_DEG = 20.0    # degrees pitch below neutral to count as a nod
HEAD_NOD_FRAMES     = 30      # frames head must stay drooped to count

# Blink detection: a blink is EAR < threshold for 2–12 consecutive frames
BLINK_MIN_FRAMES    = 2
BLINK_MAX_FRAMES    = 12
BLINK_RATE_WINDOW   = 60      # seconds rolling window for blinks-per-minute


def _dist(a, b) -> float:
    return float(np.linalg.norm(a - b))


def _lm(landmarks, idx):
    p = landmarks[idx]
    return np.array([p.x, p.y])


def _ear(landmarks, eye_idx: list) -> float:
    pts = [_lm(landmarks, i) for i in eye_idx]
    A = _dist(pts[1], pts[5])
    B = _dist(pts[2], pts[4])
    C = _dist(pts[0], pts[3])
    return (A + B) / (2.0 * C) if C > 0 else 0.0


def _mar(landmarks) -> float:
    top   = _lm(landmarks, _MOUTH_TOP)
    bot   = _lm(landmarks, _MOUTH_BOTTOM)
    left  = _lm(landmarks, _MOUTH_LEFT)
    right = _lm(landmarks, _MOUTH_RIGHT)
    h = _dist(left, right)
    return _dist(top, bot) / h if h > 0 else 0.0


def _pitch_from_transform(mat4x4) -> float:
    """
    Extract pitch angle (degrees) from MediaPipe's 4×4 facial transform matrix.
    Pitch < 0  →  head tilting down (nodding / drooping forward).
    Pitch > 0  →  head tilting up.
    """
    R = np.array(mat4x4).reshape(4, 4)[:3, :3]
    # Standard Euler decomposition for rotation around X (pitch)
    pitch_rad = math.atan2(-R[2, 1], R[2, 2])
    return math.degrees(pitch_rad)


def _download_model():
    model_path = os.path.abspath(_MODEL_PATH)
    if os.path.exists(model_path):
        return model_path
    print("[DrowsinessDetector] Downloading face_landmarker.task (~3 MB)…", flush=True)
    try:
        urllib.request.urlretrieve(_MODEL_URL, model_path)
        print(f"[DrowsinessDetector] Model saved to {model_path}", flush=True)
        return model_path
    except Exception as e:
        print(f"[DrowsinessDetector] Download failed: {e}", flush=True)
        return None


# ─────────────────────────────────────────────────────────────────────────────
class DrowsinessDetector:
    """
    Process RGB frames and return drowsiness metrics.
    Uses mediapipe Tasks API (0.10+) with FaceLandmarker in VIDEO mode.
    """

    def __init__(self):
        self._landmarker  = None
        self._available   = False
        self._start_time  = time.time()

        self._ear_hist:   list = []
        self._pitch_hist: list = []   # raw pitch values for smoothing
        self._nod_frames  = 0         # consecutive frames head is drooping
        self._yawn_frames = 0
        self._yawn_total  = 0

        # Blink tracking
        self._eye_closed_frames = 0         # current run of closed frames
        self._blink_times:  list = []       # timestamps of completed blinks

        self._init_landmarker()

    def _init_landmarker(self):
        try:
            import mediapipe.tasks as mpt

            model_path = _download_model()
            if model_path is None:
                return

            options = mpt.vision.FaceLandmarkerOptions(
                base_options=mpt.BaseOptions(model_asset_path=model_path),
                running_mode=mpt.vision.RunningMode.VIDEO,
                num_faces=1,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
                min_tracking_confidence=0.5,
                output_facial_transformation_matrixes=True,   # ← 3D head pose
            )
            self._landmarker = mpt.vision.FaceLandmarker.create_from_options(options)
            self._available  = True
        except Exception as e:
            print(f"[DrowsinessDetector] Init failed: {e}", flush=True)
            self._landmarker = None
            self._available  = False

    @property
    def available(self) -> bool:
        return self._available

    def reset_session(self):
        self._ear_hist.clear()
        self._pitch_hist.clear()
        self._nod_frames         = 0
        self._yawn_frames        = 0
        self._yawn_total         = 0
        self._eye_closed_frames  = 0
        self._blink_times.clear()
        self._start_time         = time.time()

    def process_frame(self, frame_rgb: np.ndarray) -> dict:
        if not self._available:
            return {"available": False}

        try:
            import mediapipe as mp
            mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            timestamp = int((time.time() - self._start_time) * 1000)
            result    = self._landmarker.detect_for_video(mp_image, timestamp)
        except Exception as e:
            print(f"[DrowsinessDetector] process_frame error: {e}", flush=True)
            return self._empty()

        if not result.face_landmarks:
            return self._empty()

        lms = result.face_landmarks[0]

        # ── EAR + PERCLOS + Blink rate ────────────────────────────────────────
        ear = (_ear(lms, _L_EYE) + _ear(lms, _R_EYE)) / 2.0
        eye_closed = ear < EAR_THRESH
        self._ear_hist.append(eye_closed)
        if len(self._ear_hist) > PERCLOS_WINDOW:
            self._ear_hist.pop(0)
        perclos = sum(self._ear_hist) / len(self._ear_hist)

        # Blink detection: closed run ends → count if within valid range
        if eye_closed:
            self._eye_closed_frames += 1
        else:
            run = self._eye_closed_frames
            if BLINK_MIN_FRAMES <= run <= BLINK_MAX_FRAMES:
                self._blink_times.append(time.time())
            self._eye_closed_frames = 0

        # Prune blink timestamps outside rolling window
        cutoff = time.time() - BLINK_RATE_WINDOW
        self._blink_times = [t for t in self._blink_times if t >= cutoff]
        blinks_per_min = len(self._blink_times)   # count in last 60 s

        # ── MAR / Yawn ────────────────────────────────────────────────────────
        mar = _mar(lms)
        if mar > MAR_THRESH:
            self._yawn_frames += 1
        else:
            if self._yawn_frames >= YAWN_MIN_FRAMES:
                self._yawn_total += 1
            self._yawn_frames = 0
        is_yawning = self._yawn_frames >= YAWN_MIN_FRAMES

        # ── Head pitch — real 3D angle from transform matrix ──────────────────
        pitch_deg = 0.0
        if result.facial_transformation_matrixes:
            pitch_deg = _pitch_from_transform(result.facial_transformation_matrixes[0])

        # Smooth pitch over last 10 frames to avoid jitter
        self._pitch_hist.append(pitch_deg)
        if len(self._pitch_hist) > 10:
            self._pitch_hist.pop(0)
        smooth_pitch = sum(self._pitch_hist) / len(self._pitch_hist)

        # Count consecutive frames where head is drooped past threshold
        if smooth_pitch < -HEAD_NOD_THRESH_DEG:
            self._nod_frames += 1
        else:
            self._nod_frames = max(0, self._nod_frames - 2)   # decay slowly
        head_drooping = self._nod_frames >= HEAD_NOD_FRAMES

        # ── Drowsiness score ──────────────────────────────────────────────────
        score = 0.0
        if perclos >= PERCLOS_THRESH:
            score += 0.55
        elif perclos >= 0.40:
            score += 0.25
        if is_yawning:
            score += 0.25
        elif self._yawn_total >= 2:
            score += 0.10
        if head_drooping:
            score += 0.20

        confidence = min(score, 1.0)
        is_drowsy  = confidence >= 0.50

        return {
            "available":      True,
            "face_detected":  True,
            "ear":            round(ear, 3),
            "mar":            round(mar, 3),
            "perclos":        round(perclos, 3),
            "pitch_deg":      round(smooth_pitch, 1),
            "is_yawning":     is_yawning,
            "yawn_count":     self._yawn_total,
            "head_drooping":  head_drooping,
            "is_drowsy":      is_drowsy,
            "confidence":     round(confidence, 3),
            "blinks_per_min": blinks_per_min,
        }

    def _empty(self) -> dict:
        return {
            "available": True, "face_detected": False,
            "ear": 0.0, "mar": 0.0, "perclos": 0.0, "pitch_deg": 0.0,
            "is_yawning": False, "yawn_count": self._yawn_total,
            "head_drooping": False, "is_drowsy": False, "confidence": 0.0,
            "blinks_per_min": len(self._blink_times),
        }

    def close(self):
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None
