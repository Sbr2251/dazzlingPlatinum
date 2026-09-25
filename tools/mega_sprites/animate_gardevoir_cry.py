#!/usr/bin/env python3
"""Mega Gardevoir cry pose (frame 2) for the front and back sprites.

Frame 2 is built ONLY from frame 1 (x 0-79) of the real sprites in
res/pokemon/gardevoir/forms/mega/; the existing frame 2 is ignored.
The gown is NOT touched on either side (owner feedback: keep the flowing
gown silhouette exactly as in frame 1); the gesture lives in the arm, hand,
head and upper body.

FRONT, "Rise and raise" (round 7)
  * the whole upper body (head, hair, chest, both arms, hair drips) rises
    1 px out of the gown (a pure shift; the round 3-5 crown shear is gone);
    the one new waist row is shaded darker on the right (FC24DF)
  * the extended arm (viewer's left) bends at frame 1's elbow: the upper arm
    is frame 1's own pixels, the forearm rises from the elbow (outline steps
    in 1 px above the elbow point), a 4-row forearm, and an open hand with
    one soft rounded tip, a 5 px palm and a 1 px thumb bump

BACK, "Head up, wave" (round 7)
  * the head lifts 1 px; row 21 is redrawn (neck base); under the right hair
    lock frame 1's 3x1 hole is kept (the risen shoulder spike closes it)
  * the far arm (viewer's left) is raised: a 3 px, ~10 px long upper arm,
    a rounded elbow at x42, a 45-degree forearm, an open hand (1 px
    fingertips, small thumb) clear of the hair; a clean background pocket
    under the arm down to the gown-top cap
  * the near red shoulder spike rises 1 px with the wave
  * the gown and the near arm are untouched (every gown pixel = frame 1)

Usage: animate_gardevoir_cry.py [--install] [--previews]
  default    writes tools/mega_sprites/previews/gardevoir_{front,back}.png
  --install  writes res/pokemon/gardevoir/forms/mega/{front,back}.png instead
  --previews also writes the GIFs and gardevoir_frames.png to previews/
"""
import os
import sys

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MEGA = os.path.join(ROOT, 'res/pokemon/gardevoir/forms/mega')
PREV = os.path.join(ROOT, 'tools/mega_sprites/previews')
F = 80
HEX = '0123456789ABCDEF'
BG = (200, 208, 216)
GIF_MS = [300, 430, 1000]

# In the ASCII blocks: '.' = transparent, ',' = keep what is there, hex digit
# = palette index.  (1 white, 2 light grey, 3 grey, 4 mid grey, C lavender
# white, D dark grey, 5/6/7/B greens, 8/9/E reds, F outline.)

# ==========================================================================
# FRONT
# ==========================================================================
# Round 2: the upper body rises 1 px (round 1 used 2, which stretched the
# waist into a wasp stalk); the gown is byte-identical to frame 1.
FRONT_LIFT = 1


def front_upper(x, y):
    """frame 1 pixels that belong to the upper body (they rise)."""
    return y <= 33 or (34 <= y <= 35 and x >= 42) or (36 <= y <= 41 and x >= 48)


# the one waist row the rise opens (row 33, x 27-32).  Round 5: not a copy
# of row 32 any more; the right side darkens (2 -> 4 -> D) so the stalk
# tapers into the gown collar (row 34 'DC1C4') instead of looking stretched.
FRONT_WAIST_X0, FRONT_WAIST_Y = 27, 33
FRONT_WAIST = 'FC24DF'

# frame 1 arm after the rise.  Round 5: the old hand (rows 11-16, x <= 21)
# and every arm pixel x <= 22 on rows 17-27 are cleared, then FRONT_ARM
# redraws rows 17-27 (it repeats frame 1's upper-arm pixels it keeps).
FRONT_ARM_CLEAR = [(0, 11, 21, 16), (0, 17, 22, 27)]   # x0, y0, x1, y1

# Round 5: the forearm now starts at frame 1's ELBOW (x 16-19, rows 24-26),
# not at its wrist, so shoulder-to-fingertip stays about 12-13 px (frame 1's
# arm is about 11-12).  Only the upper arm (x >= 19 on rows 24-27, frame 1
# pixels) is kept; frame 1's forearm (x 14-18, rows 21-25) is removed.
#   * elbow: rounded outer corner (15,25) -> (16,26) -> (17-18,27); a light
#     '2' row and a 'D' under-edge at the bend (like frame 1's arm at 24-26)
#   * forearm (rows 22-24) leans 1 column toward the elbow every 2 rows,
#     4-5 px inside; shade column 3 on the left, right edge 4 / D / D
#   * hand (rows 17-22, top at y 17): two finger groups split by a notch
#     (16,17) and a dark 'D' crease (16,19); a 2x2 thumb lobe (19-20,20-21)
#     toward the head with its own outline; heel narrows into the wrist
FRONT_ARM_X0, FRONT_ARM_Y0 = 13, 14
# Round 7: hand moved up 2 rows (tip y14) and the forearm gets 2 more rows
# (wrist row 20, forearm rows 21-24, 4 px fill), so the elbow bend reads.
# Palm is 5 px fill (x14-18) with one soft rounded tip ('FF' row 14 over
# 'F11F' row 15) and a 1 px thumb bump at (19,18).  Left shade column is
# broken (3,3,2,3,2,3,D) and ends in D at the elbow underside (17,24).
FRONT_ARM = [
    # x: 13  17  21
    ',,FF',        # 14  soft rounded fingertip (',' keeps the hair
    ',F11F',       # 15   outline at x22: round 7 fix, '.' erased it)
    'F1121F....',  # 16  soft finger crease (2)
    'F11211F...',  # 17
    'F31111CF..',  # 18  1 px thumb bump (19,18)
    'F311CDF...',  # 19  palm bottom
    '.FF214F...',  # 20  wrist 3 px (heel outline steps in)
    '..F31CDF..',  # 21  forearm
    '..F211DF..',  # 22
    '...F31C4F.',  # 23
    '...FD11DF.',  # 24  outline stepped in above the elbow point
    '..FD21CCDF',  # 25  elbow point (15,25); x 19-22 = frame 1
    '...FD32CCD',  # 26  x 19-22 = frame 1
    '....FFD3C3',  # 27  x 18-22 = frame 1
]

def front_frame2(f1):
    g = [[0] * F for _ in range(F)]
    for y in range(F):
        for x in range(F):
            if f1[y][x] and not front_upper(x, y):
                g[y][x] = f1[y][x]
    for y in range(F):
        for x in range(F):
            if f1[y][x] and front_upper(x, y):
                g[y - FRONT_LIFT][x] = f1[y][x]
    paste(g, FRONT_WAIST_X0, FRONT_WAIST_Y, [FRONT_WAIST])
    for x0, y0, x1, y1 in FRONT_ARM_CLEAR:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                g[y][x] = 0
    paste(g, FRONT_ARM_X0, FRONT_ARM_Y0, FRONT_ARM)
    return g


# ==========================================================================
# BACK
# ==========================================================================
BACK_HEAD_LIFT = 1
BACK_HEAD_MAXY = 21          # frame 1 rows <= this are the head (they rise)
# Row 21 is redrawn (not a copy of row 22): the shaded base of the neck
# under the hair (x 52-60) and the tip of the right hair lock (x 61-64),
# which now tapers F D 7 7 F (row 20) -> F F F F (row 21) instead of being
# stretched by a duplicated row.
# Round 5: the gap under the right hair lock is closed on row 21 (x 61-63 = D,
# the shaded neck under the lock) and frame 1's outline pixel (65,21) is
# back, so the only background under the lock is frame 1's own 3x1 hole at
# (61-63,22) plus its (60,20) notch.
BACK_ROW21 = (52, 'FD422D4DF...FF')

# frame 1 far-arm stub (viewer's left, hanging down by the gown) is cleared
# (BACK_ARM_CLEAR below); rows >= 30 stay exactly frame 1.

# Round 7 far arm: shorter and thinner (round-6 critique: arm ~26 px long vs
# the near arm's ~18-20, upper arm 5-7 px thick, flat stamped 3/4 bands,
# ruled C rim, dark knot at the armpit).
#   * hand + forearm moved (+2,+2) along the forearm line, i.e. the forearm
#     loses two diagonal steps and the hand sits lower and further right;
#     gaps to the hair stay >= 1 px incl. diagonals (thumb moved down to row
#     16 so its outline (45,16) no longer touches the hair at (46,14)); the
#     channel between forearm and hair stays open at the top
#   * elbow at x42-43 (upper arm ~10 px, was ~12): outer contour
#     (41,21) -> (42,22..24) -> (43,25) -> bottom outline row 26
#   * upper arm 3 px fill (rows 23-25, was 4-5): 1 with a C sheen at x48-49,
#     1, then ONE varied underside row 2 2 3 3 3 4 ending in D only at the
#     armpit (x50-51); bottom outline row 26 x44-51
#   * lit rim: the C staircase is broken by a 1 at (40,19); C at the elbow
#     only on rows 22-23
#   * under the arm rows 27-28 are background (clean pocket, no D sliver);
#     the gown-top cap F runs (47,29)->(51,29) over frame 1's '22'
BACK_ARM = [   # (x0, y, row); '.' = transparent, ',' = keep
    (42, 10, 'F'),
    (39, 11, 'F.F1F'),
    (37, 12, 'FF1F11F'),
    (36, 13, 'FC11D13F'),
    (36, 14, 'FC11113F'),
    (36, 15, 'FC11113FF'),      # thumb top outline (43-44,15)
    (37, 16, 'FC11111CF'),      # small thumb (43-44,16), outline x45
    (37, 17, 'FC1134FF'),       # thumb underside (43-44,17)
    (38, 18, 'FC114F'),
    (39, 19, 'F1123FF'),        # rim broken by a 1 at (40,19)
    (40, 20, 'FC1113F'),
    (41, 21, 'FC1124F'),        # crook F (47,21)
    (42, 22, 'FC111DFFFF'),     # upper-arm top outline x48-51
    (42, 23, 'FC1111CC11'),     # C sheen (48-49,23)
    (42, 24, 'F111111112'),
    (42, 25, '.F2233334DD4'),   # one varied underside row, D at the armpit
    (42, 26, '..FFFFFFFF'),     # bottom outline x44-51
    (42, 27, '..........'),     # pocket under the arm (x52 = frame 1 F)
    (42, 28, '..........'),
    (42, 29, '.....FFFFF'),     # gown-top cap over frame 1's '22' (48-49,30)
]
BACK_ARM_CLEAR = (46, 26, 51, 29)     # frame 1 hanging arm stub (x0,y0,x1,y1)

# Round 7: the near shoulder takes part in the wave - the red shoulder spike
# (x61-66, frame 1 rows 23-27) rises 1 px (a pure copy of frame 1's pixels,
# closing frame 1's 3x1 hole under the hair lock at row 22 again), and the
# one new shoulder row under it (row 27) is hand-drawn so the near arm below
# (rows >= 28, frame 1) joins without a repeated row.
BACK_SPIKE = (61, 66, 23, 27)          # x0, x1, frame-1 y0, y1 (rise 1 px)
BACK_SPIKE_ROW27 = (61, '2334F')


def back_frame2(f1):
    g = [r[:] for r in f1]
    # head rises 1 px
    for y in range(BACK_HEAD_MAXY + 1):
        for x in range(F):
            g[y][x] = 0
    for y in range(BACK_HEAD_MAXY + 1):
        for x in range(F):
            if f1[y][x]:
                g[y - BACK_HEAD_LIFT][x] = f1[y][x]
    paste(g, BACK_ROW21[0], 21, [BACK_ROW21[1]])
    # far arm raised
    x0, y0, x1, y1 = BACK_ARM_CLEAR
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            g[y][x] = 0
    for bx, by, row in BACK_ARM:
        paste(g, bx, by, [row])
    sx0, sx1, sy0, sy1 = BACK_SPIKE
    for y in range(sy0, sy1 + 1):
        for x in range(sx0, sx1 + 1):
            g[y - 1][x] = f1[y][x]
    paste(g, BACK_SPIKE_ROW27[0], sy1, [BACK_SPIKE_ROW27[1]])
    return g


# ==========================================================================
# helpers / output
# ==========================================================================
def paste(g, x0, y0, rows):
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch == ',':
                continue
            g[y0 + dy][x0 + dx] = 0 if ch == '.' else HEX.index(ch)


def apply_fix(g, fix):
    for (x, y), v in fix.items():
        g[y][x] = v


def read_pal(path):
    lines = open(path).read().replace('\r', '').split('\n')[3:]
    return [tuple(int(v) for v in l.split()) for l in lines if l.strip()][:16]


def load(side):
    im = Image.open(os.path.join(MEGA, side + '.png'))
    ix = Image.frombytes('L', im.size, im.tobytes())
    f1 = [[ix.getpixel((x, y)) for x in range(F)] for y in range(F)]
    return im, f1


def check(side, im, sheet_img):
    real = Image.frombytes('L', im.size, im.tobytes())
    out = Image.frombytes('L', sheet_img.size, sheet_img.tobytes())
    for y in range(F):
        for x in range(F):
            assert out.getpixel((x, y)) == real.getpixel((x, y)), \
                '%s: frame 1 changed at %d,%d' % (side, x, y)
    used = {real.getpixel((x, y)) for y in range(F) for x in range(F)}
    f2 = [[out.getpixel((F + x, y)) for x in range(F)] for y in range(F)]
    extra = {v for row in f2 for v in row} - used
    assert not extra, '%s: frame 2 uses new indices %s' % (side, extra)
    for y in range(F):
        for x in range(F):
            if min(x, y, F - 1 - x, F - 1 - y) < 2:
                assert f2[y][x] == 0, \
                    '%s: frame 2 art within 2 px of the edge at %d,%d' % (side, x, y)
    # hygiene: no isolated pixels, no fill colour touching transparency
    for y in range(1, F - 1):
        for x in range(1, F - 1):
            v = f2[y][x]
            if not v:
                continue
            nb = [f2[y + dy][x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            assert any(nb), '%s: loose pixel at %d,%d' % (side, x, y)
    return f2


def sheet(im, f1, f2):
    out = Image.new('P', (2 * F, F), 0)
    out.putpalette(im.getpalette())
    px = out.load()
    for y in range(F):
        for x in range(F):
            px[x, y] = f1[y][x]
            px[x + F, y] = f2[y][x]
    return out


def rgb(frame, pal, scale, bg=BG):
    img = Image.new('RGB', (F, F), bg)
    px = img.load()
    for y in range(F):
        for x in range(F):
            if frame[y][x]:
                px[x, y] = pal[frame[y][x]]
    return img.resize((F * scale, F * scale), Image.NEAREST)


def gif(f1, f2, pal, scale, path):
    a, b = rgb(f1, pal, scale), rgb(f2, pal, scale)
    a.save(path, save_all=True, append_images=[b, a],
           duration=GIF_MS, loop=0, disposal=1, optimize=False)
    with Image.open(path) as chk:
        assert chk.n_frames == 3, path
        assert chk.info.get('loop') == 0, path


def main():
    install = '--install' in sys.argv
    previews = '--previews' in sys.argv
    os.makedirs(PREV, exist_ok=True)
    frames = {}
    for side, fn in (('front', front_frame2), ('back', back_frame2)):
        im, f1 = load(side)
        f2 = fn(f1)
        out = sheet(im, f1, f2)
        check(side, im, out)
        frames[side] = (f1, f2)
        dst = (os.path.join(MEGA, side + '.png') if install
               else os.path.join(PREV, 'gardevoir_%s.png' % side))
        out.save(dst, bits=4, transparency=0)
        print('wrote', os.path.relpath(dst, ROOT))
    if previews:
        normal = read_pal(os.path.join(MEGA, 'normal.pal'))
        shiny = read_pal(os.path.join(MEGA, 'shiny.pal'))
        for side, (f1, f2) in frames.items():
            base = os.path.join(PREV, 'gardevoir_' + side)
            gif(f1, f2, normal, 4, base + '.gif')
            gif(f1, f2, shiny, 4, base + '_shiny.gif')
            gif(f1, f2, normal, 1, base + '_1x.gif')
        s = 5
        grid = Image.new('RGB', (2 * F * s, 4 * F * s), BG)
        r = 0
        for side in ('front', 'back'):
            f1, f2 = frames[side]
            for pal in (normal, shiny):
                grid.paste(rgb(f1, pal, s), (0, r * F * s))
                grid.paste(rgb(f2, pal, s), (F * s, r * F * s))
                r += 1
        grid.save(os.path.join(PREV, 'gardevoir_frames.png'))
        print('wrote previews to', os.path.relpath(PREV, ROOT))


if __name__ == '__main__':
    main()
