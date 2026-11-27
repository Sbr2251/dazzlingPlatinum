#!/usr/bin/env python3
"""Routes 216-217 (Memorial Ridge & Indra's Camp) texture set: map_texture_set_080 = stock map_texture_set_014 (read
from git HEAD, so reruns never append twice) + four procedurally drawn 64x64 pltt16 atlases. Pure math (NumPy):
value noise, SDF shapes and hand-tuned 16-colour BGR555 palettes, quantised with a 4x4 Bayer ordered dither so every
texel snaps to Platinum's pixel-art grid (atlas regions are mapped at ~16-22 texels per tile).

Usage:
  ~/.venvs/desmume/bin/python tools/routes/r216_217/textures.py                 dry run: table, VRAM, round trip
  ~/.venvs/desmume/bin/python tools/routes/r216_217/textures.py --preview DIR   also DIR/<texture>.png + x6 sheet
  ~/.venvs/desmume/bin/python tools/routes/r216_217/textures.py --write         write SET_REL (refuses on FAIL)

Atlases (texel boxes x0, y0, x1, y1, exclusive ends, in REGIONS; build_art.py maps faces onto them):
  r216_stone   opaque. Snow-dusted carved grey granite ashlar ("granite"), frost-crusted slate flags in 1-tile
               slabs ("slate"), Teo's stele face with the bevelled frame, carved emblem and the inlaid dark plaque
               with engraved silver lines ("stele"), snow cap ("snow"), frost-crusted cairn boulder ("cairn"),
               carved coping band ("coping") and a plain granite side ("side").
  r216_offer   c0=1. Frozen winter-flower wreath ("wreath"), warm vigil lantern glass ("glow"), candle stub with
               flame ("candle"), tied violet scarf with fringed tails ("scarf"), faint violet shard dust ("dust"),
               fresh boot prints ("prints"), frozen bouquet ("bouquet"), soft amber light pool ("halo").
  r217_tent    c0=1. Weathered dark-violet expedition canvas with seams, patches and frost ("canvas"), the front
               flap with the faded eclipse sigil and tie-backs ("flap"), guy rope ("rope"), pole / stake wood
               ("wood"), canvas gable end ("gable").
  r217_camp    c0=1. Warm expedition-lantern glass ("glass") and its iron/brass frame ("iron"), snow-dusted supply
               crate face with the Eclipse stencil ("crate") and its plain side ("crate_side"), shard-scanner case
               lid with the violet compass screen and the needle pointing south ("screen"), the case body with its
               violet status strip ("case"), a violet shard ("shard"), packed-snow footprint ring ("ring"), the field
               journal ("journal") and the faint violet south-pointing trace ("beam").
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
VRAM_BUDGET = 384 * 1024
N = 64

BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], float) + 0.5) / 16.0 - 0.5
YY, XX = np.mgrid[0:N, 0:N].astype(float)
BAYER = BAYER4[(YY % 4).astype(int), (XX % 4).astype(int)]

REGIONS = {
    "r216_stone": {"granite": (0, 0, 32, 32), "slate": (32, 0, 64, 32), "stele": (0, 32, 24, 64),
                   "snow": (24, 32, 40, 48), "coping": (24, 48, 40, 56), "side": (24, 56, 40, 64),
                   "cairn": (40, 32, 64, 64)},
    "r216_offer": {"wreath": (0, 0, 32, 32), "glow": (32, 0, 48, 32), "candle": (48, 0, 64, 32),
                   "scarf": (0, 32, 32, 48), "dust": (32, 32, 64, 48), "prints": (0, 48, 32, 64),
                   "bouquet": (32, 48, 48, 64), "halo": (48, 48, 64, 64)},
    "r217_tent": {"canvas": (0, 0, 64, 32), "flap": (0, 32, 32, 64), "rope": (32, 32, 64, 36),
                  "wood": (32, 36, 64, 44), "gable": (32, 44, 64, 64)},
    "r217_camp": {"glass": (0, 0, 16, 16), "iron": (0, 16, 16, 32), "crate": (16, 0, 48, 24),
                  "crate_side": (16, 24, 48, 32), "screen": (48, 0, 64, 16), "case": (48, 16, 64, 32),
                  "shard": (0, 32, 16, 48), "journal": (0, 48, 16, 64), "ring": (16, 32, 48, 64),
                  "beam": (48, 32, 64, 64)},
}
TRANSPARENT = {"r216_offer", "r217_tent", "r217_camp"}


def snap(c):
    return tuple(int(v) >> 3 << 3 for v in c)


def vnoise(shape, cells, seed):
    """Value noise in [0, 1) over an h x w region (cells lattice per region side), smoothstep-bilinear."""
    h, w = shape
    rng = np.random.RandomState(seed)
    g = rng.rand(cells + 1, cells + 1)
    y, x = np.mgrid[0:h, 0:w].astype(float)
    fx, fy = x * cells / w, y * cells / h
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - x0, fy - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a = g[y0, x0] * (1 - tx) + g[y0, x0 + 1] * tx
    b = g[y0 + 1, x0] * (1 - tx) + g[y0 + 1, x0 + 1] * tx
    return a * (1 - ty) + b * ty


def fbm(shape, seed, octs=((3, 0.5), (6, 0.3), (12, 0.2))):
    return sum(wt * vnoise(shape, c, seed + 37 * k) for k, (c, wt) in enumerate(octs))


class Atlas:
    """64x64 index canvas; regions drawn in local coordinates."""

    def __init__(self, name, pal):
        self.name, self.pal = name, pal
        self.img = np.zeros((N, N), int)

    def region(self, key):
        x0, y0, x1, y1 = REGIONS[self.name][key]
        return x0, y0, x1, y1

    def local(self, key):
        x0, y0, x1, y1 = self.region(key)
        y, x = np.mgrid[0:y1 - y0, 0:x1 - x0].astype(float)
        return x, y, BAYER[y0:y1, x0:x1]

    def put(self, key, arr, mask=None):
        x0, y0, x1, y1 = self.region(key)
        sub = self.img[y0:y1, x0:x1]
        if mask is None:
            sub[:] = arr
        else:
            sub[mask] = np.broadcast_to(arr, sub.shape)[mask]

    def get(self, key):
        x0, y0, x1, y1 = self.region(key)
        return self.img[y0:y1, x0:x1]


def ramp(t, idx, b, dither=1.0):
    n = len(idx)
    v = np.clip(np.floor(np.clip(t, 0, 1) * (n - 1) + 0.5 + b * dither), 0, n - 1).astype(int)
    return np.array(idx)[v]


# ---------------------------------------------------------------------------------------------------------------
# r216_stone: carved granite, slate flags, Teo's stele face, snow, cairn
# ---------------------------------------------------------------------------------------------------------------

STONE_PAL = [
    (20, 22, 32),     # 0 outline / deep carved shadow
    (44, 48, 62),     # 1 granite crevice
    (64, 68, 84),     # 2 dark granite
    (86, 90, 106),    # 3 granite shade
    (108, 112, 126),  # 4 granite mid
    (130, 134, 148),  # 5 granite light
    (154, 158, 170),  # 6 granite lit
    (180, 186, 198),  # 7 frost / chisel highlight
    (204, 212, 226),  # 8 snow shade
    (230, 236, 246),  # 9 snow
    (250, 252, 255),  # 10 snow highlight
    (132, 150, 184),  # 11 icy blue frost shadow
    (28, 28, 40),     # 12 plaque black
    (50, 52, 70),     # 13 plaque slate
    (196, 202, 216),  # 14 engraved silver
    (88, 94, 124),    # 15 blue-violet slate
]


def snow_dust(x, y, b, seed, top=3.0, amount=0.5):
    """Mask of snow texels settling on upper edges: dense on the top rows, flecks lower down."""
    n = vnoise(x.shape, 6, seed)
    depth = top + 2.0 * n
    return (y < depth) | ((vnoise(x.shape, 16, seed + 1) > 1.0 - amount * 0.18) & (b > 0.1))


def tex_stone():
    A = Atlas("r216_stone", STONE_PAL)
    # granite ashlar: 2 courses of 16 px (1 tile), running bond, chisel speckle, snow on each course top
    x, y, b = A.local("granite")
    base = 0.52 + 0.55 * (fbm(x.shape, 11, ((2, 0.6), (4, 0.3), (8, 0.1))) - 0.5)
    img = ramp(base, [3, 4, 5, 6], b, 0.55)
    course = (y % 16)
    off = np.where((y // 16) % 2 == 0, 0, 8)
    jx = (x + off) % 16
    img = np.where((course == 15) | (jx == 15), 1, img)                     # mortar joints (crevice)
    img = np.where(((course == 14) | (jx == 14)) & (img > 2), 2, img)        # joint shade
    img = np.where(((course == 0) | (jx == 0)) & (img < 6), np.where(b > -0.2, 6, 5), img)  # lit bevel
    img = np.where((course <= 1) & (vnoise(x.shape, 8, 13) > 0.45), np.where(course == 0, 9, 8), img)  # snow on ledges
    img = np.where((vnoise(x.shape, 32, 14) > 0.9) & (course > 2) & (course < 13), 7, img)  # frost speckle
    img = np.where((vnoise(x.shape, 32, 15) > 0.92) & (course > 2) & (course < 13), 2, img)  # dark mica flecks
    A.put("granite", img)

    # slate flags: 2x2 one-tile slabs, cool slate grey-violet, frost crust at the edges, snow in the joints
    x, y, b = A.local("slate")
    lx, ly = x % 16, y % 16
    slab = (x // 16) + 2 * (y // 16)
    t = 0.45 + 0.45 * (fbm(x.shape, 21, ((2, 0.6), (4, 0.3), (8, 0.1))) - 0.5) + 0.07 * slab - 0.1
    img = ramp(t, [15, 3, 4], b, 0.35)
    edge = np.minimum(np.minimum(lx, 15 - lx), np.minimum(ly, 15 - ly))
    frost = (edge <= 1) & (vnoise(x.shape, 10, 22) > 0.35)
    img = np.where((lx == 15) | (ly == 15), 1, img)                        # carved joint (shadow S/E)
    img = np.where(((lx == 0) | (ly == 0)) & ~((lx == 15) | (ly == 15)), 5, img)   # lit bevel (N/W)
    img = np.where(((lx == 0) | (ly == 0)) & frost, 8, img)                # frost crust on the lit edge
    img = np.where(((lx == 15) | (ly == 15)) & (vnoise(x.shape, 12, 26) > 0.62), 8, img)  # snow lodged in joints
    crack = np.abs(np.sin((lx * 0.9 + ly * 0.4 + 3 * vnoise(x.shape, 4, 23)) * 0.8)) < 0.05
    img = np.where(crack & (edge > 2), 2, img)
    img = np.where((vnoise(x.shape, 32, 24) > 0.95) & (edge > 1), 11, img)   # icy frost flecks
    A.put("slate", img)

    # Teo's stele face (24 x 32): granite frame, carved emblem, inlaid plaque with engraved lines
    x, y, b = A.local("stele")
    t = 0.55 + 0.35 * (fbm(x.shape, 31) - 0.5)
    img = ramp(t, [3, 4, 5, 6], b)
    img = np.where((x == 0) | (y == 0), 7, img)                     # chamfer light
    img = np.where((x == 23) | (y == 31), 1, img)                   # chamfer shade
    img = np.where((x == 1) | (y == 1), np.where(img > 4, 6, img), img)
    img = np.where(y <= 2, np.where(b > -0.25, 9, 8), img)          # snow settled on the top edge
    # carved emblem: a small mountain peak with a falling star (Teo, lost to the mountain)
    ex, ey = x - 11.5, y - 6.5
    peak = (ey > -2 + np.abs(ex) * 0.9) & (ey < 2.6) & (np.abs(ex) < 5)
    img = np.where(peak, 2, img)
    img = np.where(peak & (ey < -0.2 + np.abs(ex) * 0.9) , 7, img)
    img = np.where(peak & (np.abs(ex) < 1.2) & (ey < -0.8), 8, img)       # snow summit
    star = ((np.abs(x - 17) + np.abs(y - 4)) <= 1.0)
    img = np.where(star, 14, img)
    img = np.where((y == 3) & (x >= 18) & (x <= 20), 7, img)              # star trail
    # inlaid dark plaque rows 11..27, cols 3..20: bevel, slate field, engraved silver lines
    px0, px1, py0, py1 = 3, 20, 11, 27
    inside = (x >= px0) & (x <= px1) & (y >= py0) & (y <= py1)
    pl = ramp(0.5 + 0.5 * (vnoise(x.shape, 8, 33) - 0.5), [12, 13, 12], b, 0.8)
    img = np.where(inside, pl, img)
    img = np.where(inside & ((x == px0) | (y == py0)), 0, img)            # carved recess (shadowed top/left)
    img = np.where(inside & ((x == px1) | (y == py1)), 6, img)            # lit lower/right lip
    # engraved lines: "TEO" as 3x5 glyphs, then two lines of smaller text strokes
    T = ["111", "010", "010", "010", "010"]
    E = ["111", "100", "110", "100", "111"]
    O = ["111", "101", "101", "101", "111"]
    gx = 6
    for g in (T, E, O):
        for r, row in enumerate(g):
            for c, ch in enumerate(row):
                if ch == "1":
                    img[13 + r, gx + c] = 14
        gx += 4
    rng = np.random.RandomState(34)
    for ry in (20, 22, 24):
        cx = 5
        while cx < 18:
            ln = rng.randint(1, 4)
            img[ry, cx:min(cx + ln, 19)] = 14 if ry != 24 else 13 + (rng.rand() > 0.5)
            cx += ln + 1
    img[24, 5:18] = np.where(np.arange(5, 18) % 2 == 0, 14, 13)               # dotted rule
    img[29:31, 4:20] = np.where(b[29:31, 4:20] > 0.0, 5, 4)                    # carved base fillet
    A.put("stele", img)

    # snow cap: fresh snow, blue-grey dithered shading downwards, sparkle highlights
    x, y, b = A.local("snow")
    t = 1.0 - y / 15.0 * 0.6 + 0.25 * (vnoise(x.shape, 4, 41) - 0.5)
    img = ramp(t, [11, 8, 9, 9, 10], b)
    img = np.where((vnoise(x.shape, 16, 42) > 0.85) & (b > 0.2), 10, img)
    A.put("snow", img)
    # coping band: carved granite moulding (lit top roll, shadow undercut)
    x, y, b = A.local("coping")
    img = np.select([y == 0, y <= 2, y == 3, y <= 5, y == 6], [9, 7, 5, 4, 2], 0)
    img = np.where((y == 4) & ((x % 8) == 7), 2, img)
    img = np.where((y <= 1) & (vnoise(x.shape, 8, 43) > 0.5), 10, img)
    A.put("coping", img)
    # plain granite side
    x, y, b = A.local("side")
    t = 0.42 + 0.35 * (fbm(x.shape, 44) - 0.5)
    img = ramp(t, [2, 3, 4, 5], b)
    img = np.where(y == 0, 7, img)
    img = np.where((vnoise(x.shape, 16, 45) > 0.85), 7, img)
    A.put("side", img)

    # cairn boulder: rounded rocks with snow caps and dark crevices
    x, y, b = A.local("cairn")
    img = np.zeros(x.shape, int) + 1
    rocks = [(12, 24, 11, 7), (7, 14, 7, 5), (17, 13, 6, 5), (12, 5, 5, 4)]
    for k, (cx, cy, rx, ry) in enumerate(rocks):
        d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
        inside = d < 1.0
        light = np.clip(0.55 - 0.35 * (x - cx) / rx - 0.45 * (y - cy) / ry + 0.25 * (vnoise(x.shape, 8, 50 + k) - 0.5), 0, 1)
        r = ramp(light, [2, 3, 4, 5, 6, 7], b)
        r = np.where(d > 0.78, np.where((y - cy) > 0, 1, 3), r)
        cap = inside & ((y - cy) < -ry * 0.35 + 1.2 * vnoise(x.shape, 10, 60 + k))
        r = np.where(cap, np.where(b > 0.25, 10, 9), r)
        r = np.where(cap & ((y - cy) > -ry * 0.35), 8, r)
        img = np.where(inside, r, img)
    A.put("cairn", img)
    return A


# ---------------------------------------------------------------------------------------------------------------
# r216_offer: wreath, glow, candle, scarf, dust, prints, bouquet, halo (colour 0 transparent)
# ---------------------------------------------------------------------------------------------------------------

OFFER_PAL = [
    (255, 0, 255),    # 0 transparent
    (24, 40, 36),     # 1 evergreen outline
    (40, 72, 60),     # 2 dark fir
    (64, 104, 84),    # 3 fir
    (112, 150, 136),  # 4 frosted fir
    (220, 232, 244),  # 5 frost white
    (150, 190, 236),  # 6 ice-blue petal
    (192, 48, 64),    # 7 winter berry red
    (255, 248, 208),  # 8 flame white-hot
    (255, 208, 96),   # 9 warm amber
    (232, 136, 48),   # 10 deep amber / orange
    (136, 64, 32),    # 11 ember / lantern lattice
    (84, 60, 144),    # 12 scarf violet
    (128, 100, 200),  # 13 scarf lilac / violet dust
    (200, 176, 248),  # 14 pale violet sparkle
    (148, 160, 184),  # 15 snow print shadow
]


def tex_offer():
    A = Atlas("r216_offer", OFFER_PAL)
    # wreath: fir ring with frost tips, ice-blue winter flowers and red berries, transparent hole and outside
    x, y, b = A.local("wreath")
    dx, dy = x - 15.5, y - 15.5
    r = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)
    rough = 1.6 * np.sin(ang * 14 + 2 * vnoise(x.shape, 6, 70)) + 0.8 * vnoise(x.shape, 12, 71)
    ring = (r > 7.0 - 0.5 * rough) & (r < 13.5 + rough * 0.6)
    light = np.clip(0.55 - 0.35 * dx / 14 - 0.45 * dy / 14 + 0.3 * (vnoise(x.shape, 10, 72) - 0.5), 0, 1)
    img = np.where(ring, ramp(light, [2, 3, 3, 4], b), 0)
    edge = ring & ~((r > 7.8 - 0.5 * rough) & (r < 12.8 + rough * 0.6))
    img = np.where(edge, 1, img)
    tips = ring & (vnoise(x.shape, 20, 73) > 0.72) & ~edge
    img = np.where(tips, 5, img)
    for k in range(7):                                   # ice-blue five-petal winter flowers on the ring
        a = k * 2 * np.pi / 7 + 0.4
        fx, fy = 15.5 + 10.2 * np.cos(a), 15.5 + 10.2 * np.sin(a)
        d = np.hypot(x - fx, y - fy)
        img = np.where(d < 2.2, 6, img)
        img = np.where(d < 0.9, 5, img)
    for k in range(9):                                    # berries
        a = k * 2 * np.pi / 9 + 0.9
        fx, fy = 15.5 + 8.6 * np.cos(a), 15.5 + 8.6 * np.sin(a)
        img = np.where(np.hypot(x - fx, y - fy) < 1.0, 7, img)
    A.put("wreath", img)

    # vigil lantern glass: a lattice window with a candle flame glowing behind (opaque inside the region)
    x, y, b = A.local("glow")
    cx, cy = 7.5, 17.0
    d = np.hypot((x - cx) / 1.0, (y - cy) / 1.8)
    img = ramp(1.0 - d / 10.0, [11, 10, 9, 9, 8], b)
    flame = ((x - cx) ** 2 / 4.0 + (y - cy - 1) ** 2 / 25.0) < 1.0
    img = np.where(flame, 8, img)
    img = np.where((x == 0) | (x == 15) | (y == 0) | (y == 31), 11, img)       # frame
    img = np.where((y == 10) | (y == 22) | (x == 5) | (x == 10), np.where(flame, 9, 11), img)  # lattice
    A.put("glow", img)

    # candle stub with flame
    x, y, b = A.local("candle")
    img = np.zeros(x.shape, int)
    body = (np.abs(x - 7.5) <= 3) & (y >= 14) & (y <= 29)
    img = np.where(body, ramp(0.8 - (x - 4.5) / 7.0, [15, 5, 5], b), img)
    img = np.where(body & (y == 14), 5, img)
    img = np.where((np.abs(x - 7.5) <= 4) & (y >= 29) & (y <= 31), 11, img)   # brass saucer
    fl = ((x - 7.5) ** 2 / 3.0 + (y - 9) ** 2 / 16.0) < 1.0
    img = np.where(fl, 9, img)
    img = np.where(((x - 7.5) ** 2 / 1.2 + (y - 10) ** 2 / 6.0) < 1.0, 8, img)
    img = np.where((np.abs(x - 7.5) < 0.6) & (y >= 12) & (y <= 13), 11, img)  # wick
    A.put("candle", img)

    # scarf: violet knitted scarf band with a knot and two fringed tails hanging to the right
    x, y, b = A.local("scarf")
    img = np.zeros(x.shape, int)
    band = (y >= 2) & (y <= 6) & (x <= 20)
    knit = ((x + y) % 3 == 0)
    img = np.where(band, np.where(knit, 12, 13), img)
    img = np.where(band & (y == 2), 14, img)
    knot = np.hypot(x - 21, y - 5) < 3.2
    img = np.where(knot, np.where(b > 0, 13, 12), img)
    for k, (x0, slope) in enumerate(((20, 0.25), (24, 0.45))):
        tail = (y >= 6) & (y <= 14) & (np.abs(x - (x0 + slope * (y - 6))) <= 1.6)
        img = np.where(tail, np.where((y + k) % 2 == 0, 12, 13), img)
        fringe = (y == 15) & (np.abs(x - (x0 + slope * 9)) <= 1.6) & (x % 2 == 0)
        img = np.where(fringe, 14, img)
    img = np.where(band & (y == 6), 12, img)
    A.put("scarf", img)

    # faint violet shard dust: a dithered sprinkle fading out from a centre, a few bright sparkles
    x, y, b = A.local("dust")
    d = np.hypot((x - 15.5) / 15.0, (y - 7.5) / 7.0)
    dens = np.clip(1.0 - d, 0, 1)
    sp = vnoise(x.shape, 32, 80)
    img = np.where(sp + 0.25 * b < dens * 0.62 - 0.05, 13, 0)
    img = np.where((sp > 0.9) & (dens > 0.35), 14, img)
    for (sx, sy) in ((12, 6), (19, 8), (15, 4)):
        img = np.where((np.abs(x - sx) + np.abs(y - sy)) == 1, 14, img)
        img[sy, sx] = 5
    A.put("dust", img)

    # fresh boot prints: two left/right pairs walking up the region, blue-grey hollows with snow rims
    x, y, b = A.local("prints")
    img = np.zeros(x.shape, int)
    for (px, py) in ((10, 2.5), (19, 5.5), (11, 9.0), (20, 12.0)):
        sole = ((x - px) / 1.8) ** 2 + ((y - py) / 2.2) ** 2 < 1.0
        heel = ((x - px) / 1.4) ** 2 + ((y - py - 2.6) / 1.0) ** 2 < 1.0
        p = sole | heel
        img = np.where(p, 15, img)
        rim = (((x - px) / 2.6) ** 2 + ((y - py - 0.6) / 3.6) ** 2 < 1.0) & ~p & (y > py) & (b > -0.1)
        img = np.where(rim & (img == 0), 5, img)
    A.put("prints", img)

    # frozen bouquet: white/ice-blue flowers on dark stems, tied with a violet ribbon
    x, y, b = A.local("bouquet")
    img = np.zeros(x.shape, int)
    for k in range(5):
        sx = 4 + k * 2
        stem = (np.abs(x - (8 + (sx - 8) * (1 - (y - 6) / 10.0))) < 0.6) & (y >= 6) & (y <= 15)
        img = np.where(stem, 2, img)
    for (fx, fy, c) in ((4, 4, 6), (8, 2.5, 5), (12, 4, 6), (6, 6.5, 5), (10, 6.5, 6)):
        d = np.hypot(x - fx, y - fy)
        img = np.where(d < 2.0, c, img)
        img = np.where(d < 0.7, 9, img)
    img = np.where((y >= 10) & (y <= 11) & (np.abs(x - 8) <= 2), 12, img)
    A.put("bouquet", img)

    # amber light pool: a sparse ordered-dither glow fading to transparent
    x, y, b = A.local("halo")
    d = np.hypot(x - 7.5, y - 7.5) / 8.0
    dens = np.clip(1.0 - d, 0, 1) ** 1.5
    img = np.where(b + 0.5 < dens * 0.7, 9, 0)
    A.put("halo", img)
    return A


# ---------------------------------------------------------------------------------------------------------------
# r217_tent: dark-violet canvas
# ---------------------------------------------------------------------------------------------------------------

TENT_PAL = [
    (255, 0, 255),    # 0 transparent
    (20, 14, 30),     # 1 outline
    (40, 28, 58),     # 2 canvas deep
    (58, 42, 82),     # 3 canvas dark
    (76, 56, 106),    # 4 canvas
    (96, 74, 128),    # 5 canvas lit
    (120, 98, 152),   # 6 canvas worn highlight
    (150, 132, 178),  # 7 faded sigil lilac
    (196, 200, 220),  # 8 frost
    (236, 240, 250),  # 9 snow
    (64, 50, 60),     # 10 patch (darker mauve)
    (176, 150, 110),  # 11 rope light
    (124, 98, 70),    # 12 rope / wood mid
    (82, 60, 44),     # 13 wood dark
    (48, 34, 28),     # 14 wood outline
    (156, 124, 88),   # 15 wood lit
]


def tex_tent():
    A = Atlas("r217_tent", TENT_PAL)
    x, y, b = A.local("canvas")                       # 64 x 32, v = 0 at the ridge
    t = 0.5 + 0.45 * (fbm(x.shape, 90, ((2, 0.6), (5, 0.3), (10, 0.1))) - 0.5) - 0.22 * (y / 31.0) + 0.1
    img = ramp(t, [2, 3, 4, 5, 6], b, 0.6)
    seam = (x % 16 == 0)
    img = np.where(seam, 2, img)
    img = np.where((x % 16 == 1) & (y % 3 == 0), 6, img)              # stitching
    # sagging fold shading between seams
    fold = np.sin((x % 16) / 16.0 * np.pi)
    img = np.where((fold < 0.25) & (img > 3) & ~seam, img - 1, img)
    # patches
    for (px, py, w, h) in ((38, 14, 7, 6), (9, 20, 6, 5)):
        p = (x >= px) & (x < px + w) & (y >= py) & (y < py + h)
        img = np.where(p, np.where(b > 0.1, 10, 3), img)
        img = np.where(p & ((x == px) | (y == py) | (x == px + w - 1) | (y == py + h - 1)) & ((x + y) % 2 == 0), 6, img)
    # frost and snow dusting thickest at the ridge, crusting at the hem
    sn = vnoise(x.shape, 16, 91)
    img = np.where(y < 2 + 3 * vnoise(x.shape, 8, 92), 9, img)
    img = np.where((y < 9) & (sn + 0.06 * y > 0.78), 8, img)
    img = np.where((y > 28) & (sn > 0.55), 8, img)
    img = np.where(y == 31, 1, img)
    A.put("canvas", img)

    x, y, b = A.local("flap")                         # 32 x 32 front flap: door slit, tie-backs, faded sigil
    t = 0.5 + 0.3 * (fbm(x.shape, 93) - 0.5)
    img = ramp(t, [3, 4, 5], b)
    img = np.where(np.abs(x - 15.5) < 0.8, 1, img)                   # door slit
    img = np.where((np.abs(x - 15.5) < 2.2) & (np.abs(x - 15.5) >= 0.8), 2, img)
    for sx in (9, 22):                                                # rolled tie-backs
        img = np.where((np.abs(x - sx) <= 2) & (np.abs(y - 18) <= 1), 12, img)
        img = np.where((np.abs(x - sx) <= 2) & (y == 17), 11, img)
    dx, dy = x - 15.5, y - 8.5                                        # eclipse sigil: ring + offset dark disc
    r1, r2 = np.hypot(dx, dy), np.hypot(dx + 2.0, dy - 1.0)
    sig = (r1 < 5.5) & (r1 > 4.2)
    img = np.where(sig & (b > -0.3), 7, img)
    img = np.where((r1 < 4.2) & (r2 > 3.4), 6, img)
    img = np.where((r1 < 4.2) & (r2 <= 3.4), 3, img)
    img = np.where((y < 3 + 2 * vnoise(x.shape, 8, 94)), 8, img)
    img = np.where((y >= 30), 9, img)                                 # snow banked at the hem
    A.put("flap", img)

    x, y, b = A.local("rope")                          # 32 x 4 twisted rope, transparent above/below
    img = np.zeros(x.shape, int)
    tw = ((x + 2 * y) % 4 < 2)
    img = np.where((y >= 1) & (y <= 2), np.where(tw, 11, 12), img)
    img = np.where((y == 0) & tw, 12, img)
    img = np.where((y == 3) & ~tw, 13, img)
    A.put("rope", img)

    x, y, b = A.local("wood")                          # 32 x 8 pole / stake grain
    g = vnoise(x.shape, 4, 95)
    img = ramp(0.5 + 0.4 * np.sin(y * 1.3 + 3 * g) * 0.5, [13, 12, 15], b)
    img = np.where((y == 0), 15, img)
    img = np.where((y == 7), 14, img)
    img = np.where((x % 13 == 5) & (y > 1) & (y < 6), 14, img)       # knots
    A.put("wood", img)

    x, y, b = A.local("gable")                         # 32 x 20 gable end (triangle drawn by geometry)
    t = 0.42 + 0.3 * (fbm(x.shape, 96) - 0.5) - 0.12 * y / 19.0
    img = ramp(t, [2, 3, 4, 5], b)
    img = np.where(x % 16 == 8, 2, img)
    img = np.where((y < 2), 9, img)
    img = np.where((y > 16) & (vnoise(x.shape, 12, 97) > 0.45), 8, img)
    A.put("gable", img)
    return A


# ---------------------------------------------------------------------------------------------------------------
# r217_camp: lantern, crate, scanner, shard, packed-snow ring, journal, beam
# ---------------------------------------------------------------------------------------------------------------

CAMP_PAL = [
    (255, 0, 255),    # 0 transparent
    (20, 18, 24),     # 1 outline / iron black
    (60, 56, 64),     # 2 iron / gunmetal
    (104, 100, 112),  # 3 steel lit
    (184, 140, 64),   # 4 brass
    (255, 244, 200),  # 5 flame core
    (255, 196, 88),   # 6 amber glow
    (220, 120, 40),   # 7 deep amber
    (72, 48, 34),     # 8 crate wood dark
    (122, 88, 56),    # 9 crate wood
    (166, 128, 84),   # 10 crate wood lit
    (232, 238, 248),  # 11 snow
    (168, 180, 204),  # 12 packed snow shadow
    (96, 56, 176),    # 13 violet
    (164, 120, 255),  # 14 violet glow
    (226, 208, 255),  # 15 violet white
]


def tex_camp():
    A = Atlas("r217_camp", CAMP_PAL)
    x, y, b = A.local("glass")                         # warm glowing glass panel
    d = np.hypot(x - 7.5, (y - 8.5) / 1.3) / 8.0
    img = ramp(1.0 - d, [7, 6, 6, 5], b)
    img = np.where(((x - 7.5) ** 2 / 2.2 + (y - 9) ** 2 / 9.0) < 1.0, 5, img)
    img = np.where((x == 0) | (x == 15) | (y == 0) | (y == 15), 4, img)
    img = np.where((x == 7) | (x == 8), np.where(np.abs(y - 9) < 3, 5, 4), img)   # centre bar (thin)
    A.put("glass", img)

    x, y, b = A.local("iron")                          # iron frame / cap with brass rivets
    img = ramp(0.4 + 0.3 * (vnoise(x.shape, 4, 100) - 0.5) - 0.3 * (y / 15 - 0.5), [1, 2, 3], b)
    img = np.where((y == 0) | (y == 15), 1, img)
    img = np.where(((x % 5) == 2) & ((y % 5) == 2), 4, img)
    img = np.where((y <= 1) & (vnoise(x.shape, 8, 101) > 0.4), 11, img)            # frost on top
    A.put("iron", img)

    x, y, b = A.local("crate")                         # 32 x 24 crate face
    plank = (y // 6)
    t = 0.5 + 0.3 * (vnoise(x.shape, 6, 102 + 0) - 0.5) + 0.08 * (plank % 2) + 0.15 * np.sin(x * 0.9 + plank * 2) * 0.3
    img = ramp(t, [8, 9, 10], b)
    img = np.where(y % 6 == 5, 8, img)                                 # plank gaps
    frame = (x <= 2) | (x >= 29) | (y <= 2) | (y >= 21)
    img = np.where(frame, np.where((x == 0) | (y == 0) | (x == 31) | (y == 23), 8, 10), img)
    diag = np.abs((y - 3) - (x - 3) * 18.0 / 26.0) < 1.3
    img = np.where(diag & ~frame, 10, img)
    img = np.where(diag & ~frame & (np.abs((y - 3) - (x - 3) * 18.0 / 26.0) > 0.6) & ((y - 3) - (x - 3) * 18.0 / 26.0 > 0), 8, img)
    for (nx, ny) in ((1, 1), (30, 1), (1, 22), (30, 22)):
        img[ny, nx] = 3
    # Eclipse stencil: a ring with an offset disc, sprayed violet
    dx, dy = x - 22.5, y - 12.5
    r1, r2 = np.hypot(dx, dy), np.hypot(dx + 1.6, dy - 0.8)
    sten = ((r1 < 4.5) & (r1 > 3.3)) | ((r1 < 3.3) & (r2 > 2.6))
    img = np.where(sten & ~frame & (b > -0.35), 13, img)
    img = np.where((y <= 1) | ((y <= 3) & (vnoise(x.shape, 10, 103) > 0.45)), 11, img)   # snow on the lid edge
    A.put("crate", img)

    x, y, b = A.local("crate_side")                    # 32 x 8 plain plank side
    img = ramp(0.45 + 0.3 * (vnoise(x.shape, 6, 104) - 0.5), [8, 9, 10], b)
    img = np.where((y == 0) | (y == 7), 8, img)
    img = np.where(y == 0, 11, img)
    A.put("crate_side", img)

    x, y, b = A.local("screen")                        # 16 x 16 scanner lid: violet compass, needle to the south
    img = ramp(0.4 + 0.2 * (vnoise(x.shape, 4, 105) - 0.5), [1, 2, 2], b)
    d = np.hypot(x - 7.5, y - 7.5)
    img = np.where(d < 6.0, ramp(1.0 - d / 6.0, [13, 13, 14], b), img)
    img = np.where((d >= 6.0) & (d < 7.0), 3, img)
    for k in range(8):                                                 # compass ticks
        a = k * np.pi / 4
        tx, ty = 7.5 + 5.0 * np.cos(a), 7.5 + 5.0 * np.sin(a)
        img[int(round(ty)), int(round(tx))] = 15 if k == 2 else 14
    needle = (np.abs(x - 7.5) <= 0.6 + (12.5 - y) * 0.06) & (y >= 7) & (y <= 12)   # points down = south
    img = np.where(needle, 15, img)
    img = np.where((np.abs(x - 7.5) < 0.6) & (y >= 4) & (y < 7), 13, img)          # dim tail (north)
    img[7:9, 7:9] = 4
    A.put("screen", img)

    x, y, b = A.local("case")                          # 16 x 16 case body with violet status strip
    img = ramp(0.45 + 0.25 * (vnoise(x.shape, 4, 106) - 0.5) - 0.2 * (y / 15 - 0.5), [1, 2, 3], b)
    img = np.where((y == 0) | (y == 15) | (x == 0) | (x == 15), 1, img)
    img = np.where((y == 5) & (x >= 3) & (x <= 12), np.where(x % 3 == 0, 15, 14), img)
    img = np.where(((y == 11) & ((x == 3) | (x == 12))), 4, img)                   # brass latches
    img = np.where((y <= 1) & (vnoise(x.shape, 8, 107) > 0.5), 11, img)
    A.put("case", img)

    x, y, b = A.local("shard")                         # violet shard facets
    img = np.zeros(x.shape, int)
    body = (np.abs(x - 7.5) < (1.0 + (y - 1) * 0.35)) & (y >= 1) & (y <= 11) | \
           ((np.abs(x - 7.5) < (4.5 - (y - 11) * 1.1)) & (y > 11) & (y <= 15))
    img = np.where(body, np.where(x < 7.5, 14, 13), img)
    img = np.where(body & (np.abs(x - 7.0) < 0.6) & (y < 12), 15, img)
    A.put("shard", img)

    x, y, b = A.local("ring")                          # 32 x 32 packed-snow trampled patch with boot prints
    d = np.hypot(x - 15.5, y - 15.5) / 15.5
    n = vnoise(x.shape, 6, 108)
    inside = d + 0.18 * (n - 0.5) + 0.12 * b < 0.92
    img = np.where(inside, np.where(n + 0.3 * b > 0.8, 12, 11), 0)
    rng = np.random.RandomState(109)
    for k in range(9):
        a = rng.rand() * 2 * np.pi
        rr = 4 + rng.rand() * 8
        px, py = 15.5 + rr * np.cos(a), 15.5 + rr * np.sin(a)
        ca, sa = np.cos(a + np.pi / 2), np.sin(a + np.pi / 2)
        u = (x - px) * ca + (y - py) * sa
        v = -(x - px) * sa + (y - py) * ca
        p = (u / 1.6) ** 2 + (v / 2.6) ** 2 < 1.0
        img = np.where(p & inside, 12, img)
        img = np.where(p & inside & (v > 1.4) & (b > 0), 11, img)
    A.put("ring", img)

    x, y, b = A.local("journal")                       # 16 x 16 open field journal
    img = np.zeros(x.shape, int)
    page = (x >= 1) & (x <= 14) & (y >= 3) & (y <= 13)
    img = np.where(page, 11, img)
    img = np.where(page & (x == 7) | page & (x == 8), 12, img)
    img = np.where(page & (y % 2 == 1) & (y > 4) & (y < 12) & (x != 7) & (x != 8) & (x > 1) & (x < 14) &
                   (vnoise(x.shape, 16, 110) > 0.3), 2, img)
    img = np.where((y == 14) & (x >= 1) & (x <= 14), 8, img)                       # leather cover edge
    img = np.where((x >= 10) & (x <= 11) & (y >= 1) & (y <= 6), 13, img)           # violet ribbon marker
    A.put("journal", img)

    x, y, b = A.local("beam")                          # 16 x 32 faint violet trace pointing south (v up)
    w = 2.5 + y / 31.0 * 3.5
    dens = np.clip(1.0 - np.abs(x - 7.5) / w, 0, 1) * np.clip(1.0 - y / 34.0, 0, 1)
    sp = vnoise(x.shape, 16, 111)
    img = np.where(sp + 0.3 * b < dens * 0.7 - 0.1, 14, 0)
    img = np.where((img == 14) & (b > 0.3) & (dens < 0.5), 13, img)
    img = np.where((sp > 0.88) & (dens > 0.3), 15, img)
    A.put("beam", img)
    return A


TEXTURES = [("r216_stone", tex_stone), ("r216_offer", tex_offer), ("r217_tent", tex_tent), ("r217_camp", tex_camp)]


def pal_name(tex):
    return tex + "_pl"


def generate():
    out = []
    for name, fn in TEXTURES:
        A = fn()
        idx = np.asarray(A.img, int)
        assert idx.shape == (N, N) and idx.min() >= 0 and idx.max() < 16, name
        assert len(A.pal) == 16, name
        out.append((name, idx, [snap(c) for c in A.pal]))
    return out


def encode(name, idx, pal):
    flat = idx.reshape(-1).tolist()
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
    for name, idx, pal in gen:
        t, p = encode(name, idx, pal)
        for a in (t["name"], p["name"]):
            if a in names:
                fails.append(f"{a} clashes with a stock set-014 entry")
            if len(a) > 15:
                fails.append(f"{a} is longer than 15 characters")
        new_t.append(t)
        new_p.append(p)
        rows.append((name, p["name"], f"{N}x{N}", len(t["data"]), 32, t["c0"], len(set(idx.reshape(-1).tolist()))))
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
    for name, idx, pal in gen:
        t2, p2 = OT.get(name), OP.get(pal_name(name))
        if not t2 or not p2:
            fails.append(f"{name}: missing after build")
            continue
        rgba, ind = nsbtx.decode(t2, p2["colors"])
        if (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != (3, N, N, 1 if name in TRANSPARENT else 0):
            fails.append(f"{name}: format/size changed in the round trip")
        if [list(r) for r in ind] != idx.tolist():
            fails.append(f"{name}: texel indices differ after the round trip")
        want = [nsbtx.rgb(nsbtx.bgr555(pal[i])) for i in idx.reshape(-1).tolist()]
        got = [tuple(px[:3]) for row in rgba for px in row]
        if got != want:
            fails.append(f"{name}: decoded colours differ from the BGR555 palette")
    if len(so["textures"]) != len(sb["textures"]) + len(new_t) or len(so["palettes"]) != len(sb["palettes"]) + len(new_p):
        fails.append("entry count mismatch")
    # idempotence: rebuilding from the same inputs gives the same bytes
    vb, vo = nsbtx.vram_usage(sb), nsbtx.vram_usage(so)
    if sum(vo) > VRAM_TARGET:
        fails.append(f"set VRAM {sum(vo)} B > target {VRAM_TARGET}")
    table = {t["name"]: {"size": [t["w"], t["h"]]} for t in so["textures"]}
    for name, _, _ in gen:
        table[name]["palette"] = pal_name(name)
    return dict(bytes=out, rows=rows, fails=fails, vram=(vb, vo), table=table, generated=gen,
                palettes={p["name"] for p in so["palettes"]}, stock_textures=len(sb["textures"]),
                stock_palettes=len(sb["palettes"]))


def write_preview(d, gen):
    from PIL import Image
    os.makedirs(d, exist_ok=True)
    S = 6
    sheet = Image.new("RGB", (len(gen) * (N * S + 8), N * S), (30, 34, 48))
    for k, (name, idx, pal) in enumerate(gen):
        img = Image.new("RGB", (N, N))
        cols = [(60, 66, 84) if (name in TRANSPARENT and i == 0) else pal[i] for i in idx.reshape(-1).tolist()]
        img.putdata(cols)
        img.save(os.path.join(d, name + ".png"))
        sheet.paste(img.resize((N * S, N * S), Image.NEAREST), (k * (N * S + 8), 0))
    sheet.save(os.path.join(d, "r216_217_textures_sheet.png"))


def report(res):
    vb, vo = res["vram"]
    print(f"map_texture_set_080 = git {BASE_REV}:{BASE_SET_REL} ({res['stock_textures']} textures, "
          f"{res['stock_palettes']} palettes) + {len(res['rows'])} Memorial Ridge / Indra's Camp atlases")
    for name, pn, size, tb, pb, c0, nc in res["rows"]:
        print(f"  {name:12s} {pn:15s} {size:6s} texels {tb:5d} B  palette {pb} B  c0={c0}  colours {nc}")
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
        print("PASS appended textures round-trip (texels + BGR555 colours); stock textures/palettes unchanged; "
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
