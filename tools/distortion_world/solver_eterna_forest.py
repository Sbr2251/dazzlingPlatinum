#!/usr/bin/env python3
"""Standalone solver for the DW Eterna Forest puzzle (rift #2).

Design: docs/distortion_world/eterna_forest.md. Semantics follow the
engine-a API (include/overlay009/dw_puzzle.h) as published in commit
623ccce7ee, plus the honeycomb timer in src/overlay009/ov9_02249960.c.

Key semantic rules (design section 7):
- A rune fires on a WALKED step onto its tile. A landing from a rune
  flip fires NOTHING (in particular it does not re-fire the rune:
  otherwise a rune pair ping-pongs forever). The player must step off
  the landing tile and step back on to flip again.
- Sigils and checkpoints likewise fire on WALKED steps onto their
  tiles only. In this design no sigil or checkpoint tile is a rune
  landing tile, so the design assumes no landing activation at all.
- The sigil is SET (latching): a walked step onto (46,1,37) sets the
  bridge group ON. A fall restores the player to the last checkpoint
  and the bridge snapshot taken there.
- Honeycomb: ceiling (44..45, 33..36). Phase cycle 213 frames:
  solid [0,153), gone [153,213). A move costs 16 frames; a move that
  lands on a rune costs 32 (step + flip). A fall costs 60 frames.
  The model is CONSERVATIVE about step atomicity: a move whose
  honeycomb occupancy interval [phase, phase + cost] touches the gone
  window is a fall (the two possible engine models - tile updates at
  step start vs step end - differ here, and the conservative rule is
  safe under both). The documented path avoids the window entirely
  by waiting on a safe tile, so the conservatism costs it nothing.

Proofs (all run by main()):
1. Dijkstra on the phase-free abstract graph gives the minimum move
   count. Every concrete path is an abstract path with the same moves
   (phase only adds constraints), so abstract optimum == concrete
   optimum when the documented path achieves it.
2. No soft-lock: forward reachability on the abstract graph, plus a
   reverse Dijkstra from the goal states (dist-to-goal + parent tree).
   Every forward-reachable abstract state reaches the goal abstractly.
   Realization lemma: a shortest abstract path is simple, so any
   maximal run of consecutive honeycomb positions in it has at most 8
   steps (8 honeycomb tiles); with the exit move that is 9 moves =
   144 frames < 153, so the run always fits in one solid window, and
   the player aligns it by waiting on the safe tile before the run.
   A fall from a honeycomb position lands on a checkpoint (a safe
   tile) whose tree path is realizable the same way. So every
   concretely reachable state can reach the totem. The solver VERIFIES
   the run-length bound on every reachable state's tree path.
3. Concrete check: the documented 38-step path is simulated for every
   honeycomb start phase (0..212), with greedy waits at the safe tile
   (45,10,32) until the whole honeycomb occupancy (4 crossings + the
   flip exit = 96 frames) fits in the solid window.

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
# Floor, on foot: entry walkway, hive strip, Rune B platform.
# The pool (33..37, 22..23) is WATER_SEA (0x15) - Surf-only, not walkable
# on foot; the dry tile (32, 22..23) is cut off by it and unreachable.
FLOOR_TILES = {(x, 12) for x in range(17, 23)}
FLOOR_TILES |= {(x, z) for x in range(38, 49) for z in (22, 23)}
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

# Rune pairs: (surface, x, y, z) <-> (surface, x, y, z).
RUNES = {
    (WALL, 49, 1, 25): (CEIL, 49, 10, 25),
    (CEIL, 49, 10, 25): (WALL, 49, 1, 25),
    (CEIL, 45, 10, 37): (FLOOR, 45, 1, 37),
    (FLOOR, 45, 1, 37): (CEIL, 45, 10, 37),
}
# The one sigil: SET 1 (bridge on). It is the EAST platform tile, reached
# by a walked step after flipping down; the landing tile itself has no
# sigil logic, so no landing activation is assumed anywhere.
SIGIL_TILE = (FLOOR, 46, 1, 37)
# Checkpoints, all on guaranteed WALKED, non-rune tiles: entry; the two
# honeycomb-approach tiles (every first honeycomb entry steps on one);
# the four bridge tiles at z=39 (every crossing steps on one - the gap
# must be crossed from z=38 to z=39). Snapshots: approach snapshots the
# bridge as it was on arrival (OFF first time); bridge snapshots ON.
CHECKPOINTS = [(FLOOR, 20, 1, 12),
               (CEIL, 44, 10, 32), (CEIL, 45, 10, 32),
               (CEIL, 44, 10, 39), (CEIL, 45, 10, 39),
               (CEIL, 46, 10, 39), (CEIL, 47, 10, 39)]
CP_INDEX = {cp: i for i, cp in enumerate(CHECKPOINTS)}
START = (FLOOR, 20, 1, 12)
START_STATE = (START, False, False, 0, (False,) * len(CHECKPOINTS))

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
    with kind in {'walk', 'flip', 'blocked'}. Tile logic (rune, sigil,
    checkpoint) is evaluated on the WALKED-ON tile (the raw dest); the
    flip landing fires nothing."""
    pos, bridge, just_landed, cp, snaps = state
    raw = _raw_dest(pos, delta, bridge)
    if raw is None:
        return state, "blocked"
    flipped = False
    dest = raw
    if raw in RUNES and not just_landed:
        dest = RUNES[raw]
        flipped = True
    just_landed = flipped
    if raw == SIGIL_TILE:
        bridge = True
    if raw in CP_INDEX:
        cp = CP_INDEX[raw]
        snaps = tuple(bridge if i == cp else s for i, s in enumerate(snaps))
    return (dest, bridge, just_landed, cp, snaps), ("flip" if flipped else "walk")


def apply_fall(state):
    """Fall to the last checkpoint with its snapshot."""
    pos, bridge, just_landed, cp, snaps = state
    return (CHECKPOINTS[cp], snaps[cp], False, cp, snaps)


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


def dijkstra(start):
    """Minimum moves to the totem. Returns (opt, goal_state, prev)."""
    dist, prev = {start: 0}, {}
    pq = [(0, start)]
    while pq:
        d, st = heapq.heappop(pq)
        if d != dist[st]:
            continue
        if _is_goal(st[0]):
            return d, st, prev
        for ns, cost, label in successors(st):
            nd = d + cost
            if nd < dist.get(ns, 1 << 30):
                dist[ns] = nd
                prev[ns] = (st, label)
                heapq.heappush(pq, (nd, ns))
    return None, None, prev


def reconstruct(prev, goal):
    path, st = [], goal
    while st in prev:
        pst, label = prev[st]
        path.append(label)
        st = pst
    return list(reversed(path))


def soft_lock_proof(start):
    """Forward-reachable abstract states (flood, successors cached) +
    reverse Dijkstra from goal states over the cached graph (dist to
    goal + parent tree) + honeycomb-run bound on every reachable
    state's tree path (see module docstring, proof 2)."""
    cache, fwd, dq = {}, {start}, deque([start])
    while dq:
        st = dq.popleft()
        outs = successors(st)
        cache[st] = outs
        for ns, _, _ in outs:
            if ns not in fwd:
                fwd.add(ns)
                dq.append(ns)
    rev_adj = {}
    for st, outs in cache.items():
        for ns, cost, _ in outs:
            rev_adj.setdefault(ns, []).append((st, cost))
    # Reverse Dijkstra: dist-to-goal for every visited state.
    INF = 1 << 30
    dist = {st: INF for st in fwd}
    parent = {}
    pq = []
    for st in fwd:
        if _is_goal(st[0]):
            dist[st] = 0
            heapq.heappush(pq, (0, st))
    while pq:
        d, st = heapq.heappop(pq)
        if d != dist[st]:
            continue
        for ps, cost in rev_adj.get(st, []):
            nd = d + cost
            if nd < dist[ps]:
                dist[ps] = nd
                parent[ps] = st
                heapq.heappush(pq, (nd, ps))
    stranded = [st for st in fwd if dist[st] >= INF]
    # Honeycomb-run bound on every reachable state's tree path.
    max_run = 0
    for st in fwd:
        run, cur = 0, st
        while cur in parent:
            if _is_honey(cur[0]):
                run += 1
                max_run = max(max_run, run)
            else:
                run = 0
            cur = parent[cur]
        if _is_honey(cur[0]):
            run += 1
            max_run = max(max_run, run)
    return len(fwd), stranded, max_run


# --- concrete simulation: the documented 38-step path, all phases --------
# Moves as world deltas; the path is the design doc's solution.
PATH = ([(-1, 0, 0)] * 3 + [(1, 0, 0)] * 8 + [(1, 0, 0)]
        + [(0, 0, 1)] * 4 + [(0, 0, 1)] * 2 + [(-1, 0, 0)] * 4
        + [(0, 0, 1)] * 5 + [(0, 0, 1)] * 4 + [(0, 0, 1)]
        + [(1, 0, 0)] + [(-1, 0, 0)] + [(0, 0, 1)] * 4)
WAIT_TILE = (CEIL, 45, 10, 32)  # safe tile before the honeycomb
# Honeycomb occupancy of the crossing: 4 crossing moves (16f each) +
# the flip exit move (32f), starting from the tile before it.
CROSS_FRAMES = 4 * STEP_FRAMES + (STEP_FRAMES + FLIP_EXTRA_FRAMES)  # 96


def _gone_in_interval(phase, frames):
    """True if the gone window [153,213) intersects [phase, phase+frames]."""
    return any((phase + k) % HONEY_CYCLE >= HONEY_GONE_START
               for k in range(frames + 1))


def _safe_to_cross(phase):
    """The whole crossing occupancy fits in the solid window."""
    return phase + CROSS_FRAMES < HONEY_GONE_START


def simulate_path(start_phase):
    """Returns (moves, waits, falls, frames) or raises AssertionError."""
    state = START_STATE
    phase, waits = start_phase, 0
    for i, d in enumerate(PATH):
        # Greedy wait before the honeycomb crossing.
        if state[0] == WAIT_TILE and i == 27:  # next moves are the crossing
            while not _safe_to_cross(phase):
                phase = (phase + WAIT_FRAMES) % HONEY_CYCLE
                waits += 1
                assert waits < 1000, "wait loop did not converge"
        before = state
        state, kind = apply_move(state, d)
        assert kind != "blocked", f"path blocked at step {i} {before} {d}"
        cost = STEP_FRAMES + (FLIP_EXTRA_FRAMES if kind == "flip" else 0)
        if (_is_honey(before[0]) or _is_honey(state[0])) and _gone_in_interval(phase, cost):
            raise AssertionError(f"path would fall at step {i} (phase {phase})")
        phase = (phase + cost) % HONEY_CYCLE
    assert _is_goal(state[0]), f"path did not reach totem: {state[0]}"
    frames = len(PATH) * STEP_FRAMES + waits * WAIT_FRAMES
    return len(PATH), waits, 0, frames


def main():
    opt, goal, prev = dijkstra(START_STATE)
    print(f"optimal moves (Dijkstra, abstract graph): {opt}")
    print("optimal path (first solution found):")
    for s in reconstruct(prev, goal):
        print(f"  {s}")
    fwd, stranded, max_run = soft_lock_proof(START_STATE)
    print(f"forward-reachable abstract states: {fwd}")
    print(f"stranded (reachable but cannot reach totem): {len(stranded)}")
    assert not stranded, f"SOFT-LOCK: {stranded[:3]}"
    print("no-soft-lock proof (abstract + realization lemma): PASS")
    print(f"max honeycomb run on any reachable state's shortest path: "
          f"{max_run} positions; run + exit = {(max_run + 1) * STEP_FRAMES} "
          f"frames <= 153 solid window: "
          f"{'PASS' if (max_run + 1) * STEP_FRAMES <= HONEY_GONE_START else 'FAIL'}")
    assert (max_run + 1) * STEP_FRAMES <= HONEY_GONE_START
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
