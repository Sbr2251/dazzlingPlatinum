#!/usr/bin/env python3
"""Route 222 — Violet-Lit Coast art pass: surgical additions to map_data_149/150/151, map_texture_set_081
(textures.py) and lighting_set_009.

Usage (Python with NumPy; PIL only for --preview):
  ~/.venvs/desmume/bin/python tools/routes/r222/build_art.py                 dry run: build, budgets, every check
  ~/.venvs/desmume/bin/python tools/routes/r222/build_art.py --preview DIR   also DIR/view_*.png field-camera renders
                                                                              (day / dusk / night), DIR/top*.png, DIR/tex
  ~/.venvs/desmume/bin/python tools/routes/r222/build_art.py --write         write the three chunks, set 081 and
                                                                              lighting_set_009.json (refuses on FAIL)

Inputs (all from git at BASE_REV, the routes-wave2 contract commit, so reruns never feed back): the stock chunks
149/150/151, stock set 018 (textures.py appends to it), lighting_set_000 (schema and sun directions).

Method (tools/world_art/chunkedit.py, as the Solaceon wall): every stock shape and material is kept byte for byte,
so the beach, the animated sea, the houses, cliffs, trees, fences and both seams (Valor Lakefront x 736, Sunyshore
x 832) are untouched; the new geometry is appended as new materials + shapes. BDHC and props stay stock; the
permissions are stock except LAMP_BLOCKS (three grass-verge tiles in 149 that a lamp now stands on).

What it adds (docs/routes_wave2/PLAN.md section 3.4):
  * LAMPS: blacked-out coastal streetlamps (riveted iron plinth, slender post, collar, cage housing with cracked
    dark glass and a faint violet filament, iron roof rim and finial) on blocked tiles along the promenade: the sea-cliff rim and
    the dirt road in 149, the fenced stone promenade in 150 / 151. VIOLET_LAMPS: three lamps by the Sunyshore gate
    whose housings glow (unlit, baked violet) behind a translucent sparking halo card and a violet glow pool.
  * Caution tape along the promenade fences (TAPES) and dead beacon boxes (BEACONS) by the violet lamps.
  * The tide line: a violet-tinged foam lace draped over every sand -> sea edge (on the stock slope, following the
    terrain), washed-up shard / shell scatter on the sand behind it, kelp tangles, kelp strands, driftwood and
    shard fans as flat decals (hash-placed, never solid on a walkable tile), and glowing violet rift-crystal clusters
    wedged against the beach boulders and crowning offshore sea rocks (blocked tiles only).

Lighting: lit materials follow lighting_set_009 (LIGHT_CURVE: cool violet daylight, rose-indigo shadows, a violet
dusk and a glowing indigo night); the violet lamp housings, halos, glow pools and crystals are unlit with baked
vertex colours, so they glow at night.

Checks (--write refuses on any FAIL): per chunk model <= 0xF000, BDHC <= 0x9000, NSBMD parse -> rebuild
byte-identical, untouched stock shapes + all stock materials byte-identical, every material's texture / palette in
set 081 with matching size, props and BDHC identical to stock, permissions = stock + LAMP_BLOCKS; nothing solid low
over a walkable (land or water) tile; land reachability (BFS with ledges) only loses LAMP_BLOCKS and the stranded
Pokemon tiles and every event stays reachable; events (stranded Pokemon on tide-line sand, lamp sign readable);
set 081 round trip + VRAM; lighting schema.
"""
import json
import math
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
sys.path.insert(0, os.path.join(ROOT, "tools", "world_art"))
sys.path.insert(0, HERE)

import chunkedit as C  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402
import textures as TX  # noqa: E402

BASE_REV = TX.BASE_REV
OUT_MAP_DIR = "res/field/mapmodels/data"
EVENTS_REL = "res/field/maps/route_222/events.json"
MODEL_BUFFER = 0xF000            # include/overlay005/loaded_map_buffers.h MAP_MODEL_FILE_SIZE
BDHC_BUFFER = 0x9000             # include/constants/field/bdhc.h BDHC_BUFFER_SIZE
CHUNKS = {149: (23, 24), 150: (24, 24), 151: (25, 24)}     # x 736..767 / 768..799 / 800..831, z 768..799
X0, Z0, X1, Z1 = 736, 768, 832, 800
BLOCK = 0x8000
B_WATER, B_SAND, B_JUMP_S = 0x15, 0x21, 0x3B

# ---------------------------------------------------------------------------------------------------------------
# placement (absolute tiles)
# ---------------------------------------------------------------------------------------------------------------

# Lamps stand north of (or beside) the walkways wherever possible: a 3-tile lamp south of a walkable row would hide
# the player's sprite standing behind it under the 59-degree field camera.
LAMPS = [
    # 149: the sea-cliff rim over the lower beach (Valor Lakefront promenade; only the grass strip behind them is
    # in their shadow, not the road), the verge east of the dirt road, the island's north rim
    (739, 794), (747, 794), (753, 794), (756, 785), (756, 780), (766, 774),
    # 150: the island's north rim, the north fence of the stone promenade
    (772, 774), (787, 775), (792, 775), (797, 775),
    # 151: north fence, the fence down the promenade bend, the north fence of the road east
    (803, 775), (809, 775), (813, 777), (813, 781), (815, 784),
]
VIOLET_LAMPS = [(819, 784), (820, 790), (820, 793)]          # closest to Sunyshore & the Route 223 rift
LAMP_BLOCKS = [(756, 780), (756, 785)]                       # grass verge tiles that a lamp now stands on
SIGN_LAMP = (792, 775)                                       # Route222_BlackoutLamp, read from (792, 776) facing north
VIOLET_SIGN_LAMP = (820, 790)                                # Route222_VioletLamp, read from (821, 790) facing west
# caution tape runs: ((xa, za), (xb, zb)) along blocked fence tiles
TAPES = [((787.62, 775.52), (791.88, 775.52)), ((809.62, 788.5), (813.88, 788.5)),
         ((815.2, 784.5), (818.85, 784.5)), ((820.5, 788.6), (820.5, 789.85)), ((820.5, 790.15), (820.5, 792.6)),
         ((821.8, 793.5), (824.86, 793.5))]
# dead beacon boxes: (x0, z0, x1, z1)
BEACONS = [(818.38, 784.22, 818.96, 784.64), (820.2, 791.08, 820.78, 791.5), (821.12, 793.24, 821.7, 793.66),
           (786.3, 775.26, 786.88, 775.68)]
# glowing rift crystals: (x, z, scale, variant) on blocked tiles (beach boulders, offshore rocks)
# wedged against the beach boulders (south faces, inside the boulders' blocked tiles); offshore ones are picked from
# the stock sea-rock tiles by sea_rock_crystals()
CRYSTALS = [(764.7, 787.55, 1.05, 0), (765.5, 787.62, 0.7, 1), (772.6, 785.55, 1.1, 0), (773.45, 785.6, 0.72, 1),
            (788.6, 789.55, 0.95, 1), (789.4, 789.5, 0.8, 0), (787.5, 785.55, 0.7, 0)]
STRANDED = [  # (local id, gfx, species, x, z, script, text)
    ("LOCALID_STRANDED_PSYDUCK", "OBJ_EVENT_GFX_PSYDUCK", "SPECIES_PSYDUCK", 791, 790, "Route222_StrandedPsyduck"),
    ("LOCALID_STRANDED_PIPLUP", "OBJ_EVENT_GFX_PIPLUP", "SPECIES_PIPLUP", 803, 791, "Route222_StrandedPiplup"),
    ("LOCALID_STRANDED_PRINPLUP", "OBJ_EVENT_GFX_PRINPLUP", "SPECIES_PRINPLUP", 813, 795, "Route222_StrandedPrinplup"),
]

# ---------------------------------------------------------------------------------------------------------------
# materials: key -> (texture, lights, cull, alpha, polygon_id, repeat)
# ---------------------------------------------------------------------------------------------------------------

MATS = {
    "r2_lamp": ("r222_lamp", 1, "back", 31, 0, (False, False)),
    "r2_lampglow": ("r222_lamp", 0, "back", 31, 0, (False, False)),
    "r2_halo": ("r222_lamp", 0, "none", 17, 21, (False, False)),
    "r2_pool": ("r222_lamp", 0, "back", 10, 22, (False, False)),
    "r2_foam": ("r222_tide", 1, "back", 31, 0, (True, False)),
    "r2_tide": ("r222_tide", 1, "back", 31, 0, (False, False)),
    "r2_crystal": ("r222_tide", 0, "none", 31, 0, (False, False)),
    "r2_warn": ("r222_warning", 1, "back", 31, 0, (False, False)),
    "r2_tape": ("r222_warning", 1, "none", 31, 0, (True, False)),
}


def uvr(region, size):
    """texel box -> uv rect (u0, v0, u1, v1), inset by 1/4 texel against bleeding."""
    x0, y0, x1, y1 = region
    w, h = size
    e = 0.25
    return ((x0 + e) / w, (y0 + e) / h, (x1 - e) / w, (y1 - e) / h)


LAMP = {k: uvr(v, TX.SIZES["r222_lamp"]) for k, v in TX.LAMP_UV.items()}
TIDE = {k: uvr(v, TX.SIZES["r222_tide"]) for k, v in TX.TIDE_UV.items()}
WARN = {k: uvr(v, TX.SIZES["r222_warning"]) for k, v in TX.WARN_UV.items()}


def chunk_of_x(x):
    return 149 if x < 768 else 150 if x < 800 else 151


def hash01(*v):
    h = 2166136261
    for c in v:
        h = ((h ^ (int(c) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5BD1E995) & 0xFFFFFFFF
    return (h ^ (h >> 15)) / 4294967296.0


# ---------------------------------------------------------------------------------------------------------------
# stock terrain (heights for draping and grounding props)
# ---------------------------------------------------------------------------------------------------------------

GROUND_TEX = {"beach", "beachp", "hamabe", "sea", "nsand", "nsandp", "ngrass", "nectgr", "blueglay", "blueglayp",
              "newstep", "seaside3", "allpeak", "criffp", "criff", "criffp2", "plant2"}


class Terrain:
    """Upward-facing stock ground faces, bucketed per tile; h(x, z) = the highest one over the point (mesh h:
    the beach is 0, the grass plateau 1, the sea -0.5)."""

    def __init__(self, sections):
        self.buckets = {}
        for c, sec in sections.items():
            model = nsbmd.parse_bmd(sec["model"])["models"][0]
            mesh = nsbmd.model_to_mesh(model, CHUNKS[c])
            mats = {m["name"]: m for m in mesh["materials"]}
            for me in mesh["meshes"]:
                if mats[me["material"]]["texture"] not in GROUND_TEX:
                    continue
                P = me["positions"]
                for f in me["quads"] + me["tris"]:
                    vs = [tuple(P[i]) for i in f]
                    tris = [vs[:3]] if len(vs) == 3 else [(vs[0], vs[1], vs[2]), (vs[0], vs[2], vs[3])]
                    for t in tris:
                        a, b, cc = t
                        n = C._cross(C._sub(b, a), C._sub(cc, a))
                        ln = math.sqrt(sum(v * v for v in n)) or 1
                        if abs(n[1]) / ln < 0.25:
                            continue
                        xs, zs = [v[0] for v in t], [v[2] for v in t]
                        for tx in range(math.floor(min(xs)), math.ceil(max(xs))):
                            for tz in range(math.floor(min(zs)), math.ceil(max(zs))):
                                self.buckets.setdefault((tx, tz), []).append(t)

    def h(self, x, z, default=None):
        best = None
        for t in self.buckets.get((math.floor(x), math.floor(z)), []):
            (ax, ah, az), (bx, bh, bz), (cx, ch, cz) = t
            d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
            if abs(d) < 1e-9:
                continue
            l1 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / d
            l2 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / d
            l3 = 1 - l1 - l2
            if min(l1, l2, l3) < -1e-6:
                continue
            hh = l1 * ah + l2 * bh + l3 * ch
            best = hh if best is None or hh > best else best
        return default if best is None else best


# ---------------------------------------------------------------------------------------------------------------
# face builder
# ---------------------------------------------------------------------------------------------------------------

class Art:
    def __init__(self, tex_sizes, terrain):
        self.mb = {c: C.MeshBuilder() for c in CHUNKS}
        self.tex_sizes = tex_sizes
        self.T = terrain
        self.solids = []                 # non-decal faces, for the clearance check
        self.decals = 0
        self.groups = {}

    def material(self, c, key):
        tex, lights, cull, alpha, pid, rep = MATS[key]
        self.mb[c].material(key, tex, TX.pal_name(tex), self.tex_sizes[tex], lights=lights, cull=cull, alpha=alpha,
                            polygon_id=pid, repeat=rep)

    def add(self, key, pts, uvs, facing=None, color=(255, 255, 255), colors=None, solid=True, group="misc",
            chunk=None):
        pts = [tuple(float(v) for v in p) for p in pts]
        uvs = [list(u) for u in uvs]
        n = C.face_normal(pts)
        if facing is not None and sum(a * b for a, b in zip(n, facing)) < 0:
            pts, uvs = pts[::-1], uvs[::-1]
            colors = colors[::-1] if colors else None
        rep = MATS[key][5]
        for k in (0, 1):                 # rebase repeating UVs per face (small s16 texcoords)
            if rep[k]:
                lo = math.floor(min(u[k] for u in uvs) + 1e-6)
                for u in uvs:
                    u[k] -= lo
        cx = sum(p[0] for p in pts) / len(pts)
        c = chunk or chunk_of_x(cx)
        self.material(c, key)
        me = self.mb[c].meshes[key]
        b = len(me["positions"])
        me["positions"] += [list(p) for p in pts]
        me["uvs"] += [list(u) for u in uvs]
        me["colors"] += [list(cc) for cc in colors] if colors else [list(color)] * len(pts)
        me["normals"] += [list(n)] * len(pts)
        (me["quads"] if len(pts) == 4 else me["tris"]).append(list(range(b, b + len(pts))))
        self.groups[group] = self.groups.get(group, 0) + 1
        if solid:
            self.solids.append((pts, group))
        else:
            self.decals += 1

    def wall(self, key, a, b, h0, h1, uv, group="misc", solid=True, color=(255, 255, 255), colors=None):
        (xa, za), (xb, zb) = a, b
        u0, v0, u1, v1 = uv
        n = (-(zb - za), 0.0, xb - xa)
        self.add(key, [(xa, h1, za), (xb, h1, zb), (xb, h0, zb), (xa, h0, za)],
                 [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], facing=n, group=group, solid=solid, color=color,
                 colors=colors)

    def box(self, key, x0, z0, x1, z1, h0, h1, uv, sides="sewt", top_uv=None, group="misc", color=(255, 255, 255)):
        u0, v0, u1, v1 = uv
        faces = {"s": ([(x0, h1, z1), (x1, h1, z1), (x1, h0, z1), (x0, h0, z1)], (0, 0, 1)),
                 "n": ([(x1, h1, z0), (x0, h1, z0), (x0, h0, z0), (x1, h0, z0)], (0, 0, -1)),
                 "e": ([(x1, h1, z1), (x1, h1, z0), (x1, h0, z0), (x1, h0, z1)], (1, 0, 0)),
                 "w": ([(x0, h1, z0), (x0, h1, z1), (x0, h0, z1), (x0, h0, z0)], (-1, 0, 0)),
                 "t": ([(x0, h1, z1), (x1, h1, z1), (x1, h1, z0), (x0, h1, z0)], (0, 1, 0))}
        for s in sides:
            pts, n = faces[s]
            t = top_uv if (s == "t" and top_uv) else (u0, v0, u1, v1)
            self.add(key, pts, [(t[0], t[1]), (t[2], t[1]), (t[2], t[3]), (t[0], t[3])], facing=n, group=group,
                     color=color)

    def drape(self, key, x0, z0, x1, z1, uvf, off=0.03, step=0.5, group="decal", colors=None):
        """A flat decal over the stock terrain: the rect is cut on the `step` grid (stock slopes are planar per tile,
        so every cell is exact) and each vertex sits `off` above the ground; cells in a row whose corner heights are
        equal are merged along x (UVs are affine, so the merge is exact). uvf(x, z) -> (u, v)."""
        def cuts(a, b):
            return sorted({a, b} | {k * step for k in range(math.ceil(a / step), math.floor(b / step) + 1)
                                    if a < k * step < b})
        xs, zs = cuts(x0, x1), cuts(z0, z1)
        for c_, d in zip(zs, zs[1:]):
            row = []
            for a, b in zip(xs, xs[1:]):
                corners = [(a, d), (b, d), (b, c_), (a, c_)]
                hs = [self.T.h(min(max(x, a + 1e-4), b - 1e-4), min(max(z, c_ + 1e-4), d - 1e-4)) for x, z in corners]
                row.append(None if any(h is None for h in hs) else (a, b, hs))
            i = 0
            while i < len(row):
                if row[i] is None:
                    i += 1
                    continue
                a, b, hs = row[i]
                j = i + 1
                while j < len(row) and row[j] is not None and row[j][0] == b and \
                        all(abs(u - v) < 1e-6 for u, v in zip(row[j][2], hs)) and abs(hs[0] - hs[1]) < 1e-6 and \
                        abs(hs[2] - hs[3]) < 1e-6:
                    b = row[j][1]
                    j += 1
                corners = [(a, d), (b, d), (b, c_), (a, c_)]
                hh = [hs[0], row[j - 1][2][1], row[j - 1][2][2], hs[3]]
                pts = [(x, h + off, z) for (x, z), h in zip(corners, hh)]
                cols = [colors(x, z) for x, z in corners] if colors else None
                self.add(key, pts, [uvf(x, z) for x, z in corners], facing=(0, 1, 0), solid=False, group=group,
                         colors=cols)
                i = j


# ---------------------------------------------------------------------------------------------------------------
# lamps, tape, beacons
# ---------------------------------------------------------------------------------------------------------------

CAM_PITCH = math.radians(59.05)
HW = 0.22                 # lamp housing half width


def lamp_spot(T, x, z):
    """Where a lamp stands in tile (x, z): the highest ground point of the tile (a fence row or verge: the centre;
    a cliff tile: its top lip), keeping the post 0.12 inside the tile. -> (px, pz, ground h)."""
    pts = [(x + 0.12 + 0.76 * i / 6, z + 0.12 + 0.76 * j / 6) for i in range(7) for j in range(7)]
    hs = [(T.h(a, b, -9.0), a, b) for a, b in pts]
    top = max(h for h, a, b in hs)
    near = [(abs(a - x - 0.5) + abs(b - z - 0.5), a, b, h) for h, a, b in hs if h >= top - 0.07]
    _, a, b, h = min(near)
    return a, b, h


def lamp(F, x, z, violet=False):
    """Blacked-out coastal streetlamp centred in tile (x, z): plinth, post, collar, cage housing, finial."""
    px, pz, g = lamp_spot(F.T, x, z)
    grp = "violet_lamps" if violet else "lamps"
    F.box("r2_lamp", px - 0.16, pz - 0.16, px + 0.16, pz + 0.16, g, g + 0.22, LAMP["base"], sides="sewt",
          top_uv=(LAMP["base"][0], LAMP["base"][1], LAMP["base"][2], LAMP["base"][1] + 0.08), group=grp)
    u0, v0, u1, v1 = LAMP["post"]
    ph0, ph1 = g + 0.22, g + 2.0
    pv = (u0, v0, u1, v0 + (v1 - v0) * (ph1 - ph0) / 2.0)
    F.box("r2_lamp", px - 0.06, pz - 0.06, px + 0.06, pz + 0.06, ph0, ph1, pv, sides="sew", group=grp)
    F.box("r2_lamp", px - 0.1, pz - 0.1, px + 0.1, pz + 0.1, ph1, ph1 + 0.08, (u0, v0, u1, v0 + 0.04), sides="sewt",
          group=grp)
    hz0, hz1 = ph1 + 0.08, ph1 + 0.84
    if violet:
        hot = [(255, 244, 255), (255, 244, 255), (214, 168, 255), (214, 168, 255)]
        for a2, b2 in (((px - HW, pz + HW), (px + HW, pz + HW)), ((px + HW, pz + HW), (px + HW, pz - HW)),
                       ((px - HW, pz - HW), (px - HW, pz + HW))):
            F.wall("r2_lampglow", a2, b2, hz0, hz1, LAMP["lit"], group=grp, colors=hot)
        lu0, lv0, lu1, lv1 = LAMP["lit"]
        F.add("r2_lampglow", [(px - HW, hz1, pz + HW), (px + HW, hz1, pz + HW), (px + HW, hz1, pz - HW),
                              (px - HW, hz1, pz - HW)], [(lu0, lv1), (lu1, lv1), (lu1, lv0), (lu0, lv0)],
              facing=(0, 1, 0), color=(236, 210, 255), group=grp)
    else:
        F.box("r2_lamp", px - HW, pz - HW, px + HW, pz + HW, hz0, hz1, LAMP["dead"], sides="sewt", group=grp)
    # small pyramid finial on the glass roof
    cu0, cv0, cu1, cv1 = LAMP["cap"]
    r, ap = 0.11, hz1 + 0.16
    a = [(px - r, hz1, pz + r), (px + r, hz1, pz + r), (px + r, hz1, pz - r), (px - r, hz1, pz - r)]
    top = (px, ap, pz)
    for i in range(4):
        p, q = a[i], a[(i + 1) % 4]
        F.add("r2_lamp", [p, q, top], [(cu0, cv1), (cu1, cv1), ((cu0 + cu1) / 2, cv0)],
              facing=((p[0] + q[0]) / 2 - px, 0.6, (p[2] + q[2]) / 2 - pz), group=grp)
    # iron rim round the roof edge (south / east / west) so the lantern reads as a cage from above
    e = HW + 0.02
    for a2, b2 in (((px - e, pz + e), (px + e, pz + e)), ((px + e, pz + e), (px + e, pz - e)),
                   ((px - e, pz - e), (px - e, pz + e))):
        F.wall("r2_lamp", a2, b2, hz1 - 0.06, hz1 + 0.03, (cu0, cv1 - 0.1, cu1, cv1 - 0.04), group=grp)
    if violet:
        # translucent sparking halo, facing the field camera, centred on the housing
        cy, cz = (hz0 + hz1) / 2, pz + 0.24
        s = 0.78
        upy, upz = math.cos(CAM_PITCH), -math.sin(CAM_PITCH)
        hu0, hv0, hu1, hv1 = LAMP["halo"]
        pts = [(px - s, cy + s * upy, cz + s * upz), (px + s, cy + s * upy, cz + s * upz),
               (px + s, cy - s * upy, cz - s * upz), (px - s, cy - s * upy, cz - s * upz)]
        F.add("r2_halo", pts, [(hu0, hv0), (hu1, hv0), (hu1, hv1), (hu0, hv1)],
              facing=(0, math.sin(CAM_PITCH), math.cos(CAM_PITCH)), color=(236, 200, 255), group="halos",
              solid=False)
        # violet glow pool on the ground
        R = 1.25
        F.drape("r2_pool", px - R, pz - R, px + R, pz + R,
                lambda x, z: (hu0 + (hu1 - hu0) * (x - px + R) / (2 * R), hv0 + (hv1 - hv0) * (z - pz + R) / (2 * R)),
                off=0.04, group="glow_pools", colors=lambda x, z: (200, 140, 255))


def tape(F, a, b, g_of):
    """Caution tape strung between two points along blocked fence tiles, sagging slightly (3 segments)."""
    (xa, za), (xb, zb) = a, b
    L = math.hypot(xb - xa, zb - za)
    n = 3
    tu0, tv0, tu1, tv1 = WARN["tape"]
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        p0 = (xa + (xb - xa) * t0, za + (zb - za) * t0)
        p1 = (xa + (xb - xa) * t1, za + (zb - za) * t1)
        s0, s1 = 0.07 * math.sin(math.pi * t0), 0.07 * math.sin(math.pi * t1)
        g0, g1 = g_of(*p0), g_of(*p1)
        h0a, h0b = g0 + 0.58 - s0, g1 + 0.58 - s1
        uA, uB = L * t0 / 2, L * t1 / 2
        F.add("r2_tape", [(p0[0], h0a + 0.2, p0[1]), (p1[0], h0b + 0.2, p1[1]), (p1[0], h0b, p1[1]),
                          (p0[0], h0a, p0[1])], [(uA, tv0), (uB, tv0), (uB, tv1), (uA, tv1)],
              facing=(-(p1[1] - p0[1]), 0.0, p1[0] - p0[0]) if p1[0] != p0[0] else (1, 0, 0), group="tape")


def beacon(F, x0, z0, x1, z1):
    g = F.T.h((x0 + x1) / 2, (z0 + z1) / 2, 0.0)
    h1 = g + 0.72
    F.box("r2_warn", x0, z0, x1, z1, g, h1, WARN["front"], sides="s", group="beacons")
    F.box("r2_warn", x0, z0, x1, z1, g, h1, WARN["side"], sides="ew", group="beacons")
    F.box("r2_warn", x0 - 0.02, z0 - 0.02, x1 + 0.02, z1 + 0.02, h1, h1 + 0.04, WARN["lid"], sides="sewt",
          top_uv=WARN["lid"], group="beacons")
    mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
    d0, d1, dv0, dv1 = WARN["dome"]
    F.box("r2_warn", mx - 0.09, mz - 0.07, mx + 0.09, mz + 0.07, h1 + 0.04, h1 + 0.17, (d0, d1, dv0, dv1),
          sides="sewt", top_uv=(d0, d1, dv0, d1 + 0.04), group="beacons")


# ---------------------------------------------------------------------------------------------------------------
# tide line
# ---------------------------------------------------------------------------------------------------------------

def tide_line(F, perm):
    """Foam lace on every walkable land -> sea edge, scatter behind it, and hash-placed flat debris."""
    def land(x, z):
        v = perm.get((x, z))
        return v is not None and not v & BLOCK and (v & 0xFF) != B_WATER

    def water(x, z):
        v = perm.get((x, z))
        return v is not None and (v & 0xFF) == B_WATER

    fu0, fv0, fu1, fv1 = TIDE["foam"]
    su0, sv0, su1, sv1 = TIDE["scatter"]
    fw = 4.0          # foam band repeats every 4 tiles along the shore (64 texels)
    shore = set()
    edges = []        # (axis, side, line, along)
    for (x, z) in sorted(perm):
        if not land(x, z) or x < X0 or x >= X1:
            continue
        for dx, dz in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            if water(x + dx, z + dz):
                shore.add((x, z))
                if dz:
                    edges.append(("z", dz, z + (1 if dz > 0 else 0), x))
                else:
                    edges.append(("x", dx, x + (1 if dx > 0 else 0), z))

    def runs(items, seams=(768, 800)):
        items = sorted(items)
        out = []
        for t in items:
            if out and out[-1][1] == t and t not in seams:
                out[-1][1] = t + 1
            else:
                out.append([t, t + 1])
        return out

    groups = {}
    for axis, side, ln, along in edges:
        groups.setdefault((axis, side, ln), []).append(along)
    for (axis, side, ln), alongs in sorted(groups.items()):
        for a0, a1 in runs(alongs):
            # band across the edge: 0.45 inside the land, 0.55 into the water; v 0 at the landward side
            c0, c1 = (ln - 0.45, ln + 0.55) if side > 0 else (ln - 0.55, ln + 0.45)
            ls = c0 if side > 0 else c1
            if axis == "z":
                F.drape("r2_foam", a0, c0, a1, c1, lambda px, pz, ls=ls: ((px - X0) / fw, fv0 + (fv1 - fv0) * abs(pz - ls)),
                        off=0.035, group="foam")
                sel = [t for t in range(a0, a1) if hash01(t, ln, 7) < 0.6]
                s0, s1 = (ln - 0.95, ln - 0.45) if side > 0 else (ln + 0.45, ln + 0.95)
                for b0, b1 in runs(sel):
                    F.drape("r2_foam", b0, s0, b1, s1,
                            lambda px, pz, s0=s0: ((px - X0 + 1.3) / fw, sv0 + (sv1 - sv0) * (pz - s0) / 0.5),
                            off=0.03, group="scatter")
            else:
                F.drape("r2_foam", c0, a0, c1, a1, lambda px, pz, ls=ls: ((pz - Z0) / fw, fv0 + (fv1 - fv0) * abs(px - ls)),
                        off=0.036, group="foam")
    # debris on shore tiles and the row behind them (flat decals, hash-placed)
    occupied = event_tiles()
    debris = 0
    for (x, z) in sorted(shore):
        for (tx, tz) in ((x, z), (x, z - 1)):
            if not land(tx, tz) or (tx, tz) in occupied:
                continue
            r = hash01(tx, tz, 222)
            if r < 0.10:
                kind = "kelp" if hash01(tx, tz, 3) < 0.5 else "kelp2"
                k0, k1, k2, k3 = TIDE[kind]
                cx, cz = tx + 0.2 + 0.6 * hash01(tx, tz, 4), tz + 0.25 + 0.4 * hash01(tx, tz, 5)
                F.drape("r2_tide", cx - 0.42, cz - 0.42, cx + 0.42, cz + 0.42,
                        lambda px, pz, cx=cx, cz=cz, k=(k0, k1, k2, k3): (k[0] + (k[2] - k[0]) * (px - cx + 0.42) / 0.84,
                                                                         k[1] + (k[3] - k[1]) * (pz - cz + 0.42) / 0.84),
                        off=0.045, step=1.0, group="debris")
                debris += 1
            elif r < 0.16:
                d0, d1, d2, d3 = TIDE["drift"]
                cz = tz + 0.35 + 0.3 * hash01(tx, tz, 6)
                F.drape("r2_tide", tx + 0.05, cz - 0.24, tx + 1.75, cz + 0.24,
                        lambda px, pz, cz=cz, x0=tx + 0.05: (d0 + (d2 - d0) * (px - x0) / 1.7, d1 + (d3 - d1) * (pz - cz + 0.24) / 0.48),
                        off=0.05, step=1.0, group="debris")
                debris += 1
            elif r < 0.24:
                kind = "shards" if hash01(tx, tz, 8) < 0.6 else "strand"
                k0, k1, k2, k3 = TIDE[kind]
                wdt = 1.6 if kind == "shards" else 0.95
                cz = tz + 0.3 + 0.4 * hash01(tx, tz, 9)
                F.drape("r2_tide", tx + 0.1, cz - wdt / 4, tx + 0.1 + wdt, cz + wdt / 4,
                        lambda px, pz, cz=cz, x0=tx + 0.1, k=(k0, k1, k2, k3), w=wdt:
                        (k[0] + (k[2] - k[0]) * (px - x0) / w, k[1] + (k[3] - k[1]) * (pz - cz + w / 4) / (w / 2)),
                        off=0.05, step=1.0, group="debris")
                debris += 1
    return len(edges), len(shore), debris


def crystal(F, x, z, s, variant):
    """Glowing rift-crystal cluster: two crossed double-sided cards on a blocked tile (unlit, baked violet)."""
    g = F.T.h(x, z, None)
    if g is None:
        g = F.T.h(math.floor(x) + 0.5, math.floor(z) + 0.5, -0.5)
    g = max(g, -0.5) - 0.05
    reg = TIDE["crystal" if variant == 0 else "crystal2"]
    u0, v0, u1, v1 = reg
    w, h = 0.42 * s, 1.15 * s
    top, bot = (240, 214, 255), (150, 110, 220)
    for (dx, dz) in ((1, 0.22), (1, -0.26)):
        ln = math.hypot(dx, dz)
        ex, ez = dx / ln * w, dz / ln * w
        pts = [(x - ex, g + h, z - ez), (x + ex, g + h, z + ez), (x + ex, g, z + ez), (x - ex, g, z - ez)]
        F.add("r2_crystal", pts, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], facing=(-ez, 0, ex) if ez or ex else None,
              colors=[top, top, bot, bot], group="crystals")


def sea_rock_crystals(perm, T):
    """One crystal cluster on roughly every fourth offshore sea-rock tile (blocked tiles out in the sea, z >= 796)."""
    out = []
    for (x, z), v in sorted(perm.items()):
        if z < 796 or not v & BLOCK or not (X0 + 1 <= x < X1 - 1):
            continue
        if not all(perm.get((x + dx, z + dz), BLOCK) & BLOCK or (perm.get((x + dx, z + dz), 0) & 0xFF) == B_WATER
                   for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            continue
        h = T.h(x + 0.5, z + 0.5, None)
        if h is None or h > -0.2:
            continue
        r = hash01(x, z, 1729)
        if r < 0.10:
            out.append((x + 0.5, z + 0.45 + 0.1 * hash01(x, z, 5), 0.9 + 0.35 * hash01(x, z, 6), int(r * 100) % 2))
    return out


# ---------------------------------------------------------------------------------------------------------------
# events helpers
# ---------------------------------------------------------------------------------------------------------------

def stock_events():
    return json.loads(C.git_file(BASE_REV, EVENTS_REL))


def event_tiles():
    ev = stock_events()
    return {(o["x"], o["z"]) for o in ev["object_events"]} | {(b["x"], b["z"]) for b in ev["bg_events"]} | \
        {(w["x"], w["z"]) for w in ev["warp_events"]}


# ---------------------------------------------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------------------------------------------

def stock_sections():
    return {c: mapdata.unpack(C.git_file(BASE_REV, f"{OUT_MAP_DIR}/map_data_{c:03d}.bin")) for c in CHUNKS}


def perm_grid(sections):
    out = {}
    for c, sec in sections.items():
        cx, cz = CHUNKS[c]
        g = mapdata.read_permissions(sec["permissions"])
        for z in range(32):
            for x in range(32):
                out[(cx * 32 + x, cz * 32 + z)] = g[z][x]
    return out


def art_faces(tex_sizes, sections):
    T = Terrain(sections)
    F = Art(tex_sizes, T)
    perm = perm_grid(sections)
    for x, z in LAMPS:
        lamp(F, x, z)
    for x, z in VIOLET_LAMPS:
        lamp(F, x, z, violet=True)
    for a, b in TAPES:
        tape(F, a, b, lambda x, z: T.h(x, z, 0.0))
    for bx in BEACONS:
        beacon(F, *bx)
    info = dict(zip(("shore_edges", "shore_tiles", "debris"), tide_line(F, perm)))
    crystals = CRYSTALS + sea_rock_crystals(perm, T)
    for cr in crystals:
        crystal(F, *cr)
    info["crystals"] = len(crystals)
    return F, info, perm


def build():
    tex = TX.build_set()
    tex_table = {name: {"size": list(size)} for name, (pal, size) in tex["table"].items()}
    tex_sizes = {name: size for name, (pal, size) in tex["table"].items()}
    sections = stock_sections()
    F, info, perm0 = art_faces(tex_sizes, sections)
    out = {}
    for c, cell in CHUNKS.items():
        edit = C.ChunkEdit(f"{OUT_MAP_DIR}/map_data_{c:03d}.bin", cell, BASE_REV)
        edit.add(F.mb[c], tex_table)
        model = edit.model_bytes()
        perm = edit.permissions()
        for (x, z) in LAMP_BLOCKS:
            if chunk_of_x(x) == c:
                perm[z - cell[1] * 32][x - cell[0] * 32] |= BLOCK
        data = edit.pack(perm, model)
        st = edit.stats(model)
        st["new_polygons"] = F.mb[c].polygons()
        out[c] = dict(edit=edit, model=model, perm=perm, data=data, stats=st)
    return out, F, info, tex, sections, perm0


# ---------------------------------------------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------------------------------------------

def reach(perm, blocked_extra, start):
    """Land BFS over walkable tiles (not blocked, not water), with south ledges (jump over a JUMP_SOUTH tile)."""
    def walk(p):
        v = perm.get(p)
        return v is not None and not v & BLOCK and (v & 0xFF) != B_WATER and p not in blocked_extra
    seen, todo = {start}, [start]
    while todo:
        x, z = todo.pop()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            v = perm.get(n)
            if v is None:
                continue
            if walk(n) and n not in seen:
                seen.add(n)
                todo.append(n)
            elif dz == 1 and (v & 0xFF) == B_JUMP_S:
                m = (x, z + 2)
                if walk(m) and m not in seen:
                    seen.add(m)
                    todo.append(m)
    return seen


def clearance_check(F, perm_after):
    """Nothing solid inside a walkable (land or surfable water) tile's inner 0.8 x 0.8 below 1.3 tiles above its
    ground."""
    bad = set()
    for pts, grp in F.solids:
        n = len(pts)
        samples = list(pts) + [tuple(sum(p[k] for p in pts) / n for k in range(3))]
        samples += [tuple((pts[i][k] + pts[(i + 1) % n][k]) / 2 for k in range(3)) for i in range(n)]
        for x, h, z in samples:
            tx, tz = math.floor(x), math.floor(z)
            v = perm_after.get((tx, tz))
            if v is None or v & BLOCK:
                continue
            g = F.T.h(tx + 0.5, tz + 0.5, 0.0)
            if 0.1 < x - tx < 0.9 and 0.1 < z - tz < 0.9 and h < g + 1.3:
                bad.add((tx, tz, grp))
    return sorted(bad)


def run_checks(out, F, info, tex, sections, perm0):
    res = []
    set_parsed = tex["parsed"]
    TT = {t["name"]: t for t in set_parsed["textures"]}
    PP = {p["name"] for p in set_parsed["palettes"]}
    perm_after = dict(perm0)
    for (x, z) in LAMP_BLOCKS:
        perm_after[(x, z)] |= BLOCK
    for c, o in out.items():
        sec = mapdata.unpack(o["data"])
        stock = sections[c]
        res.append((f"chunk {c}: model {len(sec['model'])} B <= 0xF000 ({MODEL_BUFFER})", len(sec["model"]) <= MODEL_BUFFER))
        res.append((f"chunk {c}: BDHC {len(sec['bdhc'])} B <= 0x9000 ({BDHC_BUFFER}) and identical to stock",
                    len(sec["bdhc"]) <= BDHC_BUFFER and sec["bdhc"] == stock["bdhc"]))
        back = nsbmd.parse_bmd(sec["model"])
        res.append((f"chunk {c}: NSBMD parse -> rebuild byte-identical", nsbmd.build_bmd(back["models"]) == sec["model"]))
        edited = {o["edit"].model["shapes"][si]["name"] for si in o["edit"].faces}
        bad = C.stock_shapes_identical(o["edit"].model, o["edit"].built, edited)
        res.append((f"chunk {c}: all {len(o['edit'].model['shapes'])} stock shapes + {len(o['edit'].model['materials'])} "
                    f"stock materials byte-identical (cut: {sorted(edited)})", not bad and not edited))
        badm = []
        for m in back["models"][0]["materials"]:
            tx = TT.get(m["texture"])
            if not tx or m["palette"] not in PP or (tx["w"], tx["h"]) != (m["orig_width"], m["orig_height"]):
                badm.append(m["name"])
        res.append((f"chunk {c}: all {len(back['models'][0]['materials'])} materials' textures + palettes exist in set "
                    f"081 with matching sizes (bad: {badm})", not badm))
        res.append((f"chunk {c}: props identical to stock ({len(sec['props']) // 48})", sec["props"] == stock["props"]))
        cx, cz = CHUNKS[c]
        g0 = mapdata.read_permissions(stock["permissions"])
        g1 = mapdata.read_permissions(sec["permissions"])
        diff = [(cx * 32 + x, cz * 32 + z) for z in range(32) for x in range(32) if g0[z][x] != g1[z][x]]
        want = sorted(p for p in LAMP_BLOCKS if chunk_of_x(p[0]) == c)
        res.append((f"chunk {c}: permissions = stock + lamp blocks {want} (changed: {sorted(diff)})",
                    sorted(diff) == want and all(g1[z - cz * 32][x - cx * 32] == g0[z - cz * 32][x - cx * 32] | BLOCK
                                                 for x, z in want)))
    # lamps stand on blocked tiles (after edits); none on an event tile
    ev_tiles = event_tiles()
    lamp_tiles = LAMPS + VIOLET_LAMPS
    off = [p for p in lamp_tiles if not perm_after[p] & BLOCK or p in ev_tiles]
    res.append((f"all {len(lamp_tiles)} lamps stand on blocked, event-free tiles (bad: {off})", not off))
    # tape and beacons only over blocked tiles
    badt = []
    for (xa, za), (xb, zb) in TAPES:
        for k in range(21):
            x, z = xa + (xb - xa) * k / 20, za + (zb - za) * k / 20
            if not perm_after[(math.floor(x), math.floor(z))] & BLOCK:
                badt.append((round(x, 2), round(z, 2)))
    for x0, z0, x1, z1 in BEACONS:
        for x, z in ((x0, z0), (x1, z0), (x0, z1), (x1, z1)):
            if not perm_after[(math.floor(x), math.floor(z))] & BLOCK:
                badt.append((x, z))
    for x, z, s, v in CRYSTALS + sea_rock_crystals(perm_after, F.T):
        if not perm_after[(math.floor(x), math.floor(z))] & BLOCK:
            badt.append((x, z))
    res.append((f"caution tape, beacon boxes and rift crystals only over blocked tiles (bad: {badt[:6]})", not badt))
    cl = clearance_check(F, perm_after)
    res.append((f"nothing solid drawn low over a walkable land / water tile ({len(cl)}: {cl[:6]})", not cl))
    # reachability
    start = (736, 789)
    before = reach(perm0, set(), start)
    new_npcs = {(s[3], s[4]) for s in STRANDED}
    after = reach(perm_after, new_npcs, start)
    lost = sorted(before - after - set(LAMP_BLOCKS) - new_npcs)
    res.append((f"land reachability from the Valor seam {start}: {len(before)} -> {len(after)} tiles; lost only lamp "
                f"blocks + stranded Pokemon tiles (other lost: {lost[:6]})", not lost))
    ev = stock_events()
    unreach = []
    for o in ev["object_events"] + ev["warp_events"] + ev["bg_events"]:
        p = (o["x"], o["z"])
        if p in before and p not in after and p not in new_npcs:
            unreach.append(p)
        if p not in before:
            adj = [(p[0] + dx, p[1] + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            if any(a in before for a in adj) and not any(a in after for a in adj):
                unreach.append(p)
    res.append((f"every stock trainer, item, sign, warp and hidden item stays reachable (bad: {unreach})", not unreach))
    # stranded Pokemon on tide-line sand
    bads = []
    for s in STRANDED:
        x, z = s[3], s[4]
        v = perm0[(x, z)]
        tide = any((perm0.get((x + dx, z + dz), 0) & 0xFF) == B_WATER for dx, dz in ((0, 1), (1, 0), (-1, 0)))
        if v & BLOCK or (v & 0xFF) != B_SAND or not tide or (x, z) in ev_tiles or (x, z) in LAMP_BLOCKS or \
                chunk_of_x(x) not in (150, 151) or (x, z) not in after | new_npcs or \
                not any((x + dx, z + dz) in after for dx, dz in ((1, 0), (-1, 0), (0, -1))):
            bads.append((x, z))
    res.append((f"stranded Pokemon on walkable tide-line sand in 150/151, interactable from land (bad: {bads})", not bads))
    for (lx, lz), (rx, rz) in ((SIGN_LAMP, (SIGN_LAMP[0], SIGN_LAMP[1] + 1)),
                               (VIOLET_SIGN_LAMP, (VIOLET_SIGN_LAMP[0] + 1, VIOLET_SIGN_LAMP[1]))):
        res.append((f"lamp sign at {(lx, lz)} is a lamp tile, read from walkable {(rx, rz)}",
                    (lx, lz) in lamp_tiles and (rx, rz) in after))
    for f in tex["fails"]:
        res.append(("set 081: " + f, False))
    vb, vo = tex["vram"]
    res.append((f"set 081: 3 textures appended to stock 018, round trip, stock unchanged, VRAM {sum(vo)} B "
                f"({sum(vo) / 1024:.1f} KB) < 160 KB", not tex["fails"]))
    ltext, lfails = build_lighting()
    for f in lfails:
        res.append((f, False))
    res.append((f"lighting_set_009: {len(json.loads(ltext))} blocks, lighting_set_000 schema, 5-bit colours, stock "
                f"directions and lights 1..3", not lfails))
    return res


# ---------------------------------------------------------------------------------------------------------------
# lighting_set_009: the violet-lit coast
# ---------------------------------------------------------------------------------------------------------------

LIGHTING_REL = "res/field/lighting/lighting_set_009.json"
LIGHTING_TEMPLATE = "res/field/lighting/lighting_set_000.json"
# endTime (2 s units) -> (light 0 RGB, diffuse, ambient, specular, emission), 5-bit. Daylight stays bright and
# near-neutral (sand white, grass green, sprites readable) with a cool violet cast and rose-indigo shadows (ambient /
# emission lean red + blue); evening turns violet instead of orange, and the night is a glowing violet-indigo, a
# little brighter than stock so the beach and sprites stay legible under the rift light.
NIGHT = ((12, 11, 21), (14, 13, 18), (10, 9, 14), (14, 13, 18), (9, 8, 14))
LIGHT_CURVE = {
    0: NIGHT,
    7200: NIGHT,                                                                         # 00:00-04:00 rift night
    8100: ((13, 11, 21), (12, 11, 16), (12, 10, 15), (10, 9, 15), (10, 9, 15)),          # 04:00-04:30 pre-dawn
    9000: ((15, 12, 22), (12, 11, 14), (11, 9, 13), (11, 10, 15), (12, 10, 15)),         # 04:30-05:00 violet dawn
    14400: ((19, 18, 25), (13, 12, 14), (9, 8, 11), (13, 12, 15), (13, 12, 16)),         # 05:00-08:00 cold morning
    20700: ((22, 21, 26), (14, 14, 15), (9, 9, 11), (14, 14, 16), (13, 13, 16)),         # 08:00-11:30 violet-cast day
    21600: ((24, 23, 27), (15, 15, 16), (10, 9, 12), (16, 16, 17), (13, 13, 15)),        # 11:30-12:00
    27000: ((25, 24, 27), (16, 16, 16), (10, 10, 12), (17, 17, 18), (13, 13, 15)),       # 12:00-15:00 brightest
    27900: ((23, 22, 26), (15, 15, 16), (11, 10, 13), (16, 16, 17), (12, 12, 15)),       # 15:00-15:30
    30600: ((21, 18, 25), (15, 14, 16), (11, 10, 13), (16, 15, 17), (12, 10, 14)),       # 15:30-17:00 lilac afternoon
    32400: ((20, 16, 23), (15, 14, 16), (11, 10, 13), (16, 15, 17), (11, 10, 13)),       # 17:00-18:00 rose-violet
    33300: ((17, 14, 23), (14, 13, 16), (11, 10, 14), (15, 14, 17), (10, 9, 14)),        # 18:00-18:30 violet dusk
    34200: ((15, 13, 23), (14, 13, 16), (11, 10, 14), (14, 13, 17), (10, 9, 14)),        # 18:30-19:00 rift-lit dusk
    36000: ((13, 12, 22), (14, 13, 17), (10, 9, 14), (14, 13, 18), (9, 8, 14)),          # 19:00-20:00 indigo dusk
    43200: NIGHT,                                                                        # 20:00-24:00 rift night
}


def build_lighting():
    raw = C.git_file(BASE_REV, LIGHTING_TEMPLATE).decode()
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
    if shape(back) != shape(tmpl):
        fails.append("lighting: schema differs from lighting_set_000")
    if [b["endTime"] for b in back] != [b["endTime"] for b in tmpl]:
        fails.append("lighting: block times differ from stock")
    for i, b in enumerate(back):
        cols = [b[k] for k in ("diffuseColor", "ambientColor", "specularColor", "emissionColor")] + \
            [lt["color"] for lt in b["lights"]]
        if any(not isinstance(v, int) or not (0 <= v <= 31) for c in cols for v in c.values()):
            fails.append(f"lighting: colour out of 5-bit range at endTime {b['endTime']}")
        if [lt["direction"] for lt in b["lights"]] != [lt["direction"] for lt in tmpl[i]["lights"]]:
            fails.append(f"lighting: light directions changed at endTime {b['endTime']}")
        if b["lights"][1:] != tmpl[i]["lights"][1:]:
            fails.append(f"lighting: lights 1..3 changed at endTime {b['endTime']}")
    return text, fails


# ---------------------------------------------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------------------------------------------

VIEWS = {"promenade": (792, 778), "lamps150": (788, 777), "beach": (790, 787), "beach_west": (770, 787),
         "east_approach": (818, 787), "gate": (821, 790), "valor_cliff": (746, 791), "east_strip": (810, 792),
         "road149": (754, 781)}


def preview_meshes(out, sections):
    order = open(os.path.join(ROOT, "res/field/props/models/map_prop_models.order")).read().split()
    meshes, extra = [], []
    for c, o in out.items():
        meshes.append(nsbmd.model_to_mesh(nsbmd.parse_bmd(o["model"])["models"][0], CHUNKS[c]))
        for p in mapdata.read_props(sections[c]["props"]):
            bmd = nsbmd.parse_bmd(open(os.path.join(ROOT, "res/field/props/models", order[p["model"]]), "rb").read())
            if bmd["tex0"]:
                extra.append(nsbtx.parse(bmd["tex0"]) if isinstance(bmd["tex0"], (bytes, bytearray)) else bmd["tex0"])
            meshes.append(nsbmd.model_to_mesh(bmd["models"][0], CHUNKS[c], offset=[v / 4096 for v in p["pos"]]))
    return meshes, extra


def write_preview(d, out, tex, sections):
    import render as R
    os.makedirs(d, exist_ok=True)
    TX.write_preview(os.path.join(d, "tex"), tex["generated"])
    meshes, extra = preview_meshes(out, sections)
    pst = nsbtx.parse(open(os.path.join(ROOT, "res/field/props/texture_sets/prop_texture_set_014.nsbtx"), "rb").read())
    tc = R.TexCache(tex["parsed"], pst, *extra)
    light = json.loads(build_lighting()[0])
    blocks = {b["endTime"]: b for b in light}
    tods = {"day": blocks[27000], "dusk": blocks[34200], "night": blocks[0]}
    bgs = {"day": (0.62, 0.66, 0.86), "dusk": (0.42, 0.28, 0.55), "night": (0.10, 0.07, 0.20)}
    for name, tgt in VIEWS.items():
        for tod in (("day", "night") if name not in ("east_approach", "beach") else ("day", "dusk", "night")):
            R.render(meshes, tc, os.path.join(d, f"view_{name}_{tod}.png"), target=tgt, light=tods[tod], bg=bgs[tod])
    ev = json.load(open(os.path.join(ROOT, EVENTS_REL)))
    marks = [(o["x"], o["z"], (255, 40, 40)) for o in ev["object_events"]] + \
        [(b["x"], b["z"], (255, 230, 0)) for b in ev["bg_events"] if X0 <= b["x"] < X1]
    R.render(meshes, tc, os.path.join(d, "top.png"), top=(X0, Z0, X1, Z1), w=96 * 12, h=32 * 12, scale=1,
             light=tods["day"])
    R.render(meshes, tc, os.path.join(d, "top_marks.png"), top=(X0, Z0, X1, Z1), w=96 * 12, h=32 * 12, scale=1,
             light=tods["day"], marks=marks)
    print("wrote previews to", d)


# ---------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    out, F, info, tex, sections, perm0 = build()
    res = run_checks(out, F, info, tex, sections, perm0)
    TX.report(tex)
    print(f"\n{'chunk':>5} {'polys':>6} {'stock':>6} {'new':>5} {'verts':>6} {'mats':>4} {'model B':>8} {'stock B':>8} "
          f"{'BDHC B':>7} {'map_data B':>10}")
    for c, o in out.items():
        s = o["stats"]
        print(f"{c:>5} {s['polygons']:>6} {s['stock_polygons']:>6} {s['new_polygons']:>5} {s['vertices_sent']:>6} "
              f"{s['materials']:>4} {s['model_bytes']:>8} {s['stock_model_bytes']:>8} "
              f"{len(sections[c]['bdhc']):>7} {len(o['data']):>10}")
    print("faces by group: " + ", ".join(f"{k} {v}" for k, v in sorted(F.groups.items())))
    print(f"tide line: {info['shore_edges']} sand->sea edges on {info['shore_tiles']} shore tiles, {info['debris']} debris "
          f"decals; {len(LAMPS)} blacked-out lamps + {len(VIOLET_LAMPS)} violet lamps, {info['crystals']} crystal clusters")
    nfail = 0
    for desc, ok in res:
        print(("PASS " if ok else "FAIL ") + desc)
        nfail += not ok
    print(f"{nfail} failed")
    if "--preview" in args:
        write_preview(args[args.index("--preview") + 1], out, tex, sections)
    if "--write" in args:
        if nfail:
            print("refusing to write: checks failed")
            return 1
        open(os.path.join(ROOT, TX.SET_REL), "wb").write(tex["bytes"])
        open(os.path.join(ROOT, LIGHTING_REL), "w").write(build_lighting()[0])
        for c, o in out.items():
            open(os.path.join(ROOT, OUT_MAP_DIR, f"map_data_{c:03d}.bin"), "wb").write(o["data"])
        print(f"wrote {TX.SET_REL}, {LIGHTING_REL}, " + ", ".join(f"map_data_{c:03d}.bin ({len(o['data'])} B)"
                                                             for c, o in out.items()))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
