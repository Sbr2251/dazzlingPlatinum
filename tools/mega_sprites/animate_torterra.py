#!/usr/bin/env python3
"""Outline the Mega Torterra back sprite and give both sprites a real idle frame.

Run after fix_torterra.py. The two 80x80 frames of each sheet were near
duplicates (the second only nudged up a pixel), so the battle animation
barely moved. For the front and back sheets this:

  1. takes frame 1, strips its outer outline, and (back only) darkens the
     body/canopy pixels bordering the white spikes so they stand out;
  2. builds frame 2 from frame 1 as a breath: the legs stay planted, the
     shell lifts LIFT_BODY px and the canopy and spike tips lift LIFT_TOP px
     and lean up to SWAY px sideways; rows opened up at each seam repeat the row
     below;
  3. redraws a 1-px index-14 outline on both frames, on transparent pixels
     touching (8-connected) a non-dark body pixel, like fix_torterra.py. On
     the back, narrow crevices (the gap under the right spike, crossed by
     thin wisps) are left open, since outlining them makes a black smudge.

Frame 1 only gains an outline, so rerunning this gives the same result.

Run with: ~/.venvs/desmume/bin/python tools/mega_sprites/animate_torterra.py
"""

import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEGA = os.path.join(ROOT, 'res/pokemon/torterra/forms/mega')

FRAME = 80
OUTLINE = 14
SPIKE_EDGE = 11
# 11 (56,48,48) to 14 (0,0,0) already work as an outline (as in fix_torterra.py);
# 10 (64,80,72) is also dark enough to separate a spike, but still gets outlined.
DARK = {11, 12, 13, 14}
EDGE_DARK = DARK | {10}
SPIKE = {1, 2, 15}

# Per sheet: frame 1 is first moved so its lowest body row is BOTTOM (the back
# drops a row to leave headroom for the lift plus its new outline), then rows
# at or below LEGS stay put, rows above CANOPY get the full lift and the lean,
# and everything between lifts by LIFT_BODY. LEGS and CANOPY are rows after
# the move. OPEN_ONLY skips outlining crevices narrower than 3 px.
SHEETS = {
    'front.png': {'bottom': 75, 'legs': 58, 'canopy': 26, 'spike_edges': False, 'open_only': False},
    'back.png': {'bottom': 77, 'legs': 61, 'canopy': 31, 'spike_edges': True, 'open_only': True},
}
LIFT_BODY = 1
LIFT_TOP = 2
SWAY = -2


def load(path):
    im = Image.open(path)
    ix = Image.frombytes('L', im.size, im.tobytes())
    frames = []
    for ox in (0, FRAME):
        frames.append([[ix.getpixel((ox + x, y)) for x in range(FRAME)] for y in range(FRAME)])
    return im, frames


def neighbours8(x, y):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if (dx or dy) and 0 <= x + dx < FRAME and 0 <= y + dy < FRAME:
                yield x + dx, y + dy


def strip_outline(f):
    # The outline is the index-14 ring on the silhouette; enclosed black stays.
    edge = [(x, y) for y in range(FRAME) for x in range(FRAME)
            if f[y][x] == OUTLINE and any(f[ny][nx] == 0 for nx, ny in neighbours8(x, y))]
    for x, y in edge:
        f[y][x] = 0


def move_to_bottom(f, bottom):
    rows = [y for y in range(FRAME) if any(f[y])]
    dy = bottom - rows[-1]
    if dy:
        f[:] = [list(f[y - dy]) if 0 <= y - dy < FRAME else [0] * FRAME for y in range(FRAME)]


def darken_spike_edges(f):
    hits = []
    for y in range(FRAME):
        for x in range(FRAME):
            v = f[y][x]
            if v == 0 or v in SPIKE or v in EDGE_DARK:
                continue
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < FRAME and 0 <= ny < FRAME and f[ny][nx] in SPIKE:
                    hits.append((x, y))
                    break
    for x, y in hits:
        f[y][x] = SPIKE_EDGE


def breathe(f, legs, canopy):
    def lift(y):
        return 0 if y >= legs else LIFT_BODY if y >= canopy else LIFT_TOP

    out = [[0] * FRAME for _ in range(FRAME)]
    filled = [False] * FRAME
    for y in range(FRAME):
        dy = y - lift(y)
        # Lean rather than shear: the sway grows from 0 at the seam to SWAY at the top.
        dx = round(SWAY * (canopy - y) / canopy) if y < canopy else 0
        for x in range(FRAME):
            v = f[y][x]
            if v and 0 <= x + dx < FRAME:
                out[dy][x + dx] = v
        filled[dy] = True
    # Stretch: an opened-up row repeats the row below it.
    for y in range(FRAME - 2, -1, -1):
        if not filled[y]:
            out[y] = list(out[y + 1])
            filled[y] = True
    return out


def open_background(f):
    # Transparent pixels with an all-transparent 3x3, flood-filled from the edge.
    def wide(x, y):
        return f[y][x] == 0 and all(f[ny][nx] == 0 for nx, ny in neighbours8(x, y))

    stack = [(x, y) for y in range(FRAME) for x in range(FRAME)
             if (x in (0, FRAME - 1) or y in (0, FRAME - 1)) and wide(x, y)]
    seen = set(stack)
    while stack:
        x, y = stack.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < FRAME and 0 <= ny < FRAME and (nx, ny) not in seen and wide(nx, ny):
                seen.add((nx, ny))
                stack.append((nx, ny))
    return seen


def draw_outline(f, open_only):
    bg = open_background(f) if open_only else None
    ring = [(x, y) for y in range(FRAME) for x in range(FRAME)
            if f[y][x] == 0 and any(f[ny][nx] and f[ny][nx] not in DARK
                                    for nx, ny in neighbours8(x, y))
            and (bg is None or (x, y) in bg or any(n in bg for n in neighbours8(x, y)))]
    for x, y in ring:
        f[y][x] = OUTLINE


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
        strip_outline(base)
        move_to_bottom(base, cfg['bottom'])
        if cfg['spike_edges']:
            darken_spike_edges(base)
        second = breathe(base, cfg['legs'], cfg['canopy'])
        for f in (base, second):
            draw_outline(f, cfg['open_only'])
        diff = sum(base[y][x] != second[y][x] for y in range(FRAME) for x in range(FRAME))
        save(im, [base, second], path)
        print(f'{name}: frame 1 vs 2 differ in {diff} px')


if __name__ == '__main__':
    main()
