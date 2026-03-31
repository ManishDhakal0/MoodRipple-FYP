# ui/bridge.py
# QWebChannel bridge — bidirectional Python ↔ JS communication.
# Signals  (Python → JS): connect in JS with  bridge.signalName.connect(cb)
# Slots    (JS → Python): call from JS with    bridge.slotName(args)

import json
import base64

import cv2
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class AppBridge(QObject):
    # ── Python → JS signals ───────────────────────────────────────────────────
    frame_updated    = pyqtSignal(str)           # base64 JPEG data-URL
    emotion_updated  = pyqtSignal(str, float, str)  # emotion, confidence, mood
    scores_updated   = pyqtSignal(str)           # JSON {happy, neutral, sad, ...}
    drowsy_updated   = pyqtSignal(str)           # JSON drowsiness data
    status_updated   = pyqtSignal(str, str)      # message, colour
    spotify_updated  = pyqtSignal(str)           # JSON track/status
    calendar_updated = pyqtSignal(str)           # JSON events list
    conn_updated     = pyqtSignal(bool, bool)    # spotify_ok, calendar_ok
    chat_message     = pyqtSignal(str, bool)     # text, is_user
    tts_state        = pyqtSignal(bool)          # TTS enabled/disabled
    mic_status       = pyqtSignal(str)           # "idle" | "recording" | "transcribing"
    settings_data    = pyqtSignal(str)           # JSON settings dict
    analytics_data   = pyqtSignal(str)           # JSON analytics
    auth_result      = pyqtSignal(str)           # JSON {ok, error, user}
    loading_status   = pyqtSignal(str)           # loading screen status text
    page_changed     = pyqtSignal(int)           # active page index
    window_state     = pyqtSignal(str)           # "maximized" | "normal"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._handlers: dict = {}
        self._frame_tick = 0   # throttle: emit every 2nd frame ≈ 7-8 fps

    # ── Handler registration (called by window / auth window) ─────────────────
    def bind(self, action: str, handler):
        self._handlers[action] = handler

    def _call(self, action: str, *args):
        fn = self._handlers.get(action)
        if fn:
            try:
                fn(*args)
            except Exception as exc:
                print(f"[Bridge] handler '{action}' error: {exc}", flush=True)

    # ── Frame helper (called from window, not a slot) ─────────────────────────
    def push_frame(self, bgr_frame):
        """Convert BGR numpy frame → base64 JPEG → emit to JS."""
        self._frame_tick += 1
        if self._frame_tick % 2 != 0:
            return
        try:
            ok, buf = cv2.imencode('.jpg', bgr_frame,
                                   [cv2.IMWRITE_JPEG_QUALITY, 65])
            if ok:
                b64 = base64.b64encode(buf.tobytes()).decode('ascii')
                self.frame_updated.emit(f"data:image/jpeg;base64,{b64}")
        except Exception:
            pass

    # ── JS → Python slots ─────────────────────────────────────────────────────
    @pyqtSlot(str, str)
    def login(self, username: str, password: str):
        self._call("login", username, password)

    @pyqtSlot(str, str, str)
    def register(self, username: str, email: str, password: str):
        self._call("register", username, email, password)

    @pyqtSlot(int)
    def navigate(self, index: int):
        self._call("navigate", index)

    @pyqtSlot()
    def start_detection(self):
        self._call("start_detection")

    @pyqtSlot()
    def stop_detection(self):
        self._call("stop_detection")

    @pyqtSlot()
    def connect_spotify(self):
        self._call("connect_spotify")

    @pyqtSlot()
    def disconnect_spotify(self):
        self._call("disconnect_spotify")

    @pyqtSlot()
    def connect_calendar(self):
        self._call("connect_calendar")

    @pyqtSlot()
    def disconnect_calendar(self):
        self._call("disconnect_calendar")

    @pyqtSlot(str)
    def send_chat(self, message: str):
        self._call("send_chat", message)

    @pyqtSlot(str)
    def save_settings(self, json_str: str):
        try:
            self._call("save_settings", json.loads(json_str))
        except Exception:
            pass

    @pyqtSlot()
    def logout(self):
        self._call("logout")

    @pyqtSlot()
    def request_analytics(self):
        self._call("request_analytics")

    @pyqtSlot(int)
    def request_analytics_range(self, days: int):
        self._call("request_analytics_range", days)

    @pyqtSlot()
    def request_settings(self):
        self._call("request_settings")

    @pyqtSlot(str)
    def analyze_text(self, text: str):
        self._call("analyze_text", text)

    @pyqtSlot()
    def toggle_tts(self):
        self._call("toggle_tts")

    @pyqtSlot()
    def mic_toggle(self):
        self._call("mic_toggle")

    # Window controls — called from JS header buttons
    @pyqtSlot()
    def minimize_win(self):
        self._call("minimize_win")

    @pyqtSlot()
    def maximize_win(self):
        self._call("maximize_win")

    @pyqtSlot()
    def close_win(self):
        self._call("close_win")

    # JS-driven window drag: sends delta per mousemove
    @pyqtSlot(int, int)
    def drag_move(self, dx: int, dy: int):
        self._call("drag_move", dx, dy)
