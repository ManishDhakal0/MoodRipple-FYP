# ui/components/glass_card.py
# GlassCard — true 3-D glass panel.
#
# Depth illusion is built from multiple painted layers (all clipped to
# the rounded rect so no stray edges ever appear):
#
#   1. Base fill        — dark glass, top-lighter / bottom-darker
#   2. Specular sheen   — upper-half gloss fade (light hitting glass face)
#   3. Top rim highlight — 2 px bright strip at very top edge (light catching rim)
#   4. Left rim highlight — 1 px subtle strip on left edge (secondary light)
#   5. Bottom inner shadow — darkens bottom interior (cavity / depth)
#   6. QGraphicsDropShadowEffect — external shadow (floating / lifted feel)

from PyQt5.QtCore    import Qt, QRectF, QPointF
from PyQt5.QtGui     import (
    QPainter, QColor, QPainterPath,
    QLinearGradient, QRadialGradient, QBrush,
)
from PyQt5.QtWidgets import QFrame, QGraphicsDropShadowEffect


class GlassCard(QFrame):
    """
    Floating 3-D glass panel.
    Light source: upper-left.
    All layers are clipped to the rounded rect — zero visible strokes/borders.
    """

    def __init__(self, parent=None, radius: int = 20,
                 shadow_blur: int = 52, shadow_opacity: int = 130):
        super().__init__(parent)
        self._r = radius
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("GlassCard { background: transparent; border: none; }")

        # External drop shadow — primary depth signal
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(shadow_blur)
        shadow.setOffset(0, 18)
        shadow.setColor(QColor(0, 0, 0, shadow_opacity))
        self.setGraphicsEffect(shadow)

    # ─────────────────────────────────────────────────────────────────────────
    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        r    = float(self._r)
        w    = rect.width()
        h    = rect.height()
        x0   = rect.left()
        y0   = rect.top()

        # Clip everything to the rounded shape — no stray pixels possible
        clip = QPainterPath()
        clip.addRoundedRect(rect, r, r)
        p.setClipPath(clip)

        # ── Layer 1 · Base dark-glass fill ───────────────────────────────────
        # Light hits the top face, shadow pools at the bottom — like a slab
        base = QLinearGradient(0, y0, 0, y0 + h)
        base.setColorAt(0.00, QColor(255, 255, 255, 26))   # lighter top
        base.setColorAt(0.45, QColor(255, 255, 255, 13))
        base.setColorAt(1.00, QColor(0,   0,   0,  22))    # darker bottom
        p.fillRect(rect, QBrush(base))

        # ── Layer 2 · Upper specular sheen ───────────────────────────────────
        # Broad gloss covering ~45% of the height — as if the pane curves away
        sheen = QLinearGradient(0, y0, 0, y0 + h * 0.45)
        sheen.setColorAt(0.0, QColor(255, 255, 255, 22))
        sheen.setColorAt(1.0, QColor(255, 255, 255,  0))
        p.fillRect(rect, QBrush(sheen))

        # ── Layer 3 · Corner specular spot (upper-left catch-light) ──────────
        spot = QRadialGradient(QPointF(x0 + w * 0.25, y0 + h * 0.12), w * 0.38)
        spot.setColorAt(0.0, QColor(255, 255, 255, 28))
        spot.setColorAt(1.0, QColor(255, 255, 255,  0))
        p.fillRect(rect, QBrush(spot))

        # ── Layer 4 · Top rim highlight (2 px) ───────────────────────────────
        # Simulates light striking the top glass edge — gives lift / 3-D pop
        rim_top = QRectF(x0, y0, w, 2.0)
        rim_grad = QLinearGradient(x0, 0, x0 + w, 0)
        rim_grad.setColorAt(0.0,  QColor(255, 255, 255, 80))
        rim_grad.setColorAt(0.35, QColor(255, 255, 255, 90))
        rim_grad.setColorAt(0.65, QColor(255, 255, 255, 90))
        rim_grad.setColorAt(1.0,  QColor(255, 255, 255, 80))
        p.fillRect(rim_top, QBrush(rim_grad))

        # ── Layer 5 · Left rim highlight (1 px) ──────────────────────────────
        rim_left = QRectF(x0, y0, 1.5, h)
        left_grad = QLinearGradient(0, y0, 0, y0 + h)
        left_grad.setColorAt(0.0,  QColor(255, 255, 255, 50))
        left_grad.setColorAt(0.5,  QColor(255, 255, 255, 20))
        left_grad.setColorAt(1.0,  QColor(255, 255, 255,  0))
        p.fillRect(rim_left, QBrush(left_grad))

        # ── Layer 6 · Bottom inner shadow ────────────────────────────────────
        # Darkens the bottom ~30% — cavity effect, makes card feel thick
        bot = QLinearGradient(0, y0 + h * 0.70, 0, y0 + h)
        bot.setColorAt(0.0, QColor(0, 0, 0,  0))
        bot.setColorAt(1.0, QColor(0, 0, 0, 55))
        p.fillRect(rect, QBrush(bot))

        # ── Layer 7 · Right / bottom edge darkening ───────────────────────────
        # Opposite-side darkening reinforces the light-source direction
        edge_r = QLinearGradient(x0 + w - 30, 0, x0 + w, 0)
        edge_r.setColorAt(0.0, QColor(0, 0, 0,  0))
        edge_r.setColorAt(1.0, QColor(0, 0, 0, 30))
        p.fillRect(rect, QBrush(edge_r))

        p.end()
