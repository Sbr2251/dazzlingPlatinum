# DW Ravaged Path puzzle (rift-rp, Phase 1 design)

Arc 2 scene 2.6, progress 14 -> 15. Totem: Hitmonlee. Map:
`MAP_HEADER_DW_RAVAGED_PATH` (596), B1F clone, matrix 291 (`map_data_669/670`).

Target (PUZZLE_PLAN.md section 2, revised curve): difficulty **2**, **15-25
puzzle steps**, **one ordering idea**. This is the first time the player
meets a puzzle mechanic, so it stays gentle: the sigil is on the main
line, the ordering is taught rather than tested, and a missed bridge
bounces the player off instead of dropping them.

New mechanic: **rift sigils** -- stepping on a sigil switches on a group of
stone bridges (ghost props + live walkability, engine-a `DwPuzzleGroup` /
`DwPuzzleSigil`). Combined with: **crumbling scars** (one-use tiles, the
existing `Arc2DwRavagedPath_HandleStep` hook, unchanged).

Engine-a API: `include/overlay009/dw_puzzle.h` (branch `dw/engine-a`,
commit 623ccce7ee). This design is written against that API. **Do not
merge `dw/engine-a` yet** -- implement in Phase 2 when the lead says the
engine has landed in `dwpuzzles`.

## 1. Layout

### Floor (y = 1, `map_data_669`)

Walkable tiles only; `#` is blocked. `E` entry, `C` Cyrus (object),
`J` jump tile (wall on/off), `X` totem coord event (14,23), `T` totem
object (19,22), `o` ghost-prop stepping stone (dead end), `v` chasm lip
(step = fall, marked VOID in the engine table).

```
     x: 10        20
     x: 01234567890123456789
z10  ############.#######
z11  #####v###vvvC#######
z12  #####.....E..##o##o#
z13  #####.####vv########
z14  .#J...##############
z15  .#vvvv##############
z16  .###################
z17  .###################
z18  .###################
z19  .###################
z20  .###################
z21  .#####..############
z22  .#####...T.##o##o##o
z23  .#J.X...############
z24  .####...############
z25  #####.##############
z26  #####.##############
```

Entry: the story side warps the player to (20, 12) facing west (rift
contract). Walk west to (15, 12), south to (15, 14), west to the jump-on
ledge (12, 14). The floor is unchanged from the current map; the only
floor change in Phase 2 is the engine table marking the `v` lips VOID
(so a lip fall restores the checkpoint snapshot instead of resetting
to the initial state).

The west column x = 10, z = 14..24 is a dead strip (no connection to
the ledge: (11, 14) is blocked). The east stones (25, 12), (28, 12)
and the lower stones (23 / 26 / 29, 22) are dead ends, as today. The
solver's floor graph includes all of them, plus the five
bidirectional JUMP_TWICE stone hops (22, 12) <-> (25, 12) <->
(28, 12) and (20, 22) <-> (23, 22) <-> (26, 22) <-> (29, 22), so it
proves none of them is a shortcut. It excludes Cyrus's occupied tile
(22, 11), which his object blocks.

### West wall (x = 11, attr 13)

Rows y = 5..2 (top first), columns z = 13..22. `#` is the top rim and
the two wall trees (drawn, blocked). `.` is the seam. `S` is the sigil,
`B` is a bridge tile (group 0), `*` is a scar tile (one-use).

```
     z: 13       22
     z: 3456789012
y5  ##########
y4  ..####.BB.
y3  ..####.**.
y2  .SB*...**.
```

| Tile | What | Engine / hook |
|---|---|---|
| (11, 2, 14) `S` | Sigil. SET group 0 to 1. Rune decal on the wall face. | `DwPuzzleSigil`, fires once per step onto the tile |
| (11, 2, 15) `B` | Bridge. Socket decal; ghost-prop stone (group 4) when on. | Group 0, on SOLID / off BLOCKED, initial off |
| (11, 4, 20), (11, 4, 21) `B` | Bridge, the top crossing over scar 1. Same decals / props. | Group 0 |
| (11, 2, 16) `*` | Scar 0. Loose-boulder decal + ghost-prop rocks (group 2), as today. | Existing scar hook, unchanged |
| (11, 2, 20), (11, 2, 21), (11, 3, 20), (11, 3, 21) `*` | Scar 1. Decal + rocks (group 3), as today. | Existing scar hook, unchanged |

The wall grid (`platforms` rows in `ravaged_path.json`) is unchanged:
bridge and scar tiles are already walkable (`.` / `*`) in the stock
grid; the engine overrides decide them. No new geometry, no new
surfaces, no change to the jump points.

On the wall: LEFT = +z, RIGHT = -z, UP = climb (+y), DOWN = descend.
DOWN at the bottom row only hops off at the two ends (z = 13, z = 22,
the jump points); at any other z it does nothing.

### Ghost props

| Group | Props | Default |
|---|---|---|
| 0 | B1F clone decor + entry / lower stepping stones (as today) | visible |
| 2 | Scar 0 rocks (1x kind 1), as today | visible |
| 3 | Scar 1 rocks (4x kind 1), as today | visible |
| **4 (new)** | Bridge stones: 3x kind 1 (`PROP_KIND_FLOATING_BLUE_ROCK`) at x = 12, front of the wall face, at (y, z) = (2, 15), (4, 20), (4, 21) | **hidden** (`ghost_default_visible` stays 13 = groups 0, 2, 3) |

Kind 1 is the only prop kind proven to render on this wall face at
x = 12 (the scar rocks use it). Kind 0 (flat stepping-stone slab) is
horizontal and may render edge-on against a vertical face, so it is
not used. Phase 2 must verify in a headless frame strip that the three
group-4 props read as stone ledges on the wall.

### Decals (builder, `build_ravaged_path_map.py`)

Same technique as the scar decals (a quad a hair in front of the wall
face, x = 11 + 0.03). Two new decal sets:

* **Rune decal** on the sigil tile (2, 14).
* **Socket decals** on the three bridge tiles: an empty stone socket
  (dark recess + brackets). When the bridge is off, the socket is what
  the player sees, so an off bridge reads as "no ground here", not as
  drawn ground. When the bridge is on, its ghost-prop stone covers the
  socket. This is the collision-vs-drawn rule for bridges.

Texture choice for the rune / socket decals is open for Phase 2: it
must be a texture in DW texture set 73 that reads as a rune / an empty
socket. Do not reuse `s_land4` (the scar decal texture): it reads as a
boulder, which would make a socket look like ground.

## 2. The mechanic

* Stepping on the sigil sets group 0 ON (sound `SEQ_SE_PL_SYUWA` +
  flash, per engine-a). It stays on for the rest of the visit: the
  sigil is SET (setValue 1), **not** TOGGLE. Stepping on it again
  does nothing -- there is no way to switch a bridge back off in play.
  This is deliberate. With a toggle, switching the group off would
  start the 33-frame fade-out while the tiles stay solid (a normal
  step is 8 frames), so the player could re-enter a fading bridge
  and still be standing on it when it becomes BLOCKED, with no
  frame-fall path (`fallVar = 0`) to catch them. SET removes that
  whole failure mode: the fade-out path is never exercised in this
  rift (the only OFF transition is a fall restore, which happens
  across a warp while the player is at the entry).
* Group 0 on: the three bridge tiles are SOLID and their ghost props
  are shown. Group 0 off: the bridge tiles are BLOCKED (impassable)
  and their props are hidden.
* **Off means BLOCKED, not VOID.** A first-time player who reaches a
  bridge that is off simply cannot step onto it -- no fall, no
  punishment for looking. This is the gentle choice for difficulty 2
  (the engine-a skeleton in the README uses BLOCKED for bridges too).
  Falls in this rift come only from scars and chasm lips, as today.
* Fade-in: the engine's honeycomb rule shows the props at once and
  the tiles hold after the 3-frame fade-in lead. A normal step is 8
  frames, so by the time the player arrives on a bridge whose sigil
  they just pressed, the bridge holds.

## 3. Teaching beat

The sigil is the second tile on the wall, on the main line -- the
player cannot miss it, and the lesson is immediate:

1. Player jumps onto the wall at (2, 13).
2. First step onto the sigil (2, 14): the bridge tile (2, 15) appears
   ahead with a flash and a sound, and Cyrus's teaching line plays
   (once, section 5). Cause and effect are one step apart.
3. Player steps onto the now-solid bridge (2, 15) and on to scar 0.
   Pressing the sigil again does nothing -- the bridges stay on.
4. The top bridges (4, 20), (4, 21) were switched on by the same
   press, so when the player arrives at the top of the seam they are
   already there. The player learns the ordering (sigil before scar)
   before ever needing it under pressure.

## 4. Solution

Optimal path (solver-verified, section 6). Floor: (20, 12) west to
(15, 12), south to (15, 14), west to (12, 14), jump on. Wall:

```
(2,13) -> (2,14) SIGIL [group ON] -> (2,15) BRIDGE -> (2,16) SCAR 0
  -> (2,17) -> (2,18) -> (2,19) fork -> (3,19) -> (4,19)
  -> (4,20) BRIDGE -> (4,21) BRIDGE -> (4,22) -> (3,22) -> (2,22)
  -> hop off to (12,23) -> (13,23) -> (14,23) totem
```

**Puzzle steps: 15** (jump-on .. hop-off inclusive). Total steps
entry -> totem coord: 27 (10 flat entry walk + 15 puzzle + 2 flat
platform walk). The plan's step range counts puzzle steps -- Arc 1
seams is ~15 by the same convention.

**The one ordering idea: press the sigil BEFORE the scar.** Scar 0 is
one-way: once you cross it you cannot walk back to the sigil (stepping
back onto a spent scar is a fall), and the top bridges past the scar
are the ones the sigil switched on. The geometry enforces it for this
first rift -- the first bridge (2, 15) gates scar 0, so you cannot
reach the scar with the group off -- which is what makes it difficulty
2: the ordering is taught, not tested. Later rifts can put the sigil
where the player must remember to press it.

**Fork (existing):** at (2, 19) the bottom row on is scar 1. Stepping
onto scar 1 from the fork traps you: every neighbour except the way
back is another scar tile (stepping onto a second tile of the same
scar is a fall), so you must retreat to the fork and climb instead.
Cyrus's existing fork line still fires at (2, 19).

**Descent (two equal options):** from (4, 21) the player can descend
via (4, 22) -> (3, 22), or via (3, 21) -- a scar-1 tile entered from
above, which holds once and is spent as you step down to (3, 22).
Both are 4 moves to the hop-off; both are legal. Scar 1 is a trap
from below and a legal one-step descent from above. The solver's
optimal path takes the scar descent (a tie-break); the design does not
depend on which one the player picks.

## 5. Cyrus's lines

Existing once-only lines are unchanged: the entry line
(`CyrusFrightened`), the fork line (`CyrusFollowTheSeam` +
`CyrusScarHoldsYouOnce`), the first-fall retry line
(`CyrusAgainSlower`), the halfway shadow (no text), and the whole
totem / calm sequence. Two lines are added; both ASCII, short, in
character. (197 px boxes: the longest line below is 32 chars, inside
the range the existing lines use.)

**Teaching line** -- first step onto the sigil, once. New script entry
appended last in `scripts_dw_ravaged_path.s` (so the existing script
ids do not shift) and a step-hook trigger in the per-map hook, gated
by a new once-only flag (section 7).

```
Cyrus: The rune wakes the stone.
Step on it. The bridge holds.
```
`DWRavagedPath_Text_CyrusSigil`

**Hint after two falls** -- in the fall script. Fall 1 already plays
`CyrusAgainSlower` (gated by `FLAG_ARC2_RIFTA_A`). Fall 2 plays the
hint (gated by a second flag, set when the hint plays) and names the
ordering + the scar rule:

```
Cyrus: Press the rune first.
The scar holds you once.
Then it will not let you back.
```
`DWRavagedPath_Text_CyrusHintAfterTwoFalls`

Falls 3+ play no line. Talking to Cyrus at the entry after the hint
has played repeats the hint (so the player can re-read it); before
that, talking to Cyrus keeps the existing lines.

## 6. Checkpoints, falls, soft-lock freedom

* **Checkpoint:** exactly one -- the entry (20, 1, 12), facing kept.
  `DwPuzzleCheckpoint { 20, 1, 12, -1 }`.
* **Fall:** every fall warps the player to the entry checkpoint and
  leaves the scars intact again (the existing entry-walkway reset).
  Which group state the player comes back to depends on how the fall
  happened, and the asymmetry is part of the design:
  * **Lip fall** (chasm lip, a VOID tile in the engine table): the
    engine step hook sees the VOID tile, marks a fall pending, and
    on the first frame after the warp restores the puzzle to the
    checkpoint snapshot (the group state snapshotted when the player
    last stepped on the entry checkpoint).
  * **Scar fall** (per-map hook): the scar hook starts fall script 2
    directly, so the engine never marks a fall pending; re-entry
    looks like a fresh entry to the engine, which resets the puzzle
    to initial (group OFF, snapshot OFF). This is the correct
    reading of the engine-a API, which has no "mark a fall" entry
    point for a per-map hook.
  Fail cost, per the plan row: fall -> wall resets. With the SET
  sigil, both fall outcomes are trivially re-solvable: step on the
  sigil (SET to ON) and go.
* **Snapshot corner:** the player can walk back to the entry checkpoint
  *before* crossing scar 0 (the wall hop-off at z = 13 exists), which
  re-snapshots the group in its current state -- e.g. ON, if they
  pressed the sigil and walked back. A later lip fall then restores
  ON; a later scar fall resets to OFF. The solver models both fall
  kinds exactly, and its soft-lock proof covers every snapshot value.
* **No soft-lock invariants** (checked exhaustively by the solver,
  section 8):
  * The group can never switch off under the player: the sigil only
    ever sets it ON, and the only OFF transition in the whole rift
    is a fall restore, which happens across a warp while the player
    is at the entry.
  * Every scar tile has a non-scar neighbour to retreat to.
  * From any reachable state there is a path to the totem (solver
    reverse-reachability, fall edges included), so a "stranded"
    state always has a fall (onto a scar / lip) back to the entry.

## 7. Phase 2 implementation (tables, not code, for the rift)

### Engine table (`src/overlay009/dw_puzzle_ravaged_path.c`)

```c
static const DwPuzzleTile sRavagedPathBridgeTiles[] = {
    { 11, 2, 15, 0, 0 },
    { 11, 4, 20, 0, 0 },
    { 11, 4, 21, 0, 0 },
};
static const DwPuzzleGroup sRavagedPathGroups[] = {
    { sRavagedPathBridgeTiles, 3, 4, 0, 0,           /* ghost-prop group 4 */
      DW_PUZZLE_TILE_SOLID, DW_PUZZLE_TILE_BLOCKED, 0, 0 },
    /* tiles, count, ghost group, fadeOut, fadeInLead, on, off, initial, pad */
};
static const DwPuzzleSigil sRavagedPathSigils[] = {
    { 11, 2, 14, DW_PUZZLE_SIGIL_SET, 0, 1, 0 },   /* SET group 0 to 1 */
};
static const DwPuzzleCheckpoint sRavagedPathCheckpoints[] = {
    { 20, 1, 12, -1 },
};
/* Fall lips (coord events), VOID so a lip fall restores the snapshot. */
static const DwPuzzleTile sRavagedPathTiles[] = {
    { 15, 1, 11, DW_PUZZLE_TILE_VOID, 0 },
    { 19, 1, 11, DW_PUZZLE_TILE_VOID, 0 },
    { 20, 1, 11, DW_PUZZLE_TILE_VOID, 0 },
    { 21, 1, 11, DW_PUZZLE_TILE_VOID, 0 },
    { 20, 1, 13, DW_PUZZLE_TILE_VOID, 0 },
    { 21, 1, 13, DW_PUZZLE_TILE_VOID, 0 },
    { 12, 1, 15, DW_PUZZLE_TILE_VOID, 0 },
    { 13, 1, 15, DW_PUZZLE_TILE_VOID, 0 },
    { 14, 1, 15, DW_PUZZLE_TILE_VOID, 0 },
    { 15, 1, 15, DW_PUZZLE_TILE_VOID, 0 },
};
const DwPuzzleTable gDwPuzzleRavagedPathTable = {
    MAP_HEADER_DW_RAVAGED_PATH, 14, 14, 2, 0,   /* progress 14, fall script 2, no frame fall */
    1, 1, 0, 0, 1, 10, 0, 0,                   /* groups, sigils, runes, currents, checkpoints, tiles, pad */
    sRavagedPathGroups, sRavagedPathSigils, NULL, NULL,
    sRavagedPathCheckpoints, sRavagedPathTiles,
};
/* + one extern + one line in the sPuzzleTables[] registry in dw_puzzle.c. */
```

Notes: `fallVar = 0` means no frame fall -- there is no frame-detected
fall in this rift (bridges are BLOCKED when off, never VOID under the
player; the honeycomb-style standing-ground fall does not apply).
`minProgress = maxProgress = 14` gates the table to this scene.

### Other Phase 2 edits

* `tools/distortion_world/ravaged_path.json`: document the sigil +
  bridges (new `sigils` / `bridges` fields) and add the three group-4
  ghost props to `extra_ghost_props`; `ghost_default_visible` stays 13.
  Rebuild with `twarc.py build` and `twarc.py check`.
* `tools/distortion_world/build_ravaged_path_map.py`: add the rune +
  socket decals (section 1). `SCAR_TILES` unchanged.
* `res/field/scripts/scripts_dw_ravaged_path.s`: fall script gets the
  second-fall hint branch; append the sigil teaching script entry
  last (id 8, so existing ids do not shift); `TalkCyrus` repeats the
  hint once shown.
* `src/overlay009/ov9_02249960.c`: per-map step hook keeps the scar
  logic and gains the sigil-teaching trigger (first S1 step, once);
  add the engine glue (`DwPuzzle_HandleStep` first, etc.) per the
  engine-a README. No other ov9 changes.
* `res/text/dw_ravaged_path.json`: two new messages (teaching, hint).
  ASCII only, straight apostrophes.
* `docs/arc2/registry.md`: one block per workstream,
  `FLAG_DW_RIFT_RP_SIGIL_SEEN` and `FLAG_DW_RIFT_RP_HINT_SHOWN` --
  values assigned by the lead (the rift-a block is full; do not take
  flags from another block without the lead). These are the only two
  new flags this design needs.

### Unchanged

Rift contract (entry (20, 12) west; exit warp to Ravaged Path
(19, 46) south; calm sets `VAR_ARC2_PROGRESS` 15 +
`FLAG_TOTEM_HITMONLEE_DEFEATED`), the totem battle and calm sequence,
the existing once-only lines, the scar hook, the fork / halfway
triggers, the chasm-lip coord events, and the exit coord event at
(14, 23) (it is the totem trigger; the exit warp lives in the totem
script after calm).

## 8. Solver evidence

`tools/distortion_world/ravaged_path_solver.py` -- a small standalone
BFS with the semantics of section 6 (same state: position, group,
checkpoint snapshot, scar states; same transitions, including the
exact scar rules and the BLOCKED bridge). Run:

```
python3 tools/distortion_world/ravaged_path_solver.py
```

Result (this commit):

```
states explored: 232
avg branching (out-degree over reachable states): 2.53
optimal total steps (entry -> totem coord): 27
optimal puzzle steps (jump-on .. hop-off): 15 (plan range 15-25: PASS)
falls on optimal path: 0
soft-locked reachable states: 0 (PASS)
sigil disabled, no falls: totem reachable: False, scar 0 reachable: False (PASS)
optimal path presses sigil (step 12) before scar 0 (step 14): PASS
OVERALL: PASS
```

Difficulty reading: 232 reachable states, branching 2.53, one sigil,
one ordering idea, optimal 15 puzzle steps at the bottom of the
15-25 range -- this is a gentle first mechanic, as the revised curve
requires. If Phase 2 playtesting finds it too easy, the sanctioned
tuning is to move the sigil off the main line (e.g. a 1-step spur),
not to add a second mechanic.

## 9. Phase 2 headless proof (checklist, not yet run)

Engine not merged yet, so none of this runs in Phase 1:

* Solver output above (done, Phase 1).
* Harness replay of the solver's solution from entry to totem + calm.
* A fall at each stage (scar 0 re-step, scar 1 from the fork, each
  lip): return to the entry checkpoint. Scar falls reset the group
  to OFF; lip falls restore the checkpoint snapshot (section 6).
  Test the walk-back-then-fall corner for both kinds: snapshot ON,
  then a lip fall (group comes back ON) and a scar fall (group
  comes back OFF).
* Re-entry after a blackout (totem loss): fresh entry resets the
  puzzle; Cyrus's once-only lines do not replay.
* Collision-vs-drawn audit: every walkable tile drawn (bridge props
  when on, sockets when off, rune / scar decals), every VOID tile
  open, no jump landing on an undrawn tile.
* Regression on the other rifts (their tables are untouched; this
  rift's table is gated to progress 14 on its own map).

## 10. Open items for Phase 2

* Rune / socket decal textures (section 1).
* Group-4 bridge props read as stone ledges in a frame strip
  (section 1).
* Lead assigns the two `FLAG_DW_RIFT_RP_*` values (section 7).
* The harness workstream's `tools/distortion_world/emu/solver.py`
  (when it lands): re-express this model in its format and confirm
  the same result; until then this standalone BFS is the model.
