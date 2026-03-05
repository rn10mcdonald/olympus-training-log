"""
estate_grid.py – Canvas-based estate grid renderer.

Draws a 7-column × 5-row grid of tiles.
Each tile is a coloured rectangle with a text label.

Zones (rows):
  Row 0      – Top zone: Villa (col 3) + sanctuary placeholder
  Rows 1-2   – Middle zone: farm plots
  Row 3      – Lower zone: processing buildings
  Row 4      – Edge zone: road leading to campaign map

Call refresh(state) to redraw based on PlayerState.farms.
"""

from __future__ import annotations

import tkinter as tk
from typing import Dict, List, Tuple

from laurel_of_olympus.game_state import PlayerState

# ── Tile sizing ───────────────────────────────────────────────────────────────
COLS = 7
ROWS = 5
TILE_W = 92
TILE_H = 72
PAD = 4
CANVAS_W = COLS * (TILE_W + PAD) + PAD
CANVAS_H = ROWS * (TILE_H + PAD) + PAD

# ── Tile colours ─────────────────────────────────────────────────────────────
TILE_COLORS: Dict[str, str] = {
    "empty":        "#4a7c59",   # olive-tinted grass
    "villa":        "#d4c5a0",   # marble cream
    "sanctuary":    "#c9b037",   # gold
    "road":         "#8c7156",   # dirt path
    # Farms
    "grain_field":  "#e8c84a",   # golden yellow
    "vineyard":     "#9b59b6",   # grape purple
    "olive_grove":  "#6b8e5e",   # olive green (darker than empty)
    "apiary":       "#f39c12",   # honey orange
    "herb_garden":  "#27ae60",   # herb green
    # Processing buildings
    "winery":       "#7d3c98",   # deep purple
    "bakery":       "#ca6f1e",   # bread brown
    "olive_press":  "#5d6d7e",   # stone grey
    "meadery":      "#d4ac0d",   # mead gold
    "processing_empty": "#2e4057",  # dark placeholder
}

TILE_LABELS: Dict[str, str] = {
    "empty":            "",
    "villa":            "🏛 Villa",
    "sanctuary":        "🌿 Sanctuary",
    "road":             "— Road —",
    "grain_field":      "🌾 Grain",
    "vineyard":         "🍇 Vineyard",
    "olive_grove":      "🫒 Olives",
    "apiary":           "🍯 Apiary",
    "herb_garden":      "🌱 Herbs",
    "winery":           "🍷 Winery",
    "bakery":           "🍞 Bakery",
    "olive_press":      "🫒 Olive Press",
    "meadery":          "🍯 Meadery",
    "processing_empty": "(empty)",
}

# ── Farm plot slots: (col, row) positions available for farms ─────────────────
FARM_SLOTS: List[Tuple[int, int]] = [
    (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1),
    (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2),
]

# ── Processing slots: (col, row) positions ───────────────────────────────────
PROCESSING_SLOTS: List[Tuple[int, int]] = [
    (0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3),
]


class EstateGrid(tk.Canvas):
    """Canvas widget that renders the estate as a grid of coloured tiles."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        kwargs.setdefault("width",  CANVAS_W)
        kwargs.setdefault("height", CANVAS_H)
        kwargs.setdefault("bg",     "#1a2f4a")
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)

        self._tile_items: Dict[Tuple[int, int], int] = {}   # (col,row) → canvas rect id
        self._label_items: Dict[Tuple[int, int], int] = {}  # (col,row) → canvas text id
        self._level_items: Dict[Tuple[int, int], int] = {}  # (col,row) → level text id

        self._build_base_grid()

    # ── Initial grid ──────────────────────────────────────────────────────────

    def _build_base_grid(self) -> None:
        """Draw the static base layout (villa, road, empty slots)."""
        for row in range(ROWS):
            for col in range(COLS):
                tile_type = self._base_tile_type(col, row)
                self._draw_tile(col, row, tile_type)

    def _base_tile_type(self, col: int, row: int) -> str:
        if row == 0:
            if col == 3:
                return "villa"
            if col == 5:
                return "sanctuary"
            return "empty"
        if row in (1, 2):
            return "empty"   # farm plot (unfilled)
        if row == 3:
            return "processing_empty"
        if row == 4:
            return "road"
        return "empty"

    def _tile_xy(self, col: int, row: int) -> Tuple[int, int, int, int]:
        """Return (x0, y0, x1, y1) for a tile at (col, row)."""
        x0 = PAD + col * (TILE_W + PAD)
        y0 = PAD + row * (TILE_H + PAD)
        return x0, y0, x0 + TILE_W, y0 + TILE_H

    def _draw_tile(self, col: int, row: int, tile_type: str, level: int = 0) -> None:
        color = TILE_COLORS.get(tile_type, TILE_COLORS["empty"])
        label = TILE_LABELS.get(tile_type, "")

        x0, y0, x1, y1 = self._tile_xy(col, row)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2

        # Background rectangle
        existing_rect = self._tile_items.get((col, row))
        if existing_rect:
            self.itemconfig(existing_rect, fill=color, outline="#1a2f4a")
        else:
            rid = self.create_rectangle(
                x0, y0, x1, y1,
                fill=color, outline="#1a2f4a", width=2,
            )
            self._tile_items[(col, row)] = rid

        # Label text
        existing_lbl = self._label_items.get((col, row))
        if existing_lbl:
            self.itemconfig(existing_lbl, text=label)
        else:
            lid = self.create_text(
                cx, cy,
                text=label,
                font=("Georgia", 8, "bold"),
                fill="#1a1a1a",
                width=TILE_W - 8,
                justify="center",
            )
            self._label_items[(col, row)] = lid

        # Level indicator (e.g. "L2") for farms
        existing_lvl = self._level_items.get((col, row))
        level_text = f"L{level}" if level > 0 else ""
        if existing_lvl:
            self.itemconfig(existing_lvl, text=level_text)
        else:
            lvid = self.create_text(
                x1 - 8, y0 + 10,
                text=level_text,
                font=("Georgia", 7, "bold"),
                fill="#ffffff",
                anchor="ne",
            )
            self._level_items[(col, row)] = lvid

    # ── Public ────────────────────────────────────────────────────────────────

    def refresh(self, state: PlayerState) -> None:
        """
        Redraw tiles based on current PlayerState.

        Farm positions come from state.farms[i]["col"] and state.farms[i]["row"].
        Unoccupied farm/processing slots revert to their base type.
        """
        # Build a lookup of occupied positions → farm info
        occupied: Dict[Tuple[int, int], Dict] = {
            (f["col"], f["row"]): f for f in state.farms
        }

        for row in range(ROWS):
            for col in range(COLS):
                pos = (col, row)
                if pos in occupied:
                    farm = occupied[pos]
                    self._draw_tile(col, row, farm["farm_type"], farm.get("level", 1))
                else:
                    base = self._base_tile_type(col, row)
                    self._draw_tile(col, row, base, level=0)

    def add_farm_interactive(self, state: PlayerState, farm_type: str) -> bool:
        """
        Place a farm on the next available farm slot (left-to-right, top-to-bottom).
        Returns True if placed, False if no slot available.
        Called from the game tab when the player builds a farm.
        """
        occupied = {(f["col"], f["row"]) for f in state.farms}
        for col, row in FARM_SLOTS:
            if (col, row) not in occupied:
                state.farms.append({
                    "farm_type": farm_type,
                    "level": 1,
                    "col": col,
                    "row": row,
                })
                self.refresh(state)
                return True
        return False
