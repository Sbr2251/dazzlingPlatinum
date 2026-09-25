#!/usr/bin/env python3
"""One-shot cry frame (frame 2) for Mega Staraptor, front and back.

Frame 2 is built only from frame 1 of the real sprites; frame 1 is copied
unchanged. Moved parts are cut out of frame 1 and pasted back translated by
whole pixels or shifted as whole rows (no resampling, so every wing keeps
its length, width, outline, veins and feather marks). Joint seams and the
open beaks are then cleaned or drawn with explicit pixel tables using only
frame 1's palette indices.

FRONT (round 9), "rears up, wing leans, beak open": the head, crest and far
wing lift 4 px, and the head tips back: frame-1 rows <= 32 move 2 px back
(right) and rows 33-37 1 px, as whole rows, while the beak rows stay.  The
chest below is stretched by 4 rows with one row map for every column
(chest_rows): frame-1 rows 40/42/44/47 appear twice, and dup_pixel keeps a
short mark in only one copy, so strokes stay joined and do not lengthen;
rows 49-56 (the chest's lower-right outline) are frame 1's exactly.  The
near wing leans in: its frame-1 rows shift left 3/2/1 px (tip to
shoulder) as whole rows, the tip stays on frame 1's y=4.  The beak is open:
frame 1's own upper beak (hook included) rides up with the head; a new lower
jaw hinges at the gape and angles down-left to a B tip at (18,44), a 2-px
C/B band with a 1-px dark outline, over a dark index-2 mouth wedge.

BACK (round 9), "wings flap up and in, head up, beak open": the upper wings
(y <= 25) are row-sheared toward the body, 5 px at the tips down to 0 at
the roots (y >= 26 is frame 1's own, fringe included); the tips move from
x=4/75 to x=9/70 on y=4.  The head and the whole white bib lift 2 px
rigidly; the 2 extra neck rows go into the plain grey under the bib.  Every
head pixel is kept (crest tip included) and a hooked beak juts right from
under the crest tip, overlapping the right wing's inner edge with its own
dark outline: D top, C underside, hook tip at (51-52,35), a 2-px mouth and
a thin C/B lower-jaw wedge.

Usage: animate_staraptor_cry.py [--install] [--previews]
  default    writes tools/mega_sprites/previews/staraptor_{front,back}.png
  --install  writes res/pokemon/staraptor/forms/mega/{front,back}.png instead
  --previews also writes the preview GIFs and staraptor_frames.png
"""

import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEGA = os.path.join(ROOT, 'res/pokemon/staraptor/forms/mega')
PREVIEWS = os.path.join(ROOT, 'tools/mega_sprites/previews')
FRAME = 80
MARKS = (1, 2, 3, 4)
OUTLINE = (1, 2)          # outline / texture-mark indices


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def load_sheet(path):
    im = Image.open(path)
    ix = Image.frombytes('L', im.size, im.tobytes())
    px = ix.load()
    f1 = [[px[x, y] for x in range(FRAME)] for y in range(FRAME)]
    return im, f1


def copy(f):
    return [row[:] for row in f]


def cut(f, pred):
    """Remove the pixels matching pred(x, y, v) from f and return them as a layer."""
    layer = {}
    for y in range(FRAME):
        for x in range(FRAME):
            v = f[y][x]
            if v and pred(x, y, v):
                layer[(x, y)] = v
                f[y][x] = 0
    return layer


def shift(layer, dx, dy):
    return {(x + dx, y + dy): v for (x, y), v in layer.items()}


def paste(f, layer):
    for (x, y), v in layer.items():
        if 0 <= x < FRAME and 0 <= y < FRAME:
            f[y][x] = v


def apply(f, pixels):
    for x, y, v in pixels:
        f[y][x] = v


def rows(f, x0, y0, strings):
    """Hand pixelling as row strings: '.' keeps the pixel, '_' clears it,
    hex digits set the index."""
    for j, s in enumerate(strings):
        for i, c in enumerate(s):
            if c == '.':
                continue
            f[y0 + j][x0 + i] = 0 if c == '_' else int(c, 16)


# ---------------------------------------------------------------------------
# FRONT
# ---------------------------------------------------------------------------
# The near wing is not rotated: every frame-1 row of it is moved sideways
# as a whole row, leaning the upper wing in by near_dx(y) px: 3 px at the
# tip, stepping down to 0 at the shoulder.  (Round 8) the shear is 3 px, not
# 4, and each band ends on a row where frame 1's trailing edge steps left
# anyway, so the gold streak keeps frame 1's bow instead of standing up
# with jogs, and the wing keeps its width.  The tip stays on frame 1's y=4.
FRONT_NEAR_STEPS = ((11, -3), (19, -2), (24, -1))


def near_dx(y):
    for y_max, dx in FRONT_NEAR_STEPS:
        if y <= y_max:
            return dx
    return 0


# Optional column rise after the row shift ((x_min, dy), ...).  Round 7 used
# it to lift the tip to y=2; (round 8) disabled, the top row must be y>=3.
FRONT_NEAR_RISE = ()


def near_dy(x):
    for x_min, dy in FRONT_NEAR_RISE:
        if x >= x_min:
            return dy
    return 0
# The far wing is not rotated any more (round 4): the rotation stair-stepped
# its gold streaks.  It lifts rigidly with the head, so every streak and
# feather tick is frame 1's own.
FRONT_HEAD_ROWS = {26: (17, 27)}
FRONT_HEAD_ROWS.update({y: (8, 30) for y in range(27, 32)})
FRONT_HEAD_ROWS.update({y: (8, 29) for y in range(32, 37)})
FRONT_HEAD_ROWS.update({37: (8, 30), 38: (8, 31)})
FRONT_HEAD_ROWS.update({y: (8, 21) for y in range(39, 44)})
FRONT_HEAD_ROWS.update({y: (8, 16) for y in range(44, 50)})
FRONT_HEAD_LIFT = 4
FRONT_TILT = ((32, 2), (37, 1))   # frame-1 rows <= y lean back (right) dx


def head_dx(y):
    for y_max, dx in FRONT_TILT:
        if y <= y_max:
            return dx
    return 0
FRONT_CHEST_BOTTOM = 56
FRONT_CHEST_DUPS = (40, 42, 44, 47)   # flattest chest rows take the 4 extra
FRONT_CHEST_MAX_X = 36
FRONT_UPPER_Y = 38
FRONT_FAR_Y = 26
FRONT_EDITS = [
    # neck back edge where the tilt steps from 2 to 1 px (frame-1 rows
    # 31-32, lifted 4 to 27-28): no 1-px bump, the outline stays on x35
    (36, 27, 0), (36, 28, 0), (35, 28, 1),
    # the pocket between the neck and the near wing's leading edge is taller
    # than frame 1's (the neck rose 4, the near wing did not); its left and
    # bottom sides get a dark 3 edge so no light grey sits on transparency
    (35, 31, 3), (35, 32, 3), (36, 35, 3), (36, 36, 3), (37, 37, 3), (38, 37, 3),
    # chest / near-wing seam: frame 1's own 555EE / 553EE / 6633E runs
    (35, 41, 5), (36, 41, 5), (35, 42, 5), (36, 42, 5), (35, 46, 6), (36, 46, 6),
    # near-wing trailing edge: the lean merges frame 1's 66x6 and 65x2 runs
    # into one 8-row column at x63; row 13 steps in so the tip edge runs
    # 64x2, 63x7, 62x7 (frame 1: 67x2, 66x6, 65x2, 64x6)
    (63, 13, 0), (62, 13, 1),
]
FRONT_ROWS = [
    # open beak (head lifted 4).  The upper mandible is frame 1's own, hook
    # included (grey 4 tip at x16, rows 38-39); only its closed mouth line
    # (18,38) becomes C.  The lower jaw hinges at the gape (21-22,40) and
    # angles down-left to a B tip at (18,44): a 2-px C/B band with a 1-px
    # dark outline on both sides.  Between the jaws a dark index-2 mouth
    # wedge (4 px deep at the gape row, 1 px at the front); in front of it,
    # under the hook, x16 stays open so background shows between the tips.
    (15, 38, ['...C....',
              '..22221.',
              '.12221C1',
              '._221CB1',
              '._21CB1.',
              '._1CB1..',
              '..1B1...',
              '..11....']),
]


# left edge of the near wing, per row, below y=40 (the purple leading edge
# and then the lower feathers that overlap the hip)
FRONT_NEAR_LEFT = {40: 39, 41: 38, 42: 37, 43: 36, 44: 36, 45: 37, 46: 37,
                   47: 36, 48: 46, 49: 45, 50: 46, 51: 46, 52: 44}


def front_is_near(x, y, v=None):
    if y < 40:
        return x >= 37
    return y in FRONT_NEAR_LEFT and x >= FRONT_NEAR_LEFT[y]


def front_is_head(x, y):
    r = FRONT_HEAD_ROWS.get(y)
    return r is not None and r[0] <= x <= r[1]


def stretch_plan(f, x, top, n_old, n_new, avoid=(), want=None):
    """Source index for each of n_new output rows of a column segment.

    Plain nearest-row stretching doubles whole rows at the same place in
    every column, which turns feather ticks into vertical streaks.  Each
    extra row is instead spent inside a plain run of the same colour
    (within 2 rows of where uniform stretching would put it), so the
    ticks keep their frame-1 length.
    """
    ideal = sorted({(j * n_old) // n_new for j in range(n_new)
                    if j and (j * n_old) // n_new == ((j - 1) * n_old) // n_new})
    extra = n_new - n_old
    if want is not None:                 # preferred source rows (absolute y)
        ideal = [y - top for y in want if 0 <= y - top < n_old]

    def run_len(i):
        v = f[top + i][x]
        a = i
        while a > 0 and f[top + a - 1][x] == v:
            a -= 1
        b = i
        while b + 1 < n_old and f[top + b + 1][x] == v:
            b += 1
        return b - a + 1

    def cost(i):
        y = top + i
        v = f[y][x]
        c = 0
        if v in MARKS or run_len(i) < 3:
            c += 4                       # would lengthen a mark or short run
        if v in avoid:
            c += 3                       # keep this colour area its size
        if not (0 < x < FRAME - 1 and f[y][x - 1] == v == f[y][x + 1]):
            c += 2                       # not a plain area
        return c

    dups = []
    for p in ideal[:extra]:
        cands = [i for i in range(max(0, p - 3), min(n_old, p + 4))
                 if i not in dups]
        dups.append(min(cands, key=lambda i: (cost(i), abs(i - p))))
    while len(dups) < extra:
        dups.append(n_old - 1)
    plan = []
    for i in range(n_old):
        plan.append(i)
        plan.extend([i] * dups.count(i))
    return plan[:n_new]


def chest_rows(n_src_top, bottom, lift, dups):
    """Global row map for the chest band: frame-2 rows bottom-(n)-lift..bottom
    take frame-1 rows n_src_top..bottom, each row in `dups` appearing twice.
    Returns [(frame2_y, frame1_y, is_second_copy)]."""
    src = []
    for r in range(n_src_top, bottom + 1):
        src.append((r, False))
        if r in dups:
            src.append((r, True))
    assert len(src) == bottom - n_src_top + 1 + lift
    y0 = n_src_top - lift
    return [(y0 + j, r, second) for j, (r, second) in enumerate(src)]


# in the white chest the grey 5/6 feather ticks are marks too (only where
# they sit on white; grey areas are left alone)
DUP_MARKS = (1, 2, 3, 4, 5, 6)


def dup_pixel(f, x, r, second):
    """Pixel of copy 1 or 2 of a duplicated row r.  A short interior mark
    must not grow: it stays in the copy next to the row it continues into
    and the other copy gets the surrounding fill.  Silhouette pixels (next
    to transparency) and marks that continue both up and down stay in both
    copies, so outlines never break."""
    v = f[r][x]
    if v not in DUP_MARKS:
        return v
    nb = [f[r][x - 1], f[r][x + 1], f[r - 1][x], f[r + 1][x]]
    if 0 in nb:
        return v
    if v not in MARKS and nb.count(7) < 2:
        return v                      # grey area, not a tick on white
    up = any(f[r - 1][x + d] == v for d in (-1, 0, 1))
    down = any(f[r + 1][x + d] == v for d in (-1, 0, 1))
    if up and down:
        return v
    keep_second = down and not up
    if second == keep_second:
        return v
    marks = MARKS if v in MARKS else DUP_MARKS
    fills = [c for c in nb if c not in marks]
    return max(set(fills), key=fills.count) if fills else v


def front_frame2(f1):
    base = copy(f1)
    near = cut(base, front_is_near)
    upper = cut(base, lambda x, y, v: x <= FRONT_CHEST_MAX_X and
                (y < FRONT_UPPER_Y or front_is_head(x, y)))
    # head tips back: frame-1 rows <= 32 (far wing, crest top, crown) move
    # 2 px back (right) and rows 33-37 (eye, crest middle) 1 px, as whole
    # rows; the beak and throat rows stay, so the face turns up without any
    # resampling
    upper = {(x + head_dx(y), y): v for (x, y), v in upper.items()}
    lift = FRONT_HEAD_LIFT
    out = copy(base)
    # the chest band (columns x <= FRONT_CHEST_MAX_X, frame-1 rows
    # FRONT_UPPER_Y..FRONT_CHEST_BOTTOM) is stretched by `lift` rows with ONE
    # row map for every column, so the feather strokes stay joined across
    # columns.  The extra rows are the chest's flattest rows
    # (FRONT_CHEST_DUPS); a short interior mark of a duplicated row is kept
    # only in the copy next to the row it continues into (see dup_pixel),
    # the other copy gets the surrounding fill, so no stroke is lengthened.
    band = chest_rows(FRONT_UPPER_Y, FRONT_CHEST_BOTTOM, lift, FRONT_CHEST_DUPS)
    for x in range(FRONT_CHEST_MAX_X + 1):
        for y in range(FRONT_UPPER_Y - lift, FRONT_CHEST_BOTTOM + 1):
            out[y][x] = 0
    for y2, r, second in band:
        for x in range(FRONT_CHEST_MAX_X + 1):
            out[y2][x] = dup_pixel(base, x, r, second) if r in FRONT_CHEST_DUPS \
                else base[r][x]
    paste(out, shift(upper, 0, -lift))
    # near wing: every frame-1 row is moved as a whole row (see near_dx)
    for (x, y), v in near.items():
        nx = x + near_dx(y)
        out[y + near_dy(nx)][nx] = v
    apply(out, FRONT_EDITS)
    for x0, y0, strs in FRONT_ROWS:
        rows(out, x0, y0, strs)
    return out


# ---------------------------------------------------------------------------
# BACK
# ---------------------------------------------------------------------------
# (Round 9) both wings flap up and in by a sheared lift from the root: each
# frame-1 row of the upper wing (y <= 25) moves sideways, toward the body,
# as a whole row: 5 px at the tip (y 4-5), 4 / 3 / 2 / 1 px lower down (band
# edges on rows where frame 1's edges and gold streak already step), 0
# from y=26 (the roots, the purple fringe and everything below are frame 1's
# own, untouched).  Frame 1's outer edge is already near-vertical, so the
# shear stands the wings up without narrowing them; every pixel, streak and
# serration is frame 1's.  The tips move from x=4/75 to x=9/70.
BACK_WING_SHEAR = ((5, 5), (7, 4), (13, 3), (17, 2), (25, 1))
BACK_HEAD_LIFT = 2
BACK_NECK_BOTTOM = 46
BACK_NECK_MID = (36, 43)          # columns with plain grey under the bib
BACK_NECK_BOTTOM_MID = 51
BACK_NECK_DUPS = (44, 46)          # their extra rows (plain grey)
BACK_EDITS = [
    # plain neck grey under the lifted bib: frame 1's single 4 feather specks
    (38, 43, 4), (41, 45, 4),
    # row 26 is the first unsheared row: close the 1-px notch it leaves on
    # each wing's inner edge (edge colour continues from the row above)
    (26, 26, 5), (27, 26, 4), (51, 26, 5), (50, 26, 3),
]
BACK_ROWS = [
    # (round 9) open hooked beak jutting right from under the crest tip (the
    # head is turned right, as in frame 1).  Every head pixel is kept,
    # crest tip included; the beak starts right of it at x48 and overlaps
    # the right wing's inner edge with its own dark outline, so there is no
    # transparent channel between beak and wing.  Upper beak: culmen outline
    # (49-51,31) sloping down to (53,33); yellow D top, C underside, the
    # front curling down into a C/B hook whose tip hangs at (51-52,35).
    # Mouth: two index-2 pixels behind it, over a thin C/B lower-jaw wedge
    # (49-50,36) closed underneath at (49-50,37).
    (47, 31, ['..111',
              '..DDD1',
              '.DDDDD1',
              '1CCCCD1',
              '.122CB1',
              '.1CB11',
              '..11']),
]


def wing_dx(y):
    for y_max, dx in BACK_WING_SHEAR:
        if y <= y_max:
            return dx
    return 0


def back_is_head(x, y):
    if 17 <= y <= 37:
        return 29 <= x <= 48 and (x, y) not in ((48, 36), (48, 37), (47, 37))
    if 38 <= y <= 42:                     # the bib and its zigzag lower edge
        return 33 <= x <= 45
    return y == 43 and 36 <= x <= 43


def back_is_lwing(x, y):
    return y <= 51 and x <= (28 if y <= 38 else 26)


def back_is_rwing(x, y):
    return y <= 51 and x >= (50 if y <= 31 else 49 if y <= 38 else 53)


def back_frame2(f1):
    base = copy(f1)
    head = cut(base, lambda x, y, v: back_is_head(x, y))
    lw = cut(base, lambda x, y, v: back_is_lwing(x, y) and wing_dx(y))
    rw = cut(base, lambda x, y, v: back_is_rwing(x, y) and wing_dx(y))
    lift = BACK_HEAD_LIFT
    out = copy(base)
    # the neck under the lifted head is stretched by `lift` rows.  In the
    # middle columns (the white bib over the plain grey neck) the extra rows
    # go into the plain grey below the bib, so the bib keeps frame 1's
    # height; the textured shoulder columns spread them as usual.
    for x in range(29, 49):
        ys = [y for (hx, y) in head if hx == x]
        top = max(ys) + 1
        mid = BACK_NECK_MID[0] <= x <= BACK_NECK_MID[1]
        bot = BACK_NECK_BOTTOM_MID if mid else BACK_NECK_BOTTOM
        n_old = bot - top + 1
        n_new = n_old + lift
        col = [base[y][x] for y in range(top, bot + 1)]
        plan = stretch_plan(base, x, top, n_old, n_new,
                            want=BACK_NECK_DUPS if mid else None)
        for j, i in enumerate(plan):
            out[top - lift + j][x] = col[i]
    paste(out, {(x + wing_dx(y), y): v for (x, y), v in lw.items()})
    paste(out, {(x - wing_dx(y), y): v for (x, y), v in rw.items()})
    paste(out, shift(head, 0, -lift))
    apply(out, BACK_EDITS)
    for x0, y0, strs in BACK_ROWS:
        rows(out, x0, y0, strs)
    return out


def check(f1, f2, side):
    used = {v for row in f1 for v in row}
    bad = {v for row in f2 for v in row} - used
    assert not bad, '%s: frame 2 uses indices not in frame 1: %s' % (side, bad)
    for y in range(FRAME):
        for x in range(FRAME):
            if f2[y][x] and (x < 2 or y < 2 or x > FRAME - 3 or y > FRAME - 3):
                raise AssertionError('%s: frame 2 art at (%d, %d) within 2 px of the edge' % (side, x, y))


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------
def read_pal(path):
    rows = open(path).read().split('\n')[3:]
    return [tuple(int(c) for c in r.split()) for r in rows if r.strip()]


def save_sheet(im, f1, f2, path):
    data = bytes(v for frame_rows in zip(f1, f2) for row in frame_rows for v in row)
    # zip(f1, f2) yields (row1, row2) per y: row1 then row2 gives a 160-wide row.
    out = Image.frombytes('P', (2 * FRAME, FRAME), data)
    out.putpalette(im.getpalette())
    out.info['transparency'] = 0
    out.save(path, bits=4, transparency=0)


def rgb_frame(f, pal, scale, bg):
    img = Image.new('RGB', (FRAME, FRAME), bg)
    px = img.load()
    for y in range(FRAME):
        for x in range(FRAME):
            if f[y][x]:
                px[x, y] = pal[f[y][x]]
    return img.resize((FRAME * scale, FRAME * scale), Image.NEAREST)


def write_gif(f1, f2, pal, scale, path, bg=(200, 208, 216)):
    frames = [rgb_frame(f, pal, scale, bg) for f in (f1, f2, f1)]
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=[300, 430, 1000], loop=0, disposal=1, optimize=False)


def main(argv):
    install = '--install' in argv
    previews = '--previews' in argv
    os.makedirs(PREVIEWS, exist_ok=True)
    sheets = {}
    for side, make in (('front', front_frame2), ('back', back_frame2)):
        im, f1 = load_sheet(os.path.join(MEGA, side + '.png'))
        f2 = make(copy(f1))
        check(f1, f2, side)
        sheets[side] = (f1, f2)
        dest = (os.path.join(MEGA, side + '.png') if install
                else os.path.join(PREVIEWS, 'staraptor_%s.png' % side))
        save_sheet(im, f1, f2, dest)
        _, g1 = load_sheet(dest)
        assert g1 == f1, side + ': frame 1 changed'
        print('wrote', os.path.relpath(dest, ROOT))
    if previews:
        normal = read_pal(os.path.join(MEGA, 'normal.pal'))
        shiny = read_pal(os.path.join(MEGA, 'shiny.pal'))
        for side, (f1, f2) in sheets.items():
            base = os.path.join(PREVIEWS, 'staraptor_' + side)
            write_gif(f1, f2, normal, 4, base + '.gif')
            write_gif(f1, f2, shiny, 4, base + '_shiny.gif')
            write_gif(f1, f2, normal, 1, base + '_1x.gif')
        s = 5
        grid = Image.new('RGB', (2 * FRAME * s, 4 * FRAME * s), (200, 208, 216))
        row = 0
        for side in ('front', 'back'):
            for pal in (normal, shiny):
                for col, f in enumerate(sheets[side]):
                    grid.paste(rgb_frame(f, pal, s, (200, 208, 216)),
                               (col * FRAME * s, row * FRAME * s))
                row += 1
        grid.save(os.path.join(PREVIEWS, 'staraptor_frames.png'))
        print('wrote previews')


if __name__ == '__main__':
    main(sys.argv[1:])
