#!/usr/bin/env python3
"""Route 215 flooded-lowland art pass (v3): map_data_069/070/071 (stock terrain edited in place) + set 078 +
lighting 006.

Usage:
  ~/.venvs/desmume/bin/python tools/routes/r215/build_art.py              dry run: build, budgets, every check
  ~/.venvs/desmume/bin/python tools/routes/r215/build_art.py --write      write chunks, set 078 and lighting_set_006
                                                                          (refuses if any check fails; idempotent)

Inputs are read from git BASE_REV (common.BASE_REV): the stock chunks, stock set 010 (textures.py appends to it) and
lighting_set_000 (schema + block times + sun directions). Re-running never feeds back on itself.

What it adds (tools/world_art/chunkedit.py: every stock shape and material stays byte for byte, the new geometry is
appended as new materials/shapes; stock props and BDHC are kept verbatim):
  * Three continuous flood sheets (SHEETS) over the lowland dips, in Platinum's own animated `sea` water (stock set
    010 texture, 1 tile per repeat). Each sheet's outline is the zero contour of a smooth field (signed distance
    to the sheet's dry border + low-frequency noise), traced by marching squares on a quarter-tile grid,
    simplified (Douglas-Peucker) and ear-clipped into triangles; a shoreline strip (r215_shore, c0=1: silty
    shallows, wet mud lip, stock-green grass overhang thinning into the stock grass) follows the whole contour as
    one mitred quad strip. Walkable tiles whose centre is under the water get the stock TILE_BEHAVIOR_PUDDLE
    (0x16) low byte (splashes + reflections; collision bits untouched).
  * Weathered timber boardwalks (BOARDWALKS) spanning right across the sheets: decks 0.06 tiles over the ground
    (the BDHC floor), mud-dark skirts, corner and edge pilings standing in the water.
  * Packed-mud truck roads (RUTS) on DRY ground only (never on a flood sheet, never over tall grass; checked):
    solid road-bed strips of r215_ruts (cleanly stepped edges with a crisp 1-texel dark outline + light rim, two
    sculpted tyre grooves) ending in rounded r215_rutcap caps where they meet the staging pad, the tall grass,
    the gate stairs and the gravel apron (no square-cut ends).
  * Staging pads (TX.PADS): one texel-aligned decal quad each with a clean 1-texel outlined border - the north
    yard's mud pad + road turnaround, and the gravel apron before the Veilstone gate, which covers the stock
    speckled 'blueglayp' edge. Pads and road beds sit under the stock 'allpeak' decals (+0.03); any tall-grass
    tile a road or pad touches gets the stock 'nectgr' tile redrawn over it (none today).
  * Team Eclipse staging: the north yard is a full 3x3 supply yard (offset slate / wooden crate stacks, a draped
    olive tarp on a pallet, steel drums, an Eclipse warning banner post, a tripod work lamp, soft contact shadows);
    the gate yard south of the gate approach keeps every prop off the road bed on screen (props projected along
    the field camera: checked); a small south-field cluster with a mast lamp. Lamps glow through an unlit lamp
    glass plus smooth A3I5 halo / ground pool cards (r215_glow): no dithered glow anywhere.
  * A flooded drainage sign post (SIGNS); its tile is blocked, a BG_EVENT reads it.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as R  # noqa: E402
import paths as PA  # noqa: E402
import textures as TX  # noqa: E402
import chunkedit as C  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402

MODEL_LIMIT = 0xF000
BDHC_LIMIT = 0x9000
PUDDLE = 0x16
LIGHTING_REL = "res/field/lighting/lighting_set_006.json"
LIGHTING_TEMPLATE = "res/field/lighting/lighting_set_000.json"

# ---------------------------------------------------------------------------------------------------------------
# the layout (absolute matrix tiles; rect = (x0, z0, x1, z1) inclusive tiles)
# ---------------------------------------------------------------------------------------------------------------

# flood sheets: the water may cover the flat walkable behaviour-0 tiles of `rect` at one BDHC height plus the
# listed blocked tree-base tiles (`trees`, linking lobes under the canopy); `dry_x0` keeps the seam column clear
SHEETS = {
    "west": dict(rect=(577, 594, 589, 601), trees=[(582, 594), (583, 594), (582, 595), (583, 595)],
                 note="MAP_069 west entry from Route 210 (the west boardwalk)"),
    "lowland": dict(rect=(594, 589, 606, 595), trees=[],
                    note="MAP_069 lowland east of the first raised walkway (the long boardwalk)"),
    "east": dict(rect=(616, 585, 621, 595), trees=[],
                 note="MAP_070 lowland under the second raised walkway"),
}
SHEET_MARGIN = 0.42          # contour inset from the sheet's dry border (tiles)
SHEET_NOISE = 0.36           # contour wobble amplitude (tiles)
GRID = 0.25                  # marching-squares step (tiles)
SIMPLIFY = 0.07              # Douglas-Peucker tolerance (tiles)
DECK_H = 0.06
SHORE_IN, SHORE_OUT = 0.26, 0.62   # shoreline strip: over the water / over the bank (tiles)
H_WATER, H_SHORE = 0.036, 0.041    # decal heights over the ground (tiles): above the stock A3I5 'allpeak'
                                   # grass decals (+0.03), below the boardwalk decks (+0.06)

# boardwalk decks: (x0, z0, x1, z1) tile rects, decks run along x, 2 tiles wide in z
BOARDWALKS = [
    (577, 598, 587, 599),     # west entry (sheet west)
    (595, 591, 606, 592),     # flooded lowland (sheet lowland)
    (616, 592, 621, 593),     # MAP_070 lowland (sheet east)
]

# truck ruts: polylines of lane centres (x, z) in tiles; the lane is 2 tiles wide; corners are filleted
# packed-mud road beds, each end a rounded cap (r215_rutcap) where it meets something: the north lane runs from the
# staging yard's turnaround pad east to the tall-grass patch at x 646 (the trucks cut through the grass and the x 654
# corridor, unpaved); the south lane leaves the grass at x 649, turns down to the lane and runs east to the foot of
# the gate stairs; the gate approach runs from the stairs onto the gravel apron. No road bed crosses tall grass.
RUTS = [
    [(630.4, 586.0), (645.95, 586.0)],                                  # MAP_070/071 north field
    [(648.95, 591.0), (645.0, 591.0), (645.0, 598.0), (658.95, 598.0)],  # MAP_071 south field -> lane -> stairs
    [(660.05, 598.0), (670.9, 598.0)],                                  # MAP_071 gate approach (low ground)
]
RUT_FILLET = 1.6
H_PAD, H_RUT = 0.012, 0.020   # pads and the road bed sit UNDER the stock 'allpeak' tall-grass decals (+0.03), so
                              # tall grass the road crosses still shows (and still reads as grass) over the mud
PROJ = 1 / math.tan(math.radians(59.05))   # field camera: a height y covers the ground y * PROJ tiles to its north

# Eclipse staging clusters: tiles they block (must be free of events / NPC routes) + their props
CLUSTERS = {
    "north": dict(block=(630, 582, 632, 584), kind="yard"),       # the 3x3 roadside landmark over the north ruts
    "gate": dict(block=(665, 599, 667, 601), kind="gate"),        # 3x3 yard by the Veilstone gate
    "field": dict(block=(655, 592, 656, 593), kind="small"),
}
SIGNS = {"drain": (594, 590)}         # the flooded drainage sign post (tile blocked)
BG_SIGNS = [                          # (x, z, script) BG_EVENTs appended to events.json
    (655, 592, "Route215_EclipseCrates"),
    (594, 590, "Route215_DrainageSign"),
    (666, 599, "Route215_EclipseStaging"),
]
CLIFF_OK = {"lgreen", "lgreenp", "ngrass", "tshadow", "nectgr", "allpeak", "shadowchip", "nhana", "plant2"}


# ---------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------

def tiles(rect):
    x0, z0, x1, z1 = rect
    return [(x, z) for z in range(z0, z1 + 1) for x in range(x0, x1 + 1)]


def h01(x, z, k=0):
    v = math.sin(x * 12.9898 + z * 78.233 + k * 37.719) * 43758.5453
    return v - math.floor(v)


def vnoise(x, z, cell, k):
    """Smooth value noise in world tiles (lattice `cell` tiles)."""
    fx, fz = x / cell, z / cell
    ix, iz = math.floor(fx), math.floor(fz)
    tx, tz = fx - ix, fz - iz
    tx, tz = tx * tx * (3 - 2 * tx), tz * tz * (3 - 2 * tz)
    a = h01(ix, iz, k) * (1 - tx) + h01(ix + 1, iz, k) * tx
    b = h01(ix, iz + 1, k) * (1 - tx) + h01(ix + 1, iz + 1, k) * tx
    return a * (1 - tz) + b * tz


class Stock:
    def __init__(self):
        self.chunks = R.stock_chunks()
        self.perm = R.merged_permissions(self.chunks)
        hts = R.merged_heights(self.chunks)
        self.h = {t: (None if v is None else v - 1.0) for t, v in hts.items()}   # chunkedit h (ground = 1.0)
        self.ev = R.stock_events()
        self.cliff = self._cliff_tiles()

    def _cliff_tiles(self):
        """Tiles touched by any stock face that is not flat ground / tree art (cliffs, stairs, raised walkways)."""
        out = set()
        for c, d in self.chunks.items():
            e = d["edit"]
            for si, tex, pal in e.iter_shapes():
                if tex in CLIFF_OK or tex.startswith(("tree", "conttree")):
                    continue
                tris, quads = e._faces(si)
                for f in tris + quads:
                    pts = [e.tile(v["pos"]) for v in f]
                    xs, zs = [p[0] for p in pts], [p[2] for p in pts]
                    for x in range(int(math.floor(min(xs) + 0.05)), int(math.floor(max(xs) - 0.05)) + 1):
                        for z in range(int(math.floor(min(zs) + 0.05)), int(math.floor(max(zs) - 0.05)) + 1):
                            out.add((x, z))
        return out

    def ground(self, t, behaviours=(0,)):
        """Walkable flat ground tile: unblocked, behaviour in `behaviours`, BDHC at a whole-tile height and the four
        tile corners at the same height (no slope)."""
        if t not in self.perm or self.perm[t] & 0x8000 or (self.perm[t] & 0xFF) not in behaviours:
            return None
        h = self.h[t]
        if h is None or abs(h - round(h)) > 0.01:
            return None
        c = self.chunks[R.chunk_of(t[0])]
        b = mapdata.read_bdhc(c["sec"]["bdhc"])
        cx, cz = c["cell"]
        lx, lz = t[0] - cx * 32, t[1] - cz * 32
        for ox, oz in ((2, 2), (14, 2), (2, 14), (14, 14)):
            y = mapdata.height_at(b, (lx * 16 + ox - 256) * 4096, (lz * 16 + oz - 256) * 4096, int((h + 1) * 16 * 4096))
            if y is None or abs(y / 4096 / 16 - 1.0 - h) > 0.01:
                return None
        return round(h)

    def tree_base(self, t, h):
        """Blocked plain tile at height h with no cliff / stair art on it (a tree base under its canopy)."""
        p = self.perm.get(t)
        return p is not None and p & 0x8000 and (p & 0xFF) == 0 and t not in self.cliff and \
            self.h[t] is not None and abs(self.h[t] - h) < 0.01


class Art:
    """New faces in absolute tiles, routed to the chunk holding their centroid."""

    SPEC = {   # key -> (texture, lights, cull, alpha, polygon id)
        "water": (TX.WATER_TEXTURE, 1, "none", 31, 0),     # two-sided: a sliver can never cull into a gap
        "shore": ("r215_shore", 1, "none", 31, 0),
        "board": ("r215_board", 1, "back", 31, 0),
        "ruts": ("r215_ruts", 1, "back", 31, 0),
        "rutcap": ("r215_rutcap", 1, "back", 31, 0),
        "padn": ("r215_padn", 1, "back", 31, 0),
        "padg": ("r215_padg", 1, "back", 31, 0),
        "prop": ("r215_props", 1, "back", 31, 0),
        "prop2": ("r215_props", 1, "none", 31, 0),
        "grass": ("nectgr", 1, "back", 31, 0),     # stock tall grass redrawn over the road (same material bits)
        "crate": ("r215_crate", 1, "back", 31, 0),
        "crate2": ("r215_crate", 1, "none", 31, 0),
        "lamp": ("r215_crate", 0, "none", 31, 0),
        "shadow": ("r215_glow", 0, "back", 31, 1),
        "pool": ("r215_glow", 0, "back", 31, 2),
        "halo": ("r215_glow", 0, "none", 31, 3),
    }
    PALETTE = {TX.WATER_TEXTURE: TX.WATER_TEXTURE, "nectgr": "nectgrass"}

    def __init__(self, table):
        self.mb = {c: C.MeshBuilder() for c in R.CHUNKS}
        self.table = table
        self.decals = []        # (x0, z0, x1, z1, h) flat ground decals
        self.solids = []        # [(pts)] solid props
        self.faces = []         # (key, pts, uvs) every new face, for the geometry checks

    def add(self, key, pts, uvs, facing, solid=True, rebase=True, chunk=None, color=(255, 255, 255)):
        n = C.face_normal(pts)
        if sum(a * b for a, b in zip(n, facing)) < 0:
            pts, uvs = pts[::-1], uvs[::-1]
        tex, lights, cull, alpha, pid = self.SPEC[key]
        uvs = [list(u) for u in uvs]
        if rebase:
            for k in (0, 1):
                lo = math.floor(min(u[k] for u in uvs) + 1e-6)
                for u in uvs:
                    u[k] -= lo
        if chunk is None:
            cx = sum(p[0] for p in pts) / len(pts)
            chunk = R.chunk_of(int(math.floor(cx)))
        mb = self.mb[chunk]
        name = "r215_" + key
        mb.material(name, tex, self.PALETTE.get(tex, tex + "_pl"), self.table[tex]["size"], lights=lights, cull=cull,
                    alpha=alpha, polygon_id=pid)
        mb.face(name, [tuple(p) for p in pts], [tuple(u) for u in uvs], color=color)
        self.faces.append((key, [tuple(p) for p in pts], [tuple(u) for u in uvs]))
        if solid:
            self.solids.append(pts)

    def flat(self, key, x0, z0, x1, z1, h, uv, rebase=True, chunk=None):
        u0, v0, u1, v1 = uv
        self.add(key, [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)],
                 [(u0, v1), (u1, v1), (u1, v0), (u0, v0)], (0, 1, 0), solid=False, rebase=rebase, chunk=chunk)
        self.decals.append((x0, z0, x1, z1, h))

    def wall(self, key, a, b, h0, h1, uv, solid=True):
        (xa, za), (xb, zb) = a, b
        u0, v0, u1, v1 = uv
        n = (-(zb - za), 0.0, xb - xa)
        self.add(key, [(xa, h1, za), (xb, h1, zb), (xb, h0, zb), (xa, h0, za)],
                 [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], n, solid, rebase=False)

    def box(self, key, x0, z0, x1, z1, h0, h1, side, top=None, sides="nsew"):
        if "s" in sides:
            self.wall(key, (x0, z1), (x1, z1), h0, h1, side)
        if "n" in sides:
            self.wall(key, (x1, z0), (x0, z0), h0, h1, side)
        if "e" in sides:
            self.wall(key, (x1, z1), (x1, z0), h0, h1, side)
        if "w" in sides:
            self.wall(key, (x0, z0), (x0, z1), h0, h1, side)
        if top:
            u0, v0, u1, v1 = top
            self.add(key, [(x0, h1, z1), (x1, h1, z1), (x1, h1, z0), (x0, h1, z0)],
                     [(u0, v1), (u1, v1), (u1, v0), (u0, v0)], (0, 1, 0), solid=True, rebase=False)


def cuv(key, inset=0.25, atlas=None):
    """Atlas texel box -> uv rect (u0, v0, u1, v1), inset by a quarter texel against bleeding."""
    x0, y0, x1, y1 = (atlas or TX.CRATE_UV)[key]
    return ((x0 + inset) / 64, (y0 + inset) / 64, (x1 - inset) / 64, (y1 - inset) / 64)


def guv(key, inset=0.5):
    return cuv(key, inset, TX.GLOW_UV)


def puv(key, inset=0.25):
    """r215_props atlas (64 x 32) texel box -> uv rect."""
    x0, y0, x1, y1 = TX.PROPS_UV[key]
    return ((x0 + inset) / 64, (y0 + inset) / 32, (x1 - inset) / 64, (y1 - inset) / 32)


# ---------------------------------------------------------------------------------------------------------------
# flood sheets: field -> marching squares -> loops -> simplify -> triangles + shoreline strips
# ---------------------------------------------------------------------------------------------------------------

def sheet_tiles(S, name):
    """-> (height, set of tiles the water may cover)."""
    sh = SHEETS[name]
    hs = {}
    for t in tiles(sh["rect"]):
        h = S.ground(t)
        if h is not None and t not in S.cliff:
            hs.setdefault(h, set()).add(t)
    h, core = max(hs.items(), key=lambda kv: len(kv[1]))
    ok = set(core)
    for t in sh["trees"]:
        assert S.tree_base(t, h), f"sheet {name}: {t} is not a plain tree base at h {h}"
        ok.add(t)
    return h, ok


def sq_dist(px, pz, t):
    dx = max(t[0] - px, 0.0, px - (t[0] + 1))
    dz = max(t[1] - pz, 0.0, pz - (t[1] + 1))
    return math.hypot(dx, dz)


def field(px, pz, ok, rect, k, boost=()):
    """Signed distance to the dry border of `ok` (positive inside), inset and wobbled by noise."""
    x0, z0, x1, z1 = rect
    tx, tz = int(math.floor(px)), int(math.floor(pz))
    inside = (tx, tz) in ok
    best = 9.0
    for dz in range(-3, 4):
        for dx in range(-3, 4):
            t = (tx + dx, tz + dz)
            if (t in ok) != inside:
                best = min(best, sq_dist(px, pz, t))
    d = best if inside else -best
    d = min(d, px - 577.0)
    n = (vnoise(px, pz, 2.1, 11 + k) - 0.5) * 2 * SHEET_NOISE + (vnoise(px, pz, 0.8, 23 + k) - 0.5) * 0.18
    for bx, bz, br, ba in boost:          # keep a lobe-linking neck open
        r = math.hypot(px - bx, pz - bz) / br
        if r < 1:
            n += ba * (1 - r * r) ** 2
    return d - SHEET_MARGIN + n


def march(fn, x0, z0, nx, nz, s):
    """Marching squares of fn on the grid (x0 + i s, z0 + j s) -> list of closed loops [(x, z), ...]."""
    F = [[fn(x0 + i * s, z0 + j * s) for i in range(nx + 1)] for j in range(nz + 1)]
    for row in F:
        for i, v in enumerate(row):
            if abs(v) < 1e-6:
                row[i] = 1e-6

    def P(i, j):
        return (x0 + i * s, z0 + j * s)

    def edge_pt(e):
        kind, i, j = e
        a, b = (i, j), ((i + 1, j) if kind == "h" else (i, j + 1))
        fa, fb = F[a[1]][a[0]], F[b[1]][b[0]]
        t = fa / (fa - fb)
        pa, pb = P(*a), P(*b)
        return (pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t)

    adj = {}
    for j in range(nz):
        for i in range(nx):
            a, b, c, d = F[j][i] > 0, F[j][i + 1] > 0, F[j + 1][i + 1] > 0, F[j + 1][i] > 0
            top, right, bottom, left = ("h", i, j), ("v", i + 1, j), ("h", i, j + 1), ("v", i, j)
            es = [e for e, x in ((top, a != b), (right, b != c), (bottom, c != d), (left, d != a)) if x]
            if len(es) == 2:
                segs = [(es[0], es[1])]
            elif len(es) == 4:
                centre = (F[j][i] + F[j][i + 1] + F[j + 1][i + 1] + F[j + 1][i]) / 4 > 0
                segs = [(top, right), (bottom, left)] if centre == a else [(left, top), (right, bottom)]
            else:
                segs = []
            for p, q in segs:
                adj.setdefault(p, []).append(q)
                adj.setdefault(q, []).append(p)
    loops, seen = [], set()
    for start in adj:
        if start in seen:
            continue
        loop, prev, cur = [], None, start
        while True:
            seen.add(cur)
            loop.append(edge_pt(cur))
            nxt = [e for e in adj[cur] if e != prev]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            if cur == start:
                break
        loops.append(loop)
    return loops


def area(poly):
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))


def chaikin(loop, it=3):
    """Corner-cutting smoothing of a closed loop (rounds the tile-corner kinks of the distance field)."""
    for _ in range(it):
        out = []
        n = len(loop)
        for i in range(n):
            a, b = loop[i], loop[(i + 1) % n]
            out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        loop = out
    return loop


def simplify(loop, tol):
    def dp(pts):
        if len(pts) < 3:
            return pts
        a, b = pts[0], pts[-1]
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1e-9
        best, bi = -1.0, 0
        for i in range(1, len(pts) - 1):
            p = pts[i]
            d = abs((b[0] - a[0]) * (a[1] - p[1]) - (a[0] - p[0]) * (b[1] - a[1])) / L
            if d > best:
                best, bi = d, i
        if best <= tol:
            return [a, b]
        return dp(pts[:bi + 1])[:-1] + dp(pts[bi:])
    far = max(range(len(loop)), key=lambda i: (loop[i][0] - loop[0][0]) ** 2 + (loop[i][1] - loop[0][1]) ** 2)
    a = dp(loop[:far + 1])
    b = dp(loop[far:] + loop[:1])
    out = a[:-1] + b[:-1]
    # drop nearly collinear vertices (< 10 deg turn): they only breed sliver triangles
    changed = True
    while changed and len(out) > 4:
        changed = False
        for i in range(len(out)):
            p0, p1, p2 = out[i - 1], out[i], out[(i + 1) % len(out)]
            v1 = (p1[0] - p0[0], p1[1] - p0[1])
            v2 = (p2[0] - p1[0], p2[1] - p1[1])
            cs = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2) + 1e-12)
            if cs > math.cos(math.radians(10)):
                out.pop(i)
                changed = True
                break
    # keep segments >= 0.12 tiles (no slivers)
    res = []
    for p in out:
        if not res or math.hypot(p[0] - res[-1][0], p[1] - res[-1][1]) >= 0.2:
            res.append(p)
    if len(res) > 3 and math.hypot(res[0][0] - res[-1][0], res[0][1] - res[-1][1]) < 0.2:
        res.pop()
    return res


def point_in(poly, x, z):
    c = False
    for (ax, az), (bx, bz) in zip(poly, poly[1:] + poly[:1]):
        if (az > z) != (bz > z) and x < ax + (bx - ax) * (z - az) / (bz - az):
            c = not c
    return c


def ear_clip(poly):
    """Simple CCW polygon (positive area) -> triangles (index triples)."""
    idx = list(range(len(poly)))
    out = []

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        n = len(idx)
        cut = False
        # prefer the ear with the best (largest) minimum angle, for well-shaped triangles
        best = None
        for k in range(n):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % n]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if cross(a, b, c) <= 1e-9:
                continue
            if any(cross(a, b, poly[j]) >= -1e-12 and cross(b, c, poly[j]) >= -1e-12 and
                   cross(c, a, poly[j]) >= -1e-12 for j in idx if j not in (i0, i1, i2)):
                continue
            ang = []
            for p, q, r in ((a, b, c), (b, c, a), (c, a, b)):
                v1, v2 = (q[0] - p[0], q[1] - p[1]), (r[0] - p[0], r[1] - p[1])
                cs = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2) + 1e-12)
                ang.append(math.acos(max(-1.0, min(1.0, cs))))
            score = min(ang)
            if best is None or score > best[0]:
                best = (score, k)
        if best is not None:
            k = best[1]
            out.append((idx[k - 1], idx[k], idx[(k + 1) % n]))
            idx.pop(k)
            cut = True
        if not cut:
            raise AssertionError("ear clipping failed (self-intersecting outline?)")
    out.append(tuple(idx))
    return out


def min_angle(poly, t):
    out = 180.0
    for i in range(3):
        a, b, c = poly[t[i]], poly[t[(i + 1) % 3]], poly[t[(i + 2) % 3]]
        v1, v2 = (b[0] - a[0], b[1] - a[1]), (c[0] - a[0], c[1] - a[1])
        cs = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2) + 1e-12)
        out = min(out, math.degrees(math.acos(max(-1.0, min(1.0, cs)))))
    return out


def improve(poly, tris):
    """Lawson edge flips: flip an interior edge whenever the two triangles sharing it form a convex quad and the
    flip raises their smallest angle (kills the long slivers ear clipping leaves)."""
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    tris = [tuple(t) for t in tris]
    for _ in range(200):
        edges = {}
        for ti, t in enumerate(tris):
            for i in range(3):
                e = tuple(sorted((t[i], t[(i + 1) % 3])))
                edges.setdefault(e, []).append(ti)
        flipped = False
        for (a, b), ts in edges.items():
            if len(ts) != 2:
                continue
            t1, t2 = tris[ts[0]], tris[ts[1]]
            c = [v for v in t1 if v not in (a, b)][0]
            d = [v for v in t2 if v not in (a, b)][0]
            # orient: t1 = (a, b, c) CCW
            if cross(poly[a], poly[b], poly[c]) < 0:
                a, b = b, a
            # new triangles (c, a, d) and (d, b, c) must both be CCW (convex quad)
            n1, n2 = (c, a, d), (d, b, c)
            if cross(poly[n1[0]], poly[n1[1]], poly[n1[2]]) <= 1e-9 or \
                    cross(poly[n2[0]], poly[n2[1]], poly[n2[2]]) <= 1e-9:
                continue
            old = min(min_angle(poly, t1), min_angle(poly, t2))
            new = min(min_angle(poly, n1), min_angle(poly, n2))
            if new > old + 1e-6:
                tris[ts[0]], tris[ts[1]] = n1, n2
                flipped = True
                break
        if not flipped:
            break
    return tris


def build_sheets(F, S, decks_rects, blocked_new):
    """-> (wet tiles, sheet report dicts, water polygons per sheet)."""
    wet = set()
    report = []
    polys = {}
    deck_tiles = {t for r in decks_rects for t in tiles(r)}
    for k, (name, sh) in enumerate(SHEETS.items()):
        h, ok = sheet_tiles(S, name)
        x0, z0, x1, z1 = sh["rect"]
        gx0, gz0 = x0 - 1.0, z0 - 1.0
        nx, nz = int((x1 + 2 - gx0) / GRID), int((z1 + 2 - gz0) / GRID)
        fn = lambda px, pz: field(px, pz, ok, sh["rect"], 7 * k, sh.get("boost", ()))  # noqa: E731
        loops = [simplify(chaikin(lp), SIMPLIFY) for lp in march(fn, gx0, gz0, nx, nz, GRID)]
        loops = [lp for lp in loops if len(lp) >= 3 and abs(area(lp)) > 3.0]     # no stray mini ponds
        outer = []
        holes = []
        for lp in loops:
            # a loop inside another loop is a hole (dry island)
            if any(point_in(o, *lp[0]) for o in loops if o is not lp):
                holes.append(lp)
            else:
                outer.append(lp)
        assert not holes, f"sheet {name}: dry islands inside the water ({[round(abs(area(hh)), 2) for hh in holes]})"
        hw = h + H_WATER
        ox, oz = math.floor(x0), math.floor(z0)
        tot_area, ntri, nstrip = 0.0, 0, 0
        chunk = R.chunk_of(x0)
        polys[name] = []
        for lp in outer:
            if area(lp) < 0:
                lp = lp[::-1]
            polys[name].append(lp)
            tot_area += area(lp)
            # water: planar UVs, 1 tile per repeat of the 16x16 stock sea
            for a, b, c in improve(lp, ear_clip(lp)):
                pts = [(lp[i][0], hw, lp[i][1]) for i in (a, b, c)]
                uvs = [(lp[i][0] - ox, lp[i][1] - oz) for i in (a, b, c)]
                F.add("water", pts, uvs, (0, 1, 0), solid=False, rebase=False, chunk=chunk)
                ntri += 1
            # shoreline strip: outward normals (lp is CCW in x/z with z down -> outward = (dz, -dx) flipped by
            # test), mitred, u along the contour (2 tiles per repeat, an integer number of repeats per loop)
            n = len(lp)
            segn = []
            for i in range(n):
                a, b = lp[i], lp[(i + 1) % n]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                segn.append(((b[1] - a[1]) / L, -(b[0] - a[0]) / L))
            mx, mz = (lp[0][0] + lp[1][0]) / 2, (lp[0][1] + lp[1][1]) / 2
            if fn(mx + segn[0][0] * 0.15, mz + segn[0][1] * 0.15) > fn(mx - segn[0][0] * 0.15, mz - segn[0][1] * 0.15):
                segn = [(-a, -b) for a, b in segn]
            vn, lim = [], []
            seglen = [math.hypot(lp[(i + 1) % n][0] - lp[i][0], lp[(i + 1) % n][1] - lp[i][1]) for i in range(n)]
            for i in range(n):
                p, q = segn[i - 1], segn[i]
                sx, sz = p[0] + q[0], p[1] + q[1]
                L = math.hypot(sx, sz) or 1.0
                sx, sz = sx / L, sz / L
                cosh = max(0.6, sx * q[0] + sz * q[1])
                vn.append((sx / cosh, sz / cosh))
                # an offset d slides the corner point back along both segments by d * tan(turn / 2): keep that
                # under 45% of the shorter neighbouring segment (no crossed / bow-tie strip quads)
                turn = math.acos(max(-1.0, min(1.0, p[0] * q[0] + p[1] * q[1])))
                tn = math.tan(turn / 2)
                lim.append(9.0 if tn < 1e-6 else 0.45 * min(seglen[i - 1], seglen[i]) / tn)
            per = sum(math.hypot(lp[(i + 1) % n][0] - lp[i][0], lp[(i + 1) % n][1] - lp[i][1]) for i in range(n))
            reps = max(1, round(per / 2.0))
            s = 0.0
            us = []
            for i in range(n + 1):
                us.append(s / per * reps)
                a, b = lp[i % n], lp[(i + 1) % n]
                s += math.hypot(b[0] - a[0], b[1] - a[1])
            hs = h + H_SHORE
            for i in range(n):
                j = (i + 1) % n
                wo = [min(lim[m], SHORE_OUT * (1.0 + 0.25 * (vnoise(lp[m][0], lp[m][1], 1.1, 41 + k) - 0.5)))
                      for m in (i, j)]
                wn = [min(lim[m], SHORE_IN) for m in (i, j)]
                A_i = (lp[i][0] - vn[i][0] * wn[0], lp[i][1] - vn[i][1] * wn[0])
                B_i = (lp[i][0] + vn[i][0] * wo[0], lp[i][1] + vn[i][1] * wo[0])
                A_j = (lp[j][0] - vn[j][0] * wn[1], lp[j][1] - vn[j][1] * wn[1])
                B_j = (lp[j][0] + vn[j][0] * wo[1], lp[j][1] + vn[j][1] * wo[1])
                pts = [(A_i[0], hs, A_i[1]), (B_i[0], hs, B_i[1]), (B_j[0], hs, B_j[1]), (A_j[0], hs, A_j[1])]
                uvs = [(us[i], 0.0), (us[i], 1.0), (us[i + 1], 1.0), (us[i + 1], 0.0)]

                def sa(a, b, c):
                    return (b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0])
                s1, s2 = sa(pts[0], pts[1], pts[2]), sa(pts[0], pts[2], pts[3])
                s3, s4 = sa(pts[1], pts[2], pts[3]), sa(pts[1], pts[3], pts[0])
                if s1 * s2 > 0 and s3 * s4 > 0:
                    F.add("shore", pts, uvs, (0, 1, 0), solid=False, rebase=False, chunk=chunk)
                else:
                    # a non-convex strip quad at a tight bend: two triangles over the diagonal that keeps both
                    # positive (the hardware only rasterises convex polygons correctly)
                    tri = ((0, 1, 2), (0, 2, 3)) if s1 * s2 > 0 else ((1, 2, 3), (1, 3, 0))
                    for t3 in tri:
                        F.add("shore", [pts[m] for m in t3], [uvs[m] for m in t3], (0, 1, 0), solid=False,
                              rebase=False, chunk=chunk)
                nstrip += 1
            F.decals.append((min(p[0] for p in lp) - SHORE_OUT, min(p[1] for p in lp) - SHORE_OUT,
                             max(p[0] for p in lp) + SHORE_OUT, max(p[1] for p in lp) + SHORE_OUT, hs))
        # puddle behaviour: walkable behaviour-0 tiles whose centre is under the water (not decks / props)
        nwet = 0
        for t in ok:
            if S.perm[t] & 0x8000 or t in deck_tiles or t in blocked_new:
                continue
            if any(point_in(lp, t[0] + 0.5, t[1] + 0.5) for lp in polys[name]):
                wet.add(t)
                nwet += 1
        report.append(dict(name=name, h=h, loops=len(outer), area=tot_area, tris=ntri, strip=nstrip, wet=nwet,
                           verts=sum(len(lp) for lp in polys[name])))
    return wet, report, polys


# ---------------------------------------------------------------------------------------------------------------
# boardwalks
# ---------------------------------------------------------------------------------------------------------------

def build_boardwalks(F, S):
    """Deck top at ground + 0.06 (over the flood water); skirts; pilings at corners and every 3 tiles along the
    long edges."""
    decks = []
    for x0, z0, x1, z1 in BOARDWALKS:
        hs = {S.ground(t) for t in tiles((x0, z0, x1, z1))}
        assert len(hs) == 1 and None not in hs, f"boardwalk {x0},{z0} not on flat ground: {hs}"
        h = hs.pop()
        X0, X1, Z0, Z1 = x0 + 0.02, x1 + 0.98, z0 + 0.06, z1 + 0.94
        hd = h + DECK_H
        L = X1 - X0
        step = 4.0
        a = X0
        while a < X1 - 1e-6:
            b = min(a + step, X1)
            F.add("board", [(a, hd, Z1), (b, hd, Z1), (b, hd, Z0), (a, hd, Z0)],
                  [((a - X0) / 2, 1), ((b - X0) / 2, 1), ((b - X0) / 2, 0), ((a - X0) / 2, 0)], (0, 1, 0),
                  solid=False, rebase=True)
            F.decals.append((a, Z0, b, Z1, hd))
            F.wall("board", (a, Z1), (b, Z1), h - 0.01, hd, ((a - X0) / 2, 0.97, (b - X0) / 2, 1.0), solid=False)
            a = b
        F.wall("board", (X0, Z0), (X0, Z1), h - 0.01, hd, (0.0, 0.97, 1.0, 1.0), solid=False)
        F.wall("board", (X1, Z1), (X1, Z0), h - 0.01, hd, (0.0, 0.97, 1.0, 1.0), solid=False)
        # a dark wet line under the south edge so the deck reads as standing proud of the water
        hl = h + H_SHORE + 0.006
        F.add("board", [(X0, hl, Z1 + 0.16), (X1, hl, Z1 + 0.16), (X1, hl, Z1), (X0, hl, Z1)],
              [(0, 0.995), (L / 2, 0.995), (L / 2, 0.975), (0, 0.975)], (0, 1, 0), solid=False, rebase=False)
        xs = [float(x) for x in range(x0 + 3, x1, 3)]
        post = cuv("post")
        for px in [X0 + 0.06, X1 - 0.06] + xs:
            tall = px in (X0 + 0.06, X1 - 0.06)
            for pz in (Z0 - 0.02, Z1 + 0.02):
                s = 0.075 if tall else 0.06
                F.box("crate", px - s, pz - s, px + s, pz + s, h - 0.02, hd + (0.42 if tall else 0.12),
                      (post[0], post[1] + (0.07 if tall else 0.09), post[0] + 0.06, post[3]),
                      top=(post[0], post[1] + 0.07, post[0] + 0.03, post[1] + 0.1))
        decks.append((x0, z0, x1, z1, h))
    return decks


# ---------------------------------------------------------------------------------------------------------------
# ruts: filleted, wobbling, mitred quad strips
# ---------------------------------------------------------------------------------------------------------------

def fillet(poly, r):
    """Round every interior corner of a polyline with an arc of radius r (8 steps per quarter turn)."""
    out = [poly[0]]
    for k in range(1, len(poly) - 1):
        a, b, c = poly[k - 1], poly[k], poly[k + 1]
        d1 = ((b[0] - a[0]), (b[1] - a[1]))
        d2 = ((c[0] - b[0]), (c[1] - b[1]))
        l1, l2 = math.hypot(*d1), math.hypot(*d2)
        d1, d2 = (d1[0] / l1, d1[1] / l1), (d2[0] / l2, d2[1] / l2)
        turn = math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1])
        t = r * math.tan(abs(turn) / 2)
        p1 = (b[0] - d1[0] * t, b[1] - d1[1] * t)
        sgn = 1 if turn > 0 else -1
        cen = (p1[0] - d1[1] * r * sgn, p1[1] + d1[0] * r * sgn)
        a0 = math.atan2(p1[1] - cen[1], p1[0] - cen[0])
        steps = max(2, int(abs(turn) / (math.pi / 2) * 8))
        for i in range(steps + 1):
            ang = a0 + turn * i / steps
            out.append((cen[0] + r * math.cos(ang), cen[1] + r * math.sin(ang)))
    out.append(poly[-1])
    return out


def densify(poly, step=1.0):
    out = [poly[0]]
    for a, b in zip(poly, poly[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(round(L / step)))
        for i in range(1, n + 1):
            out.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    return out


def build_ruts(F, S, sheet_polys):
    """Solid packed-mud road bed strips (r215_ruts) with rounded end caps (r215_rutcap). The strip v runs an
    integer number of 4-tile repeats between the caps, so both caps seam onto texture row 0."""
    covered, lanes = [], []
    for pi, poly in enumerate(RUTS):
        pts = densify(fillet(poly, RUT_FILLET), 1.0)
        n = len(pts)
        # tangents / normals, a gentle lateral wobble so the lane never runs ruler-straight
        cen, nor = [], []
        for i in range(n):
            a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
            dx, dz = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dz)
            dx, dz = dx / L, dz / L
            nx, nz = -dz, dx
            w = 0.0 if i in (0, 1, n - 2, n - 1) else 0.10 * math.sin(i * 0.9 + pi) + 0.04 * math.sin(i * 2.3 + 2 * pi)
            cen.append((pts[i][0] + nx * w, pts[i][1] + nz * w))
            nor.append((nx, nz))
        s, vs = 0.0, [0.0]
        for i in range(1, n):
            s += math.hypot(cen[i][0] - cen[i - 1][0], cen[i][1] - cen[i - 1][1])
            vs.append(s)
        hs = set()
        for i in range(n):
            for o in (-0.78, 0.0, 0.78):
                tt = (int(math.floor(cen[i][0] + nor[i][0] * o)), int(math.floor(cen[i][1] + nor[i][1] * o)))
                hs.add(S.ground(tt, behaviours=(0, 2)))
                covered.append(tt)
            if i:
                mx, mz = (cen[i][0] + cen[i - 1][0]) / 2, (cen[i][1] + cen[i - 1][1]) / 2
                for o in (-0.78, 0.78):
                    tt = (int(math.floor(mx + nor[i][0] * o)), int(math.floor(mz + nor[i][1] * o)))
                    hs.add(S.ground(tt, behaviours=(0, 2)))
                    covered.append(tt)
        assert None not in hs and len(hs) == 1, f"ruts {pi} leave flat walkable ground: {hs}"
        h = hs.pop() + H_RUT
        L_ = [(cen[i][0] + nor[i][0], cen[i][1] + nor[i][1]) for i in range(n)]
        R_ = [(cen[i][0] - nor[i][0], cen[i][1] - nor[i][1]) for i in range(n)]
        span = vs[n - 2] - vs[1]
        reps = max(1, round(span / 4.0))
        vv = [(vs[i] - vs[1]) / span * reps for i in range(n)]
        for i in range(1, n - 2):
            q = [(L_[i][0], h, L_[i][1]), (R_[i][0], h, R_[i][1]), (R_[i + 1][0], h, R_[i + 1][1]),
                 (L_[i + 1][0], h, L_[i + 1][1])]
            uvs = [(0.0, vv[i]), (1.0, vv[i]), (1.0, vv[i + 1]), (0.0, vv[i + 1])]
            F.add("ruts", q, uvs, (0, 1, 0), solid=False, rebase=False)
        for seam, tip in ((1, 0), (n - 2, n - 1)):
            q = [(L_[seam][0], h, L_[seam][1]), (R_[seam][0], h, R_[seam][1]), (R_[tip][0], h, R_[tip][1]),
                 (L_[tip][0], h, L_[tip][1])]
            F.add("rutcap", q, [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)], (0, 1, 0), solid=False,
                  rebase=False)
        xs = [p[0] for p in L_ + R_]
        zs = [p[1] for p in L_ + R_]
        F.decals.append((min(xs), min(zs), max(xs), max(zs), h))
        lanes.append(dict(cen=cen, h=h - H_RUT))
    return covered, lanes


# ---------------------------------------------------------------------------------------------------------------
# staging pads: one texel-aligned decal quad each (r215_padn mud, r215_padg gravel apron over the stock blueglayp
# speckled edge), clean 1-texel outline + rim painted in the texture
# ---------------------------------------------------------------------------------------------------------------

X_MAX = 671.75


def build_pads(F, S):
    rep = []
    for name, spec in TX.PADS.items():
        ox, oz = spec["origin"]
        w, hh = spec["size"]
        x1, z1 = min(ox + w / 16.0, X_MAX), oz + hh / 16.0
        M = TX.pad_mask(spec, pad=0)
        tl = set()
        for y, x in zip(*np.nonzero(M)):
            px, pz = ox + (x + 0.5) / 16.0, oz + (y + 0.5) / 16.0
            if px < X_MAX:
                tl.add((int(math.floor(px)), int(math.floor(pz))))
        hs = {S.ground(t, behaviours=(0, 2)) for t in tl} - {None}
        assert len(hs) == 1, f"pad {name} spans several heights {hs}"
        h = hs.pop()
        warps = {(o["x"], o["z"]) for o in S.ev["warp_events"]}      # the gate door: the stock apron runs under it
        bad = [t for t in tl if S.ground(t, behaviours=(0, 2)) is None and not S.tree_base(t, h) and
               not (t in warps and S.h[t] is not None and abs(S.h[t] - h) < 0.01)]
        u1 = (x1 - ox) * 16.0 / w
        key = "padn" if spec["style"] == "mud" else "padg"
        hp = h + H_PAD
        F.add(key, [(ox, hp, z1), (x1, hp, z1), (x1, hp, oz), (ox, hp, oz)], [(0.0, 1.0), (u1, 1.0), (u1, 0.0),
                                                                             (0.0, 0.0)],
              (0, 1, 0), solid=False, rebase=False, chunk=R.chunk_of(int(math.floor((ox + x1) / 2))))
        F.decals.append((ox, oz, x1, z1, hp))
        rep.append(dict(name=name, h=h, tiles=len(tl), bad=bad))
    return rep


H_GRASS = 0.026    # tall grass redrawn over the road bed / pads: above the bed (+0.020), below 'allpeak' (+0.03)


def regrass(F, S, blocked):
    """Tall grass stays tall grass: every walkable behaviour-2 tile that a road bed or pad covers gets the stock
    'nectgr' tile redrawn over it (same texture, palette, material bits and 1-tile UV mapping as the stock ground),
    so no encounter tile ever hides under the mud."""
    covers = []
    for key, pts, uvs in F.faces:
        if key in ("ruts", "rutcap"):
            covers.append(("poly", [(p[0], p[2]) for p in pts]))
    for name, spec in TX.PADS.items():
        covers.append(("mask", (spec, TX.pad_mask(spec, pad=0))))
    out = []
    for t, p in sorted(S.perm.items()):
        if p & 0x8000 or (p & 0xFF) != 2 or t in blocked:
            continue
        hit = False
        for fz in (0.1, 0.3, 0.5, 0.7, 0.9):
            for fx in (0.1, 0.3, 0.5, 0.7, 0.9):
                px, pz = t[0] + fx, t[1] + fz
                for kind, c in covers:
                    if kind == "poly":
                        if min(q[0] for q in c) <= px <= max(q[0] for q in c) and point_in(c, px, pz):
                            hit = True
                    else:
                        spec, M = c
                        ix = int((px - spec["origin"][0]) * 16)
                        iz = int((pz - spec["origin"][1]) * 16)
                        if 0 <= iz < M.shape[0] and 0 <= ix < M.shape[1] and M[iz, ix]:
                            hit = True
        if not hit:
            continue
        h = S.ground(t, behaviours=(2,))
        assert h is not None, f"tall grass tile {t} under the road is not flat"
        x, z, y = t[0], t[1], h + H_GRASS
        F.add("grass", [(x, y, z + 1), (x + 1, y, z + 1), (x + 1, y, z), (x, y, z)],
              [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)], (0, 1, 0), solid=False, rebase=False,
              chunk=R.chunk_of(x))
        out.append(t)
    return out


# ---------------------------------------------------------------------------------------------------------------
# Eclipse staging clusters
# ---------------------------------------------------------------------------------------------------------------

def crate(F, x0, z0, sx, sz, h0, hs, variant=1):
    """Dark-slate Eclipse crate (north face skipped: it always faces away from the field camera)."""
    side = cuv("crate_s" if variant == 1 else "crate2_s")
    top = cuv("crate_t" if variant == 1 else "crate2_t")
    F.box("crate", x0, z0, x0 + sx, z0 + sz, h0, h0 + hs, side, top, sides="sew")


def wcrate(F, x0, z0, sx, sz, h0, hs):
    """Wooden supply crate (r215_props)."""
    F.box("prop", x0, z0, x0 + sx, z0 + sz, h0, h0 + hs, puv("wcrate_s"), puv("wcrate_t"), sides="sew")


def pallet(F, x0, z0, sx, sz, h0):
    F.box("crate", x0, z0, x0 + sx, z0 + sz, h0, h0 + 0.14, cuv("pallet_s"), cuv("pallet_t"), sides="sew")
    return h0 + 0.14


def barrel(F, cx, cz, h0, r=0.19, hb=0.6):
    """Steel drum: a hexagonal prism, only its three camera-facing walls (SW, S, SE) and its lid."""
    V = [(cx + r * math.cos(math.radians(60 * k)), cz + r * math.sin(math.radians(60 * k))) for k in range(6)]
    u0, v0, u1, v1 = puv("barrel_s")
    for k in (2, 1, 0):
        j = 2 - k
        F.wall("prop", V[k + 1], V[k], h0, h0 + hb, (u0 + (u1 - u0) * j / 3, v0, u0 + (u1 - u0) * (j + 1) / 3, v1))
    t0, t1, t2, t3 = puv("barrel_t")
    ht = h0 + hb

    def tuv(p):
        return (t0 + (p[0] - cx + r) / (2 * r) * (t2 - t0), t1 + (p[1] - cz + r) / (2 * r) * (t3 - t1))
    for quad in ((0, 1, 2, 3), (3, 4, 5, 0)):
        F.add("prop", [(V[i][0], ht, V[i][1]) for i in quad], [tuv(V[i]) for i in quad], (0, 1, 0), solid=True,
              rebase=False)


def banner_post(F, x, z, h, ht=1.6, side=1):
    """Team Eclipse warning post: a steel pole with a hazard collar, a cross bar and a hanging violet eclipse banner
    (swallowtail hem) facing the camera; `side` = +1 hangs it east of the pole, -1 west."""
    F.box("prop", x - 0.045, z - 0.045, x + 0.045, z + 0.045, h, h + ht, puv("pole"), puv("bar"), sides="sew")
    xa, xb = (x - 0.02, x + 0.62) if side > 0 else (x - 0.62, x + 0.02)
    F.box("prop", xa, z - 0.03, xb, z + 0.03, h + ht - 0.09, h + ht - 0.02, puv("bar"), puv("bar"), sides="sew")
    ba, bb = (x + 0.07, x + 0.59) if side > 0 else (x - 0.59, x - 0.07)
    u0, v0, u1, v1 = puv("banner")
    zb = z + 0.045
    F.add("prop2", [(ba, h + ht - 0.09, zb), (bb, h + ht - 0.09, zb), (bb, h + ht - 0.83, zb),
                    (ba, h + ht - 0.83, zb)], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], (0, 0, 1), solid=True,
          rebase=False)


def drape(F, x0, z0, x1, z1, htop, drop, k=0):
    """An olive rain tarp thrown over a stack: a top sheet and four skirts hanging out and down, the long sides in
    two panels of different lengths so the hem never runs straight."""
    e, o = 0.04, 0.11
    ht = htop + 0.02
    t0, t1, t2, t3 = cuv("tarp_t")
    F.add("crate2", [(x0 - e, ht, z1 + e), (x1 + e, ht, z1 + e), (x1 + e, ht, z0 - e), (x0 - e, ht, z0 - e)],
          [(t0, t3), (t2, t3), (t2, t1), (t0, t1)], (0, 1, 0), solid=True, rebase=False)
    u0, v0, u1, v1 = cuv("tarp_s")
    sides = [((x0 - e, z1 + e), (x1 + e, z1 + e), (0, 1)), ((x1 + e, z0 - e), (x0 - e, z0 - e), (0, -1)),
             ((x1 + e, z1 + e), (x1 + e, z0 - e), (1, 0)), ((x0 - e, z0 - e), (x0 - e, z1 + e), (-1, 0))]
    for si, ((ax, az), (bx, bz), (nx, nz)) in enumerate(sides):
        parts = 2 if si < 2 else 1
        for p in range(parts):
            t0, t1 = p / parts, (p + 1) / parts
            pa = (ax + (bx - ax) * t0, az + (bz - az) * t0)
            pb = (ax + (bx - ax) * t1, az + (bz - az) * t1)
            d = drop * (0.82 + 0.3 * h01(si, p, 5 + k))
            pts = [(pa[0], ht, pa[1]), (pb[0], ht, pb[1]), (pb[0] + nx * o, ht - d, pb[1] + nz * o),
                   (pa[0] + nx * o, ht - d, pa[1] + nz * o)]
            uu0 = u0 + (u1 - u0) * t0
            uu1 = u0 + (u1 - u0) * t1
            F.add("crate2", pts, [(uu0, v0), (uu1, v0), (uu1, v1), (uu0, v1)], (nx, 0.3, nz), solid=True,
                  rebase=False)


def glow(F, x, hy, z, size=1.3):
    """Smooth A3I5 halo card around a lamp glass, tilted to face the field camera (pitch ~59 deg)."""
    g = guv("halo_amber")
    s = size / 2
    cp, sp = math.cos(math.radians(59.05)), math.sin(math.radians(59.05))
    up = (0.0, cp, -sp)                   # card 'up' axis, perpendicular to the view direction
    pts = []
    for ox, oy in ((-s, s), (s, s), (s, -s), (-s, -s)):
        pts.append((x + ox, hy + up[1] * oy, z + 0.12 + up[2] * oy))
    F.add("halo", pts, [(g[0], g[1]), (g[2], g[1]), (g[2], g[3]), (g[0], g[3])], (0, sp, cp), solid=False,
          rebase=False)


def light_pool(F, x, z, h, rx=1.25, rz=1.0):
    g = guv("pool_amber")
    F.add("pool", [(x - rx, h + 0.039, z + rz), (x + rx, h + 0.039, z + rz), (x + rx, h + 0.039, z - rz),
                   (x - rx, h + 0.039, z - rz)], [(g[0], g[3]), (g[2], g[3]), (g[2], g[1]), (g[0], g[1])],
          (0, 1, 0), solid=False, rebase=False)


def contact_shadow(F, x0, z0, x1, z1, h, pad=0.28):
    g = guv("shadow")
    F.add("shadow", [(x0 - pad, h + 0.037, z1 + pad), (x1 + pad, h + 0.037, z1 + pad),
                     (x1 + pad, h + 0.037, z0 - pad), (x0 - pad, h + 0.037, z0 - pad)],
          [(g[0], g[3]), (g[2], g[3]), (g[2], g[1]), (g[0], g[1])], (0, 1, 0), solid=False, rebase=False)


def lamp_head(F, x, z, hh, halo=1.3):
    """Lamp housing with the unlit amber glass facing south (the camera)."""
    back, cap = cuv("lamp_back"), cuv("lamp_cap")
    F.box("crate", x - 0.17, z - 0.12, x + 0.17, z + 0.06, hh, hh + 0.30, back, cap, sides="new")
    glass = cuv("lamp_amber")
    F.add("lamp", [(x - 0.15, hh + 0.28, z + 0.07), (x + 0.15, hh + 0.28, z + 0.07), (x + 0.15, hh + 0.02, z + 0.09),
                   (x - 0.15, hh + 0.02, z + 0.09)],
          [(glass[0], glass[1]), (glass[2], glass[1]), (glass[2], glass[3]), (glass[0], glass[3])],
          (0, 0.2, 1), solid=True, rebase=False)
    F.box("crate", x - 0.19, z - 0.14, x + 0.19, z + 0.10, hh + 0.30, hh + 0.36, cap, cap)
    glow(F, x, hh + 0.15, z + 0.1, halo)


def mast_lamp(F, x, z, h):
    met = cuv("metal")
    F.box("crate", x - 0.05, z - 0.05, x + 0.05, z + 0.05, h, h + 1.35, (met[0], met[1], met[0] + 0.05, met[3]))
    hz = cuv("hazard")
    F.box("crate", x - 0.065, z - 0.065, x + 0.065, z + 0.065, h + 0.25, h + 0.42, (hz[0], hz[1], hz[0] + 0.12, hz[3]))
    lamp_head(F, x, z, h + 1.30)


def tripod_lamp(F, x, z, h, halo=1.3):
    """A tripod work lamp: three splayed legs, a mast and a lamp head."""
    met = cuv("metal")
    apex = h + 1.05
    for k in range(3):
        a = math.radians(90 + 120 * k + 15)
        fx, fz = x + 0.36 * math.cos(a), z + 0.30 * math.sin(a)
        # leg as a thin two-sided strip from the foot to the apex
        px, pz = -math.sin(a) * 0.035, math.cos(a) * 0.035
        F.add("crate2", [(x + px, apex, z + pz), (x - px, apex, z - pz), (fx - px, h, fz - pz), (fx + px, h, fz + pz)],
              [(met[0], met[1]), (met[0] + 0.04, met[1]), (met[0] + 0.04, met[3]), (met[0], met[3])],
              (math.cos(a), 0.2, math.sin(a)), solid=True, rebase=False)
    F.box("crate", x - 0.045, z - 0.045, x + 0.045, z + 0.045, apex - 0.1, h + 1.48,
          (met[0], met[1], met[0] + 0.05, met[3]))
    lamp_head(F, x, z, h + 1.44, halo)


def build_clusters(F, S):
    blocked = {}
    for name, cl in CLUSTERS.items():
        x0, z0, x1, z1 = cl["block"]
        hs = {S.ground(t, behaviours=(0, 2, PUDDLE)) for t in tiles(cl["block"])}
        assert len(hs) == 1 and None not in hs, f"cluster {name} not on flat ground: {hs}"
        h = hs.pop()
        for t in tiles(cl["block"]):
            blocked[t] = name

        def sh(a, b, c, d, pad=0.16):
            contact_shadow(F, x0 + a, z0 + b, x0 + c, z0 + d, h, pad=pad)
        if cl["kind"] == "yard":
            # the 3x3 north staging yard on its mud pad (front = south = camera side; the road runs along the
            # front, so props rise away from it). Back row: a two-high slate stack, the Eclipse warning banner
            # with two drums, a tall slate + wooden stack. Middle: the tripod work lamp, a tarp-draped stack on a
            # pallet. Front: a pallet of wooden crates, three drums.
            crate(F, x0 + 0.10, z0 + 0.12, 0.92, 0.90, h, 0.86)
            crate(F, x0 + 0.18, z0 + 0.18, 0.76, 0.74, h + 0.86, 0.70, variant=2)
            sh(0.10, 0.12, 1.02, 1.02)
            banner_post(F, x0 + 1.24, z0 + 0.40, h, ht=1.75)
            barrel(F, x0 + 1.52, z0 + 0.78, h)
            barrel(F, x0 + 1.86, z0 + 0.66, h)
            sh(1.30, 0.44, 2.06, 0.98, pad=0.1)
            crate(F, x0 + 2.05, z0 + 0.10, 0.86, 0.88, h, 0.90)
            crate(F, x0 + 2.10, z0 + 0.16, 0.76, 0.76, h + 0.90, 0.80, variant=2)
            wcrate(F, x0 + 2.20, z0 + 0.26, 0.56, 0.52, h + 1.70, 0.44)
            sh(2.05, 0.10, 2.91, 0.98)
            tripod_lamp(F, x0 + 0.52, z0 + 1.48, h)
            light_pool(F, x0 + 0.70, z0 + 1.55, h, rx=1.6, rz=1.25)
            ph = pallet(F, x0 + 1.24, z0 + 1.06, 1.24, 1.10, h)
            crate(F, x0 + 1.34, z0 + 1.12, 1.04, 0.96, ph, 0.82, variant=2)
            drape(F, x0 + 1.34, z0 + 1.12, x0 + 2.38, z0 + 2.08, ph + 0.82, 0.62, k=1)
            sh(1.24, 1.06, 2.48, 2.16)
            ph = pallet(F, x0 + 0.08, z0 + 2.12, 1.10, 0.80, h)
            wcrate(F, x0 + 0.12, z0 + 2.16, 0.52, 0.66, ph, 0.50)
            wcrate(F, x0 + 0.66, z0 + 2.20, 0.48, 0.60, ph, 0.44)
            crate(F, x0 + 0.20, z0 + 2.26, 0.38, 0.40, ph + 0.50, 0.34, variant=2)
            sh(0.08, 2.12, 1.18, 2.92)
            for bx, bz in ((1.66, 2.62), (2.08, 2.50), (2.50, 2.66)):
                barrel(F, x0 + bx, z0 + bz, h)
            sh(1.46, 2.32, 2.70, 2.86, pad=0.1)
        elif cl["kind"] == "gate":
            # 3x3 yard south of the gate approach road, on the gravel apron. The road runs along its NORTH edge, so
            # everything is set back and kept low in front: no prop (projected along the field camera) reaches the
            # road bed. Front: a pallet of wooden crates, two drums, the warning banner. Back (rising over the
            # tree canopy): a tarp-draped stack, a slate + wooden stack, the tripod work lamp.
            ph = pallet(F, x0 + 0.12, z0 + 0.62, 1.18, 0.90, h)
            wcrate(F, x0 + 0.18, z0 + 0.68, 0.52, 0.60, ph, 0.42)
            wcrate(F, x0 + 0.74, z0 + 0.70, 0.48, 0.56, ph, 0.38)
            sh(0.12, 0.62, 1.30, 1.52)
            barrel(F, x0 + 1.62, z0 + 0.86, h)
            barrel(F, x0 + 2.02, z0 + 0.80, h)
            banner_post(F, x0 + 2.62, z0 + 1.08, h, ht=1.5, side=-1)
            sh(1.40, 0.62, 2.70, 1.10, pad=0.1)
            ph = pallet(F, x0 + 0.10, z0 + 1.56, 1.20, 1.10, h)
            crate(F, x0 + 0.18, z0 + 1.62, 1.04, 0.98, ph, 0.92, variant=2)
            drape(F, x0 + 0.18, z0 + 1.62, x0 + 1.22, z0 + 2.60, ph + 0.92, 0.70, k=3)
            crate(F, x0 + 1.40, z0 + 1.58, 0.90, 0.90, h, 0.90)
            crate(F, x0 + 1.46, z0 + 1.64, 0.78, 0.76, h + 0.90, 0.80, variant=2)
            wcrate(F, x0 + 1.56, z0 + 1.88, 0.56, 0.50, h + 1.70, 0.42)
            sh(0.10, 1.56, 2.30, 2.66)
            tripod_lamp(F, x0 + 2.45, z0 + 1.66, h, halo=1.15)
            light_pool(F, x0 + 1.9, z0 + 1.2, h, rx=1.5, rz=1.05)
        else:
            # the south-field cluster under the road's corridor corner: its north row is kept low so nothing
            # projects onto the road bed
            ph = pallet(F, x0 + 0.08, z0 + 0.95, 1.10, 1.00, h)
            crate(F, x0 + 0.14, z0 + 1.02, 0.90, 0.88, ph, 0.82)
            crate(F, x0 + 1.06, z0 + 0.92, 0.86, 0.90, h, 0.84, variant=2)
            drape(F, x0 + 1.06, z0 + 0.92, x0 + 1.92, z0 + 1.82, h + 0.84, 0.62, k=2)
            wcrate(F, x0 + 0.10, z0 + 0.20, 0.62, 0.56, h, 0.48)
            mast_lamp(F, x0 + 1.50, z0 + 0.42, h)
            light_pool(F, x0 + 1.2, z0 + 0.8, h, rx=1.7, rz=1.35)
            sh(0.06, 0.16, 1.94, 1.95, pad=0.18)
    return blocked


def build_signs(F, S):
    blocked = {}
    for name, (x, z) in SIGNS.items():
        h = S.ground((x, z), behaviours=(0, PUDDLE))
        assert h is not None, f"sign {name} not on flat ground"
        blocked[(x, z)] = name
        post = cuv("post")
        board = cuv("board")
        hz = cuv("hazard")
        F.box("crate", x + 0.44, z + 0.44, x + 0.56, z + 0.56, h, h + 0.95, (post[0], post[1] + 0.1, post[0] + 0.07,
                                                                               post[3]))
        lean = 0.22
        F.add("crate2", [(x + 0.08, h + 1.12, z + 0.5 - lean), (x + 0.92, h + 1.12, z + 0.5 - lean),
                         (x + 0.92, h + 0.62, z + 0.62), (x + 0.08, h + 0.62, z + 0.62)],
              [(board[0], board[1]), (board[2], board[1]), (board[2], board[3]), (board[0], board[3])],
              (0, 0.4, 1), solid=True, rebase=False)
        # a gauge stake in the water beside it
        F.box("crate", x + 0.12, z + 0.78, x + 0.2, z + 0.86, h, h + 0.5, (hz[0], hz[1], hz[0] + 0.04, hz[3]))
    return blocked


# ---------------------------------------------------------------------------------------------------------------
# lighting: crisp overcast rain daylight, dark stormy indigo night (lighting_set_000 schema, block times, directions)
# ---------------------------------------------------------------------------------------------------------------

# endTime -> (light 0 colour, diffuse, ambient, specular, emission); 5-bit components. Terrain colour ~
# emission + light0 * (diffuse * N.L + ambient): low emission + strong diffuse = contrast (no flat grey wash).
LIGHT_CURVE = {
    0: ((8, 8, 17), (12, 12, 16), (6, 7, 12), (9, 9, 15), (3, 3, 7)),               # 00:00 stormy indigo night
    7200: ((8, 8, 17), (12, 12, 16), (6, 7, 12), (9, 9, 15), (3, 3, 7)),            # .. 02:00
    8100: ((10, 10, 18), (13, 13, 16), (7, 8, 12), (10, 10, 15), (4, 4, 8)),        # 02:15 pre-dawn
    9000: ((14, 14, 20), (14, 14, 16), (7, 8, 11), (11, 11, 15), (5, 5, 8)),        # 02:30 grey dawn
    14400: ((21, 22, 25), (17, 17, 18), (6, 7, 8), (13, 13, 15), (3, 4, 6)),        # overcast morning
    20700: ((23, 24, 26), (18, 18, 18), (6, 7, 8), (14, 14, 16), (3, 4, 5)),
    21600: ((24, 25, 27), (18, 18, 18), (6, 7, 8), (15, 15, 17), (3, 4, 5)),        # brightest rain light
    27000: ((24, 25, 27), (18, 18, 18), (6, 7, 8), (15, 15, 17), (3, 4, 5)),
    27900: ((23, 24, 26), (18, 18, 18), (6, 7, 8), (14, 14, 16), (3, 4, 5)),
    30600: ((21, 21, 25), (17, 17, 18), (6, 6, 8), (13, 13, 15), (3, 4, 6)),
    32400: ((17, 15, 19), (15, 15, 16), (7, 7, 10), (12, 12, 14), (4, 4, 7)),       # dim stormy dusk
    33300: ((13, 11, 17), (14, 14, 16), (7, 7, 11), (11, 11, 14), (3, 3, 7)),
    34200: ((10, 9, 17), (13, 13, 16), (6, 7, 11), (10, 10, 14), (3, 3, 7)),
    36000: ((8, 8, 17), (12, 12, 16), (6, 7, 12), (9, 9, 15), (3, 3, 7)),           # night
    43200: ((8, 8, 17), (12, 12, 16), (6, 7, 12), (9, 9, 15), (3, 3, 7)),
}


def terrain_rgb(blk, ndl=0.87):
    """Approximate flat-ground colour (0..1 per channel) under a lighting block."""
    out = []
    for ch in ("red", "green", "blue"):
        L = blk["lights"][0]["color"][ch] / 31
        v = blk["emissionColor"][ch] / 31 + L * (blk["diffuseColor"][ch] / 31 * ndl + blk["ambientColor"][ch] / 31)
        out.append(min(1.0, v))
    return out


def build_lighting():
    raw = R.git_file(LIGHTING_TEMPLATE).decode()
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
    notes = []
    for b, t in zip(back, tmpl):
        cols = [b[k] for k in ("diffuseColor", "ambientColor", "specularColor", "emissionColor")] + \
            [lt["color"] for lt in b["lights"]]
        if any(not isinstance(v, int) or not 0 <= v <= 31 for c in cols for v in c.values()):
            fails.append(f"lighting: colour out of 5-bit range at {b['endTime']}")
        if [lt["direction"] for lt in b["lights"]] != [lt["direction"] for lt in t["lights"]]:
            fails.append(f"lighting: light directions changed at {b['endTime']}")
        if b["lights"][1:] != t["lights"][1:]:
            fails.append(f"lighting: sprite lights 1..3 changed at {b['endTime']}")
        g = terrain_rgb(b)
        wall = terrain_rgb(b, ndl=0.25)
        if max(g) < 0.45:
            fails.append(f"lighting: terrain too dark at {b['endTime']} ({[round(v, 2) for v in g]})")
        notes.append((b["endTime"], g, wall))
    day = [n for n in notes if n[0] == 21600][0]
    night = [n for n in notes if n[0] == 0][0]
    if not (day[1][2] > day[1][0] and day[1][0] - day[2][0] > 0.25 and day[1][2] < 0.97):
        fails.append(f"lighting: noon not cool / contrasty enough {day}")
    if not (night[1][2] - night[1][0] > 0.3 and night[1][0] < 0.3):
        fails.append(f"lighting: night not a dark indigo {night}")
    return text, fails, notes


# ---------------------------------------------------------------------------------------------------------------
# build + checks
# ---------------------------------------------------------------------------------------------------------------

def build():
    S = Stock()
    texres = TX.build_set()
    F = Art(texres["table"])
    blocked = {}
    blocked.update(build_clusters(F, S))
    blocked.update(build_signs(F, S))
    wet, sheets, polys = build_sheets(F, S, BOARDWALKS, set(blocked))
    decks = build_boardwalks(F, S)
    ruts, lanes = build_ruts(F, S, polys)
    pads = build_pads(F, S)
    grass = regrass(F, S, set(blocked))
    perm = dict(S.perm)
    for t in wet:
        if (perm[t] & 0xFF) == 0 and not perm[t] & 0x8000:
            perm[t] = (perm[t] & 0xFF00) | PUDDLE
    for t in blocked:
        perm[t] = perm[t] | 0x8000
    out = {}
    for c, cell in R.CHUNKS.items():
        edit = S.chunks[c]["edit"]
        edit.faces.clear()
        edit.new.clear()
        edit.add(F.mb[c], texres["table"])
        model = edit.model_bytes()
        g = [[perm[(cell[0] * 32 + lx, cell[1] * 32 + lz)] for lx in range(32)] for lz in range(32)]
        data = edit.pack(g, model)
        out[c] = dict(edit=edit, model=model, data=data, grid=g, stats=edit.stats(model), polys=F.mb[c].polygons())
    return dict(S=S, F=F, tex=texres, out=out, perm=perm, wet=wet, sheets=sheets, polys=polys, decks=decks,
                blocked=blocked, ruts=ruts, lanes=lanes, pads=pads, grass=grass)


def checks(res):
    S, F, out, perm = res["S"], res["F"], res["out"], res["perm"]
    rs = []
    for c, o in out.items():
        st = o["stats"]
        rs.append((f"map_data_{c:03d}: model {st['model_bytes']} B <= {MODEL_LIMIT} (stock {st['stock_model_bytes']}, "
                   f"+{o['polys']} polygons, {st['polygons']} total)", st["model_bytes"] <= MODEL_LIMIT))
        sec = mapdata.unpack(o["data"])
        rs.append((f"map_data_{c:03d}: BDHC {len(sec['bdhc'])} B <= {BDHC_LIMIT}, byte-identical to stock",
                   len(sec["bdhc"]) <= BDHC_LIMIT and sec["bdhc"] == S.chunks[c]["sec"]["bdhc"]))
        rs.append((f"map_data_{c:03d}: props byte-identical to stock", sec["props"] == S.chunks[c]["sec"]["props"]))
        bmd = nsbmd.parse_bmd(sec["model"])
        rebuilt = nsbmd.build_bmd(bmd["models"])
        rs.append((f"map_data_{c:03d}: NSBMD parse -> rebuild byte-identical", rebuilt == sec["model"]))
        rs.append((f"map_data_{c:03d}: map_data unpack -> pack byte-identical",
                   mapdata.pack(sec["permissions"], sec["props"], sec["model"], sec["bdhc"]) == o["data"]))
        edited = {o["edit"].model["shapes"][si]["name"] for si in o["edit"].faces}
        bad = C.stock_shapes_identical(o["edit"].model, o["edit"].built, edited)
        rs.append((f"map_data_{c:03d}: every stock shape + material byte-identical (cut: {sorted(edited)})", not bad))
    # seams
    edge = [t for t in perm if t[0] in (576, 671)]
    rs.append(("seam columns x 576 / x 671: permissions identical to stock", all(perm[t] == S.perm[t] for t in edge)))
    near = []
    for c, mb in F.mb.items():
        for me in mb.meshes.values():
            for p in me["positions"]:
                if p[0] < 576.25 or p[0] > 671.75 or p[2] < 576.0 or p[2] > 608.0:
                    near.append((c, p))
    rs.append((f"no new geometry within 0.25 tiles of the west/east route edges ({len(near)} vertices)", not near))
    # geometry sanity: no degenerate / sliver faces, no stretched or collapsed UVs (stray-line sources)
    degen = []
    for key, pts, uvs in F.faces:
        def tri_area(a, b, c):
            u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            cr = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            return 0.5 * math.sqrt(sum(x * x for x in cr))
        ar = tri_area(pts[0], pts[1], pts[2]) + (tri_area(pts[0], pts[2], pts[3]) if len(pts) == 4 else 0)
        edges = [math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
        uva = abs(sum(uvs[i][0] * uvs[(i + 1) % len(uvs)][1] - uvs[(i + 1) % len(uvs)][0] * uvs[i][1]
                      for i in range(len(uvs)))) / 2
        bow = False
        if len(pts) == 4 and max(p[1] for p in pts) - min(p[1] for p in pts) < 1e-6:
            def sa(a, b, c):
                return (b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0])
            s1, s2 = sa(pts[0], pts[1], pts[2]), sa(pts[0], pts[2], pts[3])
            s3, s4 = sa(pts[1], pts[2], pts[3]), sa(pts[1], pts[3], pts[0])
            bow = s1 * s2 <= 0 or s3 * s4 <= 0
        if ar < 2e-4 or min(edges) < 0.01 or uva < 1e-7 or bow or max(abs(u) for uv in uvs for u in uv) > 120:
            degen.append((key, [tuple(round(x, 2) for x in p) for p in pts][:2]))
    slivers = []
    for key, pts, uvs in F.faces:
        if key in ("water", "shore") and len(pts) == 3:
            angs = []
            for i in range(3):
                a, b, c = pts[i], pts[(i + 1) % 3], pts[(i + 2) % 3]
                v1 = (b[0] - a[0], b[2] - a[2])
                v2 = (c[0] - a[0], c[2] - a[2])
                cs = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2) + 1e-12)
                angs.append(math.degrees(math.acos(max(-1, min(1, cs)))))
            if min(angs) < 2.0:
                slivers.append((key, round(min(angs), 2), [(round(p[0], 2), round(p[2], 2)) for p in pts]))
    rs.append((f"no sliver water / shore triangles (min angle >= 2 deg): {slivers[:3]}", not slivers))
    rs.append((f"every new face has real area, edges >= 0.01 tiles, no bow-tie (crossed) quads, UVs in range "
               f"({len(F.faces)} faces, bad {degen[:3]})", not degen))
    # flood sheets: 2..3 continuous sheets in the stock sea texture, boardwalks across them, ruts never on water
    shs = res["sheets"]
    rs.append((f"flood sheets: {len(shs)} continuous sheets of stock '{TX.WATER_TEXTURE}' water "
               + ", ".join(f"{s['name']} {s['area']:.1f} tiles^2 / {s['loops']} loop / {s['verts']} verts / "
                           f"{s['tris']} tris + {s['strip']} shore quads / {s['wet']} puddle tiles" for s in shs),
               2 <= len(shs) <= 3 and all(s["loops"] == 1 and s["area"] >= 18 for s in shs)))
    under = []
    for (x0, z0, x1, z1, h) in res["decks"]:
        n = cov = 0
        for xi in range(x0 * 4, (x1 + 1) * 4):
            for zi in range(z0 * 4, (z1 + 1) * 4):
                n += 1
                px, pz = (xi + 0.5) / 4, (zi + 0.5) / 4
                cov += any(point_in(lp, px, pz) for lps in res["polys"].values() for lp in lps)
        under.append(round(cov / n, 2))
    rs.append((f"boardwalks span the flood sheets (water under each deck: {under})", all(u >= 0.55 for u in under)))
    wet_rut = [t for t in res["ruts"] if any(point_in(lp, t[0] + 0.5, t[1] + 0.5)
                                             for lps in res["polys"].values() for lp in lps)]
    rut_x = [t for t in res["ruts"] if any(sh["rect"][0] - 1 <= t[0] <= sh["rect"][2] + 1 and
                                           sh["rect"][1] - 1 <= t[1] <= sh["rect"][3] + 1 for sh in SHEETS.values())]
    rs.append((f"truck ruts only on dry ground (rut tiles under water: {wet_rut[:4]}, near a sheet: {rut_x[:4]})",
               not wet_rut and not rut_x))
    # screen-space clearance: every vertex of every solid prop, slid along the field camera onto the ground
    # (z - height * PROJ), stays off the road bed (lane half-width 1 tile from the centreline)
    def seg_d(px, pz, a, b):
        dx, dz = b[0] - a[0], b[1] - a[1]
        t = max(0.0, min(1.0, ((px - a[0]) * dx + (pz - a[1]) * dz) / (dx * dx + dz * dz)))
        return math.hypot(px - a[0] - t * dx, pz - a[1] - t * dz)
    over = []
    for pts in F.solids:
        for (x, y, z) in pts:
            t = (int(math.floor(x)), int(math.floor(z)))
            g = S.h.get(t)
            if g is None:
                continue
            pz = z - (y - g) * PROJ
            for li, ln in enumerate(res["lanes"]):
                c = ln["cen"]
                d = min(seg_d(x, pz, c[i], c[i + 1]) for i in range(len(c) - 1))
                if d < 1.0:
                    over.append((li, round(x, 2), round(z, 2), round(y - g, 2), round(d, 2)))
    rs.append((f"no prop sits on the road bed on screen (props projected along the field camera; overlaps "
               f"{over[:4]})", not over))
    pr = res["pads"]
    rs.append((f"staging pads on flat dry ground (or tree bases under the canopy): "
               + ", ".join(f"{p['name']} h {p['h']} {p['tiles']} tiles, off-ground {p['bad']}" for p in pr),
               all(not p["bad"] for p in pr)))
    rs.append((f"tall grass under the road / pads redrawn in stock 'nectgr' over the mud ({len(res['grass'])} tiles: "
               f"{res['grass']})", True))
    keys = {k for k, _, _ in F.faces}
    rs.append(("no dithered glow decal: lamp glow is unlit glass + smooth A3I5 halo / pool cards only "
               f"(materials {sorted(keys)})", "glow" not in keys and "puddle" not in keys and
               {"halo", "pool", "shadow", "water", "shore"} <= keys))
    # reachability
    seen0, _ = PA.reach(S.perm)
    seen1, _ = PA.reach(perm)
    lost = seen0 - seen1 - set(res["blocked"])
    rs.append((f"reachability: {len(seen1)} tiles reachable from Route 210, stock {len(seen0)}; only prop tiles "
               f"lost ({len(seen0 - seen1)} = {len(res['blocked'])} blocked)", not lost))
    rs.append(("Veilstone gate warps (671, 598/599) reachable", (670, 598) in seen1 and (670, 599) in seen1))
    ev = S.ev
    evt = {(o["x"], o["z"]): o.get("id", o.get("script")) for k in ("object_events", "bg_events", "warp_events",
                                                                        "coord_events") for o in ev[k]}
    hit = {t: evt[t] for t in res["blocked"] if t in evt}
    rs.append((f"no stock event on a newly blocked tile {hit}", not hit))
    ranges = []
    for o in ev["object_events"]:
        rx, rz = o.get("movement_range_x", 0), o.get("movement_range_z", 0)
        if rx or rz:
            ranges.append((o["id"], o["x"] - rx, o["z"] - rz, o["x"] + rx, o["z"] + rz))
    inr = [(n, t) for t in res["blocked"] for n, a, b, cc, d in ranges if a <= t[0] <= cc and b <= t[1] <= d]
    rs.append((f"blocked tiles inside an NPC wander box (allowed, NPC just skips them): {len(inr)}", True))
    unreachable, stock_unreach = [], []
    for o in ev["object_events"] + ev["bg_events"]:
        t = (o["x"], o["z"])
        nb = [(t[0] + dx, t[1] + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))] + [t]
        if not any(n in seen1 for n in nb):
            unreachable.append(o.get("id", t))
        if not any(n in seen0 for n in nb):
            stock_unreach.append(o.get("id", t))
    rs.append((f"every object/bg event still has a reachable tile (unreachable {unreachable}, stock {stock_unreach})",
               set(map(str, unreachable)) <= set(map(str, stock_unreach))))
    dirs = {"DIR_NORTH": (0, -1), "DIR_SOUTH": (0, 1), "DIR_WEST": (-1, 0), "DIR_EAST": (1, 0)}
    sight = []
    for o in ev["object_events"]:
        if o["trainer_type"] == "TRAINER_TYPE_NONE":
            continue
        ds = [dirs[o["initial_dir"]]]
        if "WEST_AND_EAST" in o["movement_type"]:
            ds = [(-1, 0), (1, 0)]
        for d in ds:
            for k in range(1, 9):
                t = (o["x"] + d[0] * k, o["z"] + d[1] * k)
                if t in res["blocked"]:
                    sight.append((o["id"], t))
    rs.append((f"no prop in a trainer's sight line {sight}", not sight))
    evj = json.load(open(os.path.join(R.ROOT, R.EVENTS_REL)))
    have = {(b["x"], b["z"], b.get("script")) for b in evj["bg_events"]}
    okbg = all((x, z, sc) in have and (x, z) in res["blocked"] and
               any((x + dx, z + dz) in seen1 for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))) for x, z, sc in BG_SIGNS)
    stock_bg = [(b["x"], b["z"], b.get("hidden_item"), b.get("script")) for b in S.ev["bg_events"]]
    new_bg = [(b["x"], b["z"], b.get("hidden_item"), b.get("script")) for b in evj["bg_events"]]
    rs.append((f"BG_EVENT signs {[(x, z) for x, z, _ in BG_SIGNS]} present, on blocked prop tiles, readable from a "
               f"reachable tile; stock bg events kept in order", okbg and new_bg[:len(stock_bg)] == stock_bg))
    rs.append(("object / warp / coord events identical to stock",
               all(evj[k] == S.ev[k] for k in ("object_events", "warp_events", "coord_events"))))
    changed = [t for t in perm if perm[t] != S.perm[t]]
    okb = all((t in res["blocked"] and perm[t] == S.perm[t] | 0x8000) or
              (t in res["wet"] and S.perm[t] == 0 and perm[t] == PUDDLE) for t in changed)
    rs.append((f"permission changes: {len(res['wet'])} puddle tiles (behaviour 0 -> 0x16), {len(res['blocked'])} "
               f"prop tiles blocked; nothing else", okb))
    bad = []
    for pts in F.solids:
        xs, zs, hs = [p[0] for p in pts], [p[2] for p in pts], [p[1] for p in pts]
        for t in {(int(math.floor(x)), int(math.floor(z))) for x in xs for z in zs}:
            if t in perm and not perm[t] & 0x8000:
                x0, z0 = t
                inside = min(xs) < x0 + 0.85 and max(xs) > x0 + 0.15 and min(zs) < z0 + 0.85 and max(zs) > z0 + 0.15
                if inside and min(hs) < (S.h[t] or 0) + 1.3:
                    bad.append(t)
    rs.append((f"no solid prop over a walkable tile's interior {sorted(set(bad))[:8]}", not bad))
    rs.append((f"boardwalks: {len(res['decks'])} decks at BDHC floor + {DECK_H} tiles over flat ground", True))
    faces = [(o["edit"].built, R.CHUNKS[c]) for c, o in out.items()]
    cf = C.camera_faces(faces)
    walk = [t for t in perm if not perm[t] & 0x8000]
    worst, at = C.camera_polys(cf, walk[::3])
    rs.append((f"camera: worst {worst} polygons on screen (at {at}) <= 2048", worst <= 2048))
    vb, vo = res["tex"]["vram"]
    rs.append((f"set 078: VRAM {sum(vb)} -> {sum(vo)} B < {TX.VRAM_TARGET}; round trip: "
               f"{'ok' if not res['tex']['fails'] else res['tex']['fails']}", not res["tex"]["fails"]))
    return rs


def main():
    res = build()
    rs = checks(res)
    ok = True
    for name, good in rs:
        print(("PASS " if good else "FAIL ") + name)
        ok &= good
    ltext, lfails, notes = build_lighting()
    for f in lfails:
        print("FAIL", f)
    for t, g, w in notes:
        if t in (0, 9000, 21600, 32400):
            print(f"  lighting {t:5d}: ground rgb {[round(v, 2) for v in g]}  wall {[round(v, 2) for v in w]}")
    ok &= not lfails
    print(f"blocked {sorted(res['blocked'])}")
    if "--write" in sys.argv:
        assert ok, "refusing to write: a check failed"
        for c, o in res["out"].items():
            open(os.path.join(R.ROOT, R.chunk_rel(c)), "wb").write(o["data"])
        open(os.path.join(R.ROOT, TX.SET_REL), "wb").write(res["tex"]["bytes"])
        open(os.path.join(R.ROOT, LIGHTING_REL), "w").write(ltext)
        print("wrote", ", ".join(R.chunk_rel(c) for c in res["out"]), TX.SET_REL, LIGHTING_REL)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
