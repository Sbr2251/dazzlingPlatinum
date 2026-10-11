#!/usr/bin/env python3
"""Cyrus's battle back sprite (the 2.5 tag battle partner), edited from Riley's stock back sprite.

    ~/.venvs/desmume/bin/python tools/arc2_sprites/cyrus_back.py           # write the sprite
    ~/.venvs/desmume/bin/python tools/arc2_sprites/cyrus_back.py --check   # fail if stale

Source: res/trainers/classes/trainer_riley/back.png (5 throw frames, 80x80 each, 1 px separators) and
back_scan.png (frames 0 and 1 side by side). Riley's spiky hair and long coat are already close to
Cyrus's silhouette from behind, so the edit is:
  - the fedora (crown, band, both brims) is painted out and a new spiky crown is drawn in its place:
    pale steel-blue spikes swept up and back, fringe spikes over the brow (rasterised from the spike
    list below, shaded from the upper right and outlined);
  - the palette becomes Cyrus's: his hair ramp from his own front sprite, the blue coat turned into
    his grey coat, the yellow coat zip into a dull silver one.
The head is identical in every frame, only translated (HEAD_OFFSETS), so one crown is drawn and
placed per frame; pixels where another part of the frame (a raised arm) covers the head are kept.
Cell/anim JSON and the scan key are copied unchanged from Riley, so the throw animation and its
ball-release offsets (battle_display.c, row 4 of the throw table) still match.

Output: res/trainers/classes/arc2_wanderer_back/ (not a trainer class directory; appended to the
trbgra NARC after dp_rival by tools/ordergen/trainer_graphics.py, back pic index 11).
"""

from __future__ import annotations

import argparse
import io
import shutil
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "res/trainers/classes/trainer_riley"
DEST = REPO / "res/trainers/classes/arc2_wanderer_back"

FRAME = 80
STRIDE = 81  # 1 px separator row (index 255) between frames
HEAD_OFFSETS = [(0, 0), (-6, 3), (3, -1), (-5, -1), (-3, 4)]  # frame f head = frame 0 head + offset

# Riley's palette indexes
BG, HAIR_MID, HAIR_DARK, COAT_LIGHT, SLATE, COAT_DEEP, COAT_MID, HAIR_LIGHT, ZIP = 0, 1, 2, 3, 4, 5, 6, 7, 8
COAT_DARK, OUTLINE, CROWN_LIGHT = 9, 13, 14
HAT = {COAT_LIGHT, COAT_DEEP, COAT_MID, COAT_DARK}

PALETTE = {
    CROWN_LIGHT: (180, 213, 246),  # Cyrus's hair, from galactic_boss/front.png (14 is unused by Riley)
    HAIR_LIGHT: (110, 128, 172),   # Riley's sideburn/brow pixels
    HAIR_MID: (131, 156, 197),
    HAIR_DARK: (90, 106, 148),
    SLATE: (57, 65, 82),          # hair shadow and coat creases (kept)
    COAT_LIGHT: (197, 197, 205),  # Cyrus's grey coat
    COAT_MID: (139, 139, 148),
    COAT_DARK: (90, 90, 106),
    COAT_DEEP: (49, 49, 57),
    ZIP: (205, 205, 213),
}

# Crown, frame-0 coordinates. Skull cap = ellipse; spikes = triangles (base a, base b, tip).
SKULL = (40.0, 17.5, 11.5, 9.5)  # cx, cy, rx, ry (clipped to CROWN_MAX_Y)
CROWN_MAX_Y = 19
SPIKES = [
    ((31, 10), (34, 15), (18, 6)),    # back, up-left
    ((29, 13), (30, 19), (16, 13)),   # back, low
    ((31, 16), (31, 20), (20, 18)),   # back, lowest (joins Riley's own back spikes)
    ((33, 9), (38, 8), (23, 2)),      # top, swept back
    ((37, 8), (43, 8), (30, 0)),      # top
    ((42, 8), (48, 11), (40, 1)),     # top, front
    ((47, 11), (50, 16), (54, 8)),    # fringe, up-right
    ((48, 14), (50, 19), (55, 16)),   # fringe, over the brow
]
STRANDS = [  # highlight lines (from, to) inside the crown
    ((41, 10), (32, 2)),
    ((37, 11), (26, 4)),
    ((45, 11), (41, 3)),
    ((34, 13), (21, 8)),
    ((48, 13), (52, 10)),
]
STRAND_SHADOWS = [
    ((38, 15), (24, 11)),
    ((44, 14), (37, 8)),
    ((36, 18), (22, 16)),
]


def _in_triangle(px: float, py: float, a, b, c) -> bool:
    def side(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

    p = (px, py)
    d1, d2, d3 = side(p, a, b), side(p, b, c), side(p, c, a)
    neg = d1 < 0 or d2 < 0 or d3 < 0
    pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (neg and pos)


def _line(p0, p1):
    (x0, y0), (x1, y1) = p0, p1
    n = max(abs(x1 - x0), abs(y1 - y0))
    return {(round(x0 + (x1 - x0) * t / n), round(y0 + (y1 - y0) * t / n)) for t in range(n + 1)}


def crown_pixels() -> dict[tuple[int, int], int]:
    """The new crown in frame-0 coordinates: {(x, y): palette index}, outline included."""
    cx, cy, rx, ry = SKULL
    mask = set()
    for y in range(-2, CROWN_MAX_Y + 3):
        for x in range(10, 64):
            inside = y <= CROWN_MAX_Y and ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1.0
            if not inside:
                inside = any(_in_triangle(x + 0.5, y + 0.5, a, b, c) for a, b, c in SPIKES)
            if inside and y >= 0:
                mask.add((x, y))
    out = {}
    for x, y in mask:
        lit = (x + 1, y - 1) not in mask or (x, y - 1) not in mask
        shade = (x - 1, y + 1) not in mask or (x - 1, y) not in mask
        if lit and not shade:
            v = CROWN_LIGHT
        elif shade and not lit:
            v = HAIR_DARK
        else:
            v = HAIR_MID
        if y >= CROWN_MAX_Y - 1 and x < 46:
            v = HAIR_DARK  # the crown's underside meets Riley's own darker back hair
        out[(x, y)] = v
    for a, b in STRANDS:
        for p in _line(a, b):
            if p in mask and out[p] == HAIR_MID:
                out[p] = CROWN_LIGHT
    for a, b in STRAND_SHADOWS:
        for p in _line(a, b):
            if p in mask and out[p] != CROWN_LIGHT:
                out[p] = HAIR_DARK
    for x, y in list(mask):
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in mask and ny >= 0 and (nx, ny) not in out:
                out[(nx, ny)] = OUTLINE
    return out


def hat_region(x: int, y: int) -> bool:
    """Frame-0 pixels that belong to the fedora (crown, band, brims) and its shadow."""
    if y <= 16 and 14 <= x <= 62:
        return True
    if 17 <= y <= 23 and x >= 47:
        return True  # front brim and its outline
    if y == 17 and 28 <= x <= 31:
        return True  # brim underside on the left
    return False


def edit_frames(img: Image.Image) -> Image.Image:
    src = img.copy()
    out = img.copy()
    sp, op = src.load(), out.load()
    crown = crown_pixels()
    for f, (dx, dy) in enumerate(HEAD_OFFSETS):
        top = f * STRIDE

        def same_as_head(x0, y0):
            """Is frame f's pixel at the head-relative spot unchanged from frame 0 (i.e. still head)?"""
            x, y = x0 + dx, y0 + dy
            if not (0 <= x < FRAME and 0 <= y < FRAME):
                return False
            return sp[x, top + y] == sp[x0, y0]

        # 1. paint out the hat
        for y0 in range(0, 24):
            for x0 in range(0, FRAME):
                if not hat_region(x0, y0):
                    continue
                v0 = sp[x0, y0]
                if v0 == BG:
                    continue
                if y0 >= 17 and v0 not in HAT | {OUTLINE, SLATE}:
                    continue  # face / fringe pixels under the front brim stay
                if same_as_head(x0, y0):
                    op[x0 + dx, top + y0 + dy] = BG
        # 2. draw the crown where the frame shows head or background
        for (x0, y0), v in crown.items():
            x, y = x0 + dx, y0 + dy
            if not (0 <= x < FRAME and 0 <= y < FRAME):
                continue
            cur = sp[x, top + y]
            head_px = 0 <= x0 < FRAME and 0 <= y0 < FRAME and same_as_head(x0, y0)
            if cur == BG or head_px:
                if v == OUTLINE and op[x, top + y] not in (BG,) and not hat_region(x0, y0):
                    continue  # don't outline over Riley's own hair/face
                op[x, top + y] = v
    pal = out.getpalette()
    for i, rgb in PALETTE.items():
        pal[3 * i:3 * i + 3] = [((c >> 3) << 3) | (c >> 5) for c in rgb]
    out.putpalette(pal)
    return out


def build() -> tuple[bytes, bytes]:
    back = edit_frames(Image.open(SRC / "back.png"))
    scan = Image.new("P", (160, 80))
    scan.putpalette(back.getpalette()[:48])
    sp = scan.load()
    bp = back.load()
    for half in range(2):
        for y in range(FRAME):
            for x in range(FRAME):
                sp[half * FRAME + x, y] = bp[x, half * STRIDE + y]

    def png(im: Image.Image, bits: int | None = None) -> bytes:
        buf = io.BytesIO()
        if bits:
            im.save(buf, format="PNG", bits=bits, optimize=False)
        else:
            im.save(buf, format="PNG", optimize=False)
        return buf.getvalue()

    return png(back), png(scan, bits=4)


COPIED = ("back_cell.json", "back_anim.json", "back_scan.png.key")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    back, scan = build()
    want = {"back.png": back, "back_scan.png": scan}
    want.update({name: (SRC / name).read_bytes() for name in COPIED})
    if args.check:
        stale = [n for n, b in want.items() if not (DEST / n).exists() or (DEST / n).read_bytes() != b]
        if stale:
            print("out of date: " + ", ".join(stale), file=sys.stderr)
            return 1
        print("Cyrus back sprite matches the generator")
        return 0
    DEST.mkdir(parents=True, exist_ok=True)
    for name, data in want.items():
        (DEST / name).write_bytes(data)
        print(f"wrote {(DEST / name).relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
