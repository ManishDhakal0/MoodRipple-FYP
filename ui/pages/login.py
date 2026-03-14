# ui/pages/login.py
# Login page widget

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox, QFrame,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QCursor

from core.auth import AuthManager


class LoginPage(QWidget):
    """Login form.

    Signals:
        login_success(user_dict)
        go_register()
    """

    login_success = pyqtSignal(dict, bool)   # user, remember_me
    go_register   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._auth = AuthManager()
        self._build_ui()

    # ── Build UI ─────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("authWindowCard")
        card.setFixedWidth(400)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(40, 40, 40, 40)
        cl.setSpacing(0)

        # Logo + title
        logo = QLabel("◆")
        logo.setObjectName("authLogo")
        logo.setAlignment(Qt.AlignCenter)
        cl.addWidget(logo)
        cl.addSpacing(6)

        title = QLabel("Welcome back")
        title.setObjectName("authTitle")
        title.setAlignment(Qt.AlignCenter)
        cl.addWidget(title)
        cl.addSpacing(4)

        sub = QLabel("Sign in to your MoodRipple account")
        sub.setObjectName("authSub")
        sub.setAlignment(Qt.AlignCenter)
        cl.addWidget(sub)
        cl.addSpacing(28)

        # Error label (hidden until needed)
        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("authError")
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.setWordWrap(True)
        self.error_lbl.hide()
        cl.addWidget(self.error_lbl)
        cl.addSpacing(4)

        # Username
        user_lbl = QLabel("Username")
        user_lbl.setObjectName("authFieldLabel")
        self.username_input = QLineEdit()
        self.username_input.setObjectName("authInput")
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.returnPressed.connect(self._on_login)
        cl.addWidget(user_lbl)
        cl.addSpacing(6)
        cl.addWidget(self.username_input)
        cl.addSpacing(14)

        # Password
        pass_lbl = QLabel("Password")
        pass_lbl.setObjectName("authFieldLabel")
        self.password_input = QLineEdit()
        self.password_input.setObjectName("authInput")
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self._on_login)
        cl.addWidget(pass_lbl)
        cl.addSpacing(6)
        cl.addWidget(self.password_input)
        cl.addSpacing(14)

        # Remember me
        self.remember_cb = QCheckBox("Remember me")
        self.remember_cb.setObjectName("authCheck")
        cl.addWidget(self.remember_cb)
        cl.addSpacing(20)

        # Login button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setObjectName("authPrimaryButton")
        self.login_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.login_btn.clicked.connect(self._on_login)
        cl.addWidget(self.login_btn)
        cl.addSpacing(20)

        # Register link
        link_row = QHBoxLayout()
        link_row.setAlignment(Qt.AlignCenter)
        link_row.setSpacing(4)
        no_acc = QLabel("Don't have an account?")
        no_acc.setObjectName("authMuted")
        reg_link = QLabel("Create one")
        reg_link.setObjectName("authLink")
        reg_link.setCursor(QCursor(Qt.PointingHandCursor))
        reg_link.mousePressEvent = lambda _: self.go_register.emit()
        link_row.addWidget(no_acc)
        link_row.addWidget(reg_link)
        cl.addLayout(link_row)

        outer.addWidget(card)

    # ── Slots ─────────────────────────────────────────────────────────────
    def _on_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in…")
        self._hide_error()

        user, error = self._auth.login(username, password)
        if user:
            self.login_success.emit(user, self.remember_cb.isChecked())
        else:
            self._show_error(error)

        self.login_btn.setEnabled(True)
        self.login_btn.setText("Sign In")

    # ── Helpers ───────────────────────────────────────────────────────────
    def _show_error(self, msg: str):
        self.error_lbl.setText(msg)
        self.error_lbl.show()

    def _hide_error(self):
        self.error_lbl.hide()

    def clear_fields(self):
        self.username_input.clear()
        self.password_input.clear()
        self.remember_cb.setChecked(False)
        self._hide_error()
