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

## Gen 5 motion (bw2vis:idle)

What replaces Platinum's own motion on a battler the stage draws from its Gen 5 stream, and the
B/W behaviour added on top. The B/W behaviour comes from the pokebw2 decomp (`src/ov168/btlv_mcss.c`,
`btlv_effect.c`); where B/W use an effect script that isn't in the decomp (send-out, faint), the
look is approximated and says so. The code is `src/battle/battle_stage_idle.c` (and
`battle_stage_copies.c` for the move copies). Every change falls back to Platinum's behaviour on
the classic path: the stage off (L+R+SELECT), `CLASSIC_SPRITES`, `NO_SPRITE_STREAM`, and the
species without a stream (forms, Spinda, the Egg).

"Uses Gen 5 motion" (`BattleStage_UsesGen5Motion`) means: the stage is on and its streams play
(the arena drawn, or hidden with its texture VRAM kept), neither debug flag is set, and the
battler's sprite template has a stream (`BattleStageStream_HasStream`, which also answers for a
template that changed this frame, before its tables are read).

The harness reads `sGen5MotionStats` and `sMonCopyStats` (in the xMAP), zeroed at each battle's
`BattleStage_Init`.

### Entry animation

B/W play no per-species motion at send-out or wild appear: the stream's loop plays and the cry
plays. Platinum ran its per-species animation there: the frame swaps (`PokemonSprite_InitAnim`,
which also writes an x offset per frame) and the `PokemonAnim` script (`PokemonSprite_LoadAnim`:
hops, squash, rotation and palette fades; Luxio flashed solid yellow 4 times on top of its B/W
loop). All 19 call sites in `battle_display.c` now go through `BattleStage_InitEntryAnim` and
`BattleStage_LoadEntryAnim`, with the same arguments. For a battler that uses Gen 5 motion the
frame swaps don't start and the script is set up and deleted at once, before its task runs a
command, so its anim slot reads complete and the send-out tasks go on. The send-out's own ball
colour fade and scale-in, the wild silhouette fade and the cry are unchanged. Counted in
`entryAnimsSkipped` and `entryAnimsPlayed`.

### Command-menu bob

B/W bob only the active mon's HP gauge at the command menu (`btlv_gauge.c`). Platinum's task
(`ov16_02264798.c`) also bobbed the player's sprite 1 px on a 36-frame period, a third idle
motion on top of the stream and the breathing. The task still runs (it starts and stops as
before), but writes a y offset of 0 while the stage draws the battler as a mesh or from its
stream (`BattleStage_SuppressMenuBob`, from the stage's mesh and stream masks of this frame and
the last), so toggling the stage off at the menu brings the bob back. The gauge's own sway is the
hud-gauges stream's. Counted in `bobSuppressedFrames`.

### Hit flash

B/W's `BtlvEffect_StartDamage` / `BtlvEffect_BlinkTask`, 3 times: the palette all
GX_RGB(2, 2, 2) for a physical move or GX_RGB(24, 24, 24) otherwise, then hidden, then shown with
its own colours, 4 frames each (36 frames). Platinum's blink task (`ov16_0226292C`) now does
exactly that; it runs at 30 Hz, so a phase is 2 of its frames, and B/W's battle runs at 60 Hz (its
main loop waits one vblank a frame; 30 Hz mode is the field's). The colour comes from the current
move's category (`BattleStage_HitFlashColor`: `moveCur`'s class in the battle's move table). The
flash is a palette fade (`PokemonSprite_StartFade` 16 to the colour, then 0), so it shows on the
streamed mesh and on the classic sprite alike, and the status tint (`PokemonSpriteManager_SetTint`)
waits under it and comes back after. A battler hidden when the hit came (Fly, Dig) doesn't flash,
as in B/W, and is shown at the end as Platinum's blink always left it. The stage's 12-frame
shear wobble still plays (B/W has none). Counted in `hitFlashes`, the last colour in
`hitFlashColor`.

### Faint

B/W's faint is effect script 0x23B, which isn't in the decomp; from memory it is a slow sink
with a fade-out. Platinum slid the clip window down 8 px a 30 Hz frame, so the mon was gone in
about 10 frames, with no fade. Now it sinks 3 px a frame (`FAINT_SINK_PX`) and its polygon alpha
ramps from 31 to 1 over 16 frames (`FAINT_FADE_TICKS`, about half a second); it is deleted when it
has faded or sunk (alpha 0 would draw wireframe). The cry, the drop sound and the faint kick are
unchanged; the kick has settled home before the sink starts, which waits for the cry. On the mesh
the partial draw keeps its cuts (`BattleStageStream_CanvasRect`), the breathing and the blob are
off as for any partial draw, and the stat overlay skips a translucent mon. The cut guard leaves a
partially drawn sprite alone once its window's bottom is above the frame's (`CutHomeY`), as
before: the sink line is meant to show, and the camera is home by then. Counted in `faints`.

### Special idle

B/W (`btlv_mcss.c` `OnAnimationEnd`, `IdleTask`): at the end of each loop of the idle sequence a
mon may play a special idle, with a chance of 1 in 3, then 1 in 2, then 1 (the count goes back to
3 after one). The idle freezes the mon, except its idle nodes, for 48, 56 or 64 frames at random,
on the first frame of its second sequence if it has one, then restarts the loop from its first
tick. Never while an effect script runs, and a script that starts ends it at once.

The stream plays it as a second step table (`battle_stage_stream.c`, `StartSpecialIdle`,
`EndSpecialIdle`): at a loop wrap it asks `BattleStage_StreamSpecialIdleStart(battler, idleSteps,
&wait)`, which applies B/W's roll and gates (no move anim, no `FREEZE_IDLE`) with its own
generator (the battle's RNG is never touched), then plays the idle steps for `wait` vblanks
(counted whatever the speed, as B/W's frame count), cut mid-step, then the loop from step 0.
`BattleStage_StreamSpecialIdleAbort` ends it when a move anim starts; a frozen stream ends it too.

- **Real data** (sprite-source's index version 3, `idleKind`/`numIdleSteps` and
  `MonStream_IdleSteps` in `pokemon_sprite_stream.h`): compiled in when the header defines
  `MON_STREAM_IDLE_NONE`. A face with `idleKind` NONE plays no idle, as in B/W (53 species, most of
  them flyers); FREEZE and POSE play their clip.
- **Approximation** (the member has no idle data, as with version 2): the loop's first frame held
  (one step), while the breathing goes on in place of the idle nodes.
- A still (one step: the Megas' backs) never idles.

Counted in `idleRolls`, `idleStarts[4]`, `idleAborts`, `idleActiveMask`, `idleApproxStarts`,
`lastIdleWait` and B/W's `idleCount[4]`.

### Move copies

A move's copies of a battler (an OAM copy, `AddPokemonSprite`: Double Team, Agility, Minimize,
Transform and 33 more: 37 moves; a BG2 copy, `LoadPokemonSpriteIntoBg`: Acid Armor, Extrasensory, Sketch,
Spite) were the classic 80x80 window of the stream frame: a back at 1.75x showed only its
bottom-centre 46x46 texels, with no sink, and the mesh popped back larger and lower when the copy
went. Now, for a streamed battler:

- **OAM copies** (`battle_stage_copies.c`): `AddPokemonSprite` registers the copy with the stage
  (`BattleStage_AdoptMonCopy`) and uploads blank tiles in place of its own, so the 2D copy shows
  nothing and the script keeps driving it as before. After the battle's sprites,
  `BattleStage_DrawMonCopies` draws each visible copy as one quad of the battler's live stream
  frame, as the mesh draws it: its canvas at its scale (`BattleStageStream_CanvasRect`, sink
  included) about the copy's position, with the copy's affine scale and rotation, the arena's
  sprite tint, polygon alpha from the blend's EVA for a translucent copy (40 + slot as polygon ID,
  so copies over each other blend), and the battler's camera similarity off home. The copy's own
  palette tint (Double Team's) is not reproduced. `RemovePokemonSprite`, `FreePokemonSpriteManager`
  and the script's end drop the copies. An effect that uses a copy as an OBJ window (Harden,
  Superpower, Camouflage, the 2D stat change) gives the battler's copies back to 2D with their own
  tiles first (`BattleStage_ReleaseMonCopiesOf`), so the window and the copy shown still match.
  Cost: one quad a visible copy (at most 5), no VRAM.
- **BG2 copies**: after `LoadPokemonSpriteIntoBg` loaded the classic copy,
  `BattleStage_BuildBg2Copy` replaces it with the live stream frame at the mesh's scale: the
  canvas rect (sink included) in BG pixels about the classic frame's place, tile-aligned, written
  into BG2's tiles from tile 1 (tile 0 stays blank) and its 512x512 tilemap with wrap, so the
  move's BG offsets and per-line scrolls still place it. BG2's tiles end where BG3's begin: 511
  tiles at most, enough for the largest back (a 96x96 box at 1.75x is 22x22 tiles); a larger copy
  keeps the classic one. It is built before compat F1 lifts the copy over the arena
  (`BattleAnimSystem_LiftBg2Copy` keeps the BG2 tilemap's hash and drops the lift when it
  changes), so the arena stays visible with the copy lifted as before. `RemovePokemonSpriteFromBg`
  clears the tiles it used and its tilemap.

Counted in `sMonCopyStats`: `adopted`, `released`, `drawnFrames`, `bg2Copies`.

## Blob shadows

bw2vis:shadow: streamed battlers now get BW2's silhouette shadow instead of the blob
(shadows.md); the blob below is the fallback for the rest.

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

Every field, `debugFlags` included, is zeroed when a battle loads: `sBattleStage` is cleared
in `BattleStage_Init`. The critic therefore writes `debugFlags` inside each battle, once the
stage is up, and waits about 10 frames before it compares anything.

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
