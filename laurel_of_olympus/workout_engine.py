"""
workout_engine.py – Drachmae reward calculations and weekly laurel tracking.

Public API:
    calculate_reward(workout_type, **kwargs) -> float
    process_workout(state, workout_type, buffs=None, reward_override=None, **kwargs) -> list[str]
        Mutates state, returns list of event strings for the event log.
        buffs: optional dict from buff_engine.get_all_buffs(state).
               Key "workout_{workout_type}" scales the final drachmae reward.
        reward_override: if provided, skip reward calculation and use this value
               (still applies buff multipliers). Used by endpoints that calculate
               per-movement rewards externally (e.g. microcycle expansion).
"""

from __future__ import annotations

import datetime as dt
import math
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
# Reward formulas
# ---------------------------------------------------------------------------

def _reward_walking(miles: float = 1.0) -> float:
    """miles × 12. Target: 1 mile → 12 drachmae."""
    return miles * 12.0


def _reward_running(miles: float = 2.0) -> float:
    """miles × 18. Target: 1 mile → 18 drachmae."""
    return miles * 18.0


def _reward_rucking(miles: float = 2.0, lbs: float = 0.0) -> float:
    """miles × 20. Target: 1 mile → 20 drachmae."""
    return miles * 20.0


def _reward_strength(weight_lbs: float = 35.0, reps: int = 5, sets: int = 3) -> float:
    """
    Normalized weight scaling: sqrt(weight_lbs) × reps × sets × 0.03.
    Single movement target: 5–12 drachmae.
    """
    effective_weight = math.sqrt(max(1.0, float(weight_lbs)))
    return effective_weight * int(reps) * int(sets) * 0.03


# Rate per minute for time-based workouts (before 60 🪙 cap)
_TIMED_RATES: dict[str, float] = {
    "strength": 0.7,
    "yoga":     0.5,
    "pilates":  0.5,
    "general":  0.6,
}
_TIMED_CAP = 60.0  # max drachmae per timed session


def _reward_timed(minutes: float = 30.0, workout_subtype: str = "general") -> float:
    """Drachmae for duration-based workouts.  minutes × rate, capped at 60."""
    rate = _TIMED_RATES.get(workout_subtype, 0.6)
    return min(round(minutes * rate, 2), _TIMED_CAP)


_REWARD_FN = {
    "walking":  _reward_walking,
    "running":  _reward_running,
    "rucking":  _reward_rucking,
    "strength": _reward_strength,
    "timed": _reward_timed,
}


def calculate_reward(workout_type: str, **kwargs) -> float:
    """
    Return raw drachmae reward (before diminishing returns or buffs).

    kwargs per type:
        walking:  miles (float)
        running:  miles (float)
        rucking:  miles (float), lbs (float)
        strength: weight_lbs (float), reps (int), sets (int)
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
    reward_override: Optional[float] = None,
    **kwargs,
) -> List[str]:
    """
    Award drachmae for a workout, update counters, apply diminishing returns.
    Returns a list of event strings for display in the event log.

    buffs: dict from buff_engine.get_all_buffs(state).
           "workout_{workout_type}" multiplier is applied after DR scaling.

    reward_override: if set, skip reward calculation and use this pre-computed
           value as the base reward. Buff multipliers (blessings, sanctuary,
           relics) are still applied on top of this value. Use for microcycle
           expansion where per-movement rewards are summed externally.
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
    if reward_override is not None:
        # Pre-computed reward (e.g. microcycle expansion); still apply buffs.
        base_final = round(float(reward_override), 2)
    else:
        raw = calculate_reward(workout_type, **kwargs)
        multiplier = _dr_multiplier(workout_number)
        base_final = round(raw * multiplier, 2)

    # Apply sanctuary / relic / blessing workout buffs to the reward ONLY —
    # never to the player's total balance.
    workout_mult = buffs.get(f"workout_{workout_type}", 1.0) * buffs.get("workout_all", 1.0)
    final = round(base_final * workout_mult, 2)
    buff_bonus = round(final - base_final, 2)

    state.drachmae = round(state.drachmae + final, 2)

    # ── Update workout counts ───────────────────────────────────────────────
    state.workout_counts[workout_type] = state.workout_counts.get(workout_type, 0) + 1

    # ── Log the workout ─────────────────────────────────────────────────────
    state.workout_log.append({
        "date":            today,
        "workout_type":    workout_type,
        "drachmae_earned": final,
        "params":          kwargs,
    })

    # ── Build event messages ─────────────────────────────────────────────────
    type_labels = {
        "walking":  "Walk",
        "running":  "Run",
        "rucking":  "Ruck",
        "strength": "Strength",
    }
    label = type_labels.get(workout_type, workout_type.title())

    param_parts = []
    if "miles" in kwargs:
        param_parts.append(f"{kwargs['miles']} mi")
    if "lbs" in kwargs and kwargs["lbs"]:
        param_parts.append(f"{kwargs['lbs']} lbs")
    if "weight_lbs" in kwargs:
        param_parts.append(f"{kwargs['weight_lbs']:.0f} lbs")
    if "reps" in kwargs and "sets" in kwargs:
        param_parts.append(f"{kwargs['sets']}×{kwargs['reps']}")
    if reward_override is not None:
        param_parts.append("(full session)")
    param_str = ", ".join(param_parts)

    buff_str = f"  ✨ +{buff_bonus} from sanctuary/relics/blessings" if buff_bonus > 0 else ""
    events.append(f"[{label}] {param_str}  →  +{final} drachmae{buff_str}")

    if workout_number > 1:
        events.append(
            f"  ↳ Workout #{workout_number} today — "
            f"diminishing returns ×{_dr_multiplier(workout_number):.1f} applied"
        )

    # ── Check weekly laurel progress ─────────────────────────────────────────
    _update_weekly_laurel(state, today, events)

    return events


# ---------------------------------------------------------------------------
# Laurel logic
# 3 distinct workout DAYS in an ISO calendar week (Mon–Sun) → +1 laurel.
# Multiple workouts on the same day count as ONE day.
# ---------------------------------------------------------------------------

_WK_TARGET = 3  # distinct workout days per calendar week for a laurel


def _update_weekly_laurel(
    state: PlayerState, today: str, events: List[str]
) -> None:
    """
    Award a laurel on the 3rd distinct workout DAY of any ISO calendar week.
    Multiple workouts logged on the same day count as a single day.

    Uses state.week_log {"YYYY-Www": count} where count = distinct days worked.
    A "{week_key}_laurel_given" flag prevents re-awarding after the target is reached.
    """
    today_date = dt.date.fromisoformat(today)
    iso_year, iso_week, _ = today_date.isocalendar()
    week_key = f"{iso_year}-W{iso_week:02d}"
    laurel_key = f"{week_key}_laurel_given"

    # Already awarded a laurel this week — do not fire again.
    if state.week_log.get(laurel_key):
        return

    # Check if today already counted — look at previous entries in workout_log
    # (current workout was just appended, so exclude workout_log[-1])
    already_counted_today = any(
        entry.get("date") == today
        for entry in state.workout_log[:-1]
    )

    if not already_counted_today:
        current_count = state.week_log.get(week_key, 0)
        if current_count == 0:
            # First workout of this week — check if the previous week was
            # completed. If not, the streak is broken.
            prev_date = today_date - dt.timedelta(weeks=1)
            p_yr, p_wk, _ = prev_date.isocalendar()
            prev_laurel_key = f"{p_yr}-W{p_wk:02d}_laurel_given"
            if not state.week_log.get(prev_laurel_key):
                state.weekly_streak = 0
        # First workout of this day — count it toward the weekly tally
        state.week_log[week_key] = current_count + 1

    count = state.week_log.get(week_key, 0)

    if count >= _WK_TARGET:
        state.laurels += 1
        state.week_log[laurel_key] = 1  # guard: only one laurel per week
        state.weekly_streak = (state.weekly_streak or 0) + 1
        events.append(
            f"  ★ LAUREL EARNED! ({_WK_TARGET} distinct workout days this week) "
            f"→ Total laurels: {state.laurels}"
        )
