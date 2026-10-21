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

`BATTLE_STAGE_VERSION` was 2 for chunk 2 (it is 3 now, see "Time of day and weather"). The changes from v1:

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
`GX_LIGHTMASK_0`. The renderer sets these once per frame from the lighting it picked at
battle start (format v3: a blend of `atmosphere.lighting[]` by the clock and the weather, see
"Time of day and weather" below; in v2 it was `atmosphere.lighting[ov16_0223EC04(battleSys)]`):

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

# Time of day and weather (format v3, bw2vis:stage-light)

`BATTLE_STAGE_VERSION` is 3. The atmosphere has 12 lighting columns
(`enum BattleStageLightingColumn`) instead of 3, a `haze` byte per column (it was padding),
and a second fog grid for the weather haze (`hazeShift`, `hazeOffset`, `hazeBase[32]`,
`hazeTable[32]`): 344 bytes instead of 96. Nothing else in the format changed; the geometry and
textures of every piece are byte-identical to v2.

## What BW2 does

`BtlvEffect_Init` (pokebw2 `src/ov168/btlv_effect.c:289-300`) calls `FieldLightStatus_Get`
(`src/system/field_light_status.c`) once, when the battle's bgType has its `light` flag set. That
picks a light file: the weather's set from `res/lighting/battle/` when the field has weather
(`sWeatherLightIds`), else the zone's own, else the area's. A file holds 15 settings, each
holding from the previous one's end until its own: an hour period (morning, day, evening,
night, midnight, which start at 5, 10, 17, 20 and 0 in spring, `rtc.c` `LIGHT_CHANGE_HOURS`) plus
minutes. The battle takes only light 0's colour, pointing straight down; the material comes
from the stage and field models. So BW2 steps 15 times a day, per zone. Nothing in ov167-169
sets the light again: an in-battle weather change (Rain Dance, Sandstorm) does not relight the
stage. Ours does the same: lighting is picked at battle start only.

Light 0 colour of `res/lighting/battle/001.json` (a typical outdoor set): (11,11,16) until 5:00,
(12,12,18) 5:30, (12,12,22) 6:00, (15,15,22) 9:00, (18,18,21) 11:30, (22,22,20) 12:00,
(24,24,20) 15:30, (22,22,18) 16:00, (20,18,16) 17:00, (19,16,12) 18:00, (17,13,10) 18:30,
(16,13,10) 20:00, (11,12,15) 21:00, (11,11,16) 23:00. The weather sets 2-5 are a flat grey
(22,22,20) all day, 0 and 6 a dark (11,11,12); 7-9 follow the day like 001 with other night colours.

## Ours

`src/battle/battle_stage_light.c` resolves one `BattleStageFileLighting` and one fog table when
the arena loads (`BattleStageLight_Resolve`, called from `BuildArena`), and the renderer and the
stage sprites use it for the whole battle.

- **Which backgrounds.** Only the six that already have time-of-day palettes
  (`ov16_0223EC04`: plain, water, city, forest, mountain, snow) take the clock and the weather.
  Indoor, cave, Distortion World, Elite Four and facility backgrounds keep column 0 whatever
  the time and weather. In BW2 indoor bgTypes have no `light`, and cave zones have constant
  lights, so this matches; it also keeps the 2D fallback of those rooms exact.
- **Columns.** 0 day, 1 twilight, 2 night (the classic ones, unchanged), 3 morning (cool blue),
  4 dusk (orange), then 5 rain, 6 storm (heavy rain, thunderstorm), 7 snow (snow, heavy snow,
  hail), 8 blizzard, 9 fog (fog, deep fog), 10 sand, 11 rift mist (the hack's
  `OVERWORLD_WEATHER_RIFT_MIST`, Route 210 North; its fog colour is the field's (22,12,28) from
  `Weather_RiftMistTask`). Each column is made by `atmosphere.py` from an up/away target as before.
- **Clock.** The minute of the day comes from the RTC (`RTC_GetCurrentTime`) at battle start. A
  keyframed schedule gives each time-of-day column a weight, linear between keys:

  | key | weights | BW2 light 0 then |
  |---|---|---|
  | 0:00, 4:00 | night | (11,11,16) |
  | 6:00, 9:00 | morning | (12,12,22), (15,15,22) |
  | 12:00, 15:30 | day | (22,22,20), (24,24,20) |
  | 17:00 | twilight | (20,18,16) |
  | 18:30 | dusk | (17,13,10) |
  | 20:00 | half night, half dusk | (16,13,10) |
  | 21:00, 24:00 | night | (11,12,15) |

  The classic BG palettes (which the arena textures follow) still step at 4:00, 17:00 and 20:00
  (`TimeOfDayForHour`). The keys at those minutes land on the column made for that palette, so
  each palette stretch blends smoothly and the steps stay where the classic game has them.
- **Forced time of day.** When the battle's time of day did not come from the clock (the
  quick-battle launcher's Day/Twilight/Night, `FieldBattleDTO_DebugTimeOfDayForced`, or a time
  of day that does not match the RTC hour), the representative minute is used: 12:00, 17:00 or
  23:00, which are pure day, twilight and night columns. Forced battles therefore light exactly
  as in v2 (`stage_ab` and `all_backgrounds` are unchanged).
- **Weather.** The field weather of the battle (`BattleSystem_FieldWeather`, the overworld's
  weather when the battle started) picks a weather column. It is blended over the time-of-day
  result by a weight that follows the light: all of it in the morning and the day, 80% at
  twilight, 70% at dusk and 40% at night (the classic night palette is already dark, so the
  weather only greys it).
- **Fog.** The fog colour is blended with the same weights as the light, so every pick keeps
  fog and light in step. Without weather the distance fog is the v2 one: it starts beyond the
  farthest point of the home view (outdoors), so the home pose still matches the classic art
  and the haze only shows on the far panorama when the camera turns. A weather column carries a
  haze (0..128). With a haze the renderer switches to the haze grid, which starts at view
  depth 4 (just in front of the platforms), with the table
  `hazeBase + (hazeTable - hazeBase) * haze / 128`: `hazeBase` is the distance fog resampled on
  that grid and `hazeTable` the full haze (56/127 at depth 14, toward 112), never below it. So the
  weather desaturates toward its fog colour (light can only multiply the art), heavier for fog,
  blizzard, sand and the rift mist than for rain. The sprites carry no fog bit and stay crisp.

The 2D fallback (`BattleStage_Suppress`, and the stage switched off) shows the classic palettes
only. At 12:00, 17:00 and 23:00 nothing changed. In the morning and at dusk the arena is tinted a
little more than the classic art (stage on vs off, mean channel difference 11-21 on 0..255, the
twilight column's own is 6-10), and under weather by design much more (rain at noon 37, rift
mist 48). The compat fades (F6) cross-fade between the two, so a move that hides the arena
shows the change as a fade, not a pop.

`sBattleStageLightDebug` (`include/battle/battle_stage_light.h`) holds what was picked: the
minute, whether it came from the RTC, the weather column, the column weights and the resolved
lighting and fog. `atmosphere.resolve()` mirrors the C bit for bit, and `preview.py --strip`
renders it.

## Terrain and the backdrop (not done)

In BW2 the terrain picks the field model as well as the platforms (`bgData[bgType].fieldIds[terrain]`,
`btlv_effect.c:276-288`), so sand and grass in one zone get different worlds. Ours keeps the
backdrop per `battleBG` (`BACKGROUND_WATER` while surfing) and lets the terrain pick only the
platform piece (`field_battle_data_transfer.c` `CalcTerrain`). Doing BW2's split is not a small
data change in our selection: the 23 backdrops are the classic art, and there is no sand, beach or
marsh backdrop to switch to. The only remaps the existing art allows (snow or ice tiles to
`BACKGROUND_SNOW`, water to `BACKGROUND_WATER`) already happen, because the maps with those
tiles carry those backgrounds. So it stays as it is until there is backdrop art per terrain
(the BW2-style field of the stage audit's row 9).

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
  night. With "Clock" the v3 lighting follows the RTC hour and minute.
- The critic cycles all 29 launcher backgrounds at each time of day, at the home pose and
  in the debug views, and checks for holes, missing arena, garbage and palette errors.
- `stage_ab` compares against the classic art with a tolerance, not exactly.
- A Mega scenario checks that the stage stays visible and dims during the pulse.

# BW2 visual parity: stage animation (workstream stage-anim)

Gen 5's battle fields animate: the sky of the outdoor fields drifts, water flows under a wave
layer, grass and bushes sway (audit: `/tmp/bw2gap/stage.md` rows 1-3). The arena plays the same
kinds of motion from data in the pieces. It sits on format v3 (stage-light's lighting columns)
without changing any struct layout: the new mesh flags (`DRIFT`, `SWAY`) reuse the scroll
fields, and a3i5 is one more `GXTexFmt` value. A renderer without them ignores the flags and
refuses a piece with an a3i5 texture (only `BACKGROUND_WATER` has one), so the version stays 3.

Per-battle budget over the launcher's 30 pairs, after these features: at most 572 polygons
(plain/grass; 564 before), 7 textures, 49 meshes and 60 KB of textures (the water battle; limit
64 KB). BW2's worst realistic pair is about 570 polygons.

The animations count arena draws (`StageArena.frame`, 30 per second). While the critic sets
`BATTLE_STAGE_DEBUG_FREEZE_IDLE` (stage_ab and all_backgrounds compare the home pose with the
classic art) the frame holds at 0, where every animation shows the classic art.

## Drifting clouds (`DRIFT`)

`BATTLE_STAGE_MESH_DRIFT` moves a mesh's texture at a constant speed: the offset is
`(s8)scrollAmplitude[i]` texels every `scrollPeriod` draws, on s and t, wrapped at the texture's
repeat period (its size, twice that with FLIP) so the texture coordinates stay in range. An axis
that moves needs its REPEAT flag, and DRIFT can't be combined with SCROLL. It adds to
`FOLLOW_BG3_SCROLL`.

Outdoors (`KIND_OUTDOOR`) the panorama gets an extra band edge at the background's **sky row**,
derived from the art: the first row, from the top, with a pixel that isn't sky in the day
palette (bright and blue or white: blue >= 176, blue >= red, 4 * blue >= 3 * green). Every
panorama band above it drifts. The rows below it, the horizon's tree line, mountains, buildings
and the sea, stay put.

| background | sky rows | base row |
|---|---|---|
| plain | 0..49 | 57 |
| water | 0..56 | 57 |
| city | 0..38 | 56 |
| forest | none (all foliage) | 53 |
| mountain | 0..44 | 58 |
| snow | 0..38 | 48 |

The speed matches BW2's on screen. BW2's sky texture (128x64, `batt_sky01` in `074.nsbmd`)
spans its whole half-cylinder, about 16 texels across the screen through the battle camera, and
`075.nsbta` scrolls it one texture width per 5000 frames: about 0.42 px per frame at 60 fps, 25 px
per second. Our sky is the classic art at one texel per pixel, so the drift is 21 texels per 25
draws. Positive s moves the art left, as a BG3 X scroll does. The texture is REPEAT_S | FLIP_S, so
it is periodic every 512 texels and continuous at the mirror lines: the drift never shows a seam.

Each sky split costs one panorama band (22 polygons). The classic fallback (`BattleStage_Suppress`)
shows the sky at frame 0, so it can jump by the drifted amount while a move hides the arena; the
fade (F6) covers most of it. The palettes stay live, so twilight and night drift the same way.

## Water: glint layer and platform water

BW2's water field (`batt_bg21`, `115.nsbmd`) flows its base texture under a translucent a3i5
glint layer (`batt_field21n`, scrolled by `117.nsbta`). Our water keeps its base sway (`SCROLL`
on the ground bands, above) and adds the glint layer:

- `GX_TEXFMT_A3I5` textures are allowed, with an embedded 32-colour palette
  (`BATTLE_STAGE_PALETTE_EMBEDDED` only). A mesh with an a3i5 texture, or an alpha under 31, is
  translucent: the DS draws it after the opaque polygons and it doesn't write depth.
- `BACKGROUND_WATER`'s backdrop piece has a third texture, BW2's glint texture (every other row,
  128x32, checked in as `tools/battle_stage/bw2/wave.bin` by `bw2_assets.py`), and one more mesh:
  a plane 0.1 above the water from the water row to row 120, 12 polygons, with world-linear
  texture coordinates (a 4 x 8 unit tile) that `DRIFT` toward the camera and sideways at 0.5
  units per second each. Polygon alpha 20 keeps the glints under the critic's "big"
  difference (48 levels) from the classic water: at frame 0 they are a sparse sparkle, about 0.6%
  of the scene. Below row 120 the 128x32 texture would be magnified into blocks, so the layer
  stops there.

The platform water of `TERRAIN_WATER` and `TERRAIN_PUDDLE` sways (BW2's puddle stages
`batt_stage08/09` wobble their water, `023/025.nsbta`). The art's water pixels (bright blue in
the day palette: blue >= 200, blue > red + 32, blue >= green), shrunk by the sway amplitude so
they never move onto the rim or the sand, go to an overlay texture with the platform texture's
layout (the platform piece's textures are now each platform's art, then its extra textures). The
overlay meshes copy the visible disc strips that hold water pixels, 0.06 above the disc on the
same pixels and texture coordinates, so at frame 0 they show exactly what the disc does; they
`SCROLL` (water: amplitude (2, 1) texels over 60 draws, the stripes roll; puddle: (1, 1) over 40,
a shimmer). Cost: water platforms +43 polygons, puddle +19, and 8 KB of textures; the water
battle is at 60 KB of the 64 KB texture budget.

The glints' palette is embedded, so a palette fade of the BG palette doesn't darken them (the
backdrop fade, `BattleStage_SetBackdropFade`, does, through the lighting).

## Grass sway (`SWAY`) and the platform fringe

`BATTLE_STAGE_MESH_SWAY` sways a mesh: its positions shear along x, `x += k * (y - pivot)`, with
`k = (s8)scrollAmplitude[0] / 256 * sin(2pi * frame / scrollPeriod)` and `pivot =
scrollAmplitude[1] / 64` world units, applied in world units before the vertex scale (a
`G3_MultMtx43` after the platform's translation). Its normals keep their direction.

BW2's grass stages move their blades and leaves (NSBCA joint translation, 500-800-frame loops).
The classic platform art has its own blades: on `TERRAIN_GRASS` they stick out above the
platform's ellipse. Those pixels (the art's pixels above `TERRAIN_PLAIN`'s ellipse, which every
terrain shares) stand up as a **fringe**: one strip of vertical quads along the back rim, between
home screen columns, the foot of each column on the rim on the disc and its top above the highest
such pixel, textured through the home camera from an extra texture that holds only them (the main
texture loses them). At home the platform looks exactly as before (the preview's diff is 0 under
both rasters); off home the blades stand on the rim instead of lying flat behind it. The quads
are at most 32 px wide, narrower where the rim's depth changes fast, so the perspective texture
error stays under 0.25 px. The fringe sways with the shear that moves its top row 1 px at the
peak, pivot at the disc's height, over 56 draws on the player's side and 46 on the opponent's.

Cost: 18 polygons and 8 KB of textures on `TERRAIN_GRASS` (grass battles: 572 polygons on the
plain background with its sky drift, 550 in the forest). The forest's panorama itself stays still:
it is horizontal streaks of foliage, and a sway of the whole band reads as the background sliding,
not as bushes moving.

## Platform relief: standing rocks

BW2's platforms carry stones and tufts up to 1.8 units tall; ours are the flat classic art. On
`TERRAIN_MOUNTAIN` every rock of the art stands up: a blob of at least 8 grey pixels (channel
spread <= 20, plus the darker outline around it, <= 24, which only joins where it touches a body:
the art draws the ground's cracks with the same colour) becomes one vertical quad facing the
camera, its foot on the disc one row under the rock (on the rock's own bottom row the quad would
tie with the disc's depth and lose), textured through the home camera from an extra texture that
holds the rocks. The main texture fills each rock pixel inside the platform's ellipse from the
nearest ground pixel of its row, so a standing rock leaves ground behind it, and drops the parts
of rocks above the rim. At home the platform is pixel-identical at every time of day (preview,
both rasters); off home the rocks stand. Rocks that reach under the text box (the player's front
rocks) stay flat, because their foot would be off the pixel grid. Cost: 8 polygons (2 player
rocks, 6 opponent rocks) and 8 KB of textures on `TERRAIN_MOUNTAIN` (mountain battle 565
polygons). Every new prop sits inside the home-pose look: nothing is added that the classic art
doesn't draw.

## Not done: the off-home smear (audit row 9)

In the Mega orbit the ground and the panorama streak: rows of the projected classic art run off
toward the vanishing point. The cause is the art itself, not the panorama's shape: the classic
backdrops are horizontal streaks, one colour per row, so any surface that keeps the home
projection's rows (the ground past the screen edges, the arc) shows each row as a line seen
from the side. An experiment that gave the side ground and the arc cylindrical texture
coordinates (constant density past the frustum edge, `/tmp/bw2vis/stage-anim/item6/`) rendered
the Mega orbit almost unchanged, and wrapping the panorama further round behind the camera only
changes the sky band, which is already clean. The fix is BW2's: an isotropic tiled ground (and
sky cylinder) that the renderer blends in as the camera leaves home, with the home-matched arena
blended out. That needs new textures, a pose-dependent blend in the stage C and its own VRAM, so it
was left for its own piece of work rather than shipped half-done.
