from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import json, core, datetime as dt

BASE   = Path(__file__).parent
DATA   = BASE / "data.json"
STATIC = BASE / "static"

# ---------- file helpers ----------
def _load() -> dict:
    if DATA.exists():
        d = json.loads(DATA.read_text())
        # ── migrate: backfill fields added in later versions ──
        d.setdefault("total_ruck_miles",
                     sum(r.get("distance_miles", 0)
                         for r in d.get("ruck_log", [])
                         if isinstance(r, dict)))
        d.setdefault("total_run_miles",
                     sum(r.get("distance_miles", 0)
                         for r in d.get("run_log", [])
                         if isinstance(r, dict)))
        d.setdefault("run_log", [])
        d.setdefault("week_log", {})
        # journey_miles = combined ruck + run
        d.setdefault("journey_miles",
                     d["total_ruck_miles"] + d["total_run_miles"])
        mc = d.setdefault("microcycle", {})
        mc.setdefault("start_date",         str(dt.date.today()))
        mc.setdefault("badge_given",         False)
        mc.setdefault("id",                  0)
        mc.setdefault("sessions_completed",  0)
        # purge corrupted list entries
        d["ruck_log"] = [r for r in d.get("ruck_log", []) if isinstance(r, dict)]
        d["run_log"]  = [r for r in d.get("run_log",  []) if isinstance(r, dict)]
        return d
    d = core.default_state()
    DATA.write_text(json.dumps(d, indent=2))
    return d

def _save(d: dict) -> None:
    DATA.write_text(json.dumps(d, indent=2))

# ---------- FastAPI ----------
app = FastAPI(title="Olympus Training Log API")

# ──  root / PWA ────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC / "index.html")

@app.get("/static/{path:path}")
def statics(path: str):
    file_path = STATIC / path
    if not file_path.exists():
        raise HTTPException(404)
    resp = FileResponse(file_path)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@app.get("/img/{path:path}")
def images(path: str):
    """Serve monster art, ruck postcards, and other project images."""
    file_path = BASE / path
    if not file_path.exists():
        raise HTTPException(404)
    return FileResponse(file_path)

# ──  read-only JSON API ────────────────────────────────────────────────────────
@app.get("/api/state")
def get_state():
    return _load()

@app.get("/api/workout/today")
def get_today():
    return core.get_today_workout(_load())

@app.get("/api/tracks")
def get_tracks():
    return {k: v["name"] for k, v in core.TEMPLATES.items()}

@app.get("/api/tracks/{key}")
def get_track_detail(key: str):
    """Return full track data (all sessions) for the preview modal."""
    detail = core.get_track_detail(key)
    if detail is None:
        raise HTTPException(404, f"Unknown track: {key}")
    return detail

# ──  mutating endpoints ────────────────────────────────────────────────────────
@app.post("/api/track/select")
async def select_track(req: Request):
    payload = await req.json()
    key = payload.get("key", "").strip()
    if key not in core.TEMPLATES:
        raise HTTPException(400, f"Unknown track: {key}")
    state = _load()
    msg   = core.init_track(state, key)
    _save(state)
    return {"status": "ok", "msg": msg, "state": state}

@app.post("/api/workout/recommended")
async def log_recommended(req: Request):
    weight_kg = None
    try:
        p = await req.json()
        weight_lbs = p.get("weight_lbs")
        if weight_lbs is not None:
            weight_kg = float(weight_lbs) * 0.453592
    except Exception:
        pass   # body may be absent or non-JSON — that's fine
    state = _load()
    msg   = core.log_rec(state, weight_kg=weight_kg)
    _save(state)
    return {"status": "ok", "msg": msg, "state": state}

@app.post("/api/workout/custom")
async def log_custom(req: Request):
    payload = await req.json()
    text    = payload.get("text", "").strip()
    if not text:
        raise HTTPException(400, "Empty workout description")
    state = _load()
    msg   = core.log_custom(state, text)
    _save(state)
    return {"status": "ok", "msg": msg, "state": state}

@app.post("/api/ruck")
async def log_ruck(req: Request):
    p = await req.json()
    try:
        miles  = float(p["miles"])
        pounds = float(p["pounds"])
    except (KeyError, ValueError):
        raise HTTPException(400, "miles and pounds must be numeric")
    if miles <= 0:
        raise HTTPException(400, "miles must be positive")
    state = _load()
    msg   = core.log_ruck(state, miles, pounds)
    _save(state)
    return {"status": "ok", "msg": msg, "state": state}

@app.post("/api/run")
async def log_run(req: Request):
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
    state = _load()
    msg   = core.log_run(state, miles, pace)
    _save(state)
    return {"status": "ok", "msg": msg, "state": state}
