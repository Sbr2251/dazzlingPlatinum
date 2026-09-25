#!/usr/bin/env python3
"""Mega Empoleon front sprite, frame 2 "guard sweep" pose.

Reads frame 1 (x 0-79) of res/pokemon/empoleon/forms/mega/front.png and builds
frame 2 from it alone (the existing frame 2 is ignored):

  * blade flipper (viewer's left): removed and redrawn by hand as a roughly
    horizontal guard across chest and belly, gold edge facing down, tip ~(67,47)
  * torso hunches 1 px (rows <= 47 move down, source row 48 is dropped, so
    everything from row 49 down - legs and feet - is untouched)
  * head and crown drop 1 px more (2 px total) and tuck into the collar
  * wing (viewer's right): sheared in toward the body and stretched down, so
    the tips move ~4 px in and ~5 px down; wing stays behind body and blade

Usage: animate_empoleon_guard.py [out.png] [--previews]
Default output: res/pokemon/empoleon/forms/mega/front.png (rewritten in place;
frame 1 is kept). --previews also writes GIFs / PNGs to tools/mega_sprites/previews/.
"""
import os
import sys

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'res/pokemon/empoleon/forms/mega/front.png')
PREV = os.path.join(ROOT, 'tools/mega_sprites/previews')
F = 80
E = 14  # outline index


def load_frame1():
    im = Image.open(SRC)
    ix = Image.frombytes('L', im.size, im.tobytes())
    return im, [[ix.getpixel((x, y)) for x in range(F)] for y in range(F)]


# --------------------------------------------------------------------------
# 1. Remove the frame 1 blade flipper
# --------------------------------------------------------------------------
def blade_mask(f1):
    """True where frame 1's blade flipper is (x <= CUT[y] near the body, then
    the first run of pixels starting at x <= 20 further down)."""
    cut = {34: 31, 35: 32, 36: 30, 37: 32, 38: 32, 53: 31}
    cut.update({y: 34 for y in range(39, 48)})
    cut.update({y: 33 for y in range(48, 53)})
    m = [[False] * F for _ in range(F)]
    for y in range(34, F):
        if y in cut:
            for x in range(cut[y] + 1):
                m[y][x] = f1[y][x] != 0
        else:
            x = 0
            while x < F and f1[y][x] == 0:
                x += 1
            if x > 20:
                continue
            while x < F and f1[y][x] != 0:
                m[y][x] = True
                x += 1
    return m


# --------------------------------------------------------------------------
# 2. Wing mask (viewer's right): first x of the wing on each row
# --------------------------------------------------------------------------
WING_X0 = {}
for _y in range(19, 30): WING_X0[_y] = 55
for _y in range(30, 33): WING_X0[_y] = 56
for _y in range(33, 36): WING_X0[_y] = 57
for _y in range(36, 43): WING_X0[_y] = 56
for _y in range(43, 46): WING_X0[_y] = 55
for _y in range(46, 50): WING_X0[_y] = 58
for _y in range(50, 67): WING_X0[_y] = 61


def is_wing(x, y):
    return y in WING_X0 and x >= WING_X0[y]


# --------------------------------------------------------------------------
# 3. New blade, drawn in target (frame 2) coordinates before the +1 hunch
# --------------------------------------------------------------------------
def runs(spec):
    d = {}
    for (a, b), v in spec:
        for x in range(a, b + 1):
            d[x] = v
    return d


# top / bottom edge rows of the blade for each column (x 25 = base, 67 = tip)
TOP = runs([((25, 36), 35), ((37, 42), 36), ((43, 47), 37), ((48, 52), 38),
            ((53, 56), 39), ((57, 59), 40), ((60, 61), 41), ((62, 63), 42),
            ((64, 64), 43), ((65, 65), 44), ((66, 66), 45), ((67, 67), 46)])
BOT = runs([((25, 38), 47), ((39, 54), 48), ((55, 60), 47), ((61, 67), 46)])

BLADE_PIX = {}


def put(rows, x0, y0):
    """Hand pixels, one string per row separated by '/', hex index per
    pixel, ' ' = leave alone."""
    for j, row in enumerate(rows.split('/')):
        for i, ch in enumerate(row):
            if ch != ' ':
                BLADE_PIX[(x0 + i, y0 + j)] = int(ch, 16)


def col(x, y0, s):
    for j, ch in enumerate(s):
        if ch != ' ':
            BLADE_PIX[(x, y0 + j)] = int(ch, 16)


def build_blade():
    for x in TOP:
        t, b = TOP[x], BOT[x]
        for y in range(t, b + 1):
            BLADE_PIX[(x, y)] = 9
        # outer rim along the top edge: gold near the base, cream further out
        top = [E, 3, E, 6, 8] if x <= 31 else [5, 2, E, 6, 8]
        bot = [E, 3, 3, E, 12]  # from the bottom edge upward: gold edge
        for i, v in enumerate(top):
            if t + i <= b:
                BLADE_PIX[(x, t + i)] = v
        for i, v in enumerate(bot):
            if b - i >= t:
                BLADE_PIX[(x, b - i)] = v
    # rounded base (the wrist end, left of the shoulder)
    col(21, 40, "EEE")
    col(22, 38, "EECCEE")
    col(23, 37, "E6CCCCE3E")
    col(24, 36, "EE68CCCE33E")
    # feathers at the root of the flipper, over the shoulder
    put("E/E6E/E6BEE/ E6BBBE/  E6BBB", 19, 30)
    put("E/E6E/ E6BE/ E6BBE", 24, 31)
    put("EEEE", 21, 35)  # close the bottom of the first feather
    # gold cuff under the base
    put("E3552333E/ E333553E/  E3323E/   EEEE", 27, 47)
    # texture: flecks in the dark body, shading on the rim, grey separator
    for p, v in [((29, 40), 9), ((33, 40), 9), ((40, 41), 9), ((47, 42), 9),
                 ((34, 42), 8), ((50, 43), 8), ((28, 42), 8), ((27, 36), 5),
                 ((30, 36), 5), ((45, 37), 7), ((55, 39), 7), ((33, 44), 15),
                 ((44, 44), 15), ((52, 45), 15), ((41, 44), 9), ((42, 44), 9),
                 ((36, 46), 5), ((48, 47), 5), ((58, 45), 5)]:
        BLADE_PIX[p] = v


build_blade()

# --------------------------------------------------------------------------
# 4. Wing fold: row map (duplicated rows = stretch) and shear
# --------------------------------------------------------------------------
WING_DUP_ROWS = (40, 48, 55, 60)  # each repeated once -> tips drop 4 more


def wing_shift(y):
    """Horizontal shift toward the body for source row y (0 at the root)."""
    return -max(0, min(4, round((y - 36) * 4 / 28)))


# --------------------------------------------------------------------------
# 5. Hand fixes applied last, in final frame 2 coordinates
# --------------------------------------------------------------------------
FIXES = [  # (x, y, index)
    (30, 35, 12), (31, 35, 12),               # under the shoulder knob
    (31, 52, E), (32, 52, 12), (33, 52, 12), (31, 53, E), (30, 54, E),  # coat tail corner
    (59, 53, E),                              # body/wing seam
    (27, 33, E), (23, 37, E),                 # feather root / base notch
]


def build_frame2(f1):
    bm = blade_mask(f1)
    rest = [[0 if bm[y][x] else f1[y][x] for x in range(F)] for y in range(F)]
    out = [[0] * F for _ in range(F)]

    # wing layer (behind everything)
    wing_rows = []
    for y in range(F):
        wing_rows.append(y)
        if y in WING_DUP_ROWS:
            wing_rows.append(y)
    for oy_rel, sy in enumerate(wing_rows):
        oy = oy_rel + 1  # +1 hunch
        if oy >= F:
            break
        for x in range(F):
            if is_wing(x, sy) and rest[sy][x]:
                ox = x + wing_shift(sy)
                out[oy][ox] = rest[sy][x]

    # body layer: rows <= 47 down 1 (row 48 dropped), head rows <= 27 down 2
    body = [[0] * F for _ in range(F)]
    for y in range(F):
        for x in range(F):
            v = rest[y][x]
            if not v or is_wing(x, y):
                continue
            if y <= 27:
                oy = y + 2
            elif y <= 47:
                oy = y + 1
            elif y == 48:
                continue
            else:
                oy = y
            if y <= 27 or body[oy][x] == 0:
                body[oy][x] = v
    for y in range(F):
        for x in range(F):
            if body[y][x]:
                out[y][x] = body[y][x]

    # blade on top (+1 hunch)
    for (x, y), v in BLADE_PIX.items():
        if v:
            out[y + 1][x] = v

    for x, y, v in FIXES:
        out[y][x] = v
    return out


def save_sheet(im, f1, f2, path):
    L = Image.new('L', (2 * F, F))
    L.putdata([(f1[y][x] if x < F else f2[y][x - F])
               for y in range(F) for x in range(2 * F)])
    out = Image.frombytes('P', L.size, L.tobytes())
    out.putpalette(im.getpalette())
    out.save(path, bits=4, transparency=0)


def check(im, f1, f2, path):
    src = Image.frombytes('L', im.size, im.tobytes())
    res_im = Image.open(path)
    res = Image.frombytes('L', res_im.size, res_im.tobytes())
    assert res_im.mode == 'P' and res_im.size == (160, 80)
    assert res.crop((0, 0, 80, 80)).tobytes() == src.crop((0, 0, 80, 80)).tobytes(), 'frame 1 changed'
    used1 = {v for r in f1 for v in r}
    used2 = {v for r in f2 for v in r}
    assert used2 <= used1, 'frame 2 uses new indices %s' % (used2 - used1)
    for i in range(F):
        for (x, y) in ((i, 0), (i, F - 1), (0, i), (F - 1, i)):
            assert f2[y][x] == 0, 'frame 2 border pixel at (%d,%d)' % (x, y)


def jasc(path):
    lines = [l.strip() for l in open(path).read().splitlines() if l.strip()][3:]
    return [tuple(map(int, l.split())) for l in lines][:16]


def render(frame, pal, scale, bg):
    img = Image.new('RGB', (F, F), bg)
    px = img.load()
    for y in range(F):
        for x in range(F):
            if frame[y][x]:
                px[x, y] = pal[frame[y][x]]
    return img.resize((F * scale, F * scale), Image.NEAREST)


def write_previews(f1, f2):
    pdir = os.path.dirname(SRC)
    normal = jasc(os.path.join(pdir, 'normal.pal'))
    shiny = jasc(os.path.join(pdir, 'shiny.pal'))
    bg = (200, 208, 216)
    for name, pal, scale in (('empoleon_front_guard.gif', normal, 4),
                             ('empoleon_front_guard_shiny.gif', shiny, 4),
                             ('empoleon_front_guard_1x.gif', normal, 1)):
        fr = [render(f, pal, scale, bg) for f in (f1, f2, f1)]
        fr[0].save(os.path.join(PREV, name), save_all=True, append_images=fr[1:],
                   duration=[300, 433, 1000], loop=0, disposal=1)
    s = 6
    sheet = Image.new('RGB', (2 * F * s + s, 2 * F * s + s), (255, 255, 255))
    for r, pal in enumerate((normal, shiny)):
        for c, f in enumerate((f1, f2)):
            sheet.paste(render(f, pal, s, bg), (c * (F * s + s), r * (F * s + s)))
    sheet.save(os.path.join(PREV, 'empoleon_front_guard_frames.png'))


def main():
    args = [a for a in sys.argv[1:] if a != '--previews']
    default = os.path.join(ROOT, 'res/pokemon/empoleon/forms/mega/front.png')
    path = args[0] if args else default
    im, f1 = load_frame1()
    f2 = build_frame2(f1)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    save_sheet(im, f1, f2, path)
    check(im, f1, f2, path)
    if '--previews' in sys.argv:
        os.makedirs(PREV, exist_ok=True)
        write_previews(f1, f2)
    print('wrote', path)


if __name__ == '__main__':
    main()
