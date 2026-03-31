# ui/pages/dashboard.py
# DashboardPage — glassmorphism layout.
# Left: camera glass panel + text emotion panel.
# Right (scrollable): emotion display + mood stats + now playing + calendar.
# All cards are GlassCard instances (transparent with painted fill + shimmer edge).

import os

import cv2

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QSlider, QListWidget, QScrollArea,
    QTextEdit, QProgressBar,
)
from PyQt5.QtCore    import pyqtSignal, Qt
from PyQt5.QtGui     import QColor

from core.emotion_db        import EmotionDB
from core.settings_manager  import SettingsManager

from ui.components.glass_card        import GlassCard
from ui.components.detection_mixin   import DetectionMixin
from ui.components.spotify_autoplay  import SpotifyAutoplayMixin
from ui.components.calendar_mixin    import CalendarMixin


def _set_label_color(label, color: str, size: str = "12px"):
    css = f"color: {color}; font-size: {size};"
    if label.styleSheet() != css:
        label.setStyleSheet(css)


# ── Shared style constants ─────────────────────────────────────────────────────
_C1 = "#e8ecf0"                      # primary text
_C2 = "rgba(232,236,240,0.48)"       # secondary text
_C3 = "rgba(232,236,240,0.24)"       # tertiary / hint text
_CA = "#F5C518"                       # yellow accent

_BTN_PRI = """
    QPushButton {
        background: rgba(245,197,24,0.12);
        color: #F5C518;
        border: 1px solid rgba(245,197,24,0.24);
        border-radius: 100px;
        font-size: 12px; font-weight: 600;
        padding: 0 18px; min-height: 32px;
    }
    QPushButton:hover  { background: rgba(245,197,24,0.20); border-color: rgba(245,197,24,0.40); }
    QPushButton:disabled { color: rgba(245,197,24,0.28); background: rgba(245,197,24,0.05);
                           border-color: rgba(245,197,24,0.10); }
"""
_BTN_SEC = """
    QPushButton {
        background: rgba(255,255,255,0.07);
        color: rgba(232,236,240,0.55);
        border: none;
        border-radius: 100px;
        font-size: 12px;
        padding: 0 16px; min-height: 32px;
    }
    QPushButton:hover    { background: rgba(255,255,255,0.12); color: #e8ecf0; }
    QPushButton:disabled { color: rgba(232,236,240,0.20); background: rgba(255,255,255,0.03); }
    QPushButton:checked  { background: rgba(245,197,24,0.12); color: #F5C518;
                           border: 1px solid rgba(245,197,24,0.22); }
"""
_BTN_ICO = """
    QPushButton {
        background: rgba(255,255,255,0.08);
        color: rgba(232,236,240,0.72);
        border: none; border-radius: 100px;
        font-size: 14px;
        min-width: 36px; max-width: 36px;
        min-height: 36px; max-height: 36px;
        padding: 0;
    }
    QPushButton:hover    { background: rgba(255,255,255,0.14); color: #e8ecf0; }
    QPushButton:disabled { color: rgba(232,236,240,0.18); background: rgba(255,255,255,0.03); }
"""
_BTN_ICO_LG = """
    QPushButton {
        background: rgba(255,255,255,0.10);
        color: rgba(232,236,240,0.80);
        border: none; border-radius: 100px;
        font-size: 16px;
        min-width: 44px; max-width: 44px;
        min-height: 44px; max-height: 44px;
        padding: 0;
    }
    QPushButton:hover { background: rgba(255,255,255,0.16); color: #e8ecf0; }
"""
_BAR_BASE = """
    QProgressBar {
        background: rgba(255,255,255,0.08);
        border: none; border-radius: 4px;
        min-height: 7px; max-height: 7px;
    }
"""
_LIST_QSS = """
    QListWidget {
        background: rgba(255,255,255,0.04);
        border: none; border-radius: 12px;
        padding: 4px; font-size: 11px;
        color: rgba(232,236,240,0.45); outline: none;
    }
    QListWidget::item { padding: 6px 10px; border-radius: 7px; }
    QListWidget::item:hover    { background: rgba(255,255,255,0.07); color: #e8ecf0; }
    QListWidget::item:selected { background: rgba(245,197,24,0.12); color: #F5C518; }
"""
_TEXT_INPUT_QSS = """
    QTextEdit {
        background: rgba(255,255,255,0.06);
        color: #e8ecf0; border: none;
        border-radius: 14px; padding: 12px 16px; font-size: 13px;
        selection-background-color: rgba(245,197,24,0.22);
    }
    QTextEdit:focus { background: rgba(255,255,255,0.09); }
"""
_SLIDER_QSS = """
    QSlider::groove:horizontal {
        background: rgba(255,255,255,0.10);
        border: none; height: 4px; border-radius: 2px;
    }
    QSlider::handle:horizontal {
        background: #F5C518; width: 12px; height: 12px;
        border-radius: 6px; margin: -4px 0; border: none;
    }
    QSlider::sub-page:horizontal {
        background: #F5C518; border-radius: 2px;
    }
"""


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        "font-size: 10px; font-weight: 700; color: rgba(232,236,240,0.28);"
        " letter-spacing: 2.5px; background: transparent;")
    return lbl


def _bar_row(label_text: str, accent: str):
    """Returns (HBoxLayout, QProgressBar, pct_QLabel)."""
    row = QHBoxLayout()
    row.setSpacing(10)
    lbl = QLabel(label_text)
    lbl.setFixedWidth(70)
    lbl.setStyleSheet(f"font-size: 11px; color: {_C2}; background: transparent;")
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(0)
    bar.setTextVisible(False)
    bar.setStyleSheet(
        _BAR_BASE + f"QProgressBar::chunk {{ background: {accent}; border-radius: 3px; }}")
    pct = QLabel("0%")
    pct.setFixedWidth(34)
    pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    pct.setStyleSheet(f"font-size: 11px; color: {_C3}; background: transparent;")
    row.addWidget(lbl)
    row.addWidget(bar, 1)
    row.addWidget(pct)
    return row, bar, pct


def _metric_tile(label_text: str):
    """Returns (QFrame tile, value QLabel)."""
    tile = QFrame()
    tile.setStyleSheet("""
        QFrame {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
        }
    """)
    tl = QVBoxLayout(tile)
    tl.setContentsMargins(8, 8, 8, 8)
    tl.setSpacing(3)
    val = QLabel("—")
    val.setAlignment(Qt.AlignCenter)
    val.setStyleSheet(
        f"font-size: 13px; font-weight: 700; color: {_C1}; background: transparent;")
    lbl = QLabel(label_text)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(
        f"font-size: 8px; font-weight: 600; color: {_C3}; letter-spacing: 0.5px;"
        " background: transparent;")
    tl.addWidget(val)
    tl.addWidget(lbl)
    return tile, val


# ══════════════════════════════════════════════════════════════════════════════
class DashboardPage(QWidget, DetectionMixin, SpotifyAutoplayMixin, CalendarMixin):
    status_changed   = pyqtSignal(str, str)
    emotion_detected = pyqtSignal(str, str)   # (emotion, mood) — 60s cooldown in mixin

    def __init__(self, parent=None):
        super().__init__(parent)

        self.sp               = None
        self.spotify_product  = None
        self.spotify_monitor  = None
        self.calendar_service = None
        self.calendar_thread  = None
        self.detection_thread = None
        self.autoplay_enabled = False
        self.current_mood     = None
        self.pending_mood     = None
        self.last_playback_id = None
        self.queued_ids:    list = []
        self.queued_tracks: list = []
        self.queue_target   = 2
        self.text_detector       = None
        self._text_thread        = None
        self._prev_playback:dict = {}
        self._was_drowsy         = False
        self._music_prefs: dict  = {"source": "favourites", "language": "all"}
        self._mood_candidate: str   = None
        self._mood_candidate_since  = 0.0
        self._db                 = EmotionDB()
        self._mood_widget        = None

        self._init_text_detector()
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setStyleSheet("DashboardPage { background: transparent; }")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(24, 18, 24, 18)
        outer.setSpacing(18)

        # ── Left column — camera + text ──────────────────────────────────────
        left = QWidget()
        left.setStyleSheet("background: transparent;")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(14)
        lv.addWidget(self._build_camera_panel(), 1)
        lv.addWidget(self._build_text_panel())
        outer.addWidget(left, 3)

        # ── Right column — scrollable stacked glass cards ────────────────────
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }")
        right_scroll.viewport().setStyleSheet("background: transparent;")

        right_content = QWidget()
        right_content.setStyleSheet("background: transparent;")
        rv = QVBoxLayout(right_content)
        rv.setContentsMargins(0, 0, 4, 0)
        rv.setSpacing(14)
        rv.addWidget(self._build_emotion_panel())
        rv.addWidget(self._build_moodstats_panel())
        rv.addWidget(self._build_nowplaying_panel())
        rv.addWidget(self._build_calendar_panel())
        rv.addStretch()

        right_scroll.setWidget(right_content)
        outer.addWidget(right_scroll, 2)

    # ══════════════════════════════════════════════════════════════════════════
    # Camera Panel
    # ══════════════════════════════════════════════════════════════════════════
    def _build_camera_panel(self) -> GlassCard:
        card = GlassCard(radius=22)
        card.setMinimumHeight(360)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Camera feed label ─────────────────────────────────────────────────
        self.camera_label = QLabel()
        self.camera_label.setObjectName("cameraFeed")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(280, 200)
        self.camera_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.camera_label.setStyleSheet("""
            QLabel#cameraFeed {
                background: #030305;
                border: none;
                border-radius: 20px;
                color: rgba(240,240,240,0.10);
                font-size: 12px;
            }
        """)

        # Placeholder when idle
        ph = QVBoxLayout()
        ph.setAlignment(Qt.AlignCenter)
        ph.setSpacing(14)
        cam_icon = QLabel("◉")
        cam_icon.setAlignment(Qt.AlignCenter)
        cam_icon.setStyleSheet(
            "font-size: 64px; color: rgba(245,197,24,0.22); background: transparent;")
        cam_title = QLabel("Camera Off")
        cam_title.setAlignment(Qt.AlignCenter)
        cam_title.setStyleSheet(
            "font-size: 18px; font-weight: 700; color: rgba(240,240,240,0.30);"
            " letter-spacing: -0.4px; background: transparent;")
        cam_text = QLabel("Hit  ▶ Start  to begin detection")
        cam_text.setAlignment(Qt.AlignCenter)
        cam_text.setStyleSheet(
            f"font-size: 12px; color: {_C3}; background: transparent;")
        ph.addWidget(cam_icon)
        ph.addWidget(cam_title)
        ph.addWidget(cam_text)
        self.camera_label.setLayout(ph)

        layout.addWidget(self.camera_label, 1)

        # ── Controls row — floats at bottom of card ────────────────────────
        ctrl = QWidget()
        ctrl.setStyleSheet("background: transparent;")
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(18, 10, 18, 14)
        cl.setSpacing(8)

        # Spotify status pill (tiny, left side)
        self.spotify_status_lbl = QLabel("Not connected")
        self.spotify_status_lbl.setObjectName("spotifyStatus")
        self.spotify_status_lbl.setStyleSheet(
            f"font-size: 10px; color: {_C3}; background: transparent;")
        cl.addWidget(self.spotify_status_lbl)
        cl.addStretch()

        # Live indicator
        self._live_dot = QLabel("● Idle")
        self._live_dot.setStyleSheet(
            f"font-size: 10px; color: {_C3}; background: rgba(255,255,255,0.05);"
            " border-radius: 10px; padding: 2px 10px;")
        cl.addWidget(self._live_dot)
        cl.addSpacing(8)

        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.setStyleSheet(_BTN_SEC)
        self.stop_btn.clicked.connect(self.stop_detection)
        self.stop_btn.setEnabled(False)
        cl.addWidget(self.stop_btn)

        self.start_btn = QPushButton("▶  Start")
        self.start_btn.setStyleSheet(_BTN_PRI)
        self.start_btn.clicked.connect(self.start_detection)
        cl.addWidget(self.start_btn)

        self.autoplay_btn = QPushButton("⚡  Auto")
        self.autoplay_btn.setCheckable(True)
        self.autoplay_btn.setStyleSheet(_BTN_SEC)
        self.autoplay_btn.clicked.connect(
            lambda checked: self._start_autoplay() if checked else self._stop_autoplay())
        cl.addWidget(self.autoplay_btn)

        # Hidden proxy buttons satisfy SpotifyAutoplayMixin's setEnabled() calls
        self.start_autoplay_btn = QPushButton()
        self.stop_autoplay_btn  = QPushButton()
        self.start_autoplay_btn.hide()
        self.stop_autoplay_btn.hide()

        layout.addWidget(ctrl)
        return card

    # ══════════════════════════════════════════════════════════════════════════
    # Text Emotion Panel
    # ══════════════════════════════════════════════════════════════════════════
    def _build_text_panel(self) -> GlassCard:
        card = GlassCard(radius=20)
        card.setFixedHeight(188)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        lbl = QLabel("💬  Text Emotion")
        lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {_C1}; background: transparent;")
        header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)

        self.text_status_lbl = QLabel("Type how you feel when camera is off")
        self.text_status_lbl.setStyleSheet(f"font-size: 11px; color: {_C2}; background: transparent;")
        self.text_status_lbl.setWordWrap(True)
        layout.addWidget(self.text_status_lbl)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("How are you feeling right now?  ✍")
        self.text_input.setFixedHeight(62)
        self.text_input.setStyleSheet(_TEXT_INPUT_QSS)
        layout.addWidget(self.text_input)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        self.text_analyze_btn = QPushButton("✦  Analyze")
        self.text_analyze_btn.setStyleSheet(_BTN_PRI)
        self.text_analyze_btn.clicked.connect(self.analyze_text_emotion)
        self.text_result = QLabel("—")
        self.text_result.setStyleSheet(f"font-size: 11px; color: {_C2}; background: transparent;")
        self.text_result.setWordWrap(True)
        bottom.addWidget(self.text_analyze_btn)
        bottom.addWidget(self.text_result, 1)
        layout.addLayout(bottom)

        return card

    # ══════════════════════════════════════════════════════════════════════════
    # Emotion Display Panel
    # ══════════════════════════════════════════════════════════════════════════
    def _build_emotion_panel(self) -> GlassCard:
        card = GlassCard(radius=20)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # Section label
        layout.addWidget(_section_label("Current State"), 0, Qt.AlignHCenter)
        layout.addSpacing(12)

        # Emoji
        self.emotion_emoji = QLabel("😐")
        self.emotion_emoji.setObjectName("emotionEmoji")
        self.emotion_emoji.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.emotion_emoji, 0, Qt.AlignHCenter)

        # Emotion name
        self.emotion_name = QLabel("Neutral")
        self.emotion_name.setObjectName("emotionName")
        self.emotion_name.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.emotion_name, 0, Qt.AlignHCenter)

        # Confidence
        self.emotion_conf = QLabel("Confidence: —")
        self.emotion_conf.setObjectName("emotionConf")
        self.emotion_conf.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.emotion_conf, 0, Qt.AlignHCenter)
        layout.addSpacing(6)

        # Mood badge
        self.mood_badge = QLabel("🎯   Focused")
        self.mood_badge.setObjectName("moodBadge")
        self.mood_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.mood_badge, 0, Qt.AlignHCenter)
        layout.addSpacing(4)

        # Reaction text
        self.reaction_lbl = QLabel("")
        self.reaction_lbl.setObjectName("reactionText")
        self.reaction_lbl.setAlignment(Qt.AlignCenter)
        self.reaction_lbl.setWordWrap(True)
        layout.addWidget(self.reaction_lbl, 0, Qt.AlignHCenter)

        return card

    # ══════════════════════════════════════════════════════════════════════════
    # Mood Stats + Drowsiness Panel
    # ══════════════════════════════════════════════════════════════════════════
    def _build_moodstats_panel(self) -> GlassCard:
        card = GlassCard(radius=20)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(12)

        layout.addWidget(_section_label("Mood Distribution"))

        # Mood bars
        row_e, self.bar_energized, self.pct_energized = _bar_row("Energized", "#F5C518")
        row_f, self.bar_focused,   self.pct_focused   = _bar_row("Focused",   "#60a5fa")
        row_c, self.bar_calm,      self.pct_calm      = _bar_row("Calm",      "#34d399")
        row_d, self.bar_drowsy,    self.pct_drowsy    = _bar_row("Drowsy",    "#fb923c")
        for row in (row_e, row_f, row_c, row_d):
            layout.addLayout(row)

        layout.addSpacing(8)
        layout.addWidget(_section_label("Drowsiness Metrics"))
        layout.addSpacing(4)

        # Metric tiles
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(6)
        t_ear,    self._m_ear     = _metric_tile("EAR")
        t_perc,   self._m_perclos = _metric_tile("PERCLOS")
        t_yawns,  self._m_yawns   = _metric_tile("YAWNS")
        t_head,   self._m_head    = _metric_tile("HEAD")
        t_blinks, self._m_blinks  = _metric_tile("BLINKS")
        for t in (t_ear, t_perc, t_yawns, t_head, t_blinks):
            metrics_row.addWidget(t)
        layout.addLayout(metrics_row)

        # Drowsy alert banner
        self._drowsy_alert = QFrame()
        self._drowsy_alert.setStyleSheet(
            "QFrame { background: rgba(251,146,60,0.12); border-radius: 10px; }")
        al = QHBoxLayout(self._drowsy_alert)
        al.setContentsMargins(14, 10, 14, 10)
        alert_lbl = QLabel("😴  Drowsiness Detected — Stay Alert!")
        alert_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 700; color: #fb923c; background: transparent;")
        al.addWidget(alert_lbl, 0, Qt.AlignCenter)
        self._drowsy_alert.hide()
        layout.addWidget(self._drowsy_alert)

        # Status / unavail labels
        self._drowsy_status_lbl = QLabel("Start detection to monitor drowsiness")
        self._drowsy_status_lbl.setAlignment(Qt.AlignCenter)
        self._drowsy_status_lbl.setStyleSheet(f"font-size: 11px; color: {_C3}; background: transparent;")
        layout.addWidget(self._drowsy_status_lbl)

        self._drowsy_unavail = QLabel(
            "Install mediapipe for drowsiness detection:  pip install mediapipe")
        self._drowsy_unavail.setStyleSheet(
            f"font-size: 10px; color: {_C3}; background: transparent;")
        self._drowsy_unavail.setWordWrap(True)
        self._drowsy_unavail.hide()
        layout.addWidget(self._drowsy_unavail)

        return card

    # ══════════════════════════════════════════════════════════════════════════
    # Now Playing Panel
    # ══════════════════════════════════════════════════════════════════════════
    def _build_nowplaying_panel(self) -> GlassCard:
        card = GlassCard(radius=20)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(14)

        layout.addWidget(_section_label("Now Playing"))

        # ── Player row ───────────────────────────────────────────────────────
        player = QHBoxLayout()
        player.setSpacing(16)
        player.setAlignment(Qt.AlignVCenter)

        # Album art
        self.album_art = QLabel("♪")
        self.album_art.setObjectName("albumArt")
        self.album_art.setAlignment(Qt.AlignCenter)
        player.addWidget(self.album_art, 0, Qt.AlignVCenter)

        # Track info
        track_col = QVBoxLayout()
        track_col.setSpacing(3)

        self.track_name_lbl = QLabel("Nothing playing")
        self.track_name_lbl.setObjectName("trackName")
        self.track_name_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {_C1}; background: transparent;")

        self.track_artist_lbl = QLabel("Connect Spotify")
        self.track_artist_lbl.setObjectName("trackArtist")

        self.track_progress = QProgressBar()
        self.track_progress.setObjectName("trackProgress")
        self.track_progress.setRange(0, 1000)
        self.track_progress.setValue(0)
        self.track_progress.setTextVisible(False)
        self.track_progress.setFixedHeight(3)

        time_row = QHBoxLayout()
        self.time_elapsed = QLabel("0:00")
        self.time_elapsed.setObjectName("timeLabel")
        self.time_total = QLabel("0:00")
        self.time_total.setObjectName("timeLabel")
        time_row.addWidget(self.time_elapsed)
        time_row.addStretch()
        time_row.addWidget(self.time_total)

        track_col.addWidget(self.track_name_lbl)
        track_col.addWidget(self.track_artist_lbl)
        track_col.addSpacing(4)
        track_col.addWidget(self.track_progress)
        track_col.addLayout(time_row)

        player.addLayout(track_col, 1)
        layout.addLayout(player)

        # ── Player controls ──────────────────────────────────────────────────
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)

        self.prev_btn       = QPushButton("⏮")
        self.play_pause_btn = QPushButton("▶")
        self.next_btn       = QPushButton("⏭")
        self.prev_btn.setStyleSheet(_BTN_ICO)
        self.play_pause_btn.setStyleSheet(_BTN_ICO_LG)
        self.next_btn.setStyleSheet(_BTN_ICO)
        for b in (self.prev_btn, self.play_pause_btn, self.next_btn):
            b.setEnabled(False)
        self.prev_btn.clicked.connect(self._prev_track)
        self.play_pause_btn.clicked.connect(self._toggle_play_pause)
        self.next_btn.clicked.connect(self._next_track)

        ctrl.addWidget(self.prev_btn)
        ctrl.addWidget(self.play_pause_btn)
        ctrl.addWidget(self.next_btn)
        ctrl.addSpacing(10)

        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("font-size: 12px; background: transparent;")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setStyleSheet(_SLIDER_QSS)
        self.volume_slider.setEnabled(False)
        self.volume_slider.valueChanged.connect(self._change_volume)

        ctrl.addWidget(vol_icon)
        ctrl.addWidget(self.volume_slider, 1)
        layout.addLayout(ctrl)

        # ── Queue ────────────────────────────────────────────────────────────
        self.queue_list = QListWidget()
        self.queue_list.setMinimumHeight(80)
        self.queue_list.setMaximumHeight(140)
        self.queue_list.setStyleSheet(_LIST_QSS)
        self.queue_list.addItem("Queue will appear when auto-play is active")
        self.queue_list.setToolTip("Double-click a song to skip to it immediately")
        self.queue_list.itemDoubleClicked.connect(
            lambda item: self._play_queued_item(self.queue_list.row(item)))
        layout.addWidget(self.queue_list)

        return card

    # ══════════════════════════════════════════════════════════════════════════
    # Calendar Panel
    # ══════════════════════════════════════════════════════════════════════════
    def _build_calendar_panel(self) -> GlassCard:
        card = GlassCard(radius=20)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("📅  Upcoming Events")
        title.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {_C1}; background: transparent;")
        header.addWidget(title)
        header.addStretch()
        self.refresh_cal_btn = QPushButton("↺  Refresh")
        self.refresh_cal_btn.setStyleSheet(_BTN_SEC)
        self.refresh_cal_btn.setFixedHeight(28)
        self.refresh_cal_btn.clicked.connect(self.refresh_calendar)
        header.addWidget(self.refresh_cal_btn)
        layout.addLayout(header)

        self.cal_status_lbl = QLabel("Not connected — go to Calendar page to connect")
        self.cal_status_lbl.setStyleSheet(f"font-size: 11px; color: {_C2}; background: transparent;")
        self.cal_status_lbl.setWordWrap(True)
        layout.addWidget(self.cal_status_lbl)

        self.cal_list = QListWidget()
        self.cal_list.setMinimumHeight(100)
        self.cal_list.setMaximumHeight(180)
        self.cal_list.setStyleSheet(_LIST_QSS)
        self.cal_list.addItem("No events loaded")
        layout.addWidget(self.cal_list, 1)

        hint = QLabel("Manage events on the Calendar page →")
        hint.setStyleSheet(f"font-size: 10px; color: {_C3}; background: transparent;")
        layout.addWidget(hint)

        return card

    # ══════════════════════════════════════════════════════════════════════════
    # Shared helpers
    # ══════════════════════════════════════════════════════════════════════════
    def _refresh_queue_display(self):
        self.queue_list.clear()
        if not self.queued_tracks:
            self.queue_list.addItem("Queue will appear when auto-play is active")
            return
        for t in self.queued_tracks:
            self.queue_list.addItem(
                f"{t.get('name', '?')}   ·   {t.get('artist', '?')}")

    # ══════════════════════════════════════════════════════════════════════════
    # Public API (called by MainWindow / mixins)
    # ══════════════════════════════════════════════════════════════════════════
    def set_spotify(self, sp, display_name: str, product: str):
        self.sp              = sp
        self.spotify_product = product
        color = "#34d399" if product.lower() == "premium" else "#fbbf24"
        self.spotify_status_lbl.setText(f"● {display_name}  ({product.capitalize()})")
        _set_label_color(self.spotify_status_lbl, color, "10px")
        self._start_spotify_monitor()

    def clear_spotify(self):
        self.sp = None
        self.spotify_status_lbl.setText("Not connected")
        self.spotify_status_lbl.setStyleSheet(
            f"font-size: 10px; color: {_C3}; background: transparent;")
        for btn in (self.play_pause_btn, self.prev_btn, self.next_btn):
            btn.setEnabled(False)
        self.volume_slider.setEnabled(False)
        if self.spotify_monitor:
            self.spotify_monitor.stop()
            self.spotify_monitor = None

    def set_calendar_service(self, service):
        self.calendar_service = service
        self.cal_status_lbl.setText("● Google Calendar connected")
        _set_label_color(self.cal_status_lbl, "#34d399")
        self.refresh_calendar()

    def clear_calendar_service(self):
        self.calendar_service = None
        self.cal_status_lbl.setText("Not connected — go to Calendar page to connect")
        self.cal_status_lbl.setStyleSheet(f"font-size: 11px; color: {_C2}; background: transparent;")

    def set_mood_widget(self, widget):
        self._mood_widget = widget

    def emotion_db(self) -> EmotionDB:
        return self._db

    def export_session_csv(self):
        sid = self._db.session_id
        if not sid:
            sessions = self._db.get_sessions(limit=1)
            if sessions:
                sid = sessions[0]["id"]
        if not sid:
            self.status_changed.emit("No session data to export.", "#fbbf24")
            return
        folder = SettingsManager.get("export_folder", "")
        try:
            base = self._db.export_csv(sid, folder)
            self.status_changed.emit(f"Exported: {os.path.basename(base)}_*.csv", "#34d399")
        except Exception as ex:
            self.status_changed.emit(f"Export failed: {ex}", "#f87171")

    def set_music_prefs(self, prefs: dict):
        self._music_prefs = prefs

    # ══════════════════════════════════════════════════════════════════════════
    # Cleanup
    # ══════════════════════════════════════════════════════════════════════════
    def shutdown(self):
        if self.detection_thread:
            self.detection_thread.stop()
        if self.spotify_monitor:
            self.spotify_monitor.stop()
        if self.calendar_thread and self.calendar_thread.isRunning():
            self.calendar_thread.wait()
        self._db.close()
        cv2.destroyAllWindows()
