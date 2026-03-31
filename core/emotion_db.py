# core/emotion_db.py
# SQLite emotion history — logs every detected emotion, drowsy events, and played tracks.

import os
import csv
import sqlite3
import time
from datetime import datetime

_DB_FILE = "moodripple_history.db"

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  INTEGER NOT NULL,
    ended_at    INTEGER,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS emotions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL,
    ts          INTEGER NOT NULL,
    emotion     TEXT NOT NULL,
    mood        TEXT NOT NULL,
    confidence  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS drowsy_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL,
    ts          INTEGER NOT NULL,
    ear         REAL,
    perclos     REAL,
    confidence  REAL
);

CREATE TABLE IF NOT EXISTS tracks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL,
    ts          INTEGER NOT NULL,
    track       TEXT,
    artist      TEXT,
    mood        TEXT
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _connect()
    conn.executescript(_CREATE_SQL)
    conn.commit()
    conn.close()


_init_db()


class EmotionDB:
    """Thread-safe SQLite wrapper for emotion history."""

    def __init__(self):
        self._conn = _connect()
        self._session_id: int = 0
        self._last_track: str = ""

    # ── Sessions ─────────────────────────────────────────────────────────────
    def start_session(self) -> int:
        cur = self._conn.execute(
            "INSERT INTO sessions (started_at) VALUES (?)", (int(time.time()),)
        )
        self._conn.commit()
        self._session_id = cur.lastrowid
        self._last_track = ""
        return self._session_id

    def end_session(self):
        if self._session_id:
            self._conn.execute(
                "UPDATE sessions SET ended_at=? WHERE id=?",
                (int(time.time()), self._session_id),
            )
            self._conn.commit()
        self._session_id = 0

    @property
    def session_id(self) -> int:
        return self._session_id

    # ── Logging ──────────────────────────────────────────────────────────────
    def log_emotion(self, emotion: str, mood: str, confidence: float):
        if not self._session_id:
            return
        self._conn.execute(
            "INSERT INTO emotions (session_id, ts, emotion, mood, confidence) VALUES (?,?,?,?,?)",
            (self._session_id, int(time.time()), emotion, mood, round(confidence, 4)),
        )
        self._conn.commit()

    def log_drowsy_event(self, ear: float, perclos: float, confidence: float):
        if not self._session_id:
            return
        self._conn.execute(
            "INSERT INTO drowsy_events (session_id, ts, ear, perclos, confidence) VALUES (?,?,?,?,?)",
            (self._session_id, int(time.time()),
             round(ear, 3), round(perclos, 3), round(confidence, 3)),
        )
        self._conn.commit()

    def log_track(self, track: str, artist: str, mood: str):
        """Only logs when track actually changes (deduplication)."""
        if not self._session_id:
            return
        key = f"{track}||{artist}"
        if key == self._last_track:
            return
        self._last_track = key
        self._conn.execute(
            "INSERT INTO tracks (session_id, ts, track, artist, mood) VALUES (?,?,?,?,?)",
            (self._session_id, int(time.time()), track, artist, mood),
        )
        self._conn.commit()

    # ── Queries ───────────────────────────────────────────────────────────────
    def get_emotions(self, days: int = 1) -> list:
        since = int(time.time()) - days * 86400
        rows = self._conn.execute(
            "SELECT ts, emotion, mood, confidence FROM emotions WHERE ts >= ? ORDER BY ts",
            (since,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_mood_counts(self, days: int = 1) -> dict:
        since = int(time.time()) - days * 86400
        rows = self._conn.execute(
            "SELECT mood, COUNT(*) as cnt FROM emotions WHERE ts >= ? GROUP BY mood",
            (since,),
        ).fetchall()
        return {r["mood"]: r["cnt"] for r in rows}

    def get_sessions(self, limit: int = 20) -> list:
        rows = self._conn.execute(
            "SELECT id, started_at, ended_at FROM sessions ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_session_emotions(self, session_id: int) -> list:
        rows = self._conn.execute(
            "SELECT ts, emotion, mood, confidence FROM emotions WHERE session_id=? ORDER BY ts",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_session_tracks(self, session_id: int) -> list:
        rows = self._conn.execute(
            "SELECT ts, track, artist, mood FROM tracks WHERE session_id=? ORDER BY ts",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_session_drowsy(self, session_id: int) -> list:
        rows = self._conn.execute(
            "SELECT ts, ear, perclos, confidence FROM drowsy_events WHERE session_id=? ORDER BY ts",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Analytics queries ─────────────────────────────────────────────────────
    def get_emotions_by_hour(self, days: int = 7) -> dict:
        """Returns {hour(int 0-23): {mood: count}} for the last N days."""
        since = int(time.time()) - days * 86400
        rows = self._conn.execute(
            "SELECT CAST(strftime('%H', ts, 'unixepoch', 'localtime') AS INTEGER) AS h,"
            " mood, COUNT(*) as cnt FROM emotions WHERE ts >= ? GROUP BY h, mood",
            (since,)
        ).fetchall()
        result: dict = {}
        for r in rows:
            result.setdefault(r["h"], {})[r["mood"]] = r["cnt"]
        return result

    def get_emotions_by_weekday(self, days: int = 30) -> dict:
        """Returns {weekday(0=Mon..6=Sun): {mood: count}}."""
        since = int(time.time()) - days * 86400
        rows = self._conn.execute(
            "SELECT (CAST(strftime('%w', ts, 'unixepoch', 'localtime') AS INTEGER) + 6) % 7 AS wd,"
            " mood, COUNT(*) as cnt FROM emotions WHERE ts >= ? GROUP BY wd, mood",
            (since,)
        ).fetchall()
        result: dict = {}
        for r in rows:
            result.setdefault(r["wd"], {})[r["mood"]] = r["cnt"]
        return result

    def get_top_tracks(self, days: int = 30, limit: int = 10) -> list:
        """Returns [{track, artist, count}] sorted by play count desc."""
        since = int(time.time()) - days * 86400
        rows = self._conn.execute(
            "SELECT track, artist, COUNT(*) as cnt FROM tracks WHERE ts >= ?"
            " GROUP BY track, artist ORDER BY cnt DESC LIMIT ?",
            (since, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_raw_emotion_counts(self, days: int = 7) -> dict:
        """Returns {emotion: count} for all 7 raw face emotions."""
        since = int(time.time()) - days * 86400
        rows = self._conn.execute(
            "SELECT emotion, COUNT(*) as cnt FROM emotions WHERE ts >= ? GROUP BY emotion",
            (since,)
        ).fetchall()
        return {r["emotion"]: r["cnt"] for r in rows}

    def get_avg_confidence(self, days: int = 7) -> float:
        """Returns average detection confidence 0-1."""
        since = int(time.time()) - days * 86400
        row = self._conn.execute(
            "SELECT AVG(confidence) as avg_conf FROM emotions WHERE ts >= ?", (since,)
        ).fetchone()
        return round(row["avg_conf"] or 0.0, 3)

    def get_drowsy_by_hour(self, days: int = 7) -> dict:
        """Returns {hour(int 0-23): count} of drowsy events."""
        since = int(time.time()) - days * 86400
        rows = self._conn.execute(
            "SELECT CAST(strftime('%H', ts, 'unixepoch', 'localtime') AS INTEGER) AS h,"
            " COUNT(*) as cnt FROM drowsy_events WHERE ts >= ? GROUP BY h",
            (since,)
        ).fetchall()
        return {r["h"]: r["cnt"] for r in rows}

    def get_music_mood_match(self, days: int = 7) -> dict:
        """Returns {music_mood: {matching: int, total: int}}.
        Joins tracks to emotions within 60-second windows."""
        since = int(time.time()) - days * 86400
        rows = self._conn.execute(
            "SELECT t.mood AS mm, e.mood AS em, COUNT(*) as cnt"
            " FROM tracks t JOIN emotions e ON ABS(e.ts - t.ts) < 60"
            " WHERE t.ts >= ? GROUP BY t.mood, e.mood",
            (since,)
        ).fetchall()
        result: dict = {}
        for r in rows:
            d = result.setdefault(r["mm"], {"matching": 0, "total": 0})
            d["total"] += r["cnt"]
            if r["mm"] == r["em"]:
                d["matching"] += r["cnt"]
        return result

    def get_session_count(self, days: int = 7) -> int:
        """Returns number of sessions started in the last N days."""
        since = int(time.time()) - days * 86400
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM sessions WHERE started_at >= ?", (since,)
        ).fetchone()
        return row["cnt"] if row else 0

    # ── CSV Export ────────────────────────────────────────────────────────────
    def export_csv(self, session_id: int, folder: str = "") -> str:
        """Export session data to CSV files. Returns the base path used."""
        if not folder:
            folder = os.getcwd()
        os.makedirs(folder, exist_ok=True)

        dt = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.join(folder, f"moodripple_session_{session_id}_{dt}")

        emotions = self.get_session_emotions(session_id)
        tracks   = self.get_session_tracks(session_id)
        drowsy   = self.get_session_drowsy(session_id)

        def _ts(t):
            return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")

        with open(base + "_emotions.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["time", "emotion", "mood", "confidence"])
            w.writeheader()
            for r in emotions:
                w.writerow({"time": _ts(r["ts"]), "emotion": r["emotion"],
                            "mood": r["mood"], "confidence": r["confidence"]})

        with open(base + "_tracks.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["time", "track", "artist", "mood"])
            w.writeheader()
            for r in tracks:
                w.writerow({"time": _ts(r["ts"]), "track": r["track"],
                            "artist": r["artist"], "mood": r["mood"]})

        if drowsy:
            with open(base + "_drowsy.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["time", "ear", "perclos", "confidence"])
                w.writeheader()
                for r in drowsy:
                    w.writerow({"time": _ts(r["ts"]), "ear": r["ear"],
                                "perclos": r["perclos"], "confidence": r["confidence"]})

        return base

    def _get_hourly_raw(self, days: int = 7) -> dict:
        """Returns {hour(int 0-23): {emotion: count}} for raw 7 face emotions."""
        since = int(time.time()) - days * 86400
        rows = self._conn.execute(
            "SELECT CAST(strftime('%H', ts, 'unixepoch', 'localtime') AS INTEGER) AS h,"
            " emotion, COUNT(*) as cnt FROM emotions WHERE ts >= ? GROUP BY h, emotion",
            (since,)
        ).fetchall()
        result: dict = {}
        for r in rows:
            result.setdefault(r["h"], {})[r["emotion"]] = r["cnt"]
        return result

    def get_stats(self, days: int = 7) -> dict:
        """Comprehensive analytics bundle for the web frontend."""
        emotions     = self.get_emotions(days)
        mood_counts  = self.get_mood_counts(days)
        raw_emo      = self.get_raw_emotion_counts(days)
        hourly_moods = self.get_emotions_by_hour(days)
        weekday_moods= self.get_emotions_by_weekday(days)
        top_tracks   = self.get_top_tracks(days, limit=10)
        avg_conf     = self.get_avg_confidence(days)
        drowsy_hr    = self.get_drowsy_by_hour(days)
        music_match  = self.get_music_mood_match(days)
        sessions     = self.get_session_count(days)
        hourly_raw   = self._get_hourly_raw(days)

        since = int(time.time()) - days * 86400
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM drowsy_events WHERE ts >= ?", (since,)
        ).fetchone()
        drowsy_count = row["cnt"] if row else 0

        # Best hour = hour with most energized detections
        best_hr, best_cnt = None, 0
        for h, moods in hourly_moods.items():
            c = moods.get("energized", 0)
            if c > best_cnt:
                best_cnt = c; best_hr = h

        dominant_mood = max(mood_counts, key=mood_counts.get) if mood_counts else None

        # Wellbeing score 0-100: weighted positive mood ratio
        total = len(emotions)
        wellbeing = None
        if total > 0:
            e_c = mood_counts.get("energized", 0)
            f_c = mood_counts.get("focused", 0)
            c_c = mood_counts.get("calm", 0)
            wellbeing = round(min(100, max(0, (e_c * 3 + f_c * 2 + c_c) / (total * 3) * 100)))

        # Downsample timeline to ≤300 points for JS perf
        step = max(1, len(emotions) // 300)
        timeline = [
            {"ts": e["ts"], "mood": e["mood"], "confidence": round(e["confidence"], 3)}
            for e in emotions[::step]
        ]

        return {
            "days":              days,
            "total_detections":  total,
            "sessions":          sessions,
            "dominant_mood":     dominant_mood,
            "best_hour":         best_hr,
            "avg_confidence":    avg_conf,
            "track_count":       len(top_tracks),
            "drowsy_events":     drowsy_count,
            "wellbeing_score":   wellbeing,
            "mood_counts":       mood_counts,
            "raw_emotion_counts":raw_emo,
            "hourly_moods":      {str(k): v for k, v in hourly_moods.items()},
            "weekday_moods":     {str(k): v for k, v in weekday_moods.items()},
            "top_tracks":        top_tracks,
            "timeline":          timeline,
            "drowsy_by_hour":    {str(k): v for k, v in drowsy_hr.items()},
            "music_match":       music_match,
            "hourly_raw":        {str(k): v for k, v in hourly_raw.items()},
        }

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass
