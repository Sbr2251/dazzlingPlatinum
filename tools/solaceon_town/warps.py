#!/usr/bin/env python3
"""Moves the Solaceon Town warps to the door tiles of layout.py (standard library only).

Usage:
  python3 tools/solaceon_town/warps.py            dry run: the warp table, old -> new
  python3 tools/solaceon_town/warps.py --write    rewrite warp_events in layout.EVENTS_JSON

Only warp_events change, and only their x / z: entries are never added, deleted or reordered (interiors return by
warp index) and dest_header_id / dest_warp_id stay as they are. Warp 2 (the News Press) becomes the Sanctuary hall
door; the lead points its destination at the new interior. Everything else in the file is left byte for byte (the
file is re-serialised only if that reproduces it exactly; otherwise the tool refuses).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout  # noqa: E402

PATH = os.path.join(layout.ROOT, layout.EVENTS_JSON)


def main():
    raw = open(PATH).read()
    d = json.loads(raw)
    if json.dumps(d, indent=4) + "\n" != raw:
        print("refusing: the events file does not round-trip through json.dumps(indent=4)")
        return 1
    warps = d["warp_events"]
    assert len(warps) == len(layout.DOORS), (len(warps), len(layout.DOORS))
    print(f"{'#':>2}  {'old':>10}  {'new':>10}  destination / what")
    for i, w in enumerate(warps):
        (x, z), what = layout.DOORS[i]
        old = (w["x"], w["z"])
        print(f"{i:>2}  {str(old):>10}  {str((x, z)):>10}  {w['dest_header_id']} warp {w['dest_warp_id']} -- {what}"
              + ("" if old != (x, z) else "  (unchanged)"))
        w["x"], w["z"] = x, z
    t = layout.tiles()
    for i, w in enumerate(warps):
        v = t[(w["x"], w["z"])][0]
        assert v in (layout.DOOR, layout.CAVE), f"warp {i} not on a door tile: {v:#x}"
    if "--write" in sys.argv:
        out = json.dumps(d, indent=4) + "\n"
        assert out.encode("ascii")
        open(PATH, "w").write(out)
        print("wrote", layout.EVENTS_JSON)
    return 0


if __name__ == "__main__":
    sys.exit(main())
