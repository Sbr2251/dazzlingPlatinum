# Arc 1 story rewrite, part 1: contract

> **SUPERSEDED. Kept for history only.** This is the part 1 contract for branch `arc1-lake-verity-story`.
> `docs/arc1/revision/spec.md` replaced it, and `docs/arc1/part2/spec.md` covers part 2. Workstream ownership
> and story-state values here are out of date.


Branch `arc1-lake-verity-story` (off `main`). This part covers a new game up to Cyrus and Barry leaving
Lake Verity. Everything after that is "to be continued" on Route 201.

The screenplay is in `docs/arc1/screenplay.md`. This file is the contract between the workstreams: shared
names, story state, who owns which file, and how to build.

## Story state

Two names are reserved in `generated/vars_flags.txt`:

| name | meaning |
|---|---|
| `VAR_ARC1_PROGRESS` (was `VAR_UNUSED_0x406C`) | Arc 1 opening progress (values below) |
| `FLAG_LAKE_VERITY_PORTAL_HIDDEN` (was `FLAG_UNUSED_2422`) | set: the Lake Verity portal prop (model 581) is hidden and its bg events are inert |

`VAR_ARC1_PROGRESS` values:

| value | state | set by |
|---|---|---|
| 0 | new game; the Distortion World flashback plays | (default) |
| 1 | the flashback is done; the Cyrus roof landing plays at Lake Verity | Opening (before warping to Lake Verity) |
| 2 | the roof landing is done; the player is in the bedroom and the TV interview plays | Lake Verity (before warping to the bedroom) |
| 3 | the TV and Barry's upstairs scene are done; the player is heading to Lake Verity with Barry | Intro & home |
| 4 | the Lake Verity scene is done (Cyrus and Barry have left); Route 201 shows "to be continued" | Lake Verity |

Stock story vars (`VAR_PLAYER_HOUSE_STATE`, `VAR_FOLLOWER_RIVAL_STATE`, `VAR_VISITED_LAKE_VERITY_WITH_RIVAL`,
`VAR_RIVAL_HOUSE_STATE`, and so on) keep working. Each owner sets them however its own scripts need, and writes
down in its report what it set.

## Handoff warps

| from | to | how |
|---|---|---|
| Rowan intro | the flashback map | new-game spawn (`src/location.c` / `FieldSystem_InitNewGameState`), owned by Opening |
| flashback (Opening) | Lake Verity roof | `SetVar VAR_ARC1_PROGRESS, 1`, then `Warp MAP_HEADER_LAKE_VERITY, 0, 32, 31, DIR_NORTH` (terrace tile just south of the portal footprint). The Lake Verity script takes over on arrival: hides the player, and so on. |
| roof landing (Lake Verity) | bedroom | `SetVar VAR_ARC1_PROGRESS, 2`, then `Warp MAP_HEADER_TWINLEAF_TOWN_PLAYER_HOUSE_2F, 0, 4, 6, DIR_NORTH` (the stock new-game start tile). The bedroom script (Intro & home) plays the TV scene when `VAR_ARC1_PROGRESS == 2`. |
| Route 201 (Intro & home) | Lake Verity | the normal map connection/warp into Lake Verity with `VAR_ARC1_PROGRESS == 3`. Barry doesn't have to physically follow: the Lake Verity script spawns its own Barry for the scene. |
| Lake Verity scene | free roam | `SetVar VAR_ARC1_PROGRESS, 4`. The player walks back out; Route 201 shows the "to be continued" block. |

## New engine interface (Engine owns the C side; everyone else only calls it)

Script commands, added to `asm/macros/scrcmd.inc` and `src/scrcmd.c`:

- `SetLakeVerityPortalHidden <0|1>`: shows or hides the loaded portal prop (build model 581, `d5_ana_pl`)
  immediately, and sets or clears `FLAG_LAKE_VERITY_PORTAL_HIDDEN` to match. Does nothing on other maps.
- On every Lake Verity map/chunk load, when `FLAG_LAKE_VERITY_PORTAL_HIDDEN` is set, the portal prop is hidden
  automatically (via `MapProp_SetHidden`), so it stays gone across warps, saves and reloads.
- `StartArc1MawileBattle`: a scripted wild battle against Mawile Lv3, ability Hyper Cutter, moves Astonish and
  Fake Tears (no other moves). Like `StartFirstBattle`: losing does not white out, and the script continues
  after the battle either way. Running is not allowed (or has no effect) and catching is not allowed. The script
  heals the party afterwards with `HealParty`. The command waits for the battle to end, like `StartFirstBattle`.

## New overworld sprite (Sprite owns this)

- `OBJ_EVENT_GFX_MAWILE`, a new constant in `generated/object_events_gfx.txt`, appended (append-only, like the
  totem sprites in `tools/integrate_totem_overworld_sprites.py`). For now it points to a copy of a stock
  Pokemon overworld sprite. The user will supply an HGSS Mawile sprite later, so swapping the art must mean
  replacing a single file and rebuilding.

## File ownership

Only edit files you own. If the build fails in a file you don't own, it's another workstream's work in
progress: wait a minute and rebuild (up to about 15 minutes), and don't touch that file. If you need something
from a file you don't own, put it in your final report.

| workstream | owns |
|---|---|
| Starters | `src/choose_starter/**`; `generated/trainers.txt`; `res/trainers/**`; the starter-related lines that commit 09e600d51 changed in field scripts **other than** Lake Verity, Twinleaf and Route 201 files; in `scripts_route_201.s`, only the existing `StartFirstBattle` block/labels; `res/text/unk_0360.json` |
| Intro & home | `src/applications/rowan_intro/**` and its text; `scripts_twinleaf_town*.s`, `scripts_init_twinleaf_town*.s`, and their text JSONs; `scripts_route_201.s` and `scripts_init_route_201.s` (except the StartFirstBattle block), `res/field/events/events_route_201.json`, `events_twinleaf_town*.json`, and their text |
| Opening | `src/location.c`; `src/field_map_change.c`; `res/field/scripts/scripts_init_new_game.s`; `scripts_distortion_world_giratina_room.s`, `scripts_init_distortion_world_giratina_room.s`, `events_distortion_world_giratina_room.json`, and their text (or new files for a flashback-only map/script if needed) |
| Engine | `src/scrcmd.c`; `asm/macros/scrcmd.inc`; `include/scrcmd.h`; `src/overlay005/**`; `src/encounter.c`; `include/encounter.h`; new C files it adds |
| Sprite | `generated/object_events_gfx.txt`; `res/field/**/mmodel*` / overworld sprite data; `src/overlay005/` sprite tables *only* if the sprite requires it (coordinate through the report); a new `tools/` script |
| Lake Verity | `scripts_lake_verity.s`, `scripts_init_lake_verity.s`, `events_lake_verity.json`, `res/text/lake_verity.json`, and new movement/text for Lake Verity; `docs/lake_verity_redesign/gameplay.md` |
| me (lead) | `generated/vars_flags.txt`, `docs/arc1/**` |

Nobody commits. The lead commits by path at the end.

## Build and test

- Always build with `flock /tmp/dp-build.lock make release` (from `/data/repos/dazzlingPlatinum`). Never plain
  `make`, never delete the Meson lock, and never run a build without the flock.
- The ROM is `out/dazzlingPlatinum.nds`. Copy it somewhere private before testing
  (`cp out/dazzlingPlatinum.nds /tmp/<you>.nds`), because the next build overwrites it.
- Headless emulator: `~/.venvs/desmume/bin/python` with py-desmume. Helpers are in `tools/`
  (`make_desmume_dsv.py`, `platinum_save_utils.py`, `verify_platinum_save.py`, `tools/debug/`).
- Text: ASCII apostrophes and quotes only in any text you add. Keep message boxes to the stock line width
  (look at neighbouring messages).
