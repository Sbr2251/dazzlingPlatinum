# Verity Castle 1F (entrance hall)

The first floor inside the castle on Lake Verity is a basic stone hall. It has one stair down, which leads to the stock Verity Cavern and is blocked for now. It replaces the earlier 2F/3F placeholders, which used the Snowpoint Temple matrices: 2F was renamed to 1F and 3F was deleted.

## Indices

| What | Value |
| --- | --- |
| Map header | `MAP_HEADER_VERITY_CASTLE_1F` (enum 593) |
| Map matrix | 289 (`map_matrix_289.json`, name `m_vcastle1`, one chunk: `[[MAP_666]]`) |
| Map data | 666 (`map_data_666.bin`, `MAP_666` in `generated/maps.txt`) |
| Texture set | 075 (`map_texture_set_075.nsbtx`) |
| Area data | entry 0x4C (76) in `area_data.narc`: props list 21, texture set 75, light 1 |
| Events | `events_verity_castle_1f.json` |

The props list, 21, is the minimal stock indoor list. It holds model 78 (d_mat01, the indoor exit mat) and model 152, and the stock Oreburgh Gym area uses it too. Light 1 is the indoor area light, the same one the Old Chateau (area 66) uses.

## Header

The fields follow the Old Chateau interior: `CAMERA_TYPE_INTERIOR_ORTHOGRAPHIC`, mapType 3, `BACKGROUND_INDOORS_3`, clear weather, no encounters, and no bike, running, Escape Rope or Fly. It uses `scripts_verity_castle_1f` (the stair signboard) and `scripts_init_empty`, the text bank `TEXT_BANK_VERITY_CAVERN` (the sign text `VerityCastle1F_Text_OldPathBoardedUp` is appended to it) and the map label `LocationNames_Text_VerityCastle`.

**Music: `SEQ_PL_BF_CASTLE` day and night.** The Battle Castle theme: stately and grand rather than tense, and literally Platinum's castle music. The Verity Cavern theme below the stair plays once the stair is opened.

**Stair signboard.** A signboard object (`OBJ_EVENT_GFX_SIGNBOARD`, local id 0, script 1) stands at (9,5), in front of the barricaded stair. Read it from (9,6) facing north: "An old path that's been boarded up." (`ShowScrollingSign`). Remove the object when the stair is unblocked.

## Layout

Coordinates are chunk tiles, which are also absolute tiles because the map is one chunk. x runs east and z runs south. The room sits in the north-west of the chunk inside a blocked ring, like the stock interiors. `tools/lake_verity/interior_layout.py` is the single source of these values.

```
    x: 0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18
 3 ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##   north wall (torches, 2 sigil banners)
 4 ## ## .. .. .. .. .. .. .. S# ## ## ## ## .. .. .. ## ##   S# = stair warp, blocked; ## at 10..13 = stairwell
 5 ## ## .. .. .. .. .. .. .. .. ## ## ## ## .. .. .. ## ##
 6 ## ## .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ## ##
 8 ## ## .. .. .. ## .. .. .. .. .. .. .. ## .. .. .. ## ##   pillars (5,8), (13,8)
12 ## ## .. .. .. ## .. .. .. .. .. .. .. ## .. .. .. ## ##   pillars (5,12), (13,12)
15 ## ## .. .. .. .. .. .. .. EX .. .. .. .. .. .. .. ## ##   EX = exit mat
16 ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##
```

- **Walkable floor:** x 2..16, z 4..15, collision 0x00. The Old Chateau's 0x0B floor carries the encounter flag, so it is not used here.
- **Walls:** stone walls on x 1, x 17 and z 3, 5 tiles high, with a cornice. The south edge (z 16) is blocked and drawn black, like the stock interiors.
- **Carpet:** a red carpet with a gold hem runs from the exit mat north to the stair landing.
- **Pillars:** four pillars, each with a sconce torch. The pillar tiles are blocked.
- **Torches and banners:** two wall torches and two banners carrying the Verity sigil on the north wall. The torches are static geometry with baked light pools; there are no `fldtanime` entries.
- **Exit mat (9,15):** collision 0x65, the stock indoor exit mat, which fires when you press south. The mat is drawn by the stock prop model 78, placed like the Old Chateau's.
- **Stair (9,4):** collision 0x5E (WARP_STAIRS_EAST), which fires when you press east. It is currently 0x805E (blocked). The stairwell descends east over x 10..13, z 4..5 (all blocked). On arrival from a 0x5E warp the engine places the player one tile east of the warp tile, (10,4), facing west, and walks them onto it. That is why the stair visually lies east of the warp tile.
- **Barrier:** crates and rubble on (9,4), wooden boards over the stairwell and two cross boards. All of it uses the existing `lv_wood` and `lv_stone` textures.
- **BDHC:** one flat plate at floor height (world y 0) over x 1..17, z 3..16.

## Warps

| Map | # | Tile | Behaviour | Destination |
| --- | --- | --- | --- | --- |
| Verity Castle 1F | 0 | exit mat (9,15) | 0x65 | Lake Verity #0 (DOOR_1F (32,33)) |
| Verity Castle 1F | 1 | stair (9,4) | 0x5E, blocked (0x805E) | Verity Cavern #0 |
| Verity Cavern | 0 | (14,29) | 0x6F | Verity Castle 1F #1 |
| Lake Verity | 0 | DOOR_1F (32,33) | 0x6E | Verity Castle 1F #0 (from the exterior agent's events change) |

No field script `Warp` targets Verity Cavern or the castle. The only related script command is `SetFlag FLAG_FIRST_ARRIVAL_VERITY_CAVERN` in `scripts_verity_cavern.s`.

## Files and tools

- `tools/lake_verity/interior_layout.py` holds the tile contract: collision grid, warps, pillars, stair and barrier. Run it to print the map.
- `~/Documents/Lake Verity Update/art/lv_interior.py` is the Blender art script. It uses `lv_geom.py`, bakes torch light and ambient into the vertex colours, and exports `tools/lake_verity/assets/interior_1f/interior_1f.mesh.json`. Run it with `LV_REPO=<repo> Blender -b --factory-startup -P lv_interior.py`.
- `tools/lake_verity/build_interior.py` builds the model, texture set 075, permissions, the exit-mat prop and the BDHC, and runs the checks below. Without flags it is a dry run. `--write` writes map_data 666, set 075, matrix 289 and area entry 0x4C, and registers them in the `meson.build` files, the `.order` files and `generated/maps.txt`. Re-running it is idempotent: a second `--write` leaves identical bytes. `--preview <dir>` writes the meshes for `blender_preview.py`.
- `tools/lake_verity/blender_preview.py` has two new options. `--bg r,g,b` sets the background colour. `--dscolor` modulates texture by vertex colour in display space the way the DS does; without it, dark vertex colours preview much too bright.

## Budgets

| Item | Value | Limit |
| --- | --- | --- |
| Polygons | 413 (the whole room) | 2048 per frame |
| Model (NSBMD) | 22384 B | 61440 B buffer |
| Vertices / materials | 1516 / 7 | |
| Texture set 075 VRAM | 10752 B texels + 256 B palettes = 11008 B | largest stock set is 76416 B |
| BDHC | 66 B | |
| map_data_666.bin | 24562 B | |

Set 075 holds the textures `lv_flame`, `lv_glow`, `lv_paving`, `lv_sigil`, `lv_stone`, `lv_trim` and `lv_wood`.

## Checks (build_interior.py, all pass)

- NSBMD build, parse and rebuild give identical bytes, and the parsed faces equal the mesh faces.
- The NSBTX rebuild is identical, every texture decodes back to its PNG, and every texture the model uses is present.
- The map_data pack/unpack round trip is identical.
- The permissions equal `interior_layout.grid()`.
- The BDHC height at every tile matches `interior_layout.height()`, including the arrival tile (10,4).
- The exit mat and stair collision values are as expected.
- The warps in `events_verity_castle_1f.json` equal `interior_layout.WARPS`.
- Model 78 is in props list 21.
- The budgets pass via `assemble.check_budgets`.

Outside the script, I checked that `area_data.narc` has 77 entries and entries 0..75 are unchanged, and that a second `--write` is byte-identical. Previews are in `~/Documents/Lake Verity Update/pipeline_checks/interior_1f_top.png` and `interior_1f_game.png` (in-game orthographic camera from the entrance). They were rendered with `--dscolor`.

**The ROM has not been built.**

## Unblocking the stair later

1. In `interior_layout.py`, set `BARRIER_TILES = ()`. That clears bit 15 on (9,4), so the tile becomes plain 0x5E.
2. In `lv_interior.py` `main()`, drop the `barricade()` call.
3. Re-run `lv_interior.py`, then `build_interior.py --write`.

The warps are already in place: pressing east on (9,4) leads to Verity Cavern, and the cavern's exit returns to (9,4).

## Open questions and risks

- **events_lake_verity.json on this branch** still has warps 3 and 4 to `MAP_HEADER_VERITY_CASTLE_2F` / `_3F`, and warp 0 still goes to Verity Cavern. I was not allowed to edit that file. The exterior agent's worktree already points warp 0 at 1F #0 and removes warps 3 and 4. **The build fails until that change is merged**, because the 2F/3F constants no longer exist.
- **Index collision:** `build_art.py --new-set` also uses texture set 75 and area entry 76 (0x4C). If both land, one of them must move to the next free index. `build_interior.py` refuses to overwrite an area entry that uses a different set.
- **Mesprit and Verity Cavern are unreachable** while the stair is blocked. That includes Mesprit (`FLAG_MESPRIT_DISAPPEARED`), the Rowan object and `FLAG_FIRST_ARRIVAL_VERITY_CAVERN`. If the story needs Mesprit before the stair opens, it has to move.
- **Old saves inside Verity Cavern:** leaving through (14,29) puts the player at (10,4), and the engine then forces a walk west onto the blocked (9,4). I believe the forced arrival step ignores collision, but this is unverified. The worst case is that the player stays on (10,4), which is inside the blocked stairwell and has no exit. Unblocking the stair, or temporarily making (10,4) walkable, would fix it.
- **Hardware look:** the brightness is tuned so vertex colours average about 0.65, like the stock chateau, but it has not been checked on a DS or emulator.
- **Art script location:** `lv_interior.py` lives next to `lv_geom.py` outside the repo. Only its export (`interior_1f.mesh.json`) is committed.
