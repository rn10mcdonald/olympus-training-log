"""
SQLite / PostgreSQL persistence for Olympus Training Log — multi-user edition.

Uses SQLAlchemy for both dialects so the same code runs locally (SQLite)
and in production on Neon / Render Postgres.

Env vars:
  DATABASE_URL   Full PostgreSQL connection string.  Falls back to SQLite when unset.
  DB_PATH        SQLite file path (default: olympus.db).  Ignored when DATABASE_URL is set.
"""
import json, os, datetime as dt
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import create_engine, text, MetaData

# ── Engine ────────────────────────────────────────────────────────────────────

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

if _DATABASE_URL:
    # PostgreSQL (Neon, Supabase, Render Postgres, …)
    engine = create_engine(
        _DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    _IS_PG = True
else:
    # Local SQLite fallback
    _DB_PATH = Path(os.environ.get("DB_PATH", "olympus.db"))
    engine = create_engine(
        f"sqlite:///{_DB_PATH}",
        connect_args={"check_same_thread": False},
    )
    _IS_PG = False

# ── Schema (created on every startup — safe / idempotent) ────────────────────

_meta = MetaData()

sa.Table("users", _meta,
    sa.Column("id",            sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("username",      sa.Text,    nullable=False, unique=True),
    sa.Column("password_hash", sa.Text,    nullable=False),
    sa.Column("created_at",    sa.Text,    nullable=False),
)

sa.Table("player_estate", _meta,
    sa.Column("user_id",    sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
    sa.Column("data",       sa.Text,    nullable=False),
    sa.Column("updated_at", sa.Text,    nullable=False),
)

sa.Table("player_legacy", _meta,
    sa.Column("user_id",    sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
    sa.Column("data",       sa.Text,    nullable=False),
    sa.Column("updated_at", sa.Text,    nullable=False),
)

sa.Table("workouts", _meta,
    sa.Column("id",              sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("user_id",         sa.Integer, sa.ForeignKey("users.id"), nullable=False),
    sa.Column("date",            sa.Text,    nullable=False),
    sa.Column("type",            sa.Text,    nullable=False),
    sa.Column("movement",        sa.Text),
    sa.Column("weight_kg",       sa.Float),
    sa.Column("sets",            sa.Integer),
    sa.Column("reps",            sa.Integer),
    sa.Column("distance_miles",  sa.Float),
    sa.Column("duration_min",    sa.Float),
    sa.Column("weight_lbs",      sa.Float),
    sa.Column("drachmae_earned", sa.Float,   server_default=sa.text("0")),
    sa.Column("notes",           sa.Text),
    sa.Column("created_at",      sa.Text,    nullable=False),
)

_meta.create_all(engine)

# ── Internal: INSERT returning new id (dialect-aware) ────────────────────────

def _insert(conn, sql: str, params: dict) -> int:
    """Execute an INSERT and return the new row's primary key id."""
    if _IS_PG:
        result = conn.execute(text(sql + " RETURNING id"), params)
        return result.scalar()
    result = conn.execute(text(sql), params)
    return result.lastrowid


# ── User management ───────────────────────────────────────────────────────────

def create_user(username: str, password_hash: str) -> int:
    """Insert a new user and return their id.  Raises ValueError on duplicate username."""
    now = dt.datetime.utcnow().isoformat()
    try:
        with engine.begin() as conn:
            return _insert(
                conn,
                "INSERT INTO users (username, password_hash, created_at) "
                "VALUES (:username, :password_hash, :created_at)",
                {"username": username, "password_hash": password_hash, "created_at": now},
            )
    except sa.exc.IntegrityError:
        raise ValueError("Username already taken")


def get_user_by_username(username: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM users WHERE LOWER(username) = LOWER(:username)"),
            {"username": username},
        ).fetchone()
        return dict(row._mapping) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM users WHERE id = :id"),
            {"id": user_id},
        ).fetchone()
        return dict(row._mapping) if row else None


# ── Per-user estate state (Laurel of Olympus RPG) ────────────────────────────

def load_estate(user_id: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT data FROM player_estate WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()
        return json.loads(row[0]) if row else None


def save_estate(user_id: int, data: dict) -> None:
    now = dt.datetime.utcnow().isoformat()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO player_estate (user_id, data, updated_at) VALUES (:uid, :data, :now)
            ON CONFLICT(user_id) DO UPDATE SET
                data       = excluded.data,
                updated_at = excluded.updated_at
        """), {"uid": user_id, "data": json.dumps(data, default=str), "now": now})


# ── Per-user legacy workout state ─────────────────────────────────────────────

def load_legacy(user_id: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT data FROM player_legacy WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()
        return json.loads(row[0]) if row else None


def save_legacy(user_id: int, data: dict) -> None:
    now = dt.datetime.utcnow().isoformat()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO player_legacy (user_id, data, updated_at) VALUES (:uid, :data, :now)
            ON CONFLICT(user_id) DO UPDATE SET
                data       = excluded.data,
                updated_at = excluded.updated_at
        """), {"uid": user_id, "data": json.dumps(data, default=str), "now": now})


# ── Workouts table (structured per-workout rows) ──────────────────────────────

def insert_workout(user_id: int, date: str, type: str,
                   drachmae_earned: float = 0.0, **kwargs) -> int:
    """Insert a workout row and return its id."""
    now = dt.datetime.utcnow().isoformat()
    params: dict = {
        "user_id":         user_id,
        "date":            date,
        "type":            type,
        "drachmae_earned": drachmae_earned,
        "created_at":      now,
    }
    for col in ("movement", "weight_kg", "sets", "reps",
                "distance_miles", "duration_min", "weight_lbs", "notes"):
        if col in kwargs and kwargs[col] is not None:
            params[col] = kwargs[col]
    cols         = ", ".join(params.keys())
    placeholders = ", ".join(f":{k}" for k in params.keys())
    with engine.begin() as conn:
        return _insert(conn, f"INSERT INTO workouts ({cols}) VALUES ({placeholders})", params)


def get_workouts(user_id: int, limit: int = 200) -> list:
    """Return workouts for a user, newest first."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM workouts WHERE user_id = :uid "
                 "ORDER BY date DESC, id DESC LIMIT :limit"),
            {"uid": user_id, "limit": limit},
        ).fetchall()
        return [dict(r._mapping) for r in rows]


def update_workout(workout_id: int, user_id: int, **kwargs) -> bool:
    """Update allowed fields of a workout.  Returns True if a row was changed."""
    allowed = {"movement", "weight_kg", "sets", "reps",
               "distance_miles", "duration_min", "weight_lbs",
               "drachmae_earned", "notes"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    # Use prefixed keys for WHERE clause params to avoid name collision
    params = {**updates, "_wid": workout_id, "_uid": user_id}
    with engine.begin() as conn:
        result = conn.execute(
            text(f"UPDATE workouts SET {set_clause} WHERE id = :_wid AND user_id = :_uid"),
            params,
        )
        return result.rowcount > 0


def delete_workout(workout_id: int, user_id: int) -> dict | None:
    """Delete a workout and return its data (for drachmae adjustment), or None."""
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM workouts WHERE id = :wid AND user_id = :uid"),
            {"wid": workout_id, "uid": user_id},
        ).fetchone()
        if not row:
            return None
        conn.execute(
            text("DELETE FROM workouts WHERE id = :wid AND user_id = :uid"),
            {"wid": workout_id, "uid": user_id},
        )
        return dict(row._mapping)
