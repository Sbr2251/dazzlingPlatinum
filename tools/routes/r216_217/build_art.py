#!/usr/bin/env python3
"""Routes 216-217 art pass: Teo's Memorial Ridge (map_data_110) and Indra's Snowy Camp (map_data_109), surgical
edits of the stock chunks (tools/world_art/chunkedit.py), the set-080 atlases (textures.py) and lighting_set_008.

Usage (Python with NumPy; PIL for --preview):
  ~/.venvs/desmume/bin/python tools/routes/r216_217/build_art.py                 dry run: build + every check
  ~/.venvs/desmume/bin/python tools/routes/r216_217/build_art.py --preview DIR   also field-camera renders
  ~/.venvs/desmume/bin/python tools/routes/r216_217/build_art.py --write         write map_data_109/110, set 080,
                                                                                lighting_set_008 (refuses on FAIL)

Inputs are read from git at BASE_REV (stock chunks, lighting) and HEAD (stock set 014), so reruns never feed back.
Chunks 106, 107, 108, 111, 112 are not touched (checked byte-identical to BASE_REV).

Teo's Memorial Ridge, map_data_110, on the Route 216 cliff ledge (h 2, x 309..319, z 401..405) facing south toward
Mt. Coronet: the lowest stock cliff terrace (criffp, z 400..401) is cut between x 316 and 319 and replaced by a
carved granite retaining wall with a snow-capped coping and two flanking posts; slate-flag paving (x 315..320,
z 401..403) replaces the snow ground; on it a two-step plinth carrying Teo's stele (snow-capped gable, carved
mountain-and-falling-star emblem, inlaid dark plaque "TEO" with engraved lines, a violet scarf tied round it), the
frozen winter-flower wreath and bouquet, a vigil candle, a stone vigil lantern with warm unlit glass and an amber
light pool, a small snow-capped cairn, fresh boot prints and a faint trace of violet shard dust.
Blocked: (316..318, 401). Standing tile: (317, 402) facing north. Paving tiles get behaviour 0 (no deep snow).

Indra's Snowy Camp, map_data_109, in the sheltered north-east corner of the Route 217 snowfield (backed by the tree
mass at z 363+): a pitched dark-violet expedition tent (x 313..317, z 360..362) with a snow-dusted ridge pole,
gable flap with the faded eclipse sigil and guy ropes, a supply crate with a warm glowing expedition lantern and
the field journal (311, 360), the Eclipse shard-scanner case open on a low crate (312, 360) with its violet compass
screen and a faint violet trace on the snow pointing south toward Mt. Coronet, packed-snow footprint rings.
Blocked: (313..316, 360..362), (311..312, 360). Packed snow (behaviour 0xA8) on the clearing x 309..316, z 357..362.
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
G216, G217 = 2.0, 1.0

TEO_BLOCK = [(316, 401), (317, 401), (318, 401)]
TEO_PAVE = (315, 401, 320, 403)            # x0, z0, x1, z1 (exclusive)
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


# material key -> (texture, lit, cull)
MATS = {
    "rr_stone": ("r216_stone", True, "back"),
    "rr_offer": ("r216_offer", True, "none"),
    "rr_offer_u": ("r216_offer", False, "none"),
    "rr_tent": ("r217_tent", True, "back"),
    "rr_tent2": ("r217_tent", True, "none"),
    "rr_camp": ("r217_camp", True, "back"),
    "rr_camp2": ("r217_camp", True, "none"),
    "rr_camp_u": ("r217_camp", False, "none"),
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
        tex, lit, cull = MATS[key]
        self.material(key, tex, TX.pal_name(tex), self.table[tex]["size"], lights=1 if lit else 0, cull=cull)
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
# stock cliff cut (split faces at vertical planes x = lo / hi, keep the outside parts)
# ---------------------------------------------------------------------------------------------------------------

def _lerp_v(edit, a, b, t):
    pos = tuple(round(a["pos"][k] + (b["pos"][k] - a["pos"][k]) * t) for k in range(3))
    uv = tuple(round(a["uv"][k] + (b["uv"][k] - a["uv"][k]) * t) for k in range(2)) if a["uv"] else a["uv"]
    return dict(a, pos=pos, uv=uv)


def _clip(edit, poly, x, keep_less):
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        xa, xb = edit.tile(a["pos"])[0], edit.tile(b["pos"])[0]
        ina = (xa <= x + 1e-6) if keep_less else (xa >= x - 1e-6)
        inb = (xb <= x + 1e-6) if keep_less else (xb >= x - 1e-6)
        if ina:
            out.append(a)
        if ina != inb:
            t = (x - xa) / (xb - xa)
            out.append(_lerp_v(edit, a, b, t))
    return out


def cut_cliff(edit, textures, zr, lo, hi):
    """Faces of `textures` whose centroid z is in zr: remove the part with lo < x < hi."""
    n_cut = 0
    for si, tex, pal in list(edit.iter_shapes()):
        if tex not in textures:
            continue
        tris, quads = edit._faces(si)
        nt, nq, changed = [], [], False
        for f in list(tris) + list(quads):
            pts = [edit.tile(v["pos"]) for v in f]
            cz = sum(p[2] for p in pts) / len(pts)
            xs = [p[0] for p in pts]
            if not (zr[0] <= cz <= zr[1]) or max(xs) <= lo + 1e-6 or min(xs) >= hi - 1e-6:
                (nt if len(f) == 3 else nq).append(f)
                continue
            changed = True
            n_cut += 1
            for part in (_clip(edit, list(f), lo, True), _clip(edit, list(f), hi, False)):
                pp = [edit.tile(v["pos"]) for v in part]
                if len(part) < 3 or max(p[0] for p in pp) - min(p[0] for p in pp) < 1e-4:
                    continue
                if len(part) == 3:
                    nt.append(tuple(part))
                elif len(part) == 4:
                    nq.append(tuple(part))
                else:
                    for k in range(1, len(part) - 1):
                        nt.append((part[0], part[k], part[k + 1]))
        if changed:
            edit.faces[si] = (nt, nq)
        elif si in edit.faces and edit.faces[si] == (list(tris), list(quads)):
            del edit.faces[si]
    return n_cut


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


def build_teo(B):
    S = "r216_stone"
    G = G216
    side, gran, slate, snow, coping, stele = (R(S, k) for k in ("side", "granite", "slate", "snow", "coping", "stele"))
    cairn = R(S, "cairn")
    # retaining wall (x 316..319) in the cut terrace, face at z 400.92, coping and snow on top
    WZ = 400.92
    B.panel("rr_stone", gran, (316.0, G + 1.0, WZ), (1, 0, 0), (0, -1, 0), 3.0, 1.0, 16, (0, 0, 1), group="wall")
    B.flat("rr_stone", 316.0, 400.0, 319.0, WZ, G + 1.0, (snow[0], snow[1], snow[2], snow[1] + 4 / 64), group="wall")
    B.box("rr_stone", 315.95, WZ - 0.02, 319.05, WZ + 0.08, G + 0.92, G + 1.04, coping, sides="swe",
          top_uv=(snow[0], snow[1], snow[2], snow[1] + 2 / 64), group="wall")
    B.flat("rr_stone", 315.95, WZ - 0.02, 319.05, WZ + 0.08, G + 1.04, (snow[0], snow[1], snow[2], snow[1] + 2 / 64),
           group="wall")
    # flanking posts with snow caps (hide the cut ends of the stock cliff)
    for px in (316.0, 319.0):
        B.box("rr_stone", px - 0.2, 400.55, px + 0.2, 401.0, G, G + 1.22, gran, sides="swe", group="wall")
        B.box("rr_stone", px - 0.24, 400.51, px + 0.24, 401.04, G + 1.22, G + 1.3, coping, sides="swe", group="wall",
              top_uv=snow)
        B.flat("rr_stone", px - 0.24, 400.51, px + 0.24, 401.04, G + 1.3, snow, group="wall")
        lathe(B, "rr_stone", px, 400.78, [(0.2, G + 1.3), (0.15, G + 1.38), (0.0, G + 1.43)], 6, snow, group="wall",
              ang0=math.pi / 6)
    # slate paving (stock snow ground clipped there), 1 slab per tile, and a low carved kerb on the open edges
    x0, z0, x1, z1 = TEO_PAVE
    B.panel("rr_stone", slate, (x0, G, z0), (1, 0, 0), (0, 0, 1), x1 - x0, z1 - z0, 16, (0, 1, 0), group="pave",
            solid=False)
    B.box("rr_stone", x0, z1 - 0.08, x1, z1, G, G + 0.05, side, sides="st", group="kerb", top_uv=(side[0], side[1], side[2], side[1] + 1 / 64))
    B.box("rr_stone", x0, z0, x0 + 0.08, z1 - 0.08, G, G + 0.05, side, sides="wt", group="kerb")
    # plinth: two steps
    B.box("rr_stone", 316.18, 401.06, 318.82, 401.94, G, G + 0.12, side, sides="swet", group="plinth",
          top_uv=(side[0], side[1], side[2], side[1] + 6 / 64))
    B.box("rr_stone", 316.62, 401.14, 318.38, 401.8, G + 0.12, G + 0.26, side, sides="swet", group="plinth",
          top_uv=(side[0], side[1], side[2], side[1] + 5 / 64))
    # the stele: tapered slab leaning back 14 degrees toward the camera, gable top, plaque face to the south
    hb, ht, hp = G + 0.26, G + 2.05, G + 2.3
    xb, xt, zf, zb = 0.45, 0.39, 401.6, 401.38
    cx = 317.5
    tl = math.tan(math.radians(14))
    T = lambda p: (p[0], p[1], p[2] - (p[1] - hb) * tl)  # noqa: E731
    fn = (0, math.sin(math.radians(14)), math.cos(math.radians(14)))
    su0, sv0, su1, sv1 = stele
    vt = sv0 + (sv1 - sv0) * ((hp - ht) / (hp - hb))
    ul, ur = su0 + (su1 - su0) * (0.5 - xt / (2 * xb)), su0 + (su1 - su0) * (0.5 + xt / (2 * xb))
    B.add("rr_stone", [T(p) for p in [(cx - xt, ht, zf), (cx + xt, ht, zf), (cx + xb, hb, zf), (cx - xb, hb, zf)]],
          [(ul, vt), (ur, vt), (su1, sv1), (su0, sv1)], fn, group="stele")
    B.add("rr_stone", [T(p) for p in [(cx, hp, zf), (cx + xt, ht, zf), (cx - xt, ht, zf)]],
          [((su0 + su1) / 2, sv0), (ur, vt), (ul, vt)], fn, group="stele")
    for sgn in (-1, 1):
        B.add("rr_stone", [T(p) for p in [(cx + sgn * xt, ht, zf), (cx + sgn * xt, ht, zb), (cx + sgn * xb, hb, zb),
                                          (cx + sgn * xb, hb, zf)]],
              [(side[0], side[1]), (side[0] + 4 / 64, side[1]), (side[0] + 4 / 64, side[3]), (side[0], side[3])],
              (sgn, 0.05, 0), group="stele")
    # snow cap on the gable: two thin sloped slabs with a front lip
    o = 0.04
    for sgn in (-1, 1):
        B.add("rr_stone", [T(p) for p in [(cx, hp + 0.06, zb - o), (cx, hp + 0.06, zf + o), (cx + sgn * (xt + o), ht - 0.02, zf + o),
                                          (cx + sgn * (xt + o), ht - 0.02, zb - o)]],
              [(snow[0], snow[1]), (snow[2], snow[1]), (snow[2], snow[1] + 5 / 64), (snow[0], snow[1] + 5 / 64)],
              (sgn * 0.6, 0.8, 0), group="stele")
        B.add("rr_stone", [T(p) for p in [(cx, hp + 0.06, zf + o), (cx + sgn * (xt + o), ht - 0.02, zf + o),
                                          (cx + sgn * (xt + o), ht - 0.07, zf + o), (cx, hp, zf + o)]],
              [(snow[0], snow[3] - 3 / 64), (snow[2], snow[3] - 3 / 64), (snow[2], snow[3]), (snow[0], snow[3])],
              fn, group="stele")
    # violet scarf tied round the stele between the emblem and the plaque (follows the lean)
    O = "r216_offer"
    sc = R(O, "scarf")
    h0s, h1s = G + 1.36, G + 1.78
    xs0, xs1 = cx - 0.39, cx + 0.59
    B.add("rr_offer", [T(p) for p in [(xs0, h1s, zf + 0.014), (xs1, h1s, zf + 0.014), (xs1, h0s, zf + 0.014), (xs0, h0s, zf + 0.014)]],
          [(sc[0], sc[1]), (sc[2], sc[1]), (sc[2], sc[3]), (sc[0], sc[3])], fn, group="offer", solid=False)
    # wreath leaning on the upper step, bouquet and candle on the lower step
    B.card("rr_offer", cx, 401.84, 0.46, G + 0.12, G + 0.58, R(O, "wreath"), lean=0.2, group="offer", solid=False)
    B.card("rr_offer", 318.15, 401.97, 0.28, G + 0.12, G + 0.4, R(O, "bouquet"), lean=0.25, group="offer", solid=False)
    warm = lambda k: [(255, 236, 200)] * 4  # noqa: E731
    B.card("rr_offer_u", 316.95, 401.75, 0.13, G + 0.26, G + 0.52, R(O, "candle"), colors=warm(0), group="glow",
           solid=False)
    # stone vigil lantern on the west end of the lower step: base, post, glowing fire box, snow-capped roof
    lx, lz = 316.4, 401.5
    B.box("rr_stone", lx - 0.12, lz - 0.12, lx + 0.12, lz + 0.12, G + 0.12, G + 0.2, side, sides="swet", group="lantern")
    B.box("rr_stone", lx - 0.06, lz - 0.06, lx + 0.06, lz + 0.06, G + 0.2, G + 0.62, side, sides="swe", group="lantern")
    B.box("rr_stone", lx - 0.15, lz - 0.15, lx + 0.15, lz + 0.15, G + 0.62, G + 0.68, side, sides="swet", group="lantern")
    glowc = lambda n, p: (255, 244, 214) if n[2] > 0.5 else (246, 218, 170)  # noqa: E731
    B.box("rr_offer_u", lx - 0.12, lz - 0.12, lx + 0.12, lz + 0.12, G + 0.68, G + 1.02, R(O, "glow"), sides="swe",
          colors=glowc, group="glow")
    for k in range(4):                                 # stone corner posts of the fire box
        dx, dz = (-1 if k % 2 else 1) * 0.12, (-1 if k // 2 else 1) * 0.12
        B.box("rr_stone", lx + dx - 0.025, lz + dz - 0.025, lx + dx + 0.025, lz + dz + 0.025, G + 0.68, G + 1.02, side,
              sides="swe", group="lantern")
    lathe(B, "rr_stone", lx, lz, [(0.24, G + 1.02), (0.27, G + 1.07), (0.13, G + 1.18), (0.0, G + 1.27)], 4, side,
          top_box=snow, top_from=1, group="lantern", ang0=math.pi / 4)
    # cairn of snow-capped stones on the east end of the lower step
    rock = (gran[0] + 2 / 64, gran[1] + 2 / 64, gran[0] + 14 / 64, gran[1] + 13 / 64)
    rtop = (cairn[0] + 4 / 64, cairn[1] + 17 / 64, cairn[0] + 20 / 64, cairn[1] + 21 / 64)
    for (rx, rz, r, h0, hh) in ((318.5, 401.5, 0.2, G + 0.12, 0.16), (318.48, 401.48, 0.14, G + 0.27, 0.12),
                                (318.52, 401.5, 0.09, G + 0.38, 0.09)):
        lathe(B, "rr_stone", rx, rz, [(r * 0.7, h0), (r, h0 + hh * 0.4), (r * 0.7, h0 + hh * 0.85), (0.0, h0 + hh)],
              6, rock, top_box=rtop, top_from=2, group="cairn", ang0=hash01(rx * 100, h0 * 100) * 2)
    # fresh boot prints walking in from the west and back out, violet shard dust before the stele
    for (px, pz, ang) in ((313.2, 403.6, 1.25), (314.6, 403.1, 1.1), (315.6, 402.7, 0.9)):
        B.decal("rr_offer", px, pz, 1.0, 0.5, ang, G + 0.02 if px > 315 else G + 0.012, R(O, "prints"))
    B.decal("rr_offer", 317.55, 402.18, 0.95, 0.5, 0.0, G + 0.022, R(O, "dust"))


# ---------------------------------------------------------------------------------------------------------------
# Indra's Snowy Camp (map_data_109)
# ---------------------------------------------------------------------------------------------------------------

def build_camp(B):
    T, K, S = "r217_tent", "r217_camp", "r216_stone"
    G = G217
    canvas, flap, rope, wood, gable = (R(T, k) for k in ("canvas", "flap", "rope", "wood", "gable"))
    # tent: ridge north-south at x 314.9, front gable (door flap, eclipse sigil) facing south toward the camera
    tx0, tx1, tz0, tz1, rx = 313.45, 316.35, 360.05, 361.95, 314.9
    he, hr = G + 0.14, G + 1.5
    cu0, cv0, cu1, cv1 = canvas
    for sgn, ex in ((-1, tx0), (1, tx1)):            # the two slopes: u along z, v from ridge (0) to eave (1)
        B.add("rr_tent", [(rx, hr, tz1), (rx, hr, tz0), (ex, he, tz0), (ex, he, tz1)] if sgn > 0 else
              [(rx, hr, tz0), (rx, hr, tz1), (ex, he, tz1), (ex, he, tz0)],
              [(cu0, cv0), (cu1, cv0), (cu1, cv1), (cu0, cv1)], (sgn * 0.7, 0.7, 0), group="tent")
        B.add("rr_tent", [(ex, he, tz1), (ex, he, tz0), (ex, G, tz0), (ex, G, tz1)] if sgn > 0 else
              [(ex, he, tz0), (ex, he, tz1), (ex, G, tz1), (ex, G, tz0)],
              [(cu0, cv1 - 2 / 64), (cu1, cv1 - 2 / 64), (cu1, cv1), (cu0, cv1)], (sgn, 0, 0), group="tent")
    fu0, fv0, fu1, fv1 = flap
    vh = fv0 + (fv1 - fv0) * (hr - he) / (hr - G)
    B.add("rr_tent", [(rx, hr, tz1), (tx1, he, tz1), (tx0, he, tz1)], [((fu0 + fu1) / 2, fv0), (fu1, vh), (fu0, vh)],
          (0, 0, 1), group="tent")
    B.add("rr_tent", [(tx0, he, tz1), (tx1, he, tz1), (tx1, G, tz1), (tx0, G, tz1)], [(fu0, vh), (fu1, vh), (fu1, fv1), (fu0, fv1)],
          (0, 0, 1), group="tent")
    gu0, gv0, gu1, gv1 = gable
    B.add("rr_tent", [(rx, hr, tz0), (tx0, he, tz0), (tx1, he, tz0)], [((gu0 + gu1) / 2, gv0), (gu0, gv1), (gu1, gv1)],
          (0, 0, -1), group="tent")
    # ridge pole and front/back poles, snow along the ridge
    B.box("rr_tent", rx - 0.04, tz0 + 0.0, rx + 0.04, tz1 + 0.2, hr - 0.02, hr + 0.06, wood, sides="swet", group="tent")
    for pz in (tz0 + 0.06, tz1 + 0.08):
        B.box("rr_tent", rx - 0.035, pz - 0.035, rx + 0.035, pz + 0.035, G, hr, wood, sides="swe", group="tent")
    snow = R(S, "snow")
    for sgn in (-1, 1):
        B.add("rr_stone", [(rx, hr + 0.08, tz0 + 0.02), (rx, hr + 0.08, tz1 + 0.05), (rx + sgn * 0.26, hr - 0.2, tz1 + 0.05),
                           (rx + sgn * 0.26, hr - 0.2, tz0 + 0.02)][::(1 if sgn < 0 else -1)],
              [(snow[0], snow[1]), (snow[2], snow[1]), (snow[2], snow[1] + 6 / 64), (snow[0], snow[1] + 6 / 64)],
              (sgn * 0.7, 0.7, 0), group="tent")
    # guy ropes from the front apex and the front eave corners to stakes in the blocked strip (z 362)
    for (ax, ah, az, bx, bz) in ((rx, hr - 0.05, tz1 + 0.08, 313.6, 362.8), (rx, hr - 0.05, tz1 + 0.08, 316.2, 362.8),
                                 (tx0, he + 0.05, tz1, 313.25, 362.55), (tx1, he + 0.05, tz1, 316.75, 362.55)):
        d = math.hypot(bx - ax, bz - az)
        nx, nz = -(bz - az) / d * 0.03, (bx - ax) / d * 0.03
        B.quad("rr_tent2", [(ax - nx, ah, az - nz), (ax + nx, ah, az + nz), (bx + nx, G + 0.06, bz + nz), (bx - nx, G + 0.06, bz - nz)],
               rope, (0, 0.5, 0.5), group="tent", solid=False)
        B.box("rr_tent", bx - 0.03, bz - 0.03, bx + 0.03, bz + 0.03, G, G + 0.12, wood, sides="swe", group="tent")
    # supply crate with the expedition lantern and the journal
    crate, cside = R(K, "crate"), R(K, "crate_side")
    cx0, cz0, cx1, cz1, ch = 311.14, 360.24, 311.86, 360.86, G + 0.56
    B.box("rr_camp", cx0, cz0, cx1, cz1, G, ch, {"s": crate, "e": cside, "w": cside}, sides="swet", top_uv=cside,
          group="crate")
    lx, lz = 311.34, 360.52
    iron, glass = R(K, "iron"), R(K, "glass")
    B.box("rr_camp", lx - 0.1, lz - 0.1, lx + 0.1, lz + 0.1, ch, ch + 0.05, iron, sides="swet", group="lantern")
    gl = lambda n, p: (255, 246, 220) if n[2] > 0.5 else (250, 226, 180)  # noqa: E731
    B.box("rr_camp_u", lx - 0.08, lz - 0.08, lx + 0.08, lz + 0.08, ch + 0.05, ch + 0.3, glass, sides="swe", colors=gl,
          group="glow")
    B.box("rr_camp", lx - 0.1, lz - 0.1, lx + 0.1, lz + 0.1, ch + 0.3, ch + 0.34, iron, sides="swet", group="lantern")
    lathe(B, "rr_camp", lx, lz, [(0.09, ch + 0.34), (0.0, ch + 0.42)], 4, iron, group="lantern", ang0=math.pi / 4)
    B.quad("rr_camp2", [(lx - 0.07, ch + 0.52, lz), (lx + 0.07, ch + 0.52, lz), (lx + 0.07, ch + 0.42, lz), (lx - 0.07, ch + 0.42, lz)],
           (iron[0], iron[1], iron[2], iron[1] + 2 / 64), (0, 0, 1), group="lantern", solid=False)
    B.flat("rr_camp", 311.5, 360.38, 311.82, 360.72, ch + 0.012, R(K, "journal"), group="crate")
    B.flat("rr_offer_u", 310.75, 360.86, 311.95, 361.75, G + 0.018, R("r216_offer", "halo"), colors=[(255, 236, 196)] * 4)
    # low crate with the open Eclipse shard-scanner case, violet compass screen facing south
    lc = (crate[0], crate[1] + 6 / 64, crate[2], crate[3])
    sx0, sz0, sx1, sz1, sh = 312.16, 360.22, 312.84, 360.8, G + 0.36
    B.box("rr_camp", sx0, sz0, sx1, sz1, G, sh, {"s": lc, "e": cside, "w": cside}, sides="swet", top_uv=cside, group="crate")
    case, screen = R(K, "case"), R(K, "screen")
    B.box("rr_camp", 312.26, 360.36, 312.74, 360.7, sh, sh + 0.1, case, sides="swet", group="scanner")
    vio = lambda n, p: (236, 220, 255)  # noqa: E731
    B.card("rr_camp_u", 312.5, 360.4, 0.44, sh + 0.1, sh + 0.46, screen, lean=0.32, colors=[vio(0, 0)] * 4, group="glow",
           solid=False)
    B.card("rr_camp_u", 312.72, 360.74, 0.1, sh + 0.1, sh + 0.24, R(K, "shard"), lean=0.1, colors=[(220, 200, 255)] * 4,
           group="glow", solid=False)
    # faint violet trace on the snow pointing south from the scanner (toward Mt. Coronet)
    bu0, bv0, bu1, bv1 = R(K, "beam")
    B.add("rr_camp_u", [(312.3, G + 0.02, 360.85), (312.7, G + 0.02, 360.85), (312.98, G + 0.02, 363.0), (312.02, G + 0.02, 363.0)],
          [(bu0, bv0), (bu1, bv0), (bu1, bv1), (bu0, bv1)], (0, 1, 0), [(200, 186, 240)] * 4, "decal", solid=False)
    # packed-snow footprint rings around the clearing, boot prints leading south-west
    ring = R(K, "ring")
    spots = [(310.2, 358.3), (312.3, 358.0), (314.4, 358.4), (316.2, 359.0), (309.9, 360.4), (310.4, 362.1),
             (315.8, 359.6), (311.2, 359.1)]
    for k, (px, pz) in enumerate(spots):
        B.decal("rr_camp", px, pz, 1.9, 1.9, hash01(k, 7) * 6.28, G + 0.012 + 0.002 * (k % 4), ring)
    for k, (px, pz) in enumerate(((309.6, 363.4), (308.9, 364.6), (308.3, 365.9))):
        B.decal("rr_offer", px, pz, 1.0, 0.5, 3.6, G + 0.02, R("r216_offer", "prints"))


# ---------------------------------------------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------------------------------------------

def rel(c):
    return f"{MAP_DIR}/map_data_{c:03d}.bin"


def build():
    tex = TX.build_set()
    table = tex["table"]
    out = {}
    for c, fn, pave in ((110, build_teo, True), (109, build_camp, False)):
        edit = C.ChunkEdit(rel(c), CELLS[c], BASE_REV)
        info = {}
        if c == 110:
            info["cliff_faces_cut"] = cut_cliff(edit, ("criffp",), (400.0, 401.0), 316.0, 319.0)
            x0, z0, x1, z1 = TEO_PAVE
            edit.clip_flat(("ngrass",), [(x0, z0, x1, z1)])
        B = Builder(table)
        fn(B)
        edit.add(B, table)
        model = edit.model_bytes()
        perm = edit.permissions()
        cx, cz = CELLS[c]
        if c == 110:
            for (x, z) in TEO_BLOCK:
                perm[z - cz * 32][x - cx * 32] = BLOCK
            x0, z0, x1, z1 = TEO_PAVE
            for x in range(x0, x1):
                for z in range(z0, z1):
                    if not perm[z - cz * 32][x - cx * 32] & BLOCK:
                        perm[z - cz * 32][x - cx * 32] = 0x0000
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
    return res


# ---------------------------------------------------------------------------------------------------------------
# lighting_set_008: crisp melancholic alpine blue-silver day, serene moonlit snow at night
# ---------------------------------------------------------------------------------------------------------------

LIGHTING_REL = "res/field/lighting/lighting_set_008.json"
NIGHT = ((12, 14, 21), (14, 15, 18), (10, 11, 14), (14, 15, 18), (8, 9, 13))
LIGHT_CURVE = {
    0: NIGHT, 7200: NIGHT,                                                               # 00:00-04:00 moonlit snow
    8100: ((13, 14, 21), (12, 12, 16), (12, 12, 15), (10, 10, 15), (10, 10, 13)),        # pre-dawn steel blue
    9000: ((15, 15, 22), (12, 12, 15), (11, 11, 13), (12, 12, 15), (12, 12, 15)),        # cold blue dawn
    14400: ((19, 20, 24), (14, 14, 15), (9, 10, 11), (14, 14, 16), (14, 14, 17)),        # silver morning
    20700: ((22, 23, 26), (15, 15, 16), (10, 10, 12), (15, 15, 16), (14, 15, 16)),       # crisp alpine day
    21600: ((24, 25, 27), (16, 16, 17), (10, 11, 12), (16, 16, 17), (14, 14, 15)),       # bright noon
    27000: ((25, 25, 27), (16, 16, 17), (10, 11, 12), (17, 17, 18), (14, 14, 15)),       # blue-silver afternoon
    27900: ((23, 23, 26), (15, 15, 16), (11, 11, 12), (16, 16, 17), (13, 13, 15)),
    30600: ((21, 20, 24), (15, 15, 16), (11, 11, 13), (16, 16, 17), (12, 12, 14)),       # pale lavender light
    32400: ((19, 17, 22), (14, 14, 16), (11, 11, 13), (15, 15, 17), (10, 10, 13)),       # melancholic dusk
    33300: ((17, 15, 22), (14, 14, 16), (11, 11, 14), (15, 15, 17), (9, 9, 13)),         # violet-blue twilight
    34200: ((15, 15, 22), (14, 14, 16), (11, 11, 14), (14, 14, 17), (9, 9, 13)),         # serene twilight snow
    36000: ((13, 14, 21), (14, 14, 17), (10, 11, 14), (14, 15, 18), (8, 9, 13)),         # moonrise
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

VIEWS = {"teo": (TEO_STAND, G216), "teo_wide": ((314, 403), G216), "camp": (CAMP_STAND, G217),
         "camp_wide": ((310, 363), G217), "camp_approach": ((305, 366), G217)}


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
    for name, (t, h) in VIEWS.items():
        preview.render(models, tex["bytes"], t, os.path.join(d, f"view_{name}.png"), target_h=h)
    preview.render(models, tex["bytes"], TEO_STAND, os.path.join(d, "view_teo_night.png"), target_h=G216, night=True)
    preview.render(models, tex["bytes"], CAMP_STAND, os.path.join(d, "view_camp_night.png"), target_h=G217, night=True)
    preview.render(models, tex["bytes"], (317, 401.2), os.path.join(d, "zoom_teo.png"), target_h=G216 + 0.8, zoom=3.0)
    preview.render(models, tex["bytes"], (312.8, 360.6), os.path.join(d, "zoom_camp.png"), target_h=G217 + 0.5, zoom=2.6)


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
    res.append((f"set 080: stock 014 + 4 atlases round-trip, VRAM {sum(vo)} B ({sum(vo) / 1024:.1f} KB) < 160 KB",
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
