from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import core, datetime as dt, os, time as _time

_APP_VERSION = str(int(_time.time()))
import db
import auth as _auth

BASE   = Path(__file__).parent
STATIC = BASE / "static"

app = FastAPI(title="First Bell")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

CurrentUser = Depends(_auth.get_current_user)


# ── Per-user training state helpers ──────────────────────────────────────────

def _load_training(user_id: int) -> dict:
    raw = db.load_legacy(user_id)
    if raw is None:
        raw = core.default_state()
        db.save_legacy(user_id, raw)

    # Migrate old track keys that no longer exist
    if raw.get("track") and not raw["track"].startswith("custom_") \
            and raw["track"] not in core.TEMPLATES:
        raw["track"] = core.TRACK_KEYS[0]
        raw["microcycle"] = {
            "id":                 raw.get("microcycle", {}).get("id", 0),
            "sessions_completed": 0,
            "start_date":         str(dt.date.today()),
            "completed":          False,
        }

    # Ensure new state keys are present
    raw.setdefault("cycle_week", 1)
    raw.setdefault("strength_sessions_in_wave", 0)
    mc = raw.setdefault("microcycle", {})
    mc.setdefault("id",                 0)
    mc.setdefault("sessions_completed", 0)
    mc.setdefault("start_date",         str(dt.date.today()))
    mc.setdefault("completed",          False)
    raw.setdefault("week_log",           {})
    raw.setdefault("ruck_log",           [])
    raw.setdefault("run_log",            [])
    raw.setdefault("walk_log",           [])
    raw.setdefault("workouts",           [])
    raw.setdefault("custom_tracks",      [])
    raw.setdefault("total_ruck_miles",   sum(r.get("distance_miles", 0) for r in raw["ruck_log"] if isinstance(r, dict)))
    raw.setdefault("total_run_miles",    sum(r.get("distance_miles", 0) for r in raw["run_log"]  if isinstance(r, dict)))
    raw.setdefault("total_walk_miles",   sum(r.get("distance_miles", 0) for r in raw["walk_log"] if isinstance(r, dict)))
    raw.setdefault("journey_miles",
                   raw["total_ruck_miles"] + raw["total_run_miles"] + raw["total_walk_miles"])

    raw["ruck_log"] = [r for r in raw["ruck_log"] if isinstance(r, dict)]
    raw["run_log"]  = [r for r in raw["run_log"]  if isinstance(r, dict)]
    raw["walk_log"] = [r for r in raw["walk_log"] if isinstance(r, dict)]
    return raw


def _save_training(user_id: int, d: dict) -> None:
    db.save_legacy(user_id, d)


def _append_estate_log(
    state: gs.PlayerState, description: str, log_type: str = "system"
) -> None:
    """Append one entry to the player's persistent estate log (append-only, no cap)."""
    if not hasattr(state, "estate_log") or state.estate_log is None:
        state.estate_log = []
    state.estate_log.append({
        "timestamp": dt.datetime.now().isoformat(),
        "type":      log_type,
        "description": description,
    })


# ── Static serving ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC / "index.html")

@app.get("/service-worker.js")
def service_worker_root():
    fp   = STATIC / "service-worker.js"
    resp = FileResponse(fp, media_type="application/javascript")
    resp.headers["Cache-Control"]        = "no-cache, no-store, must-revalidate"
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

@app.get("/health")
def health():
    return {"status": "ok", "version": _APP_VERSION}

@app.get("/api/version")
def api_version():
    return {"version": _APP_VERSION}


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/register")
async def register(req: Request):
    p        = await req.json()
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
    p        = await req.json()
    username = (p.get("username") or "").strip()
    password = (p.get("password") or "").strip()
    if not username or not password:
        raise HTTPException(400, "username and password are required")
    user = db.get_user_by_username(username)
    if not user or not _auth.verify_password(password, user["password_hash"]):
        raise HTTPException(401, "Invalid username or password")
    token = _auth.create_token(user["id"], user["username"])
    return {"status": "ok", "token": token, "username": user["username"]}


# ── Training state ────────────────────────────────────────────────────────────

@app.get("/api/state")
def get_state(u: dict = CurrentUser):
    return _load_training(u["user_id"])

@app.get("/api/workout/today")
def get_today(u: dict = CurrentUser):
    state   = _load_training(u["user_id"])
    workout = core.get_today_workout(state)
    # Augment suggested_weight from db history if possible
    if workout.get("status") == "active":
        track = workout.get("track_key", "")
        if track and track in core.TEMPLATES:
            main_text = workout.get("main", "")
            # Try to find a matching movement in history
            history = db.get_workouts(u["user_id"], limit=50)
            for row in history:
                if row.get("movement") and row.get("weight_kg") and \
                        row.get("type") in ("recommended", "strength"):
                    workout["suggested_weight"] = float(row["weight_kg"])
                    break
    return workout

@app.get("/api/movements")
def get_movements():
    return core.get_movements()

@app.get("/api/movement_history/{movement}")
def get_movement_history(movement: str, u: dict = CurrentUser):
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
    state  = _load_training(u["user_id"])
    tracks = {k: v["name"] for k, v in core.TEMPLATES.items()}
    for ct in state.get("custom_tracks", []):
        n = len(ct.get("sessions", []))
        tracks[f"custom_{ct['id']}"] = f"{ct['name']} ({n} sessions)"
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
    key     = payload.get("key", "").strip()
    if not key.startswith("custom_") and key not in core.TEMPLATES:
        raise HTTPException(400, f"Unknown track: {key}")
    uid   = u["user_id"]
    state = _load_training(uid)
    if key.startswith("custom_"):
        track_id = key[7:]
        if core.get_custom_track_detail(state, track_id) is None:
            raise HTTPException(404, f"Custom track not found: {key}")
    msg = core.init_track(state, key)
    _save_training(uid, state)
    return {"status": "ok", "msg": msg, "state": state}


# ── Workout logging ───────────────────────────────────────────────────────────

@app.post("/api/workout/recommended")
async def log_recommended(req: Request, u: dict = CurrentUser):
    weights_lbs = None
    try:
        p = await req.json()
        weights_lbs = p.get("weights_lbs")
    except Exception:
        pass
    uid   = u["user_id"]
    state = _load_training(uid)
    msg   = core.log_rec(state, weights_lbs=weights_lbs)
    _save_training(uid, state)
    today = str(dt.date.today())
    if state.get("workouts"):
        last = state["workouts"][-1]
        db.insert_workout(uid, today, "recommended", 0,
                          notes=last.get("details", "")[:200])
    return {"status": "ok", "msg": msg, "state": state}

@app.post("/api/workout/custom")
async def log_custom(req: Request, u: dict = CurrentUser):
    payload = await req.json()
    text    = payload.get("text", "").strip()
    if not text:
        raise HTTPException(400, "Empty workout description")
    uid   = u["user_id"]
    state = _load_training(uid)
    msg   = core.log_custom(state, text)
    _save_training(uid, state)
    db.insert_workout(uid, str(dt.date.today()), "custom", 0, notes=text[:200])
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
    uid   = u["user_id"]
    state = _load_training(uid)
    msg   = core.log_ruck(state, miles, pounds)
    _save_training(uid, state)
    db.insert_workout(uid, str(dt.date.today()), "rucking", 0,
                      distance_miles=miles, weight_lbs=pounds or None,
                      duration_min=float(p.get("duration_min") or 0) or None)
    return {"status": "ok", "msg": msg, "state": state}

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
    state = _load_training(uid)
    msg   = core.log_walk(state, miles)
    _save_training(uid, state)
    db.insert_workout(uid, str(dt.date.today()), "walking", 0,
                      distance_miles=miles,
                      duration_min=float(p.get("duration_min") or 0) or None)
    return {"status": "ok", "msg": msg, "state": state}

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
    state = _load_training(uid)
    msg   = core.log_run(state, miles, pace)
    _save_training(uid, state)
    db.insert_workout(uid, str(dt.date.today()), "running", 0,
                      distance_miles=miles,
                      duration_min=float(p.get("duration_min") or 0) or None)
    return {"status": "ok", "msg": msg, "state": state}

@app.post("/api/strength")
async def log_strength(req: Request, u: dict = CurrentUser):
    p          = await req.json()
    movement   = (p.get("movement") or "").strip()
    weight_kg  = float(p.get("weight_kg") or 0)
    sets_n     = int(p.get("sets") or 1)
    reps_n     = int(p.get("reps") or 1)
    if not movement:
        raise HTTPException(400, "movement is required")
    if sets_n < 1 or reps_n < 1:
        raise HTTPException(400, "sets and reps must be at least 1")
    uid   = u["user_id"]
    today = str(dt.date.today())
    db.insert_workout(uid, today, "strength", 0,
                      movement=movement, weight_kg=weight_kg,
                      sets=sets_n, reps=reps_n)
    move_name = next((m["name"] for m in core.get_movements() if m["slug"] == movement),
                     movement.replace("_", " ").title())
    return {
        "status": "ok",
        "msg":    f"{move_name} — {sets_n}×{reps_n} @ {weight_kg}kg logged",
    }

@app.post("/api/session")
async def log_session(req: Request, u: dict = CurrentUser):
    p          = await req.json()
    session_type = (p.get("type") or "custom").strip()
    notes        = (p.get("notes") or "").strip()
    uid          = u["user_id"]
    state        = _load_training(uid)
    msg          = core.log_custom(state, notes or session_type)
    _save_training(uid, state)
    db.insert_workout(uid, str(dt.date.today()), session_type, 0,
                      notes=notes[:200] if notes else None)
    return {"status": "ok", "msg": msg, "state": state}


# ── Workout history CRUD ──────────────────────────────────────────────────────

@app.get("/api/workouts")
def get_workouts_list(u: dict = CurrentUser):
    return {"workouts": db.get_workouts(u["user_id"])}

@app.get("/api/sessions")
def get_sessions(u: dict = CurrentUser):
    return {"sessions": db.get_workouts(u["user_id"], limit=50)}

@app.put("/api/workout/{workout_id}")
async def edit_workout(workout_id: int, req: Request, u: dict = CurrentUser):
    p   = await req.json()
    uid = u["user_id"]
    old_rows = db.get_workouts(uid, limit=500)
    old = next((r for r in old_rows if r["id"] == workout_id), None)
    if not old:
        raise HTTPException(404, "Workout not found")
    update_fields = {}
    for field in ("movement", "weight_kg", "sets", "reps",
                  "distance_miles", "duration_min", "weight_lbs", "notes"):
        if field in p:
            update_fields[field] = p[field]
    ok = db.update_workout(workout_id, uid, **update_fields)
    if not ok:
        raise HTTPException(404, "Workout not found or no changes")
    return {"status": "ok", "workouts": db.get_workouts(uid)}

@app.delete("/api/workout/{workout_id}")
def del_workout(workout_id: int, u: dict = CurrentUser):
    uid     = u["user_id"]
    deleted = db.delete_workout(workout_id, uid)
    if not deleted:
        raise HTTPException(404, "Workout not found")
    return {"status": "ok", "workouts": db.get_workouts(uid)}


# ── Custom tracks ─────────────────────────────────────────────────────────────

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
    state = _load_training(uid)
    try:
        track = core.save_custom_track(state, name, sessions)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _save_training(uid, state)
    return {"status": "ok", "track": track, "state": state}

@app.delete("/api/tracks/custom/{track_id}")
def delete_custom_track(track_id: str, u: dict = CurrentUser):
    uid   = u["user_id"]
    state = _load_training(uid)
    found = core.delete_custom_track(state, track_id)
    if not found:
        raise HTTPException(404, f"Custom track not found: {track_id}")
    _save_training(uid, state)
    return {"status": "ok", "state": state}


# ── New analytics endpoints ───────────────────────────────────────────────────

@app.get("/api/streak")
def get_streak(u: dict = CurrentUser):
    state = _load_training(u["user_id"])
    return core.get_streak_info(state)

@app.get("/api/progress/{movement}")
def get_progress(movement: str, u: dict = CurrentUser):
    history = db.get_movement_history_all(u["user_id"], movement, limit=20)
    return {"movement": movement, "history": history}
