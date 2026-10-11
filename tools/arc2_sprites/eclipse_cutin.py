#!/usr/bin/env python3
"""Eclipse mark for the boss battle intro (replaces the Galactic "G" in res/trainers/classes/.shared/enc_galactic.png).

    ~/.venvs/desmume/bin/python tools/arc2_sprites/eclipse_cutin.py           # write the PNG
    ~/.venvs/desmume/bin/python tools/arc2_sprites/eclipse_cutin.py --check   # fail if stale

enc_galactic is the 128x128 sprite EncounterEffect_GalacticBoss (src/overlay005/encounter_effect_core.c)
zooms over the screen for ENCEFF_GALACTIC_CMDR (Commanders and TRAINER_CLASS_ECLIPSE_LEADER). New pixels:
the Team Eclipse mark as art-ph drew it on the crates (a dark disc inside a violet ring, eight short rays:
the eclipsed sun), at this size with a thin pale corona between disc and ring, shaded rays and a black
outline. Same file format as the stock sprite (8-bit indexed PNG, 16 colours, index 0 transparent), so the
cell/anim JSON and the build are unchanged.
"""

from __future__ import annotations

import argparse
import io
import math
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "res/trainers/classes/.shared/enc_galactic.png"
SIZE = 128
C = 64.0

PALETTE = [
    (148, 148, 0),    # 0 transparent (stock key colour)
    (12, 8, 20),      # 1 outline
    (22, 14, 38),     # 2 disc
    (40, 28, 66),     # 3 disc rim shade
    (246, 234, 255),  # 4 corona
    (78, 30, 140),    # 5 ring dark
    (138, 76, 226),   # 6 ring
    (196, 150, 255),  # 7 ring light
    (100, 46, 176),   # 8 ray dark
    (168, 112, 248),  # 9 ray light
    (222, 196, 255),  # 10 ray glint
] + [(0, 0, 0)] * 5

R_DISC, R_CORONA, R_RING_IN, R_RING_OUT = 25.0, 28.0, 29.0, 40.0
RAY_IN, RAY_OUT, RAY_HALF = 41.0, 61.0, 0.20  # radians half-width at the base


def pixel(x: int, y: int) -> int:
    dx = x + 0.5 - C
    dy = y + 0.5 - C
    r = math.hypot(dx, dy)
    a = math.atan2(dy, dx)
    light = -(dx + dy) / (r * math.sqrt(2)) if r else 0  # 1 toward the upper left
    if r <= R_DISC:
        return 3 if r > R_DISC - 3 and light < -0.2 else 2
    if r <= R_CORONA:
        return 4
    if R_RING_IN <= r <= R_RING_OUT:
        t = (r - R_RING_IN) / (R_RING_OUT - R_RING_IN)
        if light > 0.55 and 0.25 < t < 0.6:
            return 7
        return 5 if (light < -0.3 or t > 0.85) else 6
    if RAY_IN <= r <= RAY_OUT:
        # eight rays, tapering to a point at RAY_OUT
        k = round((a - math.pi / 8) / (math.pi / 4))
        centre = math.pi / 8 + k * (math.pi / 4)
        d = (a - centre + math.pi) % (2 * math.pi) - math.pi
        half = RAY_HALF * (RAY_OUT - r) / (RAY_OUT - RAY_IN) * (RAY_IN / r) * 1.6
        if abs(d) <= half:
            # one half of each ray lit, the other shaded, flipping with the light side
            v = 9 if (light > 0 and d > 0) or (light <= 0 and d < 0) else 8
            if abs(d) < half * 0.25 and r < RAY_IN + 8 and light > 0.3:
                v = 10
            return v
    return 0


def build() -> Image.Image:
    px = [[pixel(x, y) for x in range(SIZE)] for y in range(SIZE)]
    out = [row[:] for row in px]
    for y in range(SIZE):
        for x in range(SIZE):
            if px[y][x]:
                continue
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < SIZE and 0 <= ny < SIZE and px[ny][nx]:
                    out[y][x] = 1
                    break
    # a black line between the ring and the rays' roots / corona and ring reads crisper
    for y in range(SIZE):
        for x in range(SIZE):
            r = math.hypot(x + 0.5 - C, y + 0.5 - C)
            if R_CORONA < r < R_RING_IN or (R_RING_OUT < r < RAY_IN and out[y][x]):
                out[y][x] = 1
    im = Image.new("P", (SIZE, SIZE))
    flat = []
    for rgb in PALETTE:
        flat += [((c >> 3) << 3) | (c >> 5) for c in rgb]
    im.putpalette(flat + [0] * (768 - len(flat)))
    im.putdata([v for row in out for v in row])
    return im


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    buf = io.BytesIO()
    build().save(buf, format="PNG", optimize=False)
    data = buf.getvalue()
    if args.check:
        if OUT.read_bytes() != data:
            print("out of date: enc_galactic.png", file=sys.stderr)
            return 1
        print("Eclipse cut-in matches the generator")
        return 0
    OUT.write_bytes(data)
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
