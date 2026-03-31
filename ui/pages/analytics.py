# ui/pages/analytics.py
# Comprehensive Emotion Analytics — 8 charts + 6 KPI tiles, dark navy theme.

import time
from datetime import datetime

from PyQt5.QtCore    import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy,
)

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    import matplotlib
    matplotlib.rcParams.update({
        "font.family":  "sans-serif",
        "font.size":    9,
        "axes.unicode_minus": False,
    })
    _MPL_OK = True
except ImportError:
    _MPL_OK = False

from core.emotion_db import EmotionDB

# ── Palette ───────────────────────────────────────────────────────────────────
_BG_FIG  = "#0a0a0a"
_BG_AXES = "#0f0f0f"
_TXT     = "#666666"
_GRID    = "#1a1a1a"

_MOOD_COLORS = {
    "energized": "#F5C518",
    "focused":   "#60a5fa",
    "calm":      "#34d399",
    "drowsy":    "#fb923c",
}
_EMO_COLORS = {
    "happy":    "#F5C518",
    "surprise": "#FFD426",
    "neutral":  "#94a3b8",
    "fear":     "#f472b6",
    "sad":      "#60a5fa",
    "angry":    "#f87171",
    "disgust":  "#fb923c",
}
_DAY_OPTIONS = [("Today", 1), ("7 Days", 7), ("30 Days", 30)]

# ── Card styles ───────────────────────────────────────────────────────────────
_CARD_HOURLY   = ("cardHourly",
    "QFrame#cardHourly{background:#0d0d0d;"
    "border:1px solid rgba(255,255,255,0.06);border-top:2px solid rgba(245,197,24,0.55);border-radius:16px;}")
_CARD_DONUT    = ("cardDonut",
    "QFrame#cardDonut{background:#0d0d0d;"
    "border:1px solid rgba(255,255,255,0.06);border-top:2px solid rgba(245,197,24,0.40);border-radius:16px;}")
_CARD_TIMELINE = ("cardTimeline",
    "QFrame#cardTimeline{background:#0d0d0d;"
    "border:1px solid rgba(255,255,255,0.06);border-top:2px solid rgba(245,197,24,0.30);border-radius:16px;}")
_CARD_WEEKLY   = ("cardWeekly",
    "QFrame#cardWeekly{background:#0d0d0d;"
    "border:1px solid rgba(255,255,255,0.06);border-top:2px solid rgba(96,165,250,0.45);border-radius:16px;}")
_CARD_RAWEMO   = ("cardRawemo",
    "QFrame#cardRawemo{background:#0d0d0d;"
    "border:1px solid rgba(255,255,255,0.06);border-top:2px solid rgba(245,197,24,0.35);border-radius:16px;}")
_CARD_MUSIC    = ("cardMusic",
    "QFrame#cardMusic{background:#0d0d0d;"
    "border:1px solid rgba(255,255,255,0.06);border-top:2px solid rgba(52,211,153,0.45);border-radius:16px;}")
_CARD_DROWSY   = ("cardDrowsy",
    "QFrame#cardDrowsy{background:#0d0d0d;"
    "border:1px solid rgba(255,255,255,0.06);border-top:2px solid rgba(245,158,11,0.50);border-radius:16px;}")
_CARD_TRACKS   = ("cardTracks",
    "QFrame#cardTracks{background:#0d0d0d;"
    "border:1px solid rgba(255,255,255,0.06);border-top:2px solid rgba(29,185,84,0.45);border-radius:16px;}")


# ── Helpers ───────────────────────────────────────────────────────────────────
def _make_card(card_spec: tuple, icon: str, title: str, accent: str):
    """Returns (QFrame, inner_QVBoxLayout)."""
    name, qss = card_spec
    frame = QFrame()
    frame.setObjectName(name)
    frame.setStyleSheet(qss)
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(18, 16, 18, 18)
    lay.setSpacing(10)

    hdr = QHBoxLayout()
    hdr.setSpacing(8)
    ico = QLabel(icon)
    ico.setStyleSheet(f"font-size:15px; color:{accent}; background:transparent;")
    ttl = QLabel(title)
    ttl.setStyleSheet(
        f"font-size:13px; font-weight:700; color:{accent}; background:transparent; letter-spacing:0.2px;")
    hdr.addWidget(ico)
    hdr.addWidget(ttl)
    hdr.addStretch()
    lay.addLayout(hdr)
    return frame, lay


def _make_canvas(fig, height: int) -> "FigureCanvas":
    canvas = FigureCanvas(fig)
    canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    canvas.setFixedHeight(height)
    canvas.setStyleSheet("background: transparent;")
    return canvas


def _ax_style(ax, fig):
    """Apply dark theme to a matplotlib Axes."""
    fig.patch.set_facecolor(_BG_FIG)
    ax.set_facecolor(_BG_AXES)
    ax.tick_params(colors=_TXT, labelsize=8)
    ax.xaxis.label.set_color(_TXT)
    ax.yaxis.label.set_color(_TXT)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(color=_GRID, linewidth=0.5, linestyle="--", alpha=0.6)


def _no_data(ax, fig):
    ax.set_axis_off()
    ax.text(0.5, 0.5, "No data yet", ha="center", va="center",
            transform=ax.transAxes, color=_TXT, fontsize=11, alpha=0.6)
    fig.patch.set_facecolor(_BG_FIG)


# ── Main page ─────────────────────────────────────────────────────────────────
class AnalyticsPage(QWidget):

    def __init__(self, db: EmotionDB, parent=None):
        super().__init__(parent)
        self._db   = db
        self._days = 7
        self._range_btns: dict = {}
        self._build_ui()
        self.refresh()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:transparent; border:none;")

        content = QWidget()
        content.setStyleSheet("background:transparent;")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(24, 20, 24, 28)
        vbox.setSpacing(14)

        vbox.addLayout(self._build_header())
        vbox.addWidget(self._build_stat_row())
        vbox.addLayout(self._build_row1())
        vbox.addWidget(self._build_timeline_card())
        vbox.addLayout(self._build_row3())
        vbox.addLayout(self._build_row4())
        vbox.addWidget(self._build_tracks_card())

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        ico = QLabel("◆")
        ico.setStyleSheet("font-size:14px; color:#c850c0; background:transparent;")
        ttl = QLabel("Analytics")
        ttl.setStyleSheet(
            "font-size:22px; font-weight:800; color:#e8ecff;"
            " letter-spacing:-0.5px; background:transparent;")
        sub = QLabel("Your emotion & music insights")
        sub.setStyleSheet(
            "font-size:11px; color:rgba(232,236,255,0.35); background:transparent; margin-left:4px;")
        hdr.addWidget(ico)
        hdr.addWidget(ttl)
        hdr.addWidget(sub, 0, Qt.AlignBottom)
        hdr.addStretch()

        for label, days in _DAY_OPTIONS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedWidth(78)
            btn.setChecked(days == self._days)
            btn.clicked.connect(lambda _, d=days: self._set_range(d))
            btn.setObjectName("rangeBtn")
            self._range_btns[days] = btn
            hdr.addWidget(btn)

        hdr.addSpacing(4)
        ref = QPushButton("⟳  Refresh")
        ref.setObjectName("secondaryBtn")
        ref.setFixedWidth(90)
        ref.clicked.connect(self.refresh)
        hdr.addWidget(ref)
        return hdr

    def _build_stat_row(self) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background:transparent;")
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self._stat_tiles_layout = row
        # Tiles populated in _update_stats
        return container

    def _build_row1(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        # Hourly mood stacked bar
        frame, lay = _make_card(_CARD_HOURLY, "🕐", "When Am I Happiest?", "#4158d0")
        if _MPL_OK:
            self._hourly_fig    = Figure(figsize=(5, 2.8), facecolor=_BG_FIG)
            self._hourly_canvas = _make_canvas(self._hourly_fig, 260)
            lay.addWidget(self._hourly_canvas)
        row.addWidget(frame, 3)

        # Mood donut
        frame2, lay2 = _make_card(_CARD_DONUT, "◉", "Mood Breakdown", "#c850c0")
        if _MPL_OK:
            self._donut_fig    = Figure(figsize=(3.4, 2.8), facecolor=_BG_FIG)
            self._donut_canvas = _make_canvas(self._donut_fig, 260)
            lay2.addWidget(self._donut_canvas)
        row.addWidget(frame2, 2)
        return row

    def _build_timeline_card(self) -> QFrame:
        frame, lay = _make_card(_CARD_TIMELINE, "📈", "Mood Journey Over Time", "#7b4ae2")
        if _MPL_OK:
            self._tl_fig    = Figure(figsize=(8, 2.6), facecolor=_BG_FIG)
            self._tl_canvas = _make_canvas(self._tl_fig, 240)
            lay.addWidget(self._tl_canvas)
        return frame

    def _build_row3(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        frame, lay = _make_card(_CARD_WEEKLY, "📅", "Day-of-Week Patterns", "#06b6d4")
        if _MPL_OK:
            self._weekly_fig    = Figure(figsize=(4.5, 2.6), facecolor=_BG_FIG)
            self._weekly_canvas = _make_canvas(self._weekly_fig, 240)
            lay.addWidget(self._weekly_canvas)
        row.addWidget(frame, 1)

        frame2, lay2 = _make_card(_CARD_RAWEMO, "😶", "Emotion Breakdown", "#c850c0")
        if _MPL_OK:
            self._rawemo_fig    = Figure(figsize=(4.5, 2.6), facecolor=_BG_FIG)
            self._rawemo_canvas = _make_canvas(self._rawemo_fig, 240)
            lay2.addWidget(self._rawemo_canvas)
        row.addWidget(frame2, 1)
        return row

    def _build_row4(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        frame, lay = _make_card(_CARD_MUSIC, "🎵", "Does Music Improve My Mood?", "#10b981")
        if _MPL_OK:
            self._music_fig    = Figure(figsize=(4.5, 2.4), facecolor=_BG_FIG)
            self._music_canvas = _make_canvas(self._music_fig, 220)
            lay.addWidget(self._music_canvas)
        row.addWidget(frame, 1)

        frame2, lay2 = _make_card(_CARD_DROWSY, "😴", "When Am I Sleepiest?", "#f59e0b")
        if _MPL_OK:
            self._drowsy_fig    = Figure(figsize=(4.5, 2.4), facecolor=_BG_FIG)
            self._drowsy_canvas = _make_canvas(self._drowsy_fig, 220)
            lay2.addWidget(self._drowsy_canvas)
        row.addWidget(frame2, 1)
        return row

    def _build_tracks_card(self) -> QFrame:
        frame, lay = _make_card(_CARD_TRACKS, "🎧", "Top Tracks Played", "#1DB954")
        if _MPL_OK:
            self._tracks_fig    = Figure(figsize=(8, 3.0), facecolor=_BG_FIG)
            self._tracks_canvas = _make_canvas(self._tracks_fig, 280)
            lay.addWidget(self._tracks_canvas)
        return frame

    # ── Actions ───────────────────────────────────────────────────────────────
    def _set_range(self, days: int):
        self._days = days
        for d, btn in self._range_btns.items():
            btn.setChecked(d == days)
        self.refresh()

    def refresh(self):
        try:
            emotions    = self._db.get_emotions(self._days)
            mood_counts = self._db.get_mood_counts(self._days)
            hourly      = self._db.get_emotions_by_hour(self._days)
            weekly      = self._db.get_emotions_by_weekday(self._days)
            raw_emo     = self._db.get_raw_emotion_counts(self._days)
            avg_conf    = self._db.get_avg_confidence(self._days)
            drowsy_hr   = self._db.get_drowsy_by_hour(self._days)
            music_match = self._db.get_music_mood_match(self._days)
            top_tracks  = self._db.get_top_tracks(self._days, limit=12)
            sessions    = self._db.get_session_count(self._days)
        except Exception:
            return

        self._update_stats(emotions, mood_counts, hourly, avg_conf, top_tracks, sessions)

        if not _MPL_OK:
            return
        self._draw_hourly(hourly)
        self._draw_donut(mood_counts)
        self._draw_timeline(emotions)
        self._draw_weekly(weekly)
        self._draw_raw_emotions(raw_emo)
        self._draw_music_impact(music_match)
        self._draw_drowsy_hours(drowsy_hr)
        self._draw_top_tracks(top_tracks)

    # ── Stat tiles ────────────────────────────────────────────────────────────
    def _update_stats(self, emotions, mood_counts, hourly, avg_conf, top_tracks, sessions):
        # Clear old tiles
        while self._stat_tiles_layout.count():
            item = self._stat_tiles_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total = len(emotions)
        dominant = max(mood_counts, key=mood_counts.get) if mood_counts else "—"
        dom_color = _MOOD_COLORS.get(dominant, "#e8ecff")

        # Best hour = hour with most energized detections
        best_hr = "—"
        best_cnt = 0
        for h, moods in hourly.items():
            c = moods.get("energized", 0)
            if c > best_cnt:
                best_cnt = c
                best_hr = f"{h:02d}:00"

        conf_pct = f"{avg_conf * 100:.0f}%" if avg_conf else "—"
        tracks_n = str(len(top_tracks))

        tiles = [
            ("Total Detections",  str(total),       "#60a5fa"),
            ("Sessions",          str(sessions),    "#c084fc"),
            ("Dominant Mood",     dominant.capitalize(), dom_color),
            ("Best Hour",         best_hr,          "#4ade80"),
            ("Avg Confidence",    conf_pct,         "#facc15"),
            ("Tracks Played",     tracks_n,         "#1DB954"),
        ]

        for label, value, color in tiles:
            tile = QFrame()
            tile.setStyleSheet(
                "QFrame { background: rgba(255,255,255,0.04);"
                " border: 1px solid rgba(255,255,255,0.08);"
                " border-radius: 12px; }"
            )
            tl = QVBoxLayout(tile)
            tl.setContentsMargins(14, 12, 14, 12)
            tl.setSpacing(3)

            val_lbl = QLabel(value)
            val_lbl.setStyleSheet(
                f"font-size:22px; font-weight:800; color:{color}; background:transparent;")
            val_lbl.setAlignment(Qt.AlignCenter)

            key_lbl = QLabel(label)
            key_lbl.setStyleSheet(
                "font-size:10px; color:rgba(232,236,255,0.40); background:transparent;"
                " letter-spacing:0.5px;")
            key_lbl.setAlignment(Qt.AlignCenter)

            tl.addWidget(val_lbl)
            tl.addWidget(key_lbl)
            self._stat_tiles_layout.addWidget(tile, 1)

    # ── Chart: Hourly stacked bar ─────────────────────────────────────────────
    def _draw_hourly(self, data: dict):
        self._hourly_fig.clear()
        ax = self._hourly_fig.add_subplot(111)
        _ax_style(ax, self._hourly_fig)
        ax.grid(axis="y", color=_GRID, linewidth=0.5, linestyle="--", alpha=0.6)
        ax.grid(axis="x", visible=False)

        if not data:
            _no_data(ax, self._hourly_fig)
            self._hourly_canvas.draw_idle()
            return

        hours = list(range(24))
        moods = ["energized", "focused", "calm", "drowsy"]
        bottom = [0] * 24
        for mood in moods:
            vals = [data.get(h, {}).get(mood, 0) for h in hours]
            ax.bar(hours, vals, bottom=bottom, color=_MOOD_COLORS[mood],
                   width=0.7, label=mood.capitalize(), edgecolor="none", alpha=0.88)
            bottom = [b + v for b, v in zip(bottom, vals)]

        ax.set_xticks([0, 3, 6, 9, 12, 15, 18, 21, 23])
        ax.set_xticklabels(["12am", "3am", "6am", "9am", "12pm", "3pm", "6pm", "9pm", "11pm"],
                           color=_TXT, fontsize=7)
        ax.tick_params(axis="y", colors=_TXT, labelsize=7)
        ax.set_xlim(-0.5, 23.5)
        legend = ax.legend(fontsize=7, loc="upper right",
                           framealpha=0, labelcolor=_TXT, borderpad=0.3)
        self._hourly_fig.tight_layout(pad=0.8)
        self._hourly_canvas.draw_idle()

    # ── Chart: Mood donut ─────────────────────────────────────────────────────
    def _draw_donut(self, mood_counts: dict):
        self._donut_fig.clear()
        ax = self._donut_fig.add_subplot(111)
        self._donut_fig.patch.set_facecolor(_BG_FIG)
        ax.set_facecolor(_BG_FIG)

        if not mood_counts:
            _no_data(ax, self._donut_fig)
            self._donut_canvas.draw_idle()
            return

        total = sum(mood_counts.values())
        labels = list(mood_counts.keys())
        sizes  = [mood_counts[k] for k in labels]
        colors = [_MOOD_COLORS.get(k, "#666666") for k in labels]

        wedges, _ = ax.pie(
            sizes, colors=colors, startangle=90,
            wedgeprops={"width": 0.42, "edgecolor": _BG_FIG, "linewidth": 2},
        )

        dom = max(mood_counts, key=mood_counts.get)
        dom_pct = mood_counts[dom] / total * 100 if total else 0
        ax.text(0, 0.08, f"{dom_pct:.0f}%",
                ha="center", va="center", fontsize=18, fontweight="bold",
                color=_MOOD_COLORS.get(dom, "#e8ecff"))
        ax.text(0, -0.22, dom.capitalize(),
                ha="center", va="center", fontsize=9, color=_TXT)

        ax.legend(wedges, [f"{l.capitalize()} ({mood_counts[l]})" for l in labels],
                  loc="lower center", bbox_to_anchor=(0.5, -0.12),
                  ncol=2, fontsize=7, framealpha=0, labelcolor=_TXT)

        self._donut_fig.tight_layout(pad=0.4)
        self._donut_canvas.draw_idle()

    # ── Chart: Timeline step-line ─────────────────────────────────────────────
    def _draw_timeline(self, emotions: list):
        self._tl_fig.clear()
        ax = self._tl_fig.add_subplot(111)
        _ax_style(ax, self._tl_fig)

        mood_order = ["energized", "focused", "calm", "drowsy"]
        mood_y = {m: i for i, m in enumerate(mood_order)}

        if not emotions:
            _no_data(ax, self._tl_fig)
            self._tl_canvas.draw_idle()
            return

        # Group by mood and draw step lines + scatter
        by_mood: dict = {m: ([], []) for m in mood_order}
        for entry in emotions:
            mood = entry.get("mood", "focused")
            ts   = entry.get("ts", 0)
            y    = mood_y.get(mood, 0)
            dt   = datetime.fromtimestamp(ts)
            by_mood[mood][0].append(dt)
            by_mood[mood][1].append(y)

        for mood in mood_order:
            xs, ys = by_mood[mood]
            if xs:
                color = _MOOD_COLORS[mood]
                ax.scatter(xs, ys, color=color, s=10, alpha=0.7,
                           edgecolors="none", zorder=3)

        # Overall step line connecting all points by time
        all_pts = sorted(
            [(datetime.fromtimestamp(e["ts"]), mood_y.get(e.get("mood", "focused"), 0))
             for e in emotions],
            key=lambda x: x[0]
        )
        if len(all_pts) > 1:
            xs, ys = zip(*all_pts)
            ax.step(xs, ys, where="post", color=(0.55, 0.47, 1.0, 0.35),
                    linewidth=1)

        ax.set_yticks(range(len(mood_order)))
        ax.set_yticklabels([m.capitalize() for m in mood_order],
                           color=_TXT, fontsize=8)
        ax.tick_params(axis="x", colors=_TXT, labelsize=7, rotation=15)
        ax.set_ylim(-0.6, len(mood_order) - 0.4)

        self._tl_fig.tight_layout(pad=0.8)
        self._tl_canvas.draw_idle()

    # ── Chart: Weekly grouped bar ─────────────────────────────────────────────
    def _draw_weekly(self, data: dict):
        self._weekly_fig.clear()
        ax = self._weekly_fig.add_subplot(111)
        _ax_style(ax, self._weekly_fig)
        ax.grid(axis="y", color=_GRID, linewidth=0.5, linestyle="--", alpha=0.6)
        ax.grid(axis="x", visible=False)

        days_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        moods = ["energized", "focused", "calm", "drowsy"]

        if not data:
            _no_data(ax, self._weekly_fig)
            self._weekly_canvas.draw_idle()
            return

        x = list(range(7))
        n = len(moods)
        width = 0.18
        offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]

        for i, mood in enumerate(moods):
            vals = [data.get(d, {}).get(mood, 0) for d in range(7)]
            ax.bar([xi + offsets[i] for xi in x], vals,
                   width=width, color=_MOOD_COLORS[mood],
                   label=mood.capitalize(), edgecolor="none", alpha=0.88)

        ax.set_xticks(x)
        ax.set_xticklabels(days_labels, color=_TXT, fontsize=8)
        ax.tick_params(axis="y", colors=_TXT, labelsize=7)
        ax.legend(fontsize=7, framealpha=0, labelcolor=_TXT, loc="upper right")
        self._weekly_fig.tight_layout(pad=0.8)
        self._weekly_canvas.draw_idle()

    # ── Chart: Raw emotion horizontal bar ─────────────────────────────────────
    def _draw_raw_emotions(self, data: dict):
        self._rawemo_fig.clear()
        ax = self._rawemo_fig.add_subplot(111)
        _ax_style(ax, self._rawemo_fig)
        ax.grid(axis="x", color=_GRID, linewidth=0.5, linestyle="--", alpha=0.6)
        ax.grid(axis="y", visible=False)

        if not data:
            _no_data(ax, self._rawemo_fig)
            self._rawemo_canvas.draw_idle()
            return

        sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
        labels = [k.capitalize() for k, _ in sorted_items]
        values = [v for _, v in sorted_items]
        colors = [_EMO_COLORS.get(k, "#666666") for k, _ in sorted_items]

        bars = ax.barh(labels, values, color=colors, edgecolor="none",
                       alpha=0.88, height=0.6)
        for bar, v in zip(bars, values):
            ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                    str(v), va="center", ha="left", color=_TXT, fontsize=7)

        ax.tick_params(axis="y", colors=_TXT, labelsize=8)
        ax.tick_params(axis="x", colors=_TXT, labelsize=7)
        ax.set_xlim(0, max(values) * 1.2 + 1)
        ax.invert_yaxis()
        self._rawemo_fig.tight_layout(pad=0.8)
        self._rawemo_canvas.draw_idle()

    # ── Chart: Music mood match ───────────────────────────────────────────────
    def _draw_music_impact(self, data: dict):
        self._music_fig.clear()
        ax = self._music_fig.add_subplot(111)
        _ax_style(ax, self._music_fig)
        ax.grid(axis="y", color=_GRID, linewidth=0.5, linestyle="--", alpha=0.6)
        ax.grid(axis="x", visible=False)

        if not data:
            _no_data(ax, self._music_fig)
            self._music_canvas.draw_idle()
            return

        moods = list(data.keys())
        matching_pct = []
        for m in moods:
            d = data[m]
            pct = (d["matching"] / d["total"] * 100) if d["total"] > 0 else 0
            matching_pct.append(pct)

        x = list(range(len(moods)))
        width = 0.35
        ax.bar([xi - width / 2 for xi in x], matching_pct,
               width=width, color="#10b981", label="Mood matched (%)", edgecolor="none", alpha=0.88)
        ax.bar([xi + width / 2 for xi in x],
               [100 - p for p in matching_pct],
               width=width, color="#374151", label="No match (%)", edgecolor="none", alpha=0.7)

        ax.set_xticks(x)
        ax.set_xticklabels([m.capitalize() for m in moods], color=_TXT, fontsize=8)
        ax.set_ylabel("%", color=_TXT, fontsize=8)
        ax.set_ylim(0, 115)
        ax.tick_params(axis="y", colors=_TXT, labelsize=7)
        ax.legend(fontsize=7, framealpha=0, labelcolor=_TXT, loc="upper right")
        self._music_fig.tight_layout(pad=0.8)
        self._music_canvas.draw_idle()

    # ── Chart: Drowsy by hour ─────────────────────────────────────────────────
    def _draw_drowsy_hours(self, data: dict):
        self._drowsy_fig.clear()
        ax = self._drowsy_fig.add_subplot(111)
        _ax_style(ax, self._drowsy_fig)
        ax.grid(axis="y", color=_GRID, linewidth=0.5, linestyle="--", alpha=0.6)
        ax.grid(axis="x", visible=False)

        hours = list(range(24))
        vals  = [data.get(h, 0) for h in hours]

        if not any(vals):
            _no_data(ax, self._drowsy_fig)
            self._drowsy_canvas.draw_idle()
            return

        # Gradient-like alpha: darker bars at low counts
        max_v = max(vals) or 1
        alphas = [0.35 + 0.65 * (v / max_v) for v in vals]
        for h, v, a in zip(hours, vals, alphas):
            ax.bar(h, v, color="#f59e0b", alpha=a, width=0.7, edgecolor="none")

        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xticklabels(["12am", "6am", "12pm", "6pm", "11pm"],
                           color=_TXT, fontsize=7)
        ax.tick_params(axis="y", colors=_TXT, labelsize=7)
        ax.set_xlim(-0.5, 23.5)
        ax.set_ylabel("Events", color=_TXT, fontsize=8)
        self._drowsy_fig.tight_layout(pad=0.8)
        self._drowsy_canvas.draw_idle()

    # ── Chart: Top tracks horizontal bar ─────────────────────────────────────
    def _draw_top_tracks(self, data: list):
        self._tracks_fig.clear()
        ax = self._tracks_fig.add_subplot(111)
        _ax_style(ax, self._tracks_fig)
        ax.grid(axis="x", color=_GRID, linewidth=0.5, linestyle="--", alpha=0.6)
        ax.grid(axis="y", visible=False)

        if not data:
            _no_data(ax, self._tracks_fig)
            self._tracks_canvas.draw_idle()
            return

        labels = [f"{r['track'][:28]} — {r['artist'][:18]}" for r in data]
        values = [r["cnt"] for r in data]

        bars = ax.barh(labels, values, color="#1DB954", edgecolor="none",
                       alpha=0.85, height=0.6)
        for bar, v in zip(bars, values):
            ax.text(bar.get_width() + max(values) * 0.02,
                    bar.get_y() + bar.get_height() / 2,
                    str(v), va="center", ha="left", color=_TXT, fontsize=7)

        ax.tick_params(axis="y", colors=_TXT, labelsize=7)
        ax.tick_params(axis="x", colors=_TXT, labelsize=7)
        ax.set_xlim(0, max(values) * 1.2 + 1)
        ax.invert_yaxis()
        self._tracks_fig.tight_layout(pad=0.8)
        self._tracks_canvas.draw_idle()
