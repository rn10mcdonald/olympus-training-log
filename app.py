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
        return json.loads(DATA.read_text())
    d = core.default_state()
    DATA.write_text(json.dumps(d))
    return d

def _save(d: dict) -> None:
    DATA.write_text(json.dumps(d, indent=2))

# ---------- FastAPI ----------
app = FastAPI(title="Olympus Training Log API")

# -------  static / PWA assets -----------------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC / "index.html")

@app.get("/static/{path:path}")
def statics(path: str):
    file_path = STATIC / path
    if not file_path.exists():
        raise HTTPException(404)
    return FileResponse(file_path)

# -------  JSON API ----------------------------------------------
@app.get("/api/state")
def get_state():
    return _load()

@app.post("/api/workout/recommended")
def log_recommended():
    state = _load()
    msg = core.log_rec(state)
    _save(state)
    return {"status": "ok", "msg": msg, "state": state}

@app.post("/api/workout/custom")
async def log_custom(req: Request):
    payload = await req.json()
    text = payload.get("text", "").strip()
    if not text:
        raise HTTPException(400, "Empty workout description")
    state = _load()
    msg = core.log_custom(state, text)
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
    state = _load()
    msg = core.log_ruck(state, miles, pounds)
    _save(state)
    return {"status": "ok", "msg": msg, "state": state}
