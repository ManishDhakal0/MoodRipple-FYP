# ui/window.py
# MainWindow: header + sidebar + page stack + status bar

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QStackedWidget, QPushButton,
)
from PyQt5.QtCore import pyqtSignal

from ui.theme import apply_theme
from ui.sidebar import SidebarWidget
from ui.pages.dashboard import DashboardPage
from ui.pages.spotify_connect import SpotifyConnectPage
from ui.pages.calendar_connect import CalendarConnectPage
from core.auth import AuthManager


class MainWindow(QMainWindow):
    logged_out = pyqtSignal()

    def __init__(self, user: dict = None):
        super().__init__()
        self._user = user or {}
        self.setWindowTitle("MoodRipple")
        self.setMinimumSize(1200, 740)
        self.resize(1440, 860)
        apply_theme(self)
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        rl = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # ── Header ────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(64)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(0)

        dot = QLabel("◆")
        dot.setObjectName("headerDot")
        dot.setStyleSheet("font-size: 14px; color: #7c3aed; margin-right: 10px; padding-bottom: 1px;")

        title = QLabel("MoodRipple")
        title.setObjectName("headerTitle")

        sub = QLabel("  ·  Emotion-aware music  ·  Spotify  ·  Google Calendar")
        sub.setObjectName("headerSub")

        hl.addWidget(dot)
        hl.addWidget(title)
        hl.addWidget(sub)
        hl.addStretch()

        # Logged-in user + logout
        if self._user.get("username"):
            user_lbl = QLabel(f"👤  {self._user['username']}")
            user_lbl.setObjectName("headerUser")
            hl.addWidget(user_lbl)
            hl.addSpacing(12)

        logout_btn = QPushButton("Sign Out")
        logout_btn.setObjectName("logoutButton")
        logout_btn.clicked.connect(self._on_logout)
        hl.addWidget(logout_btn)

        rl.addWidget(header)

        # ── Body: sidebar + page stack ────────────────────────────
        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self.sidebar = SidebarWidget()
        self.sidebar.navigate.connect(self._navigate)
        bl.addWidget(self.sidebar)

        self.page_stack = QStackedWidget()

        self.dashboard = DashboardPage()
        self.dashboard.status_changed.connect(self._set_status)
        self.page_stack.addWidget(self.dashboard)

        self.spotify_page = SpotifyConnectPage()
        self.spotify_page.connected.connect(self._on_spotify_connected)
        self.spotify_page.disconnected.connect(self._on_spotify_disconnected)
        self.page_stack.addWidget(self.spotify_page)

        self.calendar_page = CalendarConnectPage()
        self.calendar_page.connected.connect(self._on_calendar_connected)
        self.calendar_page.disconnected.connect(self._on_calendar_disconnected)
        self.page_stack.addWidget(self.calendar_page)

        bl.addWidget(self.page_stack, 1)
        rl.addWidget(body, 1)

        # ── Status bar ────────────────────────────────────────────
        sb = QFrame()
        sb.setObjectName("statusBar")
        sb.setFixedHeight(36)
        sbl = QHBoxLayout(sb)
        sbl.setContentsMargins(20, 0, 20, 0)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusText")
        sbl.addWidget(self.status_label)
        rl.addWidget(sb)

    # ── Navigation ────────────────────────────────────────────────
    def _navigate(self, index: int):
        self.page_stack.setCurrentIndex(index)
        self.sidebar.set_active(index)

    # ── Auth signals ──────────────────────────────────────────────
    def _on_spotify_connected(self, sp, display_name: str, product: str):
        self.dashboard.set_spotify(sp, display_name, product)
        self.sidebar.set_spotify_connected(True)
        self._set_status(f"Spotify connected — {display_name} ({product})", "#10b981")

    def _on_spotify_disconnected(self):
        self.dashboard.clear_spotify()
        self.sidebar.set_spotify_connected(False)
        self._set_status("Spotify disconnected.", "#3d4f6a")

    def _on_calendar_connected(self, service):
        self.dashboard.set_calendar_service(service)
        self.sidebar.set_calendar_connected(True)
        self._set_status("Google Calendar connected.", "#10b981")

    def _on_calendar_disconnected(self):
        self.dashboard.clear_calendar_service()
        self.sidebar.set_calendar_connected(False)
        self._set_status("Google Calendar disconnected.", "#3d4f6a")

    # ── Status bar ────────────────────────────────────────────────
    def _set_status(self, msg: str, color: str = "#1e2844"):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _on_logout(self):
        AuthManager().clear_session()
        self.dashboard.shutdown()
        self.logged_out.emit()

    def closeEvent(self, event):
        self.dashboard.shutdown()
        event.accept()
