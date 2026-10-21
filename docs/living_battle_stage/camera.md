# 3D battle stage: camera system and cinematics (chunk 4)

This is the contract between the renderer (game C code) and the emulator critic
(`tools/battle_stage/emu/critic.py`). PLAN.md, chunk 4, has the goals. It builds on
arena.md (the arena and its home camera) and sprites.md (the stage sprites and blobs).

## The rule that matters most

**At the home pose nothing changes.** While the camera is home (the `AT_HOME` flag
below), every frame must be byte-for-byte what chunk 3 draws:

- the arena uses the view matrix it builds today;
- no sprite matrix is touched;
- the particle hooks do nothing.

This must be an explicit code path ("home: skip it all"), not the result of a transform
that happens to come out as the identity in fixed point. `stage_ab` still expects an exact
match at day.

**Move animations always play at home.** They draw OBJs, BG effects and window masks in
screen space, and none of those can follow a 3D camera. So the camera snaps home before
every animation script starts (the guard below). The only scripts that move the camera are
the ones that use the new camera commands themselves: Mega Evolution and the Totem aura in
this chunk, and chunk 6's redone moves later.

## Camera state

The stage camera is an orbit camera around a focus point on the ground. A **pose** is:

- `focus`: a world point (VecFx32);
- `yaw`: an angle around the world up axis through the focus, relative to the home
  direction;
- `pitch`: an elevation offset relative to home, positive means higher;
- `distance`: a scale on the home camera-to-target distance (FX32_ONE is home);
- `fov`: a scale on the home fovy tangent (FX32_ONE is home).

The **home pose** is the arena's home `camTarget`, yaw 0, pitch 0, distance 1 and fov 1.
From a pose the camera position is `focus + R(yaw, pitch) * (home camPos - home camTarget)
* distance`, looking at `focus` with world up. Debug views 1 to 3 become poses in this model:
yaw -20 / +20 degrees, and pitch +15 degrees at distance 0.8. They must look as they do today.

**Motion:**

- A move, orbit or home command eases from the current pose to a goal pose over N drawn
  frames. Use smoothstep, (3t^2 - 2t^3) in fixed point, and interpolate each pose component.
- N = 0 snaps to the goal pose.
- A new command starts from wherever the camera is at that moment, so there is no jump.
- **Shake** is added on top: a decaying offset along camera-right and camera-up, in screen
  pixels converted to world units at the focus depth. The pattern is deterministic (a fixed
  table or a sine), never random, so the critic can reproduce it. A shake with a pose at home
  ends exactly at home.
- The camera advances once per `BattleStage_Draw` call, while the arena exists, whether or
  not the stage is visible.

**The camera is home** (`AT_HOME`) when all of these hold:

- the pose equals the home pose exactly;
- no ease is in progress;
- no shake is in progress;
- `debugView` is 0.

When the camera is not home, the view is rebuilt from the pose every drawn frame. When fov
is not 1, the projection is rebuilt too, keeping the depth squeeze of `BuildProjection`.

**Snap home** whenever the stage stops being visible (suppression, the A/B toggle, a menu),
and at `BattleStage_Free`. The classic path never sees an off-home camera.

## Sprites follow the camera (screen-space billboards)

The mons stay upright, camera-facing quads. Each battler gets a 2D similarity (a scale plus
a translation, no rotation) from where its feet are at home to where they are now:

- **Home anchor:** the battler's foot point on screen at home. x is the battler slot's
  classic home x (its default sprite x, not the sprite's current x, which moves during
  animations). y is the blob row of its side (`sBlobRow`).
- **World foot W:** the home camera ray through the home anchor, intersected with the ground
  (`GroundAtRow` already does this for the blobs).
- **Current anchor:** W projected through the current view and projection, in screen pixels.
- **Scale:** `s = (zHome / zNow) * (fovTanHome / fovTanNow)`, where z is W's view-space depth.
- **Transform of a sprite point p in screen pixels:** `p' = anchorNow + s * (p - anchorHome)`.

Apply it in `DrawHook` before the pivot rotation, so whatever a script did to the sprite
(offsets, scale, rotation, partial draw) rides along. When the camera is home, skip it.

**The classic path follows too.** If the stage is visible but the hook draws classic (the
`CLASSIC_SPRITES` debug flag), the hook still loads the transformed matrix before it returns
without `DREW`, so the classic quad lands in the same place. The same goes for the classic
shadow, where the manager draws it. Blobs are world-space in the arena view, so they follow
by themselves.

Sprite depth (z) is unchanged; the sprites still draw over the arena.

## Particles follow the camera

Off home every particle follows the mons around it, the way the mons themselves follow the
camera (particles-3d, bw2vis). At home nothing changes.

**Why not a plain 3D projection.** A battle particle system draws with its own orthographic
camera, which gives the classic 2D picture. Putting the particles on a 3D surface and drawing
them with the stage camera (the "battle plane" mode below) is correct 3D, but the mons are not:
they are camera-facing billboards moved by a screen-space similarity. Measured on the Plain
stage, a particle 30 px from the enemy in the enemy close-up (85%, yaw -6) lands 3-16 px off the
mon with the 3D plane, against 0 px with the field. So the default places each particle with the
same similarity as the mon it is on.

**The two hooks** (`particle_system.c`, ARM9 main; with no hook set, both are byte-for-byte the
old code):

```c
typedef BOOL (*ParticleSystemProjectionHook)(MtxFx44 *projection);
typedef void (*ParticleSystemParticleHook)(const VecFx32 *viewPos, const VecFx32 *anchorViewPos);
void ParticleSystem_SetProjectionHook(ParticleSystemProjectionHook hook);
void ParticleSystem_SetParticleHook(ParticleSystemParticleHook hook);
```

- `ParticleSystem_Draw` calls the projection hook with a copy of the system's projection, after
  `Camera_ComputeProjectionMatrix` and only when the system has a camera and is not screen space.
  The hook may change the copy, and returns TRUE to have the particle hook called for this draw.
- The particle hook gets each particle's centre and its emission point in the system's view space
  (the SPL library calls it through `SPLManager_SetParticleDrawHook`, before each particle and
  child particle is drawn), and may load its own projection. The closing `NNS_G3dGlbFlush`
  restores the system's.
- The battle sets both in `BattleStage_Init`, when there is an arena, and clears them in
  `BattleStage_Free`.

**At home**, and whenever the stage is not visible (a debug view held while the stage hides, the
classic look), the projection hook returns FALSE at once and leaves the matrix alone.

**The particle field** (`battle_stage_particles.c`, the default off home):

- Each battler on the field has the screen similarity its sprite uses ("Sprites follow the
  camera"): its home foot anchor, its foot anchor now and its scale.
- For a particle, the system's own projection gives its classic screen point p. Each battler gets
  the weight 1 / (d^2 + 16^2)^3, d the distance in pixels from p to the battler's body point (its
  home foot anchor raised 24 px). A battler whose d^2 + 16^2 is 32 times the nearest one's or more
  counts for nothing, so a particle near one mon takes that mon's similarity exactly; between the
  mons (a projectile in flight) the similarities blend smoothly.
- The field is evaluated at the point the particle was emitted from (its emitter's position at
  its birth, `SPLParticle.emitterPos`), and a particle within 32 px of that point moves rigidly with
  it, so the particles of one ball or burst hold together even between the mons, where the blend
  is not rigid. From 96 px on (a beam streaming from the attacker to the defender) a particle takes
  the field at its own place; in between the two blend smoothly.
- The particle lands at that point and is scaled by that scale, about its own centre: the
  projection loaded for it is the system's projection followed by the similarity in clip space
  (`x_ndc = x_px / 128 - 1`, `y_ndc = 1 - y_px / 96`, the translation scaled by w, so it holds for
  orthographic and perspective particle cameras alike).
- A projection is loaded only when it differs from the last one in the draw, so the particles of
  one group, or all snapped to one mon, share one load.
- A zoom alone (`StageCameraZoom`) is exact: every battler's similarity is then the same scale
  about the screen centre.

**Screen space.** A system marked screen space skips both hooks and keeps its classic place on
screen while the camera moves: full-screen weather, screen flashes. Scripts mark it with
`SetParticleScreenSpace particleSystem[, projection]` (command 62, `SetCameraProjection`, with
`BATTLE_ANIM_PARTICLE_SCREEN_SPACE` on the projection; it holds until the move ends), and C with
`ParticleSystem_SetScreenSpace`.

**Debug and A/B** (`debugFlags`, sBattleStage+32):

| bit | name | effect |
|---|---|---|
| 12 | `PARTICLES_2D` | the old single similarity: the focused battler's (`StageCameraMove` ATTACKER or DEFENDER), the midpoint for `BETWEEN`, the home camTarget for `CENTER`. It is also the fallback when no battler has an anchor |
| 13 | `PARTICLES_PLANE` | the 3D battle plane: each particle on the upright plane through both sides' feet where the home camera sees it, drawn with the stage view and projection in one projection matrix per system. The right mode if the mons are ever drawn in perspective (Gen 5's MCSS) |
| 14 | `KEEP_VIEW_IN_MOVES` | the move tester keeps its debug view (1-3) through the animation: an off-home test bed for any move's particles. The view still resets when the overlay hides |

**Budget.** No polygons are added (the same particles draw; off home some fall off screen and are
clipped). Off home, the field costs about 100-300 ARM9 cycles per particle and up to one 4x4
projection load per particle (18 geometry words), skipped while consecutive particles snap to the
same mon. The heaviest particle move measured, Draco Meteor, peaks at 830 polygons with the arena
(641 at the command menu, about 190 particles), under half of the 2048 the hardware takes; its
animation length is unchanged with the field (368 frames either way, within its own run-to-run
spread).

## New animation script commands

These are appended to `sBattleAnimScriptCmdTable`, as commands 85 to 91, with macros in
`asm/macros/btlanimcmd.inc`. The constants go in `include/constants/battle/battle_anim.h`.

The battle overlay isn't loaded in contests, so **each handler checks
`BattleAnimSystem_IsContest` first** and, in a contest, only skips its arguments. The handlers
also do nothing, apart from recording that the script used the camera, while the stage is not
visible.

| # | macro | arguments |
|---|---|---|
| 85 | `StageCameraMove focus, distancePct, yawDeg, pitchDeg, frames` | focus is `STAGE_CAMERA_FOCUS_CENTER` (0), `_ATTACKER` (1), `_DEFENDER` (2) or `_BETWEEN` (3). distancePct: 100 is home, smaller is closer. yawDeg: signed, positive swings the camera to the right like debug view 2. pitchDeg: signed, positive is higher. |
| 86 | `StageCameraOrbit yawDeltaDeg, frames` | adds yawDeltaDeg to the goal yaw, keeping focus, distance and pitch |
| 87 | `StageCameraShake amplitudePx, frames` | decaying shake on top of the pose |
| 88 | `StageCameraHome frames` | eases back to the home pose (0 snaps) |
| 89 | `StageCameraWait` | the script waits until no ease and no shake is in progress |
| 90 | `StageCameraZoom fovDeg, frames` | eases the vertical field of view to fovDeg degrees (clamped to 10-60; home is 40), keeping the rest of the pose. 0 eases back to the home fov. `StageCameraHome` restores it too (moves.md, "Per-move camera") |
| 91 | `StageHealthbars visible` | FALSE hides the healthbars showing now, for a close-up they would cover; TRUE shows again the ones the script hid. The script end shows any still hidden. Does nothing while the stage is not visible (moves.md, "Per-move camera") |

`frames` counts drawn frames, as `Delay` does. The first camera command of a script marks
the script as a **camera script**.

## The home guard

- **Script start.** When any animation script starts (a move, or a common animation such as
  the stat boost, the status anims and Mega Evolution), if the camera is not home it
  **snaps** home and `guardSnaps` increments. It also clears the camera-script mark.
- **Script end.** When a script ends and the camera is not home, the camera eases home over
  12 frames. Camera scripts should end with `StageCameraHome` and `StageCameraWait` so this
  never has to happen.
- **The invariant the critic checks.** On every drawn frame where a script is running, has
  not used a camera command and the camera is not home, `offHomeMoveFrames` increments.
  It must stay 0.

## Cinematics

Every cinematic sets its bit in `cinematicsSeen` when it starts, and runs only while the
stage is visible. The crit and faint kicks are skipped when `debugFlags` has `NO_CINEMATICS`.

**Battle intro** (bit 6, and bit 0 outside Totem battles; bw2vis:intro). The BW2 opening shots, the
fade-in without Platinum's curtain and platform slide, and the 2D trainer and ball OBJs scaling with
the camera are in intro.md. When they play, the battle-start focus below doesn't; it remains the
fallback (the stage wasn't visible at the opening, a recorded battle, Giratina's entrance).

**Battle-start focus** (bit 0)
- **When:** once per battle, when the opponent's healthbar first slides in
  (`BattleDisplay_SlideHealthbarIn`): the opponent's Pokemon is out and, in a trainer battle,
  its trainer has left.
- **Path:** from home, over 28 frames, swing onto the opponent's side (focus on the opponent,
  or the midpoint of both opponents in a double battle; yaw -20, pitch -3, distance 70%).
  Hold there until the player's side sends out, and for at least 30 frames; then ease home
  over 20 frames.
- **Released by:** the player's "Go! {0}!" lead message (`ov16_0225DEDC`), the player's
  trainer throw (`ov16_0225D360`), the opponent turning into an OBJ (the wild intro's
  `SpriteToOAM`), or the first command menu (Safari, Pal Park: nobody sends out).
- **Waits for it:** the player's trainer throw and `SpriteToOAM` wait until the camera is
  home (`BattleStage_IsIntroFocusDone`), with a 120-frame safety cap after which the camera
  snaps home. The OBJs of the player's trainer and ball, and the OAM copy of the opponent,
  can't follow the camera.
- **The player's healthbar waits too.** A trainer battle's script slides the player's
  healthbar in a fixed 96 frames after it issues the throw and doesn't wait for the throw
  (`subscript_start_encounter.s`: `ThrowPokeball`, `WaitTime 96`, `HealthbarSlideInDelay`).
  While the throw waited for the camera, the bar came in before the ball had left the
  trainer's hand. So the throw waits with `BattleStage_IsIntroThrowReady(battler)`, which
  counts the frames it waited, and `SlideHealthbarInTask` waits them out
  (`BattleStage_HoldSendOutHealthbar`) before the bar scrolls in: it comes in after the
  Pokemon, about as long after the throw as without the stage. Wild battles are unaffected:
  their `SpriteToOAM` waits, and the script waits on it before it issues the throw.
- **Trainer OBJs:** while the camera is off home, each trainer OBJ is drawn moved by its
  side's mean anchor offset (translation only), and moved back after the OBJ draw, so the
  game's position checks never see it.
- **Trainer OBJs over the arena:** the trainers (`BattlerData.unk_18`) and the Poke Balls
  they throw (`unk_84`) are OBJs at BG priority 2, under the 3D layer on BG0 (priority 1).
  Classic BG0 is empty around them, but the opaque arena covered them: on the stage no
  trainer showed during the send-out, the player's own back sprite and throw included, and
  neither did the defeated trainer coming back. While the stage is visible,
  `RaiseIntroSprites` (`ov16_0223B140.c`, every draw before the OBJs) lifts them to BG0's
  priority, which an OBJ wins over a BG: over the arena, still under the text box. The
  classic order (the mons over the trainers) never shows anyway, as a trainer has left
  before its Pokemon comes out of the ball. The balls draw from their own task, so they
  keep the raised priority (`BallRotation_GetSprite`); nothing reads it back.
- **Opponent healthbars:** an opponent's healthbar that slides in during the focus stays
  hidden, since it would cover the zoomed-in opponent (`BattleStage_HoldIntroHealthbar`). Its
  scroll still runs, because the battle waits on it. Once the camera is home (or the stage is
  hidden), the bar slides in again (`ReleaseHealthbars`, from `BattleStageCamera_Advance`).
- **Not played:** in Totem battles (their aura intro takes its place), if the stage isn't
  visible, or once the player's side has sent out (recorded battles send out first).

**Battle-start sweep** (bit 0), the fallback when the focus didn't play
- **When:** once per battle, when the first command menu of the battle is requested.
- **Not played:** after the focus, in Totem battles, or if the stage isn't visible.
- **Path:** the focus pose over 28 frames, hold for 10 frames, then ease home over 20 frames.
- **The command menu waits** until the camera is home, with a 90-frame safety cap after which
  the camera snaps home.

**Mega Evolution** (bit 1) is played by the Mega Evolution script with the new commands:
- before the charge, push in on the attacker over 10 frames (distance 70%, pitch -4);
- during the 36-frame charge, orbit 40 degrees;
- at the burst, shake by 4 px for 12 frames;
- ease home over 20 frames while the burst particles play, then `StageCameraWait` before
  `End`.

The AffinePulse sprite and the particles stay attached through the sprite and particle
follow (the particles take the attacker's own similarity, "Particles follow the camera"). Bit 1 is set by the Mega script, through its first camera command.

**Totem intro** (bit 2) is played by the Totem aura script:
- push in on the Totem over 16 frames (distance 72%, pitch -4);
- at the flare, shake by 3 px for 10 frames, then `StageCameraWait`;
- the script ends off home. `BattleStage_HoldCameraAfterScript` (called when the aura
  animation starts) turns the end pose into a held focus (`SEQUENCE_INTRO`), so the camera
  stays on the Totem through the "aura flared to life" message;
- the first command menu request releases it: ease home over 20 frames, and the menu waits
  for home as usual.

**Lone Totem layout.** Until it summons an ally, the Totem stands centre stage at x=192 (the
wild single spot) instead of its doubles spot at 216. `TotemBattle_HomeOffsetX` (-24 while
alone) is added to the encounter slide-in target and to the stage's `sHomeX`, and move
animations see the Totem as `BATTLER_TYPE_SOLO_ENEMY` (`TotemBattle_AdjustAnimTypes`). When
the ally is summoned, the Totem slides right over 16 frames while the ally fades in, and the
offset reaches 0. It stays on the right after that, even if the ally faints.

**Critical hit kick** (bit 3)
- **When:** the hit blink (`ov16_0225DA44`) starts on a battler that just took a critical
  hit.
- **Motion:** push 8% toward that battler over 4 frames, shake 3 px for 12 frames, then home
  over 10 frames. The whole kick lasts at most 24 frames and must never delay the battle.
- **Critic hook:** `debugFlags` bit `CRIT_KICK_ON_HIT` makes every hit blink play it.

**Faint kick** (bit 4)
- **When:** the fainting sequence (`ov16_0225DB74`) starts.
- **Motion:** dip 3 degrees in pitch toward the fainting battler over 6 frames, shake 2 px for
  10 frames, then home over 12 frames. At most 28 frames.

Any camera command from a script sets bit 5.

## Idle drift at the command menu

The Gen 5 look: while the command menu is up, the camera drifts slowly between a few poses.
It sets no `cinematicsSeen` bit.

- **Start:** `BattleStage_StartIdleCamera`, when the command menu task shows its buttons
  (`ov16_022604C8`, case 3). It only starts if the camera is home and idle: no script, no
  sequence, no ease, no shake, and neither `NO_CINEMATICS` nor `NO_IDLE_CAMERA` is set.
- **Loop (`SEQUENCE_IDLE`):** hold home for 60 frames, then ease to each pose over 180
  frames and hold it for 50 frames, round and round:
  1. the wide shot, yaw +10, pitch +2;
  2. focus 35% of the way to the opponent's side, yaw -14, pitch -2, distance 86%;
  3. focus 15% of the way to the player's side, yaw +12, pitch +1 (no push-in: a bigger back
     sprite makes the cut guard pan it off the bottom);
  4. back through near home, yaw -6.
- **The menu doesn't wait** for home while the drift runs (`BattleStage_IsCameraReadyForMenu`
  returns TRUE for `SEQUENCE_IDLE`).
- **End:** `BattleStage_EndIdleCamera`, when every battler's command is in
  (`battle_controller_player.c`, before `BattleSystem_RecordCommand`): ease home over 16
  frames. If the first animation script starts before that, the script start snaps home and
  this doesn't count as a guard snap. A hidden stage snaps home as usual.
- `NO_CINEMATICS` or `NO_IDLE_CAMERA` set mid-drift snaps the camera home.

## Debug fields in sBattleStage (read by the critic from RAM via the xMAP)

These come after the sprite fields. The existing offsets must not move.

| offset | field | meaning |
|---|---|---|
| +52 | `u32 camFlags` | bit0 `AT_HOME`, bit1 `EASING`, bit2 `SHAKING`, bit3 `CAMERA_SCRIPT` (the running script used a camera command) |
| +56 | `u32 cinematicsSeen` | the cinematic bits above; zeroed at battle load like every other field |
| +60 | `u32 guardSnaps` | times the guard snapped home at a script start |
| +64 | `u32 offHomeMoveFrames` | must stay 0 |
| +68 | `u32 offHomeFrames` | drawn frames with the camera not home |
| +72 | `s16 anchor[4][2]` | per battler: the current screen foot anchor (x, y) in pixels, updated every drawn frame while the stage is visible, even at home |
| +88 | `u16 anchorScale[4]` | per battler: s in 1/256 (256 at home) |

New `debugFlags` bits, next to the chunk 3 ones:
- bit3 `NO_CINEMATICS`: no crit or faint kicks. The sweep can't be switched off this way,
  because the flags are zeroed at battle load, before the critic can write them.
- bit4 `CRIT_KICK_ON_HIT`: every hit blink plays the crit kick.
- bit5 `NO_IDLE_CAMERA`: no idle drift at the command menu. The critic's `set_flags` sets it
  by default, so frame comparisons at the menu see the home frame.

## Budget

- The per-frame work is 4 projections plus a view rebuild while off home: trivial.
- There is no new VRAM.
- The new code lives in a new `src/battle/battle_stage_camera.c`, in the battle overlay,
  with its internal header next to `battle_stage_sprites.h`. The public calls go in
  `battle/battle_stage.h`.

## Critic checks

**Existing scenarios**
- **`stage_ab`:** still an exact match at day, taken at the command menu (after the sweep).
- **Frame counts:** every scenario that waits a fixed number of frames for the first command
  menu must allow for the sweep (about 60 frames longer).
- **`move_tester`:** after every move, `offHomeMoveFrames == 0` and `AT_HOME` is set at the
  menu.
- **`debug_views`:**
  - views 1 to 3 clear `AT_HOME` and move the anchors (they differ from view 0);
  - each sprite's feet land on its blob, within about 3 px in the contact sheet;
  - view 0 matches the old home frame.
- **`mega`:**
  - `cinematicsSeen` has bits 1 and 5;
  - frames mid-orbit differ from home, and the sprite anchor moves;
  - the camera is home (`AT_HOME`) before the following move's animation starts;
  - `offHomeMoveFrames == 0`;
  - the existing checks still pass.
- **`totem_battle`:** bit 2 is set, the sweep bit 0 is not, and the camera is home at the
  first command menu.

**New `camera` scenario** (Plain, wild battle, day)
- **The sweep (the battle-start focus):** bit 0 is set by the first command menu. During the
  intro at least one frame
  has `AT_HOME` clear and the opponent's anchor scale is above 256, and `AT_HOME` is set when
  the menu shows. Save a contact sheet of the sweep.
- **Crit kick:** with `CRIT_KICK_ON_HIT`, a damaging move sets bit 3. `AT_HOME` clears for at
  least a few frames and is back within 30 frames of the hit blink.
- **No kicks:** with `NO_CINEMATICS` instead, the same move leaves `offHomeFrames` unchanged
  after the move.
- **Faint:** a fainting (a KO of the wild mon, or whatever the debug party makes reliable)
  sets bit 4, and the camera is home again within 40 frames.
- **Idle drift:** with no flags, at the menu `AT_HOME` clears within 90 frames and the menu
  stays up (contact sheet `idle`). After a move is picked the camera is home within 40
  frames, `guardSnaps` doesn't rise and `offHomeMoveFrames == 0`.
