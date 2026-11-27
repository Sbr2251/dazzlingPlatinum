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
BLOSSOMS = {"pink": (0, 0, 16, 16), "lav": (16, 0, 32, 16), "cream": (0, 16, 16, 32), "mix": (16, 16, 32, 32)}
TUFT_UV = {"tuft_a": (0, 0, 16, 16), "tuft_b": (16, 0, 32, 16), "edge": (0, 16, 16, 32), "foam": (16, 16, 32, 32)}
BARK = (26, 25, 32, 32)
GV_UV = {"hair": (1, 1, 15, 15), "pearl": (17, 1, 31, 15), "rose": (1, 17, 15, 31), "fold": (17, 17, 31, 31)}
MUSH_UV = {"cap": (0, 0, 16, 18), "gills": (0, 18, 16, 21), "stem": (2, 21, 14, 32), "glow": (17, 1, 31, 31)}
PAL_NAMES = {"ev_spiral_flw": "ev_spiralf_pl", "ev_flw_decal": "ev_flwdec_pl", "ev_tuft_decal": "ev_tuft_pl"}
TRANSPARENT_TEX = {"ev_flw_decal", "ev_tuft_decal"}

# Sakura / Wisteria re-palette of stock Platinum tree01 / conttree_t (0 = transparent, 1 = spring grass base, 2..8 sakura, 9..14 bark)
SAKURA_TREE_PAL = [
    (255, 213,   0),  #  0 transparent (c0=1)
    ( 64, 152,  92),  #  1 spring Sinnoh grass ring under trunk (matches ev_grass!)
    (152,  82, 134),  #  2 dusky sakura-rose base foliage
    (220, 134, 182),  #  3 mid cherry-blossom pink
    (242, 170, 208),  #  4 bright sakura blossom pink
    (184, 108, 158),  #  5 mid-dark sakura foliage
    (252, 204, 228),  #  6 sunlit blush petal highlight
    (255, 234, 244),  #  7 peak creamy blossom highlight
    ( 92,  50,  94),  #  8 deep plum canopy shadow
    (106,  80,  76),  #  9 warm dark cherry-bark shadow
    (204, 174, 156),  # 10 pale warm cherry-bark highlight
    ( 56,  40,  46),  # 11 dark bark outline
    ( 84,  62,  62),  # 12 dark cherry-wood bark
    (154, 120, 108),  # 13 lit cherry-wood bark
    (128,  98,  92),  # 14 mid cherry-wood bark
    (240, 224, 236),  # 15 unused soft blush
]


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
    # Vibrant spring Sinnoh grass harmonized with Platinum's ngrass/tshadow + subtle fallen sakura petals
    pal = [(42, 108, 68), (54, 132, 80), (66, 154, 92), (80, 176, 102), (96, 196, 114), (116, 214, 126), (138, 228, 142),
           (162, 240, 160), (186, 248, 178), (74, 164, 106), (124, 218, 152), (222, 172, 228), (246, 178, 214),
           (255, 240, 184), (255, 244, 250), (58, 138, 92)]
    t = 0.42 + 0.34 * (fbm(11) - 0.5) * 1.4 + 0.05 * np.sin(TAU * (X + 2 * Y) / N)
    img = ramp(t + 0.10, [2, 3, 4, 5, 6])
    img[(fbm(12) < 0.25)] = 15                      # soft dappled shade pockets
    rng = np.random.RandomState(13)
    for _ in range(38):                             # subtle Platinum grass tufts
        bx, by, ln = rng.randint(0, N), rng.randint(0, N), rng.randint(2, 3)
        put(img, bx, by + 1, 1)
        for k in range(ln):
            put(img, bx, by - k, 5 + min(k, 2))
        put(img, bx, by - ln, 8)
    for cx, cy in ((6, 7), (22, 20), (27, 4)):      # small clover sprigs
        for dx, dy in ((0, -1), (-1, 1), (1, 1)):
            put(img, cx + dx, cy + dy, 9)
        put(img, cx, cy, 10)
    # Tiny fallen sakura petals scattered lightly (Floaroma / Bellchime feel)
    for k, (cx, cy) in enumerate(((14, 12), (3, 25), (25, 28), (18, 3), (11, 21))):
        put(img, cx, cy, 12 if k % 2 else 11)
        put(img, cx + 1, cy, 14)
    return img, pal


def tex_tgrass():
    # Authentic Platinum emerald tall-grass ground bed (3D standing tuft cards sit on top of this)
    pal = [(26, 78, 52), (36, 98, 64), (48, 122, 74), (62, 146, 86), (78, 172, 98), (98, 194, 112), (124, 214, 130),
           (152, 232, 150), (182, 244, 172), (182, 136, 210), (218, 174, 238), (242, 214, 252), (214, 124, 174),
           (244, 168, 208), (255, 214, 234), (42, 110, 72)]
    img = ramp(0.32 + 0.48 * fbm(21), [1, 2, 3], 0.8)
    for row in range(4):
        y0 = row * 8 + 7
        for col in range(4):
            cx = col * 8 + (4 if row % 2 else 0) + 3.5
            for k in range(5):
                lean = (k - 2.0) * 0.22
                h = 7 - abs(k - 2.0) * 0.8
                for s in range(int(h) + 1):
                    f = s / h
                    x = cx + (k - 2.0) * 0.85 + lean * s * 0.5
                    y = y0 - s
                    shade = 3 + int(4 * f)
                    put(img, x, y, min(shade, 8))
                    if k in (0, 4) and s < h - 1:
                        put(img, x + (-1 if k == 0 else 1), y, 0)
            for dx in range(-3, 4):
                put(img, cx + dx, y0 + 1, 0)
    return img, pal


def tex_spiral_flw():
    # Lush spring flower-clearing bed under Clefairy (matches spring ev_grass!)
    pal = [(40, 106, 66), (54, 132, 80), (68, 156, 92), (84, 178, 104), (104, 200, 118), (132, 222, 142), (168, 240, 172),
           (186, 92, 150), (238, 142, 198), (255, 204, 234), (134, 110, 196), (186, 160, 238), (230, 216, 255),
           (212, 176, 86), (250, 224, 132), (255, 248, 214)]
    img = ramp(0.28 + 0.55 * fbm(31), [1, 2, 3, 4, 5])
    hues = {"pink": (7, 8, 9), "lav": (10, 11, 12), "gold": (13, 14, 15)}
    spots = [("pink", 6, 6), ("lav", 22, 10), ("gold", 14, 24), ("pink", 27, 26), ("lav", 3, 19), ("gold", 28, 3)]
    for name, cx, cy in spots:
        dk, md, br = hues[name]
        for ddx, ddy in ((0, -2), (-2, 0), (2, 0), (0, 2)):
            put(img, cx + ddx, cy + ddy, dk)
        for ddx, ddy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            put(img, cx + ddx, cy + ddy, md)
        put(img, cx - 1, cy - 1, br)
        put(img, cx, cy, 15)
    return img, pal


def tex_cobble():
    # Warm Floaroma / Canalave pale limestone flagstones with soft sage-moss grout (harmonizes with sprites & gates)
    pal = [(94, 116, 96), (112, 136, 112), (130, 154, 124), (148, 170, 136), (146, 142, 148), (162, 158, 164),
           (176, 172, 178), (190, 186, 190), (202, 198, 202), (214, 210, 214), (226, 222, 224), (238, 234, 236),
           (184, 182, 192), (196, 188, 196), (210, 204, 208), (170, 168, 178)]
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
            d = rbox(px, py, w / 2.0 - 0.8, 3.2, 2.0)
            lit = rbox(px + 0.8, py + 0.8, w / 2.0 - 0.8, 3.2, 2.0) - d
            m = d < best
            best = np.where(m, d, best)
            shade = np.where(m, lit, shade)
            tint = np.where(m, rng.randint(0, 3), tint)
            x += w
    inside = best < 0
    t = 0.48 + 0.28 * np.clip(-best / 2.6, 0, 1) - 0.34 * shade + 0.10 * (fbm(42) - 0.5)
    stones = [ramp(t, [5, 6, 7, 8, 9, 10]), ramp(t, [5, 15, 12, 7, 8, 9]), ramp(t, [5, 6, 13, 14, 8, 9])]
    img = np.where(tint == 0, stones[0], np.where(tint == 1, stones[1], stones[2]))
    img = np.where(inside & (pnoise(16, 43) > 0.88) & (best < -1.5), 11, img)
    grout = ramp(0.25 + 0.8 * fbm(44) + 0.25 * np.clip(best, 0, 1), [0, 1, 2, 3], 0.6)
    img = np.where(inside, img, grout)
    img = np.where((best >= 0) & (best < 0.6) & (shade < 0), 0, img)
    return img, pal


def tex_flw_decal():
    """Color-0-transparent (c0=1) 32x32 pastel blossom decal sheet (four 16x16 quadrants: pink, lav, cream, mix).
    Draws delicate Gen-4 style pixel flowers directly over tall grass with zero opaque square backdrop."""
    pal = [
        (0, 0, 0),        #  0 transparent (c0=1)
        (168,  84, 138),  #  1 sakura shadow
        (224, 128, 186),  #  2 sakura mid
        (248, 178, 218),  #  3 sakura bright
        (255, 224, 240),  #  4 sakura highlight
        (124,  96, 178),  #  5 wisteria shadow
        (174, 144, 226),  #  6 wisteria mid
        (216, 194, 248),  #  7 wisteria bright
        (240, 228, 255),  #  8 wisteria highlight
        (184, 156,  86),  #  9 cream-gold shadow
        (236, 212, 136),  # 10 cream-gold mid
        (252, 240, 186),  # 11 cream-gold bright
        (255, 252, 232),  # 12 warm white core
        ( 48, 114,  88),  # 13 tiny leaf dark
        ( 76, 152, 114),  # 14 tiny leaf mid
        (252, 236, 166),  # 15 golden pollen core
    ]
    img = np.zeros((N, N), dtype=int)

    def draw_flower(cx, cy, sh, md, br, hi, core=15, big=True):
        # Tiny green calyx leaves peeking diagonally under petals
        for dx, dy in ((-2, 2), (2, 2)):
            put(img, cx + dx, cy + dy, 13)
        put(img, cx - 1, cy + 2, 14)
        # Soft 5-petal pixel blossom (organic cross + diagonal tips, no square box)
        for dx, dy in ((0, -2), (-2, 0), (2, 0), (0, 2)):
            put(img, cx + dx, cy + dy, sh if dy > 0 else md)
        if big:
            for dx, dy in ((-1, -2), (1, -2), (-2, -1), (2, -1), (-2, 1), (2, 1)):
                put(img, cx + dx, cy + dy, md)
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            put(img, cx + dx, cy + dy, br)
        put(img, cx - 1, cy - 1, hi)
        put(img, cx, cy, core)

    # Quadrant 0 (0..16, 0..16): pink sakura cluster (main blossom + small bud)
    draw_flower(7, 8, 1, 2, 3, 4, core=15, big=True)
    draw_flower(12, 4, 1, 2, 3, 4, core=12, big=False)
    # Quadrant 1 (16..32, 0..16): soft wisteria-lavender cluster
    draw_flower(23, 8, 5, 6, 7, 8, core=12, big=True)
    draw_flower(19, 12, 5, 6, 7, 8, core=15, big=False)
    # Quadrant 2 (0..16, 16..32): warm starlight-cream cluster
    draw_flower(8, 24, 9, 10, 11, 12, core=15, big=True)
    draw_flower(4, 20, 1, 2, 3, 4, core=15, big=False)
    # Quadrant 3 (16..32, 16..32): mixed pink + lavender pair
    draw_flower(21, 22, 1, 2, 3, 4, core=15, big=False)
    draw_flower(27, 26, 5, 6, 7, 8, core=12, big=False)
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
    # Warm-cool weathered limestone courses with vibrant spring emerald overhanging grass lips (matches ev_grass!)
    pal = [(54, 52, 66), (76, 74, 90), (98, 96, 114), (122, 120, 138), (144, 142, 160), (166, 164, 180),
           (188, 186, 200), (208, 206, 218), (44, 112, 68), (62, 148, 86), (86, 182, 104), (118, 212, 126),
           (146, 228, 148), (178, 242, 170), (112, 110, 136), (156, 152, 174)]
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
    drip = (by <= (moss * 4.5).astype(int)) & (moss > 0.50)
    img = np.where(drip, ramp(moss - 0.25 + 0.18 * (by == 0), [8, 9, 10, 11]), img)
    img = np.where(drip & (by <= 1), np.where(by == 0, 13, 12), img)
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
    # Warm sunlit cream-moonstone plaza marble (matches Platinum's warm stone tones instead of cold purple!)
    pal = [(118, 114, 128), (140, 136, 150), (160, 156, 170), (178, 174, 188), (194, 190, 202), (208, 204, 216),
           (220, 216, 226), (232, 228, 236), (242, 238, 244), (252, 250, 252), (200, 192, 208), (190, 196, 208),
           (216, 210, 222), (210, 214, 224), (168, 172, 186), (234, 228, 238)]
    base = 0.62 + 0.28 * (fbm(91) - 0.5)
    img = np.where(pnoise(4, 92) > 0.55, ramp(base, [4, 10, 12, 6, 15, 8, 9]), ramp(base, [4, 11, 13, 6, 7, 8, 9]))
    vein = np.abs(np.sin(TAU * (X + 2 * Y) / N + 4.2 * fbm(93)))
    img = np.where(vein < 0.06, 3, np.where(vein < 0.14, np.where(BAYER > 0.15, 4, img), img))
    vein2 = np.abs(np.sin(TAU * (2 * X - Y) / N + 3.0 * fbm(94)))
    img = np.where((vein2 < 0.05) & (img > 4), 4, img)
    img = np.where((X == 31) | (Y == 31), 2, img)                           # crisp 2-tile carved stone flag seams
    img = np.where(((X == 0) | (Y == 0)) & (img > 4), 9, img)               # sunlit bevel edge
    return img, pal


def tex_gardevoir():
    # Eterna City Statue style: carved weathered cream-moonstone marble + inlaid pale celadon-jade hair + glowing rose-quartz heart!
    pal = [
        ( 76, 112,  98), (108, 148, 132), (144, 182, 166), (186, 216, 202),  # 0..3 carved pale celadon-jade marble (hair/crests)
        (158, 154, 166), (190, 186, 198), (220, 218, 226), (246, 244, 248),  # 4..7 carved pale cream-white marble (face/torso)
        (178,  66, 114), (226, 110, 154), (250, 164, 198), (255, 226, 238),  # 8..11 luminous rose-quartz crystal chest fin!
        (114, 112, 128), (148, 146, 162), (184, 182, 196), (222, 220, 232),  # 12..15 deeply carved marble gown folds w/ stone crevices
    ]
    img = np.zeros((N, N), int)
    q = (X >= 16).astype(int) + 2 * (Y >= 16).astype(int)
    lx, ly = X % 16, Y % 16
    # Subtle carved pixel chisel grain + stone shadow lines so the statue reads as DS carved stone, not smooth N64 cones
    chisel = 0.14 * (pnoise(16, 107) - 0.5)
    hair = 0.52 + 0.28 * np.sin(TAU * (lx * 2 + ly) / 16.0) * 0.55 + chisel - 0.02 * ly
    pearl = 0.66 + 0.26 * (fbm(102) - 0.5) + chisel
    rose = np.where(lx + ly < 15, 0.78 - 0.03 * ly, 0.45 + 0.02 * lx) + 0.12 * (lx == ly)
    # Crisp vertical fluted chisel lines on the marble gown swatch
    flute_line = (lx % 4 == 0)
    fold = np.where(flute_line, 0.18, 0.64 + 0.24 * (fbm(103) - 0.5) + chisel)
    img = np.where(q == 0, ramp(hair, [0, 1, 2, 3]), img)
    img = np.where(q == 1, ramp(pearl, [4, 5, 6, 7]), img)
    img = np.where(q == 2, ramp(rose, [8, 9, 10, 11]), img)
    img = np.where(q == 3, ramp(fold, [12, 13, 14, 15]), img)
    return img, pal


def tex_tuft_decal():
    """c0=1 transparent 32x32 sheet:
      (0..16,  0..16) tuft_a: standing 3D Platinum tall-grass blades w/ dark pixel outline
      (16..32, 0..16) tuft_b: standing tall-grass blades w/ tiny sakura petal tips
      (0..16, 16..32) edge:   overhanging spring grass-tuft fringe for stone-path & plaza borders
      (16..32,16..32) foam:   soft white/cyan shoreline foam edge resting on sea water
    """
    pal = [
        (0, 0, 0),        #  0 transparent (c0=1)
        ( 22,  66,  44),  #  1 dark grass pixel outline
        ( 38, 104,  62),  #  2 grass shadow
        ( 58, 144,  82),  #  3 grass mid
        ( 86, 184, 104),  #  4 grass bright
        (124, 216, 130),  #  5 grass sunlit tip
        (166, 240, 162),  #  6 grass highlight
        (214, 118, 174),  #  7 sakura petal mid
        (248, 180, 218),  #  8 sakura petal bright
        (255, 232, 244),  #  9 sakura white highlight
        (124, 198, 238),  # 10 foam pale blue
        (178, 230, 250),  # 11 foam aqua
        (228, 248, 255),  # 12 foam white-blue
        (250, 254, 255),  # 13 foam crisp white
        ( 52, 130,  78),  # 14 fringe mid-dark
        ( 96, 194, 112),  # 15 fringe bright
    ]
    img = np.zeros((N, N), dtype=int)

    def draw_blade_tuft(ox, oy, with_petal=False):
        # 5 lush upward-fanning DS tall-grass blades (base y=15, tips y=3..7) with dark outline
        blades = [(3, 9, -0.25), (6, 12, -0.10), (8, 13, 0.0), (10, 12, 0.12), (13, 9, 0.25)]
        for bx, bh, lean in blades:
            for s in range(bh):
                x = int(round(ox + bx + lean * s))
                y = oy + 15 - s
                if ox <= x < ox + 16 and oy <= y < oy + 16:
                    f = s / max(1, bh - 1)
                    col = 2 if f < 0.25 else (3 if f < 0.55 else (4 if f < 0.80 else 5))
                    img[y, x] = col
                    if x - 1 >= ox and img[y, x - 1] == 0:
                        img[y, x - 1] = 1
                    if x + 1 < ox + 16 and img[y, x + 1] == 0:
                        img[y, x + 1] = 1
            tip_x = int(round(ox + bx + lean * (bh - 1)))
            tip_y = oy + 15 - (bh - 1)
            if ox <= tip_x < ox + 16 and oy <= tip_y < oy + 16:
                img[tip_y, tip_x] = 6
        if with_petal:
            for px, py, c in ((ox + 5, oy + 5, 8), (ox + 6, oy + 5, 7), (ox + 11, oy + 6, 8), (ox + 11, oy + 5, 9)):
                img[py, px] = c

    draw_blade_tuft(0, 0, with_petal=False)
    draw_blade_tuft(16, 0, with_petal=True)

    # Bottom-left (0..16, 16..32): irregular tufted spring grass fringe along y=16..22 (hangs over path edge!)
    heights = [5, 7, 6, 4, 6, 8, 7, 5, 4, 7, 6, 5, 7, 8, 6, 4]
    for dx, hh in enumerate(heights):
        for dy in range(hh):
            y = 16 + dy
            col = 15 if dy < hh - 2 else (14 if dy == hh - 2 else 1)
            img[y, dx] = col

    # Bottom-right (16..32, 16..32): soft dithered shoreline water foam along y=16..22
    foam_h = [4, 5, 6, 5, 4, 3, 5, 6, 5, 4, 5, 6, 5, 4, 3, 4]
    for dx, fh in enumerate(foam_h):
        for dy in range(fh):
            y = 16 + dy
            col = 13 if dy < 2 else (12 if dy < fh - 1 else (11 if (dx + dy) % 2 == 0 else 10))
            img[y, 16 + dx] = col

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
            ("ev_flw_decal", tex_flw_decal), ("ev_tuft_decal", tex_tuft_decal),
            ("ev_cobble", tex_cobble), ("ev_water", tex_water), ("ev_bridge", tex_bridge), ("ev_cliff", tex_cliff),
            ("ev_blossom", tex_blossom), ("ev_marble", tex_marble), ("ev_gardevoir", tex_gardevoir),
            ("ev_crystal", tex_crystal), ("ev_mushroom", tex_mushroom)]


def pal_name(tex):
    if tex == "sea":
        return "sea"
    if tex == "tshadow":
        return "tshadow"
    if tex == "nhana":
        return "nhana"
    if tex in ("tree01", "conttree_t", "conttree_b"):
        return "ev_tree_pl"
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
    c0 = 1 if name in TRANSPARENT_TEX else 0
    tex = dict(name=name, fmt=3, w=N, h=N, c0=c0, data=data)
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
    # Extra 32-byte Sakura re-palette for stock Platinum tree01 / conttree_t / conttree_b
    new_p.append(dict(name="ev_tree_pl", colors=[nsbtx.bgr555(snap(c)) for c in SAKURA_TREE_PAL], pltt4=0))
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
        want_c0 = 1 if name in TRANSPARENT_TEX else 0
        if (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != (3, N, N, want_c0):
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
    table["sea"] = ("sea", (16, 16))
    table["tshadow"] = ("tshadow", (32, 32))
    table["nhana"] = ("nhana", (16, 16))
    table["tree01"] = ("ev_tree_pl", (64, 64))
    table["conttree_t"] = ("ev_tree_pl", (64, 64))
    table["conttree_b"] = ("ev_tree_pl", (64, 64))
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
