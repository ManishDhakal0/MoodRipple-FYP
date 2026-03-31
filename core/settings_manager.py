# core/settings_manager.py
# Singleton settings manager — persists to moodripple_settings.json

import json
import os

_SETTINGS_FILE = "moodripple_settings.json"

DEFAULTS = {
    "ear_threshold":         0.25,
    "perclos_window":        60,
    "perclos_threshold":     0.65,
    "head_nod_thresh_deg":   20.0,
    "head_nod_frames":       30,
    "mood_cooldown_secs":    30,
    "alert_minutes":         5,
    "auto_start_detection":  False,
    "show_mood_widget":      False,
    "timezone":              "Asia/Kathmandu",
    "export_folder":         "",
    "auto_export_session":   True,
    "openai_api_key":        "",
    # Smart drowsy response
    "smart_drowsy_response": True,
    "drowsy_night_hour":     22,
    "drowsy_day_music":      "drowsy",
    "drowsy_night_music":    "calm",
    # "comfort" = play calm/soothing music when sad/angry/fearful
    # "uplift"  = play energetic/happy music to counter negative emotions
    "sad_music_response":    "comfort",
}


class SettingsManager:
    _data: dict = {}
    _loaded: bool = False

    @classmethod
    def load(cls):
        cls._data = dict(DEFAULTS)
        if os.path.exists(_SETTINGS_FILE):
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                cls._data.update({k: v for k, v in saved.items() if k in DEFAULTS})
            except Exception:
                pass
        cls._loaded = True

    @classmethod
    def _ensure(cls):
        if not cls._loaded:
            cls.load()

    @classmethod
    def get(cls, key, default=None):
        cls._ensure()
        return cls._data.get(key, DEFAULTS.get(key, default))

    @classmethod
    def set(cls, key, value):
        cls._ensure()
        cls._data[key] = value
        cls.save()

    @classmethod
    def update(cls, updates: dict):
        cls._ensure()
        cls._data.update(updates)
        cls.save()

    @classmethod
    def save(cls):
        tmp = _SETTINGS_FILE + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(cls._data, f, indent=2)
            os.replace(tmp, _SETTINGS_FILE)
        except Exception as e:
            print(f"[SettingsManager] Save failed: {e}", flush=True)

    @classmethod
    def all(cls) -> dict:
        cls._ensure()
        return dict(cls._data)
