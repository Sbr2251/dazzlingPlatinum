#!/usr/bin/env python3
"""Routes 206-207 texture kit (v2): clean pixel-art textures appended to stock set 007 to make map_texture_set_079
(append-only; the stock set is read from git at common.BASE_REV, so reruns are idempotent).

Style (after Solaceon Town's excavation props): bold silhouettes at the field's true 16 texels per tile, flat
two/three-tone cel shading with a top-left key light, dark pixel outlines. Prop cells are hand-drawn at the size they
appear on screen (the DS has no mipmaps: a 32-texel crate face on a 7-pixel crate turns to shimmering mush). No
ordered dithering and no per-texel noise anywhere.

  ec_ruts       32x32 pltt16 c0=1  one sculpted wheel track (cols 0..15, tileable along v, 2 tiles per period) and
                                   its fade-out end piece (cols 16..31, v 0 = full track -> v 1 = gone)
  ec_crate      64x64 pltt16       hand-drawn cells at true size: crate sides/lids (12x12 and 8x8), manifest
                                   clipboard, hazard label, pallet and steel strips, shard-containment frame front
                                   (12x24) and side (6x24), canister case (15x10)
  ec_banner     64x32 pltt16 c0=1  Team Eclipse banner (16x32) | pennant (16x32) | violet canvas tarp (16x16)
  ec_barricade  32x32 pltt16 c0=1  hazard-stripe plank (32x4), CLOSED board (16x5), traffic cone (8x12),
                                   steel chain-link fence panel (16x16)
  ec_light      16x32 pltt16 c0=1  tripod work lamp card (clean glowing housing)
  ec_glow       64x32 a5i3         true per-texel alpha: soft radial light pool (cols 0..31) and a soft contact
                                   shadow (cols 32..63); palettes ec_glow_amb_pl (warm lamp light), ec_glow_vio_pl
                                   (violet shard glow), ec_glow_shd_pl (shadow)

NumPy is needed: run with ~/.venvs/desmume/bin/python.

Usage:
  ~/.venvs/desmume/bin/python tools/routes/r206_207/textures.py [--preview DIR] [--write]
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as K  # noqa: E402
import nsbtx  # noqa: E402

import numpy as np  # noqa: E402


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def edge_of(m):
    """Texels of mask m that touch a texel outside m (4-neighbour)."""
    p = np.pad(m, 1, constant_values=False)
    inner = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return m & ~inner


# ---------------------------------------------------------------------------------------------------------------
# palettes (16 colours each; index 0 is transparent where c0=1)
# ---------------------------------------------------------------------------------------------------------------

PAL_RUTS = [(0, 0, 0), (118, 78, 60), (146, 100, 78), (134, 90, 70), (170, 124, 98), (218, 184, 152),
            (198, 160, 128), (104, 68, 52)] + [(146, 100, 78)] * 8
PAL_CRATE = [(34, 24, 30), (104, 64, 38), (152, 98, 56), (198, 142, 82), (230, 184, 120), (66, 74, 96),
             (120, 132, 154), (178, 188, 206), (230, 236, 244), (60, 24, 104), (116, 54, 190), (170, 110, 240),
             (214, 172, 255), (248, 238, 255), (240, 196, 44), (92, 86, 136)]
PAL_BANNER = [(0, 0, 0), (28, 18, 44), (72, 36, 122), (106, 58, 170), (142, 94, 208), (176, 136, 234),
              (112, 114, 134), (172, 174, 192), (226, 228, 240), (36, 24, 54), (252, 238, 196), (74, 70, 112),
              (104, 98, 146), (138, 132, 178), (200, 174, 122), (134, 108, 72)]
PAL_BARR = [(0, 0, 0), (26, 22, 26), (58, 56, 62), (106, 108, 118), (166, 168, 178), (176, 124, 12),
            (240, 194, 30), (255, 232, 110), (176, 60, 14), (232, 104, 26), (255, 156, 72), (240, 240, 234),
            (186, 186, 182), (196, 34, 34), (120, 18, 24), (255, 250, 214)]
PAL_LIGHT = [(0, 0, 0), (24, 22, 30), (58, 60, 72), (100, 104, 120), (152, 156, 172), (204, 208, 220),
             (196, 120, 36), (246, 176, 70), (255, 222, 138), (255, 250, 222)] + [(24, 22, 30)] * 6
# a5i3 palettes: 8 colours, index 7 = pool centre
PAL_GLOW_AMB = [(236, 150, 60), (242, 164, 72), (246, 178, 86), (250, 192, 104), (252, 206, 124), (254, 220, 146),
                (255, 232, 170), (255, 242, 196)]
PAL_GLOW_VIO = [(120, 64, 214), (132, 76, 222), (146, 92, 230), (160, 110, 238), (176, 130, 244), (192, 152, 250),
                (210, 178, 255), (228, 206, 255)]
PAL_GLOW_SHD = [(26, 20, 30)] * 8


# ---------------------------------------------------------------------------------------------------------------
# ec_ruts: one wheel track across u (16 texels = 1 tile), running along v; tileable in v (period 32 = 2 tiles)
# ---------------------------------------------------------------------------------------------------------------

def _track(y, x, hw, lip, dash=None):
    """Index grid of one sculpted wheel track pressed into the ground: groove half-width hw, dust-rim width lip
    (both per row, texels). Two-tone floor (tread bars every 4 texels), the west wall in the shadow of its rim
    (light from the top-left), the east wall lit, a thin warm dust rim pushed up on both sides, broken into
    clumps along the track so it never reads as a rail."""
    c = 7.5 + 0.35 * np.sin(2 * math.pi * y / 32.0) + 0.2 * np.sin(2 * math.pi * (2 * y + 7) / 32.0)
    d = x + 0.5 - c
    a = np.abs(d)
    img = np.zeros(x.shape, int)
    groove = a < hw
    img[groove] = 2                                               # floor
    tread = groove & (((y + np.floor(a * 0.7).astype(int)) % 4) < 2) & (a < hw - 0.8)
    img[tread] = 3                                                # tread bars (second tone)
    img[groove & (d < 0) & (a >= hw - 1.0)] = 1                   # west wall, in shadow
    img[groove & (d < 0) & (a >= hw - 1.0) & (hw > 2.4)] = 7      # deepest shadow line where the groove is full
    img[groove & (d > 0) & (a >= hw - 1.0)] = 4                   # east wall, lit
    ph = (d > 0) * 2.3
    clump = (np.sin(2 * math.pi * 3 * (y + 0.5) / 32.0 + ph) + 0.8 * np.sin(2 * math.pi * 5 * (y + 0.5) / 32.0 + 1.3 * ph)
             > -0.55)
    rim = (a >= hw) & (a < hw + lip) & clump
    img[rim & (d < 0)] = 6                                        # west rim
    img[rim & (d > 0)] = 5                                        # east rim catches the light
    if dash is not None:
        img[~dash] = 0
    return img


def tex_ruts():
    W, H = 32, 32
    img = np.zeros((H, W), int)
    y, x = np.mgrid[0:H, 0:16]
    img[:, 0:16] = _track(y, x, np.full(y.shape, 3.0), np.full(y.shape, 1.0))
    # fade-out: v 0 joins the full track; the lips flatten first, then the groove narrows and breaks into the last
    # tread prints (clean dashes) before it is gone at v 1
    t = (y + 0.5) / H
    hw = 3.0 * (1 - smoothstep(0.25, 0.95, t))
    lip = 1.0 * (1 - smoothstep(0.05, 0.5, t))
    dash = (t < 0.55) | ((y % 4) < 3 - (t > 0.8))
    img[:, 16:32] = _track(y, x, hw, lip, dash) * (hw[..., :] > 0.55)
    return img, PAL_RUTS


RUTS_UV = {"full": (0.0, 0.5), "fade": (0.5, 1.0)}           # u ranges


# ---------------------------------------------------------------------------------------------------------------
# ec_crate (64x64)
# ---------------------------------------------------------------------------------------------------------------

def _emblem(cell, cx, cy, r, ring, dark, lit):
    """Eclipse emblem: a dark disc inside a pale ring, a thin bright crescent of the sun on its lower-left limb."""
    h, w = cell.shape
    y, x = np.mgrid[0:h, 0:w]
    d = np.hypot(x + 0.5 - cx, y + 0.5 - cy)
    disc = d < r - 1.0
    cell[disc] = dark
    d2 = np.hypot(x + 0.5 - (cx + r * 0.25), y + 0.5 - (cy - r * 0.25))
    cell[disc & (d2 > r - 1.3)] = lit
    cell[(d >= r - 1.0) & (d < r + 0.2)] = ring


# ---------------------------------------------------------------------------------------------------------------
# hand-drawn cells at the field's true density (16 texels per tile, no mipmaps on the DS: a prop face shows about
# as many texels as it covers screen pixels, so nothing shimmers or turns to mush when minified)
# ---------------------------------------------------------------------------------------------------------------

def paint(img, x0, y0, rows, keys):
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch != " ":
                img[y0 + dy, x0 + dx] = keys[ch]


# ec_crate keys: 0 outline, 1/2/3/4 wood dark..highlight, 5/6/7/8 steel dark..highlight, 9 crystal outline,
# A/B/C crystal dark/mid/light, W crystal highlight, Y hazard yellow, g frame glass
CK = {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "A": 10, "B": 11, "C": 12,
      "W": 13, "Y": 14, "g": 15}

CRATE_L = ["000000000000",        # 12x12 crate side (crates 0.6..0.9 tile)
           "044444444430",
           "043333333320",
           "043111111320",
           "043122234320",
           "043122342320",
           "043123422320",
           "043234222320",
           "043342222320",
           "043333333320",
           "032222222210",
           "000000000000"]
LID_L = ["000000000000",
         "044444444430",
         "043333333320",
         "011111111110",
         "043333333320",
         "032222222220",
         "011111111110",
         "043333333320",
         "032222222220",
         "011111111110",
         "033333333320",
         "000000000000"]
CRATE_S = ["00000000",          # 8x8 crate side (crates under 0.6 tile)
           "04444430",
           "04122320",
           "04124320",
           "04142320",
           "04422320",
           "03222210",
           "00000000"]
LID_S = ["00000000",
         "04444430",
         "03333320",
         "01111110",
         "04333320",
         "03222220",
         "03333320",
         "00000000"]
MANIFEST = ["01177110",
            "01888810",
            "01866810",
            "01888810",
            "01866810",
            "0188BB10",
            "01888810",
            "00000000"]
LABEL = ["666YY666",
         "66Y00Y66",
         "6Y0CB0Y6",
         "Y0CCBA0Y",
         "Y0CBBA0Y",
         "6Y0BA0Y6",
         "66Y00Y66",
         "666YY666"]
FRAME = ["000000000000",          # 12x24 shard-containment frame front
         "088888888870",
         "077777777760",
         "07ggg9gggg60",
         "07gg9W9ggg60",
         "07gg9WB9gg60",
         "07g9CWB9gg60",
         "07g9CWBA9g60",
         "07g9CCBA9g60",
         "07g9CCBA9g60",
         "07g9CCBA9g60",
         "0799CCBA9g60",
         "07W9CCBA9960",
         "07C9CCBA9B60",
         "07C9CCBA9B60",
         "07B9CCBA9A60",
         "07B9CCBA9A60",
         "07B9CCBA9A60",
         "075555555560",
         "066666666650",
         "0YY00YY00YY0",
         "0Y00YY00YY00",
         "000YY00YY000",
         "000000000000"]
GLASS_SIDE = ["000000",                # 6x24 frame side: posts and glass with a crystal edge
              "088870",
              "077760",
              "07gg60"] + ["07gB60"] * 6 + ["07CB60"] * 8 + ["075560", "066650", "0Y0Y00", "00Y0Y0", "0Y0Y00",
                                                             "000000"]
CASE = ["000000000000000",           # 15x10 canister case front
        "088888888888870",
        "07ggg7ggg7ggg60",
        "07gWg7gWg7gWg60",
        "07CWB7CWB7CWB60",
        "07CCB7CCB7CCB60",
        "07CBA7CBA7CBA60",
        "055555555555550",
        "0YY00YY00YY00Y0",
        "000000000000000"]
PALLET = ["4444444444444444",       # 16x3 pallet side strip (pallets are 0.14 tile = 2-3 px tall)
          "3310331033103310",
          "0000000000000000"]
STEEL_STRIP = ["8888888888888888",
               "6666666666666666",
               "5555555555555555"]


def tex_crate():
    W = H = 64
    img = np.full((H, W), 6)
    paint(img, 0, 0, CRATE_L, CK)
    paint(img, 12, 0, LID_L, CK)
    paint(img, 24, 0, CRATE_S, CK)
    paint(img, 32, 0, LID_S, CK)
    paint(img, 40, 0, MANIFEST, CK)
    paint(img, 48, 0, LABEL, CK)
    paint(img, 0, 12, PALLET, CK)
    paint(img, 0, 16, STEEL_STRIP, CK)
    paint(img, 0, 24, FRAME, CK)
    paint(img, 12, 24, GLASS_SIDE, CK)
    paint(img, 20, 24, CASE, CK)
    img[20:23, 0:4] = 12                                     # flat lit crystal texels for the 3D shards
    return img, PAL_CRATE


def _uv(x0, y0, w, h, W=64, H=64, inset=0.02):
    return ((x0 + inset) / W, (y0 + inset) / H, (x0 + w - inset) / W, (y0 + h - inset) / H)


CRATE_UV = {"side": _uv(0, 0, 12, 12), "lid": _uv(12, 0, 12, 12), "side_s": _uv(24, 0, 8, 8),
            "lid_s": _uv(32, 0, 8, 8), "manifest": _uv(40, 0, 8, 8), "label": _uv(48, 0, 8, 8),
            "pallet": _uv(0, 12, 16, 3), "steel": _uv(0, 16, 16, 3), "frame": _uv(0, 24, 12, 24),
            "frame_glass": _uv(12, 24, 6, 24), "case": _uv(20, 24, 15, 10), "xtal": _uv(1, 21, 1, 1, inset=0.3)}


# ---------------------------------------------------------------------------------------------------------------
# ec_banner (64x32): banner | pennant | tarp (16x16)
# ---------------------------------------------------------------------------------------------------------------

TARP = ["1111111111111111",
        "1DCCDCCCEFCCDCC1",
        "1DCCDCCCEFCCDCC1",
        "1CCBDCCBEFCBDCB1",
        "1CCBDCCBEFCBDCB1",
        "1EEEEEEEEEEEEEE1",
        "1FFFFFFFEFFFFFF1",
        "1DCBDCCBEFCBDCB1",
        "1DCBDCCBEFCBDCB1",
        "1DCBDCCBEFCBDCB1",
        "1CCBDCCBEFCBDCB1",
        "1CCBDCCBEFCBDCB1",
        "1CCBDCCBEFCBDCB1",
        "1BBBBBBBEFBBBBB1",
        "1BBBBBBBEFBBBBB1",
        "1111111111111111"]
TK = {"1": 1, "B": 11, "C": 12, "D": 13, "E": 14, "F": 15}


def tex_banner():
    W, H = 64, 32
    img = np.zeros((H, W), int)
    y, x = np.mgrid[0:H, 0:16]
    for v in (0, 1):
        b = np.zeros((H, 16), int)
        if v == 0:                                   # swallow-tailed banner
            bottom = 31 - (6 * (1 - np.abs(x + 0.5 - 8) / 8.0)).astype(int)
        else:                                        # long pointed pennant
            bottom = (18 + 13 * (1 - np.abs(x + 0.5 - 8) / 8.0)).astype(int)
        cloth = (y >= 2) & (y <= bottom) & (x >= 1) & (x <= 14)
        b[cloth] = 3
        b[cloth & ((x == 3) | (x == 4) | (x == 9))] = 4              # fold highlights
        b[cloth & ((x == 6) | (x == 11) | (x == 12))] = 2            # fold shadows
        b[cloth & (x == 2)] = 5
        b[(y >= 1) & (y <= 3) & (x >= 0) & (x <= 15)] = 7            # silver hem
        b[(y == 1) & (x >= 0) & (x <= 15)] = 8
        b[(y == 3) & (x >= 1) & (x <= 14)] = 6
        full = cloth | ((y >= 1) & (y <= 3))
        b[edge_of(full) & ~((y >= 1) & (y <= 3))] = 1
        b[(y == 0) & (x >= 0) & (x <= 15)] = 1
        cy, r = (12.0, 4.8) if v == 0 else (9.5, 4.0)
        _emblem(b, 8.0, cy, r, 8, 9, 10)
        if v == 0:
            b[(y >= 19) & (y <= 20) & (x >= 4) & (x <= 11)] = 7
            b[(y == 21) & (x >= 5) & (x <= 10)] = 6
        img[:, v * 16:(v + 1) * 16] = b
    paint(img, 32, 0, TARP, TK)
    return img, PAL_BANNER


BANNER_UV = {"tall": (0.0, 0.0, 16 / 64, 1.0), "pennant": (16 / 64, 0.0, 32 / 64, 1.0),
             "tarp": _uv(32, 0, 16, 16, 64, 32), "tarp_top": _uv(33, 1, 14, 12, 64, 32)}


# ---------------------------------------------------------------------------------------------------------------
# ec_barricade (32x32)
# ---------------------------------------------------------------------------------------------------------------

BK = {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "o": 8, "O": 9, "P": 10, "W": 11, "w": 12,
      "R": 13, "E": 14, "F": 15}
STRIPE = ["1" * 32,                                          # 32x4 hazard plank, tileable in u (16 texels/tile)
          "".join("7" if (x // 3) % 2 == 0 else "1" for x in range(32)),
          "".join("6" if ((x + 1) // 3) % 2 == 0 else "1" for x in range(32)),
          "1" * 32]
BOARD = ["EEEEEEEEEEEEEEEE",                                 # 16x5 CLOSED board (reads as red-bordered text)
         "ERWWWWWWWWWWWWRE",
         "ERWEEWEWEEWEEWRE",
         "ERWWWWWWWWWWWWRE",
         "EEEEEEEEEEEEEEEE"]
CONE = ["   PO   ",                                          # 8x12 traffic cone (cones are ~5 x 9 px)
        "   PO   ",
        "  PPOo  ",
        "  FWWw  ",
        "  POOo  ",
        " PPOOOo ",
        " FWWWww ",
        " POOOOo ",
        "PPOOOOOo",
        "PPOOOOOo",
        "33333333",
        "22222222"]


def tex_barricade():
    W = H = 32
    img = np.zeros((H, W), int)
    paint(img, 0, 0, STRIPE, BK)
    paint(img, 0, 4, BOARD, BK)
    paint(img, 16, 4, CONE, BK)
    # rows 16..31, x 16..31: steel chain-link fence panel (tileable), frame top/bottom (native: 1 tile wide)
    y, x = np.mgrid[0:H, 0:W]
    fx, fy = x - 16, y - 16
    reg = (x >= 16) & (fy >= 0)
    mesh = reg & ((((fx + fy) % 4) == 0) | (((fx - fy) % 4) == 0))
    img[mesh] = np.where(((fx[mesh] + fy[mesh]) % 8) < 4, 4, 3)
    rail = reg & ((fy <= 1) | (fy >= 14))
    img[rail] = np.where((fy[rail] == 0) | (fy[rail] == 14), 4, 2)
    return img, PAL_BARR


BARR_UV = {"stripe": _uv(0, 0, 32, 4, 32, 32), "board": _uv(0, 4, 16, 5, 32, 32), "cone": _uv(16, 4, 8, 10, 32, 32),
           "cone_base": _uv(16, 14, 8, 2, 32, 32), "fence": (16 / 32, 16 / 32, 1.0, 1.0)}


# ---------------------------------------------------------------------------------------------------------------
# ec_light (16x32): tripod work lamp card
# ---------------------------------------------------------------------------------------------------------------

def tex_light():
    W, H = 16, 32
    img = np.zeros((H, W), int)
    y, x = np.mgrid[0:H, 0:W]
    head = (x >= 1) & (x <= 14) & (y >= 2) & (y <= 11)
    img[head] = 3
    img[head & (y == 3)] = 4
    img[head & (y == 10)] = 2
    img[edge_of(head)] = 1
    lens = (x >= 3) & (x <= 12) & (y >= 4) & (y <= 9)
    img[lens] = 7
    inner = (x >= 4) & (x <= 11) & (y >= 5) & (y <= 8)
    img[inner] = 8
    img[(x >= 5) & (x <= 9) & (y >= 5) & (y <= 7)] = 9
    img[lens & ((x == 3) | (y == 9))] = 6
    img[(y == 1) & (x >= 5) & (x <= 10)] = 2                     # handle
    img[(y == 0) & ((x == 5) | (x == 10))] = 1
    img[(y >= 12) & (y <= 13) & (x >= 5) & (x <= 10)] = 3        # yoke
    img[(y == 13) & (x >= 5) & (x <= 10)] = 2
    pole = (y >= 12) & (y <= 21) & (x >= 7) & (x <= 8)
    img[pole] = np.where(x[pole] == 7, 4, 2)
    for sgn in (-1, 1):                                          # tripod legs, 2 texels wide
        for k in range(12):
            yy = 20 + k
            xx = 7.5 + sgn * (0.6 + k * 0.55)
            xi = int(round(xx))
            for dx in (0, 1 if sgn > 0 else -1):
                if 0 <= xi + dx < 16:
                    img[yy, xi + dx] = (4 if sgn < 0 else 3) if dx == 0 else 1
    img[(y >= 20) & (y <= 31) & (x >= 7) & (x <= 8)] = np.where(x[(y >= 20) & (y <= 31) & (x >= 7) & (x <= 8)] == 7,
                                                                 3, 2)
    img[(y == 31) & ((x <= 1) | (x >= 14) | (x == 7) | (x == 8))] = 1
    return img, PAL_LIGHT


LIGHT_UV = {"lamp": (0.0, 0.0, 1.0, 1.0), "lamp_head": (0.0, 0.0, 1.0, 12 / 32), "lamp_legs": (0.0, 12 / 32, 1.0, 1.0)}


# ---------------------------------------------------------------------------------------------------------------
# ec_glow (64x32, a5i3): true per-texel alpha, no dithering
# ---------------------------------------------------------------------------------------------------------------

def tex_glow():
    """-> (index grid 0..7, alpha grid 0..31)."""
    W, H = 64, 32
    y, x = np.mgrid[0:H, 0:32]
    r = np.hypot(x + 0.5 - 16, y + 0.5 - 16) / 16.0
    idx = np.zeros((H, W), int)
    alpha = np.zeros((H, W), int)
    # light pool: smooth (1 - r^2)^2 falloff, brightest colour in the centre
    a = np.clip(1 - r * r, 0, 1) ** 2
    alpha[:, 0:32] = np.round(31 * a).astype(int)
    idx[:, 0:32] = np.clip(np.round(7 * np.clip(1 - r, 0, 1) ** 0.8), 0, 7).astype(int)
    # contact shadow: a solid core with a soft rim
    a2 = (1 - smoothstep(0.45, 1.0, r)) ** 1.2
    alpha[:, 32:64] = np.round(31 * a2).astype(int)
    alpha[0, :] = alpha[-1, :] = 0
    alpha[:, 0] = alpha[:, 31] = alpha[:, 32] = alpha[:, 63] = 0
    return idx, alpha


GLOW_UV = {"pool": (0.5 / 64, 0.5 / 32, 31.5 / 64, 31.5 / 32), "shadow": (32.5 / 64, 0.5 / 32, 63.5 / 64, 31.5 / 32)}


# ---------------------------------------------------------------------------------------------------------------
# set assembly
# ---------------------------------------------------------------------------------------------------------------

TEXTURES = [("ec_ruts", tex_ruts, 1), ("ec_crate", tex_crate, 0), ("ec_banner", tex_banner, 1),
            ("ec_barricade", tex_barricade, 1), ("ec_light", tex_light, 1)]
GLOW_PALETTES = [("ec_glow_amb_pl", PAL_GLOW_AMB), ("ec_glow_vio_pl", PAL_GLOW_VIO), ("ec_glow_shd_pl", PAL_GLOW_SHD)]


def generate():
    out = []
    for name, fn, c0 in TEXTURES:
        idx, pal = fn()
        assert idx.min() >= 0 and idx.max() < 16 and len(pal) == 16, name
        out.append((name, idx, pal, c0))
    return out


def encode(name, idx, pal, c0):
    h, w = idx.shape
    flat = idx.reshape(-1)
    data = bytes(int(flat[i]) | int(flat[i + 1]) << 4 for i in range(0, len(flat), 2))
    tex = dict(name=name, fmt=3, w=w, h=h, c0=c0, data=data)
    p = dict(name=name + "_pl", colors=[nsbtx.bgr555(c) for c in pal], pltt4=0)
    return tex, p


def encode_glow():
    idx, alpha = tex_glow()
    assert idx.min() >= 0 and idx.max() < 8 and alpha.min() >= 0 and alpha.max() < 32
    flat = (idx | alpha << 3).reshape(-1)
    tex = dict(name="ec_glow", fmt=6, w=idx.shape[1], h=idx.shape[0], c0=0, data=bytes(int(v) for v in flat))
    pals = [dict(name=n, colors=[nsbtx.bgr555(c) for c in p], pltt4=0) for n, p in GLOW_PALETTES]
    return tex, pals


def build_set():
    """-> (set bytes, report lines, fails, generated). Stock set 007 at BASE_REV + the kit, append-only."""
    base = K.git_bytes(K.BASE_REV, K.BASE_SET_REL)
    s = nsbtx.parse(base)
    gen = generate()
    texs, pals = zip(*[encode(*g) for g in gen])
    gt, gp = encode_glow()
    texs, pals = list(texs) + [gt], list(pals) + gp
    names = {t["name"] for t in s["textures"]} | {p["name"] for p in s["palettes"]}
    fails = [f"name clash: {e['name']}" for e in texs + pals if e["name"] in names]
    fails += [f"name too long: {e['name']}" for e in texs + pals if len(e["name"]) > 15]
    st = [dict(t) for t in s["textures"]]
    sp = [dict(p) for p in s["palettes"]]
    for e in st + sp:
        e.pop("off", None)
    out = nsbtx.build(st + texs, sp + pals, pal_flag=s["header"]["pal_flag"])
    so = nsbtx.parse(out)
    OT = {t["name"]: t for t in so["textures"]}
    OP = {p["name"]: p for p in so["palettes"]}
    for t in s["textures"]:
        t2 = OT.get(t["name"])
        if t2 is None or t2["data"] != t["data"] or (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != \
                (t["fmt"], t["w"], t["h"], t["c0"]):
            fails.append(f"stock texture changed: {t['name']}")
    for p in s["palettes"]:
        if not OP.get(p["name"], {}).get("data", b"").startswith(p["data"]):
            fails.append(f"stock palette changed: {p['name']}")
    if [t["name"] for t in so["textures"]][:len(s["textures"])] != [t["name"] for t in s["textures"]]:
        fails.append("stock texture order changed")
    for t in texs:
        t2 = OT[t["name"]]
        if t2["data"] != t["data"] or t2["c0"] != t["c0"] or t2["fmt"] != t["fmt"]:
            fails.append(f"new texture did not round-trip: {t['name']}")
    rt = [dict(t) for t in so["textures"]]
    rp = [dict(p) for p in so["palettes"]]
    for e in rt + rp:
        e.pop("off", None)
    again = nsbtx.build(rt, rp, pal_flag=so["header"]["pal_flag"])
    if again != out:
        fails.append("set does not round-trip byte-identically (parse -> build)")
    vb, vo = nsbtx.vram_usage(s), nsbtx.vram_usage(so)
    if sum(vo) >= K.VRAM_TARGET:
        fails.append(f"VRAM {sum(vo)} B >= {K.VRAM_TARGET} B")
    rep = [f"{K.SET_REL}: {len(s['textures'])} -> {len(so['textures'])} textures, {len(s['palettes'])} -> "
           f"{len(so['palettes'])} palettes; VRAM {sum(vb)} -> {sum(vo)} B (texels {vb[0]} -> {vo[0]}, palettes "
           f"{vb[1]} -> {vo[1]}; budget {K.VRAM_TARGET}); file {len(base)} -> {len(out)} B; round trip "
           f"{'identical' if again == out else 'DIFFERENT'}"]
    for name, idx, pal, c0 in gen:
        rep.append(f"  {name:13s} {idx.shape[1]}x{idx.shape[0]} pltt16 c0={c0} colours used "
                   f"{len(np.unique(idx))}/16")
    rep.append(f"  {'ec_glow':13s} {gt['w']}x{gt['h']} a5i3 (palettes {', '.join(n for n, _ in GLOW_PALETTES)})")
    return out, rep, fails, gen


def write_preview(d, gen, scale=8):
    from PIL import Image
    os.makedirs(d, exist_ok=True)
    for name, idx, pal, c0 in gen:
        p = np.array([nsbtx.rgb(nsbtx.bgr555(c)) for c in pal], np.uint8)
        rgb = p[idx]
        if c0:
            chk = ((np.mgrid[0:idx.shape[0], 0:idx.shape[1]].sum(0) // 2) % 2)[..., None]
            bg = np.where(chk, 90, 60).astype(np.uint8)
            rgb = np.where((idx == 0)[..., None], bg, rgb)
        Image.fromarray(rgb).resize((idx.shape[1] * scale, idx.shape[0] * scale), Image.NEAREST).save(
            os.path.join(d, name + ".png"))
    idx, alpha = tex_glow()
    for n, pal in GLOW_PALETTES:
        p = np.array([nsbtx.rgb(nsbtx.bgr555(c)) for c in pal], float)
        a = (alpha / 31.0)[..., None]
        rgb = (p[idx] * a + np.array([70, 90, 60]) * (1 - a)).astype(np.uint8)
        Image.fromarray(rgb).resize((idx.shape[1] * scale, idx.shape[0] * scale), Image.NEAREST).save(
            os.path.join(d, n.replace("_pl", "") + ".png"))


def main():
    out, rep, fails, gen = build_set()
    print("\n".join(rep))
    for f in fails:
        print("FAIL", f)
    if "--preview" in sys.argv:
        write_preview(sys.argv[sys.argv.index("--preview") + 1], gen)
    if "--write" in sys.argv:
        assert not fails, "refusing to write"
        open(os.path.join(K.ROOT, K.SET_REL), "wb").write(out)
        print("wrote", K.SET_REL, len(out), "B")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
