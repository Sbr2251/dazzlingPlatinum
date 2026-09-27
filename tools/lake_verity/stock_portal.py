#!/usr/bin/env python3
"""Gives Lake Verity the stock Distortion World portal (build model 581, d5_ana_pl) from distorted Spear Pillar.

Usage: python3 tools/lake_verity/stock_portal.py [--write] [--preview DIR]
(standard library only; without --write it only checks). --preview writes DIR/portal_581.mesh.json (the prop as
placed by build_art.py, node transforms applied, animation at rest) and DIR/tex/g_demo_ana*.png for
blender_preview.py.

The portal is a stock map prop. In distorted Spear Pillar (area 0x3C = props list 56, set 59) it sits in
map_data_379, and bm_anime_list[581] gives it the looping 240-frame BCA0 bm_anime 80, which spins its four
outer discs. Nothing in C or in a script is needed: the field loads the prop and its animation with the area.

Area 62 (props list 58) is shared with Sendoff Spring and both Lake Valor maps, so the portal is not added to it.
This tool writes a Lake-Verity-only copy instead, following the Mt. Coronet (0x4B) and castle interior (0x4C)
precedent:

  area_build.narc   entry 71 = stock list 58 (311 l_lake, 72 bomb_mark, 74 l_lake_l4) + 581
  areabm_texset.narc entry 71 = stock texset 58 (l_lake, bomb_mark) + g_demo_ana1..4 and their palettes, copied
                     byte for byte from stock texset 56. The four palettes are appended contiguously in stock order
                     (ana1 16 B, ana2 64 B, ana3 32 B, ana4 16 B): ana1/ana4 are a3i5 with short palettes, so they
                     must be followed by the same bytes as in stock. (Their texels only use indices 0..5 and 0..1,
                     so they never actually read past their own palette.)
  area_data.narc    entry 77 (0x4D) = (props list 71, texture set 61, 0, light 0), i.e. area 62 with the new list

MAP_HEADER_LAKE_VERITY.areaDataArchiveID in include/data/map_headers.h must be 0x4D (checked here, not edited).
The prop record itself (model 581 on the launchpad) is written into chunk 538 by build_art.py.
Re-running rewrites the same entries.
"""

import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "coronet_lava"))
import narc  # noqa: E402
import nsbtx  # noqa: E402

ROOT = os.path.join(HERE, "..", "..")
AREADATA = os.path.join(ROOT, "res", "prebuilt", "fielddata", "areadata")
AREA_DATA = os.path.join(AREADATA, "area_data.narc")
AREA_BUILD = os.path.join(AREADATA, "area_build_model", "area_build.narc")
AREABM_TEXSET = os.path.join(AREADATA, "area_build_model", "areabm_texset.narc")
MAP_HEADERS = os.path.join(ROOT, "include", "data", "map_headers.h")

PORTAL_MODEL = 581           # d5_ana_pl, the Distortion World portal of distorted Spear Pillar
PORTAL_TEXSET = 56           # areabm_texset of distorted Spear Pillar (area 0x3C), holds the g_demo_ana textures
PORTAL_TEXTURES = ["g_demo_ana1", "g_demo_ana2", "g_demo_ana3", "g_demo_ana4"]
BASE_AREA = 62               # the shared lake area: props list 58, set 61, light 0
BASE_PROPS = 58
NEW_PROPS = 71               # first free area_build / areabm_texset index (stock has 0..70)
AREA_ID = 0x4D               # first free area_data index (0x4C is the castle interior)


def props_entry(files):
    base = files[BASE_PROPS]
    n = struct.unpack_from("<H", base)[0]
    ids = list(struct.unpack_from("<%dH" % n, base, 2))
    assert ids == [311, 72, 74], f"stock props list {BASE_PROPS} changed: {ids}"
    ids.append(PORTAL_MODEL)
    return struct.pack("<%dH" % (len(ids) + 1), len(ids), *ids)


def texset_entry(files):
    base, src = nsbtx.parse(files[BASE_PROPS]), nsbtx.parse(files[PORTAL_TEXSET])
    texs = {t["name"]: t for t in src["textures"]}
    pals = {p["name"]: p for p in src["palettes"]}
    new_t = [dict(texs[n]) for n in PORTAL_TEXTURES]
    new_p = [dict(pals[n + "_pl"]) for n in PORTAL_TEXTURES]
    # the portal palettes must be contiguous and in stock order (see the docstring)
    offs = [p["off"] for p in new_p]
    assert offs == [offs[0] + sum(len(q["data"]) for q in new_p[:i]) for i in range(4)], offs
    for t in base["textures"] + new_t:
        t.pop("off", None)
    for p in base["palettes"] + new_p:
        p.pop("off", None)
    data = nsbtx.build(base["textures"] + new_t, base["palettes"] + new_p, pal_flag=base["header"]["pal_flag"])
    # verify: same texels and the same palette bytes (incl. what the a3i5 textures read past their own palette)
    out = nsbtx.parse(data)
    otex = {t["name"]: t for t in out["textures"]}
    opal = {p["name"]: p for p in out["palettes"]}
    for t in base["textures"] + new_t:
        assert otex[t["name"]]["data"] == t["data"] and otex[t["name"]]["param"] >> 16 == t["param"] >> 16, t["name"]
    raw_new = data[data.index(b"TEX0"):]
    pal_data = raw_new[struct.unpack_from("<I", raw_new, 0x38)[0]:]
    first = opal[PORTAL_TEXTURES[0] + "_pl"]["off"]
    src_raw = files[PORTAL_TEXSET][files[PORTAL_TEXSET].index(b"TEX0"):]
    src_pal = src_raw[struct.unpack_from("<I", src_raw, 0x38)[0]:]
    span = sum(len(p["data"]) for p in new_p)
    assert pal_data[first:first + span] == src_pal[offs[0]:offs[0] + span], "portal palettes not contiguous"
    return data


# node transforms of model 581 (node data + SBC): node 0 is the core disc; nodes 1-4 are drawn with node 0's matrix
# restored first, so their translations add to node 0's. Node 3 carries a static scale of 0.9. The BCA spins nodes
# 1-4 about y. Shape polygon<i> is drawn under node i.
def node_transforms(model):
    out = []
    for n in model["nodes"]:
        d = bytes.fromhex(n["data"])
        flag = struct.unpack_from("<H", d)[0]
        assert flag & 2, "node rotation not handled"
        t = [v / 4096 for v in struct.unpack_from("<3i", d, 4)] if not flag & 1 else [0.0, 0.0, 0.0]
        sc = struct.unpack_from("<i", d, 16)[0] / 4096 if not flag & 4 else 1.0
        out.append((t, sc))
    base = out[0][0]
    return [out[0]] + [([base[k] + t[k] for k in range(3)], sc) for t, sc in out[1:]]


def write_preview(pdir, texset):
    import json
    import nsbmd
    import png
    import build_art
    bm = narc.read_files(os.path.join(ROOT, "res", "prebuilt", "fielddata", "build_model", "build_model.narc"))[2]
    model = nsbmd.parse_bmd(bm[PORTAL_MODEL])["models"][0]
    mesh = nsbmd.model_to_mesh(model, (0, 0), name=f"portal_{PORTAL_MODEL}")
    xf = node_transforms(model)
    px, py, pz = [v / 4096 for v in build_art.PORTAL_PROP["pos"]]
    cx, cz = (build_art.PORTAL_CHUNK - 537) % 3 * 32, (build_art.PORTAL_CHUNK - 537) // 3 * 32
    for me in mesh["meshes"]:
        (tx, ty, tz), sc = xf[int(me["shape"][len("polygon"):])]
        loc = []
        for x, h, z in me["positions_local"]:
            vx, vy, vz = (x - 16) * 16, h * 16 + 16, (z - 16) * 16            # back to model (world) units
            wx, wy, wz = px + tx + sc * vx, py + ty + sc * vy, pz + tz + sc * vz
            loc.append([wx / 16 + 16, (wy - 16) / 16, wz / 16 + 16])
        me["positions_local"] = loc
        me["positions"] = [[p[0] + cx, p[1], p[2] + cz] for p in loc]
    mesh["origin_tile"] = [cx, cz]
    os.makedirs(os.path.join(pdir, "tex"), exist_ok=True)
    json.dump(mesh, open(os.path.join(pdir, f"portal_{PORTAL_MODEL}.mesh.json"), "w"))
    s = nsbtx.parse(texset)
    pals = {p["name"]: p["colors"] for p in s["palettes"]}
    for t in s["textures"]:
        if t["name"] in PORTAL_TEXTURES:
            img, _ = nsbtx.decode(t, pals[t["name"] + "_pl"])
            png.write_rgba(os.path.join(pdir, "tex", t["name"] + ".png"), t["w"], t["h"], img)
            json.dump({"format": nsbtx.FMT_NAMES[t["fmt"]], "c0": t["c0"]},
                      open(os.path.join(pdir, "tex", t["name"] + ".json"), "w"))
    print(f"wrote {pdir}/portal_{PORTAL_MODEL}.mesh.json and {pdir}/tex/")


def main():
    write = "--write" in sys.argv
    ab_h, ab_b, ab = narc.read_files(AREA_BUILD)
    ts_h, ts_b, ts = narc.read_files(AREABM_TEXSET)
    ad_h, ad_b, ad = narc.read_files(AREA_DATA)
    assert len(ab) == len(ts), (len(ab), len(ts))
    assert len(ab) >= NEW_PROPS and len(ad) >= AREA_ID, "would leave a gap"
    base_area = struct.unpack("<4H", ad[BASE_AREA])
    assert base_area[0] == BASE_PROPS, base_area
    new_ab, new_ts = props_entry(ab), texset_entry(ts)
    new_ad = struct.pack("<4H", NEW_PROPS, base_area[1], 0, base_area[3])
    for files, i, entry in ((ab, NEW_PROPS, new_ab), (ts, NEW_PROPS, new_ts), (ad, AREA_ID, new_ad)):
        if len(files) > i:
            files[i] = entry
        else:
            files.append(entry)
    vram = nsbtx.vram_usage(nsbtx.parse(new_ts))
    print(f"area_build {NEW_PROPS}: {list(struct.unpack_from('<5H', new_ab)[1:])}")
    print(f"areabm_texset {NEW_PROPS}: {len(new_ts)} B, VRAM {vram[0]} texels + {vram[1]} palettes "
          f"(stock 58: {sum(nsbtx.vram_usage(nsbtx.parse(ts[BASE_PROPS])))}, stock 56: "
          f"{sum(nsbtx.vram_usage(nsbtx.parse(ts[PORTAL_TEXSET])))})")
    print(f"area_data 0x{AREA_ID:X}: {struct.unpack('<4H', new_ad)}")
    hdr = open(MAP_HEADERS).read()
    m = re.search(r"\[MAP_HEADER_LAKE_VERITY\] = \{\s*\.areaDataArchiveID = (\w+),", hdr)
    ok = m and int(m.group(1), 0) == AREA_ID
    print(f"MAP_HEADER_LAKE_VERITY.areaDataArchiveID = {m.group(1) if m else '?'}"
          + ("" if ok else f"  <- must be 0x{AREA_ID:X}"))
    if write:
        narc.write_files(AREA_BUILD, ab_h, ab_b, ab)
        narc.write_files(AREABM_TEXSET, ts_h, ts_b, ts)
        narc.write_files(AREA_DATA, ad_h, ad_b, ad)
        print("wrote area_build.narc, areabm_texset.narc, area_data.narc")
    if "--preview" in sys.argv:
        write_preview(sys.argv[sys.argv.index("--preview") + 1], new_ts)


if __name__ == "__main__":
    main()
