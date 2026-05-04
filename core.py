"""
core.py — First Bell training logic
Pure Python, no I/O. Stateless functions that operate on state dicts.
"""

import datetime as dt
import time

# ── Training templates ────────────────────────────────────────────────────────

TEMPLATES = {
    "day_a_glute_legs": {
        "name": "Day A — Glute & Legs",
        "day_type": "strength",
        "focus": "Glutes, quads, hamstrings, lateral hip",
        "bell_guidance": "Hip thrust: 16–20 kg. Split squat: 12–16 kg. Swings: 16–20 kg.",
        "sessions": [
            {
                "week_label": "Build — establish the pattern",
                "main": "KB Hip Thrust 4×10 @ RPE 7",
                "std_kg": 16,
                "accessory": [
                    "Bulgarian Split Squat 3×8/leg (bodyweight or light KB)",
                    "Banded Clamshell 3×20/side",
                    "KB Lateral Lunge 3×8/side",
                    "KB Hammer Curl 3×12",
                ],
                "finisher": "Donkey Kick + Fire Hydrant superset 3×15/side (no rest between sides)",
            },
            {
                "week_label": "Build — add volume",
                "main": "Double KB Front Squat 4×8 @ RPE 6",
                "std_kg": 12,
                "accessory": [
                    "KB Hip Thrust 3×12 (lighter, speed reps)",
                    "Lateral Band Walk 3×20/side",
                    "KB Reverse Lunge 3×10/leg",
                    "KB Zottman Curl 3×10",
                ],
                "finisher": "Goblet Squat Pulse 30 s on / 15 s off × 4",
            },
            {
                "week_label": "Develop — increase load",
                "main": "KB Hip Thrust 4×8 (↑ load from S1) @ RPE 8",
                "std_kg": 20,
                "accessory": [
                    "Bulgarian Split Squat 3×10/leg (add KB)",
                    "Banded Hip Abduction Standing 3×15/side",
                    "KB Curtsy Lunge 3×10/side",
                    "KB Hammer Curl + Tricep Kickback superset 3×10 each",
                ],
                "finisher": "KB Step-Up 30 s / 15 s rest × 5 (alternate legs)",
            },
            {
                "week_label": "Develop — push volume",
                "main": "Double KB Front Squat 5×6 (↑ load) @ RPE 7–8",
                "std_kg": 16,
                "accessory": [
                    "KB Hip Thrust 3×15 (moderate load, full squeeze)",
                    "Banded Clamshell 3×25/side",
                    "KB Lateral Lunge 4×8/side (heavier)",
                    "KB Zottman Curl 3×12",
                ],
                "finisher": "Curtsy Lunge to Lateral Raise AMRAP 3 min",
            },
            {
                "week_label": "Overreach — new top weight",
                "main": "KB Hip Thrust 5×6 (heaviest manageable) @ RPE 8–9",
                "std_kg": 24,
                "accessory": [
                    "Rear-Foot-Elevated Split Squat 3×6/leg (heavy)",
                    "Lateral Band Walk + Monster Walk superset 3×20/side",
                    "Nordic Hamstring Curl 3×5 (eccentric focus)",
                    "KB Overhead Tricep Extension 3×12",
                ],
                "finisher": "Glute Bridge Hold — 45 s max hold × 3 (loaded)",
            },
            {
                "week_label": "Deload — restore and reset",
                "main": "KB Hip Thrust 3×10 @ RPE 5 (light, perfect form)",
                "std_kg": 12,
                "accessory": [
                    "Bodyweight Glute Bridge 3×20 (slow tempo, 2-s hold)",
                    "Banded Clamshell 2×20/side",
                    "KB Goblet Squat 3×10 (light)",
                    "KB Hammer Curl 2×12 (easy)",
                ],
                "finisher": "Hip Flexor Stretch + Pigeon Pose 2 min/side",
            },
        ],
    },

    "day_b_pull_core": {
        "name": "Day B — Pull + Core",
        "day_type": "strength",
        "focus": "Rows, carries, direct abs, arm definition",
        "bell_guidance": "Rows: 12–16 kg. Carries: 16–20 kg. Arm work: 8–12 kg.",
        "sessions": [
            {
                "week_label": "Build — establish pull patterns",
                "main": "KB Bent-Over Row 4×8/side @ RPE 7",
                "std_kg": 12,
                "accessory": [
                    "Farmer Carry 4×30 m",
                    "Hanging Leg Raise 3×8 (or Lying Leg Raise if no bar)",
                    "KB Overhead Tricep Extension 3×12",
                    "TRX Face Pull 3×15 (or Rear-Delt Fly)",
                ],
                "finisher": "Ab Wheel Rollout 3×8 + Hollow Rock 3×15 (superset)",
            },
            {
                "week_label": "Build — volume day",
                "main": "Renegade Row 3×6/side @ RPE 7",
                "std_kg": 12,
                "accessory": [
                    "Suitcase Carry 4×20 m/side",
                    "Pallof Press 3×10/side",
                    "KB Hammer Curl + Zottman Curl superset 3×10 each",
                    "KB Tricep Kickback 3×12/side",
                ],
                "finisher": "Plank Pull-Through 3×15/side + Side Plank 3×30 s/side",
            },
            {
                "week_label": "Develop — increase row load",
                "main": "KB Chest-Supported Row 4×10 (↑ load) @ RPE 7–8",
                "std_kg": 16,
                "accessory": [
                    "Rack Carry 3×30 m/side",
                    "Hanging Leg Raise 3×10",
                    "KB Overhead Tricep Extension 3×15 (lighter, squeeze)",
                    "TRX Face Pull + Y-Raise superset 3×12 each",
                ],
                "finisher": "Hollow Rock 3×20 + Dead Bug 3×10/side (no rest)",
            },
            {
                "week_label": "Develop — pull volume",
                "main": "KB Bent-Over Row 5×8/side (↑ load) @ RPE 8",
                "std_kg": 16,
                "accessory": [
                    "Overhead Carry 3×20 m/side",
                    "Pallof Press 4×10/side (heavier band or greater angle)",
                    "Zottman Curl 3×12",
                    "KB Tricep Kickback 3×15/side",
                ],
                "finisher": "3-Round Core Circuit: 10 Hanging Leg Raise + 15 Hollow Rock + 30 s Side Plank/side",
            },
            {
                "week_label": "Overreach — heaviest pull",
                "main": "KB Renegade Row 4×6/side (heaviest manageable) @ RPE 8–9",
                "std_kg": 16,
                "accessory": [
                    "Farmer Carry 5×30 m (max load)",
                    "Ab Wheel Rollout 3×10",
                    "Pull-Up Negative 3×5 (5-s descent) or Assisted Pull-Up",
                    "KB Overhead Tricep Extension 3×12 (heavier)",
                ],
                "finisher": "Carry Medley: Rack 20 m → Overhead 20 m → Farmer 20 m (no put-down)",
            },
            {
                "week_label": "Deload — light and precise",
                "main": "KB Bent-Over Row 3×8/side @ RPE 5 (light, perfect form)",
                "std_kg": 8,
                "accessory": [
                    "Suitcase Carry 2×20 m/side (light)",
                    "Dead Bug 3×10/side",
                    "KB Hammer Curl 2×12 (easy)",
                    "Shoulder Mobility Flow 2×5 min",
                ],
                "finisher": "Thoracic Rotation Drill 2×10/side + Cat-Cow 2×10",
            },
        ],
    },

    "day_c_hardstyle": {
        "name": "Day C — Hardstyle Full Body",
        "day_type": "strength",
        "focus": "Swings, cleans, presses, snatches — power and conditioning",
        "bell_guidance": "Swings: 16–20 kg. Press/Clean: 12–16 kg. Snatch: 12 kg.",
        "sessions": [
            {
                "week_label": "Build — swing foundation",
                "main": "KB Swing EMOM 20 min (12 reps/min) @ RPE 6",
                "std_kg": 16,
                "accessory": [
                    "KB Clean + Press 3×5/side",
                    "Goblet Squat 3×10",
                    "Push-Up 3×12",
                    "Dead Bug 3×10/side",
                ],
                "finisher": "100 Swings for time (note your time)",
            },
            {
                "week_label": "Build — clean & press day",
                "main": "KB Clean + Press Ladder (1-2-3) × 4/side",
                "std_kg": 12,
                "accessory": [
                    "KB Swing 5×15",
                    "Goblet Squat 3×12",
                    "Renegade Row 3×5/side",
                    "Hollow Rock 3×20",
                ],
                "finisher": "5 Cleans + 5 Presses + 5 Squats/side × 3 (no rest between sides)",
            },
            {
                "week_label": "Develop — swing intensity up",
                "main": "KB Swing EMOM 20 min (15 reps/min) @ RPE 7",
                "std_kg": 16,
                "accessory": [
                    "KB Clean + Push Press 3×5/side",
                    "Goblet Squat 4×10 (heavier)",
                    "Push-Up 3×15",
                    "Pallof Press 3×10/side",
                ],
                "finisher": "Swing Tabata: 20 s on / 10 s off × 8 rounds",
            },
            {
                "week_label": "Develop — snatch introduction",
                "main": "KB Snatch Intervals 8 × 1 min (max reps, switch hand each set)",
                "std_kg": 12,
                "accessory": [
                    "KB High Pull 3×8/side",
                    "KB Swing 3×20",
                    "Goblet Squat 3×12",
                    "Dead Bug 3×10/side",
                ],
                "finisher": "Long Cycle: Clean + Jerk 2×5 min (switch hands each min)",
            },
            {
                "week_label": "Overreach — heavy swing + press",
                "main": "Double KB Swing 10×5 EMOM (heaviest pair) @ RPE 8–9",
                "std_kg": 20,
                "accessory": [
                    "KB Clean + Push Press 4×5/side (heavier)",
                    "Goblet Squat 4×8 (heavy)",
                    "Renegade Row 3×6/side",
                    "Hollow Rock 3×20",
                ],
                "finisher": "200 Swings — every time you set it down, 5 Push-Ups penalty",
            },
            {
                "week_label": "Deload — flow and reset",
                "main": "KB Swing 5×10 @ RPE 5 (light, focus on hip snap technique)",
                "std_kg": 12,
                "accessory": [
                    "KB Clean + Press 2×5/side (light)",
                    "Goblet Squat 2×10 (light)",
                    "TGU 2×1/side (very light, movement quality)",
                    "Hip Flexor Stretch 2×90 s/side",
                ],
                "finisher": "10 min flow: Swing → Goblet Squat → Halo alternating",
            },
        ],
    },

    "day_d_double_kb": {
        "name": "Day D — Double KB Strength",
        "day_type": "strength",
        "focus": "Heavy double KB compounds — overall strength base",
        "bell_guidance": "Double deadlift: 16–24 kg/bell. Double front squat: 12–20 kg/bell. Clean: 12–16 kg/bell.",
        "sessions": [
            {
                "week_label": "Build — double KB introduction",
                "main": "Double KB Deadlift 5×5 @ RPE 7",
                "std_kg": 16,
                "accessory": [
                    "Double KB Front Squat 3×6",
                    "Single-Leg RDL 3×8/side",
                    "KB Suitcase Carry 3×20 m/side",
                    "Banded Clamshell 3×20/side",
                ],
                "finisher": "5 Double Deadlifts + 5 Double Cleans × 4 (rest 90 s)",
            },
            {
                "week_label": "Build — squat focus",
                "main": "Double KB Front Squat 4×6 @ RPE 7",
                "std_kg": 12,
                "accessory": [
                    "Double KB Deadlift 3×5 (moderate)",
                    "KB Hip Thrust 3×12",
                    "Nordic Hamstring Curl 3×5 (eccentric)",
                    "Farmer Carry 4×30 m",
                ],
                "finisher": "Double Front Squat 3 reps EMOM × 8 min",
            },
            {
                "week_label": "Develop — load the deadlift",
                "main": "Double KB Deadlift 5×4 (↑ load) @ RPE 8",
                "std_kg": 20,
                "accessory": [
                    "Double KB Front Squat 4×5 (heavier)",
                    "Single-Leg RDL 3×8/side (heavier)",
                    "KB Suitcase Carry 4×20 m/side",
                    "Banded Hip Abduction 3×15/side",
                ],
                "finisher": "Heavy Complex: Double DL + Double Clean + Double Press × 3/set × 4",
            },
            {
                "week_label": "Develop — squat volume",
                "main": "Double KB Front Squat 5×5 (↑ load) @ RPE 8",
                "std_kg": 16,
                "accessory": [
                    "Double KB Deadlift 4×4 (heavy)",
                    "KB Hip Thrust 4×10 (heavy)",
                    "Nordic Hamstring Curl 3×5 (eccentric)",
                    "Overhead Carry 3×20 m/side",
                ],
                "finisher": "Double Front Squat to failure at RPE 9 × 2 sets",
            },
            {
                "week_label": "Overreach — near-maximal",
                "main": "Double KB Deadlift 6×3 (near-max) @ RPE 9",
                "std_kg": 24,
                "accessory": [
                    "Double KB Front Squat 4×3 (pause at bottom, 2 s)",
                    "Rear-Foot-Elevated Split Squat 3×5/leg (heavy)",
                    "Farmer Carry 5×30 m (max load)",
                    "Banded Clamshell 2×20/side",
                ],
                "finisher": "Max double KB deadlifts in 3 min (note your number)",
            },
            {
                "week_label": "Deload — light and mobile",
                "main": "Double KB Deadlift 3×5 @ RPE 5 (very light, form focus)",
                "std_kg": 12,
                "accessory": [
                    "Double KB Front Squat 2×8 (light)",
                    "Single-Leg RDL 2×8/side (bodyweight or light)",
                    "Hip Flexor Mobilization 2×90 s/side",
                    "Thoracic Rotation Drill 2×10/side",
                ],
                "finisher": "Hip mobility flow 10 min — 90/90, pigeon, world's greatest stretch",
            },
        ],
    },

    "mobility_flow": {
        "name": "Mobility — Flow & Restore",
        "day_type": "mobility",
        "focus": "TGU, windmill, joint prep, thoracic and hip mobility",
        "bell_guidance": "TGU: 8–12 kg. Windmill: 8–12 kg. Go lighter than you think.",
        "sessions": [
            {
                "week_label": "Standard mobility session (~25–30 min)",
                "main": "Turkish Get-Up 3×3/side (light — movement quality only)",
                "std_kg": 8,
                "accessory": [
                    "KB Windmill 3×5/side",
                    "KB Arm Bar 2×60 s/side",
                    "Hip Flexor Stretch 2×90 s/side",
                    "Thoracic Rotation Drill 2×10/side",
                ],
                "finisher": "10 min flow: Cat-Cow → World's Greatest Stretch → Pigeon Pose → 90/90",
            },
            {
                "week_label": "TGU ladder session",
                "main": "TGU Ladder (1-2-3-2-1/side) × 2 (add small load from last session)",
                "std_kg": 10,
                "accessory": [
                    "KB Windmill 3×6/side (slightly heavier)",
                    "KB Bottoms-Up Press 3×5/side (shoulder stability)",
                    "Dead Bug 3×10/side",
                    "Hip Flexor + Glute Stretch 2×2 min/side",
                ],
                "finisher": "TGU AMRAP 6 min (alternating sides, note total reps)",
            },
            {
                "week_label": "Windmill + bent press focus",
                "main": "KB Windmill 4×5/side (heavier than usual) + Bent Press 3×3/side",
                "std_kg": 12,
                "accessory": [
                    "TGU 2×2/side (heavy)",
                    "KB Arm Bar 2×60 s/side",
                    "Thoracic Rotation + Rib Grab 2×10/side",
                    "Pigeon Pose + Hip 90/90 2×2 min/side",
                ],
                "finisher": "5 Windmills + 1 TGU/side × 3 (flow, no rush)",
            },
        ],
    },
}

TRACK_KEYS      = list(TEMPLATES.keys())
SESSIONS_NEEDED = 6
WK_TARGET       = 4   # activities/week for streak

# ── Movement registry ─────────────────────────────────────────────────────────

_MOVEMENT_TABLE = [
    # KB — Hip/Glute
    ("kb_hip_thrust",           "KB Hip Thrust",              "glute",      16, "4×10"),
    ("kb_glute_bridge",         "KB Glute Bridge",            "glute",      16, "3×15"),
    # KB — Swing
    ("kb_swing",                "KB Swing",                   "swing",      16, "5×15"),
    ("kb_double_swing",         "Double KB Swing",            "swing",      16, "5×10"),
    ("kb_american_swing",       "American Swing",             "swing",      12, "EMOM 10"),
    # KB — Snatch
    ("kb_snatch",               "KB Snatch",                  "snatch",     12, "10×6/side"),
    ("kb_half_snatch",          "KB Half Snatch",             "snatch",     12, "3×8/side"),
    # KB — Clean
    ("kb_clean",                "KB Clean",                   "clean",      12, "5×5/side"),
    ("kb_double_clean",         "Double KB Clean",            "clean",      12, "5×5"),
    ("kb_clean_press",          "KB Clean + Press",           "press",      12, "5×5/side"),
    # KB — Press
    ("kb_press",                "KB Press",                   "press",      12, "5×5/side"),
    ("kb_push_press",           "KB Push-Press",              "press",      12, "5×5/side"),
    ("kb_jerk",                 "KB Jerk",                    "press",      12, "2×5 min"),
    ("kb_long_cycle",           "Long Cycle C&J",             "press",      12, "2×5 min"),
    ("kb_floor_press",          "KB Floor Press",             "press",      12, "3×8/side"),
    ("kb_bottoms_up_press",     "Bottoms-Up Press",           "press",       8, "3×5/side"),
    ("kb_oh_tricep_ext",        "KB Overhead Tricep Ext",     "arms",        8, "3×12"),
    ("kb_tricep_kickback",      "KB Tricep Kickback",         "arms",        8, "3×12/side"),
    ("kb_hammer_curl",          "KB Hammer Curl",             "arms",        8, "3×12"),
    ("kb_zottman_curl",         "KB Zottman Curl",            "arms",        8, "3×10"),
    # KB — Squat
    ("kb_goblet_squat",         "Goblet Squat",               "squat",      16, "4×10"),
    ("kb_front_squat",          "Double KB Front Squat",      "squat",      12, "5×5"),
    ("kb_lateral_lunge",        "KB Lateral Lunge",           "squat",      12, "3×8/side"),
    ("kb_curtsy_lunge",         "KB Curtsy Lunge",            "squat",      12, "3×10/side"),
    ("kb_reverse_lunge",        "KB Reverse Lunge",           "squat",      12, "3×10/leg"),
    ("kb_step_up",              "KB Step-Up",                 "squat",      12, "3×12/leg"),
    # KB — Hinge
    ("kb_deadlift",             "KB Deadlift",                "hinge",      16, "5×5"),
    ("kb_double_deadlift",      "Double KB Deadlift",         "hinge",      16, "5×5"),
    ("kb_rdl",                  "KB RDL",                     "hinge",      16, "4×8/side"),
    ("kb_suitcase_dl",          "Suitcase Deadlift",          "hinge",      16, "3×5/side"),
    ("kb_sl_rdl",               "Single-Leg RDL",             "hinge",      12, "3×8/side"),
    ("kb_high_pull",            "KB High Pull",               "hinge",      16, "3×8/side"),
    # KB — Get-Up / Windmill
    ("kb_tgu",                  "Turkish Get-Up",             "get_up",      8, "5×3/side"),
    ("kb_windmill",             "KB Windmill",                "get_up",     12, "3×5/side"),
    ("kb_bent_press",           "Bent Press",                 "get_up",     12, "4×3/side"),
    ("kb_arm_bar",              "KB Arm Bar",                 "get_up",      8, "2×60 s/side"),
    # KB — Row
    ("kb_row",                  "KB Bent-Over Row",           "row",        12, "4×8/side"),
    ("kb_renegade_row",         "Renegade Row",               "row",        12, "3×6/side"),
    ("kb_chest_supported_row",  "KB Chest-Supported Row",     "row",        12, "4×10"),
    # KB — Carry
    ("kb_farmer_carry",         "Farmer Carry",               "carry",      16, "4×30 m"),
    ("kb_rack_carry",           "Rack Carry",                 "carry",      12, "3×30 m/side"),
    ("kb_oh_carry",             "Overhead Carry",             "carry",      12, "3×20 m/side"),
    ("kb_suitcase_carry",       "Suitcase Carry",             "carry",      16, "4×20 m/side"),
    ("kb_bu_carry",             "Bottoms-Up Carry",           "carry",       8, "3×20 m/side"),
    # Bodyweight
    ("bw_push_up",              "Push-Up",                    "bodyweight",  0, "3×15"),
    ("bw_pull_up",              "Pull-Up",                    "bodyweight",  0, "4×5"),
    ("bw_bulgarian",            "Bulgarian Split Squat",      "bodyweight",  0, "3×8/leg"),
    ("bw_nordic_curl",          "Nordic Hamstring Curl",      "bodyweight",  0, "3×5 (ecc)"),
    ("bw_hip_bridge",           "Glute Bridge",               "bodyweight",  0, "3×15"),
    ("bw_clamshell",            "Banded Clamshell",           "bodyweight",  0, "3×20/side"),
    ("bw_lateral_band_walk",    "Lateral Band Walk",          "bodyweight",  0, "3×20/side"),
    ("bw_donkey_kick",          "Donkey Kick",                "bodyweight",  0, "3×15/side"),
    ("bw_fire_hydrant",         "Fire Hydrant",               "bodyweight",  0, "3×15/side"),
    ("bw_plank",                "Plank",                      "core",        0, "3×45 s"),
    ("bw_dead_bug",             "Dead Bug",                   "core",        0, "3×10/side"),
    ("bw_hollow_rock",          "Hollow Rock",                "core",        0, "3×20"),
    ("bw_ab_wheel",             "Ab Wheel Rollout",           "core",        0, "3×8"),
    ("bw_hanging_leg_raise",    "Hanging Leg Raise",          "core",        0, "3×10"),
    ("bw_pallof",               "Pallof Press",               "core",        0, "3×10/side"),
    ("bw_face_pull",            "TRX Face Pull",              "bodyweight",  0, "3×15"),
    ("bw_lunge",                "Lunge",                      "bodyweight",  0, "3×10/leg"),
    ("bw_box_jump",             "Box Jump",                   "bodyweight",  0, "3×8"),
    ("bw_burpee",               "Burpee",                     "bodyweight",  0, "3×10"),
]


def get_movements() -> list:
    return [
        {"slug": s, "name": n, "category": c, "std_kg": kg, "hint": h}
        for s, n, c, kg, h in _MOVEMENT_TABLE
    ]


# ── Default state ─────────────────────────────────────────────────────────────

def default_state() -> dict:
    return {
        "track":                    TRACK_KEYS[0],
        "cycle_week":               1,
        "strength_sessions_in_wave": 0,
        "microcycle": {
            "id":                 0,
            "sessions_completed": 0,
            "start_date":         str(dt.date.today()),
            "completed":          False,
        },
        "workouts":           [],
        "ruck_log":           [],
        "run_log":            [],
        "walk_log":           [],
        "week_log":           {},
        "custom_tracks":      [],
        "templates":          {k: v["name"] for k, v in TEMPLATES.items()},
        "total_ruck_miles":   0.0,
        "total_run_miles":    0.0,
        "total_walk_miles":   0.0,
        "journey_miles":      0.0,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_custom_track(state: dict, track_key: str) -> dict | None:
    if not track_key or not track_key.startswith("custom_"):
        return None
    track_id = track_key[7:]
    for ct in state.get("custom_tracks", []):
        if str(ct.get("id", "")) == str(track_id):
            return ct
    return None


def _week_key(d: dt.date) -> str:
    iso = d.isocalendar()
    return f"{iso[0]}-{iso[1]:02d}"


def _increment_weekly_count(state: dict) -> None:
    wk = _week_key(dt.date.today())
    state.setdefault("week_log", {})
    state["week_log"][wk] = state["week_log"].get(wk, 0) + 1


# ── Public API ────────────────────────────────────────────────────────────────

def get_today_workout(state: dict) -> dict:
    track = state.get("track")
    if not track:
        return {"status": "no_track", "message": "No track selected."}

    if track.startswith("custom_"):
        ct = _get_custom_track(state, track)
        if ct is None:
            return {"status": "no_track",
                    "message": "Custom track not found. Please select a new track."}
        sessions_needed = len(ct["sessions"])
        mc  = state["microcycle"]
        idx = mc["sessions_completed"]
        if idx >= sessions_needed:
            return {"status": "cycle_complete",
                    "message": "Cycle complete! Start a new track."}
        sess = ct["sessions"][idx]
        return {
            "status":           "active",
            "track_key":        track,
            "track_name":       ct["name"],
            "day_type":         "strength",
            "focus":            "",
            "week_label":       sess.get("week_label", ""),
            "session_idx":      idx,
            "total_sessions":   sessions_needed,
            "main":             sess.get("main", ""),
            "std_kg":           float(sess.get("std_kg", 16) or 16),
            "accessory":        sess.get("accessory", []),
            "finisher":         sess.get("finisher", ""),
            "bell_guidance":    "",
            "cycle_week":       state.get("cycle_week", 1),
            "suggested_weight": float(sess.get("std_kg", 16) or 16),
        }

    if track not in TEMPLATES:
        return {"status": "no_track", "message": "No track selected."}

    tpl = TEMPLATES[track]
    mc  = state["microcycle"]
    idx = mc["sessions_completed"]
    sessions_needed = len(tpl["sessions"])
    if idx >= sessions_needed:
        return {"status": "cycle_complete",
                "message": "Cycle complete! Select a new session or restart the track."}

    sess = tpl["sessions"][idx]
    std_kg = float(sess.get("std_kg", 16) or 16)
    return {
        "status":           "active",
        "track_key":        track,
        "track_name":       tpl["name"],
        "day_type":         tpl.get("day_type", "strength"),
        "focus":            tpl.get("focus", ""),
        "week_label":       sess.get("week_label", ""),
        "session_idx":      idx,
        "total_sessions":   sessions_needed,
        "main":             sess["main"],
        "std_kg":           std_kg,
        "accessory":        sess["accessory"],
        "finisher":         sess["finisher"],
        "bell_guidance":    tpl.get("bell_guidance", ""),
        "cycle_week":       state.get("cycle_week", 1),
        "suggested_weight": std_kg,
    }


def get_track_detail(key: str) -> dict | None:
    if key not in TEMPLATES:
        return None
    t = TEMPLATES[key]
    return {
        "key":          key,
        "name":         t["name"],
        "day_type":     t.get("day_type", "strength"),
        "focus":        t.get("focus", ""),
        "bell_guidance": t.get("bell_guidance", ""),
        "sessions":     t["sessions"],
    }


def get_custom_track_detail(state: dict, track_id: str) -> dict | None:
    for ct in state.get("custom_tracks", []):
        if str(ct.get("id", "")) == str(track_id):
            return ct
    return None


def init_track(state: dict, key: str) -> str:
    if key.startswith("custom_"):
        ct = _get_custom_track(state, key)
        if ct is None:
            return f"Custom track not found: {key}"
        state["track"] = key
        state["microcycle"] = {
            "id":                 state["microcycle"]["id"] + 1,
            "sessions_completed": 0,
            "start_date":         str(dt.date.today()),
            "completed":          False,
        }
        return f"Started {ct['name']}"
    if key not in TEMPLATES:
        return f"Unknown track: {key}"
    state["track"] = key
    state["microcycle"] = {
        "id":                 state["microcycle"]["id"] + 1,
        "sessions_completed": 0,
        "start_date":         str(dt.date.today()),
        "completed":          False,
    }
    return f"Started {TEMPLATES[key]['name']}"


def log_rec(state: dict, weights_lbs: dict | None = None) -> str:
    track = state.get("track")
    if not track:
        return "No active track. Please select a track first."
    mc  = state["microcycle"]
    idx = mc["sessions_completed"]

    if track.startswith("custom_"):
        ct = _get_custom_track(state, track)
        if ct is None:
            return "Custom track not found. Please select a new track."
        if idx >= len(ct["sessions"]):
            return "Cycle complete. Select a new track."
        tpl = ct["sessions"][idx]
        day_type = "strength"
    elif track not in TEMPLATES:
        return "No active track. Please select a track first."
    else:
        sessions_needed = len(TEMPLATES[track]["sessions"])
        if idx >= sessions_needed:
            return "Cycle complete. Select a new track or restart."
        tpl = TEMPLATES[track]["sessions"][idx]
        day_type = TEMPLATES[track].get("day_type", "strength")

    entry: dict = {
        "date":        str(dt.date.today()),
        "type":        "recommended",
        "details":     tpl["main"],
        "track":       track,
        "session_idx": idx,
        "day_type":    day_type,
    }

    if weights_lbs:
        stored: dict = {}
        for k, v in weights_lbs.items():
            try:
                f = float(v or 0)
                if f > 0:
                    stored[k] = f
            except (TypeError, ValueError):
                pass
        if stored:
            entry["weights_lbs"] = stored

    state["workouts"].append(entry)
    mc["sessions_completed"] += 1
    _increment_weekly_count(state)

    if day_type == "strength":
        state["strength_sessions_in_wave"] = state.get("strength_sessions_in_wave", 0) + 1
        if state["strength_sessions_in_wave"] >= SESSIONS_NEEDED:
            state["strength_sessions_in_wave"] = 0
            state["cycle_week"] = (state.get("cycle_week", 1) % 4) + 1

    return f"Session logged: {tpl['main']}"


def log_custom(state: dict, text: str) -> str:
    state["workouts"].append({
        "date":     str(dt.date.today()),
        "type":     "custom",
        "details":  text,
        "day_type": "custom",
    })
    state["microcycle"]["sessions_completed"] += 1
    _increment_weekly_count(state)
    return f"Custom workout logged: {text[:80]}"


def log_ruck(state: dict, miles: float, pounds: float) -> str:
    state["ruck_log"].append({
        "date":           str(dt.date.today()),
        "distance_miles": miles,
        "weight_lbs":     pounds,
    })
    state["total_ruck_miles"] = state.get("total_ruck_miles", 0.0) + miles
    prev = state.get("journey_miles", 0.0)
    state["journey_miles"] = prev + miles
    _increment_weekly_count(state)
    return f"Ruck logged: {miles:.1f} mi @ {pounds:.0f} lbs"


def log_run(state: dict, miles: float, pace: float | None = None) -> str:
    entry: dict = {
        "date":           str(dt.date.today()),
        "distance_miles": miles,
    }
    if pace is not None:
        entry["pace_min_per_mile"] = pace
    state.setdefault("run_log", []).append(entry)
    state["total_run_miles"] = state.get("total_run_miles", 0.0) + miles
    prev = state.get("journey_miles", 0.0)
    state["journey_miles"] = prev + miles
    _increment_weekly_count(state)
    return f"Run logged: {miles:.1f} mi"


def log_walk(state: dict, miles: float) -> str:
    state.setdefault("walk_log", []).append({
        "date":           str(dt.date.today()),
        "distance_miles": miles,
    })
    state["total_walk_miles"] = state.get("total_walk_miles", 0.0) + miles
    prev = state.get("journey_miles", 0.0)
    state["journey_miles"] = prev + miles
    _increment_weekly_count(state)
    return f"Walk logged: {miles:.1f} mi"


def get_streak_info(state: dict) -> dict:
    today    = dt.date.today()
    wk_log   = state.get("week_log", {})
    curr_key = _week_key(today)
    this_week = wk_log.get(curr_key, 0)

    # Count consecutive completed weeks going backwards from last week
    streak_weeks = 0
    check = today - dt.timedelta(weeks=1)
    while True:
        k = _week_key(check)
        if wk_log.get(k, 0) >= WK_TARGET:
            streak_weeks += 1
            check -= dt.timedelta(weeks=1)
        else:
            break
    # Include current week if already hit
    if this_week >= WK_TARGET:
        streak_weeks += 1

    last_week_date = today - dt.timedelta(weeks=1)
    last_week_hit  = wk_log.get(_week_key(last_week_date), 0) >= WK_TARGET

    # ISO week: Mon=1, Sun=7. Days remaining = 7 - isoweekday
    days_remaining      = 7 - today.isoweekday()
    activities_remaining = max(0, WK_TARGET - this_week)

    return {
        "week_target":         WK_TARGET,
        "this_week":           this_week,
        "streak_weeks":        streak_weeks,
        "last_week_hit":       last_week_hit,
        "days_remaining":      days_remaining,
        "activities_remaining": activities_remaining,
    }


def get_next_weight(state: dict, movement_slug: str) -> float | None:
    for w in reversed(state.get("workouts", [])):
        wl = w.get("weights_lbs", {})
        if wl and "main" in wl:
            main_kg = float(wl["main"]) * 0.453592
            return round(main_kg)
    return None


def get_week_summary(state: dict) -> dict:
    today      = dt.date.today()
    iso        = today.isocalendar()
    week_start = today - dt.timedelta(days=iso[2] - 1)
    week_end   = week_start + dt.timedelta(days=6)

    summary: dict = {"strength": 0, "mobility": 0, "cardio": 0, "total": 0}

    for w in state.get("workouts", []):
        try:
            d = dt.date.fromisoformat(w["date"])
        except (KeyError, ValueError):
            continue
        if week_start <= d <= week_end:
            track    = w.get("track", "")
            day_type = TEMPLATES.get(track, {}).get("day_type", "strength") if track in TEMPLATES else "strength"
            summary[day_type] = summary.get(day_type, 0) + 1
            summary["total"] += 1

    for log_key in ("ruck_log", "run_log", "walk_log"):
        for entry in state.get(log_key, []):
            try:
                d = dt.date.fromisoformat(entry["date"])
            except (KeyError, ValueError):
                continue
            if week_start <= d <= week_end:
                summary["cardio"] += 1
                summary["total"]  += 1

    return summary


# ── Custom track management ───────────────────────────────────────────────────

def save_custom_track(state: dict, name: str, sessions: list) -> dict:
    name = (name or "").strip()
    if not name:
        raise ValueError("Track name cannot be empty.")
    if not sessions:
        raise ValueError("A cycle must have at least 1 session.")
    if len(sessions) > 6:
        raise ValueError("A cycle can have at most 6 sessions.")

    cleaned: list = []
    for i, s in enumerate(sessions):
        main = str(s.get("main", "")).strip()
        if not main:
            raise ValueError(f"Session {i + 1} needs a main movement.")
        acc      = [str(a).strip() for a in s.get("accessory", []) if str(a).strip()]
        finisher = str(s.get("finisher", "")).strip()
        try:
            std_kg = float(s.get("std_kg", 16) or 16)
        except (TypeError, ValueError):
            std_kg = 16.0
        cleaned.append({
            "week_label": str(s.get("week_label", f"Session {i + 1}")).strip(),
            "main":       main,
            "std_kg":     std_kg,
            "accessory":  acc,
            "finisher":   finisher,
        })

    track_id = str(int(time.time() * 1000))
    track: dict = {"id": track_id, "name": name, "sessions": cleaned}
    state.setdefault("custom_tracks", []).append(track)
    return track


def delete_custom_track(state: dict, track_id: str) -> bool:
    tracks     = state.get("custom_tracks", [])
    new_tracks = [t for t in tracks if str(t.get("id", "")) != str(track_id)]
    if len(new_tracks) == len(tracks):
        return False
    state["custom_tracks"] = new_tracks
    if state.get("track") == f"custom_{track_id}":
        state["track"] = TRACK_KEYS[0]
    return True
