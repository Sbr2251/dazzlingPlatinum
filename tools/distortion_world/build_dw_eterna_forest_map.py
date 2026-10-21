#!/usr/bin/env python3
"""Builds DW Eterna Forest's own land data (MAP_HEADER_DW_ETERNA_FOREST, matrix 292): the entry-walkway block
map_data_671, the honeycomb block map_data_679, and the matrix.

The map is a hybrid (rift-a): chunk (0,0) is the Arc 1 seams floor (map_data_667, built by build_arc1_seams_map.py
from DW B1F), chunks (1,0)/(0,1)/(1,1) are stock DW B4F (613/614/615). 671 was a plain copy of 667, so it kept the
edges that only made sense in Arc 1 (owner playtest round 2; the same faults fix2-dwrp fixed in DW Ravaged Path,
build_ravaged_path_map.py). The model and BDHC are copied unchanged; only the permissions change (fix2-lost):

- False falls: the chasm-lip rows next to the walkway fall (coord events, DWEternaForest_Fall), but some lip tiles
  are drawn ground: (16..19,13) is the floor under the two trees south of the walkway and (16..18,11) the rock
  block north of it. They are plain blocked again, as in stock B1F. The open-void lips stay walkable and fall:
  (15,11), (19..21,11), (20..21,13). Keep in sync with res/field/events/events_dw_eterna_forest.json.
- Invisible stepping stones: east of the walkway, B1F's jump-twice tiles (23..24, 26..27, 29..30, z=12) hop the
  player from (22,12) to (25,12), (28,12) and (31,12). In Ravaged Path and the Lost Tower ghost props draw stones on
  (25,12) and (28,12), but this map's tw_arc record is B4F's (tools/distortion_world/eterna_forest.json), so nothing
  is drawn on any of them: the player walked on thin air. The whole chain (23..30,12) is plain blocked, so the
  walkway ends at its last drawn tile (22,12). (A jump ignores the landing tile's block bit, so blocking only the
  landings is not enough: the jump tiles themselves lose their behaviour.)
- The lower chain (21..31,22) is the same, undrawn: unreachable on foot (it lies past the B4F pool, which needs
  Surf, and behind the wall seam, which this map does not have), but its first hop from the pool's west bank
  (32,22) would land on nothing. Plain blocked too.

Tile coordinates are DW world tiles (the map sits at DW offset (0,0,0)); 671 is x 0-31, z 0-31.

The HONEYCOMB block, map_data_679 (fix2-honey, owner playtest round 2): chunk (1,0) was stock B4F 613. Its ceiling
slab (underside h 11.0 / 11.5, a full top sheet at h 12.1, terraces and rocks on top up to h 16) is what the player
walks under on the ceiling (y=10). The honeycomb (ghost-prop group 1 on the ceiling tiles x 44-45, z 33-36,
tools/distortion_world/eterna_forest.json; Arc2DwEternaForest_HandleFrame in src/overlay009/ov9_02249960.c) fades out
on a timer and the player falls, but the slab stayed drawn round the player's feet: they fell while standing on
what looked like solid ceiling.

Where to cut: where the player's feet are drawn. On the ceiling the player sprite hangs upside down from the slab,
feet on the underside; with the ceiling camera (the wall-top template of the map's tw_arc record: angle x 55, y 240,
on DISTORTION_WORLD_CAMERA_BASE_ANGLE_X) the feet meet the slab 0.4 tiles east and 0.4 tiles south of the tile the
player stands on (measured: the feet are drawn at screen (131, 72), the slab's drawn edges fit this camera to a
pixel). So the notch is the honeycomb's footprint moved by that much, x 44.4-46.4, z 32.6-36.6, and widened west
over the slab's bevelled edge to x 43.4 (nothing west of x 44 is walkable): on every honeycomb tile the feet are
half a tile inside the hole, and on the tiles round it ((44..45, 32), (44..45, 37), (46, 32)) half a tile outside
it, on slab. (The honeycomb's ghost props hang 2-4 tiles under the slab, so they draw round the player's body, not
round the feet; the camera's target, the player's map position, is 2 tiles under the slab too, and a cut placed
where that point projects, 2.3 tiles east and 5.6 south, missed the feet entirely.)

What is cut: only the underside layers (every face of the slab between h 10.5 and 11.8 over the notch; faces that
straddle its outline are clipped, UVs interpolated). The top sheet and everything on it stay, so seen from above
(the hive floor) the slab is unchanged; from below the top sheet faces away (back-face culled) and the DW void shows
through. No inner walls: at this camera's grazing angle the far wall filled the hole and read as dark rock, not as
void. The honeycomb, while it is there, is drawn over the hole. Permissions and BDHC are 613's (the ceiling's
collision is the tw_arc grid). Matrix 292 is [[671, 679], [614, 615]].

Usage: python3 tools/distortion_world/build_dw_eterna_forest_map.py [--check]
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import mapdata  # noqa: E402
import nsbmd  # noqa: E402

DATA = os.path.join(ROOT, "res/field/maps/data")
MATRIX = os.path.join(ROOT, "res/field/maps/matrices/map_matrix_292.json")
MATRIX_ROWS = [["MAP_671", "MAP_679"], ["MAP_614", "MAP_615"]]
SRC = {671: 667}
BLOCKED = 0x8000

# (x0, z0, x1, z1) inclusive: set to plain blocked (no tile behaviour).
BLOCK = [
    (16, 13, 19, 13),   # drawn ground under the two trees south of the walkway (was a falling lip)
    (16, 11, 18, 11),   # the drawn rock block north of the walkway (was a falling lip)
    (23, 12, 30, 12),   # B1F's upper hop chain east of the walkway: no stones drawn in this map
    (21, 22, 31, 22),   # B1F's lower hop chain: no stones drawn either
]


# --- the honeycomb notch (679 from 613) -------------------------------------------------------------------------
HONEY_SRC, HONEY_DST, HONEY_CHUNK = 613, 679, (1, 0)
HONEY_X0, HONEY_X1, HONEY_Z0, HONEY_Z1 = 44.0, 46.0, 33.0, 37.0   # the honeycomb tiles x 44-45, z 33-36
FEET_OFFSET = (0.4, -0.4)            # where the feet meet the slab, from the player's tile (see the docstring)
SLAB_EDGE_X = 43.4                   # the slab's bevelled west edge (x 43.5-44): cut with the notch
NOTCH_H0, NOTCH_H1 = 10.5, 11.8      # the underside layers (h 11.0, 11.5); the top sheet (h 12.1) stays


def notch_rect():
    """The notch in plan (x0, x1, z0, z1), world tiles."""
    dx, dz = FEET_OFFSET
    return (SLAB_EDGE_X, HONEY_X1 + dx, HONEY_Z0 + dz, HONEY_Z1 + dz)


def _units(model, chunk):
    """World tile <-> display-list fx16 conversions for this chunk model (nsbmd.model_to_mesh's inverse)."""
    per_tile = nsbmd.TILE * nsbmd.FX / (model["info"]["pos_scale"] / nsbmd.FX)   # fx16 per tile
    cx, cz = chunk
    return {
        "x": lambda t: round((t - 16 - cx * 32) * per_tile), "z": lambda t: round((t - 16 - cz * 32) * per_tile),
        "h": lambda h: round((h * nsbmd.TILE + nsbmd.GROUND_Y) * per_tile / nsbmd.TILE),
        "per_tile": per_tile,
    }


def _lerp_vertex(a, b, t):
    v = dict(a)
    v["pos"] = tuple(round(a["pos"][k] + (b["pos"][k] - a["pos"][k]) * t) for k in range(3))
    if a["uv"] is not None and b["uv"] is not None:
        v["uv"] = tuple(round(a["uv"][k] + (b["uv"][k] - a["uv"][k]) * t) for k in range(2))
    return v


def _clip(poly, axis, value, keep_below):
    """Sutherland-Hodgman: the part of a convex polygon with pos[axis] <= value (keep_below) or >= value."""
    inside = (lambda v: v["pos"][axis] <= value) if keep_below else (lambda v: v["pos"][axis] >= value)
    out = []
    for i, cur in enumerate(poly):
        prev = poly[i - 1]
        if inside(cur):
            if not inside(prev):
                out.append(_lerp_vertex(prev, cur, (value - prev["pos"][axis]) / (cur["pos"][axis] - prev["pos"][axis])))
            out.append(cur)
        elif inside(prev):
            out.append(_lerp_vertex(prev, cur, (value - prev["pos"][axis]) / (cur["pos"][axis] - prev["pos"][axis])))
    return out


def _area(poly):
    """3D area of a planar polygon (fx16 units squared)."""
    s = [0.0, 0.0, 0.0]
    for i, v in enumerate(poly):
        a, b = poly[i - 1]["pos"], v["pos"]
        s[0] += a[1] * b[2] - a[2] * b[1]
        s[1] += a[2] * b[0] - a[0] * b[2]
        s[2] += a[0] * b[1] - a[1] * b[0]
    return sum(c * c for c in s) ** 0.5 / 2


def _cut_face(face, rect, hrange):
    """A face minus the notch (a box: x0..x1, z0..z1 in plan, h0..h1 in height). Returns a list of convex polygons
    (the face itself when it misses the box). Faces wholly inside the box are dropped; faces that straddle its plan
    outline are split into the parts outside it."""
    x0, x1, z0, z1 = rect
    h0, h1 = hrange
    ys = [v["pos"][1] for v in face]
    if max(ys) < h0 or min(ys) > h1:
        return [face]
    xs = [v["pos"][0] for v in face]
    zs = [v["pos"][2] for v in face]
    if max(xs) <= x0 or min(xs) >= x1 or max(zs) <= z0 or min(zs) >= z1:
        return [face]
    if min(xs) >= x0 and max(xs) <= x1 and min(zs) >= z0 and max(zs) <= z1:
        return []
    pieces = [_clip(list(face), 0, x0, True), _clip(list(face), 0, x1, False)]
    mid = _clip(_clip(list(face), 0, x0, False), 0, x1, True)
    if mid:
        pieces += [_clip(mid, 2, z0, True), _clip(mid, 2, z1, False)]
    return [p for p in pieces if len(p) >= 3 and _area(p) > 4]


def _split(polys):
    tris, quads = [], []
    for p in polys:
        if len(p) == 4:
            quads.append(tuple(p))
        elif len(p) == 3:
            tris.append(tuple(p))
        else:
            tris += [(p[0], p[k], p[k + 1]) for k in range(1, len(p) - 1)]
    return tris, quads


def cut_honeycomb_notch(model_bytes):
    """613's model with the notch cut in the ceiling slab's underside. Only the shapes the notch touches are
    re-encoded; the rest of the model is byte-identical."""
    bmd = nsbmd.parse_bmd(model_bytes)
    m = bmd["models"][0]
    u = _units(m, HONEY_CHUNK)
    notch = notch_rect()
    rect = (u["x"](notch[0]), u["x"](notch[1]), u["z"](notch[2]), u["z"](notch[3]))
    hrange = (u["h"](NOTCH_H0), u["h"](NOTCH_H1))
    mat_of_shape = {si: mi for mi, si in nsbmd.shape_material_pairs(m)}
    stats = {}
    for si, shape in enumerate(m["shapes"]):
        mat = m["materials"][mat_of_shape[si]]["name"]
        tris, quads = nsbmd.prims_to_faces(nsbmd.dl_primitives(nsbmd.dl_decode(shape["dl"])))
        polys, changed = [], False
        for f in list(quads) + list(tris):
            cut = _cut_face(f, rect, hrange)
            changed |= cut != [f]
            polys += cut
        if not changed:
            continue
        nt, nq = _split(polys)
        stats[mat] = (len(tris) + len(quads), len(nt) + len(nq))
        shape["dl"] = nsbmd.dl_pack(nsbmd.encode_prims(nsbmd.faces_to_prims(nt, nq)))
    st = nsbmd.model_stats(m)
    m["info"]["num_vertex"] = st["vertices_sent"]
    m["info"]["num_polygon"] = st["polygons"]
    m["info"]["num_triangle"] = st["triangles"]
    m["info"]["num_quad"] = st["quads"]
    return nsbmd.build_bmd(bmd["models"], bmd["tex0"], bmd["version"]), stats


def build():
    out = {}
    for dst, src in SRC.items():
        parts = mapdata.unpack(open(os.path.join(DATA, f"map_data_{src}.bin"), "rb").read())
        perm = mapdata.read_permissions(parts["permissions"])
        for x0, z0, x1, z1 in BLOCK:
            for z in range(z0, z1 + 1):
                for x in range(x0, x1 + 1):
                    perm[z][x] = BLOCKED
        parts["permissions"] = mapdata.write_permissions(perm)
        out[os.path.join(DATA, f"map_data_{dst}.bin")] = mapdata.pack(parts["permissions"], parts["props"],
                                                                       parts["model"], parts["bdhc"])
    parts = mapdata.unpack(open(os.path.join(DATA, f"map_data_{HONEY_SRC}.bin"), "rb").read())
    model, _ = cut_honeycomb_notch(parts["model"])
    out[os.path.join(DATA, f"map_data_{HONEY_DST}.bin")] = mapdata.pack(parts["permissions"], parts["props"], model,
                                                                         parts["bdhc"])
    out[MATRIX] = (json.dumps({"name": "m_dwa2_2", "headers": [], "altitudes": [], "maps": MATRIX_ROWS},
                              indent=4) + "\n").encode()
    return out


def main():
    out = build()
    check = "--check" in sys.argv
    ok = True
    for path, data in out.items():
        same = os.path.exists(path) and open(path, "rb").read() == data
        ok &= same
        if not check:
            open(path, "wb").write(data)
            print(path, "unchanged" if same else "written")
    print("honeycomb notch (x0, x1, z0, z1):", notch_rect())
    if check:
        print("OK" if ok else "differs (run without --check)")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
