"""
core.py — First Bell training logic
Pure Python, no I/O. Stateless functions that operate on state dicts.
"""

import datetime as dt
import re
import time

# ── 12-Week Program Data ──────────────────────────────────────────────────────

PROGRAM_1 = {
    "name":        "Program 1 — Foundation",
    "subtitle":    "Learn the patterns. Build the engine.",
    "weeks":       4,

    "strength_a": {
        "name":  "Strength A — Glute & Legs",
        "focus": "Glutes, quads, hamstrings, lateral hip — full body",
        "weeks": {
            1: {
                "label": "Week 1 — Learn the hip thrust. Feel every rep.",
                "main":  "Two-Hand KB Hip Thrust 4×10 @ 16 kg  (2-s squeeze at top, feet flat)",
                "full_body": [
                    "Single-KB Floor Press 3×10/side @ 12 kg  [PUSH]",
                    "Single-KB Bent-Over Row 3×10/side @ 12 kg  [PULL]",
                    "Dead Bug 3×10/side  [CORE — exhale as limbs extend]",
                ],
                "focus": [
                    "Single-KB Reverse Lunge 3×10/leg @ 12 kg  (step back, both knees 90°)",
                    "Banded Clamshell 3×20/side  (rotate from hip, not waist)",
                    "Lateral Band Walk 3×20 steps/side  (mini-squat position)",
                ],
                "arms": [
                    "KB Hammer Curl 3×12 @ 8 kg  (neutral grip, no swing)",
                    "KB Tricep Kickback 3×12/side @ 8 kg  (upper arm parallel to floor)",
                ],
                "finisher": (
                    "Two-Hand KB Swing 30 s on / 30 s off × 8 rounds @ 16 kg  (~8 min)\n"
                    "Note how you feel at round 8 — this is your baseline."
                ),
            },
            2: {
                "label": "Week 2 — Same load, more volume. You're stronger than you think.",
                "main":  "Two-Hand KB Hip Thrust 5×10 @ 16 kg  (add a set — 50 total reps)",
                "full_body": [
                    "Single-KB Floor Press 4×10/side @ 12 kg  [PUSH — add a set]",
                    "Single-KB Bent-Over Row 4×10/side @ 12 kg  [PULL — add a set]",
                    "Dead Bug 3×12/side  [CORE — 2 more reps]",
                ],
                "focus": [
                    "Single-KB Reverse Lunge 4×10/leg @ 12 kg  (add a set)",
                    "Banded Clamshell 3×25/side  (more reps, same band)",
                    "Lateral Band Walk 3×25 steps/side",
                ],
                "arms": [
                    "KB Hammer Curl 3×15 @ 8 kg  (3 more reps — feel the burn)",
                    "KB Tricep Kickback 3×15/side @ 8 kg",
                ],
                "finisher": (
                    "Two-Hand KB Swing 30 s on / 25 s off × 9 rounds @ 16 kg  (~8 min)\n"
                    "Shorter rest than week 1. Harder."
                ),
            },
            3: {
                "label": "Week 3 — Up one bell. This is where strength happens.",
                "main":  "Two-Hand KB Hip Thrust 4×8 @ 20 kg  (heavier — RPE 8, earn every rep)",
                "full_body": [
                    "Single-KB Floor Press 4×8/side @ 16 kg  [PUSH — heavier]",
                    "Single-KB Bent-Over Row 4×8/side @ 16 kg  [PULL — heavier]",
                    "Dead Bug 4×10/side  [CORE — add a set]",
                ],
                "focus": [
                    "Single-KB Reverse Lunge 3×8/leg @ 16 kg  (heavier, slower eccentric 3 s down)",
                    "Banded Clamshell 3×20/side (heavier band if available)",
                    "Lateral Band Walk 3×20 steps/side (heavier band)",
                ],
                "arms": [
                    "KB Hammer Curl 3×10 @ 12 kg  (up one bell — challenging)",
                    "KB Tricep Kickback 3×10/side @ 12 kg",
                ],
                "finisher": (
                    "Two-Hand KB Swing 20 s on / 20 s off × 10 rounds @ 20 kg  (~7 min)\n"
                    "Heavier bell, same rest. Note if grip fails first."
                ),
            },
            4: {
                "label": "Week 4 — Deload. This week makes you stronger. Don't skip it.",
                "main":  "Two-Hand KB Hip Thrust 3×10 @ 12 kg  (light — feel every muscle fiber)",
                "full_body": [
                    "Single-KB Floor Press 2×10/side @ 8 kg  [PUSH — very easy]",
                    "Single-KB Bent-Over Row 2×10/side @ 8 kg  [PULL — very easy]",
                    "Dead Bug 2×10/side  [CORE — slow breathing]",
                ],
                "focus": [
                    "Single-KB Reverse Lunge 2×10/leg @ 8 kg  (bodyweight almost — form focus)",
                    "Banded Clamshell 2×20/side  (light band)",
                    "Hip Flexor Stretch 2×90 s/side + Pigeon Pose 2×90 s/side",
                ],
                "arms": [
                    "KB Hammer Curl 2×12 @ 8 kg  (easy, slow 3-s eccentric)",
                    "KB Tricep Kickback 2×12/side @ 8 kg",
                ],
                "finisher": (
                    "Two-Hand KB Swing 20 s on / 40 s off × 6 rounds @ 12 kg  (~6 min)\n"
                    "Light and technical. Float the bell. This is active recovery."
                ),
            },
        },
    },

    "strength_b": {
        "name":  "Strength B — Pull + Core + Arms",
        "focus": "Rows, carries, direct abs, biceps, triceps — full body",
        "weeks": {
            1: {
                "label": "Week 1 — Build the pull foundation. Brace everything.",
                "main":  "Single-KB Bent-Over Row 4×10/side @ 12 kg  (hinge like a deadlift, pull elbow past ribcage)",
                "full_body": [
                    "Single-KB Clean + Press 3×6/side @ 12 kg  [PUSH + lower body]",
                    "Two-Hand KB Goblet Squat 3×12 @ 16 kg  [LOWER]",
                    "Hanging Leg Raise 3×8  [CORE — no swing, tuck pelvis]",
                ],
                "focus": [
                    "Farmer Carry 4×30 m @ 16 kg/hand  (shoulders packed, walk tall)",
                    "TRX Face Pull 3×15  (or Rear-Delt Fly @ 8 kg — retract scapula)",
                    "Dead Hang 3×20 s  (pull-up foundation — grip + shoulder stability)",
                ],
                "arms": [
                    "KB Hammer Curl 3×12 @ 8 kg",
                    "KB Overhead Tricep Extension 3×12 @ 8 kg  (elbows close, full stretch)",
                ],
                "finisher": (
                    "Single-KB Snatch 30 s on / 30 s off × 8 rounds @ 12 kg  (~8 min)\n"
                    "Alternate hands each round. Note total reps."
                ),
            },
            2: {
                "label": "Week 2 — More volume on the pull. Carries are cardio too.",
                "main":  "Single-KB Bent-Over Row 5×10/side @ 12 kg  (add a set)",
                "full_body": [
                    "Single-KB Clean + Press 4×6/side @ 12 kg  [PUSH — add a set]",
                    "Two-Hand KB Goblet Squat 4×12 @ 16 kg  [LOWER — add a set]",
                    "Hanging Leg Raise 3×10  [CORE — 2 more reps]",
                ],
                "focus": [
                    "Farmer Carry 5×30 m @ 16 kg/hand  (add a set)",
                    "TRX Face Pull 3×20  (more reps)",
                    "Dead Hang 3×25 s  (5 more seconds — grip is adapting)",
                ],
                "arms": [
                    "KB Hammer Curl 4×12 @ 8 kg  (add a set)",
                    "KB Overhead Tricep Extension 4×12 @ 8 kg",
                ],
                "finisher": (
                    "Single-KB Snatch 40 s on / 20 s off × 8 rounds @ 12 kg  (~8 min)\n"
                    "Longer work interval. Same bell. Harder."
                ),
            },
            3: {
                "label": "Week 3 — Heavy rows. This is where your back gets built.",
                "main":  "Single-KB Bent-Over Row 4×8/side @ 16 kg  (heavier — RPE 8)",
                "full_body": [
                    "Single-KB Clean + Press 4×5/side @ 16 kg  [PUSH — heavier]",
                    "Two-Hand KB Goblet Squat 4×10 @ 20 kg  [LOWER — heavier]",
                    "Hanging Leg Raise 4×10  [CORE — add a set]",
                ],
                "focus": [
                    "Farmer Carry 4×40 m @ 20 kg/hand  (heavier, longer)",
                    "TRX Face Pull 3×15 (heavier angle — more horizontal)",
                    "Dead Hang 4×25 s  (add a set — grip endurance)",
                ],
                "arms": [
                    "KB Hammer Curl 3×10 @ 12 kg  (up one bell)",
                    "KB Overhead Tricep Extension 3×10 @ 12 kg",
                ],
                "finisher": (
                    "Single-KB Snatch EMOM 10 min: 8 reps @ 12 kg  (~10 min)\n"
                    "Switch hands each minute. 80 total snatches. Note if form breaks."
                ),
            },
            4: {
                "label": "Week 4 — Deload. Light rows, long hangs, breathe.",
                "main":  "Single-KB Bent-Over Row 3×8/side @ 8 kg  (light — perfect hinge)",
                "full_body": [
                    "Single-KB Clean + Press 2×6/side @ 8 kg  [PUSH — easy]",
                    "Two-Hand KB Goblet Squat 2×12 @ 12 kg  [LOWER]",
                    "Dead Bug 3×10/side  [CORE — switch from leg raise]",
                ],
                "focus": [
                    "Farmer Carry 2×30 m @ 12 kg/hand  (light)",
                    "Rear-Delt Fly 2×15 @ 8 kg  (easy, feel the scapula move)",
                    "Dead Hang 3×30 s  (longest hang yet — you're gripping less anxiously now)",
                ],
                "arms": [
                    "KB Hammer Curl 2×12 @ 8 kg  (slow 4-s eccentric)",
                    "KB Overhead Tricep Extension 2×12 @ 8 kg",
                ],
                "finisher": (
                    "Clean + Press Flow 10 min @ 8 kg  (no timer, no pressure)\n"
                    "5 cleans + 5 presses/side, switch, repeat. Moving meditation."
                ),
            },
        },
    },

    "strength_c": {
        "name":  "Strength C — Hardstyle Full Body",
        "focus": "Power, conditioning, full body — the engine session",
        "weeks": {
            1: {
                "label": "Week 1 — Build the swing. This is your cardio and your power.",
                "main":  "Two-Hand KB Swing EMOM 15 min: 12 reps/min @ 16 kg  (180 total swings)",
                "full_body": [
                    "Single-KB Clean + Press 3×5/side @ 12 kg  [PUSH + full body]",
                    "Two-Hand KB Goblet Squat 3×10 @ 16 kg  [LOWER]",
                    "Push-Up 3×10  [PUSH — bodyweight, chest to floor]",
                    "Hollow Rock 3×15  [CORE]",
                ],
                "focus": [
                    "Two-Hand KB Hip Thrust 3×12 @ 16 kg  (glute maintenance on power day)",
                    "Single-KB Reverse Lunge 2×10/leg @ 12 kg  (leg volume)",
                ],
                "arms": [
                    "KB Hammer Curl 3×10 @ 8 kg",
                    "KB Tricep Kickback 3×10/side @ 8 kg",
                ],
                "finisher": (
                    "100 Two-Hand KB Swings for time @ 16 kg\n"
                    "This is your benchmark. Write down your time."
                ),
            },
            2: {
                "label": "Week 2 — More swings, less rest. The engine grows.",
                "main":  "Two-Hand KB Swing EMOM 20 min: 12 reps/min @ 16 kg  (240 total swings)",
                "full_body": [
                    "Single-KB Clean + Press 4×5/side @ 12 kg  [PUSH — add a set]",
                    "Two-Hand KB Goblet Squat 4×10 @ 16 kg  [LOWER — add a set]",
                    "Push-Up 3×12  [PUSH — 2 more reps]",
                    "Hollow Rock 3×20  [CORE — more reps]",
                ],
                "focus": [
                    "Two-Hand KB Hip Thrust 4×12 @ 16 kg  (add a set)",
                    "Single-KB Reverse Lunge 3×10/leg @ 12 kg  (add a set)",
                ],
                "arms": [
                    "KB Hammer Curl 3×12 @ 8 kg",
                    "KB Tricep Kickback 3×12/side @ 8 kg",
                ],
                "finisher": (
                    "Swing Tabata: 20 s on / 10 s off × 8 rounds @ 16 kg  (4 min)\n"
                    "Then: 50 more swings for time. Compare to week 1 benchmark."
                ),
            },
            3: {
                "label": "Week 3 — Heavier bell. This is peak power week.",
                "main":  "Two-Hand KB Swing EMOM 20 min: 10 reps/min @ 20 kg  (200 swings, heavier)",
                "full_body": [
                    "Single-KB Clean + Press 4×5/side @ 16 kg  [PUSH — heavier]",
                    "Two-Hand KB Goblet Squat 4×8 @ 20 kg  [LOWER — heavier]",
                    "Push-Up 4×12  [PUSH — add a set]",
                    "Hollow Rock 4×20  [CORE — add a set]",
                ],
                "focus": [
                    "Two-Hand KB Hip Thrust 4×10 @ 20 kg  (heavier)",
                    "Single-KB Reverse Lunge 3×8/leg @ 16 kg  (heavier, slower)",
                ],
                "arms": [
                    "KB Hammer Curl 3×10 @ 12 kg  (up one bell)",
                    "KB Tricep Kickback 3×10/side @ 12 kg",
                ],
                "finisher": (
                    "200 Two-Hand KB Swings @ 16 kg — every time you set it down: 5 push-ups penalty\n"
                    "Note your time and how many breaks. This is a benchmark."
                ),
            },
            4: {
                "label": "Week 4 — Deload. Light swings, feel the hip snap.",
                "main":  "Two-Hand KB Swing 5×10 @ 12 kg  (light — technique only, float the bell)",
                "full_body": [
                    "Single-KB Clean + Press 2×5/side @ 8 kg  [PUSH — easy]",
                    "Two-Hand KB Goblet Squat 2×10 @ 12 kg  [LOWER]",
                    "Push-Up 2×8  [PUSH]",
                    "Dead Bug 3×10/side  [CORE — switch from hollow rock]",
                ],
                "focus": [
                    "Two-Hand KB Hip Thrust 3×10 @ 12 kg  (light, 2-s pause at top)",
                    "Hip Flexor Stretch 2×90 s/side",
                ],
                "arms": [
                    "KB Hammer Curl 2×12 @ 8 kg",
                    "KB Tricep Kickback 2×12/side @ 8 kg",
                ],
                "finisher": (
                    "10 min flow @ 12 kg: 5 Swings → Goblet Squat → 5 Halos/side\n"
                    "Repeat continuously. No rush. Moving meditation."
                ),
            },
        },
    },

    "strength_d": {
        "name":  "Strength D — Saturday Heavy Lift + Skill",
        "focus": "Heavy KB deadlift, technique skill, injury prevention, mobility",
        "note":  "Optional. Do it if you have energy. Skip guilt-free if not.",
        "weeks": {
            1: {
                "label": "Week 1 — Heavy pull introduction + overhead skill.",
                "main":  "Double KB Deadlift 5×3 @ 16 kg/bell  (lat tension before pull — own the lockout)",
                "full_body": [
                    "Dowel Rod Overhead Squat 3×8  (broom or dowel — ankles, hips, shoulders all open)",
                ],
                "focus": [
                    "Band Pull-Apart 3×20  (horizontal pull — rear delt + mid-trap)",
                    "Wall Slide 3×10  (arms slide up wall — scapular upward rotation)",
                ],
                "arms": [],
                "mobility_block": [
                    "90/90 Hip Switch 2×10",
                    "World's Greatest Stretch 2×5/side",
                    "Pigeon Pose 2×90 s/side",
                    "Cat-Cow 2×10",
                    "Thoracic Rotation 2×10/side",
                ],
                "finisher": (
                    "KB Flow / Juggling 10 min @ 12 kg  (free play — swings, catches, "
                    "anything that feels good. This is your play time.)"
                ),
            },
            2: {
                "label": "Week 2 — Heavier pull + overhead depth.",
                "main":  "Double KB Deadlift 5×3 @ 20 kg/bell  (↑ load — brace hard before the pull)",
                "full_body": [
                    "Dowel Rod Overhead Squat 3×8  (try to sit deeper — heels down)",
                ],
                "focus": [
                    "Band Pull-Apart 3×20  (slow + controlled — feel the squeeze)",
                    "Wall Slide 3×10  (press lightly into wall throughout)",
                ],
                "arms": [],
                "mobility_block": [
                    "Seated Thoracic Extension over foam roller 2×60 s",
                    "Thread the Needle 2×10/side",
                    "Hip Flexor Kneeling Stretch 2×90 s/side",
                    "Downward Dog to Cobra flow 2×10",
                ],
                "finisher": (
                    "KB Flow / Juggling 10 min @ 12–16 kg  "
                    "(try single-arm passes if comfortable)"
                ),
            },
            3: {
                "label": "Week 3 — Near-max pull + skill refinement.",
                "main":  "Double KB Deadlift 4×3 @ 24 kg/bell  (heavy — RPE 8-9, no grinding)",
                "full_body": [
                    "Dowel Rod Overhead Squat 3×8  (add a pause at the bottom — 2 s)",
                ],
                "focus": [
                    "Band Pull-Apart 3×20  (increase band tension if available)",
                    "Wall Slide 3×10  (eyes forward — avoid chin poke)",
                ],
                "arms": [],
                "mobility_block": [
                    "Couch Stretch 2×2 min/side  (deep hip flexor)",
                    "Pigeon Pose 2×2 min/side",
                    "90/90 Hip Switch 2×15",
                    "Lateral Hip Opener 2×90 s/side",
                ],
                "finisher": (
                    "KB Flow / Juggling 10 min @ 12–16 kg  "
                    "(your Saturday play. Swings, catches, cleans, whatever feels good.)"
                ),
            },
            4: {
                "label": "Week 4 — Deload pull + movement quality.",
                "main":  "Double KB Deadlift 3×3 @ 12 kg/bell  (deload — perfect tension, no ego)",
                "full_body": [
                    "Dowel Rod Overhead Squat 3×8  (easy weight — perfect reps only)",
                ],
                "focus": [
                    "Band Pull-Apart 2×20  (light — feel the pattern, not the effort)",
                    "Wall Slide 2×10  (slow and deliberate)",
                ],
                "arms": [],
                "mobility_block": [
                    "Full body flow 20 min:",
                    "  Cat-Cow × 10 → World's Greatest Stretch × 5/side",
                    "  → Pigeon Pose 2 min/side → 90/90 Hip Switch × 10",
                    "  → Thread the Needle × 10/side → Child's Pose 2 min",
                    "  → Legs-Up-the-Wall 5 min  (parasympathetic reset)",
                ],
                "finisher": (
                    "KB Flow / Juggling 10 min @ 8–12 kg  "
                    "(light and playful — this is your reward for the week)"
                ),
            },
        },
    },

    "mobility": {
        "name":  "Mobility — Program 1",
        "focus": "TGU foundation, hip opening, thoracic rotation, pilates core",
        "sessions": {
            "A": {
                "label": "Mobility A — TGU + Hip Flow",
                "main":  "Turkish Get-Up 3×3/side @ 8 kg  (pause at every position)",
                "sequence": [
                    "KB Windmill 3×5/side @ 8 kg  (packed shoulder, hinge at hip)",
                    "KB Arm Bar 2×60 s/side @ 8 kg  (shoulder external rotation)",
                    "Dead Bug 3×10/side  (lower back glued to floor)",
                    "90/90 Hip Switch 2×10  (active, not passive)",
                    "Pigeon Pose 2×90 s/side",
                    "World's Greatest Stretch 2×5/side",
                    "Hip Flexor Kneeling Stretch 2×90 s/side",
                ],
                "pilates_block": [
                    "Single-Leg Stretch 3×10/side  (Pilates — lower back imprinted)",
                    "Double-Leg Stretch 3×8",
                    "Criss-Cross 3×10/side  (Pilates oblique rotation)",
                ],
                "finisher": (
                    "Legs-Up-the-Wall 5 min  (parasympathetic reset — breathe deeply)\n"
                    "If you ran today: do this immediately after your run."
                ),
            },
            "B": {
                "label": "Mobility B — Thoracic + Core + Breath",
                "main":  "KB Bottoms-Up Press 3×5/side @ 8 kg  (shoulder stability — go slow)",
                "sequence": [
                    "Thoracic Rotation + Rib Grab 2×10/side  (hands behind head)",
                    "Thread the Needle 2×10/side  (thoracic opener)",
                    "Seated Thoracic Extension over foam roller 2×60 s",
                    "Cat-Cow 2×10  (spinal wave — 5 s per rep)",
                    "Child's Pose with Lateral Reach 2×60 s/side",
                    "Downward Dog to Cobra flow 2×8",
                ],
                "pilates_block": [
                    "Pilates Roll-Up 3×8  (slow — peel spine off floor vertebra by vertebra)",
                    "Pilates Hundred 1×100 breaths  (imprint spine, pump arms)",
                    "Pilates Swan 3×8  (thoracic extension — NOT lumbar)",
                ],
                "finisher": (
                    "Box Breathing 5 min: 4 s inhale → 4 s hold → 4 s exhale → 4 s hold\n"
                    "This is your mental centering. Do it. Your nervous system needs it."
                ),
            },
        },
    },
}


PROGRAM_2 = {
    "name":        "Program 2 — Development",
    "subtitle":    "Harder variations. More volume. Trust your body.",
    "weeks":       4,

    "strength_a": {
        "name":  "Strength A — Glute & Legs (Development)",
        "focus": "Unilateral glute strength, quad development, lateral stability",
        "weeks": {
            1: {
                "label": "Week 5 — Single-leg hip thrust. One side at a time.",
                "main":  "Single-Leg Two-Hand KB Hip Thrust 4×10/leg @ 12 kg  (pause 1 s at top)",
                "full_body": [
                    "Single-KB Floor Press 3×10/side @ 14 kg  [PUSH — between 12 and 16]",
                    "KB Chest-Supported Row 3×10 @ 12 kg  [PULL — no cheating]",
                    "Hollow Rock 3×15  [CORE — ribs down]",
                ],
                "focus": [
                    "Bulgarian Split Squat 3×8/leg @ 12 kg  (rear foot elevated)",
                    "Banded Clamshell 3×20/side  (heavier band from P1)",
                    "Single-KB Curtsy Lunge 3×10/side @ 8 kg  (cross behind and down)",
                ],
                "arms": [
                    "KB Zottman Curl 3×10 @ 8 kg  (curl up supinated, lower pronated)",
                    "KB Overhead Tricep Extension 3×12 @ 8 kg",
                ],
                "finisher": (
                    "Single-Arm KB Swing 30 s on / 30 s off × 8 rounds @ 16 kg\n"
                    "Alternate arms each round. Anti-rotation challenge."
                ),
            },
            2: {
                "label": "Week 6 — More volume on single-leg. Glutes are learning.",
                "main":  "Single-Leg Two-Hand KB Hip Thrust 5×10/leg @ 12 kg  (add a set)",
                "full_body": [
                    "Single-KB Floor Press 4×10/side @ 14 kg  [PUSH — add a set]",
                    "KB Chest-Supported Row 4×10 @ 12 kg  [PULL — add a set]",
                    "Hollow Rock 3×20  [CORE — more reps]",
                ],
                "focus": [
                    "Bulgarian Split Squat 4×8/leg @ 12 kg  (add a set)",
                    "Banded Hip Abduction Standing 3×15/side",
                    "Single-KB Curtsy Lunge 3×12/side @ 8 kg  (more reps)",
                ],
                "arms": [
                    "KB Zottman Curl 3×12 @ 8 kg",
                    "KB Overhead Tricep Extension 3×15 @ 8 kg",
                ],
                "finisher": (
                    "Single-Arm KB Swing 40 s on / 20 s off × 8 rounds @ 16 kg\n"
                    "Longer work interval. Same bell."
                ),
            },
            3: {
                "label": "Week 7 — Heavier single-leg. This is where glutes grow.",
                "main":  "Single-Leg Two-Hand KB Hip Thrust 4×8/leg @ 16 kg  (↑ load — RPE 8)",
                "full_body": [
                    "Single-KB Floor Press 4×8/side @ 16 kg  [PUSH — heavier]",
                    "KB Chest-Supported Row 4×8 @ 16 kg  [PULL — heavier]",
                    "Hollow Rock 4×20  [CORE — add a set]",
                ],
                "focus": [
                    "Bulgarian Split Squat 3×6/leg @ 16 kg  (heavier, 3-s eccentric)",
                    "Nordic Hamstring Curl 3×5 eccentric  (hamstring strength)",
                    "Lateral Lunge 3×8/side @ 12 kg  (loaded lateral)",
                ],
                "arms": [
                    "KB Zottman Curl 3×10 @ 12 kg  (up one bell)",
                    "KB Overhead Tricep Extension 3×10 @ 12 kg",
                ],
                "finisher": (
                    "Single-Arm KB Swing EMOM 10 min: 10 reps/side @ 16 kg\n"
                    "That's 100 reps per arm. Note if grip or hip fails first."
                ),
            },
            4: {
                "label": "Week 8 — Deload. Single-leg light. Breathe.",
                "main":  "Single-Leg Two-Hand KB Hip Thrust 3×10/leg @ 8 kg  (light — feel the glute)",
                "full_body": [
                    "Single-KB Floor Press 2×10/side @ 12 kg  [PUSH]",
                    "KB Chest-Supported Row 2×10 @ 12 kg  [PULL]",
                    "Dead Bug 2×10/side  [CORE — switch from hollow rock]",
                ],
                "focus": [
                    "Bodyweight Bulgarian Split Squat 2×10/leg  (form focus)",
                    "Banded Clamshell 2×20/side  (light)",
                    "Pigeon Pose 2×2 min/side",
                ],
                "arms": [
                    "KB Zottman Curl 2×12 @ 8 kg",
                    "KB Overhead Tricep Extension 2×12 @ 8 kg",
                ],
                "finisher": (
                    "Single-Arm Swing Flow 8 min @ 12 kg  (light, technical)\n"
                    "Focus on hip snap and shoulder packing. No grinding."
                ),
            },
        },
    },

    "strength_b": {
        "name":  "Strength B — Pull + Core + Arms (Development)",
        "focus": "Single-KB Z Press core integration, pull-up progression, arm definition",
        "weeks": {
            1: {
                "label": "Week 5 — Z Press. Sit on the floor, no back support, press overhead.",
                "main":  "Single-KB Z Press 4×6/side @ 12 kg  (seated on floor, legs straight — no cheating)",
                "full_body": [
                    "Single-KB Bent-Over Row 3×10/side @ 14 kg  [PULL]",
                    "Two-Hand KB Goblet Squat 3×12 @ 16 kg  [LOWER]",
                    "Ab Wheel Rollout 3×6  [CORE — from knees, ribs down]",
                ],
                "focus": [
                    "Suitcase Carry 4×20 m/side @ 16 kg  (resist the lean — anti-lateral flexion)",
                    "Pull-Up Negative 3×5  (jump to bar, 5-s controlled descent)",
                    "TRX Face Pull 3×15  (rear delt health)",
                ],
                "arms": [
                    "KB Zottman Curl 3×10 @ 8 kg",
                    "KB Tricep Kickback 3×12/side @ 8 kg",
                ],
                "finisher": (
                    "Single-KB Snatch 30 s on / 30 s off × 8 rounds @ 12 kg  (~8 min)\n"
                    "More powerful than P1. Hip snap is everything."
                ),
            },
            2: {
                "label": "Week 6 — Z Press volume. Your core is already working harder.",
                "main":  "Single-KB Z Press 5×6/side @ 12 kg  (add a set — 60 total reps)",
                "full_body": [
                    "Single-KB Bent-Over Row 4×10/side @ 14 kg  [PULL — add a set]",
                    "Two-Hand KB Goblet Squat 4×12 @ 16 kg  [LOWER — add a set]",
                    "Ab Wheel Rollout 3×8  [CORE — more reps]",
                ],
                "focus": [
                    "Suitcase Carry 5×20 m/side @ 16 kg  (add a set)",
                    "Pull-Up Negative 3×5 @ 6-s descent  (1 more second — harder)",
                    "Pallof Press 3×12/side  (anti-rotation core)",
                ],
                "arms": [
                    "KB Zottman Curl 4×10 @ 8 kg  (add a set)",
                    "KB Tricep Kickback 3×15/side @ 8 kg",
                ],
                "finisher": (
                    "Single-KB Snatch 40 s on / 20 s off × 8 rounds @ 12 kg  (~8 min)\n"
                    "Longer work. Same bell. Harder."
                ),
            },
            3: {
                "label": "Week 7 — Z Press heavier. Your shoulders are becoming iron.",
                "main":  "Single-KB Z Press 4×5/side @ 16 kg  (↑ load — RPE 8, no back support)",
                "full_body": [
                    "Single-KB Bent-Over Row 4×8/side @ 16 kg  [PULL — heavier]",
                    "Two-Hand KB Goblet Squat 4×10 @ 20 kg  [LOWER — heavier]",
                    "Ab Wheel Rollout 3×10  [CORE — more reps]",
                ],
                "focus": [
                    "Suitcase Carry 4×30 m/side @ 20 kg  (heavier, longer)",
                    "Pull-Up Negative 4×5 @ 6-s descent  (add a set)",
                    "TRX Archer Row 3×8/side  (hardest row variant)",
                ],
                "arms": [
                    "KB Zottman Curl 3×8 @ 12 kg  (up one bell)",
                    "KB Overhead Tricep Extension 3×10 @ 12 kg",
                ],
                "finisher": (
                    "Clean + Single-KB Z Press AMRAP 8 min @ 12 kg\n"
                    "5 cleans + 5 Z presses/side, switch. Note total rounds.\n"
                    "Z press from floor = brutal. Core on fire."
                ),
            },
            4: {
                "label": "Week 8 — Deload. Light Z press. Long hangs.",
                "main":  "Single-KB Z Press 3×6/side @ 8 kg  (light — feel the core bracing)",
                "full_body": [
                    "Single-KB Bent-Over Row 2×10/side @ 12 kg  [PULL]",
                    "Two-Hand KB Goblet Squat 2×12 @ 12 kg  [LOWER]",
                    "Dead Bug 3×10/side  [CORE]",
                ],
                "focus": [
                    "Suitcase Carry 2×20 m/side @ 12 kg  (light)",
                    "Dead Hang 3×30 s  (long passive hang — decompress)",
                    "Shoulder Circles + Cross-Body Stretch 2×2 min",
                ],
                "arms": [
                    "KB Zottman Curl 2×12 @ 8 kg",
                    "KB Overhead Tricep Extension 2×12 @ 8 kg",
                ],
                "finisher": (
                    "KB Flow 10 min @ 8 kg  (clean → Z press → goblet squat — repeat)\n"
                    "Moving meditation. No timer pressure."
                ),
            },
        },
    },

    "strength_c": {
        "name":  "Strength C — Hardstyle Full Body (Development)",
        "focus": "Snatch development, anti-rotation power, peak conditioning",
        "weeks": {
            1: {
                "label": "Week 5 — Snatch week. The queen of kettlebell movements.",
                "main":  "Single-KB Snatch Intervals 8 × 1 min @ 12 kg  (max reps, switch hand each set)",
                "full_body": [
                    "Single-KB Clean + Press 3×5/side @ 12 kg  [PUSH]",
                    "Double KB Front Squat 3×8 @ 12 kg/bell  [LOWER]",
                    "Push-Up 3×12  [PUSH]",
                    "Hollow Rock 3×20  [CORE]",
                ],
                "focus": [
                    "Single-KB High Pull 3×8/side @ 16 kg  (explosive — builds the snatch pull)",
                    "Two-Hand KB Hip Thrust 3×12 @ 16 kg  (glute maintenance)",
                ],
                "arms": [
                    "KB Zottman Curl 3×10 @ 8 kg",
                    "KB Overhead Tricep Extension 3×12 @ 8 kg",
                ],
                "finisher": (
                    "Long Cycle Clean + Jerk 2 × 5 min @ 12 kg  (rest 2 min between)\n"
                    "Switch hands each minute. This is sport kettlebell."
                ),
            },
            2: {
                "label": "Week 6 — More snatch volume. Your hip snap is becoming automatic.",
                "main":  "Single-KB Snatch Intervals 10 × 1 min @ 12 kg  (add 2 rounds)",
                "full_body": [
                    "KB Clean + Push Press 3×5/side @ 12 kg  [PUSH — push press harder]",
                    "Double KB Front Squat 4×8 @ 12 kg/bell  [LOWER — add a set]",
                    "Push-Up 4×12  [PUSH — add a set]",
                    "Ab Wheel Rollout 3×8  [CORE — switch from hollow rock]",
                ],
                "focus": [
                    "Single-KB High Pull 4×8/side @ 16 kg  (add a set)",
                    "Two-Hand KB Hip Thrust 4×10 @ 20 kg  (heavier)",
                ],
                "arms": [
                    "KB Zottman Curl 3×12 @ 8 kg",
                    "KB Overhead Tricep Extension 3×15 @ 8 kg",
                ],
                "finisher": (
                    "100 Single-KB Snatches for time @ 12 kg  (any hand split)\n"
                    "This is a sport standard. Note your time."
                ),
            },
            3: {
                "label": "Week 7 — Heavy week. Double KB power.",
                "main":  "Double KB Swing 10×5 EMOM @ 16 kg/bell  (5 reps, perfect, every minute)",
                "full_body": [
                    "KB Clean + Push Press 4×5/side @ 16 kg  [PUSH — heavier]",
                    "Double KB Front Squat 4×6 @ 16 kg/bell  [LOWER — heavier]",
                    "Push-Up 4×15  [PUSH — endurance]",
                    "Hanging Leg Raise 4×10  [CORE]",
                ],
                "focus": [
                    "Single-KB Snatch 5×5/side @ 16 kg  (heavy snatch — RPE 8)",
                    "Two-Hand KB Hip Thrust 4×8 @ 24 kg  (heaviest glute of the week)",
                ],
                "arms": [
                    "KB Zottman Curl 3×8 @ 12 kg  (up one bell)",
                    "KB Overhead Tricep Extension 3×10 @ 12 kg",
                ],
                "finisher": (
                    "200 Two-Hand KB Swings @ 20 kg — every time you put it down: 10 push-ups penalty\n"
                    "Heavier than P1 benchmark. Note time + breaks."
                ),
            },
            4: {
                "label": "Week 8 — Deload. Light snatches. Flow.",
                "main":  "Single-KB Snatch 5×5/side @ 8 kg  (light — technique perfection)",
                "full_body": [
                    "Single-KB Clean + Press 2×5/side @ 8 kg  [PUSH]",
                    "Two-Hand KB Goblet Squat 2×10 @ 12 kg  [LOWER]",
                    "Push-Up 2×8  [PUSH]",
                    "Dead Bug 3×10/side  [CORE]",
                ],
                "focus": [
                    "Two-Hand KB Hip Thrust 3×10 @ 12 kg  (light deload)",
                    "Hip Flexor Stretch 2×90 s/side",
                ],
                "arms": [
                    "KB Zottman Curl 2×12 @ 8 kg",
                    "KB Overhead Tricep Extension 2×12 @ 8 kg",
                ],
                "finisher": (
                    "10 min snatch flow @ 8 kg  (5/side, switch continuously)\n"
                    "No counting. Just move. This is moving meditation."
                ),
            },
        },
    },

    "strength_d": {
        "name":  "Strength D — Saturday Heavy Lift + Skill (Development)",
        "focus": "Heavy KB deadlift, overhead skill, joint prevention, yoga mobility",
        "weeks": {
            1: {
                "label": "Week 5 — Heavy pull entry + Z Press skill.",
                "main":  "Double KB Deadlift 4×3 @ 20 kg/bell  (lat tension, brace before pull)",
                "full_body": [
                    "Single-KB Z Press 3×5/side @ 12 kg  (seated floor press — no leg drive, strict overhead)",
                ],
                "focus": [
                    "Copenhagen Plank 3×20 s/side  (adductor + lateral stability)",
                    "Single-Leg Balance 3×30 s/side  (eyes open — then try eyes closed)",
                ],
                "arms": [],
                "mobility_block": [
                    "Yoga Sun Salutation A × 5 rounds  (flowing, connect breath to movement)",
                    "Warrior I + II + III flow 2×/side",
                    "Lizard Pose 2×90 s/side  (deep hip flexor)",
                    "Seated Forward Fold 2×60 s",
                ],
                "finisher": (
                    "KB Flow / Juggling 10 min @ 12–16 kg  "
                    "(try alternating hand swings and passes)"
                ),
            },
            2: {
                "label": "Week 6 — Heavier pull + Z Press volume.",
                "main":  "Double KB Deadlift 5×3 @ 20 kg/bell  (↑ volume — same load, more sets)",
                "full_body": [
                    "Single-KB Z Press 3×6/side @ 12 kg  (↑ reps — maintain upright torso)",
                ],
                "focus": [
                    "Copenhagen Plank 3×25 s/side  (progress time)",
                    "Single-Leg Balance 3×30 s/side  (add arm reach for challenge)",
                ],
                "arms": [],
                "mobility_block": [
                    "Yoga Sun Salutation B × 4 rounds",
                    "Pigeon Pose Flow 2×2 min/side",
                    "Seated Spinal Twist 2×60 s/side",
                    "Bridge Pose 3×30 s",
                ],
                "finisher": "KB Flow / Juggling 10 min @ 14–16 kg",
            },
            3: {
                "label": "Week 7 — Heavy pull + Z Press load.",
                "main":  "Double KB Deadlift 4×3 @ 24 kg/bell  (heavy — RPE 8-9, perfect form)",
                "full_body": [
                    "Single-KB Z Press 3×5/side @ 14 kg  (↑ load — slow lower, 3-s eccentric)",
                ],
                "focus": [
                    "Copenhagen Plank 3×30 s/side  (peak hold — don't let hips sag)",
                    "Single-Leg Balance 3×30 s/side  (eyes closed — full proprioceptive challenge)",
                ],
                "arms": [],
                "mobility_block": [
                    "Yoga Warrior Flow: W1 → W2 → Reverse Warrior → Triangle 3×/side",
                    "Half Pigeon 2×2 min/side",
                    "Supine Twist 2×60 s/side",
                    "Legs-Up-the-Wall 5 min",
                ],
                "finisher": "KB Flow / Juggling 10 min @ 16 kg  (peak power play)",
            },
            4: {
                "label": "Week 8 — Deload pull + movement quality.",
                "main":  "Double KB Deadlift 3×3 @ 16 kg/bell  (deload — own every rep)",
                "full_body": [
                    "Single-KB Z Press 2×5/side @ 10 kg  (light — feel the press pattern)",
                ],
                "focus": [
                    "Copenhagen Plank 2×20 s/side  (deload — quality not time)",
                    "Single-Leg Balance 2×30 s/side  (slow and controlled)",
                ],
                "arms": [],
                "mobility_block": [
                    "Restorative yoga 20 min:",
                    "  Supported Child's Pose 3 min",
                    "  Supported Bridge 3 min",
                    "  Supine Butterfly 3 min",
                    "  Legs-Up-the-Wall 5 min",
                    "  Savasana 5 min  (yes, actually do savasana)",
                ],
                "finisher": "KB Flow / Juggling 10 min @ 8–12 kg  (playful, no pressure)",
            },
        },
    },

    "mobility": {
        "name":  "Mobility — Program 2",
        "focus": "Deeper hip work, pilates core, yoga flow, shoulder prep for pull-ups",
        "sessions": {
            "A": {
                "label": "Mobility A — TGU Ladder + Yoga Hip Flow",
                "main":  "TGU Ladder (1-2-3-2-1/side) × 2 @ 8–10 kg",
                "sequence": [
                    "KB Windmill 3×6/side @ 10 kg  (heavier than P1)",
                    "KB Arm Bar 2×60 s/side @ 8 kg",
                    "Hollow Body Hold 3×20 s",
                    "Yoga Lizard Pose 2×90 s/side  (deep hip flexor)",
                    "Half Splits 2×60 s/side  (hamstring length)",
                    "Lateral Hip Opener 2×90 s/side",
                    "Frog Pose 2×60 s  (inner groin — deep)",
                ],
                "pilates_block": [
                    "Pilates Roll-Up 3×8",
                    "Pilates Teaser Prep 3×8  (legs at 45°, reach arms up)",
                    "Pilates Side-Lying Leg Lift 3×12/side  (glute medius)",
                    "Pilates Clam 3×15/side  (external rotation)",
                ],
                "finisher": (
                    "TGU AMRAP 6 min @ 8 kg  (alternating sides — note total reps)\n"
                    "Compare to P1. You should be smoother and faster."
                ),
            },
            "B": {
                "label": "Mobility B — Shoulder Prep + Pilates Core + Breath",
                "main":  "KB Bottoms-Up Press 3×6/side @ 8 kg  (more reps than P1)",
                "sequence": [
                    "Band Pull-Apart 3×20  (shoulder health — retract scapula)",
                    "Wall Slide 3×10  (shoulder mechanics — back flat on wall)",
                    "Thoracic Rotation + Rib Grab 3×10/side  (more sets than P1)",
                    "Thread the Needle 3×10/side",
                    "Cat-Cow 2×10  (5 s per rep)",
                    "Downward Dog Hold 3×30 s  (shoulder stability + hamstring)",
                ],
                "pilates_block": [
                    "Pilates Hundred 1×100 breaths  (imprint spine fully)",
                    "Pilates Double-Leg Stretch 3×10",
                    "Pilates Criss-Cross 3×12/side  (oblique rotation — slow)",
                    "Pilates Swimming 3×20 alternating  (posterior chain)",
                ],
                "finisher": (
                    "Box Breathing 5 min: 4-4-4-4\n"
                    "Then: 5 min Legs-Up-the-Wall.\n"
                    "Your nervous system is your most important muscle."
                ),
            },
        },
    },
}


PROGRAM_3 = {
    "name":        "Program 3 — Performance",
    "subtitle":    "Athletic, complex, powerful. You are the fighter now.",
    "weeks":       4,

    "strength_a": {
        "name":  "Strength A — Glute & Legs (Performance)",
        "focus": "Peak glute strength, athletic lower body, lateral power",
        "weeks": {
            1: {
                "label": "Week 9 — Elevated hip thrust. More range, more glute.",
                "main":  (
                    "Elevated Single-Leg Hip Thrust 4×10/leg @ 14 kg\n"
                    "(shoulders on bench/sofa, full hip extension, 2-s pause at top)"
                ),
                "full_body": [
                    "KB Bottoms-Up Press 3×5/side @ 8 kg  [PUSH — stability]",
                    "Double KB Renegade Row 3×6/side @ 12 kg  [PULL — anti-rotation]",
                    "Ab Wheel Rollout 3×8  [CORE — from knees]",
                ],
                "focus": [
                    "Cossack Squat 3×6/side @ 8 kg  (lateral squat — deep, heel down)",
                    "Lateral Lunge to Balance 3×8/side @ 8 kg  (lunge out, balance on return)",
                    "Single-KB Curtsy Lunge 3×10/side @ 12 kg  (heavier than P1/P2)",
                ],
                "arms": [
                    "KB Curl 3×12 @ 8 kg  (supinated — standard bicep curl)",
                    "KB Skull Crusher 3×10 @ 8 kg  (tricep mass — elbow hinge only)",
                ],
                "finisher": (
                    "Double KB Swing 8×5 EMOM @ 16 kg/bell  (40 total — powerful)\n"
                    "5 perfect reps, rest remainder of minute. Quality over quantity."
                ),
            },
            2: {
                "label": "Week 10 — More volume. Your glutes are adapting.",
                "main":  "Elevated Single-Leg Hip Thrust 5×10/leg @ 14 kg  (add a set)",
                "full_body": [
                    "KB Bottoms-Up Press 4×5/side @ 8 kg  [PUSH — add a set]",
                    "Double KB Renegade Row 3×8/side @ 12 kg  [PULL — more reps]",
                    "Ab Wheel Rollout 3×10  [CORE — more reps]",
                ],
                "focus": [
                    "Cossack Squat 3×8/side @ 8 kg  (more reps — go deeper)",
                    "Lateral Lunge to Balance 3×10/side @ 8 kg",
                    "Nordic Hamstring Curl 3×5 eccentric  (5-s descent)",
                ],
                "arms": [
                    "KB Curl 3×15 @ 8 kg  (more reps)",
                    "KB Skull Crusher 3×12 @ 8 kg",
                ],
                "finisher": (
                    "Double KB Swing 10×5 EMOM @ 16 kg/bell  (add 2 rounds)\n"
                    "50 total reps. Same quality."
                ),
            },
            3: {
                "label": "Week 11 — Heaviest week. Peak performance.",
                "main":  (
                    "Elevated Single-Leg Hip Thrust 4×8/leg @ 20 kg  (↑ load — RPE 8-9)\n"
                    "This is strong. This is what 12 weeks of work looks like."
                ),
                "full_body": [
                    "KB Bottoms-Up Press 3×5/side @ 12 kg  [PUSH — ↑ load, precision]",
                    "Double KB Renegade Row 4×6/side @ 16 kg  [PULL — heavy]",
                    "Ab Wheel Rollout 4×10  [CORE — add a set]",
                ],
                "focus": [
                    "Cossack Squat 3×6/side @ 12 kg  (loaded lateral — athlete move)",
                    "Lateral Lunge to Balance 3×8/side @ 12 kg  (heavier)",
                    "Nordic Hamstring Curl 4×5 eccentric",
                ],
                "arms": [
                    "KB Curl 3×10 @ 12 kg  (up one bell — challenging)",
                    "KB Skull Crusher 3×10 @ 12 kg  (up one bell)",
                ],
                "finisher": (
                    "Double KB Swing EMOM 12 min: 8 reps/min @ 20 kg/bell\n"
                    "96 total reps. Heavier bell. This is peak conditioning."
                ),
            },
            4: {
                "label": "Week 12 — Final deload. Let 12 weeks absorb.",
                "main":  "Elevated Single-Leg Hip Thrust 3×10/leg @ 12 kg  (light — feel the range)",
                "full_body": [
                    "KB Bottoms-Up Press 2×5/side @ 8 kg  [PUSH]",
                    "Double KB Renegade Row 2×6/side @ 12 kg  [PULL]",
                    "Dead Bug 3×10/side  [CORE]",
                ],
                "focus": [
                    "Cossack Squat 2×8/side @ BW  (bodyweight — enjoy the mobility)",
                    "Pigeon Pose 2×2 min/side",
                    "Hip Flexor Stretch 2×2 min/side",
                ],
                "arms": [
                    "KB Curl 2×12 @ 8 kg",
                    "KB Skull Crusher 2×12 @ 8 kg",
                ],
                "finisher": (
                    "Double KB Swing 5×5 @ 12 kg/bell  (light — feel the power pattern)\n"
                    "You are stronger than when you started. This is the proof."
                ),
            },
        },
    },

    "strength_b": {
        "name":  "Strength B — Pull + Core + Arms (Performance)",
        "focus": "Renegade row anti-rotation, banded pull-ups, arm definition",
        "weeks": {
            1: {
                "label": "Week 9 — Renegade rows. Core + pull simultaneously.",
                "main":  "Double KB Renegade Row 4×6/side @ 14 kg  (hips square — no rotation)",
                "full_body": [
                    "KB Bottoms-Up Press 3×5/side @ 8 kg  [PUSH]",
                    "Two-Hand KB Goblet Squat 3×10 @ 20 kg  [LOWER — heavier]",
                    "Ab Wheel Rollout 3×10  [CORE]",
                ],
                "focus": [
                    "Overhead Carry 4×20 m/side @ 12 kg  (locked shoulder — hardest carry)",
                    "Banded Pull-Up 3×5  (lightest band — closest to real pull-up)",
                    "TRX Archer Row 3×6/side  (unilateral — hardest row variant)",
                ],
                "arms": [
                    "KB Curl 3×12 @ 8 kg",
                    "KB Skull Crusher 3×10 @ 8 kg",
                ],
                "finisher": (
                    "Single-KB Snatch EMOM 12 min: 6 reps/side @ 16 kg\n"
                    "Heavier snatch than P2. Note if form holds under fatigue."
                ),
            },
            2: {
                "label": "Week 10 — More renegade volume. Your core is iron.",
                "main":  "Double KB Renegade Row 5×6/side @ 14 kg  (add a set)",
                "full_body": [
                    "KB Bottoms-Up Press 4×5/side @ 8 kg  [PUSH — add a set]",
                    "Two-Hand KB Goblet Squat 4×10 @ 20 kg  [LOWER — add a set]",
                    "Ab Wheel Rollout 4×10  [CORE — add a set]",
                ],
                "focus": [
                    "Overhead Carry 5×20 m/side @ 12 kg  (add a set)",
                    "Banded Pull-Up 3×6  (one more rep)",
                    "TRX Archer Row 3×8/side",
                ],
                "arms": [
                    "KB Curl 4×12 @ 8 kg  (add a set)",
                    "KB Skull Crusher 3×12 @ 8 kg",
                ],
                "finisher": (
                    "Single-KB Snatch EMOM 15 min: 6 reps/side @ 16 kg\n"
                    "3 more minutes than week 9. 90 total snatches per side."
                ),
            },
            3: {
                "label": "Week 11 — Heaviest renegade. Peak pulling strength.",
                "main":  "Double KB Renegade Row 4×6/side @ 16 kg  (↑ load — RPE 8-9)",
                "full_body": [
                    "KB Bottoms-Up Press 3×5/side @ 12 kg  [PUSH — ↑ load]",
                    "Two-Hand KB Goblet Squat 4×8 @ 24 kg  [LOWER — heaviest]",
                    "Ab Wheel Rollout 4×12  [CORE — more reps]",
                ],
                "focus": [
                    "Overhead Carry 4×30 m/side @ 16 kg  (heavier, longer)",
                    "Banded Pull-Up 4×5  (add a set — lightest band)",
                    "TRX Archer Row 4×6/side  (add a set)",
                ],
                "arms": [
                    "KB Curl 3×10 @ 12 kg  (up one bell)",
                    "KB Skull Crusher 3×10 @ 12 kg",
                ],
                "finisher": (
                    "Carry Medley × 5 rounds (no put-down within round):\n"
                    "  Overhead 20 m → Rack 20 m → Farmer 20 m @ 12 kg/hand\n"
                    "Rest 90 s between rounds."
                ),
            },
            4: {
                "label": "Week 12 — Final deload. Light rows. Celebrate.",
                "main":  "Double KB Renegade Row 3×6/side @ 12 kg  (light — feel the stability)",
                "full_body": [
                    "KB Bottoms-Up Press 2×5/side @ 8 kg  [PUSH]",
                    "Two-Hand KB Goblet Squat 2×10 @ 16 kg  [LOWER]",
                    "Dead Bug 3×10/side  [CORE]",
                ],
                "focus": [
                    "Overhead Carry 2×20 m/side @ 8 kg  (light)",
                    "Dead Hang 3×30 s  (passive — you've earned this grip)",
                    "Shoulder Mobility Flow 2×2 min",
                ],
                "arms": [
                    "KB Curl 2×12 @ 8 kg",
                    "KB Skull Crusher 2×12 @ 8 kg",
                ],
                "finisher": (
                    "KB Flow 10 min @ 8 kg  (clean → Z press → renegade row — repeat)\n"
                    "Moving meditation. 12 weeks complete."
                ),
            },
        },
    },

    "strength_c": {
        "name":  "Strength C — Hardstyle Full Body (Performance)",
        "focus": "Peak power output, complex conditioning, athletic capacity",
        "weeks": {
            1: {
                "label": "Week 9 — Double KB power. The hardest hardstyle session.",
                "main":  "Double KB Swing EMOM 20 min: 10 reps/min @ 16 kg/bell",
                "full_body": [
                    "KB Bottoms-Up Press 3×5/side @ 8 kg  [PUSH]",
                    "Double KB Front Squat 3×6 @ 16 kg/bell  [LOWER]",
                    "Push-Up 4×15  [PUSH — endurance]",
                    "Ab Wheel Rollout 3×10  [CORE]",
                ],
                "focus": [
                    "Single-KB Snatch Complex: 5 Snatches + 5 High Pulls/side × 3 @ 12 kg",
                    "Elevated Single-Leg Hip Thrust 3×10/leg @ 14 kg",
                ],
                "arms": [
                    "KB Curl 3×10 @ 8 kg",
                    "KB Skull Crusher 3×10 @ 8 kg",
                ],
                "finisher": (
                    "Athletic Complex × 5 rounds (rest 90 s):\n"
                    "  5 Double KB Swings + 5 Double KB Cleans + 5 Push-Ups @ 14 kg/bell"
                ),
            },
            2: {
                "label": "Week 10 — Complex conditioning. You are an athlete.",
                "main":  (
                    "Single-KB Snatch + Swing Complex EMOM 20 min @ 12 kg:\n"
                    "  Odd min: 10 Snatches (5/side)  |  Even min: 15 Swings"
                ),
                "full_body": [
                    "KB Bottoms-Up Press 4×5/side @ 8 kg  [PUSH]",
                    "Double KB Front Squat 4×6 @ 16 kg/bell  [LOWER]",
                    "Push-Up 4×15  [PUSH]",
                    "Hanging Leg Raise 4×10  [CORE]",
                ],
                "focus": [
                    "Single-KB Snatch 5×6/side @ 14 kg  (heavier snatch)",
                    "Elevated Single-Leg Hip Thrust 4×10/leg @ 16 kg",
                ],
                "arms": [
                    "KB Curl 3×12 @ 8 kg",
                    "KB Skull Crusher 3×12 @ 8 kg",
                ],
                "finisher": (
                    "300 Two-Hand KB Swings @ 16 kg — every break: 10 push-ups\n"
                    "This is the hardest finisher in the program. Note time + breaks.\n"
                    "This is what 10 weeks of training does to your capacity."
                ),
            },
            3: {
                "label": "Week 11 — Peak power week. Go heavy, go hard.",
                "main":  "Double KB Swing 12×5 EMOM @ 20 kg/bell  (heaviest double swing)",
                "full_body": [
                    "KB Bottoms-Up Press 3×5/side @ 12 kg  [PUSH — heavy]",
                    "Double KB Front Squat 4×5 @ 20 kg/bell  [LOWER — heavy]",
                    "Push-Up 4×15  [PUSH]",
                    "Ab Wheel Rollout 4×12  [CORE]",
                ],
                "focus": [
                    "Single-KB Snatch 5×5/side @ 16 kg  (heavy — RPE 8)",
                    "Elevated SL Hip Thrust 4×8/leg @ 20 kg  (peak glute load)",
                ],
                "arms": [
                    "KB Curl 3×8 @ 12 kg  (up one bell)",
                    "KB Skull Crusher 3×8 @ 12 kg",
                ],
                "finisher": (
                    "The Gauntlet:\n"
                    "  100 Double KB Swings @ 16 kg/bell\n"
                    "  Then: 50 Single-KB Snatches (25/side) @ 12 kg\n"
                    "  Then: 50 Push-Ups\n"
                    "For time. This is your 12-week fitness test."
                ),
            },
            4: {
                "label": "Week 12 — Final deload. Light swings. Reflect.",
                "main":  "Two-Hand KB Swing 5×10 @ 12 kg  (light — feel how effortless the hip snap is now)",
                "full_body": [
                    "Single-KB Clean + Press 2×5/side @ 8 kg  [PUSH]",
                    "Two-Hand KB Goblet Squat 2×10 @ 12 kg  [LOWER]",
                    "Push-Up 2×10  [PUSH]",
                    "Dead Bug 3×10/side  [CORE]",
                ],
                "focus": [
                    "Two-Hand KB Hip Thrust 3×10 @ 12 kg  (light — notice how strong your glutes feel)",
                    "Hip Mobility Flow 5 min",
                ],
                "arms": [
                    "KB Curl 2×12 @ 8 kg",
                    "KB Skull Crusher 2×12 @ 8 kg",
                ],
                "finisher": (
                    "10 min free flow @ 12 kg\n"
                    "Swings, cleans, presses, whatever feels good.\n"
                    "You started 12 weeks ago. Look at what you've built."
                ),
            },
        },
    },

    "strength_d": {
        "name":  "Strength D — Saturday Heavy Lift + Skill (Performance)",
        "focus": "Heavy KB deadlift, bottoms-up skill, athletic prevention, deep mobility",
        "weeks": {
            1: {
                "label": "Week 9 — Heavy pull + bottoms-up skill intro.",
                "main":  "Double KB Deadlift 4×3 @ 24 kg/bell  (max tension — screw feet into floor)",
                "full_body": [
                    "Bottoms-Up Press 3×5/side @ 8 kg  (wrist alignment + shoulder stability — go slow)",
                ],
                "focus": [
                    "Y-Balance Reach 3×5/side  (anterior + posteromedial + posterolateral — single-leg stability)",
                    "Copenhagen Plank 3×30 s/side  (adductor + lateral core)",
                ],
                "arms": [],
                "mobility_block": [
                    "Athletic mobility circuit 20 min:",
                    "  Yoga Warrior Flow × 3/side",
                    "  Cossack Squat hold 60 s/side",
                    "  Lizard Pose 2×90 s/side",
                    "  Pigeon Pose 2×2 min/side",
                    "  Downward Dog 3×30 s",
                    "  Handstand hold vs wall 3×20 s  (optional — shoulder strength)",
                ],
                "finisher": "KB Flow / Juggling 10 min @ 14–16 kg  (your Saturday play)",
            },
            2: {
                "label": "Week 10 — Heavier pull + bottoms-up volume.",
                "main":  "Double KB Deadlift 5×3 @ 24 kg/bell  (↑ volume — same load, add a set)",
                "full_body": [
                    "Bottoms-Up Press 3×6/side @ 8 kg  (↑ reps — keep the bell perfectly vertical)",
                ],
                "focus": [
                    "Y-Balance Reach 3×5/side  (reach further — challenge your limits)",
                    "Copenhagen Plank 3×35 s/side  (progress hold time)",
                ],
                "arms": [],
                "mobility_block": [
                    "Yoga strength flow 20 min:",
                    "  Sun Salutation B × 4",
                    "  Warrior III balance 3×30 s/side",
                    "  Chair Pose 3×30 s",
                    "  Half Moon Pose 2×30 s/side",
                    "  Legs-Up-the-Wall 5 min",
                ],
                "finisher": "KB Flow / Juggling 10 min @ 14–20 kg",
            },
            3: {
                "label": "Week 11 — Peak pull + bottoms-up load.",
                "main":  "Double KB Deadlift 4×3 @ 28 kg/bell  (peak load — RPE 9, no grinding)",
                "full_body": [
                    "Bottoms-Up Press 3×5/side @ 10 kg  (↑ load — slow and deliberate)",
                ],
                "focus": [
                    "Y-Balance Reach 3×5/side  (max reach — note your distances)",
                    "Copenhagen Plank 3×40 s/side  (peak hold — everything tight)",
                ],
                "arms": [],
                "mobility_block": [
                    "Deep restore 20 min:",
                    "  Yin Yoga Butterfly 3 min",
                    "  Yin Yoga Dragon Pose 3 min/side",
                    "  Yin Yoga Sleeping Swan 3 min/side",
                    "  Supine Spinal Twist 2×2 min/side",
                    "  Savasana 5 min",
                ],
                "finisher": "KB Flow / Juggling 10 min  (peak play — 12 weeks strong)",
            },
            4: {
                "label": "Week 12 — Deload pull + restoration.",
                "main":  "Double KB Deadlift 3×3 @ 20 kg/bell  (deload — feel strong, not tired)",
                "full_body": [
                    "Bottoms-Up Press 2×5/side @ 8 kg  (light — own the movement pattern)",
                ],
                "focus": [
                    "Y-Balance Reach 2×5/side  (light — notice how far you've come)",
                    "Copenhagen Plank 2×30 s/side  (deload — solid and easy)",
                ],
                "arms": [],
                "mobility_block": [
                    "Full restoration 20 min:",
                    "  Everything you've learned in 12 weeks",
                    "  Move through what your body needs today",
                    "  No structure — just listen and move",
                    "  End in Savasana 5 min",
                    "  You earned every second of this rest.",
                ],
                "finisher": (
                    "KB Flow / Juggling 10 min @ 8–12 kg\n"
                    "Your last Saturday session of the cycle.\n"
                    "Next week you start Program 1 again — but you are not the same person."
                ),
            },
        },
    },

    "mobility": {
        "name":  "Mobility — Program 3",
        "focus": "Athletic mobility, yin yoga, advanced pilates, performance breathing",
        "sessions": {
            "A": {
                "label": "Mobility A — Athletic Flow + Advanced Pilates",
                "main":  "TGU 3×3/side @ 12 kg  (heaviest TGU — smooth or don't go heavier)",
                "sequence": [
                    "KB Windmill 3×6/side @ 12 kg  (heaviest windmill)",
                    "Cossack Squat flow 2×10/side @ BW  (deep, controlled)",
                    "Warrior III balance 3×30 s/side  (single-leg proprioception)",
                    "Half Moon Pose 2×30 s/side",
                    "Yin Dragon Pose 2×2 min/side  (deep hip flexor — yin)",
                    "Yin Sleeping Swan 2×2 min/side  (deep pigeon — yin)",
                ],
                "pilates_block": [
                    "Pilates Teaser 3×5  (full V-sit — advanced)",
                    "Pilates Corkscrew 3×5/side  (oblique + hip control)",
                    "Pilates Side-Lying Kick Series 3×10/side",
                    "Pilates Swimming 3×30 alternating  (posterior chain endurance)",
                ],
                "finisher": (
                    "TGU AMRAP 8 min @ 10 kg  (alternating sides — longest AMRAP yet)\n"
                    "Compare total reps to P1 and P2. The improvement will surprise you."
                ),
            },
            "B": {
                "label": "Mobility B — Performance Breathing + Yin + Neural Reset",
                "main":  "KB Arm Bar 3×90 s/side @ 8 kg  (longest arm bar — full shoulder reset)",
                "sequence": [
                    "Wall Slide 3×12  (shoulder mechanics — performance prep)",
                    "Band Pull-Apart 3×25  (rear delt + scapular health)",
                    "Thoracic Rotation + Rib Grab 3×12/side",
                    "Yin Butterfly 3 min  (inner groin — passive, gravity works)",
                    "Yin Sphinx Pose 3 min  (thoracic + lumbar extension)",
                    "Yin Supine Twist 2×2 min/side",
                ],
                "pilates_block": [
                    "Pilates Hundred 1×100  (advanced — straight legs at 45°)",
                    "Pilates Roll-Over 3×5  (spinal articulation — advanced)",
                    "Pilates Jackknife 3×5  (control — hips over shoulders)",
                    "Pilates Control Balance 3×5/side  (if comfortable — advanced)",
                ],
                "finisher": (
                    "Performance breathing protocol 10 min:\n"
                    "  4 min Wim Hof style: 30 deep breaths → exhale hold → inhale hold\n"
                    "  3 min box breathing: 5-5-5-5\n"
                    "  3 min Legs-Up-the-Wall\n\n"
                    "This is your most powerful recovery tool. Do not skip this."
                ),
            },
        },
    },
}


PROGRAMS = [PROGRAM_1, PROGRAM_2, PROGRAM_3]

# ── Arms rotation ─────────────────────────────────────────────────────────────
# One pairing per program × day type. get_today_workout() uses this instead of
# the per-session hardcoded lists, so the curl/tricep combo rotates across days.

ARMS_ROTATION = {
    "program_1": {
        "strength_a": [
            "KB Hammer Curl 3×12 @ 8 kg",
            "KB Tricep Kickback 3×12/side @ 8 kg",
        ],
        "strength_b": [
            "KB Zottman Curl 3×10 @ 8 kg  (curl up supinated, lower pronated — forearm gold)",
            "KB Overhead Tricep Extension 3×12 @ 8 kg  (elbows close, full stretch at bottom)",
        ],
        "strength_c": [
            "KB Curl 3×12 @ 8 kg  (supinated — pure bicep)",
            "KB Floor Tricep Extension 3×10 @ 8 kg  (skull crusher from floor — safe)",
        ],
        "strength_d": [],
    },
    "program_2": {
        "strength_a": [
            "KB Zottman Curl 3×10 @ 10 kg  (↑ load from P1)",
            "KB Skull Crusher 3×10 @ 10 kg  (elbow hinge only — tricep mass)",
        ],
        "strength_b": [
            "Cross-Body Hammer Curl 3×10/side @ 8 kg  (curl across body — hits brachialis)",
            "Close-Grip Single-KB Floor Press 3×10 @ 12 kg  (hands touching — tricep dominant)",
        ],
        "strength_c": [
            "KB Concentration Curl 3×10/side @ 8 kg  (elbow on inner thigh — peak contraction)",
            "KB Tricep Kickback 3×12/side @ 8 kg",
        ],
        "strength_d": [],
    },
    "program_3": {
        "strength_a": [
            "KB Curl 3×10 @ 12 kg  (heavier — strength phase)",
            "KB Skull Crusher 3×10 @ 12 kg",
        ],
        "strength_b": [
            "KB Reverse Curl 3×10 @ 8 kg  (pronated grip — hits brachialis + forearm)",
            "Tricep Dip off chair 3×12  (bodyweight — full range)",
        ],
        "strength_c": [
            "KB Concentration Curl 3×10/side @ 10 kg  (↑ load)",
            "KB Overhead Tricep Extension 3×10 @ 12 kg  (↑ load)",
        ],
        "strength_d": [],
    },
}

# Day-of-week → session type (Monday=0 ... Sunday=6)
_DOW_TO_SESSION = [
    "strength_a",   # 0 Monday
    "mobility_a",   # 1 Tuesday
    "strength_b",   # 2 Wednesday
    "mobility_b",   # 3 Thursday
    "strength_c",   # 4 Friday
    "strength_d",   # 5 Saturday (optional)
    "rest",         # 6 Sunday
]

# Maps session types to track_key strings that trigger existing badge CSS
_SESSION_TRACK_KEY = {
    "strength_a": "day_a_strength",
    "strength_b": "day_b_strength",
    "strength_c": "day_c_strength",
    "strength_d": "day_d_strength",
    "mobility_a": "mobility_flow",
    "mobility_b": "mobility_flow",
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
    today  = dt.date.today()
    monday = today - dt.timedelta(days=today.weekday())
    return {
        "program_start_iso":  str(monday),
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
    session_type = _DOW_TO_SESSION[dow]

    # ── Rest day ──────────────────────────────────────────────────────────────
    if session_type == "rest":
        return {
            "status":  "rest",
            "message": "Rest day — active recovery or mobility if you feel like it.",
        }

    program_idx, current_week, weeks_elapsed = _get_program_and_week(state, today=today)
    program      = PROGRAMS[program_idx]
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

    # ── Mobility sessions ─────────────────────────────────────────────────────
    if session_type in ("mobility_a", "mobility_b"):
        mob_key = "A" if session_type == "mobility_a" else "B"
        mob     = program["mobility"]["sessions"][mob_key]
        mob_main_kg = _parse_std_kg(mob["main"], default=8.0)
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
            "main":             mob["main"],
            "std_kg":           mob_main_kg,
            "full_body_block":  mob["sequence"],
            "focus_work":       mob["pilates_block"],
            "arms":             [],
            "finisher":         mob["finisher"],
            "bell_guidance":    "Lighter than you think. Quality over load.",
            "cycle_week":       current_week,
            "suggested_weight": mob_main_kg,
            "weights_by_section": {
                "main":      mob_main_kg,
                "full_body": _first_kg(mob["sequence"]),
                "focus":     _first_kg(mob["pilates_block"]),
                "arms":      None,
                "finisher":  _first_kg([mob["finisher"]]) if mob.get("finisher") else None,
            },
        }

    # ── Strength sessions (A / B / C / D) ────────────────────────────────────
    day_data  = program[session_type]
    week_data = day_data["weeks"][current_week]
    std_kg    = _parse_std_kg(week_data["main"])
    arms_list = ARMS_ROTATION.get(f"program_{current_prog}", {}).get(
                    session_type, week_data.get("arms", []))

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
        "full_body_block":  week_data.get("full_body", []),
        "focus_work":       week_data.get("focus", []),
        "arms":             arms_list,
        "finisher":         week_data.get("finisher", ""),
        "bell_guidance":    day_data.get("focus", ""),
        "cycle_week":       current_week,
        "suggested_weight": std_kg,
        "weights_by_section": {
            "main":      std_kg,
            "full_body": _first_kg(week_data.get("full_body", [])),
            "focus":     _first_kg(week_data.get("focus", [])),
            "arms":      _first_kg(arms_list),
            "finisher":  _first_kg([week_data["finisher"]]) if week_data.get("finisher") else None,
        },
    }
    # Saturday only: include mobility block
    if session_type == "strength_d":
        result["mobility_block"] = week_data.get("mobility_block", [])

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
