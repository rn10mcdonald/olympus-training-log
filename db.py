"""
SQLite / PostgreSQL persistence for Olympus Training Log — multi-user edition.

Uses SQLAlchemy for both dialects.  Connection pooling with pool_pre_ping and
pool_recycle prevents stale-connection crashes after Render/Neon sleep cycles.

Env vars:
  DATABASE_URL   Full PostgreSQL connection string.  Required for production.
                 When unset, falls back to local SQLite for development only.
  DB_PATH        SQLite file path (default: olympus.db).
                 Ignored when DATABASE_URL is set.

Persistent game data stored in the database (no global vars, no local files):
  users           — account credentials
  player_estate   — full estate state: laurels, drachmae, blessings, buildings,
                    inventory, sanctuary, army, relics, trophies, titles (JSON)
  player_legacy   — legacy tracker state: microcycle progress, program tracks,
                    journey miles, week_log, badges (JSON)
  workouts        — individual workout rows for history / edit / delete
"""
import json, os, datetime as dt, logging
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

import sqlalchemy as sa
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker, Session

log = logging.getLogger(__name__)

# ── Engine ────────────────────────────────────────────────────────────────────

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

if _DATABASE_URL:
    engine = create_engine(
        _DATABASE_URL,
        pool_pre_ping=True,   # validate connection before checkout from pool
        pool_recycle=300,     # recycle connections every 5 min (Render sleeps)
        pool_size=5,
        max_overflow=10,
    )
    _IS_PG = True
    log.info("Database: PostgreSQL (DATABASE_URL is set)")
else:
    _DB_PATH = Path(os.environ.get("DB_PATH", "olympus.db"))
    engine = create_engine(
        f"sqlite:///{_DB_PATH}",
        connect_args={"check_same_thread": False},
    )
    _IS_PG = False
    log.warning(
        "DATABASE_URL is not set — using SQLite at '%s'.  "
        "All game data (users, workouts, laurels, blessings, estate, microcycle "
        "progress, etc.) will be stored locally and lost if the container restarts.  "
        "Set DATABASE_URL to a PostgreSQL connection string for production.",
        _DB_PATH,
    )

# ── Session factory ───────────────────────────────────────────────────────────

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency — yields a database session scoped to the HTTP request.
    The session is always closed when the request completes.

    Usage in route handlers::

        from sqlalchemy.orm import Session
        from fastapi import Depends
        import db

        @app.post("/some-route")
        def some_route(sess: Session = Depends(db.get_db)):
            row = sess.execute(text("SELECT ..."), {...}).fetchone()
            sess.commit()
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def _db():
    """
    Internal context manager used by all db helper functions.
    Automatically commits on success; rolls back and re-raises on any exception.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


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

sa.Table("workout_sessions", _meta,
    sa.Column("id",              sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("user_id",         sa.Integer, sa.ForeignKey("users.id"), nullable=False),
    sa.Column("date",            sa.Text,    nullable=False),
    sa.Column("drachmae_earned", sa.Float,   server_default=sa.text("0")),
    sa.Column("created_at",      sa.Text,    nullable=False),
)

# Create all tables on startup — IF NOT EXISTS semantics, safe to run every boot
_meta.create_all(engine)
log.info("Database tables verified / created.")

# ── Schema migrations (add columns that may not exist in older installations) ──

def _run_migrations() -> None:
    """Add columns / tables introduced after the initial schema."""
    cols_to_add = [
        ("workouts", "session_id", "INTEGER"),
    ]
    with _db() as sess:
        for table, col, col_type in cols_to_add:
            try:
                if _IS_PG:
                    sess.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}"
                    ))
                else:
                    # SQLite: no IF NOT EXISTS on ALTER TABLE ADD COLUMN — catch duplicate error
                    sess.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
            except Exception:
                pass  # column already exists

_run_migrations()

# ── INSERT helper (dialect-aware RETURNING) ───────────────────────────────────

def _insert(sess: Session, sql: str, params: dict) -> int:
    """Execute an INSERT and return the new row's primary-key id."""
    if _IS_PG:
        result = sess.execute(text(sql + " RETURNING id"), params)
        return result.scalar()
    result = sess.execute(text(sql), params)
    return result.lastrowid


# ── User management ───────────────────────────────────────────────────────────

def create_user(username: str, password_hash: str) -> int:
    """Insert a new user; return their id.  Raises ValueError on duplicate username."""
    now = dt.datetime.utcnow().isoformat()
    try:
        with _db() as sess:
            return _insert(
                sess,
                "INSERT INTO users (username, password_hash, created_at) "
                "VALUES (:username, :password_hash, :created_at)",
                {"username": username, "password_hash": password_hash, "created_at": now},
            )
    except sa.exc.IntegrityError:
        raise ValueError("Username already taken")


def get_user_by_username(username: str) -> dict | None:
    with _db() as sess:
        row = sess.execute(
            text("SELECT * FROM users WHERE LOWER(username) = LOWER(:username)"),
            {"username": username},
        ).fetchone()
        return dict(row._mapping) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with _db() as sess:
        row = sess.execute(
            text("SELECT * FROM users WHERE id = :id"),
            {"id": user_id},
        ).fetchone()
        return dict(row._mapping) if row else None


# ── Per-user estate state ─────────────────────────────────────────────────────
#
# The full PlayerState — laurels, drachmae, active_blessings, processing_buildings,
# sanctuary creatures, army units, relics, trophies, titles, farm grid, resource
# inventory (grain, olives, wine, bread, olive_oil, mead, honey, herbs, …) — is
# serialised as a single JSON blob.  Nothing is cached in memory; every request
# loads fresh from the database and saves back after mutation.

def load_estate(user_id: int) -> dict | None:
    with _db() as sess:
        row = sess.execute(
            text("SELECT data FROM player_estate WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()
        return json.loads(row[0]) if row else None


def save_estate(user_id: int, data: dict) -> None:
    now = dt.datetime.utcnow().isoformat()
    with _db() as sess:
        sess.execute(text("""
            INSERT INTO player_estate (user_id, data, updated_at) VALUES (:uid, :data, :now)
            ON CONFLICT(user_id) DO UPDATE SET
                data       = excluded.data,
                updated_at = excluded.updated_at
        """), {"uid": user_id, "data": json.dumps(data, default=str), "now": now})


# ── Per-user legacy workout state ─────────────────────────────────────────────
#
# Legacy state — microcycle progress, active program track, session history,
# total journey miles, weekly activity log, badges — stored as JSON blob.
# Never in memory or in local files.

def load_legacy(user_id: int) -> dict | None:
    with _db() as sess:
        row = sess.execute(
            text("SELECT data FROM player_legacy WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()
        return json.loads(row[0]) if row else None


def save_legacy(user_id: int, data: dict) -> None:
    now = dt.datetime.utcnow().isoformat()
    with _db() as sess:
        sess.execute(text("""
            INSERT INTO player_legacy (user_id, data, updated_at) VALUES (:uid, :data, :now)
            ON CONFLICT(user_id) DO UPDATE SET
                data       = excluded.data,
                updated_at = excluded.updated_at
        """), {"uid": user_id, "data": json.dumps(data, default=str), "now": now})



# ── Workouts table — structured rows for history / edit / delete ──────────────

def create_session(user_id: int, date: str, drachmae_earned: float = 0.0) -> int:
    """Create a workout_session record and return its id."""
    now = dt.datetime.utcnow().isoformat()
    with _db() as sess:
        return _insert(
            sess,
            "INSERT INTO workout_sessions (user_id, date, drachmae_earned, created_at) "
            "VALUES (:user_id, :date, :drachmae_earned, :created_at)",
            {"user_id": user_id, "date": date,
             "drachmae_earned": drachmae_earned, "created_at": now},
        )


def get_sessions(user_id: int, limit: int = 50) -> list:
    """Return recent workout sessions with their exercises, newest first."""
    with _db() as sess:
        session_rows = sess.execute(
            text("SELECT * FROM workout_sessions WHERE user_id = :uid "
                 "ORDER BY date DESC, id DESC LIMIT :limit"),
            {"uid": user_id, "limit": limit},
        ).fetchall()
        sessions = []
        for sr in session_rows:
            sd = dict(sr._mapping)
            exercise_rows = sess.execute(
                text("SELECT * FROM workouts WHERE session_id = :sid ORDER BY id ASC"),
                {"sid": sd["id"]},
            ).fetchall()
            sd["exercises"] = [dict(r._mapping) for r in exercise_rows]
            sessions.append(sd)
        return sessions

def insert_workout(user_id: int, date: str, type: str,
                   drachmae_earned: float = 0.0,
                   session_id: int | None = None, **kwargs) -> int:
    """Insert a workout row and return its id."""
    now = dt.datetime.utcnow().isoformat()
    params: dict = {
        "user_id":         user_id,
        "date":            date,
        "type":            type,
        "drachmae_earned": drachmae_earned,
        "created_at":      now,
    }
    if session_id is not None:
        params["session_id"] = session_id
    for col in ("movement", "weight_kg", "sets", "reps",
                "distance_miles", "duration_min", "weight_lbs", "notes"):
        if col in kwargs and kwargs[col] is not None:
            params[col] = kwargs[col]
    cols         = ", ".join(params.keys())
    placeholders = ", ".join(f":{k}" for k in params.keys())
    with _db() as sess:
        return _insert(sess, f"INSERT INTO workouts ({cols}) VALUES ({placeholders})", params)



def get_movement_history(user_id: int, movement: str) -> dict | None:
    """Return the most recent sets/reps/weight_kg for a given movement slug."""
    with _db() as sess:
        row = sess.execute(
            text(
                "SELECT sets, reps, weight_kg FROM workouts "
                "WHERE user_id = :uid AND movement = :mvt "
                "  AND sets IS NOT NULL AND reps IS NOT NULL "
                "ORDER BY date DESC, id DESC LIMIT 1"
            ),
            {"uid": user_id, "mvt": movement},
        ).fetchone()
        return dict(row._mapping) if row else None


def get_workouts(user_id: int, limit: int = 200) -> list:
    """Return workouts for a user, newest first."""
    with _db() as sess:
        rows = sess.execute(
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
    # Prefix WHERE-clause params to avoid name collisions with SET columns
    params = {**updates, "_wid": workout_id, "_uid": user_id}
    with _db() as sess:
        result = sess.execute(
            text(f"UPDATE workouts SET {set_clause} WHERE id = :_wid AND user_id = :_uid"),
            params,
        )
        return result.rowcount > 0


def delete_workout(workout_id: int, user_id: int) -> dict | None:
    """Delete a workout; return its row data (for drachmae adjustment) or None."""
    with _db() as sess:
        row = sess.execute(
            text("SELECT * FROM workouts WHERE id = :wid AND user_id = :uid"),
            {"wid": workout_id, "uid": user_id},
        ).fetchone()
        if not row:
            return None
        sess.execute(
            text("DELETE FROM workouts WHERE id = :wid AND user_id = :uid"),
            {"wid": workout_id, "uid": user_id},
        )
        return dict(row._mapping)
