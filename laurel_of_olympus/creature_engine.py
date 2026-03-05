"""
creature_engine.py – Creature encounters, Sanctuary management, and buff computation.

Creatures are loaded from data/creatures.json (new schema).
Encounters fire randomly after outdoor workouts (walking / running / rucking).

Public API:
  maybe_creature_encounter(workout_type, chance=0.05) -> dict | None
      Roll for a creature encounter.  Returns full creature dict or None.
      Only fires on outdoor workout types.

  recruit_creature(state, creature_id) -> tuple[bool, str]
      Add a creature to the sanctuary.
      Returns (success, message).

  release_creature(state, creature_id) -> tuple[bool, str, float]
      Remove a creature from the sanctuary and award drachmae.
      Returns (success, message, drachmae_earned).

  get_sanctuary_buffs(state) -> dict
      Compute combined buff multipliers from all sanctuary creatures.
      Key format: "farm_{farm_type}", "all_farms", "workout_{workout_type}",
                  "event_chance" (additive float), "army_strength" (future).

  describe_effect(effect) -> str
      Human-readable description of an effect dict.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from laurel_of_olympus.game_state import PlayerState

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent / "data"
_CREATURES: List[dict] = json.loads((_DATA_DIR / "creatures.json").read_text())
_CREATURE_MAP: Dict[str, dict] = {c["id"]: c for c in _CREATURES}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OUTDOOR_WORKOUT_TYPES = {"walking", "running", "rucking"}

RARITY_ICONS = {
    "common":    "🌿",
    "rare":      "⚡",
    "epic":      "🔥",
    "legendary": "✨",
}

RELEASE_REWARDS = {
    "common":    5.0,
    "rare":     10.0,
    "epic":     20.0,
    "legendary": 50.0,
}


# ---------------------------------------------------------------------------
# Encounter
# ---------------------------------------------------------------------------

def maybe_creature_encounter(
    workout_type: str, chance: float = 0.05
) -> Optional[dict]:
    """
    Roll for a creature encounter after an outdoor workout.
    Returns the full creature dict (with icon/release_reward injected) or None.
    """
    if workout_type not in OUTDOOR_WORKOUT_TYPES:
        return None
    if random.random() > chance:
        return None

    creature = random.choice(_CREATURES)
    return _enrich(creature)


def _enrich(creature: dict) -> dict:
    """Add display-only fields to a creature dict."""
    rarity = creature.get("rarity", "common")
    return {
        **creature,
        "icon":           RARITY_ICONS.get(rarity, "🐾"),
        "release_reward": RELEASE_REWARDS.get(rarity, 5.0),
        "buff_label":     describe_effect(creature.get("effect", {})),
    }


# ---------------------------------------------------------------------------
# Sanctuary CRUD
# ---------------------------------------------------------------------------

def recruit_creature(
    state: PlayerState, creature_id: str
) -> Tuple[bool, str]:
    """
    Add a creature to the sanctuary if there's space.
    Returns (success, message).
    """
    if creature_id not in _CREATURE_MAP:
        return False, f"Unknown creature: {creature_id}"
    if len(state.sanctuary) >= state.sanctuary_capacity:
        return False, (
            f"Sanctuary is full ({state.sanctuary_capacity}/{state.sanctuary_capacity}). "
            "Release a creature to make room."
        )
    if creature_id in state.sanctuary:
        return False, "That creature is already in your sanctuary."

    state.sanctuary.append(creature_id)
    name = _CREATURE_MAP[creature_id]["name"]
    return True, f"{name} welcomed into the sanctuary."


def release_creature(
    state: PlayerState, creature_id: str
) -> Tuple[bool, str, float]:
    """
    Release a creature from the sanctuary and award drachmae.
    Returns (success, message, drachmae_earned).
    """
    if creature_id not in state.sanctuary:
        return False, "That creature is not in your sanctuary.", 0.0

    state.sanctuary.remove(creature_id)
    creature = _CREATURE_MAP.get(creature_id, {})
    rarity   = creature.get("rarity", "common")
    reward   = RELEASE_REWARDS.get(rarity, 5.0)
    name     = creature.get("name", creature_id)

    state.drachmae = round(state.drachmae + reward, 2)
    return True, f"{name} released. +{reward:.0f} drachmae.", reward


# ---------------------------------------------------------------------------
# Buff computation
# ---------------------------------------------------------------------------

def get_sanctuary_buffs(state: PlayerState) -> dict:
    """
    Aggregate buff multipliers from all recruited creatures.

    Returns a dict where:
        "farm_{farm_type}" -> float multiplier  (e.g. "farm_vineyard": 1.10)
        "all_farms"        -> float multiplier
        "workout_{type}"   -> float multiplier  (e.g. "workout_running": 1.20)
        "event_chance"     -> float additive bonus (e.g. 0.05)
    Unrecognised / future effect types are stored under their raw type key.
    """
    buffs: dict = {}

    for creature_id in state.sanctuary:
        creature = _CREATURE_MAP.get(creature_id)
        if not creature:
            continue
        effect = creature.get("effect", {})
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
        else:
            key = "all_farms"
        buffs[key] = buffs.get(key, 1.0) * mult

    elif etype == "all_farm_bonus":
        buffs["all_farms"] = buffs.get("all_farms", 1.0) * mult

    elif etype == "workout_bonus":
        workout = effect.get("workout", "")
        if workout:
            key = f"workout_{workout}"
            buffs[key] = buffs.get(key, 1.0) * mult

    elif etype == "event_chance":
        buffs["event_chance"] = buffs.get("event_chance", 0.0) + bonus

    else:
        # Store future-use effect types for reference
        buffs[etype] = buffs.get(etype, 1.0) * mult if mult != 1.0 else buffs.get(etype, bonus)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_all_creatures() -> List[dict]:
    """Return all creatures with enriched display fields."""
    return [_enrich(c) for c in _CREATURES]


def get_sanctuary_details(state: PlayerState) -> List[dict]:
    """Return enriched dicts for all creatures currently in the sanctuary."""
    return [_enrich(_CREATURE_MAP[cid]) for cid in state.sanctuary if cid in _CREATURE_MAP]


def describe_effect(effect: dict) -> str:
    """Return a short human-readable buff description."""
    etype = effect.get("type", "")
    mult  = effect.get("multiplier", 1.0)
    bonus = effect.get("bonus", 0)
    pct   = round((float(mult) - 1.0) * 100)

    if etype == "farm_bonus":
        farm = effect.get("farm", "").replace("_", " ")
        return f"+{pct}% {farm} production" if farm else f"+{pct}% farm production"
    if etype == "all_farm_bonus":
        return f"+{pct}% all farm production"
    if etype == "workout_bonus":
        workout = effect.get("workout", "workout")
        return f"+{pct}% {workout} drachmae"
    if etype == "event_chance":
        return f"+{round(float(bonus) * 100)}% event chance"
    if etype == "estate_defense":
        return f"+{pct}% estate defense"
    if etype == "army_strength":
        return f"+{pct}% army strength (future)"
    return "Passive estate bonus"
