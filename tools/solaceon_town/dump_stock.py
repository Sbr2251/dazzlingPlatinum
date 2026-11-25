#!/usr/bin/env python3
"""Dumps stock Solaceon Town (map_data_072/073) and its neighbours to mesh.json + PNG, for previews and as the
reference for layout.py. Standard library only.

Usage: python3 tools/solaceon_town/dump_stock.py [out_dir] [--report]
       (default out_dir: ~/Documents/Solaceon Update/layout/stock)

Reads everything from git at BASE_REV (50482f890, the stock town with the memorial wall), so it never sees the
graybox. Writes:
  out_dir/chunk_NNN.mesh.json        terrain ("positions" absolute matrix tiles, h = (world y - 16) / 16, so the
                                     overworld ground is h 1.0)
  out_dir/chunk_NNN_props.mesh.json  the chunk's map props (build models), placed
  out_dir/textures/<name>.png/.json  texture set 010 (palettes from the area-0xA chunk bindings) + prop textures
  out_dir/stock.json                 per chunk: permissions [z][x], BDHC height per tile centre, props
--report prints the permissions / heights / props of 072 and 073 and the seam rows of 068 and 074.

Chunks: the 4 x 3 block of matrix 0 around the town, cells x 16..19, z 19..21:
          175 068 176 176       (z 19: 068 = Route 210 South)
          176 072 073 175       (z 20: the town)
          176 074 176 176       (z 21: 074 = Route 209)
"""
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
sys.path.insert(0, os.path.join(ROOT, "tools", "coronet_lava"))
import mapdata  # noqa: E402
import narc  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402
import png  # noqa: E402

BASE_REV = "50482f890"
SET_REL = "res/field/maps/texture_sets/map_texture_set_010.nsbtx"
BUILD_MODEL_REL = "res/prebuilt/fielddata/build_model/build_model.narc"
MATRIX_REL = "res/field/maps/matrices/map_matrix_000.json"
CELLS = [(x, z) for z in (19, 20, 21) for x in (16, 17, 18, 19)]


def git_file(rel, rev=BASE_REV):
    return subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{rel}"], check=True, capture_output=True).stdout


def matrix():
    return json.loads(git_file(MATRIX_REL))


def chunk_at(cell):
    name = matrix()["maps"][cell[1]][cell[0]]
    return int(name[4:]) if name.startswith("MAP_") and name[4:].isdigit() else None


def chunk_bytes(c):
    return git_file(f"res/field/maps/data/map_data_{c:03d}.bin")


def build_models():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".narc") as f:
        f.write(git_file(BUILD_MODEL_REL))
        f.flush()
        return narc.read_files(f.name)[2]


def heights(bdhc_raw, current=32.0):
    b = mapdata.read_bdhc(bdhc_raw)
    out = []
    for lz in range(32):
        row = []
        for lx in range(32):
            h = mapdata.height_at(b, *mapdata.tile_centre(lx, lz), current=round(current * 4096))
            row.append(None if h is None else h / 4096)
        out.append(row)
    return out


def area_pairs():
    """{texture: palette} from every chunk of matrix 0 that uses set 010 textures we might meet (the 4 x 3 block)."""
    out = {}
    for cell in CELLS:
        c = chunk_at(cell)
        if c is None:
            continue
        m = nsbmd.parse_bmd(mapdata.unpack(chunk_bytes(c))["model"])["models"][0]
        for mat in m["materials"]:
            if mat["texture"] and mat["palette"]:
                out.setdefault(mat["texture"], mat["palette"])
    return out


def export_textures(tex_bytes, out_dir, pairs):
    s = nsbtx.parse(tex_bytes)
    pals = {p["name"]: p["colors"] for p in s["palettes"]}
    for t in s["textures"]:
        pn = nsbtx.guess_palette(t["name"], pals, pairs)
        px, _ = nsbtx.decode(t, pals.get(pn))
        png.write_rgba(os.path.join(out_dir, t["name"] + ".png"), t["w"], t["h"], px)
        json.dump({"format": nsbtx.FMT_NAMES[t["fmt"]], "palette": pn, "c0": t["c0"], "size": [t["w"], t["h"]]},
                  open(os.path.join(out_dir, t["name"] + ".json"), "w"))
    return len(s["textures"])


def prop_mesh(bm_files, props, cell, name):
    out = {"name": name, "origin_tile": [cell[0] * 32, cell[1] * 32], "materials": [], "meshes": [], "props": []}
    for p in props:
        bmd = nsbmd.parse_bmd(bm_files[p["model"]])
        pm = bmd["models"][0]
        off = [v / 4096 for v in p["pos"]]
        sub = nsbmd.model_to_mesh(pm, cell, name=pm["name"], offset=off)
        out["props"].append({"build_model": p["model"], "name": pm["name"], "pos": off,
                             "tile": [(off[0] + 256) / 16 + cell[0] * 32, (off[2] + 256) / 16 + cell[1] * 32]})
        names = {m["name"] for m in out["materials"]}
        out["materials"] += [m for m in sub["materials"] if m["name"] not in names]
        out["meshes"] += sub["meshes"]
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = args[0] if args else os.path.expanduser("~/Documents/Solaceon Update/layout/stock")
    tex_dir = os.path.join(out, "textures")
    os.makedirs(tex_dir, exist_ok=True)
    bm_files = build_models()
    n = export_textures(git_file(SET_REL), tex_dir, area_pairs())
    report = {}
    done_props = set()
    for cell in CELLS:
        c = chunk_at(cell)
        if c is None:
            continue
        sec = mapdata.unpack(chunk_bytes(c))
        model = nsbmd.parse_bmd(sec["model"])["models"][0]
        mesh = nsbmd.model_to_mesh(model, cell, name=f"chunk_{c}_{cell[0]}_{cell[1]}")
        json.dump(mesh, open(os.path.join(out, f"chunk_{c:03d}_{cell[0]}_{cell[1]}.mesh.json"), "w"))
        props = mapdata.read_props(sec["props"])
        if props:
            pmesh = prop_mesh(bm_files, props, cell, f"chunk_{c}_props")
            json.dump(pmesh, open(os.path.join(out, f"chunk_{c:03d}_props.mesh.json"), "w"))
            for p in props:
                if p["model"] in done_props:
                    continue
                done_props.add(p["model"])
                bmd = nsbmd.parse_bmd(bm_files[p["model"]])
                if bmd["tex0"]:
                    export_textures(bmd["tex0"], tex_dir,
                                    {m["texture"]: m["palette"] for m in bmd["models"][0]["materials"]})
        st = nsbmd.model_stats(model)
        report[c] = {"cell": cell, "permissions": mapdata.read_permissions(sec["permissions"]),
                     "heights": heights(sec["bdhc"]), "polygons": st["polygons"], "model_bytes": len(sec["model"]),
                     "props": [{"model": p["model"], "name": nsbmd.parse_bmd(bm_files[p["model"]])["models"][0]["name"],
                                "pos": [v / 4096 for v in p["pos"]]} for p in props]}
    json.dump(report, open(os.path.join(out, "stock.json"), "w"))
    print(f"set 010: {n} textures; wrote {out}")
    if "--report" in sys.argv:
        for c in (72, 73):
            r = report[c]
            print(f"chunk {c} cell {r['cell']}: {r['polygons']} polygons, model {r['model_bytes']} B")
            for p in r["props"]:
                x = (p["pos"][0] + 256) / 16 + r["cell"][0] * 32
                z = (p["pos"][2] + 256) / 16 + r["cell"][1] * 32
                print(f"  prop {p['model']:3d} {p['name']:10s} at tile ({x:.2f}, {z:.2f}) y {p['pos'][1]:.2f}")
        for c, lz in ((68, 31), (74, 0)):
            r = report[c]
            row = r["permissions"][lz]
            walk = [r["cell"][0] * 32 + x for x in range(32) if not row[x] & 0x8000]
            print(f"chunk {c} row z {r['cell'][1] * 32 + lz}: walkable x {walk}, heights "
                  f"{sorted({h for h in r['heights'][lz]})}")


if __name__ == "__main__":
    main()
