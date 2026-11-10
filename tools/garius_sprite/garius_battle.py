#!/usr/bin/env python3
"""Garius (the rival): front battle sprite, the pose shown as a battle starts.

In stock Platinum style, built on stock Lucas's battle skeleton
(res/trainers/classes/player_male/front_scan.png): the same height, stance and open
jacket, one hand at the lapel. The body is the stock body recoloured region by region;
the head (hair, face) is redrawn by hand.

    python3 tools/garius_sprite/garius_battle.py            # write the 80x80 indexed frame
    python3 tools/garius_sprite/garius_battle.py --preview  # also the preview (needs PIL)

Design frame only: not wired into res/trainers/classes/meson.build yet.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "arc1_sprites"))

from garius import LEGEND  # noqa: E402
from garius import PALETTE as OVERWORLD_PALETTE  # noqa: E402
from integrate_mawile_overworld_sprite import read_indexed_png, write_indexed_png  # noqa: E402
from pixelkit import parse_grid  # noqa: E402

SIZE = 80
BASE = REPO_ROOT / "res/trainers/classes/player_male/front_scan.png"
FRAME = REPO_ROOT / "res/trainers/classes/garius/front_design.png"
PREVIEW = REPO_ROOT / "docs/story/art/garius_battle_design.png"

# The overworld palette with one change: the skin shadow and the jacket's dark tone share
# one rust brown (index 5), which frees index 8 for a second trouser tone.
PALETTE = list(OVERWORLD_PALETTE)
PALETTE[5] = (150, 72, 44)   # S rust: skin shadow and jacket dark
PALETTE[8] = (60, 60, 76)    # C charcoal dark
PALETTE[13] = (102, 102, 118)  # c charcoal mid

L = LEGEND
K, H, S, s, a, o, p, w, t, c, g = (L[k] for k in "KHSsaopwtcg")
O = S
C = 8

# Stock Lucas indexes: 1 jacket light, 5 jacket mid, 4 dark (jacket shadow, trousers, hair),
# 7 trousers mid, 2/3 red (shirt, cuffs), f/e/8/6 white-to-grey (scarf, bag, shoes),
# a/9 skin dark, b skin mid, c skin light, d black.
SKIN = {0xA: S, 0x9: S, 0xB: s, 0xC: a, 0xD: K}


def body_pixel(v: int, x: int, y: int) -> int:
    if v in SKIN and not (v == 0xA and 49 <= y <= 50 and x < 50):
        return SKIN[v]
    if y >= 50:  # trousers and shoes
        return {7: c, 4: C, 6: c, 8: w, 0xF: w, 0xE: s, 0xA: C}.get(v, C)
    bag = x <= 35 and y >= 38
    if v == 1:
        return p
    if v == 5:
        return o
    if v == 4:
        return O
    if v == 2:  # red: cuffs by the hand, shirt elsewhere
        return w if x >= 52 else H
    if v == 3:
        return t
    if v == 0xA:
        return H  # shirt hem
    if bag:  # the bag becomes the long tail of the oversized jacket
        return {8: o, 6: O, 0xE: O, 0xF: p}.get(v, O)
    if y <= 35:  # scarf at the neck -> popped cream collar
        return {0xF: w, 8: w, 0xE: s, 6: s}.get(v, w)
    return {0xF: t, 0xE: H, 8: t, 6: H}.get(v, t)  # scarf on the chest -> teal shirt


# Hand-drawn head. Coordinates are absolute in the 80x80 frame.
HAIR = (28, 10, """
|...............HHH....|
|.............HHhiiH...|
|........HHHHHhhiihH...|
|......HHhhhhhhiihhH...|
|....HHhhihhhhiihhhhH..|
|...HhhhiihhhhihhhhhhH.|
|..HhhhiihhhhhhhhhHhhH.|
|..HhhihhhhhhhhhhHhhhH.|
|..HhhhhhhhHhhhhHhhhhH.|
|..HhhhhhhHhhhhHhhhhhH.|
|..HhHhhhHhhhhHhhhhhHH.|
|..HHHhhHhhhhHHhhhHhH..|
|..HHhHHssHssHHsHhHHH..|
""")

FACE = (32, 23, """
|HHSSaaHaSSaHhHHK|
|KHweaaaaewaHHsH_|
|KHwKaaaaKwaaHsK_|
|_SssaaaasaaaHsK_|
|_KssaaaaaSaSKK__|
|__SsaaaSSaaK____|
|__KSsaaaaaK_____|
""")

WATCH = [(46, 50), (47, 51), (47, 52), (46, 52), (46, 53), (47, 53)]


def paint(frame: list[int], part) -> None:
    ox, oy, text = part
    for gy, row in enumerate(parse_grid(text)):
        for gx, ch in enumerate(row):
            if ch in ". ":
                continue
            frame[(oy + gy) * SIZE + ox + gx] = 0 if ch == "_" else LEGEND[ch]


def front_frame() -> list[int]:
    width, _height, pixels, _pal = read_indexed_png(BASE)
    frame = [0] * (SIZE * SIZE)
    for y in range(30, SIZE):  # everything below the chin comes from the stock body
        for x in range(SIZE):
            v = pixels[y * width + x]
            if v:
                frame[y * SIZE + x] = body_pixel(v, x, y)
    paint(frame, HAIR)
    paint(frame, FACE)
    for x, y in WATCH:
        frame[y * SIZE + x] = g
    return frame


def preview(frame: list[int], scale: int = 5) -> None:
    from PIL import Image

    bg = (197, 189, 156)
    strip = Image.new("RGB", (SIZE * 3, SIZE), bg)
    for n, name in enumerate(("rival", None, "galactic_boss")):
        if name is None:
            for i, v in enumerate(frame):
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
    frame = front_frame()
    snapped = [tuple(((ch >> 3) << 3) | (ch >> 5) for ch in rgb) for rgb in PALETTE]
    FRAME.parent.mkdir(parents=True, exist_ok=True)
    write_indexed_png(FRAME, SIZE, SIZE, frame, snapped)
    if args.preview:
        preview(frame)
    return 0


if __name__ == "__main__":
    sys.exit(main())
