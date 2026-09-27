# Lake Verity redesign: pipeline

Measurements of the stock map, and how the Nitro files for the redesign are generated. All tools are project-owned,
standard-library Python in `tools/lake_verity/`. The exception is `blender_preview.py`, which runs inside Blender.
Nothing here needs the ROM toolchain.

## 1. What the map is made of

Lake Verity is map matrix 102 (`m_dun2702_`), a 3x2 grid of chunks:

```
537 538 539
540 541 542
```

539 and 542 are forest filler. The lake and the island sit on the corner where 537, 538, 540 and 541 meet
(tile 32,32). No other matrix uses these chunks.

Each `res/field/maps/data/map_data_NNN.bin` is four u32 sizes followed by four sections:

1. permissions: 0x800 bytes
2. props
3. NSBMD terrain model
4. BDHC height data

The repo stores the sections uncompressed. The build LZ10-compresses the model.

| chunk | props | NSBMD | BDHC | polys (tri/quad) | verts sent | materials | notes |
|---|---|---|---|---|---|---|---|
| 537 | 0x30 | 31004 | 0x256 | 718 | 2292 | 9 | forest + NW shore |
| 538 | 0x30 | 31872 | 0x224 | 737 | 2374 | 10 | forest + NE shore |
| 540 | 0x30 | 39384 | 0x312 | 888 | 2986 | 14 | forest + SW shore, grass |
| 541 | 0x30 | 43704 | 0x2fa | 977 (170/807) | 3314 | 19 | SE shore, hut island, exit |

- `python3 tools/lake_verity/nsbmd.py info <map_data or nsbmd>` prints the full model breakdown.
- `python3 tools/lake_verity/mapdata.py info <map_data>` prints the sections, props and BDHC plates.

### Terrain model (NSBMD)

- Each chunk has one model (`m_dun2702_01_01c` in 541) with one node ("polySurface1") and one shape per material.
- Each model has an empty TEX0. Textures come from the area's texture set.
- posScale is 64 (`pos_scale` 0x40000). A vertex is fx16 / 4096 * 64 world units.
- The origin is the chunk centre. Chunk-local world x = (tile x - 16) * 16.
- Shapes carry normals and texcoords only (shape flag 0x5). There are no vertex colours.
- The GX display lists use every vertex format. The encoder chooses the shortest one, the same way stock does:
  - VTX_XY / XZ / YZ when one coordinate repeats;
  - VTX_10 when all coordinates are multiples of 64;
  - otherwise VTX_16.

  Strips: 23 (quad strip) and 24/25 in the command histogram.

Stock materials, all of them:

| field | value | meaning |
|---|---|---|
| poly_attr | 0x001f8081 | light 0 on, back faces culled, fog, alpha 31, polygon ID 0 |
| diff_amb | 0x7fffe739 | |
| spec_emi | 0 | |
| flag | 0x1fce | |
| tex_image_param | 0x30000 (fenter: 0) | only the repeat bits; size and format are filled in when bound |

**Lighting (this differs from PLAN.md).**
- The map materials are lit.
- `land_data.c` calls `AreaLight_UseGlobalModelAttributes`, so every map model takes the area light's global
  diffuse, ambient, specular and emission colours, and follows the time-of-day light.
- On the DS, a NORMAL command recomputes the vertex colour from the lights and overrides any COLOR command.
- So baked vertex colours only show on materials with lighting off (`lights=0`), in shapes without normals.
- Those materials do not change with time of day. That is the price of baked AO.
- A mixed approach works: bake onto the castle and props and leave the grass lit. The writer supports both, per
  material.

### Props (map props = build models)

- Every chunk has exactly one prop: build_model **311 `l_lake`**.
  - It is the lake surface: 16 quads, 40 vertices, posScale 64, its own 1184-byte TEX0 (`l_lake` 32x32 a5i3, so the translucency comes from texel alpha).
  - Placed at (0, 16, 0) world, relative to each chunk centre. Its vertices are at y -8, so **the water surface is
    at world y 8**, half a tile below the shore.
- The area's preload list (area_build 58) is [311, 72 `bomb_mark`, 74 `l_lake_l4`].
- **The water animation comes from the prop, not from fldtanime.**
  - `bm_anime_list` members 311 and 74 both point at `bm_anime` 19, a BTA0 texture-SRT animation (UV scroll).
  - None of the chunk textures are in `fldtanime.narc` member 0.
- **To keep animated water, keep the `l_lake` prop in all four chunks.** Island geometry sits on top of it (the
  island top is at world y 16 or higher).

fldtanime is the other mechanism, used by texture-name match:
- member 0 = {char name[16]; u8 frames[18][2]} entries;
- member index+1 is an NSBTX of frames, copied over the texture's texels;
- stock names include `asasea`, `hamabe`, `lakep.1`, `searock`, `dun_sea`;
- `tools/coronet_lava/add_lava_anim.py` shows how to append an entry.

It can animate new textures, such as a portal swirl or torch flames, by giving them a new name and adding an entry.

### The hut / Verity Cavern entrance

- The hut is chunk 541 terrain geometry (materials `dhole_lm1`, `fenter_lm6`, `criffp*`), not a prop.
- Its island is tiles x 29..35, z 32..34, plus the hill.
- The graybox removes it by dropping those faces.

### Texture set

- Area 62 = (props list 58, texture set 61, light 0).
- **Area 62 is shared.** Map headers SENDOFF_SPRING, LAKE_VERITY_LOW_WATER, LAKE_VERITY, LAKE_VALOR_DRAINED and
  LAKE_VALOR all use it.
- Consequences:
  - Textures may be **appended** to set 61. Stock textures must not be removed or renamed, or the other lakes
    break.
  - Alternatively, give Lake Verity its own area (section 6).

Set 61 (`res/field/maps/texture_sets/map_texture_set_061.nsbtx`):
- 62 textures (49 pltt16, 3 pltt4, 9 a3i5, 1 a5i3); the 4 lake chunks use 19 of them.
- 43008 bytes texel data + 1312 bytes palettes = 44320 bytes of VRAM.
- The field uploads the whole set.

Map texture sets across the game, for scale:

| set | VRAM |
|---|---|
| largest: 048 | 76416 |
| 072 | 62992 |
| 009 | 53520 |
| smallest: 050 | 384 |

The map set shares GX_VRAM_TEX_01_AB (256 KB) with the prop textures and the overworld sprites, so **76 KB
(set 048) is the largest proven-safe size**. The redesign may grow set 61 by about 30 KB without going past
stock precedent.

- Decoded set 61: `~/Documents/Lake Verity Update/pipeline_checks/texset61/` (PNG + JSON per texture).
- Contact sheet: `texset61_sheet.png`.

### Units, heights, collision

- 1 tile = 16 world units = FX32_CONST(16). A chunk is 32 x 32 tiles = 512 x 512 world units.
- BDHC:
  - Coordinates are chunk-centred (-256..256). A tile centre is lx * 16 + 8 - 256.
  - Stock values: shore, ground and forest at world y **16**; water (surf) at **8**; lakebed decoration down to
    -48.
  - Edge plates overhang to x = +-272 at y 0.
  - The lookup is `-(nx*x + nz*z + d) / ny`, using FX_Mul rounding and FX_Div. It returns the candidate closest
    to the object's current height, with up to 10 candidates. `mapdata.height_at` is a port of it.
- **Layout and mesh.json heights:**
  - `h` = (world y - 16) / 16, so shore = 0, stock water = -0.5, and a 4-tile wall top is at world y 80.
  - layout.py used to put water at h 0. That was a bug: stock water is at -0.5. It is fixed now (`WATER_H`).
    With the fix, every tile outside the island matches the stock BDHC height at its tile centre (3730 of 3730
    tiles).
- Permissions: 32 x 32 u16, [z][x], as in layout.py. Low byte is the behaviour; 0x8000 is blocked.

### DS limits

| limit | value |
|---|---|
| geometry engine, per frame, whole scene | 2048 polygons, 6144 vertices |
| map model heap buffer (`land_data.c`), per chunk, uncompressed | 0xF000 = 61440 bytes |
| BDHC buffer (`BDHC_BUFFER_SIZE`), per chunk | 0x9000 bytes |
| BDHC height candidates per lookup | 10 |

- The field shows up to 4 chunks at once.
- The limits count polygons after clipping: off-screen polygons are rejected by the geometry engine and don't use
  polygon RAM, but they still cost geometry time.
- The stock worst case on screen is roughly 541 + 540 = 1865 polygons if both were fully visible. In practice the
  camera only sees about 15 x 11 tiles, so most of that is clipped.
- Budget: **a chunk should stay at or below about 1000 polygons and 45 KB of model** (stock 541 is 977 and
  43704).
- Anything in the camera view at the same time as the castle counts toward the 2048 limit. Castle, 541 and 540
  terrain are all in view together.

### Field camera

CAMERA_TYPE_ZOOMED_IN (field_camera.c):

| parameter | value |
|---|---|
| distance | 515.456 world units = 32.2 tiles |
| pitch | -54.657 degrees |
| perspective FOV parameter | 10.459 degrees (half-angle; about 20.9 degrees vertical) |
| screen | 256 x 192 |

It shows about 15 x 11 tiles around the player. `blender_preview.py --views game` uses this camera.

## 2. Tools

| file | what it does |
|---|---|
| `nsbmd.py` | NSBMD (BMD0/MDL0) reader and writer. It decodes and encodes GX display lists (stock lists re-encode byte-identically), SBC, materials and dictionaries. `make_model` / `make_material` / `make_poly_attr` build models from primitives; `faces_to_prims` chains quads into quad strips; `model_to_mesh` exports to mesh.json. CLI: `info`, `dump`. |
| `nsbtx.py` | TEX0 / NSBTX reader and writer: pltt4, pltt16, pltt256, a3i5, a5i3, direct, and 4x4 (simple encoder), with VRAM accounting. CLI: `info`, `decode`, `build`. |
| `mapdata.py` | map_data packer; permissions, props and BDHC readers and writers; BDHC builder from plates; the height lookup port. |
| `png.py` | PNG reader and writer, no PIL. |
| `dump_stock.py` | Dumps chunks 537/538/540/541, their props and all their textures to mesh.json + PNG. |
| `blender_preview.py` | Blender 5 script: loads mesh.json files and textures, renders a top-down orthographic view and the in-game camera view. |
| `compare_layout.py` | Draws [layout colours / render / render tinted where the layout differs from stock] side by side. |

Stock dumps and renders are in `~/Documents/Lake Verity Update/pipeline_checks/`:

| file | contents |
|---|---|
| `stock/chunk_NNN.mesh.json` | terrain (`positions` absolute, `positions_local` chunk tiles) |
| `stock/chunk_NNN_props.mesh.json` | the l_lake prop, placed |
| `stock/textures/` | textures |
| `stock_top.png` | top-down, x 4..63, z 10..59 (the `layout.py --ascii` window), 8 px per tile |
| `stock_game.png` | in-game camera over the stock hut |
| `stock_vs_stockgrid.png` | render vs the stock collision grid: tiles line up exactly, confirming the axes and origin |
| `stock_vs_layout.png` | render vs the redesigned layout |

Re-run:

```
python3 tools/lake_verity/dump_stock.py
S=~/Documents/Lake\ Verity\ Update/pipeline_checks/stock
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P tools/lake_verity/blender_preview.py -- \
    --tex "$S/textures" --target 32,33 --out "$S/../stock" "$S"/chunk_5*.mesh.json
python3 tools/lake_verity/compare_layout.py "$S/../stock_top.png" "$S/../stock_vs_layout.png"
```
