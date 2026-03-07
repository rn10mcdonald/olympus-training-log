"""
title_engine.py – Title unlock checks and Prophecy Scroll builder.

Titles are defined in data/titles.json with machine-readable condition objects.
This module evaluates each condition against PlayerState, tracks newly-unlocked
titles, and builds the Prophecy Scroll payload for the UI.

Public API:
  check_and_unlock_titles(state) -> list[str]
      Evaluate all conditions; add newly-met titles to state.
      Returns list of newly-unlocked title ids (may be empty).

  get_prophecy_scroll(state) -> dict
      Return full Prophecy Scroll payload for /api/estate/prophecy.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import List, Dict, Any

from laurel_of_olympus.game_state import PlayerState

# ---------------------------------------------------------------------------
# Load titles.json once at import
# ---------------------------------------------------------------------------
_TITLES_RAW: dict = json.loads(
    (Path(__file__).parent / "data" / "titles.json").read_text()
)

# Real category names as they appear in titles.json
_CATEGORIES: List[str] = list(_TITLES_RAW.keys())  # consistency, workout, estate, legendary, secret

# Flat lookup: id -> {id, name, condition (raw obj), category}
_ALL_TITLES: Dict[str, dict] = {}
for _cat, _items in _TITLES_RAW.items():
    for _t in _items:
        _ALL_TITLES[_t["id"]] = {**_t, "category": _cat}

# Extra title not in titles.json — awarded externally by oracle_engine / app.py
# Injected into the Prophecy Scroll legendary section for display.
_EXTRA_TITLES: Dict[str, dict] = {
    "favorite_of_kassandra": {
        "id":        "favorite_of_kassandra",
        "name":      "Favorite of Kassandra",
        "condition": {"type": "secret", "trigger": "kassandra_break"},
        "category":  "legendary",
    }
}

# Display labels per category
_CATEGORY_LABELS: Dict[str, str] = {
    "consistency": "Consistency",
    "workout":     "Discipline",
    "estate":      "Estate",
    "legendary":   "Legend",
    "secret":      "Secret",
}

# Oracle phase labels (mirrors oracle_engine._PHASES)
_ORACLE_PHASE_NAMES: Dict[int, str] = {
    0: "Stranger",
    1: "The Oracle of Delphi",
    2: "Irritated Oracle of Delphi",
    3: "Irritated Oracle of Delphi",
    4: "Maybe Impressed Oracle of Delphi",
    5: "Kassandra",
}


# ---------------------------------------------------------------------------
# Condition evaluators
# ---------------------------------------------------------------------------

def _days_since_last_workout(state: PlayerState) -> int:
    if not state.last_workout_date:
        return 999
    last = dt.date.fromisoformat(state.last_workout_date)
    return (dt.date.today() - last).days


def _evaluate_condition(state: PlayerState, cond: dict) -> bool:
    """Return True if the machine-readable condition object is satisfied."""
    ctype = cond.get("type", "")

    if ctype == "total_workouts":
        total = sum(state.workout_counts.values())
        return total >= cond.get("count", 9999)

    if ctype == "laurels":
        return state.laurels >= cond.get("count", 9999)

    if ctype == "workout_count":
        workout = cond.get("workout", "")
        return state.workout_counts.get(workout, 0) >= cond.get("count", 9999)

    if ctype == "farms_built":
        return len(state.farms) >= cond.get("count", 9999)

    if ctype == "farm_level":
        required = cond.get("level", 9999)
        return any(f.get("level", 1) >= required for f in state.farms)

    if ctype == "has_farm_type":
        farm_type = cond.get("farm_type", "")
        return any(f.get("farm_type") == farm_type for f in state.farms)

    if ctype == "relics_held":
        return len(state.relics) >= cond.get("count", 9999)

    if ctype == "inventory_count":
        resource = cond.get("resource", "")
        return getattr(state, resource, 0) >= cond.get("count", 9999)

    if ctype == "campaigns_won":
        return getattr(state, "campaigns_won", 0) >= cond.get("count", 9999)

    if ctype == "secret":
        trigger = cond.get("trigger", "")
        if trigger == "14_day_gap":
            # Must have worked out before, then gone 14 days without
            return bool(state.last_workout_date) and _days_since_last_workout(state) >= 14
        if trigger == "kassandra_break":
            # Set externally by oracle_engine / app.py
            return "favorite_of_kassandra" in state.titles_unlocked
        # cardio_bunny, champion_of_chest_day, legs_remain_theoretical
        # require additional workout-level tracking — set externally when triggered
        if trigger in state.titles_unlocked:
            return True
        return False

    return False


# ---------------------------------------------------------------------------
# Tier ordering within each category (for combined title display)
# highest-tier first — matches descending difficulty
# Synced with IDs in data/titles.json
# ---------------------------------------------------------------------------
_CATEGORY_TIER_ORDER: Dict[str, List[str]] = {
    "consistency": [
        "discipline_of_olympus", "relentless_champion",
        "persistent_hero", "consistent_mortal",
    ],
    "workout": [
        # Running (highest first)
        "wind_of_olympus", "messenger_of_hermes", "runner_of_hermes", "jogging_mortal",
        # Strength
        "strength_of_heracles", "disciple_of_heracles", "bearer_of_bronze",
        # Rucking
        "warden_of_the_long_road", "roadwarden", "bearer_of_the_ruck",
        # Walking
        "student_of_socrates", "walking_philosopher",
    ],
    "estate": [
        "lord_of_the_estate", "steward_of_the_estate", "master_of_the_vineyard",
        "guardian_of_the_grove", "keeper_of_the_fields", "caretaker_of_dirt",
    ],
    "legendary": [
        "hero_of_olympus", "champion_of_the_gods", "favorite_of_kassandra",
    ],
    "secret": [
        "acting_suspiciously_roman", "cardio_bunny", "champion_of_chest_day",
        "wino", "relic_hoarder", "legs_remain_theoretical",
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_and_unlock_titles(state: PlayerState) -> List[str]:
    """
    Evaluate every title condition.  Any newly-satisfied title whose id is
    not already in state.titles_unlocked is added.

    Returns the list of newly-unlocked title ids (may be empty).
    """
    newly_unlocked: List[str] = []

    all_titles = {**_ALL_TITLES, **_EXTRA_TITLES}
    for title_id, title in all_titles.items():
        if title_id in state.titles_unlocked:
            continue
        cond = title.get("condition", {})
        if isinstance(cond, dict) and _evaluate_condition(state, cond):
            state.titles_unlocked.append(title_id)
            newly_unlocked.append(title_id)
            # Update active_titles with the most recently unlocked per category
            category = title["category"]
            state.active_titles[category] = title_id

    return newly_unlocked


def get_prophecy_scroll(state: PlayerState) -> dict:
    """
    Build the full Prophecy Scroll payload.

    Returns:
        {
            oracle_phase: int,
            oracle_phase_name: str,
            oracle_visits: int,
            laurels: int,
            titles_by_category: [
                {
                    category: str,
                    label: str,
                    titles: [{id, name, condition_str, unlocked}]
                }
            ],
            combined_title: str,
            newly_unlocked: [str]
        }
    """
    newly_unlocked = check_and_unlock_titles(state)

    # Build per-category breakdown
    all_titles_with_extra = {**_ALL_TITLES, **_EXTRA_TITLES}
    titles_by_category: List[dict] = []
    for category in _CATEGORIES:
        label = _CATEGORY_LABELS.get(category, category.title())
        # Items from titles.json for this category
        items = _TITLES_RAW.get(category, [])
        # Inject favorite_of_kassandra into legendary
        if category == "legendary":
            items = list(items) + [_EXTRA_TITLES["favorite_of_kassandra"]]

        cat_entry: dict = {
            "category": category,
            "label":    label,
            "titles": [
                {
                    "id":        t["id"],
                    "name":      t["name"],
                    "condition": _condition_to_string(t.get("condition", {})),
                    "unlocked":  t["id"] in state.titles_unlocked,
                }
                for t in items
            ],
        }
        titles_by_category.append(cat_entry)

    combined_parts = _build_combined_title(state)

    return {
        "oracle_phase":       state.oracle_phase,
        "oracle_phase_name":  _ORACLE_PHASE_NAMES.get(state.oracle_phase, "Stranger"),
        "oracle_visits":      state.oracle_visits,
        "laurels":            state.laurels,
        "titles_by_category": titles_by_category,
        "combined_title":     ", ".join(combined_parts) if combined_parts else "Unnamed Mortal",
        "newly_unlocked":     newly_unlocked,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _condition_to_string(cond: Any) -> str:
    """Convert a machine-readable condition dict to a human-readable string."""
    if not isinstance(cond, dict):
        return str(cond)
    ctype = cond.get("type", "")
    if ctype == "total_workouts":
        return f"Complete {cond['count']} total workouts"
    if ctype == "laurels":
        return f"Earn {cond['count']} laurel{'s' if cond['count'] != 1 else ''}"
    if ctype == "workout_count":
        wt = cond.get("workout", "")
        labels = {
            "running": "runs", "rucking": "rucks",
            "strength": "strength workouts", "walking": "walks",
        }
        return f"Complete {cond['count']} {labels.get(wt, wt + ' sessions')}"
    if ctype == "farms_built":
        return f"Build {cond['count']} farm{'s' if cond['count'] != 1 else ''}"
    if ctype == "farm_level":
        return f"Upgrade any farm to level {cond['level']}"
    if ctype == "has_farm_type":
        names = {
            "grain_field": "a Grain Field", "vineyard": "a Vineyard",
            "olive_grove": "an Olive Grove", "apiary": "an Apiary",
            "herb_garden": "a Herb Garden",
        }
        return f"Own {names.get(cond.get('farm_type', ''), cond.get('farm_type', ''))}"
    if ctype == "relics_held":
        return f"Hold {cond['count']} relics simultaneously"
    if ctype == "inventory_count":
        return f"Have {cond['count']} {cond.get('resource', 'resource')} in inventory"
    if ctype == "campaigns_won":
        return f"Win {cond['count']} campaign{'s' if cond['count'] != 1 else ''}"
    if ctype == "secret":
        trigger = cond.get("trigger", "")
        if trigger == "14_day_gap":
            return "Go 14 days without a workout"
        if trigger == "kassandra_break":
            return "Witness Kassandra break composure"
        if trigger == "cardio_bunny":
            return "Only run for 30 days straight"
        if trigger == "champion_of_chest_day":
            return "7 strength workouts with no leg exercises"
        if trigger == "legs_remain_theoretical":
            return "30 days of strength with no leg movements"
        return "Secret unlock condition"
    return "???"


def _build_combined_title(state: PlayerState) -> List[str]:
    """
    For each non-secret category, pick the highest-tier unlocked title name.
    Returns list of title names.
    """
    parts: List[str] = []
    all_titles = {**_ALL_TITLES, **_EXTRA_TITLES}
    display_categories = ["consistency", "workout", "estate", "legendary"]
    for cat in display_categories:
        tier_order = _CATEGORY_TIER_ORDER.get(cat, [])
        for tid in tier_order:
            if tid in state.titles_unlocked:
                name = all_titles.get(tid, {}).get("name", tid)
                parts.append(name)
                break
    return parts
