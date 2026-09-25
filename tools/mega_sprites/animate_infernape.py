#!/usr/bin/env python3
"""Give the Mega Infernape front and back sprites a real idle frame.

Frame 2 of each sheet was frame 1 nudged a pixel, so the battle animation
barely moved. This rebuilds frame 2 from frame 1 as a flare-up:

  1. the feet stay planted, the hips lift 1 px and everything above the waist
     (torso, arms, head, mane, staff) lifts 2 px; the rows opened at each seam
     repeat the row below, so the torso stretches a little;
  2. the mane streams further out and its tips curl up, the staff flame
     leans outward and up, and the tail flames lift another pixel;
  3. inside the flames the colours climb a pixel while the silhouette stays,
     so the fire flickers instead of just sliding.

Frame 1 is never changed, so rerunning this gives the same result.

Run with: ~/.venvs/desmume/bin/python tools/mega_sprites/animate_infernape.py
"""

import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEGA = os.path.join(ROOT, 'res/pokemon/infernape/forms/mega')

FRAME = 80
# Flame colours: yellow, oranges, reds and the dark red rims.
FLAME = {3, 5, 6, 9, 10, 12}

# Per sheet, all rows/columns in frame coordinates:
#   waist/hips: rows above WAIST lift 2 px, rows above HIPS lift 1 px.
#   mane: (x0, x1, y1, outward) box whose columns get pushed outward
#     (+1 = right, -1 = left) by 1 px past STEP1 and 2 px past STEP2, the
#     outer part also lifting a further pixel.
#   staff: (x0, x1, y1, dx) box around the staff flame, lifted 1 px more and
#     leaned dx px.
#   lift: extra 1 px lift boxes (x0, x1, y0, y1) for the tail flames.
#   flicker: boxes (x0, x1, y0, y1) where flame colours climb a pixel.
SHEETS = {
    'front.png': {
        'waist': 42, 'hips': 52,
        'mane': (56, 80, 28, +1, 60, 68),
        'staff': (0, 12, 17, -1),
        'lift': [(62, 80, 26, 40)],
        'flicker': [(0, 12, 0, 17), (42, 58, 63, 80), (40, 80, 0, 22), (62, 80, 26, 40)],
    },
    'back.png': {
        'waist': 44, 'hips': 54,
        'mane': (0, 32, 27, -1, 26, 16),
        'staff': (62, 80, 28, +1),
        'lift': [(0, 24, 28, 42)],
        'flicker': [(0, 45, 0, 27), (64, 80, 0, 28), (0, 24, 28, 42)],
    },
}


def load(path):
    im = Image.open(path)
    ix = Image.frombytes('L', im.size, im.tobytes())
    return im, [[ix.getpixel((x, y)) for x in range(FRAME)] for y in range(FRAME)]


def inside(box, x, y):
    x0, x1, y0, y1 = box
    return x0 <= x < x1 and y0 <= y < y1


def offsets(cfg, x, y):
    """Where in frame 1 the frame 2 pixel (x, y) is pulled from, as (dx, dy)."""
    oy = 2 if y < cfg['waist'] else 1 if y < cfg['hips'] else 0
    ox = 0
    mx0, mx1, my1, out, step1, step2 = cfg['mane']
    if mx0 <= x < mx1 and y < my1:
        # Measured outward, so the same thresholds work for either direction.
        far = x if out > 0 else -x
        s1, s2 = (step1, step2) if out > 0 else (-step1, -step2)
        if far >= s2:
            ox -= 2 * out
            oy += 1
        elif far >= s1:
            ox -= out
    sx0, sx1, sy1, lean = cfg['staff']
    if sx0 <= x < sx1 and y < sy1:
        ox -= lean
        oy += 1
    if any(inside(b, x, y) for b in cfg['lift']):
        oy += 1
    return ox, oy


def build_second(base, cfg):
    second = [[0] * FRAME for _ in range(FRAME)]
    for y in range(FRAME):
        for x in range(FRAME):
            ox, oy = offsets(cfg, x, y)
            sx, sy = x + ox, y + oy
            if 0 <= sx < FRAME and 0 <= sy < FRAME:
                second[y][x] = base[sy][sx]
    flickered = [row[:] for row in second]
    for y in range(FRAME - 1):
        for x in range(FRAME):
            if not any(inside(b, x, y) for b in cfg['flicker']):
                continue
            here, below = second[y][x], second[y + 1][x]
            if here in FLAME and below in FLAME:
                flickered[y][x] = below
    return flickered


def save(im, frames, path):
    ix = Image.new('L', im.size)
    for i, f in enumerate(frames):
        for y in range(FRAME):
            for x in range(FRAME):
                ix.putpixel((i * FRAME + x, y), f[y][x])
    out = Image.frombytes('P', im.size, ix.tobytes())
    out.putpalette(im.getpalette())
    out.save(path, bits=4)


def main():
    for name, cfg in SHEETS.items():
        path = os.path.join(MEGA, name)
        im, base = load(path)
        second = build_second(base, cfg)
        border = sum(1 for i in range(FRAME) for v in (second[0][i], second[-1][i], second[i][0], second[i][-1]) if v)
        diff = sum(base[y][x] != second[y][x] for y in range(FRAME) for x in range(FRAME))
        save(im, [base, second], path)
        print(f'{name}: frame 1 vs 2 differ in {diff} px, {border} border px')


if __name__ == '__main__':
    main()
