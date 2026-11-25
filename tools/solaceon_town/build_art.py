#!/usr/bin/env python3
"""Solaceon Town art pass: final map_data_072/073, the set-010 kit append and the sol_candle fldtanime entry.
Standard library only.

Usage:
  python3 tools/solaceon_town/build_art.py                  dry run: build, print budgets and every check
  python3 tools/solaceon_town/build_art.py --preview DIR    also write DIR/art/chunk_07N.mesh.json (decoded back from
                                                            the built NSBMD), DIR/art/props_07N.mesh.json and
                                                            DIR/art/textures (kit + prop textures) for render.py --art
  python3 tools/solaceon_town/build_art.py --write          write map_data_072/073, set 010 and fldtanime.narc
                                                            (refuses if any check fails)

Inputs: the stock chunks, set 010, build models and area data from git at layout.BASE_REV (50482f890), so re-running
never feeds back on itself; the kit from tools/solaceon_town/assets/textures/ (textures_kit.py builds the set);
the tile contract from layout.py / collision.py. The current fldtanime.narc is read from the work tree and the
sol_candle entry is added or replaced by name (other entries untouched), so a second --write is byte-identical.

What it builds (docs/solaceon_redesign/art.md section 6):
  * Stock terrain outside layout.REBUILD byte for byte (tools/world_art/chunkedit.py), as the graybox: the Day Care
    ranch with the memorial wall (build_wall.py's boards are kept, not rebuilt) and the Ruins hill.
  * Ground per tile kind: stock ngrass / nsand / nsandp road edges / l_grass tall grass; the kit's warm plaza setts
    (sol_plaza), forecourt flags (sol_fcpave, origin on the emblem's NW corner), the toned-down 3x3 eclipse inlay
    (sol_emblem, four quads with mirrored UVs), packed dirt (sol_yard) and the rut lane (sol_ruts) through the truck
    bay to the road.
  * The Sanctuary hall: pale ashlar on a lilac plinth, pilasters, lit arched windows, a gabled front bay over the
    stock gym door prop (298) with the sign board and medallion, a violet hip roof with the ridge-to-eave gradient,
    steps and flower planters along the blocked door row.
  * The compound wall (ashlar + violet coping), gate pillars, the open iron gate, forecourt lanterns, supply crates.
  * The registration tent (canvas, striped valance at 1.45 tiles, table with the ledger, REGISTRY board), banner
    posts, plaza lanterns, the bench, offerings with the animated candle, the memorial plaque post, the garden kerb.
  * The excavation (scaffold, work lights, warning fence with the gap, KEEP OUT board, crates, tarp pile, cable).
  * The kennel block (boards with arched kennels, green corrugated roof, dividers, sign) and the loading yard.
    No terrain truck: story scripts put crate objects in the bay (layout.TRUCK_BAY).
  * Stock-style trees and picket fences; props, permissions and BDHC exactly as the graybox (layout.py).

Checks (--write refuses on any FAIL): permissions and BDHC equal the layout; seams; door tiles have a building and
a door prop; props in area 0xA's list; per chunk <= 1000 polygons and model <= 45 KB (hard 0xF000); untouched stock
shapes and stock materials byte-identical; on-screen polygons <= 2048 at every walkable tile (both cameras); every
walkable tile's drawn floor at its layout height and nothing drawn over a walkable tile below 1.3 tiles (except
flat decals and the overhangs listed in OVERHEAD_OK); set 010 kit <= +24 KB, set <= 76416 B, stock textures and
palettes unchanged; the candle frames share the base texture's palette and size.
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
sys.path.insert(0, HERE)

import layout  # noqa: E402
import collision  # noqa: E402
import build_graybox as B  # noqa: E402
import textures_kit as K  # noqa: E402
import chunkedit as C  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402
import png  # noqa: E402

BASE_REV = layout.BASE_REV
OUT_MAP_DIR = "res/field/mapmodels/data"                 # where the macOS app branch keeps the chunks
FLDTANIME_REL = "res/prebuilt/data/fldtanime.narc"
ANIME_ENTRY = 16 + 18 * 2
POLY_LIMIT, MODEL_LIMIT, SCREEN_LIMIT = B.POLY_LIMIT, B.MODEL_LIMIT, B.SCREEN_LIMIT
G = layout.GROUND_H

# stock set-010 textures used by the art: texture -> palette
STOCK_PAL = {"ngrass": "grass", "nsand": "sandset", "nsandp": "nsandp", "l_grass_u": "l_grass_u_pl",
             "l_grass_m": "l_grass_m_pl", "l_grass_d": "l_grass_d_pl", "tree2_01": "tree2_01", "imped": "imped",
             "nbridge": "dun_bridge", "shadowchip": "shadowchip", "nhana": "nhana"}


# ---------------------------------------------------------------------------------------------------------------
# faces -> per-chunk mesh builders
# ---------------------------------------------------------------------------------------------------------------

class Art:
    """New faces in absolute tiles (x, h, z), routed to the chunk holding their centroid. Material keys: a stock
    texture name (STOCK_PAL) or a kit name; a trailing '2' makes the material double-sided (see-through cards)."""

    def __init__(self, tex_size, kit):
        self.mb = {c: C.MeshBuilder() for c in layout.CHUNKS}
        self.tex_size = tex_size
        self.kit = kit                     # kit name -> (texture, palette, repeat)
        self.flat_decals = []              # (x0, z0, x1, z1) ground decals (allowed over walkable tiles)
        self.solids = []                   # (pts) every non-ground face, for the walkable-clearance check

    def material(self, key):
        two = key.endswith("2") and key[:-1] in self.kit
        base = key[:-1] if two else key
        if base in self.kit:
            tex, pal, rep = self.kit[base]
            name = base + ("_2s" if two else "")
        else:
            tex, pal, rep = base, STOCK_PAL[base], (True, True)
            name = "sa_" + base
        return name[:16], tex, pal, rep, "none" if two else "back"

    def add(self, key, pts, uvs, facing, solid=True):
        n = C.face_normal(pts)
        if sum(a * b for a, b in zip(n, facing)) < 0:
            pts, uvs = pts[::-1], uvs[::-1]
        name, tex, pal, rep, cull = self.material(key)
        # rebase repeating UVs per face so they stay small (s16 texture coordinates)
        uvs = [list(u) for u in uvs]
        for k in (0, 1):
            if rep[k]:
                lo = math.floor(min(u[k] for u in uvs) + 1e-6)
                for u in uvs:
                    u[k] -= lo
        cx = sum(p[0] for p in pts) / len(pts)
        c = 72 if cx < 576 else 73
        self.mb[c].material(name, tex, pal, self.tex_size[tex], cull=cull, repeat=tuple(rep))
        self.mb[c].face(name, [tuple(p) for p in pts], [tuple(u) for u in uvs])
        if solid:
            self.solids.append(pts)

    # -- primitives (uv rect = (u0, v0, u1, v1), v0 at the top / north edge)
    def flat(self, key, x0, z0, x1, z1, h, uv, decal=False):
        u0, v0, u1, v1 = uv
        self.add(key, [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)],
                 [(u0, v1), (u1, v1), (u1, v0), (u0, v0)], (0, 1, 0), solid=False)
        if decal or h <= G + 0.05:
            self.flat_decals.append((x0, z0, x1, z1))
        else:
            self.solids.append([(x0, h, z0), (x1, h, z1)])

    def wall(self, key, a, b, h0, h1, uv, solid=True):
        """Upright quad from a to b ((x, z), left to right seen from the front)."""
        (xa, za), (xb, zb) = a, b
        u0, v0, u1, v1 = uv
        n = (-(zb - za), 0.0, xb - xa)
        self.add(key, [(xa, h1, za), (xb, h1, zb), (xb, h0, zb), (xa, h0, za)],
                 [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], n, solid)

    def card(self, key, x0, x1, zb, h0, h1, uv, lean=0.0):
        """South-facing card standing on z = zb, its top leaning back (north) by `lean` degrees."""
        dz = (h1 - h0) * math.tan(math.radians(lean))
        u0, v0, u1, v1 = uv
        n = (0.0, math.sin(math.radians(lean)), math.cos(math.radians(lean)))
        self.add(key, [(x0, h1, zb - dz), (x1, h1, zb - dz), (x1, h0, zb), (x0, h0, zb)],
                 [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], n)

    def box(self, x0, z0, x1, z1, h0, h1, faces):
        """faces: {"s"/"n"/"e"/"w"/"t": (key, uv)}."""
        if "s" in faces:
            self.wall(faces["s"][0], (x0, z1), (x1, z1), h0, h1, faces["s"][1])
        if "n" in faces:
            self.wall(faces["n"][0], (x1, z0), (x0, z0), h0, h1, faces["n"][1])
        if "e" in faces:
            self.wall(faces["e"][0], (x1, z1), (x1, z0), h0, h1, faces["e"][1])
        if "w" in faces:
            self.wall(faces["w"][0], (x0, z0), (x0, z1), h0, h1, faces["w"][1])
        if "t" in faces:
            self.flat(faces["t"][0], x0, z0, x1, z1, h1, faces["t"][1])

    def polygons(self):
        return {c: mb.polygons() for c, mb in self.mb.items()}


def px(x0, y0, x1, y1, w, h):
    """Atlas pixel rect -> uv rect."""
    return (x0 / w, y0 / h, x1 / w, y1 / h)


# atlas regions (art.md section 2)
A64 = (64, 64)
HATLAS = {"window": px(32, 0, 48, 32, *A64), "oculus": px(48, 0, 64, 16, *A64), "plaque": px(49, 17, 63, 31, *A64),
          "pil_cap": px(0, 32, 16, 40, *A64), "pil_shaft": px(0, 40, 16, 56, *A64), "pil_base": px(0, 56, 16, 64, *A64),
          "medallion": px(16, 32, 48, 48, *A64), "sign": px(16, 48, 48, 64, *A64), "post": px(48, 32, 64, 64, *A64)}
EX = (64, 32)
EXATLAS = {"light": px(0, 0, 16, 32, *EX), "crate_s": px(16, 0, 32, 16, *EX), "crate_t": px(16, 16, 32, 32, *EX),
           "coil": px(32, 0, 48, 16, *EX), "cable": px(32, 16, 48, 24, *EX), "bags": px(32, 24, 48, 32, *EX),
           "keepout": px(48, 0, 64, 32, *EX)}
FURN = {"bench_side": px(0, 0, 24, 12, 32, 32), "bench_top": px(0, 12, 24, 20, 32, 32),
        "board": px(0, 20, 24, 32, 32, 32), "lantern": px(24, 0, 32, 32, 32, 32)}
OFFER = {"lilies": px(0, 0, 16, 16, 32, 32), "posy": px(16, 0, 32, 16, 32, 32), "wreath": px(0, 16, 16, 32, 32, 32),
         "photo": px(16, 16, 32, 32, 32, 32)}
E = 1 / 64          # band inset (art.md: keep 1/64 off band edges)
TRIM = {"ridge": (E, 0 + E, 8 / 32 - E), "eave": (E, 8 / 32 + E, 16 / 32 - E), "plinth": (E, 16 / 32 + E, 24 / 32 - E),
        "coping": (E, 24 / 32 + E, 1 - E), "coping_top": (E, 25 / 32, 28 / 32), "fascia": (E, 13 / 32, 16 / 32 - E)}
TENT = {"top": (0, 0, 1, 0.5 - E), "cloth": (0, 0.5 + E, 1, 0.75 - E), "board": (0, 0.75 + E, 1, 1)}


def trim(band, u0, u1):
    _, v0, v1 = TRIM[band]
    return (u0, v0, u1, v1)


# ---------------------------------------------------------------------------------------------------------------
# ground
# ---------------------------------------------------------------------------------------------------------------

DECO = B.DECO | {"pillar"}
FC_ORIGIN = (layout.EMBLEM[0], layout.EMBLEM[1])     # sol_fcpave UV origin: the emblem's NW corner (art.md rule)


LAWN_BEDS = [(572, 653, 573, 655), (586, 653, 587, 655)]   # nhana flower beds on the compound lawns (tiles, walkable)
FORECOURT = (575, 653, 585, 657)          # paved forecourt in the compound; the rest of the compound is lawn
YARD_GROUND = [(592, 656, 597, 663), (547, 663, 555, 668)]   # dirt: the dig, the kennel block and the loading yard


def ground_key(t, x, z):
    coll, h, kind = t[(x, z)]
    if any(layout.in_rect(r, x, z) for r in YARD_GROUND) and kind not in ("ruts", "bay", "fence", "trough"):
        return "sol_yard"
    if kind in DECO:
        for dx, dz in ((0, 1), (0, -1), (-1, 0), (1, 0)):
            n = t.get((x + dx, z + dz))
            if n and not n[0] & layout.BLOCK and n[2] not in ("stock", "tallgrass", "gap", "emblem", "ruts", "bay"):
                return ground_key(t, x + dx, z + dz)
        return "ngrass"
    if kind == "road" and x in layout.ROAD and not layout.in_rect(layout.PLAZA, x, z):
        return "nsandp_w" if x == layout.ROAD[0] else "nsandp_e"
    if kind == "tallgrass":
        gx0, gz0, gx1, gz1 = layout.GARDEN
        return "l_grass_u" if z == gz0 else "l_grass_d" if z == gz1 else "l_grass_m"
    if kind in ("paving",):
        if layout.in_rect(layout.COMPOUND, x, z):
            if any(layout.in_rect(r, x, z) for r in LAWN_BEDS):
                return "nhana"
            return "sol_fcpave" if layout.in_rect(FORECOURT, x, z) else "ngrass"
        return "sol_plaza"
    if kind in ("hall", "gate") or (kind == "door" and layout.in_rect(layout.HALL, x, z)):
        return "sol_fcpave"
    if kind == "wall":
        return "sol_fcpave" if x == layout.GATE[0] else "ngrass"
    if kind in ("yard", "stall", "kennel", "dig", "gap"):
        return "sol_yard"
    if kind in ("emblem", "ruts", "bay"):
        return None                  # drawn by build_emblem / build_ruts
    if kind in ("tent", "tent_floor", "table", "berry"):
        return "nsand"
    if kind == "road":
        return "nsand"
    return "ngrass"


def build_ground(F, t):
    cells = {}
    for (x, z), v in t.items():
        if layout.rebuilt(x, z):
            k = ground_key(t, x, z)
            if k:
                cells[(x, z)] = (k, 72 if x < 576 else 73)
    used = set()
    for (x, z) in sorted(cells, key=lambda p: (p[1], p[0])):
        if (x, z) in used:
            continue
        k = cells[(x, z)]
        w = 1
        while w < B.MAX_RUN and (x + w, z) not in used and cells.get((x + w, z)) == k:
            w += 1
        d = 1
        while d < B.MAX_RUN and all((x + i, z + d) not in used and cells.get((x + i, z + d)) == k for i in range(w)):
            d += 1
        for i in range(w):
            for j in range(d):
                used.add((x + i, z + j))
        key = k[0]
        if key.startswith("nsandp_"):
            # the stock road-edge mapping (map_data_074): v 0.508 on the sand side .. 0.992 on the grass side
            inner, outer = (x + 1, x) if key == "nsandp_w" else (x, x + 1)
            F.add("nsandp", [(inner, G, z), (outer, G, z), (outer, G, z + d), (inner, G, z + d)],
                  [(-d / 4, 0.508), (-d / 4, 0.992), (d / 4, 0.992), (d / 4, 0.508)], (0, 1, 0), solid=False)
            F.flat_decals.append((x, z, x + 1, z + d))
            continue
        tex = F.material(key)[1]
        rep = 16.0 / F.tex_size[tex][0]
        ox, oz = FC_ORIGIN if key == "sol_fcpave" else (0, 0)
        F.flat(key, x, z, x + w, z + d, G, ((x - ox) * rep, (z - oz) * rep, (x + w - ox) * rep, (z + d - oz) * rep))


def build_emblem(F):
    """3x3 inlay as four quads; the texture holds one quadrant (texels 0..23 = 1.5 tiles), mirrored by the UVs."""
    x0, z0, x1, z1 = layout.EMBLEM
    cx, cz = (x0 + x1 + 1) / 2, (z0 + z1 + 1) / 2
    q = 24 / 32
    for (a, b, ua, ub) in ((x0, cx, 0, q), (cx, x1 + 1, q, 0)):
        for (c, d, va, vb) in ((z0, cz, 0, q), (cz, z1 + 1, q, 0)):
            F.flat("sol_emblem", a, c, b, d, G, (ua, va, ub, vb))


def build_ruts(F):
    """The rut lane: 2 tiles wide (z 666..668), from the truck bay's west end to the road verge. sol_ruts runs its
    ruts along t, so u goes across the lane (z) and v along it (x)."""
    bx0, bz0, bx1, bz1 = layout.TRUCK_BAY
    xa, xb, za, zb = bx0, layout.ROAD[0] - 1, bz0, bz1 + 1
    # (x, z) -> (u = (z - za) / 2, v = (x - xa) / 2)
    pts = [(xa, G, zb), (xb, G, zb), (xb, G, za), (xa, G, za)]
    uvs = [((p[2] - za) / 2, (p[0] - xa) / 2) for p in pts]
    F.add("sol_ruts", pts, uvs, (0, 1, 0), solid=False)
    F.flat_decals.append((xa, za, xb, zb))


# ---------------------------------------------------------------------------------------------------------------
# trees and fences (stock style)
# ---------------------------------------------------------------------------------------------------------------

def build_trees(F):
    for tx, tz in layout.TREES:
        for pts, uvs in B.TREE_QUADS:
            P = [(tx + p[0], p[1], tz + p[2]) for p in pts]
            F.add("tree2_01", P, uvs, C.face_normal(P), solid=False)     # stock overhang, as stock trees


def build_fences(F, t):
    fence = {k for k, v in t.items() if v[2] == "fence" and layout.rebuilt(*k) and k[1] != layout.DIG_FENCE_Z}
    ew = {(x, z) for x, z in fence if (x - 1, z) in fence or (x + 1, z) in fence or
          not ((x, z - 1) in fence or (x, z + 1) in fence)}
    ns = {(x, z) for x, z in fence if (x, z - 1) in fence or (x, z + 1) in fence}
    for z, x0, x1 in B.runs(ew, "x"):
        # the stock east-west picket fence: leaning back 45 degrees, imped row v 0..0.25, u 0.25 per tile
        for a in range(x0, x1 + 1, 4):
            b = min(a + 4, x1 + 1)
            F.add("imped", [(a, G + 0.02, z + 0.85), (b, G + 0.02, z + 0.85), (b, G + 0.73, z + 0.15),
                            (a, G + 0.73, z + 0.15)], [(0, 0.25), ((b - a) * 0.25, 0.25), ((b - a) * 0.25, 0), (0, 0)],
                  (0, 0.7, 0.7))
    for x, z0, z1 in B.runs(ns, "z"):
        # the stock north-south fence: a flat rail strip at h +0.375, imped v 0.312..0.438, u 0.25 per tile along z
        a, b = z0 + 0.5, z1 + 0.5
        F.add("imped", [(x + 0.25, G + 0.375, b), (x + 0.75, G + 0.375, b), (x + 0.75, G + 0.375, a),
                        (x + 0.25, G + 0.375, a)], [((b - a) * 0.25, 0.438), ((b - a) * 0.25, 0.312), (0, 0.312),
                                                    (0, 0.438)], (0, 1, 0))


# ---------------------------------------------------------------------------------------------------------------
# Sanctuary hall
# ---------------------------------------------------------------------------------------------------------------

HALL_X0, HALL_X1 = 576.1, 584.9          # body
HALL_ZN, HALL_ZW = 648.15, 651.45        # back wall, wing fronts
BAY_X0, BAY_X1, BAY_Z = 578.6, 582.4, 651.98    # front bay; the gym door prop stands on z 652.0
DOOR_X0, DOOR_X1, DOOR_TOP = 579.6, 581.4, G + 2.78   # opening behind the door prop (it spans 579.62..581.38, h 1.12..3.75)
WING_H, BAY_H, APEX_H, RIDGE_H = G + 2.5, G + 3.5, G + 5.0, G + 4.0
EAVE_O = 0.3                             # roof overhang


def stone_wall(F, a, b, h1, plinth=True, h0=G):
    """Pale ashlar (sol_hwall, 2 tiles per repeat) above a 0.5-tile lilac plinth (sol_htrim band 2)."""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    ua = (a[0] + a[1]) / 2
    hb = h0 + 0.5 if plinth else h0
    if plinth:
        F.wall("sol_htrim", a, b, h0, hb, trim("plinth", ua, ua + L / 2))
    # v from the top of the 2-tile repeat so courses line up across walls of different heights
    F.wall("sol_hwall", a, b, hb, h1, (ua, (G + 4.0 - h1) / 2, ua + L / 2, (G + 4.0 - hb) / 2))


def pilaster(F, x0, x1, z, h0, h1):
    F.card("sol_hatlas", x0, x1, z, h1 - 0.45, h1, HATLAS["pil_cap"])
    F.card("sol_hatlas", x0, x1, z, h0 + 0.45, h1 - 0.45, HATLAS["pil_shaft"])
    F.card("sol_hatlas", x0, x1, z, h0, h0 + 0.45, HATLAS["pil_base"])


def build_hall(F):
    X0, X1, ZN, ZW = HALL_X0, HALL_X1, HALL_ZN, HALL_ZW
    # wing fronts, body sides (the north wall is never seen by the field camera)
    stone_wall(F, (X0, ZW), (BAY_X0, ZW), WING_H)
    stone_wall(F, (BAY_X1, ZW), (X1, ZW), WING_H)
    stone_wall(F, (X0, ZN), (X0, ZW), WING_H)
    stone_wall(F, (X1, ZW), (X1, ZN), WING_H)
    # front bay: sides, front around the door opening, the gable
    stone_wall(F, (BAY_X0, ZW), (BAY_X0, BAY_Z), BAY_H)
    stone_wall(F, (BAY_X1, BAY_Z), (BAY_X1, ZW), BAY_H)
    stone_wall(F, (BAY_X0, BAY_Z), (DOOR_X0, BAY_Z), BAY_H)
    stone_wall(F, (DOOR_X1, BAY_Z), (BAY_X1, BAY_Z), BAY_H)
    F.wall("sol_hwall", (DOOR_X0, BAY_Z), (DOOR_X1, BAY_Z), DOOR_TOP, BAY_H,
           ((DOOR_X0 + BAY_Z) / 2, (G + 4.0 - BAY_H) / 2, (DOOR_X1 + BAY_Z) / 2, (G + 4.0 - DOOR_TOP) / 2))
    F.wall("shadowchip", (DOOR_X0, BAY_Z - 0.3), (DOOR_X1, BAY_Z - 0.3), G, DOOR_TOP, (0, 0, 1, 1))  # dark doorway
    ua = (BAY_X0 + BAY_Z) / 2
    F.add("sol_hwall", [(BAY_X0, BAY_H, BAY_Z), (BAY_X1, BAY_H, BAY_Z), ((BAY_X0 + BAY_X1) / 2, APEX_H, BAY_Z)],
          [(ua, (G + 4.0 - BAY_H) / 2), (ua + (BAY_X1 - BAY_X0) / 2, (G + 4.0 - BAY_H) / 2),
           (ua + (BAY_X1 - BAY_X0) / 4, (G + 4.0 - APEX_H) / 2)], (0, 0, 1))
    mx = (BAY_X0 + BAY_X1) / 2
    F.card("sol_hatlas", mx - 0.7, mx + 0.7, BAY_Z + 0.02, BAY_H + 0.12, BAY_H + 0.82, HATLAS["medallion"])
    F.card("sol_hatlas", mx - 0.68, mx + 0.68, BAY_Z + 0.02, DOOR_TOP + 0.06, BAY_H - 0.06, HATLAS["sign"])
    # pilasters: the wing corners and either side of the door
    pilaster(F, X0, X0 + 0.55, ZW + 0.02, G, WING_H)
    pilaster(F, X1 - 0.55, X1, ZW + 0.02, G, WING_H)
    pilaster(F, BAY_X0 + 0.1, DOOR_X0 - 0.12, BAY_Z + 0.02, G, BAY_H - 0.02)
    pilaster(F, DOOR_X1 + 0.12, BAY_X1 - 0.1, BAY_Z + 0.02, G, BAY_H - 0.02)
    # lit arched windows, centred on the wing fronts
    for wx in ((X0 + 0.55 + BAY_X0) / 2, (BAY_X1 + X1 - 0.55) / 2):
        F.card("sol_hatlas", wx - 0.4, wx + 0.4, ZW + 0.02, G + 0.6, G + 2.15, HATLAS["window"])
    # eave fascia (tile ends over the gold line) under the hip roof's edges
    e0, e1, f0, f1 = X0 - EAVE_O, X1 + EAVE_O, ZN - EAVE_O, ZW + EAVE_O
    for a, b in (((e0, f1), (BAY_X0, f1)), ((BAY_X1, f1), (e1, f1)), ((e0, f0), (e0, f1)), ((e1, f1), (e1, f0))):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        F.wall("sol_htrim", a, b, WING_H - 0.28, WING_H + 0.02, trim("eave", 0, L / 2))
    # hip roof: v 0 at the ridge, 1 at the eave (sol_hroof bakes the ridge-to-eave gradient)
    zr = (f0 + f1) / 2
    r0, r1 = e0 + (zr - f0), e1 - (zr - f0)
    W, R = WING_H, RIDGE_H
    F.add("sol_hroof", [(e0, W, f1), (e1, W, f1), (r1, R, zr), (r0, R, zr)],
          [(e0 / 2, 1), (e1 / 2, 1), (r1 / 2, 0), (r0 / 2, 0)], (0, 1, 1))
    F.add("sol_hroof", [(e1, W, f0), (e0, W, f0), (r0, R, zr), (r1, R, zr)],
          [(e1 / 2, 1), (e0 / 2, 1), (r0 / 2, 0), (r1 / 2, 0)], (0, 1, -1))
    F.add("sol_hroof", [(e0, W, f0), (e0, W, f1), (r0, R, zr)], [(f0 / 2, 1), (f1 / 2, 1), (zr / 2, 0)], (-1, 1, 0))
    F.add("sol_hroof", [(e1, W, f1), (e1, W, f0), (r1, R, zr)], [(f1 / 2, 1), (f0 / 2, 1), (zr / 2, 0)], (1, 1, 0))
    F.wall("sol_htrim", (r0, zr), (r1, zr), R - 0.08, R + 0.22, trim("ridge", 0, (r1 - r0) / 2))
    # the bay's gable roof, its ridge over the door axis, running back into the hip roof
    ge0, ge1, gz1 = BAY_X0 - EAVE_O, BAY_X1 + EAVE_O, BAY_Z + 0.32
    eh, rh = BAY_H - 0.1, APEX_H + 0.12
    F.add("sol_hroof", [(ge0, eh, gz1), (mx, rh, gz1), (mx, rh, zr), (ge0, eh, zr)],
          [(gz1 / 2, 1), (gz1 / 2, 0), (zr / 2, 0), (zr / 2, 1)], (-1, 1, 0))
    F.add("sol_hroof", [(mx, rh, gz1), (ge1, eh, gz1), (ge1, eh, zr), (mx, rh, zr)],
          [(gz1 / 2, 0), (gz1 / 2, 1), (zr / 2, 1), (zr / 2, 0)], (1, 1, 0))
    _, fv0, fv1 = TRIM["eave"]
    L = math.hypot(mx - ge0, rh - eh)
    F.add("sol_htrim", [(ge0, eh - 0.24, gz1 + 0.01), (mx, rh - 0.24, gz1 + 0.01), (mx, rh + 0.04, gz1 + 0.01),
                        (ge0, eh + 0.04, gz1 + 0.01)], [(0, fv1), (L / 2, fv1), (L / 2, fv0), (0, fv0)], (0, 0, 1))
    F.add("sol_htrim", [(mx, rh - 0.24, gz1 + 0.01), (ge1, eh - 0.24, gz1 + 0.01), (ge1, eh + 0.04, gz1 + 0.01),
                        (mx, rh + 0.04, gz1 + 0.01)], [(0, fv1), (L / 2, fv1), (L / 2, fv0), (0, fv0)], (0, 0, 1))
    # the blocked door row: steps up to the door across the bay, flower planters in front of the wings
    sx0, sx1 = BAY_X0, BAY_X1
    sw = sx1 - sx0
    for (za, zb, h, v0) in ((BAY_Z, BAY_Z + 0.45, G + 0.24, 0.0), (BAY_Z + 0.45, BAY_Z + 0.9, G + 0.12, 0.25)):
        F.flat("sol_steps", sx0, za, sx1, zb, h, (0, v0, 1, v0 + 0.13))
        F.wall("sol_steps", (sx0, zb), (sx1, zb), h - 0.12, h, (0, v0 + 0.13, 1, v0 + 0.25))
    ph = G + 0.4
    for (a, b) in ((X0, BAY_X0 - 0.04), (BAY_X1 + 0.04, X1)):
        z0, z1 = ZW + 0.03, BAY_Z + 0.88
        F.box(a, z0, b, z1, G, ph, {"s": ("sol_htrim", trim("plinth", 0, (b - a) / 2)),
                                     "e": ("sol_htrim", trim("plinth", 0, (z1 - z0) / 2)),
                                     "w": ("sol_htrim", trim("plinth", 0, (z1 - z0) / 2))})
        F.flat("nhana", a + 0.06, z0, b - 0.06, z1 - 0.06, ph, (a, z0, b - 0.12, z1 - 0.06))


# ---------------------------------------------------------------------------------------------------------------
# compound wall, gate, forecourt
# ---------------------------------------------------------------------------------------------------------------

WALL_T0, WALL_T1 = 0.3, 0.7              # wall thickness within its tile
WALL_FACE_H, WALL_H = G + 0.55, G + 0.95


def low_wall(F, a, b):
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    ua = (a[0] + a[1]) / 2
    F.wall("sol_hwall", a, b, G, WALL_FACE_H, (ua, 0.5 - 0.275, ua + L / 2, 0.5))
    F.wall("sol_htrim", a, b, WALL_FACE_H, WALL_H, trim("coping", ua, ua + L / 2))


def split576(a, b):
    """Split an x-run at the chunk seam so each piece stays in its chunk."""
    if a < 576 < b:
        return [(a, 576.0), (576.0, b)]
    return [(a, b)]


def build_compound(F):
    cx0, cz0, cx1, cz1 = layout.COMPOUND
    gx = layout.GATE[0]
    xa, xb = cx0 + WALL_T0, cx1 + WALL_T1             # outer extents
    za, zb = cz0 + WALL_T0, cz1 + WALL_T1
    _, cv0, cv1 = TRIM["coping_top"]
    # north wall: its inner (south) face and top
    for a, b in split576(xa, xb):
        low_wall(F, (a, cz0 + WALL_T1), (b, cz0 + WALL_T1))
        F.flat("sol_htrim", a, cz0 + WALL_T0, b, cz0 + WALL_T1, WALL_H, (a / 2, cv0, b / 2, cv1))
    # south wall either side of the gate pillars: outer (south) face and top
    for a, b in ((xa, gx - 1 + 0.1), (gx + 1 + 0.9, xb)):
        for p, q in split576(a, b):
            low_wall(F, (p, cz1 + WALL_T1), (q, cz1 + WALL_T1))
            F.flat("sol_htrim", p, cz1 + WALL_T0, q, cz1 + WALL_T1, WALL_H, (p / 2, cv0, q / 2, cv1))
    # west and east walls: both faces and the top
    for x in (cx0, cx1):
        low_wall(F, (x + WALL_T0, za), (x + WALL_T0, zb))          # west face
        low_wall(F, (x + WALL_T1, zb), (x + WALL_T1, za))          # east face
        F.add("sol_htrim", [(x + WALL_T0, WALL_H, zb), (x + WALL_T1, WALL_H, zb), (x + WALL_T1, WALL_H, za),
                            (x + WALL_T0, WALL_H, za)], [(zb / 2, cv1), (zb / 2, cv0), (za / 2, cv0), (za / 2, cv1)],
              (0, 1, 0), solid=True)
    # gate pillars (the gate plaque sign is the west one) and caps
    for x, z in layout.GATE_PILLARS:
        f = ("sol_hatlas", HATLAS["post"])
        F.box(x + 0.1, z + 0.12, x + 0.9, z + 0.88, G, G + 1.9, {"s": f, "e": f, "w": f})
        F.box(x + 0.04, z + 0.06, x + 0.96, z + 0.94, G + 1.9, G + 2.02,
              {"s": ("sol_htrim", trim("coping", 0, 0.46)), "e": ("sol_htrim", trim("coping", 0, 0.44)),
               "w": ("sol_htrim", trim("coping", 0, 0.44)), "t": ("sol_htrim", (0, cv0, 0.46, cv1))})
    # iron railings (gold spear tips) on the street-side wall either side of the gate; the gate itself stands open
    rz = cz1 + (WALL_T0 + WALL_T1) / 2
    for a, b in ((xa + 0.15, gx - 1 + 0.08), (gx + 1 + 0.92, xb - 0.15)):
        for p, q in split576(a, b):
            F.wall("sol_gate2", (p, rz), (q, rz), WALL_H, WALL_H + 0.62, (p / 2, 0.38, q / 2, 1.0))
    # forecourt lanterns
    for x, z in layout.LANTERNS[4:]:
        lantern(F, x, z)
    # supply crates in the west yard
    for x, z in layout.CRATES[:3]:
        crate(F, x + 0.1, z + 0.12, 0.8)
    crate(F, 571.2, 648.2, 0.6, h0=G + 0.8)


def crate(F, x0, z0, s, h0=G):
    cs, ct = ("sol_exatlas", EXATLAS["crate_s"]), ("sol_exatlas", EXATLAS["crate_t"])
    F.box(x0, z0, x0 + s, z0 + s, h0, h0 + s, {"s": cs, "e": cs, "w": cs, "t": ct})


def lantern(F, x, z):
    F.card("sol_furn2", x + 0.25, x + 0.75, z + 0.7, G, G + 2.0, FURN["lantern"], lean=14)


# ---------------------------------------------------------------------------------------------------------------
# pilgrim road, tent, plaza
# ---------------------------------------------------------------------------------------------------------------

def build_tent(F):
    x0, z0, x1, z1 = layout.TENT
    # the back canvas stands just inside the fence row (z0 - 1) so the clerk's tile only has the roof over it;
    # the front poles stand on the table row's south edge, not on the queue tiles
    X0, X1, ZB, ZF = x0 + 0.02, x1 + 0.98, z0 - 0.02, z1 + 1.02
    wall_h, ridge, zr = G + 1.95, G + 2.7, (ZB + ZF) / 2
    F.wall("sol_canvas", (X0, ZB), (X1, ZB), G, wall_h, (0, 0, (X1 - X0) / 2, 1.0))
    F.wall("sol_canvas", (X0, ZB), (X0, ZF), G, wall_h, (0, 0, (ZF - ZB) / 2, 1.0))
    F.wall("sol_canvas", (X1, ZF), (X1, ZB), G, wall_h, (0, 0, (ZF - ZB) / 2, 1.0))
    for x, f in ((X0, -1), (X1, 1)):           # gable ends
        pts = [(x, wall_h, ZB), (x, wall_h, ZF), (x, ridge, zr)]
        F.add("sol_canvas", pts, [(0, 0.4), (1, 0.4), (0.5, 0)], (f, 0, 0))
    sl = math.hypot(ZF + 0.1 - zr, ridge - wall_h) / 2
    F.add("sol_canvas", [(X0 - 0.1, wall_h, ZF + 0.1), (X1 + 0.1, wall_h, ZF + 0.1), (X1 + 0.1, ridge, zr),
                         (X0 - 0.1, ridge, zr)], [(0, sl), ((X1 - X0) / 2, sl), ((X1 - X0) / 2, 0), (0, 0)], (0, 1, 1))
    F.add("sol_canvas", [(X1 + 0.1, wall_h, ZB - 0.1), (X0 - 0.1, wall_h, ZB - 0.1), (X0 - 0.1, ridge, zr),
                         (X1 + 0.1, ridge, zr)], [(0, sl), ((X1 - X0) / 2, sl), ((X1 - X0) / 2, 0), (0, 0)], (0, 1, -1))
    # striped valance across the open south front (bottom 1.45 tiles up, art.md rule >= 1.4)
    F.wall("sol_awning2", (X0 - 0.1, ZF + 0.11), (X1 + 0.1, ZF + 0.11), G + 1.45, wall_h + 0.06,
           (0, 0, (X1 - X0 + 0.2) / 2, 1 - E))
    # front poles
    for p in (X0 + 0.02, X1 - 0.1):
        F.wall("nbridge", (p, ZF - 0.05), (p + 0.08, ZF - 0.05), G, G + 1.5, (0, 0, 0.04, 0.75))
    # the table (tile row z1, behaviour TABLE) with the ledger and name cards, its front cloth
    tx0, tx1, tz0, tz1 = x0 + 0.12, x1 + 0.88, z1 + 0.18, z1 + 0.86
    F.box(tx0, tz0, tx1, tz1, G, G + 0.6, {"s": ("sol_tent", TENT["cloth"]), "t": ("sol_tent", TENT["top"]),
                                          "e": ("sol_canvas", (0, 0, 0.35, 0.3)), "w": ("sol_canvas", (0, 0, 0.35, 0.3))})
    # record boxes either side of the clerk
    for bx in (x0, x1):
        crate(F, bx + 0.18, z0 + 0.25, 0.62)
    # REGISTRY board over the valance
    F.card("sol_tent", x0 + 0.45, x1 + 0.55, ZF + 0.13, wall_h + 0.04, wall_h + 0.5, TENT["board"], lean=10)
    # tent sign: the Eclipse sign board on a post
    sx, sz = layout.TENT_SIGN_POST
    F.wall("nbridge", (sx + 0.46, sz + 0.6), (sx + 0.54, sz + 0.6), G, G + 0.9, (0, 0, 0.04, 0.45))
    F.card("sol_hatlas", sx + 0.06, sx + 0.94, sz + 0.64, G + 0.62, G + 1.06, HATLAS["sign"], lean=15)


def build_posts(F):
    for x, z in layout.BANNER_POSTS:
        F.card("sol_banner2", x + 0.02, x + 0.98, z + 0.6, G, G + 2.1, (0, 0, 1, 1), lean=18)
    for x, z in layout.LANTERNS[:4]:
        lantern(F, x, z)
    # the bench along x 563, facing the wall (west): slatted seat, backrest on its east edge, end boards
    bx, bz0, bz1 = layout.BENCHES[0][0], layout.BENCHES[0][1], layout.BENCHES[-1][1] + 1
    s0, s1, sh = bx + 0.2, bx + 0.68, G + 0.42
    u0, v0, u1, v1 = FURN["bench_top"]
    F.add("sol_furn", [(s0, sh, bz1 - 0.12), (s1, sh, bz1 - 0.12), (s1, sh, bz0 + 0.12), (s0, sh, bz0 + 0.12)],
          [(u0, v0), (u0, v1), (u1, v1), (u1, v0)], (0, 1, 0))
    F.wall("sol_furn", (s0, bz0 + 0.12), (s0, bz1 - 0.12), sh - 0.1, sh, (u0, v0, u1, v0 + 2 / 32))
    F.add("sol_furn", [(s1, sh, bz1 - 0.12), (s1 + 0.2, sh + 0.45, bz1 - 0.12), (s1 + 0.2, sh + 0.45, bz0 + 0.12),
                       (s1, sh, bz0 + 0.12)], [(u0, v1), (u0, v0), (u1, v0), (u1, v1)], (-1, 0.5, 0))
    for zz in (bz1 - 0.16, bz0 + 0.2):
        F.card("sol_furn2", s0, s1 + 0.2, zz, G, sh + 0.45, px(0, 0, 4, 12, 32, 32))
    # offerings at both ends of the wall: wreath on its easel, lilies, photo with candles, the animated candle dish
    (ox1, oz1), (ox2, oz2) = layout.OFFERINGS
    F.card("sol_offer2", ox1 + 0.05, ox1 + 0.95, oz1 + 0.5, G, G + 1.0, OFFER["wreath"], lean=22)
    F.card("sol_offer2", ox1 + 0.0, ox1 + 0.65, oz1 + 0.84, G, G + 0.65, OFFER["lilies"], lean=25)
    F.card("sol_candle2", ox1 + 0.5, ox1 + 0.98, oz1 + 0.88, G, G + 0.48, (0, 0, 1, 1), lean=25)
    F.card("sol_offer2", ox2 + 0.05, ox2 + 0.95, oz2 + 0.5, G, G + 1.0, OFFER["photo"], lean=22)
    F.card("sol_offer2", ox2 + 0.35, ox2 + 1.0, oz2 + 0.84, G, G + 0.65, OFFER["posy"], lean=25)
    F.card("sol_candle2", ox2 + 0.02, ox2 + 0.5, oz2 + 0.88, G, G + 0.48, (0, 0, 1, 1), lean=25)
    # the memorial plaque post (band F text): a stone lectern facing the reading tile east of it
    mx, mz = layout.MEMORIAL_PLAQUE
    F.box(mx + 0.25, mz + 0.3, mx + 0.75, mz + 0.75, G, G + 0.6,
          {"s": ("sol_hwall", (0, 0.2, 0.25, 0.5)), "e": ("sol_hwall", (0, 0.2, 0.22, 0.5)),
           "w": ("sol_hwall", (0, 0.2, 0.22, 0.5))})
    F.add("sol_hatlas", [(mx + 0.2, G + 0.85, mz + 0.8), (mx + 0.8, G + 0.6, mz + 0.8), (mx + 0.8, G + 0.6, mz + 0.25),
                         (mx + 0.2, G + 0.85, mz + 0.25)],
          [(HATLAS["plaque"][0], HATLAS["plaque"][3]), (HATLAS["plaque"][2], HATLAS["plaque"][3]),
           (HATLAS["plaque"][2], HATLAS["plaque"][1]), (HATLAS["plaque"][0], HATLAS["plaque"][1])], (0.4, 1, 0))
    # garden of names: a kerb with name lines along its plaza side (sol_border's kerb half)
    gx0, gz0, gx1, gz1 = layout.GARDEN
    F.add("sol_border", [(gx0 - 0.42, G + 0.012, gz1 + 1), (gx0, G + 0.012, gz1 + 1), (gx0, G + 0.012, gz0),
                         (gx0 - 0.42, G + 0.012, gz0)],
          [((gz1 + 1 - gz0) / 2, 1 - E), ((gz1 + 1 - gz0) / 2, 0.5), (0, 0.5), (0, 1 - E)], (0, 1, 0), solid=False)
    F.flat_decals.append((gx0 - 0.42, gz0, gx0, gz1 + 1))


# ---------------------------------------------------------------------------------------------------------------
# excavation
# ---------------------------------------------------------------------------------------------------------------

def build_excavation(F):
    sc = set(layout.SCAFFOLD)
    for z, a, b in B.runs(sc, "x"):
        x0, x1 = a + 0.02, b + 0.98
        F.wall("sol_scaff2", (x0, z + 0.72), (x1, z + 0.72), G, G + 2.0, (x0 / 2, 0, x1 / 2, 1))
        F.wall("sol_scaff2", (x1, z + 0.72), (x1, z + 0.08), G, G + 2.0, (0, 0, 0.32, 1))
        F.wall("sol_scaff2", (x0, z + 0.08), (x0, z + 0.72), G, G + 2.0, (0, 0, 0.32, 1))
        # plank deck; the west scaffold's deck is covered by a blue tarp
        deck = "sol_tarp" if a == layout.SCAFFOLD[0][0] else "nbridge"
        F.flat(deck, x0, z + 0.08, x1, z + 0.72, G + 2.0, (0, 0, (x1 - x0) / 2, 0.32))
    for x, z in layout.WORKLIGHTS:
        F.card("sol_exatlas2", x + 0.05, x + 0.95, z + 0.55, G, G + 1.9, EXATLAS["light"], lean=15)
    # crates by the east light; a tarp-covered pile by the west one
    (wx, wz), (ex, ez) = layout.CRATES[3], layout.CRATES[4]
    crate(F, ex + 0.08, ez + 0.1, 0.82)
    crate(F, ex + 0.25, ez + 0.2, 0.5, h0=G + 0.82)
    # a spoil heap from the dig by the west light (stock criffp texels in the sol_spoil earth palette)
    a0, b0, a1, b1, ht = wx + 0.05, wz + 0.08, wx + 0.95, wz + 0.95, G + 0.55
    c0, d0, c1, d1 = a0 + 0.25, b0 + 0.22, a1 - 0.22, b1 - 0.3
    for pts, n in (([(a0, G, b1), (a1, G, b1), (c1, ht, d1), (c0, ht, d1)], (0, 1, 1)),
                   ([(a1, G, b0), (a0, G, b0), (c0, ht, d0), (c1, ht, d0)], (0, 1, -1)),
                   ([(a0, G, b0), (a0, G, b1), (c0, ht, d1), (c0, ht, d0)], (-1, 1, 0)),
                   ([(a1, G, b1), (a1, G, b0), (c1, ht, d0), (c1, ht, d1)], (1, 1, 0))):
        F.add("sol_spoil", pts, [(0, 0.5), (0.45, 0.5), (0.35, 0.22), (0.1, 0.22)], n)
    F.flat("sol_spoil", c0, d0, c1, d1, ht, (0.1, 0.0, 0.35, 0.22))
    # warning fence on z 659 with the gap; posts lean back like the stock picket fence
    fz = layout.DIG_FENCE_Z
    runs = B.runs({(x, fz) for x in range(layout.DIG_YARD[0], layout.DIG_YARD[2] + 1) if (x, fz) != layout.GAP}, "x")
    for z, a, b in runs:
        x0, x1 = a + 0.02, b + 0.98
        F.add("sol_wfence2", [(x0, G + 0.02, z + 0.8), (x1, G + 0.02, z + 0.8), (x1, G + 0.85, z + 0.3),
                              (x0, G + 0.85, z + 0.3)], [(0, 1 - E), ((x1 - x0) / 2, 1 - E), ((x1 - x0) / 2, 0), (0, 0)],
              (0, 0.5, 0.86))
    # KEEP OUT board on the warning-sign tile, in front of the fence
    sx, sz = layout.SIGNS["EXCAVATION_WARNING_SIGN"][0]
    F.card("sol_exatlas2", sx + 0.12, sx + 0.88, sz + 0.88, G, G + 1.5, EXATLAS["keepout"], lean=12)
    # a cable from the lights to the cave mouth, sandbags at the scaffold foot (flat decals)
    for x in range(layout.DIG_YARD[0], layout.GAP[0]):
        F.flat("sol_exatlas", x, 657.62, x + 1, 657.92, G + 0.01, EXATLAS["cable"], decal=True)
    F.flat("sol_exatlas", 593.1, 656.72, 594.0, 657.12, G + 0.01, EXATLAS["bags"], decal=True)


# ---------------------------------------------------------------------------------------------------------------
# ranch: kennel block
# ---------------------------------------------------------------------------------------------------------------

def build_kennel(F):
    x0, z0, x1, z1 = layout.KENNEL
    X0, X1, ZB, ZF = x0 + 0.02, x1 + 0.98, z0 + 0.04, z0 + 0.92
    top = G + 1.5
    # front: boards with one arched kennel per stall (texture centre on each stall's tile centre)
    ua = (X0 - (layout.KENNEL_STALLS[0][0] - 0.5)) / 2
    F.wall("sol_kwall", (X0, ZF), (X1, ZF), G, top, (ua, 0.2, ua + (X1 - X0) / 2, 1 - E))
    F.wall("sol_kwall", (X1, ZF), (X1, ZB), G, top, (0, 0.02, 0.44, 0.28))
    F.wall("sol_kwall", (X0, ZB), (X0, ZF), G, top, (0, 0.02, 0.44, 0.28))
    # mono-pitch corrugated roof, high at the back, overhanging the front
    rb, rf = G + 2.05, top - 0.05
    rz0, rz1 = ZB - 0.15, ZF + 0.3
    L = math.hypot(rz1 - rz0, rb - rf)
    F.add("sol_kroof", [(X0 - 0.12, rf, rz1), (X1 + 0.12, rf, rz1), (X1 + 0.12, rb, rz0), (X0 - 0.12, rb, rz0)],
          [(0, L), ((X1 - X0 + 0.24) / 2, L), ((X1 - X0 + 0.24) / 2, 0), (0, 0)], (0, 1, 0.4))
    for x, f in ((X0, -1), (X1, 1)):           # the end walls' sloping tops
        F.add("sol_kwall", [(x, top, ZF), (x, top, ZB), (x, rb - 0.05, ZB)] if f > 0 else
              [(x, top, ZB), (x, top, ZF), (x, rb - 0.05, ZB)], [(0, 0.28), (0.44, 0.28), (0.44, 0.02)], (f, 0, 0))
    F.wall("sol_kroof", (X0 - 0.12, rz1), (X1 + 0.12, rz1), rf - 0.08, rf, (0, 0, (X1 - X0) / 2, 0.15))
    # board dividers between the stalls
    for x in range(x0, x1 + 1):
        if (x, z1) in layout.KENNEL_STALLS:
            continue
        d0, d1 = x + 0.38, x + 0.62
        bd = ("sol_kwall", (0.1, 0.02, 0.5, 0.28))
        F.box(d0, ZF, d1, z1 + 0.88, G, G + 0.95, {"s": ("sol_kwall", (0.1, 0.02, 0.2, 0.28)), "e": bd, "w": bd,
                                                   "t": ("sol_kwall", (0.1, 0.03, 0.5, 0.05))})
    # the kennel sign on the end divider
    sx, sz = layout.SIGNS["KENNEL_SIGN"][0]
    F.card("sol_hatlas", sx + 0.18, sx + 0.82, sz + 0.9, G + 0.45, G + 1.05, HATLAS["plaque"], lean=10)


# ---------------------------------------------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------------------------------------------

def art_faces(tex_size, kit):
    t = layout.tiles()
    F = Art(tex_size, kit)
    build_ground(F, t)
    build_emblem(F)
    build_ruts(F)
    build_trees(F)
    build_fences(F, t)
    build_compound(F)
    build_hall(F)
    build_tent(F)
    build_posts(F)
    build_excavation(F)
    build_kennel(F)
    return F


def kit_set():
    """Set 010 = stock (git, BASE_REV) + the kit, via textures_kit.build. -> (bytes, rows, fails, binds, vram, kit
    material table {name: (texture, palette, repeat)}, metas)."""
    kit, missing = K.load_kit()
    base = K.git_bytes(K.BASE_REV, K.BASE_SET_REL)
    out, rows, fails, binds, vr = K.build(base, kit)
    if missing:
        fails.append(f"kit textures missing: {missing}")
    metas = {n: m for n, m, _ in kit}
    table = {}
    for name, tex, pal in binds:
        rep = metas[name].get("repeat", [True, True])
        table[name] = (tex, pal, (bool(rep[0]), bool(rep[1])))
    return out, rows, fails, vr, table, metas


def build():
    set_bytes, kit_rows, kit_fails, vram, kit_table, metas = kit_set()
    tex_table, pal_names = C.texture_table(set_bytes)
    tex_size = {k: v["size"] for k, v in tex_table.items()}
    missing = sorted(set(STOCK_PAL) - set(tex_table)) + sorted(set(STOCK_PAL.values()) - pal_names)
    assert not missing, f"not in set 010: {missing}"
    F = art_faces(tex_size, kit_table)
    plist = B.props()
    out = {}
    for c, cell in layout.CHUNKS.items():
        edit = C.ChunkEdit(layout.chunk_rel(c), cell, BASE_REV)
        stock_tex = sorted({m["texture"] for m in edit.model["materials"] if m["texture"]})
        edit.clip_flat(stock_tex, B.clip_rects(c))
        edit.add(F.mb[c], tex_table)
        model = edit.model_bytes()
        perm = collision.permissions(c)
        bd = collision.bdhc(c)
        data = mapdata.pack(perm, mapdata.write_props(plist[c]), model, bd)
        st = edit.stats(model)
        st.update(new_polygons=F.mb[c].polygons(), bdhc_bytes=len(bd), props=len(plist[c]))
        out[c] = dict(edit=edit, model=model, perm=perm, bdhc=bd, data=data, stats=st, props=plist[c])
    return out, F, dict(set=set_bytes, rows=kit_rows, fails=kit_fails, vram=vram, table=kit_table, metas=metas)


# ---------------------------------------------------------------------------------------------------------------
# fldtanime (sol_candle)
# ---------------------------------------------------------------------------------------------------------------

def candle_anim(kit):
    """-> (fldtanime bytes, report, fails). Adds or replaces the sol_candle entry of the work-tree archive."""
    sys.path.insert(0, os.path.join(ROOT, "tools", "coronet_lava"))
    import narc
    import tempfile
    fails = []
    meta = kit["metas"]["sol_candle"]
    frames = meta["frames"]
    base_img = png.read(os.path.join(K.ASSET_DIR, "sol_candle.png"))
    base_t, base_p = nsbtx.encode_texture("sol_candle", base_img, "pltt16", meta.get("c0"))
    texs = []
    for i, fn in enumerate(frames):
        img = png.read(os.path.join(K.ASSET_DIR, fn + ".png"))
        ft, fp = nsbtx.encode_texture(f"sol_candle.{i + 1}", img, "pltt16", meta.get("c0"))
        if (ft["w"], ft["h"], ft["fmt"], ft["c0"]) != (base_t["w"], base_t["h"], base_t["fmt"], base_t["c0"]):
            fails.append(f"candle frame {fn}: size/format differ from the base texture")
        if fp["colors"][:len(base_p["colors"])] != base_p["colors"][:len(fp["colors"])]:
            fails.append(f"candle frame {fn}: palette differs from sol_candle_pl (fldtanime never swaps palettes)")
        texs.append(ft)
    if texs and texs[0]["data"] != base_t["data"]:
        fails.append("candle frame 1 texels differ from the base texture")
    btx = nsbtx.build(texs, [])
    ticks = meta.get("frame_ticks", 6)
    path = os.path.join(ROOT, FLDTANIME_REL)
    header, btnf, files = narc.read_files(path)
    table = bytearray(files[0])
    count = int.from_bytes(table[:4], "little")
    names = [bytes(table[4 + i * ANIME_ENTRY:20 + i * ANIME_ENTRY]).rstrip(b"\0") for i in range(count)]
    entry = bytearray(b"sol_candle".ljust(16, b"\0") + b"\xff" * 36)
    for i in range(len(frames)):
        entry[16 + 2 * i:18 + 2 * i] = bytes((i, ticks))
    if b"sol_candle" in names:
        idx = names.index(b"sol_candle")
        table[4 + idx * ANIME_ENTRY:4 + (idx + 1) * ANIME_ENTRY] = entry
    else:
        idx = count
        table[4 + count * ANIME_ENTRY:4 + count * ANIME_ENTRY] = entry
        table[:4] = (count + 1).to_bytes(4, "little")
        if len(files) != count + 1:
            fails.append(f"fldtanime: {len(files)} members for {count} entries")
        files.append(b"")
    files[0] = bytes(table)
    files[idx + 1] = btx
    with tempfile.NamedTemporaryFile(suffix=".narc", delete=False) as tmp:
        tmp_name = tmp.name
    narc.write_files(tmp_name, header, btnf, files)
    data = open(tmp_name, "rb").read()
    os.remove(tmp_name)
    rep = f"fldtanime entry {idx} (member {idx + 1}) = sol_candle, {len(frames)} frames x {ticks} VBlanks"
    return data, rep, fails, idx


# ---------------------------------------------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------------------------------------------

OVERHEAD_OK = []          # (x0, z0, x1, z1) tiles where something may hang over a walkable tile (none needed)


def clearance_check(F, t):
    """Nothing solid drawn inside a walkable tile below 1.3 tiles above its floor (cards, walls, boxes); flat ground
    decals are fine. Tests each solid face's points and centre against the walkable tiles' inner 0.8 x 0.8."""
    bad = set()
    walk = {k for k, v in t.items() if not v[0] & layout.BLOCK}
    for pts in F.solids:
        samples = list(pts) + [tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))]
        if len(pts) == 4:
            samples += [tuple((pts[i][k] + pts[(i + 1) % 4][k]) / 2 for k in range(3)) for i in range(4)]
        for x, h, z in samples:
            tx, tz = math.floor(x), math.floor(z)
            if (tx, tz) not in walk:
                continue
            fx, fz = x - tx, z - tz
            if 0.1 < fx < 0.9 and 0.1 < fz < 0.9 and h < (t[(tx, tz)][1] or G) + 1.3:
                if not any(a <= x <= c and b <= z <= d for a, b, c, d in OVERHEAD_OK):
                    bad.add((tx, tz))
    return sorted(bad)


def floor_check(out, t):
    """Every walkable rebuilt tile: the highest drawn horizontal face at its centre (below +0.6) is at the layout
    height (within 0.05)."""
    faces = {}
    for c, o in out.items():
        mesh = nsbmd.model_to_mesh(o["edit"].built, layout.CHUNKS[c])
        for me in mesh["meshes"]:
            P = me["positions"]
            for f in me["quads"] + me["tris"]:
                vs = [P[i] for i in f]
                if max(v[1] for v in vs) - min(v[1] for v in vs) > 1e-3:
                    continue
                x0, x1 = min(v[0] for v in vs), max(v[0] for v in vs)
                z0, z1 = min(v[2] for v in vs), max(v[2] for v in vs)
                for tx in range(math.floor(x0), math.ceil(x1)):
                    for tz in range(math.floor(z0), math.ceil(z1)):
                        if x0 <= tx + 0.5 <= x1 and z0 <= tz + 0.5 <= z1:
                            faces.setdefault((tx, tz), []).append(vs[0][1])
    bad = []
    for (x, z), v in t.items():
        if v[0] & layout.BLOCK or not layout.rebuilt(x, z):
            continue
        hs = [h for h in faces.get((x, z), []) if h <= v[1] + 0.6]
        if not hs or abs(max(hs) - v[1]) > 0.05:
            bad.append((x, z))
    return bad


def run_checks(out, F, kit, anim_fails):
    plist_ids, bm_files = B.area_prop_list()
    t = layout.tiles()
    results = []
    for c, o in out.items():
        edited = {o["edit"].model["shapes"][si]["name"] for si in o["edit"].faces}
        bad = C.stock_shapes_identical(o["edit"].model, o["edit"].built, edited)
        results.append((f"chunk {c}: untouched stock shapes and all stock materials byte-identical "
                        f"({len(o['edit'].model['shapes']) - len(edited)} untouched, {len(edited)} cut)", not bad))
        sec = mapdata.unpack(o["data"])
        results.append((f"chunk {c}: permissions equal the layout", not collision.check_permissions(c, sec["permissions"])))
        off = collision.check(c, sec["bdhc"])
        results.append((f"chunk {c}: BDHC height at every tile centre equals the layout ({len(off)} off)", not off))
        bad_props = [p["model"] for p in o["props"] if p["model"] not in plist_ids]
        results.append((f"chunk {c}: every prop is in area 0xA's prop list ({len(o['props'])} props)", not bad_props))
        gb = B.props()[c]
        results.append((f"chunk {c}: props identical to the graybox (layout.md section 3)", gb == o["props"]))
    for desc, ok in layout.checks():
        results.append(("layout: " + desc, ok))
    results += B.door_checks(out, bm_files)
    fl = floor_check(out, t)
    results.append((f"every walkable rebuilt tile is drawn at its layout height ({len(fl)} off: {fl[:6]})", not fl))
    cl = clearance_check(F, t)
    results.append((f"nothing solid drawn low over a walkable tile ({len(cl)}: {cl[:8]})", not cl))
    # budgets
    pmeshes = {c: B.prop_meshes(c, o["props"], bm_files) for c, o in out.items()}
    print(f"{'chunk':>5} {'polys':>6} {'stock':>6} {'new':>5} {'verts':>6} {'model B':>8} {'stock B':>8} {'BDHC B':>7} "
          f"{'mats':>4} {'props':>5} {'prop polys':>10}")
    for c, o in out.items():
        s = o["stats"]
        pp = sum(len(m["quads"]) + len(m["tris"]) for m in pmeshes[c]["meshes"])
        print(f"{c:>5} {s['polygons']:>6} {s['stock_polygons']:>6} {s['new_polygons']:>5} {s['vertices_sent']:>6} "
              f"{s['model_bytes']:>8} {s['stock_model_bytes']:>8} {s['bdhc_bytes']:>7} {s['materials']:>4} "
              f"{s['props']:>5} {pp:>10}")
        results.append((f"chunk {c}: {s['polygons']} polygons <= {POLY_LIMIT}", s["polygons"] <= POLY_LIMIT))
        results.append((f"chunk {c}: model {s['model_bytes']} B <= {MODEL_LIMIT} (45 KB; hard 0xF000 = 61440)",
                        s["model_bytes"] <= MODEL_LIMIT and s["model_bytes"] <= C.MODEL_BUFFER))
    faces = []
    for c, o in out.items():
        faces += B.mesh_faces(nsbmd.model_to_mesh(o["edit"].built, layout.CHUNKS[c]))
        faces += B.mesh_faces(pmeshes[c])
    mat = json.loads(layout.git_file("res/field/maps/matrices/map_matrix_000.json"))
    for cz in (19, 20, 21):
        for cx in (16, 17, 18, 19):
            if (cx, cz) in layout.CHUNKS.values():
                continue
            name = mat["maps"][cz][cx]
            if not (name.startswith("MAP_") and name[4:].isdigit()):
                continue
            sec = mapdata.unpack(layout.git_file(layout.chunk_rel(int(name[4:]))))
            faces += B.mesh_faces(nsbmd.model_to_mesh(nsbmd.parse_bmd(sec["model"])["models"][0], (cx, cz)))
            if sec["props"]:
                faces += B.mesh_faces(B.prop_meshes_cell((cx, cz), mapdata.read_props(sec["props"]), bm_files))
    walk = [k for k, v in t.items() if not v[0] & layout.BLOCK]
    heights = {k: v[1] for k, v in t.items()}
    for name, worst, at in B.camera_polys(faces, walk, heights):
        print(f"camera {name}: worst {worst} polygons on screen (terrain + props of all loaded chunks) at {at}")
        results.append((f"camera {name}: {worst} polygons on screen <= {SCREEN_LIMIT}", worst <= SCREEN_LIMIT))
    # set 010
    vb, vo = kit["vram"]
    for f in kit["fails"]:
        results.append(("set 010: " + f, False))
    results.append((f"set 010: kit +{sum(vo) - sum(vb)} B <= {K.KIT_BUDGET}; set {sum(vo)} B <= {K.VRAM_PROVEN}; "
                    f"stock textures and palettes unchanged (textures_kit.build)", not kit["fails"]))
    stock_mats = {(m["texture"], m["palette"]) for o in out.values() for m in o["edit"].model["materials"]}
    used = {(m["texture"], m["palette"]) for o in out.values() for m in o["edit"].built["materials"]} - stock_mats
    unused = [n for n, (tex, pal, rep) in kit["table"].items() if (tex, pal) not in used]
    results.append((f"every kit entry is used by the town (unused: {unused})", not unused))
    for f in anim_fails:
        results.append(("fldtanime: " + f, False))
    return results, pmeshes, bm_files


# ---------------------------------------------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------------------------------------------

def write_preview(d, out, pmeshes, bm_files, kit):
    os.makedirs(d, exist_ok=True)
    palette_only = {tex_pal: name for name, tex_pal in
                    ((n, (t, p)) for n, (t, p, r) in kit["table"].items()) if tex_pal[0] != name}
    for c, o in out.items():
        back = nsbmd.parse_bmd(o["model"])["models"][0]
        mesh = nsbmd.model_to_mesh(back, layout.CHUNKS[c], name=f"chunk_{c:03d}")
        for m in mesh["materials"]:           # palette-only kit entries: point the preview at the recoloured PNG
            k = (m["texture"], m["palette"])
            if k in palette_only:
                m["texture"] = palette_only[k]
        json.dump(mesh, open(os.path.join(d, f"chunk_{c:03d}.mesh.json"), "w"))
        json.dump(pmeshes[c], open(os.path.join(d, f"props_{c:03d}.mesh.json"), "w"))
    tdir = os.path.join(d, "textures")
    os.makedirs(tdir, exist_ok=True)
    s = nsbtx.parse(kit["set"])
    TT = {t["name"]: t for t in s["textures"]}
    PP = {p["name"]: p for p in s["palettes"]}
    for name, (tex, pal, rep) in kit["table"].items():
        rgba, _ = nsbtx.decode(TT[tex], PP[pal]["colors"])
        png.write_rgba(os.path.join(tdir, name + ".png"), TT[tex]["w"], TT[tex]["h"], rgba)
        json.dump({"format": "pltt16", "repeat": list(rep)}, open(os.path.join(tdir, name + ".json"), "w"))
    import dump_stock
    for m in sorted({p["model"] for o in out.values() for p in o["props"]}):
        bmd = nsbmd.parse_bmd(bm_files[m])
        if bmd["tex0"]:
            dump_stock.export_textures(bmd["tex0"], tdir, {x["texture"]: x["palette"] for x in bmd["models"][0]["materials"]})
    json.dump({str(c): o["stats"] for c, o in out.items()}, open(os.path.join(d, "stats.json"), "w"), indent=1)
    print("wrote preview meshes and textures to", d)


def main():
    args = sys.argv[1:]
    preview = args[args.index("--preview") + 1] if "--preview" in args else None
    write = "--write" in args
    out, F, kit = build()
    anim, anim_rep, anim_fails, _ = candle_anim(kit)
    results, pmeshes, bm_files = run_checks(out, F, kit, anim_fails)
    vb, vo = kit["vram"]
    print(f"set 010 VRAM: {sum(vb)} -> {sum(vo)} B (+{sum(vo) - sum(vb)}; texels {vb[0]} -> {vo[0]}, palettes "
          f"{vb[1]} -> {vo[1]}); {len(kit['rows'])} kit entries")
    print(anim_rep)
    nfail = 0
    for desc, ok in results:
        if not ok or "--verbose" in args or not desc.startswith("layout: "):
            print(("PASS " if ok else "FAIL ") + desc)
        nfail += not ok
    print(f"({sum(1 for d, ok in results if d.startswith('layout: '))} layout checks, "
          f"{sum(1 for d, ok in results if d.startswith('layout: ') and not ok)} failed)")
    if preview:
        write_preview(os.path.join(preview, "art"), out, pmeshes, bm_files, kit)
    if write:
        if nfail:
            print(f"REFUSING to write: {nfail} check(s) failed")
            return 1
        targets = [(f"{OUT_MAP_DIR}/map_data_{c:03d}.bin", o["data"]) for c, o in out.items()]
        targets += [(K.SET_REL, kit["set"]), (FLDTANIME_REL, anim)]
        for rel, data in targets:
            p = os.path.join(ROOT, rel)
            old = open(p, "rb").read() if os.path.exists(p) else None
            open(p, "wb").write(data)
            print(("unchanged " if old == data else "wrote ") + rel, len(data), "B")
    print(f"{nfail} check(s) failed" if nfail else "all checks pass")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
