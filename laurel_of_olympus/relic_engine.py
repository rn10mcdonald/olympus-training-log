"""
relic_engine.py – Relic inventory management and buff computation.

Relics are loaded from data/relics.json (new nested schema).
Relic rarity probabilities are loaded from data/rarity_tables.json.
Capacity is read from relics.json["inventory"]["max_relics"].

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

  roll_relic_reward() -> dict
      Roll a random relic using relic_rarity_rolls probability table.
      Returns an enriched relic dict.

  get_all_relics() -> list[dict]
      Return all relics with enriched display fields.

  get_inventory_details(state) -> list[dict]
      Return enriched dicts for all relics in the player's inventory.
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

_RAW           = json.loads((_DATA_DIR / "relics.json").read_text())
_RELICS: List[dict] = _RAW["relics"]
_RELIC_MAP: Dict[str, dict] = {r["id"]: r for r in _RELICS}

# Capacity from schema (not hardcoded)
RELIC_CAPACITY: int = _RAW["inventory"]["max_relics"]

_RARITY_TABLES = json.loads((_DATA_DIR / "rarity_tables.json").read_text())

# Index relics by rarity for fast lookup
_RELICS_BY_RARITY: Dict[str, List[dict]] = {}
for _r in _RELICS:
    _rar = _r.get("rarity", "rare")
    _RELICS_BY_RARITY.setdefault(_rar, []).append(_r)

RARITY_ICONS = {
    "common":    "🌿",
    "rare":      "⚡",
    "epic":      "🔥",
    "legendary": "✨",
}


# ---------------------------------------------------------------------------
# Rarity roll helper
# ---------------------------------------------------------------------------

def _roll_rarity(rolls: List[dict]) -> str:
    """
    Weighted random rarity selection from a probability table.
    Each entry: {"rarity": str, "probability": float}.
    """
    r = random.random()
    cumulative = 0.0
    for entry in rolls:
        cumulative += entry["probability"]
        if r < cumulative:
            return entry["rarity"]
    return rolls[-1]["rarity"]  # fallback


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
    capacity = state.relic_capacity
    if len(state.relics) >= capacity:
        return False, (
            f"Relic inventory is full ({capacity}/{capacity}). "
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
# Relic reward roll (for future event rewards)
# ---------------------------------------------------------------------------

def roll_relic_reward() -> Optional[dict]:
    """
    Roll a random relic using relic_rarity_rolls from rarity_tables.json.
    Returns an enriched relic dict.
    """
    rarity     = _roll_rarity(_RARITY_TABLES["relic_rarity_rolls"])
    candidates = _RELICS_BY_RARITY.get(rarity) or _RELICS
    return _enrich(random.choice(candidates))


# ---------------------------------------------------------------------------
# Buff computation
# ---------------------------------------------------------------------------

def get_relic_buffs(state: PlayerState) -> dict:
    """
    Aggregate buff multipliers/bonuses from all held relics.
    Uses the same buff_type -> internal key mapping as creature_engine.

    buff_type -> internal buff key:
        farm_production   -> all_farms          (multiplier)
        drachmae_gain     -> workout_all         (multiplier)
        running_rewards   -> workout_running     (multiplier)
        strength_rewards  -> workout_strength    (multiplier)
        event_chance      -> event_chance        (additive)
        all_rewards       -> workout_all         (multiplier)
        rare_events       -> rare_event_chance   (additive)
        army_strength     -> army_strength       (multiplier, future)
        campaign_rewards  -> campaign_rewards    (multiplier, future)
    """
    buffs: dict = {}
    for relic_id in state.relics:
        relic = _RELIC_MAP.get(relic_id)
        if not relic:
            continue
        buff_type  = relic.get("buff_type", "")
        buff_value = float(relic.get("buff_value", 0.0))
        _merge_buff(buffs, buff_type, buff_value)
    return buffs


def _merge_buff(buffs: dict, buff_type: str, buff_value: float) -> None:
    """Merge one buff_type/buff_value pair into the running buffs accumulator."""
    mult = 1.0 + buff_value  # e.g. buff_value=0.15 -> 15 % boost

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
        # army_strength, campaign_rewards -> stored for future use
        buffs[buff_type] = buffs.get(buff_type, 1.0) * mult


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
    """Add display-only fields to a relic dict."""
    rarity     = relic.get("rarity", "rare")
    buff_type  = relic.get("buff_type", "")
    buff_value = float(relic.get("buff_value", 0.0))
    return {
        **relic,
        "icon":       RARITY_ICONS.get(rarity, "🔮"),
        "buff_label": describe_buff(buff_type, buff_value),
    }


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
