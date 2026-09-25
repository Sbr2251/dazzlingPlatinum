#!/usr/bin/env python3
"""Mega Lucario cry frame 2: "rear up and roar".

The upper body rises 2 px (front and back), the near arm
lifts frame 1's own clawed hand (flipped so the claws point up on the front)
beside the face on a new forearm, the mouth opens, and a tendril swings out
(the long one on the front; on the back the far tendril swings out and
the near one's red tip swings left and up).

Frame 2 is rebuilt from the real frame 1 (res/pokemon/lucario/forms/mega)
every run; the existing frame 2 is ignored.

usage: animate_lucario_cry.py [--install] [--previews]
  default     write tools/mega_sprites/previews/lucario_{front,back}.png
  --install   write res/pokemon/lucario/forms/mega/{front,back}.png instead
  --previews  also write the preview GIFs and lucario_frames.png
"""

import argparse
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEGA = os.path.join(ROOT, 'res/pokemon/lucario/forms/mega')
PREVIEWS = os.path.join(ROOT, 'tools/mega_sprites/previews')
F = 80
HEX = '0123456789ABCDEF'
BG = (200, 208, 216)
GIF_DURATIONS = [300, 430, 1000]

# ---------------------------------------------------------------- FRONT ----
# Pose: "rear up and roar".  The upper body rises 2 px (a per-column seam of
# repeated pixels runs through the hips, so diagonals keep clean 1-px steps
# and the feet stay planted), the lead arm (viewer's left) swings up so
# frame 1's own clawed hand is raised to mouth level with the claws pointing
# up on a visible forearm, and the jaw drops open in a wedge.
#
# Patches are row strings painted at (x0, y0): '.' leaves the pixel alone,
# '_' clears it to transparent, a hex digit sets that palette index.
# Coordinates in *_PATCHES are frame-2 (post-lift) coordinates.

# Lead arm = every pixel left of FRONT_TORSO_EDGE[y] in these rows (the kept
# column is the torso's own outline, so the body side stays closed).
FRONT_TORSO_EDGE = {38: 31, 39: 31, 40: 31, 41: 31, 42: 28, 43: 27, 44: 27,
                    45: 26, 46: 27, 47: 26, 48: 26, 49: 25, 50: 25}

# Seams: (x_first, x_last, row) runs; in each column that row is repeated and
# everything above it moves up 1 px.  Found by a min-cost DP (cost = pixels
# that differ from the one below, plus a shear penalty between columns) so
# the repeat lands on flat colour runs instead of across outlines.
FRONT_SEAMS = [
    [(0, 20, 48), (21, 21, 49), (22, 22, 50), (23, 27, 51), (28, 28, 50),
     (29, 29, 49), (30, 37, 48), (38, 38, 49), (39, 39, 50), (40, 48, 51),
     (49, 51, 52), (52, 59, 53), (60, 60, 52), (61, 61, 51), (62, 62, 50),
     (63, 63, 49), (64, 79, 48)],
    [(0, 20, 47), (21, 21, 48), (22, 22, 49), (23, 28, 50), (29, 29, 49),
     (30, 30, 48), (31, 37, 47), (38, 38, 48), (39, 39, 49), (40, 48, 50),
     (49, 51, 51), (52, 59, 52), (60, 60, 51), (61, 61, 50), (62, 62, 49),
     (63, 63, 48), (64, 79, 47)],
]
FRONT_LIFT = 2
# (The tall ear rises with the head but is swept back 1 px at the tip in
# FRONT_PATCHES, so its tip lands on row 3, not on the 2-px margin line.)
# Shoulder pixels of the cut arm (x >= 27, y <= 41) go back on the lifted
# body; the rest of the arm (y >= 39) is flipped: (x, y) -> (x - 3, 74 - y),
# so the hand (frame-1 rows 42-50) lands at rows 24-32, claws up.
FRONT_ARM_K = 74
FRONT_ARM_DX = -3

# Tendril flick: the long tendril behind the far shoulder (red tip) swings
# outward.  Each row of it from FRONT_TENDRIL[y] rightwards slides right by
# FRONT_TENDRIL_DX[y] px (below), so the tip moves 3 px while its outlines
# keep 1-px steps.  In FRONT_TENDRIL_SHARED rows the start
# column is an outline shared with the inner tendril: it stays put for the
# inner one and is copied along with the outer one.
FRONT_TENDRIL = {24: 50, 25: 50, 26: 51, 27: 51, 28: 51, 29: 51, 30: 50,
                 31: 50, 32: 50, 33: 51, 34: 51, 35: 54, 36: 55, 37: 55,
                 38: 55, 39: 55, 40: 55, 41: 55, 42: 55}
FRONT_TENDRIL_SHARED = {30, 31, 32, 33, 34}
# Per-row shift: the black band bends over rows 27-30 (1 px per row, on
# rows where frame 1's right edge has a zero step, so the edge stays a
# 1-px staircase) and everything from row 30 down, the red tip included,
# moves 3 px as one rigid block, so the tip keeps frame 1's rounded shape.
FRONT_TENDRIL_DX = {y: (0 if y <= 26 else 1 if y == 27 else 2 if y <= 29
                        else 3) for y in FRONT_TENDRIL}

FRONT_PATCHES = [
    # hand + forearm.  Relight the flipped back-of-hand spike so its
    # brightest pixel is on top, and run a grey forearm (outlined both sides,
    # lit along its upper edge, shaded 2 along its underside) down-right to
    # the shoulder.  The red glove ends in a short diagonal cuff at the
    # wrist (rows 32-34); frame 1's small wrist spike is left off, since
    # flipped it would point down and read as a loose fleck.
] + [(x, y, [row]) for x, y, row in (
    # hand + forearm, one row per entry: (first x, row, pixels).
    (18, 27, '8'),             # finger slit ends in a crease (8), not a
                               # second black pixel: knuckles, not a rake
    (15, 28, 'C.....6'),       # spike: brightest pixel on top; knuckle
    (21, 29, '6.1'),           # tops lit (6), dark 8 kept on the right
    (16, 30, 'D...6...1'),     # rim and moved to the underside
    (16, 31, '486668821__'),   # cuff: one clean diagonal (24,30)-(19,32),
    (16, 32, '1888844421_'),   # its rim a continuous 8 line; fist underside in shade
    (16, 33, '_1111B4421__'),  # wrist: 4 px of fill (rows 32-33)
    (16, 34, '____1B44421_'),  # B highlight: one 2-px segment (21,33-34)
    (16, 35, '_____1B44421'),  # forearm widens to 5 px toward the elbow;
    (20, 36, '_1B44221'),      # B highlight runs (21,33-34) (22,35-36); the
    (20, 37, '__1442221'),     # 2 shadow widens 1 -> 2 -> 3 px toward the
    (21, 38, '__1442221'),     # elbow, so the forearm is shaded round;
    (22, 39, '_1442221'),      # right outline x28 (37), x29 (38-39); 4 4 2 2
                               # (round 9): the lit side carries down
    (23, 40, '_11221'),        # round 9: rounded elbow; the bottom outline
    (24, 41, '__112'),         # is 2 px (26-27,41) and (28,41) is torso 2
    # fist top: close the left finger slit, so the top reads as knuckles,
    # and outline the spike's upper edge
    (16, 24, '1'),
    (15, 25, '16'),
    (13, 26, '11'),
    # round 9: the middle finger slit (18,26) is closed, so the top reads
    # as one knuckle row with a single crease (18,27)
    (18, 26, '6'),
    (29, 27, '2'),   # round 9: chest-fluff tip under the new jaw gets a dark edge
)] + [
    # the lift repeated the hip's left edge (x24) into a 6-row ruler line;
    # step it in by one at the top
    (24, 49, [
        '_24',  # 49
    ]),
    # the arm cut left a 1-px nub on the torso's left edge; run the edge
    # straight down x27 instead
    (26, 43, [
        '_1',   # 43
    ]),
    # open jaw (round 8): the lower jaw swings down about the cheek hinge
    # (32,23) as a tilted 2-row band, lip 4 over chin 5, so the mouth is a
    # wedge 3 rows deep at the tip (x26), 2 at x27-28 and 1 at x29-30.
    # Dark 8 under the upper jaw with the fang C hanging at (27,23), bright
    # 6 tongue along the lower lip.  The jaw has one continuous outline:
    # front (25,22-26), underside (26-28,27) (29-31,26) (32,25), which ends
    # in the cheek navy as frame 1's did at (32,24), and it sits on the
    # ruff with that outline between them.
    (24, 23, [
        # x 24 . 26 . 28 . 30 . 32
        '.18C88855',   # 23  interior under the upper jaw, fang C
        '._1864445',   # 24  front outline steps back (26,24); tongue 6
                       #     1 px behind the fang; lip 4
        '.__145551',   # 25  lip tip 4 (28,25), chin 5; outline (27,25)
        '.___1111',    # 26  underside outline (28-31,26)
        '..___',       # 27  (frame 1 is empty here)
    ]),
    # hips: the lift stacked four identical fur rows (x47-56, rows 51-54);
    # step their right edge out at row 53, and end the left hip outline's
    # x24 run at row 51 (4 rows, as in frame 1)
    (24, 50, ['_2']),
    # the raised arm no longer covers the left hip: its navy edge pixels
    # (A) become the silhouette outline
    (25, 44, ['..1',
              '.1',
              '.1',
              '1',
              '1']),
    # round 9: the exposed left hip edge is jagged like frame 1's fur, not a
    # straight ruler: edge x 26,25,24,24,25,25,25,24,24,24 down rows 45-54
    # (a small tuft at rows 47-48), and the grey 4 rim is broken with 2.
    (24, 46, ['.17',       # 46
              '17',        # 47
              '14',        # 48
              '.1',        # 49
              '.12',       # 50
              '_14',       # 51
              ]),
    (56, 53, ['31',
              '31']),
    # ear (round 8): the tall ear's 1-px tip is folded down a row, so the
    # tip is at (37,3) over the A7A shaft, leaving a 3-px top margin
    (36, 2, ['._.',
             '_A_']),
]

# ----------------------------------------------------------------- BACK ----
# Pose: the same "rear up" lift (2 px: the seams run through the tail root
# and the near shin, so the feet stay planted), with the near hand (viewer's right) raised
# beside the muzzle.  The hand is frame 1's own hand moved without flipping
# (so its lighting stays right); a new forearm runs from the wrist down
# behind the tendril, and the jaw opens.
BACK_HIP_SEAM = [(46, 46, 58), (47, 47, 56), (48, 48, 54), (49, 50, 52),
                 (51, 79, 52)]
BACK_SEAMS = [
    # 1 px at the hip line: the seam runs through the tail's flat yellow
    # just inside its lower outline (so the tail root grows 1 row, and no
    # fur stripe is cut), then (BACK_HIP_SEAM, round 9) down the tan just
    # above the near thigh's outline and across the empty gap above the
    # thigh, so the whole near leg, thigh included, keeps frame 1's
    # pixels and proportions.  Left of x31 it runs in the empty space under
    # the tail tips, so they rise rigidly.
    [(0, 30, 64), (31, 32, 62), (33, 37, 63), (38, 39, 62), (40, 41, 61),
     (42, 43, 60), (44, 45, 59)] + BACK_HIP_SEAM,
]
# Round 8: a second 1-px lift of the upper body (2 px total), applied at the
# very end of back_frame2 so every coordinate above stays in 1-px-lift
# space.  In the tail it repeats the next row of flat yellow above the first
# seam; in the near leg (x46+) the two seams repeat two different shin
# rows (frame 1 rows 69 and 64) instead of the thigh's already doubled
# stripe row, so no row appears 3+ times and the whole thigh rises rigidly.
BACK_SEAM2 = [(0, 30, 63), (31, 32, 61), (33, 37, 62), (38, 39, 61),
              (40, 41, 60), (42, 43, 59), (44, 45, 58)] + BACK_HIP_SEAM
# Final-coordinate touch-ups after the second lift.
BACK_FINAL_PATCHES = [
    # tail root, left edge: the tail rises rigidly at x30- but grows at
    # x31+, so the lower-left outline is continued down x31 to meet the
    # 2-px step at (32,63)
    (31, 62, ['1', '_']),
    # crotch: where the tail's under-edge meets the (rigidly lifted) thigh
    # the outline is closed across (46-47,59)
    (46, 59, ['11']),
] + [(x, y, [row]) for x, y, row in (
    # ---- round 9 near arm, final coordinates, one row per entry ----
    # fist: outline its left rim (frame 1 hid it behind the tendril)
    (64, 27, '1'),
    (63, 28, '1'),
    (62, 29, '1'),
    # forearm: a short, thick limb (5-7 px of fill) from the fist's
    # lower-left down to an elbow that tucks behind the near tendril;
    # dark 2 on the left, 4 on the lit right, a short B edge highlight
    (61, 30, '124'),
    (60, 31, '1244'),
    (59, 32, '12244'),
    (58, 33, '122444'),
    (57, 34, '122444B'),
    (56, 35, '122244B1'),
    (55, 36, '1222444B1'),
    (54, 37, '1222244B1'),   # (54,37) meets the tendril outline (53,37)
    (54, 38, '222224441'),   # fill runs against the tendril outline
    (55, 39, '2222441'),
    (55, 40, '112221'),      # rounded elbow: the bottom rises into the
    (57, 41, '111'),         # tendril outline on the left
    # wrist spike under the fist: a clean 1-px point, outlined
    (66, 34, '41'),
    (66, 35, '1'),
    # open mouth: the lower jaw hinges at (50,31); the fang hangs 1 px
    # behind the front, whose outline steps back on a diagonal
    # (55,32) (55,33) (54,34) (53,35)
    (51, 32, 'EECE1'),
    (51, 33, '2E671'),
    (51, 34, '1751'),
    (52, 35, '11'),
)]
# Secondary motion: the far tendril's free end swings out and up as the
# head snaps back.  Below the point where it parts from the grey lobe beside
# it (row 36) it shifts 1 px left, and its red tip 2 px left; the tip also
# rises 1 px along the swing arc by dropping one of frame 1's two identical
# neck rows (post-lift rows 39 and 40), so the tip clears the tail with a 1-px
# gap.  Both edges still step by at most 1 px per row.
# {frame-2 row: (source row, first x, last x, dx)}; source rows are
# post-lift frame-2 coordinates, and every source span is cleared first.
BACK_TENDRIL = {
    36: (36, 26, 31, -1), 37: (37, 25, 31, -1), 38: (38, 25, 30, -1),
    39: (40, 24, 29, -1), 40: (41, 24, 29, -2), 41: (42, 24, 28, -2),
    42: (43, 25, 28, -2), 43: (44, 26, 27, -2),
}
BACK_TENDRIL_CLEAR = {36: (26, 31), 37: (25, 31), 38: (25, 30), 39: (25, 30),
                      40: (24, 29), 41: (24, 29), 42: (24, 28), 43: (25, 28),
                      44: (26, 27)}
# Secondary motion on the near tendril (round 8): with the fist raised, its
# red tip no longer sits beside the hand, so it swings 2 px left (toward
# the tail) and 1 px up as one rigid block (one of its two identical grey
# rows, post-lift rows 43 and 44, is dropped).  Its thin partner strand on
# the left moves with it, and the tip now overlaps the tail's right edge,
# which closes the old channel between them without leaving holes.
# {frame-2 row: (source row, first x, last x, dx)}, same scheme as above.
BACK_NEAR_TIP = {
    42: (42, 46, 55, -1), 43: (43, 46, 55, -2),
    44: (45, 47, 56, -3), 45: (46, 48, 56, -3), 46: (47, 50, 56, -3),
    47: (48, 51, 56, -3), 48: (49, 51, 55, -3), 49: (50, 52, 54, -3),
}
BACK_NEAR_TIP_CLEAR = {42: (46, 55), 43: (46, 55), 44: (47, 56),
                       45: (47, 56), 46: (48, 56), 47: (50, 56),
                       48: (51, 56), 49: (51, 55), 50: (52, 54)}
# hand = x >= 56 in rows 39-44 and x >= 57 in rows 45-50 (frame 1)
BACK_HAND = [(range(39, 45), 56), (range(45, 51), 57)]
BACK_HAND_MOVE = (7, -14)

BACK_PATCHES = [
    # tail root: the seam grew the tail 1 row at x31+, but lifted it
    # rigidly at x30-; one outline pixel joins the two edges on a diagonal
    (31, 61, ['1']),
]
# Pixels painted only where frame 2 is still transparent.  Round 4 draws
# the whole back forearm as a normal patch, so nothing is needed here.
BACK_BEHIND = []


def load(name):
    im = Image.open(os.path.join(MEGA, name))
    ix = Image.frombytes('L', im.size, im.tobytes())
    f1 = [[ix.getpixel((x, y)) for x in range(F)] for y in range(F)]
    return im, f1


def copy(g):
    return [row[:] for row in g]


def paint(g, patches):
    for x0, y0, rows in patches:
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch in '. ':
                    continue
                g[y0 + j][x0 + i] = 0 if ch == '_' else HEX.index(ch)


def paint_behind(g, patches):
    """Like paint(), but only fills pixels that are still transparent."""
    for x0, y0, rows in patches:
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch not in '. _' and g[y0 + j][x0 + i] == 0:
                    g[y0 + j][x0 + i] = HEX.index(ch)


def seam_lift(g, runs):
    """Repeat one row per column (given as runs) so everything above it
    moves up 1 px; columns keep their feet."""
    src = copy(g)
    for x0, x1, s in runs:
        for x in range(x0, x1 + 1):
            assert src[0][x] == 0, 'lift would push art off the top'
            for r in range(s):
                g[r][x] = src[r + 1][x]
    return g


def seam_drop(g, runs):
    """Remove one pixel per column (given as runs); pixels above it move
    down 1 px."""
    src = copy(g)
    for x0, x1, s in runs:
        for x in range(x0, x1 + 1):
            for r in range(s, 0, -1):
                g[r][x] = src[r - 1][x]
            g[0][x] = 0
    return g


def front_frame2(f1):
    g = copy(f1)
    arm = {}
    for y, edge in FRONT_TORSO_EDGE.items():
        for x in range(edge):
            if f1[y][x]:
                arm[(x, y)] = f1[y][x]
            g[y][x] = 0
    for runs in FRONT_SEAMS:
        seam_lift(g, runs)
    for (x, y), v in arm.items():
        if x >= 27 and y <= 41:
            g[y - FRONT_LIFT][x] = v
    for (x, y), v in arm.items():
        if y >= 39:
            g[FRONT_ARM_K - y][x + FRONT_ARM_DX] = v
    src = copy(g)
    for y, x0 in FRONT_TENDRIL.items():
        dx = FRONT_TENDRIL_DX[y]
        if dx <= 0:
            continue
        for x in range(x0 + (y in FRONT_TENDRIL_SHARED), F):
            g[y][x] = 0
        for x in range(x0, F - dx):
            if src[y][x]:
                g[y][x + dx] = src[y][x]
    paint(g, FRONT_PATCHES)
    return g


def back_frame2(f1):
    g = copy(f1)
    hand = {}
    for rows, x0 in BACK_HAND:
        for y in rows:
            for x in range(x0, F):
                if f1[y][x]:
                    hand[(x, y)] = f1[y][x]
                g[y][x] = 0
    for runs in BACK_SEAMS:
        seam_lift(g, runs)
    dx, dy = BACK_HAND_MOVE
    for (x, y), v in hand.items():
        g[y + dy][x + dx] = v
    src = copy(g)
    for y, (xa, xb) in BACK_TENDRIL_CLEAR.items():
        for x in range(xa, xb + 1):
            g[y][x] = 0
    for moves, clears in ((BACK_TENDRIL, None),
                          (BACK_NEAR_TIP, BACK_NEAR_TIP_CLEAR)):
        for y, (xa, xb) in (clears or {}).items():
            for x in range(xa, xb + 1):
                g[y][x] = 0
        for y, (sy, xa, xb, dx) in moves.items():
            for x in range(xa, xb + 1):
                if src[sy][x]:
                    g[y][x + dx] = src[sy][x]
    paint(g, BACK_PATCHES)
    paint_behind(g, BACK_BEHIND)
    seam_lift(g, BACK_SEAM2)
    paint(g, BACK_FINAL_PATCHES)
    return g


def save_sheet(im, f1, f2, path):
    ix = Image.new('L', im.size)
    for fi, g in enumerate((f1, f2)):
        for y in range(F):
            for x in range(F):
                ix.putpixel((fi * F + x, y), g[y][x])
    out = Image.frombytes('P', im.size, ix.tobytes())
    out.putpalette(im.getpalette())
    out.save(path, bits=4, transparency=0)


def read_pal(name):
    with open(os.path.join(MEGA, name)) as fh:
        lines = fh.read().split()
    vals = [int(v) for v in lines[3:3 + 3 * 16]]
    return [tuple(vals[k:k + 3]) for k in range(0, 48, 3)]


def check(im, f1, f2):
    real = Image.frombytes('L', im.size, im.tobytes())
    for y in range(F):
        for x in range(F):
            assert f1[y][x] == real.getpixel((x, y)), 'frame 1 changed'
    used = {v for row in f1 for v in row}
    extra = {v for row in f2 for v in row} - used
    assert not extra, 'frame 2 uses new indices %s' % extra
    for k in range(F):
        for x, y in ((k, 0), (k, F - 1), (0, k), (F - 1, k)):
            assert f2[y][x] == 0, 'frame 2 touches the border at %d,%d' % (x, y)


def render(g, pal, scale, bg):
    out = Image.new('RGB', (F, F), bg)
    for y in range(F):
        for x in range(F):
            if g[y][x]:
                out.putpixel((x, y), pal[g[y][x]])
    return out.resize((F * scale, F * scale), Image.NEAREST)


def write_gif(f1, f2, pal, scale, path):
    frames = [render(g, pal, scale, BG) for g in (f1, f2, f1)]
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=GIF_DURATIONS, loop=0, disposal=1, optimize=False)
    with Image.open(path) as chk:
        assert chk.n_frames == 3, path
        assert chk.info.get('loop') == 0, path
        for n, ms in enumerate(GIF_DURATIONS):
            chk.seek(n)
            assert chk.info['duration'] == ms, path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--install', action='store_true',
                    help='write res/.../mega/{front,back}.png instead of previews/')
    ap.add_argument('--previews', action='store_true', help='also write the GIFs')
    args = ap.parse_args()
    os.makedirs(PREVIEWS, exist_ok=True)
    pals = {'normal': read_pal('normal.pal'), 'shiny': read_pal('shiny.pal')}
    frames = {}
    for side, build in (('front', front_frame2), ('back', back_frame2)):
        im, f1 = load(side + '.png')
        f2 = build(f1)
        check(im, f1, f2)
        frames[side] = (f1, f2)
        dest = (os.path.join(MEGA, side + '.png') if args.install
                else os.path.join(PREVIEWS, 'lucario_%s.png' % side))
        save_sheet(im, f1, f2, dest)
        print('wrote', os.path.relpath(dest, ROOT))
    if not args.previews:
        return
    for side, (f1, f2) in frames.items():
        base = os.path.join(PREVIEWS, 'lucario_' + side)
        write_gif(f1, f2, pals['normal'], 4, base + '.gif')
        write_gif(f1, f2, pals['shiny'], 4, base + '_shiny.gif')
        write_gif(f1, f2, pals['normal'], 1, base + '_1x.gif')
    sheet = Image.new('RGB', (2 * F * 5, 4 * F * 5), BG)
    for r, (side, pal) in enumerate((('front', 'normal'), ('front', 'shiny'),
                                     ('back', 'normal'), ('back', 'shiny'))):
        for c, g in enumerate(frames[side]):
            sheet.paste(render(g, pals[pal], 5, BG), (c * F * 5, r * F * 5))
    sheet.save(os.path.join(PREVIEWS, 'lucario_frames.png'))
    print('wrote GIFs and lucario_frames.png')


if __name__ == '__main__':
    main()
