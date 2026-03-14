# core/auth.py
# AuthManager: SQLite-backed user auth with PBKDF2-SHA256 password hashing

import os
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timezone

DB_PATH      = "moodripple.db"
SESSION_PATH = "session.json"
_ITERATIONS  = 260_000


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _ITERATIONS,
    ).hex()


class AuthManager:
    """All auth / user management operations.  Thread-safe via per-call connections."""

    # ── Database setup ─────────────────────────────────────────────────────
    def init_db(self):
        """Create tables if they don't exist yet.  Call once at startup."""
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    username      TEXT    UNIQUE NOT NULL,
                    email         TEXT    UNIQUE NOT NULL,
                    password_hash TEXT    NOT NULL,
                    salt          TEXT    NOT NULL,
                    created_at    TEXT    NOT NULL,
                    last_login    TEXT
                );
            """)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Register ───────────────────────────────────────────────────────────
    def register(self, username: str, email: str, password: str) -> tuple:
        """
        Create a new user.
        Returns (user_dict, "") on success or (None, error_message) on failure.
        """
        username = username.strip()
        email    = email.strip().lower()
        password = password.strip()

        if not username or not email or not password:
            return None, "All fields are required."
        if len(username) < 3:
            return None, "Username must be at least 3 characters."
        if "@" not in email or "." not in email.split("@")[-1]:
            return None, "Please enter a valid email address."
        if len(password) < 6:
            return None, "Password must be at least 6 characters."

        salt          = secrets.token_hex(32)
        password_hash = _hash_password(password, salt)
        created_at    = _now()

        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO users (username, email, password_hash, salt, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (username, email, password_hash, salt, created_at),
                )
                user_id = conn.execute(
                    "SELECT id FROM users WHERE username = ?", (username,)
                ).fetchone()["id"]

            return {
                "id": user_id, "username": username,
                "email": email, "created_at": created_at,
            }, ""

        except sqlite3.IntegrityError as e:
            msg = str(e)
            if "username" in msg:
                return None, "That username is already taken."
            if "email" in msg:
                return None, "An account with that email already exists."
            return None, "Registration failed. Please try again."

    # ── Login ──────────────────────────────────────────────────────────────
    def login(self, username: str, password: str) -> tuple:
        """
        Verify credentials.
        Returns (user_dict, "") on success or (None, error_message) on failure.
        """
        username = username.strip()
        password = password.strip()

        if not username or not password:
            return None, "Username and password are required."

        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, username, email, password_hash, salt, created_at "
                "FROM users WHERE username = ?",
                (username,),
            ).fetchone()

        if row is None:
            return None, "Incorrect username or password."

        expected = _hash_password(password, row["salt"])
        if not secrets.compare_digest(expected, row["password_hash"]):
            return None, "Incorrect username or password."

        # Update last_login
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?", (_now(), row["id"])
            )

        return {
            "id":         row["id"],
            "username":   row["username"],
            "email":      row["email"],
            "created_at": row["created_at"],
        }, ""

    # ── Session (remember me) ──────────────────────────────────────────────
    def save_session(self, user: dict):
        """Persist user dict to session.json so next launch skips login."""
        try:
            with open(SESSION_PATH, "w", encoding="utf-8") as f:
                json.dump(user, f, indent=2)
        except OSError:
            pass

    def load_session(self) -> dict | None:
        """Return saved user dict if session.json exists and user still exists in DB."""
        if not os.path.exists(SESSION_PATH):
            return None
        try:
            with open(SESSION_PATH, encoding="utf-8") as f:
                data = json.load(f)
            user_id = data.get("id")
            if not user_id:
                return None
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT id, username, email, created_at FROM users WHERE id = ?",
                    (user_id,),
                ).fetchone()
            if row is None:
                self.clear_session()
                return None
            return {"id": row["id"], "username": row["username"],
                    "email": row["email"], "created_at": row["created_at"]}
        except Exception:
            self.clear_session()
            return None

    def clear_session(self):
        """Delete session.json."""
        try:
            os.remove(SESSION_PATH)
        except OSError:
            pass
