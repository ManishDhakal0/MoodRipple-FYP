# ui/pages/spotify_connect.py
# Spotify OAuth connect page + Music Preferences

import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QButtonGroup,
)
from PyQt5.QtCore import pyqtSignal, Qt

from core.spotify_thread import SpotifyAuthThread
from core.constants import SPOTIFY_CACHE_PATH

_PREFS_FILE = "music_prefs.json"

_SOURCE_OPTIONS = [
    ("favourites", "⭐  My Favourites",  "Tracks from your recent plays & top songs"),
    ("discover",   "🔀  Surprise Me",    "Fresh recommendations based on your taste"),
    ("mix",        "🎯  Smart Mix",      "Blend of your favourites + new discoveries"),
]

_LANG_OPTIONS = [
    ("all",       "🌍  All"),
    ("english",   "English"),
    ("nepali",    "Nepali"),
    ("hindi",     "Hindi"),
    ("bollywood", "Bollywood"),
    ("kpop",      "K-Pop"),
    ("lofi",      "Lo-fi"),
    ("party",     "Party"),
    ("classical", "Classical"),
]


def _load_prefs() -> dict:
    try:
        with open(_PREFS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"source": "favourites", "language": "all"}


def _save_prefs(prefs: dict):
    try:
        with open(_PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
    except Exception:
        pass


class SpotifyConnectPage(QWidget):
    connected           = pyqtSignal(object, str, str)
    disconnected        = pyqtSignal()
    preferences_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sp     = None
        self._thread = None
        self._prefs  = _load_prefs()

        self._source_group = QButtonGroup(self)
        self._source_group.setExclusive(True)
        self._lang_group   = QButtonGroup(self)
        self._lang_group.setExclusive(True)

        self._build_ui()
        self._try_silent_reconnect()

    # ── UI ────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("panelScroll")

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(16)

        cl.addWidget(self._build_auth_card())
        self._prefs_card = self._build_prefs_card()
        cl.addWidget(self._prefs_card)
        cl.addWidget(self._build_info_card())
        cl.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

        # Prefs card only visible when connected
        self._prefs_card.setVisible(False)

    # ── Auth card ─────────────────────────────────────────────────────
    def _build_auth_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("authCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(0)

        # Header row
        hdr = QHBoxLayout()
        hdr.setSpacing(14)

        icon_bg = QFrame()
        icon_bg.setFixedSize(48, 48)
        icon_bg.setStyleSheet(
            "background: rgba(124,58,237,0.12); border-radius: 12px; border: none;"
        )
        icon_inner = QVBoxLayout(icon_bg)
        icon_inner.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("🎵")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 22px; background: transparent;")
        icon_inner.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        page_title = QLabel("Spotify")
        page_title.setObjectName("pageTitle")
        subtitle = QLabel("Emotion-aware music playback")
        subtitle.setStyleSheet("font-size: 12px; color: #475569;")
        title_col.addWidget(page_title)
        title_col.addWidget(subtitle)

        hdr.addWidget(icon_bg)
        hdr.addLayout(title_col)
        hdr.addStretch()
        layout.addLayout(hdr)
        layout.addSpacing(24)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)
        layout.addSpacing(20)

        # Status
        self.status_label = QLabel("Not connected")
        self.status_label.setObjectName("statusBad")
        layout.addWidget(self.status_label)
        layout.addSpacing(12)

        # Connected user card
        self.user_frame = QFrame()
        self.user_frame.setStyleSheet(
            "QFrame { background: rgba(16,185,129,0.06); border: 1px solid rgba(16,185,129,0.15);"
            " border-radius: 10px; }"
        )
        user_layout = QHBoxLayout(self.user_frame)
        user_layout.setContentsMargins(14, 12, 14, 12)
        user_layout.setSpacing(10)

        av_lbl = QLabel("♪")
        av_lbl.setFixedSize(36, 36)
        av_lbl.setAlignment(Qt.AlignCenter)
        av_lbl.setStyleSheet(
            "font-size: 16px; background: rgba(16,185,129,0.15); border-radius: 8px;"
        )
        user_layout.addWidget(av_lbl)

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        self.user_name_label = QLabel("")
        self.user_name_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #f1f5f9;")
        self.user_plan_label = QLabel("")
        self.user_plan_label.setStyleSheet("font-size: 11px; color: #475569;")
        name_col.addWidget(self.user_name_label)
        name_col.addWidget(self.user_plan_label)
        user_layout.addLayout(name_col)
        user_layout.addStretch()
        self.user_frame.hide()
        layout.addWidget(self.user_frame)
        layout.addSpacing(20)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.connect_btn = QPushButton("Connect Spotify")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.clicked.connect(self._on_connect_clicked)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setObjectName("secondaryButton")
        self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self.disconnect_btn.hide()

        btn_row.addWidget(self.connect_btn)
        btn_row.addWidget(self.disconnect_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return card

    # ── Preferences card ──────────────────────────────────────────────
    def _build_prefs_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("authCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(16)

        hdr = QLabel("MUSIC PREFERENCES")
        hdr.setObjectName("cardTitle")
        layout.addWidget(hdr)

        # ── Source section ────────────────────────────────────────────
        src_lbl = QLabel("Music Source")
        src_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        layout.addWidget(src_lbl)

        src_row = QHBoxLayout()
        src_row.setSpacing(8)
        src_row.setAlignment(Qt.AlignLeft)
        self._src_btns: dict[str, QPushButton] = {}
        for key, label, _ in _SOURCE_OPTIONS:
            btn = QPushButton(label)
            btn.setObjectName("prefPill")
            btn.setCheckable(True)
            btn.setChecked(key == self._prefs.get("source", "favourites"))
            self._source_group.addButton(btn)
            btn.clicked.connect(lambda _, k=key: self._on_source_changed(k))
            src_row.addWidget(btn)
            self._src_btns[key] = btn
        src_row.addStretch()
        layout.addLayout(src_row)

        # Source description label
        self._src_desc = QLabel(self._source_desc(self._prefs.get("source", "favourites")))
        self._src_desc.setObjectName("subText")
        self._src_desc.setStyleSheet("font-size: 11px; color: #334155;")
        layout.addWidget(self._src_desc)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        # ── Language / genre section ──────────────────────────────────
        lang_lbl = QLabel("Language / Genre Filter")
        lang_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        layout.addWidget(lang_lbl)

        # Two rows of pills
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.setAlignment(Qt.AlignLeft)
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.setAlignment(Qt.AlignLeft)

        self._lang_btns: dict[str, QPushButton] = {}
        for i, (key, label) in enumerate(_LANG_OPTIONS):
            btn = QPushButton(label)
            btn.setObjectName("langPill")
            btn.setCheckable(True)
            btn.setChecked(key == self._prefs.get("language", "all"))
            self._lang_group.addButton(btn)
            btn.clicked.connect(lambda _, k=key: self._on_lang_changed(k))
            self._lang_btns[key] = btn
            if i < 5:
                row1.addWidget(btn)
            else:
                row2.addWidget(btn)
        row1.addStretch()
        row2.addStretch()
        layout.addLayout(row1)
        layout.addLayout(row2)

        note = QLabel("Preferences are saved and applied to all auto-play sessions.")
        note.setObjectName("subText")
        note.setStyleSheet("font-size: 11px; color: rgba(71,85,105,0.55); margin-top: 2px;")
        layout.addWidget(note)

        return card

    def _source_desc(self, source: str) -> str:
        for key, _, desc in _SOURCE_OPTIONS:
            if key == source:
                return desc
        return ""

    # ── Info card ─────────────────────────────────────────────────────
    def _build_info_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("authCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(12)

        title = QLabel("HOW IT WORKS")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        for icon, text in [
            ("🌐", "A browser window opens for Spotify OAuth authorization."),
            ("🔐", "After you approve, your session is saved locally."),
            ("🎯", "Playback control requires Spotify Premium."),
            ("⭐", "'My Favourites' queues from your recent & top tracks."),
            ("🔀", "'Surprise Me' uses Spotify's recommendation engine with mood-matched audio features."),
            ("🌍", "Language filters search Spotify for tracks matching your chosen language or genre."),
        ]:
            row = QHBoxLayout()
            row.setSpacing(10)
            i_lbl = QLabel(icon)
            i_lbl.setFixedWidth(20)
            i_lbl.setStyleSheet("font-size: 13px;")
            t_lbl = QLabel(text)
            t_lbl.setObjectName("subText")
            t_lbl.setWordWrap(True)
            row.addWidget(i_lbl)
            row.addWidget(t_lbl, 1)
            layout.addLayout(row)

        return card

    # ── Logic ─────────────────────────────────────────────────────────
    def _on_source_changed(self, key: str):
        self._prefs["source"] = key
        self._src_desc.setText(self._source_desc(key))
        _save_prefs(self._prefs)
        self.preferences_changed.emit(dict(self._prefs))

    def _on_lang_changed(self, key: str):
        self._prefs["language"] = key
        _save_prefs(self._prefs)
        self.preferences_changed.emit(dict(self._prefs))

    def get_prefs(self) -> dict:
        return dict(self._prefs)

    def _try_silent_reconnect(self):
        if os.path.exists(SPOTIFY_CACHE_PATH):
            self._set_status("Reconnecting…", "#9da8b4")
            self.connect_btn.setEnabled(False)
            self._run_auth(interactive=False)

    def _on_connect_clicked(self):
        self._set_status("Opening Spotify in browser…", "#9da8b4")
        self.connect_btn.setEnabled(False)
        self._run_auth(interactive=True)

    def _on_disconnect_clicked(self):
        self._sp = None
        if os.path.exists(SPOTIFY_CACHE_PATH):
            try:
                os.remove(SPOTIFY_CACHE_PATH)
            except OSError:
                pass
        self._show_disconnected()
        self.disconnected.emit()

    def _run_auth(self, interactive: bool):
        self._thread = SpotifyAuthThread(interactive=interactive)
        self._thread.success.connect(self._on_auth_success)
        self._thread.failed.connect(self._on_auth_failed)
        self._thread.start()

    def _on_auth_success(self, sp, display_name: str, product: str):
        self._sp = sp
        self._show_connected(display_name, product)
        self.connected.emit(sp, display_name, product)

    def _on_auth_failed(self, error: str):
        self._set_status(f"Connection failed: {error}", "#f87171")
        self.connect_btn.setEnabled(True)

    # ── UI helpers ────────────────────────────────────────────────────
    def _set_status(self, msg: str, color: str):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px; padding: 4px 0;")

    def _show_connected(self, display_name: str, product: str):
        self._set_status("● Connected", "#34d399")
        self.user_name_label.setText(display_name)
        is_premium = product.lower() == "premium"
        plan_color = "#34d399" if is_premium else "#fbbf24"
        plan_text  = f"{'✦  ' if is_premium else ''}  {product.capitalize()}"
        self.user_plan_label.setText(plan_text)
        self.user_plan_label.setStyleSheet(f"font-size: 11px; color: {plan_color};")
        self.user_frame.show()
        self.connect_btn.hide()
        self.disconnect_btn.show()
        self._prefs_card.setVisible(True)

    def _show_disconnected(self):
        self._set_status("Not connected", "#f87171")
        self.user_frame.hide()
        self.connect_btn.show()
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.hide()
        self._prefs_card.setVisible(False)
