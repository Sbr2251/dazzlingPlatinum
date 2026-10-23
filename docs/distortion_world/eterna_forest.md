# DW Eterna Forest puzzle design (rift #2, revised curve)

- Map: `MAP_HEADER_DW_ETERNA_FOREST`, Arc 2 scene 2.10, progress 24 -> 26, Vespiquen totem.
- Curve row (revised 2026-10-23, `docs/distortion_world/PUZZLE_PLAN.md` section 2):
  difficulty **3**, gravity runes + honeycomb timing, **at most one sigil**, optimal **25-40 steps**,
  fail cost **fall -> last rune checkpoint**. No non-obvious move is required at this
  difficulty (that bar starts at rift 3); everything the player needs is on the
  path or in the hint after two falls.
- Engine: `include/overlay009/dw_puzzle.h` (engine-a, commit `623ccce7ee`).
  This design is written against that published API. Phase 2 implements one
  table in `src/overlay009/dw_puzzle_eterna_forest.c` plus hook-call-only glue
  in `src/overlay009/ov9_02249960.c`, the JSON/builder edits in "Phase 2 edits",
  and the script edits in "Fall, checkpoints, and Cyrus".
- Solver: `tools/distortion_world/solver_eterna_forest.py` (standalone BFS with
  the engine's semantics). It proves solvability for every honeycomb phase and
  no soft-lock from any reachable state. Difficulty stats are in "Solver stats".

## 1. The idea in one paragraph

The existing route (wall climb, ceiling, honeycomb, totem) is kept, but two
gravity runes shortcut it. Rune A sits on the wall where the player walks
anyway: stepping on it flips wall -> ceiling, teaching the rune safely
(both sides are flat, empty, and flippable back). Past the honeycomb, Rune B
flips ceiling -> floor onto a two-tile floating platform whose landing tile
is carved as the puzzle's one sigil. Landing on the sigil raises a stone
bridge over a gap cut in the ceiling; flipping back up (step off the rune,
step back on) returns the player to the ceiling, and the bridge carries them
to the totem. A fall sends the player back to the last rune checkpoint, not
to the hive. The bridge latches on (a SET sigil), so a fall never costs the
player the bridge, and no state can soft-lock: every rune and the sigil stay
reachable from every checkpoint.

## 2. Geometry: what is already there

All coordinates are DW world tiles. Floor tiles have y = 1, wall tiles
x = 49 with y >= 1, ceiling tiles y = 10. Verified against
`tools/distortion_world/eterna_forest.json` and
`python3 tools/distortion_world/twarc.py dump 597`.

### 2a. Floor (entry walkway + hive strip)

- Entry: (20,12) facing west. Walk west to (17,12); the seam folds the
  player to the hive floor (40,22) facing east.
- Hive strip: (32..48, 22..23) walkable. Walk east to (48,22); pressing
  east jumps onto the wall at (49,1,21).
- The walkway chasm lips fall to the entry (existing coord events). The
  hive is not walkably connected back to the walkway, so lip falls can only
  happen before the puzzle starts; a lip fall resetting the puzzle is
  correct (see section 6).
- A second floor patch exists only at the Rune B platform (section 3):
  (45,1,37) and (46,1,37). Every other floor tile in the ceiling's footprint
  is void. The ceiling-to-floor rune has no pre-existing floor to land on,
  which is why the platform is added (drawn, section 5) rather than assumed.

### 2b. East wall (x = 49, attr 17; rows y = 1 bottom -> 10 top, columns z = 20 -> 29)

```
      z: 20 21 22 23 24 25 26 27 28 29
y=10:  #  #  #  #  #  #  #  .  .  .
y= 9:  #  #  #  #  #  #  #  .  .  .
y= 8:  #  #  #  #  #  #  #  .  .  .
y= 7:  #  #  #  #  #  #  #  .  .  .
y= 6:  #  #  #  #  .  .  .  .  .  .
y= 5:  #  #  #  #  .  .  .  .  .  .
y= 4:  #  #  #  #  .  .  .  .  .  .
y= 3:  .  .  .  .  .  .  .  .  #  #
y= 2:  .  .  .  .  .  .  .  .  #  #
y= 1:  .  .  .  .  .  .  .  .  #  #
legend: . walkable, # blocked. R = Rune A at (y=1, z=25).
```

The wall is a staircase: y1-3 walk z20-27, y4-6 walk z24-29, y7-10 walk
z27-29. The stock jumps survive: (48,22) -> wall (49,1,21); wall
(49,1,21) down -> floor (48,22); wall (49,9,27) up -> ceiling (49,10,27);
ceiling (49,10,27) back -> wall (49,9,27). The long way round (climb to
y9, jump to the ceiling) still works and is the fallback if the player
somehow walks past Rune A: climb at z21-24, cross at y4-6, come down at
z27. It costs 48 steps end to end, which is why Rune A is worth using but
never required for solvability.

### 2c. Ceiling (y = 10, attr 18; rows x = 49 top -> 44 bottom, columns z = 25 -> 47)

```
      z: 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47
x=49:  .  .  .  .  .  .  .  .  #  #  #  #  .  #  #  #  #  #  #  #  #  #  #
x=48:  .  .  .  .  .  .  .  .  #  #  #  #  .  #  #  #  #  #  #  #  #  #  #
x=47:  #  #  .  .  .  .  .  .  #  #  #  #  .  .  .  .  .  .  .  .  .  .  .
x=46:  #  #  .  .  .  .  .  .  #  #  #  #  .  .  .  .  .  .  .  .  .  .  .
x=45:  #  #  .  .  .  .  .  H  H  H  H  .  R  .  G  G  .  .  .  .  .  .  .
x=44:  #  #  .  .  .  .  .  H  H  H  H  .  .  G  G  .  .  .  .  .  .  .
legend: . walkable, # blocked (stock grid), H honeycomb (timed, section 4),
        R Rune B at (45,37), G bridge gap (blocked unless the sigil
        latched the bridge, section 3). The totem trigger is any ceiling
        step at z >= 41.
```

Read it as three regions. Entry strip: x48-49, z25-32. Far side:
x44-47, z37-47. The two are joined only through the honeycomb (x44-45,
z33-36), because the stock grid blocks z33-36 at x46-49 and z38-47 at
x48-49. The bridge gap (x44-47, z39-40) is NEW: it is cut into the
ceiling (section 5) and is BLOCKED until the sigil latches the bridge, so
the far side is split into a honeycomb side (z <= 38) and a totem side
(z >= 41). There is no way round the gap: x48-49 is blocked at z39-47
(stock), and the wall tops out at z29.

## 3. The pieces

### Rune A: wall <-> ceiling, the teaching rune

- Wall tile (49,1,25) <-> ceiling tile (49,10,25). Both tiles are
  walkable in the stock grids, on the player's natural path.
- Walking east along the wall at y1, the player steps on (49,1,25) and
  flips to the ceiling. Nothing bad can happen: the ceiling tile is flat
  and empty, and stepping off it and back on flips back to the wall.
  That is the whole lesson, learned by doing, with no fall anywhere near.
- Rune A is a shortcut, not a gate: it saves the wall climb (9 steps).
  A player who climbs at z21-24 instead still reaches the ceiling by the
  stock jump at (49,9,27).
- Table: two `DwPuzzleRune` entries (one per direction; the API has one
  entry per direction). rot/steps copy the stock wall<->ceiling jumps
  (wall -> ceiling rot -90, ceiling -> wall rot 90, steps 16, facing -1,
  useCamera 0).

### Rune B: ceiling <-> floor, the working rune

- Ceiling tile (45,10,37) <-> floor tile (45,1,37), the west tile of the
  two-tile platform. Table: two `DwPuzzleRune` entries, rot 180 both
  ways (upside-down <-> upright), steps 16, facing -1, useCamera 0.
- The platform is (45,1,37) + (46,1,37) on the floor (y = 1). The east
  tile exists so the player can step off the rune and step back on to
  flip up again (section 7: a rune does not fire on a landing). Both
  platform tiles are made SOLID by the table (explicit overrides; the
  stock floor grid there is blocked) and are drawn by ghost props
  (section 5). From the platform the player cannot walk anywhere else:
  every neighbouring floor tile is void/blocked, so the only way out is
  the rune.
- The platform's west tile (45,1,37) is also the sigil (below). Landing
  on it fires the sigil (section 7).

### The one sigil: SET, latching, on the floor

- Sigil tile: (45,1,37), kind `DW_PUZZLE_SIGIL_SET`, target = bridge
  group, setValue 1. Stepping (or landing) on it sets the bridge group
  ON. It is not a toggle: stepping on it again sets 1 again, so the
  bridge can never be turned off by accident, and a fall can never cost
  the player the bridge.
- Bridge group: 8 tiles, the gap (44..47, 10, 39..40), onState SOLID,
  offState BLOCKED, initialOn 0, ghost-prop group 2 (8 small-platform
  props, one per gap tile; section 5). Walkability follows the honeycomb
  rule (group switches at once here: the props are solid stone, and the
  group is only ever turned on, so no fade timing is needed; fadeOut /
  fadeInLead left 0, which the API maps to the defaults, and the switch
  is effectively immediate for this group because the props appear with
  the flash).
- Why SET and not TOGGLE: at difficulty 3 the sigil is a reward for
  reaching the platform, not a state to manage. A toggle would let the
  player close the bridge under their own feet and strand themself on
  the far side with no way back except a fall; SET makes that impossible.

### Checkpoints

- Checkpoint 0: (20,1,12) facing -1, the map entry (required by the API:
  checkpoint 0 is the map entry).
- Checkpoint 1: (49,10,25) facing -1, the ceiling side of Rune A.
- Checkpoint 2: (45,10,37) facing -1, the ceiling side of Rune B.
- Stepping on (or landing on, section 7) a checkpoint tile snapshots the
  puzzle (bridge on/off) and makes it the fall target. Snapshot contents
  at each checkpoint: CP0 bridge OFF, CP1 bridge OFF, CP2 bridge ON
  (the sigil fired on the floor before the flip back up).
- Fall cost: a honeycomb fall returns the player to the last checkpoint.
  Before any rune: the entry (20,12) via the existing fall path. After
  Rune A: the ceiling (49,25) -- the honeycomb must be re-crossed, but
  the walkway, floor, and wall climb are skipped. After Rune B: the
  ceiling (45,37) -- the bridge is already latched, so the totem is 4
  steps away. This is the curve's "fall -> last rune checkpoint".

## 4. The honeycomb (unchanged, now a checkpointed hazard)

- Honeycomb: ceiling (44..45, 10, 33..36), ghost-prop group 1. Timer
  (existing `Arc2DwEternaForest_HandleFrame`): solid 120 frames, fading
  but still solid 33, gone 60, shown 3 frames before it holds again.
  Cycle 213 field frames. It holds exactly while drawn (fix2-honey).
- Stepping onto it while gone, or standing on it when it goes, drops
  the player: the existing HoneyFall script (entry 5), re-targeted at
  the last checkpoint (section 6).
- Fairness: the solid window (153 frames) is far longer than the 4-step
  crossing (4 steps at ~16 frames a step), and the tile before the
  honeycomb, (45,10,32), is a safe place to wait out the gone phase.
  The solver proves every entry phase works by waiting there (section 8).

## 5. What is drawn (collision-vs-drawn audit, Phase 2 must check)

Every walkable tile must be drawn; every VOID/blocked tile must look
open or blocked. Phase 2 edits:

- `tools/distortion_world/eterna_forest.json`:
  - ghost props, group 0 (always visible): +4 marker props, kind 0
    (`PROP_KIND_SMALL_PLATFORM`): (48,1,25) marking Rune A on the wall
    (wall props sit one tile off the face, cf. Ravaged Path scars),
    (49,10,25) marking Rune A on the ceiling, (45,10,37) marking Rune B
    on the ceiling, and (45,1,37) the Rune B platform / sigil slab.
    +1 platform prop (46,1,37), kind 0. Group 0 goes from 5 to 10 props.
  - ghost props, group 2 (new, bridge): 8 props, kind 0, at
    (44..47, 10, 39..40), one per gap tile. `ghost_default_visible`
    stays 3 (groups 0+1): group 2 starts hidden because the bridge
    starts off.
  - ghost props, group 1 (honeycomb): unchanged, 8 props.
  - Total ghost props 8 (group 1) + 10 (group 0) + 8 (group 2) = 26.
    Stock B4F carried more; Phase 2 confirms the count stays inside the
    stock DW prop/polygon budget (Lost Tower carries 27).
  - Ceiling attr grid (attr 18): gap tiles (44..47, z39-40) are
    unchanged in the JSON (`.`): the table's group offState BLOCKED is
    what closes them, not the stock grid, so the JSON stays the single
    source for the stock grid and the table owns the puzzle state.
- `tools/distortion_world/build_dw_eterna_forest_map.py` (`map_data_679`):
  cut the ceiling slab underside over the gap footprint (tiles 44-47 x
  39-40, shifted by the same feet offset the honeycomb notch uses, so
  the void shows where the feet would be when the bridge is off). The
  bridge props (group 2) draw over the hole when on. This is the same
  technique as the honeycomb notch; do not leave the slab drawn under a
  blocked gap (that would be an invisible wall) and do not leave the gap
  open with no visible hole (that would be a silent fall).
- No other model/permissions edits. The Rune B platform is drawn only
  by its two group-0 props; the floor plane there has no stock model.
  Phase 2 verifies in-game that the platform reads as standing ground
  from the ceiling (it is below the ceiling camera's view of the far
  side) and from the floor after the flip.

## 6. Fall, checkpoints, and Cyrus

- Table fields: `fallScriptId` = 5 (`DWEternaForest_HoneyFall`),
  `fallVar` = `VAR_MAP_LOCAL_2` (the existing init-frame line
  `InitScriptGoToIfEqual VAR_MAP_LOCAL_2, 1, 5` already starts the fall
  script; the fall script already clears the var first).
- `minProgress` / `maxProgress` = 24 / 24 (the puzzle is live at
  progress 24 only; the totem sets 26).
- HoneyFall changes (Phase 2, `scripts_dw_eterna_forest.s`):
  - The warp target is the last checkpoint, not always the hive. The
    engine respawns the player at the checkpoint after the fall warp
    (API: the step hook marks the fall, the fall script runs its warp,
    the engine respawns at the checkpoint on the first frame after the
    warp). The fall script keeps its fade-out / fade-in around the warp,
    so the respawn lands while faded out: one fade, no visible
    double-warp. Phase 2 verifies this on a frame strip.
  - Fall count: the script bumps `VAR_MAP_LOCAL_4` (new, proposed) on
    every honeycomb fall. It is map-local, so re-entering the rift
    resets the count: the hint is per visit.
  - Cyrus's lines: the first honeycomb fall still plays the existing
    once-only line (`FLAG_ARC2_RIFTA_C`, "Wait for it. It comes back.")
    as voice-over after the checkpoint respawn; Cyrus is not on the
    ceiling, so the script drops the FaceSouth / FaceEast movements
    after the warp (they were stage directions for the hive). The
    once-only flags `FLAG_ARC2_RIFTA_C` (honeycomb fall line) and
    `FLAG_ARC2_RIFTA_D` (hive line) keep working exactly as today:
    they gate text, never puzzle state, so the engine's snapshot /
    reset never touches them.
- Cyrus's hint after two falls: on the second honeycomb fall
  (`VAR_MAP_LOCAL_4` == 2), after the respawn, the script plays the new
  hint (two messages, ASCII, 197 px boxes). It plays once per visit
  (exactly on fall 2, not on later falls). New text (append to
  `res/text/dw_eterna_forest.json`):

  `DWEternaForest_Text_CyrusRuneHint`:
  ```
  Cyrus: The runes flip you.
  Wall to ceiling. Ceiling
  to floor. Step off, then
  step on to flip back.
  ```
  `DWEternaForest_Text_CyrusSigilHint`:
  ```
  Cyrus: Under the last rune
  is a sigil. It raises the
  bridge. Cross while the
  honey holds.
  ```
- `DWEternaForest_TalkCyrus` (talking to Cyrus at the entry / hive)
  is unchanged. No new flags are taken: `FLAG_ARC2_RIFTA_A/B` belong
  to Ravaged Path, C/D are already Eterna's, and the checkpoint / fall
  count live in `VAR_MAP_LOCAL_3` / `VAR_MAP_LOCAL_4` only if the
  engine does not already carry them (the engine carries checkpoint
  and fall count in `gDwPuzzleDebug`; the script var is only the
  hint counter). Record any var actually taken in
  `docs/arc2/registry.md` at merge time.

## 7. Semantics the solver assumes (engine contract)

These are the observable rules the solver implements and Phase 2 must
verify against the engine implementation with headless tests (reading
`gDwPuzzleDebug`). If the engine behaves differently, the design still
completes (see the Rune B note below), but the tests must be updated to
match, and the solver re-run.

1. A rune fires when the player takes a walked step onto its tile.
   A landing on a rune tile as the result of a rune flip does NOT fire
   that rune. The player must step off the landing tile and step back
   on to flip again. (Without this, a rune pair ping-pongs forever.)
2. Landing on a tile as the result of a rune flip DOES count as entering
   it for sigils and checkpoints: the Rune B landing fires the sigil,
   and a rune landing on a checkpoint tile sets that checkpoint (with
   the snapshot taken after the sigil fired).
3. A sigil fires once per entry onto its tile (walked step or landing);
   a SET sigil with setValue 1 latches: re-entering sets 1 again.
4. A group that is ON is walkable (SOLID) and drawn; a group that is OFF
   is impassable (BLOCKED) and its props are hidden. For the bridge
   group the switch is effectively immediate (it is only ever turned
   on, with the sigil flash).
5. A fall restores the player to the last checkpoint tile and the
   puzzle snapshot taken there. The snapshot is per checkpoint, not
   global: falling before the sigil restores bridge OFF, falling after
   restores bridge ON.
6. Honeycomb falls go through the same fall path (same checkpoint
   respawn and snapshot restore), even though the honeycomb is detected
   by the existing timer code, not by an engine VOID tile. See
   section 9, open question 1: the Phase 2 glue must make sure the
   engine does not treat the HoneyFall warp as a fresh entry (which
   would reset the bridge and checkpoint).
7. Rune B under the "fires on landing" alternative: if the engine fires
   a rune on a landing too, Rune B becomes touch-and-return (flip down,
   sigil fires, instant flip back up). The bridge still latches, the
   totem is still reachable, and there is no soft-lock; only the floor
   excursion (step off, step back on) never happens. The design does
   not depend on which behaviour ships, but the headless test must pin
   the shipped one.

## 8. Solution (38 steps) and solver stats

Steps are walked moves, surface jumps, and rune flips (a flip is part of
the step onto the rune tile). The fold warp is free (it is the step onto
(17,12)). Waits for the honeycomb phase are not steps: the crossing is
timed, the rest is not.

```
(20,12) F
 1-3  W,W,W -> (17,12) F, fold -> (40,22) F
 4-11 E x8 -> (48,22) F
 12   E (jump) -> (49,1,21) wall
 13-16 +z x4 -> (49,1,25) wall, RUNE A flips -> (49,10,25) ceiling
 17-18 +z x2 -> (49,10,27) ceiling
 19-22 -x x4 -> (45,10,27) ceiling
 23-27 +z x5 -> (45,10,32) ceiling (safe wait tile)
 28-31 +z x4 -> (45,10,36) ceiling, across the HONEYCOMB (timed)
 32   +z -> (45,10,37) ceiling, RUNE B flips -> (45,1,37) floor, SIGIL latches bridge
 33   +x -> (46,1,37) floor (step off the rune)
 34   -x -> (45,1,37) floor, RUNE B flips -> (45,10,37) ceiling
 35-38 +z x4 -> (45,10,41) ceiling, across the BRIDGE, totem trigger (z >= 41)
```

Total: 38 steps, 0 falls, checkpoints used: 1 then 2, honeycomb crossed
once (4 timed steps), sigil used once. The long way round (no Rune A)
is 48 steps. The solver's BFS output (per honeycomb start phase, waits,
state counts, soft-lock proof) is in "Solver stats" below and in
`/tmp/dwp/rift-ef/solver_output.txt`.

### Solver stats

(From `python3 tools/distortion_world/solver_eterna_forest.py`; the
solver's model is section 9's table in code form.)

- Optimal moves: 38 for every honeycomb start phase (0..212). The
  honeycomb never forces an extra move, only waits.
- Worst-case wait: 108 frames (~3.6 s) at the safe tile (45,10,32),
  at start phase 67; worst-case total 716 frames (~23.9 s at 30 fps)
  for the whole route. The player can always wait at (45,10,32); the
  crossing needs 4 steps inside a 153-frame solid window.
- No soft-lock: reverse reachability over the full state graph
  (position x surface x bridge x honeycomb phase x just-landed x
  checkpoint) shows every forward-reachable state can reach the
  totem. Falls included: a fall from any state lands on a checkpoint
  from which the totem is reachable (bridge ON after CP2, OFF-but-
  re-raisable before it).
- Falls in the optimal solution: 0. Deliberate-fall shortcuts: none
  (a fall always moves the player back to a checkpoint behind the
  honeycomb, never forward).

## 9. Phase 2 table (sketch; exact C in `dw_puzzle_eterna_forest.c`)

```c
/* groups[0]: bridge. tiles = (44..47, 10, 39..40), 8 tiles. */
{ sBridgeTiles, 8, 2, 0, 0, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_TILE_BLOCKED, 0, 0 },
/* sigils[0]: SET the bridge on, on the Rune B floor tile. */
{ 45, 1, 37, DW_PUZZLE_SIGIL_SET, 0, 1, 0 },
/* runes: A wall->ceiling, A ceiling->wall, B ceiling->floor, B floor->ceiling. */
{ 49, 1, 25,  49, 10, 25, DW_PUZZLE_SURFACE_CEILING, -1, -90, 16, 0, 0, 0, 0, 0 },
{ 49, 10, 25, 49, 1, 25,  DW_PUZZLE_SURFACE_EAST_WALL, -1, 90, 16, 0, 0, 0, 0, 0 },
{ 45, 10, 37, 45, 1, 37,  DW_PUZZLE_SURFACE_FLOOR, -1, 180, 16, 0, 0, 0, 0, 0 },
{ 45, 1, 37,  45, 10, 37, DW_PUZZLE_SURFACE_CEILING, -1, 180, 16, 0, 0, 0, 0, 0 },
/* checkpoints: entry, Rune A ceiling, Rune B ceiling. */
{ 20, 1, 12, -1 }, { 49, 10, 25, -1 }, { 45, 10, 37, -1 },
/* tiles: explicit overrides for the Rune B platform (stock floor blocked). */
{ 45, 1, 37, DW_PUZZLE_TILE_SOLID, 0 }, { 46, 1, 37, DW_PUZZLE_TILE_SOLID, 0 },
/* table: mapHeader MAP_HEADER_DW_ETERNA_FOREST, progress 24..24,
   fallScriptId 5, fallVar VAR_MAP_LOCAL_2,
   counts groups 1, sigils 1, runes 4, currents 0, checkpoints 3, tiles 2. */
```

Phase 2 glue (`ov9_02249960.c`, hook calls only): call
`DwPuzzle_HandleStep` first in `Arc2DwEternaForest_HandleStep` (before the
map's own honeycomb / totem logic); call `DwPuzzle_HandleFrame` in
`Arc2Dw_HandleFrame`; apply its ghost show/hide masks (bridge group 2);
on `respawnRequested` move the player to the checkpoint. The existing
honeycomb frame code stays and keeps driving ghost group 1. The
existing totem trigger (first ceiling step at z >= 41) stays after the
engine call. Register the table in `dw_puzzle.c` `sPuzzleTables[]`.

### Open questions for engine-a / Phase 2 (not assumed solved)

1. Honeycomb falls and fresh-entry reset (section 7 rule 6): the
   HoneyFall warp must be recognised as a fall, not a fresh entry.
   Candidates: a fall-notification the honeycomb code calls; routing
   the honeycomb fall through `DwPuzzle_HandleStep`; or the glue
   marking fall-pending before starting HoneyFall. Pick one with the
   engine implementation in hand; the headless fall test proves it.
2. Rune landing semantics (section 7 rules 1-2): whether the engine
   fires sigils/checkpoints on a rune landing, and whether it suppresses
   rune re-fire on a landing. Pin with headless tests reading
   `gDwPuzzleDebug` (checkpointIndex, groupBits) after each flip.
3. Respawn timing: the engine respawn after the HoneyFall warp must
   land while faded out (one fade, no visible double-warp). Verify on
   a frame strip.
4. Rune B rot 180 / camera: verify the ceiling->floor flip reads
   correctly in-game (sprite upright on the platform, camera sane);
   adjust rot / useCamera if the capture shows otherwise.
5. Bridge prop read: verify the group-2 small platforms read as a
   bridge over the cut gap, and the gap reads as a hole when off.

### Phase 2 headless proof (from the task brief, run then)

- Replay the solver's 38-step solution from entry to totem and calm.
- Falls at each stage: before any rune (respawn entry), after Rune A
  (respawn ceiling 49,25), after Rune B (respawn ceiling 45,37, bridge
  still on), on the honeycomb (gone-phase step-on and standing-when-
  it-goes), on the bridge gap with the bridge off (blocked, not a fall).
- Use a rune mid-honeycomb: flip Rune A / Rune B while the honeycomb
  is in its gone phase; no fall, no crash; then wait and cross.
- Re-enter after a blackout (lose the totem battle): fresh visit,
  bridge off, checkpoint entry, puzzle re-solvable.
- Collision-vs-drawn audit (section 5): every walkable tile drawn,
  every blocked tile looking open/blocked, gap hole visible when off,
  bridge drawn when on.
- Regression on the other rifts (their entry-to-totem routes unchanged).
