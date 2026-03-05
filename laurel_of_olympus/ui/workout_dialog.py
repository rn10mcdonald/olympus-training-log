"""
workout_dialog.py – Modal dialog for simulating a workout.

Shows relevant input fields based on the selected workout type.
Calls on_submit(workout_type, **kwargs) on confirmation.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Any

BG_DARK  = "#0d1b2a"
BG_MID   = "#162538"
ACCENT_G = "#c9b037"
FG_LIGHT = "#e0d6c2"

_WORKOUT_TYPES = ["walking", "running", "rucking", "strength"]

_ICONS = {
    "walking":  "🚶",
    "running":  "🏃",
    "rucking":  "🎒",
    "strength": "🏋️",
}

_DESCRIPTIONS = {
    "walking":  "Base 10 + 2 per mile",
    "running":  "Base 15 + 3 per mile",
    "rucking":  "Base 20 + 4 per mile + 1 per 10 lbs",
    "strength": "Base 18 + volume ÷ 400  (volume = weight × reps × sets)",
}


class WorkoutDialog(tk.Toplevel):
    """
    Modal workout simulation dialog.

    Usage:
        WorkoutDialog(parent, on_submit=callback)

    Callback signature:
        callback(workout_type: str, **kwargs)
    """

    def __init__(self, parent: tk.Widget, on_submit: Callable) -> None:
        super().__init__(parent)
        self._on_submit = on_submit

        self.title("Simulate Workout")
        self.resizable(False, False)
        self.configure(bg=BG_DARK)
        self.grab_set()   # modal

        # Centre over parent
        self.transient(parent)
        self.update_idletasks()
        pw = parent.winfo_rootx()
        py = parent.winfo_rooty()
        self.geometry(f"+{pw + 80}+{py + 80}")

        self._type_var    = tk.StringVar(value="running")
        self._miles_var   = tk.DoubleVar(value=3.0)
        self._lbs_var     = tk.DoubleVar(value=20.0)
        self._volume_var  = tk.IntVar(value=5000)

        self._build()
        self._update_fields()

    def _build(self) -> None:
        pad = {"padx": 14, "pady": 6}

        # ── Header ────────────────────────────────────────────────────────────
        tk.Label(
            self, text="Simulate Workout",
            bg=BG_DARK, fg=ACCENT_G,
            font=("Georgia", 14, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=(14, 4))

        # ── Workout type ──────────────────────────────────────────────────────
        tk.Label(self, text="Type:", bg=BG_DARK, fg=FG_LIGHT,
                 font=("Georgia", 11)).grid(row=1, column=0, sticky="e", **pad)

        type_frame = tk.Frame(self, bg=BG_DARK)
        type_frame.grid(row=1, column=1, sticky="w", **pad)
        for wt in _WORKOUT_TYPES:
            tk.Radiobutton(
                type_frame,
                text=f"{_ICONS[wt]} {wt.title()}",
                variable=self._type_var,
                value=wt,
                bg=BG_DARK, fg=FG_LIGHT,
                selectcolor=BG_MID,
                activebackground=BG_DARK,
                font=("Georgia", 10),
                command=self._update_fields,
            ).pack(anchor="w")

        # ── Description label ─────────────────────────────────────────────────
        self._desc_var = tk.StringVar()
        tk.Label(
            self, textvariable=self._desc_var,
            bg=BG_DARK, fg="#888888",
            font=("Georgia", 9, "italic"),
            wraplength=280,
        ).grid(row=2, column=0, columnspan=2, pady=(0, 6))

        # ── Distance field ────────────────────────────────────────────────────
        self._miles_label = tk.Label(
            self, text="Distance (miles):",
            bg=BG_DARK, fg=FG_LIGHT, font=("Georgia", 11),
        )
        self._miles_entry = ttk.Entry(self, textvariable=self._miles_var, width=10)

        # ── Weight field ──────────────────────────────────────────────────────
        self._lbs_label = tk.Label(
            self, text="Weight carried (lbs):",
            bg=BG_DARK, fg=FG_LIGHT, font=("Georgia", 11),
        )
        self._lbs_entry = ttk.Entry(self, textvariable=self._lbs_var, width=10)

        # ── Volume field ──────────────────────────────────────────────────────
        self._vol_label = tk.Label(
            self, text="Volume (wt × reps × sets):",
            bg=BG_DARK, fg=FG_LIGHT, font=("Georgia", 11),
        )
        self._vol_entry = ttk.Entry(self, textvariable=self._volume_var, width=10)

        # ── Preview label ─────────────────────────────────────────────────────
        self._preview_var = tk.StringVar()
        tk.Label(
            self, textvariable=self._preview_var,
            bg=BG_DARK, fg=ACCENT_G,
            font=("Georgia", 12, "bold"),
        ).grid(row=7, column=0, columnspan=2, pady=6)

        # Bind variable traces to update preview
        self._miles_var.trace_add("write", lambda *_: self._update_preview())
        self._lbs_var.trace_add("write",   lambda *_: self._update_preview())
        self._volume_var.trace_add("write", lambda *_: self._update_preview())

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=BG_DARK)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=12)

        ttk.Button(
            btn_frame, text="Simulate",
            command=self._submit,
        ).pack(side="left", padx=8)

        ttk.Button(
            btn_frame, text="Cancel",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _update_fields(self) -> None:
        """Show / hide input fields based on workout type."""
        wt = self._type_var.get()

        self._desc_var.set(_DESCRIPTIONS.get(wt, ""))

        # Hide all first
        for widget in (
            self._miles_label, self._miles_entry,
            self._lbs_label,   self._lbs_entry,
            self._vol_label,   self._vol_entry,
        ):
            widget.grid_remove()

        if wt in ("walking", "running", "rucking"):
            self._miles_label.grid(row=3, column=0, sticky="e", padx=14, pady=4)
            self._miles_entry.grid(row=3, column=1, sticky="w", padx=14, pady=4)

        if wt == "rucking":
            self._lbs_label.grid(row=4, column=0, sticky="e", padx=14, pady=4)
            self._lbs_entry.grid(row=4, column=1, sticky="w", padx=14, pady=4)

        if wt == "strength":
            self._vol_label.grid(row=5, column=0, sticky="e", padx=14, pady=4)
            self._vol_entry.grid(row=5, column=1, sticky="w", padx=14, pady=4)

        self._update_preview()

    def _kwargs(self) -> Dict[str, Any]:
        wt = self._type_var.get()
        kw: Dict[str, Any] = {}
        try:
            if wt in ("walking", "running", "rucking"):
                kw["miles"] = float(self._miles_var.get())
            if wt == "rucking":
                kw["lbs"] = float(self._lbs_var.get())
            if wt == "strength":
                kw["volume"] = float(self._volume_var.get())
        except (tk.TclError, ValueError):
            pass
        return kw

    def _update_preview(self) -> None:
        """Show estimated reward in real time."""
        try:
            from laurel_of_olympus.workout_engine import calculate_reward
            wt = self._type_var.get()
            kw = self._kwargs()
            reward = calculate_reward(wt, **kw)
            self._preview_var.set(f"Estimated reward: {reward:.0f} drachmae")
        except Exception:
            self._preview_var.set("")

    def _submit(self) -> None:
        wt = self._type_var.get()
        kw = self._kwargs()
        self.destroy()
        self._on_submit(wt, **kw)
