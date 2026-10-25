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

## DW puzzle actors (engine-b): stones, shadow, echo, totem-echo pads

Design: `docs/distortion_world/actors_design.md`. Code: `src/overlay009/dw_puzzle_actors.c` +
`include/overlay009/dw_puzzle_actors.h`, on engine-a's core API (`include/overlay009/dw_puzzle.h`).
Build order: stones, shadow and pads first; echo self last (Arc 3 Aggron rift, no Arc 2 user).
Rift workstreams own their actor tables (`dw_puzzle_<map>.c`); engine-b owns the actor code.

- **Surfaces are explicit.** Every actor tile carries its surface (FLOOR / WEST_WALL /
  EAST_WALL / CEILING / GROUND); `(x, y, z)` alone does not identify a tile.
- **Stones.** Pushed one tile by `DwActors_TryPush`, which the glue's collision path calls
  *before* allowing a step onto a stone tile, for voluntary walking only (never for slides).
  A stone pushed into a designated edge falls 12 frames and lands as a SOLID tile on the
  surface below. Stones affect walkability only through engine-a actor tiles
  (`DwPuzzle_SetActorTile`): RESTING = BLOCKED (plugs currents), LANDED = SOLID (walkable
  terrain, not pushable), FALLING = no tile. A reset (fall / catch / RESET sigil) restores
  the checkpoint snapshot; `DwActors_ResetStones` is the explicit to-start reset.
- **Shadow.** One slow, readable patrol per map, authored as `DwActors_MakeShadowLane(start,
  end, beat)` (two endpoints + a beat; Lost Tower: beat 45-60, one lane). Overlap = caught:
  Giratina cry, 30 frozen frames, then `DwPuzzle_RequestCheckpointRespawn` (latched, once)
  and the checkpoint snapshot restores (snapshot holds phase + pingpong direction + beat
  counter + grace). A 60-frame watchdog self-heals if engine-a never respawns.
- **Echo self.** Desired tile = mirror of the player on a paired surface; if the desired tile
  is not enterable the echo hides (never last-valid); it never blocks the player. Echo sigils
  fire via `DwPuzzle_PressSigil` as occupant ECHO when the echo *enters* their tile; hiding
  releases its momentary holds. Arc 3 only.
- **Totem-echo pads.** A pad tile *is* an engine-a sigil tile. Step on a pad ->
  `DW_ACTOR_EVENT_PAD_READY` -> the glue **must skip** engine-a's step handling for that
  step -> the rift script shows Yes/No -> `DwActors_ResolvePad` fires the sigil via
  `DwPuzzle_PressSigil` and returns `CUTIN` (Resonator ghost cut-in) or `CARRY_REQUESTED`
  (Skarmory: the script plays the carry with the Lost Tower Act 4 machinery; actors never
  step the player over VOID). Gated on `FLAG_TOTEM_*_DEFEATED`; a denied pad (or a pad
  with no sigil) is not marked used. Lost Tower visit 1 registers no actor table (existing
  scripted acts run); visit 2 registers the shadow + pads, and the old acts step aside
  automatically via `DwActors_IsActive()`.
- **Objects.** Actor MapObjects are all `MAP_OBJ_STATUS_18` (non-colliding), never use the
  wall-rotation animation. Two exit paths: `DwActors_VisualsExit` on map unload (deletes
  objects, keeps core state for same-map reloads) and `DwActors_OnExit` on departure (full
  teardown). Actors consume zero ghost-prop templates/groups. Budgets: <= 6 MapObjects.
- **Engine-a API.** Actors use the landing API (`QueryTile` with surface, `SetActorTile`,
  `PressSigil`, `ReleaseSigils`, `RequestCheckpointRespawn`, `resetGeneration` polling,
  `gDwPuzzleDebug`). No requested additions. Weak fallbacks for engine-a's symbols live in
  `dw_puzzle_actors.c` until `dw_puzzle.c` lands (delete them at merge).

### Headless proof (host test, same core)

    cc -std=c99 -Wall -Wextra -DDW_ACTORS_HOST_TEST -I include \
      tools/distortion_world/dw_actors_test.c src/overlay009/dw_puzzle_actors.c \
      -o /tmp/dwp/engine-b/dw_actors_test
    /tmp/dwp/engine-b/dw_actors_test > /tmp/dwp/engine-b/actors_test.log
    python3 tools/distortion_world/dw_actors_strip.py /tmp/dwp/engine-b/actors_test.log /tmp/dwp/engine-b/

The test drives `gDwActorsTestTable` (2 stones, shadow lane, echo + sigil, 4 pads) on a fake
platform: push / push-blocked / fall-to-landing + SOLID / falling-occupies-nothing /
landed-walkable / checkpoint snapshot + mid-fall restore / shadow patrol + pingpong snapshot /
catch + grace + checkpoint restore / echo mirror + hide-on-blocked + sigil fire-on-change /
pad gating + PressSigil effects + Skarmory carry request + reset restores pad bits / exit unloads
everything. Evidence (log, frame strips) goes in `/tmp/dwp/engine-b/`.

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

    static const DwPuzzleTile sBridgeTiles[] = {
        { 11, 3, 20, 0, DW_PUZZLE_SURFACE_WEST_WALL, 0, 0 },
        { 11, 3, 21, 0, DW_PUZZLE_SURFACE_WEST_WALL, 0, 0 },
    };
    /* x, y, z, state (group tiles: unused), surface, fallScriptId, pad */
    static const DwPuzzleGroup sGroups[] = {
        { sBridgeTiles, 2, 3, 0, 0, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_TILE_BLOCKED, 0, 0 },
        /* tiles, count, ghost-prop group (tw_arc id), fadeOut, fadeInLead, on, off, initial, fallScriptId */
    };
    static const DwPuzzleSigil sSigils[] = {
        { 12, 1, 14, DW_PUZZLE_SIGIL_TOGGLE, 0, 0, DW_PUZZLE_SURFACE_GROUND },
        /* x, y, z, kind, targetGroup, setValue, surface */
    };
    static const DwPuzzleCheckpoint sCheckpoints[] = { { 20, 1, 12, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } } };
    const DwPuzzleTable gDwPuzzleRavagedPathTable = {
        MAP_HEADER_DW_RAVAGED_PATH, 14, 14, 2, VAR_MAP_LOCAL_3,
        1, 1, 0, 0, 1, 0, 0, 0, sGroups, sSigils, NULL, NULL, sCheckpoints, NULL,
    };
    /* mapHeader, min/max VAR_ARC2_PROGRESS (0/0 = any), fallScriptId,
       fallVar, group/sigil/rune/current/checkpoint/tile counts, testOnly, pad, tables */

Coordinates are DW world tiles (x, y, z) as the ov9 step hook sees them: base
ground y = 1, wall y >= 2 at a fixed x, ceiling y = 10. (x, y, z) alone does
NOT identify a tile -- a wall and a ceiling can share one (the B4F wall->ceiling
transfers sit on the same tile) -- so every table entry carries a surface,
and every query passes the surface the player stands on. An entry matches
when its surface is DW_PUZZLE_SURFACE_ANY or equals the queried surface.

Surfaces: FLOOR 0 is a *floating* floor platform (ov9 kind 0, walked via its
tw_arc_attr grid); GROUND 4 is base map terrain (ov9 kind INVALID, platform
index -1, avatar distortion ACTIVE, walked via terrain collision). They are
different surfaces: a rune to GROUND must translate to platform kind INVALID
/ index -1, never to kind FLOOR. WEST_WALL 1, EAST_WALL 2, CEILING 3 follow
the ov9 numbering. Directions are FACE_* as pressed on the surface the
player stands on.

### Modules

- **Tile state.** `tiles[]` are explicit overrides (SOLID / VOID / BLOCKED).
  The walk check consults them on every surface, base ground included:
  BLOCKED is impassable, SOLID is walkable even where the stock grid says
  blocked, VOID is walkable in the collision check (so the player can step
  onto it) and the step/frame hook then starts the fall. Precedence:
  actor tiles > explicit overrides > groups (later group wins). On GROUND
  an explicit override (SOLID or VOID) takes precedence over the stock
  terrain collision bit 0x8000: the glue returns NOT colliding for SOLIC
  and for VOID before consulting the stock grid, so a player can step
  onto an explicitly-VOID ground tile even where the map permission is
  0x8000 (rift-213's landing tiles). There is no base-kind read: a tile
  that must fall carries an explicit VOID override, and a LANDED stone's
  SOLID actor tile shields it (see engine-b hooks).
- **Groups.** A group = tiles + one tw_arc ghost-prop group, on/off.
  Walkability follows the honeycomb rule: turning off starts the props
  fading at once but the tiles stay solid for `fadeOutFrames` (default 33);
  turning on shows the props at once but the tiles hold only after
  `fadeInLeadFrames` (default 3). Solid implies drawn; drawn does not
  imply solid during the fade-in lead (a step onto a drawn-but-not-yet-solid
  tile bumps, it never drops the player). The glue in ov9 applies the
  show/hide the engine requests each frame. A group with ghostPropGroup =
  DW_PUZZLE_GHOST_GROUP_NONE switches at once.
- **Sigils.** TOGGLE flips the target group; SET sets it to `setValue`;
  MOMENTARY holds the group on while any momentary sigil for it is stood on
  by any occupant (holder counts are per occupant: player, engine-b's echo,
  two momentary sigils for one group all behave); RESET restores the puzzle
  to the last checkpoint snapshot without moving the player. Every sigil
  activation plays a sound (SEQ_SE_PL_SYUWA) and starts a flash
  (`gDwPuzzleDebug.flashFrames`). Sigils fire once per step onto the tile;
  momentary sigils release on stepping off (per occupant).
- **Gravity runes.** A rune tile changes surface in place. The engine returns
  the rune action and the ov9 glue builds a `DistWorldFloatingPlatformJumpPointTemplate`
  from it (target tile, target surface, facing, rot, steps, optional camera
  transition) and starts `CreateJumpOnFloatingPlatformTask` -- the exact
  jump-point surface-change path, with its camera and rotation. `steps` 0
  means 16 (the stock jumps); `cameraSteps` 0 means 16; `cameraX/Y/Z` are
  camera angles in tw_arc camera-template units, not positions. The target
  tile must lie in a tw_arc platform of the target surface (the glue resolves
  the platform index; GROUND targets use kind INVALID / index -1); otherwise
  the rune does not fire.
- **Rift currents.** A current tile has a FACE_* drift direction. Stepping on
  one starts a slide: input is locked (player movement paused) and the player
  moves one tile per DW_PUZZLE_SLIDE_FRAMES_PER_TILE (6) field frames until
  blocked (BLOCKED tile, actor tile, edge of the surface) or off-current
  (the first non-current tile is the landing tile, then the slide ends).
  Landing on a current with a different direction turns the slide; landing
  on a sigil / rune / checkpoint ends the slide there and that tile's logic
  runs. Arrow visuals are the rift's tw_arc ghost props (`arrowGhostGroup`).
  Table rule: a current strip must not be a closed cycle with no exit; the
  engine also caps a slide at DW_PUZZLE_MAX_SLIDE_STEPS (64) tiles and ends
  it, so a bad table can never lock input forever.
- **Group tile + current on one tile (rift-214).** A tile can be both a
  group tile and a current. When the group's tile state is BLOCKED it
  wins and no slide happens (the step hook never starts a slide on a
  BLOCKED current tile, a stranded slide stops, and the frame hook stops
  a slide whose current tile went BLOCKED under the player); when the
  group is open, the current applies. A VOID current tile is a fall,
  not a slide. A slide stays within one platform.
- **Landing rule (rift-ef).** A jump, warp or respawn landing NEVER calls
  the step hook, so no sigil, rune, checkpoint, current or fall fires on
  the landing tile -- each fires only when the player next WALKS onto it.
  A rune pair therefore cannot ping-pong, and the destination rune of a
  rune pair fires only on a later walk. Checkpoints and sigils must sit
  on WALKED tiles, never on landing tiles. Implemented by architecture:
  the jump task, warps and respawn teleports do not call the step hook.
  The glue re-runs the step hook on slide landings on purpose (a slide
  is a movement), so slide landings DO fire.
- **Checkpoints and reset.** Stepping on a checkpoint tile snapshots the
  puzzle (the LOGICAL base (toggle/set) state only -- NOT the fading
  display state, rift-214: a group mid-fade at snapshot time restores to
  its logical value) and makes it the fall target. `groupBits` in the
  debug struct is the LOGICAL state (target = base OR momentary holds),
  not the lagging walkability; `groupDisplayBits` is the visual state.
  Momentary holders are NOT snapshotted -- they are per-occupant and
  cleared on restore, so occupants must re-press after a restore.
  Checkpoint 0 should be the map entry: the fresh-entry reset snapshots it
  without anyone stepping on it, so an early fall or reset always has a
  snapshot. A fall restores the player and puzzle state to the last
  checkpoint without losing the run: the step hook marks the fall, the
  map's existing fall script runs its warp, and on the first frame after
  the warp the engine restores the snapshot and respawns the player at the
  checkpoint (platform + distortion state + height mode from the glue,
  using the checkpoint's surface). The warp is detected against the
  persisted FALL TILE (the tile the fall started on), not the tracked
  position: a warp reloads overlay 9 and invalidates tracking before the
  frame hook sees it. The glue respawns at once when requested (it must
  NOT gate on LocalMapObj_IsAnimationSet, which is TRUE for an idle
  player). Restore semantics: group states restored to the snapshot base,
  fade timers cleared (props snap, no fade), holders cleared, slide cleared,
  actors notified via `gDwPuzzleDebug.resetGeneration` (engine-b restores
  its own snapshot when the generation changes). Puzzle state is RAM-only
  and lives in MAIN-binary RAM (`src/dw_puzzle_state.c`, `DwPuzzleState
  gDwPuzzleState`): a warp into a DW map -- including a same-map warp
  (fold, fall) -- reloads overlay 9 and zeroes its .bss, which would wipe
  the fall flag, the snapshot and the group state mid-fall. `gDwPuzzleDebug`
  stays in overlay 9 (repopulated every frame); `gDwPuzzleTestMode` stays
  in overlay 9 on purpose (a warp resets it to off, the safe production
  default; the harness re-enables it after each warp). Persistent
  once-only flags (Lost Tower) are never touched, so they keep working.
  A fall the step hook never sees (a coord-event lip not marked VOID in
  the table) still warps, but the puzzle resets to its initial state on
  the fresh load -- mark every fall lip VOID in the table.
  A fresh entry (no fall pending) also resets the puzzle to its initial state.
- **Scripted falls: `DwPuzzle_NotifyFall(FieldSystem *)`.** For falls the
  step hook never sees (Eterna's honeycomb, which falls from the frame
  hook; the Lost Tower false-seam drop; any scripted fall). Call it from
  the fall site BEFORE the fall script starts. It records fall-pending
  in engine RAM at the moment of the call -- the record survives the
  fall script clearing its fallVar (HoneyFall clears VAR_MAP_LOCAL_2
  first thing). On the fall script's warp, the frame hook restores the
  last checkpoint snapshot and respawns, exactly as for a VOID-tile fall.
  No-op without an active table; idempotent while a fall is in flight.
  Glued on BOTH honeycomb paths (Eterna frame hook before raising
  VAR_MAP_LOCAL_2, Eterna step hook before starting HoneyFall). Lost
  Tower wiring is that workstream's: call it before its false-seam fall
  script starts.
- **Fall routing.** A table has one frame-fall script (`fallScriptId` +
  `fallVar`, the Eterna honeycomb pattern). Step falls use the per-tile
  (`DwPuzzleTile.fallScriptId`) or per-group (`DwPuzzleGroup.fallScriptId`)
  script, falling back to the table's. Eterna Forest's split is the model:
  entry-chasm lips are VOID tiles with fallScriptId 2 (their own script),
  the honeycomb group's fallScriptId is 5, and the table's is 5.
- **Debug export.** `gDwPuzzleDebug` (in the xMAP, one RAM struct): map,
  active, player tile, surface, tile state, group solid/display bits, sigil
  bits, checkpoint, fall count, slide state + steps, last event + frame,
  flash frames, reset generation, and engine-b's stone positions / stone
  states (`u8 stoneStates[DW_PUZZLE_MAX_STONES]`, RESTING 0 / FALLING 1 /
  LANDED 2, engine-b's `DwActors_SyncDebug` writes it) / shadow phase +
  position / echo position (engine-b writes those fields; each actor
  position carries `present` and `surface`, so (0,0,0) on GROUND is
  unambiguous). The harness reads it. NOTE for harness readers: the
  struct grew past the layout some readers were written against (it gained
  `slideSteps` and per-actor `present`/`surface`/`padding`); read offsets
  from `include/overlay009/dw_puzzle.h`, not from a stale copy.
- **Engine-b hooks.** `DwPuzzle_SetActorTile(i, x, y, z, surface, state,
  present)`: an actor tile overrides a tile's state -- a stone landed as a
  stepping stone is SOLID, a stone sitting on a path is BLOCKED, and a
  stone on a current tile plugs the current (slides stop before it).
  Actor tiles BEAT explicit overrides. `DwPuzzle_ClearActorTiles()` clears
  all. `DwPuzzle_PressSigil(..., occupant)` / `DwPuzzle_ReleaseSigils(...,
  occupant)` let the echo press and release sigils without triggering
  runes, currents, checkpoints or falls. `DwPuzzle_RequestCheckpointRespawn()`
  is the shadow-catch path: restore + respawn at the checkpoint with no
  fall script. `DwPuzzle_DirDelta(surface, dir, &dx, &dy, &dz)` is the
  shared FACE_*-to-step table. Teardown (wired in the same glue that
  registers tables): `DwActors_RegisterTable` + `DwActors_VisualsInit` on
  map load (`DistWorld_DynamicMapFeaturesInit`, idempotent; a battle
  reload keeps state), `DwActors_VisualsUpdate` per frame, `DwActors_VisualsExit`
  on every map unload (`DistWorld_DynamicMapFeaturesFree`, deletes the
  MapObjects, keeps core state), and `DwActors_OnExit` only on a real
  departure (warp destination mapId != the freed map's header -- a battle
  return / same-map reload keeps the mapId, so it does NOT clear).

### Per-map glue a rift must add (in ov9_02249960.c, hook calls only)

- Step hook: call `DwPuzzle_HandleStep` first; on `fallRequested` start
  `out->fallScriptId`; on `runeRequested` build the jump template.
- Frame hook (`Arc2Dw_HandleFrame`): call `DwPuzzle_HandleFrame`; apply
  `ghostShowMask` / `ghostHideMask` with Hide/ShowGhostPropGroup; on
  `slideStep` move the player one tile and re-run the step hook; on
  `respawnRequested` move the player to the checkpoint (surface-aware).
- Collision: `DistWorld_CheckCollisionOnCurrentFloatingPlatform` and
  `DistWorld_DynamicMapFeaturesCheckCollision` (floor path) consult
  `DwPuzzle_QueryTile` with the player's current surface -- a map with no
  table returns DEFAULT and the stock grid decides.
- Frame-detected falls need the init-table line and the fall script clearing
  it, as in `DwPuzzleTable.fallVar` above (the Eterna honeycomb pattern).

### Test map (debug only)

Two debug-only tables exercise every module, one per rift:
`src/overlay009/dw_puzzle_test.c` (Ravaged Path: sigil + group bridge,
momentary sigil, reset sigil, rune, current, checkpoint, VOID fall) and
`src/overlay009/dw_puzzle_test_eterna.c` (Eterna Forest: the same modules
on the hive floor, east wall and ceiling; it does not touch the honeycomb,
which stays owned by the stock Eterna timer/frame hook). Both have
`testOnly = 1` and are returned only while test mode is on
(`gDwPuzzleTestMode`, set by the harness writing that RAM word, or
`DwPuzzle_SetTestMode`). With test mode off, both rifts have no table and
play exactly as today.

## QA gate: walkability-vs-graphics check

Run `python3 tools/qa/walkcheck.py --all-dw` before any DW merge,
with `--baseline <reviewed walkcheck.json>` once a baseline has been
triaged (see "Baseline gating" in `tools/qa/README.md`): without a
baseline it reports every HIGH finding (hundreds, mostly stock
geometry), and with one it fails only on NEW HIGH findings.
It compares what is drawn (chunk model faces, chunk props, ghost props)
against what the collision says (permissions for the floor,
`tw_arc_attr` for DW walls/ceilings) and exits 1 if any HIGH-severity
mismatch (or new HIGH vs the baseline) exists; it exits 2 if a map
fails to parse. See `tools/qa/README.md` for the mismatch classes,
the allowlist, and how to spot-check reported tiles in the emulator.
