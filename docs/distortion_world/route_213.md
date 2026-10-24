# DW Route 213, the Drowned Lake — puzzle design (rift #4)

Owner: workstream `rift-213`. Phase 1 design (the engines are not merged yet).
Plan: `docs/distortion_world/PUZZLE_PLAN.md` section 2, revised curve
(2026-10-23): Arc 2 tops out at 6/10. This rift is **difficulty 5**,
**45-65 steps across two surfaces**, with a reset sigil.

* Map: `MAP_HEADER_DW_ROUTE_213`, Arc 2 scene 2.21, progress 83 -> 84,
  Lapras totem behind the puzzle.
* New mechanic: **rift stones** (engine-b). Combined with **currents**
  (rift #3) and **gravity runes** (rift #2, used only to move between
  the two surfaces — three rune pairs, nothing else).
* Solver: `tools/distortion_world/route_213_solver.py` (standalone
  Dijkstra over the puzzle model, with the engine-a semantics).
  Optimal solution **45 steps**, in range. All 266 reachable states
  reach the totem: soft-lock free.
* Engine-a API: `include/overlay009/dw_puzzle.h` (commit 623ccce7ee on
  `dw/engine-a`). Stones use the published actor-block mechanism
  (`DwPuzzle_SetActorBlock`): a stone makes its tile BLOCKED. This
  design was revised in Codex review round 1 to stay inside that API
  (see "Two ideas" and "Open questions for engine-b").
* Flag block: `FLAG_DW_213_A..H` (0x0A18-0x0A1F) is assigned to this
  workstream in `docs/arc2/registry.md` on `dwpuzzles`. The Phase 1
  design uses **none** of them; if Phase 2 needs a persistent flag
  (e.g. for the hint), it takes `FLAG_DW_213_A` first and renames the
  matching `FLAG_UNK_0x0A18` line in `generated/vars_flags.txt`.

## The two ideas

1. **Drop a stone through a gap to plug a current.** A stone pushed on
   the ceiling into an open gap falls to the floor below and lands as
   a BLOCKED actor block at the end of a current chain. The current
   slides the player to the stone and stops before it. The gap looks
   like losing the stone; it is the solution. (Non-obvious move,
   required from rift 3 on.) The player never stands on a dropped
   stone — they walk around it, from the slide-stop tile to the
   rune-up.
2. **Currents.** Each floor detour is a current chain (two or three
   tiles) that slides the player to the dropped stone. Without the
   stone the slide runs onto open VOID and the player falls.

Everything else is walking. Three stones, three gaps, three floor
detours, seven current tiles (three chains). No sigils except the two
reset sigils. No new persistent flags.

## Geometry

The puzzle starts at the ceiling entry — the jump landing at the top
of the east wall, (49, 27), with the first checkpoint (49, 28) one
step south of it — and ends at the totem trigger on the island (any ceiling
tile with z >= 45). The floor approach (entry (20, 12), the two hops,
the jetty, the wall climb) is plain travel, not puzzle, and is not
counted in the 45 steps. The ceiling causeway is the stock serpentine
from `tools/distortion_world/route_213.json`; the floor detours are
sunken reef shelves (see "Collision vs drawn").

Coordinates: DW world tiles (x, z); ceiling y = 10, floor y = 1, as
the ov9 step hook sees them. `C` = ceiling, `F` = floor.

### Ceiling (y = 10)

`#` = BLOCKED (water / off-causeway), `.` = stock causeway, `V` = VOID
gap (the drop chute), `S` = stone spawn, `r` = rune-down alcove,
`R` = reset-sigil alcove, `P` = checkpoint.

```
z\x  44 45 46 47 48 49
25   #  #  #  #  #  #
26   #  #  #  #  #  #
27   #  #  #  #  #  .   <- jump landing (49,27)
28   #  #  #  #  #  P   <- CP1 at (49,28)
29   #  R  #  #  #  .   <- R=(45,29) reset 1 (before stone 1)
30   P  .  .  .  .  .   <- CP2 at (44,30)
31   S  #  #  #  #  .   <- stone 1 spawns on the path (44,31)
32   .  #  #  #  #  .   <- (45,32) is water: no shelf, no shortcut
33   .  r  #  #  #  .   <- r=(45,33) rune down 1
34   V  #  #  #  #  #   <- gap 1 (44,34)
35   .  #  #  #  #  #   <- (44,35) is the return tile past gap 1
36   .  .  .  .  P  .   <- CP3 at (48,36)
37   #  #  #  #  R  S   <- R=(48,37) reset 2 (before stone 2); stone 2
38   #  #  #  #  #  .   <- (48,38) is water: no shelf, no shortcut
39   #  #  #  #  r  .   <- r=(48,39) rune down 2
40   #  #  #  #  #  V   <- gap 2 (49,40)
41   #  #  #  #  #  .   <- (49,41) is the rune-up landing, NOT a checkpoint
42   .  .  .  V  S  P   <- gap 3 (47,42), stone 3 (48,42), CP4 at (49,42)
43   #  #  .  .  r  #   <- r=(48,43) rune down 3; (47,43) spur
44   #  .  .  .  .  #   <- island (45-48, 44-47)
45   #  .  .  T  .  #   <- T = totem trigger (47,45)
46   #  .  .  .  .  #
47   #  .  .  .  .  #
```

The reset sigils sit **before** their stage's stone, reachable from
the pre-stage path only. This is deliberate (found in review): a
reset sigil reachable *after* a push lets the player undo the push
after walking past the stone — stepping on it returns the stone to
spawn while the player stays past it, which skips stone 1 entirely.
Returning to a pre-stage reset passes a checkpoint, which snapshots
the pushed stones first, so the reset cannot undo a completed push.
Rows 32 and 38 are water on purpose: a shelf there would be another
shortcut around the stones.

### Floor (y = 1)

`#` = BLOCKED (stock lakebed), `.` = reef shelf (SOLID override),
`V` = VOID until a stone lands on it (as a BLOCKED actor),
`<` = current sliding west, `v` = current sliding south,
`>` = current sliding east, `^` = current sliding north,
`r` = rune-up tile, `x` = rune-down landing.

```
Stage 1 (under gap 1), x 43-47, z 32-33:
  z32:  #  #  .  .  .      <- snake west: (47,32),(46,32),(45,32)
  z33:  r  v  <  #  x      <- x=(47,33) landing; currents (45,33) W, (44,33) S;
                              r=(43,33) rune-up -> ceiling (44,35)
  The slide: (45,33) -> (44,33) -> stopped by stone 1 at (44,34).
  Then west to the rune-up. (45,34)/(45,35) are deliberately NOT
  shelves: a shelf there would let the player walk around the
  current and skip stone 1.

Stage 2 (under gap 2), x 47-49, z 34-41:
  z34:  #  #  x            <- landing (49,34), walk south
  z35:  #  #  .
  z36:  #  #  .
  z37:  #  #  v            <- currents (49,37),(49,38),(49,39) S
  z38:  #  #  v
  z39:  r  .  v            <- walk west (48,39), rune-up (47,39) -> ceiling (49,41)
  z40:  #  #  V            <- stone 2 lands at (49,40)
  The slide: (49,37) -> (49,38) -> (49,39) -> stopped by stone 2.

Stage 3 (under gap 3), x 43-48, z 42-43:
  z42:  #  #  #  #  V  #   <- stone 3 lands at (47,42)
  z43:  x  .  .  >  ^  r   <- x=(43,43) landing; currents (46,43) E, (47,43) N;
                              r=(48,43) rune-up -> ceiling (47,43)
  The slide: (46,43) -> (47,43) -> stopped by stone 3 at (47,42).
  Then east to the rune-up.
```

The three floor detours are disjoint: no floor tile of one detour is
adjacent to a floor tile of another, except at rune tiles, which
teleport on entry — so one detour can never leak into another (the
solver checks this: the optimal solution does not shortcut any stage).

## Teaching beat

Stage 1 teaches stones and currents together, with the safe order
forced by the layout:

* Stone 1 spawns **on the path** at (44, 31). The only way on is to
  push it: south along leg C to (44, 33), then south into gap 1. The
  player is already pushing before they have to think about it.
* The rune-down alcove (45, 33) is one step east of (44, 33). The
  player rides down and finds the floor detour: a snake to the
  current, a slide that stops at stone 1, a step west to the rune-up.
* A fall in stage 1 is stepping onto the ceiling gap (44, 34) after
  dropping (walking south from (44, 33) instead of east to the rune).
  It returns the player to CP2 (44, 30) with the stones as they were
  at CP2: stone 1 back on the ceiling. Trying a wrong step is cheap,
  and the retry is short.

Stage 2 repeats the drop, with a three-tile slide. Stage 3 repeats it
with a two-tile slide that turns a corner, on the way to the island.

## Solution (45 steps, from the solver)

Counting: one tile move (walk, push, slide step) = 1 step; a rune
surface change = 0 steps. `C`/`F` = surface after the move.

| # | Move | # | Move |
|---|---|---|---|
| 1-3 | C (49,27) -> (49,30) | 28 | C (49,39) -> rune (48,39) -> F (49,34) |
| 4-8 | C (49,30) -> (44,30) [CP2] | 29-30 | F (49,34) -> (49,36) |
| 9 | C (44,30) -> (44,31), push stone 1 | 31 | F (49,36) -> slide to (49,37) (current) |
| 10 | C (44,31) -> (44,32), push stone 1 | 32 | F (49,37) -> slide to (49,38) (current) |
| 11 | C (44,32) -> (44,33), drop stone 1 into gap 1 | 33 | F (49,38) -> slide to (49,39), stopped by stone 2 |
| 12 | C (44,33) -> rune (45,33) -> F (47,33) | 34 | F (49,39) -> (48,39) |
| 13-15 | F (47,33) -> (45,32) (snake west) | 35 | F (48,39) -> rune (47,39) -> C (49,41) |
| 16 | F (45,32) -> slide to (45,33) (current) | 36 | C (49,41) -> (49,42) [CP4] |
| 17 | F (45,33) -> slide to (44,33), stopped by stone 1 | 37 | C (49,42) -> (48,42), push stone 3 into gap 3 |
| 18 | F (44,33) -> rune (43,33) -> C (44,35) | 38 | C (48,42) -> rune (48,43) -> F (43,43) |
| 19-24 | C (44,35) -> (49,36), via CP3 (48,36) | 39-40 | F (43,43) -> (45,43) |
| 25 | C (49,36) -> (49,37), push stone 2 | 41 | F (45,43) -> slide to (46,43) (current) |
| 26 | C (49,37) -> (49,38), push stone 2 | 42 | F (46,43) -> slide to (47,43), stopped by stone 3 |
| 27 | C (49,38) -> (49,39), drop stone 2 into gap 2 | 43 | F (47,43) -> rune (48,43) -> C (47,43) |
| | | 44-45 | C (47,43) -> (47,45), totem |

Checkpoint snapshots: each checkpoint is stepped on **before** its
stage's stone is pushed, so the snapshot is always a clean state.
No checkpoint is a rune landing: every checkpoint is reached by
walking (the normal step hook), because engine-a's rune starts a
jump task and does not promise a step-hook call at its destination (stones at spawn, or
dropped stones from earlier stages, which are fixed on the floor as
actor blocks). A fall therefore never snapshots a bad stone position.
The reset sigils (stage 1: (45, 29); stage 2: (48, 37)) restore the
same snapshot without moving the player.

## Cyrus's hint (after two falls)

Text id `DWRoute213_Text_CyrusPuzzleHint`, new in
`res/text/dw_route_213.json` in Phase 2. ASCII, 197 px boxes, short
lines in character. Trigger: the second fall (the engine's
`gDwPuzzleDebug.fallCount` reaches 2; Phase 2 wires it to a one-shot
script, map-local `VAR_MAP_LOCAL_2` so it survives neither a blackout
nor a re-entry — it re-fires if the player falls twice again, which
is the behaviour wanted).

```
Cyrus: Push the stone into
the gap. It falls below.
A stone stops the current.
```

Line lengths: 26 / 22 / 26 characters, inside the box width used by
the existing Route 213 text (max 31).

## Checkpoints, falls, reset

| Checkpoint | Tile | Snapshot |
|---|---|---|
| CP0 (table index 0) | (20, 1, 12), floor entry | stones at spawn |
| CP1 | (49, 10, 28), first walked ceiling tile | stones at spawn |
| CP2 | (44, 10, 30) | stones at spawn |
| CP3 | (48, 10, 36) | stone 1 on floor (44, 34); stones 2, 3 at spawn |
| CP4 | (49, 10, 42) | stones 1, 2 on floor; stone 3 at spawn |

(The solver numbers the puzzle checkpoints 0-3; the table adds the
rift-entry checkpoint at index 0.)

Fall cost: return to the last checkpoint, stones to its snapshot. No
stone is ever lost: the causeway rim blocks stones at the slab edge
(they stop), so the only way a stone leaves the ceiling is through a
gap, and every gap has a floor detour that uses the stone. Reset
sigils: stage 1 (45, 10, 29), stage 2 (48, 10, 37), kind RESET.
Stage 3 needs no reset sigil — CP4 is one step from the gap, and a
fall returns there.

## Engine table (Phase 2, against engine-a)

One `DwPuzzleTable` in `src/overlay009/dw_puzzle_route_213.c`
(map 599, progress gate 83/83 or 0/0 — the map is only entered at 83;
the table stays active for the totem visit), plus the stone data
(engine-b).

* `tiles[]` (explicit overrides): 32 of 32 max — no slack.
  * Ceiling: VOID (44, 10, 34), (49, 10, 40), (47, 10, 42); SOLID
    rune alcoves (45, 10, 33), (48, 10, 39), (48, 10, 43); SOLID
    reset alcoves (45, 10, 29), (48, 10, 37).
  * Floor: SOLID reef shelves — the 21 tiles of `FLOOR_WALK` in the
    solver; VOID (44, 1, 34), (49, 1, 40), (47, 1, 42).
  * If Phase 2 needs one more override, the design must give one back
    (e.g. shorten a floor detour by one shelf) and the solver must
    be re-run — there is no spare tile. Every floor tile in the model
    is stock-BLOCKED, so every shelf needs its override.
* `currents[]`: 7 of 16. Stage 1: (44, 1, 33) dir S, (45, 1, 33)
  dir W. Stage 2: (49, 1, 37), (49, 1, 38), (49, 1, 39) dir S.
  Stage 3: (46, 1, 43) dir E, (47, 1, 43) dir N. Arrow ghost groups
  to be assigned in Phase 2.
* `runes[]`: 6 of 8. Ceiling -> floor: (45, 10, 33) -> (47, 1, 33),
  (48, 10, 39) -> (49, 1, 34), (48, 10, 43) -> (43, 1, 43).
  Floor -> ceiling: (43, 1, 33) -> (44, 10, 35),
  (47, 1, 39) -> (49, 10, 41), (48, 1, 43) -> (47, 10, 43).
  Rotation / steps follow the stock ceiling/floor jump templates
  (rot -90/90, steps 16); the Phase 2 glue picks the matching one
  per direction. Rune targets are all in a tw_arc platform of the
  target surface: ceiling targets (44, 35), (49, 41), (47, 43) are
  causeway tiles; floor targets use platform -1.
* `sigils[]`: 2 of 16, both RESET (targetGroup ignored).
* `checkpoints[]`: 5 of 8 (CP0-CP4 above), `fallScriptId` / `fallVar`
  per the Eterna honeycomb pattern (Phase 2 picks the fall script
  entry and `VAR_MAP_LOCAL_3`, matching the existing fall warp).
* `groups[]`: 0. No group tiles are needed; the stone props are
  engine-b actors, the reef shelves and rune/sigil circles are
  static drawn tiles / ghost props (below).
* Stones (engine-b): 3 of 8. Spawn (44, 10, 31), (49, 10, 37),
  (48, 10, 42); drop rule: into a VOID gap -> floor at the same
  (x, z), staying an actor block (BLOCKED) that plugs the current;
  rim: edge pushes stop.

## Collision vs drawn (fix2-lost rule)

Every walkable tile must be drawn; every VOID tile must look open.
Phase 2 must audit this tile by tile (the audit in
`/tmp/a2/fix2/fix2-lost/harness/audit.py` is the template) — the
table below is the drawing brief, not the audit.

| Tile(s) | Drawn as |
|---|---|
| Stock causeway, island | existing hanging-lake stone (`build_dw_route_213.py`) |
| 3 ceiling gaps (VOID) | open water: the hanging-lake water face, no stone quad |
| Rune alcoves (3 ceiling) | rune circle decal on the water / slab edge + a low rim (see below) |
| Reset alcoves (2 ceiling) | sigil circle decal, distinct colour from runes |
| Floor reef shelves (21) | sunken reef / lakebed shelf props (ghost props, group NONE) — the floor under the ceiling is not stock-drawn walkable ground, so each shelf needs a prop face |
| Floor VOID tiles (3) | open water / void: no shelf face; the dropped stone's prop fills the tile as a block when it lands |
| Dropped stones (3 floor) | the stone object itself, settled in the current channel; drawn as a boulder blocking the slide path |
| Ceiling stones (3) | the stone object, pushable; drawn as a boulder on the causeway |
| Current tiles (7 floor) | flowing-water decal + arrow ghost props (engine-a `arrowGhostGroup`) pointing in the slide direction |
| Rim | the ceiling rim (already built by `build_dw_route_213.py` where stone meets water) must also exist at the slab edges (44, 30-36), (49, 27-42) where a stone could be pushed at it — it is the visual reason an edge push stops. Phase 2 confirms the rim faces exist there; if any edge is open water with no rim, the rim face is added or that push is re-checked. |

## Unchanged

* Rift contract: entry (20, 12) facing west, exit
  `Warp MAP_HEADER_ROUTE_213, 0, 715, 831, DIR_SOUTH`, calm
  `VAR_ARC2_PROGRESS` 84 + `FLAG_TOTEM_LAPRAS_DEFEATED`.
* The once-only lake line: `FLAG_ARC2_RAID_B` in
  `scripts_dw_route_213.s` is untouched.
* The card: `FLAG_ARC2_ELIAS_CARD` + `ITEM_WORN_TRAINER_CARD` at
  (32, 20) on the floor, before the first hop — outside the puzzle,
  reachable with or without solving anything. The puzzle never
  gates the card, and the card never gates the puzzle.
* Story props: the sign (24, 22), the rusted frame (31, 20), the
  rowboat, the jetty, the Lapras on the island (46, 46). None moves.
  The totem hook (`Arc2DwRoute213_HandleStep`, z >= 45) is unchanged.
* No new persistent flags: the design uses no `FLAG_DW_213_*`
  flag. The hint uses map-local `VAR_MAP_LOCAL_2` only.
* No `dwpuzzles` merge yet; Phase 2 waits for the lead's word that
  engine-a and engine-b are merged.

## Solver evidence

`python3 tools/distortion_world/route_213_solver.py` prints:

```
optimal solution: 45 steps (tile moves)
reachable states: 266
states that can reach the totem: 266
soft-lock free: True
goal states: 2; all with all stones dropped: True
```

Plus the full solution trace and one fall per stage (each returns to
its stage checkpoint with the checkpoint stone snapshot). The solver
uses Dijkstra, because a slide transition can cost more than one
tile move. The headless emulator replay, the fall/reset tests on the
real ROM, the collision-vs-drawn audit, and the other-rifts
regression are Phase 2 work, once the engines land — they are not
claimed here.

## Open questions for engine-b (stones)

1. Confirm engine-b writes ceiling stones and dropped stones via
   `DwPuzzle_SetActorBlock` (BLOCKED), and that a dropped stone
   stays an actor block on its floor tile (it is a slide-stop, and
   the player walks around it — never onto it, in this design).
2. Edge pushes: this design assumes a stone pushed at a slab edge
   **stops** (rim). The solver's soft-lock proof depends on it: an
   earlier version with "lost" stones had 39 reachable states that
   could not reach the totem (checkpoint snapshot poisoning). If
   engine-b drops edge-pushed stones instead, the design needs a
   different recovery (e.g. stones respawn on a fall, not just on a
   checkpoint restore) and the solver must be re-run.
3. Pushable tiles: a stone on the ceiling can be pushed onto any
   WALK tile (including a rune / reset alcove, which then blocks
   that alcove until the stone is pushed off) and into a VOID gap.
   Confirm the push checks the destination the same way.
4. Stone visuals / exit warp: stones are DW objects; the README
   rule (objects on walls hang the game if still loaded at the exit
   warp) applies — Phase 2 unloads the stone actors on exit.
5. `gDwPuzzleDebug.stones[]`: engine-b writes the stone positions;
   the harness will read them to replay the solver's solution.
