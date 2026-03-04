"""
core.py – pure-Python logic for Olympus Training PWA
NO disk I/O, NO FastAPI; stateless functions that take `state: dict` and mutate it.
"""

import datetime as dt
import random

# ── Monster table (weighted probabilities) ────────────────────────────────────
# Folder names match actual directories on disk (some have typos — intentional)
MONSTERS = [
    # (display_name,                 folder_name,           probability %)
    ("Satyrs & Woodland Imps",       "Saytr",               10.00),
    ("Karkinos (Giant Crab)",        "Karkinos",            10.00),
    ("Harpies",                      "Harpies",             10.00),
    ("Sirens",                       "Sirens",              10.00),
    ("Calydonian Boar",              "Calydonin_Boar",      10.00),
    ("Stymphalian Birds",            "Stymphalian_Birds",    5.00),
    ("The Sphinx",                   "Sphinx",               5.00),
    ("Minotaur",                     "Minotaur",             5.00),
    ("Polyphemus (Cyclops)",         "Polyphemus",           5.00),
    ("Orthrus (Two-Headed Dog)",     "Orthrus",              5.00),
    ("Medusa",                       "Medusa",               3.00),
    ("Mares of Diomedes",            "Mares_of_Diomedes",    3.00),
    ("Nemean Lion",                  "Nemean_Lion",          3.00),
    ("Colchian Dragon",              "Colchian_Dragon",      3.00),
    ("Lernaean Hydra",               "Lernaean_Hydra",       3.00),
    ("Geryon",                       "Geryon",               1.40),
    ("Chimera",                      "Chimera",              1.40),
    ("Talos",                        "Talos",                1.40),
    ("Cerberus",                     "Cerberus",             1.40),
    ("Gigantes",                     "Gigantes",             1.40),
    ("Scylla & Charybdis",           "Scylla_&_Charybdis",  0.75),
    ("Echidna",                      "Echidna",              0.75),
    ("Hecatoncheires",               "Hecatoncheires",       0.75),
    ("Typhon",                       "Typhon",               0.75),
]
MONSTER_TOTAL = sum(p for _, _, p in MONSTERS)   # 100.0
GILD_CHANCE   = 0.10   # 10 % chance the badge is the "Gold" variant

OLYMPIANS = [
    ("Zeus", "⚡"), ("Hera", "👑"), ("Athena", "🦉"), ("Ares", "🛡️"),
    ("Apollo", "☀️"), ("Artemis", "🏹"), ("Hermes", "🪽"), ("Demeter", "🌾"),
    ("Poseidon", "🌊"), ("Hades", "🖤"),
]

# ── Ruck milestone stops (Pheidippides round-trip Athens → Sparta → Athens) ──
RUCK_STOPS = [
    (0,   "Acropolis",
     "\"Welcome to leg-day on hard mode!\" Athena's owl hoots, 'Hoot luck, buddy.'"),
    (12,  "Eleusis",
     "Demeter offers carbs—then turns bread into a kettlebell."),
    (26,  "Megara",
     "Heracles flexes and asks you to carry his lion skin too."),
    (48,  "Corinth",
     "Pegasus brags about 'flying the route'. You call him a hoverboard."),
    (75,  "Nemea",
     "Retired Nemean Lion still judges your squat depth."),
    (99,  "Tegea",
     "Atalanta rolls golden apples—you're too tired to bend."),
    (153, "Sparta",
     "Spartan mom: 'Come back with your ruck… or get roasted.'"),
    (206, "Mantinea",
     "Artemis fires a warning arrow—your shuffle scares turtles."),
    (224, "Argos",
     "Hera's all-seeing cam logs your pothole side-step as 'cowardice'."),
    (249, "Epidaurus",
     "Asclepius offers magic salve—if you pronounce his name right."),
    (286, "Sounion",
     "Poseidon: 'Try rucking underwater next time!'"),
    (306, "Athens Return",
     "Nike crowns you, whispers 'Drop the pack before gravity charges fees.'"),
]
TRIP_MILES = RUCK_STOPS[-1][0]   # 306

# ── Training templates ────────────────────────────────────────────────────────
TEMPLATES = {
    "hermes_power_forge": {
        "name": "Hermes' Power Forge (2-week / 6 sessions)",
        "sessions": [
            {   # Wk-1 Day-1  Lower Push
                "main": "Double-KB Front Squat 5×5 @ RPE 7",
                "accessory": [
                    "Bulgarian Split Squat 3×8 /leg",
                    "TRX Row 3×10",
                    "20-lb-vest Glute-Bridge March 3×40 s",
                ],
                "finisher": "30 s Goblet-Squat Pulse / 30 s rest × 4",
            },
            {   # Wk-1 Day-2  Upper
                "main": "Single-Arm Clean + Press 5×5 /side",
                "accessory": [
                    "Single-KB Floor Press 3×10 /side",
                    "Bent-Over Row 3×8 /side",
                    "TRX Face-Pull + Y-Raise superset 3×12 each",
                ],
                "finisher": "KB Hollow-Body OH Hold 20 s on / 10 s off × 4",
            },
            {   # Wk-1 Day-3  Lower Hinge
                "main": "Double-KB Deadlift 6×6 @ RPE 7",
                "accessory": [
                    "Alternating KB Swing EMOM 8 (12 reps)",
                    "TRX Hamstring Curl 3×15",
                    "Suitcase Carry 4×20 m /side",
                ],
                "finisher": "20-lb-vest Step-Ups 30 s / 15 s × 5",
            },
            {   # Wk-2 Day-1  Lower Push Progression
                "main": "Double-KB Front Squat 6×4 (↑ load)",
                "accessory": [
                    "Goblet Box-Squat Pulse 3×12",
                    "TRX Single-Leg Hip Thrust 3×10 /leg",
                    "Front-Rack Squat-Hold 3×30 s",
                ],
                "finisher": "Tabata Alternating Swings (4 min)",
            },
            {   # Wk-2 Day-2  Upper Progression
                "main": "Clean + Push-Press Ladder (1-2-3-2-1) × 3",
                "accessory": [
                    "Renegade Row 3×8 /side",
                    "TRX Atomic Push-Up 3×10",
                    "KB Windmill 3×6 /side",
                ],
                "finisher": "Farmer-Carry March 45 s / 15 s × 4",
            },
            {   # Wk-2 Day-3  Lower Hinge Progression
                "main": "Tempo KB RDL (3-s eccentric) 4×8",
                "accessory": [
                    "High Pull EMOM 10 (6 /side)",
                    "Weighted Step-Up 3×12 /leg",
                    "Plank Pull-Through 3×30 s",
                ],
                "finisher": "Swing-Sprint: 10 Swings + 50 m run × 5",
            },
        ],
    },
}

TRACK_KEYS      = list(TEMPLATES.keys())
SESSIONS_NEEDED = 6      # workouts per 2-week cycle
WK_TARGET       = 3      # workouts per calendar week for a laurel

# ── Default state ─────────────────────────────────────────────────────────────
def default_state() -> dict:
    return {
        "track": TRACK_KEYS[0],
        "microcycle": {
            "id": 0,
            "sessions_completed": 0,
            "start_date": str(dt.date.today()),
            "badge_given": False,
        },
        "workouts":         [],    # list[{date, type, details}]
        "ruck_log":         [],    # list[{date, distance_miles, weight_lbs, coins}]
        "badges":           [],    # list of badge records
        "treasury":         0.0,   # drachma accumulated
        "total_ruck_miles": 0.0,   # lifetime ruck distance
        "week_log":         {},    # {"(year, week)": count}
        "templates":        {k: v["name"] for k, v in TEMPLATES.items()},
    }

# ── Public API ────────────────────────────────────────────────────────────────

def get_today_workout(state: dict) -> dict:
    """Return structured data for the current session (no mutation)."""
    track = state.get("track")
    if not track or track not in TEMPLATES:
        return {"status": "no_track", "message": "No track selected."}
    mc  = state["microcycle"]
    idx = mc["sessions_completed"]
    if idx >= SESSIONS_NEEDED:
        return {"status": "cycle_complete",
                "message": "Cycle complete! Log a custom workout or start a new track."}
    sess = TEMPLATES[track]["sessions"][idx]
    return {
        "status":        "active",
        "session_num":   idx + 1,
        "total_sessions": SESSIONS_NEEDED,
        "main":          sess["main"],
        "accessory":     sess["accessory"],
        "finisher":      sess["finisher"],
        "track_name":    TEMPLATES[track]["name"],
    }


def init_track(state: dict, key: str) -> str:
    """Start a new micro-cycle on the given track."""
    if key not in TEMPLATES:
        return f"Unknown track: {key}"
    state["track"] = key
    state["microcycle"] = {
        "id":                  state["microcycle"]["id"] + 1,
        "sessions_completed":  0,
        "start_date":          str(dt.date.today()),
        "badge_given":         False,
    }
    return f"Started {TEMPLATES[key]['name']}"


def log_rec(state: dict) -> str:
    """Log the next recommended session for the active micro-cycle."""
    track = state.get("track")
    if not track or track not in TEMPLATES:
        return "No active track. Please select a track first."
    mc  = state["microcycle"]
    idx = mc["sessions_completed"]
    if idx >= SESSIONS_NEEDED:
        return "Cycle already complete. Log custom or start a new track."

    tpl = TEMPLATES[track]["sessions"][idx]
    state["workouts"].append({
        "date":    str(dt.date.today()),
        "type":    "recommended",
        "details": tpl["main"],
    })
    mc["sessions_completed"] += 1
    _increment_weekly_streak(state)
    _maybe_award_cycle_badge(state)
    return f"✔ Logged: {tpl['main']}"


def log_custom(state: dict, text: str) -> str:
    """Log a free-text custom workout."""
    state["workouts"].append({
        "date":    str(dt.date.today()),
        "type":    "custom",
        "details": text,
    })
    state["microcycle"]["sessions_completed"] += 1
    _increment_weekly_streak(state)
    _maybe_award_cycle_badge(state)
    return "✔ Custom workout logged."


def log_ruck(state: dict, miles: float, pounds: float) -> str:
    """Log a ruck session, award drachma, and check for milestone postcards."""
    prev      = state.get("total_ruck_miles", 0.0)
    new_total = prev + miles
    coins     = round(miles * (1 + 0.01 * pounds), 2)

    state["ruck_log"].append({
        "date":           str(dt.date.today()),
        "distance_miles": miles,
        "weight_lbs":     pounds,
        "coins":          coins,
    })
    state["treasury"]         = round(state.get("treasury", 0.0) + coins, 2)
    state["total_ruck_miles"] = new_total

    _check_ruck_milestone(state, prev, new_total)
    return (f"🪙 Earned {coins:.2f} Drachma.  "
            f"Total: {new_total:.1f} mi rucked.")

# ── Internal helpers ──────────────────────────────────────────────────────────

def _maybe_award_cycle_badge(state: dict) -> None:
    """Award monster trophy when 6 sessions are done within a 2-week window."""
    mc = state["microcycle"]
    if mc["badge_given"]:
        return
    if mc["sessions_completed"] < SESSIONS_NEEDED:
        return
    start = dt.date.fromisoformat(mc["start_date"])
    if (dt.date.today() - start).days < 13:
        return
    _award_monster_badge(state)
    mc["badge_given"] = True


def _increment_weekly_streak(state: dict) -> None:
    """Award an Olympian Laurel after WK_TARGET workouts in a calendar week."""
    today    = dt.date.today().isocalendar()[:2]   # (year, week_number)
    week_key = str(today)
    state.setdefault("week_log", {})
    count = state["week_log"].get(week_key, 0) + 1
    state["week_log"][week_key] = count
    if count == WK_TARGET:
        god, icon = random.choice(OLYMPIANS)
        state["badges"].append({
            "date":       str(dt.date.today()),
            "name":       f"{icon} {god} Laurel",
            "type":       "laurel",
            "image_path": None,
        })


def _check_ruck_milestone(state: dict,
                           prev_miles: float,
                           new_miles:  float) -> None:
    """Award ruck-quest postcards for every waypoint crossed (loop-aware)."""
    if TRIP_MILES <= 0:
        return

    prev_loop = int(prev_miles // TRIP_MILES)
    new_loop  = int(new_miles  // TRIP_MILES)

    # build set of already-earned (loop, city) pairs to prevent duplicates
    earned: set = set()
    for b in state["badges"]:
        if b.get("type") == "ruck_quest":
            earned.add((b.get("loop", 0), b.get("stop", "")))

    for loop in range(prev_loop, new_loop + 1):
        base = loop * TRIP_MILES
        for offset, city, caption in RUCK_STOPS:
            abs_mark = base + offset
            if prev_miles <= abs_mark <= new_miles and (loop, city) not in earned:
                slug = city.replace(" ", "_")
                state["badges"].append({
                    "type":       "ruck_quest",
                    "loop":       loop,
                    "stop":       city,
                    "name":       f"📜 {city} Way-Point",
                    "date":       str(dt.date.today()),
                    "caption":    caption,
                    "image_path": f"Pheidippides/{slug}.png",
                })


def _pick_monster() -> tuple:
    """Return (display_name, folder_name) using weighted random selection."""
    r   = random.uniform(0, MONSTER_TOTAL)
    cum = 0.0
    for name, folder, prob in MONSTERS:
        cum += prob
        if r <= cum:
            return name, folder
    return MONSTERS[-1][:2]   # fallback


def _award_monster_badge(state: dict) -> None:
    """Add a randomly-selected monster trophy (10 % chance of gilded variant)."""
    name, folder = _pick_monster()
    gilded   = random.random() < GILD_CHANCE
    variant  = "Gold" if gilded else "Vibrant"
    img_path = f"{folder}/{variant}/{folder}.png"
    state["badges"].append({
        "date":       str(dt.date.today()),
        "name":       name + (" ★" if gilded else ""),
        "type":       "monster",
        "image_path": img_path,
    })
