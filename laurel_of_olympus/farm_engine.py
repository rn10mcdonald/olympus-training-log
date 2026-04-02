"""
farm_engine.py – Farm construction, upgrading, and daily resource production.

Key rule (balance_table.txt):
    Farms produce ONCE per day when the player completes their FIRST workout.
    Additional workouts on the same day do NOT trigger additional production.

Public API:
    get_all_farm_types() -> list[dict]
        Return all farm type definitions from farms.json.

    build_farm(state, farm_type, col, row) -> (bool, str)
        Construct a new farm on the estate grid.
        Deducts the build_cost from state.drachmae.

    upgrade_farm(state, col, row) -> (bool, str)
        Upgrade an existing farm tile to the next level.
        Deducts the upgrade_cost from state.drachmae.

    produce_farms(state, buffs=None) -> list[str]
        Checks whether production should run today, runs it if so,
        returns list of event strings.
        buffs: optional dict from buff_engine.get_all_buffs(state) — applies
               "farm_{farm_type}" and "all_farms" multipliers to production.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from laurel_of_olympus.game_state import PlayerState

# ---------------------------------------------------------------------------
# Load farms.json for build / upgrade costs
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent / "data"
_FARMS_RAW: List[dict] = json.loads((_DATA_DIR / "farms.json").read_text())
_FARM_TYPE_MAP: Dict[str, dict] = {f["id"]: f for f in _FARMS_RAW}

# ---------------------------------------------------------------------------
# Production tables (balance_table.txt)
# Resource produced per level: index 0 = L1, 1 = L2, 2 = L3
# ---------------------------------------------------------------------------
_PRODUCTION: Dict[str, List[int]] = {
    "grain_field":  [2, 3, 4],
    "vineyard":     [2, 3, 4],
    "olive_grove":  [2, 3, 4],
    "apiary":       [1, 2, 3],
    "herb_garden":  [2, 3, 4],
}

_RESOURCE_FIELD: Dict[str, str] = {
    "grain_field":  "grain",
    "vineyard":     "grapes",
    "olive_grove":  "olives",
    "apiary":       "honey",
    "herb_garden":  "herbs",
}


def should_produce_today(state: PlayerState, today: Optional[str] = None) -> bool:
    """Return True if farms haven't produced today yet.

    today: caller's local date string (YYYY-MM-DD). Falls back to server date
    if not provided — pass the client's local date to avoid UTC/local mismatch.
    """
    today = today or str(dt.date.today())
    return state.last_farm_date != today


def produce_farms(
    state: PlayerState, buffs: Optional[dict] = None, today: Optional[str] = None
) -> Tuple[List[str], Dict[str, int]]:
    """
    Run farm production if this is the first workout of the day.
    Mutates state's resource fields and last_farm_date.
    Returns (event_strings, produced_dict) where produced_dict maps
    resource name → total amount produced (empty dict if nothing produced).

    buffs: dict from buff_engine.get_all_buffs(state).  Keys used:
        "farm_{farm_type}" – multiplier for a specific farm type
        "all_farms"        – multiplier applied to every farm

    today: caller's local date string (YYYY-MM-DD). Falls back to server date.
    """
    today = today or str(dt.date.today())
    if not should_produce_today(state, today):
        return [], {}

    if not state.farms:
        return [], {}

    events: List[str] = []
    state.last_farm_date = today
    buffs = buffs or {}

    produced: Dict[str, int] = {}
    buffed: Dict[str, int]   = {}   # track buff contribution for log

    for farm in state.farms:
        farm_type = farm["farm_type"]
        level = max(1, min(farm.get("level", 1), 3))  # clamp to 1-3

        prod_table = _PRODUCTION.get(farm_type)
        resource_field = _RESOURCE_FIELD.get(farm_type)

        if prod_table is None or resource_field is None:
            continue  # Unknown farm type — skip silently

        base   = prod_table[level - 1]
        # Apply sanctuary + relic multipliers
        specific = buffs.get(f"farm_{farm_type}", 1.0)
        all_farm = buffs.get("all_farms", 1.0)
        amount   = max(base, round(base * specific * all_farm))
        bonus    = amount - base

        # Mutate state
        current = getattr(state, resource_field, 0)
        setattr(state, resource_field, current + amount)

        produced[resource_field] = produced.get(resource_field, 0) + amount
        if bonus > 0:
            buffed[resource_field] = buffed.get(resource_field, 0) + bonus

    if produced:
        parts = [f"+{v} {k}" for k, v in sorted(produced.items())]
        msg   = f"🌾 Harvest: {', '.join(parts)}"
        if buffed:
            bonus_parts = [f"+{v} {k} (bonus)" for k, v in sorted(buffed.items())]
            msg += f"  ✨ {', '.join(bonus_parts)}"
        events.append(msg)

    return events, produced


# ---------------------------------------------------------------------------
# Farm construction and upgrading
# ---------------------------------------------------------------------------

def get_all_farm_types() -> List[dict]:
    """Return all farm type definitions from farms.json."""
    return list(_FARMS_RAW)


def build_farm(
    state: PlayerState, farm_type: str, col: int, row: int
) -> Tuple[bool, str]:
    """
    Construct a new farm on the estate grid.
    Deducts the build_cost (drachmae) from state.drachmae.
    Returns (success, message).
    """
    farm_def = _FARM_TYPE_MAP.get(farm_type)
    if not farm_def:
        return False, f"Unknown farm type: {farm_type}"

    # Prevent duplicate tiles at the same grid position
    for f in state.farms:
        if f.get("col") == col and f.get("row") == row:
            return False, "That plot is already occupied."

    build_cost = farm_def["levels"][0]["build_cost"]
    if build_cost is None:
        return False, f"Cannot build {farm_def['name']} directly."

    if state.drachmae < build_cost:
        return False, (
            f"Need {build_cost} drachmae to build a {farm_def['name']} "
            f"(have {state.drachmae:.0f})."
        )

    state.drachmae = round(state.drachmae - build_cost, 2)
    state.farms.append({
        "farm_type": farm_type,
        "level":     1,
        "col":       col,
        "row":       row,
    })
    return True, f"{farm_def['icon']} {farm_def['name']} built!"


def upgrade_farm(
    state: PlayerState, col: int, row: int
) -> Tuple[bool, str]:
    """
    Upgrade the farm at (col, row) to the next level.
    Deducts the upgrade_cost (drachmae) from state.drachmae.
    Returns (success, message).
    """
    # Find the farm at this position
    target = next(
        (f for f in state.farms if f.get("col") == col and f.get("row") == row),
        None,
    )
    if target is None:
        return False, "No farm found at that location."

    farm_def = _FARM_TYPE_MAP.get(target["farm_type"])
    if not farm_def:
        return False, "Unknown farm type."

    current_level = target.get("level", 1)
    if current_level >= 3:
        return False, f"{farm_def['name']} is already at maximum level."

    next_level_def = farm_def["levels"][current_level]  # index = current level (0-based)
    upgrade_cost = next_level_def.get("upgrade_cost")
    if upgrade_cost is None:
        return False, "No upgrade available for this farm."

    if state.drachmae < upgrade_cost:
        return False, (
            f"Need {upgrade_cost} drachmae to upgrade (have {state.drachmae:.0f})."
        )

    state.drachmae = round(state.drachmae - upgrade_cost, 2)
    target["level"] = current_level + 1
    return True, (
        f"{farm_def['icon']} {farm_def['name']} upgraded to level {target['level']}!"
    )
