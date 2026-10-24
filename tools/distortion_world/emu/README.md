# DW headless kit (`tools/distortion_world/emu/`)

The shared test kit every rift workstream uses. Library + solver; the
regression runner (`rifts_regress.py`) lands next.

| file | what |
|---|---|
| `dwlib.py` | enter any rift at its entry state, move on any surface, read surface/tile from RAM, replay solution strings, detect falls/catches/resets, read `gDwPuzzleDebug`, write labelled frame strips |
| `solver.py` | offline solver framework: BFS shortest solution, no-soft-lock proof, difficulty stats, per-rift target checks, worked examples per mechanic |

Run with the Python 3.9 venv (the 3.12 venv's desmume is broken):

```sh
SDL_VIDEODRIVER=dummy ~/.venvs/desmume39/bin/python tools/distortion_world/emu/solver.py
```

One `Emu` per process (py-desmume segfaults on a second `DeSmuME()`).

## Entry

Primary: overworld entry. The kit patches a copy of the battle-stage
save in the file (approach tile, pre-entry `VAR_ARC2_PROGRESS`, the
rift's hide flag cleared, story-true totem flags, and for talk-rifts
the rift object itself -- see below) and steps onto (Ravaged Path) or
talks to (the rest) the rift object. The game's own warp sequence runs
`OnTransition`, which activates the DW system. A Continue boot
straight into a DW map does **not** run `OnTransition`, so the DW
system stays inactive there (no jumps, the fall warp crashes); direct
boot (`DwSession.boot_rift`) is for tile/pixel checks only.

Talk-rifts need their object in the save: a Continue boot loads the
save's object list, and the base save predates the rifts, so the rift
object is missing. The kit zeroes the stale list and appends the rift
object (localID/gfx/flag/script/coords from the map's events JSON,
status fields copied from a working static entry in the base save).
Ravaged Path needs no object: its entry is a step-on coord event.

Rift approaches (`OVERWORLD_RIFTS` in `dwlib.py`):

| rift | approach | trigger |
|---|---|---|
| Ravaged Path | (19,50), walk up the stairs | step onto (19,45) |
| Eterna Forest | (84,37) facing south | A, then Yes |
| Route 214 | (726,665) facing north | A |
| Route 213 | (715,831) facing north | A |
| Lost Tower (both visits) | (7,8) facing west | A |

The Ravaged Path approach is the bottom of the stairs: the rift tile
(19,45) sits at height 2 and the stairs raise the player. Teleporting
straight to (19,46) leaves the player at the wrong height and the rift
never triggers.

## Movement

One move is one `FACE_*` direction as pressed on the surface the
player stands on (`FACE_UP = 0, DOWN = 1, LEFT = 2, RIGHT = 3`, the
D-pad key of the same name). The step table is the stock one in
`src/unk_0205F180.c`: floor `UP (0,0,-1) DOWN (0,0,+1) LEFT (-1,0,0)
RIGHT (+1,0,0)`; west wall `UP (0,+1,0) DOWN (0,-1,0) LEFT (0,0,+1)
RIGHT (0,0,-1)`; east wall the same except `LEFT/RIGHT` flipped in
`z`; ceiling `UP (0,0,+1) DOWN (0,0,-1) LEFT (-1,0,0) RIGHT (+1,0,0)`.

Solution strings are space-separated letters (`U/D/L/R` for `FACE_*`,
`W` an alias for `U`, `A` taps A, `.` waits). `DwSession.step`
presses one direction, waits for the step, pumps any dialogue (the
message box is detected by the light-pixel fraction in the top-screen
band rows 140-175: 0.56 with a box, 0.00 without), gives scripted
pauses a grace period, and settles again so a late warp (fall, fold,
carry) is that step's outcome. Falls are detected by the debug
`fallCount` when engine-a is present, else by the player settling at
the entry/checkpoint when the step did not target that tile.

The player tile comes from RAM: `sFieldSystem -> playerAvatar (+0x3C)
-> mapObject (+0x30) -> x (+100), y (+104), z (+108)`, with `y/2` as
the game reports it. The chain is torn down during warps, so reads
tolerate `None` there. The surface prefers `gDwPuzzleDebug.surface`
and otherwise infers it from the tile (y 1 floor, y 10 ceiling,
else the rift's wall).

## `gDwPuzzleDebug`

Read through the xMAP symbol of the same build, using engine-a's
`include/overlay009/dw_puzzle.h` layout (prefix 172 bytes). The struct
grows as engine-a/b add fields (`stoneStates[]`: RESTING 0, FALLING 1,
LANDED 2, appended after the prefix); the reader takes the symbol's
xMAP size and parses the tail tolerantly, so growth never breaks it.
Before engine-a lands the symbol is absent and `debug()` returns
`None`; the kit falls back to tile inference. `gDwPuzzleTestMode` is
the only live RAM write the kit makes (engine-a's documented harness
gate), read back after writing.

## Solver

`solver.py` is pure Python (no emulator). A model is surfaces (grids
per surface), jumps (edge jumps / hop points), start, goal, and
mechanics: `Sigils` (toggle/set/momentary/reset), `Runes`, `Currents`
(slides), `Stones` (push, drop to the surface below, plug currents),
`Crumbling` (per-tile one-use), `ScarGroups` (the Ravaged Path
scars' exact rule), `Shadow` (patrol lane, WAIT `.` beats), `Echo`
(mirror ghost pressing its own sigils), plus `gate_tiles` (a tile
walkable only while its group is on).

It BFSes the shortest solution (pressed moves only; a current slide
is part of the one press that started it), proves no reachable
soft-lock (every reachable state can still reach the goal over the
transition graph, falls/resets included), and prints difficulty
stats: optimal length, branching (mean out-degree over reachable
states), required toggles/pushes, and wrong-looking right moves
(optimal steps that do not strictly decrease the plain-grid distance
to the goal). `check_targets(rift, stats)` flags an optimal length
outside the revised PUZZLE_PLAN section 2 range, and a branching
below the 1.2 harness floor for difficulty >= 2 (the plan gives no
branching ranges; the floor is a harness heuristic).

Worked examples: one per mechanic, plus `ravaged_path_model()`, a
sanity model of today's Ravaged Path wall that reproduces a 16-move
optimum (the solver's line steps once on the (y3, z21) scar tile --
legal, a scar holds exactly once -- as does the documented line).

## Status (2026-10-23)

- DONE: Ravaged Path overworld entry + replay to the totem tile and
  the totem battle menu; Eterna Forest entry, fold, and ceiling route
  to the honeycomb. `solver.py` with all examples + the Ravaged Path
  sanity model. `gDwPuzzleDebug` reader at engine-a's layout, with
  tolerant `stoneStates`.
- IN PROGRESS: Eterna Forest honeycomb crossing (retry loop),
  Route 214 / Route 213 entries and floor routes, Lost Tower entries
  and routes, `rifts_regress.py` (one worker process per rift: boot,
  replay, frame strip, report).
- NOT COVERED: the post-calm exit warps (they need the totem battle
  won; QA's chained playthrough covers those). The regress exit leg
  is the Lost Tower visit-1 shadow-wall warp only.
