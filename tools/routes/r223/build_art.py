#!/usr/bin/env python3
"""Route 223 - Rift Sea Route & Waterfall Summit art pass (docs/routes_wave2/PLAN.md, arc3 scenes 3.15-3.17).

Writes map_texture_set_082 (textures.py), the surgical chunk edits of map_data_092..095 and lighting_set_010.

Usage (Python with NumPy):
  ~/.venvs/desmume/bin/python tools/routes/r223/build_art.py            dry run: build, budgets, every check
  ~/.venvs/desmume/bin/python tools/routes/r223/build_art.py --write    write the set, the four chunks and the lighting
                                                                         (refuses on any FAIL)
  ~/.venvs/desmume/bin/python tools/routes/r223/build_art.py --mesh DIR also dump DIR/chunk_NNN.mesh.json

Inputs: the stock chunks, stock set 013 and lighting_set_000 from git HEAD (never the work tree, so reruns never
feed back); textures.py for the four appended textures.

Geography (stock, surveyed with dump_stock.py): Route 223 is open sea at h -0.5 (BDHC 0.5) with rock outcrops
whose cliff tops sit at h 0.5. The waterfall itself (x 840..855, z 604), the summit terrace, the Victory Road
entrance warps and the Pokemon Center belong to MAP_113 (Pokemon League header, not part of this package), so the
summit climax is staged on MAP_092's plunge pool at the foot of the falls, where it frames the climb:

  MAP_092  Waterfall Summit Gate: twin rift-scarred basalt monoliths on the two rock horns that flank the channel
           up to the falls (west on rock 843..844 x 610..611: Dialga sapphire runes; east on rock 849..850 x
           611..614: Palkia rose runes), each split by a rift scar with violet crystal shards, broken shard chains
           trailing from the monoliths down onto the outer rocks, glowing rift cracks on the rock tops, and the Rift
           Resonance Seal (4 x 4 tiles, c0 transparent) glowing on the plunge-pool surface between them.
  MAP_094  Kingdra Sea-Rift Rock: the mid-channel outcrop x 850..855, z 692..697 crowned with a 6-sided twisted
           violet/cyan Rift Crystal spire, four base crystals, six floating fractured shards, rift cracks on the
           rock and a glowing rune ring on the water around it (all unlit with baked vertex glow).
  MAP_093  a mid-route crystal cluster on the central island rock (the rift's reach between the two set pieces).
  MAP_095  South Sea Approach: two small crystal outcrops on the first rocks north of Sunyshore.

Stock terrain, permissions, BDHC and props are untouched in all four chunks; stock shapes keep their display lists
and materials byte for byte (only new materials and shapes are appended).

Checks (--write refuses on any FAIL): set 082 round trip + VRAM (textures.py); per chunk: model <= 0xF000, BDHC
<= 0x9000, NSBMD parse -> rebuild byte-identical, stock shapes and materials byte-identical, permissions / BDHC /
props identical to stock, every new material's texture and palette present in set 082 with matching sizes, every
landmark's solid footprint on blocked stock tiles, no solid new geometry hiding an event tile from the field
camera, every event tile walkable/surfable exactly as stock; lighting schema / times / directions as stock.
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

BASE_REV = "HEAD"
OUT_MAP_DIR = "res/field/mapmodels/data"
CHUNKS = {92: (26, 19), 93: (26, 20), 94: (26, 21), 95: (26, 22)}
MODEL_BUFFER = 0xF000            # include/overlay005/loaded_map_buffers.h MAP_MODEL_FILE_SIZE
BDHC_BUFFER = 0x9000             # include/constants/field/bdhc.h BDHC_BUFFER_SIZE
SEA_H = -0.5                     # model h of the sea surface (BDHC 0.5 = where the player surfs)
EVENTS_REL = "res/field/maps/route_223/events.json"
CAM = (0.0, math.sin(math.radians(59.05)), math.cos(math.radians(59.05)))   # towards the field camera

# landmark anchors (absolute tiles)
WEST_MONO = (844.0, 611.0)       # rock 843..844 x 610..611
EAST_MONO = (850.0, 612.0)       # rock 849..850 x 611..614
SEAL = (847.0, 611.0, 1.8)       # centre x, z, half size: plunge pool between the monoliths
SPIRE = (853.0, 694.9)           # Kingdra rock x 850..855, z 692..697
RING_R = (3.05, 3.42)            # water rune ring radii around the spire
CLUSTERS = {93: [((845.0, 652.6), 2.2, 31)], 95: [((841.9, 721.8), 1.8, 41), ((847.4, 727.6), 1.4, 43)]}

# materials: name -> (texture, cull)   (all unlit: polygon lights off, baked vertex colours)
MATS = {"r223_rift_u": ("r223_rift", "back"), "r223_pil_u": ("r223_pillar", "back"),
        "r223_chn_u": ("r223_chain", "none"), "r223_dec_u": ("r223_chain", "back"),
        "r223_seal_u": ("r223_seal", "back")}


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
        self.solids = []          # (pts, group) of every non-decal face, for the clearance checks
        self.decals = []          # rock-top decals (cracks, flat chains): must lie over blocked rock
        self.groups = {}
        self.footprint = {}       # group -> [xmin, zmin, xmax, zmax, hmax]
        for name, (t, cull) in MATS.items():
            self.material(name, t, TX.pal_name(t), tex["table"][t]["size"], lights=0, cull=cull)

    def add(self, mat, pts, uvs, colors, inside=None, group="misc", solid=True, cam_cull=True):
        """pts (x, h, z) absolute tiles; colors: one RGB or one per vertex. inside: a point the face must face away
        from (fixes the winding). Faces the camera can never see are dropped (cam_cull) when the material culls."""
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
        elif group in ("cracks", "chains"):
            self.decals.append((pts, group))
        return n


def uvbox(box, w=32, h=32, inset=0.15):
    x0, y0, x1, y1 = box
    return ((x0 + inset) / w, (y0 + inset) / h, (x1 - inset) / w, (y1 - inset) / h)


# ---------------------------------------------------------------------------------------------------------------
# shared kit: crystals, shards, chains, decals
# ---------------------------------------------------------------------------------------------------------------

def crystal_colour(n, h, h0, h1, bright=1.0):
    """Violet core rising into electric cyan at the tips, facet-lit, unlit glow so it shines at night."""
    t = max(0.0, min(1.0, (h - h0) / max(0.01, h1 - h0)))
    base = (232 - 40 * t, 205 + 45 * t, 255)
    return shade(n, base, glow=0.04 + 0.10 * t, amb=0.80 * bright, key=0.32 * bright, rim=(10, 4, 18))


def prism(B, center, profile, segs, ang0=0.0, twist=0.0, tilt=None, group="crystal", uv=(0.0, 0.0, 1.0, 1.0),
          colour=None, mat="r223_rift_u"):
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
    u0, v0, u1, v1 = uv
    axis_pt = lambda i: (sum(p[0] for p in rings[i]) / segs, sum(p[1] for p in rings[i]) / segs,  # noqa: E731
                         sum(p[2] for p in rings[i]) / segs)
    col = colour or (lambda n, h: crystal_colour(n, h, h0, h1))
    for i in range(len(profile) - 1):
        top_pole = profile[i + 1][0] == 0
        inside = mul(add(axis_pt(i), axis_pt(i + 1)), 0.5)
        for j in range(segs):
            k = (j + 1) % segs
            a, b = rings[i][j], rings[i][k]
            c, d = rings[i + 1][k], rings[i + 1][j]
            fu0 = u0 + (u1 - u0) * j / segs
            fu1 = u0 + (u1 - u0) * (j + 1) / segs
            fv0 = v1 - (v1 - v0) * i / (len(profile) - 1)
            fv1 = v1 - (v1 - v0) * (i + 1) / (len(profile) - 1)
            if top_pole:
                pts, uvs = [a, b, c], [(fu0, fv0), (fu1, fv0), ((fu0 + fu1) / 2, fv1)]
            else:
                pts, uvs = [a, b, c, d], [(fu0, fv0), (fu1, fv0), (fu1, fv1), (fu0, fv1)]
            n = face_n(pts)
            if dot(n, sub(tuple(sum(p[q] for p in pts) / len(pts) for q in range(3)), inside)) < 0:
                n = mul(n, -1)
            B.add(mat, pts, uvs, [col(n, p[1]) for p in pts], inside=inside, group=group)


def bipyramid(B, c, r, hh, ang, tilt=0.0, group="shards", bright=1.2):
    """A floating fractured shard: a 4-sided bipyramid of half-height hh, radius r, yawed by ang, leaned by tilt."""
    ax = norm((math.sin(ang) * math.sin(tilt), math.cos(tilt), math.cos(ang) * math.sin(tilt)))
    e1 = norm(cross(ax, (0.0, 0.0, 1.0)))
    e2 = norm(cross(e1, ax))
    eq = [add(c, add(mul(e1, r * math.cos(a + ang)), mul(e2, r * math.sin(a + ang)))) for a in
          (0.0, math.pi / 2, math.pi, 3 * math.pi / 2)]
    top, bot = add(c, mul(ax, hh)), add(c, mul(ax, -hh))
    for k in range(4):
        p, q = eq[k], eq[(k + 1) % 4]
        for tip, uvy in ((top, 0.1), (bot, 0.9)):
            tri = [p, q, tip]
            n = face_n(tri)
            if dot(n, sub(mul(add(add(p, q), tip), 1 / 3), c)) < 0:
                n = mul(n, -1)
            cols = [crystal_colour(n, v[1], c[1] - hh, c[1] + hh, bright) for v in tri]
            B.add("r223_rift_u", tri, [(0.2 + 0.2 * k, 0.5), (0.4 + 0.2 * k, 0.5), (0.3 + 0.2 * k, uvy)], cols,
                  inside=c, group=group)


def chain(B, a, b, sag, width=0.5, group="chains", links_per_tile=0.72, breaks=(), segs=10):
    """A shard chain hanging from a to b ((x, h, z)) with a parabolic sag (tiles), as a double-sided ribbon facing
    the camera; `breaks` lists segment indices left out (shattered gaps)."""
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
        if i not in breaks:
            quad = [add(p, w), add(q, w), sub(q, w), sub(p, w)]
            n = face_n(quad)
            cols = [shade(n if dot(n, CAM) > 0 else mul(n, -1), (240, 225, 255), glow=0.06, amb=0.85, key=0.25)] * 4
            B.add("r223_chn_u", quad, [(u, v0), (un, v0), (un, v1), (u, v1)], cols, group=group, cam_cull=False)
        u = un


def chain_flat(B, a, b, h, width=0.44, group="chains", links_per_tile=0.8):
    """A broken chain length lying flat on a rock top from a to b ((x, z))."""
    d = norm((b[0] - a[0], 0.0, b[1] - a[1]))
    side = (-d[2] * width / 2, 0.0, d[0] * width / 2)
    pa, pb = (a[0], h, a[1]), (b[0], h, b[1])
    ln = math.hypot(b[0] - a[0], b[1] - a[1])
    v0, v1 = CHAIN_V
    quad = [add(pa, side), add(pb, side), sub(pb, side), sub(pa, side)]
    B.add("r223_chn_u", quad, [(0, v0), (ln * links_per_tile, v0), (ln * links_per_tile, v1), (0, v1)],
          [(245, 230, 255)] * 4, inside=(a[0], h - 1, a[1]), group=group, solid=False, cam_cull=False)


def cracks(B, x0, z0, x1, z1, h, group="cracks", flip=False):
    """Glowing rift cracks decal (flat, rows 20..31 of r223_chain) on a rock top."""
    u0, v0, u1, v1 = CRACK_UV
    if flip:
        v0, v1 = v1, v0
    pts = [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)]
    B.add("r223_dec_u", pts, [(u0, v1), (u1, v1), (u1, v0), (u0, v0)], [(235, 225, 255)] * 4, group=group,
          solid=False)


CHAIN_V = (0.2 / 32, 11.8 / 32)
CRACK_UV = (0.0, 20.2 / 32, 1.0, 31.8 / 32)
BAND_V = (12.2 / 32, 19.8 / 32)


def ring_band(B, c, r0, r1, h, segs=44, repeats=11, group="ring"):
    """Glowing rune ring (rows 12..19 of r223_chain) on the water around c."""
    v0, v1 = BAND_V
    for j in range(segs):
        a0, a1 = 2 * math.pi * j / segs, 2 * math.pi * (j + 1) / segs
        u0, u1 = repeats * j / segs, repeats * (j + 1) / segs
        p = lambda r, a: (c[0] + r * math.sin(a), h, c[1] + r * math.cos(a))  # noqa: E731
        pts = [p(r1, a0), p(r1, a1), p(r0, a1), p(r0, a0)]
        uvs = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
        B.add("r223_dec_u", pts, uvs, [(150, 230, 255)] * 4, inside=(c[0], h - 1, c[1]), group=group, solid=False)


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


def blocked(perm, cx, cz, x, z):
    lx, lz = x - cx * 32, z - cz * 32
    if not (0 <= lx < 32 and 0 <= lz < 32):
        return None
    return bool(perm[lz][lx] & 0x8000)


# ---------------------------------------------------------------------------------------------------------------
# MAP_092: the Waterfall Summit Gate
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
    for k, (hh, ln, yaw, r) in enumerate(((h0 + 1.0, 0.62, 0.35, 0.09), (h0 + 1.55, 0.48, -0.25, 0.075),
                                          (h0 + 2.2, 0.55, 0.15, 0.085))):
        ax = norm((out * math.cos(yaw), 0.55, math.sin(yaw) * 0.6 + 0.25))
        basep = (cx + out * 0.34, hh, cz + 0.05 * (k - 1))
        prism(B, (0, 0), [(r, 0.0), (r * 1.15, ln * 0.45), (0.0, ln)], 4, ang0=0.3 * k, tilt=(ax, basep),
              group=group)
    return (cx + out * 0.4, h1 - 0.25, cz)


def build_092(B, edit, perm, tops):
    cx, cz = CHUNKS[92]
    info = {}
    wt = max(tops.get((843, 610), 0.5), tops.get((844, 611), 0.5))
    et = max(tops.get((849, 612), 0.5), tops.get((850, 612), 0.5))
    wt, et = min(wt, 0.55), min(et, 0.55)
    w_anchor = monolith(B, WEST_MONO, 0.5, "blue", +1, "mono_west")
    e_anchor = monolith(B, EAST_MONO, 0.5, "rose", -1, "mono_east")
    info["rock_tops"] = (round(wt, 2), round(et, 2))
    # shattered shard chains trailing from the monoliths down onto the outer rocks
    chain(B, w_anchor, (840.5, 0.56, 609.2), 0.2, breaks=(6,), group="chains")
    chain(B, (w_anchor[0], w_anchor[1] - 0.9, w_anchor[2] + 0.1), (839.6, 0.56, 608.55), 0.12, segs=9,
          breaks=(2,), group="chains")
    chain(B, e_anchor, (853.45, 0.56, 609.05), 0.3, breaks=(3, 7), group="chains")
    chain(B, (e_anchor[0], e_anchor[1] - 0.8, e_anchor[2] - 0.1), (850.9, 0.56, 610.35), 0.3, segs=7,
          group="chains")
    chain_flat(B, (839.25, 609.75), (840.75, 608.35), 0.56)
    chain_flat(B, (850.4, 609.5), (852.6, 608.45), 0.56)
    # glowing rift cracks on the flat horn rock tops
    cracks(B, 839.1, 608.1, 840.9, 609.9, 0.53)
    cracks(B, 852.1, 608.1, 853.9, 608.9, 0.53, flip=True)
    cracks(B, 850.1, 609.1, 853.9, 609.9, 0.53)
    cracks(B, 850.05, 610.05, 851.95, 610.95, 0.53, flip=True)
    # the Rift Resonance Seal on the plunge pool between the monoliths
    sx, sz, hs = SEAL
    pts = [(sx - hs, SEA_H + 0.04, sz + hs), (sx + hs, SEA_H + 0.04, sz + hs), (sx + hs, SEA_H + 0.04, sz - hs),
           (sx - hs, SEA_H + 0.04, sz - hs)]
    e = 0.15 / 64
    B.add("r223_seal_u", pts, [(e, 1 - e), (1 - e, 1 - e), (1 - e, e), (e, e)],
          [(255, 255, 255), (230, 220, 255), (255, 255, 255), (230, 220, 255)], group="seal", solid=False)
    return info


# ---------------------------------------------------------------------------------------------------------------
# MAP_094: the Kingdra Sea-Rift Rock
# ---------------------------------------------------------------------------------------------------------------

def build_094(B, edit, perm, tops):
    sx, sz = SPIRE
    top = 0.5
    info = {}
    # main spire: 6-sided, twisted, violet base to cyan tip
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
    # rift cracks on the rock top and the rune ring on the water
    cracks(B, 850.15, 695.2, 853.6, 696.0, top + 0.03)
    cracks(B, 852.2, 692.2, 855.8, 692.95, top + 0.03, flip=True)
    cracks(B, 850.2, 696.3, 853.8, 697.0, top + 0.03, flip=True)
    ring_band(B, SPIRE, RING_R[0], RING_R[1], SEA_H + 0.04)
    info["spire_top"] = round(top + 3.1, 2)
    return info


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
# assembly and checks
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


def occluded_tiles(B, perm, cx, cz):
    """Walkable tiles (not blocked) of this chunk whose player sprite (x + 0.15..0.85, 0..1.3 above the sea) a solid
    new face hides from the field camera (near-orthographic projection along the camera direction)."""
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
            zs = z + 0.5
            for p, g in samples:
                if p[2] <= zs or not (x + 0.15 <= p[0] <= x + 0.85):
                    continue
                s = (p[2] - zs) / cs
                y = p[1] - s * sn
                if SEA_H <= y <= SEA_H + 1.3:
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
        perm = edit.permissions()
        tops = stock_tops(edit)
        boulders = boulder_tiles(edit)
        B = Builder(tex)
        info = {}
        if n == 92:
            info = build_092(B, edit, perm, tops)
        elif n == 94:
            info = build_094(B, edit, perm, tops)
        for center, height, seed in CLUSTERS.get(n, []):
            build_cluster(B, center, height, seed)
        edit.add(B, tex["table"])
        model = edit.model_bytes()
        data = edit.pack(perm, model)
        out[n] = dict(edit=edit, B=B, perm=perm, model=model, data=data, info=info, tops=tops, rel=rel, boulders=boulders,
                      stats=edit.stats(model), evt=evt)
    return out


def run_checks(out, tex):
    res = []
    for n, o in out.items():
        cx, cz = CHUNKS[n]
        edit, B, perm, model = o["edit"], o["B"], o["perm"], o["model"]
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
        bad = C.stock_shapes_identical(edit.model, edit.built, set())
        res.append((f"{n:03d} every stock shape and material byte-identical {bad if bad else ''}", not bad))
        res.append((f"{n:03d} permissions, BDHC and props identical to stock",
                    (sec["permissions"], sec["bdhc"], sec["props"]) == (stock["permissions"], stock["bdhc"],
                                                                         stock["props"])))
        missing = []
        for m in edit.built["materials"][len(edit.model["materials"]):]:
            t = tex["table"].get(m["texture"])
            if t is None or m["palette"] not in tex["palettes"] or [m["orig_width"], m["orig_height"]] != t["size"]:
                missing.append(m["name"])
        res.append((f"{n:03d} new materials bound to set-082 textures/palettes with matching sizes {missing or ''}",
                    not missing))
        # solid landmark geometry stands on blocked tiles only (sampled at every vertex below h 1.0)
        off = set()
        for pts, g in B.solids:
            for p in pts:
                if p[1] < 0.9:
                    b = blocked(perm, cx, cz, math.floor(p[0]), math.floor(p[2]))
                    if b is False:
                        off.add((math.floor(p[0]), math.floor(p[2]), g))
        res.append((f"{n:03d} solid landmark footprint on blocked rock tiles only {sorted(off) if off else ''}",
                    not off))
        offd = set()
        for pts, g in B.decals:
            for p in pts:
                t = (math.floor(p[0]), math.floor(p[2]))
                if blocked(perm, cx, cz, *t) is False or t in o["boulders"]:
                    offd.add(t + (g,))
        res.append((f"{n:03d} rock-top decals over flat (non-boulder) blocked rock only {sorted(offd) if offd else ''}",
                    not offd))
        onb = sorted({(math.floor(p[0]), math.floor(p[2]), g) for pts, g in B.solids for p in pts
                      if p[1] < 0.9 and (math.floor(p[0]), math.floor(p[2])) in o["boulders"]})
        res.append((f"{n:03d} no landmark base on a domed boulder {onb if onb else ''}", not onb))
        hid = occluded_tiles(B, perm, cx, cz)
        ev_hidden = {t: (g, o["evt"][t]) for t, g in hid.items() if t in o["evt"]}
        res.append((f"{n:03d} no event tile hidden by new geometry {ev_hidden if ev_hidden else ''}",
                    not ev_hidden))
        o["hidden"] = hid
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
    out = build_all(tex)
    for n, o in out.items():
        st = o["stats"]
        print(f"map_data_{n:03d}: model {st['stock_model_bytes']} -> {st['model_bytes']} B, polygons "
              f"{st['stock_polygons']} -> {st['polygons']}, materials {st['materials']}, groups {o['B'].groups} "
              f"{o['info'] or ''}")
    res = run_checks(out, tex)
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
