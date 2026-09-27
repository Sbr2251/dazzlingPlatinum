#!/usr/bin/env python3
"""Lake Verity graybox: regenerates map_data 537/538/540/541 from layout.py (standard library only).

    python3 tools/lake_verity/build_graybox.py [--dry-run] [--preview DIR]

For each chunk:
  * stock terrain, with the faces inside the redesign footprint removed (assemble.cut_stock; the old hut goes);
  * the island as extruded blocks: one top per layout tile at its layout height (merged into rectangles), and
    vertical sides wherever a tile is higher than its neighbour. Island sides facing open water run down to the
    lakebed (h -4). The stair top is the BDHC slope itself (collision.slopes()), so what the player walks on is
    what is drawn. The bridge is a deck at h 0 with thin sides and no underside;
  * door niches get a "dhole" overlay on their back wall;
  * stock props (the animated l_lake water plane), permissions and BDHC from collision.py.
All textures are set-61 textures (area 62), so no texture set change is needed.

--preview DIR writes chunk_<id>.mesh.json (decoded back from the built NSBMD) and stats.json for blender_preview.py.
--dry-run builds and checks budgets without writing the map_data files.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import assemble  # noqa: E402
import collision  # noqa: E402
import layout  # noqa: E402
import nsbmd  # noqa: E402

LAKEBED_H = -4.0        # island sides facing water go this deep (stock lakebed is about -4)
BRIDGE_SIDE_H = -0.25   # bridge deck thickness
MAX_RUN = 16            # merged quads stay <= 16 tiles so UVs (1 repeat per tile) fit the +-2048 texel range
DOOR_INSET = 0.05       # dhole overlay offset in front of the niche's back wall

TOP_TEX = {"courtyard": "beach", "landing": "beach", "door1": "beach", "gate_arch": "beach",
           "terrace1": "ngrass", "door2": "ngrass", "keep2": "blueglayp", "roof": "blueglay",
           "wall1": "criff", "wall2": "criff", "wall3": "criff", "rail": "criff",
           "tower": "hanger", "gate": "hanger", "stair": "newstep", "bridge": "bridge",
           "launchpad": "fenter", "hatch": "shadowchip"}
SIDE_TEX = {"tower": "hanger", "gate": "hanger", "bridge": "nbridge"}
SHORE_TEX = "criffp2"
WALL_TEX = "criffp"
DOOR_TEX = "dhole"


def mat(tex):
    return "gb_" + tex


class Island:
    def __init__(self):
        self.t = layout.tiles()
        self.fp = assemble.footprint()
        self.slope = collision.slopes()[0]          # (x0, x1, z_top, z_bottom, h_top, h_bottom)

    # ---- heights -------------------------------------------------------------------------------------------
    def in_slope(self, tile, pz):
        x0, x1, zt, zb, _, _ = self.slope
        return tile in self.fp and x0 <= tile[0] < x1 and zt <= pz <= zb and tile[1] <= pz <= tile[1] + 1

    def slope_h(self, pz):
        _, _, zt, zb, ht, hb = self.slope
        return ht + (hb - ht) * (pz - zt) / (zb - zt)

    def top(self, tile, pz):
        """Top height of tile at (continuous) z = pz on its border (or inside)."""
        if tile in self.fp:
            if self.in_slope(tile, pz):
                return self.slope_h(pz)
            return self.t[tile][1]
        return None

    def floor(self, tile, owner):
        """Height the owner's side face runs down to next to a tile outside the footprint."""
        kind = self.t[tile][2]
        if kind == "water":
            return BRIDGE_SIDE_H if self.t[owner][2] == "bridge" else LAKEBED_H
        return 0.0

    def h_at(self, tile, pz, owner):
        v = self.top(tile, pz)
        return self.floor(tile, owner) if v is None else v

    def slope_tile(self, tile):
        x0, x1, zt, zb, _, _ = self.slope
        return tile in self.fp and x0 <= tile[0] < x1 and tile[1] + 1 > zt and tile[1] < zb


def chunk_of(x, z):
    by_xy = {v: k for k, v in layout.CHUNKS.items()}
    return by_xy[(int(x // 32), int(z // 32))]


class MeshBuilder:
    """Per chunk, per material face lists with unshared vertices (flat normals)."""

    def __init__(self):
        self.chunks = {}

    def add(self, chunk, tex, pts, uvs, want):
        """pts: 3 or 4 (x, h, z); want: desired facing (normal direction); reorders the winding to face it."""
        n = _normal(pts)
        if sum(a * b for a, b in zip(n, want)) < 0:
            pts, uvs = pts[::-1], uvs[::-1]
            n = [-v for v in n]
        ln = sum(v * v for v in n) ** 0.5
        if ln < 1e-9:
            return
        n = [v / ln for v in n]
        me = self.chunks.setdefault(chunk, {}).setdefault(mat(tex), {"material": mat(tex), "positions": [],
                                                                     "uvs": [], "normals": [], "tris": [],
                                                                     "quads": []})
        base = len(me["positions"])
        me["positions"] += [list(p) for p in pts]
        me["uvs"] += [list(u) for u in uvs]
        me["normals"] += [n] * len(pts)
        me["quads" if len(pts) == 4 else "tris"].append(list(range(base, base + len(pts))))

    def meshes(self, chunk):
        mats = self.chunks.get(chunk, {})
        return {"name": f"graybox_{chunk}",
                "materials": [{"name": k, "texture": k[3:], "polygon_attr": {"lights": 1}} for k in sorted(mats)],
                "meshes": [mats[k] for k in sorted(mats)]}


def _normal(pts):
    a, b, c = pts[0], pts[1], pts[2]
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    if len(pts) == 4 and sum(x * x for x in n) < 1e-12:
        return _normal([pts[0], pts[2], pts[3]])
    return n


def _rects(cells):
    """cells: {(x, z): key}. Greedy rectangles of equal key, row-major, capped at MAX_RUN.
    -> [(x0, z0, x1, z1, key)] exclusive ends."""
    used = set()
    out = []
    for (x, z) in sorted(cells, key=lambda p: (p[1], p[0])):
        if (x, z) in used:
            continue
        k = cells[(x, z)]
        w = 1
        while w < MAX_RUN and (x + w, z) not in used and cells.get((x + w, z)) == k:
            w += 1
        d = 1
        while d < MAX_RUN and all((x + i, z + d) not in used and cells.get((x + i, z + d)) == k for i in range(w)):
            d += 1
        for i in range(w):
            for j in range(d):
                used.add((x + i, z + j))
        out.append((x, z, x + w, z + d, k))
    return out


def build_tops(isl, mb):
    flat = {}
    for tile in isl.fp:
        kind = isl.t[tile][2]
        tex = TOP_TEX[kind]
        if isl.slope_tile(tile):
            x, z = tile
            _, _, zt, zb, _, _ = isl.slope
            cuts = sorted({z, z + 1} | {c for c in (zt, zb) if z < c < z + 1})
            for za, zc in zip(cuts, cuts[1:]):
                ha, hc = isl.top(tile, za + 1e-6), isl.top(tile, zc - 1e-6)
                ha, hc = (isl.slope_h(za), isl.slope_h(zc)) if isl.in_slope(tile, (za + zc) / 2) else (ha, hc)
                pts = [(x, hc, zc), (x + 1, hc, zc), (x + 1, ha, za), (x, ha, za)]
                uvs = [(0, zc - z), (1, zc - z), (1, za - z), (0, za - z)]
                mb.add(chunk_of(x + 0.5, z + 0.5), tex, pts, uvs, (0, 1, 0))
            continue
        flat[tile] = (tex, isl.t[tile][1], chunk_of(tile[0] + 0.5, tile[1] + 0.5))
    for x0, z0, x1, z1, (tex, h, c) in _rects(flat):
        pts = [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)]
        uvs = [(0, z1 - z0), (x1 - x0, z1 - z0), (x1 - x0, 0), (0, 0)]
        mb.add(c, tex, pts, uvs, (0, 1, 0))


def build_sides(isl, mb):
    """Vertical faces on every tile edge where the two sides differ in height. Each edge is visited once; the
    higher side owns the face (split into triangles where the heights cross, e.g. stair vs rail)."""
    runs = {}      # (axis, line, dir, h_top, h_bot, tex, chunk) -> [start positions]  (flat, unit-length faces)
    edges = set()
    for (x, z) in isl.fp:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = (x, z), (x + dx, z + dz)
            edges.add((min(a, b), max(a, b)))
    for a, b in sorted(edges):
        if a[1] == b[1]:            # neighbours along x: the shared edge is the line x = b[0], z in [z, z+1]
            line, z = b[0], a[1]
            cuts = [z, z + 1]
            if isl.slope_tile(a) or isl.slope_tile(b):
                _, _, zt, zb, _, _ = isl.slope
                cuts = sorted(set(cuts) | {c for c in (zt, zb) if z < c < z + 1})
            for s0, s1 in zip(cuts, cuts[1:]):
                _edge(isl, mb, runs, "x", line, a, b, s0, s1)
        else:                       # neighbours along z: the shared edge is the line z = b[1], x in [x, x+1]
            _edge(isl, mb, runs, "z", b[1], a, b, a[0], a[0] + 1)
    # merge flat unit faces into runs
    for (axis, line, d, ht, hb, tex, c), starts in runs.items():
        starts.sort()
        i = 0
        while i < len(starts):
            j = i
            while j + 1 < len(starts) and starts[j + 1] == starts[j] + 1 and starts[j + 1] - starts[i] < MAX_RUN:
                j += 1
            _quad(mb, c, tex, axis, line, d, starts[i], starts[j] + 1, (ht, ht), (hb, hb))
            i = j + 1


def _side_tex(isl, owner, other):
    k = isl.t[owner][2]
    if k in SIDE_TEX:
        return SIDE_TEX[k]
    if other not in isl.fp and isl.t[other][2] == "water":
        return SHORE_TEX
    return WALL_TEX


def _edge(isl, mb, runs, axis, line, a, b, s0, s1):
    """Edge segment [s0, s1] on the line between tiles a (lower coordinate) and b."""
    def hs(tile, owner):
        if axis == "x":
            return isl.h_at(tile, s0, owner), isl.h_at(tile, s1, owner)
        pz = b[1]                   # z of the shared line
        return isl.h_at(tile, pz, owner), isl.h_at(tile, pz, owner)
    for owner, other, d in ((a, b, +1), (b, a, -1)):
        if owner not in isl.fp:
            continue
        o0, o1 = hs(owner, owner)
        n0, n1 = hs(other, owner)
        e0, e1 = o0 - n0, o1 - n1
        if e0 <= 1e-9 and e1 <= 1e-9:
            continue
        c = chunk_of(owner[0] + 0.5, owner[1] + 0.5)
        tex = _side_tex(isl, owner, other)
        # the face looks from the owner towards the other tile: +axis if owner is a (d = +1)
        if e0 >= -1e-9 and e1 >= -1e-9:
            if abs(o0 - o1) < 1e-9 and abs(n0 - n1) < 1e-9 and abs(s1 - s0 - 1) < 1e-9:
                runs.setdefault((axis, line, d, o0, n0, tex, c), []).append(s0)
            else:
                _quad(mb, c, tex, axis, line, d, s0, s1, (o0, o1), (n0, n1))
        else:                       # heights cross: keep the part where the owner is higher
            t = e0 / (e0 - e1)
            sm = s0 + (s1 - s0) * t
            hm = o0 + (o1 - o0) * t
            if e0 > 0:
                _tri(mb, c, tex, axis, line, d, (s0, o0), (s0, n0), (sm, hm), o0)
            else:
                _tri(mb, c, tex, axis, line, d, (s1, o1), (s1, n1), (sm, hm), o1)
        if isl.t.get(other, (0, 0, ""))[2] in ("door1", "door2") and axis == "z" and d == +1:
            _door(mb, isl, c, line, s0, s1, n0, o0)


def _pt(axis, line, s, h):
    return (line, h, s) if axis == "x" else (s, h, line)


def _facing(axis, d):
    return (d, 0, 0) if axis == "x" else (0, 0, d)


def _u(axis, d, s):
    """u runs left to right as seen from outside the face."""
    return (-s if d > 0 else s) if axis == "x" else (s if d > 0 else -s)


def _quad(mb, c, tex, axis, line, d, s0, s1, top, bot):
    ref = max(top)
    u0, u1 = _u(axis, d, s0), _u(axis, d, s1)
    base = min(u0, u1)
    pts = [_pt(axis, line, s0, top[0]), _pt(axis, line, s1, top[1]), _pt(axis, line, s1, bot[1]),
           _pt(axis, line, s0, bot[0])]
    uvs = [(u0 - base, ref - top[0]), (u1 - base, ref - top[1]), (u1 - base, ref - bot[1]), (u0 - base, ref - bot[0])]
    if abs(top[0] - bot[0]) < 1e-9:
        pts, uvs = pts[1:], uvs[1:]
    elif abs(top[1] - bot[1]) < 1e-9:
        pts, uvs = pts[:2] + pts[3:], uvs[:2] + uvs[3:]
    mb.add(c, tex, pts, uvs, _facing(axis, d))


def _tri(mb, c, tex, axis, line, d, top, bot, mid, ref):
    s = [top[0], bot[0], mid[0]]
    u = [_u(axis, d, v) for v in s]
    base = min(u)
    pts = [_pt(axis, line, *top), _pt(axis, line, *bot), _pt(axis, line, *mid)]
    uvs = [(u[0] - base, ref - top[1]), (u[1] - base, ref - bot[1]), (u[2] - base, ref - mid[1])]
    mb.add(c, tex, pts, uvs, _facing(axis, d))


def _door(mb, isl, c, line, s0, s1, h_bot, h_top):
    """dhole overlay on the back wall of a door niche (the wall faces +z, towards the camera)."""
    z = line + DOOR_INSET
    top = min(h_top, h_bot + 2)
    pts = [(s0, top, z), (s1, top, z), (s1, h_bot, z), (s0, h_bot, z)]
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]      # one door texture over the 1 x 2 tile opening
    mb.add(c, DOOR_TEX, pts, uvs, (0, 0, 1))


def graybox_meshes():
    isl = Island()
    mb = MeshBuilder()
    build_tops(isl, mb)
    build_sides(isl, mb)
    return isl, {c: mb.meshes(c) for c in assemble.CHUNKS}


def view_window_polys(models, w=16, d=12):
    """Worst case polygons in any w x d tile window over the lake (face centroids), a conservative stand-in for
    the per-frame count the camera sees (it sees about 15 x 11 tiles). -> (polys, (x, z))."""
    cent = []
    for c, model in models.items():
        m = nsbmd.model_to_mesh(model, layout.CHUNKS[c])
        for me in m["meshes"]:
            P = me["positions"]
            for f in me["tris"] + me["quads"]:
                cent.append((sum(P[i][0] for i in f) / len(f), sum(P[i][2] for i in f) / len(f)))
    best = (0, None)
    for x in range(0, 64 - w + 1):
        for z in range(0, 64 - d + 1):
            n = sum(1 for cx, cz in cent if x <= cx < x + w and z <= cz < z + d)
            if n > best[0]:
                best = (n, (x, z))
    return best


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    preview = args[args.index("--preview") + 1] if "--preview" in args else None
    isl, extra = graybox_meshes()
    textures = assemble.texture_table()
    bridge = {k for k, v in isl.t.items() if v[2] == "bridge"}
    stats, models = [], {}
    for c in assemble.CHUNKS:
        data, st, model = assemble.build_chunk(c, [extra[c]], isl.fp, textures, keep_under=bridge)
        stats.append(st)
        models[c] = model
        if not dry:
            open(assemble.map_path(c), "wb").write(data)
        if preview:
            os.makedirs(preview, exist_ok=True)
            back = nsbmd.parse_bmd(nsbmd.build_bmd([model]))["models"][0]
            json.dump(nsbmd.model_to_mesh(back, layout.CHUNKS[c], name=f"chunk_{c}"),
                      open(os.path.join(preview, f"chunk_{c}.mesh.json"), "w"))
    win, at = view_window_polys(models)
    print(f"{'chunk':>5} {'polys':>6} {'tris':>5} {'quads':>6} {'verts':>6} {'model B':>8} {'BDHC B':>7} "
          f"{'plates':>6} {'mats':>4}")
    for s in stats:
        print(f"{s['chunk']:>5} {s['polygons']:>6} {s['triangles']:>5} {s['quads']:>6} {s['vertices_sent']:>6} "
              f"{s['model_bytes']:>8} {s['bdhc_bytes']:>7} {s['bdhc_plates']:>6} {s['materials']:>4}")
    print(f"worst 16x12-tile window: {win} polygons at tile {at} (limit 2048 per frame incl. sprites)")
    problems, warnings = assemble.check_budgets(stats, window_polys=win)
    for w in warnings:
        print("warning: " + w)
    print("budgets ok" if not problems else "BUDGET PROBLEMS: " + "; ".join(problems))
    if preview:
        json.dump({"chunks": stats, "window_polys": win, "window_at": at},
                  open(os.path.join(preview, "stats.json"), "w"), indent=1)
    if not dry:
        print("wrote " + ", ".join(os.path.relpath(assemble.map_path(c), assemble.ROOT) for c in assemble.CHUNKS))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
