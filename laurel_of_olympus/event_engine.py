"""
event_engine.py – Random narrative events triggered after workouts.

Events fire at ~20% chance after any estate workout.
The oracle now has its own separate channel (oracle_engine.py); this module
handles creature / merchant / philosopher / rare events only.

Event types:
  creature   – A mythical creature is encountered near the estate
  merchant   – A travelling merchant makes an offer
  philosopher – A philosopher wanders past with unsolicited wisdom
  rare       – Something unusual occurs

Public API:
  maybe_trigger_event(state, chance=0.20) -> dict | None
    Returns an event dict or None if no event fires.

Event dict shape:
  {
    "type":    str,          # creature / merchant / philosopher / rare
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
_CREATURES  = json.loads((_DATA_DIR / "creatures.json").read_text())["creatures"]

# ---------------------------------------------------------------------------
# Event type weights  (must sum to 100)
# Oracle has its own separate channel in oracle_engine.py
# ---------------------------------------------------------------------------
_EVENT_WEIGHTS = [
    ("creature",    35),
    ("merchant",    30),
    ("philosopher", 25),
    ("rare",        10),
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
    return "creature"


def _pick(lines: list, k: int = 1) -> list[str]:
    """Return k unique random lines from a list (no repeats)."""
    pool = list(lines)
    random.shuffle(pool)
    return pool[:min(k, len(pool))]


# ---------------------------------------------------------------------------
# Per-event builders
# ---------------------------------------------------------------------------

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
    # DEV-4: Use rare_event_lines, NOT kassandra_laugh_event
    # kassandra_laugh_event is reserved for the actual Kassandra Break ultra-rare
    lines = _pick(_FLAVOR.get("rare_event_lines", [
        "The air shifts strangely about the estate.",
        "A raven circles the hill twice, then departs.",
        "The scroll shivers in your hand, as if something passes nearby.",
    ]), 2)
    return {
        "type":  "rare",
        "title": "Something Unusual Occurs",
        "icon":  "✨",
        "lines": lines,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def maybe_trigger_event(state: dict, chance: float = 0.20) -> Optional[dict]:
    """
    Roll for a random narrative event (creature / merchant / philosopher / rare).

    The oracle channel is handled separately by oracle_engine.maybe_oracle_visit().

    Args:
        state:  The PlayerState.to_dict() — kept for future contextual builders.
        chance: Probability of an event firing (default 0.20 = 20 %).

    Returns:
        An event dict, or None if no event fires.
    """
    if random.random() > chance:
        return None

    event_type = _pick_event_type()

    builders = {
        "creature":    _build_creature,
        "merchant":    _build_merchant,
        "philosopher": _build_philosopher,
        "rare":        _build_rare,
    }

    return builders[event_type]()
