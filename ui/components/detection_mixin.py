# ui/components/detection_mixin.py
# Mixin for DashboardPage — camera detection, emotion/score/drowsy callbacks,
# text emotion analysis.  All methods assume self is a DashboardPage instance.

import os
import json
import time
from pathlib import Path

import numpy as np
import cv2

from PyQt5.QtCore  import Qt, QThread, pyqtSignal
from PyQt5.QtGui   import QImage, QPixmap
from PyQt5.QtWidgets import QVBoxLayout, QLabel

from core.emotion_thread import EmotionDetectionThread
from core.constants      import EMOTION_TO_MOOD, EMOTION_EMOJIS, MOOD_ICONS, REACTION_MAP
from core.settings_manager import SettingsManager


# ── Background thread for text emotion (keeps GUI responsive) ─────────────────
class _TextEmotionThread(QThread):
    result_ready = pyqtSignal(dict)
    failed       = pyqtSignal(str)

    def __init__(self, detector, text: str):
        super().__init__()
        self._detector = detector
        self._text     = text

    def run(self):
        try:
            self.result_ready.emit(self._detector.predict(self._text))
        except Exception as e:
            self.failed.emit(str(e))


# ─────────────────────────────────────────────────────────────────────────────
class DetectionMixin:
    """
    Camera detection + text emotion methods.
    Mixed into DashboardPage — uses self.* attributes set in DashboardPage.__init__.
    """

    # ── Text detector init ────────────────────────────────────────────────────
    def _init_text_detector(self):
        try:
            from services.text_emotion import TextEmotionDetector
            self.text_detector = TextEmotionDetector()
        except Exception:
            self.text_detector = None

    # ── Camera detection ──────────────────────────────────────────────────────
    def start_detection(self):
        if self.detection_thread and self.detection_thread.isRunning():
            return
        self.detection_thread = EmotionDetectionThread()
        self.detection_thread.frame_ready.connect(self._on_frame)
        self.detection_thread.emotion_ready.connect(self._on_emotion)
        self.detection_thread.scores_ready.connect(self._on_scores)
        self.detection_thread.drowsy_ready.connect(self._on_drowsy)
        self.detection_thread.status_changed.connect(self.status_changed)
        self.detection_thread.is_running = True
        self.detection_thread.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_changed.emit("Loading model — please wait…", "#9da8b4")
        self._db.start_session()
        self._mood_candidate       = None
        self._mood_candidate_since = 0.0

    def stop_detection(self):
        if self.detection_thread:
            self.detection_thread.stop()
            self.detection_thread = None
        # Restore placeholder
        self.camera_label.clear()
        self.camera_label.setText("")
        if self.camera_label.layout() is None:
            ph = QVBoxLayout()
            ph.setAlignment(Qt.AlignCenter)
            ph_icon = QLabel("📷")
            ph_icon.setAlignment(Qt.AlignCenter)
            ph_icon.setStyleSheet("font-size: 48px; color: #2d4060;")
            ph_text = QLabel("Camera starts when you press  ▶  Start")
            ph_text.setAlignment(Qt.AlignCenter)
            ph_text.setStyleSheet("font-size: 12px; color: #3d5070; margin-top: 10px;")
            ph.addWidget(ph_icon)
            ph.addWidget(ph_text)
            self.camera_label.setLayout(ph)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_changed.emit("⏹  Detection stopped.", "#475569")
        # End session + optional auto-export
        sid = self._db.session_id
        self._db.end_session()
        if sid and SettingsManager.get("auto_export_session"):
            folder = SettingsManager.get("export_folder", "")
            try:
                base = self._db.export_csv(sid, folder)
                self.status_changed.emit(
                    f"Session CSV exported: {os.path.basename(base)}_*.csv", "#34d399")
            except Exception as ex:
                self.status_changed.emit(f"CSV export failed: {ex}", "#f87171")

    # ── Signal handlers ───────────────────────────────────────────────────────
    def _on_frame(self, frame: np.ndarray):
        lw = self.camera_label.width()
        lh = self.camera_label.height()
        if lw <= 0 or lh <= 0:
            return
        h, w, ch = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            lw, lh, Qt.KeepAspectRatio, Qt.FastTransformation)
        self.camera_label.setPixmap(pix)

    def _on_emotion(self, emotion: str, confidence: float, mood: str):
        # Override mood for negative emotions based on user preference
        _SAD_EMOTIONS = {"sad", "fear", "disgust", "angry"}
        if emotion in _SAD_EMOTIONS and mood == "calm":
            if SettingsManager.get("sad_music_response", "comfort") == "uplift":
                mood = "energized"

        emoji = EMOTION_EMOJIS.get(emotion, "😐")
        icon  = MOOD_ICONS.get(mood, "🎯")
        react = REACTION_MAP.get(emotion, "")
        self.emotion_emoji.setText(emoji)
        self.emotion_name.setText(emotion.capitalize())
        self.emotion_conf.setText(f"Confidence: {confidence * 100:.1f}%")
        self.mood_badge.setText(f"{icon}   {mood.capitalize()}")
        if mood == "drowsy":
            self.mood_badge.setStyleSheet(
                "font-size: 11px; font-weight: 700; color: #fbbf24;"
                "background: rgba(245,158,11,0.12); border: 1px solid rgba(245,158,11,0.28);"
                "border-radius: 20px; padding: 4px 16px; min-height: 26px;")
        else:
            self.mood_badge.setStyleSheet("")
        self.reaction_lbl.setText(react)
        # DB log
        self._db.log_emotion(emotion, mood, confidence)
        # Floating widget
        if self._mood_widget and self._mood_widget.isVisible():
            self._mood_widget.update_emotion(emotion, mood)
        # Proactive chat notify (60s cooldown to avoid spam)
        now = time.time()
        if not hasattr(self, '_last_chat_notify'):
            self._last_chat_notify = 0.0
        if (now - self._last_chat_notify) >= 60.0:
            self._last_chat_notify = now
            self.emotion_detected.emit(emotion, mood)
        # Mood cooldown
        if self.autoplay_enabled:
            cooldown = SettingsManager.get("mood_cooldown_secs", 30)
            now = time.time()
            if mood != self.current_mood:
                if mood == self._mood_candidate:
                    if (now - self._mood_candidate_since) >= cooldown:
                        self.pending_mood    = mood
                        self._mood_candidate = None
                else:
                    self._mood_candidate       = mood
                    self._mood_candidate_since = now
            else:
                self._mood_candidate = None
            self._refresh_queue_display()
            if self.current_mood is None:
                self._sync_autoplay(force_replace=False)

    def _on_scores(self, scores: dict):
        e_val = int(scores.get("happy",   0.0) * 100)
        f_val = int(scores.get("neutral", 0.0) * 100)
        c_val = int(scores.get("sad",     0.0) * 100)
        self.bar_energized.setValue(e_val);  self.pct_energized.setText(f"{e_val}%")
        self.bar_focused.setValue(f_val);    self.pct_focused.setText(f"{f_val}%")
        self.bar_calm.setValue(c_val);       self.pct_calm.setText(f"{c_val}%")

    def _on_drowsy(self, data: dict):
        if not data.get("available"):
            self._drowsy_unavail.show()
            self._drowsy_status_lbl.hide()
            return
        self._drowsy_unavail.hide()
        self._drowsy_status_lbl.show()
        if not data.get("face_detected"):
            self._drowsy_status_lbl.setText("No face detected")
            return

        ear        = data.get("ear",          0.0)
        perclos    = data.get("perclos",       0.0)
        yawns      = data.get("yawn_count",    0)
        droop      = data.get("head_drooping", False)
        is_d       = data.get("is_drowsy",     False)
        is_y       = data.get("is_yawning",    False)
        conf       = data.get("confidence",    0.0)
        blinks_min = data.get("blinks_per_min", 0)

        ear_color = "#f87171" if ear < 0.25 else "#34d399"
        self._m_ear.setText(f"{ear:.2f}")
        self._m_ear.setStyleSheet(f"font-size:13px;font-weight:700;color:{ear_color};")

        pct_color = "#fbbf24" if perclos > 0.4 else "#34d399"
        self._m_perclos.setText(f"{perclos*100:.0f}%")
        self._m_perclos.setStyleSheet(f"font-size:13px;font-weight:700;color:{pct_color};")

        self._m_yawns.setText(str(yawns) + ("  😮" if is_y else ""))
        self._m_yawns.setStyleSheet(
            f"font-size:13px;font-weight:700;color:{'#fbbf24' if is_y else '#94a3b8'};")

        head_color = "#fbbf24" if droop else "#34d399"
        self._m_head.setText("⬇ Droop" if droop else "✓ OK")
        self._m_head.setStyleSheet(f"font-size:11px;font-weight:700;color:{head_color};")

        blink_color = "#fbbf24" if blinks_min < 5 else "#34d399"
        self._m_blinks.setText(str(blinks_min))
        self._m_blinks.setStyleSheet(f"font-size:13px;font-weight:700;color:{blink_color};")

        drowsy_pct = int(conf * 100)
        self.bar_drowsy.setValue(drowsy_pct)
        self.pct_drowsy.setText(f"{drowsy_pct}%")

        if is_d:
            self._drowsy_alert.show()
            # Smart drowsy response: energetic before night_hour, chill after
            smart      = SettingsManager.get("smart_drowsy_response", True)
            night_hr   = int(SettingsManager.get("drowsy_night_hour", 22))
            cur_hour   = time.localtime().tm_hour
            if smart and cur_hour >= night_hr:
                target_mood  = SettingsManager.get("drowsy_night_music", "calm")
                badge_msg    = f"😴  Drowsy after {night_hr:02d}:00 — switching to chill music 🌙"
                status_msg   = f"⚠  Drowsy after {night_hr:02d}:00 — winding down with chill music."
            else:
                target_mood  = SettingsManager.get("drowsy_day_music", "drowsy")
                badge_msg    = "😴  Drowsiness detected — switching to energizing music now"
                status_msg   = "⚠  Drowsiness detected! Switching to energizing music."
            self._drowsy_status_lbl.setText(badge_msg)
            self._drowsy_status_lbl.setStyleSheet("font-size:11px;color:#fbbf24;")
            self.status_changed.emit(status_msg, "#fbbf24")
            if not self._was_drowsy and self.autoplay_enabled and self.sp:
                self.current_mood    = target_mood
                self.pending_mood    = None
                self._mood_candidate = None
                self._sync_autoplay(force_replace=True)
            if not self._was_drowsy:
                self._db.log_drowsy_event(ear, perclos, conf)
            self._was_drowsy = True
        elif is_y:
            self._drowsy_alert.hide()
            self._drowsy_status_lbl.setText("😮  Yawning detected — watch out")
            self._drowsy_status_lbl.setStyleSheet("font-size:11px;color:#fbbf24;")
            self._was_drowsy = False
        else:
            self._drowsy_alert.hide()
            self._drowsy_status_lbl.setText("✅  Alert  ·  EAR normal")
            self._drowsy_status_lbl.setStyleSheet("font-size:11px;color:#34d399;")
            self._was_drowsy = False

    # ── Text emotion ──────────────────────────────────────────────────────────
    def analyze_text_emotion(self):
        if self.detection_thread and self.detection_thread.isRunning():
            self.text_status_lbl.setText("Stop camera detection first to use text fallback.")
            self.text_status_lbl.setStyleSheet("color:#fbbf24;font-size:12px;")
            return
        if not self.text_detector:
            self.text_status_lbl.setText(
                "Text model unavailable — run scripts/text_emotion_train.py first.")
            self.text_status_lbl.setStyleSheet("color:#f87171;font-size:12px;")
            return
        text = self.text_input.toPlainText().strip()
        if not text:
            self.text_status_lbl.setText("Enter some text first.")
            self.text_status_lbl.setStyleSheet("color:#f87171;font-size:12px;")
            return
        self.text_analyze_btn.setEnabled(False)
        self.text_status_lbl.setText("Analysing…")
        self.text_status_lbl.setStyleSheet("color:#9da8b4;font-size:12px;")
        self._text_thread = _TextEmotionThread(self.text_detector, text)
        self._text_thread.result_ready.connect(self._on_text_result)
        self._text_thread.failed.connect(self._on_text_failed)
        self._text_thread.finished.connect(lambda: self.text_analyze_btn.setEnabled(True))
        self._text_thread.start()

    def _on_text_result(self, result: dict):
        emotion    = result["emotion"]
        confidence = result["confidence"]
        mood       = EMOTION_TO_MOOD.get(emotion, "focused")
        self.text_result.setText(f"Result: {emotion.capitalize()} ({confidence * 100:.1f}%)")
        self.text_status_lbl.setText("Text emotion is now driving mood.")
        self.text_status_lbl.setStyleSheet("color:#34d399;font-size:12px;")
        payload = {"emotion": emotion, "confidence": float(confidence),
                   "timestamp_unix": int(time.time()), "source": "text"}
        Path("latest_emotion.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8")
        self._on_emotion(emotion, confidence, mood)

    def _on_text_failed(self, err: str):
        self.text_status_lbl.setText(f"Error: {err}")
        self.text_status_lbl.setStyleSheet("color:#f87171;font-size:12px;")
