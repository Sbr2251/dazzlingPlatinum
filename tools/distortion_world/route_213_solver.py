#!/usr/bin/env python3
"""Solver model for DW Route 213, the Drowned Lake (rift #4, difficulty 5).

Standalone Dijkstra over the puzzle model, with the engine-a semantics
from ``include/overlay009/dw_puzzle.h`` (commit 623ccce7ee on
dw/engine-a) and the engine-b stone semantics from
``docs/distortion_world/actors_design.md`` (branch dw/engine-b):

* tile overrides: SOLID / VOID (step = fall) / BLOCKED, consulted by
  the walk check on every surface, floor included;
* currents: stepping on a current tile starts a slide in its FACE_*
  dir until blocked, stopped by a RESTING stone, or off-current;
  landing on a sigil / rune / checkpoint ends the slide. A slide
  never pushes a stone;
* sigils: RESET restores the puzzle to the last checkpoint snapshot
  (player does not move);
* checkpoints: stepping on one snapshots the puzzle (here, the stone
  states) and makes it the fall target. A fall restores the player
  and the stones to the last checkpoint snapshot. No checkpoint is a
  rune landing or a jump landing: engine-a's rune starts a jump task
  and does not promise a step-hook call at its destination, so the
  solver never checks for a checkpoint on a rune landing tile;
* runes: stepping on a rune tile changes surface in place to its target;
* stones (engine-b, via ``DwPuzzle_SetActorTile``). Max 4 per map; this
  puzzle uses 4. A stone is RESTING, FALLING, or LANDED:
  - RESTING: actor tile BLOCKED, pushable. A slide stops before it.
    Pushing it onto a current tile plugs the current (the BLOCKED
    actor tile stops the slide). A push fails if the target is
    another stone, a protected tile, a landing tile, BLOCKED, or VOID
    that is not a designated edge. A push that changes surface never
    happens; a non-unit (jump/diagonal) delta never pushes.
  - FALLING: occupies no tile, lasts 12 frames (modelled as instant:
    a push that targets a designated edge lands the stone at once).
    A fall is blocked by a landing clash (another stone LANDED at the
    landing tile, or FALLING toward it).
  - LANDED: actor tile SOLID. The stone is walkable terrain, not an
    obstacle, and not pushable. Landing tiles are reserved per stone:
    they are never current tiles, never sigils, pads, checkpoints or
    rune tiles. In this table they carry an explicit VOID override:
    VOID before landing, and the LANDED actor tile beats the override
    after landing (engine-a rule change). A stone can only fall at a
    designated edge with a designated landing.
  - A RESTING stone can never occupy a checkpoint, pad, sigil,
    landing, or reset-sigil tile (push-block rules), so the reset
    path is never stone-blocked.

Surfaces: 'C' = ceiling (y = 10), 'G' = GROUND (y = 1, base map
terrain). Route 213's lakebed is base terrain, so engine-b requires
GROUND, not FLOOR (a floating platform). For GROUND there is no
platform grid and a DEFAULT ground tile reads BLOCKED (conservative
cross-surface rule), so the table gives every ground actor tile an
explicit state: the three landing tiles carry an explicit VOID
override in the table (no map-data change, no map_data_680 clone:
the collision glue lets explicit ground overrides beat the stock
0x8000 permission, and the LANDED actor tile beats the VOID
override after landing), the (48, 40) hazard is an explicit VOID
override, and all other ground detour tiles are SOLID overrides.

Coordinates are DW world tiles (x, z) plus a surface: 'C' = ceiling
(y = 10), 'G' = ground (y = 1, base map terrain). The puzzle is counted from the ceiling
entry (the jump landing at (49, 27), checkpoint at (49, 28)) to the
totem trigger (any ceiling tile with z >= 45). One tile move (walk,
push, or slide step) = 1 step; a rune surface change costs 0 steps.
The rift entry-to-wall approach is plain travel, not puzzle, and is
not counted.

Run: ``python3 tools/distortion_world/route_213_solver.py``
Prints the optimal solution, difficulty stats, fall scenarios, and the
soft-lock proof (every reachable state can reach the totem).
"""

# Ceiling causeway, from tools/distortion_world/route_213.json (platform
# rows: x = 49 - row, columns z = 25 + col, '.' = walkable).
_CEIL_ROWS = [
    "##....#####....#..#####",
    "#####.#####.#####.#....",
    "#####.#####.######.....",
    "#####.#####.#####......",
    "#####.#####.#####.#....",
    "#####....#..#####.#####",
]
CEIL_BASE = set()
for _r, _line in enumerate(_CEIL_ROWS):
    for _c, _ch in enumerate(_line):
        if _ch == ".":
            CEIL_BASE.add((49 - _r, 25 + _c))

# Ceiling VOID gaps (explicit overrides): the three drop chutes.
# Each is a designated edge for one ceiling stone, with the landing
# on the floor below at the same (x, z).
CEIL_VOID = {(44, 34), (49, 40), (47, 42)}
# Ceiling alcove tiles (SOLID overrides, drawn as rune / sigil circles):
# rune-down tiles and reset-sigil tiles. RESETS are engine sigils.
RUNES_C = {  # (x, z) -> (target x, target z, target surface)
    (45, 33): (46, 33, "G"),  # stage 1: down to the ground detour
    (48, 39): (49, 34, "G"),  # stage 2: down to the ground detour
    (48, 43): (43, 43, "G"),  # stage 3: down to the ground detour
}
RESETS = {(45, 29), (48, 37)}  # stage 1 / 2 reset sigils (RESET kind)
CEIL_WALK = CEIL_BASE | set(RUNES_C) | RESETS

# Ground detour tiles (SOLID overrides, drawn as sunken reef shelves).
# Landing tiles (44, 34), (49, 40), (47, 42) are NOT in this set: they
# are in GROUND_VOID below (explicit VOID overrides, beaten by the
# LANDED actor tile after landing).
GROUND_WALK = {
    # stage 1: landing, walk to the landed stone, walk across it, rune-up
    # (47, 33) was dropped to fit the 32-tile cap (see the tile-budget
    # note): the stage-1 rune lands one tile closer, at (46, 33).
    (46, 33), (45, 33), (44, 33), (43, 34),
    # stage 2: approach, push the plug stone twice down the current
    # column, walk around the plugged column, across the landed stone,
    # rune-up
    (49, 34), (49, 35), (49, 36), (48, 36),
    (48, 37), (48, 38), (48, 39), (49, 38), (49, 39), (49, 41),
    # stage 3: walk to the current, ride it onto the landed stone, rune-up
    (43, 43), (44, 43), (45, 43), (46, 43), (47, 43), (48, 42),
}
# Ground VOID tiles (explicit VOID overrides in the table).
# The first three are the landing tiles: before landing the tile is
# VOID (a step there is a fall); after landing, the LANDED stone's
# SOLID actor tile beats the explicit VOID override (engine-a rule
# change, lead 2026-10-23), so the tile becomes walkable. No
# map_data_680 clone and no base-kind change is needed: the
# collision glue lets explicit ground overrides beat the stock
# 0x8000 permission. (48, 40) is an explicit VOID hazard at the end
# of the stage-2 current column (not a landing tile): without the
# plug, the slide runs (48, 37) -> (48, 38) -> (48, 39) ->
# VOID (48, 40) and falls.
GROUND_VOID = {(44, 34), (49, 40), (47, 42), (48, 40)}
RUNES_F = {  # (x, z) -> (target x, target z, target surface)
    (43, 34): (44, 35, "C"),  # stage 1: back to the ceiling past gap 1
    (49, 41): (49, 41, "C"),  # stage 2: back to the ceiling past gap 2
    (48, 42): (47, 43, "C"),  # stage 3: back to the ceiling past gap 3
}
# Ground currents: (x, z) -> (dx, dz).
# Stage 2: the column (48, 37) -> (48, 38) -> (48, 39). The plug stone
# is pushed down the column onto (48, 39); the slide stops at (48, 38).
# Stage 3: (47, 43) slides north onto the landed stone at (47, 42).
CURRENTS = {(48, 37): (0, 1), (48, 38): (0, 1), (48, 39): (0, 1),
            (47, 43): (0, -1)}

# Checkpoints, in order. Checkpoint 0 is the puzzle entry in the
# solver's numbering (the engine rule is checkpoint 0 = map entry;
# the rift-entry checkpoint at (20, 1, 12) on the ground is checkpoint
# 0 of the full map table and is outside this puzzle model, which
# starts at the ceiling entry). No checkpoint is a rune landing or a
# jump landing.
CHECKPOINTS = [
    (49, 28, "C"),  # CP1: first walked ceiling tile past the jump landing
    (44, 30, "C"),  # CP2: before stone 1 is pushed
    (48, 36, "C"),  # CP3: before stone 2 is pushed; forced before
                    # reset 2 (48, 37), so a reset cannot undo stone 1
                    # after stage 1 is complete (see the design doc)
    (49, 42, "C"),  # CP4: before stone 3 is pushed
]
CP_INDEX = {(x, z, s): i for i, (x, z, s) in enumerate(CHECKPOINTS)}
GOAL = (47, 45, "C")  # totem trigger: ceiling, z >= 45 (the island)
START_PLAYER = (49, 27, "C")

# Stones, in engine-b form: (surface, x, z, state). RESTING = pushable
# BLOCKED actor tile; LANDED = SOLID walkable terrain; FALLING is
# modelled as instant (a push into a designated edge lands at once).
# S1-S3 are the ceiling stones; S4 is the ground plug stone, which
# spawns RESTING on the stage-2 current column at (48, 37) — it is the
# current-path obstacle the player pushes down the column to (48, 39).
SPAWN = (("C", 44, 31, "RESTING"), ("C", 49, 37, "RESTING"),
         ("C", 48, 42, "RESTING"), ("G", 48, 37, "RESTING"))
# Designated edges: (surface, x, z) -> (landing surface, x, z).
# Each ceiling gap is an edge for the ceiling stone above it.
EDGES = {("C", 44, 34): ("G", 44, 34), ("C", 49, 40): ("G", 49, 40),
         ("C", 47, 42): ("G", 47, 42)}
# Landing tiles, reserved per stone: no pushes onto them, no other
# stone lands there. Each ceiling stone's landing is its own gap's.
LANDINGS = {("G", 44, 34), ("G", 49, 40), ("G", 47, 42)}
# Protected tiles (engine-b table: protectedTiles). Engine-b does
# NOT auto-protect engine-a checkpoints / reset sigils, so the table
# lists them: CP0 (20, 1, 12) ground, CP1 (49, 28) ceiling,
# CP2 (44, 30) ceiling, CP3 (48, 36) ceiling, CP4 (49, 42) ceiling,
# reset 1 (45, 29) ceiling, reset 2 (48, 37) ceiling. 7 of max 8.
# A push whose target is a protected tile fails.
PROTECTED = {("G", 20, 12), ("C", 49, 28), ("C", 44, 30),
             ("C", 48, 36), ("C", 49, 42), ("C", 45, 29), ("C", 48, 37)}
DIRS = {"N": (0, -1), "S": (0, 1), "W": (-1, 0), "E": (1, 0)}


def stone_at(surf, x, z, stones):
    """(index, state) of the stone at (surf, x, z), or (None, None)."""
    for i, st in enumerate(stones):
        if st[0] == surf and st[1] == x and st[2] == z:
            return i, st[3]
    return None, None


def tile_kind(surf, x, z, stones):
    """Tile kind: WALK / VOID / BLOCKED / STONE_RESTING / STONE_LANDED."""
    idx, state = stone_at(surf, x, z, stones)
    if idx is not None:
        return "STONE_LANDED" if state == "LANDED" else "STONE_RESTING"
    if surf == "C":
        if (x, z) in CEIL_VOID:
            return "VOID"
        return "WALK" if (x, z) in CEIL_WALK else "BLOCKED"
    if (x, z) in GROUND_VOID:
        return "VOID"
    return "WALK" if (x, z) in GROUND_WALK else "BLOCKED"


def _checkpoint(state_parts, nstones):
    """(cp, snapshot) after landing on the current tile, if it is one."""
    px, pz, psurf, ncp, nsnap = state_parts
    if (px, pz, psurf) in CP_INDEX:
        return CP_INDEX[(px, pz, psurf)], tuple(nstones)
    return ncp, nsnap


def step(state, dx, dz):
    """One player input step. Returns (new_state, tile_moves) or (None, 0).

    State = (player (x, z, surf), stones, checkpoint_index, snapshot).
    A fall returns the player/stones to the checkpoint snapshot (cost 1
    for the step onto the VOID tile). A reset sigil restores the stones
    to the checkpoint snapshot and leaves the player where they are.
    A push moves a RESTING stone one tile and the player into its tile;
    a push into a designated edge makes the stone LANDED at the landing.
    """
    (x, z, surf), stones, cp, snap = state
    nx, nz = x + dx, z + dz
    kind = tile_kind(surf, nx, nz, stones)
    pushed = False  # a push step's slide is a no-op start/stop (see below)
    nstones = list(stones)
    ncp, nsnap = cp, snap
    if kind == "STONE_RESTING":
        idx = [i for i, st in enumerate(stones)
               if st[0] == surf and st[1] == nx and st[2] == nz][0]
        sx, sy = nx + dx, nz + dz
        # Push-block rules (engine-b section 3).
        if (surf, sx, sy) in EDGES:
            # Designated edge: fall, unless a landing clash.
            landing = EDGES[(surf, sx, sy)]
            if any(st[0] == landing[0] and st[1] == landing[1]
                   and st[2] == landing[2] for st in stones):
                return None, 0  # landing clash
            nstones[idx] = (landing[0], landing[1], landing[2], "LANDED")
        elif (surf, sx, sy) in LANDINGS:
            return None, 0  # landing tiles are reserved: never push there
        elif (surf, sx, sy) in PROTECTED:
            return None, 0  # protected tile (checkpoint / reset sigil)
        elif tile_kind(surf, sx, sy, stones) != "WALK":
            # Target is BLOCKED / VOID (not a designated edge) /
            # another stone.
            return None, 0
        else:
            nstones[idx] = (surf, sx, sy, "RESTING")
        pushed = True
        px, pz, psurf = nx, nz, surf
    elif kind == "VOID":
        cx, cz, csurf = CHECKPOINTS[cp]
        return ((cx, cz, csurf), snap, cp, snap), 1  # fall -> checkpoint
    elif kind in ("WALK", "STONE_LANDED"):
        px, pz, psurf = nx, nz, surf
    else:
        return None, 0  # BLOCKED
    moves = 1
    # Checkpoint at the stepped-onto tile.
    ncp, nsnap = _checkpoint((px, pz, psurf, ncp, nsnap), nstones)
    # Reset sigil: stones back to the checkpoint snapshot.
    if psurf == "C" and (px, pz) in RESETS:
        nstones = list(nsnap)
    # Rune: surface change in place (0 extra steps). No checkpoint
    # check at the landing tile (see the module docstring).
    if psurf == "C" and (px, pz) in RUNES_C:
        px, pz, psurf = RUNES_C[(px, pz)]
    elif psurf == "G" and (px, pz) in RUNES_F:
        px, pz, psurf = RUNES_F[(px, pz)]
    # Current slide: one tile at a time until blocked / stone /
    # off-current. A slide never pushes a stone. A push step onto
    # a current tile still reaches the step hook, so the slide
    # starts — but it immediately stops before the BLOCKED actor
    # tile of the stone just pushed there (no extra tile move).
    # `while not pushed` collapses that immediate start/stop with
    # zero movement.
    while not pushed and psurf == "G" and (px, pz) in CURRENTS:
        cdx, cdz = CURRENTS[(px, pz)]
        tx, tz = px + cdx, pz + cdz
        tkind = tile_kind(psurf, tx, tz, nstones)
        if tkind in ("BLOCKED", "STONE_RESTING"):
            break  # plugged / blocked: slide stops before the stone
        if tkind == "VOID":
            cx, cz, csurf = CHECKPOINTS[ncp]
            # Slide onto VOID = fall to the (possibly updated) checkpoint.
            return ((cx, cz, csurf), tuple(nsnap), ncp, tuple(nsnap)), moves + 1
        px, pz = tx, tz
        moves += 1
        ncp, nsnap = _checkpoint((px, pz, psurf, ncp, nsnap), nstones)
        # A LANDED stone is walkable terrain: the slide passes over it
        # and, if it is off-current, the slide ends there.
    return ((px, pz, psurf), tuple(nstones), ncp, tuple(nsnap)), moves


def neighbours(state):
    for d in DIRS.values():
        out = step(state, *d)
        if out[0] is not None:
            yield out


def initial_state():
    return (START_PLAYER, SPAWN, 0, SPAWN)


def solve():
    """Dijkstra (edges have variable cost: a slide is >1 tile moves)."""
    import heapq
    init = initial_state()
    parent = {init: None}
    cost = {init: 0}
    heap = [(0, init)]
    goal = None
    while heap:
        c, s = heapq.heappop(heap)
        if c != cost[s]:
            continue
        if s[0] == GOAL:
            goal = s
            break
        for ns, moves in sorted(neighbours(s)):
            nc = c + moves
            if ns not in cost or nc < cost[ns]:
                cost[ns] = nc
                parent[ns] = s
                heapq.heappush(heap, (nc, ns))
    if goal is None:
        raise SystemExit("no solution")
    path = []
    s = goal
    while s is not None:
        path.append(s)
        s = parent[s]
    path.reverse()
    return cost[goal], path


def explore():
    """Full reachable set, and the set of states that can reach the goal."""
    from collections import deque
    init = initial_state()
    reachable, edges = set([init]), {}
    q = deque([init])
    while q:
        s = q.popleft()
        nxt = [ns for ns, _ in sorted(neighbours(s))]
        edges[s] = nxt
        for ns in nxt:
            if ns not in reachable:
                reachable.add(ns)
                q.append(ns)
    can_reach = set(s for s in reachable if s[0] == GOAL)
    q = deque(can_reach)
    rev = {}
    for s, nxts in edges.items():
        for ns in nxts:
            rev.setdefault(ns, []).append(s)
    while q:
        s = q.popleft()
        for p in rev.get(s, []):
            if p not in can_reach:
                can_reach.add(p)
                q.append(p)
    return reachable, can_reach


def fall_scenarios(reachable):
    """One fall per stage, from states asserted to be reachable.

    Stage 1: after dropping stone 1, stepped south from (44,33,C)
    onto the ceiling gap (44,34) instead of east to the rune.
    Stage 2: after dropping stone 2, stepped south from (49,39,C)
    onto the ceiling gap (49,40) instead of west to the rune.
    Stage 3: after returning upstairs, stepped north from (47,43,C)
    into the ceiling gap (47,42) instead of walking to the totem.
    """
    cases = [
        ("stage 1: ceiling gap (44,34) after dropping stone 1",
         ((44, 33, "C"), (("G", 44, 34, "LANDED"), ("C", 49, 37, "RESTING"),
                          ("C", 48, 42, "RESTING"), ("G", 48, 37, "RESTING")),
          1, SPAWN), (0, 1)),
        ("stage 2: ceiling gap (49,40) after dropping stone 2",
         ((49, 39, "C"), (("G", 44, 34, "LANDED"), ("G", 49, 40, "LANDED"),
                          ("C", 48, 42, "RESTING"), ("G", 48, 37, "RESTING")),
          2, (("G", 44, 34, "LANDED"), ("C", 49, 37, "RESTING"),
              ("C", 48, 42, "RESTING"), ("G", 48, 37, "RESTING"))), (0, 1)),
        ("stage 3: ceiling gap (47,42) after returning upstairs",
         ((47, 43, "C"), (("G", 44, 34, "LANDED"), ("G", 49, 40, "LANDED"),
                          ("G", 47, 42, "LANDED"), ("G", 48, 39, "RESTING")),
          3, (("G", 44, 34, "LANDED"), ("G", 49, 40, "LANDED"),
              ("C", 48, 42, "RESTING"), ("G", 48, 39, "RESTING"))), (0, -1)),
    ]
    out = []
    for label, setup, d in cases:
        assert setup in reachable, f"fall setup not reachable: {label} {setup}"
        st, _ = step(setup, *d)
        out.append((label, st))
    return out


def main():
    cost, path = solve()
    reachable, can_reach = explore()
    print(f"optimal solution: {cost} steps (tile moves)")
    print(f"reachable states: {len(reachable)}")
    print(f"states that can reach the totem: {len(can_reach)}")
    print(f"soft-lock free: {reachable == can_reach}")
    # No stage can be skipped: every state that reaches the totem must
    # have all three ceiling stones LANDED on the ground (a reset can
    # never undo a completed stage, because the next checkpoint is
    # forced before the next reset sigil).
    goal_states = [s for s in reachable if s[0] == GOAL]
    dropped = (("G", 44, 34, "LANDED"), ("G", 49, 40, "LANDED"),
               ("G", 47, 42, "LANDED"), ("G", 48, 39, "RESTING"))
    print(f"goal states: {len(goal_states)}; "
          f"all with all stones dropped: "
          f"{all(s[1] == dropped for s in goal_states)}")
    assert all(s[1] == dropped for s in goal_states)
    print("solution (player, stones, checkpoint):")
    prev = None
    for s in path:
        (x, z, surf), stones, cp, _ = s
        acts = ""
        if prev is not None:
            acts = f"  <- from {prev[0]}"
        print(f"  {surf} ({x},{z}) stones={stones} cp={cp}{acts}")
        prev = s
    print("fall scenarios (post-fall player, stones, checkpoint):")
    for label, st in fall_scenarios(reachable):
        print(f"  {label}: -> {st[0]} stones={st[1]} cp={st[2]}")
    # Engine-a table budget: tiles = explicit overrides (landing tiles
    # have none); currents / runes / sigils / checkpoints as listed.
    # Current tiles need their own SOLID overrides (they are all in
    # GROUND_WALK above); landing tiles each have an explicit VOID
    # override (counted in len(GROUND_VOID) below, which also holds
    # the (48, 40) hazard).
    # 8 ceiling + GROUND_WALK shelves + GROUND_VOID (3 landings +
    # (48, 40) hazard). Exactly at the 32 cap: 8 + 20 + 4 = 32.
    n_tiles = (len(CEIL_VOID) + len(RUNES_C) + len(RESETS)
               + len(GROUND_WALK) + len(GROUND_VOID))
    print(f"engine table budget: tiles {n_tiles}<=32, currents "
          f"{len(CURRENTS)}<=16, runes {len(RUNES_C) + len(RUNES_F)}<=8, "
          f"sigils {len(RESETS)}<=16, checkpoints {len(CHECKPOINTS) + 1}<=8, "
          f"stones {len(SPAWN)}<=4 (engine-b max), protected {len(PROTECTED)}<=8")


if __name__ == "__main__":
    main()
