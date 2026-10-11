#!/usr/bin/env python3
"""Builds the Veilstone Meteor Shrine (bible: NEEDS DESIGN; plan 2.17b) into overworld chunk map_data_080.

Usage:
  python3 tools/veilstone_city/build_shrine.py                 dry run: budgets + checks
  python3 tools/veilstone_city/build_shrine.py --write         write res/field/maps/data/map_data_080.bin

Inputs: the stock chunk 080 at textures.BASE_REV (read from git) and textures.py (run `textures.py --write` first).

The stock meteorite garden is three sunken pits east of the Veilstone plaza (A x 727..731 z 614..618, B x 730..733
z 621..624, the big pit C x 728..735 z 626..633, its steps at x 731..732 z 632..633). s-veilstone stages Maylene's
Key Stone trial (2.17b) on the grass between them (Maylene 728,625; the stone box 729,625; Cyrus 731,619) and keeps the
stock meteorite bg events (729,616) (731,622) (730,629) (732,628). Nothing here touches those tiles.

The shrine frame, all on tiles that are already blocked (permissions, BDHC and props stay stock):
  - a vermilion torii over the top of pit C's steps (posts on the rim tiles 730,633 and 733,633; walk-through height
    2.85), with a black cap, a straw shimenawa rope and three paper shide;
  - a stone lantern either side (729,633) (734,633), the fire box lit warm and unlit by the area light so it glows at
    night;
  - straw ropes with shide on short wooden posts along the north rims of all three pits, so each meteorite sits in a
    roped, consecrated frame.
No stock face is removed.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "world_art"))
import chunkedit as C  # noqa: E402
import textures  # noqa: E402

BASE_REV = textures.BASE_REV
CHUNK_REL = "res/field/maps/data/map_data_080.bin"
CHUNK = (22, 19)                 # x 704..735, z 608..639
G = 0.0                          # Veilstone's ground is h 0 (world y 16)

TORII_Z = (633.71, 633.99)       # post depth
TORII_POSTS = (730.65, 733.35)
LANTERNS = ((729.55, 633.6), (734.45, 633.6))
ROPES = [  # (posts x..., z): north rims of pits A, B, C
    ((728.25, 730.75), 614.35),
    ((730.45, 732.75), 621.35),
    ((729.3, 731.95, 734.6), 626.65),
]
# every tile something stands on (all must be blocked in stock)
STANDS = [(730, 633), (733, 633), (729, 633), (734, 633), (728, 614), (730, 614), (730, 621), (732, 621),
          (729, 626), (731, 626), (734, 626)]


def box(mb, mat, x0, x1, h0, h1, z0, z1, faces="sewt", stretch=True):
    """Axis-aligned box; draws the faces the fixed camera can see (s = south, e = east, w = west, t = top).
    stretch: each face maps the whole texture once (a bordered panel); else 1 repeat per tile."""
    def uv(w, h):
        return [(0, 1), (1, 1), (1, 0), (0, 0)] if stretch else [(0, h), (w, h), (w, 0), (0, 0)]
    if "s" in faces:
        mb.face(mat, [(x0, h0, z1), (x1, h0, z1), (x1, h1, z1), (x0, h1, z1)], uv(x1 - x0, h1 - h0))
    if "e" in faces:
        mb.face(mat, [(x1, h0, z1), (x1, h0, z0), (x1, h1, z0), (x1, h1, z1)], uv(z1 - z0, h1 - h0))
    if "w" in faces:
        mb.face(mat, [(x0, h0, z0), (x0, h0, z1), (x0, h1, z1), (x0, h1, z0)], uv(z1 - z0, h1 - h0))
    if "t" in faces:
        mb.face(mat, [(x0, h1, z1), (x1, h1, z1), (x1, h1, z0), (x0, h1, z0)], uv(x1 - x0, z1 - z0))


def rope(mb, xs, z, h_end, sag, thick, shide_every=None, shide_size=(0.16, 0.36)):
    """A sagging straw rope through the points xs at depth z, facing south, with paper streamers below it."""
    v0, v1 = textures.STRAW_V
    for a, b in zip(xs, xs[1:]):
        n = 4
        pts = []
        for k in range(n + 1):
            t = k / n
            x = a + (b - a) * t
            pts.append((x, h_end - sag * 4 * t * (1 - t)))
        for (xa, ha), (xb, hb) in zip(pts, pts[1:]):
            ua, ub = (xa - xs[0]) * 2, (xb - xs[0]) * 2     # 2 repeats per tile, kept small (DS UV range)
            mb.face("vs_straw", [(xa, ha - thick / 2, z), (xb, hb - thick / 2, z), (xb, hb + thick / 2, z),
                                 (xa, ha + thick / 2, z)], [(ua, v1), (ub, v1), (ub, v0), (ua, v0)])
        if shide_every:
            span = b - a
            k = max(1, round(span / shide_every))
            for i in range(k):
                t = (i + 0.5) / k
                x = a + span * t
                h = h_end - sag * 4 * t * (1 - t) - thick / 2 + 0.02
                w, ln = shide_size
                mb.face("vs_shide", [(x - w / 2, h - ln, z + 0.01), (x + w / 2, h - ln, z + 0.01),
                                     (x + w / 2, h, z + 0.01), (x - w / 2, h, z + 0.01)],
                        [(0, 1), (1, 1), (1, 0), (0, 0)])


def lantern(mb, cx, cz):
    def sq(mat, half, h0, h1, faces="sewt"):
        box(mb, mat, cx - half, cx + half, h0, h1, cz - half, cz + half, faces)
    sq("vs_stone", 0.34, G - 0.4, G + 0.22)
    sq("vs_stone", 0.13, G + 0.22, G + 1.0, "sew")
    sq("vs_stone", 0.3, G + 1.0, G + 1.12)
    # fire box: the window of c07_base_x (u 0.25..0.75, v 0.375..0.69) fills each visible face, unlit (glows)
    a, h0, h1 = 0.24, G + 1.12, G + 1.6
    win = [(0.25, 0.69), (0.75, 0.69), (0.75, 0.375), (0.25, 0.375)]
    mb.face("vs_glow", [(cx - a, h0, cz + a), (cx + a, h0, cz + a), (cx + a, h1, cz + a), (cx - a, h1, cz + a)], win)
    mb.face("vs_glow", [(cx + a, h0, cz + a), (cx + a, h0, cz - a), (cx + a, h1, cz - a), (cx + a, h1, cz + a)], win)
    mb.face("vs_glow", [(cx - a, h0, cz - a), (cx - a, h0, cz + a), (cx - a, h1, cz + a), (cx - a, h1, cz - a)], win)
    sq("vs_stone", 0.38, G + 1.6, G + 1.72, "sew")
    # roof: a low pyramid
    a, ap = 0.38, (cx, G + 1.98, cz)
    h = G + 1.72
    mb.face("vs_stone", [(cx - a, h, cz + a), (cx + a, h, cz + a), ap], [(0, 1), (1, 1), (0.5, 0)])
    mb.face("vs_stone", [(cx + a, h, cz + a), (cx + a, h, cz - a), ap], [(0, 1), (1, 1), (0.5, 0)])
    mb.face("vs_stone", [(cx - a, h, cz - a), (cx - a, h, cz + a), ap], [(0, 1), (1, 1), (0.5, 0)])


def build_shrine(mb):
    for name, (tex, pal, size) in textures.MATERIALS.items():
        mb.material(name, tex, pal, size, lights=0 if name == "vs_glow" else 1)
    z0, z1 = TORII_Z
    # torii
    for x in TORII_POSTS:
        box(mb, "vs_red", x - 0.14, x + 0.14, G - 0.6, G + 3.5, z0, z1, "sew")
    box(mb, "vs_red", 730.15, 733.85, G + 2.85, G + 3.1, z0 + 0.04, z1 - 0.04)          # nuki (tie beam)
    box(mb, "vs_red", 731.86, 732.14, G + 3.1, G + 3.45, z0 + 0.07, z1 - 0.07, "sew")   # gakuzuka (strut)
    box(mb, "vs_red", 729.8, 734.2, G + 3.45, G + 3.84, z0 - 0.04, z1 + 0.04, "sew")    # kasagi (lintel)
    box(mb, "vs_black", 729.68, 734.32, G + 3.84, G + 3.94, z0 - 0.02, z1 + 0.02)       # black cap
    rope(mb, [TORII_POSTS[0] + 0.14, TORII_POSTS[1] - 0.14], z1 + 0.02, G + 2.72, 0.18, 0.17,
         shide_every=0.75, shide_size=(0.2, 0.42))
    for cx, cz in LANTERNS:
        lantern(mb, cx, cz)
    # roped frames on the pit rims
    for xs, z in ROPES:
        for x in xs:
            box(mb, "vs_wood", x - 0.07, x + 0.07, G - 0.3, G + 1.12, z - 0.07, z + 0.07)
        rope(mb, [xs[0] + 0.07] + list(xs[1:-1]) + [xs[-1] - 0.07], z + 0.09, G + 1.0, 0.14, 0.16,
             shide_every=0.85, shide_size=(0.2, 0.42))


def build():
    edit = C.ChunkEdit(CHUNK_REL, CHUNK, BASE_REV)
    _, set_bytes, _ = textures.build_set()
    tex_table, pal_names = C.texture_table(set_bytes)
    mb = C.MeshBuilder()
    build_shrine(mb)
    missing = sorted({m["texture"] for m in mb.materials.values()} - set(tex_table)) + \
        sorted({m["palette"] for m in mb.materials.values()} - pal_names)
    assert not missing, f"not in set 011 (run textures.py --write): {missing}"
    edit.add(mb, tex_table)
    model = edit.model_bytes()
    perm = edit.permissions()
    data = edit.pack(perm, model)
    stats = edit.stats(model)
    stats["new_polygons"] = mb.polygons()
    return edit, data, model, perm, mb, stats


def checks(edit, perm):
    cx, cz = CHUNK
    res = [("everything stands on tiles that are blocked in stock",
            all(perm[z - cz * 32][x - cx * 32] & 0x8000 for x, z in STANDS))]
    walk = [(731, 633), (732, 633), (731, 632), (732, 632), (731, 634), (728, 625), (729, 625), (731, 619),
            (727, 625)]
    res.append(("the torii walk-through (pit C steps), the trial tiles and Cyrus's spot stay walkable",
                all(not perm[z - cz * 32][x - cx * 32] & 0x8000 for x, z in walk)))
    ev = json.load(open(os.path.join(ROOT, "res/field/events/events_veilstone_city.json")))
    occ = {(o["x"], o["z"]) for o in ev["object_events"]} | {(b["x"], b["z"]) for b in ev["bg_events"]}
    res.append(("no object or bg event on a tile the shrine stands on", not (occ & set(STANDS))))
    return res


def main():
    edit, data, model, perm, mb, stats = build()
    print(json.dumps(stats, indent=1))
    ok = stats["model_bytes"] <= C.MODEL_BUFFER
    print(f"model {stats['model_bytes']} B (buffer {C.MODEL_BUFFER}) -> {'OK' if ok else 'TOO BIG'}")
    bad = C.stock_shapes_identical(edit.model, edit.built, set())
    print(("PASS " if not bad else "FAIL ") + f"every stock shape and material byte-identical {bad}")
    ok &= not bad
    for name, good in checks(edit, perm):
        print(("PASS " if good else "FAIL ") + name)
        ok &= good
    print(f"permissions identical to stock: {perm == edit.permissions()}")
    if "--write" in sys.argv:
        assert ok, "refusing to write"
        open(os.path.join(ROOT, CHUNK_REL), "wb").write(data)
        print("wrote", CHUNK_REL, len(data), "B")


if __name__ == "__main__":
    main()
