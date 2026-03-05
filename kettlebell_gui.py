# kettlebell_gui.py – v3.3 (Olympus Edition + Beast Trophies & Olympian Laurels)
"""Rena’s Kettlebell & Ruck Tracker – Desktop GUI (Greek‑Mythology Theme)
=======================================================================
**Key mechanics**
* **Weekly streak** (7 logged training days) ⇒ random **Olympian Laurel** (⚡ Zeus Laurel I, 👑 Hera Laurel II, …)
* **Micro‑cycle completion** (6 recommended sessions) ⇒ random **Mythic Beast Trophy** (🦁 Nemean Lion Trophy 1, 🐲 Chimera Trophy 2, …)
* **Ruck mileage** (25‑mi increments) ⇒ Olympian Laurel.
* **Temple of Triumphs** sidebar lists **all** laurels & trophies with scrolling.

---
**Run:**
```bash
python kettlebell_gui.py
```
Requires Python 3.9+ with Tkinter (macOS ships with it; Windows installers include it).
"""
from __future__ import annotations

import json
import random
import datetime as dt
import collections
from pathlib import Path
from typing import Dict, Any
import tkinter as tk
from tkinter import ttk, simpledialog
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk

# ──────────────────────────────────────────────────────────────
#  THEME & CONSTANTS
# ──────────────────────────────────────────────────────────────
DATA_PATH = Path.home() / ".rena_kb_data.json"

BG_DARK  = "#0d1b2a"   # midnight blue
BG_LIGHT = "#f0e6d2"   # marble cream
ACCENT_G = "#c9b037"   # laurel gold

MENU_COL_W  = 620          # width for the Training Menu
MENU_COL_H = 12          # treeview rows visible for the menu
SIDE_COL_W  = 240          # laurels & temple
SIDE_CANVAS_W = 220        # inner canvas width (keep)

TARGET_WK_WORKOUTS = 3        # how many sessions keep the weekly streak alive

MICROCYCLE_LEN = 14        # days
SESSIONS_NEEDED = 6        # workouts required to finish microcycle badge requirement

# ── Ruck-Quest: Pheidippides round-trip ───────────────────────
RUCK_STOPS = [      # miles from Athens
    ("Acropolis",        0),
    ("Eleusis",         12),
    ("Megara",          26),
    ("Corinth",         48),
    ("Nemea",           75),
    ("Tegea",           99),
    ("Sparta",         153),
    ("Mantinea",       206),
    ("Argos",          224),
    ("Epidaurus",      249),
    ("Sounion",        286),
    ("Athens Return",  306),
]

# captions keyed by the *same* waypoint names
RUCK_CAPTIONS = {
    "Acropolis":        "“Welcome to leg-day on hard mode!” Athena’s owl just took one look at your ruck and muttered, “Hoot luck, buddy.”",
    "Eleusis":          "Demeter waves a loaf of ancient sourdough, promising carbs—then remembers you’re low-carb and turns it into a kettlebell instead.",
    "Megara":           "Hercules appears, flexes, and asks if you’d mind carrying his lion skin too… you politely decline and blame “strict baggage rules.”",
    "Corinth":          "Pegasus gallops past bragging about “flying the whole route.” You remind him wings are basically the original cheating hoverboard.",
    "Nemea":            "Locals offer you a selfie with the retired Nemean Lion. He is chill now—but still judges your form if you slack on posture.",
    "Tegea":            "Atalanta tries to bait you with golden apples, but you’re too tired to bend down; core engagement never felt so petty.",
    "Sparta":"A Spartan mom hands you a snack and says, “Come back with your ruck… or get roasted in the group chat.” Motivation achieved.",
    "Mantinea":         "Artemis fires a warning arrow over your head—apparently your shuffle pace is scaring the wildlife. Even the turtles.",
    "Argos":            "The Hera multi-eyed security cam spots you sidestepping a pothole and logs it as “cowardice.” You power-skip to clear your reputation.",
    "Epidaurus":        "Asclepius offers a magic salve for sore traps—but only if you pronounce “Asclepius” correctly on the first try. You limp away unhealed.",
    "Sounion":          "Poseidon hurls sea spray in your face and shouts, “Try rucking underwater next time!” You start a petition for floaty dumbbells.",
    "Athens Return":    "Nike swoops in with a laurel crown and whispers, “Congrats—now drop the pack before gravity charges late fees.”",
}

TRIP_MILES = RUCK_STOPS[-1][1]      # 306 mi in this list



OLYMPIANS = [  # weekly & ruck badges
    ("Zeus", "⚡"), ("Hera", "👑"), ("Athena", "🦉"), ("Ares", "🛡️"),
    ("Apollo", "☀️"), ("Artemis", "🏹"), ("Hermes", "🪽"), ("Demeter", "🌾"),
    ("Poseidon", "🌊"), ("Hades", "🖤")
]



# ──────────────────────────────────────────────────────────────
#  HARD-STYLE MICRO-CYCLES (6 TRACKS × 6 SESSIONS)
# ──────────────────────────────────────────────────────────────
mk = lambda d, desc, struct: {"day": d, "description": desc, "structure": struct}

# ──────────────────────────────────────────────────────────────
#  TEMPLATE LIBRARY
#  (each entry is a 2-week / 6-session micro-cycle)
# ──────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────
#  TEMPLATE LIBRARY (each entry is a 2-week / 6-session cycle)
# ──────────────────────────────────────────────────────────────
TEMPLATES: dict[str, dict[str, Any]] = {

    # ── Hermes’ Power Forge ──────────────────────────────────
    "Hermes' Power Forge": {
        "name": "Hermes' Power Forge",
        "sessions": [
            {   # Wk-1 D-1 – Lower Push
                "main": "Double-KB Front Squat 5×5 @ RPE 7",
                "accessory": [
                    "Bulgarian Split Squat 3×8 /leg",
                    "TRX Row 3×10",
                    "20-lb-vest Glute-Bridge March 3×40 s",
                ],
                "finisher": "30 s Goblet-Squat Pulse / 30 s rest ×4",
            },
            {   # Wk-1 D-2 – Upper
                "main": "Single-Arm Clean + Press 5×5 /side",
                "accessory": [
                    "Single-KB Floor Press 3×10 /side",
                    "Bent-Over Row 3×8 /side",
                    "TRX Face-Pull + Y-Raise superset 3×12 each",
                ],
                "finisher": "KB Hollow-Body OH Hold 20 s on /10 s off ×4",
            },
            {   # Wk-1 D-3 – Lower Hinge
                "main": "Double-KB Deadlift 6×6 @ RPE 7",
                "accessory": [
                    "Alternating KB Swing EMOM 8 (12 reps)",
                    "TRX Hamstring Curl 3×15",
                    "Suitcase Carry 4×20 m /side",
                ],
                "finisher": "20-lb-vest Step-Ups 30 s /15 s ×5",
            },
            {   # Wk-2 D-1 – Lower Push Prog
                "main": "Double-KB Front Squat 6×4 (↑ load)",
                "accessory": [
                    "Goblet Box-Squat Pulse 3×12",
                    "TRX Single-Leg Hip Thrust 3×10 /leg",
                    "Front-Rack Squat-Hold 3×30 s",
                ],
                "finisher": "Tabata Alternating Swings (4 min)",
            },
            {   # Wk-2 D-2 – Upper Prog
                "main": "Clean + Push-Press Ladder (1-2-3-2-1) ×3",
                "accessory": [
                    "Renegade Row 3×8 /side",
                    "TRX Atomic Push-Up 3×10",
                    "KB Windmill 3×6 /side",
                ],
                "finisher": "Farmer-Carry March 45 s /15 s ×4",
            },
            {   # Wk-2 D-3 – Lower Hinge Prog
                "main": "Tempo KB RDL (3-s eccentric) 4×8",
                "accessory": [
                    "High Pull EMOM 10 (6 /side)",
                    "Weighted Step-Up 3×12 /leg",
                    "Plank Pull-Through 3×30 s",
                ],
                "finisher": "Swing-Sprint: 10 Swings + 50 m run ×5",
            },
        ],
    },

    # ── Artemis Rites ────────────────────────────────────────
    "Artemis Rites": {
        "name": "Artemis Rites",
        "sessions": [
            {   # W-3 D-1 – Reverse-Lunge Power
                "main": "Double-KB Front-Rack Reverse Lunge 5×5 /leg",
                "accessory": [
                    "KB Swing 3×15",
                    "TRX Hamstring Curl 3×12",
                    "20-lb-vest Glute-Bridge March 3×40 s",
                ],
                "finisher": "Goblet-Squat Iso-Pulse 30 s / 15 s rest ×4",
            },
            {   # W-3 D-2 – Chest & Back
                "main": "Single-KB Floor-Press Cluster (2-2-2, 10 s intra-rest) ×4 /side",
                "accessory": [
                    "Single-Arm Bent Row 3×10 /side",
                    "TRX Face-Pull 3×15",
                ],
                "finisher": "Plank Pull-Through 20 s on / 10 s off ×6",
            },
            {   # W-3 D-3 – Sumo & Carries
                "main": "Double-KB Sumo Deadlift 6×6 (3-s eccentric)",
                "accessory": [
                    "Jumping Goblet Squat 3×12",
                    "Suitcase Carry 3×20 m /side",
                    "TRX Pistol-Assist 3×6 /leg",
                ],
                "finisher": "Tabata Alternating Swings 4 min",
            },
            {   # W-4 D-1 – Front-Squat Ladder
                "main": "Double-KB Clean + Front-Squat Ladder 1-2-3-4-3-2-1",
                "accessory": [
                    "Walking Lunges (racked) 3×12 /leg",
                    "TRX Single-Leg Hip Thrust 3×10 /leg",
                    "KB Swing 3×20",
                ],
                "finisher": "20-lb-vest Step-Up Sprint 30 s on / 15 s off ×5",
            },
            {   # W-4 D-2 – Overhead & Core
                "main": "Half-Kneeling Push-Press 5×6 /side",
                "accessory": [
                    "EMOM 10 — Odd: 8 Renegade Rows /side",
                    "EMOM 10 — Even: 6 TRX Atomic Push-Ups",
                ],
                "finisher": "Farmer-Carry March 45 s / 15 s ×4",
            },
            {   # W-4 D-3 – Single-Leg Hinge
                "main": "KB Bulgarian Single-Leg RDL 4×8 /leg",
                "accessory": [
                    "High Pull 3×10 /side",
                    "Weighted Step-Up 3×12 /leg",
                    "Plank Reach-Out 3×15 /side",
                ],
                "finisher": "Swing-Sprint — 10 Swings + 50 m dash ×5",
            },
        ],
    },
}


TRACK_KEYS = list(TEMPLATES.keys())


# ──────────────────────────────────────────────────────────────
#  PERSISTENCE & BADGE LOGIC
# ──────────────────────────────────────────────────────────────
_save = lambda d: DATA_PATH.write_text(json.dumps(d, indent=2))
_today = lambda: dt.date.today()

def _default() -> Dict[str, Any]:
    return {
        "track": None,
        "microcycle": {
        "id": 0,
        "sessions_completed": 0,
        "start_date": str(_today()),   # ← NEW
        "badge_given": False           # ← NEW
        },
        "workouts": [],
        "ruck_log": [],
        "badges": [],
        "streak": {"active_days": 0, "last_date": None},
        "total_ruck_miles": 0.0,
        "treasury": 0.0,          #  ←  NEW
    }

def _load() -> Dict[str, Any]:
    d = json.loads(DATA_PATH.read_text()) if DATA_PATH.exists() else _default()

    # one-time backward-compat patches
    mc = d["microcycle"]
    mc.setdefault("start_date", str(_today()))
    mc.setdefault("badge_given", False)
    if "treasury" not in d:
        d["treasury"] = 0.0

    return d

# ──────────────────────────────────────────────────────────────
#  MONSTER BADGE LOTTERY  (24 beasts + rarity weights)
# ──────────────────────────────────────────────────────────────
_MONSTERS = [
    #  name,                      prob%
    ("Satyrs",                       10.00),
    ("Karkinos",                     10.00),
    ("Harpies",                      10.00),
    ("Sirens",                       10.00),
    ("Calydonian_Boar",              10.00),
    ("Stymphalian_Birds",             5.00),
    ("Sphinx",                        5.00),
    ("Minotaur",                      5.00),
    ("Polyphemus",                    5.00),
    ("Orthrus",                       5.00),
    ("Medusa",                        3.00),
    ("Mares_of_Diomedes",             3.00),
    ("Nemean_Lion",                   3.00),
    ("Colchian_Dragon",               3.00),
    ("Lernaean_Hydra",                3.00),
    ("Geryon",                        1.40),
    ("Chimera",                       1.40),
    ("Talos",                         1.40),
    ("Cerberus",                      1.40),
    ("Gigantes",                      1.40),
    ("Scylla_&_Charybdis",            0.75),
    ("Echidna",                       0.75),
    ("Hecatoncheires",                0.75),
    ("Typhon",                        0.75),
]

# Pre-compute weights list for random.choices
_MONSTER_NAMES   = [m[0] for m in _MONSTERS]
_MONSTER_WEIGHTS = [m[1] for m in _MONSTERS]          # percentages sum to 100

# ──────────────────────────────────────────────────────────────
#  BADGE FACTORY  (monster trophy • weekly laurel • ruck laurel)
# ──────────────────────────────────────────────────────────────
import re

def _slug(name: str) -> str:
    """Turn 'Satyrs & other woodland imps' → 'Satyrs_and_other_woodland_imps'."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return slug

def _award_badge(d: Dict[str, Any], kind: str) -> None:
    """
    kind must be one of:
      • 'microcycle' – give weighted monster trophy (10 % gilded)
      • 'weekly'     – Olympian laurel (every 7 training days)
      • 'ruck'       – Olympian laurel (every 25 mi rucked)
    """
    if kind == "microcycle":                     # ← trophy branch
        monster = random.choices(
            _MONSTER_NAMES,
            weights=_MONSTER_WEIGHTS,
            k=1
        )[0]
        slug    = _slug(monster)                       # use new slug
        folder  = slug
        gilded = random.random() < 0.10             # 10 % chance first
        variant = "Gold" if gilded else "Vibrant"
        art_path = f"{folder}/{variant}/{slug}.png"


        tier = d["microcycle"]["id"]             # 1, 2, 3…
        name = f"{monster} Trophy {tier}" + (" ✨" if gilded else "")

        badge = {
            "name":       name,
            "earned_on":  str(_today()),
            "type":       "monster",
            "image_path": art_path,
        }

    elif kind in ("weekly", "ruck"):             # ← laurel branch
        god, icon = random.choice(OLYMPIANS)
        tier = (
            str(d["streak"]["active_days"] // 7)
            if kind == "weekly"
            else str(int(d["total_ruck_miles"] // 25))
        )
        badge = {
            "name":       f"{icon} {god} Laurel {tier}",
            "earned_on":  str(_today()),
            "type":       "laurel",
            "image_path": None,
        }

    else:                                        # fallback
        badge = {
            "name":       "Unknown Badge",
            "earned_on":  str(_today()),
            "type":       kind,
            "image_path": None,
        }

    d["badges"].append(badge)

# ──────────────────────────────────────────────────────────────
import re

# ──────────────────────────────────────────────────────────────
def _check_ruck_milestone(d: Dict[str, Any],
                           prev_m: float,
                           new_m:  float) -> None:
    """
    Award every waypoint crossed between prev_m and new_m
    (handles multi-loop jumps, no duplicates, includes Acropolis at 0 mi).
    """

    prev_loop = int(prev_m // TRIP_MILES)
    new_loop  = int(new_m  // TRIP_MILES)

    # collect already-earned (loop, city) tuples  – works for old & new badges
    earned = set()
    for b in d["badges"]:
        if b.get("type") != "ruck_quest":
            continue

        if "stop" in b and "loop" in b:          # new format
            earned.add((b["loop"], b["stop"]))

        else:                                    # legacy badge – parse city
            m = re.search(r"📜\s+(.*?)\s+Way-Point", b.get("name", ""))
            city = m.group(1) if m else b.get("name")
            earned.add((0, city))                # assume loop 0

    # walk every loop crossed by this ruck
    for loop in range(prev_loop, new_loop + 1):
        base = loop * TRIP_MILES
        for city, offset in RUCK_STOPS:
            abs_mark = base + offset

            # NOTE:  <= for lower bound so Acropolis at 0 mi triggers
            if prev_m <= abs_mark <= new_m and (loop, city) not in earned:
                slug = city.replace(" ", "_")
                d["badges"].append({
                    "type":       "ruck_quest",
                    "loop":       loop,
                    "stop":       city,
                    "name":       f"📜 {city} Way-Point",
                    "earned_on":  str(_today()),
                    "caption":    RUCK_CAPTIONS.get(city, ""),
                    "image_path": f"Pheidippides/{slug}.png",
                })


def _inc_streak(d: Dict[str, Any]):
    today = str(_today())
    if d['streak']['last_date'] != today:
        d['streak']['active_days'] += 1
        d['streak']['last_date'] = today
        if d['streak']['active_days'] % 7 == 0:
            _award_badge(d, 'weekly')


def _maybe_award_cycle_badge(d: Dict[str, Any]) -> None:
    mc = d["microcycle"]
    if mc["badge_given"]:
        return                      # already awarded

    # 6 workouts finished?
    if mc["sessions_completed"] < SESSIONS_NEEDED:
        return

    # is today ≥ start_date + 13 ?
    start = dt.date.fromisoformat(mc["start_date"])
    if (_today() - start).days < MICROCYCLE_LEN - 1:
        return

    _award_badge(d, "microcycle")
    mc["badge_given"] = True        # prevent duplicates



# ──────────────────────────────────────────────────────────────
#  CORE OPERATIONS
# ──────────────────────────────────────────────────────────────

def init_track(key: str) -> str:
    d = _load()
    d["track"] = key
    d["microcycle"] = {
        "id": d["microcycle"]["id"] + 1,
        "sessions_completed": 0,
        "start_date": str(_today()),
        "badge_given": False,
    }
    _save(d)
    return f"🔥 Began {TEMPLATES[key]['name']}"



def get_today_workout() -> str:
    d = _load()
    idx = d["microcycle"]["sessions_completed"]
    if idx >= 6:
        return "Cycle finished – log custom or start new track."

    s = TEMPLATES[d["track"]]["sessions"][idx]
    accessories = "\n • ".join(s["accessory"])
    return (f"Main  – {s['main']}\n"
            f"Accessories:\n • {accessories}\n"
            f"Finisher – {s['finisher']}")



def log_rec() -> str:
    """Log the next recommended session for the active micro-cycle."""
    d = _load()

    idx = d["microcycle"]["sessions_completed"]
    sess = TEMPLATES[d["track"]]["sessions"][idx]
    details = sess["main"]                 # concise text for History pane

    # record in history
    d["workouts"].append({
        "date": str(_today()),
        "type": "recommended",
        "details": details,
    })

    # update counters and streaks
    d["microcycle"]["sessions_completed"] += 1
    _inc_streak(d)
    _maybe_award_cycle_badge(d)

    _save(d)
    return "✔ Recommended workout logged."





def log_custom(desc: str) -> str:
    if not desc.strip():
        return "Please describe your workout."

    d = _load()
    d["workouts"].append({
        "date": str(_today()),
        "type": "custom",
        "details": desc
    })
    d["microcycle"]["sessions_completed"] += 1
    _inc_streak(d)
    _maybe_award_cycle_badge(d)          # NEW
    _save(d)

    return "✔ Custom workout logged."


def log_ruck(mi: float, lbs: float) -> str:
    d    = _load()
    prev = d["total_ruck_miles"]
    new  = prev + mi

    # ─– treasury calc
    coins = round(mi * (1 + lbs * 0.01), 2)
    d["treasury"] += coins

    d["ruck_log"].append({"date": str(_today()),
                          "distance_miles": mi,
                          "weight_lbs": lbs,
                          "coins": coins})
    d["total_ruck_miles"] = new

    # 25-mile laurels (unchanged)
    # if int(prev // 25) < int(new // 25):
    #     _award_badge(d, "ruck")

    _check_ruck_milestone(d, prev, new)   # postcard quest
    _save(d)

    return f"🦯 Ruck logged — +{coins} drachma."

# ──────────────────────────────────────────────────────────────
#  GUI DEFINITION
# ──────────────────────────────────────────────────────────────
class KBApp(tk.Tk):
    """Main Tkinter window for the Olympus Training Log."""

    def __init__(self):
        super().__init__()
        self.badge_imgs: list[ImageTk.PhotoImage] = []

        # window basics
        self.title("Olympus Training Log")
        self.geometry("1520x820")
        self.configure(bg=BG_DARK)
        self.resizable(True, True)
        self.minsize(900, 700)

        # ▶  load coin.png at icon size (e.g., 32×32) and set as app icon
        raw_icon = Image.open("Pheidippides/coin.png").resize((32, 32), Image.NEAREST)
        self.app_icon = ImageTk.PhotoImage(raw_icon)   # keep reference on self
        self.iconphoto(False, self.app_icon)           # <--  window icon

        # style setup …
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG_DARK)
        style.configure("TLabel", background=BG_DARK, foreground=ACCENT_G)
        style.configure("TButton", background=ACCENT_G)
        # Notebook tab styling
        style.configure("TNotebook",           background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab",       background="#1a2f4a", foreground=ACCENT_G,
                                               padding=[12, 5], font=("Georgia", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", "#0d1b2a")],
                  foreground=[("selected", "#ffffff")])
        style.configure("Game.TFrame",         background=BG_DARK)

        # build UI and initial refreshes
        self._build_ui()
        self._refresh_badges()
        self._update_cycle_progress()
        self._update_streak_display()
        self._refresh_history()

    def _fill_scroll_box(self, column_frame, title, canvas_w=SIDE_CANVAS_W):
        """Populate a frame with a titled scroll-box and return (canvas, inner)."""
        ttk.Label(column_frame, text=title,
                  font=("Georgia", 12, "bold")).pack(pady=4)

        # use the passed-in width
        canvas = tk.Canvas(column_frame, bg=BG_LIGHT,
                           highlightthickness=0, width=canvas_w)
        vscroll = ttk.Scrollbar(column_frame, orient="vertical",
                                command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)

        vscroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="y", expand=False)

        # inner frame for badges
        inner = tk.Frame(canvas, bg=BG_LIGHT)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        return canvas, inner   # ← MAKE SURE THIS LINE IS PRESENT

    def _build_menu_pane(self, parent) -> None:
        """Training-menu treeview with vertical + horizontal scrollbars."""
        ttk.Label(parent, text="Training Menu",
                  font=("Georgia", 12, "bold")).pack(pady=4)

        # wrapper frame for scrollbars
        wrap = ttk.Frame(parent)
        wrap.pack(fill="both", expand=True)

        # three data columns + the tree column ("#0")
        cols = ("main", "accessory", "finisher")
        tree = ttk.Treeview(
            wrap,
            columns=cols,
            show="tree headings",    # show both tree & headers
            height=18
        )
    
        # column headers
        tree.heading("#0", text="Track / Date", anchor="w")
        tree.heading("main",      text="Main Lift",  anchor="w")
        tree.heading("accessory", text="Accessories", anchor="w")
        tree.heading("finisher",  text="Finisher",   anchor="w")

        # ─ column widths & wrapping (FIXED: use tree, not self.hist_tree) ─
        tree.column("#0",        width=120, stretch=False)
        tree.column("main",      width=200, stretch=False)
        tree.column("accessory", width=200, stretch=False)   # wider for list
        tree.column("finisher",  width=200, stretch=False)

        # scrollbars
        vsb = ttk.Scrollbar(wrap, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # layout inside wrapper (tree on top, h-scroll bottom)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")        # ← now in wrap, spans full width
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)


        # ── populate ────────────────────────────────────────────
        # ── populate ────────────────────────────────────────────
        for key, tpl in TEMPLATES.items():
            # root row = track; stays auto-expanded (open=True)
            root = tree.insert(
                "", "end",
                text=tpl["name"],
                open=True,
                tags=(key,)
            )

            # child rows = the six sessions
            for s in tpl["sessions"]:
                # parent row shows MAIN + FINISHER (leave accessory cell blank)
                parent = tree.insert(
                    root, "end",
                    values=(s["main"], "", s["finisher"]),
                    open=False          # start collapsed
                )

                # grand-child rows – each accessory on its own line
                for ac in s["accessory"]:
                    tree.insert(
                        parent, "end",
                        values=("", ac, "")      # blank main & finisher cells
                    )


        # click → select track & show preview
        def on_select(event):
            item = tree.focus()
            tags = tree.item(item, "tags")
            if tags:
                key = tags[0]
                self.track_var.set(key)
                self._write(preview_track(key))

        tree.bind("<<TreeviewSelect>>", on_select)

        # keep a reference so other methods can refresh it
        self.menu_tree = tree


    def _toggle_track(self):
        if self._cycle_active():          # ⇢ STOP
            d = _load()
            d["microcycle"] = {           # reset cycle
                "id": d["microcycle"]["id"] + 1,
                "sessions_completed": 0,
                "start_date": str(_today()),
                "badge_given": False,
            }
            _save(d)
            self._write("⏹  Track stopped; progress reset.")
        else:                             # ⇢ START
            msg = init_track(self.track_var.get())
            self._write(msg)

        # update label and any dependent UI
        self.track_btn_text.set("Stop Track" if self._cycle_active() else "Start Track")
        self._refresh_badges()
        self._update_cycle_progress()     # if you have this helper


    # ── UI builder ────────────────────────────────────────────
    def _build_ui(self):
        # ▸ Top bar: track selector
        bar = ttk.Frame(self)
        bar.pack(pady=6)

        ttk.Label(bar, text="Track:").pack(side="left")
        self.track_var = tk.StringVar(value=TRACK_KEYS[0])
        ttk.OptionMenu(bar, self.track_var, TRACK_KEYS[0], *TRACK_KEYS).pack(side="left")
        # text variable so we can change label at runtime
        self.track_btn_text = tk.StringVar()
        self.track_btn = ttk.Button(
            bar, textvariable=self.track_btn_text, command=self._toggle_track
        )
        self.track_btn.pack(side="left", padx=6)
        # initial label
        self.track_btn_text.set("Stop Track" if self._cycle_active() else "Start Track")

        # after you create the Track selector bar
        self.treasury_var = tk.StringVar(value="0 Drachma")

        # load once, then scale to 24 × 24 px (or 20 × 20 if you like)
        raw  = Image.open("Pheidippides/coin.png")
        icon = raw.resize((32, 32), Image.NEAREST)     # keeps pixel look
        self.coin_img = ImageTk.PhotoImage(icon)

        # ② place icon then numeric label (icon first looks nicer)
        tk.Label(bar, image=self.coin_img, bg=BG_DARK).pack(side="right", padx=(0,2))
        ttk.Label(bar, textvariable=self.treasury_var,
          font=("Georgia", 11, "bold")).pack(side="right")

        # ─ Weekly streak display ───────────────────────────────────
        self.streak_var  = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.streak_var,
                  font=("Georgia", 10, "italic")).pack(side="right", padx=12)


        # ─ Micro-cycle progress display ─────────────────────────────
        self.cycle_var   = tk.StringVar(value="Cycle 0 ▢▢▢▢▢▢ (0/6)")
        self.next_badge_var = tk.StringVar(value="")

        ttk.Label(bar, textvariable=self.cycle_var,
                  font=("Georgia", 10, "italic")).pack(side="right", padx=12)

        #ttk.Label(bar, textvariable=self.next_badge_var,
          #        font=("Georgia", 10)).pack(side="right")




        # Bottom control bar  (already after the Track bar)
        controls = ttk.Frame(self)
        controls.pack(side="bottom", fill="x", pady=6)

        # tell grid to give columns 0 and 6 all stretch room
        for col in (0, 6):
            controls.grid_columnconfigure(col, weight=1)

        # 1st row – centered buttons
        ttk.Button(controls, text="Show Workout",
                   command=lambda: self._write(get_today_workout())
                   ).grid(row=0, column=1, padx=4)

        ttk.Button(controls, text="Log Recommended",
                   command=lambda: self._write_and_refresh(log_rec)
                   ).grid(row=0, column=2, padx=4)

        ttk.Button(controls, text="Log Custom",
                   command=self._custom_dialog
                   ).grid(row=0, column=3, padx=4)

        # 2nd row – ruck inputs, still centered
        self.mi_var = tk.DoubleVar(value=0.0)
        self.lb_var = tk.DoubleVar(value=20)

        ttk.Label(controls, text="Miles:").grid(row=1, column=1, sticky="e")
        ttk.Entry(controls, textvariable=self.mi_var,
                  width=7).grid(row=1, column=2, sticky="w")

        ttk.Label(controls, text="Weight:").grid(row=1, column=3, sticky="e")
        ttk.Entry(controls, textvariable=self.lb_var,
                  width=7).grid(row=1, column=4, sticky="w")

        ttk.Button(controls, text="Log Ruck",
                   command=lambda: self._write_and_refresh(
                       lambda: log_ruck(self.mi_var.get(), self.lb_var.get()))
                   ).grid(row=1, column=5, padx=4)


        # ──────────────────────────────────────────────────────────────
        # Notebook with Training Log + Laurel of Olympus game tabs
        # ──────────────────────────────────────────────────────────────
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True, padx=8)

        # Training Log tab (hosts the existing layout)
        log_tab = ttk.Frame(self._notebook)
        self._notebook.add(log_tab, text="📋 Training Log")

        # Laurel of Olympus game tab
        try:
            from laurel_of_olympus.ui.game_tab import GameTab
            game_tab = GameTab(self._notebook)
            self._notebook.add(game_tab, text="🏛 Laurel of Olympus")
        except Exception as _game_err:
            fallback = ttk.Frame(self._notebook)
            ttk.Label(fallback, text=f"Game failed to load: {_game_err}").pack(pady=40)
            self._notebook.add(fallback, text="🏛 Laurel of Olympus")

        # All existing layout code uses 'content' — point it at the log tab
        content = log_tab

        # column weights: let centre column stretch, others fixed
        content.columnconfigure(1, weight=1)   # centre (log/menu/journey)
        content.rowconfigure(0, weight=3)      # log      ← taller
        content.rowconfigure(1, weight=1)      # menu     ← shorter
        content.rowconfigure(2, weight=1)      # journey

        # 0 ─ Temple of Triumphs (LEFT)
        temple_col = ttk.Frame(content, width=SIDE_COL_W)
        temple_col.grid(row=0, column=0, rowspan=3, sticky="ns")
        temple_col.grid_propagate(False)
        self.temple_canvas, self.temple_inner = self._fill_scroll_box(
            temple_col, "Temple of Triumphs"
        )

        # 1a ─ Workout Log (CENTRE - top)
        self.log_box = ScrolledText(
            content, width=60, bg=BG_LIGHT, wrap="word"
        )
        self.log_box.grid(row=0, column=1, sticky="nsew", padx=(6, 6))
        self.log_box.configure(state="disabled")

        # 1b ─ Training Menu (CENTRE - middle)
        menu_col = ttk.Frame(content)
        menu_col.grid(row=1, column=1, sticky="nsew", padx=(6, 6))
        self._build_menu_pane(menu_col)

        # 1c ─ Journey postcards (CENTRE - bottom)
        journey_col = ttk.Frame(content)
        journey_col.grid(row=2, column=1, sticky="nsew", padx=(6, 6))
        self.journey_canvas, self.journey_inner = self._fill_scroll_box(
            journey_col, "Pheidippides Journey", canvas_w=MENU_COL_W - 20
        )

        # 2 ─ Hall of Laurels (RIGHT of centre)
        laurel_col = ttk.Frame(content, width=SIDE_COL_W)
        laurel_col.grid(row=0, column=2, rowspan=3, sticky="ns")
        laurel_col.grid_propagate(False)
        self.laurel_canvas, self.laurel_inner = self._fill_scroll_box(
            laurel_col, "Hall of Laurels"
        )

        # 3 ─ History column (far RIGHT)
        hist_col = ttk.Frame(content, width=300)
        hist_col.grid(row=0, column=3, rowspan=3, sticky="ns")
        hist_col.grid_propagate(False)
        ...
        # (keep the existing Treeview code exactly as you already have it)


        ttk.Label(hist_col, text="History",
                  font=("Georgia", 12, "bold")).grid(row=0, column=0,
                                             columnspan=2, pady=4)

        cols = ("kind", "details")
        self.hist_tree = ttk.Treeview(hist_col, columns=cols,
                                      show="tree headings")
        self.hist_tree.heading("#0", text="Date", anchor="w")
        self.hist_tree.heading("kind", text="Type", anchor="w")
        self.hist_tree.heading("details", text="Details", anchor="w")
        self.hist_tree.column("kind", width=80, stretch=False)
        self.hist_tree.column("details", width=240, stretch=True)

        vscroll = ttk.Scrollbar(hist_col, orient="vertical",
                                command=self.hist_tree.yview)
        hscroll = ttk.Scrollbar(hist_col, orient="horizontal",
                                command=self.hist_tree.xview)
  
        # grid layout
        self.hist_tree.grid(row=1, column=0, sticky="nsew")
        vscroll.grid(row=1, column=1, sticky="ns")
        hscroll.grid(row=2, column=0, columnspan=2, sticky="ew")

        self.hist_tree.configure(yscrollcommand=vscroll.set,
                                  xscrollcommand=hscroll.set)

        # make tree area expandable
        hist_col.grid_rowconfigure(1, weight=1)
        hist_col.grid_columnconfigure(0, weight=1)

    # ── Helpers ───────────────────────────────────────────────
    def _write(self, msg: str):
        """Append a message to the workout log."""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n\n")
        self.log_box.configure(state="disabled")
        self.log_box.see("end")

    def _write_and_refresh(self, func):
        """Run func(), write its return string, then refresh UI widgets."""
        self._write(func())           # append text to log pane
        self._refresh_badges()        # redraw laurels / trophies / postcards
        self._update_cycle_progress() # micro-cycle bar
        self._update_streak_display() # ← ADD THIS LINE
        self._refresh_history()          # NEW

    def _custom_dialog(self):
        """Prompt for a custom workout description."""
        desc = simpledialog.askstring("Custom Workout", "Describe your workout:")
        if desc:
            self._write_and_refresh(lambda: log_custom(desc))

    def _update_cycle_progress(self):
        d  = _load()
        mc = d["microcycle"]

        # ▸ Nothing underway? show idle message and exit
        if mc["id"] == 0 and mc["sessions_completed"] == 0:
            self.cycle_var.set("No active cycle")
            self.next_badge_var.set("")
            return

        done = mc["sessions_completed"]
        blocks = "▣" * min(done, 6) + "▢" * (6 - min(done, 6))
        self.cycle_var.set(f"Cycle {mc['id']}  {blocks}  ({done}/6)")

        # compute badge date
        start = dt.date.fromisoformat(mc["start_date"])
        award_date = start + dt.timedelta(days=13)   # last day of week 2

        # build suffix for badge status
        if mc["badge_given"]:
            suffix = " – ✔ badge earned"
        elif mc["sessions_completed"] >= SESSIONS_NEEDED:
            suffix = f" – Badge on {award_date.strftime('%b%d').upper()}"
        else:
            suffix = ""

        # put everything in ONE label
        self.cycle_var.set(
            f"Cycle {mc['id']}  {blocks}  ({done}/6){suffix}"
        )

    def _update_streak_display(self):
        """
        Show progress toward 3 workouts in the current ISO week
        and the coming badge date (end-of-week Sunday).
        """
        d = _load()
        today = _today()
        year, week, _ = today.isocalendar()

        # count *workouts* (rec + custom) logged this ISO week
        workouts_this_week = sum(
            1
            for w in d["workouts"]
            if dt.date.fromisoformat(w["date"]).isocalendar()[:2] == (year, week)
        )

        done  = min(workouts_this_week, TARGET_WK_WORKOUTS)
        blocks = "✔" * done + "▢" * (TARGET_WK_WORKOUTS - done)

        # find this week's Sunday
        days_to_sun = 7 - today.isoweekday()
        sunday = today + dt.timedelta(days=days_to_sun)

        if done < TARGET_WK_WORKOUTS:
            badge_msg = f"{TARGET_WK_WORKOUTS - done} to go"
        else:
            badge_msg = f"laurel on {sunday.strftime('%b%d').upper()}"


        self.streak_var.set(f"Streak {blocks}  ({done}/{TARGET_WK_WORKOUTS}) – {badge_msg}")
    # place near the other helpers
    def _cycle_active(self) -> bool:
        d = _load()
        mc = d["microcycle"]
        return mc["sessions_completed"] > 0 and not mc["badge_given"]


    def _refresh_history(self):
        """Rebuild the History tree; never crash if a key is missing."""
        self.hist_tree.delete(*self.hist_tree.get_children())

        d = _load()
        bucket = collections.defaultdict(list)

        # ─ workouts ────────────────────────────────────────────────
        for w in d["workouts"]:
            date    = w.get("date")
            details = w.get("details") or w.get("name") or w.get("type", "")
            kind    = w.get("type", "workout")
            if date:                                  # skip malformed rows
                bucket[date].append((kind, details))
  
        # ─ rucks ──────────────────────────────────────────────────
        for r in d["ruck_log"]:
            date = r.get("date")
            if date:
                details = f"{r['distance_miles']} mi @ {r['weight_lbs']} lb"
                bucket[date].append(("ruck", details))

        # newest dates first
        for date in sorted(bucket.keys(), reverse=True):
            parent = self.hist_tree.insert("", "end", text=date, open=True)  # auto-expanded
            for kind, details in bucket[date]:
                self.hist_tree.insert(parent, "end", values=(kind, details))



    # ─────────────────────────────────────────
    # ─────────────────────────────────────────
    def _refresh_badges(self):
        """Redraw monster trophies and laurel awards in their own panes."""
        # wipe previous widgets
        for pane in (self.temple_inner, self.laurel_inner, self.journey_inner):
            for w in pane.winfo_children():
                w.destroy()
        self.badge_imgs.clear()          # keep Tk images alive

        # newest badge first
        for b in reversed(_load()["badges"]):
            # choose destination pane
            target = (
                self.temple_inner if b["type"] == "monster"
                else self.laurel_inner if b["type"] == "laurel"
                else self.journey_inner        # ruck_quest
            )

            plaque = tk.Frame(target, bg=ACCENT_G, pady=2)

            # ─ image handling ──────────────────────────────────────
            if b.get("image_path"):
                img_path = Path.cwd() / b["image_path"]
                if img_path.exists():
                    pil = Image.open(img_path)

                    # size rules: monster = 48×48, postcard = scale to 60-px width
                    if b["type"] == "monster":
                        pil = pil.resize((48, 48), Image.NEAREST)
                    else:  # ruck_quest postcard
                        target_w = 80
                        w, h = pil.size
                        pil = pil.resize((target_w, int(h * target_w / w)), Image.NEAREST)

                    tk_img = ImageTk.PhotoImage(pil)
                    self.badge_imgs.append(tk_img)     # prevent GC
                    tk.Label(plaque, image=tk_img, bg=ACCENT_G).pack(side="left", padx=4)

            # ─ title text ─
            tk.Label(plaque, text=b["name"],
                     bg=ACCENT_G, font=("Georgia", 10, "bold")
                     ).pack(anchor="w", padx=2)

            # ─ optional caption for postcards ─
            if b["type"] == "ruck_quest" and b.get("caption"):
                tk.Label(plaque, text=b["caption"],
                         bg=ACCENT_G, wraplength=220, justify="left",
                         font=("Georgia", 9)
                         ).pack(anchor="w", padx=2, pady=(0, 2))

            plaque.pack(fill="x", pady=2, padx=4)

        self.treasury_var.set(f"{_load()['treasury']:.2f} drachma")

# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    KBApp().mainloop()
