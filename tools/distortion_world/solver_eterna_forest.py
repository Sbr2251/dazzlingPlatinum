#!/usr/bin/env python3
"""Standalone solver for the DW Eterna Forest puzzle (rift #2).

Design: docs/distortion_world/eterna_forest.md. Semantics follow the
engine-a API (include/overlay009/dw_puzzle.h) as published in commit
623ccce7ee, plus the honeycomb timer in src/overlay009/ov9_02249960.c:

- Surfaces: FLOOR (y=1), EAST_WALL (x=49), CEILING (y=10). A state is
  (pos, bridge, just_landed, checkpoint, snap1, snap2, [phase]).
- A rune fires on a WALKED step onto its tile. A landing from a rune
  flip does NOT fire that rune (just_landed suppresses it until the
  player steps off the tile). Landing DOES fire sigils and checkpoints.
- The sigil is SET (latching): landing on (45,1,37) sets bridge ON.
- A fall restores the player to the last checkpoint and the bridge
  snapshot taken there (snap0 is always OFF).
- Honeycomb: ceiling (44..45, 33..36). Phase cycle 213 frames:
  solid [0,153), gone [153,213). A move costs 16 frames; a move that
  lands on a rune costs 32 (step + flip); WAIT costs 1 frame; a fall
  costs 60 frames (fade + warp). Stepping onto the honeycomb while
  gone, or ending an action on it while gone, is a fall.
- The fold (step onto (17,12)) warps to (40,22) for free. The stock
  surface jumps are modelled as moves: (48,22)+x -> wall (49,1,21);
  wall (49,1,21)-y -> (48,22); wall (49,9,27)+y -> ceiling (49,10,27)
  (jump takes precedence over the plain wall step to (49,10,27));
  ceiling (49,10,27)+x -> wall (49,9,27).
- Goal: any ceiling tile with z >= 41 (the totem trigger).

Proofs:
1. Abstract graph (phase abstracted away; a fall from any honeycomb
   tile is always available because the player can wait until the
   honeycomb goes): Dijkstra gives the minimum move count, and
   forward-reachable vs reverse-reachable-from-goal shows every
   reachable state can reach the totem (no soft-lock). The abstraction
   only ADDS transitions (phase only ever gates the honeycomb, and the
   crossing can always be aligned by waiting - see 2), so the abstract
   proof covers every concretely reachable state.
2. Concrete path check: the documented 38-step path is simulated for
   every honeycomb start phase (0..212), with greedy waits at the safe
   tile (45,10,32) before the honeycomb crossing.

Harness note: this file is standalone until tools/distortion_world/emu/
solver.py (harness workstream) lands; it uses the same semantics that
file will use, and its model tables (RUNES, SIGIL_TILE, BRIDGE_TILES,
CHECKPOINTS) are the puzzle table in code form.
"""

import heapq
from collections import deque

# --- surfaces -----------------------------------------------------------------
FLOOR, WALL, CEIL = 0, 1, 2

# --- honeycomb timer (field frames) -------------------------------------------
HONEY_SOLID, HONEY_FADE, HONEY_GONE = 120, 33, 60
HONEY_CYCLE = HONEY_SOLID + HONEY_FADE + HONEY_GONE  # 213
HONEY_GONE_START = HONEY_SOLID + HONEY_FADE          # 153
STEP_FRAMES, FLIP_EXTRA_FRAMES, WAIT_FRAMES, FALL_FRAMES = 16, 16, 1, 60

# --- geometry (verified against tools/distortion_world/eterna_forest.json) ----
# Floor: entry walkway, hive strip, Rune B platform.
FLOOR_TILES = {(x, 12) for x in range(17, 23)}
FLOOR_TILES |= {(x, z) for x in range(32, 49) for z in (22, 23)}
FLOOR_TILES |= {(45, 37), (46, 37)}

# East wall x=49: (y, z), rows y=1..10 bottom->top, from twarc dump 597.
_WALL_ROWS = ["........##", "........##", "........##", "####......",
              "####......", "####......", "#######...", "#######...",
              "#######...", "#######..."]
WALL_TILES = {(1 + i, 20 + j) for i, row in enumerate(_WALL_ROWS)
              for j, c in enumerate(row) if c == "."}

# Ceiling y=10: (x, z). Stock grid, WITHOUT the bridge gap (gap tiles are
# walkable iff bridge is on; they exist as positions either way).
_CEIL_ROWS = ["........####.##########", "........####.##########",
              "##......####...........", "##......####...........",
              "##......****...........", "##......****..........."]
CEIL_TILES = {(49 - i, 25 + j) for i, row in enumerate(_CEIL_ROWS)
              for j, c in enumerate(row) if c in ".*"}
HONEY_TILES = {(x, z) for x in (44, 45) for z in range(33, 37)}
BRIDGE_TILES = {(x, z) for x in range(44, 48) for z in (39, 40)}

# Rune pairs: (surface, x, y, z) <-> (surface, x, y, z). A rune tile is
# its own pair key.
RUNES = {
    (WALL, 49, 1, 25): (CEIL, 49, 10, 25),
    (CEIL, 49, 10, 25): (WALL, 49, 1, 25),
    (CEIL, 45, 10, 37): (FLOOR, 45, 1, 37),
    (FLOOR, 45, 1, 37): (CEIL, 45, 10, 37),
}
SIGIL_TILE = (FLOOR, 45, 1, 37)  # SET 1 (bridge on); = Rune B floor tile
CHECKPOINTS = [(FLOOR, 20, 1, 12), (CEIL, 49, 10, 25), (CEIL, 45, 10, 37)]
CP_INDEX = {cp: i for i, cp in enumerate(CHECKPOINTS)}
START = (FLOOR, 20, 1, 12)

DELTAS = {
    FLOOR: [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)],
    WALL: [(0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)],
    CEIL: [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)],
}


def _walkable(pos, bridge):
    surf, x, y, z = pos
    if surf == FLOOR:
        return (x, z) in FLOOR_TILES
    if surf == WALL:
        return (y, z) in WALL_TILES
    return (x, z) in CEIL_TILES and ((x, z) not in BRIDGE_TILES or bridge)


def _is_honey(pos):
    return pos[0] == CEIL and (pos[1], pos[3]) in HONEY_TILES


def _is_goal(pos):
    return pos[0] == CEIL and pos[3] >= 41


def _raw_dest(pos, delta, bridge):
    """One walked step (no rune flip yet). Returns dest pos or None."""
    surf, x, y, z = pos
    dx, dy, dz = delta
    nx, ny, nz = x + dx, y + dy, z + dz
    # Stock surface jumps (jump takes precedence over a plain step).
    if pos == (FLOOR, 48, 1, 22) and delta == (1, 0, 0):
        return (WALL, 49, 1, 21)
    if pos == (WALL, 49, 1, 21) and delta == (0, -1, 0):
        return (FLOOR, 48, 1, 22)
    if pos == (WALL, 49, 9, 27) and delta == (0, 1, 0):
        return (CEIL, 49, 10, 27)
    if pos == (CEIL, 49, 10, 27) and delta == (1, 0, 0):
        return (WALL, 49, 9, 27)
    cand = (surf, nx, ny, nz)
    if not _walkable(cand, bridge):
        return None
    # The fold: stepping onto (17,12) warps to the hive (40,22).
    if cand == (FLOOR, 17, 1, 12):
        return (FLOOR, 40, 1, 22)
    return cand


def apply_move(state, delta):
    """Abstract transition for one walked step. Returns (state, kind)
    with kind in {'walk', 'flip', 'blocked'}; state has no phase."""
    pos, bridge, just_landed, cp, snap1, snap2 = state
    dest = _raw_dest(pos, delta, bridge)
    if dest is None:
        return state, "blocked"
    flipped = False
    if dest in RUNES and not just_landed:
        dest = RUNES[dest]
        flipped = True
        just_landed = True
    else:
        just_landed = False
    if dest == SIGIL_TILE:
        bridge = True
    if dest in CP_INDEX:
        cp = CP_INDEX[dest]
        if cp == 1:
            snap1 = bridge
        elif cp == 2:
            snap2 = bridge
    return (dest, bridge, just_landed, cp, snap1, snap2), ("flip" if flipped else "walk")


def apply_fall(state):
    """Fall to the last checkpoint with its snapshot."""
    pos, bridge, just_landed, cp, snap1, snap2 = state
    bridge = (False, snap1, snap2)[cp]
    return (CHECKPOINTS[cp], bridge, False, cp, snap1, snap2)


def successors(state):
    """Abstract successors: (new_state, cost, label). Fall costs 0 moves
    (it is a consequence, not a step); it is only listed from honeycomb
    tiles, where waiting until GONE is always possible."""
    out = []
    for d in DELTAS[state[0][0]]:
        ns, kind = apply_move(state, d)
        if kind != "blocked":
            out.append((ns, 1, f"move {d} ({kind})"))
    if _is_honey(state[0]):
        out.append((apply_fall(state), 0, "fall -> checkpoint"))
    return out


def all_positions():
    poss = [(FLOOR, x, 1, z) for (x, z) in FLOOR_TILES]
    poss += [(WALL, 49, y, z) for (y, z) in WALL_TILES]
    poss += [(CEIL, x, 10, z) for (x, z) in CEIL_TILES]
    return poss


def build_graph():
    """Full abstract transition graph: state -> [(state, cost, label)]."""
    graph = {}
    for pos in all_positions():
        for bridge in (False, True):
            for jl in (False, True):
                for cp in range(3):
                    for snap1 in (False, True):
                        for snap2 in (False, True):
                            st = (pos, bridge, jl, cp, snap1, snap2)
                            graph[st] = successors(st)
    return graph


def dijkstra(graph, start):
    dist, prev = {start: 0}, {}
    pq = [(0, start)]
    while pq:
        d, st = heapq.heappop(pq)
        if d != dist[st]:
            continue
        if _is_goal(st[0]):
            return d, st, prev, dist
        for ns, cost, label in graph[st]:
            nd = d + cost
            if nd < dist.get(ns, 1 << 30):
                dist[ns] = nd
                prev[ns] = (st, label)
                heapq.heappush(pq, (nd, ns))
    return None, None, prev, dist


def reconstruct(prev, goal):
    path, st = [], goal
    while st in prev:
        pst, label = prev[st]
        path.append(label)
        st = pst
    return list(reversed(path))


def soft_lock_proof(graph, start):
    """Forward-reachable vs reverse-reachable-from-goal on the abstract graph."""
    fwd, dq = {start}, deque([start])
    while dq:
        for ns, _, _ in graph[dq.popleft()]:
            if ns not in fwd:
                fwd.add(ns)
                dq.append(ns)
    rev_adj = {}
    for st, outs in graph.items():
        for ns, _, _ in outs:
            rev_adj.setdefault(ns, []).append(st)
    goals = [st for st in graph if _is_goal(st[0])]
    rev, dq = set(goals), deque(goals)
    while dq:
        for ps in rev_adj.get(dq.popleft(), []):
            if ps not in rev:
                rev.add(ps)
                dq.append(ps)
    stranded = fwd - rev
    return len(fwd), len(rev), len(stranded), sorted(stranded)[:5]


# --- concrete simulation: the documented 38-step path, all phases --------
# Moves as world deltas; the path is the design doc's solution.
PATH = ([(-1, 0, 0)] * 3 + [(1, 0, 0)] * 8 + [(1, 0, 0)]
        + [(0, 0, 1)] * 4 + [(0, 0, 1)] * 2 + [(-1, 0, 0)] * 4
        + [(0, 0, 1)] * 5 + [(0, 0, 1)] * 4 + [(0, 0, 1)]
        + [(1, 0, 0)] + [(-1, 0, 0)] + [(0, 0, 1)] * 4)
WAIT_TILE = (CEIL, 45, 10, 32)  # safe tile before the honeycomb


def _safe_to_cross(phase):
    """The next 4 moves (all onto honeycomb) must end in the solid window."""
    return all((phase + STEP_FRAMES * k) % HONEY_CYCLE < HONEY_GONE_START
               for k in (1, 2, 3, 4))


def simulate_path(start_phase):
    """Returns (moves, waits, falls, frames) or raises AssertionError."""
    state = (START, False, False, 0, False, False)
    phase, waits, falls = start_phase, 0, 0
    for i, d in enumerate(PATH):
        # Greedy wait before the honeycomb crossing.
        if state[0] == WAIT_TILE and i == 27:  # next 4 moves are the crossing
            while not _safe_to_cross(phase):
                phase = (phase + WAIT_FRAMES) % HONEY_CYCLE
                waits += 1
                assert waits < 1000, "wait loop did not converge"
        before = state
        state, kind = apply_move(state, d)
        assert kind != "blocked", f"path blocked at step {i} {before} {d}"
        phase = (phase + STEP_FRAMES + (FLIP_EXTRA_FRAMES if kind == "flip" else 0)) % HONEY_CYCLE
        if _is_honey(state[0]) and phase >= HONEY_GONE_START:
            state, falls = apply_fall(state), falls + 1
            phase = (phase + FALL_FRAMES) % HONEY_CYCLE
            assert False, f"path fell at step {i} (phase {phase})"
    assert _is_goal(state[0]), f"path did not reach totem: {state[0]}"
    frames = len(PATH) * STEP_FRAMES + waits * WAIT_FRAMES
    return len(PATH), waits, falls, frames


def main():
    start = (START, False, False, 0, False, False)
    graph = build_graph()
    print(f"abstract states: {len(graph)}")
    opt, goal, prev, dist = dijkstra(graph, start)
    print(f"optimal moves (Dijkstra, abstract graph): {opt}")
    print("optimal path (first solution found):")
    for s in reconstruct(prev, goal):
        print(f"  {s}")
    fwd, rev, stranded, sample = soft_lock_proof(graph, start)
    print(f"forward-reachable abstract states: {fwd}")
    print(f"states that can reach the totem: {rev}")
    print(f"stranded (reachable but cannot reach totem): {stranded}")
    assert stranded == 0, f"SOFT-LOCK: {sample}"
    print("no-soft-lock proof: PASS (every reachable state can reach the totem)")
    assert opt == len(PATH), f"documented path {len(PATH)} != optimal {opt}"
    print(f"documented path length {len(PATH)} == optimal: PASS")
    # Concrete check for every honeycomb start phase.
    worst_waits, worst_frames, worst_phase = 0, 0, None
    for ph in range(HONEY_CYCLE):
        moves, waits, falls, frames = simulate_path(ph)
        assert (moves, falls) == (len(PATH), 0), (ph, moves, falls)
        if waits > worst_waits:
            worst_waits, worst_frames, worst_phase = waits, frames, ph
    print(f"concrete path verified for all {HONEY_CYCLE} honeycomb start phases: "
          f"moves={len(PATH)} falls=0")
    print(f"worst-case waits: {worst_waits} frames (start phase {worst_phase}); "
          f"worst-case total {worst_frames} frames "
          f"({worst_frames / 30:.1f}s at 30 fps); waits are not steps")
    print("ALL CHECKS PASS")


if __name__ == "__main__":
    main()
