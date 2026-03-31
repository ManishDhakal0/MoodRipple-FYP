# ui/pages/settings.py
# Settings page — tune thresholds, alerts, display preferences, export.

from PyQt5.QtCore    import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QCheckBox, QFrame, QFileDialog, QScrollArea,
    QSpinBox, QDoubleSpinBox, QLineEdit,
)

from core.settings_manager import SettingsManager


def _card(title: str) -> tuple:
    """Returns (outer QFrame, inner QVBoxLayout)."""
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(10)
    if title:
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size:13px; font-weight:600; color:#e0e0e0;")
        layout.addWidget(lbl)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.08);")
        layout.addWidget(sep)
    return frame, layout


def _row_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color:#9da8b4; font-size:12px;")
    lbl.setFixedWidth(200)
    return lbl


def _value_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color:#c0c8d4; font-size:12px; min-width:40px;")
    lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return lbl


class SettingsPage(QWidget):
    settings_changed = pyqtSignal(dict)   # emitted after save

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_values()

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(20, 20, 20, 20)
        vbox.setSpacing(16)

        # Title
        title = QLabel("Settings")
        title.setStyleSheet("font-size:20px; font-weight:700; color:#e0e0e0;")
        vbox.addWidget(title)

        # ── Detection card ────────────────────────────────────────────────────
        card, lay = _card("Detection")
        self._ear_slider, self._ear_val = self._add_slider(
            lay, "EAR Threshold", 10, 45, 100, "0.{:02d}", "ear_threshold")
        self._perclos_w_spin, _ = self._add_spin(
            lay, "PERCLOS Window (frames)", 20, 120, "perclos_window")
        self._perclos_t_slider, self._perclos_t_val = self._add_slider(
            lay, "PERCLOS Threshold", 20, 90, 100, "0.{:02d}", "perclos_threshold")
        self._nod_deg_spin, _ = self._add_spin(
            lay, "Head Nod Threshold (°)", 5, 45, "head_nod_thresh_deg", double=True)
        self._nod_frames_spin, _ = self._add_spin(
            lay, "Head Nod Duration (frames)", 5, 90, "head_nod_frames")
        vbox.addWidget(card)

        # ── Music card ────────────────────────────────────────────────────────
        card2, lay2 = _card("Music & Mood")
        self._cooldown_spin, _ = self._add_spin(
            lay2, "Mood Cooldown (seconds)", 5, 120, "mood_cooldown_secs")

        # Sad/negative emotion music style
        sad_lbl = QLabel("When feeling sad / stressed, play:")
        sad_lbl.setStyleSheet("color:#9da8b4; font-size:12px;")
        lay2.addWidget(sad_lbl)

        sad_row = QHBoxLayout()
        sad_row.setSpacing(8)
        self._sad_comfort_btn = QPushButton("🌊  Comforting & calm")
        self._sad_comfort_btn.setCheckable(True)
        self._sad_comfort_btn.setChecked(True)
        self._sad_comfort_btn.setObjectName("prefPill")
        self._sad_comfort_btn.clicked.connect(lambda: self._set_sad_mode("comfort"))

        self._sad_uplift_btn = QPushButton("⚡  Uplifting & energetic")
        self._sad_uplift_btn.setCheckable(True)
        self._sad_uplift_btn.setChecked(False)
        self._sad_uplift_btn.setObjectName("prefPill")
        self._sad_uplift_btn.clicked.connect(lambda: self._set_sad_mode("uplift"))

        for btn in (self._sad_comfort_btn, self._sad_uplift_btn):
            btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.05); color: #9da8b4;"
                " border: 1px solid rgba(255,255,255,0.10); border-radius: 100px;"
                " padding: 6px 16px; font-size: 12px; }"
                "QPushButton:checked { background: rgba(139,92,246,0.20);"
                " color: #c4b5fd; border-color: rgba(139,92,246,0.50); }"
                "QPushButton:hover { border-color: rgba(255,255,255,0.22); color: #e0e0e0; }"
            )
        sad_row.addWidget(self._sad_comfort_btn)
        sad_row.addWidget(self._sad_uplift_btn)
        sad_row.addStretch()
        lay2.addLayout(sad_row)

        sad_hint = QLabel(
            "Comforting: matches your mood with soft music.  "
            "Uplifting: plays energetic music to cheer you up.")
        sad_hint.setStyleSheet("color: rgba(157,168,180,0.50); font-size: 10px;")
        sad_hint.setWordWrap(True)
        lay2.addWidget(sad_hint)

        vbox.addWidget(card2)

        # ── Alerts card ───────────────────────────────────────────────────────
        card3, lay3 = _card("Alerts & Calendar")
        self._alert_min_spin, _ = self._add_spin(
            lay3, "Meeting Alert (minutes before)", 1, 30, "alert_minutes")
        vbox.addWidget(card3)

        # ── Display card ──────────────────────────────────────────────────────
        card4, lay4 = _card("Display")
        self._auto_start_cb = self._add_checkbox(
            lay4, "Auto-start detection on launch", "auto_start_detection")
        self._mood_widget_cb = self._add_checkbox(
            lay4, "Show 'Now Mood' floating widget", "show_mood_widget")
        vbox.addWidget(card4)

        # ── Export card ───────────────────────────────────────────────────────
        card5, lay5 = _card("Export")
        self._auto_export_cb = self._add_checkbox(
            lay5, "Auto-export CSV at end of session", "auto_export_session")

        # Folder picker
        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        folder_row.addWidget(_row_label("Export Folder"))
        self._folder_lbl = QLabel("(app directory)")
        self._folder_lbl.setStyleSheet("color:#9da8b4; font-size:11px;")
        self._folder_lbl.setWordWrap(False)
        folder_row.addWidget(self._folder_lbl, 1)
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(80)
        browse_btn.setObjectName("secondaryBtn")
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse_btn)
        lay5.addLayout(folder_row)
        vbox.addWidget(card5)

        # ── API Keys card ─────────────────────────────────────────────────────
        card6, lay6 = _card("API Keys")

        key_row = QHBoxLayout()
        key_row.setSpacing(8)
        key_row.addWidget(_row_label("OpenAI API Key"))
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setPlaceholderText("sk-…  (required for Whisper voice input in Chat)")
        self._api_key_edit.setEchoMode(QLineEdit.Password)
        self._api_key_edit.setStyleSheet(
            "QLineEdit { background: #1e2433; color: #e0e0e0;"
            " border: 1px solid rgba(255,255,255,0.12); border-radius: 6px;"
            " padding: 5px 10px; font-size: 12px; }"
            "QLineEdit:focus { border-color: rgba(245,197,24,0.50); }"
        )
        key_row.addWidget(self._api_key_edit, 1)
        lay6.addLayout(key_row)

        hint = QLabel("Key is stored locally in moodripple_settings.json and never sent anywhere except OpenAI.")
        hint.setStyleSheet("color: rgba(157,168,180,0.55); font-size: 10px;")
        hint.setWordWrap(True)
        lay6.addWidget(hint)
        vbox.addWidget(card6)

        vbox.addStretch()

        scroll.setWidget(content)

        # ── Save / Reset — pinned OUTSIDE scroll, always visible ──────────────
        bottom_bar = QFrame()
        bottom_bar.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.03); border: none; "
            "border-top: 1px solid rgba(255,255,255,0.05); }")
        bottom_bar.setFixedHeight(62)
        bl = QHBoxLayout(bottom_bar)
        bl.setContentsMargins(20, 0, 20, 0)
        bl.setSpacing(10)
        bl.addStretch()
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setObjectName("secondaryBtn")
        reset_btn.clicked.connect(self._reset_defaults)
        save_btn = QPushButton("  Save Settings  ")
        save_btn.setObjectName("primaryBtn")
        save_btn.setMinimumHeight(38)
        save_btn.clicked.connect(self._save)
        bl.addWidget(reset_btn)
        bl.addWidget(save_btn)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(scroll, 1)
        outer.addWidget(bottom_bar)

    # ── Widget helpers ────────────────────────────────────────────────────────
    def _add_slider(self, layout, label: str, lo: int, hi: int,
                    divisor: int, fmt: str, key: str):
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(_row_label(label))
        slider = QSlider(Qt.Horizontal)
        slider.setRange(lo, hi)
        slider.setObjectName("settingsSlider")
        val_lbl = _value_label(fmt.format(lo))

        def _on_change(v):
            val_lbl.setText(f"{v / divisor:.2f}")

        slider.valueChanged.connect(_on_change)
        row.addWidget(slider, 1)
        row.addWidget(val_lbl)
        layout.addLayout(row)
        return slider, val_lbl

    def _add_spin(self, layout, label: str, lo, hi, key: str, double=False):
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(_row_label(label))
        if double:
            spin = QDoubleSpinBox()
            spin.setRange(float(lo), float(hi))
            spin.setSingleStep(0.5)
            spin.setDecimals(1)
        else:
            spin = QSpinBox()
            spin.setRange(int(lo), int(hi))
        spin.setFixedWidth(80)
        spin.setStyleSheet(
            "QSpinBox, QDoubleSpinBox {"
            " background:#1e2433; color:#e0e0e0;"
            " border:1px solid rgba(255,255,255,0.12); border-radius:6px;"
            " padding:3px 6px; font-size:12px; }"
        )
        row.addWidget(spin)
        row.addStretch()
        layout.addLayout(row)
        return spin, None

    def _add_checkbox(self, layout, label: str, key: str) -> QCheckBox:
        cb = QCheckBox(label)
        cb.setStyleSheet(
            "QCheckBox { color:#9da8b4; font-size:12px; spacing:8px; }"
            "QCheckBox::indicator { width:16px; height:16px; border-radius:3px;"
            " border:1px solid rgba(255,255,255,0.25); background:#1e2433; }"
            "QCheckBox::indicator:checked { background:#1DB954;"
            " border-color:#1DB954; }"
        )
        layout.addWidget(cb)
        return cb

    def _set_sad_mode(self, mode: str):
        self._sad_comfort_btn.setChecked(mode == "comfort")
        self._sad_uplift_btn.setChecked(mode == "uplift")

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if folder:
            self._export_folder = folder
            self._folder_lbl.setText(folder)

    # ── Load / Save ───────────────────────────────────────────────────────────
    def _load_values(self):
        s = SettingsManager.all()
        self._export_folder = s.get("export_folder", "")

        self._ear_slider.setValue(int(s.get("ear_threshold", 0.25) * 100))
        self._perclos_w_spin.setValue(int(s.get("perclos_window", 60)))
        self._perclos_t_slider.setValue(int(s.get("perclos_threshold", 0.65) * 100))
        self._nod_deg_spin.setValue(float(s.get("head_nod_thresh_deg", 20.0)))
        self._nod_frames_spin.setValue(int(s.get("head_nod_frames", 30)))
        self._cooldown_spin.setValue(int(s.get("mood_cooldown_secs", 30)))
        self._alert_min_spin.setValue(int(s.get("alert_minutes", 5)))
        self._auto_start_cb.setChecked(bool(s.get("auto_start_detection", False)))
        self._mood_widget_cb.setChecked(bool(s.get("show_mood_widget", False)))
        self._auto_export_cb.setChecked(bool(s.get("auto_export_session", True)))

        folder = s.get("export_folder", "")
        if folder:
            self._folder_lbl.setText(folder)

        self._api_key_edit.setText(s.get("openai_api_key", ""))

        sad_mode = s.get("sad_music_response", "comfort")
        self._sad_comfort_btn.setChecked(sad_mode == "comfort")
        self._sad_uplift_btn.setChecked(sad_mode == "uplift")

    def _save(self):
        updates = {
            "ear_threshold":        self._ear_slider.value() / 100.0,
            "perclos_window":       self._perclos_w_spin.value(),
            "perclos_threshold":    self._perclos_t_slider.value() / 100.0,
            "head_nod_thresh_deg":  self._nod_deg_spin.value(),
            "head_nod_frames":      self._nod_frames_spin.value(),
            "mood_cooldown_secs":   self._cooldown_spin.value(),
            "alert_minutes":        self._alert_min_spin.value(),
            "auto_start_detection": self._auto_start_cb.isChecked(),
            "show_mood_widget":     self._mood_widget_cb.isChecked(),
            "auto_export_session":  self._auto_export_cb.isChecked(),
            "export_folder":        getattr(self, "_export_folder", ""),
            "openai_api_key":       self._api_key_edit.text().strip(),
            "sad_music_response":   "comfort" if self._sad_comfort_btn.isChecked() else "uplift",
        }
        SettingsManager.update(updates)
        self.settings_changed.emit(updates)

    def _reset_defaults(self):
        from core.settings_manager import DEFAULTS
        SettingsManager.update(dict(DEFAULTS))
        self._load_values()
        self.settings_changed.emit(SettingsManager.all())
