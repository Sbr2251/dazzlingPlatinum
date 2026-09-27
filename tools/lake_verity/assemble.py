#!/usr/bin/env python3
"""Assembles Lake Verity map_data chunks from mesh.json geometry (standard library only).

A chunk is assembled from:
  * the stock terrain, minus the faces inside the redesign footprint (cut_stock);
  * any number of extra meshes in the PLAN.md mesh.json format (absolute tile positions), e.g. the graybox
    (build_graybox.py) or the art agent's tools/lake_verity/assets/*.mesh.json;
  * the stock props (the animated l_lake water plane, build_model 311);
  * permissions and BDHC from layout.py (collision.py).

Textures are referenced by name. They must be in the area's texture set (set 61), or be added to it with
texture_set() before building. See docs/lake_verity_redesign/pipeline.md, "Assembling the art".
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import collision  # noqa: E402
import layout  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402

ROOT = os.path.join(HERE, "..", "..")
MAPS = os.path.join(ROOT, "res", "field", "maps", "data")
MATRICES = os.path.join(ROOT, "res", "field", "maps", "matrices")
TEXSET_ID = 61
TEXSET = os.path.join(ROOT, "res", "field", "maps", "texture_sets", f"map_texture_set_{TEXSET_ID:03d}.nsbtx")
CHUNKS = (537, 538, 540, 541)
AREA62_MATRICES = (60, 101, 102, 104, 105)     # map headers using area 62 (Sendoff Spring, Verity, Valor)
STOCK_KINDS = ("forest", "water", "grass", "ground", "exit")

# budgets (see pipeline.md "DS limits")
MODEL_BUFFER = 0xF000
BDHC_BUFFER = 0x9000
POLY_BUDGET = 1000


def map_path(c):
    return os.path.join(MAPS, f"map_data_{c:03d}.bin")


STOCK_REV = "f0527f80e"     # last commit with the stock Lake Verity chunks (the plan/layout commit)


def stock_bytes(c):
    """Stock map_data for chunk c, read from git (STOCK_REV) so regenerated chunks never feed back into the build.
    Falls back to the checked-in file outside a git checkout."""
    rel = f"res/field/maps/data/map_data_{c:03d}.bin"
    try:
        return subprocess.run(["git", "-C", ROOT, "show", f"{STOCK_REV}:{rel}"], check=True,
                              capture_output=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return open(map_path(c), "rb").read()


def area_texture_pairs():
    """{texture: palette} from every stock map model of the area-62 matrices (so set-61 textures that Lake Verity itself
    does not use still get their stock palette)."""
    chunks = set()
    for mid in AREA62_MATRICES:
        m = json.load(open(os.path.join(MATRICES, f"map_matrix_{mid:03d}.json")))
        for row in m["maps"]:
            for name in row:
                if name.startswith("MAP_") and name[4:].isdigit():
                    chunks.add(int(name[4:]))
    return nsbtx.pairs_from_models([stock_bytes(c) for c in sorted(chunks) if os.path.exists(map_path(c))])


def texture_table(set_bytes=None):
    """{texture name: {"size": [w, h], "palette": name, "format": name, "c0": 0/1}} for the area texture set."""
    s = nsbtx.parse(set_bytes or open(TEXSET, "rb").read())
    pals = {p["name"] for p in s["palettes"]}
    pairs = area_texture_pairs()
    return {t["name"]: {"size": [t["w"], t["h"]], "palette": nsbtx.guess_palette(t["name"], pals, pairs),
                        "format": nsbtx.FMT_NAMES[t["fmt"]], "c0": t["c0"]} for t in s["textures"]}


def footprint():
    """Tiles the redesign replaces: every layout tile whose kind is not a stock kind (island, castle, bridge),
    plus the stock hut."""
    t = layout.tiles()
    out = {k for k, v in t.items() if v[2] not in STOCK_KINDS}
    out |= {(x, z) for x in range(29, 36) for z in range(28, 35)}
    return out


def stock_mesh(c):
    sec = mapdata.unpack(stock_bytes(c))
    model = nsbmd.parse_bmd(sec["model"])["models"][0]
    return nsbmd.model_to_mesh(model, layout.CHUNKS[c], name=model["name"]), sec, model


def cut_mesh(mesh, drop):
    """Removes faces for which drop(list of vertex positions (x, h, z) in absolute tiles) is true."""
    out = dict(mesh, meshes=[])
    for me in mesh["meshes"]:
        P = me["positions"]
        keep_t, keep_q = [], []
        for faces, keep in ((me.get("tris", []), keep_t), (me.get("quads", []), keep_q)):
            for f in faces:
                if not drop([P[i] for i in f]):
                    keep.append(f)
        if keep_t or keep_q:
            out["meshes"].append(dict(me, tris=keep_t, quads=keep_q))
    return out


def _touches(fp, x, z, eps=1e-3):
    """True if the point (x, z) lies in or on the border of a footprint tile."""
    return any((int((x + dx) // 1), int((z + dz) // 1)) in fp for dx in (-eps, eps) for dz in (-eps, eps))


def cut_stock(mesh, fp, keep_under=()):
    """Drops the stock faces the redesign replaces: faces whose centroid tile is in the footprint and that either
    rise above the water surface (hut, shore) or lie entirely inside the footprint (lakebed under the island).
    Lakebed faces that straddle the footprint border are kept (they are hidden under the island top), so no hole
    opens outside the footprint. On keep_under tiles (the bridge) the lakebed is always kept (it shows through
    the water)."""
    keep_under = set(keep_under)

    def drop(pts):
        cx = sum(p[0] for p in pts) / len(pts)
        cz = sum(p[2] for p in pts) / len(pts)
        tile = (int(cx // 1), int(cz // 1))
        if tile not in fp:
            return False
        hmax = max(p[1] for p in pts)
        if hmax <= layout.WATER_H + 1e-3:
            if tile in keep_under:
                return False
            return all(_touches(fp - keep_under, p[0], p[2]) for p in pts)
        return True
    return cut_mesh(mesh, drop)


def merge(meshes, name):
    out = {"name": name, "materials": [], "meshes": []}
    seen = set()
    for m in meshes:
        for mat in m.get("materials", []):
            if mat["name"] not in seen:
                seen.add(mat["name"])
                out["materials"].append(mat)
        out["meshes"] += m["meshes"]
    return out


def split_by_chunk(mesh):
    """Splits a mesh spanning several chunks by face centroid -> {chunk id: mesh}. Faces are not clipped; a face
    near a chunk edge may overhang into the neighbour, which is harmless for drawing."""
    by_xy = {v: k for k, v in layout.CHUNKS.items()}
    out = {}
    for me in mesh["meshes"]:
        P = me["positions"]
        parts = {}
        for key in ("tris", "quads"):
            for f in me.get(key, []):
                cx = int(sum(P[i][0] for i in f) / len(f) // 32)
                cz = int(sum(P[i][2] for i in f) / len(f) // 32)
                parts.setdefault(by_xy[(cx, cz)], {"tris": [], "quads": []})[key].append(f)
        for c, fs in parts.items():
            dst = out.setdefault(c, {"name": f"{mesh['name']}_{c}", "materials": mesh.get("materials", []),
                                     "meshes": []})
            dst["meshes"].append(dict(me, tris=fs["tris"], quads=fs["quads"]))
    return out


def build_chunk(c, extra_meshes, fp, textures, keep_under=(), stock_props=True):
    """-> (map_data bytes, stats dict, model dict)."""
    smesh, sec, smodel = stock_mesh(c)
    kept = cut_stock(smesh, fp, keep_under)
    mesh = merge([kept] + list(extra_meshes), smodel["name"])
    model = nsbmd.mesh_to_model(mesh, layout.CHUNKS[c], name=smodel["name"], textures=textures)
    missing = sorted({m["texture"] for m in model["materials"]} - set(textures))
    assert not missing, f"chunk {c}: textures not in the texture set: {missing}"
    nsb = nsbmd.build_bmd([model])
    bd = collision.bdhc(c)
    perm = collision.permissions(c)
    props = sec["props"] if stock_props else b""
    data = mapdata.pack(perm, props, nsb, bd)
    st = nsbmd.model_stats(model)
    stats = {"chunk": c, "polygons": st["polygons"], "triangles": st["triangles"], "quads": st["quads"],
             "vertices_sent": st["vertices_sent"], "model_bytes": len(nsb), "bdhc_bytes": len(bd),
             "materials": len(model["materials"]), "bdhc_plates": len(mapdata.read_bdhc(bd)["plates"])}
    return data, stats, model


def check_budgets(stats):
    problems = []
    for s in stats:
        if s["model_bytes"] > MODEL_BUFFER:
            problems.append(f"chunk {s['chunk']}: model {s['model_bytes']} > 0x{MODEL_BUFFER:x}")
        if s["bdhc_bytes"] > BDHC_BUFFER:
            problems.append(f"chunk {s['chunk']}: BDHC {s['bdhc_bytes']} > 0x{BDHC_BUFFER:x}")
        if s["polygons"] > POLY_BUDGET:
            problems.append(f"chunk {s['chunk']}: {s['polygons']} polygons > {POLY_BUDGET}")
    return problems


def texture_set(extra_dir=None, base=None):
    """Area texture set with the PNG textures of extra_dir appended (nsbtx.load_texture_dir; stock textures are
    kept so the other area-62 maps still work). -> NSBTX bytes."""
    base = base or open(TEXSET, "rb").read()
    s = nsbtx.parse(base)
    if not extra_dir:
        return base
    tex, pals = nsbtx.load_texture_dir(extra_dir)
    names = {t["name"] for t in s["textures"]}
    clash = [t["name"] for t in tex if t["name"] in names]
    assert not clash, f"texture names already in set {TEXSET_ID}: {clash}"
    return nsbtx.build(s["textures"] + tex, s["palettes"] + pals, pal_flag=s["header"]["pal_flag"])


def props_bytes(props):
    return mapdata.write_props(props)


if __name__ == "__main__":
    t = texture_table()
    for k, v in sorted(t.items()):
        print(f"{k:16s} {v['size'][0]:3d}x{v['size'][1]:<3d} {v['format']:7s} c0={v['c0']} palette {v['palette']}")
