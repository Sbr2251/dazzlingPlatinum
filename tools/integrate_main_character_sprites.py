#!/usr/bin/env python3
"""Replace the male player's walking/running overworld textures (mmodel 90).

The tracked art is a 128x128 RGBA sheet of 32x32 frames: rows face down, left,
right and up; columns are stand, step, stand, step. It is reduced to a fixed
15-color palette (index 0 transparent) and written over the 32 ``pl_boy01c.N``
textures in place. Only walk frames exist, so the run textures reuse them.

mmodel 90 layout, per the stock Lucas textures:
  1-4 up, 5-8 down, 9-12 left, 13-16 right (stored mirrored), 17-32 the same
  four directions for running. Within each group of four, texture 3 shares
  its texel data with texture 1 (the standing pose).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from PIL import Image

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import inspect_nitro_bmd_textures as nitro_parser
from inject_nitro_bmd_textures import inject_frames

REPO = TOOLS_DIR.parent
DEFAULT_SHEET = REPO / "res/field/objects/player/hero_walk.png"
DEFAULT_MEMBER = REPO / "res/prebuilt/data/mmodel/mmodel/mmodel_00000090.bin"
FRAME = 32

TRANSPARENT = (180, 180, 180)
PALETTE = [
    (0, 0, 0),
    (24, 24, 32),
    (40, 40, 50),
    (62, 62, 74),
    (100, 100, 116),
    (226, 58, 50),
    (166, 30, 38),
    (112, 20, 28),
    (92, 128, 186),
    (146, 176, 222),
    (56, 84, 132),
    (236, 186, 138),
    (192, 134, 94),
    (244, 244, 244),
    (196, 196, 208),
]
# Sheet colors that are not in PALETTE, folded into the closest shade by hand.
MERGE = {
    (34, 34, 42): (40, 40, 50),
    (44, 44, 54): (40, 40, 50),
    (56, 56, 68): (62, 62, 74),
    (68, 68, 80): (62, 62, 74),
    (72, 72, 84): (62, 62, 74),
    (92, 92, 106): (100, 100, 116),
    (66, 98, 150): (56, 84, 132),
    (248, 248, 248): (244, 244, 244),
    (240, 240, 240): (244, 244, 244),
    (196, 196, 206): (196, 196, 208),
    (206, 206, 214): (196, 196, 208),
    (140, 140, 156): (100, 100, 116),
    (242, 128, 112): (226, 58, 50),
    (77, 66, 18): (62, 62, 74),
    (112, 96, 64): (62, 62, 74),
    (80, 64, 48): (40, 40, 50),
}

SHEET_ROW = {"down": 0, "left": 1, "right": 2, "up": 3}
# Texture groups in mmodel order; each takes the sheet's stand, step, stand, step.
GROUPS = ["up", "down", "left", "right"] * 2
# Texture 3 aliases texture 1, so both get the first standing column.
GROUP_COLUMNS = [0, 1, 0, 3]


def indexed_frame(sheet: Image.Image, row: int, column: int, mirror: bool) -> Image.Image:
    cell = sheet.crop((column * FRAME, row * FRAME, (column + 1) * FRAME, (row + 1) * FRAME))
    if mirror:
        cell = cell.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    lookup = {color: index + 1 for index, color in enumerate(PALETTE)}
    out = Image.new("P", (FRAME, FRAME), 0)
    flat = list(TRANSPARENT)
    for color in PALETTE:
        flat.extend(color)
    out.putpalette(flat + [0] * (768 - len(flat)))
    for y in range(FRAME):
        for x in range(FRAME):
            r, g, b, a = cell.getpixel((x, y))
            if a == 0:
                continue
            rgb = MERGE.get((r, g, b), (r, g, b))
            if rgb not in lookup:
                raise ValueError(f"row {row} column {column}: color {rgb} has no palette mapping")
            out.putpixel((x, y), lookup[rgb])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sheet", type=Path, default=DEFAULT_SHEET)
    parser.add_argument("--member", type=Path, default=DEFAULT_MEMBER)
    args = parser.parse_args()

    sheet = Image.open(args.sheet).convert("RGBA")
    if sheet.size != (4 * FRAME, 4 * FRAME):
        raise SystemExit(f"{args.sheet}: expected a {4 * FRAME}x{4 * FRAME} sheet, got {sheet.size}")

    frames_by_number = {}
    for group, direction in enumerate(GROUPS):
        for step, column in enumerate(GROUP_COLUMNS):
            number = group * 4 + step + 1
            frames_by_number[number] = indexed_frame(
                sheet, SHEET_ROW[direction], column, mirror=direction == "right"
            )

    # inject_frames writes in container order, which is by name, not number.
    names = [texture["name"] for texture in nitro_parser.parse_bmd(args.member, None)["textures"]]
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name in names:
            number = int(name.rsplit(".", 1)[1])
            path = Path(tmp) / f"{number:02d}.png"
            frames_by_number[number].save(path)
            paths.append(path)
        inject_frames(args.member, paths, args.member)


if __name__ == "__main__":
    main()
