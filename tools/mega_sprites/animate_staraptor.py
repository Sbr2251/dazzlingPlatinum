#!/usr/bin/env python3
"""Give the Mega Staraptor front and back sprites a real wing-flap idle frame.

Frame 2 of both sheets used to be frame 1 moved down a pixel, so the battle
idle barely moved. This rebuilds frame 2 from frame 1 as a wing beat:

  - each raised wing stretches up and out from its shoulder, the tip moving
    2-3 px and the motion easing to nothing over the inner part of the wing;
  - the crest sways CREST_SWAY px;
  - the head and chest bob BOB px down, easing back to 0 above the talons and
    tail, which stay planted.

The motion is a smooth displacement field: every frame 2 pixel samples frame 1
at its position minus the displacement (nearest pixel), so outlines move with
the feathers and nothing tears. Frame 1 is left untouched, so rerunning this
gives the same result.

Run with: ~/.venvs/desmume/bin/python tools/mega_sprites/animate_staraptor.py
"""

import math
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEGA = os.path.join(ROOT, 'res/pokemon/staraptor/forms/mega')

FRAME = 80
BOB = 1
CREST_SWAY = 1

# Per sheet, in frame coordinates:
#   wings: (shoulder, tip, tip displacement); pixels past `inner` of the way
#          from shoulder to tip move, easing up to the full displacement at the tip.
#   bob:   rows up to bob[0] bob fully, easing to 0 at bob[1] (talons, tail).
#   crest: box (x0, y0, x1, y1) of the red crest, and the side (-1/+1) it
#          sways to; the sway eases in from the box edge nearest the head.
#   inner: fraction of the shoulder-to-tip line that stays put.
SHEETS = {
    'front.png': {
        'wings': [((34, 34), (10, 6), (-2, -3)), ((42, 44), (67, 4), (2, -3))],
        'bob': (50, 58),
        'crest': ((6, 31, 15, 50), -1),
        'inner': 0.3,
    },
    'back.png': {
        'wings': [((27, 40), (5, 4), (-2, -3)), ((53, 40), (75, 4), (2, -3))],
        'bob': (46, 54),
        'crest': ((40, 13, 50, 29), 1),
        'inner': 0.15,
    },
}


def load(path):
    im = Image.open(path)
    ix = Image.frombytes('L', im.size, im.tobytes())
    frames = []
    for ox in (0, FRAME):
        frames.append([[ix.getpixel((ox + x, y)) for x in range(FRAME)] for y in range(FRAME)])
    return im, frames


def smoothstep(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def displacement(cfg, x, y):
    b0, b1 = cfg['bob']
    bob = BOB * (1 - smoothstep((y - b0) / (b1 - b0)))
    dx, dy = 0.0, bob
    for (sx, sy), (tx, ty), (mx, my) in cfg['wings']:
        ax, ay = tx - sx, ty - sy
        t = ((x - sx) * ax + (y - sy) * ay) / (ax * ax + ay * ay)
        w = smoothstep((t - cfg['inner']) / (1 - cfg['inner']))
        # The wing carries the body bob at its root and its own lift at the tip.
        dx += w * mx
        dy += w * (my - bob)
    (x0, y0, x1, y1), side = cfg['crest']
    if x0 <= x <= x1 and y0 <= y <= y1:
        # Ease in from the head side of the box so the face does not shear.
        edge = x1 if side < 0 else x0
        dx += side * CREST_SWAY * smoothstep(abs(x - edge) / 3)
    return dx, dy


def flap(f, cfg):
    out = [[0] * FRAME for _ in range(FRAME)]
    for y in range(1, FRAME - 1):
        for x in range(1, FRAME - 1):
            dx, dy = displacement(cfg, x, y)
            sx, sy = math.floor(x - dx + 0.5), math.floor(y - dy + 0.5)
            if 0 <= sx < FRAME and 0 <= sy < FRAME:
                out[y][x] = f[sy][sx]
    return out


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
        im, frames = load(path)
        base = frames[0]
        second = flap(base, cfg)
        diff = sum(base[y][x] != second[y][x] for y in range(FRAME) for x in range(FRAME))
        save(im, [base, second], path)
        print(f'{name}: frame 1 vs 2 differ in {diff} px')


if __name__ == '__main__':
    main()
