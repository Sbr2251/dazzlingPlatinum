#!/usr/bin/env python3
"""Remove the rectangular frame left around Mega Scizor's back sprite.

Both 80x80 frames of the back sprite have a hand-drawn 1-px box in palette
index 8 (the outline colour) around the body. The box is found by flooding
through index 8 from its long top and bottom runs, stopping at any pixel
that touches a body colour, so the body's own outline is kept. Gaps in the
hand-drawn box leave a few loose index 8 pixels; any group of them that
touches no body colour is cleared too.

The back view should show no yellow: the eye and the claw's yellow edge are
front-only details, and the second frame has neither. Any yellow pixel left
on the back is recoloured to the most common colour around it. Palettes are
left untouched. Safe to rerun.
"""
import os
import sys

from PIL import Image

MEGA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'res', 'pokemon', 'scizor', 'forms', 'mega')
FRAME_SIZE = 80
BOX_INDEX = 8
BOX_MIN_RUN = 30
YELLOW_INDICES = (6, 7, 15)


def neighbours(x, y, x0):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = x + dx, y + dy
            if (dx or dy) and x0 <= nx < x0 + FRAME_SIZE and 0 <= ny < FRAME_SIZE:
                yield nx, ny


def touches_body(pixels, x, y, x0):
    return any(pixels[n] not in (0, BOX_INDEX) for n in neighbours(x, y, x0))


def find_box(pixels, x0):
    seeds = []
    for y in range(FRAME_SIZE):
        run = []
        for x in range(x0, x0 + FRAME_SIZE + 1):
            if x < x0 + FRAME_SIZE and pixels[x, y] == BOX_INDEX:
                run.append((x, y))
                continue
            if len(run) >= BOX_MIN_RUN:
                seeds += run
            run = []

    box = set()
    stack = [p for p in seeds if not touches_body(pixels, *p, x0)]
    while stack:
        p = stack.pop()
        if p in box:
            continue
        box.add(p)
        for n in neighbours(*p, x0):
            if n not in box and pixels[n] == BOX_INDEX and not touches_body(pixels, *n, x0):
                stack.append(n)
    return box


def find_loose_pixels(pixels, x0):
    loose = set()
    seen = set()
    for y in range(FRAME_SIZE):
        for x in range(x0, x0 + FRAME_SIZE):
            if (x, y) in seen or pixels[x, y] != BOX_INDEX:
                continue
            group = []
            stack = [(x, y)]
            seen.add((x, y))
            while stack:
                p = stack.pop()
                group.append(p)
                for n in neighbours(*p, x0):
                    if n not in seen and pixels[n] == BOX_INDEX:
                        seen.add(n)
                        stack.append(n)
            if not any(touches_body(pixels, *p, x0) for p in group):
                loose.update(group)
    return loose


def recolour_yellow(pixels, x0):
    yellow = [(x, y) for y in range(FRAME_SIZE) for x in range(x0, x0 + FRAME_SIZE)
              if pixels[x, y] in YELLOW_INDICES]
    # Work inwards so pixels in the middle of a yellow run take the colour
    # already given to their neighbours.
    remaining = set(yellow)
    while remaining:
        progress = False
        for p in sorted(remaining):
            counts = {}
            for n in neighbours(*p, x0):
                i = pixels[n]
                if i and n not in remaining:
                    counts[i] = counts.get(i, 0) + 1
            if not counts:
                continue
            # Prefer a body colour over the outline when tied.
            pixels[p] = max(counts, key=lambda i: (counts[i], i != BOX_INDEX))
            remaining.discard(p)
            progress = True
        if not progress:
            break
    return len(yellow)


def fix_back(path):
    im = Image.open(path)
    palette = im.getpalette()
    indices = Image.frombytes('L', im.size, im.tobytes())
    pixels = indices.load()

    cleared = 0
    recoloured = 0
    for x0 in range(0, im.size[0], FRAME_SIZE):
        for find in (find_box, find_loose_pixels):
            found = find(pixels, x0)
            for p in found:
                pixels[p] = 0
            cleared += len(found)
        recoloured += recolour_yellow(pixels, x0)

    out = Image.frombytes('P', im.size, indices.tobytes())
    out.putpalette(palette[:16 * 3])
    out.save(path, bits=4)
    return cleared, recoloured


def main():
    path = os.path.normpath(os.path.join(MEGA_DIR, 'back.png'))
    cleared, recoloured = fix_back(path)
    print(f'{path}: cleared {cleared} box pixels, recoloured {recoloured} yellow pixels')
    return 0


if __name__ == '__main__':
    sys.exit(main())
