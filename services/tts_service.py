# services/tts_service.py
# Offline TTS using pyttsx3 — thread-safe, daemon thread so it never blocks the UI.

import threading

try:
    import pyttsx3
    _PYTTSX_OK = True
except ImportError:
    _PYTTSX_OK = False


class TTSService:
    """Speaks text aloud using pyttsx3 (offline, no API key needed)."""

    def __init__(self):
        self._lock   = threading.Lock()
        self._engine = None
        if _PYTTSX_OK:
            try:
                self._engine = pyttsx3.init()
                self._engine.setProperty('rate', 155)
                self._engine.setProperty('volume', 0.9)
            except Exception:
                self._engine = None

    def speak(self, text: str):
        """Speak text in a background daemon thread (non-blocking)."""
        if not self._engine or not text:
            return
        # Strip emoji-heavy text to avoid pronunciation weirdness
        clean = _strip_emoji(text)
        threading.Thread(target=self._run, args=(clean,), daemon=True).start()

    def _run(self, text: str):
        with self._lock:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                pass

    @staticmethod
    def available() -> bool:
        return _PYTTSX_OK


# ── Helpers ───────────────────────────────────────────────────────────────────
def _strip_emoji(text: str) -> str:
    """Remove emoji characters so pyttsx3 doesn't mispronounce them."""
    import re
    # Remove common emoji / pictograph Unicode ranges
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub('', text).strip()
