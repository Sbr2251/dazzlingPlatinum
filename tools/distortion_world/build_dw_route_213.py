#!/usr/bin/env python3
"""Builds DW Route 213, the Drowned Lake (Arc 2 scene 2.21; set-lake, docs/arc2/PLAN.md S6 / D6 / D8).

The lake that vanished: the Valor Basin portal swallowed Lake Valor into the Distortion World. Its water hangs
upside down as the ceiling and its old bed is the floor, with what it swallowed still lying there.

Base: rift-b's Phase 0 floor, the stock DW B4F (map_data 612/613) with rift-b's permission edits
(build_rift_b_maps.py B4F_OPEN / B4F_BLOCK), written to map_data_675/676 and matrix 294. On top of that:

  map_data_675  the rowboat on the old lakebed beside the path down to the first hop (terrain: material dw213_wood,
                ~30 faces around (19,18)); the invisible ghost-prop walkways of stock B4F south of the lip are blocked
                (rift-b dropped the floating rocks, so those tiles were walkable void).
  map_data_676  the ceiling (y=10, x 44-49, z 25-52) is rebuilt as the hanging lake: water everywhere except the
                causeway (the walkable tiles of the ceiling grid in route_213.json), the island off its end and the
                shores under the hanging trees, which stay stone, with a rim where stone meets water. The water
                uses the floor pool's own textures in unlit materials (`lake` inside, the animated shoreline
                `lakep.1` around the edges), so it glows instead of sitting in the slab's shadow. The stock ceiling
                pool (bf_lake), its rim, the hole at x 46-49, z 33-36 and the decals on now-wet tiles go.
                The corridor from the pool to the east wall becomes a jetty: a plank deck and six mooring posts
                (examinable from the deck: bg events on PIER_BG_TILES, script 9).
  texture set 73  + dw213_wood (32x32 pltt16, weathered planks), appended; every DW map shares the set.
                The other textures are untouched (they are rebuilt from the current file, so another workstream's
                appends survive: rerun this script after merging).

The ceiling grid itself (walkable causeway + the island) is in tools/distortion_world/route_213.json (twarc.py).
Objects (sign, frame, card, Lapras on the island) are in src/overlay009/ov9_02249960.c, sArc2DwRoute213Objects.

Usage: python3 tools/distortion_world/build_dw_route_213.py [--check] [--preview DIR]
  (idempotent; --check exits 1 if any output differs; --preview writes top-down PNGs of the floor and ceiling)
"""
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
sys.path.insert(0, HERE)
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402
import build_rift_b_maps as rb  # noqa: E402

DATA = os.path.join(ROOT, "res/field/maps/data")
MATRICES = os.path.join(ROOT, "res/field/maps/matrices")
TEXSET = os.path.join(ROOT, "res/field/maps/texture_sets/map_texture_set_073.nsbtx")
SPEC = os.path.join(HERE, "route_213.json")
BLOCKED = 0x8000

MATRIX_ID, MATRIX_NAME = 294, "m_dwa2_4"
CHUNKS = {675: (612, 0, 0), 676: (613, 1, 0)}       # dst: (stock B4F src, chunk x, chunk z)

# ---------------------------------------------------------------------------------------------------------------
# floor: permissions
# ---------------------------------------------------------------------------------------------------------------

# stock B4F's floating-rock walkways (ghost props, dropped by rift-b) left walkable tiles with no floor under them,
# reachable from the lip row (20-25, 23): (20-24, 24-31). Every walkable tile of 675 whose centre has no floor face
# (facing up, h -0.6..1.2) is blocked, so nobody walks on the void. (614/615 are stock and shared: untouched.)
FLOOR_FIX_CHUNK = 675


def point_in_poly(px, pz, poly):
    inside, n = False, len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        if (z1 > pz) != (z2 > pz) and px < x1 + (pz - z1) * (x2 - x1) / (z2 - z1):
            inside = not inside
    return inside


def tiles_without_floor(ch, perm):
    polys = []
    for name, prims in ch.prims:
        tris, quads = nsbmd.prims_to_faces(prims)
        for f in tris + quads:
            ts = [ch.to_tile(v["pos"]) for v in f]
            hs = [t[1] for t in ts]
            if face_normal(ts)[1] > 0.7 and -0.6 <= min(hs) and max(hs) <= 1.2:
                polys.append([(t[0], t[2]) for t in ts])
    out = []
    for z in range(32):
        for x in range(32):
            if not perm[z][x] & BLOCKED:
                X, Z = x + ch.cx * 32, z + ch.cz * 32
                if not any(point_in_poly(X + 0.5, Z + 0.5, p) for p in polys):
                    out.append((x, z))
    return out


# ---------------------------------------------------------------------------------------------------------------
# the rowboat (chunk 675)
# ---------------------------------------------------------------------------------------------------------------

BOAT_TEX = "dw213_wood"
BOAT_CENTRE = (20.75, 18.0)     # tiles (x, z); on the blocked floor just west of the path (22, 16-19), clear of trees
BOAT_YAW = 80.0                 # degrees about y (0 = bow towards +x); 80 = bow towards +z, a little east
BOAT_ROLL = 10.0                # degrees about its keel: settled onto one side in the old mud
BOAT_LEN = 3.3                  # tiles, bow to stern
# stations along the boat (from the stern, tiles) and the half-beam of the gunwale / the keel at each
STATIONS = [0.0, 0.5, 1.3, 2.1, 2.8, 3.3]
RIM_HALF = [0.48, 0.6, 0.66, 0.6, 0.38, 0.0]
KEEL_HALF = [0.34, 0.42, 0.45, 0.4, 0.2, 0.0]
RIM_H, KEEL_H, FLOOR_H, SEAT_H = 0.56, 0.04, 0.18, 0.40
SEATS = [(0.6, 0.24), (1.85, 0.24)]     # (station, width) of the thwarts
BOAT_BG_TILES = [(21, 16), (21, 17), (21, 18), (21, 19)]   # bg events (events_dw_route_213.json) the player faces from x=22

# the jetty (chunk 676): the corridor from the pool to the east wall (x 38-47, z 22-23) gets a plank deck and
# mooring posts along both edges; the jump marks at x=48 stay stone
PIER_X, PIER_Z = (38, 47), (22, 23)
PIER_POSTS_X = [39.5, 42.5, 45.5]
PIER_POST_Z = [21.93, 24.07]            # just outside the deck's edges (z 22.0 / 24.0)
POST_HALF, POST_TOP, POST_BOTTOM = 0.09, 0.62, -0.3
PIER_BG_TILES = [(int(x), z) for x in PIER_POSTS_X for z in (21, 24)]   # examined from the deck, facing the post

# ---------------------------------------------------------------------------------------------------------------
# the hanging lake (chunk 676 ceiling)
# ---------------------------------------------------------------------------------------------------------------

CEIL_X = (44, 49)               # tile columns under the slab (the underside is x 44.0-50.0)
CEIL_Z = (25, 52)               # tile rows (z 25.0-53.0)
EAST_POOL_X = 50                # the stock pool reached one column past the slab's east edge (z 37-50): water there too
EAST_POOL_Z = (37, 50)
STONE_H, WATER_H = 11.0, 11.5   # layout h (world y = 16 + 16 h); the underside faces down
SHORE_Z = [(25, 30), (51, 52)]  # stone under the hanging trees at both ends (z rows, inclusive)
ISLAND = [(45, 48, 44, 47)]     # (x0, x1, z0, z1): the hanging lake's one island, where the Lapras waits;
                                # water all round but the 2-wide spur (46-47, 43) from the causeway
STONE_MAT, RIM_MAT = "adf", "criffp_lm9"
# the hanging water: the floor pool's own `lake` texture in an unlit material (lights off, a pale cyan vertex colour),
# so the underside of the lake glows instead of sitting in the slab's shadow like the stone around it
WATER_MAT, WATER_TEX, WATER_COLOR = "dw213_lake", "lake", (26 | 30 << 5 | 31 << 10)
# its edge: the floor pool's animated shoreline texture (lakep.1, fldtanime entry 10), laid out like the pool's
# border (edge strips: v 0.5 inside -> 1.0 at the shore, 0.5 repeat per tile along it; corners: the 0-0.5 square)
SHORE_MAT, SHORE_TEX = "dw213_lakep", "lakep.1"
WATER_UV_PER_TILE = 1.5         # the floor pool's own scale (lake_lm7: 5 repeats over 3 tiles)


def ceiling_grid():
    """Walkable ceiling tiles from route_213.json (platform rows: x = 49 - row, columns z 25..)."""
    spec = json.load(open(SPEC))
    rows = next(p["rows"] for p in spec["platforms"] if p.get("rows"))
    walk = set()
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch == ".":
                walk.add((49 - r, 25 + c))
    return walk


def ceiling_kind():
    """{(x, z): 'stone' | 'water'} over the ceiling footprint."""
    walk = ceiling_grid()
    kind = {}
    for x in range(CEIL_X[0], CEIL_X[1] + 1):
        for z in range(CEIL_Z[0], CEIL_Z[1] + 1):
            stone = (x, z) in walk or any(z0 <= z <= z1 for z0, z1 in SHORE_Z) or \
                any(x0 <= x <= x1 and z0 <= z <= z1 for x0, x1, z0, z1 in ISLAND)
            kind[(x, z)] = "stone" if stone else "water"
    for z in range(EAST_POOL_Z[0], EAST_POOL_Z[1] + 1):
        kind[(EAST_POOL_X, z)] = "water"
    return kind


# ---------------------------------------------------------------------------------------------------------------
# geometry helpers: tile space (x, h, z) <-> the chunk model's fx16 vertices
# ---------------------------------------------------------------------------------------------------------------

class Chunk:
    def __init__(self, raw, cx, cz):
        self.parts = mapdata.unpack(raw)
        self.bmd = nsbmd.parse_bmd(self.parts["model"])
        self.model = self.bmd["models"][0]
        self.cx, self.cz = cx, cz
        self.k = nsbmd.FX / (self.model["info"]["pos_scale"] / nsbmd.FX)     # fx16 units per world unit
        self.pairs = nsbmd.shape_material_pairs(self.model)
        self.prims = nsbmd.model_prims(self.model)
        self.changed = set()
        self.mat_index = {m["name"]: i for i, m in enumerate(self.model["materials"])}

    def shape_of(self, mat_name):
        mi = self.mat_index[mat_name]
        return next(si for m, si in self.pairs if m == mi)

    def to_fx(self, x, h, z):
        wx = (x - self.cx * 32 - 16) * 16
        wy = 16 + h * 16
        wz = (z - self.cz * 32 - 16) * 16
        return tuple(int(round(c * self.k)) for c in (wx, wy, wz))

    def to_tile(self, pos):
        wx, wy, wz = (c / self.k for c in pos)
        return (wx / 16 + 16 + self.cx * 32, (wy - 16) / 16, wz / 16 + 16 + self.cz * 32)

    def faces(self, si):
        return nsbmd.prims_to_faces(self.prims[si][1])

    def set_faces(self, si, tris, quads):
        self.prims[si] = (self.prims[si][0], nsbmd.faces_to_prims(tris, quads))
        self.changed.add(si)

    def add_shape(self, mat, tris, quads):
        """New material (a make_material dict) + one shape drawn with it."""
        self.model["materials"].append(mat)
        mi = len(self.model["materials"]) - 1
        self.mat_index[mat["name"]] = mi
        si = len(self.prims)
        self.prims.append((f"polygon{si}", nsbmd.faces_to_prims(tris, quads)))
        self.pairs.append((mi, si))
        self.changed.add(si)

    def build(self):
        m = self.model
        m2 = nsbmd.make_model(m["name"], m["materials"], self.prims, draw=self.pairs,
                              pos_scale=m["info"]["pos_scale"], node_name=m["nodes"][0]["name"])
        for si, s in enumerate(m["shapes"]):
            if si not in self.changed:
                m2["shapes"][si] = s          # untouched shapes keep their stock display lists byte for byte
        return nsbmd.build_bmd([m2], tex0=self.bmd["tex0"], version=self.bmd["version"])


def face_normal(pts):
    a, b, c = pts[0], pts[1], pts[2]
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    ln = math.sqrt(sum(x * x for x in n)) or 1.0
    return [x / ln for x in n]


def make_face(ch, pts, uvs, tex_size, want=None, color=None):
    """pts: tile-space (x, h, z) corners in drawing order; uvs in texture repeats; want: the normal the drawn side
    must face (the winding is reversed to match). Returns a tuple of vertex dicts with a flat normal (lit
    materials), or with `color` (rgb555) and no normal (unlit materials)."""
    n = face_normal(pts)
    if want is not None and sum(n[i] * want[i] for i in range(3)) < 0:
        pts, uvs = pts[::-1], uvs[::-1]
        n = [-x for x in n]
    w, h = tex_size
    nn = None if color is not None else nsbmd.pack_normal(n)
    return tuple({"pos": ch.to_fx(*p), "uv": (int(round(uv[0] * w * 16)), int(round(uv[1] * h * 16))),
                  "color": color, "normal": nn} for p, uv in zip(pts, uvs))


# ---------------------------------------------------------------------------------------------------------------
# the rowboat
# ---------------------------------------------------------------------------------------------------------------

def boat_points():
    """Hull lines in boat space (s along the keel from the stern, y across, h up) -> tile space, after roll and yaw."""
    cy, sy = math.cos(math.radians(BOAT_YAW)), math.sin(math.radians(BOAT_YAW))
    cr, sr = math.cos(math.radians(BOAT_ROLL)), math.sin(math.radians(BOAT_ROLL))

    def tr(s, y, h):
        # roll about the keel line (s axis, h = 0): positive leans the boat towards +y
        y2, h2 = y * cr + h * sr, -y * sr + h * cr
        h2 += abs(sr) * 0.30          # the low gunwale rests on the floor, the keel lifts a little
        dx, dz = s - BOAT_LEN / 2, y2
        return (BOAT_CENTRE[0] + dx * cy - dz * sy, h2, BOAT_CENTRE[1] + dx * sy + dz * cy)
    return tr


def boat_faces(ch):
    tr = boat_points()
    size = (32, 32)
    faces = []
    n = len(STATIONS)
    for side in (1, -1):
        rim = [(STATIONS[i], side * RIM_HALF[i], RIM_H) for i in range(n)]
        keel = [(STATIONS[i], side * KEEL_HALF[i], KEEL_H) for i in range(n)]
        inner = [(STATIONS[i], side * max(RIM_HALF[i] - 0.06, 0.0), RIM_H) for i in range(n)]
        flo = [(STATIONS[i], side * max(KEEL_HALF[i] - 0.04, 0.0), FLOOR_H) for i in range(n)]
        for i in range(n - 1):
            out = [0, side, 0.3]                     # boat-space outward normal, transformed below via winding
            # outer planking: planks run bow to stern (u along the length, v up the side)
            p = [rim[i], rim[i + 1], keel[i + 1], keel[i]]
            uv = [(STATIONS[i], 0.0), (STATIONS[i + 1], 0.0), (STATIONS[i + 1], 0.5), (STATIONS[i], 0.5)]
            centre = tr(STATIONS[i] / 2 + STATIONS[i + 1] / 2, 0, (RIM_H + KEEL_H) / 2)
            pts = [tr(*q) for q in p]
            fc = [sum(q[j] for q in pts) / 4 for j in range(3)]
            want = [fc[j] - centre[j] for j in range(3)]
            faces.append(make_face(ch, pts, uv, size, want))
            # inner side (seen from above, into the boat)
            p = [inner[i], inner[i + 1], flo[i + 1], flo[i]]
            pts = [tr(*q) for q in p]
            fc = [sum(q[j] for q in pts) / 4 for j in range(3)]
            want = [centre[j] - fc[j] for j in range(3)]
            uv = [(STATIONS[i], 0.5), (STATIONS[i + 1], 0.5), (STATIONS[i + 1], 0.9), (STATIONS[i], 0.9)]
            faces.append(make_face(ch, pts, uv, size, want))
            # gunwale cap (the top edge of the planking)
            p = [rim[i], rim[i + 1], inner[i + 1], inner[i]]
            pts = [tr(*q) for q in p]
            uv = [(STATIONS[i], 0.0), (STATIONS[i + 1], 0.0), (STATIONS[i + 1], 0.1), (STATIONS[i], 0.1)]
            faces.append(make_face(ch, pts, uv, size, [0, 1, 0]))
            del out
        # floorboards, one half
        for i in range(n - 1):
            p = [(STATIONS[i], 0, FLOOR_H), (STATIONS[i + 1], 0, FLOOR_H), flo[i + 1], flo[i]]
            pts = [tr(*q) for q in p]
            uv = [(STATIONS[i], 0.0), (STATIONS[i + 1], 0.0), (STATIONS[i + 1], 0.45), (STATIONS[i], 0.45)]
            faces.append(make_face(ch, pts, uv, size, [0, 1, 0]))
    # transom (the flat stern), outside and inside
    st = [(0.0, RIM_HALF[0], RIM_H), (0.0, -RIM_HALF[0], RIM_H), (0.0, -KEEL_HALF[0], KEEL_H), (0.0, KEEL_HALF[0], KEEL_H)]
    pts = [tr(*q) for q in st]
    back = [tr(-1, 0, 0.3)[j] - tr(0, 0, 0.3)[j] for j in range(3)]
    uv = [(0, 0), (1.2, 0), (1.2, 0.5), (0, 0.5)]
    faces.append(make_face(ch, pts, uv, size, back))
    faces.append(make_face(ch, pts, uv, size, [-x for x in back]))
    # thwarts (seats) across the boat
    for s0, w in SEATS:
        i = max(k for k in range(n) if STATIONS[k] <= s0)
        t = (s0 - STATIONS[i]) / (STATIONS[i + 1] - STATIONS[i])
        half = RIM_HALF[i] + (RIM_HALF[i + 1] - RIM_HALF[i]) * t - 0.05
        p = [(s0, half, SEAT_H), (s0 + w, half, SEAT_H), (s0 + w, -half, SEAT_H), (s0, -half, SEAT_H)]
        pts = [tr(*q) for q in p]
        uv = [(0, 0.0), (0, 0.25), (half * 2, 0.25), (half * 2, 0.0)]
        faces.append(make_face(ch, pts, uv, size, [0, 1, 0]))
        # its front edge
        p = [(s0 + w, half, SEAT_H), (s0 + w, -half, SEAT_H), (s0 + w, -half, SEAT_H - 0.06), (s0 + w, half, SEAT_H - 0.06)]
        pts = [tr(*q) for q in p]
        fwd = [tr(1, 0, 0.3)[j] - tr(0, 0, 0.3)[j] for j in range(3)]
        faces.append(make_face(ch, pts, [(0, 0.3), (half * 2, 0.3), (half * 2, 0.35), (0, 0.35)], size, fwd))
    return faces


def wood_texture():
    """32x32, 16 colours: four weathered planks running along u, dark seams, a few nails. Index 0 is opaque."""
    pal = [(70, 58, 50), (96, 82, 70), (118, 102, 88), (138, 122, 104), (156, 140, 120), (176, 160, 138),
           (48, 40, 36), (36, 30, 28), (128, 118, 112), (104, 96, 92), (150, 146, 140), (84, 70, 60),
           (112, 92, 74), (60, 50, 44), (190, 176, 156), (20, 18, 18)]
    rows = []
    seed = 12345

    def rnd():
        nonlocal seed
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        return seed
    for y in range(32):
        plank, py = divmod(y, 8)
        row = []
        for x in range(32):
            if py == 0:
                v = 7                                     # seam
            elif py == 1:
                v = 13
            else:
                base = [2, 3, 2, 4][plank]
                grain = ((x * 3 + plank * 7 + (py * 5 if (x // 6) % 2 else 0)) % 9)
                v = base + (1 if grain == 0 else -1 if grain == 4 else 0)
                r = rnd() % 23
                if r == 0:
                    v = 8                                 # grey weathering
                elif r == 1:
                    v = 9
                elif r == 2:
                    v = 11
                if py == 7:
                    v = 1
            if py == 4 and x in (3 + plank * 5 % 7, 19 + plank * 3 % 5):
                v = 15                                    # nails
            row.append(v)
        rows.append(row)
    return pal, rows


# ---------------------------------------------------------------------------------------------------------------
# the hanging lake
# ---------------------------------------------------------------------------------------------------------------

def in_ceiling_region(t):
    x, h, z = t
    return CEIL_X[0] - 0.01 <= x <= EAST_POOL_X + 1.01 and CEIL_Z[0] - 0.01 <= z <= CEIL_Z[1] + 1.01 and 10.7 <= h <= 12.05


def runs(vals):
    """Sorted ints -> [(start, length)] of consecutive runs."""
    out = []
    for v in vals:
        if out and out[-1][0] + out[-1][1] == v:
            out[-1] = (out[-1][0], out[-1][1] + 1)
        else:
            out.append((v, 1))
    return out


def merge_rects(cells, max_side=8):
    """Greedy cover of a tile set by rectangles (x, z, w, h): rows first, then grown down while the run repeats."""
    left = set(cells)
    out = []
    for z0 in range(min(c[1] for c in cells), max(c[1] for c in cells) + 1) if cells else []:
        for x0 in range(min(c[0] for c in cells), max(c[0] for c in cells) + 1):
            if (x0, z0) not in left:
                continue
            w = 1
            while (x0 + w, z0) in left and w < max_side:
                w += 1
            h = 1
            while h < max_side and all((x0 + i, z0 + h) in left for i in range(w)):
                h += 1
            for i in range(w):
                for j in range(h):
                    left.discard((x0 + i, z0 + j))
            out.append((x0, z0, w, h))
    return out


SIDES = {"N": (0, -1), "S": (0, 1), "W": (-1, 0), "E": (1, 0)}


def shore_sides(kind, t):
    """The sides of water tile t that meet stone or the slab's edge, as a string from 'NSWE'."""
    x, z = t
    return "".join(k for k, (dx, dz) in SIDES.items() if kind.get((x + dx, z + dz)) != "water")


def shore_face(ch, t, sides):
    """One water tile on the shore: an edge strip (one side), a corner (two adjacent sides). A tile between two
    opposite shores (the 1-wide east channel along the causeway) takes the edge strip of its west (causeway) side;
    three sides take the corner of the first adjacent pair."""
    x, z = t
    A, B, C, D = (x, WATER_H, z), (x + 1, WATER_H, z), (x + 1, WATER_H, z + 1), (x, WATER_H, z + 1)
    corners = {"NW": A, "NE": B, "SE": C, "SW": D}
    pair = next((a + b for a in "NS" for b in "WE" if a in sides and b in sides), None)
    if pair:
        outer = corners[pair]
        # the corner square: (0,0) at the outer corner, (0.5,0.5) at the inner one, (0.5,0)/(0,0.5) beside it
        other = {"NW": (B, D, C), "NE": (A, C, D), "SE": (D, B, A), "SW": (C, A, B)}[pair]
        pts = [outer, other[0], other[2], other[1]]
        uvs = [(0, 0), (0.5, 0), (0.5, 0.5), (0, 0.5)]
    else:
        side = "W" if "W" in sides else sides[0]
        ux, uz = (x % 4) * 0.5, (z % 4) * 0.5
        if side == "N":
            pts, uvs = [A, B, C, D], [(ux, 1), (ux + 0.5, 1), (ux + 0.5, 0.5), (ux, 0.5)]
        elif side == "S":
            pts, uvs = [A, B, C, D], [(ux, 0.5), (ux + 0.5, 0.5), (ux + 0.5, 1), (ux, 1)]
        elif side == "W":
            pts, uvs = [A, B, C, D], [(uz, 1), (uz, 0.5), (uz + 0.5, 0.5), (uz + 0.5, 1)]
        else:
            pts, uvs = [A, B, C, D], [(uz, 0.5), (uz, 1), (uz + 0.5, 1), (uz + 0.5, 0.5)]
    return make_face(ch, pts, uvs, (32, 32), [0, -1, 0], color=WATER_COLOR)


def build_pier(ch):
    """Plank deck over the corridor's top faces (adf, s_grass at h 0 in PIER_X x PIER_Z) and mooring posts."""
    removed = 0
    for mat in ("adf", "s_grass_lm8"):
        si = ch.shape_of(mat)
        tris, quads = ch.faces(si)
        keep_t, keep_q = [], []
        for lst, keep in ((tris, keep_t), (quads, keep_q)):
            for f in lst:
                ts = [ch.to_tile(v["pos"]) for v in f]
                c = [sum(t[i] for t in ts) / len(ts) for i in range(3)]
                hs = [t[1] for t in ts]
                if PIER_X[0] <= c[0] <= PIER_X[1] + 1 and PIER_Z[0] <= c[2] <= PIER_Z[1] + 1 and \
                        max(abs(h) for h in hs) < 0.01:
                    removed += 1
                else:
                    keep.append(f)
        ch.set_faces(si, keep_t, keep_q)
    faces = []
    up = [0, 1, 0]
    x0, x1, z0, z1 = PIER_X[0], PIER_X[1] + 1, PIER_Z[0], PIER_Z[1] + 1
    for x in range(x0, x1, 2):
        xe = min(x + 2, x1)
        # planks run across the jetty (along z): u along z, v along x (two planks per tile)
        pts = [(x, 0.0, z0), (xe, 0.0, z0), (xe, 0.0, z1), (x, 0.0, z1)]
        uvs = [(z0 * 0.5, x * 0.5), (z0 * 0.5, xe * 0.5), (z1 * 0.5, xe * 0.5), (z1 * 0.5, x * 0.5)]
        faces.append(make_face(ch, pts, [(u, v - x0 * 0.5) for u, v in uvs], (32, 32), up))
    for px in PIER_POSTS_X:
        for pz in PIER_POST_Z:
            a, b = px - POST_HALF, px + POST_HALF
            c, d = pz - POST_HALF, pz + POST_HALF
            lo, hi = POST_BOTTOM, POST_TOP
            faces.append(make_face(ch, [(a, hi, c), (b, hi, c), (b, hi, d), (a, hi, d)],
                                   [(0, 0.9), (0.2, 0.9), (0.2, 1.0), (0, 1.0)], (32, 32), up))
            for (xa, za), (xb, zb), n in (((a, c), (b, c), [0, 0, -1]), ((b, c), (b, d), [1, 0, 0]),
                                          ((b, d), (a, d), [0, 0, 1]), ((a, d), (a, c), [-1, 0, 0])):
                faces.append(make_face(ch, [(xa, hi, za), (xb, hi, zb), (xb, lo, zb), (xa, lo, za)],
                                       [(0, 0.55), (0.2, 0.55), (0.2, 0.95), (0, 0.95)], (32, 32), n))
    ch.add_shape(nsbmd.make_material(BOAT_TEX + "_pier", BOAT_TEX, BOAT_TEX + "_pl", 32, 32), [], faces)
    return removed, len(faces)


def rebuild_ceiling(ch):
    kind = ceiling_kind()
    removed = 0
    for mat in ("bf_lake_lm1", "bf_lakep_lm1"):          # the stock ceiling pool
        si = ch.shape_of(mat)
        tris, quads = ch.faces(si)
        removed += len(tris) + len(quads)
        ch.set_faces(si, [], [])

    def centroid(f):
        ts = [ch.to_tile(v["pos"]) for v in f]
        return [sum(t[i] for t in ts) / len(ts) for i in range(3)], ts

    # the stock underside inside the footprint (stone + the hole), the hole's rim, the pool's rim
    for mat in ("adf", "criffp2_lm2", "criffp_lm9"):
        si = ch.shape_of(mat)
        tris, quads = ch.faces(si)
        keep_t, keep_q = [], []
        for lst, keep in ((tris, keep_t), (quads, keep_q)):
            for f in lst:
                c, ts = centroid(f)
                hs = [t[1] for t in ts]
                drop = False
                if mat == "adf":
                    drop = CEIL_X[0] <= c[0] <= CEIL_X[1] + 1 and CEIL_Z[0] <= c[2] <= CEIL_Z[1] + 1 and \
                        10.9 <= min(hs) and max(hs) <= 11.6
                elif mat == "criffp2_lm2":
                    drop = 46.0 <= c[0] <= 50.0 and 33.0 <= c[2] <= 37.0 and max(hs) <= 11.05      # the hole's rim
                else:
                    # the stock pool's rim, inside the slab: x (44.0, 51.0), z (37.0, 51.0), h 11-12
                    drop = 44.0 < c[0] < 51.0 and 37.0 < c[2] < 51.0 and 10.95 <= min(hs) and max(hs) <= 12.05
                if drop:
                    removed += 1
                else:
                    keep.append(f)
        ch.set_faces(si, keep_t, keep_q)

    # the stock decals on the underside (tufts, the landing's jump marks): kept on stone tiles (no new stone quad
    # under them), dropped on tiles that are now water; the hole's floating dark panel (s_land3, h 10) goes
    decal_tiles = set()
    for mat in ("s_grass_lm8", "s_land_att_lm1", "s_land3_lm6"):
        si = ch.shape_of(mat)
        tris, quads = ch.faces(si)
        keep_t, keep_q = [], []
        for lst, keep in ((tris, keep_t), (quads, keep_q)):
            for f in lst:
                c, ts = centroid(f)
                hs = [t[1] for t in ts]
                inside = CEIL_X[0] <= c[0] <= EAST_POOL_X + 1 and CEIL_Z[0] <= c[2] <= CEIL_Z[1] + 1 and \
                    9.5 <= min(hs) and max(hs) <= 11.6
                tile = (int(c[0]), int(c[2]))
                if inside and (mat == "s_land3_lm6" or kind.get(tile) != "stone"):
                    removed += 1
                    continue
                if inside:
                    decal_tiles.add(tile)
                keep.append(f)
        ch.set_faces(si, keep_t, keep_q)

    stone_si, rim_si = ch.shape_of(STONE_MAT), ch.shape_of(RIM_MAT)
    down = [0, -1, 0]
    st_t, st_q = ch.faces(stone_si)
    wa_t, wa_q = [], []
    ri_t, ri_q = ch.faces(rim_si)
    added = 0
    d = WATER_UV_PER_TILE
    shore = {t: shore_sides(kind, t) for t, v in kind.items() if v == "water"}
    sh_q = []
    for t, sides in sorted(shore.items()):
        if sides:
            sh_q.append(shore_face(ch, t, sides))
            added += 1
    for k, cells in (("stone", {t for t, v in kind.items() if v == "stone" and t not in decal_tiles}),
                     ("water", {t for t, sides in shore.items() if not sides})):
        for x, z, w, h in merge_rects(cells):
            if k == "stone":
                pts = [(x, STONE_H, z), (x + w, STONE_H, z), (x + w, STONE_H, z + h), (x, STONE_H, z + h)]
                st_q.append(make_face(ch, pts, [(0, 0), (w, 0), (w, h), (0, h)], (16, 16), down))
            else:
                u0, v0 = (x - CEIL_X[0]) * d, (z - CEIL_Z[0]) * d
                pts = [(x, WATER_H, z), (x + w, WATER_H, z), (x + w, WATER_H, z + h), (x, WATER_H, z + h)]
                wa_q.append(make_face(ch, pts, [(u0, v0), (u0 + w * d, v0), (u0 + w * d, v0 + h * d), (u0, v0 + h * d)],
                                      (32, 32), down, color=WATER_COLOR))
            added += 1
    # rims: every water tile edge that meets stone or the slab's edge, from the stone underside (h 11) up to the
    # water (11.5), facing into the water; collinear edges are merged into runs
    edges = {}
    for (x, z), k in kind.items():
        if k != "water":
            continue
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if kind.get((x + dx, z + dz)) == "water":
                continue
            if dx:
                edges.setdefault(("x", x + (1 if dx > 0 else 0), dx), set()).add(z)
            else:
                edges.setdefault(("z", z + (1 if dz > 0 else 0), dz), set()).add(x)
    for (axis, line, sgn), cells in sorted(edges.items()):
        for a0, n in runs(sorted(cells)):
            if axis == "x":
                pa, pb, want = (line, a0), (line, a0 + n), [-sgn, 0, 0]
            else:
                pa, pb, want = (a0, line), (a0 + n, line), [0, 0, -sgn]
            pts = [(pa[0], STONE_H, pa[1]), (pb[0], STONE_H, pb[1]), (pb[0], WATER_H, pb[1]), (pa[0], WATER_H, pa[1])]
            ri_q.append(make_face(ch, pts, [(0, 0.0), (n, 0.0), (n, 0.19), (0, 0.19)], (32, 32), want))
            added += 1
    ch.set_faces(stone_si, st_t, st_q)
    ch.set_faces(rim_si, ri_t, ri_q)
    ch.add_shape(nsbmd.make_material(WATER_MAT, WATER_TEX, WATER_TEX, 32, 32, lights=0, fog=False), wa_t, wa_q)
    ch.add_shape(nsbmd.make_material(SHORE_MAT, SHORE_TEX, SHORE_TEX + "_pl", 32, 32, lights=0, fog=False), [], sh_q)
    return removed, added


# ---------------------------------------------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------------------------------------------

def texture_set():
    s = nsbtx.parse(open(TEXSET, "rb").read())
    tex = [t for t in s["textures"] if not t["name"].startswith("dw213_")]
    pals = [p for p in s["palettes"] if not p["name"].startswith("dw213_")]
    pal, rows = wood_texture()
    import png
    img = png.Image(32, 32, [[pal[v] + (255,) for v in r] for r in rows], palette=[c + (255,) for c in pal],
                    indices=rows, bit_depth=4, color_type=3)
    t, p = nsbtx.encode_texture(BOAT_TEX, img, "pltt16", c0=0)
    return nsbtx.build(tex + [t], pals + [p], pal_flag=s["header"]["pal_flag"])


def outputs():
    out = {}
    stats = {}
    for dst, (src, cx, cz) in CHUNKS.items():
        raw = rb.build_block(src, cx * 32, cz * 32, rb.B4F_OPEN, rb.B4F_BLOCK)
        ch = Chunk(raw, cx, cz)
        perm = mapdata.read_permissions(ch.parts["permissions"])
        if dst == 675:
            void = tiles_without_floor(ch, perm)
            for x, z in void:
                perm[z][x] |= BLOCKED
            faces = boat_faces(ch)
            mat = nsbmd.make_material(BOAT_TEX, BOAT_TEX, BOAT_TEX + "_pl", 32, 32)
            ch.add_shape(mat, [], faces)
            stats[dst] = {"boat_faces": len(faces), "void_tiles_blocked": len(void)}
        else:
            removed, added = rebuild_ceiling(ch)
            pier_removed, pier_added = build_pier(ch)
            stats[dst] = {"ceiling_removed": removed, "ceiling_added": added, "pier_removed": pier_removed,
                          "pier_added": pier_added}
        model = ch.build()
        assert len(model) <= 0xF000, (dst, len(model))
        st = nsbmd.model_stats(nsbmd.parse_bmd(model)["models"][0])
        stats[dst].update(model_bytes=len(model), polygons=st["polygons"])
        out[os.path.join(DATA, f"map_data_{dst}.bin")] = mapdata.pack(mapdata.write_permissions(perm),
                                                                      ch.parts["props"], model, ch.parts["bdhc"])
    out[os.path.join(MATRICES, f"map_matrix_{MATRIX_ID}.json")] = (json.dumps(
        {"name": MATRIX_NAME, "headers": [], "altitudes": [], "maps": [["MAP_675", "MAP_676"], ["MAP_614", "MAP_615"]]},
        indent=4) + "\n").encode()
    out[TEXSET] = texture_set()
    return out, stats


def main():
    check = "--check" in sys.argv
    outs, stats = outputs()
    for k, v in stats.items():
        print(k, v)
    ok = True
    for path, data in outs.items():
        same = os.path.exists(path) and open(path, "rb").read() == data
        ok &= same
        if not check and not same:
            open(path, "wb").write(data)
            print(os.path.relpath(path, ROOT), "written")
    if check:
        print("OK" if ok else "differs (run without --check)")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
