# Lake Verity redesign

Branch `lake-verity-redesign`. Lake Verity keeps its stock shape (the octagonal lake, the forest ring, the SW
tall-grass shore, the SE path from the Lakefront, the Rowan / Galactic scene on the east shore). The Verity
Cavern hut on the island becomes a three-floor castle with an exterior and an interior:

- **Exterior (Lake Verity map, matrix 102):** a drawbridge from the east shore, a courtyard, an **open
  staircase on the castle's west side where the camera tilts down as you climb**, a roof terrace on floor 1, and
  the roof deck on top of the keep with a **launchpad and a Distortion World portal**.
- **Interior (separate indoor maps, reached through doors):** 1F hall with Mesprit's chamber (replaces
  Verity Cavern), 2F, 3F, and a hatch up to the roof deck.

Route through: bridge -> courtyard -> 1F door (Mesprit) ... open staircase -> F1 terrace -> 2F door -> 2F -> 3F ->
roof hatch -> launchpad / portal.

Mock renders and the art reference are outside the repo in `~/Documents/Lake Verity Update/`
(`LV_plan_after.png`, `LV_view_castle.png`, `ArtRef_Iridium_sky_islands.png`).

## Layout contract

`tools/lake_verity/layout.py` is the single source of truth for tile positions, collision and walk heights.
`python3 tools/lake_verity/layout.py --ascii` prints it. Anything that places geometry, collision, height or
events reads it; if a change is needed, change `layout.py` first.

## Visual target

Push past stock Gen 4 toward Gen 5 / Pokemon Iridium quality (see `ArtRef_Iridium_sky_islands.png`):

- Painterly, high-detail textures: grass with blade/clover texture and light variation, cliff and island
  sides with layered dirt and hanging grass lips, dressed stone with mortar and moss, weathered wooden planks.
- Real 3D silhouettes: round towers with conical roofs, crenellations, arched door frames, banners, torches /
  candles on pillars, iron chains on the drawbridge, lily pads and reeds at the island edge, a glowing
  launchpad ring and a swirling portal.
- Baked lighting in vertex colours (map materials have lighting off): ambient occlusion in corners and under
  eaves, soft contact shadows, warm torch glow, water edge highlights.
- Animated textures where the engine supports them: water (fldtanime `*_sea` pattern), portal swirl, torch flame.

## DS budgets (keep to these unless the pipeline doc says otherwise)

- Per 32x32 chunk model: aim at or below the stock chunk's polygon count and size (the pipeline agent measures
  these and writes them to `docs/lake_verity_redesign/pipeline.md`). Prefer quads. The castle may be a map
  prop (build_model) instead of terrain if that fits the budgets better.
- Textures: power-of-two sizes, 8..128 px per side; mostly 16-colour (4bpp) or 4-colour; 4x4-compressed or
  A3I5 / A5I3 for soft-alpha effects (portal glow, torch halo). The whole area's texture set must fit the
  texture VRAM the field gives map textures (measured in pipeline.md).
- Field camera for this map is `CAMERA_TYPE_ZOOMED_IN`; design walkable surfaces to face south/east (toward the
  camera) so nothing important hides behind the keep.

## Work split

| area | owner | outputs |
|---|---|---|
| Pipeline | pipeline agent | `tools/lake_verity/` Nitro writers (NSBMD, NSBTX, BDHC, map_data), stock-chunk dumps, `pipeline.md` |
| Art | art agent | Blender scene + scripts in `~/Documents/Lake Verity Update/`; exported meshes/textures in `tools/lake_verity/assets/` |
| Gameplay | gameplay agent | camera-tilt system, interior map headers + warps, events, scripts, `gameplay.md` |

### Intermediate mesh format (art -> pipeline)

`tools/lake_verity/assets/<chunk_or_prop>.mesh.json`:

```json
{
  "name": "chunk_541", "origin_tile": [32, 32],
  "materials": [{"name": "lv_grass", "texture": "lv_grass", "alpha": 31, "polygon_attr": {"cull": "back"}}],
  "meshes": [{"material": "lv_grass",
              "positions": [[x, h, z], ...], "uvs": [[u, v], ...], "colors": [[r, g, b], ...],
              "tris": [[i, j, k], ...], "quads": [[i, j, k, l], ...]}]
}
```

Positions are in tiles in absolute matrix coordinates (x east, h up, z south); the pipeline converts to chunk-local
world units. UVs are in texels / texture size (0..1 repeats allowed). Colours are 0..255 baked vertex colours.
Textures: `tools/lake_verity/assets/textures/<name>.png` (indexed PNG, colour 0 transparent when used) plus
`<name>.json` with `{"format": "pltt16" | "pltt4" | "a3i5" | "a5i3" | "tex4x4" | "direct", "repeat": [s, t]}`.

## Build and test

Do not build locally (see CLAUDE.md). Generated binaries are checked in, like `tools/coronet_lava`. Verify with
the round-trip / preview checks in `pipeline.md`; the user builds and tests on the VM.
