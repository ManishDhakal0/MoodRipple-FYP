# moodripple_ui.py
# Full working UI with Spotify playback controls

import os
from pathlib import Path

# Set BEFORE importing TensorFlow / Qt
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

import sys
import json
import time
import random
from collections import deque
from datetime import datetime

import numpy as np
import cv2
import tensorflow as tf

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
    QSlider,
    QListWidget,
    QSplitter,
    QLineEdit,
    QTextEdit,
    QDateTimeEdit,
    QFormLayout,
    QScrollArea,
    QStackedWidget,
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer, QDateTime
from PyQt5.QtGui import QImage, QPixmap

from text_emotion import TextEmotionDetector
from spotify_auth_page import SpotifyAuthPage
from calendar_auth_page import CalendarAuthPage


SPOTIFY_CLIENT_ID = "ec7d75c8cbe549b48ccb8898a51d7c72"
SPOTIFY_CLIENT_SECRET = "dd2cae1ec9ba42afa8eccb6f9d335e98"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_SCOPE = (
    "user-read-recently-played "
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing "
    "user-top-read "
    "user-read-private"
)
EMOTION_TO_MOOD = {
    "happy": "energized",
    "surprise": "energized",
    "neutral": "focused",
    "sad": "calm",
    "fear": "calm",
    "disgust": "calm",
    "angry": "calm",
}


# ============================
# Emotion Detection Thread
# ============================
class EmotionDetectionThread(QThread):
    """Thread for running emotion detection without blocking UI"""

    update_frame = pyqtSignal(np.ndarray)
    update_emotion = pyqtSignal(str, float, str)
    update_status = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.cap = None
        self.model = None
        self.face_cascade = None
        self.emotion_labels = []
        self.EMOTION_FILE = "latest_emotion.json"

        self.EXPORT_INTERVAL = 30
        self.VOTE_WINDOW = 6
        self.MIN_FACE_CONFIDENCE = 0.38
        self.TARGET_EMOTIONS = ("happy", "sad", "neutral")
        self.EMOTION_GROUPS = {
            "happy": {"happy": 1.0, "surprise": 0.55},
            "sad": {"sad": 1.0, "fear": 0.45, "disgust": 0.20},
            "neutral": {"neutral": 0.82, "angry": 0.18, "disgust": 0.10},
        }

        self.pred_buffer = deque(maxlen=5000)
        self.last_export_time = 0

    def load_model(self) -> bool:
        try:
            if os.path.exists("emotion_recognition_model_auto.h5"):
                model_path = "emotion_recognition_model_auto.h5"
            elif os.path.exists("emotion_model_final.h5"):
                model_path = "emotion_model_final.h5"
            else:
                self.update_status.emit("❌ No model file found (.h5).", "#ff6b6b")
                return False

            self.update_status.emit(f"Loading model: {model_path} ...", "#b3b3b3")
            self.model = tf.keras.models.load_model(model_path)
            self.update_status.emit(f"✅ Model loaded: {model_path}", "#1DB954")

            if os.path.exists("class_names.json"):
                with open("class_names.json", "r", encoding="utf-8") as f:
                    self.emotion_labels = json.load(f)
            else:
                self.emotion_labels = [
                    "angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"
                ]

            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            if self.face_cascade.empty():
                self.update_status.emit("❌ Haarcascade failed to load.", "#ff6b6b")
                return False

            return True

        except Exception as e:
            self.update_status.emit(f"❌ Error loading model: {e}", "#ff6b6b")
            return False

    def run(self):
        if self.face_cascade is None or self.model is None:
            self.update_status.emit("❌ Model not loaded.", "#ff6b6b")
            return

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not self.cap.isOpened():
            self.update_status.emit("❌ Could not open camera.", "#ff6b6b")
            return

        self.update_status.emit("✅ Camera started.", "#1DB954")

        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=7, minSize=(30, 30)
            )

            best_emotion = None
            best_conf = -1.0
            best_box = None

            for x, y, w, h in faces:
                face_roi = gray[y : y + h, x : x + w]
                if face_roi.size == 0:
                    continue

                face_roi = cv2.equalizeHist(face_roi)
                face_roi = cv2.resize(face_roi, (48, 48))
                face_roi = face_roi.reshape(1, 48, 48, 1).astype(np.float32) / 255.0

                prediction = self.model.predict(face_roi, verbose=0)
                emotion, confidence = self.collapse_prediction(prediction)

                if confidence > best_conf:
                    best_conf = confidence
                    best_emotion = emotion
                    best_box = (x, y, w, h)

            if best_box is not None and best_conf >= self.MIN_FACE_CONFIDENCE:
                x, y, w, h = best_box
                self.pred_buffer.append((time.time(), best_emotion, best_conf))

                conf_pct = best_conf * 100
                color = (0, 255, 0) if conf_pct > 60 else (0, 165, 255)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)

                label = f"{best_emotion} ({conf_pct:.1f}%)"
                cv2.putText(frame, label, (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

            now = time.time()
            if (now - self.last_export_time) >= self.EXPORT_INTERVAL:
                chosen_emotion, chosen_conf = self.decide_stable_emotion()
                if chosen_emotion is not None and chosen_conf >= 0.5:
                    self.last_export_time = now
                    self.export_emotion(chosen_emotion, chosen_conf)

            self.update_frame.emit(frame)
            time.sleep(0.03)

        if self.cap is not None:
            self.cap.release()
        self.update_status.emit("⏹ Camera stopped.", "#b3b3b3")

    def decide_stable_emotion(self):
        now = time.time()
        recent = [(e, c) for (ts, e, c) in self.pred_buffer 
                  if (now - ts) <= self.VOTE_WINDOW]
        if not recent:
            return None, None

        emotion_scores = {}
        emotion_counts = {}

        for emotion, conf in recent:
            emotion_scores[emotion] = emotion_scores.get(emotion, 0.0) + conf
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        if not emotion_scores:
            return None, None

        best_emotion = max(emotion_scores, key=emotion_scores.get)
        avg_conf = emotion_scores[best_emotion] / emotion_counts[best_emotion]
        return best_emotion, avg_conf

    def export_emotion(self, emotion, confidence):
        EMOTION_TO_MOOD = {
            "happy": "energized",
            "neutral": "focused",
            "sad": "calm",
        }
        mood = EMOTION_TO_MOOD.get(emotion, "focused")

        payload = {
            "emotion": emotion,
            "confidence": float(confidence),
            "timestamp_unix": int(time.time())
        }

        tmp_path = self.EMOTION_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.EMOTION_FILE)

        self.update_emotion.emit(emotion, confidence, mood)

    def stop(self):
        self.is_running = False
        self.wait()


# ============================
# Spotify Monitor Thread
# ============================
class SpotifyMonitorThread(QThread):
    """Monitor Spotify playback state"""
    update_playback = pyqtSignal(dict)

    def __init__(self, spotify_client):
        super().__init__()
        self.sp = spotify_client
        self.is_running = False

    def run(self):
        while self.is_running:
            try:
                current = self.sp.current_playback()
                if current and current.get('item'):
                    info = {
                        'track_id': current['item'].get('id'),
                        'track': current['item']['name'],
                        'artist': current['item']['artists'][0]['name'],
                        'is_playing': current['is_playing'],
                        'volume': current.get('device', {}).get('volume_percent', 50),
                        'progress_ms': current.get('progress_ms', 0),
                        'duration_ms': current['item'].get('duration_ms', 0),
                    }
                    self.update_playback.emit(info)
            except:
                pass
            time.sleep(1)

    def stop(self):
        self.is_running = False
        self.wait()


class CalendarEventsThread(QThread):
    update_events = pyqtSignal(list)
    update_status = pyqtSignal(str, str)

    def __init__(self, service=None):
        super().__init__()
        self.service = service

    def run(self):
        try:
            from datetime import timezone
            if self.service is not None:
                service = self.service
            else:
                from fyp_calendar import get_calendar_service
                service = get_calendar_service()

            now = datetime.now(timezone.utc).isoformat()
            response = service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=8,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            events = response.get("items", [])
            self.update_events.emit(events)
            self.update_status.emit("Calendar synced.", "#1DB954")
        except Exception as e:
            self.update_status.emit(f"Calendar sync failed: {e}", "#ff6b6b")
            self.update_events.emit([])


class CalendarCreateThread(QThread):
    update_status = pyqtSignal(str, str)
    created = pyqtSignal()

    def __init__(self, payload, service=None):
        super().__init__()
        self.payload = payload
        self.service = service

    def run(self):
        try:
            if self.service is not None:
                service = self.service
            else:
                from fyp_calendar import get_calendar_service
                service = get_calendar_service()
            service.events().insert(calendarId="primary", body=self.payload).execute()
            self.update_status.emit("Calendar event created.", "#1DB954")
            self.created.emit()
        except Exception as e:
            self.update_status.emit(f"Calendar create failed: {e}", "#ff6b6b")


# ============================
# Main UI
# ============================
class MoodRippleUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MoodRipple - Emotion-Based Music Player")
        self.setGeometry(100, 100, 1400, 850)

        self.detection_thread = None
        self.spotify_monitor = None
        self.sp = None
        self.spotify_user = None
        self.spotify_product = None
        self.autoplay_enabled = False
        self.last_auto_emotion = None
        self.current_mood = None
        self.pending_mood = None
        self.last_playback_track_id = None
        self.queued_track_ids = []
        self.queued_tracks = []
        self.queue_target_size = 2
        self.calendar_thread = None
        self.calendar_create_thread = None
        self.text_detector = None
        self.calendar_service = None

        self.init_text_detector()

        self.setup_ui()
        self.apply_styles()


    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(78)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 10, 24, 10)

        title_label = QLabel("🎵 MoodRipple")
        title_label.setObjectName("title")
        subtitle_label = QLabel("Emotion-Based Music Player")
        subtitle_label.setObjectName("subtitle")

        header_layout.addWidget(title_label)
        header_layout.addSpacing(14)
        header_layout.addWidget(subtitle_label)
        header_layout.addStretch()

        main_layout.addWidget(header)

        # Body: left sidebar + stacked pages
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # ── Left sidebar navigation ──────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(185)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(10, 24, 10, 20)
        sb_layout.setSpacing(2)

        self.nav_btn_dashboard = QPushButton("🏠  Dashboard")
        self.nav_btn_dashboard.setObjectName("navButton")
        self.nav_btn_dashboard.setCheckable(True)
        self.nav_btn_dashboard.setChecked(True)
        self.nav_btn_dashboard.clicked.connect(lambda: self._navigate(0))

        self.nav_btn_spotify = QPushButton("🎵  Spotify")
        self.nav_btn_spotify.setObjectName("navButton")
        self.nav_btn_spotify.setCheckable(True)
        self.nav_btn_spotify.clicked.connect(lambda: self._navigate(1))

        self.nav_dot_spotify = QLabel("● Not connected")
        self.nav_dot_spotify.setObjectName("navDotBad")

        self.nav_btn_calendar = QPushButton("📅  Calendar")
        self.nav_btn_calendar.setObjectName("navButton")
        self.nav_btn_calendar.setCheckable(True)
        self.nav_btn_calendar.clicked.connect(lambda: self._navigate(2))

        self.nav_dot_calendar = QLabel("● Not connected")
        self.nav_dot_calendar.setObjectName("navDotBad")

        sb_layout.addWidget(self.nav_btn_dashboard)
        sb_layout.addSpacing(8)
        sb_layout.addWidget(self.nav_btn_spotify)
        sb_layout.addWidget(self.nav_dot_spotify)
        sb_layout.addSpacing(8)
        sb_layout.addWidget(self.nav_btn_calendar)
        sb_layout.addWidget(self.nav_dot_calendar)
        sb_layout.addStretch()

        # ── Stacked pages ────────────────────────────
        self.page_stack = QStackedWidget()

        # Page 0: Dashboard (existing content)
        dashboard_page = QWidget()
        dashboard_layout = QHBoxLayout(dashboard_page)
        dashboard_layout.setContentsMargins(20, 20, 20, 20)
        dashboard_layout.setSpacing(20)

        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setChildrenCollapsible(False)
        content_splitter.setHandleWidth(10)

        # LEFT PANEL: Camera
        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_panel.setMinimumWidth(520)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(12)

        cam_title = QLabel("📷 Live Camera Feed")
        cam_title.setObjectName("panelTitle")
        left_layout.addWidget(cam_title)

        self.camera_label = QLabel()
        self.camera_label.setObjectName("cameraFeed")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(360, 240)
        self.camera_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.camera_label, stretch=1)

        cam_buttons = QHBoxLayout()
        cam_buttons.setSpacing(12)

        self.start_btn = QPushButton("▶ Start Detection")
        self.start_btn.setObjectName("primaryButton")
        self.start_btn.clicked.connect(self.start_detection)

        self.stop_btn = QPushButton("⏹ Stop Detection")
        self.stop_btn.setObjectName("secondaryButton")
        self.stop_btn.clicked.connect(self.stop_detection)
        self.stop_btn.setEnabled(False)

        cam_buttons.addWidget(self.start_btn)
        cam_buttons.addWidget(self.stop_btn)
        left_layout.addLayout(cam_buttons)

        content_splitter.addWidget(left_panel)

        # RIGHT PANEL: Emotion + Spotify + Calendar
        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right_panel.setMinimumWidth(420)

        right_scroll = QScrollArea()
        right_scroll.setObjectName("panelScroll")
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(14)

        # Emotion card
        emotion_frame = QFrame()
        emotion_frame.setObjectName("card")
        emotion_layout = QVBoxLayout(emotion_frame)
        emotion_layout.setContentsMargins(14, 14, 14, 14)
        emotion_layout.setSpacing(8)

        emotion_title = QLabel("🧠 Current Emotion")
        emotion_title.setObjectName("panelTitle")

        self.emotion_display = QLabel("😐 Neutral")
        self.emotion_display.setObjectName("emotionDisplay")
        self.emotion_display.setAlignment(Qt.AlignCenter)

        self.confidence_label = QLabel("Confidence: 0.0%")
        self.confidence_label.setObjectName("subText")
        self.confidence_label.setAlignment(Qt.AlignCenter)

        self.mood_label = QLabel("Mood: Focused")
        self.mood_label.setObjectName("moodText")
        self.mood_label.setAlignment(Qt.AlignCenter)

        emotion_layout.addWidget(emotion_title)
        emotion_layout.addWidget(self.emotion_display)
        emotion_layout.addWidget(self.confidence_label)
        emotion_layout.addWidget(self.mood_label)

        right_layout.addWidget(emotion_frame)

        text_frame = QFrame()
        text_frame.setObjectName("card")
        text_layout = QVBoxLayout(text_frame)
        text_layout.setContentsMargins(14, 14, 14, 14)
        text_layout.setSpacing(10)

        text_title = QLabel("Text Emotion")
        text_title.setObjectName("panelTitle")

        self.text_status = QLabel("Use this when camera detection is off")
        self.text_status.setObjectName("subText")
        self.text_status.setWordWrap(True)

        self.text_input = QTextEdit()
        self.text_input.setObjectName("textArea")
        self.text_input.setPlaceholderText("Type how you feel here...")
        self.text_input.setFixedHeight(100)

        self.text_result_label = QLabel("Result: Not analyzed")
        self.text_result_label.setObjectName("subText")
        self.text_result_label.setWordWrap(True)

        self.text_analyze_btn = QPushButton("Analyze Text Mood")
        self.text_analyze_btn.setObjectName("primaryButton")
        self.text_analyze_btn.clicked.connect(self.analyze_text_emotion)

        text_layout.addWidget(text_title)
        text_layout.addWidget(self.text_status)
        text_layout.addWidget(self.text_input)
        text_layout.addWidget(self.text_result_label)
        text_layout.addWidget(self.text_analyze_btn)

        right_layout.addWidget(text_frame)

        # Spotify card
        spotify_frame = QFrame()
        spotify_frame.setObjectName("card")
        spotify_layout = QVBoxLayout(spotify_frame)
        spotify_layout.setContentsMargins(14, 14, 14, 14)
        spotify_layout.setSpacing(10)

        spotify_title = QLabel("🎵 Now Playing")
        spotify_title.setObjectName("panelTitle")

        self.track_label = QLabel("No track playing")
        self.track_label.setObjectName("trackLabel")
        self.track_label.setAlignment(Qt.AlignCenter)
        self.track_label.setWordWrap(True)

        self.artist_label = QLabel("")
        self.artist_label.setObjectName("subText")
        self.artist_label.setAlignment(Qt.AlignCenter)

        # Playback controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setObjectName("controlButton")
        self.prev_btn.clicked.connect(self.previous_track)
        self.prev_btn.setEnabled(False)

        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setObjectName("controlButton")
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.play_pause_btn.setEnabled(False)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setObjectName("controlButton")
        self.next_btn.clicked.connect(self.next_track)
        self.next_btn.setEnabled(False)

        controls_layout.addWidget(self.prev_btn)
        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(self.next_btn)

        # Volume control
        volume_layout = QHBoxLayout()
        volume_icon = QLabel("🔊")
        volume_icon.setObjectName("volumeIcon")
        volume_layout.addWidget(volume_icon)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setEnabled(False)
        self.volume_slider.valueChanged.connect(self.change_volume)
        volume_layout.addWidget(self.volume_slider)

        self.spotify_status = QLabel("Status: Not Connected")
        self.spotify_status.setObjectName("statusBad")
        self.spotify_status.setAlignment(Qt.AlignCenter)

        self.queue_list = QListWidget()
        self.queue_list.setObjectName("queueList")
        self.queue_list.setMinimumHeight(110)
        self.queue_list.setSpacing(4)
        self.queue_list.addItem("Queue will appear here")

        calendar_frame = QFrame()
        calendar_frame.setObjectName("card")
        calendar_layout = QVBoxLayout(calendar_frame)
        calendar_layout.setContentsMargins(14, 14, 14, 14)
        calendar_layout.setSpacing(10)

        calendar_title = QLabel("Calendar")
        calendar_title.setObjectName("panelTitle")

        self.calendar_status = QLabel("Upcoming events will appear here")
        self.calendar_status.setObjectName("subText")
        self.calendar_status.setWordWrap(True)

        self.calendar_list = QListWidget()
        self.calendar_list.setObjectName("calendarList")
        self.calendar_list.setMinimumHeight(180)
        self.calendar_list.addItem("No events loaded")

        form_title = QLabel("Add Event")
        form_title.setObjectName("panelTitle")

        calendar_form = QFormLayout()
        calendar_form.setContentsMargins(0, 0, 0, 0)
        calendar_form.setSpacing(8)

        self.calendar_title_input = QLineEdit()
        self.calendar_title_input.setObjectName("textInput")
        self.calendar_title_input.setPlaceholderText("Event title")

        self.calendar_start_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.calendar_start_input.setObjectName("dateInput")
        self.calendar_start_input.setCalendarPopup(True)
        self.calendar_start_input.setDisplayFormat("yyyy-MM-dd HH:mm")

        self.calendar_end_input = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.calendar_end_input.setObjectName("dateInput")
        self.calendar_end_input.setCalendarPopup(True)
        self.calendar_end_input.setDisplayFormat("yyyy-MM-dd HH:mm")

        self.calendar_location_input = QLineEdit()
        self.calendar_location_input.setObjectName("textInput")
        self.calendar_location_input.setPlaceholderText("Location")

        self.calendar_description_input = QTextEdit()
        self.calendar_description_input.setObjectName("textArea")
        self.calendar_description_input.setPlaceholderText("Description")
        self.calendar_description_input.setFixedHeight(72)

        calendar_form.addRow("Title", self.calendar_title_input)
        calendar_form.addRow("Start", self.calendar_start_input)
        calendar_form.addRow("End", self.calendar_end_input)
        calendar_form.addRow("Location", self.calendar_location_input)
        calendar_form.addRow("Notes", self.calendar_description_input)

        self.refresh_calendar_btn = QPushButton("Refresh Calendar")
        self.refresh_calendar_btn.setObjectName("secondaryButton")
        self.refresh_calendar_btn.clicked.connect(self.refresh_calendar)

        self.create_calendar_btn = QPushButton("Create Event")
        self.create_calendar_btn.setObjectName("primaryButton")
        self.create_calendar_btn.clicked.connect(self.create_calendar_event)

        calendar_actions = QHBoxLayout()
        calendar_actions.setSpacing(8)
        calendar_actions.addWidget(self.refresh_calendar_btn)
        calendar_actions.addWidget(self.create_calendar_btn)

        calendar_layout.addWidget(calendar_title)
        calendar_layout.addWidget(self.calendar_status)
        calendar_layout.addWidget(self.calendar_list)
        calendar_layout.addWidget(form_title)
        calendar_layout.addLayout(calendar_form)
        calendar_layout.addLayout(calendar_actions)

        self.start_spotify_btn = QPushButton("▶ Start Auto-Play")
        self.start_spotify_btn.setObjectName("primaryButton")
        self.start_spotify_btn.clicked.connect(self.start_spotify)

        self.stop_spotify_btn = QPushButton("⏹ Stop Auto-Play")
        self.stop_spotify_btn.setObjectName("secondaryButton")
        self.stop_spotify_btn.clicked.connect(self.stop_spotify)
        self.stop_spotify_btn.setEnabled(False)

        spotify_layout.addWidget(spotify_title)
        spotify_layout.addWidget(self.track_label)
        spotify_layout.addWidget(self.artist_label)
        spotify_layout.addSpacing(4)
        spotify_layout.addLayout(controls_layout)
        spotify_layout.addLayout(volume_layout)
        spotify_layout.addWidget(self.spotify_status)
        spotify_layout.addWidget(QLabel("Up Next"))
        spotify_layout.addWidget(self.queue_list)
        spotify_layout.addSpacing(6)
        spotify_layout.addWidget(self.start_spotify_btn)
        spotify_layout.addWidget(self.stop_spotify_btn)

        right_layout.addWidget(spotify_frame)
        right_layout.addWidget(calendar_frame)
        right_layout.addStretch()
        right_scroll.setWidget(right_content)

        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        right_panel_layout.addWidget(right_scroll)

        content_splitter.addWidget(right_panel)
        content_splitter.setStretchFactor(0, 3)
        content_splitter.setStretchFactor(1, 2)
        content_splitter.setSizes([900, 520])
        dashboard_layout.addWidget(content_splitter)
        self.page_stack.addWidget(dashboard_page)

        # Page 1: Spotify auth
        self.spotify_auth_page = SpotifyAuthPage()
        self.spotify_auth_page.connected.connect(self._on_spotify_connected)
        self.spotify_auth_page.disconnected.connect(self._on_spotify_disconnected)
        self.page_stack.addWidget(self.spotify_auth_page)

        # Page 2: Google Calendar auth
        self.calendar_auth_page = CalendarAuthPage()
        self.calendar_auth_page.connected.connect(self._on_calendar_connected)
        self.calendar_auth_page.disconnected.connect(self._on_calendar_disconnected)
        self.page_stack.addWidget(self.calendar_auth_page)

        body_layout.addWidget(sidebar)
        body_layout.addWidget(self.page_stack, 1)
        main_layout.addWidget(body, 1)

        # Status bar
        status_bar = QFrame()
        status_bar.setObjectName("statusBar")
        status_bar.setFixedHeight(42)
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(16, 0, 16, 0)

        self.status_label = QLabel("Ready.")
        self.status_label.setObjectName("statusText")
        status_layout.addWidget(self.status_label)

        main_layout.addWidget(status_bar)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }

            #header {
                background-color: #0e0e0e;
                border-bottom: 2px solid #1DB954;
            }
            #title { font-size: 30px; font-weight: 800; color: #1DB954; }
            #subtitle { font-size: 12px; color: #b3b3b3; padding-top: 6px; }

            #panel {
                background-color: #15181c;
                border: 1px solid #243240;
                border-radius: 18px;
            }

            #panelScroll {
                background: transparent;
            }

            #card {
                background-color: #10151c;
                border: 1px solid #22303d;
                border-radius: 16px;
            }

            #panelTitle {
                font-size: 14px;
                font-weight: 700;
                color: white;
                padding: 4px 2px;
            }

            #cameraFeed {
                background-color: #000;
                border: 1px solid #2a2a2a;
                border-radius: 12px;
            }

            #emotionDisplay {
                font-size: 44px;
                font-weight: 800;
                color: #1DB954;
                padding: 10px 0px;
            }

            #subText {
                font-size: 12px;
                color: #b3b3b3;
            }

            #moodText {
                font-size: 14px;
                font-weight: 800;
                color: #1ed760;
                padding: 6px 0px;
            }

            #trackLabel {
                font-size: 16px;
                font-weight: 800;
                color: #f3f7fb;
                padding: 8px 8px 2px 8px;
            }

            #statusBad {
                font-size: 11px;
                color: #ff6b6b;
                padding: 6px;
            }

            #controlButton {
                background-color: #1c2a38;
                color: #f3f7fb;
                font-size: 19px;
                font-weight: bold;
                border: 1px solid #2c475e;
                border-radius: 28px;
                min-width: 56px;
                min-height: 56px;
            }
            #controlButton:hover { background-color: #2a4257; border: 1px solid #4bd489; }
            #controlButton:disabled { background-color: #11161b; color: #555; border: 1px solid #1a242d; }

            #volumeIcon {
                font-size: 16px;
                color: white;
                padding: 5px;
            }

            QSlider::groove:horizontal {
                background: #404040;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #1DB954;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #1ed760;
            }

            QPushButton#primaryButton {
                background-color: #1db954;
                color: #08120d;
                font-size: 12px;
                font-weight: 800;
                padding: 10px 18px;
                border: none;
                border-radius: 24px;
                min-height: 44px;
            }
            QPushButton#primaryButton:hover { background-color: #1ed760; }
            QPushButton#primaryButton:disabled { background-color: #3f3f3f; color: #8a8a8a; }

            QPushButton#secondaryButton {
                background-color: #18222c;
                color: #e9f1f7;
                font-size: 12px;
                font-weight: 800;
                padding: 10px 18px;
                border: 1px solid #30414f;
                border-radius: 24px;
                min-height: 44px;
            }
            QPushButton#secondaryButton:hover { background-color: #22313d; }
            QPushButton#secondaryButton:disabled { background-color: #141a20; color: #666; border: 1px solid #222; }

            #queueList, #calendarList {
                background-color: #0d1217;
                border: 1px solid #20303a;
                border-radius: 12px;
                color: #d8e3ec;
                padding: 8px;
                font-size: 12px;
            }
            #queueList::item, #calendarList::item {
                padding: 8px 6px;
                border-bottom: 1px solid #182129;
            }

            #textInput, #dateInput, #textArea {
                background-color: #0d1217;
                color: #e8f0f6;
                border: 1px solid #22303d;
                border-radius: 10px;
                padding: 8px 10px;
                font-size: 12px;
            }
            #textInput:focus, #dateInput:focus, #textArea:focus {
                border: 1px solid #1db954;
            }

            #statusBar {
                background-color: #0e0e0e;
                border-top: 1px solid #2a2a2a;
            }
            #statusText {
                font-size: 11px;
                color: #b3b3b3;
            }

            /* ── Sidebar ── */
            #sidebar {
                background-color: #0a0d10;
                border-right: 1px solid #1a2230;
            }
            QPushButton#navButton {
                background-color: transparent;
                color: #b3b3b3;
                font-size: 13px;
                font-weight: 600;
                padding: 10px 14px;
                border: none;
                border-radius: 10px;
                text-align: left;
                min-height: 40px;
            }
            QPushButton#navButton:hover {
                background-color: #1a2535;
                color: #ffffff;
            }
            QPushButton#navButton:checked {
                background-color: #0d2010;
                color: #1DB954;
            }
            #navDotBad {
                color: #ff6b6b;
                font-size: 10px;
                padding-left: 14px;
                margin-top: -2px;
            }
            #navDotGood {
                color: #1DB954;
                font-size: 10px;
                padding-left: 14px;
                margin-top: -2px;
            }

            /* ── Auth pages ── */
            #pageTitle {
                font-size: 22px;
                font-weight: 800;
                color: #ffffff;
                padding-bottom: 4px;
            }
        """)

    def set_status(self, message: str, color_hex: str = "#b3b3b3"):
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color_hex}; font-size: 11px;")

    # ── Sidebar navigation ──────────────────────────────
    def _navigate(self, index: int):
        self.page_stack.setCurrentIndex(index)
        self.nav_btn_dashboard.setChecked(index == 0)
        self.nav_btn_spotify.setChecked(index == 1)
        self.nav_btn_calendar.setChecked(index == 2)

    # ── Spotify auth signals ────────────────────────────
    def _on_spotify_connected(self, sp, display_name: str, product: str):
        self.sp = sp
        self.spotify_product = product
        self.spotify_user = {"display_name": display_name, "product": product}
        self.nav_dot_spotify.setText("● Connected")
        self.nav_dot_spotify.setObjectName("navDotGood")
        self.nav_dot_spotify.setStyleSheet(
            "color: #1DB954; font-size: 10px; padding-left: 14px;"
        )
        # Update dashboard status label
        if product.lower() == "premium":
            self.spotify_status.setText(f"Status: Premium ({display_name})")
            self.spotify_status.setStyleSheet(
                "color: #1DB954; font-size: 11px; padding: 6px;"
            )
        else:
            self.spotify_status.setText(f"Status: {product.capitalize()} ({display_name})")
            self.spotify_status.setStyleSheet(
                "color: #f39c12; font-size: 11px; padding: 6px;"
            )
        self.start_spotify_monitor()
        self.set_status(f"Spotify connected — {display_name} ({product})", "#1DB954")

    def _on_spotify_disconnected(self):
        self.sp = None
        self.nav_dot_spotify.setText("● Not connected")
        self.nav_dot_spotify.setObjectName("navDotBad")
        self.nav_dot_spotify.setStyleSheet(
            "color: #ff6b6b; font-size: 10px; padding-left: 14px;"
        )
        self.spotify_status.setText("Status: Not Connected")
        self.spotify_status.setStyleSheet("color: #ff6b6b; font-size: 11px; padding: 6px;")
        for btn in (self.play_pause_btn, self.prev_btn, self.next_btn):
            btn.setEnabled(False)
        self.volume_slider.setEnabled(False)
        if self.spotify_monitor is not None:
            self.spotify_monitor.stop()
            self.spotify_monitor = None
        self.set_status("Spotify disconnected.", "#b3b3b3")

    # ── Calendar auth signals ───────────────────────────
    def _on_calendar_connected(self, service):
        self.calendar_service = service
        self.nav_dot_calendar.setText("● Connected")
        self.nav_dot_calendar.setObjectName("navDotGood")
        self.nav_dot_calendar.setStyleSheet(
            "color: #1DB954; font-size: 10px; padding-left: 14px;"
        )
        self.set_status("Google Calendar connected.", "#1DB954")
        self.refresh_calendar()

    def _on_calendar_disconnected(self):
        self.calendar_service = None
        self.nav_dot_calendar.setText("● Not connected")
        self.nav_dot_calendar.setObjectName("navDotBad")
        self.nav_dot_calendar.setStyleSheet(
            "color: #ff6b6b; font-size: 10px; padding-left: 14px;"
        )
        self.set_status("Google Calendar disconnected.", "#b3b3b3")

    # Detection methods
    def start_detection(self):
        if self.detection_thread is None or not self.detection_thread.isRunning():
            self.detection_thread = EmotionDetectionThread()
            self.detection_thread.update_frame.connect(self.update_camera_frame)
            self.detection_thread.update_emotion.connect(self.update_emotion_display)
            self.detection_thread.update_status.connect(self.set_status)

            ok = self.detection_thread.load_model()
            if not ok:
                self.set_status("❌ Could not load model.", "#ff6b6b")
                return

            self.detection_thread.is_running = True
            self.detection_thread.start()

            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.set_status("✅ Detection started.", "#1DB954")

    def stop_detection(self):
        if self.detection_thread is not None:
            self.detection_thread.stop()
            self.detection_thread = None

        self.camera_label.clear()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.set_status("⏹ Detection stopped.", "#b3b3b3")

    def update_camera_frame(self, frame: np.ndarray):
        height, width, channel = frame.shape
        bytes_per_line = channel * width

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        q_img = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(q_img)
        scaled = pixmap.scaled(
            self.camera_label.width(),
            self.camera_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.camera_label.setPixmap(scaled)


    def spotify_has_premium(self) -> bool:
        if not self.sp:
            return False

        try:
            self.spotify_user = self.sp.current_user()
            self.spotify_product = (self.spotify_user or {}).get("product", "")
        except Exception:
            return False

        return (self.spotify_product or "").lower() == "premium"

    def get_preferred_device_id(self):
        if not self.sp:
            return None

        try:
            devices = self.sp.devices().get("devices", [])
        except Exception as e:
            self.set_status(f"Could not read Spotify devices: {e}", "#ff6b6b")
            return None

        if not devices:
            self.set_status(
                "Open Spotify desktop app and play one song so it appears as a device.",
                "#ff6b6b",
            )
            return None

        for matcher in (
            lambda d: d.get("type") == "Computer" and d.get("is_active"),
            lambda d: d.get("type") == "Computer",
            lambda d: d.get("is_active"),
            lambda d: True,
        ):
            selected = next((d for d in devices if matcher(d)), None)
            if selected:
                return selected.get("id")

        return None

    def get_mood_tracks(self, mood: str, num_tracks: int = 5):
        if not self.sp:
            return []

        try:
            recent = self.sp.current_user_recently_played(limit=50)
            tracks = [item["track"] for item in recent.get("items", [])]

            if not tracks:
                top = self.sp.current_user_top_tracks(limit=50, time_range="short_term")
                tracks = top.get("items", [])

            seen_ids = set()
            unique_tracks = []
            for track in tracks:
                track_id = track.get("id")
                if (
                    track_id
                    and not track.get("is_local", False)
                    and track_id not in seen_ids
                ):
                    unique_tracks.append(track)
                    seen_ids.add(track_id)

            random.seed(mood)
            random.shuffle(unique_tracks)
            return unique_tracks[:num_tracks]
        except Exception as e:
            self.set_status(f"Could not build Spotify queue: {e}", "#ff6b6b")
            return []

    def start_playback_on_desktop(self, track_uris):
        if not self.sp or not track_uris:
            return False

        device_id = self.get_preferred_device_id()
        if not device_id:
            return False

        try:
            self.sp.transfer_playback(device_id=device_id, force_play=False)
            time.sleep(0.8)
            self.sp.start_playback(device_id=device_id, uris=track_uris)
            return True
        except Exception as e:
            self.set_status(f"Spotify playback failed: {e}", "#ff6b6b")
            return False

    def play_mood_for_emotion(self, emotion: str):
        if not self.sp:
            self.set_status("Spotify is not connected.", "#ff6b6b")
            return

        if not self.spotify_has_premium():
            product = (self.spotify_product or "unknown").upper()
            self.set_status(
                f"Spotify account type is {product}. Playback control requires Premium.",
                "#ff6b6b",
            )
            return

        mood = EMOTION_TO_MOOD.get(emotion, "focused")
        tracks = self.get_mood_tracks(mood)
        if not tracks:
            self.set_status("No playable Spotify tracks found in your history.", "#ff6b6b")
            return

        track_uris = [track["uri"] for track in tracks if track.get("uri")]
        if not track_uris:
            self.set_status("Spotify returned tracks without playable URIs.", "#ff6b6b")
            return

        if self.start_playback_on_desktop(track_uris):
            first_track = tracks[0]
            artist = first_track["artists"][0]["name"] if first_track.get("artists") else "Unknown"
            self.track_label.setText(first_track["name"])
            self.artist_label.setText(artist)
            self.last_auto_emotion = emotion
            self.set_status(
                f"Auto-play sent {mood} music to Spotify desktop app.",
                "#1DB954",
            )

    def queue_tracks_for_mood(self, mood: str, count: int = 1):
        if not self.sp or count <= 0:
            return 0

        try:
            device_id = self.get_preferred_device_id()
            if not device_id:
                return 0

            tracks = self.get_mood_tracks(mood, num_tracks=max(count + len(self.queued_track_ids), 8))
            added = 0

            for track in tracks:
                track_uri = track.get("uri")
                track_id = track.get("id")
                if not track_uri or not track_id:
                    continue
                if track_id == self.last_playback_track_id or track_id in self.queued_track_ids:
                    continue

                self.sp.add_to_queue(track_uri, device_id=device_id)
                self.queued_track_ids.append(track_id)
                artist = track["artists"][0]["name"] if track.get("artists") else "Unknown"
                self.queued_tracks.append(
                    {"id": track_id, "name": track.get("name", "Unknown"), "artist": artist, "mood": mood}
                )
                added += 1

                if added >= count:
                    break

            self.refresh_queue_display()
            return added
        except Exception as e:
            self.set_status(f"Spotify queue update failed: {e}", "#ff6b6b")
            return 0

    def sync_autoplay_queue(self, force_replace: bool = False):
        if not self.autoplay_enabled or not self.sp:
            return

        target_mood = self.pending_mood or self.current_mood
        if not target_mood:
            return

        try:
            current = self.sp.current_playback()
        except Exception as e:
            self.set_status(f"Could not read Spotify playback: {e}", "#ff6b6b")
            return

        has_current_track = bool(current and current.get("item") and current["item"].get("id"))
        if not has_current_track or force_replace:
            tracks = self.get_mood_tracks(target_mood, num_tracks=max(self.queue_target_size, 3))
            track_uris = [track["uri"] for track in tracks if track.get("uri")]
            if not track_uris:
                self.set_status("No playable Spotify tracks found in your history.", "#ff6b6b")
                return
            if self.start_playback_on_desktop(track_uris[: self.queue_target_size]):
                first_track = tracks[0]
                self.current_mood = target_mood
                self.pending_mood = None
                self.last_playback_track_id = first_track.get("id")
                self.queued_track_ids = [track.get("id") for track in tracks[1 : self.queue_target_size] if track.get("id")]
                self.queued_tracks = []
                for track in tracks[1 : self.queue_target_size]:
                    track_id = track.get("id")
                    if not track_id:
                        continue
                    artist = track["artists"][0]["name"] if track.get("artists") else "Unknown"
                    self.queued_tracks.append(
                        {"id": track_id, "name": track.get("name", "Unknown"), "artist": artist, "mood": target_mood}
                    )
                artist = first_track["artists"][0]["name"] if first_track.get("artists") else "Unknown"
                self.track_label.setText(first_track["name"])
                self.artist_label.setText(artist)
                self.refresh_queue_display()
                self.set_status(f"Auto-play started with {target_mood} music.", "#1DB954")
            return

        if self.pending_mood and self.pending_mood != self.current_mood:
            self.current_mood = self.pending_mood
            self.pending_mood = None
            self.queued_track_ids = []
            self.queued_tracks = []
            added = self.queue_tracks_for_mood(self.current_mood, count=self.queue_target_size)
            if added:
                self.set_status(
                    f"Mood changed. Replaced upcoming queue with {added} {self.current_mood} track(s) after the current song.",
                    "#1DB954",
                )
            return

        missing = max(0, self.queue_target_size - len(self.queued_track_ids))
        if missing:
            self.queue_tracks_for_mood(target_mood, count=missing)

    # Spotify methods

    def init_text_detector(self):
        try:
            self.text_detector = TextEmotionDetector()
        except Exception as e:
            self.text_detector = None
            print(f"Could not initialize text detector: {e}")

    def init_spotify(self):
        """Initialize Spotify client and force a clean re-login if cache points to a non-premium account."""
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth

            cache_path = "spotify_mood.cache"

            def build_client(show_dialog=False):
                return spotipy.Spotify(
                    auth_manager=SpotifyOAuth(
                        client_id=SPOTIFY_CLIENT_ID,
                        client_secret=SPOTIFY_CLIENT_SECRET,
                        redirect_uri=SPOTIFY_REDIRECT_URI,
                        scope=SPOTIFY_SCOPE + " user-read-email",
                        cache_path=cache_path,
                        open_browser=True,
                        show_dialog=show_dialog,
                    )
                )

            self.sp = build_client(show_dialog=False)
            self.spotify_user = self.sp.current_user()
            self.spotify_product = (self.spotify_user or {}).get("product", "")

            if (self.spotify_product or "").lower() != "premium" and os.path.exists(cache_path):
                os.remove(cache_path)
                self.sp = build_client(show_dialog=True)
                self.spotify_user = self.sp.current_user()
                self.spotify_product = (self.spotify_user or {}).get("product", "")

            user_id = (self.spotify_user or {}).get("id", "unknown")
            product = (self.spotify_product or "unknown").upper()
            print(f"Spotify client initialized for {user_id} ({product})")
        except Exception as e:
            print(f"Could not initialize Spotify: {e}")
            self.sp = None
            self.spotify_user = None
            self.spotify_product = None

    def analyze_text_emotion(self):
        if self.detection_thread is not None and self.detection_thread.isRunning():
            self.text_status.setText("Camera detection is active. Stop the camera to use text as fallback.")
            self.text_status.setStyleSheet("color: #f39c12; font-size: 12px;")
            return

        if self.text_detector is None:
            self.text_status.setText("Text emotion model is not available. Run text_emotion_train.py first.")
            self.text_status.setStyleSheet("color: #ff6b6b; font-size: 12px;")
            return

        text = self.text_input.toPlainText().strip()
        if not text:
            self.text_status.setText("Enter some text first.")
            self.text_status.setStyleSheet("color: #ff6b6b; font-size: 12px;")
            return

        result = self.text_detector.predict(text)
        emotion = result["emotion"]
        confidence = result["confidence"]
        mood = EMOTION_TO_MOOD.get(emotion, "focused")

        self.text_result_label.setText(
            f"Result: {emotion.capitalize()} ({confidence * 100:.1f}%)"
        )
        self.text_status.setText("Text emotion is now driving mood playback.")
        self.text_status.setStyleSheet("color: #1DB954; font-size: 12px;")

        payload = {
            "emotion": emotion,
            "confidence": float(confidence),
            "timestamp_unix": int(time.time()),
            "source": "text",
        }
        Path("latest_emotion.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.update_emotion_display(emotion, confidence, mood)

    def update_emotion_display(self, emotion: str, confidence: float, mood: str):
        EMOTION_EMOJIS = {
            "angry": "ðŸ˜ ", "disgust": "ðŸ¤¢", "fear": "ðŸ˜¨", "happy": "ðŸ˜Š",
            "neutral": "ðŸ˜", "sad": "ðŸ˜¢", "surprise": "ðŸ˜®"
        }
        emoji = EMOTION_EMOJIS.get(emotion, "ðŸ˜")

        self.emotion_display.setText(f"{emoji} {emotion.capitalize()}")
        self.confidence_label.setText(f"Confidence: {confidence * 100:.1f}%")
        self.mood_label.setText(f"Mood: {mood.capitalize()}")

        if self.autoplay_enabled:
            self.pending_mood = mood
            self.refresh_queue_display()
            if self.current_mood is None:
                self.sync_autoplay_queue(force_replace=False)

    def update_playback_info(self, info: dict):
        """Update Now Playing display and refill queue only after the current song changes."""
        previous_track_id = self.last_playback_track_id
        current_track_id = info.get("track_id")

        self.track_label.setText(info['track'])
        self.artist_label.setText(info['artist'])

        if info['is_playing']:
            self.play_pause_btn.setText("â¸")
        else:
            self.play_pause_btn.setText("â–¶")

        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(info['volume'])
        self.volume_slider.blockSignals(False)

        if current_track_id:
            self.last_playback_track_id = current_track_id

        if previous_track_id and current_track_id and current_track_id != previous_track_id:
            self.queued_track_ids = [
                queued_id for queued_id in self.queued_track_ids if queued_id != current_track_id
            ]
            self.queued_tracks = [
                track for track in self.queued_tracks if track.get("id") != current_track_id
            ]
            self.refresh_queue_display()
            if self.autoplay_enabled:
                self.sync_autoplay_queue(force_replace=False)

    def start_spotify_monitor(self):
        """Start monitoring Spotify playback."""
        if self.sp and (self.spotify_monitor is None or not self.spotify_monitor.isRunning()):
            self.spotify_monitor = SpotifyMonitorThread(self.sp)
            self.spotify_monitor.update_playback.connect(self.update_playback_info)
            self.spotify_monitor.is_running = True
            self.spotify_monitor.start()

            self.play_pause_btn.setEnabled(True)
            self.prev_btn.setEnabled(True)
            self.next_btn.setEnabled(True)
            self.volume_slider.setEnabled(True)

            if self.spotify_has_premium():
                user_id = (self.spotify_user or {}).get("id", "unknown")
                self.spotify_status.setText(f"Status: Premium ({user_id})")
                self.spotify_status.setStyleSheet("color: #1DB954; font-size: 11px; padding: 6px;")
            else:
                user_id = (self.spotify_user or {}).get("id", "unknown")
                product = (self.spotify_product or "unknown").capitalize()
                self.spotify_status.setText(f"Status: {product} ({user_id})")
                self.spotify_status.setStyleSheet("color: #f39c12; font-size: 11px; padding: 6px;")

    def toggle_play_pause(self):
        if self.sp:
            try:
                current = self.sp.current_playback()
                if current and current.get("is_playing"):
                    self.sp.pause_playback()
                else:
                    device_id = self.get_preferred_device_id()
                    if device_id:
                        self.sp.start_playback(device_id=device_id)
            except Exception as e:
                self.set_status(f"Spotify play/pause failed: {e}", "#ff6b6b")

    def next_track(self):
        if self.sp:
            try:
                self.sp.next_track()
            except Exception as e:
                self.set_status(f"Spotify next failed: {e}", "#ff6b6b")

    def previous_track(self):
        if self.sp:
            try:
                self.sp.previous_track()
            except Exception as e:
                self.set_status(f"Spotify previous failed: {e}", "#ff6b6b")

    def change_volume(self, value):
        if self.sp:
            try:
                self.sp.volume(value)
            except Exception as e:
                self.set_status(f"Spotify volume failed: {e}", "#ff6b6b")

    def start_spotify(self):
        """Enable in-app Spotify auto-play"""
        if not self.sp:
            self.set_status("Spotify is not connected.", "#ff6b6b")
            return

        if not self.spotify_has_premium():
            product = (self.spotify_product or "unknown").upper()
            self.set_status(
                f"Spotify account type is {product}. App playback needs Premium.",
                "#ff6b6b",
            )
            return

        if not self.get_preferred_device_id():
            return

        self.autoplay_enabled = True
        self.last_auto_emotion = None
        self.current_mood = None
        self.pending_mood = None
        self.last_playback_track_id = None
        self.queued_track_ids = []
        self.queued_tracks = []
        self.start_spotify_btn.setEnabled(False)
        self.stop_spotify_btn.setEnabled(True)
        self.refresh_queue_display()
        self.set_status("In-app Spotify auto-play enabled. Current song will finish first.", "#1DB954")

    def stop_spotify(self):
        """Disable in-app Spotify auto-play"""
        self.autoplay_enabled = False
        self.current_mood = None
        self.pending_mood = None
        self.last_playback_track_id = None
        self.queued_track_ids = []
        self.queued_tracks = []
        self.start_spotify_btn.setEnabled(True)
        self.stop_spotify_btn.setEnabled(False)
        self.refresh_queue_display()
        self.set_status("In-app Spotify auto-play disabled.", "#b3b3b3")

    def refresh_queue_display(self):
        if not hasattr(self, "queue_list"):
            return

        self.queue_list.clear()

        if self.pending_mood and self.pending_mood != self.current_mood:
            self.queue_list.addItem(f"After this song: switch to {self.pending_mood}")

        if not self.queued_tracks:
            self.queue_list.addItem("No upcoming tracks queued")
            return

        for index, track in enumerate(self.queued_tracks, start=1):
            name = track.get("name", "Unknown")
            artist = track.get("artist", "Unknown")
            mood = track.get("mood", "")
            suffix = f" [{mood}]" if mood else ""
            self.queue_list.addItem(f"{index}. {name} - {artist}{suffix}")

    def refresh_calendar(self):
        if not hasattr(self, "calendar_list"):
            return

        if not os.path.exists("token.pickle") and self.calendar_service is None:
            self.update_calendar_status(
                "Not connected — go to 📅 Calendar in the left menu to connect.",
                "#f39c12",
            )
            return

        self.refresh_calendar_btn.setEnabled(False)
        self.calendar_status.setText("Syncing Google Calendar...")

        if self.calendar_thread is not None and self.calendar_thread.isRunning():
            return

        self.calendar_thread = CalendarEventsThread(service=self.calendar_service)
        self.calendar_thread.update_events.connect(self.update_calendar_events)
        self.calendar_thread.update_status.connect(self.update_calendar_status)
        self.calendar_thread.finished.connect(
            lambda: self.refresh_calendar_btn.setEnabled(True)
        )
        self.calendar_thread.start()

    def create_calendar_event(self):
        title = self.calendar_title_input.text().strip()
        if not title:
            self.update_calendar_status("Event title is required.", "#ff6b6b")
            return

        start_dt = self.calendar_start_input.dateTime().toPyDateTime()
        end_dt = self.calendar_end_input.dateTime().toPyDateTime()
        if end_dt <= start_dt:
            self.update_calendar_status("End time must be after start time.", "#ff6b6b")
            return

        payload = {
            "summary": title,
            "description": self.calendar_description_input.toPlainText().strip(),
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kathmandu"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Kathmandu"},
        }

        location = self.calendar_location_input.text().strip()
        if location:
            payload["location"] = location

        self.create_calendar_btn.setEnabled(False)
        self.update_calendar_status("Creating calendar event...", "#b3b3b3")

        self.calendar_create_thread = CalendarCreateThread(payload, service=self.calendar_service)
        self.calendar_create_thread.update_status.connect(self.update_calendar_status)
        self.calendar_create_thread.created.connect(self.on_calendar_event_created)
        self.calendar_create_thread.finished.connect(
            lambda: self.create_calendar_btn.setEnabled(True)
        )
        self.calendar_create_thread.start()

    def on_calendar_event_created(self):
        self.calendar_title_input.clear()
        self.calendar_location_input.clear()
        self.calendar_description_input.clear()
        self.calendar_start_input.setDateTime(QDateTime.currentDateTime())
        self.calendar_end_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.refresh_calendar()

    def update_calendar_status(self, message: str, color_hex: str):
        if hasattr(self, "calendar_status"):
            self.calendar_status.setText(message)
            self.calendar_status.setStyleSheet(f"color: {color_hex}; font-size: 12px;")

    def update_calendar_events(self, events: list):
        if not hasattr(self, "calendar_list"):
            return

        self.calendar_list.clear()
        if not events:
            self.calendar_list.addItem("No upcoming events")
            return

        for event in events:
            summary = event.get("summary", "Untitled event")
            start_info = event.get("start", {})
            start_value = start_info.get("dateTime", start_info.get("date", ""))
            when = self.format_calendar_time(start_value)
            self.calendar_list.addItem(f"{when}  {summary}")

    def format_calendar_time(self, raw_value: str):
        if not raw_value:
            return "Unknown time"

        if "T" not in raw_value:
            return raw_value

        normalized = raw_value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
            return dt.strftime("%b %d, %I:%M %p")
        except ValueError:
            return raw_value

    def closeEvent(self, event):
        if self.detection_thread is not None:
            self.detection_thread.stop()

        if self.spotify_monitor is not None:
            self.spotify_monitor.stop()

        if self.calendar_thread is not None and self.calendar_thread.isRunning():
            self.calendar_thread.wait()

        if self.calendar_create_thread is not None and self.calendar_create_thread.isRunning():
            self.calendar_create_thread.wait()

        cv2.destroyAllWindows()
        event.accept()


# ============================
# MAIN
# ============================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MoodRippleUI()
    window.show()
    sys.exit(app.exec_())
