#!/usr/bin/env python3
"""Dump the stock Route 216/217 chunks (map_data_106..112 at git HEAD~ base) for planning: permissions (behaviour
codes, '#' blocked), BDHC heights (tiles) per tile centre, props, materials and section sizes.

Usage: python3 tools/routes/r216_217/dump_stock.py [chunk ...]
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import mapdata  # noqa: E402
import nsbmd  # noqa: E402

BASE_REV = "406c75f6a8"
CELLS = {106: (9, 8), 107: (9, 9), 108: (9, 10), 109: (9, 11), 110: (9, 12), 111: (10, 12), 112: (11, 12)}


def stock(c):
    raw = subprocess.run(["git", "-C", ROOT, "show", f"{BASE_REV}:res/field/mapmodels/data/map_data_{c:03d}.bin"],
                         check=True, capture_output=True).stdout
    return mapdata.unpack(raw)


def main():
    chunks = [int(a) for a in sys.argv[1:]] or sorted(CELLS)
    for c in chunks:
        cx, cz = CELLS[c]
        s = stock(c)
        perm = mapdata.read_permissions(s["permissions"])
        b = mapdata.read_bdhc(s["bdhc"])
        m = nsbmd.parse_bmd(s["model"])["models"][0]
        print(f"===== map_data_{c} cell {CELLS[c]} x {cx*32}..{cx*32+31} z {cz*32}..{cz*32+31} model {len(s['model'])} "
              f"bdhc {len(s['bdhc'])} props {len(s['props'])//48} plates {len(b['plates'])}")
        print("materials:", [(mt["name"], mt["texture"], mt["palette"]) for mt in m["materials"]])
        for p in mapdata.read_props(s["props"]):
            print("  prop", p["model"], [round(v / 4096 / 16 + 16, 2) for v in p["pos"]], p["rot"])
        print("     " + "".join(f"{(cx*32+x)%100:3d}" for x in range(32)))
        for z in range(32):
            row = []
            for x in range(32):
                v = perm[z][x]
                beh = v & 0xFF
                row.append(("#" if v & 0x8000 else " ") + (f"{beh:02x}" if beh else ". "))
            print(f"{cz*32+z:4d} " + "".join(row))
        print("heights (tiles):")
        for z in range(32):
            row = []
            for x in range(32):
                h = mapdata.height_at(b, *mapdata.tile_centre(x, z))
                row.append("  ?" if h is None else f"{h/4096/16:3.0f}" if abs(h/4096/16 - round(h/4096/16)) < .01 else f"{h/4096/16:3.1f}"[-3:])
            print(f"{cz*32+z:4d} " + "".join(row))


if __name__ == "__main__":
    main()
