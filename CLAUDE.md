# Dazzling Platinum ROM Hack

## Build & Test Workflow

- **Build on the devserver or on a Mac.** Both are supported; the commands are the same.
  - **Devserver:** `/data/repos/dazzlingPlatinum`. `make release` fetches the toolchain itself (MetroSkrew/mwccarm into `tools/metroskrew`, meson and the subprojects into `subprojects/`); the system needs `libpng-devel`.
  - **Mac (Apple silicon):** any clone of the repo. Install the dependencies listed in INSTALL.md's MacOS section: Xcode Command Line Tools; `brew install gcc@14 ninja libpng pkg-config arm-none-eabi-gcc xz`; `brew install --cask wine-stable`. The first `make release` downloads the rest of the toolchain (`tools/metroskrew`, `subprojects/`).
    - mwccarm runs through Wine. Authorize Wine once: in Applications, Control-click Wine Stable, then Open.
    - Run the build from a logged-in Terminal session. Wine fails with `wineserver: Can't check in server_mach_port` when started from a background or daemon process, for example a remote agent node; that is the environment, not the repo.
  - There is no separate VM.
- Build with `make release`. The ROM is hardlinked to `out/dazzlingPlatinum.nds`, outside `build/`. Meson's own output, `build/pokeplatinum.us.nds`, is still there; set `OUT=<dir>` to put it somewhere else.
  - Don't use plain `make` (`make all`). It also runs `check`, which compares the ROM against the vanilla SHA1 and always fails for this hack.
  - Only one build can use `build/` at a time. "Some other Meson process is already using this build directory" means another build is running; wait for it rather than deleting the lock.
- Smoke-test the ROM headlessly with py-desmume, using `SDL_VIDEODRIVER=dummy` with the right venv for the machine:
  - **Devserver:** `~/.venvs/desmume39/bin/python` (system Python 3.9). The Python 3.12 venv `~/.venvs/desmume` is built on fbcode's Python, which cannot find the system `libglib-2.0.so.0`, so it fails on devservers.
  - **Mac:** `~/.venvs/desmume/bin/python` (Python 3.12).
- When the ROM builds, commit and push the branch so the user can test on hardware or their own emulator.

## Important: Text Encoding

- **Always use straight/ASCII apostrophes** (`'` U+0027) in all text files, never curly/smart apostrophes (`'` `'` U+2018/U+2019)
- Curly apostrophes cause build errors in the NDS text compiler
- When adding text to JSON files (`res/text/*.json`), double-check for curly quotes/apostrophes before saving

## Repo layout (synced to pret on 2026-11-10)

The hack was merged onto current pret (branch `sync/pret-2026-11`). pret's layout replaced several older conventions:
- Each map's files live in `res/field/maps/<map>/`: `scripts.s`, `init.s`, `events.json`, `encounters.json`, `header.json`. Map groups and matrices are in `res/field/maps/groups.json`.
- Events reference scripts **by label** (`"script": "Route206_Hiker"`), not by `7000 + index` numbers.
- Text banks are generated: scripts include `res/text/bank/<map>.h` and use named message IDs (`Route206_Text_...`). Move and item names and descriptions come from each move's or item's data file.
- Sound is vanilla pret. The hack has no custom music, and the Gen 5 species reuse vanilla cries.
- Sound constants take the `_sseq` suffix (`SEQ_SE_DP_BEEP_sseq`).
- Trainer parties use `iv_scale`, not `power`. An optional per-member `ability` override is supported by `tools/dataproc/src/trainerproc.c`.
- The build needs the system libpng headers (`libpng-devel` on the devserver).

## Adding a New Move

1. **Constant:** add `MOVE_<NAME>` to `generated/moves.txt` before `MAX_MOVES`. The enum value is the 0-indexed line position.
2. **Move directory:** create `res/moves/<move_name>/` (the directory name maps to `MOVE_<NAME>`) containing:
   - `data.json`: `name`, `description` (lines ending in `\n`), `class`, `type`, `power`, `accuracy`, `pp`, `effect` (`type` and `chance`), `range`, `priority`, `flags`, `contest`. Copy an existing move such as `res/moves/moonblast/data.json`. The name and description text banks are generated from this file; do not edit `res/text/move_*.json`.
   - `anim.s`: the battle animation (`#include "macros/btlanimcmd.inc"`). Particle files (`.spa`) are prebuilt in `res/battle/particles/`; reuse existing ones.
     - Key pattern: `LoadParticleResource` → `CreateEmitter` → `Func_MoveEmitterA2BLinear` → impact effects → `UnloadParticleSystem` → `End`.
     - Colors: `include/constants/battle/battle_anim.h`. Background IDs: 42 (cosmic/lunar), 54 (night sky), 10 (misty).
     - Templates: `flash_cannon_spa`, `energy_ball_spa`, `shadow_ball_spa` (projectiles); `moonlight_spa`, `lunar_dance_spa`, `luster_purge_spa` (effects).
   - `script.s`: the battle logic (`#include "macros/btlcmd.inc"`). It is usually just `GoToEffectScript`, which dispatches on the move's `BATTLE_EFFECT_*`.
3. **Learnsets:** add the move to `res/pokemon/<species>/data.json` → `learnset.by_level` as `[level, "MOVE_<NAME>"]`. Stone evolutions use level 1; level-up evolutions use mid-to-late levels.
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
   - Add an object to `res/field/maps/<map>/events.json` → `object_events`:
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
