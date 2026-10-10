#!/usr/bin/env python3
"""Tile layout of the Route 203 scar (the west field of Route 203, overworld chunk map_data_019).

Usage: python3 tools/route_203/scar_layout.py [--ascii | --check]     (standard library only)

This file is the single source of truth for where things are in the redesigned field. The chunk builder
(build_scar.py: geometry + permissions), the airtight check and the events (events_route_203.json) follow it.

Coordinates are matrix-global overworld tiles (the ones the events JSON uses). Chunk 019 is matrix cell (6, 23):
x 192..223, z 736..767. Only the field x 196..213, z 744..756 (FIELD) and the fallen tree on the road below it
(z 757..760) change. Everything else in chunk 019 (the west forest x 192..195, the forest north of z 744, the road
and its fences, the x 214 cliff with its stairs, the middle section with the pond) and all of chunk 020 is stock.
Heights are stock and flat: the whole field is at world y 16 (BDHC unchanged); the fissure is blocked.

Legend:
  .  short grass (walk)                 w  tall grass (encounters)
  :  scorched ash (walk)                %  violet-cracked ash (walk)
  X  the fissure (blocked; a 1-tile-deep trench with a glowing floor)
  T  tree (2x2, stock tree01 look)      K  charred tree (2x2, tree01 with a charred palette)
  S  the split stump (blocked)          L  the fallen trunk (blocked)        C  the fallen crown (blocked)
  o  debris boulder (blocked)           G  Garius's spot (walk, cracked ash)
  =  the stock gravel road (walk; only the fallen tree is added on top of it)

Gameplay: the fallen tree (S/L/C) and the fissure form one 4-connected barrier from the road's south fence to the
fissure's tip at (210, 746). The only way past is the 2-tile gap north of the tip, (210, 744..745) = GAP, which is
where Garius's coord trigger sits. check() proves it with a flood fill.
"""

import sys

X0, Z0 = 196, 744          # top-left tile of ROWS
CHUNK = (6, 23)            # matrix cell of map_data_019
CHUNK_ID = 19

ROWS = [
    # x: 196 ....... 213
    '..........:::::...',   # 744
    '.........::%%%%:..',   # 745
    'wwww....:%%%%%X%:.',   # 746
    'wwww...:%%%%%XXG:.',   # 747
    'wwwwTT.:%%%%%X%%:.',   # 748
    'wwwwTT.:%%%XXX%%:w',   # 749
    'wwwwTT.:%%XX%%%o:w',   # 750
    'wwwwTT:%%%X%%%::.w',   # 751
    'wwwwKK:%%XX%%:..ww',   # 752
    '.ww.KK:%XX%%:...ww',   # 753
    '.....:%%X%%:......',   # 754
    '....:%%%S%::......',   # 755
    '....::%LL%:.......',   # 756
    '======LL==========',   # 757
    '=====LL===========',   # 758
    '===CCC============',   # 759
    '===CCC============',   # 760
]

WALK = set('.w:%G=')
BLOCKED = set('XTKSLCo')

GAP = [(210, 744), (210, 745)]              # Garius's trigger: x 210, z 744..745 (width 1, length 2)
GARIUS = (211, 747)                         # stands at the fissure tip, facing west into it
STARLY = [(203, 750), (204, 751)]           # the two spooked Starly, west of the fissure
STARLY_TRIGGER = (196, 754, 8, 1)           # x, z, width, length: every way north from the road crosses z 754 here
ENTRANCE = (192, 758)                       # from Jubilife
STAIRS = [(214, z) for z in range(757, 761)]  # stock stairs up to the middle section

FIELD = (196, 744, 213, 756)                # x0, z0, x1, z1 (inclusive): regenerated ground, grass and trees
ROAD = (196, 757, 213, 760)                 # the stock road; only S/L/C are added on top of it

# behaviour values (permissions low byte; 0x8000 = blocked)
BLOCK, TALL_GRASS, NONE = 0x8000, 0x02, 0x00


def tiles():
    """{(x, z): char} for the layout rectangle."""
    out = {}
    for dz, row in enumerate(ROWS):
        assert len(row) == 18, (Z0 + dz, len(row), row)
        for dx, ch in enumerate(row):
            out[(X0 + dx, Z0 + dz)] = ch
    return out


def tree_origins(kind):
    """Top-left tiles of the 2x2 trees of kind 'T' (stock look) or 'K' (charred)."""
    return {"T": [(200, 748), (200, 750)], "K": [(200, 752)]}[kind]


def permission(ch, stock):
    """Permission value for a layout char; `stock` is the stock value (kept for the road)."""
    if ch in BLOCKED:
        return BLOCK
    if ch == 'w':
        return TALL_GRASS
    if ch == '=':
        return stock
    return NONE


def walkable_world(stock_perm):
    """Walkability over x 192..255, z 736..767 using the stock permissions (chunks 019 + 020, [z][x] global dicts)
    with the layout applied on top. stock_perm: {(x, z): u16}."""
    t = tiles()
    w = {}
    for (x, z), v in stock_perm.items():
        ch = t.get((x, z))
        val = permission(ch, v) if ch is not None else v
        w[(x, z)] = not (val & 0x8000)
    return w


def flood(walk, start, blocked=()):
    seen, todo = {start}, [start]
    blocked = set(blocked)
    while todo:
        x, z = todo.pop()
        for n in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if n not in seen and walk.get(n) and n not in blocked:
                seen.add(n)
                todo.append(n)
    return seen


def check(stock_perm, objects=()):
    """Gameplay checks. objects: tiles blocked by event objects (signs, NPCs, item balls). Returns a list of
    (name, ok, detail)."""
    walk = walkable_world(stock_perm)
    for o in objects:
        walk[o] = False
    res = []
    full = flood(walk, ENTRANCE)
    res.append(("stairs reachable from the Jubilife entrance", all(s in full for s in STAIRS), ""))
    cut = flood(walk, ENTRANCE, blocked=GAP)
    res.append(("barrier is airtight: without the gap the stairs are unreachable", not any(s in cut for s in STAIRS),
                f"{len(cut)} tiles on the west side"))
    back = flood(walk, STAIRS[0])
    res.append(("route works backwards (stairs -> entrance)", ENTRANCE in back, ""))
    t = tiles()
    north = flood(walk, ENTRANCE, blocked=[(x, STARLY_TRIGGER[1]) for x in range(STARLY_TRIGGER[0],
                                                                              STARLY_TRIGGER[0] + STARLY_TRIGGER[2])])
    res.append(("Starly trigger row spans every way north from the road", not any(g in north for g in GAP), ""))
    for g in GAP:
        res.append((f"gap tile {g} walkable", walk.get(g, False), t.get(g)))
    res.append(("Garius's tile walkable", walk.get(GARIUS, False), t.get(GARIUS)))
    return res


def ascii_map():
    t = tiles()
    lines = ["      " + "".join(str(x // 10 % 10) for x in range(X0, X0 + 18)),
             "      " + "".join(str(x % 10) for x in range(X0, X0 + 18))]
    for dz in range(len(ROWS)):
        z = Z0 + dz
        lines.append(f"{z:5d} " + "".join(t[(x, z)] for x in range(X0, X0 + 18)))
    return "\n".join(lines)


if __name__ == "__main__":
    if "--ascii" in sys.argv or len(sys.argv) == 1:
        print(ascii_map())
        print("T trees at", tree_origins("T"), " K trees at", tree_origins("K"))
