#!/usr/bin/env python3
"""Route 223 (Rift Sea Route & Waterfall Summit) texture set: map_texture_set_082 = stock map_texture_set_013 +
four procedurally generated pixel-art textures. NumPy maths (periodic value noise, Voronoi facets, polar SDF rings),
quantised onto hand-picked 16-colour palettes (snapped to BGR555) with a 4x4 Bayer ordered dither, at Platinum's
16 texels per tile.

Usage:
  ~/.venvs/desmume/bin/python tools/routes/r223/textures.py                 dry run: table, VRAM, round-trip checks
  ~/.venvs/desmume/bin/python tools/routes/r223/textures.py --preview DIR   also DIR/<texture>.png + a x8 sheet
  ~/.venvs/desmume/bin/python tools/routes/r223/textures.py --write         write SET_REL (refuses if a check fails)

Idempotent: the base is always stock set 013 read from git (BASE_REV:BASE_SET_REL), never the work tree, so reruns
never append twice. Stock textures and palettes keep their names, texels and colours (asserted); the four Route 223
textures are appended after them. build_art.py imports build_set() and the UV boxes below.

Textures (pltt16):
  r223_rift    32x32 opaque  faceted deep-violet / electric-cyan Rift Crystal: Voronoi facets with lit edges and
                             periodic cyan energy veins with white-hot cores (spires, shards, crystal clusters)
  r223_pillar  32x32 opaque  weathered dark basalt with columnar joints. PILLAR_UV: rows 0..23 two carved rune
                             panels (left: Dialga sapphire channel with diamond glyphs, right: Palkia rose channel
                             with pearl glyphs), rows 24..31 plain basalt (caps, backs, plinths)
  r223_chain   32x32 c0=1    CHAIN_UV: rows 0..11 shattered violet shard-chain links (tile along u, 2 links per
                             repeat), rows 12..19 a glowing rune band (tiles along u: the water-level ring),
                             rows 20..31 jagged glowing rift cracks (flat decals on the rock tops)
  r223_seal    64x64 c0=1    the Rift Resonance Seal: outer tick ring, glyph band, three converging nodes (Dialga
                             sapphire diamond, Palkia rose pearl, Giratina gold chevron) joined by spokes and a
                             triangle, and a white-hot rift tear in the centre (4 x 4 tiles = 16 texels per tile)
"""
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import nsbtx  # noqa: E402

SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_082.nsbtx"
BASE_REV = "HEAD"
BASE_SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_013.nsbtx"
VRAM_TARGET = 160 * 1024        # PLAN goal for this set
NAME_MAX = 15
TAU = 2 * np.pi
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], float) + 0.5) / 16.0 - 0.5

# texel boxes (x0, y0, x1, y1), exclusive ends, for build_art.py's UV mapping
PILLAR_UV = {"blue": (0, 0, 16, 24), "rose": (16, 0, 32, 24), "plain": (0, 24, 32, 32)}
CHAIN_UV = {"chain": (0, 0, 32, 12), "band": (0, 12, 32, 20), "cracks": (0, 20, 32, 32)}
TRANSPARENT_TEX = {"r223_chain", "r223_seal"}


def grid(n):
    y, x = np.mgrid[0:n, 0:n].astype(float)
    return x, y, BAYER4[(y % 4).astype(int), (x % 4).astype(int)]


def pnoise(n, cells, seed):
    """Periodic value noise in [0, 1) over an n x n texture (cells x cells lattice, smoothstep-bilinear)."""
    x, y, _ = grid(n)
    g = np.random.RandomState(seed).rand(cells, cells)
    fx, fy = x * cells / n, y * cells / n
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - x0, fy - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    x0, y0, x1, y1 = x0 % cells, y0 % cells, (x0 + 1) % cells, (y0 + 1) % cells
    a = g[y0, x0] * (1 - tx) + g[y0, x1] * tx
    b = g[y1, x0] * (1 - tx) + g[y1, x1] * tx
    return a * (1 - ty) + b * ty


def fbm(n, seed, octaves=((4, 0.55), (8, 0.3), (16, 0.15))):
    return sum(w * pnoise(n, c, seed + k * 101) for k, (c, w) in enumerate(octaves))


def ramp(t, idx, bayer, dither=1.0):
    """t in [0, 1] -> palette index along `idx`, Bayer-dithered between neighbouring entries."""
    m = len(idx)
    v = np.clip(np.floor(np.clip(t, 0, 1) * (m - 1) + 0.5 + bayer * dither), 0, m - 1).astype(int)
    return np.array(idx)[v]


def wrapv(a, b, n):
    return (a - b + n / 2) % n - n / 2


def snap(c):
    return tuple(int(v) >> 3 << 3 for v in c)


# ---------------------------------------------------------------------------------------------------------------
# r223_rift: faceted violet / cyan crystal with energy veins
# ---------------------------------------------------------------------------------------------------------------

def tex_rift():
    n = 32
    X, Y, B = grid(n)
    pal = [(18, 6, 40), (36, 14, 74), (58, 24, 112), (84, 38, 152), (114, 58, 192), (148, 88, 228), (186, 132, 250),
           (222, 190, 255), (22, 58, 120), (26, 108, 182), (44, 168, 232), (112, 230, 255), (212, 252, 255),
           (255, 255, 255), (198, 70, 212), (130, 40, 170)]
    rng = np.random.RandomState(223)
    seeds = [(rng.uniform(0, n), rng.uniform(0, n), rng.uniform(0, TAU), 1 if k in (2, 6) else 0) for k in range(9)]
    d1 = np.full((n, n), 99.0)
    d2 = np.full((n, n), 99.0)
    val = np.zeros((n, n))
    kind = np.zeros((n, n), int)
    for sx, sy, ang, kd in seeds:
        px, py = wrapv(X + 0.5, sx, n), wrapv(Y + 0.5, sy, n)
        d = np.hypot(px, py)
        g = 0.5 + 0.5 * (np.cos(ang) * px + np.sin(ang) * py) / 8.0
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        val = np.where(closer, g, val)
        kind = np.where(closer, kd, kind)
        d1 = np.where(closer, d, d1)
    val = np.clip(val + 0.12 * (fbm(n, 5) - 0.5), 0, 1)
    img = np.where(kind == 0, ramp(val, [1, 2, 15, 3, 4, 14, 5, 6], B), ramp(val, [8, 9, 3, 10, 11], B))
    edge = d2 - d1
    img = np.where(edge < 0.85, np.where(val > 0.5, 7, 6), img)                    # lit facet edges
    img = np.where((edge >= 0.85) & (edge < 1.5) & (val < 0.35), 0, img)          # dark facet shadows
    # one jagged periodic energy vein (cyan glow, white-hot core) plus a faint secondary hairline
    cy = 20.0 + 3.0 * np.sin(TAU * (X + 0.5) / n + 0.7) + 1.4 * np.sign(np.sin(TAU * 3 * (X + 0.5) / n))
    dv = np.abs(wrapv(Y + 0.5, cy, n))
    img = np.where(dv < 1.3 + 0.5 * B, 10, img)
    img = np.where(dv < 0.7, np.where((X % 3) == 0, 13, 12), img)
    cy2 = 6.0 + 2.0 * np.sin(TAU * 2 * (X + 0.5) / n + 2.1)
    dv2 = np.abs(wrapv(Y + 0.5, cy2, n))
    img = np.where((dv2 < 0.55) & (B > -0.25), 11, img)
    return img, pal


# ---------------------------------------------------------------------------------------------------------------
# r223_pillar: basalt monolith stone with carved glowing rune channels
# ---------------------------------------------------------------------------------------------------------------

def tex_pillar():
    n = 32
    X, Y, B = grid(n)
    pal = [(18, 16, 28), (44, 42, 58), (62, 60, 80), (82, 80, 102), (104, 102, 126), (128, 126, 150),
           (160, 158, 184), (30, 28, 42), (18, 38, 108), (36, 88, 204), (92, 164, 255), (196, 234, 255), (104, 22, 78),
           (198, 58, 150), (255, 130, 212), (255, 218, 242)]
    stone = fbm(n, 31) * 0.75 + 0.25 * pnoise(n, 16, 77)
    img = ramp(0.15 + 0.7 * stone, [1, 2, 3, 4, 5], B, 1.2)
    # columnar joints: irregular vertical cracks + two horizontal bedding seams (rows 0..23 and the plain strip)
    jx = [3, 12, 19, 28]
    for k, x0 in enumerate(jx):
        wob = np.round(0.8 * np.sin(TAU * (Y + 0.5) / 16 + k * 1.7)).astype(int)
        img = np.where(X == (x0 + wob) % n, 0, img)
        img = np.where(X == (x0 + wob + 1) % n, np.where(stone > 0.5, 6, 5), img)  # lit lip right of each crack
    for y0 in (11, 27):
        img = np.where((Y == y0) & ((X + y0) % 9 != 0), 7, img)
        img = np.where((Y == y0 + 1) & ((X + y0) % 9 != 0), 5, img)
    pits = (pnoise(n, 16, 99) > 0.82) & (B > 0.1)
    img = np.where(pits, 1, img)                                                     # weathering pits
    # rune panels (rows 0..23): a recessed channel x 5..10 in each 16-wide half
    for half, (dk, md, hi, wh) in ((0, (8, 9, 10, 11)), (1, (12, 13, 14, 15))):
        x0 = half * 16
        lx = X - x0
        panel = (Y < 24) & (lx >= 0) & (lx < 16)
        chan = panel & (lx >= 5) & (lx <= 10)
        img = np.where(chan, np.where(lx == 5, 7, np.where(lx == 10, 6, 1)), img)    # chisel shadow / lit lip
        inner = panel & (lx >= 6) & (lx <= 9)
        img = np.where(inner, dk, img)                                               # dim channel floor
        img = np.where(inner & ((lx == 7) | (lx == 8)), md, img)                     # glowing groove
        for gy in (3.5, 11.5, 19.5):                                                 # three glyphs per panel
            dx, dy = np.abs(lx + 0.5 - 8.0), np.abs(Y + 0.5 - gy)
            if half == 0:
                shape = dx + dy                                                      # Dialga: diamond
                ring = (shape > 2.0) & (shape < 3.1)
                core = shape < 1.1
            else:
                shape = np.hypot(dx, dy)                                             # Palkia: pearl ring
                ring = (shape > 1.9) & (shape < 3.0)
                core = shape < 1.0
            img = np.where(panel & ring & (lx >= 5) & (lx <= 10), hi, img)
            img = np.where(panel & core, wh, img)
            halo = panel & (shape >= 3.1) & (shape < 4.2) & (lx >= 4) & (lx <= 11) & (B > 0.05)
            img = np.where(halo, md, img)
        img = np.where(panel & ((lx == 0) | (lx == 15)), 0, img)                     # panel edge seams
    return img, pal


# ---------------------------------------------------------------------------------------------------------------
# r223_chain: shard-chain links, rune band, rift cracks (c0 = 1)
# ---------------------------------------------------------------------------------------------------------------

def tex_chain():
    n = 32
    X, Y, B = grid(n)
    pal = [(255, 0, 255), (16, 6, 34), (52, 20, 96), (90, 40, 160), (136, 76, 220), (184, 130, 250),
           (230, 200, 255), (56, 146, 230), (120, 226, 255), (232, 255, 255), (255, 120, 220), (40, 12, 70),
           (96, 196, 250), (255, 255, 255), (150, 50, 190), (200, 170, 255)]
    img = np.zeros((n, n), int)
    # rows 0..11: links. Link A (face-on ellipse ring) centred at u 8, link B (edge-on bar) centred at u 24.
    cy = 6.0
    cx = 9.0
    ex = (X + 0.5 - cx) / 9.4
    ey = (Y + 0.5 - cy) / 5.4
    r = np.hypot(ex, ey)
    ring = (r <= 1.0) & (np.hypot((X + 0.5 - cx) / 6.0, (Y + 0.5 - cy) / 2.2) > 1.0) & (Y < 12)
    lit = np.clip(0.55 - 0.45 * ey - 0.15 * ex, 0, 1)
    img = np.where(ring, ramp(lit, [2, 3, 4, 5, 6], B), img)
    img = np.where(ring & (r > 0.88), 1, img)                                        # dark outline
    img = np.where(ring & (ey < -0.6) & (np.abs(ex) < 0.35), 8, img)                 # cyan glint on top
    bu = wrapv(X + 0.5, 25.0, n)
    bar = (np.abs(bu) <= 8.2) & (np.abs(Y + 0.5 - cy) <= 1.9) & ~((np.abs(bu) > 6.0) & ring)
    barlit = np.clip(0.75 - 0.4 * (Y + 0.5 - cy), 0, 1)
    img = np.where(bar, ramp(barlit, [3, 4, 5, 15], B), img)
    img = np.where(bar & ((np.abs(Y + 0.5 - cy) > 1.4) | (np.abs(bu) > 7.7)), 1, img)
    # shattered: a fracture through the bar with a bright fissure, and a chip broken out of the ring's crown
    img = np.where((X == 27) & (np.abs(Y + 0.5 - cy) <= 2.0), 0, img)
    img = np.where((X == 26) & bar, 9, img)
    img = np.where((X == 28) & bar, 8, img)
    img = np.where((X >= 11) & (X <= 12) & (Y <= 2), 0, img)
    img = np.where(((X == 10) | (X == 13)) & (Y <= 2) & ring, 9, img)
    # rows 12..19: rune band (tiles along u: 4 glyphs per repeat), thin borders top and bottom
    band = (Y >= 12) & (Y < 20)
    img = np.where(band & ((Y == 12) | (Y == 19)) & ((X % 4) != 3), 3, img)
    img = np.where(band & ((Y == 13) | (Y == 18)) & ((X % 2) == 0) & (B > -0.2), 14, img)
    lu = X % 8
    ly = Y - 12
    glyphs = [
        lambda u, v: (u == 3) | ((v == 3) & (u >= 2) & (u <= 4)),                   # cross
        lambda u, v: (np.abs(u - 3) + np.abs(v - 3.5) <= 2.1) & (np.abs(u - 3) + np.abs(v - 3.5) >= 1.1),
        lambda u, v: ((u == 2) | (u == 4)) & (v >= 2) & (v <= 5),                    # twin bars
        lambda u, v: (v == 5 - np.abs(u - 3)) & (u >= 1) & (u <= 5),                  # chevron
    ]
    for k, gfun in enumerate(glyphs):
        cell = band & ((X // 8) == k) & (ly >= 1) & (ly <= 6)
        on = cell & gfun(lu.astype(float), ly.astype(float))
        img = np.where(on, np.where((lu + ly) % 3 == 0, 9, 8), img)
        near = cell & ~on & (img == 0) & (B > 0.15)
        img = np.where(near & (lu >= 1) & (lu <= 6), 7, img)
    # rows 20..31: rift cracks: a jagged main fissure with two branches (tiles along u)
    crk = (Y >= 20)
    mainy = 25.5 + 2.2 * np.sin(TAU * (X + 0.5) / 32 * 2 + 0.4) + 0.9 * np.sin(TAU * (X + 0.5) / 32 * 5)
    d = np.abs(Y + 0.5 - mainy)
    img = np.where(crk & (d < 1.9), 11, img)
    img = np.where(crk & (d < 1.2), 3, img)
    img = np.where(crk & (d < 0.75), np.where(X % 4 == 0, 9, 8), img)
    for bx, by, dirx, ln in ((7, 24.0, 1, 5), (21, 27.0, -1, 6)):
        for s in range(ln):
            x = (bx + dirx * s) % n
            y = int(by + (s * 0.9 if dirx > 0 else -s * 0.8))
            if 20 <= y < 32:
                img[y, x] = 12 if s < ln - 1 else 7
                if 20 <= y + 1 < 32 and img[y + 1, x] == 0:
                    img[y + 1, x] = 11
    return img, pal


# ---------------------------------------------------------------------------------------------------------------
# r223_seal: the Rift Resonance Seal (64 x 64, c0 = 1)
# ---------------------------------------------------------------------------------------------------------------

def tex_seal():
    n = 64
    X, Y, B = grid(n)
    pal = [(255, 0, 255), (24, 8, 48), (70, 30, 132), (120, 64, 200), (170, 120, 246), (226, 202, 255),
           (60, 118, 232), (130, 200, 255), (232, 250, 255), (200, 50, 140), (255, 130, 212), (255, 220, 246),
           (196, 136, 40), (255, 212, 100), (60, 200, 230), (255, 255, 255)]
    px, py = X + 0.5 - 32, Y + 0.5 - 32
    r = np.hypot(px, py)
    th = np.arctan2(px, -py)                  # 0 at the top (north), clockwise
    img = np.zeros((n, n), int)
    # outer ring r 28..31 with 24 rune ticks
    outer = (r >= 28.0) & (r < 31.0)
    tick = (np.abs(((th / TAU * 24) % 1.0) - 0.5) > 0.38)
    img = np.where(outer, np.where(tick, 1, ramp(1 - np.abs(r - 29.5) / 1.6, [2, 3, 4, 5], B)), img)
    img = np.where(outer & (np.abs(r - 29.5) < 0.5) & ~tick, 7, img)
    # glyph band r 23..27: 12 cells alternating diamond (sapphire) / pearl (rose)
    band = (r >= 23.0) & (r < 27.0)
    cell = np.floor((th % TAU) / TAU * 12).astype(int)
    cu = ((th % TAU) / TAU * 12) % 1.0 - 0.5          # -0.5..0.5 across the cell
    cv = r - 25.0
    gx, gy = cu * 2 * np.pi * 25.0 / 12, cv
    dia = np.abs(gx) + np.abs(gy)
    pearl = np.hypot(gx, gy)
    even = cell % 2 == 0
    img = np.where(band & (np.abs(cv) > 1.7), 2, img)
    img = np.where(band & even & (dia < 1.9), np.where(dia < 0.9, 8, 6), img)
    img = np.where(band & ~even & (pearl < 1.8), np.where(pearl < 0.8, 11, 10), img)
    img = np.where(band & (np.abs(cu) > 0.47) & (np.abs(cv) <= 1.7), 3, img)
    # inner ring r 19.5..21
    img = np.where((r >= 19.5) & (r < 21.0), ramp(1 - np.abs(r - 20.25) / 0.9, [3, 4, 5], B), img)
    # three converging nodes at r 13 (120 degrees apart), spokes to the centre and the triangle between them
    nodes = [(0.0, "dialga"), (TAU / 3, "palkia"), (2 * TAU / 3, "giratina")]
    npos = [(13.0 * np.sin(a), -13.0 * np.cos(a)) for a, _ in nodes]

    def seg_dist(ax, ay, bx, by):
        vx, vy = bx - ax, by - ay
        t = np.clip(((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy), 0, 1)
        return np.hypot(px - ax - t * vx, py - ay - t * vy)
    inside = r < 19.5
    for i in range(3):
        ax, ay = npos[i]
        bx, by = npos[(i + 1) % 3]
        dtri = seg_dist(ax, ay, bx, by)
        img = np.where(inside & (dtri < 1.25 + 0.3 * B), 3, img)
        img = np.where(inside & (dtri < 0.6), 14, img)
    # inner resonance ring around the tear
    img = np.where((r >= 7.6) & (r < 8.6), np.where(((th / TAU * 16) % 1.0) < 0.75, 4, 1), img)
    for (ax, ay), (_, who) in zip(npos, nodes):
        dx, dy = px - ax, py - ay
        if who == "dialga":
            s = np.abs(dx) + np.abs(dy)
            img = np.where(s < 4.6, 1, img)
            img = np.where(s < 3.8, ramp(1 - s / 3.8 + 0.2 * (-dy / 4), [6, 7, 8], B), img)
            img = np.where(s < 1.2, 15, img)
        elif who == "palkia":
            s = np.hypot(dx, dy)
            img = np.where(s < 4.4, 1, img)
            img = np.where(s < 3.6, ramp(1 - s / 3.6 + 0.2 * (-dy / 4), [9, 10, 11], B), img)
            img = np.where(s < 1.1, 15, img)
        else:
            # Giratina: a downward gold chevron (wings) with a dark core
            ang = np.arctan2(-ax, -ay)
            ux = dx * np.cos(ang) - dy * np.sin(ang)
            uy = dx * np.sin(ang) + dy * np.cos(ang)
            chev = np.abs(uy - (2.2 - 0.9 * np.abs(ux)))
            body = (np.abs(ux) < 4.4) & (chev < 1.7)
            img = np.where(body, np.where(chev < 0.8, 13, 12), img)
            img = np.where(np.hypot(dx, dy) < 1.2, 1, img)
            img = np.where(np.hypot(dx, dy) < 0.6, 13, img)
    # central rift tear: a vertical jagged lens, violet rim, white-hot core
    lens = np.abs(px) / (2.6 * np.sqrt(np.clip(1 - (py / 6.2) ** 2, 0, 1)) + 1e-6) + 0.15 * np.sin(py * 2.3)
    img = np.where((lens < 1.4) & (np.abs(py) < 6.4), 1, img)
    img = np.where((lens < 1.0) & (np.abs(py) < 6.0), 4, img)
    img = np.where((lens < 0.62) & (np.abs(py) < 5.2), 7, img)
    img = np.where((lens < 0.3) & (np.abs(py) < 4.4), np.where(B > 0, 15, 8), img)
    img = np.where(r >= 31.0, 0, img)
    return img, pal


TEXTURES = [("r223_rift", tex_rift), ("r223_pillar", tex_pillar), ("r223_chain", tex_chain), ("r223_seal", tex_seal)]


def pal_name(tex):
    return tex + "_pl"


# ---------------------------------------------------------------------------------------------------------------
# encode, append, verify
# ---------------------------------------------------------------------------------------------------------------

def generate():
    """-> [(name, index grid, palette RGB list snapped to BGR555)]."""
    out = []
    for name, fn in TEXTURES:
        idx, pal = fn()
        idx = np.asarray(idx, int)
        assert idx.shape[0] == idx.shape[1] and idx.min() >= 0 and idx.max() < 16, name
        assert len(pal) == 16, name
        out.append((name, idx, [snap(c) for c in pal]))
    return out


def encode(name, idx, pal):
    flat = idx.reshape(-1).tolist()
    data = bytes(flat[i] | flat[i + 1] << 4 for i in range(0, len(flat), 2))
    n = idx.shape[0]
    tex = dict(name=name, fmt=3, w=n, h=n, c0=1 if name in TRANSPARENT_TEX else 0, data=data)
    return tex, dict(name=pal_name(name), colors=[nsbtx.bgr555(c) for c in pal], pltt4=0)


def git_bytes(rev, rel):
    return subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{rel}"], check=True, capture_output=True).stdout


def build_set():
    """-> dict(bytes, rows, fails, vram=(base, out), table, generated)."""
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
                fails.append(f"{a} clashes with a stock set-013 entry")
            if len(a) > NAME_MAX:
                fails.append(f"{a} is longer than {NAME_MAX} characters")
        new_t.append(t)
        new_p.append(p)
        rows.append((name, p["name"], f"{t['w']}x{t['h']}", t["c0"], len(t["data"]), 32,
                     int(len(set(idx.reshape(-1).tolist())))))
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
    if [t["name"] for t in so["textures"]][:len(sb["textures"])] != [t["name"] for t in sb["textures"]]:
        fails.append("stock texture order changed")
    for name, idx, pal in gen:
        t2, p2 = OT.get(name), OP.get(pal_name(name))
        if not t2 or not p2:
            fails.append(f"{name}: missing after build")
            continue
        _, ind = nsbtx.decode(t2, p2["colors"])
        n = idx.shape[0]
        if (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != (3, n, n, 1 if name in TRANSPARENT_TEX else 0):
            fails.append(f"{name}: format/size/c0 changed in the round trip")
        if [list(r) for r in ind] != idx.tolist():
            fails.append(f"{name}: texel indices differ after the round trip")
        if p2["colors"][:16] != [nsbtx.bgr555(c) for c in pal]:
            fails.append(f"{name}: palette colours differ after the round trip")
    if len(so["textures"]) != len(sb["textures"]) + len(new_t) or len(so["palettes"]) != len(sb["palettes"]) + len(new_p):
        fails.append("entry count mismatch")
    if nsbtx.build([dict(t) for t in so["textures"]], [dict(p) for p in so["palettes"]], keep_offsets=True,
                   pal_flag=so["header"]["pal_flag"]) != out:
        fails.append("set parse -> rebuild is not byte-identical")
    vb, vo = nsbtx.vram_usage(sb), nsbtx.vram_usage(so)
    if sum(vo) > VRAM_TARGET:
        fails.append(f"set VRAM {sum(vo)} B > target {VRAM_TARGET}")
    table = {t["name"]: {"size": [t["w"], t["h"]]} for t in so["textures"]}
    return dict(bytes=out, rows=rows, fails=fails, vram=(vb, vo), table=table, generated=gen,
                palettes={p["name"] for p in so["palettes"]}, stock_textures=len(sb["textures"]),
                stock_palettes=len(sb["palettes"]))


def write_preview(d, gen):
    from PIL import Image
    os.makedirs(d, exist_ok=True)
    cell = 256 + 8
    sheet = Image.new("RGB", (len(gen) * cell, 2 * cell), (20, 18, 30))
    for k, (name, idx, pal) in enumerate(gen):
        n = idx.shape[0]
        img = Image.new("RGB", (n, n))
        cols = [pal[i] if not (name in TRANSPARENT_TEX and i == 0) else (40, 50, 70) for i in range(16)]
        img.putdata([cols[i] for i in idx.reshape(-1).tolist()])
        img.save(os.path.join(d, name + ".png"))
        sheet.paste(img.resize((256, 256), Image.NEAREST), (k * cell, 0))
        half = img.resize((128, 128), Image.NEAREST)
        for oy in (0, 1):
            for ox in (0, 1):
                sheet.paste(half, (k * cell + ox * 128, cell + oy * 128))
    sheet.save(os.path.join(d, "r223_textures_sheet.png"))


def report(res):
    vb, vo = res["vram"]
    print(f"map_texture_set_082 = git {BASE_REV}:{BASE_SET_REL} ({res['stock_textures']} textures, "
          f"{res['stock_palettes']} palettes) + {len(res['rows'])} Route 223 textures")
    print(f"{'texture':12s} {'palette':15s} {'size':6s} {'c0':>2s} {'texel B':>7s} {'pal B':>5s} {'colours':>7s}")
    for name, pn, size, c0, tb, pb, nc in res["rows"]:
        print(f"{name:12s} {pn:15s} {size:6s} {c0:2d} {tb:7d} {pb:5d} {nc:7d}")
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
        print("PASS appended textures round-trip (texels + BGR555 palettes); stock entries unchanged; set rebuild "
              "byte-identical; VRAM within target")
    if "--write" in args:
        if res["fails"]:
            print("refusing to write: checks failed")
            return 1
        open(os.path.join(ROOT, SET_REL), "wb").write(res["bytes"])
        print("wrote", SET_REL, len(res["bytes"]), "B")
    return 1 if res["fails"] else 0


if __name__ == "__main__":
    sys.exit(main())
