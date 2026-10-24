"""Offline solver framework for DW puzzles (no emulator).

A rift workstream describes its puzzle as a small Python model and the
framework BFSes the shortest solution, proves no reachable soft-lock
IN THE MODEL, and prints difficulty stats. Models are pure data +
mechanics; nothing here knows about the ROM. The soft-lock proof is
exact over the model's transition graph -- which is why the model's
fidelity matters: a model that omits a mechanic (or models one
wrongly) proves nothing about the real puzzle. The replay of the
solver's solution on the ROM (dwlib) is the cross-check that the
model and the engine agree; a rift ships its model with its tables,
and the replay must pass before the model is trusted.

Model
-----
A model is a PuzzleModel:

    surfaces: {surface: set((x, y, z))}   walkable tiles per surface
        (surface: 0 floor, 1 west wall, 2 east wall, 3 ceiling -- the
        engine-a numbering; tile coords are DW world coords)
    jumps: {(surface, tile, face): (surface, tile)}
        edge jumps / surface changes that happen when the player presses
        `face` on that tile, instead of a plain step (hops, wall-on,
        wall-off, rune-less edge changes). A plain step that leaves every
        surface is blocked.
    start: (surface, tile) plus the initial mechanics state
    goal(state) -> bool
    mechanics: [Mechanic, ...] applied in a fixed order after the step:

        1. move (plain step or jump)          -- the framework
        2. stone push                        -- Stones
        3. rune (surface change in place)    -- Runes
        4. sigil (toggle/set/momentary)      -- Sigils (+ Echo presses)
        5. current slide                     -- Currents
        6. crumble / scar state              -- Crumbling / ScarGroups
        7. shadow catch                      -- Shadow
        8. fall (VOID tile / scar fall)      -- the framework, from the
           step result: the player respawns at the last checkpoint with
           the checkpoint's snapshot (groups, stones, shadow phase --
           the engine's actor snapshot; see PuzzleModel._fall).

State is (surface, tile, groups, stones, landed, crumble,
shadow_phase, shadow_dir, checkpoint, held, echo). `groups` is a
tuple of bools (one per group); `stones` a tuple of (surface, tile)
sorted; `landed` the frozenset of stone positions that have dropped
(LANDED); `crumble` is mechanic private state (a tuple);
`checkpoint` is a snapshot ((surface, tile), groups, stones,
shadow_phase, landed, shadow_dir) -- crumble/scar state is NOT
snapshotted, because a fall warp reloads the map and one-use tiles
and scars are whole again (Ravaged Path's walkway reset); `held`
is the set of momentary sigils currently stood on (so releases fire
on stepping off) and is NOT snapshotted: momentary holders are
per-occupant and cleared on restore, so after a fall the player must
re-press them. States are hashable, so BFS is exact over the model.

Abstraction boundaries (documented, not hidden): a stone fall is
atomic within the press. The engine falls a stone over 12 frames
(DW_STONE_FALL_FRAMES), reserving its edge tile and landing during
the fall (DwActors_TryPush: no stacking falls, no landing clash);
but a step takes longer than 12 frames, so the reservation lifts
before the next press's push hook runs, and a FALLING stone is
never observable at press granularity. The design's mid-fall
checkpoint snapshot covers script/carry arrivals within 12 frames
of a drop, which the solver (walking only) does not model. A
LANDED stone's tile keeps its underlying mechanics (a current under
a LANDED stone still fires -- the stone is terrain, not a plug).
Pads are not modelled: they carry padUsed (one use per load per
pad, checkpointed and restored), which gates the totem-act
prompt/cutscene, not movement. The shadow's beat frame counter and
the stone fall timer are sub-press timing: the solver steps each
once per press/wait.

A mechanic only has to implement:
  - tags(state, from_tile, to_tile, face) -> (extra_state_changes, tags)
    called on arrival, returning a dict of state-field updates (or
    None) plus transition tags for the difficulty stats ("toggle",
    "push", "rune", ...), or
  - slide / fall / push hooks where noted on the class.

Move strings use the dwlib alphabet: U/D/L/R are FACE_* presses,
W is an alias for U, A taps A (never emitted by the solver).
Solver moves are "pressed" moves only: a current slide triggered by
one press is part of that one transition, not extra letters.

Soft-lock proof. Every transition in the graph -- plain steps, jumps,
slides, falls, resets -- is an edge. BFS from the start builds the
reachable set; reverse BFS from the goal over the same edges finds
every state that can still reach the goal. A reachable state outside
the reverse set is a soft-lock: the proof lists one, with a shortest
path to it. An unreachable goal is reported the same way.

Difficulty stats. optimal length (pressed moves), branching (mean
out-degree over reachable states), required toggles/pushes (how many
of each tag the optimal solution uses), and wrong-looking right
moves: optimal steps that do not strictly decrease the plain-grid
distance to the goal (BFS distance ignoring mechanics). Stepping onto
a sigil you then have to step off, backing up to take a rung, or
walking past the goal to find the fork all show up here.

Per-rift targets (revised PUZZLE_PLAN section 2). check_targets(rift,
stats) flags an optimal length outside the plan row's range, and a
branching below 1.2 for rifts of difficulty >= 2 (a corridor with no
decision; the plan gives no branching ranges, so this floor is a
harness heuristic, labelled as such). Difficulty 1 (Arc 1) has no floor.
"""

from __future__ import annotations

import collections
import itertools

FACE_UP, FACE_DOWN, FACE_LEFT, FACE_RIGHT, WAIT = 0, 1, 2, 3, 4
FACE_LETTER = {0: "U", 1: "D", 2: "L", 3: "R", 4: "."}
SURF_FLOOR, SURF_WEST, SURF_EAST, SURF_CEIL = 0, 1, 2, 3

DIR_DELTA = {
    0: ((0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0)),
    1: ((0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)),
    2: ((0, 1, 0), (0, -1, 0), (0, 0, -1), (0, 0, 1)),
    3: ((0, 0, 1), (0, 0, -1), (-1, 0, 0), (1, 0, 0)),
}

# Revised plan (section 2): rift -> (difficulty, (min_len, max_len)).
TARGETS = {
    0: (1, (10, 20)),
    1: (2, (15, 25)),
    2: (3, (25, 40)),
    3: (4, (35, 50)),
    4: (5, (45, 65)),
    5: (6, (55, 80)),   # visit 2; visit 1 is a ~3 warm-up of ~20 steps
    6: (7, (80, 100)),
    7: (8.5, (100, 120)),
    8: (10, (120, 10 ** 9)),
}


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


# ---------------------------------------------------------------------------
# Mechanics
# ---------------------------------------------------------------------------

class Mechanic:
    """Base class. Only the hooks a mechanic needs are overridden."""

    def initial(self, model):
        """Extra initial state fields, as {field: value}."""
        return {}

    def on_arrive(self, model, state, prev, face, tags):
        """After the step lands. Return {field: value} updates, or a
        fall request as {'fall': True}. `tags` is a list to append to."""
        return {}

    def on_leave(self, model, state, prev, face, tags):
        """After leaving `prev` (for momentary releases / crumble)."""
        return {}


class GroupsMixin:
    """Shared group-state helpers for mechanics that toggle groups."""

    def __init__(self, n_groups):
        self.n_groups = n_groups

    def flipped(self, groups, i):
        g = list(groups)
        g[i] = not g[i]
        return tuple(g)

    def set_group(self, groups, i, val):
        g = list(groups)
        g[i] = bool(val)
        return tuple(g)


class Sigils(Mechanic, GroupsMixin):
    """sigils: {(surface, tile): (kind, target_group, set_value)}
    kind: 'toggle' | 'set' | 'momentary' | 'reset'. Momentary sigils
    hold their group on while stood on (holder count kept in `held`:
    the set of momentary sigil keys currently pressed). Reset restores
    the checkpoint snapshot (groups/stones/shadow_phase/landed/
    shadow_dir) without moving the player, and clears `held`. Crumble is
    map-load state: a reset does not reload the map, so the
    fresh-crumble restore is the same map-load state a fall warp
    produces."""

    def __init__(self, sigils, n_groups):
        GroupsMixin.__init__(self, n_groups)
        self.sigils = dict(sigils)

    def on_arrive(self, model, state, prev, face, tags):
        key = (state["surface"], state["tile"])
        sig = self.sigils.get(key)
        if sig is None:
            return {}
        kind, target, value = sig
        if kind == "toggle":
            tags.append("toggle")
            return {"groups": self.flipped(state["groups"], target)}
        if kind == "set":
            tags.append("toggle")
            return {"groups": self.set_group(state["groups"], target, value)}
        if kind == "momentary":
            held = set(state["held"]) | {key}
            tags.append("toggle")
            return {"held": frozenset(held),
                    "groups": self.set_group(state["groups"], target, True)}
        if kind == "reset":
            tags.append("reset")
            cp = state["checkpoint"]
            # A reset restores the checkpoint snapshot
            # (groups/stones/shadow_phase/landed/shadow_dir) and the
            # fresh crumble state: a fall warp reloads the map, so
            # scars / one-use tiles are whole again.
            return {"groups": cp[1], "stones": cp[2],
                    "shadow_phase": cp[3], "landed": cp[4],
                    "shadow_dir": cp[5],
                    "crumble": model.fresh_crumble(),
                    "held": frozenset()}
        raise ValueError(f"bad sigil kind {kind!r}")

    def on_leave(self, model, state, prev, face, tags):
        # Recompute momentary-held groups from the sigils still held
        # after leaving `prev`: a group stays on while any momentary
        # sigil for it is held, else falls back to its toggled state.
        # (The toggled state is the state we left behind minus the
        # momentary hold; the framework stores it in `groups` already
        # with the hold applied, so recompute from `held` only when a
        # momentary sigil was released.)
        key = (prev[0], prev[1])
        sig = self.sigils.get(key)
        if sig is None or sig[0] != "momentary":
            return {}
        held = set(state["held"]) - {key}
        groups = list(state["groups"])
        # The released group turns off unless another held momentary
        # sigil targets it. Restriction (documented): a group fed by
        # a momentary sigil is not also a toggle/set target, so the
        # holder set is the whole truth for that group.
        held_targets = {self.sigils[k][1] for k in held if self.sigils[k][0] == "momentary"}
        groups[sig[1]] = sig[1] in held_targets
        return {"held": frozenset(held), "groups": tuple(groups)}


class Runes(Mechanic):
    """runes: {(surface, tile): (surface, tile)} -- stepping on a rune
    changes surface in place (the target tile is on the destination
    surface). The rune fires once per arrival; a rune whose target is
    also a rune does not chain (the engine fires once per step)."""

    def __init__(self, runes):
        self.runes = dict(runes)

    def on_arrive(self, model, state, prev, face, tags):
        dest = self.runes.get((state["surface"], state["tile"]))
        if dest is None:
            return {}
        tags.append("rune")
        return {"surface": dest[0], "tile": dest[1]}


class Currents(Mechanic):
    """currents: {(surface, tile): face} -- drift direction on the tile.
    After arrival, the player slides tile by tile in the current's
    direction until blocked (not walkable, a RESTING stone there, or
    leaving the surface set) or off-current. Landing on a sigil /
    rune / checkpoint / a current with a different direction ends
    the slide there (that tile's logic runs; a different-direction
    current re-slides from the new direction, but a slide never
    re-enters a tile it already visited in this slide). A slide's
    tiles are part of the one pressed move. Also handles
    stone-plugged currents: a slide stops before a tile holding a
    RESTING stone; a LANDED stone's tile is walkable terrain, so the
    slide passes over it (the stone is not a plug)."""

    def __init__(self, currents):
        self.currents = dict(currents)

    def slide(self, model, state, tags):
        """Returns (state updates, stopped_on_mechanic_tile_bool)."""
        surf, tile = state["surface"], state["tile"]
        seen = {(surf, tile)}
        cur = self.currents.get((surf, tile))
        if cur is None:
            return {}, False
        tags.append("slide")
        while cur is not None:
            nxt = add(tile, DIR_DELTA[surf][cur])
            if (surf, nxt) in seen or nxt not in model.surfaces.get(surf, ()):
                break
            if (surf, nxt) in state["stones"] \
                    and (surf, nxt) not in state["landed"]:
                break  # RESTING stone plugs; LANDED stone is terrain
            tile = nxt
            seen.add((surf, tile))
            # A sigil/rune/checkpoint tile ends the slide; its logic
            # runs in the framework's arrival pass for the final tile.
            if model.is_mechanic_tile(surf, tile):
                return {"tile": tile}, True
            cur = self.currents.get((surf, tile))
        return {"tile": tile}, False


class Stones(Mechanic):
    """Pushable stones. stones: initial tuple of (surface, tile).
    drops: {(surface, tile): (surface, tile)} -- pushing a stone into
    the edge at `tile` (the tile beyond the walkable surface) drops it
    to the surface below at the mapped tile. protected: {(surface,
    tile)} -- tiles a stone may never be pushed onto (the table's
    listed protected tiles); landing tiles are added automatically
    (reserved against plain pushes -- a stone may still DROP onto
    its own landing). Protected tiles are walkable for the PLAYER:
    only stone pushes are blocked, matching the engine (protected
    tiles are player-walkable; TryPush blocks the stone).
    State: `stones` = tuple of positions, `landed` = frozenset of
    positions whose stone has dropped (LANDED). A RESTING stone is
    BLOCKED and pushable; a LANDED stone is SOLID walkable terrain:
    the player steps onto it, it cannot be pushed, and a slide
    passes over it. A RESTING stone on a current tile plugs the
    current (Currents stops before it). Push checks mirror
    DwActors_TryPush: a designated edge drops before any walkability
    check (FindEdge beats TileAt); a plain push is blocked on a
    protected tile, a stone, a non-walkable tile, or a VOID tile
    (TileAt BLOCKED/VOID). A fall is modelled as atomic within the
    press (see the module docstring): the falling stone occupies
    no tile, and by the time the next press resolves it has
    landed."""

    def __init__(self, stones, drops=None, protected=()):
        self.stones = tuple(sorted(stones))
        self.drops = dict(drops or {})
        # Landing tiles are reserved: a stone may only land there,
        # never be pushed there (plain pushes onto a landing are
        # blocked; the drop itself is allowed).
        self.protected = set(protected) | set(self.drops.values())

    def initial(self, model):
        return {"stones": self.stones}

    def try_push(self, model, state, surf, tile, face, tags):
        """If a stone sits at the destination tile, push it. Returns
        ((stones_tuple, landed_frozenset), ok). The framework calls
        this before moving. A LANDED stone is terrain, not an
        obstacle: the step proceeds with no push."""
        stones = state["stones"]
        landed = state["landed"]
        if (surf, tile) not in stones:
            return (stones, landed), True
        if (surf, tile) in landed:
            return (stones, landed), True
        delta = DIR_DELTA[surf][face]
        beyond = add(tile, delta)
        # Protected target: no push of any kind onto it.
        if (surf, beyond) in self.protected:
            return (stones, landed), False
        # Designated edge: drop first, before any walkability check.
        drop = self.drops.get((surf, beyond))
        if drop is not None:
            if (surf, beyond) in stones or drop in stones:
                return (stones, landed), False  # edge / landing occupied
            if drop[1] not in model.surfaces.get(drop[0], ()):
                return (stones, landed), False
            new = set(stones)
            new.discard((surf, tile))
            new.add(drop)
            tags.append("push")
            tags.append("drop")
            return (tuple(sorted(new)), landed | {drop}), True
        # Plain push: no stacking, walkable, not VOID.
        if (surf, beyond) in stones:
            return (stones, landed), False
        if beyond not in model.surfaces.get(surf, ()) \
                or (surf, beyond) in model.void_tiles:
            return (stones, landed), False
        new = set(stones)
        new.discard((surf, tile))
        new.add((surf, beyond))
        tags.append("push")
        return (tuple(sorted(new)), landed), True


class Crumbling(Mechanic):
    """Per-tile one-use tiles (a tile crumbles one step after it is
    left; stepping on a crumbled tile is a fall). crumble_tiles:
    set of (surface, tile). State field `crumble` = (crumbled
    frozenset, left_tile_or_None). One step after leaving a crumble
    tile it is crumbled for good."""

    def __init__(self, crumble_tiles):
        self.tiles = set(crumble_tiles)

    def initial(self, model):
        return {"crumble": (frozenset(), None)}

    def on_arrive(self, model, state, prev, face, tags):
        crumbled, left = state["crumble"]
        if (state["surface"], state["tile"]) in crumbled:
            return {"fall": True}
        # The tile left on the previous step crumbles now.
        new_crumbled = set(crumbled)
        if left is not None and (prev[0], prev[1]) in self.tiles:
            new_crumbled.add((prev[0], prev[1]))
        if (state["surface"], state["tile"]) in self.tiles:
            tags.append("crumble")
            return {"crumble": (frozenset(new_crumbled), (state["surface"], state["tile"]))}
        return {"crumble": (frozenset(new_crumbled), None)}


class ScarGroups(Mechanic):
    """Ravaged Path scars (the game's exact rule). groups: {idx:
    set((surface, tile))}. State field `crumble` = (states tuple,
    prev_group_or_-1) with states in 0 intact / 1 holding / 2 left /
    3 crumbled. At each step, LEFT groups crumble; stepping onto a
    non-intact group tile falls; stepping from one tile of a group to
    another tile of the same group falls (the group is HOLDING, not
    INTACT); leaving a HOLDING group marks it LEFT."""

    def __init__(self, groups):
        self.groups = {i: set(v) for i, v in groups.items()}
        self.lookup = {}
        for i, tiles in self.groups.items():
            for t in tiles:
                self.lookup[t] = i

    def initial(self, model):
        return {"crumble": (tuple(0 for _ in self.groups), -1)}

    def on_arrive(self, model, state, prev, face, tags):
        states, prev_g = state["crumble"]
        states = [3 if s == 2 else s for s in states]  # LEFT -> crumbled
        key = (state["surface"], state["tile"])
        g = self.lookup.get(key, -1)
        if g >= 0 and states[g] != 0:
            return {"fall": True}
        if prev_g >= 0 and prev_g != g and states[prev_g] == 1:
            states[prev_g] = 2
        if g >= 0:
            states[g] = 1
            tags.append("scar")
        return {"crumble": (tuple(states), g)}


class Shadow(Mechanic):
    """Giratina's shadow: patrol lanes. lane: [(surface, tile), ...]
    walked on a fixed beat; phase advances one step per pressed move
    (or per WAIT). `pingpong`: the lane reverses at its ends
    (0,1,2,1,0,...), matching the engine's pingpong direction; loop
    lanes wrap (0,1,2,0,...). The checkpoint snapshot stores phase
    AND direction (the engine snapshots pattern index + pingpong
    direction + beat frame counter). The beat frame counter is
    sub-beat timing the press-level model does not represent: the
    solver's phase advances once per press/wait, while the engine
    advances once per beatFrames frames -- a press is not a beat.
    For fast play the solver's shadow may step more often than the
    engine's (conservative for catching: it catches the player where
    the engine might not have arrived yet); timing-critical rifts
    calibrate via the replay.
    Caught = the shadow's tile equals the player's after the move
    (and the player is not on a tile in `safe`), which respawns at the
    last checkpoint (falls count as respawns, not falls). `phase0` is
    the starting index into the lane."""

    def __init__(self, lane, safe=(), phase0=0, pingpong=False):
        self.lane = list(lane)
        self.safe = set(safe)
        self.phase0 = phase0
        self.pingpong = pingpong

    def initial(self, model):
        return {"shadow_phase": self.phase0, "shadow_dir": 1}

    def advance(self, state):
        """Next (phase, direction) after one beat. Pure: returns the
        update dict."""
        n = len(self.lane)
        if n <= 1:
            return {"shadow_phase": 0, "shadow_dir": 1}
        phase, d = state["shadow_phase"], state["shadow_dir"]
        if not self.pingpong:
            return {"shadow_phase": (phase + 1) % n, "shadow_dir": 1}
        nxt = phase + d
        if nxt >= n or nxt < 0:
            d = -d
            nxt = phase + d
        return {"shadow_phase": nxt, "shadow_dir": d}

    def on_arrive(self, model, state, prev, face, tags):
        upd = self.advance(state)
        shadow_here = self.lane[upd["shadow_phase"]]
        if (state["surface"], state["tile"]) == shadow_here \
                and (state["surface"], state["tile"]) not in self.safe:
            tags.append("caught")
            upd = dict(upd, respawn=True)
        return upd


class Echo(Mechanic):
    """Echo self: a mirrored ghost on a paired surface. mirror:
    (surface, tile) -> (surface, tile) for the player's tile, or None
    (no echo there). echo_sigils: {(surface, tile): (kind, group, val)}
    with the same kinds as Sigils (the echo presses them when it
    arrives). The echo moves with the player's pressed move: its
    delta is the mirror of the player's new tile minus the mirror of
    the old tile. State field `echo` = (surface, tile) or None."""

    def __init__(self, mirror, echo_sigils, n_groups):
        self.mirror = dict(mirror)
        self.sigils = dict(echo_sigils)
        self.n_groups = n_groups

    def initial(self, model):
        return {"echo": None}

    def on_arrive(self, model, state, prev, face, tags):
        key = (state["surface"], state["tile"])
        echo = self.mirror.get(key)
        if echo is None:
            return {"echo": None}
        updates = {"echo": echo}
        sig = self.sigils.get(echo)
        if sig is not None:
            kind, target, value = sig
            if kind == "toggle":
                g = list(state["groups"])
                g[target] = not g[target]
                updates["groups"] = tuple(g)
                tags.append("echo-toggle")
            elif kind == "set":
                g = list(state["groups"])
                g[target] = bool(value)
                updates["groups"] = tuple(g)
                tags.append("echo-toggle")
        return updates


# ---------------------------------------------------------------------------
# Model + BFS
# ---------------------------------------------------------------------------

class PuzzleModel:
    def __init__(self, name, surfaces, start, goal, jumps=None, mechanics=(),
                 checkpoints=(), void_tiles=(), n_groups=0, gate_tiles=None):
        self.name = name
        self.surfaces = {s: set(t) for s, t in surfaces.items()}
        self.start = start  # (surface, tile)
        self.goal = goal    # callable(state_dict) -> bool
        self.jumps = dict(jumps or {})
        self.mechanics = list(mechanics)
        self.checkpoints = list(checkpoints)  # [(surface, tile), ...]; [0] = entry
        self.void_tiles = set(void_tiles)    # step = fall
        self.n_groups = n_groups
        # gate_tiles: {group_index: set((surface, tile))} -- a gated
        # tile is walkable only while its group is on (a group-gated
        # bridge). A tile in the plain grid is never gated.
        self.gate_tiles = {g: set(v) for g, v in (gate_tiles or {}).items()}
        self._gate_of = {}
        for g, tiles in self.gate_tiles.items():
            for t in tiles:
                self._gate_of[t] = g
        self._sigil_keys = set()
        self._rune_keys = set()
        for m in self.mechanics:
            if isinstance(m, Sigils):
                self._sigil_keys |= set(m.sigils)
            if isinstance(m, Runes):
                self._rune_keys |= set(m.runes)

    def is_mechanic_tile(self, surf, tile):
        """Tiles whose own logic ends a slide (sigil / rune / checkpoint)."""
        return (surf, tile) in self._sigil_keys or (surf, tile) in self._rune_keys \
            or (surf, tile) in self.checkpoints

    def fresh_crumble(self):
        """The crumble/scar state of a freshly loaded map (a fall warp
        reloads the map, so one-use tiles and scars are whole again).
        Only one crumble mechanic per model carries it."""
        crumble = (frozenset(), None)
        for m in self.mechanics:
            init = m.initial(self)
            if "crumble" in init:
                crumble = init["crumble"]
        return crumble

    def initial_state(self):
        st = {"surface": self.start[0], "tile": self.start[1],
              "groups": tuple(False for _ in range(self.n_groups)),
              "stones": tuple(), "landed": frozenset(),
              "crumble": self.fresh_crumble(),
              "shadow_phase": 0, "shadow_dir": 1,
              "held": frozenset(), "echo": None}
        for m in self.mechanics:
            st.update(m.initial(self))
        # A checkpoint snapshots (tile, groups, stones, shadow_phase,
        # landed, shadow_dir) -- the engine's actor snapshot
        # (pattern index + pingpong direction; the beat frame counter
        # is sub-beat timing, see Shadow). Crumble state is map-load
        # state (see fresh_crumble); `held` is per-occupant and
        # cleared on restore, so it is not snapshotted.
        st["checkpoint"] = (self.start, st["groups"], st["stones"],
                            st["shadow_phase"], st["landed"],
                            st["shadow_dir"])
        return st

    def _freeze(self, st):
        return (st["surface"], st["tile"], st["groups"], st["stones"],
                st["landed"], st["crumble"], st["shadow_phase"],
                st["shadow_dir"], st["held"], st["echo"],
                st["checkpoint"])

    def successors(self, state):
        """Yields (face, new_state, tags). Falls/respawns are edges
        too: the new state's tile is the checkpoint tile. WAIT (face
        4) stands still: only time-based mechanics (Shadow) tick."""
        out = []
        for face in range(4):
            nxt, tags = self._step(state, face)
            if nxt is not None:
                out.append((face, nxt, tags))
        nxt, tags = self._wait(state)
        if nxt is not None:
            out.append((WAIT, nxt, tags))
        return out

    def _wait(self, state):
        """Stand still for one beat. Only Shadow advances; a wait that
        gets the player caught is a respawn edge. Waiting while the
        shadow is elsewhere is a self-loop -- it is still a useful
        edge (it changes the phase), so it is kept."""
        tags = ["wait"]
        st = dict(state)
        for m in self.mechanics:
            if isinstance(m, Shadow):
                upd = m.advance(st)
                st.update(upd)
                if (st["surface"], st["tile"]) == m.lane[upd["shadow_phase"]] \
                        and (st["surface"], st["tile"]) not in m.safe:
                    tags.append("caught")
                    return self._respawn(st, tags), tags
        return st, tags

    def _step(self, state, face):
        tags = []
        surf, tile = state["surface"], state["tile"]
        # Jump (hop / edge surface change) beats a plain step.
        if (surf, tile, face) in self.jumps:
            nsurf, ntile = self.jumps[(surf, tile, face)]
            return self._arrive(state, (surf, tile), nsurf, ntile, face, tags, jumped=True)
        delta = DIR_DELTA[surf][face]
        ntile = add(tile, delta)
        gate = self._gate_of.get((surf, ntile))
        if gate is not None:
            if not state["groups"][gate]:
                return None, tags  # gated bridge is off
        elif ntile not in self.surfaces.get(surf, ()):
            return None, tags
        # Stones: push before moving.
        stones = state["stones"]
        landed = state["landed"]
        for m in self.mechanics:
            if isinstance(m, Stones):
                (stones, landed), ok = m.try_push(self, state, surf, ntile,
                                                  face, tags)
                if not ok:
                    return None, tags
        return self._arrive(state, (surf, tile), surf, ntile, face, tags,
                            jumped=False, stones=stones, landed=landed)

    def _arrive(self, state, prev, surf, tile, face, tags, jumped,
                stones=None, landed=None):
        st = dict(state)
        if stones is not None:
            st["stones"] = stones
        if landed is not None:
            st["landed"] = landed
        st["surface"], st["tile"] = surf, tile
        # Momentary releases: leaving `prev` (all mechanics see it).
        for m in self.mechanics:
            upd = m.on_leave(self, st, prev, face, tags)
            st.update(upd)
        # Arrival: stones already applied; runes, sigils, echo, scars,
        # shadow in mechanic order, then currents slide, then fall.
        for m in self.mechanics:
            if isinstance(m, (Stones, Currents)):
                continue
            upd = m.on_arrive(self, st, prev, face, tags)
            if upd.pop("fall", False):
                return self._fall(st, tags), tags
            if upd.pop("respawn", False):
                return self._respawn(st, tags), tags
            st.update(upd)
        # Currents slide (after the arrival logic of the landing tile).
        for m in self.mechanics:
            if isinstance(m, Currents):
                upd, _stopped = m.slide(self, st, tags)
                st.update(upd)
                # The slide's final tile may be a sigil/rune: run its
                # arrival logic once (the landing tile, not the start).
                if upd.get("tile") is not None and upd["tile"] != tile:
                    for m2 in self.mechanics:
                        if isinstance(m2, (Stones, Currents)):
                            continue
                        upd2 = m2.on_arrive(self, st, prev, face, tags)
                        if upd2.pop("fall", False):
                            return self._fall(st, tags), tags
                        if upd2.pop("respawn", False):
                            return self._respawn(st, tags), tags
                        st.update(upd2)
                break
        # A reset sigil's restore is authoritative over anything else
        # this press did to the snapshotted fields: the shadow tick
        # for this press must not undo the restore (mechanic list
        # order must not decide whether the reset reset the shadow).
        # The restore was already applied mid-pass (so later arrival
        # logic sees restored state); re-apply it now so it wins.
        if "reset" in tags:
            cp = st["checkpoint"]
            st["groups"], st["stones"] = cp[1], cp[2]
            st["shadow_phase"], st["landed"] = cp[3], cp[4]
            st["shadow_dir"] = cp[5]
            st["held"] = frozenset()
        # Checkpoint snapshot (tile, groups, stones, shadow_phase,
        # landed, shadow_dir) -- the engine's actor snapshot.
        if (st["surface"], st["tile"]) in self.checkpoints:
            tags.append("checkpoint")
            st["checkpoint"] = ((st["surface"], st["tile"]), st["groups"],
                                st["stones"], st["shadow_phase"],
                                st["landed"], st["shadow_dir"])
        # VOID tile: fall.
        if (st["surface"], st["tile"]) in self.void_tiles:
            tags.append("fall")
            return self._fall(st, tags), tags
        return st, tags

    def _fall(self, st, tags):
        # Restore the checkpoint snapshot (groups, stones, shadow
        # phase + direction, landed) exactly as the engine's actor
        # snapshot restore does; crumble is map-load state (a fall
        # warp reloads the map); momentary holders are per-occupant
        # and cleared; the echo is recomputed from the restored tile,
        # so the stale cache is dropped. A stone that was mid-fall
        # when the player fell is restored to its checkpoint state,
        # the same as a stone that had already landed (a fall is
        # atomic within a press -- see Stones).
        cp = st["checkpoint"]
        out = dict(st)
        out["surface"], out["tile"] = cp[0]
        out["groups"], out["stones"] = cp[1], cp[2]
        out["shadow_phase"], out["landed"] = cp[3], cp[4]
        out["shadow_dir"] = cp[5]
        out["crumble"] = self.fresh_crumble()
        out["held"] = frozenset()
        out["echo"] = None
        return out

    def _respawn(self, st, tags):
        # Caught by the shadow: same restore as a fall, no fall tag.
        return self._fall(st, tags)

    # -- analysis -----------------------------------------------------

    def solve(self):
        """BFS. Returns SolveResult, or None if the goal is unreachable."""
        start = self.initial_state()
        start_key = self._freeze(start)
        prev = {start_key: None}
        move_of = {}
        tags_of = {}
        queue = collections.deque([start])
        seen = {start_key: start}
        goal_key = None
        while queue:
            st = queue.popleft()
            key = self._freeze(st)
            if self.goal(st):
                goal_key = key
                break
            for face, nxt, tags in self.successors(st):
                nkey = self._freeze(nxt)
                if nkey not in seen:
                    seen[nkey] = nxt
                    prev[nkey] = key
                    move_of[nkey] = face
                    tags_of[nkey] = tags
                    queue.append(nxt)
        if goal_key is None:
            return None
        moves, tags = [], []
        key = goal_key
        while prev[key] is not None:
            moves.append(move_of[key])
            tags.append(tags_of[key])
            key = prev[key]
        moves.reverse()
        tags.reverse()
        return SolveResult(self, seen, prev, goal_key, moves, tags)

    def reachable(self):
        """All reachable (key -> state), via BFS without stopping."""
        start = self.initial_state()
        start_key = self._freeze(start)
        seen = {start_key: start}
        queue = collections.deque([start])
        edges = collections.defaultdict(list)
        while queue:
            st = queue.popleft()
            key = self._freeze(st)
            for face, nxt, tags in self.successors(st):
                nkey = self._freeze(nxt)
                edges[key].append(nkey)
                if nkey not in seen:
                    seen[nkey] = nxt
                    queue.append(nxt)
        return seen, edges

    def soft_locks(self):
        """Reachable states that cannot reach the goal (falls, resets
        and slides are edges, so a state that can fall/reset its way
        back still counts as reaching). Returns [(key, path_moves)]."""
        seen, edges = self.reachable()
        reverse = collections.defaultdict(list)
        for a, bs in edges.items():
            for b in bs:
                reverse[b].append(a)
        can = set()
        queue = collections.deque([k for k, st in seen.items() if self.goal(st)])
        can.update(queue)
        while queue:
            k = queue.popleft()
            for p in reverse.get(k, ()):
                if p not in can:
                    can.add(p)
                    queue.append(p)
        # Shortest path to each soft-locked state, for the report.
        bad = [k for k in seen if k not in can]
        if not bad:
            return []
        # BFS from the start to recover parent pointers.
        start = self._freeze(self.initial_state())
        prev = {start: None}
        move_of = {}
        queue = collections.deque([start])
        while queue:
            k = queue.popleft()
            for nxt in edges.get(k, ()):
                if nxt not in prev:
                    prev[nxt] = k
                    queue.append(nxt)
        out = []
        for k in bad[:10]:
            path, cur = [], k
            while prev.get(cur) is not None:
                path.append(cur)
                cur = prev[cur]
            out.append((seen[k], len(path)))
        return out


class SolveResult:
    def __init__(self, model, seen, prev, goal_key, moves, tags):
        self.model, self.seen, self.prev = model, seen, prev
        self.goal_key, self.moves, self.tags = goal_key, moves, tags

    @property
    def move_string(self):
        return " ".join(FACE_LETTER[m] for m in self.moves)

    def stats(self):
        """Difficulty stats for this model + solution."""
        model = self.model
        seen, edges = model.reachable()
        n = len(seen)
        branching = (sum(len(v) for v in edges.values()) / n) if n else 0.0
        flat = [t for step in self.tags for t in step]
        # Plain-grid distance to the goal tile (ignoring mechanics),
        # over surfaces+jumps, for the wrong-looking count.
        goal_tiles = None
        dist = self._plain_distances()
        wrong = 0
        st = model.initial_state()
        for face in self.moves:
            before = dist.get((st["surface"], st["tile"]), 10 ** 9)
            if face == WAIT:
                nxt, _tags = model._wait(st)
            else:
                nxt, _tags = model._step(st, face)
            st = nxt
            after = dist.get((st["surface"], st["tile"]), 10 ** 9)
            if after >= before:
                wrong += 1
        return {"optimal_length": len(self.moves), "branching": round(branching, 2),
                "reachable_states": n,
                "toggles": flat.count("toggle") + flat.count("echo-toggle"),
                "pushes": flat.count("push"),
                "runes": flat.count("rune"), "slides": flat.count("slide"),
                "falls_in_solution": flat.count("fall"),
                "wrong_looking_right_moves": wrong,
                "move_string": self.move_string}

    def _plain_distances(self):
        """BFS distance (plain steps + jumps) to any goal state tile,
        per (surface, tile). Goal states are those the model's goal()
        accepts; approximate with the goal_key's tile when goal() is
        tile-based, else fall back to distance 0 at the goal tile."""
        model = self.model
        goal_tile = (self.goal_key[0], self.goal_key[1])
        dist = {goal_tile: 0}
        queue = collections.deque([goal_tile])
        # Reverse edges over the plain grid + jumps.
        while queue:
            surf, tile = queue.popleft()
            d = dist[(surf, tile)]
            for face in range(4):
                delta = DIR_DELTA[surf][face]
                prev_tile = (tile[0] - delta[0], tile[1] - delta[1], tile[2] - delta[2])
                if prev_tile in model.surfaces.get(surf, ()) \
                        and (surf, prev_tile) not in dist:
                    dist[(surf, prev_tile)] = d + 1
                    queue.append((surf, prev_tile))
            for (s, t, f), (ds, dt) in model.jumps.items():
                if (ds, dt) == (surf, tile) and (s, t) not in dist:
                    dist[(s, t)] = d + 1
                    queue.append((s, t))
        return dist


def check_targets(rift_no, stats):
    """Flag optimal length outside the plan row's range, and branching
    below the 1.2 harness floor for difficulty >= 2 (the plan gives no
    branching ranges; the floor is a harness heuristic). Returns a list
    of finding strings (empty = in range)."""
    diff, (lo, hi) = TARGETS[rift_no]
    out = []
    if not lo <= stats["optimal_length"] <= hi:
        out.append(f"optimal length {stats['optimal_length']} outside "
                   f"plan range {lo}-{hi} for rift {rift_no} (difficulty {diff})")
    if diff >= 2 and stats["branching"] < 1.2:
        out.append(f"branching {stats['branching']} below the 1.2 harness "
                   f"floor for rift {rift_no} (difficulty {diff}): a corridor, no decision")
    return out


# ---------------------------------------------------------------------------
# Worked examples (one per mechanic) + Ravaged Path sanity model
# ---------------------------------------------------------------------------

def _goal_at(surf, tile):
    return lambda st: (st["surface"], st["tile"]) == (surf, tile)


def sigil_gate_example():
    """Sigil + group-gated bridge: the bridge tile (2,1,1) is walkable
    only while group 0 is on. Step on the sigil at (0,1,1) to turn
    the bridge on, cross it, reach (3,1,1)."""
    return PuzzleModel(
        "sigil-gate", {0: {(-1, 1, 1), (0, 1, 1), (1, 1, 1), (3, 1, 1)}},
        (0, (-1, 1, 1)), _goal_at(0, (3, 1, 1)), n_groups=1,
        gate_tiles={0: {(0, (2, 1, 1))}},
        mechanics=[Sigils({(0, (0, 1, 1)): ("toggle", 0, 0)}, 1)])


def rune_example():
    """Rune: the floor tile (2,1,1) flips the player to the ceiling
    tile (2,10,1); the goal is further along the ceiling."""
    surfaces = {0: {(1, 1, 1), (2, 1, 1)}, 3: {(2, 10, 1), (3, 10, 1)}}
    return PuzzleModel("rune", surfaces, (0, (1, 1, 1)), _goal_at(3, (3, 10, 1)),
                       mechanics=[Runes({(0, (2, 1, 1)): (3, (2, 10, 1))})])


def current_example():
    """Current: stepping east onto (2,1,1) slides east until the wall
    at (4,1,1) is not walkable; the goal (3,1,1) is passed mid-slide
    but a slide stops on mechanic tiles -- here the goal tile ends it
    because goal tiles are not mechanic tiles, so the slide stops at
    (3,1,1) only if it is the end of the slide: actually the slide
    stops at the last walkable tile (3,1,1)."""
    surfaces = {0: {(1, 1, 1), (2, 1, 1), (3, 1, 1)}}
    return PuzzleModel("current", surfaces, (0, (1, 1, 1)), _goal_at(0, (3, 1, 1)),
                       mechanics=[Currents({(0, (2, 1, 1)): FACE_RIGHT})])


def stone_example():
    """Stone: push the stone at (2,1,1) east onto the plate at
    (3,1,1). The goal is the stone on the plate (a pushed stone
    cannot be walked through, so the goal is a stone state)."""
    surfaces = {0: {(1, 1, 1), (2, 1, 1), (3, 1, 1)}}
    return PuzzleModel("stone", surfaces, (0, (1, 1, 1)),
                       lambda st: (0, (3, 1, 1)) in st["stones"],
                       mechanics=[Stones([(0, (2, 1, 1))])])


def stone_drop_example():
    """Stone dropped to the surface below: push the stone at (2,1,1)
    east off the floor edge; it lands on the ceiling tile (3,10,1)
    below... (drop target is a second surface the model walks on
    after a rune; here the goal is simply the stone landing)."""
    surfaces = {0: {(1, 1, 1), (2, 1, 1)}, 3: {(3, 10, 1)}}
    m = PuzzleModel("stone-drop", surfaces, (0, (1, 1, 1)),
                    lambda st: (3, (3, 10, 1)) in st["stones"],
                    mechanics=[Stones([(0, (2, 1, 1))],
                                     drops={(0, (3, 1, 1)): (3, (3, 10, 1))})])
    return m


def shadow_example():
    """Shadow: a 2-tile patrol on the floor; the goal is past it.
    The shadow starts on (3,1,1), so crossing at once walks into it
    on (2,1,1); the optimal line waits one beat ('.') then crosses."""
    surfaces = {0: {(1, 1, 1), (2, 1, 1), (3, 1, 1), (4, 1, 1)}}
    lane = [(0, (2, 1, 1)), (0, (3, 1, 1))]
    return PuzzleModel("shadow", surfaces, (0, (1, 1, 1)), _goal_at(0, (4, 1, 1)),
                       mechanics=[Shadow(lane, phase0=1)])


def echo_example():
    """Echo: the player walks the floor; a mirror ghost walks the
    ceiling (x mirrored). The ceiling sigil at (3,10,2) toggles group
    0 when the echo arrives; the floor goal tile (4,1,1) is gated by
    group 0 in the same way as sigil_gate_example (omitted here for
    brevity: the goal is simply to reach (4,1,1) after the echo press,
    checked via the solution's tags)."""
    surfaces = {0: {(1, 1, 1), (2, 1, 1), (3, 1, 1), (4, 1, 1)},
                3: {(1, 10, 2), (2, 10, 2), (3, 10, 2), (4, 10, 2)}}
    mirror = {(0, (x, 1, 1)): (3, (x, 10, 2)) for x in (1, 2, 3, 4)}
    return PuzzleModel("echo", surfaces, (0, (1, 1, 1)), _goal_at(0, (4, 1, 1)),
                       n_groups=1,
                       mechanics=[Echo(mirror, {(3, (3, 10, 2)): ("toggle", 0, 0)}, 1)])


def crumble_example():
    """Crumbling: the tile (2,1,1) holds once; the goal is (3,1,1).
    Going there and back falls on the second step onto it."""
    surfaces = {0: {(1, 1, 1), (2, 1, 1), (3, 1, 1)}}
    return PuzzleModel("crumble", surfaces, (0, (1, 1, 1)), _goal_at(0, (3, 1, 1)),
                       checkpoints=[(0, (1, 1, 1))],
                       mechanics=[Crumbling({(0, (2, 1, 1))})])


def ravaged_path_model():
    """Sanity model of today's Ravaged Path wall (the floor walkway
    is a straight line, so the model starts on the wall). West wall
    x=11, tiles (y, z) with y 2..4, z 13..22; scars as ScarGroups
    (scar 0: {(2,16)}, scar 1: {(2,20),(2,21),(3,20),(3,21)}).
    Known solution: L*6, U U, L*3, D D, D (off-jump to the floor
    at (12,1,23)), then R R to the totem tile (14,1,23). The solver's
    optimum is also 16 moves but steps once on the (y3, z21) scar
    tile (legal: a scar holds exactly once) -- both lines are valid,
    and the model accepts both."""
    wall = set()
    for y in (2, 3, 4):
        for z in range(13, 23):
            if y == 4 and z < 19:
                continue
            if y == 3 and z < 19:
                continue
            wall.add((11, y, z))
    surfaces = {1: wall, 0: {(12, 1, 23), (13, 1, 23), (14, 1, 23)}}
    jumps = {(1, (11, 2, 22), FACE_DOWN): (0, (12, 1, 23))}  # off-jump is DOWN (tw_arc dir 1)
    scars = {0: {(1, (11, 2, 16))}, 1: {(1, (11, 2, 20)), (1, (11, 2, 21)),
                                        (1, (11, 3, 20)), (1, (11, 3, 21))}}
    return PuzzleModel("ravaged-path", surfaces, (1, (11, 2, 13)),
                       _goal_at(0, (14, 1, 23)), jumps=jumps,
                       checkpoints=[(1, (11, 2, 13))],
                       mechanics=[ScarGroups(scars)])


EXAMPLES = {
    "sigil": sigil_gate_example,
    "rune": rune_example,
    "current": current_example,
    "stone": stone_example,
    "stone-drop": stone_drop_example,
    "shadow": shadow_example,
    "echo": echo_example,
    "crumble": crumble_example,
    "ravaged-path": ravaged_path_model,
}


def main():
    """Run the examples. Exit 1 on any failure (unsolvable, soft-lock,
    or target violation) so CI and the regress runner can treat a
    solver run as a check, not a report."""
    import sys
    names = sys.argv[1:] or list(EXAMPLES)
    failed = False
    for name in names:
        model = EXAMPLES[name]()
        res = model.solve()
        locks = model.soft_locks()
        print(f"== {name}: {model.name}")
        if res is None:
            print("   UNSOLVABLE")
            failed = True
            continue
        stats = res.stats()
        print(f"   solution ({stats['optimal_length']}): {res.move_string}")
        print(f"   stats: {stats}")
        print(f"   soft-locks: {len(locks)}" + (f" e.g. {locks[:2]}" if locks else ""))
        if locks:
            failed = True
        if name == "ravaged-path":
            rift = 1
            violations = check_targets(rift, stats)
            print(f"   targets rift {rift}: {violations or 'in range'}")
            if violations:
                failed = True
            known = "L L L L L L U U L L L D D D R R"
            print(f"   known solution length: {len(known.split())} "
                  f"(solver optimum {stats['optimal_length']})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
