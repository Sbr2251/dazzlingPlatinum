#!/usr/bin/env python3
"""Dumps stock interior maps (terrain model, placed props, textures, permission grid) for reference renders.
Standard library only; reads the stock files from git at BASE_REV.

Usage: python3 tools/solaceon_town/interior/dump_stock.py [out_dir] [HEADER ...]
       default out_dir ~/Documents/Solaceon Update/interior/stock; default headers: the references in interior.md
       (HEADER without the MAP_HEADER_ prefix)
Writes <out>/<header>.mesh.json (terrain), <header>_props.mesh.json, textures/ and prints the permission grid.
"""
import json
import os
import re
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
sys.path.insert(0, os.path.join(ROOT, "tools", "coronet_lava"))

import dump_stock  # noqa: E402
import mapdata  # noqa: E402
import narc  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402

BASE_REV = "50482f890"
DEFAULT = ["FOREIGN_BUILDING", "SOLACEON_TOWN_POKEMON_NEWS_PRESS", "TEAM_GALACTIC_ETERNA_BUILDING_1F"]


def git_bytes(rel):
    return subprocess.run(["git", "-C", ROOT, "show", f"{BASE_REV}:{rel}"], capture_output=True, check=True).stdout


def header_fields(name):
    src = git_bytes("include/data/map_headers.h").decode()
    b = re.search(r"\[MAP_HEADER_" + name + r"\] = \{(.*?)\}", src, re.S).group(1)
    return dict(re.findall(r"\.(\w+) = ([^,]+),", b))


def dump(name, out):
    h = header_fields(name)
    area, mx = int(h["areaDataArchiveID"], 0), int(h["mapMatrixID"], 0)
    m = json.loads(git_bytes(f"res/field/maps/matrices/map_matrix_{mx:03d}.json"))
    md = int(m["maps"][0][0].split("_")[1])
    texd = os.path.join(out, "textures")
    os.makedirs(texd, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        def tmp(rel):
            p = os.path.join(td, os.path.basename(rel))
            open(p, "wb").write(git_bytes(rel))
            return p
        ad = narc.read_files(tmp("res/prebuilt/fielddata/areadata/area_data.narc"))[2][area]
        props_id, set_id, _, light = struct.unpack("<4H", ad)
        mpath = tmp(f"res/field/maps/data/map_data_{md:03d}.bin")
        tpath = tmp(f"res/field/maps/texture_sets/map_texture_set_{set_id:03d}.nsbtx")
        bm = narc.read_files(tmp("res/prebuilt/fielddata/build_model/build_model.narc"))[2]
        dump_stock.export_textures(open(tpath, "rb").read(), texd, nsbtx.pairs_from_models([mpath]))
        sec = mapdata.unpack(open(mpath, "rb").read())
    model = nsbmd.parse_bmd(sec["model"])["models"][0]
    json.dump(nsbmd.model_to_mesh(model, (0, 0), name=name), open(os.path.join(out, name + ".mesh.json"), "w"))
    pm = {"name": name + "_props", "origin_tile": [0, 0], "materials": [], "meshes": []}
    props = mapdata.read_props(sec["props"])
    for p in props:
        b = nsbmd.parse_bmd(bm[p["model"]])
        sub = nsbmd.model_to_mesh(b["models"][0], (0, 0), offset=[v / 4096 for v in p["pos"]])
        pm["materials"] += sub["materials"]
        pm["meshes"] += sub["meshes"]
        if b["tex0"]:
            dump_stock.export_textures(b["tex0"], texd, {x["texture"]: x["palette"] for x in b["models"][0]["materials"]})
    json.dump(pm, open(os.path.join(out, name + "_props.mesh.json"), "w"))
    st = nsbmd.model_stats(model)
    g = mapdata.read_permissions(sec["permissions"])
    print(f"== {name}: area {area} (props {props_id}, set {set_id}, light {light}), matrix {mx}, map_data {md}; "
          f"{st['polygons']} polys, model {len(sec['model'])} B, texset {len(open(tpath, 'rb').read()) if False else ''}props "
          f"{[(p['model'], p['pos'][0] / 65536 + 16, p['pos'][1] / 65536, p['pos'][2] / 65536 + 16) for p in props]}")
    rows = [z for z in range(32) if any(g[z][x] != 0x8000 for x in range(32))]
    cols = [x for x in range(32) if any(g[z][x] != 0x8000 for z in range(32))]
    if rows:
        x0, x1 = max(0, cols[0] - 1), min(31, cols[-1] + 1)
        print("    " + " ".join(f"{x:2d}" for x in range(x0, x1 + 1)))
        for z in range(max(0, rows[0] - 1), min(31, rows[-1] + 2)):
            cells = []
            for x in range(x0, x1 + 1):
                v = g[z][x]
                cells.append("##" if v == 0x8000 else (f"{v & 0xff:02x}" if not v & 0x8000 else "#" + f"{v & 0xff:x}"[-1]))
            print(f"{z:3d} " + " ".join(cells))


def main():
    args = sys.argv[1:]
    out = args.pop(0) if args and not args[0].isupper() else os.path.expanduser("~/Documents/Solaceon Update/interior/stock")
    os.makedirs(out, exist_ok=True)
    for name in args or DEFAULT:
        dump(name, out)


if __name__ == "__main__":
    main()
