# Planned Route Redesigns — Wave 2 Contract

Branch: `feat/routes-wave2` (base: `origin/main` `b02114cbb4`, after Route 218 Everspring Sanctuary v2).
Target: **Native macOS / iOS / Linux SDL3 port ONLY** (DS `.nds` ROM is deprecated).

## 1. Visual & Technical Standards (Learned from Solaceon Town + Everspring v2)

Every route workstream MUST follow these proven Gen 4/5 art-direction & engine rules so the final routes look like official Platinum / Pokémon Iridium upgrades rather than programmer art:

1. **Preserve Stock Terrain Outside Redesigned Zones (Seamless Neighbor Safety):**
   - Unlike gated Route 218, these routes stream seamlessly against neighboring towns/routes on `map_matrix_000`.
   - Use **surgical terrain editing / chunkedit** (study `tools/solaceon_town/build_art.py` and `tools/lake_verity/nsbmd.py` / `nsbtx.py` / `mapdata.py`): keep stock terrain, cliffs, animated `sea` water, trees, and border rows/cols intact outside each route's redesigned focal zones, so seamless transitions into Veilstone, Route 210, Oreburgh, Eterna, Mt. Coronet, Acuity Lakefront, Valor Lakefront, Sunyshore, and Victory Road never break or pop.
   - Keep **every existing warp, trainer, item, and story NPC reachable** (or cleanly repositioned on walkable tiles with verified BFS reachability!). Never break existing main-story pathing!
2. **Append-Only Texture Sets (Zero Missing Stock Textures):**
   - Each route has its own dedicated `map_texture_set_078..082` seeded verbatim from its stock base set. Always **read the stock base set from git (`HEAD:res/field/mapmodels/texture_sets/map_texture_set_0XX.nsbtx`)** and **append** new math/pixel-art textures (16-color BGR555, Bayer-dithered, 16px/tile density, `c0=1` transparency for decals/foliage/props) so reruns are idempotent and stock textures never break.
3. **Authentic Platinum Art Direction (No Plastic / Smooth N64 Blobs):**
   - Reuse original animated Platinum `sea` water where water is present; add dithered shoreline foam/edges (`c0=1`) rather than raw sharp grid borders.
   - Never stretch a flat/wavy canopy sheet over trees; reuse/re-palette stock `tree01`/`conttree` or keep stock trees + dark shadows.
   - Build new 3D landmarks (boardwalks, Eclipse crates/shard racks/banners, Teo's carved stone memorial marker, Indra's camp tent/lantern, blacked-out coastal lamps, Kingdra rift rock, waterfall summit monoliths) with crisp DS-scale pixel-art textures, dark outlines, baked vertex-color AO/glow, and grounded Platinum palettes.
   - Respect `MAP_MODEL_FILE_SIZE = 0xF000` (61,440 B) and `BDHC_BUFFER_SIZE = 0x9000` (36,864 B) per chunk!
4. **Script & Text Hygiene (`CLAUDE.md`):**
   - Use **straight ASCII apostrophes** (`'` U+0027) ONLY — never curly quotes.
   - Keep existing text indices intact (append new messages at the end of `res/text/route_NNN.json`).
   - Run `python3 tools/dazzling/test/static_checks.py` (all 8 checks must pass with 0 problems!).
   - Mark all commits `(AI-assisted)`.

## 2. Shared Registry (Registered on Base Commit — Do Not Re-register)

`src/overlay005/area_light.c`: `AREA_LIGHT_FILE_COUNT` is already bumped to **`11`** (`0..10`).

| Package | Worktree / Branch | Chunks (`map_data_NNN.bin`) | Area Data | Texture Set (Stock Base) | Lighting Set | SDL3 Weather Kind |
|---|---|---|---|---|---|---|
| **Route 215** *(Flooded Lowland)* | `/data/repos/dp-wt/r215-flooded` (`routes/r215`) | `069, 070, 071` (`x=576..671, z=576..607`) | `area_data_080` | `map_texture_set_078` (`010`) | `lighting_set_006` | `kind = 8` (rain mist) |
| **Routes 206–207** *(Eclipse Supply Road)* | `/data/repos/dp-wt/r206-207-supply` (`routes/r206-207`) | `025..030` (`x=288..351, z=576..735`) | `area_data_081` | `map_texture_set_079` (`007`) | `lighting_set_007` | stock / clear |
| **Routes 216–217** *(Memorial Ridge & Indra's Camp)* | `/data/repos/dp-wt/r216-217-ridge` (`routes/r216-217`) | `106..112` (`x=288..383, z=256..415`) | `area_data_082` | `map_texture_set_080` (`014`) | `lighting_set_008` | `kind = 8` (alpine snowdrift) |
| **Route 222** *(Violet-Lit Coast)* | `/data/repos/dp-wt/r222-violet` (`routes/r222`) | `149, 150, 151` (`x=736..831, z=768..799`) | `area_data_083` | `map_texture_set_081` (`018`) | `lighting_set_009` | `kind = 7` (violet rift glow) |
| **Route 223** *(Rift Sea Route & Waterfall Summit)* | `/data/repos/dp-wt/r223-summit` (`routes/r223`) | `092, 093, 094, 095` (`x=832..863, z=608..735`) | `area_data_084` | `map_texture_set_082` (`013`) | `lighting_set_010` | `kind = 7` (violet rift sky) |
| **SDL3 Shaders & Verifier** | `/data/repos/dp-wt/routes-shaders` (`routes/shaders`) | — | — | — | — | `src/fx_weather.c`, `libntr.patch`, `tools/routes/verify_all_routes.py` |

## 3. Per-Route Redesign Briefs (from `docs/story/map_changes.md` & `arc3_screenplay.md`)

1. **Route 215 — Flooded Lowland & Eclipse Truck Ruts (Arc 2):**
   - Rain runoff from the Route 214 rift has turned the lowland route into a drenched marsh: raised **timber boardwalks** spanning flooded puddles/standing water, muddy **Eclipse truck tire ruts** heading east toward Veilstone's shipping depot, stacked wet supply crates / tarp-covered staging gear, moody overcast rain lighting (`lighting_set_006`), and atmospheric inspectable signs/NPC remarks (referencing the runoff from Route 214 and Eclipse's night trucks).
2. **Routes 206–207 — Eclipse Supply Road & Cycling Road Barricade (Arc 3):**
   - Route 207 becomes Eclipse's supply staging yard at Mt. Coronet's south entrance: **Eclipse violet banners, supply crates, shard racks, glowing work lights, wheel ruts** leading straight to Mt. Coronet's entrance (`map_data_026`), plus an inspectable manifest/crate sign.
   - Route 206 (under & around Cycling Road): warning cones/barricades & Eclipse equipment marking part of the old road closed/diverted, harsh industrial dusk lighting (`lighting_set_007`), keeping full north-south walkability and all existing items/trainers intact!
3. **Routes 216–217 — Teo's Memorial Ridge & Indra's Snowy Camp (Arc 3, Scene 3.7):**
   - Create a poignant, unmistakable landmark on the mountainside overlook (Route 216 / 217 transition ridge): **Teo's Memorial Marker** (a carved snow-dusted stone cairn/monolith with a small sheltered lantern, frozen floral offering, and inspectable `BG_EVENT` inscription honoring Teo — directly staging Scene 3.7 from `arc3_screenplay.md`!).
   - Build **Indra's Snowy Camp** nearby on Route 217: a weathered dark-violet Eclipse expedition tent, glowing tripod lantern, shard-scanner crate, and campfire/snow-packed clearing with an inspectable journal/field note hinting at Indra's search for Teo under Mt. Coronet.
   - Tune `lighting_set_008` to crisp melancholic blue-silver alpine twilight.
4. **Route 222 — Violet-Lit Coast (Arc 3):**
   - Coastal road bathed in eerie violet glow cast westward from the Route 223 rift (`lighting_set_009`): **blacked-out/darkened coastal street lamps** (with one or two flickering violet-haloed lamps), **stranded Water Pokémon** (`OBJ_EVENT_GFX_*` Magikarp/Shellos/Wingull/etc. or interactive shoreline events) along the tide line, and anxious dialogue/signs noting the unnatural violet glow over Sunyshore and Route 223.
5. **Route 223 — Rift Sea Route & Final-Battle Waterfall Summit (Arc 3, Scenes 3.15–3.17):**
   - Redesigned dramatic sea approach to the Pokémon League (`MAP_092..095`):
     - **Kingdra Totem Rift Rock** (`MAP_093`/`094`): an expanded rocky sea outcrop crowned with a **pulsing violet/cyan Rift Crystal spire & fractured energy ring** (inspectable `BG_EVENT` resonating with Kingdra's sea-rift lore!).
     - **Violet-Lit Waterfall & Final-Battle Summit Plateau** (`MAP_092`, top of the waterfall leading to Victory Road): carved ancient stone battle terrace flanked by twin glowing rift-scarred pillars & shattered shard chains framing the entrance to Victory Road, giving space for the climax of Dialga, Palkia, and Giratina (`lighting_set_010` deep dramatic violet storm sky).

## 4. Zero-Overlap File Ownership

- `r215-flooded`: `tools/routes/r215/*`, `res/field/mapmodels/data/map_data_0{69,70,71}.bin`, `res/field/mapmodels/texture_sets/map_texture_set_078.nsbtx`, `res/field/lighting/lighting_set_006.json`, `res/field/maps/route_215/*`, `res/text/route_215.json`
- `r206-207-supply`: `tools/routes/r206_207/*`, `res/field/mapmodels/data/map_data_0{25,26,27,28,29,30}.bin`, `res/field/mapmodels/texture_sets/map_texture_set_079.nsbtx`, `res/field/lighting/lighting_set_007.json`, `res/field/maps/route_206/*`, `res/field/maps/route_207/*`, `res/text/route_206.json`, `res/text/route_207.json`
- `r216-217-ridge`: `tools/routes/r216_217/*`, `res/field/mapmodels/data/map_data_{106,107,108,109,110,111,112}.bin`, `res/field/mapmodels/texture_sets/map_texture_set_080.nsbtx`, `res/field/lighting/lighting_set_008.json`, `res/field/maps/route_216/*`, `res/field/maps/route_217/*`, `res/text/route_216.json`, `res/text/route_217.json`
- `r222-violet`: `tools/routes/r222/*`, `res/field/mapmodels/data/map_data_{149,150,151}.bin`, `res/field/mapmodels/texture_sets/map_texture_set_081.nsbtx`, `res/field/lighting/lighting_set_009.json`, `res/field/maps/route_222/*`, `res/text/route_222.json`
- `r223-summit`: `tools/routes/r223/*`, `res/field/mapmodels/data/map_data_0{92,93,94,95}.bin`, `res/field/mapmodels/texture_sets/map_texture_set_082.nsbtx`, `res/field/lighting/lighting_set_010.json`, `res/field/maps/route_223/*`, `res/text/route_223.json`
- `routes-shaders`: `src/fx_weather.c`, `subprojects/libntr/*`, `tools/macos/patches/libntr.patch`, `tools/routes/verify_all_routes.py`
