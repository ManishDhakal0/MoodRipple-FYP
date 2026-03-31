# ui/window.py
# MainWindow — frameless QWebEngineView showing web/app.html.
# All existing page logic runs in the background (hidden); signals relay
# through AppBridge so the HTML frontend stays in sync.

import json
import os
from datetime import datetime, timezone, timedelta

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
from PyQt5.QtCore    import pyqtSignal, Qt, QPoint, QUrl, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtWebChannel       import QWebChannel

from ui.bridge import AppBridge

from ui.pages.dashboard        import DashboardPage
from ui.pages.spotify_connect  import SpotifyConnectPage
from ui.pages.calendar_connect import CalendarConnectPage
from ui.pages.analytics        import AnalyticsPage
from ui.pages.settings         import SettingsPage
from ui.pages.chat_page        import ChatPage
from ui.widgets.mood_widget    import NowMoodWidget
from core.auth                 import AuthManager
from core.settings_manager     import SettingsManager


# ── Helpers ───────────────────────────────────────────────────────────────────
def _parse_dt(raw: str):
    if not raw:
        return None
    if "T" not in raw:
        try:
            return datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None

def _fmt_clock(dt: datetime) -> str:
    try:
        return dt.astimezone().strftime("%I:%M %p").lstrip("0")
    except Exception:
        return ""

def _ev_key(ev: dict) -> str:
    start = ev.get("start", {})
    return ev.get("id") or (ev.get("summary","") + start.get("dateTime", start.get("date","")))


# ── ChatPage subclass that emits bubble_added signal ──────────────────────────
class _ChatPageBridge(ChatPage):
    """Thin subclass — intercepts _add_bubble so bridge can push to JS."""
    bubble_added = pyqtSignal(str, bool)

    def _add_bubble(self, text: str, is_user: bool):
        super()._add_bubble(text, is_user)
        self.bubble_added.emit(text, is_user)


# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    logged_out = pyqtSignal()

    def __init__(self, user: dict = None):
        super().__init__()
        self._user          = user or {}
        self._raw_events:   list = []
        self._alerted_evs:  set  = set()
        self._snoozed_evs:  dict = {}
        self._banner_key:   str  = ""
        self._dismissed_key:str  = ""
        self._drag_pos: QPoint   = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setWindowTitle("MoodRipple")
        self.setMinimumSize(1200, 740)
        self.resize(1440, 860)

        # Bridge
        self._bridge  = AppBridge(self)
        self._channel = QWebChannel(self)
        self._channel.registerObject("bridge", self._bridge)

        # Instantiate all page logic (hidden)
        self._init_pages()

        # Wire bridge ↔ pages
        self._wire_bridge()

        # Build web UI
        self._build_web_ui()

        # Emit user info to JS once the page loads
        self._view.loadFinished.connect(self._on_load_finished)

        # Calendar check timer
        self._event_timer = QTimer(self)
        self._event_timer.setInterval(30_000)
        self._event_timer.timeout.connect(self._check_upcoming)
        self._event_timer.start()

        # Auto-start detection
        if SettingsManager.get("auto_start_detection"):
            QTimer.singleShot(2000, self.dashboard.start_detection)

    # ── Web UI ────────────────────────────────────────────────────────────────
    def _build_web_ui(self):
        self._view = QWebEngineView()
        self._view.page().setWebChannel(self._channel)
        s = self._view.settings()
        s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessLocalUrls, True)
        self._view.setContextMenuPolicy(Qt.NoContextMenu)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)
        self.setCentralWidget(container)

        html_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "web", "app.html")
        self._view.load(QUrl.fromLocalFile(html_path))

    def _on_load_finished(self, ok: bool):
        if not ok:
            return
        # Push user info
        u = self._user.get("username", "User")
        self._bridge.auth_result.emit(json.dumps({"user": {"username": u}}))
        # Push actual connection states (may already be connected via silent reconnect)
        sp_ok  = bool(getattr(self.spotify_page,  '_sp',      None))
        cal_ok = bool(getattr(self.calendar_page, '_service', None))
        self._bridge.conn_updated.emit(sp_ok, cal_ok)
        # Push current Spotify status
        self._push_spotify_status()
        # If calendar already connected, push its events too
        if cal_ok:
            self.calendar_page._load_events()

    # ── Page initialisation ───────────────────────────────────────────────────
    def _init_pages(self):
        """Create all page objects. They live in memory but are never shown."""
        self._page_host = QWidget()  # invisible parent keeps Qt happy

        self.dashboard = DashboardPage(self._page_host)
        self.dashboard.status_changed.connect(self._bridge.status_updated)

        self.spotify_page = SpotifyConnectPage(self._page_host)
        self.spotify_page.connected.connect(self._on_spotify_connected)
        self.spotify_page.disconnected.connect(self._on_spotify_disconnected)
        self.spotify_page.preferences_changed.connect(self.dashboard.set_music_prefs)
        self.dashboard.set_music_prefs(self.spotify_page.get_prefs())

        self.calendar_page = CalendarConnectPage(self._page_host)
        self.calendar_page.connected.connect(self._on_calendar_connected)
        self.calendar_page.disconnected.connect(self._on_calendar_disconnected)
        self.calendar_page.event_created.connect(self.dashboard.refresh_calendar)
        self.calendar_page.events_updated.connect(self._on_events_updated)

        self.analytics_page = AnalyticsPage(db=self.dashboard.emotion_db(),
                                            parent=self._page_host)

        self.settings_page = SettingsPage(self._page_host)
        self.settings_page.settings_changed.connect(self._on_settings_changed)

        self.chat_page = _ChatPageBridge(dashboard=self.dashboard,
                                         parent=self._page_host)
        self.chat_page.bubble_added.connect(self._bridge.chat_message)
        self.dashboard.emotion_detected.connect(self.chat_page.inject_emotion_message)

        self._mood_widget = NowMoodWidget()
        self.dashboard.set_mood_widget(self._mood_widget)
        if SettingsManager.get("show_mood_widget"):
            self._mood_widget.show()

    # ── Bridge wiring ─────────────────────────────────────────────────────────
    def _wire_bridge(self):
        b = self._bridge

        # JS → Python
        b.bind("navigate",            self._navigate)
        b.bind("start_detection",     self._start_detection)
        b.bind("stop_detection",      self.dashboard.stop_detection)
        b.bind("connect_spotify",     self.spotify_page._on_connect_clicked)
        b.bind("disconnect_spotify",  self.spotify_page._on_disconnect_clicked)
        b.bind("connect_calendar",    self.calendar_page._on_connect_clicked)
        b.bind("disconnect_calendar", self.calendar_page._on_disconnect_clicked)
        b.bind("send_chat",           lambda msg: self.chat_page.send_message(msg))
        b.bind("save_settings",       self._save_settings)
        b.bind("logout",              self._on_logout)
        b.bind("request_analytics",       self._push_analytics)
        b.bind("request_analytics_range", self._push_analytics_days)
        b.bind("request_settings",        self._push_settings)
        b.bind("analyze_text",        self._analyze_text)
        b.bind("toggle_tts",          self._web_toggle_tts)
        b.bind("mic_toggle",          self._web_mic_toggle)
        b.bind("minimize_win",        lambda: self.showMinimized())
        b.bind("maximize_win",        self._toggle_maximize)
        b.bind("close_win",           lambda: self.close())
        b.bind("drag_move",           self._drag_move)

    # ── Detection ──────────────────────────────────────────────────────────────
    def _start_detection(self):
        self.dashboard.start_detection()
        # Connect frame + emotion signals now (thread created inside start_detection)
        QTimer.singleShot(500, self._connect_detection_signals)

    def _connect_detection_signals(self):
        t = getattr(self.dashboard, 'detection_thread', None)
        if t is None:
            return
        # Avoid double-connecting
        try:
            t.frame_ready.disconnect(self._bridge.push_frame)
        except TypeError:
            pass
        try:
            t.emotion_ready.disconnect(self._on_emotion_ready)
        except TypeError:
            pass
        try:
            t.scores_ready.disconnect(self._on_scores_ready)
        except TypeError:
            pass
        try:
            t.drowsy_ready.disconnect(self._on_drowsy_ready)
        except TypeError:
            pass
        t.frame_ready.connect(self._bridge.push_frame)
        t.emotion_ready.connect(self._on_emotion_ready)
        t.scores_ready.connect(self._on_scores_ready)
        t.drowsy_ready.connect(self._on_drowsy_ready)

    def _on_emotion_ready(self, emotion: str, confidence: float, mood: str):
        self._bridge.emotion_updated.emit(emotion, confidence, mood)

    def _on_scores_ready(self, scores: dict):
        self._bridge.scores_updated.emit(json.dumps(scores))

    def _on_drowsy_ready(self, data: dict):
        self._bridge.drowsy_updated.emit(json.dumps(data))

    # ── Navigation ────────────────────────────────────────────────────────────
    def _navigate(self, index: int):
        if index == 3:
            self.analytics_page.refresh()
            self._push_analytics()

    # ── Drag ──────────────────────────────────────────────────────────────────
    def _drag_move(self, dx: int, dy: int):
        self.move(self.pos() + QPoint(dx, dy))

    # ── Maximize / restore ────────────────────────────────────────────────────
    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event):
        from PyQt5.QtCore import QEvent
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            state = "maximized" if self.isMaximized() else "normal"
            self._bridge.window_state.emit(state)

    # ── Analytics ─────────────────────────────────────────────────────────────
    def _push_analytics(self, *_):
        self._push_analytics_days(7)

    def _push_analytics_days(self, days: int = 7):
        try:
            db = self.dashboard.emotion_db()
            stats = db.get_stats(days) if hasattr(db, "get_stats") else {}
            self._bridge.analytics_data.emit(json.dumps(stats))
        except Exception:
            self._bridge.analytics_data.emit(json.dumps({}))

    # ── Settings ──────────────────────────────────────────────────────────────
    def _push_settings(self, *_):
        data = {
            "auto_start_detection":  bool(SettingsManager.get("auto_start_detection")),
            "auto_export_session":   bool(SettingsManager.get("auto_export_session")),
            "show_mood_widget":      bool(SettingsManager.get("show_mood_widget")),
            "mood_cooldown_secs":    int(SettingsManager.get("mood_cooldown_secs", 30)),
            "openai_api_key":        SettingsManager.get("openai_api_key", ""),
            "smart_drowsy_response": bool(SettingsManager.get("smart_drowsy_response", True)),
            "drowsy_night_hour":     int(SettingsManager.get("drowsy_night_hour", 22)),
            "drowsy_day_music":      SettingsManager.get("drowsy_day_music", "drowsy"),
            "drowsy_night_music":    SettingsManager.get("drowsy_night_music", "calm"),
            "sad_music_response":    SettingsManager.get("sad_music_response", "comfort"),
        }
        self._bridge.settings_data.emit(json.dumps(data))

    def _save_settings(self, data: dict):
        for k, v in data.items():
            SettingsManager.set(k, v)
        self._on_settings_changed(data)
        self._bridge.status_updated.emit("Settings saved.", "#34d399")

    def _analyze_text(self, text: str):
        try:
            self.dashboard.text_input.setPlainText(text)
            self.dashboard.analyze_text_emotion()
        except Exception as e:
            self._bridge.status_updated.emit(f"Text analysis error: {e}", "#f87171")

    # ── TTS / STT (web frontend) ─────────────────────────────────────────────
    def _web_toggle_tts(self):
        cp = self.chat_page
        cp._tts_enabled = not cp._tts_enabled
        self._bridge.tts_state.emit(cp._tts_enabled)
        if cp._tts_enabled and not cp._tts.available():
            self._bridge.chat_message.emit(
                "⚠ pyttsx3 not installed. Run: pip install pyttsx3", False)
            cp._tts_enabled = False
            self._bridge.tts_state.emit(False)

    def _web_mic_toggle(self):
        from core.settings_manager import SettingsManager
        cp = self.chat_page
        # If already recording — stop
        if cp._rec_thread and cp._rec_thread.isRunning():
            cp._rec_thread.stop_recording()
            self._bridge.mic_status.emit("idle")
            return
        # Check API key
        api_key = SettingsManager.get("openai_api_key", "")
        if not api_key:
            self._bridge.chat_message.emit(
                "⚠ Set your OpenAI API key in Settings → API Keys to use voice input.", False)
            return
        # Start recording thread
        from services.stt_service import RecordingThread
        cp._rec_thread = RecordingThread(api_key=api_key, parent=cp)
        cp._rec_thread.transcription_ready.connect(self._on_web_transcription)
        cp._rec_thread.error_occurred.connect(self._on_web_rec_error)
        cp._rec_thread.status_changed.connect(self._bridge.mic_status)
        cp._rec_thread.start()
        self._bridge.mic_status.emit("recording")

    def _on_web_transcription(self, text: str):
        self._bridge.mic_status.emit("idle")
        if text:
            self.chat_page.send_message(text)

    def _on_web_rec_error(self, msg: str):
        self._bridge.mic_status.emit("idle")
        self._bridge.chat_message.emit(f"⚠ {msg}", False)

    # ── Spotify ───────────────────────────────────────────────────────────────
    def _on_spotify_connected(self, sp, display_name: str, product: str):
        self.dashboard.set_spotify(sp, display_name, product)
        self._bridge.conn_updated.emit(True,
            bool(getattr(self.dashboard, '_calendar_service', None)))
        self._push_spotify_status(
            connected=True, display_name=display_name, product=product)
        self._bridge.status_updated.emit(
            f"Spotify connected — {display_name} ({product})", "#10b981")

    def _on_spotify_disconnected(self):
        self.dashboard.clear_spotify()
        self._bridge.conn_updated.emit(False,
            bool(getattr(self.dashboard, '_calendar_service', None)))
        self._push_spotify_status(connected=False)
        self._bridge.status_updated.emit("Spotify disconnected.", "#475569")

    def _push_spotify_status(self, connected=False, display_name="", product=""):
        data = {"connected": connected, "display_name": display_name,
                "track": "—", "artist": "—", "art_emoji": "🎵"}
        sp = getattr(self.dashboard, 'sp', None)
        if sp:
            try:
                cur = sp.current_playback()
                if cur and cur.get("item"):
                    item = cur["item"]
                    data["track"]  = item.get("name", "—")
                    data["artist"] = ", ".join(
                        a["name"] for a in item.get("artists", []))
                    data["connected"] = True
            except Exception:
                pass
        self._bridge.spotify_updated.emit(json.dumps(data))

    # ── Calendar ──────────────────────────────────────────────────────────────
    def _on_calendar_connected(self, service):
        self.dashboard.set_calendar_service(service)
        self._bridge.conn_updated.emit(
            bool(getattr(self.dashboard, 'sp', None)), True)
        self._bridge.status_updated.emit("Google Calendar connected.", "#10b981")

    def _on_calendar_disconnected(self):
        self.dashboard.clear_calendar_service()
        self._bridge.conn_updated.emit(
            bool(getattr(self.dashboard, 'sp', None)), False)
        self._raw_events = []
        self._bridge.calendar_updated.emit(json.dumps([]))
        self._bridge.status_updated.emit("Calendar disconnected.", "#475569")

    def _on_events_updated(self, events: list):
        self._raw_events = events
        self._bridge.calendar_updated.emit(json.dumps(events))
        self._check_upcoming()

    # ── Meeting banner ────────────────────────────────────────────────────────
    def _check_upcoming(self):
        if not self._raw_events:
            return
        now     = datetime.now(timezone.utc)
        next_ev = None; min_secs = None
        for ev in self._raw_events:
            start = ev.get("start", {})
            dt    = _parse_dt(start.get("dateTime", start.get("date", "")))
            if dt is None:
                continue
            secs = (dt - now).total_seconds()
            if 0 <= secs <= 3600:
                if min_secs is None or secs < min_secs:
                    min_secs = secs; next_ev = (ev, dt, secs)
        if next_ev is None:
            return
        ev, dt, secs = next_ev
        mins = int(secs / 60)
        key  = _ev_key(ev)
        if key == self._dismissed_key:
            return
        self._banner_key = key
        if mins <= 5:
            col = "#ef4444"
        elif mins <= 15:
            col = "#f97316"
        elif mins <= 30:
            col = "#fbbf24"
        else:
            col = "#60a5fa"
        title = ev.get("summary", "Untitled")
        label = f"in {mins} min" if mins > 0 else "starting NOW"
        js = (f"document.getElementById('eventsBanner').classList.add('visible');"
              f"document.getElementById('bannerText').innerHTML="
              f"\"<span style='color:{col};font-weight:700'>{title}</span>"
              f"  ·  <span style='color:{col}'>{label}</span>\";")
        self._view.page().runJavaScript(js)

    # ── Settings changed ──────────────────────────────────────────────────────
    def _on_settings_changed(self, updates: dict):
        show = updates.get("show_mood_widget",
                           SettingsManager.get("show_mood_widget"))
        if show:
            self._mood_widget.show()
        else:
            self._mood_widget.hide()

    # ── Logout / close ────────────────────────────────────────────────────────
    def _on_logout(self):
        AuthManager().clear_session()
        self.dashboard.shutdown()
        self.logged_out.emit()

    def closeEvent(self, event):
        if hasattr(self, '_event_timer'):
            self._event_timer.stop()
        if hasattr(self, '_mood_widget'):
            self._mood_widget.hide()
        if hasattr(self, 'dashboard'):
            self.dashboard.shutdown()
        event.accept()
