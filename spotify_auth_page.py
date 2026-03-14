# spotify_auth_page.py
# In-app Spotify OAuth widget — shown as a page in the left-side menu

import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt

SPOTIFY_CLIENT_ID = "ec7d75c8cbe549b48ccb8898a51d7c72"
SPOTIFY_CLIENT_SECRET = "dd2cae1ec9ba42afa8eccb6f9d335e98"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_SCOPE = (
    "user-read-recently-played "
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing "
    "user-top-read "
    "user-read-private "
    "user-read-email"
)
CACHE_PATH = "spotify_mood.cache"


# ─────────────────────────────────────────────
# Background thread: runs Spotify OAuth
# ─────────────────────────────────────────────
class SpotifyAuthThread(QThread):
    auth_success = pyqtSignal(object, str, str)   # sp client, display_name, product
    auth_failed  = pyqtSignal(str)

    def __init__(self, interactive: bool = False):
        super().__init__()
        self.interactive = interactive

    def run(self):
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth

            sp = spotipy.Spotify(
                auth_manager=SpotifyOAuth(
                    client_id=SPOTIFY_CLIENT_ID,
                    client_secret=SPOTIFY_CLIENT_SECRET,
                    redirect_uri=SPOTIFY_REDIRECT_URI,
                    scope=SPOTIFY_SCOPE,
                    cache_path=CACHE_PATH,
                    open_browser=self.interactive,
                    show_dialog=self.interactive,
                )
            )
            user = sp.current_user()
            display_name = user.get("display_name") or user.get("id", "unknown")
            product = user.get("product", "unknown")
            self.auth_success.emit(sp, display_name, product)

        except Exception as e:
            self.auth_failed.emit(str(e))


# ─────────────────────────────────────────────
# Spotify Auth Page widget
# ─────────────────────────────────────────────
class SpotifyAuthPage(QWidget):
    # Emitted when connection state changes
    connected    = pyqtSignal(object, str, str)   # sp, display_name, product
    disconnected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.auth_thread = None
        self._setup_ui()
        # Try silent connect if a cached token already exists
        if os.path.exists(CACHE_PATH):
            self._run_auth(interactive=False)

    # ── UI ──────────────────────────────────
    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.setSpacing(24)

        title = QLabel("🎵 Spotify Connection")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        # Status card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(10)

        self.status_label = QLabel("● Not Connected")
        self.status_label.setStyleSheet("color: #ff6b6b; font-size: 14px; font-weight: bold;")

        self.user_label = QLabel("")
        self.user_label.setObjectName("subText")
        self.user_label.hide()

        self.product_label = QLabel("")
        self.product_label.setObjectName("subText")
        self.product_label.hide()

        self.note_label = QLabel(
            "⚠ Spotify Premium is required for automatic playback control.\n"
            "Free accounts can still open tracks in the browser."
        )
        self.note_label.setObjectName("subText")
        self.note_label.setWordWrap(True)
        self.note_label.hide()

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

        card_layout.addWidget(self.status_label)
        card_layout.addWidget(self.user_label)
        card_layout.addWidget(self.product_label)
        card_layout.addWidget(self.note_label)
        card_layout.addSpacing(8)
        card_layout.addLayout(btn_row)
        outer.addWidget(card)

        # Instructions card
        info = QFrame()
        info.setObjectName("card")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(24, 16, 24, 16)
        info_layout.setSpacing(6)

        info_title = QLabel("How to connect")
        info_title.setObjectName("panelTitle")
        info_layout.addWidget(info_title)

        steps = [
            "1. Click Connect Spotify above.",
            "2. A browser window will open with the Spotify login page.",
            "3. Log in and click Authorize.",
            "4. The app will detect the login automatically — no copy-paste needed.",
            "5. Once connected, go back to Dashboard and use Auto-Play.",
        ]
        for step in steps:
            lbl = QLabel(step)
            lbl.setObjectName("subText")
            lbl.setWordWrap(True)
            info_layout.addWidget(lbl)

        outer.addWidget(info)
        outer.addStretch()

    # ── Auth flow ────────────────────────────
    def _on_connect_clicked(self):
        self.connect_btn.setEnabled(False)
        self.status_label.setText("⏳ Connecting… check your browser")
        self.status_label.setStyleSheet("color: #f39c12; font-size: 14px; font-weight: bold;")
        self._run_auth(interactive=True)

    def _run_auth(self, interactive: bool):
        if self.auth_thread is not None and self.auth_thread.isRunning():
            return
        self.auth_thread = SpotifyAuthThread(interactive=interactive)
        self.auth_thread.auth_success.connect(self._on_success)
        self.auth_thread.auth_failed.connect(self._on_failed)
        self.auth_thread.start()

    def _on_success(self, sp, display_name, product):
        self.status_label.setText("● Connected")
        self.status_label.setStyleSheet("color: #1DB954; font-size: 14px; font-weight: bold;")
        self.user_label.setText(f"Account: {display_name}")
        self.user_label.show()
        self.product_label.setText(f"Type: {product.capitalize()}")
        self.product_label.show()
        self.note_label.show()
        self.connect_btn.hide()
        self.disconnect_btn.show()
        self.connected.emit(sp, display_name, product)

    def _on_failed(self, error: str):
        # Silent connect failure is normal if no cache — don't alarm the user
        self.status_label.setText("● Not Connected")
        self.status_label.setStyleSheet("color: #ff6b6b; font-size: 14px; font-weight: bold;")
        self.user_label.hide()
        self.product_label.hide()
        self.note_label.hide()
        self.connect_btn.setEnabled(True)
        self.connect_btn.show()
        self.disconnect_btn.hide()

    def _on_disconnect_clicked(self):
        if os.path.exists(CACHE_PATH):
            os.remove(CACHE_PATH)
        self.status_label.setText("● Not Connected")
        self.status_label.setStyleSheet("color: #ff6b6b; font-size: 14px; font-weight: bold;")
        self.user_label.hide()
        self.product_label.hide()
        self.note_label.hide()
        self.connect_btn.setEnabled(True)
        self.connect_btn.show()
        self.disconnect_btn.hide()
        self.disconnected.emit()

    # ── Public helper ────────────────────────
    def is_connected(self) -> bool:
        return "Connected" in self.status_label.text() and "Not" not in self.status_label.text()
