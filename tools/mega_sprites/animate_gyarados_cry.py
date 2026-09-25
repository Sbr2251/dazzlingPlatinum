#!/usr/bin/env python3
"""Mega Gyarados cry pose: new frame 2 for the front and back sprites.

Frame 2 is built only from frame 1 (x 0-79) of the real sheets; the existing
frame 2 is ignored. sprite_data.json shows frame 2 once for ~26 ticks on battle
entry, so it is a big one-shot gesture. Every part is frame-1 art moved as a
rigid layer (translation only, nothing stretched or re-shaded); joins and
outlines are re-drawn by hand in FRONT_PAINT / BACK_PAINT.

FRONT "lunge and roar"
  * the head, crest and dorsal fins lunge FRONT_DX px left (toward the
    player) and FRONT_DY px down as one rigid layer (the big dorsal fin
    keeps its frame-1 drawing; no per-column flare);
  * the lower jaw (FRONT_CHIN) drops a further FRONT_CHIN_DY px as a hinged
    piece: its five frame-1 rows are copied unchanged and sheared forward
    1 px per 2 rows (FRONT_CHIN_SHEAR), so the jaw swings open on its hinge
    (hinge ~(20,45), tip ~(13,49)) instead of hanging as a box; FRONT_PAINT
    is the hand-drawn maw (upper fangs, a black upper throat, a 4-px red
    tongue shaded dark red lying on the jaw, a lower fang) closed at the
    front by a black lip line and joined at the back by the red cheek strip;
    the whisker loop swings FRONT_LOOP_DX px further out, clear of the lip;
  * the neck rows (FRONT_BAND) are re-laid whole, each row shifted, so the
    neck leans into the lunge at its frame-1 width; where it meets the
    planted whisker root the 1-px lean is absorbed inside the black
    underside run, so no stripe or navy run is lengthened;
  * the body answers the lunge: the coil, belly and long whisker dip
    FRONT_BODY_DY px and the lower-left fin flares up FRONT_FIN_LIFT px
    relative to them (FRONT_PAINT_JOINS closes the belly/fin join);
  * the long right whisker keeps frame 1's drawing; the throat strand is
    continued 1:1 (FRONT_STRAND_END) so it runs from the chin to the belly.

BACK "rear back, roar, tail flick"
  * the upper body rears back toward the tail: the fin block, crest and
    head top (rows down to y 37) move 5 px left as one rigid layer, and the
    body below ramps back into place 1 px per 2 rows over rows 38-45
    (BACK_LEAN_ROWS), so no spike is sheared; the crest keeps every row
    and its tip stays at y 3; the red triangle marking moves 1 px left
    whole so it keeps its slanted frame-1 shape;
  * the head column (lower mouth, column and prongs, BACK_JAW) lifts
    1 px (BACK_JAW_DY = -1); the whiskers hanging from it lift with it and
    their straight runs repeat one row, so the loop and curl stay put;
  * the whole lower-right fin blade, base wedge included, flares
    BACK_BLADE_D (1 px out, 4 px up); the small navy spine is drawn on top
    of it (as in frame 1), moved BACK_SPINE_D with the lean, so its 44 fill
    shows; frame 1's column outline stays behind the blade;
  * everything above is relative to BACK_LIFT: the whole creature rises
    1 px as it rears, so the fin block moves (-5,-1), the head column
    (0,-2) and the loops/curls hang 1 px higher;
  * the tail flicks up: tip and joint rise 2 px as one rigid piece
    (BACK_TAIL_STEPS/LIFT), the root and the lower small fin stay planted,
    and the joint's fill runs on through the seam into the root;
  * BACK_PAINT hand-cleans the red triangle, the spine pinhole, the column
    edge under the blade and the tail seam.

Usage: animate_gyarados_cry.py [--install] [--previews]
  default    writes tools/mega_sprites/previews/gyarados_{front,back}.png
  --install  writes res/pokemon/gyarados/forms/mega/{front,back}.png instead
  --previews also writes the preview GIFs and gyarados_frames.png
"""
import os
import sys

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MEGA = os.path.join(ROOT, 'res/pokemon/gyarados/forms/mega')
PREV = os.path.join(ROOT, 'tools/mega_sprites/previews')
F = 80

# ---------------------------------------------------------------- FRONT ----
FRONT_DX, FRONT_DY = -6, 1   # head/crest lunge (left = toward the player)
# lower jaw (frame-1 rows -> column span): it moves as one piece, a further
# FRONT_CHIN_DY px down, so the maw opens and the chin keeps its drawing
FRONT_CHIN = {41: (20, 26), 42: (20, 26), 43: (20, 26),
              44: (20, 26), 45: (21, 25)}
FRONT_CHIN_DY = 3
# the jaw swings open on its hinge (back, top right): its five frame-1 rows
# are copied unchanged, and the lower rows step forward 1 px per 2 rows, so
# the jaw leans forward/down like a jaw rotated open (frame-2 tip ~(13,49),
# hinge ~(20,45)) instead of hanging as a box.  Frame-1 row -> extra x shift.
FRONT_CHIN_SHEAR = {41: 0, 42: 0, 43: -1, 44: -1, 45: -1}
FRONT_LOOP = (12, 18, 40, 46)  # whisker loop box (x0, x1, y0, y1) in frame 1 ...
FRONT_LOOP_DX = -2             # ... it swings 2 px further out, clear of the lip
# neck (frame-1 rows 37..47 minus FRONT_BAND_DROP, x <= FRONT_BAND_CUT) re-laid
# on frame-2 rows 38..47, each row shifted whole: the neck leans into the
# lunge at its full frame-1 width; the gap at the right cut is flat colour
FRONT_BAND = (37, 47)
FRONT_BAND_DROP = None
FRONT_BAND_CUT = 57
# an int shifts the whole row; (left, right, split_x) shifts frame-1 pixels
# x <= split_x by left and the rest by right, filling the 1-px gap inside the
# neck's flat black underside run, so where the neck meets the planted
# whisker root (frame-1 rows 45-46) no navy/red run is lengthened
FRONT_NECK_SHIFT = (-6, -6, -5, -5, -4, -3, -2, (-2, -1, 40), (-1, 0, 40),
                    (-1, 0, 40), 0)  # frame-2 rows 38..48
# the coil, belly, lower-left fin and long whisker dip this many px as the
# body takes the weight of the lunge (the neck then keeps all its rows)
FRONT_BODY_DY = 1
FRONT_FIN = (15, 33, 53, 63)  # lower-left fin box (x0, x1, y0, y1) in frame 1 ...
FRONT_FIN_LIFT = 2            # ... lifted this many px as the body answers the lunge
# Hand-painted pixels, frame-2 coordinates: {y: (x0, row)}; ' ' keeps the
# pixel, '.' clears it, a hex digit sets that palette index.
FRONT_PAINT = {
    39: (11, "7666777777" + " " * 7 + "c"),
    40: (8, "7767ccbcccbcc7" + " " * 6 + "cc"),
    41: (12, "fcbccccc77"),
    42: (12, "fccc66cc77"),
    43: (12, "fcc6666c77"),
    44: (13, "fb7777c77"),
}
# The long right whisker (x >= FRONT_WHISKER_X0) could sway its upper run
# per row; since round 8 it is empty, so the whisker is frame 1's exactly.
FRONT_WHISKER_X0 = 62
FRONT_WHISKER_SWAY = {}

FRONT_PAINT_JOINS = {
    # the lifted fin's root meets the dipped belly line: finish the belly's
    # diagonal on the fin's top edge, and give the fin root its frame-1 dark
    # outline against the coil (frame-1 rows 54-55: '353c' over '3c7fc')
    52: (32, "3c"),
    53: (32, "fc"),
}
# throat barbel strand: frame 1's strand runs from the chin almost to the
# belly; continue it 1:1 down-right from its frame-2 end (26-27,48) so it
# reads as one strand again, stopping 1 px short of the fin root (as frame 1
# stops 1 px short of the belly) so the pocket behind the jaw stays open
FRONT_STRAND_END = {49: (27, "5c"), 50: (28, "5c")}
# neck underside: the per-row neck shifts leave a step in the dark
# underside at rows 42-43; these two pixels even it into a clean diagonal
FRONT_NECK_STEP = {42: (31, "c"), 43: (33, "f"), 44: (34, "f")}

# ----------------------------------------------------------------- BACK ----
# The upper body rears back toward the tail: every row down to y 37 (the fin
# block, crest and head top) moves 5 px left as one rigid layer, and rows
# 38-45 ramp back 1 px per 2 rows (BACK_LEAN_ROWS: last row of each shift
# band), so the lean is gradual, no spike is sheared, nothing is stretched,
# shrunk or dropped. The crest keeps every row and its tip stays at y 3.
BACK_LEAN_ROWS = ((37, -5), (39, -4), (41, -3), (43, -2), (45, -1))
# lower jaw: everything under the mouth band (x 44-67 from row 55 down: the
# band's lower lip, the jaw block and its prongs) could drop BACK_JAW_DY px as
# one piece; since round 8 it LIFTS 1 px (-1): the head column rises as it
# roars, taking the lower mouth band up with it
BACK_JAW_DY = -1
BACK_JAW_DX = 0
def back_jaw(x, y):
    return ((39 <= x <= 43 and 52 <= y <= 59) or (44 <= x <= 47 and y >= 54)
            or (48 <= x <= 67 and 55 <= y <= 58) or (48 <= x <= 66 and y >= 59))
# whiskers hang from the jaw: their top runs move with it and their straight
# vertical runs absorb BACK_JAW_DY (shorter when it drops, the run's last row
# repeated when it lifts), so the loop and curl stay put.
# (box x0, x1, y0, y1; first and last row of the straight run)
BACK_WHISKERS = (((40, 48, 56, 72), (66, 70)),    # centre whisker
                 ((67, 69, 59, 70), (65, 70)))    # right whisker
# lower-right blade (x >= its left edge per row, rows 37-56 incl. the 888
# base wedge and the stem): it flares 1 px out and 4 px up as one piece; the
# spine leans with the head rows underneath it
BACK_BLADE_EDGE = {47: 70, 48: 69, 49: 69, 50: 68, 51: 67}
def back_blade(x, y):
    edge = 71 if y < 47 else BACK_BLADE_EDGE.get(y, 67)
    return 37 <= y <= 56 and x >= edge
BACK_BLADE_D = (-1, -4)
# last frame-1 blade row moved (56 = all of it, base wedge included)
BACK_BLADE_LAST = 56
# draw order: False = the blade goes over the spine, so the moved base
# wedge (888) shows whole at x ~66-70, y 46-49
BACK_SPINE_ON_TOP = True
BACK_SPINE_D = (-2, -1)
# the whole creature rises this many px as it rears up to roar (on top of
# the lean, the head-column lift and the blade/tail flicks, which are all
# relative to it); the crest tip lands on y 2
BACK_LIFT = -1
def back_spine(x, y):
    """The small navy spine at the head's right edge, in front of the blade."""
    return 44 <= y <= 49 and 65 <= x <= 70 and not back_blade(x, y)
# tail flick: tail pixels (x <= 22, y >= 50, minus the body's spike fin) are
# lifted per column, BACK_TAIL_LIFT[i] px for x <= BACK_TAIL_STEPS[i]: the
# tip and joint (x <= 16) rise 2 px as one rigid piece, the root and the lower
# small fin stay planted; any fill pixel a step leaves bare gets an f outline
BACK_TAIL_STEPS = (16, 22)
BACK_TAIL_LIFT = (2, 0)
BACK_TAIL_FIN = (16, 57, 63)   # the middle tail fin (x >= x0, rows y0..y1)
                               # lifts as one piece with its segment
BACK_JAW_FILL = {}
# Hand-painted joins, frame-2 coordinates (same format as FRONT_PAINT).
BACK_PAINT = {
    # red triangle on the left body column (frame 1 x 34-37, rows 43-47):
    # the lean's 2-rows-per-px ramp would split it across three shifts;
    # carry the whole marking 1 px left instead, so it keeps frame 1's
    # vertical right edge and slanted left edge (the dark underline under
    # it gives up its last pixel to the moved base)
    43: (35, "16"),
    # row 46 also gets the outline back at x 27 (the ramp's 0-shift row
    # left a 1-px dent) and the navy underline keeps its frame-1 5 px
    46: (27, "f5555566661"),
    # the -3 / -2 ramp step at rows 41/42 made a 2-px jog in the left
    # outline; one more outline pixel makes it step 1 px at a time
    42: (25, "f"),
    47: (33, "5661"),
    # the whole blade slides (-1,-4) off the column; frame 1's column
    # outline (x 65 at rows 50-51, x 66 at rows 52-56) stays, and the one
    # stem-rim pixel left on it at (66,54) turns black
    54: (66, "f"),
    # tail joint -> root seam: the lifted joint's fill runs on through the
    # divider into the planted root (as frame 1 rows 65-68 do) instead of
    # ending in a black bar; the bottom outline bends down 13/14/15/16/16/17
    65: (17, "1"),
    66: (16, "11"),
    67: (16, "f1"),
}

def load(name):
    im = Image.open(os.path.join(MEGA, name))
    ix = Image.frombytes('L', im.size, im.tobytes())
    return im, [[ix.getpixel((x, y)) for x in range(F)] for y in range(F)]


def blank():
    return [[0] * F for _ in range(F)]


def paste(dst, src, dx=0, dy=0):
    for y in range(F):
        for x in range(F):
            v = src[y][x]
            if v and 0 <= x + dx < F and 0 <= y + dy < F:
                dst[y + dy][x + dx] = v


# ---------------------------------------------------------------- FRONT ----
def front_layer(x, y):
    x0, x1, y0, y1 = FRONT_FIN
    if x0 <= x <= x1 and y0 <= y <= y1 and x <= 31:
        return 'fin'
    if x >= 62 and y >= 29:
        return 'lower'           # long right whisker
    if x <= 33 and y <= 47:
        return 'head'
    if y < FRONT_BAND[0]:
        return 'upper'           # crest, dorsal fins, top of neck
    if y <= FRONT_BAND[1] and x <= FRONT_BAND_CUT:
        return 'band'            # neck
    return 'lower'


def paint(out, table, dy=0):
    for y, (x0, s) in table.items():
        for i, ch in enumerate(s):
            if ch != ' ':
                out[y + dy][x0 + i] = 0 if ch == '.' else int(ch, 16)


def build_front(f1):
    L = {k: blank() for k in ('head', 'upper', 'band', 'fin', 'lower')}
    for y in range(F):
        for x in range(F):
            if f1[y][x]:
                L[front_layer(x, y)][y][x] = f1[y][x]
    out = blank()
    paste(out, L['lower'], 0, FRONT_BODY_DY)
    for y, sw in FRONT_WHISKER_SWAY.items():
        row = [(x, out[y][x]) for x in range(FRONT_WHISKER_X0, F) if out[y][x]]
        for x, _ in row:
            out[y][x] = 0
        for x, v in row:
            out[y][x + sw] = v
    cut = FRONT_BAND_CUT
    rows = [r for r in range(FRONT_BAND[0], FRONT_BAND[1] + 1) if r != FRONT_BAND_DROP]
    y0 = FRONT_BAND[1] + 1 + FRONT_BODY_DY - len(rows)
    for i, (r, s) in enumerate(zip(rows, FRONT_NECK_SHIFT)):
        oy = y0 + i
        sl, sr, sx = s if isinstance(s, tuple) else (s, s, F)
        for x in range(F):
            if L['band'][r][x]:
                out[oy][x + (sl if x <= sx else sr)] = L['band'][r][x]
        for x in range(sx + sl + 1, sx + sr + 1):   # split gap: flat black
            out[oy][x] = f1[r][sx]
        s = sr
        for x in range(cut + s + 1, cut + 1):   # gap at the cut: flat colour
            if f1[r][x] and not out[oy][x]:
                out[oy][x] = f1[r][cut]
    paste(out, L['fin'], 0, FRONT_BODY_DY - FRONT_FIN_LIFT)
    paste(out, L['upper'], FRONT_DX, FRONT_DY)
    lx0, lx1, ly0, ly1 = FRONT_LOOP
    for y in range(F):
        for x in range(F):
            v = L['head'][y][x]
            if not v:
                continue
            dx, dy = FRONT_DX, FRONT_DY
            if y in FRONT_CHIN and FRONT_CHIN[y][0] <= x <= FRONT_CHIN[y][1]:
                dy += FRONT_CHIN_DY
                dx += FRONT_CHIN_SHEAR[y]
            elif lx0 <= x <= lx1 and ly0 <= y <= ly1:
                dx += FRONT_LOOP_DX
            out[y + dy][x + dx] = v
    paint(out, FRONT_PAINT)
    paint(out, FRONT_PAINT_JOINS)
    paint(out, FRONT_STRAND_END)
    paint(out, FRONT_NECK_STEP)
    return out


# ----------------------------------------------------------------- BACK ----
def back_lean(y):
    for lim, sft in BACK_LEAN_ROWS:
        if y <= lim:
            return sft
    return 0


def build_back(f1):
    """Built in round-8 frame-2 coordinates, then everything but the whisker
    loop/curl ends is placed BACK_LIFT px higher (y + G)."""
    out = blank()
    G = BACK_LIFT
    D = BACK_JAW_DY + G
    wh = set()
    for (x0, x1, y0, y1), (s0, s1) in BACK_WHISKERS:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if f1[y][x]:
                    wh.add((x, y))
    for y in range(F):
        for x in range(F):
            v = f1[y][x]
            if not v or (x, y) in wh or back_blade(x, y):
                continue
            if back_jaw(x, y):
                dx, dy = BACK_JAW_DX, D
            else:
                dx, dy = back_lean(y), G
            out[y + dy][x + dx] = v
    # whiskers: top run moves with the jaw, the straight run absorbs the
    # jaw's own lift (BACK_JAW_DY), and the loop/curl ends move only G
    J = BACK_JAW_DY
    for (x0, x1, y0, y1), (s0, s1) in BACK_WHISKERS:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                v = f1[y][x]
                if not v:
                    continue
                if J < 0:
                    # lifted: the run's last row repeats to bridge the lift
                    if y <= s1:
                        out[y + J + G][x + BACK_JAW_DX] = v
                    if y >= s1:
                        out[y + G][x] = v
                    if y == s1:
                        for k in range(1, -J):
                            out[y - k + G][x] = v
                elif y <= s1 - J:
                    out[y + J + G][x + BACK_JAW_DX] = v
                elif y > s1:
                    out[y + G][x] = v
    bdx, bdy = BACK_BLADE_D
    def blade():
        for y in range(F):
            for x in range(F):
                if f1[y][x] and back_blade(x, y) and y <= BACK_BLADE_LAST:
                    out[y + bdy + G][x + bdx] = f1[y][x]
    def spine():
        sdx, sdy = BACK_SPINE_D
        for y in range(F):
            for x in range(F):
                if f1[y][x] and back_spine(x, y):
                    out[y + sdy + G][x + sdx] = f1[y][x]
    if BACK_SPINE_ON_TOP:
        blade(); spine()
    else:
        spine(); blade()
    back_tail(f1, out, G)
    paint(out, BACK_JAW_FILL, G)
    paint(out, BACK_PAINT, G)
    return out


def back_spike(x, y):
    """The body's spike fin left of the column (planted, not tail)."""
    return y <= 56 and x >= 14 or y <= 58 and x >= 19


def back_tail(f1, out, G=0):
    tail = {(x, y) for y in range(50, F) for x in range(23)
            if f1[y][x] and not back_spike(x, y)}
    fx, fy0, fy1 = BACK_TAIL_FIN
    moved = {}
    for x, y in tail:
        out[y + G][x] = 0
        xs = max(x, BACK_TAIL_STEPS[-2] + 1) if x >= fx and fy0 <= y <= fy1 else x
        k = next(k for t, k in zip(BACK_TAIL_STEPS, BACK_TAIL_LIFT) if xs <= t)
        moved[(x, y - k + G)] = f1[y][x]
    for (x, y), v in moved.items():
        out[y][x] = v
    for (x, y), v in moved.items():     # outline fill pixels the steps bared
        if v in (0xf, 0x7, 0xc):
            continue
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not out[ny][nx]:
                out[ny][nx] = 0xf


# ---------------------------------------------------------------- output ---
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
    assert res_im.mode == 'P' and res_im.size == (2 * F, F)
    assert res.crop((0, 0, F, F)).tobytes() == src.crop((0, 0, F, F)).tobytes(), 'frame 1 changed'
    assert res.crop((F, 0, 2 * F, F)).tobytes() == bytes(v for r in f2 for v in r)
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


def write_gif(path, f1, f2, pal, scale, bg=(200, 208, 216)):
    fr = [render(f, pal, scale, bg) for f in (f1, f2, f1)]
    fr[0].save(path, save_all=True, append_images=fr[1:],
               duration=[300, 430, 1000], loop=0, disposal=1)
    g = Image.open(path)
    durs = []
    for i in range(g.n_frames):
        g.seek(i)
        durs.append(g.info['duration'])
    assert g.n_frames == 3 and durs == [300, 430, 1000] and g.info.get('loop') == 0, (path, durs)


def write_previews(sheets):
    normal = jasc(os.path.join(MEGA, 'normal.pal'))
    shiny = jasc(os.path.join(MEGA, 'shiny.pal'))
    bg = (200, 208, 216)
    for side, (f1, f2) in sheets.items():
        write_gif(os.path.join(PREV, 'gyarados_%s.gif' % side), f1, f2, normal, 4)
        write_gif(os.path.join(PREV, 'gyarados_%s_shiny.gif' % side), f1, f2, shiny, 4)
        write_gif(os.path.join(PREV, 'gyarados_%s_1x.gif' % side), f1, f2, normal, 1)
    s, gap = 5, 5
    rows = [(sheets['front'], normal), (sheets['front'], shiny),
            (sheets['back'], normal), (sheets['back'], shiny)]
    grid = Image.new('RGB', (2 * F * s + gap, len(rows) * (F * s + gap) - gap), (255, 255, 255))
    for r, ((f1, f2), pal) in enumerate(rows):
        for c, f in enumerate((f1, f2)):
            grid.paste(render(f, pal, s, bg), (c * (F * s + gap), r * (F * s + gap)))
    grid.save(os.path.join(PREV, 'gyarados_frames.png'))


def main():
    install = '--install' in sys.argv
    sheets = {}
    for side, build in (('front', build_front), ('back', build_back)):
        im, f1 = load(side + '.png')
        f2 = build(f1)
        if install:
            path = os.path.join(MEGA, side + '.png')
        else:
            os.makedirs(PREV, exist_ok=True)
            path = os.path.join(PREV, 'gyarados_%s.png' % side)
        save_sheet(im, f1, f2, path)
        check(im, f1, f2, path)
        sheets[side] = (f1, f2)
        print('wrote', os.path.relpath(path, ROOT))
    if '--previews' in sys.argv:
        os.makedirs(PREV, exist_ok=True)
        write_previews(sheets)
        print('wrote previews to', os.path.relpath(PREV, ROOT))


if __name__ == '__main__':
    main()
