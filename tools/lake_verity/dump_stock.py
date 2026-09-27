#!/usr/bin/env python3
"""Dumps the stock Lake Verity chunks (537, 538, 540, 541) to the PLAN.md mesh.json format, plus their map props
(the l_lake water plane, build_model 311) and every texture they use, for previews and as the art agent's
reference. Standard library only.

Usage: python3 tools/lake_verity/dump_stock.py [out_dir]
       (default: ~/Documents/Lake Verity Update/pipeline_checks/stock)

Writes out_dir/chunk_NNN.mesh.json (terrain; "positions" absolute tiles, "positions_local" chunk tiles),
out_dir/chunk_NNN_props.mesh.json (props placed at their map position), out_dir/textures/<name>.png + .json
(texture set 61 via the map models' texture->palette bindings, and the props' own TEX0 textures).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "coronet_lava"))

import layout  # noqa: E402
import mapdata  # noqa: E402
import narc  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402
import png  # noqa: E402

ROOT = os.path.join(HERE, "..", "..")
MAPS = os.path.join(ROOT, "res", "field", "maps", "data")
TEXSET = os.path.join(ROOT, "res", "field", "maps", "texture_sets", "map_texture_set_061.nsbtx")
AREA_DATA = os.path.join(ROOT, "res", "prebuilt", "fielddata", "areadata", "area_data.narc")
AREA_BUILD = os.path.join(ROOT, "res", "prebuilt", "fielddata", "areadata", "area_build_model", "area_build.narc")
BUILD_MODEL = os.path.join(ROOT, "res", "prebuilt", "fielddata", "build_model", "build_model.narc")
AREA_ID = 62
USED = (537, 538, 540, 541)


def area_prop_models(area_id=AREA_ID):
    """-> (props archive id, texture set id, [build_model ids of the area's prop list])."""
    import struct
    ad = narc.read_files(AREA_DATA)[2][area_id]
    props_id, texset_id = struct.unpack_from("<2H", ad)
    ab = narc.read_files(AREA_BUILD)[2][props_id]
    n = struct.unpack_from("<H", ab)[0]
    return props_id, texset_id, list(struct.unpack_from("<%dH" % n, ab, 2))


def export_textures(tex_bytes, out_dir, pairs):
    s = nsbtx.parse(tex_bytes)
    pals = {p["name"]: p["colors"] for p in s["palettes"]}
    for t in s["textures"]:
        pn = nsbtx.guess_palette(t["name"], pals, pairs)
        px, idx = nsbtx.decode(t, pals.get(pn))
        png.write_rgba(os.path.join(out_dir, t["name"] + ".png"), t["w"], t["h"], px)
        json.dump({"format": nsbtx.FMT_NAMES[t["fmt"]], "palette": pn, "c0": t["c0"], "size": [t["w"], t["h"]]},
                  open(os.path.join(out_dir, t["name"] + ".json"), "w"))
    return len(s["textures"])


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Documents/Lake Verity Update/pipeline_checks/stock")
    tex_dir = os.path.join(out, "textures")
    os.makedirs(tex_dir, exist_ok=True)
    props_id, texset_id, prop_list = area_prop_models()
    bm_files = narc.read_files(BUILD_MODEL)[2]
    maps = {c: os.path.join(MAPS, f"map_data_{c:03d}.bin") for c in USED}
    n = export_textures(open(TEXSET, "rb").read(), tex_dir, nsbtx.pairs_from_models(maps.values()))
    print(f"area {AREA_ID}: props list {props_id} -> build models {prop_list}, texture set {texset_id} ({n} textures)")
    exported_props = set()
    for c, path in maps.items():
        sec = mapdata.unpack(open(path, "rb").read())
        model = nsbmd.parse_bmd(sec["model"])["models"][0]
        cxz = layout.CHUNKS[c]
        mesh = nsbmd.model_to_mesh(model, cxz, name=f"chunk_{c}")
        json.dump(mesh, open(os.path.join(out, f"chunk_{c}.mesh.json"), "w"))
        props_mesh = {"name": f"chunk_{c}_props", "origin_tile": mesh["origin_tile"], "materials": [], "meshes": [],
                      "props": []}
        for p in mapdata.read_props(sec["props"]):
            # MapProp.modelID is a build_model.narc index (map_prop.c); the area_build list names the models to preload
            bm_id = p["model"]
            bmd = nsbmd.parse_bmd(bm_files[bm_id])
            pm = bmd["models"][0]
            off = [v / 4096 for v in p["pos"]]
            sub = nsbmd.model_to_mesh(pm, cxz, name=pm["name"], offset=off)
            props_mesh["props"].append({"build_model": bm_id, "name": pm["name"], "pos": off, "rot": p["rot"],
                                        "scale": [v / 4096 for v in p["scale"]]})
            names = {m["name"] for m in props_mesh["materials"]}
            props_mesh["materials"] += [m for m in sub["materials"] if m["name"] not in names]
            props_mesh["meshes"] += sub["meshes"]
            if bmd["tex0"] and bm_id not in exported_props:
                exported_props.add(bm_id)
                pairs = {m["texture"]: m["palette"] for m in pm["materials"]}
                export_textures(bmd["tex0"], tex_dir, pairs)   # nsbtx.parse also takes a bare TEX0 block
        json.dump(props_mesh, open(os.path.join(out, f"chunk_{c}_props.mesh.json"), "w"))
        st = nsbmd.model_stats(model)
        print(f"chunk {c}: {len(mesh['meshes'])} meshes, {st['vertices_sent']} verts, {st['polygons']} polys, "
              f"props {[x['name'] for x in props_mesh['props']]}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
