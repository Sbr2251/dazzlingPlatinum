# Mt. Coronet 1F South - Lava Theme Plan

Status: mock approved in direction, **lava tile must be re-matched to the reference before implementing** (see Step 1).
Branch: `feat/coronet-4f-lava` (name predates the retarget; the work is 1F South, not 4F).

## Goal

Turn Mt. Coronet 1F South (the floor joining Route 207, Route 208 and the stairs up to 2F, `[A]`) into a magma cavern:

- Near-black slate cliffs, dark brown basalt floor
- All four water pools become animated lava in the style of `LavaArtDirection.jpeg`
- Every other Mt. Coronet floor keeps the normal cave look

Files in this folder:

| File | What it is |
|---|---|
| `mtcoronetsouth.png` | Current map (source screenshot) |
| `LavaArtDirection.jpeg` | Art direction reference for the lava and rock |
| `coronet_1f_south_lava_mock_v2.png` | Current mock (recolour of the screenshot) |

Regenerate the mock: `python3 tools/coronet_lava/make_mock.py` (Pillow; output in `$OUT_DIR`, default `/tmp/coronet_lava`).

## Key facts (verified in this repo)

- **Map header:** `include/data/map_headers.h`, `[MAP_HEADER_MT_CORONET_1F_SOUTH]`
  - `.areaDataArchiveID = 0x45`
  - `.mapMatrixID = 9` → `MAP_351`, i.e. `res/field/maps/data/map_data_351.bin`
- **Area data:** `res/prebuilt/fielddata/areadata/area_data.narc` is a prebuilt NARC with 75 files (IDs 0x00-0x4A).
  - Each file is 8 bytes: `u16 mapPropArchive, u16 textureSetID, u16 unk, u16 areaLightArchiveID`.
  - Entry 0x45 is `41 00 44 00 00 00 02 00`: props 0x41, texture set 0x44 (= 68), light 2.
  - 0x45 is shared by 1F South, 2F, 3F, 1F Tunnel Room, 1F North Rooms 1+2, B1F and the Iceberg Ruins. **Do not edit 0x45**; add a new entry.
- **Texture sets:** `res/field/maps/texture_sets/map_texture_set_000..073.nsbtx`, listed in that folder's `meson.build`.
  - The next free ID is **074**.
  - Set 068 textures: `dun_floor*`, `dun_wall_{n,s,e,w,c}{,2}`, `dun_sea` (16x16), `dun_sside`, `dun_slope`, `dun_hanger`, `dun_jump`, `dun_step`, `dun_level`, `dun_srock`, `dun_imped`, `dun_ent*`, `dun_dhole*`, ...
  - Most are 16-colour paletted, format 3. `dun_light` is format 6.
- **Map data file** (`map_data_NNN.bin`):
  - Header: 4 x u32 sizes (perms 0x800, props, NSBMD, BDHC).
  - Perms: 32x32 u16. Low byte = tile behaviour; bit 15 = collision.
  - The NSBMD materials reference textures **by name**, so a copied texture set with the same names swaps in cleanly.
- **Lighting:** `areaLightArchiveID` indexes `res/prebuilt/data/arealight.narc` (`src/overlay005/area_light.c`). Light 2 is a cool cave light.
- **Animation:** there is **no terrain texture animation** in the field engine. Only map props animate (`src/overlay005/map_prop_animation.c`). Animated lava needs new code (Step 4).
- **1F South pools** (map 351 tile coords):

  | Pool | Tiles | Notes |
  |---|---|---|
  | North | rows 4-6, cols 7-16 | **Required Surf crossing**: the only way from the 207 side to the ledge area, Rock Climb (27,8-9) and the 2F stairs (25,3) |
  | West | cols 7-9, rows 15-22 | Not required |
  | East | cols 22-26, rows 14-22 | Not required |
  | South | rows 26-29, cols 16-25 | **Required Surf crossing** to reach the Poke Ball at (28,28) (script 7047) |

  - Other features: ledges JUMP_SOUTH at (22..27, 11); warps to Route 207 at (3,8)/(4,8), Route 208 at (27,20)/(28,20), 2F at (25,3).

## Tools

- `tools/coronet_lava/btx.py`: NSBTX reader.
  - `load(path)` returns `(tex, info, texs, pals)`.
  - `decode(tex, info, t, palOff)` returns RGBA rows. It handles formats 1-7.
  - Use it to dump set 068 and to verify the written set 074.
- `tools/coronet_lava/make_mock.py`: mock generator. Its `CLIFF`/`FLOOR` ramps and `lava_tile()` are the starting palettes.

## Steps

### Step 1 - Re-match the lava tile to the reference (mock update, needs user sign-off)

The v2 mock lava is too bright and blobby compared with `LavaArtDirection.jpeg`:

| | Reference | v2 mock |
|---|---|---|
| Base colour | deep red-orange | bright orange-yellow |
| Pattern | small yellow-orange speckle clusters in loose horizontal rows, a few dark crimson spots | large yellow cells with red outlines (mosaic look) |

1. Sample the lava colours from the reference (crop around x 470-580, y 20-130 and the brighter strip at the lower right).
2. Build a 16-colour palette from those samples.
3. Rewrite `lava_tile()` as a tileable 16x16 (the size of `dun_sea`) speckle pattern with those colours.
4. Re-render the mock with a side-by-side swatch (reference crop vs tile at 4x) and get approval.
5. Also make 3-4 animation frames, or a palette-cycle order (see Step 4), and preview them as a GIF.

### Step 2 - New texture set 074 (lava recolour of 068)

1. Copy `map_texture_set_068.nsbtx` to `map_texture_set_074.nsbtx` and add it to `res/field/maps/texture_sets/meson.build`.
2. Write a small patcher, `tools/coronet_lava/make_texset.py`:
   - **Palette-only recolour** for rock and floor textures: rewrite the palette entries in place. Map luminance onto the `CLIFF` ramp for walls/cliffs and the `FLOOR` ramp for floors. The texel data is unchanged, so there is no re-encoding.
     - Walls/cliffs: `dun_wall_*`, `dun_level`, `dun_step`, `dun_jump`, `dun_dhole*`, `dun_down`, `dun_ent*`
     - Floors: `dun_floor*`
   - **`dun_sea`**: replace texels and palette with the Step 1 lava tile, keeping the same format, size and palette slot size.
   - `dun_sside` (shore edge): a red-hot rim colour.
   - `dun_hanger`: orange-glowing holds.
   - `dun_srock` / `dun_imped`: obsidian tones.
   - Palettes are BGR555. Convert with `(r>>3) | (g>>3)<<5 | (b>>3)<<10`.
3. Verify by decoding 074 with `btx.py` and making a contact sheet.

### Step 3 - New area data entry and header switch

1. Rebuild `area_data.narc` with a 76th file (ID **0x4B**) = `41 00 4A 00 00 00 LL 00`:
   - Texture set 0x4A (= 74).
   - `LL` = light ID, 2 for now (see Step 5).
   - Write `tools/coronet_lava/add_area_data.py`. The NARC is BTAF (offset table) + BTNF + GMIF. Append the 8-byte file, add a BTAF entry and fix the section and file sizes.
2. In `map_headers.h`, set `[MAP_HEADER_MT_CORONET_1F_SOUTH].areaDataArchiveID = 0x4B`.
3. Check that nothing asserts on the area data count. Grep for area-data/texture-set NARC member limits in `src/overlay005/area_data.c` and `land_data.c`.
4. **Build and test checkpoint:** the recolour plus static lava should now show in-game on 1F South only. Walk to 2F and check that it still looks normal.

### Step 4 - Animate the lava (new engine code)

The field engine has no terrain texture animation, so use **palette cycling** (cheapest, and it looks like flowing lava):

1. After the area texture is loaded, find the `dun_sea` palette's VRAM address in the loaded `mapTexture` (`AreaDataManager_GetMapTexture`), e.g. with `NNS_G3dPlttGetRequiredSize` / the TexPltt key via the `NNSG3dResDictPlttData` of `dun_sea`.
2. Register a VBlank task, active only when the current area data ID is 0x4B, that rotates palette entries 1..N of `dun_sea` every few frames. Upload with `GX_BeginLoadTexPltt` / `GX_LoadTexPltt` / `GX_EndLoadTexPltt`.
3. Hook creation/teardown where the area data manager is created and freed (`src/overlay005/fieldmap.c`, `AreaDataManager_Alloc` / `_Free` callers).
4. Alternative if cycling looks bad: frame swapping (upload new `dun_sea` texels from a small table of frames). This costs more VRAM writes but uses the same hook.

### Step 5 - Warmer lighting (optional, after seeing Step 3 in-game)

The cool cave light may mute the lava.

1. Duplicate light 2 in `res/prebuilt/data/arealight.narc` as a new entry with warmer ambient/diffuse colours.
2. Point area data 0x4B at the new entry.
3. Decide in-game against the reference.

### Step 6 - Keep the Surf-only spots reachable (needs a user decision)

Two pools currently require Surf (see the table above). Options:

- **A. Basalt causeways (as mocked).**
  - Perms: set collision off and behaviour 0x08 (CAVE_FLOOR) on the causeway tiles:
    - north pool row 6, cols 7-16
    - south lake row 29, cols 16-25
  - Retexture those tiles as floor, which needs the NSBMD mesh to have separate quads there. First dump `map_data_351.bin`'s NSBMD polygons over the pool area.
  - If the pool is one big quad, split it (a model edit), or place a flat "crust" map prop on top (new prop model plus prop entries in the map data's props block).
  - Update BDHC heights if the lava plane is lower than the floor.
- **B. Keep Surf on the lava** (behaviour stays WATER_SEA). Zero geometry work, but lore-odd.
- **C. Move the items instead.** Move the Poke Ball (28,28) out of the south area and accept the north crossing via B. Partial fix.

Recommendation: A. Start by checking the mesh; if the quads are per-tile, it's cheap.

### Step 7 - Optional extras (ask the user)

- Fire-type encounters in `encounters_mt_coronet_1f_south`: Slugma, Numel, Magmar, Houndour, Torkoal.
- `battleBG` stays `BACKGROUND_CAVE_2` unless a volcanic battle background is wanted.

## Build and test

- Do **not** build on the Mac. Commit and push; build on the devserver with `make release`.
- Test checklist:
  - 1F South shows the lava theme.
  - 2F, 3F, B1F, North Rooms and the Iceberg Ruins look unchanged.
  - Route 207 → 1F South → 2F is still possible.
  - The Poke Ball at (28,28) is still reachable.
  - No texture corruption after entering and leaving the map several times (palette cycling teardown).
