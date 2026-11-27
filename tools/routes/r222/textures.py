#!/usr/bin/env python3
"""Route 222 (Violet-Lit Coast) texture set: map_texture_set_081 = stock map_texture_set_018 + three pixel-art
atlases, generated from math (NumPy), quantised onto hand-tuned 16-colour BGR555 palettes with a 4x4 Bayer ordered
dither at Platinum's 16 texels per tile. All three use c0 = 1 (palette index 0 transparent) so props cut out cleanly.

Usage:
  ~/.venvs/desmume/bin/python tools/routes/r222/textures.py                dry run: table, VRAM, round-trip checks
  ~/.venvs/desmume/bin/python tools/routes/r222/textures.py --preview DIR  also DIR/<texture>.png (and x8 copies)
  ~/.venvs/desmume/bin/python tools/routes/r222/textures.py --write        write SET_REL (refuses if a check fails)

Idempotent: the base is always stock set 018 read from git (BASE_REV:BASE_SET_REL, the routes-wave2 contract commit),
never the work tree, so reruns never append twice; stock textures and palettes keep their names, texels and colours
(asserted). build_art.py drives this module (build_set()) and binds the materials.

Textures (pltt16, c0 = 1):
  r222_lamp     64x32  blacked-out coastal streetlamp atlas: LAMP_UV regions = violet spark halo (32x32, used as a
                       translucent card and ground glow), riveted black-iron post strip, dead housing (cracked dark
                       glass, a faint violet filament), violet-lit housing (sparking filament), cap, base plinth
  r222_tide     64x64  violet shoreline atlas: TIDE_UV regions = lacy violet-tinted tide foam band (64 wide, tiles
                       along u every 4 tiles), washed-up shard / shell scatter band (64 wide), two upright sea-rift
                       crystal cluster cards, two tangled kelp clumps, bleached driftwood log, crystal prism facets,
                       loose kelp strand, a fan of broken shards
  r222_warning  32x32  power-outage kit: WARN_UV regions = torn yellow/black caution tape (tiles along u), beacon box
                       front (hazard band + lightning triangle), side (vents + rust), lid, dead amber beacon dome
"""
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import nsbtx  # noqa: E402

SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_081.nsbtx"
BASE_REV = "406c75f6a8"           # routes-wave2 contract commit (set 081 == stock 018 there)
BASE_SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_018.nsbtx"
VRAM_TARGET = 160 * 1024          # PLAN goal
NAME_MAX = 15

BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], float) + 0.5) / 16.0 - 0.5
TAU = 2 * np.pi

# atlas regions (x0, y0, x1, y1) in texels, exclusive ends
LAMP_UV = {"halo": (0, 0, 32, 32), "post": (32, 0, 40, 32), "dead": (40, 0, 56, 16), "lit": (40, 16, 56, 32),
           "cap": (56, 0, 64, 16), "base": (56, 16, 64, 32)}
TIDE_UV = {"foam": (0, 0, 64, 16), "scatter": (0, 16, 64, 32), "crystal": (0, 32, 16, 48), "kelp": (16, 32, 32, 48),
           "prism": (32, 32, 48, 40), "strand": (48, 32, 64, 40), "drift": (32, 40, 64, 48),
           "crystal2": (0, 48, 16, 64), "kelp2": (16, 48, 32, 64), "shards": (32, 48, 64, 64)}
WARN_UV = {"tape": (0, 0, 32, 8), "front": (0, 8, 16, 24), "side": (16, 8, 32, 24), "lid": (0, 24, 16, 32),
           "dome": (16, 24, 32, 32)}
SIZES = {"r222_lamp": (64, 32), "r222_tide": (64, 64), "r222_warning": (32, 32)}


def bayer(h, w):
    y, x = np.mgrid[0:h, 0:w]
    return BAYER4[y % 4, x % 4]


def ramp(t, idx, dither=1.0):
    """t in [0, 1] (array) -> palette index along `idx`, Bayer-dithered between neighbouring entries."""
    t = np.asarray(t, float)
    n = len(idx)
    v = np.clip(np.floor(np.clip(t, 0, 1) * (n - 1) + 0.5 + bayer(*t.shape) * dither), 0, n - 1).astype(int)
    return np.array(idx)[v]


def vnoise(h, w, cells, seed, wrap_x=True):
    """Value noise in [0, 1) over an h x w region, periodic in x (so bands tile along u)."""
    rng = np.random.RandomState(seed)
    cy = max(1, int(round(cells * h / w)))
    g = rng.rand(cy + 1, cells + 1)
    if wrap_x:
        g[:, -1] = g[:, 0]
    y, x = np.mgrid[0:h, 0:w].astype(float)
    fx, fy = x * cells / w, y * cy / h
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - x0, fy - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a = g[y0, x0] * (1 - tx) + g[y0, x0 + 1] * tx
    b = g[y0 + 1, x0] * (1 - tx) + g[y0 + 1, x0 + 1] * tx
    return a * (1 - ty) + b * ty


def snap(c):
    return tuple(int(v) >> 3 << 3 for v in c)


def line(img, x0, y0, x1, y1, v, mask=None):
    """Bresenham line of index v (clipped)."""
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    h, w = img.shape
    while True:
        if 0 <= x0 < w and 0 <= y0 < h and (mask is None or mask[y0, x0]):
            img[y0, x0] = v
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


# ---------------------------------------------------------------------------------------------------------------
# r222_lamp
# ---------------------------------------------------------------------------------------------------------------

LAMP_PAL = [
    (255, 0, 255),     # 0 transparent
    (12, 10, 18),      # 1 near-black outline
    (26, 24, 34),      # 2 dark iron
    (40, 38, 50),      # 3 iron mid
    (60, 58, 72),      # 4 iron light
    (88, 86, 102),     # 5 iron edge glint
    (24, 30, 44),      # 6 dead glass deep
    (42, 52, 72),      # 7 dead glass
    (88, 102, 128),    # 8 glass reflection streak
    (56, 30, 92),      # 9 dim violet filament
    (100, 54, 158),    # 10 violet
    (152, 92, 220),    # 11 bright violet
    (206, 164, 250),   # 12 pale violet
    (248, 236, 255),   # 13 white-violet spark core
    (74, 58, 46),      # 14 rust bronze
    (118, 120, 136),   # 15 crack line / pale glass edge
]


def lamp_halo():
    n = 32
    y, x = np.mgrid[0:n, 0:n].astype(float) + 0.5
    dx, dy = x - 16, y - 16
    r = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)
    wob = 1.0 + 0.10 * np.sin(5 * ang + 0.7) + 0.06 * np.sin(11 * ang)
    t = np.clip(1 - r / (15.0 * wob), 0, 1) ** 1.25
    # bright ramp only: on the DS a translucent halo can only blend, so a dark rim would darken the ground under it
    img = ramp(t, [0, 11, 11, 12, 12, 13], dither=1.1)
    img = np.where(t <= 0.02, 0, img)
    # crackling spark rays: jagged lines from the core
    rng = np.random.RandomState(222)
    for k in range(7):
        a = rng.uniform(0, TAU)
        L = rng.uniform(9, 15)
        px, py = 16.0, 16.0
        segs = 4
        for s in range(segs):
            a2 = a + rng.uniform(-0.6, 0.6)
            nx, ny = px + np.cos(a2) * L / segs, py + np.sin(a2) * L / segs
            line(img, px, py, nx, ny, 13 if s < 2 else 12)
            px, py = nx, ny
    img[14:18, 14:18] = 13
    return img


def lamp_post():
    w, h = 8, 32
    cols = np.array([1, 2, 4, 5, 4, 3, 2, 1])
    img = np.tile(cols, (h, 1))
    nz = vnoise(h, w, 2, 7)
    img = np.where((nz > 0.78) & (cols >= 3), 14, img)          # rust specks
    for yb in (0, 15, 16):                                      # collar band with rivets
        img[yb, 1:7] = 3
    img[0, :] = 1
    img[15, 2] = img[15, 5] = 5
    return img


def lamp_housing(lit):
    n = 16
    img = np.zeros((n, n), int)
    y, x = np.mgrid[0:n, 0:n].astype(float) + 0.5
    if lit:
        r = np.hypot(x - 8, y - 9) / 7.5
        img = ramp(np.clip(1 - r, 0, 1) ** 0.9, [9, 10, 11, 12, 13], dither=1.0)
    else:
        t = 0.35 + 0.5 * vnoise(n, n, 3, 31) - 0.25 * (y / n)
        img = ramp(t, [6, 6, 7, 7], dither=1.0)
        # glass reflection streak (diagonal)
        streak = np.abs((x - y * 0.6) - 4.5) < 0.9
        img = np.where(streak, 8, img)
    # cracks from the upper-right
    for (ax, ay, bx, by) in ((12, 3, 9, 7), (9, 7, 10, 11), (9, 7, 6, 8), (6, 8, 4, 12)):
        line(img, ax, ay, bx, by, 15 if not lit else 12)
    # filament zigzag
    fil = [(6, 10), (7, 8), (8, 10), (9, 8), (10, 10)]
    for (ax, ay), (bx, by) in zip(fil, fil[1:]):
        line(img, ax, ay, bx, by, 13 if lit else 9)
    if not lit:
        img[8, 7] = 10          # faint spark glint
        img[10, 9] = 10
    # cage frame: outline + iron border + centre mullion
    img[:, 0] = img[:, 15] = 1
    img[0, :] = img[15, :] = 1
    img[1, 1:15] = 4
    img[14, 1:15] = 3
    img[1:15, 1] = 3
    img[1:15, 14] = 2
    img[2:14, 7] = np.where(img[2:14, 7] >= 9, img[2:14, 7], 3) if lit else 3
    return img


def lamp_cap():
    w, h = 8, 16
    y = np.mgrid[0:h, 0:w][0].astype(float)
    img = ramp(1 - y / (h - 1), [2, 3, 4], dither=1.0)
    img[:, 0] = img[:, 7] = 1
    img[0, :] = 1
    img[13, 1:7] = 5
    img[14:, :] = 1
    return img


def lamp_base():
    w, h = 8, 16
    y, x = np.mgrid[0:h, 0:w].astype(float)
    img = ramp(0.6 - 0.4 * (y / h) + 0.15 * vnoise(h, w, 2, 5), [2, 3, 4], dither=1.0)
    img = np.where(vnoise(h, w, 3, 9) > 0.75, 14, img)
    img[0, :] = 5
    img[:, 0] = img[:, 7] = 1
    img[h - 1, :] = 1
    img[3, 2] = img[3, 5] = 5
    img[12, 2] = img[12, 5] = 5
    return img


def tex_lamp():
    img = np.zeros((32, 64), int)
    img[0:32, 0:32] = lamp_halo()
    img[0:32, 32:40] = lamp_post()
    img[0:16, 40:56] = lamp_housing(False)
    img[16:32, 40:56] = lamp_housing(True)
    img[0:16, 56:64] = lamp_cap()
    img[16:32, 56:64] = lamp_base()
    return img, LAMP_PAL


# ---------------------------------------------------------------------------------------------------------------
# r222_tide
# ---------------------------------------------------------------------------------------------------------------

TIDE_PAL = [
    (255, 0, 255),     # 0 transparent
    (234, 228, 250),   # 1 foam white-lilac
    (198, 182, 238),   # 2 foam lilac
    (152, 130, 212),   # 3 foam violet shadow
    (104, 86, 170),    # 4 deep violet foam edge
    (70, 52, 120),     # 5 crystal deep
    (130, 80, 202),    # 6 crystal violet
    (188, 132, 248),   # 7 crystal light
    (242, 216, 255),   # 8 crystal glint
    (30, 58, 46),      # 9 kelp dark
    (48, 94, 62),      # 10 kelp mid
    (86, 134, 80),     # 11 kelp light
    (90, 70, 54),      # 12 driftwood dark
    (140, 112, 84),    # 13 driftwood mid
    (192, 166, 130),   # 14 driftwood bleached
    (70, 156, 196),    # 15 cyan rift glint
]


def tide_foam():
    """64 x 16 (4 tiles), tiles along u. v 0 = landward edge (sparse droplets), v ~0.45 = the scalloped wash
    line, v 1 = seaward (dense lace over the stock shoreline slope)."""
    w, h = 64, 16
    y, x = np.mgrid[0:h, 0:w].astype(float) + 0.5
    edge = 6.5 + 1.6 * np.sin(x * TAU / w * 3 + 0.4) + 0.9 * np.sin(x * TAU / w * 7 + 1.3)
    lace = vnoise(h, w, 16, 41) * 0.6 + vnoise(h, w, 32, 43) * 0.4
    img = np.zeros((h, w), int)
    d = y - edge                                   # >0 seaward of the wash line
    band = np.abs(d) < 1.1
    img = np.where(band, ramp(0.6 + 0.4 * lace, [2, 1], dither=1.0), img)
    img = np.where((d >= -2.2) & (d < -1.1), np.where(lace > 0.55, 3, 0), img)    # wet violet rim landward
    sea = d >= 1.1
    holes = lace + 0.18 * np.sin(x * 1.7 + y * 2.3)
    img = np.where(sea & (holes > 0.62 - 0.02 * d), ramp(np.clip(holes, 0, 1), [4, 3, 2, 1], dither=1.0), img)
    drops = (d < -2.2) & (vnoise(h, w, 32, 47) > 0.80)
    img = np.where(drops, 3, img)
    return img


def tide_scatter():
    """64 x 16, tiles along u: washed-up violet shard chips, cyan glints, pale shells, damp kelp bits."""
    w, h = 64, 16
    img = np.zeros((h, w), int)
    rng = np.random.RandomState(2220)
    for _ in range(16):                       # shard chips: tiny diamonds
        cx, cy = rng.randint(1, w - 1), rng.randint(2, h - 2)
        col = rng.choice([6, 7, 5])
        img[cy, cx] = 8
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            img[cy + dy, (cx + dx) % w] = col
        if rng.rand() < 0.5:
            img[cy + 1, (cx + 1) % w] = 15
    for _ in range(9):                       # shells
        cx, cy = rng.randint(0, w), rng.randint(1, h - 1)
        img[cy, cx] = 14
        img[cy, (cx + 1) % w] = 13
    for _ in range(7):                       # kelp bits
        cx, cy = rng.randint(0, w), rng.randint(1, h - 2)
        img[cy, cx] = 10
        img[cy + 1, (cx + 1) % w] = 9
    return img


def tide_crystal(shards=((7.5, 1.0, 3.2, -0.10), (3.5, 6.0, 2.2, -0.35), (11.8, 4.5, 2.4, 0.30))):
    """16 x 16 upright sea-rift crystal cluster, bottom row = the sand / rock line."""
    n = 16
    img = np.zeros((n, n), int)
    y, x = np.mgrid[0:n, 0:n].astype(float) + 0.5
    for (cx, top, hw, tilt) in shards:
        u = (x - cx) - tilt * (n - y)
        inside = (np.abs(u) < hw * np.clip((y - top) / 3.0, 0, 1)) & (y > top) & (y < n - 0.5)
        shade = np.where(u < -0.3 * hw, 7, np.where(u > 0.35 * hw, 5, 6))
        img = np.where(inside, shade, img)
        edge = inside & (np.abs(u + 0.1) < 0.6)
        img = np.where(edge, 8, img)
    img[n - 1, :] = np.where(img[n - 2, :] > 0, 4, 0)
    img[3, 7] = img[7, 3] = 8
    img[5, 12] = 15
    return img


def tide_kelp(seed=73):
    n = 16
    img = np.zeros((n, n), int)
    rng = np.random.RandomState(seed)
    for k in range(6):
        a = rng.uniform(0, TAU)
        px, py = 8 + rng.uniform(-2, 2), 8 + rng.uniform(-2, 2)
        for s in range(6):
            a += rng.uniform(-0.9, 0.9)
            nx, ny = px + np.cos(a) * 1.6, py + np.sin(a) * 1.6
            line(img, px, py, nx, ny, [9, 10, 11][(k + s) % 3])
            px, py = np.clip(nx, 1, 14), np.clip(ny, 1, 14)
    img[7, 8] = img[9, 6] = 15             # a shard snagged in the tangle
    img[8, 7] = 7
    return img


def tide_drift():
    w, h = 32, 8
    y, x = np.mgrid[0:h, 0:w].astype(float) + 0.5
    prof = np.abs(y - 4.0) / 3.2
    log = (prof < 1.0) & (x > 1.5 + 1.2 * np.abs(y - 4)) & (x < 30.5 - 0.8 * np.abs(y - 4))
    grain = 0.55 - 0.45 * prof + 0.18 * np.sin(x * 0.9 + y * 0.4) * (1 - prof)
    img = np.where(log, ramp(grain, [12, 13, 14], dither=1.0), 0)
    img = np.where(log & (prof > 0.8), 12, img)
    img[3, 9] = img[4, 10] = 12            # knot
    img[2, 21] = img[5, 22] = 12
    img[1, 24:27] = 0
    return img


def tide_prism():
    w, h = 16, 8
    y, x = np.mgrid[0:h, 0:w].astype(float) + 0.5
    facet = (np.floor(x / 4) % 4)
    t = np.choose(facet.astype(int), [0.85, 0.55, 0.35, 0.6]) - 0.25 * y / h
    img = ramp(t, [5, 6, 7, 8], dither=1.0)
    img = np.where((x % 4) < 0.9, 8, img)
    img[0, :] = 8
    return img


def tide_strand():
    w, h = 16, 8
    img = np.zeros((h, w), int)
    pts = [(0, 5), (3, 3), (6, 4), (9, 2), (12, 4), (15, 3)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        line(img, ax, ay, bx, by, 10)
        line(img, ax, ay + 1, bx, by + 1, 9)
    img[2, 9] = 11
    img[3, 4] = 11
    img[5, 12] = 7
    return img


def tide_shards():
    """32 x 16 flat pile of broken rift shards washed up in a fan of violet-wet sand."""
    w, h = 32, 16
    y, x = np.mgrid[0:h, 0:w].astype(float) + 0.5
    r = np.hypot((x - 16) / 14.0, (y - 8) / 6.5)
    img = np.where(r < 1.0, np.where(vnoise(h, w, 8, 97) > 0.45, 4, 0), 0)
    rng = np.random.RandomState(4242)
    for _ in range(9):
        cx, cy = rng.uniform(4, 28), rng.uniform(3, 13)
        a = rng.uniform(0, TAU)
        L = rng.uniform(2.0, 4.5)
        line(img, cx - np.cos(a) * L / 2, cy - np.sin(a) * L / 2, cx + np.cos(a) * L / 2, cy + np.sin(a) * L / 2,
             rng.choice([6, 7]))
        line(img, cx - np.cos(a) * L / 2, cy - np.sin(a) * L / 2 + 1, cx + np.cos(a) * L / 2,
             cy + np.sin(a) * L / 2 + 1, 5)
        img[int(cy) % h, int(cx) % w] = 8
    img[6, 11] = img[9, 20] = 15
    return img


def tex_tide():
    img = np.zeros((64, 64), int)
    img[0:16, 0:64] = tide_foam()
    img[16:32, 0:64] = tide_scatter()
    img[32:48, 0:16] = tide_crystal()
    img[32:48, 16:32] = tide_kelp()
    img[32:40, 32:48] = tide_prism()
    img[32:40, 48:64] = tide_strand()
    img[40:48, 32:64] = tide_drift()
    img[48:64, 0:16] = tide_crystal(((8.0, 0.5, 2.6, 0.05), (4.0, 7.5, 1.8, -0.30), (12.5, 8.5, 1.6, 0.35)))
    img[48:64, 16:32] = tide_kelp(91)
    img[48:64, 32:64] = tide_shards()
    return img, TIDE_PAL


# ---------------------------------------------------------------------------------------------------------------
# r222_warning
# ---------------------------------------------------------------------------------------------------------------

WARN_PAL = [
    (255, 0, 255),     # 0 transparent
    (16, 14, 18),      # 1 black
    (64, 58, 42),      # 2 grime
    (190, 154, 40),    # 3 weathered yellow
    (232, 200, 70),    # 4 yellow
    (248, 234, 150),   # 5 yellow highlight
    (52, 60, 72),      # 6 box dark steel
    (82, 92, 106),     # 7 box mid
    (120, 130, 140),   # 8 box light
    (164, 170, 178),   # 9 box highlight
    (110, 62, 40),     # 10 rust dark
    (162, 98, 52),     # 11 rust
    (86, 38, 22),      # 12 dead amber deep
    (148, 72, 26),     # 13 dead amber
    (208, 122, 62),    # 14 amber glint
    (230, 226, 214),   # 15 white symbol
]


def warn_tape():
    w, h = 32, 8
    y, x = np.mgrid[0:h, 0:w].astype(float)
    stripe = ((x + y) // 4) % 2
    img = np.where(stripe == 0, 4, 1)
    grime = vnoise(h, w, 8, 61)
    img = np.where((img == 4) & (grime > 0.6), 3, img)
    img = np.where((img == 1) & (grime > 0.7), 2, img)
    img[1, :] = np.where(img[1, :] == 4, 5, img[1, :])
    # torn, ragged edges: transparent outside a wobbly band
    top = 1 + (vnoise(1, w, 8, 63)[0] > 0.7)
    bot = 6 - (vnoise(1, w, 8, 65)[0] > 0.72)
    img = np.where((y < top) | (y > bot), 0, img)
    return img


def warn_front():
    n = 16
    y, x = np.mgrid[0:n, 0:n].astype(float)
    img = ramp(0.55 + 0.25 * vnoise(n, n, 3, 71) - 0.2 * y / n, [6, 7, 8], dither=1.0)
    # hazard band (rows 11..13)
    band = (y >= 11) & (y <= 13)
    img = np.where(band, np.where(((x + y) // 2) % 2 == 0, 4, 1), img)
    # warning triangle with a lightning bolt (rows 2..9)
    tri = (y >= 2) & (y <= 9) & (np.abs(x - 7.5) <= (y - 2) * 0.62 + 0.4)
    img = np.where(tri, 4, img)
    triedge = tri & ~((y >= 3) & (y <= 8) & (np.abs(x - 7.5) <= (y - 3) * 0.62 - 0.3))
    img = np.where(triedge, 1, img)
    for (bx, by) in ((8, 4), (7, 5), (7, 6), (8, 6), (8, 7)):
        img[by, bx] = 1
    # rust streaks, rivets, outline
    img = np.where((vnoise(n, n, 4, 73) > 0.8) & ~tri & ~band, 11, img)
    img[1, 1] = img[1, 14] = img[14, 1] = img[14, 14] = 9
    img[0, :] = img[n - 1, :] = 1
    img[:, 0] = img[:, n - 1] = 1
    return img


def warn_side():
    n = 16
    y, x = np.mgrid[0:n, 0:n].astype(float)
    img = ramp(0.45 + 0.25 * vnoise(n, n, 3, 81) - 0.2 * y / n, [6, 7, 8], dither=1.0)
    for vy in (3, 5, 7):                 # vents
        img[vy, 3:13] = 1
        img[vy + 1, 3:13] = 8
    img = np.where((vnoise(n, n, 5, 83) > 0.72) & (y > 8), 10, img)
    img = np.where((vnoise(n, n, 5, 85) > 0.82) & (y > 8), 11, img)
    img[0, :] = img[n - 1, :] = 1
    img[:, 0] = img[:, n - 1] = 1
    return img


def warn_lid():
    w, h = 16, 8
    y, x = np.mgrid[0:h, 0:w].astype(float)
    img = ramp(0.7 - 0.3 * y / h + 0.1 * vnoise(h, w, 4, 91), [7, 8, 9], dither=1.0)
    img[0, :] = img[h - 1, :] = 1
    img[:, 0] = img[:, w - 1] = 1
    img[3:6, 6:10] = 13                  # dead beacon base seen from above
    img[3, 7] = 14
    return img


def warn_dome():
    w, h = 16, 8
    y, x = np.mgrid[0:h, 0:w].astype(float)
    """16 x 8 dead amber beacon dome (side view): half-ellipse of cold amber glass on a steel collar."""
    r = np.hypot((x + 0.5 - 8) / 6.5, (y + 0.5 - 6.5) / 6.0)
    dome = (r < 1.0) & (y < 6)
    img = np.where(dome, ramp(0.8 - 0.55 * (y / 6) - 0.3 * np.clip((x - 8) / 7, 0, 1), [12, 13, 14], dither=1.0), 0)
    img = np.where(dome & (r > 0.86), 1, img)
    img[2, 5] = img[3, 5] = 15           # cold glint
    img[6, 1:15] = 7
    img[7, 1:15] = 6
    img[6:8, 1] = img[6:8, 14] = 1
    return img


def tex_warning():
    img = np.zeros((32, 32), int)
    img[0:8, 0:32] = warn_tape()
    img[8:24, 0:16] = warn_front()
    img[8:24, 16:32] = warn_side()
    img[24:32, 0:16] = warn_lid()
    img[24:32, 16:32] = warn_dome()
    return img, WARN_PAL


TEXTURES = [("r222_lamp", tex_lamp), ("r222_tide", tex_tide), ("r222_warning", tex_warning)]


def pal_name(tex):
    return tex + "_pl"


# ---------------------------------------------------------------------------------------------------------------
# encode, append, verify
# ---------------------------------------------------------------------------------------------------------------

def generate():
    """-> [(name, index grid (np int h x w), palette RGB list snapped to BGR555)]."""
    out = []
    for name, fn in TEXTURES:
        idx, pal = fn()
        idx = np.asarray(idx, int)
        w, h = SIZES[name]
        assert idx.shape == (h, w) and idx.min() >= 0 and idx.max() < 16, name
        assert len(pal) == 16, name
        out.append((name, idx, [snap(c) for c in pal]))
    return out


def encode(name, idx, pal):
    flat = idx.reshape(-1).tolist()
    data = bytes(flat[i] | flat[i + 1] << 4 for i in range(0, len(flat), 2))
    h, w = idx.shape
    tex = dict(name=name, fmt=3, w=w, h=h, c0=1, data=data)
    return tex, dict(name=pal_name(name), colors=[nsbtx.bgr555(c) for c in pal], pltt4=0)


def git_bytes(rev, rel):
    return subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{rel}"], check=True, capture_output=True).stdout


def build_set():
    """-> dict(bytes, rows, fails, vram=(base, out), table={tex: (palette, (w, h))}, generated, base)."""
    fails = []
    base_bytes = git_bytes(BASE_REV, BASE_SET_REL)
    base = nsbtx.parse(base_bytes)
    T = {t["name"] for t in base["textures"]}
    P = {p["name"] for p in base["palettes"]}
    gen = generate()
    new_t, new_p, rows = [], [], []
    for name, idx, pal in gen:
        t, p = encode(name, idx, pal)
        for a in (t["name"], p["name"]):
            if a in T or a in P:
                fails.append(f"{a} clashes with a stock set-018 entry")
            if len(a) > NAME_MAX:
                fails.append(f"{a} is longer than {NAME_MAX} characters")
        new_t.append(t)
        new_p.append(p)
        rows.append((name, p["name"], f"{t['w']}x{t['h']}", len(t["data"]), 32, len(set(idx.reshape(-1).tolist()))))
    for t in base["textures"]:
        t.pop("off", None)
    for p in base["palettes"]:
        p.pop("off", None)
    out = nsbtx.build(base["textures"] + new_t, base["palettes"] + new_p, pal_flag=base["header"]["pal_flag"])
    sb, so = nsbtx.parse(base_bytes), nsbtx.parse(out)
    OT = {t["name"]: t for t in so["textures"]}
    OP = {p["name"]: p for p in so["palettes"]}
    for t in sb["textures"]:
        t2 = OT.get(t["name"])
        if not t2 or t2["data"] != t["data"] or t2.get("index") != t.get("index") or \
                (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != (t["fmt"], t["w"], t["h"], t["c0"]):
            fails.append(f"stock texture {t['name']} changed")
    for p in sb["palettes"]:
        if p["name"] not in OP or not OP[p["name"]]["data"].startswith(p["data"]):
            fails.append(f"stock palette {p['name']} changed")
    for name, idx, pal in gen:
        t2, p2 = OT.get(name), OP.get(pal_name(name))
        if not t2 or not p2:
            fails.append(f"{name}: missing after build")
            continue
        rgba, ind = nsbtx.decode(t2, p2["colors"])
        h, w = idx.shape
        if (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != (3, w, h, 1):
            fails.append(f"{name}: format/size changed in the round trip")
        if [list(r) for r in ind] != idx.tolist():
            fails.append(f"{name}: texel indices differ after the round trip")
        want = [nsbtx.rgb(nsbtx.bgr555(pal[i])) for i in idx.reshape(-1).tolist()]
        got = [tuple(px[:3]) for row in rgba for px in row]
        if got != want:
            fails.append(f"{name}: decoded colours differ from the BGR555 palette")
    if len(so["textures"]) != len(sb["textures"]) + len(new_t) or len(so["palettes"]) != len(sb["palettes"]) + len(new_p):
        fails.append("entry count mismatch")
    if nsbtx.build(so["textures"], so["palettes"], keep_offsets=True, pal_flag=so["header"]["pal_flag"]) != out:
        fails.append("set 081 parse -> rebuild is not byte-identical")
    vb, vo = nsbtx.vram_usage(sb), nsbtx.vram_usage(so)
    if sum(vo) > VRAM_TARGET:
        fails.append(f"set VRAM {sum(vo)} B > target {VRAM_TARGET}")
    table = {t["name"]: (None, (t["w"], t["h"])) for t in so["textures"]}
    for name, idx, _ in gen:
        table[name] = (pal_name(name), (idx.shape[1], idx.shape[0]))
    return dict(bytes=out, rows=rows, fails=fails, vram=(vb, vo), table=table, generated=gen, parsed=so,
                stock_textures=len(sb["textures"]), stock_palettes=len(sb["palettes"]))


def write_preview(d, gen):
    from PIL import Image
    os.makedirs(d, exist_ok=True)
    for name, idx, pal in gen:
        rgb = np.array([pal[i] for i in idx.reshape(-1)], np.uint8).reshape(idx.shape[0], idx.shape[1], 3)
        a = np.where(idx == 0, 0, 255).astype(np.uint8)[..., None]
        im = Image.fromarray(np.concatenate([rgb, a], axis=2), "RGBA")
        im.save(os.path.join(d, name + ".png"))
        bg = Image.new("RGBA", im.size, (40, 46, 40, 255))
        bg.alpha_composite(im)
        bg.resize((im.size[0] * 8, im.size[1] * 8), Image.NEAREST).save(os.path.join(d, name + "_x8.png"))


def report(res):
    vb, vo = res["vram"]
    print(f"{'texture':<14} {'palette':<16} {'size':>6} {'texel B':>8} {'pal B':>6} {'colours':>8}")
    for r in res["rows"]:
        print(f"{r[0]:<14} {r[1]:<16} {r[2]:>6} {r[3]:>8} {r[4]:>6} {r[5]:>8}")
    print(f"set 081: {res['stock_textures']} stock + {len(res['rows'])} new textures; VRAM {sum(vb)} -> {sum(vo)} B "
          f"({sum(vo) / 1024:.1f} KB; texels {vb[0]} -> {vo[0]}, palettes {vb[1]} -> {vo[1]}), target "
          f"{VRAM_TARGET // 1024} KB")


def main():
    args = sys.argv[1:]
    res = build_set()
    report(res)
    for f in res["fails"]:
        print("FAIL", f)
    if not res["fails"]:
        print("PASS stock textures/palettes unchanged, new textures round-trip, set parse -> rebuild identical, VRAM ok")
    if "--preview" in args:
        write_preview(args[args.index("--preview") + 1], res["generated"])
    if "--write" in args:
        if res["fails"]:
            print("refusing to write")
            return 1
        open(os.path.join(ROOT, SET_REL), "wb").write(res["bytes"])
        print("wrote", SET_REL, len(res["bytes"]), "B")
    return 1 if res["fails"] else 0


if __name__ == "__main__":
    sys.exit(main())
