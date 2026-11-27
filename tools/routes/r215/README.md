# Route 215 — Flooded Lowland (routes wave 2, Arc 2)

Rain runoff from the Route 214 rift has flooded Route 215's lowland (v3 art): three continuous flood sheets in
Platinum's own animated `sea` water with muddy, grass-fringed shorelines (the stock splash / reflection puddle
behaviour on the flooded tiles), weathered timber boardwalks spanning right across them, solid packed-mud Team
Eclipse truck roads (crisp 1-texel outlined, cleanly stepped edges, dual-tyre grooves, rounded end caps) on the dry
fields running east to the Veilstone gate, a full 3x3 Eclipse supply yard on an outlined mud pad by the north road,
a second yard on an outlined gravel apron at the gate (kept off the road on screen) and a small south-field cluster,
warm work lamps (unlit glass + smooth A3I5 halos, no dithered glow), and a crisp overcast day / dark indigo storm
night lighting set. Contract: `docs/routes_wave2/PLAN.md`.

Chunks MAP_069 / 070 / 071 (matrix row z 18, x 576..671, z 576..607) are edited in place with
`tools/world_art/chunkedit.py`: every stock shape, material, prop and BDHC byte is kept, new geometry is appended.
The west (Route 210, x 576) and east (Veilstone gate, x 671) seam columns are untouched.

| file | what |
|---|---|
| `common.py` | Chunk cells, stock readers (from git `BASE_REV`), tile maps. |
| `inspect_stock.py` | ASCII permissions / BDHC heights / texture usage / events of the stock route. |
| `show.py x0 z0 x1 z1` | Tile classes of a rect (flat ground, grass, blocked, slopes, events). |
| `paths.py` | Walk graph (4-neighbour + one-way ledges); reachability and the shortest Route 210 -> gate path. |
| `textures.py` | Set 078 = stock set 010 + `r215_board`, `r215_ruts`, `r215_rutcap`, `r215_shore`, `r215_crate`, `r215_props`, `r215_padn`, `r215_padg` (all c0 except the board), `r215_glow` (A3I5); PADS (pad shapes). The flood water is the stock `sea`. |
| `build_art.py` | The layout (SHEETS, BOARDWALKS, RUTS, CLUSTERS, SIGNS), flood-sheet contouring, road beds + caps, pads, chunk edits, puddle behaviour + prop blocking, lighting_set_006; every check. `--write` refuses on a FAIL. |
| `render.py` | NumPy software previews (top view, field-camera views) decoded from the built NSBMD + set (A3I5 alpha blended). |
| `verify_r215.py` | Headless in-game run (Linux/macOS SDL3 build): viewpoints day/night, the three BG_EVENTs, the boardwalk walk, the Route 210 seam and the Veilstone gate warp. |

```
~/.venvs/desmume/bin/python tools/routes/r215/build_art.py           # dry run + checks
~/.venvs/desmume/bin/python tools/routes/r215/build_art.py --write   # chunks, set 078, lighting_set_006
~/.venvs/desmume/bin/python tools/routes/r215/render.py /tmp/r215 --top --views
python3 tools/routes/r215/verify_r215.py build_linux /tmp/r215/game --night
python3 tools/dazzling/test/static_checks.py
```

## Layout

- Flood sheets (stock `sea`, 1 tile per repeat): each outline is the zero contour of a smooth field (signed distance
  to the sheet's dry border, inset 0.42 tiles, wobbled by low-frequency noise), traced by marching squares on a
  quarter-tile grid, Chaikin-smoothed, simplified, ear-clipped and edge-flipped (no slivers); a mitred shoreline
  strip (`r215_shore`: silty shallows, wet mud lip, stock-green grass overhang) follows the whole contour. Walkable
  tiles whose centre is under water get `TILE_BEHAVIOR_PUDDLE` 0x16 (decks and props excluded).
  - west: x 577..589 z 594..601 (MAP_069, the Route 210 entry; links under two tree bases at x 582..583);
  - lowland: x 594..606 z 589..595 (MAP_069, around the long boardwalk);
  - east: x 616..621 z 585..595 (MAP_070).
- Decal stack over the ground: pads +0.012, road beds +0.020, (redrawn tall grass +0.026), stock `allpeak` decals
  +0.03, water +0.036, contact shadows +0.037, lamp pools +0.039, shoreline +0.041, boardwalk decks +0.06 (the BDHC
  floor is unchanged).
- Boardwalks: x 577..587 z 598..599, x 595..606 z 591..592, x 616..621 z 592..593.
- Roads (dry ground only, never over tall grass, checked): north field z 585..586 from the yard's turnaround pad
  (cap at x 630.4) east to the tall-grass patch (cap at x 646); south field z 590..591 from the grass patch (cap at
  x 649) -> x 644..645 down to the lane -> z 597..598 to the gate stairs (cap at x 659), filleted corners; gate
  approach z 597..598 from the foot of the stairs (cap at x 660) onto the gravel apron (cap at x 671). The strip v
  runs a whole number of 4-tile texture repeats, so both caps seam onto texture row 0.
- Pads (`textures.PADS`, one texel-aligned quad each): north mud pad x 629.6..633 z 582..587.3 (the yard + the
  road's turnaround); gate gravel apron x 664.6..671.75 z 597..601 (L-shaped round the yard), covering the stock
  speckled `blueglayp` edge of the gate's gravel with a clean outline + mud rim.
- Staging (soft contact shadows + a warm lamp in each): the north yard x 630..632 z 582..584 is a full 3x3 supply yard
  on its pad (back: two-high slate stack, Eclipse warning banner post + two drums, slate + wooden stack; middle:
  tripod work lamp, olive tarp draped over a stack on a pallet; front: pallet of wooden crates, three drums); the
  gate yard x 665..667 z 599..601 sits south of the gate road, low props in front and tall ones at the back so no
  prop reaches the road bed on screen (`no prop sits on the road bed on screen` check: every solid vertex slid along
  the field camera, z - height / tan 59.05 deg) (BG_EVENT `Route215_EclipseStaging` at 666,599, read from 666,598
  facing south); the south-field cluster x 655..656 z 592..593 (BG_EVENT `Route215_EclipseCrates` at 655,592) has a
  mast lamp.
- Showcase viewpoints (x, z, facing): north yard (633, 585, west); flooded boardwalk (600, 592, east); Veilstone gate
  yard (663, 598, east).
- Drainage sign post at 594,590 (blocked; BG_EVENT `Route215_DrainageSign`, read from 595,590 facing west).
- Weather: `OVERWORLD_WEATHER_CLOUDY`. The stock rain's OAM drops only ever drew one or two isolated streaks at the
  bottom of the top screen in this port (the "stray white diagonal lines"); the route's rain is the SDL3 weather
  pass (kind 8 rain mist, wired to MAP_HEADER_ROUTE_215 by map id in `src/fx_weather.c` on routes-shaders).
