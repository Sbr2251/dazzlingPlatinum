# Battle stage asset tool

Generates `res/prebuilt/battle/graphic/battle_stage.narc`, the 3D arenas that
`src/battle/battle_stage.c` draws in place of the classic BG3 backdrop and platform
OBJs. The file format is `include/battle/battle_stage_format.h`; the design is in
`docs/living_battle_stage/stage_format.md`. The emulator critic is in `emu/`
(see `emu/README.md`).

## Regenerating the NARC

```sh
python3 tools/battle_stage/build_stage.py            # writes the checked-in NARC
~/.venvs/desmume/bin/python tools/battle_stage/preview.py   # renders /tmp/battle_stage_preview
flock /tmp/dazzling_build.lock make release
```

`build_stage.py` only needs the standard library. It reads the stock
`pl_batt_bg.narc` / `pl_batt_obj.narc`, and the output is the same bytes on every run,
so commit the NARC whenever the tool changes and check `git diff --stat` shows it
changed only when you expected it to.

`preview.py` needs numpy and PIL. It software-renders the pieces with the renderer's
light, fog and sway, and prints per background, terrain, time of day and raster:

- `mean`, `max`: the home pose vs the classic scene (BG3 + platform OBJs with the
  palettes of the same `ov16_0223EC04` column), rows 0..143 (the text box covers the
  rest), per channel on the 0..255 scale;
- `differ`: pixels that differ in rows 0..143;
- `holes`: pixels nothing was drawn to in view 0 (rows 0..143) and debug views 1..3.

Holes must be 0 everywhere. The day mean should be about 0 (the E4 rooms keep a few
pixels of disc rim shading; the snow, cave and Distortion World haze is meant to
show); twilight, night and caves show a small tint.

| flag | what |
|---|---|
| `--bg N` | background (default 0, `BACKGROUND_PLAIN`) |
| `--terrain N` | platform piece (default: the one the background usually comes with) |
| `--tod 0/1/2` | day, twilight or night only (default: all three) |
| `--frame N` | sway `SCROLL` meshes to arena draw N (30 per second; default: no sway) |
| `--raster desmume/hardware/both` | `desmume` (default): the soft rasterizer of DeSmuME 0.9.12, which py-desmume and so the critic use (1/16 pixel positions, fog depth one more than the DS); `hardware`: whole-pixel vertices and the DS fog depth |
| `--all` | every background with its usual terrain at the three times of day, and every terrain on `BACKGROUND_PLAIN` at day (about 110 s with `--raster both`) |
| `--out DIR` | where the PNGs go (default `/tmp/battle_stage_preview`) |

One background writes `sheet_bgNN_tT.png` (classic, home and diff above views 1..3)
and `home_bgNN_tT.png`. `--all` writes `sheet_bgNN.png` (classic, home and diff per
time of day, then views 1..3), `contact_home_{day,twilight,night}.png`,
`contact_view{1,2,3}.png` and `contact_terrains.png`, then prints the worst line per
time of day and raster. In the diff images grey is equal, red differs (brighter is a
larger difference) and magenta is a hole.

Then run the critic on the ROM:

```sh
SDL_VIDEODRIVER=dummy ~/.venvs/desmume39/bin/python tools/battle_stage/emu/critic.py \
    out/dazzlingPlatinum.nds /tmp/stage_critic --scenario stage_ab debug_views
```

## Files

| file | what |
|---|---|
| `build_stage.py` | entry point: builds every piece, checks the per-battle budget over every backdrop x terrain pair and writes the NARC. Prints each piece's size, meshes, polygons and fog; `--quiet` prints only the totals |
| `arena.py` | the geometry: home camera, the backdrop piece of each background (ground or floor, panorama or walls) and the platform discs of each terrain, with every texture coordinate taken through the home camera, normals, and the water `SCROLL`. `python3 arena.py` prints the mesh list and budgets |
| `atmosphere.py` | light and fog per background class: the three lighting columns (material from "up" and "away" colour targets), the fog table over the remapped depth, and the DS lighting math the preview uses |
| `stage_format.py` | reads and writes pieces; mirrors `battle_stage_format.h` (v2) |
| `fx.py` | bit-exact NitroSDK camera math (`MTX_PerspectiveW`, `MTX_LookAt`, `VEC_*`, `FX_*`), the renderer's debug-view cameras, the geometry engine's vertex-to-screen transform and the remapped 15-bit fog depth |
| `classic.py` | the classic scene the arena must match: the BG3 backdrop image and palettes, the platform OBJ art, and a composite of the home screen |
| `nitro.py` | NARC read/write, LZ77, and NCLR/NCGR/NSCR/NCER decoding |
| `preview.py` | software renderer (light, fog, sway) for the four views, the home-vs-classic diff and hole check, contact sheets |

## What is generated

47 members: the 23 backdrop pieces (`BACKGROUND_*` order), then the 24 platform
pieces (`TERRAIN_*` order). Every piece is real; a battle draws its background's
backdrop piece with its terrain's platform piece.

- Backdrop piece: textures A (256x128) and B (256x32) of the background's BG3 image,
  8bpp, 20..23 meshes and 382..472 polygons, and the atmosphere (three lighting
  columns and the fog table).
- Platform piece: one 4bpp texture per platform (player 256x32, enemy 128x64) from the
  terrain's platform OBJ art, 17..21 meshes. `TERRAIN_GIRATINA` has only the player
  platform (the classic scene has no enemy platform there).
- Per battle at most 48 KB of textures (limit 64 KB), 44 meshes (both pieces), 4
  textures and about 630 polygons.
- Every mesh is `LIT` and `FOG`. The ground bands of `BACKGROUND_WATER` from 4 rows
  below the base row are `SCROLL`, amplitude (3, 1) texels, period 105 arena draws
  (3.5 s at 30 draws per second).

## How the home pose matches

Every vertex the home camera can see is placed so it projects into
[x, x + `VERTEX_WINDOW`) x [y, y + `VERTEX_WINDOW`) for a whole pixel (x, y), with
`VERTEX_WINDOW` = 1/32, checked with `fx.py`'s integer transform. Its texture
coordinate is (x + `HALF_PIXEL`, y + `HALF_PIXEL`) minus the texture's origin. The DS
drops the fraction, and DeSmuME rounds positions to 1/16 pixel, so both see the vertex
exactly on (x, y). Close to the camera one fx16 step moves a vertex more than 1/32
pixel, so `Placer.exact` searches the fx16 lattice around the ideal point.

Every polygon side the home view sees is also a vertical pixel column (or a whole
pixel row). DeSmuME starts each span with the attributes of the exact edge point and
spreads them over the pixels from ceil(left) to ceil(right), so on a slanted side, or
a vertex even 1/16 pixel right of x, the texels shift one pixel right. That is why
every disc row uses the same columns, making the disc a trapezoid whose corners are
transparent, and why the side band's outline sits where the disc covers it at home.

The DS interpolates texture coordinates with perspective correction, so they only stay
screen-linear where w is constant. The camera has no yaw or roll, so w is constant
along every screen row of the ground, the platform discs and the front of the
panorama, and columns can be wide (32 px). Down a column the error of a band h rows
tall and d rows below the horizon is about h * h / (4 * d) pixels, so band heights
grow with d to keep it under `BAND_ERROR_PX` (0.25). That replaces the "about 16 px
triangles" rule of thumb in the design note and keeps the arena near 500 polygons.

Where two surfaces meet at a pixel row, both sample the same texel: the ground and
the panorama meet at row 57 and both use texture A there; texture A (rows 0..127) and
B (rows 127..158) overlap by row 127, which is where the ground switches from one to
the other. So the result doesn't depend on which polygon the rasterizer gives that row.

## Arena layout

- Camera at (0, 4, 14) looking down -z, fovy 40 degrees, horizon on row 20, target
  midway between the platform depths, near 1, far 128, vertexScale 8. The same home
  camera for every background.
- Each background has a base row (`BACKGROUND_BASE_ROW`), the screen row where its
  ground or floor meets its panorama or back wall, and a kind:
  - outdoor (plain, water, city, forest, mountain, snow), cave (caves 1..3) and void
    (Distortion World): the ground (y = 0) from the base row down to row 240 (below the
    screen, for view 3) and sideways well past the screen edges, plus a panorama, a
    flat wall standing on the base row's ground line across the home view that bends
    toward the camera past the screen edges as a 30-unit radius arc;
  - room (indoors 1..3, the Elite Four and Champion rooms, the Frontier facilities): a
    floor plus a box of walls, the back wall on the base row's floor line and a
    straight side wall on each side where the back wall meets the home frustum. The
    side walls continue the back wall's texture round the corner.
- The panorama or back wall goes up to home row -64. Rows 0..base are exact; above row
  0 texture A's t clamps to the top sky row.
- Textures A and B are 8bpp BG palette indices with REPEAT_S | FLIP_S, which is what
  the mirrored 512-wide BG3 map looks like at any X scroll. B also mirrors in T, so the
  ground past row 158 repeats rows 158..127 instead of the black rows below the art.
- Platforms: discs 0.1 above the ground, textured with the platform OBJ art (only the
  ellipse is opaque), with a side band along the front half of the art's outline down
  to just under the ground. The player art is only the top half of its ellipse (the
  text box hides the rest), so its texture mirrors at sprite row 16 (FLIP_T) and the
  disc is a whole ellipse in the debug views.

## Light and fog

Light 0 is white, from the same direction for every background (down and away from the
camera in equal parts, a little from the left), so the ground and the panorama meet at
the same light level. Each lighting column's material is solved from two colour
targets: a surface facing up (or the camera), and one facing away from the light. A
target of 31 saturates from half the "up" level, so at day every up- or camera-facing
surface shows the art unchanged and the shading only shows on disc sides, the arc and
the side walls. The columns are day, twilight and night, picked like the classic
palettes (`ov16_0223EC04`: the time of day for backgrounds 0..5, else day).

| class | up (day / twilight / night) | away | fog colour | fog ramp |
|---|---|---|---|---|
| outdoor | 31,31,31 / 31,30,28 / 28,29,31 | 24,24,24 / 24,21,19 / 17,18,23 | 27,29,31 / 26,18,16 / 2,3,8 | starts past the farthest home-view point, 24 at 60 units, max 32 |
| snow | as outdoor | 24,25,26 at day, else as outdoor | 30,31,31 / 28,24,24 / 8,10,16 | 0 to 16 units, 10 at 30, max 24 |
| cave | 30,30,31 | 18,18,22 | 2,2,5 | 0 to 10 units, 20 at 30, max 36 |
| void | 29,28,31 | 20,18,28 | 6,2,10 | 0 to 12 units, 20 at 30, max 28 |
| room | 31,31,31 | 24,24,24, tinted in the E4 and Champion rooms | none | no fog |

Densities are out of 128. The fog table is sampled over view depth through the
renderer's depth remap: the whole arena lies between about 32690 and 32760 of the
15-bit depth, so `fogShift` is 10 (one depth unit per entry) and `fogOffset` is just
past the ramp's start (32750..32752 outdoors, 32741 snow, 32728 caves, 32734 void). Entry 0
is always 0, so the platforms and the near ground stay clear. DeSmuME computes the fog
depth as `(z/w + 1) * 0x4000`, one more than the DS's `z/w * 0x4000 + 0x3FFF`; the
tool keeps every depth that must be clear clear under both.
