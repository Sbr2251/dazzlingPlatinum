# Brilliant Diamond-Style 3D Battle Scene Plan (`feat/bdsp-battle-scene`)

Goal: evolve Dazzling Platinum's macOS/iOS Metal battle scene into a full-frame 16:9 3D stylized battle presentation modeled on *Pokemon Brilliant Diamond / Shining Pearl* (BDSP) — lush 3D biome clearings with layered cliffs/trees/sky, real-time soft cast shadows and atmospheric lighting, over-the-shoulder perspective camera, and edge-docked HUD with 100% unobstructed battlefield visibility — while preserving compatibility with all ~470 existing battle scripts, move animations, Mega Evolution, and Totem battles.

Because NDS ROM builds are no longer supported (`CLAUDE.md`), this branch is free to use native Metal GPU pipelines, 32-bit RGBA textures, glTF 2.0 (`.glb`) 3D assets, real shadow maps, and display-resolution rendering on macOS and iOS.

---

## Current Baseline vs. Target Look

| Layer | Current (`main` / `86a7fae03a`) | Target (BDSP Reference) |
|---|---|---|
| **Arena geometry** | `battle_stage.narc`: DS-budget `<=600` polys, 64 KB indexed textures, projection-mapped flat BG3 backdrop + oval platform discs | Native Metal 3D `.glb` biome clearings (grass-to-dirt ground, zero platform ovals, sculpted cliffs, bushes, flowers, layered pine trees, sky dome) |
| **Lighting & shadows** | DS vertex lighting + flat oval `BLOB_TEX` A5I3 ground shadows | Directional sun + hemisphere sky/ground ambient + 1024x1024 PCF soft shadow map (real silhouette shadows on grass) + exponential atmospheric distance haze |
| **Camera** | Home pose mirrors classic DS ortho framing; wide aspect 16:9 | Low over-the-shoulder perspective behind player mon (left foreground) looking across clearing toward opponent (right midground), with smooth idle drift & action cuts |
| **Battlers** | Animated 2D/Gen 5 sprites on 8x8 deformable quads (`battle_stage_sprites.c`) | Either **Option A (HD-2D)** lit sprites with real projected shadows on 3D ground, or **Option B (True 3D)** animated `.glb` Pokemon models with cel/toon Metal shader + automatic 2D fallback |
| **Battle HUD** | Bottom 48px Platinum `PL_WINFRAME` bar + DS OAM healthboxes | Edge-docked corner HUD: enemy bar top-right, player bar + party balls bottom-left, vertical 4-button stack (`Battle` / `Pokemon` / `Bag` / `Run`) + quick-Ball shortcut bottom-right; message box appears only during text events so 100% of the clearing is visible |

---

## Architecture Overview

### 1. Native Metal 3D Scene Pass (`subprojects/libntr`, `render_gpu/`)
Rather than squeezing high-poly 3D environments through NitroSDK's 16-bit fixed-point `G3_*` FIFO and 64 KB DS VRAM:
- Add a clean C bridge `include/port/sim_battle3d.h` / `src/port/sim_battle3d.c` (weak symbols like `sim_wide.c`, no-op when disabled or in headless goldens unless `SIM_FX_BDSP_BATTLE=1`).
- Game code passes per-frame scene state to Metal:
  - `biomeId` (`BACKGROUND_*` + `TERRAIN_*`), `timeOfDay` (morning/day/evening/night), `weather` (clear/rain/sun/hail/sand/fog)
  - Camera pose (`view` + `projection` 4x4 float matrices derived from `battle_stage_camera.c`)
  - Up to 4 battler world transforms (`pos, yaw, scale, animState, animTime, speciesId, form, isShiny, visible`)
  - Suppression / fade alpha (respects `BattleStage_Suppress()` so legacy BG2/BG3 move animations fade cleanly with zero breakage).
- Inside `render_gpu/` (`sim_render_gpu_g3.cpp` + new `fx_battle3d.cpp`):
  - **Asset loader**: vendored single-header `cgltf.h` + `stb_image.h` (pure C/C++, works identically on macOS and iOS Metal, zero external dependencies) loading `.glb` files from `Resources/game/battle3d/`.
  - **Pass 1 (Shadow Map)**: render shadow-casting arena props (trees/cliffs) and battlers from directional sun light into a `1024x1024` `D32_FLOAT` shadow texture.
  - **Pass 2 (Native 3D Battle Scene)**: render sky dome, 3D clearing ground, instanced foliage/rocks/trees, and 3D battlers (if enabled) directly into the Metal `Scene3D` target at full internal resolution (`4x` Mac / `2x` iOS), writing compatible depth so DS 3D particles (`SPL`) and 2D/HD-2D sprites composite in correct depth order.
  - **BDSP Toon/Painterly Shader (`battle3d.vert` / `battle3d.frag`)**:
    - Soft 2-band stylized diffuse ramp (keeps BDSP's bright, storybook warmth rather than harsh photorealism)
    - Hemisphere ambient (`skyColor` / `groundBounceColor`) keyed to time-of-day + weather
    - 4-tap PCF directional shadow sampling with soft warm-tinted shadow color (never muddy black)
    - Subtle Fresnel rim highlight on battlers + foliage edge light
    - Smooth exponential distance + height fog blending distant pines into the sky horizon.

### 2. Biome Arena Pipeline (`tools/battle3d/`)
Build a repeatable, offline Blender/Python asset pipeline generating compact `.glb` biome arenas under `res/battle3d/arenas/` (bundled into `Dazzling Platinum.app/Contents/Resources/game/battle3d/`):
- **Vertical Slice Biome (Milestone 1)**: `plain_route.glb` (Sinnoh Route 201/202 sunny meadow clearing — matches the reference screenshot: grass-to-dirt clearing floor, layered mossy cliffs, bushes, wildflowers, multi-tier stylized pine trees, sky dome).
- **Biome Roster (Milestone 5)**: 8 core biome arenas covering all 23 `BACKGROUND_*` values via biome mapping + time-of-day / weather lighting presets:
  1. `plain_route` (Plain / Grassy routes)
  2. `forest` (Eterna Forest dense canopy clearing)
  3. `water_lake` (Lakeside / Surf shoreline with animated water plane)
  4. `mountain_cave` (Mt. Coronet / Oreburgh rocky cavern)
  5. `snow` (Snowpoint / Route 216 snowy pines)
  6. `city` (Jubilife / Veilstone paved plaza)
  7. `indoors_gym` (Gym / League / Battle Frontier stadium floor)
  8. `distortion_world` (Floating platforms + purple cosmic skybox)

### 3. Over-the-Shoulder Camera & Legacy Move Compatibility (`src/battle/battle_stage_camera.c`)
- Add a BDSP over-the-shoulder **home pose** (`yaw`, `pitch`, `fov ~38 deg`, low eye height near player mon's shoulder) with separate tuned poses for Singles and Doubles.
- Keep the existing **Home Pose Rule**:
  - During command selection, gentle breathing/idle camera drift circles subtly around the clearing.
  - For moves that use legacy screen-space 2D/BG2/OAM tricks, ease smoothly to the safe framing pose or suppress the 3D arena via existing `BattleStage_Suppress()` with the 8-frame crossfade so all ~470 move animations stay intact.
  - For modern 3D-safe attacks, Poké Ball throws, and Mega Evolutions, allow dynamic camera cuts (attacker close-up -> defender impact -> return to over-the-shoulder).

### 4. Battlers & Shadows (`src/battle/battle_stage_sprites.c` + `fx_battle3d.cpp`)
Two compatible tracks (Track A lands immediately for 100% of species; Track B layers on top cleanly):
- **Track A — Lit HD-2D Sprites on 3D Ground (Immediate, 100% species coverage)**:
  - Place each battler quad in true 3D clearing coordinates (no floating oval platforms), sized by species height/scale.
  - Cast each battler's **alpha-tested sprite silhouette into the 1024x1024 directional shadow map** so Honchkrow / Bidoof cast real shaped shadows onto the grassy clearing!
  - Apply matching BDSP sunlight + rim light + atmospheric tint in `g3.frag`.
- **Track B — Animated 3D glTF Pokemon Models (Incremental BDSP fidelity)**:
  - Skinned mesh GPU skinning (`jointMatrices[64]` uniform buffer in `battle3d.vert`) loading `battle3d/mons/<species_id>[_form][_shiny].glb`.
  - Standard clip table: `idle`, `attack_phys`, `attack_spec`, `hit`, `faint`, `cry`.
  - Driven directly from existing battle state hooks (`PokemonSprite` anim triggers, HP/status speed modulation, faint drop).
  - Automatic per-species fallback to Track A whenever a `.glb` is not present.

### 5. Corner-Docked Full-Frame 16:9 Battle HUD (`src/battle/battle_hud.c`, `healthbox.c`, or Metal HD HUD pass)
To match the BDSP screenshot's unobstructed 16:9 framing (zero permanent bottom bar):
- **Top-Right**: Enemy nameplate (`Name`, gender, `Lv.`, HP bar, caught Ball icon). Doubles stacks two compact enemy plates top-right.
- **Bottom-Left**: Player nameplate (`Name`, gender, `Lv.`, HP bar + numeric `cur/max`, EXP bar, and 6-slot party Ball status strip underneath). Doubles stacks two compact player plates bottom-left.
- **Bottom-Right**:
  - Quick Poké Ball shortcut pill (`X` + last-used Ball icon) directly above `Battle` (in wild battles) — one click/press throws a ball without navigating Bag!
  - Vertical 4-button stack: **Battle** (crimson), **Pokemon** (emerald), **Bag** (gold), **Run** (blue/slate) with icons and crisp selection brackets.
  - Clicking/pressing **Battle** slides in the 4 move cards on the right (type color, category icon, PP, effectiveness hint, Mega toggle); **Target** highlights targets directly in-world + right-side selector.
- **Transient Message Box**: Only appears at bottom-center while combat text is printing, then hides cleanly so the full clearing breathes.
- **Art Style Gate (Decision Needed)**: Can be rendered either in **crisp high-res Platinum pixel art** on the 342x192 wide 2D canvas, OR as a **native HD Metal UI pass** (smooth rounded cards, crisp vector-scale icons & font matching the BDSP screenshot 1:1) toggleable in Options (`Battle Style: Classic Wide / BDSP`).

---

## Phased Milestones & Verification Gates

Each milestone ends with a headless Metal screenshot suite (`SIM_FX_BDSP_BATTLE=1`, zero regressions on existing `visual_battlehud_*` goldens) and visual review:

| Milestone | Scope | Deliverable & Gate |
|---|---|---|
| **M0: Engine Bridge & Skeleton** | `sim_battle3d.h/.c`, `cgltf.h` + `stb_image.h` vendored in `libntr`, empty Metal `fx_battle3d` pass, `BattleScene3D` toggle in Options `FX` tab | Builds cleanly on macOS/iOS Metal; 0 golden diffs when off |
| **M1: Vertical Slice 3D Arena (`plain_route`)** | Procedural/Blender `plain_route.glb` (grass clearing, cliffs, bushes, pine trees, sky dome) + BDSP toon/fog shader + 1024x1024 PCF shadow map + over-the-shoulder camera | 16:9 Metal screenshot of Route 201 wild battle (Honchkrow vs Bidoof / Starter vs Bidoof) with full 3D clearing & soft shadows |
| **M2: Battler Integration (Shadows + Track A / Track B Slice)** | Alpha-tested silhouette shadow casting for sprites (Track A) + optional skinned `.glb` loader with vertical-slice test models (e.g. Bidoof + Honchkrow/Infernape) | Real ground-projected shadows, zero floating ovals, idle/hit/faint animations working, 60 FPS steady |
| **M3: Edge-Docked BDSP Battle HUD + Quick-Ball** | Corner healthbars (top-right enemy, bottom-left player + party balls), bottom-right vertical 4-button stack + `X` quick-Ball button, transient message box, full mouse/touch + controller | 16:9 Metal screenshots for Singles Action, Move Select (with/without Mega), Doubles Target, and Combat Idle; touch clicks verified |
| **M4: Camera Cinematics & Move Compat Pass** | Smooth idle camera orbit, send-out/attack/capture cuts, `BattleStage_Suppress` verification across move-animation test suite | Full battle scenario suite green; no clipped/black frames on legacy moves |
| **M5: All 8 Biome Arenas + Time-of-Day / Weather** | Remaining 7 biome `.glb` arenas (`forest`, `water_lake`, `mountain_cave`, `snow`, `city`, `indoors_gym`, `distortion_world`) + morning/day/sunset/night & weather lighting presets | Contact sheet across all 8 biomes x Day/Night + Rain/Snow |

---

## Open Decisions Before Starting M0

1. **Battler Visuals**: Start with **Track A (HD-2D animated sprites with real projected 3D shadows & lighting on the 3D clearing — instant 100% Pokédex coverage)**, or go straight to **Track B (skinned 3D `.glb` Pokémon models with 2D fallback)**?
2. **HUD Style on this branch**: Keep **authentic Platinum pixel-art style** rearranged into the BDSP corner layout, or build a **native HD Metal BDSP-style HUD** (rounded cards, smooth font, icons, quick-Ball button)?
3. **3D Asset Source**: Procedurally generated stylized `.glb` arenas in Python/Blender (100% clean-room, script-reproducible in `tools/battle3d/`), or importing external/custom `.glb` environments & Pokémon models you provide?
