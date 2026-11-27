#!/usr/bin/env python3
"""Routes 206-207 Eclipse Supply Road art pass: map_data_025..030 (surgical edits on the stock chunks), the set-079
kit (textures.py) and lighting_set_007. Standard library + NumPy (textures); run with ~/.venvs/desmume/bin/python.

Usage:
  ~/.venvs/desmume/bin/python tools/routes/r206_207/build_art.py                 dry run: budgets + every check
  ~/.venvs/desmume/bin/python tools/routes/r206_207/build_art.py --preview DIR   also render previews (render.py)
  ~/.venvs/desmume/bin/python tools/routes/r206_207/build_art.py --write         write the chunks, set 079 and
                                                                                 lighting_set_007 (refuses on FAIL)

Inputs come from git at common.BASE_REV (stock chunks 025..030, stock set 007, lighting_set_000), so reruns are
idempotent. Edits (tools/world_art/chunkedit.py): every stock shape and material stays byte for byte; the new
geometry is appended as new ec_* materials/shapes; stock props and BDHC are kept; permissions gain bit 15 on the
tiles in layout.blocked_tiles() only (behaviour bytes kept).

Checks (--write refuses on any FAIL): texture set append-only, round trip and VRAM; per chunk model <= 0xF000 and
BDHC <= 0x9000; every built NSBMD parses and rebuilds byte-identically; untouched stock shapes/materials identical;
permissions differ from stock only by bit 15 on the listed tiles; no warp/object/BG/coord event tile and no
KEEP_OPEN tile blocked; every stock walkable region stays connected after the blocks; the Cycling Road deck stays
continuous from the north gate to the south gate; every new solid face sits over blocked tiles (decals, light pools
and shadows excepted); ruts lie on flat ground; lighting keeps the stock schema.
"""
import collections
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as K  # noqa: E402
import layout as L  # noqa: E402
import textures as TX  # noqa: E402
import chunkedit as C  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402

FX = 4096

# ---------------------------------------------------------------------------------------------------------------
# heights (stock BDHC)
# ---------------------------------------------------------------------------------------------------------------


class Heights:
    def __init__(self):
        self.b = {c: mapdata.read_bdhc(mapdata.unpack(K.git_bytes(K.BASE_REV, K.chunk_rel(c)))["bdhc"])
                  for c in K.CHUNKS}

    def h(self, x, z, near=-99.0):
        """Mesh h (tiles; BDHC height / 16 - 1) of the stock walkable surface at absolute (x, z), the plate closest
        to `near` (mesh h) where several overlap (Cycling Road deck over the ground)."""
        c = K.chunk_of(math.floor(x), math.floor(z))
        if c is None:
            return None
        cx, cz = K.CHUNKS[c]
        lx, lz = (x - cx * 32) * 16 - 256, (z - cz * 32) * 16 - 256
        v = mapdata.height_at(self.b[c], round(lx * FX), round(lz * FX), current=round((near + 1) * 16 * FX))
        return None if v is None else v / FX / 16 - 1


# ---------------------------------------------------------------------------------------------------------------
# faces -> per-chunk mesh builders
# ---------------------------------------------------------------------------------------------------------------

# key -> (material name, texture, palette, lights, cull, alpha, polygon id)
MATS = {
    "crate": ("ec_crate_l", "ec_crate", "ec_crate_pl", 1, "back", 31, 0),
    "crate2": ("ec_crate_2s", "ec_crate", "ec_crate_pl", 1, "none", 31, 0),
    "glow": ("ec_crate_u", "ec_crate", "ec_crate_pl", 0, "back", 31, 0),      # unlit: frame glass + crystals
    "banner": ("ec_banner_2s", "ec_banner", "ec_banner_pl", 1, "none", 31, 0),
    "tarp": ("ec_tarp_l", "ec_banner", "ec_banner_pl", 1, "back", 31, 0),
    "barr": ("ec_barr_l", "ec_barricade", "ec_barricade_pl", 1, "back", 31, 0),
    "barr2": ("ec_barr_2s", "ec_barricade", "ec_barricade_pl", 1, "none", 31, 0),
    "lamp": ("ec_light_2s", "ec_light", "ec_light_pl", 1, "none", 31, 0),
    "lampu": ("ec_light_u2s", "ec_light", "ec_light_pl", 0, "none", 31, 0),
    # a5i3 (per-texel alpha) soft decals: no dithering, no checkerboard
    "pool": ("ec_pool_u", "ec_glow", "ec_glow_amb_pl", 0, "back", 12, 21),     # warm lamp light pool
    "vglow": ("ec_vglow_u", "ec_glow", "ec_glow_vio_pl", 0, "back", 11, 22),   # violet shard glow
    "shadow": ("ec_shadow_u", "ec_glow", "ec_glow_shd_pl", 0, "back", 15, 23),  # soft contact shadow
    # wheel tracks: opaque full track, then three translucent feather steps at each run end
    "ruts": ("ec_ruts_l", "ec_ruts", "ec_ruts_pl", 1, "back", 31, 0),
    "rutf2": ("ec_ruts_f24", "ec_ruts", "ec_ruts_pl", 1, "back", 24, 26),
    "rutf1": ("ec_ruts_f16", "ec_ruts", "ec_ruts_pl", 1, "back", 16, 25),
    "rutf0": ("ec_ruts_f09", "ec_ruts", "ec_ruts_pl", 1, "back", 9, 24),
}
RUT_KEYS = ("ruts", "rutf2", "rutf1", "rutf0")
DECAL_KEYS = set(RUT_KEYS) | {"pool", "vglow", "shadow"}


class Art:
    def __init__(self, tex_size):
        self.mb = {c: C.MeshBuilder() for c in K.CHUNKS}
        self.tex_size = tex_size
        self.solids = []           # (key, pts) of every non-decal face
        self.decals = []
        self.groups = collections.Counter()

    def add(self, key, pts, uvs, facing=None, colors=None, group="misc"):
        pts = [tuple(float(v) for v in p) for p in pts]
        uvs = [list(u) for u in uvs]
        colors = [tuple(c) for c in colors] if colors else [(255, 255, 255)] * len(pts)
        n = C.face_normal(pts)
        if facing is not None and sum(a * b for a, b in zip(n, facing)) < 0:
            pts, uvs, colors = pts[::-1], uvs[::-1], colors[::-1]
            n = C.face_normal(pts)
        name, tex, pal, lights, cull, alpha, pid = MATS[key]
        if key in RUT_KEYS:                # the only repeating texture: rebase v per face (s16 UV range)
            lo = math.floor(min(u[1] for u in uvs) + 1e-6)
            for u in uvs:
                u[1] -= lo
        cx = sum(p[0] for p in pts) / len(pts)
        cz = sum(p[2] for p in pts) / len(pts)
        c = K.chunk_of(math.floor(cx), math.floor(cz))
        assert c is not None, (key, pts)
        mb = self.mb[c]
        mb.material(name, tex, pal, self.tex_size[tex], lights=lights, cull=cull, alpha=alpha, polygon_id=pid)
        me = mb.meshes[name]
        b = len(me["positions"])
        me["positions"] += [list(p) for p in pts]
        me["uvs"] += uvs
        me["colors"] += [list(cc) for cc in colors]
        me["normals"] += [list(n)] * len(pts)
        (me["quads"] if len(pts) == 4 else me["tris"]).append(list(range(b, b + len(pts))))
        (self.decals if key in DECAL_KEYS else self.solids).append((key, pts))
        self.groups[group] += 1

    def polygons(self):
        return {c: mb.polygons() for c, mb in self.mb.items()}


def sub(uv, a, b, c, d):
    """Sub-rectangle (fractions a..c across, b..d down) of a uv rect."""
    u0, v0, u1, v1 = uv
    return (u0 + (u1 - u0) * a, v0 + (v1 - v0) * b, u0 + (u1 - u0) * c, v0 + (v1 - v0) * d)


def quad_uv(uv):
    """uv rect -> corner uvs for pts ordered top-left, top-right, bottom-right, bottom-left."""
    u0, v0, u1, v1 = uv
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


# ---------------------------------------------------------------------------------------------------------------
# primitives
# ---------------------------------------------------------------------------------------------------------------

def rot(cx, cz, lx, lz, yaw):
    s, c = math.sin(yaw), math.cos(yaw)
    return cx + lx * c - lz * s, cz + lx * s + lz * c


def box(F, cx, cz, w, d, h0, h1, side, top, yaw=0.0, key="crate", front=None, front_key=None, front_cols=None,
        sides="sewt", group="box", side_cols=None):
    """Upright box centred on (cx, cz). side/top: uv rects; front: uv rect for the south face (key front_key).
    North faces are left out by default: the field camera always looks north, so they are never visible."""
    hw, hd = w / 2, d / 2
    P = {k: rot(cx, cz, lx, lz, yaw) for k, (lx, lz) in
         {"nw": (-hw, -hd), "ne": (hw, -hd), "se": (hw, hd), "sw": (-hw, hd)}.items()}
    walls = {"s": ("sw", "se", (0, 0, 1)), "n": ("ne", "nw", (0, 0, -1)), "e": ("se", "ne", (1, 0, 0)),
             "w": ("nw", "sw", (-1, 0, 0))}
    for k in "snew":
        if k not in sides:
            continue
        a, b, nrm = walls[k]
        nrm = (rot(0, 0, nrm[0], nrm[2], yaw)[0], 0.0, rot(0, 0, nrm[0], nrm[2], yaw)[1])
        (xa, za), (xb, zb) = P[a], P[b]
        uv = front if (k == "s" and front) else side
        kk = front_key if (k == "s" and front_key) else key
        cols = front_cols if (k == "s" and front_cols) else side_cols
        F.add(kk, [(xa, h1, za), (xb, h1, zb), (xb, h0, zb), (xa, h0, za)], quad_uv(uv), nrm, cols, group)
    if "t" in sides:
        F.add(key, [(P["sw"][0], h1, P["sw"][1]), (P["se"][0], h1, P["se"][1]), (P["ne"][0], h1, P["ne"][1]),
                    (P["nw"][0], h1, P["nw"][1])], [(top[0], top[3]), (top[2], top[3]), (top[2], top[1]),
                                                    (top[0], top[1])], (0, 1, 0), None, group)


def card(F, key, x0, x1, zb, h0, h1, uv, lean=0.0, cols=None, group="card"):
    """South-facing upright card on z = zb from x0 to x1, its top leaning back (north) by `lean` degrees."""
    dz = (h1 - h0) * math.tan(math.radians(lean))
    n = (0.0, math.sin(math.radians(lean)), math.cos(math.radians(lean)))
    F.add(key, [(x0, h1, zb - dz), (x1, h1, zb - dz), (x1, h0, zb), (x0, h0, zb)], quad_uv(uv), n, cols, group)


def card_ns(F, key, z0, z1, xb, h0, h1, uv, cols=None, group="card"):
    """East-facing upright card on x = xb from z1 (left, south) to z0 (right, north)."""
    F.add(key, [(xb, h1, z1), (xb, h1, z0), (xb, h0, z0), (xb, h0, z1)], quad_uv(uv), (1, 0, 0), cols, group)


def decal(F, key, x0, z0, x1, z1, h, uv, cols=None, group="decal"):
    u0, v0, u1, v1 = uv
    F.add(key, [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)], [(u0, v1), (u1, v1), (u1, v0), (u0, v0)],
          (0, 1, 0), cols, group)


CU = TX.CRATE_UV
BU = TX.BARR_UV
LU = TX.LIGHT_UV
GU = TX.GLOW_UV
TU = TX.BANNER_UV
STEEL = CU["steel"]


def shadow(F, cx, cz, rx, rz, h):
    """Soft contact shadow: one quad of the a5i3 shadow disc (solid core, feathered rim) centred on (cx, cz)."""
    decal(F, "shadow", cx - rx, cz - rz, cx + rx, cz + rz, h, GU["shadow"], group="shadow")


def pool(F, cx, z0, z1, hw, h):
    decal(F, "pool", cx - hw, z0, cx + hw, z1, h, GU["pool"], group="light")


def vglow(F, cx, z0, z1, hw, h):
    decal(F, "vglow", cx - hw, z0, cx + hw, z1, h, GU["pool"], group="light")


def crate(F, cx, cz, s, h0, yaw=0.0, tall=1.0, d=None):
    big = s >= 0.6                         # 12x12 cells for big crates, 8x8 for small ones (true texel density)
    box(F, cx, cz, s, d or s, h0, h0 + s * tall, CU["side" if big else "side_s"], CU["lid" if big else "lid_s"], yaw,
        group="crates")
    return h0 + s * tall


def pallet(F, cx, cz, w, d, h0, yaw=0.0):
    """Wooden pallet: slatted block sides, plank top."""
    box(F, cx, cz, w, d, h0, h0 + 0.14, CU["pallet"], CU["lid"], yaw, group="crates")
    return h0 + 0.14


def canister_case(F, cx, cz, w, d, h0, h1, yaw=0.0):
    """A low case of strapped shard canisters: the containment-frame glass on its front (unlit), steel body."""
    box(F, cx, cz, w, d, h0, h1, STEEL, STEEL, yaw, key="crate", front=CU["case"], front_key="glow",
        group="racks")


def crystal(F, cx, cz, h0, r, body, tip, yaw=0.0):
    """Faceted violet shard: a square prism turned 45 deg to the camera with a pyramid point; unlit, each facet a
    flat vertex colour (lit south-west facet, darker east facets)."""
    corners = [rot(cx, cz, r * math.cos(a), r * math.sin(a), 0.0) for a in
               [yaw + math.pi / 4 + k * math.pi / 2 for k in range(4)]]
    uv = CU["xtal"]
    uvq = [(uv[0], uv[1]), (uv[2], uv[1]), (uv[2], uv[3]), (uv[0], uv[3])]
    ap = (cx, h0 + body + tip, cz)
    light = (-0.75, 0.66)                                             # towards the light: west and south
    for k in range(4):
        (xa, za), (xb, zb) = corners[k], corners[(k + 1) % 4]
        nx, nz = (xa + xb) / 2 - cx, (za + zb) / 2 - cz
        nn = math.hypot(nx, nz) or 1.0
        lam = max(0.0, (nx * light[0] + nz * light[1]) / nn)
        if nz / nn < -0.3:
            continue                                                  # north-facing facets are never seen
        v = 0.55 + 0.45 * lam
        col = tuple(int(min(255, c * v)) for c in (255, 248, 255))
        capc = tuple(int(min(255, c * min(1.0, v + 0.18))) for c in (255, 248, 255))
        F.add("glow", [(xb, h0 + body, zb), (xa, h0 + body, za), (xa, h0, za), (xb, h0, zb)], uvq,
              (nx, 0.0, nz), [col] * 4, "crystals")
        F.add("glow", [ap, (xa, h0 + body, za), (xb, h0 + body, zb)], uvq[:3], (nx, 0.6, nz), [capc] * 3,
              "crystals")


# ---------------------------------------------------------------------------------------------------------------
# props
# ---------------------------------------------------------------------------------------------------------------

def p_stack(F, x, z, G, p):
    cx, cz = x + 0.5, z + 0.5
    k = p.get("kind", "pair")
    yaw = p.get("yaw", 0.0)
    if k == "pallet3":
        t = pallet(F, cx, cz + 0.02, 0.88, 0.8, G, yaw)
        crate(F, cx - 0.21, cz + 0.06, 0.42, t, yaw + 0.06)
        crate(F, cx + 0.22, cz + 0.06, 0.42, t, yaw - 0.05, tall=1.15)
        crate(F, cx - 0.04, cz + 0.06, 0.38, t + 0.42, yaw + 0.2)
        shadow(F, cx, cz + 0.08, 0.62, 0.52, G + 0.01)
    elif k == "pallet2":
        t = pallet(F, cx, cz + 0.04, 0.86, 0.72, G, yaw)
        crate(F, cx - 0.18, cz + 0.06, 0.44, t, yaw + 0.04)
        crate(F, cx + 0.22, cz + 0.08, 0.36, t, yaw - 0.12, tall=0.9)
        shadow(F, cx, cz + 0.07, 0.6, 0.48, G + 0.01)
    elif k == "pair":
        t = crate(F, cx - 0.06, cz + 0.08, 0.62, G, yaw + 0.04)
        crate(F, cx + 0.04, cz + 0.1, 0.42, t, yaw - 0.21)
        shadow(F, cx - 0.04, cz + 0.1, 0.5, 0.46, G + 0.01)
    elif k == "tall":
        t = pallet(F, cx, cz + 0.02, 0.88, 0.8, G, yaw)
        t = crate(F, cx, cz + 0.05, 0.72, t, yaw - 0.03)
        t = crate(F, cx - 0.04, cz + 0.08, 0.56, t, yaw + 0.14)
        crate(F, cx + 0.05, cz + 0.1, 0.38, t, yaw - 0.26)
        shadow(F, cx, cz + 0.08, 0.62, 0.52, G + 0.01)
    elif k == "equip":
        # the parked Eclipse equipment crate: a long crate on a pallet, hazard label, a small crate on top
        t = pallet(F, cx, cz + 0.04, 0.94, 0.84, G, yaw)
        box(F, cx, cz + 0.06, 0.84, 0.66, t, t + 0.62, CU["side"], CU["lid"], yaw, group="crates")
        card(F, "crate", cx - 0.17, cx + 0.17, cz + 0.06 + 0.33 + 0.012, t + 0.14, t + 0.48, CU["label"],
             group="crates")
        crate(F, cx + 0.16, cz + 0.08, 0.4, t + 0.62, yaw + 0.22)
        shadow(F, cx, cz + 0.08, 0.64, 0.52, G + 0.01)
    elif k == "canisters":
        t = pallet(F, cx, cz + 0.02, 0.9, 0.8, G, yaw)
        canister_case(F, cx, cz + 0.04, 0.84, 0.62, t, t + 0.6, yaw)
        crate(F, cx + 0.14, cz + 0.04, 0.34, t + 0.6, yaw + 0.2)
        vglow(F, cx, z + 0.7, z + 1.7, 0.75, G + 0.02)
        shadow(F, cx, cz + 0.06, 0.62, 0.5, G + 0.01)


def p_frame(F, x, z, G, p):
    """Shard-containment frame: steel plinth, two front corner posts and a top cap around an unlit glass core with
    the faceted crystal cluster, a big faceted shard rising through the cap, violet glow spilling south."""
    cx, cz = x + 0.5, z + 0.56
    yaw = p.get("yaw", 0.0)
    ht = p.get("ht", 1.5)
    w, d = 0.8, 0.54
    box(F, cx, cz, w + 0.1, d + 0.1, G, G + 0.12, STEEL, STEEL, yaw, group="racks")
    h0, h1 = G + 0.12, G + ht - 0.1
    box(F, cx, cz, w - 0.06, d - 0.08, h0, h1, CU["frame_glass"], STEEL, yaw, key="glow", front=CU["frame"],
        front_key="glow", sides="sew", side_cols=[(196, 186, 220)] * 4, group="racks")
    steel_bar = sub(STEEL, 0, 0, 0.12, 1)
    for sx in (-1, 1):
        px, pz = rot(cx, cz, sx * (w / 2 - 0.02), d / 2 - 0.03, yaw)
        box(F, px, pz, 0.09, 0.09, h0, h1, steel_bar, steel_bar, yaw, sides="sew", group="racks")
    box(F, cx, cz, w + 0.06, d + 0.06, h1, h1 + 0.1, STEEL, STEEL, yaw, group="racks")
    crystal(F, cx - 0.06, cz - 0.02, h1 + 0.1, 0.13, 0.22 + 0.1 * (ht > 1.6), 0.24, yaw)
    crystal(F, cx + 0.2, cz + 0.04, h1 + 0.1, 0.075, 0.08, 0.14, yaw + 0.4)
    vglow(F, cx, z + 0.75, z + 1.85, 0.85, G + 0.021)
    shadow(F, cx, cz + 0.04, 0.6, 0.44, G + 0.01)


def p_tarp(F, x, z, G, p):
    """A tarp-covered crate stack on a pallet: violet canvas drawn over the top and flaring at the skirt."""
    cx, cz = x + 0.5, z + 0.54
    yaw = p.get("yaw", 0.0)
    t = pallet(F, cx, cz, 0.92, 0.8, G, yaw)
    ht = G + p.get("ht", 1.1)
    rings = [(0.62, 0.5, ht), (0.8, 0.68, ht - 0.16), (0.86, 0.74, t)]
    tu = TU["tarp"]
    vs = [tu[1], tu[1] + (tu[3] - tu[1]) * 0.2, tu[3]]

    def ring(i):
        w, d, h = rings[i]
        return {k: (rot(cx, cz, lx, lz, yaw), h) for k, (lx, lz) in
                {"nw": (-w / 2, -d / 2), "ne": (w / 2, -d / 2), "se": (w / 2, d / 2), "sw": (-w / 2, d / 2)}.items()}
    R = [ring(i) for i in range(3)]

    def P(r, k):
        (xx, zz), h = R[r][k]
        return (xx, h, zz)
    tt = TU["tarp_top"]
    F.add("tarp", [P(0, "sw"), P(0, "se"), P(0, "ne"), P(0, "nw")], [(tt[0], tt[3]), (tt[2], tt[3]), (tt[2], tt[1]),
                                                                     (tt[0], tt[1])], (0, 1, 0), None, "tarps")
    for a, b, nrm in (("sw", "se", (0, 0, 1)), ("se", "ne", (1, 0, 0)), ("nw", "sw", (-1, 0, 0))):
        nrm = (rot(0, 0, nrm[0], nrm[2], yaw)[0], 0.25, rot(0, 0, nrm[0], nrm[2], yaw)[1])
        for i in range(2):
            F.add("tarp", [P(i, a), P(i, b), P(i + 1, b), P(i + 1, a)],
                  [(tu[0], vs[i]), (tu[2], vs[i]), (tu[2], vs[i + 1]), (tu[0], vs[i + 1])], nrm, None, "tarps")
    shadow(F, cx, cz + 0.06, 0.62, 0.52, G + 0.01)


def p_lamp(F, x, z, G, p):
    """Tripod work lamp: lit legs, an unlit glowing head, a soft warm a5i3 light pool on the ground."""
    cx, zb = x + 0.5, z + 0.62
    h_total = 2.0
    split = 12 / 32
    h_split = G + h_total * (1 - split)
    lean = 8.0
    t = math.tan(math.radians(lean))
    card(F, "lamp", cx - 0.5, cx + 0.5, zb, G, h_split, LU["lamp_legs"], lean, group="lamps")
    zs = zb - (h_split - G) * t
    card(F, "lampu", cx - 0.5, cx + 0.5, zs, h_split, G + h_total, LU["lamp_head"], lean, group="lamps")
    pool(F, cx, z - 0.1, z + 2.3, 1.25, G + 0.024)
    shadow(F, cx, zb - 0.02, 0.42, 0.26, G + 0.012)


def p_banner(F, x, z, G, p):
    px, pz = x + 0.12, z + 0.5
    top = G + 2.9
    box(F, px, pz, 0.1, 0.1, G, top, sub(STEEL, 0, 0, 0.1, 1), sub(STEEL, 0, 0, 0.1, 0.25), group="banners")
    box(F, px + 0.42, pz, 0.84, 0.07, top - 0.16, top - 0.09, sub(STEEL, 0, 0, 1, 0.25), sub(STEEL, 0, 0, 1, 0.25),
        group="banners")
    card(F, "banner", x + 0.17, x + 0.93, pz + 0.03, G + 0.86, top - 0.12, TU["tall"], group="banners")
    box(F, px, pz, 0.16, 0.16, top, top + 0.08, STEEL, STEEL, group="banners")       # finial cap
    box(F, px, pz, 0.24, 0.24, G, G + 0.1, STEEL, STEEL, group="banners")            # weighted foot
    shadow(F, px + 0.12, pz + 0.04, 0.3, 0.22, G + 0.01)


def p_manifest(F, x, z, G, p):
    """The Staging Yard manifest crate (BG event): a full-size crate with the manifest clipboard on its south face,
    a smaller crate on top with the shard hazard label."""
    cx, cz = x + 0.5, z + 0.5
    s = 0.86
    t = crate(F, cx, cz + 0.04, s, G, 0.0)
    card(F, "crate", cx - 0.2, cx + 0.2, cz + 0.04 + s / 2 + 0.012, G + 0.26, G + 0.66, CU["manifest"], lean=0,
         group="crates")
    crate(F, cx - 0.08, cz + 0.06, 0.48, t, 0.16)
    card(F, "crate", cx + 0.02, cx + 0.3, cz + 0.06 + 0.24 + 0.012, t + 0.1, t + 0.38, CU["label"], group="crates")
    shadow(F, cx, cz + 0.08, 0.64, 0.54, G + 0.01)


def barricade_x(F, x0, x1, zc, G):
    """A-frame road barricade from x0 to x1 (tiles) centred on z = zc: two hazard planks, steel legs, CLOSED board."""
    L_ = x1 - x0
    steel = sub(STEEL, 0, 0, 0.12, 1)
    for u in (x0 + 0.1, x1 - 0.1):
        for sgn in (-1, 1):
            F.add("crate2", [(u - 0.03, G + 0.82, zc), (u + 0.03, G + 0.82, zc), (u + 0.03, G, zc + 0.26 * sgn),
                             (u - 0.03, G, zc + 0.26 * sgn)], quad_uv(steel), (0, 0.3, sgn), None, "barricades")
    for h0, h1 in ((G + 0.5, G + 0.76), (G + 0.2, G + 0.38)):
        F.add("barr2", [(x0, h1, zc + 0.012), (x1, h1, zc + 0.012), (x1, h0, zc + 0.012), (x0, h0, zc + 0.012)],
              [(0, BU["stripe"][1]), (L_ / 2, BU["stripe"][1]), (L_ / 2, BU["stripe"][3]), (0, BU["stripe"][3])],
              (0, 0, 1), None, "barricades")
    xm = (x0 + x1) / 2
    bw = min(0.6, L_ / 2 - 0.02)
    card(F, "barr2", xm - bw, xm + bw, zc + 0.02, G + 0.8, G + 1.1, BU["board"], lean=6, group="barricades")
    for u in (xm - bw * 0.7, xm + bw * 0.7):     # board posts
        card(F, "crate2", u - 0.025, u + 0.025, zc + 0.016, G + 0.74, G + 0.84, steel, group="barricades")
    shadow(F, xm, zc + 0.02, L_ / 2 + 0.06, 0.26, G + 0.01)


def cone(F, cx, cz, G, s=1.0):
    u0, v0, u1, v1 = BU["cone"]
    apex_v, base_v = v0, v1
    um = (u0 + u1) / 2
    r, ht = 0.17 * s, 0.55 * s
    a = (cx, G + ht, cz)
    c4 = [(cx - r, G + 0.03, cz + r), (cx + r, G + 0.03, cz + r), (cx + r, G + 0.03, cz - r),
          (cx - r, G + 0.03, cz - r)]
    for k in range(3):                   # the north facet is never seen
        p, q = c4[k], c4[(k + 1) % 4]
        if k == 1:
            p, q = c4[3], c4[0]          # west facet
        nrm = ((p[0] + q[0]) / 2 - cx, 0.4, (p[2] + q[2]) / 2 - cz)
        F.add("barr", [a, q, p], [(um, apex_v), (u1 - 0.03, base_v), (u0 + 0.03, base_v)], nrm, None, "cones")
    b = 0.17 * s
    decal(F, "barr", cx - b, cz - b, cx + b, cz + b, G + 0.03, BU["cone_base"], group="cones")
    shadow(F, cx + 0.02, cz + 0.03, 0.27 * s, 0.24 * s, G + 0.008)


def p_barricade(F, x, z, G, p):
    barricade_x(F, x + 0.04, p["x1"] - 0.04, z + 0.5, G)


def p_cones(F, x, z, G, p):
    if p.get("n", 1) == 1:
        cone(F, x + 0.5, z + 0.5, G)
    else:
        cone(F, x + 0.3, z + 0.35, G)
        cone(F, x + 0.68, z + 0.66, G, 0.9)


def p_cones_line(F, x, z, G, p, H):
    for zz in range(z, p["z1"]):
        g = H.h(x + 0.5, zz + 0.5, 99 if p.get("deck") else -99)
        cone(F, x + 0.62, zz + 0.5, g, 0.95)


def fence_run(F, a, b, line, G, axis="x"):
    """Steel chain-link fence panels, one fence cell per tile, posts at every tile boundary."""
    fu = BU["fence"]
    for t in range(int(math.floor(a)), int(math.ceil(b))):
        t0, t1 = max(a, t), min(b, t + 1)
        f0, f1 = t0 - t, t1 - t
        uv = (fu[0] + (fu[2] - fu[0]) * f0, fu[1], fu[0] + (fu[2] - fu[0]) * f1, fu[3])
        if axis == "x":
            card(F, "barr2", t0, t1, line, G, G + 0.9, uv, group="fences")
        else:
            card_ns(F, "barr2", t0, t1, line, G, G + 0.9, uv, group="fences")
    steel = sub(STEEL, 0, 0, 0.08, 1)
    k = a
    while k <= b + 1e-6:
        if axis == "x":
            box(F, k, line, 0.07, 0.07, G, G + 0.98, steel, steel, group="fences")
        else:
            box(F, line, k, 0.07, 0.07, G, G + 0.98, steel, steel, group="fences")
        k += 1.0


def p_fence(F, x, z, G, p):
    fence_run(F, x + 0.06, p["x1"] - 0.06, p["zline"], G, "x")


def p_fence_ns(F, x, z, G, p):
    fence_run(F, z + 0.06, p["z1"] - 0.06, p["xline"], G, "z")


def p_sign(F, x, z, G, p):
    """ROAD CLOSED sign (BG event): CLOSED board on two posts, a small Eclipse pennant on the right post."""
    cx, zb = x + 0.5, z + 0.62
    steel = sub(STEEL, 0, 0, 0.1, 1)
    for u in (cx - 0.32, cx + 0.32):
        box(F, u, zb - 0.02, 0.06, 0.06, G, G + 0.98, steel, steel, group="signs")
    card(F, "barr2", cx - 0.48, cx + 0.48, zb + 0.035, G + 0.62, G + 0.92, BU["board"], lean=8, group="signs")
    card(F, "barr2", cx - 0.48, cx + 0.48, zb + 0.02, G + 0.42, G + 0.56, sub(BU["stripe"], 0, 0, 0.5, 1), lean=0,
         group="signs")
    card(F, "banner", cx + 0.34, cx + 0.48, zb + 0.01, G + 0.98, G + 1.32, TU["pennant"], group="signs")
    shadow(F, cx, zb, 0.52, 0.2, G + 0.01)


BUILDERS = {"stack": p_stack, "rack": p_frame, "frame": p_frame, "tarp": p_tarp, "lamp": p_lamp,
            "banner": p_banner, "manifest": p_manifest, "barricade": p_barricade, "cones": p_cones,
            "fence": p_fence, "fence_ns": p_fence_ns, "sign": p_sign}


# ---------------------------------------------------------------------------------------------------------------
# ruts: two wheel tracks, clipped to bare dirt / sand ground, feathered at every run end
# ---------------------------------------------------------------------------------------------------------------

MASK_BOX = (296, 696, 344, 720)      # tiles x0, z0, x1, z1 the ruts can touch
MASK_PPT = 16


def ground_mask():
    """Stock ground (chunks at BASE_REV, stock set 007) rendered straight down at 16 px/tile -> bool array, True on
    bare dirt / sand texels (no green: grass and its sand-edge fringe are False; so is anything not drawn)."""
    import numpy as np
    import render as R
    models = {c: mapdata.unpack(K.git_bytes(K.BASE_REV, K.chunk_rel(c)))["model"] for c in (25, 26, 27)}
    x0, z0, x1, z1 = MASK_BOX
    w, h = (x1 - x0) * MASK_PPT, (z1 - z0) * MASK_PPT
    meshes = R.collect(models, R.texture_arrays(K.git_bytes(K.BASE_REV, K.BASE_SET_REL)),
                       dict(R.DAY, amb=(1.0, 1.0, 1.0), light=(0.0, 0.0, 0.0)))
    img = R.rasterise(meshes, R.top_projector(x0, z0, MASK_PPT), w, h, (1.0, 0.0, 1.0)) * 255
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    sky = (r > 250) & (g < 5) & (b > 250)
    green = (g > r + 4) & (g >= b - 10)
    return ~(green | sky)


class RutClip:
    def __init__(self, H):
        self.H = H
        self.mask = ground_mask()
        self.walk = {}
        for c, (cx, cz) in K.CHUNKS.items():
            P = mapdata.read_permissions(mapdata.unpack(K.git_bytes(K.BASE_REV, K.chunk_rel(c)))["permissions"])
            for lz in range(32):
                for lx in range(32):
                    self.walk[(cx * 32 + lx, cz * 32 + lz)] = not P[lz][lx] & K.BLOCK

    def ok(self, x, z):
        """Bare dirt texel, on a stock-walkable tile, at road height (no ledge or cliff)."""
        x0, z0, x1, z1 = MASK_BOX
        if not (x0 <= x < x1 and z0 <= z < z1):
            return False
        if not self.walk.get((math.floor(x), math.floor(z))):
            return False
        hh = self.H.h(x, z, 4.0)
        if hh is None or abs(hh - 4.0) > 0.02:
            return False
        return bool(self.mask[int((z - z0) * MASK_PPT), int((x - x0) * MASK_PPT)])


def rut_centreline():
    """Polyline every 0.25 tile (chunk borders x 320 and z 704 fall on samples): south along the sand lane, a
    quarter arc, east along RUT_LINE_Z."""
    x0, z0 = L.RUT_START
    cx, cz = L.RUT_TURN_CENTRE
    r = cx - x0
    pts = [(x0, z0 + 0.25 * k) for k in range(int(round((cz - z0) / 0.25)) + 1)]
    n = 32
    for k in range(1, n + 1):
        a = math.pi - (math.pi / 2) * k / n                  # 180 deg -> 90 deg: west -> south of the centre
        pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    ze = L.RUT_LINE_Z
    pts += [(cx + 0.25 * k, ze) for k in range(1, int(round((L.RUT_END_X - cx) / 0.25)) + 1)]
    return pts


TRACK_HALF = 0.5          # quad half-width (16 texels = 1 tile across)
TRACK_OPAQUE = 0.3        # half-width of the painted track (groove + lips)
FADE_ALPHA_KEYS = ["rutf0", "rutf1", "rutf2", "ruts"]      # feather steps from the very end inwards


def build_ruts(F, H):
    clip = RutClip(H)
    cl = rut_centreline()
    tang = []
    for i in range(len(cl)):
        a, b = cl[max(i - 1, 0)], cl[min(i + 1, len(cl) - 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]
        nn = math.hypot(tx, tz)
        tang.append((tx / nn, tz / nn))
    stats = dict(segments=0, kept=0, runs=0, quads=0, dropped_short=0)
    hs = []
    for off in (L.RUT_TRACK, -L.RUT_TRACK):
        # track points and per-point left normal
        P, N = [], []
        for (x, z), (tx, tz) in zip(cl, tang):
            lx, lz = -tz, tx
            P.append((x + lx * off, z + lz * off))
            N.append((lx, lz))
        seg_ok = []
        for i in range(len(P) - 1):
            good = True
            for f in (0.0, 0.25, 0.5, 0.75, 1.0):
                px = P[i][0] + (P[i + 1][0] - P[i][0]) * f
                pz = P[i][1] + (P[i + 1][1] - P[i][1]) * f
                nx = N[i][0] + (N[i + 1][0] - N[i][0]) * f
                nz = N[i][1] + (N[i + 1][1] - N[i][1]) * f
                for o in (-TRACK_OPAQUE, -0.15, 0.0, 0.15, TRACK_OPAQUE):
                    if not clip.ok(px + nx * o, pz + nz * o):
                        good = False
            seg_ok.append(good)
        stats["segments"] += len(seg_ok)
        # runs of kept segments
        runs, i = [], 0
        while i < len(seg_ok):
            if seg_ok[i]:
                j = i
                while j < len(seg_ok) and seg_ok[j]:
                    j += 1
                runs.append((i, j))
                i = j
            else:
                i += 1
        for i0, i1 in runs:
            seglen = [math.hypot(P[k + 1][0] - P[k][0], P[k + 1][1] - P[k][1]) for k in range(i0, i1)]
            Lr = sum(seglen)
            if Lr < 2.5:                                     # no stubs: short patches stay bare
                stats["dropped_short"] += 1
                continue
            stats["runs"] += 1
            stats["kept"] += i1 - i0
            fl = min(1.5, Lr / 3)
            s_at = [0.0]
            for sl in seglen:
                s_at.append(s_at[-1] + sl)
            pieces = []        # (key, k0, k1, is_fade) over point indices
            for k in range(i0, i1):
                sm = (s_at[k - i0] + s_at[k + 1 - i0]) / 2
                de = min(sm, Lr - sm)                       # distance from the nearer run end
                if de < fl:
                    key = FADE_ALPHA_KEYS[min(3, int(4 * de / fl))]
                    fade = True
                else:
                    key, fade = "ruts", False
                ch = K.chunk_of(math.floor((P[k][0] + P[k + 1][0]) / 2), math.floor((P[k][1] + P[k + 1][1]) / 2))
                straight = abs(tang[k][0] - tang[k + 1][0]) < 1e-6 and abs(tang[k][1] - tang[k + 1][1]) < 1e-6
                tag = (key, fade, ch, sm < Lr / 2 if fade else None)
                if pieces and pieces[-1][0] == tag and pieces[-1][3] and straight:
                    pieces[-1][2] = k + 1
                else:
                    pieces.append([tag, k, k + 1, straight])

            def vcoord(k, fade, start_side):
                s = s_at[k - i0]
                if not fade:
                    return s / 2.0                           # 32 texels per 2 tiles
                de = s if start_side else Lr - s
                t = 1.0 - min(1.0, de / fl)                  # 0 joins the full track, 1 is the very end
                return (0.5 + 31.0 * t) / 32.0
            for (key, fade, ch, start_side), k0, k1, _ in pieces:
                u0, u1 = (16.5 / 32, 31.5 / 32) if fade else (0.5 / 32, 15.5 / 32)
                la = (P[k0][0] + N[k0][0] * TRACK_HALF, P[k0][1] + N[k0][1] * TRACK_HALF)
                lb = (P[k1][0] + N[k1][0] * TRACK_HALF, P[k1][1] + N[k1][1] * TRACK_HALF)
                ra = (P[k0][0] - N[k0][0] * TRACK_HALF, P[k0][1] - N[k0][1] * TRACK_HALF)
                rb = (P[k1][0] - N[k1][0] * TRACK_HALF, P[k1][1] - N[k1][1] * TRACK_HALF)
                va, vb = vcoord(k0, fade, start_side), vcoord(k1, fade, start_side)
                q = [la, lb, rb, ra]
                hq = [H.h(px, pz, 4.0) for px, pz in q]
                hs += hq
                Pq = [(px, hh + 0.012, pz) for (px, pz), hh in zip(q, hq)]
                F.add(key, Pq, [(u1, va), (u1, vb), (u0, vb), (u0, va)], (0, 1, 0), None, "ruts")
                stats["quads"] += 1
    return hs, stats


# ---------------------------------------------------------------------------------------------------------------
# lighting
# ---------------------------------------------------------------------------------------------------------------

NIGHT = ((9, 10, 18), (12, 13, 17), (9, 10, 14), (12, 12, 17), (6, 7, 11))   # deep indigo-green, clean
LIGHT_CURVE = {           # light 0 colour, diffuse, ambient, specular, emission (5-bit)
    0: NIGHT,
    7200: NIGHT,                                                                         # 00:00-04:00 indigo night
    8100: ((11, 11, 19), (11, 11, 15), (10, 10, 14), (9, 9, 14), (8, 8, 12)),            # 04:00-04:30 pre-dawn
    9000: ((17, 14, 16), (12, 11, 12), (10, 9, 10), (11, 10, 12), (12, 10, 11)),         # 04:30-05:00 dusty dawn
    14400: ((22, 19, 15), (14, 13, 12), (9, 8, 8), (13, 12, 12), (13, 12, 11)),          # 05:00-08:00 hazy morning
    20700: ((24, 21, 16), (15, 14, 13), (9, 9, 8), (15, 14, 13), (14, 13, 12)),          # 08:00-11:30 dusty day
    21600: ((26, 23, 18), (16, 15, 14), (10, 10, 9), (16, 15, 14), (14, 13, 12)),        # 11:30-12:00 noon glare
    27000: ((27, 23, 17), (17, 15, 13), (11, 10, 9), (17, 16, 14), (14, 13, 11)),        # 12:00-15:00 industrial amber
    27900: ((27, 21, 14), (17, 15, 12), (11, 10, 9), (17, 15, 13), (14, 12, 10)),        # 15:00-15:30 late afternoon
    30600: ((27, 19, 11), (16, 14, 11), (11, 9, 8), (16, 14, 12), (13, 10, 8)),          # 15:30-17:00 dusty amber
    32400: ((25, 15, 9), (15, 12, 10), (10, 9, 9), (15, 13, 12), (11, 8, 7)),            # 17:00-18:00 rust sunset
    33300: ((19, 11, 11), (14, 12, 12), (10, 9, 11), (14, 12, 13), (9, 7, 9)),           # 18:00-18:30 ember dusk
    34200: ((14, 10, 16), (13, 12, 14), (10, 9, 13), (13, 12, 15), (8, 7, 11)),          # 18:30-19:00 violet dusk
    36000: ((10, 10, 18), (13, 12, 16), (9, 9, 14), (12, 12, 16), (7, 7, 11)),           # 19:00-20:00 dusk indigo
    43200: NIGHT,                                                                        # 20:00-24:00 stark night
}


def build_lighting():
    raw = K.git_bytes(K.BASE_REV, K.LIGHTING_TEMPLATE).decode()
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
    for b, t in zip(back, tmpl):
        if b["endTime"] != t["endTime"]:
            fails.append("lighting: block times differ")
        cols = [b[k] for k in ("diffuseColor", "ambientColor", "specularColor", "emissionColor")] + \
            [lt["color"] for lt in b["lights"]]
        if any(not (0 <= v <= 31) for c in cols for v in c.values()):
            fails.append(f"lighting: colour out of range at {b['endTime']}")
        if b["lights"][1:] != t["lights"][1:] or b["lights"][0]["direction"] != t["lights"][0]["direction"]:
            fails.append(f"lighting: light directions / lights 1..3 changed at {b['endTime']}")
    return text, fails


# ---------------------------------------------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------------------------------------------

def build():
    set_bytes, tex_rep, tex_fails, gen = TX.build_set()
    tex_table, pal_names = C.texture_table(set_bytes)
    tex_size = {k: v["size"] for k, v in tex_table.items()}
    H = Heights()
    F = Art(tex_size)
    rut_h, rut_stats = build_ruts(F, H)
    placed = []
    for kind, x, z, p in L.PROPS:
        if kind == "block":
            continue
        near = 99.0 if p.get("deck") else -99.0
        G = p["h"] if "h" in p else H.h(x + 0.5, z + 0.5, near)
        if kind == "cones_line":
            p_cones_line(F, x, z, G, p, H)
        else:
            BUILDERS[kind](F, x, z, G, p)
        placed.append((kind, x, z, round(G, 3)))
    blocked = L.blocked_tiles()
    out = {}
    for c, cell in K.CHUNKS.items():
        edit = C.ChunkEdit(K.chunk_rel(c), cell, K.BASE_REV)
        edit.add(F.mb[c], tex_table)
        model = edit.model_bytes()
        perm = edit.permissions()
        for (x, z) in blocked:
            if K.chunk_of(x, z) == c:
                perm[z - cell[1] * 32][x - cell[0] * 32] |= K.BLOCK
        data = edit.pack(perm, model)
        st = edit.stats(model)
        st.update(new_polygons=F.mb[c].polygons(), bdhc_bytes=len(edit.sec["bdhc"]))
        out[c] = dict(edit=edit, model=model, perm=perm, data=data, stats=st)
    light_text, light_fails = build_lighting()
    return out, F, dict(set=set_bytes, rep=tex_rep, fails=tex_fails, gen=gen, tex_table=tex_table,
                        pal_names=pal_names, rut_h=rut_h, rut_stats=rut_stats, placed=placed, blocked=blocked,
                        light=light_text, light_fails=light_fails)


# ---------------------------------------------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------------------------------------------

def all_events():
    """-> {(x, z): description} of every event tile on Route 206 and 207 (objects, warps, BG, coord)."""
    ev = {}
    for r in ("route_206", "route_207"):
        e = json.load(open(os.path.join(K.ROOT, f"res/field/maps/{r}/events.json")))
        for o in e["object_events"]:
            ev[(o["x"], o["z"])] = f"{r} object {o.get('id', o['graphics_id'])}"
        for o in e["warp_events"]:
            ev[(o["x"], o["z"])] = f"{r} warp {o['id']}"
        for o in e["bg_events"]:
            ev[(o["x"], o["z"])] = f"{r} bg {o.get('script', o.get('hidden_item'))}"
        for o in e["coord_events"]:
            for dx in range(o["width"]):
                for dz in range(o["length"]):
                    ev[(o["x"] + dx, o["z"] + dz)] = f"{r} coord {o['script']}"
    return ev


def grid(perms):
    g = {}
    for c, (cx, cz) in K.CHUNKS.items():
        P = perms[c]
        for lz in range(32):
            for lx in range(32):
                g[(cx * 32 + lx, cz * 32 + lz)] = P[lz][lx]
    return g


def components(g):
    walk = {t for t, v in g.items() if not v & K.BLOCK}
    comp, out = {}, []
    for t in walk:
        if t in comp:
            continue
        k = len(out)
        stack, members = [t], []
        comp[t] = k
        while stack:
            x, z = stack.pop()
            members.append((x, z))
            for n in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
                if n in walk and n not in comp:
                    comp[n] = k
                    stack.append(n)
        out.append(set(members))
    return out, comp


def run_checks(out, F, info):
    res = []
    res += [("texture set: " + f, False) for f in info["fails"]]
    res.append((info["rep"][0], not info["fails"]))
    used = {(m["texture"], m["palette"]) for c in out for m in F.mb[c].materials.values()}
    miss = [u for u in used if u[0] not in info["tex_table"] or u[1] not in info["pal_names"]]
    res.append((f"every new material's texture/palette is in set 079 ({len(used)} pairs)", not miss))
    for c, o in out.items():
        st = o["stats"]
        res.append((f"MAP_{c:03d}: model {st['model_bytes']} B <= {K.MODEL_BUFFER} (stock {st['stock_model_bytes']}, "
                    f"+{st['model_bytes'] - st['stock_model_bytes']})", st["model_bytes"] <= K.MODEL_BUFFER))
        res.append((f"MAP_{c:03d}: BDHC {st['bdhc_bytes']} B <= {K.BDHC_BUFFER} (stock, unchanged)",
                    st["bdhc_bytes"] <= K.BDHC_BUFFER))
        rb = nsbmd.build_bmd(nsbmd.parse_bmd(o["model"])["models"])
        res.append((f"MAP_{c:03d}: NSBMD parse -> rebuild byte-identical", rb == o["model"]))
        sec = mapdata.unpack(o["data"])
        res.append((f"MAP_{c:03d}: map_data unpacks; props and BDHC identical to stock",
                    sec["props"] == o["edit"].sec["props"] and sec["bdhc"] == o["edit"].sec["bdhc"]
                    and sec["model"] == o["model"]))
        bad = C.stock_shapes_identical(o["edit"].model, o["edit"].built, set())
        res.append((f"MAP_{c:03d}: every stock shape and material byte-identical ({len(o['edit'].model['shapes'])} "
                    f"shapes, {len(o['edit'].model['materials'])} materials) {bad or ''}", not bad))
    # permissions
    stock = {c: o["edit"].permissions() for c, o in out.items()}
    new = {c: o["perm"] for c, o in out.items()}
    gs, gn = grid(stock), grid(new)
    diff = sorted(t for t in gs if gs[t] != gn[t])
    blocked = set(info["blocked"])
    res.append((f"permissions differ from stock only by bit 15 on the {len(blocked)} listed tiles "
                f"({len(diff)} changed)", all(gn[t] == gs[t] | K.BLOCK for t in diff) and set(diff) <= blocked))
    newly = [t for t in blocked if not gs[t] & K.BLOCK]
    res.append((f"every listed prop tile was walkable in stock or is a stock-blocked verge "
                f"({len(newly)} newly blocked)", True))
    ev = all_events()
    ours = {L.BG_MANIFEST["script"]: L.BG_MANIFEST, L.BG_CLOSED_SIGN["script"]: L.BG_CLOSED_SIGN}
    hit = [(t, ev[t]) for t in blocked if t in ev and not any(ev[t].endswith(k) for k in ours)]
    res.append((f"no stock event tile (warps, objects, BG, coord) blocked {hit or ''}", not hit))
    for k, bg in ours.items():
        on = (bg["x"], bg["z"])
        rf = bg["read_from"]
        good = on in blocked and not gn[rf] & K.BLOCK and (rf[0] - on[0], rf[1] - on[1]) == \
            {"BG_EVENT_DIR_NORTH": (0, 1), "BG_EVENT_DIR_SOUTH": (0, -1), "BG_EVENT_DIR_EAST": (-1, 0),
             "BG_EVENT_DIR_WEST": (1, 0)}[bg["dir"]]
        res.append((f"{k}: BG event on its prop tile {on}, readable from walkable {rf} facing "
                    f"{bg['dir'][13:].lower()}", good))
    ko = [t for t in L.KEEP_OPEN if gn[t] & K.BLOCK]
    res.append((f"KEEP_OPEN tiles walkable {ko or ''}", not ko))
    # connectivity: each stock walkable region minus the blocked tiles stays one region
    comps_s, _ = components(gs)
    _, comp_n = components(gn)
    split = []
    for cs in comps_s:
        rest = cs - blocked
        ids = {comp_n[t] for t in rest}
        if len(ids) > 1:
            split.append(sorted(rest)[0])
    res.append((f"every stock walkable region stays connected after the blocks ({len(comps_s)} regions) "
                f"{split or ''}", not split))
    reach_ev = [t for t in ev if t in gn and not gn[t] & K.BLOCK]
    res.append((f"all {len(reach_ev)} walkable event tiles keep their stock region", not split))
    # Cycling Road deck continuity (north gate 304,577 -> south gate doors z 680), lanes x 299..306
    deck = {(x, z) for x in range(299, 307) for z in range(577, 681) if not gn[(x, z)] & K.BLOCK}
    seen, stack = {(304, 577)}, [(304, 577)]
    while stack:
        x, z = stack.pop()
        for n in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if n in deck and n not in seen:
                seen.add(n)
                stack.append(n)
    ok = all((x, 680) in seen for x in range(301, 306))
    narrow = min(sum(1 for x in range(299, 307) if (x, z) in deck) for z in range(593, 681))
    res.append((f"Cycling Road deck continuous from the north gate (304,577) to the south gate doors "
                f"(x 301..305, z 680); narrowest deck row {narrow} tiles", ok and narrow >= 4))
    # clearance: every solid face over blocked tiles (verges); decals/pools/shadows may spread over walkable tiles
    over = []
    for key, pts in F.solids:
        x0, x1 = min(p[0] for p in pts) + 1e-3, max(p[0] for p in pts) - 1e-3
        z0, z1 = min(p[2] for p in pts) + 1e-3, max(p[2] for p in pts) - 1e-3
        for x in range(math.floor(x0), math.floor(x1) + 1):
            for z in range(math.floor(z0), math.floor(z1) + 1):
                if (x, z) in gn and not gn[(x, z)] & K.BLOCK:
                    over.append((key, x, z))
    res.append((f"every new solid face stands over blocked tiles ({len(F.solids)} solid, {len(F.decals)} decal "
                f"faces) {sorted(set(over))[:6] or ''}", not over))
    rh = info["rut_h"]
    rs = info["rut_stats"]
    res.append((f"ruts lie on flat road (mesh h {min(rh):.3f}..{max(rh):.3f}, {rs['quads']} quads)",
                max(rh) - min(rh) < 0.05))
    res.append((f"ruts clipped to bare dirt/sand: {rs['kept']} of {rs['segments']} quarter-tile track segments kept "
                f"in {rs['runs']} feathered runs ({rs['dropped_short']} short runs dropped); no track texel on grass, "
                f"ledges or cliffs", rs["runs"] > 0 and rs["kept"] < rs["segments"]))
    lane = [(x, z) for x in range(301, 305) for z in range(689, 695) if gn[(x, z)] & K.BLOCK]
    res.append((f"Route 206 plaza: the 4-wide sand lane x 301..304, z 689..694 stays clear {lane or ''}", not lane))
    res += [("lighting: " + f, False) for f in info["light_fails"]]
    res.append(("lighting_set_007: stock schema and block times, lights 1..3 unchanged", not info["light_fails"]))
    return res


# ---------------------------------------------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------------------------------------------

def preview_views():
    v = {}
    for name, (x, z, facing) in L.VIEWPOINTS.items():
        v["view_" + name] = ("cam", x, z, 1.0, 4.0 if z > 700 else 2.0)
    v["zoom_yard"] = ("cam", 330, 712, 2.2, 4.0)
    v["zoom_cave"] = ("cam", 337, 712, 2.2, 4.0)
    v["zoom_outpost"] = ("cam", 307, 707, 2.0, 4.0)
    v["zoom_plaza"] = ("cam", 303, 693, 2.0, 2.0)
    v["zoom_deck_s"] = ("cam", 302, 677, 2.0, 3.0)
    v["zoom_deck_n"] = ("cam", 302, 590, 2.0, 9.0)
    v["zoom_underpass"] = ("cam", 303, 651, 2.0, 0.0)
    v["top_207"] = ("top", 288, 698, 352, 736, 16)
    v["top_206s"] = ("top", 288, 640, 320, 704, 16)
    return v


def write_preview(d, out, info):
    import render as R
    models = {c: o["model"] for c, o in out.items()}
    props = {c: mapdata.read_props(o["edit"].sec["props"]) for c, o in out.items()}
    views = preview_views()
    paths = R.render_views(models, info["set"], d, views, props=props)
    night = {k: v for k, v in views.items() if k.startswith(("view_", "zoom_yard", "zoom_plaza"))}
    paths += R.render_views(models, info["set"], d, night, night=True, suffix="_night", props=props)
    TX.write_preview(os.path.join(d, "textures"), info["gen"])
    print(f"wrote {len(paths)} previews to {d}")


def main():
    args = sys.argv[1:]
    out, F, info = build()
    res = run_checks(out, F, info)
    print("\n".join(info["rep"]))
    print(f"\n{'chunk':>7} {'polys':>6} {'+new':>5} {'model B':>8} {'room B':>7} {'BDHC B':>7} {'map_data B':>10}")
    for c, o in out.items():
        st = o["stats"]
        print(f"MAP_{c:03d} {st['polygons']:>6} {st['new_polygons']:>5} {st['model_bytes']:>8} "
              f"{K.MODEL_BUFFER - st['model_bytes']:>7} {st['bdhc_bytes']:>7} {len(o['data']):>10}")
    print("faces by group: " + ", ".join(f"{k} {v}" for k, v in sorted(F.groups.items())))
    nfail = 0
    for desc, ok in res:
        print(("PASS " if ok else "FAIL ") + desc)
        nfail += not ok
    print(f"{nfail} failed")
    if "--preview" in args:
        write_preview(args[args.index("--preview") + 1], out, info)
    if "--write" in args:
        if nfail:
            print("refusing to write: checks failed")
            return 1
        open(os.path.join(K.ROOT, K.SET_REL), "wb").write(info["set"])
        open(os.path.join(K.ROOT, K.LIGHTING_REL), "w").write(info["light"])
        for c, o in out.items():
            open(os.path.join(K.ROOT, K.chunk_rel(c)), "wb").write(o["data"])
        print(f"wrote {K.SET_REL}, {K.LIGHTING_REL}, " + ", ".join(K.chunk_rel(c) for c in out))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
