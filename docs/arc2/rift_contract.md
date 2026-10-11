# Arc 2 rift contract (R0)

The five Arc 2 rifts are standalone Distortion World maps (`MAP_HEADER_DW_*`, ids 596-600, registered in R0).
Story workstreams own the overworld side: the rift object, the scene before entry, and what happens after
return. Rift workstreams own everything inside the DW map. Both sides code to this table. Any change to a row
goes through the orchestrator, and the side that changes publishes the new value.

## The table

| DW map (owner) | Overworld map (owner) | Rift object tile | Entry state (story sets, then warps) | Exit warp (DW script, after calm) | Calm sets |
|---|---|---|---|---|---|
| `MAP_HEADER_DW_RAVAGED_PATH` (rift-a) | `MAP_HEADER_RAVAGED_PATH` (s-route204) | (19,45), the stock Hitmonlee totem's tile | 14 | `Warp MAP_HEADER_RAVAGED_PATH, 0, 19, 46, DIR_SOUTH` | `VAR_ARC2_PROGRESS` 15, `FLAG_TOTEM_HITMONLEE_DEFEATED` |
| `MAP_HEADER_DW_ETERNA_FOREST` (rift-a) | `MAP_HEADER_ETERNA_FOREST` (s-floaroma) | (84,36), the stock Vespiquen totem's tile | 25 | `Warp MAP_HEADER_ETERNA_FOREST, 0, 84, 37, DIR_SOUTH` | 26, `FLAG_TOTEM_VESPIQUEN_DEFEATED` |
| `MAP_HEADER_DW_ROUTE_214` (rift-b) | `MAP_HEADER_ROUTE_214` (s-route214) | (726,664), the stock Skarmory totem's tile | 62 | `Warp MAP_HEADER_ROUTE_214, 0, 726, 665, DIR_SOUTH` | 63, `FLAG_TOTEM_SKARMORY_DEFEATED` (+ `VAR_ARC2_CHOICES` bit 2 from the boost choice) |
| `MAP_HEADER_DW_ROUTE_213` (rift-b) | `MAP_HEADER_ROUTE_213` (s-raid) | (715,830), the stock Lapras totem's tile (beach sand) | 83 | `Warp MAP_HEADER_ROUTE_213, 0, 715, 831, DIR_SOUTH` | 84, `FLAG_TOTEM_LAPRAS_DEFEATED` (+ `FLAG_ARC2_ELIAS_CARD` if the card is picked up) |
| `MAP_HEADER_DW_LOST_TOWER` (rift-b) | `MAP_HEADER_ROUTE_209_LOST_TOWER_2F` (s-hearthome) | (6,8), the stock Spiritomb totem's tile | first visit 92; second visit 94 | `Warp MAP_HEADER_ROUTE_209_LOST_TOWER_2F, 0, 5, 8, DIR_WEST` (both visits) | first visit: `FLAG_ARC2_RIFTB_C` (= vein found), state unchanged; second visit: 95, `FLAG_TOTEM_SPIRITOMB_DEFEATED` |

Coordinates are tiles: matrix-global on outdoor maps (Routes 213 and 214), local in Ravaged Path, Eterna Forest
and the Lost Tower. All five tiles were checked against the collision data (`/tmp/a2/r0/colview.py`). Each exit tile is walkable,
right next to the rift tile, with the player facing away from it. Every stub's exit was walked headlessly from the
DW entry, and the player landed on exactly the tile in the table (`/tmp/a2/r0/t_setstate.py dwexit:...`, logs in
`/tmp/a2/r0/t_setstate_*.json`).

### Entry (story side)

- The rift object replaces the overworld totem object at the same tile. Per D15, the story workstream deletes
  the `StartTotemBattle` totem object. Graphics: `OBJ_EVENT_GFX_RIFT_ARC2` (placeholder).
- The rift object's script sets the entry state, then warps the player in, using the Arc 1 launchpad sequence
  (`scripts_lake_verity.s`, `LakeVerity_Arc1LaunchpadStepIn`):

      SetVar VAR_ARC2_PROGRESS, <entry state>
      PlayFanfare SEQ_SE_PL_SYUWA
      FadeScreenOut
      WaitFadeScreen
      ScrCmd_320
      ReturnToField
      Warp MAP_HEADER_DW_<NAME>, 0, 20, 12, DIR_WEST
      FadeScreenIn
      WaitFadeScreen

- **The DW entry tile is (20,12), facing west, for all five maps.** That is the arc1 seams clone's entry
  platform. If a rift workstream moves its entry tile, it tells the orchestrator, and the story owner updates
  its one `Warp` line.
- Hide the rift object once the calm value is set (story side, using map-local hide flags 0x30-0x3F).
- The entry state values are recommendations within each story block. Rift scripts should test ranges
  (`GoToIfLt` / `GoToIfGe`), not exact values.

### Inside and exit (rift side)

- The rift workstream owns the floor, the puzzle, the totem battle (`StartTotemBattle`), the Calm Shard text,
  and the calm values in the table, which it sets before the exit warp.
- The exit uses the Arc 1 exit-rift sequence (`scripts_distortion_world_arc1_seams.s`):
  `PlayFanfare SEQ_SE_PL_SYUWA`, `FadeScreenOut`, `WaitFadeScreen`, `ScrCmd_320`, `ReturnToField`, `Warp
  <exit>`, `FadeScreenIn`, `WaitFadeScreen`.
- After the exit, the story owner's map takes over on its OnTransition/OnFrame at the calm value:
  - 15: Ravaged Path aftermath, then 2.8.
  - 26: the 2.10 aftermath.
  - 63: s-route214 sends the player to the 2.19 cutaway, which sets 69.
  - 84: the 2.22 Rowan scene, owned by s-pastoria.
  - 95: the 2.26 Spiritomb aftermath.
- Lost Tower:
  - First visit (state 92): the shadow wall stays closed below state 94. Finding the vein sets
    `FLAG_ARC2_RIFTB_C` (to be renamed `FLAG_ARC2_VEIN_FOUND` at merge), then the exit warp runs.
  - s-hearthome sees state 92 plus that flag on Lost Tower 2F, plays the vein call, and sets 93. The 94 grunt
    scene follows, then the second entry at 94, where the wall opens.
- The current stubs (`scripts_dw_<name>.s`) already contain the exact exit `Warp` for each map. A coord event
  at (17,12), three steps west of the entry, runs it.

## Findings

### The Route 211 / Mt. Coronet tunnel to Celestic needs Rock Smash and Strength

- The walk is Eterna, then Route 211 West, then `MT_CORONET_1F_NORTH_ROOM_1` (enter at warp (2,41), leave
  at warp (29,35)), then Route 211 East, then Celestic.
- Both outdoor halves are open with no field moves (BFS over collision with the obstacle objects blocking).
  The Route 211 East Cut tree (423,533) and its rocks are off the path.
- `MT_CORONET_1F_NORTH_ROOM_1` is not open:
  - Out of the west pocket: either the Rock Smash rock at (10,36), or the Strength boulder at (15,34).
  - Then east: either the Strength boulder at (18,39), or the one at (18,43). There is no other way to the
    east exit.
  - Checked by BFS (`/tmp/a2/r0/bfs211.py`): no field moves, Rock Smash only, Cut only, and Rock Smash + Cut
    all fail. Removing boulder (18,39) and smashing rock (10,36) succeeds.
- In the new order, Rock Smash is available from state 15 (Coal Badge + Hitmonlee totem + Resonator, per
  `src/field_move_tasks.c`). **Strength is not** (Mine Badge + Aggron, Arc 3).
- **Action for s-celestic** (owns `mt_coronet_1f_north_room_1`): remove the Strength boulder
  `MT_CORONET_1F_NORTH_ROOM_1_STRENGTH_BOULDER_9` at (18,39) from the events JSON. Its hide flag is
  `FLAG_UNK_0x0029`, a map-local temporary that resets on every load, so deletion is the reliable fix. Keep
  the rock at (10,36) as the Resonator Rock Smash beat.
- The stock Galactic grunts in this room are there too: (19,41) beside the path, and (14,10)/(14,11). They
  are hidden by stock flags; s-celestic should confirm they stay hidden in Arc 2.

### How stock Platinum switches Lake Valor to its drained header

- `MAP_HEADER_VALOR_LAKEFRONT` has two warp pairs on the same tiles, (717,760) and (717,761):
  - warps 3/4 lead to `MAP_HEADER_LAKE_VALOR_DRAINED`;
  - warps 5/6 lead to `MAP_HEADER_LAKE_VALOR` (full).
- `scripts_valor_lakefront.s` entries 1 and 2 (`_0026` OnTransition, `_0061` OnResume) move the unused pair
  off the path with `SetWarpEventPos ... 0x2C9 (713), 0x2F8/0x2F9`:
  - `FLAG_GALACTIC_LEFT_LAKE_VALOR` **unset**: warps 5/6 move away, so the lakefront leads to the **drained**
    lake;
  - flag set: warps 3/4 move away, so it leads to the full lake.
- The flag is set only by post-Galactic-HQ scripts (`scripts_galactic_hq_1f.s`, `scripts_valor_cavern.s`,
  `scripts_sendoff_spring.s`) and `events_route_207.json`.
- D12 (the Basin always drained) therefore holds as long as nobody sets `FLAG_GALACTIC_LEFT_LAKE_VALOR` in
  Arc 2. No header edit is needed.
- `FLAG_ALT_MUSIC_LAKE_VALOR` (`src/system_flags.c`) picks the drained map's music.
- s-pastoria owns `lake_valor_drained`, which still holds the stock Galactic grunts and Magikarp
  (`events_lake_valor_drained.json`). s-route214 owns `valor_lakefront` and must keep its two warp entries.


## Orchestrator ruling (2026-10-11 00:45): Lost Tower
- The 2F rift object is at (6,8), where the stock Spiritomb stood (owned by s-hearthome).
- First visit exit (progress 92-93): `Warp MAP_HEADER_ROUTE_209_LOST_TOWER_2F, 0, 7, 8, DIR_EAST`.
- Second visit exit, after the 95 calm: `Warp MAP_HEADER_ROUTE_209, 0, 568, 681, DIR_SOUTH` (outside the Lost Tower door, where
  s-hearthome stages the aftermath).
- The vein flag is `FLAG_ARC2_RIFTB_E` (0x092F), per the screenplay. It supersedes `FLAG_ARC2_RIFTB_C` above.
