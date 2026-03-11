"""
SQLite persistence layer for Olympus Training Log.

All state is stored as JSON blobs in a single key-value table so the
existing in-memory logic (PlayerState, core.py dicts) is untouched.

DB_PATH env-var lets Railway / Render point at a mounted volume:
    DB_PATH=/data/olympus.db
"""
import sqlite3, json, os, datetime as dt
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", "olympus.db"))

_DDL = """
CREATE TABLE IF NOT EXISTS kv_store (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute(_DDL)
    conn.commit()
    return conn


# ── Public API ────────────────────────────────────────────────────────────────

def load(key: str) -> dict | None:
    """Return the stored dict for *key*, or None if it doesn't exist."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT value FROM kv_store WHERE key = ?", (key,)
        ).fetchone()
        return json.loads(row[0]) if row else None


def save(key: str, data: dict) -> None:
    """Upsert *data* (serialised as JSON) under *key*."""
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO kv_store (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value      = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, json.dumps(data, default=str), dt.datetime.utcnow().isoformat()),
        )


def migrate_from_file(key: str, file_path: Path) -> bool:
    """
    One-time migration: if *file_path* exists and *key* is not yet in SQLite,
    copy the file contents into SQLite then rename the file to *.bak*.
    Returns True if migration happened.
    """
    if not file_path.exists():
        return False
    if load(key) is not None:
        return False  # already migrated
    try:
        data = json.loads(file_path.read_text())
        save(key, data)
        file_path.rename(file_path.with_suffix(".json.bak"))
        return True
    except Exception:
        return False
