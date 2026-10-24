#!/usr/bin/env python3
"""Solver model for DW Route 213, the Drowned Lake (rift #4, difficulty 5).

Standalone BFS/Dijkstra over the puzzle model, with the engine-a
semantics from ``include/overlay009/dw_puzzle.h`` (commit 623ccce7ee
on dw/engine-a):

* tile overrides: SOLID / VOID (step = fall) / BLOCKED, consulted by
  the walk check on every surface, floor included;
* currents: stepping on a current tile starts a slide in its FACE_*
  dir until blocked, stopped by an actor block / a stone, or
  off-current; landing on a sigil / rune / checkpoint ends the slide;
* sigils: RESET restores the puzzle to the last checkpoint snapshot
  (player does not move);
* checkpoints: stepping on one snapshots the puzzle (here, the stone
  positions) and makes it the fall target. A fall restores the player
  and the stones to the last checkpoint snapshot. No checkpoint is a
  rune landing: every checkpoint is reached by walking (engine-a's
  rune starts a jump task and does not promise a step-hook call at
  its destination), so the solver does not check for a checkpoint
  on a rune landing tile;
* runes: stepping on a rune tile changes surface in place to its target;
* stones (engine-b, via ``DwPuzzle_SetActorBlock``): a stone on a
  tile makes that tile BLOCKED for walking. On the ceiling a stone is
  pushable. Pushed into a VOID gap tile it falls to the floor at that
  (x, z) and stays there as an actor block: it stops a slide that
  would enter its tile (it plugs the current) and the player walks
  *around* it, never onto it. The causeway's outer rim blocks stones
  at the slab edge: a stone pushed at an edge stops, so a stone can
  only leave the ceiling through a gap. A stone pushed into a
  BLOCKED tile is blocked (water tiles are walls for stones).

Coordinates are DW world tiles (x, z) plus a surface: 'C' = ceiling
(y = 10), 'F' = floor (y = 1). The puzzle is counted from the ceiling
entry checkpoint (49, 27) to the totem trigger (any ceiling tile with
z >= 45). One tile move (walk, push, or slide step) = 1 step; a rune
surface change costs 0 steps. The rift entry-to-wall approach is plain
travel, not puzzle, and is not counted.

Run: ``python3 tools/distortion_world/route_213_solver.py``
Prints the optimal solution, difficulty stats, fall scenarios, and the
soft-lock proof (every reachable state can reach the totem).
"""

# Ceiling causeway, from tools/distortion_world/route_213.json (platform
# rows: x = 49 - row, columns z = 25 + col, '.' = walkable).
_CEIL_ROWS = [
    "##....#####.......#####",
    "#####.#####.#####.#....",
    "#####.#####.#####......",
    "#####.#####.#####......",
    "#####.#####.#####.#....",
    "#####.......#####.#####",
]
CEIL_BASE = set()
for _r, _line in enumerate(_CEIL_ROWS):
    for _c, _ch in enumerate(_line):
        if _ch == ".":
            CEIL_BASE.add((49 - _r, 25 + _c))

# Ceiling VOID gaps (explicit overrides): the three drop chutes.
CEIL_VOID = {(44, 34), (49, 40), (47, 42)}
# Ceiling alcove tiles (SOLID overrides, drawn as rune / sigil circles):
# rune-down tiles and reset-sigil tiles. RESETS are engine sigils.
RUNES_C = {  # (x, z) -> (target x, target z, target surface)
    (45, 33): (47, 33, "F"),  # stage 1: down to the floor detour
    (48, 39): (49, 34, "F"),  # stage 2: down to the floor detour
    (48, 43): (43, 43, "F"),  # stage 3: down to the floor detour
}
RESETS = {(45, 29), (48, 37)}  # stage 1 / 2 reset sigils (RESET kind)
# Reset sigils sit BEFORE their stage's stone (reachable from the
# pre-stage path only), so stepping on one can never undo a push
# the player has already walked past: returning to one passes a
# checkpoint, which snapshots the pushed stones first.
CEIL_WALK = CEIL_BASE | set(RUNES_C) | RESETS

# Floor detour tiles (SOLID overrides, drawn as sunken reef shelves).
# No floor tile is ever a stone tile the player stands on: a dropped
# stone is a BLOCKED actor, and the player walks around it.
FLOOR_WALK = {
    # stage 1: landing, snake to the current (the ONLY way on), rune-up
    # west of the stop tile. (45,34)/(45,35) are deliberately NOT
    # shelves: a shelf there would let the player walk around the
    # current and skip stone 1.
    (47, 33), (47, 32), (46, 32), (45, 32), (45, 33), (44, 33), (43, 33),
    # stage 2: approach, current, stop tile, walk west twice to rune-up
    (49, 34), (49, 35), (49, 36), (49, 37), (49, 38), (49, 39), (48, 39),
    (47, 39),
    # stage 3: approach, current, rune-up east of it
    (43, 43), (44, 43), (45, 43), (46, 43), (47, 43), (48, 43),
}
# Floor tiles that are VOID until a dropped stone lands on them (as a
# BLOCKED actor that plugs the current sliding into them).
FLOOR_VOID = {(44, 34), (49, 40), (47, 42)}
RUNES_F = {  # (x, z) -> (target x, target z, target surface)
    (43, 33): (44, 35, "C"),  # stage 1: back to the ceiling past gap 1
    (47, 39): (49, 41, "C"),  # stage 2: back to the ceiling past gap 2
    (48, 43): (47, 43, "C"),  # stage 3: back to the ceiling past gap 3
}
# Floor currents: (x, z) -> (dx, dz). Each stage's current chain
# ends at its stage's stone, which stops the slide. A chain of two
# or three current tiles makes the slide a real move, not a 0-step
# stop: stage 1 slides west then south, stage 2 slides south three
# tiles, stage 3 slides east then north.
CURRENTS = {(45, 33): (-1, 0), (44, 33): (0, 1),
            (49, 37): (0, 1), (49, 38): (0, 1), (49, 39): (0, 1),
            (46, 43): (1, 0), (47, 43): (0, -1)}

# Checkpoints, in order. Checkpoint 0 is the puzzle entry (the engine
# rule is checkpoint 0 = map entry; the rift-entry checkpoint at
# (20, 1, 12) on the floor is checkpoint 0 of the full map table and is
# outside this puzzle model, which starts at the ceiling entry).
# No checkpoint is a rune landing: every checkpoint below is reached
# by walking (the normal step hook). Engine-a's rune starts a jump
# task and does not promise a step-hook call at the destination, so
# the design never relies on one. In particular there is no
# checkpoint at (49, 41), the stage-2 rune-up landing.
CHECKPOINTS = [
    (49, 28, "C"),  # CP1: first walked ceiling tile past the jump
                    # landing at (49, 27) (the stock wall->ceiling jump
                    # does not promise a step-hook call, so the
                    # checkpoint is one step south of the landing)
    (44, 30, "C"),  # CP2: before stone 1 is pushed
    (48, 36, "C"),  # CP3: before stone 2 is pushed; forced before
                    # reset 2 (48, 37), so a reset cannot undo stone 1
                    # after stage 1 is complete (see the design doc)
    (49, 42, "C"),  # CP4: before stone 3 is pushed
]
CP_INDEX = {(x, z, s): i for i, (x, z, s) in enumerate(CHECKPOINTS)}
GOAL = (47, 45, "C")  # totem trigger: ceiling, z >= 45 (the island)
START_PLAYER = (49, 27, "C")

# Stones: (surface, x, z). A stone is an actor block wherever it is.
SPAWN = (("C", 44, 31), ("C", 49, 37), ("C", 48, 42))
DIRS = {"N": (0, -1), "S": (0, 1), "W": (-1, 0), "E": (1, 0)}


def tile_kind(surf, x, z, stones):
    """Tile kind: WALK / VOID / BLOCKED / STONE_CEIL / STONE.

    STONE (a dropped stone on the floor, or any stone the player is
    not pushing) is BLOCKED for walking. STONE_CEIL is a pushable
    stone on the ceiling.
    """
    for st in stones:
        if st == (surf, x, z):
            return "STONE_CEIL" if surf == "C" else "STONE"
    if surf == "C":
        if (x, z) in CEIL_VOID:
            return "VOID"
        return "WALK" if (x, z) in CEIL_WALK else "BLOCKED"
    if (x, z) in FLOOR_VOID:
        return "VOID"
    return "WALK" if (x, z) in FLOOR_WALK else "BLOCKED"


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
    """
    (x, z, surf), stones, cp, snap = state
    nx, nz = x + dx, z + dz
    kind = tile_kind(surf, nx, nz, stones)
    nstones = list(stones)
    ncp, nsnap = cp, snap
    if kind == "STONE_CEIL":
        sx, sy = nx + dx, nz + dz
        idx = [i for i, st in enumerate(stones) if st == (surf, nx, nz)][0]
        if (sx, sy) in CEIL_VOID and surf == "C":
            nstones[idx] = ("F", sx, sy)  # into the gap: drops to the floor
        elif surf == "C" and not (44 <= sx <= 49 and 27 <= sy <= 47):
            return None, 0  # rim at the slab edge: the stone stops
        else:
            skind = tile_kind(surf, sx, sy, stones)
            if skind == "WALK":
                nstones[idx] = (surf, sx, sy)
            else:
                return None, 0  # stone blocked (wall, water, another stone)
        px, pz, psurf = nx, nz, surf
    elif kind == "VOID":
        cx, cz, csurf = CHECKPOINTS[cp]
        return ((cx, cz, csurf), snap, cp, snap), 1  # fall -> checkpoint
    elif kind == "WALK":
        px, pz, psurf = nx, nz, surf
    else:
        return None, 0  # BLOCKED, or a dropped (floor) stone: impassable
    moves = 1
    # Checkpoint at the stepped-onto tile.
    ncp, nsnap = _checkpoint((px, pz, psurf, ncp, nsnap), nstones)
    # Reset sigil: stones back to the checkpoint snapshot.
    if psurf == "C" and (px, pz) in RESETS:
        nstones = list(nsnap)
    # Rune: surface change in place (0 extra steps). No checkpoint
    # check at the landing tile: engine-a's rune starts a jump task
    # and does not promise a step-hook call there, and no rune
    # target in this design is a checkpoint.
    if psurf == "C" and (px, pz) in RUNES_C:
        px, pz, psurf = RUNES_C[(px, pz)]
    elif psurf == "F" and (px, pz) in RUNES_F:
        px, pz, psurf = RUNES_F[(px, pz)]
    # Current slide: one tile at a time until blocked / stone / off-current.
    while psurf == "F" and (px, pz) in CURRENTS:
        cdx, cdz = CURRENTS[(px, pz)]
        tx, tz = px + cdx, pz + cdz
        tkind = tile_kind(psurf, tx, tz, nstones)
        if tkind in ("BLOCKED", "STONE_CEIL", "STONE"):
            break  # plugged / blocked: slide stops before the stone
        if tkind == "VOID":
            cx, cz, csurf = CHECKPOINTS[ncp]
            # Slide onto VOID = fall to the (possibly updated) checkpoint.
            return ((cx, cz, csurf), tuple(nsnap), ncp, tuple(nsnap)), moves + 1
        px, pz = tx, tz
        moves += 1
        ncp, nsnap = _checkpoint((px, pz, psurf, ncp, nsnap), nstones)
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
    onto the ceiling gap (44,34) instead of going to the rune.
    (The floor current cannot be met with stone 1 undropped: the
    rune-down is only reachable after the drop, and the pre-stage
    reset sigils cannot undo a push the player walked past.)
    Stage 2: after dropping stone 2, stepped south from (49,39,C)
    onto the ceiling gap (49,40) instead of going to the rune.
    Stage 3: after returning upstairs, stepped north from (47,43,C)
    into the ceiling gap (47,42) instead of walking to the totem.
    """
    spawn = SPAWN
    cases = [
        ("stage 1: ceiling gap (44,34) after dropping stone 1",
         ((44, 33, "C"), (("F", 44, 34), ("C", 49, 37), ("C", 48, 42)), 1,
          spawn), (0, 1)),
        ("stage 2: ceiling gap (49,40) after dropping stone 2",
         ((49, 39, "C"), (("F", 44, 34), ("F", 49, 40), ("C", 48, 42)), 2,
          (("F", 44, 34), ("C", 49, 37), ("C", 48, 42))), (0, 1)),
        ("stage 3: ceiling gap (47,42) after returning upstairs",
         ((47, 43, "C"), (("F", 44, 34), ("F", 49, 40), ("F", 47, 42)), 3,
          (("F", 44, 34), ("F", 49, 40), ("C", 48, 42))), (0, -1)),
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
    # have all three stones dropped on the floor (a reset can never
    # undo a completed stage, because the next checkpoint is forced
    # before the next reset sigil).
    goal_states = [s for s in reachable if s[0] == GOAL]
    dropped = (("F", 44, 34), ("F", 49, 40), ("F", 47, 42))
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
    print("engine table budget: tiles <= 32, currents <= 16, runes <= 8, "
          "sigils <= 16, checkpoints <= 8, stones <= 8")


if __name__ == "__main__":
    main()
