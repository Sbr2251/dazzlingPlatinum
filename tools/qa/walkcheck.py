#!/usr/bin/env python3
"""Automatic walkability-vs-graphics checker (QA tool).

Compares what is *drawn* (chunk model faces, DW ghost props) against
what the *collision* says (the permissions grid for the floor, the
tw_arc_attr grids for DW walls/ceilings) and reports tiles where the
two disagree: tiles that look walkable but are blocked, tiles that
look blocked but are walkable, water mismatches, and a few more.

  python3 tools/qa/walkcheck.py --map MAP_HEADER_ROUTE_214
  python3 tools/qa/walkcheck.py --map 293 --region 8,5,55,31
  python3 tools/qa/walkcheck.py --all-dw
  python3 tools/qa/walkcheck.py --all --out-dir /tmp/walkcheck
  python3 tools/qa/walkcheck.py --map MAP_HEADER_DW_ROUTE_214 --diff /path/to/other/tree

Drawn classification (floor surface), per tile, from the chunk models:

  floor   an upward-facing (normal y > 0.7) face of a ground material
          whose height sits in [base-1.2, base+1.2], where base is the
          chunk's modal ground height (so Jubilife chunks at h=1 and
          Eterna Forest chunks at h=6 are handled). This generalises
          the Route 214 seed rule (seed: upward face, normal y > 0.7,
          height in [-0.6, 1.2], non-water material).
  water   an upward water-material face (lake/lakep/bf_lake/bf_lakep/
          water/sea/river/pond/puddle/surf) at the same heights.
  stairs  a sloped face (0.3 < normal y <= 0.95) spanning >= 0.5 height.
  raised  an upward face with height in (base+1.2, base+3.5]: a ledge
          top, cliff top or bridge deck. Raised is neutral: it is
          neither flagged as floor nor as blocked-looking.
  tall    a tall obstacle centred on the tile: a gap-chain of
          faces whose centroids lie in the tile running from the
          ground (h <= base+0.6) up to the canopy/roof (h >=
          base+1.5), or a covering-centre chain of one material
          family from the ground up to the canopy/roof (that only
          explains a blocked tile -- a cone tree's canopy covers
          the tiles around the trunk too), or a building prop, or
          a facade/ditch face covering the tile centre. Trees,
          rocks, buildings and cliff faces never count as floor,
          so a tree tile is tall, not "drawn floor". A tile covered
          only by tree-canopy faces is "canopy" (neutral).
  void    nothing drawn at the tile centre (shadow decals, the
          s_land3_lm6 backdrop panel and prop water planes are
          excluded: a shadow does not make a tile look walkable).

Collision classification, from the permissions u16: bit 15 = blocked,
low byte = tile behaviour (names parsed from
include/constants/field/map_tile_behaviors.h). A blocked tile whose
behaviour is water / ledge / jump / warp / door / an interactable
(table, PC, berry patch, ...) is classed "behaviour", not plain
blocked: those tiles are traversable in a special way or are
designed obstacles, so drawn floor over them is not a mismatch.

Exemptions (a tile is explained, not a mismatch): object footprints
(object_events, including their movement ranges), warp tiles,
coord-event rects, DW jump tiles, and DW ghost props (any prop
explains a blocked tile; a stone-block prop, kind 23, is the drawn
block). An allowlist file (tools/qa/walkcheck_allow.json) covers
intentional cases with a reason each; allowlisted tiles are listed
separately and do not gate the exit code.

DW surfaces: a DW map's tw_arc record (twarc.py) gives wall and
ceiling platforms whose collision comes from tw_arc_attr.narc, with
the engine's indexing (ceiling: relVert = sizeX - (x - startX);
east wall: relVert = y - startY; west wall: relVert =
sizeY - (y - startY); relHoriz = z - startZ in all cases;
index = relVert + relHoriz * tiles_v). The platform geometry in the
chunk models is what is drawn: a ceiling tile is drawn if a solid
face (not the s_land3_lm6 backdrop, not a water surface) covers it
at the platform height; a wall tile is drawn if a face covers its
(y, z) centre near the wall plane. Floor tiles of DW maps are
checked only on tiles in scope: reachable by walking/jumping from
the entry plus their neighbours plus designed tiles (objects,
warps, jumps, props) -- the unreachable B4F quadrants of a DW
matrix are not QA-relevant. Stock maps are checked on all of their
chunks.

Outputs: a JSON report, a per-map overlay PNG (colour-coded, with a
legend; stdlib png.py), a one-line summary per map, and exit code 1
if any HIGH-severity mismatch exists. Standard library plus the
repo's own modules only.
"""
import argparse
import collections
import importlib.util
import json
import math
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

# ---------------------------------------------------------------- material taxonomy
WATER_SUBS = ("lake", "lakep", "bf_lake", "bf_lakep", "water", "sea",
              "river", "pond", "puddle", "surf")
SHADOW_SUBS = ("shadow", "tshadow", "decal", "mark_")
TREE_SUBS = ("tree", "conttree", "sbt01", "sbt02")
CLIFF_SUBS = ("criff", "cliff", "wcliff")
IMPED_SUBS = ("imped",)
BACKDROP_MATS = {"s_land3_lm6"}
# Water surfaces on a DW ceiling: the hanging-lake materials are real
# water; bf_lake/bf_lakep there are the lakebed underside (solid).
CEIL_WATER_SUBS = ("dw213_lake", "dw213_lakep", "dw214_lake",
                   "dw214_lakep", "lake", "lakep")


def is_ceiling_water_mat(name):
    """Ceiling water: the hanging-lake surfaces. bf_lake/bf_lakep
    are lakebed (solid), not water, despite the substring."""
    base = re.sub(r"_lm\d+$", "", name)
    return base in CEIL_WATER_SUBS
GHOST_BLOCK_KIND = 23  # PROP_KIND_LAND_ROCK, the stone block
DW_ENTRY = (20, 12)    # shared entry tile of the DW rift maps


def is_water_mat(name):
    return any(s in name for s in WATER_SUBS)


def is_tree_mat(name):
    return any(s in name for s in TREE_SUBS)


def is_cliff_mat(name):
    return any(s in name for s in CLIFF_SUBS)


def is_imped_mat(name):
    return any(s in name for s in IMPED_SUBS)


def is_shadow_mat(name):
    return any(s in name for s in SHADOW_SUBS)


def is_facade_mat(name):
    return re.match(r"^c\d+_f(_|$)", name) is not None


def is_floor_excluded_mat(name):
    """Materials that never count as drawn floor (they are obstacles,
    cliff, shadow decals, building facades, or the backdrop panel)."""
    return (is_shadow_mat(name) or is_tree_mat(name) or is_cliff_mat(name)
            or is_imped_mat(name) or is_facade_mat(name)
            or name in BACKDROP_MATS or is_water_mat(name))


def family_of(name):
    """Material family for the tall-chain test. Building materials
    (c1_g1, c1_r1, c1_f_ud, ...) group by their building prefix;
    s_land / s_land2 / s_land3 stay distinct; the rest group by
    their first token (tree01, conttree, ngrass, ...)."""
    base = re.sub(r"_lm\d+$", "", name)
    if re.match(r"^c\d+_", base):
        return "_".join(base.split("_")[:2]) if False else base.split("_")[0]
    if base.startswith("s_"):
        return base
    return base.split("_")[0]


# ---------------------------------------------------------------- behaviour names
def load_behaviour_names(root):
    """Tile-behaviour names, in enum order, from the repo header."""
    path = os.path.join(root, "include", "constants", "field",
                        "map_tile_behaviors.h")
    names = []
    try:
        for line in open(path):
            line = line.strip()
            if line.startswith("TILE_BEHAVIOR_"):
                names.append(line.split()[0].rstrip(","))
    except OSError:
        pass
    return names


def behaviour_kind(names, beh):
    """'water' | 'directional' | 'warp' | 'special' | 'floor' | 'walkable'.

    directional = ledge / jump / slide / rock climb (traversable one
    way, or blocked from one side only); warp = door / warp / stairs /
    escalator; special = interactable furniture (table, PC, TV, town
    map, berry patch) that blocks stepping but is a designed object.
    """
    name = names[beh] if beh < len(names) else "TILE_BEHAVIOR_UNKNOWN_%02x" % beh
    core = name.replace("TILE_BEHAVIOR_", "")
    if ("WATER" in core or "PUDDLE" in core or "SHALLOW" in core
            or core == "WATERFALL"):
        return "water"
    if (core.startswith("BLOCK_") or core.startswith("JUMP_")
            or core.startswith("SLIDE_") or core.startswith("ROCK_CLIMB")):
        return "directional"
    if ("WARP" in core or core == "DOOR" or "ESCALATOR" in core
            or "STAIR" in core):
        return "warp"
    if (core in ("TABLE", "PC", "TOWN_MAP", "TV", "BERRY_PATCH",
                "UNKNOWN_x88", "UNKNOWN_x8E")
            or "BOOKSHELF" in core or "TRASH_CAN" in core
            or "MART_SHELF" in core or "SIGN" in core
            or core in ("NOTICE_BOARD", "POSTER", "BULLETIN_BOARD")):
        return "special"
    if core in ("BRIDGE_START", "BRIDGE", "BRIDGE_OVER_CAVE",
                "BRIDGE_OVER_WATER", "BRIDGE_OVER_SAND",
                "BRIDGE_OVER_SNOW") or core.startswith("BIKE_BRIDGE"):
        return "bridge"
    return "floor"


def classify_collision(raw, names):
    """-> (collision, behaviour_name): collision in
    walkable | water | behaviour | blocked."""
    blocked = bool(raw & 0x8000)
    beh = raw & 0xFF
    kind = behaviour_kind(names, beh)
    beh_name = names[beh] if beh < len(names) else "UNKNOWN_%02x" % beh
    if blocked:
        if kind in ("water", "directional", "warp", "special", "bridge"):
            return "behaviour", beh_name
        return "blocked", beh_name
    if kind == "water":
        return "water", beh_name
    if kind in ("directional", "warp", "special", "bridge"):
        return "behaviour", beh_name
    return "walkable", beh_name


# ---------------------------------------------------------------- repo module loading (per-tree)
def load_module(root, relpath, name):
    path = os.path.join(root, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Tree:
    """One checkout: repo modules loaded from that tree's paths."""

    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.mapdata = load_module(self.root, "tools/lake_verity/mapdata.py",
                                   "walkcheck_mapdata_%x" % abs(hash(self.root)))
        self.nsbmd = load_module(self.root, "tools/lake_verity/nsbmd.py",
                                 "walkcheck_nsbmd_%x" % abs(hash(self.root)))
        self.png = load_module(self.root, "tools/lake_verity/png.py",
                               "walkcheck_png_%x" % abs(hash(self.root)))
        self.narc = load_module(self.root, "tools/coronet_lava/narc.py",
                                "walkcheck_narc_%x" % abs(hash(self.root)))
        self._build_models = None
        self._prop_cache = {}
        # twarc imports narc from the same tree.
        sys.path.insert(0, os.path.join(self.root, "tools", "coronet_lava"))
        sys.path.insert(0, os.path.join(self.root, "tools", "distortion_world"))
        self.twarc = load_module(self.root, "tools/distortion_world/twarc.py",
                                 "walkcheck_twarc_%x" % abs(hash(self.root)))
        self.names = load_behaviour_names(self.root)
        self._chunk_faces = {}
        self._chunk_perms = {}
        self._headers = None

    # -- map headers ---------------------------------------------------
    def headers(self):
        """{header: (matrix_id, events_archive_id)} from map_headers.h."""
        if self._headers is not None:
            return self._headers
        out = {}
        path = os.path.join(self.root, "include", "data", "map_headers.h")
        try:
            text = open(path).read()
        except OSError:
            text = ""
        for m in re.finditer(r"\[(MAP_HEADER_\w+)\]", text):
            header = m.group(1)
            window = text[m.start():m.start() + 1400]
            mm = re.search(r"\.mapMatrixID\s*=\s*(0x[0-9a-fA-F]+|\d+)", window)
            ev = re.search(r"\.eventsArchiveID\s*=\s*(\w+)", window)
            if mm:
                out[header] = (int(mm.group(1), 0),
                               ev.group(1) if ev else None)
        self._headers = out
        return out

    def matrix_path(self, mid):
        return os.path.join(self.root, "res", "field", "maps", "matrices",
                            "map_matrix_%03d.json" % mid)

    def load_matrix(self, mid):
        with open(self.matrix_path(mid)) as f:
            return json.load(f)

    # -- chunk geometry -------------------------------------------------
    def chunk_faces(self, chunk):
        """[(material, normal_y, min_h, max_h, pts)] in matrix tiles,
        chunk-relative origin resolved by the caller via offsets."""
        if chunk in self._chunk_faces:
            return self._chunk_faces[chunk]
        path = os.path.join(self.root, "res", "field", "maps", "data",
                            "map_data_%03d.bin" % chunk)
        parts = self.mapdata.unpack(open(path, "rb").read())
        model = self.nsbmd.parse_bmd(parts["model"])["models"][0]
        pos_scale = model["info"]["pos_scale"] / self.nsbmd.FX
        pairs = self.nsbmd.shape_material_pairs(model)
        prims = self.nsbmd.model_prims(model)
        matname = {i: mm["name"] for i, mm in enumerate(model["materials"])}
        faces = []
        for mi, si in pairs:
            tris, quads = self.nsbmd.prims_to_faces(prims[si][1])
            for face in tris + quads:
                pts = []
                for v in face:
                    wx, wy, wz = (c / (self.nsbmd.FX / pos_scale)
                                  for c in v["pos"])
                    pts.append((wx / 16.0, (wy - 16.0) / 16.0, wz / 16.0))
                a, b, c = pts[0], pts[1], pts[2]
                u = [b[i] - a[i] for i in range(3)]
                vv = [c[i] - a[i] for i in range(3)]
                n = [u[1] * vv[2] - u[2] * vv[1],
                     u[2] * vv[0] - u[0] * vv[2],
                     u[0] * vv[1] - u[1] * vv[0]]
                ln = math.sqrt(sum(x * x for x in n)) or 1.0
                faces.append((matname[mi], n[1] / ln,
                              min(p[1] for p in pts), max(p[1] for p in pts),
                              pts, tuple(pts)))
        self._chunk_faces[chunk] = faces
        while len(self._chunk_faces) > 256:
            self._chunk_faces.pop(next(iter(self._chunk_faces)))
        return faces

    def build_models(self):
        """build_model.narc members (NSBMD blobs, one per prop model)."""
        if self._build_models is None:
            path = os.path.join(self.root, "res", "prebuilt", "fielddata",
                                "build_model", "build_model.narc")
            self._build_models = self.narc.read_files(path)[2]
        return self._build_models

    def prop_footprint(self, chunk, cx, cz):
        """[(name, x0, z0, x1, z1, h_min, h_max)] of one chunk's props,
        in absolute matrix tiles. Rotation is ignored (props are
        overwhelmingly axis-aligned; the bbox may over-cover a
        rotated prop by a tile), which is safe here: a prop
        footprint only ever *explains* a blocked tile."""
        key = (chunk, cx, cz)
        if key in self._prop_cache:
            return self._prop_cache[key]
        out = []
        try:
            path = os.path.join(self.root, "res", "field", "maps", "data",
                                "map_data_%03d.bin" % chunk)
            parts = self.mapdata.unpack(open(path, "rb").read())
            props = self.mapdata.read_props(parts["props"])
            models = self.build_models()
        except (OSError, IndexError, struct.error):
            self._prop_cache[key] = out
            return out
        for pr in props:
            bm_id = pr["model"]
            if bm_id >= len(models):
                continue
            try:
                pm = self.nsbmd.parse_bmd(models[bm_id])["models"][0]
            except Exception:
                continue
            ps = pm["info"]["pos_scale"] / self.nsbmd.FX
            off = [v / 4096.0 for v in pr["pos"]]
            scl = [v / 4096.0 for v in pr.get("scale", [4096, 4096, 4096])]
            verts = []
            # Collect vertices straight from the shape display lists.
            for shape in pm["shapes"]:
                for _t, vs in self.nsbmd.dl_primitives(
                        self.nsbmd.dl_decode(shape["dl"])):
                    for v in vs:
                        x = (v["pos"][0] / self.nsbmd.FX * ps * scl[0] + off[0]) / 16.0 + 16 + cx * 32
                        h = (v["pos"][1] / self.nsbmd.FX * ps * scl[1] + off[1] - 16.0) / 16.0
                        z = (v["pos"][2] / self.nsbmd.FX * ps * scl[2] + off[2]) / 16.0 + 16 + cz * 32
                        verts.append((x, h, z))
            if verts:
                out.append((pm["name"],
                            min(v[0] for v in verts), min(v[2] for v in verts),
                            max(v[0] for v in verts), max(v[2] for v in verts),
                            min(v[1] for v in verts), max(v[1] for v in verts)))
        self._prop_cache[key] = out
        while len(self._prop_cache) > 256:
            self._prop_cache.pop(next(iter(self._prop_cache)))
        return out

    def chunk_perm(self, chunk):
        if chunk not in self._chunk_perms:
            path = os.path.join(self.root, "res", "field", "maps", "data",
                                "map_data_%03d.bin" % chunk)
            parts = self.mapdata.unpack(open(path, "rb").read())
            self._chunk_perms[chunk] = self.mapdata.read_permissions(parts["permissions"])
            while len(self._chunk_perms) > 256:
                self._chunk_perms.pop(next(iter(self._chunk_perms)))
        return self._chunk_perms[chunk]


def covers_centre(px, pz, poly):
    """Centre test with a half-tile tolerance: a face covering half a
    tile still draws over it (diagonal wall faces end mid-tile)."""
    if point_in_poly(px, pz, poly):
        return True
    hits = 0
    for dx, dz in ((0.3, 0.3), (-0.3, 0.3), (0.3, -0.3), (-0.3, -0.3)):
        if point_in_poly(px + dx, pz + dz, poly):
            hits += 1
    return hits >= 2


def poly_area(poly):
    """XZ polygon area (shoelace) of a face's (x, h, z) vertices."""
    a = 0.0
    for i in range(len(poly)):
        x1, z1 = poly[i][0], poly[i][2]
        x2, z2 = poly[(i + 1) % len(poly)][0], poly[(i + 1) % len(poly)][2]
        a += x1 * z2 - x2 * z1
    return abs(a) / 2.0


def point_in_poly(px, pz, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        if (z1 > pz) != (z2 > pz) and px < x1 + (pz - z1) * (x2 - x1) / (z2 - z1):
            inside = not inside
    return inside


# ---------------------------------------------------------------- map model
class MapData:
    def __init__(self, tree, header, matrix_id):
        self.tree = tree
        self.header = header
        self.matrix_id = matrix_id
        self.matrix = tree.load_matrix(matrix_id)
        self.cells = []  # (cell_x, cell_z, chunk)
        headers = self.matrix.get("headers") or []
        maps = self.matrix.get("maps") or []
        if headers:
            for rz, row in enumerate(headers):
                for cx, h in enumerate(row):
                    if h == header and maps and maps[rz][cx] != "MAP_NONE":
                        self.cells.append((cx, rz, int(maps[rz][cx][4:])))
        else:
            for rz, row in enumerate(maps):
                for cx, name in enumerate(row):
                    if name != "MAP_NONE":
                        self.cells.append((cx, rz, int(name[4:])))
        self.tiles = {}  # (x, z) -> (chunk, local_x, local_z)
        for cx, cz, chunk in self.cells:
            for lz in range(32):
                for lx in range(32):
                    self.tiles[(cx * 32 + lx, cz * 32 + lz)] = (chunk, lx, lz)
        self.bases = {}  # chunk -> modal ground height
        self.prop_tiles = collections.defaultdict(list)  # (x,z) -> prop footprints
        self.tile_faces = collections.defaultdict(list)  # (x,z) -> faces
        self.wall_faces = collections.defaultdict(list)  # (h_tile,z) -> faces
        pass
        self.events = {"objects": [], "warps": [], "coords": []}
        self.dw = None  # twarc record, if any
        self.dw_error = None  # DW parse failure, if any (see _load_dw)
        self._load_events()
        self._load_dw()
        self._load_geometry()

    # -- events ---------------------------------------------------------
    def _load_events(self):
        hdr = self.tree.headers().get(self.header, (None, None))
        ev_name = hdr[1]
        cands = []
        if ev_name:
            cands.append("events_%s.json" % ev_name[len("events_"):] if ev_name.startswith("events_") else "%s.json" % ev_name)
            cands.append("%s.json" % ev_name)
        cands.append("events_%s.json" % self.header[len("MAP_HEADER_"):].lower())
        for name in cands:
            path = os.path.join(self.tree.root, "res", "field", "events", name)
            if os.path.exists(path):
                try:
                    data = json.load(open(path))
                except (OSError, ValueError):
                    return
                for o in data.get("object_events", []):
                    self.events["objects"].append(o)
                for w in data.get("warp_events", []):
                    self.events["warps"].append(w)
                for c in data.get("coord_events", []):
                    self.events["coords"].append(c)
                return

    def object_tiles(self):
        # Base tile only. An object blocks the tile it stands on;
        # its movement range is where it *might* walk, which does not
        # explain plain blocked collision under visible floor there.
        return {(o.get("x", 0), o.get("z", 0)): o
                for o in self.events["objects"]}

    def warp_tiles(self):
        return {(w.get("x"), w.get("z")): w for w in self.events["warps"]}

    def coord_tiles(self):
        out = {}
        for c in self.events["coords"]:
            w = c.get("width", 1) or 1
            l = c.get("length", 1) or 1
            for dx in range(w):
                for dz in range(l):
                    out[(c.get("x", 0) + dx, c.get("z", 0) + dz)] = c
        return out

    # -- geometry -------------------------------------------------------
    def _chunk_base(self, chunk, faces, cx=0, cz=0):
        """Modal ground height of a chunk: the lowest height with at
        least half the modal count, over ground-like upward faces.
        Faces whose centre lies in a DW ceiling-platform footprint
        are excluded: a chunk can contain a ceiling slab whose top
        faces would otherwise outvote the ground plane."""
        footprints = []
        if self.dw:
            for plat in self.dw["record"]["platforms"]:
                if plat["kind"] == 3:
                    footprints.append((plat["x"], plat["z"],
                                       plat["x"] + plat["sx"],
                                       plat["z"] + plat["sz"]))
        counts = collections.Counter()
        for mat, ny, mn, mx, pts, _ in faces:
            if ny > 0.7 and not is_floor_excluded_mat(mat):
                ccx = sum(p[0] for p in pts) / len(pts) + 16 + cx * 32
                ccz = sum(p[2] for p in pts) / len(pts) + 16 + cz * 32
                if any(x0 <= ccx <= x1 and z0 <= ccz <= z1
                       for x0, z0, x1, z1 in footprints):
                    continue
                counts[round(mn * 2) / 2] += 1
        if not counts:
            counts = collections.Counter()
            for mat, ny, mn, mx, pts, _ in faces:
                if ny > 0.7 and not is_shadow_mat(mat) and not is_water_mat(mat):
                    counts[round(mn * 2) / 2] += 1
        if not counts:
            return 0.0
        top = max(counts.values())
        # Lowest prominent height: a chunk can contain a whole
        # ceiling slab whose top faces outnumber the ground plane
        # (DW B4F chunks: 138 faces at h=13 vs 23 at h<=0).
        cands = [h for h, c in counts.items() if c >= max(3, 0.1 * top)]
        return min(cands) if cands else min(counts)

    def _load_geometry(self):
        tree = self.tree
        tile_set = set(self.tiles)
        # Chunks to read faces from: the map's own chunks plus the
        # matrix cells adjacent to them (geometry spills a tile or
        # two over a chunk border, e.g. tree canopies).
        wanted = {}
        for cx, cz, chunk in self.cells:
            wanted[(cx, cz)] = chunk
        maps = self.matrix.get("maps") or []
        for cx, cz, _ in list(self.cells):
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    if 0 <= cz + dr < len(maps) and 0 <= cx + dc < len(maps[cz + dr]):
                        name = maps[cz + dr][cx + dc]
                        if name != "MAP_NONE":
                            wanted[(cx + dc, cz + dr)] = int(name[4:])
        # Per-chunk bases (from the chunk's own faces).
        for (cx, cz), chunk in wanted.items():
            if chunk not in self.bases:
                self.bases[chunk] = self._chunk_base(
                    chunk, tree.chunk_faces(chunk), cx, cz)
        # Prop footprints -> tiles (from this map's chunks and the
        # adjacent chunks, whose props can spill over the border).
        for (cx, cz), chunk in wanted.items():
            for name, x0, z0, x1, z1, mn, mx in tree.prop_footprint(chunk, cx, cz):
                for z in range(int(math.floor(z0)), int(math.floor(z1)) + 1):
                    for x in range(int(math.floor(x0)), int(math.floor(x1)) + 1):
                        if (x, z) in tile_set:
                            self.prop_tiles[(x, z)].append((name, mn, mx))
        # Face -> tile assignment, in absolute matrix tiles.
        for (cx, cz), chunk in wanted.items():
            base = self.bases[chunk]
            for mat, ny, mn, mx, pts, _ in tree.chunk_faces(chunk):
                shifted = [(p[0] + 16 + cx * 32, p[1], p[2] + 16 + cz * 32)
                           for p in pts]
                # Floor / ceiling faces: bbox in (x, z).
                x0 = int(math.floor(min(p[0] for p in shifted)))
                x1 = int(math.floor(max(p[0] for p in shifted)))
                z0 = int(math.floor(min(p[2] for p in shifted)))
                z1 = int(math.floor(max(p[2] for p in shifted)))
                rec = (mat, ny, mn, mx, shifted, base)
                for z in range(z0, z1 + 1):
                    for x in range(x0, x1 + 1):
                        if (x, z) in tile_set:
                            self.tile_faces[(x, z)].append(rec)
                # Wall faces: bbox in (h, z), kept for DW walls.
                h0 = int(math.floor(min(p[1] for p in shifted)))
                h1 = int(math.floor(max(p[1] for p in shifted)))
                xlo = min(p[0] for p in shifted)
                xhi = max(p[0] for p in shifted)
                for z in range(z0, z1 + 1):
                    for h in range(h0, h1 + 1):
                        self.wall_faces[(h, z)].append(
                            (mat, shifted, xlo, xhi, base))
    # -- DW -------------------------------------------------------------
    def _load_dw(self):
        try:
            twarc = self.tree.twarc
            import narc as _narc
            hdr, btnf, tw = _narc.read_files(twarc.TW)
            index = twarc.read_index(tw[0])
            mid = twarc.map_header_id(self.header)
            entry = next((e for e in index if e[0] == mid), None)
            if entry is None:
                return
            rec = twarc.parse_record(tw[entry[1] + 1])
            # The tw_arc record stores DW *world* coordinates; the
            # chunk models (and the map's tile grid) are in map-local
            # coordinates, so subtract the index offset. The custom
            # DW maps use offset (0, 0, 0); the stock DW floors are
            # stacked in world Y (B2F at y 224, ...).
            off = list(entry[2:5])
            for plat in rec["platforms"]:
                plat["x"] -= off[0]; plat["y"] -= off[1]; plat["z"] -= off[2]
            for j in rec["jumps"]:
                j["x"] -= off[0]; j["y"] -= off[1]; j["z"] -= off[2]
            for c in rec["cameras"]:
                c["x"] -= off[0]; c["y"] -= off[1]; c["z"] -= off[2]
            for pr in rec["ghost"]["props"]:
                pr["x"] -= off[0]; pr["y"] -= off[1]; pr["z"] -= off[2]
            for tr in rec["ghost"]["triggers"]:
                tr["bounds"][0] -= off[0]; tr["bounds"][1] -= off[1]
                tr["bounds"][2] -= off[2]
            ahdr, abtnf, attr = _narc.read_files(twarc.ATTR)
            grids = {}
            for p in rec["platforms"]:
                if p["attr"] < len(attr):
                    grids[p["attr"]] = struct.unpack("<1024H", attr[p["attr"]])
            off = entry[2:5]
            self.dw = {"record": rec, "grids": grids, "offset": off}
        except Exception as e:
            # A corrupt/missing platform archive must not silently
            # disable DW support: the report records dw_error and
            # main() exits 2 rather than passing the gate.
            self.dw = None
            self.dw_error = "%s: %s" % (type(e).__name__, e)

    # -- drawn classification --------------------------------------------
    def drawn_floor(self, x, z):
        """-> (drawn, evidence, centred, from_prop): drawn in
        floor|water|stairs|raised|tall|canopy|void. centred is True
        when a gap-chain of faces with centroids in the tile runs
        from the ground to the canopy/roof: a tall obstacle centred
        on this tile (the strong evidence for a walk-through flag).
        A covering-centre chain (faces covering the centre from
        ground to canopy) only explains a blocked tile: a tree's
        canopy/root faces cover the tiles around the trunk too."""
        chunk = self.tiles.get((x, z), (None,))[0]
        base = self.bases.get(chunk, 0.0)
        faces = self.tile_faces.get((x, z), [])
        covering = []
        centroid = []
        for mat, ny, mn, mx, pts, _ in faces:
            if point_in_poly(x + 0.5, z + 0.5, [(p[0], p[2]) for p in pts]):
                covering.append((mat, ny, mn, mx, pts))
            ccx = sum(p[0] for p in pts) / len(pts)
            ccz = sum(p[2] for p in pts) / len(pts)
            if int(math.floor(ccx)) == x and int(math.floor(ccz)) == z:
                centroid.append((mat, ny, mn, mx, pts))
        if not covering and not centroid:
            return "void", "no face covers the tile centre", False, False
        water = [f for f in covering
                 if f[1] > 0.7 and is_water_mat(f[0])
                 and base - 1.2 <= f[2] <= base + 1.2]
        floor = [f for f in covering
                 if f[1] > 0.7
                 and (not is_floor_excluded_mat(f[0])
                      or ("wcliff" in f[0]))
                 and base - 1.2 <= f[2] <= base + 1.2 and f[3] <= base + 1.8]
        stairs = [f for f in covering
                  if 0.3 < f[1] <= 0.95 and not is_floor_excluded_mat(f[0])
                  and base - 1.2 <= f[2] <= base + 1.2 and f[3] - f[2] >= 0.5]
        raised = [f for f in covering
                  if f[1] > 0.7 and not is_shadow_mat(f[0])
                  and not is_water_mat(f[0])
                  and base + 1.2 < f[2] <= base + 3.5]
        # Gap-chain test over one family of faces: intervals from the
        # ground (first min_h <= base+0.6) to the canopy/roof (max_h
        # >= base+1.5) with no gap > 0.75 between consecutive faces.
        def gap_chain(fl):
            ivs = sorted((f[2], f[3]) for f in fl)
            if not ivs or ivs[0][0] > base + 0.6:
                return False
            cur = ivs[0][1]
            for lo, hi in ivs[1:]:
                if lo <= cur + 0.75:
                    cur = max(cur, hi)
                else:
                    break
            return cur >= base + 1.5
        byfam_cent = collections.defaultdict(list)
        for f in centroid:
            if is_shadow_mat(f[0]) or is_water_mat(f[0]):
                continue
            byfam_cent[family_of(f[0])].append(f)
        centred = False
        centred_why = ""
        for fam, fl in byfam_cent.items():
            if gap_chain(fl):
                centred = True
                centred_why = "centred chain %s" % fam
                break
        # Covering-centre chain (explains a blocked tile).
        byfam_cov = collections.defaultdict(list)
        for f in covering:
            if is_shadow_mat(f[0]) or is_water_mat(f[0]):
                continue
            byfam_cov[family_of(f[0])].append(f)
        cover_why = ""
        for fam, fl in byfam_cov.items():
            lo = min(f[2] for f in fl)
            hi = max(f[3] for f in fl)
            if lo <= base + 0.6 and hi >= base + 1.5:
                cover_why = "chain %s h %.2f..%.2f" % (fam, lo, hi)
                break
        if centred:
            return "tall", centred_why, True, False
        if cover_why:
            return "tall", cover_why, False, False
        # A building-facade or ditch face covering the centre means
        # the tile is a wall/fence/ditch strip (city perimeter), not
        # floor -- even though the ground plane also covers it.
        struct = [f for f in covering
                  if is_facade_mat(f[0])
                  or re.match(r"^c\d+_d(_|$)", f[0]) is not None]
        if struct:
            return "tall", "facade/ditch face %s h %.2f..%.2f" % (
                struct[0][0], struct[0][2], struct[0][3]), False, False
        # Chunk props: a tall building prop over the tile makes it
        # a tall obstacle; a flat water prop (a lake plane) makes it
        # drawn water. Rotation is ignored in the footprint, so a
        # prop footprint only ever explains, never flags.
        props_here = self.prop_tiles.get((x, z), [])
        tall_prop = [p for p in props_here
                     if not is_shadow_mat(p[0]) and p[2] >= base + 1.5]
        water_prop = [p for p in props_here
                      if any(w in p[0] for w in ("lake", "water", "pond"))
                      and p[2] - p[1] < 0.5 and base - 1.2 <= p[1] <= base + 0.3]
        if tall_prop:
            # A tall prop footprint is approximate (bbox, rotation
            # ignored): it explains a blocked tile, but it must
            # never itself produce a mismatch (from_prop=True).
            return "tall", "building prop %s h %.2f..%.2f" % (
                tall_prop[0][0], tall_prop[0][1], tall_prop[0][2]), False, True
        if water_prop and not floor:
            return "water", "water-plane prop %s h %.2f" % (
                water_prop[0][0], water_prop[0][1]), False, False
        if water and (not floor or water[0][2] >= floor[0][2] - 0.3):
            return "water", "water face %s h %.2f" % (water[0][0], water[0][2]), False, False
        if floor:
            return "floor", "floor face %s h %.2f..%.2f" % (floor[0][0], floor[0][2], floor[0][3]), False, False
        if stairs:
            return "stairs", "sloped face %s h %.2f..%.2f" % (stairs[0][0], stairs[0][2], stairs[0][3]), False, False
        if raised:
            return "raised", "raised face %s h %.2f" % (raised[0][0], raised[0][2]), False, False
        non_shadow = [f for f in covering if not is_shadow_mat(f[0])]
        if non_shadow and all(is_tree_mat(f[0]) for f in non_shadow):
            return "canopy", "tree canopy faces only (no trunk on this tile)", False, False
        return "void", "faces present but none is floor/water/tall: %s" % (
            ", ".join(sorted({f[0] for f in covering}))), False, False

    def drawn_dw_surface(self, plat, x, z):
        """-> (drawn, evidence) for a ceiling- or floor-platform tile:
        a solid face at the platform height, else a water face."""
        y = plat["y"]
        water_subs = CEIL_WATER_SUBS if plat["kind"] == 3 else WATER_SUBS
        faces = []
        for mat, ny, mn, mx, pts, _ in self.tile_faces.get((x, z), []):
            if covers_centre(x + 0.5, z + 0.5, [(p[0], p[2]) for p in pts]):
                faces.append((mat, ny, mn, mx))
        def is_water(f):
            return is_ceiling_water_mat(f[0]) if water_subs is CEIL_WATER_SUBS else is_water_mat(f[0])
        solid = [f for f in faces
                 if f[0] not in BACKDROP_MATS
                 and not is_water(f)
                 and y - 0.5 <= f[2] <= y + 2.5]
        water = [f for f in faces
                 if is_water(f)
                 and y - 0.5 <= f[2] <= y + 2.5]
        if solid:
            return "floor", "platform slab face %s h %.2f" % (solid[0][0], solid[0][2])
        if water:
            return "water", "platform water face %s h %.2f" % (water[0][0], water[0][2])
        return "void", "no platform face at h %.1f..%.1f" % (y - 0.5, y + 2.5)

    def drawn_dw_wall(self, plat, y, z):
        """-> (drawn, evidence) for a wall-platform tile (y, z).

        The visual wall face sits about a tile out from the walkable
        column (east wall: x ~ plane+1; west wall: x ~ plane-1) and
        is thin in x; a fat face there is a floor/ceiling face that
        merely overlaps the (h, z) projection."""
        x_plane = plat["x"]
        faces = []
        for mat, pts, xlo, xhi, _ in self.wall_faces.get((y, z), []):
            if xhi - xlo > 2.0:
                continue
            if plat["kind"] == 2:  # east wall: face just east of the column
                if not (xlo <= x_plane + 2.5 and xhi >= x_plane + 0.5):
                    continue
            else:  # west wall: face just west of the column
                if not (xhi >= x_plane - 2.5 and xlo <= x_plane - 0.5):
                    continue
            if covers_centre(y + 0.5, z + 0.5, [(p[1], p[2]) for p in pts]):
                faces.append((mat, xlo, xhi))
        if faces:
            return "floor", "wall face %s x %.2f..%.2f" % (
                faces[0][0], faces[0][1], faces[0][2])
        return "void", "no wall face near x=%d" % x_plane


# ---------------------------------------------------------------- analysis
def dw_platform_tiles(plat):
    """(key, label) tiles of a platform, in engine coordinates.

    Floor platform: (x, z). Wall: (y, z), keyed by (y, z). Ceiling: (x, z).
    """
    if plat["kind"] == 0:  # floor
        return [((x, z), (x, z)) for x in range(plat["x"], plat["x"] + plat["sx"] + 1)
                for z in range(plat["z"], plat["z"] + plat["sz"] + 1)]
    if plat["kind"] in (1, 2):  # walls
        return [((y, z), (y, z)) for y in range(plat["y"], plat["y"] + plat["sy"] + 1)
                for z in range(plat["z"], plat["z"] + plat["sz"] + 1)]
    # ceiling
    return [((x, z), (x, z)) for x in range(plat["x"], plat["x"] + plat["sx"] + 1)
            for z in range(plat["z"], plat["z"] + plat["sz"] + 1)]


def dw_attr_collision(md, plat, key):
    """Collision (attr grid value) of one platform tile, engine indexing."""
    grid = md.dw["grids"].get(plat["attr"])
    if grid is None:
        return None
    tiles_v = plat["tiles_v"] or 32
    if plat["kind"] == 0:
        rv = key[0] - plat["x"]
        rh = key[1] - plat["z"]
    elif plat["kind"] == 1:  # west wall
        rv = plat["sy"] - (key[0] - plat["y"])
        rh = key[1] - plat["z"]
    elif plat["kind"] == 2:  # east wall
        rv = key[0] - plat["y"]
        rh = key[1] - plat["z"]
    else:  # ceiling
        rv = plat["sx"] - (key[0] - plat["x"])
        rh = key[1] - plat["z"]
    if not (0 <= rv < 32 and 0 <= rh < 32):
        return None
    return grid[rv + rh * tiles_v]


def dw_surface_name(plat):
    return {0: "floor", 1: "wall", 2: "wall", 3: "ceiling"}.get(plat["kind"], "floor")


def analyse_map(tree, header, matrix_id, region, allowlist):
    md = MapData(tree, header, matrix_id)
    names = tree.names
    objects = md.object_tiles()  # base tiles only: an object blocks the
    # tile it stands on, not every tile of its movement range.
    warps = md.warp_tiles()
    coords = md.coord_tiles()
    # DW jump tiles (floor coords) and jump landings, from the twarc record.
    jump_tiles = set()
    jump_landings = set()
    if md.dw:
        for j in md.dw["record"]["jumps"]:
            for dx in range(j["sx"] + 1):
                for dz in range(j["sz"] + 1):
                    jump_tiles.add((j["x"] + dx, j["z"] + dz))
                    jump_landings.add((j["x"] + j["dx"] + dx,
                                       j["z"] + j["dz"] + dz))
    # DW ghost props, keyed by surface tile: (kind, visible, group).
    # Only props whose group is in the record's default_visible mask
    # are drawn when the map loads; a hidden prop is not drawn, so
    # it does not explain a blocked tile (its tile must show some
    # other drawn geometry, or it is a mismatch).
    ghost_by_tile = collections.defaultdict(list)
    if md.dw:
        default_visible = md.dw["record"]["ghost"]["default_visible"]
        for pr in md.dw["record"]["ghost"]["props"]:
            surf = None
            key = None
            for plat in md.dw["record"]["platforms"]:
                if plat["kind"] == 3 and pr["y"] == plat["y"] and \
                        plat["x"] <= pr["x"] <= plat["x"] + plat["sx"] and \
                        plat["z"] <= pr["z"] <= plat["z"] + plat["sz"]:
                    surf, key = "ceiling", (pr["x"], pr["z"])
                elif plat["kind"] in (1, 2) and pr["x"] == plat["x"] and \
                        plat["y"] <= pr["y"] <= plat["y"] + plat["sy"] and \
                        plat["z"] <= pr["z"] <= plat["z"] + plat["sz"]:
                    surf, key = "wall", (pr["y"], pr["z"])
            if surf is None:
                surf, key = ("floor", (pr["x"], pr["z"])) if pr["y"] <= 1 else ("ceiling", (pr["x"], pr["z"]))
            visible = bool(default_visible & (1 << pr["group"]))
            ghost_by_tile[(surf, key)].append((pr["kind"], visible, pr["group"]))
    # Per-surface jump source / landing keys, classified by the
    # tile's own coordinates against the platforms (the jump
    # record's "platform" field is the DESTINATION platform, so
    # keying a source tile by it misclassifies wall sources as
    # ceiling tiles). A landing that is also a jump source is a
    # chain link (a designed transition), not a bug.
    def _classify_tile(x, y, z):
        for plat in md.dw["record"]["platforms"]:
            if plat["kind"] in (1, 2) and x == plat["x"] and \
                    plat["y"] <= y <= plat["y"] + plat["sy"] and \
                    plat["z"] <= z <= plat["z"] + plat["sz"]:
                return "wall", (y, z), plat
            if plat["kind"] in (0, 3) and y == plat["y"] and \
                    plat["x"] <= x <= plat["x"] + plat["sx"] and \
                    plat["z"] <= z <= plat["z"] + plat["sz"]:
                return dw_surface_name(plat), (x, z), plat
        return "floor", (x, z), None

    jump_src_by_surface = set()
    jump_land_by_surface = set()
    if md.dw:
        for j in md.dw["record"]["jumps"]:
            if j["platform"] != 65535 and j["platform"] < len(md.dw["record"]["platforms"]):
                pass  # the platform field is the destination; classify by coords
            for dy in range(j["sy"] + 1):
                for dz in range(j["sz"] + 1):
                    for dx in range(j["sx"] + 1):
                        surf, key, _pl = _classify_tile(j["x"] + dx, j["y"] + dy, j["z"] + dz)
                        jump_src_by_surface.add((surf, key))
                        lsurf, lkey, _pl2 = _classify_tile(
                            j["x"] + j["dx"] + dx, j["y"] + j["dy"] + dy, j["z"] + j["dz"] + dz)
                        jump_land_by_surface.add((lsurf, lkey))
    # Tiles inside a DW platform footprint are checked as that
    # surface, not as ordinary floor (their perms are blocked there
    # because the ground is not the playable surface).
    dw_footprint = set()
    if md.dw:
        for plat in md.dw["record"]["platforms"]:
            if plat["kind"] == 3 or plat["kind"] == 0:
                for x in range(plat["x"], plat["x"] + plat["sx"] + 1):
                    for z in range(plat["z"], plat["z"] + plat["sz"] + 1):
                        dw_footprint.add((x, z))
            elif plat["kind"] in (1, 2):
                for z in range(plat["z"], plat["z"] + plat["sz"] + 1):
                    dw_footprint.add((plat["x"], z))

    # Scope for floor tiles: every tile of the map's chunks, except
    # on DW maps (see below). A reachability scope was tried and
    # rejected: it hides the interior of a wrongly blocked region
    # (the Route 214 bug is a large blocked floor area whose
    # interior tiles are not adjacent to any walkable tile).
    scope = set(md.tiles)
    if md.dw:
        # DW floor scope: chunks holding a floor-level puzzle feature
        # -- the entry, a floor jump, a coord/warp/object, or a ghost
        # prop at floor height. The rest of a DW matrix is leftover
        # stock Distortion World floor (the B4F south quadrants):
        # stock-drawn, stock-blocked, and not part of this map's
        # puzzle. A wrongly blocked floor area inside the puzzle is
        # still in scope (its chunk holds the entry / jumps).
        feat_chunks = set()
        for (x, z) in (DW_ENTRY,):
            if (x, z) in md.tiles:
                feat_chunks.add(md.tiles[(x, z)][0])
        for j in md.dw["record"]["jumps"]:
            if (j["x"], j["z"]) in md.tiles:
                feat_chunks.add(md.tiles[(j["x"], j["z"])][0])
        for t in list(warps) + list(coords) + list(objects):
            if t in md.tiles:
                feat_chunks.add(md.tiles[t][0])
        for pr in md.dw["record"]["ghost"]["props"]:
            if pr["y"] <= 1 and (pr["x"], pr["z"]) in md.tiles:
                feat_chunks.add(md.tiles[(pr["x"], pr["z"])][0])
        scoped = {t for t in md.tiles if md.tiles[t][0] in feat_chunks}
        if len(scoped) >= 0.1 * len(md.tiles):
            scope = scoped
    if region is not None:
        x0, z0, x1, z1 = region
        scope = {t for t in scope if x0 <= t[0] <= x1 and z0 <= t[1] <= z1}

    mismatches = []
    allowlisted = []
    explained = 0
    counts = collections.Counter()

    def record(entry, allow_key):
        # allow_key is (map, surface, class, x, y, z); the allowlist
        # is keyed by that plus severity, with a severity-less entry
        # matching any severity (an entry WITH severity only matches
        # that severity, so a HIGH<->MEDIUM change is not silenced).
        for key in (allow_key + (entry["severity"],), allow_key + (None,)):
            if key in allowlist:
                entry["allowlisted"] = allowlist[key]
                allowlisted.append(entry)
                return
        mismatches.append(entry)
        counts[(entry["class"], entry["severity"])] += 1

    def allow_key_for(m, surface, cls, x, z, y=None):
        return (m, surface, cls, x, y, z)

    # ---- floor tiles ----------------------------------------------------
    # Phase 1: classify every scoped tile once.
    tiles_data = []
    for (x, z) in sorted(scope):
        if (x, z) in dw_footprint:
            continue
        if any((x + dx, z + dz) not in md.tiles
               for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            explained += 1
            continue
        chunk, lx, lz = md.tiles[(x, z)]
        raw = tree.chunk_perm(chunk)[lz][lx]
        coll, beh_name = classify_collision(raw, names)
        drawn, dev, centred, from_prop = md.drawn_floor(x, z)
        ghosts = ghost_by_tile.get(("floor", (x, z)), [])
        tiles_data.append({"x": x, "z": z, "raw": raw, "coll": coll,
                           "beh": beh_name, "drawn": drawn, "dev": dev,
                           "centred": centred, "from_prop": from_prop,
                           "ghosts": ghosts})
    # Phase 2: the drawn bounding box (of anything drawn, expanded
    # by one tile) bounds the invisible-floor checks: padding
    # outside an interior model is void + walkable in the perms,
    # but it was never a room the player can see. Drawn-floor +
    # blocked is still checked globally.
    drawn_tiles = [t for t in tiles_data if t["drawn"] != "void"]
    if drawn_tiles:
        bx0 = min(t["x"] for t in drawn_tiles) - 1
        bx1 = max(t["x"] for t in drawn_tiles) + 1
        bz0 = min(t["z"] for t in drawn_tiles) - 1
        bz1 = max(t["z"] for t in drawn_tiles) + 1
    else:
        bx0, bx1, bz0, bz1 = -10 ** 9, 10 ** 9, -10 ** 9, 10 ** 9
    for t in tiles_data:
        x, z, raw = t["x"], t["z"], t["raw"]
        coll, beh_name = t["coll"], t["beh"]
        drawn, dev = t["drawn"], t["dev"]
        centred, from_prop = t["centred"], t["from_prop"]
        ghosts = t["ghosts"]
        visible = [g for g in ghosts if g[1]]
        hidden = [g for g in ghosts if not g[1]]
        ev = "%s; collision 0x%04x (%s, beh %s)" % (dev, raw, coll, beh_name)
        if visible:
            ev += "; ghost props kinds %s" % ([g[0] for g in visible],)
        if hidden:
            ev += "; ghost props hidden at load kinds %s" % ([g[0] for g in hidden],)
        if (x, z) in objects:
            # An object tile is explained whatever its perms say:
            # MapObjects block movement through the object system,
            # so the permissions grid need not (and often does not)
            # mark the tile blocked. Only the base tile counts:
            # the object blocks the tile it stands on, not every
            # tile of its movement range.
            ev += "; object %s" % (objects[(x, z)].get("id"),)
            explained += 1
            continue
        # Exemptions are class-specific: a warp / coord trigger /
        # jump source only explains the pair it actually is.
        if (x, z) in jump_tiles and drawn == "floor" and coll == "blocked":
            # A jump source is plain blocked by design (a jump
            # ignores the landing/source block bit), drawn as floor.
            explained += 1
            continue
        if (x, z) in warps and drawn in ("void", "tall") and coll == "walkable":
            # A warp tile in a wall / tall structure (a door).
            explained += 1
            continue
        if (x, z) in coords and drawn == "void" and coll == "walkable":
            # A coord trigger over open void (a fall trigger).
            explained += 1
            continue
        if visible:
            if GHOST_BLOCK_KIND in [g[0] for g in visible] and coll == "walkable":
                record({"map": header, "x": x, "z": z, "surface": "floor",
                        "class": "LOOKS_BLOCKED_BUT_WALKABLE", "severity": "HIGH",
                        "drawn": "tall", "collision": coll,
                        "behaviour": beh_name,
                        "evidence": ev + "; stone-block ghost prop on a walkable tile"},
                       allow_key_for(header, "floor", "LOOKS_BLOCKED_BUT_WALKABLE", x, z))
            # A visible ghost prop explains a blocked tile
            # (alcove, pad, ...).
            continue
        in_bbox = bx0 <= x <= bx1 and bz0 <= z <= bz1
        if drawn == "floor" and coll == "blocked":
            record({"map": header, "x": x, "z": z, "surface": "floor",
                    "class": "LOOKS_WALKABLE_BUT_BLOCKED", "severity": "HIGH",
                    "drawn": drawn, "collision": coll,
                    "behaviour": beh_name, "evidence": ev},
                   allow_key_for(header, "floor", "LOOKS_WALKABLE_BUT_BLOCKED", x, z))
        elif drawn == "floor" and coll == "water":
            record({"map": header, "x": x, "z": z, "surface": "floor",
                    "class": "WATER_MISMATCH", "severity": "HIGH",
                    "drawn": drawn, "collision": coll,
                    "behaviour": beh_name,
                    "evidence": ev + "; drawn floor, walkable water collision"},
                   allow_key_for(header, "floor", "WATER_MISMATCH", x, z))
        elif drawn == "water" and coll == "walkable":
            record({"map": header, "x": x, "z": z, "surface": "floor",
                    "class": "WATER_MISMATCH", "severity": "HIGH",
                    "drawn": drawn, "collision": coll,
                    "behaviour": beh_name,
                    "evidence": ev + "; drawn water, walkable non-water collision"},
                   allow_key_for(header, "floor", "WATER_MISMATCH", x, z))
        elif drawn == "tall" and coll == "walkable" and centred and in_bbox:
            record({"map": header, "x": x, "z": z, "surface": "floor",
                    "class": "LOOKS_BLOCKED_BUT_WALKABLE", "severity": "HIGH",
                    "drawn": drawn, "collision": coll,
                    "behaviour": beh_name,
                    "evidence": ev + "; tall obstacle centred on the tile, collision walkable"},
                   allow_key_for(header, "floor", "LOOKS_BLOCKED_BUT_WALKABLE", x, z))
        elif drawn == "void" and coll == "walkable" and in_bbox:
            record({"map": header, "x": x, "z": z, "surface": "floor",
                    "class": "LOOKS_BLOCKED_BUT_WALKABLE", "severity": "HIGH",
                    "drawn": drawn, "collision": coll,
                    "behaviour": beh_name,
                    "evidence": ev + "; nothing drawn, collision walkable"},
                   allow_key_for(header, "floor", "LOOKS_BLOCKED_BUT_WALKABLE", x, z))
        elif drawn == "tall" and coll == "water" and not from_prop:
            # A tall obstacle over walkable water. Tall from an
            # approximate prop footprint never flags (it is
            # explanatory-only by construction).
            record({"map": header, "x": x, "z": z, "surface": "floor",
                    "class": "WATER_MISMATCH", "severity": "MEDIUM",
                    "drawn": drawn, "collision": coll,
                    "behaviour": beh_name,
                    "evidence": ev + "; tall obstacle drawn, walkable water collision"},
                   allow_key_for(header, "floor", "WATER_MISMATCH", x, z))

    # ---- DW wall / ceiling tiles -----------------------------------------
    if md.dw:
        for plat in md.dw["record"]["platforms"]:
            surf = dw_surface_name(plat)
            for key, _label in dw_platform_tiles(plat):
                # Region filter: (x, z) for ceiling, (wall x, z) for walls.
                if region is not None:
                    if surf == "ceiling":
                        if not (region[0] <= key[0] <= region[2]
                                and region[1] <= key[1] <= region[3]):
                            continue
                    else:
                        if not (region[0] <= plat["x"] <= region[2]
                                and region[1] <= key[1] <= region[3]):
                            continue
                raw = dw_attr_collision(md, plat, key)
                if raw is None:
                    continue
                coll, beh_name = classify_collision(raw, names)
                ghosts = ghost_by_tile.get((surf, key), [])
                visible = [g for g in ghosts if g[1]]
                hidden = [g for g in ghosts if not g[1]]
                if surf in ("ceiling", "floor"):
                    # A floor platform is a floating platform whose
                    # collision is the attr grid, not the perms.
                    drawn, dev = md.drawn_dw_surface(plat, key[0], key[1])
                    tx, tz = key
                else:
                    drawn, dev = md.drawn_dw_wall(plat, key[0], key[1])
                    tx, tz = plat["x"], key[1]
                ev = "%s; collision 0x%04x (%s, beh %s)" % (dev, raw, coll, beh_name)
                if visible:
                    ev += "; ghost props kinds %s" % ([g[0] for g in visible],)
                if hidden:
                    ev += "; ghost props hidden at load kinds %s" % ([g[0] for g in hidden],)
                # A jump source on a DW surface is a designed
                # transition: its tile belongs to the jump system,
                # not to the walkable surface (a wall source is
                # void+walkable by design, a ceiling source is
                # floor+blocked). This is the DW-surface analogue
                # of the floor loop's narrower rule, where the
                # collision is the attr grid rather than perms.
                surf_y = plat["y"] if surf in ("ceiling", "floor") else key[0]
                on_jump = any(j["x"] <= tx <= j["x"] + j["sx"]
                              and j["y"] <= surf_y <= j["y"] + j["sy"]
                              and j["z"] <= tz <= j["z"] + j["sz"]
                              for j in md.dw["record"]["jumps"])
                if visible:
                    if GHOST_BLOCK_KIND in [g[0] for g in visible] and coll == "walkable":
                        record({"map": header, "x": tx, "y": key[0] if surf == "wall" else None,
                                "z": tz, "surface": surf,
                                "class": "LOOKS_BLOCKED_BUT_WALKABLE", "severity": "HIGH",
                                "drawn": "tall", "collision": coll,
                                "behaviour": beh_name,
                                "evidence": ev + "; stone-block ghost prop on a walkable tile"},
                               allow_key_for(header, surf, "LOOKS_BLOCKED_BUT_WALKABLE", tx, tz,
                                             y=key[0] if surf == "wall" else None))
                    continue
                if on_jump:
                    explained += 1
                    continue
                if surf == "wall":
                    # A wall face is not walkable-looking floor: blocked
                    # wall tiles are the wall's edges/corners. The
                    # checkable wall bug is an undrawn walkable tile
                    # (an invisible wall path).
                    if drawn == "void" and coll == "walkable":
                        # A void tile next to a drawn wall tile is an
                        # edge/corner tile of the wall path (the wall
                        # face clips its corner): MEDIUM, not HIGH.
                        edge = any(
                            md.drawn_dw_wall(plat, key[0] + dy, key[1] + dz)[0] == "floor"
                            for dy, dz in ((1, 0), (-1, 0), (0, 1), (0, -1),
                                           (1, 1), (1, -1), (-1, 1), (-1, -1))
                            if plat["y"] <= key[0] + dy <= plat["y"] + plat["sy"]
                            and plat["z"] <= key[1] + dz <= plat["z"] + plat["sz"])
                        if edge:
                            record({"map": header, "x": tx, "y": key[0], "z": tz, "surface": surf,
                                    "class": "LOOKS_BLOCKED_BUT_WALKABLE", "severity": "MEDIUM",
                                    "drawn": drawn, "collision": coll,
                                    "behaviour": beh_name,
                                    "evidence": ev + "; undrawn walkable wall tile adjacent to drawn wall (edge/corner)"},
                                   allow_key_for(header, surf, "LOOKS_BLOCKED_BUT_WALKABLE", tx, tz,
                                                 y=key[0]))
                        elif key[0] == plat["y"] + plat["sy"]:
                            record({"map": header, "x": tx, "y": key[0], "z": tz, "surface": surf,
                                    "class": "LOOKS_BLOCKED_BUT_WALKABLE", "severity": "MEDIUM",
                                    "drawn": drawn, "collision": coll,
                                    "behaviour": beh_name,
                                    "evidence": ev + "; undrawn walkable wall tile on the top row (transition)"},
                                   allow_key_for(header, surf, "LOOKS_BLOCKED_BUT_WALKABLE", tx, tz,
                                                 y=key[0]))
                        else:
                            record({"map": header, "x": tx, "y": key[0], "z": tz, "surface": surf,
                                    "class": "LOOKS_BLOCKED_BUT_WALKABLE", "severity": "HIGH",
                                    "drawn": drawn, "collision": coll,
                                    "behaviour": beh_name,
                                    "evidence": ev + "; nothing drawn on a walkable wall tile"},
                                   allow_key_for(header, surf, "LOOKS_BLOCKED_BUT_WALKABLE", tx, tz,
                                                 y=key[0]))
                    elif drawn == "water" and coll == "walkable":
                        record({"map": header, "x": tx, "y": key[0], "z": tz, "surface": surf,
                                "class": "WATER_MISMATCH", "severity": "HIGH",
                                "drawn": drawn, "collision": coll,
                                "behaviour": beh_name, "evidence": ev},
                               allow_key_for(header, surf, "WATER_MISMATCH", tx, tz, y=key[0]))
                    continue
                # Ceiling / DW floor platform.
                if drawn == "floor" and coll == "blocked":
                    record({"map": header, "x": tx, "z": tz, "surface": surf,
                            "class": "LOOKS_WALKABLE_BUT_BLOCKED", "severity": "HIGH",
                            "drawn": drawn, "collision": coll,
                            "behaviour": beh_name,
                            "evidence": ev + "; drawn platform slab, collision blocked, no ghost prop"},
                           allow_key_for(header, surf, "LOOKS_WALKABLE_BUT_BLOCKED", tx, tz))
                elif drawn == "water" and coll == "walkable":
                    record({"map": header, "x": tx, "z": tz, "surface": surf,
                            "class": "WATER_MISMATCH", "severity": "HIGH",
                            "drawn": drawn, "collision": coll,
                            "behaviour": beh_name,
                            "evidence": ev + "; drawn platform water, collision walkable"},
                           allow_key_for(header, surf, "WATER_MISMATCH", tx, tz))
                elif drawn == "void" and coll == "walkable":
                    record({"map": header, "x": tx, "z": tz, "surface": surf,
                            "class": "LOOKS_BLOCKED_BUT_WALKABLE", "severity": "HIGH",
                            "drawn": drawn, "collision": coll,
                            "behaviour": beh_name,
                            "evidence": ev + "; nothing drawn on a walkable platform tile"},
                           allow_key_for(header, surf, "LOOKS_BLOCKED_BUT_WALKABLE", tx, tz))

    # ---- DW jump landings -------------------------------------------------
    # Jump destinations must be drawn on their surface: a jump ignores
    # the landing tile's block bit, so the ordinary checks cannot
    # catch a landing on an undrawn tile (the fix2-lost rule: "no jump
    # tile may land on an undrawn tile"). The landing's surface is
    # its own tile surface, not the jump record's destination
    # platform (which can be a different surface for chain jumps).
    if md.dw:
        seen_landings = set()
        for ji, j in enumerate(md.dw["record"]["jumps"]):
            for dy in range(j["sy"] + 1):
                for dz in range(j["sz"] + 1):
                    for dx in range(j["sx"] + 1):
                        lx = j["x"] + j["dx"] + dx
                        ly = j["y"] + j["dy"] + dy
                        lz = j["z"] + j["dz"] + dz
                        surf, lkey, plat = _classify_tile(lx, ly, lz)
                        if (surf, lkey) in seen_landings:
                            continue
                        seen_landings.add((surf, lkey))
                        # A wall-surface landing that is also a jump
                        # source is a chain link; drawn_dw_wall's void
                        # is not reliable evidence there (face offset).
                        if surf == "wall" and (surf, lkey) in jump_src_by_surface:
                            continue
                        if surf == "wall":
                            drawn, dev = md.drawn_dw_wall(plat, lkey[0], lkey[1])
                            tx, tz, ty = plat["x"], lkey[1], lkey[0]
                            raw = dw_attr_collision(md, plat, lkey)
                        elif plat is not None:
                            drawn, dev = md.drawn_dw_surface(plat, lkey[0], lkey[1])
                            tx, tz, ty = lkey[0], lkey[1], plat["y"]
                            raw = dw_attr_collision(md, plat, lkey)
                        else:
                            if (lx, lz) not in md.tiles:
                                continue
                            drawn, dev, _centred, _fp = md.drawn_floor(lx, lz)
                            tx, tz, ty = lx, lz, None
                            chunk, llx, llz = md.tiles[(lx, lz)]
                            raw = tree.chunk_perm(chunk)[llz][llx]
                        coll = classify_collision(raw, names)[0] if raw is not None else "blocked"
                        if drawn == "void":
                            record({"map": header, "x": tx, "y": ty, "z": tz, "surface": surf,
                                    "class": "JUMP_LANDING_UNDRAWN", "severity": "HIGH",
                                    "drawn": drawn, "collision": coll,
                                    "behaviour": "n/a (jump ignores the block bit)",
                                    "evidence": "%s; jump %d from (%s, %s, %s) -> "
                                    "landing (%s, %s, %s) on %s is undrawn" % (
                                        dev, ji, j["x"], j["y"], j["z"], lx, ly, lz, surf)},
                                   allow_key_for(header, surf, "JUMP_LANDING_UNDRAWN", tx, tz, y=ty))
                        elif drawn == "tall":
                            record({"map": header, "x": tx, "y": ty, "z": tz, "surface": surf,
                                    "class": "JUMP_LANDING_OBSTRUCTED", "severity": "HIGH",
                                    "drawn": drawn, "collision": coll,
                                    "behaviour": "n/a (jump ignores the block bit)",
                                    "evidence": "%s; jump %d from (%s, %s, %s) -> "
                                    "landing (%s, %s, %s) on %s is on a tall obstacle" % (
                                        dev, ji, j["x"], j["y"], j["z"], lx, ly, lz, surf)},
                                   allow_key_for(header, surf, "JUMP_LANDING_OBSTRUCTED", tx, tz, y=ty))

    out = {"map": header, "matrix": matrix_id,
           "tiles_checked": len(scope),
           "counts": {("%s|%s" % k): v for k, v in sorted(counts.items())},
           "mismatches": mismatches, "allowlisted": allowlisted,
           "explained_tiles": explained, "_md": md, "_scope": scope,
           "dw_error": getattr(md, "dw_error", None)}
    return out


# ---------------------------------------------------------------- overlays
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "01010", "00100", "00100", "00100", "01010", "10001"),
    "Y": ("10001", "01010", "00100", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10001", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "10001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    ":": ("00000", "00100", "00000", "00000", "00000", "00100", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00100", "00100"),
    ",": ("00000", "00000", "00000", "00000", "00100", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
}
# Colours: (tile colour, meaning)
LEGEND = [
    ((60, 180, 60), "drawn floor, walkable"),
    ((220, 30, 30), "HIGH looks walkable but blocked"),
    ((240, 220, 0), "HIGH looks blocked but walkable"),
    ((0, 140, 220), "water"),
    ((220, 80, 200), "HIGH water mismatch"),
    ((230, 130, 30), "tall obstacle, blocked"),
    ((160, 160, 160), "raised / stairs"),
    ((30, 30, 90), "void, blocked"),
    ((255, 255, 255), "not checked"),
]


def _draw_text(pixels, x, y, text, colour=(0, 0, 0), scale=1):
    for ch in text.upper():
        glyph = FONT.get(ch, FONT[" "])
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            px, py = x + col * scale + dx, y + row * scale + dy
                            if 0 <= py < len(pixels) and 0 <= px < len(pixels[0]):
                                pixels[py][px] = colour + (255,)
        x += 6 * scale
    return x


def write_overlay(png_mod, path, title, cell_grid, legend_items):
    """cell_grid: rows of (colour, label) cells. Writes a PNG with a legend."""
    h = len(cell_grid)
    w = len(cell_grid[0]) if h else 1
    cell = max(1, min(16, 640 // max(w, h, 1)))
    img_w = max(w * cell, 320)
    img_h = h * cell + 20 + len(legend_items) * 16
    pixels = [[(255, 255, 255, 255)] * img_w for _ in range(img_h)]
    for z, row in enumerate(cell_grid):
        for x, col in enumerate(row):
            for dy in range(cell):
                for dx in range(cell):
                    pixels[z * cell + dy][x * cell + dx] = col + (255,)
            if cell >= 3:
                for i in range(cell):
                    pixels[z * cell][x * cell + i] = (200, 200, 200, 255)
                    pixels[z * cell + i][x * cell] = (200, 200, 200, 255)
    _draw_text(pixels, 6, h * cell + 6, title, (0, 0, 0), 1)
    for i, (col, label) in enumerate(legend_items):
        ly = h * cell + 20 + i * 16
        for dy in range(10):
            for dx in range(14):
                pixels[ly + dy][6 + dx] = col + (255,)
        _draw_text(pixels, 26, ly + 1, label, (0, 0, 0), 1)
    png_mod.write_rgba(path, img_w, img_h, pixels)


def render_map_overlays(tree, result, out_dir, region):
    md = None
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, result["map"].replace("MAP_HEADER_", ""))
    # Floor overlay: rebuild the drawn/collision picture cheaply from
    # the report: mismatches are coloured, everything else by drawn.
    # Full re-derivation needs MapData; analyse_map already computed it
    # -- cache it on the result for the overlay step.
    data = result.get("_md")
    if data is None:
        return []
    md = data
    names = tree.names
    # The analyzer's exact scope (result["_scope"]): the renderer must
    # not recompute a narrower one (it used to, and omitted reported
    # tiles from the PNG). Fall back to all tiles for old results.
    scope = result.get("_scope")
    tiles = sorted(scope) if scope is not None else sorted(
        t for t in md.tiles if region is None or
        (region[0] <= t[0] <= region[2] and region[1] <= t[1] <= region[3]))
    if not tiles:
        return []
    x0, x1 = min(t[0] for t in tiles), max(t[0] for t in tiles)
    z0, z1 = min(t[1] for t in tiles), max(t[1] for t in tiles)
    by_tile = {(m["x"], m["z"]): m for m in result["mismatches"] if m["surface"] == "floor"}
    in_scope = scope if scope is not None else set(md.tiles)
    grid = []
    for z in range(z0, z1 + 1):
        row = []
        for x in range(x0, x1 + 1):
            if (x, z) not in md.tiles or (x, z) not in in_scope:
                row.append((255, 255, 255))
                continue
            chunk, lx, lz = md.tiles[(x, z)]
            raw = tree.chunk_perm(chunk)[lz][lx]
            coll, _ = classify_collision(raw, names)
            drawn, _, _, _ = md.drawn_floor(x, z)
            m = by_tile.get((x, z))
            if m is not None:
                if m["class"] == "LOOKS_WALKABLE_BUT_BLOCKED":
                    row.append((220, 30, 30))
                elif m["class"] == "WATER_MISMATCH":
                    row.append((220, 80, 200))
                elif m["class"] == "LOOKS_BLOCKED_BUT_WALKABLE":
                    row.append((240, 220, 0))
                else:
                    row.append((255, 180, 0))
            elif drawn == "floor" and coll == "walkable":
                row.append((60, 180, 60))
            elif drawn == "water":
                row.append((0, 140, 220))
            elif drawn == "tall":
                row.append((230, 130, 30))
            elif drawn in ("raised", "stairs"):
                row.append((160, 160, 160))
            elif coll == "blocked":
                row.append((30, 30, 90))
            else:
                row.append((255, 255, 255))
        grid.append(row)
    out = []
    write_overlay(tree.png, base + ".png",
                  "%s floor x[%d,%d] z[%d,%d]" % (result["map"], x0, x1, z0, z1),
                  grid, LEGEND)
    out.append(base + ".png")
    # DW surfaces.
    if md.dw:
        for plat in md.dw["record"]["platforms"]:
            surf = dw_surface_name(plat)
            if surf == "ceiling":
                keys = [(x, z) for x in range(plat["x"], plat["x"] + plat["sx"] + 1)
                        for z in range(plat["z"], plat["z"] + plat["sz"] + 1)]
                xs = [k[0] for k in keys]
                zs = [k[1] for k in keys]
                by_tile_s = {(m["x"], m["z"]): m for m in result["mismatches"] if m["surface"] == surf}
                grid = []
                for z in range(min(zs), max(zs) + 1):
                    row = []
                    for x in range(min(xs), max(xs) + 1):
                        m = by_tile_s.get((x, z))
                        raw = dw_attr_collision(md, plat, (x, z))
                        coll = classify_collision(raw, names)[0] if raw is not None else "blocked"
                        drawn, _ = md.drawn_dw_surface(plat, x, z)
                        if m is not None:
                            row.append((220, 30, 30) if m["class"] == "LOOKS_WALKABLE_BUT_BLOCKED"
                                       else (240, 220, 0) if m["class"] == "LOOKS_BLOCKED_BUT_WALKABLE"
                                       else (220, 80, 200))
                        elif drawn == "floor" and coll == "walkable":
                            row.append((60, 180, 60))
                        elif drawn == "water":
                            row.append((0, 140, 220))
                        elif drawn == "floor" and coll == "blocked":
                            row.append((230, 130, 30))
                        elif coll == "blocked":
                            row.append((30, 30, 90))
                        else:
                            row.append((255, 255, 255))
                    grid.append(row)
                write_overlay(tree.png, base + "_ceiling.png",
                              "%s ceiling" % result["map"], grid, LEGEND)
                out.append(base + "_ceiling.png")
            else:
                keys = [(y, z) for y in range(plat["y"], plat["y"] + plat["sy"] + 1)
                        for z in range(plat["z"], plat["z"] + plat["sz"] + 1)]
                by_tile_s = {(m["z"],): m for m in []}  # wall tiles keyed below by (y,z)
                by_w = {}
                for m in result["mismatches"]:
                    if m["surface"] == "wall":
                        by_w[(m.get("y", None), m["z"])] = m
                grid = []
                for y in range(plat["y"] + plat["sy"], plat["y"] - 1, -1):
                    row = []
                    for z in range(plat["z"], plat["z"] + plat["sz"] + 1):
                        raw = dw_attr_collision(md, plat, (y, z))
                        coll = classify_collision(raw, names)[0] if raw is not None else "blocked"
                        drawn, _ = md.drawn_dw_wall(plat, y, z)
                        m = next((mm for mm in result["mismatches"]
                                  if mm["surface"] == "wall" and mm["z"] == z
                                  and mm.get("y") == y), None)
                        if m is not None:
                            row.append((240, 220, 0) if m["class"] == "LOOKS_BLOCKED_BUT_WALKABLE" else (220, 80, 200))
                        elif drawn == "floor" and coll == "walkable":
                            row.append((60, 180, 60))
                        elif coll == "blocked":
                            row.append((30, 30, 90))
                        else:
                            row.append((255, 255, 255))
                    grid.append(row)
                write_overlay(tree.png, base + "_wall.png",
                              "%s wall (y down, z across)" % result["map"], grid, LEGEND)
                out.append(base + "_wall.png")
    return out


# ---------------------------------------------------------------- allowlist
def load_allowlist(path):
    out = {}
    if path and os.path.exists(path):
        try:
            data = json.load(open(path))
        except (OSError, ValueError):
            return out
        for e in data.get("entries", []):
            # y and severity are optional: an entry without severity
            # matches any severity; one with severity matches only
            # that severity (so a HIGH<->MEDIUM change is not
            # silenced). Wall entries must carry y.
            key = (e.get("map"), e.get("surface", "floor"), e.get("class"),
                   e.get("x"), e.get("y"), e.get("z"), e.get("severity"))
            out[key] = e.get("reason", "")
    return out


# ---------------------------------------------------------------- selection
def select_maps(tree, args):
    hdrs = tree.headers()
    if args.all_dw:
        # The custom DW maps of this hack (the QA gate's scope).
        # The stock DISTORTION_WORLD_* floors are intentionally not
        # included: their floor platforms use stock DW mechanics the
        # tool does not model (see tools/qa/README.md, Known limits).
        return sorted(h for h in hdrs
                      if h.startswith("MAP_HEADER_DW_")
                      or h == "MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS")
    if args.all:
        return sorted(h for h in hdrs
                      if h not in ("MAP_HEADER_EVERYWHERE", "MAP_HEADER_NOTHING"))
    if args.map is not None:
        out = []
        for arg in args.map:
            if arg.isdigit() or arg.startswith("map_matrix_"):
                mid = int(arg.replace("map_matrix_", ""))
                maps = [h for h, (m, _e) in hdrs.items() if m == mid]
                if not maps:
                    raise SystemExit("no map header with matrix %d" % mid)
                out += maps
            else:
                name = arg if arg.startswith("MAP_HEADER_") else "MAP_HEADER_" + arg
                if name not in hdrs:
                    raise SystemExit("unknown map header %s" % name)
                out.append(name)
        return sorted(set(out))
    raise SystemExit("give --map, --all-dw or --all")


def _ident(m):
    # Full mismatch identity: map, coords (wall y included),
    # surface, class, severity. Two map entries that differ only in
    # severity or wall height are different findings.
    return (m["map"], m.get("x"), m.get("y"), m["z"], m["surface"],
            m["class"], m["severity"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--map", dest="map", default=None, action="append",
                    help="MAP_HEADER_* name (prefix optional) or matrix id (repeatable)")
    ap.add_argument("--all-dw", action="store_true", help="every DW map")
    ap.add_argument("--all", action="store_true", help="every map with a matrix")
    ap.add_argument("--region", default=None,
                    help="x0,z0,x1,z1 tile region to check")
    ap.add_argument("--rom-tree", default=DEFAULT_ROOT,
                    help="repo checkout to check (default: this repo)")
    ap.add_argument("--diff", default=None,
                    help="compare against another checkout at this path")
    ap.add_argument("--baseline", default=None,
                    help="walkcheck.json from a reviewed run: the gate "
                    "fails only on NEW HIGH findings vs that baseline")
    ap.add_argument("--out-dir", default="walkcheck_out",
                    help="where to write the JSON report and overlays")
    ap.add_argument("--allowlist", default=None,
                    help="allowlist JSON (default: tools/qa/walkcheck_allow.json in --rom-tree)")
    ap.add_argument("--no-png", action="store_true", help="skip overlay PNGs")
    args = ap.parse_args(argv)
    region = None
    if args.region:
        try:
            region = tuple(int(v) for v in args.region.split(","))
            assert len(region) == 4
        except (ValueError, AssertionError):
            raise SystemExit("--region must be x0,z0,x1,z1")
    tree = Tree(args.rom_tree)
    allow_path = args.allowlist or os.path.join(
        args.rom_tree, "tools", "qa", "walkcheck_allow.json")
    allowlist = load_allowlist(allow_path)
    selected = select_maps(tree, args)
    report = {"tool": "tools/qa/walkcheck.py", "rom_tree": tree.root,
              "maps": [], "diff": None}
    any_high = False
    errors = []
    for header in selected:
        matrix_id = tree.headers()[header][0]
        try:
            result = analyse_map(tree, header, matrix_id, region, allowlist)
        except FileNotFoundError as e:
            msg = "%s: missing file %s" % (header, e.filename or e)
            print("%s: SKIP (%s)" % (header, msg))
            errors.append(msg)
            continue
        except KeyError as e:
            msg = "%s: missing data %s" % (header, e)
            print("%s: SKIP (%s)" % (header, msg))
            errors.append(msg)
            continue
        if result.get("dw_error"):
            # A failed DW parse is a hard error, not a silent skip:
            # the map would otherwise leave the gate unchecked.
            msg = "%s: DW parse failed: %s" % (header, result["dw_error"])
            print(msg)
            errors.append(msg)
        counts = collections.Counter()
        for m in result["mismatches"]:
            counts[(m["class"], m["severity"])] += 1
        high = sum(v for (c, s), v in counts.items() if s == "HIGH")
        any_high |= high > 0
        line = ("%s: %d tiles checked, %d mismatches "
                "(%d HIGH, %d MEDIUM, %d LOW), %d allowlisted, %d explained" % (
                    header, result["tiles_checked"], len(result["mismatches"]),
                    sum(v for (c, s), v in counts.items() if s == "HIGH"),
                    sum(v for (c, s), v in counts.items() if s == "MEDIUM"),
                    sum(v for (c, s), v in counts.items() if s == "LOW"),
                    len(result["allowlisted"]), result["explained_tiles"]))
        for (c, s), v in sorted(counts.items()):
            line += "; %s %s=%d" % (c, s, v)
        print(line, flush=True)
        # Render now and strip the geometry: keeping every MapData
        # alive until the end of a --all run peaked at 1.55 GB RSS.
        if not args.no_png:
            try:
                render_map_overlays(tree, result, args.out_dir, region)
            except Exception as e:
                print("%s: overlay failed: %s" % (result["map"], e))
        result.pop("_md", None)
        result.pop("_scope", None)
        report["maps"].append(result)
    # Diff against another tree, same selection.
    if args.diff:
        other = Tree(args.diff)
        mine = {_ident(m) for r in report["maps"] for m in r["mismatches"]}
        theirs = set()
        other_maps = []
        for header in selected:
            matrix_id = other.headers()[header][0]
            try:
                res = analyse_map(other, header, matrix_id, region, allowlist)
            except (FileNotFoundError, KeyError):
                continue
            res.pop("_md", None)
            res.pop("_scope", None)
            other_maps.append(res)
            for m in res["mismatches"]:
                theirs.add(_ident(m))
        report["diff"] = {
            "other_tree": other.root,
            "added_in_this_tree": sorted(mine - theirs),
            "fixed_in_this_tree": sorted(theirs - mine),
            "other_maps": other_maps,
        }
        print("DIFF vs %s: +%d added, -%d fixed" % (
            other.root, len(mine - theirs), len(theirs - mine)))
    # Baseline gating: with --baseline, only HIGH findings that are
    # not in the reviewed baseline fail the gate. Without it, any
    # HIGH finding fails.
    new_high = None
    if args.baseline:
        try:
            bdata = json.load(open(args.baseline))
        except (OSError, ValueError) as e:
            raise SystemExit("--baseline unreadable: %s" % e)
        base_high = {_ident(m) for r in bdata.get("maps", [])
                     for m in r.get("mismatches", [])
                     if m["severity"] == "HIGH"}
        cur_high = {_ident(m) for r in report["maps"]
                    for m in r["mismatches"] if m["severity"] == "HIGH"}
        new_high = sorted(cur_high - base_high)
        report["baseline"] = {"path": args.baseline,
                              "baseline_high": len(base_high),
                              "new_high": new_high}
        print("BASELINE %s: %d new HIGH vs %d baselined HIGH" % (
            args.baseline, len(new_high), len(base_high)))
    os.makedirs(args.out_dir, exist_ok=True)
    out_json = os.path.join(args.out_dir, "walkcheck.json")
    with open(out_json, "w") as f:
        json.dump(report, f, indent=1)
    print("wrote %s" % out_json)
    if errors:
        print("ERRORS: %d map(s) failed to parse; exiting 2" % len(errors))
        return 2
    if new_high is not None:
        return 1 if new_high else 0
    return 1 if any_high else 0


if __name__ == "__main__":
    sys.exit(main())
