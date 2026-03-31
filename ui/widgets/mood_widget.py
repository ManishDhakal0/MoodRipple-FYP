# ui/widgets/mood_widget.py
# Always-on-top floating "Now Mood" widget — frameless, draggable, semi-transparent.

from PyQt5.QtCore    import Qt, QPoint
from PyQt5.QtGui     import QFont, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)

_MOOD_COLORS = {
    "energized": "#1DB954",
    "focused":   "#5B9BD5",
    "calm":      "#9B59B6",
    "drowsy":    "#E67E22",
}
_MOOD_EMOJI = {
    "energized": "⚡",
    "focused":   "🎯",
    "calm":      "😌",
    "drowsy":    "😴",
}


class NowMoodWidget(QWidget):
    """Small always-on-top widget showing current emotion + song."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._drag_pos = QPoint()
        self._build_ui()
        self.resize(310, 100)

    def _build_ui(self):
        self._container = QFrame(self)
        self._container.setObjectName("moodFloatContainer")
        self._container.setStyleSheet("""
            QFrame#moodFloatContainer {
                background: rgba(18, 18, 30, 210);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 12px;
            }
        """)

        root = QVBoxLayout(self._container)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(4)

        # Header row: emoji + label + close button
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        self._emoji_lbl = QLabel("🎯")
        self._emoji_lbl.setFont(QFont("Segoe UI Emoji", 20))
        self._emoji_lbl.setFixedWidth(36)

        self._mood_lbl = QLabel("Now Mood")
        self._mood_lbl.setStyleSheet("color: #e0e0e0; font-size: 13px; font-weight: 600;")

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                color: #888; background: transparent; border: none; font-size: 11px;
            }
            QPushButton:hover { color: #e05555; }
        """)
        close_btn.clicked.connect(self.hide)

        hdr.addWidget(self._emoji_lbl)
        hdr.addWidget(self._mood_lbl, 1)
        hdr.addWidget(close_btn)
        root.addLayout(hdr)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.10);")
        root.addWidget(sep)

        # Track row
        self._track_lbl = QLabel("No track playing")
        self._track_lbl.setStyleSheet("color: #9da8b4; font-size: 11px;")
        self._track_lbl.setWordWrap(False)
        self._track_lbl.setMaximumWidth(280)
        root.addWidget(self._track_lbl)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._container)

    # ── Public API ─────────────────────────────────────────────────────────
    def update_emotion(self, emotion: str, mood: str):
        color  = _MOOD_COLORS.get(mood, "#9da8b4")
        emoji  = _MOOD_EMOJI.get(mood, "🙂")
        label  = f"{emotion.capitalize()}  •  {mood.capitalize()}"
        self._emoji_lbl.setText(emoji)
        self._mood_lbl.setText(label)
        self._mood_lbl.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: 600;"
        )

    def update_track(self, track: str, artist: str):
        if track:
            text = f"♫  {track}"
            if artist:
                text += f"  —  {artist}"
            self._track_lbl.setText(text)
        else:
            self._track_lbl.setText("No track playing")

    # ── Dragging ───────────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = QPoint()
