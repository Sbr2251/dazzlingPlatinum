#!/usr/bin/env python3
"""Garius (the rival): overworld key frame and design preview.

Design (approved 2026-11-09, see docs/story/art/garius.md):
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
    (22, 18, 32),     # 1  K outline
    (30, 36, 72),     # 2  H hair dark
    (50, 64, 118),    # 3  h hair mid
    (92, 114, 176),   # 4  i hair light
    (170, 100, 80),   # 5  S skin shadow
    (232, 172, 136),  # 6  s skin mid
    (250, 212, 182),  # 7  a skin light
    (136, 54, 28),    # 8  O jacket dark
    (204, 96, 36),    # 9  o jacket mid
    (242, 148, 68),   # 10 p jacket light
    (250, 238, 208),  # 11 w cream
    (28, 100, 108),   # 12 t teal shirt
    (60, 60, 76),     # 13 c charcoal
    (240, 194, 72),   # 14 g brass
    (200, 124, 24),   # 15 e amber
]

LEGEND = {
    "K": 1, "H": 2, "h": 3, "i": 4, "S": 5, "s": 6, "a": 7, "O": 8, "o": 9, "p": 10,
    "w": 11, "t": 12, "c": 13, "g": 14, "e": 15,
}

FRONT = """
|............HHH.....|
|.......HHHHHhiiH....|
|.....HHhhhhhhiihH...|
|....HhhhihhhiihhhH..|
|...HhhhiihhiihhhhhH.|
|..HhhhiihhHihhhhhhH.|
|..HhhihhhHhhhhhHhH..|
|..HhhhhhHhhhhhHhhH..|
|..HhhhhHhhhhhHhhhH..|
|..HhHhHahhhHHaHhHH..|
|..HHsHaaaaHaaaaHHH..|
|.KsHaKKaaaaaaKKaHsK.|
|.KsSaeKaaaaaaKeaSsK.|
|..KSaaaaaaaaaaaaSK..|
|...KsaaaaaaaaaasK...|
|....KsaaaaasSasK....|
|...KpKKsaaaasKKpK...|
|..KpowKKssssKKwopK..|
|..KpowwKttttKwwopK..|
|.KopooowttttwooopoK.|
|.KopKoowttttwooKpoK.|
|.KOoKoOwttttwOoKoOK.|
|.KwwKoOwttttwOoKwwK.|
|.KsaKOOOwttwOOOKasK.|
|..KsKKccccKcccgKsK..|
|...K.KcccK.KcccK.K..|
|.....KwwOK.KOwwK....|
|......KKK...KKK.....|
"""


def front_frame() -> list[int]:
    grid = parse_grid(FRONT)
    ox = (CELL - len(grid[0])) // 2
    oy = CELL - len(grid) - 2  # feet sit 2 px above the cell floor, like stock walkers
    return paint(blank(), grid, LEGEND, ox, oy)


def preview(frame: list[int], scale: int = 12) -> None:
    from PIL import Image

    bg = (128, 200, 176)
    cell = Image.new("RGB", (CELL, CELL), bg)
    for i, v in enumerate(frame):
        if v:
            cell.putpixel((i % CELL, i // CELL), PALETTE[v])
    big = cell.resize((CELL * scale, CELL * scale), Image.NEAREST)
    sw = 24
    out = Image.new("RGB", (big.width + CELL * 3 + 48, big.height + sw + 24), bg)
    out.paste(big, (8, 8))
    # true-size and 2x copies, the way it reads on a DS screen
    out.paste(cell, (big.width + 20, 16))
    out.paste(cell.resize((CELL * 2, CELL * 2), Image.NEAREST), (big.width + 20, 64))
    for n, rgb in enumerate(PALETTE[1:]):
        out.paste(Image.new("RGB", (sw, sw), rgb), (8 + n * (sw + 2), big.height + 16))
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
