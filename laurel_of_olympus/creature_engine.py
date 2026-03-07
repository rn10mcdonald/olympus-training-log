"""
creature_engine.py – Creature encounters, Sanctuary management, and buff computation.

Creatures are loaded from data/creatures.json (new nested schema).
Spawn chance and rarity probabilities are loaded from data/rarity_tables.json.
Encounters fire randomly after outdoor workouts (walking / running / rucking).

Public API:
  maybe_creature_encounter(workout_type, chance=None) -> dict | None
      Two-stage roll: spawn chance → rarity roll → filter by rarity → pick one.
      Returns full creature dict (with icon/release_reward/buff_label) or None.
      Only fires on outdoor workout types.

  recruit_creature(state, creature_id) -> tuple[bool, str]
      Add a creature to the sanctuary.
      Returns (success, message).

  release_creature(state, creature_id) -> tuple[bool, str, float]
      Remove a creature from the sanctuary and award drachmae.
      Returns (success, message, drachmae_earned).

  get_sanctuary_buffs(state) -> dict
      Compute combined buff multipliers from all sanctuary creatures.
      Key format:
        "all_farms"         -> float multiplier (farm_production buff_type)
        "workout_all"       -> float multiplier (drachmae_gain / all_rewards)
        "workout_running"   -> float multiplier (running_rewards)
        "workout_strength"  -> float multiplier (strength_rewards)
        "event_chance"      -> float additive bonus
        "rare_event_chance" -> float additive bonus (rare_events)
        "army_strength"     -> float multiplier (future)
        "campaign_rewards"  -> float multiplier (future)

  get_all_creatures() -> list[dict]
      Return all creatures with enriched display fields.

  get_sanctuary_details(state) -> list[dict]
      Return enriched dicts for all creatures currently in the sanctuary.

  describe_buff(buff_type, buff_value) -> str
      Human-readable description of a creature/relic buff.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from laurel_of_olympus.game_state import PlayerState

# ---------------------------------------------------------------------------
# Load data files once at import time
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent / "data"

_RAW            = json.loads((_DATA_DIR / "creatures.json").read_text())
_CREATURES: List[dict] = _RAW["creatures"]
_CREATURE_MAP: Dict[str, dict] = {c["id"]: c for c in _CREATURES}

_RARITY_TABLES  = json.loads((_DATA_DIR / "rarity_tables.json").read_text())

# Index creatures by rarity for fast lookup
_CREATURES_BY_RARITY: Dict[str, List[dict]] = {}
for _c in _CREATURES:
    _r = _c.get("rarity", "common")
    _CREATURES_BY_RARITY.setdefault(_r, []).append(_c)

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
# Rarity roll helper
# ---------------------------------------------------------------------------

def _roll_rarity(rolls: List[dict]) -> str:
    """
    Weighted random rarity selection from a probability table.
    Each entry: {"rarity": str, "probability": float}.
    Probabilities need not sum to exactly 1.0 — the last tier is the fallback.
    """
    r = random.random()
    cumulative = 0.0
    for entry in rolls:
        cumulative += entry["probability"]
        if r < cumulative:
            return entry["rarity"]
    return rolls[-1]["rarity"]  # fallback (handles floating-point edge cases)


# ---------------------------------------------------------------------------
# Encounter
# ---------------------------------------------------------------------------

def maybe_creature_encounter(
    workout_type: str, chance: Optional[float] = None
) -> Optional[dict]:
    """
    Two-stage roll for a creature encounter after an outdoor workout:
      1. Roll creature_spawn_chance (loaded from rarity_tables.json).
      2. If spawn fires, roll creature_rarity_rolls to select a rarity tier.
      3. Filter _CREATURES by that rarity and pick one at random.

    Args:
        workout_type: Must be in OUTDOOR_WORKOUT_TYPES to be eligible.
        chance:       Override spawn chance; if None, uses rarity_tables.json value.

    Returns:
        Enriched creature dict or None.
    """
    if workout_type not in OUTDOOR_WORKOUT_TYPES:
        return None

    spawn_chance = (
        chance
        if chance is not None
        else _RARITY_TABLES["creature_spawn_chance"]
    )
    if random.random() >= spawn_chance:
        return None

    # Roll rarity tier
    rarity = _roll_rarity(_RARITY_TABLES["creature_rarity_rolls"])

    # Pick a creature of that rarity (fall back to full pool if none exist)
    candidates = _CREATURES_BY_RARITY.get(rarity) or _CREATURES
    return _enrich(random.choice(candidates))


def _enrich(creature: dict) -> dict:
    """Add display-only fields to a creature dict."""
    rarity     = creature.get("rarity", "common")
    buff_type  = creature.get("buff_type", "")
    buff_value = float(creature.get("buff_value", 0.0))
    return {
        **creature,
        "icon":           RARITY_ICONS.get(rarity, "🐾"),
        "release_reward": RELEASE_REWARDS.get(rarity, 5.0),
        "buff_label":     describe_buff(buff_type, buff_value),
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

    buff_type → internal buff key mapping:
        farm_production   → all_farms          (multiplier)
        drachmae_gain     → workout_all         (multiplier)
        running_rewards   → workout_running     (multiplier)
        strength_rewards  → workout_strength    (multiplier)
        event_chance      → event_chance        (additive)
        all_rewards       → workout_all         (multiplier)
        rare_events       → rare_event_chance   (additive)
        army_strength     → army_strength       (multiplier, future)
        campaign_rewards  → campaign_rewards    (multiplier, future)
    """
    buffs: dict = {}
    for creature_id in state.sanctuary:
        creature = _CREATURE_MAP.get(creature_id)
        if not creature:
            continue
        buff_type  = creature.get("buff_type", "")
        buff_value = float(creature.get("buff_value", 0.0))
        _merge_buff(buffs, buff_type, buff_value)
    return buffs


def _merge_buff(buffs: dict, buff_type: str, buff_value: float) -> None:
    """Merge one buff_type/buff_value pair into the running buffs accumulator."""
    mult = 1.0 + buff_value  # e.g. buff_value=0.10 → 10 % boost

    if buff_type == "farm_production":
        buffs["all_farms"] = buffs.get("all_farms", 1.0) * mult

    elif buff_type in ("drachmae_gain", "all_rewards"):
        buffs["workout_all"] = buffs.get("workout_all", 1.0) * mult

    elif buff_type == "running_rewards":
        buffs["workout_running"] = buffs.get("workout_running", 1.0) * mult

    elif buff_type == "strength_rewards":
        buffs["workout_strength"] = buffs.get("workout_strength", 1.0) * mult

    elif buff_type == "event_chance":
        buffs["event_chance"] = buffs.get("event_chance", 0.0) + buff_value

    elif buff_type == "rare_events":
        buffs["rare_event_chance"] = buffs.get("rare_event_chance", 0.0) + buff_value

    else:
        # army_strength, campaign_rewards → stored for future use
        buffs[buff_type] = buffs.get(buff_type, 1.0) * mult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_all_creatures() -> List[dict]:
    """Return all creatures with enriched display fields."""
    return [_enrich(c) for c in _CREATURES]


def get_sanctuary_details(state: PlayerState) -> List[dict]:
    """Return enriched dicts for all creatures currently in the sanctuary."""
    return [_enrich(_CREATURE_MAP[cid]) for cid in state.sanctuary if cid in _CREATURE_MAP]


def describe_buff(buff_type: str, buff_value: float) -> str:
    """Return a short human-readable buff description from buff_type + buff_value."""
    pct = round(buff_value * 100)
    labels = {
        "farm_production":  f"+{pct}% farm production",
        "drachmae_gain":    f"+{pct}% all drachmae",
        "running_rewards":  f"+{pct}% running drachmae",
        "strength_rewards": f"+{pct}% strength drachmae",
        "event_chance":     f"+{pct}% event chance",
        "all_rewards":      f"+{pct}% all rewards",
        "rare_events":      f"+{pct}% rare event chance",
        "army_strength":    f"+{pct}% army strength",
        "campaign_rewards": f"+{pct}% campaign rewards",
    }
    return labels.get(buff_type, f"+{pct}% passive bonus")
