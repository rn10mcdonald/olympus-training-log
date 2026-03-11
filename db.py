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
    """
    CREATE TABLE IF NOT EXISTS workouts (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL REFERENCES users(id),
        date            TEXT NOT NULL,
        type            TEXT NOT NULL,
        movement        TEXT,
        weight_kg       REAL,
        sets            INTEGER,
        reps            INTEGER,
        distance_miles  REAL,
        duration_min    REAL,
        weight_lbs      REAL,
        drachmae_earned REAL DEFAULT 0,
        notes           TEXT,
        created_at      TEXT NOT NULL
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


# ── Workouts table (structured per-workout rows) ─────────────────────────────

def insert_workout(user_id: int, date: str, type: str,
                   drachmae_earned: float = 0.0, **kwargs) -> int:
    """Insert a workout row and return its id."""
    now = dt.datetime.utcnow().isoformat()
    cols = ["user_id", "date", "type", "drachmae_earned", "created_at"]
    vals = [user_id, date, type, drachmae_earned, now]
    for col in ("movement", "weight_kg", "sets", "reps",
                "distance_miles", "duration_min", "weight_lbs", "notes"):
        if col in kwargs:
            cols.append(col)
            vals.append(kwargs[col])
    sql = (f"INSERT INTO workouts ({', '.join(cols)}) "
           f"VALUES ({', '.join('?' * len(vals))})")
    with _conn() as conn:
        cur = conn.execute(sql, vals)
        return cur.lastrowid


def get_workouts(user_id: int, limit: int = 200) -> list:
    """Return workouts for a user, newest first."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM workouts WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def update_workout(workout_id: int, user_id: int, **kwargs) -> bool:
    """Update allowed fields of a workout. Returns True if a row was changed."""
    allowed = {"movement", "weight_kg", "sets", "reps",
               "distance_miles", "duration_min", "weight_lbs",
               "drachmae_earned", "notes"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [workout_id, user_id]
    with _conn() as conn:
        cur = conn.execute(
            f"UPDATE workouts SET {set_clause} WHERE id = ? AND user_id = ?", vals
        )
        return cur.rowcount > 0


def delete_workout(workout_id: int, user_id: int) -> dict | None:
    """Delete a workout and return its data (for drachmae adjustment), or None."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM workouts WHERE id = ? AND user_id = ?",
            (workout_id, user_id),
        ).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM workouts WHERE id = ? AND user_id = ?",
                     (workout_id, user_id))
        return dict(row)
