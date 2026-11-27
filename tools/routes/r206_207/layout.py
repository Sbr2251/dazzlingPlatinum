#!/usr/bin/env python3
"""Routes 206-207 Eclipse Supply Road: the tile contract (what goes where). Absolute matrix tiles x/z.

Everything here sits on tiles that are walkable in stock only where listed in BLOCK (those become blocked; the
behaviour byte is kept), or on tiles that are already blocked in stock (cliff edges, verges). build_art.py turns the
PROPS into geometry; story.py places the BG events; the checks in build_art.py prove that every stock walkable
region stays connected (minus BLOCK), the Cycling Road deck stays continuous, and no event tile is covered.

Areas:
  Route 207 (MAP_025 / MAP_026, road at BDHC height 5 = mesh h 4):
    RUTS       truck wheel ruts from the Route 206 junction (x 304.5, z 699) south, curving east along the road
               (z 712.5) into Mt. Coronet's south cave mouth (warp 341,712).
    YARD       the Mt. Coronet Staging Yard on the north verge of the road (row z 710, x 322..337): crate stacks,
               violet shard-containment racks, work lamps, the manifest crate, and twin Eclipse banners flanking
               the road at x 334 (z 710 north, z 715 south); a steel safety fence on the cliff edge x 336..340.
    OUTPOST    the roadside outpost where the ruts turn: banner, crates and lamp at x 307, z 704, 705, 707; crates, a
               rack and a lamp on the north verge x 314..318, z 710 (honey tree 311,709 and its tile 311,710 kept).
  Route 206 (MAP_027 / MAP_028 / MAP_030):
    PLAZA      the south gate approach (z 689..694): barricades narrow the plaza to the 4-wide sand lane
               (x 301..304) to the gate doors; crates, cones, a work lamp and the ROAD CLOSED sign (BG event).
    EAST_PATH  steel fencing and cones narrow the east underpass path (x 309, z 692..693).
    DECK_S     Cycling Road deck, south end: west lane (x 299..300, z 674..679) coned off behind a barricade.
    DECK_N     Cycling Road ramp, north end: west lane (x 299..300, z 588..591) closed the same way.
    UNDERPASS  ground between the split deck lanes (x 301..304, z 648..654): Eclipse supply cache under the road
               (rack 302,649, crates 303,649, lamp 303,653; the Burn Heal at 302,652 stays reachable).
"""

# ---------------------------------------------------------------------------------------------------------------
# ruts: centreline polyline (x, z) and lane half-width (tiles)
# ---------------------------------------------------------------------------------------------------------------

RUT_HALF = 1.0
RUT_START = (304.5, 699.05)
RUT_TURN_CENTRE = (309.5, 707.5)     # quarter arc of radius 5 from (304.5, 707.5) to (309.5, 712.5)
RUT_END_X = 341.45                   # just short of the cave mouth (warp 341,712; the hole is drawn at x 342)

# ---------------------------------------------------------------------------------------------------------------
# props: (kind, x, z, params). x, z are the tile; geometry stays inside the tile (or on blocked stock tiles)
# ---------------------------------------------------------------------------------------------------------------

PROPS = [
    # --- Route 207 Mt. Coronet Staging Yard (MAP_026), north verge z 710
    ("stack", 322, 710, dict(kind="pallet3")),
    ("stack", 323, 710, dict(kind="pair")),
    ("lamp", 324, 710, {}),
    ("rack", 325, 710, {}),
    ("rack", 326, 710, {}),
    ("stack", 327, 710, dict(kind="tall")),
    ("lamp", 328, 710, {}),
    ("stack", 329, 710, dict(kind="pallet3")),
    ("stack", 330, 710, dict(kind="canisters")),
    ("rack", 331, 710, {}),
    ("stack", 332, 710, dict(kind="pair")),
    ("manifest", 333, 710, {}),
    ("banner", 334, 710, {}),
    ("rack", 335, 710, {}),
    ("lamp", 336, 710, {}),
    ("stack", 337, 710, dict(kind="tall")),
    ("banner", 334, 715, {}),
    ("fence", 336, 715, dict(x1=341, zline=715.3, h=4.0)),   # on the blocked cliff-edge tiles x 336..340
    # --- Route 207 roadside outpost (MAP_025)
    ("banner", 307, 704, {}),
    ("stack", 307, 705, dict(kind="pallet3")),
    ("lamp", 307, 707, {}),
    ("stack", 314, 710, dict(kind="tall")),
    ("lamp", 315, 710, {}),
    ("stack", 316, 710, dict(kind="canisters")),
    ("stack", 317, 710, dict(kind="pair")),
    ("rack", 318, 710, {}),
    # --- Route 206 south gate plaza (MAP_027)
    ("barricade", 299, 691, dict(x1=301, axis="x")),
    ("barricade", 305, 691, dict(x1=307, axis="x")),
    ("stack", 299, 693, dict(kind="pallet3")),
    ("cones", 300, 693, dict(n=2)),
    ("sign", 305, 693, {}),
    ("lamp", 306, 693, {}),
    # east underpass path
    ("fence_ns", 309, 692, dict(z1=694, xline=309.2)),
    ("cones", 309, 693, dict(n=1)),
    # Cycling Road deck, south end (west lane): the whole coned-off lane is blocked
    ("block", 299, 674, dict(x1=301, z1=680)),
    ("barricade", 299, 674, dict(x1=301, axis="x", deck=True)),
    ("cones_line", 300, 675, dict(z1=680, deck=True)),
    ("stack", 299, 676, dict(kind="pair", deck=True)),
    ("lamp", 299, 678, dict(deck=True)),
    # --- Route 206 underpass cache (MAP_028)
    ("rack", 302, 649, {}),
    ("stack", 303, 649, dict(kind="pallet3")),
    ("lamp", 303, 653, {}),
    # --- Route 206 Cycling Road ramp, north end (MAP_030)
    ("block", 299, 588, dict(x1=301, z1=592)),
    ("barricade", 299, 588, dict(x1=301, axis="x", deck=True)),
    ("cones_line", 300, 589, dict(z1=592, deck=True)),
    ("stack", 299, 590, dict(kind="pair", deck=True)),
]


def footprint(kind, x, z, p):
    """Tiles a prop blocks."""
    if kind in ("barricade",) and p.get("axis", "x") == "x":
        return [(xx, z) for xx in range(x, p["x1"])]
    if kind == "cones_line":
        return [(x, zz) for zz in range(z, p["z1"])]
    if kind == "block":
        return [(xx, zz) for xx in range(x, p["x1"]) for zz in range(z, p["z1"])]
    if kind == "fence":
        return []                           # on already-blocked cliff-edge tiles
    if kind == "fence_ns":
        return [(x, zz) for zz in range(z, p["z1"])]
    return [(x, z)]


def blocked_tiles():
    out = []
    for kind, x, z, p in PROPS:
        for t in footprint(kind, x, z, p):
            if t not in out:
                out.append(t)
    return out


# tiles that must never be blocked: the honey tree's reading tile, sign-reading tiles, and the yard's road rows
KEEP_OPEN = [(311, 710), (313, 712), (333, 711), (305, 694), (340, 712), (340, 713), (340, 714), (341, 712)]

# ---------------------------------------------------------------------------------------------------------------
# BG events added by story.py (tile, facing the player must have, script label)
# ---------------------------------------------------------------------------------------------------------------

BG_MANIFEST = dict(x=333, z=710, dir="BG_EVENT_DIR_NORTH", script="Route207_ManifestCrate", read_from=(333, 711))
BG_CLOSED_SIGN = dict(x=305, z=693, dir="BG_EVENT_DIR_NORTH", script="Route206_RoadClosedSign", read_from=(305, 694))

# showcase viewpoints for the report and previews: (player tile x, z, facing)
VIEWPOINTS = {
    "coronet_yard": (332, 713, "north"),
    "supply_ruts": (310, 713, "east"),
    "r206_barricade": (302, 695, "north"),
}
