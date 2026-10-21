# 3D battle stage: camera system and cinematics (chunk 4)

This is the contract between the renderer (game C code) and the emulator critic
(`tools/battle_stage/emu/critic.py`). PLAN.md, chunk 4, has the goals. It builds on
arena.md (the arena and its home camera) and sprites.md (the stage sprites and blobs).

## The rule that matters most

**At the home pose nothing changes.** While the camera is home (the `AT_HOME` flag
below), every frame must be byte-for-byte what chunk 3 draws:

- the arena uses the view matrix it builds today;
- no sprite matrix is touched;
- the particle projection hook does nothing.

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

**Motion** (bw2vis camera-core: BW2's, `btlv_camera.c`):

- **The clock.** Eases and shakes run on BW2's 60 Hz clock: each is a function of the screen
  frames since it started. The camera advances once per `BattleStage_Draw` call (while the arena
  exists, whether or not the stage is visible), which is two screen frames at the battle's 30 Hz
  (`STEP_FRAMES`). BW2's frame counts are used as they are; a script's drawn frames are doubled.
  "Update rate" below has why the camera stays at 30 Hz.
- **BW2's curve, the default** (`CURVE_LINEAR`, `BtlvCamera_MoveTo` and `BtlvEffTool_CalcStepVec`):
  the camera position and the target each move in a straight line at constant speed, so a turn
  takes the chord (C7). An optional brake halves the speed after `brake - 1` frames (BW2's
  `brakeFrames`, `btlv_camera.c:185-204`): BW2's command prompt zoom, 10 frames with brake 8, is 7
  frames at full speed and 6 at half speed, 13 in all. With no brake the camera starts and stops
  dead. The pose is rebuilt from the interpolated position each frame (`PoseAnglesFromOffset`), so
  everything downstream (shake, anchors, cut guard) still works on poses.
- **Smoothstep** (`CURVE_SMOOTH`): (3t^2 - 2t^3) on each pose component, so a turn takes the arc.
  The chunk 4 cinematics the intro workstream owns (the battle-start focus and sweep, the Totem
  aura's held pose going home) still use it through `EaseTo`; scripts get it with
  `STAGE_CAMERA_SMOOTH`.
- N = 0 snaps to the goal pose. A new command starts from wherever the camera is at that moment,
  so there is no jump.
- **Shake** is added on top. **BW2's shake, the default** (`BtlvCamera_Shake`, `BtlvEffTool_Move`
  type 3): a triangle wave of the full amplitude on one world axis (up by default, or sideways along
  the ground), `count` whole swings of 4 quarters, starting at rest and ending exactly at rest, so it
  keeps its strength to the end and stops dead. The amplitude is in screen pixels converted to world
  units at the focus depth. A quarter is 4 screen frames (2 drawn frames) unless the script says
  otherwise, so even sampled at 30 Hz it is seen to start from rest (half the amplitude, then all
  of it). The old shake (decaying sines on both screen axes) is `STAGE_CAMERA_SHAKE_DECAY`; its
  vertical sine used to start at full amplitude (a cosine), a one-frame jump on every shake (C5),
  and now starts at 0 too. Every shake is deterministic, never random, and a shake with a pose at
  home ends exactly at home.

**Framing** (bw2vis camera-core, C6). A `StageCameraMove` with a battler focus (attacker or
defender) is BW2's attacker or defender preset (`CmdCameraMovePreset` types 9-12, which resolve to
the battler's slot preset, `btlv_effvm.c:468-505`): the home camera trucked onto the mon with no turn
(the script's yaw and pitch are dropped) at BW2's size for that slot, with its feet where BW2's
camera puts them:

| slot | BW2 preset | size against home | feet on row |
|---|---|---|---|
| single battle, your mon | 0 | 0.91x | 124 |
| single battle, the foe | 1 | 1.50x | 113 |
| double battle, your left / right mon | 2 / 4 | 1.19x / 1.06x | 125 / 139 |
| double battle, the right / left foe | 3 / 5 | 1.47x / 1.49x | 111 / 104 |

The sizes are the ratio of the mon's distances to BW2's home and preset cameras (the gap audit's
measure). The rows are where BW2's camera (fovy 26, aspect 1.35) projects the mon's feet, as the same
share of our scene, which ends at the text box (row 144) where BW2's ends at the screen's bottom.
Across, BW2 puts your mon at x 113-123 and the foe at 133-135; ours stand at x 96 and 152, where
Platinum's bigger healthbar boxes (yours from x 136, the foe's up to x 128) leave them clear.
The old framing pushed your own mon to 1.46x and turned 6-12 degrees; the foe's side was already at
1.46x. `TruckGoal` solves the distance for the size from the foot's home depth, then raises the camera
and its focus together until the feet sit on the row. `STAGE_CAMERA_FREE` on the focus keeps the old
free framing (the script's distance, yaw and pitch), as the Mega Evolution and Totem aura scripts do.

**Camera range.** Every pose the camera now takes was checked with BG0 renders (magenta where the
arena draws nothing) on all 30 quick-battle arenas: the prompt shots, the 6 idle shots (start and
end), the wide shot, 1.12x to 1.6x the home distance, yaw -20 at 1.12x and pitch -6. All are clean
(at most 0.01% at pitch -6 on one arena). `CAMERA_MAX_DISTANCE` is 1.45x.

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

`particle_system.c` (ARM9 main) gets a projection hook, the same pattern as the sprite draw
hook:

```c
typedef void (*ParticleSystemProjectionHook)(MtxFx44 *projection);
void ParticleSystem_SetProjectionHook(ParticleSystemProjectionHook hook);
```

- In `ParticleSystem_Draw`, after `Camera_ComputeProjectionMatrix` and only when the system
  has a camera: if a hook is set, read `NNS_G3dGlbGetProjectionMtx()`, let the hook modify a
  copy, and put it back with `NNS_G3dGlbSetProjectionMtx`.
- With no hook set, the function is byte-for-byte the old code.
- The battle sets the hook in `BattleStage_Init`, when there is an arena, and clears it in
  `BattleStage_Free`.

The hook post-multiplies the projection by the screen-space similarity of the camera's
**particle focus**, turned into clip space: `x_ndc = x_px / 128 - 1`, `y_ndc = 1 - y_px / 96`,
and the translation is multiplied by w, so it works for orthographic and perspective
particle cameras alike. The focus depends on the command:

- `StageCameraMove` with a battler focus: that battler's similarity;
- `CENTER`: the similarity of the home camTarget point;
- `BETWEEN`: the midpoint of the two battlers' anchors, with the mean of their scales.

When the camera is home, the hook returns at once and leaves the matrix alone. Every battle
particle system goes through it, including the Totem aura's own system.

## New animation script commands

These are appended to `sBattleAnimScriptCmdTable`, as commands 85 to 91, with macros in
`asm/macros/btlanimcmd.inc`. The constants go in `include/constants/battle/battle_anim.h`.

The battle overlay isn't loaded in contests, so **each handler checks
`BattleAnimSystem_IsContest` first** and, in a contest, only skips its arguments. The handlers
also do nothing, apart from recording that the script used the camera, while the stage is not
visible.

| # | macro | arguments |
|---|---|---|
| 85 | `StageCameraMove focus, distancePct, yawDeg, pitchDeg, frames` | focus is `STAGE_CAMERA_FOCUS_CENTER` (0), `_ATTACKER` (1), `_DEFENDER` (2) or `_BETWEEN` (3). distancePct: 100 is home, smaller is closer. yawDeg: signed, positive swings the camera to the right like debug view 2. pitchDeg: signed, positive is higher. A battler focus is BW2's preset for its slot and ignores the three ("Framing") unless the focus has `\| STAGE_CAMERA_FREE` |
| 86 | `StageCameraOrbit yawDeltaDeg, frames` | adds yawDeltaDeg to the goal yaw, keeping focus, distance and pitch. BW2's curve turns along the chord (the camera dips toward the focus mid-turn), `STAGE_CAMERA_SMOOTH` along the arc |
| 87 | `StageCameraShake amplitudePx, frames` | BW2's shake on top of the pose: vertical, full strength, whole swings (frames is rounded up to them). `amplitudePx \| STAGE_CAMERA_SHAKE_X` shakes sideways, `\| STAGE_CAMERA_SHAKE_DECAY` is the old decaying shake; `frames \| STAGE_CAMERA_SHAKE_QUARTER(n)` makes a quarter swing n drawn frames (default 2) |
| 88 | `StageCameraHome frames` | eases back to the home pose (0 snaps) |
| 89 | `StageCameraWait` | the script waits until no ease and no shake is in progress |
| 90 | `StageCameraZoom fovDeg, frames` | eases the vertical field of view to fovDeg degrees (clamped to 10-60; home is 40), keeping the rest of the pose. 0 eases back to the home fov. `StageCameraHome` restores it too (moves.md, "Per-move camera") |
| 91 | `StageHealthbars visible` | FALSE hides the healthbars showing now, for a close-up they would cover; TRUE shows again the ones the script hid. The script end shows any still hidden. Does nothing while the stage is not visible (moves.md, "Per-move camera") |

`frames` counts drawn frames, as `Delay` does, in its low byte. Every frames word of 85, 86, 88
and 90 takes BW2's motion by default; `| STAGE_CAMERA_BRAKE(n)` adds BW2's half-speed tail after
n - 1 drawn frames (BW2's frames and brakeFrames count 60 Hz frames: halve both, so BW2's 10 / brake
8 is `5 | STAGE_CAMERA_BRAKE(4)`), and `| STAGE_CAMERA_SMOOTH` is the old smoothstep. The options ride
in the existing words (`constants/battle/battle_anim.h`), so no command changed its arguments and
every existing script still assembles. The first camera command of a script marks the script as a
**camera script**.

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
- before the charge, push in on the attacker over 10 frames with BW2's tail from frame 7 (distance
  70% on the foe's side, 42% and pitch -8 on yours; `STAGE_CAMERA_FREE` keeps this shot rather than
  BW2's preset, which pulls back from your mon);
- during the 36-frame charge, orbit 40 degrees along the chord (BW2's CameraRotate: the camera dips
  about 6% toward the Pokemon mid-turn, so it grows a little and settles);
- at the burst, BW2's shake by 4 px (12 frames, rounded up to 2 whole swings);
- ease home over 20 frames with a tail from frame 14 while the burst particles play, then
  `StageCameraWait` before `End`.

The AffinePulse sprite and the particles stay attached through the sprite and particle
follow. Bit 1 is set by the Mega script, through its first camera command.

**Totem intro** (bit 2) is played by the Totem aura script:
- push in on the Totem over 16 frames with BW2's tail from frame 11 (distance 72%, pitch -4,
  `STAGE_CAMERA_FREE`);
- at the flare, BW2's shake by 3 px (2 whole swings), then `StageCameraWait`;
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
- **Motion:** push 8% toward that battler over 4 screen frames at constant speed, with one swing
  of BW2's 3 px shake (16 screen frames) from the start, then home over 8. The whole kick lasts 24
  screen frames and must never delay the battle. (Not in Gen 5: BW2's damage reaction is a tint.)
- **Critic hook:** `debugFlags` bit `CRIT_KICK_ON_HIT` makes every hit blink play it.

**Faint kick** (bit 4)
- **When:** the fainting sequence (`ov16_0225DB74`) starts.
- **Motion:** dip 3 degrees in pitch toward the fainting battler over 6 screen frames, with one
  swing of BW2's 2 px shake (16), then home over 12 with a tail from frame 8 (17). 33 screen frames.

Any camera command from a script sets bit 5.

## Command menu camera (bw2vis camera-core; BW2's, `btlv_input.c`, `btlv_effect.c`)

It sets no `cinematicsSeen` bit. Everything here is off while `NO_CINEMATICS` or `NO_IDLE_CAMERA`
is set, and either flag set while it runs snaps the camera home (the critic sets `NO_IDLE_CAMERA`
by default, so its frame comparisons at the menu see the home frame).

- **The prompt (E4).** Every command prompt (`ov16_022604C8` case 3,
  `BattleStage_StartIdleCamera(battler)`) eases onto the battler whose command is being picked, as
  BW2's `BtlvInput_StartFingerCursor` does: `BtlvEffect_ZoomCamera`, a MoveTo of 10 frames with brake
  8. BW2 plays effect 0x23f (doubles: 0x240 / 0x241) there, whose camera data isn't extracted; the
  shot is the slot's BW2 preset ("Framing"): your mon at 0.91x in a single battle, 1.19x / 1.06x for
  your left / right mon in a double battle, re-aimed when the next battler's prompt opens. It starts
  from home (the menu still waits for home first) or from the previous battler's prompt.
- **Move and target select in a double battle (E6).** Move select (`ov16_02260C00`) eases to BW2's
  wide doubles shot over the same 10 frames with brake 8 and restarts the idle wait, as BW2's
  `RestartIdleEffect(2)` with effect 0x244 does (its data isn't extracted; the shot is BW2's preset
  14: from the home target, pulled back until your mons are 0.68x, which leaves the foes at about
  0.79x; BW2's are 0.65-0.70x and 0.81x). Target select (`ov16_02260F14`) keeps it. A single battle's
  move list keeps the prompt shot and its wait, as in BW2. Back at the command menu, the prompt plays
  again.
- **The idle shots (E5).** 900 screen frames (15 s) after the prompt (BW2's `idleEffectWait`; a
  double battle's move select restarts the wait), the idle shots start and follow one another
  until the commands are in. BW2 picks one of 6 idle effect scripts (0x235, 0x24c-0x250) at random,
  never the same twice in a row; their camera data isn't extracted, so the 6 shots here are built
  from BW2's camera grammar (preset slides, chord turns, the trucked home pose of preset 18): each
  is a cut to a start pose and a slow move at constant speed to an end pose, then a short hold
  (screen frames):

  | # | shot | move | hold |
  |---|---|---|---|
  | 0 | the foe, a slow push from 1.25x to its preset size (1.50x) | 240 | 60 |
  | 1 | your mon at its preset size, sliding 45% of the way from home toward your side | 240 | 60 |
  | 2 | a slow turn across the field about the home target, yaw -16 to +16 | 300 | 45 |
  | 3 | a low turn about the foe at 1.2x, yaw +10 to -10, pitch -3 | 240 | 45 |
  | 4 | BW2's preset 18: the home pose trucked from 30% toward the foes to 30% toward your side | 300 | 45 |
  | 5 | over the field from your side (yaw +8, pitch +2) to a high look at the foe (yaw -6, pitch +4) | 240 | 60 |

  In a double battle the foe shots frame both foes at 1.25x. The random numbers are a private LCG
  seeded at battle load, so the battle's own RNG (and a recorded or linked battle) never sees them.
- **The menu doesn't wait** for home while any of these runs (`BattleStage_IsCameraReadyForMenu`
  returns TRUE for `SEQUENCE_PROMPT`, `SEQUENCE_SELECT` and `SEQUENCE_IDLE`).
- **End:** `BattleStage_EndIdleCamera`, when every battler's command is in
  (`battle_controller_player.c`, before `BattleSystem_RecordCommand`): ease home over BW2's 10
  frames with brake 8 (BW2 plays its return effect 0x236 there). If the first animation script
  starts before that, the script start snaps home and this doesn't count as a guard snap. A hidden
  stage snaps home as usual; the bag and party screens keep the stage up, so the menu camera runs
  on under them.

## Beats after the first prompt (bw2vis camera-core)

The first command prompt of a battle opens the beats (the battle start is the intro workstream's).
BW2 plays an effect script for each: the recall 0x26C and send-in 0x26D (`BtlvScu_StartMemberOut`
/ `MemberIn`), the ball 0x23a, the trainer's return 0x270. Their camera data isn't extracted, so
these are BW2-like. Each eases in at constant speed (16 screen frames, brake 12), holds, and eases
home (20, brake 14). Each is skipped with `NO_CINEMATICS`, a hidden arena or a running anim script
(and snapped home if one starts, which isn't a guard snap), and the next command menu sends a beat
still holding home (the menu then waits for home as usual).

The Poke Balls and the trainers are 2D OBJs. They follow their side's mean similarity (the intro
workstream's `BattleStage_FollowIntroSprite` and ball draw hook: moved and scaled, up to 2x), not
their own battler's, and their flights are screen paths drawn for home. So the beats keep the
battler's feet where they stand:

- **Switch (E7).** A recall (`ov16_0225D118`) closes in on the battler along the ray from the home
  camera through its feet (`DollyGoal`): its feet keep their screen point, so the recall ball's and
  the send-in ball's paths still end on it, and it grows to 1.12x (your side) or 1.35x (the foe's). The send-in
  (`ov16_0225CF70`) stays there (or closes in, after a faint) and holds until the new battler's
  healthbar is in, then 24 frames more. A recall with no send-in gives up after 300 frames. The
  Totem's summoned ally keeps its own entrance.
- **Ball throw and catch (E12).** The throw plays at home. When the ball opens on the foe
  (`ov16_0225D1C4`) the camera closes in on it (1.35x, the same ray), so the ball keeps its place on
  the platform through the shakes. A break-free sends the Pokemon out again: the send-in beat takes
  over and lets go. A catch holds until the battle ends. The ball grows with the foe's side.
- **End of a trainer battle (E13).** When the defeated trainer slides back in (`ov16_0225D414`), the
  camera trucks over to the foes' side at home size (`TruckGoal` at 1.0x, feet on row 113, x 152), so
  the trainer OBJ slides in to where it stands, and holds until the battle ends.

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
- bit5 `NO_IDLE_CAMERA`: no command menu camera (the prompt shot, the doubles select shot, the idle
  shots). The critic's `set_flags` sets it
  by default, so frame comparisons at the menu see the home frame.

## Debug launcher: a double battle (bw2vis camera-core)

In the field, L+R opens the quick-battle panel; B steps the X battle through the Totem encounters
and then "X: Doubles" (the 10th choice), and X starts a plain wild double battle against the
selected species and the next one (`Encounter_NewVsDoubleSpeciesAtLevel`). The panel's background
and time of day apply as for A. (Y is the gym leader battle, from battle-events.)

## Debug block (bw2vis camera-core)

`sStageCameraDebug` (battle_stage_camera.c, `StageCameraDebug`, 124 bytes, in the xMAP) holds the
camera's state for the critic and the capture scripts, all s32: `magic` (0x4D414343 once set up),
`sequence` (0 none, 1 to, 2 hold, 3 intro, 4 idle, 5 prompt, 6 select, 7 beat), `curve` (0 BW2, 1
smoothstep), `brake`, `easeT`, `easeEnd` (screen frames; 0 when not easing), `shakeMode` (0 vertical,
1 sideways, 2 decay), `shakeAmp`, `shakeT`, `shakeEnd`, `promptBattler` (-1 before the first prompt),
`idleShot` (-1 for none), `idleTimer`, `beat` (0 none, 1 recall, 2 send-out, 3 catch, 4 end), `flags`
(bit 0: the first prompt has opened), the pose (`yaw`, `pitch` in fx32 degrees, `distance` in fx32,
`focusX/Y/Z` relative to the home target), `progress` (fx32 0..1 of the ease), `advanceTicks` and
`advanceTicksMax` (OS ticks of the last and the longest `BattleStageCamera_Advance`), then a test
hook: `forcePose` 1 shows the pose `forceFocusX/Y/Z`, `forceYaw`, `forcePitch` (fx32 degrees),
`forceDistance` (fx32, 0 = home) like a debug view; 0x100 + n starts idle shot n now; 0x200 + n
cuts to its end pose.

## Budget

- The per-frame work is 4 projections plus a view rebuild while off home: about 150-260 OS ticks
  (0.3-0.5 ms) per `BattleStageCamera_Advance` off home in DeSmuME (`advanceTicksMax`), against a
  33 ms frame.
- There is no new VRAM.
- The new code lives in a new `src/battle/battle_stage_camera.c`, in the battle overlay,
  with its internal header next to `battle_stage_sprites.h`. The public calls go in
  `battle/battle_stage.h`.

## Update rate (C3, bw2vis camera-core)

BW2 steps its camera every 60 Hz frame; ours steps once per `BattleStage_Draw`, which is 30 Hz,
because the whole battle (its logic and its 3D frame: arena, mons and particles, swapped with
`G3_RequestSwapBuffers` in `ov16_0223CF48`) runs at 30 Hz. A 60 Hz camera needs a second 3D frame
per logic frame. Measured on a probe build (`main.c` and `ov16_0223CF48` timed with `OS_GetTick`,
not committed; DeSmuME's timing model, which isn't cycle-exact, so hardware is likely slower):

| scene | work per 30 Hz frame, mean / max (ms) | 3D part of the draw, mean / max (ms) | swap requested after the vblank, max (ms) |
|---|---|---|---|
| single battle, command menu | 8.3 / 10.4 | 3.7 / 5.8 | 10.4 |
| single battle, 9 moves (Shadow Ball, Earthquake, Blizzard, Fire Blast, Hyper Beam, Thunder, Psychic, Swords Dance, Tackle) | 9.5-12.6 / 89-107 * | 1.8-4.8 / 5.6-7.9 | 89-107 * |
| Totem double battle, command menu | 10.0 / 13.0 | 5.3 / 8.4 | 13.0 |
| Totem double battle, 3 moves | 10.9-13.4 / 89-92 * | 4.1-6.3 / 7.4-10.7 | 89-92 * |

\* the first frames of each animation load its resources: 3-6 frames per move overrun the vblank.

A 60 Hz camera would cost a second submission of the 3D part, 2-11 ms more per 33 ms, which has to
land in the 16.7 ms between the two vblanks of a logic frame. On these numbers it fits on average
(about 5 ms to spare in a double battle's moves, in DeSmuME) but not in the loading frames, and it
needs a draw-only path in four systems that advance state while they draw today: the mon sprites
tick their animations in `PokemonSpriteManager_DrawSprites`, the particles run
`ParticleSystem_UpdateAll` after `ParticleSystem_DrawAll`, `BattleStage_Draw` advances the fade,
the platforms and the idle animation, and the 2D OBJs that follow the camera (trainers, balls)
would still move at 30 Hz against a 60 Hz arena. **Decision: the camera stays at 30 Hz.** Its
motion runs on BW2's 60 Hz clock (`STEP_FRAMES`), sampled every second frame, so a 60 Hz redraw,
if it comes, only has to advance the camera by one screen frame instead of two.

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
- **`totem_battle`:** bit 2 is set, the sweep bit 0 is not, and the camera is home at the first
  command menu, or on the command prompt shot, which starts from home (`StageRam.menu_camera`, from
  `sStageCameraDebug.sequence`).

**New `camera` scenario** (Plain, wild battle, day)
- **The sweep (the battle-start focus):** bit 0 is set by the first command menu. During the
  intro at least one frame
  has `AT_HOME` clear and the opponent's anchor scale is above 256, and `AT_HOME` is set when
  the menu shows (or the command menu camera is on: the prompt shot starts from home). Save a
  contact sheet of the sweep.
- **Crit kick:** with `CRIT_KICK_ON_HIT`, a damaging move sets bit 3. `AT_HOME` clears for at
  least a few frames and is back within 30 frames of the hit blink.
- **No kicks:** with `NO_CINEMATICS` instead, the same move leaves `offHomeFrames` unchanged
  after the move.
- **Faint:** a fainting (a KO of the wild mon, or whatever the debug party makes reliable)
  sets bit 4, and the camera is home again within 40 frames.
- **Idle drift** (now the command menu camera): with no flags, at the menu `AT_HOME` clears
  within 90 frames (the prompt shot clears it at once) and the menu stays up (contact sheet
  `idle`). After a move is picked the camera is home within 40 frames, `guardSnaps` doesn't rise
  and `offHomeMoveFrames == 0`.
