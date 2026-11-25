#!/usr/bin/env python3
"""Preview helpers: the raid's object events as camera-facing billboards (mesh.json) for blender_preview, plus the
concept sheets of the new field sprites raid_maps.md specifies (standard library only).

  python3 tools/solaceon_ruins/billboards.py --concept     (re)draw tools/solaceon_ruins/concept/*.png

Sprites come from the existing sheets (res/field/objects/arc1|arc2) where there is one; stock sprites that live
only in the prebuilt mmodel archive get a stand-in (Cyrus: a recoloured grunt, Looker: the Arc 2 Looker sheet, the
item ball and the rock: small drawings). The new sprites (generator, barrier, dark rack/crystal, dig rope) use the
concept sheets, drawn here in the documented idle2 format (64x32, two 32x32 frames, index 0 transparent).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import placements as PL  # noqa: E402
import ruins as R  # noqa: E402

sys.path.insert(0, os.path.join(R.ROOT, "tools", "world_art"))
import chunkedit as C  # noqa: E402,F401  (sets up the lake_verity path)
import png  # noqa: E402

CONCEPT = os.path.join(HERE, "concept")
OBJ = os.path.join(R.ROOT, "res", "field", "objects")
PITCH = math.radians(63.2647705078125)        # CAMERA_TYPE_CAVE
WALKER_ROW = {"N": 0, "S": 1, "W": 2, "E": 3}

SHEETS = {
    "OBJ_EVENT_GFX_ECLIPSE_GRUNT_M": ("arc1/eclipse_grunt_m.png", "walker"),
    "OBJ_EVENT_GFX_ECLIPSE_GRUNT_F": ("arc1/eclipse_grunt_f.png", "walker"),
    "OBJ_EVENT_GFX_INDRA": ("arc2/indra.png", "walker"),
    "OBJ_EVENT_GFX_LOOKER": ("arc2/looker_newspaper.png", "walker"),          # stand-in for the stock Looker
    "OBJ_EVENT_GFX_ECLIPSE_CRATE": ("arc2/eclipse_crate.png", "idle2"),
    "OBJ_EVENT_GFX_SHARD_FRAME": ("arc2/shard_frame.png", "idle2"),
    "OBJ_EVENT_GFX_VIOLET_CRYSTAL": ("arc2/violet_crystal.png", "idle2"),
    "OBJ_EVENT_GFX_RIFT_ARC2": ("arc2/rift_arc2.png", "idle2"),
}
CONCEPTS = ["shard_generator", "shard_generator_off", "shard_barrier", "shard_frame_dark", "violet_crystal_dark",
            "dig_rope"]


# --------------------------------------------------------------------------------------------------------------
# concept sheets (idle2 64x32, 16 colours, index 0 transparent)
# --------------------------------------------------------------------------------------------------------------

def _blank():
    return [[0] * 64 for _ in range(32)]


def _rect(g, x0, y0, x1, y1, v, fx=0):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            g[y][x + fx] = v


PAL_MACHINE = [(0, 0, 0), (24, 26, 32), (52, 58, 70), (82, 90, 104), (118, 126, 140), (164, 170, 182),
               (52, 30, 74), (92, 52, 132), (140, 96, 186), (200, 172, 236), (250, 246, 255), (222, 180, 41),
               (12, 12, 14), (60, 44, 30), (90, 30, 30), (40, 40, 46)]


def concept_generator(on):
    g = _blank()
    for f in (0, 32):
        # skids, cabinet, top vent, the round shard window, an amber lamp, two cables out of the base
        _rect(g, 6, 28, 25, 29, 12, f)
        _rect(g, 7, 9, 24, 27, 2, f)
        _rect(g, 7, 9, 24, 9, 5, f)
        _rect(g, 7, 10, 7, 27, 4, f)
        _rect(g, 24, 10, 24, 27, 1, f)
        _rect(g, 9, 5, 22, 8, 3, f)
        for x in range(10, 22, 3):
            _rect(g, x, 6, x, 7, 1, f)
        cx, cy = 15.5, 18
        for y in range(12, 25):
            for x in range(9, 23):
                r = math.hypot(x - cx, y - cy)
                if r < 5.6:
                    if on:
                        v = 10 if r < 1.6 + (f // 32) * 0.8 else (9 if r < 3.0 else (8 if r < 4.3 else 7))
                    else:
                        v = 15 if r < 3.0 else 1
                    g[y][x + f] = v
                elif r < 6.4:
                    g[y][x + f] = 1
        g[11][21 + f] = 11 if on else 3
        g[11][22 + f] = 11 if on else 3
        # black-sun stencil (a ring) on the top vent
        for x in (13, 18):
            g[4][x + f] = 1
        _rect(g, 14, 3, 17, 3, 1, f)
        # cables
        for y in range(26, 32):
            g[y][4 + f] = 12 if y % 2 else 1
            g[y][27 + f] = 7 if on else 15
        _rect(g, 4, 25, 7, 25, 12, f)
        _rect(g, 24, 25, 27, 25, 7 if on else 15, f)
    return g, PAL_MACHINE


def concept_barrier():
    pal = [(0, 0, 0), (40, 18, 64), (70, 34, 110), (110, 60, 170), (150, 100, 210), (196, 160, 240), (236, 220, 255),
           (255, 255, 255)]
    g = _blank()
    for f in (0, 32):
        ph = (f // 32) * 2.1
        for y in range(12, 31):          # a short curtain (rows 12-30): it must not hide whoever stands behind it
            for x in range(0, 32):
                # a curtain of light: bright edges, dithered core, a moving band
                band = 0.5 + 0.5 * math.sin(y * 0.55 + ph + x * 0.18)
                core = (x + y + f // 32) % 2 == 0
                if y in (12, 30):
                    v = 5
                elif (x + y) % 2 and band < 0.35:
                    v = 0                    # see-through holes
                else:
                    v = 2 + int(band * 3) + (1 if core and band > 0.7 else 0)
                g[y][x + f] = v
            g[y][0 + f] = 6
            g[y][31 + f] = 6
        for x in range(2, 30, 6):
            g[13][x + f] = 7
            g[29][x + 3 + f if x + 3 < 32 else x + f] = 7
    return g, pal


def recolour_sheet(rel, ramp):
    """A copy of an existing sheet with its violet colours mapped onto `ramp` by luminance (the drained look)."""
    im = png.read(os.path.join(OBJ, rel))
    pal, idx = list(im.palette), im.indices
    out = []
    for c in pal:
        r, g_, b = c[:3]
        if b > r + 20 and b > g_ + 10:          # violet-ish
            l = (0.3 * r + 0.59 * g_ + 0.11 * b) / 255
            out.append(ramp[min(len(ramp) - 1, int(l * len(ramp) * 1.4))])
        else:
            out.append(tuple(c[:3]))
    n = max(max(r) for r in idx) + 1
    assert n <= 16, (rel, n)
    return idx, out[:16]


def concept_rope():
    pal = [(0, 0, 0), (74, 49, 24), (139, 98, 57), (205, 164, 106), (222, 180, 41), (255, 230, 120), (190, 40, 40),
           (240, 240, 232), (40, 30, 20)]
    g = _blank()
    for f in (0, 32):
        for px in (4, 26):           # two posts
            _rect(g, px, 12, px + 2, 29, 2, f)
            _rect(g, px, 12, px, 29, 3, f)
            _rect(g, px - 1, 29, px + 3, 30, 8, f)
            _rect(g, px, 11, px + 2, 11, 1, f)
        for x in range(7, 26):       # the sagging rope with red/white flags
            y = 15 + int(3 * math.sin((x - 7) / 19 * math.pi))
            g[y][x + f] = 3
            g[y + 1][x + f] = 1
            if x in (11, 16, 21):
                _rect(g, x, y + 2, x + 1, y + 4, 6 if x != 16 else 7, f)
        # the little bell (swings between frames)
        bx = 16 + (1 if f else -1)
        _rect(g, bx - 1, 20, bx + 1, 22, 4, f)
        g[23][bx + f] = 5
    return g, pal


def write_concepts(d=CONCEPT):
    os.makedirs(d, exist_ok=True)
    grey = [(40, 40, 46), (70, 72, 80), (104, 106, 114), (140, 142, 150), (180, 182, 188)]
    items = {
        "shard_generator": concept_generator(True),
        "shard_generator_off": concept_generator(False),
        "shard_barrier": concept_barrier(),
        "shard_frame_dark": recolour_sheet("arc2/shard_frame.png", grey),
        "violet_crystal_dark": recolour_sheet("arc2/violet_crystal.png", grey),
        "dig_rope": concept_rope(),
    }
    for name, (g, pal) in items.items():
        assert len(pal) <= 16, name
        png.write_indexed(os.path.join(d, name + ".png"), 64, 32, g, [tuple(c) + (255,) for c in pal],
                          transparent0=True)
    return list(items)


# --------------------------------------------------------------------------------------------------------------
# billboards
# --------------------------------------------------------------------------------------------------------------

def _frame(im, x0, y0):
    return [[im.pixels[y0 + y][x0 + x] for x in range(32)] for y in range(32)]


def _standin(kind):
    px = [[(0, 0, 0, 0)] * 32 for _ in range(32)]
    if kind == "ball":
        for y in range(32):
            for x in range(32):
                r = math.hypot(x - 15.5, y - 24)
                if r < 5:
                    px[y][x] = (230, 40, 40, 255) if y < 24 else (240, 240, 240, 255)
                    if abs(y - 24) < 1 or 1.2 < r < 2.2 and y >= 23:
                        px[y][x] = (30, 30, 30, 255)
    elif kind == "rock":
        for y in range(32):
            for x in range(32):
                r = math.hypot((x - 15.5) / 1.2, y - 21)
                if r < 8:
                    v = 150 - int(r * 9) + (20 if x + y < 36 else 0)
                    px[y][x] = (v, v - 8, v - 18, 255)
    return px


def sprite_png(gfx, d, facing="S"):
    """-> texture name (written as d/<name>.png) for an object's gfx and facing."""
    os.makedirs(d, exist_ok=True)
    name = "spr_" + gfx[len("OBJ_EVENT_GFX_"):].lower() + "_" + facing.lower()
    path = os.path.join(d, name + ".png")
    if os.path.exists(path):
        return name
    if gfx in SHEETS:
        rel, layout = SHEETS[gfx]
        im = png.read(os.path.join(OBJ, rel))
        px = _frame(im, 0, 32 * WALKER_ROW[facing]) if layout == "walker" else _frame(im, 0, 0)
    elif gfx == "OBJ_EVENT_GFX_CYRUS":
        im = png.read(os.path.join(OBJ, "arc1/eclipse_grunt_m.png"))
        px = [[(p[2] // 2 + 40, p[1] // 2 + 50, p[0] // 2 + 70, p[3]) if p[3] else p for p in row]
              for row in _frame(im, 0, 32 * WALKER_ROW[facing])]
    elif gfx in ("OBJ_EVENT_GFX_HIKER", "OBJ_EVENT_GFX_RUIN_MANIAC"):      # stock NPCs: a warm stand-in
        im = png.read(os.path.join(OBJ, "arc1/eclipse_grunt_m.png"))
        px = [[(p[0] // 2 + 90, p[1] // 2 + 60, p[2] // 3 + 30, p[3]) if p[3] else p for p in row]
              for row in _frame(im, 0, 32 * WALKER_ROW[facing])]
    elif gfx == "OBJ_EVENT_GFX_POKEBALL":
        px = _standin("ball")
    elif gfx in ("OBJ_EVENT_GFX_ROCK_SMASH", "OBJ_EVENT_GFX_STRENGTH_BOULDER"):
        px = _standin("rock")
    else:
        cname = gfx[len("OBJ_EVENT_GFX_"):].lower()
        cp = os.path.join(CONCEPT, cname + ".png")
        if cname in CONCEPTS:
            if not os.path.exists(cp):
                write_concepts()
            px = _frame(png.read(cp), 0, 0)
        else:
            px = [[(255, 0, 255, 255) if 8 < x < 24 and 8 < y < 30 else (0, 0, 0, 0) for x in range(32)]
                  for y in range(32)]
    png.write_rgba(path, 32, 32, px)
    json.dump({"format": "pltt16", "c0": 1, "size": [32, 32]}, open(os.path.join(d, name + ".json"), "w"))
    return name


def billboard_mesh(objs, d, name, mode="game"):
    """objs: [(gfx, x, z, facing)] -> mesh.json dict of camera-facing quads (feet at the tile centre); mode "top":
    flat 1x1-tile icons lying on each object's tile instead, for the top-down view."""
    up = (0.0, math.cos(PITCH), -math.sin(PITCH))
    mats, meshes = {}, []
    for i, (gfx, x, z, facing) in enumerate(objs):
        tex = sprite_png(gfx, d, facing)
        mats[tex] = {"name": tex, "texture": tex, "palette": tex, "alpha": 31, "size": [32, 32],
                     "polygon_attr": {"lights": 0, "cull": "none", "alpha": 31}}
        fx, fz = x + 0.5, z + 0.5
        if mode == "top":
            h = 0.9 + 0.01 * i
            pos = [[x, h, z + 1], [x + 1, h, z + 1], [x + 1, h, z], [x, h, z]]
            meshes.append({"material": tex, "positions": pos, "uvs": [[0, 1], [1, 1], [1, 0], [0, 0]],
                           "colors": [[255, 255, 255]] * 4, "normals": None, "quads": [[0, 1, 2, 3]], "tris": []})
            continue
        # pulled 4 tiles towards the camera along the view direction (the projection barely moves with this
        # narrow FOV), so Blender's depth test doesn't cut the sprites into the beveled north walls
        k = 4.0 + 0.03 * (x % 2) + 0.015 * i     # and never coplanar with a neighbour (Cycles skips those)
        b = (fx, 0.0 - up[1] * 3 / 16 + 0.01 + k * math.sin(PITCH), fz - up[2] * 3 / 16 + k * math.cos(PITCH))
        pos = []
        for dx, k in ((-1, 0), (1, 0), (1, 2), (-1, 2)):
            pos.append([b[0] + dx, b[1] + up[1] * k, b[2] + up[2] * k])
        meshes.append({"material": tex, "positions": pos, "uvs": [[0, 1], [1, 1], [1, 0], [0, 0]],
                       "colors": [[255, 255, 255]] * 4, "normals": None, "quads": [[0, 1, 2, 3]], "tris": []})
    return {"name": name, "origin_tile": [0, 0], "materials": list(mats.values()), "meshes": meshes}


STATE_OF = {"pre": dict(var=0), "raid": dict(var=30), "vault": dict(var=40, A=1, B=1, C=1, D=1),
            "after": dict(var=50, A=1, B=1, C=1, D=1, E=1, F=1, G=1)}


def write_room_billboards(mesh_dir, spr_dir, state, mode="game"):
    """Billboard mesh.json per dressed room for a story state; -> {room short name: path}."""
    s = PL.full_state(STATE_OF[state])
    out = {}
    for room in R.ROOMS:
        objs = []
        for o in PL.ROOMS.get(room, []):
            if PL.visible(room, o, s):
                objs.append((o["gfx"], o["x"], o["z"], o["dir"]))
        for o in PL.stock_events(room)["object_events"]:
            objs.append((o["graphics_id"], o["x"], o["z"], "NSWE"[int(o["initial_dir"])]))
        if not objs:
            continue
        name = R.ROOMS[room][0]
        path = os.path.join(mesh_dir, f"billboards_{name}_{state}_{mode}.mesh.json")
        json.dump(billboard_mesh(objs, spr_dir, f"bb_{name}", mode), open(path, "w"))
        out[name] = path
    return out


if __name__ == "__main__":
    if "--concept" in sys.argv:
        print("wrote", write_concepts(), "to", CONCEPT)
