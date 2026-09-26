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

These are appended to `sBattleAnimScriptCmdTable`, as commands 85 to 89, with macros in
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

**Battle-start sweep** (bit 0)
- **When:** once per battle, when the first command menu of the battle is requested. By then
  both sides' Pokemon are out and every trainer sprite, which is a 2D OBJ that can't follow
  the camera, has left.
- **Not played:** in Totem battles (their aura intro takes its place), or if the stage isn't
  visible.
- **Path:** from home, over 28 frames, swing onto the opponent's side (focus on the opponent,
  or the midpoint of both opponents in a double battle; yaw -20, pitch -3, distance 70%).
  Hold for 10 frames, then ease home over 20 frames.
- **The command menu waits** until the camera is home, with a 90-frame safety cap after which
  the camera snaps home.

**Mega Evolution** (bit 1) is played by the Mega Evolution script with the new commands:
- before the charge, push in on the attacker over 10 frames (distance 70%, pitch -4);
- during the 36-frame charge, orbit 40 degrees;
- at the burst, shake by 4 px for 12 frames;
- ease home over 20 frames while the burst particles play, then `StageCameraWait` before
  `End`.

The AffinePulse sprite and the particles stay attached through the sprite and particle
follow. Bit 1 is set by the Mega script, through its first camera command.

**Totem intro** (bit 2) is played by the Totem aura script:
- push in on the Totem over 16 frames (distance 72%, pitch -4);
- at the flare, shake by 3 px for 10 frames;
- ease home over 16 frames, then `StageCameraWait`.

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
- **The sweep:** bit 0 is set by the first command menu. During the sweep at least one frame
  has `AT_HOME` clear and the opponent's anchor scale is above 256, and `AT_HOME` is set when
  the menu shows. Save a contact sheet of the sweep.
- **Crit kick:** with `CRIT_KICK_ON_HIT`, a damaging move sets bit 3. `AT_HOME` clears for at
  least a few frames and is back within 30 frames of the hit blink.
- **No kicks:** with `NO_CINEMATICS` instead, the same move leaves `offHomeFrames` unchanged
  after the move.
- **Faint:** a fainting (a KO of the wild mon, or whatever the debug party makes reliable)
  sets bit 4, and the camera is home again within 40 frames.
