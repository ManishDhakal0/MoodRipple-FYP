# ui/sidebar.py
# FloatingSidebar — 64 px wide, fully transparent.
# Icon-only nav; active item glows yellow. Brand orb has drop-shadow glow.

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui  import QColor


_ICONS = {
    "dashboard": "⬡",
    "spotify":   "◎",
    "calendar":  "▦",
    "analytics": "⬙",
    "settings":  "◈",
    "chat":      "◇",
}
_TOOLTIPS = {
    "dashboard": "Dashboard",
    "spotify":   "Spotify",
    "calendar":  "Calendar",
    "analytics": "Analytics",
    "settings":  "Settings",
    "chat":      "MoodBot Chat",
}

_BTN_QSS = """
    QPushButton {
        background: transparent;
        color: rgba(255,255,255,0.20);
        border: none;
        border-radius: 14px;
        font-size: 19px;
        padding: 0;
    }
    QPushButton:hover {
        color: rgba(255,255,255,0.62);
        background: rgba(255,255,255,0.05);
    }
    QPushButton:checked {
        color: #F5C518;
        background: rgba(245,197,24,0.10);
    }
"""

_DOT_GOOD = "color: rgba(52,211,153,0.75); font-size: 6px; background: transparent;"
_DOT_BAD  = "color: rgba(255,255,255,0.12); font-size: 6px; background: transparent;"


class SidebarWidget(QWidget):
    navigate = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(64)
        # Fully transparent — glow background shows through
        self.setStyleSheet("QWidget#sidebar { background: transparent; border: none; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 24, 8, 24)
        root.setSpacing(0)

        # ── Brand orb — yellow glow dot ─────────────────────────────────────
        orb = QLabel("◆")
        orb.setAlignment(Qt.AlignCenter)
        orb.setFixedHeight(44)
        orb.setStyleSheet("font-size: 14px; color: #F5C518; background: transparent;")
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(22)
        glow.setOffset(0, 0)
        glow.setColor(QColor(245, 197, 24, 200))
        orb.setGraphicsEffect(glow)
        root.addWidget(orb, 0, Qt.AlignHCenter)
        root.addSpacing(30)

        # ── Main nav ────────────────────────────────────────────────────────
        self.btn_dashboard = self._btn("dashboard")
        self.btn_dashboard.setChecked(True)
        self.btn_dashboard.clicked.connect(lambda: self._activate(0))
        root.addWidget(self.btn_dashboard, 0, Qt.AlignHCenter)
        root.addSpacing(2)

        self.btn_spotify = self._btn("spotify")
        self.btn_spotify.clicked.connect(lambda: self._activate(1))
        root.addWidget(self.btn_spotify, 0, Qt.AlignHCenter)
        self.dot_spotify = self._dot()
        root.addWidget(self.dot_spotify, 0, Qt.AlignHCenter)
        root.addSpacing(2)

        self.btn_calendar = self._btn("calendar")
        self.btn_calendar.clicked.connect(lambda: self._activate(2))
        root.addWidget(self.btn_calendar, 0, Qt.AlignHCenter)
        self.dot_calendar = self._dot()
        root.addWidget(self.dot_calendar, 0, Qt.AlignHCenter)

        # ── Divider ─────────────────────────────────────────────────────────
        root.addSpacing(20)
        div = QFrame()
        div.setFixedSize(16, 1)
        div.setStyleSheet("background: rgba(255,255,255,0.07); border: none;")
        root.addWidget(div, 0, Qt.AlignHCenter)
        root.addSpacing(20)

        # ── Tools nav ───────────────────────────────────────────────────────
        self.btn_analytics = self._btn("analytics")
        self.btn_analytics.clicked.connect(lambda: self._activate(3))
        root.addWidget(self.btn_analytics, 0, Qt.AlignHCenter)
        root.addSpacing(2)

        self.btn_settings = self._btn("settings")
        self.btn_settings.clicked.connect(lambda: self._activate(4))
        root.addWidget(self.btn_settings, 0, Qt.AlignHCenter)
        root.addSpacing(2)

        self.btn_chat = self._btn("chat")
        self.btn_chat.clicked.connect(lambda: self._activate(5))
        root.addWidget(self.btn_chat, 0, Qt.AlignHCenter)

        root.addStretch()

        # ── Status pulse ────────────────────────────────────────────────────
        pulse = QLabel("●")
        pulse.setAlignment(Qt.AlignCenter)
        pulse.setStyleSheet(
            "font-size: 6px; color: rgba(52,211,153,0.50); background: transparent;")
        root.addWidget(pulse, 0, Qt.AlignHCenter)

    # ── Helpers ─────────────────────────────────────────────────────────────
    def _btn(self, key: str) -> QPushButton:
        btn = QPushButton(_ICONS[key])
        btn.setObjectName("navButton")
        btn.setCheckable(True)
        btn.setToolTip(_TOOLTIPS[key])
        btn.setFixedSize(44, 44)
        btn.setStyleSheet(_BTN_QSS)
        return btn

    def _dot(self) -> QLabel:
        lbl = QLabel("●")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFixedHeight(9)
        lbl.setObjectName("navDotBad")
        return lbl

    def _refresh_dot(self, lbl: QLabel):
        lbl.style().unpolish(lbl)
        lbl.style().polish(lbl)

    # ── Public API ──────────────────────────────────────────────────────────
    def _activate(self, index: int):
        self.set_active(index)
        self.navigate.emit(index)

    def set_active(self, index: int):
        self.btn_dashboard.setChecked(index == 0)
        self.btn_spotify.setChecked(index == 1)
        self.btn_calendar.setChecked(index == 2)
        self.btn_analytics.setChecked(index == 3)
        self.btn_settings.setChecked(index == 4)
        self.btn_chat.setChecked(index == 5)

    def set_spotify_connected(self, connected: bool):
        self.dot_spotify.setObjectName("navDotGood" if connected else "navDotBad")
        self._refresh_dot(self.dot_spotify)

    def set_calendar_connected(self, connected: bool):
        self.dot_calendar.setObjectName("navDotGood" if connected else "navDotBad")
        self._refresh_dot(self.dot_calendar)
