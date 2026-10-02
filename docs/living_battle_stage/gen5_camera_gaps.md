# Gen 5 battle camera: gap analysis

Where the Living 3D Battle Stage camera (camera.md, chunks 4 and 6) stands against the Black/White
battle camera, as of `main` at 77009099d. The Gen 5 column describes the target behaviour; check each
row against B/W footage before building it.

## What main already has

- An orbit camera (focus, yaw, pitch, distance, fov) with smoothstep eases and deterministic shake
  (`src/battle/battle_stage_camera.c`).
- Mons as camera-facing billboards. Their feet stay on their platforms off home, and particles follow
  through a 2D similarity hook.
- Seven script commands (`StageCameraMove/Orbit/Shake/Home/Wait/Zoom`, `StageHealthbars`). `mega_evolution.s`,
  `totem_aura.s` and eight move scripts use them (feature/gen5-move-camera; moves.md, "Per-move
  camera").
- Cinematics:
  - the battle-start focus on the opponent, with a fallback sweep at the first menu;
  - the Mega orbit;
  - the Totem push-in;
  - the crit kick and the faint kick.
- The home rule: every move animation starts at the home pose and ends there. The guard snaps home
  at script start. Only the eight per-move camera scripts leave home on purpose, and they ease back
  before `End`.
- Chunk 6: the BG3 shake is mirrored onto the camera for 13 moves. 17 shake moves still fade the arena.

## Behaviour gaps

| # | Gen 5 behaviour | Main today | Gap | Blocker | Size |
|---|---|---|---|---|---|
| 1 | **Wild intro:** opens close on the wild mon, then pulls back to the wide shot | Starts at home. After the healthbar slides in, it swings to the opponent (yaw -20, pitch -3, 70%), holds until the player sends out, then eases home | The direction is backwards (out-to-in instead of in-to-out), and it runs after the slide-in rather than as the opener | The wild intro's `SpriteToOAM` copy can't follow the camera, so the camera must be home by then | M |
| 2 | **Trainer intro:** frames the opponent trainer, follows the throw, the mon lands | The same opponent focus, only once the mon is out. Trainer OBJs are only translated off home, never scaled | No trainer shot and no throw follow | Trainer and ball are 2D OBJs (see foundation C) | L |
| 3 | **Player send-out:** over-the-shoulder behind the player's trainer, follows the ball, the mon pops out, the camera settles | The player's throw waits until the camera is home (120-frame cap). No shot | The whole shot is missing | Foundation C; the back-sprite cut line (F) | L |
| 4 | **Idle camera at the command menu:** slow looping drift between the wide shot, over the player's shoulder and an opponent close-up | **Done (feature/idle-camera-drift):** `SEQUENCE_IDLE` loops four gentle poses while the menu is up and eases home in 16 frames once the commands are in (camera.md, "Idle drift") | No real over-the-shoulder shot: the player-side pose only leans 15% toward the player without a push-in | The cut guard (F) and camera range (A) limit player-side framing | M |
| 5 | **Doubles/triples:** during selection, frames the battler whose turn it is | Nothing | Missing | Cheap once #4 exists | S |
| 6 | **Per-move camera:** the camera moves with the move (onto the attacker, following to the target, an impact punch) | **Started (feature/gen5-move-camera):** Tackle, Earthquake, Shadow Ball, X-Scissor, Leaf Blade, Stone Edge, Air Slash and Swords Dance frame the attacker, follow to the target and shake on the hit (moves.md, "Per-move camera"). Every other move plays at home. 13 shake moves drive the camera from the BG3 shake | The other moves. (Both directions of the eight are checked on the stage: `move_redo` and `move_redo --reverse`) | Moves draw 2D effects in screen space: OAM copies (38 moves), BG2 pictures, window masks, HBlank waves, `SwitchBg` (168 moves; 55 suppress the arena), blends. These break off home. move_audit.md has the list | L (per move) |
| 7 | **Generic attack framing** (a cheap stand-in for #6): a short push toward the attacker before the animation and a punch toward the defender on the hit; the animation itself stays at home | Crit kick (only on crits: 8% push plus shake) and faint kick | Normal hits and attacker pre-rolls get nothing | None: the hooks exist (`ov16_0225DA44` hit blink, the script-start guard) | S-M |
| 8 | **Mid-battle switch / send-out:** focus on the side that sends out | Nothing after the intro | Missing | Ball OBJ (C) | M |
| 9 | **Poke Ball throw and catch:** follows the ball to the target, holds on the shaking ball | Nothing. Throw, shake and catch play at home | Missing | The ball is OBJ/particles at home (C, E) | M-L |
| 10 | **Trainer defeat / battle end:** the opponent trainer slides back in, framed | Nothing | Missing | Trainer OBJ (C) | M |
| 11 | **Stat change / status animations:** a brief look at the affected mon (verify) | Common animations play at home | Missing if B/W does it | Same screen-space rule as #6, but these scripts are simple | S-M |
| 12 | **Faint** | Faint kick: 3-degree dip plus a 2 px shake | Roughly there; tune only | None | S |

## Foundation gaps (engine work several rows depend on)

| # | Area | Today | Needed for Gen 5 | Rows |
|---|---|---|---|---|
| A | Camera range | Holes only checked at yaw +/-20 and pitch +15 (debug views 1-3, stage_format.md). The panorama is generated from flat 2D backdrops | Wider and lower shots (over the shoulder, low opponent close-ups). Extend the panorama and ground coverage for all 23 arenas, and add a hole check at the new poses | 1, 3, 4, 6 |
| B | Zoom | **Done (feature/gen5-move-camera):** command 90, `StageCameraZoom fovDeg, frames`, eases the fov (10-60 degrees, home 40). `StageCameraHome` and the script-start snap restore it. No script uses it yet | - | 1, 4, 6 |
| C | OBJ actors | Trainers, Poke Balls and OAM copies are 2D OBJs, only translated off home | Trainers and balls drawn as stage billboards (like the mons), so they scale and sit in depth | 2, 3, 8, 9, 10 |
| D | Menu gating | **Done** with #4: the menu doesn't wait during `SEQUENCE_IDLE`, and the camera eases home when the commands are in | - | 4, 5 |
| E | Particles off home | Scale plus translate only (no perspective), through the particle projection hook | Fine for short kicks. Real per-move camera shots need depth-correct emitters or per-move limits | 6, 9 |
| F | Back-sprite cut line | 89 of 568 back sprites are cut at the frame bottom. The cut guard stops the player's mon rising above the textbox off home | Over-the-shoulder shots need the guard to reframe (as it does today) or full-body back art | 3, 4 |
| G | Critic | Checks the home invariants, sweep, Mega, Totem, crit and faint | Scenarios for the idle camera, the send-out shots, catch framing and a camera-range hole sweep | all |
