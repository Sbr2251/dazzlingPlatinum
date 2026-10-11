#!/usr/bin/env python3
"""Builds the Route 203 scar into overworld chunk map_data_019 (standard library only).

Usage:
  python3 tools/route_203/build_scar.py                  dry run: budgets + gameplay checks
  python3 tools/route_203/build_scar.py --write          write res/field/maps/data/map_data_019.bin
  python3 tools/route_203/build_scar.py --mesh OUT.json  also dump the assembled mesh (PLAN.md mesh.json format)

Inputs: the stock chunk 019 at BASE_REV (read from git, so re-running never feeds back), tools/route_203/scar_layout.py
(the tile contract) and the scar materials of textures.py (run `textures.py --write` first so set 006 has them).

What it does (see README.md):
  1. Stock terrain: every face of the stock chunk is kept, except inside the field FIELD (x 196..213, z 744..756):
     flat ground (grass, tall grass, flowers, tree shadows) is clipped exactly to the field's edge, and trees and the
     old ledge row whose centroid lies in the field are dropped. The road, its fences, the forests around the field,
     the x 214 cliff and stairs and the middle section are untouched.
  2. New ground in the field, per layout tile: grass, tall grass, tree shadow, or scorched ash (per-tile UV flips so
     the 16x16 dirt doesn't tile visibly).
  3. Scorch decals (alpha-cut blots) along the ash/grass edge and inside the ash, at h +0.03..0.05, to break up the
     tile edges.
  4. The fissure: X tiles are split into quarter-tile cells; a jagged polyline through the X chain decides which cells
     are open. Open cells get the glowing floor (asasea texels, violet palette, unlit, so it keeps glowing at night)
     at h -0.9, closed cells get ash, and every open/closed boundary gets a dark violet rock wall (criffp texels).
  5. Crack decals (unlit, glowing) on the cracked-ash tiles, oriented away from the fissure, never over an open cell.
  6. The fallen tree: split stump (S), a round log along the road (L) and the dead crown (C); new trees (T), a
     charred tree (K) and a debris boulder (o).
  7. Permissions from the layout (road tiles keep their stock values); BDHC and props stay stock.
"""
import json
import math
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import scar_layout as layout  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402
import textures  # noqa: E402

BASE_REV = textures.BASE_REV
CHUNK_REL = "res/field/maps/data/map_data_019.bin"
SET_REL = textures.SET_REL
CX, CZ = layout.CHUNK
FX0, FZ0, FX1, FZ1 = layout.FIELD
FIELD_RECT = (FX0, FZ0, FX1 + 1, FZ1 + 1)       # tile-edge coordinates [x0, x1) x [z0, z1)

FLAT_CLIP = ("ngrass", "nectgr", "nhana", "tshadow")   # texture names of flat ground faces clipped at the field edge
DROP_IN_FIELD = ("tree01", "conttree_b", "conttree_t", "allpeak")

MODEL_BUFFER = 0xF000

H_SCORCH = 0.03
H_SCORCH2 = 0.05
H_CRACK = 0.08
H_FLOOR = -0.9


def base_file(rel):
    return textures.base_file(rel)


# ---------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------

class MeshBuilder:
    """Collects faces per material in the mesh.json format (absolute tiles)."""

    def __init__(self):
        self.materials = {}
        self.meshes = {}

    def material(self, name, **m):
        self.materials.setdefault(name, dict(name=name, **m))
        self.meshes.setdefault(name, dict(material=name, positions=[], uvs=[], colors=[], quads=[], tris=[]))
        return name

    def quad(self, mat, pts, uvs, color=(255, 255, 255)):
        me = self.meshes[mat]
        b = len(me["positions"])
        me["positions"] += [list(p) for p in pts]
        me["uvs"] += [list(u) for u in uvs]
        me["colors"] += [list(color)] * 4
        me["quads"].append([b, b + 1, b + 2, b + 3])

    def tri(self, mat, pts, uvs, color=(255, 255, 255)):
        me = self.meshes[mat]
        b = len(me["positions"])
        me["positions"] += [list(p) for p in pts]
        me["uvs"] += [list(u) for u in uvs]
        me["colors"] += [list(color)] * 3
        me["tris"].append([b, b + 1, b + 2])

    def mesh(self, name):
        return {"name": name, "materials": list(self.materials.values()),
                "meshes": [m for m in self.meshes.values() if m["quads"] or m["tris"]]}


def flat_quad(mb, mat, x0, z0, x1, z1, h, uv0=(0, 0), uv_per_tile=1.0, rot=0, flip=False, color=(255, 255, 255)):
    """Horizontal quad over [x0,x1] x [z0,z1] at height h, wound like the stock ground quads (visible from above).
    UVs: u along x, v along z, scaled; rot (0..3) rotates the UV frame by 90 degree steps, flip mirrors u."""
    pts = [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)]
    w, d = (x1 - x0) * uv_per_tile, (z1 - z0) * uv_per_tile
    uvs = [(0, d), (w, d), (w, 0), (0, 0)]
    if flip:
        uvs = [(w - u, v) for u, v in uvs]
    for _ in range(rot % 4):
        uvs = [(v, w - u) for u, v in uvs]   # rotate frame
        w, d = d, w
    uvs = [(u + uv0[0], v + uv0[1]) for u, v in uvs]
    mb.quad(mat, pts, uvs, color)


def decal(mb, mat, cx, cz, size, h, angle, color=(255, 255, 255)):
    """A square decal of `size` tiles centred at (cx, cz), rotated by `angle` radians in the ground plane, the whole
    texture mapped once (UV 0..1). Winding as flat_quad."""
    s = size / 2
    ca, sa = math.cos(angle), math.sin(angle)
    corners = [(-s, s), (s, s), (s, -s), (-s, -s)]           # (dx, dz) like flat_quad: (x0,z1) (x1,z1) (x1,z0) (x0,z0)
    pts = [(cx + dx * ca - dz * sa, h, cz + dx * sa + dz * ca) for dx, dz in corners]
    uvs = [(0, 1), (1, 1), (1, 0), (0, 0)]
    mb.quad(mat, pts, uvs, color)


def merge_rects(cells):
    """cells: set of (x, z) unit cells (any integer grid) -> list of (x0, z0, x1, z1) rectangles covering them
    exactly (greedy: widest run first, then extend down)."""
    cells = set(cells)
    out = []
    while cells:
        x0, z0 = min(cells, key=lambda c: (c[1], c[0]))
        x1 = x0
        while (x1 + 1, z0) in cells:
            x1 += 1
        z1 = z0
        while all((x, z1 + 1) in cells for x in range(x0, x1 + 1)):
            z1 += 1
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                cells.discard((x, z))
        out.append((x0, z0, x1 + 1, z1 + 1))
    return out


# ---------------------------------------------------------------------------------------------------------------
# 1. stock terrain, cut at the field
# ---------------------------------------------------------------------------------------------------------------

def stock_mesh():
    sec = mapdata.unpack(base_file(CHUNK_REL))
    model = nsbmd.parse_bmd(sec["model"])["models"][0]
    return nsbmd.model_to_mesh(model, (CX, CZ), name=model["name"]), sec, model


def _in_field(x, z):
    return FIELD_RECT[0] <= x < FIELD_RECT[2] and FIELD_RECT[1] <= z < FIELD_RECT[3]


def clip_flat(P, U):
    """An axis-aligned horizontal quad (4 corners) -> list of (positions, uvs) quads for the parts outside the field
    rectangle; UVs are interpolated bilinearly (they are affine on these quads). None if the quad isn't
    axis-aligned or isn't flat."""
    xs = sorted({round(p[0], 4) for p in P})
    zs = sorted({round(p[2], 4) for p in P})
    hs = {round(p[1], 4) for p in P}
    if len(xs) != 2 or len(zs) != 2 or len(hs) != 1:
        return None
    (ax, bx), (az, bz), h = xs, zs, P[0][1]
    # affine UV from 3 corners
    def corner(x, z):
        for p, u in zip(P, U):
            if abs(p[0] - x) < 1e-3 and abs(p[2] - z) < 1e-3:
                return u
        return None
    u00, u10, u01 = corner(ax, az), corner(bx, az), corner(ax, bz)

    def uv(x, z):
        fx = (x - ax) / (bx - ax)
        fz = (z - az) / (bz - az)
        return [u00[0] + (u10[0] - u00[0]) * fx + (u01[0] - u00[0]) * fz,
                u00[1] + (u10[1] - u00[1]) * fx + (u01[1] - u00[1]) * fz]
    fx0, fz0, fx1, fz1 = FIELD_RECT
    ix0, iz0, ix1, iz1 = max(ax, fx0), max(az, fz0), min(bx, fx1), min(bz, fz1)
    if ix0 >= ix1 or iz0 >= iz1:
        return [(P, U)]                       # no overlap: keep as is
    parts = []
    if az < iz0:
        parts.append((ax, az, bx, iz0))
    if iz1 < bz:
        parts.append((ax, iz1, bx, bz))
    if ax < ix0:
        parts.append((ax, iz0, ix0, iz1))
    if ix1 < bx:
        parts.append((ix1, iz0, bx, iz1))
    out = []
    for x0, z0, x1, z1 in parts:
        pts = [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)]
        out.append((pts, [uv(p[0], p[2]) for p in pts]))
    return out


def cut_stock(mesh):
    mats = {m["name"]: m for m in mesh["materials"]}
    out = dict(mesh, meshes=[])
    stats = {"clipped": 0, "dropped": 0}
    for me in mesh["meshes"]:
        tex = mats[me["material"]]["texture"]
        P, U = me["positions"], me["uvs"]
        nrm = me.get("normals")
        newP, newU, newN, quads, tris = [], [], [], [], []

        def add(pts, uvs, ns=None):
            b = len(newP)
            newP.extend([list(p) for p in pts])
            newU.extend([list(u) for u in uvs])
            newN.extend(ns if ns is not None else [[0.0, 1.0, 0.0]] * len(pts))
            return list(range(b, b + len(pts)))

        for f in me["quads"]:
            pts, uvs = [P[i] for i in f], [U[i] for i in f]
            ns = [nrm[i] for i in f] if nrm else None
            cx = sum(p[0] for p in pts) / 4
            cz = sum(p[2] for p in pts) / 4
            if tex in FLAT_CLIP:
                parts = clip_flat(pts, uvs)
                if parts is not None:
                    if len(parts) != 1 or parts[0][0] is not pts:
                        stats["clipped"] += 1
                    for pp, uu in parts:
                        quads.append(add(pp, uu, ns if pp is pts else None))
                    continue
                if _in_field(cx, cz):
                    stats["dropped"] += 1
                    continue
            elif tex in DROP_IN_FIELD and _in_field(cx, cz):
                stats["dropped"] += 1
                continue
            quads.append(add(pts, uvs, ns))
        for f in me["tris"]:
            pts, uvs = [P[i] for i in f], [U[i] for i in f]
            ns = [nrm[i] for i in f] if nrm else None
            cx = sum(p[0] for p in pts) / 3
            cz = sum(p[2] for p in pts) / 3
            if (tex in FLAT_CLIP or tex in DROP_IN_FIELD) and _in_field(cx, cz):
                stats["dropped"] += 1
                continue
            tris.append(add(pts, uvs, ns))
        if quads or tris:
            m2 = dict(me, positions=newP, uvs=newU, quads=quads, tris=tris)
            m2["normals"] = newN if nrm else None
            m2.pop("positions_local", None)
            m2["colors"] = [[255, 255, 255]] * len(newP)
            out["meshes"].append(m2)
    return out, stats


def stock_material(mesh, texture):
    """Name of the stock material of `texture` in the chunk (to reuse its attributes)."""
    for m in mesh["materials"]:
        if m["texture"] == texture:
            return m
    return None


def tree_template(mesh, center=(201, 749)):
    """The 4 quads of the stock tree whose 2x2 footprint is centred at `center` (tile corner), relative positions
    and UVs: [(dx, h, dz), ...], [(u, v), ...]."""
    out = []
    for me in mesh["meshes"]:
        if not me["material"].startswith("tree01"):
            continue
        P, U = me["positions"], me["uvs"]
        for f in me["quads"]:
            pts = [P[i] for i in f]
            cx = sum(p[0] for p in pts) / 4
            cz = sum(p[2] for p in pts) / 4
            if abs(cx - center[0]) < 0.6 and abs(cz - (center[1] - 0.3)) < 0.9:
                out.append(([(p[0] - center[0], p[1], p[2] - center[1]) for p in pts], [U[i] for i in f]))
    assert len(out) == 4, f"tree template at {center}: {len(out)} quads"
    return out


# ---------------------------------------------------------------------------------------------------------------
# 4. the fissure
# ---------------------------------------------------------------------------------------------------------------

SUB = 8    # cells per tile side


def fissure_chain(t):
    """Ordered list of the X tiles from the stump end to the tip (walks the 4-connected chain)."""
    xs = {k for k, v in t.items() if v == "X"}
    stump = next(k for k, v in t.items() if v == "S")
    start = next(n for n in ((stump[0], stump[1] - 1), (stump[0] + 1, stump[1]), (stump[0] - 1, stump[1]))
                 if n in xs)
    chain, seen = [start], {start}
    while True:
        x, z = chain[-1]
        nxt = [n for n in ((x + 1, z), (x, z - 1), (x - 1, z), (x, z + 1)) if n in xs and n not in seen]
        if not nxt:
            break
        chain.append(nxt[0])
        seen.add(nxt[0])
    assert len(chain) == len(xs), (len(chain), len(xs))
    return chain


def _seg_dist(px, pz, ax, az, bx, bz):
    vx, vz = bx - ax, bz - az
    L = vx * vx + vz * vz
    tt = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * vx + (pz - az) * vz) / L))
    qx, qz = ax + vx * tt, az + vz * tt
    return math.hypot(px - qx, pz - qz), tt


def fissure_cells(t, rng):
    """-> (open cells, closed cells) in quarter-tile cells (cx, cz) = (x*SUB + i, z*SUB + j), X tiles only.
    The opening follows a jittered polyline through the chain's tile centres; its half-width wanders between
    0.16 and 0.42 tiles (wider in the middle, narrow at both ends)."""
    chain = fissure_chain(t)
    pts = [(x + 0.5, z + 0.5) for (x, z) in chain]
    stump = next(k for k, v in t.items() if v == "S")
    # start the crack at the root end (the edge shared with the stump tile)
    pts.insert(0, ((pts[0][0] + stump[0] + 0.5) / 2, (pts[0][1] + stump[1] + 0.5) / 2))
    for _ in range(2):          # Chaikin: the tile staircase becomes a rough diagonal with small zig-zags
        sm = [pts[0]]
        for p, q in zip(pts, pts[1:]):
            sm += [(0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]),
                   (0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1])]
        pts = sm + [pts[-1]]
    pts = [pts[0]] + [(x + rng.uniform(-0.12, 0.12), z + rng.uniform(-0.12, 0.12)) for x, z in pts[1:-1]] + [pts[-1]]
    n = len(pts)
    half = []
    for i in range(n):
        f = i / (n - 1)
        w = 0.16 + 0.26 * math.sin(math.pi * min(1.0, f * 1.15)) ** 0.8
        half.append(max(0.14, w + rng.uniform(-0.05, 0.05)))
    xs = {k for k, v in t.items() if v == "X"}
    open_c, closed_c = set(), set()
    for (x, z) in xs:
        for i in range(SUB):
            for j in range(SUB):
                px, pz = x + (i + 0.5) / SUB, z + (j + 0.5) / SUB
                best = 9.0
                for k in range(n - 1):
                    d, tt = _seg_dist(px, pz, *pts[k], *pts[k + 1])
                    w = half[k] + (half[k + 1] - half[k]) * tt
                    best = min(best, d - w)
                c = (x * SUB + i, z * SUB + j)
                best += rng.uniform(-0.07, 0.07)          # ragged rock edges instead of clean steps
                (open_c if best < 0 else closed_c).add(c)
    return open_c, closed_c, pts


def build_fissure(mb, t, rng):
    open_c, closed_c, pts = fissure_cells(t, rng)
    s = 1.0 / SUB
    # floor (merged rectangles of open cells), glow, unlit
    for x0, z0, x1, z1 in merge_rects(open_c):
        flat_quad(mb, "r203_rift", x0 * s, z0 * s, x1 * s, z1 * s, H_FLOOR, uv0=((x0 * s) % 4, (z0 * s) % 4))
    # closed cells: ash ground (merged per tile so the per-tile UV jitter matches the neighbours)
    for x0, z0, x1, z1 in merge_rects(closed_c):
        flat_quad(mb, "r203_ash", x0 * s, z0 * s, x1 * s, z1 * s, 0.0, uv0=((x0 * s) % 4, (z0 * s) % 4))
    # walls: every edge between an open cell and a non-open cell; the wall faces into the opening
    edges = {}   # (direction, line coordinate) -> list of cell positions along the line
    for (cx, cz) in open_c:
        for d, (nx, nz) in (("N", (cx, cz - 1)), ("S", (cx, cz + 1)), ("W", (cx - 1, cz)), ("E", (cx + 1, cz))):
            if (nx, nz) in open_c or d == "S":
                continue      # S walls face north, away from the fixed field camera: always back-face culled
            if d in ("N", "S"):
                line = cz if d == "N" else cz + 1
                edges.setdefault((d, line), []).append(cx)
            else:
                line = cx if d == "W" else cx + 1
                edges.setdefault((d, line), []).append(cz)
    nwall = 0
    for (d, line), run in edges.items():
        run.sort()
        groups, cur = [], [run[0]]
        for v in run[1:]:
            if v == cur[-1] + 1:
                cur.append(v)
            else:
                groups.append(cur)
                cur = [v]
        groups.append(cur)
        for g in groups:
            a, b = g[0] * s, (g[-1] + 1) * s
            L = line * s
            ua = a % 8                      # UVs stay small (the DS takes +-2048 texels); 1 repeat per 2 tiles
            ub = ua + (b - a)
            top, bot = 0.0, H_FLOOR
            vt, vb = 0.22, 0.22 + (top - bot) * 0.5
            # the wall on the opening's north edge (d == "N") faces south (+z), towards the camera
            if d == "N":
                pts4 = [(a, bot, L), (b, bot, L), (b, top, L), (a, top, L)]
                uvs = [(ua / 2, vb), (ub / 2, vb), (ub / 2, vt), (ua / 2, vt)]
            elif d == "S":
                pts4 = [(b, bot, L), (a, bot, L), (a, top, L), (b, top, L)]
                uvs = [(ub / 2, vb), (ua / 2, vb), (ua / 2, vt), (ub / 2, vt)]
            elif d == "W":
                pts4 = [(L, bot, b), (L, bot, a), (L, top, a), (L, top, b)]
                uvs = [(ub / 2, vb), (ua / 2, vb), (ua / 2, vt), (ub / 2, vt)]
            else:
                pts4 = [(L, bot, a), (L, bot, b), (L, top, b), (L, top, a)]
                uvs = [(ua / 2, vb), (ub / 2, vb), (ub / 2, vt), (ua / 2, vt)]
            mb.quad("r203_rockv", pts4, uvs)
            nwall += 1
    return open_c, closed_c, pts, nwall


# ---------------------------------------------------------------------------------------------------------------
# the whole build
# ---------------------------------------------------------------------------------------------------------------

def build(verbose=True):
    rng = random.Random(20310)
    smesh, sec, smodel = stock_mesh()
    kept, cstats = cut_stock(smesh)
    t = layout.tiles()
    mb = MeshBuilder()

    def stock_mat(tex):
        m = stock_material(smesh, tex)
        assert m, tex
        return m

    def use_stock(tex, newname=None):
        m = stock_mat(tex)
        name = newname or m["name"]
        mb.material(name, texture=m["texture"], palette=m["palette"], size=m["size"],
                    polygon_attr=m["polygon_attr"], alpha=m["alpha"],
                    repeat=[m["tex_param"]["repeat_s"], m["tex_param"]["repeat_t"]])
        return name

    M_GRASS = use_stock("ngrass")
    M_TALL = use_stock("nectgr")
    M_SHADOW = use_stock("tshadow")
    M_TREE = use_stock("tree01")
    M_IMPED = use_stock("imped")
    lit = dict(lights=1, cull="back", fog=True)
    unlit = dict(lights=0, cull="back", fog=True)
    for name, (tex, pal, size) in textures.MATERIALS.items():
        attr = unlit if name in ("r203_crack", "r203_rift") else lit
        if name in ("r203_dead", "r203_char", "r203_bark"):
            attr = dict(lit)
        mb.material(name, texture=tex, palette=pal, size=list(size), polygon_attr=attr, alpha=31)

    # --- 2. ground ---------------------------------------------------------------------------------------------
    grass, tall, ash_tiles = set(), set(), []
    tree_tiles = {(ox + a, oz + b): k for k in ("T", "K") for (ox, oz) in layout.tree_origins(k)
                  for a in (0, 1) for b in (0, 1)}
    for (x, z), ch in t.items():
        if not (FX0 <= x <= FX1 and FZ0 <= z <= FZ1):
            continue
        if ch == "X":
            continue                          # the fissure builds its own ground
        if (x, z) in tree_tiles and tree_tiles[(x, z)] == "T":
            continue                          # tree shadow below
        if ch == "w":
            tall.add((x, z))
        elif ch in ".":
            grass.add((x, z))
        else:                                  # : % G S o K (charred tree stands on ash)
            ash_tiles.append((x, z))
    for x0, z0, x1, z1 in merge_rects(grass):
        flat_quad(mb, M_GRASS, x0, z0, x1, z1, 0.0, uv0=(0, 0))
    for x0, z0, x1, z1 in merge_rects(tall):
        flat_quad(mb, M_TALL, x0, z0, x1, z1, 0.0, uv0=(0, 0))
    for (x, z) in sorted(ash_tiles):
        flat_quad(mb, "r203_ash", x, z, x + 1, z + 1, 0.0, rot=rng.randrange(4), flip=rng.random() < 0.5)
    for k in ("T",):
        for (ox, oz) in layout.tree_origins(k):
            flat_quad(mb, M_SHADOW, ox, oz, ox + 2, oz + 2, 0.0, uv_per_tile=0.5)

    # --- 4. fissure ----------------------------------------------------------------------------------------------
    open_c, closed_c, crack_pts, nwall = build_fissure(mb, t, rng)

    def near_open(cx, cz, r):
        """True if any open cell lies within r tiles (square) of (cx, cz)."""
        for (ox, oz) in open_c:
            if abs((ox + 0.5) / SUB - cx) < r + 0.2 and abs((oz + 0.5) / SUB - cz) < r + 0.2:
                return True
        return False

    scorched = {k for k, v in t.items() if v in ":%GSoXK" or (k in tree_tiles and tree_tiles[k] == "K")}

    # --- 3. scorch decals ---------------------------------------------------------------------------------------
    nscorch = 0

    def put_scorch(cx, cz, size):
        nonlocal nscorch
        if near_open(cx, cz, size / 2):
            return
        decal(mb, "r203_scorch", cx, cz, size, H_SCORCH if nscorch % 2 else H_SCORCH2, rng.uniform(0, 2 * math.pi))
        nscorch += 1

    def unscorched(n):
        return n in t and n not in scorched and t[n] not in "=TLC"

    for (x, z) in sorted(t):
        nb = [(x + dx, z + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        if (x, z) in scorched and t[(x, z)] != "X":
            edge = [n for n in nb if unscorched(n)]
            if edge:            # on the ash side of the edge, pushed towards the grass
                ex = sum(n[0] - x for n in edge) * 0.3
                ez = sum(n[1] - z for n in edge) * 0.3
                put_scorch(x + 0.5 + ex + rng.uniform(-0.15, 0.15), z + 0.5 + ez + rng.uniform(-0.15, 0.15),
                           rng.uniform(1.5, 2.0))
            elif rng.random() < 0.3:
                put_scorch(x + 0.5 + rng.uniform(-0.3, 0.3), z + 0.5 + rng.uniform(-0.3, 0.3), rng.uniform(1.0, 1.5))
        elif unscorched((x, z)) and any(n in scorched for n in nb) and rng.random() < 0.4:
            # spill a small blot onto the grass so the edge isn't a tile line
            put_scorch(x + 0.5 + rng.uniform(-0.2, 0.2), z + 0.5 + rng.uniform(-0.2, 0.2), rng.uniform(0.9, 1.3))

    # --- 5. crack decals -----------------------------------------------------------------------------------------
    ncrack = 0
    crack_tiles = sorted(k for k, v in t.items() if v in "%G")
    xt = [k for k, v in t.items() if v == "X"]
    for (x, z) in crack_tiles:
        dmin = min(math.hypot(x - a, z - b) for a, b in xt)
        if rng.random() > (0.9 if dmin < 1.5 else 0.6 if dmin < 2.5 else 0.35):
            continue
        cx, cz = x + 0.5 + rng.uniform(-0.25, 0.25), z + 0.5 + rng.uniform(-0.25, 0.25)
        # orient the crack's main line away from the nearest point of the fissure polyline
        best, bd = None, 9e9
        for (px, pz) in crack_pts:
            d = (px - cx) ** 2 + (pz - cz) ** 2
            if d < bd:
                bd, best = d, (px, pz)
        ang = math.atan2(cz - best[1], cx - best[0])
        size = rng.uniform(1.2, 1.7) if bd < 4 else rng.uniform(1.0, 1.4)
        for shrink in (1.0, 0.8, 0.65):
            if not near_open(cx, cz, size * shrink / 2 * 0.8):
                decal(mb, "r203_crack", cx, cz, size * shrink, H_CRACK, ang + rng.uniform(-0.35, 0.35))
                ncrack += 1
                break

    # --- 6. props as terrain: trees, fallen tree, boulder -------------------------------------------------------
    tmpl = tree_template(smesh)
    for k, mat in (("T", M_TREE), ("K", "r203_char")):
        for (ox, oz) in layout.tree_origins(k):
            for pts, uvs in tmpl:
                mb.quad(mat, [(ox + 1 + p[0], p[1], oz + 1 + p[2]) for p in pts], uvs)
    sx, sz = next(k for k, v in t.items() if v == "S")
    crown = sorted(k for k, v in t.items() if v == "C")
    ccx = sum(c[0] for c in crown) / len(crown) + 0.5
    ccz = sum(c[1] for c in crown) / len(crown) + 0.5
    # log: a 5-sided half-round prism lying diagonally from the root end (S) to the crown (C)
    ax, az = sx + 0.45, sz + 0.75
    bx, bz = ccx + 0.35, ccz - 0.6
    L = math.hypot(bx - ax, bz - az)
    dx_, dz_ = (bx - ax) / L, (bz - az) / L
    nx_, nz_ = -dz_, dx_                                    # horizontal unit normal (left of the direction)
    r = 0.55
    ring = [(math.cos(a) * r, 0.03 + math.sin(a) * r + r * 0.2) for a in
            (0.0, math.pi / 4, math.pi / 2, 3 * math.pi / 4, math.pi)]
    v_lo, v_hi = 0.64, 0.86
    for i in range(len(ring) - 1):
        (o0, h0), (o1, h1) = ring[i], ring[i + 1]
        va = v_lo + (v_hi - v_lo) * i / (len(ring) - 1)
        vb = v_lo + (v_hi - v_lo) * (i + 1) / (len(ring) - 1)
        pa0 = (ax + nx_ * o0, h0, az + nz_ * o0)
        pa1 = (ax + nx_ * o1, h1, az + nz_ * o1)
        pb0 = (bx + nx_ * o0, h0, bz + nz_ * o0)
        pb1 = (bx + nx_ * o1, h1, bz + nz_ * o1)
        pts = [pb0, pb1, pa1, pa0]
        uvs = [(L / 2, va), (L / 2, vb), (0, vb), (0, va)]
        # keep the face pointing outwards (away from the log axis) whatever the direction
        u = [pts[1][k] - pts[0][k] for k in range(3)]
        w = [pts[2][k] - pts[0][k] for k in range(3)]
        nrm = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
        mid = [(pa0[k] + pa1[k]) / 2 for k in range(3)]
        out = (mid[0] - ax, mid[1] - (0.03 + r * 0.2), mid[2] - az)
        if nrm[0] * out[0] + nrm[1] * out[1] + nrm[2] * out[2] < 0:
            pts = [pts[1], pts[0], pts[3], pts[2]]
            uvs = [uvs[1], uvs[0], uvs[3], uvs[2]]
        mb.quad("r203_bark", pts, uvs)
    # root end: the upturned root plate, a shaggy dark blob standing up behind the log's end
    rcx, rcz = sx + 0.55, sz + 0.45
    mb.quad("r203_char", [(rcx - 0.9, 0.0, rcz + 0.45), (rcx + 0.9, 0.0, rcz + 0.45),
                          (rcx + 0.9, 1.35, rcz - 0.45), (rcx - 0.9, 1.35, rcz - 0.45)],
            [(0.344, 1.0), (1.0, 1.0), (1.0, 0.438), (0.344, 0.438)])
    # crown: three tree01 canopy layers lying low across the road, dead palette
    layers = [  # (half width, h front, h back, z front, z back, uvs)
        (1.65, 0.06, 0.62, 0.95, -0.95, [(0.344, 1.0), (1.0, 1.0), (1.0, 0.438), (0.344, 0.438)]),
        (1.30, 0.30, 0.95, 0.70, -0.85, [(0.0, 0.469), (0.531, 0.469), (0.531, 0.0), (0.0, 0.0)]),
        (0.80, 0.62, 1.20, 0.30, -0.65, [(0.0, 1.0), (0.344, 1.0), (0.344, 0.656), (0.0, 0.656)]),
    ]
    for hw, hf, hb, zf, zb, uvs in layers:
        mb.quad("r203_dead", [(ccx - hw, hf, ccz + zf), (ccx + hw, hf, ccz + zf), (ccx + hw, hb, ccz + zb),
                              (ccx - hw, hb, ccz + zb)], uvs)
    # boulder(s): the imped rock as a tilted billboard
    for (bx, bz), v in sorted(t.items()):
        if v != "o":
            continue
        cx, cz = bx + 0.5, bz + 0.5
        mb.quad(M_IMPED, [(cx - 0.8, 0.0, cz + 0.6), (cx + 0.8, 0.0, cz + 0.6), (cx + 0.8, 1.15, cz - 0.45),
                          (cx - 0.8, 1.15, cz - 0.45)], [(0.0, 1.0), (0.5, 1.0), (0.5, 0.47), (0.0, 0.47)])

    # --- assemble --------------------------------------------------------------------------------------------------
    new = mb.mesh("scar")
    mesh = {"name": smodel["name"], "materials": kept["materials"] + [m for m in new["materials"]
                                                                       if m["name"] not in {x["name"] for x in kept["materials"]}],
            "meshes": kept["meshes"] + new["meshes"]}
    tex_table = texture_table()
    model = nsbmd.mesh_to_model(mesh, (CX, CZ), name=smodel["name"], textures=tex_table)
    missing = sorted({m["texture"] for m in model["materials"]} - set(tex_table))
    assert not missing, f"textures not in set 006 (run textures.py --write): {missing}"
    nsb = nsbmd.build_bmd([model])

    # --- 7. permissions -------------------------------------------------------------------------------------------
    perm = mapdata.read_permissions(sec["permissions"])
    for (x, z), ch in t.items():
        lx, lz = x - CX * 32, z - CZ * 32
        perm[lz][lx] = layout.permission(ch, perm[lz][lx])
    data = mapdata.pack(mapdata.write_permissions(perm), sec["props"], nsb, sec["bdhc"])
    st = nsbmd.model_stats(model)
    stats = dict(cut=cstats, polygons=st["polygons"], vertices_sent=st["vertices_sent"], model_bytes=len(nsb),
                 stock_polygons=nsbmd.model_stats(smodel)["polygons"], stock_model_bytes=len(sec["model"]),
                 materials=len(model["materials"]), fissure_open_cells=len(open_c), walls=nwall,
                 scorch_decals=nscorch, crack_decals=ncrack)
    return data, stats, mesh, model, perm


def texture_table():
    s = nsbtx.parse(open(os.path.join(ROOT, SET_REL), "rb").read())
    return {t["name"]: {"size": [t["w"], t["h"]]} for t in s["textures"]}


def gameplay_checks(perm):
    stock = {}
    p20 = mapdata.read_permissions(mapdata.unpack(open(os.path.join(ROOT, "res/field/maps/data/map_data_020.bin"),
                                                       "rb").read())["permissions"])
    for z in range(32):
        for x in range(32):
            stock[(CX * 32 + x, CZ * 32 + z)] = perm[z][x]
            stock[(CX * 32 + 32 + x, CZ * 32 + z)] = p20[z][x]
    ev = json.load(open(os.path.join(ROOT, "res/field/events/events_route_203.json")))
    objs = [(o["x"], o["z"]) for o in ev["object_events"] if o.get("hidden_flag") in ("0", 0)
            and o["graphics_id"] not in ("OBJ_EVENT_GFX_BARRY",)]
    # perms already include the layout, so pass them through walkable_world unchanged
    walk = {k: not (v & 0x8000) for k, v in stock.items()}
    for o in objs:
        walk[o] = False
    res = []
    full = layout.flood(walk, layout.ENTRANCE)
    res.append(("stairs reachable from the Jubilife entrance", all(s in full for s in layout.STAIRS)))
    cut = layout.flood(walk, layout.ENTRANCE, blocked=layout.GAP)
    res.append(("barrier airtight: without the gap tiles the stairs are unreachable",
                not any(s in cut for s in layout.STAIRS)))
    back = layout.flood(walk, layout.STAIRS[0])
    res.append(("route works backwards (stairs -> entrance)", layout.ENTRANCE in back))
    res.append(("gap and Garius tiles walkable", all(walk.get(g) for g in layout.GAP + [layout.GARIUS])))
    return res


def main():
    data, stats, mesh, model, perm = build()
    print(json.dumps(stats, indent=1))
    ok = stats["model_bytes"] <= MODEL_BUFFER
    print(f"model {stats['model_bytes']} B (buffer 0x{MODEL_BUFFER:x} = {MODEL_BUFFER}) -> {'OK' if ok else 'TOO BIG'}")
    for name, good in gameplay_checks(perm):
        print(("PASS " if good else "FAIL ") + name)
        ok &= good
    if "--mesh" in sys.argv:
        json.dump(mesh, open(sys.argv[sys.argv.index("--mesh") + 1], "w"))
    if "--write" in sys.argv:
        assert ok, "refusing to write"
        open(os.path.join(ROOT, CHUNK_REL), "wb").write(data)
        print("wrote", CHUNK_REL, len(data), "B")


if __name__ == "__main__":
    main()
