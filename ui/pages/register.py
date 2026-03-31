# ui/pages/register.py
# Premium glassmorphism registration form.

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui  import QCursor

from core.auth import AuthManager
from ui.theme  import T, qss_input, qss_button_primary
from ui.components.glass_card import GlassCard
from ui.components.utils      import glow


_FIELD_QSS = qss_input()
_BTN_QSS   = qss_button_primary()

_LINK_QSS = (
    f"QLabel {{ font-size: {T.SIZE_SM}; color: {T.ACCENT}; font-weight: 600;"
    " background: transparent; }"
    "QLabel:hover { color: #FFD426; }"
)
_MUTED_QSS = (
    f"font-size: {T.SIZE_SM}; color: {T.TEXT_3}; background: transparent;"
)
_ERROR_QSS = (
    f"font-size: {T.SIZE_SM}; color: #fca5a5;"
    " background: rgba(239,68,68,0.08);"
    f" border: none; border-radius: {T.R_SM}px;"
    " padding: 10px 14px;"
)
_FIELD_LBL = (
    f"font-size: 10px; font-weight: 600; color: {T.TEXT_2};"
    " letter-spacing: 0.5px; background: transparent;"
)


def _field(parent_layout, caption: str, placeholder: str,
           password: bool = False) -> QLineEdit:
    lbl = QLabel(caption)
    lbl.setStyleSheet(_FIELD_LBL)
    inp = QLineEdit()
    inp.setObjectName("authInput")
    inp.setPlaceholderText(placeholder)
    inp.setMinimumHeight(46)
    if password:
        inp.setEchoMode(QLineEdit.Password)
    parent_layout.addWidget(lbl)
    parent_layout.addSpacing(6)
    parent_layout.addWidget(inp)
    return inp


class RegisterPage(QWidget):
    register_success = pyqtSignal(dict)
    go_login         = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._auth = AuthManager()
        self.setStyleSheet("background: transparent;")
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(T.SP_LG, 0, T.SP_LG, T.SP_SM)
        outer.setAlignment(Qt.AlignCenter)

        # Scroll wrapper so tall form doesn't overflow the auth window
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.viewport().setStyleSheet("background: transparent;")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 0, 0, 0)
        iv.setSpacing(0)
        iv.setAlignment(Qt.AlignCenter)

        # ── Glass panel ───────────────────────────────────────────────────────
        card = GlassCard(radius=22, shadow_blur=60, shadow_opacity=130)
        card.setFixedWidth(420)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(T.SP_XL, T.SP_LG, T.SP_XL, T.SP_LG)
        cl.setSpacing(0)

        # ── Brand orb ─────────────────────────────────────────────────────────
        orb = QLabel("◆")
        orb.setAlignment(Qt.AlignCenter)
        orb.setFixedHeight(40)
        orb.setStyleSheet(
            f"font-size: 20px; color: {T.ACCENT}; background: transparent;")
        glow(orb, color=(245, 197, 24), blur=26, alpha=190)
        cl.addWidget(orb)
        cl.addSpacing(T.SP_XS + 2)

        # ── Title + sub ───────────────────────────────────────────────────────
        title = QLabel("Create account")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 800; color: {T.TEXT_1};"
            " letter-spacing: -0.5px; background: transparent;")
        cl.addWidget(title)
        cl.addSpacing(4)

        sub = QLabel("Join MoodRipple — it only takes a moment")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(_MUTED_QSS)
        cl.addWidget(sub)
        cl.addSpacing(T.SP_MD)

        # ── Error label ───────────────────────────────────────────────────────
        self.error_lbl = QLabel("")
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setStyleSheet(_ERROR_QSS)
        self.error_lbl.hide()
        cl.addWidget(self.error_lbl)
        cl.addSpacing(4)

        # ── Fields ────────────────────────────────────────────────────────────
        self.username_input = _field(cl, "USERNAME", "e.g. john_doe")
        cl.addSpacing(T.SP_MD)

        self.email_input = _field(cl, "EMAIL", "you@example.com")
        cl.addSpacing(T.SP_MD)

        self.password_input = _field(cl, "PASSWORD", "At least 6 characters",
                                     password=True)
        cl.addSpacing(T.SP_MD)

        self.confirm_input = _field(cl, "CONFIRM PASSWORD", "Repeat your password",
                                    password=True)
        self.confirm_input.returnPressed.connect(self._on_register)
        cl.addSpacing(T.SP_LG)

        # ── Create Account button ─────────────────────────────────────────────
        self.reg_btn = QPushButton("Create Account")
        self.reg_btn.setObjectName("authPrimaryButton")
        self.reg_btn.setMinimumHeight(50)
        self.reg_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.reg_btn.clicked.connect(self._on_register)
        cl.addWidget(self.reg_btn)
        cl.addSpacing(T.SP_MD)

        # ── Sign-in link ──────────────────────────────────────────────────────
        link_row = QHBoxLayout()
        link_row.setAlignment(Qt.AlignCenter)
        link_row.setSpacing(5)
        have_acc = QLabel("Already have an account?")
        have_acc.setStyleSheet(_MUTED_QSS)
        sign_link = QLabel("Sign in →")
        sign_link.setObjectName("authLink")
        sign_link.setStyleSheet(_LINK_QSS)
        sign_link.setCursor(QCursor(Qt.PointingHandCursor))
        sign_link.mousePressEvent = lambda _: self.go_login.emit()
        link_row.addWidget(have_acc)
        link_row.addWidget(sign_link)
        cl.addLayout(link_row)

        iv.addWidget(card)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

    # ── Slots ──────────────────────────────────────────────────────────────────
    def _on_register(self):
        username = self.username_input.text().strip()
        email    = self.email_input.text().strip()
        password = self.password_input.text()
        confirm  = self.confirm_input.text()

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

    def _show_error(self, msg: str):
        self.error_lbl.setText(msg)
        self.error_lbl.show()

    def _hide_error(self):
        self.error_lbl.hide()

    def clear_fields(self):
        for w in (self.username_input, self.email_input,
                  self.password_input, self.confirm_input):
            w.clear()
        self._hide_error()
