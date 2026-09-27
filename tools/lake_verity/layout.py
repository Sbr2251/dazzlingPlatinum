#!/usr/bin/env python3
"""Tile layout of the redesigned Lake Verity (map matrix 102, chunks 537-542). See docs/lake_verity_redesign/PLAN.md.

Usage: python3 tools/lake_verity/layout.py [--ascii]  (standard library only)

This file is the single source of truth for WHERE things are. The art (Blender scene), the collision
(permissions), the height map (BDHC) and the events (warps, NPCs) are all generated from / checked against it.

Coordinates are absolute tiles over the 96x64 matrix: x = 0..95 west->east, z = 0..63 north->south.
Chunk (cx, cz) = (x // 32, z // 32); chunk ids 537 538 539 / 540 541 542. The island sits on the corner where
537/538/540/541 meet (x=32, z=32).
Heights `h` are in tiles above the lake shore ground (1 tile = 16 world units, FX32_CONST(16); world y = 16 + 16 * h).
Water is at h = WATER_H = -0.5: the stock surf collision and the l_lake water plane are at world y 8, half a tile below
the shore (see docs/lake_verity_redesign/pipeline.md).

Everything outside the island + bridge is the stock map, unchanged.

The castle is one storey outside: the F1 block, whose only door is DOOR_1F on the courtyard (-> the castle interior),
and on top of it an open-air roof terrace at h = F1_H, surrounded by F1's crenellated parapet and reached by the open
west staircase. The Distortion World portal lies in the middle of the terrace: the stock floor vortex of distorted
Spear Pillar (map prop 581, placed by build_art.py), centred on LAUNCHPAD. As in Spear Pillar its footprint
(PORTAL_TILES, 7 x 6 tiles) is blocked at the terrace height; the player stands next to it and presses A on any
of its edge tiles (PORTAL_EDGE, the bg events). There is no upper floor, keep, roof deck or roof hatch any more,
and only the two south corner towers remain.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAP_DATA = os.path.join(HERE, "..", "..", "res", "field", "maps", "data")
CHUNKS = {537: (0, 0), 538: (1, 0), 539: (2, 0), 540: (0, 1), 541: (1, 1), 542: (2, 1)}
W, H = 96, 64

# collision values (u16 per tile in map_data permissions)
BLOCK, WATER, GRASS, WALK = 0x8000, 0x15, 0x02, 0x00
WATER_H = -0.5       # stock water surface / surf collision height (world y 8)
DOOR = 0x6E          # stock value of the Verity Cavern door tile (32,32)
EXIT = 0x6F          # stock value of the Lakefront exit tiles (46,54), (47,54)

# ---- feature geometry (inclusive tile ranges) ----
ISLAND = (23, 21, 41, 39)             # x0, z0, x1, z1 walkable plateau; 2-tile octagon corner cuts
F1 = (25, 22, 39, 33)                 # the castle block: walls + crenellated parapet on its perimeter; its whole
F1_H = 4                              # inside is the open-air roof terrace at h=F1_H (walkable, reached by the stair)
TOWERS = [(25, 33), (39, 33)]         # round towers on the two south corners of F1 (wall tiles), visual only
TOWER_H = 10                          # tower top (collision height of the blocked tower tiles)
DOOR_1F = (32, 33)                    # the castle's only door (ground) -> castle 1F interior (was the Verity Cavern
                                      # warp at (32,32))
LAUNCHPAD = (32, 27)                  # centre tile of the Distortion World portal, centred on the terrace
# The stock portal's footprint, blocked like the stock Spear Pillar permissions around its centre tile (31,25):
# rows dz -3 and +2 span dx -2..+2, rows dz -2..+1 span dx -3..+3. The prop's widest disc is about 7.8 tiles.
PORTAL_ROWS = {-3: 2, -2: 3, -1: 3, 0: 3, 1: 3, 2: 2}
PORTAL_TILES = [(LAUNCHPAD[0] + dx, LAUNCHPAD[1] + dz) for dz, w in PORTAL_ROWS.items() for dx in range(-w, w + 1)]
# footprint tiles next to a walkable tile: the portal's bg events (the player faces one of them and presses A)
PORTAL_EDGE = [t for t in PORTAL_TILES
               if any((t[0] + dx, t[1] + dz) not in PORTAL_TILES for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
# Open staircase (camera tilt): west side, climbs north from the courtyard (enter from z=37, h=0) to the F1 terrace
STAIR = (23, 31, 24, 36)              # x0, z0, x1, z1; height rises linearly from z1 (bottom) to z0 (top)
STAIR_LANDING = (23, 29, 24, 30)      # flat at h=F1_H, enters the F1 terrace through a gap in F1's west wall
STAIR_WALL_GAP = [(25, 29), (25, 30)]
STAIR_RAIL = [(25, z) for z in range(34, 37)] + [(23, 28), (24, 28)]   # low walls: stair/courtyard, landing/courtyard
# Drawbridge: east from the island to the east shore (stock walkable tiles (50,36), (50,37))
BRIDGE = (42, 36, 49, 37)
GATE_TOWERS = [(41, 35), (41, 38)]    # gatehouse pillars (blocked); (41,36), (41,37) is the arch (walkable)


def stock_grid():
    grid = {}
    for idx, (cx, cz) in CHUNKS.items():
        with open(os.path.join(MAP_DATA, f"map_data_{idx:03d}.bin"), "rb") as f:
            d = f.read()
        vals = struct.unpack("<1024H", d[16:16 + 0x800])
        for i, v in enumerate(vals):
            grid[(cx * 32 + i % 32, cz * 32 + i // 32)] = v
    return grid


def inside(r, x, z):
    return r[0] <= x <= r[2] and r[1] <= z <= r[3]


def perimeter(r, x, z):
    return inside(r, x, z) and (x in (r[0], r[2]) or z in (r[1], r[3]))


def island_cut(x, z):
    x0, z0, x1, z1 = ISLAND
    dx = min(x - x0, x1 - x)
    dz = min(z - z0, z1 - z)
    return dx + dz < 2


def stair_height(z):
    x0, z0, x1, z1 = STAIR
    # tile z1 is the first step (h just above 0), tile z0 the last before the landing
    return F1_H * (z1 - z + 1) / (z1 - z0 + 2)


def tiles():
    """Returns {(x, z): (collision, h, kind)} for the whole 96x64 matrix."""
    g = stock_grid()
    out = {}
    for (x, z), v in g.items():
        kind = {BLOCK: "forest", WATER: "water", GRASS: "grass", WALK: "ground", EXIT: "exit"}.get(v, "ground")
        # the stock hut / cavern door no longer exist
        if 29 <= x <= 35 and 28 <= z <= 34:
            v, kind = WATER, "water"
        out[(x, z)] = (v, WATER_H if kind == "water" else 0.0, kind)

    def put(x, z, coll, h, kind):
        out[(x, z)] = (coll, float(h), kind)

    for x in range(ISLAND[0], ISLAND[2] + 1):
        for z in range(ISLAND[1], ISLAND[3] + 1):
            if not island_cut(x, z):
                put(x, z, WALK, 0, "courtyard")
    for x in range(F1[0], F1[2] + 1):
        for z in range(F1[1], F1[3] + 1):
            if perimeter(F1, x, z):
                put(x, z, BLOCK, F1_H, "wall1")
            else:
                put(x, z, WALK, F1_H, "terrace1")
    for x, z in TOWERS:
        put(x, z, BLOCK, TOWER_H, "tower")
    put(*DOOR_1F, DOOR, 0, "door1")
    for x, z in PORTAL_TILES:
        put(x, z, BLOCK, F1_H, "portal")
    put(*LAUNCHPAD, BLOCK, F1_H, "launchpad")
    for x in range(STAIR[0], STAIR[2] + 1):
        for z in range(STAIR[1], STAIR[3] + 1):
            put(x, z, WALK, stair_height(z), "stair")
    for x in range(STAIR_LANDING[0], STAIR_LANDING[2] + 1):
        for z in range(STAIR_LANDING[1], STAIR_LANDING[3] + 1):
            put(x, z, WALK, F1_H, "landing")
    for x, z in STAIR_WALL_GAP:
        put(x, z, WALK, F1_H, "landing")
    for x, z in STAIR_RAIL:
        put(x, z, BLOCK, 1, "rail")
    for x in range(BRIDGE[0], BRIDGE[2] + 1):
        for z in range(BRIDGE[1], BRIDGE[3] + 1):
            put(x, z, WALK, 0, "bridge")
    for x, z in GATE_TOWERS:
        put(x, z, BLOCK, 5, "gate")
    for z in (36, 37):
        put(41, z, WALK, 0, "gate_arch")
    return out


CHARS = {"forest": "#", "water": "~", "grass": '"', "ground": ".", "exit": "E", "courtyard": ",",
         "wall1": "1", "terrace1": "t", "tower": "O", "door1": "D", "launchpad": "L", "portal": "P", "stair": "/", "landing": "=",
         "rail": "|", "bridge": "b", "gate": "G", "gate_arch": "a"}

if __name__ == "__main__":
    t = tiles()
    if "--ascii" in sys.argv:
        for z in range(10, 60):
            print(f"{z:2d} " + "".join(CHARS[t[(x, z)][2]] for x in range(4, 64)))
        print("   " + "".join(str(x // 10) if x % 10 == 0 else " " for x in range(4, 64)))
