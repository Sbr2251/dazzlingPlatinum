#!/usr/bin/env python3
"""Tile layout of the redesigned Lake Verity (map matrix 102, chunks 537-542). See docs/lake_verity_redesign/PLAN.md.

Usage: python3 tools/lake_verity/layout.py [--ascii]  (standard library only)

This file is the single source of truth for WHERE things are. The art (Blender scene), the collision
(permissions), the height map (BDHC) and the events (warps, NPCs) are all generated from / checked against it.

Coordinates are absolute tiles over the 96x64 matrix: x = 0..95 west->east, z = 0..63 north->south.
Chunk (cx, cz) = (x // 32, z // 32); chunk ids 537 538 539 / 540 541 542. The island sits on the corner where
537/538/540/541 meet (x=32, z=32).
Heights `h` are in tiles above the lake shore ground (1 tile = 16 world units, FX32_CONST(16)); water is at 0
too (the stock water surface is flush with the shore collision).

Everything outside the island + bridge is the stock map, unchanged.
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
DOOR = 0x6E          # stock value of the Verity Cavern door tile (32,32)
EXIT = 0x6F          # stock value of the Lakefront exit tiles (46,54), (47,54)

# ---- feature geometry (inclusive tile ranges) ----
ISLAND = (23, 21, 41, 39)             # x0, z0, x1, z1 walkable plateau; 2-tile octagon corner cuts
F1 = (25, 22, 39, 33)                 # floor 1 block, walls on its perimeter, roof terrace inside at h=F1_H
F1_H = 4
F2 = (28, 23, 36, 30)                 # floor 2 block, roof terrace inside at h=F2_H (not walkable: decorative)
F2_H = 8
F3 = (30, 24, 34, 28)                 # top keep; its inside is the roof deck at h=F3_H (launchpad + portal)
F3_H = 10
TOWERS = [(25, 22), (39, 22), (25, 33), (39, 33)]   # round corner towers (on F1 wall tiles), visual only
DOOR_1F = (32, 33)                    # ground door -> castle 1F interior (was the Verity Cavern warp at (32,32))
DOOR_2F = (32, 30)                    # door in F2's south wall, reached from the F1 roof terrace -> castle 2F interior
ROOF_HATCH = (33, 27)                 # arrival/exit warp on the roof deck <-> castle 3F interior
LAUNCHPAD = (32, 26)                  # centre of the launchpad; portal hovers above it
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
        out[(x, z)] = (v, 0.0, kind)

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
            elif inside(F2, x, z):
                put(x, z, BLOCK, F2_H, "wall2" if perimeter(F2, x, z) else "keep2")
            else:
                put(x, z, WALK, F1_H, "terrace1")
    for x in range(F3[0], F3[2] + 1):
        for z in range(F3[1], F3[3] + 1):
            put(x, z, BLOCK if perimeter(F3, x, z) else WALK, F3_H, "wall3" if perimeter(F3, x, z) else "roof")
    for x, z in TOWERS:
        put(x, z, BLOCK, F2_H + 2, "tower")
    put(*DOOR_1F, DOOR, 0, "door1")
    put(*DOOR_2F, DOOR, F1_H, "door2")
    put(*ROOF_HATCH, DOOR, F3_H, "hatch")
    put(*LAUNCHPAD, WALK, F3_H, "launchpad")
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
         "wall1": "1", "wall2": "2", "keep2": "2", "wall3": "3", "terrace1": "t", "roof": "r", "tower": "O",
         "door1": "D", "door2": "d", "hatch": "h", "launchpad": "L", "stair": "/", "landing": "=", "rail": "|",
         "bridge": "b", "gate": "G", "gate_arch": "a"}

if __name__ == "__main__":
    t = tiles()
    if "--ascii" in sys.argv:
        for z in range(10, 60):
            print(f"{z:2d} " + "".join(CHARS[t[(x, z)][2]] for x in range(4, 64)))
        print("   " + "".join(str(x // 10) if x % 10 == 0 else " " for x in range(4, 64)))
