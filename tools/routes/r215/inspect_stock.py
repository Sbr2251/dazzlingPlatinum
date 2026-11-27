#!/usr/bin/env python3
"""Route 215 stock inspection: permissions / BDHC heights / textures of map_data_069..071 (read from git BASE_REV)
plus the route's events, as ASCII maps. Standard library only.

Usage:
  python3 tools/routes/r215/inspect_stock.py [perm|height|tex|events|all]
"""
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as R  # noqa: E402


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    stock = R.stock_chunks()
    perm = R.merged_permissions(stock)
    hts = R.merged_heights(stock)
    ev = R.stock_events()
    marks = R.event_marks(ev)
    if what in ("perm", "all"):
        beh = Counter()
        print("permissions (# blocked, . walk, ~ water(0x15/0x10), g grass 0x02, other = low byte hex digit); "
              "events overlaid")
        print("      " + "".join(str((x // 10) % 10) for x in R.XS))
        print("      " + "".join(str(x % 10) for x in R.XS))
        for z in R.ZS:
            row = []
            for x in R.XS:
                p = perm[(x, z)]
                beh[(p & 0xFF, bool(p & 0x8000))] += 1
                row.append(marks.get((x, z)) or R.perm_char(p))
            print(f"{z:4d}  " + "".join(row))
        print("behaviours:", sorted(((hex(b), bl), n) for (b, bl), n in beh.items()))
    if what in ("height", "all"):
        print("BDHC height at tile centres (tiles, h=0 -> world y 0; ground 2.0 = y 32): digit = round(h*2) - 2*2")
        for z in R.ZS:
            row = []
            for x in R.XS:
                h = hts[(x, z)]
                row.append("?" if h is None else R.hchar(h))
            print(f"{z:4d}  " + "".join(row))
        print("legend: '0' = y 32 (ground), each step = 8 world units (half tile); '-' below, '?' none")
    if what in ("tex", "all"):
        for c, d in stock.items():
            edit = d["edit"]
            cnt = Counter()
            boxes = defaultdict(lambda: [1e9, 1e9, -1e9, -1e9, 1e9, -1e9])
            for si, tex, pal in edit.iter_shapes():
                tris, quads = edit._faces(si)
                for f in tris + quads:
                    pts = [edit.tile(v["pos"]) for v in f]
                    cnt[(tex, pal)] += 1
                    b = boxes[(tex, pal)]
                    for p in pts:
                        b[0], b[1] = min(b[0], p[0]), min(b[1], p[2])
                        b[2], b[3] = max(b[2], p[0]), max(b[3], p[2])
                        b[4], b[5] = min(b[4], p[1]), max(b[5], p[1])
            edit.faces.clear()
            print(f"map_data_{c:03d}: {len(edit.model['shapes'])} shapes, {len(edit.model['materials'])} materials, "
                  f"model {len(d['sec']['model'])} B, bdhc {len(d['sec']['bdhc'])} B")
            for (tex, pal), n in sorted(cnt.items(), key=lambda kv: -kv[1]):
                b = boxes[(tex, pal)]
                print(f"   {tex:14s} {pal:14s} {n:4d} faces  x {b[0]:.1f}..{b[2]:.1f} z {b[1]:.1f}..{b[3]:.1f} "
                      f"h {b[4]:.2f}..{b[5]:.2f}")
    if what in ("events", "all"):
        for k in ("bg_events", "object_events", "warp_events", "coord_events"):
            for o in ev[k]:
                print(k, o.get("id", o.get("script")), o["x"], o["z"], o.get("script", ""))


if __name__ == "__main__":
    main()
