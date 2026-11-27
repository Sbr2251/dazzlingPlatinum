# Routes 206-207 - Eclipse Supply Road (routes wave 2, `routes/r206-207`)

Arc 3: Team Eclipse's supply road into Mt. Coronet. Contract: `docs/routes_wave2/PLAN.md`. Chunks `MAP_025..030`
(x 288..351, z 576..735), `area_data_081` -> `map_texture_set_079` (stock base 007) + `lighting_set_007`.

All inputs are read from git at `common.BASE_REV` (406c75f6a8: stock chunks, stock set 007, lighting_set_000), so
every tool is idempotent: rerunning `--write` gives byte-identical files.

| file | what |
|---|---|
| `common.py` | chunk table, paths, budgets (`0xF000` model, `0x9000` BDHC, 160 KB VRAM). |
| `stock_report.py` | stock sizes/materials/props and an ASCII map of permissions, events and BDHC heights. |
| `layout.py` | the tile contract: rut centreline, every prop (kind, tile), the tiles they block, KEEP_OPEN tiles (incl. the yard's cluster gaps), both BG events, showcase viewpoints. |
| `textures.py` | the kit appended to set 007 -> `map_texture_set_079.nsbtx` (append-only, round trip, VRAM): five hand-drawn 16-colour textures at true 16 texels/tile (`ec_ruts`, `ec_crate`, `ec_banner`, `ec_barricade`, `ec_light`; no dithering, no noise) and `ec_glow`, an a5i3 per-texel-alpha texture for soft light pools, shard glow and contact shadows. |
| `build_art.py` | surgical chunk edits (tools/world_art/chunkedit.py: stock shapes/materials/props/BDHC byte for byte, new `ec_*` materials appended), permissions (bit 15 on the prop tiles only), lighting_set_007, every check, previews. |
| `render.py` | NumPy rasteriser (field camera / top view) for previews, with the real set textures (a3i5/a5i3 texel alpha included) and map props; also renders the stock ground mask the ruts are clipped to. |
| `story.py` | the two BG events + scripts + text (append-only). |
| `verify_ingame.py` | headless in-game test on a Linux/macOS SDL3 build (viewpoints day/night, both BG events, plaza lane into the south gate, supply road into Mt. Coronet, blocked props). |

```
~/.venvs/desmume/bin/python tools/routes/r206_207/build_art.py --preview /tmp/r206/preview   # dry run + renders
~/.venvs/desmume/bin/python tools/routes/r206_207/build_art.py --write
python3 tools/routes/r206_207/story.py --write
python3 tools/dazzling/test/static_checks.py
python3 tools/routes/r206_207/verify_ingame.py build_linux /tmp/r206/ingame --night
```

## What changed

v2 art rework (critic re-review):

* **Textures at true density, no dithering.** The DS samples without mipmaps, so a 32-texel crate face on a 7-pixel
  crate turned to purple-black mush. Every prop cell is now hand-drawn at the size it shows on screen: 12x12 / 8x8 crate
  sides and lids, a 12x24 shard-containment frame (steel frame, faceted violet crystals, hazard band), a 15x10 canister
  case, 16x3 pallet and steel strips, a 16x16 tarp, 16x5 CLOSED board, 8x12 cone. Bold dark outlines, flat 2-3 tone
  cel shading, warm wood instead of dark slate, after Solaceon's excavation props.
* **Light pools without checkerboards.** The Bayer-dithered pool/glow decals are gone. `ec_glow` (a5i3) carries a smooth
  radial alpha: warm amber pools under the lamps, violet glow in front of the frames, and one-quad soft contact shadows
  under every prop (palettes `ec_glow_amb_pl` / `ec_glow_vio_pl` / `ec_glow_shd_pl`).
* **Ruts.** `ec_ruts` is one sculpted wheel track (two-tone tread floor, shadowed west wall, lit east wall, a thin broken
  dust rim) plus a tapered fade-out piece. The two tracks are built from quarter-tile segments that are kept only where
  the stock ground is bare dirt/sand (rendered ground mask, no green), walkable and at road height: they never touch
  grass, ledges or cliffs. Each run feathers out over its last 1.5 tiles (taper + translucent steps 24/16/9) where the
  ground turns to grass or the cave mouth; runs under 2.5 tiles are dropped (no stubs).
* **Staging Yard clusters.** The ruler-straight row of 10 racks is three clusters with natural gaps (A x 321..324, gap,
  B x 327..330, gap, C x 333..337), some pieces pulled forward onto z 711: crate stacks on wooden pallets, tarp-covered
  stacks, three 3D shard-containment frames (1.2 / 1.45 / 1.8 tiles, slight yaws, a faceted shard through the cap),
  banners, lamps, the manifest crate. The roadside outpost (x 306..307 / 314..318) is broken up the same way.
* **Route 206 lane closure.** Both plaza shoulders (x 299..300, 305..306, z 689..694) carry a staggered closure:
  alternating barricades, a cone taper, a parked Eclipse equipment crate on a pallet, banner posts, work lamps and the
  ROAD CLOSED sign; the 4-wide sand lane x 301..304 stays clear (checked). The Cycling Road south closure (x 299..300,
  z 674..679) gets staggered barricades, an equipment crate, a lamp and a banner.
* **lighting_set_007 night** nudged towards a clean deep indigo-green (the teal night streaks are the water-reflection
  pass, fixed separately by routes-shaders).

Showcase viewpoints (player tile, facing): Coronet Staging Yard (329, 713, north); supply ruts (310, 713, east);
Route 206 lane closure (302, 695, north).

v1:

* **Route 207 supply road** (MAP_025/026 + the junction rows of MAP_027): two-tile `ec_ruts` decal lane from the Route
  206 junction (x 304.5, z 699) south, a radius-5 curve at (309.5, 707.5), then east along z 711.5..713.5 into Mt.
  Coronet's south cave mouth (warp 341,712).
* **Mt. Coronet Staging Yard** (MAP_026, north verge z 710, x 322..337): crate stacks on steel pallets, four violet
  shard-containment racks (unlit, baked violet glow + translucent glow pools), three tripod work lamps (unlit heads,
  translucent amber light pools), the manifest crate (BG event 333,710), twin Eclipse banners flanking the road at x 334
  (z 710 / 715) and a steel safety fence on the cliff edge x 336..340, z 715.
* **Roadside outpost** (MAP_025): banner / crates / lamp at x 307, z 704..707 where the ruts turn; crates, a canister
  case, a lamp and a rack on the north verge x 314..318, z 710 (honey tree 311,709 and its tile 311,710 untouched).
* **Route 206 partial Cycling Road closure**: barricades narrow the south-gate plaza (MAP_027) to the 4-wide sand lane
  x 301..304, with crates, cones, a lamp and the ROAD CLOSED sign (BG event 305,693); steel fence + cone on the east
  underpass path (x 309, z 692..693); the Cycling Road west lane is coned off behind barricades at the south end
  (x 299..300, z 674..679) and on the north ramp (x 299..300, z 588..591) - the deck stays >= 4 lanes wide everywhere;
  an Eclipse supply cache under the road between the split deck lanes (MAP_028: rack 302,649, crates 303,649, lamp
  303,653; the Burn Heal at 302,652 stays reachable). MAP_029 is unchanged (2.2 KB of model room).
* **lighting_set_007**: hazy dusty-amber day, rust sunset, violet-indigo dusk and a stark indigo night.

Only bit 15 of 57 permission tiles changes; no warp, object, hidden item, trainer or coord-event tile is blocked, and
every stock walkable region stays connected (checked by `build_art.py`, confirmed in-game by `verify_ingame.py`).
