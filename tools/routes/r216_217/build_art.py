#!/usr/bin/env python3
"""Routes 216-217 art pass: Teo's Memorial Ridge (map_data_110) and Indra's Snowy Camp (map_data_109), surgical
edits of the stock chunks (tools/world_art/chunkedit.py), the set-080 atlases (textures.py) and lighting_set_008.

Usage (Python with NumPy; PIL for --preview):
  ~/.venvs/desmume/bin/python tools/routes/r216_217/build_art.py                 dry run: build + every check
  ~/.venvs/desmume/bin/python tools/routes/r216_217/build_art.py --preview DIR   also field-camera renders
  ~/.venvs/desmume/bin/python tools/routes/r216_217/build_art.py --write         write map_data_109/110, set 080,
                                                                                lighting_set_008 (refuses on FAIL)

Inputs are read from git at BASE_REV (stock chunks, lighting) and HEAD (stock set 014), so reruns never feed back.
Chunks 106, 107, 108, 111, 112 are not touched (checked byte-identical to BASE_REV). Stock geometry of 109 / 110 is
kept whole (no cuts); everything below is added on top of it.

Teo's Memorial Ridge, map_data_110, on the Route 216 cliff ledge (h 2) at the foot of the lowest stock terrace,
facing south to Mt. Coronet: a monumental carved granite monolith (2.78 tiles to the top of its snow cap, ~2x the
player on the DS camera) on a two-step pedestal. The thick bevelled shaft leans back 25 degrees toward the cliff, so
it rises tall on the CAMERA_TYPE_DEFAULT view; its face carries the outlined mountain-and-falling-star emblem and the
inlaid dark "TEO" plaque. A crisp snow cap with a drip lip rests on top, a bold deep-violet knotted scarf wraps the
upper shaft with two fluttering tails down the east flank, a large evergreen & winter-blossom wreath leans on the
front steps, a ~1.4-tile stone vigil lantern stands at (316.2, 401.3) with warm unlit glass, a soft A3I5 amber bloom
and light pool. Dithered c0 snow drifts creep over the steps, soft A3I5 contact shadows sit under the pedestal and
lantern, boot prints lead in from the west beside glinting violet shard dust. Blocked: (316..318, 401). Standing
tile: (317, 402) facing north; the trampled approach (315..319, 402) is shallow snow.

Indra's Snowy Camp, map_data_109, in the sheltered north-east corner of the Route 217 snowfield (backed by the tree
mass at z 363+): a deep-violet A-frame expedition tent (x 313..317, z 360..362, ridge 1.9) with dark pixel outlines,
heaped ridge snow, the pale-silver Eclipse emblem on both roof slopes, an open shadowed doorway with tied-back flaps
facing south, staked guy ropes; a supply crate with a bright expedition lantern (warm unlit glass + A3I5 amber bloom
and pool) and the field journal (311, 360); the open Eclipse shard-scanner case on two stacked crates (312, 360)
with its electric-violet compass lid, violet bloom and pool; packed-snow clearing patches with dithered rims and
soft contact shadows under the tent and crates. Blocked: (313..316, 360..362), (311..312, 360). Packed snow
(behaviour 0xA8) on the clearing x 309..316, z 357..362.
"""
import json
import math
import os
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

BASE_REV = "406c75f6a8"
MAP_DIR = "res/field/mapmodels/data"
CELLS = {106: (9, 8), 107: (9, 9), 108: (9, 10), 109: (9, 11), 110: (9, 12), 111: (10, 12), 112: (11, 12)}
MODEL_BUFFER, BDHC_BUFFER = 0xF000, 0x9000
BLOCK = 0x8000
SNOW_DEEP, SNOW_SHALLOW = 0xA1, 0xA8

# showcase / event coordinates
TEO_MARKER = (317, 401)
TEO_STAND = (317, 402)
CAMP_EVENT = (312, 360)
CAMP_EVENT2 = (311, 360)
CAMP_STAND = (312, 361)
TEO_APPROACH = (315, 404)                  # walking up the Route 216 ledge, memorial ahead to the north-east
CAMP_APPROACH = (309, 364)                 # coming up the Route 217 snowfield from the south-west
G216, G217 = 2.0, 1.0

TEO_BLOCK = [(316, 401), (317, 401), (318, 401)]
TEO_PACKED = (315, 402, 320, 403)          # trampled approach (x0, z0, x1, z1 exclusive): shallow snow
CAMP_BLOCK = [(x, z) for x in range(313, 317) for z in range(360, 363)] + [(311, 360), (312, 360)]
CAMP_PACKED = (309, 357, 317, 363)

CAM = (0.0, 0.857, 0.515)


# ---------------------------------------------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------------------------------------------

def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(v):
    n = math.sqrt(dot(v, v)) or 1.0
    return tuple(c / n for c in v)


def face_n(pts):
    n = cross(sub(pts[1], pts[0]), sub(pts[2], pts[0]))
    if len(pts) == 4 and dot(n, n) < 1e-12:
        n = cross(sub(pts[2], pts[0]), sub(pts[3], pts[0]))
    return norm(n)


def hash01(*v):
    h = 2166136261
    for c in v:
        h = ((h ^ (int(c) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5BD1E995) & 0xFFFFFFFF
    return (h ^ (h >> 15)) / 4294967296.0


# material key -> (texture, lit, cull, polygon id). Translucent A3I5 materials get their own polygon ids so the
# hardware's same-id translucent rule never drops a glow where it overlaps a pool or a shadow.
MATS = {
    "rr_stone": ("r216_stone", True, "back", 0),
    "rr_offer": ("r216_offer", True, "none", 0),
    "rr_offer_u": ("r216_offer", False, "none", 0),
    "rr_glow": ("r216_glow", False, "none", 20),
    "rr_pool": ("r216_glow", False, "none", 21),
    "rr_poolv": ("r216_glow", False, "none", 22),
    "rr_shadow": ("r216_glow", False, "none", 23),
    "rr_tent": ("r217_tent", True, "back", 0),
    "rr_tent2": ("r217_tent", True, "none", 0),
    "rr_tent_u": ("r217_tent", False, "none", 0),
    "rr_camp": ("r217_camp", True, "back", 0),
    "rr_camp2": ("r217_camp", True, "none", 0),
    "rr_camp_u": ("r217_camp", False, "none", 0),
    "rr_clear": ("r217_camp", True, "none", 0),
}


def R(tex, key, sub_box=None):
    """Normalised UV box of an atlas region (optionally a texel sub-box inside it)."""
    x0, y0, x1, y1 = TX.REGIONS[tex][key]
    if sub_box:
        a, b, c, d = sub_box
        x0, y0, x1, y1 = x0 + a, y0 + b, x0 + c, y0 + d
    return (x0 / TX.N, y0 / TX.N, x1 / TX.N, y1 / TX.N)


class Builder(C.MeshBuilder):
    """MeshBuilder with per-vertex colours, facing correction and bookkeeping for the checks."""

    def __init__(self, table):
        super().__init__()
        self.table = table
        self.solids = []          # non-flat solid faces (absolute tiles)
        self.groups = {}

    def mat(self, key):
        tex, lit, cull, pid = MATS[key]
        self.material(key, tex, TX.pal_name(tex), self.table[tex]["size"], lights=1 if lit else 0, cull=cull,
                      polygon_id=pid)
        return key, lit

    def add(self, key, pts, uvs, facing=None, colors=None, group="misc", solid=True):
        pts = [tuple(float(c) for c in p) for p in pts]
        uvs = [tuple(u) for u in uvs]
        n = face_n(pts)
        if facing is not None and dot(n, facing) < 0:
            pts, uvs = pts[::-1], uvs[::-1]
            colors = colors[::-1] if colors else colors
            n = tuple(-c for c in n)
        name, lit = self.mat(key)
        me = self.meshes[name]
        b = len(me["positions"])
        me["positions"] += [list(p) for p in pts]
        me["uvs"] += [list(u) for u in uvs]
        cols = colors if (colors and not lit) else [(255, 255, 255)] * len(pts)
        me["colors"] += [list(c) for c in cols]
        me["normals"] += [list(n)] * len(pts)
        (me["quads"] if len(pts) == 4 else me["tris"]).append(list(range(b, b + len(pts))))
        self.groups[group] = self.groups.get(group, 0) + 1
        if solid and abs(n[1]) < 0.999:
            self.solids.append((pts, group))

    def quad(self, key, pts, box, facing, colors=None, group="misc", solid=True):
        """pts TL, TR, BR, BL as seen from the front; box = normalised UV (u0, v0, u1, v1)."""
        u0, v0, u1, v1 = box
        self.add(key, pts, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], facing, colors, group, solid)

    def box(self, key, x0, z0, x1, z1, h0, h1, uv, sides="swet", top_uv=None, colors=None, group="misc"):
        """Axis-aligned box; uv: box or {side: box}."""
        F = {"s": ([(x0, h1, z1), (x1, h1, z1), (x1, h0, z1), (x0, h0, z1)], (0, 0, 1)),
             "n": ([(x1, h1, z0), (x0, h1, z0), (x0, h0, z0), (x1, h0, z0)], (0, 0, -1)),
             "e": ([(x1, h1, z1), (x1, h1, z0), (x1, h0, z0), (x1, h0, z1)], (1, 0, 0)),
             "w": ([(x0, h1, z0), (x0, h1, z1), (x0, h0, z1), (x0, h0, z0)], (-1, 0, 0)),
             "t": ([(x0, h1, z0), (x1, h1, z0), (x1, h1, z1), (x0, h1, z1)], (0, 1, 0))}
        for s in sides:
            pts, n = F[s]
            bx = (top_uv if s == "t" and top_uv else (uv[s] if isinstance(uv, dict) else uv))
            cols = [colors(n, p) for p in pts] if colors else None
            self.quad(key, pts, bx, n, cols, group, solid=s != "t")

    def flat(self, key, x0, z0, x1, z1, h, box, colors=None, group="decal"):
        u0, v0, u1, v1 = box
        self.add(key, [(x0, h, z0), (x1, h, z0), (x1, h, z1), (x0, h, z1)], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)],
                 (0, 1, 0), colors, group, solid=False)

    def decal(self, key, cx, cz, w, l, ang, h, box, colors=None, group="decal"):
        """Flat quad centred (cx, cz), width w across, length l along heading ang (0 = north, v up = forward)."""
        u0, v0, u1, v1 = box
        fx, fz = math.sin(ang), -math.cos(ang)
        rx, rz = -fz, fx
        corner = lambda a, b: (cx + rx * a * w / 2 + fx * b * l / 2, h, cz + rz * a * w / 2 + fz * b * l / 2)  # noqa: E731
        self.add(key, [corner(-1, 1), corner(1, 1), corner(1, -1), corner(-1, -1)],
                 [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], (0, 1, 0), colors, group, solid=False)

    def card(self, key, cx, z, w, h0, h1, box, lean=0.0, colors=None, group="card", solid=True):
        """Upright card facing south at z, leaning back by `lean` radians (top moves north)."""
        dz = (h1 - h0) * math.tan(lean)
        self.quad(key, [(cx - w / 2, h1, z - dz), (cx + w / 2, h1, z - dz), (cx + w / 2, h0, z), (cx - w / 2, h0, z)],
                  box, (0, math.sin(lean), math.cos(lean)), colors, group, solid)

    def panel(self, key, region_box, p0, eu, ev, lu, lv, dens, facing, group="misc", solid=True):
        """Planar rectangle p0 + s*eu + t*ev (s in 0..lu, t in 0..lv tiles), split where the texel coordinate
        (dens texels per tile) wraps the region, so a region tiles across large faces. ev points DOWN the image."""
        u0, v0, u1, v1 = region_box
        rw, rh = (u1 - u0) * TX.N, (v1 - v0) * TX.N
        def cuts(L, size):
            out, s = [0.0], 0.0
            while s < L - 1e-6:
                nxt = min(L, (math.floor(s * dens / size + 1e-6) + 1) * size / dens)
                out.append(nxt)
                s = nxt
            return out
        su, sv = cuts(lu, rw), cuts(lv, rh)
        for i in range(len(su) - 1):
            for j in range(len(sv) - 1):
                a, b_, c, d = su[i], su[i + 1], sv[j], sv[j + 1]
                ta = (a * dens) % rw
                tc = (c * dens) % rh
                tb, td = ta + (b_ - a) * dens, tc + (d - c) * dens
                P = lambda s, t: tuple(p0[k] + eu[k] * s + ev[k] * t for k in range(3))  # noqa: E731
                self.quad(key, [P(a, c), P(b_, c), P(b_, d), P(a, d)],
                          (u0 + ta / TX.N, v0 + tc / TX.N, u0 + tb / TX.N, v0 + td / TX.N), facing, None, group, solid)


# ---------------------------------------------------------------------------------------------------------------
# Teo's Memorial Ridge (map_data_110)
# ---------------------------------------------------------------------------------------------------------------

def lathe(B, key, cx, cz, prof, segs, box, top_box=None, top_from=None, group="misc", ang0=0.0):
    """Low-poly rock / roof: profile [(r, h)], faces dropped when turned away from the camera."""
    ang = [ang0 + 2 * math.pi * j / segs for j in range(segs)]
    u0, v0, u1, v1 = box
    for i in range(len(prof) - 1):
        (ra, ha), (rb, hb) = prof[i], prof[i + 1]
        bx = top_box if (top_box and top_from is not None and i >= top_from) else box
        bu0, bv0, bu1, bv1 = bx
        for j in range(segs):
            a0, a1 = ang[j], ang[(j + 1) % segs]
            p = [(cx + rb * math.sin(a0), hb, cz + rb * math.cos(a0)), (cx + rb * math.sin(a1), hb, cz + rb * math.cos(a1)),
                 (cx + ra * math.sin(a1), ha, cz + ra * math.cos(a1)), (cx + ra * math.sin(a0), ha, cz + ra * math.cos(a0))]
            mid = ((a0 + a1) / 2)
            outward = (math.sin(mid), 0.4, math.cos(mid))
            uv = [(bu0 + (bu1 - bu0) * j / segs, bv0), (bu0 + (bu1 - bu0) * (j + 1) / segs, bv0),
                  (bu0 + (bu1 - bu0) * (j + 1) / segs, bv1), (bu0 + (bu1 - bu0) * j / segs, bv1)]
            if rb < 1e-6:
                p, uv = p[1:], uv[1:]
                p = [p[0], p[1], p[2]]
                p = [(cx, hb, cz), p[1], p[2]]
            n = face_n(p)
            if dot(n, outward) < 0:
                p, uv = p[::-1], uv[::-1]
                n = tuple(-c for c in n)
            if dot(n, CAM) < -0.3:
                continue
            B.add(key, p, uv, None, None, group)


CAM_UP = (0.0, CAM[2], -CAM[1])          # screen-up direction in the world (perpendicular to the view)


def billboard(B, key, cx, h, cz, w, hh, box, colors=None, group="glow"):
    """Quad centred at (cx, h, cz) facing the field camera (soft glows, blooms)."""
    up, half = CAM_UP, (w / 2, hh / 2)
    P = lambda a, b: (cx + a * half[0], h + b * half[1] * up[1], cz + b * half[1] * up[2])  # noqa: E731
    B.quad(key, [P(-1, 1), P(1, 1), P(1, -1), P(-1, -1)], box, CAM, colors, group, solid=False)


def pool(B, key, cx, cz, w, l, h, box, tint, clip=None, group="glow"):
    """Flat soft decal centred (cx, cz), w across x, l along z; clip = (x0, z0, x1, z1) keeps only that part with
    the UVs mapped proportionally (a light pool cut to a step top)."""
    x0, z0, x1, z1 = cx - w / 2, cz - l / 2, cx + w / 2, cz + l / 2
    u0, v0, u1, v1 = box
    if clip:
        a, b_, c, d = max(x0, clip[0]), max(z0, clip[1]), min(x1, clip[2]), min(z1, clip[3])
        if a >= c or b_ >= d:
            return
        U = lambda x: u0 + (u1 - u0) * (x - x0) / (x1 - x0)  # noqa: E731
        V = lambda z: v0 + (v1 - v0) * (z - z0) / (z1 - z0)  # noqa: E731
        x0, z0, x1, z1, u0, v0, u1, v1 = a, b_, c, d, U(a), V(b_), U(c), V(d)
    B.flat(key, x0, z0, x1, z1, h, (u0, v0, u1, v1), colors=[tint] * 4, group=group)


def wedge(B, key, x0, x1, z_lo, h_lo, z_hi, h_hi, box, group="drift"):
    """Snow drift wedge facing south: a sloped quad from the ground line (z_lo, h_lo) up to a step edge
    (z_hi, h_hi); the texture's top rows are the irregular crest."""
    B.quad(key, [(x0, h_hi, z_hi), (x1, h_hi, z_hi), (x1, h_lo, z_lo), (x0, h_lo, z_lo)], box, (0, 0.7, 0.7),
           group=group, solid=False)


def wedge_x(B, key, z0, z1, x_lo, h_lo, x_hi, h_hi, box, group="drift"):
    """Drift wedge on an east / west riser (x_lo on the ground, x_hi at the step edge)."""
    sgn = 1 if x_lo > x_hi else -1
    B.quad(key, [(x_hi, h_hi, z0), (x_hi, h_hi, z1), (x_lo, h_lo, z1), (x_lo, h_lo, z0)], box, (sgn * 0.7, 0.7, 0),
           group=group, solid=False)


# unlit offering tints: the scarf and wreath keep their colour by day and read as focal accents in the night snow
SCARF, WREATH, EMBLEM = (214, 206, 232), (206, 210, 216), (206, 210, 226)

# Teo's monolith (absolute tiles / heights above the G216 ground)
STELE = dict(cx=317.62, xb=0.56, xt=0.5, zf=401.72, depth_b=0.5, depth_t=0.38, hb=0.42, ht=2.56, lean=25.0)


def build_teo(B):
    S, O, GL = "r216_stone", "r216_offer", "r216_glow"
    G = G216
    snow, snow_side, step, step_top = R(S, "snow"), R(S, "snow_side"), R(S, "step"), R(S, "step_top")
    lant, post, roof, gran = R(S, "lantern"), R(S, "post"), R(S, "roof"), R(S, "granite")
    drift, mound, drip = R(O, "drift"), R(O, "mound"), R(O, "drip")
    shadow, amber, poolb = R(GL, "shadow"), R(GL, "amber"), R(GL, "pool")

    # soft contact shadows (A3I5) under the pedestal (spilling east, away from the light) and the lantern
    pool(B, "rr_shadow", 317.78, 401.6, 3.1, 1.6, G + 0.010, shadow, (255, 255, 255), group="shadow")
    pool(B, "rr_shadow", 316.26, 401.36, 0.85, 0.7, G + 0.011, shadow, (255, 255, 255), group="shadow")

    # stepped pedestal: two outlined granite steps with snow-dusted tops
    sx0, sz0, sx1, sz1, sh1 = 316.45, 401.06, 318.86, 401.98, 0.2
    tx0, tz0, tx1, tz1, sh2 = 316.8, 401.18, 318.5, 401.84, 0.42
    B.box("rr_stone", sx0, sz0, sx1, sz1, G, G + sh1, {"s": step, "e": step, "w": step}, sides="swet",
          top_uv=step_top, group="pedestal")
    B.box("rr_stone", tx0, tz0, tx1, tz1, G + sh1, G + sh2, {"s": step, "e": step, "w": step}, sides="swet",
          top_uv=step_top, group="pedestal")

    # the monolith: thick bevelled tapered shaft leaning back toward the cliff (so it rises tall on the DS camera)
    st = STELE
    cx, hb, ht = st["cx"], G + st["hb"], G + st["ht"]
    tl = math.tan(math.radians(st["lean"]))
    zf = st["zf"]
    fz = lambda h: zf - (h - hb) * tl                      # noqa: E731  front face z at height h
    hw = lambda h: st["xb"] + (st["xt"] - st["xb"]) * (h - hb) / (ht - hb)  # noqa: E731
    dp = lambda h: st["depth_b"] + (st["depth_t"] - st["depth_b"]) * (h - hb) / (ht - hb)  # noqa: E731
    fn = (0, math.sin(math.radians(st["lean"])), math.cos(math.radians(st["lean"])))
    B.quad("rr_stone", [(cx - hw(ht), ht, fz(ht)), (cx + hw(ht), ht, fz(ht)), (cx + hw(hb), hb, fz(hb)),
                        (cx - hw(hb), hb, fz(hb))], R(S, "stele"), fn, group="stele")
    side = R(S, "stele_side")
    for sgn in (-1, 1):
        B.quad("rr_stone", [(cx + sgn * hw(ht), ht, fz(ht) - dp(ht)), (cx + sgn * hw(ht), ht, fz(ht)),
                            (cx + sgn * hw(hb), hb, fz(hb)), (cx + sgn * hw(hb), hb, fz(hb) - dp(hb))][::-sgn],
               side if sgn < 0 else (side[2], side[1], side[0], side[3]), (sgn, 0, 0), group="stele")
    # crisp snow cap: outlined slab with a rounded mound, and a drip lip hanging over the face
    o = 0.045
    zF, zB = fz(ht) + 0.06, fz(ht) - dp(ht) - 0.04
    xa, xb_ = cx - hw(ht) - o, cx + hw(ht) + o
    hc0, hc1, hr = ht - 0.03, ht + 0.05, ht + 0.16
    B.box("rr_stone", xa, zB, xb_, zF, hc0, hc1, snow_side, sides="swe", group="cap")
    # pillow-shaped snow mound: raised inner top + four bevels running down to the slab edges
    i = 0.17
    ia, ib, iF, iB = xa + i, xb_ - i, zF - i * 0.6, zB + i * 0.6
    su0, sv0, su1, sv1 = snow
    inner = (su0 + 2 / 64, sv0 + 2 / 64, su1 - 2 / 64, sv0 + 10 / 64)
    B.flat("rr_stone", ia, iB, ib, iF, hr, inner, group="cap")
    zm_c = (iF + iB) / 2
    ring = [((xa, zF), (xb_, zF), (ib, iF), (ia, iF), (0, 0.7, 0.7)), ((xb_, zB), (xa, zB), (ia, iB), (ib, iB), (0, 0.7, -0.7)),
            ((xa, zB), (xa, zF), (ia, iF), (ia, iB), (-0.7, 0.7, 0)), ((xb_, zF), (xb_, zB), (ib, iB), (ib, iF), (0.7, 0.7, 0))]
    for (o0, o1, i1, i0, nrm) in ring:
        B.add("rr_stone", [(i0[0], hr, i0[1]), (i1[0], hr, i1[1]), (o1[0], hc1, o1[1]), (o0[0], hc1, o0[1])],
              [(su0, sv0), (su1, sv0), (su1, sv1), (su0, sv1)], nrm, group="cap", solid=False)
    # irregular c0 snow crest heaped along the front of the cap (breaks the rectangular silhouette)
    B.quad("rr_offer", [(xa - 0.02, hr + 0.06, zm_c), (xb_ + 0.02, hr + 0.06, zm_c), (xb_ + 0.02, hc1, zF + 0.01),
                        (xa - 0.02, hc1, zF + 0.01)], drift, (0, 0.8, 0.6), group="cap", solid=False)
    B.teo_height = hr + 0.06 - G
    hd = hc0 - 0.16
    B.quad("rr_offer", [(xa + 0.02, hc0 + 0.01, fz(hc0) + 0.075), (xb_ - 0.02, hc0 + 0.01, fz(hc0) + 0.075),
                        (xb_ - 0.02, hd, fz(hd) + 0.075), (xa + 0.02, hd, fz(hd) + 0.075)], drip, fn, group="cap",
           solid=False)

    # bold deep-violet knotted scarf round the upper shaft: front band, side wraps, knot at the south-east corner,
    # two fluttering tails hanging down the east flank
    sc, knot = R(O, "scarf"), R(O, "knot")
    h0, h1 = G + 2.0, G + 2.24
    off = 0.025
    B.quad("rr_offer_u", [(cx - hw(h1) - off, h1, fz(h1) + off), (cx + hw(h1) + off, h1, fz(h1) + off),
                        (cx + hw(h0) + off, h0, fz(h0) + off), (cx - hw(h0) - off, h0, fz(h0) + off)],
           sc, fn, [SCARF] * 4, group="scarf", solid=False)
    for sgn in (-1, 1):
        xs1, xs0 = cx + sgn * (hw(h1) + off), cx + sgn * (hw(h0) + off)
        B.quad("rr_offer_u", [(xs1, h1, fz(h1) - dp(h1) - off), (xs1, h1, fz(h1) + off), (xs0, h0, fz(h0) + off),
                            (xs0, h0, fz(h0) - dp(h0) - off)][::-sgn], sc, (sgn, 0, 0), [SCARF] * 4, group="scarf",
               solid=False)
    kh = (h0 + h1) / 2
    kx, kz = cx + hw(kh) - 0.02, fz(kh) + 0.04
    B.box("rr_offer_u", kx - 0.12, kz - 0.14, kx + 0.12, kz + 0.1, kh - 0.13, kh + 0.13, knot, sides="swet",
          colors=lambda n, p: SCARF, group="scarf")
    tail, tail2 = R(O, "tail"), R(O, "tail2")
    for (box_, x_top, dz, w_, ln, sway) in ((tail, kx + 0.08, 0.02, 0.17, 0.95, 0.14), (tail2, kx + 0.2, -0.06, 0.15,
                                                                                         0.78, 0.2)):
        ztop = kz + dz
        B.quad("rr_offer_u", [(x_top - w_ / 2, kh, ztop), (x_top + w_ / 2, kh, ztop),
                            (x_top + w_ / 2 + sway, kh - ln, ztop + 0.05), (x_top - w_ / 2 + sway, kh - ln, ztop + 0.05)],
               box_, (0, 0, 1), [SCARF] * 4, group="scarf", solid=False)

    # large evergreen & winter-blossom wreath leaning on the front step edges, bouquet on the west step
    B.card("rr_offer_u", 318.4, 402.05, 0.9, G, G + 0.9, R(O, "wreath"), lean=0.32, colors=[WREATH] * 4,
           group="offer", solid=False)
    B.card("rr_offer_u", 317.02, 401.95, 0.3, G + sh1, G + sh1 + 0.32, R(O, "bouquet"), lean=0.25,
           colors=[WREATH] * 4, group="offer", solid=False)

    # tall stone vigil lantern (~1.4 tiles) west of the pedestal with a warm unlit glass core + soft amber bloom
    lx, lz = 316.2, 401.3
    B.box("rr_stone", lx - 0.18, lz - 0.18, lx + 0.18, lz + 0.18, G, G + 0.13, lant, sides="swet", group="lantern")
    B.box("rr_stone", lx - 0.075, lz - 0.075, lx + 0.075, lz + 0.075, G + 0.13, G + 0.62, post, sides="swe",
          group="lantern")
    B.box("rr_stone", lx - 0.17, lz - 0.17, lx + 0.17, lz + 0.17, G + 0.62, G + 0.69, lant, sides="swet",
          group="lantern")
    warm = lambda n, p: (255, 250, 236) if n[2] > 0.5 else (255, 230, 186)  # noqa: E731
    B.box("rr_camp_u", lx - 0.125, lz - 0.125, lx + 0.125, lz + 0.125, G + 0.69, G + 1.02, R("r217_camp", "glass"),
          sides="swe", colors=warm, group="glow")
    for k in range(4):
        dx, dz = (-1 if k % 2 else 1) * 0.13, (-1 if k // 2 else 1) * 0.13
        B.box("rr_stone", lx + dx - 0.03, lz + dz - 0.03, lx + dx + 0.03, lz + dz + 0.03, G + 0.69, G + 1.02, post,
              sides="swe", group="lantern")
    lathe(B, "rr_stone", lx, lz, [(0.27, G + 1.02), (0.3, G + 1.07), (0.15, G + 1.2), (0.0, G + 1.28)], 4, roof,
          top_box=snow, top_from=1, group="lantern", ang0=math.pi / 4)
    B.box("rr_stone", lx - 0.035, lz - 0.035, lx + 0.035, lz + 0.035, G + 1.24, G + 1.36, post, sides="swe",
          group="lantern")
    lathe(B, "rr_stone", lx, lz, [(0.05, G + 1.36), (0.0, G + 1.41)], 4, snow, group="lantern", ang0=math.pi / 4)
    billboard(B, "rr_glow", lx, G + 0.86, lz - 0.08, 1.15, 1.15, amber, colors=[(255, 244, 220)] * 4)
    pool(B, "rr_pool", 316.3, 401.75, 1.9, 1.5, G + 0.016, poolb, (255, 206, 128))
    pool(B, "rr_pool", 316.3, 401.6, 1.9, 1.5, G + sh1 + 0.006, poolb, (255, 206, 128), clip=(sx0, sz0, sx1, sz1))

    # soft dithered snow drifts encroaching over the steps and heaped round the bases
    wedge(B, "rr_offer", 316.36, 317.32, 402.24, G + 0.0, 401.975, G + sh1, drift)
    wedge(B, "rr_offer", 317.7, 318.95, 402.22, G + 0.0, 401.975, G + sh1, drift)
    wedge(B, "rr_offer", 316.75, 317.35, 401.96, G + sh1, 401.835, G + sh2, drift)
    wedge(B, "rr_offer", 318.05, 318.55, 401.96, G + sh1, 401.835, G + sh2, drift)
    wedge_x(B, "rr_offer", 401.3, 401.99, 318.99, G + 0.0, sx1 - 0.005, G + sh1, drift)
    wedge_x(B, "rr_offer", 401.2, 401.83, sx1 - 0.02, G + sh1, tx1 - 0.005, G + sh2, drift)
    for (mx, mz, ms, mh) in ((316.62, 401.84, 0.4, sh1), (318.68, 401.22, 0.42, sh1), (316.98, 401.3, 0.34, sh2),
                             (318.36, 401.7, 0.3, sh2), (316.02, 401.6, 0.48, 0.0), (318.98, 401.5, 0.36, 0.0)):
        B.decal("rr_offer", mx, mz, ms, ms * 0.8, hash01(mx * 10, mz * 10) * 6.0, G + mh + 0.007, mound)

    # fresh boot prints walking in from the west, glinting violet shard dust in the snow beside them
    for (px, pz, ang) in ((313.3, 403.5, 1.2), (314.5, 403.05, 1.1), (315.55, 402.65, 0.95)):
        B.decal("rr_offer", px, pz, 0.45, 0.68, ang, G + 0.02, R(O, "prints"))
    B.decal("rr_offer_u", 316.75, 402.35, 0.85, 0.24, 1.35, G + 0.022, R(O, "dust"), colors=[(255, 255, 255)] * 4)
    B.decal("rr_offer_u", 315.2, 403.05, 0.7, 0.2, 0.4, G + 0.021, R(O, "dust"), colors=[(240, 230, 255)] * 4)


# ---------------------------------------------------------------------------------------------------------------
# Indra's Snowy Camp (map_data_109)
# ---------------------------------------------------------------------------------------------------------------

def build_camp(B):
    T, K, S, O, GL = "r217_tent", "r217_camp", "r216_stone", "r216_offer", "r216_glow"
    G = G217
    canvas, gable, flap = R(T, "canvas"), R(T, "gable"), R(T, "flap")
    rope, wood, rsnow = R(T, "rope"), R(T, "wood"), R(T, "ridge_snow")
    shadow, amber, violet, poolb = R(GL, "shadow"), R(GL, "amber"), R(GL, "violet"), R(GL, "pool")

    # packed-snow clearing: large dithered-rim patches blending into the fresh snow
    clear = R(K, "clear")
    for k, (px, pz, s) in enumerate(((311.0, 359.4, 3.3), (313.7, 358.9, 3.1), (309.9, 361.6, 2.9),
                                     (316.1, 359.0, 2.6), (311.9, 362.2, 2.4), (309.4, 358.6, 2.2))):
        B.decal("rr_clear", px, pz, s, s * 0.92, hash01(k, 7) * 6.28, G + 0.006 + 0.002 * k, clear, group="clear")
    # dark contact shadows under the tent and the crates
    pool(B, "rr_shadow", 315.0, 361.15, 3.95, 2.45, G + 0.018, shadow, (255, 255, 255), group="shadow")
    pool(B, "rr_shadow", 311.55, 360.62, 1.15, 0.95, G + 0.019, shadow, (255, 255, 255), group="shadow")
    pool(B, "rr_shadow", 312.55, 360.6, 1.05, 0.9, G + 0.019, shadow, (255, 255, 255), group="shadow")

    # pitched A-frame expedition tent, ridge north-south, open doorway gable facing south toward the camera
    tx0, tx1, tz0, tz1, rx = 313.25, 316.55, 360.1, 361.86, 314.9
    he, hr = G + 0.02, G + 1.9
    cu0, cv0, cu1, cv1 = canvas
    for sgn, ex, box_ in ((-1, tx0, canvas), (1, tx1, canvas)):
        u0, v0, u1, v1 = box_
        pts = [(rx, hr, tz1), (rx, hr, tz0), (ex, he, tz0), (ex, he, tz1)] if sgn > 0 else \
              [(rx, hr, tz0), (rx, hr, tz1), (ex, he, tz1), (ex, he, tz0)]
        uv = [(u1, v0), (u0, v0), (u0, v1), (u1, v1)] if sgn > 0 else [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        B.add("rr_tent", pts, uv, (sgn * 0.7, 0.7, 0), group="tent")
        # unlit pale-silver Eclipse emblem overlay, a hair above the canvas
        nx_, ny_ = sgn * 0.012, 0.012
        eu0, ev0, eu1, ev1 = R(T, "emblem")
        euv = [(eu1, ev0), (eu0, ev0), (eu0, ev1), (eu1, ev1)] if sgn > 0 else [(eu0, ev0), (eu1, ev0), (eu1, ev1), (eu0, ev1)]
        B.add("rr_tent_u", [(p[0] + nx_, p[1] + ny_, p[2]) for p in pts], euv, (sgn * 0.7, 0.7, 0), [EMBLEM] * 4,
              group="tent", solid=False)
        # heaped snow along the ridge (irregular dithered lower edge)
        ln = 0.42
        f = ln / math.hypot(ex - rx, hr - he)
        ox, oy = sgn * 0.025, 0.03
        q = [(rx + ox, hr + oy, tz0 - 0.03), (rx + ox, hr + oy, tz1 + 0.05), (rx + (ex - rx) * f + ox, hr - (hr - he) * f + oy,
             tz1 + 0.05), (rx + (ex - rx) * f + ox, hr - (hr - he) * f + oy, tz0 - 0.03)]
        u0, v0, u1, v1 = rsnow
        quv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        B.add("rr_tent2", q if sgn < 0 else [q[1], q[0], q[3], q[2]], quv if sgn < 0 else [quv[1], quv[0], quv[3], quv[2]],
              (sgn * 0.7, 0.7, 0), group="tent", solid=False)
    gu0, gv0, gu1, gv1 = gable
    B.add("rr_tent", [(rx, hr, tz1), (tx1, he, tz1), (tx0, he, tz1)], [((gu0 + gu1) / 2, gv0), (gu1, gv1), (gu0, gv1)],
          (0, 0, 1), group="tent")
    bu0, bv0, bu1, bv1 = R(T, "back")
    B.add("rr_tent", [(rx, hr, tz0), (tx0, he, tz0), (tx1, he, tz0)], [((bu0 + bu1) / 2, bv0), (bu0, bv1), (bu1, bv1)],
          (0, 0, -1), group="tent")
    # tied-back door flaps folded outward toward the camera (lighter lining), framing the dark doorway
    dh = G + (hr - G) * 0.75
    dw = (tx1 - tx0) / 2 * (6.5 / 16.0)
    fu0, fv0, fu1, fv1 = flap
    for sgn in (-1, 1):
        B.add("rr_tent2", [(rx, dh, tz1 + 0.01), (rx + sgn * dw, G + 0.02, tz1 + 0.01),
                           (rx + sgn * (dw + 0.32), G + 0.3, tz1 + 0.3)],
              [((fu0 + fu1) / 2, fv0), (fu1 if sgn > 0 else fu0, fv1), (fu0 if sgn > 0 else fu1, fv1 - 6 / 64)],
              (0, 0.3, 1), group="tent", solid=False)
    # ridge roll of snow + pole ends
    B.box("rr_stone", rx - 0.08, tz0 - 0.04, rx + 0.08, tz1 + 0.07, hr - 0.03, hr + 0.07, R(S, "snow_side"), sides="swe",
          top_uv=R(S, "snow"), group="tent")
    B.box("rr_tent", rx - 0.035, tz1 + 0.07, rx + 0.035, tz1 + 0.22, hr - 0.06, hr + 0.01, wood, sides="swet",
          group="tent")
    # staked guy ropes from the front apex and the gable corners
    for (ax, ah, az, bx, bz) in ((rx, hr - 0.05, tz1 + 0.18, 313.55, 362.85), (rx, hr - 0.05, tz1 + 0.18, 316.25, 362.85),
                                 (tx0 + 0.1, G + 0.35, tz1, 313.1, 362.6), (tx1 - 0.1, G + 0.35, tz1, 316.9, 362.6)):
        d = math.hypot(bx - ax, bz - az)
        nx, nz = -(bz - az) / d * 0.035, (bx - ax) / d * 0.035
        B.quad("rr_tent2", [(ax - nx, ah, az - nz), (ax + nx, ah, az + nz), (bx + nx, G + 0.08, bz + nz),
                            (bx - nx, G + 0.08, bz - nz)], rope, (0, 0.5, 0.5), group="tent", solid=False)
        B.box("rr_tent", bx - 0.035, bz - 0.035, bx + 0.035, bz + 0.035, G, G + 0.14, wood, sides="swe", group="tent")

    # supply crate with the expedition lantern (bright warm glass + amber bloom + light pool) and the journal
    crate, cside = R(K, "crate"), R(K, "crate_side")
    cx0, cz0, cx1, cz1, ch = 311.1, 360.22, 311.9, 360.86, G + 0.56
    B.box("rr_camp", cx0, cz0, cx1, cz1, G, ch, {"s": crate, "e": cside, "w": cside}, sides="swet", top_uv=cside,
          group="crate")
    lx, lz = 311.36, 360.5
    iron, glass = R(K, "iron"), R(K, "glass")
    B.box("rr_camp", lx - 0.13, lz - 0.13, lx + 0.13, lz + 0.13, ch, ch + 0.06, iron, sides="swet", group="lantern")
    gl = lambda n, p: (255, 252, 240) if n[2] > 0.5 else (255, 232, 190)  # noqa: E731
    B.box("rr_camp_u", lx - 0.105, lz - 0.105, lx + 0.105, lz + 0.105, ch + 0.06, ch + 0.4, glass, sides="swe",
          colors=gl, group="glow")
    B.box("rr_camp", lx - 0.13, lz - 0.13, lx + 0.13, lz + 0.13, ch + 0.4, ch + 0.45, iron, sides="swet",
          group="lantern")
    lathe(B, "rr_camp", lx, lz, [(0.11, ch + 0.45), (0.0, ch + 0.55)], 4, iron, group="lantern", ang0=math.pi / 4)
    B.quad("rr_camp2", [(lx - 0.08, ch + 0.66, lz), (lx + 0.08, ch + 0.66, lz), (lx + 0.08, ch + 0.55, lz),
                        (lx - 0.08, ch + 0.55, lz)], (iron[0], iron[1], iron[2], iron[1] + 2 / 64), (0, 0, 1),
           group="lantern", solid=False)
    B.flat("rr_camp", 311.56, 360.36, 311.86, 360.7, ch + 0.012, R(K, "journal"), group="crate")
    billboard(B, "rr_glow", lx, ch + 0.24, lz - 0.06, 1.3, 1.3, amber, colors=[(255, 244, 220)] * 4)
    pool(B, "rr_pool", 311.4, 361.25, 2.1, 1.7, G + 0.022, poolb, (255, 206, 128))

    # open Eclipse shard-scanner case on two stacked supply crates (so its lid rises above the player's head):
    # glowing electric-violet compass lid + violet bloom and pool
    lc = (crate[0], crate[1] + 6 / 64, crate[2], crate[3])
    sx0, sz0, sx1, sz1, sh0 = 312.12, 360.18, 312.88, 360.84, G + 0.44
    B.box("rr_camp", sx0, sz0, sx1, sz1, G, sh0, {"s": lc, "e": cside, "w": cside}, sides="swet", top_uv=cside,
          group="crate")
    sh = sh0 + 0.34
    B.box("rr_camp", 312.2, 360.26, 312.8, 360.78, sh0, sh, {"s": lc, "e": cside, "w": cside}, sides="swet",
          top_uv=cside, group="crate")
    B.box("rr_camp", 312.24, 360.36, 312.76, 360.72, sh, sh + 0.11, R(K, "case"), sides="swet", group="scanner")
    vio = [(255, 255, 255)] * 4
    B.card("rr_camp_u", 312.5, 360.38, 0.52, sh + 0.11, sh + 0.56, R(K, "screen"), lean=0.3, colors=vio,
           group="glow", solid=False)
    B.card("rr_camp_u", 312.82, 360.7, 0.12, sh + 0.11, sh + 0.28, R(K, "shard"), lean=0.1,
           colors=[(240, 228, 255)] * 4, group="glow", solid=False)
    billboard(B, "rr_glow", 312.5, sh + 0.34, 360.3, 1.15, 1.15, violet, colors=[(255, 255, 255)] * 4)
    pool(B, "rr_poolv", 312.55, 361.2, 1.5, 1.2, G + 0.024, poolb, (196, 150, 255))
    # boot prints leading away south-west
    for k, (px, pz) in enumerate(((309.6, 363.4), (308.9, 364.6), (308.3, 365.9))):
        B.decal("rr_offer", px, pz, 0.45, 0.68, 3.6, G + 0.02, R(O, "prints"))


# ---------------------------------------------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------------------------------------------

def rel(c):
    return f"{MAP_DIR}/map_data_{c:03d}.bin"


def build():
    tex = TX.build_set()
    table = tex["table"]
    out = {}
    for c, fn in ((110, build_teo), (109, build_camp)):
        edit = C.ChunkEdit(rel(c), CELLS[c], BASE_REV)
        info = {}
        B = Builder(table)
        fn(B)
        edit.add(B, table)
        model = edit.model_bytes()
        perm = edit.permissions()
        cx, cz = CELLS[c]
        if c == 110:
            for (x, z) in TEO_BLOCK:
                perm[z - cz * 32][x - cx * 32] = BLOCK
            x0, z0, x1, z1 = TEO_PACKED
            for x in range(x0, x1):
                for z in range(z0, z1):
                    v = perm[z - cz * 32][x - cx * 32]
                    if not v & BLOCK and (v & 0xFF) == SNOW_DEEP:
                        perm[z - cz * 32][x - cx * 32] = SNOW_SHALLOW
        else:
            for (x, z) in CAMP_BLOCK:
                perm[z - cz * 32][x - cx * 32] = BLOCK | SNOW_DEEP
            x0, z0, x1, z1 = CAMP_PACKED
            for x in range(x0, x1):
                for z in range(z0, z1):
                    v = perm[z - cz * 32][x - cx * 32]
                    if not v & BLOCK and (v & 0xFF) == SNOW_DEEP:
                        perm[z - cz * 32][x - cx * 32] = SNOW_SHALLOW
        data = edit.pack(perm, model)
        out[c] = dict(edit=edit, builder=B, model=model, perm=perm, data=data, info=info, stats=edit.stats(model))
    return out, tex


# ---------------------------------------------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------------------------------------------

def git_bytes(rev, path):
    return subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{path}"], check=True, capture_output=True).stdout


def global_perm(datas):
    """{(x, z): u16} over all seven chunks; datas: {chunk: map_data bytes}."""
    g = {}
    for c, (cx, cz) in CELLS.items():
        p = mapdata.read_permissions(mapdata.unpack(datas[c])["permissions"])
        for z in range(32):
            for x in range(32):
                g[(cx * 32 + x, cz * 32 + z)] = p[z][x]
    return g


def components(g):
    walk = {k for k, v in g.items() if not v & BLOCK}
    comp, cid = {}, 0
    for s in walk:
        if s in comp:
            continue
        stack = [s]
        comp[s] = cid
        while stack:
            x, z = stack.pop()
            for n in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
                if n in walk and n not in comp:
                    comp[n] = cid
                    stack.append(n)
        cid += 1
    return comp


def events():
    ev = []
    for r in ("route_216", "route_217"):
        e = json.load(open(os.path.join(ROOT, "res/field/maps", r, "events.json")))
        for o in e["object_events"]:
            ev.append((r, o["id"], o["x"], o["z"], "obj"))
        for w in e["warp_events"]:
            ev.append((r, w["id"], w["x"], w["z"], "warp"))
        for b in e["bg_events"]:
            ev.append((r, b.get("script") or b.get("hidden_item"), b["x"], b["z"], "bg"))
        for c in e["coord_events"]:
            ev.append((r, c["script"], c["x"], c["z"], "coord"))
    return ev


def reach_checks(out):
    res = []
    stock = {c: git_bytes(BASE_REV, rel(c)) for c in CELLS}
    new = dict(stock)
    for c, o in out.items():
        new[c] = o["data"]
    gs, gn = global_perm(stock), global_perm(new)
    newly = sorted(k for k in gs if not gs[k] & BLOCK and gn[k] & BLOCK)
    expected = sorted(set(TEO_BLOCK) | set(CAMP_BLOCK))
    res.append((f"newly blocked tiles are exactly the landmark footprints ({len(newly)} tiles)",
                set(newly) <= set(expected)))
    opened = [k for k in gs if gs[k] & BLOCK and not gn[k] & BLOCK]
    res.append((f"no stock-blocked tile opened ({len(opened)})", not opened))
    cs, cn = components(gs), components(gn)
    split = []
    groups = {}
    for k, ci in cs.items():
        if k in cn:
            groups.setdefault(ci, set()).add(cn[k])
    split = [ci for ci, s in groups.items() if len(s) > 1]
    res.append((f"no stock walkable region split by the landmarks ({len(groups)} regions, {len(split)} split)", not split))
    bad = []
    ours = {"Route216_TeoMemorial", "Route217_IndraCamp"}      # new landmark events: standing tiles checked below
    for r, name, x, z, kind in events():
        if name in ours:
            continue
        if (x, z) in set(newly):
            bad.append((name, x, z))
            continue
        nb = [(x, z), (x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)]
        ok_s = [cs.get(t) for t in nb if t in cs]
        ok_n = [cn.get(t) for t in nb if t in cn]
        if len(ok_s) != len(ok_n):
            bad.append((name, x, z))
    res.append((f"every Route 216/217 object, warp, bg and coord event keeps its tile and walkable neighbours "
                f"({len(events())} events; bad: {bad[:4]})", not bad))
    s_ok = not gn[TEO_STAND] & BLOCK and gn[TEO_MARKER] & BLOCK and cn.get(TEO_STAND) == cn.get((375, 404))
    res.append((f"Teo's marker {TEO_MARKER} blocked, standing tile {TEO_STAND} walkable and connected to the Mt. Coronet "
                f"exit path", s_ok))
    c_ok = not gn[CAMP_STAND] & BLOCK and gn[CAMP_EVENT] & BLOCK and cn.get(CAMP_STAND) == cn.get((304, 383)) \
        and cn.get(CAMP_STAND) == cn.get((300, 300)) and cn.get(CAMP_STAND) == cn.get((310, 262))
    res.append((f"Indra's scanner crate {CAMP_EVENT} blocked, standing tile {CAMP_STAND} walkable and connected to the "
                f"Route 216 seam and the Route 217 north field", c_ok))
    for c in CELLS:
        if c not in out:
            res.append((f"chunk {c}: untouched, work tree byte-identical to {BASE_REV}",
                        open(os.path.join(ROOT, rel(c)), "rb").read() == stock[c]))
    return res


def mesh_faces(model, cell):
    mesh = nsbmd.model_to_mesh(model, cell)
    for me in mesh["meshes"]:
        P = me["positions"]
        for f in me["quads"] + me["tris"]:
            yield me["material"], [P[i] for i in f]


def pip(px, pz, poly):
    inside, n = False, len(poly)
    for i in range(n):
        (x0, z0), (x1, z1) = poly[i], poly[(i + 1) % n]
        if (z0 > pz) != (z1 > pz) and px < x0 + (pz - z0) * (x1 - x0) / (z1 - z0):
            inside = not inside
    return inside


def chunk_checks(c, o, tex):
    res = []
    edit, B = o["edit"], o["builder"]
    sec = mapdata.unpack(o["data"])
    stock_sec = mapdata.unpack(git_bytes(BASE_REV, rel(c)))
    res.append((f"chunk {c}: model {len(o['model'])} B <= 0xF000 (stock {len(stock_sec['model'])} B)",
                len(o["model"]) <= MODEL_BUFFER))
    res.append((f"chunk {c}: BDHC {len(sec['bdhc'])} B <= 0x9000 and identical to stock (heights unchanged)",
                len(sec["bdhc"]) <= BDHC_BUFFER and sec["bdhc"] == stock_sec["bdhc"]))
    res.append((f"chunk {c}: props identical to stock ({len(sec['props']) // 48})", sec["props"] == stock_sec["props"]))
    back = nsbmd.parse_bmd(o["model"])
    res.append((f"chunk {c}: NSBMD parse -> rebuild byte-identical", nsbmd.build_bmd(back["models"]) == o["model"]))
    edited = {edit.model["shapes"][si]["name"] for si in edit.faces}
    bad = C.stock_shapes_identical(edit.model, edit.built, edited)
    res.append((f"chunk {c}: untouched stock shapes + all stock materials byte-identical (re-encoded: {sorted(edited)})",
                not bad))
    s = nsbtx.parse(tex["bytes"])
    T = {t["name"]: t for t in s["textures"]}
    P = {p["name"] for p in s["palettes"]}
    badm = [m["name"] for m in back["models"][0]["materials"] if m["texture"] not in T or m["palette"] not in P
            or (T[m["texture"]]["w"], T[m["texture"]]["h"]) != (m["orig_width"], m["orig_height"])]
    res.append((f"chunk {c}: every material's texture + palette in set 080 with matching size (bad {badm})", not badm))
    # floor + clearance over the walkable tiles of the edited area
    cx, cz = CELLS[c]
    b = mapdata.read_bdhc(sec["bdhc"])
    perm = o["perm"]
    area = (313, 399, 321, 406) if c == 110 else (307, 355, 319, 367)
    floors = {}
    for mat, vs in mesh_faces(back["models"][0], (cx, cz)):
        if max(v[1] for v in vs) - min(v[1] for v in vs) > 1e-3:
            continue
        for tx in range(area[0], area[2]):
            for tz in range(area[1], area[3]):
                if pip(tx + 0.5, tz + 0.5, [(v[0], v[2]) for v in vs]):
                    floors.setdefault((tx, tz), []).append(vs[0][1])
    off, low = [], []
    for tx in range(area[0], min(area[2], cx * 32 + 32)):
        for tz in range(area[1], area[3]):
            if perm[tz - cz * 32][tx - cx * 32] & BLOCK:
                continue
            want = mapdata.height_at(b, *mapdata.tile_centre(tx - cx * 32, tz - cz * 32)) / 4096 / 16 - 1
            hs = [h for h in floors.get((tx, tz), []) if h <= want + 0.06]
            if not hs or abs(max(hs) - want) > 0.03:
                off.append((tx, tz))
    res.append((f"chunk {c}: every walkable tile in the edited area drawn at its BDHC height (off {off[:6]})", not off))
    for pts, grp in B.solids:
        for x, h, z in pts + [tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))]:
            tx, tz = math.floor(x), math.floor(z)
            if cx * 32 <= tx < cx * 32 + 32 and cz * 32 <= tz < cz * 32 + 32 and not perm[tz - cz * 32][tx - cx * 32] & BLOCK \
                    and 0.1 < x - tx < 0.9 and 0.1 < z - tz < 0.9:
                low.append((tx, tz, grp))
    res.append((f"chunk {c}: nothing solid drawn inside a walkable tile ({sorted(set(low))[:6]})", not low))
    if c == 110:
        th = B.teo_height
        res.append((f"chunk 110: Teo's monolith {th:.2f} tiles tall to the top of its snow cap (2.4 .. 2.8)",
                    2.4 <= th <= 2.8))
    return res


# ---------------------------------------------------------------------------------------------------------------
# lighting_set_008: crisp melancholic alpine blue-silver day, serene moonlit snow at night
# ---------------------------------------------------------------------------------------------------------------

LIGHTING_REL = "res/field/lighting/lighting_set_008.json"
# (light 0, diffuse, ambient, specular, emission). Day: brighter key light and lower emission than v1, so the shaded
# sides of the dark-violet tent and the carved grey stone keep their contrast against the snow. Night: clear moonlit
# indigo (blue key light, low emission) that leaves the unlit amber / violet lanterns as the warm focal points.
NIGHT = ((10, 12, 21), (14, 14, 18), (9, 10, 14), (14, 15, 18), (7, 8, 12))
LIGHT_CURVE = {
    0: NIGHT, 7200: NIGHT,                                                               # 00:00-04:00 moonlit snow
    8100: ((12, 13, 21), (12, 12, 16), (11, 11, 15), (10, 10, 15), (9, 9, 13)),          # pre-dawn steel blue
    9000: ((15, 15, 22), (13, 13, 15), (10, 10, 13), (12, 12, 15), (11, 11, 14)),        # cold blue dawn
    14400: ((21, 22, 25), (15, 15, 16), (9, 10, 11), (14, 14, 16), (12, 12, 14)),        # silver morning
    20700: ((25, 26, 28), (16, 16, 17), (9, 10, 11), (15, 15, 16), (11, 12, 13)),        # crisp alpine day
    21600: ((27, 28, 30), (17, 17, 18), (9, 10, 12), (16, 16, 17), (11, 11, 13)),        # bright blue-white noon
    27000: ((27, 27, 29), (17, 17, 18), (9, 10, 12), (17, 17, 18), (11, 11, 13)),        # blue-white afternoon
    27900: ((24, 24, 27), (16, 16, 17), (10, 10, 12), (16, 16, 17), (11, 11, 13)),
    30600: ((21, 20, 24), (15, 15, 16), (11, 11, 13), (16, 16, 17), (11, 11, 13)),       # pale lavender light
    32400: ((19, 17, 22), (14, 14, 16), (11, 11, 13), (15, 15, 17), (9, 9, 12)),         # melancholic dusk
    33300: ((16, 15, 22), (14, 14, 16), (10, 11, 14), (15, 15, 17), (8, 8, 12)),         # violet-blue twilight
    34200: ((14, 15, 22), (14, 14, 17), (10, 11, 14), (14, 14, 17), (8, 8, 12)),         # serene twilight snow
    36000: ((11, 13, 21), (14, 14, 18), (9, 10, 14), (14, 15, 18), (7, 8, 12)),          # moonrise
    43200: NIGHT,
}


def build_lighting():
    raw = git_bytes(BASE_REV, LIGHTING_REL).decode()
    tmpl = json.loads(raw)
    out = json.loads(raw)
    fails = []
    rgb = lambda c: {"red": c[0], "green": c[1], "blue": c[2]}  # noqa: E731
    for blk in out:
        cur = LIGHT_CURVE.get(blk["endTime"])
        if cur is None:
            fails.append(f"lighting: no curve entry for endTime {blk['endTime']}")
            continue
        blk["lights"][0]["color"] = rgb(cur[0])
        for key, col in zip(("diffuseColor", "ambientColor", "specularColor", "emissionColor"), cur[1:]):
            blk[key] = rgb(col)
    text = json.dumps(out, indent=4) + "\n"
    back = json.loads(text)
    if [list(b.keys()) for b in back] != [list(b.keys()) for b in tmpl] or [b["endTime"] for b in back] != \
            [b["endTime"] for b in tmpl]:
        fails.append("lighting: schema / block times differ from stock")
    for i, b in enumerate(back):
        cols = [b[k] for k in ("diffuseColor", "ambientColor", "specularColor", "emissionColor")] + [lt["color"] for lt in b["lights"]]
        if any(not isinstance(v, int) or not 0 <= v <= 31 for c in cols for v in c.values()):
            fails.append(f"lighting: colour out of range at {b['endTime']}")
        if [lt["direction"] for lt in b["lights"]] != [lt["direction"] for lt in tmpl[i]["lights"]] or \
                b["lights"][1:] != tmpl[i]["lights"][1:]:
            fails.append(f"lighting: directions or lights 1..3 changed at {b['endTime']}")
    return text, fails


# ---------------------------------------------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------------------------------------------

# name: (camera target tile, ground height, player stand-in (x, z) or None, zoom). Field-camera distance (zoom 1, the
# CAMERA_TYPE_DEFAULT pitch / distance / FOV) and close-ups.
VIEWS = {"teo": (TEO_STAND, G216, TEO_STAND, 1.0), "teo_approach": (TEO_APPROACH, G216, TEO_APPROACH, 1.0),
         "teo_close": ((317, 401.6), G216 + 0.6, TEO_STAND, 2.4),
         "camp": (CAMP_STAND, G217, CAMP_STAND, 1.0), "camp_approach": (CAMP_APPROACH, G217, CAMP_APPROACH, 1.0),
         "camp_close": ((313.2, 360.9), G217 + 0.4, CAMP_STAND, 2.2)}


def write_preview(d, out, tex):
    import preview
    os.makedirs(d, exist_ok=True)
    TX.write_preview(os.path.join(d, "tex"), tex["generated"])
    models = []
    for c in CELLS:
        if c in out:
            models.append((out[c]["edit"].built, CELLS[c]))
        else:
            models.append((nsbmd.parse_bmd(mapdata.unpack(git_bytes(BASE_REV, rel(c)))["model"])["models"][0], CELLS[c]))
    for name, (t, h, pl, zoom) in VIEWS.items():
        for night in (False, True):
            preview.render(models, tex["bytes"], t, os.path.join(d, f"{'night' if night else 'day'}_{name}.png"),
                           target_h=h, night=night, zoom=zoom, player=(pl[0], pl[1], h) if pl else None)


def main():
    out, tex = build()
    res = []
    for c, o in out.items():
        st = o["stats"]
        print(f"map_data_{c}: model {st['stock_model_bytes']} -> {st['model_bytes']} B, polygons "
              f"{st['stock_polygons']} -> {st['polygons']}, materials {st['materials']}, new faces "
              f"{o['builder'].polygons()} {o['builder'].groups}, {o['info']}")
        res += chunk_checks(c, o, tex)
    res += reach_checks(out)
    for f in tex["fails"]:
        res.append(("set 080: " + f, False))
    vb, vo = tex["vram"]
    res.append((f"set 080: stock 014 + {len(tex['rows'])} atlases (A3I5 glow incl.) round-trip, VRAM {sum(vo)} B ({sum(vo) / 1024:.1f} KB) < 160 KB",
                not tex["fails"]))
    ltext, lf = build_lighting()
    res += [(f, False) for f in lf]
    res.append(("lighting_set_008: stock schema, block times, directions and lights 1..3; 5-bit colours", not lf))
    ok = True
    for desc, good in res:
        print(("PASS " if good else "FAIL ") + desc)
        ok &= bool(good)
    print(f"showcase: Teo's Memorial Ridge stand {TEO_STAND} facing north at marker {TEO_MARKER}; "
          f"Indra's camp stand {CAMP_STAND} facing north at {CAMP_EVENT}")
    if "--preview" in sys.argv:
        d = sys.argv[sys.argv.index("--preview") + 1]
        write_preview(d, out, tex)
        print("wrote previews to", d)
    if "--write" in sys.argv:
        if not ok:
            print("refusing to write: checks failed")
            return 1
        for c, o in out.items():
            open(os.path.join(ROOT, rel(c)), "wb").write(o["data"])
        open(os.path.join(ROOT, TX.SET_REL), "wb").write(tex["bytes"])
        open(os.path.join(ROOT, LIGHTING_REL), "w").write(ltext)
        print("wrote", ", ".join(rel(c) for c in out), TX.SET_REL, LIGHTING_REL)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
