"""
trophy_engine.py – Monster trophy inventory and passive buff system.

Monster trophies are awarded when a player completes a 6-workout microcycle
(laurel window). Each trophy carries a permanent passive buff that stacks with
other trophies of the same type.

Public API:
    award_random_trophy(state) -> dict
        Pick a weighted-random trophy, add to state.trophies, return it.

    get_trophy_buffs(state) -> list[dict]
        Return [{buff_type, buff_value}, ...] for every trophy in inventory.

    get_trophy_inventory(state) -> list[dict]
        Return the full trophy list for UI display.

    describe_buff(buff_type, buff_value) -> str
        Human-readable passive bonus label (e.g. "+3% drachmae from workouts").
"""

from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from laurel_of_olympus.game_state import PlayerState

_DATA_PATH = Path(__file__).parent / "data" / "trophies.json"
_cache: dict | None = None

# Map monster name (as stored in trophies.json) → image folder path (relative,
# served by the /img/{path} route in app.py).
_MONSTER_IMAGE_MAP: dict[str, str] = {
    "Cyclops":  "Polyphemus/Vibrant/Polyphemus.png",
    "Harpy":    "Harpies/Vibrant/Harpies.png",
    "Satyr":    "Saytr/Vibrant/Saytr.png",
    "Minotaur": "Minotaur/Vibrant/Minotaur.png",
    "Medusa":   "Medusa/Vibrant/Medusa.png",
    "Sphinx":   "Sphinx/Vibrant/Sphinx.png",
    "Hydra":    "Lernaean_Hydra/Vibrant/Lernaean_Hydra.png",
    "Chimera":  "Chimera/Vibrant/Chimera.png",
    "Scylla":   "Scylla_&_Charybdis/Vibrant/Scylla_&_Charybdis.png",
    "Typhon":   "Typhon/Vibrant/Typhon.png",
}

_RARITY_COLOURS = {
    "common":    "#a0a0a0",
    "uncommon":  "#4fc35a",
    "rare":      "#4a9eff",
    "epic":      "#b44aff",
    "legendary": "#ffd700",
}

_RARITY_LABELS = {
    "common":    "Common",
    "uncommon":  "Uncommon",
    "rare":      "Rare",
    "epic":      "Epic",
    "legendary": "Legendary",
}


def _load() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(_DATA_PATH.read_text())
    return _cache


# ---------------------------------------------------------------------------
# Trophy awarding
# ---------------------------------------------------------------------------

def award_random_trophy(state: PlayerState) -> Dict[str, Any]:
    """
    Pick a weighted-random trophy from the pool, append it to state.trophies,
    and return the full trophy dict (including date_earned).
    """
    data = _load()
    weights_map: dict = data["rarity_weights"]
    pool: list = data["trophies"]
    weights = [weights_map.get(t["rarity"], 1) for t in pool]

    chosen: dict = random.choices(pool, weights=weights, k=1)[0]
    entry = {
        **chosen,
        "date_earned": str(date.today()),
        "buff_label":  describe_buff(chosen["buff_type"], chosen["buff_value"]),
        "image_path":  _MONSTER_IMAGE_MAP.get(chosen.get("monster", ""), None),
    }
    if not hasattr(state, "trophies") or state.trophies is None:
        state.trophies = []
    state.trophies.append(entry)
    return entry


# ---------------------------------------------------------------------------
# Buff extraction
# ---------------------------------------------------------------------------

def get_trophy_buffs(state: PlayerState) -> List[Dict[str, Any]]:
    """
    Return a list of {buff_type, buff_value} dicts for every trophy in the
    player's inventory.  buff_engine merges these into the global buff dict.
    """
    trophies = getattr(state, "trophies", None) or []
    return [
        {"buff_type": t["buff_type"], "buff_value": t["buff_value"]}
        for t in trophies
    ]


def get_trophy_inventory(state: PlayerState) -> List[Dict[str, Any]]:
    """Return the full trophy list, enriched with display data."""
    trophies = getattr(state, "trophies", None) or []
    result = []
    for t in trophies:
        entry = dict(t)
        # Ensure buff_label is always present
        if "buff_label" not in entry:
            entry["buff_label"] = describe_buff(t["buff_type"], t["buff_value"])
        entry["rarity_colour"] = _RARITY_COLOURS.get(t.get("rarity", "common"), "#a0a0a0")
        entry["rarity_label"]  = _RARITY_LABELS.get(t.get("rarity", "common"), "Common")
        if "image_path" not in entry:
            entry["image_path"] = _MONSTER_IMAGE_MAP.get(t.get("monster", ""), None)
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Buff summary (stacked totals per type)
# ---------------------------------------------------------------------------

def get_buff_summary(state: PlayerState) -> List[Dict[str, Any]]:
    """
    Aggregate all trophy bonuses by buff_type and return a sorted list of
    {buff_type, total_value, label} for the UI summary panel.
    """
    trophies = getattr(state, "trophies", None) or []
    totals: Dict[str, float] = {}
    for t in trophies:
        bt = t["buff_type"]
        totals[bt] = totals.get(bt, 0.0) + t["buff_value"]

    summary = []
    for bt, total in sorted(totals.items()):
        summary.append({
            "buff_type":   bt,
            "total_value": total,
            "label":       describe_buff(bt, total),
        })
    return summary


# ---------------------------------------------------------------------------
# Human-readable buff descriptions
# ---------------------------------------------------------------------------

def describe_buff(buff_type: str, buff_value: float) -> str:
    pct = round(buff_value * 100, 1)
    # Show whole numbers without decimal for cleanliness
    pct_str = str(int(pct)) if pct == int(pct) else str(pct)
    labels: Dict[str, str] = {
        "drachmae_gain":     f"+{pct_str}% drachmae from workouts",
        "strength_rewards":  f"+{pct_str}% strength rewards",
        "farm_production":   f"+{pct_str}% farm production",
        "creature_chance":   f"+{pct_str}% creature encounter chance",
        "campaign_strength": f"+{pct_str}% army strength",
        "relic_chance":      f"+{pct_str}% relic drop chance",
    }
    return labels.get(buff_type, f"+{pct_str}% {buff_type}")
