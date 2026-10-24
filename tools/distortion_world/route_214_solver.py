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

Fade timing (honeycomb rule). The engine does NOT flip a group's tile
state at once: turning a group off leaves its tiles solid for
fadeOutFrames (default 33), and turning one on shows its props at once
but holds its tiles only after fadeInLeadFrames (default 3). The solver
models this strictly: a sigil toggle flips the group's *logical* state
and marks a fade pending, and while a fade is pending the only
transitions are WAIT (settle the fade) and FALL -- movement is
forbidden. That makes the model sound in both directions: it cannot
slide through a gap that is still closing (the engine blocks it after
3 frames), nor through a gap that is still opening (the engine holds
it blocked for 33 frames). WAIT is always a legal action, so any path
the model finds works in the engine. Checkpoint snapshots store
logical group states, and a fall settles pending fades (the respawn
warp takes longer than any fade).

Other rules:
- A step onto a current tile starts a slide in that tile's FACE_* direction.
- During a slide: landing on a current with a different direction turns
  the slide; landing on a sigil or checkpoint ends it and that tile's
  logic runs; a BLOCKED tile / surface edge stops it on the tile before.
  In mode A, landing on any other plain tile also ends it. In mode B,
  plain tiles are crossed (ice-style).
- A step onto a sigil toggles its group (logical state + fade pending).
  A step onto a checkpoint snapshots the logical groups at that
  checkpoint.
- A fall is an extra transition from any state: the player and the puzzle
  return to the last checkpoint with its snapshot groups (fades settled).
  Falls are never useful for reaching the goal; they exist so the
  soft-lock proof covers the engine's fall/checkpoint restore.
- Group A is the W2 forward-gap tile (48,33): BLOCKED while A is
  effectively on, current 'v' (south) while effectively off. Group B
  is the C3 wall gap (44,39): same pattern. The permanent wall group
  never toggles.

Scope. START is the ceiling-entry checkpoint. Falls *before* the
ceiling are not modelled: no sigil is reachable before the ceiling, so
the puzzle state before the ceiling is always the initial one, and a
fall there returns the player to the map entry with initial groups —
equivalent to a fresh entry. The solver's fall proof covers falls from
any ceiling state; Phase 2 must still headless-test a floor/wall fall.

Layout rows are z = 27..47 (top to bottom), columns x = 44..49 (left to
right). Symbols: '.' plain, '#' permanent blocker, 'v'/'^' current
(+z/-z), 's' sigil A toggle, 't' sigil B toggle, 'C' checkpoint.
Group tiles: 'A' (48,33), 'B' (44,39), both currents when effectively off.

State = (x, z, effA, effB, logA, logB, pendA, pendB, cp, snapA, snapB)
  eff = effective tile state (what the walk/slide check sees)
  log = logical group state (what a snapshot stores)
  pend = a fade is pending for that group
  cp = index of the last checkpoint reached; snap = its snapshot groups

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
_put(48, 33, "A")  # W2 forward gap: group A (current 'v' when effectively off)
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
_put(44, 39, "B")  # group B gap (current 'v' when effectively off)
# Checkpoints: ceiling entry (49,28: the jump lands at (49,27) and
# landings fire nothing) + one landing per crossing.
_put(49, 28, "C")
_put(46, 32, "C")
_put(48, 36, "C")
_put(44, 40, "C")
_put(47, 44, "C")

CHECKPOINTS = [(49, 28), (46, 32), (48, 36), (44, 40), (47, 44)]
CP_INDEX = {pos: i for i, pos in enumerate(CHECKPOINTS)}
START = (49, 27, 1, 1, 1, 1, False, False, 0, 1, 1)  # jump landing (49,27); cp 0 = map entry until (49,28) is walked onto

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
    assert GRID[(49, 27)] == "." and GRID[(49, 28)] == "C" and GRID[(46, 32)] == "C" and GRID[(48, 36)] == "C"
    assert GRID[(44, 40)] == "C" and GRID[(47, 44)] == "C"

_check_grid()

def blocked(state, x, z):
    """Effective tile state: fades pending do not change it."""
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
    x0, z0, ea, eb, la, lb, pa, pb, cp, sa, sb = state
    ch = GRID[(x, z)]
    if ch == "s":
        la, pa = 1 - la, True
    elif ch == "t":
        lb, pb = 1 - lb, True
    if (x, z) in CP_INDEX:
        cp = CP_INDEX[(x, z)]
        sa, sb = la, lb
    return (x, z, ea, eb, la, lb, pa, pb, cp, sa, sb)

class SlideLoop(Exception):
    pass

def slide(state, x, z, mode):
    """Resolve a slide starting on current tile (x, z). Returns
    (new_state, tile_letters) with one letter per tile entered."""
    d = current_dir(state, x, z)
    seen = set()
    pos = (x, z)
    letters = []
    while True:
        key = (pos, d)
        if key in seen:
            raise SlideLoop(f"slide loops at {pos} dir {d}")
        seen.add(key)
        dx, dz = DIRS[d]
        nx, nz = pos[0] + dx, pos[1] + dz
        if blocked(state, nx, nz):
            break
        pos = (nx, nz)
        letters.append(d.lower())
        if pos in VOIDS:
            # Entering a VOID forces the fall immediately (engine):
            # the slide stops here and the player restores to the
            # last checkpoint with its snapshot groups.
            return fall(land(state, pos[0], pos[1])), letters, True
        ch = GRID[pos]
        if ch in "stC":
            break
        if mode == "A" and current_dir(state, *pos) is None:
            break  # off-current: the first non-current tile ends the slide
        nd = current_dir(state, *pos)
        if nd is not None:
            d = nd
    return land(state, pos[0], pos[1]), letters, False

def step(state, direction, mode):
    """One player step. Returns (new_state, tile_letters, fell) or None.
    Entering a VOID forces the fall at once (see VOIDS); the returned
    state is the fall-restored state and fell is True."""
    x, z = state[0], state[1]
    dx, dz = DIRS[direction]
    nx, nz = x + dx, z + dz
    if blocked(state, nx, nz):
        return None
    if current_dir(state, nx, nz) is not None:
        nstate, letters, fell = slide(state, nx, nz, mode)
        return nstate, [direction] + letters, fell
    if (nx, nz) in VOIDS:
        return fall(land(state, nx, nz)), [direction], True
    return land(state, nx, nz), [direction], False

def wait(state):
    """Wait until pending fades settle: effective state becomes logical.
    Offered only while a fade is pending."""
    if not (state[6] or state[7]):
        return None
    x, z, _, _, la, lb, _, _, cp, sa, sb = state
    return (x, z, la, lb, la, lb, False, False, cp, sa, sb)

# Production VOID lips (the only tiles where a fall can start in the
# shipped table). Entering one forces the fall IMMEDIATELY (the engine
# restores the checkpoint the moment the tile is entered); the player
# never stands on a VOID and walks away. step()/slide() apply fall()
# at once on entering a VOID, and transitions() offers no separate FALL.
VOIDS = {(49, 34), (44, 42)}

def fall(state):
    """The engine's fall transition: back to the last checkpoint with its
    snapshot groups, fades settled. Cost 0 tile steps."""
    _, _, _, _, _, _, _, _, cp, sa, sb = state
    cx, cz = CHECKPOINTS[cp]
    return (cx, cz, sa, sb, sa, sb, False, False, cp, sa, sb)

def is_goal(state):
    return state[1] >= 45

def transitions(state, mode):
    """All transitions from a state: (new_state, tile_cost, label, fell).

    While a fade is pending, movement is forbidden: only WAIT (settle
    the fade) is offered. Allowing movement while pending
    would be unsound in the toggle-on direction — the real engine
    blocks the gap after the 3-frame fade-in lead, so a slide through
    a barely-closing gap is impossible, while the model would have
    let it through indefinitely.
    """
    if state[6] or state[7]:
        w = wait(state)
        assert w is not None
        return [(w, 0, "W", False)]
    out = []
    for d in "UDLR":
        try:
            res = step(state, d, mode)
        except SlideLoop as e:
            raise AssertionError(f"slide loop from reachable state {state}: {e}")
        if res is not None:
            out.append((res[0], len(res[1]), d, res[2]))
    w = wait(state)
    if w is not None:
        out.append((w, 0, "W", False))
    return out

def solve(mode):
    """Dijkstra over tile steps (steps cost tiles entered; WAIT costs 0;
    a fall is forced on entering a VOID and costs 0 additional tiles).
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
                goal = st
            continue
        for nst, w, label, fell in transitions(st, mode):
            nc = cost + w
            if nst not in dist or nc < dist[nst]:
                dist[nst] = nc
                parent[nst] = (st, label, fell)
                heapq.heappush(heap, (nc, nst))
    assert goal is not None, f"mode {mode}: no solution"
    # Reconstruct the optimal path from the recorded parents (label +
    # fell), not by re-matching transitions -- two directions can
    # converge to the same state, and re-matching could mislabel a
    # forced fall as an ordinary walk (or vice versa).
    seq = []
    st = goal
    while parent[st] is not None:
        prev, label, fell = parent[st]
        seq.append((prev, label, fell))
        st = prev
    seq.reverse()
    full = []
    for prev, label, fell in seq:
        if label in "UDLR":
            full.extend(step(prev, label, mode)[1])
            if fell:
                full.append("F")
        else:
            full.append(label)
    stats = {
        "states_reached": len(dist),
        "solution_tile_steps": dist[goal],
        "solution": "".join(c for c in full if c not in "WF"),
        "goal_state": goal,
        "waits_in_solution": sum(1 for c in full if c == "W"),
        "falls_in_solution": sum(1 for c in full if c == "F"),
    }
    # Soft-lock proof: reverse reachability from all goal states in `dist`
    # over the same transition set (steps + WAIT; falls are forced inside
    # steps on entering a VOID).
    succ = {}
    for st in dist:
        if is_goal(st):
            continue
        succ[st] = {n for n, _, _, _ in transitions(st, mode)}
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
    return dist[goal], "".join(c for c in full if c not in "WF"), stats

def main():
    ok = True
    for mode in ("A", "B"):
        _, sol, stats = solve(mode)
        print(f"mode {mode} (slide {'stops at first plain tile' if mode == 'A' else 'crosses plain tiles'}):")
        print(f"  optimal tile steps : {stats['solution_tile_steps']}")
        print(f"  solution           : {sol}")
        print(f"  goal state         : {stats['goal_state']}")
        print(f"  waits in solution  : {stats['waits_in_solution']}")
        print(f"  falls in solution  : {stats['falls_in_solution']}")
        print(f"  states reached     : {stats['states_reached']}")
        print(f"  soft-lock free     : {stats['soft_lock_free']} {stats['stuck_states']}")
        print(f"  in range 35-50     : {35 <= stats['solution_tile_steps'] <= 50}")
        ok &= stats["soft_lock_free"] and 35 <= stats["solution_tile_steps"] <= 50
    if not ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
