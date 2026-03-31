# ui/pages/calendar_connect.py
# Google Calendar — two-column layout:
#   Left  (330px): Add Event form (always visible)
#   Right (expands): OAuth connection + Upcoming Events list

import os
import pickle
import shutil
from datetime import datetime, timezone

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QFileDialog, QLineEdit, QTextEdit,
    QDateTimeEdit, QFormLayout, QListWidget,
)
from PyQt5.QtCore import pyqtSignal, Qt, QThread, QDateTime

from core.constants import GOOGLE_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH, GOOGLE_SCOPES
from core.calendar_thread import CalendarEventsThread, CalendarCreateThread


# ─────────────────────────────────────────────────────────────────────────────
# Auth thread
# ─────────────────────────────────────────────────────────────────────────────
class _CalendarAuthThread(QThread):
    success = pyqtSignal(object)
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
                try:
                    with open(GOOGLE_TOKEN_PATH, "rb") as f:
                        creds = pickle.load(f)
                except Exception:
                    creds = None

            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(GOOGLE_TOKEN_PATH, "wb") as f:
                        pickle.dump(creds, f)
                except Exception:
                    creds = None
                    try:
                        os.remove(GOOGLE_TOKEN_PATH)
                    except OSError:
                        pass

            if not creds or not creds.valid:
                if not self.interactive:
                    self.failed.emit("Token expired or revoked — please reconnect.")
                    return
                if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
                    self.failed.emit(
                        "credentials.json not found. Use 'Load credentials.json' button."
                    )
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


# ─────────────────────────────────────────────────────────────────────────────
# Main page
# ─────────────────────────────────────────────────────────────────────────────
class CalendarConnectPage(QWidget):
    connected      = pyqtSignal(object)
    disconnected   = pyqtSignal()
    event_created  = pyqtSignal()
    events_updated = pyqtSignal(list)   # raw event dicts for banner/alert

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service             = None
        self._auth_thread         = None
        self._events_thread       = None
        self._create_thread       = None
        self._build_ui()
        self._try_silent_reconnect()

    # ─────────────────────────────────────────────────────────────────
    # Root layout: Left sidebar | Right panel
    # ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_left_panel())
        root.addWidget(self._build_right_panel(), 1)

    # ─────────────────────────────────────────────────────────────────
    # LEFT: Add Event form
    # ─────────────────────────────────────────────────────────────────
    def _build_left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("calSidebar")
        panel.setFixedWidth(330)

        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("panelScroll")

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(20, 24, 20, 20)
        cl.setSpacing(14)

        # Header
        hdr = QLabel("ADD EVENT")
        hdr.setObjectName("cardTitle")
        cl.addWidget(hdr)

        # Not-connected hint
        self._add_hint = QLabel("Connect Google Calendar (→) to create events.")
        self._add_hint.setObjectName("subText")
        self._add_hint.setWordWrap(True)
        self._add_hint.setStyleSheet("font-size: 11px; color: #334155;")
        cl.addWidget(self._add_hint)

        # Form card
        form_card = QFrame()
        form_card.setObjectName("card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

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
        self.cal_desc_input.setFixedHeight(64)

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

        form_layout.addLayout(form)

        self.create_event_btn = QPushButton("Create Event")
        self.create_event_btn.setObjectName("primaryButton")
        self.create_event_btn.clicked.connect(self._create_event)
        self.create_event_btn.setEnabled(False)
        form_layout.addWidget(self.create_event_btn)

        self._create_status = QLabel("")
        self._create_status.setObjectName("subText")
        self._create_status.setWordWrap(True)
        form_layout.addWidget(self._create_status)

        cl.addWidget(form_card)
        cl.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        return panel

    # ─────────────────────────────────────────────────────────────────
    # RIGHT: Auth + Events
    # ─────────────────────────────────────────────────────────────────
    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("panelScroll")

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(28, 28, 28, 28)
        cl.setSpacing(16)

        cl.addWidget(self._build_auth_card())
        cl.addWidget(self._build_events_card())
        cl.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)
        return panel

    # ── Auth card ─────────────────────────────────────────────────────
    def _build_auth_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("authCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(0)

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(14)

        icon_bg = QFrame()
        icon_bg.setFixedSize(44, 44)
        icon_bg.setStyleSheet(
            "background: rgba(59,130,246,0.12); border-radius: 11px; border: none;"
        )
        icon_inner = QVBoxLayout(icon_bg)
        icon_inner.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("📅")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 20px; background: transparent;")
        icon_inner.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        page_title = QLabel("Google Calendar")
        page_title.setObjectName("pageTitle")
        subtitle = QLabel("View and create events from MoodRipple")
        subtitle.setStyleSheet("font-size: 12px; color: #475569;")
        title_col.addWidget(page_title)
        title_col.addWidget(subtitle)

        hdr.addWidget(icon_bg)
        hdr.addLayout(title_col)
        hdr.addStretch()
        layout.addLayout(hdr)
        layout.addSpacing(20)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)
        layout.addSpacing(16)

        # credentials.json section
        creds_has = os.path.exists(GOOGLE_CREDENTIALS_PATH)
        self._creds_frame = QFrame()
        self._creds_frame.setStyleSheet(
            "QFrame { background: rgba(16,185,129,0.06); border: 1px solid rgba(16,185,129,0.15);"
            " border-radius: 10px; }" if creds_has else
            "QFrame { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.18);"
            " border-radius: 10px; }"
        )
        cf_layout = QVBoxLayout(self._creds_frame)
        cf_layout.setContentsMargins(14, 11, 14, 11)
        cf_layout.setSpacing(7)

        cf_top = QHBoxLayout()
        cf_top.setSpacing(10)
        self._creds_icon = QLabel("✓" if creds_has else "⚠")
        self._creds_icon.setStyleSheet(
            f"font-size: 15px; color: {'#34d399' if creds_has else '#fbbf24'};"
        )
        cf_top.addWidget(self._creds_icon)

        creds_col = QVBoxLayout()
        creds_col.setSpacing(2)
        self._creds_title = QLabel(
            "credentials.json loaded" if creds_has else "credentials.json required"
        )
        self._creds_title.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {'#34d399' if creds_has else '#fbbf24'};"
        )
        self._creds_sub = QLabel(
            "Google API credentials are ready." if creds_has else
            "Download from Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client."
        )
        self._creds_sub.setStyleSheet("font-size: 11px; color: #64748b;")
        self._creds_sub.setWordWrap(True)
        creds_col.addWidget(self._creds_title)
        creds_col.addWidget(self._creds_sub)
        cf_top.addLayout(creds_col, 1)
        cf_layout.addLayout(cf_top)

        self._load_creds_btn = QPushButton(
            "Change credentials.json" if creds_has else "Browse for credentials.json…"
        )
        self._load_creds_btn.setObjectName("secondaryButton")
        self._load_creds_btn.clicked.connect(self._browse_credentials)
        cf_layout.addWidget(self._load_creds_btn)
        layout.addWidget(self._creds_frame)
        layout.addSpacing(14)

        # Status
        self.status_label = QLabel("Not connected")
        self.status_label.setObjectName("statusBad")
        layout.addWidget(self.status_label)
        layout.addSpacing(10)

        # Connected badge
        self.connected_frame = QFrame()
        self.connected_frame.setStyleSheet(
            "QFrame { background: rgba(16,185,129,0.06); border: 1px solid rgba(16,185,129,0.15);"
            " border-radius: 10px; }"
        )
        cf2 = QHBoxLayout(self.connected_frame)
        cf2.setContentsMargins(14, 10, 14, 10)
        cf2.setSpacing(10)
        check = QLabel("✓")
        check.setFixedSize(30, 30)
        check.setAlignment(Qt.AlignCenter)
        check.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #34d399;"
            "background: rgba(16,185,129,0.12); border-radius: 8px;"
        )
        cf2.addWidget(check)
        badge_lbl = QLabel("Google Calendar connected")
        badge_lbl.setObjectName("statusGood")
        cf2.addWidget(badge_lbl)
        cf2.addStretch()
        self.connected_frame.hide()
        layout.addWidget(self.connected_frame)
        layout.addSpacing(16)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.connect_btn = QPushButton("Connect Google Calendar")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        self.connect_btn.setEnabled(creds_has)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setObjectName("secondaryButton")
        self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self.disconnect_btn.hide()

        btn_row.addWidget(self.connect_btn)
        btn_row.addWidget(self.disconnect_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # How-to info
        layout.addSpacing(16)
        how_lbl = QLabel("HOW TO GET credentials.json")
        how_lbl.setObjectName("cardTitle")
        layout.addWidget(how_lbl)
        layout.addSpacing(8)

        for icon, text in [
            ("1️⃣", "console.cloud.google.com → select or create a project."),
            ("2️⃣", "Enable Google Calendar API under APIs & Services → Library."),
            ("3️⃣", "APIs & Services → Credentials → Create → OAuth 2.0 Client ID (Desktop App)."),
            ("4️⃣", "Download JSON, then click 'Browse for credentials.json' above."),
        ]:
            row = QHBoxLayout()
            row.setSpacing(8)
            i_lbl = QLabel(icon)
            i_lbl.setFixedWidth(22)
            i_lbl.setStyleSheet("font-size: 12px;")
            t_lbl = QLabel(text)
            t_lbl.setObjectName("subText")
            t_lbl.setWordWrap(True)
            row.addWidget(i_lbl)
            row.addWidget(t_lbl, 1)
            layout.addLayout(row)

        return card

    # ── Events card ───────────────────────────────────────────────────
    def _build_events_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("authCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        # Header row
        hdr_row = QHBoxLayout()
        hdr_lbl = QLabel("UPCOMING EVENTS")
        hdr_lbl.setObjectName("cardTitle")
        hdr_row.addWidget(hdr_lbl)
        hdr_row.addStretch()

        self.refresh_btn = QPushButton("↻  Refresh")
        self.refresh_btn.setObjectName("secondaryButton")
        self.refresh_btn.setFixedHeight(30)
        self.refresh_btn.clicked.connect(self._load_events)
        hdr_row.addWidget(self.refresh_btn)
        layout.addLayout(hdr_row)

        self._events_status = QLabel("Connect Google Calendar to view events.")
        self._events_status.setObjectName("subText")
        self._events_status.setStyleSheet("font-size: 11px; color: #334155;")
        layout.addWidget(self._events_status)

        self.events_list = QListWidget()
        self.events_list.setMinimumHeight(160)
        self.events_list.setMaximumHeight(320)
        self.events_list.addItem("No events loaded")
        layout.addWidget(self.events_list)

        return card

    # ─────────────────────────────────────────────────────────────────
    # Logic
    # ─────────────────────────────────────────────────────────────────
    def _browse_credentials(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select credentials.json",
            os.path.expanduser("~"), "JSON files (*.json)",
        )
        if not path:
            return
        try:
            shutil.copy(path, GOOGLE_CREDENTIALS_PATH)
        except Exception as e:
            self._set_status(f"Could not copy file: {e}", "#f87171")
            return
        self._creds_frame.setStyleSheet(
            "QFrame { background: rgba(16,185,129,0.06); border: 1px solid rgba(16,185,129,0.15);"
            " border-radius: 10px; }"
        )
        self._creds_icon.setText("✓")
        self._creds_icon.setStyleSheet("font-size: 15px; color: #34d399;")
        self._creds_title.setText("credentials.json loaded")
        self._creds_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #34d399;")
        self._creds_sub.setText("Google API credentials are ready.")
        self._load_creds_btn.setText("Change credentials.json")
        self.connect_btn.setEnabled(True)
        self._set_status("credentials.json loaded — click Connect to sign in.", "#34d399")

    def _try_silent_reconnect(self):
        if os.path.exists(GOOGLE_TOKEN_PATH):
            self._set_status("Reconnecting…", "#9da8b4")
            self.connect_btn.setEnabled(False)
            self._run_auth(interactive=False)

    def _on_connect_clicked(self):
        self._set_status("Opening Google sign-in in browser…", "#9da8b4")
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

    def _run_auth(self, interactive: bool):
        self._auth_thread = _CalendarAuthThread(interactive=interactive)
        self._auth_thread.success.connect(self._on_auth_success)
        self._auth_thread.failed.connect(self._on_auth_failed)
        self._auth_thread.start()

    def _on_auth_success(self, service):
        self._service = service
        self._show_connected()
        self.connected.emit(service)
        self._load_events()

    def _on_auth_failed(self, error: str):
        self._set_status(f"{error}", "#f87171")
        self.connect_btn.setEnabled(os.path.exists(GOOGLE_CREDENTIALS_PATH))

    # ── Events ────────────────────────────────────────────────────────
    def _load_events(self):
        if not self._service:
            self._events_status.setText("Not connected.")
            return
        self.refresh_btn.setEnabled(False)
        self._events_status.setText("Syncing…")
        if self._events_thread and self._events_thread.isRunning():
            return
        self._events_thread = CalendarEventsThread(service=self._service)
        self._events_thread.events_ready.connect(self._on_events_ready)
        self._events_thread.status_changed.connect(
            lambda msg, color: self._events_status.setText(msg)
        )
        self._events_thread.finished.connect(lambda: self.refresh_btn.setEnabled(True))
        self._events_thread.start()

    def _on_events_ready(self, events: list):
        self.events_updated.emit(events)
        self.events_list.clear()
        if not events:
            self.events_list.addItem("No upcoming events")
            return
        for ev in events:
            summary = ev.get("summary", "Untitled")
            start   = ev.get("start", {})
            raw     = start.get("dateTime", start.get("date", ""))
            self.events_list.addItem(f"{self._fmt_time(raw)}   ·   {summary}")

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

    # ── Create event ──────────────────────────────────────────────────
    def _create_event(self):
        title = self.cal_title_input.text().strip()
        if not title:
            self._create_status.setText("Event title is required.")
            self._create_status.setStyleSheet("color: #f87171; font-size: 11px;")
            return
        start_dt = self.cal_start_input.dateTime().toPyDateTime()
        end_dt   = self.cal_end_input.dateTime().toPyDateTime()
        if end_dt <= start_dt:
            self._create_status.setText("End time must be after start time.")
            self._create_status.setStyleSheet("color: #f87171; font-size: 11px;")
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
        self._create_status.setText("Creating…")
        self._create_status.setStyleSheet("color: #9da8b4; font-size: 11px;")

        self._create_thread = CalendarCreateThread(payload, service=self._service)
        self._create_thread.status_changed.connect(self._on_create_status)
        self._create_thread.created.connect(self._on_event_created)
        self._create_thread.finished.connect(
            lambda: self.create_event_btn.setEnabled(True)
        )
        self._create_thread.start()

    def _on_create_status(self, msg: str, color: str):
        self._create_status.setText(msg)
        self._create_status.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _on_event_created(self):
        self.cal_title_input.clear()
        self.cal_location_input.clear()
        self.cal_desc_input.clear()
        self.cal_start_input.setDateTime(QDateTime.currentDateTime())
        self.cal_end_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self._load_events()
        self.event_created.emit()

    # ── UI helpers ────────────────────────────────────────────────────
    def _set_status(self, msg: str, color: str):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px; padding: 4px 0;")

    def _show_connected(self):
        self._set_status("● Connected", "#34d399")
        self.connected_frame.show()
        self.connect_btn.hide()
        self.disconnect_btn.show()
        self._add_hint.setText("Fill in the form and click Create Event.")
        self._add_hint.setStyleSheet("font-size: 11px; color: #34d399;")
        self.create_event_btn.setEnabled(True)
        self._events_status.setText("Loaded.")

    def _show_disconnected(self):
        self._set_status("Not connected", "#f87171")
        self.connected_frame.hide()
        self.connect_btn.show()
        self.connect_btn.setEnabled(os.path.exists(GOOGLE_CREDENTIALS_PATH))
        self.disconnect_btn.hide()
        self._add_hint.setText("Connect Google Calendar (→) to create events.")
        self._add_hint.setStyleSheet("font-size: 11px; color: #334155;")
        self.create_event_btn.setEnabled(False)
        self.events_list.clear()
        self.events_list.addItem("No events loaded")
        self._events_status.setText("Connect Google Calendar to view events.")
