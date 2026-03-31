# ui/theme.py
# ─────────────────────────────────────────────────────────────────────────────
# MoodRipple Design System — Tailwind-inspired token architecture
#
# HOW TO USE
# ──────────
# 1. Import token class:        from ui.theme import T
# 2. Apply effect utilities:    from ui.theme import glow, shadow, spacing
# 3. Get style snippets:        from ui.theme import qss_input, qss_button
#
# All colours/radii/spacing in the stylesheet are derived FROM the T class —
# never hard-coded directly — so changing one token updates everything.
# ─────────────────────────────────────────────────────────────────────────────

from PyQt5.QtWidgets import QApplication, QGraphicsDropShadowEffect
from PyQt5.QtGui     import QColor


# ══════════════════════════════════════════════════════════════════════════════
# T — Design token namespace (like a Tailwind config)
# ══════════════════════════════════════════════════════════════════════════════
class T:
    # ── Base colours ──────────────────────────────────────────────────────────
    BG          = "#060609"          # near-black canvas
    BG_CARD     = "rgba(255,255,255,0.04)"   # glass fill
    BG_INPUT    = "rgba(255,255,255,0.07)"   # input rest
    BG_INPUT_HV = "rgba(255,255,255,0.11)"   # input focused
    BG_BTN_SEC  = "rgba(255,255,255,0.07)"   # secondary button

    # ── Accent ────────────────────────────────────────────────────────────────
    ACCENT      = "#F5C518"
    ACCENT_DARK = "#E8A800"
    ACCENT_GLOW = "rgba(245,197,24,0.12)"    # subtle accent fill
    ACCENT_RING = "rgba(245,197,24,0.40)"    # focus ring

    # ── Text ──────────────────────────────────────────────────────────────────
    TEXT_1  = "#F0F0F0"                      # primary
    TEXT_2  = "rgba(240,240,240,0.50)"       # secondary
    TEXT_3  = "rgba(240,240,240,0.25)"       # muted / hint
    TEXT_AC = ACCENT                         # accent text

    # ── Semantic ──────────────────────────────────────────────────────────────
    SUCCESS = "#22C55E"
    DANGER  = "#EF4444"
    WARNING = "#F97316"
    INFO    = "#60A5FA"

    # ── Spacing scale (px) ────────────────────────────────────────────────────
    SP_XS =  6
    SP_SM = 12
    SP_MD = 20
    SP_LG = 28
    SP_XL = 40

    # ── Border-radius scale ───────────────────────────────────────────────────
    R_SM =  8
    R_MD = 14
    R_LG = 20
    R_XL = 24

    # ── Typography ────────────────────────────────────────────────────────────
    FONT    = "'Segoe UI', 'SF Pro Display', Arial, sans-serif"
    SIZE_XS = "10px"
    SIZE_SM = "12px"
    SIZE_MD = "13px"
    SIZE_LG = "16px"
    SIZE_XL = "22px"
    SIZE_2X = "32px"
    SIZE_3X = "42px"

    # ── Shadow definitions (blur, y-offset, alpha) ────────────────────────────
    SHADOW_SM  = (28,  8,  80)
    SHADOW_MD  = (52, 14, 110)
    SHADOW_LG  = (72, 20, 140)
    SHADOW_XL  = (90, 24, 160)

    # ── Glow definitions (blur, alpha) ────────────────────────────────────────
    GLOW_ACCENT = (28, 180)     # yellow glow
    GLOW_WHITE  = (22, 100)     # white/neutral glow


# ══════════════════════════════════════════════════════════════════════════════
# Utility functions — apply design tokens to widgets
# ══════════════════════════════════════════════════════════════════════════════

def glow(widget, color: tuple = (245, 197, 24), blur: int = 28,
         offset: int = 0, alpha: int = 180):
    """Attach a coloured glow (QGraphicsDropShadowEffect) to a widget."""
    fx = QGraphicsDropShadowEffect(widget)
    fx.setBlurRadius(blur)
    fx.setOffset(0, offset)
    fx.setColor(QColor(*color, alpha))
    widget.setGraphicsEffect(fx)
    return fx


def shadow(widget, blur: int = 52, y: int = 14, alpha: int = 110):
    """Attach a dark drop shadow to create floating depth."""
    fx = QGraphicsDropShadowEffect(widget)
    fx.setBlurRadius(blur)
    fx.setOffset(0, y)
    fx.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(fx)
    return fx


def spacing(layout, pad: int = T.SP_MD, gap: int = T.SP_SM):
    """Set consistent margins and spacing on any layout."""
    layout.setContentsMargins(pad, pad, pad, pad)
    layout.setSpacing(gap)
    return layout


def spacing_h(layout, h_pad: int = T.SP_MD, v_pad: int = 0,
              gap: int = T.SP_SM):
    """Set horizontal-only padding on a layout (for toolbars, rows)."""
    layout.setContentsMargins(h_pad, v_pad, h_pad, v_pad)
    layout.setSpacing(gap)
    return layout


# ── QSS snippets — use these in setStyleSheet() calls ─────────────────────

def qss_input() -> str:
    """Glass input field — no border at rest, accent ring on focus."""
    return f"""
        QLineEdit, QTextEdit {{
            background: {T.BG_INPUT};
            color: {T.TEXT_1};
            border: 1px solid transparent;
            border-radius: {T.R_MD}px;
            padding: 12px 18px;
            font-size: {T.SIZE_MD};
            font-family: {T.FONT};
            selection-background-color: {T.ACCENT_GLOW};
        }}
        QLineEdit:focus, QTextEdit:focus {{
            background: {T.BG_INPUT_HV};
            border: 1px solid {T.ACCENT_RING};
        }}
        QLineEdit:hover, QTextEdit:hover {{
            background: rgba(255,255,255,0.09);
        }}
    """


def qss_button_primary() -> str:
    return f"""
        QPushButton {{
            background: {T.ACCENT};
            color: #080808;
            border: none;
            border-radius: {T.R_XL}px;
            font-size: {T.SIZE_MD};
            font-weight: 700;
            padding: 0 28px;
            min-height: 46px;
            letter-spacing: 0.2px;
        }}
        QPushButton:hover  {{ background: #FFD426; }}
        QPushButton:pressed {{ background: {T.ACCENT_DARK}; }}
        QPushButton:disabled {{
            background: rgba(245,197,24,0.10);
            color: rgba(8,8,8,0.28);
        }}
    """


def qss_button_secondary() -> str:
    return f"""
        QPushButton {{
            background: {T.BG_BTN_SEC};
            color: {T.TEXT_2};
            border: none;
            border-radius: {T.R_XL}px;
            font-size: {T.SIZE_MD};
            padding: 0 22px;
            min-height: 40px;
        }}
        QPushButton:hover  {{
            background: {T.ACCENT_GLOW};
            color: {T.ACCENT};
        }}
        QPushButton:checked {{
            background: {T.ACCENT_GLOW};
            color: {T.ACCENT};
        }}
        QPushButton:disabled {{ color: {T.TEXT_3}; }}
    """


def qss_button_ghost() -> str:
    return f"""
        QPushButton {{
            background: transparent;
            color: {T.TEXT_3};
            border: none;
            border-radius: {T.R_SM}px;
            font-size: {T.SIZE_SM};
            padding: 4px 12px;
            min-height: 28px;
        }}
        QPushButton:hover {{ color: {T.TEXT_1}; background: rgba(255,255,255,0.05); }}
    """


# ══════════════════════════════════════════════════════════════════════════════
# Global QSS stylesheet (applied to QApplication)
# Built entirely from T tokens — no hand-coded hex values.
# ══════════════════════════════════════════════════════════════════════════════
_DARK = f"""
/* ── Base ─────────────────────────────────────────────────────────────── */
QMainWindow, QDialog {{
    background-color: {T.BG};
    color: {T.TEXT_1};
    font-family: {T.FONT};
    font-size: {T.SIZE_MD};
}}
QWidget {{
    color: {T.TEXT_1};
    font-family: {T.FONT};
    font-size: {T.SIZE_MD};
}}
QLabel    {{ background: transparent; color: {T.TEXT_1}; }}
QCheckBox {{ background: transparent; }}

QWidget#dashContent,
QWidget#panelScroll {{ background: transparent; }}

/* ── Scrollbars ───────────────────────────────────────────────────────── */
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{
    background: transparent; width: 4px; margin: 6px 0;
}}
QScrollBar::handle:vertical {{
    background: {T.ACCENT_GLOW};
    border-radius: 2px; min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{ background: rgba(245,197,24,0.38); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 4px; margin: 0 6px; }}
QScrollBar::handle:horizontal {{
    background: {T.ACCENT_GLOW}; border-radius: 2px;
}}
QScrollBar::handle:horizontal:hover {{ background: rgba(245,197,24,0.38); }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Header / Status bar ──────────────────────────────────────────────── */
#header    {{ background: transparent; border: none; }}
#statusBar {{ background: transparent; border: none; }}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
#sidebar    {{ background: transparent; border: none; }}
#calSidebar {{ background: rgba(255,255,255,0.02); border: none; }}

QPushButton#navButton {{
    background: transparent;
    color: rgba(240,240,240,0.22);
    font-size: 18px; border: none;
    border-radius: {T.R_SM}px;
    min-width: 44px; min-height: 44px;
    max-width: 44px; max-height: 44px;
    padding: 0;
}}
QPushButton#navButton:hover  {{
    color: rgba(240,240,240,0.65);
    background: rgba(255,255,255,0.05);
}}
QPushButton#navButton:checked {{
    color: {T.ACCENT};
    background: {T.ACCENT_GLOW};
    border: none;
}}

#navDotBad  {{ color: rgba(248,113,113,0.55); font-size: 7px; }}
#navDotGood {{ color: rgba(52,211,153,0.75);  font-size: 7px; }}

/* ── Cards ────────────────────────────────────────────────────────────── */
#card {{
    background: {T.BG_CARD};
    border: none;
    border-radius: {T.R_LG}px;
}}
#cameraFeed {{
    background: rgba(3,3,5,0.90);
    border: none;
    border-radius: 18px;
    color: {T.TEXT_3};
    font-size: {T.SIZE_SM};
}}
#albumArt {{
    background: rgba(255,255,255,0.07);
    border: none; border-radius: 14px;
    font-size: 28px; color: rgba(245,197,24,0.50);
    min-width: 88px; min-height: 88px;
    max-width: 88px; max-height: 88px;
}}

/* ── Emotion display ──────────────────────────────────────────────────── */
#emotionEmoji {{ font-size: 72px; padding: 6px 0; }}
#emotionName  {{
    font-size: 40px; font-weight: 800;
    color: {T.TEXT_1}; letter-spacing: -1.5px;
}}
#emotionConf  {{ font-size: {T.SIZE_SM}; color: {T.TEXT_3}; }}
#moodBadge {{
    font-size: {T.SIZE_SM}; font-weight: 700;
    color: {T.ACCENT};
    background: {T.ACCENT_GLOW}; border: none;
    border-radius: 100px;
    padding: 6px 20px; min-height: 32px; letter-spacing: 0.8px;
}}
#reactionText {{ font-size: {T.SIZE_SM}; color: {T.TEXT_3}; font-style: italic; }}

/* ── Mood bars ────────────────────────────────────────────────────────── */
#barLabel {{ font-size: {T.SIZE_XS}; color: {T.TEXT_2}; font-weight: 600; }}
#barPct   {{ font-size: {T.SIZE_SM}; color: {T.TEXT_3}; font-weight: 500; }}

QProgressBar#barEnergized, QProgressBar#barFocused,
QProgressBar#barCalm, QProgressBar#barDrowsy {{
    background: rgba(255,255,255,0.08);
    border: none; border-radius: 4px;
    min-height: 7px; max-height: 7px; text-align: left;
}}
QProgressBar#barEnergized::chunk {{ background: {T.ACCENT}; border-radius: 4px; }}
QProgressBar#barFocused::chunk   {{ background: {T.INFO};   border-radius: 4px; }}
QProgressBar#barCalm::chunk      {{ background: {T.SUCCESS}; border-radius: 4px; }}
QProgressBar#barDrowsy::chunk    {{ background: {T.WARNING}; border-radius: 4px; }}

/* ── Track info ───────────────────────────────────────────────────────── */
#trackName   {{ font-size: 15px; font-weight: 600; color: {T.TEXT_1}; }}
#trackArtist {{ font-size: {T.SIZE_SM}; color: {T.TEXT_2}; }}
#spotifyStatus {{ font-size: {T.SIZE_XS}; color: {T.TEXT_3}; }}
#timeLabel   {{ font-size: {T.SIZE_XS}; color: rgba(240,240,240,0.18); }}

QProgressBar#trackProgress {{
    background: rgba(255,255,255,0.07);
    border: none; border-radius: 2px;
    min-height: 3px; max-height: 3px;
}}
QProgressBar#trackProgress::chunk {{
    background: {T.ACCENT}; border-radius: 2px;
}}

/* ── Buttons (named) ──────────────────────────────────────────────────── */
QPushButton#primaryButton, QPushButton#primaryBtn {{
    background: {T.ACCENT}; color: #080808;
    border: none; border-radius: 100px;
    font-size: {T.SIZE_MD}; font-weight: 700;
    padding: 0 26px; min-height: 42px;
}}
QPushButton#primaryButton:hover, QPushButton#primaryBtn:hover  {{ background: #FFD426; }}
QPushButton#primaryButton:disabled, QPushButton#primaryBtn:disabled {{
    background: rgba(245,197,24,0.08); color: rgba(8,8,8,0.20);
}}

QPushButton#secondaryButton, QPushButton#secondaryBtn {{
    background: {T.BG_BTN_SEC}; color: {T.TEXT_2};
    border: none; border-radius: 100px;
    font-size: {T.SIZE_MD}; padding: 0 22px; min-height: 40px;
}}
QPushButton#secondaryButton:hover, QPushButton#secondaryBtn:hover {{
    background: {T.ACCENT_GLOW}; color: {T.ACCENT};
}}
QPushButton#secondaryButton:checked, QPushButton#secondaryBtn:checked {{
    background: {T.ACCENT_GLOW}; color: {T.ACCENT};
}}
QPushButton#secondaryButton:disabled, QPushButton#secondaryBtn:disabled {{
    color: {T.TEXT_3};
}}

QPushButton#greenButton {{
    background: #16A34A; color: #fff;
    border: none; border-radius: 100px;
    font-size: {T.SIZE_MD}; font-weight: 600;
    padding: 0 26px; min-height: 40px;
}}
QPushButton#greenButton:hover    {{ background: {T.SUCCESS}; }}
QPushButton#greenButton:disabled {{ background: rgba(22,163,74,0.10); color: {T.TEXT_3}; }}

QPushButton#logoutButton {{
    background: transparent; color: {T.TEXT_3};
    border: none; border-radius: {T.R_SM}px;
    font-size: {T.SIZE_SM}; padding: 5px 14px; min-height: 28px;
}}
QPushButton#logoutButton:hover {{
    background: rgba(239,68,68,0.08); color: #fca5a5;
}}

QPushButton#themeButton {{
    background: transparent; color: {T.TEXT_3};
    border: none; border-radius: {T.R_SM}px;
    padding: 3px 10px; min-width: 32px;
    min-height: 28px; max-height: 28px;
}}
QPushButton#themeButton:hover {{
    background: {T.ACCENT_GLOW}; color: {T.ACCENT};
}}

QPushButton#rangeBtn {{
    background: transparent; color: {T.TEXT_3};
    border: none; border-radius: 100px;
    font-size: {T.SIZE_SM}; padding: 5px 14px;
}}
QPushButton#rangeBtn:checked {{
    background: {T.ACCENT_GLOW}; color: {T.ACCENT}; font-weight: 600;
}}
QPushButton#rangeBtn:hover {{ background: rgba(255,255,255,0.05); color: {T.TEXT_2}; }}

QPushButton#controlButton {{
    background: rgba(255,255,255,0.07); color: {T.TEXT_2};
    border: none; border-radius: 50%;
    font-size: 15px;
    min-width: 38px; min-height: 38px;
    max-width: 38px; max-height: 38px;
}}
QPushButton#controlButton:hover {{
    background: {T.ACCENT_GLOW}; color: {T.ACCENT};
}}
QPushButton#controlButton:disabled {{ background: transparent; color: {T.TEXT_3}; }}

QPushButton#playButton {{
    background: {T.ACCENT}; color: #080808;
    border: none; border-radius: 50%;
    font-size: 16px; font-weight: 700;
    min-width: 48px; min-height: 48px;
    max-width: 48px; max-height: 48px;
}}
QPushButton#playButton:hover    {{ background: #FFD426; }}
QPushButton#playButton:disabled {{
    background: rgba(245,197,24,0.07); color: rgba(8,8,8,0.20);
}}

QPushButton#prefPill, QPushButton#langPill {{
    background: {T.ACCENT_GLOW}; color: {T.TEXT_2};
    border: none; border-radius: 100px;
    font-size: {T.SIZE_SM}; font-weight: 500;
    padding: 4px 14px; min-height: 28px;
}}
QPushButton#prefPill:hover, QPushButton#langPill:hover {{
    background: rgba(245,197,24,0.18); color: {T.TEXT_1};
}}
QPushButton#prefPill:checked {{
    background: rgba(245,197,24,0.20); color: {T.ACCENT}; font-weight: 600;
}}
QPushButton#langPill:checked {{
    background: rgba(52,211,153,0.12); color: #6ee7b7; font-weight: 600;
}}

/* ── Inputs (generic) ─────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QDateTimeEdit {{
    background: {T.BG_INPUT}; color: {T.TEXT_1};
    border: 1px solid transparent;
    border-radius: {T.R_MD}px;
    padding: 10px 16px; font-size: {T.SIZE_MD};
    selection-background-color: {T.ACCENT_GLOW};
}}
QLineEdit:focus, QTextEdit:focus, QDateTimeEdit:focus {{
    border: 1px solid {T.ACCENT_RING};
    background: {T.BG_INPUT_HV};
}}
QLineEdit:hover {{ background: rgba(255,255,255,0.09); }}
QDateTimeEdit::drop-down {{ border: none; width: 20px; }}

/* ── Sliders ──────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    background: rgba(255,255,255,0.08); height: 4px; border-radius: 2px;
}}
QSlider::sub-page:horizontal {{ background: {T.ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {T.ACCENT}; width: 13px; height: 13px;
    margin: -5px 0; border-radius: 7px; border: none;
}}
QSlider::handle:horizontal:hover {{ background: #FFD426; }}

QSlider#settingsSlider::groove:horizontal {{
    background: rgba(255,255,255,0.08); height: 4px; border-radius: 2px;
}}
QSlider#settingsSlider::sub-page:horizontal {{
    background: {T.ACCENT}; border-radius: 2px;
}}
QSlider#settingsSlider::handle:horizontal {{
    background: {T.ACCENT}; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}}

/* ── SpinBox ──────────────────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {{
    background: {T.BG_INPUT}; color: {T.TEXT_1};
    border: 1px solid transparent; border-radius: {T.R_SM}px;
    padding: 4px 8px; font-size: {T.SIZE_SM}; min-height: 30px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {T.ACCENT_RING};
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: rgba(255,255,255,0.06); border: none; width: 18px; border-radius: 4px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {T.ACCENT_GLOW};
}}

/* ── Checkbox ─────────────────────────────────────────────────────────── */
QCheckBox {{ font-size: {T.SIZE_SM}; color: {T.TEXT_2}; spacing: 9px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 6px;
    background: {T.BG_INPUT};
}}
QCheckBox::indicator:hover   {{ border-color: {T.ACCENT_RING}; }}
QCheckBox::indicator:checked {{
    background: {T.ACCENT}; border-color: {T.ACCENT};
}}

/* ── List widget ──────────────────────────────────────────────────────── */
QListWidget {{
    background: rgba(255,255,255,0.04); color: {T.TEXT_2};
    border: none; border-radius: {T.R_MD}px;
    padding: 6px; font-size: {T.SIZE_SM}; outline: none;
}}
QListWidget::item {{ padding: 8px 12px; border-radius: {T.R_SM}px; }}
QListWidget::item:hover    {{ background: rgba(255,255,255,0.06); color: {T.TEXT_1}; }}
QListWidget::item:selected {{ background: {T.ACCENT_GLOW}; color: {T.ACCENT}; }}

/* ── Auth pages ───────────────────────────────────────────────────────── */
#pageTitle  {{ font-size: {T.SIZE_XL}; font-weight: 700; color: {T.TEXT_1}; }}
#authCard, #authWindowCard {{
    background: rgba(255,255,255,0.04); border: none; border-radius: {T.R_XL}px;
}}
#authLogo  {{ font-size: 22px; color: {T.ACCENT}; }}
#authTitle {{ font-size: 26px; font-weight: 800; color: {T.TEXT_1}; letter-spacing: -0.6px; }}
#authSub   {{ font-size: {T.SIZE_SM}; color: {T.TEXT_3}; }}
#authFieldLabel {{
    font-size: {T.SIZE_XS}; font-weight: 600;
    color: {T.TEXT_2}; letter-spacing: 0.4px;
}}
QLineEdit#authInput {{
    background: {T.BG_INPUT}; color: {T.TEXT_1};
    border: 1px solid transparent; border-radius: {T.R_MD}px;
    padding: 13px 18px; font-size: {T.SIZE_MD}; min-height: 46px;
}}
QLineEdit#authInput:focus  {{ border: 1px solid {T.ACCENT_RING}; background: {T.BG_INPUT_HV}; }}
QLineEdit#authInput:hover  {{ background: rgba(255,255,255,0.09); }}
QPushButton#authPrimaryButton {{
    background: {T.ACCENT}; color: #080808;
    font-size: {T.SIZE_MD}; font-weight: 700;
    border: none; border-radius: 100px; min-height: 50px;
}}
QPushButton#authPrimaryButton:hover    {{ background: #FFD426; }}
QPushButton#authPrimaryButton:disabled {{ background: rgba(245,197,24,0.08); color: rgba(8,8,8,0.18); }}
QCheckBox#authCheck {{ font-size: {T.SIZE_SM}; color: {T.TEXT_2}; spacing: 8px; }}
QCheckBox#authCheck::indicator {{
    width: 17px; height: 17px;
    border: 1px solid rgba(255,255,255,0.12); border-radius: 5px;
    background: {T.BG_INPUT};
}}
QCheckBox#authCheck::indicator:hover   {{ border-color: {T.ACCENT_RING}; }}
QCheckBox#authCheck::indicator:checked {{ background: {T.ACCENT}; border-color: {T.ACCENT}; }}
QLabel#authLink  {{ font-size: {T.SIZE_SM}; color: {T.ACCENT}; font-weight: 500; }}
QLabel#authMuted {{ font-size: {T.SIZE_SM}; color: {T.TEXT_3}; }}
QLabel#authError {{
    font-size: {T.SIZE_SM}; color: #fca5a5;
    background: rgba(239,68,68,0.08); border: none;
    border-radius: {T.R_SM}px; padding: 10px 14px;
}}

/* ── Status / misc ────────────────────────────────────────────────────── */
#statusText {{ font-size: {T.SIZE_XS}; color: {T.TEXT_3}; }}
#separator  {{ background: rgba(255,255,255,0.05); min-height: 1px; max-height: 1px; }}
#subText    {{ font-size: {T.SIZE_SM}; color: {T.TEXT_2}; line-height: 1.7; }}
#labelMuted {{ font-size: {T.SIZE_SM}; color: {T.TEXT_3}; }}
#statusBad  {{ font-size: {T.SIZE_SM}; color: #fca5a5; }}
#statusGood {{ font-size: {T.SIZE_SM}; color: {T.SUCCESS}; font-weight: 500; }}
#statusWarn {{
    font-size: {T.SIZE_SM}; color: {T.ACCENT};
    background: {T.ACCENT_GLOW}; border: none;
    border-radius: {T.R_MD}px; padding: 10px 16px; line-height: 1.6;
}}

/* ── Events banner ────────────────────────────────────────────────────── */
#eventsBanner {{ background: {T.ACCENT_GLOW}; border: none; }}

/* ── Connect pages ────────────────────────────────────────────────────── */
#formLabel {{ font-size: {T.SIZE_XS}; color: {T.TEXT_2}; font-weight: 500; }}
"""


# ══════════════════════════════════════════════════════════════════════════════
# ThemeManager + apply_theme (existing API, unchanged)
# ══════════════════════════════════════════════════════════════════════════════
class ThemeManager:
    _dark: bool = True

    @classmethod
    def apply(cls):
        app = QApplication.instance()
        if app:
            app.setStyleSheet(_DARK)

    @classmethod
    def toggle(cls):
        cls._dark = not cls._dark

    @classmethod
    def is_dark(cls) -> bool:
        return cls._dark


def apply_theme(app=None):
    from PyQt5.QtWidgets import QApplication as _QA
    target = app or _QA.instance()
    if target:
        target.setStyleSheet(_DARK)
