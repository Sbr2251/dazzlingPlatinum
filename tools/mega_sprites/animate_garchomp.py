#!/usr/bin/env python3
"""Give the Mega Garchomp back sprite an idle frame that keeps the rear view.

Frame 2 of back.png was a side-on three-quarter pose, so the battle idle
flipped Garchomp between two viewpoints. Frame 1 is the correct rear view
(back to the camera, both blade-arms raised, like the base Garchomp back),
so it is kept as is and frame 2 is rebuilt from it:

  - feet planted: rows from FEET down do not move;
  - the torso lifts BODY_LIFT px, easing back to 0 between HIPS and FEET;
  - the head lifts HEAD_LIFT px;
  - both blade-arms raise ARM_LIFT px and spread ARM_SPREAD px outward,
    blended into the torso motion near each shoulder;
  - the tail swings TAIL_SWAY px out and 1 px up, and the side fin flares.

Each part's offset is a smooth displacement field, and frame 2 pulls each
pixel from frame 1 at (x, y) minus the offset (inverse mapping), so joints
stretch instead of tearing and no holes open. Frame 1 is never changed, so
rerunning this gives the same result. front.png and the palettes are not
touched.

Run with: ~/.venvs/desmume/bin/python tools/mega_sprites/animate_garchomp.py
"""

import math
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(ROOT, 'res/pokemon/garchomp/forms/mega/back.png')

FRAME = 80
FEET = 64
HIPS = 58
BODY_LIFT = 1
HEAD_LIFT = 2
ARM_LIFT = 3
ARM_SPREAD = 1
TAIL_SWAY = 2
# Shoulder pivots in frame 1; the arm offset fades in over ARM_BLEND px from here.
SHOULDERS = {'left': (25, 30), 'right': (55, 30)}
ARM_BLEND = (2, 8)


def clamp01(v):
    return max(0.0, min(1.0, v))


def region(x, y):
    """Which part a coordinate belongs to, from frame 1's layout."""
    if y <= 31:
        if x <= 29:
            return 'left'
        if (y <= 12 and x >= 48) or x >= 53:
            return 'right'
        return 'head'
    return 'body'


def offset(x, y):
    # Torso: full lift above HIPS, easing to 0 at FEET.
    body = BODY_LIFT * clamp01((FEET - y) / (FEET - HIPS))
    dx, dy = 0.0, -body
    part = region(x, y)
    if part == 'head':
        # Blend the neck from the torso lift (row 32) to the full head lift (row 26).
        w = clamp01((32 - y) / 6)
        dy = -(body + w * (HEAD_LIFT - body))
    elif part in SHOULDERS:
        sx, sy = SHOULDERS[part]
        w = clamp01((math.hypot(x - sx, y - sy) - ARM_BLEND[0]) / (ARM_BLEND[1] - ARM_BLEND[0]))
        spread = -ARM_SPREAD if part == 'left' else ARM_SPREAD
        dx = w * spread
        dy = -(body + w * (ARM_LIFT - body))
    else:
        # Tail and tail fin (lower left): swing out and up, growing toward the tip.
        if 44 <= y <= 67 and x <= 24:
            w = clamp01((24 - x) / 10)
            dx -= w * TAIL_SWAY
            dy -= w * 1
        # Side fin on the left flank flares out and up.
        if 35 <= y <= 45 and x <= 26:
            w = clamp01((27 - x) / 7)
            dx -= w
            dy -= w
    return dx, dy


def load(path):
    im = Image.open(path)
    ix = Image.frombytes('L', im.size, im.tobytes())
    base = [[ix.getpixel((x, y)) for x in range(FRAME)] for y in range(FRAME)]
    return im, base


def idle(base):
    out = [[0] * FRAME for _ in range(FRAME)]
    for y in range(FRAME):
        for x in range(FRAME):
            dx, dy = offset(x, y)
            sx, sy = round(x - dx), round(y - dy)
            if 0 <= sx < FRAME and 0 <= sy < FRAME:
                out[y][x] = base[sy][sx]
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
    im, base = load(PATH)
    second = idle(base)
    border = sum(1 for i in range(FRAME) for v in (second[0][i], second[-1][i], second[i][0], second[i][-1]) if v)
    assert border == 0, f'frame 2 touches the border ({border} px)'
    diff = sum(base[y][x] != second[y][x] for y in range(FRAME) for x in range(FRAME))
    save(im, [base, second], PATH)
    print(f'back.png: frame 1 vs 2 differ in {diff} px')


if __name__ == '__main__':
    main()
