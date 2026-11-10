#!/usr/bin/env python3
"""Convert the generated Garius concept image into an 80x80, 15-colour battle frame.

    python3 tools/garius_sprite/convert_concept.py [--height 66]     (needs PIL)

Reads docs/story/art/src/garius_battle_concept.webp (magenta background), and writes
  tools/garius_sprite/concept_grid.txt   the converted frame as an editable pixel grid
The grid is the raw conversion; hand fixes live in garius_battle.py, which reads it.

Method: every target pixel covers a block of source pixels. Each source pixel is snapped
to the nearest palette colour and the block takes the majority colour, except that a
block with enough outline pixels becomes outline (thin dark lines survive the shrink).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
SOURCE = REPO_ROOT / "docs/story/art/src/garius_battle_concept.webp"
GRID = HERE / "concept_grid.txt"
SIZE = 80

# letter -> colour. Index order (1..15) is the order here; 0 is transparent.
PALETTE = {
    "K": (16, 12, 20),      # outline
    "H": (22, 28, 52),      # hair dark, also the shirt's shadow
    "h": (56, 76, 132),     # hair mid
    "S": (150, 72, 44),     # rust: skin shadow and jacket dark
    "s": (222, 165, 123),   # skin mid
    "a": (250, 212, 180),   # skin light
    "o": (206, 98, 40),     # jacket mid
    "p": (234, 134, 62),    # jacket light
    "w": (246, 234, 190),   # cream
    "y": (204, 182, 128),   # cream shadow
    "t": (24, 84, 84),      # teal shirt
    "D": (62, 62, 66),      # charcoal dark
    "c": (92, 92, 94),      # charcoal mid
    "g": (222, 172, 60),    # brass
    "e": (190, 100, 10),    # amber
}
OUTLINE_SHARE = 0.30


def is_background(p, bg) -> bool:
    return sum(abs(a - b) for a, b in zip(p, bg)) < 90 or (p[0] > 150 and p[1] < 95 and p[2] > 100)


def nearest(p) -> str:
    return min(PALETTE, key=lambda k: sum((a - b) ** 2 for a, b in zip(p, PALETTE[k])))


def convert(height: int) -> list[str]:
    from PIL import Image

    im = Image.open(SOURCE).convert("RGB")
    px = im.load()
    bg = px[5, 5]
    w, h = im.size
    pts = [(x, y) for y in range(h) for x in range(w) if not is_background(px[x, y], bg)]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts) + 1
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts) + 1
    step = (y1 - y0) / height
    width = round((x1 - x0) / step)
    ox = (SIZE - width) // 2
    oy = SIZE - 2 - height  # feet two rows above the bottom edge, like stock sprites
    rows = [["."] * SIZE for _ in range(SIZE)]
    cache: dict = {}
    for ty in range(height):
        for tx in range(width):
            votes: Counter = Counter()
            total = 0
            for sy in range(int(y0 + ty * step), int(y0 + (ty + 1) * step)):
                for sx in range(int(x0 + tx * step), int(x0 + (tx + 1) * step)):
                    if not (0 <= sx < w and 0 <= sy < h):
                        continue
                    p = px[sx, sy]
                    total += 1
                    if is_background(p, bg):
                        votes["."] += 1
                    else:
                        if p not in cache:
                            cache[p] = nearest(p)
                        votes[cache[p]] += 1
            if not total or votes["."] > total * 0.5:
                continue
            solid = total - votes["."]
            if votes["K"] >= solid * OUTLINE_SHARE:
                ch = "K"
            else:
                del votes["."]
                ch = votes.most_common(1)[0][0]
            rows[oy + ty][ox + tx] = ch
    return ["".join(r) for r in rows]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--height", type=int, default=66)
    args = ap.parse_args()
    GRID.write_text("\n".join(convert(args.height)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
