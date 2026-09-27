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
- The builders check the real on-screen count per camera position (`assemble.camera_polys`, section 3). The
  per-chunk figures above are only soft warnings, and 0xF000 is the hard limit.

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
| `layout.py` | The tile contract (owned by the plan): collision, height and kind per tile. |
| `collision.py` | Permissions and BDHC from layout.py: flat plates merged on a half-tile grid, one sloped plate per chunk for the stair. `check` compares any BDHC against the layout at every tile centre. |
| `assemble.py` | Chunk assembly library: stock terrain (read from git at `STOCK_REV`, so regenerated chunks never feed back), `cut_stock` (drops the footprint), `merge`, `split_by_chunk`, `build_chunk` (model + stock props + layout permissions/BDHC -> map_data), `texture_table` (set-61 sizes and palettes), `check_budgets`. |
| `build_graybox.py` | Writes the graybox map_data 537/538/540/541 (section 4). |
| `build_art.py` | Assembles the art agent's `assets/` into map_data, set 61 and fldtanime (section 5). Dry run unless `--write`. |
| `roundtrip.py` | All round-trip and consistency checks (section 7). |

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

## 3. Running everything

Run everything from the repo root with the system `python3` (no numpy or PIL). None of these commands build the ROM.

```
# checks, about 1 s. --generated also checks the checked-in chunks against the layout
python3 tools/lake_verity/roundtrip.py --generated

# gameplay-facing collision: permissions + BDHC per chunk, compared with layout.py
python3 tools/lake_verity/collision.py

# final chunks from the art. Dry run first; --write writes map_data 537/538/540/541,
# set 61 and fldtanime.narc
python3 tools/lake_verity/build_art.py --preview /tmp/lv/art
python3 tools/lake_verity/build_art.py --write

# or the graybox instead of the art (overwrites the same 4 chunks; set 61 is not touched)
python3 tools/lake_verity/build_graybox.py --preview /tmp/lv/gb

# preview of what was written (the --preview files are decoded from the written NSBMD)
P="$HOME/Documents/Lake Verity Update/pipeline_checks"
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P tools/lake_verity/blender_preview.py -- \
    --tex tools/lake_verity/assets/textures --tex "$P/texset61" --out "$P/art_final" --views top,game \
    --target 32,31 /tmp/lv/art/chunk_537.mesh.json /tmp/lv/art/chunk_538.mesh.json \
    /tmp/lv/art/chunk_540.mesh.json /tmp/lv/art/chunk_541.mesh.json
python3 tools/lake_verity/compare_layout.py "$P/art_final_top.png" "$P/art_final_vs_layout.png"
```

To preview the graybox, add `--lit`, because graybox materials are lit like stock ones.

Both builders read the stock chunks and stock set 61 from git (`assemble.STOCK_REV`, f0527f80e). They never read their own output, so re-running is safe and deterministic.

Both builders print a budget report and refuse `--write` if there is an error:

| check | limit | kind |
|---|---|---|
| model bytes per chunk | 0xF000, the land_data.c load buffer | error |
| BDHC bytes per chunk | 0x9000 | error |
| map polygons on screen (`assemble.camera_polys`) | 1800 of the DS's 2048 per frame; the rest is headroom for sprites, shadows and the stock props | error |
| map polygons in any 16 x 12 tile window, by face centroid | 1800 | warning (older, cruder check) |
| polygons per chunk | 1000; stock max is 977 | warning |
| texture set VRAM | 76416, the largest stock set (048) | warning |

How `camera_polys` works:

- It puts the real field camera behind the player on every walkable tile and counts the faces that survive the view frustum (near 150, far 900) and back-face culling. The DS keeps only those faces in polygon RAM, and a quad counts as one polygon.
- It checks two cameras:
  - CAMERA_TYPE_ZOOMED_IN: pitch 54.66 deg, distance 515.46, half-fov 10.46 deg.
  - The stair tilt from `field_camera_zones.c`: pitch 44 deg, distance 460, applied at full strength on every tile the zone touches (x 21..26, z 29..37).
- As a sanity check, the stock map scores 703 (zoomed in) and 687 (stair camera).

## 4. The graybox (commit fdb22f3bc)

The graybox is a test build of the castle made from stock set-61 textures. The user can test it from commit fdb22f3bc. The art replaced it in commit 488d1159d. To go back to the graybox, run `build_graybox.py`.

How `build_graybox.py` builds it:

- **Footprint:** every layout tile whose kind is not stock (forest, water, grass, ground, exit), plus the stock hut tiles (29..35 x 28..34).
- **Stock terrain:** stock faces whose centroid tile is in the footprint are dropped if they rise above the water or if they are lakebed lying entirely inside the footprint.
  - Lakebed that straddles the footprint edge is kept, hidden under the island, so no holes open.
  - Lakebed under the bridge is kept.
- **Tops:** one quad per tile at its layout height, merged into rectangles of at most 16 tiles.
  - The stair top is exactly the BDHC slope: h 4 at z 30.5, down to h 0 at z 37.5.
  - Tiles are split at z 30.5 and 37.5 so the drawn surface and the collision agree.
- **Sides:** each tile edge is visited once, and the higher side owns the vertical face.
  - Where the two heights cross (stair against rail), the side is made of triangles.
  - Faces towards water go down to h -4; faces towards ground go down to h 0.
  - Runs of side faces are merged, at most 16 tiles each.
- **Bridge:** a deck at h 0 with sides down to -0.25.
- **Doors:** each door niche's back wall gets a `dhole` overlay 0.05 tile in front of it.
- **Materials:** named `gb_<texture>`, lit like stock, with flat normals and one texture repeat per tile.
- **Props:** the stock `l_lake` water plane is kept.
- **Permissions and BDHC:** generated by `collision.py`.

Textures used by each surface:

| surface | texture |
|---|---|
| courtyard, landing, door floors | beach |
| terrace1 | ngrass |
| keep2 top | blueglayp |
| roof | blueglay |
| wall tops, rail | criff |
| walls | criffp |
| island sides | criffp2 |
| towers, gatehouse | hanger |
| stair | newstep |
| bridge deck | bridge |
| bridge sides | nbridge |
| launchpad | fenter |
| hatch | shadowchip |
| door niches | dhole |

Graybox budgets:

| chunk | polys | verts sent | model B | BDHC B (plates) | materials |
|---|---|---|---|---|---|
| 537 | 655 | 2215 | 30144 | 1046 (28) | 17 |
| 538 | 651 | 2216 | 30460 | 946 (26) | 19 |
| 540 | 838 | 2933 | 38704 | 904 (23) | 19 |
| 541 | 883 | 3102 | 41588 | 886 (23) | 25 |

- On screen: at most 542 polygons with the zoomed-in camera and 582 with the stair camera.
- Worst 16 x 12 window: 461 polygons.

Graybox renders, in `~/Documents/Lake Verity Update/pipeline_checks/`:

- `graybox_top.png`
- `graybox_game.png`
- `graybox_stair_game.png`
- `graybox_bridge_game.png`
- `graybox_vs_layout.png`, which shows the island lining up exactly with layout.py.

## 5. Assembling the art (`build_art.py`, commit 488d1159d)

Inputs are in `tools/lake_verity/assets/`, in the PLAN.md mesh format; see its README for counts.

- **`chunk_<id>.mesh.json`:** the full terrain for that chunk. It replaces the stock terrain.
  - A chunk without one keeps the stock terrain minus the footprint, as in the graybox.
- **Other `*.mesh.json` (castle, bridge, portal):** positioned in absolute tiles.
  - They are split into chunks by face centroid and merged into the chunk models.
  - They are not map props. Map props would need build_model archive entries and an entry in the area's preload list.
- **`textures/<name>.png` + `<name>.json`:** each JSON holds `{"format", "repeat", "c0", "palette"?, "frames"?, "frame_ticks"?}`.
  - Textures are encoded with `nsbtx.encode_texture` and appended to stock set 61.
  - Stock textures stay, because area 62 is also used by Sendoff Spring, Lake Verity (low water) and both Lake Valor maps.
  - A name that clashes with a stock texture is an error.
  - The palette is `<texture>_pl` unless `"palette"` is given. Names are at most 16 characters.
- **Animations:** each texture with `"frames"` gets a fldtanime entry (frame index and `frame_ticks` VBlanks per frame) and a frame NSBTX named `<name>.1..N`. This follows the coronet_lava `add_lava_anim.py` precedent.
  - The field looks entries up by texture name in the current set, copies each frame's texels over the texture and never swaps the palette.
  - So the base texture and all its frames are re-indexed onto one shared palette (`share_palette`).
  - Frame textures do not go into the set.
  - At most 16 animated textures can be active on a map (`MAX_TEXTURE_KEYS`).
- **Lighting:** materials whose meshes carry `colors`, and that don't set `polygon_attr.lights`, are built unlit (lights 0, a colour per vertex, no normals), so the bake shows. Set `"lights": 1` for stock-like lit shading.
- **Water:** if any material uses `lv_water`, the stock `l_lake` prop is dropped (the props section is written empty, as in 283 stock chunks), so the two water planes don't z-fight. Use `--keep-lake` to keep it.
- **Height check:** every walkable tile's drawn floor must be within 0.25 tile of its layout/BDHC height.

Results of the committed assembly:

| chunk | polys | verts sent | model B | BDHC B | materials |
|---|---|---|---|---|---|
| 537 | 719 | 2501 | 38536 | 1046 | 12 |
| 538 | 781 | 2737 | 41756 | 946 | 14 |
| 540 | 1141 (warning) | 3907 | 58404 (0xF000 = 61440) | 904 | 12 |
| 541 | 978 | 3277 | 49760 | 886 | 15 |

- Set 61: 62 stock + 17 new textures, VRAM 71200 + 1888 = 73088 B.
- fldtanime:

| member | texture | frames | VBlanks per frame |
|---|---|---|---|
| 55 | lv_flame | 4 | 4 |
| 56 | lv_portal | 4 | 6 |
| 57 | lv_water | 8 | 8 |

- On screen: at most 827 polygons with the zoomed-in camera (at 32,27) and 713 with the stair camera. Worst 16 x 12 window: 672.
- 0 walkable tiles are off the layout height.
- The gameplay tiles check out:
  - The door tiles are walkable with behaviour 0x6e: (32,33) at h 0, (32,30) at h 4 and the hatch (33,27) at h 10.
  - (32,34), (32,31) and (32,27) are walkable.
- Renders: `art_final_top.png` and `art_final_game.png`, decoded from the written chunks.

## 6. A new texture set and area data entry

This is optional: it lets Lake Verity stop sharing area 62. Appending to set 61 works without touching anything else, and set 61 is still below the largest stock set. Lake Verity needs its own area if either of these happens:

- the other four area-62 maps must not pay the extra VRAM;
- Lake Verity needs its own area light.

`build_art.py --write --new-set` does steps 1 and 2, following the Mt. Coronet lava precedent (`tools/coronet_lava/make_texset.py`, `add_area_data.py`, `docs/coronet_1f_lava/PLAN.md`).

1. **Texture set.**
   - It writes `res/field/maps/texture_sets/map_texture_set_075.nsbtx`, which is stock set 61 plus the art textures.
   - It appends that file to both `texture_sets/meson.build` (after `map_texture_set_074.nsbtx`) and `map_texture_set.order`. The NARC index is the list position.
   - It restores set 61 to stock.
2. **Area data.**
   - It appends to `res/prebuilt/fielddata/areadata/area_data.narc` a copy of entry 62 (props list 58, light 0) that uses set 75. That is entry 76 = 0x4C; there are currently 76 entries, 0..0x4B.
   - Each entry is `u16 props list, u16 texture set, u16 dummy, u16 area light`.
   - Re-running rewrites the same set and entry.
3. **Map header (not done by the tool).**
   - Set `areaDataArchiveID` of `MAP_HEADER_LAKE_VERITY` in `include/data/map_headers.h` (currently 62) to 0x4C. Coronet made the same change for `MT_CORONET_1F_SOUTH` (0x4B).
   - Without this change, Lake Verity loads stock set 61 and the art textures are missing.
   - This is a header edit, so it belongs to the gameplay owner.
4. **Optional light.** `tools/coronet_lava/add_area_light.py` shows how to add an area light; put its id in the new entry.

fldtanime is keyed by texture name, not by set, so the animations work with either set.

## 7. Round-trip results (`roundtrip.py --generated`: all pass)

| check | result |
|---|---|
| NSBMD parse -> build, stock 537/538/540/541 | byte-identical |
| GX display lists decode -> encode | byte-identical, 52/52 shapes |
| mesh.json -> NSBMD -> decode | same faces (positions, UVs, normals) and material attributes |
| NSBTX rebuild, all 75 map texture sets | 74 identical; set 007 differs (the coronet tools renumbered its dictionaries) |
| set 61 textures decode -> encode -> decode | 79/79 same pixels (62 stock + 17 art) |
| map_data unpack -> pack | 666/666 identical |
| BDHC read -> write | 666/666 identical |
| BDHC strip builder vs stock | 665/666; map_data_184 has a zero-depth plate that the stock tool listed once more |
| collision.bdhc vs layout, 4 chunks x 1024 tile centres | 0 mismatches |
| checked-in chunks: BDHC and permissions vs layout | 0 mismatches, identical |

In the mesh.json round trip, our strips send 3 to 4% more vertices than Nintendo's (chunk 541: 3394 vs 3314 vertices, 44548 vs 43704 B).

## 8. Known gaps and open problems

- **Lighting vs PLAN.md:**
  - The art's coloured materials are unlit (baked), so they won't follow the area light or darken at night. Stock map materials are lit.
  - Needs an art-direction decision, ideally checked on hardware at night. The alternative is `"lights": 1` per material.
- **Area 62 is shared:** set 61 grew from 44320 to 73088 B of VRAM, and Sendoff Spring and Lake Valor load it too. That is within stock precedent (76416), but only hardware proves it. Section 6 is the way out.
- **Chunk 540 density:** 1141 polygons, the only soft warning. Its model is 58404 B, 3 KB under the buffer, so there is little room for more art in that chunk.
- **Per-frame count:**
  - `camera_polys` models the camera without its 6-frame follow delay and ignores sprites, shadows and stock props (hence the 1800 limit).
  - It assumes the materials' cull flags are what the DS uses.
  - The real count needs the ROM.
- **Not verified in-game:**
  - the fldtanime frame format (it matches the coronet_lava precedent);
  - the tex4x4 encoder, which is simple (extreme colours per 4x4 block);
  - fog and area light colours.
- **Strip efficiency:** 3 to 4% more vertices than stock. Harmless.
- **Not handled here:**
  - map props with their own build_model archive entries;
  - the 539/542 filler chunks (unchanged);
  - LAKE_VERITY_LOW_WATER's own chunks: the gameplay branch now uses matrix 102 for every story state.
- **layout.py:** water was at h 0. It is now `WATER_H = -0.5`, matching the stock BDHC on 3730/3730 non-island tiles. This was a genuine bug, fixed in f6bb633bf; the docstring is correct.
