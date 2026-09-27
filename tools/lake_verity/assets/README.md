# Lake Verity redesign: exported art

These are the game-ready exports from the art scripts in `~/Documents/Lake Verity Update/art/`:
- `lv_textures.py` paints and quantises the textures.
- `lv_geom.py` builds the geometry, bakes the vertex colours and exports the meshes.
- `lv_render.py` renders the previews.

All files follow the intermediate format in `docs/lake_verity_redesign/PLAN.md`. Do not edit them by hand; re-run the scripts instead.

## Meshes

| file | kind | origin_tile | polys (tri/quad) | verts | notes |
|---|---|---|---|---|---|
| chunk_537.mesh.json | terrain | [0, 0] | 464 (78/386) | 1242 | NW forest, shore, lake |
| chunk_538.mesh.json | terrain | [32, 0] | 475 (78/397) | 1281 | NE forest, shore, lake, island north half (x >= 32) |
| chunk_540.mesh.json | terrain | [0, 32] | 986 (168/818) | 2781 | SW forest, tall grass, island SW, courtyard west |
| chunk_541.mesh.json | terrain | [32, 32] | 758 (114/644) | 1963 | SE shore, tall grass, dirt path, exit, courtyard east |
| castle.mesh.json | prop | [32, 32] | 615 (32/583) | 1938 | one-storey F1 block with an open roof terrace (h4) inside a crenellated parapet, 2 south towers, west stair + landing + rail wall, gatehouse, torches; plain paving at the terrace centre (32,27) under the stock portal |
| bridge.mesh.json | prop | [32, 32] | 39 (0/39) | 104 | lowered drawbridge (42..49, 36..37) and chains |

There is no portal mesh any more. The terrace portal is the stock Distortion World portal of distorted Spear Pillar (map prop 581 `d5_ana_pl` with its stock textures and animation), placed by `build_art.py` and `stock_portal.py`; see `docs/lake_verity_redesign/pipeline.md` section 5, "The portal". The old `portal.mesh.json` (ring, swirl disc, halo, light shaft), the `lv_portal` texture with its frames and the terrace's `lv_sigil` ring were removed.

The pipeline budget is 1000 polygons or fewer per chunk; every chunk is under it. Chunks 539 and 542 are not generated, so they stay stock. The castle, 540 and 541 are on screen together. Off-screen polygons are clipped, and a ZOOMED_IN frame sees about 15 x 11 tiles.

### Conventions

- Positions are absolute tiles (x east, h up, z south), taken from `tools/lake_verity/layout.py`.
- Every walkable tile centre was ray-checked against its layout height by `lv_geom.py`. Stair tiles were checked against the continuous slope `h = 4 * (37.5 - z) / 7` within 0.16.
- The stair has 12 treads of 0.5 tile. Each tread's height equals the slope at its centre, so tile centres land exactly on `stair_height(z)`.
- Water is drawn at h = -0.5, the stock l_lake plane and stock BDHC surf height. Shore ground is at 0.
- Faces are CCW when seen from their front: cross(b - a, c - a) points outward. Faces that no field camera can see were dropped, which removes most north-facing and underside faces.
- UVs are texel / size with v = 0 at the top PNG row. Atlas UVs are inset by 1/16 texel.
- Vertex colours hold all the baked lighting and are snapped to 5-5-5:
  - sun from the SW-above;
  - sky ambient with AO;
  - warm torch and candle point lights.
- Materials are unlit (lights off in the bake sense). Build them without normals.
- Material `polygon_attr`:
  - opaque: `{"cull": "back"}`
  - `lv_chain`: `{"cull": "none"}`
  - translucent a3i5 materials use `{"cull": "none", "polygon_id": N}` with glow 1, flame 2 and foam 3. The distinct IDs stop translucent overlaps from rejecting each other.

## Textures (`textures/`)

| texture | format | size | frames | texel + palette bytes (all frames) | repeat |
|---|---|---|---|---|---|
| lv_grass | pltt16 | 128x128 | 1 | 8224 | s, t |
| lv_paving | pltt16 | 64x64 | 1 | 2080 | s, t |
| lv_stone | pltt16 | 64x64 | 1 | 2080 | s, t |
| lv_cliff | pltt16 | 64x16 | 1 | 544 | s |
| lv_trim (atlas) | pltt16 | 64x64 | 1 | 2080 | - |
| lv_foliage (atlas) | pltt16 | 64x64 | 1 | 2080 | - |
| lv_canopy | pltt16 | 64x64 | 1 | 2080 | s, t |
| lv_roof | pltt16 | 32x32 | 1 | 544 | s, t |
| lv_wood | pltt16 | 32x64 | 1 | 1056 | s, t |
| lv_path | pltt16 | 32x64 | 1 | 1056 | t |
| lv_sigil (castle interior only) | pltt16 | 64x64 | 1 | 2080 | - |
| lv_chain | pltt4 | 8x16 | 1 | 40 | t |
| lv_water | pltt16 | 64x64 | 8 (8 ticks) | 16416 | s, t |
| lv_flame | a3i5 | 16x32 | 4 (4 ticks) | 2112 | - |
| lv_glow | a3i5 | 32x32 | 1 | 1088 | - |
| lv_foam | a3i5 | 32x16 | 1 | 576 | s |

- Total over all frames: 44136 bytes.
- Only the textures a builder uses go into a texture set: set 61 gets 10 of them (no lv_water, lv_foam, lv_grass, lv_canopy, lv_path, lv_sigil in stock-terrain mode); the castle interior's set 075 gets 7, including lv_sigil. Flame frames go in a fldtanime NSBTX, not in the map texture set.
- `lv_glow` is still used by the torch flames.

### Sidecar json keys

- `format`, `repeat` and `c0` are read by `nsbtx.load_texture_dir`. `c0` = 1 means palette colour 0 is transparent.
- `color0_transparent` is informational.
- Animated textures:
  - The base json lists `frames` (PNG names in order) and `frame_ticks`.
  - Every frame PNG has its own json with the same format, plus `frame_of` and `frame_index`.
  - The frames of one texture share one palette, and their texel indices line up, so fldtanime can copy texels over the base texture.

### Format notes

- **pltt16 / pltt4:** indexed PNGs.
  - Opaque textures never use index 0.
  - Transparent atlases (lv_trim, lv_foliage, lv_chain, lv_sigil) use index 0 as transparent.
- **a3i5:** RGBA PNGs.
  - RGB is the snapped palette colour. Alpha is quantised to 8 levels.
  - At most 32 colours per frame. The pipeline builds the a3i5 palette per PNG, so palette order can differ between frames.
  - For animated lv_flame, build one palette for all 4 frames, or animate it with a texture swap instead of a texel copy.

## Notes for the pipeline / gameplay agents

- Remove or disable stock prop 311 (the l_lake water plane, h -0.5). Chunk water is now part of these meshes and would z-fight with it.
- The layout.py docstring on HEAD still says water is flush with the shore (h 0). The art uses -0.5, which matches the stock data and the pipeline's `WATER_H` fix.
- The stair's west balustrades, landing balustrades and gatehouse torches are cards. They are thin from the straight-on field camera but read well at the stair camera tilt.
