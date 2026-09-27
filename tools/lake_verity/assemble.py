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

# budgets (see pipeline.md "DS limits"). Hard: the field's per-chunk load buffers and the per-frame polygon count
# (checked on a 16 x 12 tile window, a little more than the camera sees). Soft: stock-like per-chunk density and
# the largest stock texture set.
MODEL_BUFFER = 0xF000
BDHC_BUFFER = 0x9000
WINDOW_POLYS = 1800          # of 2048 per frame; the rest is headroom for sprites, shadows and props
POLY_SOFT = 1000             # stock chunks have 718..977
VRAM_PROVEN = 76416          # largest stock map texture set (048)


def map_path(c):
    return os.path.join(MAPS, f"map_data_{c:03d}.bin")


STOCK_REV = "f0527f80e"     # last commit with the stock Lake Verity chunks (the plan/layout commit)


def stock_file(rel):
    """A repo file as it was at STOCK_REV (read from git), so regenerated files never feed back into the build.
    Falls back to the checked-in file outside a git checkout."""
    try:
        return subprocess.run(["git", "-C", ROOT, "show", f"{STOCK_REV}:{rel}"], check=True,
                              capture_output=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return open(os.path.join(ROOT, rel), "rb").read()


def stock_bytes(c):
    """Stock map_data for chunk c (at STOCK_REV)."""
    return stock_file(f"res/field/maps/data/map_data_{c:03d}.bin")


def stock_texset():
    """Stock texture set 61 (at STOCK_REV)."""
    return stock_file(f"res/field/maps/texture_sets/map_texture_set_{TEXSET_ID:03d}.nsbtx")


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


# field cameras seen on Lake Verity (src/overlay005/field_camera.c, field_camera_zones.c):
# (name, pitch deg below horizontal, distance, vertical half-fov deg, target tiles or None = every walkable tile)
CAMERAS = (
    ("zoomed_in", 54.656982421875, 515.4560546875, 10.458984375, None),
    ("stair_tilt", 44.0, 460.0, 10.458984375, [(x, z) for x in range(21, 27) for z in range(29, 38)]),
)
NEAR, FAR = 150.0, 900.0


def camera_polys(models, cameras=CAMERAS):
    """Per-frame map polygons for the real field cameras: for every walkable target tile, the camera is placed
    behind the player (south, looking north) and the faces that survive the view frustum and back-face culling
    are counted (the DS stores only those in polygon RAM; quads count as one polygon). Sprites and the stock
    props (l_lake) are not included. -> [(camera, worst culled, worst unculled, target (x, z))]."""
    import math
    faces = []   # (cx, cz, [world verts], double_sided)
    for c, model in models.items():
        m = nsbmd.model_to_mesh(model, layout.CHUNKS[c])
        cull = {mt["name"]: mt.get("polygon_attr", {}).get("cull", "back") for mt in m["materials"]}
        for me in m["meshes"]:
            P = [(p[0] * 16.0, 16.0 + p[1] * 16.0, p[2] * 16.0) for p in me["positions"]]
            ds = cull.get(me["material"], "back") != "back"
            for f in me["tris"] + me["quads"]:
                vs = [P[i] for i in f]
                faces.append((sum(v[0] for v in vs) / len(vs) / 16, sum(v[2] for v in vs) / len(vs) / 16, vs, ds))
    buckets = {}
    for fc in faces:
        buckets.setdefault((int(fc[0]) // 4, int(fc[1]) // 4), []).append(fc)
    tiles = layout.tiles()
    walk = [(x, z) for (x, z), (coll, h, kind) in tiles.items() if not coll & 0x8000 and 0 <= x < 64 and 0 <= z < 64]
    out = []
    for name, pitch, dist, fov, targets in cameras:
        sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
        ty, tx = math.tan(math.radians(fov)), math.tan(math.radians(fov)) * 256 / 192
        best = (0, 0, None)
        for (x, z) in (targets or walk):
            if (x, z) not in tiles:
                continue
            h = tiles[(x, z)][1]
            T = ((x + 0.5) * 16, 16 + h * 16, (z + 0.5) * 16)
            E = (T[0], T[1] + dist * sp, T[2] + dist * cp)
            fwd, up = (0.0, -sp, -cp), (0.0, cp, -sp)
            n_all = n_cull = 0
            for bx in range((x - 24) // 4, (x + 24) // 4 + 1):
                for bz in range((z - 28) // 4, (z + 20) // 4 + 1):
                    for fcx, fcz, vs, ds in buckets.get((bx, bz), ()):
                        out_mask = 63
                        for v in vs:
                            d = (v[0] - E[0], v[1] - E[1], v[2] - E[2])
                            zc = d[1] * fwd[1] + d[2] * fwd[2]
                            yc = d[1] * up[1] + d[2] * up[2]
                            xc = d[0]
                            m = (zc < NEAR) | (zc > FAR) << 1 | (yc > zc * ty) << 2 | (yc < -zc * ty) << 3 | \
                                (xc > zc * tx) << 4 | (xc < -zc * tx) << 5
                            out_mask &= m
                        if out_mask:
                            continue
                        n_all += 1
                        if not ds:
                            a, b, c_ = vs[0], vs[1], vs[2]
                            u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
                            w = (c_[0] - a[0], c_[1] - a[1], c_[2] - a[2])
                            nrm = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
                            if nrm[0] * (E[0] - a[0]) + nrm[1] * (E[1] - a[1]) + nrm[2] * (E[2] - a[2]) <= 0:
                                continue
                        n_cull += 1
            if n_cull > best[0]:
                best = (n_cull, n_all, (x, z))
        out.append((name,) + best)
    return out


def check_budgets(stats, window_polys=None, vram=None, camera=None):
    """-> (errors, warnings). errors break the game (buffer overflow, dropped polygons); warnings exceed stock
    precedent only."""
    errors, warnings = [], []
    for s in stats:
        if s["model_bytes"] > MODEL_BUFFER:
            errors.append(f"chunk {s['chunk']}: model {s['model_bytes']} B > 0x{MODEL_BUFFER:x} buffer")
        if s["bdhc_bytes"] > BDHC_BUFFER:
            errors.append(f"chunk {s['chunk']}: BDHC {s['bdhc_bytes']} B > 0x{BDHC_BUFFER:x} buffer")
        if s["polygons"] > POLY_SOFT:
            warnings.append(f"chunk {s['chunk']}: {s['polygons']} polygons > {POLY_SOFT} (stock max 977)")
    if window_polys is not None and window_polys > WINDOW_POLYS:
        (errors if camera is None else warnings).append(f"view window {window_polys} polygons > {WINDOW_POLYS}")
    for name, culled, unculled, at in camera or ():
        if culled > WINDOW_POLYS:
            errors.append(f"camera {name} at {at}: {culled} polygons on screen > {WINDOW_POLYS}")
    if vram is not None and vram > VRAM_PROVEN:
        warnings.append(f"texture set VRAM {vram} B > {VRAM_PROVEN} B (largest stock set)")
    return errors, warnings


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
