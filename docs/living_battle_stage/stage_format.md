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
