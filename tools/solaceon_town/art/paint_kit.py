#!/usr/bin/env python3
"""Paints the Solaceon texture kit and exports it to tools/solaceon_town/assets/textures/ (lake_verity format).

Usage: python3 tools/solaceon_town/art/paint_kit.py [--sheet] [--only name,name]
  --sheet   also writes kit_sheet.png (labelled contact sheet) and kit_table.txt to the preview dir
            (common.preview_dir(): /tmp/Solaceon Update/textures in sandboxed sessions)

Everything is pixel art as code: integer drawing on grid.G with colour names from palette.py (every name is a stock
colour from set 010 or a Solaceon-light building set, apart from five blends listed in palette.DERIVED). Random detail
uses random.Random(seed) per texture, so re-running gives byte-identical PNGs.

Density: 16 texels per tile, like stock set 010 ground (16.0 measured on chunks 072/073) and the Solaceon house walls
(t4_h01_a: 16.0). See docs/solaceon_redesign/art.md for the per-texture UV rules.

Index rules (tools/lake_verity/assets/README.md): opaque pltt16 textures never use index 0; transparent textures
(c0 = 1) use index 0 as transparent. Palettes are ordered dark -> light after index 0.
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import palette as P  # noqa: E402
from grid import G  # noqa: E402

# ---------------------------------------------------------------------------------------------------------------
# Sanctuary hall
# ---------------------------------------------------------------------------------------------------------------


def hwall():
    """Pale ashlar, 2x2 tiles: 16x8 blocks in running bond, 1 px top highlight, 1 px joint, a few chips."""
    rng = random.Random(101)
    g = G(32, 32, "stone2")
    for r in range(4):
        off = 8 * (r % 2)
        for b in range(2):
            x0 = b * 16 + off
            face = rng.choice(["stone2", "stone2", "stone2", "stone1", "stone3"])
            g.rect(x0, r * 8, 16, 8, face, wrap=True)
            g.hline(x0 + 1, r * 8, 15, "stone0", wrap=True)
            g.vline(x0, r * 8, 8, "stone4", wrap=True)
            g.hline(x0, r * 8 + 7, 16, "stone4", wrap=True)
            g.hline(x0 + 1, r * 8 + 6, 15, "stone3" if face != "stone3" else "stone4", wrap=True)
            for _ in range(2):
                cx, cy = x0 + 2 + rng.randrange(12), r * 8 + 2 + rng.randrange(3)
                g.set(cx, cy, "stone3" if face != "stone3" else "stone4", wrap=True)
    return g


def scallop_rows(w, h, cols):
    """Overlapping round roof tiles: rows 8 px tall, tiles 8 px wide, every other row offset by 4. cols = (glint,
    face, side, shadow, deep) colour names."""
    glint, face, side, shadow, deep = cols
    g = G(w, h, face)
    # each tile's lower edge is an arc that hangs 2 px into the next row
    hang = [0, 1, 2, 2, 2, 2, 1, 0]
    for y in range(h):
        r, ly = divmod(y, 8)
        for x in range(w):
            off = 4 * (r % 2)
            lx = (x + off) % 8
            # the row above hangs over the top of this row
            offp = 4 * ((r - 1) % 2)
            lxp = (x + offp) % 8
            if ly < hang[lxp]:
                # the previous row's arc: its rim
                g.set(x, y, glint if ly == hang[lxp] - 1 and 1 <= lxp <= 6 else face)
                continue
            if ly == hang[lxp] or (ly == hang[lxp] + 1 and lxp in (0, 7)):
                g.set(x, y, deep)        # the shadow cast by the overlap
            elif ly == hang[lxp] + 1:
                g.set(x, y, shadow)
            elif lx == 0:
                g.set(x, y, side)        # the gap between two tiles
            elif lx == 7 and ly < 6:
                g.set(x, y, shadow)
            elif lx in (1, 2) and 3 <= ly <= 5:
                g.set(x, y, face)
            else:
                g.set(x, y, face)
    return g


def hroof():
    """Hall roof slope, mapped once across the whole slope: v 0 at the ridge, v 1 at the eave, repeat s only (2 tiles
    per repeat along the eave). Four rows of round tiles that darken from the ridge to the eave, the light-to-dark
    band stock roofs bake in (pcloof's slope strip): a slope of about 2.7 tiles gives 12 texels per tile down the
    slope, inside the stock roof range (6 to 13)."""
    rows = [("mist2", "violet0", "violet1", "violet1", "violet2"),
            ("violet0", "violet1", "violet2", "violet2", "violet3"),
            ("violet1", "violet1", "violet2", "violet3", "violet3"),
            ("violet1", "violet2", "violet3", "violet3", "violet4")]
    g = G(32, 32, "violet1")
    for r, cols in enumerate(rows):
        band = scallop_rows(32, 32, cols)
        for y in range(r * 8, r * 8 + 8):
            for x in range(32):
                g.set(x, y, band.get(x, y))
    return g


def htrim():
    """Four 8 px bands, repeat s: ridge cap, eave (tile ends over a gold fascia), plinth, violet coping."""
    g = G(32, 32, "stone2")
    # band 0: ridge cap, half-round tiles 8 px long
    for x in range(32):
        lx = x % 8
        col = ["violet3", "violet0", "violet0", "violet1", "violet1", "violet2", "violet3", "violet4"]
        for y in range(8):
            g.set(x, y, col[y])
        if lx == 7:
            g.rect(x, 1, 1, 5, "violet3")
        if lx == 0:
            g.rect(x, 1, 1, 2, "mist1")
    # band 1: eave, round tile ends seen from the front, gold fascia below
    end = ["  aaaa  ", " abbbbc ", "abbbbbbc", "bbbbbbbc", "cbbbbbcd"]
    for x0 in range(0, 32, 8):
        g.rect(x0, 8, 8, 5, "violet4")
        g.stamp(x0, 8, end, {"a": "violet0", "b": "violet1", "c": "violet2", "d": "violet3"})
    g.hline(0, 13, 32, "gold0")
    g.hline(0, 14, 32, "gold1")
    g.hline(0, 15, 32, "gold2")
    # band 2: plinth, lilac base course in 16 px blocks
    g.rect(0, 16, 32, 8, "lilac1")
    g.hline(0, 16, 32, "stone0")
    g.hline(0, 17, 32, "lilac1")
    for x0 in (0, 16):
        g.vline(x0 + 7, 17, 5, "lilac3")
        g.vline(x0 + 8, 17, 5, "lilac1")
    g.rect(0, 20, 32, 2, "lilac2")
    g.hline(0, 22, 32, "lilac3")
    g.hline(0, 23, 32, "lilac4")
    # band 3: coping, violet stones 8 px long with a drip line, its shadow on the wall
    g.rect(0, 24, 32, 8, "violet1")
    g.hline(0, 24, 32, "violet0")
    for x0 in range(0, 32, 8):
        g.vline(x0 + 7, 25, 4, "violet2")
    g.hline(0, 29, 32, "violet2")
    g.hline(0, 30, 32, "violet3")
    g.hline(0, 31, 32, "stone4")
    return g


ECL = {"k": "ink", "g": "gold0", "h": "gold1", "j": "gold2", "v": "violet1", "w": "violet2", "x": "violet3"}


def eclipse(g, cx, cy, r_disc, r_out, rays=16, ring="gold0", corona=("violet1", "violet2"), ray="gold1",
            disc="ink", rim=None):
    """The eclipse mark: a dark disc, a bright ring, a violet corona with gold rays. Integer cells; centre (cx, cy)
    in cell units (use x.0 for a centre on a cell corner)."""
    for yy in range(int(cy - r_out - 1), int(cy + r_out + 2)):
        for xx in range(int(cx - r_out - 1), int(cx + r_out + 2)):
            dx, dy = xx + 0.5 - cx, yy + 0.5 - cy
            d = math.hypot(dx, dy)
            if d > r_out:
                continue
            a = math.atan2(dy, dx) % (2 * math.pi)
            step = 2 * math.pi / rays
            k = int(round(a / step))
            da = abs(a - k * step)                    # angle to the nearest ray
            reach = 1.0 if k % 2 == 0 else 0.62       # long and short rays alternate
            if d <= r_disc:
                v = disc
                if rim and d > r_disc - 1.0:
                    v = rim
            elif d <= r_disc + 1.2:
                v = ring
            else:
                t = (d - r_disc) / (r_out - r_disc)
                if t <= reach and da * d < (1.9 * (1 - t / reach) + 0.45):
                    v = ray
                else:
                    v = corona[0] if t < 0.42 else corona[1]
            g.set(xx, yy, v)


def hatlas():
    """64x64, opaque, no repeat. Door 32x32 at (0,0); arched window 16x32 at (32,0); oculus 16x16 at (48,0); plaque
    16x16 at (48,16); pilaster 16x32 at (0,32); medallion 32x16 at (16,32); sign board 32x16 at (16,48); gate post
    16x32 at (48,32)."""
    g = G(64, 64, "stone2")
    # --- double door, 2x2 tiles: arched stone surround, violet leaves, the eclipse across both leaves
    g.rect(0, 0, 32, 32, "stone2")
    for y in range(32):
        g.set(0, y, "stone0")
        g.set(31, y, "stone4")
    cx, cy, r = 16.0, 13.0, 11.0
    for y in range(32):
        for x in range(32):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            inside = (abs(dx) <= r and y >= cy) or (dy < 0 and math.hypot(dx, dy) <= r)
            near = (abs(dx) <= r + 2 and y >= cy) or (dy < 0 and math.hypot(dx, dy) <= r + 2)
            if inside:
                g.set(x, y, "violet2")
            elif near:
                g.set(x, y, "stone0" if dx < 0 or dy < -r * 0.7 else "stone3")
    # voussoir joints
    for k in (-3, -2, -1, 1, 2, 3):
        a = math.pi / 2 + k * math.pi / 8
        for rr in (r + 0.5, r + 1.5):
            g.set(int(cx + math.cos(a) * rr), int(cy - math.sin(a) * rr), "stone4")
    g.rect(14, 0, 4, 3, "gold1")                       # keystone
    g.hline(14, 0, 4, "gold0")
    g.hline(14, 2, 4, "gold2")
    # leaves: frame, panels, the centre seam
    for y in range(32):
        for x in range(32):
            if g.get(x, y) == "violet2":
                dx, dy = x + 0.5 - cx, y + 0.5 - cy
                edge = (abs(dx) > r - 1.0 and y >= cy) or (dy < 0 and math.hypot(dx, dy) > r - 1.0)
                if edge:
                    g.set(x, y, "ink")
    g.vline(15, 3, 27, "ink")
    g.vline(16, 3, 27, "violet3")
    for x0 in (7, 18):
        g.bevel(x0, 22, 7, 6, "violet2", "violet1", "violet3")
    g.rect(5, 30, 22, 2, "stone3")                     # threshold
    g.hline(5, 30, 22, "stone0")
    g.hline(5, 31, 22, "stone4")
    eclipse(g, 16.0, 13.0, 3.6, 8.6, rays=12)
    g.set(14, 19, "gold0")                             # handles
    g.set(17, 19, "gold0")
    g.set(14, 20, "gold2")
    g.set(17, 20, "gold2")
    # --- arched window, 1x2 tiles, warm lit glass
    w = G(16, 32, "stone2")
    w.vline(0, 0, 32, "stone0")
    w.vline(15, 0, 32, "stone4")
    for y in range(32):
        for x in range(16):
            dx, dy = x + 0.5 - 8, y + 0.5 - 9
            inner = (abs(dx) <= 5 and y >= 9 and y <= 27) or (dy < 0 and math.hypot(dx, dy) <= 5)
            outer = (abs(dx) <= 6.5 and y >= 9 and y <= 28) or (dy < 0 and math.hypot(dx, dy) <= 6.5)
            if inner:
                w.set(x, y, "glow1")
            elif outer:
                w.set(x, y, "stone4" if dx > 0 else "stone3")
    for y in range(32):
        for x in range(16):
            if w.get(x, y) == "glow1":
                dx = x + 0.5 - 8
                if abs(dx) < 2.2 and 8 <= y <= 25:
                    w.set(x, y, "glow0")
                elif abs(dx) > 4 or y >= 26:
                    w.set(x, y, "glow2")
    w.vline(8, 4, 24, "stone3")                        # mullion and transom
    w.hline(3, 16, 11, "stone3")
    w.rect(2, 28, 12, 2, "stone0")                     # sill
    w.hline(2, 29, 12, "stone4")
    g.blit(w, 32, 0)
    # --- oculus (round gable window), 1x1 tile
    o = G(16, 16, "stone2")
    o.ring(8, 8, 5.2, 7.2, "stone0")
    o.ring(8, 8, 5.2, 7.2, "stone0")
    for y in range(16):
        for x in range(16):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 8)
            if 5.2 < d <= 7.2 and (x + y) > 15:
                o.set(x, y, "stone3")
    o.disc(8, 8, 5.2, "glow2")
    o.disc(8, 8, 4.0, "glow1")
    o.disc(7.4, 7.4, 2.2, "glow0")
    o.ring(8, 8, 1.8, 2.6, "stone4")                   # the eclipse ring tracery
    o.hline(2, 8, 12, "stone3")
    o.vline(8, 2, 12, "stone3")
    o.disc(8, 8, 1.8, "ink")
    g.blit(o, 48, 0)
    # --- cornerstone with a gold plaque, 1x1 tile
    p = G(16, 16, "stone3")
    p.bevel(0, 0, 16, 16, "stone3", "stone0", "stone5")
    p.bevel(3, 4, 10, 8, "gold1", "gold0", "gold2")
    for y in (6, 8, 10):
        p.hline(5, y, 6 if y != 10 else 4, "ink")
    p.set(4, 5, "gold0")
    g.blit(p, 48, 16)
    # --- pilaster 1x2 tiles: capital rows 0-7, plain shaft 8-23 (may be stretched), base 24-31
    pl = G(16, 32, "stone2")
    pl.rect(0, 0, 16, 2, "stone0")
    pl.hline(0, 2, 16, "stone4")
    pl.rect(1, 3, 14, 2, "stone1")
    pl.hline(1, 5, 14, "stone3")
    pl.rect(2, 6, 12, 2, "stone2")
    pl.hline(2, 7, 12, "stone4")
    pl.rect(2, 8, 12, 16, "stone2")
    pl.vline(2, 8, 16, "stone0")
    pl.vline(13, 8, 16, "stone4")
    for x in (5, 8, 11):
        pl.vline(x, 9, 14, "stone3")
    pl.rect(0, 8, 2, 16, "stone3")
    pl.rect(14, 8, 2, 16, "stone3")
    pl.rect(1, 24, 14, 2, "stone1")
    pl.hline(1, 24, 14, "stone0")
    pl.rect(0, 26, 16, 4, "stone3")
    pl.hline(0, 26, 16, "stone0")
    pl.rect(0, 30, 16, 2, "stone4")
    pl.hline(0, 31, 16, "stone5")
    g.blit(pl, 0, 32)
    # --- gable medallion 2x1 tiles: the eclipse in a stone roundel, carved laurels either side
    m = G(32, 16, "stone2")
    m.disc(16, 8, 7.8, "stone4")
    m.disc(15.6, 7.6, 7.2, "stone0")
    m.disc(16, 8, 6.8, "stone3")
    eclipse(m, 16, 8, 2.6, 6.2, rays=12)
    for x0 in (0, 25):                                 # moulded bands either side of the roundel
        m.hline(x0, 6, 7, "stone0")
        m.hline(x0, 7, 7, "stone3")
        m.hline(x0, 9, 7, "stone0")
        m.hline(x0, 10, 7, "stone4")
    m.hline(0, 15, 32, "stone4")
    m.hline(0, 0, 32, "stone0")
    g.blit(m, 16, 32)
    # --- sign board 2x1 tiles: violet board, gold border, a row of gold glyphs
    s = G(32, 16, "violet2")
    s.rect(0, 0, 32, 16, "ink")
    s.rect(1, 1, 30, 14, "gold1")
    s.hline(1, 1, 30, "gold0")
    s.rect(2, 2, 28, 12, "violet2")
    s.hline(2, 2, 28, "violet1")
    s.hline(2, 13, 28, "violet3")
    eclipse(s, 6.0, 8.0, 1.6, 3.6, rays=8)
    rng = random.Random(7)
    x = 11
    while x < 28:
        n = rng.choice((2, 3))
        s.rect(x, 6, n - 1, 4, "gold0")
        if rng.random() < 0.5:
            s.set(x + n - 2, 8, "violet2")
        x += n + (1 if rng.random() < 0.7 else 2)
    g.blit(s, 16, 48)
    # --- gate post 1x2 tiles: gold finial, violet cap, stone shaft with a sunk panel, base
    gp = G(16, 32, "stone2")
    gp.rect(0, 0, 16, 32, "stone2")
    gp.disc(8, 2.5, 2.2, "gold1")
    gp.disc(7.4, 1.9, 1.0, "gold0")
    gp.rect(1, 5, 14, 3, "violet1")
    gp.hline(1, 5, 14, "violet0")
    gp.hline(1, 7, 14, "violet3")
    gp.rect(0, 0, 16, 1, "stone2") if False else None
    gp.bevel(2, 8, 12, 20, "stone2", "stone0", "stone4")
    gp.bevel(4, 11, 8, 13, "stone3", "stone4", "stone0")
    gp.rect(1, 28, 14, 4, "stone3")
    gp.hline(1, 28, 14, "stone0")
    gp.hline(1, 31, 14, "stone5")
    for y in range(5):
        for x in (0, 15):
            gp.set(x, y, "stone2")
    g.blit(gp, 48, 32)
    # 15 colours max: fold the two the atlas can spare into their neighbours
    for y in range(64):
        for x in range(64):
            g.p[y][x] = {"violet0": "violet1", "stone5": "stone4"}.get(g.p[y][x], g.p[y][x])
    return g


def gate():
    """pltt4, 32x32, transparent between the bars, repeat s: iron bars with gold spear tips and two rails."""
    g = G(32, 32, None)
    for x0 in range(1, 32, 4):
        g.vline(x0, 3, 27, "ink2")
        g.vline(x0 + 1, 3, 27, "ink")
        g.set(x0, 2, "gold1")
        g.set(x0 + 1, 2, "gold1")
        g.set(x0, 1, "gold1")
        g.set(x0 + 1, 0, "gold1") if False else None
    for y in (6, 25):
        g.hline(0, y, 32, "ink2")
        g.hline(0, y + 1, 32, "ink")
    # gold rings between the rails, every other gap
    for x0 in range(3, 32, 8):
        for (dx, dy) in ((0, 0), (1, 0), (-1, 1), (2, 1), (-1, 2), (2, 2), (0, 3), (1, 3)):
            g.set(x0 + dx, 13 + dy, "gold1")
    g.hline(0, 30, 32, "ink")
    return g


# ---------------------------------------------------------------------------------------------------------------
# forecourt, plaza, garden
# ---------------------------------------------------------------------------------------------------------------

def flags(g, rng, x0=0, y0=0, w=32, h=32, mask=None):
    """Forecourt flagstones, one per tile: blueglay-style 2-tone checker dither, highlight top/left, joint
    bottom/right. mask(x, y) -> bool limits where it paints."""
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            if mask and not mask(x, y):
                continue
            lx, ly = x % 16, y % 16
            fx, fy = x // 16, y // 16
            base = "pave0" if (fx + fy * 3 + 1) % 3 else "pave1"
            v = base
            if (lx + ly) % 2 == 0 and ((lx * 7 + ly * 5 + fx * 3) % 11) < 3:
                v = "pave1" if base == "pave0" else "pave0"
            if lx == 15 or ly == 15:
                v = "lilac2"
            elif lx == 14 or ly == 14:
                v = "pave2"
            elif lx == 0 or ly == 0:
                v = "stone0"
            g.set(x, y, v)
    return g


def fcpave():
    g = G(32, 32, "pave0")
    flags(g, random.Random(3))
    g.set(5, 9, "pave2")
    g.set(22, 4, "pave2")
    g.set(23, 4, "pave2")
    g.set(9, 26, "pave2")
    return g


EMBLEM_R = 24          # emblem radius in texels: 3 tiles across at 16 texels per tile


def emblem():
    """Top-left quadrant of the 3x3-tile eclipse inlay (toned down: the hall stays the focal point). The forecourt
    flags show through most of it; the mark is a slate disc, a thin gold ring, 8 thin gold rays and 8 short lilac
    ones, and a carved lilac double ring at the rim. Texels 0..23 are the quadrant (1.5 x 1.5 tiles, centre at texel
    (24, 24), tile joint at texel 16, the same flags as sol_fcpave with its origin on the emblem's NW corner);
    texels 24..31 mirror it, so a sample on the centre line never reads outside. The map draws it as four quads with
    mirrored UVs (no flip material): NW u 0..0.75, NE u 0.75..0, and so on."""
    R = EMBLEM_R
    q = G(32, 32, "pave0")
    flags(q, random.Random(3))
    cx = cy = float(R)
    for y in range(R):
        for x in range(R):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            d = math.hypot(dx, dy)
            a = math.atan2(-dy, -dx)                 # 0 .. pi/2 in this quadrant (towards the NW corner)
            v = None
            if d <= 8.4:
                v = "lilac4"
                if d > 7.5:
                    v = "lilac5"
            elif d <= 9.7:
                v = "gold1" if a > 0.55 else "gold2"          # thin gold ring, lit from the upper left
                if d > 9.1 and 0.6 < a < 1.2:
                    v = "gold0"
            elif 19.4 < d <= 20.3:
                v = "lilac2"
            elif 20.3 < d <= 21.2:
                v = "lilac3"
            else:
                for k in range(-1, 5):                        # rays every 22.5 degrees; long ones on the axes
                    ang = k * math.pi / 8
                    off = abs(math.sin(a - ang)) * d          # distance from the ray's centre line
                    along = math.cos(a - ang) * d
                    long_ray = k % 2 == 0
                    reach = 18.6 if long_ray else 14.5
                    if along > 0 and along <= reach and off < (0.75 if long_ray else 0.6):
                        v = "gold2" if long_ray else "lilac3"
                        if long_ray and along < 13 and off < 0.45:
                            v = "gold1"
                        break
                if v is None and d <= 11.6:
                    v = "lilac1"                              # a faint corona just outside the ring
                elif v is None and d <= 13.4 and q.get(x, y) in ("pave0", "pave1") and (x + y) % 2:
                    v = "lilac1"
            if v:
                q.set(x, y, v)
    g = G(32, 32, "pave0")
    for y in range(32):
        for x in range(32):
            g.set(x, y, q.get(x if x < R else 2 * R - 1 - x, y if y < R else 2 * R - 1 - y))
    return g


def plaza():
    """Warm square setts (Hearthome beige), 4 per tile, running bond (rows offset by half a sett), soft 1 px joints
    with rounded corners, a few tone changes and chips. Lower contrast than the forecourt flags."""
    rng = random.Random(11)
    g = G(32, 32, "beige1")
    for r in range(4):
        off = 4 * (r % 2)
        for b in range(4):
            x, y = b * 8 + off, r * 8
            face = rng.choice(["beige1", "beige1", "beige1", "beige0", "beige2"])
            g.rect(x, y, 8, 8, face, wrap=True)
            g.hline(x, y + 7, 8, "beige3", wrap=True)
            g.vline(x + 7, y, 8, "beige3", wrap=True)
            g.set(x, y + 6, "beige2" if face != "beige2" else "beige3", wrap=True)
            g.set(x + 6, y, "beige2" if face != "beige2" else "beige3", wrap=True)
            if face == "beige1":
                g.hline(x + 1, y, 5, "beige0", wrap=True)
            if rng.random() < 0.5:
                g.set(x + 1 + rng.randrange(5), y + 1 + rng.randrange(5), "beige2" if face != "beige2" else "beige3",
                      wrap=True)
    return g


def border():
    """The garden of names edge, 2x1 tiles, repeat s: grass with small flowers, a kerb of rounded stones (some with a
    carved name line), the kerb's shadow on the paving side."""
    rng = random.Random(23)
    g = G(32, 16, "grass1")
    for y in range(6):
        for x in range(32):
            if (x + y) % 2 == 0 and rng.random() < 0.3:
                g.set(x, y, "grass2")
    for (x, y, c) in ((3, 1, "lily"), (11, 3, "sky"), (18, 1, "lily"), (25, 2, "pink"), (29, 4, "lily"),
                      (7, 4, "pink")):
        g.set(x, y, c)
        g.set(x, y + 1, "leaf2")
    g.hline(0, 6, 32, "grass3")
    for x0 in range(0, 32, 8):
        g.rect(x0, 7, 8, 7, "stone2")
        g.rect(x0 + 1, 7, 6, 1, "stone0")
        g.set(x0, 7, "grass3")
        g.set(x0 + 7, 7, "grass3")
        g.vline(x0 + 7, 8, 5, "stone4")
        g.hline(x0, 13, 8, "stone4")
        g.set(x0 + 1, 8, "stone0")
        if (x0 // 8) % 2 == 0:
            g.hline(x0 + 2, 10, 4, "stone5")
    g.hline(0, 14, 32, "stone5")
    g.hline(0, 15, 32, "beige1")
    return g


def furn():
    """32x32, colour 0 transparent. Bench side 24x12 at (0,0), bench top 24x8 at (0,12), memorial card board 24x12 at
    (0,20), lantern post 8x32 at (24,0) (lamp head lit)."""
    g = G(32, 32, None)
    # bench, side: backrest slats, seat edge, iron ends
    for y, c in ((0, "wood0"), (1, "wood1"), (2, "wood3"), (3, "wood0"), (4, "wood1"), (5, "wood3")):
        g.hline(2, y, 20, c)
    g.hline(1, 7, 22, "wood0")
    g.hline(1, 8, 22, "wood2")
    g.hline(1, 9, 22, "wood4")
    for x in (2, 20):
        g.rect(x, 0, 2, 12, "ink2")
        g.vline(x + 1, 0, 12, "ink")
    g.rect(1, 6, 4, 1, "ink2")
    g.rect(19, 6, 4, 1, "ink2")
    # bench, top: three slats
    for k in range(3):
        y = 12 + k * 3
        g.hline(0, y, 24, "wood0")
        g.hline(0, y + 1, 24, "wood1")
        g.hline(0, y + 2, 24, "wood4" if k < 2 else "wood3")
    g.rect(2, 12, 2, 8, "ink2")
    g.rect(20, 12, 2, 8, "ink2")
    # memorial card board: wooden frame, photo cards and pins
    g.rect(0, 20, 24, 10, "wood3")
    g.rect(1, 21, 22, 8, "wood2")
    for (x, y, w, h, c) in ((2, 22, 4, 4, "white"), (7, 22, 3, 3, "glass0"), (11, 23, 4, 4, "white"),
                            (16, 22, 5, 4, "white"), (6, 26, 4, 2, "white"), (13, 27, 4, 2, "glass0")):
        g.rect(x, y, w, h, c)
        g.set(x + w // 2, y, "gold1")
    g.set(3, 24, "ink2")
    g.set(17, 24, "ink2")
    g.set(12, 25, "ink2")
    g.rect(2, 30, 2, 2, "wood4")
    g.rect(20, 30, 2, 2, "wood4")
    # lantern post: cap, lit glass, bracket, post, base
    L = ["  kggk  ",
         " kkkkkk ",
         " k1001k ",
         " k1001k ",
         " k0000k ",
         " k1001k ",
         " k2112k ",
         " kkkkkk ",
         "  kggk  ",
         "   kk   "]
    g.stamp(24, 0, L, {"k": "ink", "g": "gold1", "0": "glow0", "1": "glow1", "2": "glow2"})
    g.rect(27, 10, 2, 19, "ink2")
    g.vline(28, 10, 19, "ink")
    g.rect(26, 15, 4, 1, "ink")
    g.rect(25, 28, 6, 2, "ink2")
    g.rect(25, 30, 6, 2, "ink")
    g.hline(25, 28, 6, "gold1")
    return g


def offer():
    """32x32, colour 0 transparent. White lilies in violet paper (0,0); yellow/pink posy in cream paper (16,0);
    wreath on an easel (0,16); three lit candles before a photo frame (16,16)."""
    g = G(32, 32, None)
    lil = ["   w  w  w     ",
           "  wlw wlwwlw   ",
           "   w y w  w    ",
           "  e  eyw e  e  ",
           "   e e y e e   ",
           "  fe  ee  ef   ",
           "  ffffeefff    ",
           "   ffffffff    ",
           "   fffgfff     ",
           "    ffgff      ",
           "    ffgff      ",
           "     fgf       ",
           "     fgf       ",
           "      g        "]
    g.stamp(1, 1, lil, {"w": "white", "l": "lily", "y": "yellow", "e": "leaf1", "f": "violet1", "g": "violet2"})
    posy = ["   p  y  o     ",
            "  pyp yoy py   ",
            "   p eye ypy   ",
            "  e yeeepoe e  ",
            "   eeyeeeye    ",
            "  cceeeeeecc   ",
            "  cccccccccc   ",
            "   ccccdcccc   ",
            "   ccccdccc    ",
            "    cccdcc     ",
            "    cccdcc     ",
            "     ccdc      ",
            "     ccdc      ",
            "      d        "]
    g.stamp(17, 1, posy, {"p": "pink", "y": "yellow", "o": "orange", "e": "leaf1", "c": "cream1", "d": "cream2"})
    # wreath
    w = G(16, 16, None)
    w.ring(8, 7, 3.2, 6.4, "leaf2")
    w.ring(8, 7, 4.2, 5.6, "leaf1")
    rng = random.Random(5)
    for k in range(10):
        a = k * math.pi / 5 + 0.2
        x, y = int(8 + math.cos(a) * 4.9), int(7 + math.sin(a) * 4.9)
        w.set(x, y, "white" if k % 2 else "violet1")
        if rng.random() < 0.5:
            w.set(x + 1, y, "leaf3")
    w.rect(6, 11, 4, 2, "violet2")
    w.set(5, 13, "violet2")
    w.set(10, 13, "violet2")
    w.line(4, 15, 7, 12, "wood3")
    w.line(12, 15, 9, 12, "wood3")
    g.blit(w, 0, 16)
    # candles + photo frame
    c = G(16, 16, None)
    c.rect(4, 0, 9, 8, "gold2")
    c.rect(5, 1, 7, 6, "sky")
    c.rect(5, 4, 7, 3, "leaf1")
    c.rect(7, 2, 3, 3, "pink")
    for (x, top) in ((3, 8), (7, 10), (11, 7)):
        c.rect(x, top, 2, 15 - top, "cream0")
        c.vline(x + 1, top, 15 - top, "cream2")
        c.set(x, top - 1, "glow2")
        c.set(x, top - 2, "glow0")
        c.set(x + 1, top - 2, "glow2")
    c.hline(1, 15, 14, "gold2")
    g.blit(c, 16, 16)
    return g


def banner():
    """16x32, colour 0 transparent: the violet Eclipse banner on its post (gold finial, crossbar, fringe)."""
    g = G(16, 32, None)
    g.rect(7, 0, 2, 2, "gold1")
    g.set(7, 0, "gold0")
    g.hline(1, 2, 14, "ink2")
    g.hline(1, 3, 14, "ink")
    g.set(0, 2, "gold1")
    g.set(15, 2, "gold1")
    g.rect(2, 4, 12, 22, "violet2")
    g.vline(2, 4, 22, "violet1")
    g.vline(3, 4, 22, "violet1")
    g.vline(13, 4, 22, "violet3")
    g.vline(8, 6, 18, "violet3")
    g.hline(2, 5, 12, "gold1")
    eclipse(g, 8.0, 12.0, 2.2, 4.6, rays=8)
    for y in (19, 21):
        g.hline(5, y, 6, "gold0")
    g.set(7, 21, "violet2")
    for x in range(2, 14):
        g.set(x, 26, "gold1")
        if x % 2 == 0:
            g.set(x, 27, "gold1")
            g.set(x, 28, "gold2")
    g.rect(7, 26, 2, 6, "ink2")
    g.vline(8, 26, 6, "ink")
    return g


def candle_frames():
    """16x16, colour 0 transparent, 3 frames (fldtanime): three candles in a brass dish; only the flames change."""
    base = G(16, 16, None)
    for (x, top) in ((3, 8), (7, 6), (11, 9)):
        base.rect(x, top, 2, 14 - top, "cream0")
        base.vline(x + 1, top, 14 - top, "cream2")
    base.rect(1, 14, 14, 1, "gold1")
    base.rect(2, 15, 12, 1, "gold2")
    flames = [
        [(0, -1, "glow2"), (0, -2, "glow0"), (1, -2, "glow1"), (0, -3, "glow1")],
        [(0, -1, "glow2"), (1, -2, "glow0"), (0, -2, "glow1"), (1, -3, "glow2")],
        [(0, -1, "glow2"), (0, -2, "glow0"), (1, -2, "glow0"), (0, -3, "glow0"), (0, -4, "glow2")],
    ]
    out = []
    for f in range(3):
        g = base.copy()
        for k, (x, top) in enumerate(((3, 8), (7, 6), (11, 9))):
            for (dx, dy, c) in flames[(f + k) % 3]:
                g.set(x + dx, top + dy, c)
        out.append(g)
    return out


# ---------------------------------------------------------------------------------------------------------------
# registration tent
# ---------------------------------------------------------------------------------------------------------------

def canvas():
    """Pilgrim-tent canvas, repeat s and t: cream and pale lilac panels, 8 px each (2 per tile), stitched seams, a
    light weave."""
    rng = random.Random(31)
    g = G(32, 32, "cream1")
    for y in range(32):
        for x in range(32):
            lilac = (x // 8) % 2 == 1
            face, hi = ("mist1", "cream0") if lilac else ("cream1", "cream0")
            v = face
            if (x + y) % 2 == 0 and rng.random() < 0.10:
                v = hi
            g.set(x, y, v)
    for x0 in range(0, 32, 8):
        g.vline(x0 + 7, 0, 32, "mist2" if (x0 // 8) % 2 else "cream2")
        for y in range(1, 32, 4):
            g.set(x0, y, "cream2")
    return g


def awning():
    """32x16, repeat s, colour 0 transparent below the scallops: violet and cream stripes, 8 px each."""
    g = G(32, 16, None)
    for x in range(32):
        violet = (x // 8) % 2 == 0
        lx = x % 8
        face, dark, deep = ("violet2", "violet3", "violet4") if violet else ("cream0", "cream1", "cream2")
        for y in range(11):
            g.set(x, y, face)
        g.set(x, 0, deep)
        g.set(x, 1, dark)
        if lx == 7:
            g.rect(x, 2, 1, 9, dark)
        # scallop: the stripe ends in a half round
        depth = [2, 3, 4, 4, 4, 4, 3, 2][lx]
        for y in range(11, 11 + depth):
            g.set(x, y, face if y < 10 + depth else dark)
    g.hline(0, 9, 32, None) if False else None
    for x in range(32):
        g.set(x, 10, "violet4" if (x // 8) % 2 == 0 else "cream2")
    return g


def tent():
    """32x32, opaque. Table top with name cards and the open registry ledger (0,0)-(31,15); front cloth (y 16-23);
    the REGISTRY sign board (y 24-31)."""
    rng = random.Random(41)
    g = G(32, 32, "wood2")
    for y in range(16):
        for x in range(32):
            g.set(x, y, "wood2" if (y // 3) % 2 == 0 else "wood1")
    g.hline(0, 15, 32, "wood0")
    g.hline(0, 0, 32, "wood3")
    # ledger
    g.rect(10, 4, 12, 8, "violet3")
    g.rect(11, 4, 5, 7, "white")
    g.rect(16, 4, 5, 7, "cream1")
    g.vline(16, 4, 7, "cream2")
    for y in (5, 7, 9):
        g.hline(12, y, 3, "ink2")
        g.hline(17, y, 3, "ink2")
    # name cards
    for (x, y) in ((1, 2), (5, 9), (2, 11), (24, 2), (26, 8), (23, 11), (6, 3)):
        g.rect(x, y, 4, 3, "white")
        g.hline(x + 1, y + 1, 2, "ink2")
        g.set(x + 3, y + 2, "cream2")
    g.rect(28, 12, 2, 2, "ink")       # ink pot
    g.set(29, 11, "gold1")
    # cloth
    g.rect(0, 16, 32, 8, "violet2")
    g.hline(0, 16, 32, "gold1")
    for x in range(3, 32, 6):
        g.vline(x, 17, 7, "violet3")
        g.vline(x + 1, 17, 7, "violet1")
    eclipse(g, 16.0, 20.0, 1.4, 3.0, rays=8)
    g.hline(0, 23, 32, "violet3")
    # sign
    g.rect(0, 24, 32, 8, "wood3")
    g.rect(0, 25, 32, 6, "cream1")
    font = C._FONT
    x = 0
    for ch in "REGISTRY":
        bits = font[ch]
        for k, b in enumerate(bits):
            if b == "1":
                g.set(x + k % 3, 25 + k // 3, "ink")
        x += 4
    g.hline(0, 31, 32, "wood3")
    _ = rng
    return g


# ---------------------------------------------------------------------------------------------------------------
# excavation
# ---------------------------------------------------------------------------------------------------------------

def scaff():
    """32x32, colour 0 transparent, repeat s and t: one standard per tile, a ledger, an X brace per 2 tiles and a
    plank deck with a toe board."""
    g = G(32, 32, None)
    g.line(3, 24, 15, 3, "steel2")
    g.line(4, 24, 16, 3, "steel1")
    g.line(18, 3, 30, 24, "steel2")
    g.line(19, 3, 31, 24, "steel1")
    for x0 in (0, 16):
        g.vline(x0, 0, 32, "steel0")
        g.vline(x0 + 1, 0, 32, "steel2")
        g.vline(x0 + 2, 0, 32, "steel3")
    for y0 in (1,):
        g.hline(0, y0, 32, "steel0")
        g.hline(0, y0 + 1, 32, "steel2")
        g.hline(0, y0 + 2, 32, "steel3")
    for x0 in (0, 16):
        g.rect(x0 - 1, 0, 5, 4, "ink2", wrap=True)
        g.rect(x0, 1, 3, 2, "steel1", wrap=True)
    # deck: planks seen from the front, toe board
    g.rect(0, 25, 32, 7, "wood1")
    g.hline(0, 25, 32, "wood0")
    g.hline(0, 28, 32, "wood3")
    g.hline(0, 29, 32, "wood0")
    g.hline(0, 31, 32, "wood4")
    for x in (7, 23):
        g.vline(x, 26, 2, "wood3")
    for x0 in (0, 16):
        g.vline(x0, 25, 7, "steel0")
        g.vline(x0 + 1, 25, 7, "steel2")
        g.vline(x0 + 2, 25, 7, "steel3")
    return g


def wfence():
    """32x16, colour 0 transparent, repeat s: posts and two rails striped warning yellow and black."""
    g = G(32, 16, None)
    for (y0, h) in ((2, 4), (9, 3)):
        for y in range(y0, y0 + h):
            for x in range(32):
                g.set(x, y, "yellow" if ((x + y) // 4) % 2 == 0 else "ink")
        g.hline(0, y0, 32, None) if False else None
        g.hline(0, y0 + h - 1, 32, "ink2")
    for x0 in (0, 16):
        g.rect(x0, 0, 2, 15, "steel1")
        g.vline(x0 + 1, 0, 15, "steel3")
        g.rect(x0 - 1, 14, 4, 2, "ink2", wrap=True)
        g.set(x0, 0, "red1")
        g.set(x0 + 1, 0, "red2")
    return g


def tarp():
    """Blue tarp, repeat s and t: broad diagonal folds (highlight + shadow) and a crease."""
    g = G(32, 32, "blue1")
    for y in range(32):
        for x in range(32):
            t = (x + 2 * y) % 32
            if t in (0, 1):
                g.set(x, y, "blue0")
            elif t in (2,):
                g.set(x, y, "blue1")
            elif t in (3, 4):
                g.set(x, y, "blue2")
            u = (2 * x - y) % 32
            if u in (16,) and g.get(x, y) == "blue1":
                g.set(x, y, "blue2")
            if u in (17,) and g.get(x, y) == "blue1":
                g.set(x, y, "blue0")
    for (x, y) in ((5, 6), (21, 22), (12, 18)):
        g.set(x, y, "blue3")
    return g


def exatlas():
    """64x32, colour 0 transparent. Work light 16x32 at (0,0); crate side 16x16 at (16,0); crate top 16x16 at
    (16,16); cable coil 16x16 at (32,0); cable 16x8 at (32,16); sandbags 16x8 at (32,24); KEEP OUT board 16x32 at
    (48,0)."""
    g = G(64, 32, None)
    lamp = ["  kkkkkkkkkk    ",
            " kssssssssssk   ",
            " ks00000001sk   ",
            " ks00000001sk   ",
            " ks01111111sk   ",
            " kssssssssssk   ",
            "  kkkkkkkkkk    ",
            "     kk         ",
            "     kk         "]
    g.stamp(1, 0, lamp, {"k": "ink", "s": "steel2", "0": "glow0", "1": "glow1"})
    g.rect(6, 9, 2, 14, "steel3")
    g.vline(6, 9, 14, "steel1")
    g.line(6, 22, 1, 31, "steel3")
    g.line(7, 22, 7, 31, "steel2")
    g.line(7, 22, 13, 31, "steel3")
    g.rect(5, 22, 4, 2, "ink2")
    # crate side
    g.rect(16, 0, 16, 16, "board1")
    for y in (4, 8, 12):
        g.hline(16, y - 1, 16, "board2")
    g.rect(16, 0, 16, 2, "wood3")
    g.rect(16, 14, 16, 2, "wood3")
    g.rect(16, 0, 2, 16, "wood3")
    g.rect(30, 0, 2, 16, "wood3")
    g.line(18, 13, 29, 2, "wood3")
    g.disc(24, 8, 3.6, "violet2")
    g.disc(24, 8, 2.2, "ink")
    # crate top
    g.rect(16, 16, 16, 16, "board1")
    for x in (20, 24, 28):
        g.vline(x - 1, 16, 16, "board2")
    g.rect(16, 16, 16, 2, "wood3")
    g.rect(16, 30, 16, 2, "wood3")
    g.rect(16, 16, 2, 16, "wood3")
    g.rect(30, 16, 2, 16, "wood3")
    # cable coil
    g.ring(40, 8, 3.0, 6.6, "ink")
    g.ring(40, 8, 4.2, 5.0, "ink2")
    g.ring(40, 8, 6.0, 6.6, "ink2")
    g.line(45, 12, 47, 15, "ink")
    # cable run (ground decal, tiles end to end along s)
    for x in range(32, 48):
        y = 19 + int(round(1.5 * math.sin((x - 32) * math.pi / 8)))
        g.set(x, y, "ink")
        g.set(x, y + 1, "ink2")
    # sandbags
    for (x, y) in ((32, 26), (38, 26), (35, 24), (42, 26)):
        g.rect(x, y, 6, 4, "dirt1")
        g.hline(x, y, 6, "board1")
        g.hline(x, y + 3, 6, "dirt2")
        g.vline(x + 5, y, 4, "dirt2")
    g.hline(32, 30, 16, "dirt2")
    # KEEP OUT board on two posts
    g.rect(49, 2, 14, 13, "ink")
    g.rect(50, 3, 12, 11, "yellow")
    g.hline(50, 3, 12, "gold0")
    tri = ["     k     ",
           "    kkk    ",
           "    kyk    ",
           "   kkykk   ",
           "   kkkkk   ",
           "  kkkykkk  ",
           "  kkkkkkk  "]
    tri = ["    k     ",
           "   kyk    ",
           "   kkk    ",
           "  kykyk   ",
           "  kkykk   ",
           " kkkkkkk  ",
           " kkkykkk  ",
           "kkkkkkkkk "]
    g.stamp(51, 4, tri, {"k": "ink", "y": "yellow"})
    for x0 in (51, 59):
        g.rect(x0, 15, 2, 17, "wood3")
        g.vline(x0 + 1, 15, 17, "wood4")
    return g


# ---------------------------------------------------------------------------------------------------------------
# ranch
# ---------------------------------------------------------------------------------------------------------------

def kwall():
    """32x32, opaque, repeat s: Day Care boards with one arched kennel opening per 2 tiles, a name plate over it,
    a concrete footing."""
    g = G(32, 32, "board1")
    for y in range(29):
        k = y % 4
        g.hline(0, y, 32, ["board0", "board1", "board1", "board2"][k])
    for x in (0, 31):
        g.vline(x, 0, 29, "wood3")
    for x in (15, 16):
        g.vline(x, 0, 9, "board2" if x == 16 else "wood3")
    # kennel opening
    cx, top, r = 16.0, 17.0, 7.0
    for y in range(10, 29):
        for x in range(32):
            dx, dy = x + 0.5 - cx, y + 0.5 - top
            frame = (abs(dx) <= r + 1.5 and y >= top) or (dy < 0 and math.hypot(dx, dy) <= r + 1.5)
            hole = (abs(dx) <= r - 0.5 and y >= top) or (dy < 0 and math.hypot(dx, dy) <= r - 0.5)
            if hole:
                g.set(x, y, "ink" if y > 22 or abs(dx) > 3 else "ink2")
            elif frame:
                g.set(x, y, "wood3" if dx > 0 else "wood2")
    g.rect(12, 9, 8, 3, "white")
    g.hline(13, 10, 6, "ink2")
    g.rect(0, 29, 32, 3, "stone3")
    g.hline(0, 29, 32, "stone2")
    g.hline(0, 31, 32, "stone5")
    return g


def yard_base(rng):
    g = G(32, 32, "sand4")
    for y in range(32):
        for x in range(32):
            if (x + y) % 2 == 0 and rng.random() < 0.35:
                g.set(x, y, "sand3")
    for _ in range(9):
        x, y = rng.randrange(32), rng.randrange(32)
        if g.get(x, y) in ("sand4", "sand3"):
            g.set(x, y, "rock2")
            g.set(x + 1, y + 1, "dirt3", wrap=True)
    return g


def yard():
    """Loading yard, repeat s and t: packed sandy dirt, darker than the sand road, pebbles. sol_ruts sits on it."""
    return yard_base(random.Random(53))


def kroof():
    """Kennel roof, repeat s and t: corrugated sheet in the Day Care's roof green, ridges along t (down the slope)
    every 4 px, a lap joint every tile."""
    g = G(32, 16, "groof2")
    for x in range(32):
        g.vline(x, 0, 16, ["groof1", "groof2", "groof2", "groof3"][x % 4])
    g.hline(0, 15, 32, "slate2")
    g.hline(0, 0, 32, "groof1")
    for x in (2, 10, 18, 26):
        g.set(x, 1, "slate3")
        g.set(x, 14, "slate3")
    return g


def ruts():
    """A yard lane 2 tiles wide, repeat t (s optional): the sol_yard dirt with two tyre ruts 1 tile apart, tread
    marks every 4 px. Lay it on top of / beside sol_yard along the way to Route 209; its edges are plain yard."""
    rng = random.Random(53)
    g = G(32, 32, "sand4")
    for y in range(32):
        for x in range(32):
            if (x + y) % 2 == 0 and rng.random() < 0.35:
                g.set(x, y, "sand3")
    # soft ruts (town-art): a pressed band of yard dirt with a 2-tone checker edge, sparse tread marks; no hard rim
    for x0 in (5, 21):
        for y in range(32):
            for dx in range(4):
                edge = dx in (0, 3)
                if edge:
                    g.set(x0 + dx, y, "dirt1" if (x0 + dx + y) % 2 == 0 and rng.random() < 0.5 else "sand3")
                else:
                    g.set(x0 + dx, y, "sand3" if (x0 + dx + y) % 2 == 0 and rng.random() < 0.3 else "dirt1")
            if y % 4 == 0:
                g.set(x0 + 1 + (y // 4) % 2, y, "dirt2")
    for _ in range(9):
        x, y = rng.randrange(32), rng.randrange(32)
        if g.get(x, y) in ("sand4", "sand3"):
            g.set(x, y, "rock2")
            g.set(x + 1, y + 1, "dirt3", wrap=True)
    return g


# ---------------------------------------------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------------------------------------------

# name, painter, format, repeat (s, t), c0, group, use. Optional: "flip" (mirror repeat), "frames", "frame_ticks",
# "texels_of" + "rename" (palette-only recolour of another kit texture).
KIT = [
    dict(name="sol_hwall", fn=hwall, fmt="pltt16", repeat=(1, 1), c0=0, group="hall",
         use="Sanctuary hall + compound wall: pale ashlar, 2x2 tiles per repeat"),
    dict(name="sol_hroof", fn=hroof, fmt="pltt16", repeat=(1, 0), c0=0, group="hall",
         use="hall roof slopes: violet round tiles darkening ridge -> eave; v 0..1 across the whole slope, 2 tiles "
             "per repeat along s"),
    dict(name="sol_htrim", fn=htrim, fmt="pltt16", repeat=(1, 0), c0=0, group="hall",
         use="bands, repeat s, 2 tiles per repeat: v 0-.25 ridge cap, .25-.5 eave + gold fascia, .5-.75 lilac "
             "plinth, .75-1 violet coping (compound wall top)"),
    dict(name="sol_hatlas", fn=hatlas, fmt="pltt16", repeat=(0, 0), c0=0, group="hall",
         use="hall details: double door with eclipse (0,0 32x32), arched lit window (32,0 16x32), oculus "
             "(48,0), plaque (48,16), pilaster (0,32 16x32), medallion (16,32 32x16), sign (16,48 32x16), gate post "
             "(48,32 16x32)"),
    dict(name="sol_gate", fn=gate, fmt="pltt4", repeat=(1, 0), c0=1, group="hall",
         use="iron gate leaves / railings, 2x2 tiles, repeat s, see-through"),
    dict(name="sol_fcpave", fn=fcpave, fmt="pltt16", repeat=(1, 1), c0=0, group="forecourt",
         use="forecourt flagstones, one flag per tile, 2x2 tiles per repeat"),
    dict(name="sol_emblem", fn=emblem, fmt="pltt16", repeat=(0, 0), c0=0, group="forecourt",
         use="eclipse inlay, 3x3 tiles: quadrant (texels 0..23) drawn as 4 quads with mirrored UVs; its flags "
             "match sol_fcpave's grid"),
    dict(name="sol_plaza", fn=plaza, fmt="pltt16", repeat=(1, 1), c0=0, group="plaza",
         use="memorial plaza: warm basket-weave setts, 2x2 tiles per repeat"),
    dict(name="sol_border", fn=border, fmt="pltt16", repeat=(1, 0), c0=0, group="plaza",
         use="garden of names edge (ground strip), 2x1 tiles, repeat s; grass side v=0, paving side v=1"),
    dict(name="sol_furn", fn=furn, fmt="pltt16", repeat=(0, 0), c0=1, group="plaza",
         use="bench side (0,0 24x12) / top (0,12 24x8), card board (0,20 24x12), lantern post (24,0 8x32)"),
    dict(name="sol_offer", fn=offer, fmt="pltt16", repeat=(0, 0), c0=1, group="plaza",
         fold={"leaf3": "leaf2", "wood3": "gold2", "cream0": "white", "sky": "lily"},
         use="offerings cards, 1x1 tile each: lilies, posy, wreath, candles + photo"),
    dict(name="sol_banner", fn=banner, fmt="pltt16", repeat=(0, 0), c0=1, group="plaza",
         use="violet Eclipse banner on a post, card 1x2 tiles"),
    dict(name="sol_candle", fn=None, frames_fn=candle_frames, fmt="pltt16", repeat=(0, 0), c0=1, group="plaza",
         frame_ticks=6, use="candle dish, 1x1 tile card, 3-frame flicker (fldtanime, 6 VBlanks per frame)"),
    dict(name="sol_canvas", fn=canvas, fmt="pltt16", repeat=(1, 1), c0=0, group="tent",
         use="tent canvas walls/roof, seams along t every tile"),
    dict(name="sol_awning", fn=awning, fmt="pltt16", repeat=(1, 0), c0=1, group="tent",
         use="striped valance, 2x1 tiles, repeat s, scalloped see-through lower edge"),
    dict(name="sol_tent", fn=tent, fmt="pltt16", repeat=(0, 0), c0=0, group="tent",
         use="table top with cards + ledger (v 0-.5, 2x1 tiles), front cloth (.5-.75), REGISTRY board (.75-1)"),
    dict(name="sol_scaff", fn=scaff, fmt="pltt16", repeat=(1, 1), c0=1, group="excavation",
         use="scaffold face, 2x2 tiles per bay, repeat s/t, see-through"),
    dict(name="sol_wfence", fn=wfence, fmt="pltt16", repeat=(1, 0), c0=1, group="excavation",
         use="warning fence, 2x1 tiles, repeat s, see-through"),
    dict(name="sol_tarp", fn=tarp, fmt="pltt16", repeat=(1, 1), c0=0, group="excavation",
         use="tarp over the dig / crates, 2x2 tiles per repeat"),
    dict(name="sol_exatlas", fn=exatlas, fmt="pltt16", repeat=(0, 0), c0=1, group="excavation",
         fold={"wood4": "wood3"},
         use="work light (0,0 16x32), crate side/top (16,0/16,16), cable coil (32,0), cable (32,16 16x8), sandbags "
             "(32,24), KEEP OUT board (48,0 16x32)"),
    dict(name="sol_kwall", fn=kwall, fmt="pltt16", repeat=(1, 0), c0=0, group="ranch",
         use="kennel block front, one kennel per 2 tiles, repeat s"),
    dict(name="sol_kroof", fn=kroof, fmt="pltt16", repeat=(1, 1), c0=0, group="ranch",
         use="kennel roof: corrugated sheet in the Day Care green, 2x1 tiles, ridges run down the slope (along t)"),
    dict(name="sol_yard", fn=yard, fmt="pltt16", repeat=(1, 1), c0=0, group="ranch",
         use="loading yard: packed dirt, 2x2 tiles per repeat"),
    dict(name="sol_ruts", fn=ruts, fmt="pltt16", repeat=(1, 1), c0=0, group="ranch",
         use="yard lane: sol_yard dirt with two tyre ruts along t, 1 tile apart; lane 2 tiles wide (u 0..1)"),
    # palette-only recolours of stock set 010 texels (32 B each, the memorial wall's blueglay -> sol_stone trick)
    dict(name="sol_steps", stock_texels="newstep", stock_palette="newstep", fmt="pltt16", repeat=(0, 1), c0=0,
         group="hall", pal_map={4: "stone0", 1: "stone2", 0: "stone3", 3: "stone4", 9: "lilac1", 10: "lilac2",
                                6: "lilac2", 5: "lilac3", 8: "lilac4"},
         use="hall front steps / gate threshold: stock newstep texels (2x2 tiles, 4 treads) in pale stone with lilac "
             "cheeks"),
    dict(name="sol_spoil", stock_texels="criffp", stock_palette="criff", fmt="pltt16", repeat=(1, 1), c0=0,
         group="excavation", lum_ramp=["ink", "wood5", "wood3", "dirt2", "dirt1"],
         use="fresh-dug pit face / spoil heap: stock criffp cliff texels in raw-earth browns (by luminance)"),
]

SIZE_BYTES = {"pltt16": 0.5, "pltt4": 0.25, "a3i5": 1}
PAL_BYTES = {"pltt16": 32, "pltt4": 8, "a3i5": 64}


def luma_order(names):
    return sorted(names, key=lambda n: (C.lum(P.colour(n)), n))


def to_indices(grids, c0, fmt):
    names = []
    for g in grids:
        for n in g.names():
            if n not in names:
                names.append(n)
    order = luma_order(names)
    n_max = {"pltt16": 16, "pltt4": 4}[fmt]
    assert len(order) + 1 <= n_max, (fmt, len(order), order)
    index = {n: i + 1 for i, n in enumerate(order)}
    pal_names = [None] + order
    out = []
    for g in grids:
        rows = []
        for r in g.p:
            row = []
            for v in r:
                if v is None:
                    assert c0, "transparent cell in an opaque texture"
                    row.append(0)
                else:
                    row.append(index[v])
            rows.append(row)
        out.append(rows)
    return out, pal_names


def stock_entry(e):
    """Palette-only recolour of a stock set 010 texture: its texel indices unchanged, a new palette from pal_map
    (index -> colour name; unmapped indices keep the stock colour) or lum_ramp (luminance ramp over colour names, the
    rule of tools/world_art/chunkedit.recolour)."""
    s = C.set010()
    t = next(t for t in s["textures"] if t["name"] == e["stock_texels"])
    sp = next(p for p in s["palettes"] if p["name"] == e["stock_palette"])
    idx = C.decode_indices(t)
    used = sorted({v for r in idx for v in r})
    stock = [C.nsbtx.rgb(c) for c in sp["colors"]][:16]
    stock += [(0, 0, 0)] * (16 - len(stock))
    if "pal_map" in e:
        pal = [P.colour(e["pal_map"][i]) if i in e["pal_map"] else stock[i] for i in range(16)]
        names = [e["pal_map"].get(i, f"{e['stock_palette']}[{i}]") if i in used else None for i in range(16)]
    else:
        pal = C.remap_by_lum(stock, used, [P.colour(n) for n in e["lum_ramp"]])
        names = [f"lum({'/'.join(e['lum_ramp'])})" if i in used else None for i in range(16)]
    return dict(e, idx=[idx], pal_names=names, palette=pal, c0=t["c0"], used=used)


def paint(only=None):
    """-> {name: dict(entry, idx=[frames of index rows], pal_names, palette rgb)} for the whole kit."""
    res = {}
    for e in KIT:
        if only and e["name"] not in only:
            continue
        if "stock_texels" in e:
            res[e["name"]] = stock_entry(e)
            continue
        grids = e["frames_fn"]() if e.get("frames_fn") else [e["fn"]()]
        for g in grids:                       # "fold": merge colours a 16-colour palette cannot hold
            for row in g.p:
                for x, v in enumerate(row):
                    row[x] = e.get("fold", {}).get(v, v)
        idx, pal_names = to_indices(grids, e["c0"], e["fmt"])
        r = dict(e, idx=idx, pal_names=pal_names)
        spare = P.colour(pal_names[1]) if not e["c0"] else (0, 0, 0)
        r["palette"] = [spare if n is None else P.colour(n) for n in pal_names]
        res[e["name"]] = r
    return res


def vram(r):
    w, h = len(r["idx"][0][0]), len(r["idx"][0])
    tex = 0 if "stock_texels" in r else int(w * h * SIZE_BYTES[r["fmt"]])
    return tex, PAL_BYTES[r["fmt"]]


def export(res):
    os.makedirs(C.ASSET_DIR, exist_ok=True)
    for name, r in res.items():
        frames = r["idx"]
        extra = {"group": r["group"], "use": r["use"], "palette_names": r["pal_names"],
                 "palette_sources": {n: P.source(n) for n in r["pal_names"] if n in P.STOCK or n in P.DERIVED}}
        if r.get("flip"):
            extra["flip"] = [bool(r["flip"][0]), bool(r["flip"][1])]
        if "stock_texels" in r:
            # palette only: the set gets palette <name>; the material binds stock texture <texels_of> + palette <name>
            extra["texels_of"] = r["stock_texels"]
            extra["stock_palette"] = r["stock_palette"]
            extra["palette"] = name
        if len(frames) > 1:
            extra["frames"] = [f"{name}.{k + 1}" for k in range(len(frames))]
            extra["frame_ticks"] = r["frame_ticks"]
        C.export_texture(name, frames[0], r["palette"], r["fmt"], r["repeat"], r["c0"], extra=extra)
        for k in range(1, len(frames) + 1) if len(frames) > 1 else ():
            C.export_texture(f"{name}.{k}", frames[k - 1], r["palette"], r["fmt"], r["repeat"], r["c0"],
                             extra={"frame_of": name, "frame_index": k - 1})


def stock_report(r):
    if "stock_texels" in r:
        return f"stock texels {r['stock_texels']}"
    return P.report([n for n in r["pal_names"] if n])


def rgba(r, frame=0):
    pal = r["palette"]
    return [[(0, 0, 0, 0) if (v == 0 and r["c0"]) else tuple(pal[v]) + (255,) for v in row] for row in r["idx"][frame]]


def table(res):
    lines = ["| texture | group | format | size | frames | texel B | palette B | repeat | c0 | stock colours |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    tt = tp = 0
    for e in KIT:
        if e["name"] not in res:
            continue
        r = res[e["name"]]
        t, p = vram(r)
        tt += t
        tp += p
        w, h = len(r["idx"][0][0]), len(r["idx"][0])
        rep = "".join(c for c, on in zip("st", r["repeat"]) if on) or "-"
        if r.get("flip"):
            rep += " (+flip)"
        frames = len(r["idx"])
        lines.append(f"| {e['name']} | {r['group']} | {r['fmt']} | {w}x{h} | {frames} | {t} | {p} | {rep} | {r['c0']} "
                     f"| {stock_report(r)} |")
    lines.append(f"| **total** | | | | | **{tt}** | **{tp}** | | | **{tt + tp} B** |")
    return "\n".join(lines), tt, tp


def sheet(res, path):
    items = []
    for e in KIT:
        if e["name"] not in res:
            continue
        r = res[e["name"]]
        t, p = vram(r)
        w, h = len(r["idx"][0][0]), len(r["idx"][0])
        items.append(([f"{e['name']} {w}x{h}", f"{r['fmt']} {t + p}B {''.join(c for c, on in zip('st', r['repeat']) if on) or '-'}"
                       f"{' C0' if r['c0'] else ''}{' X%d' % len(r['idx']) if len(r['idx']) > 1 else ''}"],
                      rgba(r), r["palette"][1:]))
    C.contact_sheet(path, items, "SOLACEON KIT (SET 010 APPEND)", cols=6)


def main():
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    res = paint(only)
    export(res)
    tab, tt, tp = table(res)
    print(tab)
    print(f"kit VRAM: {tt} texel + {tp} palette = {tt + tp} B (budget 24576)")
    if "--sheet" in sys.argv:
        d = C.preview_dir()
        sheet(res, os.path.join(d, "kit_sheet.png"))
        open(os.path.join(d, "kit_table.txt"), "w").write(tab + "\n")
        print("wrote", os.path.join(d, "kit_sheet.png"))


if __name__ == "__main__":
    main()
