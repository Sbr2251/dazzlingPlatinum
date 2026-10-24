# DW Route 214 puzzle (rift #3, Skarmory) — Phase 1 design

- Rift: `MAP_HEADER_DW_ROUTE_214`, Arc 2 scene 2.18, progress 62 -> 63.
- Difficulty: **4** (revised curve, `PUZZLE_PLAN.md` section 2: Arc 2 tops out at 6/10).
- New mechanic: **rift currents**. Old mechanics combined: **sigils** (one per
  crossing, toggling a block). No runes, no stones, no shadow: the plan caps
  this rift at currents + sigils.
- Status: Phase 1 design. Engine-a's API is
  `include/overlay009/dw_puzzle.h` (commit `623ccce7ee`, header + guide only);
  nothing is implemented here. Phase 2 waits for the lead's merge notice.
- Solver: `tools/distortion_world/route_214_solver.py` (standalone BFS with
  engine-a semantics). Optimal solution **36 tile steps** (35-50 required),
  solvable, soft-lock free, no slide loop.

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
| `v` | current, drifts +z (UP, toward Skarmory) |
| `^` | current, drifts -z (DOWN, back north) |
| `s` | sigil A: step on, toggles group A |
| `t` | sigil B: step on, toggles group B |
| `A` | group A tile: the W2 forward gap. BLOCKED while A is on, current `v` while A is off |
| `B` | group B tile: mid-chamber stop-block in C3. BLOCKED while B is on, plain while B is off |
| `C` | checkpoint (stops a slide; snapshots groups + sigil states) |

```
     x44 45 46 47 48 49
z27  .....C      C0, entry checkpoint (49,27)
z28  ......
z29  ##v###      W1: forward gap v at (46,29)
z30  ......      C1
z31  .s....      C1: sigil A at (45,31)
z32  ..C...      C1: checkpoint at (46,32), W1 landing
z33  ^###A#      W2: return ^ at (44,33), forward gap A at (48,33)
z34  ......      C2
z35  .t....      C2: sigil B at (45,35)
z36  ....C.      C2: checkpoint at (48,36), W2 landing
z37  v####^      W3: forward v at (44,37), return ^ at (49,37)
z38  ......      C3
z39  B.....      C3: group B stop-block at (44,39)
z40  C.....      C3: checkpoint at (44,40), W3 landing (B off)
z41  ^##v##      W4: return ^ at (44,41), forward v at (47,41)
z42  ......      C4
z43  ......      C4
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
- otherwise (plain tile): the slide keeps going in the same direction,
  ice-style, until a block stops it.

This is the "slide until you hit a block" reading of the plan and of
`dw_puzzle.h` / the engine-a guide. It is the one load-bearing assumption
of this design; see section 8.

What a slide is **not**: it is not a walk. The player cannot step
tile-by-tile along a slide path: the first step onto a current commits
them to the whole slide. They choose slides by choosing which current
tile to step onto, from a chamber or from a slide's stopping tile.

## 3. Walls, gaps, returns

Every wall has a forward gap (a `v` current) and, from W2 on, a return gap
(a `^` current). The return gap is what makes the puzzle soft-lock free:

- Forward gap: stepping south onto it slides the player south through the
  next chamber to the next wall (or to a stop-block).
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
- **Sigil B** at (45,35) in C2 toggles group B, the stop-block (44,39)
  in C3. Initial state: B **on**. A W3 slide with B on stops short at
  (44,38); a W3 slide with B off passes (44,39) and stops at the
  checkpoint (44,40). The player who crosses W3 before pressing B lands
  short, walks east to the W3 return gap (49,37), slides back north to
  C2, presses B, and slides W3 again. The player who presses B first
  (it is four steps from the W2 landing) never sees the short stop.

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
a gate, and the W3 slide introduces the stop-block + return.

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

- Optimal solution (tile steps): **36** (required 35-50).
  `ULLLUuuuDLURRRUuuuDLLLULUuuuRRRUuuuU` (24 player steps).
- Trace (player steps; `->` is the tile the step/slide ends on):

| step | press | ends on | note |
|---|---|---|---|
| 0-3 | U L L L | (46,28) | walk across C0 to the W1 arrow column |
| 4 | U | (46,32) C | W1 slide (teaching), stops at checkpoint |
| 5-6 | D L | (45,31) s | walk to sigil A, toggle A off (W2 gap opens) |
| 7-10 | U R R R | (48,32) | walk to the W2 gap |
| 11 | U | (48,36) C | W2 slide, stops at checkpoint |
| 12-15 | D L L L | (45,35) t | walk to sigil B, toggle B off (C3 stop-block clears) |
| 16-18 | U L U | (44,40) C | walk to W3 gap, W3 slide, stops at checkpoint |
| 19-21 | R R R | (47,40) | walk to the W4 gap |
| 22 | U | (47,44) C | W4 slide, stops at checkpoint |
| 23 | U | (47,45) | step south: totem triggers (z >= 45) |

- Solver stats: 203 reachable states (player steps, goal terminal);
  **every reachable non-goal state can still reach the goal** (reverse
  BFS from the goal over the same transitions) — no soft-lock.
  No slide loops in any reachable state (the solver raises on a loop).
  Longest slide: 3 tiles past the entry step. Average out-degree 3.21.
- Recovery costs (player steps to goal from a missed-sigil state):
  short stop at (44,38) with B on: 7; W2 gap tried with A on: the gap
  is simply blocked, the player is still in C1. Worst reachable state
  is 24 player steps from the goal — nothing strands the player.

## 8. Puzzle table (for Phase 2, `dw_puzzle_route_214.c`)

One `DwPuzzleTable` (`gDwPuzzleRoute214Table`), `MAP_HEADER_DW_ROUTE_214`,
progress 62 -> 63 (min = max = 62: the whole visit runs at progress
62; the calm at 63 ends the visit, so the table need not be active at 63).

| module | entries |
|---|---|
| Groups (3) | 0: permanent walls, 17 tiles, ghost group P, onState BLOCKED, offState SOLID, initialOn 1, never toggled. 1: group A, 1 tile (48,33), ghost group A, onState BLOCKED, offState SOLID, initialOn 1. 2: group B, 1 tile (44,39), ghost group B, onState BLOCKED, offState SOLID, initialOn 1 |
| Sigils (2) | (45,31) TOGGLE group 1 (A); (45,35) TOGGLE group 2 (B) |
| Runes (0) | none |
| Currents (7) | (46,29) U; (48,33) U (group A tile, drifts when A is off); (44,33) D; (44,37) U; (49,37) D; (47,41) U; (44,41) D |
| Checkpoints (6) | map entry (20,1,12); ceiling entry (49,10,27); (46,10,32); (48,10,36); (44,10,40); (47,10,44). Checkpoint 0 is the map entry, per the engine guide |
| Explicit tiles (0) | none: all blockers are group tiles, all other ceiling tiles are stock walkable |
| fallScriptId / fallVar | the map's fall script + `VAR_MAP_LOCAL_3`, Eterna-honeycomb pattern: the rift's init frame table gets `InitScriptGoToIfEqual <fallVar>, 1, <fallScriptId>` and the fall script clears `<fallVar>` first. Route 214 has no fall script today; Phase 2 adds one (the fall warp already exists on the floor/wall path: a fall restores the player and puzzle state to the last checkpoint) |

Coordinates are (x, y, z) as the ov9 step hook sees them: ceiling y = 10,
floor y = 1. Group A tile (48,33) is both a group tile and a current:
when A is on it is BLOCKED (the current never fires); when A is off it
is a current tile. If the engine does not allow a tile to be both, Phase 2
must split it (gap tile = plain when A is off, with the current on the
tile south of it) and re-run the solver with that split.

### Ghost props (tw_arc, `route_214.json`)

Total 28 props, inside the stock DW budget (stock B3F has 49, B4F 24):

| group | props | what |
|---|---|---|
| P (permanent walls) | 17 | one stone block per `#` wall tile |
| A | 1 | stone block on (48,33) while A is on |
| B | 1 | stone block on (44,39) while B is on |
| arrows | 7 | one arrow per current tile, pointing in its drift direction |
| sigils | 2 | one glyph decal per sigil tile |

The permanent blocks are the stock B4F rock-maze blocks (the same prop
kinds B4F already uses), drawn where the attr grid says BLOCKED.

### Collision vs drawn (fix2-lost rule)

- Every walkable ceiling tile is slab (already drawn) or a group tile
  whose prop is shown while it holds (honeycomb rule: the engine keeps
  props and walkability in step).
- Every BLOCKED tile is a drawn stone block (a ghost prop above), never
  an invisible wall: the 17 permanent blocks + A + B are all props.
- No VOID tiles on the ceiling, so no fall trigger sits on drawn ground.
- The attr grid for the ceiling (attr 22) is the only grid that changes:
  the rest of the ceiling strip stays as Phase 0. Phase 2 runs the
  collision-vs-drawn audit (the fix2-lost harness) over the final JSON.

## 9. Hint after two falls

Cyrus's hint plays on the respawn after the **second** fall in this rift
(the fall count is `gDwPuzzleDebug.fallCount`; the two flags below make
it a script-visible state machine). ASCII, short lines, in character.
It names the two ideas the player needs: slides stop at blocks, and
the sigil moves the block.

```
Cyrus: The drift carries you
until a stone block stops it.
The sigil moves the block.
```

- First fall in the rift: set `FLAG_DW_214_A` (fell once), no hint.
- Second fall: if `FLAG_DW_214_A` is set and `FLAG_DW_214_B` (hint
  shown) is not, show the hint above on respawn, then set
  `FLAG_DW_214_B`. Later falls show no hint.
- The hint is a design requirement on Phase 2: the glue that runs the
  fall respawn must be able to start this script when the fall count
  reaches 2. If engine-a's glue cannot start a script on respawn, the
  fallback is: Cyrus says the same lines when talked to after two falls
  (he stands at the frame; the talk script checks the two flags).
- Note: a fall on this map is a fall anywhere in the rift (floor hops,
  wall, ceiling edge): the engine restores the player and the puzzle to
  the last checkpoint on any fall warp, so a fall always costs the
  progress since the last checkpoint, and the puzzle state at the
  checkpoint (not the state at the fall) is restored.

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
   in the stock grid and opened by the engine), the 28 ghost props
   (groups P / A / B / arrows / sigils), no jump/camera changes.
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

1. **Slide semantics (load-bearing).** This design assumes a slide
   continues across plain tiles until a block, a sigil, a checkpoint,
   or a turning current — "slide until you hit a block", as the plan
   states. If engine-a instead ends a slide on the first non-current
   tile, this maze does not work (every slide would stop after one
   tile) and the design must be redone with current-tiled slide paths.
   Confirm against the engine-a implementation when it lands; the
   solver encodes the assumed semantics and must be re-run against any
   change.
2. **A tile that is both a group tile and a current** (the W2 gap,
   section 8). If the engine forbids the overlap, split it and re-run
   the solver.
3. **Hint on respawn**: needs a glue hook that can start a script when
   `fallCount` reaches 2 (section 9 fallback: Cyrus's talk script).
4. **Ceiling prop budget**: 28 props is inside the stock maximum (49),
   slightly above B4F's own 24. If the lead holds B4F's 24 as the cap
   for this map, drop the 2 sigil glyph props (draw sigils as floor
   decals instead) and merge the arrow props into the wall group where
   possible.
