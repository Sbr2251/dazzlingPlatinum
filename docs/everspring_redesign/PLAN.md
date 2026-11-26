# Route 218 — Everspring Sanctuary Redesign Contract

Branch: `feat/everspring-redesign` (base: `origin/main` `f571ecb7eb`).
Target: **Native macOS / iOS / Linux SDL3 port ONLY** (DS `.nds` ROM is deprecated).

## 1. Design Vision & Art Direction

Redesign Route 218 (**Everspring Sanctuary**, between Canalave City and Jubilife City, `MAP_050` + `MAP_051` on `map_matrix_000` row 23 cols 2–3, world coords `x=64..127, z=736..767`) into a completely new **Crescent Fairy Glade** anchored by a monumental **Gardevoir Fountain**.

- **Math-driven assets, authentic Platinum art direction:**
  - Procedural Python generators (`tools/everspring/`) produce all new 3D geometry (`NSBMD` meshes in `map_data_050.bin` / `map_data_051.bin`) and pixel-art textures (`map_texture_set_077.nsbtx`) from equations (SDF shapes, logarithmic spiral blossoms, Voronoi/rounded-box moonstone cobbles, trigonometric caustic water, lathed/extruded low-poly Gardevoir statue & fountain tiers, glowing mushrooms, Rift Crystal obelisk) — **strictly snapped to Platinum's 16px/tile texel grid, 16-color BGR555 palettes with controlled Bayer dithering, crisp dark outlines, and baked vertex-color lighting/AO**.
  - Native **SDL3 runtime math FX** (`kind = 6`, Everspring Fairy Sanctuary in `src/fx_weather.c` + `subprojects/libntr`) adds gentle drifting bioluminescent spores/petals, subtle twilight lavender-indigo color grading, soft water reflections/caustics, and screen-blended glow without clipping to harsh white.
- **Keep stock Canalave/Jubilife seam safety:** `map_texture_set_077.nsbtx` starts from a copy of stock `map_texture_set_015.nsbtx` (preserving stock texture names if edge chunks ever load) and appends/overrides Everspring fairy textures.

## 2. Shared Registry (Registered on Base Commit — Do Not Re-register)

| Asset | ID | Notes |
|---|---|---|
| Area Data | `area_data_079` | `prop_model_set_011`, `map_texture_set_077`, `lighting_set_005` |
| Texture Set | `map_texture_set_077` | Base `map_texture_set_015` + Everspring math-generated fairy textures (`everspring/art` owns binary) |
| Lighting Set | `lighting_set_005` | Custom twilight-fairy lighting curves (`everspring/art` owns JSON tuning) |
| Route 218 Header | `res/field/maps/route_218/header.json` | `"areaData": "area_data_079"` |
| SDL3 Weather FX Kind | `kind = 6` (`SIM_Weather_Set(6, ...)`) | Everspring Fairy Sanctuary shader mode (`everspring/shaders` owns implementation) |

## 3. Redesigned Layout Contract (World Coordinates: `x=64..127`, `z=736..767`)

Chunk boundary: `MAP_050` covers `x=64..95`, `MAP_051` covers `x=96..127`. Both span `z=736..767`.
The route shape is **completely redesigned** into a crescent fairy glade surrounding a central moonlit lagoon and octagonal **Gardevoir Fountain Island**:

### Fixed Gate Warps (NEVER MOVE)
| Warp | World `(x, z)` | Notes |
|---|---|---|
| Canalave Gate (West) | `(70, 754)`, `(70, 755)` | Exits east into West Blossom Approach |
| Jubilife Gate (East) | `(121, 758)`, `(121, 759)` | Exits west into East Wisteria Grove |

### Major Zones
1. **West Blossom Approach (`x=70..82, z=751..756`)**: Curving moonstone cobble path emerging from Canalave Gate, framed by sakura/wisteria blossom trees and glowing mushrooms.
2. **North-West Fairy-Ring Alcove (`x=74..80, z=744..750`)**: Quiet blossom clearing north of the west path (connected at `x=76..78, z=750..751`) holding the West Item (`Rare Candy`).
3. **Spiral Blossom Meadow (`x=74..86, z=756..763`)**: Crescent-shaped tall grass meadow where the Rift's pulse illuminates a 3-arm logarithmic spiral of glowing blossoms (`sin(3θ - 1.55r)`). Contains a small flower clearing at `(81, 760)` for `LOCALID_EVERSPRING_CLEFAIRY_WEST`.
4. **West Arched Moonbridge (`x=83..87, z=752..754`)**: 5-tile-long, 3-tile-wide silver-lavender timber bridge with rose-gold railings and warm lantern posts crossing the western lagoon inlet directly onto the Central Gardevoir Fountain Island (`height = 0`, walkable).
5. **Central Gardevoir Fountain Island (`x=88..101, z=745..758`)**: Octagonal terraced moonstone plaza ringed by shimmering crescent water (`z=741..764`).
   - **Gardevoir Fountain (`x=93..96, z=749..752`, 4×4 blocked)**: Multi-tiered octagonal pale moonstone basin with glowing cyan-lavender water, cascading water arcs, and a **sculpted 3D low-poly Gardevoir statue** facing south toward the camera (flowing white marble gown, emerald hair/crest, rose-crystal chest emblem, arms outstretched in a protective ward).
   - **Fountain Plaque Standing Tiles**: `(94, 753)` and `(95, 753)` walkable; facing NORTH triggers `Route218_GardevoirFountain` (`BG_EVENT_TYPE_FACING` at `(94, 752)` and `(95, 752)`).
   - **Rift Conduit Crystal Pillar (`x=98..99, z=747`, 2×1 blocked)**: Faceted violet/cyan crystal obelisk on the NE plaza terrace; standing at `(98, 748)` or `(99, 748)` facing NORTH triggers `Route218_RiftShrine` (`BG_EVENT_TYPE_FACING` at `(98, 747)` and `(99, 747)`).
   - **East Surf Landing (`x=101, z=751..754`)**: Gently sloped moonstone steps into the East Lagoon Surf crossing.
6. **East Shimmering Lagoon Surf Crossing (`x=102..106, z=746..759`)**: 5-tile-wide iridescent fairy water channel preserving Platinum's Surf gate between Jubilife and Canalave. Early-game visitors from Jubilife can walk out onto the East Lantern Pier and see the glowing Gardevoir Fountain across the water.
7. **East Lantern Overlook Pier (`x=107..111, z=752..754`)**: Silver-lavender lantern pier extending west from the East Wisteria Grove to the lagoon's edge (`x=107, z=752..754` meets Surf water at `x=106`).
8. **East Wisteria Grove & Meadow (`x=108..121, z=744..762`)**: Curving moonstone path from Jubilife Gate (`121, 758..759`) north-west to the East Lantern Pier, plus an East Fairy Tall Grass patch (`x=112..118, z=751..755`) and North-East Glade (`x=108..116, z=744..749`).

### Exact Event & NPC Anchor Coordinates (Single Source of Truth)
| Entity | Kind | World `(x, z)` | Facing / Trigger |
|---|---|---|---|
| `Route218_GardevoirFountain` | `BG_EVENT_TYPE_FACING` | `(94, 752)`, `(95, 752)` | `BG_EVENT_DIR_NORTH` (stand at `z=753`) |
| `Route218_RiftShrine` | `BG_EVENT_TYPE_FACING` | `(98, 747)`, `(99, 747)` | `BG_EVENT_DIR_NORTH` (stand at `z=748`) |
| `LOCALID_EVERSPRING_RIVAL` (Barry) | Object (Barry) | `(95, 755)` | `DIR_SOUTH`, `FLAG_HIDE_EVERSPRING_RIVAL` |
| `Route218_RivalScene` | Coord Event | `x=89, z=756, w=11, l=2` | `VAR_EVERSPRING_RIVAL_SCENE_STATE == 0` |
| `LOCALID_RIFT_RESEARCHER` | Object (Scientist F) | `(90, 748)` | `DIR_SOUTH` |
| `LOCALID_EVERSPRING_CLEFAIRY_WEST` | Object (Clefairy) | `(81, 760)` | `DIR_NORTH` |
| `LOCALID_EVERSPRING_CLEFAIRY_EAST` | Object (Clefairy) | `(110, 748)` | `DIR_WEST` |
| `LOCALID_EVERSPRING_ITEM_WEST` | Object (PokeBall) | `(77, 745)` | `VisibleItems_Route218_RareCandy` |
| `LOCALID_EVERSPRING_ITEM_EAST` | Object (PokeBall) | `(114, 745)` | `VisibleItems_Route218_HyperPotion` |
| `LOCALID_EVERSPRING_SIGN_WEST` | Object (Signboard) | `(73, 753)` | `Route218_SanctuarySign` |
| `LOCALID_EVERSPRING_SIGN_EAST` | Object (Signboard) | `(119, 757)` | `Route218_SanctuarySign` |

## 4. Gardevoir Fountain Lore Contract

- **Who she was:** Long before the Canalave–Jubilife gatehouses were built, a tear in space opened over this coastal marsh, threatening to swallow travelers and drown the shore. A lone **Gardevoir** stood at the heart of the marsh and poured out her aura—not to shatter the rift, but to weave its wild energy into a living ward. Where her power settled, the marsh bloomed into an eternal spring of luminous flowers whose spiral pattern still echoes the barrier she wove.
- **The Fountain:** Travelers from Canalave and Jubilife raised this moonstone fountain in her likeness—arms outstretched, keeping the waters clear and calm. Legend says whenever the rift beneath Everspring stirs again, the fountain's waters brighten and the meadow's spiral blossoms answer her call.
- **Integration with existing story:** Keep Barry's existing rival dialogue (Cyrus, Totems, father's conduits), the Rift Researcher's spiral-flower observation (optionally adding a line connecting the spiral to the Gardevoir legend), both Clefairies, and the Rift Crystal's warm vibration. Fix the `"EVERSRING SANCTUARY"` typo → `"EVERSPRING SANCTUARY"`.

## 5. Workstream File Ownership (Zero Overlap)

| Workstream | Branch / Worktree | Owned Files |
|---|---|---|
| `r218-art` | `everspring/art` (`/data/repos/dp-wt/r218-art`) | `tools/everspring/{layout.py,collision.py,textures_math.py,gardevoir_fountain.py,build_art.py}`, `res/field/mapmodels/data/map_data_050.bin`, `res/field/mapmodels/data/map_data_051.bin`, `res/field/mapmodels/texture_sets/map_texture_set_077.nsbtx`, `res/field/lighting/lighting_set_005.json` |
| `r218-shaders` | `everspring/shaders` (`/data/repos/dp-wt/r218-shaders`) | `src/fx_weather.c`, `subprojects/libntr/...` (SDL3 Fairy Sanctuary weather/spore/glow pass `kind=6`) + `tools/macos/patches/libntr.patch` |
| `r218-story` | `everspring/story` (`/data/repos/dp-wt/r218-story`) | `res/field/maps/route_218/{events.json,scripts.s,encounters.json}`, `res/text/route_218.json` |
| `r218-verify` | `everspring/verify` (`/data/repos/dp-wt/r218-verify`) | `tools/everspring/verify_route218.py` (headless Linux test + day/night/FX screenshot harness) |
