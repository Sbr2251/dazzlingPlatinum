#!/usr/bin/env python3
"""Builds map_data_667/668 (the Arc 1 wall-walk puzzle map) from Distortion World B1F's map_data_602/603.

The terrain model and BDHC are copied unchanged (Phase 0). Only the permissions change: the void tiles along the
chasm lips become walkable so the player can step off the edge; coord events there run the fall script
(res/field/events/events_distortion_world_arc1_seams.json). Tile coordinates below are DW world tiles of the new
map, which sits at DW offset (0,0,0): x 0-31 is map_data_667, x 32-63 is map_data_668.

Usage: python3 tools/distortion_world/build_arc1_seams_map.py [--check]
Then: python3 tools/distortion_world/twarc.py build tools/distortion_world/arc1_seams.json
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import mapdata  # noqa: E402

DATA = os.path.join(ROOT, "res/field/maps/data")
SRC = {667: 602, 668: 603}

# Chasm lips (x0, z0, x1, z1 inclusive), world tiles. Keep in sync with the coord events.
LIPS = [
    (16, 13, 21, 13),   # upper walkway, south edge (toward the briefcase platform)
    (15, 11, 21, 11),   # upper walkway, north edge
    (12, 15, 15, 15),   # jump-on ledge, south edge
]

# Stock B1F floor tiles with no visible terrain (the floor-transition landing zones east of the stepping stones):
# blocked, so the stepping-stone paths are dead ends instead of walks on thin air.
BLOCKS = [
    (29, 12, 31, 12),   # upper stepping stones: the last hop and the invisible landing
    (31, 9, 31, 11),
    (30, 22, 31, 22),   # lower stepping stones: the last hop
    (32, 0, 63, 31),    # all of map_data_668 (invisible landing platforms)
]


def build():
    out = {}
    for dst, src in SRC.items():
        parts = mapdata.unpack(open(os.path.join(DATA, f"map_data_{src}.bin"), "rb").read())
        perm = mapdata.read_permissions(parts["permissions"])
        x_base = 0 if dst == 667 else 32
        for x0, z0, x1, z1 in BLOCKS:
            for z in range(z0, z1 + 1):
                for x in range(x0, x1 + 1):
                    if x_base <= x < x_base + 32:
                        perm[z][x - x_base] |= 0x8000
        for x0, z0, x1, z1 in LIPS:
            for z in range(z0, z1 + 1):
                for x in range(x0, x1 + 1):
                    if x_base <= x < x_base + 32:
                        assert perm[z][x - x_base] & 0x8000, (x, z, "lip tile is not void in the stock map")
                        perm[z][x - x_base] = 0x0000
        parts["permissions"] = mapdata.write_permissions(perm)
        out[dst] = mapdata.pack(parts["permissions"], parts["props"], parts["model"], parts["bdhc"])
    return out


def main():
    out = build()
    check = "--check" in sys.argv
    ok = True
    for dst, data in out.items():
        path = os.path.join(DATA, f"map_data_{dst}.bin")
        same = os.path.exists(path) and open(path, "rb").read() == data
        ok &= same
        if not check:
            open(path, "wb").write(data)
            print(path, "unchanged" if same else "written")
    if check:
        print("OK" if ok else "map_data differs (run without --check)")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
