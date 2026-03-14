# core/calendar_thread.py
# Google Calendar background threads: fetch events + create event

import os
from datetime import datetime, timezone
from PyQt5.QtCore import QThread, pyqtSignal

from core.constants import GOOGLE_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH, GOOGLE_SCOPES


def _get_service(provided_service=None):
    """Return a Calendar service — uses provided if available, else re-authenticates."""
    if provided_service is not None:
        return provided_service
    from fyp_calendar import get_calendar_service
    return get_calendar_service()


class CalendarEventsThread(QThread):
    events_ready   = pyqtSignal(list)
    status_changed = pyqtSignal(str, str)

    def __init__(self, service=None):
        super().__init__()
        self.service = service

    def run(self):
        try:
            svc = _get_service(self.service)
            now = datetime.now(timezone.utc).isoformat()
            result = svc.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            self.events_ready.emit(result.get("items", []))
            self.status_changed.emit("Calendar synced.", "#1DB954")
        except Exception as e:
            self.status_changed.emit(f"Sync failed: {e}", "#e05555")
            self.events_ready.emit([])


class CalendarCreateThread(QThread):
    status_changed = pyqtSignal(str, str)
    created        = pyqtSignal()

    def __init__(self, payload: dict, service=None):
        super().__init__()
        self.payload = payload
        self.service = service

    def run(self):
        try:
            svc = _get_service(self.service)
            svc.events().insert(calendarId="primary", body=self.payload).execute()
            self.status_changed.emit("Event created successfully.", "#1DB954")
            self.created.emit()
        except Exception as e:
            self.status_changed.emit(f"Create failed: {e}", "#e05555")
