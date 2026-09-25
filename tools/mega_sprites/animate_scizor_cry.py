#!/usr/bin/env python3
"""Cry-pose frame 2s for Mega Scizor (front and back).

Scizor's sprite animation shows frame 1, then frame 2 once, then stops, so
frame 2 is a one-shot gesture on battle entry and has to read at 1x.
Frame 1 of each sheet is read from the real sprite and kept byte-identical;
frame 2 is rebuilt only from frame 1 (the old frame 2 is ignored).  Every
moving part is a rigid translation of exact frame-1 pixels (no rotation or
resampling); the seams the moves open are closed with small hand patches.

FRONT, "rear up and brandish":
  - the whole sprite rises HOP px;
  - the low claw is flung rigidly LOW_MOVE (3 left, 7 up) to shoulder
    height on a hand-drawn upper arm (elbow up), tucked under the wing's
    dark lower edge;
  - the raised claw lifts rigidly 2 px; its lower blade is pasted back
    hinged (heel 1 px lower, tip 2 px lower) so the pincer gapes, with a
    dark-red inner jaw breaking up the black mouth;
  - secondary action: the wing flares 2 px up and out (the root strip it
    uncovers continues the 45-degree vein stripes); the shins step 1 px
    outward below the knees (feet spread).

BACK, "rise up, claws flung wide":
  - the whole sprite rises HOP px;
  - both claws move rigidly 6 px up (left 5 out, right 3 out), pasted
    BEHIND the lower wing lobes so they clear them; hand-drawn 2-px upper
    arms (dark-red outline, red midtone) run from each shoulder ball to
    the claw base;
  - secondary action: both upper wings flare 2 px up and out (separators
    to the red blade-arms and the right tail outline re-inked); the shins
    step 1 px outward below the knees (feet spread).

Hand edits are the *_PATCH tables below: rows of palette indices
written as hex digits, '.' = transparent, ' ' = leave as is.

Usage: animate_scizor_cry.py [--install] [--previews]
  default    writes tools/mega_sprites/previews/scizor_{front,back}.png
  --install  writes res/pokemon/scizor/forms/mega/{front,back}.png instead
  --previews also writes the preview GIFs and scizor_frames.png
"""

import argparse
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEGA = os.path.join(ROOT, 'res/pokemon/scizor/forms/mega')
PREVIEWS = os.path.join(ROOT, 'tools/mega_sprites/previews')
FRAME = 80

HOP = 2              # whole sprite rises this far in frame 2 (front and back)


# --------------------------------------------------------------------------
# FRONT parameters (frame-1 coordinates unless noted)
# --------------------------------------------------------------------------
# Low claw: everything left of the lower-left wing lobe on rows 36-53 (the
# claw, its wrist gem and the stub of forearm that runs under the lobe).
LOW_ROWS = {36: 29, 37: 28, 38: 28, 39: 27, 40: 26, 41: 26, 42: 26, 43: 25,
            44: 24, 45: 23, 46: 23, 47: 22, 48: 23}
LOW_ROWS.update({y: 21 for y in range(49, 54)})
# Wing: the grey membrane at the upper left (flood-filled from WING_SEED,
# kept left of the head and above the shoulder) lifts up and out.
WING_SEED = (15, 16)
WING_INSIDE = lambda x, y: x <= 29 and y <= 30   # noqa: E731
WING_MOVE = (-2, -2)
FRONT_WING_VALUES = (0x9, 0xa, 0xb, 0xd)   # greys only: the 'e' beside it is the red band's outline
# Low claw: flung up and out to shoulder height.
LOW_MOVE = (-3, -7)
# Raised claw (everything right of x=53 above row 31, gem included) lifts
# rigidly; its lower blade (white pincer + teeth) is cut out first and
# pasted back lower, hinged: the heel drops BLADE_DROP, the tip part
# (x >= BLADE_HINGE_X) one more, so the jaw swings open.
CLAW_MOVE = (0, -2)
BLADE_DROP = 1
BLADE_HINGE_X = 66
# Legs: below LEG_KNEE_Y each shin steps 1 px outward (feet spread).
FRONT_LEGS = (lambda x, y: x <= 34, lambda x, y: x >= 45)
FRONT_KNEE_Y = 56


def in_blade(x, y, v):
    return ((x >= 60 and 22 <= y <= 29) or (x == 59 and 26 <= y <= 28)) \
        and v in (0x8, 0x9, 0xa, 0xb, 0xd, 0xe)


def in_claw(x, y, v):
    return x >= 53 and y <= 30 and not (y <= 19 and v in (0x9, 0xa, 0xe) and x <= 54)


# Hand edits on the composed frame 2 (final coordinates, after the hop).
FRONT_PATCH = [
    # low arm: wing's dark lower edge over the claw, upper arm, lobe edge
    (26, 23, 'eeeeeee'),
    (27, 27, 'e'),
    (28, 26, '24eeeeee'),
    (29, 26, '524'),
    (30, 25, 'e5224'),
    (31, 25, 'ee5224'),
    (31, 24, 'e'),
    (32, 24, 'eeea'),
    (33, 24, 'e'),
    (33, 25, 'eaa'),
    (34, 24, '.eaaaaa'),
    (35, 25, 'eaaaaa'),
    (36, 26, 'eaa'),
    (37, 27, 'e'),
    # raised claw: mouth interior at the hinge (dark-red inner jaw, black)
    (18, 60, '5588'),
    (19, 60, '488'),
    (20, 60, '88'),
    # knees: rejoin the outer/inner outlines where the shins step outward
    (54, 30, '24'),
    (53, 54, '24'),
]

# --------------------------------------------------------------------------
# BACK parameters
# --------------------------------------------------------------------------
LEFT_CLAW_ROWS = {45: (0, 27), 46: (0, 27), 47: (0, 28)}
LEFT_CLAW_ROWS.update({y: (0, 30) for y in range(48, 57)})
LEFT_CLAW_ROWS.update({y: (0, 27) for y in range(57, 63)})
RIGHT_CLAW_ROWS = {45: (57, 79), 46: (56, 79), 47: (56, 79)}
RIGHT_CLAW_ROWS.update({y: (55, 79) for y in range(48, 57)})
RIGHT_CLAW_ROWS.update({y: (59, 79) for y in range(57, 64)})
# Upper wings: each grey membrane (flood-filled from its seed, above the
# lower wing lobes) lifts up and out.
LEFT_WING_SEED, LEFT_WING_INSIDE = (15, 17), (lambda x, y: x <= 38 and y <= 36)
RIGHT_WING_SEED, RIGHT_WING_INSIDE = (67, 18), (lambda x, y: x >= 46 and y <= 36)
BACK_WING_MOVE = 2
# Claws: each moves rigidly up and out and is pasted BEHIND the body and
# wings (in the rear view the wings are nearest the viewer).
LEFT_MOVE = (-5, -6)
RIGHT_MOVE = (3, -6)
BACK_LEGS = (lambda x, y: x <= 38, lambda x, y: x >= 47)
BACK_KNEE_Y = 62

BACK_PATCH = [        # composed frame 2, final coordinates (after the hop)
    # left upper arm: claw wrist (24,43) down-right to the shoulder ball (32,47)
    (42, 26, '5'),
    (43, 26, '45'),
    (44, 23, '5'),
    (44, 26, '24'),
    (45, 25, '5225'),
    (46, 26, '54225'),
    (47, 28, '55425'),
    (48, 30, '5'),
    # right upper arm: claw wrist (58,43) down-left to the shoulder ball (51,47)
    (43, 57, '5'),
    (44, 56, '524'),
    (45, 56, '225'),
    (46, 55, '5245'),
    (47, 52, '52245'),
    (48, 52, '55'),
    # wing roots: restore the dark separators between the red blade-arms and
    # the flared membranes (the moved wing overwrote them)
    (32, 34, 'e'),
    (32, 49, '5e'),
    # right upper wing: outline the tail end the flare left bare
    (33, 58, 'ae'),
    (34, 57, 'ae'),
    (35, 56, 'e'),
    # left knee: rejoin the outer outline where the shin steps outward
    (59, 28, '2'),
]

# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def read_pal(path):
    lines = open(path).read().split('\n')
    return [tuple(int(c) for c in l.split()) for l in lines[3:] if l.strip()]


def load_frame1(path):
    im = Image.open(path)
    ix = Image.frombytes('L', im.size, im.tobytes())
    return im, [[ix.getpixel((x, y)) for x in range(FRAME)] for y in range(FRAME)]


def copy(f):
    return [row[:] for row in f]


def cut(f, pred):
    """Remove pixels matching pred(x, y, v) from f and return them as a layer."""
    layer = {}
    for y in range(FRAME):
        for x in range(FRAME):
            v = f[y][x]
            if v and pred(x, y, v):
                layer[(x, y)] = v
                f[y][x] = 0
    return layer


def rows_pred(rows):
    def pred(x, y, v):
        if y not in rows:
            return False
        lo, hi = rows[y] if isinstance(rows[y], tuple) else (0, rows[y])
        return lo <= x <= hi
    return pred


def moved(layer, fn):
    return {fn(x, y): v for (x, y), v in layer.items()}


def shifted(layer, dx, dy):
    return moved(layer, lambda x, y: (x + dx, y + dy))


def paste(f, layer):
    for (x, y), v in layer.items():
        f[y][x] = v


def paste_behind(f, layer):
    for (x, y), v in layer.items():
        if not f[y][x]:
            f[y][x] = v


def hop(f):
    """Raise the whole frame HOP px."""
    return [f[y + HOP][:] if y + HOP < FRAME else [0] * FRAME for y in range(FRAME)]


def apply_patch(target, patch):
    """patch rows: (y, x0, 'hex digits'); '.' clears, ' ' keeps."""
    for y, x0, s in patch:
        for i, ch in enumerate(s):
            if ch == ' ':
                continue
            target[y][x0 + i] = 0 if ch == '.' else int(ch, 16)


WING_VALUES = (0x9, 0xa, 0xb, 0xd, 0xe)   # greys and the dark outline


def wing_layer(f, seed, inside, values=WING_VALUES):
    """Flood-fill the grey wing membrane from seed, staying where inside(x, y).
    A dark 'e' pixel that touches red is the outline of the red part in front
    of the wing, not the wing's own edge, so it is left out."""
    red = (0x1, 0x2, 0x3, 0x4, 0x5, 0xc)
    todo, seen = [seed], set()
    while todo:
        x, y = todo.pop()
        if (x, y) in seen or not inside(x, y) or f[y][x] not in values:
            continue
        if f[y][x] == 0xe and any(f[y + j][x + i] in red
                                   for i, j in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            continue
        seen.add((x, y))
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return {(x, y): f[y][x] for x, y in seen}


def flare(f, wing, dx, dy):
    """Move a wing rigidly by (dx, dy) along its length.  Where it slides out
    from behind a body part, the uncovered root strip (up to max(|dx|,|dy|)
    px from the body) is filled by continuing the membrane's diagonal vein
    pattern back from the moved copy, so no gap opens at the root."""
    new = shifted(wing, dx, dy)
    for (x, y) in wing:
        f[y][x] = 0
    n = max(abs(dx), abs(dy))
    ux, uy = (dx > 0) - (dx < 0), (dy > 0) - (dy < 0)      # outward unit step
    strip = []
    for (x, y) in wing:
        if (x, y) in new:
            continue
        for k in range(1, n + 1):
            p = (x - ux * k, y - uy * k)
            if p in wing:
                continue
            if f[p[1]][p[0]]:
                strip.append((x, y))
            break
    paste(f, new)
    # fill nearest-to-the-moved-wing first, copying the outward neighbour
    for x, y in sorted(strip, key=lambda p: -(p[0] * ux + p[1] * uy)):
        v = f[y + uy][x + ux]
        f[y][x] = v if v in WING_VALUES else wing[(x, y)]


def spread_legs(f, preds, knee_y, lo_y=0):
    """Below knee_y, step each shin 1 px outward (left leg -1, right +1)."""
    for pred, dx in zip(preds, (-1, 1)):
        shin = cut(f, lambda x, y, v: y >= knee_y and pred(x, y))
        paste(f, shifted(shin, dx, 0))


# --------------------------------------------------------------------------
# FRONT
# --------------------------------------------------------------------------
def build_front(f1):
    f = copy(f1)
    flare(f, wing_layer(f, WING_SEED, WING_INSIDE, FRONT_WING_VALUES), *WING_MOVE)
    low = cut(f, rows_pred(LOW_ROWS))
    spread_legs(f, FRONT_LEGS, FRONT_KNEE_Y)
    paste(f, shifted(low, *LOW_MOVE))
    blade = cut(f, in_blade)
    claw = cut(f, in_claw)
    paste(f, shifted(claw, *CLAW_MOVE))
    paste(f, moved(blade, lambda x, y: (x, y + BLADE_DROP + (x >= BLADE_HINGE_X))))
    f = hop(f)
    apply_patch(f, FRONT_PATCH)
    return f


# --------------------------------------------------------------------------
# BACK
# --------------------------------------------------------------------------
def build_back(f1):
    f = copy(f1)
    left_wing = wing_layer(f, LEFT_WING_SEED, LEFT_WING_INSIDE)
    right_wing = wing_layer(f, RIGHT_WING_SEED, RIGHT_WING_INSIDE)
    flare(f, left_wing, -BACK_WING_MOVE, -BACK_WING_MOVE)
    flare(f, right_wing, BACK_WING_MOVE, -BACK_WING_MOVE)
    left = cut(f, rows_pred(LEFT_CLAW_ROWS))
    right = cut(f, rows_pred(RIGHT_CLAW_ROWS))
    spread_legs(f, BACK_LEGS, BACK_KNEE_Y)
    paste_behind(f, shifted(left, *LEFT_MOVE))
    paste_behind(f, shifted(right, *RIGHT_MOVE))
    f = hop(f)
    apply_patch(f, BACK_PATCH)
    return f


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
def sheet(im, frames):
    ix = Image.new('L', im.size)
    for i, fr in enumerate(frames):
        for y in range(FRAME):
            for x in range(FRAME):
                ix.putpixel((i * FRAME + x, y), fr[y][x])
    out = Image.frombytes('P', im.size, ix.tobytes())
    out.putpalette(im.getpalette())
    out.info['transparency'] = 0
    return out


def save_sheet(im, frames, path):
    sheet(im, frames).save(path, bits=4, transparency=0)


def rgb_frame(fr, pal, scale, bg):
    out = Image.new('RGB', (FRAME * scale, FRAME * scale), bg)
    d = ImageDraw.Draw(out)
    for y in range(FRAME):
        for x in range(FRAME):
            v = fr[y][x]
            if v:
                d.rectangle([x * scale, y * scale, x * scale + scale - 1, y * scale + scale - 1], fill=pal[v])
    return out


BG = (200, 208, 216)
TIMING = [(0, 300), (1, 430), (0, 1000)]


def write_gif(frames, pal, scale, path):
    imgs = [rgb_frame(frames[i], pal, scale, BG) for i, _ in TIMING]
    imgs = [i.convert('P', palette=Image.ADAPTIVE, colors=32) for i in imgs]
    imgs[0].save(path, save_all=True, append_images=imgs[1:],
                 duration=[d for _, d in TIMING], loop=0, disposal=1, optimize=False)


def check(f1_res, f1, f2, name):
    assert f1 == f1_res, f'{name}: frame 1 differs from res/'
    used = {v for row in f1 for v in row}
    extra = {v for row in f2 for v in row} - used
    assert not extra, f'{name}: frame 2 uses indices not in frame 1: {sorted(extra)}'
    border = [(x, y) for y in range(FRAME) for x in range(FRAME)
              if f2[y][x] and (x in (0, FRAME - 1) or y in (0, FRAME - 1))]
    assert not border, f'{name}: frame 2 touches the border at {border[:5]}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--install', action='store_true')
    ap.add_argument('--previews', action='store_true')
    args = ap.parse_args()
    os.makedirs(PREVIEWS, exist_ok=True)

    built = {}
    for side, build in (('front', build_front), ('back', build_back)):
        src = os.path.join(MEGA, f'{side}.png')
        im, f1 = load_frame1(src)
        f2 = build(copy(f1))
        dest = os.path.join(MEGA if args.install else PREVIEWS,
                            f'{side}.png' if args.install else f'scizor_{side}.png')
        save_sheet(im, [f1, f2], dest)
        # Re-read what was written: frame 1 must still match res/ exactly.
        _, f1_out = load_frame1(dest)
        _, f1_res = load_frame1(src) if not args.install else (None, f1)
        check(f1_res, f1_out, f2, side)
        built[side] = (f1, f2)
        diff = sum(f1[y][x] != f2[y][x] for y in range(FRAME) for x in range(FRAME))
        print(f'{side}: frame 2 differs from frame 1 in {diff} px -> {os.path.relpath(dest, ROOT)}')

    if args.previews:
        normal = read_pal(os.path.join(MEGA, 'normal.pal'))
        shiny = read_pal(os.path.join(MEGA, 'shiny.pal'))
        for side, frames in built.items():
            write_gif(frames, normal, 4, os.path.join(PREVIEWS, f'scizor_{side}.gif'))
            write_gif(frames, shiny, 4, os.path.join(PREVIEWS, f'scizor_{side}_shiny.gif'))
            write_gif(frames, normal, 1, os.path.join(PREVIEWS, f'scizor_{side}_1x.gif'))
        s = 5
        grid = Image.new('RGB', (2 * FRAME * s, 4 * FRAME * s), BG)
        r = 0
        for side in ('front', 'back'):
            for pal in (normal, shiny):
                for c in range(2):
                    grid.paste(rgb_frame(built[side][c], pal, s, BG), (c * FRAME * s, r * FRAME * s))
                r += 1
        grid.save(os.path.join(PREVIEWS, 'scizor_frames.png'))
        print('previews written to', os.path.relpath(PREVIEWS, ROOT))


if __name__ == '__main__':
    main()
