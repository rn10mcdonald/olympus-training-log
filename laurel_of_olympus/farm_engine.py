"""
farm_engine.py – Daily farm resource production.

Key rule (balance_table.txt):
    Farms produce ONCE per day when the player completes their FIRST workout.
    Additional workouts on the same day do NOT trigger additional production.

Public API:
    produce_farms(state, buffs=None) -> list[str]
        Checks whether production should run today, runs it if so,
        returns list of event strings.
        buffs: optional dict from buff_engine.get_all_buffs(state) — applies
               "farm_{farm_type}" and "all_farms" multipliers to production.
"""

from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional

from laurel_of_olympus.game_state import PlayerState

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


def should_produce_today(state: PlayerState) -> bool:
    """Return True if farms haven't produced today yet."""
    return state.last_farm_date != str(dt.date.today())


def produce_farms(state: PlayerState, buffs: Optional[dict] = None) -> List[str]:
    """
    Run farm production if this is the first workout of the day.
    Mutates state's resource fields and last_farm_date.
    Returns event strings for the log.

    buffs: dict from buff_engine.get_all_buffs(state).  Keys used:
        "farm_{farm_type}" – multiplier for a specific farm type
        "all_farms"        – multiplier applied to every farm
    """
    if not should_produce_today(state):
        return []

    if not state.farms:
        return []

    events: List[str] = []
    state.last_farm_date = str(dt.date.today())
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
        msg   = f"[Farm harvest] {', '.join(parts)}"
        if buffed:
            bonus_parts = [f"+{v} {k} (creature/relic)" for k, v in sorted(buffed.items())]
            msg += f"  ✨ {', '.join(bonus_parts)}"
        events.append(msg)
    else:
        events.append("[Farm harvest] No farms built yet.")

    return events
