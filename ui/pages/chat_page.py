# ui/pages/chat_page.py
# MoodBot chat UI — bubbles, quick-action chips, input row, Whisper STT, pyttsx3 TTS.

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer

from services.chatbot import MoodBot, load_prefs, save_prefs
from services.tts_service import TTSService
from services.stt_service import RecordingThread


# ── Bubble / chip palette ────────────────────────────────────────────────────
_USER_BUBBLE = (
    "QLabel { background: rgba(245,197,24,0.14); color: #f0f0f8;"
    " border: 1px solid rgba(245,197,24,0.32);"
    " border-radius: 16px 16px 4px 16px;"
    " padding: 10px 14px; font-size: 13px; line-height: 1.5; }"
)
_BOT_BUBBLE = (
    "QLabel { background: rgba(255,255,255,0.05); color: #f0f0f8;"
    " border: 1px solid rgba(255,255,255,0.08);"
    " border-radius: 16px 16px 16px 4px;"
    " padding: 10px 14px; font-size: 13px; line-height: 1.5; }"
)
_CHIP_STYLE = (
    "QPushButton { background: rgba(245,197,24,0.08);"
    " color: rgba(240,240,248,0.70);"
    " border: 1px solid rgba(245,197,24,0.20);"
    " border-radius: 100px; padding: 5px 14px; font-size: 11px; }"
    "QPushButton:hover { background: rgba(245,197,24,0.16);"
    " color: #f0f0f8; border-color: rgba(245,197,24,0.38); }"
)
_INPUT_STYLE = (
    "QLineEdit { background: rgba(255,255,255,0.05);"
    " color: #f0f0f8; border: 1px solid rgba(255,255,255,0.09);"
    " border-radius: 100px; padding: 10px 18px; font-size: 13px; }"
    "QLineEdit:focus { border-color: rgba(245,197,24,0.50);"
    " background: rgba(245,197,24,0.05); }"
)
_SEND_STYLE = (
    "QPushButton { background: #F5C518; color: #080808;"
    " border: none; border-radius: 100px;"
    " font-size: 13px; font-weight: 700;"
    " min-width: 80px; min-height: 40px; padding: 0 20px; }"
    "QPushButton:hover { background: #FFD426; }"
    "QPushButton:disabled { background: rgba(245,197,24,0.15);"
    " color: rgba(240,240,248,0.30); }"
)
_MIC_IDLE_STYLE = (
    "QPushButton { background: rgba(255,255,255,0.05); color: #f0f0f8;"
    " border: 1px solid rgba(255,255,255,0.09);"
    " border-radius: 100px; min-width: 42px; min-height: 40px;"
    " font-size: 15px; padding: 0 12px; }"
    "QPushButton:hover { background: rgba(245,197,24,0.10);"
    " border-color: rgba(245,197,24,0.30); }"
)
_MIC_RECORDING_STYLE = (
    "QPushButton { background: rgba(239,68,68,0.18); color: #ef4444;"
    " border: 1px solid rgba(239,68,68,0.45);"
    " border-radius: 100px; min-width: 90px; min-height: 40px;"
    " font-size: 12px; font-weight: 600; padding: 0 12px; }"
    "QPushButton:hover { background: rgba(239,68,68,0.28); }"
)
_HDR_BTN_STYLE = (
    "QPushButton { background: transparent; color: rgba(240,240,248,0.25);"
    " border: 1px solid rgba(255,255,255,0.07); border-radius: 8px;"
    " font-size: 11px; padding: 4px 12px; }"
    "QPushButton:hover { color: #f0f0f8; border-color: rgba(255,255,255,0.14); }"
    "QPushButton:checked { color: #F5C518; border-color: rgba(245,197,24,0.40);"
    " background: rgba(245,197,24,0.08); }"
)

_QUICK_CHIPS = [
    ("⏭  Skip",      "skip"),
    ("⏸  Pause",     "pause"),
    ("🎭  My mood?", "how am i feeling?"),
    ("🌊  Calm",      "calm me down"),
    ("⚡  Energy",    "give me energy"),
]


class ChatPage(QWidget):
    def __init__(self, dashboard, parent=None):
        super().__init__(parent)
        self._dashboard   = dashboard
        self._bot         = MoodBot()
        self._tts         = TTSService()
        self._tts_enabled = False
        self._rec_thread  = None
        self._build_ui()
        # Welcome message
        QTimer.singleShot(300, self._show_welcome)

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_chat_area(), 1)
        root.addWidget(self._build_chips_row())
        root.addWidget(self._build_input_row())

    def _build_header(self) -> QFrame:
        hdr = QFrame()
        hdr.setFixedHeight(54)
        hdr.setStyleSheet(
            "QFrame { background: transparent; border: none; }")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(24, 0, 20, 0)

        icon = QLabel("◇")
        icon.setStyleSheet("font-size: 16px; color: #F5C518; background: transparent;")
        title = QLabel("MoodBot")
        title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #f0f0f8;"
            " background: transparent; margin-left: 8px;")
        sub = QLabel("Your emotion-aware music assistant")
        sub.setStyleSheet(
            "font-size: 11px; color: rgba(240,240,248,0.30);"
            " background: transparent; margin-left: 10px;")

        hl.addWidget(icon)
        hl.addWidget(title)
        hl.addWidget(sub, 0, Qt.AlignBottom)
        hl.addStretch()

        status_dot = QLabel("●")
        status_dot.setStyleSheet(
            "font-size: 8px; color: rgba(52,211,153,0.70); background: transparent;")
        status_lbl = QLabel("Online")
        status_lbl.setStyleSheet(
            "font-size: 11px; color: rgba(52,211,153,0.70);"
            " background: transparent; margin-left: 5px;")

        # TTS toggle
        self._tts_btn = QPushButton("🔇")
        self._tts_btn.setCheckable(True)
        self._tts_btn.setToolTip("Toggle voice responses (pyttsx3)")
        self._tts_btn.setStyleSheet(_HDR_BTN_STYLE)
        self._tts_btn.clicked.connect(self._toggle_tts)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(_HDR_BTN_STYLE)
        clear_btn.clicked.connect(self._clear_chat)

        hl.addWidget(status_dot)
        hl.addWidget(status_lbl)
        hl.addSpacing(14)
        hl.addWidget(self._tts_btn)
        hl.addSpacing(6)
        hl.addWidget(clear_btn)
        return hdr

    def _build_chat_area(self) -> QScrollArea:
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("background: transparent; border: none;")

        self._chat_widget = QWidget()
        self._chat_widget.setStyleSheet("background: transparent;")
        self._chat_layout = QVBoxLayout(self._chat_widget)
        self._chat_layout.setContentsMargins(20, 18, 20, 10)
        self._chat_layout.setSpacing(10)
        self._chat_layout.addStretch()

        self._scroll.setWidget(self._chat_widget)
        return self._scroll

    def _build_chips_row(self) -> QWidget:
        container = QWidget()
        container.setStyleSheet(
            "QWidget { background: transparent; border: none; }")
        row = QHBoxLayout(container)
        row.setContentsMargins(20, 10, 20, 10)
        row.setSpacing(8)

        for label, command in _QUICK_CHIPS:
            btn = QPushButton(label)
            btn.setStyleSheet(_CHIP_STYLE)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, cmd=command: self.send_message(cmd))
            row.addWidget(btn)
        row.addStretch()
        return container

    def _build_input_row(self) -> QWidget:
        container = QWidget()
        container.setStyleSheet(
            "QWidget { background: #0a0a0a;"
            " border-top: 1px solid rgba(255,255,255,0.04); }")
        row = QHBoxLayout(container)
        row.setContentsMargins(20, 12, 20, 16)
        row.setSpacing(10)

        self._input = QLineEdit()
        self._input.setPlaceholderText(
            "Ask MoodBot anything… (try 'skip', 'play lofi', 'how am I?')")
        self._input.setStyleSheet(_INPUT_STYLE)
        self._input.setMinimumHeight(42)
        self._input.returnPressed.connect(self._on_send)

        self._send_btn = QPushButton("Send →")
        self._send_btn.setStyleSheet(_SEND_STYLE)
        self._send_btn.clicked.connect(self._on_send)

        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setCheckable(True)
        self._mic_btn.setToolTip("Click to record voice (Whisper STT) — click again to stop")
        self._mic_btn.setStyleSheet(_MIC_IDLE_STYLE)
        self._mic_btn.clicked.connect(self._on_mic_toggle)

        row.addWidget(self._input, 1)
        row.addWidget(self._send_btn)
        row.addWidget(self._mic_btn)
        return container

    # ── TTS toggle ────────────────────────────────────────────────────────────
    def _toggle_tts(self):
        self._tts_enabled = self._tts_btn.isChecked()
        self._tts_btn.setText("🔊" if self._tts_enabled else "🔇")
        if not TTSService.available() and self._tts_enabled:
            self._add_bubble(
                "⚠ pyttsx3 not installed. Run: pip install pyttsx3", is_user=False)
            self._tts_enabled = False
            self._tts_btn.setChecked(False)
            self._tts_btn.setText("🔇")

    # ── Mic / STT ─────────────────────────────────────────────────────────────
    def _on_mic_toggle(self):
        if self._mic_btn.isChecked():
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        from core.settings_manager import SettingsManager
        api_key = SettingsManager.get("openai_api_key", "")
        if not api_key:
            self._add_bubble(
                "⚠ Set your OpenAI API key in Settings → API Keys to use voice input.",
                is_user=False)
            self._mic_btn.setChecked(False)
            return

        self._rec_thread = RecordingThread(api_key=api_key, parent=self)
        self._rec_thread.transcription_ready.connect(self._on_transcription)
        self._rec_thread.error_occurred.connect(self._on_rec_error)
        self._rec_thread.status_changed.connect(self._on_rec_status)
        self._rec_thread.start()

        self._mic_btn.setText("⏹  Stop")
        self._mic_btn.setStyleSheet(_MIC_RECORDING_STYLE)
        self._send_btn.setEnabled(False)

    def _stop_recording(self):
        if self._rec_thread and self._rec_thread.isRunning():
            self._rec_thread.stop_recording()
        self._mic_btn.setText("🎤")
        self._mic_btn.setStyleSheet(_MIC_IDLE_STYLE)
        self._mic_btn.setChecked(False)
        self._send_btn.setEnabled(True)

    def _on_transcription(self, text: str):
        self._stop_recording()
        if text:
            self.send_message(text)

    def _on_rec_error(self, msg: str):
        self._stop_recording()
        self._add_bubble(f"⚠ {msg}", is_user=False)

    def _on_rec_status(self, status: str):
        if status == "transcribing":
            self._mic_btn.setText("⏳ Thinking…")
            self._mic_btn.setStyleSheet(_MIC_RECORDING_STYLE)

    # ── Send ──────────────────────────────────────────────────────────────────
    def _on_send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.send_message(text)

    def send_message(self, text: str):
        self._add_bubble(text, is_user=True)
        context  = self._build_context()
        response = self._bot.process(text, context)
        QTimer.singleShot(180, lambda: self._deliver_response(response))

    def _deliver_response(self, response):
        self._add_bubble(response.text, is_user=False)
        if self._tts_enabled:
            self._tts.speak(response.text)
        if response.action:
            self._execute_action(response)

    def _execute_action(self, response):
        d      = self._dashboard
        action = response.action
        val    = response.value

        try:
            if action == "skip":
                d._next_track()
            elif action == "prev":
                d._prev_track()
            elif action in ("pause", "play"):
                d._toggle_play_pause()
            elif action == "volume":
                d._change_volume(int(val))
                if hasattr(d, "volume_slider"):
                    d.volume_slider.blockSignals(True)
                    d.volume_slider.setValue(int(val))
                    d.volume_slider.blockSignals(False)
            elif action == "set_language":
                prefs = load_prefs()
                prefs["language"] = val
                save_prefs(prefs)
                if hasattr(d, "set_music_prefs"):
                    d.set_music_prefs(prefs)
            elif action == "set_source":
                prefs = load_prefs()
                prefs["source"] = val
                save_prefs(prefs)
                if hasattr(d, "set_music_prefs"):
                    d.set_music_prefs(prefs)
            elif action == "set_mood":
                d.pending_mood = val
                if hasattr(d, "_sync_autoplay"):
                    d._sync_autoplay(force_replace=True)
        except Exception as e:
            self._add_bubble(f"⚠ Couldn't execute that: {e}", is_user=False)

    def _clear_chat(self):
        while self._chat_layout.count() > 1:   # keep trailing stretch
            item = self._chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        QTimer.singleShot(100, self._show_welcome)

    # ── Bubble ────────────────────────────────────────────────────────────────
    def _add_bubble(self, text: str, is_user: bool):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl.setStyleSheet(_USER_BUBBLE if is_user else _BOT_BUBBLE)
        lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        lbl.setMaximumWidth(int(self.width() * 0.76) if self.width() > 200 else 480)

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wl = QHBoxLayout(wrapper)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(0)

        if is_user:
            wl.addStretch()
            wl.addWidget(lbl)
        else:
            av = QLabel("◇")
            av.setFixedSize(28, 28)
            av.setAlignment(Qt.AlignCenter)
            av.setStyleSheet(
                "font-size: 12px; color: #F5C518; background: rgba(245,197,24,0.10);"
                " border-radius: 14px; border: none;")
            wl.addWidget(av, 0, Qt.AlignTop)
            wl.addSpacing(8)
            wl.addWidget(lbl)
            wl.addStretch()

        self._chat_layout.insertWidget(self._chat_layout.count() - 1, wrapper)
        QTimer.singleShot(60, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    # ── Context builder ───────────────────────────────────────────────────────
    def _build_context(self) -> dict:
        d     = self._dashboard
        prefs = load_prefs()
        return {
            "current_mood":      getattr(d, "current_mood", None),
            "current_emotion":   getattr(d, "_last_emotion", None),
            "current_track":     getattr(d, "_last_track_name", None),
            "current_artist":    getattr(d, "_last_track_artist", None),
            "is_playing":        getattr(d, "_is_playing", False),
            "volume":            getattr(d, "_last_volume", 50),
            "spotify_connected": getattr(d, "sp", None) is not None,
            "language":          prefs.get("language", "all"),
            "source":            prefs.get("source", "mix"),
            "confidence":        getattr(d, "_last_confidence", 0.0),
        }

    # ── Welcome ───────────────────────────────────────────────────────────────
    def _show_welcome(self):
        self._add_bubble(
            "Hey! 👋 I'm MoodBot — your emotion-aware music assistant.\n\n"
            "I can control your music, change genres, and react to your mood.\n"
            "Try the quick buttons above or just type naturally!\n"
            "Type 'help' for the full command list.\n\n"
            "🎤 Mic button = voice input (Whisper)  ·  🔇 = toggle voice responses",
            is_user=False,
        )

    # ── Public: proactive messages ────────────────────────────────────────────
    def inject_mood_message(self, mood: str):
        """Called externally when detected mood changes."""
        msg = self._bot.mood_message(mood)
        self._add_bubble(msg, is_user=False)
        if self._tts_enabled:
            self._tts.speak(msg)

    def inject_emotion_message(self, emotion: str, mood: str):
        """Called from window when webcam detects an emotion change (60s cooldown)."""
        msg = self._bot.emotion_message(emotion, mood)
        self._add_bubble(msg, is_user=False)
        if self._tts_enabled:
            self._tts.speak(msg)
