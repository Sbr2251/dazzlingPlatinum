#!/usr/bin/env python3
"""Mega Garchomp cry frame 2 (front "rear-up roar", back "lunge and flare").

Frame 2 is rebuilt from the real frame 1 (res/pokemon/garchomp/forms/mega)
every run; the existing frame 2 in res/ is ignored.

Method: NO rotation or resampling.  Every moving part is cut out of frame 1
with a hand-drawn mask and moved by whole pixels, so every part keeps frame
1's exact pixels, size and shading.  Gaps that a move opens are closed by
repainting a thin slice of frame 1 at in-between offsets (a stair-stepped
extension of the limb itself) or by one plain frame-1 row, and every seam is
then hand-cleaned with the pixel patches below.

usage: animate_garchomp_cry.py [--install] [--previews]
  default     write tools/mega_sprites/previews/garchomp_{front,back}.png
  --install   write res/pokemon/garchomp/forms/mega/{front,back}.png instead
  --previews  also write the preview GIFs and garchomp_frames.png
"""

import argparse
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEGA = os.path.join(ROOT, 'res/pokemon/garchomp/forms/mega')
PREVIEWS = os.path.join(ROOT, 'tools/mega_sprites/previews')
F = 80
BG = (200, 208, 216)
GIF_DURATIONS = [300, 430, 1000]

# Palette: 1-5 navy (dark..light), 6/7/8 red (dark..light), 9/A yellow,
# B white, C light grey, D outline, E maroon, F grey-blue.
#
# PARTS: (name, dx, dy, regions).  Every opaque frame-1 pixel goes to the
# first part whose regions contain it; the last part should be a catch-all.
#   region ('rows', y0, y1, x0, x1): rows y0..y1, cols x0..x1 inclusive
#   region ('px', [(x, y), ...]):     explicit pixels
# OPS, painted in order (later on top):
#   ('part', name)                         the part at its offset
#   ('copy', part, regions, [(dx, dy)..])  a slice of a part (frame-1
#        coordinates) repainted at each listed offset: joins and fillers
# PATCHES: (x, y, rows) in frame-2 coordinates; a hex digit is a palette
# index, '.' is transparent, ' ' leaves the pixel as it is.

# ---------------------------------------------------------------- FRONT ----
FRONT_PARTS = [
    ('larm', 0, -3, [('rows', 20, 30, 0, 24), ('rows', 31, 32, 0, 31),
                     ('rows', 33, 33, 0, 30), ('rows', 34, 38, 0, 29),
                     ('rows', 39, 52, 0, 20)]),
    ('uarm', 2, -3, [('rows', 19, 23, 48, 53), ('rows', 24, 24, 48, 52)]),
    ('rarm', 2, -3, [('rows', 17, 21, 51, 79), ('rows', 22, 26, 52, 79),
                     ('rows', 27, 27, 51, 79), ('rows', 28, 30, 50, 79),
                     ('rows', 31, 31, 49, 79), ('rows', 32, 34, 48, 79),
                     ('rows', 35, 45, 47, 59), ('rows', 46, 47, 48, 50),
                     ('rows', 48, 48, 48, 49)]),
    ('head', 0, -3, [('rows', 0, 17, 0, 79)]),
    ('jaw', -1, 0, [('rows', 18, 19, 33, 40), ('rows', 20, 22, 31, 39),
                    ('rows', 23, 23, 33, 35)]),
    ('upper', 0, -1, [('rows', 0, 62, 0, 79)]),
    ('feet', 0, 0, [('rows', 63, 79, 0, 79)]),
]
FRONT_OPS = [
    ('part', 'feet'),
    ('copy', 'upper', [('rows', 62, 62, 0, 79)], [(0, 0)]),       # shins +1
    ('part', 'upper'),
    ('copy', 'upper', [('rows', 18, 18, 40, 46)], [(0, -2), (0, -3)]),  # neck
    ('part', 'jaw'),
    ('part', 'head'),
    ('copy', 'uarm', [('rows', 0, 79, 0, 79)], [(0, -1), (1, -2)]),
    ('part', 'uarm'),
    ('part', 'rarm'),
    ('part', 'larm'),
]
FRONT_PATCHES = [
    # open mouth, 3 rows (head up 2 on the body, lower jaw down 1 and 1 px
    # forward).  Roof: maroon with the upper fang C hanging from frame 1's
    # grey tooth F.  Middle: a maroon cavity that only darkens (D) at the
    # back of the throat.  Floor: maroon with the lower fang C standing on
    # the jaw's own grey tooth F.
    (32, 15, ["DEECEEEDD",
              "..DEEEEDD",
              ".DEECEEDD"]),
    # cheek column the lower jaw vacated when it swung forward 1 px
    (40, 18, ["1"]),
    (39, 20, ["1", "1"]),
    # right upper arm, raised: its top edge keeps frame 1's rhythm (outline
    # pixel, two highlight pixels, one row up) from the shoulder to the bar
    (47, 19, ["  D11",
              "D11  "]),
    # right armpit.  The blade keeps every frame-1 pixel; only pixels LEFT
    # of it are painted.  Maroon rim E on the blade's inner edge where frame
    # 1's blade had none (it lay on the chest), the chest's own D outline
    # beside it, and from row 31 down the armpit window opens between them
    # (3 px wide lower down, 1 px more than frame 1 because the wing is
    # spread 2 px).
    (53, 23, ["E"]),
    (52, 24, ["E"]),
    (50, 26, ["1E"]),
    (50, 27, ["DE"]),
    (50, 28, ["E"]),
    (49, 30, ["D"]),
    (48, 31, ["D"]),
    # blade tip hangs clear of the thigh: maroon inner edge, capped point
    (49, 42, ["E"]),
    (50, 43, ["E"]),
    (51, 45, ["D"]),
    # right thigh the blade used to cover: rounded outline, dark rim inside
    (47, 43, ["D"]),
    (47, 44, ["D"]),
    (48, 45, ["D"]),
    (47, 46, ["2D"]),
    (48, 47, ["2D"]),
    # left arm raised 2 on the shoulder: the upper arm's lower rows ride up
    # with the hand, so the V between shoulder and wing keeps its shape and
    # its claws.  Clean the upper arm's left edge into a diagonal, and close
    # the chest outline beside the hand.
    (27, 28, [".D"]),
    (32, 29, ["E"]),
    (31, 30, ["E"]),
    (31, 31, ["EE"]),
    # left shin gets 1 row (feet planted, body up 1): an in-between row so
    # the shin's inner highlight is not doubled
    (24, 61, ["D111221D"]),
]


# ----------------------------------------------------------------- BACK ----
BACK_PARTS = [
    # head moves as ONE piece, including the on-model red mouth at x43-46
    ('head', 1, -3, [('rows', 13, 13, 29, 51), ('rows', 14, 21, 29, 52),
                     ('rows', 22, 22, 35, 42), ('rows', 22, 25, 43, 46),
                     ('rows', 26, 26, 43, 45)]),
    # arm bars (forearms between blade and shoulder), split in 1-2 row bands
    # at in-between offsets so they lean evenly (1 px across per 2 rows)
    # instead of stretching
    ('lbar_a', -4, -3, [('rows', 22, 23, 21, 27)]),
    ('lbar_b', -3, -3, [('rows', 24, 25, 21, 27)]),
    ('lbar_c', 0, -2, [('rows', 26, 28, 21, 27)]),
    ('rbar_a', 4, -3, [('rows', 21, 22, 53, 58)]),
    ('rbar_b', 3, -3, [('rows', 23, 24, 53, 58)]),
    ('rbar_c', 2, -2, [('rows', 25, 25, 53, 58)]),
    ('rbar_d', 1, -2, [('rows', 26, 28, 53, 58)]),
    # blades flare up and out
    ('lblade', -4, -3, [('rows', 0, 12, 0, 31), ('rows', 13, 21, 0, 28), ('rows', 22, 31, 0, 20)]),
    ('rblade', 4, -3, [('rows', 0, 12, 50, 79), ('rows', 13, 20, 52, 79), ('rows', 21, 31, 59, 79)]),
    # body: shoulders/neck base up 2, mid-back up 1, legs+tail planted
    ('back', 1, -2, [('rows', 0, 30, 0, 79)]),
    ('mid', 1, -1, [('rows', 31, 35, 0, 79)]),
    ('lower', 0, 0, [('rows', 36, 79, 0, 79)]),
]
BACK_OPS = [
    ('part', 'lower'),
    ('copy', 'mid', [('rows', 35, 35, 0, 79)], [(0, 0)]),      # waist +1
    ('part', 'mid'),
    ('copy', 'back', [('rows', 30, 30, 0, 79)], [(1, -1)]),     # upper back +1
    ('part', 'back'),
    ('copy', 'back', [('rows', 23, 23, 35, 42)], [(1, -3)]),  # one collar neck row
    ('part', 'head'),
    # each bar +1 row: its plain row once more, one step further along the
    # lean (left: 'D23D', exactly as frame 1 stacks 'D23D' over '1242';
    # right: 'D31D' over '241D')
    ('copy', 'lbar_b', [('rows', 25, 25, 0, 79)], [(-2, -2)]),
    ('part', 'lbar_c'), ('part', 'lbar_b'), ('part', 'lbar_a'),
    ('copy', 'rbar_b', [('rows', 24, 24, 0, 79)], [(2, -2)]),
    ('part', 'rbar_d'), ('part', 'rbar_c'), ('part', 'rbar_b'), ('part', 'rbar_a'),
    ('part', 'lblade'), ('part', 'rblade'),
]
BACK_PATCHES = [
    # The head rises 1 row more than the shoulders, so the neck gets one
    # more row.  The whole red throat stripe (frame 1's 'E751/E6C4/D77E/E76/
    # DEE', rows 22-26) rides up with the head, unchanged and unbroken; the
    # new neck row opens between the stripe's end and the shoulder outline
    # and is filled with plain neck navy, keeping frame 1's D over the notch
    # at the neck's corner.
    (44, 24, ["D11"]),
    # left bar: outline under the in-between 'D23D' row so the bar's left
    # edge runs x20, x21, x22 and then straight down into the shoulder
    (22, 24, ["D"]),
    # upper-back cut (+1 row): the 45-degree side edges would step twice at
    # rows 28-29; pull row 29 in by 1 on the left, and rows 29-30 in by 1 on
    # the right so that edge keeps a clean 1:1 diagonal.  The internal
    # crease pixel D at x30 is not doubled.
    (25, 29, [".12322"]),
    (53, 29, ["321D."]),
    (52, 30, ["221D."]),
]


# --------------------------------------------------------------- helpers ----

def load(side):
    im = Image.open(os.path.join(MEGA, side + '.png'))
    ix = np.array(Image.frombytes('L', im.size, im.tobytes()), dtype=np.uint8)
    return im, ix[:, :F].copy()


def region_mask(regions):
    m = np.zeros((F, F), dtype=bool)
    for r in regions:
        if r[0] == 'rows':
            _, y0, y1, x0, x1 = r
            m[y0:y1 + 1, x0:x1 + 1] = True
        else:
            for x, y in r[1]:
                m[y, x] = True
    return m


def shift(layer, dx, dy):
    out = np.zeros_like(layer)
    ys, xs = np.nonzero(layer)
    nx, ny = xs + dx, ys + dy
    ok = (nx >= 0) & (nx < F) & (ny >= 0) & (ny < F)
    out[ny[ok], nx[ok]] = layer[ys[ok], xs[ok]]
    return out


def over(base, layer):
    out = base.copy()
    out[layer != 0] = layer[layer != 0]
    return out


def patch(a, x0, y0, rows):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != ' ':
                a[y0 + j, x0 + i] = 0 if ch == '.' else int(ch, 16)


def compose(f1, parts, ops, patches):
    free = f1 > 0
    layers, offs = {}, {}
    for name, dx, dy, regions in parts:
        m = region_mask(regions) & free
        free &= ~m
        layers[name] = np.where(m, f1, 0).astype(np.uint8)
        offs[name] = (dx, dy)
    assert not free.any(), 'unassigned frame-1 pixels'
    out = np.zeros_like(f1)
    for op in ops:
        if op[0] == 'part':
            out = over(out, shift(layers[op[1]], *offs[op[1]]))
        else:
            _, part, regions, steps = op
            sl = np.where(region_mask(regions), layers[part], 0).astype(np.uint8)
            for dx, dy in steps:
                out = over(out, shift(sl, dx, dy))
    for x, y, rows in patches:
        patch(out, x, y, rows)
    return out


def front_frame2(f1):
    return compose(f1, FRONT_PARTS, FRONT_OPS, FRONT_PATCHES)


def back_frame2(f1):
    return compose(f1, BACK_PARTS, BACK_OPS, BACK_PATCHES)


# ---------------------------------------------------------------- output ----

def check(im, f1, f2):
    real = np.array(Image.frombytes('L', im.size, im.tobytes()), dtype=np.uint8)
    assert (f1 == real[:, :F]).all(), 'frame 1 changed'
    extra = set(np.unique(f2).tolist()) - set(np.unique(f1).tolist())
    assert not extra, 'frame 2 uses new indices %s' % extra
    assert not (f2[0].any() or f2[-1].any() or f2[:, 0].any() or f2[:, -1].any()), \
        'frame 2 touches the border'
    assert not (f2[1].any() or f2[-2].any() or f2[:, 1].any() or f2[:, -2].any()), \
        'frame 2 art within 1 px of the edge'


def save_sheet(im, f1, f2, path):
    sheet = np.hstack([f1, f2]).astype(np.uint8)
    out = Image.frombytes('P', im.size, sheet.tobytes())
    out.putpalette(im.getpalette())
    out.save(path, bits=4, transparency=0)


def read_pal(name):
    with open(os.path.join(MEGA, name)) as fh:
        vals = [int(v) for v in fh.read().split()[3:3 + 48]]
    return [tuple(vals[k:k + 3]) for k in range(0, 48, 3)]


def render(g, pal, scale, bg):
    rgb = np.array([bg] + pal[1:16], dtype=np.uint8)[g]
    out = Image.fromarray(rgb, 'RGB')
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
        im, f1 = load(side)
        f2 = build(f1)
        check(im, f1, f2)
        frames[side] = (f1, f2)
        dest = (os.path.join(MEGA, side + '.png') if args.install
                else os.path.join(PREVIEWS, 'garchomp_%s.png' % side))
        save_sheet(im, f1, f2, dest)
        print('wrote', os.path.relpath(dest, ROOT))
    if not args.previews:
        return
    for side, (f1, f2) in frames.items():
        base = os.path.join(PREVIEWS, 'garchomp_' + side)
        write_gif(f1, f2, pals['normal'], 4, base + '.gif')
        write_gif(f1, f2, pals['shiny'], 4, base + '_shiny.gif')
        write_gif(f1, f2, pals['normal'], 1, base + '_1x.gif')
    sheet = Image.new('RGB', (2 * F * 5, 4 * F * 5), BG)
    for r, (side, pal) in enumerate((('front', 'normal'), ('front', 'shiny'),
                                     ('back', 'normal'), ('back', 'shiny'))):
        for c, g in enumerate(frames[side]):
            sheet.paste(render(g, pals[pal], 5, BG), (c * F * 5, r * F * 5))
    sheet.save(os.path.join(PREVIEWS, 'garchomp_frames.png'))
    print('wrote GIFs and garchomp_frames.png')


if __name__ == '__main__':
    main()
