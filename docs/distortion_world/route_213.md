# DW Route 213, the Drowned Lake — puzzle design (rift #4)

Owner: workstream `rift-213`. Phase 1 design (the engines are not merged yet).
Plan: `docs/distortion_world/PUZZLE_PLAN.md` section 2, revised curve
(2026-10-23): Arc 2 tops out at 6/10. This rift is **difficulty 5**,
**45-65 steps across two surfaces** (ceiling + ground), with a reset sigil.

* Map: `MAP_HEADER_DW_ROUTE_213`, Arc 2 scene 2.21, progress 83 -> 84,
  Lapras totem behind the puzzle.
* New mechanic: **rift stones** (engine-b). Combined with **currents**
  (rift #3) and **gravity runes** (rift #2, used only to move between
  the two surfaces — three rune pairs, nothing else).
* Solver: `tools/distortion_world/route_213_solver.py` (standalone
  Dijkstra over the puzzle model, with the engine-a and engine-b
  semantics). Optimal solution **46 steps**, in range. All 296
  reachable states reach the totem: soft-lock free.
* Surfaces: ceiling (y = 10) + **GROUND** (y = 1, base map terrain).
  Route 213's lakebed is base terrain, so engine-b requires GROUND,
  not FLOOR (a floating platform). For GROUND there is no platform
  grid and a DEFAULT ground tile reads BLOCKED (engine-b's conservative
  cross-surface rule), so the table gives
  every ground actor tile an explicit state (see "Engine tables").
* Engine-a API: `include/overlay009/dw_puzzle.h` (commit 623ccce7ee on
  `dw/engine-a`). Engine-b stone semantics: `docs/distortion_world/
  actors_design.md` (branch `dw/engine-b`) — **authoritative for
  stones**. This design was reworked in Phase 1 review round 5 to
  match it (see "Rework history").
* Flag block: `FLAG_DW_213_A..H` (0x0A18-0x0A1F) is assigned to this
  workstream in `docs/arc2/registry.md` on `dwpuzzles`. The Phase 1
  design uses **none** of them; if Phase 2 needs a persistent flag
  (e.g. for the hint), it takes `FLAG_DW_213_A` first and renames the
  matching `FLAG_UNK_0x0A18` line in `generated/vars_flags.txt`.

## The two ideas

1. **Drop a stone through a gap to bridge it below.** A stone pushed on
   the ceiling into an open gap falls to the ground below and lands as
   **SOLID walkable terrain** — a stepping stone over a VOID gap
   (engine-b: LANDED). The gap looks like losing the stone; it is the
   solution. (Non-obvious move, required from rift 3 on.) The player
   walks **onto** the landed stone. It is not pushable and not an
   obstacle.
2. **Plug a current with a resting stone on the same surface.** A
   RESTING stone pushed onto a current tile plugs the current: its
   BLOCKED actor tile stops the slide before it. In stage 2 the plug
   stone is pushed twice down the current column onto the last current
   tile, so the slide stops at the tile before it — the gateway around
   the column.

Everything else is walking. Four stones (engine-b max per map): three
ceiling stones that drop to bridge ground gaps, one ground stone that
plugs the stage-2 current. Three gaps, three ground detours, four
current tiles (one three-tile chain, one ride). No sigils except the
two reset sigils. No new persistent flags.

## Geometry

The puzzle starts at the ceiling entry — the jump landing at the top
of the east wall, (49, 27), with the first checkpoint (49, 28) one
step south of it — and ends at the totem trigger on the island (any
ceiling tile with z >= 45). The ground approach (entry (20, 12), the
two hops, the jetty, the wall climb) is plain travel, not puzzle, and
is not counted in the 46 steps. The ceiling causeway is the stock
serpentine from `tools/distortion_world/route_213.json`; the ground
detours are sunken reef shelves (see "Collision vs drawn").

Coordinates: DW world tiles (x, z); ceiling y = 10, ground y = 1, as
the ov9 step hook sees them. `C` = ceiling, `G` = ground (GROUND
surface, base map terrain).

### Ceiling (y = 10)

`#` = BLOCKED (water / off-causeway), `.` = stock causeway, `V` = VOID
gap (the drop chute; each is a designated edge for one ceiling stone),
`S` = stone spawn, `r` = rune-down alcove, `R` = reset-sigil alcove,
`P` = checkpoint.

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
34   V  #  #  #  #  #   <- gap 1 (44,34): edge, landing ground (44,34)
35   .  #  #  #  #  #   <- (44,35) is the return tile past gap 1
36   .  .  .  .  P  .   <- CP3 at (48,36)
37   #  #  #  #  R  S   <- R=(48,37) reset 2 (before stone 2); stone 2
38   #  #  #  #  #  .   <- (48,38) is water: no shelf, no shortcut
39   #  #  #  #  r  .   <- r=(48,39) rune down 2
40   #  #  #  #  #  V   <- gap 2 (49,40): edge, landing ground (49,40)
41   #  #  #  #  #  .   <- (49,41) is the rune-up landing, NOT a checkpoint
42   .  .  .  V  S  P   <- gap 3 (47,42): edge, landing ground (47,42);
                              stone 3 (48,42), CP4 at (49,42)
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

### Ground (y = 1, GROUND surface)

`#` = BLOCKED (stock lakebed), `.` = reef shelf (SOLID override),
`V` = VOID until a dropped stone lands on it (as a SOLID actor tile;
landing tiles carry an explicit VOID override, beaten by the LANDED
actor tile after landing), `v` = current tile
(sliding south), `^` = current tile (sliding north), `r` = rune-up
tile, `x` = rune-down landing, `s` = resting stone spawn.

```
Stage 1 (under gap 1), x 43-47, z 33-34:  the bridge teach
  z33:  #  .  .  x  #      <- x=(46,33) landing (rune-down); walk west
  z34:  r  V  #  #  #      <- V=(44,34) landing; walk onto the landed stone;
                              r=(43,34) rune-up -> ceiling (44,35)

Stage 2 (under gap 2), x 48-49, z 34-41:  the plug teach
  Columns are x=48 (left) then x=49 (right) in every row.
  z34:  #  x               <- x=(49,34) landing (rune-down); walk south
  z35:  #  .               <- walk south
  z36:  .  .               <- walk south, then west
  z37:  s  #               <- s=(48,37): the plug stone, resting on the
                              current column; push it south twice
  z38:  v  .               <- v=(48,38): current; after the first push the
                              stone rests here; walk around via (49,38)
  z39:  v  .               <- v=(48,39): current; after the second push
                              the stone rests here and plugs the column;
                              the slide stops at (48,38)
  z40:  V  V               <- (48,40) is an explicit VOID hazard:
                              without the plug the slide runs
                              (48,37)->(48,38)->(48,39)->(48,40) and
                              falls; (49,40) is the landing of stone 2
                              (VOID until stone 2 lands on it)
  z41:  #  r               <- r=(49,41) rune-up -> ceiling (49,41)

Stage 3 (under gap 3), x 43-48, z 42-43:  the ride
  z42:  #  #  #  #  V  r   <- V=(47,42) landing; r=(48,42) rune-up ->
                              ceiling (47,43)
  z43:  x  .  .  .  ^  #   <- x=(43,43) landing (rune-down); ^=(47,43)
                              slides north onto the landed stone
  The slide: (47,43) -> (47,42) landed stone (off-current, slide ends).
```

The three ground detours are disjoint: no ground tile of one detour is
adjacent to a ground tile of another, except at rune tiles, which
teleport on entry — so one detour can never leak into another (the
solver checks this: the optimal solution does not shortcut any stage).

## Teaching beat

Stage 1 teaches the drop, with no current:

* Stone 1 spawns **on the path** at (44, 31). The only way on is to
  push it: south along leg C to (44, 33), then south into gap 1. The
  player is already pushing before they have to think about it.
* The rune-down alcove (45, 33) is one step east of (44, 33). The
  player rides down and finds the ground detour: a walk west, then
  across the landed stone at (44, 34) to the rune-up.
* A fall in stage 1 is stepping onto the ceiling gap (44, 34) after
  dropping (walking south from (44, 33) instead of east to the rune).
  It returns the player to CP2 (44, 30) with the stones as they were
  at CP2: stone 1 back on the ceiling. Trying a wrong step is cheap,
  and the retry is short. (Counterfactual, not a reachable fall:
  stepping onto the ground landing (44, 34) before the ceiling stone
  is dropped would also be a fall, but the rune-down path to the
  ground detour requires dropping stone 1 first — the player cannot
  get there with the landing still VOID.)

Stage 2 teaches the plug: the ground stone rests on the current column
at (48, 37). Pushing it south twice puts it on (48, 39), plugging the
column; the slide from (48, 37) would otherwise run to (48, 40),
which is VOID (a fall). With the plug, the slide stops at (48, 38),
the gateway around the column.

Stage 3 repeats the drop with a current ride: the current at (47, 43)
slides the player north onto the landed stone at (47, 42). (Counterfactual,
not a reachable fall: without the dropped stone the slide would run onto
VOID (47, 42) and the player would fall, but the rune-down path to the
ground detour requires dropping stone 3 first.)

## Solution (46 steps, from the solver)

Counting: one tile move (walk, push, slide step) = 1 step; a rune
surface change = 0 steps. `C`/`G` = surface after the move. The
table lists 45 input steps; the total is 46 tile moves because step
42 is a two-tile slide (step onto the current at (47,43), then slide
to (47,42)).

Each row is one input step, except step 42, which is two tile moves
(step onto the current at (47,43), then the slide to (47,42)). A rune
fires as part of the step onto its tile (0 extra steps). Numbering is
the solver trace, verified.

| # | Move | # | Move |
|---|---|---|---|
| 1-3 | C (49,27) -> (49,30) | 24-25 | C (49,37) -> (49,39), push stone 2 twice |
| 4-8 | C (49,30) -> (44,30) [CP2] | 26 | C (49,39) -> rune (48,39) -> G (49,34) |
| 9-11 | C (44,30) -> (44,33), push stone 1 twice, drop into gap 1 | 27-29 | G (49,34) -> (48,36) |
| 12 | C (44,33) -> rune (45,33) -> G (46,33) | 30 | G (48,36) -> (48,37), push plug stone to (48,38) |
| 13-14 | G (46,33) -> (44,33) | 31 | G (48,37) -> (48,38), push plug stone to (48,39), plug |
| 15 | G (44,33) -> (44,34), onto landed stone 1 | 32-33 | G (48,38) -> (49,39) via (49,38) |
| 16 | G (44,34) -> rune (43,34) -> C (44,35) | 34 | G (49,39) -> (49,40), onto landed stone 2 |
| 17-22 | C (44,35) -> (49,36), via CP3 (48,36) | 35 | G (49,40) -> rune (49,41) -> C (49,41) |
| 23 | C (49,36) -> (49,37), push stone 2 | 36 | C (49,41) -> (49,42) [CP4] |
| | | 37 | C (49,42) -> (48,42), push stone 3 into gap 3 |
| | | 38 | C (48,42) -> rune (48,43) -> G (43,43) |
| | | 39-41 | G (43,43) -> (46,43) |
| | | 42 | G (46,43) -> slide to (47,42), onto landed stone 3 |
| | | 43 | G (47,42) -> rune (48,42) -> C (47,43) |
| | | 44-45 | C (47,43) -> (47,45), totem |

Checkpoint snapshots: each checkpoint is stepped on **before** its
stage's stone is pushed, so the snapshot is always a clean state
(stones at spawn, or dropped stones from earlier stages, which are
fixed on the ground as LANDED actor tiles). A fall therefore never
snapshots a bad stone position. No checkpoint is a rune landing: every
checkpoint is reached by walking (the normal step hook), because
engine-a's rune starts a jump task and does not promise a step-hook
call at its destination. The reset sigils (stage 1: (45, 29); stage 2:
(48, 37)) restore the same snapshot without moving the player.

## Cyrus's hint (after two falls)

Text id `DWRoute213_Text_CyrusPuzzleHint`, in
`res/text/dw_route_213.json`. ASCII, 197 px boxes, short
lines in character. Trigger: the second fall, in the fall script
(`DWRoute213_Fall`, entry 10). It fires once per save, via persistent
flags `FLAG_DW_213_A` (fell once) + `FLAG_DW_213_B` (hint shown):
map-local vars cannot count falls because they reset on the fall
warp. (Phase 1 doc said map-local + re-fire; Phase 2 changed this —
persistent flags are the only counter that survives the warp.)

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
| CP0 (table index 0) | (20, 1, 12), ground entry | stones at spawn |
| CP1 | (49, 10, 28), first walked ceiling tile | stones at spawn |
| CP2 | (44, 10, 30) | stones at spawn |
| CP3 | (48, 10, 36) | stone 1 LANDED (44, 34); stones 2, 3, plug at spawn |
| CP4 | (49, 10, 42) | stones 1, 2 LANDED; stone 3, plug as at CP3 |

(The solver numbers the puzzle checkpoints 0-3; the table adds the
rift-entry checkpoint at index 0.)

Fall cost: return to the last checkpoint, stones to its snapshot. No
stone is ever lost: a stone can only fall at a designated edge with a
designated landing, and never into a landing clash. A RESTING stone
can never occupy a checkpoint, pad, sigil, landing, or reset-sigil
tile (push-block rules), so the reset path is never stone-blocked.
Reset sigils: stage 1 (45, 10, 29), stage 2 (48, 10, 37), kind RESET.
Stage 3 needs no reset sigil — CP4 is one step from the gap, and a
fall returns there.

## Engine tables (Phase 2, against engine-a + engine-b)

One `DwPuzzleTable` in `src/overlay009/dw_puzzle_route_213.c`
(map 599, progress gate 83/83 or 0/0 — the map is only entered at 83;
the table stays active for the totem visit), plus the actor table
(engine-b) in the same file.

* `tiles[]` (explicit overrides): 32 of 32 max — exactly at the cap.
  How it fits (lead rule change, 2026-10-23): engine-a now makes
  actor tiles beat explicit overrides, so the 3 landing tiles get an
  explicit VOID override each (VOID before landing, LANDED SOLID
  actor tile wins after). That took the budget from 30 to 33, over
  the 32 cap. Instead of asking engine-a for a bigger cap, one
  override was dropped: the stage-1 rune-down landing moved from
  (47, 1, 33) to (46, 1, 33), so (47, 1, 33) is no longer a shelf.
  30 + 3 - 1 = 32.
  * Ceiling: VOID (44, 10, 34), (49, 10, 40), (47, 10, 42); SOLID
    rune alcoves (45, 10, 33), (48, 10, 39), (48, 10, 43); SOLID
    reset alcoves (45, 10, 29), (48, 10, 37).
  * Ground: SOLID reef shelves — the 20 tiles of `GROUND_WALK` in the
    solver (this includes the four current tiles; current tiles need
    their own SOLID overrides); plus four explicit VOID overrides:
    the 3 landing tiles (44, 1, 34), (49, 1, 40), (47, 1, 42), and
    (48, 1, 40), the hazard at the end of the stage-2 current
    column. The landing tiles' VOID override is beaten by the LANDED
    actor tile after landing (engine-a rule change), so no
    `map_data_680` clone and no base-kind change is needed: the
    collision glue lets explicit ground overrides beat the stock
    0x8000 permission in `map_data_615`, and engine-a is adding a
    guard so a LANDED (SOLID) stone suppresses the stock fall-lip.
    The landing tiles must still *look* like holes or water
    (collision-vs-drawn: no shelf face drawn on them).
* `currents[]`: 4 of 16. Stage 2: (48, 1, 37), (48, 1, 38),
  (48, 1, 39) dir S. Stage 3: (47, 1, 43) dir N. Arrow ghost groups
  to be assigned in Phase 2.
* `runes[]`: 6 of 8. Ceiling -> ground: (45, 10, 33) -> (46, 1, 33),
  (48, 10, 39) -> (49, 1, 34), (48, 10, 43) -> (43, 1, 43).
  Ground -> ceiling: (43, 1, 34) -> (44, 10, 35),
  (49, 1, 41) -> (49, 10, 41), (48, 1, 42) -> (47, 10, 43).
  Rotation: ceiling -> ground rot +180, ground -> ceiling rot
  -180, steps 0 (= 16). (An earlier draft said +-90, mirroring the
  stock wall -> ceiling turns; that was wrong: the ceiling and the
  ground face opposite directions, a 180-degree flip, while a wall
  meets the ceiling at 90 degrees. The replay proves +-180.) Rune targets are all in a tw_arc platform of the
  target surface: ceiling targets (44, 35), (49, 41), (47, 43) are
  causeway tiles; ground targets use surface GROUND (platform -1 for the rune glue).
* `sigils[]`: 2 of 16, both RESET (targetGroup ignored).
* `checkpoints[]`: 5 of 8 (CP0-CP4 above), `fallScriptId` / `fallVar`
  per the Eterna honeycomb pattern (Phase 2 picks the fall script
  entry and `VAR_MAP_LOCAL_3`, matching the existing fall warp).
* `groups[]`: 0. No group tiles are needed; the stone props are
  engine-b actors, the reef shelves and rune/sigil circles are
  static drawn tiles / ghost props (below).
* Stones (engine-b actor table): 4 of 4 max.
  * S1: start (44, 10, 31) ceiling RESTING; edge (44, 10, 34) ->
    landing (44, 1, 34) ground LANDED.
  * S2: start (49, 10, 37) ceiling RESTING; edge (49, 10, 40) ->
    landing (49, 1, 40) ground LANDED.
  * S3: start (48, 10, 42) ceiling RESTING; edge (47, 10, 42) ->
    landing (47, 1, 42) ground LANDED.
  * S4 (plug): start (48, 1, 37) ground RESTING, on the stage-2
    current column; no edges (it never falls). It is pushed south
    twice to (48, 1, 39), where it plugs the current.
  * Surfaces: ceiling stones carry surface CEILING; ground stones
    carry surface GROUND (the old lakebed is base map terrain).
    The solver models the two surfaces as C/G. For GROUND, a DEFAULT
    tile reads BLOCKED (engine-b's conservative cross-surface rule),
    so every ground tile the puzzle uses gets an explicit state:
    the landing tiles get an explicit VOID override in the table
    (above), the (48, 40) hazard gets an explicit VOID override, and
    all other ground detour tiles get SOLID overrides.
  * Protected tiles (`protectedTiles`, engine-b): engine-b does NOT
    auto-protect engine-a checkpoints / reset sigils, so the actor
    table lists all seven: CP0 (20, 1, 12) GROUND, CP1 (49, 10, 28)
    CEILING, CP2 (44, 10, 30) CEILING, CP3 (48, 10, 36) CEILING,
    CP4 (49, 10, 42) CEILING, reset 1 (45, 10, 29) CEILING, reset 2
    (48, 10, 37) CEILING. 7 of engine-b's max 8. The solver models
    this set: a push whose target is a protected tile fails.
  * A push step onto a current tile still reaches the engine-a step
    hook, so the slide starts — but it immediately stops before the
    BLOCKED actor tile of the stone just pushed there (no extra tile
    move). The solver models this as no slide movement on a push
    step. This is the glue-consistent reading (engine-b suppresses
    engine-a step handling only for PAD_READY, not for pushes), and
    it needs no new glue behaviour.

## Collision vs drawn (fix2-lost rule)

Every walkable tile must be drawn; every VOID tile must look open.
Phase 2 must audit this tile by tile (the audit in
`/tmp/a2/fix2/fix2-lost/harness/audit.py` is the template) — the
table below is the drawing brief, not the audit.

| Tile(s) | Drawn as |
|---|---|
| Stock causeway, island | existing hanging-lake stone (`build_dw_route_213.py`) |
| 3 ceiling gaps (VOID) | open water: the 676 model's shore face (`dw213_lakep`, full tile) over the gap, no stone quad, rim (`criffp_lm9`) on every water->non-water edge. The gaps are `#` (blocked) in the stock ceiling grid (JSON rows + tw_arc_attr), so they behave like the ground VOIDs (stock-blocked + VOID override). Found by the Phase 2 audit: the gaps were `.` (stone) in the JSON rows, so the builder drew causeway stone over them; fixed by flipping the three chars to `#` (Codex round-1 finding 2). |
| Rune alcoves (3 ceiling) | small-platform ghost prop (kind 0, group 0) at y=10 on the water tile (the Eterna honeycomb pattern for walkable ceiling tiles) |
| Reset alcoves (2 ceiling) | small-platform ghost prop (kind 0, group 0) at y=10 on the water tile, same prop as runes (no separate sigil colour in the prop set) |
| Ground reef shelves (20) | small-platform ghost props (kind 0, group 0, default-visible) at y=1 — stock 615 draws nothing at these tiles, so each shelf needs a prop face |
| Ground landing tiles (3) | open water / void: no shelf face; the landed stone's MapObject fills the tile when it lands (the sprite is the drawn proof of the SOLID tile) |
| Landed stones (3 ground) | the stone MapObject itself, settled on the gap; drawn as a stepping stone |
| Ceiling stones (3) | the stone MapObject, pushable; drawn as a boulder on the causeway |
| Plug stone (1 ground) | the stone MapObject, pushable; drawn as a boulder on the current column |
| Current tiles (4 ground) | reef shelf prop (kind 0) like the other shelves; no arrow ghost prop exists in the DW prop set — drift direction is shown by the corridor geometry (the stage-2 column points south to the hazard gap; the stage-3 tile points north to the landed stone) plus the Cyrus hint |
| Rim | the ceiling rim (already built by `build_dw_route_213.py` where stone meets water) must also exist at the slab edges (44, 30-36), (49, 27-42) where a stone could be pushed at it — it is the visual reason an edge push stops. Phase 2 confirms the rim faces exist there; if any edge is open water with no rim, the rim face is added or that push is re-checked. |

Note: the design has no "rim stops a stone" rule any more. A stone
pushed at a slab edge that is not a designated edge is blocked by the
push-block rules (BLOCKED target), not by a rim. The ceiling rim is
purely visual now; the solver does not rely on it.

## Unchanged

* Rift contract: entry (20, 12) facing west, exit
  `Warp MAP_HEADER_ROUTE_213, 0, 715, 831, DIR_SOUTH`, calm
  `VAR_ARC2_PROGRESS` 84 + `FLAG_TOTEM_LAPRAS_DEFEATED`.
* The once-only lake line: `FLAG_ARC2_RAID_B` in
  `scripts_dw_route_213.s` is untouched.
* The card: `FLAG_ARC2_ELIAS_CARD` + `ITEM_WORN_TRAINER_CARD` at
  (32, 20) on the ground, before the first hop — outside the puzzle,
  reachable with or without solving anything. The puzzle never
  gates the card, and the card never gates the puzzle.
* Story props: the sign (24, 22), the rusted frame (31, 20), the
  rowboat, the jetty, the Lapras on the island (46, 46). None moves.
  The totem hook (`Arc2DwRoute213_HandleStep`, z >= 45) is unchanged.
* Persistent flags: `FLAG_DW_213_A` (fell once) + `FLAG_DW_213_B`
  (hint shown), from the assigned block, for the hint counter
  (see above). Nothing else takes a flag.

## Solver evidence

`python3 tools/distortion_world/route_213_solver.py` prints:

```
optimal solution: 46 steps (tile moves)
reachable states: 296
states that can reach the totem: 296
soft-lock free: True
goal states: 2; all with all stones dropped: True
engine table budget: tiles 32<=32, currents 4<=16, runes 6<=8,
  sigils 2<=16, checkpoints 5<=8, stones 4<=4 (engine-b max),
  protected 7<=8
```

Plus the full solution trace and one fall per stage (each returns to
its stage checkpoint with the checkpoint stone snapshot). The solver
uses Dijkstra, because a slide transition can cost more than one
tile move. The headless emulator replay, the fall/reset tests on the
real ROM, the collision-vs-drawn audit, and the other-rifts
regression are Phase 2 work, once the engines land — they are not
claimed here.

## Rework history

* Phase 1 rounds 1-4 (Codex, against engine-a): stones as slide-stops
  (player walks around them), reset-sigil bypass fixes, Dijkstra,
  checkpoint-after-rune removed, CP1 moved to (49, 28). APPROVED.
* Phase 1 round 5 (lead: engine-b's design is authoritative for
  stones): the slide-stop design is not supported — a LANDED stone is
  SOLID walkable terrain, not a slide-stop, and landing tiles are
  never current tiles. Reworked: dropped stones bridge ground VOID
  gaps (player walks onto them); current-plugging is done by pushing
  a RESTING stone onto a current tile on the same surface (stage 2).
  Stone count cut from 6 to 4 (engine-b max). Tile budget 30/32.
  Solver rewritten with engine-b states (RESTING / FALLING /
  LANDED), edge/landing tables, landing-clash, and push-block rules.
* Phase 1 round 6 (Codex delta review, against engine-b): GROUND
  surface specified throughout (the lakebed is base terrain, not a
  floating FLOOR); (48, 40) added as an explicit VOID hazard so the
  stage-2 slide is a real fall without the plug; push-step slide
  modelled as a no-op start/stop (glue-consistent); CP0-CP4 + both
  reset sigils listed in `protectedTiles` (7/8); stage-2/3 ASCII
  columns fixed; input-vs-tile-move counting clarified.
* Phase 1 round 7 (Codex delta review, against engine-b): DEFAULT
  GROUND reads BLOCKED (not WALKABLE) corrected in both files;
  landing tiles located in matrix chunk (1, 1) = stock `map_data_615`,
  so Phase 2 needs a Route-213-specific clone (`map_data_680`) with
  a matrix update, not edits to 675/676; solution notation C/F -> C/G;
  push-step comment clarified as zero-movement start/stop; stage-2
  z40 row shows `V V`; stage-1 ground fall and stage-3 stone-less
  ride labelled counterfactual (unreachable — the rune-down paths
  require dropping those stones first).
* Phase 1 round 8 (Codex delta review): stale open question, stale
  solver comment, budget-quote suffix fixed. APPROVED.
* Phase 1 rule change (lead, engine-a: actor tiles beat explicit
  overrides): the 3 landing tiles now get an explicit VOID override
  each (VOID before landing, LANDED SOLID wins after) — no
  `map_data_680` clone, no base-kind change, and the round-7 clone
  plan above is superseded. Budget went 30 + 3 = 33, over the 32
  cap; instead of asking engine-a for a bigger cap, one override was
  dropped (stage-1 rune-down landing (47, 33) -> (46, 33), so
  (47, 33) is no longer a shelf). Budget 32/32, solution 46 steps,
  296 reachable states, all reaching the totem. No full Codex round
  for this change (lead: reviewed in the Phase 2 review).

## Open questions for engine-b (stones)

1. CONFIRMED by the Phase 2 plug proof: the plug stone lands on
   (48, 39) and the slide stops at (48, 38).
2. RESOLVED by the lead's rule change (no answer needed): landing
   tiles get an explicit VOID override in the table; actor tiles
   beat overrides, so the LANDED stone wins after landing. No
   `map_data_680` clone, no base-kind change. The landing tiles
   must still *look* like holes or water (collision-vs-drawn).
3. CONFIRMED by the Phase 2 fallframes proof: FALLING spans 12
   engine ticks (~21-22 emulator frames at the ~30 Hz tick).
4. CONFIRMED by construction: the totem block (exit warp + calm)
   is byte-identical to `dwpuzzles`, and the engine's `VisualsExit`
   teardown runs on the exit warp (engine-a delivered).
5. `gDwPuzzleDebug.stones[]`: engine-b writes the stone positions;
   the harness will read them to replay the solver's solution.

## Phase 2 proof (headless, on the built ROM)

`tools/distortion_world/r213_proof.py` (one Emu per process).
Evidence in `/tmp/dwp/rift-213/` (`replay.json`, `falls.json`,
`reset.json`, `plug.json`, `fallframes.json`, `reentry.json`,
`audit.json`, `exit.json`, `strip_*.png`). All PASS:

* **replay**: approach + the solver's 45 inputs; every step's
  tile, surface, and all 4 stone positions/states match the solver
  trace; ends at (47, 10, 45) with the Lapras battle menu up.
* **falls**: one fall per stage (ceiling gaps). Fall 1 ->
  (44, 30) CP2, fall 2 -> (48, 36) CP3, fall 3 -> (49, 42) CP4;
  stones restore to the checkpoint snapshot (pre-stage snapshots:
  CP3 predates stage 2, so a stage-2 fall restores S2 and the plug
  to spawn). Fall 2 shows the Cyrus hint; `FLAG_DW_213_A/B`
  (0x0A18/0x0A19) both set. `fallCount` survives the fall warp
  (it reads 0 transiently mid-warp while the debug struct is
  re-initialised).
* **reset**: both sigils fire (`resetGeneration` +1, lastEvent
  RESET). Reset 2 (reached without crossing a checkpoint)
  genuinely restores the pushed stone 2 to spawn. Reset 1 is
  reached via a CP2 re-step, which re-snapshots (the engine
  snapshots stones on EVERY checkpoint step, not just index
  changes), so it restores to a snapshot that already includes
  the push — the documented "a reset cannot undo a completed
  push" semantics. No test change to the engine was made for this.
* **plug**: (47, 36) blocks; the plug stone lands on (48, 39);
  the plugged slide stops at (48, 38); stepping W from the
  landed stone 2 onto the (48, 40) VOID hazard falls (explicit
  VOID override on a stock-`0x8000` ground tile) and respawns
  at CP3.
* **fallframes**: a stone's FALLING state spans 21-22 emulator
  frames = 12 engine ticks (`DW_STONE_FALL_FRAMES`); the actor
  frame tick runs at ~30 Hz.
* **reentry**: fresh boot has stones at spawn, checkpoint 0,
  fallCount 0.
* **audit**: all 84 puzzle tiles covered (shelves + alcoves +
  causeway + VOIDs + landed stones); ghost-prop set is exactly
  the 20 shelves + 5 alcoves, `ghost_default_visible` 1,
  `ghost_triggers` [].
* **exit**: the totem block (exit warp + calm 84) is byte-identical
  to `dwpuzzles`.
* **regression**: `rifts_regress.py` on the other rifts against
  this build: all 7 legs PASS (arc1 totem, rp totem, ef totem
  after 3 honeycomb crossing attempts, r214 totem, lt1 totem +
  shadow-wall exit to Lost Tower 2F (7, 8), lt2 totem).
  r213 is excluded because its recorded solution is the obsolete
  pre-puzzle route; the proof above supersedes it for r213.

## Phase 2 engine glue fixes (in `src/overlay009/ov9_02249960.c`, marked `// dwp:rift-213`)

Two bugs in the shared engine glue, both found by this rift's
proof and both required for it. They are the lead's to merge or
move to engine-a/b; they are NOT rift-213 table changes.

1. **Ceiling facing (`DwPuzzle_Ov9FaceFromDir`)**: the glue fed
   `PlayerAvatar_GetDir` (world DIR) straight into
   `DwPuzzle_DirDelta`, which indexes by surface FACE. On the
   ceiling the avatar faces mirrored in both axes (a LEFT press
   faces DIR 3, RIGHT faces DIR 2, UP/DOWN face DIR 1/0), so the
   correct conversion is `FACE = DIR ^ 1`. Before the fix, an
   x-push on the ceiling targeted the tile on the wrong side
   (the walk check's dest test failed, the step was blocked) —
   stone 3 could never be pushed into gap 3. GROUND/FLOOR are
   identity; the ceiling is `DIR ^ 1`; the walls are west
   {3,2,0,1} / east {2,3,1,0} (DIR -> FACE), verified by headless
   facing probes on both walls (the travel direction is uniquely
   invertible from the facing: on the west wall, facing west =
   climbing, east = descending, north = -z, south = +z; on the
   east wall, facing east = climbing, west = descending, north =
   -z, south = +z). The inverse (`DirFromFace`) converts the
   table's FACE_* rune / checkpoint facings back to world DIRs
   for the jump task / respawn, and `HandleFrame` gets a FACE
   (the table's checkpoint facings are FACE_*). The fix applies
   at both `DirDelta` call sites (pre-move `Ov9TryPushTile` and
   the step-hook prev computation).
2. **Jump-task travel loss (`TickJump...`, `while` not `if`)**:
   the per-axis accumulation used `if`, so when one tick's
   travel exceeded the threshold the excess was stranded and
   the jump landed short. Stock jumps displace at most 6 tiles
   over 16 steps (the hops), so each tick's increment stays
   below the per-axis threshold (x: 24576 < 65536; y: 4096 <
   32768) and `while` is equivalent to `if` for them; a rune
   jump displaces up to 9 tiles, and ceiling -> ground stopped
   at y = 2 (the player was stuck: the glue found no override
   at (x, 2, z)). With `while`, the delivery is exact for all
   six runes.

Also: a new table file must be listed in
`platinum.us/main.lsf` (overlay 9's Object list) as well as in
`src/meson.build` — without the `.lsf` line it compiles but its
symbols link as absolute 0 and the table pointer is NULL at
runtime (rift-rp hit this first; the lead's heads-up).

Harness note (for the harness workstream, not this rift):
dwlib's `flag()` uses `NUM_VARS=290`, but the game has
`NUM_VARS=288` (`VARS_END - VARS_START`), so it reads 32 bits
past the true flags base — `flag(0x0A18)` reads true flag
`0x0A38`. The proof works around it with `flag_correct`
(`_vars_flags_addr() + 288*2`); the flag-bit diff across the
two falls confirms the game sets the right bits (0x0A18/0x0A19).
`var()` is unaffected (it uses `VARS_START`, not `NUM_VARS`).
