"""
core.py – pure-Python logic for Olympus Training PWA
NO disk I/O, NO FastAPI; everything is stateless functions that
take `state: dict` and mutate it.
"""

import datetime as dt
import random, math

# ── Monster table (weighted probabilities) ────────────────
MONSTERS = [
    # (name, folder_name, probability %)
    ("Satyrs & Woodland Imps",       "Satyrs",              10.00),
    ("Karkinos (Giant Crab)",        "Karkinos",            10.00),
    ("Harpies",                      "Harpies",             10.00),
    ("Sirens",                       "Sirens",              10.00),
    ("Calydonian Boar",              "Calydonian_Boar",     10.00),
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
    ("Scylla & Charybdis",           "Scylla_Charybdis",     0.75),
    ("Echidna",                      "Echidna",              0.75),
    ("Hecatoncheires",              "Hecatoncheires",       0.75),
    ("Typhon",                       "Typhon",               0.75),
]
MONSTER_TOTAL = sum(p for _, _, p in MONSTERS)   # 100.0
GILD_CHANCE = 0.10   # 10 % chance the badge is the “Gold” variant

# ── Ruck postcard milestones (miles, city, line) ──────────
RUCK_STOPS = [
    (0,   "Acropolis",  "“Welcome to leg-day on hard mode!” Athena’s owl hoots, 'Hoot luck, buddy.'"),
    (12,  "Eleusis",    "Demeter offers carbs—then turns bread into a kettlebell."),
    (26,  "Megara",     "Heracles flexes and asks you to carry his lion skin too."),
    (48,  "Corinth",    "Pegasus brags about 'flying the route'. You call him a hoverboard."),
    (75,  "Nemea",      "Retired Nemean Lion still judges your squat depth."),
    (99,  "Tegea",      "Atalanta rolls golden apples—you’re too tired to bend."),
    (153, "Sparta",     "Spartan mom: 'Come back with your ruck… or get roasted.'"),
    (206, "Mantinea",   "Artemis fires a warning arrow—your shuffle scares turtles."),
    (224, "Argos",      "Hera’s all-seeing cam logs your pothole side-step as 'cowardice'."),
    (249, "Epidaurus",  "Asclepius offers magic salve—if you pronounce his name right."),
    (286, "Sounion",    "Poseidon: 'Try rucking underwater next time!'"),
    (306, "Athens Return", "Nike crowns you, whispers 'Drop the pack before gravity charges fees.'"),
]

# ──────────────────────────────────────────────────────────────
#  TEMPLATES  (add more cycles the same way)
# ──────────────────────────────────────────────────────────────
TEMPLATES = {
    "hermes_power_forge": {
        "name": "Hermes' Power Forge (2-week / 6 sessions)",
        "sessions": [
            {   # W-1 D-1
                "main": "Double-KB Front Squat 5×5 @ RPE 7",
                "accessory": [
                    "Bulgarian Split Squat 3×8 /leg",
                    "TRX Row 3×10",
                    "20-lb-vest Glute-Bridge March 3×40 s",
                ],
                "finisher": "30 s Goblet-Squat Pulse / 30 s rest × 4",
            },
            # … (add the other five sessions exactly as before)
        ],
    },
}

TRACK_KEYS = list(TEMPLATES.keys())
SESSIONS_NEEDED = 6             # workouts per 2-week cycle
WK_TARGET   = 3                 # workouts per calendar week

# ──────────────────────────────────────────────────────────────
#  Helper – default blank state
# ──────────────────────────────────────────────────────────────
def default_state() -> dict:
    return {
        "track": TRACK_KEYS[0],
        "microcycle": {
            "id": 0,
            "sessions_completed": 0,
            "start_date": str(dt.date.today()),
            "badge_given": False,
        },
        "workouts": [],         # list[ {date, type, details} ]
        "ruck_log": [],         # list[ {date, distance_miles, weight_lbs} ]
        "badges": [],           # list of any badge records
        "treasury": 0.0,        # drachma
        "templates": {k: v["name"] for k, v in TEMPLATES.items()},
    }

# ──────────────────────────────────────────────────────────────
#  Public API functions (used by FastAPI layer)
# ──────────────────────────────────────────────────────────────
def log_rec(state: dict) -> str:
    """Log the next recommended workout for the active cycle."""
    mc  = state["microcycle"]
    idx = mc["sessions_completed"]
    tpl = TEMPLATES[state["track"]]["sessions"][idx]

    # history entry
    state["workouts"].append({
        "date": str(dt.date.today()),
        "type": "recommended",
        "details": tpl["main"],
    })

    # counters
    mc["sessions_completed"] += 1
    _increment_weekly_streak(state)

        # cycle badge logic
    if mc["sessions_completed"] >= SESSIONS_NEEDED:
        start = dt.date.fromisoformat(mc["start_date"])
        if (dt.date.today() - start).days >= 13 and not mc["badge_given"]:
            _award_monster_badge(state)
            mc["badge_given"] = True


    return f"✔ Logged: {tpl['main']}"

def log_custom(state: dict, text: str) -> str:
    state["workouts"].append({
        "date": str(dt.date.today()),
        "type": "custom",
        "details": text,
    })
    _increment_weekly_streak(state)
    return "✔ Custom workout logged."

def log_ruck(state: dict, miles: float, pounds: float) -> str:
    state["ruck_log"].append({
        "date": str(dt.date.today()),
        "distance_miles": miles,
        "weight_lbs": pounds,
    })
    # drachma: 1 per mile × (1 + 0.01·lbs)
    coins = miles * (1 + 0.01 * pounds)
    state["treasury"] = round(state["treasury"] + coins, 2)
    return f"🪙 Earned {coins:.2f} Drachma."
  
def _check_ruck_milestone(state: dict, prev_miles: float, new_miles: float):
    for miles, city, line in RUCK_STOPS:
        if prev_miles < miles <= new_miles:
            state["badges"].append({
                "date": str(dt.date.today()),
                "name": f"{city} Postcard",
                "type": "ruck_quest",
                "details": line,
                "image_path": f"Pheidippides/{city.replace(' ', '_')}.png"
            })

def log_ruck(state: dict, miles: float, pounds: float) -> str:
    ...
    prev = sum(r["distance_miles"] for r in state["ruck_log"])
    state["ruck_log"].append({...})
    new_total = prev + miles
    _check_ruck_milestone(state, prev, new_total)
    ...


# ──────────────────────────────────────────────────────────────
#  Internal helpers
# ──────────────────────────────────────────────────────────────
def _increment_weekly_streak(state: dict):
    """Award laurel badge after 3 workouts in a calendar week."""
    today = dt.date.today().isocalendar()[:2]     # (year, week)
    state.setdefault("week_log", {}).setdefault(str(today), 0)
    wk_count = state["week_log"][str(today)] + 1
    state["week_log"][str(today)] = wk_count
    if wk_count == WK_TARGET:
        state["badges"].append({
            "date": str(dt.date.today()),
            "name": "Olympian Laurel",
            "type": "laurel"
        })

def _pick_monster() -> tuple[str, str]:
    """Return (monster_name, image_folder)."""
    r = random.uniform(0, MONSTER_TOTAL)
    cum = 0.0
    for name, folder, prob in MONSTERS:
        cum += prob
        if r <= cum:
            return name, folder
    return MONSTERS[-1][:2]   # fallback

def _award_monster_badge(state: dict):
    name, folder = _pick_monster()
    gilded = random.random() < GILD_CHANCE
    variant = "Gold" if gilded else "Vibrant"
    img_path = f"monsters/{folder}/{variant}/{folder}.png"

    state["badges"].append({
        "date": str(dt.date.today()),
        "name": name + (" ★" if gilded else ""),
        "type": "monster",
        "image_path": img_path,
    })

