# ui/theme.py
# MoodRipple — Dark Indigo / Purple theme

STYLESHEET = """
/* ═══ Base ═══════════════════════════════════════════════════════════ */
QMainWindow, QWidget {
    background-color: #0c0e1a;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    font-size: 13px;
}
/* Labels must be transparent so card/frame gradients show through.
   Without this every QLabel renders its own background box. */
QLabel {
    background: transparent;
}
QCheckBox {
    background: transparent;
}
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical {
    background: transparent; width: 5px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #1e2844; border-radius: 2px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #7c3aed; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 5px; }
QScrollBar::handle:horizontal { background: #1e2844; border-radius: 2px; }

/* ═══ Header ══════════════════════════════════════════════════════════ */
#header {
    background-color: #090b14;
    border-bottom: 1px solid #141a30;
}
#headerTitle {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.3px;
}
#headerDot { font-size: 16px; color: #7c3aed; }
#headerSub { font-size: 11px; color: #252d45; }

/* ═══ Sidebar ═════════════════════════════════════════════════════════ */
#sidebar {
    background-color: #090b14;
    border-right: 1px solid #111829;
}
#sidebarBrand {
    font-size: 9px;
    font-weight: 700;
    color: #1e2844;
    letter-spacing: 2.5px;
    padding: 0 18px;
}
QPushButton#navButton {
    background: transparent;
    color: #3d4f6a;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
    padding: 11px 16px 11px 18px;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    min-height: 44px;
}
QPushButton#navButton:hover {
    color: #c4b5fd;
    background: rgba(124,58,237,0.07);
    border-left-color: rgba(124,58,237,0.3);
}
QPushButton#navButton:checked {
    color: #a78bfa;
    background: rgba(124,58,237,0.10);
    border-left-color: #7c3aed;
}
#navDotBad  { color: #3a1a1a; font-size: 9px; padding-left: 20px; }
#navDotGood { color: #10b981; font-size: 9px; padding-left: 20px; }

/* ═══ Card ════════════════════════════════════════════════════════════ */
#card {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #13192e, stop:1 #0f1320);
    border: 1px solid #1a2240;
    border-radius: 16px;
}
#cardTitle {
    font-size: 10px;
    font-weight: 700;
    color: #2d3a52;
    letter-spacing: 1.8px;
}
#panelScroll { background: transparent; }
#separator {
    background-color: #1a2240;
    min-height: 1px;
    max-height: 1px;
}

/* ═══ Camera ══════════════════════════════════════════════════════════ */
#cameraFeed {
    background-color: #070910;
    border: 1px solid #111829;
    border-radius: 12px;
    color: #1e2844;
    font-size: 12px;
}

/* ═══ Emotion display ═════════════════════════════════════════════════ */
#emotionEmoji { font-size: 58px; padding: 2px 0; }
#emotionName  { font-size: 24px; font-weight: 800; color: #f1f5f9; }
#emotionConf  { font-size: 11px; color: #2d3a52; }
#moodBadge {
    font-size: 11px;
    font-weight: 700;
    color: #a78bfa;
    background: rgba(124,58,237,0.13);
    border: 1px solid rgba(124,58,237,0.22);
    border-radius: 20px;
    padding: 5px 18px;
    min-height: 28px;
}
#reactionText { font-size: 11px; color: #3d4f6a; font-style: italic; }

/* ═══ Mood score bars ═════════════════════════════════════════════════ */
#barLabel { font-size: 10px; color: #3d4f6a; font-weight: 700; letter-spacing: 0.8px; }
#barPct   { font-size: 10px; color: #4a5a72; font-weight: 700; }

QProgressBar#barEnergized,
QProgressBar#barFocused,
QProgressBar#barCalm {
    background-color: #111829;
    border: none;
    border-radius: 3px;
    min-height: 6px;
    max-height: 6px;
    text-align: left;
}
QProgressBar#barEnergized::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7c3aed, stop:1 #a78bfa);
    border-radius: 3px;
}
QProgressBar#barFocused::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1d4ed8, stop:1 #60a5fa);
    border-radius: 3px;
}
QProgressBar#barCalm::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #065f46, stop:1 #10b981);
    border-radius: 3px;
}

/* ═══ Album art placeholder ═══════════════════════════════════════════ */
#albumArt {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #2e1065, stop:1 #1a1540);
    border: 1px solid #3730a3;
    border-radius: 10px;
    font-size: 28px;
    color: #6d28d9;
    min-width: 78px; min-height: 78px;
    max-width: 78px; max-height: 78px;
}

/* ═══ Track info ══════════════════════════════════════════════════════ */
#trackName   { font-size: 16px; font-weight: 800; color: #f1f5f9; }
#trackArtist { font-size: 12px; color: #3d4f6a; }
#spotifyStatus { font-size: 11px; color: #2d3a52; }

QProgressBar#trackProgress {
    background-color: #111829;
    border: none;
    border-radius: 2px;
    min-height: 4px;
    max-height: 4px;
    text-align: left;
}
QProgressBar#trackProgress::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7c3aed, stop:1 #06b6d4);
    border-radius: 2px;
}
#timeLabel { font-size: 10px; color: #2d3a52; }

/* ═══ Playback controls ═══════════════════════════════════════════════ */
QPushButton#controlButton {
    background: #111829;
    color: #6b7a8d;
    font-size: 16px;
    border: 1px solid #1a2240;
    border-radius: 50%;
    min-width: 44px; min-height: 44px;
    max-width: 44px; max-height: 44px;
}
QPushButton#controlButton:hover {
    background: #1a2240;
    border-color: #7c3aed;
    color: #c4b5fd;
}
QPushButton#controlButton:disabled {
    background: #0a0d18;
    color: #141a30;
    border-color: #0f1525;
}
QPushButton#playButton {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #7c3aed, stop:1 #6d28d9);
    color: #ffffff;
    font-size: 17px;
    border: none;
    border-radius: 50%;
    min-width: 52px; min-height: 52px;
    max-width: 52px; max-height: 52px;
}
QPushButton#playButton:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #8b5cf6, stop:1 #7c3aed);
}
QPushButton#playButton:disabled { background: #111829; color: #1a2240; }

/* ═══ Volume ══════════════════════════════════════════════════════════ */
QSlider::groove:horizontal {
    background: #111829; height: 4px; border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7c3aed, stop:1 #a78bfa);
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #c4b5fd; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: #f5f3ff; }

/* ═══ Buttons ═════════════════════════════════════════════════════════ */
QPushButton#primaryButton {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7c3aed, stop:1 #6d28d9);
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 10px 22px;
    border: none;
    border-radius: 10px;
    min-height: 40px;
}
QPushButton#primaryButton:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #8b5cf6, stop:1 #7c3aed);
}
QPushButton#primaryButton:disabled { background: #111829; color: #1e2844; }

QPushButton#secondaryButton {
    background: transparent;
    color: #3d4f6a;
    font-size: 12px;
    font-weight: 600;
    padding: 10px 22px;
    border: 1px solid #1a2240;
    border-radius: 10px;
    min-height: 40px;
}
QPushButton#secondaryButton:hover {
    background: #111829;
    color: #c4b5fd;
    border-color: #7c3aed;
}
QPushButton#secondaryButton:disabled { color: #1a2240; border-color: #111829; }

QPushButton#greenButton {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #065f46, stop:1 #10b981);
    color: #ecfdf5;
    font-size: 12px;
    font-weight: 700;
    padding: 10px 22px;
    border: none;
    border-radius: 10px;
    min-height: 40px;
}
QPushButton#greenButton:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #10b981, stop:1 #34d399);
}
QPushButton#greenButton:disabled { background: #111829; color: #1e2844; }

/* ═══ Text inputs ═════════════════════════════════════════════════════ */
QLineEdit, QTextEdit, QDateTimeEdit {
    background: #0a0d18;
    color: #e2e8f0;
    border: 1px solid #1a2240;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
    selection-background-color: #4c1d95;
    selection-color: #f5f3ff;
}
QLineEdit:focus, QTextEdit:focus, QDateTimeEdit:focus {
    border-color: #7c3aed;
    background: #0d1025;
}
QDateTimeEdit::drop-down { border: none; width: 20px; }

/* ═══ Lists ═══════════════════════════════════════════════════════════ */
QListWidget {
    background: #0a0d18;
    color: #6b7a8d;
    border: 1px solid #1a2240;
    border-radius: 10px;
    padding: 6px;
    font-size: 12px;
    outline: none;
}
QListWidget::item {
    padding: 8px 10px;
    border-radius: 7px;
    border-bottom: 1px solid #0f1525;
}
QListWidget::item:hover    { background: rgba(124,58,237,0.07); color: #c4cdd6; }
QListWidget::item:selected { background: rgba(124,58,237,0.13); color: #a78bfa; }

/* ═══ Form labels ═════════════════════════════════════════════════════ */
QLabel#formLabel { font-size: 11px; color: #2d3a52; font-weight: 600; }

/* ═══ Status bar ══════════════════════════════════════════════════════ */
#statusBar { background: #090b14; border-top: 1px solid #111829; }
#statusText { font-size: 11px; color: #1e2844; }

/* ═══ General text ════════════════════════════════════════════════════ */
#subText    { font-size: 12px; color: #3d4f6a; }
#labelMuted { font-size: 11px; color: #1e2844; }
#statusBad  { font-size: 12px; color: #ef4444; padding: 4px 0; }
#statusWarn {
    font-size: 12px; color: #f59e0b;
    background: rgba(245,158,11,0.07);
    border: 1px solid rgba(245,158,11,0.16);
    border-radius: 8px;
    padding: 10px 14px;
}
#statusGood { font-size: 12px; color: #10b981; font-weight: 600; }

/* ═══ Auth page ═══════════════════════════════════════════════════════ */
#pageTitle { font-size: 24px; font-weight: 800; color: #f1f5f9; }
#authCard {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #13192e, stop:1 #0f1320);
    border: 1px solid #1a2240;
    border-radius: 16px;
}
"""


_AUTH_STYLES = """
/* ═══ Auth window ═════════════════════════════════════════════════════ */
#authWindowCard {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #13192e, stop:1 #0e1220);
    border: 1px solid #1e2a50;
    border-radius: 20px;
}
#authLogo {
    font-size: 22px;
    color: #7c3aed;
    padding-bottom: 2px;
}
#authTitle {
    font-size: 24px;
    font-weight: 800;
    color: #f1f5f9;
    letter-spacing: 0.2px;
}
#authSub {
    font-size: 12px;
    color: #2d3a52;
}
#authFieldLabel {
    font-size: 11px;
    font-weight: 700;
    color: #3d4f6a;
    letter-spacing: 0.8px;
}
QLineEdit#authInput {
    background: #0a0d18;
    color: #e2e8f0;
    border: 1px solid #1a2240;
    border-radius: 10px;
    padding: 11px 14px;
    font-size: 13px;
    min-height: 42px;
}
QLineEdit#authInput:focus {
    border: 1px solid #7c3aed;
    background: #0d1025;
}
QPushButton#authPrimaryButton {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7c3aed, stop:1 #6d28d9);
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    border: none;
    border-radius: 12px;
    min-height: 48px;
    letter-spacing: 0.2px;
}
QPushButton#authPrimaryButton:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #8b5cf6, stop:1 #7c3aed);
}
QPushButton#authPrimaryButton:disabled {
    background: #1a2035;
    color: #2d3a52;
}
QCheckBox#authCheck {
    font-size: 12px;
    color: #3d4f6a;
    spacing: 8px;
}
QCheckBox#authCheck::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #1e2844;
    border-radius: 4px;
    background: #0a0d18;
}
QCheckBox#authCheck::indicator:checked {
    background: #7c3aed;
    border-color: #7c3aed;
}
QLabel#authLink {
    font-size: 12px;
    color: #7c3aed;
    font-weight: 600;
}
QLabel#authLink:hover { color: #a78bfa; }
QLabel#authMuted { font-size: 12px; color: #2d3a52; }
QLabel#authError {
    font-size: 12px;
    color: #ef4444;
    background: rgba(239,68,68,0.08);
    border: 1px solid rgba(239,68,68,0.18);
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 20px;
}
/* ── User info + logout in header ─────────────────────────────────── */
#headerUser {
    font-size: 12px;
    font-weight: 600;
    color: #4a5a72;
}
QPushButton#logoutButton {
    background: transparent;
    color: #2d3a52;
    font-size: 11px;
    font-weight: 600;
    border: 1px solid #1a2240;
    border-radius: 8px;
    padding: 5px 12px;
    min-height: 28px;
}
QPushButton#logoutButton:hover {
    background: rgba(239,68,68,0.08);
    color: #ef4444;
    border-color: rgba(239,68,68,0.3);
}
"""

STYLESHEET = STYLESHEET + _AUTH_STYLES


def apply_theme(widget):
    widget.setStyleSheet(STYLESHEET)
