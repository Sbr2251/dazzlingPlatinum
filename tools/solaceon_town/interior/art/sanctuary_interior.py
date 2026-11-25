#!/usr/bin/env python3
"""Authors the Sanctuary hall interior as Python geometry (standard library only; no Blender needed).

Usage: python3 tools/solaceon_town/interior/art/sanctuary_interior.py
Writes tools/solaceon_town/interior/assets/sanctuary.mesh.json (PLAN.md mesh format: absolute tiles (x, h, z),
uvs in texture units with v in image space, baked vertex colours) and assets/textures/<name>.png + .json
(painted by sanctuary_textures.py). Deterministic: re-running gives identical files.

How it follows the stock interiors (Foreign Building map_data_244, News Press 313, Galactic 333):
  * unlit materials (lights 0) with baked vertex colours, averaging about 0.65 like stock; warm candle light,
    a faint cold violet glow around the emblem, cool daylight at the door;
  * the drawn floor at h -1.125 (1/8 tile under the collision plate), rugs at h -1.0;
  * wall faces 3/8 tile into the wall row (z 6.625), wainscot + plaster, the hall's north wall 7 tiles tall (as the
    Foreign Building's), the office walls 3.5 tiles; wall tops black; nothing drawn on the open south edges or the
    outer sides (black, the clear colour), so no wall top ever hides a walkable tile;
  * only faces the fixed orthographic camera can see: tops and south-facing fronts (east/west faces are exactly
    edge-on to it, north-facing faces are culled);
  * furniture is terrain; the exit mat is the stock prop 78 (placed by build_interior.py).
"""
import json
import math
import os
import sys

import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "lake_verity"))
sys.path.insert(0, HERE)

import png  # noqa: E402
import sanctuary_textures  # noqa: E402

# the tile contract, loaded under its own name (tools/lake_verity has a different layout.py)
_spec = importlib.util.spec_from_file_location("sanctuary_layout", os.path.join(HERE, "..", "layout.py"))
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

ASSETS = os.path.join(HERE, "..", "assets")
TEXDIR = os.path.join(ASSETS, "textures")

FLOOR = L.DRAWN_FLOOR_H       # -1.125
RUG = -1.0
WALL_Z = L.NORTH_WALL_Z + 0.625
HALL_TOP = FLOOR + 7.0        # 5.875
OFFICE_TOP = FLOOR + 3.5      # 2.375
WAIN = FLOOR + 1.0            # top of the wainscot
DECAL = 0.03                  # decals stand this far in front of their wall
SOUTH = (0.0, 0.0, 1.0)
UP = (0.0, 1.0, 0.0)


# ------------------------------------------------------------------------------------------------ baked light
# (position (x, h, z), colour, radius in tiles, strength)
LIGHTS = []


def _add_light(p, rgb, r, s):
    LIGHTS.append((p, rgb, r, s))


CANDLE = (255, 168, 92)
for cx in (3.9, 6.1):                              # the candle ledges under the photo boards (and mirrored)
    _add_light((cx, 0.35, 6.95), CANDLE, 2.8, 0.42)
    _add_light((21.0 - cx, 0.35, 6.95), CANDLE, 2.8, 0.42)
for cx in (8.5, 12.5):                             # candelabra
    _add_light((cx, 0.85, 9.5), CANDLE, 4.4, 0.62)
_add_light((2.5, 0.9, 6.9), CANDLE, 3.0, 0.5)      # wall sconce
_add_light((10.5, 3.1, 7.4), (112, 78, 214), 6.2, 0.36)    # the emblem's cold glow
_add_light((10.5, 1.2, 21.0), (196, 208, 232), 5.5, 0.34)  # daylight at the door
_add_light((23.75, -0.1, 10.45), CANDLE, 4.6, 0.85)          # Indra's desk lamp
_add_light((19.0, 0.4, 13.6), CANDLE, 2.5, 0.18)           # hall light spilling through the doorway

AMB_HALL = (162, 148, 132)
AMB_OFFICE = (140, 134, 128)


def shade(p, n, gain=1.0, ao=1.0):
    x, h, z = p
    office = x > L.INNER_WALL_X + 0.5 and z < L.OFFICE[3] + 1.0
    col = list(AMB_OFFICE if office else AMB_HALL)
    for (lx, lh, lz), rgb, r, s in LIGHTS:
        if office != (lx > L.INNER_WALL_X + 0.5 and lz < L.OFFICE[3] + 1.0) and abs(lx - 19.0) > 0.01:
            continue      # the inner wall stops light between the rooms (except the doorway spill)
        d = math.dist((x, h, z), (lx, lh, lz))
        if d >= r:
            continue
        f = (1 - d / r) ** 2 * s
        if d > 1e-6:
            ndl = (n[0] * (lx - x) + n[1] * (lh - h) + n[2] * (lz - z)) / d
            f *= 0.3 + 0.7 * max(0.0, ndl)
        for i in range(3):
            col[i] += rgb[i] * f
    return [max(0, min(255, int(round(c * gain * ao)))) for c in col]


def floor_ao(x, z):
    """Darker towards the north wall and around the furniture footprints (the 4 tiles touching the vertex)."""
    a = 0.8 + 0.2 * min(1.0, max(0.0, (z - WALL_Z) / 1.3))
    for tx in {math.floor(x - 0.01), math.floor(x + 0.01)}:
        for tz in {math.floor(z - 0.01), math.floor(z + 0.01)}:
            if (tx, tz) in L.FURNITURE and (tx, tz) != L.LECTERN:
                a *= 0.93
    return a


# ------------------------------------------------------------------------------------------------ mesh builder
class Mesh:
    def __init__(self):
        self.materials = {}
        self.meshes = {}

    def material(self, name, texture, cull="back", polygon_id=0):
        self.materials[name] = {"name": name, "texture": texture, "alpha": 31,
                                "polygon_attr": {"cull": cull, "lights": 0, "polygon_id": polygon_id}}
        self.meshes[name] = {"material": name, "positions": [], "uvs": [], "colors": [], "tris": [], "quads": []}

    def quad(self, mat, pts, uvs, cols, normal):
        """pts: 4 corners (x, h, z); flips the winding if needed so the face is drawn on the `normal` side."""
        a, b, c = pts[0], pts[1], pts[2]
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        cr = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        if sum(cr[i] * normal[i] for i in range(3)) < 0:
            pts, uvs, cols = pts[::-1], uvs[::-1], cols[::-1]
        m = self.meshes[mat]
        k = len(m["positions"])
        m["positions"] += [[round(p[0], 4), round(p[1], 4), round(p[2], 4)] for p in pts]
        m["uvs"] += [[round(t[0], 5), round(t[1], 5)] for t in uvs]
        m["colors"] += [list(c) for c in cols]
        m["quads"].append([k, k + 1, k + 2, k + 3])

    # -- surfaces
    def floor(self, mat, x0, x1, z0, z1, h, step=1.0, scale=1.0, ao=True, gain=1.0):
        xs = _cuts(x0, x1, step)
        zs = _cuts(z0, z1, step)
        for i in range(len(xs) - 1):
            for j in range(len(zs) - 1):
                xa, xb, za, zb = xs[i], xs[i + 1], zs[j], zs[j + 1]
                pts = [(xa, h, za), (xa, h, zb), (xb, h, zb), (xb, h, za)]
                ox, oz = math.floor(xa * scale), math.floor(za * scale)
                uvs = [((p[0] * scale - ox), (p[2] * scale - oz)) for p in pts]
                cols = [shade(p, UP, gain, floor_ao(p[0], p[2]) if ao else 1.0) for p in pts]
                self.quad(mat, pts, uvs, cols, UP)

    def front(self, mat, x0, x1, h0, h1, z, u_per_tile=1.0, v_tiles=1.0, v_top=None, stepx=1.0, steph=1.0,
              gain=1.0, uv=None, flat=None):
        """South-facing rectangle at z. Texture repeats every 1/u_per_tile tiles across and v_tiles tiles down,
        anchored at x 0 and h v_top (default h1). uv=(u0, u1, v0, v1) maps the whole rectangle instead."""
        v_top = h1 if v_top is None else v_top
        xs = _cuts(x0, x1, stepx)
        hs = _cuts(h0, h1, steph)
        for i in range(len(xs) - 1):
            for j in range(len(hs) - 1):
                xa, xb, ha, hb = xs[i], xs[i + 1], hs[j], hs[j + 1]
                pts = [(xa, ha, z), (xb, ha, z), (xb, hb, z), (xa, hb, z)]
                if uv:
                    u0, u1, v0, v1 = uv
                    uvs = [(u0 + (p[0] - x0) / (x1 - x0) * (u1 - u0), v0 + (h1 - p[1]) / (h1 - h0) * (v1 - v0))
                           for p in pts]
                else:
                    ou = math.floor(xa * u_per_tile)
                    uvs = [(p[0] * u_per_tile - ou, (v_top - p[1]) / v_tiles) for p in pts]
                cols = [list(flat) if flat else shade(p, SOUTH, gain) for p in pts]
                self.quad(mat, pts, uvs, cols, SOUTH)

    def top(self, mat, x0, x1, z0, z1, h, gain=1.0, uv=None, flat=None, stepx=1.0):
        xs = _cuts(x0, x1, stepx)
        for i in range(len(xs) - 1):
            xa, xb = xs[i], xs[i + 1]
            pts = [(xa, h, z0), (xa, h, z1), (xb, h, z1), (xb, h, z0)]
            if uv:
                u0, u1, v0, v1 = uv
                uvs = [(u0 + (p[0] - x0) / (x1 - x0) * (u1 - u0), v0 + (p[2] - z0) / (z1 - z0) * (v1 - v0))
                       for p in pts]
            else:
                ou = math.floor(xa)
                uvs = [(p[0] - ou, (p[2] - z0)) for p in pts]
            cols = [list(flat) if flat else shade(p, UP, gain) for p in pts]
            self.quad(mat, pts, uvs, cols, UP)

    def slope(self, mat, x0, x1, z_lo, h_lo, z_hi, h_hi, uv=(0, 1, 0, 1), gain=1.0):
        """A board rising from (z_lo, h_lo) to (z_hi, h_hi), drawn on its upper side."""
        pts = [(x0, h_hi, z_hi), (x0, h_lo, z_lo), (x1, h_lo, z_lo), (x1, h_hi, z_hi)]
        u0, u1, v0, v1 = uv
        uvs = [(u0, v0), (u0, v1), (u1, v1), (u1, v0)]
        a, b, c = pts[0], pts[1], pts[2]
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        ln = math.sqrt(sum(t * t for t in n))
        n = tuple(t / ln * (1 if n[1] >= 0 else -1) for t in n)
        cols = [shade(p, n, gain) for p in pts]
        self.quad(mat, pts, uvs, cols, n)

    def box(self, top_mat, front_mat, x0, x1, z0, z1, h0, h1, top_gain=1.0, front_gain=1.0, front_uv=None,
            top_uv=None, u_per_tile=1.0, v_tiles=1.0, stepx=1.0):
        self.top(top_mat, x0, x1, z0, z1, h1, gain=top_gain, uv=top_uv, stepx=stepx)
        self.front(front_mat, x0, x1, h0, h1, z1, u_per_tile=u_per_tile, v_tiles=v_tiles, gain=front_gain,
                   uv=front_uv, stepx=stepx, steph=max(1.0, h1 - h0))

    def candle(self, x, z, base_h, wax_h, flame=0.22, w=0.085):
        self.front("sa_wax", x - w / 2, x + w / 2, base_h, base_h + wax_h, z, uv=(0.2, 0.8, 0.1, 0.9),
                   flat=(236, 224, 196))
        fw = flame * 0.55
        self.front("sa_flame", x - fw, x + fw, base_h + wax_h - 0.03, base_h + wax_h - 0.03 + flame, z + 0.005,
                   uv=(0, 1, 0, 1), flat=(255, 255, 255))

    def to_json(self):
        order = sorted(self.meshes)
        return {"name": "solaceon_sanctuary", "origin_tile": [0, 0],
                "materials": [self.materials[k] for k in order],
                "meshes": [self.meshes[k] for k in order if self.meshes[k]["quads"]]}


def _cuts(a, b, step):
    """a, the integer multiples of step strictly between a and b, b."""
    out = [a]
    k = math.floor(a / step) + 1
    while k * step < b - 1e-6:
        if k * step > a + 1e-6:
            out.append(k * step)
        k += 1
    out.append(b)
    return out


# ------------------------------------------------------------------------------------------------ the room
def build():
    m = Mesh()
    for name, tex in (("sa_floor", "sa_floor"), ("sa_planks", "sa_planks"), ("sa_rug", "sa_rug"),
                      ("sa_hem", "sa_hem"), ("sa_plaster", "sa_plaster"), ("sa_wainscot", "sa_wainscot"),
                      ("sa_trim", "sa_trim"), ("sa_wood", "sa_wood"), ("sa_brass", "sa_brass"),
                      ("sa_cards", "sa_cards"), ("sa_emblem", "sa_emblem"), ("sa_window", "sa_window"),
                      ("sa_door", "sa_door"), ("sa_files", "sa_files"), ("sa_box", "sa_box"),
                      ("sa_ledger", "sa_ledger"), ("sa_map", "sa_map"), ("sa_lily", "sa_lily"),
                      ("sa_black", "sa_plaster"), ("sa_wax", "sa_plaster")):
        m.material(name, tex)
    m.material("sa_flame", "sa_flame", cull="none")

    hx0, hz0, hx1, hz1 = L.HALL
    ox0, oz0, ox1, oz1 = L.OFFICE
    # ---- floors
    m.floor("sa_floor", hx0, hx1 + 1, WALL_Z, hz1 + 1, FLOOR, step=2.0)
    m.floor("sa_planks", ox0, ox1 + 1, WALL_Z, oz1 + 1, FLOOR, step=2.0)
    dx, dz = L.DOORWAY
    m.floor("sa_planks", dx, dx + 1, dz - 0.375, dz + 1, FLOOR)

    # ---- the runner and the dais rug (one outline, gold hem 1/4 tile wide)
    rug(m)

    # ---- the hall's north wall
    W = WALL_Z
    m.front("sa_wainscot", hx0, hx1 + 1, FLOOR, WAIN, W, stepx=2.0)
    m.front("sa_plaster", hx0, hx1 + 1, WAIN, HALL_TOP - 0.375, W, v_tiles=2.0, v_top=HALL_TOP - 0.375,
            stepx=2.0, steph=2.0)
    m.front("sa_trim", hx0, hx1 + 1, HALL_TOP - 0.375, HALL_TOP, W, stepx=4.0)
    m.top("sa_black", hx0, hx1 + 1, L.NORTH_WALL_Z, W, HALL_TOP, flat=(0, 0, 0), stepx=8.0)
    # photo-card boards, framed, with an offering ledge of candles below
    for bx0, shift in ((3.0, 0.0), (14.0, 0.5)):
        bx1 = bx0 + 4.0
        m.front("sa_cards", bx0, bx1, 0.0, 2.0, W + DECAL, uv=(shift, shift + 1.0, 0.0, 1.0), stepx=1.0, steph=1.0)
        m.front("sa_trim", bx0 - 0.12, bx1 + 0.12, 2.0, 2.14, W + DECAL, uv=(0, 4.25, 0, 1))
        m.front("sa_wood", bx0 - 0.12, bx0, 0.0, 2.0, W + DECAL, uv=(0, 0.12, 0, 2), steph=1.0)
        m.front("sa_wood", bx1, bx1 + 0.12, 0.0, 2.0, W + DECAL, uv=(0, 0.12, 0, 2), steph=1.0)
        m.box("sa_wood", "sa_trim", bx0 - 0.15, bx1 + 0.15, W, W + 0.34, -0.17, 0.0, front_uv=(0, 4.3, 0.1, 0.6))
    for cx, wax in ((3.35, 0.2), (3.8, 0.13), (4.45, 0.26), (5.3, 0.16), (5.95, 0.22), (6.6, 0.12)):
        m.candle(cx, W + 0.2, 0.0, wax)
        m.candle(21.0 - cx, W + 0.2, 0.0, wax + 0.03)
    # the eclipse
    m.front("sa_emblem", 8.25, 12.75, 0.75, 5.25, W + DECAL + 0.01, uv=(0, 1, 0, 1), stepx=1.5, steph=1.5,
            gain=1.32)
    # high violet windows
    for wx in (4.375, 15.375):
        m.front("sa_window", wx, wx + 1.25, 2.75, 5.0, W + DECAL, uv=(0, 1, 0, 1), stepx=1.25, steph=2.25,
                gain=1.25)
    # the locked back door (18, 6) and the sconce (2, 6)
    m.front("sa_door", 18.1, 18.9, FLOOR, FLOOR + 1.875, W + DECAL, uv=(0, 1, 0, 1), stepx=0.8, steph=1.0)
    m.front("sa_brass", 2.38, 2.62, 0.35, 0.72, W + DECAL, uv=(0, 1, 0, 1))
    m.box("sa_brass", "sa_brass", 2.18, 2.82, W, W + 0.22, 0.66, 0.72, front_uv=(0, 1, 0, 1), top_uv=(0, 1, 0, 1))
    for cx, wax in ((2.28, 0.14), (2.5, 0.2), (2.72, 0.14)):
        m.candle(cx, W + 0.16, 0.72, wax)

    # ---- lectern, candelabra, pews, guest book, vases
    lx, lz = L.LECTERN
    m.box("sa_wood", "sa_wood", lx + 0.12, lx + 0.88, lz + 0.3, lz + 0.8, FLOOR, -0.08)
    m.top("sa_ledger", lx + 0.24, lx + 0.76, lz + 0.36, lz + 0.72, -0.055, uv=(0, 1, 0, 1))
    m.front("sa_emblem", lx + 0.3, lx + 0.7, -0.62, -0.22, lz + 0.8 + DECAL, uv=(0, 1, 0, 1), gain=1.2)
    m.front("sa_trim", lx + 0.12, lx + 0.88, -0.2, -0.08, lz + 0.8 + DECAL, uv=(0, 1, 0, 1))
    for (cx, cz) in L.CANDELABRA:
        x = cx + 0.5
        m.box("sa_brass", "sa_brass", x - 0.22, x + 0.22, cz + 0.32, cz + 0.68, FLOOR, FLOOR + 0.12,
              front_uv=(0, 1, 0, 1), top_uv=(0, 1, 0, 1))
        m.front("sa_brass", x - 0.045, x + 0.045, FLOOR + 0.12, 0.42, cz + 0.5, uv=(0, 1, 0, 1), steph=1.0)
        m.front("sa_brass", x - 0.36, x + 0.36, 0.38, 0.46, cz + 0.5, uv=(0, 1, 0, 1))
        for k, ddx in enumerate((-0.31, 0.0, 0.31)):
            m.candle(x + ddx, cz + 0.52, 0.46, 0.22 if k == 1 else 0.17)
    for z in L.PEW_ROWS:
        for x0, x1 in L.PEW_SPANS:
            pew(m, x0, x1 + 1, z)
    gx, gz = L.GUEST_BOOK
    m.box("sa_wood", "sa_wood", gx + 0.32, gx + 0.68, gz + 0.38, gz + 0.66, FLOOR, -0.36)
    m.slope("sa_ledger", gx + 0.14, gx + 0.86, gz + 0.78, -0.34, gz + 0.26, -0.18)
    for vx, vz in L.VASES:
        m.front("sa_lily", vx + 0.1, vx + 0.9, FLOOR, FLOOR + 1.6, vz + 0.55, uv=(0, 1, 0, 1), steph=0.8,
                gain=1.12)

    # ---- the inner wall (column 19, z 6..12) and its jamb at the doorway
    jz = L.DOORWAY[1] - 0.375
    ix = L.INNER_WALL_X
    m.top("sa_black", ix, ix + 1, L.NORTH_WALL_Z, jz, OFFICE_TOP, flat=(0, 0, 0))
    m.front("sa_wainscot", ix, ix + 1, FLOOR, WAIN, jz)
    m.front("sa_plaster", ix, ix + 1, WAIN, OFFICE_TOP - 0.25, jz, v_tiles=2.0)
    m.front("sa_trim", ix, ix + 1, OFFICE_TOP - 0.25, OFFICE_TOP, jz, uv=(0, 1, 0, 1))
    m.front("sa_brass", ix + 0.28, ix + 0.72, 0.35, 0.62, jz + DECAL, uv=(0, 1, 0, 1))   # "RECORDS" plate

    # ---- the office: north wall, map, shelves, desk, cabinet, card boxes
    m.front("sa_wainscot", ox0, ox1 + 1, FLOOR, WAIN, W, stepx=2.0)
    m.front("sa_plaster", ox0, ox1 + 1, WAIN, OFFICE_TOP - 0.25, W, v_tiles=2.0, stepx=2.0, steph=2.0)
    m.front("sa_trim", ox0, ox1 + 1, OFFICE_TOP - 0.25, OFFICE_TOP, W, stepx=6.0)
    m.top("sa_black", ox0, ox1 + 1, L.NORTH_WALL_Z, W, OFFICE_TOP, flat=(0, 0, 0), stepx=8.0)
    m.front("sa_map", 22.5, 24.5, 1.0, 2.0, W + DECAL, uv=(0, 1, 0, 1), stepx=1.0, gain=1.1)
    for sx0, sx1 in ((20, 23), (24, 26)):
        m.box("sa_wood", "sa_files", sx0 + 0.04, sx1 - 0.04, W + 0.02, L.NORTH_WALL_Z + 1.8, FLOOR, FLOOR + 2.0,
              top_gain=0.55, v_tiles=2.0)
    m.box("sa_wood", "sa_wood", 22.1, 23.9, 10.15, 10.85, FLOOR, -0.4, top_gain=1.12, front_gain=0.62)
    m.top("sa_ledger", 22.2, 22.85, 10.24, 10.76, -0.38, uv=(0, 1, 0, 1))
    m.box("sa_box", "sa_box", 23.18, 23.58, 10.28, 10.62, -0.4, -0.2, front_uv=(0, 1, 0.2, 0.8),
          top_uv=(0, 1, 0, 1))
    m.box("sa_brass", "sa_brass", 23.66, 23.86, 10.3, 10.5, -0.4, -0.36, front_uv=(0, 1, 0, 1), top_uv=(0, 1, 0, 1))
    m.candle(23.76, 10.42, -0.36, 0.14)
    cbx, cbz = L.CABINET
    m.box("sa_wood", "sa_files", cbx + 0.08, cbx + 0.92, cbz + 0.05, cbz + 0.85, FLOOR, 0.5, top_gain=0.6,
          front_uv=(0, 1, 0.5, 1.0))
    for (bx, bz), stack in zip(L.CARD_BOXES, (2, 1, 2)):
        h = FLOOR
        for k in range(stack):
            ins = 0.12 + 0.06 * k
            m.box("sa_box", "sa_box", bx + ins, bx + 1 - ins, bz + 0.18 + 0.04 * k, bz + 0.86 - 0.03 * k, h,
                  h + 0.5, front_uv=(0, 1, 0, 1), top_uv=(0, 1, 0, 1))
            h += 0.5
    return m


def pew(m, x0, x1, z):
    """A pew in tile row z facing north: the seat, the backrest along the south edge, end panels."""
    seat_h = FLOOR + 0.45
    back_h = FLOOR + 0.98
    m.top("sa_wood", x0 + 0.1, x1 - 0.1, z + 0.12, z + 0.62, seat_h, gain=0.9, stepx=2.0)
    m.top("sa_wood", x0 + 0.1, x1 - 0.1, z + 0.62, z + 0.8, back_h, gain=1.08, stepx=2.0)
    m.front("sa_wood", x0 + 0.1, x1 - 0.1, FLOOR, back_h, z + 0.8, v_tiles=1.0, v_top=back_h, stepx=2.0)
    for ex0 in (x0, x1 - 0.12):
        m.box("sa_wood", "sa_wood", ex0, ex0 + 0.12, z + 0.06, z + 0.86, FLOOR, back_h + 0.08, front_gain=0.82,
              front_uv=(0.0, 0.12, 0.0, 1.0), top_uv=(0, 0.12, 0, 0.8))


def rug(m):
    w = 0.25
    body = [(7.75, 13.25, 7.25, 9.75), (9.25, 11.75, 9.75, 18.75)]
    for x0, x1, z0, z1 in body:
        m.floor("sa_rug", x0, x1, z0, z1, RUG, ao=False, step=2.0)
    # hem strips: (x0, x1, z0, z1, outer side) ; v runs 0 at the outer edge to 1 at the inner edge
    hems = [(7.5, 13.5, 7.0, 7.25, "n"), (7.5, 7.75, 7.25, 9.75, "w"), (13.25, 13.5, 7.25, 9.75, "e"),
            (7.5, 9.0, 9.75, 10.0, "s"), (12.0, 13.5, 9.75, 10.0, "s"), (9.0, 9.25, 9.75, 18.75, "w"),
            (11.75, 12.0, 9.75, 18.75, "e"), (9.0, 12.0, 18.75, 19.0, "s")]
    for x0, x1, z0, z1, side in hems:
        pts = [(x0, RUG, z0), (x0, RUG, z1), (x1, RUG, z1), (x1, RUG, z0)]
        if side in "ns":
            n0 = z0 if side == "n" else z1
            uvs = [(p[0] - math.floor(x0), abs(p[2] - n0) / w) for p in pts]
        else:
            n0 = x0 if side == "w" else x1
            uvs = [(p[2] - math.floor(z0), abs(p[0] - n0) / w) for p in pts]
        cols = [shade(p, UP) for p in pts]
        # long strips: split into tiles so the light and the UV range stay local
        if max(x1 - x0, z1 - z0) > 2.01:
            if side in "ns":
                for a in _cuts(x0, x1, 2.0)[:-1]:
                    b = min(x1, math.floor(a / 2) * 2 + 2.0)
                    sub = [(a, RUG, z0), (a, RUG, z1), (b, RUG, z1), (b, RUG, z0)]
                    m.quad("sa_hem", sub, [(p[0] - math.floor(a), abs(p[2] - n0) / w) for p in sub],
                           [shade(p, UP) for p in sub], UP)
            else:
                for a in _cuts(z0, z1, 2.0)[:-1]:
                    b = min(z1, math.floor(a / 2) * 2 + 2.0)
                    sub = [(x0, RUG, a), (x0, RUG, b), (x1, RUG, b), (x1, RUG, a)]
                    m.quad("sa_hem", sub, [(p[2] - math.floor(a), abs(p[0] - n0) / w) for p in sub],
                           [shade(p, UP) for p in sub], UP)
        else:
            m.quad("sa_hem", pts, uvs, cols, UP)


# ------------------------------------------------------------------------------------------------ output
def write_textures():
    os.makedirs(TEXDIR, exist_ok=True)
    for name, (w, h, rows, pal, meta) in sorted(sanctuary_textures.paint_all().items()):
        png.write_indexed(os.path.join(TEXDIR, name + ".png"), w, h, rows, pal, bits=4,
                          transparent0=bool(meta.get("c0")))
        with open(os.path.join(TEXDIR, name + ".json"), "w", newline="\n") as f:
            f.write(json.dumps(meta, indent=1, sort_keys=True) + "\n")


def main():
    write_textures()
    mesh = build().to_json()
    os.makedirs(ASSETS, exist_ok=True)
    with open(os.path.join(ASSETS, "sanctuary.mesh.json"), "w", newline="\n") as f:
        json.dump(mesh, f, separators=(",", ":"))
        f.write("\n")
    n = sum(len(me["quads"]) + len(me["tris"]) for me in mesh["meshes"])
    cols = [c for me in mesh["meshes"] if me["material"] not in ("sa_black", "sa_flame", "sa_wax")
            for c in me["colors"]]
    avg = sum(sum(c) for c in cols) / (3 * 255 * len(cols))
    print(f"sanctuary.mesh.json: {len(mesh['meshes'])} materials, {n} faces; mean vertex colour {avg:.2f} "
          f"(stock interiors ~0.55-0.7); {len(os.listdir(TEXDIR)) // 2} textures")


if __name__ == "__main__":
    main()
