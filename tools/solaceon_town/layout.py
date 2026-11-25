#!/usr/bin/env python3
"""Tile layout of the redesigned Solaceon Town (overworld matrix 0, chunks map_data_072 and map_data_073).
See docs/solaceon_redesign/PLAN.md (sections 3 and 4) and docs/solaceon_redesign/layout.md.

Usage: python3 tools/solaceon_town/layout.py [--ascii] [--anchors] [--check]     (standard library only)

This file is the single source of truth for WHERE things are in the town. The graybox (build_graybox.py), the
collision (collision.py: permissions and BDHC), the warps (warps.py) and the NPC/sign spots for town-scripts are
generated from or checked against it.

Coordinates: absolute matrix tiles. x 544..607 west -> east, z 640..671 north -> south.
  map_data_072 = matrix cell (17, 20) = x 544..575;  map_data_073 = cell (18, 20) = x 576..607.
Heights h are in tiles with world y = 16 + 16 * h (the nsbmd.py / chunkedit.py convention), so the overworld ground
is h 1.0 (world y 32). The whole town is flat at h 1.0; the only other height is the stock ledge in front of the
Maniac Tunnel room (x 594..607, z 651..653, h 3.0), which is kept as stock.

Regions:
  * REBUILD rectangles: the graybox replaces the stock terrain there (the road, the whole east side, the
    excavation front and the south-west kennel yard).
  * Everything else keeps the stock terrain at BASE_REV: the Day Care ranch (with the memorial wall on x 556) and the
    Ruins hill. Their tiles copy the stock permissions and heights, except the overrides below (the north/south
    seam rows, the west edge and the Day Care trough, which the kennel yard now exposes).

Story zones (PLAN section 4): 1 pilgrim road + registration tent (north), 2 memorial plaza + garden of names
(centre), 3 Sanctuary compound (east), 4 excavation (Ruins hill), 5 ranch + kennel + loading yard (south-west),
6 believers' houses.
"""
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))

BASE_REV = "50482f890"      # stock town (with the memorial wall); every builder reads its stock inputs here
# repo paths (one place, so a port can retarget them, e.g. res/field/mapmodels/data on the macOS branch)
MAP_DATA_DIR = "res/field/maps/data"
EVENTS_JSON = "res/field/events/events_solaceon_town.json"

X0, X1, Z0, Z1 = 544, 607, 640, 671           # the two town chunks
CHUNKS = {72: (17, 20), 73: (18, 20)}         # chunk id -> matrix cell
NEIGHBOURS = {"north": (68, (17, 19)), "south": (74, (17, 21))}   # Route 210 South, Route 209
GROUND_H = 1.0

# ---- collision values (u16 per tile in map_data permissions: low byte = tile behaviour, 0x8000 = blocked) ----
BLOCK = 0x8000
WALK = 0x00
TALL_GRASS = 0x02            # TILE_BEHAVIOR_TALL_GRASS (needs an encounter table in the map header)
DOOR = 0x8069                # TILE_BEHAVIOR_DOOR, blocked: the warp fires when the player walks into it (stock)
CAVE = 0x6E                  # TILE_BEHAVIOR_WARP_NORTH, walkable: the stock Ruins entrances
TABLE = 0x8080               # TILE_BEHAVIOR_TABLE, blocked: NPCs behind it can be talked to across it
BERRY = 0x80A0               # TILE_BEHAVIOR_BERRY_PATCH, blocked (stock; the berry soil objects stand there)

# kind -> (ascii char, collision, ground texture in set 010). Building/prop shapes are drawn by build_graybox.py.
KINDS = {
    "grass":     (".", WALK, "ngrass"),
    "road":      (",", WALK, "nsand"),
    "paving":    (":", WALK, "blueglay"),
    "emblem":    ("*", WALK, "shadowchip"),
    "tallgrass": ('"', TALL_GRASS, "l_grass_m"),
    "tree":      ("T", BLOCK, "ngrass"),
    "house":     ("H", BLOCK, "ngrass"),
    "pc":        ("P", BLOCK, "ngrass"),
    "mart":      ("M", BLOCK, "ngrass"),
    "hall":      ("S", BLOCK, "blueglay"),
    "door":      ("D", DOOR, "ngrass"),
    "wall":      ("w", BLOCK, "blueglay"),
    "pillar":    ("I", BLOCK, "blueglay"),
    "gate":      ("G", WALK, "blueglay"),
    "fence":     ("f", BLOCK, "ngrass"),
    "post":      ("i", BLOCK, "nsand"),
    "lantern":   ("l", BLOCK, "blueglay"),
    "bench":     ("n", BLOCK, "blueglay"),
    "offering":  ("o", BLOCK, "blueglay"),
    "plaque":    ("q", BLOCK, "blueglay"),
    "tent":      ("t", BLOCK, "nsand"),
    "tent_floor": ("u", WALK, "nsand"),
    "table":     ("x", TABLE, "nsand"),
    "kennel":    ("k", BLOCK, "nsand"),
    "stall":     ("m", WALK, "nsand"),
    "trough":    ("r", BLOCK, "ngrass"),
    "yard":      ("y", WALK, "nsand"),
    "bay":       ("Y", WALK, "shadowchip"),
    "ruts":      ("z", WALK, "nsand"),        # wheel tracks drawn on top by build_graybox.py
    "scaffold":  ("s", BLOCK, "criff"),
    "crate":     ("C", BLOCK, "criff"),
    "worklight": ("L", BLOCK, "criff"),
    "dig":       ("_", WALK, "criff"),
    "gap":       ("g", WALK, "criff"),
    "berry":     ("b", BERRY, "nsand"),
    # stock tiles (terrain kept); the char depends on the stock value
    "stock":     ("-", None, None),
}

# ---------------------------------------------------------------------------------------------------------------
# Regions
# ---------------------------------------------------------------------------------------------------------------

# inclusive tile rectangles (x0, z0, x1, z1) where the graybox replaces the stock terrain
REBUILD = [
    (557, 640, 591, 669),     # the road, the plaza and the whole east side up to the Ruins hill
    (592, 656, 597, 663),     # the excavation front, between the Ruins cliff and its south lobe
    (545, 662, 556, 671),     # south-west: the kennel block and the loading yard
    (557, 670, 563, 671),     # the road to Route 209
]

# ---------------------------------------------------------------------------------------------------------------
# Fixed anchors (PLAN section 3) and the new ones
# ---------------------------------------------------------------------------------------------------------------

ROAD = (558, 562)                       # sand, x 558..562; grass verges x 557 and x 563 (seams walk at 557..563)
SEAM_WALK = (557, 563)                  # walkable columns at z 640 and z 671 (Route 210 South row 639, Route 209 row 672)
WALL_X, WALL_Z = 556, (652, 656)        # memorial wall signs (bg events, stock geometry from build_wall.py)
READ_X = 557                            # reading tiles x 557, z 652..656 (Indra's cutaway spot (557,654))

PC = (564, 653, 568, 656)               # stock prop 4 'pc' at (566.5, 655.0), door (566,656)
MART = (570, 663, 573, 665)             # stock prop 5 'fs' at (572.0, 665.0), door (571,665)
DAYCARE = (550, 643, 555, 645)          # stock prop 198 't4_s01' (building + shed + troughs), door (553,645)
DAYCARE_TROUGH = (545, 661, 546, 664)   # the south trough of prop 198 (visual only in stock); blocked now

PLAZA = (557, 649, 563, 660)
GARDEN = (564, 649, 568, 652)           # the garden of names: tall grass, 5 x 4
TENT = (565, 643, 567, 644)             # registration tent, 3 wide x 2 deep, open (south) front
TENT_CLERK_TILE = (566, 643)            # inside, behind the table row z 644
COMPOUND = (570, 647, 591, 658)         # Sanctuary compound: wall on the perimeter
HALL = (576, 648, 584, 652)             # Sanctuary hall, 9 wide x 5 deep, about 4 tiles tall
HALL_H = 4.0                            # tiles above the ground (walls 3, roof ridge +1)
GATE = (580, 658)                       # the compound's only gate (walkable)
GATE_PILLARS = [(579, 658), (581, 658)]
EMBLEM = (579, 654, 581, 656)           # eclipse emblem in the forecourt paving, centred on (580,655)
DIG_YARD = (592, 656, 597, 658)         # excavation yard in front of Ruins Room 1, fenced on z 659
DIG_FENCE_Z = 659
GAP = (595, 659)                        # the one gap in the excavation fence (a guard object stands here)
KENNEL = (547, 663, 554, 664)           # kennel block: back row z 663, stalls on z 664 at x 547/549/551/553
KENNEL_STALLS = [(547, 664), (549, 664), (551, 664), (553, 664)]
YARD = (547, 665, 556, 668)             # loading yard (x 556 is the yard gate onto the road)
TRUCK_BAY = (550, 666, 552, 667)        # 3 wide x 2 deep, a truck facing east (no truck in the graybox; see layout.md)
BERRIES = [(565, 663), (566, 663), (567, 663), (568, 663)]   # stock berry soil objects (data 34..37)

# houses: name -> (x0, z0) of the stock 4 x 4 house footprint (prop 197 't4_h01'); door at (x0 + 1, z0 + 3)
HOUSES = {
    "north": (569, 642),          # warp 3, MAP_HEADER_SOLACEON_TOWN_NORTH_HOUSE
    "northeast": (575, 642),      # warp 1, MAP_HEADER_SOLACEON_TOWN_NORTHEAST_HOUSE
    "east": (576, 662),           # warp 4, MAP_HEADER_SOLACEON_TOWN_EAST_HOUSE
}


def house_rect(name):
    x, z = HOUSES[name]
    return (x, z, x + 3, z + 3)


def house_door(name):
    x, z = HOUSES[name]
    return (x + 1, z + 3)


DOORS = {   # warp index -> (tile, what). Warp order in events_solaceon_town.json is fixed (interiors return by index).
    0: ((553, 645), "Day Care"),
    1: (house_door("northeast"), "Northeast House (believer's home)"),
    2: ((HALL[0] + 4, HALL[3]), "Sanctuary hall (was the News Press warp)"),
    3: (house_door("north"), "North House (believer's home)"),
    4: (house_door("east"), "East House (believer's home)"),
    5: ((566, 656), "Pokemon Center"),
    6: ((571, 665), "Poke Mart"),
    7: ((597, 652), "Ruins: Maniac Tunnel room (stock, on the h 3 ledge)"),
    8: ((595, 655), "Ruins: Room 1 (stock)"),
}

# trees: top-left tiles of 2 x 2 stock-style trees (blocked)
TREES = ([(x, 640) for x in range(564, 592, 2)] +                       # north edge
         [(573, 642)] +
         [(x, z) for x in range(580, 592, 2) for z in (642, 644)] +     # behind the compound
         [(x, 668) for x in range(566, 592, 2)] +                       # south edge (stock trees at z 670..671)
         [(586, 662), (588, 662), (590, 662), (588, 664), (590, 664), (574, 661)] +
         [(545, 665), (545, 667)] + [(x, 670) for x in range(545, 557, 2)])

BANNER_POSTS = [(557, 643), (563, 643), (557, 647), (563, 647)]
LANTERNS = [(557, 649), (557, 658), (563, 649), (563, 658), (577, 653), (583, 653)]
BENCHES = [(563, 654), (563, 655)]
OFFERINGS = [(557, 651), (557, 657)]
MEMORIAL_PLAQUE = (557, 650)
TENT_SIGN_POST = (564, 644)
CRATES = [(571, 648), (572, 648), (571, 649), (592, 658), (597, 658)]
WORKLIGHTS = [(592, 657), (597, 657)]
SCAFFOLD = [(592, 656), (593, 656), (594, 656), (596, 656), (597, 656)]

# signs: name -> (sign tile, read-from tile, facing when reading). bg_events (or signboard objects) for town-scripts.
SIGNS = {
    "TOWN_SIGN": ((564, 667), (564, 666), "north"),            # the stock map signpost OBJECT stays at (564,667)
    "SANCTUARY_GATE_PLAQUE": ((579, 658), (579, 659), "north"),
    "TENT_SIGN": (TENT_SIGN_POST, (564, 645), "north"),
    "EXCAVATION_WARNING_SIGN": ((594, 659), (594, 660), "north"),
    "KENNEL_SIGN": ((554, 664), (554, 665), "north"),
    "MEMORIAL_PLAQUE": (MEMORIAL_PLAQUE, (558, 650), "west"),   # band F only
    "BANNER_POST_NW": ((557, 643), (558, 643), "west"),         # banner / torn-banner spots
    "BANNER_POST_NE": ((563, 643), (562, 643), "east"),
    "BANNER_POST_SW": ((557, 647), (558, 647), "west"),
    "BANNER_POST_SE": ((563, 647), (562, 647), "east"),
    "WALL_652_PHOTOS": ((556, 652), (557, 652), "west"),        # the five stock 2.16a wall signs (unchanged)
    "WALL_653_PONYTA": ((556, 653), (557, 653), "west"),
    "WALL_654_ELIAS": ((556, 654), (557, 654), "west"),
    "WALL_655_BANNER": ((556, 655), (557, 655), "west"),
    "WALL_656_TEO": ((556, 656), (557, 656), "west"),
}

# NPC spots for the screenplay roles (docs/solaceon_redesign/screenplay.md "Cast by zone"): role -> (x, z, facing)
NPC_SPOTS = {
    # zone 1: pilgrim road + registration tent
    "TENT_CLERK": (566, 643, "south"),
    "PILGRIM_FATHER": (565, 645, "north"),        # the queue, front (at the table's west end)
    "PILGRIM_SAILOR": (565, 646, "north"),
    "PILGRIM_SISTER": (565, 647, "north"),
    "PILGRIM_SON": (565, 648, "north"),
    "ROAD_GREETER": (562, 645, "west"),
    # zone 2: plaza + garden of names
    "WALL_WIDOW": (558, 652, "west"),
    "GARDEN_GIRL": (563, 651, "east"),
    "LANTERN_MAN": (562, 650, "east"),
    "BELIEVER_MOTHER": (561, 656, "west"),
    "LOOKER": (558, 657, "north"),               # raid briefing (band D, progress 10), at the wall's south end
    "CYRUS": (559, 657, "north"),
    "POSTGAME_GARDEN_1": (565, 650, "south"),
    "POSTGAME_GARDEN_2": (567, 650, "south"),
    "POSTGAME_GARDEN_3": (565, 652, "west"),
    "POSTGAME_GARDEN_4": (567, 651, "west"),
    # zone 3: Sanctuary compound
    "GATE_GREETER": (581, 657, "south"),          # inside, beside the open gate
    "GATE_GRUNT_L": (579, 659, "south"),          # outside, flanking the gate; in band D one steps onto (580,659)
    "GATE_GRUNT_R": (581, 659, "south"),
    "FORECOURT_SWEEPER": (582, 656, "west"),
    "IP_OFFICER_GATE": (581, 659, "south"),
    "IP_OFFICER_COURT": (575, 655, "east"),
    # zone 4: excavation
    "DIG_WORKER": (593, 657, "north"),
    "EXCAVATION_GRUNT_M": (595, 659, "south"),    # ON the gap: blocks it. Sight line south: (595,660..663)
    "EXCAVATION_GRUNT_F": (596, 660, "west"),     # beside the gap. Sight line west: (595,660), (594,660), ...
    "RUIN_MANIAC": (593, 661, "north"),
    "IP_OFFICER_DIG": (596, 660, "west"),
    "CYRUS_AT_FENCE": (597, 662, "west"),         # after the briefing, a few tiles from the dig pair, facing it
    # zone 5: ranch, kennel, loading yard
    "KENNEL_KEEPER": (555, 665, "west"),
    "KENNEL_MON_1": (547, 664, "south"),
    "KENNEL_MON_2": (549, 664, "south"),
    "KENNEL_MON_3": (551, 664, "south"),
    "KENNEL_MON_4": (553, 664, "south"),
    "LOADING_GRUNT": (553, 668, "north"),
    "RANCHER": (554, 648, "south"),               # Day Care yard (stock terrain)
    "DAYCARE_KID": (552, 647, "east"),
    # zone 6: believers' houses
    "SUNDAY_MAN": (573, 644, "south"),
    "DOUBTER": (579, 666, "west"),
    "POKETCH_MAN": (579, 644, "south"),
}
# where the excavation pair step aside after the raid battles, leaving the gap and its approach (595,660) free:
# F steps east one tile; M steps south off the gap and then east (two steps). Both tiles are walkable dirt.
GRUNT_ASIDE = {"EXCAVATION_GRUNT_M": (596, 661), "EXCAVATION_GRUNT_F": (597, 660)}

# ---------------------------------------------------------------------------------------------------------------
# Stock input (BASE_REV)
# ---------------------------------------------------------------------------------------------------------------

_cache = {}


def git_file(rel, rev=BASE_REV):
    key = (rev, rel)
    if key not in _cache:
        _cache[key] = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{rel}"], check=True,
                                     capture_output=True).stdout
    return _cache[key]


def chunk_rel(c):
    return f"{MAP_DATA_DIR}/map_data_{c:03d}.bin"


def _sections(raw):
    sizes = struct.unpack_from("<4I", raw)
    o, out = 16, []
    for s in sizes:
        out.append(raw[o:o + s])
        o += s
    return out


def stock_perm(c):
    """Stock permissions of chunk c at BASE_REV -> 32 x 32 [z][x]."""
    v = struct.unpack("<1024H", _sections(git_file(chunk_rel(c)))[0])
    return [list(v[z * 32:(z + 1) * 32]) for z in range(32)]


def stock_heights(c):
    """Stock BDHC height (tiles, h) at each tile centre of chunk c -> 32 x 32 [z][x] (None = no plate)."""
    if os.path.join(ROOT, "tools", "lake_verity") not in sys.path:
        sys.path.append(os.path.join(ROOT, "tools", "lake_verity"))
    import mapdata
    b = mapdata.read_bdhc(_sections(git_file(chunk_rel(c)))[3])
    out = []
    for lz in range(32):
        row = []
        for lx in range(32):
            h = mapdata.height_at(b, *mapdata.tile_centre(lx, lz), current=32 * 4096)
            row.append(None if h is None else (h / 4096 - 16) / 16)
        out.append(row)
    return out


def in_rect(r, x, z):
    return r[0] <= x <= r[2] and r[1] <= z <= r[3]


def rebuilt(x, z):
    return any(in_rect(r, x, z) for r in REBUILD)


# ---------------------------------------------------------------------------------------------------------------
# The tile map
# ---------------------------------------------------------------------------------------------------------------

def tiles():
    """-> {(x, z): (collision, h, kind)} for x 544..607, z 640..671."""
    if "tiles" in _cache:
        return _cache["tiles"]
    out = {}
    # stock everywhere first
    for c, (cx, cz) in CHUNKS.items():
        p, hs = stock_perm(c), stock_heights(c)
        for lz in range(32):
            for lx in range(32):
                out[(cx * 32 + lx, cz * 32 + lz)] = (p[lz][lx], hs[lz][lx], "stock")

    def put(x, z, kind, h=GROUND_H):
        out[(x, z)] = (KINDS[kind][1], float(h), kind)

    def fill(r, kind):
        for x in range(r[0], r[2] + 1):
            for z in range(r[1], r[3] + 1):
                put(x, z, kind)

    # base ground of the rebuilt regions
    for r in REBUILD:
        fill(r, "grass")
    fill((ROAD[0], Z0, ROAD[1], Z1), "road")
    # zone 2: plaza (paved across the road), garden of names
    fill(PLAZA, "paving")
    for z in range(WALL_Z[0], WALL_Z[1] + 1):
        put(READ_X, z, "paving")
    fill(GARDEN, "tallgrass")
    for t in LANTERNS[:4]:
        put(*t, "lantern")
    for t in BENCHES:
        put(*t, "bench")
    for t in OFFERINGS:
        put(*t, "offering")
    put(*MEMORIAL_PLAQUE, "plaque")
    fill((564, 657, 569, 658), "paving")          # in front of the Pokemon Center
    # lanes and the street
    fill((564, 646, 579, 646), "road")            # north lane: tent, North and Northeast houses
    fill((569, 647, 569, 658), "road")            # alley between the Pokemon Center and the compound
    fill((564, 659, 591, 660), "road")            # street: plaza -> Sanctuary gate -> excavation
    fill((564, 666, 585, 666), "road")            # south lane: Mart, East House
    # zone 1: tent, banner posts
    fill((564, 642, 568, 642), "fence")           # behind the tent
    put(564, 643, "fence")
    put(TENT[0], TENT[1], "tent")
    put(TENT[0] + 1, TENT[1], "tent_floor")
    put(TENT[2], TENT[1], "tent")
    for x in range(TENT[0], TENT[2] + 1):
        put(x, TENT[3], "table")
    put(*TENT_SIGN_POST, "post")
    for t in BANNER_POSTS:
        put(*t, "post")
    # zone 3: the compound
    x0, z0, x1, z1 = COMPOUND
    fill((x0 + 1, z0 + 1, x1 - 1, z1 - 1), "paving")
    for x in range(x0, x1 + 1):
        put(x, z0, "wall")
        put(x, z1, "wall")
    for z in range(z0, z1 + 1):
        put(x0, z, "wall")
        put(x1, z, "wall")
    put(*GATE, "gate")
    for t in GATE_PILLARS:
        put(*t, "pillar")
    fill(HALL, "hall")
    put(*DOORS[2][0], "door")
    fill(EMBLEM, "emblem")
    for t in LANTERNS[4:]:
        put(*t, "lantern")
    # zone 4: excavation
    fill(DIG_YARD, "dig")
    fill((592, 660, 597, 663), "dig")
    for x in range(DIG_YARD[0], DIG_YARD[2] + 1):
        put(x, DIG_FENCE_Z, "fence")
    put(*GAP, "gap")
    for t in SCAFFOLD:
        put(*t, "scaffold")
    for t in WORKLIGHTS:
        put(*t, "worklight")
    # zone 5: kennel and loading yard
    fill((547, 662, 556, 662), "fence")
    fill(YARD, "yard")
    fill(KENNEL, "kennel")
    for t in KENNEL_STALLS:
        put(*t, "stall")
    fill(TRUCK_BAY, "bay")
    fill((553, 666, 556, 667), "ruts")
    fill((545, 669, 556, 669), "fence")
    for z in (663, 664):
        put(556, z, "fence")
    fill(DAYCARE_TROUGH, "trough")
    # zone 6 + fixed buildings
    for name in HOUSES:
        fill(house_rect(name), "house")
        put(*house_door(name), "door")
    fill(PC, "pc")
    put(566, 656, "door")
    fill(MART, "mart")
    put(571, 665, "door")
    fill((564, 662, 569, 662), "fence")           # the berry patch's fence (as stock)
    put(564, 663, "fence")
    put(569, 663, "fence")
    for t in BERRIES:
        put(*t, "berry")
    for x, z in TREES:
        for dx in (0, 1):
            for dz in (0, 1):
                put(x + dx, z + dz, "tree")
    for t in CRATES:
        put(*t, "crate")
    # edges: west column and the seam rows blocked except the road (stock terrain stays drawn)
    for z in range(Z0, Z1 + 1):
        if out[(X0, z)][0] & BLOCK == 0:
            out[(X0, z)] = (BLOCK, out[(X0, z)][1], out[(X0, z)][2])
    for z in (Z0, Z1):
        for x in range(X0, X1 + 1):
            if not SEAM_WALK[0] <= x <= SEAM_WALK[1] and out[(x, z)][0] & BLOCK == 0:
                out[(x, z)] = (BLOCK, out[(x, z)][1], out[(x, z)][2])
    _cache["tiles"] = out
    return out


def stock_char(v, h):
    if v & BLOCK:
        return {0x69: "D", 0x3B: "v"}.get(v & 0xFF, "#")
    if (v & 0xFF) == CAVE:
        return "E"
    if (v & 0xFF) == 0x16:
        return "~"
    return "^" if h is not None and h > GROUND_H + 0.5 else "-"


def char(t):
    coll, h, kind = t
    if kind == "stock":
        return stock_char(coll, h)
    return KINDS[kind][0]


def ascii_map(t=None, x0=X0, x1=X1):
    t = t or tiles()
    lines = ["      " + "".join(str(x // 10 % 10) for x in range(x0, x1 + 1)),
             "      " + "".join(str(x % 10) for x in range(x0, x1 + 1))]
    for z in range(Z0, Z1 + 1):
        lines.append(f"{z:4d}  " + "".join(char(t[(x, z)]) for x in range(x0, x1 + 1)))
    return "\n".join(lines)


LEGEND = """legend:  . grass   , road (sand)   : paving   * emblem paving   " tall grass (garden of names, encounters)
         T tree   H house   P Pokemon Center   M Mart   S Sanctuary hall   D door (warp)   w compound wall
         I gate pillar   G gate   f fence   i post (banner / sign)   l lantern   n bench   o offerings
         q memorial plaque   t tent   u tent floor (clerk)   x tent table (talk across)   k kennel   m kennel stall
         r trough   y loading yard   Y truck bay   z ruts   s scaffolding   C crates   L work light   _ dig dirt
         g fence gap (guard)   b berry patch
         stock terrain kept:  - walkable   # blocked   ~ puddle   v ledge   E Ruins entrance   ^ raised (h 3) walkable"""


# ---------------------------------------------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------------------------------------------

def walkable(t, x, z):
    v = t.get((x, z))
    return v is not None and not v[0] & BLOCK


def reachable(t=None, start=(560, 640)):
    """Tiles the player can walk to from the north road entrance (4-neighbour flood fill over walkable tiles of equal
    height). Cave entrances count as reachable tiles."""
    t = t or tiles()
    seen = {start}
    todo = [start]
    while todo:
        x, z = todo.pop()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n in seen or not walkable(t, *n):
                continue
            if abs((t[n][1] or 0) - (t[(x, z)][1] or 0)) > 0.01:
                continue
            seen.add(n)
            todo.append(n)
    return seen


def checks():
    """-> [(description, ok)]."""
    t = tiles()
    res = []
    reach = reachable(t)
    # fixed anchors
    for i, ((x, z), what) in DOORS.items():
        v = t[(x, z)][0]
        want = CAVE if i in (7, 8) else DOOR
        res.append((f"warp {i} {what} door tile ({x},{z}) has behaviour {want:#x}", v == want))
        front = (x, z + 1)
        if i == 7:
            res.append((f"warp 7 Maniac Tunnel door ({x},{z}) is on the stock h 3 ledge (left as stock, not reachable "
                        f"from town)", abs(t[(x, z)][1] - 3.0) < 1e-6))
        elif i == 8:
            res.append((f"warp 8 Room 1 ({x},{z}) is reachable from town", (x, z) in reach))
        else:
            res.append((f"warp {i} door ({x},{z}): the tile in front ({front[0]},{front[1]}) is reachable",
                        front in reach))
    res.append(("Pokemon Center door at (566,656), Mart door at (571,665), Day Care door at (553,645)",
                DOORS[5][0] == (566, 656) and DOORS[6][0] == (571, 665) and DOORS[0][0] == (553, 645)))
    res.append(("fly / blackout landing (566,657) (src/unk_0203A7D8.c: 0x236, 0x291) walkable and reachable",
                (566, 657) in reach))
    res.append(("hall is 9 wide x 5 deep, door in the middle of the south face",
                HALL[2] - HALL[0] + 1 == 9 and HALL[3] - HALL[1] + 1 == 5 and DOORS[2][0] == (HALL[0] + 4, HALL[3])))
    res.append(("tent footprint is 3 wide x 2 deep", TENT[2] - TENT[0] + 1 == 3 and TENT[3] - TENT[1] + 1 == 2))
    gw, gd = GARDEN[2] - GARDEN[0] + 1, GARDEN[3] - GARDEN[1] + 1
    res.append((f"garden of names {gw} x {gd} tall grass (4x3 .. 6x4)",
                4 <= gw <= 6 and 3 <= gd <= 4 and all(t[(x, z)][0] == TALL_GRASS
                                                      for x in range(GARDEN[0], GARDEN[2] + 1)
                                                      for z in range(GARDEN[1], GARDEN[3] + 1))))
    res.append(("garden of names reachable", any((x, z) in reach for x in range(GARDEN[0], GARDEN[2] + 1)
                                                 for z in range(GARDEN[1], GARDEN[3] + 1))))
    wall = [(WALL_X, z) for z in range(WALL_Z[0], WALL_Z[1] + 1)]
    read = [(READ_X, z) for z in range(WALL_Z[0], WALL_Z[1] + 1)]
    res.append(("memorial wall x 556 z 652..656 blocked (stock terrain kept)",
                all(t[w][0] & BLOCK and t[w][2] == "stock" for w in wall)))
    res.append(("reading tiles x 557 z 652..656 walkable and reachable", all(r in reach for r in read)))
    # gap
    fence_row = [(x, DIG_FENCE_Z) for x in range(DIG_YARD[0], DIG_YARD[2] + 1)]
    res.append(("excavation fence z 659 x 592..597 blocked except the one gap (595,659)",
                [p for p in fence_row if walkable(t, *p)] == [GAP]))
    t2 = dict(t)
    t2[GAP] = (BLOCK, t[GAP][1], "fence")
    r2 = reachable(t2)
    res.append(("Ruins Room 1 (595,655) is reachable only through the gap (guard on the gap blocks it)",
                (595, 655) in reach and (595, 655) not in r2))
    # the compound
    t3 = dict(t)
    t3[GATE] = (BLOCK, t[GATE][1], "wall")
    r3 = reachable(t3)
    res.append(("the hall door is reachable only through the compound gate", (580, 653) in reach and (580, 653) not in r3))
    # seams and edges
    for side, (c, cell) in NEIGHBOURS.items():
        p, hs = stock_perm(c), stock_heights(c)
        lz, z = (31, Z0) if side == "north" else (0, Z1)
        bad = []
        for lx in range(32):
            x = cell[0] * 32 + lx
            nw = not p[lz][lx] & BLOCK
            mw = walkable(t, x, z)
            if nw != mw or (mw and abs(hs[lz][lx] - t[(x, z)][1]) > 1e-6):
                bad.append(x)
        res.append((f"{side} seam z {z} matches map_data_{c:03d} (walkability and height, x 544..575)", not bad))
    res.append(("z 640 / z 671 of map_data_073 blocked (filler map_data_176 beyond)",
                not any(walkable(t, x, z) for x in range(576, 608) for z in (Z0, Z1))))
    res.append(("west edge x 544 and east edge x 607 blocked",
                not any(walkable(t, x, z) for x in (X0, X1) for z in range(Z0, Z1 + 1))))
    res.append(("seam roads x 557..563 walkable at z 640 and z 671",
                all(walkable(t, x, z) for x in range(557, 564) for z in (Z0, Z1))))
    # signs and NPC spots
    for name, (sign, frm, facing) in SIGNS.items():
        if name == "TOWN_SIGN":     # an object (stock map signpost): stands on a walkable tile, talked to
            res.append((f"sign {name} object at {sign} on a walkable tile, read from {frm}",
                        walkable(t, *sign) and frm in reach))
            continue
        ok = t[sign][0] & BLOCK and frm in reach
        res.append((f"sign {name} at {sign} is blocked and its read tile {frm} reachable", bool(ok)))
    for role, (x, z, facing) in NPC_SPOTS.items():
        res.append((f"NPC spot {role} ({x},{z}) walkable and reachable" if role not in ("TENT_CLERK",) + tuple(
            k for k in NPC_SPOTS if k.startswith("KENNEL_MON")) else
            f"NPC spot {role} ({x},{z}) walkable (behind a table / in a stall)", walkable(t, x, z) and
            ((x, z) in reach or role == "TENT_CLERK" or role.startswith("KENNEL_MON"))))
    res.append(("tent clerk can be talked to across the table from (566,645)",
                t[(566, 644)][0] == TABLE and (566, 645) in reach and walkable(t, *TENT_CLERK_TILE)))
    stall_ok = all((x, z + 1) in reach and walkable(t, x, z) for x, z in KENNEL_STALLS)
    res.append(("each kennel stall can be talked to from the yard", stall_ok))
    res.append(("berry patches (565..568,663) kept, reachable from the south",
                all(t[b][0] == BERRY and (b[0], b[1] + 1) in reach for b in BERRIES)))
    res.append(("truck bay walkable and reachable", all((x, z) in reach for x in range(TRUCK_BAY[0], TRUCK_BAY[2] + 1)
                                                         for z in range(TRUCK_BAY[1], TRUCK_BAY[3] + 1))))
    # nothing walkable in the rebuilt regions is cut off (field obstacles would only be trees here: none planned)
    cut = [k for k, v in t.items() if rebuilt(*k) and not v[0] & BLOCK and k not in reach and k != TENT_CLERK_TILE]
    res.append((f"every walkable rebuilt tile is reachable from the road (unreachable: {cut[:6]})", not cut))
    return res


def events_on_blocked():
    """Existing object/bg events of events_solaceon_town.json (at BASE_REV) that would sit on a blocked tile, or block
    a 1-wide passage, in the new layout (for town-scripts)."""
    t = tiles()
    ev = json.loads(git_file(EVENTS_JSON))
    out = []
    for o in ev["object_events"]:
        p = (o["x"], o["z"])
        if p in t and not walkable(t, *p) and not (o["graphics_id"] == "OBJ_EVENT_GFX_UNK_100" and p in BERRIES):
            out.append(f"object {o['id']} at {p}: now {t[p][2]}")
    return out


def main():
    if "--ascii" in sys.argv or len(sys.argv) == 1:
        print(ascii_map())
        print(LEGEND)
    if "--anchors" in sys.argv:
        for i, (tile, what) in DOORS.items():
            print(f"warp {i}: {tile} {what}")
        for k, v in SIGNS.items():
            print(f"sign {k}: {v}")
        for k, v in NPC_SPOTS.items():
            print(f"npc {k}: {v}")
    if "--check" in sys.argv:
        bad = 0
        for desc, ok in checks():
            print(("PASS " if ok else "FAIL ") + desc)
            bad += not ok
        for line in events_on_blocked():
            print("note: existing " + line)
        print(f"{bad} failed")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
