#!/usr/bin/env python3
"""Garius (the rival): front battle sprite, the pose shown as a battle starts.

The pose, anatomy and shading come from a generated concept image
(docs/story/art/src/garius_battle_concept.webp), shrunk to 80x80 and 15 colours by
convert_concept.py (-> concept_grid.txt). This script applies the clean-up on top:
  1. closes the outline wherever the shrink lost it and thins it back to one pixel,
  2. shades the jacket, shirt and trousers (lit from the top left),
  3. redraws by hand what does not survive at this size: the whole head and the watch,
  4. mirrors the frame so he faces left, towards the player, like the stock opponents.
Two frames for the intro animation: head bowed with eyes shut, then looking up with the smirk.

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
# Drawn in the concept's orientation (facing right); the finished frame is mirrored so he
# faces left, towards the player, like the stock opponents.
HEAD_BOX = (28, 10, 51, 27)  # cleared before the head is painted (x0, y0, x1, y1)
HEAD = (30, 10, [
    "......KK...........",
    "....KKHHK..........",
    "...KHHhHK.KK.......",
    "..KHHhhHKKHHKKK....",
    ".KHHhhHHHHHhhHHKK..",
    ".KHhhHHHHHhhhhHHHK.",
    "KHHhHHHHHhhhHHHHHHK",
    "KHhHHHHsaaHHhHHHHHK",
    "KHhHHHsaaaaHHHHHKK.",
    "KHHHHsaaaaaaaHHK...",
    ".KHHsaHHaaaHHaK....",
    ".KHssaeKaaaeKaK....",
    ".KKsSawKaaawKaK....",
    "..KSsaaaaaaaSsK....",
    "...KsaaaaaSSaK.....",
    "...KKHKsaaaaK......",
    "...KKKKKKSssK......",
])
# Frame 1 changes these rows of HEAD (eyes shut, no smirk) and bows the head one pixel.
SHUT_ROWS = {
    11: ".KHssaaaaaaaaaK....",
    12: ".KKsSaKKaaaKKaK....",
    13: "..KSsaaaaaaaasK....",
}
WATCH = (38, 50, [
    "g......",
    ".gg....",
    "...gggD",
    "..cgwwg",
    "..cgwwg",
    "...DggD",
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

    sides = ((1, 0), (-1, 0), (0, 1), (0, -1))
    cells = [(x, y) for y in range(SIZE) for x in range(SIZE)]
    # 1. close the outline: an empty pixel beside a coloured (non-outline) one becomes outline
    for x, y in [c for c in cells if at(*c) == "." and any(at(c[0] + dx, c[1] + dy) not in ".K" for dx, dy in sides)]:
        grid[y][x] = "K"
    #    ...then thin it: drop outline pixels on the outside that touch no colour at all
    for x, y in [c for c in cells if at(*c) == "K"
                 and any(at(c[0] + dx, c[1] + dy) == "." for dx, dy in sides)
                 and all(at(c[0] + dx, c[1] + dy) in ".K" for dx, dy in sides)]:
        grid[y][x] = "."
    # 2. shading, lit from the top left. Jacket: light under a top edge, rust shadow against
    #    a right or bottom edge. Shirt: teal except its shadowed edge. Trousers: the near
    #    leg darkens towards its right edge, the far leg catches light on its left edge.
    for y in range(27, 50):
        for x in range(SIZE):
            if grid[y][x] == "o" and at(x, y - 1) in "Kw":
                grid[y][x] = "p"
                if at(x, y + 1) == "o" and at(x - 1, y) != "K":
                    grid[y + 1][x] = "p"
        for x in [x for x in range(SIZE) if grid[y][x] == "H"][1:]:
            grid[y][x] = "t"
    for x, y in [c for c in cells if at(*c) == "o" and 27 <= c[1] < 50
                 and (at(c[0] + 1, c[1]) == "K" or at(c[0], c[1] + 1) == "K")]:
        grid[y][x] = "S"
    for x, y in [c for c in cells if c[1] >= 52]:
        if grid[y][x] == "c" and "K" in (at(x + 1, y), at(x + 2, y)):
            grid[y][x] = "D"
    for x, y in [c for c in cells if c[1] >= 56 and at(*c) == "D" and at(c[0] - 1, c[1]) == "K"
                 and at(c[0] + 1, c[1]) == "D"]:
        grid[y][x] = "c"
    return grid


def front_frames() -> list[list[int]]:
    """[frame 1 (head bowed, eyes shut), frame 2 (looking up, smirk)]."""
    frames = []
    for shut in (True, False):
        grid = base()
        x0, y0, x1, y1 = HEAD_BOX
        for y in range(y0, y1):
            for x in range(x0, x1):
                grid[y][x] = "."
        ox, oy, rows = HEAD
        rows = list(rows)
        if shut:
            for n, row in SHUT_ROWS.items():
                rows[n] = row
            patch(grid, (ox, oy + 1, rows[:-1]))  # the neck row stays where it is
            patch(grid, (ox, oy + len(rows) - 1, rows[-1:]))
        else:
            patch(grid, (ox, oy, rows))
        patch(grid, WATCH)
        frames.append([INDEX.get(ch, 0) for row in grid for ch in reversed(row)])
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
