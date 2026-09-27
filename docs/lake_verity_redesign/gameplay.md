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
| New map headers | `generated/map_headers.txt`, `include/data/map_headers.h` (`MAP_HEADER_VERITY_CASTLE_2F`, `_3F`) |
| New events | `res/field/events/events_verity_castle_2f.json`, `events_verity_castle_3f.json`, plus `meson.build` and `zone_event.order` |
| Location name | `res/text/location_names.json` (`LocationNames_Text_VerityCastle`, appended). Castle 1F (Verity Cavern), 2F and 3F use it. |
| Lake Verity | `res/field/events/events_lake_verity.json`, `res/field/scripts/scripts_lake_verity.s`, `res/text/lake_verity.json` |
| Flag | `generated/vars_flags.txt`: `FLAG_UNUSED_2420` is renamed to `FLAG_LAKE_VERITY_PORTAL_OPEN` |
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

### Castle 1F: Verity Cavern (repurposed)
- The header is unchanged apart from the map label, which is now "Verity Castle". Its matrix, scripts and events stay stock.
- Mesprit (`FLAG_MESPRIT_DISAPPEARED`, script 2), the Rowan object and `FLAG_FIRST_ARRIVAL_VERITY_CAVERN` are untouched.
- 1F is a dead end: its only warp goes back out through DOOR_1F.

### Castle 2F and 3F: new headers
- **Headers.** `MAP_HEADER_VERITY_CASTLE_2F` and `MAP_HEADER_VERITY_CASTLE_3F` are appended before `MAP_HEADER_COUNT` (enum values 593 and 594), with matching entries at the end of `sMapHeaders`.
- **Header settings.** Area data 65, `scripts_empty` / `scripts_init_empty`, text bank `TEXT_BANK_VERITY_CAVERN` (unused), music `SEQ_D_RYAYHY` (the Verity Cavern theme), no encounters, clear weather, `CAMERA_TYPE_CAVE`, mapType 3 (cave), `BACKGROUND_CAVE_2`, no Fly or Escape Rope.
- **Placeholder maps: stock Snowpoint Temple 1F (matrix 68) for 2F and Snowpoint Temple B1F (matrix 69) for 3F.** Why these:
  - They are ancient stone temple interiors with pillars, the closest stock look to a castle.
  - Both matrices have `"headers": []`, so every chunk takes the current header and sharing them with the temple is safe.
  - Their warp tiles already give exactly the links needed:
    - an entrance on 1F: (8,13), 0x6F WARP_SOUTH
    - a stair pair: 1F (14,3) 0x5F, then B1F (4,3) 0x5E
    - an onward stair on B1F: (14,3) 0x5F
  - So the stock stair arrival animations behave correctly without any collision edits.
  - I considered Canalave Library 2F/3F (matrices 218/219), but it is orthographic and full of bookshelves. Old Chateau is a mansion.
- **Temple leftovers.** The small ice patches (0x20) stay, and the route is still solvable. The temple bg events and the B1F pokeball were not copied.
- **Pipeline agent.** Swap the matrices for real castle interiors later by changing `mapMatrixID` / `areaDataArchiveID` and the warp coordinates in the two events files.

## Warp table

Warps on 0x6E (DOOR / WARP_NORTH) fire when you step onto the tile. 0x6F fires when you press south while standing on it. 0x5E / 0x5F fire when you press east / west on the tile.

| Map | # | Tile | Behaviour | Destination |
| --- | --- | --- | --- | --- |
| Lake Verity | 0 | DOOR_1F (32,33), h0 | 0x6E | Verity Cavern #0 |
| Lake Verity | 1 | (46,54) | 0x6F | Verity Lakefront #2 (unchanged) |
| Lake Verity | 2 | (47,54) | 0x6F | Verity Lakefront #3 (unchanged) |
| Lake Verity | 3 | DOOR_2F (32,30), h4 | 0x6E | Verity Castle 2F #0 |
| Lake Verity | 4 | ROOF_HATCH (33,27), h10 | 0x6E | Verity Castle 3F #1 |
| Verity Cavern (1F) | 0 | (14,29) | 0x6F | Lake Verity #0 |
| Verity Castle 2F | 0 | (8,13) | 0x6F | Lake Verity #3 |
| Verity Castle 2F | 1 | (14,3) | 0x5F | Verity Castle 3F #0 |
| Verity Castle 3F | 0 | (4,3) | 0x5E | Verity Castle 2F #1 |
| Verity Castle 3F | 1 | (14,3) | 0x5F | Lake Verity #4 |
| Verity Lakefront | 0 | (81,843) | stock | Lake Verity #2 (was LOW_WATER #1; also moved away by the Lakefront script) |
| Verity Lakefront | 1 | (80,843) | stock | Lake Verity #1 (was LOW_WATER #0; also moved away by the Lakefront script) |
| Verity Lakefront | 2 | (80,843) | stock | Lake Verity #1 (now always active) |
| Verity Lakefront | 3 | (81,843) | stock | Lake Verity #2 (now always active) |
| Verity Lakefront intro | script | `VerityLakefront_WarpToLakeValor` | scripted `Warp` | Lake Verity, (46,54) facing north (was LOW_WATER) |

**Where the player arrives outside.**
- Interiors return to the door or hatch tile itself, the same as the stock cavern return to (32,32).
- The engine always plays an exit step on arrival:
  - cave to outdoors: the player appears and walks one tile south;
  - stairs: the player walks one tile in the facing direction, west here.
- So the player ends up:
  - at (32,34) (courtyard, h0) from 1F;
  - at (32,31) (F1 terrace, h4) from 2F;
  - at (32,27) (roof deck, h10, west of the hatch, south of the launchpad) from 3F.
- Height comes from the BDHC.
- An arrival point on the tile south of the door would leave the player two tiles out, appearing from nowhere. Arriving on a WARP_NORTH tile does not re-trigger it; only stepping onto it does.
- Lakefront warp indices 1 and 2 are kept, so `events_verity_lakefront.json` needs no change.

## Lake Verity events

- **NPC positions.** Rowan, the Counterpart, Mars and the grunts all stand on stock tiles east and south of the island, (43..55, 38..51), off the island and bridge.
  - After Team Galactic leaves, `LakeVerity_SetPositionsAfterTeamGalactic` used to put Rowan at (50,37), on a bridge landing tile. He is now at (51,37), still facing west toward the bridge, so both landing tiles (50,36)/(50,37) stay free.
  - The Counterpart at (50,39) doesn't block anything: (50,38), (51,38) and (51,39) are open.
- **Launchpad.** A bg event at LAUNCHPAD (32,26), facing any direction, runs script 8, `LakeVerity_Launchpad`.
  - With `FLAG_LAKE_VERITY_PORTAL_OPEN` off (the default; nothing sets it yet), it shows "An ancient stone ring is set into the roof. It hums faintly, but nothing happens...".
  - With the flag on, it asks "Step into the rift?". Yes plays the stock Distortion World warp sequence copied from Spear Pillar:
    1. `ScrCmd_320` (the DW warp tunnel app)
    2. `ReturnToField`
    3. `SetPartyGiratinaForm GIRATINA_FORM_ORIGIN`
    4. `Warp MAP_HEADER_DISTORTION_WORLD_1F, 0, 55, 40, DIR_SOUTH`
  - To turn the portal on from any script, use `SetFlag FLAG_LAKE_VERITY_PORTAL_OPEN`.
- **Gate tower signs.** Bg events on the gate towers (41,35) and (41,38) run script 9, "VERITY CASTLE / The drawbridge is down.". Read them from the arch facing north or south.
- **New text.** It is appended to `res/text/lake_verity.json` and uses ASCII apostrophes only.

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
3. Walk onto DOOR_1F (32,33). You should warp into Verity Cavern with the "Verity Castle" popup. Check that Mesprit and Rowan behave as in stock. Leave by pressing south on (14,29): you should appear at the door and step out to (32,34).
4. Stair camera:
   - Walk to (23,37) or (24,37), then climb north. The camera should flatten and move in smoothly as you climb, reaching full tilt at the landing (z 29-30).
   - Step east through the wall gap onto the terrace. The camera should ease back to stock within about 2 tiles.
   - Walk down the stair. It should ease back to stock by z=37.
   - Stand mid-stair, open the start menu, bag and party, then close them. The tilt should be unchanged, with no jump and no drift.
   - Save and reset while mid-stair, then continue. The camera should load already tilted to match the position.
   - Talk to an NPC or run a script elsewhere. The camera should behave as stock.
5. On the terrace, walk onto DOOR_2F (32,30). You should reach 2F at (8,13). Press south there: you should arrive at the door and step out to (32,31) at h4.
6. On 2F, press west on the stairs (14,3). You should reach 3F at (4,3). Press east there to go back to 2F (14,3), then return to 3F.
7. On 3F, press west on the stairs (14,3). You should come out on the roof at the hatch and walk west to (32,27).
8. Face north toward the launchpad (32,26) and press A. The dormant message should show. Set `FLAG_LAKE_VERITY_PORTAL_OPEN` with a debug script or save editor and press A again. The Yes/No prompt should appear; No closes it, Yes plays the warp tunnel and puts you in Distortion World 1F.
9. Step onto the hatch (33,27). You should arrive on 3F at (14,3).
10. Warp or Fly away from Lake Verity, then come back. The camera should be stock everywhere except the stair.

## Unverified risks (nothing has been built)

- **Compile.**
  - The C code follows the existing overlay 5 idioms, and every symbol was checked by grep: `Camera_AdjustAngleAroundTarget`, `Camera_AdjustDistance`, `PlayerAvatar_PosVector`, `FieldSystem_IsRunningTask`, `MAP_OBJECT_TILE_SIZE`, `NELEMS` from the pch, and `MAP_HEADER_LAKE_VERITY` from `generated/map_headers.h`.
  - Overlay 5 grows by about 1 KB. If the ARM9 overlay region is already tight, the link could fail.
- **Symbol names.** The events NARC enum names `events_verity_castle_2f` / `_3f` and `LocationNames_Text_VerityCastle` are generated at build time from the order file and the JSON ids; I assumed the same scheme as the neighbouring entries.
- **BDHC heights.** Arrival height, and the stair tilt feeling right, depend on the pipeline agent's BDHC. The door tiles must give h0 (DOOR_1F), h4 (DOOR_2F) and h10 (ROOF_HATCH), and the exit step must land on walkable tiles: (32,34), (32,31) and (32,27).
- **Stair camera values.** The camera numbers are unverified on screen. The deltas can be tuned in one place.
- **Castle from the start.** Resolved: every visit uses `MAP_HEADER_LAKE_VERITY` (see "One Lake Verity map for every story state"). Remaining risks:
  - The early game now has the castle, its doors and the stair open while the player may have no Pokemon (the intro). The interiors have no encounters; the shore grass is stock.
  - The early lake now uses `encounters_lake_verity` instead of `encounters_lake_verity_low_water`. They differ in one night slot (Starly instead of Bidoof).
  - Ported text keeps stock wording ("The lake hasn't changed at all", "legendary Pokemon of the lake bed").
  - Old saves standing inside LOW_WATER load the stock lake once (see above).
- **Distortion World entry.** The Distortion World 1F frame script runs its story intro while `VAR_DISTORTION_WORLD_PROGRESS == 0`. Entering early through the launchpad would play that scene out of order. There is also no way back to Lake Verity except the stock DW exits to Spear Pillar. Keep the flag off until the story is designed.
- **Flag choice.** `FLAG_LAKE_VERITY_PORTAL_OPEN` reuses system flag 2420, which is unused in stock (`FLAG_UNUSED_2420`) and not referenced anywhere in the repo.
- **Placeholder look.** The 2F/3F placeholders use Snowpoint Temple visuals and ice tiles, and the 3F stairs look like they go down.
- **Location label.** The 1F label change means Verity Cavern now shows "Verity Castle" in the map popup, journal and TV.
