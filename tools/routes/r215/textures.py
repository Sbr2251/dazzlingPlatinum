#!/usr/bin/env python3
"""Route 215 flooded-lowland texture set (v3): map_texture_set_078 = stock map_texture_set_010 (git BASE_REV) +
nine procedurally painted pixel-art textures (NumPy), 16 texels per tile like Platinum's own terrain.

The flood water itself is NOT a custom texture: the flood sheets use set 010's own animated `sea` texture (the
field texture animation is keyed by texture name, so it animates in set 078 exactly as on the stock coast).

Organic edges use a hashed per-texel threshold (white noise shaped by smooth noise), never an ordered Bayer grid,
and every translucent glow / shadow is a smooth A3I5 alpha ramp (8 alpha levels), so nothing reads as a
checkerboard.

Usage:
  ~/.venvs/desmume/bin/python tools/routes/r215/textures.py                dry run: table, VRAM, round-trip checks
  ~/.venvs/desmume/bin/python tools/routes/r215/textures.py --preview DIR  also write DIR/<texture>.png (x8 sheet too)
  ~/.venvs/desmume/bin/python tools/routes/r215/textures.py --write        write SET_REL (refuses if a check fails)

Idempotent: the base is always stock set 010 read from git, never the work tree, so reruns never append twice.

Textures:
  r215_board   pltt16 32x32 opaque. Wet dark-timber boardwalk planks (4-texel planks across the walk), stringer
               nails, wet sheen, mud splashes, dark edge beams at v 0 / 31.
  r215_ruts    pltt16 32x64 c0=1. Solid packed-mud road bed (two-level tone blobs, no isolated texels) between
               cleanly stepped edges (runs of 4..10 rows, 1-texel steps), each a crisp 1-texel dark outline with a
               light 1-texel rim; two sculpted tyre grooves (shaded / lit walls, tread bars, contiguous standing
               rainwater). u across the 2-tile lane, v along it (4 tiles per repeat).
  r215_rutcap  pltt16 32x16 c0=1. Rounded end cap: row 0 = the ruts' row 0, the bed narrows to a stepped round tip
               with the same outline + rim, the grooves shallow out and end.
  r215_padn /  pltt16 64x128 / 128x64 c0=1. Texel-aligned staging pads (PADS): the north yard's mud pad and the
  r215_padg    gravel apron before the gate (stock blueglay tones, 2x2 pebbles), each with a clean 1-texel dark
               outline and a mud rim.
  r215_props   pltt16 64x32 c0=1. Wooden crate side/top, steel drum side/lid, pole, cross bar and the Team Eclipse
               warning banner (eclipse emblem, swallowtail hem) (PROPS_UV).
  r215_shore   pltt16 32x16 c0=1. Flood shoreline fringe laid along the water's contour: v 0 = water side
               (silty shallows breaking up over the sea), wet dark mud lip, lighter churned mud, then stock-green
               grass blades overhanging the mud and thinning out into the stock grass (v 15).
  r215_crate   pltt16 64x64 c0=1. Team Eclipse staging atlas (CRATE_UV): dark-slate crates (two variants) with
               1-texel black outlines and violet eclipse stencils, olive rain tarp (ragged hem) + top, wooden
               pallet side + top, dark metal, hazard band, timber post, sign board, amber work-lamp glass + housing.
  r215_glow    a3i5 64x64. Smooth translucent ramps (GLOW_UV): amber lamp halo, amber ground light pool, the
               contact shadow under the staging clusters, violet halo.
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
WATER_TEXTURE = "sea"            # stock set-010 animated sea water (16x16, 1 tile per repeat)

TAU = 2 * np.pi

CRATE_UV = {"crate_s": (0, 0, 16, 16), "crate_t": (16, 0, 32, 16), "crate2_s": (32, 0, 48, 16),
            "tarp_s": (48, 0, 64, 16), "tarp_t": (0, 16, 16, 32), "pallet_s": (16, 16, 32, 24),
            "pallet_t": (16, 24, 32, 32), "metal": (32, 16, 48, 24), "hazard": (32, 24, 48, 32),
            "post": (48, 16, 64, 32), "lamp_amber": (0, 32, 8, 48), "lamp_cap": (8, 32, 16, 40),
            "lamp_back": (8, 40, 16, 48), "board": (16, 32, 48, 48), "crate2_t": (48, 32, 64, 48)}
GLOW_UV = {"halo_amber": (0, 0, 32, 32), "pool_amber": (32, 0, 64, 32), "shadow": (0, 32, 32, 64),
           "halo_violet": (32, 32, 64, 64)}
SHORE_H = 16
RUTS_H = 64


def grid(w, h):
    Y, X = np.mgrid[0:h, 0:w].astype(float)
    return X, Y


def hashn(w, h, seed):
    """Per-texel white noise in [0, 1) (deterministic)."""
    return np.random.RandomState(seed).rand(h, w)


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


def noise1(n, cells, seed):
    """Periodic 1-D value noise of length n."""
    return pnoise(n, 1, cells, 1, seed)[0]


def fbm(w, h, seed, octs=((4, 0.55), (8, 0.3), (16, 0.15))):
    return sum(wt * pnoise(w, h, c, c, seed + k * 101) for k, (c, wt) in enumerate(octs))


def ramp(t, idx, jitter=None, amount=0.0):
    """Quantise t in [0, 1] onto palette indices idx, with optional white-noise jitter (no ordered pattern)."""
    n = len(idx)
    j = 0.0 if jitter is None else (jitter - 0.5) * amount
    v = np.clip(np.floor(np.clip(t, 0, 1) * (n - 1) + 0.5 + j), 0, n - 1).astype(int)
    return np.array(idx)[v]


def snap(c):
    return tuple(int(v) >> 3 << 3 for v in c)


# ---------------------------------------------------------------------------------------------------------------
# r215_board (unchanged design; wet timber deck)
# ---------------------------------------------------------------------------------------------------------------

def tex_board():
    pal = [(30, 24, 26), (50, 40, 40), (76, 62, 54), (96, 78, 64), (114, 94, 74), (132, 110, 86), (150, 128, 100),
           (172, 150, 120), (112, 124, 136), (156, 170, 184), (74, 62, 48), (100, 82, 62), (40, 40, 46),
           (190, 190, 198), (72, 88, 66), (56, 60, 70)]
    w = h = 32
    X, Y = grid(w, h)
    J = hashn(w, h, 5)
    rng = np.random.RandomState(215)
    plank = (X // 4).astype(int)
    tone = rng.rand(8)[plank] * 0.30 - 0.12
    grain = pnoise(w, h, 8, 2, 7) * 0.6 + pnoise(w, h, 32, 4, 9) * 0.4
    t = 0.54 + tone + (grain - 0.5) * 0.45
    t -= 0.10 * (X % 4 == 0)
    t += 0.08 * (X % 4 == 2)
    img = ramp(t, [2, 3, 4, 5, 6, 7], J, 0.7)
    img[(X % 4) == 3] = 1
    img[((X % 4) == 3) & (pnoise(w, h, 8, 8, 3) > 0.62)] = 0
    wet = pnoise(w, h, 4, 4, 21)
    sheen = (wet > 0.62) & ((X % 4) != 3) & (J < (wet - 0.62) * 2.2) & ((X % 4) != 0)
    img[sheen] = 8
    img[sheen & (wet > 0.78) & ((X % 4) == 1)] = 9
    for y in (1, 30):
        img[y, :] = ramp(0.35 + 0.25 * pnoise(w, 1, 8, 1, 31 + y)[0], [3, 4, 5], J[y], 0.6)
    img[0, :] = 0
    img[31, :] = 0
    img[2, :] = np.where(X[2] % 4 == 3, 1, 2)
    img[29, :] = np.where(X[29] % 4 == 3, 1, 2)
    for vy in (4, 27, 15):
        for px in range(1, 32, 4):
            if vy == 15 and (px // 4) % 2:
                continue
            img[vy, px] = 12
            img[vy - 1, px] = 13
    mud = pnoise(w, h, 16, 16, 41)
    edge = np.minimum(Y, 31 - Y)
    splash = (edge >= 2) & (edge <= 6) & (mud + J * 0.35 > 0.84 + edge * 0.03)
    img[splash] = np.where(mud[splash] > 0.9, 10, 11)
    img[((X % 4) == 3) & (mud > 0.7) & (edge > 4)] = 14
    img[(img == 1) & (wet > 0.7)] = 15
    return img, pal


# ---------------------------------------------------------------------------------------------------------------
# shared pixel-art helpers: stepped edges, 1-texel outlines, no isolated texels
# ---------------------------------------------------------------------------------------------------------------

def stepped(n, seed, lo=0, hi=2, rmin=4, rmax=10):
    """Periodic piecewise-constant integer profile of length n: runs of rmin..rmax rows, each step +-1, the wrap
    within one step too (a cleanly stepped edge, never a jagged 1-row flicker)."""
    rng = np.random.RandomState(seed)
    lev = int(rng.randint(lo, hi + 1))
    out = []
    while len(out) < n:
        out += [lev] * int(rng.randint(rmin, rmax + 1))
        lev = int(np.clip(lev + rng.choice([-1, 1]), lo, hi))
    out = out[:n]
    k = n - 1
    while k > 0 and out[k - 1] == out[-1]:
        k -= 1
    if n - k < 3:                               # a short trailing run: fold it into the run before it
        out[k:] = [out[k - 1]] * (n - k)
    if abs(out[-1] - out[0]) > 1:
        k = n - 1
        while k > 0 and out[k - 1] == out[-1]:
            k -= 1
        out[k:] = [(lo + hi) // 2] * (n - k)
    return np.array(out, int)


def edge_rings(M, wrap_v=False):
    """Inside mask M -> (outline, rim): the outline is every inside texel with an outside 4-neighbour (a clean
    8-connected 1-texel line), the rim the inside texels 4-adjacent to the outline."""
    def nb_any(A, fill):
        P = np.pad(A, 1, mode="constant", constant_values=fill)
        if wrap_v:
            P[0, 1:-1] = A[-1]
            P[-1, 1:-1] = A[0]
        return P[:-2, 1:-1] | P[2:, 1:-1] | P[1:-1, :-2] | P[1:-1, 2:]
    out = M & nb_any(~M, True)
    rim = M & ~out & nb_any(out, False)
    return out, rim


def declump(img, keep=(), passes=2):
    """Replace every isolated texel (no 4-neighbour of the same index) by its most common neighbour: tone patches
    stay solid blobs, nothing reads as single-pixel noise. Indices in `keep` are left alone."""
    h, w = img.shape
    for _ in range(passes):
        P = np.pad(img, 1, mode="edge")
        nbs = np.stack([P[:-2, 1:-1], P[2:, 1:-1], P[1:-1, :-2], P[1:-1, 2:]], 0)
        lone = (nbs != img[None]).all(0) & ~np.isin(img, list(keep))
        for y, x in zip(*np.nonzero(lone)):
            vals, cnt = np.unique(nbs[:, y, x], return_counts=True)
            img[y, x] = vals[np.argmax(cnt)]
    return img


def patches(w, h, seed, lo_idx, mid_idx, hi_idx, cells=(3, 6), lo=0.36, hi=0.64, periodic=True):
    """Two-level tone patches (large solid blobs, no jitter) over a base tone."""
    n = 0.65 * pnoise(w, h, cells[0], cells[1], seed) + 0.35 * pnoise(w, h, cells[0] * 2, cells[1] * 2, seed + 1)
    img = np.full((h, w), mid_idx)
    img[n < lo] = lo_idx
    img[n > hi] = hi_idx
    return declump(img)


# ---------------------------------------------------------------------------------------------------------------
# r215_ruts: a solid packed-mud road bed with dual-tyre grooves (v3)
# ---------------------------------------------------------------------------------------------------------------

RUT_PAL = [(255, 0, 255),
           (36, 26, 24),                                      # 1 outline / deepest trough
           (54, 40, 32),                                      # 2 trough
           (74, 56, 42),                                      # 3 shaded groove wall / tread bars
           (98, 76, 56),                                      # 4 damp packed mud
           (114, 90, 66),                                     # 5 packed mud (road bed)
           (132, 104, 76),                                    # 6 lit groove wall / low ridge
           (154, 124, 92),                                    # 7 rim / ridge crest
           (60, 78, 96), (96, 122, 146), (176, 204, 222),     # 8-10 standing rainwater: deep / mid / sky
           (232, 242, 248),                                   # 11 glint
           (52, 112, 66), (78, 150, 90),                      # 12-13 (spare greens)
           (88, 68, 52),                                      # 14 (spare dark mud)
           (124, 98, 72)]                                     # 15 dry packed mud
RUT_GROOVES = (8, 24)


def rut_bed_rows(h):
    """Per row v: (l, r) = first / last inside texel of the road bed (stepped, 0..2 texels in from each side)."""
    eL = stepped(h, 121)
    eR = stepped(h, 133)
    return eL, 31 - eR


def paint_grooves(img, v0, v1, J, water_noise):
    """Dual-tyre grooves on rows v0..v1-1 of a 32-wide road-bed image."""
    for k, c in enumerate(RUT_GROOVES):
        for v in range(v0, v1):
            img[v, c - 3] = 6                               # low south ridge
            img[v, c - 2] = 3                               # shaded south wall
            img[v, c - 1] = 1                               # deep trough
            img[v, c] = 2
            img[v, c + 1] = 6                               # lit north wall (faces the camera / light)
            img[v, c + 2] = 7                               # crest
            if (v + 2 * k) % 4 == 0:                        # tyre tread bar across the trough
                img[v, c - 1] = 3
                img[v, c] = 3
        # standing rainwater in contiguous stretches of the trough
        wet = water_noise[k][v0:v1] > 0.6
        run = 0
        for i, v in enumerate(range(v0, v1)):
            if wet[i]:
                img[v, c - 1] = 8
                img[v, c] = 10 if run == 0 else 9
                if run == 2:
                    img[v, c] = 11
                run += 1
            else:
                run = 0
    return img


def tex_ruts():
    """32 x 64: u across the 2-tile lane (u 0 = the lane's left / south side), v along it (4 tiles per repeat).
    A solid packed-mud road bed (two-level tone blobs, no noise) between cleanly stepped edges, each edge a crisp
    1-texel dark outline with a 1-texel light rim inside; two sculpted tyre grooves (shaded / lit walls, tread
    bars, contiguous standing rainwater). Periodic in v."""
    w, h = 32, RUTS_H
    J = hashn(w, h, 571)
    l, r = rut_bed_rows(h)
    U = np.arange(w)[None, :]
    M = (U >= l[:, None]) & (U <= r[:, None])
    img = patches(w, h, 51, 4, 5, 15, cells=(2, 4))
    water = [noise1(h, 5, 61 + 7 * k) for k in range(2)]
    paint_grooves(img, 0, h, J, water)
    out, rim = edge_rings(M, wrap_v=True)
    img[rim] = 7
    img[out] = 1
    img[~M] = 0
    return img, RUT_PAL


def tex_rutcap():
    """32 x 16 rounded end cap of the road bed: row 0 is the ruts' row 0 (the lane is laid out with an integer
    number of 4-tile repeats, so both lane ends sit on that row), then the bed narrows to a rounded tip (stepped
    arc, the same 1-texel outline + rim) and the grooves shallow out and end."""
    w, h = 32, 16
    rut, _ = tex_ruts()
    l, r = rut_bed_rows(RUTS_H)
    img = rut[:h].copy()
    J = hashn(w, RUTS_H, 571)
    base = patches(w, RUTS_H, 51, 4, 5, 15, cells=(2, 4))[:h]
    img[1:] = base[1:]
    water = [noise1(RUTS_H, 5, 61 + 7 * k) for k in range(2)]
    paint_grooves(img, 1, 7, J, water)
    for c in RUT_GROOVES:                                   # the grooves shallow out ...
        img[7, c - 2:c + 2] = [4, 3, 3, 4]
        img[7, c + 2] = 6
        img[8, c - 1:c + 1] = 4
    img[1:7][np.isin(img[1:7], (8, 9, 10, 11))] = 2        # ... with no water in the shallow end
    R, A = 14.6, 14.5
    M = np.zeros((h, w), bool)
    for v in range(h):
        f = A * (1 - np.sqrt(max(0.0, 1 - (v / R) ** 2))) if v < R else 99
        lv, rv = l[v] + int(round(f)), r[v] - int(round(f))
        if lv <= rv:
            M[v, lv:rv + 1] = True
    Mp = np.vstack([M[:1], M])                              # row -1 = row 0: the seam edge is open
    out, rim = edge_rings(Mp)
    out, rim = out[1:], rim[1:]
    img[rim] = 7
    img[out] = 1
    img[~M] = 0
    img[0] = rut[0]
    return img, RUT_PAL


# ---------------------------------------------------------------------------------------------------------------
# staging pads: texel-aligned decals (one quad each, 16 texels per tile) with a clean outlined border
# ---------------------------------------------------------------------------------------------------------------

# name -> origin (world tiles, multiple of 1/16), size (texels), rounded rects (x0, z0, x1, z1, radius) in world tiles
# unioned with a smooth fillet, style. A rect reaching past the texture (gate pad, east) gets no border there.
PADS = {
    "r215_padn": dict(origin=(629.5, 581.5), size=(64, 128), style="mud",
                      rects=[(629.62, 582.0, 633.0, 585.4, 0.38), (629.62, 584.8, 633.0, 587.3, 0.38)]),
    "r215_padg": dict(origin=(664.0, 597.0), size=(128, 64), style="gravel",
                      rects=[(667.62, 597.0, 673.5, 601.0, 0.38), (664.56, 599.12, 668.5, 601.0, 0.38)]),
}

PAD_GRAVEL_PAL = [(255, 0, 255),
                  (44, 38, 42),                               # 1 outline
                  (100, 80, 62),                              # 2 wet mud rim
                  (150, 158, 172),                            # 3 gravel dark patch
                  (172, 180, 190),                            # 4 gravel (stock blueglay tone)
                  (184, 196, 206),                            # 5 gravel light patch
                  (214, 222, 234),                            # 6 pebble light
                  (126, 132, 146),                            # 7 pebble shadow
                  (60, 78, 96), (96, 122, 146), (176, 204, 222), (232, 242, 248),   # 8-11 (spare water)
                  (82, 64, 50), (120, 96, 72), (140, 148, 162), (196, 204, 218)]   # 12-15 (spare)


def pad_mask(spec, pad=1):
    ox, oz = spec["origin"]
    w, h = spec["size"]
    X, Y = grid(w + 2 * pad, h + 2 * pad)
    px = ox + (X - pad + 0.5) / 16.0
    pz = oz + (Y - pad + 0.5) / 16.0
    d = None
    for x0, z0, x1, z1, rad in spec["rects"]:
        cx, cz, bx, bz = (x0 + x1) / 2, (z0 + z1) / 2, (x1 - x0) / 2, (z1 - z0) / 2
        qx, qz = np.abs(px - cx) - (bx - rad), np.abs(pz - cz) - (bz - rad)
        di = np.hypot(np.maximum(qx, 0), np.maximum(qz, 0)) + np.minimum(np.maximum(qx, qz), 0) - rad
        if d is None:
            d = di
        else:                                               # smooth union: a rounded inner corner, no notch
            k = 0.3
            hh = np.clip(0.5 + 0.5 * (di - d) / k, 0, 1)
            d = di * (1 - hh) + d * hh - k * hh * (1 - hh)
    return d <= 0


def tex_pad(name):
    spec = PADS[name]
    w, h = spec["size"]
    Mp = pad_mask(spec)
    out, rim = edge_rings(Mp)
    M, out, rim = Mp[1:-1, 1:-1], out[1:-1, 1:-1], rim[1:-1, 1:-1]
    if spec["style"] == "mud":
        img = patches(w, h, 313, 4, 5, 15, cells=(4, 8))
        img[rim] = 7
        pal = RUT_PAL
    else:
        img = patches(w, h, 331, 3, 4, 5, cells=(8, 4))
        # gravel: 2 x 2 pebbles (light top, shadowed bottom) on a jittered 6-texel lattice, never single texels
        rng = np.random.RandomState(337)
        for gy in range(0, h, 6):
            for gx in range(0, w, 6):
                if rng.rand() < 0.42:
                    y, x = gy + rng.randint(0, 4), gx + rng.randint(0, 4)
                    if y + 1 < h and x + 1 < w:
                        img[y, x:x + 2] = 6
                        img[y + 1, x:x + 2] = 7
        img[rim] = 2
        pal = PAD_GRAVEL_PAL
    img[out] = 1
    img[~M] = 0
    return img, pal


# ---------------------------------------------------------------------------------------------------------------
# r215_props: wooden crates, steel drums, the Team Eclipse warning banner (own palette)
# ---------------------------------------------------------------------------------------------------------------

PROPS_UV = {"wcrate_s": (0, 0, 16, 16), "wcrate_t": (16, 0, 32, 16), "barrel_s": (32, 0, 48, 16),
            "barrel_t": (48, 0, 56, 8), "bar": (48, 8, 56, 16), "pole": (56, 0, 60, 16), "banner": (0, 16, 16, 32)}


def tex_props():
    pal = [(255, 0, 255),
           (20, 14, 18),                                      # 1 outline
           (92, 58, 34), (134, 90, 52), (174, 124, 72),       # 2-4 wood dark / mid / light
           (204, 158, 98),                                    # 5 wood highlight
           (36, 44, 60), (58, 70, 90), (92, 106, 128),        # 6-8 drum dark / mid / light
           (150, 158, 172),                                   # 9 steel
           (76, 40, 124), (116, 70, 176), (162, 120, 222),    # 10-12 eclipse violet
           (240, 176, 64),                                    # 13 amber corona
           (236, 228, 250),                                   # 14 pale emblem edge
           (236, 200, 56)]                                    # 15 hazard yellow
    img = np.zeros((32, 64), int)

    def cell(key):
        x0, y0, x1, y1 = PROPS_UV[key]
        X, Y = grid(x1 - x0, y1 - y0)
        return slice(y0, y1), slice(x0, x1), X.astype(int), Y.astype(int)

    # wooden crate side: light 2-texel frame, horizontal planks, a diagonal brace, nail heads
    ys, xs, X, Y = cell("wcrate_s")
    c = np.where(((Y - 3) // 3) % 2 == 0, 3, 4)
    c[(Y - 3) % 3 == 2] = 2
    br = (np.abs(X - Y) <= 1) & (X >= 3) & (X <= 12)
    c[br] = 4
    c[br & (Y - X == 1)] = 2
    fr = (X <= 2) | (X >= 13) | (Y <= 2) | (Y >= 13)
    c[fr] = 4
    c[fr & ((X == 1) | (Y == 1))] = 5
    c[fr & ((X == 2) | (Y == 2) | (X == 14) | (Y == 14)) & ~((X == 1) | (Y == 1))] = 3
    for nx, ny in ((2, 2), (13, 2), (2, 13), (13, 13)):
        c[ny, nx] = 9
    c[(X == 0) | (X == 15) | (Y == 0) | (Y == 15)] = 1
    img[ys, xs] = c
    # wooden crate top: planks along v, dark gaps, nails
    ys, xs, X, Y = cell("wcrate_t")
    c = np.where((X // 4) % 2 == 0, 4, 5)
    c[X % 4 == 3] = 2
    c[((Y == 2) | (Y == 13)) & (X % 4 == 1)] = 9
    c[(X == 0) | (X == 15) | (Y == 0) | (Y == 15)] = 1
    img[ys, xs] = c
    # steel drum side (3 faces across u): cylinder shading, two steel hoops, a violet band
    ys, xs, X, Y = cell("barrel_s")
    shade = np.array([6, 7, 7, 8, 8, 9, 8, 8, 7, 7, 7, 6, 6, 7, 6, 6])
    c = shade[X]
    hoop = (Y == 2) | (Y == 13)
    c[hoop] = 9
    c[(Y == 3) | (Y == 14)] = 6
    band = (Y >= 6) & (Y <= 9)
    c[band] = np.where((X >= 4) & (X <= 6), 12, 11)[band]
    c[band & ((Y == 9) | (X >= 13))] = 10
    c[(Y == 0) | (Y == 15)] = 1
    img[ys, xs] = c
    # drum lid
    ys, xs, X, Y = cell("barrel_t")
    rr = np.hypot(X + 0.5 - 4, Y + 0.5 - 4)
    c = np.where(rr < 2.3, 8, np.where(rr < 3.2, 9, 7))
    c[(np.abs(X - 5) <= 0) & (np.abs(Y - 2) <= 0)] = 6
    img[ys, xs] = c
    # cross bar + pole (dark steel, light top edge)
    ys, xs, X, Y = cell("bar")
    c = np.full(X.shape, 7)
    c[Y <= 1] = 9
    c[Y >= 6] = 1
    img[ys, xs] = c
    ys, xs, X, Y = cell("pole")
    c = np.array([1, 9, 7, 1])[X]
    c[(Y >= 9) & (Y <= 12)] = np.where(((X + Y) // 2) % 2 == 0, 15, 1)[(Y >= 9) & (Y <= 12)]
    img[ys, xs] = c
    # Team Eclipse banner: violet cloth with folds, a dark hem with grommets, the eclipse emblem (dark disc, amber
    # corona, pale limb) and a swallowtail bottom; 1-texel outline all round
    ys, xs, X, Y = cell("banner")
    c = np.full(X.shape, 11)
    c[(X == 4) | (X == 11)] = 10
    c[(X == 3) | (X == 10)] = 12
    c[Y <= 2] = 10
    c[(Y == 1) & ((X == 3) | (X == 12))] = 9
    rr = np.hypot(X + 0.5 - 8, Y + 0.5 - 8)
    c[(rr >= 2.6) & (rr < 4.0) & (Y > 2)] = 13
    c[rr < 2.6] = 1
    c[(rr >= 2.0) & (rr < 2.6) & (X >= 8) & (Y <= 7)] = 14
    M = ~((Y >= 12) & (np.abs(X + 0.5 - 8) < (Y - 11.5) * 1.6))
    out, _ = edge_rings(M)
    c[out] = 1
    c[~M] = 0
    img[ys, xs] = c
    return img, pal


# ---------------------------------------------------------------------------------------------------------------
# r215_shore: flood shoreline fringe (v 0 water side -> v 15 grass side)
# ---------------------------------------------------------------------------------------------------------------

def tex_shore():
    pal = [(255, 0, 255),
           (48, 98, 168), (66, 108, 156), (92, 112, 132),     # 1-3 silty shallows (sea blue -> silt)
           (186, 216, 238),                                   # 4 ripple / foam
           (46, 34, 30), (64, 48, 38), (86, 66, 50),          # 5-7 wet mud dark -> mid
           (112, 88, 64),                                     # 8 churned mud light
           (41, 148, 74), (57, 189, 106), (82, 230, 106),     # 9-11 grass shadow / dark / mid (stock greens)
           (82, 255, 148), (131, 246, 139), (164, 255, 156),  # 12-14 stock lgreen / lgreenp tones
           (74, 120, 70)]                                     # 15 muddy grass
    w, h = 32, SHORE_H
    X, Y = grid(w, h)
    J = hashn(w, h, 901)
    J2 = hashn(w, h, 907)
    img = np.zeros((h, w), int)
    u = np.arange(w)
    # boundaries along u (periodic, so the strip tiles seamlessly along the contour)
    b_water = 2.6 + 2.2 * noise1(w, 4, 11) + 0.8 * noise1(w, 8, 12)        # shallows start
    b_mud = b_water + 1.6 + 1.2 * noise1(w, 4, 13)                          # wet mud starts
    b_grass = 8.4 + 1.8 * noise1(w, 4, 14) + 1.0 * noise1(w, 16, 15)        # grass overhang bottom (base)
    blade = (J2[0] * 2.2).astype(int) * (u % 2 == 0)                        # blades hanging lower
    b_grass_tip = b_grass - blade
    yy = Y + 0.5
    BW, BM, BG = b_water[None, :], b_mud[None, :], b_grass_tip[None, :]
    # silty shallows: break up over the water with white-noise holes (not an ordered grid)
    sh = (yy >= BW - 1.2) & (yy < BM)
    p = np.clip((yy - (BW - 1.2)) / 1.6, 0, 1)
    keep = sh & (J < 0.25 + 0.75 * p)
    img[keep] = np.where(yy[keep] < BW[np.zeros_like(Y, int)[keep], X.astype(int)[keep]], 1,
                         np.where(J2[keep] > 0.5, 2, 3))
    rip = sh & (J2 > 0.94) & (yy < BM - 0.5)
    img[rip] = 4
    # wet mud lip
    md = (yy >= BM) & (yy < BG + 1.0)
    t = (yy - BM) / (BG + 1.0 - BM + 1e-6)
    img[md] = ramp(t[md] * 0.9 + 0.05, [5, 6, 7, 8], J[md], 0.9)
    img[md & (J2 < 0.10)] = 5
    # grass overhang: blades over the mud, darker at the tips
    gr = yy >= BG
    t = np.clip((yy - BG) / 3.0, 0, 1)
    gcol = ramp(t, [9, 10, 11, 12], J, 0.8)
    img[gr] = gcol[gr]
    tip = gr & (yy < BG + 1.0)
    img[tip] = 9
    img[gr & (yy < BG + 2.0) & (J2 < 0.15)] = 15
    # thin out into the stock grass: texels drop out with rising probability (white noise)
    top = yy > 11.0
    drop = top & (J > 1.0 - (yy - 11.0) / 5.0 * 0.95)
    img[top & ~drop & (img >= 11)] = np.where(J2[top & ~drop & (img >= 11)] > 0.5, 12,
                                              np.where(J2[top & ~drop & (img >= 11)] > 0.25, 13, 14))
    img[drop] = 0
    img[(yy > 15.0)] = 0
    return img, pal


# ---------------------------------------------------------------------------------------------------------------
# r215_crate: Team Eclipse staging atlas
# ---------------------------------------------------------------------------------------------------------------

def tex_crate():
    pal = [(255, 0, 255),
           (14, 12, 20),                                      # 1 outline
           (38, 42, 56), (54, 60, 76), (74, 82, 100),         # 2-4 dark slate
           (102, 110, 130),                                   # 5 slate highlight
           (150, 156, 170),                                   # 6 bracket steel
           (112, 76, 168), (164, 128, 222),                   # 7-8 eclipse violet
           (72, 78, 42), (104, 112, 60), (140, 148, 84),      # 9-11 olive tarp
           (96, 68, 44), (140, 104, 66),                      # 12-13 pallet wood
           (240, 176, 64), (255, 244, 196)]                   # 14-15 amber / hot white (lamp, hazard)
    img = np.zeros((64, 64), int)
    J = hashn(64, 64, 4242)
    n = fbm(64, 64, 91)

    def cell(key):
        x0, y0, x1, y1 = CRATE_UV[key]
        return slice(y0, y1), slice(x0, x1), x1 - x0, y1 - y0

    def outline(c, w, h):
        X, Y = grid(w, h)
        c[(X == 0) | (X == w - 1) | (Y == 0) | (Y == h - 1)] = 1
        return c

    # crate side: slate boards in a lighter frame, steel corner brackets, violet eclipse ring stencil
    for key, stripe in (("crate_s", False), ("crate2_s", True)):
        ys, xs, w, h = cell(key)
        X, Y = grid(w, h)
        c = ramp(0.45 + (n[ys, xs] - 0.5) * 0.6 + 0.18 * ((Y.astype(int) // 4) % 2), [2, 3, 4], J[ys, xs], 0.5)
        c[(Y.astype(int) % 4) == 0] = 2
        frame = (X <= 2) | (X >= 13) | (Y <= 2) | (Y >= 13)
        c[frame] = 4
        c[(X == 1) | (Y == 1)] = 5
        c[(X == 2) | (Y == 2)] = 3
        c[((X == 14) | (Y == 14)) & frame] = 3
        for bx, by in ((1, 1), (12, 1), (1, 12), (12, 12)):
            c[by:by + 3, bx:bx + 3] = 6
            c[by + 1, bx + 1] = 3
        if stripe:
            c[(Y >= 6) & (Y <= 8) & ~frame] = 7
            c[(Y == 7) & ~frame & (X.astype(int) % 3 == 0)] = 8
        else:
            r = np.hypot(X + 0.5 - 8, Y + 0.5 - 8)
            ring = (np.abs(r - 2.9) < 0.75) & ~frame
            c[ring] = 7
            c[ring & (X > 8) & (Y < 8)] = 8
            c[(r < 1.5) & ~frame] = 2
        img[ys, xs] = outline(c, w, h)
    # crate tops
    for key in ("crate_t", "crate2_t"):
        ys, xs, w, h = cell(key)
        X, Y = grid(w, h)
        c = ramp(0.5 + (n[ys, xs] - 0.5) * 0.5 + 0.15 * ((X.astype(int) // 5) % 2), [3, 4, 5], J[ys, xs], 0.4)
        c[(X.astype(int) % 5) == 4] = 2
        for bx, by in ((1, 1), (12, 1), (1, 12), (12, 12)):
            c[by:by + 3, bx:bx + 3] = 6
        if key == "crate2_t":
            c[(np.abs(Y - 7.5) < 1.0)] = 7
        img[ys, xs] = outline(c, w, h)
    # olive tarp skirt: vertical folds, violet strap, ragged transparent hem
    ys, xs, w, h = cell("tarp_s")
    X, Y = grid(w, h)
    fold = 0.5 + 0.5 * np.sin(TAU * (X + 0.25 * Y) / 5.0 + 0.6 * np.sin(TAU * Y / 16))
    c = ramp(0.2 + 0.7 * fold * (0.75 + 0.5 * n[ys, xs]), [9, 10, 11], J[ys, xs], 0.5)
    c[(fold < 0.18)] = 2
    c[np.abs(X - 10.5) < 1.0] = 7
    c[(np.abs(X - 10.5) < 1.0) & (Y.astype(int) % 4 == 1)] = 8
    hem = 12.5 + 2.0 * noise1(16, 4, 33)[None, :] + (J[ys, xs][0][None, :] > 0.6)
    c[(Y + 0.5 > hem - 1.0)] = 9
    c[(Y + 0.5 > hem)] = 0
    c[Y == 0] = 1
    img[ys, xs] = c
    # tarp top: canvas with crossing violet straps and grommets
    ys, xs, w, h = cell("tarp_t")
    X, Y = grid(w, h)
    wr = 0.5 + 0.5 * np.sin(TAU * (X - 0.6 * Y) / 6.0)
    c = ramp(0.3 + 0.55 * wr * (0.7 + 0.6 * n[ys, xs]), [9, 10, 11], J[ys, xs], 0.5)
    c[np.abs(X - 5.5) < 1.0] = 7
    c[np.abs(Y - 9.5) < 1.0] = 7
    c[(np.abs(X - 5.5) < 1.0) & (np.abs(Y - 9.5) < 1.0)] = 8
    for gx, gy in ((1, 1), (14, 1), (1, 14), (14, 14)):
        c[gy, gx] = 6
    img[ys, xs] = outline(c, w, h)
    # pallet side (16x8): three blocks with dark gaps under a top board
    ys, xs, w, h = cell("pallet_s")
    X, Y = grid(w, h)
    c = np.full((h, w), 13)
    c[Y >= 3] = 12
    c[(Y >= 3) & (((X >= 3) & (X <= 5)) | ((X >= 10) & (X <= 12)))] = 1
    c[(Y == 2)] = 12
    c[(Y == 0)] = 13
    c[J[ys, xs] > 0.9] = 12
    img[ys, xs] = outline(c, w, h)
    # pallet top (16x8): slats along u with gaps
    ys, xs, w, h = cell("pallet_t")
    X, Y = grid(w, h)
    c = np.where((X.astype(int) % 4) == 3, 1, np.where(J[ys, xs] > 0.8, 12, 13))
    img[ys, xs] = outline(c, w, h)
    # dark riveted metal
    ys, xs, w, h = cell("metal")
    X, Y = grid(w, h)
    c = ramp(0.4 + (n[ys, xs] - 0.5) * 0.7, [2, 3, 4], J[ys, xs], 0.5)
    c[(Y == 1) & (X.astype(int) % 4 == 1)] = 6
    c[(Y == 0) | (Y == 7)] = 1
    img[ys, xs] = c
    # hazard band
    ys, xs, w, h = cell("hazard")
    X, Y = grid(w, h)
    c = np.where(((X + Y).astype(int) // 3) % 2 == 0, 14, 1)
    c[(Y == 0) | (Y == 7)] = 1
    img[ys, xs] = c
    # timber post with a hazard collar
    ys, xs, w, h = cell("post")
    X, Y = grid(w, h)
    c = ramp(0.45 + (pnoise(16, 16, 2, 8, 5) - 0.5) * 0.7, [12, 13, 12], J[ys, xs], 0.5)
    c[(X.astype(int) % 4) == 0] = 12
    c[Y < 4] = np.where((((X + Y).astype(int) // 2) % 2) == 0, 14, 1)[Y < 4]
    c[(Y == 4)] = 1
    c[(X == 0) | (X == 15)] = 1
    img[ys, xs] = c
    # lamp glass (8x16): hot white core, amber lens, steel rim (drawn unlit: it is the light source)
    ys, xs, w, h = cell("lamp_amber")
    X, Y = grid(w, h)
    r = np.hypot((X + 0.5 - 4) / 3.3, (Y + 0.5 - 7) / 6.0)
    c = np.where(r < 0.45, 15, np.where(r < 1.0, 14, 6))
    c[(X == 0) | (X == 7) | (Y == 0) | (Y == 15)] = 1
    img[ys, xs] = c
    ys, xs, w, h = cell("lamp_cap")
    X, Y = grid(w, h)
    c = np.full((h, w), 3)
    c[Y < 2] = 4
    img[ys, xs] = outline(c, w, h)
    ys, xs, w, h = cell("lamp_back")
    X, Y = grid(w, h)
    c = np.full((h, w), 2)
    c[(Y.astype(int) % 3) == 1] = 3
    img[ys, xs] = outline(c, w, h)
    # sign board (32x16): weathered planks with a violet header and a water-level glyph row
    ys, xs, w, h = cell("board")
    X, Y = grid(w, h)
    c = ramp(0.5 + (pnoise(32, 16, 4, 2, 77) - 0.5) * 0.7, [12, 13], J[ys, xs], 0.5)
    c[(Y.astype(int) % 5) == 4] = 12
    c[Y < 4] = 7
    c[(Y == 2) & (X.astype(int) % 4 == 1)] = 15
    wave = (np.abs(Y - (9 + np.round(np.sin(TAU * X / 8.0)))) < 0.6) & (X > 3) & (X < 28)
    c[wave] = 1
    c[(np.abs(X - 16) < 1) & (Y > 5) & (Y < 14)] = 1
    img[ys, xs] = outline(c, w, h)
    return img, pal


# ---------------------------------------------------------------------------------------------------------------
# r215_glow: smooth A3I5 alpha ramps (no dithering at all)
# ---------------------------------------------------------------------------------------------------------------

GLOW_PAL = ([(196, 84, 20), (214, 104, 28), (230, 126, 40), (240, 148, 52), (248, 170, 70), (252, 192, 96),
             (255, 212, 128), (255, 228, 164), (255, 242, 204), (255, 252, 236)] +              # 0-9 amber ramp
            [(12, 12, 20), (20, 20, 30), (30, 28, 42), (40, 38, 54)] +                           # 10-13 shadow
            [(70, 40, 120), (96, 60, 160), (128, 88, 200), (164, 128, 232), (204, 176, 248),
             (236, 224, 255)] +                                                                  # 14-19 violet
            [(0, 0, 0)] * 12)


def tex_glow():
    """64 x 64 A3I5: (index, alpha 0..7) per texel."""
    idx = np.zeros((64, 64), int)
    alp = np.zeros((64, 64), int)
    X, Y = grid(32, 32)

    def put(key, i, a):
        x0, y0, x1, y1 = GLOW_UV[key]
        idx[y0:y1, x0:x1] = i
        alp[y0:y1, x0:x1] = a

    # halo: radial, core white-hot, alpha (1 - r)^1.5 up to 6/7
    r = np.clip(np.hypot(X + 0.5 - 16, Y + 0.5 - 16) / 15.5, 0, 1)
    a = np.round(6.2 * (1 - r) ** 1.6).astype(int)
    put("halo_amber", np.clip(np.round((1 - r) ** 1.3 * 9.4), 0, 9).astype(int), a)
    put("halo_violet", 14 + np.clip(np.round((1 - r) ** 1.3 * 5.4), 0, 5).astype(int), a)
    # ground light pool: wide soft ellipse, low alpha (max 4/7) so the ground stays readable
    rp = np.clip(np.hypot((X + 0.5 - 16) / 15.5, (Y + 0.5 - 16) / 15.5), 0, 1)
    put("pool_amber", np.clip(np.round(3 + (1 - rp) * 5), 0, 9).astype(int), np.round(4.4 * (1 - rp) ** 1.3).astype(int))
    # contact shadow: soft rounded rectangle, alpha up to 5/7 in the middle
    dx = np.maximum(np.abs(X + 0.5 - 16) - 9.0, 0)
    dy = np.maximum(np.abs(Y + 0.5 - 16) - 9.0, 0)
    rs = np.clip(np.hypot(dx, dy) / 6.5, 0, 1)
    put("shadow", np.clip(np.round(10 + rs * 3), 10, 13).astype(int), np.round(5.4 * (1 - rs) ** 1.2).astype(int))
    return idx, alp


TEXTURES = [("r215_board", tex_board, 3), ("r215_ruts", tex_ruts, 3), ("r215_rutcap", tex_rutcap, 3),
            ("r215_shore", tex_shore, 3), ("r215_crate", tex_crate, 3), ("r215_props", tex_props, 3),
            ("r215_padn", lambda: tex_pad("r215_padn"), 3), ("r215_padg", lambda: tex_pad("r215_padg"), 3),
            ("r215_glow", None, 1)]
TRANSPARENT = {"r215_ruts", "r215_rutcap", "r215_shore", "r215_crate", "r215_props", "r215_padn", "r215_padg"}


def pal_name(tex):
    return tex + "_pl"


def generate():
    out = []
    for name, fn, fmt in TEXTURES:
        if fmt == 3:
            idx, pal = fn()
            idx = np.asarray(idx, int)
            assert idx.min() >= 0 and idx.max() < 16, name
            assert len(pal) == 16, name
            out.append(dict(name=name, fmt=3, idx=idx, alpha=None, pal=[snap(c) for c in pal]))
        else:
            idx, alp = tex_glow()
            assert idx.min() >= 0 and idx.max() < 32 and alp.min() >= 0 and alp.max() <= 7, name
            out.append(dict(name=name, fmt=1, idx=idx, alpha=alp, pal=[snap(c) for c in GLOW_PAL]))
    return out


def encode(g):
    idx = g["idx"]
    h, w = idx.shape
    flat = idx.reshape(-1).tolist()
    if g["fmt"] == 3:
        data = bytes(flat[i] | flat[i + 1] << 4 for i in range(0, len(flat), 2))
        c0 = 1 if g["name"] in TRANSPARENT else 0
    else:
        al = g["alpha"].reshape(-1).tolist()
        data = bytes(v | (a << 5) for v, a in zip(flat, al))
        c0 = 0
    tex = dict(name=g["name"], fmt=g["fmt"], w=w, h=h, c0=c0, data=data)
    return tex, dict(name=pal_name(g["name"]), colors=[nsbtx.bgr555(c) for c in g["pal"]], pltt4=0)


def git_bytes(rev, rel):
    return subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{rel}"], check=True, capture_output=True).stdout


def build_set():
    fails = []
    base_bytes = git_bytes(BASE_REV, BASE_SET_REL)
    base = nsbtx.parse(base_bytes)
    names = {t["name"] for t in base["textures"]} | {p["name"] for p in base["palettes"]}
    if WATER_TEXTURE not in {t["name"] for t in base["textures"]} or WATER_TEXTURE not in names:
        fails.append(f"stock water texture/palette '{WATER_TEXTURE}' missing from set 010")
    gen = generate()
    new_t, new_p, rows = [], [], []
    for g in gen:
        t, p = encode(g)
        for a in (t["name"], p["name"]):
            if a in names:
                fails.append(f"{a} clashes with a stock set-010 entry")
            if len(a) > NAME_MAX:
                fails.append(f"{a} is longer than {NAME_MAX} characters")
        new_t.append(t)
        new_p.append(p)
        rows.append((g["name"], p["name"], {3: "pltt16", 1: "a3i5"}[g["fmt"]], f"{t['w']}x{t['h']}", len(t["data"]),
                     len(p["colors"]) * 2, t["c0"], len(set(g["idx"].reshape(-1).tolist()))))
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
    for g in gen:
        name = g["name"]
        t2, p2 = OT.get(name), OP.get(pal_name(name))
        if not t2 or not p2:
            fails.append(f"{name}: missing after build")
            continue
        rgba, ind = nsbtx.decode(t2, p2["colors"])
        want_c0 = 1 if name in TRANSPARENT else 0
        if (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != (g["fmt"], g["idx"].shape[1], g["idx"].shape[0], want_c0):
            fails.append(f"{name}: format/size changed in the round trip")
        if [list(r) for r in ind] != g["idx"].tolist():
            fails.append(f"{name}: texel indices differ after the round trip")
        want = [nsbtx.rgb(nsbtx.bgr555(g["pal"][i])) for i in g["idx"].reshape(-1).tolist()]
        got = [tuple(px[:3]) for row in rgba for px in row]
        if got != want:
            fails.append(f"{name}: decoded colours differ from the BGR555 palette")
        if g["fmt"] == 1:
            ga = [px[3] for row in rgba for px in row]
            if ga != [a * 255 // 7 for a in g["alpha"].reshape(-1).tolist()]:
                fails.append(f"{name}: A3I5 alpha differs after the round trip")
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


def rgba_of(g):
    h, w = g["idx"].shape
    out = np.zeros((h, w, 4), np.uint8)
    pal = np.array(g["pal"], np.uint8)
    out[..., :3] = pal[g["idx"]]
    if g["fmt"] == 1:
        out[..., 3] = (g["alpha"] * 255 // 7).astype(np.uint8)
    else:
        out[..., 3] = np.where((g["idx"] == 0) & (g["name"] in TRANSPARENT), 0, 255)
    return out


def write_preview(d, gen):
    from PIL import Image
    os.makedirs(d, exist_ok=True)
    tiles = []
    for g in gen:
        img = Image.fromarray(rgba_of(g), "RGBA")
        img.save(os.path.join(d, g["name"] + ".png"))
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
          f"{res['stock_palettes']} palettes) + {len(res['rows'])} Route 215 textures; flood water = stock "
          f"'{WATER_TEXTURE}'")
    print(f"{'texture':12s} {'palette':15s} {'fmt':6s} {'size':6s} {'texel B':>7s} {'pal B':>5s} {'c0':>3s} "
          f"{'colours':>7s}")
    for name, pn, fmt, size, tb, pb, c0, nc in res["rows"]:
        print(f"{name:12s} {pn:15s} {fmt:6s} {size:6s} {tb:7d} {pb:5d} {c0:3d} {nc:7d}")
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
        print("PASS every appended texture round-trips (texels, BGR555 colours, A3I5 alpha); stock textures/palettes "
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
