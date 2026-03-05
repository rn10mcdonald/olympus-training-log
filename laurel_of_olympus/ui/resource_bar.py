"""
resource_bar.py – Horizontal resource display bar.

Shows: Drachmae · Laurels · Grain · Grapes · Olives · Honey · Herbs
Updates via refresh(state) when game state changes.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

from laurel_of_olympus.game_state import PlayerState

# ── Palette (matches main app) ───────────────────────────────────────────────
BG_DARK  = "#0d1b2a"
ACCENT_G = "#c9b037"
BG_MID   = "#162538"

# Resource definitions: (attribute_name, icon, label, color)
_RESOURCES = [
    ("drachmae",  "🪙", "Drachmae", "#f4d03f"),
    ("laurels",   "🌿", "Laurels",  "#27ae60"),
    ("grain",     "🌾", "Grain",    "#e8c84a"),
    ("grapes",    "🍇", "Grapes",   "#9b59b6"),
    ("olives",    "🫒", "Olives",   "#6b8e5e"),
    ("honey",     "🍯", "Honey",    "#f39c12"),
    ("herbs",     "🌱", "Herbs",    "#2ecc71"),
]


class ResourceBar(ttk.Frame):
    """Horizontal bar showing all player resources."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.configure(style="ResourceBar.TFrame")

        self._vars: Dict[str, tk.StringVar] = {}

        self._build()

    def _build(self) -> None:
        # Title label on the far left
        tk.Label(
            self, text="ESTATE",
            bg=BG_MID, fg=ACCENT_G,
            font=("Georgia", 10, "bold"),
            padx=8,
        ).pack(side="left")

        # One chip per resource
        for attr, icon, label, color in _RESOURCES:
            var = tk.StringVar(value="0")
            self._vars[attr] = var

            chip = tk.Frame(self, bg=BG_MID, padx=6, pady=2)
            chip.pack(side="left", padx=4)

            tk.Label(
                chip, text=icon,
                bg=BG_MID, font=("TkDefaultFont", 14),
            ).pack(side="left")

            tk.Label(
                chip, textvariable=var,
                bg=BG_MID, fg=color,
                font=("Georgia", 11, "bold"),
            ).pack(side="left", padx=(2, 0))

            tk.Label(
                chip, text=label,
                bg=BG_MID, fg="#aaaaaa",
                font=("Georgia", 9),
            ).pack(side="left", padx=(2, 0))

    def refresh(self, state: PlayerState) -> None:
        """Update all resource labels from the current state."""
        for attr, _icon, _label, _color in _RESOURCES:
            val = getattr(state, attr, 0)
            if isinstance(val, float):
                self._vars[attr].set(f"{val:.1f}")
            else:
                self._vars[attr].set(str(val))
