# Dazzling Platinum ROM Hack

## Build & Test Workflow

- **Do NOT build locally.** The project requires a cross-compilation toolchain (MetroSkrew/mwccarm) that runs on a separate VM.
- When changes are ready to test, commit and push to the branch. The user will build and test on their VM.

## Important: Text Encoding

- **Always use straight/ASCII apostrophes** (`'` U+0027) in all text files, never curly/smart apostrophes (`'` `'` U+2018/U+2019)
- Curly apostrophes cause build errors in the NDS text compiler
- When adding text to JSON files (`res/text/*.json`), double-check for curly quotes/apostrophes before saving

## Adding a New Move

To add a new move (e.g., Moonblast), follow these steps:

### 1. Register the move constant
- **File:** `generated/moves.txt`
- Add `MOVE_<NAME>` before the `MAX_MOVES` line
- The enum value is the 0-indexed line position (MOVE_NONE=0, MOVE_POUND=1, etc.)

### 2. Add text entries
- **`res/text/move_names.json`** — Add `{"id": "pl_msg_00000647_NNNNN", "en_US": "Move Name"}` at end of array
- **`res/text/move_names_uppercase.json`** — Add `{"id": "pl_msg_00000648_NNNNN", "en_US": "MOVE NAME"}` at end of array
- **`res/text/move_descriptions.json`** — Add `{"id": "pl_msg_00000646_NNNNN", "en_US": [...]}` at end of array
- NNNNN is the 0-indexed move number (e.g., 00468 for the first new move after Shadow Force)

### 3. Create move data
- **File:** `res/battle/moves/<move_name>/data.json` (new directory + file)
- Fields: name, class, type, power, accuracy, pp, effect (type + chance), range, priority, flags, contest
- The build system auto-discovers this via `generated/moves.txt` → `meson.build`

### 4. Create battle animation
- **File:** `res/battle/moves/<move_name>/anim.s`
- Uses `#include "macros/btlanimcmd.inc"` (NOT `.include`)
- Particle files (`.spa`) are prebuilt binaries in `res/battle/particles/` — reuse existing ones
- Key pattern: `LoadParticleResource` → `CreateEmitter` → `Func_MoveEmitterA2BLinear` → impact effects → `UnloadParticleSystem` → `End`
- Color constants in `include/constants/battle/battle_anim.h` (e.g., `BATTLE_COLOR_LIGHT_RED` for pink)
- Background IDs: 42 (cosmic/lunar), 54 (night sky), 10 (misty)
- Good projectile templates: `flash_cannon_spa`, `energy_ball_spa`, `shadow_ball_spa`
- Good effect templates: `moonlight_spa`, `lunar_dance_spa`, `luster_purge_spa`

### 5. Battle logic script
- **File:** `res/battle/scripts/moves/move_script_NNNN.s` — already exists up to 0500 as placeholders
- Most just contain `GoToEffectScript` which dispatches to the effect script for the move's `BATTLE_EFFECT_*`
- No manual changes needed if the effect type already exists

### 6. Add to Pokemon learnsets
- **Files:** `res/pokemon/<species>/data.json`
- Add to `learnset.by_level` array as `[level, "MOVE_<NAME>"]`
- Stone evolutions use level 1; level-up evolutions use mid-to-late levels

### Key reference files
- Battle effects: `generated/battle_move_effects.txt`
- Move flags: `generated/move_flags.txt` (e.g., MOVE_FLAG_CAN_PROTECT, MOVE_FLAG_CAN_MIRROR_MOVE)
- Move ranges: `generated/move_ranges.txt` (e.g., RANGE_SINGLE_TARGET, RANGE_BOTH_OPPONENTS)
- Particle index: `res/battle/particles/battle_particles.order`
- Animation opcodes: `asm/macros/btlanimcmd.inc`
- Animation functions: `asm/macros/btlanimfunc.inc`
- Type icon palettes: `src/type_icon.c`, `src/overlay011/move_palettes.c`

### Build system notes
- `meson.build` auto-discovers new move directories from `moves.txt`
- `movedata.py` maps directory name to move enum (e.g., `moonblast/` → `MOVE_MOONBLAST`)
- `battle_anim_scripts.py` generates NARC ordering from `moves.txt`
- No manual meson.build changes needed for new named moves

## Adding a New Item (with Bag Icon and Overworld Pickup)

To add a new holdable/usable item with a bag icon and a ground pickup on a route, follow these steps:

### 1. Register the item constant
- **File:** `generated/items.txt`
- Add `ITEM_<NAME>` before the `MAX_ITEMS` line
- The enum value is the 0-indexed line position (ITEM_NONE=0, ITEM_MASTER_BALL=1, etc.)

### 2. Add item data
- **File:** `res/items/pl_item_data.csv`
- Add a row for the new item. Key columns:
  - `item`: `ITEM_<NAME>`
  - `price`: buy/sell price (0 for non-tradeable)
  - `holdEffect`: `HOLD_EFFECT_NONE` or a specific effect
  - `fieldPocket`: `POCKET_ITEMS`, `POCKET_BALLS`, `POCKET_KEY_ITEMS`, etc.
  - `battlePocket`: `BATTLE_POCKET_MASK_NONE` for most items
- Copy an existing similar item's row as a template

### 3. Add text entries (4 files)
All four text files must have entries at the same index position:
- **`res/text/item_names.json`** — `{"id": "pl_msg_00000392_NNNNN", "en_US": "Item Name"}`
- **`res/text/item_names_with_articles.json`** — `{"id": "pl_msg_00000393_NNNNN", "en_US": "a {COLOR 255}Item Name{COLOR 0}"}`
  - Use "an" for vowel-starting names. The `{COLOR 255}...{COLOR 0}` wrapper is required.
- **`res/text/item_names_plural.json`** — `{"id": "pl_msg_00000394_NNNNN", "en_US": "Item Names"}`
- **`res/text/item_descriptions.json`** — `{"id": "pl_msg_00000391_NNNNN", "en_US": ["Line 1\n", "Line 2"]}`
- NNNNN is the 0-indexed item number matching `generated/items.txt`
- **CRITICAL:** Missing entries in `item_names_with_articles.json` causes "picked up ???" text

### 4. Create bag icon (PNG + PAL)
- **Directory:** `res/graphics/item_icons/`
- **PNG format:** 32x32 pixels, 4-bit indexed color (16-color palette), non-interlaced
  - **MUST be 4-bit depth** — 8-bit causes corrupted sprites in-game
  - Content should be centered around pixel (12, 12) in the 32x32 canvas to match existing icons
  - Palette index 0 is the transparent/background color (use 180, 180, 180)
- **PAL format:** JASC-PAL file with CRLF line endings, 256 entries (only first 16 used, rest 0 0 0)
  ```
  JASC-PAL
  0100
  256
  180 180 180
  <15 more RGB colors>
  <240 lines of "0 0 0">
  ```
- **Add to build system:**
  - `res/graphics/item_icons/meson.build` — Add `'<name>.png'` to `item_icon_pngs` list (alphabetical) and `'<name>.pal'` to `item_icon_pals` list (alphabetical)
  - `res/graphics/item_icons/item_icon.order` — Add `<name>.NCGR` and `<name>.NCLR` before the `none.NCGR`/`none.NCLR` entries
- **Register in item.c:**
  - `src/item.c` — In `sItemArchiveIDs[]`, set `.iconID = <name>_NCGR` and `.paletteID = <name>_NCLR` for your item
  - Multiple items can share the same icon (e.g., all mega stones use `mega_stone_NCGR`/`mega_stone_NCLR`)

### 5. Add as ground pickup on a route

Ground items require changes to TWO files: the script file and the events file.

#### 5a. Script entry (field script file)
- **File:** `res/field/scripts/scripts_unk_XXXX.s` (each map zone has its own script file)
  - Route 206 uses `scripts_unk_0404.s`
- **Add a ScriptEntry** before `ScriptEntryEnd`:
  ```asm
  ScriptEntry _my_item_label
  ```
- **Add the script block** at the end of the file:
  ```asm
  _my_item_label:
      SetVar VAR_0x8008, ITEM_<NAME>
      SetVar VAR_0x8009, 1
      GoTo _1EAE
      End
  ```
  - `_1EAE` is the shared ground item pickup handler
  - `VAR_0x8009` is the quantity (usually 1)

#### 5b. Count your script index
- **ScriptEntry indices are 0-based.** Count from the first `ScriptEntry` line (index 0) to find your entry's index.
- The event script ID = `7000 + index`
- Example: if your `ScriptEntry` is the 329th line (index 328), the event script ID is `7328`
- **Common mistake:** off-by-one errors. Always count with: `grep -c "ScriptEntry " file.s` (subtract 1 for ScriptEntryEnd)

#### 5c. Event object (events JSON)
- **File:** `res/field/events/events_<route_name>.json`
  - Route 206 uses `events_route_206.json`
- Add an object entry to the `"obj_events"` array:
  ```json
  {
      "id": "ROUTE_NAME_POKEBALL_ITEMNAME",
      "graphics_id": "OBJ_EVENT_GFX_POKEBALL",
      "movement_type": "MOVEMENT_TYPE_NONE",
      "trainer_type": "TRAINER_TYPE_NONE",
      "hidden_flag": "FLAG_UNK_0xNNNN",
      "script": 7NNN,
      "initial_dir": 0,
      "data": [],
      "movement_range_x": 0,
      "movement_range_z": 0,
      "x": <grid_x>,
      "z": <grid_z>,
      "y": 0
  }
  ```
- **hidden_flag:** Must be a unique unused flag. Check existing flags in the events file to find unused ones. Existing Route 206 items use `FLAG_UNK_0x0414`–`FLAG_UNK_0x0542`.
- **script:** `7000 + ScriptEntry_index` (0-based, see step 5b)
- **x/z coordinates:** Use coordinates near existing pokeballs on the same route as reference for reachable positions

### Key reference files
- Item enum constants: `generated/items.txt`
- Item data CSV: `res/items/pl_item_data.csv`
- Item text banks: `00000392` (names), `00000393` (with articles), `00000394` (plurals), `00000391` (descriptions)
- Icon system: `res/graphics/item_icons/` (PNG, PAL, `meson.build`, `item_icon.order`)
- Icon→item mapping: `src/item.c` → `sItemArchiveIDs[]`
- Ground item scripts: `res/field/scripts/scripts_unk_XXXX.s` (handler at `_1EAE`)
- Ground item events: `res/field/events/events_<route>.json`
- Script macros: `asm/macros/scrcmd.inc` (ScriptEntry definition)
