"""
event_log.py – Scrolled text widget for game events.

Supports colour-coded message categories using tk text tags.
"""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from typing import List

BG = "#0d1b2a"
FG_DEFAULT  = "#e0d6c2"
FG_REWARD   = "#f4d03f"   # gold – drachmae reward
FG_FARM     = "#27ae60"   # green – farm production
FG_LAUREL   = "#c9b037"   # laurel gold – laurel events
FG_SYSTEM   = "#5dade2"   # blue – system / info
FG_WARNING  = "#e74c3c"   # red – warnings


class EventLog(ScrolledText):
    """Read-only scrolled text widget with category-based colour coding."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        kwargs.setdefault("width",  38)
        kwargs.setdefault("height", 22)
        kwargs.setdefault("bg",     BG)
        kwargs.setdefault("fg",     FG_DEFAULT)
        kwargs.setdefault("font",   ("Courier", 10))
        kwargs.setdefault("wrap",   "word")
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("bd",     0)
        super().__init__(parent, **kwargs)
        self.configure(state="disabled")

        # Colour tags
        self.tag_config("reward",  foreground=FG_REWARD)
        self.tag_config("farm",    foreground=FG_FARM)
        self.tag_config("laurel",  foreground=FG_LAUREL)
        self.tag_config("system",  foreground=FG_SYSTEM)
        self.tag_config("warning", foreground=FG_WARNING)
        self.tag_config("muted",   foreground="#666666")
        self.tag_config("bold",    font=("Courier", 10, "bold"))

    # ── Public API ────────────────────────────────────────────────────────────

    def log(self, message: str, tag: str = "") -> None:
        """Append a single line to the log."""
        self.configure(state="normal")
        self.insert("end", message + "\n", tag or ())
        self.configure(state="disabled")
        self.see("end")

    def log_events(self, events: List[str]) -> None:
        """
        Append a list of event strings, auto-detecting their category
        for colour coding.
        """
        for evt in events:
            tag = _detect_tag(evt)
            self.log(evt, tag)

    def log_separator(self, timestamp: bool = True) -> None:
        """Insert a visual separator, optionally with a timestamp."""
        when = f"  {dt.datetime.now().strftime('%H:%M:%S')}" if timestamp else ""
        self.log(f"─── {when} {'─' * max(0, 28 - len(when))}", "muted")

    def log_section(self, title: str) -> None:
        """Insert a bold section header."""
        self.configure(state="normal")
        self.insert("end", f"\n{title}\n", ("bold", "system"))
        self.configure(state="disabled")
        self.see("end")

    def clear(self) -> None:
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _detect_tag(msg: str) -> str:
    low = msg.lower()
    if "drachmae" in low or "reward" in low:
        return "reward"
    if "farm" in low or "harvest" in low or "grain" in low or "grape" in low:
        return "farm"
    if "laurel" in low or "★" in msg:
        return "laurel"
    if "warning" in low or "error" in low or "failed" in low:
        return "warning"
    if msg.startswith("  ↳"):
        return "muted"
    return ""
