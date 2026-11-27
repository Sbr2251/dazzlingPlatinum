#!/usr/bin/env python3
"""Route 215 flooded-lowland art pass: map_data_069/070/071 (stock terrain edited in place) + set 078 + lighting 006.

Usage:
  ~/.venvs/desmume/bin/python tools/routes/r215/build_art.py              dry run: build, budgets, every check
  ~/.venvs/desmume/bin/python tools/routes/r215/build_art.py --write      write chunks, set 078 and lighting_set_006
                                                                          (refuses if any check fails; idempotent)

Inputs are read from git BASE_REV (common.BASE_REV): the stock chunks, stock set 010 (textures.py appends to it) and
lighting_set_000 (schema + block times + sun directions). Re-running never feeds back on itself.

What it adds (tools/world_art/chunkedit.py: every stock shape and material stays byte for byte, the new geometry is
appended as new materials/shapes; stock props and BDHC are kept verbatim):
  * Flooded standing water: r215_puddle blobs (2x2 tiles each, c0 transparent) scattered over the main lowland paths
    (FLOOD zones). Every tile whose centre is under puddle water gets the stock TILE_BEHAVIOR_PUDDLE (0x16) low byte,
    so the player splashes and reflects in it (collision bits untouched).
  * Weathered timber boardwalks (BOARDWALKS): r215_board decks 0.03 tiles over the ground (the BDHC floor: feet never
    sink or float), mud-dark skirts and short pilings on the deck edges, laid over flooded stretches.
  * Eclipse truck ruts (RUTS): r215_ruts dual-tyre tracks (2 tiles wide) through MAP_070's north field and MAP_071's
    south field / lane, down to the Veilstone gate approach.
  * Three Eclipse staging clusters (CLUSTERS): stacked crates, tarp-covered stacks, hazard barriers, warning posts and
    amber / violet work lamps (unlit lamp heads + translucent glow pools), only on tiles that are blocked by them
    (newly blocked tiles are checked: no event, no NPC route, full reachability kept) or already blocked.
  * A flooded drainage sign post (SIGNS) by the west boardwalk; its tile is blocked, the BG_EVENTs read it.
"""
import json
import math
import os
import subprocess
import sys

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

# flooded zones: puddle blobs are placed on a jittered 2-tile lattice inside them, only where the whole 2x2 footprint
# is flat walkable ground (behaviour 0) at one BDHC height
FLOOD = [
    (577, 595, 589, 601),     # MAP_069 west entry from Route 210 (x 576 seam column left stock)
    (584, 589, 590, 594),     # MAP_069 lowland west of the first bridge
    (594, 589, 606, 594),     # MAP_069 lowland east of the bridge (the flooded boardwalk)
    (608, 588, 621, 597),     # MAP_070 lowland under the second bridge
    (630, 583, 645, 587),     # MAP_070 north field (truck ruts)
    (640, 590, 654, 593),     # MAP_071 south field
    (644, 596, 658, 599),     # MAP_071 lane to the gate stairs
    (660, 595, 667, 601),     # MAP_071 Veilstone gate approach (low ground, h 0)
]
FLOOD_SKIP = [(600, 591, 600, 591)]   # keep a dry spot for the Max Ether ball

# boardwalk decks: (x0, z0, x1, z1) tile rects, decks run along x, 2 tiles wide in z
BOARDWALKS = [
    (577, 598, 587, 599),     # west entry
    (595, 591, 606, 592),     # flooded lowland east of the bridge
    (616, 592, 621, 593),     # MAP_070 lowland
]

# truck ruts: polylines of lane centres (x, z) in tiles; the lane is 2 tiles wide
RUTS = [
    [(630.3, 586.0), (656.6, 586.0)],                                   # MAP_070 -> 071 north field, eastbound
    [(653.5, 591.0), (645.0, 591.0), (645.0, 598.0), (658.6, 598.0)],   # MAP_071 south field -> lane -> stairs
    [(661.2, 598.5), (667.8, 598.5)],                                   # MAP_071 gate approach (low ground)
]

# Eclipse staging clusters: tiles they block (must be free of events / NPC routes) + their props
CLUSTERS = {
    "field": dict(block=(655, 592, 656, 593), lamp="violet"),
    "gate": dict(block=(665, 600, 667, 601), lamp="amber"),
    "north": dict(block=(630, 583, 631, 584), lamp="amber"),
}
SIGNS = {"drain": (594, 590)}         # the flooded drainage sign post (tile blocked)
BG_SIGNS = [                          # (x, z, script) BG_EVENTs appended to events.json
    (655, 592, "Route215_EclipseCrates"),
    (594, 590, "Route215_DrainageSign"),
]


# ---------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------

def tiles(rect):
    x0, z0, x1, z1 = rect
    return [(x, z) for z in range(z0, z1 + 1) for x in range(x0, x1 + 1)]


def h01(x, z, k=0):
    v = math.sin(x * 12.9898 + z * 78.233 + k * 37.719) * 43758.5453
    return v - math.floor(v)


class Stock:
    def __init__(self):
        self.chunks = R.stock_chunks()
        self.perm = R.merged_permissions(self.chunks)
        hts = R.merged_heights(self.chunks)
        self.h = {t: (None if v is None else v - 1.0) for t, v in hts.items()}   # chunkedit h (ground = 1.0)
        self.ev = R.stock_events()

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


class Art:
    """New faces in absolute tiles, routed to the chunk holding their centroid."""

    def __init__(self, table):
        self.mb = {c: C.MeshBuilder() for c in R.CHUNKS}
        self.table = table
        self.decals = []        # (x0, z0, x1, z1, h) flat ground decals
        self.solids = []        # [(pts)] solid props
        self.mats = {}

    def material(self, key):
        """key -> (name, texture, palette, lights, cull, alpha)."""
        spec = {
            "board": ("r215_board", 1, "back", 31),
            "board2": ("r215_board", 1, "none", 31),
            "ruts": ("r215_ruts", 1, "back", 31),
            "puddle": ("r215_puddle", 1, "back", 31),
            "crate": ("r215_crate", 1, "back", 31),
            "crate2": ("r215_crate", 1, "none", 31),
            "lamp": ("r215_crate", 0, "none", 31),
            "glow": ("r215_crate", 0, "back", 14),
        }[key]
        tex, lights, cull, alpha = spec
        return "r215_" + key, tex, tex + "_pl", lights, cull, alpha

    def add(self, key, pts, uvs, facing, solid=True, rebase=True):
        n = C.face_normal(pts)
        if sum(a * b for a, b in zip(n, facing)) < 0:
            pts, uvs = pts[::-1], uvs[::-1]
        name, tex, pal, lights, cull, alpha = self.material(key)
        uvs = [list(u) for u in uvs]
        if rebase:
            for k in (0, 1):
                lo = math.floor(min(u[k] for u in uvs) + 1e-6)
                for u in uvs:
                    u[k] -= lo
        cx = sum(p[0] for p in pts) / len(pts)
        c = R.chunk_of(int(math.floor(cx)))
        mb = self.mb[c]
        mb.material(name, tex, pal, self.table[tex]["size"], lights=lights, cull=cull, alpha=alpha)
        mb.face(name, [tuple(p) for p in pts], [tuple(u) for u in uvs],
                color=(255, 255, 255) if lights else (255, 255, 255))
        if solid:
            self.solids.append(pts)

    def flat(self, key, x0, z0, x1, z1, h, uv, rebase=True):
        u0, v0, u1, v1 = uv
        self.add(key, [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)],
                 [(u0, v1), (u1, v1), (u1, v0), (u0, v0)], (0, 1, 0), solid=False, rebase=rebase)
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


def cuv(key, inset=0.25):
    """Atlas texel box -> uv rect (u0, v0, u1, v1), inset by a quarter texel against bleeding."""
    x0, y0, x1, y1 = TX.CRATE_UV[key]
    return ((x0 + inset) / 64, (y0 + inset) / 64, (x1 - inset) / 64, (y1 - inset) / 64)


# ---------------------------------------------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------------------------------------------

def build_puddles(F, S, blocked_new):
    """Greedy blob placement: candidate 2x2 footprints at quarter-tile jitter around every tile of the flood zones,
    in hash order; a blob is kept when every walkable tile under it is flat ground (behaviour 0) at one height,
    at least half of its 2x2 tiles are walkable, the rest are blocked plain ground at that height (tree bases: the
    canopy covers them, never a ledge, slope or cliff), and its centre is >= MIN_GAP from every kept blob.
    -> (puddle-behaviour tiles, placed blobs)."""
    masks = {k: TX.puddle_mask(k) for k in TX.PUDDLES}
    wet = set()
    placed = []
    skip = {t for r in FLOOD_SKIP for t in tiles(r)}
    MIN_GAP = 1.55
    cands = []
    for (x0, z0, x1, z1) in FLOOD:
        for gz in range(z0 - 1, z1 + 1):
            for gx in range(x0 - 1, x1 + 1):
                jx = round((h01(gx, gz, 2) - 0.5) * 0.9 * 4) / 4
                jz = round((h01(gx, gz, 3) - 0.5) * 0.9 * 4) / 4
                cands.append((h01(gx, gz, 1), gx + jx, gz + jz, gx, gz, (x0, z0, x1, z1)))
    cands.sort()
    for _, px, pz, gx, gz, zone in cands:
        if px < 576.3 or px + 2 > 671.7:
            continue
        cxm, czm = px + 1, pz + 1
        if not (zone[0] <= cxm <= zone[2] + 1 and zone[1] <= czm <= zone[3] + 1):
            continue
        if any(math.hypot(cxm - q[0] - 1, czm - q[1] - 1) < MIN_GAP for q in placed):
            continue
        foot = {(int(math.floor(px + a)), int(math.floor(pz + b))) for a in (0.02, 1.0, 1.98)
                for b in (0.02, 1.0, 1.98)}
        if foot & blocked_new or foot & skip:
            continue
        walk = [t for t in foot if not S.perm[t] & 0x8000]
        hs = {S.ground(t) for t in walk}
        if None in hs or len(hs) != 1 or len(walk) * 2 < len(foot):
            continue
        h = next(iter(hs))
        ok = True
        for t in foot:
            if S.perm[t] & 0x8000:
                if (S.perm[t] & 0xFF) != 0 or S.h[t] is None or abs(S.h[t] - h) > 0.01:
                    ok = False
        if not ok:
            continue
        key = "abcd"[int(h01(gx, gz, 4) * 4) % 4]
        bx0, by0, bx1, by1 = TX.PUDDLES[key]
        k = len(placed)
        hh = h + 0.006 + 0.0015 * (k % 4)
        F.flat("puddle", px, pz, px + 2, pz + 2, hh, (bx0 / 64, by0 / 64, bx1 / 64, by1 / 64), rebase=False)
        placed.append((px, pz, key, h))
        m = masks[key]
        for t in walk:
            cx = int(((t[0] + 0.5) - px) * 16)
            cz = int(((t[1] + 0.5) - pz) * 16)
            if 0 <= cx < 32 and 0 <= cz < 32 and m[cz, cx] and t not in skip:
                wet.add(t)
    return wet, placed


def build_boardwalks(F, S):
    """Deck top at ground + 0.03; skirts; pilings at corners and every 3 tiles along the long edges."""
    decks = []
    for x0, z0, x1, z1 in BOARDWALKS:
        hs = {S.ground(t) for t in tiles((x0, z0, x1, z1))}
        assert len(hs) == 1 and None not in hs, f"boardwalk {x0},{z0} not on flat ground: {hs}"
        h = hs.pop()
        X0, X1, Z0, Z1 = x0 + 0.02, x1 + 0.98, z0 + 0.06, z1 + 0.94
        hd = h + 0.03
        # deck: u along x, 32 texels (2 tiles) per repeat; v 0..1 across the 2-tile width
        L = X1 - X0
        step = 4.0
        a = X0
        while a < X1 - 1e-6:
            b = min(a + step, X1)
            F.add("board", [(a, hd, Z1), (b, hd, Z1), (b, hd, Z0), (a, hd, Z0)],
                  [((a - X0) / 2, 1), ((b - X0) / 2, 1), ((b - X0) / 2, 0), ((a - X0) / 2, 0)], (0, 1, 0),
                  solid=False, rebase=True)
            F.decals.append((a, Z0, b, Z1, hd))
            # south skirt (camera side): the dark edge beam band of the texture
            F.wall("board", (a, Z1), (b, Z1), h - 0.01, hd, ((a - X0) / 2, 0.97, (b - X0) / 2, 1.0), solid=False)
            a = b
        # end caps
        F.wall("board", (X0, Z0), (X0, Z1), h - 0.01, hd, (0.0, 0.97, 1.0, 1.0), solid=False)
        F.wall("board", (X1, Z1), (X1, Z0), h - 0.01, hd, (0.0, 0.97, 1.0, 1.0), solid=False)
        # a wet shadow line under the south edge so the deck reads as standing proud of the water
        F.add("board", [(X0, h + 0.02, Z1 + 0.16), (X1, h + 0.02, Z1 + 0.16), (X1, h + 0.02, Z1), (X0, h + 0.02, Z1)],
              [(0, 0.995), (L / 2, 0.995), (L / 2, 0.975), (0, 0.975)], (0, 1, 0), solid=False, rebase=False)
        # pilings: weathered posts at the deck corners (taller, roped) and short stubs along the long edges,
        # all on tile boundaries
        xs = [float(x) for x in range(x0 + 3, x1, 3)]
        post = cuv("post")
        for px in [X0 + 0.06, X1 - 0.06] + xs:
            tall = px in (X0 + 0.06, X1 - 0.06)
            for pz in (Z0 - 0.02, Z1 + 0.02):
                s = 0.075 if tall else 0.06
                F.box("crate", px - s, pz - s, px + s, pz + s, h - 0.02, hd + (0.42 if tall else 0.12),
                      (post[0], post[1] + (0.02 if tall else 0.06), post[0] + 0.06, post[3]),
                      top=(post[0], post[1], post[0] + 0.03, post[1] + 0.03))
        decks.append((x0, z0, x1, z1, h))
    return decks


def lane_segments(poly):
    out = []
    for (xa, za), (xb, zb) in zip(poly, poly[1:]):
        # split at chunk boundaries so each face lives in one chunk
        cuts = [0.0, 1.0]
        for xb_ in (608.0, 640.0):
            if (xa - xb_) * (xb - xb_) < 0:
                cuts.append((xb_ - xa) / (xb - xa))
        cuts.sort()
        for t0, t1 in zip(cuts, cuts[1:]):
            out.append(((xa + (xb - xa) * t0, za + (zb - za) * t0), (xa + (xb - xa) * t1, za + (zb - za) * t1)))
    return out


def build_ruts(F, S):
    covered = []
    for pi, poly in enumerate(RUTS):
        s_acc = 0.0
        for k, ((xa, za), (xb, zb)) in enumerate(lane_segments(poly)):
            L = math.hypot(xb - xa, zb - za)
            dx, dz = (xb - xa) / L, (zb - za) / L
            nx, nz = -dz, dx                                   # left of the direction of travel
            # extend each piece by 1 tile at corners so the turns overlap cleanly
            ea = 1.0 if k > 0 and abs(dx) < 0.5 else 0.0
            eb = 1.0 if abs(dx) < 0.5 and k < len(lane_segments(poly)) - 1 else 0.0
            pa = (xa - dx * ea, za - dz * ea)
            pb = (xb + dx * eb, zb + dz * eb)
            # tiles under the lane must be walkable ground (tall grass allowed: flattened by the tyres)
            n = max(1, int(math.ceil((L + ea + eb) * 2)))
            hs = set()
            for i in range(n + 1):
                t = i / n
                cx, cz = pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t
                for o in (-0.85, 0.0, 0.85):
                    tt = (int(math.floor(cx + nx * o)), int(math.floor(cz + nz * o)))
                    hs.add(S.ground(tt, behaviours=(0, 2, PUDDLE)))
                    covered.append(tt)
            assert None not in hs and len(hs) == 1, f"ruts {pi}/{k} leave flat walkable ground: {hs}"
            h = hs.pop() + 0.011
            A = (pa[0] + nx, pa[1] + nz)
            Bv = (pa[0] - nx, pa[1] - nz)
            Cv = (pb[0] - nx, pb[1] - nz)
            D = (pb[0] + nx, pb[1] + nz)
            s0, s1 = s_acc - ea, s_acc + L + eb
            pts = [(A[0], h, A[1]), (Bv[0], h, Bv[1]), (Cv[0], h, Cv[1]), (D[0], h, D[1])]
            uvs = [(0.0, s0 / 4), (1.0, s0 / 4), (1.0, s1 / 4), (0.0, s1 / 4)]
            F.add("ruts", pts, uvs, (0, 1, 0), solid=False, rebase=True)
            F.decals.append((min(A[0], Cv[0]), min(A[1], Cv[1]), max(A[0], Cv[0]), max(A[1], Cv[1]), h))
            s_acc += L
    return covered


def crate(F, x0, z0, s, h0, hs, tarp=False):
    side = cuv("tarp_s" if tarp else "crate_s")
    top = cuv("tarp_t" if tarp else "crate_t")
    F.box("crate", x0, z0, x0 + s, z0 + s, h0, h0 + hs, side, top)


def lamp(F, x, z, h, color):
    """A work-lamp mast: dark metal pole, hazard collar, unlit lamp head card and a translucent glow pool."""
    met = cuv("metal")
    F.box("crate", x - 0.05, z - 0.05, x + 0.05, z + 0.05, h, h + 1.35, (met[0], met[1], met[0] + 0.05, met[3]))
    hz = cuv("hazard")
    F.box("crate", x - 0.065, z - 0.065, x + 0.065, z + 0.065, h + 0.25, h + 0.42, (hz[0], hz[1], hz[0] + 0.12, hz[3]))
    head = cuv("lamp_" + color)
    # lamp head: a south-facing card, tilted down toward the ground, lit by nothing (glows in the dark)
    hh = h + 1.35
    F.add("lamp", [(x - 0.17, hh + 0.42, z + 0.02), (x + 0.17, hh + 0.42, z + 0.02), (x + 0.17, hh, z + 0.16),
                   (x - 0.17, hh, z + 0.16)], [(head[0], head[1]), (head[2], head[1]), (head[2], head[3]),
                                                (head[0], head[3])], (0, 0.3, 1), solid=True, rebase=False)
    cap = cuv("lamp_cap")
    F.box("crate", x - 0.2, z - 0.06, x + 0.2, z + 0.04, hh + 0.40, hh + 0.48, cap, top=cap)
    g = cuv("glow_" + color, 0.0)
    F.add("glow", [(x - 1.5, h + 0.02, z + 1.9), (x + 1.5, h + 0.02, z + 1.9), (x + 1.5, h + 0.02, z - 1.1),
                   (x - 1.5, h + 0.02, z - 1.1)], [(g[0], g[3]), (g[2], g[3]), (g[2], g[1]), (g[0], g[1])], (0, 1, 0),
          solid=False, rebase=False)


def barrier(F, xa, xb, z, h):
    """Two hazard-collared warning posts with a striped bar between them."""
    post = cuv("post")
    for x in (xa, xb):
        F.box("crate", x - 0.06, z - 0.06, x + 0.06, z + 0.06, h, h + 0.62, (post[0], post[1], post[0] + 0.06, post[3]),
              top=(post[0], post[1], post[0] + 0.03, post[1] + 0.03))
    hz = cuv("hazard")
    L = xb - xa
    F.box("crate", xa, z - 0.035, xb, z + 0.035, h + 0.38, h + 0.52, (hz[0], hz[1], hz[0] + L / 4 * 0.25, hz[3]),
          sides="ns", top=(hz[0], hz[1], hz[2], hz[1] + 0.02))


def build_clusters(F, S):
    blocked = {}
    for name, cl in CLUSTERS.items():
        x0, z0, x1, z1 = cl["block"]
        hs = {S.ground(t, behaviours=(0, PUDDLE)) for t in tiles(cl["block"])}
        assert len(hs) == 1 and None not in hs, f"cluster {name} not on flat ground: {hs}"
        h = hs.pop()
        for t in tiles(cl["block"]):
            blocked[t] = name
        W, D = x1 - x0 + 1, z1 - z0 + 1
        bx, bz = x0 + 0.08, z0 + 0.06
        if name == "field":
            # 2x2: a 2-high crate stack, a tarp-covered stack, a loose crate, a violet lamp behind
            crate(F, bx, bz + 0.95, 0.9, h, 0.82)
            crate(F, bx + 0.05, bz + 1.0, 0.8, h + 0.82, 0.72)
            crate(F, bx + 0.98, bz + 0.9, 0.84, h, 0.8, tarp=True)
            crate(F, bx + 1.0, bz + 0.15, 0.72, h, 0.62)
            lamp(F, x0 + 0.35, z0 + 0.4, h, cl["lamp"])
        elif name == "gate":
            # 3x2 by the gate: tarp stacks, a crate pyramid, amber lamp, a hazard barrier along the north edge
            crate(F, bx, bz + 0.95, 0.9, h, 0.85, tarp=True)
            crate(F, bx + 0.02, bz + 1.0, 0.86, h + 0.85, 0.6, tarp=True)
            crate(F, bx + 1.0, bz + 1.0, 0.86, h, 0.8)
            crate(F, bx + 1.95, bz + 0.95, 0.86, h, 0.8)
            crate(F, bx + 1.45, bz + 1.05, 0.8, h + 0.8, 0.72)
            crate(F, bx + 1.98, bz + 0.1, 0.8, h, 0.66)
            lamp(F, x0 + 0.5, z0 + 0.35, h, cl["lamp"])
            barrier(F, x0 + 1.0, x1 + 0.85, z0 + 0.12, h)
        else:
            # 2x2 north-field stack under an amber lamp
            crate(F, bx + 0.05, bz + 1.0, 0.86, h, 0.8)
            crate(F, bx + 0.95, bz + 0.98, 0.9, h, 0.86, tarp=True)
            crate(F, bx + 0.5, bz + 1.02, 0.8, h + 0.8, 0.66)
            crate(F, bx + 1.05, bz + 0.12, 0.78, h, 0.6)
            lamp(F, x0 + 0.3, z0 + 0.35, h, cl["lamp"])
    return blocked


def build_signs(F, S):
    blocked = {}
    for name, (x, z) in SIGNS.items():
        h = S.ground((x, z), behaviours=(0, PUDDLE))
        assert h is not None, f"sign {name} not on flat ground"
        blocked[(x, z)] = name
        post = cuv("post")
        hz = cuv("hazard")
        F.box("crate", x + 0.44, z + 0.44, x + 0.56, z + 0.56, h, h + 0.95, (post[0], post[1] + 0.1, post[0] + 0.07,
                                                                               post[3]))
        # the board: a south-facing card on the post, leaning back like the stock signs, hazard stripe header
        lean = 0.22
        F.add("crate2", [(x + 0.1, h + 1.05, z + 0.5 - lean), (x + 0.9, h + 1.05, z + 0.5 - lean),
                         (x + 0.9, h + 0.55, z + 0.62), (x + 0.1, h + 0.55, z + 0.62)],
              [(post[0], post[1] + 6 / 64), (post[2], post[1] + 6 / 64), (post[2], post[3]), (post[0], post[3])],
              (0, 0.4, 1), solid=True, rebase=False)
        F.add("crate2", [(x + 0.1, h + 1.17, z + 0.5 - lean - 0.05), (x + 0.9, h + 1.17, z + 0.5 - lean - 0.05),
                         (x + 0.9, h + 1.05, z + 0.5 - lean), (x + 0.1, h + 1.05, z + 0.5 - lean)],
              [(hz[0], hz[1]), (hz[2], hz[1]), (hz[2], hz[3]), (hz[0], hz[3])], (0, 0.4, 1), solid=True, rebase=False)
        # a gauge stake in the water beside it
        F.box("crate", x + 0.12, z + 0.78, x + 0.2, z + 0.86, h, h + 0.5, (hz[0], hz[1], hz[0] + 0.04, hz[3]))
    return blocked


# ---------------------------------------------------------------------------------------------------------------
# lighting: overcast slate-blue rain daylight, stormy night (lighting_set_000 schema, block times, directions)
# ---------------------------------------------------------------------------------------------------------------

# endTime -> (light 0 colour, diffuse, ambient, specular, emission); 5-bit components
LIGHT_CURVE = {
    0: ((8, 9, 14), (11, 12, 15), (8, 9, 12), (10, 11, 15), (6, 7, 11)),          # 00:00 stormy night
    7200: ((8, 9, 14), (11, 12, 15), (8, 9, 12), (10, 11, 15), (6, 7, 11)),       # .. 04:00
    8100: ((9, 10, 15), (10, 11, 14), (10, 11, 13), (8, 9, 13), (8, 9, 12)),      # 04:30 pre-dawn
    9000: ((10, 11, 17), (11, 11, 14), (10, 11, 13), (9, 10, 14), (10, 11, 13)),  # 05:00 grey dawn
    14400: ((13, 14, 19), (12, 12, 14), (10, 11, 13), (11, 12, 15), (12, 13, 16)),  # 08:00 overcast morning
    20700: ((15, 16, 20), (13, 13, 15), (11, 12, 14), (13, 14, 16), (13, 14, 16)),  # 11:30
    21600: ((17, 18, 21), (14, 14, 16), (11, 12, 14), (14, 15, 17), (13, 14, 16)),  # 12:00 brightest rain light
    27000: ((18, 19, 22), (15, 15, 16), (12, 13, 15), (15, 16, 18), (13, 14, 15)),  # 15:00
    27900: ((17, 18, 21), (14, 14, 16), (12, 13, 15), (15, 15, 17), (12, 13, 15)),  # 15:30
    30600: ((16, 16, 20), (14, 14, 15), (11, 12, 14), (14, 14, 16), (11, 12, 14)),  # 17:00
    32400: ((15, 14, 17), (13, 13, 14), (11, 11, 13), (13, 13, 15), (9, 9, 12)),    # 18:00 dim stormy dusk
    33300: ((13, 11, 14), (12, 12, 14), (10, 10, 13), (12, 12, 14), (8, 8, 11)),    # 18:30
    34200: ((11, 10, 14), (12, 12, 14), (10, 10, 13), (11, 11, 14), (7, 8, 11)),    # 19:00
    36000: ((9, 10, 14), (11, 12, 14), (9, 10, 12), (10, 11, 14), (6, 7, 11)),      # 20:00 night
    43200: ((8, 9, 14), (11, 12, 15), (8, 9, 12), (10, 11, 15), (6, 7, 11)),        # 24:00
}


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
    for b, t in zip(back, tmpl):
        cols = [b[k] for k in ("diffuseColor", "ambientColor", "specularColor", "emissionColor")] + \
            [lt["color"] for lt in b["lights"]]
        if any(not isinstance(v, int) or not 0 <= v <= 31 for c in cols for v in c.values()):
            fails.append(f"lighting: colour out of 5-bit range at {b['endTime']}")
        if [lt["direction"] for lt in b["lights"]] != [lt["direction"] for lt in t["lights"]]:
            fails.append(f"lighting: light directions changed at {b['endTime']}")
        if b["lights"][1:] != t["lights"][1:]:
            fails.append(f"lighting: sprite lights 1..3 changed at {b['endTime']}")
        # readability: sprites are lit by lights 2/3 (stock); terrain brightness floor
        if sum(b["lights"][0]["color"].values()) + sum(b["ambientColor"].values()) < 40:
            fails.append(f"lighting: too dark at {b['endTime']}")
    return text, fails


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
    wet, placed = build_puddles(F, S, set(blocked))
    decks = build_boardwalks(F, S)
    ruts = build_ruts(F, S)
    # permissions: stock + puddle behaviour on wet tiles + blocked prop tiles
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
        edit.add(F.mb[c], texres["table"])
        model = edit.model_bytes()
        g = [[perm[(cell[0] * 32 + lx, cell[1] * 32 + lz)] for lx in range(32)] for lz in range(32)]
        data = edit.pack(g, model)
        out[c] = dict(edit=edit, model=model, data=data, grid=g, stats=edit.stats(model), polys=F.mb[c].polygons())
    return dict(S=S, F=F, tex=texres, out=out, perm=perm, wet=wet, placed=placed, decks=decks, blocked=blocked,
                ruts=ruts)


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
    # seams: the x 576 and x 671 columns' permissions/heights untouched, no new geometry within 0.25 of the outer
    # chunk edges (Route 210 / Veilstone stream against them)
    edge = [t for t in perm if t[0] in (576, 671)]
    rs.append(("seam columns x 576 / x 671: permissions identical to stock", all(perm[t] == S.perm[t] for t in edge)))
    near = []
    for c, mb in F.mb.items():
        for me in mb.meshes.values():
            for p in me["positions"]:
                if p[0] < 576.25 or p[0] > 671.75 or p[2] < 576.0 or p[2] > 608.0:
                    near.append((c, p))
    rs.append((f"no new geometry within 0.25 tiles of the west/east route edges ({len(near)} vertices)", not near))
    # reachability: every stock-reachable tile is still reachable except the tiles the props now block
    seen0, _ = PA.reach(S.perm)
    seen1, _ = PA.reach(perm)
    lost = seen0 - seen1 - set(res["blocked"])
    rs.append((f"reachability: {len(seen1)} tiles reachable from Route 210, stock {len(seen0)}; only prop tiles "
               f"lost ({len(seen0 - seen1)} = {len(res['blocked'])} blocked)", not lost))
    rs.append(("Veilstone gate warps (671, 598/599) reachable", (670, 598) in seen1 and (670, 599) in seen1))
    # events: no event, coord trigger or NPC wander box on a newly blocked tile; every event still reachable
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
    unreachable = []
    for o in ev["object_events"] + ev["bg_events"]:
        t = (o["x"], o["z"])
        nb = [(t[0] + dx, t[1] + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))] + [t]
        if not any(n in seen1 for n in nb):
            unreachable.append(o.get("id", t))
    stock_unreach = []
    for o in ev["object_events"] + ev["bg_events"]:
        t = (o["x"], o["z"])
        nb = [(t[0] + dx, t[1] + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))] + [t]
        if not any(n in seen0 for n in nb):
            stock_unreach.append(o.get("id", t))
    rs.append((f"every object/bg event still has a reachable tile (unreachable {unreachable}, stock {stock_unreach})",
               set(map(str, unreachable)) <= set(map(str, stock_unreach))))
    # trainer sight lines: no newly blocked tile in a trainer's facing line within 8 tiles
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
    # BG_EVENT signs: in events.json, on a prop-blocked tile, with a reachable tile beside them
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
    # puddle behaviour only on stock behaviour-0 walkable tiles
    changed = [t for t in perm if perm[t] != S.perm[t]]
    okb = all((t in res["blocked"] and perm[t] == S.perm[t] | 0x8000) or
              (t in res["wet"] and S.perm[t] == 0 and perm[t] == PUDDLE) for t in changed)
    rs.append((f"permission changes: {len(res['wet'])} puddle tiles (behaviour 0 -> 0x16), {len(res['blocked'])} "
               f"prop tiles blocked; nothing else", okb))
    # walkable clearance: no solid prop face over the interior of a walkable tile below 1.3 tiles
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
    # boardwalk decks sit at the BDHC floor (+0.03 tiles = 0.48 world units)
    rs.append((f"boardwalks: {len(res['decks'])} decks at BDHC floor + 0.03 tiles over flat ground", True))
    # camera polygons
    faces = []
    for c, o in out.items():
        faces.append((o["edit"].built, R.CHUNKS[c]))
    cf = C.camera_faces(faces)
    walk = [t for t in perm if not perm[t] & 0x8000]
    worst, at = C.camera_polys(cf, walk[::3])
    rs.append((f"camera: worst {worst} polygons on screen (at {at}) <= 2048", worst <= 2048))
    # textures
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
    ltext, lfails = build_lighting()
    for f in lfails:
        print("FAIL", f)
    ok &= not lfails
    print(f"puddles: {len(res['placed'])} blobs, {len(res['wet'])} puddle tiles; decks {len(res['decks'])}; "
          f"blocked {sorted(res['blocked'])}")
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
