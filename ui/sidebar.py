# ui/sidebar.py
# Left navigation sidebar

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal


class SidebarWidget(QFrame):
    navigate = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(178)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 28, 0, 20)
        layout.setSpacing(0)

        brand = QLabel("MOODRIPPLE")
        brand.setObjectName("sidebarBrand")
        layout.addWidget(brand)
        layout.addSpacing(20)

        self.btn_dashboard = QPushButton("🏠  Dashboard")
        self.btn_dashboard.setObjectName("navButton")
        self.btn_dashboard.setCheckable(True)
        self.btn_dashboard.setChecked(True)
        self.btn_dashboard.clicked.connect(lambda: self.navigate.emit(0))
        layout.addWidget(self.btn_dashboard)

        layout.addSpacing(4)

        self.btn_spotify = QPushButton("🎵  Spotify")
        self.btn_spotify.setObjectName("navButton")
        self.btn_spotify.setCheckable(True)
        self.btn_spotify.clicked.connect(lambda: self.navigate.emit(1))
        layout.addWidget(self.btn_spotify)

        self.dot_spotify = QLabel("  ● not connected")
        self.dot_spotify.setObjectName("navDotBad")
        layout.addWidget(self.dot_spotify)

        layout.addSpacing(4)

        self.btn_calendar = QPushButton("📅  Calendar")
        self.btn_calendar.setObjectName("navButton")
        self.btn_calendar.setCheckable(True)
        self.btn_calendar.clicked.connect(lambda: self.navigate.emit(2))
        layout.addWidget(self.btn_calendar)

        self.dot_calendar = QLabel("  ● not connected")
        self.dot_calendar.setObjectName("navDotBad")
        layout.addWidget(self.dot_calendar)

        layout.addStretch()

    def set_active(self, index: int):
        self.btn_dashboard.setChecked(index == 0)
        self.btn_spotify.setChecked(index == 1)
        self.btn_calendar.setChecked(index == 2)

    def set_spotify_connected(self, connected: bool):
        if connected:
            self.dot_spotify.setText("  ● connected")
            self.dot_spotify.setStyleSheet("color: #10b981; font-size: 9px; padding-left: 16px;")
        else:
            self.dot_spotify.setText("  ● not connected")
            self.dot_spotify.setStyleSheet("color: #3a1a1a; font-size: 9px; padding-left: 16px;")

    def set_calendar_connected(self, connected: bool):
        if connected:
            self.dot_calendar.setText("  ● connected")
            self.dot_calendar.setStyleSheet("color: #10b981; font-size: 9px; padding-left: 16px;")
        else:
            self.dot_calendar.setText("  ● not connected")
            self.dot_calendar.setStyleSheet("color: #3a1a1a; font-size: 9px; padding-left: 16px;")
