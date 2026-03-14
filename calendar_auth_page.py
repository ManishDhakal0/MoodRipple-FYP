# calendar_auth_page.py
# In-app Google Calendar OAuth widget — shown as a page in the left-side menu

import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt5.QtCore import QThread, pyqtSignal

CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.pickle"


# ─────────────────────────────────────────────
# Background thread: runs Google Calendar OAuth
# ─────────────────────────────────────────────
class CalendarAuthThread(QThread):
    auth_success = pyqtSignal(object)   # google calendar service
    auth_failed  = pyqtSignal(str)

    def run(self):
        try:
            import pickle
            from google.auth.transport.requests import Request
            from google.auth.exceptions import RefreshError
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            SCOPES = ["https://www.googleapis.com/auth/calendar"]

            creds = None
            if os.path.exists(TOKEN_PATH):
                with open(TOKEN_PATH, "rb") as token:
                    creds = pickle.load(token)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except RefreshError:
                        creds = None

                if not creds:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        CREDENTIALS_PATH, SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                with open(TOKEN_PATH, "wb") as token:
                    pickle.dump(creds, token)

            service = build("calendar", "v3", credentials=creds)
            self.auth_success.emit(service)

        except Exception as e:
            self.auth_failed.emit(str(e))


# ─────────────────────────────────────────────
# Calendar Auth Page widget
# ─────────────────────────────────────────────
class CalendarAuthPage(QWidget):
    connected    = pyqtSignal(object)   # google calendar service
    disconnected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.auth_thread = None
        self._setup_ui()
        # Try silent connect if a token is already saved
        if os.path.exists(TOKEN_PATH) and os.path.exists(CREDENTIALS_PATH):
            self._run_auth()

    # ── UI ──────────────────────────────────
    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.setSpacing(24)

        title = QLabel("📅 Google Calendar Connection")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        # Status card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(10)

        self.status_label = QLabel("● Not Connected")
        self.status_label.setStyleSheet("color: #ff6b6b; font-size: 14px; font-weight: bold;")

        # Show a warning if credentials.json is missing
        creds_ok = os.path.exists(CREDENTIALS_PATH)
        self.creds_warning = QLabel(
            "⚠ credentials.json not found in the project folder.\n"
            "Download it from Google Cloud Console → OAuth 2.0 Credentials."
        )
        self.creds_warning.setStyleSheet("color: #f39c12; font-size: 12px;")
        self.creds_warning.setWordWrap(True)
        self.creds_warning.setVisible(not creds_ok)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.connect_btn = QPushButton("Connect Google Calendar")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.setEnabled(creds_ok)
        self.connect_btn.clicked.connect(self._on_connect_clicked)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setObjectName("secondaryButton")
        self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self.disconnect_btn.hide()

        btn_row.addWidget(self.connect_btn)
        btn_row.addWidget(self.disconnect_btn)
        btn_row.addStretch()

        card_layout.addWidget(self.status_label)
        card_layout.addWidget(self.creds_warning)
        card_layout.addSpacing(8)
        card_layout.addLayout(btn_row)
        outer.addWidget(card)

        # Instructions card
        info = QFrame()
        info.setObjectName("card")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(24, 16, 24, 16)
        info_layout.setSpacing(6)

        info_title = QLabel("How to connect")
        info_title.setObjectName("panelTitle")
        info_layout.addWidget(info_title)

        steps = [
            "1. Make sure credentials.json is in the project folder.",
            "2. Click Connect Google Calendar above.",
            "3. A browser window will open with the Google sign-in page.",
            "4. Sign in and click Allow to grant MoodRipple access to your calendar.",
            "5. The app saves your session — you only need to do this once.",
        ]
        for step in steps:
            lbl = QLabel(step)
            lbl.setObjectName("subText")
            lbl.setWordWrap(True)
            info_layout.addWidget(lbl)

        outer.addWidget(info)
        outer.addStretch()

    # ── Auth flow ────────────────────────────
    def _on_connect_clicked(self):
        self.connect_btn.setEnabled(False)
        self.status_label.setText("⏳ Connecting… check your browser")
        self.status_label.setStyleSheet("color: #f39c12; font-size: 14px; font-weight: bold;")
        self._run_auth()

    def _run_auth(self):
        if self.auth_thread is not None and self.auth_thread.isRunning():
            return
        self.auth_thread = CalendarAuthThread()
        self.auth_thread.auth_success.connect(self._on_success)
        self.auth_thread.auth_failed.connect(self._on_failed)
        self.auth_thread.start()

    def _on_success(self, service):
        self.status_label.setText("● Connected")
        self.status_label.setStyleSheet("color: #1DB954; font-size: 14px; font-weight: bold;")
        self.connect_btn.hide()
        self.disconnect_btn.show()
        self.connected.emit(service)

    def _on_failed(self, error: str):
        self.status_label.setText("● Not Connected")
        self.status_label.setStyleSheet("color: #ff6b6b; font-size: 14px; font-weight: bold;")
        self.connect_btn.setEnabled(os.path.exists(CREDENTIALS_PATH))
        self.connect_btn.show()
        self.disconnect_btn.hide()

    def _on_disconnect_clicked(self):
        if os.path.exists(TOKEN_PATH):
            os.remove(TOKEN_PATH)
        self.status_label.setText("● Not Connected")
        self.status_label.setStyleSheet("color: #ff6b6b; font-size: 14px; font-weight: bold;")
        self.connect_btn.setEnabled(os.path.exists(CREDENTIALS_PATH))
        self.connect_btn.show()
        self.disconnect_btn.hide()
        self.disconnected.emit()

    # ── Public helper ────────────────────────
    def is_connected(self) -> bool:
        return "Connected" in self.status_label.text() and "Not" not in self.status_label.text()
