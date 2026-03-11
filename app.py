from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json, core, datetime as dt, os
import db  # SQLite persistence layer
from laurel_of_olympus import game_state as gs
from laurel_of_olympus import workout_engine, farm_engine, event_engine
from laurel_of_olympus import oracle_engine, title_engine
from laurel_of_olympus import creature_engine, relic_engine, buff_engine
from laurel_of_olympus import army_engine, processing_engine, trophy_engine

BASE   = Path(__file__).parent
STATIC = BASE / "static"

# ── One-time migration from legacy JSON files → SQLite ────────────────────────
_LEGACY_DATA   = BASE / "data.json"
_LEGACY_ESTATE = Path.home() / ".laurel_of_olympus.json"
db.migrate_from_file("legacy_state",  _LEGACY_DATA)
db.migrate_from_file("estate_state",  _LEGACY_ESTATE)

# ── State helpers (SQLite-backed) ─────────────────────────────────────────────

def _load() -> dict:
    """Load legacy workout state from SQLite (falls back to core defaults)."""
    raw = db.load("legacy_state")
    if raw is None:
        raw = core.default_state()
        db.save("legacy_state", raw)
    # Migrate: backfill fields added in later versions
    raw.setdefault("total_ruck_miles",
                   sum(r.get("distance_miles", 0)
                       for r in raw.get("ruck_log", [])
                       if isinstance(r, dict)))
    raw.setdefault("total_run_miles",
                   sum(r.get("distance_miles", 0)
                       for r in raw.get("run_log", [])
                       if isinstance(r, dict)))
    raw.setdefault("walk_log", [])
    raw.setdefault("total_walk_miles",
                   sum(r.get("distance_miles", 0)
                       for r in raw.get("walk_log", [])
                       if isinstance(r, dict)))
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


def _save(d: dict) -> None:
    db.save("legacy_state", d)


def _load_estate() -> gs.PlayerState:
    """Load estate PlayerState from SQLite."""
    raw = db.load("estate_state")
    if raw is None:
        return gs.PlayerState()
    try:
        return gs.PlayerState.from_dict(raw)
    except Exception:
        return gs.PlayerState()


def _save_estate(state: gs.PlayerState) -> None:
    db.save("estate_state", state.to_dict())


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="Olympus Training Log API")

# CORS — allow all origins so mobile browsers and external clients can reach the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static file serving ───────────────────────────────────────────────────────

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

# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

# ── Deployment-friendly shorthand endpoints ───────────────────────────────────

@app.get("/player-state")
def player_state():
    """Combined player state: legacy workout data + estate RPG state."""
    return {
        "workout": _load(),
        "estate":  _load_estate().to_dict(),
    }

@app.get("/estate")
def get_estate():
    """Return estate RPG state."""
    return _load_estate().to_dict()

@app.get("/creatures")
def get_creatures():
    """Return sanctuary contents and all creature definitions."""
    state = _load_estate()
    return {
        "sanctuary":     creature_engine.get_sanctuary_details(state),
        "capacity":      state.sanctuary_capacity,
        "sanctuary_ids": state.sanctuary,
        "all_creatures": creature_engine.get_all_creatures(),
        "buffs":         creature_engine.get_sanctuary_buffs(state),
    }

@app.post("/log-workout")
async def log_workout(req: Request):
    """
    Log a workout and apply all estate RPG effects.
    Body: { "workout_type": "strength"|"running"|"walking"|"rucking",
            "volume": 5000, "miles": 2.0, ... }
    Delegates to the full estate simulate-workout pipeline.
    """
    p = await req.json()
    return await _run_estate_workout(p)

@app.post("/campaign")
async def campaign(req: Request):
    """Launch a campaign. Body: { "region_id": "..." }"""
    p = await req.json()
    return await _run_campaign(p)

# ── Legacy workout API ────────────────────────────────────────────────────────

@app.get("/api/state")
def get_state():
    return _load()

@app.get("/api/workout/today")
def get_today():
    return core.get_today_workout(_load())

@app.get("/api/movements")
def get_movements():
    return core.get_movements()

@app.get("/api/tracks")
def get_tracks():
    state  = _load()
    tracks = {k: v["name"] for k, v in core.TEMPLATES.items()}
    for ct in state.get("custom_tracks", []):
        n = len(ct.get("sessions", []))
        tracks[f"custom_{ct['id']}"] = f"⚒ {ct['name']} ({n} sessions)"
    return tracks

@app.get("/api/tracks/{key}")
def get_track_detail(key: str):
    if key.startswith("custom_"):
        state    = _load()
        track_id = key[7:]
        detail   = core.get_custom_track_detail(state, track_id)
        if detail is None:
            raise HTTPException(404, f"Custom track not found: {key}")
        return {"key": key, "name": detail["name"], "sessions": detail["sessions"]}
    detail = core.get_track_detail(key)
    if detail is None:
        raise HTTPException(404, f"Unknown track: {key}")
    return detail

@app.post("/api/track/select")
async def select_track(req: Request):
    payload = await req.json()
    key = payload.get("key", "").strip()
    if not key.startswith("custom_") and key not in core.TEMPLATES:
        raise HTTPException(400, f"Unknown track: {key}")
    state = _load()
    if key.startswith("custom_"):
        track_id = key[7:]
        if core.get_custom_track_detail(state, track_id) is None:
            raise HTTPException(404, f"Custom track not found: {key}")
    msg = core.init_track(state, key)
    _save(state)
    return {"status": "ok", "msg": msg, "state": state}

@app.post("/api/workout/recommended")
async def log_recommended(req: Request):
    weights_lbs = None
    try:
        p = await req.json()
        weights_lbs = p.get("weights_lbs")
    except Exception:
        pass
    state = _load()
    msg   = core.log_rec(state, weights_lbs=weights_lbs)
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

@app.post("/api/walk")
async def log_walk(req: Request):
    p = await req.json()
    try:
        miles = float(p["miles"])
    except (KeyError, ValueError):
        raise HTTPException(400, "miles must be numeric")
    if miles <= 0:
        raise HTTPException(400, "miles must be positive")
    state = _load()
    msg   = core.log_walk(state, miles)
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

@app.post("/api/tracks/custom")
async def save_custom_track(req: Request):
    p        = await req.json()
    name     = (p.get("name") or "").strip()
    sessions = p.get("sessions", [])
    if not name:
        raise HTTPException(400, "Track name is required.")
    if not sessions:
        raise HTTPException(400, "At least one session is required.")
    state = _load()
    try:
        track = core.save_custom_track(state, name, sessions)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _save(state)
    return {"status": "ok", "track": track, "state": state}

@app.delete("/api/tracks/custom/{track_id}")
def delete_custom_track(track_id: str):
    state = _load()
    found = core.delete_custom_track(state, track_id)
    if not found:
        raise HTTPException(404, f"Custom track not found: {track_id}")
    _save(state)
    return {"status": "ok", "state": state}

# ── Estate (Laurel of Olympus RPG) ───────────────────────────────────────────

@app.get("/api/estate/state")
def get_estate_state():
    return _load_estate().to_dict()


async def _run_estate_workout(p: dict) -> dict:
    """Shared logic for /log-workout and /api/estate/simulate-workout."""
    workout_type = p.get("workout_type", "strength")
    kwargs = {k: v for k, v in p.items() if k != "workout_type"}
    if workout_type == "strength" and "volume" not in kwargs:
        kwargs["volume"] = 5000.0
    elif workout_type in ("walking", "running", "rucking") and "miles" not in kwargs:
        kwargs["miles"] = 2.0

    state = _load_estate()
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
                "type":  "oracle",
                "title": "Kassandra Stirs",
                "icon":  "🏛️",
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
            if ok_r:
                relic_find = candidate
            else:
                relic_find = {**candidate, "not_added": True}

    _save_estate(state)
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
async def estate_simulate_workout(req: Request):
    p = await req.json()
    return await _run_estate_workout(p)


@app.get("/api/estate/prophecy")
def get_prophecy_scroll():
    state = _load_estate()
    scroll = title_engine.get_prophecy_scroll(state)
    _save_estate(state)
    return scroll


# ── Creature / Sanctuary endpoints ───────────────────────────────────────────

@app.get("/api/estate/sanctuary")
def get_sanctuary():
    state = _load_estate()
    return {
        "sanctuary":     creature_engine.get_sanctuary_details(state),
        "capacity":      state.sanctuary_capacity,
        "sanctuary_ids": state.sanctuary,
        "all_creatures": creature_engine.get_all_creatures(),
        "buffs":         creature_engine.get_sanctuary_buffs(state),
    }

@app.post("/api/estate/creature/recruit")
async def recruit_creature(req: Request):
    p = await req.json()
    creature_id = p.get("creature_id", "").strip()
    if not creature_id:
        raise HTTPException(400, "creature_id is required")
    state = _load_estate()
    ok, msg = creature_engine.recruit_creature(state, creature_id)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(state)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}

@app.post("/api/estate/creature/release")
async def release_creature(req: Request):
    p = await req.json()
    creature_id = p.get("creature_id", "").strip()
    if not creature_id:
        raise HTTPException(400, "creature_id is required")
    state = _load_estate()
    ok, msg, reward = creature_engine.release_creature(state, creature_id)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(state)
    return {"status": "ok", "msg": msg, "reward": reward, "state": state.to_dict()}


# ── Relic endpoints ──────────────────────────────────────────────────────────

@app.get("/api/estate/relics")
def get_relics():
    state = _load_estate()
    return {
        "inventory":  relic_engine.get_inventory_details(state),
        "capacity":   state.relic_capacity,
        "relic_ids":  state.relics,
        "all_relics": relic_engine.get_all_relics(),
        "buffs":      relic_engine.get_relic_buffs(state),
    }

@app.post("/api/estate/relic/add")
async def add_relic(req: Request):
    p = await req.json()
    relic_id = p.get("relic_id", "").strip()
    if not relic_id:
        raise HTTPException(400, "relic_id is required")
    state = _load_estate()
    ok, msg = relic_engine.add_relic(state, relic_id)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(state)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}

@app.post("/api/estate/relic/remove")
async def remove_relic(req: Request):
    p = await req.json()
    relic_id = p.get("relic_id", "").strip()
    if not relic_id:
        raise HTTPException(400, "relic_id is required")
    state = _load_estate()
    ok, msg = relic_engine.remove_relic(state, relic_id)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(state)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}


# ── Trophy endpoints ─────────────────────────────────────────────────────────

@app.get("/api/estate/trophies")
def get_trophies():
    state = _load_estate()
    return {
        "trophies":     trophy_engine.get_trophy_inventory(state),
        "buff_summary": trophy_engine.get_buff_summary(state),
        "total":        len(getattr(state, "trophies", None) or []),
    }


# ── Army / Barracks endpoints ────────────────────────────────────────────────

@app.get("/api/estate/army")
def get_army():
    state = _load_estate()
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
async def build_barracks(req: Request):
    state = _load_estate()
    ok, msg = army_engine.build_barracks(state)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(state)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}

@app.post("/api/estate/army/recruit")
async def recruit_unit(req: Request):
    p = await req.json()
    unit_id = p.get("unit_id", "").strip()
    if not unit_id:
        raise HTTPException(400, "unit_id is required")
    state = _load_estate()
    ok, msg = army_engine.recruit_unit(state, unit_id)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(state)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}

@app.post("/api/estate/army/disband")
async def disband_unit(req: Request):
    p = await req.json()
    unit_id = p.get("unit_id", "").strip()
    if not unit_id:
        raise HTTPException(400, "unit_id is required")
    state = _load_estate()
    ok, msg = army_engine.disband_unit(state, unit_id)
    if not ok:
        raise HTTPException(400, msg)
    _save_estate(state)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}


async def _run_campaign(p: dict) -> dict:
    """Shared logic for /campaign and /api/estate/campaign/launch."""
    region_id = p.get("region_id", "").strip()
    if not region_id:
        raise HTTPException(400, "region_id is required")

    state = _load_estate()
    buffs = buff_engine.get_all_buffs(state)
    result = army_engine.launch_campaign(state, region_id, buffs=buffs)

    if "error" in result:
        raise HTTPException(400, result["error"])

    if buffs.get("blessing_ares"):
        state.active_blessings["ares"] = max(0, state.active_blessings.get("ares", 1) - 1)

    if result.get("relic_reward"):
        relic_id = result["relic_reward"]["id"]
        ok_relic, _ = relic_engine.add_relic(state, relic_id)
        if not ok_relic:
            result["relic_reward"]["not_added"] = True

    import random as _random
    if result.get("victory") and _random.random() < 0.15:
        state.laurels += 1
        result["laurel_earned"] = 1
        newly_t = title_engine.check_and_unlock_titles(state)
        if newly_t:
            result["titles_unlocked"] = newly_t

    if (
        state.campaigns_won >= 20
        and "champion_of_the_gods" not in state.titles_unlocked
    ):
        state.titles_unlocked.append("champion_of_the_gods")
        state.active_titles["legendary"] = "champion_of_the_gods"
        result["title_unlocked"] = "Champion of the Gods"

    _save_estate(state)
    return {
        "status":             "ok",
        "result":             result,
        "creature_encounter": result.get("creature_reward"),
        "state":              state.to_dict(),
    }


@app.post("/api/estate/campaign/launch")
async def launch_campaign(req: Request):
    p = await req.json()
    return await _run_campaign(p)


# ── Farm endpoints ───────────────────────────────────────────────────────────

@app.get("/api/estate/farm-types")
def get_farm_types():
    return {"farm_types": farm_engine.get_all_farm_types()}

@app.post("/api/estate/farm/build")
async def build_farm(req: Request):
    p = await req.json()
    farm_type = p.get("farm_type", "").strip()
    col = int(p.get("col", 0))
    row = int(p.get("row", 0))
    if not farm_type:
        raise HTTPException(400, "farm_type is required")
    state = _load_estate()
    ok, msg = farm_engine.build_farm(state, farm_type, col, row)
    if ok:
        title_engine.check_and_unlock_titles(state)
        _save_estate(state)
    return {"status": "ok" if ok else "error", "message": msg, "state": state.to_dict()}

@app.post("/api/estate/farm/upgrade")
async def upgrade_farm(req: Request):
    p = await req.json()
    col = int(p.get("col", 0))
    row = int(p.get("row", 0))
    state = _load_estate()
    ok, msg = farm_engine.upgrade_farm(state, col, row)
    if ok:
        _save_estate(state)
    return {"status": "ok" if ok else "error", "message": msg, "state": state.to_dict()}


# ── Processing building endpoints ─────────────────────────────────────────────

@app.get("/api/estate/processing")
def get_processing():
    state = _load_estate()
    return {
        "buildings": processing_engine.get_player_buildings(state),
        "state":     state.to_dict(),
    }

@app.post("/api/estate/processing/build")
async def build_processing(req: Request):
    p = await req.json()
    building_id = p.get("building_id", "").strip()
    if not building_id:
        raise HTTPException(400, "building_id is required")
    state = _load_estate()
    ok, msg = processing_engine.build_processing_building(state, building_id)
    if ok:
        _save_estate(state)
    return {"status": "ok" if ok else "error", "message": msg, "state": state.to_dict()}

@app.post("/api/estate/processing/process")
async def process_goods(req: Request):
    p = await req.json()
    building_id = p.get("building_id", "").strip()
    amount = int(p.get("amount", 1))
    if not building_id:
        raise HTTPException(400, "building_id is required")
    state = _load_estate()
    ok, msg, detail = processing_engine.process_goods(state, building_id, amount)
    if ok:
        title_engine.check_and_unlock_titles(state)
        _save_estate(state)
    return {
        "status":  "ok" if ok else "error",
        "message": msg,
        "detail":  detail,
        "state":   state.to_dict(),
    }


# ── Villa upgrade endpoint ────────────────────────────────────────────────────

@app.get("/api/estate/villa")
def get_villa():
    state = _load_estate()
    level = getattr(state, "villa_level", 1)
    next_cost = army_engine.VILLA_UPGRADE_COSTS.get(level + 1)
    return {
        "villa_level":  level,
        "max_level":    3,
        "upgrade_cost": next_cost,
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
async def upgrade_villa(req: Request):
    state = _load_estate()
    ok, msg = army_engine.upgrade_villa(state)
    if ok:
        _save_estate(state)
    return {"status": "ok" if ok else "error", "message": msg, "state": state.to_dict()}


# ── Blessings endpoints ───────────────────────────────────────────────────────

_BLESSINGS = {
    "hermes": {
        "id":          "hermes",
        "name":        "Blessing of Hermes",
        "icon":        "🪶",
        "cost_laurels": 1,
        "effect":      "+30% running drachmae for your next run",
        "buff_key":    "blessing_hermes",
        "expires":     "after next run",
    },
    "demeter": {
        "id":          "demeter",
        "name":        "Blessing of Demeter",
        "icon":        "🌾",
        "cost_laurels": 1,
        "effect":      "+50% farm production for next harvest",
        "buff_key":    "blessing_demeter",
        "expires":     "after next farm harvest",
    },
    "ares": {
        "id":          "ares",
        "name":        "Blessing of Ares",
        "icon":        "⚔️",
        "cost_laurels": 1,
        "effect":      "+50% army strength for next campaign",
        "buff_key":    "blessing_ares",
        "expires":     "after next campaign",
    },
}

@app.get("/api/estate/blessings")
def get_blessings():
    state = _load_estate()
    active = getattr(state, "active_blessings", {})
    result = []
    for b in _BLESSINGS.values():
        result.append({
            **b,
            "active":    active.get(b["id"], 0) > 0,
            "remaining": active.get(b["id"], 0),
        })
    return {"blessings": result, "laurels": state.laurels}

@app.post("/api/estate/blessing/activate")
async def activate_blessing(req: Request):
    p = await req.json()
    blessing_id = p.get("blessing_id", "").strip()
    if blessing_id not in _BLESSINGS:
        raise HTTPException(400, f"Unknown blessing: {blessing_id}")
    state = _load_estate()
    b = _BLESSINGS[blessing_id]
    cost = b["cost_laurels"]
    if state.laurels < cost:
        return {
            "status":  "error",
            "message": f"Need {cost} laurel to activate {b['name']} (have {state.laurels}).",
            "state":   state.to_dict(),
        }
    state.laurels -= cost
    if not hasattr(state, "active_blessings") or state.active_blessings is None:
        state.active_blessings = {}
    state.active_blessings[blessing_id] = state.active_blessings.get(blessing_id, 0) + 1
    _save_estate(state)
    return {
        "status":  "ok",
        "message": f"{b['icon']} {b['name']} activated! {b['effect']}",
        "state":   state.to_dict(),
    }
