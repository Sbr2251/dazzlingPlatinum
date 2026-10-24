#!/usr/bin/env python3
"""Standalone BFS solver for the DW Lost Tower puzzle (design phase).

Semantics mirror include/overlay009/dw_puzzle.h (engine-a) and
docs/distortion_world/actors_design.md (engine-b): groups, SET sigils
(idempotent), runes, checkpoints with *actual* snapshots, VOID falls,
and the engine-b shadow (phase abstracted - geometry-only for timing;
catch -> checkpoint respawn). Visit 1 has no engine table: the
solver's Visit 1 models the Phase 0 walk (falls to the entry, act
flags persist). Visit 2 has one engine-a table (progress 94-95) and
one engine-b actor table (4 pads + shadow).

Conformance to engine-b (docs/distortion_world/actors_design.md, authoritative):
- Visit 1 has NO engine table: the Phase 0 scripted ghost acts run unchanged.
  The solver's Visit 1 models the WALK (act tiles as SET stand-ins with the
  same passability effect; the real acts are scripts, not engine sigils).
- Visit 2 has ONE engine-a table (progress 94-95) + ONE engine-b actor
  table (4 pads: H, V, L, S - exactly DW_ACTORS_MAX_PADS). The V1 wall
  (scar/seam) is already open in Visit 2 via the persistent Phase 0 acts,
  so it carries no engine groups.
- Pads are Yes/No prompts: stepping on a pad starts a prompt script
  (shadow frozen, catch suppressed); Yes resolves via PressSigil. The
  solver assumes Yes. Pad tiles are never checkpoint/rune/current tiles.
- Shadow is frame-driven, beat 45-60 frames/tile (engine-b). The solver
  is GEOMETRY-ONLY for timing: the shadow phase is abstracted as a
  nondeterministic choice. Stepping onto a lane tile yields two branches:
  safe (the player timed it - waiting for a favourable phase is always
  available on safe tiles) and caught (respawn at the checkpoint with
  its snapshot). The solver therefore proves (i) reachability assuming
  favourable timing and (ii) that EVERY catch lands in a state from
  which the goal is still reachable. It does NOT prove a specific frame
  schedule: the timing proof is deferred to the harness (headless replay
  against the real beat). Lane: (17,22)-(22,22), 6 tiles (<= 16),
  avoiding script tiles (the S pad at (32,22) is off-lane).
- Catch/fall restores engine-b's checkpoint snapshot. The solver does
  not model the restored phase (it is abstracted away); the catch
  branch lands on the checkpoint with the checkpoint's snapshot, which
  is the real post-catch state up to the phase, and the phase can
  always be waited out on safe tiles.
- No checkpoint is on the shadow lane (CPs: entry, vein, (16,23),
  carry landing (37,22)), so catch-before-checkpoint ordering is moot:
  catches on lane tiles request respawn to the last committed CP.
- G_STONES off = VOID, not BLOCKED: hopping onto a sunk stone falls
  (the tile is drawn as open mist), so no jump-point suppression glue
  is needed. Stones only ever turn on (SET).
- All persistent object blockers, including candles on VOID lips.

History (superseded notes removed; the current model is the header above
plus the design doc):
- Round 1: pads were TOGGLE on a shared table; superseded by engine-b
  (pads are Yes/No prompts on a Visit 2-only table; SET sigils).
- Round 2: checkpoint snapshots were fixed masks, and catch/fall was
  checked before checkpoint commitment; superseded - snapshots are
  real state, and no checkpoint is on the shadow lane, so no ordering
  is needed.
- Round 3: stone hops were gated on the hop edge; superseded - G_STONES
  off = VOID, hopping onto a sunk stone falls, no hop suppression.
- Solver polarity: a group bit means "open" (SOLID). In the engine
  mapping (design doc) crystal/mist/aura groups are inverted (engine
  group on = obstacle present).

Usage: python3 tools/distortion_world/lost_tower_solver.py [--visit 1|2]
       [--refuse HITMONLEE|VESPIQUEN|LAPRAS|SKARMORY]  (debug: pad refused)
       [--softlock]  (reverse reachability: every reachable state reaches goal)
"""
import argparse
from collections import deque

# --- geometry -------------------------------------------------------------
# Floor standing tiles (x, 1, z), from map_data_677/678 walkable tiles minus
# jump tiles (not standing).
FLOOR = set()
for (x, z) in [
    (22, 10), (22, 11), (15, 11), (19, 11), (20, 11), (21, 11),
    (15, 12), (16, 12), (17, 12), (18, 12), (19, 12), (20, 12), (21, 12), (22, 12),
    (15, 13), (20, 13), (21, 13), (10, 14), (12, 14), (13, 14), (14, 14), (15, 14),
    (10, 15), (12, 15), (13, 15), (14, 15), (15, 15),
    (10, 16), (10, 17), (10, 18), (10, 19), (10, 20), (10, 21),
    (16, 21), (17, 21), (10, 22), (16, 22), (17, 22), (18, 22), (19, 22), (20, 22),
    (23, 22), (26, 22), (29, 22), (32, 22),
    (37, 21), (38, 21), (39, 21), (40, 21), (41, 21),
    (37, 22), (38, 22), (40, 22), (41, 22),
    (37, 23), (38, 23), (39, 23), (40, 23), (41, 23),
    (10, 23), (12, 23), (13, 23), (14, 23), (15, 23), (16, 23), (17, 23),
    (10, 24), (16, 24), (17, 24),
]:
    FLOOR.add((x, 1, z))
# West wall tiles (11, y, z).
WALL = set()
for z in range(13, 23):
    WALL.add((11, 2, z))
for z in (13, 14, 19, 20, 21, 22):
    WALL.add((11, 3, z))
    WALL.add((11, 4, z))

VOID_FLOOR = {(15, 1, 11), (19, 1, 11), (20, 1, 11), (21, 1, 11),
              (20, 1, 13), (21, 1, 13),
              (12, 1, 15), (13, 1, 15), (14, 1, 15), (15, 1, 15)}
VOID_WALL = {(11, 2, 20), (11, 2, 21)}  # false seam

# Groups (Visit 2 engine table only): bit = "open" (SOLID). See design
# doc for the engine mapping (crystal/mist/aura groups are inverted).
G_H2, G_V2, G_STONES, G_GATE, G_SPUR = range(5)
GROUP_TILES = {
    G_H2: {(18, 1, 22)}, G_V2: {(19, 1, 22), (20, 1, 22)},
    G_STONES: {(23, 1, 22), (26, 1, 22), (29, 1, 22), (32, 1, 22)},
    G_GATE: {(38, 1, 22)},
    G_SPUR: {(16, 1, 24), (17, 1, 24)},
}
# Visit 1 walk model: the scripted acts' passability effects, as SET
# stand-ins (V1 has no engine table; see header note).
V1_TRIGGERS = {(11, 2, 15): ("H1", "H1"), (11, 2, 19): ("V1", "V1")}
V1_GROUP_TILES = {(11, 2, 16), (11, 3, 20), (11, 3, 21)}
# SET sigils: tile -> (group, totem or None). All pads/sigils are SET.
# Engine-a sigils / pads, Visit 2 table. Pads (H/V/L) fire only via the
# Yes/No prompt (PressSigil); plain sigils (spur, gate) auto-fire.
# PADS set (tile, group, totem): the solver assumes the player answers Yes.
PADS = {
    (16, 1, 22): (G_H2, "HITMONLEE"),
    (11, 4, 20): (G_V2, "VESPIQUEN"),
    (16, 1, 24): (G_STONES, "LAPRAS"),
}
# Plain engine-a sigils (auto-fire, not pads).
SIGILS = {
    (20, 1, 22): G_SPUR,   # spur sigil: mist clears
    (37, 1, 23): G_GATE,   # gate sigil on the island
}
# Rune: (17,23) -> wall (11,4,20), the V pad tile. Landing fires the pad.
RUNES = {(17, 1, 23): (11, 4, 19)}  # landing fires NOTHING (landing rule); walk onto (11,4,20) for the V pad
# Shadow lane (visit 2): (17,22)-(22,22), 6 tiles (<= DW_ACTORS_MAX_SHADOW_TILES
# = 16), endpoints via DwActors_MakeShadowLane, beat 45-60 frames/tile.
# Ledge + stones only: the island (carry landing, goal, S pad) is off-lane,
# and the lane avoids script tiles (the S pad at (32,22) is off-lane).
SHADOW_LANE = {(x, 1, 22) for x in range(17, 23)}
# No clock/period in the model: the shadow phase is abstracted (see header).


# Checkpoints, all off the shadow lane (catch-before-commit is moot).
# Visit 2 checkpoints (all off-lane). Visit 1 has NO engine checkpoints:
# Phase 0 always falls to the entry and act flags persist (see Model).
CP_TILES_V2 = {(20, 1, 12): 0, (13, 1, 23): 1, (16, 1, 23): 2, (37, 1, 22): 3}
CP_TILES_V1 = {(20, 1, 12): 0}
# Persistent object blockers: Litwick candles (16,21), (37,21), (41,23)
# (the (13,15)/(15,15) candles sit on VOID lips; the (12,19) candle sits
# on a non-floor tile); the Spiritomb at (41,22). Cyrus (39,22) is not
# in FLOOR. Script-only ghost/starter objects are hidden and do not block.
OBJECT_BLOCKERS = {(16, 1, 21), (37, 1, 21), (41, 1, 23), (41, 1, 22),
                   (13, 1, 15), (15, 1, 15)}  # candles, incl. two on VOID lips


class Model:
    def __init__(self, visit, refuse=None):
        self.visit = visit
        self.refuse = refuse
        self.start = (20, 1, 12)
        # Visit 1 has no engine checkpoints: Phase 0 always falls to the
        # entry and act flags persist. Visit 2 commits the four CPs.
        self.cp_tiles = CP_TILES_V1 if visit == 1 else CP_TILES_V2
        # Shadow-wall object blocks (16,23) in Visit 1 only.
        self.blocked_extra = set(OBJECT_BLOCKERS)
        if visit == 1:
            self.blocked_extra.add((16, 1, 23))

    def blocked(self, pos, groups):
        if pos in self.blocked_extra:
            return True
        if self.visit == 1 and pos in V1_GROUP_TILES and not (groups >> 5) & 1:
            return True
        for g, tiles in GROUP_TILES.items():
            if g == G_STONES:
                continue  # VOID when sunk (step = fall), never BLOCKED
            if pos in tiles and not (groups >> g) & 1:
                return True
        return False

    def neighbours(self, pos):
        x, y, z = pos
        out = []
        if pos in WALL:
            for dy, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (11, y + dy, z + dz)
                if q in WALL:
                    out.append((q, "wall"))
        else:
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, 1, z + dz)
                if q in FLOOR:
                    out.append((q, "step"))
        if pos == (12, 1, 14):
            out.append(((11, 2, 13), "jump-on-wall"))
        if pos == (11, 2, 22):
            out.append(((12, 1, 23), "jump-off-wall"))
        for a, b in [((20, 1, 22), (23, 1, 22)), ((23, 1, 22), (26, 1, 22)),
                     ((26, 1, 22), (29, 1, 22)), ((29, 1, 22), (32, 1, 22)),
                     ((23, 1, 22), (20, 1, 22)), ((26, 1, 22), (23, 1, 22)),
                     ((29, 1, 22), (26, 1, 22)), ((32, 1, 22), (29, 1, 22))]:
            if pos == a:
                out.append((b, "hop"))
        return out

    def apply_trigger(self, pos, groups):
        # Visit 1: act stand-ins (passability only; real acts are scripts).
        # One "wall open" stand-in bit (bit 5) for the route model.
        if self.visit == 1:
            if pos in V1_TRIGGERS:
                groups |= (1 << 5)
            return groups
        if pos in PADS:
            g, totem = PADS[pos]
            if not (self.refuse is not None and totem == self.refuse):
                groups |= (1 << g)
            return groups
        if pos in SIGILS:
            groups |= (1 << SIGILS[pos])
        return groups

    def is_pad(self, pos):
        return self.visit == 2 and pos in PADS

    def successors(self, state):
        """state = (pos, groups, cp, snap, vein). No clock: the shadow phase
        is abstracted (see header)."""
        pos, groups, cp, snap, vein = state
        # WAIT: no state change (waiting only changes the shadow phase,
        # which is abstracted away). Kept as an action for path readability.
        yield ((pos, groups, cp, snap, vein), "wait")
        for q, act in self.neighbours(pos):
            if self.blocked(q, groups):
                continue
            # Skarmory carry: a hop onto (32,22) lands on the island.
            # The carry is a script: the shadow is frozen and cannot catch.
            # The S pad's sigil targets the no-op group G_CARRY (no tiles),
            # so it has no walkability effect and is not in this model.
            if self.visit == 2 and q == (32, 1, 22) and act == "hop" and self.refuse != "SKARMORY":
                landing = (37, 1, 22)
                cp_p = self.cp_tiles[landing]
                for res in self._after(landing, groups, cp, snap, cp_p, groups, vein,
                                       act + "+skarmory-carry", True):
                    yield res
                continue
            if q in RUNES:
                landing = RUNES[q]
                g2 = groups  # landing fires NOTHING (landing rule): no sigil, no checkpoint re-fire
                if self.blocked(landing, g2):
                    continue
                cp_p, snap_p = ((self.cp_tiles[landing], g2) if landing in self.cp_tiles
                                else (cp, snap))
                for res in self._after(landing, g2, cp, snap, cp_p, snap_p, vein,
                                       act + "+rune", self.is_pad(landing)):
                    yield res
                continue
            g2 = self.apply_trigger(q, groups)
            vein2 = vein or (self.visit == 1 and q == (13, 1, 23))
            cp_p, snap_p = (self.cp_tiles[q], g2) if q in self.cp_tiles else (cp, snap)
            # A pad step starts the Yes/No prompt script: catch suppressed.
            for res in self._after(q, g2, cp, snap, cp_p, snap_p, vein2, act,
                                   self.is_pad(q)):
                yield res

    def _after(self, landed, groups, old_cp, old_snap, cp_p, snap_p, vein, act, script):
        """Fall/catch checks. No checkpoint is on the shadow lane, so
        checkpoint commitment needs no ordering (engine-a commits during
        HandleStep; a catch on a lane tile requests respawn to the last
        committed checkpoint). A pad/carry step is a script: catch is
        suppressed (engine-b freezes the patrol and suppresses catches
        while a script runs). The shadow phase is abstracted: stepping
        onto a lane tile yields a safe branch (timed it) and a caught
        branch (respawn at the checkpoint with its snapshot). Visit 1
        falls always return to the entry with act flags (groups) and
        the vein flag preserved (Phase 0 semantics)."""
        void = landed in VOID_FLOOR or landed in VOID_WALL
        if (self.visit == 2 and landed in GROUP_TILES[G_STONES]
                and not (groups >> G_STONES) & 1):
            void = True  # hopping onto a sunk stone falls (VOID, open mist)
        if void:
            if self.visit == 1:
                # Phase 0: fall to the entry; acts and vein persist.
                yield ((self._cp_pos(0), groups, 0, 0, vein), act + "+FALL")
            else:
                yield ((self._cp_pos(old_cp), old_snap, old_cp, old_snap, vein), act + "+FALL")
            return
        if not script and self.visit == 2 and landed in SHADOW_LANE:
            # Caught branch: respawn at the checkpoint with its snapshot.
            yield ((self._cp_pos(old_cp), old_snap, old_cp, old_snap, vein), act + "+CAUGHT")
        # Safe branch (also the only branch off-lane / on script steps).
        yield ((landed, groups, cp_p, snap_p, vein), act)

    def _cp_pos(self, cp):
        for tile, idx in self.cp_tiles.items():
            if idx == cp:
                return tile
        raise KeyError(cp)

    def is_goal(self, state):
        pos, groups, cp, snap, vein = state
        if self.visit == 1:
            return pos == (15, 1, 23) and vein
        return pos == (38, 1, 22)


def solve(visit, refuse=None, max_states=4_000_000, explore_all=False):
    m = Model(visit, refuse)
    start = (m.start, 0, 0, 0, False)
    prev = {start: None}
    dq = deque([start])
    goal = None
    while dq:
        s = dq.popleft()
        if m.is_goal(s) and goal is None:
            goal = s
            if not explore_all:
                break
        for ns, act in m.successors(s):
            if ns not in prev:
                prev[ns] = (s, act)
                dq.append(ns)
                if len(prev) > max_states:
                    raise RuntimeError("state cap")
    if goal is None:
        return None, prev, m
    path = []
    s = goal
    while prev[s] is not None:
        p, act = prev[s]
        path.append((act, s))
        s = p
    path.reverse()
    return path, prev, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--visit", type=int, default=0, choices=[0, 1, 2])
    ap.add_argument("--refuse", default=None)
    ap.add_argument("--softlock", action="store_true")
    args = ap.parse_args()
    for visit in ([1, 2] if args.visit == 0 else [args.visit]):
        path, prev, m = solve(visit, args.refuse, explore_all=args.softlock)
        if path is None:
            print(f"visit {visit}: NO SOLUTION (states {len(prev)})")
            continue
        waits = sum(1 for a, _ in path if a == "wait")
        falls = sum(1 for a, _ in path if "FALL" in a or "CAUGHT" in a)
        runes = sum(1 for a, _ in path if "rune" in a)
        print(f"visit {visit}: SOLVED len={len(path)} waits={waits} "
              f"falls/caught_on_path={falls} rune_uses={runes} states={len(prev)}")
        print("  " + " | ".join(a for a, _ in path))
        if args.softlock:
            succ = {}
            for s in prev:
                succ[s] = [ns for ns, _ in m.successors(s)]
            goal_states = [s for s in prev if m.is_goal(s)]
            rev = {}
            for s, ns_list in succ.items():
                for ns in ns_list:
                    rev.setdefault(ns, []).append(s)
            seen = set(goal_states)
            dq = deque(goal_states)
            while dq:
                s = dq.popleft()
                for p in rev.get(s, []):
                    if p not in seen:
                        seen.add(p)
                        dq.append(p)
            dead = [s for s in prev if s not in seen]
            print(f"  soft-lock check: reachable={len(prev)} can_reach_goal={len(seen)} dead={len(dead)}")
            if dead:
                print(f"  DEAD example: {dead[0]}")


if __name__ == "__main__":
    main()
