#!/usr/bin/env python3
"""Route 215 flooded-lowland texture set: map_texture_set_078 = stock map_texture_set_010 (git BASE_REV) + four
procedurally painted pixel-art textures (NumPy): periodic value noise, signed-distance blobs and plank/tread
patterns, quantised onto hand-tuned 16-colour BGR555 palettes with a 4x4 Bayer ordered dither, so every texel snaps
to Platinum's 16 px per tile grid.

Usage:
  ~/.venvs/desmume/bin/python tools/routes/r215/textures.py                dry run: table, VRAM, round-trip checks
  ~/.venvs/desmume/bin/python tools/routes/r215/textures.py --preview DIR  also write DIR/<texture>.png (x8 sheet too)
  ~/.venvs/desmume/bin/python tools/routes/r215/textures.py --write        write SET_REL (refuses if a check fails)

Idempotent: the base is always stock set 010 read from git, never the work tree, so reruns never append twice.

Textures (pltt16):
  r215_board   32x32 opaque. Wet dark-timber boardwalk planks: 4-texel planks running along v (across the walk), dark
               gaps, grain, nail heads on the two stringers, wet slate sheen, mud splashes and dark edge beams at
               v 0 / 31 (a 2-tile-wide deck maps v 0..1 across its width).
  r215_ruts    32x64 c0=1. Eclipse dual-tire truck ruts: two tracks (u 8 / u 24, 2 tiles across), each two treaded
               grooves with rain water pooled in them, crushed-grass and mud lips, splashed mud, dithered edges.
               Tiles along v.
  r215_puddle  64x64 c0=1. Four rain-soaked standing-water puddles (32x32 each = 2x2 tiles): reflective slate-blue
               water with overcast sky streaks, rain ripples, a mud rim and a dithered wet-grass fringe.
               PUDDLES gives the texel boxes; puddle_mask() the water texels (for the puddle tile behaviour).
  r215_crate   64x64 c0=1. Team Eclipse staging atlas (CRATE_UV): violet/slate crate side + top, strapped canvas tarp
               side + top, hazard stripe band, timber warning post, amber + violet work-lamp panels, and two
               dithered amber / violet lamp-glow pools (32x32).
"""
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import nsbtx  # noqa: E402

SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_078.nsbtx"
BASE_REV = "406c75f6a8"
BASE_SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_010.nsbtx"
VRAM_TARGET = 160 * 1024
NAME_MAX = 15

BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], float) + 0.5) / 16.0 - 0.5
TAU = 2 * np.pi

PUDDLES = {"a": (0, 0, 32, 32), "b": (32, 0, 64, 32), "c": (0, 32, 32, 64), "d": (32, 32, 64, 64)}
CRATE_UV = {"crate_s": (0, 0, 16, 16), "crate_t": (16, 0, 32, 16), "tarp_s": (32, 0, 48, 16),
            "tarp_t": (48, 0, 64, 16), "hazard": (0, 16, 16, 24), "metal": (0, 24, 16, 32),
            "post": (16, 16, 32, 32), "lamp_amber": (32, 16, 40, 32), "lamp_violet": (48, 16, 56, 32),
            "lamp_cap": (40, 16, 48, 24), "glow_amber": (0, 32, 32, 64), "glow_violet": (32, 32, 64, 64)}
TRANSPARENT = {"r215_ruts", "r215_puddle", "r215_crate"}


def grid(w, h):
    Y, X = np.mgrid[0:h, 0:w].astype(float)
    return X, Y


def bayer(w, h):
    X, Y = grid(w, h)
    return BAYER4[(Y % 4).astype(int), (X % 4).astype(int)]


def pnoise(w, h, cx, cy, seed):
    """Periodic value noise over a w x h texture: a cx x cy lattice, smoothstep-bilinear, wrapping."""
    rng = np.random.RandomState(seed)
    g = rng.rand(cy, cx)
    X, Y = grid(w, h)
    fx, fy = X * cx / w, Y * cy / h
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - x0, fy - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    x0, y0, x1, y1 = x0 % cx, y0 % cy, (x0 + 1) % cx, (y0 + 1) % cy
    a = g[y0, x0] * (1 - tx) + g[y0, x1] * tx
    b = g[y1, x0] * (1 - tx) + g[y1, x1] * tx
    return a * (1 - ty) + b * ty


def fbm(w, h, seed, octs=((4, 0.55), (8, 0.3), (16, 0.15))):
    return sum(wt * pnoise(w, h, c, c, seed + k * 101) for k, (c, wt) in enumerate(octs))


def ramp(t, idx, B, dither=1.0):
    n = len(idx)
    v = np.clip(np.floor(np.clip(t, 0, 1) * (n - 1) + 0.5 + B * dither), 0, n - 1).astype(int)
    return np.array(idx)[v]


def snap(c):
    return tuple(int(v) >> 3 << 3 for v in c)


# ---------------------------------------------------------------------------------------------------------------
# r215_board
# ---------------------------------------------------------------------------------------------------------------

def tex_board():
    pal = [(30, 24, 26), (50, 40, 40), (76, 62, 54), (96, 78, 64), (114, 94, 74), (132, 110, 86), (150, 128, 100),
           (172, 150, 120), (112, 124, 136), (156, 170, 184), (74, 62, 48), (100, 82, 62), (40, 40, 46),
           (190, 190, 198), (72, 88, 66), (56, 60, 70)]
    w = h = 32
    X, Y = grid(w, h)
    B = bayer(w, h)
    rng = np.random.RandomState(215)
    plank = (X // 4).astype(int)                       # 8 planks per repeat, each 4 texels (4 per tile)
    tone = rng.rand(8)[plank] * 0.30 - 0.12
    grain = pnoise(w, h, 8, 2, 7) * 0.6 + pnoise(w, h, 32, 4, 9) * 0.4    # stretched along v (across the walk)
    t = 0.54 + tone + (grain - 0.5) * 0.45
    t -= 0.10 * (X % 4 == 0)                           # plank west edge in shade
    t += 0.08 * (X % 4 == 2)
    img = ramp(t, [2, 3, 4, 5, 6, 7], B, 0.9)
    img[(X % 4) == 3] = 1                              # gaps between planks
    img[((X % 4) == 3) & (pnoise(w, h, 8, 8, 3) > 0.62)] = 0
    # wet sheen: overcast sky caught on the soaked boards
    wet = pnoise(w, h, 4, 4, 21)
    sheen = (wet > 0.60) & ((X % 4) != 3) & (B < (wet - 0.60) * 2.4 - 0.25) & ((X.astype(int) * 7 + Y.astype(int)) % 3 != 0)
    img[sheen] = 8
    img[sheen & (wet > 0.78) & ((X % 4) == 1)] = 9
    # edge beams (deck edges, v 0..1 and 30..31) with a dark outline
    for y in (1, 30):
        img[y, :] = ramp(0.35 + 0.25 * pnoise(w, 1, 8, 1, 31 + y)[0], [3, 4, 5], B[y], 0.8)
    img[0, :] = 0
    img[31, :] = 0
    img[2, :] = np.where(X[2] % 4 == 3, 1, 2)
    img[29, :] = np.where(X[29] % 4 == 3, 1, 2)
    # nail heads on the stringers (v 3/4 and 27/28) and the middle cross beam (v 15/16)
    for vy in (4, 27, 15):
        for px in range(1, 32, 4):
            if vy == 15 and (px // 4) % 2:
                continue
            img[vy, px] = 12
            img[vy - 1, px] = 13
    # mud splashed up from the flooded ground at the deck edges, moss in the gaps
    mud = pnoise(w, h, 16, 16, 41)
    edge = np.minimum(Y, 31 - Y)
    splash = (edge >= 2) & (edge <= 6) & (mud + B * 0.5 > 0.80 + edge * 0.03)
    img[splash] = np.where(mud[splash] > 0.9, 10, 11)
    img[((X % 4) == 3) & (mud > 0.7) & (edge > 4)] = 14
    img[(img == 1) & (wet > 0.7)] = 15
    return img, pal


# ---------------------------------------------------------------------------------------------------------------
# r215_ruts
# ---------------------------------------------------------------------------------------------------------------

RUTS_H = 64


def tex_ruts():
    """32 x 64: u across the 2-tile lane, v along it (4 tiles per repeat)."""
    pal = [(255, 0, 255), (46, 34, 28), (64, 48, 38), (84, 64, 48), (104, 80, 60), (124, 98, 72), (146, 118, 88),
           (100, 140, 150), (138, 180, 190), (196, 224, 232), (58, 120, 72), (80, 150, 92), (108, 176, 110),
           (74, 56, 44), (234, 244, 248), (94, 72, 54)]
    w, h = 32, RUTS_H
    X, Y = grid(w, h)
    B = bayer(w, h)
    img = np.zeros((h, w), int)
    mud = fbm(w, h, 51, ((4, 0.5), (8, 0.3), (16, 0.2)))
    speck = pnoise(w, h, 16, 32, 57)
    for k, c in enumerate((8.0, 24.0)):
        wob = 0.8 * np.sin(TAU * Y / h + 0.7 + k) + 0.45 * np.sin(TAU * 3 * Y / h + 2.1 + 2 * k)
        width = 5.4 + 1.1 * np.sin(TAU * 2 * Y / h + 1.3 * k) + 0.8 * (pnoise(w, h, 2, 8, 70 + k) - 0.5) * 2
        d = X - (c + wob)
        ad = np.abs(d)
        # outer lip: churned mud then crushed grass, dithered out to transparent
        lip = (ad <= width + 2.2) & (ad > width - 0.5)
        fade = (ad - (width - 0.5)) / 2.7
        keep = lip & (B + 0.5 > fade)
        img[keep] = np.where(mud[keep] > 0.55, 5, np.where(mud[keep] > 0.40, 12, 11))
        img[keep & (ad > width + 0.8) & (mud < 0.5)] = 10
        # the churned mud bed
        bed = ad <= width - 0.5
        img[bed] = ramp(0.50 + (mud[bed] - 0.5) * 1.0 + (speck[bed] - 0.5) * 0.45, [2, 3, 4, 15, 5], B[bed], 1.0)
        img[bed & (ad > width - 1.5) & (d < 0)] = 6          # sunlit west lip of the rut
        img[bed & (ad > width - 1.5) & (d > 0)] = 13         # shaded east wall
        # dual-tyre grooves broken by tread speckle
        groove = bed & (np.abs(ad - width * 0.42) <= 0.85)
        img[groove] = np.where(speck[groove] + B[groove] * 0.5 > 0.60, 13, 2)
        img[groove & (speck < 0.32)] = 1
        # standing rain water in the deepest stretches
        wv = pnoise(w, h, 2, 6, 61 + k)
        water = bed & (ad < width - 1.2) & (wv > 0.60)
        img[water] = 7
        img[water & (B > -0.15) & (wv > 0.64)] = 8
        img[water & (B > 0.38) & (speck > 0.55)] = 9
        img[water & (B > 0.44) & ((Y.astype(int) % 7) == 3) & (wv > 0.68)] = 14
    # splashed mud flecks between and beside the tracks
    rng = np.random.RandomState(77)
    for _ in range(46):
        x, y = rng.randint(0, w), rng.randint(0, h)
        if img[y, x] == 0 and (abs(x - 16) < 4 or x < 2 or x > 29):
            img[y, x] = 15 if rng.rand() < 0.6 else 3
            if rng.rand() < 0.5 and img[(y + 1) % h, x] == 0:
                img[(y + 1) % h, x] = 13
    return img, pal


# ---------------------------------------------------------------------------------------------------------------
# r215_puddle
# ---------------------------------------------------------------------------------------------------------------

PUD_SHAPES = {"a": (13.0, 11.0, 0.0, 11), "b": (14.0, 9.5, 0.35, 23), "c": (11.0, 13.0, -0.25, 37),
              "d": (14.5, 12.0, 0.15, 53)}


def puddle_sdf(key):
    """Signed distance (texels, negative inside) of puddle `key` over its 32x32 cell."""
    rx, ry, rot, seed = PUD_SHAPES[key]
    X, Y = grid(32, 32)
    dx, dy = X + 0.5 - 16, Y + 0.5 - 16
    cr, sr = np.cos(rot), np.sin(rot)
    u, v = dx * cr + dy * sr, -dx * sr + dy * cr
    ang = np.arctan2(v, u)
    rng = np.random.RandomState(seed)
    wob = 1 + 0.10 * np.sin(3 * ang + rng.rand() * TAU) + 0.07 * np.sin(5 * ang + rng.rand() * TAU) + \
        0.05 * np.sin(2 * ang + rng.rand() * TAU)
    r = np.sqrt((u / rx) ** 2 + (v / ry) ** 2)
    return (r / wob - 1.0) * min(rx, ry)


def puddle_mask(key):
    return puddle_sdf(key) < -0.5


def tex_puddle():
    pal = [(255, 0, 255), (64, 112, 124), (80, 132, 142), (98, 150, 158), (116, 168, 174), (138, 186, 194),
           (166, 206, 216), (204, 230, 238), (238, 248, 252), (104, 74, 84), (138, 98, 108), (168, 128, 126),
           (60, 150, 98), (84, 178, 116), (50, 88, 98), (132, 196, 226)]
    img = np.zeros((64, 64), int)
    B = bayer(32, 32)
    X, Y = grid(32, 32)
    for key, (x0, y0, x1, y1) in PUDDLES.items():
        sd = puddle_sdf(key)
        rx, ry, rot, seed = PUD_SHAPES[key]
        cell = np.zeros((32, 32), int)
        n = pnoise(32, 32, 8, 8, seed)
        # wet-grass fringe, dithered out
        fringe = (sd >= 0.4) & (sd < 3.2) & (B + 0.5 > (sd - 0.4) / 2.8)
        cell[fringe] = np.where(n[fringe] > 0.5, 13, 12)
        # mud rim
        rim = (sd >= -1.0) & (sd < 0.9 + (n - 0.5) * 1.4)
        cell[rim] = np.where(sd[rim] < -0.2, 9, np.where(n[rim] > 0.55, 11, 10))
        inside = sd < -1.0
        # water: darker toward the middle (depth), sky reflection streaks along u, shallow murk at the edge
        depth = np.clip(-sd / (min(rx, ry) * 0.8), 0, 1)
        streak = 0.5 + 0.5 * np.sin(TAU * (Y + 0.35 * X) / 9.0 + seed)
        t = 0.78 - 0.42 * depth + 0.20 * (streak - 0.5) + 0.12 * (n - 0.5) - 0.10 * (Y / 32.0)
        cell[inside] = ramp(t[inside], [1, 2, 3, 4, 5, 6], B[inside], 1.0)
        shallow = inside & (sd > -2.2)
        cell[shallow] = np.where(B[shallow] > 0, 15, 4)
        # outline ring on the north edge so the water reads as sunk below the grass
        north = inside & (sd > -1.5) & (Y < 13)
        cell[north] = 14
        # sky glints and rain ripples
        rng = np.random.RandomState(seed + 5)
        for _ in range(4):
            cx, cy = rng.randint(9, 23), rng.randint(10, 22)
            rr = rng.choice([1.6, 2.2])
            ring = inside & (sd < -2.5) & (np.abs(np.hypot(X + 0.5 - cx, (Y + 0.5 - cy) * 1.8) - rr) < 0.45)
            cell[ring & (B > -0.2)] = 7
            if cell[cy, cx] != 0 and sd[cy, cx] < -2.5:
                cell[cy, cx] = 8
        gl = inside & (sd < -3.0) & (streak > 0.93) & (B > 0.2)
        cell[gl] = 7
        img[y0:y1, x0:x1] = cell
    return img, pal


# ---------------------------------------------------------------------------------------------------------------
# r215_crate
# ---------------------------------------------------------------------------------------------------------------

def tex_crate():
    pal = [(255, 0, 255), (22, 18, 30), (46, 38, 62), (70, 58, 94), (98, 84, 126), (54, 62, 78), (88, 96, 114),
           (140, 148, 164), (204, 150, 40), (250, 206, 92), (255, 242, 190), (150, 96, 214), (210, 170, 250),
           (36, 32, 34), (86, 64, 48), (128, 98, 66)]
    img = np.zeros((64, 64), int)
    B = bayer(64, 64)
    n = fbm(64, 64, 91)

    def cell(key):
        x0, y0, x1, y1 = CRATE_UV[key]
        return slice(y0, y1), slice(x0, x1), x1 - x0, y1 - y0

    # crate side: violet slate boards in a darker frame, a muted amber eclipse ring stencil
    ys, xs, w, h = cell("crate_s")
    X, Y = grid(w, h)
    c = ramp(0.45 + (n[ys, xs] - 0.5) * 0.7 + 0.15 * ((Y.astype(int) // 4) % 2), [2, 3, 4], B[ys, xs], 0.9)
    c[(Y.astype(int) % 4) == 3] = 2
    frame = (X < 2) | (X > 13) | (Y < 2) | (Y > 13)
    c[frame] = 5
    c[(X == 1) | (X == 14) | (Y == 1) | (Y == 14)] = 6
    diag = np.abs(X - Y) < 0.8
    c[diag & ~frame] = 5
    r = np.hypot(X + 0.5 - 8, Y + 0.5 - 8)
    ring = (np.abs(r - 3.2) < 0.75) & ~((X > 8.5) & (Y < 7.5))
    c[ring] = 8
    c[(np.abs(r - 3.2) < 0.75) & (X > 8.5) & (Y < 7.5)] = 2
    c[(X == 0) | (X == 15) | (Y == 0) | (Y == 15)] = 1
    img[ys, xs] = c
    # crate top: planks with corner brackets and bolts
    ys, xs, w, h = cell("crate_t")
    X, Y = grid(w, h)
    c = ramp(0.5 + (n[ys, xs] - 0.5) * 0.6 + 0.12 * ((X.astype(int) // 5) % 2), [3, 4, 3], B[ys, xs], 0.9)
    c[(X.astype(int) % 5) == 4] = 2
    br = ((X < 3) | (X > 12)) & ((Y < 3) | (Y > 12))
    c[br] = 6
    for bx, by in ((1, 1), (14, 1), (1, 14), (14, 14)):
        c[by, bx] = 7
    c[(X == 0) | (X == 15) | (Y == 0) | (Y == 15)] = 1
    img[ys, xs] = c
    # tarp side: slate-violet canvas folds, a yellow ratchet strap, wet sheen
    ys, xs, w, h = cell("tarp_s")
    X, Y = grid(w, h)
    fold = 0.5 + 0.5 * np.sin(TAU * (X + 0.4 * Y) / 6.0)
    c = ramp(0.25 + 0.55 * fold * (0.7 + 0.6 * n[ys, xs]), [2, 5, 3, 6], B[ys, xs], 1.0)
    c[(np.abs(X - 10.5) < 1.0)] = 8
    c[(np.abs(X - 10.5) < 1.0) & (Y.astype(int) % 5 == 2)] = 9
    c[(np.abs(X - 10.5) < 1.0) & (Y > 11) & (Y < 14)] = 7
    c[(Y == 15)] = 1
    c[(Y == 0)] = 2
    img[ys, xs] = c
    # tarp top: canvas with two crossing straps and grommets
    ys, xs, w, h = cell("tarp_t")
    X, Y = grid(w, h)
    wr = 0.5 + 0.5 * np.sin(TAU * (X - Y) / 7.0)
    c = ramp(0.3 + 0.5 * wr * (0.7 + 0.6 * n[ys, xs]), [5, 3, 6], B[ys, xs], 1.0)
    c[np.abs(X - 5.5) < 1.0] = 8
    c[np.abs(Y - 9.5) < 1.0] = 8
    c[(np.abs(X - 5.5) < 1.0) & (np.abs(Y - 9.5) < 1.0)] = 7
    for gx, gy in ((1, 1), (14, 1), (1, 14), (14, 14)):
        c[gy, gx] = 7
    c[(X == 0) | (X == 15) | (Y == 0) | (Y == 15)] = 1
    img[ys, xs] = c
    # hazard stripe band (amber / black diagonals) and dark riveted metal
    ys, xs, w, h = cell("hazard")
    X, Y = grid(w, h)
    c = np.where(((X + Y).astype(int) // 3) % 2 == 0, 9, 13)
    c[((X + Y).astype(int) // 3) % 2 == 0 & (B[ys, xs] > 0.3)] = 8
    c[(Y == 0) | (Y == 7)] = 1
    img[ys, xs] = c
    ys, xs, w, h = cell("metal")
    X, Y = grid(w, h)
    c = ramp(0.4 + (n[ys, xs] - 0.5) * 0.8, [5, 6, 5], B[ys, xs], 0.9)
    c[(Y == 1) & (X.astype(int) % 4 == 1)] = 7
    c[(Y == 0) | (Y == 7)] = 1
    img[ys, xs] = c
    # timber warning post: wet wood with a hazard collar at the top
    ys, xs, w, h = cell("post")
    X, Y = grid(w, h)
    c = ramp(0.45 + (pnoise(16, 16, 2, 8, 5) - 0.5) * 0.7, [14, 15, 14], B[ys, xs], 0.9)
    c[(X.astype(int) % 4) == 0] = 14
    c[Y < 5] = np.where((((X + Y).astype(int) // 2) % 2) == 0, 9, 13)[Y < 5]
    c[(Y == 5)] = 1
    c[(X == 0) | (X == 15)] = 1
    img[ys, xs] = c
    # work-lamp panels (unlit material): hot core, coloured lens, dark housing
    for key, ramp_idx in (("lamp_amber", [8, 9, 10]), ("lamp_violet", [11, 12, 10])):
        ys, xs, w, h = cell(key)
        X, Y = grid(w, h)
        r = np.hypot((X + 0.5 - 4) / 3.5, (Y + 0.5 - 6) / 5.0)
        c = ramp(1.0 - r, ramp_idx, B[ys, xs], 0.8)
        c[r > 1.0] = 1
        c[Y > 11] = 5
        c[(Y > 11) & (X.astype(int) % 3 == 1)] = 6
        c[Y == 15] = 1
        img[ys, xs] = c
    ys, xs, w, h = cell("lamp_cap")
    X, Y = grid(w, h)
    c = np.full((h, w), 5)
    c[Y < 2] = 6
    c[(Y == 0) | (X == 0) | (X == 7)] = 1
    img[ys, xs] = c
    # lamp glow pools: dithered radial falloff to transparent
    for key, idx in (("glow_amber", [8, 9, 10]), ("glow_violet", [11, 12, 10])):
        ys, xs, w, h = cell(key)
        X, Y = grid(w, h)
        r = np.hypot(X + 0.5 - 16, (Y + 0.5 - 16) * 1.15) / 15.5
        c = ramp(np.clip(1.15 - r * 1.25, 0, 1), idx, B[ys, xs], 0.9)
        keep = B[ys, xs] + 0.5 > r ** 1.4
        c[~keep | (r > 1)] = 0
        img[ys, xs] = c
    return img, pal


TEXTURES = [("r215_board", tex_board), ("r215_ruts", tex_ruts), ("r215_puddle", tex_puddle),
            ("r215_crate", tex_crate)]


def pal_name(tex):
    return tex + "_pl"


def generate():
    out = []
    for name, fn in TEXTURES:
        idx, pal = fn()
        idx = np.asarray(idx, int)
        assert idx.min() >= 0 and idx.max() < 16, name
        assert len(pal) == 16, name
        out.append((name, idx, [snap(c) for c in pal]))
    return out


def encode(name, idx, pal):
    h, w = idx.shape
    flat = idx.reshape(-1).tolist()
    data = bytes(flat[i] | flat[i + 1] << 4 for i in range(0, len(flat), 2))
    tex = dict(name=name, fmt=3, w=w, h=h, c0=1 if name in TRANSPARENT else 0, data=data)
    return tex, dict(name=pal_name(name), colors=[nsbtx.bgr555(c) for c in pal], pltt4=0)


def git_bytes(rev, rel):
    return subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{rel}"], check=True, capture_output=True).stdout


def build_set():
    fails = []
    base_bytes = git_bytes(BASE_REV, BASE_SET_REL)
    base = nsbtx.parse(base_bytes)
    names = {t["name"] for t in base["textures"]} | {p["name"] for p in base["palettes"]}
    gen = generate()
    new_t, new_p, rows = [], [], []
    for name, idx, pal in gen:
        t, p = encode(name, idx, pal)
        for a in (t["name"], p["name"]):
            if a in names:
                fails.append(f"{a} clashes with a stock set-010 entry")
            if len(a) > NAME_MAX:
                fails.append(f"{a} is longer than {NAME_MAX} characters")
        new_t.append(t)
        new_p.append(p)
        rows.append((name, p["name"], f"{t['w']}x{t['h']}", len(t["data"]), 32, t["c0"],
                     len(set(idx.reshape(-1).tolist()))))
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
        if not t2 or t2["data"] != t["data"] or (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != \
                (t["fmt"], t["w"], t["h"], t["c0"]):
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
        if (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != (3, idx.shape[1], idx.shape[0], 1 if name in TRANSPARENT else 0):
            fails.append(f"{name}: format/size changed in the round trip")
        if [list(r) for r in ind] != idx.tolist():
            fails.append(f"{name}: texel indices differ after the round trip")
        want = [nsbtx.rgb(nsbtx.bgr555(pal[i])) for i in idx.reshape(-1).tolist()]
        got = [tuple(px[:3]) for row in rgba for px in row]
        if got != want:
            fails.append(f"{name}: decoded colours differ from the BGR555 palette")
    if nsbtx.build(so["textures"] and [dict(t) for t in so["textures"]], [dict(p) for p in so["palettes"]],
                   pal_flag=so["header"]["pal_flag"]) is None:
        fails.append("rebuild failed")
    if len(so["textures"]) != len(sb["textures"]) + len(new_t) or \
            len(so["palettes"]) != len(sb["palettes"]) + len(new_p):
        fails.append("entry count mismatch")
    vb, vo = nsbtx.vram_usage(sb), nsbtx.vram_usage(so)
    if sum(vo) > VRAM_TARGET:
        fails.append(f"set VRAM {sum(vo)} B > target {VRAM_TARGET}")
    table = {t["name"]: {"size": [t["w"], t["h"]]} for t in so["textures"]}
    return dict(bytes=out, rows=rows, fails=fails, vram=(vb, vo), table=table, generated=gen,
                palettes={p["name"] for p in so["palettes"]},
                stock_textures=len(sb["textures"]), stock_palettes=len(sb["palettes"]))


def write_preview(d, gen):
    from PIL import Image
    os.makedirs(d, exist_ok=True)
    tiles = []
    for name, idx, pal in gen:
        h, w = idx.shape
        img = Image.new("RGBA", (w, h))
        img.putdata([(0, 0, 0, 0) if (name in TRANSPARENT and i == 0) else pal[i] + (255,)
                     for i in idx.reshape(-1).tolist()])
        img.save(os.path.join(d, name + ".png"))
        tiles.append(img)
    W = sum(t.width * 8 + 8 for t in tiles)
    sheet = Image.new("RGBA", (W, 64 * 8), (92, 170, 110, 255))
    x = 0
    for t in tiles:
        big = t.resize((t.width * 8, t.height * 8), Image.NEAREST)
        sheet.alpha_composite(big, (x, 0))
        x += t.width * 8 + 8
    sheet.save(os.path.join(d, "r215_textures_sheet.png"))


def report(res):
    vb, vo = res["vram"]
    print(f"map_texture_set_078 = git {BASE_REV}:{BASE_SET_REL} ({res['stock_textures']} textures, "
          f"{res['stock_palettes']} palettes) + {len(res['rows'])} Route 215 textures")
    print(f"{'texture':12s} {'palette':15s} {'size':6s} {'texel B':>7s} {'pal B':>5s} {'c0':>3s} {'colours':>7s}")
    for name, pn, size, tb, pb, c0, nc in res["rows"]:
        print(f"{name:12s} {pn:15s} {size:6s} {tb:7d} {pb:5d} {c0:3d} {nc:7d}")
    print(f"VRAM: {sum(vb)} -> {sum(vo)} B ({sum(vo) / 1024:.1f} KB; texels {vb[0]} -> {vo[0]}, palettes {vb[1]} -> "
          f"{vo[1]}); target < {VRAM_TARGET // 1024} KB")


def main():
    args = sys.argv[1:]
    res = build_set()
    report(res)
    if "--preview" in args:
        write_preview(args[args.index("--preview") + 1], res["generated"])
    for f in res["fails"]:
        print("FAIL", f)
    if not res["fails"]:
        print("PASS every appended texture round-trips (texels + BGR555 colours); stock textures/palettes "
              "unchanged; VRAM within target")
    if "--write" in args:
        if res["fails"]:
            print("refusing to write: checks failed")
            return 1
        open(os.path.join(ROOT, SET_REL), "wb").write(res["bytes"])
        print("wrote", SET_REL, len(res["bytes"]), "B")
    return 1 if res["fails"] else 0


if __name__ == "__main__":
    sys.exit(main())
