#!/usr/bin/env python3
"""Renders the Solaceon kit through the Platinum field camera, beside stock Solaceon buildings.

Usage: python3 tools/solaceon_town/art/preview_kit.py [--no-render] [--lit] [--views street,hall,...]
  (run tools/solaceon_town/art/decode_stock.py and paint_kit.py first)

Builds a mock street (mesh.json, tiles: x east, h up, z south, ground h 0) and renders it with
tools/lake_verity/blender_preview.py --views game --dscolor (CAMERA_TYPE_ZOOMED_IN, 256x192 x4):
  - stock: the Pokemon Center (build model 4 + its door prop 70) and a Solaceon house (197 + door 246), with their
    stock textures and palettes from Solaceon's building set; stock set 010 ground (ngrass, nsand, nhana) and cliff
    (criffp, dhole); stock nbridge planks on the scaffold deck.
  - kit: a graybox Sanctuary hall (9 x 5 tiles, door at the middle of the south face, 3-tile walls + hip roof, a
    gabled front bay to h 5), its walled compound with gate posts, open gate and forecourt emblem; the memorial plaza
    (benches, lanterns, card board, offerings, candles, garden of names); the registration tent; the excavation
    (scaffold, warning fence, work lights, KEEP OUT board, tarp pile, crates, cable, sandbags); the ranch (kennel
    block, yard).
Every kit texture appears at least once (checked). Outputs to <preview dir>/render/:
  street_top.png            whole mock, straight down, 8 px per tile
  <view>_game.png           field camera on each zone (see VIEWS)
The emblem uses a pre-mirrored 48x48 preview copy of the 24x24 quadrant; the game draws the 3x3 inlay as four quads
with mirrored UVs (tools/solaceon_town/build_art.py build_emblem).
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import nsbmd  # noqa: E402
import png  # noqa: E402

BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
BP = os.path.join(HERE, "blender_cpu.py")        # blender_preview.py on Cycles CPU (EEVEE needs Metal)

VIEWS = {
    "street": (18.5, 8.5),     # stock Pokemon Center beside the Sanctuary hall
    "hall": (25.5, 7.0),        # hall front, forecourt emblem, gate
    "plaza": (8.0, 18.5),       # benches, lanterns, offerings, garden of names
    "tent": (18.0, 17.0),       # registration tent
    "dig": (41.0, 6.5),         # excavation
    "ranch": (35.0, 19.0),      # kennel block, yard
}


class Scene:
    def __init__(self, name):
        self.name = name
        self.materials = {}
        self.meshes = {}

    def mat(self, name, texture=None, alpha=31, repeat=True):
        if name not in self.materials:
            self.materials[name] = {"name": name, "texture": texture or name, "alpha": alpha,
                                    "polygon_attr": {"cull": "none"}, "tex_param": {"repeat_s": repeat}}
        return name

    def quad(self, mat, pts, uvs):
        m = self.meshes.setdefault(mat, {"material": mat, "positions": [], "uvs": [], "quads": [], "tris": []})
        n = len(m["positions"])
        m["positions"] += [list(p) for p in pts]
        m["uvs"] += [list(u) for u in uvs]
        m["quads"].append([n, n + 1, n + 2, n + 3])

    def tri(self, mat, pts, uvs):
        m = self.meshes.setdefault(mat, {"material": mat, "positions": [], "uvs": [], "quads": [], "tris": []})
        n = len(m["positions"])
        m["positions"] += [list(p) for p in pts]
        m["uvs"] += [list(u) for u in uvs]
        m["tris"].append([n, n + 1, n + 2])

    # --- helpers. uv rects are (u0, v0, u1, v1) with v0 at the top of the quad
    def wall(self, mat, x0, z0, x1, z1, h0, h1, uv):
        u0, v0, u1, v1 = uv
        self.quad(mat, [(x0, h0, z0), (x1, h0, z1), (x1, h1, z1), (x0, h1, z0)],
                  [(u0, v1), (u1, v1), (u1, v0), (u0, v0)])

    def floor(self, mat, x0, z0, x1, z1, h, uv):
        u0, v0, u1, v1 = uv
        self.quad(mat, [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)],
                  [(u0, v1), (u1, v1), (u1, v0), (u0, v0)])

    def tiled_floor(self, mat, x0, z0, x1, z1, h, tiles_per_repeat, ox=0.0, oz=0.0):
        t = tiles_per_repeat
        self.floor(mat, x0, z0, x1, z1, h, ((x0 - ox) / t, (z0 - oz) / t, (x1 - ox) / t, (z1 - oz) / t))

    def card(self, mat, x0, x1, z, h0, h1, px, size):
        """Upright quad facing south showing atlas pixels px = (x0, y0, x1, y1) of a texture of size (w, h)."""
        w, h = size
        self.wall(mat, x0, z, x1, z, h0, h1, (px[0] / w, px[1] / h, px[2] / w, px[3] / h))

    def box(self, x0, z0, x1, z1, h0, h1, faces):
        """faces: {"s","n","e","w","top": (mat, uv)}."""
        if "s" in faces:
            self.wall(faces["s"][0], x0, z1, x1, z1, h0, h1, faces["s"][1])
        if "n" in faces:
            self.wall(faces["n"][0], x1, z0, x0, z0, h0, h1, faces["n"][1])
        if "e" in faces:
            self.wall(faces["e"][0], x1, z1, x1, z0, h0, h1, faces["e"][1])
        if "w" in faces:
            self.wall(faces["w"][0], x0, z0, x0, z1, h0, h1, faces["w"][1])
        if "top" in faces:
            self.floor(faces["top"][0], x0, z0, x1, z1, h1, faces["top"][1])

    def save(self, d):
        out = {"name": self.name, "origin_tile": [0, 0], "materials": list(self.materials.values()),
               "meshes": list(self.meshes.values())}
        p = os.path.join(d, self.name + ".mesh.json")
        json.dump(out, open(p, "w"))
        return p


def px(x0, y0, x1, y1, w, h):
    return (x0 / w, y0 / h, x1 / w, y1 / h)


# ---------------------------------------------------------------------------------------------------------------
# kit pieces
# ---------------------------------------------------------------------------------------------------------------

def stone_wall(s, x0, z0, x1, z1, h1, plinth=True):
    """A pale-stone wall face: lilac plinth (htrim band 2) to h 0.5, ashlar above."""
    L = ((x1 - x0) ** 2 + (z1 - z0) ** 2) ** 0.5
    ua = (x0 + z0) / 2
    if plinth:
        s.wall("sol_htrim", x0, z0, x1, z1, 0.0, 0.5, (ua, 16 / 32, ua + L / 2, 24 / 32))
    hb = 0.5 if plinth else 0.0
    s.wall("sol_hwall", x0, z0, x1, z1, hb, h1, (ua, (4.0 - h1) / 2, ua + L / 2, (4.0 - hb) / 2))


def pilaster(s, x0, x1, z, h1):
    A = (64, 64)
    s.card("sol_hatlas", x0, x1, z, h1 - 0.5, h1, (0, 32, 16, 40), A)
    s.card("sol_hatlas", x0, x1, z, 0.5, h1 - 0.5, (0, 40, 16, 56), A)
    s.card("sol_hatlas", x0, x1, z, 0.0, 0.5, (0, 56, 16, 64), A)


WALL_H = 2.5      # hall walls
BAY_H = 3.0       # front bay walls (door 2 tiles + the sign board above it)
APEX_H = 4.75     # bay gable apex
RIDGE_H = 4.0     # hip roof ridge


def hall(s):
    """9 x 5 tiles: x 21..30, z 2.5..7.5; front bay x 23..28 to z 8.0, door x 24.5..26.5 (tile 25 is the warp).
    About 4 tiles tall: walls 2.5, hip ridge 4.0, the bay's gable to 4.75 (the Pokemon Center is 3.9)."""
    A = (64, 64)
    for m in ("sol_hwall", "sol_htrim", "sol_hroof", "sol_hatlas", "sol_steps"):
        s.mat(m)
    W, B = WALL_H, BAY_H
    stone_wall(s, 21, 7.5, 23, 7.5, W)
    stone_wall(s, 28, 7.5, 30, 7.5, W)
    stone_wall(s, 30, 7.5, 30, 2.5, W)
    stone_wall(s, 21, 2.5, 21, 7.5, W)
    stone_wall(s, 23, 8.0, 28, 8.0, B)
    stone_wall(s, 23, 7.5, 23, 8.0, B)
    stone_wall(s, 28, 8.0, 28, 7.5, B)
    # gable over the bay, the eclipse medallion in it
    s.tri("sol_hwall", [(23, B, 8.0), (28, B, 8.0), (25.5, APEX_H, 8.0)], [(0, 0.875), (2.5, 0.875), (1.25, 0)])
    s.card("sol_hatlas", 24.5, 26.5, 8.02, B + 0.05, B + 1.0, (16, 32, 48, 48), A)
    # pilasters, windows (0.8 x 1.55 tiles), door, sign, plaque, step
    for (x0, z, h) in ((21.0, 7.52, W), (29.25, 7.52, W), (23.0, 8.02, B), (27.25, 8.02, B)):
        pilaster(s, x0, x0 + 0.75, z, h)
    for x0 in (22.0, 28.1):
        s.card("sol_hatlas", x0, x0 + 0.8, 7.53, 0.55, 2.1, (32, 0, 48, 32), A)
    for z0 in (3.6, 5.6):
        s.wall("sol_hatlas", 30.02, z0 + 0.8, 30.02, z0, 0.55, 2.1, px(32, 0, 48, 32, 64, 64))
        s.wall("sol_hatlas", 20.98, z0, 20.98, z0 + 0.8, 0.55, 2.1, px(32, 0, 48, 32, 64, 64))
    s.card("sol_hatlas", 24.5, 26.5, 8.03, 0.0, 2.0, (0, 0, 32, 32), A)
    s.card("sol_hatlas", 24.5, 26.5, 8.03, 2.05, 2.95, (16, 48, 48, 64), A)
    s.card("sol_hatlas", 23.8, 24.4, 8.03, 0.9, 1.5, (48, 16, 64, 32), A)
    s.floor("sol_steps", 24.25, 8.0, 26.75, 8.4, 0.2, (0, 0, 1.25, 4 / 32))
    s.wall("sol_steps", 24.25, 8.4, 26.75, 8.4, 0.0, 0.2, (0, 4 / 32, 1.25, 8 / 32))
    # eave fascia (htrim band 1) under the roof edge
    s.wall("sol_htrim", 20.6, 7.9, 30.4, 7.9, W - 0.4, W + 0.1, (0, 8 / 32, 4.9, 16 / 32))
    s.wall("sol_htrim", 30.4, 7.9, 30.4, 2.1, W - 0.4, W + 0.1, (0, 8 / 32, 2.9, 16 / 32))
    s.wall("sol_htrim", 20.6, 2.1, 20.6, 7.9, W - 0.4, W + 0.1, (0, 8 / 32, 2.9, 16 / 32))
    # hip roof: eaves x 20.6..30.4, z 2.1..7.9 at h W; ridge x 23.6..27.4 at z 5.0
    R = RIDGE_H
    sl = (2.9 ** 2 + (R - W) ** 2) ** 0.5 / 2
    s.quad("sol_hroof", [(20.6, W, 7.9), (30.4, W, 7.9), (27.4, R, 5.0), (23.6, R, 5.0)],
           [(20.6 / 2, sl), (30.4 / 2, sl), (27.4 / 2, 0), (23.6 / 2, 0)])
    s.quad("sol_hroof", [(30.4, W, 2.1), (20.6, W, 2.1), (23.6, R, 5.0), (27.4, R, 5.0)],
           [(30.4 / 2, sl), (20.6 / 2, sl), (23.6 / 2, 0), (27.4 / 2, 0)])
    s.tri("sol_hroof", [(30.4, W, 7.9), (30.4, W, 2.1), (27.4, R, 5.0)], [(7.9 / 2, sl), (2.1 / 2, sl), (2.5, 0)])
    s.tri("sol_hroof", [(20.6, W, 2.1), (20.6, W, 7.9), (23.6, R, 5.0)], [(2.1 / 2, sl), (7.9 / 2, sl), (2.5, 0)])
    s.wall("sol_htrim", 23.6, 5.0, 27.4, 5.0, R - 0.05, R + 0.3, (0, 0, 1.9, 8 / 32))      # ridge cap
    # bay gable roof: eaves at x 22.7 / 28.3 (h B - 0.1), ridge x 25.5 at the apex, from z 8.35 back to 5.6
    eh, rh = B - 0.1, APEX_H + 0.15
    gl = (2.8 ** 2 + (rh - eh) ** 2) ** 0.5 / 2
    s.quad("sol_hroof", [(22.7, eh, 8.35), (25.5, rh, 8.35), (25.5, rh, 5.6), (22.7, eh, 5.6)],
           [(0, gl), (0, 0), (1.4, 0), (1.4, gl)])
    s.quad("sol_hroof", [(25.5, rh, 8.35), (28.3, eh, 8.35), (28.3, eh, 5.6), (25.5, rh, 5.6)],
           [(0, 0), (0, gl), (1.4, gl), (1.4, 0)])
    # bargeboards: the eave band along the gable's slopes
    s.quad("sol_htrim", [(22.7, eh - 0.25, 8.36), (25.5, rh - 0.25, 8.36), (25.5, rh + 0.05, 8.36),
                         (22.7, eh + 0.05, 8.36)], [(0, 16 / 32), (1.7, 16 / 32), (1.7, 8 / 32), (0, 8 / 32)])
    s.quad("sol_htrim", [(25.5, rh - 0.25, 8.36), (28.3, eh - 0.25, 8.36), (28.3, eh + 0.05, 8.36),
                         (25.5, rh + 0.05, 8.36)], [(0, 16 / 32), (1.7, 16 / 32), (1.7, 8 / 32), (0, 8 / 32)])


def compound(s):
    """Low wall around x 16.5..34.5, z 1.5..12.5 with violet coping, gate posts and an open iron gate at x 24..27;
    forecourt flags and the eclipse emblem (centre 25.5, 10.0) in front of the hall."""
    A = (64, 64)
    s.mat("sol_gate")
    s.mat("sol_fcpave")
    s.mat("sol_emblem_full")

    def low_wall(x0, z0, x1, z1):
        L = ((x1 - x0) ** 2 + (z1 - z0) ** 2) ** 0.5
        s.wall("sol_hwall", x0, z0, x1, z1, 0.0, 0.55, (0, 0, L / 2, 0.275))
        s.wall("sol_htrim", x0, z0, x1, z1, 0.55, 1.05, (0, 24 / 32, L / 2, 1.0))

    def coping_top(x0, z0, x1, z1):
        s.floor("sol_htrim", x0, z0, x1, z1, 1.05, (0, 25 / 32, max(x1 - x0, z1 - z0) / 2, 28 / 32))

    for (x0, x1) in ((16.5, 23.25), (27.75, 34.5)):
        low_wall(x0, 12.5, x1, 12.5)
        coping_top(x0, 12.0, x1, 12.5)
    low_wall(16.5, 1.5, 16.5, 12.5)
    low_wall(17.0, 12.0, 17.0, 1.5)
    coping_top(16.5, 1.5, 17.0, 12.5)
    low_wall(34.5, 12.5, 34.5, 1.5)
    low_wall(34.0, 1.5, 34.0, 12.0)
    coping_top(34.0, 1.5, 34.5, 12.5)
    low_wall(17.0, 2.0, 34.0, 2.0)
    coping_top(16.5, 1.5, 34.5, 2.0)
    for x0 in (23.25, 27.0):
        f = ("sol_hatlas", px(48, 32, 64, 64, 64, 64))
        s.box(x0, 11.9, x0 + 0.75, 12.65, 0.0, 2.0, {"s": f, "e": f, "w": f, "n": f,
                                                   "top": ("sol_htrim", (0, 25 / 32, 0.4, 28 / 32))})
    # open gate leaves, swung in
    s.wall("sol_gate", 24.0, 12.3, 24.0, 10.8, 0.0, 2.0, (0, 0, 0.75, 1))
    s.wall("sol_gate", 27.0, 12.3, 27.0, 10.8, 0.0, 2.0, (0, 0, 0.75, 1))
    # forecourt: flags on the emblem's grid (u offset by half a tile), emblem decal on top
    s.tiled_floor("sol_fcpave", 17.0, 8.0, 34.0, 12.0, 0.01, 2.0, ox=23.5, oz=8.0)
    s.tiled_floor("sol_fcpave", 24.5, 12.0, 26.5, 13.0, 0.01, 2.0, ox=23.5, oz=8.0)
    s.floor("sol_emblem_full", 24.0, 8.5, 27.0, 11.5, 0.02, (0, 0, 1, 1))     # 3x3 tiles (town-art)
    # lanterns in the forecourt corners, banners outside the gate
    s.mat("sol_furn")
    s.mat("sol_banner")
    for x in (18.0, 32.5):
        s.card("sol_furn", x, x + 0.5, 8.6, 0.0, 2.0, (24, 0, 32, 32), (32, 32))
    for x in (21.5, 28.5):
        s.card("sol_banner", x, x + 1.0, 13.1, 0.0, 2.0, (0, 0, 16, 32), (16, 32))


def plaza(s):
    """Memorial plaza south of the road: x 1..14, z 16..23."""
    for m in ("sol_plaza", "sol_border", "sol_furn", "sol_offer", "sol_candle"):
        s.mat(m)
    s.tiled_floor("sol_plaza", 1.0, 16.0, 14.5, 23.5, 0.01, 2.0)
    # garden of names: flower grass x 10..14, z 18.5..22.5, border strips on its edges
    s.mat("nhana")
    s.tiled_floor("nhana", 10.5, 18.5, 13.5, 22.5, 0.02, 1.0)
    # border strips: v 0 (grass) on the garden side, v 1 (kerb shadow) on the paving side
    h = 0.03
    s.quad("sol_border", [(9.5, h, 18.5), (14.5, h, 18.5), (14.5, h, 17.5), (9.5, h, 17.5)],
           [(0, 0), (2.5, 0), (2.5, 1), (0, 1)])                                    # north edge
    s.quad("sol_border", [(9.5, h, 22.5), (14.5, h, 22.5), (14.5, h, 23.5), (9.5, h, 23.5)],
           [(0, 0), (2.5, 0), (2.5, 1), (0, 1)])                                    # south edge
    s.quad("sol_border", [(10.5, h, 18.5), (10.5, h, 22.5), (9.5, h, 22.5), (9.5, h, 18.5)],
           [(0, 0), (2.0, 0), (2.0, 1), (0, 1)])                                    # west edge
    s.quad("sol_border", [(13.5, h, 22.5), (13.5, h, 18.5), (14.5, h, 18.5), (14.5, h, 22.5)],
           [(0, 0), (2.0, 0), (2.0, 1), (0, 1)])                                    # east edge
    F = (32, 32)
    for x in (2.5, 6.0):
        s.card("sol_furn", x, x + 1.5, 18.2, 0.0, 0.75, (0, 0, 24, 12), F)
        s.floor("sol_furn", x, 17.7, x + 1.5, 18.2, 0.45, px(0, 12, 24, 20, 32, 32))
    for (x, z) in ((1.5, 16.6), (8.5, 16.6), (8.5, 22.0), (1.5, 22.0)):
        s.card("sol_furn", x, x + 0.5, z, 0.0, 2.0, (24, 0, 32, 32), F)
    s.card("sol_furn", 4.0, 5.5, 21.0, 0.0, 0.75, (0, 20, 24, 32), F)
    s.card("sol_offer", 3.4, 4.2, 21.3, 0.0, 0.8, (0, 0, 16, 16), F)
    s.card("sol_offer", 5.4, 6.2, 21.3, 0.0, 0.8, (16, 0, 32, 16), F)
    s.card("sol_offer", 6.3, 7.1, 21.2, 0.0, 0.8, (0, 16, 16, 32), F)
    s.card("sol_offer", 4.4, 5.2, 21.5, 0.0, 0.8, (16, 16, 32, 32), F)
    s.card("sol_candle", 2.5, 3.2, 21.4, 0.0, 0.7, (0, 0, 16, 16), (16, 16))


def tent(s):
    """Registration tent, 3 x 2 tiles (x 16..19, z 17..19), 2-tile walls, open front facing south (the camera looks north,
    so an open side has to face south to be seen): canvas back, sides and pitched roof, striped valance, the
    registry table, the REGISTRY board."""
    for m in ("sol_canvas", "sol_awning", "sol_tent"):
        s.mat(m)
    s.wall("sol_canvas", 16, 17, 19, 17, 0, 2.0, (0, 0, 1.5, 1.0))
    for x in (16, 19):
        s.wall("sol_canvas", x, 17, x, 19, 0, 2.0, (0, 0, 1.0, 1.0))
        s.tri("sol_canvas", [(x, 2.0, 17), (x, 2.0, 19), (x, 2.7, 18)], [(0, 0.4), (1, 0.4), (0.5, 0)])
    for (zf, ze) in ((18, 16.9), (18, 19.1)):
        s.quad("sol_canvas", [(15.9, 1.95, ze), (19.1, 1.95, ze), (19.1, 2.7, zf), (15.9, 2.7, zf)],
               [(0, 0.7), (1.6, 0.7), (1.6, 0), (0, 0)])
    s.wall("sol_awning", 15.9, 19.12, 19.1, 19.12, 1.6, 2.05, (0, 0, 1.6, 11 / 16))
    s.wall("sol_awning", 15.9, 19.12, 19.1, 19.12, 1.4, 1.6, (0, 11 / 16, 1.6, 15 / 16))
    T = (32, 32)
    s.box(16.5, 18.3, 18.5, 19.0, 0.0, 0.6, {"s": ("sol_tent", px(0, 16, 32, 24, 32, 32)),
                                             "top": ("sol_tent", px(0, 0, 32, 16, 32, 32))})
    s.card("sol_tent", 16.5, 18.5, 19.15, 2.05, 2.55, (0, 24, 32, 32), T)


def dig(s):
    """The excavation in front of the Ruins hill: x 35..48, z 0..12."""
    for m in ("criffp", "dhole", "nsand", "ngrass", "nbridge", "sol_scaff", "sol_wfence", "sol_tarp", "sol_exatlas",
              "sol_spoil"):
        s.mat(m)
    s.wall("criffp", 35, 4.0, 48, 4.0, 0, 4, (0, 0, 6.5, 2))
    s.tiled_floor("ngrass", 35, 0, 48, 4.0, 4.0, 1.0)
    s.wall("dhole", 39.5, 3.98, 43.5, 3.98, 0, 4, (0, 0, 1, 1))
    s.tiled_floor("nsand", 35, 4, 48, 12.5, 0.005, 1.0)
    # scaffold faces (2 bays tall west, 1 bay east), plank decks
    s.wall("sol_scaff", 36, 4.7, 39, 4.7, 0, 4, (0, 0, 1.5, 2))
    s.wall("sol_scaff", 39, 4.7, 39, 4.05, 0, 4, (0, 0, 0.33, 2))
    s.floor("nbridge", 36, 4.05, 39, 4.7, 2.0, (0, 0, 1.5, 0.3))
    s.wall("sol_scaff", 44, 4.7, 47, 4.7, 0, 2, (0, 0, 1.5, 1))
    s.floor("nbridge", 44, 4.05, 47, 4.7, 2.0, (0, 0, 1.5, 0.3))
    # warning fence with the gap the grunt stands in
    s.wall("sol_wfence", 35.5, 8.5, 40.0, 8.5, 0, 1, (0, 0, 2.25, 1))
    s.wall("sol_wfence", 43.0, 8.5, 47.5, 8.5, 0, 1, (0, 0, 2.25, 1))
    E = (64, 32)
    for x in (37.6, 45.0):
        s.card("sol_exatlas", x, x + 1, 8.2, 0, 2, (0, 0, 16, 32), E)
    s.card("sol_exatlas", 43.1, 44.1, 8.7, 0, 2, (48, 0, 64, 32), E)
    s.card("sol_exatlas", 40.3, 41.3, 8.8, 0, 0.5, (32, 24, 48, 32), E)
    # spoil heap from the dig (stock criffp texels, sol_spoil palette)
    s.quad("sol_spoil", [(39.6, 0.0, 7.2), (41.6, 0.0, 7.2), (41.2, 0.7, 6.3), (40.0, 0.7, 6.3)],
           [(0, 0.55), (1, 0.55), (0.8, 0), (0.2, 0)])
    s.floor("sol_spoil", 40.0, 5.6, 41.2, 6.3, 0.7, (0.2, 0, 0.8, 0.35))
    # tarp-covered pile, crates
    s.box(36.4, 5.6, 38.6, 7.4, 0, 0.8, {"s": ("sol_tarp", (0, 0, 1.1, 0.4)), "e": ("sol_tarp", (0, 0, 0.9, 0.4)),
                                         "w": ("sol_tarp", (0, 0, 0.9, 0.4)), "top": ("sol_tarp", (0, 0, 1.1, 0.9))})
    cs = ("sol_exatlas", px(16, 0, 32, 16, 64, 32))
    ct = ("sol_exatlas", px(16, 16, 32, 32, 64, 32))
    for (x, z, h) in ((44.5, 5.5, 0), (45.5, 5.5, 0), (45.0, 5.5, 1.0), (46.0, 6.6, 0)):
        s.box(x, z, x + 1, z + 1, h, h + 1, {"s": cs, "e": cs, "w": cs, "top": ct})
    # cable from the lights to the cave, cable coil
    for x in range(38, 42):
        s.floor("sol_exatlas", x, 7.6, x + 1, 8.1, 0.02, px(32, 16, 48, 24, 64, 32))
    s.floor("sol_exatlas", 42.2, 6.4, 43.2, 7.4, 0.02, px(32, 0, 48, 16, 64, 32))


def ranch(s):
    """Kennel block (x 24..32, z 19..21), loading yard (x 33..47, z 16..24). (sol_truck was cut by town-art.)"""
    for m in ("sol_kwall", "sol_kroof", "sol_yard", "sol_ruts"):
        s.mat(m)
    s.tiled_floor("sol_yard", 33, 16.0, 47.5, 24.0, 0.01, 2.0)
    s.floor("sol_ruts", 43.0, 16.0, 45.0, 24.0, 0.015, (0, 0, 1, 4))
    s.wall("sol_kwall", 24, 21, 32, 21, 0, 2, (0, 0, 4, 1))
    s.wall("sol_kwall", 32, 21, 32, 19, 0, 2, (0, 0, 0.0001, 0.28))
    s.wall("sol_kwall", 32, 21, 32, 19, 0, 2, (0.02, 0, 0.48, 0.28))
    s.wall("sol_kwall", 24, 19, 24, 21, 0, 2, (0.02, 0, 0.48, 0.28))
    for x in (24, 32):
        s.tri("sol_kwall", [(x, 2, 19), (x, 2, 21), (x, 2.8, 20)], [(0.02, 0.28), (0.48, 0.28), (0.25, 0)])
    kl = (1.2 ** 2 + 0.8 ** 2) ** 0.5
    s.quad("sol_kroof", [(23.8, 2.0, 21.2), (32.2, 2.0, 21.2), (32.2, 2.8, 20), (23.8, 2.8, 20)],
           [(0, kl), (4.2, kl), (4.2, 0), (0, 0)])
    s.quad("sol_kroof", [(32.2, 2.0, 18.8), (23.8, 2.0, 18.8), (23.8, 2.8, 20), (32.2, 2.8, 20)],
           [(0, kl), (4.2, kl), (4.2, 0), (0, 0)])


def ground(s):
    for m in ("ngrass", "nsand"):
        s.mat(m)
    s.tiled_floor("ngrass", 0, 0, 35, 13.0, 0.0, 1.0)
    s.tiled_floor("nsand", 0, 13.0, 48, 16.0, 0.0, 1.0)
    s.tiled_floor("ngrass", 0, 16.0, 33, 24.0, 0.0, 1.0)
    s.tiled_floor("ngrass", 47.5, 12.5, 48, 24, 0.0, 1.0)


def stock_prop(model_id, x, z, name, h=0.0):
    m = C.build_model(model_id)
    mesh = nsbmd.model_to_mesh(m, (0, 0), name=name, offset=((x - 16) * 16, 16 + h * 16, (z - 16) * 16))
    for me in mesh["meshes"]:
        me["positions"] = me["positions_local"]
    return mesh


def full_emblem(src, dst):
    """Mirror the 24x24 quadrant (texels 0..23) into the 48x48 3x3-tile inlay the game draws with four mirrored-UV
    quads (build_art.build_emblem)."""
    im = png.read(src)
    q = im.pixels
    rows = []
    for y in range(48):
        yy = y if y < 24 else 47 - y
        rows.append([q[yy][x if x < 24 else 47 - x] for x in range(48)])
    png.write_rgba(dst, 48, 48, rows)
    open(dst[:-4] + ".json", "w").write('{"format": "pltt16"}')


def main():
    root = C.preview_dir()
    mdir = os.path.join(root, "render", "meshes")
    tdir = os.path.join(root, "render", "tex")
    os.makedirs(mdir, exist_ok=True)
    os.makedirs(tdir, exist_ok=True)
    full_emblem(os.path.join(C.ASSET_DIR, "sol_emblem.png"), os.path.join(tdir, "sol_emblem_full.png"))
    s = Scene("sol_mock")
    ground(s)
    hall(s)
    compound(s)
    plaza(s)
    tent(s)
    dig(s)
    ranch(s)
    files = [s.save(mdir)]
    # stock buildings: Pokemon Center + door, a Solaceon house + door (offsets as in chunk 072)
    for (mid, x, z, h, nm) in ((4, 13.0, 10.5, 0.0, "stock_pc"), (70, 13.0, 11.5625, 0.0386, "stock_pc_door"),
                               (197, 6.5, 9.5, 0.0, "stock_house"), (246, 6.608, 10.123, 0.0794, "stock_house_door")):
        mesh = stock_prop(mid, x, z, nm, h)
        p = os.path.join(mdir, nm + ".mesh.json")
        json.dump(mesh, open(p, "w"))
        files.append(p)
    used = {m["texture"] for m in s.materials.values()}
    kit = sorted(f[:-5] for f in os.listdir(C.ASSET_DIR) if f.endswith(".json") and "." not in f[:-5])
    missing = [k for k in kit if k not in used and not (k == "sol_emblem" and "sol_emblem_full" in used)]
    print("kit textures in the mock:", len(kit) - len(missing), "/", len(kit), "missing:", missing)
    if "--no-render" in sys.argv:
        return
    texdirs = [tdir, C.ASSET_DIR, os.path.join(root, "stock_set010"), os.path.join(root, "stock_props_solaceon")]
    tex_args = sum((["--tex", d] for d in texdirs), [])
    lit = ["--lit"] if "--lit" in sys.argv else []
    suffix = "_lit" if lit else ""
    want = sys.argv[sys.argv.index("--views") + 1].split(",") if "--views" in sys.argv else list(VIEWS)
    out = os.path.join(root, "render")
    if "top" in want or "--views" not in sys.argv:
        cmd = [BLENDER, "-b", "--factory-startup", "-P", BP, "--", *tex_args, "--out", os.path.join(out, "street" + suffix),
               "--views", "top", "--region", "0,0,48,24", "--px", "16", "--dscolor", *lit, *files]
        subprocess.run(cmd, check=True, capture_output=True)
        print("wrote", os.path.join(out, f"street{suffix}_top.png"))
    for v in want:
        if v not in VIEWS:
            continue
        tx, tz = VIEWS[v]
        cmd = [BLENDER, "-b", "--factory-startup", "-P", BP, "--", *tex_args, "--out", os.path.join(out, v + suffix),
               "--views", "game", "--target", f"{tx},{tz}", "--dscolor", *lit, *files]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            print(r.stdout[-2000:], r.stderr[-2000:])
            raise SystemExit(1)
        print("wrote", os.path.join(out, f"{v}{suffix}_game.png"))


if __name__ == "__main__":
    main()
