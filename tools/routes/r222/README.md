# Route 222 — Violet-Lit Coast (routes-wave2, `routes/r222`)

Arc 3: the coastal road between Valor Lakefront and Sunyshore, cast in the violet glow of the Route 223 rift. Plan:
`docs/routes_wave2/PLAN.md` (section 3.4). Chunks `map_data_149/150/151` (x 736..831, z 768..799), area data
`area_data_083` (set `map_texture_set_081`, lighting `lighting_set_009`).

All tools read their stock inputs from git at the routes-wave2 contract commit (`BASE_REV = 406c75f6a8`), so reruns
are idempotent and never feed back.

| file | what |
|---|---|
| `textures.py` | `map_texture_set_081` = stock set 018 + `r222_lamp` (64x32), `r222_tide` (64x64), `r222_warning` (32x32): NumPy pixel art, 16-colour BGR555 palettes, 4x4 Bayer dither, 16 texels per tile, `c0 = 1`. Round trip, stock unchanged, set parse -> rebuild identical, VRAM. |
| `build_art.py` | Surgical chunk edit (`tools/world_art/chunkedit.py`): every stock shape and material byte-identical, new geometry appended (lamps, violet lamps with halo + glow pool, caution tape, beacon boxes, tide-line foam / scatter / debris draped on the stock terrain, rift crystals on boulders and sea rocks). BDHC and props stock; permissions stock + 3 lamp verge tiles. Writes the chunks, set 081 and `lighting_set_009.json`. `--preview DIR` renders field-camera views (day / dusk / night) and top views. |
| `events.py` | Appends the stranded Psyduck / Piplup / Prinplup, the `Route222_BlackoutLamp` and `Route222_VioletLamp` signs, their scripts and text (stock entries keep their indices). |
| `render.py` | NumPy rasteriser for the previews (real set-081 textures, approximate GX lighting from a lighting block). |
| `verify_route222.py` | Headless in-game tour on a build of the base commit with this tree's Route 222 archives overlaid (no rebuild): viewpoints by day / night, every new interaction, the promenade walk, a lamp verge block, the Valor seam and the Sunyshore gate warp. |

```
~/.venvs/desmume/bin/python tools/routes/r222/build_art.py --preview /tmp/r222/preview
~/.venvs/desmume/bin/python tools/routes/r222/build_art.py --write
~/.venvs/desmume/bin/python tools/routes/r222/events.py --write
python3 tools/dazzling/test/static_checks.py
python3 tools/routes/r222/verify_route222.py <base build_linux> /tmp/r222/game --night
```

## Placement

- Blacked-out lamps (blocked tiles, north of or beside the walkways so they never hide a sprite): 149 sea-cliff rim
  (739,794) (747,794) (753,794), dirt road verge (756,780) (756,785), island rim (766,774); 150 (772,774) (787,775)
  (792,775) (797,775); 151 (803,775) (809,775) (813,777) (813,781) (815,784). Violet sparking lamps by the Sunyshore
  gate: (819,784) (820,790) (820,793).
- Stranded Water Pokemon (tide-line sand, facing east): Psyduck (791,790), Piplup (803,791), Prinplup (813,795).
- Signs: `Route222_BlackoutLamp` on (792,775), read from (792,776) facing north; `Route222_VioletLamp` on (820,790),
  read from (821,790) facing west.

## Not done here

- The SDL3 weather kind 7 (violet rift glow) belongs to the routes-shaders workstream (`src/fx_weather.c`).
- The lamps are terrain, so they are dark in every story state.
