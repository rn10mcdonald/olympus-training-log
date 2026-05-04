"""
core.py — First Bell training logic
Pure Python, no I/O. Stateless functions that operate on state dicts.
"""

import datetime as dt
import time

# ── Training templates ────────────────────────────────────────────────────────

TEMPLATES = {

    # ══════════════════════════════════════════════════════════════════════════
    #  DAY A — GLUTE & LEGS
    #  Anchor: Hip Thrust. Extra focus: glutes, quads, hamstrings, lateral hip.
    #  Full body skeleton present every session.
    # ══════════════════════════════════════════════════════════════════════════
    "day_a_glute_legs": {
        "name":     "Day A — Glute & Legs",
        "day_type": "strength",
        "focus":    "Glutes, quads, hamstrings, lateral hip — full body with lower emphasis",
        "bell_guidance": (
            "Hip thrust: 16 kg wk1 → 20 kg wk2 → 24 kg wk3 → 12 kg wk4. "
            "Split squat: 12 kg wk1–2 → 16 kg wk3. "
            "Floor press / row: 12 kg. Swings: 16–20 kg."
        ),
        "sessions": [
            {   # ── Session 1 · Week 1 feel · Build ─────────────────────────
                "week_label": "Week 1 — Build the foundation",
                "main": "KB Hip Thrust 4×10 @ 16 kg",
                "std_kg": 16,
                "full_body_block": [
                    "KB Floor Press 3×10/side @ 12 kg  [PUSH]",
                    "KB Bent-Over Row 3×10/side @ 12 kg  [PULL]",
                    "Hanging Leg Raise 3×8 (or Lying Leg Raise)  [CORE]",
                ],
                "focus_work": [
                    "Bulgarian Split Squat 3×8/leg (bodyweight or 8 kg goblet)",
                    "Banded Clamshell 3×20/side",
                    "Lateral Band Walk 3×20 steps/side",
                ],
                "arms": [
                    "KB Hammer Curl 3×12 @ 8 kg",
                    "KB Tricep Kickback 3×12/side @ 8 kg",
                ],
                "finisher": (
                    "KB Swing 30 s on / 30 s off × 8 rounds @ 16 kg  "
                    "(~8 min — note how you feel at round 8)"
                ),
            },
            {   # ── Session 2 · Week 1 feel · Volume ────────────────────────
                "week_label": "Week 1 — Add volume, own the movement",
                "main": "Double KB Front Squat 4×8 @ 12 kg/bell",
                "std_kg": 12,
                "full_body_block": [
                    "KB Push Press 3×8/side @ 12 kg  [PUSH]",
                    "KB Renegade Row 3×6/side @ 12 kg  [PULL]",
                    "Ab Wheel Rollout 3×8 (or Dead Bug 3×10/side)  [CORE]",
                ],
                "focus_work": [
                    "KB Hip Thrust 3×12 @ 16 kg (speed reps — squeeze hard at top)",
                    "KB Reverse Lunge 3×10/leg @ 12 kg",
                    "KB Curtsy Lunge 3×10/side @ 8 kg",
                ],
                "arms": [
                    "KB Zottman Curl 3×10 @ 8 kg",
                    "KB Overhead Tricep Extension 3×12 @ 8 kg",
                ],
                "finisher": (
                    "Goblet Squat Pulse 20 s / KB Swing 40 s — alternating × 6 rounds @ 16 kg  "
                    "(~6 min — no rest between movements)"
                ),
            },
            {   # ── Session 3 · Week 2 feel · Develop ───────────────────────
                "week_label": "Week 2 — Increase load, maintain quality",
                "main": "KB Hip Thrust 4×8 @ 20 kg  (↑ from Session 1)",
                "std_kg": 20,
                "full_body_block": [
                    "KB Floor Press 4×8/side @ 12 kg  [PUSH — add a set]",
                    "KB Chest-Supported Row 4×10 @ 12 kg  [PULL]",
                    "Hanging Leg Raise 3×10  [CORE — 2 more reps]",
                ],
                "focus_work": [
                    "Bulgarian Split Squat 3×10/leg @ 12 kg  (↑ load and reps)",
                    "Single-Leg KB Hip Thrust 3×10/leg @ 12 kg",
                    "Banded Hip Abduction Standing 3×15/side",
                ],
                "arms": [
                    "KB Hammer Curl 3×12 @ 10 kg  (↑ load if available, else more reps)",
                    "KB Tricep Kickback 3×15/side @ 8 kg  (↑ reps)",
                ],
                "finisher": (
                    "KB Swing 30 s on / 20 s off × 10 rounds @ 16 kg  "
                    "(~8 min — shorter rest than S1, harder)"
                ),
            },
            {   # ── Session 4 · Week 2 feel · Volume push ───────────────────
                "week_label": "Week 2 — Push the volume ceiling",
                "main": "Double KB Front Squat 5×6 @ 16 kg/bell  (↑ load from S2)",
                "std_kg": 16,
                "full_body_block": [
                    "KB Push Press 4×6/side @ 12 kg  [PUSH — heavier, fewer reps]",
                    "KB Renegade Row 3×8/side @ 12 kg  [PULL — more reps]",
                    "Hollow Rock 3×20  [CORE]",
                ],
                "focus_work": [
                    "KB Hip Thrust 4×10 @ 20 kg (full squeeze, 1-s pause at top)",
                    "KB Lateral Lunge 3×10/side @ 12 kg",
                    "Banded Clamshell 3×25/side (more reps)",
                ],
                "arms": [
                    "KB Zottman Curl 3×12 @ 8 kg",
                    "KB Overhead Tricep Extension 3×15 @ 8 kg",
                ],
                "finisher": (
                    "Tabata KB Swings: 20 s on / 10 s off × 8 rounds @ 16 kg  "
                    "(4 min — all out, note total reps)"
                ),
            },
            {   # ── Session 5 · Week 3 feel · Overreach ─────────────────────
                "week_label": "Week 3 — New top weight, dig deep",
                "main": "KB Hip Thrust 5×6 @ 24 kg  (heaviest you've done — RPE 8–9)",
                "std_kg": 24,
                "full_body_block": [
                    "KB Floor Press 4×6/side @ 16 kg  [PUSH — heavy]",
                    "KB Bent-Over Row 4×6/side @ 16 kg  [PULL — heavy]",
                    "Hanging Leg Raise 4×10  [CORE — add a set]",
                ],
                "focus_work": [
                    "Rear-Foot-Elevated Split Squat 3×6/leg @ 16 kg  (heavy, slow eccentric)",
                    "Nordic Hamstring Curl 3×5 (eccentric only — lower as slow as possible)",
                    "Single-Leg Glute Bridge 3×12/leg @ 16 kg (loaded, pause at top)",
                ],
                "arms": [
                    "KB Hammer Curl 3×10 @ 12 kg  (↑ load)",
                    "KB Tricep Kickback 3×12/side @ 10 kg  (↑ load)",
                ],
                "finisher": (
                    "EMOM 10 min: odd minutes 10 KB Swings @ 20 kg, "
                    "even minutes 10 Goblet Squat Pulses @ 16 kg  "
                    "(power + burn — this is the hardest finisher in the cycle)"
                ),
            },
            {   # ── Session 6 · Week 4 · Deload ─────────────────────────────
                "week_label": "Week 4 — Deload: restore, don't grind",
                "main": "KB Hip Thrust 3×10 @ 12 kg  (light — perfect form, feel every rep)",
                "std_kg": 12,
                "full_body_block": [
                    "KB Floor Press 2×10/side @ 8 kg  [PUSH — easy]",
                    "KB Bent-Over Row 2×10/side @ 8 kg  [PULL — easy]",
                    "Dead Bug 3×10/side  [CORE — controlled breathing]",
                ],
                "focus_work": [
                    "Bodyweight Glute Bridge 3×20 (2-s squeeze at top)",
                    "Banded Clamshell 2×20/side",
                    "Hip Flexor Stretch 2×90 s/side + Pigeon Pose 2×90 s/side",
                ],
                "arms": [
                    "KB Hammer Curl 2×12 @ 8 kg  (easy — feel the muscle)",
                    "KB Overhead Tricep Extension 2×12 @ 8 kg",
                ],
                "finisher": (
                    "KB Swing 20 s on / 40 s off × 6 rounds @ 12 kg  "
                    "(light, technique focus — snap the hips, float the bell)"
                ),
            },
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    #  DAY B — PULL + CORE
    #  Anchor: Rows / Carries. Extra focus: rows, carries, direct abs, arms.
    #  Full body skeleton present every session.
    #  Pull-up progression built into every session.
    # ══════════════════════════════════════════════════════════════════════════
    "day_b_pull_core": {
        "name":     "Day B — Pull + Core",
        "day_type": "strength",
        "focus":    "Rows, carries, direct abs, arms — full body with upper pull emphasis",
        "bell_guidance": (
            "Rows: 12 kg wk1–2 → 16 kg wk3. "
            "Carries: 16–20 kg. "
            "Curls/triceps: 8–12 kg. "
            "Press: 12 kg."
        ),
        "sessions": [
            {   # ── Session 1 · Week 1 feel · Build ─────────────────────────
                "week_label": "Week 1 — Build the pull foundation",
                "main": "KB Bent-Over Row 4×10/side @ 12 kg",
                "std_kg": 12,
                "full_body_block": [
                    "KB Clean + Press 3×6/side @ 12 kg  [PUSH]",
                    "KB Hip Thrust 3×12 @ 16 kg  [LOWER — glute maintenance]",
                    "Hanging Leg Raise 3×8  [CORE]",
                ],
                "focus_work": [
                    "Farmer Carry 4×30 m @ 16 kg/hand  (walk tall, no lean)",
                    "TRX Face Pull 3×15 (or Rear-Delt Fly @ 8 kg)",
                    "Dead Hang 3×20 s  (pull-up foundation — grip and shoulder stability)",
                ],
                "arms": [
                    "KB Hammer Curl 3×12 @ 8 kg",
                    "KB Overhead Tricep Extension 3×12 @ 8 kg",
                ],
                "finisher": (
                    "KB Snatch 30 s on / 30 s off × 8 rounds @ 12 kg  "
                    "(alternate hands each round — note total reps)"
                ),
            },
            {   # ── Session 2 · Week 1 feel · Volume ────────────────────────
                "week_label": "Week 1 — Volume day, brace everything",
                "main": "KB Renegade Row 3×6/side @ 12 kg  (slow — 3-s per rep)",
                "std_kg": 12,
                "full_body_block": [
                    "KB Push Press 3×8/side @ 12 kg  [PUSH]",
                    "KB Goblet Squat 3×12 @ 16 kg  [LOWER]",
                    "Ab Wheel Rollout 3×8  [CORE]",
                ],
                "focus_work": [
                    "Suitcase Carry 4×20 m/side @ 16 kg  (resist the lean)",
                    "TRX Row 3×12 (or Chest-Supported Row @ 12 kg)",
                    "Pull-Up Negative 3×4  (jump to bar, 5-s controlled descent)",
                ],
                "arms": [
                    "KB Zottman Curl 3×10 @ 8 kg",
                    "KB Tricep Kickback 3×12/side @ 8 kg",
                ],
                "finisher": (
                    "Clean + Press AMRAP 5 min @ 12 kg  "
                    "(5 cleans + 5 presses/side, switch — note total rounds)"
                ),
            },
            {   # ── Session 3 · Week 2 feel · Develop ───────────────────────
                "week_label": "Week 2 — Heavier rows, more pull volume",
                "main": "KB Chest-Supported Row 4×10 @ 12–16 kg  (↑ from S1)",
                "std_kg": 14,
                "full_body_block": [
                    "KB Clean + Press 4×5/side @ 12 kg  [PUSH — add a set]",
                    "KB Hip Thrust 3×10 @ 20 kg  [LOWER — heavier]",
                    "Hollow Rock 3×20  [CORE]",
                ],
                "focus_work": [
                    "Rack Carry 3×30 m/side @ 12 kg  (forearm vertical, brace)",
                    "TRX Face Pull + Y-Raise superset 3×12 each",
                    "Pull-Up Negative 3×5  (5-s descent — one more rep than S2)",
                ],
                "arms": [
                    "KB Hammer Curl 3×12 @ 10 kg  (↑ load)",
                    "KB Overhead Tricep Extension 3×15 @ 8 kg  (↑ reps)",
                ],
                "finisher": (
                    "KB Snatch 40 s on / 20 s off × 8 rounds @ 12 kg  "
                    "(longer work interval — harder than S1)"
                ),
            },
            {   # ── Session 4 · Week 2 feel · Volume push ───────────────────
                "week_label": "Week 2 — Push the pull volume ceiling",
                "main": "KB Bent-Over Row 5×8/side @ 14–16 kg  (↑ load and sets)",
                "std_kg": 16,
                "full_body_block": [
                    "KB Push Press 4×6/side @ 12 kg  [PUSH]",
                    "KB Reverse Lunge 3×10/leg @ 12 kg  [LOWER]",
                    "Pallof Press 3×12/side  [CORE — anti-rotation]",
                ],
                "focus_work": [
                    "Overhead Carry 3×20 m/side @ 12 kg  (locked shoulder, eyes forward)",
                    "KB Renegade Row 3×8/side @ 12 kg  (↑ reps from S2)",
                    "Pull-Up Negative 3×5 @ 6-s descent  (slower = harder)",
                ],
                "arms": [
                    "KB Zottman Curl 3×12 @ 8 kg",
                    "KB Tricep Kickback 3×15/side @ 8 kg",
                ],
                "finisher": (
                    "3-Round Core + Cardio Circuit (no rest within rounds, 60 s between):\n"
                    "  10 Hanging Leg Raise → 15 Hollow Rock → "
                    "30 s KB Swing @ 16 kg → 20 s Side Plank/side"
                ),
            },
            {   # ── Session 5 · Week 3 feel · Overreach ─────────────────────
                "week_label": "Week 3 — Heaviest pull, dig in",
                "main": "KB Renegade Row 4×6/side @ 16 kg  (heaviest manageable — RPE 8–9)",
                "std_kg": 16,
                "full_body_block": [
                    "KB Floor Press 4×6/side @ 16 kg  [PUSH — heavy]",
                    "KB Hip Thrust 4×8 @ 24 kg  [LOWER — heavy]",
                    "Hanging Leg Raise 4×10  [CORE — add a set]",
                ],
                "focus_work": [
                    "Farmer Carry 5×30 m @ 20 kg/hand  (max load)",
                    "Pull-Up Negative 4×5 @ 6-s descent  (add a set)",
                    "Carry Medley: Rack 20 m → Overhead 20 m → Farmer 20 m (no put-down)",
                ],
                "arms": [
                    "KB Hammer Curl 3×10 @ 12 kg  (↑ load — challenging)",
                    "KB Overhead Tricep Extension 3×12 @ 10 kg  (↑ load)",
                ],
                "finisher": (
                    "KB Snatch EMOM 10 min: 8 reps @ 12 kg  "
                    "(switch hands each minute — 80 total snatches, note time to finish)"
                ),
            },
            {   # ── Session 6 · Week 4 · Deload ─────────────────────────────
                "week_label": "Week 4 — Deload: light, feel everything",
                "main": "KB Bent-Over Row 3×10/side @ 8 kg  (light — perfect hinge, squeeze)",
                "std_kg": 8,
                "full_body_block": [
                    "KB Clean + Press 2×8/side @ 8 kg  [PUSH — easy]",
                    "KB Goblet Squat 2×12 @ 12 kg  [LOWER]",
                    "Dead Bug 3×10/side  [CORE]",
                ],
                "focus_work": [
                    "Suitcase Carry 2×20 m/side @ 12 kg  (light)",
                    "Dead Hang 3×30 s  (longer hang than wk1 — progress)",
                    "Shoulder Mobility Flow: Arm Circles + Cross-Body Stretch 2×2 min",
                ],
                "arms": [
                    "KB Hammer Curl 2×12 @ 8 kg  (easy, slow eccentric)",
                    "KB Overhead Tricep Extension 2×12 @ 8 kg",
                ],
                "finisher": (
                    "KB Swing 20 s on / 40 s off × 6 rounds @ 12 kg  "
                    "(light and technical — this is active recovery)"
                ),
            },
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    #  DAY C — HARDSTYLE FULL BODY
    #  Anchor: Swings / Snatches / Clean+Press. This is the conditioning day.
    #  Still full body — push, pull, lower, core, arms present.
    #  Cardio finisher is the hardest of the week.
    # ══════════════════════════════════════════════════════════════════════════
    "day_c_hardstyle": {
        "name":     "Day C — Hardstyle Full Body",
        "day_type": "strength",
        "focus":    "Swings, cleans, snatches — power + conditioning, full body",
        "bell_guidance": (
            "Swings: 16 kg wk1 → 20 kg wk3. "
            "Clean+Press: 12 kg. "
            "Snatch: 12 kg. "
            "Goblet: 16 kg. "
            "Arms: 8 kg."
        ),
        "sessions": [
            {   # ── Session 1 · Week 1 feel · Build ─────────────────────────
                "week_label": "Week 1 — Swing foundation, build the engine",
                "main": "KB Swing EMOM 15 min: 12 reps/min @ 16 kg",
                "std_kg": 16,
                "full_body_block": [
                    "KB Clean + Press 3×5/side @ 12 kg  [PUSH + full body]",
                    "KB Goblet Squat 3×10 @ 16 kg  [LOWER]",
                    "Push-Up 3×10  [PUSH — bodyweight]",
                    "Hollow Rock 3×15  [CORE]",
                ],
                "focus_work": [
                    "KB High Pull 3×8/side @ 12 kg  (swing → explosive pull — shoulder health)",
                    "KB Hip Thrust 3×10 @ 16 kg  (glute maintenance on hardstyle day)",
                ],
                "arms": [
                    "KB Hammer Curl 3×10 @ 8 kg",
                    "KB Tricep Kickback 3×10/side @ 8 kg",
                ],
                "finisher": (
                    "100 KB Swings for time @ 16 kg  "
                    "(note your time — this is your benchmark for the cycle)"
                ),
            },
            {   # ── Session 2 · Week 1 feel · Clean+Press day ───────────────
                "week_label": "Week 1 — Clean + Press ladders, classic hardstyle",
                "main": "KB Clean + Press Ladder (1-2-3/side) × 4 @ 12 kg",
                "std_kg": 12,
                "full_body_block": [
                    "KB Swing 5×12 @ 16 kg  [HINGE + power]",
                    "KB Goblet Squat 3×12 @ 16 kg  [LOWER]",
                    "KB Renegade Row 3×5/side @ 12 kg  [PULL]",
                    "Dead Bug 3×10/side  [CORE]",
                ],
                "focus_work": [
                    "KB Hip Thrust 3×12 @ 16 kg  (glute maintenance)",
                    "KB Single-Arm Swing 3×10/side @ 16 kg  (anti-rotation challenge)",
                ],
                "arms": [
                    "KB Zottman Curl 3×10 @ 8 kg",
                    "KB Overhead Tricep Extension 3×10 @ 8 kg",
                ],
                "finisher": (
                    "5 Cleans + 5 Presses + 5 Front Squats/side × 4 rounds @ 12 kg  "
                    "(no rest between sides — rest 60 s between rounds)"
                ),
            },
            {   # ── Session 3 · Week 2 feel · Develop ───────────────────────
                "week_label": "Week 2 — More swings, faster pace",
                "main": "KB Swing EMOM 20 min: 15 reps/min @ 16 kg  (↑ reps/min and duration)",
                "std_kg": 16,
                "full_body_block": [
                    "KB Clean + Push Press 3×5/side @ 12 kg  [PUSH — push press harder than press]",
                    "KB Goblet Squat 4×10 @ 16 kg  [LOWER — add a set]",
                    "Push-Up 3×12  [PUSH — more reps]",
                    "Pallof Press 3×10/side  [CORE — anti-rotation]",
                ],
                "focus_work": [
                    "KB High Pull 3×10/side @ 12 kg  (↑ reps)",
                    "KB Hip Thrust 4×10 @ 20 kg  (↑ load on hardstyle day)",
                ],
                "arms": [
                    "KB Hammer Curl 3×12 @ 8 kg  (↑ reps)",
                    "KB Tricep Kickback 3×12/side @ 8 kg",
                ],
                "finisher": (
                    "Swing Tabata: 20 s on / 10 s off × 8 rounds @ 16 kg  "
                    "(4 min — maximum effort, note total swing count)"
                ),
            },
            {   # ── Session 4 · Week 2 feel · Snatch day ────────────────────
                "week_label": "Week 2 — Snatch intervals, the queen of KB movements",
                "main": "KB Snatch Intervals: 8 × 1 min @ 12 kg  (max reps, switch hand each set)",
                "std_kg": 12,
                "full_body_block": [
                    "KB Clean + Press 3×6/side @ 12 kg  [PUSH]",
                    "KB Goblet Squat 3×12 @ 16 kg  [LOWER]",
                    "KB Bent-Over Row 3×8/side @ 12 kg  [PULL]",
                    "Hollow Rock 3×20  [CORE]",
                ],
                "focus_work": [
                    "KB Half Snatch 3×8/side @ 12 kg  (snatch up, clean down — builds the pull)",
                    "KB Hip Thrust 3×12 @ 20 kg  (glute maintenance)",
                ],
                "arms": [
                    "KB Zottman Curl 3×10 @ 8 kg",
                    "KB Overhead Tricep Extension 3×12 @ 8 kg",
                ],
                "finisher": (
                    "Long Cycle Clean + Jerk 2 × 5 min @ 12 kg  "
                    "(switch hands each minute — rest 2 min between sets)"
                ),
            },
            {   # ── Session 5 · Week 3 feel · Overreach ─────────────────────
                "week_label": "Week 3 — Heavy swings + press, peak conditioning",
                "main": "Double KB Swing 10×5 EMOM @ 20 kg/bell  (heaviest pair — RPE 8–9)",
                "std_kg": 20,
                "full_body_block": [
                    "KB Clean + Push Press 4×5/side @ 12 kg  [PUSH — heavy]",
                    "Double KB Front Squat 3×6 @ 16 kg/bell  [LOWER — heavy]",
                    "Push-Up 3×15  [PUSH — higher reps for endurance]",
                    "Hanging Leg Raise 3×10  [CORE]",
                ],
                "focus_work": [
                    "KB Snatch 5×5/side @ 12 kg  (heavy for snatch — note any grind)",
                    "KB Hip Thrust 4×8 @ 24 kg  (heaviest glute work of the week)",
                ],
                "arms": [
                    "KB Hammer Curl 3×10 @ 12 kg  (↑ load)",
                    "KB Overhead Tricep Extension 3×10 @ 10 kg  (↑ load)",
                ],
                "finisher": (
                    "200 KB Swings @ 16 kg — every time you put the bell down, 5 Push-Ups penalty  "
                    "(note your time and how many breaks you took)"
                ),
            },
            {   # ── Session 6 · Week 4 · Deload ─────────────────────────────
                "week_label": "Week 4 — Deload: flow and feel",
                "main": "KB Swing 5×10 @ 12 kg  (light — focus on hip snap, float the bell)",
                "std_kg": 12,
                "full_body_block": [
                    "KB Clean + Press 2×5/side @ 8 kg  [PUSH — easy]",
                    "KB Goblet Squat 2×10 @ 12 kg  [LOWER]",
                    "Push-Up 2×8  [PUSH]",
                    "Dead Bug 3×10/side  [CORE]",
                ],
                "focus_work": [
                    "KB TGU 2×1/side @ 8 kg  (very light — movement quality only)",
                    "Hip Flexor Stretch 2×90 s/side",
                ],
                "arms": [
                    "KB Hammer Curl 2×12 @ 8 kg  (easy, slow)",
                    "KB Overhead Tricep Extension 2×12 @ 8 kg",
                ],
                "finisher": (
                    "10 min flow: 5 Swings → 1 Goblet Squat → 5 Halos/side — "
                    "repeat continuously @ 12 kg  (movement meditation, no rush)"
                ),
            },
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    #  DAY D — DOUBLE KB STRENGTH
    #  Anchor: Heavy double KB compounds. Builds raw strength base.
    #  Full body skeleton always present.
    #  Optional 4th training day — do if you have energy, skip if not.
    # ══════════════════════════════════════════════════════════════════════════
    "day_d_double_kb": {
        "name":     "Day D — Double KB Strength",
        "day_type": "strength",
        "focus":    "Heavy double KB compounds — strength base, full body",
        "bell_guidance": (
            "Double deadlift: 16 kg/bell wk1 → 20 kg wk2 → 24 kg wk3. "
            "Double front squat: 12 kg/bell wk1 → 16 kg wk2–3. "
            "Double clean: 12 kg/bell. "
            "Press: 12 kg. Arms: 8–10 kg."
        ),
        "sessions": [
            {   # ── Session 1 · Week 1 feel · Build ─────────────────────────
                "week_label": "Week 1 — Double KB introduction",
                "main": "Double KB Deadlift 5×5 @ 16 kg/bell",
                "std_kg": 16,
                "full_body_block": [
                    "KB Clean + Press 3×5/side @ 12 kg  [PUSH]",
                    "Double KB Front Squat 3×6 @ 12 kg/bell  [LOWER]",
                    "Push-Up 3×12  [PUSH — bodyweight]",
                    "Hanging Leg Raise 3×8  [CORE]",
                ],
                "focus_work": [
                    "KB Single-Leg RDL 3×8/side @ 12 kg  (hinge quality work)",
                    "KB Hip Thrust 3×12 @ 16 kg  (glute maintenance)",
                    "KB Suitcase Carry 3×20 m/side @ 16 kg",
                ],
                "arms": [
                    "KB Hammer Curl 3×12 @ 8 kg",
                    "KB Tricep Kickback 3×12/side @ 8 kg",
                ],
                "finisher": (
                    "5 Double KB Deadlifts + 5 Double KB Cleans × 4 rounds @ 12 kg/bell  "
                    "(rest 90 s between rounds)"
                ),
            },
            {   # ── Session 2 · Week 1 feel · Squat focus ───────────────────
                "week_label": "Week 1 — Front squat focus",
                "main": "Double KB Front Squat 4×6 @ 12 kg/bell",
                "std_kg": 12,
                "full_body_block": [
                    "KB Push Press 3×6/side @ 12 kg  [PUSH]",
                    "Double KB Deadlift 3×5 @ 16 kg/bell  [HINGE]",
                    "KB Bent-Over Row 3×8/side @ 12 kg  [PULL]",
                    "Ab Wheel Rollout 3×8  [CORE]",
                ],
                "focus_work": [
                    "KB Hip Thrust 3×12 @ 20 kg  (heavier glute work)",
                    "Nordic Hamstring Curl 3×5 (eccentric — lower as slow as possible)",
                    "Farmer Carry 4×30 m @ 20 kg/hand",
                ],
                "arms": [
                    "KB Zottman Curl 3×10 @ 8 kg",
                    "KB Overhead Tricep Extension 3×12 @ 8 kg",
                ],
                "finisher": (
                    "Double KB Front Squat 3 reps EMOM × 8 min @ 12 kg/bell  "
                    "(24 total reps — note if any got ugly)"
                ),
            },
            {   # ── Session 3 · Week 2 feel · Develop deadlift ──────────────
                "week_label": "Week 2 — Load the deadlift",
                "main": "Double KB Deadlift 5×4 @ 20 kg/bell  (↑ load)",
                "std_kg": 20,
                "full_body_block": [
                    "KB Clean + Press 4×5/side @ 12 kg  [PUSH]",
                    "Double KB Front Squat 4×5 @ 16 kg/bell  [LOWER — heavier]",
                    "Push-Up 3×15  [PUSH — more reps]",
                    "Hollow Rock 3×20  [CORE]",
                ],
                "focus_work": [
                    "KB Single-Leg RDL 3×8/side @ 16 kg  (↑ load)",
                    "KB Hip Thrust 4×8 @ 24 kg  (heaviest hip thrust of D days)",
                    "Suitcase Carry 4×20 m/side @ 16 kg",
                ],
                "arms": [
                    "KB Hammer Curl 3×12 @ 10 kg  (↑ load)",
                    "KB Tricep Kickback 3×12/side @ 10 kg",
                ],
                "finisher": (
                    "Heavy Complex × 4 rounds (rest 90 s):\n"
                    "  3 Double KB Deadlifts + 3 Double KB Cleans + 3 Double KB Presses @ 12 kg/bell"
                ),
            },
            {   # ── Session 4 · Week 2 feel · Squat volume ──────────────────
                "week_label": "Week 2 — Squat volume, push the ceiling",
                "main": "Double KB Front Squat 5×5 @ 16 kg/bell  (↑ load from S2)",
                "std_kg": 16,
                "full_body_block": [
                    "KB Push Press 4×6/side @ 12 kg  [PUSH]",
                    "Double KB Deadlift 4×4 @ 20 kg/bell  [HINGE — heavy]",
                    "KB Renegade Row 3×6/side @ 12 kg  [PULL]",
                    "Pallof Press 3×10/side  [CORE]",
                ],
                "focus_work": [
                    "KB Hip Thrust 4×10 @ 20 kg",
                    "Nordic Hamstring Curl 3×5 (eccentric)",
                    "Overhead Carry 3×20 m/side @ 12 kg",
                ],
                "arms": [
                    "KB Zottman Curl 3×12 @ 8 kg",
                    "KB Overhead Tricep Extension 3×15 @ 8 kg",
                ],
                "finisher": (
                    "Double KB Front Squat: 1 rep every 30 s × 10 min @ 12 kg/bell  "
                    "(20 total reps — stay sharp every single one)"
                ),
            },
            {   # ── Session 5 · Week 3 feel · Overreach ─────────────────────
                "week_label": "Week 3 — Near-maximal, earn it",
                "main": "Double KB Deadlift 6×3 @ 24 kg/bell  (near-max — RPE 9)",
                "std_kg": 24,
                "full_body_block": [
                    "KB Floor Press 4×6/side @ 16 kg  [PUSH — heavy]",
                    "Double KB Front Squat 4×3 @ 20 kg/bell  [LOWER — 2-s pause at bottom]",
                    "Push-Up 3×15  [PUSH]",
                    "Hanging Leg Raise 4×10  [CORE]",
                ],
                "focus_work": [
                    "Rear-Foot-Elevated Split Squat 3×5/leg @ 16 kg  (heavy, slow eccentric)",
                    "Farmer Carry 5×30 m @ 20 kg/hand  (max load)",
                    "KB Hip Thrust 4×6 @ 24 kg  (heavy)",
                ],
                "arms": [
                    "KB Hammer Curl 3×10 @ 12 kg  (↑ load)",
                    "KB Overhead Tricep Extension 3×10 @ 10 kg  (↑ load)",
                ],
                "finisher": (
                    "Max Double KB Deadlifts in 3 min @ 20 kg/bell  "
                    "(note your number — this is a benchmark)"
                ),
            },
            {   # ── Session 6 · Week 4 · Deload ─────────────────────────────
                "week_label": "Week 4 — Deload: light and mobile",
                "main": "Double KB Deadlift 3×5 @ 12 kg/bell  (light — perfect tension)",
                "std_kg": 12,
                "full_body_block": [
                    "KB Clean + Press 2×6/side @ 8 kg  [PUSH — easy]",
                    "Double KB Front Squat 2×8 @ 12 kg/bell  [LOWER — light]",
                    "Push-Up 2×10  [PUSH]",
                    "Dead Bug 3×10/side  [CORE]",
                ],
                "focus_work": [
                    "Single-Leg RDL 2×8/side @ 8 kg  (bodyweight or very light)",
                    "Hip Flexor Mobilization 2×90 s/side",
                    "Thoracic Rotation + Rib Grab 2×10/side",
                ],
                "arms": [
                    "KB Hammer Curl 2×12 @ 8 kg  (easy)",
                    "KB Overhead Tricep Extension 2×12 @ 8 kg",
                ],
                "finisher": (
                    "Hip mobility flow 10 min:\n"
                    "  90/90 Hip Switch × 10 → World's Greatest Stretch × 5/side → "
                    "Pigeon Pose 90 s/side → Cat-Cow × 10"
                ),
            },
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    #  MOBILITY — FLOW & RESTORE
    #  TGU anchor. Hip/thoracic mobility. Low CNS cost.
    #  Counts toward weekly streak. Not a rest day — active restoration.
    #  3 session variants rotate. ~25–30 min total.
    #  NO heavy loading. GO LIGHTER THAN YOU THINK.
    # ══════════════════════════════════════════════════════════════════════════
    "mobility_flow": {
        "name":     "Mobility — Flow & Restore",
        "day_type": "mobility",
        "focus":    "TGU, windmill, hip + thoracic mobility — active restoration",
        "bell_guidance": (
            "TGU: 8 kg only. Windmill: 8–12 kg. "
            "Everything else: bodyweight or 8 kg. "
            "Lighter than you think. Quality over load."
        ),
        "sessions": [
            {   # ── Mobility Session 1 · Standard ────────────────────────────
                "week_label": "Standard mobility — foundation",
                "main": "Turkish Get-Up 3×3/side @ 8 kg  (slow — full pause at each position)",
                "std_kg": 8,
                "full_body_block": [
                    "KB Windmill 3×5/side @ 8 kg  [shoulder + lateral chain]",
                    "KB Arm Bar 2×60 s/side @ 8 kg  [shoulder external rotation]",
                    "Dead Bug 3×10/side  [core — breathing focus]",
                ],
                "focus_work": [
                    "Hip Flexor Stretch 2×90 s/side (couch stretch or kneeling)",
                    "Thoracic Rotation + Rib Grab 2×10/side",
                    "Pigeon Pose 2×90 s/side",
                ],
                "arms": [
                    "KB Bottoms-Up Press 3×5/side @ 8 kg  (shoulder stability — very controlled)",
                ],
                "finisher": (
                    "10 min flow (continuous, no rushing):\n"
                    "  Cat-Cow × 10 → World's Greatest Stretch × 5/side → "
                    "90/90 Hip Switch × 10 → Child's Pose 60 s"
                ),
            },
            {   # ── Mobility Session 2 · TGU Ladder ──────────────────────────
                "week_label": "TGU ladder — build the skill",
                "main": "TGU Ladder (1-2-3-2-1/side) × 2 @ 8 kg  (rest fully between sides)",
                "std_kg": 8,
                "full_body_block": [
                    "KB Windmill 3×6/side @ 10 kg  (slightly heavier than S1)",
                    "KB Bottoms-Up Press 3×5/side @ 8 kg  [shoulder stability]",
                    "Hollow Body Hold 3×20 s  [core]",
                ],
                "focus_work": [
                    "Hip Flexor + Quad Stretch 2×2 min/side",
                    "Banded Hip Distraction 2×90 s/side (if band available)",
                    "Seated Thoracic Extension over foam roller 2×60 s",
                ],
                "arms": [
                    "KB Arm Bar 2×60 s/side @ 8 kg",
                ],
                "finisher": (
                    "TGU AMRAP 6 min @ 8 kg (alternating sides — note total reps)\n"
                    "  Goal: smooth, no rushing, every position deliberate"
                ),
            },
            {   # ── Mobility Session 3 · Windmill + Bent Press ───────────────
                "week_label": "Windmill + bent press — lateral chain",
                "main": "KB Windmill 4×5/side @ 12 kg + Bent Press 3×3/side @ 12 kg",
                "std_kg": 12,
                "full_body_block": [
                    "KB TGU 2×2/side @ 8 kg  (heavy for mobility day — focus on smooth)",
                    "KB Arm Bar 2×60 s/side @ 8 kg",
                    "Dead Bug 3×10/side  [core — exhale as limbs extend]",
                ],
                "focus_work": [
                    "Pigeon Pose 2×2 min/side",
                    "World's Greatest Stretch 2×5/side",
                    "Thoracic Rotation — hands behind head 2×10/side",
                ],
                "arms": [
                    "KB Bottoms-Up Press 3×5/side @ 8 kg",
                ],
                "finisher": (
                    "5 min flow — no rest:\n"
                    "  5 Windmills/side → 1 TGU/side → 5 Halos/side @ 8 kg\n"
                    "  Repeat until time is up — this is moving meditation"
                ),
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
        "full_body_block":  sess.get("full_body_block", []),
        "focus_work":       sess.get("focus_work", []),
        "arms":             sess.get("arms", []),
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
