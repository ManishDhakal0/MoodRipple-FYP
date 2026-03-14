# ui/pages/dashboard.py
# Main dashboard: camera + emotion bars + Spotify player + Calendar

import os
import json
import time
import random
from datetime import datetime
from pathlib import Path

import numpy as np
import cv2

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QSlider, QListWidget, QScrollArea,
    QLineEdit, QTextEdit, QDateTimeEdit, QFormLayout, QProgressBar,
)
from PyQt5.QtCore import pyqtSignal, Qt, QDateTime
from PyQt5.QtGui import QImage, QPixmap

from core.emotion_thread import EmotionDetectionThread
from core.spotify_thread import SpotifyMonitorThread
from core.calendar_thread import CalendarEventsThread, CalendarCreateThread
from core.constants import EMOTION_TO_MOOD, EMOTION_EMOJIS, MOOD_ICONS, REACTION_MAP


def _ms_to_str(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


class DashboardPage(QWidget):
    """
    Main dashboard.
    Public API:
        set_spotify(sp, display_name, product)
        clear_spotify()
        set_calendar_service(service)
        clear_calendar_service()
    Signal:
        status_changed(message, color_hex)
    """

    status_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.sp               = None
        self.spotify_product  = None
        self.calendar_service = None

        self.detection_thread       = None
        self.spotify_monitor        = None
        self.calendar_thread        = None
        self.calendar_create_thread = None

        self.autoplay_enabled = False
        self.current_mood     = None
        self.pending_mood     = None
        self.last_playback_id = None
        self.queued_ids       = []
        self.queued_tracks    = []
        self.queue_target     = 2

        self.text_detector = None
        self._init_text_detector()

        self._build_ui()

    # ══════════════════════════════════════════════════════════════
    # UI Construction
    # ══════════════════════════════════════════════════════════════
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("panelScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(18, 18, 18, 18)
        cl.setSpacing(12)

        # ── Row 1: Camera (60%) | Emotion analysis (40%) ─────────
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        row1.addWidget(self._build_camera_card(), 6)
        row1.addWidget(self._build_emotion_card(), 4)
        cl.addLayout(row1)

        # ── Row 2: Now Playing (full width) ──────────────────────
        cl.addWidget(self._build_nowplaying_card())

        # ── Row 3: Text emotion (40%) | Calendar (60%) ───────────
        row3 = QHBoxLayout()
        row3.setSpacing(12)
        row3.addWidget(self._build_text_card(), 4)
        row3.addWidget(self._build_calendar_card(), 6)
        cl.addLayout(row3)

        cl.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)

    # ── Card factory helpers ──────────────────────────────────────
    def _card(self, title: str = ""):
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        if title:
            lbl = QLabel(title)
            lbl.setObjectName("cardTitle")
            layout.addWidget(lbl)
        return frame, layout

    def _sep(self):
        line = QFrame()
        line.setObjectName("separator")
        line.setFrameShape(QFrame.HLine)
        return line

    # ──────────────────────────────────────────────────────────────
    # Camera card
    # ──────────────────────────────────────────────────────────────
    def _build_camera_card(self):
        frame, layout = self._card("LIVE DETECTION")

        self.camera_label = QLabel("Camera will appear here\nwhen detection starts")
        self.camera_label.setObjectName("cameraFeed")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(340, 250)
        self.camera_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.camera_label, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.start_btn = QPushButton("▶  Start Detection")
        self.start_btn.setObjectName("primaryButton")
        self.start_btn.clicked.connect(self.start_detection)

        self.stop_btn = QPushButton("⏹  Stop")
        self.stop_btn.setObjectName("secondaryButton")
        self.stop_btn.clicked.connect(self.stop_detection)
        self.stop_btn.setEnabled(False)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return frame

    # ──────────────────────────────────────────────────────────────
    # Emotion analysis card
    # ──────────────────────────────────────────────────────────────
    def _build_emotion_card(self):
        frame, layout = self._card("EMOTION ANALYSIS")
        layout.setAlignment(Qt.AlignTop)

        self.emotion_emoji = QLabel("😐")
        self.emotion_emoji.setObjectName("emotionEmoji")
        self.emotion_emoji.setAlignment(Qt.AlignCenter)

        self.emotion_name = QLabel("Neutral")
        self.emotion_name.setObjectName("emotionName")
        self.emotion_name.setAlignment(Qt.AlignCenter)

        self.emotion_conf = QLabel("Confidence: —")
        self.emotion_conf.setObjectName("emotionConf")
        self.emotion_conf.setAlignment(Qt.AlignCenter)

        self.mood_badge = QLabel("🎯  Focused")
        self.mood_badge.setObjectName("moodBadge")
        self.mood_badge.setAlignment(Qt.AlignCenter)
        self.mood_badge.setFixedHeight(30)

        self.reaction_lbl = QLabel("Steady mood. Balanced vibe.")
        self.reaction_lbl.setObjectName("reactionText")
        self.reaction_lbl.setAlignment(Qt.AlignCenter)
        self.reaction_lbl.setWordWrap(True)

        layout.addWidget(self.emotion_emoji)
        layout.addWidget(self.emotion_name)
        layout.addWidget(self.emotion_conf)
        layout.addWidget(self.mood_badge)
        layout.addWidget(self.reaction_lbl)
        layout.addWidget(self._sep())

        # Mood distribution bars
        dist_lbl = QLabel("MOOD DISTRIBUTION")
        dist_lbl.setObjectName("cardTitle")
        layout.addWidget(dist_lbl)

        self.bar_energized, self.pct_energized = self._bar_row(layout, "ENERGIZED", "barEnergized")
        self.bar_focused,   self.pct_focused   = self._bar_row(layout, "FOCUSED",   "barFocused")
        self.bar_calm,      self.pct_calm      = self._bar_row(layout, "CALM",      "barCalm")
        layout.addStretch()
        return frame

    def _bar_row(self, parent_layout, label_text: str, bar_id: str):
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 2, 0, 2)
        rl.setSpacing(8)

        lbl = QLabel(label_text)
        lbl.setObjectName("barLabel")
        lbl.setFixedWidth(70)

        bar = QProgressBar()
        bar.setObjectName(bar_id)
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)

        pct = QLabel("0%")
        pct.setObjectName("barPct")
        pct.setFixedWidth(32)
        pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        rl.addWidget(lbl)
        rl.addWidget(bar, 1)
        rl.addWidget(pct)
        parent_layout.addWidget(row)
        return bar, pct

    # ──────────────────────────────────────────────────────────────
    # Now Playing card
    # ──────────────────────────────────────────────────────────────
    def _build_nowplaying_card(self):
        frame, layout = self._card("NOW PLAYING")

        main_row = QHBoxLayout()
        main_row.setSpacing(20)

        # Album art
        self.album_art = QLabel("🎵")
        self.album_art.setObjectName("albumArt")
        self.album_art.setAlignment(Qt.AlignCenter)
        self.album_art.setFixedSize(78, 78)
        main_row.addWidget(self.album_art, 0, Qt.AlignTop)

        # Center: track info + progress + controls
        center = QVBoxLayout()
        center.setSpacing(6)

        self.track_name_lbl = QLabel("Nothing playing")
        self.track_name_lbl.setObjectName("trackName")

        self.track_artist_lbl = QLabel("Connect Spotify to see playback")
        self.track_artist_lbl.setObjectName("trackArtist")

        center.addWidget(self.track_name_lbl)
        center.addWidget(self.track_artist_lbl)
        center.addSpacing(2)

        # Progress bar + time labels
        self.track_progress = QProgressBar()
        self.track_progress.setObjectName("trackProgress")
        self.track_progress.setRange(0, 1000)
        self.track_progress.setValue(0)
        self.track_progress.setTextVisible(False)

        time_row = QHBoxLayout()
        self.time_elapsed = QLabel("0:00")
        self.time_elapsed.setObjectName("timeLabel")
        self.time_total = QLabel("0:00")
        self.time_total.setObjectName("timeLabel")
        time_row.addWidget(self.time_elapsed)
        time_row.addStretch()
        time_row.addWidget(self.time_total)

        center.addWidget(self.track_progress)
        center.addLayout(time_row)

        # Controls
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)
        ctrl_row.setAlignment(Qt.AlignLeft)

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setObjectName("controlButton")
        self.prev_btn.clicked.connect(self._prev_track)
        self.prev_btn.setEnabled(False)

        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setObjectName("playButton")
        self.play_pause_btn.clicked.connect(self._toggle_play_pause)
        self.play_pause_btn.setEnabled(False)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setObjectName("controlButton")
        self.next_btn.clicked.connect(self._next_track)
        self.next_btn.setEnabled(False)

        ctrl_row.addWidget(self.prev_btn)
        ctrl_row.addWidget(self.play_pause_btn)
        ctrl_row.addWidget(self.next_btn)
        center.addLayout(ctrl_row)

        main_row.addLayout(center, 1)

        # Right: volume + status + autoplay buttons
        right_col = QVBoxLayout()
        right_col.setSpacing(8)
        right_col.setAlignment(Qt.AlignTop)

        vol_row = QHBoxLayout()
        vol_row.setSpacing(8)
        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("font-size: 12px; color: #3d4f6a;")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setEnabled(False)
        self.volume_slider.valueChanged.connect(self._change_volume)
        self.volume_slider.setFixedWidth(120)
        vol_row.addWidget(vol_icon)
        vol_row.addWidget(self.volume_slider)
        right_col.addLayout(vol_row)

        self.spotify_status_lbl = QLabel("Not connected")
        self.spotify_status_lbl.setObjectName("spotifyStatus")
        self.spotify_status_lbl.setWordWrap(True)
        right_col.addWidget(self.spotify_status_lbl)

        right_col.addStretch()

        self.start_autoplay_btn = QPushButton("▶  Auto-Play On")
        self.start_autoplay_btn.setObjectName("greenButton")
        self.start_autoplay_btn.clicked.connect(self._start_autoplay)

        self.stop_autoplay_btn = QPushButton("⏹  Auto-Play Off")
        self.stop_autoplay_btn.setObjectName("secondaryButton")
        self.stop_autoplay_btn.clicked.connect(self._stop_autoplay)
        self.stop_autoplay_btn.setEnabled(False)

        right_col.addWidget(self.start_autoplay_btn)
        right_col.addWidget(self.stop_autoplay_btn)

        main_row.addLayout(right_col)
        layout.addLayout(main_row)

        # Queue
        layout.addWidget(self._sep())
        queue_hdr = QLabel("UP NEXT")
        queue_hdr.setObjectName("cardTitle")
        layout.addWidget(queue_hdr)

        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(80)
        self.queue_list.addItem("Queue will appear when auto-play is active")
        layout.addWidget(self.queue_list)
        return frame

    # ──────────────────────────────────────────────────────────────
    # Text emotion card
    # ──────────────────────────────────────────────────────────────
    def _build_text_card(self):
        frame, layout = self._card("TEXT EMOTION")

        self.text_status_lbl = QLabel("Type below when camera detection is off")
        self.text_status_lbl.setObjectName("subText")
        self.text_status_lbl.setWordWrap(True)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("How are you feeling right now?")
        self.text_input.setFixedHeight(90)

        self.text_result = QLabel("—")
        self.text_result.setObjectName("subText")
        self.text_result.setWordWrap(True)

        self.text_analyze_btn = QPushButton("Analyze Text Mood")
        self.text_analyze_btn.setObjectName("primaryButton")
        self.text_analyze_btn.clicked.connect(self.analyze_text_emotion)

        layout.addWidget(self.text_status_lbl)
        layout.addWidget(self.text_input)
        layout.addWidget(self.text_result)
        layout.addWidget(self.text_analyze_btn)
        layout.addStretch()
        return frame

    # ──────────────────────────────────────────────────────────────
    # Calendar card
    # ──────────────────────────────────────────────────────────────
    def _build_calendar_card(self):
        frame, layout = self._card("GOOGLE CALENDAR")

        self.cal_status_lbl = QLabel("Not connected — go to 📅 Calendar page")
        self.cal_status_lbl.setObjectName("subText")
        self.cal_status_lbl.setWordWrap(True)

        self.cal_list = QListWidget()
        self.cal_list.setMinimumHeight(120)
        self.cal_list.setMaximumHeight(170)
        self.cal_list.addItem("No events loaded")

        self.refresh_cal_btn = QPushButton("Refresh Events")
        self.refresh_cal_btn.setObjectName("secondaryButton")
        self.refresh_cal_btn.clicked.connect(self.refresh_calendar)

        layout.addWidget(self.cal_status_lbl)
        layout.addWidget(self.cal_list)
        layout.addWidget(self.refresh_cal_btn)
        layout.addWidget(self._sep())

        add_hdr = QLabel("ADD EVENT")
        add_hdr.setObjectName("cardTitle")
        layout.addWidget(add_hdr)

        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 0)
        form.setSpacing(8)

        self.cal_title_input = QLineEdit()
        self.cal_title_input.setPlaceholderText("Event title")

        self.cal_start_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.cal_start_input.setCalendarPopup(True)
        self.cal_start_input.setDisplayFormat("MMM d, yyyy  HH:mm")

        self.cal_end_input = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.cal_end_input.setCalendarPopup(True)
        self.cal_end_input.setDisplayFormat("MMM d, yyyy  HH:mm")

        self.cal_location_input = QLineEdit()
        self.cal_location_input.setPlaceholderText("Location (optional)")

        self.cal_desc_input = QTextEdit()
        self.cal_desc_input.setPlaceholderText("Notes (optional)")
        self.cal_desc_input.setFixedHeight(60)

        for lbl_text, widget in [
            ("Title",    self.cal_title_input),
            ("Start",    self.cal_start_input),
            ("End",      self.cal_end_input),
            ("Location", self.cal_location_input),
            ("Notes",    self.cal_desc_input),
        ]:
            lbl = QLabel(lbl_text)
            lbl.setObjectName("formLabel")
            form.addRow(lbl, widget)

        layout.addLayout(form)

        self.create_event_btn = QPushButton("Create Event")
        self.create_event_btn.setObjectName("primaryButton")
        self.create_event_btn.clicked.connect(self.create_calendar_event)
        layout.addWidget(self.create_event_btn)
        return frame

    # ══════════════════════════════════════════════════════════════
    # Public API
    # ══════════════════════════════════════════════════════════════
    def set_spotify(self, sp, display_name: str, product: str):
        self.sp              = sp
        self.spotify_product = product
        color = "#10b981" if product.lower() == "premium" else "#f59e0b"
        self.spotify_status_lbl.setText(f"● {display_name}  ({product.capitalize()})")
        self.spotify_status_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        self._start_spotify_monitor()

    def clear_spotify(self):
        self.sp = None
        self.spotify_status_lbl.setText("Not connected")
        self.spotify_status_lbl.setStyleSheet("")
        for btn in (self.play_pause_btn, self.prev_btn, self.next_btn):
            btn.setEnabled(False)
        self.volume_slider.setEnabled(False)
        if self.spotify_monitor:
            self.spotify_monitor.stop()
            self.spotify_monitor = None

    def set_calendar_service(self, service):
        self.calendar_service = service
        self.cal_status_lbl.setText("● Google Calendar connected")
        self.cal_status_lbl.setStyleSheet("color: #10b981; font-size: 12px;")
        self.refresh_calendar()

    def clear_calendar_service(self):
        self.calendar_service = None
        self.cal_status_lbl.setText("Not connected — go to 📅 Calendar page")
        self.cal_status_lbl.setStyleSheet("")

    # ══════════════════════════════════════════════════════════════
    # Detection
    # ══════════════════════════════════════════════════════════════
    def start_detection(self):
        if self.detection_thread and self.detection_thread.isRunning():
            return
        self.detection_thread = EmotionDetectionThread()
        self.detection_thread.frame_ready.connect(self._on_frame)
        self.detection_thread.emotion_ready.connect(self._on_emotion)
        self.detection_thread.scores_ready.connect(self._on_scores)
        self.detection_thread.status_changed.connect(self.status_changed)

        if not self.detection_thread.load_model():
            self.status_changed.emit("❌ Model failed to load.", "#ef4444")
            return

        self.detection_thread.is_running = True
        self.detection_thread.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_changed.emit("✅ Detection started.", "#10b981")

    def stop_detection(self):
        if self.detection_thread:
            self.detection_thread.stop()
            self.detection_thread = None
        self.camera_label.clear()
        self.camera_label.setText("Camera will appear here\nwhen detection starts")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_changed.emit("⏹ Detection stopped.", "#3d4f6a")

    def _on_frame(self, frame: np.ndarray):
        h, w, ch = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self.camera_label.width(), self.camera_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.camera_label.setPixmap(pix)

    def _on_emotion(self, emotion: str, confidence: float, mood: str):
        emoji = EMOTION_EMOJIS.get(emotion, "😐")
        icon  = MOOD_ICONS.get(mood, "🎯")
        react = REACTION_MAP.get(emotion, "")
        self.emotion_emoji.setText(emoji)
        self.emotion_name.setText(emotion.capitalize())
        self.emotion_conf.setText(f"Confidence: {confidence * 100:.1f}%")
        self.mood_badge.setText(f"{icon}  {mood.capitalize()}")
        self.reaction_lbl.setText(react)
        if self.autoplay_enabled:
            self.pending_mood = mood
            self._refresh_queue_display()
            if self.current_mood is None:
                self._sync_autoplay(force_replace=False)

    def _on_scores(self, scores: dict):
        """Update 3 mood score bars with normalised values from the thread."""
        e_val = int(scores.get("happy",   0.0) * 100)
        f_val = int(scores.get("neutral", 0.0) * 100)
        c_val = int(scores.get("sad",     0.0) * 100)
        self.bar_energized.setValue(e_val)
        self.pct_energized.setText(f"{e_val}%")
        self.bar_focused.setValue(f_val)
        self.pct_focused.setText(f"{f_val}%")
        self.bar_calm.setValue(c_val)
        self.pct_calm.setText(f"{c_val}%")

    # ══════════════════════════════════════════════════════════════
    # Text emotion
    # ══════════════════════════════════════════════════════════════
    def _init_text_detector(self):
        try:
            from text_emotion import TextEmotionDetector
            self.text_detector = TextEmotionDetector()
        except Exception:
            self.text_detector = None

    def analyze_text_emotion(self):
        if self.detection_thread and self.detection_thread.isRunning():
            self.text_status_lbl.setText("Stop camera detection first to use text fallback.")
            self.text_status_lbl.setStyleSheet("color: #f59e0b; font-size: 12px;")
            return
        if not self.text_detector:
            self.text_status_lbl.setText("Text model unavailable — run text_emotion_train.py first.")
            self.text_status_lbl.setStyleSheet("color: #ef4444; font-size: 12px;")
            return
        text = self.text_input.toPlainText().strip()
        if not text:
            self.text_status_lbl.setText("Enter some text first.")
            self.text_status_lbl.setStyleSheet("color: #ef4444; font-size: 12px;")
            return

        result     = self.text_detector.predict(text)
        emotion    = result["emotion"]
        confidence = result["confidence"]
        mood       = EMOTION_TO_MOOD.get(emotion, "focused")
        self.text_result.setText(f"Result: {emotion.capitalize()} ({confidence * 100:.1f}%)")
        self.text_status_lbl.setText("Text emotion is now driving mood.")
        self.text_status_lbl.setStyleSheet("color: #10b981; font-size: 12px;")

        payload = {
            "emotion": emotion, "confidence": float(confidence),
            "timestamp_unix": int(time.time()), "source": "text",
        }
        Path("latest_emotion.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._on_emotion(emotion, confidence, mood)

    # ══════════════════════════════════════════════════════════════
    # Spotify
    # ══════════════════════════════════════════════════════════════
    def _start_spotify_monitor(self):
        if self.sp and (not self.spotify_monitor or not self.spotify_monitor.isRunning()):
            self.spotify_monitor = SpotifyMonitorThread(self.sp)
            self.spotify_monitor.playback_updated.connect(self._on_playback)
            self.spotify_monitor.is_running = True
            self.spotify_monitor.start()
            for btn in (self.play_pause_btn, self.prev_btn, self.next_btn):
                btn.setEnabled(True)
            self.volume_slider.setEnabled(True)

    def _on_playback(self, info: dict):
        prev_id    = self.last_playback_id
        current_id = info.get("track_id")
        self.track_name_lbl.setText(info["track"])
        self.track_artist_lbl.setText(info["artist"])
        self.play_pause_btn.setText("⏸" if info["is_playing"] else "▶")

        progress = info.get("progress_ms", 0)
        duration = info.get("duration_ms", 0)
        if duration:
            self.track_progress.setValue(int(progress / duration * 1000))
            self.time_elapsed.setText(_ms_to_str(progress))
            self.time_total.setText(_ms_to_str(duration))

        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(info["volume"])
        self.volume_slider.blockSignals(False)

        if current_id:
            self.last_playback_id = current_id
        if prev_id and current_id and current_id != prev_id:
            self.queued_ids    = [i for i in self.queued_ids    if i != current_id]
            self.queued_tracks = [t for t in self.queued_tracks if t.get("id") != current_id]
            self._refresh_queue_display()
            if self.autoplay_enabled:
                self._sync_autoplay(force_replace=False)

    def _toggle_play_pause(self):
        if not self.sp:
            return
        try:
            cur = self.sp.current_playback()
            if cur and cur.get("is_playing"):
                self.sp.pause_playback()
            else:
                dev = self._preferred_device()
                if dev:
                    self.sp.start_playback(device_id=dev)
        except Exception as e:
            self.status_changed.emit(f"Play/pause error: {e}", "#ef4444")

    def _next_track(self):
        if self.sp:
            try:
                self.sp.next_track()
            except Exception as e:
                self.status_changed.emit(f"Next track error: {e}", "#ef4444")

    def _prev_track(self):
        if self.sp:
            try:
                self.sp.previous_track()
            except Exception as e:
                self.status_changed.emit(f"Prev track error: {e}", "#ef4444")

    def _change_volume(self, val):
        if self.sp:
            try:
                self.sp.volume(val)
            except Exception:
                pass

    def _preferred_device(self):
        if not self.sp:
            return None
        try:
            devices = self.sp.devices().get("devices", [])
        except Exception as e:
            self.status_changed.emit(f"Cannot read Spotify devices: {e}", "#ef4444")
            return None
        if not devices:
            self.status_changed.emit(
                "Open Spotify on your computer and play a song first.", "#ef4444"
            )
            return None
        for matcher in (
            lambda d: d.get("type") == "Computer" and d.get("is_active"),
            lambda d: d.get("type") == "Computer",
            lambda d: d.get("is_active"),
            lambda d: True,
        ):
            dev = next((d for d in devices if matcher(d)), None)
            if dev:
                return dev.get("id")
        return None

    def _is_premium(self) -> bool:
        return (self.spotify_product or "").lower() == "premium"

    def _mood_tracks(self, mood: str, n: int = 5):
        if not self.sp:
            return []
        try:
            recent = self.sp.current_user_recently_played(limit=50)
            tracks = [item["track"] for item in recent.get("items", [])]
            if not tracks:
                top = self.sp.current_user_top_tracks(limit=50, time_range="short_term")
                tracks = top.get("items", [])
            seen, unique = set(), []
            for t in tracks:
                tid = t.get("id")
                if tid and not t.get("is_local") and tid not in seen:
                    unique.append(t)
                    seen.add(tid)
            random.seed(mood)
            random.shuffle(unique)
            return unique[:n]
        except Exception as e:
            self.status_changed.emit(f"Cannot build Spotify queue: {e}", "#ef4444")
            return []

    def _start_playback(self, uris):
        dev = self._preferred_device()
        if not dev:
            return False
        try:
            self.sp.transfer_playback(device_id=dev, force_play=False)
            time.sleep(0.8)
            self.sp.start_playback(device_id=dev, uris=uris)
            return True
        except Exception as e:
            self.status_changed.emit(f"Spotify playback failed: {e}", "#ef4444")
            return False

    def _queue_tracks(self, mood: str, count: int = 1) -> int:
        if not self.sp or count <= 0:
            return 0
        dev = self._preferred_device()
        if not dev:
            return 0
        tracks = self._mood_tracks(mood, n=max(count + len(self.queued_ids), 8))
        added = 0
        for track in tracks:
            uri, tid = track.get("uri"), track.get("id")
            if not uri or not tid or tid == self.last_playback_id or tid in self.queued_ids:
                continue
            try:
                self.sp.add_to_queue(uri, device_id=dev)
            except Exception:
                continue
            self.queued_ids.append(tid)
            artist = track["artists"][0]["name"] if track.get("artists") else "Unknown"
            self.queued_tracks.append({
                "id": tid, "name": track.get("name", "Unknown"),
                "artist": artist, "mood": mood,
            })
            added += 1
            if added >= count:
                break
        self._refresh_queue_display()
        return added

    def _start_autoplay(self):
        if not self.sp:
            self.status_changed.emit("Spotify not connected.", "#ef4444")
            return
        if not self._is_premium():
            self.status_changed.emit("Spotify Premium required for playback control.", "#f59e0b")
            return
        if not self._preferred_device():
            return
        self.autoplay_enabled = True
        self.current_mood = self.pending_mood = None
        self.last_playback_id = None
        self.queued_ids = self.queued_tracks = []
        self.start_autoplay_btn.setEnabled(False)
        self.stop_autoplay_btn.setEnabled(True)
        self._refresh_queue_display()
        self.status_changed.emit("Auto-play enabled.", "#10b981")

    def _stop_autoplay(self):
        self.autoplay_enabled = False
        self.current_mood = self.pending_mood = None
        self.last_playback_id = None
        self.queued_ids = self.queued_tracks = []
        self.start_autoplay_btn.setEnabled(True)
        self.stop_autoplay_btn.setEnabled(False)
        self._refresh_queue_display()
        self.status_changed.emit("Auto-play disabled.", "#3d4f6a")

    def _sync_autoplay(self, force_replace: bool = False):
        if not self.autoplay_enabled or not self.sp:
            return
        target = self.pending_mood or self.current_mood
        if not target:
            return
        try:
            current = self.sp.current_playback()
        except Exception as e:
            self.status_changed.emit(f"Cannot read Spotify: {e}", "#ef4444")
            return
        has_track = bool(current and current.get("item") and current["item"].get("id"))
        if not has_track or force_replace:
            tracks = self._mood_tracks(target, n=max(self.queue_target, 3))
            uris   = [t["uri"] for t in tracks if t.get("uri")]
            if not uris:
                return
            if self._start_playback(uris[:self.queue_target]):
                first = tracks[0]
                self.current_mood     = target
                self.pending_mood     = None
                self.last_playback_id = first.get("id")
                self.queued_ids       = [t.get("id") for t in tracks[1:self.queue_target] if t.get("id")]
                self.queued_tracks    = []
                for t in tracks[1:self.queue_target]:
                    if not t.get("id"):
                        continue
                    artist = t["artists"][0]["name"] if t.get("artists") else "Unknown"
                    self.queued_tracks.append({
                        "id": t["id"], "name": t.get("name", "Unknown"),
                        "artist": artist, "mood": target,
                    })
                self.track_name_lbl.setText(first["name"])
                self.track_artist_lbl.setText(
                    first["artists"][0]["name"] if first.get("artists") else ""
                )
                self._refresh_queue_display()
                self.status_changed.emit(f"Auto-play: {target} music.", "#10b981")
            return
        if self.pending_mood and self.pending_mood != self.current_mood:
            self.current_mood  = self.pending_mood
            self.pending_mood  = None
            self.queued_ids = self.queued_tracks = []
            added = self._queue_tracks(self.current_mood, count=self.queue_target)
            if added:
                self.status_changed.emit(f"Mood changed → {self.current_mood}.", "#10b981")
            return
        missing = max(0, self.queue_target - len(self.queued_ids))
        if missing:
            self._queue_tracks(target, count=missing)

    def _refresh_queue_display(self):
        self.queue_list.clear()
        if self.pending_mood and self.pending_mood != self.current_mood:
            self.queue_list.addItem(f"After this song: switching to {self.pending_mood}")
        if not self.queued_tracks:
            self.queue_list.addItem("No upcoming tracks queued")
            return
        for i, t in enumerate(self.queued_tracks, 1):
            mood_tag = f" [{t['mood']}]" if t.get("mood") else ""
            self.queue_list.addItem(f"{i}. {t['name']} — {t['artist']}{mood_tag}")

    # ══════════════════════════════════════════════════════════════
    # Calendar
    # ══════════════════════════════════════════════════════════════
    def refresh_calendar(self):
        if not self.calendar_service and not os.path.exists("token.pickle"):
            self.cal_status_lbl.setText("Not connected — go to 📅 Calendar page to connect.")
            return
        self.refresh_cal_btn.setEnabled(False)
        self.cal_status_lbl.setText("Syncing…")
        if self.calendar_thread and self.calendar_thread.isRunning():
            return
        self.calendar_thread = CalendarEventsThread(service=self.calendar_service)
        self.calendar_thread.events_ready.connect(self._on_calendar_events)
        self.calendar_thread.status_changed.connect(self._on_cal_status)
        self.calendar_thread.finished.connect(lambda: self.refresh_cal_btn.setEnabled(True))
        self.calendar_thread.start()

    def create_calendar_event(self):
        title = self.cal_title_input.text().strip()
        if not title:
            self._on_cal_status("Event title is required.", "#ef4444")
            return
        start_dt = self.cal_start_input.dateTime().toPyDateTime()
        end_dt   = self.cal_end_input.dateTime().toPyDateTime()
        if end_dt <= start_dt:
            self._on_cal_status("End time must be after start time.", "#ef4444")
            return
        payload = {
            "summary":     title,
            "description": self.cal_desc_input.toPlainText().strip(),
            "start":       {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kathmandu"},
            "end":         {"dateTime": end_dt.isoformat(),   "timeZone": "Asia/Kathmandu"},
        }
        loc = self.cal_location_input.text().strip()
        if loc:
            payload["location"] = loc
        self.create_event_btn.setEnabled(False)
        self._on_cal_status("Creating event…", "#3d4f6a")
        self.calendar_create_thread = CalendarCreateThread(payload, service=self.calendar_service)
        self.calendar_create_thread.status_changed.connect(self._on_cal_status)
        self.calendar_create_thread.created.connect(self._on_event_created)
        self.calendar_create_thread.finished.connect(lambda: self.create_event_btn.setEnabled(True))
        self.calendar_create_thread.start()

    def _on_event_created(self):
        self.cal_title_input.clear()
        self.cal_location_input.clear()
        self.cal_desc_input.clear()
        self.cal_start_input.setDateTime(QDateTime.currentDateTime())
        self.cal_end_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.refresh_calendar()

    def _on_cal_status(self, msg: str, color: str):
        self.cal_status_lbl.setText(msg)
        self.cal_status_lbl.setStyleSheet(f"color: {color}; font-size: 12px;")
        self.status_changed.emit(msg, color)

    def _on_calendar_events(self, events: list):
        self.cal_list.clear()
        if not events:
            self.cal_list.addItem("No upcoming events")
            return
        for ev in events:
            summary = ev.get("summary", "Untitled")
            start   = ev.get("start", {})
            raw     = start.get("dateTime", start.get("date", ""))
            self.cal_list.addItem(f"{self._fmt_time(raw)}  ·  {summary}")

    @staticmethod
    def _fmt_time(raw: str) -> str:
        if not raw:
            return "?"
        if "T" not in raw:
            return raw
        try:
            return datetime.fromisoformat(
                raw.replace("Z", "+00:00")
            ).strftime("%b %d  %I:%M %p")
        except ValueError:
            return raw

    # ══════════════════════════════════════════════════════════════
    # Cleanup
    # ══════════════════════════════════════════════════════════════
    def shutdown(self):
        if self.detection_thread:
            self.detection_thread.stop()
        if self.spotify_monitor:
            self.spotify_monitor.stop()
        if self.calendar_thread and self.calendar_thread.isRunning():
            self.calendar_thread.wait()
        if self.calendar_create_thread and self.calendar_create_thread.isRunning():
            self.calendar_create_thread.wait()
        cv2.destroyAllWindows()
