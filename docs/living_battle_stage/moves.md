# 3D battle stage: per-move redo (chunk 6)

This is the contract for chunk 6 between the move fixers and the emulator critic
(`tools/battle_stage/emu/critic.py`). PLAN.md, chunk 6, has the goal; compat.md has the
chunk 5 machinery (suppression, the F1 BG2 lift, the F2 sprite tint, the F6 fade).

## Where things stand

After chunk 5, a move that changes the backdrop fades the arena out, shows the classic BG3
backdrop for as long as it lasts, then fades back in. Nothing breaks, but the scene goes
flat for those moves, and three kinds of effect are still wrong or lost:

- **The effect is lost.** Some moves fade the BG3 palette (`Func_FadeBg FADE_BG_TYPE_BASE`,
  `Func_SetBgGrayscale`). The arena covers BG3, so the dimming never shows (Night Shade,
  Dark Pulse, Explosion, Outrage, Aura Sphere, and more; move_audit.md, notes "FadeBg" and
  "SetBgGrayscale").
- **The arena fades for something it could do itself.** About 25 moves shake BG3
  (`ShakeBg`, Earthquake, Magnitude, Fissure). Today any BG3 offset suppresses the arena.
- **The effect only exists in 2D.** Fake Out's curtain, the Superpower and Camouflage
  pictures, Surf's and Muddy Water's water, and Dig's hole are 2D tricks the arena fades
  away for.

Chunk 6 keeps the arena on screen for these moves and makes the effect read on it.

**The rules from compat.md still hold.** With no effect running, day at home stays
byte-identical (`stage_ab`). A script end must leave the arena at alpha 31, the camera home
and the sprites as the move intended. Contests never touch the stage: keep the
`BattleAnimSystem_IsContest` guards.

**A move whose backdrop really changes** (SwitchBg to a picture: Psychic, Hyper Beam,
Moonlight and so on) keeps the chunk 5 fade. That is the intended look, not a chunk 6 item.

## Categories

Each category is one fixer on its own branch. Each fixer lists its moves in its own redo
file (below), so the critic knows what to expect.

### A. shake: BG3 offsets become stage camera offsets

`BattleAnimSystem_UpdateStageSuppress` counts any BG3 x/y offset as `BG_SWITCH`. Instead,
while BG3 still shows the normal backdrop (no SwitchBg, no bgAnim, normal effect BG), the BG3
offset shifts the stage camera by the same number of pixels, and the arena stays up.

- Add `void BattleStage_SetBackdropShake(int dx, int dy)` (pixels, BG scroll sign: the
  picture moves by (-dx, -dy)). Apply it in battle_stage_camera.c the way `ShakePixels`
  already shifts the camera, added to any running shake.
- The arena, the stage sprites and the particles move together, so the mons stay on their
  platforms. Classic BG3 shook under fixed mons; shaking everything reads better.
- A mirrored shake must not count as off home: `offHomeFrames` and `offHomeMoveFrames` stay
  unchanged, so the `camera` and `switchbg_moves` checks still pass. `BATTLE_STAGE_CAMERA_SHAKING`
  may be set.
- The offset is dropped when it returns to 0, when another reason suppresses the arena, and
  at the latest when the script ends.
- Earthquake, Magnitude and Fissure also get a bigger stage shake than the BG3 scroll. Use
  camera command 87 (`CameraShake`) in their anim.s or scale the mirrored offset.
- When the move also switches or fades the backdrop, the other reason still applies.

### B. backdrop_fade: palette fades of the backdrop reach the arena

`Func_FadeBg` with `FADE_BG_TYPE_BASE`, `Func_SetBgGrayscale` and any other BG3 palette fade
or tint the audit finds should also fade the arena towards the same colour by the same amount.

- Generalize `BattleStage_SetBrightness` (a flat fog table, black or white) to any colour
  and amount. Suggested: `void BattleStage_SetBackdropFade(u16 color, int alpha)`, with alpha
  0..16 as the palette fade. Grayscale may use a fog towards the average arena colour, or
  whatever reads closest to the classic look.
- Feed it from the palette-fade code the moves use, by patching the anim funcs or reading
  the BG3 palette fade state each frame. Pick whichever is less fragile.
- It must not stack with the Mega brightness. Mega wins while it is set.
- Night Shade and Dark Pulse then darken the arena. `switchbg_moves` must stop expecting a
  fade for them and expect the arena to stay visible and darken instead. Update that check.

### C. silhouette: Fake Out, Superpower, Camouflage

These moves shape BG3 or a BG2 picture with a window. Today (move_audit.md, "F3: window
decisions", option b) they suppress and fade.

- Make each of them work with the arena up, for example:
  - **Superpower and Camouflage:** lift BG2 above BG0 inside the OBJ window, like F1.
  - **Fake Out:** a curtain on a layer above BG0, such as BG2 or OBJ, or a stage-side
    curtain drawn in 3D.
- Choose per move and write the choice in move_audit.md.
- Keep the `BATTLE_STAGE_SUPPRESS_WINDOW` path for any window user you don't redo.

### D. water_ground: Surf, Muddy Water, Dig

- **Muddy Water** puts a full-screen picture on BG2 blended over BG0|BG3. Lift BG2 above
  BG0 for it (compat.md F4: BG0 as a 2nd target is fine) so the water washes over the lit
  arena.
- **Surf:** the same approach for its wave, or a UV-scrolled 3D water plane if the 2D one
  can't be lifted.
- **Dig:** today the digger is clipped (partial draw) against the platform line. Keep the
  clip and draw a dark hole decal on the arena ground under the digger while it is
  underground, so the mon visibly goes into the ground.
  - Dig's first turn and its attack turn are different anim scripts; handle both.
  - The decal must go away at the end of the script.

### E. critic tools (the `move_redo` scenario)

See the critic section below.

### Out of scope

Fly's low angle, Double Team depth and the other optional stage upgrades in PLAN.md. They
come later if the user wants them.

## Redo files

Each fixer writes `docs/living_battle_stage/redo/<category>.json`, a list with one object
per move it touched:

```json
{"id": 89, "name": "EARTHQUAKE", "category": "shake",
 "expect": "kept",
 "needs": [],
 "min_change_pct": 3,
 "effect": "arena, mons and particles shake together; no fade"}
```

- **expect:**
  - `kept`: the arena never hides for this move. `fades`, `hiddenFrames` and `hardPops`
    stay unchanged during it.
  - `fade`: the move still fades, for another reason; `effect` says why.
- **needs:** the other categories this move also needs before it can be `kept`. Explosion,
  for example, both shakes and fades the backdrop, so it needs `shake` and `backdrop_fade`.
  On a branch without those, the critic reports such a move as info, not as a failure.
- **min_change_pct:** optional. The effect is judged visible when at least this much of
  the scene (HUD masked) differs from the pre-move frame at some point. The default is 3.
- **effect:** one line saying what should be seen. The critic agent reads it.

## Critic checks (new scenario `move_redo`)

`move_redo` plays every move in `docs/living_battle_stage/redo/*.json`, or the `--moves`
list, from the move tester on a Plain battle, at day and again at night. It uses
`FREEZE_IDLE|NO_CINEMATICS` like move_audit.

Per move, it checks:

- The animation finishes, and the normal look is restored 90 frames later.
- `hardPops` does not rise.
- `arenaAlpha` is 31 after the move, and the camera is home (AT_HOME) at the menu.
- For `expect: kept`:
  - `fades` and `hiddenFrames` do not rise.
  - The effect is visible: the maximum scene change reaches `min_change_pct`.
  - If `needs` names a category whose redo file is missing, the check is reported as info.
- For `expect: fade`: `fades` rises.
- No CPU exceptions.

It also writes a side-by-side contact sheet per move and time of day,
`move_redo/<id>_<tod>.png`:

- Top row: the stage frames at fixed offsets across the animation (about 8, from the first
  frame after L+R+A to the end).
- Bottom row: the same move at the same offsets with the stage off (the debug A/B toggle),
  i.e. the classic look.
- `move_redo/index.png` lists all the moves at a small size.

A critic agent compares the rows. The stage version should read as the same effect as the
classic one, only on the 3D arena.

The existing scenarios must still pass: `stage_ab`, `move_audit`, `move_tester`,
`switchbg_moves` (with category B's update), `sprite_life`, `camera`, `mega` and
`totem_battle`.

## Per-move camera

Eight moves move the stage camera with the move, in the Black/White pattern. Every other move
still plays at the home pose.

**The pattern:**

1. Wind-up: `StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER` over 8-10 frames.
2. Launch: `StageCameraMove` to `DEFENDER`, or to `BETWEEN` for a projectile in flight.
3. Impact: `StageCameraShake` on the hit.
4. End: `StageCameraHome 12` and `StageCameraWait` before `End`, so the script hands the camera
   back at home.

**Distance by side.** `distancePct` is measured from the focus point, not from the home camera.
A mon on the player's side stands nearer the camera than the home focus, so 85% from it frames
it smaller than at home. A mon on the enemy's side stands farther away, so 85% from it is a
push-in. Every close-up on the attacker or the defender therefore picks its distance with
`JumpIfBattlerSide`, whose first address is taken when the battler is on the player's side:

```
    JumpIfBattlerSide BATTLER_ROLE_ATTACKER, L_1, L_2
L_1:
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 48, 6, 0, 8    // player side
    Jump L_3
L_2:
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 85, 6, 0, 8    // enemy side
L_3:
```

On the Plain stage, 48% frames the player's mon at about 1.46x its home size, and 85% frames the
enemy's mon at about 1.46x (82% about 1.5x, 88% about 1.41x). 85% on the player's side gave
0.84x, smaller than home. These are the battler's anchor scale (`anchorScale`, 256 = home) read
from RAM through both `move_redo` runs (see Checking). `BETWEEN` frames the midpoint and needs
no branch.

The macro's comment in `btlanimcmd.inc` had the two addresses the wrong way round (enemy first).
The handler, `BattleAnimScriptCmd_JumpIfBattlerSide`, skips to the second address for a battler
on the enemy's side, and vanilla scripts such as Surf rely on that. The comment and the
parameter names now say player first; the bytes are unchanged.

**The limits:**

- Yaw stays within about 15 degrees and pitch within about 5 degrees, inside the range the
  arenas are checked at (stage_format.md, debug views 1-3).
- Particles off home follow one 2D similarity, anchored on the focused battler, or on the
  midpoint for `BETWEEN` (foundation E in gen5_camera_gaps.md). Particles on the focused battler
  land exactly. Particles far from it drift slightly, so each script keeps its emitters on the
  battler the camera is framing at that moment.
- These moves use no `SwitchBg`, no OAM copies and no window masks, so nothing drawn in screen
  space breaks off home.

Distances in the table read player side / enemy side.

| Move | Wind-up | Launch | Impact |
|---|---|---|---|
| Tackle (33) | Attacker 48/85%, yaw 6, 8 frames | Defender 48/85%, yaw -6, 6 frames, at the lunge | Shake 2, 6 frames |
| Earthquake (89) | - | Defender 48/88%, yaw -8, pitch -3, 10 frames | The mirrored 2x BG3 shake (category A) |
| Shadow Ball (247) | Attacker 48/85%, yaw 8, 10 frames, during the charge | Between 95%, yaw -4, 8 frames, as the ball flies | Shake 3, 8 frames |
| X-Scissor (404) | Attacker 48/85%, yaw 6, 8 frames | Defender 48/82%, yaw -8, 6 frames | Shake 2, 6 frames |
| Leaf Blade (348) | Attacker 48/85%, yaw 6, 8 frames | Defender 48/85%, yaw -10, pitch 2, 10 frames | Shake 3, 8 frames |
| Stone Edge (444) | Attacker 48/85%, yaw 6, 8 frames | Defender 48/85%, yaw -8, pitch -3, 10 frames | Shake 4, 12 frames |
| Air Slash (403) | Attacker 48/85%, yaw 6, 8 frames | Defender 48/82%, yaw 8, 6 frames | Shake 2, 6 frames |
| Swords Dance (14) | Attacker 48/82%, yaw -12, pitch 2, 8 frames | Orbit +24 degrees over 30 frames (yaw -12 to +12) around the attacker | - |

All eight end with `StageCameraHome 12` and `StageCameraWait`.

**Healthbars.** Seven of the eight moves hide the healthbars for the whole script, as they do in
the classic look (their move data lacks flag `0x40`, which keeps the bars). Tackle and Swords
Dance have the flag, so on the stage they hide the bars themselves with command 91
(`StageHealthbars FALSE`) before the wind-up, and show them again 6 frames into
`StageCameraHome 12`.

### Command 90: `StageCameraZoom fovDeg, frames`

Eases the vertical field of view to `fovDeg` degrees over `frames` camera frames (30 Hz, the
same unit as `Delay`) and keeps the rest of the pose. The home fov is 40 degrees on every arena,
and values are clamped to 10-60. `0` eases back to the home fov. `StageCameraHome` restores the
fov with the rest of the pose, and so does the snap home at script start. A `StageCameraMove`
issued while a zoom is still easing keeps the zoom's target fov.

In a contest, the command skips its two arguments and does nothing, like commands 85-89.

A zoom alone keeps the particles exact: changing the fov is a pure 2D scale about the screen
centre, which the particle similarity reproduces. None of the eight moves uses it yet. It is
there for quick push-ins and dolly-zooms (gap B).

### Command 91: `StageHealthbars visible`

`StageHealthbars FALSE` hides the healthbars that are showing, for a close-up they would cover.
`StageHealthbars TRUE` shows again the ones the script hid, and only those. Any the script leaves
hidden come back when the script ends. The command does nothing while the stage is not visible
(the classic look keeps the move's own healthbar behaviour) and, in a contest, only skips its
argument.

### Checking

`move_redo --moves 33,89,247,404,348,444,403,14` plays the eight moves on the stage. The camera
must be home (AT_HOME) at the menu after each one, and `offHomeMoveFrames` must stay 0, because
that counter only counts scripts that left home without a camera command. The contact sheets
compare each move against the classic look.

`move_redo --reverse --moves ...` plays the same moves enemy->player (the move tester's Y),
still on the Plain stage, and writes the sheets as `move_redo/<id>_<tod>_rev.png`. That run
checks the other branch of every `JumpIfBattlerSide`: the attacker close-up on the enemy and the
defender close-up on the player's mon.

**Known looks:**

- In a close-up on the enemy's mon, the player's mon is nearer the camera than the focus, so it
  grows far more than the focused mon (an anchor scale of 2.6-3x against 1.46x). It is mostly
  off the bottom left of the screen by then. In Tackle, a slice of it shows at the bottom left
  as the camera eases home.
- 85% on the enemy's side frames the enemy's mon at 1.46x, the same as 48% on the player's
  side, so both directions of a move push in by the same amount.
