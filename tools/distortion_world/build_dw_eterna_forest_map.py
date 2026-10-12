#!/usr/bin/env python3
"""Builds the entry-walkway block of DW Eterna Forest (MAP_HEADER_DW_ETERNA_FOREST, matrix 292, map_data_671).

The map is a hybrid (rift-a): chunk (0,0) is the Arc 1 seams floor (map_data_667, built by build_arc1_seams_map.py
from DW B1F), chunks (1,0)/(0,1)/(1,1) are stock DW B4F (613/614/615). 671 was a plain copy of 667, so it kept the
edges that only made sense in Arc 1 (owner playtest round 2; the same faults fix2-dwrp fixed in DW Ravaged Path,
build_ravaged_path_map.py). The model and BDHC are copied unchanged; only the permissions change (fix2-lost):

- False falls: the chasm-lip rows next to the walkway fall (coord events, DWEternaForest_Fall), but some lip tiles
  are drawn ground: (16..19,13) is the floor under the two trees south of the walkway and (16..18,11) the rock
  block north of it. They are plain blocked again, as in stock B1F. The open-void lips stay walkable and fall:
  (15,11), (19..21,11), (20..21,13). Keep in sync with res/field/events/events_dw_eterna_forest.json.
- Invisible stepping stones: east of the walkway, B1F's jump-twice tiles (23..24, 26..27, 29..30, z=12) hop the
  player from (22,12) to (25,12), (28,12) and (31,12). In Ravaged Path and the Lost Tower ghost props draw stones on
  (25,12) and (28,12), but this map's tw_arc record is B4F's (tools/distortion_world/eterna_forest.json), so nothing
  is drawn on any of them: the player walked on thin air. The whole chain (23..30,12) is plain blocked, so the
  walkway ends at its last drawn tile (22,12). (A jump ignores the landing tile's block bit, so blocking only the
  landings is not enough: the jump tiles themselves lose their behaviour.)
- The lower chain (21..31,22) is the same, undrawn: unreachable on foot (it lies past the B4F pool, which needs
  Surf, and behind the wall seam, which this map does not have), but its first hop from the pool's west bank
  (32,22) would land on nothing. Plain blocked too.

Tile coordinates are DW world tiles (the map sits at DW offset (0,0,0)); 671 is x 0-31, z 0-31.

Usage: python3 tools/distortion_world/build_dw_eterna_forest_map.py [--check]
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import mapdata  # noqa: E402

DATA = os.path.join(ROOT, "res/field/maps/data")
SRC = {671: 667}
BLOCKED = 0x8000

# (x0, z0, x1, z1) inclusive: set to plain blocked (no tile behaviour).
BLOCK = [
    (16, 13, 19, 13),   # drawn ground under the two trees south of the walkway (was a falling lip)
    (16, 11, 18, 11),   # the drawn rock block north of the walkway (was a falling lip)
    (23, 12, 30, 12),   # B1F's upper hop chain east of the walkway: no stones drawn in this map
    (21, 22, 31, 22),   # B1F's lower hop chain: no stones drawn either
]


def build():
    out = {}
    for dst, src in SRC.items():
        parts = mapdata.unpack(open(os.path.join(DATA, f"map_data_{src}.bin"), "rb").read())
        perm = mapdata.read_permissions(parts["permissions"])
        for x0, z0, x1, z1 in BLOCK:
            for z in range(z0, z1 + 1):
                for x in range(x0, x1 + 1):
                    perm[z][x] = BLOCKED
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
