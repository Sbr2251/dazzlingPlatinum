# DW Route 214 puzzle (rift #3, Skarmory) — Phase 1 design

- Rift: `MAP_HEADER_DW_ROUTE_214`, Arc 2 scene 2.18, progress 62 -> 63.
- Difficulty: **4** (revised curve, `PUZZLE_PLAN.md` section 2: Arc 2 tops out at 6/10).
- New mechanic: **rift currents**. Old mechanics combined: **sigils** (one per
  crossing, toggling a block). No runes, no stones, no shadow: the plan caps
  this rift at currents + sigils.
- Status: Phase 1 design. Engine-a's API is
  `include/overlay009/dw_puzzle.h` (commit `623ccce7ee`, header + guide only);
  nothing is implemented here. Phase 2 waits for the lead's merge notice.
- Solver: `tools/distortion_world/route_214_solver.py` (Dijkstra over
  tile steps, with fall transitions). Optimal solution **36 tile steps**
  (35-50 required), **the same 36 under both slide readings** (section 2),
  solvable, soft-lock free including falls, no slide loop.

## 1. Where the puzzle lives

The floor, hops, corridor, east wall and boost frame are Phase 0, unchanged.
The puzzle is on the **ceiling** (the 6-wide strip, x 44-49, z 27-47, y = 10).
The ceiling is split into five chambers by four stone-block walls; each wall
is crossed only by sliding through its current gap. Between walls the player
walks freely. That keeps the puzzle on the existing B4F geometry: no ceiling
widening, no new floor, no model rebuild.

Directions on the ceiling (stock `unk_0205F180.c` tables, `DwPuzzle_DirDelta`):
UP = +z (toward Skarmory), DOWN = -z (back), LEFT = -x, RIGHT = +x.
The doc and the solver both write directions in this pad-relative sense:
`U` = +z, `D` = -z, `L` = -x, `R` = +x.

### 1.1 Floor (schematic, unchanged Phase 0)

```
entry (20,12) -> island -> hop (25,22-23) -> (31,22-23)
  -> hop (32,22-23) -> (38,22-23) -> corridor -> boost frame (44,22-23)
  -> east wall on at (48,22-23) -> climb -> ceiling
```

- Entry (20,12) facing west; the entry scene steps the player out to (17,12).
- The two hops are ground-to-ground jump points (kind 4, dx +-6), unchanged.
- Boost-choice frame at (44,22-23): coord event, script 3, unchanged (section 6).
- The corridor to the wall is (38,22-23) -> (48,22-23), unchanged.

### 1.2 East wall (unchanged Phase 0)

Attr 21 grid, rows y = 1..10 (top row first in the tool dump is y = 10),
columns z = 20..29. `.` = walkable, `#` = blocked.

```
y10  #######...
y9   #######...
y8   #######...
y7   #######...
y6   ####......
y5   ####......
y4   ####......
y3   ........##
y2   ........##
y1   ........##
      z20..29
```

On at (48,22-23) pressing right, climb to (y = 9, z 27-30), press up onto
the ceiling at (49,27). No puzzle on the wall: it is the climb to the maze.

### 1.3 Ceiling (the puzzle)

Rows z = 27..47 (top to bottom), columns x = 44..49 (left to right).
`y = 10` throughout. Symbols:

| symbol | meaning |
|---|---|
| `.` | plain slab, walk normally |
| `#` | stone block, BLOCKED (permanent group, ghost prop, always shown) |
| `v` | current, drifts +z (UP, toward Skarmory) — wall gaps, slide paths |
| `^` | current, drifts -z (DOWN, back north) — return gaps |
| `s` | sigil A: step on, toggles group A |
| `t` | sigil B: step on, toggles group B |
| `A` | group A tile: the W2 forward gap. BLOCKED while A is on, current `v` while A is off |
| `B` | group B tile: the C3 wall gap. BLOCKED while B is on, current `v` while B is off |
| `C` | checkpoint (stops a slide; snapshots groups + sigil states) |

```
     x44 45 46 47 48 49
z27  .....C      C0, entry checkpoint (49,27)
z28  ......
z29  ##v###      W1: forward gap v at (46,29)
z30  ..v...      C1: W1 slide path (46,30) v
z31  .sv...      C1: sigil A at (45,31); slide path (46,31) v
z32  ..C...      C1: checkpoint at (46,32), W1 landing
z33  ^###A#      W2: return ^ at (44,33), forward gap A at (48,33)
z34  ....v.      C2: W2 slide path (48,34) v
z35  .t..v.      C2: sigil B at (45,35); slide path (48,35) v
z36  ....C.      C2: checkpoint at (48,36), W2 landing
z37  v####^      W3: forward v at (44,37), return ^ at (49,37)
z38  v.....      C3: W3 slide path (44,38) v
z39  B#####      C3 wall: group B gap at (44,39), stone blocks x45-49
z40  C.....      C3: checkpoint at (44,40), W3 landing (B off)
z41  ^##v##      W4: return ^ at (44,41), forward v at (47,41)
z42  ...v..      C4: W4 slide path (47,42) v
z43  ...v..      C4: W4 slide path (47,43) v
z44  ...C..      C4: checkpoint at (47,44), W4 landing
z45  ......      goal row: first step onto z >= 45 starts the totem
z46  ......
z47  ......
```

Chambers: C0 z27-28, C1 z30-32, C2 z34-36, C3 z38-40, C4 z42-44.
Walls: W1 z29, W2 z33, W3 z37, W4 z41.

## 2. Currents (the new mechanic)

A current tile has a FACE_* drift direction, shown by an arrow ghost prop.
Stepping on one starts a slide: input is locked, the player moves one tile
per `DW_PUZZLE_SLIDE_FRAMES_PER_TILE` (6) field frames, until:

- the next tile is BLOCKED or the surface edge: the slide stops on the
  current tile (the tile just before the block);
- the next tile is a sigil or a checkpoint: the slide stops there and that
  tile's logic runs;
- the next tile is a current with a different direction: the slide turns
  and continues in the new direction;
- otherwise: see the two readings below.

**Two readings of "off-current".** The engine-a guide says a slide runs
"until blocked ... or off-current", which is ambiguous: it may mean a
slide stops on the first non-current tile (reading A) or keeps sliding
across plain tiles until a block (reading B, ice-style). This design is
valid under **both**, and the solver proves it under both:

- Every **forward** slide path is tiled with currents of one direction
  and ends on a checkpoint, so a forward slide reaches the same
  checkpoint under A and under B. The W1 slide, for example, is
  (46,29) v -> (46,30) v -> (46,31) v -> checkpoint (46,32) under both.
- Every **return** slide lands in the same chamber under both readings;
  only the exact landing tile inside that chamber differs (W2 return:
  (44,32) under A, (44,30) under B; W3 return: (49,36) under A,
  (49,34) under B). Both landings can reach the sigil and the next gap.
  The W4 return slide ends on the checkpoint (44,40) under both.
- The A/B gap tiles (48,33) and (44,39) are currents when their group
  is off, so they are part of their forward slide paths under both.

What a slide is **not**: it is not a walk. The player cannot step
tile-by-tile along a slide path: the first step onto a current commits
them to the whole slide. They choose slides by choosing which current
tile to step onto, from a chamber or from a slide's stopping tile.

## 3. Walls, gaps, returns

Every wall has a forward gap (a `v` current) and, from W2 on, a return gap
(a `^` current). The return gap is what makes the puzzle soft-lock free:

- Forward gap: stepping south onto it slides the player south along the
  current-tiled slide path to the next chamber's checkpoint (or, with
  the gap's group on, to the stop tile just before the closed gap/wall).
- Return gap: stepping north onto it slides the player back to the previous
  chamber. Stepping south onto a return gap slides the player back north,
  so a return gap can never be used to cross forward: walls are one-way
  except through their forward gap.
- A player who crosses a wall without pressing that chamber's sigil can
  always return through the return gap, press the sigil, and slide again.
  No chamber is a dead end: every chamber has a return gap (or, for C1,
  the sigil it needs is inside it) and every slide stop has a walking
  route to a return gap or to a sigil.

## 4. Sigils (the combination)

Two toggle sigils, each in the chamber **before** the wall its block sits
behind:

- **Sigil A** at (45,31) in C1 toggles group A, the W2 forward gap
  (48,33). Initial state: A **on**, so the gap is a stone block. The
  player who tries W2 before pressing A finds the gap closed, walks to
  the sigil (two steps west of the W1 landing), presses it, and the gap
  opens as a `v` current. The gap is a visible stone block while closed:
  the sigil's effect is in the same wall the player is looking at.
- **Sigil B** at (45,35) in C2 toggles group B, the gap (44,39) in the
  C3 wall (z39, otherwise a solid line of stone blocks). Initial state:
  B **on**, so the C3 wall has no gap. A W3 slide with B on stops at
  (44,38), north of the wall; the player cannot walk around the gap,
  because the whole z39 row is blocked except the gap tile itself.
  The player walks east along z38 to the W3 return gap (49,37), slides
  back north to C2, presses B, and slides W3 again — now the gap is a
  `v` current and the slide passes it to the checkpoint (44,40).
  The player who presses B first (four steps from the W2 landing)
  never sees the short stop.

Both sigils play the engine's sigil sound + flash (`gDwPuzzleDebug.flashFrames`).

## 5. Teaching beat

The first slide is the teaching beat, before any sigil, gate, or choice:

1. The player climbs onto the ceiling at (49,27) (checkpoint).
2. C0 is a plain 6 x 2 chamber. The only way south is W1: five of its six
   tiles are stone blocks; the sixth, at (46,29), is an arrow tile.
   The player walks to (46,28) and steps south onto the arrow.
3. The slide carries them south across C1 — (46,30), (46,31) — and stops
   at the checkpoint (46,32), just before W2. No fall, no sigil on the
   path, no choice: one slide, one block, one stop. The lesson is
   "step on an arrow, you slide until a block stops you."
4. C1 then teaches sigils the same way: the closed W2 gap is a visible
   stone block; the sigil is in the same chamber; pressing it opens the gap.

There is no second teaching slide: the W2 slide repeats the lesson with
a gate, and the W3 slide introduces the walled gap + return.

## 6. The non-obvious move

Two moves look wrong and are right:

1. In C1, walk **west** to sigil A (away from the W2 gap at the east of
   the chamber) before crossing. The optimal route does this.
2. After a W3 slide stops short at (44,38) with B on, walk **east** to the
   return gap and go **back north** through W3 — away from Skarmory — to
   press sigil B in C2, then slide W3 again. Going back is the only way
   forward. (The optimal route presses B before crossing, so it never
   needs this; the move is the recovery, and it is also how a player
   discovers what sigil B does.)

## 7. Solution and difficulty stats

Solver: `python3 tools/distortion_world/route_214_solver.py`.
Directions in the solution string are pad presses on the ceiling:
`U` = +z (toward Skarmory), `D` = -z, `L` = -x, `R` = +x; lower-case
letters are slide tiles, upper-case are player steps.

- Optimal solution (tile steps): **36** (required 35-50), under **both**
  slide readings (A and B, section 2). The solver now uses Dijkstra over
  tile steps, not BFS over player inputs, so 36 is the true tile-step
  optimum: no 35-tile route exists, and sigil B is required (the C3
  wall z39 is solid except the B gap, so B cannot be walked around).
  Solution string (23 player steps + 2 waits):
  `LLLUUuuuLDRuRRUuuuLLLDLUUuuuRRRUuuuU`.
  The 2 waits are the fade waits after the two sigil presses (see
  "Fade timing" below): in the real engine the walk to the gap may
  already cover the 33-frame fade, but waiting is always safe, and
  the solver models the wait explicitly.
- Trace (player steps):

| step | press | ends on | note |
|---|---|---|---|
| 0-2 | L L L | (46,27) | walk west across C0 to the W1 arrow column |
| 3-4 | U U | (46,32) C | walk to (46,28), W1 slide (teaching), stops at checkpoint |
| 5-6 | L D | (45,31) s | walk to sigil A, toggle A off (fade pending) |
| 6b | wait | (45,31) | wait for the A fade to settle (gap opens) |
| 7 | R | (46,32) C | step east onto (46,31) `v`, slides south to checkpoint; snapshot now has A off |
| 8-9 | R R | (48,32) | walk to the W2 gap |
| 10 | U | (48,36) C | W2 slide, stops at checkpoint |
| 11-14 | L L L D | (45,35) t | walk to sigil B, toggle B off (fade pending) |
| 14b | wait | (45,35) | wait for the B fade to settle (gap opens) |
| 15-16 | L U | (44,36) | walk to the W3 gap |
| 17 | U | (44,40) C | W3 slide, stops at checkpoint |
| 18-20 | R R R | (47,40) | walk to the W4 gap |
| 21 | U | (47,44) C | W4 slide, stops at checkpoint |
| 22 | U | (47,45) | step south: totem triggers (z >= 45) |

- Solver stats: 2608 reachable states (tile-step Dijkstra, goal terminal,
  fade-pending states + fall transitions included — see sections 4/9);
  **every reachable non-goal state can still reach the goal** (reverse
  BFS from the goal over the same transitions, steps + waits + falls) —
  no soft-lock. No slide loops in any reachable state (the solver raises
  on a loop). Falls in the optimal solution: 0; waits: 2.

**Fade timing.** A sigil toggle does not change its block at once
(engine-a honeycomb rule): turning a group off leaves its tiles solid
for `fadeOutFrames` (default 33 field frames, ~1 s) while its props fade;
turning one on shows its props at once but blocks only after
`fadeInLeadFrames` (default 3). The solver models this with a
fade-pending state and an explicit WAIT ("wait until the fades
settle"); walking/sliding steps do not advance fades in the model,
although in the real engine they take frames too, so the model is
stricter than the engine and any path it finds works in the engine.
In practice the player waits ~1 s after each sigil press (or walks
slowly to the gap); pressing a sigil and sliding through its gap in
under 33 frames would find the gap still closed, which is a wasted
slide, not a soft-lock — the return gaps let the player try again.
Re-entering a checkpoint after a toggle re-snapshots with the new
state (step 7 above re-snapshots C1 with A off).
- Recovery cost (tile steps to goal from a missed-sigil state):
  short stop at (44,38) with B on (checkpoint snapshot still C2):
  **18** — walk east to the W3 return gap, slide back to C2, press B,
  slide W3 again, finish. A W2 gap tried with A on is simply blocked;
  the player is still in C1.

## 8. Puzzle table (for Phase 2, `dw_puzzle_route_214.c`)

One `DwPuzzleTable` (`gDwPuzzleRoute214Table`), `MAP_HEADER_DW_ROUTE_214`,
progress 62 -> 63 (min = max = 62: the whole visit runs at progress
62; the calm at 63 ends the visit, so the table need not be active at 63).

| module | entries |
|---|---|
| Groups (3) | 0: permanent walls, 22 tiles, ghost group 1, onState BLOCKED, offState SOLID, initialOn 1, never toggled. 1: group A, 1 tile (48,33), ghost group 2, onState BLOCKED, offState SOLID, initialOn 1. 2: group B, 1 tile (44,39), ghost group 3, onState BLOCKED, offState SOLID, initialOn 1 |
| Sigils (2) | (45,31) TOGGLE group 1 (A); (45,35) TOGGLE group 2 (B) |
| Runes (0) | none |
| Currents (15) | wall gaps: (46,29) U; (48,33) U (group A tile, drifts when A is off); (44,33) D; (44,37) U; (49,37) D; (47,41) U; (44,41) D. Slide paths: (46,30) U; (46,31) U; (48,34) U; (48,35) U; (44,38) U; (44,39) U (group B tile, drifts when B is off); (47,42) U; (47,43) U |
| Checkpoints (6) | map entry (20,1,12); ceiling entry (49,10,27); (46,10,32); (48,10,36); (44,10,40); (47,10,44). Checkpoint 0 is the map entry, per the engine guide |
| Explicit tiles (0) | none: all blockers are group tiles, all other ceiling tiles are stock walkable |
| fallScriptId / fallVar | the map's fall script + `VAR_MAP_LOCAL_3`, Eterna-honeycomb pattern: the rift's init frame table gets `InitScriptGoToIfEqual <fallVar>, 1, <fallScriptId>` and the fall script clears `<fallVar>` first. Route 214 has no fall script today; Phase 2 adds one (a fall restores the player and puzzle state to the last checkpoint, section 9) |

Coordinates are (x, y, z) as the ov9 step hook sees them: ceiling y = 10,
floor y = 1. Group A/B tiles are both group tiles and currents: when the
group is on the tile is BLOCKED (the current never fires); when off it
is a current tile. If the engine does not allow a tile to be both, Phase 2
must split it (gap tile = plain when the group is off, with the current on
the tile south of it) and re-run the solver with that split.

### Ghost props (tw_arc, `route_214.json`)

Total **39** props. Budget: the plan's "B4F has the most props" is
contradicted by the data — `twarc.py dump` shows stock B3F with 49 props
and B4F with 24 — so the cap used here is the stock DW maximum, 49.
39 is inside that cap. (Flagged for the lead in section 12: if the lead
holds B4F's 24 as this map's cap, the fallback is to draw the permanent
walls as attr-blocked slab edges, like stock B4F's own blocked ceiling
tiles, and keep only the 17 moving/sigil/arrow props.)

| ghost group | props | what |
|---|---|---|
| 1 (permanent walls) | 22 | one stone block per `#` wall tile |
| 2 (A) | 1 | stone block on (48,33) while A is on |
| 3 (B) | 1 | stone block on (44,39) while B is on |
| 4 (arrows) | 13 | one arrow per current tile except the A/B gap tiles, which show only their block while closed and no arrow while open (the arrow on the preceding slide tile points the way) |
| 5 (sigils) | 2 | one glyph decal per sigil tile |

The permanent blocks are the stock B4F rock-maze blocks (the same prop
kinds B4F already uses), drawn where the attr grid says BLOCKED.

**Inherited triggers and default visibility:** `route_214.json` today
carries B4F's 47 ghost triggers with zero props ("their triggers stay
and toggle nothing"). Phase 2 must set `ghost_triggers` to `[]` in the
Route 214 spec, so none of the inherited triggers can touch groups 1-5,
and must set `ghost_default_visible` to `0x3E` (groups 1-5 visible at
map load). The inherited `0xF55` mask leaves groups 1, 3, 4 and 5
hidden — without the new mask the walls, the B block, the arrows and
the sigils would start invisible.

### Collision vs drawn (fix2-lost rule)

- Every walkable ceiling tile is slab (already drawn) or a group tile
  whose prop is shown while it holds (honeycomb rule: the engine keeps
  props and walkability in step).
- Every BLOCKED tile is a drawn stone block (a ghost prop above), never
  an invisible wall: the 22 permanent blocks + A + B are all props.
- No VOID tiles on the ceiling, so no fall trigger sits on drawn ground.
- The attr grid for the ceiling (attr 22) is the only grid that changes:
  the rest of the ceiling strip stays as Phase 0. Phase 2 runs the
  collision-vs-drawn audit (the fix2-lost harness) over the final JSON.

## 9. Falls, checkpoints, and the hint

**Reset policy.** "Fall -> reset the strip" (`PUZZLE_PLAN.md` row #3)
means: a fall restores the player **and** the puzzle to the last
checkpoint's snapshot — the strip as it was when that checkpoint was
reached — not to the initial state, and not to the state at the fall.
A fall before any checkpoint (or a fall the step hook never sees, e.g.
an unmarked coord-event lip) resets to the initial state, per the
engine-a guide. The solver models this exactly: its state carries the
last checkpoint and its snapshot groups, and a fall transition from
any state returns to that checkpoint with those groups. The soft-lock
proof (section 7) includes those fall transitions.

Concretely: a fall in C2 after pressing B returns the player to the
C2 checkpoint (48,36) with **B on** — the checkpoint was reached
before B was pressed, so its snapshot still has B on, and B must be
pressed again. (An earlier draft had this backwards.) A fall in C1
after pressing A but before re-entering the (46,32) checkpoint also
returns with A on. But if the player re-enters a checkpoint after a
toggle — as step 7 of the solution re-enters (46,32) with A off — the
snapshot updates, and a later fall returns with A off.

**Hint after two falls.** Cyrus's hint plays on the respawn after the
**second** fall in this rift. It is wired through the fall script's
two flags (the script, not `gDwPuzzleDebug`, is what scripts can read):
ASCII, short lines, in character. It names the two ideas the player
needs: slides stop at blocks, and the sigil moves the block.

```
Cyrus: The drift carries you
until a stone block stops it.
The sigil moves the block.
```

- First fall in the rift: the fall script sets `FLAG_DW_214_A`
  (fell once), no hint.
- Second fall: if `FLAG_DW_214_A` is set and `FLAG_DW_214_B` (hint
  shown) is not, the fall script shows the hint above on respawn, then
  sets `FLAG_DW_214_B`. Later falls show no hint.
- The hint is a design requirement on Phase 2: the fall script must be
  able to show this text on respawn. Fallback if the respawn path
  cannot show text: Cyrus says the same lines when talked to after two
  falls (he stands at the frame; the talk script checks the two flags).
- A fall on this map is a fall anywhere in the rift (floor hops, wall,
  ceiling edge): the engine restores the player and the puzzle to the
  last checkpoint on any fall warp. **Scope:** the solver's fall proof
  covers falls from any ceiling state. Falls *before* the ceiling are
  not in the solver: no sigil is reachable before the ceiling, so the
  puzzle state there is always the initial one, and a fall there
  returns the player to the map entry with initial groups — equivalent
  to a fresh entry. Phase 2 must still headless-test one floor/wall
  fall. **Phase 2 must give this map a concrete fall path to prove
  against** (today `events_dw_route_214.json` has only the boost-choice
  event): either mark the existing floor/wall fall lips as VOID in the
  puzzle table so the engine's fall path runs, or trigger the fall warp
  from the harness and prove the checkpoint restore. The solver's fall
  transition covers both: it does not depend on which tile caused the
  fall.

## 10. Boost choice, re-entry, contract (unchanged)

- Boost choice: the frame scene at (44,22-23) on the floor corridor,
  before the wall, is unchanged. Yes (Cyrus pulls the shard) sets
  `FLAG_ARC2_RIFTB_B` and `VAR_ARC2_CHOICES` bit 2 (AddVar 4); No leaves
  the totem boosted. The totem script reads the same flag, unchanged.
  The puzzle does not read the boost choice: both choices play the same
  maze, and the solver proof holds for both (the choice changes only the
  totem's stats).
- Re-entry: Cyrus's entry line skips once he stands at the frame
  (`FLAG_ARC2_RIFTB_A` gate in `DWRoute214_EntryScene`), unchanged.
  After a blackout the choice stands, the frame stays as left, the
  puzzle resets to its initial state on a fresh entry (engine rule),
  and a fall mid-maze restores the last checkpoint.
- Contract: entry (20,12) facing west, exit warp
  `MAP_HEADER_ROUTE_214, 0, 726, 665, DIR_SOUTH`, calm
  `VAR_ARC2_PROGRESS` 63 + `FLAG_TOTEM_SKARMORY_DEFEATED`, unchanged.
  The totem triggers at z >= 45 on the ceiling (`Arc2DwB4F_HandleCeilingEnd`),
  unchanged; the maze ends the moment the player steps onto z = 45.

## 11. Phase 2 implementation checklist (not started)

1. `src/overlay009/dw_puzzle_route_214.c`: the table in section 8.
2. `tools/distortion_world/route_214.json`: ceiling attr 22 rows from
   section 1.3 (`#` = BLOCKED, `.` = walkable; group tiles are BLOCKED
   in the stock grid and opened by the engine), the 39 ghost props
   (groups 1-5), `ghost_triggers` set to `[]` (clearing B4F's
   inherited 47), `ghost_default_visible` set to `0x3E` (groups 1-5
   visible at load), no jump/camera changes.
   Rebuild with `twarc.py build` and `twarc.py check`.
3. `build_rift_b_maps.py`: no change (the floor is unchanged). If the
   ceiling attr edit needs a land-data change, do it there and keep
   `route_213.json` / `lost_tower.json` builds green.
4. `scripts_dw_route_214.s` + `events_dw_route_214.json`: the fall
   script (section 8), the hint wiring (section 9), and the fall-var
   init-table line. No change to the entry, frame, or totem scripts.
5. `generated/vars_flags.txt`: rename `FLAG_UNK_0x0A10` ->
   `FLAG_DW_214_A`, `FLAG_UNK_0x0A11` -> `FLAG_DW_214_B` (registry
   block `FLAG_DW_214_A..H`, 0x0A10-0x0A17). `FLAG_DW_214_C..H` unused.
6. Headless proof (Phase 2): solver replay from entry to the totem for
   both boost choices; a fall at each stage (checkpoint restore);
   re-entry after a blackout (choice stands, puzzle initial);
   collision-vs-drawn audit; regression on the other rifts;
   `make release`.
7. Codex reviews at first-playable and at final, per `COMMON.md`.

## 12. Open questions / assumptions (for engine-a + lead)

1. **Slide semantics (no longer load-bearing).** The guide's "off-current"
   is ambiguous (reading A: stop on the first non-current tile; reading B:
   slide across plain tiles until a block). Forward slides are
   current-tiled and end on checkpoints, so they reach the same
   checkpoint under both readings; return slides land in the same
   chamber under both. The solver proves the 36-tile optimum under
   both readings. No engine change needed; if the engine implements a
   third reading (e.g. a slide ends *before* the first non-current
   tile), re-run the solver with that reading before Phase 2.
2. **A tile that is both a group tile and a current** (the A/B gaps,
   section 8). If the engine forbids the overlap, split each gap
   (gap tile = plain when the group is off, with the current on the
   tile south of it) and re-run the solver.
3. **Hint on respawn**: the fall script shows the hint itself (section
   9); no glue hook or `gDwPuzzleDebug` access is needed. If the fall
   script cannot show text on the respawn path, use the talk-script
   fallback in section 9.
4. **Ceiling prop budget**: 39 props, inside the stock DW maximum 49
   (B3F). The plan's "B4F has the most props" is contradicted by the
   `twarc.py dump` data (B3F 49, B4F 24); the lead is asked to confirm
   the cap is the stock maximum. If the lead holds B4F's 24 as this
   map's cap, the fallback in section 8 draws the permanent walls as
   attr-blocked slab edges and keeps only 17 props.
5. **Concrete fall path**: Phase 2 must give this map a fall path to
   prove against (section 9): mark real fall lips VOID in the table,
   or trigger the fall warp from the harness.
6. **Fade/snapshot assumptions** (solver section, modelled): checkpoint
   snapshots store *logical* group states, and a fall settles pending
   fades (respawn warp outlasts any fade). If the engine snapshots
   effective states instead, the only change is the C2-after-B example
   in section 9 (a fall after pressing B but before re-entering the
   checkpoint would return with B off); confirm against the engine-a
   implementation when it lands.
