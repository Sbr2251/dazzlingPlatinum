# Battle stage: chunk 1 design and file format

The on-disk structs are in `include/battle/battle_stage_format.h`. The runtime API is in
`include/battle/battle_stage.h`. This note covers the decisions that the tool, the renderer
and the compatibility work all depend on.

## Home pose by projection mapping

The arena is real 3D geometry: a ground plane, a curved panorama behind it, and
platform discs. But every texture coordinate is computed by projecting the vertex
through the **home camera** onto the classic 256x192 screen, then reading the classic
art at that screen pixel:

- the backdrop pieces sample the BG3 backdrop image (at BG3 scroll 0,0);
- the platform tops sample the platform OBJ art at the platform's home screen position.

So at home pose the arena renders the same pixels as the classic BG3 backdrop and OBJ
platforms, however the geometry is shaped. The geometry only matters once the camera
moves (the debug views now, cinematics in chunk 4). It should roughly follow the scene:
ground below the art's horizon row, the panorama above it, and platforms as slightly
raised elliptical discs with a thin side band.

Because the arena matches BG3 at home pose, the renderer can fall back to the classic
backdrop at any time (`BattleStage_Suppress`) with no visible jump. The compatibility
work relies on this: any move that does something to BG3 or BG2 that the arena can't
reproduce just suppresses the arena for its duration.

The DS texture-maps with perspective correction. Keep triangles small enough, about 16
screen px, so any error stays under half a pixel.

Pixel convention: a vertex whose projection lands at screen (sx, sy), with the viewport
0..255 x 0..191 as in `G3_ViewPort(0, 0, 255, 191)`, samples texel (sx, sy) of the
screen-space art. The tool keeps a single named constant for a half-pixel offset, so the
critic's A/B pixel diff can tune it.

## Camera and depth

- The header holds the home camera. The renderer uses `G3_Perspective(fovySin,
  fovyCos, FX32_ONE * 4 / 3, near, far, NULL)` and `G3_LookAt(camPos, up = +Y,
  camTarget)`. The tool must reproduce NitroSDK's matrices exactly; see
  `G3_Perspective`/`MTX_PerspectiveW` and `MTX_LookAt` in the SDK headers under
  `subprojects/` / `lib/`.
- The arena is drawn **first** in the frame, before particles and sprites. It must
  always be behind them, so the renderer remaps the arena's clip-space depth into the
  far end of the depth range. It premultiplies the projection with a matrix that sets
  `z' = a*z + b*w`, so NDC z lands in about [0.96, 0.995], behind anything the ortho
  sprite, shadow and particle cameras produce, and in front of the clear depth.
- The renderer saves and restores the projection and position matrices
  (`G3_MtxMode` + `G3_PushMtx`/`G3_PopMtx`). The particle and sprite code keeps setting
  up its own cameras unchanged.
- Polygons are opaque (alpha 31), `GX_POLYGONMODE_MODULATE`, no lights, and the vertex
  colour is white unless shading is baked in. Toon shading is on globally with no toon
  table, which doesn't affect MODULATE.

## Textures, palettes and VRAM

- The backdrop is 8bpp (`GX_TEXFMT_PLTT256`) with the original BG palette indices.
  Power-of-two sizes are needed, so a 256x192 image becomes 256x128 + 256x64
  (48 KB). The platform tops are 4bpp (`GX_TEXFMT_PLTT16`).
- Budget: at most 64 KB of textures per battle (backdrop piece + platform piece).
- Textures are allocated in `BattleStage_Init`, right after `ov16_0223CE28()` reserves
  the sprite area. The address must end below 0x20000 (bank B), so the arena survives
  the bag/party menus unmapping bank C. The renderer asserts this.
- Palettes are synced from the live palette buffers each frame, and uploaded only when
  they change, via a VBlank VRAM transfer:
  - BG textures copy all 256 colours of the faded main BG palette;
  - platform textures copy the OBJ palette row of their side's platform sprite.

  This way time-of-day palettes, battle fades and move palette effects on the backdrop
  also show on the arena. The embedded palette is only a fallback.
- `BATTLE_STAGE_MESH_FOLLOW_BG3_SCROLL` meshes mirror the BG3 x/y offset through the
  texture matrix, with texgen = TEXCOORD and texture repeat on.

## Debug views

`BattleStage_SetDebugView`, cycled by holding L+R and pressing B at the command menu:

| View | Camera |
|---|---|
| 0 | home pose |
| 1 | orbit 20 degrees left (yaw) around `camTarget` |
| 2 | orbit 20 degrees right |
| 3 | orbit 15 degrees up (pitch), and 20% closer to `camTarget` |

The arena must have no holes in views 1-3: the panorama and ground reach wide enough,
and texture coordinates past the classic screen edge mirror (`FLIP`) rather than tile.
The tool's preview renders the same four views. The move tester returns to view 0
before it plays an animation.

## Platforms

Platform meshes carry `FOLLOW_PLATFORM_PLAYER`/`_ENEMY`. Each frame the renderer reads
the platform OBJ's screen offset from its home position (it slides in during the
intro) and translates those meshes by `offset * platformPixelToWorld[side]` along
camera-right. While the arena is visible, the platform OBJs are hidden. While it is
suppressed, they are shown again.

## NARC and build

The tool writes `res/prebuilt/battle/graphic/battle_stage.narc`. It is checked in,
like the other prebuilt battle NARCs, and registered in `platinum.us/filesys.csv` and
the local `meson.build`. The members are listed in the format header. Pieces not
generated yet are empty (`numMeshes == 0`). In chunk 1 only `BACKGROUND_PLAIN` and
`TERRAIN_PLAIN` have real pieces.

# Chunk 2: light, atmosphere and all backgrounds (format v2)

`BATTLE_STAGE_VERSION` is 2. The renderer only accepts v2. The changes from v1:

- `BattleStageFileHeader.atmosphereOffset` points at a `BattleStageFileAtmosphere`. Only the
  backdrop piece has one; platform pieces write 0. With 0 the arena is unlit white with no
  fog, as in v1.
- `BattleStageFileVertex.padding` became `u32 normal` (GX_VECFX10). The vertex is still 16 bytes.
- `BattleStageFileMesh` gained `scrollAmplitude[2]` and `scrollPeriod` (16 bytes).
- New mesh flags: `LIT`, `FOG` and `SCROLL`.

## Every background and terrain

Every NARC member is a real piece: all 23 backdrops and all 24 platform terrains. The
projection mapping stays as it is: at the home pose the texture coordinates reproduce the
classic art. Only the geometry and the atmosphere differ per background:

- Outdoor art (plain, water, city, forest, mountain, snow) is split at its horizon row into
  ground and panorama, as the plain one is.
- Indoor rooms, Elite Four and Champion rooms, and the Frontier facilities use a floor and a
  back wall. They can use a box, the camera-facing side walls optional.
- Caves use the same split with a darker, closer fog.
- In the Distortion World the art is a void, so a panorama without a real floor is fine.
- Water: the ground mesh under the water gets `SCROLL`, a slow sway of a few texels: the offset is
  `amplitude * (sin(a), sin(2a))` with `a = 2pi * frame / period`, a figure eight that starts at 0. Keep the
  scrolling region away from the edges of the mesh so there is no visible seam.
  `scrollPeriod` counts arena draws, not VBlanks. The battle draws the 3D scene every
  other VBlank (30 fps), so a period of 120 lasts 4 seconds.

Each terrain's platform piece samples that terrain's platform OBJ art (`PLATFORM_CHAR` and
the `[terrain][tod]` palette table in `classic.py`). The runtime palette comes from the
live OBJ row, as before.

Budget: at most 64 KB of textures per battle (backdrop plus platform), and at most
`STAGE_MAX_MESHES` meshes per piece.

## Light

`LIT` meshes send `G3C_Normal` for each vertex instead of `G3C_Color`, with
`GX_LIGHTMASK_0`. The renderer sets these once per frame from
`atmosphere.lighting[ov16_0223EC04(battleSys)]`:

- light 0 with `G3_LightColor` and `G3_LightVector`;
- the material with `G3_MaterialColorDiffAmb(diffuse, ambient, FALSE)` and
  `G3_MaterialColorSpecEmi(black, emission, FALSE)`.

Light 0 is set after the view matrix is loaded in `GX_MTXMODE_POSITION_VECTOR`, so
`lightDir` is in world space. The DS lighting per channel is
`min(31, emission + ambient*light/32 + diffuse*light*max(0, -dot(lightDir, normal))/32)`.

Keep the home pose close to the classic art. The fallback to BG3 (`BattleStage_Suppress`)
must not visibly jump:

- Day, column 0: surfaces that face the camera or face up (ground, panorama, disc tops)
  saturate to white. Shading shows on disc sides and on surfaces that turn away from the
  light when the camera moves.
- Twilight and night: a gentle tint and dimming on top of the classic palettes, which are
  already darker, so the effect does not double.

## Fog

`FOG` meshes get `GX_POLYGON_ATTR_MISC_FOG`. Every arena mesh sets it. Nothing else in the
battle uses fog, and the clear colour has fog off.

With `fogEnabled` set, the renderer calls:

- `G3X_SetFog(TRUE, GX_FOGBLEND_COLOR_ALPHA, fogShift, fogOffset)`;
- `G3X_SetFogColor(fogColor, fogAlpha)`;
- `G3X_SetFogTable`.

It turns fog off whenever the arena is not drawn.

Battles use `GX_BUFFERMODE_Z`, and the arena's depth is remapped into
[`STAGE_DEPTH_NEAR`, `STAGE_DEPTH_FAR`]/4096 of NDC, so the tool must compute
`fogOffset`/`fogShift` from the remapped 15-bit depth. Fog is meant for distance: caves,
snow haze and the far panorama. It must stay light at the home pose, so the arena keeps
roughly matching BG3.

The remapped depth range is very narrow. For a camera-space distance `d`, with the
`G3_Perspective` clip `z = (f+n)/(f-n)*d - 2*f*n/(f-n)` and `w = d`:

- `z' = A*z + B*w`, where `A = (STAGE_DEPTH_FAR - STAGE_DEPTH_NEAR)/2/4096` and
  `B = (STAGE_DEPTH_FAR + STAGE_DEPTH_NEAR)/2/4096`;
- `depth15 = (z'/w + 1)/2 * 32767`.

At the plain home camera (near 1, far 128), the nearest ground (d = 5) is at about 32694 and
the panorama (d = 30) at about 32750. The whole arena spans about 57 depth units, so use
`fogShift` 9 (2 units per table entry) or 10 (1 unit), with `fogOffset` around 32690-32705.
With a smaller shift, every arena pixel lands in the same one or two table entries. DeSmuME
confirms this: with shift 9, offset 32704 and table `i*4`, the panorama shows 72% fog (entry 23)
and the near ground about 30%.

## Brightness (Mega flash)

The Mega Evolution sequence dims and flashes the scene with the 2D brightness blend, which
skips BG0. `BattleStage_SetBrightness(int brightness)` (-16..16, the same scale as
`G2_SetBlendBrightness`) applies the same effect to the arena through fog.

While the brightness is not 0, it overrides the atmosphere fog:

- the fog colour is black for a negative brightness and white for a positive one;
- alpha is 31;
- every table entry is `min(127, |brightness| * 8)`;
- `fogOffset` is 0.

The fog blend `(fog*d + pixel*(128-d))/128` is then exactly the 2D brightness formula.
The sprites and particles carry no fog bit, so the evolving Pokemon stays white, as the
2D planes intend. The Affine Pulse calls `BattleStage_SetBrightness` alongside
`G2_SetBlendBrightnessExt` and resets it to 0 at the end. It no longer suppresses the stage.

## Checking it

- The quick-battle launcher gets a time-of-day override: map clock, morning/day, twilight,
  night.
- The critic cycles all 29 launcher backgrounds at each time of day, at the home pose and
  in the debug views, and checks for holes, missing arena, garbage and palette errors.
- `stage_ab` compares against the classic art with a tolerance, not exactly.
- A Mega scenario checks that the stage stays visible and dims during the pulse.
