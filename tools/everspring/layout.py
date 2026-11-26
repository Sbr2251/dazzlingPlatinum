#!/usr/bin/env python3
"""Tile layout of the redesigned Route 218 — Everspring Sanctuary (Crescent Fairy Glade).

Chunks: map_data_050 (matrix col 2, row 23: x=64..95, z=736..767)
        map_data_051 (matrix col 3, row 23: x=96..127, z=736..767)
Contract: docs/everspring_redesign/PLAN.md

Usage:
  python3 tools/everspring/layout.py --ascii --check
  python3 tools/everspring/layout.py --anchors
"""
import math
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))

MAP_DATA_DIR = "res/field/mapmodels/data"
X0, X1, Z0, Z1 = 64, 127, 736, 767
CHUNKS = {50: (2, 23), 51: (3, 23)}  # chunk id -> (matrix_col, matrix_row)

# Heights in tiles (world_y = 16.0 + 16.0 * h, matching stock map_data_050/051)
GROUND_H = 0.0   # world y = 16.0
WATER_H = -0.5   # world y = 8.0

# Tile permission values (u16: low byte = TileBehavior, 0x8000 = blocked)
BLOCK = 0x8000
WALK = 0x0000
TALL_GRASS = 0x0002          # TILE_BEHAVIOR_TALL_GRASS
WATER = 0x0015               # TILE_BEHAVIOR_WATER_SEA (Surfable)
WATER_BLOCK = 0x8015         # Decorative/railing-adjacent water (impassable even with Surf)
WARP_WEST = 0x006D           # TILE_BEHAVIOR_WARP_WEST (109, Canalave Gate)
WARP_EAST = 0x006C           # TILE_BEHAVIOR_WARP_EAST (108, Jubilife Gate)

# Tile kind -> (ascii char, permission u16, height h)
KINDS = {
    "grass":        (".", WALK,        GROUND_H),
    "cobble":       (",", WALK,        GROUND_H),
    "plaza":        (":", WALK,        GROUND_H),
    "plaza_edge":   (";", WALK,        GROUND_H),  # Surf landing moonstone steps
    "tallgrass":    ('"', TALL_GRASS,  GROUND_H),
    "spiral_grass": ("*", TALL_GRASS,  GROUND_H),  # Spiral Blossom Meadow tall grass
    "spiral_flw":   ("o", WALK,        GROUND_H),  # Glowing spiral blossom clearing
    "bridge":       ("=", WALK,        GROUND_H),  # West Arched Moonbridge
    "pier":         ("-", WALK,        GROUND_H),  # East Lantern Overlook Pier
    "water":        ("~", WATER,       WATER_H),   # Surfable lagoon water
    "water_block":  ("^", WATER_BLOCK, WATER_H),   # Decorative / railing-guarded water
    "warp_w":       ("W", WARP_WEST,   GROUND_H),  # Canalave Gate warp (70, 754..755)
    "warp_e":       ("E", WARP_EAST,   GROUND_H),  # Jubilife Gate warp (121, 758..759)
    "fountain":     ("F", BLOCK,       GROUND_H),  # Gardevoir Fountain 4x4 (93..96, 749..752)
    "crystal":      ("C", BLOCK,       GROUND_H),  # Rift Conduit Crystal 2x1 (98..99, 747)
    "tree":         ("T", BLOCK,       GROUND_H),  # Sakura / Wisteria blossom tree
    "cliff":        ("#", BLOCK,       GROUND_H),  # Mossy moonstone border cliff/hedge
    "mushroom":     ("m", BLOCK,       GROUND_H),  # Glowing fairy mushroom cluster
    "lantern":      ("l", BLOCK,       GROUND_H),  # Fairy lantern post
    "gate_pad":     ("G", BLOCK,       GROUND_H),  # Behind gatehouse props (model 40)
}

# ---------------------------------------------------------------------------
# Single Source of Truth: Exact Anchor Coordinates (PLAN.md Section 3)
# ---------------------------------------------------------------------------

GATE_WEST_WARPS = [(70, 754), (70, 755)]
GATE_EAST_WARPS = [(121, 758), (121, 759)]

# Gardevoir Fountain (4x4 blocked) & standing tiles
FOUNTAIN_RECT = (93, 749, 96, 752)
FOUNTAIN_BG_EVENTS = [(94, 752), (95, 752)]
FOUNTAIN_STAND_TILES = [(94, 753), (95, 753)]

# Rift Conduit Crystal Pillar (2x1 blocked) & standing tiles
CRYSTAL_RECT = (98, 747, 99, 747)
CRYSTAL_BG_EVENTS = [(98, 747), (99, 747)]
CRYSTAL_STAND_TILES = [(98, 748), (99, 748)]

# Major zone rectangles (inclusive x0, z0, x1, z1)
WEST_BRIDGE_RECT = (83, 752, 87, 754)
CENTRAL_ISLAND_RECT = (88, 745, 101, 758)
EAST_SURF_LANDING = [(101, z) for z in range(751, 755)]
EAST_SURF_CHANNEL = (102, 746, 106, 759)
EAST_PIER_RECT = (107, 752, 111, 754)
SPIRAL_MEADOW_CENTER = (81.0, 760.0)

# Coord event: Route218_RivalScene (x=89, z=756, w=11, l=2 -> x=89..99, z=756..757)
RIVAL_COORD_EVENT_RECT = (89, 756, 99, 757)

# Object events (all sit on walkable ground tiles)
ANCHORS = {
    "LOCALID_EVERSPRING_RIVAL":         (95, 755),
    "LOCALID_RIFT_RESEARCHER":          (90, 748),
    "LOCALID_EVERSPRING_CLEFAIRY_WEST": (81, 760),
    "LOCALID_EVERSPRING_CLEFAIRY_EAST": (110, 748),
    "LOCALID_EVERSPRING_ITEM_WEST":     (77, 745),
    "LOCALID_EVERSPRING_ITEM_EAST":     (114, 745),
    "LOCALID_EVERSPRING_SIGN_WEST":     (73, 753),
    "LOCALID_EVERSPRING_SIGN_EAST":     (119, 757),
}

WEST_FOOT_ANCHORS = [
    "LOCALID_EVERSPRING_RIVAL",
    "LOCALID_RIFT_RESEARCHER",
    "LOCALID_EVERSPRING_CLEFAIRY_WEST",
    "LOCALID_EVERSPRING_ITEM_WEST",
    "LOCALID_EVERSPRING_SIGN_WEST",
]

EAST_FOOT_ANCHORS = [
    "LOCALID_EVERSPRING_CLEFAIRY_EAST",
    "LOCALID_EVERSPRING_ITEM_EAST",
    "LOCALID_EVERSPRING_SIGN_EAST",
]

# Stock gatehouse props kept verbatim (model 40 = gate_b)
# map_data_050: prop 1 at world (67.0, h=0.0, 755.0) -> raw_pos [-851968, 65536, 196608]
# map_data_051: prop 0 at world (125.0, h=0.0, 759.0) -> raw_pos [851968, 65536, 458752]
GATE_PROPS = {
    50: [dict(model=40, pos=[-851968, 65536, 196608], rot=[0, 0, 0], scale=[4096, 4096, 4096], dummy=[0, 0])],
    51: [dict(model=40, pos=[851968, 65536, 458752], rot=[0, 0, 0], scale=[4096, 4096, 4096], dummy=[0, 0])],
}


def in_rect(r, x, z):
    return r[0] <= x <= r[2] and r[1] <= z <= r[3]


def spiral_field(x, z):
    """3-arm logarithmic spiral blossom field centered at (81.0, 760.0): sin(3*theta - 1.55*r)."""
    dx = x + 0.5 - SPIRAL_MEADOW_CENTER[0]
    dz = z + 0.5 - SPIRAL_MEADOW_CENTER[1]
    r = math.hypot(dx, dz)
    theta = math.atan2(dz, dx)
    return math.sin(3.0 * theta - 1.55 * r)


def is_island_octagon(x, z):
    """Octagonal Central Gardevoir Fountain Island: x=88..101, z=745..758 with 2-tile chamfered corners."""
    x0, z0, x1, z1 = CENTRAL_ISLAND_RECT
    if not (x0 <= x <= x1 and z0 <= z <= z1):
        return False
    # 2-tile chamfer on all 4 corners (clips 3 tiles per corner -> crisp octagon)
    # Keeps (89, 756..757) and (99, 756..757) and (90, 748) and (98..99, 747) strictly inside!
    if (x - x0) + (z - z0) < 2:
        return False
    if (x1 - x) + (z - z0) < 2:
        return False
    if (x - x0) + (z1 - z) < 2:
        return False
    if (x1 - x) + (z1 - z) < 2:
        return False
    return True


_CACHE = {}


def tiles():
    """Return {(x, z): (perm_u16, h, kind)} for x=64..127, z=736..767."""
    if "tiles" in _CACHE:
        return _CACHE["tiles"]

    grid = {}

    def put(x, z, kind):
        _, perm, h = KINDS[kind]
        grid[(x, z)] = (perm, h, kind)

    def fill(rect, kind):
        for x in range(rect[0], rect[2] + 1):
            for z in range(rect[1], rect[3] + 1):
                put(x, z, kind)

    # 1. Start with deep border forest / trees everywhere
    fill((X0, Z0, X1, Z1), "tree")

    # 2. Crescent Moonlit Lagoon basin (water) wrapping around the central island
    #    Spans north sea/lagoon (z=736..744), western inlet (x=82..87), central moat,
    #    east Surf channel (x=102..106, z=744..763), and southern lagoon bay (z=759..767)
    for z in range(Z0, Z1 + 1):
        for x in range(X0, X1 + 1):
            # Northern lagoon & ocean backdrop
            if z <= 743 and 82 <= x <= 107:
                put(x, z, "water_block")
            # Southern lagoon & ocean backdrop
            if z >= 764 and 80 <= x <= 107:
                put(x, z, "water_block")

    # Sculpted crescent lagoon around center (94.5, 751.5)
    for z in range(741, 765):
        for x in range(81, 112):
            dx = (x + 0.5 - 95.5) / 14.2
            dz = (z + 0.5 - 752.0) / 11.2
            dist = math.hypot(dx, dz)
            if dist <= 1.0:
                put(x, z, "water_block")

    # Explicit western inlet around the West Arched Moonbridge (x=83..87, z=744..763)
    fill((83, 744, 87, 762), "water_block")
    # Explicit southern crescent bay separating West Spiral Meadow from East Grove
    fill((87, 759, 108, 763), "water_block")
    # Explicit northern crescent bay
    fill((83, 741, 106, 744), "water_block")

    # East Shimmering Lagoon Surf Crossing: x=102..106, z=746..759 (SURFABLE)
    fill(EAST_SURF_CHANNEL, "water")
    # Also allow surfing gently north/south inside the open East Lagoon pocket (x=102..106, z=745..760)
    fill((102, 745, 106, 760), "water")
    # Pier water under/beside East Lantern Overlook Pier (x=107..111)
    fill((107, 750, 110, 759), "water_block")

    # 3. West Blossom Approach (x=70..82, z=751..756)
    fill((71, 751, 82, 756), "grass")
    # Curving moonstone cobble path from Canalave Gate (70, 754..755) to West Moonbridge (83, 752..754)
    fill((71, 754, 76, 755), "cobble")
    fill((76, 753, 79, 755), "cobble")
    fill((79, 752, 82, 754), "cobble")
    # Path spur north toward NW Fairy-Ring Alcove (x=76..78, z=750..753)
    fill((76, 750, 78, 753), "cobble")

    # 4. North-West Fairy-Ring Alcove (x=74..80, z=744..750)
    fill((74, 744, 80, 750), "grass")
    # Soft organic rounding of NW alcove corners
    put(74, 744, "tree")
    put(80, 744, "tree")
    put(74, 745, "mushroom")
    put(80, 745, "mushroom")
    # Blossom ring paving around West Item (77, 745)
    fill((76, 745, 78, 749), "spiral_flw")
    put(77, 746, "cobble")
    put(77, 747, "cobble")
    put(77, 748, "cobble")
    put(77, 749, "cobble")
    # Item West tile (77, 745)
    put(77, 745, "spiral_flw")

    # 5. Spiral Blossom Meadow (x=74..86, z=756..763)
    #    Crescent-shaped meadow hugging the SW lagoon curve; stays strictly west of x=87
    for z in range(756, 764):
        for x in range(74, 87):
            # Organic crescent envelope
            if z == 756 and x >= 83:
                continue
            if z == 757 and x >= 84:
                continue
            if z == 763 and (x <= 75 or x >= 85):
                continue
            if z == 762 and x >= 86:
                continue
            if z >= 761 and x == 74:
                continue
            # Inside meadow: spiral tall grass vs glowing spiral flower accents
            val = spiral_field(x, z)
            if val > 0.55 and (x, z) != (81, 760):
                put(x, z, "spiral_grass")
            else:
                put(x, z, "tallgrass")

    # Walkable entrance neck from West Blossom Approach into Spiral Meadow (x=75..78, z=756)
    fill((75, 756, 77, 756), "spiral_flw")
    # Clefairy West flower clearing around (81, 760)
    for cx, cz in [(81, 760), (80, 760), (82, 760), (81, 759), (81, 761)]:
        put(cx, cz, "spiral_flw")
    # Glowing fairy mushrooms accenting the western edge of the spiral meadow
    put(73, 758, "mushroom")
    put(73, 760, "mushroom")
    put(75, 763, "mushroom")

    # 6. West Arched Moonbridge (x=83..87, z=752..754)
    fill(WEST_BRIDGE_RECT, "bridge")
    # Water immediately north/south of bridge stays water_block (railings guard edges)
    for x in range(83, 88):
        put(x, 751, "water_block")
        put(x, 755, "water_block")

    # 7. Central Gardevoir Fountain Island (x=88..101, z=745..758)
    for z in range(CENTRAL_ISLAND_RECT[1], CENTRAL_ISLAND_RECT[3] + 1):
        for x in range(CENTRAL_ISLAND_RECT[0], CENTRAL_ISLAND_RECT[2] + 1):
            if is_island_octagon(x, z):
                put(x, z, "plaza")

    # Gardevoir Fountain (x=93..96, z=749..752, 4x4 blocked)
    fill(FOUNTAIN_RECT, "fountain")
    # Rift Conduit Crystal Pillar (x=98..99, z=747, 2x1 blocked)
    fill(CRYSTAL_RECT, "crystal")

    # Decorative lanterns on the 4 outer diagonal shoulders of the octagonal plaza
    # (check they don't collide with any anchor, trigger, bridge, or Surf landing!)
    # Anchors on island: Researcher (90,748), Barry (95,755), Rival coord (89..99, 756..757),
    # Fountain stand (94..95, 753), Crystal stand (98..99, 748), Bridge (88, 752..754), Surf (101, 751..754)
    for lx, lz in [(89, 746), (100, 749), (88, 755), (100, 756)]:
        put(lx, lz, "lantern")
    # Subtle glowing mushroom pair tucked near NW & NE plaza corners
    put(92, 745, "mushroom")
    put(97, 745, "mushroom")

    # East Surf Landing (x=101, z=751..754): moonstone steps into the East Lagoon
    for sx, sz in EAST_SURF_LANDING:
        put(sx, sz, "plaza_edge")

    # 8. East Lantern Overlook Pier (x=107..111, z=752..754)
    fill(EAST_PIER_RECT, "pier")
    # Guard north/south edges of the pier so Surf embarks cleanly from the west end (107, 752..754)
    for x in range(107, 111):
        put(x, 751, "water_block")
        put(x, 755, "water_block")

    # 9. East Wisteria Grove & Meadow (x=108..121, z=744..762)
    # Main east grove clearing
    fill((112, 744, 120, 761), "grass")
    # North-East Glade (x=108..116, z=744..749) overlooking the lagoon
    fill((108, 744, 116, 749), "grass")
    # Organic corner trees & mushrooms in NE Glade
    put(108, 744, "tree")
    put(109, 744, "mushroom")
    put(116, 744, "tree")
    put(117, 744, "tree")
    put(118, 744, "tree")
    put(119, 744, "tree")
    put(120, 744, "tree")
    put(119, 745, "tree")
    put(120, 745, "tree")
    put(120, 746, "tree")
    # Keep x=107 north of pier as water/cliff so NE Glade never touches Central Island
    for z in range(744, 751):
        put(107, z, "water_block")
    # Keep water directly below NE Glade overhang (x=108..110, z=750)
    fill((108, 750, 110, 750), "water_block")
    # Blossom floor accents in NE Glade around Clefairy East (110, 748) & Item East (114, 745)
    for fx, fz in [(110, 748), (111, 748), (110, 747), (111, 747),
                   (114, 745), (113, 745), (114, 746), (115, 745)]:
        put(fx, fz, "spiral_flw")
    put(108, 749, "mushroom")
    put(115, 744, "mushroom")

    # East Fairy Tall Grass patch (x=112..118, z=751..755)
    fill((112, 751, 118, 755), "tallgrass")
    # Keep a curving moonstone cobble path from Jubilife Gate (121, 758..759) to East Pier (111, 752..754)
    # and north-west branch into NE Glade!
    fill((115, 758, 120, 759), "cobble")
    fill((112, 756, 116, 758), "cobble")
    # Pier approach stepping cleanly into x=111, z=752..754 (carve 2 cobble tiles at x=112, z=753..754 + 112,755)
    fill((112, 753, 112, 756), "cobble")
    # Cobble trail up east side of tall grass into NE Glade (x=119, z=749..756 -> x=115..118, z=748..750)
    fill((119, 750, 119, 756), "cobble")
    fill((115, 748, 119, 750), "cobble")
    # Sign East at (119, 757) sits on walkable grass/cobble right beside the gate approach
    put(119, 757, "grass")
    # South-east woodland border below the Jubilife path
    fill((111, 760, 120, 762), "tree")
    put(112, 759, "tree")
    put(113, 759, "tree")
    put(114, 759, "mushroom")
    put(120, 756, "lantern")
    put(111, 751, "lantern")
    put(111, 755, "lantern")
    put(111, 750, "grass")
    put(111, 756, "grass")

    # 10. Gatehouse footprints & warps (NEVER MOVE!)
    # West Canalave Gatehouse prop 40 at (67.0, 755.0): x=64..70, z=752..758
    fill((64, 752, 70, 758), "gate_pad")
    for wx, wz in GATE_WEST_WARPS:
        put(wx, wz, "warp_w")
    # Clear area immediately east of Canalave Gate doorway (71, 753..756)
    put(71, 753, "grass")
    put(71, 754, "cobble")
    put(71, 755, "cobble")
    put(71, 756, "grass")
    # Sign West at (73, 753) on walkable grass verge
    put(73, 753, "grass")
    put(72, 752, "lantern")

    # East Jubilife Gatehouse prop 40 at (125.0, 759.0): x=121..127, z=756..762
    fill((121, 756, 127, 762), "gate_pad")
    for wx, wz in GATE_EAST_WARPS:
        put(wx, wz, "warp_e")
    # Clear area immediately west of Jubilife Gate doorway (120, 757..760)
    put(120, 757, "grass")
    put(120, 758, "cobble")
    put(120, 759, "cobble")

    # 11. Ensure all 4 outer perimeter borders of the 64x32 block are strictly impassable
    for x in range(X0, X1 + 1):
        for z in (Z0, Z1):
            if not (grid[(x, z)][0] & BLOCK):
                put(x, z, "tree")
    for z in range(Z0, Z1 + 1):
        for x in (X0, X1):
            if not (grid[(x, z)][0] & BLOCK):
                put(x, z, "tree")

    _CACHE["tiles"] = grid
    return grid


# ---------------------------------------------------------------------------
# Reachability & Validation Checks
# ---------------------------------------------------------------------------

def is_land_walkable(grid, x, z):
    v = grid.get((x, z))
    if v is None:
        return False
    perm = v[0]
    if perm & BLOCK:
        return False
    return (perm & 0xFF) != WATER


def is_surf_traversable(grid, x, z):
    v = grid.get((x, z))
    if v is None:
        return False
    perm = v[0]
    return not (perm & BLOCK)


def bfs(grid, start, allow_surf=False):
    pred = is_surf_traversable if allow_surf else is_land_walkable
    if not pred(grid, *start):
        return set()
    seen = {start}
    queue = [start]
    while queue:
        x, z = queue.pop(0)
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n not in seen and pred(grid, *n):
                seen.add(n)
                queue.append(n)
    return seen


def stock_warp_behaviors():
    """Read stock warp tile behaviors at HEAD from git (or disk fallback)."""
    out = {}
    for cid, cx, coords in [(50, 2, GATE_WEST_WARPS), (51, 3, GATE_EAST_WARPS)]:
        rel = f"{MAP_DATA_DIR}/map_data_{cid:03d}.bin"
        try:
            raw = subprocess.run(["git", "-C", ROOT, "show", f"HEAD:{rel}"],
                                 check=True, capture_output=True).stdout
        except Exception:
            raw = open(os.path.join(ROOT, rel), "rb").read()
        p_size = struct.unpack_from("<I", raw, 0)[0]
        perm = struct.unpack("<1024H", raw[16:16 + p_size])
        for wx, wz in coords:
            lx, lz = wx - cx * 32, wz - 736
            out[(wx, wz)] = perm[lz * 32 + lx]
    return out


def checks():
    grid = tiles()
    res = []

    # 1. Exact warp coordinates & behaviors matching stock
    stock_w = stock_warp_behaviors()
    for p in GATE_WEST_WARPS:
        v = grid[p][0]
        res.append((f"Canalave Gate warp {p} has behavior 0x{WARP_WEST:04x} (stock 0x{stock_w[p]:04x})",
                    v == WARP_WEST and v == stock_w[p]))
    for p in GATE_EAST_WARPS:
        v = grid[p][0]
        res.append((f"Jubilife Gate warp {p} has behavior 0x{WARP_EAST:04x} (stock 0x{stock_w[p]:04x})",
                    v == WARP_EAST and v == stock_w[p]))

    # 2. Gardevoir Fountain (4x4 blocked) & standing tiles
    f_blocked = all(grid[(x, z)][0] & BLOCK
                    for x in range(FOUNTAIN_RECT[0], FOUNTAIN_RECT[2] + 1)
                    for z in range(FOUNTAIN_RECT[1], FOUNTAIN_RECT[3] + 1))
    res.append(("Gardevoir Fountain (93..96, 749..752) is 4x4 blocked", f_blocked))
    res.append(("Fountain plaque standing tiles (94,753) and (95,753) are walkable",
                all(is_land_walkable(grid, *p) for p in FOUNTAIN_STAND_TILES)))

    # 3. Rift Conduit Crystal (2x1 blocked) & standing tiles
    c_blocked = all(grid[(x, z)][0] & BLOCK
                    for x in range(CRYSTAL_RECT[0], CRYSTAL_RECT[2] + 1)
                    for z in range(CRYSTAL_RECT[1], CRYSTAL_RECT[3] + 1))
    res.append(("Rift Conduit Crystal (98..99, 747) is 2x1 blocked", c_blocked))
    res.append(("Rift Conduit standing tiles (98,748) and (99,748) are walkable",
                all(is_land_walkable(grid, *p) for p in CRYSTAL_STAND_TILES)))

    # 4. West Moonbridge & East Pier & East Surf channel
    wb_ok = all(is_land_walkable(grid, x, z) and grid[(x, z)][1] == 0.0
                for x in range(WEST_BRIDGE_RECT[0], WEST_BRIDGE_RECT[2] + 1)
                for z in range(WEST_BRIDGE_RECT[1], WEST_BRIDGE_RECT[3] + 1))
    res.append(("West Arched Moonbridge (83..87, 752..754) is walkable at h=0.0", wb_ok))

    ep_ok = all(is_land_walkable(grid, x, z) and grid[(x, z)][1] == 0.0
                for x in range(EAST_PIER_RECT[0], EAST_PIER_RECT[2] + 1)
                for z in range(EAST_PIER_RECT[1], EAST_PIER_RECT[3] + 1))
    res.append(("East Lantern Overlook Pier (107..111, 752..754) is walkable at h=0.0", ep_ok))

    surf_ok = all(grid[(x, z)][0] == WATER and grid[(x, z)][1] == WATER_H
                  for x in range(EAST_SURF_CHANNEL[0], EAST_SURF_CHANNEL[2] + 1)
                  for z in range(EAST_SURF_CHANNEL[1], EAST_SURF_CHANNEL[3] + 1))
    res.append(("East Shimmering Lagoon Surf crossing (102..106, 746..759) is Surf water (0x15, h=-0.5)", surf_ok))

    # 5. Rival coord event rectangle walkable
    rc_ok = all(is_land_walkable(grid, x, z)
                for x in range(RIVAL_COORD_EVENT_RECT[0], RIVAL_COORD_EVENT_RECT[2] + 1)
                for z in range(RIVAL_COORD_EVENT_RECT[1], RIVAL_COORD_EVENT_RECT[3] + 1))
    res.append(("Rival coord event rect (89..99, 756..757) is fully walkable", rc_ok))

    # 6. BFS on foot from Canalave Gate (70, 754)
    foot_west = bfs(grid, GATE_WEST_WARPS[0], allow_surf=False)
    for name in WEST_FOOT_ANCHORS:
        p = ANCHORS[name]
        res.append((f"On-foot from Canalave reaches {name} at {p}", p in foot_west))
    for p in FOUNTAIN_STAND_TILES:
        res.append((f"On-foot from Canalave reaches Fountain stand {p}", p in foot_west))
    for p in CRYSTAL_STAND_TILES:
        res.append((f"On-foot from Canalave reaches Rift Crystal stand {p}", p in foot_west))
    for p in EAST_SURF_LANDING:
        res.append((f"On-foot from Canalave reaches East Surf Landing {p}", p in foot_west))

    # Plaza loop around fountain (verify north, south, west, east sides of fountain are all reachable)
    ring_pts = [(94, 748), (95, 748), (92, 750), (97, 750), (94, 753), (95, 753)]
    res.append(("Walkable plaza ring encircles Gardevoir Fountain", all(p in foot_west for p in ring_pts)))

    # 7. Surf gate integrity: NO land path bypasses the East Lagoon Surf crossing!
    res.append(("NO land path bypasses Surf gate to East Pier (107, 753)", (107, 753) not in foot_west))
    res.append(("NO land path bypasses Surf gate to Jubilife Gate (121, 758)", GATE_EAST_WARPS[0] not in foot_west))

    # 8. BFS on foot from Jubilife Gate (121, 758) reaches East Pier + East anchors
    foot_east = bfs(grid, GATE_EAST_WARPS[0], allow_surf=False)
    res.append(("On-foot from Jubilife reaches East Pier overlook tip (107, 753)", (107, 753) in foot_east))
    for name in EAST_FOOT_ANCHORS:
        p = ANCHORS[name]
        res.append((f"On-foot from Jubilife reaches {name} at {p}", p in foot_east))

    # 9. BFS with Surf from Canalave Gate reaches entire East side & Jubilife Gate
    surf_all = bfs(grid, GATE_WEST_WARPS[0], allow_surf=True)
    res.append(("With Surf from Canalave reaches East Pier (107, 753)", (107, 753) in surf_all))
    res.append(("With Surf from Canalave reaches Jubilife Gate (121, 758)", GATE_EAST_WARPS[0] in surf_all))
    for name in EAST_FOOT_ANCHORS:
        p = ANCHORS[name]
        res.append((f"With Surf from Canalave reaches {name} at {p}", p in surf_all))

    # 10. Tall grass counts exist on both West Spiral Meadow and East Grove
    w_tg = sum(1 for (x, z), (perm, _, _) in grid.items() if x < 96 and perm == TALL_GRASS)
    e_tg = sum(1 for (x, z), (perm, _, _) in grid.items() if x >= 96 and perm == TALL_GRASS)
    res.append((f"Spiral Blossom Meadow has tall grass ({w_tg} tiles) and East Grove has tall grass ({e_tg} tiles)",
                w_tg >= 40 and e_tg >= 20))

    # 11. No isolated unreachable land tiles
    unreachable_land = [p for p in grid if is_land_walkable(grid, *p) and p not in foot_west and p not in foot_east]
    res.append((f"Every walkable land tile is reachable from Canalave or Jubilife ({len(unreachable_land)} isolated: {unreachable_land[:5]})",
                not unreachable_land))

    # 12. Perimeter is sealed
    edge_walk = [p for p in grid if (p[0] in (X0, X1) or p[1] in (Z0, Z1)) and not (grid[p][0] & BLOCK)]
    res.append((f"Outer 64x32 perimeter is sealed ({len(edge_walk)} leaks)", not edge_walk))

    return res


def ascii_map(grid=None):
    grid = grid or tiles()
    anchor_mark = {}
    labels = {
        "LOCALID_EVERSPRING_RIVAL": "B",
        "LOCALID_RIFT_RESEARCHER": "R",
        "LOCALID_EVERSPRING_CLEFAIRY_WEST": "c",
        "LOCALID_EVERSPRING_CLEFAIRY_EAST": "c",
        "LOCALID_EVERSPRING_ITEM_WEST": "I",
        "LOCALID_EVERSPRING_ITEM_EAST": "I",
        "LOCALID_EVERSPRING_SIGN_WEST": "S",
        "LOCALID_EVERSPRING_SIGN_EAST": "S",
    }
    for name, pos in ANCHORS.items():
        anchor_mark[pos] = labels[name]

    lines = [
        "      " + "".join(str(x // 10 % 10) for x in range(X0, X1 + 1)),
        "      " + "".join(str(x % 10) for x in range(X0, X1 + 1)),
        "      " + ("-" * 32) + "|" + ("-" * 31) + "  (chunk 050 | chunk 051)",
    ]
    for z in range(Z0, Z1 + 1):
        row = []
        for x in range(X0, X1 + 1):
            if (x, z) in anchor_mark:
                row.append(anchor_mark[(x, z)])
            else:
                row.append(KINDS[grid[(x, z)][2]][0])
        lines.append(f"{z:4d}  " + "".join(row))
    return "\n".join(lines)


LEGEND = """legend:  . grass   , cobble   : moonstone plaza   ; Surf landing   "/* tall grass (spiral)   o spiral flowers
         = West Moonbridge   - East Lantern Pier   ~ Surf lagoon water   ^ guarded water   T blossom tree
         F Gardevoir Fountain (4x4)   C Rift Crystal (2x1)   m fairy mushroom   l lantern   G gatehouse
         W Canalave warp (0x6D)   E Jubilife warp (0x6C)
anchors: B Barry (95,755)   R Researcher (90,748)   c Clefairies (81,760 & 110,748)
         I Items (77,745 & 114,745)   S Signs (73,753 & 119,757)"""


def main():
    if "--ascii" in sys.argv or len(sys.argv) == 1:
        print(ascii_map())
        print(LEGEND)
    if "--anchors" in sys.argv:
        print("West warps:", GATE_WEST_WARPS)
        print("East warps:", GATE_EAST_WARPS)
        print("Fountain:", FOUNTAIN_RECT, "bg:", FOUNTAIN_BG_EVENTS, "stand:", FOUNTAIN_STAND_TILES)
        print("Crystal:", CRYSTAL_RECT, "bg:", CRYSTAL_BG_EVENTS, "stand:", CRYSTAL_STAND_TILES)
        print("Rival coord rect:", RIVAL_COORD_EVENT_RECT)
        for k, v in ANCHORS.items():
            print(f"  {k}: {v}")
    if "--check" in sys.argv:
        bad = 0
        for desc, ok in checks():
            print(("PASS " if ok else "FAIL ") + desc)
            bad += not ok
        print(f"\n{bad} failed")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
