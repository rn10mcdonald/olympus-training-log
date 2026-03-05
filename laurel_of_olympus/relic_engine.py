"""
relic_engine.py – Relic inventory management and buff computation.

Relics are loaded from data/relics.json (new schema).
Relics provide passive bonuses applied to farms and workouts.

Public API:
  add_relic(state, relic_id) -> tuple[bool, str]
      Add a relic to the player's inventory (no duplicates, capacity check).
      Returns (success, message).

  remove_relic(state, relic_id) -> tuple[bool, str]
      Remove a relic from the player's inventory.
      Returns (success, message).

  get_relic_buffs(state) -> dict
      Compute combined buff multipliers/bonuses from all held relics.
      Same key format as creature_engine.get_sanctuary_buffs().

  describe_effect(effect) -> str
      Human-readable description of an effect dict.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from laurel_of_olympus.game_state import PlayerState

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
_DATA_DIR  = Path(__file__).parent / "data"
_RELICS: List[dict] = json.loads((_DATA_DIR / "relics.json").read_text())
_RELIC_MAP: Dict[str, dict] = {r["id"]: r for r in _RELICS}

RELIC_CAPACITY = 5   # max relics a player can carry

RARITY_ICONS = {
    "common":    "🌿",
    "rare":      "⚡",
    "epic":      "🔥",
    "legendary": "✨",
}


# ---------------------------------------------------------------------------
# Inventory CRUD
# ---------------------------------------------------------------------------

def add_relic(state: PlayerState, relic_id: str) -> Tuple[bool, str]:
    """
    Add a relic to the inventory.
    Returns (success, message).
    """
    if relic_id not in _RELIC_MAP:
        return False, f"Unknown relic: {relic_id}"
    if relic_id in state.relics:
        return False, "You already possess this relic."
    if len(state.relics) >= state.relic_capacity:
        return False, (
            f"Relic inventory is full ({state.relic_capacity}/{state.relic_capacity}). "
            "Discard a relic to make room."
        )
    state.relics.append(relic_id)
    name = _RELIC_MAP[relic_id]["name"]
    return True, f"Relic acquired: {name}."


def remove_relic(state: PlayerState, relic_id: str) -> Tuple[bool, str]:
    """
    Remove a relic from the inventory.
    Returns (success, message).
    """
    if relic_id not in state.relics:
        return False, "That relic is not in your inventory."
    state.relics.remove(relic_id)
    name = _RELIC_MAP.get(relic_id, {}).get("name", relic_id)
    return True, f"{name} discarded."


# ---------------------------------------------------------------------------
# Buff computation
# ---------------------------------------------------------------------------

def get_relic_buffs(state: PlayerState) -> dict:
    """
    Aggregate buff multipliers/bonuses from all held relics.
    Same key format as creature_engine.get_sanctuary_buffs().
    """
    buffs: dict = {}
    for relic_id in state.relics:
        relic = _RELIC_MAP.get(relic_id)
        if not relic:
            continue
        effect = relic.get("effect", {})
        _merge_effect(buffs, effect)
    return buffs


def _merge_effect(buffs: dict, effect: dict) -> None:
    """Merge one effect dict into the running buffs accumulator."""
    etype = effect.get("type", "")
    mult  = float(effect.get("multiplier", 1.0))
    bonus = float(effect.get("bonus", 0.0))

    if etype == "farm_bonus":
        farm = effect.get("farm")
        if farm:
            key = f"farm_{farm}"
            buffs[key] = buffs.get(key, 1.0) * mult
        else:
            # No specific farm → applies to all farms
            buffs["all_farms"] = buffs.get("all_farms", 1.0) * mult

    elif etype == "workout_bonus":
        workout = effect.get("workout", "")
        if workout:
            key = f"workout_{workout}"
            buffs[key] = buffs.get(key, 1.0) * mult

    elif etype == "event_chance":
        buffs["event_chance"] = buffs.get("event_chance", 0.0) + bonus

    elif etype == "laurel_bonus":
        buffs["laurel_bonus"] = buffs.get("laurel_bonus", 0) + int(bonus)

    else:
        # army_defense and other future types stored for reference
        if mult != 1.0:
            buffs[etype] = buffs.get(etype, 1.0) * mult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_all_relics() -> List[dict]:
    """Return all relics with enriched display fields."""
    return [_enrich(r) for r in _RELICS]


def get_inventory_details(state: PlayerState) -> List[dict]:
    """Return enriched dicts for all relics in the player's inventory."""
    return [_enrich(_RELIC_MAP[rid]) for rid in state.relics if rid in _RELIC_MAP]


def _enrich(relic: dict) -> dict:
    rarity = relic.get("rarity", "common")
    return {
        **relic,
        "icon":       RARITY_ICONS.get(rarity, "🔮"),
        "buff_label": describe_effect(relic.get("effect", {})),
    }


def describe_effect(effect: dict) -> str:
    """Return a short human-readable buff description."""
    etype = effect.get("type", "")
    mult  = effect.get("multiplier", 1.0)
    bonus = effect.get("bonus", 0)
    pct   = round((float(mult) - 1.0) * 100)

    if etype == "farm_bonus":
        farm = effect.get("farm", "").replace("_", " ")
        return f"+{pct}% {farm} production" if farm else f"+{pct}% all farm production"
    if etype == "workout_bonus":
        workout = effect.get("workout", "workout")
        return f"+{pct}% {workout} drachmae"
    if etype == "event_chance":
        return f"+{round(float(bonus) * 100)}% event chance"
    if etype == "laurel_bonus":
        n = int(bonus)
        return f"+{n} bonus laurel{'s' if n != 1 else ''} per streak"
    if etype == "army_defense":
        return f"+{pct}% army defense (future)"
    return "Passive bonus"
