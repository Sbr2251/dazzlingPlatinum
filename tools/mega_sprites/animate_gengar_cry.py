#!/usr/bin/env python3
"""Mega Gengar cry pose: build frame 2 of the front and back sprites from frame 1.

The Mega sprites show frame 1 for ~18 ticks and frame 2 for ~26 ticks, then
stop. Frame 2 is a one-shot cry pose.

Frame 2 is the frame-1 drawing with parts moved. Nothing is re-rendered, and
the pool, the ground and the lower body are the frame-1 pixels in place:

  front "Cackling lean": the head leans right as a banded shift (spike tips
      +4, crown +3, face +2, jaw +2/+1). The left claw rises 3 px and the
      right claw 4, and each swings 4 px out, as rigid frame-1 clusters.
      The right claw clears the head spikes with a transparent wedge
      channel that ends in an armpit cap, and its forearm wall steps back
      toward the body in 1-px steps over a shadow wedge. The jaw drops
      2 px: a maroon row broken by two fang tips, then a row with a small
      tongue, and the frame-1 lower teeth and lip sit 2 px lower. Rows 51+
      are frame 1.
  back "Shrug and fling": the head and ears tilt right (+3/+2/+1). Both
      arms rise 3 px as frame-1 pixel sets, with a per-row shear that
      splays them out (left -3/-4/-5, right +2/+3/+4). Only the shoulders
      and armpits are drawn by hand. The body, legs and pool are frame 1.

Moves copy frame-1 pixels (`move`, and the shifts in `build_back`). A
few hand patches (`apply_patch`: '.' keep, '_' clear, hex digit = palette
index) close the outlines where moved parts meet fixed ones.

Hard rules the script asserts: frame 1 stays byte-identical to res/, frame 2
uses only palette indices that frame 1 uses, and frame 2 keeps a 2-px
transparent margin.

Usage (with ~/.venvs/desmume/bin/python):
  animate_gengar_cry.py              write previews/gengar_{front,back}.png
  animate_gengar_cry.py --previews   ... plus the GIFs and gengar_frames.png
  animate_gengar_cry.py --install    write res/pokemon/gengar/forms/mega/
                                     {front,back}.png instead
"""

import argparse
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEGA = os.path.join(ROOT, 'res/pokemon/gengar/forms/mega')
PREVIEWS = os.path.join(ROOT, 'tools/mega_sprites/previews')
FRAME = 80
MARGIN = 2          # frame 2 art stays this many px away from every edge

CHARS = '0123456789abcdef'


def load(path):
    im = Image.open(path)
    ix = Image.frombytes('L', im.size, im.tobytes())
    return im, [[ix.getpixel((x, y)) for x in range(im.width)] for y in range(im.height)]


def frame1(rows):
    return [r[:FRAME] for r in rows[:FRAME]]


def apply_patch(img, patch):
    """patch: [(y, x0, 'chars')]. '.' keeps, '_' clears, a hex digit sets that index."""
    for y, x0, s in patch:
        for i, ch in enumerate(s):
            if ch == '.':
                continue
            img[y][x0 + i] = 0 if ch == '_' else CHARS.index(ch)


def cells_of(img, spec):
    """spec: {y: (x0, x1)} inclusive ranges -> the non-transparent cells."""
    out = []
    for y, rng in spec.items():
        ranges = rng if isinstance(rng[0], tuple) else [rng]
        for x0, x1 in ranges:
            out += [(x, y) for x in range(x0, x1 + 1) if img[y][x]]
    return out


def move(img, src, moves):
    """moves: [(cells, dx, dy)]. Every listed cell is cleared first, then the
    frame-1 pixel is painted at its new place (later moves paint on top)."""
    for cells, _, _ in moves:
        for x, y in cells:
            img[y][x] = 0
    for cells, dx, dy in moves:
        for x, y in cells:
            img[y + dy][x + dx] = src[y][x]


def rows_spec(y0, y1, x0, x1):
    return {y: (x0, x1) for y in range(y0, y1 + 1)}


# ---------------------------------------------------------------- front --
# Left claw (frame-1 cells): the spread fingers and the lit palm, above the
# dark forearm that rises out of the pool.
FRONT_LCLAW = {41: [(16, 17), (21, 22)], 42: [(16, 17), (20, 22)],
               43: (14, 22), 44: (14, 22), 45: (14, 22), 46: (13, 22),
               47: (6, 21), 48: (6, 21), 49: (5, 21), 50: (5, 21),
               51: (5, 22), 52: (5, 21)}
# Right claw: the dark spiky hand with its lit inner edge, everything right
# of the body's flank outline (x55 on rows 47-49), down to its wrist.
FRONT_RCLAW = {**{y: (59, 68) for y in range(36, 43)},
               43: (58, 68), 44: (58, 68),
               **{y: (56, 68) for y in range(45, 56)}}
FRONT_LCLAW_MOVE = (-4, -3)     # up 3 and out 4 px, away from the face
FRONT_RCLAW_MOVE = (4, -4)      # up 4 and out 4 px, clear of the head
# Head lean: (y0, y1, x0, x1, dx). Spike tips +4, crown +3, face +2; the jaw
# rows lean +2 left of the mouth corner and +1 right of it. Each band edge
# is a 1-px step, so the outlines stay diagonal. Rows 48+ (chin, belly,
# pool) do not move.
FRONT_HEAD_BANDS = [(0, 15, 0, 79, 4), (16, 27, 0, 79, 3), (28, 40, 0, 79, 2),
                    (41, 47, 0, 43, 2), (41, 47, 44, 79, 1)]

# Open mouth (frame-2 coordinates). The upper teeth are frame-1 rows 43-45
# (moved with the face). Under them the mouth opens 2 px: a maroon (7) row
# with e corners, broken by the two fang tips (x34, x38) that hang 1 px
# below the upper teeth, then a row with a small rounded tongue (7887) whose
# ends are the lower teeth's outer tips, 1 px higher than the other teeth. The frame-1 lower
# teeth (rows 46-47) and lower lip (row 48) drop 2 px, and row 51 keeps the
# frame-1 chin fill.
FRONT_MOUTH = [
    (46, 30, '1' 'ddddddddddd' '1'),              # x30-42, dark interior
    (47, 26, 'dfff' '15' 'ddccccdd' '61'),       # x26-41, red tongue; tooth ends rise
    (48, 26, 'dfff15' '6bbb6bbb6' '1'),          # lower teeth, frame-1 row 46
    (49, 29, 'ff1' '6bbb6bb5' '1'),              # frame-1 row 47
    (50, 29, 'fffe' '11111' 'eff'),              # lower lip, frame-1 row 48
    (51, 29, 'fffffffffffff'),                   # chin fill, as frame 1
]
# Left cheek: the claw no longer covers it; give it a clean outline that
# bulges 1 px at the cheek (rows 44-45) and tucks 1 px in under the chin
# (row 50), where the dropped jaw meets the body.
FRONT_CHEEK = [
    (41, 24, 'd'),
    (44, 24, '_de'), (45, 24, '_de'), (46, 25, 'de'),
    (48, 25, '_'),
    (49, 21, '_____d'),
    (50, 22, '__'), (50, 26, 'df'),
]
# Left claw: the inner finger's outline stayed with the head, so redraw it
# (frame-1 x23 moved with the claw), then the wrist. Three rows of frame-1
# forearm (row 53) step back from the claw's -4 offset (-2, -1, 0), so both
# walls of the wrist lean like a raised arm; the top wrist row carries the
# palm's lit patch (frame-1 row 52's 3s) down 1 px so it is not a flat tube.
FRONT_LHAND = [
    *[(y, 19, 'd') for y in range(38, 43)],
    (49, 18, 'd'),
    (50, 6, 'dff33fffeee1d_'),
    (51, 7, 'dffffffffee1d_'),
    (52, 8, 'dffffffffee1d_'),
    (44, 5, '__'), (45, 5, 'd1'),     # claw tip: 2 px wide, no lone spur
]
# Right claw: outline its left edge (it used to sit against the body), close
# the body's flank, and run the frame-1 wrist strip (row 55: 333f1ed) down
# and back to the body in 1-px steps, so the raised hand stays attached.
# A 2-4 px transparent channel separates hand and head/body on rows 38-51
# (the shoulder spike loses its last tip pixel to keep it 2 px wide).
FRONT_RHAND = [
    (39, 60, '_'),                    # trim the shoulder spike's 1-px tip
    (40, 62, 'd'), (41, 60, '_'),
    (38, 63, 'd2'),                   # the claw's inner wall steps 1 px
    (39, 62, '_d'), (40, 62, '_d'),   # right at the top: the channel is a
                                      # wedge, 4-3-3 px wide above 2 px
    *[(y, 60, 'd') for y in range(42, 46)],
    (42, 57, 'd'), (44, 58, '_'),
    (46, 55, '2' '1dd' 'd3'),         # armpit cap closes the channel
    (47, 55, '322333'),               # below it the forearm's lit edge
    (48, 54, '223333'),               # melts into the body (as in frame 1's
    (49, 55, '23333'),                # rows 52-54), with a soft 2 crease
    (50, 55, '233333'),               # instead of a dark contour
    (51, 55, '23333'),
    (48, 63, '1'),                    # no loose outline pixel in the palm
    (35, 65, '_'), (36, 65, 'd'),     # claw-tip spurs: blunt 2-px tips
    (32, 71, '_'), (42, 72, '_'),
    (52, 55, '3333333f1ed'),
    (53, 55, '333333f1ed'),
    (54, 55, '33333f1ed'),
    (55, 55, '3333f1ed'),
]
# Outline pixel where the lean bands meet, so the left edge stays a diagonal.
FRONT_SEAMS = [(27, 26, '1')]


def build_front(f1):
    img = [r[:] for r in f1]
    lclaw = set(cells_of(f1, FRONT_LCLAW))
    rclaw = set(cells_of(f1, FRONT_RCLAW))
    moves = []
    for y0, y1, x0, x1, dx in FRONT_HEAD_BANDS:
        cells = [c for c in cells_of(f1, rows_spec(y0, y1, x0, x1))
                 if c not in lclaw and c not in rclaw]
        moves.append((cells, dx, 0))
    moves.append((sorted(lclaw), *FRONT_LCLAW_MOVE))
    moves.append((sorted(rclaw), *FRONT_RCLAW_MOVE))
    move(img, f1, moves)
    for patch in (FRONT_MOUTH, FRONT_CHEEK, FRONT_LHAND, FRONT_RHAND, FRONT_SEAMS):
        apply_patch(img, patch)
    return img


# ----------------------------------------------------------------- back --
# "Shrug and fling": the head tilts right and both arms lift up and splay
# out as frame-1 pixels. The body, legs and pool do not move at all.
#
# Head/ears tilt right as three bands, so the top moves most (a rotation):
# rows 0-16 +3, rows 17-21 +2, rows 22-25 +1.
BACK_HEAD_BANDS = [(0, 16, 3), (17, 21, 2), (22, 25, 1)]
# Arms (frame-1 cells, inclusive x ranges). The left lobe is everything left
# of the arm/body crease; the right lobe is everything right of the body wall,
# from the shoulder (row 30) down to the claws.
BACK_LARM = {35: (19, 19), 36: (18, 19), 37: (17, 18), 38: (17, 20), 39: (16, 19),
             40: (16, 19), 41: (15, 19), 42: (15, 19), 43: (14, 19), 44: (14, 19),
             45: (14, 20), 46: (14, 20), 47: (14, 20), 48: (13, 21), 49: (14, 20),
             50: (13, 19), 51: (14, 19), 52: (16, 19)}
BACK_RARM = {**{y: (59, 70) for y in range(30, 46)}, 46: (57, 70), 47: (58, 70),
             48: (59, 70), 49: (60, 70), 50: (61, 70), 51: (61, 70),
             **{y: (62, 70) for y in range(52, 55)}}


def back_lmove(y):
    """Left arm: 3 up for every row; out 3 (upper arm), 4 (forearm), 5 (claws).
    One dy for all rows, so every frame-1 row survives exactly once; the
    per-row dx is a shear that angles the arm away from the body."""
    return (-3, -3) if y <= 39 else (-4, -3) if y <= 44 else (-5, -3)


def back_rmove(y):
    """Right arm: 3 up; out 2, 3, 4 px down the arm (mirror of the left)."""
    return (2, -3) if y <= 39 else (3, -3) if y <= 44 else (4, -3)


# Hand-drawn joints (frame-2 coordinates). Left: the shoulder becomes a
# sloped highlight rim with a crease, the armpit a tapered wedge whose inner
# wall is the body's outline at x19-21. Right: the shoulder slopes down
# (58,28)-(62,30), the armpit is a wedge between the arm's inner wall (x58)
# and the body wall, which curves in to x57 on rows 39-44.
BACK_LJOINT = [
    (31, 19, '614'), (32, 16, '_66144'), (33, 16, '6144444'), (34, 15, '4155443'),
    (35, 17, '34433'), (36, 17, '14433'), (37, 15, 'd_d4'), (38, 18, 'd41'),
    (39, 18, 'd4'), *[(y, 19, 'd') for y in range(40, 45)], (41, 15, 'd'),
    (45, 15, 'd_'), (45, 20, 'd'), (46, 20, 'd'), (47, 20, 'd'), (48, 21, 'd'),
    (49, 20, 'd'),
]
BACK_RJOINT = [
    (28, 59, 'd_'), (28, 61, '_'), (29, 58, '34dd'), (30, 59, '44'), (31, 59, '444'),
    (32, 59, '43'), (33, 59, 'd1'),
    *[(y, 58, 'd') for y in range(34, 46)],
    *[(y, 60, 'd') for y in range(34, 37)],
    *[(y, 61, 'd') for y in range(37, 42)],
    (42, 62, 'd'), (43, 61, '_d'), (44, 62, 'd'),
    (46, 57, '1d'), (47, 58, 'd'), (47, 65, 'd'),
    *[(y, 57, 'd_') for y in range(39, 45)],
]

# Round 7: taper both arms toward a rounded hand, outline the shoulder rims,
# and give the right body wall a bulge instead of a straight cut.
BACK_LARM_FIX = [
    (30, 19, 'd'), (31, 17, 'dd'), (32, 15, 'dd'), (33, 14, 'd'),   # rim outline
    (34, 13, 'd'), (35, 13, 'd'),
    (41, 7, '___d543d__'),            # inner wall steps in: 15 -> 14 -> 13
    (42, 7, '__e5331d__'),
    (43, 7, '__13331d__'),
    (44, 7, '__13311d__'),
    (45, 7, '_d13321d__'),            # palm, closed outer outline
    (46, 7, '_d13121d__'),
    (47, 7, '_d1131d___'),            # rounded tip
    (48, 7, '__d131d___'),
    (49, 7, '___ddd____'),
    (41, 18, 'd4'), (42, 18, 'd4'), (43, 18, 'd4'),   # body wall bulges 1 px
    (49, 20, '_d'),                   # no 1-px nub on the body wall
]
BACK_RARM_FIX = [
    (33, 64, 'd'), (34, 65, 'd'),     # rim outline
    (34, 58, '2d3'), (35, 58, '2d3'), (36, 58, '2d'),   # armpit apex, no slit
    (39, 57, '22d__d223'),            # body wall bulges out (x59-60) while
    (40, 57, '22d__d222'),            # the arm's inner wall leans with the
    (41, 57, '221d__d222'),           # arm, so the gap is a 2-px wedge
    (42, 57, '221d__d'),
    (43, 57, '21d____d3222'),
    (44, 57, '1d_____d1222'),
    (45, 63, '__d43211d'),            # hand tapers to a rounded tip
    (46, 64, '_de3321d'),
    (47, 65, '_d3311d'),
    (48, 65, '_d1331d'),
    (49, 66, '_d131d'),
    (50, 66, '__ddd_'),
    (51, 66, '____'),
]


def build_back(f1):
    larm = cells_of(f1, BACK_LARM)
    rarm = cells_of(f1, BACK_RARM)
    img = [r[:] for r in f1]
    for x, y in larm + rarm:
        img[y][x] = 0
    tilted = [r[:] for r in img]
    for y0, y1, dx in BACK_HEAD_BANDS:
        for y in range(y0, y1 + 1):
            tilted[y] = [0] * FRAME
            for x in range(FRAME):
                if img[y][x]:
                    tilted[y][x + dx] = img[y][x]
    img = tilted
    for cells, mv in ((larm, back_lmove), (rarm, back_rmove)):
        for x, y in cells:
            dx, dy = mv(y)
            img[y + dy][x + dx] = f1[y][x]
    apply_patch(img, BACK_LJOINT + BACK_RJOINT + BACK_LARM_FIX + BACK_RARM_FIX)
    return img


# ---------------------------------------------------------------- rules --
def check_rules(side, f1_res, f1, f2):
    assert f1 == f1_res, f'{side}: frame 1 differs from res/'
    used = {c for r in f1 for c in r}
    extra = {c for r in f2 for c in r} - used
    assert not extra, f'{side}: frame 2 uses indices not in frame 1: {sorted(extra)}'
    for y in range(FRAME):
        for x in range(FRAME):
            edge = min(x, y, FRAME - 1 - x, FRAME - 1 - y)
            assert edge >= MARGIN or f2[y][x] == 0, \
                f'{side}: frame 2 pixel ({x},{y}) is within {MARGIN} px of the edge'
    assert f2 != f1, f'{side}: frame 2 equals frame 1'


# ------------------------------------------------------------------ I/O --
def write_sheet(src_im, rows_f1, rows_f2, path):
    data = bytearray()
    for y in range(FRAME):
        data.extend(rows_f1[y])
        data.extend(rows_f2[y])
    out = Image.frombytes('P', (FRAME * 2, FRAME), bytes(data))
    out.putpalette(src_im.getpalette())
    out.save(path, bits=4, transparency=0)


# ------------------------------------------------------------- previews --
PREVIEW_BG = (200, 208, 216)
GIF_DURATIONS = [300, 430, 1000]   # frame 1, frame 2, frame 1 (ms)


def read_pal(path):
    with open(path) as f:
        lines = f.read().split()
    n = int(lines[2])
    vals = [int(v) for v in lines[3:3 + 3 * n]]
    return [tuple(vals[i:i + 3]) for i in range(0, len(vals), 3)]


def render(rows, pal, scale):
    im = Image.new('RGB', (FRAME, FRAME))
    im.putdata([PREVIEW_BG if c == 0 else pal[c] for r in rows for c in r])
    return im.resize((FRAME * scale, FRAME * scale), Image.NEAREST)


def write_gif(f1, f2, pal, scale, path):
    a, b = render(f1, pal, scale), render(f2, pal, scale)
    a.save(path, save_all=True, append_images=[b, a.copy()],
           duration=GIF_DURATIONS, loop=0, optimize=False, disposal=1)


def write_previews(frames):
    pals = {k: read_pal(os.path.join(MEGA, k + '.pal')) for k in ('normal', 'shiny')}
    for side, (f1, f2) in frames.items():
        base = os.path.join(PREVIEWS, 'gengar_' + side)
        write_gif(f1, f2, pals['normal'], 4, base + '.gif')
        write_gif(f1, f2, pals['shiny'], 4, base + '_shiny.gif')
        write_gif(f1, f2, pals['normal'], 1, base + '_1x.gif')
    scale = 5
    cell = FRAME * scale
    sheet = Image.new('RGB', (cell * 2, cell * 4), PREVIEW_BG)
    for r, (side, palname) in enumerate([('front', 'normal'), ('front', 'shiny'),
                                          ('back', 'normal'), ('back', 'shiny')]):
        for c, rows in enumerate(frames[side]):
            sheet.paste(render(rows, pals[palname], scale), (c * cell, r * cell))
    sheet.save(os.path.join(PREVIEWS, 'gengar_frames.png'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--install', action='store_true')
    ap.add_argument('--previews', action='store_true')
    a = ap.parse_args()
    outdir = MEGA if a.install else PREVIEWS
    os.makedirs(outdir, exist_ok=True)
    frames = {}
    for side, build in (('front', build_front), ('back', build_back)):
        im, rows = load(os.path.join(MEGA, side + '.png'))
        f1 = frame1(rows)
        f2 = build(f1)
        check_rules(side, f1, f1, f2)
        frames[side] = (f1, f2)
    # Build everything from the untouched sheets before writing anything.
    for side, (f1, f2) in frames.items():
        im, _ = load(os.path.join(MEGA, side + '.png'))
        path = os.path.join(outdir, (side if a.install else 'gengar_' + side) + '.png')
        write_sheet(im, f1, f2, path)
        # Re-read what was written: frame 1 must still match res/ byte for byte.
        out, rows = load(path)
        assert out.size == (FRAME * 2, FRAME) and out.mode == 'P', path
        got_f1 = frame1(rows)
        got_f2 = [r[FRAME:] for r in rows]
        check_rules(side, f1, got_f1, got_f2)
        assert got_f2 == f2, f'{side}: frame 2 changed on save'
    if a.previews:
        os.makedirs(PREVIEWS, exist_ok=True)
        write_previews(frames)


if __name__ == '__main__':
    main()
