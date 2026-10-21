#!/usr/bin/env python3
"""Textures and palettes for the Route 212 North brass gate, appended to overworld texture set 012.

Usage:
  python3 tools/route_212_north/textures.py                 dry run: what would be added, VRAM before/after
  python3 tools/route_212_north/textures.py --write         write res/field/maps/texture_sets/map_texture_set_012.nsbtx
  python3 tools/route_212_north/textures.py --preview DIR   PNG previews (needs nothing but tools/lake_verity/png.py)

Set 012 belongs to area 0xC: Pastoria City, Route 212 North, Route 212 South and Trophy Garden. Route 212 North is
entered through the Hearthome gate (a warp), so set 012 is the one loaded there. APPEND-ONLY: stock textures and
palettes keep their names and data, so the other maps don't change. Always rebuilt from BASE_REV (idempotent).

New texel data (2 x 512 B, procedural and deterministic):
  r212_gear    32x32 pltt16, colour 0 transparent: a ten-tooth brass gear with four spokes
  r212_clock   32x32 pltt16, colour 0 transparent: a brass-rimmed clock face, twelve marks, hands, Dialga-blue gem
New palettes only (stock texels, recoloured by luminance):
  r212_brass   for hanger   (round bosses)   -> riveted brass band: the arch ring and the jambs
  r212_plate   for blueglay (paving)         -> brass plate: the gate rails
  r212_dark    for shadowchip                -> blue-black: the dark hall behind the bars
  r212_aged    for criffp   (cliff face)     -> darker, older rock for the gate's inner returns
The bars themselves are the stock gold mansion-fence finials (area07_hei_h / _h2 with their stock palettes).
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "world_art"))
import chunkedit as C  # noqa: E402
import nsbtx  # noqa: E402

BASE_REV = "065698b277"      # arc2 before world-art: stock set 012 and chunk 085
SET_REL = "res/field/maps/texture_sets/map_texture_set_012.nsbtx"

BRASS = [(54, 30, 10), (104, 66, 22), (160, 112, 38), (212, 164, 64), (246, 220, 132)]
RECOLOURS = [
    # palette,      texture,      stock palette, ramp dark -> light,                                   keep
    ("r212_brass", "hanger", "hanger", BRASS, ()),
    ("r212_plate", "blueglay", "blueglay", [(80, 50, 18), (150, 104, 36), (206, 158, 60), (238, 206, 112)], ()),
    ("r212_dark", "shadowchip", "shadowchip", [(10, 12, 26), (22, 28, 52), (34, 44, 78)], ()),
    ("r212_aged", "criffp", "criff", [(30, 24, 26), (62, 50, 50), (96, 80, 76), (130, 112, 104)], ()),
]

GEAR_PAL = [(0, 0, 0), (40, 22, 8), (88, 54, 18), (136, 92, 32), (184, 136, 52), (222, 180, 84), (250, 228, 150),
            (64, 40, 14)]
CLOCK_PAL = [(0, 0, 0), (40, 24, 8), (104, 66, 22), (170, 122, 42), (226, 186, 90), (250, 230, 156),
             (238, 228, 196), (204, 192, 160), (46, 36, 30), (60, 104, 186), (150, 190, 246), (160, 150, 124)]


def make_gear(n=32, teeth=10):
    """indices: 0 out, 1 outline, 2..6 brass dark->light (lit from the top left), 7 hub shadow."""
    c = (n - 1) / 2
    r_out, r_root, r_rim, r_hub = 15.4, 12.6, 9.6, 3.6
    g = [[0] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            dx, dy = x - c, y - c
            r = math.hypot(dx, dy)
            a = math.atan2(dy, dx)
            # tooth profile: trapezoid teeth via a clipped cosine
            tooth = 0.5 + 0.5 * math.cos(a * teeth)
            edge = r_root + (r_out - r_root) * min(1.0, max(0.0, (tooth - 0.25) / 0.5))
            if r > edge:
                continue
            shade = 4 + (-dx - dy) / (2 * c) * 1.6          # light from the top left
            v = 0
            if r >= r_rim:                                   # rim + teeth
                v = int(round(shade)) + (1 if r < r_rim + 1.2 else 0)
            else:
                # four spokes
                ang = (a % (math.pi / 2)) - math.pi / 4
                spoke = abs(math.sin(ang)) * r < 1.9
                if r <= r_hub + 1.2:
                    v = 7 if r <= 1.4 else int(round(shade)) + 1
                elif spoke:
                    v = int(round(shade))
                else:
                    v = 0                                    # see-through between the spokes
            g[y][x] = max(0, min(7, v))
    # outline: transparent-adjacent solid pixels on the lower right get the dark outline
    out = [row[:] for row in g]
    for y in range(n):
        for x in range(n):
            if g[y][x] and any(not (0 <= x + dx < n and 0 <= y + dy < n) or g[y + dy][x + dx] == 0
                               for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1))):
                out[y][x] = 1 if (x + y) > n - 6 or g[y][x] <= 3 else 2
    for y in range(n):
        out[y][0] = out[y][n - 1] = 0
    out[0] = [0] * n
    out[n - 1] = [0] * n
    return out


def make_clock(n=32):
    """indices: 0 out, 1 outline, 2..5 brass rim, 6/7 dial, 8 marks + hands, 9/10 gem, 11 dial ring."""
    c = (n - 1) / 2
    g = [[0] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            dx, dy = x - c, y - c
            r = math.hypot(dx, dy)
            if r > 15.3:
                continue
            if r > 13.6:
                g[y][x] = 1
            elif r > 11.2:
                g[y][x] = 2 + max(0, min(3, int(round(1.6 + (-dx - dy) / 14))))
            elif r > 10.4:
                g[y][x] = 11
            else:
                g[y][x] = 6 if (dx + dy) < 6 else 7
    # twelve marks (long at 12/3/6/9)
    for k in range(12):
        a = k * math.pi / 6
        r0 = 7.6 if k % 3 else 6.4
        for t in range(0, 9):
            rr = r0 + (9.8 - r0) * t / 8
            x = round(c + math.sin(a) * rr)
            y = round(c - math.cos(a) * rr)
            g[y][x] = 8
    # hands: hour hand towards 10, minute hand towards 2 (the stopped hour of the palace)
    for a, ln, w in ((-math.pi / 3, 6.2, 1), (math.pi / 3, 9.0, 0)):
        for t in range(0, 40):
            rr = ln * t / 39
            x, y = c + math.sin(a) * rr, c - math.cos(a) * rr
            for ox in range(-w, w + 1):
                g[round(y)][round(x + ox * 0.5)] = 8
    # centre gem (Dialga blue), a small diamond
    for y in range(n):
        for x in range(n):
            d = abs(x - c) + abs(y - c)
            if d <= 2.6:
                g[y][x] = 10 if (x - c) + (y - c) < -0.5 else 9
    return g


def entries():
    gear_t, gear_p = C.indexed_texture("r212_gear", make_gear(), GEAR_PAL)
    clock_t, clock_p = C.indexed_texture("r212_clock", make_clock(), CLOCK_PAL)
    return [gear_t, clock_t], [gear_p, clock_p]


# material table for the chunk builder: material name -> (texture, palette, size)
MATERIALS = {
    "r212_gear": ("r212_gear", "r212_gear_pl", (32, 32)),
    "r212_clock": ("r212_clock", "r212_clock_pl", (32, 32)),
    "r212_brass": ("hanger", "r212_brass", (32, 32)),
    "r212_plate": ("blueglay", "r212_plate", (16, 16)),
    "r212_dark": ("shadowchip", "r212_dark", (16, 16)),
    "r212_aged": ("criffp", "r212_aged", (32, 32)),
}


def build_set():
    tex, pals = entries()
    return C.texset_append(SET_REL, BASE_REV, RECOLOURS, tex, pals)


def preview(out_bytes, d):
    import png  # tools/lake_verity/png.py
    os.makedirs(d, exist_ok=True)
    s = nsbtx.parse(out_bytes)
    T = {t["name"]: t for t in s["textures"]}
    P = {p["name"]: p for p in s["palettes"]}
    for name, (tn, pn, _) in MATERIALS.items():
        rows, _ = nsbtx.decode(T[tn], P[pn]["colors"])
        png.write_rgba(os.path.join(d, f"{name}.png"), T[tn]["w"], T[tn]["h"], [[tuple(p) for p in r] for r in rows])


def main():
    base, out, rep = build_set()
    print(rep)
    if "--preview" in sys.argv:
        preview(out, sys.argv[sys.argv.index("--preview") + 1])
    if "--write" in sys.argv:
        open(os.path.join(ROOT, SET_REL), "wb").write(out)
        print("wrote", SET_REL, len(out), "B")


if __name__ == "__main__":
    main()
