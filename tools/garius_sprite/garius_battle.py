#!/usr/bin/env python3
"""Garius (the rival): front battle sprite, the pose shown as a battle starts.

The pose, anatomy and shading come from a generated concept image
(docs/story/art/src/garius_battle_concept.webp), shrunk to 80x80 and 15 colours by
convert_concept.py (-> concept_grid.txt). This script applies the clean-up on top:
  1. closes the outline wherever the shrink lost it,
  2. lights the top edges of the jacket and keeps the shirt teal,
  3. redraws by hand what does not survive at this size: face, hair lights, watch.
Two frames for the intro animation: eyes shut and mouth flat, then eyes open with the smirk.

    python3 tools/garius_sprite/garius_battle.py            # write both frames (160x80)
    python3 tools/garius_sprite/garius_battle.py --preview  # also the preview (needs PIL)

Design frames only: not wired into res/trainers/classes/meson.build yet.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from convert_concept import GRID, PALETTE as LETTER_COLOURS, SIZE  # noqa: E402
from integrate_mawile_overworld_sprite import write_indexed_png  # noqa: E402

FRAME = REPO_ROOT / "res/trainers/classes/garius/front_design.png"
PREVIEW = REPO_ROOT / "docs/story/art/garius_battle_design.png"

LETTERS = list(LETTER_COLOURS)
PALETTE = [(255, 0, 255)] + [LETTER_COLOURS[k] for k in LETTERS]
INDEX = {k: n + 1 for n, k in enumerate(LETTERS)}

# Hand-drawn patches: (x, y, rows). '.' leaves the pixel alone, '_' clears it.
FACE = (31, 20, [
    "KHHHHHaSSaaSSHKK",
    "_HHHsaeKaaKeaK__",
    "_KKssawKaaKwaK__",
    "__KSsaaaaaasaK__",
    "___KsaaaSSSaaK__",
    "__KKHKsaaaaaK___",
    "__KKKKKKSssK____",
])
EYES_SHUT = (31, 21, [
    "_HHHsaaaaaaaaK__",
    "_KKssaKKaaKKaK__",
    "__KSsaaaaaasaK__",
    "___KsaaaaSSaaK__",
])
HAIR_LIGHTS = [(35, 15), (36, 15), (40, 15), (41, 15), (34, 17), (35, 17), (33, 18), (33, 19)]
WATCH = (38, 50, [
    "g.....",
    ".gg...",
    "...gg.",
    "..gwwg",
    "..gwwg",
    "...gg.",
])


def patch(grid: list[list[str]], part) -> None:
    ox, oy, rows = part
    for gy, row in enumerate(rows):
        for gx, ch in enumerate(row):
            if ch != ".":
                grid[oy + gy][ox + gx] = "." if ch == "_" else ch


def base() -> list[list[str]]:
    grid = [list(r.ljust(SIZE, ".")) for r in GRID.read_text().split("\n")[:SIZE]]

    def at(x, y):
        return grid[y][x] if 0 <= x < SIZE and 0 <= y < SIZE else "."

    # 1. close the outline: an empty pixel beside a coloured (non-outline) one becomes outline
    add = [(x, y) for y in range(SIZE) for x in range(SIZE) if grid[y][x] == "."
           and any(at(x + dx, y + dy) not in ".K" for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for x, y in add:
        grid[y][x] = "K"
    # 2. jacket: light the pixels just under a top edge; shirt: teal except its shadowed edge
    for y in range(27, 50):
        for x in range(SIZE):
            if grid[y][x] == "o" and at(x, y - 1) in "Kw":
                grid[y][x] = "p"
                if at(x, y + 1) == "o" and at(x - 1, y) != "K":
                    grid[y + 1][x] = "p"
        run = [x for x in range(SIZE) if grid[y][x] == "H"]
        for x in run[1:]:
            grid[y][x] = "t"
    return grid


def front_frames() -> list[list[int]]:
    """[frame 1 (eyes shut), frame 2 (eyes open, smirk)]."""
    frames = []
    for shut in (True, False):
        grid = base()
        patch(grid, FACE)
        if shut:
            patch(grid, EYES_SHUT)
        for x, y in HAIR_LIGHTS:
            grid[y][x] = "h"
        patch(grid, WATCH)
        frames.append([INDEX.get(ch, 0) for row in grid for ch in row])
    return frames


def preview(frames: list[list[int]], scale: int = 4) -> None:
    from PIL import Image

    bg = (197, 189, 156)
    strip = Image.new("RGB", (SIZE * 4, SIZE), bg)
    for n, name in enumerate(("rival", 0, 1, "galactic_boss")):
        if isinstance(name, int):
            for i, v in enumerate(frames[name]):
                if v:
                    strip.putpixel((n * SIZE + i % SIZE, i // SIZE), PALETTE[v])
            continue
        im = Image.open(REPO_ROOT / "res/trainers/classes" / name / "front_scan.png")
        stock = im.convert("RGB").crop((0, 0, SIZE, SIZE))
        first = stock.getpixel((0, 0))
        for y in range(SIZE):
            for x in range(SIZE):
                px = stock.getpixel((x, y))
                strip.putpixel((n * SIZE + x, y), bg if px == first else px)
    big = strip.resize((strip.width * scale, SIZE * scale), Image.NEAREST)
    out = Image.new("RGB", (big.width, big.height + SIZE + 16), bg)
    out.paste(big, (0, 0))
    out.paste(strip, (8, big.height + 8))
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    out.save(PREVIEW)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    frames = front_frames()
    sheet = [0] * (SIZE * 2 * SIZE)  # both frames side by side, like a stock front_scan.png
    for n, frame in enumerate(frames):
        for i, v in enumerate(frame):
            sheet[(i // SIZE) * SIZE * 2 + n * SIZE + i % SIZE] = v
    snapped = [tuple(((ch >> 3) << 3) | (ch >> 5) for ch in rgb) for rgb in PALETTE]
    FRAME.parent.mkdir(parents=True, exist_ok=True)
    write_indexed_png(FRAME, SIZE * 2, SIZE, sheet, snapped)
    if args.preview:
        preview(frames)
    return 0


if __name__ == "__main__":
    sys.exit(main())
