#!/usr/bin/env python3
"""Builds the land data of rift-b's three Arc 2 Distortion World maps (Phase 0, docs/arc2/PLAN.md D8).

  DW_ROUTE_214  matrix 293 [[673, 674], [614, 615]]  DW B4F (stock 612-615): 673 = 612, 674 = 613, both edited
  DW_ROUTE_213  matrix 294 [[675, 676], [614, 615]]  the same B4F floor: built by build_dw_route_213.py (set-lake)
  DW_LOST_TOWER matrix 295 [[677, 678]]              the Arc 1 seams floor (DW B1F clone, map_data 667/668)

B4F gives the floor -> east wall -> ceiling hops (the wall at x=49, the ceiling at y=10 over x 44-49, z 25-47);
the B1F clone gives the west-wall seam. The terrain models and BDHC are copied unchanged; only permissions change.
Tile coordinates below are map tiles (the maps sit at DW offset (0,0,0), so map tiles = DW world tiles).
The 614/615 halves of B4F are referenced unchanged (nothing walkable there is reachable).

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

# Lost Tower (Arc 1 seams floor) edits: the same lips stay walkable for the fall script (copied from 667/668).
LOST_TOWER_OPEN = []
LOST_TOWER_BLOCK = [
    (15, 24, 15, 26),   # the arm south of the vein room: the wall of shadow at (16,23) must close the only way deeper
]

MAPS = {
    # name: (matrix id, matrix name, {dst: (src, x_base, z_base)}, open, block, matrix rows)
    "route_214": (293, "m_dwa2_3", {673: (612, 0, 0), 674: (613, 32, 0)}, B4F_OPEN, B4F_BLOCK,
                  [["MAP_673", "MAP_674"], ["MAP_614", "MAP_615"]]),
    # route_213 (matrix 294, map_data_675/676) is built by build_dw_route_213.py (set-lake: the Drowned Lake
    # dressing on top of this same B4F base, B4F_OPEN / B4F_BLOCK included)
    "lost_tower": (295, "m_dwa2_5", {677: (667, 0, 0), 678: (668, 32, 0)}, LOST_TOWER_OPEN, LOST_TOWER_BLOCK,
                   [["MAP_677", "MAP_678"]]),
}


def build_block(src, x_base, z_base, open_, block):
    parts = mapdata.unpack(open(os.path.join(DATA, f"map_data_{src}.bin"), "rb").read())
    perm = mapdata.read_permissions(parts["permissions"])
    for rects, fn in ((block, lambda v: v | BLOCKED), (open_, lambda v: 0)):
        for x0, z0, x1, z1 in rects:
            for z in range(z0, z1 + 1):
                for x in range(x0, x1 + 1):
                    if x_base <= x < x_base + 32 and z_base <= z < z_base + 32:
                        perm[z - z_base][x - x_base] = fn(perm[z - z_base][x - x_base])
    parts["permissions"] = mapdata.write_permissions(perm)
    return mapdata.pack(parts["permissions"], parts["props"], parts["model"], parts["bdhc"])


def outputs():
    out = {}
    for name, (mid, mname, blocks, open_, block, rows) in MAPS.items():
        for dst, (src, xb, zb) in blocks.items():
            out[os.path.join(DATA, f"map_data_{dst}.bin")] = build_block(src, xb, zb, open_, block)
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
