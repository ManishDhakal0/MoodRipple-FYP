# ui/pages/calendar_connect.py
# In-app Google Calendar OAuth page

import os
import pickle
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt5.QtCore import pyqtSignal, Qt, QThread

from core.constants import GOOGLE_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH, GOOGLE_SCOPES


class _CalendarAuthThread(QThread):
    success = pyqtSignal(object)   # Google Calendar service
    failed  = pyqtSignal(str)

    def __init__(self, interactive: bool = False):
        super().__init__()
        self.interactive = interactive

    def run(self):
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            creds = None
            if os.path.exists(GOOGLE_TOKEN_PATH):
                with open(GOOGLE_TOKEN_PATH, "rb") as f:
                    creds = pickle.load(f)

            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(GOOGLE_TOKEN_PATH, "wb") as f:
                    pickle.dump(creds, f)
            elif not creds or not creds.valid:
                if not self.interactive:
                    self.failed.emit("No valid token — please connect.")
                    return
                flow = InstalledAppFlow.from_client_secrets_file(
                    GOOGLE_CREDENTIALS_PATH, GOOGLE_SCOPES
                )
                creds = flow.run_local_server(port=0)
                with open(GOOGLE_TOKEN_PATH, "wb") as f:
                    pickle.dump(creds, f)

            service = build("calendar", "v3", credentials=creds)
            self.success.emit(service)
        except Exception as e:
            self.failed.emit(str(e))


class CalendarConnectPage(QWidget):
    """Full-page Google Calendar OAuth UI.

    Signals:
        connected(service)
        disconnected()
    """

    connected    = pyqtSignal(object)
    disconnected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = None
        self._thread  = None
        self._build_ui()
        self._try_silent_reconnect()

    # ── Build UI ─────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.setSpacing(0)

        # Card
        card = QFrame()
        card.setObjectName("authCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(18)
        card_layout.setAlignment(Qt.AlignTop)

        # Title row
        title_row = QHBoxLayout()
        icon = QLabel("📅")
        icon.setStyleSheet("font-size: 36px;")
        page_title = QLabel("Google Calendar")
        page_title.setObjectName("pageTitle")
        title_row.addWidget(icon)
        title_row.addSpacing(12)
        title_row.addWidget(page_title)
        title_row.addStretch()
        card_layout.addLayout(title_row)

        # Description
        desc = QLabel(
            "Connect your Google Calendar to view upcoming events and create\n"
            "new events directly from MoodRipple.\n\n"
            "You need a credentials.json file from Google Cloud Console."
        )
        desc.setObjectName("subText")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        # credentials.json warning
        if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
            warn = QLabel(
                "⚠  credentials.json not found.\n"
                "Download it from Google Cloud Console → APIs & Services → Credentials."
            )
            warn.setObjectName("statusWarn")
            warn.setWordWrap(True)
            card_layout.addWidget(warn)

        card_layout.addSpacing(8)

        # Status
        self.status_label = QLabel("Not connected")
        self.status_label.setObjectName("statusBad")
        self.status_label.setWordWrap(True)
        card_layout.addWidget(self.status_label)

        # Connected indicator
        self.connected_frame = QFrame()
        self.connected_frame.setObjectName("card")
        cf_layout = QVBoxLayout(self.connected_frame)
        cf_layout.setContentsMargins(16, 14, 16, 14)
        cf_layout.setSpacing(4)
        self.connected_badge = QLabel("✅  Google Calendar connected")
        self.connected_badge.setObjectName("statusGood")
        cf_layout.addWidget(self.connected_badge)
        self.connected_frame.hide()
        card_layout.addWidget(self.connected_frame)

        card_layout.addSpacing(8)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.connect_btn = QPushButton("Connect Google Calendar")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
            self.connect_btn.setEnabled(False)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setObjectName("secondaryButton")
        self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self.disconnect_btn.hide()

        btn_row.addWidget(self.connect_btn)
        btn_row.addWidget(self.disconnect_btn)
        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        note = QLabel(
            "A browser window will open for Google authorization.\n"
            "After you approve, return here — the page will update automatically."
        )
        note.setObjectName("labelMuted")
        note.setWordWrap(True)
        card_layout.addWidget(note)

        outer.addWidget(card)
        outer.addStretch()

    # ── Reconnect on startup ──────────────────────────────────────────────
    def _try_silent_reconnect(self):
        if os.path.exists(GOOGLE_TOKEN_PATH):
            self._set_status("Reconnecting…", "#9da8b4")
            self.connect_btn.setEnabled(False)
            self._run_auth(interactive=False)

    # ── Slots ─────────────────────────────────────────────────────────────
    def _on_connect_clicked(self):
        self._set_status("Opening Google in browser…", "#9da8b4")
        self.connect_btn.setEnabled(False)
        self._run_auth(interactive=True)

    def _on_disconnect_clicked(self):
        self._service = None
        if os.path.exists(GOOGLE_TOKEN_PATH):
            try:
                os.remove(GOOGLE_TOKEN_PATH)
            except OSError:
                pass
        self._show_disconnected()
        self.disconnected.emit()

    # ── Thread management ─────────────────────────────────────────────────
    def _run_auth(self, interactive: bool):
        self._thread = _CalendarAuthThread(interactive=interactive)
        self._thread.success.connect(self._on_auth_success)
        self._thread.failed.connect(self._on_auth_failed)
        self._thread.start()

    def _on_auth_success(self, service):
        self._service = service
        self._show_connected()
        self.connected.emit(service)

    def _on_auth_failed(self, error: str):
        self._set_status(f"Connection failed: {error}", "#e05555")
        self.connect_btn.setEnabled(
            os.path.exists(GOOGLE_CREDENTIALS_PATH)
        )

    # ── UI helpers ────────────────────────────────────────────────────────
    def _set_status(self, msg: str, color: str):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(
            f"color: {color}; font-size: 12px; padding: 4px 0;"
        )

    def _show_connected(self):
        self._set_status("Connected", "#1DB954")
        self.connected_frame.show()
        self.connect_btn.hide()
        self.disconnect_btn.show()

    def _show_disconnected(self):
        self._set_status("Not connected", "#e05555")
        self.connected_frame.hide()
        self.connect_btn.show()
        self.connect_btn.setEnabled(os.path.exists(GOOGLE_CREDENTIALS_PATH))
        self.disconnect_btn.hide()
