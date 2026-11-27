#!/usr/bin/env python3
"""Route 223 - Rift Sea Route & Waterfall Summit art pass, v2 (docs/routes_wave2/PLAN.md, arc3 scenes 3.15-3.17).

Writes map_texture_set_082 (textures.py), map_data_092..095 (stock chunks + appended geometry, plus the new carved
stone landings in permissions and BDHC) and lighting_set_010.

Usage (Python with NumPy):
  ~/.venvs/desmume/bin/python tools/routes/r223/build_art.py            dry run: build, budgets, every check
  ~/.venvs/desmume/bin/python tools/routes/r223/build_art.py --write    write the set, the four chunks and the lighting
                                                                         (refuses on any FAIL)
  ~/.venvs/desmume/bin/python tools/routes/r223/build_art.py --mesh DIR also dump DIR/chunk_NNN.mesh.json

Inputs: the stock chunks, stock set 013 and lighting_set_000 from git STOCK_REV (the routes-wave2 contract commit,
before any Route 223 art), never the work tree, so reruns never feed back; textures.py for the appended textures.

Geography (stock, surveyed with dump_stock.py): open sea (model h -0.5, BDHC 8 = where the player surfs) with low
cliff rocks (tops h 0.5) and domed boulders. The waterfall itself (x 840..855, z 604) and the Victory Road summit
belong to MAP_113 (Pokemon League header, not this package), so the summit sanctuary is built on MAP_092's two rock
horns that frame the 3-tile Surf channel (x 846..848) running north to the plunge pool and the falls:

  MAP_092  Waterfall Summit Sanctuary: a carved basalt battle terrace on each horn - a raised dais (h 0.62) with
           carved Greek-key walls, flagstone paving and parapets with corner posts, a lower step terrace (h 0.31)
           to the south, carved steps, and a walkable stone pier landing (h 0.0, BDHC 16) where the player steps off
           Surf right beside the monolith: west pier x 845 z 610..611 (in the horn's notch on the channel side),
           east pier x 851 z 610..611 (outer side of the east horn). The twin Dialga / Palkia rune monoliths stand
           on the daises, chunky crystal-iron chains drape from them onto the terrace posts and paving, and the
           Rift Resonance Seal is a half-submerged ring of 12 carved rim blocks (rune-inlaid tops just above the
           water, white foam lapping inside and out) in the channel between them. The channel stays open water.
  MAP_094  Kingdra Sea-Rift Rock: the 6-sided twisted Rift Crystal spire, base crystals and orbiting shards on
           rock 850..855 x 692..697, in clean flat facets; three faceted crystal arcs orbiting the spire as a broken
           halo; a carved stone landing x 851..852 z 698 (h 0.0) on the reading tiles south of the rock with a step up.
  MAP_093  a mid-route crystal cluster on the central island rock.
  MAP_095  South Sea Approach: two crystal outcrops and a carved stone landing east of the rock at x 849..850
           z 726..729 (was shallow water 0x17; h 0.0, holds the Heart Scale hidden item tile), foam round the landing
           and the rock's waterline.
  All four: the stock shallow-sea overlay (asasea, a hard-edged translucent box under the storm light) is redrawn
           as plain sea (shallows_to_sea); no glyph-band rift cracks or rune-band halo cards.

Stock shapes keep their display lists and materials byte for byte (new materials and shapes are appended); props
are untouched; permissions and BDHC change only on the LANDINGS tiles (behaviour 0x0000 walkable, BDHC plate at
16 = model h 0.0, rebuilt as non-overlapping rectangles, every other tile height identical to stock).

Checks (--write refuses on any FAIL): set 082 round trip + VRAM (textures.py); per chunk: model <= 0xF000, BDHC
<= 0x9000, NSBMD parse -> rebuild byte-identical, stock shapes and materials byte-identical, props identical,
permissions identical except the landings (exactly 0x0000), BDHC height at every tile centre = stock except the
landings (= 16), every new material bound to a set-082 texture with matching size, solid geometry standing only on
blocked rock or the chunk's own landing tiles (the seal ring alone on water and never above h SEA_H + 0.3), decals
on blocked tiles / water as designed, no event or landing tile hidden from the field camera; route-wide: the Surf
network from Sunyshore (z 735) reaches the plunge pool row (z 608 x 840..855), the channel, every swimmer and
everything it reached in stock (minus the landing tiles), and every landing touches it; lighting schema / times /
directions as stock.
"""
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "world_art"))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import chunkedit as C  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import textures as TX  # noqa: E402

STOCK_REV = TX.STOCK_REV
BASE_REV = STOCK_REV
OUT_MAP_DIR = "res/field/mapmodels/data"
CHUNKS = {92: (26, 19), 93: (26, 20), 94: (26, 21), 95: (26, 22)}
MODEL_BUFFER = 0xF000            # include/overlay005/loaded_map_buffers.h MAP_MODEL_FILE_SIZE
BDHC_BUFFER = 0x9000             # include/constants/field/bdhc.h BDHC_BUFFER_SIZE
SEA_H = -0.5                     # model h of the sea surface (BDHC 8 = where the player surfs)
LAND_H = 0.0                     # model h of the walkable stone landings (BDHC 16)
STEP_H = 0.31                    # lower terrace / carved steps
DAIS_H = 0.62                    # raised sanctuary dais
FOOT = SEA_H - 0.06              # walls run just below the waterline
FX = 4096
SEA_BDHC = 8 * FX
LAND_BDHC = int((nsbmd.GROUND_Y + LAND_H * nsbmd.TILE) * FX)
WALK = 0x0000                    # permission of a landing tile: TILE_BEHAVIOR_NONE, not blocked
EVENTS_REL = "res/field/maps/route_223/events.json"
CAM = (0.0, math.sin(math.radians(59.05)), math.cos(math.radians(59.05)))   # towards the field camera

# landmark anchors (absolute tiles)
WEST_MONO = (843.95, 611.0)      # on the west dais (rock 843..844 x 610..611)
EAST_MONO = (849.95, 612.0)      # on the east dais (rock 849..850 x 610..612)
SEAL = (847.5, 612.5)            # centre of the stone ring in the channel (x 846..848, z 611..613)
SEAL_R = (0.9, 1.36)             # inner / outer radius of the rim blocks
SPIRE = (853.0, 694.9)           # Kingdra rock x 850..855, z 692..697
CLUSTERS = {93: [((845.0, 652.6), 2.2, 31)], 95: [((841.9, 721.8), 1.8, 41), ((847.4, 727.6), 1.4, 43)]}
# walkable carved stone landings: chunk -> absolute tiles (permission WALK, BDHC LAND_BDHC)
LANDINGS = {92: [(845, 610), (845, 611), (849, 615), (849, 616)],
            94: [(851, 698), (852, 698)],
            95: [(x, z) for z in range(726, 730) for x in (849, 850)]}
SURF_START_Z = 735               # Sunyshore end of the route (south edge of MAP_095)
PLUNGE_POOL = [(x, 608) for x in range(840, 856)]    # north edge of MAP_092 below the falls (MAP_113)
# showcase viewpoints (dry stone): (name, x, z, facing)
SHOWCASE = [("summit_terrace_west_pier", 845, 610, "DIR_NORTH"),
            ("kingdra_rift_landing", 852, 698, "DIR_NORTH"),
            ("south_sea_landing", 850, 726, "DIR_NORTH")]

# materials: name -> (texture, cull, lights)   (all unlit with baked vertex colours, like the monoliths: the carved
# stone keeps its key-lit faces readable in the storm night and matches the monolith plinths it carries)
MATS = {"r223_rift_u": ("r223_rift", "back", 0), "r223_pil_u": ("r223_pillar", "back", 0),
        "r223_chn_u": ("r223_chain", "none", 0), "r223_dec_u": ("r223_chain", "back", 0),
        "r223_band_u": ("r223_chain", "none", 0), "r223_pave_l": ("r223_pave", "back", 0),
        "r223_ter_l": ("r223_terrace", "back", 0), "r223_rune_u": ("r223_terrace", "back", 0),
        "r223_foam_l": ("r223_foam", "back", 0)}


# ---------------------------------------------------------------------------------------------------------------
# vector helpers
# ---------------------------------------------------------------------------------------------------------------

def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(v):
    n = math.sqrt(dot(v, v)) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def face_n(pts):
    n = cross(sub(pts[1], pts[0]), sub(pts[2], pts[0]))
    if len(pts) == 4 and dot(n, n) < 1e-12:
        n = cross(sub(pts[2], pts[0]), sub(pts[3], pts[0]))
    return norm(n)


def clamp8(v):
    return max(0, min(255, int(round(v))))




KEY = norm((-0.45, 0.78, 0.43))   # baked key light: upper left, towards the camera (storm-lit from the rift)


def shade(n, base, glow=0.0, amb=0.55, key=0.55, rim=(0.0, 0.0, 0.0)):
    """Baked colour: base RGB (0..255) * (ambient + key * N.L) + additive glow (0..1 of white-ish) + rim."""
    d = max(0.0, dot(n, KEY))
    f = amb + key * d
    return tuple(clamp8(base[k] * f + 255 * glow + rim[k]) for k in range(3))


# ---------------------------------------------------------------------------------------------------------------
# face builder (per chunk): chunkedit.MeshBuilder with per-vertex colours and outward winding
# ---------------------------------------------------------------------------------------------------------------

class Builder(C.MeshBuilder):
    def __init__(self, tex):
        super().__init__()
        self.tex = tex
        self.solids = []          # (pts, group) of every non-decal face, for the footprint / clearance checks
        self.decals = []          # (pts, group, where) flat decals: where "rock" (blocked tiles) or "water"
        self.groups = {}
        self.footprint = {}       # group -> [xmin, zmin, xmax, zmax, hmax]
        for name, (t, cull, lights) in MATS.items():
            self.material(name, t, TX.pal_name(t), tex["table"][t]["size"], lights=lights, cull=cull)

    def add(self, mat, pts, uvs, colors, inside=None, group="misc", solid=True, cam_cull=True, decal=None):
        """pts (x, h, z) absolute tiles; colors: one RGB or one per vertex. inside: a point the face must face away
        from (fixes the winding). Faces the camera can never see are dropped (cam_cull) when the material culls.
        decal: "rock" / "water" / "stone" for flat non-solid decals (checked against the tiles under them)."""
        pts = [tuple(float(c) for c in p) for p in pts]
        if len({tuple(round(c, 5) for c in p) for p in pts}) < 3:
            return
        n = face_n(pts)
        if inside is not None:
            cen = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
            if dot(n, sub(cen, inside)) < 0:
                pts, uvs = pts[::-1], uvs[::-1]
                if isinstance(colors, list):
                    colors = colors[::-1]
                n = mul(n, -1)
        if cam_cull and MATS[mat][1] == "back" and dot(n, CAM) < -0.2:
            return
        cols = colors if isinstance(colors, list) else [colors] * len(pts)
        # rebase UVs by whole repeats (world-aligned tiling stays aligned; NSBMD UVs are limited to +-2048 texels)
        du, dv = math.floor(min(u[0] for u in uvs) + 1e-9), math.floor(min(u[1] for u in uvs) + 1e-9)
        uvs = [(u[0] - du, u[1] - dv) for u in uvs]
        me = self.meshes[mat]
        b = len(me["positions"])
        me["positions"] += [list(p) for p in pts]
        me["uvs"] += [list(u) for u in uvs]
        me["colors"] += [list(c) for c in cols]
        me["normals"] += [list(n)] * len(pts)
        (me["quads"] if len(pts) == 4 else me["tris"]).append(list(range(b, b + len(pts))))
        self.groups[group] = self.groups.get(group, 0) + 1
        fp = self.footprint.setdefault(group, [1e9, 1e9, -1e9, -1e9, -1e9])
        for p in pts:
            fp[0], fp[1], fp[2], fp[3], fp[4] = min(fp[0], p[0]), min(fp[1], p[2]), max(fp[2], p[0]), \
                max(fp[3], p[2]), max(fp[4], p[1])
        if solid:
            self.solids.append((pts, group))
        elif decal:
            self.decals.append((pts, group, decal))
        return n


def uvbox(box, w=32, h=32, inset=0.15):
    x0, y0, x1, y1 = box
    return ((x0 + inset) / w, (y0 + inset) / h, (x1 - inset) / w, (y1 - inset) / h)


def band_v(band, inset=0.15):
    y0, y1 = TX.TERRACE_V[band]
    return (y0 + inset) / 32, (y1 - inset) / 32


# ---------------------------------------------------------------------------------------------------------------
# crystals: clean flat-shaded facets (each facet = one r223_rift strip chosen by its light)
# ---------------------------------------------------------------------------------------------------------------

def facet_style(n, t):
    """t = relative height (0 base .. 1 tip) of the facet centre."""
    d = dot(n, KEY)
    if d > 0.62:
        return "hot" if t > 0.55 else "lit"
    if d > 0.12:
        return "mid"
    return "shadow"


def facet_uv(style, width):
    """u range of one facet: the whole strip (outline + ridge + fill) when the facet is wide enough to carry them at
    ~16 texels per tile, only the flat fill when it is a sliver (no sub-pixel outline shimmer)."""
    k = TX.RIFT_STRIPS[style]
    lo = 8 * k + (0.15 if width >= 0.3 else 2.15)
    return lo / 32, (8 * k + 7.85) / 32


FACET_COL = {"shadow": (225, 225, 240), "mid": (245, 245, 255), "lit": (255, 255, 255), "hot": (255, 255, 255)}


def crystal_face(B, pts, inside, h0, h1, group, mat="r223_rift_u"):
    n = face_n(pts)
    cen = tuple(sum(p[q] for p in pts) / len(pts) for q in range(3))
    if dot(n, sub(cen, inside)) < 0:
        n = mul(n, -1)
    t = max(0.0, min(1.0, (cen[1] - h0) / max(0.01, h1 - h0)))
    style = facet_style(n, t)
    width = math.sqrt(dot(sub(pts[1], pts[0]), sub(pts[1], pts[0])))
    u0, u1 = facet_uv(style, width)
    v0, v1 = 0.1, 0.9
    if len(pts) == 3:                            # (a, b, apex): the outline runs along a -> apex
        uvs = [(u0, v1), (u1, v1), (u0, v0)]
    else:                                        # (a, b, c, d) = ring i j, ring i k, ring i+1 k, ring i+1 j
        uvs = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
    B.add(mat, pts, uvs, FACET_COL[style], inside=inside, group=group)


def prism(B, center, profile, segs, ang0=0.0, twist=0.0, tilt=None, group="crystal"):
    """Faceted crystal: rings (r, h) bottom to top around center (x, z) (last r 0 = point), each ring rotated by
    `twist` radians more than the one below. tilt: (axis_dir unit (dx, dy, dz), base (x, h, z)) leans the crystal
    along that axis instead of standing it up (h then measures along the axis). Flat-shaded facets."""
    cx, cz = center
    rings = []
    for i, (r, h) in enumerate(profile):
        ring = []
        for j in range(segs):
            a = ang0 + twist * i + 2 * math.pi * j / segs
            if tilt is None:
                ring.append((cx + r * math.sin(a), h, cz + r * math.cos(a)))
            else:
                ax, base = tilt
                e1 = norm(cross(ax, (0.0, 0.0, 1.0)) if abs(ax[2]) < 0.9 else cross(ax, (1.0, 0.0, 0.0)))
                e2 = norm(cross(e1, ax))
                off = add(mul(e1, r * math.cos(a)), mul(e2, r * math.sin(a)))
                ring.append(add(add(base, mul(ax, h)), off))
        rings.append(ring)
    hs = [p[1] for ring in rings for p in ring]
    h0, h1 = min(hs), max(hs)
    axis_pt = lambda i: (sum(p[0] for p in rings[i]) / segs, sum(p[1] for p in rings[i]) / segs,  # noqa: E731
                         sum(p[2] for p in rings[i]) / segs)
    for i in range(len(profile) - 1):
        top_pole = profile[i + 1][0] == 0
        inside = mul(add(axis_pt(i), axis_pt(i + 1)), 0.5)
        for j in range(segs):
            k = (j + 1) % segs
            a, b = rings[i][j], rings[i][k]
            c, d = rings[i + 1][k], rings[i + 1][j]
            crystal_face(B, [a, b, c] if top_pole else [a, b, c, d], inside, h0, h1, group)


def bipyramid(B, c, r, hh, ang, tilt=0.0, group="shards"):
    """A floating fractured shard: a 4-sided bipyramid of half-height hh, radius r, yawed by ang, leaned by tilt."""
    ax = norm((math.sin(ang) * math.sin(tilt), math.cos(tilt), math.cos(ang) * math.sin(tilt)))
    e1 = norm(cross(ax, (0.0, 0.0, 1.0)))
    e2 = norm(cross(e1, ax))
    eq = [add(c, add(mul(e1, r * math.cos(a + ang)), mul(e2, r * math.sin(a + ang)))) for a in
          (0.0, math.pi / 2, math.pi, 3 * math.pi / 2)]
    top, bot = add(c, mul(ax, hh)), add(c, mul(ax, -hh))
    for k in range(4):
        p, q = eq[k], eq[(k + 1) % 4]
        for tip in (top, bot):
            crystal_face(B, [p, q, tip], c, c[1] - hh, c[1] + hh, group)


# ---------------------------------------------------------------------------------------------------------------
# chains, decals, rings
# ---------------------------------------------------------------------------------------------------------------

CHAIN_V = (0.15 / 32, 11.85 / 32)
CRACK_UV = (0.0, 20.2 / 32, 1.0, 31.8 / 32)
BAND_V = (12.2 / 32, 19.8 / 32)


def chain(B, a, b, sag, width=0.62, group="chains", links_per_tile=0.85, segs=6):
    """A chunky crystal-iron chain hanging from a to b ((x, h, z)) with a parabolic sag (tiles): a camera-facing
    ribbon whose links run continuously along u (one oval + one crystal link per 1 / links_per_tile tiles)."""
    pts = []
    for i in range(segs + 1):
        t = i / segs
        p = add(mul(a, 1 - t), mul(b, t))
        pts.append((p[0], p[1] - 4 * sag * t * (1 - t), p[2]))
    u = 0.0
    v0, v1 = CHAIN_V
    for i in range(segs):
        p, q = pts[i], pts[i + 1]
        d = norm(sub(q, p))
        side = norm(cross(d, CAM))              # ribbon width direction, perpendicular to the chain and the view
        w = mul(side, width / 2)
        ln = math.sqrt(dot(sub(q, p), sub(q, p)))
        un = u + ln * links_per_tile
        quad = [add(p, w), add(q, w), sub(q, w), sub(p, w)]
        n = face_n(quad)
        cols = [shade(n if dot(n, CAM) > 0 else mul(n, -1), (240, 235, 255), glow=0.04, amb=0.86, key=0.2)] * 4
        B.add("r223_chn_u", quad, [(u, v0), (un, v0), (un, v1), (u, v1)], cols, group=group, cam_cull=False)
        u = un


def chain_flat(B, a, b, h, width=0.56, group="chains_flat", links_per_tile=0.85):
    """A loose chain length lying flat on the terrace paving from a to b ((x, z))."""
    d = norm((b[0] - a[0], 0.0, b[1] - a[1]))
    side = (-d[2] * width / 2, 0.0, d[0] * width / 2)
    pa, pb = (a[0], h, a[1]), (b[0], h, b[1])
    ln = math.hypot(b[0] - a[0], b[1] - a[1])
    v0, v1 = CHAIN_V
    quad = [add(pa, side), add(pb, side), sub(pb, side), sub(pa, side)]
    B.add("r223_chn_u", quad, [(0, v0), (ln * links_per_tile, v0), (ln * links_per_tile, v1), (0, v1)],
          [(232, 226, 250)] * 4, inside=(a[0], h - 1, a[1]), group=group, solid=False, cam_cull=False, decal="stone")


def cracks(B, x0, z0, x1, z1, h, group="cracks", flip=False):
    """Glowing rift cracks decal (flat, rows 20..31 of r223_chain) on a rock top."""
    u0, v0, u1, v1 = CRACK_UV
    if flip:
        v0, v1 = v1, v0
    pts = [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)]
    B.add("r223_dec_u", pts, [(u0, v1), (u1, v1), (u1, v0), (u0, v0)], [(235, 225, 255)] * 4, group=group,
          solid=False, decal="rock")


def crystal_arcs(B, c, r, tilt, yaw, arcs=((0.35, 1.75), (2.45, 3.85), (4.55, 5.95)), thick=0.085, segs=6,
                 group="arcs"):
    """Clean stylized crystal arcs: each arc a diamond-section blade swept around a tilted circle of radius r about
    c, tapering to a point at both ends, built from flat crystal facets (fill only at this width: crisp edges, no
    1-px sparkle). The arcs together read as a broken halo around the spire."""
    nrm = norm((math.sin(yaw) * math.sin(tilt), math.cos(tilt), math.cos(yaw) * math.sin(tilt)))
    e1 = norm(cross(nrm, (0.0, 0.0, 1.0)))
    e2 = norm(cross(e1, nrm))
    hs = []
    for a0, a1 in arcs:
        secs, axis = [], []
        for i in range(segs + 1):
            a = a0 + (a1 - a0) * i / segs
            rad = add(mul(e1, math.sin(a)), mul(e2, math.cos(a)))
            ctr = add(c, mul(rad, r))
            k = thick * math.sin(math.pi * i / segs) ** 0.6
            secs.append([add(ctr, mul(rad, k)), add(ctr, mul(nrm, k)), sub(ctr, mul(rad, k)), sub(ctr, mul(nrm, k))])
            axis.append(ctr)
            hs.append(ctr[1])
        h0, h1 = min(hs) - thick, max(hs) + thick
        for i in range(segs):
            inside = mul(add(axis[i], axis[i + 1]), 0.5)
            for j in range(4):
                k = (j + 1) % 4
                if i == 0:
                    crystal_face(B, [secs[1][k], secs[1][j], axis[0]], inside, h0, h1, group)
                elif i == segs - 1:
                    crystal_face(B, [secs[i][j], secs[i][k], axis[segs]], inside, h0, h1, group)
                else:
                    crystal_face(B, [secs[i][j], secs[i][k], secs[i + 1][k], secs[i + 1][j]], inside, h0, h1, group)


def floating_ring(B, c, r0, r1, tilt, yaw, segs=28, repeats=7, gaps=(4, 5, 13, 21, 22), group="ring"):
    """The fractured rune ring floating around the Kingdra spire: a tilted double-sided band (rows 12..19 of
    r223_chain), broken at `gaps` segments."""
    nrm = norm((math.sin(yaw) * math.sin(tilt), math.cos(tilt), math.cos(yaw) * math.sin(tilt)))
    e1 = norm(cross(nrm, (0.0, 0.0, 1.0)))
    e2 = norm(cross(e1, nrm))
    v0, v1 = BAND_V
    for j in range(segs):
        if j in gaps:
            continue
        a0, a1 = 2 * math.pi * j / segs, 2 * math.pi * (j + 1) / segs
        p = lambda r, a: add(c, add(mul(e1, r * math.sin(a)), mul(e2, r * math.cos(a))))  # noqa: E731
        u0, u1 = repeats * j / segs, repeats * (j + 1) / segs
        pts = [p(r1, a0), p(r1, a1), p(r0, a1), p(r0, a0)]
        B.add("r223_band_u", pts, [(u0, v1), (u1, v1), (u1, v0), (u0, v0)], [(170, 235, 255)] * 4,
              inside=sub(c, nrm), group=group, solid=False, cam_cull=False)


# ---------------------------------------------------------------------------------------------------------------
# carved stone kit: blocks, parapets, posts, foam
# ---------------------------------------------------------------------------------------------------------------

STONE = (232, 228, 244)


def stone_col(n, k=1.0):
    return shade(n, STONE, amb=0.60 * k, key=0.42 * k)


def block(B, x0, x1, z0, z1, h1, h0=FOOT, top="pave", band="wall", faces="sewn", foot=None, group="terrace"):
    """A carved basalt block: flagstone (or rune-inlay) top at h1, carved side walls (TERRACE_V band, tiling along
    their length at 16 texels per tile, the band's sea-dark foot at the bottom) down to h0 (per side via foot)."""
    foot = foot or {}
    mid = ((x0 + x1) / 2, (h0 + h1) / 2 - 0.3, (z0 + z1) / 2)
    if top == "pave":
        pts = [(x0, h1, z1), (x1, h1, z1), (x1, h1, z0), (x0, h1, z0)]
        B.add("r223_pave_l", pts, [(p[0] / 2, p[2] / 2) for p in pts], stone_col((0, 1, 0)), inside=mid,
              group=group)
    elif top == "rune":
        rv0, rv1 = band_v("rune")
        pts = [(x0, h1, z1), (x1, h1, z1), (x1, h1, z0), (x0, h1, z0)]
        along_x = (x1 - x0) >= (z1 - z0)
        uvs = [((p[0] if along_x else p[2]) / 2, rv0 if (p[2] == z0 if along_x else p[0] == x0) else rv1)
               for p in pts]
        B.add("r223_rune_u", pts, uvs, (255, 255, 255), inside=mid, group=group)
    corners = {"s": ((x0, z1), (x1, z1)), "e": ((x1, z1), (x1, z0)), "n": ((x1, z0), (x0, z0)),
               "w": ((x0, z0), (x0, z1))}
    bv0, bv1 = band_v(band)
    for f in faces:
        (ax, az), (bx, bz) = corners[f]
        lo = foot.get(f, h0)
        if lo >= h1 - 1e-6:
            continue
        pts = [(ax, lo, az), (bx, lo, bz), (bx, h1, bz), (ax, h1, az)]
        ua, ub = (ax / 2, bx / 2) if f in "sn" else (az / 2, bz / 2)
        # the band's lit lip sits at the top; for low faces only the upper part of the band is used
        span = min(1.0, (h1 - lo) / (1.0 if band == "wall" else 0.5))
        vlo = bv0 + (bv1 - bv0) * span
        n = face_n(pts)
        B.add("r223_ter_l", pts, [(ua, vlo), (ub, vlo), (ub, bv0), (ua, bv0)], stone_col(n), inside=mid,
              group=group)


def post(B, x, z, h0, hgt, r=0.13, group="posts", crystal=False):
    """A square carved post with a projecting cap (and an optional little rift crystal finial)."""
    block(B, x - r, x + r, z - r, z + r, h0 + hgt, h0=h0, band="riser", group=group)
    block(B, x - r - 0.04, x + r + 0.04, z - r - 0.04, z + r + 0.04, h0 + hgt + 0.08, h0=h0 + hgt, band="riser",
          group=group)
    if crystal:
        prism(B, (x, z), [(0.05, h0 + hgt + 0.06), (0.07, h0 + hgt + 0.2), (0.0, h0 + hgt + 0.42)], 4, ang0=0.4,
              group=group)
    return (x, h0 + hgt + 0.02, z)


def offset_outline(poly, d, closed):
    """Offset a polyline [(x, z)] by d to its left (mitre joins). Left of travel in (x right, z down) coordinates."""
    n = len(poly)
    out = []
    for i in range(n):
        if not closed and i in (0, n - 1):
            a, b = (poly[0], poly[1]) if i == 0 else (poly[-2], poly[-1])
            dx, dz = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dz)
            nx, nz = dz / ln, -dx / ln
            out.append((poly[i][0] + nx * d, poly[i][1] + nz * d))
            continue
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]
        n1 = norm((p1[1] - p0[1], 0.0, -(p1[0] - p0[0])))
        n2 = norm((p2[1] - p1[1], 0.0, -(p2[0] - p1[0])))
        m = norm((n1[0] + n2[0], 0.0, n1[2] + n2[2]))
        k = d / max(0.3, dot(m, n1))
        out.append((p1[0] + m[0] * k, p1[1] + m[2] * k))
    return out


def foam_outline(B, poly, closed=True, width=0.34, h=SEA_H + 0.05, phase=0, group="foam"):
    """Dithered white foam lapping along a stone outline on the water: poly [(x, z)] traversed with the water on
    its left (offset_outline), mitred corners so no two strips overlap."""
    outer = offset_outline(poly, width, closed)
    v0, v1 = (TX.FOAM_V[phase][0] + 0.15) / 32, (TX.FOAM_V[phase][1] - 0.15) / 32
    m = len(poly) if closed else len(poly) - 1
    u = 0.0
    for i in range(m):
        j = (i + 1) % len(poly)
        a, b, bo, ao = poly[i], poly[j], outer[j], outer[i]
        ln = math.hypot(b[0] - a[0], b[1] - a[1])
        pts = [(a[0], h, a[1]), (b[0], h, b[1]), (bo[0], h, bo[1]), (ao[0], h, ao[1])]
        uvs = [(u, v0), (u + ln * 0.5, v0), (u + ln * 0.5, v1), (u, v1)]
        B.add("r223_foam_l", pts, uvs, (255, 255, 255), inside=(a[0], h - 1, a[1]), group=group, solid=False,
              decal="water")
        u += ln * 0.5


def foam_ring(B, c, r_stone, r_out, segs=36, h=SEA_H + 0.065, phase=1, repeats=5, group="seal_foam"):
    v0, v1 = (TX.FOAM_V[phase][0] + 0.15) / 32, (TX.FOAM_V[phase][1] - 0.15) / 32
    for j in range(segs):
        a0, a1 = 2 * math.pi * j / segs, 2 * math.pi * (j + 1) / segs
        p = lambda r, a: (c[0] + r * math.sin(a), h, c[1] + r * math.cos(a))  # noqa: E731
        u0, u1 = repeats * j / segs, repeats * (j + 1) / segs
        pts = [p(r_stone, a0), p(r_stone, a1), p(r_out, a1), p(r_out, a0)]
        B.add("r223_foam_l", pts, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], (255, 255, 255),
              inside=(c[0], h - 1, c[1]), group=group, solid=False, decal="water")


def stone_ring(B, c, r0, r1, n_blocks=12, gap=0.06, group="seal"):
    """The Rift Resonance Seal: n_blocks weathered carved rim blocks in a ring, tops just above the water with the
    rune inlay band glowing along them (u around the ring, v across), outer and inner faces in riser stone."""
    rv0, rv1 = band_v("rune")
    sv0, sv1 = band_v("riser")
    tops = [-0.27, -0.22, -0.29, -0.24, -0.21, -0.33, -0.25, -0.22, -0.28, -0.23, -0.26, -0.30]
    bot = SEA_H - 0.12
    cen = (c[0], bot - 0.5, c[1])
    for k in range(n_blocks):
        a0 = 2 * math.pi * k / n_blocks + gap / 2
        a1 = 2 * math.pi * (k + 1) / n_blocks - gap / 2
        h = tops[k % len(tops)]
        tilt = 0.03 if k == 5 else 0.0                       # one sunken, tipped block
        p = lambda r, a, y: (c[0] + r * math.sin(a), y, c[1] + r * math.cos(a))  # noqa: E731
        sub_n = 3
        for s in range(sub_n):
            b0 = a0 + (a1 - a0) * s / sub_n
            b1 = a0 + (a1 - a0) * (s + 1) / sub_n
            rm = (r0 + r1) / 2
            u0, u1 = b0 * rm / 2, b1 * rm / 2                # 16 texels per tile around the ring
            h0s, h1s = h - tilt * s, h - tilt * (s + 1)
            top = [p(r1, b0, h0s), p(r1, b1, h1s), p(r0, b1, h1s), p(r0, b0, h0s)]
            B.add("r223_rune_u", top, [(u0, rv1), (u1, rv1), (u1, rv0), (u0, rv0)], (255, 255, 255),
                  inside=cen, group=group)
            for r, inward in ((r1, False), (r0, True)):
                q = [p(r, b0, bot), p(r, b1, bot), p(r, b1, h1s), p(r, b0, h0s)]
                inside = (c[0], -0.4, c[1]) if not inward else p(r + 0.5, (b0 + b1) / 2, -0.4)
                n = face_n(q)
                hv = sv0 + (sv1 - sv0) * min(1.0, (h - SEA_H + 0.12) / 0.5)
                B.add("r223_ter_l", q, [(u0, hv), (u1, hv), (u1, sv0), (u0, sv0)], stone_col(n), inside=inside,
                      group=group)
        for a, hh in ((a0, h), (a1, h - tilt * sub_n)):     # radial end faces (visible across the gaps)
            q = [p(r0, a, bot), p(r1, a, bot), p(r1, a, hh), p(r0, a, hh)]
            mida = (a0 + a1) / 2
            B.add("r223_ter_l", q, [(0.0, sv1), (0.25, sv1), (0.25, sv0), (0.0, sv0)], stone_col(face_n(q)),
                  inside=p((r0 + r1) / 2, mida, -0.45), group=group)


# ---------------------------------------------------------------------------------------------------------------
# stock survey helpers
# ---------------------------------------------------------------------------------------------------------------

def stock_tops(edit):
    """{(x, z): max model h of the stock faces over that tile} (sampled at face vertices and centroids)."""
    tops = {}
    for si, tex, pal in edit.iter_shapes():
        tris, quads = edit._faces(si)
        for f in tris + quads:
            pts = [edit.tile(v["pos"]) for v in f]
            cen = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
            for p in pts + [cen]:
                for x in (math.floor(p[0] - 1e-6), math.floor(p[0] + 1e-6)):
                    for z in (math.floor(p[2] - 1e-6), math.floor(p[2] + 1e-6)):
                        tops[(x, z)] = max(tops.get((x, z), -9.0), p[1])
        edit.faces.pop(si, None)          # decoding only: the shape stays byte-identical
    return tops


def boulder_tiles(edit):
    """Tiles under the stock domed sea boulders (texture searock, up to h 0.96): never decal or anchor there."""
    out = set()
    for si, tex, pal in edit.iter_shapes():
        if tex != "searock":
            continue
        tris, quads = edit._faces(si)
        for f in tris + quads:
            pts = [edit.tile(v["pos"]) for v in f]
            c = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
            for p in pts + [c]:
                q = [p[k] + (c[k] - p[k]) * 0.02 for k in range(3)]      # nudged inside the face
                out.add((math.floor(q[0]), math.floor(q[2])))
        edit.faces.pop(si, None)
    return out


# terrace footprints (x0, x1, z0, z1) that cover stock domed boulders, which would poke through the paving
TERRACE_RECTS = {92: [(843.0, 845.0, 610.0, 612.0), (844.0, 846.0, 612.0, 614.0), (849.0, 851.0, 611.0, 615.0),
                      (850.0, 852.0, 610.0, 611.0)]}


def drop_buried_boulders(edit, rects):
    """Remove the stock sea boulders (texture searock) whose dome centre lies under a terrace: each boulder is one
    connected set of faces; it goes whole or not at all. -> (names of the edited stock shapes, boulders removed)."""
    if not rects:
        return set(), 0
    faces = []
    for si, tex, pal in edit.iter_shapes():
        if tex != "searock":
            continue
        tris, quads = edit._faces(si)
        for f in tris + quads:
            faces.append((si, tuple(tuple(round(c, 4) for c in edit.tile(v["pos"])) for v in f)))
    parent = list(range(len(faces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    owner = {}
    for i, (si, pts) in enumerate(faces):
        for p in pts:
            if p in owner:
                parent[find(i)] = find(owner[p])
            else:
                owner[p] = i
    blobs = {}
    for i in range(len(faces)):
        blobs.setdefault(find(i), []).append(i)
    doomed = set()
    for members in blobs.values():
        pts = [p for i in members for p in faces[i][1]]
        cx = sum(p[0] for p in pts) / len(pts)
        cz = sum(p[2] for p in pts) / len(pts)
        if any(x0 <= cx <= x1 and z0 <= cz <= z1 for x0, x1, z0, z1 in rects):
            doomed |= {faces[i][1] for i in members}
    for si in {faces[i][0] for i in range(len(faces))}:
        edit.faces.pop(si, None)
    if not doomed:
        return set(), 0
    edit.drop(lambda tex, pal, c, pts: tuple(tuple(round(q, 4) for q in p) for p in pts) in doomed,
              textures={"searock"})
    names = {edit.model["shapes"][si]["name"] for si in edit.faces}
    return names, len([1 for m in blobs.values() if faces[m[0]][1] in doomed])


def shallows_to_sea(edit):
    """The stock shallow-sea overlay (texture asasea) reads as a hard-edged translucent lavender box under the rift
    storm lighting. Its faces fill holes cut in the sea surface, so they move, unchanged (same h -0.5 positions, same
    world-aligned 1-repeat-per-tile UVs as the sea), into the stock sea shape and are drawn with the stock sea
    material (seamless, animated with the rest of the sea); the emptied asasea shape is removed. Permissions keep
    the stock shallow behaviour. -> names of the two edited stock shapes."""
    sea = [si for si, tex, pal in edit.iter_shapes() if tex == "sea"]
    sha = [si for si, tex, pal in edit.iter_shapes() if tex == "asasea"]
    if not sha:
        return set()
    assert len(sea) == 1, "expected one stock sea shape"
    st, sq = edit._faces(sea[0])
    for si in sha:
        t, q = edit._faces(si)
        st, sq = st + t, sq + q
        edit.faces[si] = ([], [])
    edit.faces[sea[0]] = (st, sq)
    return {edit.model["shapes"][si]["name"] for si in sea + sha}


def blocked(perm, cx, cz, x, z):
    lx, lz = x - cx * 32, z - cz * 32
    if not (0 <= lx < 32 and 0 <= lz < 32):
        return None
    return bool(perm[lz][lx] & 0x8000)


# ---------------------------------------------------------------------------------------------------------------
# the twin rune monoliths
# ---------------------------------------------------------------------------------------------------------------

def monolith(B, center, top_h, runes, side_sign, group):
    """Tapered basalt monolith on a rock (center x, z; base on the rock top top_h). runes 'blue' / 'rose' select the
    carved rune panel shown on its south face and its channel-side face (side_sign +1: east face, -1: west face)."""
    cx, cz = center
    pu = TX.PILLAR_UV
    panel = uvbox(pu[runes])
    plain = uvbox(pu["plain"])
    base = top_h - 0.08
    stone = (226, 222, 250)

    def col(n, h, glow_k=0.0):
        t = (h - base) / 4.2
        return shade(n, stone, glow=0.02 + glow_k, amb=0.72 + 0.10 * t, key=0.36, rim=(8, 4, 18))

    def frustum(hx0, hz0, hx1, hz1, h0, h1, faces, uvs_for, glow_k=0.0, cap=None):
        lo = [(cx - hx0, h0, cz + hz0), (cx + hx0, h0, cz + hz0), (cx + hx0, h0, cz - hz0), (cx - hx0, h0, cz - hz0)]
        hi = [(cx - hx1, h1, cz + hz1), (cx + hx1, h1, cz + hz1), (cx + hx1, h1, cz - hz1), (cx - hx1, h1, cz - hz1)]
        mid = (cx, (h0 + h1) / 2, cz)
        sides = {"s": (lo[0], lo[1], hi[1], hi[0]), "e": (lo[1], lo[2], hi[2], hi[1]),
                 "n": (lo[2], lo[3], hi[3], hi[2]), "w": (lo[3], lo[0], hi[0], hi[3])}
        for s in faces:
            pts = list(sides[s])
            u0, v0, u1, v1 = uvs_for(s)
            uvs = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
            n = face_n(pts)
            if dot(n, sub(tuple(sum(p[k] for p in pts) / 4 for k in range(3)), mid)) < 0:
                n = mul(n, -1)
            B.add("r223_pil_u", pts, uvs, [col(n, p[1], glow_k) for p in pts], inside=mid, group=group)
        if cap is not None:
            u0, v0, u1, v1 = cap
            B.add("r223_pil_u", hi[::-1] if False else [hi[0], hi[1], hi[2], hi[3]],
                  [(u0, v1), (u1, v1), (u1, v0), (u0, v0)], [col((0, 1, 0), h1)] * 4, inside=(cx, h0, cz), group=group)

    rune_face = "e" if side_sign > 0 else "w"
    # plinth: two stepped blocks
    frustum(0.78, 0.62, 0.74, 0.58, base, top_h + 0.22, "sewn", lambda s: plain, cap=plain)
    frustum(0.62, 0.50, 0.60, 0.48, top_h + 0.22, top_h + 0.40, "sewn", lambda s: plain, cap=plain)
    # shaft: carved rune panels on the south face and the channel-side face
    h0, h1 = top_h + 0.40, top_h + 3.55
    hm = (h0 + h1) / 2           # two stacked panel repeats keep the runes at ~16 texels per tile
    frustum(0.46, 0.36, 0.41, 0.32, h0, hm, "sewn", lambda s: panel if s in ("s", rune_face) else plain)
    frustum(0.41, 0.32, 0.36, 0.28, hm, h1, "sewn", lambda s: panel if s in ("s", rune_face) else plain)
    # pyramidion cap
    apex = (cx, h1 + 0.55, cz)
    ring = [(cx - 0.36, h1, cz + 0.28), (cx + 0.36, h1, cz + 0.28), (cx + 0.36, h1, cz - 0.28),
            (cx - 0.36, h1, cz - 0.28)]
    for k in range(4):
        tri = [ring[k], ring[(k + 1) % 4], apex]
        n = face_n(tri)
        if dot(n, sub(mul(add(add(tri[0], tri[1]), tri[2]), 1 / 3), (cx, h1, cz))) < 0:
            n = mul(n, -1)
        u0, v0, u1, v1 = plain
        B.add("r223_pil_u", tri, [(u0, v1), (u1, v1), ((u0 + u1) / 2, v0)], [col(n, p[1]) for p in tri],
              inside=(cx, h1 + 0.1, cz), group=group)
    # a glowing rune capstone crystal set into the pyramidion
    prism(B, (cx, cz), [(0.10, h1 + 0.45), (0.13, h1 + 0.62), (0.0, h1 + 0.98)], 4, ang0=0.4, group=group)
    # rift scar: violet crystal shards bursting out of the outer side of the shaft
    out = -side_sign
    hw = lambda h: 0.46 - 0.10 * (h - h0) / (h1 - h0)    # noqa: E731  shaft half width (x) at height h
    for k, (hh, ln, yaw, r) in enumerate(((h0 + 1.0, 0.62, 0.35, 0.09), (h0 + 1.55, 0.48, -0.25, 0.075),
                                          (h0 + 2.2, 0.55, 0.15, 0.085))):
        ax = norm((out * math.cos(yaw), 0.55, math.sin(yaw) * 0.6 + 0.25))
        basep = (cx + out * 0.34, hh, cz + 0.05 * (k - 1))
        prism(B, (0, 0), [(r, 0.0), (r * 1.15, ln * 0.45), (0.0, ln)], 4, ang0=0.3 * k, tilt=(ax, basep),
              group=group)
    # chain anchors: points just proud of the shaft faces
    ha, hb = top_h + 2.75, top_h + 2.15
    return {"east": (cx + hw(ha) + 0.02, ha, cz), "west": (cx - hw(hb) - 0.02, hb, cz),
            "south": (cx - 0.12 * side_sign, top_h + 1.7, cz + 0.36 - 0.06 * (1.7 - 0.40) / 3.15 + 0.03)}



# ---------------------------------------------------------------------------------------------------------------
# MAP_092: the Waterfall Summit Sanctuary
# ---------------------------------------------------------------------------------------------------------------

def terrace_west(B):
    """West horn: dais A (843..845 x 610..612, h DAIS_H) carrying the Dialga monolith, lower terrace B (844..846 x
    612..614, h STEP_H) to the south, the walkable pier (845 x 610..611, h LAND_H) in the notch on the channel side,
    a carved stair from the pier up onto the dais between two cheek blocks, parapets and posts. Returns the posts."""
    xe, xs = 845.97, 844.75                      # water-side faces stay inside their tiles; xs: the stair's back
    block(B, 843.0, xs, 610.0, 611.998, DAIS_H, faces="w", group="dais")
    block(B, 843.0, 844.0, 611.998, 611.999, DAIS_H, top=None, faces="s", group="dais")
    block(B, 844.0, xs, 611.998, 611.999, DAIS_H, h0=STEP_H, top=None, faces="s", group="dais")
    block(B, xs, 845.0, 610.0, 610.35, DAIS_H, faces="se", foot={"e": LAND_H, "s": STEP_H}, group="dais")
    block(B, xs, 845.0, 611.65, 612.0, DAIS_H, faces="se", foot={"e": LAND_H, "s": STEP_H}, group="dais")
    block(B, xs, 845.0, 610.35, 611.65, STEP_H, h0=LAND_H, faces="e", band="riser", group="steps")
    block(B, xs - 1e-3, xs, 610.35, 611.65, DAIS_H, h0=STEP_H, top=None, faces="e", band="riser", group="steps")
    block(B, 844.0, xe, 612.0, 613.97, STEP_H, faces="sew", group="terrace")
    # pier landing: flagstones level with the BDHC landing plate, a glowing rune inlay along its channel edge
    block(B, 845.0, xe, 610.03, 611.99, LAND_H, faces="e", band="riser", group="landing")
    block(B, 845.76, xe, 610.03, 611.99, LAND_H + 0.004, h0=LAND_H, top="rune", faces="", group="landing_inlay")
    # parapets with carved posts
    block(B, 843.0, 844.48, 610.0, 610.2, DAIS_H + 0.26, h0=DAIS_H, faces="sew", band="riser", group="parapet")
    block(B, 844.0, xe, 613.77, 613.97, STEP_H + 0.24, h0=STEP_H, faces="sew", band="riser", group="parapet")
    block(B, 845.77, xe, 612.0, 613.77, STEP_H + 0.24, h0=STEP_H, faces="sew", band="riser", group="parapet")
    posts = {"nw": post(B, 843.14, 610.14, DAIS_H, 0.44), "ne": post(B, 844.52, 610.14, DAIS_H, 0.44),
             "sw": post(B, 843.14, 611.86, DAIS_H, 0.44), "se": post(B, 845.82, 613.82, STEP_H, 0.36),
             "pier": post(B, 845.83, 610.17, LAND_H, 0.42, r=0.11, crystal=True)}
    foam_outline(B, [(843.0, 610.0), (xe, 610.0), (xe, 613.97), (844.0, 613.97), (844.0, 612.0), (843.0, 612.0)])
    return posts


def terrace_east(B):
    """East horn (rock 849..850 x 611..614 with 850..851 x 610): dais C (849..851 x 611..613, h DAIS_H) carrying
    the Palkia monolith, a step terrace C2 over the horn's north tip (850..852 x 610), the lower terrace D
    (849..851 x 613..615, h STEP_H) and, off its south tip, the walkable pier (849 x 615..616, h LAND_H) on the
    channel's east bank with a half step up onto D. Parapets and posts. Returns the posts."""
    x0, xc = 849.0, 850.97
    block(B, x0, xc, 611.0, 613.0, DAIS_H, faces="w", group="dais")
    block(B, 850.0, 851.97, 610.03, 610.998, STEP_H, faces="ew", foot={"w": STEP_H}, group="terrace")
    block(B, 850.97, 851.97, 610.997, 610.998, STEP_H, top=None, faces="s", group="terrace")
    block(B, xc - 1e-3, xc, 611.0, 613.0, DAIS_H, top=None, faces="e", group="dais")
    block(B, x0, xc, 613.0, 614.97, STEP_H, faces="ew", group="terrace")
    block(B, x0, xc, 612.999, 613.0, DAIS_H, h0=STEP_H, top=None, faces="s", group="dais")
    block(B, 849.97, xc, 614.97 - 1e-3, 614.97, STEP_H, top=None, faces="s", group="terrace")
    block(B, x0, 849.97, 614.7, 614.97, STEP_H - 0.15, h0=LAND_H, faces="s", band="riser", group="steps")
    block(B, x0, 849.97, 614.699, 614.7, STEP_H, h0=STEP_H - 0.15, top=None, faces="s", band="riser", group="steps")
    # pier landing off the south tip, rune inlay along its channel edge
    block(B, 849.03, 849.97, 614.97, 616.97, LAND_H, faces="sew", band="riser", group="landing")
    block(B, 849.03, 849.24, 614.97, 616.97, LAND_H + 0.004, h0=LAND_H, top="rune", faces="", group="landing_inlay")
    # parapets
    block(B, 850.4, 851.97, 610.03, 610.23, STEP_H + 0.24, h0=STEP_H, faces="sew", band="riser", group="parapet")
    block(B, x0, x0 + 0.2, 611.0, 611.2, DAIS_H + 0.26, h0=DAIS_H, faces="sew", band="riser", group="parapet")
    block(B, 849.95, xc, 614.77, 614.97, STEP_H + 0.24, h0=STEP_H, faces="sew", band="riser", group="parapet")
    posts = {"nw": post(B, 849.15, 611.15, DAIS_H, 0.44), "ne": post(B, 850.8, 611.15, DAIS_H, 0.44),
             "sw": post(B, 849.15, 612.86, DAIS_H, 0.44), "tip": post(B, 851.82, 610.17, STEP_H, 0.4),
             "s": post(B, 850.6, 614.45, STEP_H, 0.36, crystal=True),
             "pier": post(B, 849.83, 615.13, LAND_H, 0.42, r=0.1, crystal=True)}
    foam_outline(B, [(x0, 611.0), (x0, 614.97), (849.03, 614.97), (849.03, 616.97), (849.97, 616.97),
                     (849.97, 614.97)], closed=False)
    foam_outline(B, [(849.0, 610.03), (x0, 611.0)], closed=False)
    return posts


def build_092(B, edit, perm, tops):
    info = {}
    pw = terrace_west(B)
    pe = terrace_east(B)
    wa = monolith(B, WEST_MONO, DAIS_H, "blue", +1, "mono_west")
    ea = monolith(B, EAST_MONO, DAIS_H, "rose", -1, "mono_east")
    # chunky crystal-iron chains draped from the monoliths' plain outer faces onto the terrace posts (the carved rune
    # panels on the south and channel faces stay clear)
    chain(B, wa["west"], add(pw["nw"], (0.0, -0.05, 0.0)), 0.22, segs=5, group="chains")
    chain(B, wa["west"], add(pw["sw"], (0.0, -0.05, 0.0)), 0.22, segs=5, group="chains")
    chain(B, ea["east"], add(pe["tip"], (0.0, -0.05, 0.0)), 0.32, group="chains")
    chain(B, ea["east"], add(pe["s"], (0.0, -0.05, 0.0)), 0.3, group="chains")
    # loose chain lengths lying across the lower terraces' paving
    chain_flat(B, (844.25, 612.35), (845.45, 613.45), STEP_H + 0.006)
    chain_flat(B, (849.45, 613.25), (850.6, 614.35), STEP_H + 0.006)
    # the Rift Resonance Seal: a half-submerged carved stone ring in the channel, foam lapping inside and out
    stone_ring(B, SEAL, SEAL_R[0], SEAL_R[1])
    foam_ring(B, SEAL, SEAL_R[1], SEAL_R[1] + 0.28)
    foam_ring(B, SEAL, SEAL_R[0], SEAL_R[0] - 0.26, phase=0, repeats=3)
    info["seal_top"] = round(max(p[1] for pts, g in B.solids if g == "seal" for p in pts), 2)
    return info


# ---------------------------------------------------------------------------------------------------------------
# MAP_094: the Kingdra Sea-Rift Rock
# ---------------------------------------------------------------------------------------------------------------

def build_094(B, edit, perm, tops):
    sx, sz = SPIRE
    top = 0.5
    info = {}
    # main spire: 6-sided, twisted, deep indigo / violet / cyan flat facets
    prism(B, (sx, sz), [(0.66, top - 0.1), (0.74, top + 0.3), (0.60, top + 1.3), (0.44, top + 2.1),
                        (0.24, top + 2.6), (0.0, top + 3.1)], 6, ang0=0.15, twist=0.22, group="spire")
    # base crystals leaning out of the rock
    for k, (yaw, tilt, ln, r) in enumerate(((2.3, 0.62, 1.45, 0.2), (-2.2, 0.55, 1.25, 0.18), (0.75, 0.7, 1.05, 0.16),
                                            (-0.7, 0.66, 1.15, 0.17), (3.1, 0.5, 0.9, 0.14), (1.6, 0.8, 0.8, 0.13))):
        ax = norm((math.sin(yaw) * math.sin(tilt), math.cos(tilt), math.cos(yaw) * math.sin(tilt) * 0.7))
        basep = (sx + 0.5 * math.sin(yaw), top - 0.05, sz + 0.38 * math.cos(yaw))
        prism(B, (0, 0), [(r, 0.0), (r * 1.2, ln * 0.4), (0.0, ln)], 5, ang0=0.5 * k, tilt=(ax, basep),
              group="spire")
    # floating fractured shards orbiting the spire
    for k in range(6):
        a = 0.4 + k * 2 * math.pi / 6
        rr = 1.0 + 0.14 * (k % 2)
        hh = top + 1.1 + 0.3 * k
        bipyramid(B, (sx + rr * math.sin(a), hh, sz + rr * math.cos(a) * 0.75), 0.13 + 0.03 * (k % 3),
                  0.24 + 0.04 * (k % 2), a, tilt=0.35 + 0.1 * k, group="shards")
    # three clean faceted crystal arcs orbiting the spire (a broken halo: solid flat facets, no glyph band)
    crystal_arcs(B, (sx, top + 1.45, sz), 1.55, tilt=0.22, yaw=2.6)
    # carved stone landing on the reading tiles south of the rock, with a step up onto the rock
    block(B, 851.03, 852.97, 698.0, 698.97, LAND_H, faces="sew", band="riser", group="landing")
    block(B, 851.15, 852.85, 697.6, 698.0, 0.25, h0=LAND_H, faces="sew", band="riser", group="steps")
    post(B, 851.17, 698.15, LAND_H, 0.42, r=0.11, crystal=True, group="posts")
    post(B, 852.83, 698.15, LAND_H, 0.42, r=0.11, crystal=True, group="posts")
    foam_outline(B, [(852.97, 698.0), (852.97, 698.97), (851.03, 698.97), (851.03, 698.0)], closed=False)
    info["spire_top"] = round(top + 3.1, 2)
    return info


# the stock rock's waterline (criffp base ring at h SEA_H), from the south-east corner by the landing round to the
# north-east corner, water on the left
ROCK_095_SHORE = [(849.0, 729.97), (848.5, 729.875), (848.0, 730.0), (847.0, 730.0), (846.5, 729.875),
                  (846.125, 729.5), (846.0, 729.0), (846.0, 727.0), (846.125, 726.5), (846.5, 726.125), (847.0, 726.0),
                  (848.0, 726.0), (848.5, 726.125), (849.0, 726.03)]


def build_095(B, edit, perm, tops):
    """South Sea Approach: a carved basalt landing east of rock 846..848 x 726..729 (on the stock shallow tiles), a
    step up onto the rock, corner posts, and soft white foam lapping round the landing and the rock's waterline."""
    block(B, 849.0, 850.97, 726.03, 729.97, LAND_H, faces="nse", band="riser", group="landing")
    block(B, 848.62, 849.0, 726.4, 729.6, 0.25, h0=LAND_H, faces="nse", band="riser", group="steps")
    post(B, 850.83, 726.17, LAND_H, 0.42, r=0.11, crystal=True, group="posts")
    post(B, 849.17, 726.17, LAND_H, 0.42, r=0.11, group="posts")
    foam_outline(B, [(849.0, 726.03), (850.97, 726.03), (850.97, 729.97), (849.0, 729.97)], closed=False)
    foam_outline(B, ROCK_095_SHORE, closed=False, width=0.3, phase=1, group="shore_foam")
    return {}


def build_cluster(B, center, height, seed):
    """A small rift crystal outcrop: one leaning main crystal and 2-3 satellites."""
    import random
    rnd = random.Random(seed)
    cx, cz = center
    top = 0.5
    specs = [(0.0, 0.08, height, 0.26)] + [(rnd.uniform(0, 2 * math.pi), rnd.uniform(0.35, 0.7),
                                           height * rnd.uniform(0.45, 0.7), rnd.uniform(0.13, 0.18)) for _ in range(4)]
    for k, (yaw, tilt, ln, r) in enumerate(specs):
        ax = norm((math.sin(yaw) * math.sin(tilt), math.cos(tilt), math.cos(yaw) * math.sin(tilt) * 0.7))
        basep = (cx + (0.0 if k == 0 else 0.34 * math.sin(yaw)), top - 0.05,
                 cz + (0.0 if k == 0 else 0.26 * math.cos(yaw)))
        prism(B, (0, 0), [(r, 0.0), (r * 1.18, ln * 0.45), (0.0, ln)], 5 if k == 0 else 4, ang0=0.4 * k,
              tilt=(ax, basep), group="cluster")
    bipyramid(B, (cx + 0.35, top + height + 0.25, cz + 0.1), 0.09, 0.17, 0.8, tilt=0.4, group="cluster")


# ---------------------------------------------------------------------------------------------------------------
# landings: permissions + BDHC
# ---------------------------------------------------------------------------------------------------------------

def local(n, x, z):
    cx, cz = CHUNKS[n]
    return x - cx * 32, z - cz * 32


def landing_perm(perm, n):
    out = [list(r) for r in perm]
    for x, z in LANDINGS.get(n, []):
        lx, lz = local(n, x, z)
        out[lz][lx] = WALK
    return out


def landing_bdhc(stock_raw, n):
    """Stock flat sea plate split into non-overlapping rectangles around the landing tiles (raised to LAND_BDHC).
    Chunks without landings keep their stock BDHC bytes."""
    tiles = {local(n, x, z) for x, z in LANDINGS.get(n, [])}
    if not tiles:
        return stock_raw
    b = mapdata.read_bdhc(stock_raw)
    assert len(b["plates"]) == 1 and b["normals"] == [[0, FX, 0]] and b["constants"] == [-SEA_BDHC], \
        "stock BDHC is expected to be one flat sea plate"
    H = [[LAND_BDHC if (lx, lz) in tiles else SEA_BDHC for lx in range(32)] for lz in range(32)]
    rects = []                     # (lx0, lz0, lx1, lz1, h) inclusive tile ranges
    open_runs = {}                 # (lx0, lx1, h) -> rect index still growing downwards
    for lz in range(32):
        runs, lx = [], 0
        while lx < 32:
            e = lx
            while e + 1 < 32 and H[lz][e + 1] == H[lz][lx]:
                e += 1
            runs.append((lx, e, H[lz][lx]))
            lx = e + 1
        nxt = {}
        for r in runs:
            if r in open_runs:
                i = open_runs[r]
                rects[i] = rects[i][:3] + (lz, r[2])
            else:
                rects.append((r[0], lz, r[1], lz, r[2]))
                i = len(rects) - 1
            nxt[r] = i
        open_runs = nxt
    t = 16 * FX
    plates = [((x0 * 16 - 256) * FX, (z0 * 16 - 256) * FX, ((x1 + 1) * 16 - 256) * FX, ((z1 + 1) * 16 - 256) * FX,
               (0, FX, 0), -h) for x0, z0, x1, z1, h in rects]
    assert t
    return mapdata.write_bdhc(mapdata.build_bdhc(plates))


def tile_heights(raw):
    b = mapdata.read_bdhc(raw)
    return [[mapdata.height_at(b, *mapdata.tile_centre(lx, lz), current=SEA_BDHC) for lx in range(32)]
            for lz in range(32)]


# ---------------------------------------------------------------------------------------------------------------
# route-wide Surf network
# ---------------------------------------------------------------------------------------------------------------

SURFABLE = {0x10, 0x13, 0x15}


def route_grid(perms):
    """{(x, z): permission} over the four chunks."""
    g = {}
    for n, perm in perms.items():
        cx, cz = CHUNKS[n]
        for lz in range(32):
            for lx in range(32):
                g[(cx * 32 + lx, cz * 32 + lz)] = perm[lz][lx]
    return g


def reach(g):
    """Tiles reachable from the Sunyshore edge moving through unblocked tiles: Surf on water, walking on rock
    islands and landings (the stock route itself needs both: the player steps onto the shallow-rock islands
    mid-route and surfs on), 4-neighbour moves inside the four chunks."""
    free = {t for t, v in g.items() if not v & 0x8000}
    start = [t for t in free if t[1] == SURF_START_Z]
    seen, todo = set(start), list(start)
    while todo:
        x, z = todo.pop()
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            t = (x + d[0], z + d[1])
            if t in free and t not in seen:
                seen.add(t)
                todo.append(t)
    return seen


def is_surf(v):
    return not v & 0x8000 and (v & 0xFF) in SURFABLE


def route_checks(out, ev):
    res = []
    stock = route_grid({n: o["stock_perm"] for n, o in out.items()})
    new = route_grid({n: o["perm"] for n, o in out.items()})
    rs, rn = reach(stock), reach(new)
    land = {t for n in LANDINGS for t in LANDINGS[n]}
    lost = sorted(rs - rn)
    res.append((f"route network from z {SURF_START_Z}: {len(rn)} tiles reachable ({len(rs)} stock), nothing lost "
                f"{lost if lost else ''}", not lost))
    pool = [t for t in PLUNGE_POOL if is_surf(new.get(t, 0x8000))]
    miss = [t for t in pool if t not in rn]
    res.append((f"plunge pool below the falls ({len(pool)} open water tiles of z 608 x 840..855) reachable "
                f"{miss if miss else ''}", not miss and len(pool) >= 8))
    chan = [(x, z) for x in (846, 847, 848) for z in range(608, 616)]
    bad = [t for t in chan if not is_surf(new[t]) or t not in rn]
    res.append((f"Surf channel x 846..848 z 608..615 stays open, surfable water, all reachable {bad if bad else ''}",
                not bad))
    sw = [(o["id"], (o["x"], o["z"])) for o in ev["object_events"] if "SWIMMER" in o["graphics_id"]]
    bad = [i for i, t in sw if t not in rn or not is_surf(new[t])]
    res.append((f"all {len(sw)} swimmers on reachable Surf tiles {bad if bad else ''}", not bad))
    bad = [t for t in sorted(land) if t not in rn]
    groups_ok = []
    for n, tiles in LANDINGS.items():
        ts = set(tiles)
        groups_ok.append(any(is_surf(new.get((x + d[0], z + d[1]), 0x8000)) for x, z in ts
                             for d in ((1, 0), (-1, 0), (0, 1), (0, -1))))
    res.append((f"every landing tile reachable and every landing borders Surf water {bad if bad else ''}",
                not bad and all(groups_ok)))
    walk = [t for t, v in stock.items() if not v & 0x8000 and (v & 0xFF) not in SURFABLE]
    bad = [t for t in walk if new[t] & 0x8000]
    res.append((f"all {len(walk)} stock walkable rock tiles still walkable {bad if bad else ''}", not bad))
    return res


# ---------------------------------------------------------------------------------------------------------------
# assembly and per-chunk checks
# ---------------------------------------------------------------------------------------------------------------

def events():
    return json.load(open(os.path.join(ROOT, EVENTS_REL)))


def event_tiles(ev):
    out = {}
    for o in ev["object_events"]:
        out[(o["x"], o["z"])] = o.get("id", o["graphics_id"])
        if o.get("movement_range_x") or o.get("movement_range_z"):
            for dx in range(-o.get("movement_range_x", 0), o.get("movement_range_x", 0) + 1):
                for dz in range(-o.get("movement_range_z", 0), o.get("movement_range_z", 0) + 1):
                    out.setdefault((o["x"] + dx, o["z"] + dz), o.get("id", "?") + " (patrol)")
    for b in ev["bg_events"]:
        out[(b["x"], b["z"])] = b.get("script") or b.get("hidden_item")
    return out


def occluded_tiles(B, perm, cx, cz, land):
    """Unblocked tiles of this chunk whose player sprite (x + 0.15..0.85, feet .. feet + 1.3; feet = LAND_H on a
    landing, SEA_H elsewhere) a solid new face hides from the field camera (near-orthographic projection)."""
    sn, cs = CAM[1], CAM[2]
    hidden = {}
    samples = []
    for pts, g in B.solids:
        cen = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
        samples += [(p, g) for p in pts] + [(cen, g)]
        for p in pts:
            samples.append((tuple((p[k] + cen[k]) / 2 for k in range(3)), g))
    for lz in range(32):
        for lx in range(32):
            if perm[lz][lx] & 0x8000:
                continue
            x, z = cx * 32 + lx, cz * 32 + lz
            feet = LAND_H if (x, z) in land else SEA_H
            zs = z + 0.5
            for p, g in samples:
                if p[2] <= zs + 0.02 or not (x + 0.15 <= p[0] <= x + 0.85):
                    continue
                s = (p[2] - zs) / cs
                y = p[1] - s * sn
                if feet + 0.02 <= y <= feet + 1.3:
                    hidden[(x, z)] = g
                    break
    return hidden


def build_all(tex):
    out = {}
    ev = events()
    evt = event_tiles(ev)
    for n, (cx, cz) in CHUNKS.items():
        rel = f"{OUT_MAP_DIR}/map_data_{n:03d}.bin"
        edit = C.ChunkEdit(rel, (cx, cz), BASE_REV)
        stock_perm = edit.permissions()
        perm = landing_perm(stock_perm, n)
        tops = stock_tops(edit)
        boulders = boulder_tiles(edit)
        edited, buried = drop_buried_boulders(edit, TERRACE_RECTS.get(n, []))
        shallows = shallows_to_sea(edit)
        B = Builder(tex)
        info = {}
        if n == 92:
            info = build_092(B, edit, perm, tops)
        elif n == 94:
            info = build_094(B, edit, perm, tops)
        elif n == 95:
            info = build_095(B, edit, perm, tops)
        for center, height, seed in CLUSTERS.get(n, []):
            build_cluster(B, center, height, seed)
        edit.add(B, tex["table"])
        model = edit.model_bytes()
        bdhc = landing_bdhc(edit.sec["bdhc"], n)
        data = mapdata.pack(mapdata.write_permissions(perm), edit.sec["props"], model, bdhc)
        out[n] = dict(edit=edit, B=B, perm=perm, stock_perm=stock_perm, model=model, data=data, info=info, tops=tops,
                      rel=rel, boulders=boulders, stats=edit.stats(model), evt=evt, bdhc=bdhc,
                      edited=edited | shallows, buried=buried, shallows=shallows)
    return out, ev


def run_checks(out, tex, ev):
    res = []
    for n, o in out.items():
        cx, cz = CHUNKS[n]
        edit, B, perm, model = o["edit"], o["B"], o["perm"], o["model"]
        land = set(LANDINGS.get(n, []))
        st = o["stats"]
        sec = mapdata.unpack(o["data"])
        stock = mapdata.unpack(C.git_file(BASE_REV, o["rel"]))
        res.append((f"{n:03d} model {len(model)} B <= 0x{MODEL_BUFFER:X} ({len(stock['model'])} stock, "
                    f"+{st['polygons'] - st['stock_polygons']} polygons)", len(model) <= MODEL_BUFFER))
        res.append((f"{n:03d} BDHC {len(sec['bdhc'])} B <= 0x{BDHC_BUFFER:X}", len(sec["bdhc"]) <= BDHC_BUFFER))
        bmd = nsbmd.parse_bmd(model)
        res.append((f"{n:03d} NSBMD parse -> rebuild byte-identical", nsbmd.build_bmd(bmd["models"]) == model))
        res.append((f"{n:03d} map_data unpack -> pack byte-identical",
                    mapdata.pack(sec["permissions"], sec["props"], sec["model"], sec["bdhc"]) == o["data"]))
        bdhc_rt = mapdata.write_bdhc(mapdata.read_bdhc(sec["bdhc"])) == sec["bdhc"]
        res.append((f"{n:03d} BDHC read -> write byte-identical", bdhc_rt))
        bad = C.stock_shapes_identical(edit.model, edit.built, o["edited"])
        res.append((f"{n:03d} every stock shape and material byte-identical except the {o['buried']} sea boulders "
                    f"buried under the terraces and the shallow overlay moved into the sea (shapes "
                    f"{sorted(o['edited'])}) {bad if bad else ''}", not bad))
        sh = [s for s in edit.built["shapes"]
              for mi, si in nsbmd.shape_material_pairs(edit.built)
              if edit.built["shapes"][si] is s and edit.built["materials"][mi]["texture"] == "asasea"]
        res.append((f"{n:03d} no shallow-sea (asasea) overlay left in the chunk", not sh))
        res.append((f"{n:03d} props identical to stock", sec["props"] == stock["props"]))
        sp, np_ = mapdata.read_permissions(stock["permissions"]), mapdata.read_permissions(sec["permissions"])
        diff = sorted((cx * 32 + lx, cz * 32 + lz) for lz in range(32) for lx in range(32) if sp[lz][lx] != np_[lz][lx])
        ok = set(diff) == land and all(np_[z - cz * 32][x - cx * 32] == WALK for x, z in land)
        res.append((f"{n:03d} permissions = stock except the {len(land)} landing tiles (0x{WALK:04X}) "
                    f"{'' if ok else diff}", ok))
        hs, hn = tile_heights(stock["bdhc"]), tile_heights(sec["bdhc"])
        badh = [(cx * 32 + lx, cz * 32 + lz, hn[lz][lx]) for lz in range(32) for lx in range(32)
                if hn[lz][lx] != (LAND_BDHC if (cx * 32 + lx, cz * 32 + lz) in land else hs[lz][lx])]
        # from the sea height and from the landing height alike, every tile resolves to one plate
        b = mapdata.read_bdhc(sec["bdhc"])
        amb = [(lx, lz) for lz in range(32) for lx in range(32)
               if mapdata.height_at(b, *mapdata.tile_centre(lx, lz), current=LAND_BDHC) != hn[lz][lx]]
        res.append((f"{n:03d} BDHC height at every tile centre = stock, landings = {LAND_BDHC // FX} "
                    f"({len(b['plates'])} plates) {badh[:6] if badh else ''}{amb[:6] if amb else ''}",
                    not badh and not amb))
        missing = []
        for m in edit.built["materials"][len(edit.model["materials"]):]:
            t = tex["table"].get(m["texture"])
            if t is None or m["palette"] not in tex["palettes"] or [m["orig_width"], m["orig_height"]] != t["size"]:
                missing.append(m["name"])
        res.append((f"{n:03d} new materials bound to set-082 textures/palettes with matching sizes {missing or ''}",
                    not missing))
        # solid geometry below h 0.9 stands on blocked rock or this chunk's landings; the seal alone on water, low
        off = set()
        for pts, g in B.solids:
            for p in pts:
                t = (math.floor(p[0]), math.floor(p[2]))
                if g == "seal":
                    if p[1] > SEA_H + 0.3 or blocked(perm, cx, cz, *t) is None:
                        off.add(t + (g,))
                    continue
                if p[1] < 0.9 and blocked(perm, cx, cz, *t) is False and t not in land:
                    off.add(t + (g,))
        res.append((f"{n:03d} solid geometry on blocked rock / own landings only, seal ring <= SEA_H + 0.3 "
                    f"{sorted(off) if off else ''}", not off))
        offd = set()
        for pts, g, where in B.decals:
            for p in pts:
                t = (math.floor(p[0]), math.floor(p[2]))
                b_ = blocked(perm, cx, cz, *t)
                if where == "rock" and (b_ is not True or t in o["boulders"]):
                    offd.add(t + (g,))
                if where == "stone" and b_ is not True and t not in land:
                    offd.add(t + (g,))
                if where == "water" and b_ is None:
                    offd.add(t + (g,))
        res.append((f"{n:03d} decals where designed (cracks on flat blocked rock, chains on terrace stone, foam in "
                    f"the chunk) {sorted(offd) if offd else ''}", not offd))
        onb = sorted({(math.floor(p[0]), math.floor(p[2]), g) for pts, g in B.solids for p in pts
                      if p[1] < 0.9 and g in ("spire", "cluster", "mono_west", "mono_east")
                      and (math.floor(p[0]), math.floor(p[2])) in o["boulders"]})
        res.append((f"{n:03d} no crystal / monolith base on a domed boulder {onb if onb else ''}", not onb))
        hid = occluded_tiles(B, perm, cx, cz, land)
        watch = dict(o["evt"])
        watch.update({t: "landing" for t in land})
        ev_hidden = {t: (g, watch[t]) for t, g in hid.items() if t in watch}
        res.append((f"{n:03d} no event or landing tile hidden by new geometry {ev_hidden if ev_hidden else ''}",
                    not ev_hidden))
        o["hidden"] = hid
    res += route_checks(out, ev)
    # set 082
    for f in tex["fails"]:
        res.append(("set 082: " + f, False))
    res.append(("set 082 round trip, stock entries unchanged, VRAM < 160 KB", not tex["fails"]))
    return res


# ---------------------------------------------------------------------------------------------------------------
# lighting_set_010: violet rift storm
# ---------------------------------------------------------------------------------------------------------------

LIGHTING_REL = "res/field/lighting/lighting_set_010.json"
LIGHTING_TEMPLATE = "res/field/lighting/lighting_set_000.json"
# endTime (2 s units, 43200 = 24:00) -> (light 0, diffuse, ambient, specular, emission), 5-bit 0..31.
# Indigo-violet ambient all day with electric-lavender highlights; day stays bright (sea, rocks and swimmers crisp),
# evening flares lavender-magenta, night drops to a deep storm indigo with a violet emission floor.
NIGHT = ((13, 11, 23), (14, 12, 18), (12, 10, 16), (14, 12, 19), (11, 8, 16))
LIGHT_CURVE = {
    0: NIGHT,
    7200: NIGHT,                                                                         # 00:00-04:00 storm night
    8100: ((13, 11, 22), (11, 10, 15), (12, 10, 15), (9, 8, 15), (11, 9, 15)),           # 04:00-04:30 pre-dawn
    9000: ((15, 12, 23), (12, 11, 15), (10, 9, 13), (11, 10, 16), (13, 11, 16)),         # 04:30-05:00 violet dawn
    14400: ((18, 16, 25), (13, 12, 15), (9, 8, 12), (13, 12, 16), (14, 12, 18)),         # 05:00-08:00 storm morning
    20700: ((20, 18, 27), (14, 13, 16), (9, 8, 13), (15, 14, 17), (14, 13, 18)),         # 08:00-11:30 bright rift day
    21600: ((22, 20, 27), (15, 14, 17), (10, 9, 14), (16, 15, 18), (14, 13, 17)),       # 11:30-12:00 noon
    27000: ((23, 21, 28), (16, 15, 17), (10, 10, 14), (17, 16, 18), (14, 13, 17)),       # 12:00-15:00 peak
    27900: ((22, 20, 27), (15, 14, 17), (11, 10, 14), (16, 15, 18), (13, 12, 16)),       # 15:00-15:30
    30600: ((21, 18, 26), (15, 14, 16), (11, 11, 13), (16, 15, 18), (12, 11, 14)),       # 15:30-17:00 lavender
    32400: ((21, 15, 27), (15, 14, 16), (11, 10, 14), (16, 14, 18), (11, 9, 14)),        # 17:00-18:00 electric lavender
    33300: ((19, 13, 26), (14, 13, 16), (12, 10, 15), (15, 13, 18), (10, 8, 14)),        # 18:00-18:30 magenta storm
    34200: ((16, 12, 25), (14, 13, 16), (12, 10, 15), (14, 12, 18), (10, 8, 14)),        # 18:30-19:00 violet dusk
    36000: ((13, 11, 23), (14, 12, 17), (11, 9, 15), (14, 12, 18), (9, 7, 14)),          # 19:00-20:00 indigo dusk
    43200: NIGHT,                                                                        # 20:00-24:00 storm night
}


def build_lighting():
    raw = subprocess.run(["git", "-C", ROOT, "show", f"{BASE_REV}:{LIGHTING_TEMPLATE}"], check=True,
                         capture_output=True).stdout.decode()
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
    if [list(b.keys()) for b in back] != [list(b.keys()) for b in tmpl]:
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
            fails.append(f"lighting: lights 1..3 changed at {b['endTime']}")
    return text, fails


# ---------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    tex = TX.build_set()
    TX.report(tex)
    out, ev = build_all(tex)
    for n, o in out.items():
        st = o["stats"]
        print(f"map_data_{n:03d}: model {st['stock_model_bytes']} -> {st['model_bytes']} B, polygons "
              f"{st['stock_polygons']} -> {st['polygons']}, materials {st['materials']}, data {len(o['data'])} B, "
              f"groups {o['B'].groups} {o['info'] or ''}")
    res = run_checks(out, tex, ev)
    light_text, light_fails = build_lighting()
    res += [(f, False) for f in light_fails]
    res.append(("lighting_set_010 schema, block times, light directions and lights 1..3 as stock", not light_fails))
    ok = True
    for msg, good in res:
        print(("PASS " if good else "FAIL ") + msg)
        ok &= good
    for n, o in out.items():
        if o.get("hidden"):
            print(f"note {n:03d}: plain sea tiles partly behind new geometry (no events): "
                  f"{sorted(o['hidden'])}")
    print("showcase (dry stone):", ", ".join(f"{nm} ({x}, {z}, {f})" for nm, x, z, f in SHOWCASE))
    if "--mesh" in args:
        d = args[args.index("--mesh") + 1]
        os.makedirs(d, exist_ok=True)
        for n, o in out.items():
            json.dump(nsbmd.model_to_mesh(nsbmd.parse_bmd(o["model"])["models"][0], CHUNKS[n]),
                      open(os.path.join(d, f"chunk_{n:03d}.mesh.json"), "w"))
    if "--write" in args:
        if not ok:
            print("refusing to write: checks failed")
            return 1
        open(os.path.join(ROOT, TX.SET_REL), "wb").write(tex["bytes"])
        print("wrote", TX.SET_REL, len(tex["bytes"]), "B")
        for n, o in out.items():
            open(os.path.join(ROOT, o["rel"]), "wb").write(o["data"])
            print("wrote", o["rel"], len(o["data"]), "B")
        open(os.path.join(ROOT, LIGHTING_REL), "w").write(light_text)
        print("wrote", LIGHTING_REL)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
