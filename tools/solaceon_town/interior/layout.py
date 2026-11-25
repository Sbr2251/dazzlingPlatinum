#!/usr/bin/env python3
"""The Sanctuary hall (MAP_HEADER_SOLACEON_SANCTUARY): the tile contract shared by the art script
(art/sanctuary_interior.py), build_interior.py and the town-scripts workstream (events, scripts). Standard library
only. Run it to print the map.

The map is one chunk (map group 296 = [[MAP_680]]), so chunk-local tiles are absolute tiles (x east, z south). As in
the stock interiors (Hearthome's Foreign Building, map_data_244; the Eterna Galactic building, map_data_333) the
rooms sit in the north-west of the chunk; every tile outside them is blocked. The floor collision is at world y 0
(h = -1 in the mesh.json convention world y = 16 + 16 h); the drawn floor is 1/8 tile lower (h -1.125), as stock.

Rooms:
    public hall        x 2..18, z 7..19 (17 x 13), symmetric about x 10.5; the entrance (exit mat) at (10, 19)
    records office     x 20..25, z 7..13 (6 x 7), Indra's; reached through the doorway (19, 13)
    walls              north wall row z 6 (the hall's is 7 tiles tall and carries the photo-card boards, the eclipse
                       emblem and the locked back door); the hall/office wall is column x 19 (z 6..12); the open
                       south edges (z 20 under the hall, z 14 under the office) and the outer sides (x 1, x 26) are
                       blocked and drawn black, like the stock interiors
Furniture is terrain (blocked tiles): six pews, the speaker's lectern (a TABLE tile, so the speaker behind it can be
talked to across it), two candelabra, the guest book, two lily vases, the office shelves, desk, cabinet and card boxes.
"""

BLOCK = 0x8000
FLOOR = 0x00                  # plain indoor floor, no encounters
EXIT_MAT = 0x65               # TILE_BEHAVIOR_WARP_ENTRANCE_SOUTH: the stock indoor exit mat, fires on pressing south
TABLE = 0x80                  # TILE_BEHAVIOR_TABLE: talking to the facing tile reaches the object one tile beyond

FLOOR_H = -1.0                # collision height (h) of every walkable tile (world y 0)
DRAWN_FLOOR_H = -1.125        # the drawn floor, as stock (rugs sit at -1.0)

HALL = (2, 7, 18, 19)         # x0, z0, x1, z1 inclusive
OFFICE = (20, 7, 25, 13)
DOORWAY = (19, 13)            # hall <-> office; one tile, so one object event blocks it (see OFFICE_BLOCKER)
NORTH_WALL_Z = 6              # wall row; the drawn wall faces are at z 6.625 (3/8 tile into the row, as stock)
INNER_WALL_X = 19             # hall/office wall column, z 6..12

EXIT_TILE = (10, 19)          # warp 0; the player arrives on it from Solaceon Town warp 2
ARRIVAL_TILE = EXIT_TILE

# furniture (blocked); value = behaviour low byte
LECTERN = (10, 9)             # TABLE
CANDELABRA = ((8, 9), (12, 9))
PEW_ROWS = (11, 13, 15)
PEW_SPANS = ((5, 8), (12, 15))            # x0, x1 inclusive, west and east of the aisle x 9..11
GUEST_BOOK = (6, 18)
VASES = ((2, 19), (18, 19))
SHELVES = ((20, 7), (21, 7), (22, 7), (24, 7), (25, 7))
DESK_LEDGER = (22, 10)        # the half of the desk with the ledger (plain blocked: its sign is read here)
DESK_TABLE = (23, 10)         # TABLE: Indra behind it at (23, 9) can be talked to across the desk
CABINET = (25, 9)
CARD_BOXES = ((24, 13), (25, 13), (25, 12))

# warp_events of events_solaceon_sanctuary.json, in order: (tile, dest header, dest warp)
WARPS = (
    (EXIT_TILE, "MAP_HEADER_SOLACEON_TOWN", 2),
)

# NPC spots (walkable tiles) for the town-scripts workstream: name -> (x, z, facing)
NPC_SPOTS = {
    "SPEAKER": (10, 8, "south"),        # the Eclipse speaker, behind the lectern
    "BELIEVER_A": (6, 12, "north"),     # in the pew rows, facing the emblem
    "BELIEVER_B": (14, 12, "north"),
    "BELIEVER_C": (7, 14, "north"),
    "BELIEVER_D": (13, 16, "north"),
    "MOURNER": (4, 7, "north"),         # at the west photo board
    "GREETER": (7, 18, "east"),         # by the guest book, facing the aisle
    "INDRA": (23, 9, "south"),          # behind her desk
}
# The office doorway is one tile: an object event standing on it blocks the office (see interior.md)
OFFICE_BLOCKER = DOORWAY

# bg_event tiles (all blocked; read from the tile in front, facing as given): name -> ([(x, z)], (read x, z), facing)
SIGNS = {
    "PHOTO_BOARD_WEST": ([(3, 6), (4, 6), (5, 6), (6, 6)], (4, 7), "north"),
    "EMBLEM": ([(9, 6), (10, 6), (11, 6)], (10, 7), "north"),
    "PHOTO_BOARD_EAST": ([(14, 6), (15, 6), (16, 6), (17, 6)], (16, 7), "north"),
    "BACK_DOOR": ([(18, 6)], (18, 7), "north"),          # the locked back door (visual only)
    "SCONCE": ([(2, 6)], (2, 7), "north"),
    "LECTERN": ([LECTERN], (10, 10), "north"),           # TABLE tile: an object behind it is talked to first
    "GUEST_BOOK": ([GUEST_BOOK], (6, 17), "south"),
    "SHELVES": (list(SHELVES), (21, 8), "north"),
    "SINNOH_MAP": ([(23, 6)], (23, 7), "north"),
    "LEDGER": ([DESK_LEDGER], (22, 11), "north"),
    "CABINET": ([CABINET], (24, 9), "east"),
    "CARD_BOXES": (list(CARD_BOXES), (24, 12), "south"),
}

EXIT_MAT_MODEL = 78           # stock exit mat prop (area_build model 78, d_mat01), in props list 21


def in_rect(r, x, z):
    return r[0] <= x <= r[2] and r[1] <= z <= r[3]


def blocked_furniture():
    out = {LECTERN: TABLE, DESK_TABLE: TABLE}
    for t in CANDELABRA + VASES + SHELVES + CARD_BOXES + (GUEST_BOOK, DESK_LEDGER, CABINET):
        out[t] = 0
    for z in PEW_ROWS:
        for x0, x1 in PEW_SPANS:
            for x in range(x0, x1 + 1):
                out[(x, z)] = 0
    return out


FURNITURE = blocked_furniture()


def walkable(x, z):
    return (in_rect(HALL, x, z) or in_rect(OFFICE, x, z) or (x, z) == DOORWAY) and (x, z) not in FURNITURE


def collision(x, z):
    """Permission value of chunk tile (x, z)."""
    if (x, z) == EXIT_TILE:
        return EXIT_MAT
    if walkable(x, z):
        return FLOOR
    return BLOCK | FURNITURE.get((x, z), 0)


def grid():
    """32 x 32 [z][x] permission values."""
    return [[collision(x, z) for x in range(32)] for z in range(32)]


# BDHC: one flat plate at the floor height over both rooms and their wall ring, like the stock interiors
BDHC_RECT = (1, 6, 27, 21)    # x0, z0, x1, z1 exclusive, in tiles


def height(x, z):
    """Collision height (h) at a tile centre, or None where there is no plate."""
    x0, z0, x1, z1 = BDHC_RECT
    return FLOOR_H if x0 <= x < x1 and z0 <= z < z1 else None


def ascii_map():
    marks = {}
    for name, (x, z, _) in NPC_SPOTS.items():
        marks[(x, z)] = {"SPEAKER": "Sp", "INDRA": "In", "MOURNER": "Mo", "GREETER": "Gr"}.get(name, "B" + name[-1])
    marks[DOORWAY] = "DD"
    marks[EXIT_TILE] = "EX"
    names = {"PHOTO_BOARD_WEST": "Pw", "EMBLEM": "Em", "PHOTO_BOARD_EAST": "Pe", "BACK_DOOR": "Dr", "SCONCE": "Sc",
             "SHELVES": "Sh", "SINNOH_MAP": "Ma", "CABINET": "Cb", "CARD_BOXES": "Bx", "GUEST_BOOK": "GB",
             "LEDGER": "Lg", "LECTERN": "Lc"}
    for name, (tiles, _, _) in SIGNS.items():
        for t in tiles:
            marks.setdefault(t, names[name])
    furn = {t: "pw" for z in PEW_ROWS for x0, x1 in PEW_SPANS for t in [(x, z) for x in range(x0, x1 + 1)]}
    furn.update({t: "ca" for t in CANDELABRA})
    furn.update({t: "va" for t in VASES})
    furn[DESK_TABLE] = "Dk"
    lines = ["    x " + " ".join(f"{x:2d}" for x in range(1, 27))]
    for z in range(5, 21):
        row = []
        for x in range(1, 27):
            v = collision(x, z)
            m = marks.get((x, z)) or furn.get((x, z))
            row.append(m if m else ("##" if v & BLOCK else ".."))
        lines.append(f"z {z:2d}  " + " ".join(row))
    return "\n".join(lines)


if __name__ == "__main__":
    print(ascii_map())
