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
Since bw2vis (effect_bg.md) these 55 moves show Black 2/White 2's effect backgrounds, and most of them cut
from the arena to the picture (`BATTLE_BG_SWITCH_MODE_CUT`), as Gen 5 does; the fade stays where the move
depends on it (Moonlight, Wish, Cosmic Power, Lunar Dance, Moonblast, Nightmare, Dark Void, Trick Room).

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

252 of the 474 move animations move the stage camera with the move, in the Black/White pattern:
eight hand-authored scripts (below) and 244 that use the camera templates ("Templates"). Every
other move still plays at the home pose.

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

Since camera-core, a battler focus without `STAGE_CAMERA_FREE` is BW2's preset shot of the slot
(camera.md, "Framing": your mon at 0.91x, the foe at 1.50x, no turn), so the distances and yaws of the
battler shots in this table are ignored; Shadow Ball now frames `BETWEEN` at 88% and 96% (camera-core,
the camera auditor's B1). The templates below keep their own framing with `STAGE_CAMERA_FREE`.

**Healthbars.** While the stage is visible, every move animation hides the healthbars for the
whole script, as Black/White 2 does (`btlv_effvm.c:584-586`), except Transform, Mirror Move and
Nature Power, which BW2 also exempts (`Healthbar_MoveAnimHidesHealthbars`, healthbar.c). The
classic look keeps Platinum's per-move flag `MOVE_FLAG_KEEPS_HP_GAUGES` (bit `0x40`, which was
misnamed `MOVE_FLAG_HIDES_HP_GAUGES`): 119 moves carry it and keep the bars there. Tackle and
Swords Dance still carry command 91 (`StageHealthbars FALSE` before the wind-up, `TRUE` 6 frames
into `StageCameraHome 12`); with the bars already hidden it finds none showing, so they come back
when the script ends, like every other move's.

### Templates

244 moves use one of six camera templates built from Black 2/White 2's camera presets. They are
macros in `asm/macros/btlanimcam.inc`, and `tools/battle_stage/camera_templates.py` writes them into
the scripts. Its table is the list of templated moves: `--check` says whether the scripts match it,
`--list` prints it by template and `--strip` takes every template out.

**Where the poses come from.** pokebw2 has no BW2 move scripts (archive 65 is not extracted), but the
move VM's camera commands and their preset poses are there: `CmdCameraMovePreset` and the other camera
opcodes in `src/ov168/btlv_effvm.c:762-1124`, the preset table at `:468-505`, and the home pose in
`src/ov167/btlv_camera.c:41-53`. Every BW2 preset is the home camera trucked onto a mon or a group, with no
rotation. In singles that frames the enemy's mon at about 1.50x home size and the player's mon at about
0.91x (a pan with a slight pull-back), and `CmdCameraShake` punches the hit. The templates use those
framings in our relative poses (camera auditor, C6):

| shot | player's side | enemy's side |
|---|---|---|
| close (`CAMTPL_CLOSE_*`, `CAMTPL_SELF_*`) | 78%: 0.91x, BW2's player shot | 92%: 1.35x |
| two-shot (`CAMTPL_BETWEEN`, focus `BETWEEN`) | 95% | 95% |
| wide (`CAMTPL_WIDE`, focus `CENTER`) | 112%: the player's mon at 0.85x, the enemy's at 0.91x | |

The scales are the battlers' `anchorScale`, read in the move tester on the Plain stage. From a mon on the
player's side, 100% frames it at 0.71x and 48% at 1.46x. On the enemy's side, BW2's 1.50x is 85% (the old
1.46x of the hand-authored moves), but at that size the sparks around a hit fly out of the frame: the
particle check below WARNs for five of them at 85%. So the templates stop at 92%. Every battler shot carries
`STAGE_CAMERA_FREE`, which keeps these distances instead of camera-core's preset shot (camera.md,
"Framing"); on the player's side the size is the preset's anyway. Yaw stays within 8 degrees and pitch
within 3.

The motion is BW2's, camera-core's default: constant speed on a straight line, with BW2's brake on every
move (`8 | STAGE_CAMERA_BRAKE(6)` for the wind-up, `6 | BRAKE(4)` for the cut, `10 | BRAKE(7)` for the
two-shot and the self shot, `12 | BRAKE(8)` for the pull-back and the ease home), as the Mega Evolution and
Totem scripts do. The self template's orbit is `STAGE_CAMERA_SMOOTH`, an arc around the mon rather than
BW2's chord, which would dip toward it. The punch on the hit is BW2's shake, camera-core's default: a
vertical triangle at full strength that ends at rest, rounded up to whole 8-frame swings.

**The templates.** Each opens at the top of the script and ends with `CamTplClose` before every `End`:
`StageCameraHome 12`, the healthbars it hid back 6 frames in, then `StageCameraWait`. Every template but
"wide" also sends `StageHealthbars FALSE` for its close shots; since hud-gauges hides the bars for every
move on the stage (Healthbars, above), it finds none showing and does nothing, and it still covers a
move that rule exempts.

| template | open | at each hit (the defender's `Func_Shake`) | moves |
|---|---|---|---|
| contact | the attacker's close shot (yaw 6), hold 8 frames, then the defender's close shot (yaw -6). The whole animation then plays on the defender | `CamTplImpact`: a 2 px shake of one swing (3 px and 8 frames when the mon's own shake is 3 px or more) | 42 |
| push | the two-shot (yaw -4) while it flies | `CamTplPushImpact`, the defender's close shot, then `CamTplImpact` | 70 |
| twoshot | the two-shot for the whole move | `CamTplImpact` | 71 |
| self | the attacker's close shot (yaw -8, pitch 2), then a 14-degree orbit over 40 frames | - | 34 |
| wide | the pull-back, pitch 3 | `CamTplImpact`, a spread hit included | 27 |
| shake | none: the camera stays home | `CamTplImpact` | 0 |

The contact template adds 8 frames before the move's own animation. Every template adds about 17 at its
end (the braked ease home and the wait).

**How each move got its template.** The candidates were the 277 moves `move_audit.json` rates risk: low
(particles and sprite moves only), less the eight hand-authored ones and the 25 rejected below. None of
them uses `SwitchBg`, `FadeBg` or any other background change; those belong to the effect-bg workstream.

1. A first pick by the move data. `RANGE_USER`, `RANGE_USER_SIDE` and `RANGE_USER_OR_ALLY` get "self";
   spread and field ranges get "wide". A single-target move gets "contact" if it makes contact or its
   particles sit on the defender (90% of them in the classic run), else "push".
2. Every move was played with its template in the move tester, player->enemy and enemy->player, and every
   live particle was read from RAM every other frame (the particle check under Checking).
3. A move whose particles left the scene (more than 3% of them) or drifted off a battler (more than
   10 px), in either direction, stepped down and was played again: contact to push when its particles
   also sit on the attacker, contact or push to twoshot, self to wide, twoshot or wide to shake. The
   margin under the check's PASS limits (5%, 16 px) keeps a move whose sparks are random from failing on
   another run. Secret Power went the other way, push to contact: its one emitter is on the defender, and
   the two-shot drifted it.
4. After merging bw2vis, a full critic run and a second profile on the merged ROM put ten more over the
   margin (random sparks on another day): Covet, Beat Up, Scratch, Karate Chop, Pay Day, Bone Club, Lovely
   Kiss, Rock Smash, Seed Bomb and Mud Bomb went to twoshot.
5. After merging camera-core (BW2's motion, brake and triangle shake; the preset framing, which the
   templates opt out of with `STAGE_CAMERA_FREE`), every templated move was profiled again, both
   directions, with Finneon and with the debug Garchomp (whose back sprite is cut) in the lead. Only Iron
   Head drifted (25 px, Garchomp, enemy->player); it went to twoshot. After merging layout (back sprites at
   2x, BW2 placement, the message box fading out during moves) the same profile passed every move; Wing
   Attack, at 3.5% off the scene enemy->player, went to twoshot for the margin.

95 moves ended on another template than their first pick, none on shake. Every templated move ends at
home, keeps its particles on screen and passes the move_redo, move_tester and move_audit checks at day and
at night (Checking).

The emitters are still flat 2D, which the particles-3d workstream is changing. The templates live with that
by keeping each move's particles on the battler that is framed: contact plays the whole animation on the
defender and self on the attacker, push only moves in on the defender at the hit, and the two-shot and the
wide shot keep both mons in the frame, where the particle similarity stays close to both battlers' own.
Once particles are projected in 3D, the moves that stepped down to twoshot can go back to contact or push.

**The moves by template** (`camera_templates.py --list`; move_audit.json notes each one as "per-move camera
(template ...)"):

- **contact (42):** Comet Punch, Cut, Bind, Vine Whip, Horn Attack, Fury Attack, Body Slam, Wrap, Thrash,
  Pin Missile, Ember, Peck, Drill Peck, Submission, Low Kick, Strength, Lick, Smog, Clamp, Hi Jump Kick,
  Dizzy Punch, Fury Swipes, Struggle, Triple Kick, Attract, Return, Vital Throw, Brick Break, Secret
  Power, Arm Thrust, Poison Fang, Astonish, Poison Tail, Feint, Pluck, Wring Out, Sucker Punch, Force
  Palm, Poison Jab, Bullet Punch, Grass Knot, Play Rough.
- **push (70):** Sand-Attack, Poison Sting, Twineedle, Roar, Psybeam, PoisonPowder, Stun Spore, Sleep
  Powder, Fire Spin, Rock Throw, Dig, Hypnosis, Screech, Sludge, Poison Gas, Leech Life, Spore, Psywave,
  Spider Web, Flail, Cotton Spore, Mach Punch, Sweet Kiss, Sludge Bomb, Giga Drain, Charm, Rollout, Steel
  Wing, Sleep Talk, Mirror Coat, AncientPower, Uproar, Spit Up, Flatter, Will-O-Wisp, Facade, Magic Coat,
  Yawn, Skill Swap, Snatch, Dive, FeatherDance, Ice Ball, Fake Tears, Tickle, Sand Tomb, Block, Bounce,
  Magical Leaf, Rock Blast, Gyro Ball, Brine, Natural Gift, Payback, Fling, Psycho Shift, Gastro Acid, Me
  First, Copycat, Power Swap, Guard Swap, Worry Seed, Heart Swap, Vacuum Wave, Psycho Cut, Rock Climb,
  Magnet Bomb, Chatter, Attack Order, Crush Grip.
- **twoshot (71):** Karate Chop, DoubleSlap, Pay Day, Scratch, ViceGrip, Wing Attack, Whirlwind, Slam,
  Stomp, Double Kick, Jump Kick, Headbutt, Horn Drill, Take Down, Bite, SonicBoom, Water Gun, BubbleBeam,
  Counter, Leech Seed, Petal Dance, Dragon Rage, Rage, SmokeScreen, Egg Bomb, Bone Club, Spike Cannon,
  Lovely Kiss, Hyper Fang, Super Fang, Slash, Thief, Flame Wheel, Mud-Slap, Octazooka, Bone Rush,
  Frustration, Pain Split, DragonBreath, Rapid Spin, Cross Chop, Crunch, Rock Smash, Beat Up, Knock Off,
  Endeavor, Blaze Kick, Needle Arm, Signal Beam, Bullet Seed, Mud Shot, Covet, Wake-Up Slap, U-turn,
  Assurance, Embargo, Trump Card, Punishment, Last Resort, Night Slash, Seed Bomb, Bug Buzz, Shadow Claw,
  Mud Bomb, Mirror Shot, Cross Poison, Iron Head, Bug Bite, Aqua Jet, Double Hit, Ominous Wind.
- **self (34):** Growth, Recover, Withdraw, Defense Curl, Barrier, Light Screen, Reflect, Focus Energy,
  Bide, Softboiled, Splash, Rest, Sharpen, Conversion, Protect, Belly Drum, Endure, Milk Drink, Safeguard,
  Synthesis, Stockpile, Recycle, Slack Off, Bulk Up, Dragon Dance, Roost, Acupressure, Power Trick, Lucky
  Chant, Aqua Ring, Magnet Rise, Nasty Plot, Defend Order, Heal Order.
- **wide (27):** Razor Wind, Tail Whip, Growl, Acid, Razor Leaf, Haze, Bubble, Rock Slide, Conversion 2,
  Spikes, Sandstorm, Sweet Scent, Swallow, Heat Wave, Imprison, Teeter Dance, Mud Sport, Air Cutter, Water
  Spout, Howl, Water Sport, Gravity, Tailwind, Toxic Spikes, Lava Plume, Captivate, Stealth Rock.

**Rejected** (risk: low, but no template; `REJECTED` in the tool):

- 2D OBJ effect sprites, which are drawn in screen space and can't follow the camera: Bonemerang,
  Swagger, Baton Pass, Torment, Smelling Salts, Crush Claw, Icicle Spear, Dragon Claw, and Metronome,
  Constrict and Follow Me (OBJ sprites only).
- A background-layer shake (`Func_ShakeBg`), which the stage mirrors onto the camera: Barrage, Snore,
  Hammer Arm, Dragon Rush, Wood Hammer and Rock Tomb. Magnitude too (its BG3 shake is mirrored, chunk 6
  category A).
- Particles switched to the perspective particle camera (`SetCameraProjection`): Gust and Twister (and Rock
  Tomb).
- Substitute: its doll is drawn in screen space (`BtlAnimCmd_068`), and sprite_life checks it.
- No animation of its own: Mirror Move and Nature Power.
- The critic's reference moves at home: Pound (the camera scenario's "tester Pound at home", stage_toggle,
  move_tester's second turn) and False Swipe (the real turns of camera and move_tester, which never KO).
  With a template the camera scenario's checks that nothing but a kick leaves home would have nothing to
  hold on to.

The other 197 moves (risk medium or high in move_audit: background switches and fades, OAM and BG2 copies,
windows, per-line waves) were not candidates. The eight hand-authored moves are unchanged.

**The pull-back on every arena.** The wide template is the only pose farther out than home. Growl was
played on all 30 quick-battle backgrounds, and the 3D layer was rendered alone with the magenta marker
while the camera was pulled back. No background showed a hole: the panoramas reach 64 rows above the home
frame, and the ground 48 rows below it and out to x = 720 at the sides (`arena.py`). camera-core's range
check (camera.md, "Camera range") covers 1.12x to 1.6x the home distance on every arena as well.

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

**Particles off home.** `move_redo` also reads every live particle from RAM every other frame while a
move plays, and grades "particles stay on screen off home" for any move whose camera left home
(`tools/battle_stage/emu/README.md`, "Particles off home"):

- **lost:** of the particles classic shows inside the scene (above the text box, at least 16 px from its
  edges), the share the camera puts more than 8 px outside it. PASS at 5% or less, FAIL above 15%.
- **drift:** for particles on a battler (within 44 px of its body, and not emitted by the other battler),
  how far the particle similarity draws them from that battler's own similarity, 95th percentile. PASS at
  16 px or less, FAIL above 32.

The hand-authored moves at 85% on the enemy's side WARN on lost (Tackle, X-Scissor, Leaf Blade, Stone
Edge and Air Slash, 6-9%: sparks leave the 1.46x frame), and Shadow Ball FAILs (15% lost, 48 px drift: its
charge sits off the attacker it frames, the camera auditor's bug B1). Earthquake and Swords Dance PASS.

**The templated moves** are checked with the same scenarios and their full list (the ids are in
`camera_templates.py --list` and move_audit.json):

```
critic.py ROM OUT --scenario move_redo --moves <the 246 ids> --map build/main.nef.xMAP
critic.py ROM OUT --scenario move_redo --reverse --moves <the 246 ids> --map build/main.nef.xMAP
critic.py ROM OUT --scenario move_tester --reverse --moves <the 246 ids> --sprite-moves "" --map ...
critic.py ROM OUT --scenario move_audit --moves <the 246 ids> --map build/main.nef.xMAP
```

move_tester's battle (the save's Eterna Forest) has no arena, so it checks the animations and the menu
but not the camera; move_redo and move_audit play on the Plain stage at day and at night.

**Known looks:**

- In a close-up on the enemy's mon, the player's mon is nearer the camera than the focus, so it
  grows far more than the focused mon (an anchor scale of 2.6-3x against 1.46x). It is mostly
  off the bottom left of the screen by then. In Tackle, a slice of it shows at the bottom left
  as the camera eases home.
- 85% on the enemy's side frames the enemy's mon at 1.46x, the same as 48% on the player's
  side, so both directions of a move push in by the same amount.
