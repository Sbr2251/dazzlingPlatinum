# Mt. Coronet 1F South - Lava Theme Plan

Status: plan approved; no more mock rounds. Implement in the order below, building and testing on the devserver at each checkpoint.
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
| `coronet_1f_south_lava_mock_v2.png` | Layout mock: rock recolour and causeway placement are final. Its lava tile is **superseded** by the spec in Step 1 |

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

### Step 1 - Lava art spec (final, no approval round)

The v2 mock's lava was too bright and mosaic-like. The spec below is taken from `LavaArtDirection.jpeg`.

**Brightness:** that screenshot is uniformly darkened (even its brightest lava is only about R 135). The colours below are its hues scaled back up to normal DS brightness.

#### Lava palette (`dun_sea`, 16 colours, BGR555)

| Idx | RGB | Role |
|---|---|---|
| 0 | (160, 40, 22) | darkest crust / veins |
| 1 | (91, 40, 51) | dark crimson cooling spots (sparse) |
| 2-5 | (210,36,14) (228,40,15) (240,42,15) (243,56,16) | red-orange base, 4 steps (cycled, see Step 4) |
| 6-9 | (243,74,17) (245,94,18) (243,114,17) (248,134,20) | orange speckle bodies (cycled) |
| 10-13 | (250,154,21) (252,176,40) (255,196,64) (255,214,90) | yellow-orange speckle cores (cycled) |
| 14 | (255,236,150) | hot fleck highlight |
| 15 | (255,250,210) | bubble pop, used by 1-2 texels per frame only |

#### Tile (`dun_sea`)

- 16x16, 4bpp, tileable in both axes.
- Base fill: indices 2-5 in soft diagonal bands.
- Speckle clusters: 2-4 px blobs of 6-9 with 10-13 cores, laid out in loose horizontal rows about 4 px apart, with the rows offset from each other like the reference.
- 3-4 single-texel crimson (1) spots, and one vein line of index 0.
- The band layout matters: palette cycling (Step 4) animates by rotating indices, so neighbouring texels in a band must use consecutive indices.

#### Rock

- `CLIFF` ramp (walls, level, steps, jump, holes): (20,18,32) (39,35,60) (52,47,78) (66,60,96) (82,76,115). This is the reference's blue-slate rock scaled x1.5; darker than stock, keeps the purple cast.
- `FLOOR` ramp (`dun_floor*`): (42,32,40) (56,44,54) (66,52,64) (78,62,74) (92,74,86), the reference's mauve-brown ground.
- `dun_sside` (the shore edge against lava): (60,16,14) → (150,30,10) → (230,90,20), so shores read red-hot.

#### Tool

Write `tools/coronet_lava/make_lava.py`:
- Emit the tile as an indexed PNG plus the palette as JASC-PAL.
- Emit the texel-frame set for Step 4 (8 frames).
- Emit a preview GIF, for reference only. The implementer can check it against the reference, but no sign-off is needed.

### Step 2 - New texture set 074 (lava recolour of 068)

1. Copy `map_texture_set_068.nsbtx` to `map_texture_set_074.nsbtx` and add it to `res/field/maps/texture_sets/meson.build`.
2. Write a small patcher, `tools/coronet_lava/make_texset.py`:
   - **Palette-only recolour** for rock and floor textures: rewrite the palette entries in place. Map luminance onto the `CLIFF` ramp for walls/cliffs and the `FLOOR` ramp for floors. The texel data is unchanged, so there is no re-encoding.
     - Walls/cliffs: `dun_wall_*`, `dun_level`, `dun_step`, `dun_jump`, `dun_dhole*`, `dun_down`, `dun_ent*`
     - Floors: `dun_floor*`
   - **`dun_sea`**: replace texels and palette with the Step 1 lava tile. Keep format 3 (4bpp, 16 colours) and 16x16, so the dictionary offsets don't move.
   - `dun_sside` (shore edge): the red-hot ramp from Step 1.
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

The field engine has no terrain texture animation, so this adds a small `lava_anim` module. It's layered so each tier can ship on its own.

#### Tier 1 - core flow (must ship)

**a) Texel flow frames.**
- 8 pre-baked 16x16 frames: the speckle layer drifts +1 px right per frame and bobs 1 px vertically on a 4-frame sine. Clusters therefore creep sideways the way the reference's rows read.
- Because the tile is tileable, frame 8 wraps back to frame 1 seamlessly.
- Swap frames every 6 VBlanks, which is 10 fps and the usual DS "liquid" rate.
- Cost: 128 bytes of texel upload per swap, trivial during VBlank.
- Upload into the `dun_sea` texel slot with `GX_BeginLoadTex` / `GX_LoadTex` / `GX_EndLoadTex`. Find the VRAM address from the loaded texture's dictionary entry for `dun_sea` (`NNS_G3dGetTex` → `NNSG3dResDictTexData`, TexKey from the resource after `NNS_G3dTexLoad`).

**b) Palette shimmer.**
- Independently of the frames, rotate each cycling band by one step on its own period:
  - base 2-5: every 10 frames
  - bodies 6-9: every 7 frames
  - cores 10-13: every 5 frames
- The periods are coprime, so the combined pattern only repeats after 350 frames (~6 s), and the lava never looks like a short loop.
- Cost: a 32-byte palette upload with `GX_BeginLoadTexPltt` / `GX_LoadTexPltt` / `GX_EndLoadTexPltt`.

**c) Heat pulse.**
- Scale indices 10-15 toward white on a slow 2 s sine (±12% brightness).
- Pulse `dun_sside`'s top colour in sync, so the shores breathe with the lava.

**Hooking it in:**
- Create the task when the area data manager loads area 0x4B; tear it down with the manager. Look at `src/overlay005/fieldmap.c` and the callers of `AreaDataManager_Alloc` / `_Free`.
- Run the uploads from the field VBlank callback, not the main loop, to avoid tearing.
- Guard every upload with the area-ID check, so a stale task can never write into another map's texture VRAM.

**Reduce visible tiling:**
- Dump the NSBMD UVs over the pools (see Step 6).
- If a pool's UVs run continuously across tiles (for example 0..160 over 10 tiles), widen `dun_sea` to 32x32 with 4 distinct speckle quadrants. Frame cost becomes 512 bytes, still fine.
- If UVs restart every tile, stay at 16x16.

#### Tier 2 - polish (do if Tier 1 is solid)

**d) Warm light flicker.**
- Every frame, nudge the area light's diffuse colour by ±1-2 in R/G using layered sines (0.7 s and 1.9 s).
- Result: faint firelight on the walls and the player.
- Do this through the area light manager (`src/overlay005/area_light.c`) so it composes with the base light rather than fighting it.

**e) Bubble pops.**
- Every 40-90 frames (random), draw one texel in a random clustered spot of the current frame to index 15 for 3 frames. This reuses the texel upload.

#### Tier 3 - pushing the DS (stretch, behind `#define LAVA_HEAT_HAZE` / `LAVA_EMBERS`)

**f) Heat haze.**
- Per-scanline horizontal offset of the 3D layer (BG0) via HBlank DMA: a 1 px sine wave that scrolls up the screen at 1 line per frame.
- The DS supports this cheaply, and it gives a real heat-shimmer look.
- Constraints: turn it off during menus and transitions and on map exit. First check that the field doesn't already use HBlank DMA or BG0 offset for something else (weather effects).
- Keep the amplitude at 1 px so sprites and text stay readable.

**g) Embers.**
- 6-10 tiny additive-orange sprites that rise slowly from random lava tiles and fade out over about 1 s.
- Use the existing field sprite/particle path for overworld effects in `src/overlay005` (the same system that draws weather or surf effects).
- Cap the count so the OAM and CPU budget stays safe next to NPCs.

### Step 5 - Warmer lighting

The cool cave light (light 2) would mute the lava. Do this together with Step 3.

1. Duplicate light 2 in `res/prebuilt/data/arealight.narc` as a new entry.
2. Warm it:
   - diffuse about +15% R, -10% B
   - ambient toward (10,6,6) in 5-bit units
   - keep the direction
3. Point area data 0x4B at it.
4. If Tier 2d lands, it flickers around this base.

### Step 6 - Keep the Surf-only spots reachable: basalt causeways (decided)

Two pools currently require Surf (see the table above). Lava is not surfable, so add cooled-basalt causeways as in the mock:
- north pool: row 6, cols 7-16 (bottom row)
- south lake: row 29, cols 16-25 (bottom row)

1. **Perms:** on those tiles in `map_data_351.bin`, clear bit 15 and set behaviour 0x08 (CAVE_FLOOR).
2. **Mesh check first:** dump the NSBMD polygons and UVs that cover the pool areas.
   - **Per-tile quads:** reassign the causeway quads from the `dun_sea` material to a floor material (`dun_floor2`), and raise their Y to floor height if the lava plane is lower.
   - **One big quad:** split it at the causeway row, which is a small model edit in the NSBMD display list.
3. **BDHC:** make sure the causeway tiles' height plates match the floor so the player doesn't sink or float.
4. **Fallback if mesh editing stalls:** keep the south lake as lava and move the Poke Ball at (28,28) (script 7047) to (28,26) on dry ground. Make only the north causeway, since that crossing is progression-critical.
5. **Test:** Route 207 entrance → north causeway → ledge area → Rock Climb → 2F stairs, and reach the Poke Ball.

### Step 7 - Fire-type encounters (separate commit, easy to revert)

1. Change `encounters_mt_coronet_1f_south`. Keep the level range and swap about half the slots to Slugma, Numel, Houndour and Magby. Put Torkoal in a rarer slot.
2. Leave `battleBG` as `BACKGROUND_CAVE_2`.

## Implementation notes (deviations from the steps above)

- **Flow frames: 16, not 8.** A +1 px/frame drift over a 16 px tile only wraps after 16 frames. Same speed and per-swap cost (128 bytes); 2 KB total. `make_lava.py` writes them to `lava_frames.bin`.
- **dun_sea palette is appended, not rewritten in place.** Set 068's `dun_sea` palette slot holds only 8 colours. `make_texset.py` appends the 16-colour lava palette at the end of TEX0 (offset 0x520 in the palette block) and repoints `dun_sea`'s palette dictionary entry at it. Step 4b/4c uploads must target that slot.
- **Recolour stats use only the palette indices the texels reference** (stock palettes pad unused slots with white). Holes, entrances and the lit `*2` wall variants fade back to their stock colour above luminance 150, so exits still glow.
- **Warm light is area light 4** (`add_area_light.py`), with `AREA_LIGHT_FILE_COUNT` raised to 5. Beyond Step 5's diffuse/ambient change, emission (8,8,11 → 9,7,7) and key light 0 (7,7,12 → 10,7,8) were also warmed, since those were the main blue sources.

## Commit order

Each commit should build on its own:
1. Lava tile, palettes and texture set 074, plus the new area data 0x4B and the header switch (static lava).
2. Warm light entry.
3. Tier 1 animation.
4. Causeways (perms, mesh, BDHC).
5. Tier 2.
6. Tier 3.
7. Encounters.

## Build and test

- Build on the devserver with `make release` (see CLAUDE.md, Build & Test Workflow), then commit and push.
- Test checklist:
  - 1F South shows the lava theme.
  - 2F, 3F, B1F, North Rooms and the Iceberg Ruins look unchanged.
  - Route 207 → 1F South → 2F is still possible.
  - The Poke Ball at (28,28) is still reachable.
  - No texture corruption on other maps after entering and leaving 1F South several times (animation teardown, area-ID guard).
  - Animation holds 60 fps with NPCs on screen (watch the heat-haze and ember tiers).
