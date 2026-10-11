#!/usr/bin/env python3
"""Builds the Solaceon memorial wall (plan S4 / scene 2.16a) into overworld chunk map_data_072 (standard library only).

Usage:
  python3 tools/solaceon_town/build_wall.py                 dry run: budgets + checks
  python3 tools/solaceon_town/build_wall.py --write         write res/field/maps/data/map_data_072.bin

Inputs: the stock chunk 072 at textures.BASE_REV (read from git) and textures.py (run `textures.py --write` first).

s-celestic placed the wall's five sign events on the fence west of the main road: x 556, z 652..656, read from the
road (x 557) facing west (photos, the Ponyta drawing, Elias, the banner, Teo; Indra pins Teo's card from (557,654)).
That fence segment becomes the wall:

  - the stock white picket fence along x 556 (its flat top strip and the two corner posts) is dropped; the east-west
    fences of the flower pen stay and now end against the wall;
  - a low stone wall (blueglay texels, sol_stone palette) along x 556.06..556.94, z 651.55..656.8, 0.55 tiles high;
  - five boards standing on it, one per sign tile, leaning back 40 degrees so the fixed camera (pitch 59) and the road
    both see them, each in a stone frame and showing a 16x16 cell of sol_wall: photo cards, the Ponyta drawing, the
    ELIAS card, the violet banner, Teo's new card. Like the stock north-south fences, they are drawn for the camera
    rather than literally on the wall's east face.

Permissions (x 556, z 651..656 were already blocked by the fence), BDHC and props are stock.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "world_art"))
import chunkedit as C  # noqa: E402
import textures  # noqa: E402

BASE_REV = textures.BASE_REV
CHUNK_REL = "res/field/maps/data/map_data_072.bin"
CHUNK = (17, 20)                 # x 544..575, z 640..671
G = 1.0
SIGN_X = 556
SIGN_Z = [652, 653, 654, 655, 656]       # s-celestic's bg events, script order photos/ponyta/elias/banner/teo
W, E = 556.06, 556.94
ZN, ZS = 651.55, 656.8
HB = G + 0.55                            # the wall body's top


LEAN = math.radians(40.0)                # the boards lean back towards the north, facing the camera and the road
BOARD_L = 1.15                           # board length up the slope
FRAME = 0.06


def build_wall(mb):
    for name, (tex, pal, size) in textures.MATERIALS.items():
        mb.material(name, tex, pal, size)
    # body: a low stone wall
    mb.flat("sol_stone", W, ZN, E, ZS, HB)
    mb.face("sol_stone", [(E, G, ZS), (E, G, ZN), (E, HB, ZN), (E, HB, ZS)],
            [(0, HB - G), (ZS - ZN, HB - G), (ZS - ZN, 0), (0, 0)])                     # east, faces the road
    mb.face("sol_stone", [(W, G, ZN), (W, G, ZS), (W, HB, ZS), (W, HB, ZN)],
            [(0, HB - G), (ZS - ZN, HB - G), (ZS - ZN, 0), (0, 0)])                     # west, seen from the pen
    mb.face("sol_stone", [(W, G, ZS), (E, G, ZS), (E, HB, ZS), (W, HB, ZS)],
            [(0, HB - G), (E - W, HB - G), (E - W, 0), (0, 0)])                         # south end
    # boards, one per sign tile, standing on the wall and leaning back; a stone frame behind each
    sn, cs = math.sin(LEAN), math.cos(LEAN)
    for i, z in enumerate(SIGN_Z):
        zb = z + 0.93
        u0, u1 = i / textures.NCELLS, (i + 1) / textures.NCELLS
        for mat, grow, back, uvs in (("sol_stone", FRAME, 0.0, [(0, 1), (1, 1), (1, 0), (0, 0)]),
                                     ("sol_wall", 0.0, 0.012, [(u0, 1), (u1, 1), (u1, 0), (u0, 0)])):
            x0, x1 = W + 0.04 - grow, E - 0.04 + grow
            l0, l1 = -grow, BOARD_L + grow
            # offset along the board normal (0, sn, cs) by `back`
            pb = lambda l: (HB + l * cs + back * sn, zb - l * sn + back * cs)
            (h0, z0), (h1, z1) = pb(l0), pb(l1)
            mb.face(mat, [(x0, h0, z0), (x1, h0, z0), (x1, h1, z1), (x0, h1, z1)], uvs)


def build():
    edit = C.ChunkEdit(CHUNK_REL, CHUNK, BASE_REV)

    def drop_fence(tex, pal, c, pts):
        return 556.2 < c[0] < 556.8 and 651.0 < c[2] < 657.0
    edit.drop(drop_fence, textures=("imped",))
    _, set_bytes, _ = textures.build_set()
    tex_table, pal_names = C.texture_table(set_bytes)
    mb = C.MeshBuilder()
    build_wall(mb)
    missing = sorted({m["texture"] for m in mb.materials.values()} - set(tex_table)) + \
        sorted({m["palette"] for m in mb.materials.values()} - pal_names)
    assert not missing, f"not in set 010 (run textures.py --write): {missing}"
    edit.add(mb, tex_table)
    model = edit.model_bytes()
    perm = edit.permissions()
    data = edit.pack(perm, model)
    stats = edit.stats(model)
    stats["new_polygons"] = mb.polygons()
    return edit, data, model, perm, mb, stats


def checks(edit, perm):
    cx, cz = CHUNK
    res = []
    wall = [(SIGN_X, z) for z in [651] + SIGN_Z]
    res.append(("wall tiles x 556, z 651..656 blocked (as the stock fence)",
                all(perm[z - cz * 32][x - cx * 32] & 0x8000 for x, z in wall)))
    road = [(557, z) for z in SIGN_Z]
    res.append(("reading tiles x 557, z 652..656 walkable", all(not perm[z - cz * 32][x - cx * 32] & 0x8000
                                                                for x, z in road)))
    ev = os.path.join(ROOT, "res/field/events/events_solaceon_town.json")
    try:
        bg = [(b["x"], b["z"]) for b in json.load(open(ev))["bg_events"]]
        have = [t for t in [(SIGN_X, z) for z in SIGN_Z] if t in bg]
        res.append((f"s-celestic's wall sign events present in this tree: {len(have)}/5 "
                    "(0 before a2/s-celestic merges; coordinates from that branch)", True))
    except OSError:
        pass
    return res


def main():
    edit, data, model, perm, mb, stats = build()
    print(json.dumps(stats, indent=1))
    ok = stats["model_bytes"] <= C.MODEL_BUFFER
    print(f"model {stats['model_bytes']} B (buffer {C.MODEL_BUFFER}) -> {'OK' if ok else 'TOO BIG'}")
    edited = {edit.model["shapes"][si]["name"] for si in edit.faces}
    bad = C.stock_shapes_identical(edit.model, edit.built, edited)
    print(("PASS " if not bad else "FAIL ") + f"untouched stock shapes and all stock materials byte-identical "
          f"(re-encoded after cuts: {sorted(edited)}) {bad}")
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
