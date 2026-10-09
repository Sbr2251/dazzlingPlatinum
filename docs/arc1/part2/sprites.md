# Arc 1 part 2 field sprites (placeholders, swap-ready)

The lead pre-work registered five object graphics IDs with placeholder art, so every stream can use
the constants from day 1. The Art stream replaces the five PNG sheets. Nothing else needs to change.

| constant | gfx ID | mmodel member | sheet (the ONLY file Art replaces) | layout | placeholder copied from |
|---|---|---|---|---|---|
| `OBJ_EVENT_GFX_SAROS` | 285 | 479 (0x1DF) | `res/field/objects/arc1/saros.png` | walker | `OBJ_EVENT_GFX_GENTLEMAN` (member 0x22) |
| `OBJ_EVENT_GFX_ECLIPSE_GRUNT_M` | 286 | 480 (0x1E0) | `res/field/objects/arc1/eclipse_grunt_m.png` | walker | `OBJ_EVENT_GFX_GRUNT_M` (member 0x67) |
| `OBJ_EVENT_GFX_ECLIPSE_GRUNT_F` | 287 | 481 (0x1E1) | `res/field/objects/arc1/eclipse_grunt_f.png` | walker | `OBJ_EVENT_GFX_GRUNT_F` (member 0x68) |
| `OBJ_EVENT_GFX_ARC1_RIFT` | 288 | 482 (0x1E2) | `res/field/objects/arc1/arc1_rift.png` | idle2 | `OBJ_EVENT_GFX_ROCK_SMASH`'s rock (member 0x53), centred in both frames |
| `OBJ_EVENT_GFX_TOTEM_HITMONLEE_VIOLET` | 289 | 483 (0x1E3) | `res/field/objects/arc1/totem_hitmonlee_violet.png` | idle2 | `OBJ_EVENT_GFX_TOTEM_HITMONLEE` (`res/field/objects/totems/hitmonlee_idle_{a,b}.png`) |

The walker placeholders build byte-identical to their stock members. The violet Hitmonlee differs only in
palette entry 0, which is transparent. All five render in game: a scratch build placed each on Twinleaf Town
next to the stock sprites, and the walkers walked and ran. The scratch build was not committed.

## How it is wired

The registration is append-only, following `docs/arc1/mawile_sprite.md` (Mawile is gfx 284, member 478).
`tools/integrate_arc1_field_sprites.py` (lead-owned) handles it:

- The five constants are appended to `generated/object_events_gfx.txt` after `OBJ_EVENT_GFX_MAWILE`.
- `src/overlay005/ov5_021FAF40.c` gets one row per constant in each of the four tables:
  - renderer, animation and draw rows: copied from the template constant (walkers from their stock
    sprite, idle2 from `OBJ_EVENT_GFX_TOTEM_HITMONLEE`);
  - member table: `0x1DF`-`0x1E3`.
- `res/prebuilt/data/mmodel/mmodel/meson.build` gets one `custom_target` per member, after Mawile's.
  - Each target runs `tools/integrate_arc1_field_sprites.py build-member` on the sheet and the stock
    template member: the walker's own member, or Uxie (member 130) for idle2, which is what every Totem
    clones.
  - No `.bin` is checked in, and changing a sheet rebuilds its member.
  - Members must stay contiguous after 478, because `narc create` packs the directory in name order.
- The tool is PIL-free, because the build runs it with the system Python. It reuses the PNG reader in
  `tools/integrate_mawile_overworld_sprite.py`.

Commands:
- `python3 tools/integrate_arc1_field_sprites.py check` validates every sheet. Run it before you build.
- `python3 tools/integrate_arc1_field_sprites.py extract-placeholder --constant OBJ_EVENT_GFX_SAROS`
  restores one placeholder. Leave out `--constant` to restore all five.
- `python3 tools/integrate_arc1_field_sprites.py` is the idempotent registration. It is already done.

## Sheet rules (both layouts)

- PNG, indexed colour (palette mode), bit depth 4 or 8, non-interlaced. Truecolour or RGBA is rejected.
- Use 16 colours at most: every pixel must be palette index 0-15. One palette covers the whole sheet.
- Index 0 is transparent. Its RGB value doesn't matter.
- Colours are reduced to BGR555 (`value >> 3` per channel), so colours that differ only in the low 3 bits
  look the same in game.
- The cells are 32x32. Draw the figure the way stock sprites sit in the cell: centred horizontally around
  x=15, with the lowest pixel (the feet) on row y=29. The placeholders' first cell covers x 7-23 and
  y 6-29. Anything outside the cell is lost.

### walker (`SAROS`, `ECLIPSE_GRUNT_M`, `ECLIPSE_GRUNT_F`)

- The sheet is 128x128: 4 rows by 4 columns.
  - Rows, in this order: up (back view), down (front view), left, right.
  - Columns: stand, step A, stand, step B.
- A 64x128 sheet (stand, step) also works. The tool expands it to stand, step, stand, step.
- The right row is required, because the engine doesn't mirror the left one.
- There are no run frames. `WalkFast*` movements play the walk frames faster, as for every stock NPC
  walker. Every `ApplyMovement` that stock NPCs support works, including the emotes.

### idle2 (`ARC1_RIFT`, `TOTEM_HITMONLEE_VIOLET`)

- The sheet is 64x32: frame A in x 0-31, then frame B in x 32-63.
- The engine loops A/B like the Totem idle, and the image is the same for every facing.
- These objects shouldn't walk. Use `MOVEMENT_TYPE_NONE` (Totem precedent) and move them with
  `SetObjectEventPos` or `AddObject`/`RemoveObject`.
- The rift placeholder is a grey rock, and the violet Hitmonlee placeholder looks exactly like the stock
  Totem.

## Rules for the streams

- Streams A-D use the constants in events JSON (`"graphics_id": "OBJ_EVENT_GFX_SAROS"`) or in script
  commands, and never touch the PNGs or any registration file.
- Art owns only the five PNGs, plus its own generator under `tools/arc1_sprites/` and a design sheet under
  `docs/story/art/`.
- Keep the number of distinct gfx visible on one screen low. Every distinct gfx loads its own texture: see
  the Jubilife budget in `spec.md` risk 6.
- Fallbacks, if a sheet ever breaks the build: replace the constant with the stock one it was copied
  from (table above). The registration is known good, so `extract-placeholder` is the faster fix.
