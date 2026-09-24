#!/usr/bin/env python3
"""Remove the solid black box behind the Mega Torterra front sprite.

The front sheet (160x80, two 80x80 frames) drew the art inside a rectangle
of palette index 14 (black) instead of the transparent index 0, so it showed
up in battle as a black square. For each frame this:

  1. flood-fills (4-connected) the index-14 region reachable from the box's
     outer ring to index 0, so black pockets fully enclosed by the art stay;
  2. redraws a 1-px outline in index 14 on transparent pixels that touch
     (8-connected) a non-dark body pixel. The black box had been doubling as
     the outline, and edges that already end in a dark colour are left alone.

A frame is skipped if its outer ring isn't a solid index-14 box, so rerunning
this on an already-fixed sheet changes nothing. The palettes aren't touched.

Run with: ~/.venvs/desmume/bin/python tools/mega_sprites/fix_torterra.py
"""

import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONT = os.path.join(ROOT, 'res/pokemon/torterra/forms/mega/front.png')

FRAME = 80
BOX = 14
OUTLINE = 14
# 11 (56,48,48), 12 (24,24,40), 13 (8,0,8), 14 (0,0,0): already an outline.
DARK = {11, 12, 13, 14}


def fix_frame(px, ox):
    def get(x, y):
        return px[ox + x, y]

    def put(x, y, v):
        px[ox + x, y] = v

    solid = [(x, y) for y in range(FRAME) for x in range(FRAME) if get(x, y)]
    if not solid:
        return 'empty'
    x0 = min(x for x, _ in solid)
    x1 = max(x for x, _ in solid)
    y0 = min(y for _, y in solid)
    y1 = max(y for _, y in solid)
    ring = [(x, y0) for x in range(x0, x1 + 1)] + [(x, y1) for x in range(x0, x1 + 1)]
    ring += [(x0, y) for y in range(y0, y1 + 1)] + [(x1, y) for y in range(y0, y1 + 1)]
    if any(get(x, y) != BOX for x, y in ring):
        return 'no box, skipped'

    stack = list(ring)
    filled = 0
    while stack:
        x, y = stack.pop()
        if not (0 <= x < FRAME and 0 <= y < FRAME) or get(x, y) != BOX:
            continue
        put(x, y, 0)
        filled += 1
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]

    outline = []
    for y in range(FRAME):
        for x in range(FRAME):
            if get(x, y):
                continue
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < FRAME and 0 <= ny < FRAME:
                        v = get(nx, ny)
                        if v and v not in DARK:
                            outline.append((x, y))
                            break
                else:
                    continue
                break
    for x, y in outline:
        put(x, y, OUTLINE)
    return f'box {x1 - x0 + 1}x{y1 - y0 + 1} cleared ({filled} px), outline +{len(outline)} px'


def main():
    im = Image.open(FRONT)
    if im.mode != 'P' or im.size != (2 * FRAME, FRAME):
        sys.exit(f'{FRONT}: expected a 160x80 P-mode sheet, got {im.mode} {im.size}')
    palette = im.getpalette()[:16 * 3]
    idx = Image.frombytes('L', im.size, im.tobytes())
    px = idx.load()
    for frame in range(2):
        print(f'frame {frame}: {fix_frame(px, frame * FRAME)}')

    out = Image.frombytes('P', im.size, idx.tobytes())
    out.putpalette(palette)
    out.save(FRONT, bits=4, optimize=False)


if __name__ == '__main__':
    main()
