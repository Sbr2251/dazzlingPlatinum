# DW Eterna Forest puzzle design (rift #2, revised curve)

- Map: `MAP_HEADER_DW_ETERNA_FOREST`, Arc 2 scene 2.10, progress 24 -> 26, Vespiquen totem.
- Progress note: the design gates on 24 because the story sets 24
  (`res/field/scripts/scripts_eterna_forest.s`, `SetVar VAR_ARC2_PROGRESS, 24`
  before the entry warp), the DW hooks and coord events gate on 24, and the
  task brief says 24 -> 26. (The rift-contract table once listed entry
  state 25; the lead confirmed 24 and corrected the table on dwpuzzles
  to "24 (as built)" during design review.)
- Flags: the rift's flag block is `FLAG_DW_EF_A..H` (0x0A08-0x0A0F,
  assigned in `docs/arc2/registry.md` on dwpuzzles). Phase 2 takes
  three, renamed in place from `FLAG_UNK_0x0A08..0x0A0A` in
  `generated/vars_flags.txt` (rename in place -- never insert lines:
  that would shift every later flag ID): `FLAG_DW_EF_A/B/C`, the
  HoneyFall hint state machine (section 6).
  All other puzzle state is engine state or map-local vars; do not
  take flags from any other block.
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
flips ceiling -> floor onto a two-tile floating platform whose east
tile is carved as the puzzle's one sigil. Stepping east onto the sigil
raises a stone bridge over a gap cut in the ceiling; stepping west back
onto the rune flips the player up to the ceiling, and the bridge
carries them to the totem. A fall sends the player back to the last rune checkpoint, not
to the hive. The bridge latches on (a SET sigil), so a fall after a
bridge checkpoint never costs the player the bridge -- a fall before
one (backtracking onto the honeycomb after latching) restores the
approach checkpoint's bridge-OFF snapshot, so the player redoes Rune B
and the sigil, which stay reachable. No state can soft-lock: every
rune and the sigil stay reachable from every checkpoint.

## 2. Geometry: what is already there

All coordinates are DW world tiles. Floor tiles have y = 1, wall tiles
x = 49 with y >= 1, ceiling tiles y = 10. Verified against
`tools/distortion_world/eterna_forest.json` and
`python3 tools/distortion_world/twarc.py dump 597`.

### 2a. Floor (entry walkway + hive strip)

- Entry: (20,12) facing west. Walk west to (17,12); the seam folds the
  player to the hive floor (40,22) facing east.
- Hive strip, on foot: (38..48, 22..23) walkable. Walk east to (48,22);
  pressing east jumps onto the wall at (49,1,21). West of the hive, the
  pool (33..37, 22..23) is `WATER_SEA` (tile behaviour 0x15): Surf-only,
  not walkable on foot, so it is outside the solver's floor set. The
  dry tile (32, 22..23) is cut off by the pool and unreachable on foot.
- The walkway chasm lips fall to the entry (engine VOID tiles in the
  puzzle table; the old coord events were removed). The
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
y= 2:  #  #  #  #  #  #  .  .  #  #   <- G: the rune gate (rock rubble)
y= 1:  .  .  .  .  .  .  .  .  #  #
legend: . walkable, # blocked. R = Rune A at (y=1, z=25).
```

The wall is a staircase: y1 walk z20-27, y2 walk z26-27 only, y3 walk
z20-27, y4-6 walk z24-29, y7-10 walk z27-29. The G row is the rune
gate: (49, y=2, z=20..25) is BLOCKED and drawn as rock rubble (ghost
props, section 5), so the wall cannot be climbed past y=1 without
Rune A. Every climb column at z <= 25 is closed, and reaching z >= 26
on the bottom row means stepping on the rune at z=25 first. Rune A is
therefore REQUIRED, not a shortcut: the only way from the floor to
the ceiling is the rune (the stock jump at (49,9,27) is the return
path: a ceiling player can jump back down to the wall). The stock
jumps survive: (48,22) -> wall (49,1,21); wall (49,1,21) down ->
floor (48,22); wall (49,9,27) up -> ceiling (49,10,27); ceiling
(49,10,27) back -> wall (49,9,27).

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
- Rune A is REQUIRED: the rune gate (section 2b) closes every climb
  past y=1, so the only way from the floor to the ceiling is the rune.
  Both rune transformations are therefore required: wall <-> ceiling
  here, ceiling <-> floor at Rune B. A player returning from the
  ceiling to the floor flips back to the wall at Rune A, walks west
  on y1 to (49,1,21), and jumps down -- the rune never strands them,
  because walking AWAY from it on y1 never re-triggers it.
- Table: two `DwPuzzleRune` entries (one per direction; the API has one
  entry per direction). rot copies the stock wall<->ceiling jumps
  (wall -> ceiling rot -90, ceiling -> wall rot 90, facing -1,
  useCamera 0). steps is 32, not the stock 16: the jump task moves Y
  at most one half-tile per frame, so a 9-tile Y change needs > 18
  steps; 16 steps landed the player a tile short, stranded at
  (49,9,25) on the ceiling (found in headless testing).

### Rune B: ceiling <-> floor, the working rune

- Ceiling tile (45,10,37) <-> floor tile (45,1,37), the west tile of the
  two-tile platform. Table: two `DwPuzzleRune` entries, rot 180 both
  ways (upside-down <-> upright), steps 32 (same jump-task Y cap as
  Rune A), facing -1, useCamera 0.
- The platform is (45,1,37) + (46,1,37) on the floor (y = 1). The west
  tile is the rune landing; the east tile is the sigil (below). The
  flow is: flip down onto (45,37), step east onto the sigil (46,37),
  step west back onto the rune (45,37), flip up. The platform FORCES
  the sigil visit: from the landing tile the only walkable step is
  east to the sigil, and from the sigil the only walkable step is
  west back to the rune. No landing activation is assumed anywhere
  (section 7): the sigil fires on the walked step east, the flip up
  fires on the walked step west.
- Both platform tiles are made SOLID by the table (explicit overrides;
  the stock floor grid there is blocked) and are drawn by ghost props
  (section 5). From the platform the player cannot walk anywhere else:
  every neighbouring floor tile is void/blocked, so the only way out is
  the rune.

### The one sigil: SET, latching, on the floor

- Sigil tile: (46,1,37), kind `DW_PUZZLE_SIGIL_SET`, target = bridge
  group, setValue 1. A walked step onto it sets the bridge group ON.
  It is not a toggle: stepping on it again sets 1 again, so the
  bridge can never be turned off by accident. A fall AFTER a bridge
  checkpoint never costs the bridge (that checkpoint's snapshot has
  it ON); a fall BEFORE one -- backtracking onto the honeycomb after
  latching, before stepping on a z=39 tile -- restores the approach
  checkpoint's bridge-OFF snapshot, so the player redoes Rune B and
  the sigil. That redo is short (approach -> honeycomb -> Rune B ->
  sigil), the rune and sigil stay reachable from the approach
  checkpoint, and it is never a soft-lock.
- Bridge group: 8 tiles, the gap (44..47, 10, 39..40), onState SOLID,
  offState BLOCKED, initialOn 0, ghost-prop group 2 (8 small-platform
  props, one per gap tile; section 5). The group's fade fields are 0,
  which the API maps to the defaults: fadeOut 33, fadeInLead 3. The
  group only ever turns on, and the 3-frame fade-in lead is harmless:
  80 frames (step west 16, flip up 32, two steps south 32)
  elapse between the sigil and the first bridge step. The group only
  ever turns off via a checkpoint restore (a fall to a checkpoint whose
  snapshot has bridge OFF): then the props fade for 33 frames while
  the tiles stay solid (the honeycomb rule), and the minimum re-solve
  from the approach checkpoint to the gap is 208 frames (4 honeycomb
  steps 64 + flip down 48 + sigil step 16 + flip up 48 + 2 steps south
  32), so the fade is over before the player can reach the gap again.
- Why SET and not TOGGLE: at difficulty 3 the sigil is a reward for
  reaching the platform, not a state to manage. A toggle would let the
  player close the bridge under their own feet and strand themself on
  the far side with no way back except a fall; SET makes that impossible.

### Checkpoints

Every checkpoint tile is a guaranteed WALKED, non-rune tile, so
checkpoint activation needs no landing semantics at all (section 7).
The table has 7 checkpoints (max 8):

- Checkpoint 0: (20,1,12) facing -1, the map entry (required by the API:
  checkpoint 0 is the map entry). Snapshot: bridge OFF.
- Checkpoints 1-2: (44,10,32) and (45,10,32) facing -1, the two
  honeycomb-approach tiles. Every first honeycomb entry steps on one of
  them (the honeycomb can only be entered from the north: x46-49 at
  z33-36 is blocked stock, and the south side is unreachable before a
  first crossing). Snapshot: the bridge as it was on arrival (OFF the
  first time; ON if the player walks back across later).
- Checkpoints 3-6: (44..47,10,39) facing -1, the four bridge tiles at
  z=39. Every crossing steps on one of them (the gap must be crossed
  from z=38 to z=39; x48-49 is blocked stock). Snapshot: always ON,
  by construction: the tile is only steppable while the bridge is on.
- Stepping on a checkpoint tile snapshots the puzzle (bridge on/off)
  and makes it the fall target.
- Fall cost: a honeycomb fall returns the player to the last checkpoint.
  Before the honeycomb: the entry (20,12) via the existing fall path.
  After the approach: the approach tile (44/45,32) -- the honeycomb
  must be re-crossed, but the walkway, floor, and wall climb are
  skipped. After the bridge: the bridge tile (x,39) -- the bridge is
  already latched, so the totem is 2 steps away. This is the curve's
  "fall -> last rune checkpoint".

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
  - Wall attr grid (attr 17): add explicit `rows` -- BOTTOM-first
    (y=1 first), because for `EAST_WALL` the grid index is
    v = y - y0 (contrast the west wall, where v runs top-first):
    y1 `"........##"`, y2 `"######..##"` (the rune gate: z20-25
    blocked), y3 `"........##"`, y4-y6 `"####......"`,
    y7-y10 `"#######..."`. The ceiling-side rows above y2 are
    unchanged from stock B4F; only the gate row differs.
  - ghost props, group 0 (always visible):
    +6 gate props, kind 1 (`PROP_KIND_FLOATING_BLUE_ROCK`): rock
    rubble at (48, 2, 20..25), one tile off the wall face (cf.
    Ravaged Path scars), drawing the y=2 blockage. They read as
    rubble blocking the climb, not as steps.
    +4 marker props, kind 0 (`PROP_KIND_SMALL_PLATFORM`):
    (48,1,25) marking Rune A on the wall (wall props sit one tile
    off the face), (49,10,25) marking Rune A on the ceiling,
    (45,10,37) marking Rune B on the ceiling, and (45,1,37) the
    Rune B platform landing.
    +1 platform prop (46,1,37), kind 0: the sigil slab.
    Group 0 goes from 5 to 16 props.
  - ghost props, group 2 (new, bridge): 8 props, kind 0, at
    (44..47, 10, 39..40), one per gap tile. `ghost_default_visible`
    stays 3 (groups 0+1): group 2 starts hidden because the bridge
    starts off.
  - ghost props, group 1 (honeycomb): unchanged, 8 props.
  - Total ghost props 8 (group 1) + 16 (group 0) + 8 (group 2) = 32.
    Stock DW records carry up to 49 ghost props (map 576 in the
    current `twarc.py dump`), so 32 is inside the stock budget;
    Phase 2 confirms the polygon budget the same way (small
    platforms and rocks are the cheapest prop kinds).
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
  script; the fall script already clears the var first). BOTH
  honeycomb fall paths must mark the fall pending SYNCHRONOUSLY, by
  calling `DwPuzzle_NotifyFall` (required new API, section 9, open
  question 1) at fall detection, before starting HoneyFall: the
  frame path (standing on the honeycomb when it goes) when it sets
  `fallVar`, and the step-hook path (stepping onto a gone honeycomb),
  which today starts HoneyFall directly. Polling `fallVar` from
  the engine frame hook does NOT suffice: HoneyFall clears
  `fallVar` first thing, so the engine frame poll is not guaranteed
  to run between the set and the clear -- a race. `fallVar` stays
  as the script trigger (the init-frame line starts HoneyFall);
  `DwPuzzle_NotifyFall` is the engine's fall-pending signal, and
  it must survive HoneyFall clearing `fallVar`. A fall path that
  does not notify would reload as a fresh entry and wipe the
  bridge state and checkpoint.
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
  - Fall count / hint state machine: see the hint paragraph below
    (FLAG_DW_EF_A/B/C).
  - Cyrus's lines: the first honeycomb fall still plays the existing
    once-only line (`FLAG_ARC2_RIFTA_C`, "Wait for it. It comes back.")
    as voice-over after the checkpoint respawn; Cyrus is not on the
    ceiling, so the script drops the FaceSouth / FaceEast movements
    after the warp (they were stage directions for the hive). The
    once-only flags `FLAG_ARC2_RIFTA_C` (honeycomb fall line) and
    `FLAG_ARC2_RIFTA_D` (hive line) keep working exactly as today:
    they gate text, never puzzle state, so the engine's snapshot /
    reset never touches them.
- Cyrus's hint after two falls: on the second honeycomb fall,
  after the respawn, the script plays the new hint (two messages,
  ASCII, 197 px boxes). It plays once per save (exactly on fall 2,
  not on later falls), like the other Cyrus once-only lines. Counting
  is a 3-flag state machine in HoneyFall, because a map-local var
  CANNOT count falls: `ClearLocalFlags` wipes all `VAR_MAP_LOCAL_*`
  on every DW map load, including the fall warp itself, so a counter
  would read 1 on every fall. `FLAG_DW_EF_B` = a honeycomb fall has
  happened and the hint has not played yet; `FLAG_DW_EF_A` = the hint
  is pending this fall (set before the warp on the second fall,
  cleared after the hint plays); `FLAG_DW_EF_C` = the hint has
  played. New text (append to
  `res/text/dw_eterna_forest.json`):

  `DWEternaForest_Text_CyrusRuneHint` (page break `\r` after line 2,
  as in the existing texts: each page holds two lines):
  ```
  Cyrus: The runes flip you.
  Wall to ceiling. Ceiling
  to floor. Step off, then
  step on to flip back.
  ```
  Stored as `"Cyrus: The runes flip you.\nWall to ceiling. Ceiling\rto floor. Step off, then\nstep on to flip back."`.
  `DWEternaForest_Text_CyrusSigilHint` (the sigil is the platform tile
  beside the rune's floor tile, not under it):
  ```
  Cyrus: Beside the rune sits
  a sigil. It raises the
  bridge. Cross while the
  honey holds.
  ```
  Stored as `"Cyrus: Beside the rune sits\na sigil. It raises the\rbridge. Cross while the\nhoney holds."`.
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
`gDwPuzzleDebug`). Rules 1-5 are designed to follow from the published
API alone: every activation in this puzzle is a WALKED step onto a
tile, and no sigil or checkpoint tile is a rune landing tile, so the
design assumes no landing activation for anything. Rule 6 is the one
place the design needs a single engine semantic beyond the letter of
the published API, and rule 7 is a hard engine requirement.

1. A rune fires when the player takes a walked step onto its tile.
2. A landing on a tile as the result of a rune flip fires NOTHING:
   not the rune, not a sigil, not a checkpoint. The player must step
   off the landing tile and step back on to flip again.
3. A sigil fires once per walked step onto its tile; a SET sigil with
   setValue 1 latches: re-entering sets 1 again.
4. A checkpoint sets on a walked step onto its tile, snapshotting the
   puzzle (bridge on/off) at that moment.
5. A group that is ON is walkable (SOLID) and drawn; a group that is OFF
   is impassable (BLOCKED) and its props are hidden. Bridge timing:
   fadeInLead 3 frames after the sigil (covered by the 64+ frames
   before the first bridge step), fadeOut 33 frames on a restore-off
   (covered by the walk back from the respawn).
6. A fall restores the player to the last checkpoint tile and the
   puzzle snapshot taken there. The snapshot is per checkpoint, not
   global: falling before reaching a bridge checkpoint restores the
   last checkpoint's snapshot (bridge OFF at the entry / approach
   checkpoints, even if the sigil has already been latched -- that
   is the backtrack redo); falling after stepping on a bridge
   checkpoint restores bridge ON.
7. REQUIRED: a rune must not re-fire on the landing its own flip
   produced. If the engine's step hook runs on a rune landing and
   would fire the rune there, the engine (or glue) must suppress
   exactly that re-fire. Without this, a rune pair ping-pongs forever
   and Rune B is unusable: the player could never stay on the floor
   long enough to walk to the sigil. This is not an open question:
   Phase 2 must demonstrate it headlessly (flip Rune B down, show the
   player stays on the floor platform, `gDwPuzzleDebug` shows one
   `DW_PUZZLE_EVENT_RUNE` for the flip down, and no second rune event
   until the player steps off and back on).
8. Honeycomb falls go through the same fall path (same checkpoint
   respawn and snapshot restore), even though the honeycomb is detected
   by the existing timer code, not by an engine VOID tile. This
   needs an engine change, specified in section 9, open question 1,
   applied to BOTH fall paths: the frame path (standing when the
   honeycomb goes) and the step path (stepping onto a gone
   honeycomb), which today starts `HoneyFall` without marking the
   fall pending. The Phase 2 glue must make sure the engine does
   not treat either HoneyFall warp as a fresh entry (which would
   reset the bridge and checkpoint).

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
 32   +z -> (45,10,37) ceiling, RUNE B flips -> (45,1,37) floor
 33   +x -> (46,1,37) floor, SIGIL latches the bridge
 34   -x -> (45,1,37) floor, RUNE B flips -> (45,10,37) ceiling
 35-38 +z x4 -> (45,10,41) ceiling, across the BRIDGE, totem trigger (z >= 41)
```

Total: 38 steps, 0 falls, checkpoints used: approach then bridge,
honeycomb crossed once (4 timed steps), sigil used once. There is no
long way round any more: the rune gate (section 2b) closes the wall
climb, so a rune-free route to the ceiling does not exist (the solver
confirms with three isolated floods: all rune tiles blocked,
Rune A tiles blocked with Rune B live, and Rune B tiles blocked
with Rune A live all fail to reach the goal -- each rune is
individually required, and blocking the tiles (not merely
disabling the flip) is the correct model, since a player who
could walk through a rune tile as plain ground could pass the
gate without flipping). The solver's output (per honeycomb
start phase, waits, state counts, soft-lock proof) is in "Solver
stats" below and in `/tmp/dwp/rift-ef/solver_output.txt`.

### Solver stats

(From `python3 tools/distortion_world/solver_eterna_forest.py`; the
solver's model is section 9's table in code form.)

- Optimal moves: 38 for every honeycomb start phase (0..212). The
  honeycomb never forces an extra move, only waits.
- Worst-case wait: 172 frames (~5.7 s) at the safe tile (45,10,32),
  at start phase 3; worst-case total 876 frames (~29.2 s at 30 fps)
  for the whole route (38 moves at 16f + 3 flips at +32f each +
  waits). The wait rule is conservative: the player waits until the
  whole crossing occupancy (4 crossing moves + the 48-frame flip
  exit = 112 frames) fits inside the 153-frame solid window, so the
  result holds whether the engine updates the player's tile at step
  start or at step end.
- No soft-lock: forward reachability over the abstract state graph
  (15,447 reachable states: position x surface x bridge x just-landed
  x checkpoint x per-checkpoint snapshots) plus reverse Dijkstra
  from the goal states shows every forward-reachable state can reach
  the totem abstractly. Realization: a shortest abstract path is
  simple, so its honeycomb runs are short; the solver verifies the
  EXACT weighted occupancy of every run on every reachable state's
  shortest tree path -- 16f per honeycomb position plus the exit
  move (16f walk, 48f flip exit); a run ending in a fall needs no
  bound, since the fall lands on a checkpoint (a safe tile) whose
  own path is realizable the same way. Max occupancy observed: 112
  frames, inside one 153-frame solid window; the player aligns a
  run by waiting on the safe tile before it. Falls included: a
  fall from any state lands on a checkpoint from which the totem is
  reachable (bridge ON after a bridge checkpoint, OFF-but-
  re-raisable before it, via the backtrack redo).
- Falls in the optimal solution: 0. Deliberate-fall shortcuts: none
  (a fall always moves the player back to a checkpoint behind the
  honeycomb, never forward).

## 9. Phase 2 table (sketch; exact C in `dw_puzzle_eterna_forest.c`)

The shipped table is `src/overlay009/dw_puzzle_eterna_forest.c`
(`gDwPuzzleEternaForestTable`); this sketch mirrors it. v2 API notes:
base terrain is `GROUND` (not `FLOOR`, a floating platform); every
entry carries a surface; tiles carry a per-tile fallScriptId; the
table carries `testOnly`. The table is registered in `dw_puzzle.c`
`sPuzzleTables[]` after the test tables (a test table still wins in
test mode) and the file is listed in `src/meson.build` AND in
`platinum.us/main.lsf` overlay 9 (meson alone compiles the .o but
the linker script decides what lands in the overlay -- without the
main.lsf line the table symbol linked as 0 and the engine never
activated in production; caught by reading `sPuzzleTables` from
live RAM).

```c
/* groups[0]: bridge. tiles = (44..47, 10, 39..40) on CEILING, 8 tiles.
   Fade fields 0 -> defaults (fadeOut 33, fadeInLead 3); see section 3. */
{ sBridgeTiles, 8, 2, 0, 0, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_TILE_BLOCKED, 0, 0 },
/* sigils[0]: SET the bridge on, on the EAST platform tile (walked step), GROUND. */
{ 46, 1, 37, DW_PUZZLE_SIGIL_SET, 0, 1, DW_PUZZLE_SURFACE_GROUND },
/* runes: A wall->ceiling, A ceiling->wall, B ceiling->ground, B ground->ceiling.
   steps 32 (jump-task Y cap; section 3). */
{ 49, 1, 25,  49, 10, 25, DW_PUZZLE_SURFACE_EAST_WALL, DW_PUZZLE_SURFACE_CEILING,
  -1, 0, -90, 32, 0, 0, 0, 0, 0 },
{ 49, 10, 25, 49, 1, 25,  DW_PUZZLE_SURFACE_CEILING, DW_PUZZLE_SURFACE_EAST_WALL,
  -1, 0, 90, 32, 0, 0, 0, 0, 0 },
{ 45, 10, 37, 45, 1, 37,  DW_PUZZLE_SURFACE_CEILING, DW_PUZZLE_SURFACE_GROUND,
  -1, 0, 180, 32, 0, 0, 0, 0, 0 },
{ 45, 1, 37,  45, 10, 37, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_SURFACE_CEILING,
  -1, 0, 180, 32, 0, 0, 0, 0, 0 },
/* checkpoints (7): entry; honeycomb approach x44, x45; bridge x44-47 at z39. */
{ 20, 1, 12, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
{ 44, 10, 32, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
{ 45, 10, 32, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
{ 44, 10, 39, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
{ 45, 10, 39, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
{ 46, 10, 39, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
{ 47, 10, 39, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
/* tiles (8): Rune B platform SOLID (GROUND) + 6 entry-lip VOID (GROUND, fall script 2). */
{ 45, 1, 37, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
{ 46, 1, 37, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
{ 15, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
{ 19, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
{ 20, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
{ 21, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
{ 20, 1, 13, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
{ 21, 1, 13, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
/* table: mapHeader MAP_HEADER_DW_ETERNA_FOREST, progress 24..24,
   fallScriptId 5, fallVar VAR_MAP_LOCAL_2,
   counts groups 1, sigils 1, runes 4, currents 0, checkpoints 7, tiles 8,
   testOnly 0. */
```

Glue (`ov9_02249960.c`): engine-a already ships the generic glue --
`DwPuzzle_HandleStep` runs before the per-map chain in `ov9_0224A71C`,
`DwPuzzle_HandleFrame` runs in `Arc2Dw_HandleFrame` (ghost masks,
slide, respawn), and `DwPuzzle_NotifyFall` is wired on both honeycomb
fall paths. This rift needed no per-map glue changes: the existing
honeycomb frame code keeps driving ghost group 1, and the existing
totem trigger (first ceiling step at z >= 41) runs after the engine
step hook.

### Open questions resolved in Phase 2

1. DELIVERED by engine-a: honeycomb falls and fresh-entry reset
   (section 7 rule 8). The published API has no way for the existing
   honeycomb timer code (which detects the fall, not an engine VOID
   tile) to mark the fall pending, and the usage guide says an
   unrecognised fall resets the puzzle as a fresh entry. That would
   wipe the bridge state and the checkpoint, breaking the design's
   core promise. REQUIRED: a new synchronous API,
   `DwPuzzle_NotifyFall(FieldSystem *)`, which the honeycomb code
   calls at fall detection on BOTH paths -- the frame path
   (standing on the honeycomb when it goes) and the step-hook path
   (stepping onto a gone honeycomb), which today starts HoneyFall
   directly -- before starting HoneyFall. The engine records
   fall-pending in RAM at the call; it must survive HoneyFall
   clearing `fallVar` (which stays as the script trigger). The
   earlier polling idea (engine polls `fallVar`) is REJECTED: it
   races, because HoneyFall clears `fallVar` first thing and the
   engine frame poll is not guaranteed to run between the set and
   the clear. Fallback if NotifyFall is refused: the honeycomb
   becomes an engine timer group. Phase 2 is blocked until
   engine-a confirms NotifyFall (or the timer-group fallback)
   lands; the headless fall tests (both honeycomb fall paths,
   bridge ON + bridge checkpoint surviving) prove it.
2. DELIVERED by engine-a: no rune re-fire on a rune landing
   (the landing rule: a landing fires NOTHING). Pinned by the
   headless rune test (one flip per step onto a rune; the player
   stays on the floor platform after flipping down).
3. Respawn timing: the engine respawn after the HoneyFall warp must
   land while faded out (one fade, no visible double-warp). Verify on
   a frame strip.
4. Rune B rot 180 / camera: verify the ceiling->floor flip reads
   correctly in-game (sprite upright on the platform, camera sane);
   adjust rot / useCamera if the capture shows otherwise.
5. Bridge prop read: verify the group-2 small platforms read as a
   bridge over the cut gap, and the gap reads as a hole when off.
6. Rune gate read: verify the y=2 rock rubble reads as a blocked
   climb (not as steps), and that a rune-free route to the ceiling
   does not exist in-game (walk the wall: every climb past y=1 is
   blocked; the only way up is Rune A).

### Phase 2 headless proof (from the task brief, run then)

- Replay the solver's 38-step solution from entry to totem and calm.
- Falls at each stage: before the honeycomb (respawn entry),
  after the honeycomb approach (respawn (44/45,10,32), bridge OFF),
  after the bridge (respawn (x,10,39), bridge still ON), on the
  honeycomb via BOTH paths (gone-phase step-on, which must also set
  `fallVar`, and standing-when-it-goes), on the bridge gap with the
  bridge off (blocked, not a fall).
- Backtrack redo: latch the bridge, walk back onto the honeycomb
  while gone, fall -> respawn approach, bridge OFF (the approach
  snapshot); re-solve via Rune B and the sigil; no soft-lock.
- Use a rune mid-honeycomb: flip Rune A / Rune B while the honeycomb
  is in its gone phase; no fall, no crash; then wait and cross.
- Re-enter after a blackout (lose the totem battle): fresh visit,
  bridge off, checkpoint entry, puzzle re-solvable.
- Collision-vs-drawn audit (section 5): every walkable tile drawn,
  every blocked tile looking open/blocked, gap hole visible when off,
  bridge drawn when on.
- Regression on the other rifts (their entry-to-totem routes unchanged).
