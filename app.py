from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import json, core, datetime as dt
from laurel_of_olympus import game_state as gs
from laurel_of_olympus import workout_engine, farm_engine, event_engine
from laurel_of_olympus import oracle_engine, title_engine
from laurel_of_olympus import creature_engine, relic_engine, buff_engine
from laurel_of_olympus import army_engine, processing_engine

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
        d.setdefault("walk_log", [])
        d.setdefault("total_walk_miles",
                     sum(r.get("distance_miles", 0)
                         for r in d.get("walk_log", [])
                         if isinstance(r, dict)))
        d.setdefault("run_log", [])
        d.setdefault("week_log", {})
        # journey_miles = combined ruck + run + walk
        d.setdefault("journey_miles",
                     d["total_ruck_miles"] + d["total_run_miles"] + d["total_walk_miles"])
        mc = d.setdefault("microcycle", {})
        mc.setdefault("start_date",         str(dt.date.today()))
        mc.setdefault("badge_given",         False)
        mc.setdefault("id",                  0)
        mc.setdefault("sessions_completed",  0)
        # purge corrupted list entries
        d["ruck_log"] = [r for r in d.get("ruck_log", []) if isinstance(r, dict)]
        d["run_log"]  = [r for r in d.get("run_log",  []) if isinstance(r, dict)]
        d.setdefault("custom_tracks", [])
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

@app.get("/api/movements")
def get_movements():
    """Return the full movement registry for the cycle builder."""
    return core.get_movements()

@app.get("/api/tracks")
def get_tracks():
    state  = _load()
    tracks = {k: v["name"] for k, v in core.TEMPLATES.items()}
    # Append user-built custom tracks
    for ct in state.get("custom_tracks", []):
        n = len(ct.get("sessions", []))
        tracks[f"custom_{ct['id']}"] = f"⚒ {ct['name']} ({n} sessions)"
    return tracks

@app.get("/api/tracks/{key}")
def get_track_detail(key: str):
    """Return full track data (all sessions) for the preview modal."""
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

# ──  mutating endpoints ────────────────────────────────────────────────────────
@app.post("/api/track/select")
async def select_track(req: Request):
    payload = await req.json()
    key = payload.get("key", "").strip()
    # Validate: must be a built-in template or an existing custom track
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
        weights_lbs = p.get("weights_lbs")   # dict: {main, acc_0, acc_1, acc_2, finisher}
    except Exception:
        pass   # body may be absent or non-JSON — that's fine
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

# ──  custom tracks ──────────────────────────────────────────────────────────────

@app.post("/api/tracks/custom")
async def save_custom_track(req: Request):
    """Save a new user-built training cycle."""
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
    """Delete a user-built training cycle by id."""
    state = _load()
    found = core.delete_custom_track(state, track_id)
    if not found:
        raise HTTPException(404, f"Custom track not found: {track_id}")
    _save(state)
    return {"status": "ok", "state": state}

# ── Estate (Laurel of Olympus RPG) ─────────────────────────────────────────────

ESTATE_SAVE = Path.home() / ".laurel_of_olympus.json"

@app.get("/api/estate/state")
def get_estate_state():
    return gs.load(ESTATE_SAVE).to_dict()

@app.post("/api/estate/simulate-workout")
async def estate_simulate_workout(req: Request):
    p = await req.json()
    workout_type = p.get("workout_type", "strength")
    kwargs = {k: v for k, v in p.items() if k != "workout_type"}
    # Provide sensible defaults so the call always succeeds
    if workout_type == "strength" and "volume" not in kwargs:
        kwargs["volume"] = 5000.0
    elif workout_type in ("walking", "running", "rucking") and "miles" not in kwargs:
        kwargs["miles"] = 2.0

    state = gs.load(ESTATE_SAVE)

    # ── Compute passive buffs from sanctuary + relics ────────────────────────
    buffs = buff_engine.get_all_buffs(state)

    events = workout_engine.process_workout(state, workout_type, buffs=buffs, **kwargs)

    # Consume Hermes blessing after a run (MISS-4)
    if buffs.get("blessing_hermes") and workout_type == "running":
        state.active_blessings["hermes"] = max(0, state.active_blessings.get("hermes", 1) - 1)
        events.append("  🪶 Blessing of Hermes consumed.")

    farm_events = farm_engine.produce_farms(state, buffs=buffs)
    events.extend(farm_events)

    # Consume Demeter blessing after farm production (MISS-4)
    if buffs.get("blessing_demeter") and farm_events and "No farms" not in farm_events[0]:
        state.active_blessings["demeter"] = max(0, state.active_blessings.get("demeter", 1) - 1)
        events.append("  🌾 Blessing of Demeter consumed.")

    # ── Title checks (run before event priority chain) ───────────────────────
    newly_unlocked = title_engine.check_and_unlock_titles(state)
    for tid in newly_unlocked:
        events.append(f"  🏅 Title unlocked: {tid.replace('_', ' ').title()}")

    # ── Creature encounter (outdoor workouts only, 5% base) ──────────────────
    encounter_chance = buff_engine.effective_event_chance(buffs, 0.05)
    creature_encounter = creature_engine.maybe_creature_encounter(
        workout_type, chance=encounter_chance
    )

    # ── Event priority chain (only one popup per workout) ────────────────────
    # 1. Ultra-rare: Kassandra Breaks Composure (0.1%, phase ≥ 4)
    narrative_event = oracle_engine.maybe_kassandra_break(state, chance=0.001)
    if narrative_event:
        # Kassandra break also unlocks "favorite_of_kassandra"
        if "favorite_of_kassandra" not in state.titles_unlocked:
            state.titles_unlocked.append("favorite_of_kassandra")
            state.active_titles["legendary"] = "favorite_of_kassandra"
            events.append("  🌟 Title unlocked: Favorite of Kassandra")
    else:
        # 2. Army unlock narrative — one-time hint when conditions are first met
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
        # 3. Oracle visit (10%)
        if narrative_event is None:
            narrative_event = oracle_engine.maybe_oracle_visit(state, chance=0.10)
        if narrative_event is None:
            # 4. Regular flavour event — base 20% + event_chance buff
            flavour_chance = buff_engine.effective_event_chance(buffs, 0.20)
            narrative_event = event_engine.maybe_trigger_event(
                state.to_dict(), chance=flavour_chance
            )

    # ── Relic discovery via events (MISS-6): 3% base chance ─────────────────
    relic_find = None
    import random as _random
    relic_chance = buff_engine.effective_event_chance(buffs, 0.03)
    if _random.random() < relic_chance:
        candidate = relic_engine.roll_relic_reward()
        if candidate:
            ok_r, _ = relic_engine.add_relic(state, candidate["id"])
            if ok_r:
                relic_find = candidate
            else:
                relic_find = {**candidate, "not_added": True}

    gs.save(state, ESTATE_SAVE)
    return {
        "status":             "ok",
        "events":             events,
        "state":              state.to_dict(),
        "event":              narrative_event,       # None or event dict
        "creature_encounter": creature_encounter,    # None or creature dict
        "relic_find":         relic_find,            # None or relic dict (MISS-6)
    }


@app.get("/api/estate/prophecy")
def get_prophecy_scroll():
    """Return the full Prophecy Scroll payload (titles + oracle phase + combined title)."""
    state = gs.load(ESTATE_SAVE)
    scroll = title_engine.get_prophecy_scroll(state)
    gs.save(state, ESTATE_SAVE)  # persist any newly unlocked titles
    return scroll


# ── Creature / Sanctuary endpoints ─────────────────────────────────────────────

@app.get("/api/estate/sanctuary")
def get_sanctuary():
    """Return sanctuary contents and all creature definitions."""
    state = gs.load(ESTATE_SAVE)
    return {
        "sanctuary":          creature_engine.get_sanctuary_details(state),
        "capacity":           state.sanctuary_capacity,
        "sanctuary_ids":      state.sanctuary,
        "all_creatures":      creature_engine.get_all_creatures(),
        "buffs":              creature_engine.get_sanctuary_buffs(state),
    }


@app.post("/api/estate/creature/recruit")
async def recruit_creature(req: Request):
    p = await req.json()
    creature_id = p.get("creature_id", "").strip()
    if not creature_id:
        raise HTTPException(400, "creature_id is required")
    state = gs.load(ESTATE_SAVE)
    ok, msg = creature_engine.recruit_creature(state, creature_id)
    if not ok:
        raise HTTPException(400, msg)
    gs.save(state, ESTATE_SAVE)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}


@app.post("/api/estate/creature/release")
async def release_creature(req: Request):
    p = await req.json()
    creature_id = p.get("creature_id", "").strip()
    if not creature_id:
        raise HTTPException(400, "creature_id is required")
    state = gs.load(ESTATE_SAVE)
    ok, msg, reward = creature_engine.release_creature(state, creature_id)
    if not ok:
        raise HTTPException(400, msg)
    gs.save(state, ESTATE_SAVE)
    return {"status": "ok", "msg": msg, "reward": reward, "state": state.to_dict()}


# ── Relic endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/estate/relics")
def get_relics():
    """Return relic inventory and all relic definitions."""
    state = gs.load(ESTATE_SAVE)
    return {
        "inventory":     relic_engine.get_inventory_details(state),
        "capacity":      state.relic_capacity,
        "relic_ids":     state.relics,
        "all_relics":    relic_engine.get_all_relics(),
        "buffs":         relic_engine.get_relic_buffs(state),
    }


@app.post("/api/estate/relic/add")
async def add_relic(req: Request):
    p = await req.json()
    relic_id = p.get("relic_id", "").strip()
    if not relic_id:
        raise HTTPException(400, "relic_id is required")
    state = gs.load(ESTATE_SAVE)
    ok, msg = relic_engine.add_relic(state, relic_id)
    if not ok:
        raise HTTPException(400, msg)
    gs.save(state, ESTATE_SAVE)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}


@app.post("/api/estate/relic/remove")
async def remove_relic(req: Request):
    p = await req.json()
    relic_id = p.get("relic_id", "").strip()
    if not relic_id:
        raise HTTPException(400, "relic_id is required")
    state = gs.load(ESTATE_SAVE)
    ok, msg = relic_engine.remove_relic(state, relic_id)
    if not ok:
        raise HTTPException(400, msg)
    gs.save(state, ESTATE_SAVE)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}

# ── Army / Barracks endpoints ───────────────────────────────────────────────────

@app.get("/api/estate/army")
def get_army():
    """Return army details, all unit defs, all regions, barracks status, strength."""
    state = gs.load(ESTATE_SAVE)
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
    state = gs.load(ESTATE_SAVE)
    ok, msg = army_engine.build_barracks(state)
    if not ok:
        raise HTTPException(400, msg)
    gs.save(state, ESTATE_SAVE)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}


@app.post("/api/estate/army/recruit")
async def recruit_unit(req: Request):
    p = await req.json()
    unit_id = p.get("unit_id", "").strip()
    if not unit_id:
        raise HTTPException(400, "unit_id is required")
    state = gs.load(ESTATE_SAVE)
    ok, msg = army_engine.recruit_unit(state, unit_id)
    if not ok:
        raise HTTPException(400, msg)
    gs.save(state, ESTATE_SAVE)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}


@app.post("/api/estate/army/disband")
async def disband_unit(req: Request):
    p = await req.json()
    unit_id = p.get("unit_id", "").strip()
    if not unit_id:
        raise HTTPException(400, "unit_id is required")
    state = gs.load(ESTATE_SAVE)
    ok, msg = army_engine.disband_unit(state, unit_id)
    if not ok:
        raise HTTPException(400, msg)
    gs.save(state, ESTATE_SAVE)
    return {"status": "ok", "msg": msg, "state": state.to_dict()}


@app.post("/api/estate/campaign/launch")
async def launch_campaign(req: Request):
    p = await req.json()
    region_id = p.get("region_id", "").strip()
    if not region_id:
        raise HTTPException(400, "region_id is required")

    state = gs.load(ESTATE_SAVE)
    buffs = buff_engine.get_all_buffs(state)

    result = army_engine.launch_campaign(state, region_id, buffs=buffs)

    # If engine returned an error string, propagate as 400
    if "error" in result:
        raise HTTPException(400, result["error"])

    # Consume Ares blessing after any campaign attempt (MISS-4)
    if buffs.get("blessing_ares"):
        state.active_blessings["ares"] = max(0, state.active_blessings.get("ares", 1) - 1)

    # Auto-add relic reward to inventory if found and space available
    if result.get("relic_reward"):
        relic_id = result["relic_reward"]["id"]
        ok_relic, _ = relic_engine.add_relic(state, relic_id)
        if not ok_relic:
            # Inventory full — mark relic as not added so frontend can inform player
            result["relic_reward"]["not_added"] = True

    # MISS-5: Award laurel on victory (~15% chance)
    import random as _random
    if result.get("victory") and _random.random() < 0.15:
        state.laurels += 1
        result["laurel_earned"] = 1
        # Re-run title checks — campaign laurel may unlock a consistency title
        newly_t = title_engine.check_and_unlock_titles(state)
        if newly_t:
            result["titles_unlocked"] = newly_t

    # Award champion_of_the_gods title if 20 campaigns won
    if (
        state.campaigns_won >= 20
        and "champion_of_the_gods" not in state.titles_unlocked
    ):
        state.titles_unlocked.append("champion_of_the_gods")
        state.active_titles["legendary"] = "champion_of_the_gods"
        result["title_unlocked"] = "Champion of the Gods"

    gs.save(state, ESTATE_SAVE)

    # creature_reward (if any) is returned to the frontend as an encounter dict;
    # the frontend shows the encounter dialog so the player can recruit or release.
    return {
        "status":           "ok",
        "result":           result,
        "creature_encounter": result.get("creature_reward"),
        "state":            state.to_dict(),
    }


# ── Farm build / upgrade endpoints (MISS-1) ────────────────────────────────

@app.get("/api/estate/farm-types")
def get_farm_types():
    """Return all farm type definitions with costs."""
    return {"farm_types": farm_engine.get_all_farm_types()}


@app.post("/api/estate/farm/build")
async def build_farm(req: Request):
    p = await req.json()
    farm_type = p.get("farm_type", "").strip()
    col = int(p.get("col", 0))
    row = int(p.get("row", 0))
    if not farm_type:
        raise HTTPException(400, "farm_type is required")
    state = gs.load(ESTATE_SAVE)
    ok, msg = farm_engine.build_farm(state, farm_type, col, row)
    if ok:
        title_engine.check_and_unlock_titles(state)
        gs.save(state, ESTATE_SAVE)
    return {"status": "ok" if ok else "error", "message": msg, "state": state.to_dict()}


@app.post("/api/estate/farm/upgrade")
async def upgrade_farm(req: Request):
    p = await req.json()
    col = int(p.get("col", 0))
    row = int(p.get("row", 0))
    state = gs.load(ESTATE_SAVE)
    ok, msg = farm_engine.upgrade_farm(state, col, row)
    if ok:
        gs.save(state, ESTATE_SAVE)
    return {"status": "ok" if ok else "error", "message": msg, "state": state.to_dict()}


# ── Processing building endpoints (MISS-2) ────────────────────────────────

@app.get("/api/estate/processing")
def get_processing():
    """Return processing buildings status."""
    state = gs.load(ESTATE_SAVE)
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
    state = gs.load(ESTATE_SAVE)
    ok, msg = processing_engine.build_processing_building(state, building_id)
    if ok:
        gs.save(state, ESTATE_SAVE)
    return {"status": "ok" if ok else "error", "message": msg, "state": state.to_dict()}


@app.post("/api/estate/processing/process")
async def process_goods(req: Request):
    p = await req.json()
    building_id = p.get("building_id", "").strip()
    amount = int(p.get("amount", 1))
    if not building_id:
        raise HTTPException(400, "building_id is required")
    state = gs.load(ESTATE_SAVE)
    ok, msg, detail = processing_engine.process_goods(state, building_id, amount)
    if ok:
        title_engine.check_and_unlock_titles(state)
        gs.save(state, ESTATE_SAVE)
    return {
        "status":  "ok" if ok else "error",
        "message": msg,
        "detail":  detail,
        "state":   state.to_dict(),
    }


# ── Villa upgrade endpoint (MISS-3) ───────────────────────────────────────

@app.get("/api/estate/villa")
def get_villa():
    """Return villa level and upgrade cost."""
    import json as _json
    state = gs.load(ESTATE_SAVE)
    level = getattr(state, "villa_level", 1)
    next_cost = army_engine.VILLA_UPGRADE_COSTS.get(level + 1)
    return {
        "villa_level":     level,
        "max_level":       3,
        "upgrade_cost":    next_cost,
        "army_limit":      state.army_limit,
        "barracks_unlock": {
            "laurels_needed":  3,
            "farms_needed":    3,
            "villa_level_needed": 2,
            "laurels_have":    state.laurels,
            "farms_have":      len(state.farms),
            "villa_have":      level,
            "unlocked":        (state.laurels >= 3 and len(state.farms) >= 3 and level >= 2),
        },
    }


@app.post("/api/estate/villa/upgrade")
async def upgrade_villa(req: Request):
    state = gs.load(ESTATE_SAVE)
    ok, msg = army_engine.upgrade_villa(state)
    if ok:
        gs.save(state, ESTATE_SAVE)
    return {"status": "ok" if ok else "error", "message": msg, "state": state.to_dict()}


# ── Blessings endpoints (MISS-4) ─────────────────────────────────────────

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
    state = gs.load(ESTATE_SAVE)
    active = getattr(state, "active_blessings", {})
    result = []
    for b in _BLESSINGS.values():
        result.append({
            **b,
            "active": active.get(b["id"], 0) > 0,
            "remaining": active.get(b["id"], 0),
        })
    return {"blessings": result, "laurels": state.laurels}


@app.post("/api/estate/blessing/activate")
async def activate_blessing(req: Request):
    p = await req.json()
    blessing_id = p.get("blessing_id", "").strip()
    if blessing_id not in _BLESSINGS:
        raise HTTPException(400, f"Unknown blessing: {blessing_id}")
    state = gs.load(ESTATE_SAVE)
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
    gs.save(state, ESTATE_SAVE)
    return {
        "status":  "ok",
        "message": f"{b['icon']} {b['name']} activated! {b['effect']}",
        "state":   state.to_dict(),
    }
