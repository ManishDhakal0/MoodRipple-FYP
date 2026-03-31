# services/stt_service.py
# Whisper STT — records mic audio in a QThread, transcribes via OpenAI Whisper API.

import wave
import tempfile
import os
import threading

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

try:
    import sounddevice as sd
    _SD_OK = True
except ImportError:
    _SD_OK = False

try:
    from openai import OpenAI
    _OAI_OK = True
except ImportError:
    _OAI_OK = False


class RecordingThread(QThread):
    """
    Records mic audio until stop_recording() is called (or max_seconds reached),
    then sends the WAV to OpenAI Whisper-1 and emits the transcription.
    """

    transcription_ready = pyqtSignal(str)   # final transcribed text
    error_occurred      = pyqtSignal(str)   # human-readable error
    status_changed      = pyqtSignal(str)   # "recording" | "transcribing" | "done"

    SAMPLE_RATE = 16_000  # Whisper prefers 16 kHz

    def __init__(self, api_key: str, max_seconds: int = 30, parent=None):
        super().__init__(parent)
        self._api_key   = api_key
        self._max_secs  = max_seconds
        self._stop_flag = threading.Event()
        self._chunks: list = []

    def stop_recording(self):
        """Signal the recording loop to stop and proceed to transcription."""
        self._stop_flag.set()

    def run(self):
        if not _SD_OK:
            self.error_occurred.emit(
                "sounddevice not installed. Run: pip install sounddevice")
            return
        if not _OAI_OK:
            self.error_occurred.emit(
                "openai not installed. Run: pip install openai")
            return
        if not self._api_key:
            self.error_occurred.emit(
                "No OpenAI API key — add it in Settings.")
            return

        self._chunks = []
        self._stop_flag.clear()
        self.status_changed.emit("recording")

        def _callback(indata, frames, time_info, status):
            if not self._stop_flag.is_set():
                self._chunks.append(indata.copy())

        try:
            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=1,
                dtype='int16',
                callback=_callback,
            ):
                for _ in range(self._max_secs * 10):   # poll every 100 ms
                    if self._stop_flag.is_set():
                        break
                    self.msleep(100)
        except Exception as exc:
            self.error_occurred.emit(f"Mic error: {exc}")
            return

        if not self._chunks:
            self.error_occurred.emit("No audio recorded.")
            return

        self.status_changed.emit("transcribing")
        audio = np.concatenate(self._chunks, axis=0)

        # Write to temp WAV
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        try:
            with wave.open(tmp.name, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)       # 16-bit = 2 bytes
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(audio.tobytes())

            client = OpenAI(api_key=self._api_key)
            with open(tmp.name, 'rb') as audio_file:
                result = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                )
            text = result.text.strip()
            self.transcription_ready.emit(text)
            self.status_changed.emit("done")

        except Exception as exc:
            self.error_occurred.emit(_friendly_error(exc))
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass


def _friendly_error(exc: Exception) -> str:
    """Convert raw OpenAI/network exceptions into short readable messages."""
    msg = str(exc)
    # OpenAI API error codes
    if "insufficient_quota" in msg or "429" in msg:
        return "Voice input unavailable — your OpenAI API key has no credits left. Top up at platform.openai.com/account/billing"
    if "invalid_api_key" in msg or "401" in msg:
        return "Invalid OpenAI API key. Check Settings → API Keys."
    if "rate_limit" in msg:
        return "Whisper rate limit hit — please wait a moment and try again."
    if "audio" in msg.lower() and ("format" in msg.lower() or "size" in msg.lower()):
        return "Audio too short or unreadable. Try speaking for at least 1 second."
    if "connection" in msg.lower() or "timeout" in msg.lower():
        return "No internet connection — Whisper requires an online connection."
    # Fall back to a trimmed version without the raw dict
    if "{" in msg:
        # Strip the JSON blob, keep only the first sentence
        msg = msg.split("{")[0].strip(" :-")
    return f"Whisper error: {msg}" if msg else "Whisper transcription failed."


def stt_available() -> bool:
    return _SD_OK and _OAI_OK
