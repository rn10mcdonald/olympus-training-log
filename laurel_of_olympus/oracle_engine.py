"""
oracle_engine.py – Oracle phase system and Kassandra ultra-rare event.

The Oracle tracks a 5-phase relationship with the player, advancing as they
accumulate oracle_visits.  A separate channel from the regular event system:
  • 0.10% per workout → Kassandra Breaks Composure (requires phase >= 4)
  • 10.0% per workout → Oracle visit (normal oracle encounter)

Phase thresholds (oracle_visits to reach each phase):
  0  Stranger          – not yet encountered
  1  The Oracle Sees   – visits >= 1
  2  Familiar Mortal   – visits >= 3
  3  Favored Mortal    – visits >= 7
  4  Kassandra Notices – visits >= 12
  5  Kassandra, Ally   – visits >= 20

Public API:
  maybe_oracle_visit(state, chance=0.10) -> dict | None
      Roll for a regular oracle encounter. Advances oracle_phase if threshold
      is crossed. Returns an oracle event dict or None.

  maybe_kassandra_break(state, chance=0.001) -> dict | None
      Roll for the ultra-rare "Kassandra Breaks Composure" event.
      Only fires when oracle_phase >= 4. Awards +1 laurel.
      Returns an event dict or None.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

from laurel_of_olympus.game_state import PlayerState

# ---------------------------------------------------------------------------
# Flavor text
# ---------------------------------------------------------------------------
_FLAVOR = json.loads(
    (Path(__file__).parent / "data" / "flavor_text.json").read_text()
)

# ---------------------------------------------------------------------------
# Phase metadata
# ---------------------------------------------------------------------------
_PHASES = [
    # (min_visits, phase_id, phase_name)
    (0,  0, "Stranger"),
    (1,  1, "The Oracle of Delphi"),
    (3,  2, "Irritated Oracle of Delphi"),
    (7,  3, "Irritated Oracle of Delphi"),
    (12, 4, "Maybe Impressed Oracle of Delphi"),
    (20, 5, "Kassandra"),
]

# oracle_lines per phase — drawn from flavor_text or defined inline
_PHASE_POOLS = {
    0: [],   # never called (phase 0 = no visit yet)
    1: _FLAVOR["oracle_lines"],
    2: _FLAVOR["oracle_lines"] + _FLAVOR["oracle_irritated_lines"],
    3: _FLAVOR["oracle_irritated_lines"],
    4: _FLAVOR["oracle_impressed_lines"],
    5: _FLAVOR["oracle_impressed_lines"] + _FLAVOR["kassandra_lines"],
}

_PHASE_TITLES = {
    0: "The Oracle of Delphi",
    1: "The Oracle of Delphi",
    2: "An Irritated Oracle",
    3: "An Irritated Oracle",
    4: "Perhaps She Is Impressed",
    5: "Kassandra Speaks",
}


def _compute_phase(visits: int) -> int:
    phase = 0
    for min_v, p, _ in _PHASES:
        if visits >= min_v:
            phase = p
    return phase


def _pick(pool: list, k: int = 2) -> list:
    if not pool:
        return []
    p = list(pool)
    random.shuffle(p)
    return p[: min(k, len(p))]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def maybe_oracle_visit(
    state: PlayerState, chance: float = 0.10
) -> Optional[dict]:
    """
    Roll for an oracle encounter.  If it fires:
      • increment oracle_visits
      • advance oracle_phase if threshold crossed
      • return an event dict

    Returns None if the roll fails.
    """
    if random.random() > chance:
        return None

    state.oracle_visits += 1
    new_phase = _compute_phase(state.oracle_visits)
    phase_advanced = new_phase > state.oracle_phase
    state.oracle_phase = new_phase

    pool = _PHASE_POOLS.get(new_phase, _FLAVOR["oracle_lines"])
    lines = _pick(pool, 2)

    # At phase 4+ there's a 40% chance Kassandra adds a line
    if new_phase >= 4 and random.random() < 0.40:
        lines.append(random.choice(_FLAVOR["kassandra_lines"]))

    title = _PHASE_TITLES.get(new_phase, "The Oracle Appears")

    event: dict = {
        "type":          "oracle",
        "title":         title,
        "icon":          "🔮",
        "lines":         lines,
        "oracle_phase":  new_phase,
        "phase_advanced": phase_advanced,
    }

    if phase_advanced and new_phase > 1:
        phase_names = {p: name for _, p, name in _PHASES}
        event["phase_name"] = phase_names.get(new_phase, "")

    return event


def maybe_kassandra_break(
    state: PlayerState, chance: float = 0.001
) -> Optional[dict]:
    """
    Ultra-rare event: Kassandra Breaks Composure.
    Only rolls when oracle_phase >= 4.
    Awards +1 laurel on trigger.

    Returns an event dict or None.
    """
    if state.oracle_phase < 4:
        return None
    if random.random() > chance:
        return None

    state.laurels += 1

    return {
        "type":   "rare",
        "title":  "Kassandra Breaks Composure",
        "icon":   "✨",
        "lines":  list(_FLAVOR["kassandra_laugh_event"]) + [
            f"A laurel is awarded. Total: {state.laurels}."
        ],
        "kassandra_break": True,
    }
