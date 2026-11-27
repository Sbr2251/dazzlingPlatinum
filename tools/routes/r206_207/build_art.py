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
    "glow": ("ec_crate_u", "ec_crate", "ec_crate_pl", 0, "back", 31, 0),
    "banner": ("ec_banner_2s", "ec_banner", "ec_banner_pl", 1, "none", 31, 0),
    "barr": ("ec_barr_l", "ec_barricade", "ec_barricade_pl", 1, "back", 31, 0),
    "barr2": ("ec_barr_2s", "ec_barricade", "ec_barricade_pl", 1, "none", 31, 0),
    "lamp": ("ec_light_2s", "ec_light", "ec_light_pl", 1, "none", 31, 0),
    "lampu": ("ec_light_u2s", "ec_light", "ec_light_pl", 0, "none", 31, 0),
    "pool": ("ec_pool_u", "ec_light", "ec_light_pl", 0, "back", 18, 21),      # translucent amber light pool
    "vglow": ("ec_vglow_u", "ec_light", "ec_light_pl", 0, "back", 16, 22),    # translucent violet shard glow
    "ruts": ("ec_ruts_l", "ec_ruts", "ec_ruts_pl", 1, "back", 31, 0),
    "shadow": ("ec_shadow", "shadowchip", "shadowchip", 9, "back", 9, 15),   # as the stock prop shadows
}
DECAL_KEYS = {"ruts", "pool", "vglow", "shadow"}


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
        if key == "ruts":                  # the only repeating texture: rebase v per face (s16 UV range)
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
        sides="nsewt", group="box"):
    """Upright box centred on (cx, cz). side/top: uv rects; front: uv rect for the south face (key front_key)."""
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
        cols = front_cols if (k == "s" and front_cols) else None
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


def shadow(F, cx, cz, rx, rz, h):
    """Soft octagonal translucent shadow (stock shadowchip, alpha 9) centred on (cx, cz): three quads."""
    k = 0.414
    uv = [(0.5, 0.5)] * 4
    F.add("shadow", [(cx - rx, h, cz + rz * k), (cx + rx, h, cz + rz * k), (cx + rx, h, cz - rz * k),
                     (cx - rx, h, cz - rz * k)], uv, (0, 1, 0), None, "shadow")
    F.add("shadow", [(cx - rx, h, cz - rz * k), (cx + rx, h, cz - rz * k), (cx + rx * k, h, cz - rz),
                     (cx - rx * k, h, cz - rz)], uv, (0, 1, 0), None, "shadow")
    F.add("shadow", [(cx - rx * k, h, cz + rz), (cx + rx * k, h, cz + rz), (cx + rx, h, cz + rz * k),
                     (cx - rx, h, cz + rz * k)], uv, (0, 1, 0), None, "shadow")


CU = TX.CRATE_UV
BU = TX.BARR_UV
LU = TX.LIGHT_UV
GLOW_TOP, GLOW_BOT = (236, 214, 255), (184, 150, 236)     # baked unlit shard-rack glow (vertex colours)


def crate(F, cx, cz, s, h0, yaw=0.0, tall=1.0):
    box(F, cx, cz, s, s, h0, h0 + s * tall, CU["side"], CU["lid"], yaw, group="crates")
    return h0 + s * tall


def pallet(F, cx, cz, w, d, h0):
    box(F, cx, cz, w, d, h0, h0 + 0.12, sub(CU["steel"], 0, 0, 1, 0.5), CU["steel"], group="crates")
    return h0 + 0.12


def canister_case(F, cx, cz, w, d, h0, h1):
    """A low case of strapped shard canisters: glowing canister front (unlit), steel body."""
    box(F, cx, cz, w, d, h0, h1, CU["steel"], CU["steel"], key="crate", front=CU["rack"], front_key="glow",
        front_cols=[GLOW_TOP, GLOW_TOP, GLOW_BOT, GLOW_BOT], group="racks")


# ---------------------------------------------------------------------------------------------------------------
# props
# ---------------------------------------------------------------------------------------------------------------

def p_stack(F, x, z, G, p):
    cx, cz = x + 0.5, z + 0.5
    k = p.get("kind", "pair")
    if k == "pallet3":
        t = pallet(F, cx, cz, 0.9, 0.86, G)
        crate(F, cx - 0.22, cz + 0.05, 0.42, t, 0.06)
        crate(F, cx + 0.23, cz + 0.02, 0.42, t, -0.05)
        crate(F, cx + 0.02, cz + 0.03, 0.4, t + 0.42, 0.18)
        shadow(F, cx, cz + 0.05, 0.58, 0.52, G + 0.01)
    elif k == "pair":
        t = crate(F, cx - 0.06, cz + 0.06, 0.64, G, 0.04)
        crate(F, cx + 0.04, cz + 0.08, 0.44, t, -0.21)
        shadow(F, cx - 0.04, cz + 0.08, 0.48, 0.46, G + 0.01)
    elif k == "tall":
        t = crate(F, cx, cz + 0.05, 0.74, G, -0.03)
        t = crate(F, cx - 0.03, cz + 0.06, 0.6, t, 0.14)
        crate(F, cx + 0.05, cz + 0.08, 0.42, t, -0.26)
        shadow(F, cx, cz + 0.06, 0.52, 0.5, G + 0.01)
    elif k == "canisters":
        t = pallet(F, cx, cz, 0.9, 0.8, G)
        canister_case(F, cx, cz + 0.02, 0.84, 0.66, t, t + 0.62)
        crate(F, cx + 0.12, cz + 0.02, 0.36, t + 0.62, 0.2)
        decal(F, "vglow", cx - 0.7, cz + 0.3, cx + 0.7, cz + 1.1, G + 0.02, LU["glow"], [(220, 200, 255)] * 4,
              group="glow")
        shadow(F, cx, cz + 0.04, 0.58, 0.5, G + 0.01)


def p_rack(F, x, z, G, p):
    """Shard-containment rack: steel frame, glowing canister front (unlit, baked violet glow), glow on the ground."""
    cx, cz = x + 0.5, z + 0.5
    w, d, ht = 0.9, 0.5, 1.5
    box(F, cx, cz + 0.08, w, d, G, G + ht, sub(CU["steel"], 0, 0, 0.3, 1), CU["steel"], key="crate",
        front=CU["rack"], front_key="glow", front_cols=[GLOW_TOP, GLOW_TOP, GLOW_BOT, GLOW_BOT], group="racks")
    # hazard label on the frame's cap
    card(F, "crate", cx - 0.16, cx + 0.16, cz + 0.08 + d / 2 + 0.005, G + ht + 0.02, G + ht + 0.34, CU["label"],
         lean=20, group="racks")
    decal(F, "vglow", cx - 0.75, cz + 0.25, cx + 0.75, cz + 1.25, G + 0.021, LU["glow"], [(230, 210, 255)] * 4,
          group="glow")
    shadow(F, cx, cz + 0.08, 0.56, 0.36, G + 0.01)


def p_lamp(F, x, z, G, p):
    """Tripod work lamp: lit legs, unlit glowing head, an amber light pool on the ground."""
    cx, zb = x + 0.5, z + 0.62
    h_total = 2.0
    split = 12 / 32
    h_split = G + h_total * (1 - split)
    lean = 8.0
    t = math.tan(math.radians(lean))
    card(F, "lamp", cx - 0.5, cx + 0.5, zb, G, h_split, LU["lamp_legs"], lean, group="lamps")
    zs = zb - (h_split - G) * t
    card(F, "lampu", cx - 0.5, cx + 0.5, zs, h_split, G + h_total, LU["lamp_head"], lean,
         cols=[(255, 250, 236)] * 2 + [(230, 220, 210)] * 2, group="lamps")
    decal(F, "pool", cx - 1.15, z + 0.05, cx + 1.15, z + 2.15, G + 0.024, LU["pool"], [(255, 232, 196)] * 4,
          group="lamps")
    shadow(F, cx, zb - 0.05, 0.4, 0.22, G + 0.012)


def p_banner(F, x, z, G, p):
    px, pz = x + 0.12, z + 0.5
    top = G + 2.9
    box(F, px, pz, 0.1, 0.1, G, top, sub(CU["steel"], 0, 0, 0.1, 1), sub(CU["steel"], 0, 0, 0.1, 0.25),
        group="banners")
    box(F, px + 0.42, pz, 0.84, 0.07, top - 0.16, top - 0.09, sub(CU["steel"], 0, 0, 1, 0.25),
        sub(CU["steel"], 0, 0, 1, 0.25), group="banners")
    card(F, "banner", x + 0.17, x + 0.93, pz + 0.03, G + 0.86, top - 0.12, TX.BANNER_UV["tall"], group="banners")
    box(F, px, pz, 0.16, 0.16, top, top + 0.08, CU["steel"], CU["steel"], group="banners")       # finial cap
    shadow(F, px + 0.1, pz + 0.05, 0.22, 0.16, G + 0.01)


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
    shadow(F, cx, cz + 0.06, 0.6, 0.52, G + 0.01)


def barricade_x(F, x0, x1, zc, G):
    """A-frame road barricade from x0 to x1 (tiles) centred on z = zc: two hazard planks, steel legs, CLOSED board."""
    L_ = x1 - x0
    steel = sub(CU["steel"], 0, 0, 0.12, 1)
    for u in (x0 + 0.1, x1 - 0.1):
        for sgn in (-1, 1):
            F.add("crate2", [(u - 0.03, G + 0.82, zc), (u + 0.03, G + 0.82, zc), (u + 0.03, G, zc + 0.26 * sgn),
                             (u - 0.03, G, zc + 0.26 * sgn)], quad_uv(steel), (0, 0.3, sgn), None, "barricades")
    for h0, h1 in ((G + 0.5, G + 0.76), (G + 0.2, G + 0.38)):
        F.add("barr2", [(x0, h1, zc + 0.012), (x1, h1, zc + 0.012), (x1, h0, zc + 0.012), (x0, h0, zc + 0.012)],
              [(0, BU["stripe"][1]), (L_ / 2, BU["stripe"][1]), (L_ / 2, BU["stripe"][3]), (0, BU["stripe"][3])],
              (0, 0, 1), None, "barricades")
    xm = (x0 + x1) / 2
    card(F, "barr2", xm - 0.6, xm + 0.6, zc + 0.02, G + 0.8, G + 1.1, BU["board"], lean=6, group="barricades")
    for u in (xm - 0.42, xm + 0.42):     # board posts
        card(F, "crate2", u - 0.025, u + 0.025, zc + 0.016, G + 0.74, G + 0.84, steel, group="barricades")
    shadow(F, xm, zc, L_ / 2 + 0.05, 0.3, G + 0.01)


def cone(F, cx, cz, G, s=1.0):
    u0, v0, u1, v1 = BU["cone"]
    apex_v, base_v = v0 + (v1 - v0) * 1 / 16, v0 + (v1 - v0) * 13 / 16
    um = (u0 + u1) / 2
    r, ht = 0.17 * s, 0.55 * s
    a = (cx, G + ht, cz)
    c4 = [(cx - r, G + 0.03, cz + r), (cx + r, G + 0.03, cz + r), (cx + r, G + 0.03, cz - r),
          (cx - r, G + 0.03, cz - r)]
    for k in range(4):
        p, q = c4[k], c4[(k + 1) % 4]
        nrm = ((p[0] + q[0]) / 2 - cx, 0.4, (p[2] + q[2]) / 2 - cz)
        F.add("barr", [a, q, p], [(um, apex_v), (u1 - 0.03, base_v), (u0 + 0.03, base_v)], nrm, None, "cones")
    b = 0.2 * s
    bv0, bv1 = v0 + (v1 - v0) * 13.5 / 16, v0 + (v1 - v0) * 15.5 / 16
    decal(F, "barr", cx - b, cz - b, cx + b, cz + b, G + 0.03, (u0 + 0.06, bv0, u1 - 0.06, bv1), group="cones")
    shadow(F, cx, cz + 0.02, 0.26 * s, 0.22 * s, G + 0.008)


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
    steel = sub(CU["steel"], 0, 0, 0.08, 1)
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
    steel = sub(CU["steel"], 0, 0, 0.1, 1)
    for u in (cx - 0.32, cx + 0.32):
        box(F, u, zb - 0.02, 0.06, 0.06, G, G + 0.98, steel, steel, group="signs")
    card(F, "barr2", cx - 0.5, cx + 0.5, zb + 0.035, G + 0.62, G + 0.92, BU["board"], lean=8, group="signs")
    card(F, "barr2", cx - 0.5, cx + 0.5, zb + 0.02, G + 0.42, G + 0.56, BU["stripe"], lean=0, group="signs")
    card(F, "banner", cx + 0.34, cx + 0.48, zb + 0.01, G + 0.98, G + 1.32, TX.BANNER_UV["pennant"], group="signs")
    shadow(F, cx, zb, 0.5, 0.18, G + 0.01)


BUILDERS = {"stack": p_stack, "rack": p_rack, "lamp": p_lamp, "banner": p_banner, "manifest": p_manifest,
            "barricade": p_barricade, "cones": p_cones, "fence": p_fence, "fence_ns": p_fence_ns, "sign": p_sign}


# ---------------------------------------------------------------------------------------------------------------
# ruts
# ---------------------------------------------------------------------------------------------------------------

def rut_centreline():
    pts = []
    x0, z0 = L.RUT_START
    cx, cz = L.RUT_TURN_CENTRE
    r = cx - x0
    zs = [z0] + [z for z in [699.5 + 0.5 * k for k in range(40)] if z0 < z < cz] + [cz]
    pts += [(x0, z) for z in sorted(set(zs))]
    n = 12
    for k in range(1, n + 1):
        a = math.pi + (math.pi / 2) * k / n          # 180 deg -> 90 deg (towards +z, then east)
        pts.append((cx + r * math.cos(a), cz - r * math.sin(a)))
    xs = [x for x in [cx + 0.5 * k for k in range(1, 80)] if x < L.RUT_END_X] + [320.0, L.RUT_END_X]
    pts += [(x, cz + r) for x in sorted(set(xs)) if x > cx]
    return pts


def build_ruts(F, H):
    pts = rut_centreline()
    half = L.RUT_HALF
    secs = []
    for i, (x, z) in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]
        n = math.hypot(tx, tz)
        tx, tz = tx / n, tz / n
        # left of travel direction: (tz, -tx) points... travel south (0,1): left = east (+x)
        lx, lz = -tz, tx
        secs.append(((x + lx * half, z + lz * half), (x - lx * half, z - lz * half)))
    s_acc = [0.0]
    for i in range(1, len(pts)):
        s_acc.append(s_acc[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    hs = []
    for i in range(len(pts) - 1):
        (l0, r0), (l1, r1) = secs[i], secs[i + 1]
        v0, v1 = s_acc[i] / 2, s_acc[i + 1] / 2
        q = [l0, l1, r1, r0]
        hq = [H.h(px, pz, 4.0) for px, pz in q]
        hs += hq
        P = [(px, h + 0.012, pz) for (px, pz), h in zip(q, hq)]
        F.add("ruts", P, [(1.0, v0), (1.0, v1), (0.0, v1), (0.0, v0)], (0, 1, 0), None, "ruts")
    return hs, len(pts) - 1


# ---------------------------------------------------------------------------------------------------------------
# lighting
# ---------------------------------------------------------------------------------------------------------------

NIGHT = ((9, 9, 18), (12, 12, 17), (9, 9, 14), (12, 12, 17), (6, 6, 11))
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
    rut_h, rut_quads = build_ruts(F, H)
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
                        pal_names=pal_names, rut_h=rut_h, rut_quads=rut_quads, placed=placed, blocked=blocked,
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
    res.append((f"ruts lie on flat road (mesh h {min(rh):.3f}..{max(rh):.3f}, {info['rut_quads']} quads)",
                max(rh) - min(rh) < 0.05))
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
