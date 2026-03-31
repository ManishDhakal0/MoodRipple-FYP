# ui/components/spotify_autoplay.py
# Mixin for DashboardPage — all Spotify playback, track selection, and autoplay logic.

import time
import random

from core.spotify_thread   import SpotifyMonitorThread
from core.settings_manager import SettingsManager


def _ms_to_str(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


class SpotifyAutoplayMixin:
    """
    Spotify methods mixed into DashboardPage.
    Assumes self has: sp, spotify_product, spotify_monitor, autoplay_enabled,
    current_mood, pending_mood, last_playback_id, queued_ids, queued_tracks,
    queue_target, _prev_playback, _mood_candidate, status_changed, _music_prefs,
    and all the Now Playing UI widgets.
    """

    # ── Language → Spotify search queries ────────────────────────────────────
    _LANG_QUERIES = {
        "english":   ["english pop hits", "top 40 hits"],
        "nepali":    ["nepali pop songs", "nepali songs"],
        "hindi":     ["hindi songs", "hindi pop 2024"],
        "bollywood": ["bollywood hits", "bollywood 2024"],
        "kpop":      ["kpop k-pop songs", "korean pop"],
        "lofi":      ["lo-fi hip hop beats", "lofi study chill"],
        "party":     ["dance party hits", "edm dance party"],
        "classical": ["classical music", "instrumental classical"],
    }
    # ── Mood → Spotify audio feature targets (discover mode) ─────────────────
    _MOOD_FEATURES = {
        "energized": {"target_energy": 0.85, "target_valence": 0.80, "min_tempo": 115.0},
        "focused":   {"target_energy": 0.50, "target_valence": 0.50},
        "calm":      {"target_energy": 0.25, "target_valence": 0.40, "max_tempo": 100.0},
        "drowsy":    {"target_energy": 0.90, "target_valence": 0.85, "min_tempo": 125.0},
    }
    # ── Mood → search keywords ────────────────────────────────────────────────
    _MOOD_SEARCH = {
        "energized": "upbeat energetic happy",
        "focused":   "focus concentrate study",
        "calm":      "chill calm relaxing",
        "drowsy":    "pump up energy wake up hype",
    }

    # ── Spotify monitor ───────────────────────────────────────────────────────
    def _start_spotify_monitor(self):
        if self.sp and (not self.spotify_monitor or not self.spotify_monitor.isRunning()):
            self.spotify_monitor = SpotifyMonitorThread(self.sp)
            self.spotify_monitor.playback_updated.connect(self._on_playback)
            self.spotify_monitor.is_running = True
            self.spotify_monitor.start()
            for btn in (self.play_pause_btn, self.prev_btn, self.next_btn):
                btn.setEnabled(True)
            self.volume_slider.setEnabled(True)

    # ── Playback update ───────────────────────────────────────────────────────
    def _on_playback(self, info: dict):
        prev       = self._prev_playback
        current_id = info.get("track_id")
        prev_id    = self.last_playback_id

        if info["track"]      != prev.get("track"):   self.track_name_lbl.setText(info["track"])
        if info["artist"]     != prev.get("artist"):  self.track_artist_lbl.setText(info["artist"])
        if info["is_playing"] != prev.get("is_playing"):
            self.play_pause_btn.setText("⏸" if info["is_playing"] else "▶")

        progress = info.get("progress_ms", 0)
        duration = info.get("duration_ms", 0)
        if duration:
            self.track_progress.setValue(int(progress / duration * 1000))
            self.time_elapsed.setText(_ms_to_str(progress))
            if info.get("duration_ms") != prev.get("duration_ms"):
                self.time_total.setText(_ms_to_str(duration))

        if info["volume"] != prev.get("volume"):
            self.volume_slider.blockSignals(True)
            self.volume_slider.setValue(info["volume"])
            self.volume_slider.blockSignals(False)

        self._prev_playback = info

        if current_id:
            self.last_playback_id = current_id
            self._db.log_track(info.get("track", ""), info.get("artist", ""),
                               self.current_mood or "")
            if self._mood_widget and self._mood_widget.isVisible():
                self._mood_widget.update_track(info.get("track", ""), info.get("artist", ""))

        if prev_id and current_id and current_id != prev_id:
            self.queued_ids    = [i for i in self.queued_ids    if i != current_id]
            self.queued_tracks = [t for t in self.queued_tracks if t.get("id") != current_id]
            self._refresh_queue_display()
            if self.autoplay_enabled:
                self._sync_autoplay(force_replace=False)

    # ── Controls ──────────────────────────────────────────────────────────────
    def _toggle_play_pause(self):
        if not self.sp:
            return
        try:
            cur = self.sp.current_playback()
            if cur and cur.get("is_playing"):
                self.sp.pause_playback()
            else:
                dev = self._preferred_device()
                if dev:
                    self.sp.start_playback(device_id=dev)
        except Exception as e:
            self.status_changed.emit(f"Play/pause error: {e}", "#f87171")

    def _next_track(self):
        if not self.sp:
            return
        try:
            # When autoplay is active, bypass Spotify's native queue (which mixes
            # our tracks with the user's own Spotify queue) and play directly from
            # our internal queued_tracks list so the right song always plays.
            if self.autoplay_enabled and self.queued_tracks:
                self._play_queued_item(0)
                return
            self.sp.next_track()
        except Exception as e:
            self.status_changed.emit(f"Next track error: {e}", "#f87171")

    def _play_queued_item(self, index: int):
        """Skip to the track at `index` in queued_tracks immediately, mid-song."""
        if not self.sp or index >= len(self.queued_tracks):
            return
        remaining = self.queued_tracks[index:]
        uris = ["spotify:track:" + t["id"] for t in remaining if t.get("id")]
        if not uris:
            return
        dev = self._preferred_device()
        if not dev:
            return
        try:
            self.sp.start_playback(device_id=dev, uris=uris)
            played = self.queued_tracks[index]
            self.last_playback_id = played["id"]
            self.queued_ids    = [t["id"] for t in remaining[1:] if t.get("id")]
            self.queued_tracks = list(remaining[1:])
            self.track_name_lbl.setText(played.get("name", ""))
            self.track_artist_lbl.setText(played.get("artist", ""))
            self._refresh_queue_display()
            self.status_changed.emit(
                f"Skipped to: {played.get('name', '?')}", "#a78bfa")
        except Exception as e:
            self.status_changed.emit(f"Skip error: {e}", "#f87171")

    def _prev_track(self):
        if self.sp:
            try:
                self.sp.previous_track()
            except Exception as e:
                self.status_changed.emit(f"Prev track error: {e}", "#f87171")

    def _change_volume(self, val: int):
        if self.sp:
            try:
                self.sp.volume(val)
            except Exception:
                pass

    def _preferred_device(self):
        if not self.sp:
            return None
        try:
            devices = self.sp.devices().get("devices", [])
        except Exception as e:
            self.status_changed.emit(f"Cannot read Spotify devices: {e}", "#f87171")
            return None
        if not devices:
            self.status_changed.emit(
                "Open Spotify on your computer and play a song first.", "#f87171")
            return None
        for matcher in (
            lambda d: d.get("type") == "Computer" and d.get("is_active"),
            lambda d: d.get("type") == "Computer",
            lambda d: d.get("is_active"),
            lambda d: True,
        ):
            dev = next((d for d in devices if matcher(d)), None)
            if dev:
                return dev.get("id")
        return None

    def _is_premium(self) -> bool:
        return (self.spotify_product or "").lower() == "premium"

    # ── Track selection ───────────────────────────────────────────────────────
    def _mood_tracks(self, mood: str, n: int = 5) -> list:
        if not self.sp:
            return []
        source   = self._music_prefs.get("source",   "favourites")
        language = self._music_prefs.get("language", "all")
        try:
            if language != "all":
                return self._language_tracks(mood, language, n)
            if source == "discover":
                return self._discover_tracks(mood, n)
            if source == "mix":
                personal = self._personal_tracks(n)
                discover = self._discover_tracks(mood, n)
                seen, unique = set(), []
                for t in personal + discover:
                    tid = t.get("id")
                    if tid and not t.get("is_local") and tid not in seen:
                        unique.append(t); seen.add(tid)
                return unique[:n]
            return self._personal_tracks(n)
        except Exception as e:
            self.status_changed.emit(f"Cannot build Spotify queue: {e}", "#f87171")
            return []

    def _personal_tracks(self, n: int) -> list:
        recent = self.sp.current_user_recently_played(limit=50)
        tracks = [item["track"] for item in recent.get("items", [])]
        if not tracks:
            top    = self.sp.current_user_top_tracks(limit=50, time_range="short_term")
            tracks = top.get("items", [])
        seen, unique = set(), []
        for t in tracks:
            tid = t.get("id")
            if tid and not t.get("is_local") and tid not in seen:
                unique.append(t); seen.add(tid)
        random.shuffle(unique)
        return unique[:n]

    def _discover_tracks(self, mood: str, n: int) -> list:
        features = self._MOOD_FEATURES.get(mood, {})
        top      = self.sp.current_user_top_tracks(limit=5, time_range="short_term")
        seed     = [t["id"] for t in top.get("items", [])[:5] if t.get("id")]
        if not seed:
            return self._personal_tracks(n)
        recs   = self.sp.recommendations(seed_tracks=seed, limit=max(n * 3, 20), **features)
        tracks = recs.get("tracks", [])
        seen, unique = set(), []
        for t in tracks:
            tid = t.get("id")
            if tid and tid not in seen:
                unique.append(t); seen.add(tid)
        random.shuffle(unique)
        return unique[:n]

    def _language_tracks(self, mood: str, language: str, n: int) -> list:
        queries  = self._LANG_QUERIES.get(language, [language + " songs"])
        mood_kw  = self._MOOD_SEARCH.get(mood, "")
        all_tracks, seen = [], set()
        for q in queries:
            results = self.sp.search(q=f"{q} {mood_kw}".strip(), type="track", limit=30)
            for t in results.get("tracks", {}).get("items", []):
                tid = t.get("id")
                if tid and not t.get("is_local") and tid not in seen:
                    all_tracks.append(t); seen.add(tid)
            if len(all_tracks) >= n * 3:
                break
        random.shuffle(all_tracks)
        return all_tracks[:n]

    # ── Playback helpers ──────────────────────────────────────────────────────
    def _start_playback(self, uris: list) -> bool:
        dev = self._preferred_device()
        if not dev:
            return False
        try:
            self.sp.transfer_playback(device_id=dev, force_play=False)
            time.sleep(0.8)
            self.sp.start_playback(device_id=dev, uris=uris)
            return True
        except Exception as e:
            self.status_changed.emit(f"Spotify playback failed: {e}", "#f87171")
            return False

    def _queue_tracks(self, mood: str, count: int = 1) -> int:
        if not self.sp or count <= 0:
            return 0
        dev = self._preferred_device()
        if not dev:
            return 0
        tracks = self._mood_tracks(mood, n=max(count + len(self.queued_ids), 8))
        added  = 0
        for track in tracks:
            uri, tid = track.get("uri"), track.get("id")
            if not uri or not tid or tid == self.last_playback_id or tid in self.queued_ids:
                continue
            try:
                self.sp.add_to_queue(uri, device_id=dev)
            except Exception:
                continue
            self.queued_ids.append(tid)
            artist = track["artists"][0]["name"] if track.get("artists") else "Unknown"
            self.queued_tracks.append(
                {"id": tid, "name": track.get("name", "Unknown"),
                 "artist": artist, "mood": mood})
            added += 1
            if added >= count:
                break
        self._refresh_queue_display()
        return added

    # ── Autoplay control ──────────────────────────────────────────────────────
    def _start_autoplay(self):
        if not self.sp:
            self.status_changed.emit("Spotify not connected.", "#f87171")
            return
        if not self._is_premium():
            self.status_changed.emit(
                "Spotify Premium required for playback control.", "#fbbf24")
            return
        if not self._preferred_device():
            return
        self.autoplay_enabled  = True
        self.current_mood      = self.pending_mood = None
        self.last_playback_id  = None
        self.queued_ids        = []
        self.queued_tracks     = []
        self.start_autoplay_btn.setEnabled(False)
        self.stop_autoplay_btn.setEnabled(True)
        self._refresh_queue_display()
        self.status_changed.emit("Auto-play enabled.", "#34d399")

    def _stop_autoplay(self):
        self.autoplay_enabled = False
        self.current_mood     = self.pending_mood = None
        self.last_playback_id = None
        self.queued_ids       = []
        self.queued_tracks    = []
        self.start_autoplay_btn.setEnabled(True)
        self.stop_autoplay_btn.setEnabled(False)
        self._refresh_queue_display()
        self.status_changed.emit("Auto-play disabled.", "#475569")

    def _sync_autoplay(self, force_replace: bool = False):
        if not self.autoplay_enabled or not self.sp:
            return
        target = self.pending_mood or self.current_mood
        if not target:
            return
        try:
            current = self.sp.current_playback()
        except Exception as e:
            self.status_changed.emit(f"Cannot read Spotify: {e}", "#f87171")
            return
        has_track = bool(current and current.get("item") and current["item"].get("id"))
        if not has_track or force_replace:
            tracks = self._mood_tracks(target, n=max(self.queue_target, 3))
            uris   = [t["uri"] for t in tracks if t.get("uri")]
            if not uris:
                return
            if self._start_playback(uris[:self.queue_target]):
                first                  = tracks[0]
                self.current_mood      = target
                self.pending_mood      = None
                self.last_playback_id  = first.get("id")
                self.queued_ids        = [t.get("id") for t in tracks[1:self.queue_target]
                                          if t.get("id")]
                self.queued_tracks     = []
                for t in tracks[1:self.queue_target]:
                    if not t.get("id"):
                        continue
                    artist = t["artists"][0]["name"] if t.get("artists") else "Unknown"
                    self.queued_tracks.append(
                        {"id": t["id"], "name": t.get("name", "Unknown"),
                         "artist": artist, "mood": target})
                self.track_name_lbl.setText(first["name"])
                self.track_artist_lbl.setText(
                    first["artists"][0]["name"] if first.get("artists") else "")
                self._refresh_queue_display()
                self.status_changed.emit(f"Auto-play: {target} music.", "#34d399")
            return
        if self.pending_mood and self.pending_mood != self.current_mood:
            self.current_mood  = self.pending_mood
            self.pending_mood  = None
            self.queued_ids    = []
            self.queued_tracks = []
            added = self._queue_tracks(self.current_mood, count=self.queue_target)
            if added:
                self.status_changed.emit(f"Mood changed → {self.current_mood}.", "#34d399")
            return
        missing = max(0, self.queue_target - len(self.queued_ids))
        if missing:
            self._queue_tracks(target, count=missing)

    # ── Queue display ─────────────────────────────────────────────────────────
    def _refresh_queue_display(self):
        self.queue_list.setUpdatesEnabled(False)
        try:
            self.queue_list.clear()
            if self.pending_mood and self.pending_mood != self.current_mood:
                self.queue_list.addItem(
                    f"After this song: switching to {self.pending_mood}")
            if not self.queued_tracks:
                self.queue_list.addItem("No upcoming tracks queued")
                return
            for i, t in enumerate(self.queued_tracks, 1):
                tag = f" [{t['mood']}]" if t.get("mood") else ""
                self.queue_list.addItem(f"{i}.  {t['name']}  —  {t['artist']}{tag}")
        finally:
            self.queue_list.setUpdatesEnabled(True)

    # ── Music prefs ───────────────────────────────────────────────────────────
    def set_music_prefs(self, prefs: dict):
        self._music_prefs = prefs
