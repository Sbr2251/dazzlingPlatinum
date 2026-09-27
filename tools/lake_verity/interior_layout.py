#!/usr/bin/env python3
"""Verity Castle 1F (entrance hall): the tile contract shared by the art script (lv_interior.py) and
build_interior.py. Standard library only.

The map is one chunk (matrix 289 = [[MAP_666]]), so chunk-local tiles are absolute tiles. Like the stock indoor
maps (Old Chateau, map_data_509) the room sits in the north-west of the chunk inside a ring of blocked tiles;
everything outside the room is blocked too. The floor is at world y 0 (h = -1 in the mesh.json convention
world y = 16 + 16 h), as in the stock interiors.

Room (x east, z south, tiles):
    walkable floor        x 2..16, z 4..15 (15 x 12)
    wall ring (blocked)   x 1 and x 17 (side walls), z 3 (north wall); z 16 is the open south edge (blocked,
                          drawn black like the stock interiors)
    exit mat              (9, 15)  collision 0x65 WARP_ENTRANCE_SOUTH (stock indoor exit mat), warp 0
    stair warp            (9, 4)   collision 0x5E WARP_STAIRS_EAST, warp 1, BLOCKED (0x805E) behind a barricade
    stairwell             x 10..13, z 4..5, descends east (blocked); the arrival tile for warp 1 is (10, 4)
    pillars               (5, 8), (13, 8), (5, 12), (13, 12) (blocked)

Unblocking the stair later: clear bit 15 on (9, 4) (BARRIER_TILES) and drop the barricade geometry.
"""

BLOCK = 0x8000
FLOOR = 0x00                  # plain indoor floor (0x0B OLD_CHATEAU_FLOOR carries the encounter flag)
EXIT_MAT = 0x65               # TILE_BEHAVIOR_WARP_ENTRANCE_SOUTH: fires when the player presses south on it
STAIRS_EAST = 0x5E            # TILE_BEHAVIOR_WARP_STAIRS_EAST: fires when the player presses east on it

FLOOR_H = -1.0                # mesh.json h of the floor (world y 0)
X0, X1 = 2, 16                # walkable x range (inclusive)
Z0, Z1 = 4, 15                # walkable z range (inclusive)
WALL_H = 4.0                  # top of the walls (h), i.e. 5 tiles above the floor

EXIT_TILE = (9, 15)
STAIR_TILE = (9, 4)
STAIRWELL = (10, 4, 13, 5)    # x0, z0, x1, z1 inclusive
STAIR_ARRIVAL = (10, 4)       # sub_02057368 places the player one tile east of a 0x5E warp, facing west
PILLARS = ((5, 8), (13, 8), (5, 12), (13, 12))
BARRIER_TILES = (STAIR_TILE,)

# warp_events of events_verity_castle_1f.json, in order
WARPS = (
    (EXIT_TILE, "MAP_HEADER_LAKE_VERITY", 0),
    (STAIR_TILE, "MAP_HEADER_VERITY_CAVERN", 0),
)

# stock exit mat prop: area_build model 78 (d_mat01), in props list 21 (used by area 0x4C)
EXIT_MAT_MODEL = 78


def in_room(x, z):
    return X0 <= x <= X1 and Z0 <= z <= Z1


def in_stairwell(x, z):
    x0, z0, x1, z1 = STAIRWELL
    return x0 <= x <= x1 and z0 <= z <= z1


def collision(x, z):
    """Permission value of chunk tile (x, z)."""
    if not in_room(x, z):
        return BLOCK
    if (x, z) == EXIT_TILE:
        return EXIT_MAT
    if (x, z) == STAIR_TILE:
        return STAIRS_EAST | (BLOCK if STAIR_TILE in BARRIER_TILES else 0)
    if in_stairwell(x, z) or (x, z) in PILLARS:
        return BLOCK
    return FLOOR


def grid():
    """32 x 32 [z][x] permission values."""
    return [[collision(x, z) for x in range(32)] for z in range(32)]


# BDHC: one flat plate at the floor height covering the room and its wall ring (x 1..17, z 3..16), like the stock
# interiors (whose plates only cover the room). The stairwell is flat too: the only thing that stands there is the
# player for the arrival step from Verity Cavern.
BDHC_RECT = (1, 3, 18, 17)    # x0, z0, x1, z1 exclusive, in tiles


def height(x, z):
    """Collision height (h) at a tile centre, or None where there is no plate."""
    x0, z0, x1, z1 = BDHC_RECT
    return FLOOR_H if x0 <= x < x1 and z0 <= z < z1 else None


if __name__ == "__main__":
    g = grid()
    for z in range(2, 18):
        print(f"{z:2d} " + " ".join({BLOCK: "##", FLOOR: "..", EXIT_MAT: "EX", STAIRS_EAST | BLOCK: "S#",
                                    STAIRS_EAST: "S>"}.get(v, f"{v:02x}") for v in g[z][0:19]))
