# ui/pages/login.py
# Premium glassmorphism login form.
# Uses GlassCard panel + design-system tokens.

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui  import QCursor

from core.auth import AuthManager
from ui.theme  import T, qss_input, qss_button_primary
from ui.components.glass_card import GlassCard
from ui.components.utils      import glow, shadow, label, heading, subheading


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
    " padding: 10px 14px; line-height: 1.5;"
)
_CB_QSS = (
    f"QCheckBox {{ font-size: {T.SIZE_SM}; color: {T.TEXT_2}; spacing: 8px; }}"
    " QCheckBox::indicator { width: 17px; height: 17px;"
    f" border: 1px solid rgba(255,255,255,0.15); border-radius: 5px;"
    f" background: {T.BG_INPUT}; }}"
    f" QCheckBox::indicator:hover {{ border-color: {T.ACCENT_RING}; }}"
    f" QCheckBox::indicator:checked {{ background: {T.ACCENT}; border-color: {T.ACCENT}; }}"
)
_FIELD_LBL = (
    f"font-size: 10px; font-weight: 600; color: {T.TEXT_2};"
    " letter-spacing: 0.5px; background: transparent;"
)


class LoginPage(QWidget):
    login_success = pyqtSignal(dict, bool)
    go_register   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._auth = AuthManager()
        self.setStyleSheet("background: transparent;")
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(T.SP_LG, 0, T.SP_LG, T.SP_LG)
        outer.setAlignment(Qt.AlignCenter)

        # ── Glass panel ───────────────────────────────────────────────────────
        card = GlassCard(radius=22, shadow_blur=60, shadow_opacity=130)
        card.setFixedWidth(420)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(T.SP_XL, T.SP_XL, T.SP_XL, T.SP_XL)
        cl.setSpacing(0)

        # ── Brand orb ─────────────────────────────────────────────────────────
        orb = QLabel("◆")
        orb.setAlignment(Qt.AlignCenter)
        orb.setFixedHeight(44)
        orb.setStyleSheet(
            f"font-size: 22px; color: {T.ACCENT}; background: transparent;")
        glow(orb, color=(245, 197, 24), blur=26, alpha=200)
        cl.addWidget(orb)
        cl.addSpacing(T.SP_SM)

        # ── Title + subtitle ──────────────────────────────────────────────────
        title = QLabel("Welcome back")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"font-size: 26px; font-weight: 800; color: {T.TEXT_1};"
            " letter-spacing: -0.6px; background: transparent;")
        cl.addWidget(title)
        cl.addSpacing(4)

        sub = QLabel("Sign in to your MoodRipple account")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(_MUTED_QSS)
        cl.addWidget(sub)
        cl.addSpacing(T.SP_LG)

        # ── Error label ───────────────────────────────────────────────────────
        self.error_lbl = QLabel("")
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setStyleSheet(_ERROR_QSS)
        self.error_lbl.hide()
        cl.addWidget(self.error_lbl)
        self._error_spacer_idx = cl.count()  # track for show/hide spacing

        # ── Username ──────────────────────────────────────────────────────────
        u_lbl = QLabel("USERNAME")
        u_lbl.setStyleSheet(_FIELD_LBL)
        self.username_input = QLineEdit()
        self.username_input.setObjectName("authInput")
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setMinimumHeight(46)
        self.username_input.returnPressed.connect(self._on_login)
        cl.addWidget(u_lbl)
        cl.addSpacing(6)
        cl.addWidget(self.username_input)
        cl.addSpacing(T.SP_MD)

        # ── Password ──────────────────────────────────────────────────────────
        p_lbl = QLabel("PASSWORD")
        p_lbl.setStyleSheet(_FIELD_LBL)
        self.password_input = QLineEdit()
        self.password_input.setObjectName("authInput")
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(46)
        self.password_input.returnPressed.connect(self._on_login)
        cl.addWidget(p_lbl)
        cl.addSpacing(6)
        cl.addWidget(self.password_input)
        cl.addSpacing(T.SP_SM + 2)

        # ── Remember me ───────────────────────────────────────────────────────
        self.remember_cb = QCheckBox("Keep me signed in")
        self.remember_cb.setObjectName("authCheck")
        self.remember_cb.setStyleSheet(_CB_QSS)
        cl.addWidget(self.remember_cb)
        cl.addSpacing(T.SP_LG)

        # ── Sign In button ────────────────────────────────────────────────────
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setObjectName("authPrimaryButton")
        self.login_btn.setMinimumHeight(50)
        self.login_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.login_btn.clicked.connect(self._on_login)
        cl.addWidget(self.login_btn)
        cl.addSpacing(T.SP_MD)

        # ── Register link ─────────────────────────────────────────────────────
        link_row = QHBoxLayout()
        link_row.setAlignment(Qt.AlignCenter)
        link_row.setSpacing(5)
        no_acc = QLabel("Don't have an account?")
        no_acc.setStyleSheet(_MUTED_QSS)
        reg_link = QLabel("Create one →")
        reg_link.setObjectName("authLink")
        reg_link.setStyleSheet(_LINK_QSS)
        reg_link.setCursor(QCursor(Qt.PointingHandCursor))
        reg_link.mousePressEvent = lambda _: self.go_register.emit()
        link_row.addWidget(no_acc)
        link_row.addWidget(reg_link)
        cl.addLayout(link_row)

        outer.addWidget(card)

    # ── Slots ──────────────────────────────────────────────────────────────────
    def _on_login(self):
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in…")
        self._hide_error()

        user, error = self._auth.login(
            self.username_input.text(), self.password_input.text())

        if user:
            self.login_success.emit(user, self.remember_cb.isChecked())
        else:
            self._show_error(error)

        self.login_btn.setEnabled(True)
        self.login_btn.setText("Sign In")

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
