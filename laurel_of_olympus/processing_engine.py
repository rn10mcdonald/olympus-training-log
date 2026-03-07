"""
processing_engine.py – Processing building construction and goods production.

Processing buildings convert raw farm resources into refined goods:
    Winery:       grapes → wine       (ratio 2:1)
    Bakery:       grain  → bread      (ratio 2:1)
    Olive Press:  olives → olive_oil  (ratio 2:1)
    Meadery:      honey  → mead       (ratio 2:1)

Buildings must be constructed before they can be used.
Each building type can only be built once.

Public API:
    get_all_buildings() -> list[dict]
        Return all building definitions with enriched display fields.

    get_player_buildings(state) -> list[dict]
        Return enriched dicts for buildings the player has constructed,
        plus unbuild buildings for the shop display.

    build_processing_building(state, building_id) -> (bool, str)
        Construct a building. Deducts build_cost from drachmae + grain.
        Returns (success, message).

    process_goods(state, building_id, amount) -> (bool, str, dict)
        Convert raw resources → refined goods.
        amount: number of output units to produce (each costs ratio inputs).
        Returns (success, message, {input_used, output_produced}).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from laurel_of_olympus.game_state import PlayerState

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent / "data"
_BUILDINGS_RAW: List[dict] = json.loads((_DATA_DIR / "processing.json").read_text())
_BUILDING_MAP: Dict[str, dict] = {b["id"]: b for b in _BUILDINGS_RAW}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_buildings() -> List[dict]:
    """Return all building definitions."""
    return list(_BUILDINGS_RAW)


def get_player_buildings(state: PlayerState) -> List[dict]:
    """
    Return a list of all buildings enriched with player-state fields:
        built: bool
        can_afford: bool
        input_held: int   — how much raw resource the player currently has
        output_held: int  — how much refined good the player currently has
    """
    result = []
    for b in _BUILDINGS_RAW:
        built = b["id"] in state.processing_buildings
        cost = b["build_cost"]
        can_afford = (
            state.drachmae >= cost.get("drachmae", 0)
            and getattr(state, "grain", 0) >= cost.get("grain", 0)
        )
        result.append({
            **b,
            "built":       built,
            "can_afford":  can_afford,
            "input_held":  getattr(state, b["input"], 0),
            "output_held": getattr(state, b["output"], 0),
        })
    return result


def build_processing_building(
    state: PlayerState, building_id: str
) -> Tuple[bool, str]:
    """
    Construct a processing building.
    Returns (success, message).
    """
    building = _BUILDING_MAP.get(building_id)
    if not building:
        return False, f"Unknown building: {building_id}"
    if building_id in state.processing_buildings:
        return False, f"{building['name']} is already built."

    cost = building["build_cost"]
    dr_cost   = cost.get("drachmae", 0)
    grain_cost = cost.get("grain", 0)

    if state.drachmae < dr_cost:
        return False, (
            f"Need {dr_cost:.0f} drachmae to build {building['name']}. "
            f"You have {state.drachmae:.0f}."
        )
    if getattr(state, "grain", 0) < grain_cost:
        return False, (
            f"Need {grain_cost} grain to build {building['name']}. "
            f"You have {getattr(state, 'grain', 0)}."
        )

    state.drachmae = round(state.drachmae - dr_cost, 2)
    state.grain    = state.grain - grain_cost
    state.processing_buildings.append(building_id)

    return True, f"{building['icon']} {building['name']} constructed!"


def process_goods(
    state: PlayerState, building_id: str, amount: int = 1
) -> Tuple[bool, str, dict]:
    """
    Produce refined goods using a constructed building.

    amount: how many output units to produce (minimum 1).
    Each output unit costs `ratio` input units.

    Returns (success, message, detail_dict).
    detail_dict keys: input_used, output_produced.
    """
    if amount < 1:
        amount = 1

    building = _BUILDING_MAP.get(building_id)
    if not building:
        return False, f"Unknown building: {building_id}", {}

    if building_id not in state.processing_buildings:
        return False, f"You haven't built a {building['name']} yet.", {}

    ratio       = building["ratio"]
    input_field = building["input"]
    output_field = building["output"]
    input_needed = ratio * amount

    current_input = getattr(state, input_field, 0)
    if current_input < input_needed:
        # How much can we actually make?
        possible = current_input // ratio
        if possible == 0:
            return False, (
                f"Not enough {input_field} to process. "
                f"Need {ratio} per unit, you have {current_input}."
            ), {}
        # Clamp to what's possible
        amount      = possible
        input_needed = ratio * amount

    # Perform conversion
    setattr(state, input_field,  getattr(state, input_field,  0) - input_needed)
    setattr(state, output_field, getattr(state, output_field, 0) + amount)

    msg = (
        f"{building['icon']} Processed {input_needed} {input_field} "
        f"→ {amount} {output_field}."
    )
    return True, msg, {"input_used": input_needed, "output_produced": amount}
