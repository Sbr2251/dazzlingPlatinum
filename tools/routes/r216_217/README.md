# Routes 216-217: Teo's Memorial Ridge & Indra's Snowy Camp

Reproducible pipeline (inputs read from git: stock chunks/lighting at `406c75f6a8`, stock set 014 at HEAD):

    ~/.venvs/desmume/bin/python tools/routes/r216_217/dump_stock.py 110     # stock permissions / heights / props
    ~/.venvs/desmume/bin/python tools/routes/r216_217/textures.py --preview DIR
    ~/.venvs/desmume/bin/python tools/routes/r216_217/build_art.py --preview DIR   # all checks + day/night renders
    ~/.venvs/desmume/bin/python tools/routes/r216_217/build_art.py --write   # map_data_109/110, set 080, lighting_set_008
    python3 tools/routes/r216_217/story.py                                    # BG events, scripts, text (idempotent)
    python3 tools/dazzling/test/static_checks.py

`--preview DIR` writes `day_*.png` / `night_*.png` at field-camera distance (`CAMERA_TYPE_DEFAULT` pitch, distance
and FOV) and as close-ups, with a player-sized stand-in sprite (1 x 1.56 screen tiles) on the showcase tile, so the
landmark heights can be judged against the player. Translucent A3I5 texels are blended in a second pass.

v2 art (critic re-review):

- Teo's Memorial: a 2.78-tile carved granite monolith on a two-step pedestal (leaning back 25 degrees so it rises
  ~2x the player on the DS camera), outlined pixel-art face with the emblem and "TEO" plaque, crisp snow cap with a
  drip lip, bold deep-violet knotted scarf with two tails on the east flank, large evergreen & winter-blossom wreath,
  ~1.4-tile stone vigil lantern at (316.2, 401.3) with warm unlit glass + soft A3I5 amber bloom and light pool. The
  v1 slate paving, retaining wall and cliff cut are gone: stock snow ground and cliff stay whole, dithered c0 snow
  drifts creep over the steps, soft A3I5 contact shadows sit under the pedestal and lantern.
- Indra's camp: deep-violet A-frame tent with dark outlines, heaped ridge snow, pale-silver Eclipse emblem on both
  slopes, open shadowed doorway with tied-back flaps facing south, staked guy ropes; bright amber crate lantern and the
  electric-violet scanner lid (raised on two stacked crates so it shows above the player's head), both with A3I5
  blooms and ground pools (no ordered-dither checkerboards); dithered packed-snow clearing rims and contact shadows.
- `lighting_set_008`: brighter blue-white day key light with lower emission (more contrast on the violet canvas and
  carved stone), clear moonlit indigo night.

Showcase (absolute tiles):

| Landmark | Chunk | Blocked | Stand (x, z, facing) | BG event |
|---|---|---|---|---|
| Teo's Memorial close-up (Route 216 cliff ledge, faces south to Mt. Coronet) | map_data_110 | (316..318, 401) | (317, 402, north) | `Route216_TeoMemorial` at (317, 401) |
| Teo's Memorial approach along the Route 216 ledge | map_data_110 | | (315, 404, north) | |
| Indra's camp: tent, crate lantern, scanner case (Route 217 NE snowfield) | map_data_109 | (313..316, 360..362), (311..312, 360) | (312, 361, north) | `Route217_IndraCamp` at (312, 360) and (311, 360) |

Chunks 106, 107, 108, 111, 112 are untouched (checked byte-identical); BDHC and props of 109/110 are stock.
