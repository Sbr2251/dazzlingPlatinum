# Dazzling Platinum (macOS & iOS)

## Build & Test Workflow

- **Targets: macOS (Apple Silicon) and iOS (arm64)** via SDL3 + Metal. The NDS ROM build path has been removed; code is free to use native memory, wider 2D/3D assets, and Metal/SDL3 features.
- **macOS build:** `tools/macos/build.sh [dev|release|asan]` (or `make macos` / `make macos-release` / `make macos-asan`). Outputs `build_macos[_release|_asan]/Dazzling Platinum.app`.
  - Rebuild after edits with `ninja -C build_macos` (or `build_macos_release`), with `LIBRARY_PATH`/`CPATH` set to `/opt/homebrew` plus `$DEPS/prefix` (default `../pokeplatinum-macos-deps/prefix`).
- **iOS build:** `tools/ios/build.sh [device|sim] [--dev|--release]` (see `docs/ios.md`). Outputs `build_ios[_sim]/Dazzling Platinum.app` (plus `build_ios/DazzlingPlatinum.ipa` for device).
- **Adding C source files:** add new game `.c` files directly to `src/meson.build` (or port-only files to `pokeplatinum_port_c` in `meson.build`).
- **Saves & app data:** live in `~/Library/Application Support/Dazzling Platinum` on macOS (and the app's Documents folder on iOS). `save.bin` is a raw 512 KB save; `Cmd+E`/`Cmd+I` export and import `.sav`/`.dsv`. Inspect/edit saves with `tools/dazzling/save_tool.py info|edit`.
- **64-bit clang C rules:**
  - include the header for every function called (clang rejects implicit declarations);
  - never store a pointer in a `u32`: use `uPtr` for pointer arithmetic and alignment;
  - never pass `NULL` for an integer parameter.
- **Simulator (`libntr`) fixes:** edit inside `subprojects/libntr` and regenerate `tools/macos/patches/libntr.patch` with `git -C subprojects/libntr add -N . && git -C subprojects/libntr diff HEAD > tools/macos/patches/libntr.patch` (and verify with `git apply --check` against the revision pinned in `tools/macos/patches/REVISIONS`).
- **Field script safety:** after editing field scripts, run `python3 tools/dazzling/test/static_checks.py` (which includes `check_script_targets` and catches invalid GoTo/Call targets, missing text labels, WaitFanfare hazards, and infinite self-loops).
- **Headless testing:** debug automation variables are listed in `README_macOS.md`, e.g. `SIM_DEBUG_FAST=1 SIM_DEBUG_IMPORT_SAVE=20:<save> SIM_DEBUG_KEYS=... SIM_DEBUG_SHOT_DIR=... SIM_DEBUG_EXIT_FRAME=...`.
- When a change builds and passes checks, commit and push the branch so the owner can test it.

## Test suite (tools/dazzling/test/)

- Static checks (no game build): `python3 tools/dazzling/test/static_checks.py`
- Scenario suite (headless lockstep): `python3 tools/dazzling/test/run.py -j 2`
- Record reference screenshots: `python3 tools/dazzling/test/run.py --record --filter title`
- Runner unit tests against the mock game: `python3 tools/dazzling/test/test_runner.py`
- Script coverage report: `python3 tools/dazzling/test/coverage.py <coverage.txt>` (game side: `SIM_SCRIPT_COVERAGE=<file>`)
- Scenario format, state paths and coverage details: `tools/dazzling/test/README.md`.

## Important: Text Encoding

- **Always use straight/ASCII apostrophes** (`'` U+0027) in all text files, never curly/smart apostrophes (`'` `'` U+2018/U+2019)
- Curly apostrophes fail `static_checks.py` and the text compiler (`msgenc`)
- When adding text to JSON files (`res/text/*.json`), double-check for curly quotes/apostrophes before saving

## Repo layout

- Each map's files live in `res/field/maps/<map>/`: `scripts.s`, `init.s`, `events.json`, `encounters.json`, `header.json`. Map groups and matrices are in `res/field/maps/groups.json`.
- Events reference scripts **by label** (`"script": "Route206_Hiker"`), not by `7000 + index` numbers.
- Text banks are generated: scripts include `res/text/bank/<map>.h` and use named message IDs (`Route206_Text_...`). Move and item names and descriptions come from each move's or item's data file.
- Sound constants take the `_sseq` suffix (`SEQ_SE_DP_BEEP_sseq`).
- Trainer parties use `iv_scale`, not `power`. An optional per-member `ability` override is supported by `tools/dataproc/src/trainerproc.c`.
- Asset-pipeline script assemblers still use Homebrew `arm-none-eabi-gcc` / `arm-none-eabi-objcopy` to compile field scripts, battle scripts, move animations, and trainer AI bytecode.

## Adding a New Move

1. **Constant:** add `MOVE_<NAME>` to `generated/moves.txt` before `MAX_MOVES`. The enum value is the 0-indexed line position.
2. **Move directory:** create `res/moves/<move_name>/` (the directory name maps to `MOVE_<NAME>`) containing:
   - `data.json`: `name`, `description` (lines ending in `\n`), `class`, `type`, `power`, `accuracy`, `pp`, `effect` (`type` and `chance`), `range`, `priority`, `flags`, `contest`. Copy an existing move such as `res/moves/moonblast/data.json`. The name and description text banks are generated from this file; do not edit `res/text/move_*.json`.
   - `anim.s`: the battle animation (`#include "macros/btlanimcmd.inc"`). Particle files (`.spa`) are prebuilt in `res/battle/particles/`; reuse existing ones.
     - Key pattern: `LoadParticleResource` -> `CreateEmitter` -> `Func_MoveEmitterA2BLinear` -> impact effects -> `UnloadParticleSystem` -> `End`.
     - Colors: `include/constants/battle/battle_anim.h`. Background IDs: 42 (cosmic/lunar), 54 (night sky), 10 (misty).
     - Templates: `flash_cannon_spa`, `energy_ball_spa`, `shadow_ball_spa` (projectiles); `moonlight_spa`, `lunar_dance_spa`, `luster_purge_spa` (effects).
   - `script.s`: the battle logic (`#include "macros/btlcmd.inc"`). It is usually just `GoToEffectScript`, which dispatches on the move's `BATTLE_EFFECT_*`.
3. **Learnsets:** add the move to `res/pokemon/<species>/data.json` -> `learnset.by_level` as `[level, "MOVE_<NAME>"]`. Stone evolutions use level 1; level-up evolutions use mid-to-late levels.
4. **Reference:** `generated/battle_move_effects.txt`, `generated/move_flags.txt`, `generated/move_ranges.txt`, `res/battle/particles/battle_particles.order`, `asm/macros/btlanimcmd.inc`, `asm/macros/btlanimfunc.inc`.

## Adding a New Item (with Bag Icon and Overworld Pickup)

1. **Constant:** add `ITEM_<NAME>` to `generated/items.txt`. The enum value is the 0-indexed line position. The hack reuses unused vanilla slots, e.g. the Mega Stones after `ITEM_GRISEOUS_ORB`.
2. **Item data:** create `res/items/data/<name>.json`, where the file stem is the lowercased constant without `ITEM_`. Copy a similar item, e.g. `res/items/data/garchompite.json`.
   - Fields: `name`, `plural`, `article` (`a`/`an`), `description` (lines ending in `\n`), `icon` (`sprite`/`palette`), price, effects, pockets, use functions.
   - The four item text banks are generated from this file. A missing `article` or `plural` gives "picked up ???".
3. **Bag icon:** add `<name>.png` and `<name>.pal` to `res/items/icons/`.
   - PNG: 32x32, **4-bit** indexed (8-bit corrupts the sprite), content centered around (12, 12), palette index 0 = transparent (180, 180, 180).
   - PAL: JASC-PAL with CRLF line endings and 256 entries (16 used, the rest `0 0 0`).
   - Register the files in `res/items/icons/meson.build` and in `res/items/item_icon.order` (before the `none` entries).
   - Point the item JSON's `icon` at `<name>_NCGR` / `<name>_NCLR`. Items can share an icon, e.g. all Mega Stones use `mega_stone`.
4. **Ground pickup on a map:**
   - Add a script to `res/field/scripts/visible_items.s`. Add `ScriptEntry VisibleItems_<Map>_<Item>` to the entry list (before `ScriptEntryEnd`), then the block:
     ```asm
     VisibleItems_<Map>_<Item>:
         SetVar VAR_0x8008, ITEM_<NAME>
         SetVar VAR_0x8009, 1
         GoTo VisibleItems_TryGiveItem
         End
     ```
   - Add an object to `res/field/maps/<map>/events.json` -> `object_events`:
     ```json
     {
         "id": "LOCALID_ITEM_<NAME>",
         "graphics_id": "OBJ_EVENT_GFX_POKEBALL",
         "movement_type": "MOVEMENT_TYPE_NONE",
         "trainer_type": "TRAINER_TYPE_NONE",
         "hidden_flag": "FLAG_OBTAINED_<MAP>_<NAME>",
         "script": "VisibleItems_<Map>_<Item>",
         "initial_dir": "DIR_NORTH",
         "data": [],
         "movement_range_x": 0,
         "movement_range_z": 0,
         "x": <grid_x>,
         "z": <grid_z>,
         "y": 0
     }
     ```
   - `hidden_flag` must be an unused flag. Name a free slot in `generated/vars_flags.txt`; never shift existing entries, because flag numbers are stored in saves.
   - Use coordinates near existing items on the same map.

## Renderer (SDL3 GPU / Metal)

- The SDL3 GPU API (Metal on macOS and iOS) is the primary render backend. On macOS, OpenGL remains available as a fallback (`Renderer=gl` in `sim_config.ini` or `SIM_RENDERER=gl`); iOS is Metal-only.
- Architecture and verification details: `docs/sdl_gpu_migration/PLAN.md`. A/B backend verification: `python3 tools/dazzling/test/run.py --compare-backends`.
