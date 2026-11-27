#!/usr/bin/env python3
"""Route 223 (Rift Sea Route & Waterfall Summit) texture set: map_texture_set_082 = stock map_texture_set_013 +
six hand-structured pixel-art textures (NumPy masks, hand-picked 16-colour palettes snapped to BGR555), drawn at
Platinum's 16 texels per tile with crisp 1-texel outlines and flat tones (no noise static; the only dither is the
ordered Bayer fleck pattern of the sea foam).

Usage:
  ~/.venvs/desmume/bin/python tools/routes/r223/textures.py                 dry run: table, VRAM, round-trip checks
  ~/.venvs/desmume/bin/python tools/routes/r223/textures.py --preview DIR   also DIR/<texture>.png + a x8 sheet
  ~/.venvs/desmume/bin/python tools/routes/r223/textures.py --write         write SET_REL (refuses if a check fails)

Idempotent: the base is always stock set 013 read from git (STOCK_REV:BASE_SET_REL, the commit before the Route 223
art), never the work tree, so reruns never append twice. Stock textures and palettes keep their names, texels and
colours (asserted); the Route 223 textures are appended after them. build_art.py imports build_set() and the UV
boxes below.

Textures (pltt16):
  r223_rift     32x32 opaque  RIFT_STRIPS: four flat crystal facet styles side by side (shadow deep indigo, mid
                              vivid violet, lit electric cyan, hot bright cyan), each 8 columns: dark outline, 1-texel
                              specular ridge, one flat fill. Constant along v; one facet = one strip.
  r223_pillar   32x32 opaque  weathered dark basalt with columnar joints. PILLAR_UV: rows 0..23 two carved rune
                              panels (left: Dialga sapphire channel with diamond glyphs, right: Palkia rose channel
                              with pearl glyphs), rows 24..31 plain basalt (caps, backs, plinths)
  r223_chain    32x32 c0=1    CHAIN_UV: rows 0..11 chunky crystal-iron chain (a face-on iron oval link threaded by
                              an edge-on violet crystal link, 3-texel bodies, 1-texel dark outlines; tiles along u),
                              rows 12..19 a glowing rune band (the floating fractured ring of the Kingdra spire),
                              rows 20..31 jagged glowing rift cracks (flat decals on the rock tops)
  r223_foam     32x32 c0=1    FOAM_V: two phases of a lapping sea-foam strip (white crest against the stone,
                              ordered-dither flecks fading out), laid on the water around every stone that meets it
  r223_pave     32x32 opaque  carved basalt flagstones, one slab per tile with a chiselled inset border (2 x 2
                              tiles per repeat), two slabs engraved with violet-inlaid glyphs: terrace, pier and
                              landing tops
  r223_terrace  32x32 opaque  TERRACE_V row bands: W carved wall with a Greek-key frieze, R rune inlay channel
                              (glowing glyphs), S riser blocks (steps, low walls, the stone ring's rim blocks)
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
STOCK_REV = "406c75f6a8dfbd4cd2165be59e1fe0edb77e7398"   # routes-wave2 contract commit: stock Route 223 data
BASE_REV = STOCK_REV
BASE_SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_013.nsbtx"
VRAM_TARGET = 160 * 1024        # PLAN goal for this set
NAME_MAX = 15
TAU = 2 * np.pi
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], float) + 0.5) / 16.0 - 0.5

# texel boxes (x0, y0, x1, y1), exclusive ends, for build_art.py's UV mapping
PILLAR_UV = {"blue": (0, 0, 16, 24), "rose": (16, 0, 32, 24), "plain": (0, 24, 32, 32)}
CHAIN_UV = {"chain": (0, 0, 32, 12), "band": (0, 12, 32, 20), "cracks": (0, 20, 32, 32)}
RIFT_STRIPS = {"shadow": 0, "mid": 1, "lit": 2, "hot": 3}          # strip k = texel columns 8k..8k+7
FOAM_V = ((0, 8), (8, 16))                                         # texel rows of the two foam phases
TERRACE_V = {"wall": (0, 16), "rune": (16, 24), "riser": (24, 32)}  # texel rows of the r223_terrace bands
TRANSPARENT_TEX = {"r223_chain", "r223_foam"}


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
# r223_rift: clean flat-shaded crystal facets (4 facet strips of 8 texel columns, constant along v)
# ---------------------------------------------------------------------------------------------------------------

def tex_rift():
    """Four facet styles side by side (RIFT_STRIPS): each strip is one flat crystal facet - a 1-texel dark outline
    (col 0), a crisp 1-texel ridge highlight (col 1) and one flat fill colour (cols 2..7). No noise, no dither:
    build_art.py maps every crystal facet onto one strip picked from its baked light (shadow / mid / lit / hot)."""
    n = 32
    X, Y, _ = grid(n)
    pal = [(14, 8, 38),        # 0 dark outline
           (38, 22, 100),      # 1 deep indigo shadow facet
           (70, 46, 150),      # 2 indigo ridge
           (132, 72, 228),     # 3 vivid violet mid facet
           (200, 156, 255),    # 4 lavender ridge
           (40, 176, 240),     # 5 electric cyan lit facet
           (120, 228, 255),    # 6 bright cyan hot facet
           (242, 252, 255)]    # 7 specular white ridge
    pal += [pal[0]] * (16 - len(pal))
    styles = [(2, 1), (4, 3), (7, 5), (7, 6)]           # (ridge, fill) of shadow, mid, lit, hot
    img = np.zeros((n, n), int)
    for k, (ridge, fill) in enumerate(styles):
        lx = X - 8 * k
        strip = (lx >= 0) & (lx < 8)
        img = np.where(strip, np.where(lx == 0, 0, np.where(lx == 1, ridge, fill)), img)
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
# r223_chain: chunky crystal-iron chain links, rune band, rift cracks (c0 = 1)
# ---------------------------------------------------------------------------------------------------------------

def outline_of(mask, wrap_x=False):
    """Pixels of `mask` with a 4-neighbour outside it (rows never wrap; columns wrap when wrap_x)."""
    m = mask.astype(bool)
    up = np.vstack([np.zeros((1, m.shape[1]), bool), m[:-1]])
    dn = np.vstack([m[1:], np.zeros((1, m.shape[1]), bool)])
    if wrap_x:
        lf, rt = np.roll(m, 1, axis=1), np.roll(m, -1, axis=1)
    else:
        lf = np.hstack([np.zeros((m.shape[0], 1), bool), m[:, :-1]])
        rt = np.hstack([m[:, 1:], np.zeros((m.shape[0], 1), bool)])
    return m & ~(up & dn & lf & rt)


def tex_chain():
    n = 32
    X, Y, B = grid(n)
    pal = [(255, 0, 255), (16, 6, 34), (72, 62, 104), (90, 40, 160), (120, 112, 158), (172, 166, 212),
           (150, 88, 236), (56, 146, 230), (120, 226, 255), (232, 255, 255), (212, 178, 255), (40, 12, 70),
           (96, 196, 250), (250, 252, 255), (150, 50, 190), (220, 216, 244)]
    img = np.zeros((n, n), int)
    # rows 0..11: one repeat = a face-on iron oval link A (u 1..18) and an edge-on crystal link B threaded
    # through it (u 12..38, wrapping): chunky 3-texel bodies with crisp 1-texel dark outlines.
    rows = Y < 12
    cy = 6.0
    ax, ay = X + 0.5 - 9.5, Y + 0.5 - cy
    ring = rows & ((ax / 8.7) ** 2 + (ay / 5.95) ** 2 <= 1.0) & ~((ax / 4.6) ** 2 + (ay / 2.3) ** 2 <= 1.0)
    bu = (X + 0.5 - 12.0) % n
    bar = rows & (bu <= 26.0) & (Y >= 3) & (Y <= 8)
    behind = bar & (X <= 6)                       # B's far end passes behind A's left side, into its hole
    front = bar & (X >= 12)                       # B's near end passes in front of A's right side

    def paint_bar(img, m):
        o = outline_of(bar, wrap_x=True) & m
        body = m & ~o
        img = np.where(body & (Y == 4), np.where((X % 7) == 3, 13, 15), img)     # lit crystal edge + glints
        img = np.where(body & (Y == 5), 10, img)                                 # lavender crystal face
        img = np.where(body & (Y >= 6), 6, img)                                  # violet underside
        return np.where(o, 1, img)
    img = paint_bar(img, behind)
    o = outline_of(ring)
    body = ring & ~o
    shade_a = np.where(ay < -2.0, np.where(ay < -3.6, 15, 5), np.where(ay > 2.0, 2, 4))
    img = np.where(body, shade_a, img)
    img = np.where(body & (ay < -3.0) & (ax > -5.5) & (ax < -2.5), 13, img)       # specular highlight top-left
    img = np.where(body & (np.abs(ay) < 1.5) & (ax < -5.5), 8, img)               # cyan glint on the left flank
    img = np.where(o, 1, img)
    img = paint_bar(img, front)
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
# r223_foam: dithered white sea-foam lapping strips (c0 = 1)
# ---------------------------------------------------------------------------------------------------------------

def tex_foam():
    """FOAM_V: rows 0..7 and 8..15 are two phases of one lapping-foam strip (v 0 = against the stone: a scalloped
    solid white crest, then Bayer-dithered foam flecks thinning out to clear water by row 7). Tiles along u."""
    n = 32
    X, Y, B = grid(n)
    pal = [(255, 0, 255), (168, 174, 210), (214, 222, 246), (250, 252, 255)]
    pal += [pal[1]] * (16 - len(pal))
    img = np.zeros((n, n), int)
    for k, ph in ((0, 0.0), (1, 2.3)):
        ly = Y - 8 * k
        strip = (ly >= 0) & (ly < 8)
        u = X + 0.5
        crest = 1.7 + 0.9 * np.sin(TAU * u / 16 + ph) + 0.5 * np.sin(TAU * 3 * u / 32 + 1.1 + ph)
        y = ly + 0.5
        img = np.where(strip & (y < crest - 0.7), 3, img)
        img = np.where(strip & (y >= crest - 0.7) & (y < crest + 0.2), 2, img)
        clump = 0.55 + 0.45 * np.sin(TAU * 2 * u / 32 + 0.7 + 1.7 * ph)
        dens = np.clip(1.0 - (y - crest) / 4.6, 0, 1) * clump
        fleck = strip & (y >= crest + 0.2) & (B + 0.5 < dens * 0.75)
        img = np.where(fleck, np.where((X + ly) % 3 == 0, 1, 2), img)
    return img, pal


# ---------------------------------------------------------------------------------------------------------------
# r223_pave: carved basalt flagstones (2 x 2 tiles per repeat, running bond, opaque)
# ---------------------------------------------------------------------------------------------------------------

PAVE_PAL = [(40, 38, 50), (58, 56, 68), (80, 78, 92), (100, 98, 112), (126, 124, 138), (140, 138, 152),
            (164, 162, 176), (198, 196, 208), (100, 110, 104), (88, 58, 150), (178, 128, 248), (226, 200, 255),
            (116, 114, 128), (134, 132, 146), (40, 38, 50), (40, 38, 50)]


def tex_pave():
    """Carved basalt flagstones, one 16 x 16 texel slab per tile (2 x 2 slabs per repeat), each one flat tone with
    a 1-texel dark joint, a lit bevel along its top/left edges, a shadowed bottom/right edge and a chiselled inset
    border; two of the four slabs carry an engraved glyph (Palkia ring / Dialga diamond) with a faint violet inlay."""
    n = 32
    X, Y, _ = grid(n)
    X, Y = X.astype(int), Y.astype(int)
    sx, sy = X % 16, Y % 16
    slab = (X // 16) + 2 * (Y // 16)
    img = np.array([4, 13, 12, 5])[slab]
    img = np.where(sy == 15, 2, img)                                       # shadowed bottom edge
    img = np.where(sx == 15, 3, img)                                       # shadowed right edge
    img = np.where((sy == 1) & (sx >= 1), 6, img)                          # lit top bevel
    img = np.where((sx == 1) & (sy >= 1), 6, img)
    # chiselled inset border: groove (dark) with a lit lower/right lip
    inset = (np.maximum(np.abs(sx - 7.5), np.abs(sy - 7.5)) == 4.5)
    img = np.where(inset, 2, img)
    lip = (np.maximum(np.abs(sx - 7.5), np.abs(sy - 7.5)) == 3.5) & ((sy > 7) | (sx > 7))
    img = np.where(lip, 6, img)
    img = np.where((sy == 0) | (sx == 0), 0, img)                          # joints
    cx, cy = sx + 0.5 - 8.0, sy + 0.5 - 8.0
    ring = (slab == 0) & (np.hypot(cx, cy) >= 1.6) & (np.hypot(cx, cy) < 2.6)
    dia = (slab == 3) & (np.abs(cx) + np.abs(cy) >= 1.4) & (np.abs(cx) + np.abs(cy) < 2.5)
    img = np.where(ring | dia, 9, img)
    img = np.where(((slab == 0) & (np.hypot(cx, cy) < 0.8)) | ((slab == 3) & (np.abs(cx) + np.abs(cy) < 0.6)), 10,
                   img)
    return img, list(PAVE_PAL)


# ---------------------------------------------------------------------------------------------------------------
# r223_terrace: carved wall frieze, rune inlay band and riser blocks (full-width row bands, opaque)
# ---------------------------------------------------------------------------------------------------------------

KEY_CELL = ["XXXXXXX.",
            "X.....X.",
            "X.XXX.X.",
            "X.X.X.X.",
            "X.X...X.",
            "X.XXXXX.",
            "X......."]
GLYPHS = [["..XX....", ".X..X...", ".X..X...", "..XX...."],      # Palkia pearl
          ["...X....", "..XXX...", "..XXX...", "...X...."],      # Dialga diamond
          [".X...X..", "..X.X...", "...X....", "...X...."],      # Giratina chevron
          ["..X.X...", "..X.X...", "..X.X...", "..X.X..."]]      # twin bars


def tex_terrace():
    """TERRACE_V row bands (each tiles along u, 32 texels = 2 tiles):
      rows 0..15  W carved wall: lit lip, a Greek-key meander frieze between two chisel grooves, block face with
                  joints every tile and a sea-darkened foot (dais / pier walls, parapets' big faces)
      rows 16..23 R rune inlay: bevelled stone lips around a dark channel of glowing glyphs (the Rift Resonance
                  ring top, inlay strips)
      rows 24..31 S riser blocks: lit lip, block face with joints, wet foot (steps, low walls, ring rim sides)"""
    n = 32
    X, Y, _ = grid(n)
    pal = [(36, 34, 46), (58, 56, 68), (78, 76, 90), (98, 96, 110), (120, 118, 132), (144, 142, 156),
           (168, 166, 180), (200, 198, 210), (46, 48, 62), (60, 32, 108), (164, 100, 246), (214, 180, 255),
           (120, 226, 255), (244, 252, 255), (100, 110, 104), (110, 108, 122)]
    img = np.full((n, n), 4)
    # W: rows 0..15
    img = np.where(Y == 0, 7, img)
    img = np.where(Y == 1, 6, img)
    img = np.where(Y == 2, 4, img)
    img = np.where((Y == 3) | (Y == 11), 1, img)
    key = np.array([[c == "X" for c in r] for r in KEY_CELL])
    for y in range(7):
        for x in range(n):
            if key[y, x % 8]:
                img[4 + y, x] = 0
            elif y > 0 and key[y - 1, x % 8]:
                img[4 + y, x] = 6                             # lit lip below each groove
            else:
                img[4 + y, x] = 3
    img = np.where(Y == 12, 6, img)
    img = np.where((Y >= 13) & (Y <= 14), np.where(Y == 13, 15, 4), img)
    img = np.where((Y >= 12) & (Y <= 14) & (X % 16 == 0), 0, img)
    img = np.where((Y >= 13) & (Y <= 14) & (X % 16 == 1), 5, img)
    img = np.where(Y == 15, 8, img)
    # R: rows 16..23
    img = np.where(Y == 16, 7, img)
    img = np.where(Y == 17, 2, img)
    img = np.where((Y >= 18) & (Y <= 21), 9, img)
    for k, g in enumerate(GLYPHS * 2):
        for y in range(4):
            for x in range(8):
                if g[y][x] == "X":
                    img[18 + y, 8 * (k % 4) + x] = 12 if k % 4 == 1 else 11
        img[19, 8 * (k % 4) + 7] = 10
        img[20, 8 * (k % 4) + 7] = 10
    img[19, 3] = img[20, 3] = 13                              # white-hot glyph cores
    img[19:21, 11] = 13
    img = np.where(Y == 22, 6, img)
    img = np.where(Y == 23, 0, img)
    # S: rows 24..31
    img = np.where(Y == 24, 7, img)
    img = np.where(Y == 25, 5, img)
    img = np.where((Y >= 26) & (Y <= 29), np.where(Y <= 27, 4, 15), img)
    img = np.where((Y >= 25) & (Y <= 29) & (X % 16 == 8), 0, img)
    img = np.where((Y >= 26) & (Y <= 29) & (X % 16 == 9), 6, img)
    img = np.where(Y == 30, 2, img)
    img = np.where(Y == 31, 8, img)
    return img, pal


TEXTURES = [("r223_rift", tex_rift), ("r223_pillar", tex_pillar), ("r223_chain", tex_chain), ("r223_foam", tex_foam),
            ("r223_pave", tex_pave), ("r223_terrace", tex_terrace)]


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
