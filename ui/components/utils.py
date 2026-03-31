# ui/components/utils.py
# ─────────────────────────────────────────────────────────────────────────────
# Tailwind-inspired utility functions for the MoodRipple design system.
# Import and call these instead of hand-writing individual setStyleSheet calls.
#
# Usage:
#   from ui.components.utils import glow, shadow, pill, label, divider
# ─────────────────────────────────────────────────────────────────────────────

from PyQt5.QtWidgets import (
    QLabel, QFrame, QHBoxLayout, QVBoxLayout,
    QGraphicsDropShadowEffect, QSizePolicy,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui  import QColor, QFont

from ui.theme import T


# ══════════════════════════════════════════════════════════════════════════════
# Effect utilities
# ══════════════════════════════════════════════════════════════════════════════

def glow(widget, color: tuple = (245, 197, 24), blur: int = 26,
         y: int = 0, alpha: int = 180):
    """Attach a soft coloured glow to any widget."""
    fx = QGraphicsDropShadowEffect(widget)
    fx.setBlurRadius(blur)
    fx.setOffset(0, y)
    fx.setColor(QColor(*color, alpha))
    widget.setGraphicsEffect(fx)
    return fx


def shadow(widget, blur: int = 52, y: int = 14, alpha: int = 110):
    """Attach a dark drop shadow — creates floating / elevated depth."""
    fx = QGraphicsDropShadowEffect(widget)
    fx.setBlurRadius(blur)
    fx.setOffset(0, y)
    fx.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(fx)
    return fx


def clear_fx(widget):
    """Remove any graphics effect from a widget."""
    widget.setGraphicsEffect(None)


# ══════════════════════════════════════════════════════════════════════════════
# Layout utilities
# ══════════════════════════════════════════════════════════════════════════════

def spacing(layout, pad: int = T.SP_MD, gap: int = T.SP_SM):
    """Apply consistent padding + spacing to a layout."""
    layout.setContentsMargins(pad, pad, pad, pad)
    layout.setSpacing(gap)
    return layout


def row_layout(pad_h: int = T.SP_MD, pad_v: int = 0,
               gap: int = T.SP_SM) -> QHBoxLayout:
    """Return a pre-configured horizontal layout."""
    l = QHBoxLayout()
    l.setContentsMargins(pad_h, pad_v, pad_h, pad_v)
    l.setSpacing(gap)
    return l


def col_layout(pad: int = T.SP_MD, gap: int = T.SP_SM) -> QVBoxLayout:
    """Return a pre-configured vertical layout."""
    l = QVBoxLayout()
    l.setContentsMargins(pad, pad, pad, pad)
    l.setSpacing(gap)
    return l


# ══════════════════════════════════════════════════════════════════════════════
# Label factories
# ══════════════════════════════════════════════════════════════════════════════

def label(text: str, size: str = T.SIZE_MD, color: str = T.TEXT_1,
          weight: int = 400, align=Qt.AlignLeft,
          letter_spacing: str = "0px") -> QLabel:
    """Create a styled QLabel from design tokens."""
    lbl = QLabel(text)
    lbl.setAlignment(align)
    lbl.setStyleSheet(
        f"font-size: {size}; font-weight: {weight}; color: {color};"
        f" letter-spacing: {letter_spacing}; background: transparent;")
    return lbl


def heading(text: str, size: str = T.SIZE_XL,
            color: str = T.TEXT_1) -> QLabel:
    return label(text, size=size, color=color, weight=800,
                 letter_spacing="-0.6px", align=Qt.AlignCenter)


def subheading(text: str) -> QLabel:
    return label(text, size=T.SIZE_SM, color=T.TEXT_3,
                 align=Qt.AlignCenter)


def section_label(text: str) -> QLabel:
    """ALL-CAPS section header — like Tailwind text-xs tracking-widest."""
    return label(text.upper(), size="10px", color=T.TEXT_2,
                 weight=700, letter_spacing="2.5px")


def muted(text: str) -> QLabel:
    return label(text, size=T.SIZE_SM, color=T.TEXT_3)


def accent_text(text: str, size: str = T.SIZE_SM) -> QLabel:
    return label(text, size=size, color=T.ACCENT, weight=600)


# ══════════════════════════════════════════════════════════════════════════════
# Divider
# ══════════════════════════════════════════════════════════════════════════════

def divider(vertical: bool = False) -> QFrame:
    """1-pixel spacer line — no colour, pure transparency rhythm."""
    d = QFrame()
    if vertical:
        d.setFrameShape(QFrame.VLine)
        d.setFixedWidth(1)
    else:
        d.setFrameShape(QFrame.HLine)
        d.setFixedHeight(1)
    d.setStyleSheet("background: rgba(255,255,255,0.06); border: none;")
    return d


# ══════════════════════════════════════════════════════════════════════════════
# Status dot (connection indicator)
# ══════════════════════════════════════════════════════════════════════════════

def status_dot(connected: bool = False) -> QLabel:
    color = "rgba(52,211,153,0.80)" if connected else "rgba(255,255,255,0.15)"
    d = QLabel("●")
    d.setStyleSheet(
        f"font-size: 6px; color: {color}; background: transparent;")
    return d


# ══════════════════════════════════════════════════════════════════════════════
# Pill badge
# ══════════════════════════════════════════════════════════════════════════════

def badge(text: str, color: str = T.ACCENT,
          bg: str = T.ACCENT_GLOW) -> QLabel:
    """Small pill badge."""
    b = QLabel(text)
    b.setAlignment(Qt.AlignCenter)
    b.setStyleSheet(
        f"font-size: 10px; font-weight: 700; color: {color};"
        f" background: {bg}; border: none;"
        f" border-radius: 100px; padding: 3px 10px;")
    return b


# ══════════════════════════════════════════════════════════════════════════════
# Metric tile — small stat box used in drowsiness panel
# ══════════════════════════════════════════════════════════════════════════════

def metric_tile(caption: str):
    """Returns (QFrame, value_QLabel). Transparent glass mini-card."""
    tile = QFrame()
    tile.setStyleSheet(
        f"QFrame {{ background: rgba(255,255,255,0.05);"
        f" border: none; border-radius: {T.R_SM}px; }}"
    )
    tl = QVBoxLayout(tile)
    tl.setContentsMargins(8, 9, 8, 9)
    tl.setSpacing(3)
    val = QLabel("—")
    val.setAlignment(Qt.AlignCenter)
    val.setStyleSheet(
        f"font-size: 13px; font-weight: 700; color: {T.TEXT_1}; background: transparent;")
    cap = QLabel(caption)
    cap.setAlignment(Qt.AlignCenter)
    cap.setStyleSheet(
        f"font-size: 8px; font-weight: 600; color: {T.TEXT_3};"
        " letter-spacing: 0.5px; background: transparent;")
    tl.addWidget(val)
    tl.addWidget(cap)
    return tile, val


# ══════════════════════════════════════════════════════════════════════════════
# Bar row (mood progress bar row)
# ══════════════════════════════════════════════════════════════════════════════

def bar_row(label_text: str, accent: str):
    """Returns (QHBoxLayout, QProgressBar, pct_QLabel)."""
    from PyQt5.QtWidgets import QProgressBar
    row = QHBoxLayout()
    row.setSpacing(10)
    lbl = QLabel(label_text)
    lbl.setFixedWidth(70)
    lbl.setStyleSheet(
        f"font-size: 12px; color: {T.TEXT_2}; background: transparent;")
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(0)
    bar.setTextVisible(False)
    bar.setStyleSheet(
        f"QProgressBar {{ background: rgba(255,255,255,0.08); border: none;"
        f" border-radius: 4px; min-height: 7px; max-height: 7px; }}"
        f"QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}")
    pct = QLabel("0%")
    pct.setFixedWidth(34)
    pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    pct.setStyleSheet(
        f"font-size: 11px; color: {T.TEXT_3}; background: transparent;")
    row.addWidget(lbl)
    row.addWidget(bar, 1)
    row.addWidget(pct)
    return row, bar, pct
