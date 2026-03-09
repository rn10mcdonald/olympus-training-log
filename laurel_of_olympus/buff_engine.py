"""
buff_engine.py – Aggregate passive buffs from Sanctuary creatures and Relics.

This module is the single source of truth for the player's current combined
passive bonuses.  Both farm_engine and workout_engine receive the merged buffs
dict so they can scale their outputs accordingly.

Public API:
  get_all_buffs(state) -> dict
      Merge creature (sanctuary) and relic buffs into one dict.
      Multipliers are combined multiplicatively; additive bonuses are summed.

  apply_farm_buff(buffs, farm_type, base_amount) -> int
      Apply the relevant farm multiplier to a raw production amount.

  apply_workout_buff(buffs, workout_type, base_reward) -> float
      Apply the relevant workout multiplier to a raw drachmae reward.

  effective_event_chance(buffs, base_chance) -> float
      Return the event probability after adding any event_chance bonus.
"""

from __future__ import annotations

from laurel_of_olympus.game_state import PlayerState
from laurel_of_olympus import creature_engine, relic_engine, trophy_engine


def _merge_buff(merged: dict, buff_type: str, buff_value: float) -> None:
    """
    Merge a single buff into the accumulated dict.

    Additive types (probabilities/bonuses that sum):
        event_chance, rare_events, laurel_bonus, creature_chance, relic_chance

    All other types are multiplicative (compound multipliers).
    """
    additive_keys = ("event_chance", "rare_events", "laurel_bonus",
                     "creature_chance", "relic_chance")
    if buff_type in additive_keys:
        merged[buff_type] = merged.get(buff_type, 0.0) + buff_value
    else:
        merged[buff_type] = merged.get(buff_type, 1.0) * (1.0 + buff_value)


def get_all_buffs(state: PlayerState) -> dict:
    """
    Merge sanctuary creature buffs, relic buffs, trophy buffs, and active blessings.

    For multiplier keys: buffs multiply together (compound interest style).
    For additive keys ("event_chance", "laurel_bonus", etc.): values sum.

    Active blessing buff keys:
        "blessing_hermes"  → workout_running multiplier (+30%)
        "blessing_demeter" → all_farms multiplier (+50%)
        "blessing_ares"    → army_strength multiplier (+50%)

    Trophy buffs are permanent passive modifiers that stack across all trophies.
    """
    c_buffs = creature_engine.get_sanctuary_buffs(state)
    r_buffs = relic_engine.get_relic_buffs(state)

    merged: dict = dict(c_buffs)
    for key, val in r_buffs.items():
        if key in ("event_chance", "laurel_bonus"):
            merged[key] = merged.get(key, 0) + val
        else:
            merged[key] = merged.get(key, 1.0) * val

    # ── Trophy passive buffs (permanent, stacking) ───────────────────────────
    for tb in trophy_engine.get_trophy_buffs(state):
        _merge_buff(merged, tb["buff_type"], tb["buff_value"])

    # Apply active blessings (MISS-4)
    active = getattr(state, "active_blessings", {}) or {}
    if active.get("hermes", 0) > 0:
        merged["workout_running"] = merged.get("workout_running", 1.0) * 1.30
        merged["blessing_hermes"] = True   # flag for simulate-workout to consume
    if active.get("demeter", 0) > 0:
        merged["all_farms"] = merged.get("all_farms", 1.0) * 1.50
        merged["blessing_demeter"] = True  # flag for farm production to consume
    if active.get("ares", 0) > 0:
        merged["army_strength"] = merged.get("army_strength", 1.0) * 1.50
        merged["blessing_ares"] = True     # flag for campaign to consume

    return merged


def apply_farm_buff(buffs: dict, farm_type: str, base_amount: int) -> int:
    """
    Scale farm production by specific-farm and all-farm multipliers.
    Always returns at least 1 if base_amount > 0.
    """
    specific = buffs.get(f"farm_{farm_type}", 1.0)
    all_farm = buffs.get("all_farms", 1.0)
    result   = base_amount * specific * all_farm
    return max(base_amount, round(result)) if base_amount > 0 else 0


def apply_workout_buff(buffs: dict, workout_type: str, base_reward: float) -> float:
    """
    Scale a workout drachmae reward by the relevant workout multiplier.

    Applies both the type-specific multiplier (e.g. "workout_running") and the
    all-workout multiplier ("workout_all") from drachmae_gain / all_rewards buffs.
    Both are combined multiplicatively.
    """
    type_mult = buffs.get(f"workout_{workout_type}", 1.0)
    all_mult  = buffs.get("workout_all", 1.0)
    return round(base_reward * type_mult * all_mult, 2)


def effective_event_chance(buffs: dict, base_chance: float) -> float:
    """Add any event_chance bonus from relics/creatures to the base probability."""
    return min(1.0, base_chance + buffs.get("event_chance", 0.0))
