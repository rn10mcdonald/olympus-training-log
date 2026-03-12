"""
workout_engine.py – Drachmae reward calculations.

All formulas come directly from balance_table.txt.

Public API:
    calculate_reward(workout_type, **kwargs) -> float
    process_workout(state, workout_type, buffs=None, **kwargs) -> list[str]
        Mutates state, returns list of event strings for the event log.
        buffs: optional dict from buff_engine.get_all_buffs(state).
               Key "workout_{workout_type}" scales the final drachmae reward.
"""

from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional

from laurel_of_olympus.game_state import PlayerState

# ---------------------------------------------------------------------------
# Diminishing-returns multipliers for multiple workouts in one day
# ---------------------------------------------------------------------------
_DR_MULTIPLIERS = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4}
_DR_FLOOR = 0.4  # 4th workout and beyond


def _dr_multiplier(workout_number: int) -> float:
    return _DR_MULTIPLIERS.get(workout_number, _DR_FLOOR)


# ---------------------------------------------------------------------------
# Reward formulas (balance_table.txt)
# ---------------------------------------------------------------------------

def _reward_walking(miles: float = 1.0) -> float:
    """Base 10 + 2 per mile."""
    return 10.0 + 2.0 * miles


def _reward_running(miles: float = 2.0) -> float:
    """Base 15 + 3 per mile."""
    return 15.0 + 3.0 * miles


def _reward_rucking(miles: float = 2.0, lbs: float = 20.0) -> float:
    """Base 20 + 4 per mile + 1 per 10 lbs carried."""
    return 20.0 + 4.0 * miles + (lbs / 10.0)


def _reward_strength(volume: float = 5000.0) -> float:
    """Base 18 + volume / 400. Volume = weight × reps × sets."""
    return 18.0 + volume / 400.0


_REWARD_FN = {
    "walking": _reward_walking,
    "running": _reward_running,
    "rucking": _reward_rucking,
    "strength": _reward_strength,
}


def calculate_reward(workout_type: str, **kwargs) -> float:
    """
    Return raw drachmae reward (before diminishing returns).

    kwargs per type:
        walking:  miles (float)
        running:  miles (float)
        rucking:  miles (float), lbs (float)
        strength: volume (float)  [weight × reps × sets]
    """
    fn = _REWARD_FN.get(workout_type)
    if fn is None:
        raise ValueError(f"Unknown workout type: {workout_type!r}")
    return round(fn(**kwargs), 2)


# ---------------------------------------------------------------------------
# State mutation
# ---------------------------------------------------------------------------

def process_workout(
    state: PlayerState,
    workout_type: str,
    buffs: Optional[dict] = None,
    **kwargs,
) -> List[str]:
    """
    Award drachmae for a workout, update counters, apply diminishing returns.
    Returns a list of event strings for display in the event log.

    buffs: dict from buff_engine.get_all_buffs(state).
           "workout_{workout_type}" multiplier is applied after DR scaling.
    """
    events: List[str] = []
    today = str(dt.date.today())
    buffs = buffs or {}

    # ── Reset daily counter if it's a new day ───────────────────────────────
    if state.last_workout_date != today:
        state.last_workout_date = today
        state.workouts_today = 0

    state.workouts_today += 1
    workout_number = state.workouts_today

    # ── Calculate reward ────────────────────────────────────────────────────
    raw = calculate_reward(workout_type, **kwargs)
    multiplier = _dr_multiplier(workout_number)
    base_final = round(raw * multiplier, 2)

    # Apply sanctuary / relic workout buffs
    # type-specific multiplier (e.g. running_rewards) × all-workout multiplier
    workout_mult = buffs.get(f"workout_{workout_type}", 1.0) * buffs.get("workout_all", 1.0)
    final = round(base_final * workout_mult, 2)
    buff_bonus = round(final - base_final, 2)

    state.drachmae = round(state.drachmae + final, 2)

    # ── Update workout counts ───────────────────────────────────────────────
    state.workout_counts[workout_type] = state.workout_counts.get(workout_type, 0) + 1

    # ── Log the workout ─────────────────────────────────────────────────────
    state.workout_log.append({
        "date": today,
        "workout_type": workout_type,
        "drachmae_earned": final,
        "params": kwargs,
    })

    # ── Build event messages ─────────────────────────────────────────────────
    type_labels = {
        "walking":  "Walk",
        "running":  "Run",
        "rucking":  "Ruck",
        "strength": "Strength",
    }
    label = type_labels.get(workout_type, workout_type.title())

    # Param summary
    param_parts = []
    if "miles" in kwargs:
        param_parts.append(f"{kwargs['miles']} mi")
    if "lbs" in kwargs:
        param_parts.append(f"{kwargs['lbs']} lbs")
    if "volume" in kwargs:
        param_parts.append(f"vol {int(kwargs['volume'])}")
    param_str = ", ".join(param_parts)

    buff_str = f"  ✨ +{buff_bonus} from sanctuary/relics" if buff_bonus > 0 else ""
    events.append(f"[{label}] {param_str}  →  +{final} drachmae{buff_str}")

    if workout_number > 1:
        events.append(
            f"  ↳ Workout #{workout_number} today — "
            f"diminishing returns ×{multiplier:.1f} applied"
        )

    # ── Check laurel window progress ─────────────────────────────────────────
    _update_laurel_window(state, today, events)

    return events


# ---------------------------------------------------------------------------
# Laurel window logic  (6 workouts within any 14-day window → +1 laurel)
# ---------------------------------------------------------------------------

def _update_laurel_window(
    state: PlayerState, today: str, events: List[str]
) -> None:
    """
    Maintain a rolling 14-day window. If 6 workouts fall within it, award
    a laurel and open a new window.
    """
    today_date = dt.date.fromisoformat(today)

    # Open the very first window
    if not state.laurel_windows:
        state.laurel_windows.append({"start": today, "workouts": [today]})
        return

    current = state.laurel_windows[-1]
    window_start = dt.date.fromisoformat(current["start"])
    days_elapsed = (today_date - window_start).days

    if days_elapsed <= 14:
        # Still inside the current window
        current["workouts"].append(today)
        count = len(current["workouts"])
        if count >= 6:
            state.laurels += 1
            events.append(
                f"  ★ LAUREL EARNED! ({count} workouts in 14 days) "
                f"→ Total laurels: {state.laurels}"
            )
            # Open a fresh window starting today
            state.laurel_windows.append({"start": today, "workouts": [today]})
    else:
        # Window expired – open a new one
        state.laurel_windows.append({"start": today, "workouts": [today]})
        events.append(
            "  (New 14-day laurel window opened — "
            f"6 workouts within it earn a laurel)"
        )
