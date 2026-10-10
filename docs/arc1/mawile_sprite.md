# Mawile overworld sprite (`OBJ_EVENT_GFX_MAWILE`)

Arc 1 needs a walking Mawile on the overworld: it jumps out, runs in circles, turns
to face different directions and jumps at the player. HGSS has a Mawile follower
sprite, but Platinum does not. **The art is now the Black/White overworld Mawile** (Spriters Resource asset 34110,
"Old-Gen Overworld Pokemon", 2-column 64x128 sheet, 13 colours), injected on 2026-10-10. It replaced the
Skitty placeholder, which `extract-placeholder` can still regenerate.

## At a glance

| What | Value |
| --- | --- |
| Graphics constant | `OBJ_EVENT_GFX_MAWILE` (line 285 of `generated/object_events_gfx.txt`, so ID **284** / `0x11C`) |
| mmodel NARC member | **478** (`0x1DE`), file `mmodel_00000478.bin` in the build dir |
| Art source (the ONLY file to replace) | `res/field/objects/mawile/mawile_overworld.png` |
| Placeholder copied from | Skitty: `OBJ_EVENT_GFX_SKITTY` (ID 79), mmodel member 77 (`0x4D`, `res/prebuilt/data/mmodel/mmodel/mmodel_00000077.bin`) |
| Integration tool | `tools/integrate_mawile_overworld_sprite.py` |
| Overlay 5 table rows | `src/overlay005/ov5_021FAF40.c` (one row in each of four tables, see below) |

You use it like any other object graphic, for example `"graphics_id": "OBJ_EVENT_GFX_MAWILE"`
in an events JSON, or with the object-graphics script commands. It uses the same
renderer, animation and draw rows as Skitty, so every walker movement action works:
walking, facing each of the 4 directions, and jumping.

## How it is wired

The integration is append-only, like `tools/integrate_totem_overworld_sprites.py`:
no existing graphics ID or mmodel member number changes.

1. `generated/object_events_gfx.txt`: `OBJ_EVENT_GFX_MAWILE` is appended after
   `OBJ_EVENT_GFX_TOTEM_KINGDRA`.
2. `src/overlay005/ov5_021FAF40.c`: one row is added before the sentinel of each
   of these tables. Each row copies Skitty's row, except the member row.
   - `Unk_ov5_021FB97C` (renderer): `{ OBJ_EVENT_GFX_MAWILE, &Unk_ov5_021FAFD8 }`,
     the 4-direction walker renderer.
   - `Unk_ov5_021FC9B4` (graphics ID to mmodel member): `{ OBJ_EVENT_GFX_MAWILE, 0x1DE }`.
   - `Unk_ov5_021FD77C` (animation): `{ OBJ_EVENT_GFX_MAWILE, 0x0, 0x0, Unk_ov5_021FB2C0 }`.
     `Unk_ov5_021FB2C0` holds the four 16-frame direction ranges.
   - `Unk_ov5_021FC194` (draw): `{ OBJ_EVENT_GFX_MAWILE, 0x1, 0x1, 0x1, 0x1, 0x0 }`.
3. `res/prebuilt/data/mmodel/mmodel/meson.build`: a `custom_target` after the
   `fs.copyfile` loop creates `mmodel_00000478.bin` **at build time**. It runs
   `tools/integrate_mawile_overworld_sprite.py build-member` on the PNG and the
   Skitty member, and the output is packed into `mmodel.narc` with the other
   members. No `.bin` for Mawile is checked in. The target depends on both the
   PNG and the tool, so changing either one rebuilds the member.

To re-run the integration, use `python3 tools/integrate_mawile_overworld_sprite.py`
(the default subcommand is `integrate`). It is idempotent: steps already done are
skipped. It also checks that the PNG builds. If the PNG is missing, it regenerates
the Skitty placeholder first.

## Swapping in the HGSS Mawile sprite

1. Convert the HGSS art into the sheet format described below and save it over
   `res/field/objects/mawile/mawile_overworld.png`. Replace nothing else.
2. Optional: check it before building:
   `python3 tools/integrate_mawile_overworld_sprite.py`
   Any error (wrong size, too many colours, not indexed) is printed with the reason.
3. Build: `cd /data/repos/dazzlingPlatinum && make release`. Use
   `flock /tmp/dp-build.lock make release` if other builds may be running.

No C, meson or table change is needed, as long as the art fits the 32x32 cell
described below.

To go back to the placeholder, run
`python3 tools/integrate_mawile_overworld_sprite.py extract-placeholder`.

### Sheet format

- **PNG, indexed colour** (palette mode), bit depth 4 or 8, non-interlaced.
  Truecolour or RGBA PNGs are rejected: quantise to a palette first.
- **16 colours max.** Every pixel must use palette index 0-15. Entries 16 and
  above can exist in the file but must not be used.
- **Index 0 is transparent.** Its RGB value does not matter in game. The
  placeholder uses Skitty's background colour.
- **One palette for all frames.** The whole sheet shares one 16-colour palette.
- Colours are reduced to BGR555 (5 bits per channel, i.e. `value >> 3`), so
  colours that differ only in the low 3 bits will look the same in game.
- **Cells are 32x32**, laid out in rows by facing direction, **in this order**:

  | Row | y range | Facing |
  | --- | --- | --- |
  | 0 | 0-31 | up (back view, walking away from the camera) |
  | 1 | 32-63 | down (front view, walking toward the camera) |
  | 2 | 64-95 | left |
  | 3 | 96-127 | right |

- The columns can be laid out in one of two ways:
  - **4 columns, 128x128**: `stand, step A, stand, step B`. Used as-is. This
    matches the stock Platinum layout.
  - **2 columns, 64x128**: `stand, step`, the usual HGSS follower layout. The tool
    expands each row to `stand, step, stand, step`, so the same step frame is
    used for both feet.
- **The right-facing row is required.** The engine does not mirror left frames.
  If the HGSS sheet only has left-facing frames, flip them horizontally to make
  the right row.
- Put the sprite in the cell the way stock sprites are placed: centred
  horizontally (around x=15), with the lowest pixel on row y=29 of the cell,
  as Skitty's are. Look at the placeholder PNG for reference. Anything outside
  the cell is lost.
- There are no jump frames. The jump movement actions in the story scene use the
  walker's normal frames, with the engine moving the sprite through the hop, the
  same way as for Skitty.

### Mapping to the texture (for reference)

The member is a BTX0 cloned from Skitty's: 16 textures `eneco.1` to `eneco.16`,
each 32x32 `4bpp` (format 3, colour 0 transparent), plus one 16-colour palette
`eneco`. The tool keeps Skitty's names and replaces only the texel data and the
palette, which is how the placeholder is proven to work in game. The tool
writes, frame by frame:

| Textures | Facing | Sheet row |
| --- | --- | --- |
| `eneco.1`-`eneco.4` | up | 0 |
| `eneco.5`-`eneco.8` | down | 1 |
| `eneco.9`-`eneco.12` | left | 2 |
| `eneco.13`-`eneco.16` | right | 3 |

Within a direction, the order is stand, step A, stand, step B.

### Larger art

A 32x32 cell fits Mawile, which is a small Pokemon, just as it fits Platinum's
own small walkers such as Skitty. If the HGSS art really needs a
bigger cell, for example 64x64, this template does not work. You would need to
clone a different stock member with the larger layout and change the tool's
`TEMPLATE_*` constants, `CELL`, and the `Unk_ov5_021FB97C`, `Unk_ov5_021FD77C`
and `Unk_ov5_021FC194` rows to match that template.
