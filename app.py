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
        # migrate older states that predate new fields
        d.setdefault("total_ruck_miles",
                     sum(r.get("distance_miles", 0)
                         for r in d.get("ruck_log", [])
                         if isinstance(r, dict)))
        d.setdefault("week_log", {})
        mc = d.setdefault("microcycle", {})
        mc.setdefault("start_date",          str(dt.date.today()))
        mc.setdefault("badge_given",          False)
        mc.setdefault("id",                   0)
        mc.setdefault("sessions_completed",   0)
        # purge any corrupted ruck entries that aren't dicts
        d["ruck_log"] = [r for r in d.get("ruck_log", []) if isinstance(r, dict)]
        return d
    d = core.default_state()
    DATA.write_text(json.dumps(d, indent=2))
    return d

def _save(d: dict) -> None:
    DATA.write_text(json.dumps(d, indent=2))

# ---------- FastAPI ----------
app = FastAPI(title="Olympus Training Log API")

# -------  root / PWA ---------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC / "index.html")

@app.get("/static/{path:path}")
def statics(path: str):
    file_path = STATIC / path
    if not file_path.exists():
        raise HTTPException(404)
    return FileResponse(file_path)

@app.get("/img/{path:path}")
def images(path: str):
    """Serve monster art, ruck postcards, and other project images."""
    file_path = BASE / path
    if not file_path.exists():
        raise HTTPException(404)
    return FileResponse(file_path)

# -------  read-only JSON API -------------------------------------------
@app.get("/api/state")
def get_state():
    return _load()

@app.get("/api/workout/today")
def get_today():
    return core.get_today_workout(_load())

@app.get("/api/tracks")
def get_tracks():
    return {k: v["name"] for k, v in core.TEMPLATES.items()}

# -------  mutating endpoints -------------------------------------------
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
def log_recommended():
    state = _load()
    msg   = core.log_rec(state)
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
