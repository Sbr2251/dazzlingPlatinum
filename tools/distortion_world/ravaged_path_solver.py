#!/usr/bin/env python3
"""Standalone BFS model of the DW Ravaged Path puzzle (Phase 1 design).

Semantics mirror engine-a (include/overlay009/dw_puzzle.h) exactly, as far as
a tile model can:

* One SET sigil at wall (11, 2, 14) sets bridge group 0 ON. Sigils fire
  once per step onto the tile. The sigil never switches the group
  off, so the fade-out path is never exercised in this rift.
* Group 0 = bridge tiles (11, 2, 15), (11, 4, 20), (11, 4, 21), ghost-prop
  group 4, onState SOLID, offState BLOCKED, initialOn 0. A bridge that is
  off is impassable (the engine-a skeleton's choice); it never drops the
  player. Fade-in: props show at once, tiles hold after the 3-frame
  lead. The lead is measured from the switch to the next walk check,
  so a direction pressed within 3 frames of the sigil firing may bump
  once; the player retries and it opens (the first time, the teaching
  message supplies ample delay). No state depends on winning that race.
* The Hitmonlee totem object blocks (19, 22), and the goal tile
  (14, 1, 23) is absorbing: stepping on it starts the terminal
  totem script.
* Scars (existing ov9 hook, unchanged): a scar tile may be stepped on
  while its scar is INTACT; stepping onto a spent scar, or onto a second
  tile of the scar you are standing on, is a fall. Leaving a scar spends
  it. Scar 0 = {(2, 16)}; scar 1 = {(2, 20), (2, 21), (3, 20), (3, 21)}
  (wall (y, z), x = 11).
* Falls are asymmetric (engine-a has no "mark a fall" entry point for a
  per-map hook, so only engine-seen falls restore the snapshot):
  - Lip fall (chasm lip, VOID in the engine table): respawn at the
    checkpoint with group := snapshot, snapshot unchanged.
  - Scar fall (per-map hook starts fall script 2 directly): re-entry
    looks fresh to the engine, which resets the puzzle to initial
    (group OFF, snapshot OFF).
  Scars are intact again after any fall (the existing entry-walkway
  reset). A fall is a 1-cost edge to the entry state.
* Wall moves are 4-neighbour on the attr-13 grid (ravaged_path.json).
  Jump-on / hop-off at the two wall ends are 1-cost moves. DOWN off the
  wall at an intermediate z does nothing in-game (no jump point) and is
  no edge here. Floor moves are 4-neighbour on the map_data_669
  walkable tiles (permissions dump; lips included as fall edges).
  The five bidirectional JUMP_*_TWICE stone hops (tile behaviours
  0x5d JUMP_EAST_TWICE / 0x5c JUMP_WEST_TWICE in map_data_669) are
  1-cost edges: (22,12)<->(25,12)<->(28,12) and
  (20,22)<->(23,22)<->(26,22)<->(29,22). Cyrus's object at (22, 11)
  blocks that tile; it is excluded from the floor graph.

"Puzzle steps" are the moves from the jump-on to the hop-off inclusive,
the plan's counting convention (Arc 1 seams is ~15 by it: the flat entry
walk and totem-platform walk are not puzzle steps). Total steps are also
reported.

Checks: (1) optimal path, (2) no soft-lock: every reachable state can
reach the totem (reverse reachability over the full transition graph,
fall edges included), (3) ordering: with the sigil disabled and falls
removed, the totem (and scar 0) are unreachable -- every fall-free
successful path presses the sigil before scar 0.

Usage: python3 tools/distortion_world/ravaged_path_solver.py
"""
import sys
from collections import deque

FLOOR = 0
WALL = 1

# Floor walkable tiles (x, z) from map_data_669 permissions (y = 1).
# (22, 11) is walkable in the permissions but occupied by Cyrus's
# object, so it is excluded: objects block their tile. (19, 22) is
# likewise occupied by the Hitmonlee totem object.
FLOOR_TILES = {
    (22, 10),
    (15, 11), (19, 11), (20, 11), (21, 11),
    (15, 12), (16, 12), (17, 12), (18, 12), (19, 12), (20, 12), (21, 12), (22, 12),
    (25, 12), (28, 12),
    (15, 13), (20, 13), (21, 13),
    (10, 14), (12, 14), (13, 14), (14, 14), (15, 14),
    (10, 15), (12, 15), (13, 15), (14, 15), (15, 15),
    (10, 16), (10, 17), (10, 18), (10, 19), (10, 20),
    (10, 21), (16, 21), (17, 21),
    (10, 22), (16, 22), (17, 22), (18, 22), (20, 22), (23, 22), (26, 22), (29, 22),
    (10, 23), (12, 23), (13, 23), (14, 23), (15, 23), (16, 23), (17, 23),
    (10, 24), (15, 24), (16, 24), (17, 24),
    (15, 25), (15, 26),
}
# Bidirectional JUMP_*_TWICE stone hops (map_data_669 tile behaviours
# 0x5d JUMP_EAST_TWICE / 0x5c JUMP_WEST_TWICE on the tiles between
# the stones). Middle stones have two partners (west and east), so
# this is an adjacency list, not a dict: a dict would silently drop
# one partner (that bug made the stones look soft-locked).
JUMP_PAIRS = (((22, 12), (25, 12)), ((25, 12), (28, 12)),
              ((20, 22), (23, 22)), ((23, 22), (26, 22)), ((26, 22), (29, 22)))
JUMP_ADJ = {}
for _a, _b in JUMP_PAIRS:
    JUMP_ADJ.setdefault(_a, []).append(_b)
    JUMP_ADJ.setdefault(_b, []).append(_a)
# Fall-lip coord events (events_dw_ravaged_path.json): step = fall.
LIPS = {(15, 11), (19, 11), (20, 11), (21, 11),
        (20, 13), (21, 13),
        (12, 15), (13, 15), (14, 15), (15, 15)}
ENTRY = (FLOOR, 20, 1, 12)          # (surface, x, y, z)
GOAL = (FLOOR, 14, 1, 23)           # totem coord event
CHECKPOINT = (20, 1, 12)

# Wall grid (y, z), rows y = 5..2 top first, columns z = 13..22.
# From tools/distortion_world/ravaged_path.json, attr 13 ('*' = scar tile,
# walkable in the stock grid; scars are handled by scar state, not here).
WALL_ROWS = ["##########", "..####....", "..####.**.", "...*...**."]
WALL_TILES = set()
for _i, _row in enumerate(WALL_ROWS):
    _y = 5 - _i
    for _j, _c in enumerate(_row):
        if _c != "#":
            WALL_TILES.add((_y, 13 + _j))

SIGIL = (2, 14)                      # wall (y, z); engine coords (11, 2, 14)
BRIDGES = {(2, 15), (4, 20), (4, 21)}
SCARS = {0: {(2, 16)}, 1: {(2, 20), (2, 21), (3, 20), (3, 21)}}
SCAR_OF = {}
for _sid, _tiles in SCARS.items():
    for _t in _tiles:
        SCAR_OF[_t] = _sid
INTACT, STANDING, SPENT = 0, 1, 2


def scar_state_of(state, sid):
    # State layout: (surface, x, y, z, group, snap, scar0, scar1).
    return state[6 + sid]


def fall_state(state, kind):
    """Fall edge: respawn at the checkpoint, scars intact.
    kind 'lip': group := snapshot (state[5]), snapshot unchanged
    (engine-seen fall).
    kind 'scar': reset to initial (group OFF, snapshot OFF), because the
    per-map scar hook starts the fall script directly and the engine
    never marks a fall pending, so re-entry looks fresh to it."""
    if kind == "lip":
        return (FLOOR, 20, 1, 12, state[5], state[5], INTACT, INTACT)
    return (FLOOR, 20, 1, 12, False, False, INTACT, INTACT)


def transitions(state, sigil_enabled=True, falls=True):
    """Yield (new_state, label, is_fall). State:
    (surface, x, y, z, group_on, snap_on, scar0, scar1).
    The goal (totem coord) is absorbing: stepping on it starts the
    terminal totem script, so no transitions leave it."""
    if state[:4] == GOAL:
        return
    surf, x, y, z, group, snap, s0, s1 = state
    scars = (s0, s1)
    if surf == FLOOR:
        # Jump-ons at the two wall ends.
        if (x, z) == (12, 14):
            yield (WALL, 11, 2, 13, group, snap, s0, s1), "jump-on", False
        if (x, z) == (12, 23):
            yield (WALL, 11, 2, 22, group, snap, s0, s1), "jump-on", False
        # JUMP_*_TWICE stone hops (1-cost edges, each partner).
        for jx, jz in JUMP_ADJ.get((x, z), ()):
            yield (FLOOR, jx, 1, jz, group, snap, s0, s1), "jump", False
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + dx, z + dz
            if (nx, nz) not in FLOOR_TILES:
                continue
            if falls and (nx, nz) in LIPS:
                yield fall_state(state, "lip"), "fall(lip)", True
                continue
            nsnap = group if (nx, nz) == (CHECKPOINT[0], CHECKPOINT[2]) else snap
            yield (FLOOR, nx, 1, nz, group, nsnap, s0, s1), "walk", False
        return
    # Wall: (y, z), x = 11.
    if (y, z) == (2, 13):
        yield (FLOOR, 12, 1, 14, group, snap, s0, s1), "hop-off", False
    if (y, z) == (2, 22):
        yield (FLOOR, 12, 1, 23, group, snap, s0, s1), "hop-off", False
    for dy, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nz = y + dy, z + dz
        if (ny, nz) not in WALL_TILES:
            continue
        if (ny, nz) in BRIDGES and not group:
            continue  # offState BLOCKED: impassable, no fall
        sid = SCAR_OF.get((ny, nz))
        if sid is not None and scars[sid] != INTACT:
            if falls:
                yield fall_state(state, "scar"), "fall(scar)", True
            continue
        # Leaving a scar spends it (unless the destination is the same
        # scar, which the INTACT check above already turned into a fall).
        nscars = list(scars)
        cur_sid = SCAR_OF.get((y, z))
        if cur_sid is not None and scars[cur_sid] == STANDING:
            nscars[cur_sid] = SPENT
        if sid is not None:
            nscars[sid] = STANDING
        ngroup = group
        if sigil_enabled and (ny, nz) == SIGIL:
            ngroup = True  # SET sigil: sets group 0 ON, never toggles off
        yield (WALL, 11, ny, nz, ngroup, snap, nscars[0], nscars[1]), "walk", False


def bfs(start, sigil_enabled=True, falls=True, want_edges=False):
    """Uniform-cost BFS. Returns (dist, parent, edges) where edges maps a
    state to its successor states (for the soft-lock reverse check)."""
    dist = {start: 0}
    parent = {start: None}
    edge_of = {}
    edges = {}
    q = deque([start])
    while q:
        st = q.popleft()
        succs = []
        for ns, label, _is_fall in transitions(st, sigil_enabled, falls):
            succs.append(ns)
            if ns not in dist:
                dist[ns] = dist[st] + 1
                parent[ns] = (st, label)
                q.append(ns)
        if want_edges:
            edges[st] = succs
    return dist, parent, edges


def reconstruct(parent, goal_state):
    path = []
    st = goal_state
    while parent[st] is not None:
        prev, label = parent[st]
        path.append((prev, label, st))
        st = prev
    path.reverse()
    return path


def self_check():
    """Targeted assertions for the fall / sigil semantics (these are
    the transitions a BFS summary cannot show)."""
    # Lip fall restores the SNAPSHOT, not the current group: group OFF,
    # snapshot ON, standing next to a lip -> fall -> group ON.
    st = (FLOOR, 13, 1, 14, False, True, INTACT, INTACT)
    outs = [ns for ns, _lab, is_f in transitions(st) if is_f]
    assert outs == [(FLOOR, 20, 1, 12, True, True, INTACT, INTACT)], outs
    # Scar fall resets to initial even when the snapshot is ON.
    st = (WALL, 11, 2, 17, True, True, SPENT, INTACT)
    outs = [ns for ns, _lab, is_f in transitions(st) if is_f]
    assert outs == [(FLOOR, 20, 1, 12, False, False, INTACT, INTACT)], outs
    # SET sigil: OFF -> ON, and ON stays ON (never toggles off).
    st = (WALL, 11, 2, 13, False, False, INTACT, INTACT)
    outs = [ns for ns, _lab, _f in transitions(st)
            if ns[0] == WALL and (ns[2], ns[3]) == SIGIL]
    assert outs and outs[0][4] is True, outs
    st = (WALL, 11, 2, 13, True, True, INTACT, INTACT)
    outs = [ns for ns, _lab, _f in transitions(st)
            if ns[0] == WALL and (ns[2], ns[3]) == SIGIL]
    assert outs and outs[0][4] is True, outs
    # Goal is absorbing; totem tile is blocked.
    assert list(transitions((FLOOR, 14, 1, 23, True, True, SPENT, SPENT))) == []
    assert (19, 22) not in FLOOR_TILES
    print("self-checks: PASS (lip restore, scar reset, SET stays ON, "
          "goal absorbing, totem tile blocked)")


def main():
    self_check()
    start = (FLOOR, 20, 1, 12, False, False, INTACT, INTACT)
    dist, parent, edges = bfs(start, want_edges=True)
    goal_states = [s for s in dist if s[:4] == GOAL]
    assert goal_states, "totem unreachable"
    goal = min(goal_states, key=lambda s: dist[s])
    path = reconstruct(parent, goal)
    # Puzzle steps: jump-on edge .. hop-off edge, inclusive.
    jump_i = next(i for i, (_a, lab, _b) in enumerate(path) if lab == "jump-on")
    hop_i = next(i for i, (_a, lab, _b) in enumerate(path) if lab == "hop-off")
    puzzle_len = hop_i - jump_i + 1
    falls_on_path = sum(1 for (_a, lab, _b) in path if lab.startswith("fall"))

    # Soft-lock proof: reverse reachability from ALL goal states (the
    # totem tile with any group/snapshot/scar state), over the full graph.
    rev = {g: True for g in goal_states}
    # Reverse adjacency from stored edges (all visited states were expanded).
    incoming = {}
    for src, succs in edges.items():
        for dst in succs:
            incoming.setdefault(dst, []).append(src)
    q = deque(goal_states)
    while q:
        cur = q.popleft()
        for src in incoming.get(cur, []):
            if src not in rev:
                rev[src] = True
                q.append(src)
    soft_locked = [s for s in dist if s not in rev]

    # Ordering check: sigil disabled + no falls => totem and scar 0 unreachable.
    dist_nosigil, _p, _e = bfs(start, sigil_enabled=False, falls=False)
    goal_nosigil = [s for s in dist_nosigil if s[:4] == GOAL]
    scar0_nosigil = [s for s in dist_nosigil
                     if s[0] == WALL and s[2] == 2 and s[3] == 16]

    # Path checks: sigil pressed before scar 0 on the optimal path.
    sigil_i = next(i for i, (_a, lab, b) in enumerate(path)
                   if b[0] == WALL and (b[2], b[3]) == SIGIL)
    scar_i = next(i for i, (_a, lab, b) in enumerate(path)
                  if b[0] == WALL and (b[2], b[3]) in SCAR_OF)

    out_degree = sum(len(v) for v in edges.values())
    print(f"states explored: {len(dist)}")
    print(f"avg branching (out-degree over reachable states): "
          f"{out_degree / len(dist):.2f}")
    print(f"optimal total steps (entry -> totem coord): {dist[goal]}")
    print(f"optimal puzzle steps (jump-on .. hop-off): {puzzle_len} "
          f"(plan range 15-25: {'PASS' if 15 <= puzzle_len <= 25 else 'FAIL'})")
    print(f"falls on optimal path: {falls_on_path}")
    print(f"soft-locked reachable states: {len(soft_locked)} "
          f"({'PASS' if not soft_locked else 'FAIL'})")
    print(f"sigil disabled, no falls: totem reachable: {bool(goal_nosigil)}, "
          f"scar 0 reachable: {bool(scar0_nosigil)} "
          f"({'PASS' if not goal_nosigil and not scar0_nosigil else 'FAIL'})")
    print(f"optimal path presses sigil (step {sigil_i + 1}) before scar 0 "
          f"(step {scar_i + 1}): {'PASS' if sigil_i < scar_i else 'FAIL'}")
    print("optimal path:")
    for i, (a, lab, b) in enumerate(path, 1):
        mark = ""
        if b[0] == WALL and (b[2], b[3]) == SIGIL:
            mark = " <- SIGIL (group SET ON)"
        if b[0] == WALL and (b[2], b[3]) in BRIDGES:
            mark = " <- BRIDGE"
        if b[0] == WALL and (b[2], b[3]) in SCAR_OF:
            mark = " <- SCAR"
        print(f"  {i:2d}. {lab:10s} -> {b[:4]}{' group=' + str(b[4]) if b[0] == WALL else ''}{mark}")
    ok = (15 <= puzzle_len <= 25 and not soft_locked
          and not goal_nosigil and not scar0_nosigil
          and falls_on_path == 0 and sigil_i < scar_i)
    print("OVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
