# 3D battle stage: lit, deformable Pokemon sprites (chunk 3)

This is the contract between the renderer (game C code) and the emulator critic
(`tools/battle_stage/emu/critic.py`). PLAN.md, chunk 3, has the goals.

## When the new path runs

The battle sprites get the new "stage sprite" path only while `BattleStage_IsVisible()`
is TRUE: the arena is loaded for this battle, enabled, and not suppressed. Otherwise every
sprite draws exactly as before (one unlit quad from `NNS_G2dDrawSpriteFast`). The debug
A/B toggle (L+R+SELECT) and every suppression reason therefore switch the sprites back to
classic together with the arena.

Other users of `PokemonSpriteManager`, such as the summary screen, evolution, contests
and the Pokedex, never see the new path. `pokemon_sprite.c` is in the ARM9 main binary
and battle_stage.c is in the battle code, so the link is a hook: the battle sets it on its
own `PokemonSpriteManager` in `BattleStage_Init`, or wherever the manager is available,
and clears it in `BattleStage_Free`. With the hook NULL, `PokemonSpriteManager_DrawSprites`
is byte-for-byte the old code path.

## The mesh

Each visible, non-hidden mon is drawn as an 8 x 8 grid of quads, 81 vertices, instead of
one quad. The grid covers exactly the rectangle and UVs the old quad covered:

- **Normal draw:** the rectangle centred on (xCenter + xOffset, yCenter + yOffset -
  shadow.height), sized by scaleX and scaleY, with the full frame UVs.
- **Partial draw** (Dig, Fly, the silhouette intro and others): the drawX/Y/Width/Height
  rectangle and its clipped UVs.
- The same matrix setup as today: translate to the pivot, rotate X/Y/Z, translate back.
  Mosaic, flip, fade, the palette and the per-sprite `alpha` and `polygonID` are unchanged.

**Normals** form a soft pillow. Each vertex normal is the camera-facing normal tilted
outward toward the grid edge, by at most about 35 degrees at the rim. In the sprite
camera's space, +z faces the viewer. Watch the sign of y: the sprite camera maps 1 unit
to 1 pixel, and its y axis may point down.

**Lighting:** polygons use `GX_LIGHTMASK_0`, with light 0 left as the arena set it. The
arena loads the light vector in its view space, and the sprite normals are in the sprite
camera's view space; both look down -z, so up and left must agree. The material is the
arena's lighting column for the time of day (`SetLight`), combined with the sprite's own
`diffuseR/G/B` and `ambientR/G/B`, which move animations use to dim or tint a mon:

- `material diffuse = arena.diffuse * sprite.diffuse / 31`
- the same for ambient
- the arena's emission is used as is

A camera-facing surface therefore saturates to the unchanged texture at day, just as the
arena's camera-facing surfaces do. **Day at the home pose, with idle motion frozen and blob
shadows off, must be pixel-identical to classic** (see the critic below). Twilight and
night tint the mon like the arena, and the pillow rim shows soft shading at every time of
day.

## Idle motion

- **Breathing:** squash and stretch anchored at the feet (the bottom row of the grid stays
  put). About +-2.5% in y, the opposite in x (half of it), plus a slight top sway of at
  most 1 pixel in x. The period is about 3 seconds at 30 fps. The phase is offset per
  battler so the mons are not in sync.
- **Paused during move animations:** while a move/anim script is running (the battle anim
  system's active flag, or whatever the renderer finds most reliable). Also paused while
  the sprite is under partial draw, or has a non-default scale or rotation from a move.
  It resumes from the rest pose (phase restarts at 0) so there is no snap.
- **Hit wobble:** when a mon takes damage (the hit blink task in battle_display.c, or the
  HP-drop hook), its grid does a short decaying wobble of about 12 frames: a horizontal
  shear of the upper rows, at most about 3 pixels at the top.

All of this deforms grid vertex positions only. The sprite's `transforms` in RAM are never
written, so move animations, the critic and the game logic see the same values as before.

## Blob shadows

A soft translucent ellipse sits on the 3D ground under each visible mon. It uses a small
alpha texture (A3I5 or A5I3) generated at init and placed in the arena's texture VRAM
range, so it survives the menu bank swap. It follows the mon's x (and the platform offset
during the intro slide). While blobs show, the classic shadow quad is not drawn. When the
stage is not visible, the classic shadow comes back.

The blob is drawn after the arena, before particles and sprites. Use a polygon ID and
alpha so it blends over the ground and does not z-fight it: offset it a little toward the
camera, or disable depth writes with `GX_POLYGON_ATTR_MISC_XLU_DEPTH_UPDATE` off.

## Debug fields in sBattleStage (read by the critic from RAM via the xMAP)

`BattleStage` gains these fields after `brightness`. The existing offsets must not move.

| offset | field | meaning |
|---|---|---|
| +32 | `u32 debugFlags` | written by the critic. bit0 `FREEZE_IDLE`: no breathing and no wobble. bit1 `NO_BLOB_SHADOWS`: blobs off, classic shadow back. bit2 `CLASSIC_SPRITES`: sprites take the old path even while the arena shows. |
| +36 | `u32 spriteMeshes` | number of mons drawn as a mesh in the last drawn frame |
| +40 | `u32 idleFrames` | increments on every drawn frame in which breathing advanced for at least one mon |
| +44 | `u32 wobbleMask` | bit n set while battler n wobbles |
| +48 | `u32 blobShadows` | number of blob shadows drawn in the last frame |

Every field is reset in `BattleStage_Init`, except `debugFlags`, which survives battles so
the critic can set it once at the overworld.

## Budget

- **Geometry:** at most 4 x 64 quads plus 4 blob quads per frame. Use quad strips (8
  strips of 18 vertices per mon), or triangles if strips cause trouble.
- **CPU:** the per-vertex math must be fixed point. Precompute the normals and the
  grid-relative positions once, since only breathing, wobble and scale change per frame.
- **VRAM:** the blob texture is at most 1 KB.

## Critic checks (new scenario `sprite_life`, plus changes to others)

- `stage_ab` sets `FREEZE_IDLE | NO_BLOB_SHADOWS` before its battle and still expects an
  exact match at day.
- Every check that compares against "the closest idle frame" also sets `FREEZE_IDLE`, or
  masks the sprite boxes.
- `sprite_life`, on the Plain battle at day:
  - `spriteMeshes == 2`.
  - `idleFrames` advances at the command menu, and the sprite boxes change over 3 s while
    the rest of the scene does not.
  - `idleFrames` stops during a move played from the move tester.
  - Blob shadows show (`blobShadows == 2`), and the area under each mon is darker than
    with `NO_BLOB_SHADOWS`.
  - With `CLASSIC_SPRITES`, the sprites match the stage-off frame.
  - At night the mons differ from the stage-off frame, which shows the tint, and are not
    black.
  - Wobble: a damaging move from the wild battle or the move tester sets `wobbleMask`.
- `move_tester` also plays Minimize (107), Dig (91), Fly (19), Substitute (164) and
  Transform (144). Each must finish and restore the normal look.
- The `mega` and `totem_battle` scenarios still pass.
