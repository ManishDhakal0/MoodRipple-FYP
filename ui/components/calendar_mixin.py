# ui/components/calendar_mixin.py
# Mixin for DashboardPage — Google Calendar quick-view logic.

from datetime import datetime

from core.calendar_thread import CalendarEventsThread


def _set_label_color(label, color: str, size: str = "12px"):
    css = f"color: {color}; font-size: {size};"
    if label.styleSheet() != css:
        label.setStyleSheet(css)


class CalendarMixin:
    """
    Calendar quick-view methods mixed into DashboardPage.
    Assumes self has: calendar_service, calendar_thread, cal_status_lbl,
    cal_list, refresh_cal_btn, status_changed.
    """

    def refresh_calendar(self):
        if not self.calendar_service:
            self.cal_status_lbl.setText(
                "Not connected — go to  📅  Calendar page to connect.")
            return
        self.refresh_cal_btn.setEnabled(False)
        self.cal_status_lbl.setText("Syncing…")
        if self.calendar_thread and self.calendar_thread.isRunning():
            return
        self.calendar_thread = CalendarEventsThread(service=self.calendar_service)
        self.calendar_thread.events_ready.connect(self._on_calendar_events)
        self.calendar_thread.status_changed.connect(
            lambda msg, color: _set_label_color(self.cal_status_lbl, color))
        self.calendar_thread.finished.connect(
            lambda: self.refresh_cal_btn.setEnabled(True))
        self.calendar_thread.start()

    def _on_calendar_events(self, events: list):
        self.cal_list.clear()
        if not events:
            self.cal_list.addItem("No upcoming events")
            return
        for ev in events:
            summary = ev.get("summary", "Untitled")
            start   = ev.get("start", {})
            raw     = start.get("dateTime", start.get("date", ""))
            self.cal_list.addItem(f"{self._fmt_time(raw)}   ·   {summary}")

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
