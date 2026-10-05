#!/usr/bin/env python3
"""Distortion World tw_arc / tw_arc_attr tool (standard library only).

res/prebuilt/fielddata/tornworld/tw_arc.narc
    member 0: s32 count, then count x {u32 mapHeaderID, u16 member index (file = index + 1), s16 offset x, y, z}
              (tile offsets that place each DW map in the shared DW coordinate space, fieldmap.c / ov9_02251094)
    member N: one record per map (src/overlay009/ov9_02249960.c DistWorldFile_Load):
              header {s32 dummy, s32 platform section size, s32 jump section size, s32 camera section size,
                      s32 ghost-prop section size}
              platforms   s32 count + count x 20 B {s16 kind, u16 attrID, bounds(6 x s16), u16 tilesV, u16 tilesH}
              jump points s32 count + count x 40 B (DistWorldFloatingPlatformJumpPointTemplate)
              cameras     s32 count + count x 24 B (DistWorldCameraAngleTemplate)
              ghost props {s32 templateCount, s32 triggerCount, u32 defaultVisibleGroups},
                          templates 12 B {u32 group, u16 propKind, s16 x, y, z}, triggers 20 B
res/prebuilt/fielddata/tornworld/tw_arc_attr.narc
    member N: 32 x 32 u16 wall/ceiling collision grid, index = v + h * 32 (ov9 GetCurrentFloatingPlatformTileAttributes).
              0x8000 = blocked, low byte = tile behaviour.

All coordinates in a record are DW world tiles (map tile + the map's member-0 offset).

Usage:
  twarc.py dump [MAP_HEADER_ID]          print member 0 and the decoded records
  twarc.py build SPEC.json               (re)write the map described by SPEC into both archives (idempotent)
  twarc.py check SPEC.json               verify both archives match SPEC (exit 1 if not)
"""
import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "coronet_lava"))
import narc  # noqa: E402

TW = os.path.join(ROOT, "res/prebuilt/fielddata/tornworld/tw_arc.narc")
ATTR = os.path.join(ROOT, "res/prebuilt/fielddata/tornworld/tw_arc_attr.narc")
MAP_HEADERS = os.path.join(ROOT, "generated/map_headers.txt")

PLAT = struct.Struct("<hH6hHH")
JUMP = struct.Struct("<Hhi6h3hhhHHhhH")
CAM = struct.Struct("<6hHHHhi")
GHOST = struct.Struct("<IH3h")
GHOST_TRIG = struct.Struct("<Ihh6h")
JUMP_KEYS = ("handler", "dir", "dummy", "x", "y", "z", "sx", "sy", "sz", "dx", "dy", "dz", "rot", "steps",
             "unk_1E", "unk_20", "final_dir", "kind", "platform")
PLAT_KEYS = ("kind", "attr", "x", "y", "z", "sx", "sy", "sz", "tiles_v", "tiles_h")
CAM_KEYS = ("x", "y", "z", "sx", "sy", "sz", "ax", "ay", "az", "dir", "steps")


def map_header_id(name):
    with open(MAP_HEADERS) as f:
        names = [line.strip() for line in f if line.strip()]
    return names.index(name)


def _section(rec, o, size, st, keys):
    if size == 0:
        return [], o
    n = struct.unpack_from("<i", rec, o)[0]
    assert size == 4 + n * st.size, (size, n, st.size)
    out = [dict(zip(keys, st.unpack_from(rec, o + 4 + i * st.size))) for i in range(n)]
    return out, o + size


def parse_record(rec):
    dummy, ps, js, cs, gs = struct.unpack_from("<5i", rec, 0)
    o = 20
    plats, o = _section(rec, o, ps, PLAT, PLAT_KEYS)
    jumps, o = _section(rec, o, js, JUMP, JUMP_KEYS)
    cams, o = _section(rec, o, cs, CAM, CAM_KEYS)
    ghost = {"default_visible": 0, "props": [], "triggers": []}
    if gs:
        nt, ntr, dv = struct.unpack_from("<iiI", rec, o)
        ghost["default_visible"] = dv
        q = o + 12
        for i in range(nt):
            g, k, x, y, z = GHOST.unpack_from(rec, q)
            ghost["props"].append({"group": g, "kind": k, "x": x, "y": y, "z": z})
            q += GHOST.size
        for i in range(ntr):
            v = GHOST_TRIG.unpack_from(rec, q)
            ghost["triggers"].append({"group": v[0], "dir": v[1], "show": v[2], "bounds": list(v[3:])})
            q += GHOST_TRIG.size
        assert q == o + gs
        o += gs
    assert o == len(rec), (o, len(rec))
    return {"dummy": dummy, "platforms": plats, "jumps": jumps, "cameras": cams, "ghost": ghost}


def _pack_section(items, st, keys):
    if not items:
        return b""
    return struct.pack("<i", len(items)) + b"".join(st.pack(*[it[k] for k in keys]) for it in items)


def pack_record(r):
    ps = _pack_section(r["platforms"], PLAT, PLAT_KEYS)
    js = _pack_section(r["jumps"], JUMP, JUMP_KEYS)
    cs = _pack_section(r["cameras"], CAM, CAM_KEYS)
    g = r["ghost"]
    gs = b""
    if g["props"] or g["triggers"]:
        gs = struct.pack("<iiI", len(g["props"]), len(g["triggers"]), g["default_visible"])
        gs += b"".join(GHOST.pack(p["group"], p["kind"], p["x"], p["y"], p["z"]) for p in g["props"])
        gs += b"".join(GHOST_TRIG.pack(t["group"], t["dir"], t["show"], *t["bounds"]) for t in g["triggers"])
    return struct.pack("<5i", r.get("dummy", 0), len(ps), len(js), len(cs), len(gs)) + ps + js + cs + gs


def read_index(m0):
    n = struct.unpack_from("<i", m0, 0)[0]
    return [list(struct.unpack_from("<IHhhh", m0, 4 + 12 * i)) for i in range(n)]


def pack_index(entries):
    return struct.pack("<i", len(entries)) + b"".join(struct.pack("<IHhhh", *e) for e in entries)


def grid_from_rows(rows, base=None):
    """rows: list of strings, row v (top first), column h. '#' blocked, '.' walkable (0), or keep base value for ' '."""
    g = list(base) if base else [0x8000] * 1024
    for v, row in enumerate(rows):
        for h, c in enumerate(row):
            if c == "#":
                g[v + h * 32] = 0x8000
            elif c in ".*":
                g[v + h * 32] = 0
    return g


def rows_from_grid(g, nv, nh):
    return ["".join("#" if g[v + h * 32] & 0x8000 else "." for h in range(nh)) for v in range(nv)]


def shift_record(r, dx, dy, dz):
    for p in r["platforms"]:
        p["x"] += dx; p["y"] += dy; p["z"] += dz
    for j in r["jumps"]:
        j["x"] += dx; j["y"] += dy; j["z"] += dz
    for c in r["cameras"]:
        c["x"] += dx; c["y"] += dy; c["z"] += dz
    for p in r["ghost"]["props"]:
        p["x"] += dx; p["y"] += dy; p["z"] += dz
    for t in r["ghost"]["triggers"]:
        t["bounds"][0] += dx; t["bounds"][1] += dy; t["bounds"][2] += dz


def spec_outputs(spec):
    """-> (map id, offset, record bytes, {attr id: grid bytes})"""
    hdr, btnf, tw = narc.read_files(TW)
    ahdr, abtnf, attr = narc.read_files(ATTR)
    index = read_index(tw[0])
    src_id = map_header_id(spec["clone_from"])
    src = next(e for e in index if e[0] == src_id)
    rec = parse_record(tw[src[1] + 1])
    off = spec["offset"]
    shift_record(rec, off[0] - src[2], off[1] - src[3], off[2] - src[4])
    attrs = {}
    for k, p in enumerate(rec["platforms"]):
        ps = spec["platforms"][k] if k < len(spec.get("platforms", [])) else {}
        new_attr = ps.get("attr", p["attr"])
        base = list(struct.unpack("<1024H", attr[p["attr"]])) if p["attr"] < len(attr) else None
        if new_attr != p["attr"] and new_attr < len(attr) and new_attr not in spec.get("attr_ids", []):
            raise SystemExit(f"attr id {new_attr} is a stock member")
        for key in ("x", "y", "z", "sx", "sy", "sz"):
            if key in ps:
                p[key] = ps[key]
        g = grid_from_rows(ps["rows"], base) if "rows" in ps else base
        p["attr"] = new_attr
        attrs[new_attr] = struct.pack("<1024H", *g)
    if "jumps" in spec:
        rec["jumps"] = [dict(zip(JUMP_KEYS, [j.get(k, 0) for k in JUMP_KEYS])) for j in spec["jumps"]]
    if "cameras" in spec:
        rec["cameras"] = [dict(zip(CAM_KEYS, [c.get(k, 0) for k in CAM_KEYS])) for c in spec["cameras"]]
    if spec.get("ghost_props") is not None:
        rec["ghost"]["props"] = spec["ghost_props"]
    rec["ghost"]["props"] += spec.get("extra_ghost_props", [])
    return map_header_id(spec["map"]), off, pack_record(rec), attrs


def build(spec_path, write=True):
    spec = json.load(open(spec_path))
    mid, off, rec, attrs = spec_outputs(spec)
    hdr, btnf, tw = narc.read_files(TW)
    ahdr, abtnf, attr = narc.read_files(ATTR)
    index = read_index(tw[0])
    entry = next((e for e in index if e[0] == mid), None)
    if entry is None:
        member = len(tw) - 1          # new member index (file = index + 1)
        index.append([mid, member, *off])
        tw.append(rec)
    else:
        entry[2:5] = off
        tw[entry[1] + 1] = rec
    changed = tw[0] != pack_index(index)
    tw[0] = pack_index(index)
    ok = not changed
    for aid, data in attrs.items():
        if aid < len(attr):
            ok &= attr[aid] == data
            attr[aid] = data
        else:
            assert aid == len(attr), f"attr id {aid} would leave a gap (archive has {len(attr)})"
            attr.append(data)
            ok = False
    old_tw = open(TW, "rb").read()
    if write:
        narc.write_files(TW, hdr, btnf, tw)
        narc.write_files(ATTR, ahdr, abtnf, attr)
        print(f"map {spec['map']} = {mid}: tw_arc member {next(e for e in index if e[0] == mid)[1] + 1}, "
              f"offset {off}, attr {sorted(attrs)}; tw_arc {'unchanged' if open(TW, 'rb').read() == old_tw else 'updated'}")
    return ok


def dump(only=None):
    hdr, btnf, tw = narc.read_files(TW)
    ahdr, abtnf, attr = narc.read_files(ATTR)
    for e in read_index(tw[0]):
        if only is not None and e[0] != only:
            continue
        print("map", e[0], "member", e[1] + 1, "offset", e[2:])
        r = parse_record(tw[e[1] + 1])
        for p in r["platforms"]:
            print("  platform", p)
            g = struct.unpack("<1024H", attr[p["attr"]])
            for row in rows_from_grid(g, p["sy"] + 1 if p["kind"] in (1, 2) else p["sx"] + 1, p["sz"] + 1):
                print("     ", row)
        for j in r["jumps"]:
            print("  jump", j)
        for c in r["cameras"]:
            print("  camera", c)
        print("  ghost props", len(r["ghost"]["props"]), "triggers", len(r["ghost"]["triggers"]))
    print("attr members", len(attr))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "dump":
        dump(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    elif cmd == "build":
        build(sys.argv[2])
    elif cmd == "check":
        ok = build(sys.argv[2], write=False)
        print("OK" if ok else "archives differ from spec (run build)")
        sys.exit(0 if ok else 1)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
