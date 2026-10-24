"""Collision-vs-drawn audit for DW Route 214 (final JSON + C table + solver GRID).

For every ceiling tile (x44-49, z27-47, y=10):
- Collision (attr/solver GRID): '#' = BLOCKED, 'A'/'B' = group gap (BLOCKED
  while its group is on, current when off), '.'/'v'/'^'/'s'/'t'/'C' = walkable,
  VOID = fall.
- Drawn (JSON ghost props): kind 23 = stone block, kind 0 = arrow pad,
  kind 1 = sigil decal, none = slab.
Rules (fix2-lost):
  R1: every attr-BLOCKED (#) tile must have a stone-block prop (ghost 1).
  R2: every group-gap tile (A/B) must have a stone-block prop (ghost 2/3)
      that shows while its group is on.
  R3: every walkable tile must NOT have a stone-block prop (a block on a
      walkable tile would be an invisible wall / a wall on a walkable look).
  R4: every VOID tile must have NO prop (open edge) and must sit on the
      strip boundary (x==44 or x==49), i.e. drawn as open edge.
  R5: every current tile in the C table must be walkable in the grid
      (a current on a BLOCKED tile never fires) -- except the A/B gap
      tiles, which are currents only when their group is off.
  R6: every sigil/checkpoint in the C table must be walkable in the grid.
  R7: ghost_default_visible must expose groups 1-5; ghost_triggers empty.
"""
import json, re, sys
sys.path.insert(0, "tools/distortion_world")
import route_214_solver as S

def parse_tiles(name, src):
    m = re.search(rf"{name}\[\] = \{{(.*?)\}};", src, re.S)
    out = []
    for tup in re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+),", m.group(1)):
        out.append((int(tup[0]), int(tup[2])))
    return out

def parse_currents(src):
    m = re.search(r"sCurrents\[\] = \{(.*?)\};", src, re.S)
    return [(int(a), int(c)) for a, b, c in re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+),", m.group(1))]

def parse_sigils(src):
    m = re.search(r"sSigils\[\] = \{(.*?)\};", src, re.S)
    return [(int(a), int(c)) for a, b, c in re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+),", m.group(1))]

def parse_checkpoints(src):
    m = re.search(r"sCheckpoints\[\] = \{(.*?)\};", src, re.S)
    return [(int(a), int(c)) for a, b, c in re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+),", m.group(1))]

c = open("src/overlay009/dw_puzzle_route_214.c").read()
wall = set(parse_tiles("sWallTiles", c)); ga = set(parse_tiles("sGroupATiles", c))
gb = set(parse_tiles("sGroupBTiles", c)); voids = set(parse_tiles("sTiles", c))
currents = parse_currents(c); sigils = parse_sigils(c); cps = parse_checkpoints(c)
j = json.load(open("tools/distortion_world/route_214.json"))
props = {(p["x"], p["z"]): (p["group"], p["kind"]) for p in j["ghost_props"]}
blocks = {k for k, v in props.items() if v[1] == 23}
print(f"C table: wall={len(wall)} A={ga} B={gb} VOIDs={sorted(voids)} currents={len(currents)} sigils={sigils} cps={cps}")
print(f"JSON: {len(props)} props, blocks={len(blocks)}, visible={j['ghost_default_visible']}, triggers={j['ghost_triggers']}")
fails = []
def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond: fails.append(name)
# R1
bad = [t for t in wall if props.get(t) != (1, 23)]
check("R1 wall # tiles have ghost-1 block props", not bad, f"bad={bad}")
# R1 also: every '#' in GRID must be a wall tile
grid_hash = {(x, z) for (x, z), ch in S.GRID.items() if ch == "#"}
check("R1b GRID # == C wall set", grid_hash == wall, f"grid-only={sorted(grid_hash-wall)} c-only={sorted(wall-grid_hash)}")
# R2
check("R2 A gap has ghost-2 block", props.get(next(iter(ga))) == (2, 23), f"{props.get(next(iter(ga)))}")
check("R2 B gap has ghost-3 block", props.get(next(iter(gb))) == (3, 23), f"{props.get(next(iter(gb)))}")
# R3: no block prop on a walkable (non-#) tile -- except group gaps (covered by R2)
walk_blocks = [t for t in blocks if t not in wall and t not in ga and t not in gb]
check("R3 no block prop on walkable tile", not walk_blocks, f"{walk_blocks}")
# R4
for v in voids:
    check(f"R4 VOID {v} has no prop", v not in props, f"prop={props.get(v)}")
    check(f"R4 VOID {v} on strip boundary (x==44 or 49)", v[0] in (44, 49), f"x={v[0]}")
    check(f"R4 VOID {v} walkable in GRID", S.GRID[v] == ".", f"grid={S.GRID[v]}")
# R5: currents walkable (or A/B gap)
for t in currents:
    ch = S.GRID[t]
    ok = ch in "v^." or t in ga or t in gb
    if not ok: check(f"R5 current {t} walkable", False, f"grid={ch}"); break
else:
    check("R5 all currents walkable (or A/B gap)", True)
# R6
for t in sigils:
    check(f"R6 sigil {t} on walkable grid", S.GRID[t] in "st", f"grid={S.GRID[t]}")
for t in cps:
    if t == (20, 12): continue  # map-entry CP is on the floor, not the ceiling grid
    check(f"R6 checkpoint {t} on walkable grid", S.GRID[t] in "C.", f"grid={S.GRID[t]}")
# R7
check("R7 ghost_default_visible exposes groups 1-5 (62)", j["ghost_default_visible"] == 62, f"={j['ghost_default_visible']}")
check("R7 ghost_triggers empty", j["ghost_triggers"] == [], f"={j['ghost_triggers']}")
check("R7 39 props total", len(props) == 39, f"={len(props)}")
# Arrow props: one per current except A/B gaps (13)
arrows = {k for k, v in props.items() if v[1] == 0}
expect_arrows = {t for t in currents if t not in ga and t not in gb}
check("R7 arrow props == currents minus A/B gaps", arrows == expect_arrows,
      f"extra={sorted(arrows-expect_arrows)} missing={sorted(expect_arrows-arrows)}")
print("RESULT", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
