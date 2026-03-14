# ui/pages/register.py
# Register page widget

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QCursor

from core.auth import AuthManager


class RegisterPage(QWidget):
    """Registration form.

    Signals:
        register_success(user_dict)
        go_login()
    """

    register_success = pyqtSignal(dict)
    go_login         = pyqtSignal()

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
        cl.setContentsMargins(40, 36, 40, 36)
        cl.setSpacing(0)

        # Logo + title
        logo = QLabel("◆")
        logo.setObjectName("authLogo")
        logo.setAlignment(Qt.AlignCenter)
        cl.addWidget(logo)
        cl.addSpacing(6)

        title = QLabel("Create account")
        title.setObjectName("authTitle")
        title.setAlignment(Qt.AlignCenter)
        cl.addWidget(title)
        cl.addSpacing(4)

        sub = QLabel("Join MoodRipple — it only takes a moment")
        sub.setObjectName("authSub")
        sub.setAlignment(Qt.AlignCenter)
        cl.addWidget(sub)
        cl.addSpacing(22)

        # Error / success label
        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("authError")
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.setWordWrap(True)
        self.error_lbl.hide()
        cl.addWidget(self.error_lbl)
        cl.addSpacing(4)

        # Username
        self.username_input = self._field(cl, "Username", "e.g. john_doe")
        cl.addSpacing(12)

        # Email
        self.email_input = self._field(cl, "Email", "you@example.com")
        cl.addSpacing(12)

        # Password
        self.password_input = self._field(cl, "Password", "At least 6 characters", password=True)
        cl.addSpacing(12)

        # Confirm password
        self.confirm_input = self._field(cl, "Confirm Password", "Repeat your password", password=True)
        self.confirm_input.returnPressed.connect(self._on_register)
        cl.addSpacing(22)

        # Register button
        self.reg_btn = QPushButton("Create Account")
        self.reg_btn.setObjectName("authPrimaryButton")
        self.reg_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.reg_btn.clicked.connect(self._on_register)
        cl.addWidget(self.reg_btn)
        cl.addSpacing(18)

        # Sign in link
        link_row = QHBoxLayout()
        link_row.setAlignment(Qt.AlignCenter)
        link_row.setSpacing(4)
        have_acc = QLabel("Already have an account?")
        have_acc.setObjectName("authMuted")
        sign_link = QLabel("Sign in")
        sign_link.setObjectName("authLink")
        sign_link.setCursor(QCursor(Qt.PointingHandCursor))
        sign_link.mousePressEvent = lambda _: self.go_login.emit()
        link_row.addWidget(have_acc)
        link_row.addWidget(sign_link)
        cl.addLayout(link_row)

        outer.addWidget(card)

    def _field(self, parent_layout, label: str, placeholder: str, password=False) -> QLineEdit:
        lbl = QLabel(label)
        lbl.setObjectName("authFieldLabel")
        inp = QLineEdit()
        inp.setObjectName("authInput")
        inp.setPlaceholderText(placeholder)
        if password:
            inp.setEchoMode(QLineEdit.Password)
        parent_layout.addWidget(lbl)
        parent_layout.addSpacing(6)
        parent_layout.addWidget(inp)
        return inp

    # ── Slots ─────────────────────────────────────────────────────────────
    def _on_register(self):
        username = self.username_input.text().strip()
        email    = self.email_input.text().strip()
        password = self.password_input.text()
        confirm  = self.confirm_input.text()

        # Client-side pre-check
        if not all([username, email, password, confirm]):
            self._show_error("Please fill in all fields.")
            return
        if password != confirm:
            self._show_error("Passwords do not match.")
            return

        self.reg_btn.setEnabled(False)
        self.reg_btn.setText("Creating account…")
        self._hide_error()

        user, error = self._auth.register(username, email, password)
        if user:
            self.register_success.emit(user)
        else:
            self._show_error(error)

        self.reg_btn.setEnabled(True)
        self.reg_btn.setText("Create Account")

    # ── Helpers ───────────────────────────────────────────────────────────
    def _show_error(self, msg: str):
        self.error_lbl.setText(msg)
        self.error_lbl.setObjectName("authError")
        self.error_lbl.setStyleSheet("color: #ef4444; font-size: 12px; padding: 6px 0;")
        self.error_lbl.show()

    def _hide_error(self):
        self.error_lbl.hide()

    def clear_fields(self):
        for w in (self.username_input, self.email_input,
                  self.password_input, self.confirm_input):
            w.clear()
        self._hide_error()
