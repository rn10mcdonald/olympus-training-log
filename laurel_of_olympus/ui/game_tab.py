"""
game_tab.py – Main "Laurel of Olympus" tab frame.

Layout:
  ┌─────────────────────────────────────────────────────────┐
  │  ResourceBar  (top strip)                               │
  ├──────────────────────────────┬──────────────────────────┤
  │                              │                          │
  │   EstateGrid  (canvas)       │   EventLog               │
  │                              │                          │
  ├──────────────────────────────┤                          │
  │   Control panel              │                          │
  │   [Simulate Workout] [Build] │                          │
  └──────────────────────────────┴──────────────────────────┘

Controls:
  - Simulate Workout → opens WorkoutDialog → runs engines → refreshes UI
  - Build Farm       → opens a simple farm-type chooser
  - Save / Load      → manual save/load buttons
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from laurel_of_olympus import game_state as gs
from laurel_of_olympus.game_state import PlayerState
from laurel_of_olympus.workout_engine import process_workout
from laurel_of_olympus.farm_engine import produce_farms, should_produce_today
from laurel_of_olympus.ui.resource_bar import ResourceBar
from laurel_of_olympus.ui.estate_grid import EstateGrid
from laurel_of_olympus.ui.event_log import EventLog
from laurel_of_olympus.ui.workout_dialog import WorkoutDialog

# ── Palette ──────────────────────────────────────────────────────────────────
BG_DARK  = "#0d1b2a"
BG_MID   = "#162538"
BG_PANEL = "#1a2f4a"
ACCENT_G = "#c9b037"
FG_LIGHT = "#e0d6c2"

# Farm build costs (drachmae) from balance_table.txt
_BUILD_COSTS = {
    "grain_field": 250,
    "vineyard":    300,
    "olive_grove": 300,
    "apiary":      350,
    "herb_garden": 275,
}

_FARM_NAMES = {
    "grain_field": "🌾 Grain Field",
    "vineyard":    "🍇 Vineyard",
    "olive_grove": "🫒 Olive Grove",
    "apiary":      "🍯 Apiary",
    "herb_garden": "🌱 Herb Garden",
}


class GameTab(ttk.Frame):
    """Top-level frame for the Laurel of Olympus game tab."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.configure(style="Game.TFrame")

        self._state: PlayerState = gs.load()
        self._build_ui()
        self._full_refresh()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=3)   # left: grid + controls
        self.columnconfigure(1, weight=1)   # right: event log
        self.rowconfigure(0, weight=0)      # resource bar
        self.rowconfigure(1, weight=1)      # grid
        self.rowconfigure(2, weight=0)      # controls

        # ── Resource bar (row 0, full width) ──────────────────────────────────
        resource_frame = tk.Frame(self, bg=BG_MID, pady=4)
        resource_frame.grid(row=0, column=0, columnspan=2, sticky="ew")

        self._resource_bar = ResourceBar(resource_frame, style="Game.TFrame")
        self._resource_bar.pack(side="left", fill="x", expand=True, padx=8)

        # Save/Load buttons in resource bar
        ttk.Button(resource_frame, text="💾 Save",
                   command=self._save).pack(side="right", padx=4)
        ttk.Button(resource_frame, text="📂 Load",
                   command=self._load).pack(side="right", padx=4)

        # ── Estate grid (row 1, left column) ──────────────────────────────────
        grid_frame = tk.Frame(self, bg=BG_PANEL)
        grid_frame.grid(row=1, column=0, sticky="nsew", padx=(6, 3), pady=6)

        tk.Label(
            grid_frame, text="Estate",
            bg=BG_PANEL, fg=ACCENT_G,
            font=("Georgia", 11, "bold"),
        ).pack(anchor="w", padx=8, pady=(6, 2))

        self._estate_grid = EstateGrid(grid_frame, bg=BG_PANEL)
        self._estate_grid.pack(padx=6, pady=(0, 6))

        # ── Event log (rows 1-2, right column) ────────────────────────────────
        log_frame = tk.Frame(self, bg=BG_PANEL)
        log_frame.grid(row=1, column=1, rowspan=2, sticky="nsew", padx=(3, 6), pady=6)

        tk.Label(
            log_frame, text="Event Log",
            bg=BG_PANEL, fg=ACCENT_G,
            font=("Georgia", 11, "bold"),
        ).pack(anchor="w", padx=8, pady=(6, 2))

        self._event_log = EventLog(log_frame, bg=BG_DARK)
        self._event_log.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # ── Control panel (row 2, left column) ────────────────────────────────
        ctrl = tk.Frame(self, bg=BG_MID)
        ctrl.grid(row=2, column=0, sticky="ew", padx=(6, 3), pady=(0, 6))

        # Left controls: workout simulation
        workout_section = tk.Frame(ctrl, bg=BG_MID)
        workout_section.pack(side="left", padx=12, pady=8)

        tk.Label(
            workout_section, text="Workout",
            bg=BG_MID, fg=ACCENT_G, font=("Georgia", 10, "bold"),
        ).pack(anchor="w")

        ttk.Button(
            workout_section, text="⚡ Simulate Workout",
            command=self._open_workout_dialog,
        ).pack(side="left", padx=(0, 6))

        # Middle controls: farm building
        farm_section = tk.Frame(ctrl, bg=BG_MID)
        farm_section.pack(side="left", padx=12, pady=8)

        tk.Label(
            farm_section, text="Build",
            bg=BG_MID, fg=ACCENT_G, font=("Georgia", 10, "bold"),
        ).pack(anchor="w")

        self._farm_type_var = tk.StringVar(value="grain_field")
        farm_combo = ttk.Combobox(
            farm_section,
            textvariable=self._farm_type_var,
            values=list(_FARM_NAMES.keys()),
            state="readonly",
            width=14,
        )
        farm_combo.pack(side="left", padx=(0, 4))

        # Show display name in combo
        farm_combo.bind("<<ComboboxSelected>>", lambda _: None)

        ttk.Button(
            farm_section, text="🏗 Build Farm",
            command=self._build_farm,
        ).pack(side="left")

        # Cost display
        self._cost_var = tk.StringVar()
        tk.Label(
            farm_section, textvariable=self._cost_var,
            bg=BG_MID, fg="#aaaaaa", font=("Georgia", 9),
        ).pack(side="left", padx=8)
        self._update_cost_label()
        self._farm_type_var.trace_add("write", lambda *_: self._update_cost_label())

        # Right: stats summary
        stats_section = tk.Frame(ctrl, bg=BG_MID)
        stats_section.pack(side="right", padx=12, pady=8)

        self._stats_var = tk.StringVar()
        tk.Label(
            stats_section, textvariable=self._stats_var,
            bg=BG_MID, fg=FG_LIGHT, font=("Georgia", 9),
            justify="left",
        ).pack(anchor="w")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _open_workout_dialog(self) -> None:
        WorkoutDialog(self, on_submit=self._simulate_workout)

    def _simulate_workout(self, workout_type: str, **kwargs) -> None:
        """Called by WorkoutDialog on confirm. Runs engines and refreshes."""
        events = []

        # 1. Farm production (once per day, on first workout)
        farm_events = produce_farms(self._state)
        if farm_events:
            events.extend(farm_events)
        elif should_produce_today(self._state):
            pass  # no farms yet, silently skip

        # 2. Workout reward
        workout_events = process_workout(self._state, workout_type, **kwargs)
        events.extend(workout_events)

        # 3. Log to event log
        self._event_log.log_separator()
        self._event_log.log_events(events)

        # 4. Print to stdout as well (design spec)
        for evt in events:
            print(f"[LaurelOfOlympus] {evt}")

        # 5. Auto-save and refresh
        gs.save(self._state)
        self._full_refresh()

    def _build_farm(self) -> None:
        farm_type = self._farm_type_var.get()
        cost = _BUILD_COSTS.get(farm_type, 0)

        if self._state.drachmae < cost:
            messagebox.showwarning(
                "Insufficient Drachmae",
                f"Building a {_FARM_NAMES[farm_type]} costs {cost} drachmae.\n"
                f"You have {self._state.drachmae:.1f} drachmae.\n\n"
                f"Simulate more workouts to earn drachmae!",
                parent=self,
            )
            return

        placed = self._estate_grid.add_farm_interactive(self._state, farm_type)

        if not placed:
            messagebox.showinfo(
                "No Farm Slots",
                "All farm plots are occupied. (Max 14 farms.)",
                parent=self,
            )
            return

        self._state.drachmae = round(self._state.drachmae - cost, 2)

        self._event_log.log_separator(timestamp=False)
        self._event_log.log(
            f"[Build] {_FARM_NAMES[farm_type]} constructed for {cost} drachmae.",
            "system",
        )
        print(f"[LaurelOfOlympus] Built {farm_type} for {cost} drachmae.")

        gs.save(self._state)
        self._full_refresh()

    def _save(self) -> None:
        gs.save(self._state)
        self._event_log.log("[System] Game saved.", "system")

    def _load(self) -> None:
        self._state = gs.load()
        self._full_refresh()
        self._event_log.log("[System] Game loaded.", "system")

    # ── Refresh helpers ───────────────────────────────────────────────────────

    def _full_refresh(self) -> None:
        self._resource_bar.refresh(self._state)
        self._estate_grid.refresh(self._state)
        self._update_stats()
        self._update_cost_label()

    def _update_stats(self) -> None:
        s = self._state
        lines = [
            f"Workouts: {s.total_workouts}",
            f"Farms:    {s.farms_built}",
            f"Laurels:  {s.laurels}",
        ]
        self._stats_var.set("\n".join(lines))

    def _update_cost_label(self) -> None:
        farm_type = self._farm_type_var.get()
        cost = _BUILD_COSTS.get(farm_type, 0)
        name = _FARM_NAMES.get(farm_type, farm_type)
        self._cost_var.set(f"{name}: {cost} ₯")
