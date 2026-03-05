"""
event_engine.py – Random narrative events triggered after workouts.

Events fire at ~20% chance after any estate workout.

Event types:
  oracle     – The Oracle (or Kassandra) appears with commentary
  creature   – A mythical creature is encountered near the estate
  merchant   – A travelling merchant makes an offer
  philosopher – A philosopher wanders past with unsolicited wisdom
  rare       – Kassandra laughs (very uncommon)

Public API:
  maybe_trigger_event(state, chance=0.20) -> dict | None
    Returns an event dict or None if no event fires.

Event dict shape:
  {
    "type":    str,          # oracle / creature / merchant / philosopher / rare
    "title":   str,          # popup heading
    "icon":    str,          # emoji
    "lines":   list[str],    # 1–4 flavor text lines
    "creature": {            # only present for creature events
      "name": str, "description": str, "rarity": str, "flavor": str
    }
  }
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Load data files once at import time
# ---------------------------------------------------------------------------

_DATA_DIR   = Path(__file__).parent / "data"
_FLAVOR     = json.loads((_DATA_DIR / "flavor_text.json").read_text())
_CREATURES  = json.loads((_DATA_DIR / "creatures.json").read_text())

# ---------------------------------------------------------------------------
# Event type weights  (must sum to 100)
# ---------------------------------------------------------------------------
_EVENT_WEIGHTS = [
    ("oracle",      35),
    ("creature",    25),
    ("merchant",    22),
    ("philosopher", 15),
    ("rare",         3),
]
_EVENT_TYPES  = [t for t, _ in _EVENT_WEIGHTS]
_EVENT_WCUM   = []
_cum = 0
for _t, _w in _EVENT_WEIGHTS:
    _cum += _w
    _EVENT_WCUM.append(_cum)
_TOTAL_W = _cum  # 100


def _pick_event_type() -> str:
    r = random.uniform(0, _TOTAL_W)
    for t, cum in zip(_EVENT_TYPES, _EVENT_WCUM):
        if r <= cum:
            return t
    return "oracle"


def _pick(lines: list, k: int = 1) -> list[str]:
    """Return k unique random lines from a list (no repeats)."""
    pool = list(lines)
    random.shuffle(pool)
    return pool[:min(k, len(pool))]


# ---------------------------------------------------------------------------
# Per-event builders
# ---------------------------------------------------------------------------

def _build_oracle(state: dict) -> dict:
    total_workouts = sum(state.get("workout_counts", {}).values())
    workouts_today = state.get("workouts_today", 1)
    laurels        = state.get("laurels", 0)

    # Choose which pool of oracle lines to use
    if total_workouts >= 15 and laurels >= 1:
        pool = _FLAVOR["oracle_impressed_lines"]
        title = "The Oracle Is Impressed"
    elif workouts_today >= 3 or total_workouts >= 8:
        pool = _FLAVOR["oracle_irritated_lines"]
        title = "The Oracle Is Irritated"
    else:
        pool = _FLAVOR["oracle_lines"]
        title = "The Oracle Appears"

    # 30 % chance Kassandra speaks instead of / in addition to the Oracle
    lines = _pick(pool, 2)
    if random.random() < 0.30:
        lines.append(random.choice(_FLAVOR["kassandra_lines"]))
        title = "Kassandra Speaks"

    return {
        "type":  "oracle",
        "title": title,
        "icon":  "🔮",
        "lines": lines,
    }


def _build_creature() -> dict:
    creature = random.choice(_CREATURES)
    rarity_icons = {
        "common":    "🌿",
        "rare":      "⚡",
        "epic":      "🔥",
        "legendary": "✨",
    }
    icon = rarity_icons.get(creature.get("rarity", "common"), "🐾")

    lines = _pick(_FLAVOR["creature_encounter_lines"], 1)
    lines.append(creature["description"])
    if creature.get("flavor"):
        lines.append(f'"{creature["flavor"]}"')

    return {
        "type":     "creature",
        "title":    f'{creature["name"]} Encountered',
        "icon":     icon,
        "lines":    lines,
        "creature": {
            "name":        creature["name"],
            "description": creature["description"],
            "rarity":      creature.get("rarity", "common"),
            "flavor":      creature.get("flavor", ""),
        },
    }


def _build_merchant() -> dict:
    lines = _pick(_FLAVOR["merchant_lines"], 2)
    # Occasional roman joke (20 % chance)
    if random.random() < 0.20:
        lines.append(random.choice(_FLAVOR["roman_jokes"]))

    return {
        "type":  "merchant",
        "title": "A Merchant Appears",
        "icon":  "⚖️",
        "lines": lines,
    }


def _build_philosopher() -> dict:
    lines = _pick(_FLAVOR["philosopher_lines"], 2)

    return {
        "type":  "philosopher",
        "title": "A Philosopher Wanders By",
        "icon":  "📜",
        "lines": lines,
    }


def _build_rare() -> dict:
    return {
        "type":  "rare",
        "title": "Something Unusual Occurs",
        "icon":  "✨",
        "lines": list(_FLAVOR["kassandra_laugh_event"]),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def maybe_trigger_event(state: dict, chance: float = 0.20) -> Optional[dict]:
    """
    Roll for a random narrative event.

    Args:
        state:  The PlayerState.to_dict() — used for contextual oracle lines.
        chance: Probability of an event firing (default 0.20 = 20 %).

    Returns:
        An event dict, or None if no event fires.
    """
    if random.random() > chance:
        return None

    event_type = _pick_event_type()

    builders = {
        "oracle":      lambda: _build_oracle(state),
        "creature":    _build_creature,
        "merchant":    _build_merchant,
        "philosopher": _build_philosopher,
        "rare":        _build_rare,
    }

    return builders[event_type]()
