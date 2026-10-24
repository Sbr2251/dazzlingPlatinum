#!/usr/bin/env python3
"""Route 214 puzzle solver (Phase 1, standalone).

Models the Route 214 ceiling puzzle exactly as docs/distortion_world/route_214.md
specifies it, using the engine-a semantics from include/overlay009/dw_puzzle.h
and tools/distortion_world/README.md (DwPuzzleCurrent / DwPuzzleSigil / groups):

- A step onto a current tile starts a slide in that tile's FACE_* direction.
- A slide continues tile by tile: across plain tiles (ice-style), turning when it
  lands on a current with a different direction, stopping just before a BLOCKED
  tile / edge, and stopping on a sigil or checkpoint tile (whose logic then runs).
  Stepping onto a VOID tile during a slide would be a fall (this puzzle has no
  VOID tiles, so no slide ever falls).
- A step onto a sigil toggles its group. A step onto a checkpoint snapshots
  (snapshot state is tracked only for the fall proof: no VOID tiles, so a fall
  can only come from outside the ceiling puzzle, and the engine restores the
  snapshot then).
- Group A is the W2 forward-gap tile (48,33): BLOCKED while A is on, current
  'v' (south) while A is off. Group B is the (44,39) mid-chamber tile: BLOCKED
  while B is on, plain while B is off. The permanent wall group never toggles.

The solver proves: (1) a solution exists with length in the design range,
(2) every reachable non-goal state can still reach the goal (no soft-lock),
(3) no slide ever loops.

Layout rows are z = 27..47 (top to bottom), columns x = 44..49 (left to right).
Symbols: '.' plain, '#' permanent blocker, 'v'/'^' current (+z/-z),
's' sigil A toggle, 't' sigil B toggle, 'C' checkpoint, 'E' ceiling entry.
Group tiles: 'A' (48,33, used as 'v' when off), 'B' (44,39, plain when off).

Usage: python3 tools/distortion_world/route_214_solver.py
"""
from collections import deque
import sys

# ---------------------------------------------------------------- model ---
# Rows z27..47, cols x44..49.  W1 z29, W2 z33, W3 z37, W4 z41.
# Symbols: '.' plain, '#' permanent blocker, 'v'/'^' current (+z/-z),
# 's' sigil A toggle, 't' sigil B toggle, 'C' checkpoint, 'E' ceiling entry.
# Group tiles: 'A' (48,33, used as 'v' when off), 'B' (44,39, plain when off).
# The authoritative layout is GRID below, checked by _check_grid().
GRID = {}
def _put(x, z, ch):
    GRID[(x, z)] = ch

# Plain chambers (every ceiling tile not named below is a permanent blocker).
for z in range(27, 48):
    for x in range(44, 50):
        _put(x, z, "#")
# C0: z27-28 all plain; C1: z30-32; C2: z34-36; C3: z38-40; C4: z42-44.
for z in [27, 28, 30, 31, 32, 34, 35, 36, 38, 39, 40, 42, 43, 44, 45, 46, 47]:
    for x in range(44, 50):
        _put(x, z, ".")
# Walls: only the named gaps are passable; the rest stay '#'.
_put(46, 29, "v")  # W1 forward gap
_put(48, 33, "A")  # W2 forward gap: group A (current 'v' when off)
_put(44, 33, "^")  # W2 return gap
_put(44, 37, "v")  # W3 forward gap
_put(49, 37, "^")  # W3 return gap
_put(47, 41, "v")  # W4 forward gap
_put(44, 41, "^")  # W4 return gap
_put(45, 31, "s")  # sigil A (toggle group A)
_put(45, 35, "t")  # sigil B (toggle group B)
_put(44, 39, "B")  # group B blocker (plain when off)
# Checkpoints: ceiling entry + one landing per crossing.
_put(49, 27, "C")  # entry checkpoint (pad)
_put(46, 32, "C")  # W1 landing
_put(48, 36, "C")  # W2 landing
_put(44, 40, "C")  # W3 landing
_put(47, 44, "C")  # W4 landing

DIRS = {"U": (0, 1), "D": (0, -1), "L": (-1, 0), "R": (1, 0)}  # FACE_* on ceiling
CUR = {"v": "U", "^": "D"}  # current tile -> FACE_* drift

def _check_grid():
    assert GRID[(46, 29)] == "v" and GRID[(48, 33)] == "A" and GRID[(44, 33)] == "^"
    assert GRID[(44, 37)] == "v" and GRID[(49, 37)] == "^"
    assert GRID[(47, 41)] == "v" and GRID[(44, 41)] == "^"
    assert GRID[(45, 31)] == "s" and GRID[(45, 35)] == "t" and GRID[(44, 39)] == "B"
    assert GRID[(49, 27)] == "C" and GRID[(46, 32)] == "C" and GRID[(48, 36)] == "C"
    assert GRID[(44, 40)] == "C" and GRID[(47, 44)] == "C"

_check_grid()

START = (49, 27)
INIT_GROUPS = (1, 1)  # A on (gap closed), B on (stop-block present)

def blocked(state, x, z):
    """True if (x, z) is impassable in state (x, z, A, B)."""
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
    """FACE_* drift of the tile, or None. Group A tile drifts 'U' when off."""
    ch = GRID[(x, z)]
    if ch in CUR:
        return CUR[ch]
    if ch == "A" and state[2] == 0:
        return "U"
    return None

def slide(state, x, z, path):
    """Resolve a slide that starts by stepping onto current tile (x, z).

    Returns (final_state, path) or raises SlideLoop. path holds one letter
    per tile entered: 'U/D/L/R' for slide tiles, plus the entry step.
    """
    _, _, ga, gb = state
    d = current_dir(state, x, z)
    seen = set()
    pos = (x, z)
    while True:
        key = (pos, d)
        if key in seen:
            raise SlideLoop(f"slide loops at {pos} dir {d}")
        seen.add(key)
        dx, dz = DIRS[d]
        nx, nz = pos[0] + dx, pos[1] + dz
        if blocked(state, nx, nz):
            break  # stop just before the block / edge
        pos = (nx, nz)
        path.append(d.lower())
        ch = GRID[pos]
        if ch in "stC":
            break  # sigil / checkpoint ends the slide; its logic runs below
        nd = current_dir(state, *pos)
        if nd is not None:
            d = nd  # turn
        # else plain tile: keep sliding in the same direction (ice-style)
    return (pos[0], pos[1], ga, gb), path

class SlideLoop(Exception):
    pass

def step(state, direction):
    """One player step in FACE direction. Returns new state + path letters,
    or None if the step is blocked. Raises SlideLoop if a slide never ends."""
    x, z, ga, gb = state
    dx, dz = DIRS[direction]
    nx, nz = x + dx, z + dz
    if blocked(state, nx, nz):
        return None
    path = [direction]
    nstate = (nx, nz, ga, gb)
    if current_dir(state, nx, nz) is not None:
        nstate, path = slide(state, nx, nz, path)
    # Landing-tile logic (plain step or slide end).
    ch = GRID[(nstate[0], nstate[1])]
    ga, gb = nstate[2], nstate[3]
    if ch == "s":
        ga = 1 - ga
    elif ch == "t":
        gb = 1 - gb
    return (nstate[0], nstate[1], ga, gb), path

def is_goal(state):
    return state[1] >= 45

def solve():
    """BFS over (x, z, A, B). Returns (solution_path, stats)."""
    start = (START[0], START[1], INIT_GROUPS[0], INIT_GROUPS[1])
    parent = {start: None}
    action = {}
    q = deque([start])
    goal = None
    while q:
        st = q.popleft()
        if is_goal(st):
            if goal is None:
                goal = st
            continue  # goal states are terminal: do not expand past the totem
        for d in "UDLR":
            try:
                res = step(st, d)
            except SlideLoop as e:
                raise AssertionError(f"slide loop from reachable state {st}: {e}")
            if res is None:
                continue
            nst, _ = res
            if nst not in parent:
                parent[nst] = st
                action[nst] = d
                q.append(nst)
    assert goal is not None, "no solution: puzzle unsolvable"
    # Reconstruct the path (tile-step letters).
    path = []
    st = goal
    while parent[st] is not None:
        path.append(action[st])
        st = parent[st]
    path.reverse()
    # Expand: replay the action sequence to get the full tile-step string
    # (BFS edges are player steps; slide tiles are inside step()).
    full, st = [], start
    for d in path:
        nst, letters = step(st, d)
        full.extend(letters)
        st = nst
    stats = {
        "states_reached": len(parent),
        "solution_player_steps": len(path),
        "solution_tile_steps": len(full),
        "solution": "".join(full),
        "goal_state": goal,
    }
    return "".join(full), stats, parent

def soft_lock_proof(parent):
    """Every reachable state must reach the goal: reverse-BFS from goal
    states over the same transitions and compare with the forward set.
    The forward set must be exhaustive (solve() expands every non-goal
    reachable state), otherwise states beyond the first goal found would
    go unchecked."""
    # Build reverse edges from the forward BFS tree is not enough (a state
    # can reach the goal via a state outside its own forward path), so
    # re-walk all transitions from every reached state.
    forward = set(parent)
    transitions = {}
    for st in forward:
        if is_goal(st):
            continue  # terminal: no transitions past the totem
        outs = set()
        for d in "UDLR":
            try:
                res = step(st, d)
            except SlideLoop:
                return False, f"slide loop from {st}"
            if res is not None:
                outs.add(res[0])
        transitions[st] = outs
    can_reach = {st for st in forward if is_goal(st)}
    dq = deque(can_reach)
    rev = {}
    for st, outs in transitions.items():
        for o in outs:
            rev.setdefault(o, set()).add(st)
    while dq:
        st = dq.popleft()
        for pre in rev.get(st, ()):
            if pre not in can_reach:
                can_reach.add(pre)
                dq.append(pre)
    stuck = forward - can_reach
    return (not stuck), (f"{len(stuck)} reachable states cannot reach the goal: "
                        f"{sorted(stuck)[:5]}" if stuck else "all reachable states reach the goal")

def main():
    full, stats, parent = solve()
    ok, msg = soft_lock_proof(parent)
    print(f"optimal tile steps : {stats['solution_tile_steps']} "
          f"(player steps {stats['solution_player_steps']})")
    print(f"solution           : {stats['solution']}")
    print(f"goal state         : {stats['goal_state']} (A,B = groups off)")
    print(f"states reached     : {stats['states_reached']}")
    print(f"soft-lock free     : {ok} - {msg}")
    print(f"slide loops       : none (a loop would have raised during BFS)")
    print(f"in design range 35-50: {35 <= stats['solution_tile_steps'] <= 50}")
    if not ok or not (35 <= stats['solution_tile_steps'] <= 50):
        sys.exit(1)

if __name__ == "__main__":
    main()
