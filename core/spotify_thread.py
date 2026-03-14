# core/spotify_thread.py
# Spotify background threads: OAuth auth + playback monitor

import os
import time
from PyQt5.QtCore import QThread, pyqtSignal

from core.constants import (
    SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI, SPOTIFY_SCOPE, SPOTIFY_CACHE_PATH,
)


class SpotifyAuthThread(QThread):
    """Run Spotify OAuth in background so the UI stays responsive."""
    success = pyqtSignal(object, str, str)   # sp client, display_name, product
    failed  = pyqtSignal(str)

    def __init__(self, interactive: bool = False):
        super().__init__()
        self.interactive = interactive

    def run(self):
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth

            sp = spotipy.Spotify(
                auth_manager=SpotifyOAuth(
                    client_id=SPOTIFY_CLIENT_ID,
                    client_secret=SPOTIFY_CLIENT_SECRET,
                    redirect_uri=SPOTIFY_REDIRECT_URI,
                    scope=SPOTIFY_SCOPE,
                    cache_path=SPOTIFY_CACHE_PATH,
                    open_browser=self.interactive,
                    show_dialog=self.interactive,
                )
            )
            user         = sp.current_user()
            display_name = user.get("display_name") or user.get("id", "unknown")
            product      = user.get("product", "unknown")
            self.success.emit(sp, display_name, product)

        except Exception as e:
            self.failed.emit(str(e))


class SpotifyMonitorThread(QThread):
    """Poll Spotify every second and emit current playback state."""
    playback_updated = pyqtSignal(dict)

    def __init__(self, sp):
        super().__init__()
        self.sp         = sp
        self.is_running = False

    def run(self):
        while self.is_running:
            try:
                current = self.sp.current_playback()
                if current and current.get("item"):
                    item = current["item"]
                    self.playback_updated.emit({
                        "track_id":    item.get("id"),
                        "track":       item["name"],
                        "artist":      item["artists"][0]["name"],
                        "is_playing":  current["is_playing"],
                        "volume":      current.get("device", {}).get("volume_percent", 50),
                        "progress_ms": current.get("progress_ms", 0),
                        "duration_ms": item.get("duration_ms", 0),
                    })
            except Exception:
                pass
            time.sleep(1)

    def stop(self):
        self.is_running = False
        self.wait()
