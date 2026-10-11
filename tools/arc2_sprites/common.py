"""Shared imports for the Arc 2 sprite generators.

Reuses the Arc 1 pixel helpers (tools/arc1_sprites/pixelkit.py, walker.py) rather than copying them:
they are pure Python, read the stock mmodel members and write 4bpp indexed PNGs.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARC1 = HERE.parent / "arc1_sprites"
for p in (str(HERE), str(ARC1)):
    if p not in sys.path:
        sys.path.insert(0, p)

from pixelkit import (  # noqa: E402,F401
    CELL,
    DOWN,
    LEFT,
    REPO_ROOT,
    RIGHT,
    UP,
    blank,
    clear_rows,
    mirror,
    neighbours,
    paint,
    parse_grid,
    read_png,
    remap,
    stock_walker,
    top_row,
    write_sheet,
)
from walker import Character, Part, compose  # noqa: E402,F401

SHEET_DIR = REPO_ROOT / "res/field/objects/arc2"

# A head Part that paints nothing (for variants that keep the stock head).
NO_HEAD = Part("|.|", 0, 0)


def set_px(frame: list[int], x: int, y: int, v: int) -> None:
    if 0 <= x < CELL and 0 <= y < CELL:
        frame[y * CELL + x] = v


def get_px(frame: list[int], x: int, y: int) -> int:
    if 0 <= x < CELL and 0 <= y < CELL:
        return frame[y * CELL + x]
    return 0
