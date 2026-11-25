#!/usr/bin/env python3
"""Textures for the Solaceon Ruins raid dressing, appended to map texture set 055 (standard library only).

Usage:
  python3 tools/solaceon_ruins/textures.py                 dry run: what is added, VRAM before/after, checks
  python3 tools/solaceon_ruins/textures.py --preview DIR   PNG + JSON per texture (blender_preview format) and a
                                                           contact sheet DIR/raid_textures.png
  python3 tools/solaceon_ruins/textures.py --write         write res/field/maps/texture_sets/map_texture_set_055.nsbtx

Set 055 belongs to area 56: every Solaceon Ruins room, all of Turnback Cave and the Celestic Town cave. APPEND-ONLY:
stock textures and palettes keep their names, data and offsets-by-name, so those maps don't change. The set is
rebuilt from ruins.BASE_REV each run (idempotent; it never reads its own output).

All new textures are 16-colour (pltt16) at the stock density of 16 texels per tile, except the a5i3 light pool
(the stock exit light dun_light is a5i3 too). Palettes are sampled from the stock set: the sandstone browns of
dun_wall_* / dun_floor2, the grey-greens of dun_level / dun_floor, plus a dim Eclipse violet for the shard accents.

  rd_cable    32x8   two floor cables, ties every tile (laid 2 tiles per repeat, 0.5 tile wide)
  rd_crack    32x32  floor fissures with a dim violet core (2x2 tiles), transparent around
  rd_steel    16x16  dark machine steel with rivets (plinth sides)
  rd_plate    16x16  plinth top: steel, a round shard socket, a black-sun ring stencil
  rd_scaff    16x32  scaffold face: galvanised poles, ledgers and a cross brace, transparent between (1x2 tiles)
  rd_plank    16x16  scaffold boards (warm wood)
  rd_lamp     16x16  work-lamp head (yellow housing, hot lens)
  rd_crate    16x16  plain wooden crate side
  rd_tunnel   32x32  a fresh tunnel mouth: broken sandstone rim around a black hole, transparent outside
  rd_rubble   16x16  loose sandstone chunks, transparent around (floor decal)
  rd_glow     32x32  a5i3 warm work-light pool (translucent)
"""
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ruins as R  # noqa: E402

sys.path.insert(0, os.path.join(R.ROOT, "tools", "world_art"))
import chunkedit as C  # noqa: E402
import nsbtx  # noqa: E402
import png  # noqa: E402

BASE_REV = R.BASE_REV
SET_REL = R.texset_rel()
TRANSP = (180, 180, 180)     # index 0 (transparent when c0)

# palettes sampled from stock set 055 (dun_wall_n / dun_wall_c / dun_floor2 / dun_level / dun_floor), plus violet
SAND = [(57, 41, 24), (74, 57, 24), (98, 74, 32), (123, 98, 49), (148, 123, 82), (164, 139, 98), (189, 156, 115)]
GREY = [(32, 57, 49), (49, 65, 57), (74, 90, 82), (106, 115, 106), (131, 139, 131), (172, 180, 172)]
FLOOR = [(74, 90, 74), (82, 98, 82), (98, 115, 98), (106, 131, 106)]
VIOLET = [(52, 30, 74), (92, 52, 132), (140, 96, 186), (190, 160, 226)]
STEEL = [(24, 28, 36), (44, 50, 62), (70, 78, 92), (100, 108, 122), (140, 148, 160), (190, 196, 204)]
WOOD = [(74, 49, 24), (106, 74, 41), (139, 98, 57), (172, 131, 82), (205, 164, 106)]
YELLOW = [(164, 120, 24), (222, 180, 41), (255, 230, 120), (255, 252, 220)]


def grid(w, h, v=0):
    return [[v] * w for _ in range(h)]


def put(g, x, y, v):
    if 0 <= y < len(g) and 0 <= x < len(g[0]):
        g[y][x] = v


def tex_cable():
    pal = [TRANSP, STEEL[0], STEEL[1], STEEL[2], STEEL[3], VIOLET[0], VIOLET[1], YELLOW[1], (20, 20, 22)]
    g = grid(32, 8)
    for x in range(32):
        # cable A: rows 1-3 (black rubber), cable B: rows 5-7 (violet-sheathed power line)
        g[0][x] = 0
        g[1][x], g[2][x], g[3][x] = 3, 2, 8
        g[4][x] = 0
        g[5][x], g[6][x], g[7][x] = 6, 5, 8
        if x % 16 in (7, 8):              # ties every tile
            for y in (1, 2, 3, 5, 6, 7):
                g[y][x] = 7 if y in (2, 6) else 4
    return g, pal, 1


def tex_crack(rng):
    pal = [TRANSP, (30, 26, 22), SAND[0], FLOOR[0], VIOLET[0], VIOLET[1], VIOLET[2], (60, 58, 50)]
    g = grid(32, 32)

    def walk(x, y, ang, n, w):
        for _ in range(n):
            xi, yi = int(round(x)), int(round(y))
            if not (2 <= xi <= 29 and 2 <= yi <= 29):
                return
            put(g, xi, yi, 5 if w > 1 else 4)
            if w > 1:
                put(g, xi + 1, yi, 4 if rng.random() < 0.5 else 1)
                if rng.random() < 0.4:
                    put(g, xi, yi, 6)
            put(g, xi, yi + 1, 1)
            ang += rng.uniform(-0.55, 0.55)
            x += math.cos(ang)
            y += math.sin(ang)
            if rng.random() < 0.10 and w > 1:
                walk(x, y, ang + rng.choice((-1.0, 1.0)), n // 2, 1)
    walk(16, 16, 0.35, 15, 2)
    walk(16, 16, 0.35 + math.pi, 15, 2)
    walk(16, 16, 1.8, 11, 2)
    walk(16, 16, -1.3, 10, 1)
    walk(16, 16, 2.7, 8, 1)
    # dark rim around every crack pixel
    for y in range(32):
        for x in range(32):
            if g[y][x] == 0 and 0 < x < 31 and 0 < y < 31 and any(g[y + dy][x + dx] in (4, 5, 6) for dx, dy in
                                                                  ((1, 0), (-1, 0), (0, 1), (0, -1))) and rng.random() < 0.55:
                g[y][x] = 7 if rng.random() < 0.5 else 3
    return g, pal, 1


def tex_steel(rng):
    pal = [STEEL[0]] + STEEL[1:] + [VIOLET[1]]
    g = grid(16, 16, 2)
    for y in range(16):
        for x in range(16):
            if rng.random() < 0.12:
                g[y][x] = 1 if rng.random() < 0.5 else 3
    for x in range(16):
        g[0][x], g[15][x] = 4, 0
    for y in range(16):
        g[y][0], g[y][15] = 4, 0
    for (x, y) in ((2, 2), (13, 2), (2, 13), (13, 13)):
        g[y][x], g[y + 1][x + 1] = 5, 0
    for x in range(4, 12):
        g[8][x] = 1
        g[9][x] = 3
    return g, pal, 0


def tex_plate(rng):
    pal = [STEEL[0], STEEL[1], STEEL[2], STEEL[3], STEEL[4], VIOLET[0], VIOLET[1], (12, 12, 16), STEEL[5]]
    g = grid(16, 16, 2)
    for y in range(16):
        for x in range(16):
            if rng.random() < 0.10:
                g[y][x] = 3
    for x in range(16):
        g[0][x], g[15][x] = 4, 1
    for y in range(16):
        g[y][0], g[y][15] = 4, 1
    c = 7.5
    for y in range(16):
        for x in range(16):
            r = math.hypot(x - c, y - c)
            if 5.2 <= r < 6.4:
                g[y][x] = 7              # the black-sun ring stencil
            elif 3.4 <= r < 4.2:
                g[y][x] = 1              # socket rim
            elif r < 3.4:
                g[y][x] = 5 if r > 1.6 else 6   # the socket, a dim violet core
    return g, pal, 0


def tex_scaff():
    pal = [TRANSP, STEEL[1], STEEL[3], STEEL[4], STEEL[5], YELLOW[0], YELLOW[1], (40, 40, 44)]
    g = grid(16, 32)
    for y in range(32):              # poles at the edges
        g[y][0], g[y][1] = 2, 3
        g[y][14], g[y][15] = 3, 1
    for y0 in (0, 15, 30):           # ledgers
        for x in range(16):
            g[y0][x] = 4
            if y0 + 1 < 32:
                g[y0 + 1][x] = 2
        for x in (0, 1, 14, 15):     # yellow couplers
            g[y0][x] = 6
            if y0 + 1 < 32:
                g[y0 + 1][x] = 5
    for i in range(2, 14):           # cross braces in both bays
        for y in (1 + i, 16 + i):
            g[y][i] = 3
            g[y][i + 1 if i < 14 else i] = 1
    return g, pal, 1


def tex_plank(rng):
    pal = WOOD + [(50, 32, 18)]
    g = grid(16, 16)
    for y in range(16):
        board = y // 4
        for x in range(16):
            v = 2 + (board % 2)
            if rng.random() < 0.2:
                v = 1 if rng.random() < 0.5 else 4
            g[y][x] = v
        if y % 4 == 3:
            for x in range(16):
                g[y][x] = 5
    for y in range(16):
        for x in (3, 12):
            if y % 4 in (1,):
                g[y][x] = 0
    return g, pal, 0


def tex_lamp():
    pal = [TRANSP, (40, 36, 30), YELLOW[0], YELLOW[1], YELLOW[2], YELLOW[3], (255, 255, 255), STEEL[1]]
    g = grid(16, 16)
    for y in range(2, 14):
        for x in range(1, 15):
            g[y][x] = 2 if (x in (1, 14) or y in (2, 13)) else 3
    for y in range(4, 12):
        for x in range(3, 13):
            r = math.hypot(x - 7.5, y - 7.5)
            g[y][x] = 6 if r < 2.2 else (5 if r < 3.6 else 4)
    for x in range(1, 15):
        g[13][x] = 1
    g[14][7] = g[14][8] = g[15][7] = g[15][8] = 7
    return g, pal, 1


def tex_crate(rng):
    pal = WOOD + [(40, 26, 14), STEEL[2]]
    g = grid(16, 16)
    for y in range(16):
        for x in range(16):
            g[y][x] = 2 + ((y // 3) % 2)
            if rng.random() < 0.15:
                g[y][x] = 1
    for i in range(16):
        g[0][i] = g[i][0] = 4
        g[15][i] = g[i][15] = 5
        g[1][i] = g[i][1] = 3
    for i in range(2, 14):            # diagonal brace
        g[i][i] = 4
        g[i][min(15, i + 1)] = 1
    for (x, y) in ((1, 1), (14, 1), (1, 14), (14, 14)):
        g[y][x] = 6
    return g, pal, 0


def tex_tunnel(rng):
    pal = [TRANSP, (4, 4, 6), (14, 12, 12), (28, 24, 20), SAND[0], SAND[1], SAND[2], SAND[3], SAND[4], SAND[5],
           SAND[6], (40, 30, 18)]
    g = grid(32, 32)
    cx, cy = 15.5, 17.0
    for y in range(32):
        for x in range(32):
            # an irregular arch: wider at the bottom (the floor is v=1, the wall top v=0)
            rx = 12.5 + 1.8 * math.sin(y * 0.7 + 1.3) + (y - 4) * 0.08
            ry = 15.0
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            n = rng.random()
            if d < 0.45:
                g[y][x] = 1
            elif d < 0.62:
                g[y][x] = 2 if n < 0.7 else 1
            elif d < 0.78:
                g[y][x] = 3 if n < 0.6 else 2
            elif d < 1.05 + 0.12 * n:
                g[y][x] = 4 + int(n * 7)        # broken sandstone rim
                if rng.random() < 0.15:
                    g[y][x] = 11
    return g, pal, 1


def tex_rubble(rng):
    pal = [TRANSP] + SAND + [(30, 22, 14)]
    g = grid(16, 16)
    stones = []
    while len(stones) < 7:
        x0, y0, r = rng.randrange(2, 14), rng.randrange(2, 13), rng.choice((1, 1, 1, 2, 2))
        if all(math.hypot(x0 - a, y0 - b) > r + c + 1.5 for a, b, c in stones):
            stones.append((x0, y0, r))
    for x0, y0, r in stones:
        for y in range(y0 - r, y0 + r + 1):
            for x in range(x0 - r, x0 + r + 1):
                if 0 <= x < 16 and 0 <= y < 16 and math.hypot(x - x0, y - y0) <= r + 0.3:
                    lit = (x - x0) + (y - y0) < 0
                    g[y][x] = (6 if lit else 3) + rng.choice((0, 1))
        for x in range(x0 - r, x0 + r + 1):
            if 0 <= x < 16 and y0 + r + 1 < 16 and g[y0 + r + 1][x] == 0:
                g[y0 + r + 1][x] = 8
    return g, pal, 1


def tex_glow():
    """a5i3: (colour index, alpha 0..31) per texel; radial warm pool."""
    pal = [YELLOW[3], YELLOW[2], (255, 214, 140), (255, 196, 110), (240, 170, 90), (220, 150, 80), (200, 130, 70),
           (180, 110, 60)]
    texels = []
    for y in range(32):
        row = []
        for x in range(32):
            r = math.hypot(x - 15.5, y - 15.5) / 15.5
            a = max(0.0, 1.0 - r) ** 0.9
            row.append((min(7, int(r * 8)), int(round(a * 20))))
        texels.append(row)
    return texels, pal


def a5i3_texture(name, texels, pal):
    h, w = len(texels), len(texels[0])
    data = bytes(i | (a << 3) for row in texels for (i, a) in row)
    return (dict(name=name, fmt=6, w=w, h=h, c0=0, data=data),
            dict(name=name + "_pl", colors=[nsbtx.bgr555(c) for c in pal] + [0] * (8 - len(pal)), pltt4=0))


def build_textures():
    rng = random.Random(0x5014CE0)
    out = []
    for name, fn in (("rd_cable", lambda: tex_cable()), ("rd_crack", lambda: tex_crack(rng)),
                     ("rd_steel", lambda: tex_steel(rng)), ("rd_plate", lambda: tex_plate(rng)),
                     ("rd_scaff", lambda: tex_scaff()), ("rd_plank", lambda: tex_plank(rng)),
                     ("rd_lamp", lambda: tex_lamp()), ("rd_crate", lambda: tex_crate(rng)),
                     ("rd_tunnel", lambda: tex_tunnel(rng)), ("rd_rubble", lambda: tex_rubble(rng))):
        g, pal, c0 = fn()
        assert len(pal) <= 16, (name, len(pal))
        assert max(max(r) for r in g) < len(pal), name
        tex, p = C.indexed_texture(name, g, pal, c0=c0)
        out.append((tex, p, g, pal))
    texels, pal = tex_glow()
    tex, p = a5i3_texture("rd_glow", texels, pal)
    out.append((tex, p, texels, pal))
    return out


# name -> (texture, palette, [w, h]) for the chunk builder's materials
def materials():
    return {t["name"]: (t["name"], p["name"], [t["w"], t["h"]]) for t, p, _, _ in build_textures()}


def build_set():
    items = build_textures()
    return C.texset_append(SET_REL, BASE_REV, new_textures=[t for t, _, _, _ in items],
                           new_palettes=[p for _, p, _, _ in items])


def checks(base, out):
    sb, so = nsbtx.parse(base), nsbtx.parse(out)
    res = []
    res.append(("stock texture names and order kept (appended after them)",
                [t["name"] for t in so["textures"][:len(sb["textures"])]] == [t["name"] for t in sb["textures"]]))
    res.append(("stock palette names and order kept",
                [p["name"] for p in so["palettes"][:len(sb["palettes"])]] == [p["name"] for p in sb["palettes"]]))
    for t in so["textures"][len(sb["textures"]):]:
        res.append((f"{t['name']}: {nsbtx.FMT_NAMES[t['fmt']]} {t['w']}x{t['h']}, 16-colour or a5i3",
                    t["fmt"] in (3, 6)))
    vb, vo = nsbtx.vram_usage(sb), nsbtx.vram_usage(so)
    res.append((f"VRAM {sum(vb)} -> {sum(vo)} B (largest stock set 048: {C.VRAM_PROVEN})", sum(vo) <= C.VRAM_PROVEN))
    return res


def preview(d, items):
    os.makedirs(d, exist_ok=True)
    for tex, pal, g, colours in items:
        name = tex["name"]
        if tex["fmt"] == 6:
            px = [[colours[i] + (round(a * 255 / 31),) for (i, a) in row] for row in g]
        else:
            px = [[(0, 0, 0, 0) if (v == 0 and tex["c0"]) else colours[v] + (255,) for v in row] for row in g]
        png.write_rgba(os.path.join(d, name + ".png"), tex["w"], tex["h"], px)
        json.dump({"format": nsbtx.FMT_NAMES[tex["fmt"]], "palette": pal["name"], "c0": tex["c0"],
                   "size": [tex["w"], tex["h"]]}, open(os.path.join(d, name + ".json"), "w"))
    # contact sheet, 6x
    S, pad = 6, 6
    cells = [(t["name"], png.read(os.path.join(d, t["name"] + ".png"))) for t, _, _, _ in items]
    W = sum(im.width * S + pad for _, im in cells) + pad
    H = max(im.height * S for _, im in cells) + 2 * pad
    px = [[(36, 36, 44, 255)] * W for _ in range(H)]
    ox = pad
    for _, im in cells:
        for y in range(im.height * S):
            for x in range(im.width * S):
                p = im.pixels[y // S][x // S]
                bg = (70, 70, 80) if ((x // 6 + y // 6) % 2) else (90, 90, 100)
                a = p[3] / 255
                px[pad + y][ox + x] = tuple(round(p[k] * a + bg[k] * (1 - a)) for k in range(3)) + (255,)
        ox += im.width * S + pad
    png.write_rgba(os.path.join(d, "raid_textures.png"), W, H, px)
    print("preview:", d, "(raid_textures.png, left to right:", ", ".join(n for n, _ in cells) + ")")


def main():
    items = build_textures()
    base, out, rep = build_set()
    print(rep)
    ok = True
    for name, good in checks(base, out):
        print(("PASS " if good else "FAIL ") + name)
        ok &= good
    if "--preview" in sys.argv:
        preview(sys.argv[sys.argv.index("--preview") + 1], items)
    if "--write" in sys.argv:
        assert ok, "refusing to write"
        open(os.path.join(R.ROOT, SET_REL), "wb").write(out)
        print("wrote", SET_REL, len(out), "B")


if __name__ == "__main__":
    main()
