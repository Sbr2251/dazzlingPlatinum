# Gen 5 battle camera: gap analysis

Where the Living 3D Battle Stage camera (camera.md, chunks 4 and 6) stands against the Black/White 2
battle camera, as of the bw2vis camera-core workstream (branch `bv/camera-core`, with `bw2vis` merged
in: intro and effect-bg). The Gen 5 column is taken from the pokebw2 decomp (`src/ov168/btlv_camera.c`,
`btlv_effvm.c`, `btlv_effect.c`, `btlv_input.c`) and the gap audit (`/tmp/bw2gap/camera.md`, rows C1-C11
and E1-E14). BW2's effect scripts (archives 65 and 66) aren't extracted, so the C gives the camera
model, the presets and the timings, but not the camera paths of the intro, prompt, idle, switch,
catch and trainer-return scripts: those rows are approximations, built from BW2's camera grammar and
said so.

## What the camera has

- An orbit camera (focus, yaw, pitch, distance, fov) whose motion runs on BW2's 60 Hz clock, sampled
  at the battle's 30 Hz (`src/battle/battle_stage_camera.c`, camera.md "Motion").
- BW2's motion by default: constant speed along the straight line between camera positions (a turn
  takes the chord) with BW2's optional half-speed tail; smoothstep stays available. BW2's shake by
  default: a triangle wave at full strength on one world axis, whole swings, ending at rest.
- Battler close-ups as BW2's presets: a slide with no turn, at BW2's size and screen row per slot
  (your mon 0.91x, the foe 1.50x in a single battle). `STAGE_CAMERA_FREE` keeps the old free framing.
- Mons as camera-facing billboards. Their feet stay on their platforms off home, and every particle
  follows the mons around it by their own similarities (foundation E, particles-3d).
- Seven script commands (`StageCameraMove/Orbit/Shake/Home/Wait/Zoom`, `StageHealthbars`), with the
  curve, brake, framing and shake options in their existing words. `mega_evolution.s`, `totem_aura.s`
  and eight move scripts use them (moves.md, "Per-move camera").
- Cinematics: the BW2 intro shots (the intro workstream's, intro.md: the wild pull-out from the fade,
  the trainer and send-out shots on BW2's preset framings; the battle-start focus and sweep stay as
  the fallback), the Mega orbit, the Totem push-in, the crit kick and the faint kick.
- The command menu camera: the prompt shot of the battler choosing, the doubles move/target select
  wide shot, and the idle shots after 15 s (camera.md "Command menu camera").
- Beats after the first prompt: the switch, the catch and the defeated trainer's return (camera.md
  "Beats").
- The home rule: every move animation starts at the home pose and ends there; the guard snaps home at
  script start. Chunk 6: the BG3 shake is mirrored onto the camera for 13 moves; the other 17 shake
  moves, which swap the background, cut to BW2's effect backgrounds (effect-bg, effect_bg.md).
- The 2D trainer and ball OBJs follow their side's similarity off home, moved and scaled (intro).

## Behaviour gaps

| # | Gen 5 behaviour | Now | Gap | Blocker | Size |
|---|---|---|---|---|---|
| 1 | **Wild intro (E1):** effect 0x231 starts with the fade-in; from memory it opens close on the wild mon and pulls back | **Done (intro, approximation):** opens close on the wild mon with the fade-in and pulls out to home before the foe's healthbar (intro.md) | The script's exact path | Archive 66 | - |
| 2 | **Trainer intro (E2):** 0x237 / 0x238 / 0x239 with the trainer, the throw and the mon | **Done (intro, approximation):** opens on the foe's trainer, eases out through "You are challenged by", tightens on the throw; the trainer and ball OBJs follow the camera | The scripts' exact paths; the OBJs are flat (foundation C) | Archive 66 | - |
| 3 | **Player send-out (E3):** 0x232 / 0x234 | **Done (intro, approximation):** a send-out shot on BW2's player preset framing, held until the mons are out, then home | The scripts' exact paths | Archive 66; the back-sprite cut line (F) | - |
| 4 | **Focus at each command prompt (E4):** `BtlvEffect_ZoomCamera` (MoveTo 10 f, brake 8) plays 0x23f / 0x240 / 0x241 on the battler choosing | **Done (approximation):** the same timing onto the slot's BW2 preset shot of the battler choosing, re-aimed per battler in a double battle | The scripts' exact paths (not extracted) | Archive 66 | - |
| 5 | **Move and target select in doubles (E6):** 0x244 and an idle-wait restart | **Done (approximation):** BW2's wide doubles preset (14) with the restart; target select keeps it | The script's exact path | Archive 66 | - |
| 6 | **Idle camera at the menu (E5):** 900 f (15 s) after the prompt, one of 6 scripts at random, never twice in a row, back to back | **Done (approximation):** the same wait and picking over 6 shots built from BW2's presets, chord turns and preset 18, each a cut and a slow constant-speed move | The 6 scripts' exact paths | Archive 66 | - |
| 7 | **Per-move camera (C9):** every move or effect script can drive the camera opcodes | 8 of 507 move scripts; their close-ups now take BW2's presets (C6) and BW2's motion. The rest play at home | The other moves (the camera-moves workstream's templates) | 2D effects in screen space (move_audit.md); archive 65 | L (per move) |
| 8 | **Generic attack framing:** a stand-in for row 7 | Crit kick (only on crits; not in Gen 5) and faint kick, now on BW2's motion and shake | Normal hits get nothing | None | S-M |
| 9 | **Mid-battle switch and recall (E7):** 0x26C / 0x26D | **Done (approximation):** the recall and the send-in close in on the slot along the ray through its feet (1.12x yours, 1.35x the foe's) and hold until the healthbar is in | A centred BW2 preset (the balls' flights are screen paths drawn for home) | Archive 66; foundation C | S |
| 10 | **Ball throw and catch (E12):** 0x23a | **Done (approximation):** the throw at home, then the camera closes in on the ball at the foe (1.35x) through the shakes; a break-free lets go, a catch holds | No follow of the throw | Archive 66; foundations C, E | S |
| 11 | **End of a trainer battle (E13):** 0x270 / 0x271 | **Done (approximation):** a truck over to the foes' side at home size when the defeated trainer comes back, held to the end | The scripts' exact paths | Archive 66 | S |
| 12 | **Stat change, weather, EXP (E10, E11, E14):** effect scripts | Common animations play at home | Unknown whether BW2 moves the camera | Archive 66 | S-M |
| 13 | **Faint (E8):** 0x23b | Faint kick (3 degree dip, one swing of BW2's 2 px shake) | Unknown whether 0x23b moves the camera | Archive 66 | S |

## Camera model gaps

| # | Area | Gen 5 | Now | Status |
|---|---|---|---|---|
| C1 | Home camera and lens | 3/4 view, fovy 26, aspect 1.35 | Straight-on, fovy 40, matching Platinum's 2D layout pixel for pixel | By design. Off-home shots show more perspective than BW2 |
| C2 | Motion curve | MoveTo: constant speed, optional half-speed tail (brakeFrames) | **Done:** the default for every camera command and the new beats; smoothstep with `STAGE_CAMERA_SMOOTH` | Done |
| C3 | Update rate | 60 Hz | 30 Hz, on a 60 Hz clock (camera.md "Update rate": measured; a second 3D frame per logic frame costs 2-11 ms and a draw-only path in four systems) | Kept at 30 Hz by decision |
| C4 | Shake model | Triangle, one world axis, full strength, whole swings | **Done:** the default; the old decaying shake with `STAGE_CAMERA_SHAKE_DECAY` | Done |
| C5 | Shake onset | From rest | **Fixed:** the old shake's vertical term started at full amplitude; both shakes now start at rest | Done |
| C6 | Close-up framing | Presets slide with no turn: your mon 0.91x, the foe 1.50x | **Done:** battler focus is BW2's preset for its slot (sizes and screen rows from BW2's camera) | Done |
| C7 | Orbit path | The chord (MoveTo to the rotated position) | **Done:** BW2's curve turns along the chord; the arc with `STAGE_CAMERA_SMOOTH` | Done |
| C8 | Command set | Absolute / relative moves, 22 presets, save / restore, lock, wide shots, wait and brake | Move (with presets), orbit, shake (axis, quarter), home, wait, zoom; brake and curve on every frames word | Missing: a relative move, save / restore, the camera lock, `wait` |
| C10 | Screen shake vs camera shake | Separate systems | BG3 shake mirrored for 13 moves (redo/shake.json); the 17 shake moves that swap the background cut to BW2's effect backgrounds (effect-bg) | Partial |
| C11 | Off-home sprite projection | Flat at home, perspective off home | Screen-space similarity from each foot anchor | Equivalent |

## Foundation gaps (engine work several rows depend on)

| # | Area | Now | Needed for Gen 5 | Rows |
|---|---|---|---|---|
| A | Camera range | **Checked (bw2vis camera-core):** all 30 quick-battle arenas show no hole at the prompt shots, the 6 idle shots, 1.12x-1.6x the home distance, yaw -20 at 1.12x and pitch -6 (BG0 renders). The panorama is still generated from flat 2D backdrops, so off-home shots smear it | 3D backdrops for low or reverse shots | 1, 3, 6 |
| B | Zoom | Command 90 exists; no script uses it, and BW2 never changes the fov | - | - |
| C | OBJ actors | Trainers and Poke Balls are 2D OBJs that follow their side's mean similarity off home, moved and scaled up to 2x (intro); OAM copies don't follow. The beats keep the battler's feet in place (a dolly along the ray through them, or a truck at home size) because the balls' flights are screen paths drawn for home | Trainers and balls as stage billboards that sit in depth, with flights in world space | 2, 3, 9, 10, 11 |
| D | Menu gating | Done: the menu doesn't wait during the menu camera; a held beat goes home for the menu | - | 4, 5, 6 |
| E | Particles off home | **Done (bw2vis particles-3d):** every particle takes the similarity of the mons around it, the same one their sprites use, so it stays on its mon in any pose (camera.md, "Particles follow the camera"). Full-screen effects opt out with `SetParticleScreenSpace`. A true 3D battle-plane mode exists for A/B (debug bit 21). Before, one similarity moved them all (Shadow Ball's charge drifted to the frame's edge in an attacker close-up; it now frames the pair) | Particles no longer limit per-move cameras; the 2D effects (SwitchBg, OAM copies, windows, HBlank) still do (moves.md, "Particles and per-move cameras") | 7, 10 |
| F | Back-sprite cut line | 89 of 568 back sprites are cut at the frame bottom; the cut guard pans so the cut edge stays under the text box off home | Full-body back art for over-the-shoulder shots | 3, 4 |
| G | Critic | Checks the home invariants, sweep, Mega, Totem, crit and faint; accepts the prompt shot at the first menu (`sStageCameraDebug`) | Scenarios for the prompt, idle shots, select and beats (the bw2vis camera-core captures in `/tmp/bw2vis/camera-core/` do it by hand) | all |
