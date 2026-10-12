#!/usr/bin/env python3
"""Builds the land data of DW Ravaged Path (MAP_HEADER_DW_RAVAGED_PATH, matrix 291, map_data_669/670).

The map is the Arc 1 seams floor (map_data_667/668, built by build_arc1_seams_map.py from DW B1F). The terrain
model and BDHC are copied unchanged; only permissions change, so the walkable tiles match what the model draws
(owner playtest round 2, fix2-dwrp):

- In Arc 1, Barry stood at (21,12), east of the entry, and closed the walkway's east end. Ravaged Path has no
  Barry, so the player could walk right off the entry: the stepping stones (25,12) and (28,12) are drawn (ghost
  props), but B1F's hop tiles (29..30,12) then jumped the player to (31,12), where nothing is drawn (an invisible
  ledge). The hop tiles past the last stone lose their jump behaviour and stay blocked, so (28,12) is a dead end.
  The same for the lower chain's last hop (30..31,22), which jumps into the all-blocked 670 block.

Tile coordinates are DW world tiles (the map sits at DW offset (0,0,0)): x 0-31 is 669, x 32-63 is 670.

Usage: python3 tools/distortion_world/build_ravaged_path_map.py [--check]
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import mapdata  # noqa: E402

DATA = os.path.join(ROOT, "res/field/maps/data")
SRC = {669: 667, 670: 668}
BLOCKED = 0x8000

# (x0, z0, x1, z1) inclusive: set to plain blocked (no tile behaviour).
BLOCK = [
    (29, 12, 30, 12),   # the hop off the last upper stepping stone (28,12) onto the undrawn (31,12)
    (30, 22, 31, 22),   # the hop off the last lower stepping stone (29,22) into the 670 block
]


def build():
    out = {}
    for dst, src in SRC.items():
        parts = mapdata.unpack(open(os.path.join(DATA, f"map_data_{src}.bin"), "rb").read())
        perm = mapdata.read_permissions(parts["permissions"])
        x_base = 0 if dst == 669 else 32
        for x0, z0, x1, z1 in BLOCK:
            for z in range(z0, z1 + 1):
                for x in range(x0, x1 + 1):
                    if x_base <= x < x_base + 32:
                        perm[z][x - x_base] = BLOCKED
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
