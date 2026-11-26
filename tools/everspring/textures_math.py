#!/usr/bin/env python3
"""Everspring Sanctuary (Route 218) texture set: map_texture_set_077 = stock map_texture_set_015 + twelve
procedurally generated fairy-glade textures. Pure math (NumPy): periodic value noise, rounded-box SDF cobbles,
trigonometric caustics, Voronoi facets, sphere-lit blossom clusters, all quantised onto hand-tuned 16-colour
BGR555 palettes with a 4x4 Bayer ordered dither, so every texel snaps to Platinum's 16 px per tile pixel-art grid.

Usage:
  ~/.venvs/desmume/bin/python tools/everspring/textures_math.py                 dry run: table, VRAM, round-trip checks
  ~/.venvs/desmume/bin/python tools/everspring/textures_math.py --preview DIR   also write DIR/<texture>.png (x8 sheet too)
  ~/.venvs/desmume/bin/python tools/everspring/textures_math.py --write         write SET_REL (refuses if a check fails)

Idempotent: the base is always stock set 015 read from git (BASE_REV:BASE_SET_REL), never the work tree, so reruns
never append twice. Stock textures and palettes keep their names, texels and colours (asserted); the Everspring
textures are appended after them. build_art.py drives this module (build_set()) and binds the materials.

Textures (all pltt16, opaque, 32x32 = 2 tiles per repeat = 16 texels per tile):
  ev_grass       twilight emerald meadow: blade strokes, clover sprigs, tiny lavender/pink flowers
  ev_tgrass      fairy tall grass: overlapping fanned tufts with luminous pink / lavender petal tips
  ev_spiral_flw  glowing spiral-blossom meadow: pink / cyan / gold pixel blossoms with mint halos.
                 BLOSSOMS gives the exact texel boxes of three blossoms (build_art maps glow decals onto them)
  ev_cobble      rounded-box SDF moonstone cobbles (running bond, bevel-lit) in mossy turquoise grout
  ev_water       iridescent moonlit caustics: indigo depth, cyan/white caustic web, violet shimmer zones
  ev_bridge      silver-lavender timber planks (rows 0..23) + rose-gold riveted trim band (rows 24..31)
  ev_cliff       mossy moonstone courses with turquoise moss drips (terrace curbs, shore walls)
  ev_blossom     sakura-pink and wisteria-lavender canopy clusters over plum shade; BARK = plum bark box
  ev_marble      pale moonstone marble with soft veins and faint 1-tile flag seams (fountain, plaza)
  ev_gardevoir   statue swatch atlas: emerald hair / pearl white / rose crystal / lavender-white folds (GV_UV)
  ev_crystal     faceted violet-cyan Rift Conduit crystal (Voronoi facets with lit edges)
  ev_mushroom    left: spotted magenta cap, gills and pale stem (MUSH_UV); right: warm lantern glow panel
"""
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import nsbtx  # noqa: E402

SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_077.nsbtx"
BASE_REV = "HEAD"
BASE_SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_015.nsbtx"
VRAM_BUDGET = 384 * 1024        # field 3D texture VRAM since f571ecb7eb (banks A+B+C)
VRAM_TARGET = 160 * 1024        # PLAN goal for this set
NAME_MAX = 15
N = 32

BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], float) + 0.5) / 16.0 - 0.5
Y, X = np.mgrid[0:N, 0:N].astype(float)
BAYER = BAYER4[(Y % 4).astype(int), (X % 4).astype(int)]
TAU = 2 * np.pi

# texel boxes (x0, y0, x1, y1), exclusive ends, used by build_art.py for UV mapping
BLOSSOMS = {"pink": (3, 3, 10, 10), "cyan": (19, 7, 26, 14), "gold": (11, 21, 18, 28)}
BARK = (26, 25, 32, 32)
GV_UV = {"hair": (1, 1, 15, 15), "pearl": (17, 1, 31, 15), "rose": (1, 17, 15, 31), "fold": (17, 17, 31, 31)}
MUSH_UV = {"cap": (0, 0, 16, 18), "gills": (0, 18, 16, 21), "stem": (2, 21, 14, 32), "glow": (17, 1, 31, 31)}
PAL_NAMES = {"ev_spiral_flw": "ev_spiralf_pl"}


# ---------------------------------------------------------------------------------------------------------------
# math helpers (everything periodic over 32 texels so textures tile seamlessly)
# ---------------------------------------------------------------------------------------------------------------

def pnoise(cells, seed):
    """Periodic value noise in [0, 1): a cells x cells lattice, smoothstep-bilinear, wrapping at 32 texels."""
    rng = np.random.RandomState(seed)
    g = rng.rand(cells, cells)
    fx, fy = X * cells / N, Y * cells / N
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - x0, fy - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    x0, y0, x1, y1 = x0 % cells, y0 % cells, (x0 + 1) % cells, (y0 + 1) % cells
    a = g[y0, x0] * (1 - tx) + g[y0, x1] * tx
    b = g[y1, x0] * (1 - tx) + g[y1, x1] * tx
    return a * (1 - ty) + b * ty


def fbm(seed, octaves=((4, 0.55), (8, 0.3), (16, 0.15))):
    return sum(w * pnoise(c, seed + k * 101) for k, (c, w) in enumerate(octaves))


def wrapd(a, b):
    d = np.abs(a - b) % N
    return np.minimum(d, N - d)


def wrapv(a, b):
    """Signed periodic difference a - b in [-16, 16)."""
    return (a - b + N / 2) % N - N / 2


def rbox(px, py, bx, by, r):
    """Rounded-box SDF (negative inside); half extents bx, by; corner radius r."""
    qx, qy = np.abs(px) - bx + r, np.abs(py) - by + r
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def ramp(t, idx, dither=1.0):
    """t in [0, 1] -> palette index along the ramp `idx`, Bayer-dithered between neighbouring entries."""
    n = len(idx)
    v = np.clip(np.floor(np.clip(t, 0, 1) * (n - 1) + 0.5 + BAYER * dither), 0, n - 1).astype(int)
    return np.array(idx)[v]


def snap(c):
    return tuple(int(v) >> 3 << 3 for v in c)


def put(img, x, y, v):
    img[int(y) % N, int(x) % N] = v


# ---------------------------------------------------------------------------------------------------------------
# the twelve textures: each returns (index grid 32x32, 16 RGB colours)
# ---------------------------------------------------------------------------------------------------------------

def tex_grass():
    pal = [(16, 52, 48), (22, 70, 58), (30, 88, 66), (40, 108, 74), (54, 128, 84), (70, 148, 94), (90, 168, 106),
           (114, 188, 120), (142, 206, 140), (62, 140, 110), (104, 190, 150), (176, 150, 224), (236, 160, 206),
           (250, 236, 180), (232, 244, 255), (40, 84, 96)]
    t = 0.38 + 0.42 * (fbm(11) - 0.5) * 1.6 + 0.06 * np.sin(TAU * (X + 2 * Y) / N)
    img = ramp(t + 0.12, [1, 2, 3, 4, 5, 6])
    img[(fbm(12) < 0.28)] = 15                      # cool twilight shade pockets
    img = np.where((fbm(12) < 0.33) & (img != 15), 2, img)
    rng = np.random.RandomState(13)
    for _ in range(46):                             # short blade strokes, lit tip, dark root
        bx, by, ln = rng.randint(0, N), rng.randint(0, N), rng.randint(2, 4)
        put(img, bx, by + 1, 1)
        for k in range(ln):
            put(img, bx, by - k, 5 + min(k, 2))
        put(img, bx, by - ln, 8)
    for cx, cy in ((6, 7), (22, 20), (27, 4)):      # clover sprigs: three round leaves
        for dx, dy in ((0, -1), (-1, 1), (1, 1)):
            for ex, ey in ((0, 0), (1, 0), (0, 1), (1, 1)):
                put(img, cx + 2 * dx + ex - 1, cy + 2 * dy + ey - 1, 10 if (ex, ey) == (0, 0) else 9)
        put(img, cx, cy + 3, 1)
    for k, (cx, cy) in enumerate(((14, 12), (3, 25), (25, 28), (18, 3), (11, 21))):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            put(img, cx + dx, cy + dy, 11 if k % 2 else 12)
        put(img, cx, cy, 13)
        put(img, cx + 1, cy + 2, 1)
    for cx, cy in ((9, 15), (29, 13)):
        put(img, cx, cy, 14)
    return img, pal


def tex_tgrass():
    pal = [(12, 40, 44), (18, 60, 54), (26, 82, 62), (36, 106, 72), (50, 132, 84), (68, 156, 96), (92, 180, 112),
           (126, 204, 134), (164, 226, 160), (120, 80, 170), (178, 140, 236), (220, 196, 252), (190, 80, 150),
           (240, 140, 200), (255, 206, 234), (34, 62, 86)]
    img = ramp(0.3 + 0.5 * fbm(21), [15, 1, 2], 1.0)
    for row in range(4):                            # back rows first: lower tufts overlap the ones above
        y0 = row * 8 + 7
        for col in range(4):
            cx = col * 8 + (4 if row % 2 else 0) + 3.5
            tip = (9, 10, 11) if (row + col) % 2 else (12, 13, 14)
            for k in range(6):                      # six fanned blades per tuft
                lean = (k - 2.5) * 0.55
                h = 9 - abs(k - 2.5) * 0.9
                for s in range(int(h) + 1):
                    f = s / h
                    x = cx + (k - 2.5) * 0.7 + lean * s * 0.6
                    y = y0 - s
                    shade = 3 + int(4 * f) + (1 if k < 3 else 0)
                    put(img, x, y, min(shade, 8))
                    if k in (0, 5) and s < h - 1:
                        put(img, x + (-1 if k == 0 else 1), y, 1)      # crisp dark outline on the tuft flanks
                tx, ty = cx + (k - 2.5) * 0.7 + lean * h * 0.6, y0 - h
                put(img, tx, ty, tip[2] if k in (2, 3) else tip[1])
                put(img, tx, ty + 1, tip[0])
            for dx in range(-3, 5):
                put(img, cx + dx, y0 + 1, 0)       # shadow line under each tuft
    return img, pal


def tex_spiral_flw():
    pal = [(14, 44, 46), (22, 64, 58), (32, 86, 68), (46, 110, 80), (64, 136, 94), (96, 170, 130), (150, 214, 190),
           (150, 40, 120), (236, 100, 184), (255, 190, 232), (30, 120, 170), (70, 200, 236), (190, 246, 255),
           (200, 140, 30), (255, 210, 80), (255, 250, 214)]
    img = ramp(0.25 + 0.6 * fbm(31), [0, 1, 2, 3, 4])
    # a three-arm logarithmic spiral of soft glow across the tile (sin(3 theta - 1.55 r), r in texel/4 units)
    dx, dy = wrapv(X, 15.5), wrapv(Y, 15.5)
    r, th = np.hypot(dx, dy) / 4.0, np.arctan2(dy, dx)
    arm = np.sin(3 * th - 1.55 * r)
    img = np.where((arm > 0.75) & (img < 4), img + 1, img)
    hues = {"pink": (7, 8, 9), "cyan": (10, 11, 12), "gold": (13, 14, 15)}
    spots = [("pink", 6, 6), ("cyan", 22, 10), ("gold", 14, 24), ("pink", 27, 26), ("cyan", 3, 19), ("gold", 28, 1),
             ("pink", 17, 15), ("cyan", 9, 29)]
    for name, cx, cy in spots:
        d = np.hypot(wrapv(X, cx), wrapv(Y, cy))
        img = np.where((d < 3.4) & (d >= 2.3), np.where(BAYER > -0.1, 6, 5), img)      # mint glow halo
        dk, md, br = hues[name]
        for ddx, ddy in ((0, -2), (-2, 0), (2, 0), (0, 2)):                             # four petals
            put(img, cx + ddx, cy + ddy, dk)
        for ddx, ddy in ((0, -1), (-1, 0), (1, 0), (0, 1), (-1, -1), (1, 1)):
            put(img, cx + ddx, cy + ddy, md)
        put(img, cx - 1, cy - 1, br)
        put(img, cx, cy, 15)
    return img, pal


def tex_cobble():
    pal = [(16, 34, 44), (30, 74, 78), (46, 112, 108), (72, 148, 128), (70, 74, 108), (98, 104, 140), (124, 130, 166),
           (150, 156, 190), (176, 182, 212), (200, 206, 230), (222, 228, 244), (244, 246, 255), (136, 150, 196),
           (168, 160, 206), (190, 186, 222), (110, 120, 170)]
    best = np.full((N, N), 99.0)
    shade = np.zeros((N, N))
    tint = np.zeros((N, N), int)
    rng = np.random.RandomState(41)
    widths = [10, 11, 11]
    for row in range(4):
        x = (row % 2) * 6 + (row // 2) * 3
        for k, w in enumerate(widths):
            cx, cy = x + w / 2.0, row * 8 + 4.0
            px, py = wrapv(X + 0.5, cx), wrapv(Y + 0.5, cy)
            d = rbox(px, py, w / 2.0 - 1.0, 3.0, 2.2)
            lit = rbox(px + 0.9, py + 0.9, w / 2.0 - 1.0, 3.0, 2.2) - d        # >0 toward the lit top-left edge
            m = d < best
            best = np.where(m, d, best)
            shade = np.where(m, lit, shade)
            tint = np.where(m, rng.randint(0, 3), tint)
            x += w
    inside = best < 0
    t = 0.45 + 0.35 * np.clip(-best / 2.5, 0, 1) - 0.45 * shade + 0.12 * (fbm(42) - 0.5)
    stones = [ramp(t, [4, 5, 6, 7, 8, 9, 10]), ramp(t, [4, 15, 12, 7, 8, 9, 10]), ramp(t, [4, 5, 13, 14, 8, 9, 10])]
    img = np.where(tint == 0, stones[0], np.where(tint == 1, stones[1], stones[2]))
    img = np.where(inside & (pnoise(16, 43) > 0.86) & (best < -1.5), 11, img)           # moonstone glints
    grout = ramp(0.2 + 0.9 * fbm(44) + 0.3 * np.clip(best, 0, 1), [0, 1, 2, 3], 0.8)
    img = np.where(inside, img, grout)
    img = np.where((best >= 0) & (best < 0.7) & (shade < 0), 0, img)                    # crisp dark lower-right rims
    return img, pal


def tex_water():
    pal = [(24, 34, 84), (36, 56, 120), (44, 80, 152), (52, 106, 178), (62, 132, 198), (76, 158, 216), (96, 184, 230),
           (124, 210, 240), (164, 232, 248), (214, 248, 255), (250, 255, 255), (72, 82, 168), (104, 110, 204),
           (144, 140, 232), (194, 184, 250), (80, 168, 200)]
    u = TAU * (2 * X / N + 0.18 * np.sin(TAU * 2 * Y / N) + 0.10 * np.sin(TAU * (X + Y) / N))
    v = TAU * ((X + 2 * Y) / N + 0.16 * np.sin(TAU * 3 * X / N + 1.0))
    w = TAU * ((3 * Y - X) / N + 0.12 * np.sin(TAU * 2 * (X - Y) / N))
    caustic = (1 - np.abs(np.sin(u))) ** 5 + (1 - np.abs(np.sin(v))) ** 5 + 0.6 * (1 - np.abs(np.sin(w))) ** 6
    depth = 0.56 + 0.35 * (fbm(51) - 0.5) + 0.12 * np.sin(TAU * (X - Y) / N)
    violet = (0.5 + 0.5 * np.sin(TAU * (X + Y) / N + 1.3) * np.cos(TAU * (Y - 2 * X) / N)) + 0.25 * (pnoise(8, 52) - 0.5) > 0.86
    img = np.where(violet, ramp(depth, [2, 11, 12, 13]), ramp(depth, [2, 3, 4, 5, 15, 6]))
    c = np.clip(caustic / 1.4, 0, 1)
    img = np.where(c > 0.45, np.where(violet, ramp((c - 0.45) / 0.55, [13, 14, 9]), ramp((c - 0.45) / 0.55, [6, 7, 8, 9])), img)
    img = np.where((c > 0.93) & (BAYER > 0.2), 10, img)
    return img, pal


def tex_bridge():
    pal = [(40, 32, 64), (78, 66, 110), (110, 100, 146), (136, 126, 170), (160, 152, 192), (182, 176, 212),
           (204, 200, 228), (226, 224, 242), (246, 246, 255), (110, 58, 64), (160, 90, 86), (204, 128, 112),
           (236, 170, 140), (252, 212, 180), (255, 240, 220), (150, 140, 186)]
    grain = 0.5 + 0.28 * np.sin(TAU * (X / 8.0) * 3 + 2.2 * pnoise(8, 61)) + 0.25 * (fbm(62) - 0.5)
    plank = (X // 8).astype(int)
    t = grain + 0.08 * ((plank * 37) % 5 - 2) / 2.0 + 0.18 * (1 - (X % 8) / 7.0) - 0.05
    img = ramp(t, [2, 15, 3, 4, 5, 6, 7])
    img = np.where(X % 8 == 7, 1, img)                                    # plank seams
    img = np.where(X % 8 == 0, np.where(Y % 4 == 0, 8, 7), img)           # lit plank edges
    for p in range(4):                                                    # staggered butt joints + nail pairs
        jy = (p * 11 + 5) % 24
        img[jy, p * 8:p * 8 + 7] = 0
        img[(jy + 2) % 24, p * 8 + 2] = 1
        img[(jy + 2) % 24, p * 8 + 5] = 1
    band = [9, 13, 12, 11, 12, 13, 11, 9]
    for k, v in enumerate(band):
        img[24 + k, :] = v
    for rx in range(3, N, 8):                                             # rivets on the rose-gold trim
        img[27, rx], img[28, rx], img[28, rx + 1] = 14, 10, 10
    return img, pal


def tex_cliff():
    pal = [(22, 24, 46), (44, 46, 78), (66, 70, 104), (90, 96, 132), (116, 122, 160), (142, 148, 186),
           (168, 174, 208), (196, 200, 228), (30, 70, 64), (46, 104, 82), (70, 140, 100), (104, 176, 120),
           (60, 150, 150), (120, 206, 190), (84, 88, 140), (150, 140, 190)]
    row = (Y // 8).astype(int)
    off = (row % 2) * 8
    bx = ((X + off) % 16)
    by = Y % 8
    edge = np.minimum(np.minimum(bx, 15 - bx), np.minimum(by, 7 - by))
    t = 0.5 + 0.25 * (by < 2) - 0.25 * (by > 5) + 0.18 * (bx < 2) - 0.12 * (bx > 13) + 0.3 * (fbm(71) - 0.5)
    alt = ((X + off) // 16 + row) % 3
    img = np.where(alt == 0, ramp(t, [1, 2, 3, 4, 5, 6, 7]), np.where(alt == 1, ramp(t, [1, 14, 3, 4, 15, 6, 7]),
                                                                       ramp(t, [1, 2, 14, 4, 5, 15, 7])))
    img = np.where(edge == 0, np.where((by == 7) | (bx == 15), 0, 2), img)
    moss = pnoise(8, 72) + 0.6 * pnoise(16, 73)
    drip = (by <= (moss * 4.2).astype(int)) & (moss > 0.55)
    img = np.where(drip, ramp(moss - 0.3 + 0.15 * (by == 0), [8, 9, 10, 11]), img)
    img = np.where(drip & (pnoise(16, 74) > 0.72), np.where(by == 0, 13, 12), img)
    return img, pal


def tex_blossom():
    pal = [(36, 14, 40), (66, 26, 62), (98, 40, 84), (150, 60, 120), (200, 96, 160), (236, 140, 196),
           (252, 186, 222), (255, 226, 240), (80, 60, 140), (120, 90, 190), (160, 128, 228), (198, 170, 250),
           (232, 214, 255), (128, 52, 104), (50, 80, 70), (90, 140, 100)]
    img = ramp(0.2 + 0.7 * fbm(81), [0, 1, 2, 13])
    img = np.where(pnoise(16, 82) > 0.78, 14, img)                       # green leaf glints in the shade
    img = np.where(pnoise(16, 83) > 0.86, 15, img)
    rng = np.random.RandomState(84)
    clusters = []
    while len(clusters) < 22:
        cx, cy, r = rng.uniform(0, N), rng.uniform(0, N), rng.uniform(3.2, 5.4)
        if wrapd(cx, 29) < 3.2 + r and wrapd(cy, 28.5) < 3.5 + r:
            continue                                                       # keep the bark box clear
        clusters.append((cx, cy, r, len(clusters) % 2))
    for cx, cy, r, kind in sorted(clusters, key=lambda c: -c[3]):     # wisteria first, sakura over it
        if kind == 0:
            r *= 1.12
        px, py = wrapv(X + 0.5, cx), wrapv(Y + 0.5, cy)
        d = np.hypot(px, py) / r
        m = d < 1.0
        z = np.sqrt(np.clip(1 - d * d, 0, 1))
        lit = np.clip(0.25 + 0.75 * (z * 0.7 - px / r * 0.35 - py / r * 0.45), 0, 1)
        lit = lit + 0.12 * (pnoise(16, 85 + kind) - 0.5)
        ramp_idx = [3, 13, 4, 5, 6, 7] if kind == 0 else [8, 9, 10, 11, 12]
        img = np.where(m, ramp(lit, ramp_idx), img)
        img = np.where((d >= 1.0) & (d < 1.18) & (py > 0), 0, img)        # crisp plum rim under each cluster
    x0, y0, x1, y1 = BARK
    for yy in range(y0, y1):
        for xx in range(x0, x1):
            img[yy, xx] = (0, 1, 2, 1, 0, 1)[(xx - x0 + (yy // 3)) % 6] if (xx * 7 + yy * 3) % 11 else 2
    return img, pal


def tex_marble():
    pal = [(96, 96, 140), (122, 122, 166), (146, 148, 188), (168, 170, 206), (186, 188, 220), (202, 204, 232),
           (216, 218, 240), (228, 230, 248), (240, 242, 252), (252, 252, 255), (190, 180, 226), (176, 196, 226),
           (210, 200, 236), (200, 214, 238), (150, 170, 200), (230, 220, 246)]
    base = 0.62 + 0.3 * (fbm(91) - 0.5)
    img = np.where(pnoise(4, 92) > 0.55, ramp(base, [4, 10, 12, 6, 15, 8, 9]), ramp(base, [4, 11, 13, 6, 7, 8, 9]))
    vein = np.abs(np.sin(TAU * (X + 2 * Y) / N + 4.2 * fbm(93)))
    img = np.where(vein < 0.06, 3, np.where(vein < 0.14, np.where(BAYER > 0.15, 4, img), img))
    vein2 = np.abs(np.sin(TAU * (2 * X - Y) / N + 3.0 * fbm(94)))
    img = np.where((vein2 < 0.05) & (img > 4), 4, img)
    img = np.where((X == 31) | (Y == 31), 3, img)                           # faint 2-tile flag seams
    img = np.where(((X == 0) | (Y == 0)) & (img > 4), 9, img)               # lit seam lips
    return img, pal


def tex_gardevoir():
    pal = [(20, 96, 66), (34, 140, 90), (70, 190, 124), (150, 236, 180),
           (196, 198, 224), (220, 222, 240), (240, 242, 252), (255, 255, 255),
           (176, 56, 110), (226, 104, 152), (250, 160, 196), (255, 226, 238),
           (170, 164, 214), (198, 194, 232), (222, 220, 246), (246, 244, 255)]
    img = np.zeros((N, N), int)
    q = (X >= 16).astype(int) + 2 * (Y >= 16).astype(int)
    lx, ly = X % 16, Y % 16
    hair = 0.55 + 0.35 * np.sin(TAU * (lx * 2 + ly) / 16.0) * 0.6 + 0.2 * (pnoise(8, 101) - 0.5) - 0.02 * ly
    pearl = 0.72 + 0.25 * (fbm(102) - 0.5)
    rose = np.where(lx + ly < 15, 0.75 - 0.03 * ly, 0.45 + 0.02 * lx) + 0.1 * (lx == ly)
    fold = 0.68 + 0.28 * (fbm(103) - 0.5) + 0.06 * np.sin(TAU * (lx + ly) / 16.0)
    img = np.where(q == 0, ramp(hair, [0, 1, 2, 3]), img)
    img = np.where(q == 1, ramp(pearl, [4, 5, 6, 7]), img)
    img = np.where(q == 2, ramp(rose, [8, 9, 10, 11]), img)
    img = np.where(q == 3, ramp(fold, [12, 13, 14, 15]), img)
    return img, pal


def tex_crystal():
    pal = [(28, 10, 60), (52, 22, 104), (80, 40, 150), (112, 64, 196), (146, 98, 232), (184, 144, 250),
           (222, 200, 255), (40, 70, 150), (50, 120, 200), (70, 170, 230), (120, 220, 250), (200, 250, 255),
           (255, 255, 255), (170, 80, 220), (96, 200, 220), (240, 230, 255)]
    rng = np.random.RandomState(111)
    seeds = [(rng.uniform(0, N), rng.uniform(0, N), rng.uniform(0, TAU), k % 2) for k in range(7)]
    d1 = np.full((N, N), 99.0)
    d2 = np.full((N, N), 99.0)
    val = np.zeros((N, N))
    kind = np.zeros((N, N), int)
    for sx, sy, ang, kd in seeds:
        px, py = wrapv(X + 0.5, sx), wrapv(Y + 0.5, sy)
        d = np.hypot(px, py)
        g = 0.5 + 0.5 * (np.cos(ang) * px + np.sin(ang) * py) / 9.0
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        val = np.where(closer, g, val)
        kind = np.where(closer, kd, kind)
        d1 = np.where(closer, d, d1)
    img = np.where(kind == 0, ramp(val, [1, 2, 13, 3, 4, 5, 6]), ramp(val, [7, 8, 14, 9, 10, 11]))
    edge = d2 - d1
    img = np.where(edge < 0.9, np.where((X + Y) % 2 == 0, 12, 15), img)  # bright facet edges
    img = np.where((edge >= 0.9) & (edge < 1.6) & (val < 0.4), 0, img)   # dark facet shadows
    return img, pal


def tex_mushroom():
    pal = [(40, 14, 46), (110, 24, 96), (180, 50, 150), (236, 96, 196), (255, 170, 230), (90, 230, 246),
           (230, 252, 255), (180, 170, 210), (226, 220, 240), (250, 248, 255), (110, 70, 40), (200, 120, 50),
           (246, 170, 70), (255, 214, 120), (255, 240, 190), (255, 255, 236)]
    img = np.zeros((N, N), int)
    left = X < 16
    # cap: dome-lit, cyan and white spots
    cx, cy = 7.5, 15.0
    d = np.hypot((X + 0.5 - 8) / 8.0, (Y + 0.5 - cy) / 15.0)
    lit = np.clip(1.15 - d - 0.25 * (X - 4) / 12.0, 0, 1)
    cap = ramp(lit, [1, 2, 3, 4])
    for sx, sy, sr in ((4, 5, 1.8), (11, 4, 1.4), (8, 10, 2.0), (2, 13, 1.3), (13, 12, 1.6), (6, 16, 1.2)):
        ds = np.hypot(X + 0.5 - sx, Y + 0.5 - sy)
        cap = np.where(ds < sr, np.where(ds < sr * 0.5, 6, 5), cap)
    img = np.where(left & (Y < 18), cap, img)
    img = np.where(left & (Y >= 18) & (Y < 21), np.where(X % 2 == 0, 1, 0), img)       # gills
    stem = ramp(0.35 + 0.6 * (1 - np.abs(X + 0.5 - 8) / 8.0) + 0.08 * (fbm(121) - 0.5), [7, 8, 9])
    img = np.where(left & (Y >= 21), stem, img)
    # lantern glow panel: radial warm glow inside a dark frame with a cross mullion
    g = np.hypot(X + 0.5 - 24, (Y + 0.5 - 16) * 0.55) / 9.0
    glow = ramp(1 - g, [11, 12, 13, 14, 15], 1.0)
    frame = (X == 16) | (X == 31) | (Y == 0) | (Y == 31) | ((X == 24) & (np.abs(Y - 16) > 3)) | \
        ((Y == 16) & (np.abs(X - 24) > 3))
    img = np.where(~left, np.where(frame, 10, glow), img)
    return img, pal


TEXTURES = [("ev_grass", tex_grass), ("ev_tgrass", tex_tgrass), ("ev_spiral_flw", tex_spiral_flw),
            ("ev_cobble", tex_cobble), ("ev_water", tex_water), ("ev_bridge", tex_bridge), ("ev_cliff", tex_cliff),
            ("ev_blossom", tex_blossom), ("ev_marble", tex_marble), ("ev_gardevoir", tex_gardevoir),
            ("ev_crystal", tex_crystal), ("ev_mushroom", tex_mushroom)]


def pal_name(tex):
    return PAL_NAMES.get(tex, tex + "_pl")


# ---------------------------------------------------------------------------------------------------------------
# encode, append, verify
# ---------------------------------------------------------------------------------------------------------------

def generate():
    """-> [(name, index grid (np int 32x32), palette RGB list (snapped to BGR555))]."""
    out = []
    for name, fn in TEXTURES:
        idx, pal = fn()
        idx = np.asarray(idx, int)
        assert idx.shape == (N, N) and idx.min() >= 0 and idx.max() < 16, name
        assert len(pal) == 16, name
        out.append((name, idx, [snap(c) for c in pal]))
    return out


def encode(name, idx, pal):
    flat = idx.reshape(-1).tolist()
    data = bytes(flat[i] | flat[i + 1] << 4 for i in range(0, len(flat), 2))
    tex = dict(name=name, fmt=3, w=N, h=N, c0=0, data=data)
    return tex, dict(name=pal_name(name), colors=[nsbtx.bgr555(c) for c in pal], pltt4=0)


def git_bytes(rev, rel):
    return subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{rel}"], check=True, capture_output=True).stdout


def build_set():
    """-> dict(bytes, rows, fails, vram=(base, out), table={tex: (palette, (w, h))}, generated)."""
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
                fails.append(f"{a} clashes with a stock set-015 entry")
            if len(a) > NAME_MAX:
                fails.append(f"{a} is longer than {NAME_MAX} characters")
        new_t.append(t)
        new_p.append(p)
        rows.append((name, p["name"], f"{N}x{N}", len(t["data"]), 32, int(len(set(idx.reshape(-1).tolist())))))
    for t in base["textures"]:
        t.pop("off", None)
    for p in base["palettes"]:
        p.pop("off", None)
    out = nsbtx.build(base["textures"] + new_t, base["palettes"] + new_p, pal_flag=base["header"]["pal_flag"])
    # round trip: stock entries unchanged, every appended texture decodes back to exactly the generated texels
    sb, so = nsbtx.parse(base_bytes), nsbtx.parse(out)
    OT = {t["name"]: t for t in so["textures"]}
    OP = {p["name"]: p for p in so["palettes"]}
    for t in sb["textures"]:
        t2 = OT.get(t["name"])
        if not t2 or t2["data"] != t["data"] or (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != (t["fmt"], t["w"], t["h"], t["c0"]):
            fails.append(f"stock texture {t['name']} changed")
    for p in sb["palettes"]:
        if p["name"] not in OP or not OP[p["name"]]["data"].startswith(p["data"]):
            fails.append(f"stock palette {p['name']} changed")
    decoded = {}
    for name, idx, pal in gen:
        t2, p2 = OT.get(name), OP.get(pal_name(name))
        if not t2 or not p2:
            fails.append(f"{name}: missing after build")
            continue
        rgba, ind = nsbtx.decode(t2, p2["colors"])
        if (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != (3, N, N, 0):
            fails.append(f"{name}: format/size changed in the round trip")
        if [list(r) for r in ind] != idx.tolist():
            fails.append(f"{name}: texel indices differ after the round trip")
        want = [nsbtx.rgb(nsbtx.bgr555(pal[i])) for i in idx.reshape(-1).tolist()]
        got = [tuple(px[:3]) for row in rgba for px in row] if isinstance(rgba[0], (list, tuple)) and \
            isinstance(rgba[0][0], (list, tuple)) else None
        if got is not None and got != want:
            fails.append(f"{name}: decoded colours differ from the BGR555 palette")
        decoded[name] = (rgba, ind)
    if len(so["textures"]) != len(sb["textures"]) + len(new_t) or len(so["palettes"]) != len(sb["palettes"]) + len(new_p):
        fails.append("entry count mismatch")
    vb, vo = nsbtx.vram_usage(sb), nsbtx.vram_usage(so)
    if sum(vo) > VRAM_TARGET:
        fails.append(f"set VRAM {sum(vo)} B > target {VRAM_TARGET}")
    if sum(vo) > VRAM_BUDGET:
        fails.append(f"set VRAM {sum(vo)} B > budget {VRAM_BUDGET}")
    table = {t["name"]: (None, (t["w"], t["h"])) for t in so["textures"]}
    for name, _, _ in gen:
        table[name] = (pal_name(name), (N, N))
    return dict(bytes=out, rows=rows, fails=fails, vram=(vb, vo), table=table, generated=gen, decoded=decoded,
                stock_textures=len(sb["textures"]), stock_palettes=len(sb["palettes"]))


def write_preview(d, gen):
    from PIL import Image
    os.makedirs(d, exist_ok=True)
    sheet = Image.new("RGB", (len(gen) * (N * 8 + 8), N * 8 * 2 + 8), (20, 18, 30))
    for k, (name, idx, pal) in enumerate(gen):
        img = Image.new("RGB", (N, N))
        img.putdata([pal[i] for i in idx.reshape(-1).tolist()])
        img.save(os.path.join(d, name + ".png"))
        big = img.resize((N * 4, N * 4), Image.NEAREST)
        tiled = Image.new("RGB", (N * 8, N * 8))
        for oy in (0, 1):
            for ox in (0, 1):
                tiled.paste(big, (ox * N * 4, oy * N * 4))
        sheet.paste(img.resize((N * 8, N * 8), Image.NEAREST), (k * (N * 8 + 8), 0))
        sheet.paste(tiled, (k * (N * 8 + 8), N * 8 + 8))
    sheet.save(os.path.join(d, "ev_textures_sheet.png"))


def report(res):
    vb, vo = res["vram"]
    print(f"map_texture_set_077 = git {BASE_REV}:{BASE_SET_REL} ({res['stock_textures']} textures, "
          f"{res['stock_palettes']} palettes) + {len(res['rows'])} Everspring textures")
    print(f"{'texture':14s} {'palette':15s} {'size':6s} {'texel B':>7s} {'pal B':>5s} {'colours':>7s}")
    for name, pn, size, tb, pb, nc in res["rows"]:
        print(f"{name:14s} {pn:15s} {size:6s} {tb:7d} {pb:5d} {nc:7d}")
    print(f"VRAM: {sum(vb)} -> {sum(vo)} B ({sum(vo) / 1024:.1f} KB; texels {vb[0]} -> {vo[0]}, palettes {vb[1]} -> "
          f"{vo[1]}); target {VRAM_TARGET // 1024} KB, budget {VRAM_BUDGET // 1024} KB")


def main():
    args = sys.argv[1:]
    res = build_set()
    report(res)
    if "--preview" in args:
        d = args[args.index("--preview") + 1]
        write_preview(d, res["generated"])
        print("wrote texture previews to", d)
    for f in res["fails"]:
        print("FAIL", f)
    if not res["fails"]:
        print("PASS every appended texture round-trips (texels + BGR555 colours); stock textures/palettes unchanged; "
              "VRAM within target")
    if "--write" in args:
        if res["fails"]:
            print("refusing to write: checks failed")
            return 1
        open(os.path.join(ROOT, SET_REL), "wb").write(res["bytes"])
        print("wrote", SET_REL, len(res["bytes"]), "B")
    return 1 if res["fails"] else 0


if __name__ == "__main__":
    sys.exit(main())
