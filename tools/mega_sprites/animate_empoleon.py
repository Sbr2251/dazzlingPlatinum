#!/usr/bin/env python3
"""Give the Mega Empoleon back sprite a real idle frame.

(The front sprite's frame 2 is now the "guard sweep" pose from
animate_empoleon_guard.py; this script only writes back.png.)

Frame 2 of each sheet was frame 1 nudged up a pixel, so the battle idle
looked static. This rebuilds frame 2 from frame 1 as a breath in:

  - feet planted: rows from FEET down do not move, the body lifts BODY_LIFT px
    above HIPS and the legs stretch between;
  - the head and trident crown lift HEAD_LIFT px in total;
  - the blade-flipper on the left swings up about its shoulder, so its tip
    rises 2-3 px (it also rides the body lift, since the arm holds it);
  - the wing on the right swings too: in front the hanging cape flares out
    and up at its lower edge, in back the feather-blades raise their tips.

Each part's motion is a smooth displacement field (a rotation about the joint,
faded in with a soft mask), and frame 2 pulls every pixel from frame 1 at
(x, y) minus the offset (inverse mapping), so joints stretch instead of
tearing, and no new colours or holes appear. Frame 1 is never changed, so
rerunning this gives the same result. The palettes are not touched.

Run with: ~/.venvs/desmume/bin/python tools/mega_sprites/animate_empoleon.py
"""

import math
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEGA = os.path.join(ROOT, 'res/pokemon/empoleon/forms/mega')

FRAME = 80
BODY_LIFT = 1
HEAD_LIFT = 2

# Per sheet, in frame coordinates:
#   hips/feet: the body lift is full above HIPS and fades to 0 at FEET.
#   head: (x0, x1, y_full, y_none) box; the extra head lift is full above
#     y_full and fades out by y_none.
#   blade: pivot, angle in degrees (positive = clockwise on screen) and the
#     line (x, y), (x, y) along its inner edge; pixels left of it swing.
#   wing: pivot, angle, and a function giving the soft mask for a pixel.
SHEETS = {
    'back.png': {
        'hips': 50, 'feet': 64,
        'head': (22, 58, 24, 30),
        'blade': {'pivot': (35, 40), 'angle': 2.4, 'edge': ((37, 44), (25, 60))},
        'wing': {'pivot': (50, 29), 'angle': -4.0, 'mask': 'back_wing'},
    },
}


def clamp01(v):
    return max(0.0, min(1.0, v))


def smooth(v):
    v = clamp01(v)
    return v * v * (3 - 2 * v)


def rotation(x, y, pivot, degrees):
    """Displacement of (x, y) when rotated about pivot (y points down)."""
    a = math.radians(degrees)
    rx, ry = x - pivot[0], y - pivot[1]
    nx = math.cos(a) * rx - math.sin(a) * ry
    ny = math.sin(a) * rx + math.cos(a) * ry
    return nx - rx, ny - ry


def left_of(x, y, edge):
    """Signed distance of (x, y) to the left of the edge line (positive = left)."""
    (x0, y0), (x1, y1) = edge
    ex, ey = x1 - x0, y1 - y0
    # Edges run downwards, so with y pointing down the left side is where
    # this cross product is positive.
    return (ex * (y - y0) - ey * (x - x0)) / math.hypot(ex, ey)


def front_wing(x, y):
    # The cape hangs from the right shoulder. Down to row 44 it touches the
    # dark edge of the body (x <= 56), so fade in across that seam; lower
    # down a gap opens (x 57, then x 60-61) and the wing starts right of it,
    # so the gap stays empty; the wing ends above the right foot.
    if y > 65:
        return 0.0
    if y <= 44:
        return smooth((x - 54.5) / 3)
    return smooth((x - (56.5 if y <= 49 else 60.5)) / 1.5)


def back_wing(x, y):
    # Feather-blades up and right of the head; the white head reaches x 55
    # and the dark back x 56 on the lower rows, so fade in past them.
    if y > 37:
        return 0.0
    seam = 54 if y <= 22 else 52 if y <= 27 else 56
    return smooth((x - seam) / 4) * smooth((38 - y) / 3)


MASKS = {'front_wing': front_wing, 'back_wing': back_wing}


def offset(cfg, x, y):
    body = BODY_LIFT * smooth((cfg['feet'] - y) / (cfg['feet'] - cfg['hips']))
    dx, dy = 0.0, -body

    hx0, hx1, hfull, hnone = cfg['head']
    if hx0 <= x < hx1:
        dy -= (HEAD_LIFT - BODY_LIFT) * smooth((hnone - y) / (hnone - hfull))

    # The blade and wing are held at the shoulder, so they ride the full
    # body lift plus their own swing, whatever row they reach down to.
    blade = cfg['blade']
    m = smooth((left_of(x, y, blade['edge']) + 1) / 3)
    if m:
        rx, ry = rotation(x, y, blade['pivot'], blade['angle'])
        dx = (1 - m) * dx + m * rx
        dy = (1 - m) * dy + m * (ry - BODY_LIFT)

    wing = cfg['wing']
    m = MASKS[wing['mask']](x, y)
    if m:
        rx, ry = rotation(x, y, wing['pivot'], wing['angle'])
        dx = (1 - m) * dx + m * rx
        dy = (1 - m) * dy + m * (ry - BODY_LIFT)
    return dx, dy


def load(path):
    im = Image.open(path)
    ix = Image.frombytes('L', im.size, im.tobytes())
    return im, [[ix.getpixel((x, y)) for x in range(FRAME)] for y in range(FRAME)]


def build_second(base, cfg):
    second = [[0] * FRAME for _ in range(FRAME)]
    for y in range(FRAME):
        for x in range(FRAME):
            dx, dy = offset(cfg, x, y)
            sx, sy = math.floor(x - dx + 0.5), math.floor(y - dy + 0.5)
            if 0 <= sx < FRAME and 0 <= sy < FRAME:
                second[y][x] = base[sy][sx]
    return second


def lonely(frame):
    """Opaque pixels with no opaque 8-neighbour."""
    n = 0
    for y in range(FRAME):
        for x in range(FRAME):
            if frame[y][x] and not any(
                frame[y + j][x + i]
                for j in (-1, 0, 1) for i in (-1, 0, 1)
                if (i or j) and 0 <= x + i < FRAME and 0 <= y + j < FRAME
            ):
                n += 1
    return n


def save(im, frames, path):
    ix = Image.new('L', im.size)
    for i, f in enumerate(frames):
        for y in range(FRAME):
            for x in range(FRAME):
                ix.putpixel((i * FRAME + x, y), f[y][x])
    out = Image.frombytes('P', im.size, ix.tobytes())
    out.putpalette(im.getpalette())
    out.save(path, bits=4, transparency=0)


def main():
    for name, cfg in SHEETS.items():
        path = os.path.join(MEGA, name)
        im, base = load(path)
        second = build_second(base, cfg)
        border = sum(1 for i in range(FRAME) for v in (second[0][i], second[-1][i], second[i][0], second[i][-1]) if v)
        assert border == 0, f'{name}: frame 2 touches the border ({border} px)'
        diff = sum(base[y][x] != second[y][x] for y in range(FRAME) for x in range(FRAME))
        save(im, [base, second], path)
        print(f'{name}: frame 1 vs 2 differ in {diff} px, lonely px {lonely(base)} -> {lonely(second)}')


if __name__ == '__main__':
    main()
