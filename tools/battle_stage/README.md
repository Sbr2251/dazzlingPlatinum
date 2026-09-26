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

`preview.py` needs numpy and PIL. It prints the pixel diff between the home pose and
the classic scene (rows 0..143; the text box covers the rest) and the hole count of
every debug view. Both should be 0 with both `--raster desmume` (the default: the soft
rasterizer of DeSmuME 0.9.12, which py-desmume and so the critic use) and
`--raster hardware` (whole-pixel vertices, like the DS). `--terrain 2` checks the
TERRAIN_GRASS platforms (route battles in tall grass). `--tod 1` uses the twilight
palettes the critic's battle has.

Then run the critic on the ROM:

```sh
SDL_VIDEODRIVER=dummy ~/.venvs/desmume39/bin/python tools/battle_stage/emu/critic.py \
    out/dazzlingPlatinum.nds /tmp/stage_critic --scenario stage_ab debug_views
```

## Files

| file | what |
|---|---|
| `build_stage.py` | entry point: builds the textures and pieces and writes the NARC (47 members: 23 backdrop pieces, then 24 platform pieces; all but `BACKGROUND_PLAIN`, `TERRAIN_PLAIN` and `TERRAIN_GRASS` are empty, which keeps the classic scene; a battle needs both its pieces) |
| `arena.py` | the geometry: home camera, ground, panorama and platform discs, with every texture coordinate taken through the home camera. `python3 arena.py` prints the mesh list and budgets |
| `stage_format.py` | reads and writes pieces; mirrors `battle_stage_format.h` |
| `fx.py` | bit-exact NitroSDK camera math (`MTX_PerspectiveW`, `MTX_LookAt`, `VEC_*`, `FX_*`), the renderer's debug-view cameras and the geometry engine's vertex-to-screen transform |
| `classic.py` | the classic scene the arena must match: the BG3 backdrop image and palettes, the platform OBJ art, and a composite of the home screen |
| `nitro.py` | NARC read/write, LZ77, and NCLR/NCGR/NSCR/NCER decoding |
| `preview.py` | software renderer for the four views, the home-vs-classic diff and hole check |

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

## Arena layout (BACKGROUND_PLAIN / TERRAIN_PLAIN and TERRAIN_GRASS)

- Camera at (0, 4, 14) looking down -z, fovy 40 degrees, horizon on row 20, target
  midway between the platform depths, near 1, far 128, vertexScale 8.
- Ground (y = 0) from row 57 down to row 240 (below the screen, for view 3) and
  sideways well past the screen edges for views 1 and 2.
- Panorama: a flat wall standing on the row 57 ground line across the home view,
  bending toward the camera past the screen edges as a 30-unit radius arc, from the
  ground up to home row -64. Rows 0..57 are exact; above row 0 texture A's t clamps to
  the top sky row.
- Textures A (256x128) and B (256x32) are 8bpp BG palette indices with REPEAT_S |
  FLIP_S, which is what the mirrored 512-wide BG3 map looks like at any X scroll. B
  also mirrors in T, so the ground past row 158 repeats rows 158..127 instead of the
  black rows below the art.
- Platforms: discs 0.1 above the ground, textured with the platform OBJ art (only the
  ellipse is opaque), with a side band along the front half of the art's outline down
  to just under the ground. The player
  art is only the top half of its ellipse (the text box hides the rest), so its texture
  mirrors at sprite row 16 (FLIP_T) and the disc is a whole ellipse in the debug views.
