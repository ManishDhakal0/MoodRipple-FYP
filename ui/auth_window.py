# ui/auth_window.py
# AuthWindow — frameless QWebEngineView shell showing web/login.html.
# All login/register logic stays in Python (AuthManager).
# Bridge relays JS calls → AuthManager, result → JS via auth_result signal.

import json
import os

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtCore    import pyqtSignal, Qt, QPoint, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtWebChannel       import QWebChannel

from core.auth  import AuthManager
from ui.bridge  import AppBridge


class AuthWindow(QMainWindow):
    """Shown instead of MainWindow until the user logs in."""
    logged_in = pyqtSignal(dict, bool)   # user_dict, remember_me

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setWindowTitle("MoodRipple — Sign In")
        self.setFixedSize(520, 620)

        self._auth     = AuthManager()
        self._auth.init_db()
        self._drag_pos: QPoint = None

        # Bridge
        self._bridge  = AppBridge(self)
        self._channel = QWebChannel(self)
        self._channel.registerObject("bridge", self._bridge)

        # Register JS→Python handlers
        self._bridge.bind("login",       self._on_login)
        self._bridge.bind("register",    self._on_register)
        self._bridge.bind("minimize_win", lambda: self.showMinimized())
        self._bridge.bind("close_win",   lambda: self.close())
        self._bridge.bind("drag_move",   self._drag_move)

        # Web view
        self._view = QWebEngineView()
        self._view.page().setWebChannel(self._channel)
        self._view.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self._view.setContextMenuPolicy(Qt.NoContextMenu)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)
        self.setCentralWidget(container)

        html_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "web", "login.html")
        self._view.load(QUrl.fromLocalFile(html_path))

        self._try_silent_restore()

    # ── Drag ──────────────────────────────────────────────────────────────────
    def _drag_move(self, dx: int, dy: int):
        self.move(self.pos() + QPoint(dx, dy))

    # ── Silent session restore ────────────────────────────────────────────────
    def _try_silent_restore(self):
        user = self._auth.load_session()
        if user:
            self.logged_in.emit(user, True)

    # ── Auth handlers ─────────────────────────────────────────────────────────
    def _on_login(self, username: str, password: str):
        user, error = self._auth.login(username, password)
        if user:
            remember = True   # honour "keep me signed in" from page default
            self._auth.save_session(user)
            self.logged_in.emit(user, remember)
        else:
            self._bridge.auth_result.emit(json.dumps({
                "ok": False, "error": error, "page": "login"
            }))

    def _on_register(self, username: str, email: str, password: str):
        user, error = self._auth.register(username, email, password)
        if user:
            self.logged_in.emit(user, False)
        else:
            self._bridge.auth_result.emit(json.dumps({
                "ok": False, "error": error, "page": "register"
            }))
