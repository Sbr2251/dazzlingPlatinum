#!/usr/bin/env python3
"""Route 218 — Everspring Sanctuary art pass: writes map_texture_set_077 (textures_math.py), map_data_050 and
map_data_051 (terrain + props + Gardevoir Fountain + Rift Conduit + permissions + BDHC), all from math.

Usage (Python with NumPy; PIL only for --preview):
  ~/.venvs/desmume/bin/python tools/everspring/build_art.py                 dry run: build, budgets, every check
  ~/.venvs/desmume/bin/python tools/everspring/build_art.py --preview DIR   also DIR/view_*.png field-camera renders,
                                                                             DIR/top.png and DIR/tex/*.png
  ~/.venvs/desmume/bin/python tools/everspring/build_art.py --write         write the three binaries and
                                                                             lighting_set_005.json (refuses on FAIL)

Inputs: the tile contract (layout.py: kinds, heights, anchors; collision.py: permissions + BDHC), stock set 015 and
the stock gatehouse props from git HEAD (so reruns never feed back), textures_math.py, gardevoir_fountain.py.
The chunk models are rebuilt from scratch (nsbmd.mesh_to_model / build_bmd, the Lake Verity writer): nothing of
the stock Route 218 terrain is kept except the two gatehouse props (build model 40) the warps lead into.

What it builds (docs/everspring_redesign/PLAN.md section 3), absolute tiles x 64..127, z 736..767, h 0 = ground:
  * ground per tile kind, merged into rectangles: ev_grass meadow, ev_cobble walkways, ev_marble plaza (a true
    octagon: the chamfer corners are cut on the diagonal), ev_tgrass tall grass, ev_spiral_flw blossom clearings,
    ev_water lagoon at h -0.5; ev_cliff shore and terrace curbs where land meets water; moonstone steps at the East
    Surf Landing.
  * a continuous blossom canopy over every tree tile (smooth-normal heightfield, ev_blossom) and a rounded low-poly
    sakura / wisteria crown with a plum trunk on every forest-edge tree facing the glade.
  * the West Arched Moonbridge (planked deck, arched south fascia, rose-gold arched rails, lantern posts) and the
    East Lantern Overlook Pier (deck on piles, rails, open west end for Surf).
  * lanterns (warm unlit glow heads), glowing fairy mushroom clusters, the logarithmic spiral of glowing pixel
    blossoms sin(3 theta - 1.55 r) across the Spiral Blossom Meadow.
  * the Gardevoir Fountain (gardevoir_fountain.py, all of it in map_data_050) and the Rift Conduit crystal obelisk.
  * permissions and BDHC exactly as collision.py; the stock gatehouse props at HEAD (layout.GATE_PROPS).

Lighting: terrain, trees, bridge and pier are lit by light 0 (lighting_set_005 drives day / evening / night);
the fountain, statue, crystal, mushrooms, lantern heads, water jets and spiral blossoms are unlit with baked
vertex colours, so they glow softly at night.

Checks (--write refuses on any FAIL): layout checks; permissions + BDHC per chunk equal the layout; BDHC and model
within the land-data buffers (0x9000 / 0xF000); NSBMD parse -> rebuild byte-identical; every material's texture and
palette exist in set 077 with matching sizes; every walkable tile drawn at its layout height; nothing solid low
over a walkable tile; fountain inside its rect and entirely in map_data_050; crystal inside its rect; gate props
identical to stock; set 077 round trip + VRAM (textures_math).
"""
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
sys.path.insert(0, HERE)

import layout  # noqa: E402
import collision  # noqa: E402
import textures_math as TM  # noqa: E402
import gardevoir_fountain as GF  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402

OUT_MAP_DIR = "res/field/mapmodels/data"
MODEL_BUFFER = 0xF000            # include/overlay005/loaded_map_buffers.h MAP_MODEL_FILE_SIZE
BDHC_BUFFER = 0x9000             # include/constants/field/bdhc.h BDHC_BUFFER_SIZE
G, WH = layout.GROUND_H, layout.WATER_H
UVR = 0.5                        # ground UV per tile: 32-texel textures repeat every 2 tiles = 16 texels per tile
OX, OZ = 64, 736                 # planar UV origin (keeps texcoords small, seamless across both chunks)

# material key -> (texture, lit, cull)
MATS = {
    "ev_grass": ("ev_grass", True, "back"), "ev_tgrass": ("ev_tgrass", True, "back"),
    "ev_spiral_flw": ("ev_spiral_flw", True, "back"), "ev_cobble": ("ev_cobble", True, "back"),
    "ev_water": ("ev_water", True, "back"), "ev_marble": ("ev_marble", True, "back"),
    "ev_cliff": ("ev_cliff", True, "back"), "ev_blossom": ("ev_blossom", True, "back"),
    "ev_bridge": ("ev_bridge", True, "back"),
    "u_marble": ("ev_marble", False, "back"), "u_water": ("ev_water", False, "back"),
    "u_jet": ("ev_marble", False, "none"), "u_gv": ("ev_gardevoir", False, "back"),
    "u_gv2": ("ev_gardevoir", False, "none"), "u_crystal": ("ev_crystal", False, "back"),
    "u_mushroom": ("ev_mushroom", False, "back"), "u_blossom": ("ev_spiral_flw", False, "back"),
}


# groups whose vertices snap to the 1/16-tile grid (the fountain and the crystal keep full fx16 precision)
SNAP = {"ground", "curb", "canopy", "crowns", "bridge", "pier", "lanterns", "mushrooms", "spiral"}


def chunk_of_x(x):
    return 50 if x < 96 else 51


def hash01(*v):
    h = 2166136261
    for c in v:
        h = ((h ^ (int(c) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5BD1E995) & 0xFFFFFFFF
    return (h ^ (h >> 15)) / 4294967296.0


# ---------------------------------------------------------------------------------------------------------------
# face builder
# ---------------------------------------------------------------------------------------------------------------

class Art:
    """Faces in absolute tiles (x, h, z) per chunk and material. Lit materials carry normals (flat by default),
    unlit ones baked colours. Faces go to the chunk of their centroid unless `chunk` is given."""

    def __init__(self):
        self.faces = {c: {} for c in layout.CHUNKS}
        self.groups = {}
        self.solids = []           # non-flat faces, for the walkable-clearance check
        self.bounds = {}           # group -> [xmin, zmin, xmax, zmax, hmax]
        self.group_chunks = {}

    def add(self, mat, pts, uvs, colors=None, normals=None, facing=None, chunk=None, group=None, solid=True):
        if group in SNAP:            # 1/16 tile = 1 world unit = 64 fx: VTX_10 / one-word vertices, on the pixel grid
            pts = [tuple(round(float(c) * 16) / 16 for c in p) for p in pts]
            if len({p for p in pts}) < 3:
                return
        else:
            pts = [tuple(float(c) for c in p) for p in pts]
        uvs = [tuple(u) for u in uvs]
        n = GF.face_n(pts)
        if facing is not None and GF.dot(n, facing) < 0:
            pts, uvs = pts[::-1], uvs[::-1]
            colors = colors[::-1] if colors else colors
            normals = normals[::-1] if normals else normals
            n = tuple(-c for c in n)
        tex, lit, cull = MATS[mat]
        if lit:
            normals = [tuple(v) for v in normals] if normals else [n] * len(pts)
            colors = None
        else:
            colors = [tuple(c) for c in colors] if colors else [(255, 255, 255)] * len(pts)
            normals = None
        cx = sum(p[0] for p in pts) / len(pts)
        c = chunk if chunk is not None else chunk_of_x(cx)
        self.faces[c].setdefault(mat, []).append((pts, uvs, colors, normals, group or "misc"))
        g = group or "misc"
        self.groups[g] = self.groups.get(g, 0) + 1
        self.group_chunks.setdefault(g, set()).add(c)
        b = self.bounds.setdefault(g, [1e9, 1e9, -1e9, -1e9, -1e9])
        for p in pts:
            b[0], b[1], b[2], b[3], b[4] = min(b[0], p[0]), min(b[1], p[2]), max(b[2], p[0]), max(b[3], p[2]), max(b[4], p[1])
        if solid and abs(n[1]) < 0.999:
            self.solids.append(pts)

    def count(self, group=None):
        return self.groups.get(group, 0) if group else sum(self.groups.values())

    def box(self, mat, x0, z0, x1, z1, h0, h1, uv, color=None, sides="swet", chunk=None, group=None, solid=True,
            top_uv=None):
        u0, v0, u1, v1 = uv
        faces = {"s": ([(x0, h1, z1), (x1, h1, z1), (x1, h0, z1), (x0, h0, z1)], (0, 0, 1)),
                 "n": ([(x1, h1, z0), (x0, h1, z0), (x0, h0, z0), (x1, h0, z0)], (0, 0, -1)),
                 "e": ([(x1, h1, z1), (x1, h1, z0), (x1, h0, z0), (x1, h0, z1)], (1, 0, 0)),
                 "w": ([(x0, h1, z0), (x0, h1, z1), (x0, h0, z1), (x0, h0, z0)], (-1, 0, 0)),
                 "t": ([(x0, h1, z1), (x1, h1, z1), (x1, h1, z0), (x0, h1, z0)], (0, 1, 0))}
        for s in sides:
            pts, n = faces[s]
            tu = top_uv if (s == "t" and top_uv) else (u0, v0, u1, v1)
            uvs = [(tu[0], tu[1]), (tu[2], tu[1]), (tu[2], tu[3]), (tu[0], tu[3])]
            cols = [color(n, p[1]) for p in pts] if color else None
            self.add(mat, pts, uvs, colors=cols, facing=n, chunk=chunk, group=group, solid=solid and s != "t")

    def flat(self, mat, x0, z0, x1, z1, h, group="ground", planar=UVR, uv=None, colors=None):
        pts = [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)]
        if uv is None:
            uvs = [((p[0] - OX) * planar, (p[2] - OZ) * planar) for p in pts]
        else:
            u0, v0, u1, v1 = uv
            uvs = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
        self.add(mat, pts, uvs, colors=colors, facing=(0, 1, 0), group=group, solid=False)

    def wall(self, mat, a, b, h0, h1, uv, group="misc", colors=None, solid=True):
        """Upright quad from a to b ((x, z), left to right seen from its front)."""
        (xa, za), (xb, zb) = a, b
        u0, v0, u1, v1 = uv
        n = (-(zb - za), 0.0, xb - xa)
        self.add(mat, [(xa, h1, za), (xb, h1, zb), (xb, h0, zb), (xa, h0, za)],
                 [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], colors=colors, facing=n, group=group, solid=solid)

    def mesh(self, c, only=None):
        mats, meshes = [], []
        for mat, flist in self.faces[c].items():
            if only is not None:
                flist = [f for f in flist if f[4] in only]
                if not flist:
                    continue
            tex, lit, cull = MATS[mat]
            mats.append({"name": mat, "texture": tex, "palette": TM.pal_name(tex), "size": [TM.N, TM.N],
                         "repeat": [True, True], "polygon_attr": {"lights": 1 if lit else 0, "cull": cull, "fog": True}})
            pos, uv, col, nrm, tris, quads = [], [], [], [], [], []
            for pts, uvs, colors, normals, _ in flist:
                b = len(pos)
                pos += [list(p) for p in pts]
                uv += [list(u) for u in uvs]
                col += [list(cc) for cc in colors] if colors else [[255, 255, 255]] * len(pts)
                nrm += [list(nn) for nn in normals] if normals else [[0.0, 1.0, 0.0]] * len(pts)
                (quads if len(pts) == 4 else tris).append(list(range(b, b + len(pts))))
            meshes.append({"material": mat, "positions": pos, "uvs": uv, "colors": col, "normals": nrm,
                           "tris": tris, "quads": quads})
        return {"name": f"ev_r218_{c:03d}", "materials": mats, "meshes": meshes}


def planar(p):
    return ((p[0] - OX) * UVR, (p[2] - OZ) * UVR)


# ---------------------------------------------------------------------------------------------------------------
# ground, curbs, steps
# ---------------------------------------------------------------------------------------------------------------

def island_in(x, z):
    return layout.is_island_octagon(x, z)


def ground_mat(t, x, z):
    kind = t[(x, z)][2]
    if kind in ("water", "water_block", "bridge", "pier"):
        return "ev_water", WH
    if kind in ("plaza", "plaza_edge", "fountain", "crystal") or (kind in ("lantern", "mushroom") and island_in(x, z)):
        return "ev_marble", G
    if kind in ("cobble", "warp_w", "warp_e"):
        return "ev_cobble", G
    if kind in ("tallgrass", "spiral_grass"):
        return "ev_tgrass", G
    if kind == "spiral_flw":
        return "ev_spiral_flw", G
    return "ev_grass", G


STEP_X = 101.6                   # East Surf Landing: plaza to x 101.6, then two moonstone steps down to the water


def build_ground(F, t):
    cells = {}
    for (x, z) in t:
        m, h = ground_mat(t, x, z)
        cells[(x, z)] = (m, h, chunk_of_x(x), t[(x, z)][2] == "plaza_edge")
    used = set()
    for (x, z) in sorted(cells, key=lambda p: (p[1], p[0])):
        if (x, z) in used:
            continue
        k = cells[(x, z)]
        w = 1
        while (x + w, z) not in used and cells.get((x + w, z)) == k:
            w += 1
        d = 1
        while all((x + i, z + d) not in used and cells.get((x + i, z + d)) == k for i in range(w)):
            d += 1
        for i in range(w):
            for j in range(d):
                used.add((x + i, z + j))
        m, h, _, edge = k
        F.flat(m, x, z, (STEP_X if edge else x + w), z + d, h)
    # octagon chamfers: the plaza continues to the diagonal x+z = 835 / x-z = -645 / z-x = 669 / x+z = 859
    for p in chamfer_triangles():
        F.add("ev_marble", p, [planar(q) for q in p], facing=(0, 1, 0), group="ground", solid=False)
    # Surf landing steps (x 101.6..102): two treads and their risers, ev_cliff risers
    z0, z1 = layout.EAST_SURF_LANDING[0][1], layout.EAST_SURF_LANDING[-1][1] + 1
    for (xa, xb, h) in ((STEP_X, 101.8, -0.17), (101.8, 102.0, -0.34)):
        F.flat("ev_marble", xa, z0, xb, z1, h)
        F.wall("ev_cliff", (xa, z1), (xa, z0), h, h + 0.17 if h > -0.2 else -0.17, ((z0 - OZ) * 0.5, 0.0, (z1 - OZ) * 0.5, 0.2),
               group="curb", solid=False)
    F.wall("ev_cliff", (102.0, z1), (102.0, z0), WH, -0.34, (0, 0.8, 2, 1.0), group="curb", solid=False)


def chamfer_triangles():
    x0, z0, x1, z1 = layout.CENTRAL_ISLAND_RECT
    X1, Z1 = x1 + 1, z1 + 1
    tris = []
    # NW: diagonal (x0, z0+2) - (x0+2, z0); half-tiles (x0, z0+1) and (x0+1, z0)
    tris.append([(x0, G, z0 + 2), (x0 + 1, G, z0 + 1), (x0 + 1, G, z0 + 2)])
    tris.append([(x0 + 1, G, z0 + 1), (x0 + 2, G, z0), (x0 + 2, G, z0 + 1)])
    # NE
    tris.append([(X1 - 2, G, z0), (X1 - 1, G, z0 + 1), (X1 - 2, G, z0 + 1)])
    tris.append([(X1 - 1, G, z0 + 1), (X1, G, z0 + 2), (X1 - 1, G, z0 + 2)])
    # SW
    tris.append([(x0, G, Z1 - 2), (x0 + 1, G, Z1 - 2), (x0 + 1, G, Z1 - 1)])
    tris.append([(x0 + 1, G, Z1 - 1), (x0 + 2, G, Z1 - 1), (x0 + 2, G, Z1)])
    # SE
    tris.append([(X1 - 1, G, Z1 - 2), (X1, G, Z1 - 2), (X1 - 1, G, Z1 - 1)])
    tris.append([(X1 - 2, G, Z1 - 1), (X1 - 1, G, Z1 - 1), (X1 - 2, G, Z1)])
    return tris


def chamfer_tiles():
    x0, z0, x1, z1 = layout.CENTRAL_ISLAND_RECT
    out = set()
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if not island_in(x, z):
                out.add((x, z))
    return out


def build_curbs(F, t):
    """Vertical ev_cliff faces where land (h 0) meets water (h -0.5), merged into runs along each edge line. Faces
    turned away from the field camera (land south of water) are not emitted."""
    land = lambda k: k not in ("water", "water_block") and k not in ("bridge", "pier")  # noqa: E731
    cut = chamfer_tiles()
    landing = set(layout.EAST_SURF_LANDING)
    edges = {"s": set(), "e": set(), "w": set()}
    for (x, z), (_, h, kind) in t.items():
        if not land(kind):
            continue
        for d, (dx, dz) in (("s", (0, 1)), ("e", (1, 0)), ("w", (-1, 0))):
            nb = t.get((x + dx, z + dz))
            if nb is None or nb[2] not in ("water", "water_block") or (x + dx, z + dz) in cut:
                continue
            if d == "e" and (x, z) in landing:
                continue
            edges[d].add((x, z))
    for d, cells in edges.items():
        if d == "s":
            runs = runs_of(cells, "x")
            for z, a, b in runs:
                for p, q in split96(a, b + 1):
                    F.wall("ev_cliff", (p, z + 1), (q, z + 1), WH, G, ((p - OX) * UVR, 0.0, (q - OX) * UVR, 0.25),
                           group="curb", solid=False)
        else:
            for x, a, b in runs_of(cells, "z"):
                xe = x + 1 if d == "e" else x
                pa, pb = ((xe, b + 1), (xe, a)) if d == "e" else ((xe, a), (xe, b + 1))
                F.wall("ev_cliff", pa, pb, WH, G, ((a - OZ) * UVR, 0.0, (b + 1 - OZ) * UVR, 0.25), group="curb",
                       solid=False)
    # the island's south-west and south-east diagonals (the north ones face away from the camera)
    x0, z0, x1, z1 = layout.CENTRAL_ISLAND_RECT
    X1, Z1 = x1 + 1, z1 + 1
    F.wall("ev_cliff", (x0, Z1 - 2), (x0 + 2, Z1), WH, G, (0, 0, 1.4, 0.25), group="curb", solid=False)
    F.wall("ev_cliff", (X1 - 2, Z1), (X1, Z1 - 2), WH, G, (0, 0, 1.4, 0.25), group="curb", solid=False)
    # a low moonstone terrace lip round the plaza's visible straight edges (inside the outer 0.1 of the tiles)
    lip = 0.07
    F.box("ev_cliff", x0 + 2, Z1 - 0.1, X1 - 2, Z1, G, G + lip, (0, 0.0, 5, 0.1), sides="st", group="curb",
          top_uv=(0, 0, 5, 0.05))
    F.box("ev_cliff", x0, z0 + 2, x0 + 0.1, z0 + 7, G, G + lip, (0, 0, 2.5, 0.1), sides="wt", group="curb",
          top_uv=(0, 0, 0.05, 2.5))
    F.box("ev_cliff", X1 - 0.1, z0 + 2, X1, z0 + 6, G, G + lip, (0, 0, 2, 0.1), sides="et", group="curb",
          top_uv=(0, 0, 0.05, 2))


def runs_of(cells, axis):
    """Group cells into maximal runs along axis: [(fixed, start, end)]."""
    out = []
    if axis == "x":
        rows = {}
        for x, z in cells:
            rows.setdefault(z, []).append(x)
        for z, xs in rows.items():
            xs.sort()
            s = p = xs[0]
            for x in xs[1:] + [None]:
                if x is not None and x == p + 1:
                    p = x
                    continue
                out.append((z, s, p))
                if x is not None:
                    s = p = x
    else:
        cols = {}
        for x, z in cells:
            cols.setdefault(x, []).append(z)
        for x, zs in cols.items():
            zs.sort()
            s = p = zs[0]
            for z in zs[1:] + [None]:
                if z is not None and z == p + 1:
                    p = z
                    continue
                out.append((x, s, p))
                if z is not None:
                    s = p = z
    return out


def split96(a, b):
    return [(a, 96), (96, b)] if a < 96 < b else [(a, b)]


# ---------------------------------------------------------------------------------------------------------------
# blossom forest: canopy heightfield + edge crowns
# ---------------------------------------------------------------------------------------------------------------

CANOPY_H, CANOPY_EDGE = 1.85, 1.2


def crown_windows(w=12, h=10):
    """The brightest sakura-dominant and wisteria-dominant w x h texel windows of ev_blossom (outside the bark
    box), as UV rects: crowns sample blossom clusters, not the plum shade between them."""
    idx, pal = TM.tex_blossom()
    lum = [0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] for c in pal]
    best = {"pink": [], "lav": []}
    bx0, by0, _, _ = TM.BARK
    for y0 in range(0, 32 - h + 1, 2):
        for x0 in range(0, 32 - w + 1, 2):
            if x0 + w > bx0 and y0 + h > by0:
                continue
            cells = [int(idx[y, x]) for y in range(y0, y0 + h) for x in range(x0, x0 + w)]
            L = sum(lum[c] for c in cells) / len(cells)
            pink = sum(1 for c in cells if 3 <= c <= 7) / len(cells)
            lav = sum(1 for c in cells if 8 <= c <= 12) / len(cells)
            best["pink" if pink > lav else "lav"].append((L * (0.5 + max(pink, lav)), x0, y0))
    out = []
    for k in ("pink", "lav"):
        for _, x0, y0 in sorted(best[k], reverse=True)[:2]:
            out.append((x0 / 32, y0 / 32, (x0 + w) / 32, (y0 + h) / 32))
    return out


CROWN_WINDOWS = crown_windows()


def is_tree(t, x, z):
    v = t.get((x, z))
    return v is None or v[2] == "tree"            # outside the route: forest continues into the neighbours


def build_forest(F, t):
    """Blossom canopy heightfield over every tree tile (2x2 cells deep in the forest, 1x1 near its edges, the
    cells' edge midpoints interpolated so there are no cracks), then rounded crowns on alternate forest-edge trees
    that face the glade (south / east / west), each with a plum trunk."""
    trees = {k for k, v in t.items() if v[2] == "tree"}
    near_edge = {(x, z) for x, z in trees if any(not is_tree(t, x + a, z + b) for a in (-1, 0, 1) for b in (-1, 0, 1))}
    blocks = set()
    for x, z in trees:
        if x % 2 == 0 and z % 2 == 0 and all((x + a, z + b) in trees and (x + a, z + b) not in near_edge
                                             for a in (0, 1) for b in (0, 1)) and chunk_of_x(x) == chunk_of_x(x + 1):
            blocks.add((x, z))
    in_block = {(x + a, z + b) for x, z in blocks for a in (0, 1) for b in (0, 1)}

    def corner_h(cx, cz):
        n = sum(is_tree(t, cx - a, cz - b) for a in (0, 1) for b in (0, 1))
        if n < 4:
            return CANOPY_EDGE + 0.08 * (hash01(cx, cz, 7) - 0.5)
        return CANOPY_H + 0.42 * (hash01(cx, cz, 3) - 0.5) + 0.18 * math.sin(cx * 0.9 + cz * 0.6)

    H = {}
    for x, z in trees:
        for a in (0, 1):
            for b in (0, 1):
                H.setdefault((x + a, z + b), corner_h(x + a, z + b))
    for x, z in blocks:                       # edge midpoints of the 2x2 cells follow the cell edges (no cracks)
        for (mx, mz), (p, q) in (((x + 1, z), ((x, z), (x + 2, z))), ((x + 1, z + 2), ((x, z + 2), (x + 2, z + 2))),
                                 ((x, z + 1), ((x, z), (x, z + 2))), ((x + 2, z + 1), ((x + 2, z), (x + 2, z + 2)))):
            H[(mx, mz)] = (H[p] + H[q]) / 2

    def nrm(cx, cz):
        hl, hr = H.get((cx - 1, cz), H[(cx, cz)]), H.get((cx + 1, cz), H[(cx, cz)])
        hu, hd = H.get((cx, cz - 1), H[(cx, cz)]), H.get((cx, cz + 1), H[(cx, cz)])
        return GF.norm((hl - hr, 1.4, hu - hd))

    def cell(x0, z0, s):
        cs = [(x0, z0 + s), (x0 + s, z0 + s), (x0 + s, z0), (x0, z0)]
        pts = [(cx, H[(cx, cz)], cz) for cx, cz in cs]
        F.add("ev_blossom", pts, [planar(p) for p in pts], normals=[nrm(cx, cz) for cx, cz in cs], facing=(0, 1, 0),
              chunk=chunk_of_x(x0), group="canopy", solid=False)
    for x, z in sorted(blocks):
        cell(x, z, 2)
    for x, z in sorted(trees - in_block):
        cell(x, z, 1)
    n_crowns = 0
    bark = GF.uvbox(TM.BARK)
    for x, z in sorted(trees):
        open_dirs = [(dx, dz) for dx, dz in ((0, 1), (1, 0), (-1, 0))
                     if (x + dx, z + dz) in t and t[(x + dx, z + dz)][2] not in ("tree", "gate_pad")]
        if not open_dirs or (x + z) % 2:
            continue
        ox = sum(d[0] for d in open_dirs) * 0.14
        oz = sum(d[1] for d in open_dirs) * 0.14
        cx, cz = x + 0.5 + ox, z + 0.5 + oz
        r = 0.66 + 0.1 * hash01(x, z, 11)
        top = 2.15 + 0.3 * hash01(x, z, 13)
        win = CROWN_WINDOWS[int(hash01(x, z, 17) * len(CROWN_WINDOWS))]
        GF.lathe(F, "ev_blossom", (cx, cz), [(r * 0.72, 0.8), (r, 1.28), (r * 0.66, top - 0.28), (0.0, top)], 6, win, ang0=hash01(x, z, 19) * 1.2, group="crowns",
                 solid=False, chunk=chunk_of_x(x))
        F.wall("ev_blossom", (cx - 0.08, cz + 0.12), (cx + 0.08, cz + 0.12), 0.0, 0.9, bark, group="crowns", solid=False)
        n_crowns += 1
    return n_crowns, len(blocks)


# ---------------------------------------------------------------------------------------------------------------
# bridge, pier, lanterns, mushrooms, spiral blossoms, Rift Conduit
# ---------------------------------------------------------------------------------------------------------------

PLANK = (0.0, 0.0, 1.0, 0.74)
TRIM = (0.0, 24.5 / 32, 1.0, 31.5 / 32)


def rail(F, xa, xb, z, h_of, segs, group, posts=(0, -1), mid=True):
    """Rose-gold hand-rail along z from xa to xb (front face + top, following h_of), silver posts."""
    xs = [xa + (xb - xa) * s / segs for s in range(segs + 1)]
    for s in range(segs):
        p, q = xs[s], xs[s + 1]
        hp, hq = h_of(p), h_of(q)
        F.add("ev_bridge", [(p, hp + 0.06, z), (q, hq + 0.06, z), (q, hq - 0.04, z), (p, hp - 0.04, z)],
              [(s * 0.5, TRIM[1]), ((s + 1) * 0.5, TRIM[1]), ((s + 1) * 0.5, TRIM[3]), (s * 0.5, TRIM[3])],
              facing=(0, 0, 1), group=group, solid=False)
        if mid:
            F.add("ev_bridge", [(p, hp * 0.5 + 0.03, z), (q, hq * 0.5 + 0.03, z), (q, hq * 0.5 - 0.03, z),
                                (p, hp * 0.5 - 0.03, z)], [(0, 0.1), (1, 0.1), (1, 0.15), (0, 0.15)],
                  facing=(0, 0, 1), group=group, solid=False)
    for k in posts:
        p = xs[k]
        F.box("ev_bridge", p - 0.05, z - 0.05, p + 0.05, z + 0.05, 0.0, h_of(p) + 0.12, (0.0, 0.1, 0.12, 0.7),
              sides="st", group=group, solid=False, top_uv=(0.4, 0.8, 0.5, 0.86))


def build_bridge(F):
    x0, z0, x1, z1 = layout.WEST_BRIDGE_RECT
    X1, Z1 = x1 + 1, z1 + 1
    L = X1 - x0
    F.add("ev_bridge", [(x0, G, Z1), (X1, G, Z1), (X1, G, z0), (x0, G, z0)],
          [(0, 0.74), (L * UVR * 2, 0.74), (L * UVR * 2, 0.0), (0, 0.0)], facing=(0, 1, 0), group="bridge", solid=False)
    arch = lambda x: WH + 0.06 + 0.30 * math.sin(math.pi * (x - x0) / L)  # noqa: E731
    segs = 6
    for s in range(segs):                     # the arched south fascia (water shows under the arch)
        p, q = x0 + L * s / segs, x0 + L * (s + 1) / segs
        F.add("ev_bridge", [(p, G, Z1), (q, G, Z1), (q, arch(q), Z1), (p, arch(p), Z1)],
              [(s * 0.25, 0.0), ((s + 1) * 0.25, 0.0), ((s + 1) * 0.25, 0.25), (s * 0.25, 0.25)], facing=(0, 0, 1),
              group="bridge", solid=False)
    F.wall("ev_bridge", (x0, Z1 + 0.02), (X1, Z1 + 0.02), G - 0.06, G + 0.04, (0, TRIM[1], L, TRIM[3]),
           group="bridge", solid=False)
    rh = lambda x: 0.52 + 0.18 * math.sin(math.pi * (x - x0) / L)  # noqa: E731
    rail(F, x0, X1, z0 - 0.06, rh, 4, "bridge", posts=(0, 2, 4), mid=False)
    rail(F, x0, X1, Z1 + 0.06, rh, 4, "bridge", posts=(0, 2, 4))
    for lx, lz in ((x0 + 0.2, z0 - 0.25), (X1 - 0.2, z0 - 0.25), (x0 + 0.2, Z1 + 0.25), (X1 - 0.2, Z1 + 0.25)):
        lantern(F, lx, lz, group="bridge")


def build_pier(F):
    x0, z0, x1, z1 = layout.EAST_PIER_RECT
    X1, Z1 = x1 + 1, z1 + 1
    L = X1 - x0
    F.add("ev_bridge", [(x0, G, Z1), (X1, G, Z1), (X1, G, z0), (x0, G, z0)],
          [(0, 0.74), (L * UVR * 2, 0.74), (L * UVR * 2, 0.0), (0, 0.0)], facing=(0, 1, 0), group="pier", solid=False)
    F.wall("ev_bridge", (x0, Z1), (X1, Z1), G - 0.14, G, (0, TRIM[1], L, TRIM[3]), group="pier", solid=False)
    F.wall("ev_bridge", (x0, z0), (x0, Z1), G - 0.14, G, (0, TRIM[1], 1.5, TRIM[3]), group="pier", solid=False)
    for px in (x0 + 0.12, x0 + 1.75, x0 + 3.4):
        F.box("ev_bridge", px - 0.08, Z1 - 0.14, px + 0.08, Z1 - 0.02, WH - 0.05, G - 0.14, (0.25, 0.0, 0.4, 0.7),
              sides="sw", group="pier", solid=False)
    rh = lambda x: 0.55  # noqa: E731
    rail(F, x0 + 1.0, X1, z0 - 0.06, rh, 2, "pier", posts=(0, 1, 2), mid=False)
    rail(F, x0 + 1.0, X1, Z1 + 0.06, rh, 2, "pier", posts=(0, 1, 2))


def lantern(F, x, z, group="lanterns"):
    """Fairy lantern: moonstone foot, slender silver post, warm unlit glow head, rose-gold pyramid cap."""
    F.box("ev_cliff", x - 0.12, z - 0.12, x + 0.12, z + 0.12, 0.0, 0.12, (0, 0, 0.25, 0.1), sides="st", group=group,
          top_uv=(0, 0, 0.2, 0.2))
    F.box("ev_bridge", x - 0.0625, z - 0.0625, x + 0.0625, z + 0.0625, 0.12, 1.25, (0.0, 0.0, 0.1, 0.7), sides="sew",
          group=group)
    glow = GF.uvbox(TM.MUSH_UV["glow"])
    hot = lambda n, h: (255, 246, 220) if n[1] > 0.5 else (252, 230, 190)  # noqa: E731
    F.box("u_mushroom", x - 0.125, z - 0.125, x + 0.125, z + 0.125, 1.25, 1.5, glow, color=hot, sides="sewt",
          group=group)
    GF.lathe(F, "ev_bridge", (x, z), [(0.27, 1.5), (0.0, 1.72)], 4, (0.0, TRIM[1], 1.0, TRIM[3]), ang0=math.pi / 4,
             group=group)


def build_lanterns(F, t):
    n = 0
    for (x, z), v in sorted(t.items()):
        if v[2] == "lantern":
            lantern(F, x + 0.5, z + 0.55)
            n += 1
    return n


def mushroom(F, x, z, r, hs, tint, group="mushrooms"):
    """Glowing fairy mushroom: a 5-segment cap (unlit, magenta or cyan-tinted, cyan spots) on a pale stem card."""
    cap = GF.uvbox(TM.MUSH_UV["cap"])
    stem = GF.uvbox(TM.MUSH_UV["stem"])
    sw = max(0.0625, r * 0.3)
    F.wall("u_mushroom", (x - sw, z + 0.02), (x + sw, z + 0.02), 0.0, hs + 0.02, stem,
           colors=[(236, 230, 250), (236, 230, 250), (170, 160, 200), (170, 160, 200)], group=group, solid=True)
    GF.lathe(F, "u_mushroom", (x, z), [(r, hs), (r * 0.62, hs + 0.13), (0.0, hs + 0.2)], 5, cap,
             color=lambda n, h, j, i: GF.bake(n, h, 0.85 + 0.06 * i, tint=tint, water_h=-1, bounce=0, glow=0.10,
                                              cap=1.0),
             group=group)


def build_mushrooms(F, t):
    n = 0
    for (x, z), v in sorted(t.items()):
        if v[2] != "mushroom":
            continue
        cyan = hash01(x, z, 5) < 0.5
        tint = (0.62, 1.0, 1.05) if cyan else (1.0, 1.0, 1.0)
        mushroom(F, x + 0.56, z + 0.6, 0.28, 0.3, tint)
        if hash01(x, z, 9) < 0.45:
            mushroom(F, x + 0.22, z + 0.3, 0.17, 0.18, (1.0, 1.0, 1.0) if cyan else (0.62, 1.0, 1.05))
        n += 1
    return n


def spiral_value(px, pz):
    cx, cz = layout.SPIRAL_MEADOW_CENTER
    dx, dz = px - cx, pz - cz
    return math.sin(3.0 * math.atan2(dz, dx) - 1.55 * math.hypot(dx, dz))


SPIRAL_T = 0.84


def build_spiral(F, t):
    """Glowing pixel blossoms on the arms of the meadow's spiral: flat unlit decals (0.4 tile) mapped onto the
    pink / cyan / gold blossom sprites of ev_spiral_flw, sampled on a half-tile lattice where
    sin(3 theta - 1.55 r) > 0.78."""
    meadow = {k for k, v in t.items() if v[2] in ("tallgrass", "spiral_grass", "spiral_flw")
              and 74 <= k[0] <= 86 and 756 <= k[1] <= 763}
    n = 0
    names = ["pink", "cyan", "gold"]
    for (x, z) in sorted(meadow):
        for a in (0.25, 0.75):
            for b in (0.25, 0.75):
                px, pz = x + a, z + b
                if spiral_value(px, pz) < SPIRAL_T:
                    continue
                jx, jz = (hash01(px * 4, pz * 4, 1) - 0.5) * 0.12, (hash01(px * 4, pz * 4, 2) - 0.5) * 0.12
                name = names[int(hash01(px * 4, pz * 4, 3) * 3)]
                box = GF.uvbox(TM.BLOSSOMS[name])
                s = 0.2
                F.flat("u_blossom", px + jx - s, pz + jz - s, px + jx + s, pz + jz + s, G + 0.0625, group="spiral",
                       uv=box, colors=[(255, 255, 255)] * 4)
                n += 1
    return n


def build_crystal(F):
    """Rift Conduit Crystal Pillar on (98..99, 747): hexagonal violet-cyan obelisk, four angled side shards, a
    moonstone plinth with a glowing rune ring; all unlit with baked glow (violet core to cyan tips)."""
    x0, z0, x1, z1 = layout.CRYSTAL_RECT
    cx, cz = (x0 + x1 + 1) / 2.0, z0 + 0.5
    C = (cx, cz)
    grp = dict(group="crystal")
    GF.lathe(F, "u_marble", C, [(0.47, 0.0), (0.47, 0.12), (0.42, 0.15)], 6, (0, 0, 1, 0.2), ang0=math.pi / 6,
             color=lambda n, h, j, i: GF.bake(n, h, 0.85, water_h=-1, bounce=0), **grp)
    ring = GF.uvbox((0, 0, 32, 32))
    GF.disc(F, "u_crystal", C, 0.42, 0.33, 0.152, 6, ring, ang0=math.pi / 6,
            color=lambda n, h, d: (150, 250, 255), solid=False, **grp)
    GF.disc(F, "u_marble", C, 0.33, 0.0, 0.15, 6, (0.3, 0.3, 0.7, 0.7), ang0=math.pi / 6,
            color=lambda n, h, d: (200, 196, 240), solid=False, **grp)

    def glow(n, h, *a):
        f = min(1.0, h / 2.4)
        base = GF.bake(n, h, 1.0, water_h=-1, bounce=0, glow=0.08, cap=1.0)
        tint = (0.95 - 0.25 * f, 0.75 + 0.25 * f, 1.0)
        return tuple(min(255, int(base[k] * tint[k] + 30 * f)) for k in range(3))
    GF.lathe(F, "u_crystal", C, [(0.24, 0.15), (0.29, 0.55), (0.23, 1.85), (0.0, 2.5)], 6, (0, 0, 1, 1), ang0=0.2,
             color=lambda n, h, j, i: glow(n, h), **grp)
    for k, (ang, tilt, ln, r) in enumerate(((1.25, 0.55, 0.85, 0.09), (1.95, 0.45, 0.6, 0.075), (-1.2, 0.5, 0.8, 0.085),
                                            (-2.0, 0.6, 0.55, 0.07))):
        bx, bz = cx + 0.26 * math.sin(ang), cz + 0.18 * math.cos(ang)
        dx, dy, dz = math.sin(ang) * math.sin(tilt), math.cos(tilt), math.cos(ang) * math.sin(tilt) * 0.55
        ax = GF.norm((dx, dy, dz))
        tip = (bx + ax[0] * ln, 0.15 + ax[1] * ln, bz + ax[2] * ln)
        e1 = GF.norm(GF.cross(ax, (0, 0, 1)))
        e2 = GF.norm(GF.cross(e1, ax))
        base = [(bx + r * (math.cos(a) * e1[0] + math.sin(a) * e2[0]), 0.15 + r * (math.cos(a) * e1[1] + math.sin(a) * e2[1]),
                 bz + r * (math.cos(a) * e1[2] + math.sin(a) * e2[2])) for a in (0.0, 1.571, 3.142, 4.712)]
        for q in range(4):
            tri = [base[q], base[(q + 1) % 4], tip]
            n = GF.face_n(tri)
            mid = tuple(sum(p[c] for p in tri) / 3 for c in range(3))
            if GF.dot(n, GF.sub(mid, (bx, 0.15 + ln * 0.3, bz))) < 0:
                tri, n = tri[::-1], tuple(-c for c in n)
            if not GF.visible(n):
                continue
            F.add("u_crystal", tri, [(0.1, 0.9), (0.4, 0.9), (0.25, 0.1)], colors=[glow(n, p[1]) for p in tri],
                  facing=n, **grp)


# ---------------------------------------------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------------------------------------------

def art_faces():
    t = layout.tiles()
    F = Art()
    build_ground(F, t)
    build_curbs(F, t)
    info = {}
    info["crowns"], info["canopy_blocks"] = build_forest(F, t)
    build_bridge(F)
    build_pier(F)
    info["lanterns"] = build_lanterns(F, t)
    info["mushrooms"] = build_mushrooms(F, t)
    info["spiral_blossoms"] = build_spiral(F, t)
    build_crystal(F)
    info["fountain"] = GF.build(F)
    return F, info


def stock_gate_props():
    out = {}
    for c in layout.CHUNKS:
        raw = subprocess.run(["git", "-C", ROOT, "show", f"HEAD:{OUT_MAP_DIR}/map_data_{c:03d}.bin"], check=True,
                             capture_output=True).stdout
        out[c] = [p for p in mapdata.read_props(mapdata.unpack(raw)["props"]) if p["model"] == 40]
    return out


def build():
    tex = TM.build_set()
    textures = {name: {"size": list(size), "palette": pal} for name, (pal, size) in tex["table"].items()}
    F, info = art_faces()
    out = {}
    for c, cell in layout.CHUNKS.items():
        mesh = F.mesh(c)
        model = nsbmd.mesh_to_model(mesh, cell, name=mesh["name"], textures=textures)
        nsb = nsbmd.build_bmd([model])
        perm = collision.permissions(c)
        bd = collision.bdhc(c)
        props = mapdata.write_props(layout.GATE_PROPS[c])
        data = mapdata.pack(perm, props, nsb, bd)
        out[c] = dict(model=model, nsb=nsb, perm=perm, bdhc=bd, props=props, data=data, mesh=mesh)
    return out, F, info, tex


# ---------------------------------------------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------------------------------------------

def floor_check(out, t):
    """Every walkable tile: the highest drawn horizontal face over its centre (below +0.6) sits at its height."""
    faces = {}
    for c, o in out.items():
        mesh = nsbmd.model_to_mesh(nsbmd.parse_bmd(o["nsb"])["models"][0], layout.CHUNKS[c])
        for me in mesh["meshes"]:
            P = me["positions"]
            for f in me["quads"] + me["tris"]:
                vs = [P[i] for i in f]
                if max(v[1] for v in vs) - min(v[1] for v in vs) > 1e-3:
                    continue
                for tx in range(math.floor(min(v[0] for v in vs)), math.ceil(max(v[0] for v in vs))):
                    for tz in range(math.floor(min(v[2] for v in vs)), math.ceil(max(v[2] for v in vs))):
                        if point_in_poly(tx + 0.5, tz + 0.5, [(v[0], v[2]) for v in vs]):
                            faces.setdefault((tx, tz), []).append(vs[0][1])
    bad = []
    for (x, z), v in t.items():
        if v[0] & layout.BLOCK:
            continue
        hs = [h for h in faces.get((x, z), []) if h <= v[1] + 0.6]
        if not hs or abs(max(hs) - v[1]) > 0.05:
            bad.append((x, z))
    return bad


def point_in_poly(px, pz, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        (x0, z0), (x1, z1) = poly[i], poly[(i + 1) % n]
        if (z0 > pz) != (z1 > pz):
            xi = x0 + (pz - z0) * (x1 - x0) / (z1 - z0)
            if px < xi:
                inside = not inside
    return inside


def clearance_check(F, t):
    """Nothing solid inside a walkable tile's inner 0.8 x 0.8 below 1.3 tiles above its floor."""
    bad = set()
    walk = {k for k, v in t.items() if not v[0] & layout.BLOCK}
    for pts in F.solids:
        samples = list(pts) + [tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))]
        samples += [tuple((pts[i][k] + pts[(i + 1) % len(pts)][k]) / 2 for k in range(3)) for i in range(len(pts))]
        for x, h, z in samples:
            tx, tz = math.floor(x), math.floor(z)
            if (tx, tz) in walk and 0.1 < x - tx < 0.9 and 0.1 < z - tz < 0.9 and h < t[(tx, tz)][1] + 1.3:
                bad.add((tx, tz))
    return sorted(bad)


def run_checks(out, F, info, tex):
    t = layout.tiles()
    res = []
    for desc, ok in layout.checks():
        res.append(("layout: " + desc, ok))
    set_parsed = nsbtx.parse(tex["bytes"])
    T = {x["name"]: x for x in set_parsed["textures"]}
    P = {x["name"] for x in set_parsed["palettes"]}
    for c, o in out.items():
        sec = mapdata.unpack(o["data"])
        res.append((f"chunk {c}: map_data sections unpack (perm {len(sec['permissions'])}, props {len(sec['props'])}, "
                    f"model {len(sec['model'])}, BDHC {len(sec['bdhc'])} B)",
                    len(sec["permissions"]) == 2048 and sec["model"] == o["nsb"] and sec["bdhc"] == o["bdhc"]))
        offp = collision.check_permissions(c, sec["permissions"])
        res.append((f"chunk {c}: permissions equal the layout ({len(offp)} off)", not offp))
        offh = collision.check_bdhc(c, sec["bdhc"])
        res.append((f"chunk {c}: BDHC height at every tile centre equals the layout ({len(offh)} off)", not offh))
        b = mapdata.read_bdhc(sec["bdhc"])
        res.append((f"chunk {c}: BDHC {len(sec['bdhc'])} B <= {BDHC_BUFFER} ({len(b['plates'])} plates, "
                    f"{len(b['strips'])} strips)", len(sec["bdhc"]) <= BDHC_BUFFER))
        res.append((f"chunk {c}: model {len(o['nsb'])} B <= {MODEL_BUFFER} (MAP_MODEL_FILE_SIZE)",
                    len(o["nsb"]) <= MODEL_BUFFER))
        back = nsbmd.parse_bmd(o["nsb"])
        res.append((f"chunk {c}: NSBMD parse -> rebuild byte-identical", nsbmd.build_bmd(back["models"]) == o["nsb"]))
        bad = []
        for m in back["models"][0]["materials"]:
            tx = T.get(m["texture"])
            if not tx or m["palette"] not in P or (tx["w"], tx["h"]) != (m["orig_width"], m["orig_height"]):
                bad.append(m["name"])
        res.append((f"chunk {c}: all {len(back['models'][0]['materials'])} materials' textures + palettes exist in "
                    f"set 077 with matching sizes (bad: {bad})", not bad))
        props = mapdata.read_props(sec["props"])
        res.append((f"chunk {c}: gatehouse props identical to stock HEAD ({len(props)} x model 40)",
                    props == stock_gate_props()[c]))
    fl = floor_check(out, t)
    res.append((f"every walkable tile is drawn at its layout height ({len(fl)} off: {fl[:6]})", not fl))
    cl = clearance_check(F, t)
    res.append((f"nothing solid drawn low over a walkable tile ({len(cl)}: {cl[:8]})", not cl))
    fb = F.bounds["fountain"]
    fx0, fz0, fx1, fz1 = layout.FOUNTAIN_RECT
    res.append((f"fountain inside its blocked rect x {fx0}..{fx1 + 1}, z {fz0}..{fz1 + 1} "
                f"(x {fb[0]:.2f}..{fb[2]:.2f}, z {fb[1]:.2f}..{fb[3]:.2f}, top h {fb[4]:.2f})",
                fb[0] >= fx0 and fb[2] <= fx1 + 1 and fb[1] >= fz0 and fb[3] <= fz1 + 1))
    res.append((f"fountain entirely in map_data_050 (chunks {sorted(F.group_chunks['fountain'])}); statue centre "
                f"x {GF.CX} < 96", F.group_chunks["fountain"] == {50} and GF.CX < 96))
    cb = F.bounds["crystal"]
    cx0, cz0, cx1, cz1 = layout.CRYSTAL_RECT
    res.append((f"Rift Conduit inside its rect x {cx0}..{cx1 + 1}, z {cz0}..{cz1 + 1} (x {cb[0]:.2f}..{cb[2]:.2f}, "
                f"z {cb[1]:.2f}..{cb[3]:.2f}) and in map_data_051", cb[0] >= cx0 and cb[2] <= cx1 + 1 and cb[1] >= cz0
                and cb[3] <= cz1 + 1 and F.group_chunks["crystal"] == {51}))
    for f in tex["fails"]:
        res.append(("set 077: " + f, False))
    ltext, lfails = build_lighting()
    for f in lfails:
        res.append((f, False))
    res.append((f"lighting_set_005: {len(json.loads(ltext))} time blocks, lighting_set_000 schema, 5-bit colours, "
                f"stock directions and lights 1..3", not lfails))
    vb, vo = tex["vram"]
    res.append((f"set 077: 12 textures round-trip, stock unchanged, VRAM {sum(vo)} B ({sum(vo) / 1024:.1f} KB) <= "
                f"{TM.VRAM_TARGET // 1024} KB target (budget {TM.VRAM_BUDGET // 1024} KB)", not tex["fails"]))
    return res


# ---------------------------------------------------------------------------------------------------------------
# lighting_set_005: the Everspring twilight-fairy curve
# ---------------------------------------------------------------------------------------------------------------

LIGHTING_REL = "res/field/lighting/lighting_set_005.json"
LIGHTING_TEMPLATE = "res/field/lighting/lighting_set_000.json"   # stock schema, block times, sun directions
# endTime (2 s units, 43200 = 24:00) -> (light 0 RGB, diffuse, ambient, specular, emission), 5-bit 0..31.
# Night: moonlit indigo with a soft glow floor; dawn: rose-violet; day: bright, crisp lavender-tinted white (the
# light stays near-neutral so grass reads green and paths read pale, never muddy); evening: golden-lavender into
# rose-violet and indigo dusk. Lights 1..3 (sprites / other passes) and the light-0 directions stay stock.
NIGHT = ((12, 12, 21), (14, 13, 18), (10, 9, 14), (14, 13, 18), (9, 8, 14))
LIGHT_CURVE = {
    0: NIGHT,
    7200: NIGHT,                                                                         # 00:00-04:00 night
    8100: ((13, 12, 21), (12, 11, 16), (12, 11, 15), (10, 9, 15), (10, 9, 14)),          # 04:00-04:30 pre-dawn
    9000: ((16, 13, 21), (12, 11, 14), (11, 10, 13), (12, 11, 15), (13, 11, 15)),        # 04:30-05:00 rose dawn
    14400: ((19, 18, 24), (13, 13, 14), (9, 9, 10), (13, 13, 15), (14, 14, 17)),         # 05:00-08:00 lavender morning
    20700: ((22, 22, 25), (14, 14, 15), (9, 9, 11), (14, 14, 16), (14, 14, 16)),         # 08:00-11:30 day
    21600: ((24, 24, 26), (15, 15, 16), (10, 10, 11), (16, 16, 17), (14, 14, 15)),       # 11:30-12:00
    27000: ((25, 24, 27), (16, 16, 16), (10, 11, 12), (18, 18, 19), (14, 14, 15)),       # 12:00-15:00 peak
    27900: ((24, 22, 25), (15, 15, 16), (11, 11, 12), (17, 17, 18), (13, 13, 14)),       # 15:00-15:30
    30600: ((23, 20, 23), (15, 15, 15), (11, 11, 12), (17, 16, 17), (13, 12, 13)),       # 15:30-17:00 golden lavender
    32400: ((22, 17, 21), (15, 14, 15), (11, 11, 13), (16, 15, 17), (12, 10, 12)),       # 17:00-18:00 rose evening
    33300: ((20, 14, 20), (14, 13, 15), (12, 11, 13), (15, 14, 16), (11, 9, 12)),        # 18:00-18:30 rose-violet
    34200: ((17, 13, 21), (14, 13, 15), (12, 11, 14), (14, 13, 16), (10, 9, 13)),        # 18:30-19:00 violet dusk
    36000: ((13, 12, 21), (14, 13, 16), (11, 10, 14), (14, 13, 17), (9, 8, 13)),         # 19:00-20:00 indigo dusk
    43200: NIGHT,                                                                        # 20:00-24:00 moonlit night
}


def build_lighting():
    """-> (json text, fails). lighting_set_000 at HEAD supplies the schema; LIGHT_CURVE the colours."""
    raw = subprocess.run(["git", "-C", ROOT, "show", f"HEAD:{LIGHTING_TEMPLATE}"], check=True,
                         capture_output=True).stdout.decode()
    tmpl = json.loads(raw)
    fails = []
    out = json.loads(raw)
    rgb = lambda c: {"red": c[0], "green": c[1], "blue": c[2]}  # noqa: E731
    for blk in out:
        cur = LIGHT_CURVE.get(blk["endTime"])
        if cur is None:
            fails.append(f"lighting: no curve entry for endTime {blk['endTime']}")
            continue
        blk["lights"][0]["color"] = rgb(cur[0])
        for key, c in zip(("diffuseColor", "ambientColor", "specularColor", "emissionColor"), cur[1:]):
            blk[key] = rgb(c)
    text = json.dumps(out, indent=4) + "\n"
    back = json.loads(text)

    def shape(v):
        return {k: shape(x) for k, x in v.items()} if isinstance(v, dict) else [shape(x) for x in v] \
            if isinstance(v, list) else type(v).__name__
    if shape(back) != shape(tmpl) or [list(b.keys()) for b in back] != [list(b.keys()) for b in tmpl]:
        fails.append("lighting: schema differs from lighting_set_000")
    if [b["endTime"] for b in back] != [b["endTime"] for b in tmpl]:
        fails.append("lighting: block times differ from stock")
    for b in back:
        cols = [b[k] for k in ("diffuseColor", "ambientColor", "specularColor", "emissionColor")] + \
            [lt["color"] for lt in b["lights"]]
        if any(not (0 <= v <= 31) or not isinstance(v, int) for c in cols for v in c.values()):
            fails.append(f"lighting: colour out of 5-bit range at endTime {b['endTime']}")
        if [lt["direction"] for lt in b["lights"]] != [lt["direction"] for lt in tmpl[back.index(b)]["lights"]]:
            fails.append(f"lighting: light directions changed at endTime {b['endTime']}")
        if b["lights"][1:] != tmpl[back.index(b)]["lights"][1:]:
            fails.append(f"lighting: lights 1..3 changed at endTime {b['endTime']}")
    return text, fails


# ---------------------------------------------------------------------------------------------------------------
# preview: a small NumPy rasteriser with the field camera (CAMERA_TYPE_DEFAULT)
# ---------------------------------------------------------------------------------------------------------------

VIEWS = {"fountain": (95, 755), "approach": (76, 754), "meadow": (80, 759), "bridge": (85, 753),
         "crystal": (98, 750), "pier": (110, 753), "grove": (116, 757), "alcove": (77, 747)}


def render(out, tex, target, path, night=False, w=640, h=360, top=False, zoom=1.0, target_h=0.0):
    import numpy as np
    from PIL import Image
    texs = {}
    for name, idx, pal in tex["generated"]:
        texs[name] = np.array([pal[i] for i in idx.reshape(-1)], float).reshape(32, 32, 3) / 255.0
    pitch, dist, fovy = math.radians(59.05), 666.9, math.radians(8.09) * 2
    if top:
        pitch, dist, fovy = math.radians(89.0), 3000.0, math.radians(15.5)
    fovy = 2 * math.atan(math.tan(fovy / 2) / zoom)
    tx, tz = target
    tgt = np.array([(tx + 0.5) * 16, 16.0 + 16 * target_h, (tz + 0.5) * 16])
    cam = tgt + np.array([0, dist * math.sin(pitch), dist * math.cos(pitch)])
    fwd = (tgt - cam) / np.linalg.norm(tgt - cam)
    right = np.cross(fwd, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    f = 1 / math.tan(fovy / 2)
    img = np.zeros((h, w, 3))
    img[:] = (0.10, 0.08, 0.18) if night else (0.55, 0.62, 0.85)
    zb = np.full((h, w), np.inf)
    light = np.array([0.46, -0.88, -0.11]) * -1
    lc = (0.45, 0.42, 0.62) if night else (0.85, 0.82, 0.90)
    amb = (0.42, 0.40, 0.60) if night else (0.62, 0.60, 0.66)
    for c, o in out.items():
        mesh = nsbmd.model_to_mesh(nsbmd.parse_bmd(o["nsb"])["models"][0], layout.CHUNKS[c])
        mats = {m["name"]: m for m in mesh["materials"]}
        for me in mesh["meshes"]:
            m = mats[me["material"]]
            lit = m["polygon_attr"]["lights"] != 0
            two = m["polygon_attr"]["cull"] != "back"
            T = texs[m["texture"]]
            P = np.array(me["positions"]) * [16, 16, 16] + [0, 16, 0]
            UV = np.array(me["uvs"])
            CO = np.array(me["colors"], float) / 255.0
            NO = np.array([n if n else [0, 1, 0] for n in me["normals"]]) if me["normals"] else None
            rel = P - cam
            xc, yc, zc = rel @ right, rel @ up, rel @ fwd
            sx = w / 2 + xc / zc * f * h / 2
            sy = h / 2 - yc / zc * f * h / 2
            tris = [tuple(q) for q in me["tris"]] + [tri for q in me["quads"] for tri in ((q[0], q[1], q[2]), (q[0], q[2], q[3]))]
            for a, b, cc in tris:
                if min(zc[a], zc[b], zc[cc]) < 50:
                    continue
                x0, y0, x1, y1, x2, y2 = sx[a], sy[a], sx[b], sy[b], sx[cc], sy[cc]
                area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
                if area == 0 or (area > 0 and not two):
                    continue
                bx0, bx1 = max(int(min(x0, x1, x2)), 0), min(int(max(x0, x1, x2)) + 1, w)
                by0, by1 = max(int(min(y0, y1, y2)), 0), min(int(max(y0, y1, y2)) + 1, h)
                if bx0 >= bx1 or by0 >= by1:
                    continue
                gy, gx = np.mgrid[by0:by1, bx0:bx1] + 0.5
                w0 = ((x1 - gx) * (y2 - gy) - (x2 - gx) * (y1 - gy)) / area
                w1 = ((x2 - gx) * (y0 - gy) - (x0 - gx) * (y2 - gy)) / area
                w2 = 1 - w0 - w1
                msk = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
                if not msk.any():
                    continue
                iz = w0 / zc[a] + w1 / zc[b] + w2 / zc[cc]
                depth = 1 / iz
                sub = zb[by0:by1, bx0:bx1]
                msk &= depth < sub
                if not msk.any():
                    continue
                pu = (w0 * UV[a, 0] / zc[a] + w1 * UV[b, 0] / zc[b] + w2 * UV[cc, 0] / zc[cc]) * depth
                pv = (w0 * UV[a, 1] / zc[a] + w1 * UV[b, 1] / zc[b] + w2 * UV[cc, 1] / zc[cc]) * depth
                tc = T[(np.floor(pv * 32).astype(int)) % 32, (np.floor(pu * 32).astype(int)) % 32]
                if lit:                       # Gouraud, as the GX lights each vertex
                    sh = [np.array([amb[k] + lc[k] * 0.8 * max(0.0, float(np.dot(NO[v], light))) for k in range(3)])
                          for v in (a, b, cc)]
                    shade = w0[..., None] * sh[0] + w1[..., None] * sh[1] + w2[..., None] * sh[2]
                    col = tc * np.clip(shade, 0, 1.15)
                else:
                    vc = (w0[..., None] * CO[a] + w1[..., None] * CO[b] + w2[..., None] * CO[cc])
                    col = tc * vc
                reg = img[by0:by1, bx0:bx1]
                reg[msk] = np.clip(col[msk], 0, 1)
                sub[msk] = depth[msk]
    Image.fromarray((img * 255).astype("uint8")).resize((w * 2, h * 2), Image.NEAREST).save(path)


def write_preview(d, out, tex):
    os.makedirs(d, exist_ok=True)
    TM.write_preview(os.path.join(d, "tex"), tex["generated"])
    for name, tgt in VIEWS.items():
        render(out, tex, tgt, os.path.join(d, f"view_{name}.png"))
    render(out, tex, VIEWS["fountain"], os.path.join(d, "view_fountain_night.png"), night=True)
    render(out, tex, (95, 751), os.path.join(d, "top.png"), w=640, h=360, top=True)
    render(out, tex, (94.5, 750.5), os.path.join(d, "zoom_fountain.png"), zoom=3.2, target_h=1.4)
    render(out, tex, (94.5, 750.5), os.path.join(d, "zoom_fountain_night.png"), zoom=3.2, target_h=1.4, night=True)
    for c, o in out.items():
        json.dump(nsbmd.model_to_mesh(nsbmd.parse_bmd(o["nsb"])["models"][0], layout.CHUNKS[c]),
                  open(os.path.join(d, f"chunk_{c:03d}.mesh.json"), "w"))
    print("wrote previews to", d)


# ---------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    out, F, info, tex = build()
    res = run_checks(out, F, info, tex)
    TM.report(tex)
    print(f"\n{'chunk':>5} {'polys':>6} {'tris':>5} {'quads':>6} {'verts':>6} {'mats':>4} {'model B':>8} {'BDHC B':>7} "
          f"{'map_data B':>10}")
    total = 0
    for c, o in out.items():
        st = nsbmd.model_stats(o["model"])
        total += st["polygons"]
        print(f"{c:>5} {st['polygons']:>6} {st['triangles']:>5} {st['quads']:>6} {st['vertices_sent']:>6} "
              f"{len(o['model']['materials']):>4} {len(o['nsb']):>8} {len(o['bdhc']):>7} {len(o['data']):>10}")
    print(f"total {total} polygons")
    print("faces by group (before strip packing): " + ", ".join(f"{k} {v}" for k, v in sorted(F.groups.items())))
    print(f"edge crowns {info['crowns']}, lanterns {info['lanterns']} (+4 bridge), mushroom tiles {info['mushrooms']}, "
          f"spiral blossoms {info['spiral_blossoms']}")
    s, _ = GF.summary()
    print("Gardevoir Fountain (map_data_050):\n" + s)
    nfail = 0
    for desc, ok in res:
        if not ok or "--verbose" in args or not desc.startswith("layout: "):
            print(("PASS " if ok else "FAIL ") + desc)
        nfail += not ok
    print(f"({sum(1 for d, _ in res if d.startswith('layout: '))} layout checks, all "
          f"{'pass' if all(ok for d, ok in res if d.startswith('layout: ')) else 'NOT passing'}; --verbose lists them)")
    print(f"{nfail} failed")
    if "--preview" in args:
        write_preview(args[args.index("--preview") + 1], out, tex)
    if "--write" in args:
        if nfail:
            print("refusing to write: checks failed")
            return 1
        open(os.path.join(ROOT, TM.SET_REL), "wb").write(tex["bytes"])
        open(os.path.join(ROOT, LIGHTING_REL), "w").write(build_lighting()[0])
        for c, o in out.items():
            open(os.path.join(ROOT, OUT_MAP_DIR, f"map_data_{c:03d}.bin"), "wb").write(o["data"])
        print(f"wrote {TM.SET_REL} ({len(tex['bytes'])} B), {LIGHTING_REL}, " +
              ", ".join(f"{OUT_MAP_DIR}/map_data_{c:03d}.bin ({len(o['data'])} B)" for c, o in out.items()))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
