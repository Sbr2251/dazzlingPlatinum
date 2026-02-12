# Dazzling Platinum ROM Hack

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
