# ui/auth_window.py
# AuthWindow: standalone login/register gate shown before the main app

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget, QVBoxLayout,
)
from PyQt5.QtCore import pyqtSignal, Qt

from ui.theme import apply_theme
from ui.pages.login import LoginPage
from ui.pages.register import RegisterPage
from core.auth import AuthManager


class AuthWindow(QMainWindow):
    """
    Shown instead of MainWindow until the user logs in.

    Signal:
        logged_in(user_dict, remember_me)
    """

    logged_in = pyqtSignal(dict, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MoodRipple — Sign In")
        self.setFixedSize(520, 620)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        apply_theme(self)

        self._auth = AuthManager()
        self._auth.init_db()

        self._build_ui()
        self._try_silent_restore()

    # ── Build UI ─────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        rl = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()

        self.login_page = LoginPage()
        self.login_page.login_success.connect(self._on_login_success)
        self.login_page.go_register.connect(self._show_register)

        self.register_page = RegisterPage()
        self.register_page.register_success.connect(self._on_register_success)
        self.register_page.go_login.connect(self._show_login)

        self.stack.addWidget(self.login_page)    # index 0
        self.stack.addWidget(self.register_page) # index 1

        rl.addWidget(self.stack)

    # ── Silent session restore ────────────────────────────────────────────
    def _try_silent_restore(self):
        user = self._auth.load_session()
        if user:
            self.logged_in.emit(user, True)

    # ── Slots ─────────────────────────────────────────────────────────────
    def _on_login_success(self, user: dict, remember: bool):
        if remember:
            self._auth.save_session(user)
        self.logged_in.emit(user, remember)

    def _on_register_success(self, user: dict):
        # Auto-login after registration (no remember-me by default)
        self.logged_in.emit(user, False)

    def _show_register(self):
        self.register_page.clear_fields()
        self.stack.setCurrentIndex(1)

    def _show_login(self):
        self.login_page.clear_fields()
        self.stack.setCurrentIndex(0)
