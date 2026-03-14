# ui/pages/spotify_connect.py
# In-app Spotify OAuth page

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt5.QtCore import pyqtSignal, Qt

from core.spotify_thread import SpotifyAuthThread
from core.constants import SPOTIFY_CACHE_PATH


class SpotifyConnectPage(QWidget):
    """Full-page Spotify OAuth UI.

    Signals:
        connected(sp, display_name, product)
        disconnected()
    """

    connected    = pyqtSignal(object, str, str)
    disconnected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sp    = None
        self._thread = None
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
        icon = QLabel("🎵")
        icon.setStyleSheet("font-size: 36px;")
        page_title = QLabel("Spotify")
        page_title.setObjectName("pageTitle")
        title_row.addWidget(icon)
        title_row.addSpacing(12)
        title_row.addWidget(page_title)
        title_row.addStretch()
        card_layout.addLayout(title_row)

        # Description
        desc = QLabel(
            "Connect your Spotify account so MoodRipple can automatically queue\n"
            "music that matches your detected emotion.\n\n"
            "Playback control requires a Spotify Premium subscription."
        )
        desc.setObjectName("subText")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        card_layout.addSpacing(8)

        # Status area
        self.status_label = QLabel("Not connected")
        self.status_label.setObjectName("statusBad")
        self.status_label.setWordWrap(True)
        card_layout.addWidget(self.status_label)

        # User info (hidden until connected)
        self.user_frame = QFrame()
        self.user_frame.setObjectName("card")
        user_layout = QVBoxLayout(self.user_frame)
        user_layout.setContentsMargins(16, 14, 16, 14)
        user_layout.setSpacing(4)
        self.user_name_label = QLabel("")
        self.user_name_label.setObjectName("trackName")
        self.user_plan_label = QLabel("")
        self.user_plan_label.setObjectName("subText")
        user_layout.addWidget(self.user_name_label)
        user_layout.addWidget(self.user_plan_label)
        self.user_frame.hide()
        card_layout.addWidget(self.user_frame)

        card_layout.addSpacing(8)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

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
        card_layout.addLayout(btn_row)

        # Note
        note = QLabel(
            "A browser window will open for Spotify authorization.\n"
            "After you approve, return here — the page will update automatically."
        )
        note.setObjectName("labelMuted")
        note.setWordWrap(True)
        card_layout.addWidget(note)

        outer.addWidget(card)
        outer.addStretch()

    # ── Reconnect on startup ──────────────────────────────────────────────
    def _try_silent_reconnect(self):
        if os.path.exists(SPOTIFY_CACHE_PATH):
            self._set_status("Reconnecting…", "#9da8b4")
            self.connect_btn.setEnabled(False)
            self._run_auth(interactive=False)

    # ── Slots ─────────────────────────────────────────────────────────────
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

    # ── Thread management ─────────────────────────────────────────────────
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
        self._set_status(f"Connection failed: {error}", "#e05555")
        self.connect_btn.setEnabled(True)

    # ── UI helpers ────────────────────────────────────────────────────────
    def _set_status(self, msg: str, color: str):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(
            f"color: {color}; font-size: 12px; padding: 4px 0;"
        )

    def _show_connected(self, display_name: str, product: str):
        self._set_status("Connected", "#1DB954")
        self.user_name_label.setText(display_name)
        plan_color = "#1DB954" if product.lower() == "premium" else "#e09030"
        self.user_plan_label.setText(product.capitalize())
        self.user_plan_label.setStyleSheet(f"color: {plan_color}; font-size: 12px;")
        self.user_frame.show()
        self.connect_btn.hide()
        self.disconnect_btn.show()

    def _show_disconnected(self):
        self._set_status("Not connected", "#e05555")
        self.user_frame.hide()
        self.connect_btn.show()
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.hide()
