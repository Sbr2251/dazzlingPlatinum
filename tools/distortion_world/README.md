# Distortion World tools (Arc 1 wall-walk puzzle)

The Arc 1 puzzle map `MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS` is a standalone DW map cloned from DW B1F
(Phase 0 of `docs/arc1/revision/puzzle_wall_walk.md`), at DW offset (0,0,0) like the Giratina room.

| file | what |
|---|---|
| `twarc.py` | dump / build / check `res/prebuilt/fielddata/tornworld/tw_arc.narc` (per-map surfaces, jump points, cameras, ghost props) and `tw_arc_attr.narc` (32x32 wall collision grids) |
| `arc1_seams.json` | the puzzle map's record: B1F's record shifted to (0,0,0), its wall grid copied to attr 12 and edited (`rows`, top row first, column = z - 13) |
| `build_arc1_seams_map.py` | builds `map_data_667/668` from B1F's 602/603: walkable chasm lips (fall coord events) and blocked invisible landing zones |

Rebuild after editing: `python3 tools/distortion_world/build_arc1_seams_map.py`, then
`python3 tools/distortion_world/twarc.py build tools/distortion_world/arc1_seams.json` (both idempotent; `--check` /
`check` verify). `twarc.py` looks the map ID up in `generated/map_headers.txt`, so rerun `build` if the header enum
ever moves.

Wall grid (west wall x=11, z 13-22, y 2-5; `.` = walkable). It matches what the stock wall face draws, which is
B1F's own grid: y5 is the top rim, and the `#` block at z 15-18 is where the two wall trees grow out of the face.
A Phase 0 wall face looks the same everywhere, so any other blocked tile would be an invisible wall (and walkable
tiles over the trunks let the player walk through the trees).

    y5  ##########
    y4  ..####....   dead-end corner up the wall at z 19-22
    y3  ..####....   fork scene: first step onto z=19 (any row), see Arc1Seams_HandleStep
    y2  ..........   on at z=13 (from the ledge 12,14), under the trees, off at z=22 (to 12,23)

On the wall: LEFT = +z, RIGHT = -z, UP = climb, DOWN = descend (or hop off at the two ends).
Scripts: `res/field/scripts/scripts_distortion_world_arc1_seams.s`; objects and the fork / idle-hint step hook:
`src/overlay009/ov9_02249960.c` (`sArc1SeamsObjects`, `Arc1Seams_HandleStep`).

## Arc 2 rift-b maps (Route 214, Route 213, Lost Tower; Phase 0)

| map | floor | land data / matrix | tw_arc spec | attr ids |
|---|---|---|---|---|
| `MAP_HEADER_DW_ROUTE_214` | DW B4F clone | `map_data_673/674` (B4F 612/613, edited) + `672` (B4F 614, edited) + stock 615, matrix 293 | `route_214.json` | 21 (east wall), 22 (ceiling) |
| `MAP_HEADER_DW_ROUTE_213` | DW B4F clone, dressed as the Drowned Lake (set-lake) | `map_data_675/676` (B4F 612/613, edited; built by `build_dw_route_213.py`) + `672` + stock 615, matrix 294 | `route_213.json` | 25 (east wall), 26 (ceiling) |
| `MAP_HEADER_DW_LOST_TOWER` | Arc 1 seams (B1F) clone | `map_data_677/678` (667/668, edited), matrix 295 | `lost_tower.json` | 29 (west wall) |

Rebuild (all idempotent; `--check` / `check` verify):

    python3 tools/distortion_world/build_rift_b_maps.py
    python3 tools/distortion_world/build_dw_route_213.py     # DW Route 213 (set-lake): the rowboat, the hanging lake
    for m in route_214 route_213 lost_tower; do python3 tools/distortion_world/twarc.py build tools/distortion_world/$m.json; done

The JSON specs are authoritative for `tw_arc.narc` / `tw_arc_attr.narc`: after merging another workstream's narcs,
rerun the three `build` lines (rift-a's specs touch other members).

B4F maps (both): entry (20,12) facing west on the tree island (B4F 612, with (16..20,12) opened); hop the chasm
(25,22-23) -> (31,22-23) and the pool (32,22-23) -> (38,22-23) (ground-to-ground jump points: kind 4, rot 0,
dx +-6; the pool tiles are blocked so there is no Surf prompt); the corridor to the east wall x=49 (stock B4F jumps:
on at (48,22-23) pressing right, climb, at the top (y=9, z 27-30) pressing up onto the ceiling y=10). On the east
wall UP climbs and RIGHT/LEFT walk +z/-z; on the ceiling UP/DOWN walk +z/-z and RIGHT/LEFT walk +x/-x. Ceiling grid
rows are x = 49 - row (row 0 = x 49), columns z 25..47. The totem fight starts at the ceiling's far end (z >= 45,
`Arc2DwB4F_HandleCeilingEnd` in `src/overlay009/ov9_02249960.c`). Route 214's ceiling is a 6-wide strip;
Route 213's is a serpentine path "under the lake". The B4F ghost props (its rock-maze blocks) are dropped
(`"ghost_props": []`); their triggers stay and toggle nothing.

Lost Tower: the Arc 1 seam unchanged (on from the ledge (12,14), off at (12,23)); the vein room is (12..15,23)
with (15,24..26) blocked so the wall-of-shadow object at (16,23) closes the only way deeper.

### DW Lost Tower: the ghost acts (set-tower, Arc 2 R3, S7)

Still Phase 0 terrain; the set piece lives in `lost_tower.json` (wall grid + ghost props), `build_rift_b_maps.py`
(`LOST_TOWER_OPEN`: the last stone (32,22) and Cyrus's island (37..41, 21..23) in the east block 678), the
`Arc2DwLostTower_*` step/frame hooks and `sArc2DwLostTower*` objects in `src/overlay009/ov9_02249960.c`, and
`scripts_dw_lost_tower.s`. Wall scars are walkable in the grid (`*`): (y2, z14) Hitmonlee's scar, (y2, z20-21) the
false seam (the step hook drops you). Ghost-prop groups: 2 the scar's rock (until Hitmonlee kicks it shut), 3
Vespiquen's light in front of the true seam (y3, z19-22), 4 B1F's own stepping stones east of the deeper ledge
(23/26/29/32, 22; sunk until Lapras lifts them; B1F's jump-twice tiles do the hops), 0 the rest (B1F decor, the false
seam's rocks, and the island: a `PROP_KIND_MEDIUM_ELEVATOR_PLATFORM_1` at (39,22)). B1F's stones at (32,19) and
(35,19) are dropped. Ghost props render fine in front of the wall (x=12); map objects there must not use the wall
rotation (`unk_04 = 1`): one still loaded when the exit's warp animation runs hangs the game.

### DW Route 213: the Drowned Lake (set-lake, Arc 2 R3)

`build_dw_route_213.py` builds 675/676 from the same B4F base (rift-b's `B4F_OPEN` / `B4F_BLOCK` edits included) and
dresses it: a rowboat (terrain, texture `dw213_wood` appended to DW texture set 73) on the old lakebed at
(19.5-21.5, 16.4-19.6); the corridor from the pool to the east wall as a jetty (plank deck, six mooring posts); the ceiling rebuilt as the hanging lake (water around the causeway, the island at
x 45-48, z 44-47 where the Lapras waits, unlit `lake` / animated `lakep.1` water); the void tiles of stock B4F's
dropped floating-rock walkways (20-24, 24-31) blocked. The island and its spur are walkable in `route_213.json` (x 45-48,
z 44-47; spur x 46-47, z 43); the old leg down x 44 past z 42 is water now. The texture set is rebuilt from the current file minus any `dw213_*` entries, so rerun the script after
merging another workstream's texture-set change. Objects (the lakefront sign 0x84, the frame, the card, the Lapras on
the island at (46,46), rotated 180) are in `sArc2DwRoute213Objects`.

## Collision vs drawn geometry (fix2-lost, owner playtest round 2)

Every walkable floor tile of the Arc 2 DW maps must be drawn (map model or a visible ghost prop), every fall trigger
must sit on open void, and no jump tile may land on an undrawn tile. A jump ignores the landing tile's block bit, so
a hop past the drawn stones is closed by making the **jump tiles** plain blocked (0x8000, no behaviour), not the
landing. The builders do it:

| map | builder | what is plain blocked |
|---|---|---|
| DW Ravaged Path | `build_ravaged_path_map.py` (fix2-dwrp) | the last hops, the drawn lips |
| DW Eterna Forest | `build_dw_eterna_forest_map.py` (671 from 667; 679 from 613, fix2-honey) | the drawn lips (16..19,13), (16..18,11); B1F's hop chains (23..30,12) and (21..31,22): this map's tw_arc record is B4F's, so no stones are drawn |
| DW Route 214 / 213 | `build_rift_b_maps.py` `B4F_PLAIN` (673, 675 via `build_dw_route_213.py`, and 672 = 614 for both) | B4F's jumps onto its floating-rock walkways (ghost props, dropped by rift-b) and the walkway tiles |
| DW Lost Tower | `build_rift_b_maps.py` `LOST_TOWER_PLAIN` | the drawn lips; the hop past (28,12); the hops north of (32,22) to B1F's dropped stones |

Fall coord events (`events_dw_*.json`) cover only the open-void lips: (15,11), (19..21,11), (20..21,13), (12..15,15).
`map_data_672` was registered for DW Eterna Forest by R0 but never used there (matrix 292 showed the stock B4F
chunks); it is now the shared fixed copy of B4F's 614. DW Eterna Forest's own second block is `map_data_679` (below). A tile-by-tile audit (model faces, ghost props, permissions,
jumps, coord events) is in `/tmp/a2/fix2/fix2-lost/harness/audit.py`.

### DW Eterna Forest: the honeycomb (fix2-honey, owner playtest round 2)

The honeycomb (ghost-prop group 1, ceiling tiles x 44-45, z 33-36) fades out on a timer and drops the player, but
stock B4F's ceiling slab (chunk 613) stayed drawn where the player's feet are. Matrix 292 is now
`[[671, 679], [614, 615]]`: `map_data_679` (registered in `generated/maps.txt`, `map_data.order` and the data
`meson.build`) is 613 with the slab's underside cut away under the feet, built by `build_dw_eterna_forest_map.py`
(its docstring has the measurements). Note for any other ceiling work: the player sprite hangs upside down with its
feet on the slab underside (h 11, two tiles above the walking plane y=10), so the slab under the feet is the slab
at the player's own tile (0.4 east, 0.4 south with the ceiling camera), while ghost props at y=10 are drawn 2-4
tiles below the slab, round the player's body. The timer (`Arc2DwEternaForest_HandleFrame`, field frames, ~30 a
second): shown and solid 120, fading out but still solid 33 (the props' fade, 31 opacity steps plus 2 frames' lag),
gone 60, shown again 3 frames before it holds. So it holds exactly while it is drawn.


## DW puzzle engine (engine-a): API and data-table usage guide

Engine: `include/overlay009/dw_puzzle.h` + `src/overlay009/dw_puzzle.c`, hooked from
`src/overlay009/ov9_02249960.c` (hook calls only). A map with no puzzle table behaves
exactly as today: the hooks return "no table" and change nothing.

### Writing a puzzle: one table per map

Each rift workstream writes `src/overlay009/dw_puzzle_<map>.c` (tables only) defining
one `const DwPuzzleTable gDwPuzzle<Map>Table`, and adds one extern + one line to the
registry in `dw_puzzle.c` (`sPuzzleTables[]`). Example skeleton (Ravaged Path sigils):

    static const DwPuzzleTile sBridgeTiles[] = { { 11, 3, 20, 0, 0 }, { 11, 3, 21, 0, 0 } };
    static const DwPuzzleGroup sGroups[] = {
        { sBridgeTiles, 2, 3, 0, 0, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_TILE_BLOCKED, 0, 0 },
        /* tiles, count, ghost-prop group (tw_arc id), fadeOut, fadeInLead, on, off, initial, pad */
    };
    static const DwPuzzleSigil sSigils[] = {
        { 12, 1, 14, DW_PUZZLE_SIGIL_TOGGLE, 0, 0, 0 },
        /* x, y, z, kind, targetGroup, setValue, pad */
    };
    static const DwPuzzleCheckpoint sCheckpoints[] = { { 20, 1, 12, -1 } };
    const DwPuzzleTable gDwPuzzleRavagedPathTable = {
        MAP_HEADER_DW_RAVAGED_PATH, 14, 14, 2, VAR_MAP_LOCAL_3,
        1, 1, 0, 0, 1, 0, 0, 0, sGroups, sSigils, NULL, NULL, sCheckpoints, NULL,
    };
    /* mapHeader, min/max VAR_ARC2_PROGRESS (0/0 = any), fallScriptId,
       fallVar, group/sigil/rune/current/checkpoint/tile counts, pad, tables */

Coordinates are DW world tiles (x, y, z) as the ov9 step hook sees them: floor y = 1,
wall y >= 2 at a fixed x, ceiling y = 10. Surfaces use the ov9 numbering
(FLOOR 0, WEST_WALL 1, EAST_WALL 2, CEILING 3); directions are FACE_* as pressed
on the surface the player stands on.

### Modules

- **Tile state.** `tiles[]` are explicit overrides (SOLID / VOID / BLOCKED). The walk
  check consults them on every surface, floor included: BLOCKED is impassable,
  SOLID is walkable even where the stock grid says blocked, VOID is walkable in
  the collision check (so the player can step onto it) and the step/frame hook
  then starts the fall. Explicit overrides win over groups; among groups the
  later group in the table wins.
- **Groups.** A group = tiles + one tw_arc ghost-prop group, on/off. Walkability
  follows the honeycomb rule: turning off starts the props fading at once but
  the tiles stay solid for `fadeOutFrames` (default 33); turning on shows the
  props at once but the tiles hold only after `fadeInLeadFrames` (default 3).
  The glue in ov9 applies the show/hide the engine requests each frame, so a
  group is never drawn-but-not-solid or solid-but-not-drawn. A group with
  ghostPropGroup = DW_PUZZLE_GHOST_GROUP_NONE switches at once.
- **Sigils.** TOGGLE flips the target group; SET sets it to `setValue`;
  MOMENTARY holds the group on while any momentary sigil for it is stood on
  (a holder count, so two momentary sigils for one group behave); RESET
  restores the puzzle to the last checkpoint snapshot without moving the
  player. Every sigil activation plays a sound (SEQ_SE_PL_SYUWA) and starts a
  flash (`gDwPuzzleDebug.flashFrames`). Sigils fire once per step onto the
  tile; momentary sigils release on stepping off.
- **Gravity runes.** A rune tile changes surface in place. The engine returns
  the rune action and the ov9 glue builds a `DistWorldFloatingPlatformJumpPointTemplate`
  from it (target tile, target surface, facing, rot, steps, optional camera
  transition) and starts `CreateJumpOnFloatingPlatformTask` -- the exact
  jump-point surface-change path, with its camera and rotation. The target
  tile must lie in a tw_arc platform of the target surface (the glue resolves
  the platform index; FLOOR targets use index -1); otherwise the rune does
  not fire.
- **Rift currents.** A current tile has a FACE_* drift direction. Stepping on
  one starts a slide: input is locked (player movement paused) and the player
  moves one tile per DW_PUZZLE_SLIDE_FRAMES_PER_TILE (6) field frames until
  blocked (BLOCKED tile, actor block, edge of the surface) or off-current.
  Landing on a current with a different direction turns the slide; landing
  on a sigil / rune / checkpoint ends the slide there and that tile's logic
  runs. Arrow visuals are the rift's tw_arc ghost props (`arrowGhostGroup`).
- **Checkpoints and reset.** Stepping on a checkpoint tile snapshots the
  puzzle (group on/off + sigil states; engine-b actors poll
  `gDwPuzzleDebug.resetGeneration` and restore their own snapshot when it
  changes) and makes it the fall target. Checkpoint 0 should be the map entry.
  A fall restores the player and puzzle state to the last checkpoint without
  losing the run: the step hook marks the fall, the map's existing fall script
  runs its warp, and on the first frame after the warp the engine restores
  the snapshot and respawns the player at the checkpoint. Puzzle state is
  RAM-only; persistent once-only flags (Lost Tower) are never touched, so
  they keep working. A fall the step hook never sees (a coord-event lip not
  marked VOID in the table) still warps, but the puzzle resets to its initial
  state on the fresh load -- mark every fall lip VOID in the table.
  A fresh entry (no fall pending) also resets the puzzle to its initial state.
- **Debug export.** `gDwPuzzleDebug` (in the xMAP): map, active, player tile,
  surface, tile state, group solid/display bits, sigil bits, checkpoint,
  fall count, slide state, last event + frame, flash frames, reset
  generation, and engine-b's stone positions / shadow phase / echo position
  (engine-b writes those fields). The harness reads it; it costs a RAM struct.
- **Engine-b hooks.** `DwPuzzle_SetActorBlock(i, x, y, z, present)`: a stone /
  actor on a tile makes it BLOCKED, and a stone on a current tile plugs the
  current (slides stop before it). `DwPuzzle_ClearActorBlocks()` clears all.
  `DwPuzzle_DirDelta(surface, dir, &dx, &dy, &dz)` is the shared
  FACE_*-to-step table.

### Per-map glue a rift must add (in ov9_02249960.c, hook calls only)

- Step hook: call `DwPuzzle_HandleStep` first; on `fallRequested` start the
  table's `fallScriptId`; on `runeRequested` build the jump template.
- Frame hook (`Arc2Dw_HandleFrame`): call `DwPuzzle_HandleFrame`; apply
  `ghostShowMask` / `ghostHideMask` with Hide/ShowGhostPropGroup; on
  `slideStep` move the player one tile; on `respawnRequested` move the
  player to the checkpoint.
- Collision: `DistWorld_CheckCollisionOnCurrentFloatingPlatform` and
  `DistWorld_DynamicMapFeaturesCheckCollision` (floor path) consult
  `DwPuzzle_QueryTile` -- a map with no table returns DEFAULT and the stock
  grid decides.
- Frame-detected falls need the init-table line and the fall script clearing
  it, as in `DwPuzzleTable.fallVar` above (the Eterna honeycomb pattern).

### Test map (debug only)

`src/overlay009/dw_puzzle_test.c` holds a puzzle table for Ravaged Path that
exercises every module (sigil + group bridge, rune, current, checkpoint,
VOID fall). It is returned only while test mode is on (`gDwPuzzleTestMode`,
set by the harness writing that RAM word, or `DwPuzzle_SetTestMode`). With
test mode off, Ravaged Path has no table and plays exactly as today.
