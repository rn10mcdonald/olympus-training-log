"""
core.py — First Bell training logic
Pure Python, no I/O. Stateless functions that operate on state dicts.
"""

import datetime as dt
import re
import time

# ── Program Data — Fighter (4-week repeating wave) + Kyle (12-week arc) ───────


# ── Fighter Program Data (v3) ───────────────────────────────────────────────
#  Circuit-based strength + HS-5K-style running structure. Replaces the old
#  12-week Foundation/Development/Performance arc (PROGRAM_1/2/3 body-comp
#  split) with a single repeating 4-week wave: LEARN -> BUILD -> SHARPEN ->
#  RESTORE. Source design doc: fighter_program_v3_revamp.py.
#
#  Schema note: v3's original "circuit"/"rounds"/"rest_between_*_sec" shape
#  is folded into the existing renderer's fields so get_today_workout and
#  index.html need no new parsing branch for strength days:
#    main             = circuit[0]           (anchor lift, has "@ N kg" for
#                                              suggested-weight parsing)
#    full_body_block   = circuit[1:]          (remaining circuit movements)
#    focus_work         = [rounds/rest recap]  (single info line)
#    arms                = []                  (v3 has no arm isolation block —
#                                              skill finishers replace it)
#    finisher            = unchanged
# ==========================================================================

# ── Rehab, tied to run type (per Rena's call): easy runs get the lower-
#    body/running rehab; interval + long runs get shoulder/posture rehab.
#    Carried over unchanged from the old "mobility" dict — v3 intentionally
#    left this out, it wasn't meant to be cut. ───────────────────────────────
FIGHTER_REHAB_LOWER = [
    "Overhead Rod Squat 2×8  — Dowel overhead, sit deep. Opens ankles and thoracic for running posture.",
    "Calf Raise — straight-leg 2×15 + bent-knee 2×15  — Both hit the calf differently. Slow down — this is shin-splint armor.",
    "Tibialis Raise 2×15  — Heels down, pull toes to shins hard. The muscle that fails first in shin splints; most runners never train it.",
    "Single-Leg Balance 2×30s/side  — Bare feet. Wobble is the work — it's ankle stability for the run.",
    "Hip Flexor + Glute Activation 2×10/side  — Wake up the glutes so they fire on the run instead of the low back.",
]

FIGHTER_REHAB_SHOULDER = [
    "TRX Face Pull 3×15  — Elbows high, pull to forehead, squeeze blades. Undoes desk and microscope posture.",
    "TRX Y-T-W 2×8 each  — Three positions, light and slow. Lower-trap and rear-delt work for the webcam posture.",
    "Band/TRX External Rotation 2×12/side  — Elbow pinned to your side. Rotator cuff health for pressing.",
    "Band Pull-Apart 2×20  — Arms straight, pull the band to your chest, squeeze the upper back.",
    "Thread the Needle 2×8/side  — Thoracic rotation — opens the mid-back that rounds at your desk.",
]

FIGHTER_STRETCH_LOWER = [
    "World's Greatest Stretch 2×5/side  — Hits hips, hamstrings, thoracic in one shot.",
    "Pigeon Pose 2×60s/side  — Deep glute and hip after the run.",
    "Standing Calf + Hamstring Stretch 2×30s/side  — Post-run lengthening.",
]

FIGHTER_STRETCH_SHOULDER = [
    "Downward Dog → Cobra flow 2×6  — Decompress the spine, open the chest.",
    "Doorway Pec Stretch 2×30s/side  — Counters the forward-shoulder desk posture.",
    "Child's Pose with Lateral Reach 2×45s/side  — Lat and side-body length to finish.",
]

# ── Benchmark — repeat Week 1 and Week 4 of every cycle ─────────────────────
BENCHMARK = {
    "test": "100 KB Swings for time @ 16 kg",
    "when": "Week 1 (baseline) and Week 4 (retest)",
    "purpose": (
        "The one number that tells you if conditioning actually moved, "
        "instead of trusting that circuits 'felt hard' each week. Write "
        "down the time both weeks and compare."
    ),
}


# ── STRENGTH — HINGE  (Monday) ───────────────────────────────────────────
#  Anchor: Double KB RDL. 4 rounds, minimal rest between moves.
STRENGTH_HINGE = {
    "name":   "Hinge Day",
    "anchor": "Double KB RDL",
    "focus":  "Posterior chain — RDL, swing, and core stability in one dense circuit (35-40 min)",
    "weeks": {
        1: {
            "label": "Week 1 — Learn the circuit, own each movement.",
            "main":  "Double KB RDL 8 reps @ 16 kg/bell  — Hips back first, flat back, bells stay close to the shins.",
            "full_body_block": [
                "Single-Arm Swing 10/side @ 16 kg  — Shoulder packed, resist the twist as the bell floats.",
                "Renegade Row 6/side @ 8 kg  — Plank stays square, don't let the hips rotate toward the pulling arm.",
                "Suitcase Hold 30s/side @ 16 kg  — Resist the lean — that's the only rep that counts.",
            ],
            "focus_work": [],
            "circuit_note": "4 rounds — 30s rest between moves, 90s between rounds.",
            "arms": [],
            "finisher": "BENCHMARK BASELINE — 100 KB Swings for time @ 16 kg. Write it down, retest Week 4. Then Windmill ladder @ 8 kg — 1 rep/side at :30, add a rep/side every 30s, cap at 6 min.",
        },
        2: {
            "label": "Week 2 — Build. More reps, tighter density.",
            "main":  "Double KB RDL 10 reps @ 16 kg/bell  — Same load, more reps. Feel the hamstring, not the low back.",
            "full_body_block": [
                "Single-Arm Swing 12/side @ 16 kg  — Crisper hip snap each rep.",
                "Renegade Row 8/side @ 8 kg  — Slow the tempo down as the reps climb.",
                "Suitcase Hold 30s/side @ 20 kg  — Heavier hold, same brace.",
            ],
            "focus_work": [],
            "circuit_note": "4 rounds — 25s rest between moves, 75s between rounds.",
            "arms": [],
            "finisher": "Windmill ladder @ 8 kg — same format, try to beat last week's cap.",
        },
        3: {
            "label": "Week 3 — Sharpen. Heavier where it counts.",
            "main":  "Double KB RDL 8 reps @ 20 kg/bell  — Up a bell. Same clean hinge, no back rounding.",
            "full_body_block": [
                "Single-Arm Swing 10/side @ 20 kg  — Heavier bell, full power each rep.",
                "Renegade Row 8/side @ 12 kg  — Up a bell. Plank discipline over speed.",
                "Suitcase Hold 25s/side @ 24 kg  — Heaviest hold of the block.",
            ],
            "focus_work": [],
            "circuit_note": "4 rounds — 20s rest between moves, 60s between rounds.",
            "arms": [],
            "finisher": "Arm Bar 2×90s/side @ 8 kg — slow, deliberate, full shoulder packing.",
        },
        4: {
            "label": "Week 4 — Restore. Lighter, clean, retest the benchmark.",
            "main":  "Double KB RDL 8 reps @ 16 kg/bell  — Light. Pure technique.",
            "full_body_block": [
                "Single-Arm Swing 10/side @ 16 kg  — Float it.",
                "Renegade Row 6/side @ 8 kg  — Easy, controlled.",
                "Suitcase Hold 30s/side @ 16 kg  — Light, clean brace.",
            ],
            "focus_work": [],
            "circuit_note": "3 rounds — 30s rest between moves, 90s between rounds.",
            "arms": [],
            "finisher": "BENCHMARK RETEST — 100 KB Swings for time @ 16 kg. Compare to Week 1.",
        },
    },
}


# ── STRENGTH — SWING / CONDITIONING  (Saturday) ─────────────────────────
#  Anchor: KB Swing. Highest metabolic day of the week.
STRENGTH_SWING_CONDITIONING = {
    "name":   "Swing / Conditioning Day",
    "anchor": "KB Swing",
    "focus":  "Metabolic circuit — swing volume leads, everything else supports it (30-35 min)",
    "weeks": {
        1: {
            "label": "Week 1 — Learn the pace. This should feel like conditioning, not lifting.",
            "main":  "Single-Arm Swing 12/side @ 16 kg  — Hike hard, snap hips, bell floats.",
            "full_body_block": [
                "Goblet Squat Hold 30s @ 16 kg  — Sit deep, elbows pry knees, breathe through it.",
                "Figure-8 10 passes @ 12 kg  — Hand to hand between the legs, stay low.",
                "Halo 8/side @ 8 kg  — Bell circles the head, ribs stay down, don't arch.",
            ],
            "focus_work": [],
            "circuit_note": "4 rounds — 30s rest between moves, 90s between rounds.",
            "arms": [],
            "finisher": "Swing EMOM 6 min: 10/side @ 16 kg — note total reps, this is your week-to-week number to beat.",
        },
        2: {
            "label": "Week 2 — Build density.",
            "main":  "Single-Arm Swing 12/side @ 20 kg  — Up a bell.",
            "full_body_block": [
                "Goblet Squat Hold 35s @ 20 kg  — Heavier hold.",
                "Figure-8 12 passes @ 12 kg  — More passes, same low stance.",
                "Halo 10/side @ 8 kg  — More reps, control the circle.",
            ],
            "focus_work": [],
            "circuit_note": "4 rounds — 25s rest between moves, 75s between rounds.",
            "arms": [],
            "finisher": "Swing EMOM 6 min: beat Week 1's total @ 16-20 kg.",
        },
        3: {
            "label": "Week 3 — Sharpen. Heaviest, densest day of the block.",
            "main":  "Single-Arm Swing 15/side @ 20 kg  — Highest volume of the block.",
            "full_body_block": [
                "Goblet Squat Hold 40s @ 20 kg  — Longest hold of the block.",
                "Figure-8 12 passes @ 16 kg  — Up a bell.",
                "Halo 8/side @ 12 kg  — Up a bell, control over speed.",
            ],
            "focus_work": [],
            "circuit_note": "4 rounds — 20s rest between moves, 60s between rounds.",
            "arms": [],
            "finisher": "Swing EMOM 8 min: beat Week 2's total.",
        },
        4: {
            "label": "Week 4 — Restore, light.",
            "main":  "Single-Arm Swing 10/side @ 16 kg  — Light, technical.",
            "full_body_block": [
                "Goblet Squat Hold 30s @ 16 kg  — Easy.",
                "Figure-8 10 passes @ 12 kg  — Smooth.",
                "Halo 8/side @ 8 kg  — Light.",
            ],
            "focus_work": [],
            "circuit_note": "3 rounds — 30s rest between moves, 90s between rounds.",
            "arms": [],
            "finisher": "Easy swing flow 5 min @ 16 kg — no counting, just clean reps.",
        },
    },
}


# ── STRENGTH — SQUAT / HIP THRUST  (Sunday) ──────────────────────────────
#  Anchor: Hip Thrust. Second glute/leg exposure of the week alongside Hinge.
STRENGTH_SQUAT_HIPTHRUST = {
    "name":   "Squat / Hip Thrust Day",
    "anchor": "Two-Hand KB Hip Thrust",
    "focus":  "Glute/leg strength circuit, indoor-friendly stability work (35-40 min)",
    "weeks": {
        1: {
            "label": "Week 1 — Learn the circuit.",
            "main":  "KB Hip Thrust 10 reps @ 20 kg  — Ribs down, chin tucked, squeeze 1 sec at lockout.",
            "full_body_block": [
                "Goblet Squat 8 reps @ 16 kg  — Elbows pry knees apart, chest proud.",
                "Bottoms-Up Press 6/side @ 8 kg  — Bell upside down — grip and shoulder do all the work, don't let it tip.",
                "Waiter's Carry March 20 steps (in place) @ 12 kg  — Overhead, knee drives up, ribs stay down.",
            ],
            "focus_work": [],
            "circuit_note": "4 rounds — 30s rest between moves, 90s between rounds.",
            "arms": [],
            "finisher": "Arm Bar ladder @ 8 kg — 1 rep/side at :30, add a rep/side every 30s, cap at 6 min.",
        },
        2: {
            "label": "Week 2 — Build. More reps, same load.",
            "main":  "KB Hip Thrust 12 reps @ 20 kg  — Same load, more reps.",
            "full_body_block": [
                "Goblet Squat 10 reps @ 16 kg  — Add reps, pause 1 sec at the bottom.",
                "Bottoms-Up Press 8/side @ 8 kg  — More reps, same tight grip.",
                "Waiter's Carry March 20 steps @ 16 kg  — Heavier bell overhead.",
            ],
            "focus_work": [],
            "circuit_note": "4 rounds — 25s rest between moves, 75s between rounds.",
            "arms": [],
            "finisher": "Arm Bar ladder @ 8 kg — beat last week's cap.",
        },
        3: {
            "label": "Week 3 — Sharpen. Heaviest day of the block.",
            "main":  "KB Hip Thrust 8 reps @ 24 kg  — Heaviest of the block. Earn the lockout.",
            "full_body_block": [
                "Goblet Squat 8 reps @ 20 kg  — Up a bell, stay tall.",
                "Bottoms-Up Press 6/side @ 12 kg  — Up a bell, control over speed.",
                "Waiter's Carry March 24 steps @ 16 kg  — More steps, same lockout.",
            ],
            "focus_work": [],
            "circuit_note": "4 rounds — 20s rest between moves, 60s between rounds.",
            "arms": [],
            "finisher": "Windmill 2×90s/side @ 8 kg — slow, full range.",
        },
        4: {
            "label": "Week 4 — Restore.",
            "main":  "KB Hip Thrust 10 reps @ 16 kg  — Light, pure squeeze.",
            "full_body_block": [
                "Goblet Squat 8 reps @ 12 kg  — Easy, breathe.",
                "Bottoms-Up Press 6/side @ 8 kg  — Light, technical.",
                "Waiter's Carry March 20 steps @ 12 kg  — Easy.",
            ],
            "focus_work": [],
            "circuit_note": "3 rounds — 30s rest between moves, 90s between rounds.",
            "arms": [],
            "finisher": "Easy flow 5 min @ 12 kg: hip thrust -> squat -> halo, repeat.",
        },
    },
}


# ==========================================================================
#  RUNNING — "TRAIN LIKE AN HS 5K RUNNER"
#  Easy days + one dedicated interval/speed day + one long run.
#  10%/week mileage climb on easy+long days, cutback every 4th week.
# ==========================================================================

# Easy/Long mileage below is v3's own "+10%/week, cutback ~70% wk4" rule
# made explicit — anchored to Rena's last documented easy-run baseline
# (~3.7 mi, Zone 2, ~14:00/mi, run/walk 2:1→3:1; see old Program 3 mobility
# text) rather than a guessed number. Long = ~12% longer than that week's
# easy run, per v3's "10-15% longer" rule.
RUN_EASY = {
    "name": "Easy Run",
    "purpose": "Aerobic base — this is where the weekly mileage build lives.",
    "rehab":   FIGHTER_REHAB_LOWER,
    "stretch": FIGHTER_STRETCH_LOWER,
    "weeks": {
        1: {"label": "Week 1", "run_line": "3.7 mi easy, run/walk 2:1, Zone 2 (HR ~130s, ~14:00/mi pace)."},
        2: {"label": "Week 2", "run_line": "4.0 mi easy, run/walk 2:1→3:1, Zone 2 (HR ~130s, ~14:00/mi pace)."},
        3: {"label": "Week 3", "run_line": "4.4 mi easy, run/walk 3:1, Zone 2 (HR ~130s, ~14:00/mi pace)."},
        4: {"label": "Week 4 — cutback", "run_line": "3.1 mi easy, light effort. Zone 2, ~14:00/mi pace."},
    },
}

RUN_INTERVAL = {
    "name": "Interval / Speed Day",
    "purpose": "The dedicated speed stimulus — this is what makes it feel like training toward something.",
    "non_negotiables": [
        "1 mile continuous warmup, no stopping — this is your calf's proven safe distance.",
        "1 min walk between every interval rep, always — non-negotiable regardless of how easy the reps feel.",
        "Pace = perceived effort ('comfortably hard, could hold a short conversation') until a time trial sets a real number.",
    ],
    "rehab":   FIGHTER_REHAB_SHOULDER,
    "stretch": FIGHTER_STRETCH_SHOULDER,
    "weeks": {
        1: {"label": "Week 1", "ladder": "4 x 400m", "note": "Own the pace before chasing more volume."},
        2: {"label": "Week 2", "ladder": "5 x 400m", "note": "One more rep, same effort."},
        3: {"label": "Week 3", "ladder": "3 x 800m", "note": "Longer reps, same 'comfortably hard' ceiling — don't chase Week 1's 400 pace."},
        4: {"label": "Week 4 — cutback", "ladder": "2 x 800m", "note": "Half volume, full quality. Legs should feel fresher after this week, not more worn."},
    },
    "next_block_note": "After 4 weeks, progress to 2x1200m + 2x400m if HR/calf response has been clean.",
}

RUN_LONG = {
    "name": "Long Run",
    "purpose": "Longest single run of the week — grows with the overall mileage build.",
    "rehab":   FIGHTER_REHAB_SHOULDER,
    "stretch": FIGHTER_STRETCH_SHOULDER,
    "weeks": {
        1: {"label": "Week 1", "run_line": "4.2 mi easy pace, Zone 2 (HR ~130s, ~14:00/mi pace)."},
        2: {"label": "Week 2", "run_line": "4.5 mi easy pace, Zone 2 (HR ~130s, ~14:00/mi pace)."},
        3: {"label": "Week 3", "run_line": "5.0 mi easy pace, Zone 2 (HR ~130s, ~14:00/mi pace)."},
        4: {"label": "Week 4 — cutback", "run_line": "3.5 mi easy pace, light effort. Zone 2, ~14:00/mi pace."},
    },
}


# ==========================================================================
#  WEEKLY SCHEDULE (final, per Rena — back to the original v3 draft's
#  schedule, long run confirmed on Sunday):
#    Mon Hinge · Tue Easy Run · Wed Squat/Hip Thrust · Thu Interval ·
#    Fri Easy Run · Sat Swing/Conditioning · Sun Long Run
#  4 run days / 3 strength days, no dedicated rest day — matches v3's own
#  file total exactly. Flagged to Rena as a real load change (the old
#  schedule had Sunday as a hard rest day); she confirmed it.
# ==========================================================================

FIGHTER_PROGRAM = {
    "name":     "Fighter — Circuit + Run",
    "subtitle": "Short dense circuits. Real running structure.",
    "weeks":    4,
    "description": (
        "Strength sessions are short, dense circuits built almost entirely "
        "from movements you're engaged by — swing, RDL, hip thrust, goblet "
        "squat — with a skill-based finisher instead of a bolted-on arm/ab "
        "block. Running gets a real structure: easy days, a dedicated "
        "interval day, and a long run. This 4-week wave (Learn → Build → "
        "Sharpen → Restore) repeats indefinitely — there's no separate "
        "12-week arc anymore."
    ),
    "strength_hinge":              STRENGTH_HINGE,
    "strength_squat_hipthrust":    STRENGTH_SQUAT_HIPTHRUST,
    "strength_swing_conditioning": STRENGTH_SWING_CONDITIONING,
    "run_easy":     RUN_EASY,
    "run_interval": RUN_INTERVAL,
    "run_long":     RUN_LONG,
    "benchmark":    BENCHMARK,
}

# Single repeating 4-week wave — all three "program" slots share identical
# content (see get_today_workout / _get_program_and_week: the 12-week
# machinery is left in place for Kyle, but for Fighter these three all being
# the same dict makes it functionally a 4-week repeat, not a 12-week arc).
PROGRAM_1 = FIGHTER_PROGRAM
PROGRAM_2 = FIGHTER_PROGRAM
PROGRAM_3 = FIGHTER_PROGRAM




# ── Kyle Rehab Track ─────────────────────────────────────────────────────────
KYLE_PROGRAM_1 = {
    "name":        "Program 1 — Reset & Reactivate",
    "subtitle":    "Exit KB Strong. Establish the baseline. Begin closing the gap.",
    "weeks":       4,
    "description": (
        "You've just run 10×5 / 10×4 / 10×5 bilateral pressing for weeks. "
        "Your left serratus and lower trap are underrecruited. "
        "Week 1 is about resetting the pattern — not about load. "
        "The double swing feels right because your body knows hip hinge. "
        "We start there and build everything else around it. "
        "No bilateral overhead pressing this entire program."
    ),

    # ── PRE-SESSION ACTIVATION (every strength session) ──────────────────────
    "pre_session": [
        "Serratus Wall Slide 2×10  (face wall, forearms on wall, slide up WITHOUT shrugging — "
        "if upper trap fires you're doing it wrong. This is your most important exercise.)",
        "Bear Plank Reach 2×10/side  (quadruped, protract LEFT scapula at end range — "
        "hold 2 s, feel the serratus fire under your armpit)",
        "Diaphragmatic Breath 10 slow breaths  (hand on belly, hand on chest — "
        "only belly hand moves. This decompresses your thoracic outlet.)",
    ],

    # ── STRENGTH A — Lower Body + Unilateral Press ────────────────────────────
    "strength_a": {
        "name":    "Strength A — Lower Body + Unilateral Press",
        "anchor":  "Two-Hand KB Swing + Half-Kneeling Single-Arm Press",
        "note":    "Track LEFT and RIGHT press weight independently every session.",
        "weeks": {

            1: {
                "label": "Week 1 — Establish baseline. What can left actually do?",
                "main":  "Two-Hand KB Swing 5×10 @ 24 kg  (your wheelhouse — crisp and powerful)",
                "full_body": [
                    "SUPERSET A1 — Half-Kneeling Single-Arm Press 4×5/side @ RIGHT: 24 kg / LEFT: 20 kg  "
                    "[PRESS — half-kneeling removes leg drive, isolates shoulder. "
                    "Log both weights. This is your gap baseline. The shoulder rests while the hinge works.]",
                    "SUPERSET A2 — Double KB Deadlift 4×5 @ 32 kg/bell  [HINGE — heavy, hip dominant, "
                    "no shoulder loading. This is where you're strong.]",
                    "Hollow Rock 3×15  [CORE — no spinal compression]",
                ],
                "focus": [
                    "Single-Leg RDL 3×8/side @ 24 kg  (unilateral hinge — expose any "
                    "left/right imbalance below the waist too)",
                    "Y-T-W Raise 3×10 each position @ light band or 4 kg  "
                    "(prone — lower trap reactivation. Looks easy. Burns.)",
                    "Face Pull with External Rotation 3×15  (band — rear delt + "
                    "rotator cuff health. Every session.)",
                ],
                "corrective": [
                    "KB Arm Bar LEFT side only 2×60 s @ 16 kg  "
                    "(sub-scap release — feel the tissue release, not the weight)",
                    "Serratus Wall Slide 2×10  (second set — end of session reinforcement)",
                ],
                "finisher": (
                    "Two-Hand KB Swing 50 reps @ 24 kg — for time\n"
                    "Note your time. This is your conditioning baseline."
                ),
            },

            2: {
                "label": "Week 2 — Add volume. Left side catching up?",
                "main":  "Two-Hand KB Swing 6×10 @ 24 kg  (add a set — 60 total)",
                "full_body": [
                    "SUPERSET A1 — Half-Kneeling Single-Arm Press 5×5/side @ RIGHT: 24 kg / LEFT: 20 kg  "
                    "[PRESS — add a set. Is left feeling stronger? Note it.]",
                    "SUPERSET A2 — Double KB Deadlift 5×5 @ 32 kg/bell  [HINGE — add a set. Shoulder rests here.]",
                    "Hollow Rock 3×20  [CORE — more reps]",
                ],
                "focus": [
                    "Single-Leg RDL 4×8/side @ 24 kg  (add a set)",
                    "Y-T-W Raise 3×12 each @ light band  (more reps)",
                    "Face Pull with External Rotation 3×20  (more reps)",
                ],
                "corrective": [
                    "KB Arm Bar LEFT 2×60 s @ 16 kg",
                    "KB Arm Bar with Thoracic Rotation 2×8/side @ 12 kg  "
                    "(from arm bar position, rotate thoracic toward ceiling — "
                    "this hits the scar tissue bundle directly)",
                ],
                "finisher": (
                    "Two-Hand KB Swing 75 reps @ 24 kg — for time\n"
                    "Compare to week 1. You should be faster."
                ),
            },

            3: {
                "label": "Week 3 — Push the press. Can left handle 24 kg for some sets?",
                "main":  "Two-Hand KB Swing 5×10 @ 32 kg  (↑ bell — RPE 8)",
                "full_body": [
                    "SUPERSET A1 — Half-Kneeling Single-Arm Press 4×5/side @ RIGHT: 24 kg / "
                    "LEFT: attempt 24 kg for sets 1-2, drop to 20 kg if form breaks  "
                    "[PRESS — this is the week we test the ceiling. Take full rest before each press set — "
                    "the hinge is your rest. No visual disturbance = proceed. Any disturbance = stop that set.]",
                    "SUPERSET A2 — Double KB Deadlift 4×4 @ 40 kg/bell  [HINGE — near max, crisp]",
                    "Hanging Leg Raise 3×10  [CORE — add load to core]",
                ],
                "focus": [
                    "Single-Leg RDL 3×6/side @ 32 kg  (↑ load — heavier)",
                    "Y-T-W Raise 3×10 @ 6 kg  (↑ load — still light but harder)",
                    "Face Pull with External Rotation 4×15  (add a set)",
                ],
                "corrective": [
                    "KB Arm Bar with Rotation LEFT 3×8 @ 12 kg  (add a set)",
                    "Scalene Stretch LEFT 3×60 s  "
                    "(lateral neck flexion right, depress LEFT shoulder simultaneously — "
                    "direct stretch of the tissue compressing your brachial plexus)",
                ],
                "finisher": (
                    "Two-Hand KB Swing 100 reps @ 24 kg — for time\n"
                    "This is a real benchmark. Sub 5 min is strong."
                ),
            },

            4: {
                "label": "Week 4 — Deload. Let the left side absorb.",
                "main":  "Two-Hand KB Swing 4×8 @ 20 kg  (light — hip snap focus)",
                "full_body": [
                    "SUPERSET A1 — Half-Kneeling Single-Arm Press 3×5/side @ RIGHT: 20 kg / LEFT: 16 kg  "
                    "[PRESS — deload. Feel the left side move without strain.]",
                    "SUPERSET A2 — Double KB Deadlift 3×5 @ 24 kg/bell  [HINGE — light]",
                    "Dead Bug 3×10/side  [CORE — breathing focus]",
                ],
                "focus": [
                    "Single-Leg RDL 2×8/side @ 20 kg  (light)",
                    "Y-T-W Raise 2×10 @ band  (easy — feel the lower trap)",
                    "Face Pull 2×15  (light)",
                ],
                "corrective": [
                    "KB Arm Bar LEFT 3×90 s @ 12 kg  (longer hold — tissue release)",
                    "Scalene Stretch LEFT 3×90 s  (longer hold)",
                    "Thoracic Rotation Drill 2×10/side  (seated, hands behind head)",
                ],
                "finisher": (
                    "Two-Hand KB Swing flow 10 min @ 20 kg\n"
                    "No timer pressure. Just move. Feel the hip hinge."
                ),
            },
        },
    },

    # ── STRENGTH B — Pull + Corrective Upper ──────────────────────────────────
    "strength_b": {
        "name":   "Strength B — Pull + Corrective Upper",
        "anchor": "Single-Arm KB Row (track left/right independently)",
        "note":   "Pull days are where your left side can actually load safely. "
                  "Pulling is scapular retraction — the opposite of what's compressed.",
        "weeks": {

            1: {
                "label": "Week 1 — Establish pull baseline. Left vs right.",
                "main":  "Single-Arm KB Row 4×8/side @ RIGHT: 32 kg / LEFT: 32 kg  "
                         "(pulling is safe — load it. Note if left fatigues faster.)",
                "full_body": [
                    "SUPERSET A1 — Z Press Single-Arm 4×5/side @ RIGHT: 24 kg / LEFT: 20 kg  "
                    "[PRESS — seated floor, no back support. "
                    "Even harder than half-kneeling for core demand. "
                    "LEFT shoulder controls the load completely — no compensation possible.]",
                    "SUPERSET A2 — KB Goblet Squat 4×8 @ 32 kg  [LOWER — no shoulder loading. The squat is the shoulder's rest.]",
                    "Ab Wheel Rollout 3×6  [CORE — from knees]",
                ],
                "focus": [
                    "Chest-Supported Row 3×12 @ 24 kg  (bilateral is fine for rows — "
                    "retraction not compression)",
                    "Band Pull-Apart 3×25  (rear delt — every pull day)",
                    "Dead Hang 3×30 s  (traction for your thoracic outlet — "
                    "passive hang decompresses the whole structure)",
                ],
                "corrective": [
                    "Sleeper Stretch LEFT 3×60 s  "
                    "(internal rotation release — swimmers need this. "
                    "Lie on left side, arm at 90°, gently rotate forearm toward floor)",
                    "90/90 Shoulder Rotation LEFT 2×10  "
                    "(controlled articular rotation — full range, no pain)",
                ],
                "finisher": (
                    "KB Snatch 5×5/side @ 24 kg  (rest 60 s between sets)\n"
                    "Hip power to overhead — but single arm so left side works independently.\n"
                    "Note if left overhead feels different from right."
                ),
            },

            2: {
                "label": "Week 2 — More pull volume. Left row keeping up?",
                "main":  "Single-Arm KB Row 5×8/side @ 32 kg  (add a set)",
                "full_body": [
                    "SUPERSET A1 — Z Press Single-Arm 5×5/side @ RIGHT: 24 kg / LEFT: 20 kg  "
                    "[PRESS — add a set]",
                    "SUPERSET A2 — KB Goblet Squat 5×8 @ 32 kg  [LOWER — add a set. Shoulder rests here.]",
                    "Ab Wheel Rollout 3×8  [CORE — more reps]",
                ],
                "focus": [
                    "Chest-Supported Row 4×12 @ 24 kg  (add a set)",
                    "Band Pull-Apart 3×30  (more reps)",
                    "Dead Hang 4×30 s  (add a set)",
                ],
                "corrective": [
                    "Sleeper Stretch LEFT 3×75 s  (longer)",
                    "90/90 Shoulder Rotation LEFT 3×10  (add a set)",
                    "Thoracic Extension over foam roller 2×60 s  "
                    "(mid-back — open the thoracic cage)",
                ],
                "finisher": (
                    "KB Snatch 6×5/side @ 24 kg\n"
                    "Add a round. Rest 60 s. Note if left overhead fatigue changes."
                ),
            },

            3: {
                "label": "Week 3 — Heavy rows. You're strong here.",
                "main":  "Single-Arm KB Row 4×6/side @ 40 kg  (↑ load — heavy)",
                "full_body": [
                    "SUPERSET A1 — Z Press Single-Arm 4×5/side @ RIGHT: 24 kg / LEFT: attempt 22-24 kg  "
                    "[PRESS — test left ceiling again on pull day too. Full rest before each press set.]",
                    "SUPERSET A2 — KB Goblet Squat 4×6 @ 40 kg  [LOWER — heavy]",
                    "Hanging Leg Raise 3×12  [CORE]",
                ],
                "focus": [
                    "Chest-Supported Row 4×10 @ 32 kg  (↑ load)",
                    "Band Pull-Apart 4×25  (add a set)",
                    "Dead Hang 4×40 s  (longer hang)",
                ],
                "corrective": [
                    "Sleeper Stretch LEFT 3×90 s",
                    "90/90 Shoulder Rotation LEFT 3×12",
                    "Scalene Stretch LEFT 2×60 s  (after the row work — tissue is warm)",
                ],
                "finisher": (
                    "KB Snatch 8×5/side @ 24 kg\n"
                    "8 rounds. 40 reps per arm. This is conditioning."
                ),
            },

            4: {
                "label": "Week 4 — Deload. Long hangs. Let it absorb.",
                "main":  "Single-Arm KB Row 3×8/side @ 24 kg  (light — feel the scapula move)",
                "full_body": [
                    "SUPERSET A1 — Z Press Single-Arm 2×5/side @ RIGHT: 20 kg / LEFT: 16 kg  [PRESS — easy]",
                    "SUPERSET A2 — KB Goblet Squat 3×8 @ 24 kg  [LOWER]",
                    "Dead Bug 3×10/side  [CORE]",
                ],
                "focus": [
                    "Chest-Supported Row 2×12 @ 20 kg  (light)",
                    "Band Pull-Apart 2×20",
                    "Dead Hang 3×45 s  (longest hang yet — decompress everything)",
                ],
                "corrective": [
                    "Sleeper Stretch LEFT 3×90 s",
                    "KB Arm Bar LEFT 2×90 s @ 12 kg",
                    "Full shoulder mobility flow 5 min  "
                    "(arm circles, cross-body, doorframe stretch — feel good)",
                ],
                "finisher": (
                    "KB Snatch flow 8 min @ 20 kg\n"
                    "No counting. Switch hands when you want. Moving meditation."
                ),
            },
        },
    },

    # ── STRENGTH C — Hardstyle Power ──────────────────────────────────────────
    "strength_c": {
        "name":   "Strength C — Hardstyle Power",
        "anchor": "Two-Hand KB Swing (your strongest movement — honor it)",
        "note":   "This is your conditioning day. Ultra-short race pace energy. "
                  "Complete work, complete rest. Swimming background shows here.",
        "weeks": {

            1: {
                "label": "Week 1 — Reestablish hardstyle baseline.",
                "main":  "Two-Hand KB Swing EMOM 20 min: 10 reps/min @ 32 kg",
                "full_body": [
                    "SUPERSET A1 — Single-Arm KB Clean + Press 3×5/side @ RIGHT: 24 kg / LEFT: 20 kg  "
                    "[PUSH — clean keeps the press honest. "
                    "Left cleans to rack, presses from there. No bilateral.]",
                    "SUPERSET A2 — Double KB Deadlift 3×5 @ 32 kg/bell  [HINGE — shoulder rests while you pull]",
                    "SUPERSET B1 — Push-Up 3×15  [PUSH — bodyweight, no shoulder asymmetry issue]",
                    "SUPERSET B2 — Hollow Rock 3×20  [CORE]",
                ],
                "focus": [
                    "KB High Pull 3×8/side @ 24 kg  (explosive — hip to shoulder height)",
                    "Single-Leg Hip Thrust 3×10/side @ 24 kg  (hip power maintenance)",
                ],
                "corrective": [
                    "Serratus wall slide 2×10  (mid-session — reinforcement)",
                ],
                "finisher": (
                    "100 Two-Hand KB Swings for time @ 32 kg\n"
                    "Your benchmark. Sub 4 min is strong at 32 kg."
                ),
            },

            2: {
                "label": "Week 2 — More swing volume. Engine growing.",
                "main":  "Two-Hand KB Swing EMOM 25 min: 10 reps/min @ 32 kg  (add 5 min)",
                "full_body": [
                    "SUPERSET A1 — Single-Arm KB Clean + Press 4×5/side @ RIGHT: 24 kg / LEFT: 20 kg  "
                    "[PUSH — add a set]",
                    "SUPERSET A2 — Double KB Deadlift 4×5 @ 32 kg/bell  [HINGE]",
                    "SUPERSET B1 — Push-Up 4×15  [PUSH — add a set]",
                    "SUPERSET B2 — Ab Wheel Rollout 3×8  [CORE]",
                ],
                "focus": [
                    "KB High Pull 4×8/side @ 24 kg  (add a set)",
                    "Single-Leg Hip Thrust 4×10/side @ 24 kg",
                ],
                "corrective": [
                    "Serratus wall slide 2×10",
                ],
                "finisher": (
                    "Swing Tabata: 20 s on / 10 s off × 8 rounds @ 32 kg\n"
                    "4 min. Maximum power. Note total swing count."
                ),
            },

            3: {
                "label": "Week 3 — Peak power. This is what you came for.",
                "main":  "Two-Hand KB Swing EMOM 20 min: 12 reps/min @ 32 kg  (↑ reps/min)",
                "full_body": [
                    "SUPERSET A1 — Single-Arm KB Clean + Press 4×5/side @ RIGHT: 28-32 kg / LEFT: 24 kg  "
                    "[PUSH — left gets to 24 kg this week. This is the milestone.]",
                    "SUPERSET A2 — Double KB Deadlift 4×4 @ 40 kg/bell  [HINGE — heavy]",
                    "SUPERSET B1 — Push-Up 4×20  [PUSH — endurance]",
                    "SUPERSET B2 — Hanging Leg Raise 4×10  [CORE]",
                ],
                "focus": [
                    "KB Snatch 5×5/side @ 24 kg  (power endurance)",
                    "Single-Leg Hip Thrust 4×8/side @ 32 kg  (heavy)",
                ],
                "corrective": [
                    "Serratus wall slide 3×10  (more sets — peak week needs more activation)",
                ],
                "finisher": (
                    "200 Two-Hand KB Swings @ 24 kg — every time you put it down: "
                    "5 push-ups penalty\n"
                    "Note time and breaks. This is your peak week benchmark."
                ),
            },

            4: {
                "label": "Week 4 — Deload. Light swings. Feel the power pattern.",
                "main":  "Two-Hand KB Swing 5×10 @ 20 kg  (light — perfect hip snap)",
                "full_body": [
                    "SUPERSET A1 — Single-Arm KB Clean + Press 2×5/side @ RIGHT: 20 kg / LEFT: 16 kg  "
                    "[PUSH — easy]",
                    "SUPERSET A2 — Double KB Deadlift 3×5 @ 24 kg/bell  [HINGE — light]",
                    "SUPERSET B1 — Push-Up 2×10  [PUSH]",
                    "SUPERSET B2 — Dead Bug 3×10/side  [CORE]",
                ],
                "focus": [
                    "KB High Pull 2×8/side @ 20 kg  (light)",
                    "Hip Flexor Stretch 2×90 s/side",
                ],
                "corrective": [
                    "Serratus wall slide 2×10",
                    "Diaphragmatic breathing 5 min  (deload week — extra breath work)",
                ],
                "finisher": (
                    "KB flow 10 min @ 20 kg — swings, cleans, halos\n"
                    "No structure. Just move. This is your reward."
                ),
            },
        },
    },

    # ── STRENGTH D — Saturday Optional ───────────────────────────────────────
    "strength_d": {
        "name":  "Strength D — Saturday Optional",
        "anchor": "Heavy Double KB Deadlift + Skill + Mobility Play",
        "note":   "Optional. No arms. No overhead. Just heavy lower, one skill, mobility, play.",
        "weeks": {

            1: {
                "label": "Week 1 — Heavy pull + thoracic skill + play",
                "main":  "Double KB Deadlift 5×3 @ 40 kg/bell  (heavy and crisp — 3 reps means perfect every time)",
                "skill": "Dowel Rod Overhead Squat 3×8  (technique — dowel only, no load. "
                         "This will expose thoracic mobility immediately.)",
                "prevention": [
                    "Band Pull-Apart 3×25",
                    "Serratus Wall Slide 3×10  (third session this week — reinforcing)",
                    "Y-T-W Raise 2×10 each",
                ],
                "mobility_block": [
                    "Thoracic rotation + rib grab 2×10/side",
                    "Thread the needle 2×10/side",
                    "Scalene stretch LEFT 3×90 s",
                    "90/90 hip switch 2×10",
                    "Pigeon pose 2×2 min/side",
                ],
                "finisher": "BUTT BURNER 5000 (Dan John) @ 12 kg  — Ladder 1→10: 1 KB hip hinge (goat-bag swing/RDL) + 1 goblet squat, 2+2 … up to 10+10. Pure lower body, zero shoulder load — perfect for this track. Light and flowing, it's cardio. Then juggle/play if you've got time.",
            },

            2: {
                "label": "Week 2 — Heavier pull + Z press skill",
                "main":  "Double KB Deadlift 5×3 @ 40 kg/bell",
                "skill": "Z Press Single-Arm 3×5/side @ 20 kg LEFT / 24 kg RIGHT  "
                         "(Saturday skill work — lighter than strength days, focus on positioning)",
                "prevention": [
                    "Band Pull-Apart 3×25",
                    "Serratus Wall Slide 3×10",
                    "Dead Hang 3×45 s",
                ],
                "mobility_block": [
                    "Yoga sun salutation A × 4  (thoracic opener)",
                    "Warrior I + II flow 2×/side",
                    "Lizard pose 2×90 s/side",
                    "Scalene stretch LEFT 3×90 s",
                    "Legs-up-the-wall 5 min  (parasympathetic reset + thoracic outlet decompression)",
                ],
                "finisher": "BUTT BURNER 5000 @ 12 kg  — Same 1→10 ladder, hip hinge + goblet squat each rung. Push the pace a touch this week — note your time. Juggle/play after if you want.",
            },

            3: {
                "label": "Week 3 — Near-max pull + bottoms-up skill",
                "main":  "Double KB Deadlift 4×3 @ 40 kg/bell  (near-max — RPE 9)",
                "skill": "Bottoms-Up Press Single-Arm 3×5/side @ 12 kg  "
                         "(LEFT side especially — forces perfect shoulder recruitment. "
                         "Serratus must fire to stabilize. This is corrective masquerading as skill.)",
                "prevention": [
                    "Serratus Wall Slide 3×10",
                    "Y-T-W 3×10 each",
                    "Scalene stretch LEFT 3×90 s",
                ],
                "mobility_block": [
                    "Yin dragon pose 2×2 min/side",
                    "Yin sleeping swan 2×2 min/side",
                    "Supine spinal twist 2×2 min/side",
                    "Thoracic extension over foam roller 2×60 s",
                    "Savasana 5 min  (yes, actually)",
                ],
                "finisher": "BUTT BURNER 5000 @ 16 kg  — 1→10 ladder, hip hinge + goblet squat each rung. Up a bell but keep it flowing — if you have to grind a rep you're too heavy. Play after.",
            },

            4: {
                "label": "Week 4 — Light deload + full mobility",
                "main":  "Double KB Deadlift 3×3 @ 24 kg/bell  (light — deload)",
                "skill": "Dowel Overhead Squat 3×8  (back to basics — notice if it feels different than week 1)",
                "prevention": [
                    "Serratus Wall Slide 2×10",
                    "Band Pull-Apart 2×20",
                ],
                "mobility_block": [
                    "Full restoration flow 20 min — everything you've learned",
                    "Extra time on: scalene stretch LEFT, sleeper stretch LEFT, dead hang",
                    "Savasana 5 min",
                ],
                "finisher": "KB flow / juggling 10 min @ light bells  (playful, no pressure)",
            },
        },
    },

    # ── MOBILITY DAYS — Kyle Program 1 ────────────────────────────────────────
    "mobility": {
        "name":  "Mobility — Kyle Program 1",
        "focus": "Thoracic outlet decompression, serratus reactivation, "
                 "brachial plexus nerve gliding, diaphragmatic breathing, "
                 "sub-scapularis release. This is your most important training.",
        "note":  "Run first if running today. Mobility immediately after. "
                 "The tissue is warm and receptive post-run.",
        "sessions": {

            "A": {  # Tuesday
                "label": "Mobility A — Thoracic + Serratus + Nerve",
                "opening": [
                    "Diaphragmatic Breathing 5 min  "
                    "(lying down, knees bent. Hand on belly, hand on chest. "
                    "ONLY belly rises. 4 s inhale through nose, 6 s exhale through pursed lips. "
                    "This is therapeutic — you are mechanically decompressing your thoracic outlet "
                    "with every exhale. Do not rush this. Do not skip this.)",
                ],
                "main": "Serratus Wall Slide 3×12  (slow — 3 s up, 3 s down. "
                        "Feel LEFT serratus fire under your armpit. "
                        "If you feel upper trap: reset and go slower.)",
                "sequence": [
                    "Bear Plank Reach 3×10/side  (protract LEFT scapula at end range — hold 2 s)",
                    "KB Arm Bar with Thoracic Rotation LEFT 3×8 @ 12 kg  "
                    "(from arm bar, rotate thoracic toward ceiling — "
                    "this mobilizes the scar tissue bundle directly)",
                    "Scalene Stretch LEFT 3×90 s  "
                    "(right lateral neck flexion + LEFT shoulder depression simultaneously. "
                    "You should feel a pull from left ear to left collarbone. "
                    "This is the tissue compressing your brachial plexus.)",
                    "Sleeper Stretch LEFT 3×90 s  "
                    "(swimmer's tightest tissue. Lie on left side, arm at 90°, "
                    "gently press forearm toward floor. Feel internal rotation releasing.)",
                    "Thoracic Rotation + Rib Grab 3×10/side  "
                    "(seated, hands behind head — isolate thoracic, not lumbar)",
                    "Thread the Needle 3×10/side  (thoracic rotation in quadruped)",
                ],
                "nerve_gliding": [
                    "Brachial Plexus Nerve Glide LEFT 3×10  "
                    "(arm out to side, tilt head right, flex wrist back — "
                    "you should feel a stretch/tingle down the arm. "
                    "This is nerve mobilization — gentle, not aggressive. "
                    "If tingling becomes sharp: stop.)",
                    "Median Nerve Glide LEFT 3×10  "
                    "(arm out, palm up, extend wrist, tilt head right — "
                    "different nerve path, same principle)",
                ],
                "finisher": (
                    "Legs-Up-the-Wall 8 min  "
                    "(the single best thoracic outlet decompression position. "
                    "Gravity pulls the shoulder girdle away from the thoracic outlet. "
                    "Arms out to sides, palms up. Breathe diaphragmatically. "
                    "This is medicine.)"
                ),
            },

            "B": {  # Thursday
                "label": "Mobility B — Sub-Scap Release + Breathing + Reset",
                "opening": [
                    "Diaphragmatic Breathing 5 min  "
                    "(same protocol as Tuesday. This is non-negotiable. "
                    "You've been running 5 days this week — your breathing pattern "
                    "is probably chest-dominant by Thursday. Reset it.)",
                ],
                "main": "90/90 Shoulder Rotation LEFT 3×10  "
                        "(controlled articular rotation — full range, no pain. "
                        "Take the joint through its complete available range.)",
                "sequence": [
                    "Serratus Wall Slide 3×10  "
                    "(third time this week — the neural pattern is forming)",
                    "Sub-Scap Self-Release LEFT 3×60 s  "
                    "(lacrosse ball or firm ball under LEFT armpit — "
                    "same area Rena works with massage. Roll slowly. "
                    "When you find the knot: stay on it and breathe. "
                    "You'll likely feel tingling down the arm — that's the brachial plexus. "
                    "Stay until it reduces.)",
                    "Doorframe Pec Stretch 3×60 s  "
                    "(pec minor tightness compresses the thoracic outlet from the front. "
                    "Arm at 90°, lean into doorframe — feel the pec minor, not the pec major)",
                    "Thoracic Extension over Foam Roller 3×60 s  "
                    "(different vertebral levels — don't just sit at one spot. "
                    "Mid thoracic is most important for you.)",
                    "Cat-Cow 2×10  (5 s per rep — spinal wave)",
                    "Child's Pose with Lateral Reach LEFT 2×90 s  "
                    "(reach left arm overhead — lateral thoracic stretch)",
                ],
                "breathing_protocol": [
                    "4-7-8 Breathing 4 rounds  "
                    "(inhale 4 s, hold 7 s, exhale 8 s — "
                    "activates parasympathetic nervous system. "
                    "Reduces the chronic sympathetic tone that keeps your scalenes tight.)",
                    "Box Breathing 5 min: 5-5-5-5  "
                    "(your system needs this after 5 running days. "
                    "This is HRV training. This is recovery.)",
                ],
                "finisher": (
                    "Legs-Up-the-Wall 8 min  (same as Tuesday — double dose this week)\n"
                    "Arms overhead in Y position — maximum thoracic outlet decompression.\n"
                    "Feel your breathing slow. Feel your trap release.\n"
                    "This is the most therapeutic thing you can do for your condition "
                    "outside of what Rena does with her hands."
                ),
            },
        },
    },
}


# ============================================================================
#  KYLE PROGRAM 2 — DEVELOPMENT  (Weeks 5–8)
#  The gap is closing. Add complexity. Trust the left side more.
# ============================================================================

KYLE_PROGRAM_2 = {
    "name":    "Program 2 — Development",
    "subtitle": "The gap is closing. Add complexity. Trust the left side.",
    "weeks":   4,
    "description": (
        "By week 5 your left serratus is waking up. "
        "The half-kneeling press transfers to Z press. "
        "The Z press transfers to standing single-arm press. "
        "We add complexity without adding bilateral overhead. "
        "The double swing stays heavy. The left side is catching up."
    ),

    "strength_a": {
        "name":   "Strength A — Lower + Unilateral Press Development",
        "anchor": "Double KB Swing + Z Press Single-Arm",
        "weeks": {
            1: {
                "label": "Week 5 — Z press replaces half-kneeling. Harder.",
                "main":  "Double KB Swing 6×8 @ 32 kg/bell  (double bell — bilateral hip power)",
                "full_body": [
                    "SUPERSET A1 — Z Press Single-Arm 4×5/side @ RIGHT: 24 kg / LEFT: 22-24 kg  "
                    "[PRESS — seated floor, legs straight. Harder than half-kneeling. "
                    "Left should be close to right by now.]",
                    "SUPERSET A2 — Double KB Deadlift 5×5 @ 40 kg/bell  [HINGE — heavy. The pull is the shoulder's rest.]",
                    "Ab Wheel Rollout 3×8  [CORE]",
                ],
                "focus": [
                    "Bulgarian Split Squat 3×8/leg @ 32 kg  (unilateral — expose any imbalance)",
                    "Y-T-W Raise 3×12 @ 6 kg  (progressive loading)",
                    "Face Pull with External Rotation 3×20",
                ],
                "corrective": [
                    "KB Arm Bar with Rotation LEFT 3×8 @ 16 kg  (↑ load)",
                    "Scalene Stretch LEFT 3×90 s",
                ],
                "finisher": (
                    "Double KB Swing 50 reps @ 32 kg/bell — for time\n"
                    "Double bells change everything. Note time."
                ),
            },
            2: {
                "label": "Week 6 — More Z press volume. Left closing the gap.",
                "main":  "Double KB Swing 8×8 @ 32 kg/bell  (add sets)",
                "full_body": [
                    "SUPERSET A1 — Z Press Single-Arm 5×5/side @ RIGHT: 24 kg / LEFT: 24 kg  "
                    "[PRESS — left matches right this week. This is the milestone.]",
                    "SUPERSET A2 — Double KB Deadlift 5×4 @ 40 kg/bell  [HINGE]",
                    "Ab Wheel Rollout 3×10  [CORE]",
                ],
                "focus": [
                    "Bulgarian Split Squat 4×8/leg @ 32 kg",
                    "Y-T-W 3×12 @ 8 kg  (↑ load)",
                    "Face Pull 4×20",
                ],
                "corrective": [
                    "KB Arm Bar with Rotation LEFT 3×10 @ 16 kg",
                    "Scalene Stretch LEFT 3×90 s",
                ],
                "finisher": (
                    "Double KB Swing Tabata: 20 s on / 10 s off × 8 @ 28 kg/bell\n"
                    "Lighter for tabata — speed and power, not grind."
                ),
            },
            3: {
                "label": "Week 7 — Heavy everything. Left side now pulling its weight.",
                "main":  "Double KB Swing 10×5 EMOM @ 32 kg/bell  (5 perfect reps every minute)",
                "full_body": [
                    "SUPERSET A1 — Z Press Single-Arm 4×4/side @ RIGHT: 28 kg / LEFT: 24-28 kg  "
                    "[PRESS — test 28 kg left. Full rest before each press set. If form holds for 3+ reps: log it.]",
                    "SUPERSET A2 — Double KB Deadlift 4×3 @ 40 kg/bell  [HINGE — near max]",
                    "Hanging Leg Raise 4×12  [CORE]",
                ],
                "focus": [
                    "Single-Leg RDL 3×6/side @ 32 kg  (heavy unilateral)",
                    "Y-T-W 4×10 @ 8 kg",
                    "Face Pull 4×20",
                ],
                "corrective": [
                    "Bottoms-Up Press LEFT 3×5 @ 12 kg  "
                    "(forced serratus recruitment — can't cheat this)",
                    "Scalene Stretch LEFT 3×90 s",
                ],
                "finisher": (
                    "200 KB Swings — mix of double and single @ 24-32 kg\n"
                    "Your choice of split. Note total time."
                ),
            },
            4: {
                "label": "Week 8 — Deload. Reflect on the gap.",
                "main":  "Double KB Swing 4×8 @ 24 kg/bell  (light)",
                "full_body": [
                    "SUPERSET A1 — Z Press Single-Arm 3×5/side @ RIGHT: 20 kg / LEFT: 20 kg  [PRESS — equal and easy]",
                    "SUPERSET A2 — Double KB Deadlift 3×5 @ 32 kg/bell  [HINGE — moderate]",
                    "Dead Bug 3×10/side  [CORE]",
                ],
                "focus": [
                    "Single-Leg RDL 2×8/side @ 24 kg",
                    "Y-T-W 2×10 @ band",
                    "Face Pull 2×15",
                ],
                "corrective": [
                    "KB Arm Bar LEFT 3×90 s @ 12 kg",
                    "Full shoulder mobility flow 5 min",
                ],
                "finisher": "KB flow 10 min @ 20 kg  (deload — just move)",
            },
        },
    },

    "strength_b": {
        "name":   "Strength B — Pull + Advanced Corrective",
        "anchor": "Single-Arm KB Row + Renegade Row",
        "weeks": {
            1: {
                "label": "Week 5 — Renegade rows added. Anti-rotation challenge.",
                "main":  "Single-Arm KB Row 5×8/side @ 32-40 kg  (heavy)",
                "full_body": [
                    "SUPERSET A1 — Single-Arm KB Clean + Z Press 4×4/side @ RIGHT: 24 kg / LEFT: 24 kg  "
                    "[PRESS — clean feeds the press. One fluid movement.]",
                    "SUPERSET A2 — KB Goblet Squat 4×8 @ 40 kg  [LOWER — heavy. Shoulder rests while you squat.]",
                    "SUPERSET B1 — Renegade Row 3×6/side @ 24 kg  [PULL — anti-rotation. "
                    "Left shoulder stabilizes differently here. Note any asymmetry.]",
                    "SUPERSET B2 — Ab Wheel 3×10  [CORE]",
                ],
                "focus": [
                    "Overhead Carry Single-Arm LEFT 4×20 m @ 20 kg  "
                    "(loaded protraction — serratus under load. Start left side.)",
                    "Dead Hang 4×45 s",
                    "Band Pull-Apart 3×25",
                ],
                "corrective": [
                    "Sleeper Stretch LEFT 3×90 s",
                    "Sub-Scap Self-Release LEFT 2×60 s",
                ],
                "finisher": (
                    "KB Snatch complex 5×5/side @ 24 kg:\n"
                    "5 snatches + 5 high pulls/side — rest 60 s"
                ),
            },
            2: {
                "label": "Week 6 — More overhead carry. Left shoulder rebuilding.",
                "main":  "Single-Arm KB Row 5×6/side @ 40 kg  (↑ load)",
                "full_body": [
                    "SUPERSET A1 — Single-Arm KB Clean + Z Press 5×4/side @ RIGHT: 24 kg / LEFT: 24 kg  [PRESS]",
                    "SUPERSET A2 — KB Goblet Squat 5×8 @ 40 kg  [LOWER — shoulder rests here]",
                    "SUPERSET B1 — Renegade Row 4×6/side @ 24 kg  [PULL]",
                    "SUPERSET B2 — Ab Wheel 3×12  [CORE]",
                ],
                "focus": [
                    "Overhead Carry LEFT then RIGHT 4×20 m @ 20 kg  (both sides now)",
                    "Dead Hang 4×45 s",
                    "Band Pull-Apart 4×25",
                ],
                "corrective": [
                    "Sleeper Stretch LEFT 3×90 s",
                    "90/90 Shoulder Rotation LEFT 3×12",
                ],
                "finisher": "KB Snatch EMOM 10 min: 6/side @ 24 kg",
            },
            3: {
                "label": "Week 7 — Heavy week. Overhead carry goes heavier.",
                "main":  "Single-Arm KB Row 4×5/side @ 40 kg  (heavy — RPE 8-9)",
                "full_body": [
                    "SUPERSET A1 — Single-Arm KB Clean + Z Press 4×4/side @ RIGHT: 28 kg / LEFT: 24-28 kg  [PRESS]",
                    "SUPERSET A2 — KB Goblet Squat 4×6 @ 40 kg  [LOWER — shoulder rests here]",
                    "SUPERSET B1 — Renegade Row 4×5/side @ 32 kg  [PULL — heavy renegade]",
                    "SUPERSET B2 — Hanging Leg Raise 4×12  [CORE]",
                ],
                "focus": [
                    "Overhead Carry LEFT 5×20 m @ 24 kg  (↑ load — serratus under serious load)",
                    "Dead Hang 4×60 s  (longest hang yet)",
                    "Band Pull-Apart 4×30",
                ],
                "corrective": [
                    "Bottoms-Up Press LEFT 3×5 @ 16 kg  (↑ load from P1)",
                    "Scalene Stretch LEFT 3×90 s",
                ],
                "finisher": (
                    "Carry Medley × 4 rounds:\n"
                    "  Overhead LEFT 20 m → Rack 20 m → Farmer 20 m @ 24 kg\n"
                    "  Rest 90 s between rounds"
                ),
            },
            4: {
                "label": "Week 8 — Deload. Long hangs. Everything light.",
                "main":  "Single-Arm KB Row 3×8/side @ 24 kg  (light)",
                "full_body": [
                    "SUPERSET A1 — Z Press Single-Arm 2×5/side @ 16 kg  [PRESS — easy]",
                    "SUPERSET A2 — KB Goblet Squat 2×10 @ 24 kg  [LOWER]",
                    "SUPERSET B1 — Renegade Row 2×5/side @ 20 kg  [PULL]",
                    "SUPERSET B2 — Dead Bug 3×10/side  [CORE]",
                ],
                "focus": [
                    "Overhead Carry 2×20 m/side @ 16 kg  (light)",
                    "Dead Hang 3×60 s",
                    "Band Pull-Apart 2×20",
                ],
                "corrective": [
                    "Full corrective flow 10 min — everything that's helped most",
                ],
                "finisher": "KB flow 10 min @ 16-20 kg",
            },
        },
    },

    "strength_c": {
        "name":   "Strength C — Hardstyle Power Development",
        "anchor": "Double KB Swing + KB Snatch Complex",
        "weeks": {
            1: {
                "label": "Week 5 — Double KB power. Snatch complexity added.",
                "main":  "Double KB Swing EMOM 20 min: 8 reps/min @ 32 kg/bell",
                "full_body": [
                    "SUPERSET A1 — Single-Arm KB Clean + Press 4×5/side @ RIGHT: 28 kg / LEFT: 24 kg  [PUSH]",
                    "SUPERSET A2 — KB Goblet Squat 3×5 @ 40 kg  "
                    "[LOWER — Two-Hand KB Goblet Squat — cup the bell, elbows inside knees at bottom, drive knees out, heels rooted. Go heavy. Perfect every time.]",
                    "SUPERSET B1 — Push-Up 4×20  [PUSH]",
                    "SUPERSET B2 — Hollow Rock 4×20  [CORE]",
                ],
                "focus": [
                    "KB Snatch 5×5/side @ 24 kg  (single arm overhead is fine — "
                    "it's the bilateral compression that's the issue, not overhead per se)",
                    "Single-Leg Hip Thrust 3×10/side @ 32 kg",
                ],
                "corrective": [
                    "Serratus Wall Slide 2×10",
                ],
                "finisher": (
                    "Ultra-short race pace conditioning — your swimming background:\n"
                    "10 × (10 Double KB Swings @ 32 kg + 30 s complete rest)\n"
                    "Maximum power every set. Complete recovery between. "
                    "This is how you trained. Honor it."
                ),
            },
            2: {
                "label": "Week 6 — More double KB volume. Power endurance.",
                "main":  "Double KB Swing EMOM 25 min: 8 reps/min @ 32 kg/bell",
                "full_body": [
                    "SUPERSET A1 — Single-Arm KB Clean + Press 5×5/side @ RIGHT: 28 kg / LEFT: 24 kg  [PUSH]",
                    "SUPERSET A2 — KB Goblet Squat 4×5 @ 40 kg  [LOWER — ↑ load]",
                    "SUPERSET B1 — Push-Up 4×20  [PUSH]",
                    "SUPERSET B2 — Ab Wheel 3×10  [CORE]",
                ],
                "focus": [
                    "KB Snatch 6×5/side @ 24 kg",
                    "Single-Leg Hip Thrust 4×8/side @ 32 kg",
                ],
                "corrective": ["Serratus Wall Slide 2×10"],
                "finisher": (
                    "10 × (10 Double KB Swings @ 32 kg + 30 s rest)\n"
                    "Same protocol. Are you faster or more powerful than week 5?"
                ),
            },
            3: {
                "label": "Week 7 — Peak power. Everything heavy.",
                "main":  "Double KB Swing 12×5 EMOM @ 40 kg/bell  (heaviest double swing)",
                "full_body": [
                    "SUPERSET A1 — Single-Arm KB Clean + Press 4×4/side @ RIGHT: 32 kg / LEFT: 28 kg  [PUSH — heavy]",
                    "SUPERSET A2 — KB Goblet Squat 4×4 @ 40 kg  [LOWER — heavy]",
                    "SUPERSET B1 — Push-Up 4×20  [PUSH]",
                    "SUPERSET B2 — Hanging Leg Raise 4×12  [CORE]",
                ],
                "focus": [
                    "KB Snatch 5×5/side @ 28 kg  (heavy snatch)",
                    "Single-Leg Hip Thrust 4×6/side @ 40 kg  (near max)",
                ],
                "corrective": ["Serratus Wall Slide 3×10"],
                "finisher": (
                    "The swim set:\n"
                    "10 × (5 Double KB Swings @ 40 kg + 30 s rest)\n"
                    "Maximum power. Sub-maximal reps. Complete rest. "
                    "This is ultra-short race pace. This is yours."
                ),
            },
            4: {
                "label": "Week 8 — Deload. Feel how far you've come.",
                "main":  "Two-Hand KB Swing 5×10 @ 24 kg  (light — just feel it)",
                "full_body": [
                    "SUPERSET A1 — Single-Arm KB Clean + Press 2×5/side @ 20 kg  [PUSH — easy]",
                    "SUPERSET A2 — KB Goblet Squat 2×10 @ 24 kg  [LOWER]",
                    "SUPERSET B1 — Push-Up 2×10  [PUSH]",
                    "SUPERSET B2 — Dead Bug 3×10/side  [CORE]",
                ],
                "focus": [
                    "Hip Flexor Stretch 2×90 s/side",
                    "KB Arm Bar LEFT 2×90 s",
                ],
                "corrective": ["Diaphragmatic breathing 5 min"],
                "finisher": "KB flow 10 min @ 20 kg",
            },
        },
    },

    "strength_d": {
        "name":  "Strength D — Saturday Optional (Program 2)",
        "weeks": {
            1: {
                "label": "Week 5 — Heavy deadlift + Z press skill",
                "main":  "Double KB Deadlift 5×3 @ 40 kg/bell",
                "skill": "Z Press Single-Arm 3×5/side @ 20 kg LEFT / 24 kg RIGHT",
                "prevention": [
                    "Copenhagen Plank 3×20 s/side",
                    "Single-Leg Balance 3×30 s/side  (eyes closed if easy)",
                    "Serratus Wall Slide 3×10",
                ],
                "mobility_block": [
                    "Yoga warrior flow × 3/side",
                    "Half pigeon 2×2 min/side",
                    "Scalene stretch LEFT 3×90 s",
                    "Legs-up-the-wall 8 min",
                ],
                "finisher": "BUTT BURNER 5000 (Dan John) @ 12 kg  — Ladder 1→10: 1 KB hip hinge (goat-bag swing/RDL) + 1 goblet squat, 2+2 … up to 10+10. Pure lower body, zero shoulder load. Light and flowing — cardio. Juggle/play after if you've got time.",
            },
            2: {
                "label": "Week 6 — Heavy deadlift + overhead carry skill",
                "main":  "Double KB Deadlift 5×3 @ 40 kg/bell",
                "skill": "Single-Arm Overhead Carry LEFT 4×30 m @ 20 kg  "
                         "(skill work — left shoulder stability under load)",
                "prevention": [
                    "Copenhagen Plank 3×25 s/side",
                    "Y-Balance Reach 3×5/side",
                    "Serratus Wall Slide 3×10",
                ],
                "mobility_block": [
                    "Sun salutation B × 4",
                    "Warrior III 3×30 s/side",
                    "Scalene stretch LEFT 3×90 s",
                    "Legs-up-the-wall 8 min — arms in Y",
                ],
                "finisher": "BUTT BURNER 5000 @ 12 kg  — Same 1→10 ladder, hip hinge + goblet squat each rung. Push the pace a touch — note your time. Play after if you want.",
            },
            3: {
                "label": "Week 7 — Near-max deadlift + bottoms-up skill",
                "main":  "Double KB Deadlift 4×2 @ 40 kg/bell  (heaviest — 2 perfect reps)",
                "skill": "Bottoms-Up Press LEFT 3×5 @ 16 kg  (serratus activation under load)",
                "prevention": [
                    "Copenhagen Plank 3×30 s/side",
                    "Serratus Wall Slide 3×10",
                    "Scalene stretch LEFT 3×90 s",
                ],
                "mobility_block": [
                    "Yin butterfly 3 min",
                    "Yin dragon pose 2×2 min/side",
                    "Yin sleeping swan 2×2 min/side",
                    "Savasana 5 min",
                ],
                "finisher": "BUTT BURNER 5000 @ 16 kg  — 1→10 ladder, hip hinge + goblet squat each rung. Up a bell but keep it flowing — if you grind a rep you're too heavy.",
            },
            4: {
                "label": "Week 8 — Light + full restoration",
                "main":  "Double KB Deadlift 3×3 @ 32 kg/bell  (light deload)",
                "skill": "Dowel Overhead Squat 3×8  (return to basics — notice improvement)",
                "prevention": ["Serratus Wall Slide 2×10", "Band Pull-Apart 2×20"],
                "mobility_block": [
                    "Full restoration — anything your body needs",
                    "Extra: scalene LEFT, sleeper stretch LEFT, legs-up-the-wall",
                ],
                "finisher": "KB flow 10 min @ light bells",
            },
        },
    },

    "mobility": {
        "name":  "Mobility — Kyle Program 2",
        "focus": "Deeper tissue work, advanced breathing, yoga integration",
        "sessions": {
            "A": {
                "label": "Mobility A — Advanced Thoracic + Nerve Gliding",
                "opening": ["Diaphragmatic Breathing 5 min  (same protocol — never skip)"],
                "main": "Serratus Wall Slide 3×12 + Bear Plank Reach 3×10/side",
                "sequence": [
                    "KB Arm Bar with Rotation LEFT 3×10 @ 16 kg  (↑ load and reps)",
                    "Scalene Stretch LEFT 4×90 s  (add a set)",
                    "Sleeper Stretch LEFT 4×90 s",
                    "Pec Minor Release LEFT — lacrosse ball under coracoid process 2×60 s  "
                    "(find the knot just inside the shoulder — stay and breathe)",
                    "Thoracic Rotation 3×12/side",
                    "Thread the Needle 3×12/side",
                ],
                "nerve_gliding": [
                    "Brachial Plexus Nerve Glide LEFT 3×12  (↑ reps)",
                    "Ulnar Nerve Glide LEFT 3×10  "
                    "(arm out, elbow bent, tilt head — different nerve path. "
                    "Given the ulnar surgery this is important.)",
                    "Radial Nerve Glide LEFT 3×10  "
                    "(arm down, wrist extended behind — third nerve path)",
                ],
                "finisher": "Legs-Up-the-Wall 10 min  (↑ duration — arms in Y, breathe)",
            },
            "B": {
                "label": "Mobility B — Sub-Scap Deep Release + Advanced Breathing",
                "opening": ["Diaphragmatic Breathing 5 min"],
                "main": "Sub-Scap Self-Release LEFT 3×90 s  "
                        "(longer holds — you know where the tissue is now)",
                "sequence": [
                    "90/90 Shoulder Rotation LEFT 3×12",
                    "Doorframe Pec Stretch 3×90 s  (longer)",
                    "Thoracic Extension over roller 3×60 s  (different levels)",
                    "Yoga cat-cow 2×10  (5 s/rep)",
                    "Downward dog hold 3×30 s  (shoulder stability + hamstring)",
                    "Child's pose lateral reach LEFT 3×90 s",
                ],
                "breathing_protocol": [
                    "Wim Hof round 1: 30 breaths → exhale hold → inhale hold  "
                    "(sympathetic activation then reset — do not do more than 1 round "
                    "given blood pressure. One round is therapeutic.)",
                    "4-7-8 Breathing 4 rounds  (parasympathetic follow-up)",
                    "Box Breathing 5 min: 5-5-5-5",
                ],
                "finisher": (
                    "Legs-Up-the-Wall 10 min — arms in Y\n"
                    "If Rena is available: have her work on the serratus/sub-scap bundle now.\n"
                    "Then 5 min arm bar immediately after while tissue is released.\n"
                    "This combination is more therapeutic than either alone."
                ),
            },
        },
    },
}


# ============================================================================
#  KYLE PROGRAM 3 — PERFORMANCE  (Weeks 9–12)
#  The gap is closed. Bilateral symmetry restored. Build from here.
# ============================================================================

KYLE_PROGRAM_3 = {
    "name":    "Program 3 — Performance",
    "subtitle": "The gap is closed. Bilateral symmetry restored. Build from here.",
    "weeks":   4,
    "description": (
        "By week 9 your left side should be pressing at or near 24 kg. "
        "The serratus is reactivated. The scar tissue has been mobilized. "
        "Now we build. The corrective work doesn't stop — it becomes maintenance. "
        "The strength work gets heavier. The conditioning gets harder. "
        "You are rebuilding what D3 swimming built — just smarter this time."
    ),

    "strength_a": {
        "name":   "Strength A — Lower + Full Pressing Strength",
        "anchor": "Double KB Swing + Standing Single-Arm Press",
        "weeks": {
            1: {
                "label": "Week 9 — Standing press. No more kneeling or floor.",
                "main":  "Double KB Swing 8×8 @ 32 kg/bell",
                "full_body": [
                    "SUPERSET A1 — Standing Single-Arm KB Press 4×5/side @ RIGHT: 28 kg / LEFT: 24 kg  "
                    "[PRESS — standing now. Full body tension. "
                    "Left at 24 kg standing is significant progress from 20 kg half-kneeling.]",
                    "SUPERSET A2 — Double KB Deadlift 5×4 @ 40 kg/bell  [HINGE — the pull is the shoulder's rest]",
                    "Ab Wheel Rollout 4×10  [CORE]",
                ],
                "focus": [
                    "Cossack Squat 3×6/side @ 16 kg  (lateral athletic mobility)",
                    "Y-T-W 3×12 @ 8 kg  (maintenance)",
                    "Face Pull 3×20",
                ],
                "corrective": [
                    "Serratus Wall Slide 2×10  (maintenance — always)",
                    "KB Arm Bar LEFT 2×60 s @ 20 kg  (↑ load)",
                    "Scalene Stretch LEFT 2×90 s",
                ],
                "finisher": (
                    "Ultra-short race pace:\n"
                    "12 × (8 Double KB Swings @ 32 kg + 30 s rest)\n"
                    "96 total reps. Maximum power every set."
                ),
            },
            2: {
                "label": "Week 10 — More standing press volume.",
                "main":  "Double KB Swing 10×8 @ 32 kg/bell",
                "full_body": [
                    "SUPERSET A1 — Standing Single-Arm KB Press 5×5/side @ RIGHT: 28 kg / LEFT: 24-28 kg  "
                    "[PRESS — test 28 kg LEFT this week]",
                    "SUPERSET A2 — Double KB Deadlift 5×4 @ 40 kg/bell  [HINGE]",
                    "Ab Wheel Rollout 4×12  [CORE]",
                ],
                "focus": [
                    "Cossack Squat 4×6/side @ 16 kg",
                    "Y-T-W 3×12 @ 8 kg",
                    "Overhead Carry LEFT 4×20 m @ 24 kg  (maintenance)",
                ],
                "corrective": [
                    "Serratus Wall Slide 2×10",
                    "Scalene Stretch LEFT 2×90 s",
                ],
                "finisher": (
                    "12 × (8 Double KB Swings @ 36 kg + 30 s rest)\n"
                    "↑ load from week 9"
                ),
            },
            3: {
                "label": "Week 11 — Peak strength. Left side strong.",
                "main":  "Double KB Swing 12×6 EMOM @ 36 kg/bell",
                "full_body": [
                    "SUPERSET A1 — Standing Single-Arm KB Press 4×4/side @ RIGHT: 32 kg / LEFT: 28 kg  "
                    "[PRESS — this is where you were with bilateral before injury. "
                    "Unilateral LEFT at 28 kg = equivalent bilateral demand at 32+ kg. "
                    "You are back.]",
                    "SUPERSET A2 — Double KB Deadlift 4×3 @ 40 kg/bell  [HINGE — near max]",
                    "Hanging Leg Raise 4×12  [CORE]",
                ],
                "focus": [
                    "Cossack Squat 3×6/side @ 20 kg  (↑ load)",
                    "Y-T-W 4×10 @ 10 kg",
                    "Overhead Carry LEFT 4×30 m @ 28 kg",
                ],
                "corrective": [
                    "Serratus Wall Slide 3×10  (peak week — extra activation)",
                    "Scalene Stretch LEFT 3×90 s",
                ],
                "finisher": (
                    "The benchmark:\n"
                    "12 × (8 Double KB Swings @ 40 kg + 30 s rest)\n"
                    "40 kg bells. 96 reps. This is elite."
                ),
            },
            4: {
                "label": "Week 12 — Final deload. You did it.",
                "main":  "Two-Hand KB Swing 5×10 @ 24 kg  (light — feel the ease)",
                "full_body": [
                    "SUPERSET A1 — Standing Single-Arm KB Press 3×5/side @ 20 kg  [PRESS — easy]",
                    "SUPERSET A2 — Double KB Deadlift 3×5 @ 32 kg/bell  [HINGE — moderate]",
                    "Dead Bug 3×10/side  [CORE]",
                ],
                "focus": [
                    "Hip Flexor Stretch 2×90 s/side",
                    "Thoracic Rotation 2×10/side",
                ],
                "corrective": [
                    "Serratus Wall Slide 2×10",
                    "Full corrective flow 10 min — everything",
                    "Scalene Stretch LEFT 2×90 s",
                ],
                "finisher": (
                    "KB flow 10 min @ 20 kg\n"
                    "12 weeks ago your left pressed 20 kg and fatigued quickly.\n"
                    "Today you stand-pressed 28 kg for sets.\n"
                    "The gap is closed. The pattern is restored.\n"
                    "What comes next is up to you."
                ),
            },
        },
    },

    "strength_b": {
        "name":   "Strength B — Heavy Pull + Performance Upper",
        "anchor": "Heavy Single-Arm Row + Overhead Carry",
        "weeks": {
            1: {
                "label": "Week 9 — Heavy pulling. You're strong here.",
                "main":  "Single-Arm KB Row 5×6/side @ 40 kg",
                "full_body": [
                    "SUPERSET A1 — Standing Single-Arm Press 4×4/side @ RIGHT: 28 kg / LEFT: 24 kg  [PRESS]",
                    "SUPERSET A2 — KB Goblet Squat 4×6 @ 40 kg  [LOWER — shoulder rests while you squat]",
                    "SUPERSET B1 — Renegade Row 4×6/side @ 28 kg  [PULL — heavy renegade]",
                    "SUPERSET B2 — Ab Wheel 4×12  [CORE]",
                ],
                "focus": [
                    "Overhead Carry LEFT then RIGHT 5×20 m @ 28 kg",
                    "Dead Hang 4×60 s",
                    "Band Pull-Apart 4×30",
                ],
                "corrective": [
                    "Bottoms-Up Press LEFT 3×5 @ 20 kg  (heaviest BU press)",
                    "Scalene Stretch LEFT 2×90 s",
                ],
                "finisher": "KB Snatch EMOM 12 min: 6/side @ 28 kg",
            },
            2: {
                "label": "Week 10 — Volume on pulls.",
                "main":  "Single-Arm KB Row 6×6/side @ 40 kg  (add a set)",
                "full_body": [
                    "SUPERSET A1 — Standing Single-Arm Press 5×4/side @ RIGHT: 28 kg / LEFT: 24-28 kg  [PRESS]",
                    "SUPERSET A2 — KB Goblet Squat 4×5 @ 40 kg  [LOWER — shoulder rests here]",
                    "SUPERSET B1 — Renegade Row 4×5/side @ 32 kg  [PULL — heavier]",
                    "SUPERSET B2 — Ab Wheel 4×12  [CORE]",
                ],
                "focus": [
                    "Overhead Carry 5×30 m/side @ 28 kg  (longer)",
                    "Dead Hang 4×60 s",
                    "Serratus Wall Slide 3×10",
                ],
                "corrective": [
                    "Sleeper Stretch LEFT 3×90 s",
                    "90/90 Shoulder Rotation LEFT 3×12",
                ],
                "finisher": "KB Snatch EMOM 15 min: 6/side @ 28 kg",
            },
            3: {
                "label": "Week 11 — Peak pulling strength.",
                "main":  "Single-Arm KB Row 4×5/side @ 40 kg  (heavy — RPE 9)",
                "full_body": [
                    "SUPERSET A1 — Standing Single-Arm Press 4×4/side @ RIGHT: 32 kg / LEFT: 28 kg  [PRESS]",
                    "SUPERSET A2 — KB Goblet Squat 4×4 @ 40 kg  [LOWER — shoulder rests here]",
                    "SUPERSET B1 — Renegade Row 4×4/side @ 32 kg  [PULL — max renegade]",
                    "SUPERSET B2 — Hanging Leg Raise 4×15  [CORE]",
                ],
                "focus": [
                    "Overhead Carry LEFT 5×30 m @ 32 kg  (peak load — "
                    "left shoulder overhead at 32 kg is remarkable after week 1)",
                    "Dead Hang 5×60 s",
                    "Band Pull-Apart 4×30",
                ],
                "corrective": [
                    "Bottoms-Up Press LEFT 3×5 @ 20 kg",
                    "Scalene Stretch LEFT 3×90 s",
                ],
                "finisher": (
                    "Carry Gauntlet × 5:\n"
                    "  Overhead LEFT 30 m → Rack RIGHT 30 m → Farmer both 30 m @ 28 kg\n"
                    "  Rest 90 s. This is performance."
                ),
            },
            4: {
                "label": "Week 12 — Final deload. Long hangs. Celebrate.",
                "main":  "Single-Arm KB Row 3×8/side @ 28 kg  (light)",
                "full_body": [
                    "SUPERSET A1 — Standing Single-Arm Press 2×5/side @ 20 kg  [PRESS — easy]",
                    "SUPERSET A2 — KB Goblet Squat 2×10 @ 28 kg  [LOWER]",
                    "SUPERSET B1 — Renegade Row 2×5/side @ 20 kg  [PULL]",
                    "SUPERSET B2 — Dead Bug 3×10/side  [CORE]",
                ],
                "focus": [
                    "Overhead Carry 2×20 m/side @ 20 kg  (light)",
                    "Dead Hang 3×60 s",
                    "Band Pull-Apart 2×20",
                ],
                "corrective": [
                    "Full corrective flow — everything that helped",
                    "Rena massage on serratus/sub-scap if available",
                    "Arm bar after immediately",
                ],
                "finisher": "KB flow 10 min @ 16-20 kg  (12 weeks. You're done. Well done.)",
            },
        },
    },

    "strength_c": {
        "name":   "Strength C — Peak Hardstyle Performance",
        "anchor": "Double KB Swing + Complex Conditioning",
        "weeks": {
            1: {
                "label": "Week 9 — Elite conditioning. Ultra-short race pace.",
                "main":  "Double KB Swing EMOM 20 min: 10 reps/min @ 36 kg/bell",
                "full_body": [
                    "SUPERSET A1 — Standing Single-Arm Clean + Press 4×4/side @ RIGHT: 28 kg / LEFT: 24 kg  [PUSH]",
                    "SUPERSET A2 — KB Goblet Squat 4×4 @ 40 kg  [LOWER]",
                    "SUPERSET B1 — Push-Up 5×20  [PUSH]",
                    "SUPERSET B2 — Ab Wheel 4×12  [CORE]",
                ],
                "focus": [
                    "KB Snatch 5×5/side @ 28 kg  (heavy snatch)",
                    "Single-Leg Hip Thrust 4×8/side @ 40 kg",
                ],
                "corrective": ["Serratus Wall Slide 3×10"],
                "finisher": (
                    "The race set:\n"
                    "15 × (6 Double KB Swings @ 36 kg + 30 s rest)\n"
                    "90 total reps. Maximum power. Complete rest. Pure swimming logic."
                ),
            },
            2: {
                "label": "Week 10 — Peak volume.",
                "main":  "Double KB Swing EMOM 25 min: 10 reps/min @ 36 kg/bell",
                "full_body": [
                    "SUPERSET A1 — Standing Single-Arm Clean + Press 5×4/side @ RIGHT: 32 kg / LEFT: 28 kg  [PUSH]",
                    "SUPERSET A2 — KB Goblet Squat 5×4 @ 40 kg  [LOWER]",
                    "SUPERSET B1 — Push-Up 5×20  [PUSH]",
                    "SUPERSET B2 — Hanging Leg Raise 4×12  [CORE]",
                ],
                "focus": [
                    "KB Snatch 6×5/side @ 28 kg",
                    "Single-Leg Hip Thrust 4×6/side @ 40 kg",
                ],
                "corrective": ["Serratus Wall Slide 3×10"],
                "finisher": (
                    "15 × (6 Double KB Swings @ 40 kg + 30 s rest)\n"
                    "40 kg bells. This is where you were before. You're back."
                ),
            },
            3: {
                "label": "Week 11 — Peak everything.",
                "main":  "Double KB Swing 15×5 EMOM @ 40 kg/bell  (near-max load)",
                "full_body": [
                    "SUPERSET A1 — Standing Single-Arm Clean + Press 4×3/side @ RIGHT: 32 kg / LEFT: 28-32 kg  "
                    "[PUSH — left at 32 kg standing. This is where you were with doubles before.]",
                    "SUPERSET A2 — KB Goblet Squat 4×3 @ 40 kg  [LOWER — heavy]",
                    "SUPERSET B1 — Push-Up 5×20  [PUSH]",
                    "SUPERSET B2 — Ab Wheel 4×15  [CORE]",
                ],
                "focus": [
                    "KB Snatch 5×4/side @ 32 kg  (heavy — RPE 8-9)",
                    "Single-Leg Hip Thrust 4×5/side @ 40 kg",
                ],
                "corrective": ["Serratus Wall Slide 3×10"],
                "finisher": (
                    "The 12-week test:\n"
                    "10 × (10 Double KB Swings @ 40 kg + 30 s rest)\n"
                    "Then: 50 KB Snatches (25/side) @ 28 kg\n"
                    "Then: 30 Push-Ups\n"
                    "For time. This is your 12-week fitness test.\n"
                    "12 weeks ago your left side was fading at 20 kg. Today you're here."
                ),
            },
            4: {
                "label": "Week 12 — Deload. Reflect.",
                "main":  "Two-Hand KB Swing 5×10 @ 24 kg  (light)",
                "full_body": [
                    "SUPERSET A1 — Standing Single-Arm Press 2×5/side @ 20 kg  [PUSH — easy]",
                    "SUPERSET A2 — KB Goblet Squat 2×10 @ 28 kg  [LOWER]",
                    "SUPERSET B1 — Push-Up 2×10  [PUSH]",
                    "SUPERSET B2 — Dead Bug 3×10/side  [CORE]",
                ],
                "focus": [
                    "Hip Flexor Stretch 2×90 s/side",
                    "Arm Bar LEFT 2×90 s",
                ],
                "corrective": ["Diaphragmatic breathing 5 min"],
                "finisher": (
                    "KB flow 10 min @ 20 kg\n"
                    "You came in with a 4 kg bilateral press gap and chronic trap ache.\n"
                    "The gap is closed. The serratus is awake.\n"
                    "The double 70lb reds are waiting."
                ),
            },
        },
    },

    "strength_d": {
        "name":  "Strength D — Saturday Optional (Program 3)",
        "weeks": {
            1: {
                "label": "Week 9 — Heavy deadlift + overhead squat skill",
                "main":  "Double KB Deadlift 5×2 @ 40 kg/bell  (max load — 2 perfect reps)",
                "skill": "KB Overhead Squat Single-Arm 3×5/side @ 16 kg  "
                         "(progression from dowel — actual load now)",
                "prevention": [
                    "Y-Balance Reach 3×5/side",
                    "Copenhagen Plank 3×30 s/side",
                    "Serratus Wall Slide 3×10",
                ],
                "mobility_block": [
                    "Athletic mobility circuit 20 min",
                    "Warrior flow + Warrior III balance",
                    "Scalene stretch LEFT 3×90 s",
                    "Legs-up-the-wall 10 min — arms in Y",
                ],
                "finisher": "BUTT BURNER 5000 (Dan John) @ 12 kg  — Ladder 1→10: 1 KB hip hinge (goat-bag swing/RDL) + 1 goblet squat, 2+2 … up to 10+10. Pure lower body, zero shoulder load. Light and flowing — cardio. Juggle/play after if you've got time.",
            },
            2: {
                "label": "Week 10 — Heavy deadlift + press skill",
                "main":  "Double KB Deadlift 5×2 @ 40 kg/bell",
                "skill": "Standing Single-Arm Press 3×5/side @ LEFT: 24 kg  "
                         "(Saturday skill — left shoulder focus)",
                "prevention": [
                    "Copenhagen Plank 3×30 s/side",
                    "Bottoms-Up Press LEFT 2×5 @ 16 kg",
                    "Serratus Wall Slide 3×10",
                ],
                "mobility_block": [
                    "Yoga strength flow 20 min",
                    "Scalene stretch LEFT 3×90 s",
                    "Legs-up-the-wall 10 min",
                ],
                "finisher": "BUTT BURNER 5000 @ 12 kg  — Same 1→10 ladder, hip hinge + goblet squat each rung. Push the pace a touch — note your time. Play after if you want.",
            },
            3: {
                "label": "Week 11 — Peak Saturday. Heavy and mobile.",
                "main":  "Double KB Deadlift 4×2 @ 40 kg/bell  (near-max)",
                "skill": "Single-Arm Overhead Squat LEFT 3×5 @ 20 kg  (heavy skill work)",
                "prevention": [
                    "Y-Balance Reach 3×5/side",
                    "Serratus Wall Slide 3×10",
                    "Scalene stretch LEFT 3×90 s",
                ],
                "mobility_block": [
                    "Yin yoga 20 min — deepest session of the cycle",
                    "Dragon pose 3 min/side",
                    "Sleeping swan 3 min/side",
                    "Savasana 5 min",
                ],
                "finisher": "BUTT BURNER 5000 @ 16 kg  — 1→10 ladder, hip hinge + goblet squat each rung. Peak week — up a bell but keep it flowing. Play after.",
            },
            4: {
                "label": "Week 12 — Light + celebration mobility",
                "main":  "Double KB Deadlift 3×3 @ 32 kg/bell  (light)",
                "skill": "Dowel Overhead Squat 3×8  (back to basics — notice transformation)",
                "prevention": ["Serratus Wall Slide 2×10", "Band Pull-Apart 2×20"],
                "mobility_block": [
                    "Move through whatever your body needs",
                    "Honor the 12 weeks",
                    "Savasana 5 min",
                ],
                "finisher": (
                    "KB flow / juggling 10 min @ any weight\n"
                    "12 weeks. Done.\n"
                    "Now plan what comes next."
                ),
            },
        },
    },

    "mobility": {
        "name":  "Mobility — Kyle Program 3",
        "focus": "Performance mobility, advanced breathing, maintenance corrective",
        "sessions": {
            "A": {
                "label": "Mobility A — Performance Thoracic + Advanced Nerve Work",
                "opening": ["Diaphragmatic Breathing 5 min  (12 weeks in — this should feel natural now)"],
                "main": "Serratus Wall Slide 3×12 + Bear Plank Reach 3×10/side  (maintenance)",
                "sequence": [
                    "KB Arm Bar with Rotation LEFT 3×10 @ 20 kg  (heaviest arm bar)",
                    "Scalene Stretch LEFT 4×90 s",
                    "Sleeper Stretch LEFT 4×90 s",
                    "Sub-Scap Release LEFT 2×90 s  (lacrosse ball — you know where the tissue is)",
                    "Cossack Squat flow 2×10/side  (lateral hip mobility)",
                    "Warrior III balance 3×30 s/side  (proprioception)",
                ],
                "nerve_gliding": [
                    "All three nerve glides LEFT: brachial plexus + ulnar + radial 3×12 each",
                    "These should feel easier than week 1. The tissue is clearing.",
                ],
                "finisher": "Legs-Up-the-Wall 10 min — arms in Y  (10 min is now standard for you)",
            },
            "B": {
                "label": "Mobility B — Peak Breathing + Full Release",
                "opening": ["Diaphragmatic Breathing 5 min"],
                "main": "Sub-Scap Release LEFT 3×90 s  (deepest release of the program)",
                "sequence": [
                    "90/90 Shoulder Rotation LEFT 3×15  (full range — compare to week 1)",
                    "Doorframe Pec Stretch 3×90 s",
                    "Thoracic Extension over roller 3×60 s",
                    "Full yoga flow 10 min — whatever feels good",
                ],
                "breathing_protocol": [
                    "Box Breathing 5 min: 6-6-6-6  (harder than 4-4-4-4 — longer cycles)",
                    "4-7-8 Breathing 4 rounds",
                    "5 min silence — just notice your breathing pattern",
                    "(After 12 weeks of breathing work your resting pattern should "
                    "have shifted toward diaphragmatic. This is measurable. "
                    "Your HRV has likely improved. Your trap resting tone has likely decreased.)",
                ],
                "finisher": (
                    "Legs-Up-the-Wall 10 min — arms in Y\n\n"
                    "If Rena does massage on the serratus/sub-scap bundle today:\n"
                    "  → Arm bar immediately after (tissue is released + warm)\n"
                    "  → Then legs-up-the-wall\n"
                    "  → Then 5 min diaphragmatic breathing\n\n"
                    "This sequence is the most therapeutic thing available to you "
                    "outside of clinical care. Use it."
                ),
            },
        },
    },
}


# ============================================================================
#  PROGRAM NOTES FOR KYLE
# ============================================================================

KYLE_PROGRAM_NOTES = {
    "north_star": (
        "The gap: LEFT 20 kg → RIGHT 24 kg at program start.\n"
        "The goal: 24/24 by week 12.\n"
        "Track both sides every pressing session. The gap closing IS the program working."
    ),
    "on_geoff_kb_strong": (
        "KB Strong is a great program for someone with bilateral symmetry.\n"
        "It was reinforcing your asymmetry. You knew this.\n"
        "Single-arm pressing for 12 weeks will reset the pattern."
    ),
    "on_visual_disturbance": (
        "The head pressure and visual disturbance during bilateral overhead pressing "
        "is vascular thoracic outlet compression.\n"
        "Single-arm pressing at appropriate loads should not trigger this.\n"
        "If it does: stop, note the load, report it.\n"
        "This program avoids bilateral overhead pressing entirely."
    ),
    "on_diaphragmatic_breathing": (
        "Shallow chest breathing chronically elevates the structures around "
        "the thoracic outlet and maintains compression.\n"
        "Diaphragmatic breathing mechanically decompresses the thoracic outlet "
        "with every exhale.\n"
        "5 minutes daily is therapeutic, not optional."
    ),
    "on_rena_massage": (
        "The manual release Rena does on the serratus/sub-scap bundle is "
        "probably the most therapeutic intervention available to you.\n"
        "The tingling it produces is the brachial plexus being unloaded.\n"
        "Timing: immediate arm bar after massage while tissue is released.\n"
        "Frequency: as often as possible."
    ),
    "on_the_double_70lb_reds": (
        "You pressed double 70lb reds before.\n"
        "That's 32 kg per hand.\n"
        "By week 12 you'll be standing-pressing 28-32 kg left.\n"
        "The reds are waiting."
    ),
    "after_12_weeks": (
        "After this program:\n"
        "Option 1: Repeat with heavier starting weights. Your movement history carries over.\n"
        "Option 2: Cautiously reintroduce bilateral pressing — single sets, "
        "monitor for visual disturbance, bilateral only after unilateral warmup.\n"
        "Option 3: Design Program 4 based on what you learned.\n\n"
        "The corrective work never fully stops. Serratus wall slides and "
        "diaphragmatic breathing become permanent fixtures.\n"
        "The scar tissue will always be there. The question is whether it's "
        "mobile or rigid. Keep it mobile."
    ),
}


# ── Program lists by track ────────────────────────────────────────────────────
PROGRAMS = [PROGRAM_1, PROGRAM_2, PROGRAM_3]  # default fighter track

TRACK_PROGRAMS = {
    'fighter': [PROGRAM_1, PROGRAM_2, PROGRAM_3],
    'kyle':    [KYLE_PROGRAM_1, KYLE_PROGRAM_2, KYLE_PROGRAM_3],
}

# NOTE: ARMS_ROTATION (curl/tricep pairing per program × day) was removed in
# the v3 Fighter merge — it was already dead code (nothing read it; strength
# days pull "arms" straight from week_data) and its keys (strength_a/b/c/d)
# no longer exist in the Fighter schema. Kyle never used it (no arms work).

# Day-of-week → session type (Monday=0 ... Sunday=6). Track-specific: Kyle
# keeps the original 6-day/1-rest structure; Fighter (v3) runs 4x/lifts 2x
# with Swing/Conditioning folded onto the short interval day — no rest day,
# confirmed with Rena (flagged, not unnoticed).
_DOW_TO_SESSION_KYLE = [
    "strength_a",   # 0 Monday
    "mobility_a",   # 1 Tuesday
    "strength_b",   # 2 Wednesday
    "mobility_b",   # 3 Thursday
    "strength_c",   # 4 Friday
    "strength_d",   # 5 Saturday (optional)
    "rest",         # 6 Sunday
]
_DOW_TO_SESSION_FIGHTER = [
    "strength_hinge",              # 0 Monday
    "run_easy",                    # 1 Tuesday
    "strength_squat_hipthrust",    # 2 Wednesday
    "run_interval",                # 3 Thursday
    "run_easy",                    # 4 Friday
    "strength_swing_conditioning", # 5 Saturday
    "run_long",                    # 6 Sunday
]

# Maps session types to track_key strings that trigger existing badge CSS
_SESSION_TRACK_KEY = {
    "strength_a": "day_a_strength",
    "strength_b": "day_b_strength",
    "strength_c": "day_c_strength",
    "strength_d": "day_d_strength",
    "mobility_a": "mobility_flow",
    "mobility_b": "mobility_flow",
    "strength_hinge":              "hinge_strength",
    "strength_squat_hipthrust":    "squat_hipthrust_strength",
    "strength_swing_conditioning": "swing_conditioning_strength",
    "run_easy":     "run_easy",
    "run_interval": "run_interval",
    "run_long":     "run_long",
}

WK_TARGET = 4   # activities/week for streak


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
        "program_start_iso":  None,    # set when user picks a track
        "program_track":      None,    # None = new user, show selector
        "workouts":           [],
        "ruck_log":           [],
        "run_log":            [],
        "walk_log":           [],
        "week_log":           {},
        "custom_tracks":      [],
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


def _get_program_and_week(state: dict, today: dt.date | None = None) -> tuple:
    """Returns (program_idx 0–2, current_week 1–4, weeks_elapsed).
    Derives from program_start_iso — no user action needed to advance."""
    today     = today or dt.date.today()
    start_iso = state.get("program_start_iso")
    if not start_iso:
        monday = today - dt.timedelta(days=today.weekday())
        state["program_start_iso"] = str(monday)
        start_iso = str(monday)
    try:
        start = dt.date.fromisoformat(start_iso)
    except ValueError:
        monday = today - dt.timedelta(days=today.weekday())
        state["program_start_iso"] = str(monday)
        start = monday
    weeks_elapsed = max(0, (today - start).days // 7)
    week_in_cycle = weeks_elapsed % 12   # 0–11
    program_idx   = week_in_cycle // 4   # 0–2
    current_week  = (week_in_cycle % 4) + 1  # 1–4
    return program_idx, current_week, weeks_elapsed


def _parse_std_kg(main_text: str, default: float = 16.0) -> float:
    """Extract first '@ N kg' weight from a string; returns default when absent."""
    m = re.search(r'@\s*(\d+(?:\.\d+)?)\s*kg', main_text or "")
    return float(m.group(1)) if m else default


def _first_kg(strings: list) -> float | None:
    """Return the weight (kg) from the first item in a list that contains '@ N kg'.
    Returns None when no item has an explicit weight."""
    for s in (strings or []):
        m = re.search(r'@\s*(\d+(?:\.\d+)?)\s*kg', s or "")
        if m:
            return float(m.group(1))
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_today_workout(state: dict, for_date: dt.date | None = None) -> dict:
    today        = for_date or dt.date.today()
    dow          = today.weekday()          # 0=Mon … 6=Sun
    track        = state.get("program_track", "fighter")
    dow_map      = _DOW_TO_SESSION_KYLE if track == "kyle" else _DOW_TO_SESSION_FIGHTER
    session_type = dow_map[dow]

    # ── Rest day ──────────────────────────────────────────────────────────────
    if session_type == "rest":
        return {
            "status":  "rest",
            "message": "Rest day — active recovery or mobility if you feel like it.",
        }

    # ── No program selected yet (new user before track selector) ──────────────
    if not state.get("program_start_iso"):
        return {"no_program": True, "message": "No program selected yet"}

    # ── Program selected but start date hasn't arrived yet ────────────────────
    start_iso = state.get("program_start_iso", "")
    if str(today) < start_iso:
        programs  = TRACK_PROGRAMS.get(track, TRACK_PROGRAMS["fighter"])
        program   = programs[0]   # always preview Program 1, Week 1, first strength day
        first_key = "strength_a" if track == "kyle" else "strength_hinge"
        sa        = program.get(first_key, {})
        week1     = sa.get("weeks", {}).get(1, {})
        return {
            "status":           "pending",
            "program_start_iso": start_iso,
            "preview_label":    sa.get("name", "Strength A"),
            "preview_main":     week1.get("main", ""),
            "message":          f"Your program begins {start_iso}. Rest up and get ready.",
        }

    program_idx, current_week, weeks_elapsed = _get_program_and_week(state, today=today)
    programs = TRACK_PROGRAMS.get(track, TRACK_PROGRAMS["fighter"])
    program  = programs[program_idx]
    is_kyle  = (track == "kyle")
    current_prog = program_idx + 1          # 1–3
    track_key    = _SESSION_TRACK_KEY.get(session_type, "day_a_strength")

    # ── Custom track (legacy support) ────────────────────────────────────────
    custom_key = state.get("track", "")
    if custom_key and custom_key.startswith("custom_"):
        ct = _get_custom_track(state, custom_key)
        if ct:
            mc  = state.setdefault("microcycle", {"id": 0, "sessions_completed": 0,
                                                   "start_date": str(today), "completed": False})
            idx = mc.get("sessions_completed", 0)
            sessions_needed = len(ct["sessions"])
            if idx >= sessions_needed:
                return {"status": "cycle_complete",
                        "message": "Cycle complete! Start a new track."}
            sess   = ct["sessions"][idx]
            std_kg = float(sess.get("std_kg", 16) or 16)
            return {
                "status":           "active",
                "track_key":        custom_key,
                "track_name":       ct["name"],
                "day_type":         "strength",
                "focus":            "",
                "week_label":       sess.get("week_label", ""),
                "session_idx":      idx,
                "total_sessions":   sessions_needed,
                "main":             sess.get("main", ""),
                "std_kg":           std_kg,
                "full_body_block":  sess.get("full_body_block", sess.get("accessory", [])),
                "focus_work":       sess.get("focus_work", []),
                "arms":             sess.get("arms", []),
                "finisher":         sess.get("finisher", ""),
                "bell_guidance":    "",
                "cycle_week":       current_week,
                "suggested_weight": std_kg,
            }

    # ── Fighter v3 — Run days (Easy / Interval / Long) ────────────────────────
    # Same "run_day" contract the UI already renders (rehab / run_prescription
    # / stretch). All three now carry explicit weeks{1-4} content: Easy/Long
    # give real mileage+pace (anchored to Rena's documented baseline, +10%/wk,
    # cutback wk4); Interval gives the ladder + perceived-effort pacing, by
    # her choice — no time trial run yet, so no fabricated target splits.
    if session_type in ("run_easy", "run_interval", "run_long"):
        run_block  = program[session_type]
        week_data  = run_block["weeks"][current_week]
        week_label = week_data["label"]
        if session_type == "run_interval":
            run_line = f"{week_data['ladder']}  — {week_data['note']}"
        else:
            run_line = week_data["run_line"]
        return {
            "status":           "active",
            "track_key":        track_key,
            "track_name":       run_block["name"],
            "day_type":         "run_day",
            "session_type":     session_type,
            "program_name":     program["name"],
            "current_program":  current_prog,
            "current_week":     current_week,
            "week_label":       week_label,
            "session_idx":      current_week - 1,
            "total_sessions":   4,
            "main":             run_line,
            "rehab":            run_block.get("rehab", []),
            "run_prescription": run_line,
            "stretch":          run_block.get("stretch", []),
            "arms":             [],
            "finisher":         "",
            "bell_guidance":    run_block.get("purpose", ""),
            "cycle_week":       current_week,
            "suggested_weight": 0,
            "std_kg":           0,
        }

    # ── Mobility / Run-Day sessions (Kyle only — Fighter is handled above) ────
    if session_type in ("mobility_a", "mobility_b"):
        mob_key = "A" if session_type == "mobility_a" else "B"
        mob     = program["mobility"]["sessions"][mob_key]

        if is_kyle:
            # Kyle mobility: opening + sequence → full_body_block;
            # nerve_gliding + breathing_protocol → focus_work
            full_body_blk = mob.get("opening", []) + mob.get("sequence", [])
            focus_blk     = mob.get("nerve_gliding", []) + mob.get("breathing_protocol", [])
            mob_main      = mob.get("main", "")
            mob_main_kg   = _parse_std_kg(mob_main, default=8.0)
            return {
                "status":           "active",
                "track_key":        track_key,
                "track_name":       program["mobility"]["name"],
                "day_type":         "mobility",
                "session_type":     session_type,
                "program_name":     program["name"],
                "current_program":  current_prog,
                "current_week":     current_week,
                "week_label":       mob["label"],
                "session_idx":      current_week - 1,
                "total_sessions":   4,
                "main":             mob_main,
                "std_kg":           mob_main_kg,
                "full_body_block":  full_body_blk,
                "focus_work":       focus_blk,
                "arms":             [],
                "finisher":         mob.get("finisher", ""),
                "bell_guidance":    "Lighter than you think. Quality over load.",
                "cycle_week":       current_week,
                "suggested_weight": mob_main_kg,
                "weights_by_section": {
                    "main":      mob_main_kg,
                    "full_body": _first_kg(full_body_blk),
                    "focus":     _first_kg(focus_blk),
                    "arms":      None,
                    "finisher":  _first_kg([mob.get("finisher","")]) if mob.get("finisher") else None,
                },
            }
        else:
            # Fighter v2: run-day format — rehab / run prescription / stretch
            session_label = "A" if session_type == "mobility_a" else "B"
            return {
                "status":          "active",
                "track_key":       track_key,
                "track_name":      program["mobility"]["name"],
                "day_type":        "run_day",
                "session_type":    session_type,
                "program_name":    program["name"],
                "current_program": current_prog,
                "current_week":    current_week,
                "week_label":      mob["label"],
                "session_idx":     current_week - 1,
                "total_sessions":  4,
                "main":            mob["run"],
                "rehab":           mob.get("rehab", []),
                "run_prescription": mob["run"],
                "stretch":         mob.get("stretch", []),
                "arms":            [],
                "finisher":        "",
                "bell_guidance":   "",
                "cycle_week":      current_week,
                "suggested_weight": 0,
                "std_kg":          0,
            }

    # ── Strength sessions (A / B / C / D) ────────────────────────────────────
    day_data  = program[session_type]
    week_data = day_data["weeks"][current_week]
    std_kg    = _parse_std_kg(week_data["main"])

    if is_kyle:
        # Kyle has no arms; ARMS_ROTATION does not apply
        arms_list = []
        if session_type == "strength_d":
            # skill → single-item full_body_block; prevention → focus_work
            skill = week_data.get("skill", "")
            full_body_blk = [skill] if skill else []
            focus_blk     = week_data.get("prevention", [])
        else:
            # strength_a / b / c: full_body + focus + corrective merged into focus
            full_body_blk = week_data.get("full_body", [])
            focus_blk     = week_data.get("focus", []) + week_data.get("corrective", [])
    else:
        # Fighter v2: arms, full_body_block, focus_work are all inline in week data
        full_body_blk = week_data.get("full_body_block", week_data.get("full_body", []))
        focus_blk     = week_data.get("focus_work",      week_data.get("focus",      []))
        arms_list     = week_data.get("arms", [])

    result = {
        "status":           "active",
        "track_key":        track_key,
        "track_name":       day_data["name"],
        "day_type":         "strength",
        "session_type":     session_type,
        "program_name":     program["name"],
        "current_program":  current_prog,
        "current_week":     current_week,
        "week_label":       week_data["label"],
        "session_idx":      current_week - 1,
        "total_sessions":   4,
        "main":             week_data["main"],
        "std_kg":           std_kg,
        "full_body_block":  full_body_blk,
        "focus_work":       focus_blk,
        "arms":             arms_list,
        "finisher":         week_data.get("finisher", ""),
        "bell_guidance":    day_data.get("anchor", day_data.get("focus", "")),
        "circuit_note":     week_data.get("circuit_note", ""),   # Fighter v3 circuit days: "N rounds — Xs/Ys rest" caption
        "cycle_week":       current_week,
        "suggested_weight": std_kg,
        "weights_by_section": {
            "main":      std_kg,
            "full_body": _first_kg(full_body_blk),
            "focus":     _first_kg(focus_blk),
            "arms":      _first_kg(arms_list),
            "finisher":  _first_kg([week_data["finisher"]]) if week_data.get("finisher") else None,
        },
    }
    # Saturday only: include mobility block
    if session_type == "strength_d":
        result["mobility_block"] = week_data.get("mobility_block", [])
    # Kyle: expose pre_session activation block
    if is_kyle:
        result["pre_session"] = program.get("pre_session", [])

    return result


def get_track_detail(key: str) -> dict | None:
    """Returns detail for a built-in program track key like 'program_1'."""
    if key.startswith("program_"):
        try:
            idx = int(key.split("_")[1]) - 1
            p   = PROGRAMS[idx]
            return {"key": key, "name": p["name"], "subtitle": p.get("subtitle", "")}
        except (IndexError, ValueError):
            return None
    return None


def get_custom_track_detail(state: dict, track_id: str) -> dict | None:
    for ct in state.get("custom_tracks", []):
        if str(ct.get("id", "")) == str(track_id):
            return ct
    return None


def init_track(state: dict, key: str) -> str:
    """Select a custom track, or reset program start for a built-in program key."""
    if key.startswith("custom_"):
        ct = _get_custom_track(state, key)
        if ct is None:
            return f"Custom track not found: {key}"
        state["track"] = key
        mc = state.setdefault("microcycle", {})
        mc["id"]                 = mc.get("id", 0) + 1
        mc["sessions_completed"] = 0
        mc["start_date"]         = str(dt.date.today())
        mc["completed"]          = False
        return f"Started {ct['name']}"
    if key.startswith("program_"):
        try:
            idx   = int(key.split("_")[1]) - 1
            PROGRAMS[idx]   # validate
        except (IndexError, ValueError):
            return f"Unknown program: {key}"
        # Set program_start_iso so program_idx lands on the right one
        # weeks_elapsed % 12 // 4 == idx  →  weeks_elapsed = idx * 4
        monday = dt.date.today() - dt.timedelta(days=dt.date.today().weekday())
        # Back-calculate a Monday that puts us at week 1 of the chosen program
        target_weeks = idx * 4
        state["program_start_iso"] = str(monday - dt.timedelta(weeks=target_weeks))
        state.pop("track", None)
        return f"Started {PROGRAMS[idx]['name']}"
    return f"Unknown track: {key}"


def log_rec(state: dict, weights_lbs: dict | None = None) -> str:
    workout = get_today_workout(state)
    if workout.get("status") == "rest":
        return "Rest day — nothing to log as a recommended session."
    if workout.get("status") != "active":
        return workout.get("message", "No workout available.")

    entry: dict = {
        "date":         str(dt.date.today()),
        "type":         "recommended",
        "details":      workout.get("main", ""),
        "day_type":     workout.get("day_type", "strength"),
        "session_type": workout.get("session_type", ""),
        "program":      workout.get("current_program", 1),
        "week":         workout.get("current_week", 1),
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
    # Keep legacy microcycle counter ticking for any code that reads it
    mc = state.setdefault("microcycle", {"id": 0, "sessions_completed": 0,
                                         "start_date": str(dt.date.today()), "completed": False})
    mc["sessions_completed"] = mc.get("sessions_completed", 0) + 1
    _increment_weekly_count(state)
    return f"Session logged: {workout.get('main', '')[:80]}"


def log_custom(state: dict, text: str) -> str:
    state["workouts"].append({
        "date":     str(dt.date.today()),
        "type":     "custom",
        "details":  text,
        "day_type": "custom",
    })
    mc = state.setdefault("microcycle", {"id": 0, "sessions_completed": 0,
                                         "start_date": str(dt.date.today()), "completed": False})
    mc["sessions_completed"] = mc.get("sessions_completed", 0) + 1
    _increment_weekly_count(state)
    return f"Custom workout logged: {text[:80]}"


def log_ruck(state: dict, miles: float, pounds: float,
             today_str: str | None = None) -> str:
    state["ruck_log"].append({
        "date":           today_str or str(dt.date.today()),
        "distance_miles": miles,
        "weight_lbs":     pounds,
    })
    state["total_ruck_miles"] = state.get("total_ruck_miles", 0.0) + miles
    state["journey_miles"]    = state.get("journey_miles", 0.0) + miles
    _increment_weekly_count(state)
    return f"Ruck logged: {miles:.1f} mi @ {pounds:.0f} lbs"


def log_run(state: dict, miles: float, pace: float | None = None,
            today_str: str | None = None) -> str:
    entry: dict = {"date": today_str or str(dt.date.today()), "distance_miles": miles}
    if pace is not None:
        entry["pace_min_per_mile"] = pace
    state.setdefault("run_log", []).append(entry)
    state["total_run_miles"] = state.get("total_run_miles", 0.0) + miles
    state["journey_miles"]   = state.get("journey_miles", 0.0) + miles
    _increment_weekly_count(state)
    return f"Run logged: {miles:.1f} mi"


def log_walk(state: dict, miles: float,
             today_str: str | None = None) -> str:
    state.setdefault("walk_log", []).append({
        "date":           today_str or str(dt.date.today()),
        "distance_miles": miles,
    })
    state["total_walk_miles"] = state.get("total_walk_miles", 0.0) + miles
    state["journey_miles"]    = state.get("journey_miles", 0.0) + miles
    _increment_weekly_count(state)
    return f"Walk logged: {miles:.1f} mi"


def get_streak_info(state: dict) -> dict:
    today = dt.date.today()

    # Collect every activity date from all logs (unique calendar days per week)
    all_dates: list[dt.date] = []
    for w in state.get("workouts", []):
        try:
            all_dates.append(dt.date.fromisoformat(w["date"]))
        except (KeyError, ValueError, TypeError):
            pass
    for log_key in ("ruck_log", "run_log", "walk_log"):
        for entry in state.get(log_key, []):
            try:
                all_dates.append(dt.date.fromisoformat(entry["date"]))
            except (KeyError, ValueError, TypeError):
                pass

    # Group into ISO-week buckets → set of unique dates
    week_days: dict[str, set] = {}
    for d in all_dates:
        k = _week_key(d)
        week_days.setdefault(k, set()).add(d)

    curr_key  = _week_key(today)
    this_week = len(week_days.get(curr_key, set()))

    # Count consecutive fully-completed past weeks (current week excluded)
    streak_weeks = 0
    check = today - dt.timedelta(weeks=1)   # start from last week
    while True:
        k = _week_key(check)
        if len(week_days.get(k, set())) >= WK_TARGET:
            streak_weeks += 1
            check -= dt.timedelta(weeks=1)
        else:
            break
    # Current week contributes to this_week / activities_remaining only —
    # it is NOT added to streak_weeks until it becomes a past week.

    last_week_date = today - dt.timedelta(weeks=1)
    last_week_hit  = len(week_days.get(_week_key(last_week_date), set())) >= WK_TARGET
    days_remaining       = 7 - today.isoweekday()
    activities_remaining = max(0, WK_TARGET - this_week)

    return {
        "week_target":           WK_TARGET,
        "this_week":             this_week,
        "streak_weeks":          streak_weeks,
        "last_week_hit":         last_week_hit,
        "days_remaining":        days_remaining,
        "activities_remaining":  activities_remaining,
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
            day_type = w.get("day_type", "strength")
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
        state.pop("track", None)
    return True
