#!/usr/bin/env python3
"""Solaceon Town graybox: writes map_data_072 and map_data_073 from layout.py (standard library only).

Usage:
  python3 tools/solaceon_town/build_graybox.py                  dry run: build, print budgets and checks
  python3 tools/solaceon_town/build_graybox.py --preview DIR    also write DIR/chunk_07N.mesh.json (decoded back
                                                                from the built NSBMD) + DIR/props_07N.mesh.json
  python3 tools/solaceon_town/build_graybox.py --write          write the two map_data bins (refuses if a check fails)

Inputs, all read from git at layout.BASE_REV (50482f890), so re-running never feeds back: the stock chunks
072/073 (with the memorial wall), the neighbours 068/074/175/176 (camera count), texture set 010 and the build
models. Nothing else in the repo is read or written.

Per chunk:
  * Stock terrain is kept outside layout.REBUILD, byte for byte (tools/world_art/chunkedit.py): the Day Care ranch
    with the memorial wall and the fences on x 556, and the Ruins hill with both entrances. Inside REBUILD every
    stock face is cut away (flat ground faces are clipped exactly at the rectangle edges).
  * Graybox geometry for the rebuilt tiles, using only stock set-010 textures and palettes, lit like stock:
    ground per tile kind (merged into rectangles), stock-style trees (the 4 quads of a stock tree2_01 tree), stock-
    style picket fences (imped), the compound wall and gate, the Sanctuary hall (9 x 5, ~4 tiles tall, a door
    recess for the gym door prop), the registration tent (open front, table), banner posts (sol_wall's violet
    banner cell), lanterns, benches, offerings, the memorial plaque, the kennel block and stalls, scaffolding, crates
    and work lights at the excavation.
  * Props (map props = build models of area 0xA's list 6): the Day Care, Pokemon Center and Mart stay where they are;
    the four stock houses go; three stock houses (t4_h01 + c1_door1) stand on the new lots; the hall door is the
    stock gym door (298) so the field's door animation finds a door prop (ov5_021D431C.c asserts otherwise).
  * Permissions and BDHC from collision.py (layout.py).

Checks (--write refuses on any FAIL): permissions equal the layout; BDHC height at every tile centre equals the
layout; seams equal the neighbours (walkability + height at z 640 vs map_data_068 row z 639, z 671 vs map_data_074
row z 672; filler rows/edges blocked); every door tile has a building behind it and a door prop on it; all props are
in area 0xA's prop list; per chunk <= 1000 polygons and <= 45 KB of model (hard limit 0xF000); untouched stock shapes
byte-identical; on-screen polygons (terrain of every loaded chunk + props) <= 2048 for the real camera
(CAMERA_TYPE_DEFAULT) and the zoomed-in camera at every walkable tile.
"""
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
sys.path.insert(0, os.path.join(ROOT, "tools", "world_art"))
sys.path.insert(0, HERE)            # first: "layout" / "collision" are this directory's

import layout  # noqa: E402
import collision  # noqa: E402
import chunkedit as C  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402

BASE_REV = layout.BASE_REV
SET_REL = "res/field/maps/texture_sets/map_texture_set_010.nsbtx"
BUILD_MODEL_REL = "res/prebuilt/fielddata/build_model/build_model.narc"
AREA_DATA_REL = "res/prebuilt/fielddata/areadata/area_data.narc"
AREA_BUILD_REL = "res/prebuilt/fielddata/areadata/area_build_model/area_build.narc"
AREA_ID = 0xA

POLY_LIMIT = 1000            # per chunk (PLAN section 4)
MODEL_LIMIT = 45 * 1024      # per chunk (PLAN section 4); the hard limit is the 0xF000 load buffer
SCREEN_LIMIT = 2048          # DS polygons per frame
MAX_RUN = 16                 # merged ground quads stay <= 16 tiles (UV range)

# texture -> palette (all stock entries of set 010 at BASE_REV)
PALETTE = {"ngrass": "grass", "nsand": "sandset", "nsandp": "nsandp", "blueglay": "blueglay",
           "blueglayp": "blueglayp", "shadowchip": "shadowchip", "l_grass_u": "l_grass_u_pl",
           "l_grass_m": "l_grass_m_pl", "l_grass_d": "l_grass_d_pl", "tree2_01": "tree2_01", "imped": "imped",
           "hanger": "hanger", "criff": "criff", "criffp": "criff", "nbridge": "dun_bridge", "bridge": "bridge",
           "beach": "beach", "rhana": "rhana", "nhana": "nhana", "sol_wall": "sol_wall_pl", "dhole": "dhole",
           "lgreen": "lgreen", "fenter": "fenter"}
DOUBLE_SIDED = {"tent_canopy"}

# prop model ids (build_model.narc), all in area 0xA's prop list 6
PC_PROP, MART_PROP, SLIDING_DOOR, HOUSE_PROP, HOUSE_DOOR, DAYCARE_PROP, DAYCARE_DOOR, GYM_DOOR = \
    4, 5, 70, 197, 246, 198, 67, 298
DOOR_MODELS = {SLIDING_DOOR, HOUSE_DOOR, DAYCARE_DOOR, GYM_DOOR, 444}
HOUSE_DOOR_DELTA = (7070, 5205, 40791)     # fx32, house prop -> its c1_door1 (as all four stock Solaceon houses)


# ---------------------------------------------------------------------------------------------------------------
# geometry helpers (absolute tiles (x, h, z))
# ---------------------------------------------------------------------------------------------------------------

class Faces:
    """All new faces, routed to the chunk that contains their centroid."""

    def __init__(self):
        self.mb = {c: C.MeshBuilder() for c in layout.CHUNKS}

    def chunk_of(self, pts):
        cx = sum(p[0] for p in pts) / len(pts)
        return 72 if cx < 576 else 73

    def add(self, tex, pts, uvs, facing, mat=None):
        """pts wound in any order; reordered so the normal points along `facing`."""
        n = C.face_normal(pts)
        if sum(a * b for a, b in zip(n, facing)) < 0:
            pts, uvs = pts[::-1], uvs[::-1]
        c = self.chunk_of(pts)
        name = mat or ("gb_" + tex)
        size = TEX_SIZE[tex]
        self.mb[c].material(name[:16], tex, PALETTE[tex], size,
                            cull="none" if name in DOUBLE_SIDED else "back")
        self.mb[c].face(name[:16], [tuple(p) for p in pts], [tuple(u) for u in uvs])

    # -- primitives
    def flat(self, tex, x0, z0, x1, z1, h, rep=None, u0=0.0, v0=0.0):
        rep = rep if rep is not None else 16.0 / TEX_SIZE[tex][0]
        pts = [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)]
        uvs = [((p[0] - x0) * rep + u0, (p[2] - z0) * rep + v0) for p in pts]
        self.add(tex, pts, uvs, (0, 1, 0))

    def wall_z(self, tex, x0, x1, z, h0, h1, facing, rep=None, uv=None):
        """Vertical quad on the plane z (facing +z or -z)."""
        rep = rep if rep is not None else 16.0 / TEX_SIZE[tex][0]
        pts = [(x0, h1, z), (x1, h1, z), (x1, h0, z), (x0, h0, z)]
        uvs = uv or [(0, 0), ((x1 - x0) * rep, 0), ((x1 - x0) * rep, (h1 - h0) * rep), (0, (h1 - h0) * rep)]
        if facing < 0:
            uvs = [((x1 - x0) * rep - u, v) for u, v in uvs] if not uv else uvs
        self.add(tex, pts, uvs, (0, 0, facing))

    def wall_x(self, tex, x, z0, z1, h0, h1, facing, rep=None):
        rep = rep if rep is not None else 16.0 / TEX_SIZE[tex][0]
        pts = [(x, h1, z0), (x, h1, z1), (x, h0, z1), (x, h0, z0)]
        uvs = [(0, 0), ((z1 - z0) * rep, 0), ((z1 - z0) * rep, (h1 - h0) * rep), (0, (h1 - h0) * rep)]
        self.add(tex, pts, uvs, (facing, 0, 0))

    def box(self, side, top, x0, z0, x1, z1, h0, h1, rep=None, faces="nsewt"):
        if "t" in faces:
            self.flat(top, x0, z0, x1, z1, h1, rep)
        if "s" in faces:
            self.wall_z(side, x0, x1, z1, h0, h1, +1, rep)
        if "n" in faces:
            self.wall_z(side, x0, x1, z0, h0, h1, -1, rep)
        if "e" in faces:
            self.wall_x(side, x1, z0, z1, h0, h1, +1, rep)
        if "w" in faces:
            self.wall_x(side, x0, z0, z1, h0, h1, -1, rep)

    def polygons(self):
        return {c: mb.polygons() for c, mb in self.mb.items()}


TEX_SIZE = {}       # filled from set 010


# ---------------------------------------------------------------------------------------------------------------
# the town
# ---------------------------------------------------------------------------------------------------------------

G = layout.GROUND_H


DECO = {"fence", "post", "lantern", "bench", "offering", "plaque", "crate", "worklight", "scaffold"}


def ground_tex(t, x, z):
    coll, h, kind = t[(x, z)]
    if kind in DECO:            # small blocked things stand on the ground around them
        for dx, dz in ((0, 1), (0, -1), (-1, 0), (1, 0)):
            n = t.get((x + dx, z + dz))
            if n and not n[0] & layout.BLOCK and n[2] not in ("stock", "tallgrass", "road", "gap"):
                return layout.KINDS[n[2]][2]
        return "ngrass"
    if kind == "road" and x in (layout.ROAD[0], layout.ROAD[1]) and not layout.in_rect(layout.PLAZA, x, z):
        return "nsandp_w" if x == layout.ROAD[0] else "nsandp_e"
    if kind == "tallgrass":
        gx0, gz0, gx1, gz1 = layout.GARDEN
        return "l_grass_u" if z == gz0 else "l_grass_d" if z == gz1 else "l_grass_m"
    return layout.KINDS[kind][2]


def build_ground(F, t):
    cells = {}
    for (x, z), v in t.items():
        if layout.rebuilt(x, z):
            cells[(x, z)] = (ground_tex(t, x, z), 72 if x < 576 else 73)
    used = set()
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
        tex = k[0]
        if tex.startswith("nsandp_"):
            # the stock road-edge mapping (map_data_074): v 0.508 on the sand side .. 0.992 on the grass side,
            # u 0.5 per tile along z
            inner, outer = (x + 1, x) if tex == "nsandp_w" else (x, x + 1)
            pts = [(inner, G, z), (outer, G, z), (outer, G, z + d), (inner, G, z + d)]
            uvs = [(-d / 4, 0.508), (-d / 4, 0.992), (d / 4, 0.992), (d / 4, 0.508)]
            F.add("nsandp", pts, uvs, (0, 1, 0), mat="gb_nsandp")
        else:
            rep = 16.0 / TEX_SIZE[tex][0]
            F.flat(tex, x, z, x + w, z + d, G, rep, u0=-(x * rep % 1), v0=-(z * rep % 1))


# one stock tree (map_data_073, the tree on tiles (586..587, 656..657)): 4 quads of tree2_01, relative to its NW tile
TREE_QUADS = [
    ([(0.31, 2.86, 1.13), (1.69, 2.86, 1.13), (1.69, 3.64, 0.00), (0.31, 3.64, 0.00)],
     [(0.000, 1.000), (0.344, 1.000), (0.344, 0.656), (0.000, 0.656)]),
    ([(-0.03, 2.15, 1.46), (2.03, 2.15, 1.46), (2.03, 3.23, -0.08), (-0.03, 3.23, -0.08)],
     [(0.000, 0.469), (0.531, 0.469), (0.531, 0.000), (0.000, 0.000)]),
    ([(-0.25, 1.45, 1.62), (2.25, 1.45, 1.62), (2.25, 2.67, -0.12), (-0.25, 2.67, -0.12)],
     [(0.344, 1.000), (1.000, 1.000), (1.000, 0.438), (0.344, 0.438)]),
    ([(0.00, 1.06, 1.94), (2.00, 1.06, 1.94), (2.00, 1.06, 0.06), (0.00, 1.06, 0.06)],
     [(0.531, 0.438), (1.000, 0.438), (1.000, 0.000), (0.531, 0.000)]),
]


def build_trees(F):
    for tx, tz in layout.TREES:
        for pts, uvs in TREE_QUADS:
            P = [(tx + p[0], p[1], tz + p[2]) for p in pts]
            n = C.face_normal(P)
            F.add("tree2_01", P, uvs, n)


def runs(tiles_set, axis):
    """Maximal runs of tiles along x (axis 'x') or z: [(fixed, start, end)] inclusive."""
    out = []
    by = {}
    for x, z in tiles_set:
        k, s = (z, x) if axis == "x" else (x, z)
        by.setdefault(k, []).append(s)
    for k, ss in by.items():
        ss.sort()
        i = 0
        while i < len(ss):
            j = i
            while j + 1 < len(ss) and ss[j + 1] == ss[j] + 1:
                j += 1
            out.append((k, ss[i], ss[j]))
            i = j + 1
    return out


def build_fences(F, t):
    fence = {k for k, v in t.items() if v[2] == "fence" and layout.rebuilt(*k)}
    ew = {(x, z) for x, z in fence if (x - 1, z) in fence or (x + 1, z) in fence or
          not ((x, z - 1) in fence or (x, z + 1) in fence)}
    ns = {(x, z) for x, z in fence if (x, z - 1) in fence or (x, z + 1) in fence}
    for z, x0, x1 in runs(ew, "x"):
        # the stock east-west picket fence: leaning back 45 degrees, imped row v 0..0.25, u 0.25 per tile
        for a in range(x0, x1 + 1, 4):
            b = min(a + 4, x1 + 1)
            pts = [(a, G + 0.02, z + 0.85), (b, G + 0.02, z + 0.85), (b, G + 0.73, z + 0.15), (a, G + 0.73, z + 0.15)]
            uvs = [(0, 0.25), ((b - a) * 0.25, 0.25), ((b - a) * 0.25, 0), (0, 0)]
            F.add("imped", pts, uvs, (0, 0.7, 0.7))
    for x, z0, z1 in runs(ns, "z"):
        # the stock north-south fence: a flat rail strip at h +0.375, imped v 0.312..0.438, u 0.25 per tile along z
        a, b = z0 + 0.5, z1 + 0.5
        pts = [(x + 0.25, G + 0.375, b), (x + 0.75, G + 0.375, b), (x + 0.75, G + 0.375, a), (x + 0.25, G + 0.375, a)]
        uvs = [((b - a) * 0.25, 0.438), ((b - a) * 0.25, 0.312), (0, 0.312), (0, 0.438)]
        F.add("imped", pts, uvs, (0, 1, 0))


def build_compound(F, t):
    wall = {k for k, v in t.items() if v[2] == "wall"}
    top = G + 1.4
    for z, x0, x1 in runs({(x, z) for x, z in wall if (x - 1, z) in wall or (x + 1, z) in wall}, "x"):
        F.box("hanger", "criff", x0, z + 0.2, x1 + 1, z + 0.8, G, top, faces="nsewt")
    for x, z0, z1 in runs({(x, z) for x, z in wall if (x, z - 1) in wall or (x, z + 1) in wall}, "z"):
        F.box("hanger", "criff", x + 0.2, z0 + 0.8, x + 0.8, z1 + 0.2, G, top, faces="ewt")
    for x, z in layout.GATE_PILLARS:
        F.box("hanger", "criff", x + 0.1, z + 0.1, x + 0.9, z + 0.9, G, G + 2.0)
        F.box("criff", "criff", x + 0.02, z + 0.02, x + 0.98, z + 0.98, G + 2.0, G + 2.2)


def build_hall(F):
    x0, z0, x1, z1 = layout.HALL
    X0, X1 = x0 + 0.1, x1 + 0.9                  # body
    ZN, ZS = z0 + 0.1, z1 - 0.02                 # the facade stands on the door row's north edge (as stock doors)
    eave = G + 3.0
    ridge = G + layout.HALL_H
    dx = layout.DOORS[2][0][0]
    d0, d1, dtop = dx + 0.5 - 0.95, dx + 0.5 + 0.95, G + 2.85
    # walls (pale stone)
    F.wall_z("hanger", X0, d0, ZS, G, eave, +1)
    F.wall_z("hanger", d1, X1, ZS, G, eave, +1)
    F.wall_z("hanger", d0, d1, ZS, dtop, eave, +1)
    F.wall_z("shadowchip", d0, d1, ZS - 0.01, G, dtop, +1)          # the dark doorway behind the gym door prop
    F.wall_z("hanger", X0, X1, ZN, G, eave, -1)
    F.wall_x("hanger", X0, ZN, ZS, G, eave, -1)
    F.wall_x("hanger", X1, ZN, ZS, G, eave, +1)
    # pilasters either side of the door and at the corners
    for px in (d0 - 0.3, d1, X0 - 0.05, X1 - 0.25):
        F.box("criff", "criff", px, ZS - 0.05, px + 0.3, ZS + 0.25, G, eave + 0.1, faces="sewt")
    # hip roof with an overhang
    e0, e1, f0, f1 = X0 - 0.25, X1 + 0.25, ZN - 0.25, ZS + 0.35
    zr = (f0 + f1) / 2
    r0, r1 = e0 + (zr - f0), e1 - (zr - f0)
    rep = 16.0 / TEX_SIZE["blueglay"][0]
    F.add("blueglay", [(e0, eave, f1), (e1, eave, f1), (r1, ridge, zr), (r0, ridge, zr)],
          [(0, 0), ((e1 - e0) * rep, 0), ((r1 - e0) * rep, 2 * rep), ((r0 - e0) * rep, 2 * rep)], (0, 1, 1))
    F.add("blueglay", [(e1, eave, f0), (e0, eave, f0), (r0, ridge, zr), (r1, ridge, zr)],
          [(0, 0), ((e1 - e0) * rep, 0), ((e1 - r0) * rep, 2 * rep), ((e1 - r1) * rep, 2 * rep)], (0, 1, -1))
    F.add("blueglay", [(e0, eave, f0), (e0, eave, f1), (r0, ridge, zr)],
          [(0, 0), ((f1 - f0) * rep, 0), ((zr - f0) * rep, 2 * rep)], (-1, 1, 0))
    F.add("blueglay", [(e1, eave, f1), (e1, eave, f0), (r1, ridge, zr)],
          [(0, 0), ((f1 - f0) * rep, 0), ((zr - f0) * rep, 2 * rep)], (1, 1, 0))
    # roof edge band and the porch step on the door row
    F.wall_z("criff", e0, e1, f1, eave - 0.2, eave, +1)
    F.box("blueglay", "blueglay", d0 - 0.6, z1 + 0.0, d1 + 0.6, z1 + 0.85, G, G + 0.1, faces="sewt")


def build_tent(F):
    x0, z0, x1, z1 = layout.TENT
    X0, X1, ZB, ZF = x0 + 0.02, x1 + 0.98, z0 + 0.05, z1 + 1.0
    F.wall_z("beach", X0, X1, ZB, G, G + 2.0, +1)                    # back canvas
    F.add("beach", [(X0, G + 2.0, ZB), (X1, G + 2.0, ZB), (X1, G + 1.75, ZF + 0.1), (X0, G + 1.75, ZF + 0.1)],
          [(0, 0), (3, 0), (3, 2), (0, 2)], (0, 1, 0.3), mat="tent_canopy")
    for px in (X0, X1 - 0.12):                                     # front poles
        F.box("nbridge", "nbridge", px, ZF - 0.12, px + 0.12, ZF, G, G + 1.75, faces="sew")
    F.box("nbridge", "nbridge", x0 + 0.08, z1 + 0.15, x1 + 0.92, z1 + 0.85, G, G + 0.55, faces="sewnt")   # table
    for cx in (x0, x1):                                            # card boxes behind the table
        F.box("nbridge", "nbridge", cx + 0.15, z0 + 0.2, cx + 0.85, z0 + 0.8, G, G + 0.6, faces="sewt")
    # the tent sign: a board on a post
    sx, sz = layout.TENT_SIGN_POST
    F.box("nbridge", "nbridge", sx + 0.44, sz + 0.44, sx + 0.56, sz + 0.56, G, G + 1.0, faces="sew")
    F.wall_z("bridge", sx + 0.1, sx + 0.9, sz + 0.6, G + 0.95, G + 1.45, +1)


def build_posts(F):
    for x, z in layout.BANNER_POSTS:
        F.box("nbridge", "nbridge", x + 0.42, z + 0.42, x + 0.58, z + 0.58, G, G + 2.5, faces="sewt")
        # the violet Eclipse banner: sol_wall cell 3 (128 x 16 atlas, eight 16 x 16 cells)
        F.wall_z("sol_wall", x + 0.12, x + 0.88, z + 0.6, G + 1.1, G + 2.3, +1,
                 uv=[(3 / 8, 0), (4 / 8, 0), (4 / 8, 1), (3 / 8, 1)])
    for x, z in layout.LANTERNS:
        F.box("shadowchip", "shadowchip", x + 0.43, z + 0.43, x + 0.57, z + 0.57, G, G + 1.5, faces="sew")
        F.box("beach", "beach", x + 0.3, z + 0.3, x + 0.7, z + 0.7, G + 1.5, G + 1.9)
    benches = runs(set(layout.BENCHES), "z")
    for x, z0, z1 in benches:
        F.box("nbridge", "nbridge", x + 0.2, z0 + 0.1, x + 0.75, z1 + 0.9, G + 0.3, G + 0.42, faces="sewnt")
        F.wall_x("nbridge", x + 0.75, z0 + 0.1, z1 + 0.9, G + 0.42, G + 0.9, -1)
    for x, z in layout.OFFERINGS:
        F.box("nbridge", "rhana", x + 0.1, z + 0.1, x + 0.9, z + 0.9, G, G + 0.25)
    x, z = layout.MEMORIAL_PLAQUE
    F.box("hanger", "blueglay", x + 0.15, z + 0.3, x + 0.85, z + 0.7, G, G + 0.7)


def build_kennel(F):
    x0, z0, x1, z1 = layout.KENNEL
    X0, X1 = x0 + 0.05, x1 + 0.95
    F.box("nbridge", "nbridge", X0, z0 + 0.05, X1, z0 + 0.95, G, G + 1.8, faces="sewn")
    rep = 0.5
    F.add("criff", [(X0 - 0.1, G + 2.2, z0 - 0.05), (X1 + 0.1, G + 2.2, z0 - 0.05), (X1 + 0.1, G + 1.8, z0 + 1.15),
                    (X0 - 0.1, G + 1.8, z0 + 1.15)],
          [(0, 0), ((X1 - X0) * rep, 0), ((X1 - X0) * rep, 1), (0, 1)], (0, 1, 0.3))
    for x, z in [(x, z1) for x in range(x0, x1 + 1) if (x, z1) not in layout.KENNEL_STALLS]:
        F.box("nbridge", "nbridge", x + 0.35, z + 0.0, x + 0.65, z + 0.95, G, G + 1.0, faces="sewt")
    sx, sz = layout.SIGNS["KENNEL_SIGN"][0]
    F.wall_z("bridge", sx + 0.1, sx + 0.9, sz + 0.96, G + 0.55, G + 1.0, +1)
    # wheel ruts from the truck bay out through the yard gate onto the road (and on towards Route 209)
    bx0, bz0, bx1, bz1 = layout.TRUCK_BAY
    rz = [(z0, z1) for z, x0, x1 in runs({k for k, v in layout.tiles().items() if v[2] == "ruts"}, "x")
          for z0, z1 in [(z + 0.25, z + 0.45)]]
    for z0, z1 in rz:
        F.flat("criff", bx1 + 1, z0, layout.ROAD[0] + 0.5, z1, G + 0.01)


def build_excavation(F):
    sc = set(layout.SCAFFOLD)
    for z, a, b in runs(sc, "x"):
        for px in range(a, b + 2):                                  # poles on the tile edges
            F.box("nbridge", "nbridge", max(a, px - 0.06), z + 0.75, min(b + 1, px + 0.06), z + 0.87, G, G + 2.6,
                  faces="sew")
        for h in (G + 1.2, G + 2.2):
            F.wall_z("bridge", a, b + 1, z + 0.88, h, h + 0.25, +1)
        F.box("bridge", "bridge", a, z + 0.05, b + 1, z + 0.88, G + 2.6, G + 2.7, faces="st")
    for x, z in layout.CRATES:
        F.box("nbridge", "nbridge", x + 0.1, z + 0.1, x + 0.9, z + 0.9, G, G + 0.8)
    for x, z in layout.WORKLIGHTS:
        F.box("shadowchip", "shadowchip", x + 0.44, z + 0.44, x + 0.56, z + 0.56, G, G + 2.0, faces="sew")
        F.box("beach", "beach", x + 0.25, z + 0.3, x + 0.75, z + 0.6, G + 2.0, G + 2.35)


def graybox_faces():
    t = layout.tiles()
    F = Faces()
    build_ground(F, t)
    build_trees(F)
    build_fences(F, t)
    build_compound(F, t)
    build_hall(F)
    build_tent(F)
    build_posts(F)
    build_kennel(F)
    build_excavation(F)
    return F


# ---------------------------------------------------------------------------------------------------------------
# props
# ---------------------------------------------------------------------------------------------------------------

def prop_fx(c, tx, ty_world, tz):
    """Absolute tile position (x, z) + world y -> fx32 position relative to the chunk centre."""
    cx, cz = layout.CHUNKS[c]
    return [round((tx - cx * 32 - 16) * 16 * 4096), round(ty_world * 4096), round((tz - cz * 32 - 16) * 16 * 4096)]


def props():
    """-> {chunk: [prop dict]} (mapdata.write_props format)."""
    stock = {c: mapdata.read_props(mapdata.unpack(layout.git_file(layout.chunk_rel(c)))["props"]) for c in layout.CHUNKS}
    keep = {PC_PROP, MART_PROP, SLIDING_DOOR, DAYCARE_PROP, DAYCARE_DOOR}
    out = {c: [p for p in stock[c] if p["model"] in keep] for c in layout.CHUNKS}
    for name, (x0, z0) in layout.HOUSES.items():
        hx, hz = x0 + 2.0, z0 + 2.5                 # stock: house at (x0 + 2, z0 + 2.5), door tile (x0 + 1, z0 + 3)
        c = 72 if hx < 576 else 73
        pos = prop_fx(c, hx, 32, hz)
        out[c].append(dict(model=HOUSE_PROP, pos=pos))
        out[c].append(dict(model=HOUSE_DOOR, pos=[pos[i] + HOUSE_DOOR_DELTA[i] for i in range(3)]))
    (dx, dz), _ = layout.DOORS[2]
    c = 72 if dx < 576 else 73
    out[c].append(dict(model=GYM_DOOR, pos=prop_fx(c, dx + 0.5, 32, dz)))   # as stock gym doors: tile centre x,
    return out                                                              # the door row's north edge


def area_prop_list():
    import tempfile
    sys.path.insert(0, os.path.join(ROOT, "tools", "coronet_lava"))
    import narc

    def files(rel):
        with tempfile.NamedTemporaryFile(suffix=".narc") as f:
            f.write(layout.git_file(rel))
            f.flush()
            return narc.read_files(f.name)[2]
    ad = files(AREA_DATA_REL)[AREA_ID]
    pid = struct.unpack_from("<H", ad)[0]
    ab = files(AREA_BUILD_REL)[pid]
    n = struct.unpack_from("<H", ab)[0]
    return list(struct.unpack_from("<%dH" % n, ab, 2)), files(BUILD_MODEL_REL)


def prop_meshes(c, plist, bm_files):
    """Placed prop meshes in absolute tiles (for previews and the camera count)."""
    cell = layout.CHUNKS[c]
    out = {"name": f"props_{c:03d}", "origin_tile": [cell[0] * 32, cell[1] * 32], "materials": [], "meshes": []}
    for p in plist:
        pm = nsbmd.parse_bmd(bm_files[p["model"]])["models"][0]
        sub = nsbmd.model_to_mesh(pm, cell, name=pm["name"], offset=[v / 4096 for v in p["pos"]])
        names = {m["name"] for m in out["materials"]}
        out["materials"] += [m for m in sub["materials"] if m["name"] not in names]
        out["meshes"] += sub["meshes"]
    return out


# ---------------------------------------------------------------------------------------------------------------
# camera count (method of tools/lake_verity/assemble.camera_polys, for the overworld cameras)
# ---------------------------------------------------------------------------------------------------------------

CAMERAS = (("default", 59.051513671875, 666.922119140625, 8.0914306640625),     # Solaceon's header camera
           ("zoomed_in", 54.656982421875, 515.4560546875, 10.458984375))
NEAR, FAR = 150.0, 900.0


def mesh_faces(mesh):
    cull = {mt["name"]: mt.get("polygon_attr", {}).get("cull", "back") for mt in mesh["materials"]}
    out = []
    for me in mesh["meshes"]:
        P = [(p[0] * 16.0, 16.0 + p[1] * 16.0, p[2] * 16.0) for p in me["positions"]]
        ds = cull.get(me["material"], "back") != "back"
        for f in me["tris"] + me["quads"]:
            vs = [P[i] for i in f]
            out.append((sum(v[0] for v in vs) / len(vs) / 16, sum(v[2] for v in vs) / len(vs) / 16, vs, ds))
    return out


def camera_polys(faces, targets, heights):
    """Worst per-frame polygon count over the target tiles for each camera -> [(camera, worst, tile)]."""
    buckets = {}
    for fc in faces:
        buckets.setdefault((int(fc[0]) // 4, int(fc[1]) // 4), []).append(fc)
    res = []
    for name, pitch, dist, fov in CAMERAS:
        sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
        ty, tx = math.tan(math.radians(fov)), math.tan(math.radians(fov)) * 256 / 192
        fwd, up = (0.0, -sp, -cp), (0.0, cp, -sp)
        best = (0, None)
        for (x, z) in targets:
            T = ((x + 0.5) * 16, 16 + heights[(x, z)] * 16, (z + 0.5) * 16)
            E = (T[0], T[1] + dist * sp, T[2] + dist * cp)
            n = 0
            for bx in range((x - 24) // 4, (x + 24) // 4 + 1):
                for bz in range((z - 28) // 4, (z + 20) // 4 + 1):
                    for fcx, fcz, vs, ds in buckets.get((bx, bz), ()):
                        out_mask = 63
                        for v in vs:
                            d = (v[0] - E[0], v[1] - E[1], v[2] - E[2])
                            zc = d[1] * fwd[1] + d[2] * fwd[2]
                            yc = d[1] * up[1] + d[2] * up[2]
                            xc = d[0]
                            out_mask &= (zc < NEAR) | (zc > FAR) << 1 | (yc > zc * ty) << 2 | \
                                (yc < -zc * ty) << 3 | (xc > zc * tx) << 4 | (xc < -zc * tx) << 5
                        if out_mask:
                            continue
                        if not ds:
                            a, b, c_ = vs[0], vs[1], vs[2]
                            u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
                            w = (c_[0] - a[0], c_[1] - a[1], c_[2] - a[2])
                            nrm = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
                            if nrm[0] * (E[0] - a[0]) + nrm[1] * (E[1] - a[1]) + nrm[2] * (E[2] - a[2]) <= 0:
                                continue
                        n += 1
            if n > best[0]:
                best = (n, (x, z))
        res.append((name,) + best)
    return res


# ---------------------------------------------------------------------------------------------------------------
# build + checks
# ---------------------------------------------------------------------------------------------------------------

def clip_rects(c):
    cx, cz = layout.CHUNKS[c]
    out = []
    for x0, z0, x1, z1 in layout.REBUILD:
        a, b = max(x0, cx * 32), min(x1 + 1, cx * 32 + 32)
        if a < b:
            out.append((a, max(z0, cz * 32), b, min(z1 + 1, cz * 32 + 32)))
    return out


def build():
    set_bytes = layout.git_file(SET_REL)
    tex_table, pal_names = C.texture_table(set_bytes)
    for k, v in tex_table.items():
        TEX_SIZE[k] = v["size"]
    missing = sorted(set(PALETTE) - set(tex_table)) + sorted(set(PALETTE.values()) - pal_names)
    assert not missing, f"not in stock set 010: {missing}"
    F = graybox_faces()
    plist = props()
    out = {}
    for c, cell in layout.CHUNKS.items():
        edit = C.ChunkEdit(layout.chunk_rel(c), cell, BASE_REV)
        stock_tex = sorted({m["texture"] for m in edit.model["materials"] if m["texture"]})
        edit.clip_flat(stock_tex, clip_rects(c))
        edit.add(F.mb[c], tex_table)
        model = edit.model_bytes()
        perm = collision.permissions(c)
        bd = collision.bdhc(c)
        data = mapdata.pack(perm, mapdata.write_props(plist[c]), model, bd)
        st = edit.stats(model)
        st.update(new_polygons=F.mb[c].polygons(), bdhc_bytes=len(bd), props=len(plist[c]))
        out[c] = dict(edit=edit, model=model, perm=perm, bdhc=bd, data=data, stats=st, props=plist[c])
    return out, F


def door_checks(out, bm_files):
    t = layout.tiles()
    res = []
    buildings = {"house", "pc", "mart", "hall", "door"}
    all_props = {c: o["props"] for c, o in out.items()}
    for i, ((x, z), what) in layout.DOORS.items():
        if i in (7, 8):
            continue
        behind = t[(x, z - 1)]
        ok_b = behind[2] in buildings or (behind[2] == "stock" and behind[0] & layout.BLOCK)
        c = 72 if x < 576 else 73
        found = []
        for p in all_props[c]:
            if p["model"] not in DOOR_MODELS:
                continue
            px = (p["pos"][0] / 4096 / 16) + 16 + layout.CHUNKS[c][0] * 32
            pz = (p["pos"][2] / 4096 / 16) + 16 + layout.CHUNKS[c][1] * 32
            pm = nsbmd.parse_bmd(bm_files[p["model"]])["models"][0]["info"]
            k = pm["box_pos_scale"] / 4096 / 4096 / 16
            bx0, bx1 = px + pm["box_x"] * k, px + (pm["box_x"] + pm["box_w"]) * k
            if bx0 < x + 0.9 and bx1 > x + 0.1 and z - 0.01 <= pz <= z + 0.5:
                found.append(p["model"])
        res.append((f"warp {i} door ({x},{z}) {what}: building behind it ({behind[2]}) and a door prop on it {found}",
                    bool(ok_b and found)))
    return res


def main():
    args = sys.argv[1:]
    preview = args[args.index("--preview") + 1] if "--preview" in args else None
    write = "--write" in args
    out, F = build()
    plist_ids, bm_files = area_prop_list()
    results = []
    # stock shapes untouched, permissions/BDHC = layout, seams
    for c, o in out.items():
        edited = {o["edit"].model["shapes"][si]["name"] for si in o["edit"].faces}
        bad = C.stock_shapes_identical(o["edit"].model, o["edit"].built, edited)
        results.append((f"chunk {c}: untouched stock shapes and all stock materials byte-identical "
                        f"({len(o['edit'].model['shapes']) - len(edited)} untouched, {len(edited)} cut)", not bad))
        sec = mapdata.unpack(o["data"])
        results.append((f"chunk {c}: permissions equal the layout",
                        not collision.check_permissions(c, sec["permissions"])))
        off = collision.check(c, sec["bdhc"])
        results.append((f"chunk {c}: BDHC height at every tile centre equals the layout ({len(off)} off)", not off))
        bad_props = [p["model"] for p in o["props"] if p["model"] not in plist_ids]
        results.append((f"chunk {c}: every prop is in area 0xA's prop list ({len(o['props'])} props)", not bad_props))
    for desc, ok in layout.checks():
        if "seam" in desc or "edge" in desc or "filler" in desc:
            results.append((desc, ok))
    results += door_checks(out, bm_files)
    # budgets
    print(f"{'chunk':>5} {'polys':>6} {'stock':>6} {'new':>5} {'verts':>6} {'model B':>8} {'stock B':>8} {'BDHC B':>7} "
          f"{'mats':>4} {'props':>5} {'prop polys':>10}")
    pmeshes = {c: prop_meshes(c, o["props"], bm_files) for c, o in out.items()}
    for c, o in out.items():
        s = o["stats"]
        pp = sum(len(m["quads"]) + len(m["tris"]) for m in pmeshes[c]["meshes"])
        print(f"{c:>5} {s['polygons']:>6} {s['stock_polygons']:>6} {s['new_polygons']:>5} {s['vertices_sent']:>6} "
              f"{s['model_bytes']:>8} {s['stock_model_bytes']:>8} {s['bdhc_bytes']:>7} {s['materials']:>4} "
              f"{s['props']:>5} {pp:>10}")
        results.append((f"chunk {c}: {s['polygons']} polygons <= {POLY_LIMIT}", s["polygons"] <= POLY_LIMIT))
        results.append((f"chunk {c}: model {s['model_bytes']} B <= {MODEL_LIMIT} (45 KB; hard 0xF000 = 61440)",
                        s["model_bytes"] <= MODEL_LIMIT and s["model_bytes"] <= C.MODEL_BUFFER))
    # camera: terrain of every chunk that can be on screen + all props
    faces = []
    for c, o in out.items():
        faces += mesh_faces(nsbmd.model_to_mesh(o["edit"].built, layout.CHUNKS[c]))
        faces += mesh_faces(pmeshes[c])
    mat = json.loads(layout.git_file("res/field/maps/matrices/map_matrix_000.json"))
    for cz in (19, 20, 21):
        for cx in (16, 17, 18, 19):
            if (cx, cz) in layout.CHUNKS.values():
                continue
            name = mat["maps"][cz][cx]
            if not (name.startswith("MAP_") and name[4:].isdigit()):
                continue
            nb = int(name[4:])
            sec = mapdata.unpack(layout.git_file(layout.chunk_rel(nb)))
            faces += mesh_faces(nsbmd.model_to_mesh(nsbmd.parse_bmd(sec["model"])["models"][0], (cx, cz)))
            if sec["props"]:
                faces += mesh_faces(prop_meshes_cell((cx, cz), mapdata.read_props(sec["props"]), bm_files))
    t = layout.tiles()
    walk = [k for k, v in t.items() if not v[0] & layout.BLOCK]
    heights = {k: v[1] for k, v in t.items()}
    for name, worst, at in camera_polys(faces, walk, heights):
        print(f"camera {name}: worst {worst} polygons on screen (terrain + props of all loaded chunks) at {at}")
        results.append((f"camera {name}: {worst} polygons on screen <= {SCREEN_LIMIT}", worst <= SCREEN_LIMIT))
    nfail = 0
    for desc, ok in results:
        print(("PASS " if ok else "FAIL ") + desc)
        nfail += not ok
    if preview:
        os.makedirs(preview, exist_ok=True)
        for c, o in out.items():
            back = nsbmd.parse_bmd(o["model"])["models"][0]
            json.dump(nsbmd.model_to_mesh(back, layout.CHUNKS[c], name=f"chunk_{c:03d}"),
                      open(os.path.join(preview, f"chunk_{c:03d}.mesh.json"), "w"))
            json.dump(pmeshes[c], open(os.path.join(preview, f"props_{c:03d}.mesh.json"), "w"))
        json.dump({str(c): o["stats"] for c, o in out.items()}, open(os.path.join(preview, "stats.json"), "w"),
                  indent=1)
        import dump_stock                  # the props' own textures (TEX0), for the preview
        tdir = os.path.join(preview, "textures")
        os.makedirs(tdir, exist_ok=True)
        for m in sorted({p["model"] for o in out.values() for p in o["props"]}):
            bmd = nsbmd.parse_bmd(bm_files[m])
            if bmd["tex0"]:
                dump_stock.export_textures(bmd["tex0"], tdir,
                                           {x["texture"]: x["palette"] for x in bmd["models"][0]["materials"]})
        print("wrote preview meshes to", preview)
    if write:
        if nfail:
            print(f"REFUSING to write: {nfail} check(s) failed")
            return 1
        for c, o in out.items():
            open(os.path.join(ROOT, layout.chunk_rel(c)), "wb").write(o["data"])
            print("wrote", layout.chunk_rel(c), len(o["data"]), "B")
    print(f"{nfail} check(s) failed" if nfail else "all checks pass")
    return 1 if nfail else 0


def prop_meshes_cell(cell, plist, bm_files):
    out = {"name": "props", "materials": [], "meshes": []}
    for p in plist:
        pm = nsbmd.parse_bmd(bm_files[p["model"]])["models"][0]
        sub = nsbmd.model_to_mesh(pm, cell, name=pm["name"], offset=[v / 4096 for v in p["pos"]])
        out["materials"] += sub["materials"]
        out["meshes"] += sub["meshes"]
    return out


if __name__ == "__main__":
    sys.exit(main())
