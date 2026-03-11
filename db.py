"""
SQLite persistence for Olympus Training Log — multi-user edition.

All player state is stored as JSON blobs so the existing game engines
(PlayerState, core.py dicts) are unchanged.

Env vars:
  DB_PATH   path to .db file  (default: olympus.db)
            On Render free tier use /tmp/olympus.db or mount a disk.
"""
import sqlite3, json, os, datetime as dt
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", "olympus.db"))

_DDL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT UNIQUE NOT NULL COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        created_at    TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS player_estate (
        user_id    INTEGER PRIMARY KEY REFERENCES users(id),
        data       TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS player_legacy (
        user_id    INTEGER PRIMARY KEY REFERENCES users(id),
        data       TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
]


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    for stmt in _DDL:
        conn.execute(stmt)
    conn.commit()
    return conn


# ── User management ───────────────────────────────────────────────────────────

def create_user(username: str, password_hash: str) -> int:
    """Insert a new user and return their id. Raises on duplicate username."""
    now = dt.datetime.utcnow().isoformat()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, now),
        )
        return cur.lastrowid


def get_user_by_username(username: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


# ── Per-user estate state (Laurel of Olympus RPG) ────────────────────────────

def load_estate(user_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT data FROM player_estate WHERE user_id = ?", (user_id,)
        ).fetchone()
        return json.loads(row["data"]) if row else None


def save_estate(user_id: int, data: dict) -> None:
    now = dt.datetime.utcnow().isoformat()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO player_estate (user_id, data, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                data       = excluded.data,
                updated_at = excluded.updated_at
            """,
            (user_id, json.dumps(data, default=str), now),
        )


# ── Per-user legacy workout state ─────────────────────────────────────────────

def load_legacy(user_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT data FROM player_legacy WHERE user_id = ?", (user_id,)
        ).fetchone()
        return json.loads(row["data"]) if row else None


def save_legacy(user_id: int, data: dict) -> None:
    now = dt.datetime.utcnow().isoformat()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO player_legacy (user_id, data, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                data       = excluded.data,
                updated_at = excluded.updated_at
            """,
            (user_id, json.dumps(data, default=str), now),
        )
