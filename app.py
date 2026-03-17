from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json, core, datetime as dt, os, time as _time, logging, re as _re

log = logging.getLogger(__name__)

# Version string: process start-time so every new Render deploy gets a new token
_APP_VERSION = str(int(_time.time()))
import db
import auth as _auth
from laurel_of_olympus import game_state as gs
from laurel_of_olympus import workout_engine, farm_engine, event_engine
from laurel_of_olympus import oracle_engine, title_engine
from laurel_of_olympus import creature_engine, relic_engine, buff_engine
from laurel_of_olympus import army_engine, processing_engine, trophy_engine

BASE   = Path(__file__).parent
STATIC = BASE / "static"

# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="Olympus Training Log")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth dependency alias ─────────────────────────────────────────────────────
CurrentUser = Depends(_auth.get_current_user)

# ── Per-user state helpers ────────────────────────────────────────────────────

def _parse_total_reps(text: str) -> int:
    """Extract total reps from movement description strings.
    Handles: '5×5', '3×8/leg', '(1-2-3-2-1)×3', '4×20 m/side', etc.
    Returns a sensible default (20) when no pattern matches.
    """
    # Standard N×M or NxM
    m = _re.search(r'(\d+)\s*[x×]\s*(\d+)', text)
    if m:
        return int(m.group(1)) * int(m.group(2))
    # Ladder (1-2-3-2-1) × N
    ladder = _re.search(r'\(([\d\-]+)\)\s*[x×]\s*(\d+)', text)
    if ladder:
        total = sum(int(v) for v in ladder.group(1).split('-') if v.isdigit())
        return total * int(ladder.group(2))
    return 20  # fallback for bodyweight / unstructured finishers


def _session_volume_lbs(session: dict, weights_lbs: dict | None) -> float:
    """Sum volume (lbs × reps) for all movements in a microcycle session.
    Uses user-submitted weights_lbs when available, falls back to std_kg.
    """
    std_lbs = float(session.get("std_kg", 16) or 16) * 2.20462

    def _weight(key: str) -> float:
        if weights_lbs:
            v = weights_lbs.get(key)
            if v and float(v) > 0:
                return float(v)
        return std_lbs

    total = 0.0
    # Main lift
    main_text = session.get("main", "")
    if main_text:
        total += _weight("main") * _parse_total_reps(main_text)
    # Accessories
    for i, acc in enumerate(session.get("accessory") or []):
        total += _weight(f"acc_{i}") * _parse_total_reps(acc)
    # Finisher (optional weight entry)
    finisher = session.get("finisher", "")
    if finisher:
        fin_lbs = _weight("finisher")
        total += fin_lbs * _parse_total_reps(finisher)
    return round(total, 2)


def _load_estate(user_id: int) -> gs.PlayerState:
    raw = db.load_estate(user_id)
    if raw is None:
        # New user — return default state (will be saved on first mutation)
        return gs.PlayerState()
    try:
        return gs.PlayerState.from_dict(raw)
    except Exception as exc:
        # Deserialization failure: log and preserve raw data rather than silently
        # returning an empty state (which would wipe the player's estate on next save).
        log.error(
            "Failed to deserialize estate for user %d: %s — serving empty state "
            "without overwriting DB record. Raw keys: %s",
            user_id, exc, list(raw.keys()) if isinstance(raw, dict) else type(raw),
        )
        # Return empty state IN MEMORY but do NOT save it — the DB record is safe.
        state = gs.PlayerState()
        state._load_error = True  # sentinel so callers can detect degraded state
        return state


def _save_estate(user_id: int, state: gs.PlayerState) -> None:
    if getattr(state, "_load_error", False):
        log.warning("Refusing to save degraded estate state for user %d — DB record preserved.", user_id)
        return
    db.save_estate(user_id, state.to_dict())


def _load_legacy(user_id: int) -> dict:
    raw = db.load_legacy(user_id)
    if raw is None:
        raw = core.default_state()
        db.save_legacy(user_id, raw)
    raw.setdefault("total_ruck_miles",
                   sum(r.get("distance_miles", 0)
                       for r in raw.get("ruck_log", []) if isinstance(r, dict)))
    raw.setdefault("total_run_miles",
                   sum(r.get("distance_miles", 0)
                       for r in raw.get("run_log", []) if isinstance(r, dict)))
    raw.setdefault("walk_log", [])
    raw.setdefault("total_walk_miles",
                   sum(r.get("distance_miles", 0)
                       for r in raw.get("walk_log", []) if isinstance(r, dict)))
    raw.setdefault("run_log", [])
    raw.setdefault("week_log", {})
    raw.setdefault("journey_miles",
                   raw["total_ruck_miles"] + raw["total_run_miles"] + raw["total_walk_miles"])
    mc = raw.setdefault("microcycle", {})
    mc.setdefault("start_date",        str(dt.date.today()))
    mc.setdefault("badge_given",        False)
    mc.setdefault("id",                 0)
    mc.setdefault("sessions_completed", 0)
    raw["ruck_log"] = [r for r in raw.get("ruck_log", []) if isinstance(r, dict)]
    raw["run_log"]  = [r for r in raw.get("run_log",  []) if isinstance(r, dict)]
    raw.setdefault("custom_tracks", [])
    return raw


def _save_legacy(user_id: int, d: dict) -> None:
    db.save_legacy(user_id, d)


# ── Static serving ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC / "index.html")

@app.get("/service-worker.js")
def service_worker_root():
    """Serve SW from root path so its scope covers '/' (not just '/static/')."""
    fp = STATIC / "service-worker.js"
    resp = FileResponse(fp, media_type="application/javascript")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp

@app.get("/static/{path:path}")
def statics(path: str):
    fp = STATIC / path
    if not fp.exists():
        raise HTTPException(404)
    resp = FileResponse(fp)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@app.get("/img/{path:path}")
def images(path: str):
    fp = BASE / path
    if not fp.exists():
        raise HTTPException(404)
    return FileResponse(fp)

# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": _APP_VERSION}

@app.get("/api/version")
def api_version():
    """Returns the server start-time as a version token.
    Clients poll this every 60 s and reload when it changes (new deploy)."""
    return {"version": _APP_VERSION}

# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.post("/register")
async def register(req: Request):
    p = await req.json()
    username = (p.get("username") or "").strip()
    password = (p.get("password") or "").strip()
    if not username or not password:
        raise HTTPException(400, "username and password are required")
    if len(username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    if len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if db.get_user_by_username(username):
        raise HTTPException(409, "Username already taken")
    try:
        user_id = db.create_user(username, _auth.hash_password(password))
    except ValueError:
        raise HTTPException(409, "Username already taken")
    token = _auth.create_token(user_id, username)
    return {"status": "ok", "token": token, "username": username}


@app.post("/login")
async def login(req: Request):
    p = await req.json()
    username = (p.get("username") or "").strip()
    password = (p.get("password") or "").strip()
    if not username or not password:
        raise HTTPException(400, "username and password are required")
    user = db.get_user_by_username(username)
    if not user or not _auth.verify_password(password, user["password_hash"]):
        raise HTTPException(401, "Invalid username or password")
    token = _auth.create_token(user["id"], user["username"])
    return {"status": "ok", "token": token, "username": user["username"]}

# ── Deployment-friendly shorthand endpoints (protected) ───────────────────────

@app.get("/player-state")
def player_state(u: dict = CurrentUser):
    uid = u["user_id"]
    return {
        "workout":  _load_legacy(uid),
        "estate":   _load_estate(uid).to_dict(),
        "username": u["username"],
    }

@app.get("/estate")
def get_estate(u: dict = CurrentUser):
    return _load_estate(u["user_id"]).to_dict()

@app.get("/creatures")
def get_creatures(u: dict = CurrentUser):
    state = _load_estate(u["user_id"])
    return {
        "sanctuary":     creature_engine.get_sanctuary_details(state),
        "capacity":      state.sanctuary_capacity,
        "all_creatures": creature_engine.get_all_creatures(),
    }

@app.post("/log-workout")
async def log_workout(req: Request, u: dict = CurrentUser):
    p = await req.json()
    return await _run_estate_workout(u["user_id"], p)

@app.post("/campaign")
async def campaign(req: Request, u: dict = CurrentUser):
    p = await req.json()
    return await _run_campaign(u["user_id"], p)

# ── Legacy workout API (protected) ────────────────────────────────────────────

@app.get("/api/state")
def get_state(u: dict = CurrentUser):
    return _load_legacy(u["user_id"])

@app.get("/api/workout/today")
def get_today(u: dict = CurrentUser):
    return core.get_today_workout(_load_legacy(u["user_id"]))

@app.get("/api/movements")
def get_movements():
    return core.get_movements()

@app.get("/api/movement_history/{movement}")
def get_movement_history(movement: str, u: dict = CurrentUser):
    """Return the last logged sets/reps/weight_kg for a given movement slug."""
    workouts = db.get_workouts(u["user_id"], limit=200)
    for w in workouts:
        if w.get("movement") == movement and w.get("sets") and w.get("reps"):
            return {
                "movement":  movement,
                "weight_kg": w.get("weight_kg"),
                "sets":      w["sets"],
                "reps":      w["reps"],
                "date":      w["date"],
            }
    return {"movement": movement, "weight_kg": None, "sets": None, "reps": None}

@app.get("/api/tracks")
def get_tracks(u: dict = CurrentUser):
    state  = _load_legacy(u["user_id"])
    tracks = {k: v["name"] for k, v in core.TEMPLATES.items()}
    for ct in state.get("custom_tracks", []):
        n = len(ct.get("sessions", []))
        tracks[f"custom_{ct['id']}"] = f"⚒ {ct['name']} ({n} sessions)"
    return tracks

@app.get("/api/tracks/{key}")
def get_track_detail(key: str):
    if key.startswith("custom_"):
        raise HTTPException(404, "Custom tracks require auth context")
    detail = core.get_track_detail(key)
    if detail is None:
        raise HTTPException(404, f"Unknown track: {key}")
    return detail

@app.post("/api/track/select")
async def select_track(req: Request, u: dict = CurrentUser):
    payload = await req.json()
    key = payload.get("key", "").strip()
    if not key.startswith("custom_") and key not in core.TEMPLATES:
        raise HTTPException(400, f"Unknown track: {key}")
    uid   = u["user_id"]
    state = _load_legacy(uid)
    if key.startswith("custom_"):
        track_id = key[7:]
        if core.get_custom_track_detail(state, track_id) is None:
            raise HTTPException(404, f"Custom track not found: {key}")
    msg = core.init_track(state, key)
    _save_legacy(uid, state)
    return {"status": "ok", "msg": msg, "state": state}

@app.post("/api/workout/recommended")
async def log_recommended(req: Request, u: dict = CurrentUser):
    weights_lbs = None
    try:
        p = await req.json()
        weights_lbs = p.get("weights_lbs")
    except Exception:
        pass
    uid   = u["user_id"]
    state = _load_legacy(uid)

    # Legacy state: journey miles, microcycle progress, weekly laurel tracking
    msg = core.log_rec(state, weights_lbs=weights_lbs)
    _save_legacy(uid, state)

    # ── Estate reward: expand session into movements, sum volume ───────────────
    estate = _load_estate(uid)
    buffs  = buff_engine.get_all_buffs(estate)

    # Look up the current session template to get movement structure
    track = state.get("track", "")
    mc    = state.get("microcycle", {})
    # sessions_completed was just incremented by core.log_rec; use idx - 1
    idx   = max(0, mc.get("sessions_completed", 1) - 1)
    session_def: dict = {}
    if track and not track.startswith("custom_") and track in core.TEMPLATES:
        sessions = core.TEMPLATES[track].get("sessions", [])
        if idx < len(sessions):
            session_def = sessions[idx]

    volume = _session_volume_lbs(session_def, weights_lbs)

    raw_evts     = workout_engine.process_workout(estate, "strength", buffs=buffs, volume=volume)
    trophy_award = None
    events       = []
    for e in raw_evts:
        if isinstance(e, dict) and e.get("type") == "trophy":
            trophy_award = e["trophy"]
            events.append(e["msg"])
        else:
            events.append(e)

    if buffs.get("blessing_hephaestus"):
        estate.active_blessings["hephaestus"] = max(
            0, estate.active_blessings.get("hephaestus", 1) - 1
        )
    oracle_evt = oracle_engine.maybe_oracle_visit(estate, chance=0.10)
    _save_estate(uid, estate)

    today  = str(dt.date.today())
    earned = estate.drachmae  # post-mutation value reflects what was added
    db.insert_workout(uid, today, "strength", round(volume * 0.035, 2),
                      notes=msg[:200] if msg else None)

    return {
        "status": "ok", "msg": msg, "state": state,
        "events": events, "trophy_award": trophy_award,
        "oracle_event": oracle_evt, "estate_state": estate.to_dict(),
    }

@app.post("/api/workout/custom")
async def log_custom(req: Request, u: dict = CurrentUser):
    payload = await req.json()
    text    = payload.get("text", "").strip()
    if not text:
        raise HTTPException(400, "Empty workout description")
    uid          = u["user_id"]
    state        = _load_legacy(uid)
    old_treasury = state.get("treasury", 0.0)
    msg          = core.log_custom(state, text)
    _save_legacy(uid, state)
    base_coins   = round(state.get("treasury", 0.0) - old_treasury, 2)

    # Credit estate drachmae, apply strength buff, consume Hephaestus blessing
    estate = _load_estate(uid)
    buffs  = buff_engine.get_all_buffs(estate)
    earned = buff_engine.apply_workout_buff(buffs, "strength", base_coins)
    if base_coins > 0:
        estate.drachmae = round(estate.drachmae + earned, 2)
    if buffs.get("blessing_hephaestus") and base_coins > 0:
        estate.active_blessings["hephaestus"] = max(
            0, estate.active_blessings.get("hephaestus", 1) - 1
        )
    _save_estate(uid, estate)

    if base_coins > 0:
        today = str(dt.date.today())
        db.insert_workout(uid, today, "custom", earned, notes=text[:200])

    return {"status": "ok", "msg": msg, "state": state}

@app.post("/api/ruck")
async def log_ruck(req: Request, u: dict = CurrentUser):
    p = await req.json()
    try:
        miles  = float(p["miles"])
        pounds = float(p.get("pounds", 0) or 0)
    except (KeyError, ValueError):
        raise HTTPException(400, "miles must be numeric")
    if miles <= 0:
        raise HTTPException(400, "miles must be positive")
    uid      = u["user_id"]
    state    = _load_legacy(uid)
    msg      = core.log_ruck(state, miles, pounds)
    _save_legacy(uid, state)
    # Also run through estate engine for laurel tracking
    estate   = _load_estate(uid)
    buffs    = buff_engine.get_all_buffs(estate)
    raw_evts = workout_engine.process_workout(estate, "rucking", buffs=buffs,
                                              miles=miles, lbs=pounds)
    trophy_award = None
    events = []
    for e in raw_evts:
        if isinstance(e, dict) and e.get("type") == "trophy":
            trophy_award = e["trophy"]
            events.append(e["msg"])
        else:
            events.append(e)
    if buffs.get("blessing_poseidon"):
        estate.active_blessings["poseidon"] = max(
            0, estate.active_blessings.get("poseidon", 1) - 1
        )
        events.append("  🌊 Blessing of Poseidon consumed.")
    _save_estate(uid, estate)
    oracle_evt = oracle_engine.maybe_oracle_visit(estate, chance=0.10)
    if oracle_evt:
        _save_estate(uid, estate)
    # Persist to workouts table
    today  = str(dt.date.today())
    earned = next((float(ev.split("+")[1].split(" ")[0]) for ev in events
                   if isinstance(ev, str) and "drachmae" in ev), 0.0)
    db.insert_workout(uid, today, "rucking", earned,
                      distance_miles=miles, weight_lbs=pounds,
                      duration_min=float(p.get("duration_min") or 0) or None)
    return {"status": "ok", "msg": msg, "state": state,
            "events": events, "trophy_award": trophy_award, "oracle_event": oracle_evt}

@app.post("/api/walk")
async def log_walk(req: Request, u: dict = CurrentUser):
    p = await req.json()
    try:
        miles = float(p["miles"])
    except (KeyError, ValueError):
        raise HTTPException(400, "miles must be numeric")
    if miles <= 0:
        raise HTTPException(400, "miles must be positive")
    uid   = u["user_id"]
    state = _load_legacy(uid)
    msg   = core.log_walk(state, miles)
    _save_legacy(uid, state)
    estate   = _load_estate(uid)
    buffs    = buff_engine.get_all_buffs(estate)
    raw_evts = workout_engine.process_workout(estate, "walking", buffs=buffs, miles=miles)
    trophy_award = None
    events = []
    for e in raw_evts:
        if isinstance(e, dict) and e.get("type") == "trophy":
            trophy_award = e["trophy"]
            events.append(e["msg"])
        else:
            events.append(e)
    _save_estate(uid, estate)
    oracle_evt = oracle_engine.maybe_oracle_visit(estate, chance=0.10)
    if oracle_evt:
        _save_estate(uid, estate)
    today  = str(dt.date.today())
    earned = next((float(ev.split("+")[1].split(" ")[0]) for ev in events
                   if isinstance(ev, str) and "drachmae" in ev), 0.0)
    db.insert_workout(uid, today, "walking", earned,
                      distance_miles=miles,
                      duration_min=float(p.get("duration_min") or 0) or None)
    return {"status": "ok", "msg": msg, "state": state,
            "events": events, "trophy_award": trophy_award, "oracle_event": oracle_evt}

@app.post("/api/run")
async def log_run(req: Request, u: dict = CurrentUser):
    p = await req.json()
    try:
        miles = float(p["miles"])
    except (KeyError, ValueError):
        raise HTTPException(400, "miles must be numeric")
    if miles <= 0:
        raise HTTPException(400, "miles must be positive")
    pace = p.get("pace_min_per_mile")
    if pace is not None:
        try:
            pace = float(pace)
        except (TypeError, ValueError):
            pace = None
    uid   = u["user_id"]
    state = _load_legacy(uid)
    msg   = core.log_run(state, miles, pace)
    _save_legacy(uid, state)
    estate   = _load_estate(uid)
    buffs    = buff_engine.get_all_buffs(estate)
    raw_evts = workout_engine.process_workout(estate, "running", buffs=buffs, miles=miles)
    trophy_award = None
    events = []
    for e in raw_evts:
        if isinstance(e, dict) and e.get("type") == "trophy":
            trophy_award = e["trophy"]
            events.append(e["msg"])
        else:
            events.append(e)
    if buffs.get("blessing_hermes"):
        estate.active_blessings["hermes"] = max(
            0, estate.active_blessings.get("hermes", 1) - 1
        )
        events.append("  🪶 Blessing of Hermes consumed.")
    _save_estate(uid, estate)
    oracle_evt = oracle_engine.maybe_oracle_visit(estate, chance=0.10)
    if oracle_evt:
        _save_estate(uid, estate)
    today  = str(dt.date.today())
    earned = next((float(ev.split("+")[1].split(" ")[0]) for ev in events
                   if isinstance(ev, str) and "drachmae" in ev), 0.0)
    db.insert_workout(uid, today, "running", earned,
                      distance_miles=miles,
                      duration_min=float(p.get("duration_min") or 0) or None)
    return {"status": "ok", "msg": msg, "state": state,
            "events": events, "trophy_award": trophy_award, "oracle_event": oracle_evt}

@app.post("/api/hike")
async def log_hike(req: Request, u: dict = CurrentUser):
    """Hike: like a ruck but counts toward walking miles."""
    p = await req.json()
    try:
        miles  = float(p["miles"])
        pounds = float(p.get("pounds", 0) or 0)
    except (KeyError, ValueError):
        raise HTTPException(400, "miles must be numeric")
    if miles <= 0:
        raise HTTPException(400, "miles must be positive")
    uid   = u["user_id"]
    state = _load_legacy(uid)
    msg   = core.log_walk(state, miles)   # counts toward walk miles
    _save_legacy(uid, state)
    estate   = _load_estate(uid)
    buffs    = buff_engine.get_all_buffs(estate)
    raw_evts = workout_engine.process_workout(estate, "rucking", buffs=buffs,
                                              miles=miles, lbs=pounds)
    trophy_award = None
    events = []
    for e in raw_evts:
        if isinstance(e, dict) and e.get("type") == "trophy":
            trophy_award = e["trophy"]
            events.append(e["msg"])
        else:
            events.append(e)
    if buffs.get("blessing_poseidon"):
        estate.active_blessings["poseidon"] = max(
            0, estate.active_blessings.get("poseidon", 1) - 1
        )
        events.append("  🌊 Blessing of Poseidon consumed.")
    _save_estate(uid, estate)
    oracle_evt = oracle_engine.maybe_oracle_visit(estate, chance=0.10)
    if oracle_evt:
        _save_estate(uid, estate)
    today  = str(dt.date.today())
    earned = next((float(ev.split("+")[1].split(" ")[0]) for ev in events
                   if isinstance(ev, str) and "drachmae" in ev), 0.0)
    db.insert_workout(uid, today, "hiking", earned,
                      distance_miles=miles, weight_lbs=pounds or None,
                      duration_min=float(p.get("duration_min") or 0) or None)
    return {"status": "ok", "msg": f"⛰️ Hike logged! {msg}", "state": state,
            "events": events, "trophy_award": trophy_award, "oracle_event": oracle_evt}

@app.post("/api/strength")
async def log_strength(req: Request, u: dict = CurrentUser):
    """Free-form strength workout logging with movement selector."""
    p = await req.json()
    movement   = (p.get("movement") or "").strip()
    weight_kg  = float(p.get("weight_kg") or 0)
    sets_n     = int(p.get("sets") or 1)
    reps_n     = int(p.get("reps") or 1)
    if not movement:
        raise HTTPException(400, "movement is required")
    if sets_n < 1 or reps_n < 1:
        raise HTTPException(400, "sets and reps must be at least 1")
    # volume in lbs for reward calculation
    volume = weight_kg * 2.20462 * sets_n * reps_n
    uid    = u["user_id"]
    estate = _load_estate(uid)
    buffs  = buff_engine.get_all_buffs(estate)
    raw_evts = workout_engine.process_workout(estate, "strength", buffs=buffs, volume=volume)
    trophy_award = None
    events = []
    for e in raw_evts:
        if isinstance(e, dict) and e.get("type") == "trophy":
            trophy_award = e["trophy"]
            events.append(e["msg"])
        else:
            events.append(e)
    if buffs.get("blessing_hephaestus"):
        estate.active_blessings["hephaestus"] = max(
            0, estate.active_blessings.get("hephaestus", 1) - 1
        )
        events.append("  🔥 Blessing of Hephaestus consumed.")
    _save_estate(uid, estate)
    oracle_evt = oracle_engine.maybe_oracle_visit(estate, chance=0.10)
    if oracle_evt:
        _save_estate(uid, estate)
    today  = str(dt.date.today())
    earned = next((float(ev.split("+")[1].split(" ")[0]) for ev in events
                   if isinstance(ev, str) and "drachmae" in ev), 0.0)
    db.insert_workout(uid, today, "strength", earned,
                      movement=movement, weight_kg=weight_kg,
                      sets=sets_n, reps=reps_n)
    move_name = next((m["name"] for m in core.get_movements() if m["slug"] == movement),
                     movement.replace("_", " ").title())
    return {
        "status": "ok",
        "msg": f"💪 {move_name} — {sets_n}×{reps_n} @ {weight_kg}kg logged! +{earned:.2f} ⚡",
        "events": events,
        "trophy_award": trophy_award,
        "oracle_event": oracle_evt,
        "estate_state": estate.to_dict(),
    }

# ── Workout history CRUD ───────────────────────────────────────────────────────

@app.get("/api/workouts")
def get_workouts_list(u: dict = CurrentUser):
    return {"workouts": db.get_workouts(u["user_id"])}


@app.get("/api/movement_history/{movement}")
def get_movement_history_api(movement: str, u: dict = CurrentUser):
    """Return the most recent sets/reps/weight_kg logged for a movement."""
    history = db.get_movement_history(u["user_id"], movement)
    return {"history": history}


@app.post("/api/session")
async def log_session(req: Request, u: dict = CurrentUser):
    """
    Log a multi-exercise session (Issue #1 custom workout builder).

    Body: {
        "exercises": [
            {"movement": str, "weight_kg": float, "sets": int, "reps": int, "notes"?: str},
            ...
        ],
        "date": "YYYY-MM-DD"   # optional, defaults to today
    }
    """
    p         = await req.json()
    exercises = p.get("exercises") or []
    date      = (p.get("date") or str(dt.date.today())).strip()

    if not exercises:
        raise HTTPException(400, "exercises list is required")
    for ex in exercises:
        if not ex.get("movement"):
            raise HTTPException(400, "Each exercise must have a movement")
        if int(ex.get("sets") or 0) < 1 or int(ex.get("reps") or 0) < 1:
            raise HTTPException(400, "Each exercise must have sets and reps ≥ 1")

    uid    = u["user_id"]
    estate = _load_estate(uid)
    buffs  = buff_engine.get_all_buffs(estate)

    # Compute total volume across all exercises (in lbs)
    total_volume = 0.0
    for ex in exercises:
        wkg  = float(ex.get("weight_kg") or 0)
        sets = int(ex.get("sets") or 1)
        reps = int(ex.get("reps") or 1)
        total_volume += wkg * 2.20462 * sets * reps

    raw_evts = workout_engine.process_workout(
        estate, "strength", buffs=buffs, volume=total_volume
    )
    trophy_award = None
    events = []
    for e in raw_evts:
        if isinstance(e, dict) and e.get("type") == "trophy":
            trophy_award = e["trophy"]
            events.append(e["msg"])
        else:
            events.append(e)
    _save_estate(uid, estate)

    oracle_evt = oracle_engine.maybe_oracle_visit(estate, chance=0.10)
    if oracle_evt:
        _save_estate(uid, estate)

    # Persist: create session row, then one workout row per exercise
    total_earned = next(
        (float(ev.split("+")[1].split(" ")[0]) for ev in events
         if isinstance(ev, str) and "drachmae" in ev),
        0.0,
    )
    session_id = db.create_session(uid, date, total_earned)
    workout_ids = []
    for ex in exercises:
        wkg  = float(ex.get("weight_kg") or 0)
        sets = int(ex.get("sets") or 1)
        reps = int(ex.get("reps") or 1)
        wid  = db.insert_workout(
            uid, date, "strength",
            drachmae_earned=0.0,   # total on session; each exercise row gets 0
            session_id=session_id,
            movement=ex["movement"],
            weight_kg=wkg if wkg > 0 else None,
            sets=sets, reps=reps,
            notes=ex.get("notes") or None,
        )
        workout_ids.append(wid)
    # Assign full drachmae to the first exercise row for history display
    if workout_ids and total_earned > 0:
        db.update_workout(workout_ids[0], uid, drachmae_earned=total_earned)

    move_names = {m["slug"]: m["name"] for m in core.get_movements()}
    parts = []
    for ex in exercises:
        name = move_names.get(ex["movement"], ex["movement"].replace("_", " ").title())
        parts.append(f"{name} {ex['sets']}×{ex['reps']} @ {ex.get('weight_kg', 0)}kg")

    return {
        "status":       "ok",
        "msg":          "💪 Session logged: " + " | ".join(parts),
        "events":       events,
        "session_id":   session_id,
        "trophy_award": trophy_award,
        "oracle_event": oracle_evt,
        "estate_state": estate.to_dict(),
    }

@app.put("/api/workout/{workout_id}")
async def edit_workout(workout_id: int, req: Request, u: dict = CurrentUser):
    p   = await req.json()
    uid = u["user_id"]
    # Get old drachmae to compute diff
    old_rows = db.get_workouts(uid, limit=500)
    old = next((r for r in old_rows if r["id"] == workout_id), None)
    if not old:
        raise HTTPException(404, "Workout not found")
    update_fields = {}
    for field in ("movement", "weight_kg", "sets", "reps",
                  "distance_miles", "duration_min", "weight_lbs", "notes"):
        if field in p:
            update_fields[field] = p[field]
    new_drachmae = p.get("drachmae_earned")
    if new_drachmae is not None:
        update_fields["drachmae_earned"] = float(new_drachmae)
    ok = db.update_workout(workout_id, uid, **update_fields)
    if not ok:
        raise HTTPException(404, "Workout not found or no changes")
    # Adjust estate drachmae if changed
    if new_drachmae is not None:
        diff = float(new_drachmae) - float(old["drachmae_earned"] or 0)
        if abs(diff) > 0.001:
            estate = _load_estate(uid)
            estate.drachmae = round(estate.drachmae + diff, 2)
            _save_estate(uid, estate)
    return {"status": "ok", "workouts": db.get_workouts(uid)}

@app.delete("/api/workout/{workout_id}")
def del_workout(workout_id: int, u: dict = CurrentUser):
    uid     = u["user_id"]
    deleted = db.delete_workout(workout_id, uid)
    if not deleted:
        raise HTTPException(404, "Workout not found")
    # Subtract drachmae from estate
    earned = float(deleted.get("drachmae_earned") or 0)
    if earned > 0:
        estate = _load_estate(uid)
        estate.drachmae = max(0.0, round(estate.drachmae - earned, 2))
        _save_estate(uid, estate)
    return {"status": "ok", "workouts": db.get_workouts(uid)}

@app.post("/api/tracks/custom")
async def save_custom_track(req: Request, u: dict = CurrentUser):
    p        = await req.json()
    name     = (p.get("name") or "").strip()
    sessions = p.get("sessions", [])
    if not name:
        raise HTTPException(400, "Track name is required.")
    if not sessions:
        raise HTTPException(400, "At least one session is required.")
    uid   = u["user_id"]
    state = _load_legacy(uid)
    try:
        track = core.save_custom_track(state, name, sessions)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _save_legacy(uid, state)
    return {"status": "ok", "track": track, "state": state}

@app.delete("/api/tracks/custom/{track_id}")
def delete_custom_track(track_id: str, u: dict = CurrentUser):
    uid   = u["user_id"]
    state = _load_legacy(uid)
    found = core.delete_custom_track(state, track_id)
    if not found:
        raise HTTPException(404, f"Custom track not found: {track_id}")
    _save_legacy(uid, state)
    return {"status": "ok", "state": state}

# ── Estate (Laurel of Olympus RPG) — all endpoints protected ─────────────────

@app.get("/api/estate/state")
def get_estate_state(u: dict = CurrentUser):
    return _load_estate(u["user_id"]).to_dict()


async def _run_estate_workout(user_id: int, p: dict) -> dict:
    workout_type = p.get("workout_type", "strength")
    kwargs = {k: v for k, v in p.items() if k != "workout_type"}
    if workout_type == "strength" and "volume" not in kwargs:
        kwargs["volume"] = 5000.0
    elif workout_type in ("walking", "running", "rucking") and "miles" not in kwargs:
        kwargs["miles"] = 2.0

    state = _load_estate(user_id)
    buffs = buff_engine.get_all_buffs(state)

    raw_events = workout_engine.process_workout(state, workout_type, buffs=buffs, **kwargs)

    trophy_award = None
    events = []
    for e in raw_events:
        if isinstance(e, dict) and e.get("type") == "trophy":
            trophy_award = e["trophy"]
            events.append(e["msg"])
        else:
            events.append(e)

    if buffs.get("blessing_hermes") and workout_type == "running":
        state.active_blessings["hermes"] = max(0, state.active_blessings.get("hermes", 1) - 1)
        events.append("  🪶 Blessing of Hermes consumed.")

    farm_events = farm_engine.produce_farms(state, buffs=buffs)
    events.extend(farm_events)

    if buffs.get("blessing_demeter") and farm_events and "No farms" not in farm_events[0]:
        state.active_blessings["demeter"] = max(0, state.active_blessings.get("demeter", 1) - 1)
        events.append("  🌾 Blessing of Demeter consumed.")

    newly_unlocked = title_engine.check_and_unlock_titles(state)
    for tid in newly_unlocked:
        events.append(f"  🏅 Title unlocked: {tid.replace('_', ' ').title()}")

    encounter_chance = buff_engine.effective_event_chance(buffs, 0.05)
    encounter_chance = min(1.0, encounter_chance + buffs.get("creature_chance", 0.0))
    creature_encounter = creature_engine.maybe_creature_encounter(
        workout_type, chance=encounter_chance
    )

    narrative_event = oracle_engine.maybe_kassandra_break(state, chance=0.001)
    if narrative_event:
        if "favorite_of_kassandra" not in state.titles_unlocked:
            state.titles_unlocked.append("favorite_of_kassandra")
            state.active_titles["legendary"] = "favorite_of_kassandra"
            events.append("  🌟 Title unlocked: Favorite of Kassandra")
    else:
        if army_engine.check_army_unlock_hint(state):
            narrative_event = {
                "type":  "oracle", "title": "Kassandra Stirs", "icon": "🏛️",
                "lines": [
                    "The Oracle sets down her scroll.",
                    "She regards the estate — the fields, the sanctuary, the growing stores.",
                    "'You have built something here. It would be a shame to lose it.'",
                    "'Perhaps... it is time to consider defending it.'",
                    "She says nothing more. But the thought lingers.",
                ],
            }
        if narrative_event is None:
            narrative_event = oracle_engine.maybe_oracle_visit(state, chance=0.10)
        if narrative_event is None:
            flavour_chance = buff_engine.effective_event_chance(buffs, 0.20)
            narrative_event = event_engine.maybe_trigger_event(
                state.to_dict(), chance=flavour_chance
            )

    relic_find = None
    import random as _random
    relic_chance = buff_engine.effective_event_chance(buffs, 0.03)
    relic_chance = min(1.0, relic_chance + buffs.get("relic_chance", 0.0))
    if _random.random() < relic_chance:
        candidate = relic_engine.roll_relic_reward()
        if candidate:
            ok_r, _ = relic_engine.add_relic(state, candidate["id"])
            relic_find = candidate if ok_r else {**candidate, "not_added": True}

    _save_estate(user_id, state)
    return {
        "status":             "ok",
        "events":             events,
        "state":              state.to_dict(),
        "event":              narrative_event,
        "creature_encounter": creature_encounter,
        "relic_find":         relic_find,
        "trophy_award":       trophy_award,
    }


@app.post("/api/estate/simulate-workout")
async def estate_simulate_workout(req: Request, u: dict = CurrentUser):
    return await _run_estate_workout(u["user_id"], await req.json())


@app.get("/api/estate/prophecy")
def get_prophecy_scroll(u: dict = CurrentUser):
    uid   = u["user_id"]
    state = _load_estate(uid)
    scroll = title_engine.get_prophecy_scroll(state)
    _save_estate(uid, state)
    return scroll


@app.get("/api/estate/sanctuary")
def get_sanctuary(u: dict = CurrentUser):
    state = _load_estate(u["user_id"])
    return {
        "sanctuary":     creature_engine.get_sanctuary_details(state),
        "capacity":      state.sanctuary_capacity,
        "sanctuary_ids": state.sanctuary,
        "all_creatures": creature_engine.get_all_creatures(),
        "buffs":         creature_engine.get_sanctuary_buffs(state),
    }

@app.post("/api/estate/creature/recruit")
async def recruit_creature(req: Request, u: dict = CurrentUser):
    p = await req.json()
    creature_id = p.get("creature_id", "").strip()
    if not creature_id:
        raise HTTPException(400, "creature_id is required")
    uid   = u["user_id"]
    state = _load_estate(uid)
    ok, msg = creature_engine.recruit_creature(state, creature_id)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(uid, state)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}

@app.post("/api/estate/creature/release")
async def release_creature(req: Request, u: dict = CurrentUser):
    p = await req.json()
    creature_id = p.get("creature_id", "").strip()
    if not creature_id:
        raise HTTPException(400, "creature_id is required")
    uid   = u["user_id"]
    state = _load_estate(uid)
    ok, msg, reward = creature_engine.release_creature(state, creature_id)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(uid, state)
    return {"status": "ok", "msg": msg, "reward": reward, "state": state.to_dict()}


@app.get("/api/estate/relics")
def get_relics(u: dict = CurrentUser):
    state = _load_estate(u["user_id"])
    return {
        "inventory":  relic_engine.get_inventory_details(state),
        "capacity":   state.relic_capacity,
        "relic_ids":  state.relics,
        "all_relics": relic_engine.get_all_relics(),
        "buffs":      relic_engine.get_relic_buffs(state),
    }

@app.post("/api/estate/relic/add")
async def add_relic(req: Request, u: dict = CurrentUser):
    p = await req.json()
    relic_id = p.get("relic_id", "").strip()
    if not relic_id:
        raise HTTPException(400, "relic_id is required")
    uid   = u["user_id"]
    state = _load_estate(uid)
    ok, msg = relic_engine.add_relic(state, relic_id)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(uid, state)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}

@app.post("/api/estate/relic/remove")
async def remove_relic(req: Request, u: dict = CurrentUser):
    p = await req.json()
    relic_id = p.get("relic_id", "").strip()
    if not relic_id:
        raise HTTPException(400, "relic_id is required")
    uid   = u["user_id"]
    state = _load_estate(uid)
    ok, msg = relic_engine.remove_relic(state, relic_id)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(uid, state)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}


@app.get("/api/estate/trophies")
def get_trophies(u: dict = CurrentUser):
    state = _load_estate(u["user_id"])
    return {
        "trophies":     trophy_engine.get_trophy_inventory(state),
        "buff_summary": trophy_engine.get_buff_summary(state),
        "total":        len(getattr(state, "trophies", None) or []),
    }


@app.get("/api/estate/army")
def get_army(u: dict = CurrentUser):
    state = _load_estate(u["user_id"])
    buffs = buff_engine.get_all_buffs(state)
    return {
        "barracks_built": state.barracks_built,
        "barracks_cost":  army_engine.BARRACKS_COST,
        "army":           army_engine.get_army_details(state),
        "army_ids":       state.army,
        "army_limit":     state.army_limit,
        "army_strength":  army_engine.get_army_strength(state, buffs),
        "campaigns_won":  state.campaigns_won,
        "all_units":      army_engine.get_all_units(),
        "all_regions":    army_engine.get_all_regions(),
        "buffs":          buffs,
    }

@app.post("/api/estate/barracks/build")
async def build_barracks(req: Request, u: dict = CurrentUser):
    uid   = u["user_id"]
    state = _load_estate(uid)
    ok, msg = army_engine.build_barracks(state)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(uid, state)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}

@app.post("/api/estate/army/recruit")
async def recruit_unit(req: Request, u: dict = CurrentUser):
    p = await req.json()
    unit_id = p.get("unit_id", "").strip()
    if not unit_id:
        raise HTTPException(400, "unit_id is required")
    uid   = u["user_id"]
    state = _load_estate(uid)
    ok, msg = army_engine.recruit_unit(state, unit_id)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(uid, state)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}

@app.post("/api/estate/army/disband")
async def disband_unit(req: Request, u: dict = CurrentUser):
    p = await req.json()
    unit_id = p.get("unit_id", "").strip()
    if not unit_id:
        raise HTTPException(400, "unit_id is required")
    uid   = u["user_id"]
    state = _load_estate(uid)
    ok, msg = army_engine.disband_unit(state, unit_id)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(uid, state)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}


async def _run_campaign(user_id: int, p: dict) -> dict:
    region_id = p.get("region_id", "").strip()
    if not region_id:
        raise HTTPException(400, "region_id is required")
    state = _load_estate(user_id)
    buffs = buff_engine.get_all_buffs(state)
    result = army_engine.launch_campaign(state, region_id, buffs=buffs)
    if "error" in result:
        raise HTTPException(400, result["error"])
    if buffs.get("blessing_ares"):
        state.active_blessings["ares"] = max(0, state.active_blessings.get("ares", 1) - 1)
    if result.get("relic_reward"):
        ok_relic, _ = relic_engine.add_relic(state, result["relic_reward"]["id"])
        if not ok_relic:
            result["relic_reward"]["not_added"] = True
    import random as _random
    if result.get("victory") and _random.random() < 0.15:
        state.laurels += 1
        result["laurel_earned"] = 1
        newly_t = title_engine.check_and_unlock_titles(state)
        if newly_t:
            result["titles_unlocked"] = newly_t
    if state.campaigns_won >= 20 and "champion_of_the_gods" not in state.titles_unlocked:
        state.titles_unlocked.append("champion_of_the_gods")
        state.active_titles["legendary"] = "champion_of_the_gods"
        result["title_unlocked"] = "Champion of the Gods"
    _save_estate(user_id, state)
    return {
        "status":             "ok",
        "result":             result,
        "creature_encounter": result.get("creature_reward"),
        "state":              state.to_dict(),
    }

@app.post("/api/estate/campaign/launch")
async def launch_campaign(req: Request, u: dict = CurrentUser):
    return await _run_campaign(u["user_id"], await req.json())


@app.get("/api/estate/farm-types")
def get_farm_types():
    return {"farm_types": farm_engine.get_all_farm_types()}

@app.post("/api/estate/farm/build")
async def build_farm(req: Request, u: dict = CurrentUser):
    p = await req.json()
    farm_type = p.get("farm_type", "").strip()
    col = int(p.get("col", 0))
    row = int(p.get("row", 0))
    if not farm_type:
        raise HTTPException(400, "farm_type is required")
    uid   = u["user_id"]
    state = _load_estate(uid)
    ok, msg = farm_engine.build_farm(state, farm_type, col, row)
    if ok:
        title_engine.check_and_unlock_titles(state)
        _save_estate(uid, state)
    return {"status": "ok" if ok else "error", "message": msg, "state": state.to_dict()}

@app.post("/api/estate/farm/upgrade")
async def upgrade_farm(req: Request, u: dict = CurrentUser):
    p = await req.json()
    col = int(p.get("col", 0))
    row = int(p.get("row", 0))
    uid   = u["user_id"]
    state = _load_estate(uid)
    ok, msg = farm_engine.upgrade_farm(state, col, row)
    if ok:
        _save_estate(uid, state)
    return {"status": "ok" if ok else "error", "message": msg, "state": state.to_dict()}


@app.get("/api/estate/processing")
def get_processing(u: dict = CurrentUser):
    state = _load_estate(u["user_id"])
    return {"buildings": processing_engine.get_player_buildings(state), "state": state.to_dict()}

@app.post("/api/estate/processing/build")
async def build_processing(req: Request, u: dict = CurrentUser):
    p = await req.json()
    building_id = p.get("building_id", "").strip()
    if not building_id:
        raise HTTPException(400, "building_id is required")
    uid   = u["user_id"]
    state = _load_estate(uid)
    ok, msg = processing_engine.build_processing_building(state, building_id)
    if ok:
        _save_estate(uid, state)
    return {"status": "ok" if ok else "error", "message": msg, "state": state.to_dict()}

@app.post("/api/estate/processing/process")
async def process_goods(req: Request, u: dict = CurrentUser):
    p = await req.json()
    building_id = p.get("building_id", "").strip()
    amount = int(p.get("amount", 1))
    if not building_id:
        raise HTTPException(400, "building_id is required")
    uid   = u["user_id"]
    state = _load_estate(uid)
    ok, msg, detail = processing_engine.process_goods(state, building_id, amount)
    if ok:
        title_engine.check_and_unlock_titles(state)
        _save_estate(uid, state)
    return {"status": "ok" if ok else "error", "message": msg, "detail": detail, "state": state.to_dict()}


@app.get("/api/estate/villa")
def get_villa(u: dict = CurrentUser):
    state = _load_estate(u["user_id"])
    level = getattr(state, "villa_level", 1)
    return {
        "villa_level":  level,
        "max_level":    3,
        "upgrade_cost": army_engine.VILLA_UPGRADE_COSTS.get(level + 1),
        "army_limit":   state.army_limit,
        "barracks_unlock": {
            "laurels_needed":     3,
            "farms_needed":       3,
            "villa_level_needed": 2,
            "laurels_have":       state.laurels,
            "farms_have":         len(state.farms),
            "villa_have":         level,
            "unlocked": (state.laurels >= 3 and len(state.farms) >= 3 and level >= 2),
        },
    }

@app.post("/api/estate/villa/upgrade")
async def upgrade_villa(req: Request, u: dict = CurrentUser):
    uid   = u["user_id"]
    state = _load_estate(uid)
    ok, msg = army_engine.upgrade_villa(state)
    if ok:
        _save_estate(uid, state)
    return {"status": "ok" if ok else "error", "message": msg, "state": state.to_dict()}


_BLESSINGS = {
    "hermes": {"id": "hermes", "name": "Blessing of Hermes", "icon": "🪶",
               "cost_laurels": 1, "effect": "+30% running drachmae for your next run",
               "buff_key": "blessing_hermes", "expires": "after next run"},
    "demeter": {"id": "demeter", "name": "Blessing of Demeter", "icon": "🌾",
                "cost_laurels": 1, "effect": "+50% farm production for next harvest",
                "buff_key": "blessing_demeter", "expires": "after next farm harvest"},
    "ares":   {"id": "ares",   "name": "Blessing of Ares",   "icon": "⚔️",
               "cost_laurels": 1, "effect": "+50% army strength for next campaign",
               "buff_key": "blessing_ares", "expires": "after next campaign"},
    "poseidon": {"id": "poseidon", "name": "Blessing of Poseidon", "icon": "🌊",
                 "cost_laurels": 1, "effect": "+30% rucking drachmae for your next ruck",
                 "buff_key": "blessing_poseidon", "expires": "after next ruck"},
    "hephaestus": {"id": "hephaestus", "name": "Blessing of Hephaestus", "icon": "🔥",
                   "cost_laurels": 1,
                   "effect": "+30% strength drachmae for your next strength workout",
                   "buff_key": "blessing_hephaestus", "expires": "after next strength workout"},
}

@app.get("/api/estate/blessings")
def get_blessings(u: dict = CurrentUser):
    state  = _load_estate(u["user_id"])
    active = getattr(state, "active_blessings", {})
    return {
        "blessings": [{**b, "active": active.get(b["id"], 0) > 0,
                       "remaining": active.get(b["id"], 0)} for b in _BLESSINGS.values()],
        "laurels": state.laurels,
    }

@app.post("/api/estate/blessing/activate")
async def activate_blessing(req: Request, u: dict = CurrentUser):
    p = await req.json()
    blessing_id = p.get("blessing_id", "").strip()
    if blessing_id not in _BLESSINGS:
        raise HTTPException(400, f"Unknown blessing: {blessing_id}")
    uid   = u["user_id"]
    state = _load_estate(uid)
    b     = _BLESSINGS[blessing_id]
    cost  = b["cost_laurels"]
    if state.laurels < cost:
        return {"status": "error",
                "message": f"Need {cost} laurel (have {state.laurels}).",
                "state": state.to_dict()}
    state.laurels -= cost
    if not hasattr(state, "active_blessings") or state.active_blessings is None:
        state.active_blessings = {}
    state.active_blessings[blessing_id] = state.active_blessings.get(blessing_id, 0) + 1
    _save_estate(uid, state)
    return {"status": "ok", "message": f"{b['icon']} {b['name']} activated! {b['effect']}",
            "state": state.to_dict()}


# ── Agora — sell goods for drachmae ───────────────────────────────────────────

import json as _json

_MARKET_PATH = BASE / "static" / "market_prices.json"

def _market_prices() -> dict:
    try:
        return _json.loads(_MARKET_PATH.read_text())
    except Exception:
        return {}

@app.get("/api/estate/agora/prices")
def agora_prices():
    return _market_prices()

@app.post("/api/estate/agora/sell")
async def agora_sell(req: Request, u: dict = CurrentUser):
    p        = await req.json()
    resource = (p.get("resource") or "").strip()
    quantity = int(p.get("quantity") or 1)
    if quantity < 1:
        raise HTTPException(400, "quantity must be at least 1")
    prices = _market_prices()
    if resource not in prices:
        raise HTTPException(400, f"Unknown resource: {resource}")
    uid   = u["user_id"]
    state = _load_estate(uid)
    stock = getattr(state, resource, 0)
    if stock < quantity:
        raise HTTPException(400, f"Not enough {resource} (have {stock}, need {quantity})")
    setattr(state, resource, stock - quantity)
    earned = prices[resource]["price"] * quantity
    state.drachmae = round(state.drachmae + earned, 2)
    _save_estate(uid, state)
    label = prices[resource]["label"]
    emoji = prices[resource]["emoji"]
    return {
        "status":   "ok",
        "message":  f"Sold {quantity}× {emoji} {label} for +{earned} 🪙",
        "earned":   earned,
        "state":    state.to_dict(),
    }

# ── Admin endpoints ───────────────────────────────────────────────────────────

@app.post("/admin/backup")
async def admin_backup(req: Request):
    """
    Export a JSON snapshot of all player data for backup purposes.
    Requires the ADMIN_SECRET env var to match the X-Admin-Secret header.
    """
    secret = os.environ.get("ADMIN_SECRET", "")
    if not secret or req.headers.get("X-Admin-Secret", "") != secret:
        raise HTTPException(403, "Forbidden")

    from sqlalchemy import text as _text
    backup: dict = {"created_at": dt.datetime.utcnow().isoformat(), "tables": {}}

    with db._db() as sess:
        for table in ("users", "player_estate", "player_legacy", "workouts", "workout_sessions"):
            try:
                rows = sess.execute(_text(f"SELECT * FROM {table}")).fetchall()
                backup["tables"][table] = [dict(r._mapping) for r in rows]
            except Exception as e:
                backup["tables"][table] = {"error": str(e)}

    timestamp = dt.datetime.utcnow().strftime("%Y_%m_%d_%H%M%S")
    filename  = f"backup_{timestamp}.json"

    # Write locally (useful for SQLite; on Render this is ephemeral storage)
    backup_path = BASE / filename
    try:
        backup_path.write_text(json.dumps(backup, default=str, indent=2))
        log.info("Backup written to %s", backup_path)
    except Exception as e:
        log.warning("Could not write backup file: %s", e)

    return JSONResponse(content={"status": "ok", "filename": filename, "backup": backup})


# ── Startup logging ───────────────────────────────────────────────────────────

@app.on_event("startup")
async def _startup_log():
    db_type = "PostgreSQL" if db._IS_PG else f"SQLite ({os.environ.get('DB_PATH', 'olympus.db')})"
    log.info("=" * 60)
    log.info("Olympus Training Log — server starting")
    log.info("App version : %s", _APP_VERSION)
    log.info("Database    : %s", db_type)
    log.info("=" * 60)
