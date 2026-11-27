#!/usr/bin/env python3
"""Route 223 stock survey: permissions, BDHC heights, model materials and props of map_data_092..095 (read from git
HEAD, never the work tree), with the route's events overlaid. Standard library only.

Usage:
  python3 tools/routes/r223/dump_stock.py              permission/height grids + events for all four chunks
  python3 tools/routes/r223/dump_stock.py --models     also list each chunk model's materials and polygon counts

Grid legend (one char per tile): '~' sea (0x15), 'W' waterfall (0x13), 'r' river (0x10), '.' walkable ground,
'#' blocked, 'g' tall grass, 's' sand, 'j' ledge jump, '?' other behaviour; events overlay: S swimmer/trainer,
I item, H hidden item, K Kingdra totem, J Jasmine, B bg event.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "world_art"))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import chunkedit as C  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402

CHUNKS = {92: (26, 19), 93: (26, 20), 94: (26, 21), 95: (26, 22)}
EVENTS = os.path.join(ROOT, "res/field/maps/route_223/events.json")


def ch(v):
    b, blk = v & 0xFF, v & 0x8000
    if b == 0x15:
        return "~"
    if b == 0x13:
        return "W"
    if b == 0x10:
        return "r"
    if 0x38 <= b <= 0x3B:
        return "j"
    if b == 0x02:
        return "g"
    if b == 0x21:
        return "s"
    if blk:
        return "#"
    return "." if b == 0 else "?"


def main():
    ev = json.load(open(EVENTS))
    marks = {}
    for o in ev["object_events"]:
        g = o["graphics_id"]
        c = "K" if "KINGDRA" in g else "J" if "JASMINE" in g else "I" if "POKEBALL" in g else "S"
        marks[(o["x"], o["z"])] = c
    for b in ev["bg_events"]:
        marks[(b["x"], b["z"])] = "H" if "hidden_item" in b else "B"
    for n, (cx, cz) in CHUNKS.items():
        rel = f"res/field/mapmodels/data/map_data_{n:03d}.bin"
        raw = C.git_file("HEAD", rel)
        sec = mapdata.unpack(raw)
        perm = mapdata.read_permissions(sec["permissions"])
        b = mapdata.read_bdhc(sec["bdhc"])
        print(f"== map_data_{n:03d} chunk ({cx},{cz}) x {cx*32}..{cx*32+31} z {cz*32}..{cz*32+31} sizes",
              {k: len(v) for k, v in sec.items()})
        others = sorted({v & 0xFF for r in perm for v in r})
        print("   behaviours:", [hex(v) for v in others])
        print("   props:", [(p["model"], [round(c / 4096 / 16 + 16, 2) for c in p["pos"]]) for p in mapdata.read_props(sec["props"])])
        print("      " + "".join(str((cx * 32 + x) % 10) for x in range(32)) + "   heights (tiles above y0)")
        for z in range(32):
            row = ""
            hs = []
            for x in range(32):
                gx, gz = cx * 32 + x, cz * 32 + z
                row += marks.get((gx, gz), ch(perm[z][x]))
                h = mapdata.height_at(b, *mapdata.tile_centre(x, z))
                hs.append("  ?" if h is None else f"{h / 4096 / 16:3.0f}")
            print(f"  {cz*32+z:3d} {row}  {''.join(hs)}")
        if "--models" in sys.argv:
            m = nsbmd.parse_bmd(sec["model"])["models"][0]
            e = C.ChunkEdit(rel, (cx, cz), "HEAD")
            for si, tex, pal in e.iter_shapes():
                tris, quads = e._faces(si)
                pts = [e.tile(v["pos"]) for f in tris + quads for v in f]
                hs = sorted({round(p[1], 2) for p in pts})
                print(f"   shape {si:2d} {tex:14s} {pal:14s} tris {len(tris):4d} quads {len(quads):4d} "
                      f"h {hs[0] if hs else '-'}..{hs[-1] if hs else '-'}")
            print("   ", nsbmd.model_stats(m))


if __name__ == "__main__":
    main()
