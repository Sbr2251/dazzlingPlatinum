#!/usr/bin/env python3
"""Builds the land data of rift-b's three Arc 2 Distortion World maps (Phase 0, docs/arc2/PLAN.md D8).

  DW_ROUTE_214  matrix 293 [[673, 674], [672, 615]]  DW B4F (stock 612-615): 673 = 612, 674 = 613, 672 = 614, edited
  DW_ROUTE_213  matrix 294 [[675, 676], [672, 615]]  the same B4F floor: built by build_dw_route_213.py (set-lake)
  DW_LOST_TOWER matrix 295 [[677, 678]]              the Arc 1 seams floor (DW B1F clone, map_data 667/668)

B4F gives the floor -> east wall -> ceiling hops (the wall at x=49, the ceiling at y=10 over x 44-49, z 25-47);
the B1F clone gives the west-wall seam. The terrain models and BDHC are copied unchanged; only permissions change.
Tile coordinates below are map tiles (the maps sit at DW offset (0,0,0), so map tiles = DW world tiles).
615 is referenced unchanged. 614 was too, but its jump tiles hop onto B4F's dropped walkways (B4F_PLAIN): its
edited copy is map_data_672.

Usage: python3 tools/distortion_world/build_rift_b_maps.py [--check]
Then:  python3 tools/distortion_world/twarc.py build tools/distortion_world/{route_214,route_213,lost_tower}.json
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import mapdata  # noqa: E402

DATA = os.path.join(ROOT, "res/field/maps/data")
MATRICES = os.path.join(ROOT, "res/field/maps/matrices")
BLOCKED = 0x8000

# B4F edits, shared by both B4F maps. (x0, z0, x1, z1) inclusive.
B4F_OPEN = [
    (16, 12, 20, 12),   # entry (20,12), the contract tile, out west through the trees to the island's maze
]
B4F_BLOCK = [
    (33, 20, 37, 25),   # the pool: no Surf prompt in the DW; the hop crosses it
]
# fix2-lost (owner playtest round 2): stock B4F's floating-rock walkways are ghost props, and rift-b dropped B4F's
# ghost props, so the walkways are not drawn any more, but B4F's jump-twice tiles still hop the player onto them:
# from the island's south edge (20..24,23) down onto (20..24,26), from (20..22,38) down onto (20..22,41), from
# (15,43..46) east onto (18,43..46), and back. The player stood on thin air (Route 214's walkway tiles are even
# walkable; Route 213's are blocked, but a jump ignores the landing tile's block bit). These tiles become plain
# blocked: no behaviour, so no jump. Applied last, after B4F_BLOCK / B4F_OPEN. The rows z >= 32 lie in B4F's stock
# chunk 614, shared with DW Eterna Forest's matrix: the fixed copy is map_data_672 (registered by R0 for DW Eterna
# Forest, which never used it: matrix 292 shows the stock 613/614/615).
B4F_PLAIN = [
    (20, 24, 24, 25),   # the hops between the island's south edge (z 23) and the walkway (z 26)
    (20, 26, 24, 30),   # the dropped walkway south of the island
    (20, 31, 22, 32),   # the hops between the walkway (z 30) and the floor south of it (z 33)
    (20, 39, 22, 40),   # the hops from (20..22,38) south onto the dropped walkway (z 41)
    (18, 41, 23, 46),   # the dropped walkway in the south-west
    (16, 43, 17, 46),   # the hops from (15,43..46) east onto it
]

# Lost Tower (Arc 1 seams floor) edits: the same lips stay walkable for the fall script (copied from 667/668).
LOST_TOWER_OPEN = [
    # set-tower (S7): the second visit goes deeper than the shadow wall. Lapras lifts the stones (23..32, 22): B1F's
    # own hop chain, ending on (32,22) in the east block; Skarmory carries the player from there to Cyrus's island
    # (a floating-platform ghost prop at (39,22), tools/distortion_world/lost_tower.json).
    (32, 22, 32, 22),   # the last stone
    (37, 21, 41, 23),   # the island
]
LOST_TOWER_BLOCK = [
    (15, 24, 15, 26),   # the arm south of the vein room: the wall of shadow at (16,23) must close the only way deeper
]

MAPS = {
    # name: (matrix id, matrix name, {dst: (src, x_base, z_base)}, open, block, plain, matrix rows)
    "route_214": (293, "m_dwa2_3", {673: (612, 0, 0), 674: (613, 32, 0), 672: (614, 0, 32)}, B4F_OPEN, B4F_BLOCK,
                  B4F_PLAIN, [["MAP_673", "MAP_674"], ["MAP_672", "MAP_615"]]),
    # route_213 (matrix 294, map_data_675/676) is built by build_dw_route_213.py (set-lake: the Drowned Lake
    # dressing on top of this same B4F base, B4F_OPEN / B4F_BLOCK / B4F_PLAIN included; it shares 672)
    "lost_tower": (295, "m_dwa2_5", {677: (667, 0, 0), 678: (668, 32, 0)}, LOST_TOWER_OPEN, LOST_TOWER_BLOCK,
                   [], [["MAP_677", "MAP_678"]]),
}


def build_block(src, x_base, z_base, open_, block, plain=()):
    parts = mapdata.unpack(open(os.path.join(DATA, f"map_data_{src}.bin"), "rb").read())
    perm = mapdata.read_permissions(parts["permissions"])
    for rects, fn in ((block, lambda v: v | BLOCKED), (open_, lambda v: 0), (plain, lambda v: BLOCKED)):
        for x0, z0, x1, z1 in rects:
            for z in range(z0, z1 + 1):
                for x in range(x0, x1 + 1):
                    if x_base <= x < x_base + 32 and z_base <= z < z_base + 32:
                        perm[z - z_base][x - x_base] = fn(perm[z - z_base][x - x_base])
    parts["permissions"] = mapdata.write_permissions(perm)
    return mapdata.pack(parts["permissions"], parts["props"], parts["model"], parts["bdhc"])


def outputs():
    out = {}
    for name, (mid, mname, blocks, open_, block, plain, rows) in MAPS.items():
        for dst, (src, xb, zb) in blocks.items():
            out[os.path.join(DATA, f"map_data_{dst}.bin")] = build_block(src, xb, zb, open_, block, plain)
        out[os.path.join(MATRICES, f"map_matrix_{mid}.json")] = (json.dumps(
            {"name": mname, "headers": [], "altitudes": [], "maps": rows}, indent=4) + "\n").encode()
    return out


def main():
    check = "--check" in sys.argv
    ok = True
    for path, data in outputs().items():
        same = os.path.exists(path) and open(path, "rb").read() == data
        ok &= same
        if not check and not same:
            open(path, "wb").write(data)
            print(path, "written")
    if check:
        print("OK" if ok else "differs (run without --check)")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
