#!/usr/bin/env python3
"""Routes 206-207 Eclipse Supply Road: the tile contract (what goes where). Absolute matrix tiles x/z.

Everything here sits on tiles that are walkable in stock only where listed in BLOCK (those become blocked; the
behaviour byte is kept), or on tiles that are already blocked in stock (cliff edges, verges). build_art.py turns the
PROPS into geometry; story.py places the BG events; the checks in build_art.py prove that every stock walkable
region stays connected (minus BLOCK), the Cycling Road deck stays continuous, and no event tile is covered.

Areas:
  Route 207 (MAP_025 / MAP_026, road at BDHC height 5 = mesh h 4):
    RUTS       two sculpted truck wheel tracks from below the Route 206 steps (x 303.5, z 699) south along the sand
               lane, a radius-5 curve at (308.5, 708), then east along z 713 towards Mt. Coronet's south cave mouth.
               build_art.py clips every track piece to bare dirt/sand ground (never grass, cliffs or ledges, from
               the stock ground textures) and feathers each run out where it meets grass or the cave.
    YARD       the Mt. Coronet Staging Yard on the north verge (z 710, a few pieces forward on z 711), three organic
               clusters with natural gaps: A x 321..324 (crates on a pallet, a tarp stack, a shard-containment
               frame, a work lamp), gap 325..326, B x 327..330 (banner, two containment frames, crates, a canister case
               pulled forward),
               gap 331..332, C x 333..337 (manifest crate, banner, tarp stack, pallet, lamp); the twin banner
               south of the road at (334, 715) and the cliff-edge safety fence x 336..340.
    OUTPOST    the roadside outpost where the ruts turn (x 306..307, z 704..707, leaving 306..307,706 open) and the north-verge cluster
               x 314..318 (honey tree 311,709 and its tile 311,710 kept).
  Route 206 (MAP_027 / MAP_028 / MAP_030):
    PLAZA      the south gate approach (z 689..694): a staggered partial lane closure on both grass shoulders
               (x 299..300 and 305..306) - alternating yellow/black barricades, a cone taper, a parked Eclipse
               equipment crate on a pallet, banner posts, a work lamp and the ROAD CLOSED sign (BG event). The
               4-wide sand lane x 301..304 to the gate doors stays clear.
    EAST_PATH  steel fencing and cones narrow the east underpass path (x 309, z 692..693).
    DECK_S     Cycling Road deck, south end: west lane (x 299..300, z 674..679) closed by staggered barricades,
               cones, an equipment crate, a lamp and a banner.
    DECK_N     Cycling Road ramp, north end: west lane (x 299..300, z 588..591) closed the same way.
    UNDERPASS  ground between the split deck lanes (x 301..304, z 648..654): Eclipse supply cache under the road
               (containment frame 302,649, crates 303,649, lamp 303,653; the Burn Heal at 302,652 stays reachable).
"""

# ---------------------------------------------------------------------------------------------------------------
# ruts: centreline polyline (x, z) and lane half-width (tiles)
# ---------------------------------------------------------------------------------------------------------------

RUT_START = (303.5, 699.0)           # sand lane below the Route 206 steps (ledge rows z 697..698)
RUT_TURN_CENTRE = (308.5, 708.0)     # quarter arc of radius 5 from (303.5, 708) to (308.5, 713)
RUT_LINE_Z = 713.0                   # the east run: tracks at z 712.45 and 713.55 (tile 711 stays free for props)
RUT_END_X = 341.0                    # the cave mouth (warp 341,712); the clip ends the tracks on the dirt before it
RUT_TRACK = 0.55                     # wheel-track offset either side of the centreline (tiles)

# ---------------------------------------------------------------------------------------------------------------
# props: (kind, x, z, params). x, z are the tile; geometry stays inside the tile (or on blocked stock tiles)
# ---------------------------------------------------------------------------------------------------------------

PROPS = [
    # --- Route 207 Mt. Coronet Staging Yard (MAP_026): cluster A
    ("stack", 321, 710, dict(kind="tall", yaw=0.05)),
    ("tarp", 322, 710, dict(ht=1.15, yaw=-0.06)),
    ("stack", 322, 711, dict(kind="pallet2", yaw=0.12)),
    ("frame", 323, 710, dict(ht=1.45, yaw=0.04)),
    ("lamp", 324, 710, {}),
    # cluster B
    ("banner", 327, 710, {}),
    ("stack", 327, 711, dict(kind="pair", yaw=-0.15)),
    ("frame", 328, 710, dict(ht=1.8, yaw=-0.07)),
    ("frame", 329, 710, dict(ht=1.2, yaw=0.1)),
    ("stack", 330, 710, dict(kind="pallet2", yaw=-0.06)),
    ("stack", 330, 711, dict(kind="canisters", yaw=0.08)),
    # cluster C
    ("manifest", 333, 710, {}),
    ("banner", 334, 710, {}),
    ("tarp", 335, 710, dict(ht=0.95, yaw=0.08)),
    ("stack", 335, 711, dict(kind="pallet3", yaw=-0.1)),
    ("lamp", 336, 710, {}),
    ("stack", 337, 710, dict(kind="tall", yaw=-0.04)),        # stock-blocked tile under the cliff corner
    ("banner", 334, 715, {}),
    ("fence", 336, 715, dict(x1=341, zline=715.3, h=4.0)),   # on the blocked cliff-edge tiles x 336..340
    # --- Route 207 roadside outpost (MAP_025)
    ("banner", 307, 704, {}),
    ("tarp", 307, 705, dict(ht=1.0, yaw=0.06)),
    ("lamp", 307, 707, {}),
    ("stack", 306, 707, dict(kind="pair", yaw=0.15)),
    ("stack", 314, 710, dict(kind="tall", yaw=-0.08)),
    ("lamp", 315, 710, {}),
    ("tarp", 316, 710, dict(ht=1.05, yaw=0.05)),
    ("stack", 316, 711, dict(kind="pair", yaw=0.18)),
    ("stack", 318, 710, dict(kind="canisters")),
    # --- Route 206 south gate plaza (MAP_027): west shoulder closure (lane x 301..304 stays clear)
    ("block", 299, 689, dict(x1=301, z1=694)),
    ("banner", 299, 689, {}),
    ("cones", 300, 689, dict(n=1)),
    ("stack", 299, 690, dict(kind="equip")),
    ("barricade", 300, 690, dict(x1=301, axis="x")),
    ("lamp", 299, 691, {}),
    ("cones", 300, 691, dict(n=1)),
    ("barricade", 299, 692, dict(x1=301, axis="x")),
    ("stack", 299, 693, dict(kind="pair", yaw=0.1)),
    ("cones", 300, 693, dict(n=2)),
    ("cones", 299, 694, dict(n=1)),
    # east shoulder closure (the sign is read from 305,694)
    ("block", 305, 689, dict(x1=307, z1=693)),
    ("cones", 305, 689, dict(n=1)),
    ("stack", 306, 689, dict(kind="tall", yaw=0.06)),
    ("barricade", 305, 690, dict(x1=307, axis="x")),
    ("cones", 305, 691, dict(n=1)),
    ("lamp", 306, 691, {}),
    ("barricade", 305, 692, dict(x1=306, axis="x")),
    ("stack", 306, 692, dict(kind="equip")),
    ("sign", 305, 693, {}),
    ("banner", 306, 693, {}),
    ("cones", 306, 694, dict(n=1)),
    # east underpass path
    ("fence_ns", 309, 692, dict(z1=694, xline=309.2)),
    ("cones", 309, 693, dict(n=1)),
    # Cycling Road deck, south end (west lane): the whole closed lane is blocked
    ("block", 299, 674, dict(x1=301, z1=680)),
    ("barricade", 299, 674, dict(x1=301, axis="x", deck=True)),
    ("stack", 299, 675, dict(kind="equip", deck=True)),
    ("cones", 300, 675, dict(n=1, deck=True)),
    ("barricade", 300, 676, dict(x1=301, axis="x", deck=True)),
    ("lamp", 299, 677, dict(deck=True)),
    ("cones", 300, 677, dict(n=1, deck=True)),
    ("stack", 299, 678, dict(kind="pair", yaw=-0.12, deck=True)),
    ("cones", 300, 678, dict(n=1, deck=True)),
    ("banner", 299, 679, dict(deck=True)),
    ("cones", 300, 679, dict(n=2, deck=True)),
    # --- Route 206 underpass cache (MAP_028)
    ("frame", 302, 649, dict(ht=1.4)),
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
KEEP_OPEN = [(311, 710), (313, 712), (333, 711), (305, 694), (300, 694), (301, 689), (304, 689), (340, 712),
             (340, 713), (340, 714), (341, 712), (325, 710), (326, 710), (331, 710), (332, 710)]

# ---------------------------------------------------------------------------------------------------------------
# BG events added by story.py (tile, facing the player must have, script label)
# ---------------------------------------------------------------------------------------------------------------

BG_MANIFEST = dict(x=333, z=710, dir="BG_EVENT_DIR_NORTH", script="Route207_ManifestCrate", read_from=(333, 711))
BG_CLOSED_SIGN = dict(x=305, z=693, dir="BG_EVENT_DIR_NORTH", script="Route206_RoadClosedSign", read_from=(305, 694))

# showcase viewpoints for the report and previews: (player tile x, z, facing)
VIEWPOINTS = {
    "coronet_yard": (329, 713, "north"),
    "supply_ruts": (310, 713, "east"),
    "r206_barricade": (302, 695, "north"),
}
