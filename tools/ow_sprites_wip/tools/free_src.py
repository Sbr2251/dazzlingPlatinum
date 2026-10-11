import sys, json, colorsys, glob, os, re
sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp/a1r3/tools')
import owlib
from owlib import *
from extract import recolor_stock
from PIL import Image, ImageChops

owlib.OUT = OUT2 = Path('/tmp/a1r3/ow_sprites_free')
S2 = Path('/tmp/a1r3/src2')
TUX = S2 / 'tuxemon/mods/tuxemon/sprites'
KIT = S2 / 'cc/pokemon png'
CANDS = []


def add(char, key, name, walk, extras=(), run=None, **meta):
    titles = {'darren_boy': 'Darren (boy)', 'darren_girl': 'Darren (girl)', 'garius': 'Garius', 'ruth': 'Ruth'}
    meta['char_title'] = titles[char]
    c = Candidate(char, key, name, walk, extras, run=run, meta=meta)
    c.process()
    owlib.OUT = OUT2
    c.write()
    CANDS.append(c)
    print(char, key, 'shift', c.dx, c.dy, 'colours', c.orig_colors, '->', len(c.pal))
    return c


def pad32(cell, ox=None, oy=None):
    o = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    if ox is None:
        ox = (32 - cell.width) // 2
    if oy is None:
        oy = 32 - cell.height - 2
    o.paste(cell, (ox, oy), cell)
    return o


def diff(a, b):
    return sum(1 for p, q in zip(a.getdata(), b.getdata()) if p != q)


def walk3(rows):
    """rows: {facing: [f0, f1, f2]} -> stand/stepA/stand/stepB, stand = the frame closest to the other two."""
    w = {}
    for fac, fr in rows.items():
        d01, d12, d02 = diff(fr[0], fr[1]), diff(fr[1], fr[2]), diff(fr[0], fr[2])
        cost = [d01 + d02, d01 + d12, d02 + d12]
        s = cost.index(min(cost))
        steps = [i for i in range(3) if i != s]
        w[fac] = [fr[s], fr[steps[0]], fr[s], fr[steps[1]]]
    return w


def sheet_rgba(path, index0_transparent=False):
    im = Image.open(path)
    if index0_transparent and im.mode == 'P':
        pal = im.getpalette()
        o = Image.new('RGBA', im.size, (0, 0, 0, 0))
        po = o.load()
        for i, v in enumerate(im.getdata()):
            if v:
                po[i % im.width, i // im.width] = (pal[3 * v], pal[3 * v + 1], pal[3 * v + 2], 255)
        return o
    return im.convert('RGBA')


def cells(img, ox, oy, pw, ph, cols, rows):
    return [[img.crop((ox + c * pw, oy + r * ph, ox + (c + 1) * pw, oy + (r + 1) * ph)) for c in range(cols)] for r in range(rows)]


# ---------------------------------------------------------------- sources

OM1 = sheet_rgba(S2 / 'openmon1_16398979.png')
OM2 = sheet_rgba(S2 / 'openmon1_16398978.png')


def despeckle(im, min_px=4):
    """Drop tiny islands (stray pixels from the source sheet), keep everything connected to the body."""
    from collections import deque
    W, H = im.size
    a = im.load()
    seen = set()
    comps = []
    for y in range(H):
        for x in range(W):
            if a[x, y][3] and (x, y) not in seen:
                q = deque([(x, y)]); seen.add((x, y)); comp = []
                while q:
                    p = q.popleft(); comp.append(p)
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            n = (p[0] + dx, p[1] + dy)
                            if 0 <= n[0] < W and 0 <= n[1] < H and n not in seen and a[n][3]:
                                seen.add(n); q.append(n)
                comps.append(comp)
    o = im.copy()
    po = o.load()
    for comp in comps:
        if len(comp) < min_px:
            for p in comp:
                po[p] = (0, 0, 0, 0)
    return o


def openmon(sheet, idx):
    """Openmon NPC set 1: 18x26 pitch, 3 frames x rows (down, left, right, up), 4 characters per band.
    Wide hair can spill past the 18 px pitch, so each frame is cut between the midpoints of its neighbours' centroids."""
    band, col = divmod(idx, 4)
    order = ['down', 'left', 'right', 'up']
    rows = {}
    a = sheet.getchannel('A')
    for r in range(4):
        y0 = band * 104 + r * 26
        cents = []
        for k in range(12):
            xs = [x for x in range(k * 18, k * 18 + 18) for y in range(y0, y0 + 26) if a.getpixel((x, y))]
            cents.append(sum(xs) / len(xs) if xs else k * 18 + 9)
        fr = []
        for k in range(col * 3, col * 3 + 3):
            lo = int(round((cents[k - 1] + cents[k]) / 2)) if k > 0 else max(0, int(cents[k]) - 13)
            hi = int(round((cents[k] + cents[k + 1]) / 2)) if k < 11 else min(sheet.width, int(cents[k]) + 14)
            c = sheet.crop((lo, y0, hi, y0 + 26))
            o = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
            o.paste(c, (16 - int(round(cents[k] - lo)), 4), c)
            fr.append(despeckle(o))
        rows[order[r]] = fr
    return walk3(rows)


def tux(name):
    im = sheet_rgba(TUX / f'{name}.png')
    cs = cells(im, 0, 0, 16, 32, 3, 4)
    order = ['down', 'left', 'right', 'up']
    return walk3({order[r]: [pad32(c, 8, 0) for c in cs[r]] for r in range(4)})


def cabbit(path):
    im = sheet_rgba(path, index0_transparent=True)
    cs = cells(im, 0, 0, 24, 32, 3, 4)
    order = ['up', 'right', 'down', 'left']
    return walk3({order[r]: [pad32(c, 4, 0) for c in cs[r]] for r in range(4)})


def kit_find(mode, sub, *words):
    base = KIT / f'overworld {mode}'
    cands = sorted(glob.glob(str(base / sub / '**' / '*.png'), recursive=True))
    for f in cands:
        n = os.path.relpath(f, base / sub).lower()
        if all(w.lower() in n for w in words):
            return f
    raise FileNotFoundError((mode, sub, words, [os.path.basename(c) for c in cands][:20]))


def kit_compose(mode, layers):
    out = None
    for sub, words in layers:
        im = Image.open(kit_find(mode, sub, *words)).convert('RGBA')
        out = im if out is None else Image.alpha_composite(out, im)
    # the kit is drawn at Essentials' 2px density: every pixel is a 2x2 block
    return out.resize((out.width // 2, out.height // 2), Image.NEAREST)


def kit_walk(img):
    """Essentials charset: 4x4 cells of 64x64, rows down/left/right/up, cols stand/step/stand/step."""
    cw = img.width // 4
    ch = img.height // 4
    # union bbox of all cells
    xs0, ys0, xs1, ys1 = 99, 99, 0, 0
    for r in range(4):
        for c in range(4):
            b = img.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)).getchannel('A').getbbox()
            if b:
                xs0, ys0, xs1, ys1 = min(xs0, b[0]), min(ys0, b[1]), max(xs1, b[2]), max(ys1, b[3])
    cx = (xs0 + xs1) // 2
    x0 = cx - 16
    y0 = ys1 - 30
    order = ['down', 'left', 'right', 'up']
    w = {}
    for r in range(4):
        w[order[r]] = [img.crop((c * cw + x0, r * ch + y0, c * cw + x0 + 32, r * ch + y0 + 32)) for c in range(4)]
    return w, (xs1 - xs0, ys1 - ys0)


def hsv_map(walk, fn):
    out = {}
    for f, frames in walk.items():
        out[f] = []
        for im in frames:
            o = im.copy()
            px = o.load()
            for y in range(o.height):
                for x in range(o.width):
                    p = px[x, y]
                    if p[3]:
                        r, g, b = p[:3]
                        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                        h, s, v = fn(h * 360, s, v)
                        px[x, y] = tuple(int(round(t * 255)) for t in colorsys.hsv_to_rgb(h / 360 % 1, max(0, min(1, s)), max(0, min(1, v)))) + (255,)
            out[f].append(o)
    return out
