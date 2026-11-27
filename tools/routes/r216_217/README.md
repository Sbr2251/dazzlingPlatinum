# Routes 216-217: Teo's Memorial Ridge & Indra's Snowy Camp

Reproducible pipeline (inputs read from git: stock chunks/lighting at `406c75f6a8`, stock set 014 at HEAD):

    ~/.venvs/desmume/bin/python tools/routes/r216_217/dump_stock.py 110     # stock permissions / heights / props
    ~/.venvs/desmume/bin/python tools/routes/r216_217/textures.py --preview DIR
    ~/.venvs/desmume/bin/python tools/routes/r216_217/build_art.py --preview DIR   # all checks + day/night renders
    ~/.venvs/desmume/bin/python tools/routes/r216_217/build_art.py --write   # map_data_109/110, set 080, lighting_set_008
    python3 tools/routes/r216_217/story.py                                    # BG events, scripts, text (idempotent)
    python3 tools/routes/verify_all_routes.py build_linux OUT --only r216 --night --spots-json SPOTS   # in-game (integ tool)
    python3 tools/dazzling/test/static_checks.py

`--preview DIR` writes `day_*.png` / `night_*.png` at field-camera distance (`CAMERA_TYPE_DEFAULT` pitch, distance
and FOV) and as close-ups, with a player-sized stand-in sprite (1 x 1.56 screen tiles) on the showcase tile, so the
landmark heights can be judged against the player. Translucent A3I5 texels are blended in a second pass.

v3 polish (critic 5.5 -> 8 pass):

- Weather: `route_216/header.json` and `route_217/header.json` use `OVERWORLD_WEATHER_SNOWING` (gentle falling flakes,
  as in Snowpoint City). `OVERWORLD_WEATHER_ROUTE_216` resolves to `HEAVY_SNOW` on many days (Jan 2 included) and Route
  217 was `BLIZZARD`; both draw the stock full-screen white fog sheet that washed out the outlines and flattened night.
- `lighting_set_008`: night is a deep moonlit alpine indigo (key light (8, 10, 19), ambient (6, 7, 12), emission (4, 5,
  9)) with a darker twilight ramp; day is unchanged (crisp blue-white), so noon vs 22:00 is dramatic and the unlit
  amber lanterns / campfire and the violet scanner glow read as beacons.
- Teo's Memorial: carved alpine stele instead of the v2 box: wide two-tier stepped plinth with chamfered corners and
  a bevelled moulded collar, a tapered shaft with chamfered front edges (leaning back 22 degrees for the DS camera), a
  projecting snow-lipped cornice and a peaked stone cap (pyramidion) with a carved diamond pediment, snow-laden
  flanks and a sculpted snow crest (2.6 tiles tall). The face carries a recessed dark-slate memorial tablet inside a
  raised carved frame with delicate etched inscription lines (no block letters) under a small carved peak-and-star
  emblem. The violet scarf drapes diagonally over the shoulders to a knot on the east shoulder; wreath, bouquet,
  vigil lantern, snow drifts nestled against the steps and corner heaps stay.
- Indra's camp: lived-in expedition site round the tent: stacked Eclipse supply crates with a rope coil (310, 360),
  lantern crate + journal and the raised scanner case (311..312, 360), a stone-ringed campfire with a glowing ember
  bed, crossed logs, A3I5 amber bloom and ground pool (311, 361), a split-log bench on stumps (309, 361), a rolled
  violet sleeping bag at the door, the Eclipse survey pole with a pennant and two plank trail-marker arrows on a snow
  cairn (308, 360), the scanner's faint violet beam onto the snow and a ground trace running south-south-west toward
  Mt. Coronet, trampled packed-snow paths and boot prints.

Showcase (absolute tiles):

| Landmark | Chunk | Blocked | Showcase (x, z, facing) | BG event (read from) |
|---|---|---|---|---|
| Teo's Memorial close-up (Route 216 cliff ledge) | map_data_110 | (316..318, 401) | (319, 402, west) | `Route216_TeoMemorial` at (317, 401), from (317, 402) north |
| Teo's Memorial approach along the Route 216 ledge | map_data_110 | | (318, 404, north) | |
| Indra's camp (Route 217 NE snowfield) | map_data_109 | (313..316, 360..362), (310..312, 360), (311, 361), (309, 361), (308, 360) | (310, 363, north) | `Route217_IndraCamp` at the scanner (312, 360) and the campfire (311, 361), from (312, 361) / (311, 362) north |

All three showcase tiles are outside every trainer's sight line (`verify_all_routes.py --list-spots`: 0 warnings).
Chunks 106, 107, 108, 111, 112 are untouched (checked byte-identical); BDHC and props of 109/110 are stock.

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
