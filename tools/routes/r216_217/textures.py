#!/usr/bin/env python3
"""Routes 216-217 (Memorial Ridge & Indra's Camp) texture set, v2: map_texture_set_080 = stock map_texture_set_014
(read from git HEAD, so reruns never append twice) + five procedurally drawn 64x64 atlases. Pure math (NumPy): value
noise, SDF shapes and hand-tuned BGR555 palettes. Opaque / c0 atlases are pltt16 pixel art with 1-texel dark outlines
on every silhouette edge (faces map whole regions, so a region border is a face border on screen); the soft glows,
light pools and contact shadows are one A3I5 atlas with smooth 3-bit alpha ramps (no ordered dither, no checkerboard).

Usage:
  ~/.venvs/desmume/bin/python tools/routes/r216_217/textures.py                 dry run: table, VRAM, round trip
  ~/.venvs/desmume/bin/python tools/routes/r216_217/textures.py --preview DIR   also DIR/<texture>.png + x6 sheet
  ~/.venvs/desmume/bin/python tools/routes/r216_217/textures.py --write         write SET_REL (refuses on FAIL)

Atlases (texel boxes x0, y0, x1, y1, exclusive ends, in REGIONS; build_art.py maps faces onto them):
  r216_stone   opaque pltt16. Teo's monolith face (bevelled outline, carved mountain-and-falling-star emblem, inlaid
               dark plaque with the engraved "TEO" and lines, carved base fillet) and its side, pedestal riser, step
               top with settled snow, ashlar granite, crisp snow cap and its outlined side band, lantern stone parts.
  r216_offer   c0=1. Evergreen & winter-blossom wreath, deep-violet knitted scarf band, knot and two fringed tails,
               dithered snow drift wedge, snow pile, snow-cap drip lip, violet shard dust, boot prints, frozen bouquet.
  r216_glow    A3I5. Warm amber bloom, electric-violet bloom, soft ground light pool, soft blue contact shadow
               (shared by both chunks).
  r217_tent    c0=1. Deep-violet canvas slope with the pale-silver Eclipse emblem, emblem overlay, front gable with the
               open shadowed doorway, tied-back flap lining, guy rope, pole wood, heaped ridge snow.
  r217_camp    c0=1. Expedition-lantern glass and frame, supply crate face and side, shard-scanner lid screen and case
               body, violet shard, field journal, packed-snow clearing patch with a dithered rim.
"""
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import nsbtx  # noqa: E402

SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_080.nsbtx"
BASE_REV = "HEAD"
BASE_SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_014.nsbtx"
VRAM_TARGET = 160 * 1024
N = 64

BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], float) + 0.5) / 16.0 - 0.5
YY, XX = np.mgrid[0:N, 0:N].astype(float)
BAYER = BAYER4[(YY % 4).astype(int), (XX % 4).astype(int)]

REGIONS = {
    "r216_stone": {"stele": (0, 0, 24, 48), "stele_side": (24, 0, 32, 48), "step": (32, 0, 64, 8),
                   "step_top": (32, 8, 64, 24), "snow": (32, 24, 48, 40), "lantern": (48, 24, 64, 40),
                   "post": (32, 40, 40, 64), "snow_side": (40, 40, 64, 48), "granite": (0, 48, 32, 64),
                   "roof": (40, 48, 64, 56), "chamfer": (40, 56, 64, 64)},
    "r216_offer": {"wreath": (0, 0, 32, 32), "scarf": (32, 0, 64, 8), "knot": (32, 8, 48, 24),
                   "tail": (48, 8, 56, 40), "tail2": (56, 8, 64, 40), "bouquet": (32, 24, 48, 40),
                   "drift": (0, 32, 32, 48), "mound": (32, 40, 48, 56), "drip": (0, 48, 32, 56),
                   "dust": (0, 56, 32, 64), "prints": (48, 40, 64, 64), "spare": (32, 56, 48, 64)},
    "r216_glow": {"amber": (0, 0, 32, 32), "violet": (32, 0, 64, 32), "pool": (0, 32, 32, 64),
                  "shadow": (32, 32, 64, 64)},
    "r217_tent": {"canvas": (0, 0, 32, 32), "emblem": (32, 0, 64, 32), "gable": (0, 32, 32, 56),
                  "flap": (32, 32, 48, 56), "rope": (48, 32, 64, 36), "wood": (48, 36, 64, 44),
                  "back": (48, 44, 64, 56), "ridge_snow": (0, 56, 32, 64), "wall": (32, 56, 64, 64)},
    "r217_camp": {"glass": (0, 0, 16, 16), "iron": (0, 16, 16, 32), "crate": (16, 0, 48, 24),
                  "crate_side": (16, 24, 48, 32), "screen": (48, 0, 64, 16), "case": (48, 16, 64, 32),
                  "shard": (0, 32, 16, 48), "journal": (0, 48, 16, 64), "clear": (16, 32, 48, 64),
                  "lid": (48, 32, 64, 48), "spare": (48, 48, 64, 64)},
}
TRANSPARENT = {"r216_offer", "r217_tent", "r217_camp"}
ALPHA_FMT = {"r216_glow"}            # A3I5 (fmt 1): 5-bit index, 3-bit alpha


def snap(c):
    return tuple(int(v) >> 3 << 3 for v in c)


def vnoise(shape, cells, seed):
    """Value noise in [0, 1) over an h x w region (cells lattice per region side), smoothstep-bilinear."""
    h, w = shape
    rng = np.random.RandomState(seed)
    g = rng.rand(cells + 1, cells + 1)
    y, x = np.mgrid[0:h, 0:w].astype(float)
    fx, fy = x * cells / w, y * cells / h
    x0, y0 = np.minimum(np.floor(fx).astype(int), cells - 1), np.minimum(np.floor(fy).astype(int), cells - 1)
    tx, ty = fx - x0, fy - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a = g[y0, x0] * (1 - tx) + g[y0, x0 + 1] * tx
    b = g[y0 + 1, x0] * (1 - tx) + g[y0 + 1, x0 + 1] * tx
    return a * (1 - ty) + b * ty


def fbm(shape, seed, octs=((3, 0.5), (6, 0.3), (12, 0.2))):
    return sum(wt * vnoise(shape, c, seed + 37 * k) for k, (c, wt) in enumerate(octs))


class Atlas:
    """64x64 index canvas (+ alpha canvas for A3I5); regions drawn in local coordinates."""

    def __init__(self, name, pal):
        self.name, self.pal = name, pal
        self.img = np.zeros((N, N), int)
        self.alpha = np.zeros((N, N), int)

    def region(self, key):
        return REGIONS[self.name][key]

    def local(self, key):
        x0, y0, x1, y1 = self.region(key)
        y, x = np.mgrid[0:y1 - y0, 0:x1 - x0].astype(float)
        return x, y, BAYER[y0:y1, x0:x1]

    def put(self, key, arr, alpha=None):
        x0, y0, x1, y1 = self.region(key)
        self.img[y0:y1, x0:x1] = arr
        if alpha is not None:
            self.alpha[y0:y1, x0:x1] = alpha


def ramp(t, idx, b, dither=1.0):
    n = len(idx)
    v = np.clip(np.floor(np.clip(t, 0, 1) * (n - 1) + 0.5 + b * dither), 0, n - 1).astype(int)
    return np.array(idx)[v]


def outline(img, x, y, w, h, c=0, sides="lrtb"):
    m = np.zeros(img.shape, bool)
    if "l" in sides:
        m |= x == 0
    if "r" in sides:
        m |= x == w - 1
    if "t" in sides:
        m |= y == 0
    if "b" in sides:
        m |= y == h - 1
    return np.where(m, c, img)


# ---------------------------------------------------------------------------------------------------------------
# r216_stone: Teo's monolith, pedestal, snow cap, lantern stone (opaque)
# ---------------------------------------------------------------------------------------------------------------

STONE_PAL = [
    (16, 18, 30),     # 0 outline / deep carved shadow
    (40, 44, 60),     # 1 crevice
    (64, 68, 86),     # 2 dark granite
    (90, 94, 112),    # 3 granite shade
    (116, 120, 138),  # 4 granite mid
    (142, 146, 162),  # 5 granite light
    (168, 172, 188),  # 6 granite lit
    (196, 202, 216),  # 7 chisel highlight / frost
    (176, 192, 222),  # 8 snow shade (cool blue)
    (230, 236, 248),  # 9 snow
    (252, 252, 255),  # 10 snow highlight
    (128, 148, 192),  # 11 icy blue shadow
    (22, 22, 34),     # 12 plaque black
    (46, 48, 68),     # 13 plaque slate
    (208, 214, 232),  # 14 engraved silver
    (96, 100, 132),   # 15 blue-violet slate
]


def granite(x, y, b, seed, idx=(3, 4, 5, 6), amp=0.5, base=0.5):
    t = base + amp * (fbm(x.shape, seed, ((2, 0.55), (5, 0.3), (11, 0.15))) - 0.5)
    img = ramp(t, list(idx), b, 0.45)
    img = np.where((vnoise(x.shape, 24, seed + 3) > 0.9), 7, img)          # frost / quartz speckle
    img = np.where((vnoise(x.shape, 24, seed + 4) > 0.93), 2, img)         # dark mica flecks
    return img


def tex_stone():
    A = Atlas("r216_stone", STONE_PAL)
    # monolith face 24 x 48 (v down): outline, bevel, carved emblem, scarf band zone, inlaid plaque, base fillet
    x, y, b = A.local("stele")
    W, H = 24, 48
    img = granite(x, y, b, 31, (2, 3, 4), 0.45, 0.5)                       # charcoal granite face
    img = np.where(y < 18, np.where(img == 2, 3, img), img)               # upper face catches more light
    img = np.where(x == 1, 7, img)                                         # lit west bevel
    img = np.where(x == 2, 5, img)
    img = np.where(x == W - 2, 1, img)                                     # shaded east bevel
    img = np.where(y == 1, 6, img)
    img = np.where(y == H - 2, 2, img)
    # carved recessed border panel (groove: shadow top/left, lit lip bottom/right)
    gx0, gx1, gy0, gy1 = 4, W - 5, 3, H - 8
    frame = ((x == gx0) | (y == gy0)) & (x >= gx0) & (x <= gx1) & (y >= gy0) & (y <= gy1)
    lip = ((x == gx1) | (y == gy1)) & (x >= gx0) & (x <= gx1) & (y >= gy0) & (y <= gy1)
    img = np.where(frame, 0, img)
    img = np.where(lip & ~frame, 6, img)
    # carved emblem: mountain peak with snow summit and a falling star (rows 5..13)
    ex, ey = x - 11.5, y - 9.5
    peak = (ey > -4.2 + np.abs(ex) * 0.85) & (ey < 3.5) & (np.abs(ex) < 6.5) & (x > gx0) & (x < gx1)
    img = np.where(peak, 4, img)
    img = np.where(peak & (ex < 0) & (ey < -1.0 + np.abs(ex) * 0.85), 7, img)   # lit west flank
    img = np.where(peak & (np.abs(ex) < 1.6) & (ey < -2.3), 9, img)              # snow summit
    edge = peak & ~((ey > -3.2 + np.abs(ex) * 0.85) & (ey < 2.5) & (np.abs(ex) < 5.5))
    img = np.where(edge & (ey > -4.2 + np.abs(ex) * 0.85 + 0.0), np.where(ey > 2.4, 1, 0), img)
    star = (np.abs(x - 17) + np.abs(y - 5)) <= 1.0
    img = np.where(star, 14, img)
    img[5, 17] = 10
    img = np.where((y == 6) & (x >= 13) & (x <= 15), 7, img)                     # star trail
    img = np.where((y == 7) & (x >= 11) & (x <= 12), 6, img)
    # inlaid dark plaque rows 22..37 cols 6..17: recess, slate field, engraved silver TEO + lines
    px0, px1, py0, py1 = 6, 17, 22, 37
    inside = (x >= px0) & (x <= px1) & (y >= py0) & (y <= py1)
    pl = ramp(0.5 + 0.5 * (vnoise(x.shape, 8, 33) - 0.5), [12, 13, 12], b, 0.8)
    img = np.where(inside, pl, img)
    img = np.where(inside & ((x == px0) | (y == py0)), 0, img)
    img = np.where(inside & ((x == px1) | (y == py1)), 6, img)
    T = ["111", "010", "010", "010", "010"]
    E = ["111", "100", "110", "100", "111"]
    O = ["111", "101", "101", "101", "111"]
    gx = 7
    for g in (T, E, O):
        for r, row in enumerate(g):
            for c, ch in enumerate(row):
                if ch == "1":
                    img[24 + r, gx + c] = 14
        gx += 4
    rng = np.random.RandomState(34)
    for ry in (31, 33):
        cx = 8
        while cx < 16:
            ln = rng.randint(1, 4)
            img[ry, cx:min(cx + ln, 16)] = 14
            cx += ln + 1
    img[35, 8:16] = np.where(np.arange(8, 16) % 2 == 0, 14, 13)
    # carved base fillet + moulding rows 41..45
    img = np.where((y >= 41) & (y <= 42) & (x > 1) & (x < W - 2), np.where(b > -0.1, 5, 4), img)
    img = np.where((y == 43) & (x > 1) & (x < W - 2), 0, img)
    img = np.where((y >= 44) & (y <= 45) & (x > 1) & (x < W - 2), 2, img)
    img = outline(img, x, y, W, H, 0)
    A.put("stele", img)

    # monolith side 8 x 48: darker granite, outlined, bevel highlight on the front edge
    x, y, b = A.local("stele_side")
    img = granite(x, y, b, 35, (1, 2, 3), 0.45, 0.5)
    img = np.where(x == 1, 4, img)
    img = np.where((y >= 41) & (y <= 42), 4, img)
    img = np.where(y == 43, 1, img)
    img = outline(img, x, y, 8, 48, 0)
    A.put("stele_side", img)

    # chamfer strip 24 x 8 (u along the edge, v across): bright bevel
    x, y, b = A.local("chamfer")
    img = ramp(0.6 + 0.3 * (vnoise(x.shape, 6, 36) - 0.5), [5, 6, 7], b)
    img = np.where(y == 7, 0, img)
    A.put("chamfer", img)

    # pedestal riser 32 x 8: snow-dusted lit lip, granite, joints, dark outline foot
    x, y, b = A.local("step")
    img = granite(x, y, b, 41, (3, 4, 5), 0.4, 0.45)
    img = np.where(y == 1, 7, img)
    img = np.where(y == 0, np.where(vnoise(x.shape, 8, 42) > 0.4, 10, 9), img)
    img = np.where((x % 16 == 15) & (y > 1), 1, img)
    img = np.where(y == 6, 2, img)
    img = np.where(y == 7, 0, img)
    img = outline(img, x, y, 32, 8, 0, "lr")
    A.put("step", img)

    # step top 32 x 16: carved granite with settled snow drifts along the back and in patches
    x, y, b = A.local("step_top")
    img = granite(x, y, b, 43, (4, 5, 6), 0.4, 0.55)
    sn = vnoise(x.shape, 6, 44) + 0.06 * (8 - y)
    img = np.where(sn > 0.78, np.where(b > 0.1, 10, 9), img)
    img = np.where((sn > 0.7) & (sn <= 0.78), 8, img)
    img = np.where(y == 15, 7, img)                                         # lit front edge
    img = np.where(x % 16 == 15, np.where(sn > 0.7, 8, 1), img)
    A.put("step_top", img)

    # snow cap 16 x 16: fresh snow, cool shading, sparkles
    x, y, b = A.local("snow")
    t = 1.0 - y / 15.0 * 0.45 + 0.25 * (vnoise(x.shape, 4, 45) - 0.5)
    img = ramp(t, [8, 9, 9, 10], b, 0.7)
    img = np.where((vnoise(x.shape, 16, 46) > 0.86) & (b > 0.2), 10, img)
    img = np.where(y == 15, 11, img)                                        # cool rim on the outer edge
    img = np.where(y == 0, 10, img)
    A.put("snow", img)

    # snow side band 24 x 8: bright lip, cool underside, dark outline row (crisp silhouette)
    x, y, b = A.local("snow_side")
    lip = 4 + np.round(1.2 * np.sin(x * 0.9) + vnoise(x.shape, 8, 47))
    img = np.where(y < lip - 1, np.where(b > 0.0, 10, 9), 9)
    img = np.where(y >= lip - 1, 8, img)
    img = np.where(y >= lip, 11, img)
    img = np.where(y >= lip + 1, 0, img)
    img = np.where(y == 0, 10, img)
    A.put("snow_side", img)

    # lantern stone 16 x 16, post 8 x 24, roof 24 x 8: granite with outlines
    x, y, b = A.local("lantern")
    img = granite(x, y, b, 48, (3, 4, 5), 0.4, 0.5)
    img = np.where((x == 1) | (y == 1), 6, img)
    img = outline(img, x, y, 16, 16, 0)
    A.put("lantern", img)
    x, y, b = A.local("post")
    img = granite(x, y, b, 49, (3, 4, 5), 0.4, 0.5)
    img = np.where(x == 1, 6, img)
    img = np.where(x == 6, 2, img)
    img = outline(img, x, y, 8, 24, 0, "lr")
    A.put("post", img)
    x, y, b = A.local("roof")
    img = granite(x, y, b, 50, (2, 3, 4), 0.4, 0.5)
    img = np.where(y <= 1, np.where(vnoise(x.shape, 8, 51) > 0.35, 9, 7), img)
    img = np.where(y == 7, 0, img)
    A.put("roof", img)

    # ashlar granite 32 x 16 for pedestal sides
    x, y, b = A.local("granite")
    img = granite(x, y, b, 52, (3, 4, 5), 0.45, 0.45)
    img = np.where((y % 8 == 7) | (((x + np.where(y // 8 == 0, 0, 8)) % 16) == 15), 1, img)
    img = np.where((y % 8 == 0), 6, img)
    img = np.where(y == 0, 9, img)
    A.put("granite", img)
    return A


# ---------------------------------------------------------------------------------------------------------------
# r216_offer: wreath, scarf, drifts, dust, prints (colour 0 transparent)
# ---------------------------------------------------------------------------------------------------------------

OFFER_PAL = [
    (255, 0, 255),    # 0 transparent
    (18, 12, 34),     # 1 outline
    (28, 64, 44),     # 2 dark fir
    (46, 108, 66),    # 3 fir
    (104, 168, 120),  # 4 frosted fir
    (248, 250, 255),  # 5 snow white
    (186, 202, 234),  # 6 snow shade
    (220, 36, 56),    # 7 winter berry red
    (255, 214, 236),  # 8 winter blossom pink-white
    (255, 196, 72),   # 9 gold
    (58, 20, 112),    # 10 scarf deep violet
    (96, 40, 176),    # 11 scarf violet
    (140, 84, 228),   # 12 scarf lit
    (192, 156, 255),  # 13 scarf highlight / dust
    (232, 216, 255),  # 14 violet sparkle
    (140, 158, 200),  # 15 snow hollow / print
]


def tex_offer():
    A = Atlas("r216_offer", OFFER_PAL)
    # wreath 32 x 32: bold fir ring, dark outline, frost tips, pink-white winter blossoms, red berries, gold bow
    x, y, b = A.local("wreath")
    dx, dy = x - 15.5, y - 15.5
    r = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)
    rough = 0.9 * np.sin(ang * 16) + 0.5 * (vnoise(x.shape, 12, 71) - 0.5)
    ring = (r > 6.0 - 0.4 * rough) & (r < 14.6 + rough * 0.6)
    light = np.clip(0.6 - 0.35 * dx / 14 - 0.45 * dy / 14 + 0.3 * (vnoise(x.shape, 10, 72) - 0.5), 0, 1)
    img = np.where(ring, ramp(light, [2, 3, 3, 4], b, 0.6), 0)
    inner = (r > 7.0 - 0.4 * rough) & (r < 13.6 + rough * 0.6)
    img = np.where(ring & ~inner, 1, img)
    img = np.where(inner & (vnoise(x.shape, 20, 73) > 0.75), 5, img)              # frost tips
    for k in range(6):                                                              # winter blossoms
        a = k * 2 * np.pi / 6 + 0.3
        fx, fy = 15.5 + 10.2 * np.cos(a), 15.5 + 10.2 * np.sin(a)
        d = np.hypot(x - fx, y - fy)
        img = np.where(d < 2.6, 1, img)
        img = np.where(d < 2.0, 8, img)
        img = np.where(d < 0.8, 9, img)
    for k in range(8):
        a = k * 2 * np.pi / 8 + 0.75
        fx, fy = 15.5 + 8.2 * np.cos(a), 15.5 + 8.2 * np.sin(a)
        d = np.hypot(x - fx, y - fy)
        img = np.where(d < 1.3, 7, img)
        img = np.where((d < 0.5), 8, img)
    bow = (np.abs(dx) < 4.5) & (dy > 9.5) & (dy < 14.5) & (np.abs(dy - 12) < 2.5 - 0.3 * np.abs(dx))
    img = np.where(bow, 11, img)
    img = np.where(bow & (np.abs(dx) < 1.2), 12, img)
    A.put("wreath", img)

    # scarf band 32 x 8: chunky knit, lit top, outlined edges
    x, y, b = A.local("scarf")
    img = np.where((x + 2 * (y // 2)) % 4 < 2, 11, 12)
    img = np.where(y == 1, 13, img)
    img = np.where(y >= 5, 10, img)
    img = np.where((y == 3) & (x % 4 == 0), 10, img)
    img = np.where((y == 0) | (y == 7), 1, img)
    A.put("scarf", img)

    # knot 16 x 16: round knot with fold shading
    x, y, b = A.local("knot")
    d = np.hypot((x - 7.5) / 7.0, (y - 7.5) / 6.5)
    img = np.where(d < 1.0, ramp(0.9 - 0.5 * (x / 15) - 0.4 * (y / 15), [10, 11, 12, 13], b, 0.5), 0)
    img = np.where((d < 1.0) & (np.abs(x - 7.5 - 0.6 * (y - 7.5)) < 0.8), 10, img)
    img = np.where((d >= 0.86) & (d < 1.0), 1, img)
    A.put("knot", img)

    # tails 8 x 32: hanging scarf ends with a flutter curve and a pale fringe
    for key, seed, ph in (("tail", 75, 0.0), ("tail2", 76, 1.7)):
        x, y, b = A.local(key)
        cx = 3.5 + 1.3 * np.sin(y / 31.0 * 3.2 + ph) * (y / 31.0)
        hw = 2.6 - 0.4 * (y / 31.0)
        body = (np.abs(x - cx) < hw) & (y <= 27)
        img = np.where(body, np.where(x < cx - 0.4, 12, 11), 0)
        img = np.where(body & ((y + int(ph)) % 4 == 0), 10, img)
        img = np.where(body & ~(np.abs(x - cx) < hw - 1.0), 1, img)
        fr = (y >= 28) & (y <= 31) & (np.abs(x - cx) < hw) & ((x.astype(int) + key.__len__()) % 2 == 0)
        img = np.where(fr, 13, img)
        img = np.where((y == 28) & (np.abs(x - cx) < hw), 1, img)
        A.put(key, img)

    # frozen bouquet 16 x 16
    x, y, b = A.local("bouquet")
    img = np.zeros(x.shape, int)
    for k in range(5):
        sx = 4 + k * 2
        stem = (np.abs(x - (8 + (sx - 8) * (1 - (y - 6) / 10.0))) < 0.6) & (y >= 6) & (y <= 15)
        img = np.where(stem, 2, img)
    for (fx, fy, c) in ((4, 4, 8), (8, 2.5, 5), (12, 4, 8), (6, 6.5, 5), (10, 6.5, 8)):
        d = np.hypot(x - fx, y - fy)
        img = np.where(d < 2.2, 1, img)
        img = np.where(d < 1.6, c, img)
        img = np.where(d < 0.6, 9, img)
    img = np.where((y >= 10) & (y <= 11) & (np.abs(x - 8) <= 2), 11, img)
    A.put("bouquet", img)

    # snow drift wedge 32 x 16 (v = 0 is the high / far edge): irregular dithered crest, cool lower shading
    x, y, b = A.local("drift")
    crest = 3.0 + 2.5 * vnoise(x.shape, 5, 77) + 1.5 * np.sin(x * 0.45)
    side = np.minimum(x, 31 - x)
    crest = crest + np.clip(5 - side, 0, 5) * 1.3
    t = (y - crest)
    body = t + 0.9 * b > 0
    img = np.where(body, ramp(0.95 - y / 16.0 * 0.5, [6, 5, 5], b, 0.6), 0)
    img = np.where(body & (t < 1.2), 5, img)
    A.put("drift", img)

    # snow pile 16 x 16 (flat decal): soft blob with dithered rim
    x, y, b = A.local("mound")
    d = np.hypot(x - 7.5, y - 7.5) / 7.5 + 0.25 * (vnoise(x.shape, 5, 78) - 0.5)
    img = np.where(d + 0.25 * b < 0.92, np.where(d < 0.55 + 0.2 * b, 5, 6), 0)
    A.put("mound", img)

    # snow-cap drip lip 32 x 8: solid top rows, rounded icicle drips below, cool outline under the drips
    x, y, b = A.local("drip")
    dl = 2.5 + 2.8 * np.abs(np.sin(x * 0.55 + 0.6 * vnoise(x.shape, 6, 79))) ** 3 + 1.2 * vnoise(x.shape, 10, 80)
    img = np.where(y < dl, 5, 0)
    img = np.where((y < dl) & (y >= dl - 1.4), 6, img)
    img = np.where((y >= dl) & (y < dl + 1), 15, img)
    A.put("drip", img)

    # violet shard dust 32 x 8: sparse glints with four-point sparkles
    x, y, b = A.local("dust")
    sp = vnoise(x.shape, 32, 81)
    dens = np.clip(1.0 - np.hypot((x - 15.5) / 15.5, (y - 3.5) / 3.5), 0, 1)
    img = np.where((sp > 0.82 - 0.25 * dens), 13, 0)
    for (sx, sy) in ((6, 3), (15, 4), (24, 2), (11, 6)):
        img = np.where((np.abs(x - sx) + np.abs(y - sy)) == 1, 13, img)
        img[sy, sx] = 14
    A.put("dust", img)

    # boot prints 16 x 24: two left/right pairs walking up, cool hollows with bright rims
    x, y, b = A.local("prints")
    img = np.zeros(x.shape, int)
    for (px, py) in ((5, 3.0), (11, 8.5), (5, 14.0), (11, 19.5)):
        sole = ((x - px) / 1.7) ** 2 + ((y - py) / 2.0) ** 2 < 1.0
        heel = ((x - px) / 1.3) ** 2 + ((y - py - 2.5) / 0.9) ** 2 < 1.0
        p = sole | heel
        img = np.where(p, 15, img)
        rim = (((x - px) / 2.5) ** 2 + ((y - py - 0.6) / 3.4) ** 2 < 1.0) & ~p & (y > py + 1)
        img = np.where(rim & (img == 0), 6, img)
    A.put("prints", img)
    return A


# ---------------------------------------------------------------------------------------------------------------
# r216_glow: A3I5 smooth glows, pools and shadows
# ---------------------------------------------------------------------------------------------------------------

GLOW_PAL = [
    (255, 252, 236), (255, 240, 184), (255, 222, 132), (255, 198, 92),     # 0..3 amber white-hot -> gold
    (248, 170, 62), (236, 140, 44), (212, 108, 32), (176, 76, 24),         # 4..7 amber -> ember
    (252, 244, 255), (232, 214, 255), (208, 180, 255), (184, 144, 255),    # 8..11 violet white -> lilac
    (160, 112, 252), (136, 84, 240), (112, 60, 216), (84, 40, 176),        # 12..15 electric violet -> deep
    (14, 18, 40), (28, 34, 64), (46, 54, 92), (70, 82, 124),               # 16..19 contact shadow blues
] + [(0, 0, 0)] * 12


def soft(d, peak, gamma):
    """3-bit alpha from a normalised distance (0 centre, 1 edge): a smooth quantised falloff, no dither."""
    a = peak * np.clip(1.0 - d, 0, 1) ** gamma
    return np.clip(np.round(a), 0, 7).astype(int)


def tex_glow():
    A = Atlas("r216_glow", GLOW_PAL)
    for key, base in (("amber", 0), ("violet", 8)):
        x, y, b = A.local(key)
        d = np.hypot(x - 15.5, y - 15.5) / 15.5
        al = soft(d, 7.4, 1.7)
        idx = base + np.clip(np.floor(d * 7.0), 0, 5).astype(int)
        A.put(key, np.where(al > 0, idx, base + 5), al)
    x, y, b = A.local("pool")                                   # soft warm ground pool (colour from vertex tint)
    d = np.hypot(x - 15.5, y - 15.5) / 15.5
    al = soft(d, 5.4, 1.3)
    idx = 1 + np.clip(np.floor(d * 6.0), 0, 5).astype(int)
    A.put("pool", idx, al)
    x, y, b = A.local("shadow")                                 # soft blue contact shadow, darker core
    d = np.hypot(x - 15.5, y - 15.5) / 15.5
    al = soft(d, 6.2, 0.9)
    idx = 16 + np.clip(np.floor(d * 4.0), 0, 3).astype(int)
    A.put("shadow", idx, al)
    return A


# ---------------------------------------------------------------------------------------------------------------
# r217_tent: deep-violet expedition canvas with the pale-silver Eclipse emblem
# ---------------------------------------------------------------------------------------------------------------

TENT_PAL = [
    (255, 0, 255),    # 0 transparent
    (16, 8, 34),      # 1 outline
    (36, 12, 76),     # 2 canvas deep
    (54, 22, 112),    # 3 canvas dark
    (76, 36, 148),    # 4 canvas
    (102, 58, 182),   # 5 canvas lit
    (138, 96, 214),   # 6 canvas highlight / stitching
    (236, 240, 252),  # 7 pale silver emblem
    (150, 156, 186),  # 8 silver shade
    (246, 248, 255),  # 9 snow
    (188, 200, 230),  # 10 snow shade
    (186, 158, 112),  # 11 rope light
    (128, 98, 66),    # 12 rope / wood mid
    (84, 58, 40),     # 13 wood dark
    (8, 4, 16),       # 14 doorway black
    (160, 126, 86),   # 15 wood lit
]


def canvas_base(x, y, b, seed, lit=0.55):
    t = lit + 0.35 * (fbm(x.shape, seed, ((2, 0.6), (5, 0.3), (10, 0.1))) - 0.5) - 0.18 * (y / 31.0)
    img = ramp(t, [3, 4, 5], b, 0.5)
    img = np.where(x % 16 == 0, 2, img)                                     # seams
    img = np.where((x % 16 == 1) & (y % 3 == 0), 6, img)                    # stitching
    return img


def eclipse(img, x, y, cx, cy, r):
    """Pale-silver Eclipse emblem: bold ring with a crescent cut by an offset dark disc, outlined."""
    r1 = np.hypot(x - cx, y - cy)
    r2 = np.hypot(x - cx - r * 0.38, y - cy + r * 0.22)
    ring = (r1 < r) & (r1 >= r - 1.6)
    cres = (r1 < r - 2.4) & (r2 >= r * 0.62)
    img = np.where((r1 < r + 1.0) & (r1 >= r), 1, img)
    img = np.where(ring, 7, img)
    img = np.where(ring & (y > cy + r * 0.5), 8, img)
    img = np.where(cres, 7, img)
    img = np.where(cres & (x > cx + r * 0.1) & (y > cy), 8, img)
    img = np.where((r1 < r - 1.6) & (r1 >= r - 2.4), 1, img)
    return img


def tex_tent():
    A = Atlas("r217_tent", TENT_PAL)
    # slope 32 x 32 (u along z, v = 0 at the ridge): canvas, emblem centred, outlined front/back/eave edges
    x, y, b = A.local("canvas")
    img = canvas_base(x, y, b, 90)
    img = eclipse(img, x, y, 15.5, 16.5, 8.0)
    img = np.where((y > 27) & (vnoise(x.shape, 12, 91) > 0.5), 10, img)    # snow crust at the hem
    img = np.where(y >= 30, np.where(b > -0.1, 9, 10), img)
    img = outline(img, x, y, 32, 32, 1, "lrb")
    img = np.where(((x == 1) | (x == 30) | (y == 30)) & (img != 9), 2, img)      # 2-texel dark rim
    A.put("canvas", img)
    # emblem overlay 32 x 32 (c0): the same Eclipse emblem alone, drawn unlit over both slopes so it stays a
    # pale-silver focal mark in the night snow
    x, y, b = A.local("emblem")
    img = eclipse(np.zeros(x.shape, int), x, y, 15.5, 16.5, 8.0)
    img = np.where((img == 1) & (np.hypot(x - 15.5, y - 16.5) < 5.0), 0, img)      # keep the canvas inside the ring
    A.put("emblem", img)

    # front gable 32 x 24 (triangle apex at (16, 0), base row 23): open doorway, outlined sloped edges
    x, y, b = A.local("gable")
    t = 0.62 + 0.25 * (fbm(x.shape, 94) - 0.5)
    img = ramp(t, [3, 4, 5], b, 0.5)
    slope = np.abs(x - 15.5) - (y + 0.5) * (16.0 / 24.0)
    img = np.where(slope > -1.6, 1, img)                                    # sloped outline (2 texels)
    door = np.abs(x - 15.5) < (y - 6.0) * (6.5 / 17.0)
    img = np.where(door, np.where(y > 19, 2, 14), img)
    img = np.where(door & (np.abs(x - 15.5) > (y - 6.0) * (6.5 / 17.0) - 1.0), 1, img)
    img = np.where(door & (y > 19) & (b > 0.1), 3, img)                     # faint floor glow inside
    rim = (~door) & (np.abs(x - 15.5) < (y - 6.0) * (6.5 / 17.0) + 1.5) & (y > 6)
    img = np.where(rim, 6, img)                                             # lit hem of the opening
    for sx in (6, 25):                                                      # rolled tie-backs
        img = np.where((np.abs(x - sx) <= 1.5) & (np.abs(y - 15) <= 1), 12, img)
        img = np.where((np.abs(x - sx) <= 1.5) & (y == 14), 11, img)
    img = np.where(y == 23, 1, img)
    A.put("gable", img)

    # tied-back flap lining 16 x 24: lighter inner canvas with outline
    x, y, b = A.local("flap")
    img = ramp(0.6 + 0.3 * (vnoise(x.shape, 5, 95) - 0.5) - 0.2 * y / 23, [4, 5, 6], b, 0.5)
    img = np.where((x + y) % 7 == 0, 4, img)
    img = outline(img, x, y, 16, 24, 1)
    A.put("flap", img)

    x, y, b = A.local("rope")                          # 16 x 4 twisted rope, dark edge
    tw = ((x + 2 * y) % 4 < 2)
    img = np.where((y >= 1) & (y <= 2), np.where(tw, 11, 12), 0)
    img = np.where((y == 0) & tw, 12, img)
    img = np.where(y == 3, 13, img)
    A.put("rope", img)

    x, y, b = A.local("wood")                          # 16 x 8 pole / stake grain
    g = vnoise(x.shape, 4, 96)
    img = ramp(0.5 + 0.4 * np.sin(y * 1.3 + 3 * g) * 0.5, [13, 12, 15], b)
    img = np.where(y == 0, 15, img)
    img = np.where(y == 7, 1, img)
    A.put("wood", img)

    x, y, b = A.local("back")                          # 16 x 12 back gable / side wall
    img = canvas_base(x, y, b, 97, 0.4)
    img = outline(img, x, y, 16, 12, 1, "b")
    A.put("back", img)

    x, y, b = A.local("wall")                          # 32 x 8 low side wall with banked snow
    img = ramp(0.45 + 0.3 * (vnoise(x.shape, 6, 98) - 0.5), [2, 3, 4], b)
    bank = y > 3.5 + 1.5 * vnoise(x.shape, 6, 99) + 0.8 * b
    img = np.where(bank, np.where(y > 5, 10, 9), img)
    img = np.where(y == 0, 1, img)
    A.put("wall", img)

    # ridge snow 32 x 8 (v = 0 at the ridge): heaped snow, irregular dithered lower edge, cool outline below
    x, y, b = A.local("ridge_snow")
    low = 3.8 + 2.2 * vnoise(x.shape, 7, 100) + 0.8 * np.sin(x * 0.7)
    img = np.where(y < low + 0.7 * b, np.where((y < 1.5) | (b > 0.3), 9, 9), 0)
    img = np.where((img > 0) & (y >= low - 1.2), 10, img)
    img = np.where((img == 0) & (y < low + 1.2) & (y >= low + 0.7 * b), 2, img)
    A.put("ridge_snow", img)
    return A


# ---------------------------------------------------------------------------------------------------------------
# r217_camp: lantern, crate, scanner, shard, journal, packed-snow clearing
# ---------------------------------------------------------------------------------------------------------------

CAMP_PAL = [
    (255, 0, 255),    # 0 transparent
    (18, 14, 26),     # 1 outline / iron black
    (60, 56, 70),     # 2 iron / gunmetal
    (108, 104, 120),  # 3 steel lit
    (196, 150, 64),   # 4 brass
    (255, 250, 222),  # 5 flame white-hot
    (255, 204, 90),   # 6 amber glow
    (236, 130, 40),   # 7 deep amber
    (70, 44, 30),     # 8 crate wood dark
    (124, 86, 52),    # 9 crate wood
    (170, 128, 80),   # 10 crate wood lit
    (240, 244, 252),  # 11 snow
    (180, 194, 226),  # 12 packed snow
    (104, 40, 220),   # 13 electric violet
    (172, 120, 255),  # 14 violet glow
    (236, 220, 255),  # 15 violet white
]


def tex_camp():
    A = Atlas("r217_camp", CAMP_PAL)
    x, y, b = A.local("glass")                         # warm glowing glass panel, white-hot flame core
    d = np.hypot(x - 7.5, (y - 8.5) / 1.3) / 8.0
    img = ramp(1.0 - d, [7, 6, 6, 5, 5], b, 0.4)
    img = np.where(((x - 7.5) ** 2 / 3.0 + (y - 8.5) ** 2 / 12.0) < 1.0, 5, img)
    img = np.where((x == 0) | (x == 15) | (y == 0) | (y == 15), 1, img)
    img = np.where((x == 1) | (x == 14) | (y == 1) | (y == 14), 4, img)
    A.put("glass", img)

    x, y, b = A.local("iron")                          # iron frame / cap with brass rivets
    img = ramp(0.4 + 0.3 * (vnoise(x.shape, 4, 101) - 0.5) - 0.3 * (y / 15 - 0.5), [1, 2, 3], b)
    img = np.where((y == 0) | (y == 15), 1, img)
    img = np.where(((x % 5) == 2) & ((y % 5) == 2), 4, img)
    img = np.where((y <= 1) & (vnoise(x.shape, 8, 102) > 0.4), 11, img)
    A.put("iron", img)

    x, y, b = A.local("crate")                         # 32 x 24 crate face with the violet Eclipse stencil
    plank = (y // 6)
    t = 0.55 + 0.3 * (vnoise(x.shape, 6, 103) - 0.5) + 0.08 * (plank % 2)
    img = ramp(t, [8, 9, 10], b)
    img = np.where(y % 6 == 5, 8, img)
    frame = (x <= 2) | (x >= 29) | (y <= 2) | (y >= 21)
    img = np.where(frame, 10, img)
    diag = np.abs((y - 3) - (x - 3) * 18.0 / 26.0) < 1.3
    img = np.where(diag & ~frame, 10, img)
    dx, dy = x - 21.5, y - 12.5
    r1, r2 = np.hypot(dx, dy), np.hypot(dx + 1.6, dy - 0.8)
    sten = ((r1 < 5.0) & (r1 > 3.6)) | ((r1 < 3.6) & (r2 > 2.8))
    img = np.where(sten & ~frame, 13, img)
    img = np.where((y <= 1) | ((y <= 3) & (vnoise(x.shape, 10, 104) > 0.45)), 11, img)
    img = outline(img, x, y, 32, 24, 1, "lrb")
    A.put("crate", img)

    x, y, b = A.local("crate_side")                    # 32 x 8 plank side / top
    img = ramp(0.5 + 0.3 * (vnoise(x.shape, 6, 105) - 0.5), [8, 9, 10], b)
    img = np.where(y == 0, 11, img)
    img = np.where(y == 7, 1, img)
    A.put("crate_side", img)

    x, y, b = A.local("screen")                        # 16 x 16 lid screen: vivid electric-violet compass
    img = np.full(x.shape, 1)
    d = np.hypot(x - 7.5, y - 7.5)
    img = np.where(d < 6.6, ramp(1.0 - d / 6.6, [13, 14, 14, 15], b, 0.4), img)
    img = np.where((d >= 6.6) & (d < 7.4), 4, img)
    for k in range(8):
        a = k * np.pi / 4
        tx, ty = 7.5 + 5.2 * np.cos(a), 7.5 + 5.2 * np.sin(a)
        img[int(round(ty)), int(round(tx))] = 15 if k == 2 else 13
    needle = (np.abs(x - 7.5) <= 0.6 + (12.5 - y) * 0.08) & (y >= 7) & (y <= 12)
    img = np.where(needle, 5, img)
    img = np.where((np.abs(x - 7.5) < 0.6) & (y >= 3) & (y < 7), 13, img)
    img[7:9, 7:9] = 4
    A.put("screen", img)

    x, y, b = A.local("lid")                           # 16 x 16 lid back: gunmetal with brass corners
    img = ramp(0.45 + 0.25 * (vnoise(x.shape, 4, 106) - 0.5), [2, 2, 3], b)
    img = np.where(((x <= 1) | (x >= 14)) & ((y <= 1) | (y >= 14)), 4, img)
    img = outline(img, x, y, 16, 16, 1)
    A.put("lid", img)

    x, y, b = A.local("case")                          # 16 x 16 case body with a glowing violet status strip
    img = ramp(0.45 + 0.25 * (vnoise(x.shape, 4, 107) - 0.5) - 0.2 * (y / 15 - 0.5), [1, 2, 3], b)
    img = np.where((y >= 4) & (y <= 6) & (x >= 2) & (x <= 13), np.where(y == 5, 15, 14), img)
    img = np.where(((y == 11) & ((x == 3) | (x == 12))), 4, img)
    img = outline(img, x, y, 16, 16, 1)
    A.put("case", img)

    x, y, b = A.local("shard")                         # violet shard facets, outlined
    body = (np.abs(x - 7.5) < (1.0 + (y - 1) * 0.35)) & (y >= 1) & (y <= 11) | \
           ((np.abs(x - 7.5) < (4.5 - (y - 11) * 1.1)) & (y > 11) & (y <= 15))
    img = np.where(body, np.where(x < 7.5, 14, 13), 0)
    img = np.where(body & (np.abs(x - 7.0) < 0.6) & (y < 12), 15, img)
    A.put("shard", img)

    x, y, b = A.local("journal")                       # 16 x 16 open field journal
    img = np.zeros(x.shape, int)
    page = (x >= 1) & (x <= 14) & (y >= 3) & (y <= 13)
    img = np.where(page, 11, img)
    img = np.where(page & ((x == 7) | (x == 8)), 12, img)
    img = np.where(page & (y % 2 == 1) & (y > 4) & (y < 12) & (x != 7) & (x != 8) & (x > 1) & (x < 14) &
                   (vnoise(x.shape, 16, 108) > 0.3), 2, img)
    img = np.where((y == 14) & (x >= 1) & (x <= 14), 8, img)
    img = np.where((x >= 10) & (x <= 11) & (y >= 1) & (y <= 6), 13, img)
    A.put("journal", img)

    # packed-snow clearing 32 x 32: trampled pale blue-grey centre, dithered rim fading into the fresh snow
    x, y, b = A.local("clear")
    d = np.hypot(x - 15.5, y - 15.5) / 15.5 + 0.22 * (vnoise(x.shape, 5, 109) - 0.5)
    img = np.where(d + 0.35 * b < 0.95, 12, 0)
    img = np.where((img == 12) & (d + 0.35 * b > 0.78), 11, img)
    A.put("clear", img)
    return A


TEXTURES = [("r216_stone", tex_stone), ("r216_offer", tex_offer), ("r216_glow", tex_glow),
            ("r217_tent", tex_tent), ("r217_camp", tex_camp)]


def pal_name(tex):
    return tex + "_pl"


def generate():
    out = []
    for name, fn in TEXTURES:
        A = fn()
        idx = np.asarray(A.img, int)
        ncol = 32 if name in ALPHA_FMT else 16
        assert idx.shape == (N, N) and idx.min() >= 0 and idx.max() < ncol, name
        assert len(A.pal) == ncol, name
        al = np.asarray(A.alpha, int) if name in ALPHA_FMT else None
        out.append((name, idx, [snap(c) for c in A.pal], al))
    return out


def encode(name, idx, pal, al):
    flat = idx.reshape(-1).tolist()
    if al is not None:
        a = al.reshape(-1).tolist()
        data = bytes(flat[i] | a[i] << 5 for i in range(len(flat)))
        tex = dict(name=name, fmt=1, w=N, h=N, c0=0, data=data)
    else:
        data = bytes(flat[i] | flat[i + 1] << 4 for i in range(0, len(flat), 2))
        tex = dict(name=name, fmt=3, w=N, h=N, c0=1 if name in TRANSPARENT else 0, data=data)
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
    for name, idx, pal, al in gen:
        t, p = encode(name, idx, pal, al)
        for a in (t["name"], p["name"]):
            if a in names:
                fails.append(f"{a} clashes with a stock set-014 entry")
            if len(a) > 15:
                fails.append(f"{a} is longer than 15 characters")
        new_t.append(t)
        new_p.append(p)
        rows.append((name, p["name"], f"{N}x{N}", nsbtx.FMT_NAMES[t["fmt"]], len(t["data"]), 2 * len(pal), t["c0"],
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
        if not t2 or t2["data"] != t["data"] or (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != (t["fmt"], t["w"], t["h"], t["c0"]):
            fails.append(f"stock texture {t['name']} changed")
    for p in sb["palettes"]:
        if p["name"] not in OP or not OP[p["name"]]["data"].startswith(p["data"]):
            fails.append(f"stock palette {p['name']} changed")
    for name, idx, pal, al in gen:
        t2, p2 = OT.get(name), OP.get(pal_name(name))
        if not t2 or not p2:
            fails.append(f"{name}: missing after build")
            continue
        rgba, ind = nsbtx.decode(t2, p2["colors"])
        want_fmt = (1, N, N, 0) if name in ALPHA_FMT else (3, N, N, 1 if name in TRANSPARENT else 0)
        if (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != want_fmt:
            fails.append(f"{name}: format/size changed in the round trip")
        if [list(r) for r in ind] != idx.tolist():
            fails.append(f"{name}: texel indices differ after the round trip")
        want = [nsbtx.rgb(nsbtx.bgr555(pal[i])) for i in idx.reshape(-1).tolist()]
        got = [tuple(px[:3]) for row in rgba for px in row]
        if got != want:
            fails.append(f"{name}: decoded colours differ from the BGR555 palette")
        if al is not None:
            ga = [px[3] for row in rgba for px in row]
            if ga != [a * 255 // 7 for a in al.reshape(-1).tolist()]:
                fails.append(f"{name}: decoded alpha differs")
            if len(set(al.reshape(-1).tolist())) < 6:
                fails.append(f"{name}: alpha ramp has fewer than 6 levels")
    if len(so["textures"]) != len(sb["textures"]) + len(new_t) or len(so["palettes"]) != len(sb["palettes"]) + len(new_p):
        fails.append("entry count mismatch")
    vb, vo = nsbtx.vram_usage(sb), nsbtx.vram_usage(so)
    if sum(vo) > VRAM_TARGET:
        fails.append(f"set VRAM {sum(vo)} B > target {VRAM_TARGET}")
    table = {t["name"]: {"size": [t["w"], t["h"]]} for t in so["textures"]}
    for name, _, _, _ in gen:
        table[name]["palette"] = pal_name(name)
    return dict(bytes=out, rows=rows, fails=fails, vram=(vb, vo), table=table, generated=gen,
                palettes={p["name"] for p in so["palettes"]}, stock_textures=len(sb["textures"]),
                stock_palettes=len(sb["palettes"]))


def write_preview(d, gen):
    from PIL import Image
    os.makedirs(d, exist_ok=True)
    S = 6
    sheet = Image.new("RGB", (len(gen) * (N * S + 8), N * S), (30, 34, 48))
    for k, (name, idx, pal, al) in enumerate(gen):
        bg = np.array([60, 66, 84], float)
        cols = np.array([pal[i] for i in idx.reshape(-1).tolist()], float)
        if al is not None:
            a = (al.reshape(-1, 1) / 7.0)
            cols = cols * a + bg * (1 - a)
        elif name in TRANSPARENT:
            cols[idx.reshape(-1) == 0] = bg
        img = Image.fromarray(cols.reshape(N, N, 3).astype("uint8"))
        img.save(os.path.join(d, name + ".png"))
        sheet.paste(img.resize((N * S, N * S), Image.NEAREST), (k * (N * S + 8), 0))
    sheet.save(os.path.join(d, "r216_217_textures_sheet.png"))


def report(res):
    vb, vo = res["vram"]
    print(f"map_texture_set_080 = git {BASE_REV}:{BASE_SET_REL} ({res['stock_textures']} textures, "
          f"{res['stock_palettes']} palettes) + {len(res['rows'])} Memorial Ridge / Indra's Camp atlases")
    for name, pn, size, fmt, tb, pb, c0, nc in res["rows"]:
        print(f"  {name:12s} {pn:15s} {size:6s} {fmt:6s} texels {tb:5d} B  palette {pb} B  c0={c0}  colours {nc}")
    print(f"VRAM: {sum(vb)} -> {sum(vo)} B ({sum(vo) / 1024:.1f} KB; texels {vb[0]} -> {vo[0]}, palettes {vb[1]} -> "
          f"{vo[1]}); target {VRAM_TARGET // 1024} KB")


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
        print("PASS appended textures round-trip (texels, BGR555 colours, A3I5 alpha); stock textures/palettes "
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
