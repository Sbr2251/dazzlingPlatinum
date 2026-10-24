#!/usr/bin/env python3
"""Route 214 puzzle solver (Phase 1, standalone).

Models the Route 214 ceiling puzzle exactly as docs/distortion_world/route_214.md
specifies it, using the engine-a semantics from include/overlay009/dw_puzzle.h
and tools/distortion_world/README.md (DwPuzzleCurrent / DwPuzzleSigil / groups).

Slide semantics. The engine-a guide says a slide runs "until blocked ...
or off-current", which is ambiguous: it may mean a slide stops on the
first non-current tile (mode A) or keeps sliding across plain tiles until
a block (mode B, ice-style). The design is valid under BOTH, because every
forward slide path is tiled with currents and ends on a checkpoint, and
every return slide lands in the same chamber under both readings (only
the exact landing tile inside that chamber differs). The solver runs
both modes and reports both optima.

Other rules:
- A step onto a current tile starts a slide in that tile's FACE_* direction.
- During a slide: landing on a current with a different direction turns
  the slide; landing on a sigil or checkpoint ends it and that tile's
  logic runs; a BLOCKED tile / surface edge stops it on the tile before.
  In mode A, landing on any other plain tile also ends it. In mode B,
  plain tiles are crossed (ice-style).
- A step onto a sigil toggles its group. A step onto a checkpoint
  snapshots the groups (sigil states) at that checkpoint.
- A fall is an extra transition from any state: the player and the puzzle
  return to the last checkpoint with its snapshot groups. Falls are
  never useful for reaching the goal; they exist so the soft-lock proof
  covers the engine's fall/checkpoint restore.
- Group A is the W2 forward-gap tile (48,33): BLOCKED while A is on,
  current 'v' (south) while A is off. Group B is the C3 wall gap
  (44,39): BLOCKED while B is on, current 'v' while B is off. The
  permanent wall group never toggles.

Layout rows are z = 27..47 (top to bottom), columns x = 44..49 (left to
right). Symbols: '.' plain, '#' permanent blocker, 'v'/'^' current
(+z/-z), 's' sigil A toggle, 't' sigil B toggle, 'C' checkpoint.
Group tiles: 'A' (48,33), 'B' (44,39), both currents when off.

Usage: python3 tools/distortion_world/route_214_solver.py
Exits non-zero if either mode is unsolvable, soft-locked, has a slide
loop, or has a tile-step optimum outside 35..50.
"""
from collections import deque
import heapq
import sys

# ---------------------------------------------------------------- model ---
GRID = {}

def _put(x, z, ch):
    GRID[(x, z)] = ch

# Default: every ceiling tile is a permanent blocker.
for z in range(27, 48):
    for x in range(44, 50):
        _put(x, z, "#")
# Chambers (plain): C0 z27-28, C1 z30-32, C2 z34-36, C3 z38 + z40, C4 z42-47.
for z in [27, 28, 30, 31, 32, 34, 35, 36, 38, 40, 42, 43, 44, 45, 46, 47]:
    for x in range(44, 50):
        _put(x, z, ".")
# C3 wall z39: only the group B gap at x44 is passable.
for x in range(45, 50):
    _put(x, 39, "#")
# Forward / return gaps (wall tiles).
_put(46, 29, "v")  # W1 forward gap
_put(48, 33, "A")  # W2 forward gap: group A (current 'v' when off)
_put(44, 33, "^")  # W2 return gap
_put(44, 37, "v")  # W3 forward gap
_put(49, 37, "^")  # W3 return gap
_put(47, 41, "v")  # W4 forward gap
_put(44, 41, "^")  # W4 return gap
# Slide-path currents: every forward slide travels on currents only.
_put(46, 30, "v"); _put(46, 31, "v")  # W1 slide
_put(48, 34, "v"); _put(48, 35, "v")  # W2 slide
_put(44, 38, "v")                     # W3 slide (then B gap, then checkpoint)
_put(47, 42, "v"); _put(47, 43, "v")  # W4 slide
# Sigils and the group B gap.
_put(45, 31, "s")  # sigil A (toggle group A)
_put(45, 35, "t")  # sigil B (toggle group B)
_put(44, 39, "B")  # group B gap (current 'v' when off)
# Checkpoints: ceiling entry + one landing per crossing.
_put(49, 27, "C")
_put(46, 32, "C")
_put(48, 36, "C")
_put(44, 40, "C")
_put(47, 44, "C")

CHECKPOINTS = [(49, 27), (46, 32), (48, 36), (44, 40), (47, 44)]
CP_INDEX = {pos: i for i, pos in enumerate(CHECKPOINTS)}
# (map-entry checkpoint 0 would be (20,12) on the floor; the ceiling solver
# starts at the ceiling entry, so checkpoint indices here are ceiling-only
# and index 0 is the ceiling entry. The full table has one more entry.)
START = (49, 27, 1, 1, 0, 1, 1)  # x, z, A, B, cp, snapA, snapB

DIRS = {"U": (0, 1), "D": (0, -1), "L": (-1, 0), "R": (1, 0)}  # FACE_* on ceiling
CUR = {"v": "U", "^": "D"}

def _check_grid():
    assert GRID[(46, 29)] == "v" and GRID[(48, 33)] == "A" and GRID[(44, 33)] == "^"
    assert GRID[(44, 37)] == "v" and GRID[(49, 37)] == "^"
    assert GRID[(47, 41)] == "v" and GRID[(44, 41)] == "^"
    assert GRID[(45, 31)] == "s" and GRID[(45, 35)] == "t" and GRID[(44, 39)] == "B"
    assert GRID[(46, 30)] == "v" and GRID[(46, 31)] == "v"
    assert GRID[(48, 34)] == "v" and GRID[(48, 35)] == "v"
    assert GRID[(44, 38)] == "v" and GRID[(47, 42)] == "v" and GRID[(47, 43)] == "v"
    for x in range(45, 50):
        assert GRID[(x, 39)] == "#", f"C3 wall must be closed except the B gap, got {(x, 39)}"
    assert GRID[(49, 27)] == "C" and GRID[(46, 32)] == "C" and GRID[(48, 36)] == "C"
    assert GRID[(44, 40)] == "C" and GRID[(47, 44)] == "C"

_check_grid()

def blocked(state, x, z):
    if not (44 <= x <= 49 and 27 <= z <= 47):
        return True
    ch = GRID[(x, z)]
    if ch == "#":
        return True
    if ch == "A":
        return state[2] == 1
    if ch == "B":
        return state[3] == 1
    return False

def current_dir(state, x, z):
    ch = GRID[(x, z)]
    if ch in CUR:
        return CUR[ch]
    if ch == "A" and state[2] == 0:
        return "U"
    if ch == "B" and state[3] == 0:
        return "U"
    return None

def land(state, x, z):
    """Apply landing-tile logic (sigil toggle / checkpoint snapshot)."""
    _, _, ga, gb, cp, sa, sb = state[0], state[1], state[2], state[3], state[4], state[5], state[6]
    ch = GRID[(x, z)]
    if ch == "s":
        ga = 1 - ga
    elif ch == "t":
        gb = 1 - gb
    if (x, z) in CP_INDEX:
        cp = CP_INDEX[(x, z)]
        sa, sb = ga, gb
    return (x, z, ga, gb, cp, sa, sb)

class SlideLoop(Exception):
    pass

def slide(state, x, z, mode):
    """Resolve a slide starting on current tile (x, z). Returns
    (new_state, tile_letters) with one letter per tile entered."""
    d = current_dir(state, x, z)
    seen = set()
    pos = (x, z)
    letters = []
    cur = state
    while True:
        key = (pos, d)
        if key in seen:
            raise SlideLoop(f"slide loops at {pos} dir {d}")
        seen.add(key)
        dx, dz = DIRS[d]
        nx, nz = pos[0] + dx, pos[1] + dz
        if blocked(cur, nx, nz):
            break
        pos = (nx, nz)
        letters.append(d.lower())
        ch = GRID[pos]
        if ch in "stC":
            break
        if mode == "A":
            # Off-current: the first non-current tile ends the slide.
            if current_dir(cur, *pos) is None:
                break
        nd = current_dir(cur, *pos)
        if nd is not None:
            d = nd
    return land(cur, pos[0], pos[1]), letters

def step(state, direction, mode):
    """One player step. Returns (new_state, tile_letters) or None."""
    x, z = state[0], state[1]
    dx, dz = DIRS[direction]
    nx, nz = x + dx, z + dz
    if blocked(state, nx, nz):
        return None
    if current_dir(state, nx, nz) is not None:
        nstate, letters = slide(state, nx, nz, mode)
        return nstate, [direction] + letters
    return land(state, nx, nz), [direction]

def fall(state):
    """The engine's fall transition: back to the last checkpoint with
    its snapshot groups. Cost 0 tile steps (a fall is not a step)."""
    _, _, _, _, cp, sa, sb = state
    cx, cz = CHECKPOINTS[cp]
    return (cx, cz, sa, sb, cp, sa, sb)

def is_goal(state):
    return state[1] >= 45

def solve(mode):
    """Dijkstra over tile steps (edge cost = tiles entered; falls cost 0).
    Goal states are terminal. Returns (optimum, solution, stats)."""
    dist = {START: 0}
    parent = {START: None}
    heap = [(0, START)]
    goal = None
    while heap:
        cost, st = heapq.heappop(heap)
        if cost != dist[st]:
            continue
        if is_goal(st):
            if goal is None:
                goal = st  # Dijkstra: first goal popped is optimal
            continue
        transitions = []
        for d in "UDLR":
            try:
                res = step(st, d, mode)
            except SlideLoop as e:
                raise AssertionError(f"slide loop from reachable state {st}: {e}")
            if res is not None:
                transitions.append((res[0], len(res[1]), d))
        transitions.append((fall(st), 0, "F"))
        for nst, w, _ in transitions:
            nc = cost + w
            if nst not in dist or nc < dist[nst]:
                dist[nst] = nc
                parent[nst] = st
                heapq.heappush(heap, (nc, nst))
    assert goal is not None, f"mode {mode}: no solution"
    # Reconstruct player steps and tile letters for the optimal path.
    actions = []
    st = goal
    while parent[st] is not None:
        actions.append(st)
        st = parent[st]
    actions.reverse()
    full, letters = [], START
    for nst in actions:
        # Re-derive the transition (step or fall) between consecutive states.
        if nst == fall(letters):
            full.append("F")
        else:
            for d in "UDLR":
                res = step(letters, d, mode)
                if res is not None and res[0] == nst:
                    full.extend(res[1])
                    break
            else:
                raise AssertionError(f"cannot replay transition {letters} -> {nst}")
        letters = nst
    stats = {
        "states_reached": len(dist),
        "solution_tile_steps": dist[goal],
        "solution": "".join(c for c in full if c != "F"),
        "goal_state": goal,
        "falls_in_solution": sum(1 for c in full if c == "F"),
    }
    # Soft-lock proof: reverse reachability from all goal states in `dist`
    # over the same transition set (steps + falls). Every non-goal state in
    # `dist` must reach a goal.
    succ = {}
    for st in dist:
        if is_goal(st):
            continue
        outs = set()
        for d in "UDLR":
            res = step(st, d, mode)
            if res is not None:
                outs.add(res[0])
        outs.add(fall(st))
        succ[st] = outs
    can = {st for st in dist if is_goal(st)}
    dq = deque(can)
    rev = {}
    for st, outs in succ.items():
        for o in outs:
            rev.setdefault(o, set()).add(st)
    while dq:
        st = dq.popleft()
        for pre in rev.get(st, ()):
            if pre not in can:
                can.add(pre)
                dq.append(pre)
    stuck = set(dist) - can - {st for st in dist if is_goal(st)}
    stats["soft_lock_free"] = not stuck
    stats["stuck_states"] = sorted(stuck)[:5]
    return dist[goal], "".join(c for c in full if c != "F"), stats

def main():
    ok = True
    for mode in ("A", "B"):
        _, sol, stats = solve(mode)
        print(f"mode {mode} (slide {'stops at first plain tile' if mode == 'A' else 'crosses plain tiles'}):")
        print(f"  optimal tile steps : {stats['solution_tile_steps']}")
        print(f"  solution           : {sol}")
        print(f"  goal state         : {stats['goal_state']}")
        print(f"  falls in solution  : {stats['falls_in_solution']}")
        print(f"  states reached     : {stats['states_reached']}")
        print(f"  soft-lock free     : {stats['soft_lock_free']} {stats['stuck_states']}")
        print(f"  in range 35-50     : {35 <= stats['solution_tile_steps'] <= 50}")
        ok &= stats["soft_lock_free"] and 35 <= stats["solution_tile_steps"] <= 50
    if not ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
