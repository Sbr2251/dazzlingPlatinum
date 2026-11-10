#!/usr/bin/env python3
"""Garius (the rival): overworld key frame and design preview.

Design (approved 2026-11-09, see docs/story/art/garius.md), in stock Platinum style:
  - He wears his dead father's field jacket: burnt orange with cream trim, a size too
    big, collar popped, sleeves pushed up. It is the only loud colour on him and the
    opposite of Team Eclipse's dark and violet.
  - Ink-navy hair, short at the sides, with a windswept tuft blown back off the forehead.
  - Amber eyes, slightly narrowed.
  - Dark teal shirt, charcoal trousers, cream-and-rust shoes.
  - His father's brass pocket watch at the hip (a gold glint at this size).

    python3 tools/garius_sprite/garius.py            # write the 32x32 indexed key frame
    python3 tools/garius_sprite/garius.py --preview  # also the design preview (needs PIL)

The key frame is the front-facing standing pose only. The walker sheet (up, left,
steps) follows once the design is signed off.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / "arc1_sprites"))

from pixelkit import CELL, blank, paint, parse_grid, write_sheet  # noqa: E402

KEY_FRAME = REPO_ROOT / "res/field/objects/garius/garius_front.png"
PREVIEW = REPO_ROOT / "docs/story/art/garius_design.png"

PALETTE = [
    (255, 0, 255),    # 0  transparent
    (8, 8, 16),       # 1  K outline (stock walkers use pure black here)
    (24, 33, 66),     # 2  H hair dark (also the hair's outline, as on stock sprites)
    (58, 82, 148),    # 3  h hair mid
    (115, 148, 214),  # 4  i hair light
    (148, 90, 74),    # 5  S skin shadow / face outline
    (222, 165, 123),  # 6  s skin mid
    (255, 214, 189),  # 7  a skin light
    (148, 66, 33),    # 8  O jacket dark
    (214, 107, 41),   # 9  o jacket mid
    (247, 156, 82),   # 10 p jacket light
    (247, 239, 214),  # 11 w cream / eye white
    (33, 107, 115),   # 12 t teal shirt
    (66, 66, 82),     # 13 c charcoal
    (247, 198, 82),   # 14 g brass
    (189, 99, 8),    # 15 e amber
]

LEGEND = {
    "K": 1, "H": 2, "h": 3, "i": 4, "S": 5, "s": 6, "a": 7, "O": 8, "o": 9, "p": 10,
    "w": 11, "t": 12, "c": 13, "g": 14, "e": 15,
}

# Drawn on stock Barry's skeleton (mmodel member 0x7F, frame 4): same cell position,
# 23 px height plus the tuft, same face box, eye columns and stance.
FRONT_ORIGIN = (6, 6)
FRONT = """
|...........HHH......|
|......HHHHHhiiH.....|
|....HHhhhhhiihhH....|
|...HhhihhhiihhhhH...|
|..HhhiihhhHhhhihhH..|
|.HhhiihhhHhhhhhHhhH.|
|.HhhihhhHhhhhhHhhhH.|
|.HhihhhHhhhhhHhhihH.|
|.HhHhhHhhHhhHhhHhH..|
|.HHhhHhhhHhhhHhhHH..|
|.KHhHhaaaaHaaHhHHK..|
|.KHHsaSSaaaSSsHHHK..|
|..KSssweaaaewssSK...|
|...KsswKaaaKwssK....|
|....SsaaaaaaasS.....|
|....KSsaaSsasSK.....|
|...KpwKSsssSKwpK....|
|..KopowwtttwwopoK...|
|.KawoOowtttwoOowaK..|
|.KssKOOotttoOOKssK..|
|..KK.KOOcccgOK.KK...|
|....KccccKccgcK.....|
|....KwOK...KOwK.....|
|.....KK.....KK......|
"""


def front_frame() -> list[int]:
    grid = parse_grid(FRONT)
    return paint(blank(), grid, LEGEND, *FRONT_ORIGIN)


def preview(frame: list[int], scale: int = 8) -> None:
    """Line-up with stock walkers (Barry, Rowan, Cyrus) at `scale`, 2x and true size."""
    from PIL import Image

    from pixelkit import DOWN, stock_walker

    bg = (120, 192, 112)  # roughly the stock grass tile
    cast = []
    for member in (0x7F,):
        frames, pal = stock_walker(member)
        cast.append((frames[DOWN * 4], pal))
    cast.append((frame, PALETTE))
    for member in (0x5E, 0x63):
        frames, pal = stock_walker(member)
        cast.append((frames[DOWN * 4], pal))
    strip = Image.new("RGB", (CELL * len(cast), CELL), bg)
    for n, (fr, pal) in enumerate(cast):
        for i, v in enumerate(fr):
            if v:
                strip.putpixel((n * CELL + i % CELL, i // CELL), tuple(pal[v][:3]))
    big = strip.resize((strip.width * scale, strip.height * scale), Image.NEAREST)
    out = Image.new("RGB", (big.width, big.height + CELL * 3 + 24), bg)
    out.paste(big, (0, 0))
    out.paste(strip.resize((strip.width * 2, CELL * 2), Image.NEAREST), (8, big.height + 8))
    out.paste(strip, (strip.width * 2 + 32, big.height + 8 + CELL))
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    out.save(PREVIEW)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    frame = front_frame()
    write_sheet(KEY_FRAME, [frame], 1, PALETTE)
    if args.preview:
        preview(frame)
    return 0


if __name__ == "__main__":
    sys.exit(main())
