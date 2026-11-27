#!/usr/bin/env python3
"""Routes 206-207 texture kit: five 16-colour BGR555 pixel-art textures appended to stock set 007 to make
map_texture_set_079 (append-only; the stock set is read from git at common.BASE_REV, so reruns are idempotent).

  ec_ruts       32x32  c0=1  Eclipse truck wheel ruts (two tracks across u, running along v; 2 tiles wide, 2 long)
  ec_crate      64x64        atlas of 32x32 cells: crate side | crate lid / shard canister rack | steel pallet frame
  ec_banner     32x32  c0=1  two 16x32 deep-violet Team Eclipse pennants with the pale silver eclipse emblem
  ec_barricade  32x32  c0=1  hazard-stripe plank band (rows 0-7), CLOSED board (rows 8-15), traffic cone (16x16),
                             steel chain-link fence panel (16x16)
  ec_light      32x32  c0=1  tripod work lamp card (16x32) | amber light pool (16x16) | violet shard glow (16x16)

All texels are painted at 16 texels per tile (the field's stock density) with 4x4 Bayer dithering between palette
ramps, dark outlines and a top-left key light. NumPy is needed: run with ~/.venvs/desmume/bin/python.

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

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 + 1 / 32.0


def bayer(h, w, ox=0, oy=0):
    y, x = np.mgrid[0:h, 0:w]
    return BAYER4[(y + oy) % 4, (x + ox) % 4]


def hash2(x, y, seed):
    """Deterministic per-texel hash in [0, 1)."""
    v = (np.asarray(x, np.int64) * 374761393 + np.asarray(y, np.int64) * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((v ^ (v >> 16)) & 0xFFFF) / 65536.0


def dither_ramp(t, ramp, th):
    """t in [0, 1] (array) -> palette indices from the ordered list `ramp`, Bayer-dithered between neighbours."""
    n = len(ramp) - 1
    f = np.clip(t, 0, 1) * n
    i = np.floor(f).astype(int)
    frac = f - i
    i = np.where(frac > th, i + 1, i)
    return np.array(ramp)[np.clip(i, 0, n)]


# ---------------------------------------------------------------------------------------------------------------
# palettes (16 colours each; index 0 is transparent where c0=1)
# ---------------------------------------------------------------------------------------------------------------

PAL_RUTS = [(0, 0, 0), (30, 21, 17), (46, 33, 25), (62, 45, 33), (80, 59, 42), (99, 74, 52), (120, 92, 65),
            (144, 112, 80), (168, 134, 98), (86, 82, 80), (118, 112, 106), (156, 148, 138), (52, 44, 58),
            (40, 30, 46), (134, 110, 84), (190, 162, 124)]
PAL_CRATE = [(16, 14, 24), (34, 36, 52), (48, 52, 72), (64, 70, 94), (86, 94, 120), (78, 80, 92), (116, 120, 132),
             (164, 168, 180), (212, 214, 226), (52, 22, 90), (98, 44, 154), (150, 88, 216), (204, 162, 255),
             (172, 124, 40), (104, 72, 26), (240, 236, 255)]
PAL_BANNER = [(0, 0, 0), (18, 10, 30), (40, 18, 66), (60, 26, 98), (80, 36, 128), (102, 50, 156), (126, 70, 182),
              (150, 98, 204), (92, 94, 108), (138, 140, 154), (184, 186, 200), (222, 222, 236), (248, 248, 255),
              (120, 96, 40), (176, 146, 70), (60, 60, 70)]
PAL_BARR = [(0, 0, 0), (20, 18, 22), (58, 56, 62), (106, 108, 118), (166, 168, 178), (176, 124, 12),
            (236, 190, 28), (255, 230, 104), (164, 56, 12), (228, 100, 24), (255, 152, 70), (234, 234, 228),
            (176, 176, 172), (188, 30, 32), (116, 16, 22), (255, 250, 214)]
PAL_LIGHT = [(0, 0, 0), (16, 14, 20), (52, 52, 62), (94, 96, 108), (146, 148, 160), (140, 74, 16), (214, 134, 38),
             (255, 190, 76), (255, 236, 160), (255, 255, 234), (72, 28, 122), (124, 66, 196), (174, 126, 248),
             (218, 194, 255), (236, 166, 86), (250, 214, 112)]


# ---------------------------------------------------------------------------------------------------------------
# ec_ruts: tracks along v (y), u (x) across a 2-tile lane; tileable in y (period 32)
# ---------------------------------------------------------------------------------------------------------------

def tex_ruts():
    W = H = 32
    y, x = np.mgrid[0:H, 0:W]
    th = bayer(H, W)
    img = np.zeros((H, W), int)
    wob = 0.7 * np.sin(2 * math.pi * y / 32.0) + 0.4 * np.sin(2 * math.pi * (2 * y + 5) / 32.0)
    # churned verge between and around the tracks: sparse dirt clods and gravel (mostly transparent)
    n = hash2(x, y, 7)
    verge = (n < 0.10) & ((np.abs(x - 16) < 5) | (x < 3) | (x > 28))
    img[verge] = np.where(hash2(x, y, 9)[verge] < 0.5, 5, 4)
    gravel = (hash2(x, y, 11) < 0.05)
    img[gravel] = np.where(hash2(x, y, 13)[gravel] < 0.5, 10, 11)
    for cx in (8.0, 24.0):
        c = cx + wob * (1 if cx < 16 else -1) * 0.6
        d = np.abs(x + 0.5 - c)
        inside = d < 3.6 + 0.6 * th
        # base: deep compacted mud, darker in the centre groove
        t = np.clip(0.30 + 0.16 * (d / 3.6) + 0.10 * (hash2(x, y, 3) - 0.5), 0, 1)
        base = dither_ramp(t, [2, 3, 4], th)
        # tyre tread: raised chevron lugs every 4 texels along the track, with a dark groove behind each
        ph = (y + np.floor(d * 0.9).astype(int)) % 4
        base = np.where((ph == 0) & (d < 2.9), 5, base)
        base = np.where((ph == 2) & (d < 2.9), 2, base)
        # oily sheen streak (a faint violet-black stain, Eclipse rigs leak)
        sheen = (np.abs(x + 0.5 - c + 1.2) < 0.6) & (((y * 3 + int(cx)) % 11) < 4)
        base = np.where(sheen, 13, base)
        img = np.where(inside, base, img)
        # raised mud ridges either side: west ridge catches the light, east ridge in shadow
        rw = (x + 0.5 > c - 5.2) & (x + 0.5 <= c - 3.6)
        re = (x + 0.5 >= c + 3.6) & (x + 0.5 < c + 5.0)
        img = np.where(rw & (th < 0.85), dither_ramp(0.55 + 0.4 * hash2(x, y, 5), [6, 7, 8, 15], th), img)
        img = np.where(re & (th < 0.8), dither_ramp(0.4 * hash2(x, y, 6), [3, 4, 14], th), img)
        # dark rim between ridge and track
        img = np.where((np.abs(d - 3.6) < 0.5) & (th < 0.6), 2, img)
    return img, PAL_RUTS


# ---------------------------------------------------------------------------------------------------------------
# ec_crate (64x64)
# ---------------------------------------------------------------------------------------------------------------

def _emblem(cell, cx, cy, r, ring, dark, lit, th):
    """Eclipse emblem: a dark disc inside a pale corona ring, with a thin bright crescent of the sun showing on its
    lower-left limb (the 'diamond ring'), painted into cell in place."""
    h, w = cell.shape
    y, x = np.mgrid[0:h, 0:w]
    d = np.hypot(x + 0.5 - cx, y + 0.5 - cy)
    disc = d < r - 1.0
    cell[disc] = dark
    d2 = np.hypot(x + 0.5 - (cx + r * 0.22), y + 0.5 - (cy - r * 0.22))
    cell[disc & (d2 > r - 1.2)] = lit
    cell[(d >= r - 1.0) & (d < r + 0.35)] = ring
    for k in range(8):                     # short corona rays
        a = k * math.pi / 4 + math.pi / 8
        px, py = int(cx + math.cos(a) * (r + 1.2)), int(cy + math.sin(a) * (r + 1.2))
        if 0 <= px < w and 0 <= py < h:
            cell[py, px] = ring


def tex_crate():
    W = H = 64
    img = np.zeros((H, W), int)
    th = bayer(32, 32)
    y, x = np.mgrid[0:32, 0:32]
    # -- A: crate side: dark slate planks, steel corner brackets with rivets, silver/violet eclipse stencil
    a = np.zeros((32, 32), int)
    plank = y // 8
    t = 0.45 + 0.18 * np.sin(x * 0.7 + plank * 1.7) * 0.3 + 0.12 * (hash2(x, plank, 21) - 0.5) - 0.10 * (y % 8) / 8
    a[:] = dither_ramp(t, [1, 2, 3, 4], th)
    a[(y % 8) == 0] = 1
    a[(y % 8) == 7] = np.where(th[(y % 8) == 7] < 0.5, 2, 1)
    frame = (x < 2) | (x > 29) | (y < 2) | (y > 29)
    a[frame] = dither_ramp(0.5 + 0.4 * ((x[frame] + y[frame]) < 32), [5, 6, 7], th[frame])
    a[(x == 0) | (x == 31) | (y == 0) | (y == 31)] = 0
    for (rx, ry) in ((3, 3), (28, 3), (3, 28), (28, 28)):
        a[ry, rx] = 8
        a[ry + 1, rx] = 5
    # corner brackets
    for (bx, by) in ((2, 2), (26, 2), (2, 26), (26, 26)):
        blk = a[by:by + 4, bx:bx + 4]
        blk[:] = np.where(blk == 0, 0, 6)
        blk[0, :] = 7
    _emblem(a, 16.0, 16.0, 7.0, 8, 0, 12, th)
    a[(np.hypot(x + 0.5 - 16, y + 0.5 - 16) < 5.0) & (a == 0)] = 9
    # stencil bars either side of the emblem
    a[15:17, 4:7] = 7
    a[15:17, 26:29] = 7
    img[0:32, 0:32] = a
    # -- B: crate lid: planks across, steel edge, crossing amber strap with buckle
    b = np.zeros((32, 32), int)
    t = 0.55 + 0.12 * (hash2(x // 8, y, 31) - 0.5) - 0.12 * (x % 8) / 8
    b[:] = dither_ramp(t, [1, 2, 3, 4], th)
    b[(x % 8) == 0] = 1
    edge = (x < 2) | (x > 29) | (y < 2) | (y > 29)
    b[edge] = dither_ramp(np.full(edge.sum(), 0.6), [5, 6, 7], th[edge])
    b[(x == 0) | (x == 31) | (y == 0) | (y == 31)] = 0
    strap = (np.abs(y - 15.5) < 2.0)
    b[strap] = np.where(np.abs(y[strap] - 15.5) < 1.0, 13, 14)
    b[13:19, 14:18] = 7
    b[14:18, 15:17] = 5
    img[0:32, 32:64] = b
    # -- C: shard canister rack front: steel frame, two glass canisters with glowing violet shards
    c = np.zeros((32, 32), int)
    c[:] = 1
    c[(x < 2) | (x > 29)] = 6
    c[(y < 2) | (y > 29) | ((y > 14) & (y < 17))] = 6
    c[(x == 0) | (x == 31) | (y == 0) | (y == 31)] = 0
    c[(x == 1) | (y == 1)] = 7
    for cx0 in (4, 17):
        for cy0 in (3, 18):
            cw, ch = 11, 11
            yy, xx = y - cy0, x - cx0
            inside = (xx >= 0) & (xx < cw) & (yy >= 0) & (yy < ch)
            glass = inside & (xx > 0) & (xx < cw - 1) & (yy > 1) & (yy < ch - 2)
            # cylinder shading across x
            u = (xx + 0.5) / cw
            shade = 0.25 + 0.75 * np.sin(np.clip(u, 0, 1) * math.pi)
            # shard crystal: a diamond in the middle, brighter core
            dia = np.abs(xx - (cw - 1) / 2) * 1.4 + np.abs(yy - ch / 2) * 0.8
            crystal = glass & (dia < 4.2)
            c[glass] = dither_ramp(shade[glass] * 0.55, [9, 10, 11], th[glass])
            c[crystal] = dither_ramp(np.clip(1.0 - dia[crystal] / 4.2, 0, 1), [10, 11, 12, 15], th[crystal])
            c[inside & ((yy <= 1) | (yy >= ch - 2))] = 7
            c[inside & ((yy == 0) | (yy == ch - 1))] = 5
            c[inside & (xx == 2) & glass & ~crystal] = 12        # glass highlight
            c[inside & (np.abs(yy - ch / 2 + 2) < 0.6) & ~crystal & glass] = 13  # strap band
    img[32:64, 0:32] = c
    # -- D: rows 32..47 steel pallet slats (tileable along x), rows 48..63 manifest clipboard | shard hazard label
    d = np.zeros((32, 32), int)
    top = y < 16
    slat = (y % 8) < 6
    t = 0.65 - 0.35 * ((y % 8) / 6.0) + 0.1 * (hash2(x, y // 8, 41) - 0.5)
    m = top & slat
    d[m] = dither_ramp(t[m], [5, 6, 7, 8], th[m])
    d[top & ((y % 8) == 0)] = 7
    d[top & ((y % 8) == 5)] = 5
    m = top & ~slat
    d[m] = np.where(th[m] < 0.3, 1, 0)
    d[top & ((x % 16) == 3) & ((y % 8) == 2)] = 8
    d[top & ((x % 16) == 12) & ((y % 8) == 2)] = 8
    # manifest: brown clipboard, white sheet with ruled lines, steel clip, violet stamp
    yy, xx = y - 16, x
    clip = (yy >= 0) & (xx < 16)
    d[clip] = 14
    d[clip & ((xx == 0) | (xx == 15) | (yy == 0) | (yy == 15))] = 0
    sheet = clip & (xx >= 2) & (xx <= 13) & (yy >= 3) & (yy <= 14)
    d[sheet] = 15
    d[sheet & (yy % 2 == 0) & (xx >= 3) & (xx <= 12) & (yy >= 6)] = 6
    d[sheet & (yy >= 3) & (yy <= 4) & (xx >= 3) & (xx <= 9)] = 3
    d[clip & (yy >= 1) & (yy <= 3) & (xx >= 5) & (xx <= 10)] = 7
    d[clip & (yy == 2) & (xx >= 6) & (xx <= 9)] = 5
    d[clip & (np.hypot(xx - 10.5, yy - 11.5) < 2.2) & sheet] = 10
    # hazard label: violet diamond with a pale shard glyph on slate
    lab = (yy >= 0) & (xx >= 16)
    lx = xx - 16
    d[lab] = 2
    dia = lab & (np.abs(lx - 7.5) + np.abs(yy - 7.5) <= 7)
    d[dia] = 10
    d[lab & (np.abs(np.abs(lx - 7.5) + np.abs(yy - 7.5) - 7) < 0.6)] = 8
    shard = lab & (np.abs(lx - 7.5) * 2.2 + np.abs(yy - 7.5) * 0.9 <= 4)
    d[shard] = 12
    d[shard & (lx == 7) & (yy < 8)] = 15
    img[32:64, 32:64] = d
    return img, PAL_CRATE


CRATE_UV = {"side": (0.5 / 64, 0.5 / 64, 31.5 / 64, 31.5 / 64), "lid": (32.5 / 64, 0.5 / 64, 63.5 / 64, 31.5 / 64),
            "rack": (0.5 / 64, 32.5 / 64, 31.5 / 64, 63.5 / 64), "steel": (32.5 / 64, 32.5 / 64, 63.5 / 64, 47.5 / 64),
            "manifest": (32 / 64, 48 / 64, 48 / 64, 1.0), "label": (48 / 64, 48 / 64, 1.0, 1.0)}


# ---------------------------------------------------------------------------------------------------------------
# ec_banner (32x32): two 16x32 pennants
# ---------------------------------------------------------------------------------------------------------------

def tex_banner():
    W, H = 32, 32
    img = np.zeros((H, W), int)
    th = bayer(H, 16)
    y, x = np.mgrid[0:H, 0:16]
    for v in (0, 1):
        b = np.zeros((H, 16), int)
        notch = 6 if v == 0 else 10                  # swallow-tail depth
        bottom = 31 - np.where(np.abs(x - 7.5) < 7, notch * (1 - np.abs(x - 7.5) / 7.5), 0).astype(int) \
            if v == 0 else 31 - (np.abs(x - 7.5) * 0 + (notch * (1 - np.abs(x - 7.5) / 8.0))).astype(int)
        if v == 1:                                   # long pointed pennant
            bottom = (18 + 13 * (1 - np.abs(x - 7.5) / 8.0)).astype(int)
        cloth = (y >= 2) & (y <= bottom) & (x >= 1) & (x <= 14)
        # vertical folds: shading bands across x
        fold = 0.55 + 0.30 * np.sin((x + 0.5) * math.pi / 4.0) - 0.15 * (y / H)
        b[cloth] = dither_ramp(fold[cloth], [2, 3, 4, 5, 6, 7], th[cloth])
        # silver trim: top hem and side edges
        b[cloth & ((x == 1) | (x == 14))] = 9
        b[(y >= 1) & (y <= 3) & (x >= 0) & (x <= 15)] = 10
        b[(y == 1) & (x >= 0) & (x <= 15)] = 11
        b[(y == 3) & (x >= 1) & (x <= 14)] = 8
        # outline along the bottom edge
        edge = cloth & ~np.roll(cloth, -1, axis=0)
        b[edge] = 1
        # emblem
        cy = 11.0 if v == 0 else 9.5
        r = 4.6 if v == 0 else 4.0
        _emblem(b, 8.0, cy, r, 11, 1, 12, th)
        if v == 0:
            b[(y >= 18) & (y <= 19) & (x >= 4) & (x <= 11)] = 10      # silver bar under the emblem
            b[(y == 21) & (x >= 6) & (x <= 9)] = 9
        img[:, v * 16:(v + 1) * 16] = b
    return img, PAL_BANNER


BANNER_UV = {"tall": (0.0, 0.0, 16 / 32, 1.0), "pennant": (16 / 32, 0.0, 1.0, 1.0)}


# ---------------------------------------------------------------------------------------------------------------
# ec_barricade (32x32)
# ---------------------------------------------------------------------------------------------------------------

FONT3x5 = {"C": ["111", "100", "100", "100", "111"], "L": ["100", "100", "100", "100", "111"],
           "O": ["111", "101", "101", "101", "111"], "S": ["111", "100", "111", "001", "111"],
           "E": ["111", "100", "110", "100", "111"], "D": ["110", "101", "101", "101", "110"]}


def tex_barricade():
    W = H = 32
    img = np.zeros((H, W), int)
    y, x = np.mgrid[0:H, 0:W]
    th = bayer(H, W)
    # rows 0..7: hazard stripe plank (tileable across 32), outline + bevel
    band = (y < 8)
    stripe = ((x + y) // 4) % 2 == 0
    img[band & stripe] = 6
    img[band & ~stripe] = 1
    img[band & stripe & (y == 1)] = 7
    img[band & stripe & (y == 6)] = 5
    img[band & ~stripe & (y == 1)] = 2
    img[(y == 0) | (y == 7)] = 1
    # rows 8..15: CLOSED board: white face, red border, dark red letters
    bd = (y >= 8) & (y < 16)
    img[bd] = 11
    img[bd & ((y == 8) | (y == 15) | (x == 0) | (x == 31))] = 14
    img[bd & ((y == 9) | (y == 14) | (x == 1) | (x == 30))] = 13
    cx = 4
    for ch in "CLOSED":
        g = FONT3x5[ch]
        for gy in range(5):
            for gx in range(3):
                if g[gy][gx] == "1":
                    img[10 + gy, cx + gx] = 14
        cx += 4
    img[bd & (y == 9) & (x > 1) & (x < 30)] = 13
    # rows 16..31, x 0..15: traffic cone (apex at top centre, reflective white bands, black rubber base)
    cy, cxx = y - 16, x
    cone = (cy >= 1) & (cy <= 12) & (np.abs(cxx - 7.5) <= 0.8 + cy * 0.52) & (x < 16)
    u = np.where(cone, (cxx - 7.5) / (0.8 + cy * 0.52 + 1e-6), 0)
    shade = 0.75 - 0.45 * u
    img[cone] = dither_ramp(shade[cone], [8, 9, 10], th[cone])
    bands = cone & (((cy >= 4) & (cy <= 5)) | ((cy >= 8) & (cy <= 9)))
    img[bands] = dither_ramp(shade[bands], [12, 11, 15], th[bands])
    img[cone & (np.abs(u) > 0.85)] = 8
    base = (cy >= 13) & (cy <= 15) & (x >= 0) & (x < 16) & (np.abs(cxx - 7.5) <= 7.4)
    img[base] = np.where(cy[base] == 13, 2, 1)
    # rows 16..31, x 16..31: steel chain-link fence panel (tileable), frame top/bottom
    fx, fy = x - 16, y - 16
    reg = (x >= 16) & (fy >= 0)
    mesh = reg & ((((fx + fy) % 4) == 0) | (((fx - fy) % 4) == 0))
    img[mesh] = np.where(((fx[mesh] + fy[mesh]) % 8) < 4, 4, 3)
    rail = reg & ((fy <= 1) | (fy >= 14))
    img[rail] = np.where((fy[rail] == 0) | (fy[rail] == 14), 4, 2)
    return img, PAL_BARR


BARR_UV = {"stripe": (0.0, 0.5 / 32, 1.0, 7.5 / 32), "board": (0.0, 8 / 32, 1.0, 16 / 32),
           "cone": (0.0, 16 / 32, 16 / 32, 1.0), "fence": (16 / 32, 16 / 32, 1.0, 1.0)}


# ---------------------------------------------------------------------------------------------------------------
# ec_light (32x32)
# ---------------------------------------------------------------------------------------------------------------

def tex_light():
    W = H = 32
    img = np.zeros((H, W), int)
    y, x = np.mgrid[0:H, 0:W]
    th = bayer(H, W)
    # left 16x32: tripod lamp card. Head: rows 2..10, x 2..13
    head = (x >= 2) & (x <= 13) & (y >= 2) & (y <= 10)
    img[head] = 2
    img[head & ((x == 2) | (x == 13) | (y == 2) | (y == 10))] = 1
    lens = (x >= 4) & (x <= 11) & (y >= 4) & (y <= 8)
    d = np.hypot((x + 0.5 - 8.0) / 4.0, (y + 0.5 - 6.5) / 2.5)
    img[lens] = dither_ramp(np.clip(1.1 - d[lens], 0, 1), [6, 7, 8, 9], th[lens])
    img[(y == 3) & (x >= 3) & (x <= 12)] = 3                      # housing top highlight
    img[(y == 1) & (x >= 6) & (x <= 9)] = 3                       # handle
    img[(y == 0) & ((x == 6) | (x == 9))] = 2
    # yoke + pole
    img[(y >= 11) & (y <= 12) & (x >= 5) & (x <= 10)] = 3
    pole = (y >= 11) & (y <= 24) & (x >= 7) & (x <= 8)
    img[pole] = np.where(x[pole] == 7, 4, 3)
    # tripod legs splaying from y 20 to 31
    for sgn in (-1, 1):
        for k in range(12):
            yy = 20 + k
            xx = 7.5 + sgn * (0.5 + k * 0.55)
            xi = int(round(xx))
            if 0 <= xi < 16:
                img[yy, xi] = 3 if sgn < 0 else 2
    img[(y >= 20) & (y <= 31) & (x == 7)] = np.where(th[(y >= 20) & (y <= 31) & (x == 7)] < 0.5, 3, 2)
    img[(y == 31) & ((x == 1) | (x == 14) | (x == 7))] = 1
    # cable tail
    img[(y == 30) & (x >= 8) & (x <= 12)] = 1
    # right top 16x16: amber light pool (radial, dithered to transparent)
    rx, ry = x - 16, y
    r = np.hypot(rx + 0.5 - 8.0, ry + 0.5 - 8.0) / 8.0
    pool = (x >= 16) & (y < 16)
    t = np.clip(1.0 - r, 0, 1)
    vis = pool & (t ** 0.8 > th * 0.95)
    img[vis] = dither_ramp(t[vis] ** 0.9, [5, 14, 6, 15, 7, 8], th[vis])
    # right bottom 16x16: violet shard glow
    gy = y - 16
    r2 = np.hypot(rx + 0.5 - 8.0, gy + 0.5 - 8.0) / 8.0
    glow = (x >= 16) & (y >= 16)
    t2 = np.clip(1.0 - r2, 0, 1)
    vis2 = glow & (t2 ** 0.8 > th * 0.95)
    img[vis2] = dither_ramp(t2[vis2] ** 0.9, [10, 11, 12, 13], th[vis2])
    return img, PAL_LIGHT


LIGHT_UV = {"lamp": (0.0, 0.0, 16 / 32, 1.0), "lamp_head": (0.0, 0.0, 16 / 32, 12 / 32),
            "lamp_legs": (0.0, 12 / 32, 16 / 32, 1.0), "pool": (16 / 32, 0.0, 1.0, 16 / 32),
            "glow": (16 / 32, 16 / 32, 1.0, 1.0)}


# ---------------------------------------------------------------------------------------------------------------
# set assembly
# ---------------------------------------------------------------------------------------------------------------

TEXTURES = [("ec_ruts", tex_ruts, 1), ("ec_crate", tex_crate, 0), ("ec_banner", tex_banner, 1),
            ("ec_barricade", tex_barricade, 1), ("ec_light", tex_light, 1)]


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


def build_set():
    """-> (set bytes, report lines, fails, generated). Stock set 007 at BASE_REV + the kit, append-only."""
    base = K.git_bytes(K.BASE_REV, K.BASE_SET_REL)
    s = nsbtx.parse(base)
    gen = generate()
    texs, pals = zip(*[encode(*g) for g in gen])
    names = {t["name"] for t in s["textures"]} | {p["name"] for p in s["palettes"]}
    fails = [f"name clash: {e['name']}" for e in list(texs) + list(pals) if e["name"] in names]
    fails += [f"name too long: {e['name']}" for e in list(texs) + list(pals) if len(e["name"]) > 15]
    st = [dict(t) for t in s["textures"]]
    sp = [dict(p) for p in s["palettes"]]
    for e in st + sp:
        e.pop("off", None)
    out = nsbtx.build(st + list(texs), sp + list(pals), pal_flag=s["header"]["pal_flag"])
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
        if t2["data"] != t["data"] or t2["c0"] != t["c0"]:
            fails.append(f"new texture did not round-trip: {t['name']}")
    # round trip: parse -> build gives the same bytes
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
