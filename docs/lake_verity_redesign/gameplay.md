# Lake Verity redesign: gameplay

This covers the camera zone on the open staircase, the castle interiors, the Lake Verity events and how to test it all.
All tile coordinates come from `tools/lake_verity/layout.py`. Event coordinates are absolute tiles over the 96x64 matrix
102. The stock Verity Cavern door at (32,32) has collision 0x6E and the Lakefront exits (46,54)/(47,54) have 0x6F,
which is how we know the coordinates are absolute.

## Changes

| Area | Files |
| --- | --- |
| Camera zones (new) | `include/overlay005/field_camera_zones.h`, `src/overlay005/field_camera_zones.c` |
| Camera hooks | `src/overlay005/fieldmap.c` (`ov5_021D15F4`), `src/overlay005/field_camera.c` (`FieldCamera_Create`) |
| Build registration | `src/meson.build`, `platinum.us/main.lsf` (Overlay overlay5) |
| New map headers | `generated/map_headers.txt`, `include/data/map_headers.h` (`MAP_HEADER_VERITY_CASTLE_1F`; the earlier 2F/3F placeholders are gone, see [interior_1f.md](interior_1f.md)) |
| New events | `res/field/events/events_verity_castle_1f.json`, plus `meson.build` and `zone_event.order`; `events_verity_cavern.json` (exit retargeted) |
| Location name | `res/text/location_names.json` (`LocationNames_Text_VerityCastle`, appended). Verity Castle 1F and Verity Cavern (below its stair) use it. |
| Lake Verity | `res/field/events/events_lake_verity.json`, `res/field/scripts/scripts_lake_verity.s`, `res/text/lake_verity.json` |
| Flag | `generated/vars_flags.txt`: `FLAG_UNUSED_2420` is renamed to `FLAG_LAKE_VERITY_PORTAL_OPEN` |
| Portal (stock Spear Pillar asset) | `include/data/map_headers.h` (`MAP_HEADER_LAKE_VERITY.areaDataArchiveID` 62 -> 0x4D), the area NARCs written by `tools/lake_verity/stock_portal.py`, the prop record in `map_data_538.bin` written by `build_art.py`; see "The portal" below |
| Castle from the start | `res/field/scripts/scripts_verity_lakefront.s`, `res/field/events/events_verity_lakefront.json`, `res/field/scripts/scripts_init_lake_verity.s`, `src/system_flags.c`, plus the early scenes ported into the Lake Verity events, scripts and text above |

Nothing under `res/field/maps/data/*.bin` or `tools/lake_verity/assets` was touched. I found no bugs in `layout.py`.

## Camera zone system

A zone is a box of absolute tiles (inclusive) on one map header. It also has a progress axis:
- `weight = boxWeight(x) * boxWeight(z) * progress`
- `boxWeight` is 1 inside the box and falls linearly to 0 over `fadeTiles` outside it.
- `progress` runs 0 to 1 from `progressStart` to `progressEnd` along the axis, clamped.

The target offset is the sum of `weight * pitchDelta` and `weight * distanceDelta` over all zones on the current map.

- **Input.** The player's continuous world position, `PlayerAvatar_PosVector` converted to tiles as `(pos - 8) / 16`. The camera follows the walk animation smoothly instead of stepping once per tile.
- **Easing.** Every rendered field frame, the current offset moves 1/6 of the way to the target, and snaps once the step rounds to 0. It eases back the same way when you leave.
- **Applying the offset.** It is applied as a delta through `Camera_AdjustAngleAroundTarget` / `Camera_AdjustDistance`. Only the change since the last frame is added, so other camera code keeps working. For example, the FOV zoom in the cave-exit animation is untouched.
- **Scripts and menus.** While any field task runs (scripts, start menu, warps, fades), `FieldSystem_IsRunningTask` freezes the offset. Scripted camera moves never fight it.
- **Restoring the camera.** `FieldCamera_Create` calls `FieldCameraZones_Reset()`. Every map load, warp, return from an app (bag, party, battle) and save-load creates a fresh stock camera, and the tracked offset goes back to 0 with it. On the first frame after a reset the offset snaps to the target, even during the fade-in task. Coming back from the bag while standing on the stair shows the tilted camera at once, with no visible ease.
- **Hook.** `FieldCameraZones_Update()` is called in `ov5_021D15F4` right after `G3_ResetG3X()`, before the view matrix is built.

### Lake Verity stair zone

| Field | Value |
| --- | --- |
| Map | `MAP_HEADER_LAKE_VERITY` (matrix 102, now used for every visit) |
| Box | x 23..24, z 29..37: STAIR (23,31)-(24,36), STAIR_LANDING (23,29)-(24,30) and the approach tile row z=37 |
| Fade | 2 tiles outside the box. It fades out east through STAIR_WALL_GAP (25,29)/(25,30) onto the F1 terrace. |
| Progress | Z axis, from z=37 (0, stair foot at h0) to z=30 (1, landing). Full tilt is held across the landing. |

| Camera | Pitch | Distance | Camera height above target | Horizontal offset |
| --- | --- | --- | --- | --- |
| Stock `CAMERA_TYPE_ZOOMED_IN` | -54.657 deg | 515.456 | 420 | 298 |
| Top of stair / landing | -44.0 deg | 460.0 | 320 | 331 |
| Delta in the zone table | +10.657 deg (`F32_DEG_TO_IDX(10.656982421875)`) | `FX32_CONST(-55.4560546875)` | | |

FOV (10.46 deg) and the clip planes (150 / 900) stay stock; the camera moves closer, so the far plane still covers the scene.
To tune it, edit `sCameraZones[]` in `field_camera_zones.c`. To add a zone on another map, add a row there.

## Interiors

### Castle 1F: the entrance hall (new header)
- **Header.** `MAP_HEADER_VERITY_CASTLE_1F` (enum 593) is appended before `MAP_HEADER_COUNT`, with its entry at the end of `sMapHeaders`. The earlier `_2F`/`_3F` placeholders (Snowpoint Temple matrices) were renamed/removed: 2F became 1F and 3F was deleted.
- **Map.** A real castle hall: map_data 666, matrix 289, texture set 075, area data 0x4C, built by `tools/lake_verity/build_interior.py`. Layout, warps, budgets and checks are in [interior_1f.md](interior_1f.md).
- **Header settings.** Old Chateau-style interior fields: `CAMERA_TYPE_INTERIOR_ORTHOGRAPHIC`, mapType 3, `BACKGROUND_INDOORS_3`, no bike, running, Escape Rope or Fly, no encounters, clear weather, `scripts_verity_castle_1f` / `scripts_init_empty`. Music is `SEQ_PL_BF_CASTLE` (the Battle Castle theme). A signboard at (9,5) in front of the blocked stair reads "An old path that's been boarded up."
- **Stair.** A single stair down on the north wall leads to Verity Cavern. It is blocked for now (barricade, collision 0x805E on the warp tile).

### Verity Cavern: below the 1F stair
- The header, matrix, scripts and objects stay stock apart from the "Verity Castle" map label.
- Its exit (14,29) now returns to Castle 1F warp 1 (the stair) instead of the lake door.
- While the 1F stair is blocked, the cavern is unreachable, and so are Mesprit (`FLAG_MESPRIT_DISAPPEARED`, script 2), the Rowan object and `FLAG_FIRST_ARRIVAL_VERITY_CAVERN`. No script `Warp`s point at the cavern or the castle.

## Warp table

Warps on 0x6E (DOOR / WARP_NORTH) fire when you step onto the tile. 0x6F and 0x65 (indoor exit mat) fire when you press south while standing on it. 0x5E / 0x5F fire when you press east / west on the tile.

| Map | # | Tile | Behaviour | Destination |
| --- | --- | --- | --- | --- |
| Lake Verity | 0 | DOOR_1F (32,33), h0 | 0x6E | Verity Castle 1F #0 |
| Lake Verity | 1 | (46,54) | 0x6F | Verity Lakefront #2 (unchanged) |
| Lake Verity | 2 | (47,54) | 0x6F | Verity Lakefront #3 (unchanged) |
| Verity Castle 1F | 0 | exit mat (9,15) | 0x65 | Lake Verity #0 |
| Verity Castle 1F | 1 | stair (9,4) | 0x5E, blocked (0x805E) | Verity Cavern #0 |
| Verity Cavern | 0 | (14,29) | 0x6F | Verity Castle 1F #1 (arrives at (10,4), walks west onto the stair tile) |

The castle exterior has one storey: DOOR_1F is its only door. The old Lake Verity warps 3 (DOOR_2F) and 4 (ROOF_HATCH) are deleted, and the upper floor of the castle is now just the open F1 roof terrace. See `interior_1f.md` for the 1F hall.
| Verity Lakefront | 0 | (81,843) | stock | Lake Verity #2 (was LOW_WATER #1; also moved away by the Lakefront script) |
| Verity Lakefront | 1 | (80,843) | stock | Lake Verity #1 (was LOW_WATER #0; also moved away by the Lakefront script) |
| Verity Lakefront | 2 | (80,843) | stock | Lake Verity #1 (now always active) |
| Verity Lakefront | 3 | (81,843) | stock | Lake Verity #2 (now always active) |
| Verity Lakefront intro | script | `VerityLakefront_WarpToLakeValor` | scripted `Warp` | Lake Verity, (46,54) facing north (was LOW_WATER) |

**Where the player arrives outside.**
- Interiors return to the door tile itself, the same as the stock cavern return to (32,32).
- The engine always plays an exit step on arrival:
  - cave to outdoors: the player appears and walks one tile south;
  - stairs: the player walks one tile in the facing direction, west here.
- So the player ends up:
  - at (32,34) (courtyard, h0) from Castle 1F.
- Height comes from the BDHC.
- An arrival point on the tile south of the door would leave the player two tiles out, appearing from nowhere. Arriving on a WARP_NORTH tile does not re-trigger it; only stepping onto it does.
- Lakefront warp indices 1 and 2 are kept, so `events_verity_lakefront.json` needs no change.

## Lake Verity events

- **NPC positions.** Rowan, the Counterpart, Mars and the grunts all stand on stock tiles east and south of the island, (43..55, 38..51), off the island and bridge.
  - After Team Galactic leaves, `LakeVerity_SetPositionsAfterTeamGalactic` used to put Rowan at (50,37), on a bridge landing tile. He is now at (51,37), still facing west toward the bridge, so both landing tiles (50,36)/(50,37) stay free.
  - The Counterpart at (50,39) doesn't block anything: (50,38), (51,38) and (51,39) are open.
- **The portal.** The terrace centre holds the stock Distortion World portal from distorted Spear Pillar (see "The portal" below). Its footprint, 7 x 6 tiles around LAUNCHPAD (32,27) (`layout.PORTAL_TILES`: z24 x30..34, z25..28 x29..35, z29 x30..34), is blocked at h4, the same shape the stock Spear Pillar permissions block around their portal. The player stands next to it.
  - Its 18 edge tiles (`layout.PORTAL_EDGE`) each carry a bg event, facing any direction, that runs script 8, `LakeVerity_Launchpad`. Face the portal from any walkable neighbour and press A. (This replaces the single bg event on the formerly walkable LAUNCHPAD tile; LAUNCHPAD itself is now the blocked centre tile, still at h4.)
  - With `FLAG_LAKE_VERITY_PORTAL_OPEN` off (the default; nothing sets it yet), it shows "A dark rift swirls across the terrace. It hums faintly, but something seems to hold it shut...".
  - With the flag on, it says "A dark rift swirls across the terrace. It seems to be pulling at you..." and asks "Step into the rift?". Yes plays the stock Distortion World warp sequence copied from Spear Pillar:
    1. `ScrCmd_320` (the DW warp tunnel app)
    2. `ReturnToField`
    3. `SetPartyGiratinaForm GIRATINA_FORM_ORIGIN`
    4. `Warp MAP_HEADER_DISTORTION_WORLD_1F, 0, 55, 40, DIR_SOUTH`
  - To turn the portal on from any script, use `SetFlag FLAG_LAKE_VERITY_PORTAL_OPEN`.
- The portal prop is always drawn, whatever the flag says (a map prop has no visibility flag; the old custom portal was chunk geometry and was always drawn too).
- **Gate tower signs.** Bg events on the gate towers (41,35) and (41,38) run script 9, "VERITY CASTLE / The drawbridge is down.". Read them from the arch facing north or south.
- **New text.** It is appended to `res/text/lake_verity.json` and uses ASCII apostrophes only.

## The portal

The user asked for the stock Distortion World portal from the Spear Pillar climax, with no new textures.

- **What it is.** Build model 581 `d5_ana_pl` (`res/prebuilt/fielddata/build_model/build_model.narc`), a map prop of distorted Spear Pillar (header `SPEAR_PILLAR_DISTORTED`, area 0x3C = props list 56, set 59). `map_data_379` places it at the centre of tile (31,25), 8 units above the floor; the same chunk has the Dialga and Palkia rifts (580 `d5_ana_p`, 579 `d5_ana_d`).
  - It is a flat floor vortex: 5 horizontal quads (core, two 7.8-tile dark rings, a 5.5-tile and a 3.1-tile swirl) 0.6 to 1.1 tiles above the floor, lit materials.
  - Its textures `g_demo_ana1..4` (a3i5 64x64 x3, pltt16 32x32) and palettes live in areabm_texset 56.
  - `bm_anime_list[581]` gives it bm_anime 80, a 240-frame looping BCA0 that spins the four outer discs. The field starts it when the prop loads, so no script or C is involved.
- **How Lake Verity shows it.** Exactly as Spear Pillar does: a prop record in the chunk, loaded through the area's props list.
  - `build_art.py` appends a 581 record to chunk 538's props section (after the stock l_lake record): chunk-centred (-248, 88, 182), i.e. the centre of LAUNCHPAD (32,27) minus 2 units in z, and 8 units above the terrace (world y 80), the same offsets as in map_data_379.
  - Area 62 (props list 58) is shared with Sendoff Spring, Lake Verity Low Water and both Lake Valor maps, so the portal is not added to it. `tools/lake_verity/stock_portal.py --write` adds a Lake-Verity-only copy instead:
    - `area_build.narc` entry 71 = stock list 58 + 581: [311 l_lake, 72 bomb_mark, 74 l_lake_l4, 581].
    - `areabm_texset.narc` entry 71 = stock texset 58 (l_lake, bomb_mark) + `g_demo_ana1..4` and their palettes copied byte for byte from texset 56 (palettes contiguous, in stock order). No new textures.
    - `area_data.narc` entry 77 (0x4D) = (props list 71, set 61, 0, light 0): area 62 with the new list.
    - `MAP_HEADER_LAKE_VERITY.areaDataArchiveID` = 0x4D (was 62). Matrix 102 (chunks 537-542) is only used by this header, so no other map sees the 581 record.
  - This follows the Mt. Coronet (0x4B) and castle interior (0x4C) precedent. `build_interior.py` rewrites only entry 0x4C in place, so the two tools don't collide.
- **Tradeoff.**
  - Adding 581 to the shared list 58 instead would have needed no header change, but Sendoff Spring and both Lake Valor maps would each load the 15 KB model, its animation and 12.8 KB of prop texture VRAM for nothing.
  - The own-area route costs one header edit and three appended NARC entries; the prop texture set grows from 3120 to 16048 B of VRAM for Lake Verity only (stock Spear Pillar's is 18624).
  - The portal's animation plays all the time, as in Spear Pillar. Hiding it until the flag is set would need extra script or C work (or a second area), which the request did not ask for.
- **Removed:** the custom portal mesh (`assets/portal.mesh.json`: ring, swirl disc, halo, light shaft), the `lv_portal` texture and its 3 frames (and its fldtanime entry), the portal's uses of `lv_glow`, the violet bake light, and the `lv_sigil` ring on the terrace floor with its light. `lv_sigil` stays in `assets/textures/` because the castle interior's floor sigil uses it (set 075); `lv_glow` stays for the torches.
- **Renders:** `~/Documents/Lake Verity Update/pipeline_checks/portal_stock_top.png` and `portal_stock_game.png` (static pose; the prop decoded by `stock_portal.py --preview`).

## One Lake Verity map for every story state

The castle (matrix 102, `MAP_HEADER_LAKE_VERITY`) is now used from the start of the game. Stock Platinum used two headers.

### Which header is the "low water" one

`MAP_HEADER_LAKE_VERITY_LOW_WATER` (matrix 101) is the **early** lake, not a drained lake after a story beat.
- `VerityLakefront_OnLoad` / `_OnTransition` sent the player to it while `FLAG_DEFEATED_COMMANDER_SATURN_VALOR_CAVERN` was unset, and to `MAP_HEADER_LAKE_VERITY` afterwards. (The stock label names are the wrong way round: `SetWarpsLakeVerityNormal` disabled the LAKE_VERITY warps.)
- Its scenes are the intro (Cyrus, the rival, the Mesprit cry) and Rowan plus the counterpart after Canalave ("How was Lake Valor?").
- Matrix 101 does look like lower water: a band of shallow/puddle tiles (0x16, 0xA9) at x16-38, z27-41 where matrix 102 has open water. The east shore used by every scene is identical in both matrices.
- The post-bomb drained lake in Platinum is Lake Valor (`MAP_HEADER_LAKE_VALOR_DRAINED`), which this work does not touch.

### Every path that chose between the two headers

| Path | Stock | Now |
| --- | --- | --- |
| `VerityLakefront_OnLoad` / `_OnTransition` | Flag-based: warps 0/1 (LOW_WATER) before Saturn, warps 2/3 (LAKE_VERITY) after | Always moves warps 0/1 away, so warps 2/3 are always used |
| `events_verity_lakefront.json` warps 0/1 | LOW_WATER #1 / #0 | Retargeted to LAKE_VERITY #2 / #1, so nothing reaches LOW_WATER even if they were active |
| `VerityLakefront_WarpToLakeValor` (intro walk-in) | `Warp MAP_HEADER_LAKE_VERITY_LOW_WATER, 0, 46, 54, 0` | `Warp MAP_HEADER_LAKE_VERITY, 0, 46, 54, 0` |
| `SystemFlag_GetAltMusicForHeader` (`src/system_flags.c`) | LAKE_VERITY: Galactic music until `FLAG_ALT_MUSIC_LAKE_VERITY` | Lake music also while Saturn is not beaten (LOW_WATER's music) |
| Fly, Dig, Escape Rope, blackout, C special-casing | None reference either header (Escape Rope is off on both; not a Fly target) | Unchanged |
| Nothing else | `grep` for `LAKE_VERITY_LOW_WATER` finds only the header table, its own scripts/events/text/encounters and the flag names | |

### Story-state table

| State | Condition | What Lake Verity shows |
| --- | --- | --- |
| A1 Intro | Saturn not beaten, `VAR_VISITED_LAKE_VERITY_WITH_RIVAL == 0` | Cyrus (48,43) and the rival (47,54). Frame script 10 `LakeVerity_OnFrameCyrus` plays the stock intro, then sets the var to 1 |
| A2 Before Canalave | Saturn not beaten, intro done | Empty lake and castle, lake music |
| A3 After Canalave | Saturn not beaten, `FLAG_HIDE_LAKE_VERITY_LOW_WATER_PROF_ROWAN/_COUNTERPART` cleared by Canalave | Rowan (48,43) and the counterpart (49,43) facing the lake, scripts 11/12 ("How was Lake Valor?") |
| B1 Team Galactic | Saturn beaten, `FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY` unset | Stock Galactic scene: Mars, grunts, Rowan, counterpart, Galactic music. Rowan notices the player on arrival (frame script 5) |
| B2 After Mars | Galactic left, Lake Acuity not done | Rowan (51,37) and the counterpart (50,39), lake music |
| B3 After Lake Acuity | Lake Acuity sets both Rowan/counterpart hide flags | Empty lake and castle |

How it is gated (`LakeVerity_OnTransition`, which runs before objects are created):
- Saturn not beaten: `LakeVerity_SetEarlyState` sets the Galactic, Rowan and counterpart hide flags of the Galactic scene. The early objects keep their stock flags.
- Saturn beaten: `LakeVerity_SetTeamGalacticState` sets the four early hide flags (as in stock, where those objects were on the other map), clears the Galactic scene's hide flags while Galactic has not left, and arms Rowan's notice.
- Rowan's notice used to fire whenever `VAR_LAKE_VERITY_PROF_ROWAN_STATE == 0`, which would now include the intro. It is gated by `VAR_MAP_LOCAL_1` instead: set to 1 in `SetTeamGalacticState` if the state var is 0, cleared by the notice script. Map-local vars are zeroed on every map change before the transition script runs.
- The frame table checks the intro first (`VAR_VISITED_LAKE_VERITY_WITH_RIVAL, 0, 10`), then the notice (`VAR_MAP_LOCAL_1, 1, 5`).
- Hide flags set by `RemoveObject` (Cyrus, rival, the Galactic group after Mars) behave as in stock.

Ported from LOW_WATER: the Cyrus, rival, early Rowan and early counterpart objects (appended as local ids 9-12, so ids 0-8 are unchanged), the intro and Rowan/counterpart scripts with their used movements, and the 12 text entries (appended to `lake_verity.json`, apostrophes made ASCII).
Not ported: the two Starly objects (their hide flag is set in `scripts_init_new_game.s` and never cleared, so they never appear) with the `FLAG_MAP_LOCAL` OnLoad that hid them, the pokeball (Lake Verity already has the same one, same flag), and the unused movements.

All intro tiles were checked against `layout.py`: Cyrus's path (48,43)-(48,48)-(47,48)-(47,52), the rival's (47,50)-(47,54) and (48,53), the player at (46,53)/(46,54) and the camera pan column (46,44)-(46,53) are stock shore tiles, walkable in the new layout. Nothing in the intro uses the lake bed or the island, so no scene needed reworking.

### LOW_WATER is kept but unreachable

`MAP_HEADER_LAKE_VERITY_LOW_WATER` stays in the header table with its stock data, scripts, events, text and encounters, so nothing is renumbered and it still builds. No warp or script leads to it any more.
I did not alias it to the castle data: its header id would still differ from `MAP_HEADER_LAKE_VERITY`, so the stair camera zone, the music rule and the Verity Cavern return warp would not match it, and an alias would give two ids for one place.
A save made while standing in LOW_WATER still loads the stock lake; leaving through (46,54)/(47,54) arrives at the Lakefront normally (warp arrival reads the positions from the event file before the Lakefront script moves warps), and the next entry uses the castle.

## In-game test steps

Story visits (new game, or saves at each point):
- **Intro (A1).** Start a new game and follow the rival to Lake Verity. The Lakefront walk-in should put you at (46,54) on the castle map with lake music. The intro should play as in stock: the camera pans north to Cyrus at (48,43), he walks down to you and leaves south, the rival reacts to the cry and runs off. Nobody should walk through water or scenery. No Mars, grunts or Galactic-scene Rowan should be visible, and Rowan should not "notice" you.
- **After the intro (A2).** Walk out and back in before getting a Pokemon, and again later. The lake should be empty, lake music, no scene. The castle doors work but the interiors are empty (Mesprit is hidden until the post-game).
- **After Canalave (A3).** Rowan and the counterpart should stand at (48,43)/(49,43) facing the lake. Talk to Rowan twice (first and repeat lines) and to the counterpart (Dawn or Lucas text by player gender).
- **Team Galactic (B1).** After beating Saturn in Valor Cavern, enter: Galactic music, grunts, Mars, Rowan steps south and says "What timing!" once. Leave and re-enter: he should not repeat it. The early Rowan/counterpart should be gone. Beat Mars as in stock.
- **After Mars (B2).** Lake music, Rowan at (51,37) and the counterpart at (50,39).
- **After Lake Acuity (B3).** Both gone.

Castle checks:
1. Enter Lake Verity from the Lakefront in any story state. You should arrive at (46,54)/(47,54) as before, and walking back out should still work.
2. Walk across the drawbridge. Face north at (41,36) and press A, then face south at (41,37) and press A. The sign text should show both times.
3. Walk onto DOOR_1F (32,33). You should arrive in Verity Castle 1F on the exit mat (9,15) with the "Verity Castle" popup. Walk north along the carpet: the stair at the north wall (9,4) is barricaded and cannot be entered. Press south on the mat: you should appear at the door and step out to (32,34).
4. Stair camera:
   - Walk to (23,37) or (24,37), then climb north. The camera should flatten and move in smoothly as you climb, reaching full tilt at the landing (z 29-30).
   - Step east through the wall gap onto the terrace. The camera should ease back to stock within about 2 tiles.
   - Walk down the stair. It should ease back to stock by z=37.
   - Stand mid-stair, open the start menu, bag and party, then close them. The tilt should be unchanged, with no jump and no drift.
   - Save and reset while mid-stair, then continue. The camera should load already tilted to match the position.
   - Talk to an NPC or run a script elsewhere. The camera should behave as stock.
5. On the terrace (h4), walk the whole area inside the parapet (26..38 x 23..32). There should be no door, hatch or warp anywhere on it, and the parapet should block you at the edges.
6. On the terrace, the stock Spear Pillar portal should swirl in the middle. Walk around it: its 7 x 6 footprint should block you. Face it from any side and press A. The dormant message should show. Set `FLAG_LAKE_VERITY_PORTAL_OPEN` with a debug script or save editor and press A again. The Yes/No prompt should appear; No closes it, Yes plays the warp tunnel and puts you in Distortion World 1F.
7. Warp or Fly away from Lake Verity, then come back. The camera should be stock everywhere except the stair.

## Unverified risks (nothing has been built)

- **Compile.**
  - The C code follows the existing overlay 5 idioms, and every symbol was checked by grep: `Camera_AdjustAngleAroundTarget`, `Camera_AdjustDistance`, `PlayerAvatar_PosVector`, `FieldSystem_IsRunningTask`, `MAP_OBJECT_TILE_SIZE`, `NELEMS` from the pch, and `MAP_HEADER_LAKE_VERITY` from `generated/map_headers.h`.
  - Overlay 5 grows by about 1 KB. If the ARM9 overlay region is already tight, the link could fail.
- **Symbol names.** The events NARC enum name `events_verity_castle_1f` and `LocationNames_Text_VerityCastle` are generated at build time from the order file and the JSON ids; I assumed the same scheme as the neighbouring entries.
- **BDHC heights.** Arrival height, and the stair tilt feeling right, depend on the pipeline agent's BDHC. DOOR_1F must give h0 and the exit step must land on the walkable tile (32,34); the terrace, including the blocked portal footprint around (32,27), must give h4. Both were checked against the rebuilt BDHC with `mapdata.height_at`.
- **Stair camera values.** The camera numbers are unverified on screen. The deltas can be tuned in one place.
- **Castle from the start.** Resolved: every visit uses `MAP_HEADER_LAKE_VERITY` (see "One Lake Verity map for every story state"). Remaining risks:
  - The early game now has the castle, its doors and the stair open while the player may have no Pokemon (the intro). The interiors have no encounters; the shore grass is stock.
  - The early lake now uses `encounters_lake_verity` instead of `encounters_lake_verity_low_water`. They differ in one night slot (Starly instead of Bidoof).
  - Ported text keeps stock wording ("The lake hasn't changed at all", "legendary Pokemon of the lake bed").
  - Old saves standing inside LOW_WATER load the stock lake once (see above).
- **Distortion World entry.** The Distortion World 1F frame script runs its story intro while `VAR_DISTORTION_WORLD_PROGRESS == 0`. Entering early through the launchpad would play that scene out of order. There is also no way back to Lake Verity except the stock DW exits to Spear Pillar. Keep the flag off until the story is designed.
- **Portal prop.** Untested in game: that area 0x4D loads (texture binding of model 581 to texset 71 is GF_ASSERTed), that the prop draws at the right height and spins, and that the portal plus the castle stay within the per-frame polygon and texture budgets on hardware.
- **Flag choice.** `FLAG_LAKE_VERITY_PORTAL_OPEN` reuses system flag 2420, which is unused in stock (`FLAG_UNUSED_2420`) and not referenced anywhere in the repo.
- **Location label.** The label change means Verity Cavern now shows "Verity Castle" in the map popup, journal and TV.
