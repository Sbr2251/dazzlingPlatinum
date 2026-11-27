#!/usr/bin/env python3
"""Stock report for Routes 206-207 (chunks 025..030 at common.BASE_REV): sizes, materials, props, and an ASCII map of
permissions, events and BDHC heights.

Usage:
  python3 tools/routes/r206_207/stock_report.py [--heights] [--x0 X --x1 X --z0 Z --z1 Z]

Legend: '.' walkable, '"' tall grass, '#' blocked, '~' water, '%' other blocked behaviour, '?' other behaviour,
'=' bridge/deck behaviour (0x70/0x71 Cycling Road), events: W warp, T trainer, i item ball, h hidden item, s sign,
b berry soil, c cut tree, o other object.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as K  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402


def load():
    perm, hgt, secs = {}, {}, {}
    for c, (cx, cz) in K.CHUNKS.items():
        sec = mapdata.unpack(K.git_bytes(K.BASE_REV, K.chunk_rel(c)))
        secs[c] = sec
        P = mapdata.read_permissions(sec["permissions"])
        B = mapdata.read_bdhc(sec["bdhc"])
        for lz in range(32):
            for lx in range(32):
                x, z = cx * 32 + lx, cz * 32 + lz
                perm[(x, z)] = P[lz][lx]
                h = mapdata.height_at(B, *mapdata.tile_centre(lx, lz))
                hgt[(x, z)] = None if h is None else h / 4096 / 16
    return perm, hgt, secs


def events():
    ev = {}
    for r in ("route_206", "route_207"):
        e = json.load(open(os.path.join(K.ROOT, f"res/field/maps/{r}/events.json")))
        for o in e["object_events"]:
            g = o["graphics_id"]
            ev[(o["x"], o["z"])] = ("T" if o.get("trainer") else "i" if "POKEBALL" in g else "s" if "SIGN" in g
                                    else "b" if "BERRY" in g else "c" if "CUT" in g else "o")
        for o in e["warp_events"]:
            ev[(o["x"], o["z"])] = "W"
        for o in e["bg_events"]:
            ev[(o["x"], o["z"])] = "h" if "hidden_item" in o else "B"
    return ev


def sym(perm, ev, x, z):
    if (x, z) in ev:
        return ev[(x, z)]
    v = perm.get((x, z))
    if v is None:
        return " "
    b = v & 0xFF
    if v & K.BLOCK:
        return "#" if b == 0 else "~" if b in (0x15, 0x10) else "%"
    return {0: ".", 2: '"', 0x15: "~", 0x10: "~", 0x70: "=", 0x71: "="}.get(b, "?")


def main():
    a = sys.argv[1:]
    g = lambda k, d: int(a[a.index(k) + 1]) if k in a else d  # noqa: E731
    x0, x1, z0, z1 = g("--x0", 288), g("--x1", 352), g("--z0", 576), g("--z1", 736)
    perm, hgt, secs = load()
    ev = events()
    for c, sec in secs.items():
        m = nsbmd.parse_bmd(sec["model"])["models"][0]
        st = nsbmd.model_stats(m)
        props = mapdata.read_props(sec["props"])
        print(f"MAP_{c:03d} cell {K.CHUNKS[c]} model {len(sec['model'])} B (room {K.MODEL_BUFFER - len(sec['model'])}) "
              f"bdhc {len(sec['bdhc'])} B polys {st['polygons']} props "
              f"{[(p['model'], [round(v / 4096 / 16 + 16, 1) for v in p['pos']]) for p in props]}")
        print("   textures:", sorted({mt["texture"] for mt in m["materials"]}))
    beh = collections.Counter(v & 0xFF for v in perm.values())
    print("behaviours:", sorted((hex(k), n) for k, n in beh.items()))
    print("     " + "".join(str((x // 10) % 10) if x % 10 == 0 else " " for x in range(x0, x1)))
    print("     " + "".join(str(x % 10) for x in range(x0, x1)))
    for z in range(z0, z1):
        row = "".join(sym(perm, ev, x, z) for x in range(x0, x1))
        if "--heights" in a:
            row += "  " + " ".join("  ?" if hgt.get((x, z)) is None else "%3d" % round(hgt[(x, z)])
                                   for x in range(x0, x1, 2))
        print(f"{z:4d} {row}")
    odd = sorted((x, z, hex(v)) for (x, z), v in perm.items() if (v & 0xFF) not in (0, 2, 0x15, 0x70, 0x71)
                 and x0 <= x < x1 and z0 <= z < z1)
    print("special behaviours:", odd)


if __name__ == "__main__":
    main()
