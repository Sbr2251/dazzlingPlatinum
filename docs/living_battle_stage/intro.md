# Battle intro: the BW2 opening on the 3D stage (bw2vis:intro)

Everything from the field transition to the first command prompt, while the 3D stage is visible.
The stage-off (classic, L+R+SELECT) path keeps Platinum's opening; only the tray order and the doubles
gauge order (below) apply to both.

The sequencing comes from pokebw2's C (`src/ov167/btlv_scu.c` `BtlvScu_Encount*`, `btlv_core.c`,
`src/ov168/btlv_effect.c`). The camera paths inside BW2's effect scripts (0x231, 0x237-0x239, 0x232,
0x234; archive `a/0/6/6`) are not extracted, so the poses below are approximations: they reuse BW2's
own preset framings (enemy 1.50x, the player's mon 0.91x, `btlv_effvm.c:468-505`) and the order and
waits of `btlv_scu.c`. No BW2 asset is used.

## The opening (presentation rows 1-2)

- **No curtain.** Platinum's opening is a terrain particle wipe (sky blue, grass...) and a white burst
  over BG palettes filled with the wipe's colour (`ov16_02263014`). On the stage it is replaced by
  `IntroStageOpening` (`battle_display.c`): the real palettes at once, and a master-brightness fade-in
  on both screens over `INTRO_FADE_IN_STEPS` (24) task frames, about 48 screen frames like BW2's 16
  levels 2 frames apart (`BtlvScu_EncountFadeIn`, `btlv_scu.c:580-587`). It fades from white when the
  field's transition ended white (the Totem's flash), else from black, as BW2 does.
- **Black from the first frame.** Battle init (`ov16_0223B140.c`) sets the master brightness to black
  (or white) when the stage is enabled, so the curtain's flat colour never shows. The classic path
  (no arena, or the stage off) puts it back to 0 when the opening task starts.
- **No platform slide.** The platforms, the trainers and the wild mon start at their places
  (`IntroNoSlide`; BW2 sets its trainers at their 3D spots, `btlv_scu.c:747`). The camera provides the
  motion. The cries and the trainers' intro animations play at the same task frames as before (the
  28-frame wait is kept). Giratina's own entrance (`BATTLE_STATUS_GIRATINA`) is untouched.
- **The wild mon in colour.** No Platinum silhouette on the stage (BW2 adds the wild mon in colour,
  `btlv_scu.c:650-658`).

## Camera shots (`battle_stage_camera.c`, the intro block)

| beat | BW2 | ours | pose (focus side, toward %, distance %, yaw, pitch) |
|---|---|---|---|
| wild opening | 0x231 with the fade-in, the message waits for it (`btlv_scu.c:654-665`) | `BattleStage_StartIntroOpen` at the opening: snap close on the wild side, ease home over 120 screen frames, ending before the opponent's healthbar (`WaitTime 122`) | opponents, 100, 62, -14, -3 |
| trainer opening | 0x237 with the fade-in (`:758-762`) | snap close on the opponent's side, ease out a little over 150 frames, hold through "You are challenged by" | opponents, 100, 80, -12, -2 to 92, -8, -1 |
| trainer throw | 0x238 after the message (`:776-780`) | `BattleStage_IntroEnemyThrow` (the opponent's throw task): tighten over 40 frames, particles follow the opponents | opponents, 100, 82, -14, -2 |
| foe out, player's throw | the foe gauge shows as 0x232 starts (`:807-811`) | the opponent's healthbar (`StartIntroFocus`) turns the camera to the send-out shot; in a wild battle "Go!" does (`IntroPlayerSendOut`) | players, 40, 94, 0, +3 (about 0.92x on the player's mon) |
| player's mon out | 0x234; the player's gauge after it ends (`:820-842`) | `BattleStage_IntroMonOut` when the last mon thrown is out: hold 16 frames, ease home over 30; the player's healthbars wait for home | home |

- The opponent's healthbar is held only while the wild pull-out is still easing (the legacy rule).
  In the trainer shots it shows at once, as in BW2.
- The send-out shot is BW2's player preset (a pan with a slight pull-back), not an over-the-shoulder
  close-up: a camera behind the trainer would put the trainer OBJ and the player's back sprites,
  which are cut at the frame bottom (camera.md foundation F, cut_guard.md), in the foreground. The pan
  is partial (40%) so the platform stays bottom left and the player's ball tray stays beside it.
- A recorded battle (the player's side sends out first) opens at home; so does Giratina's battle,
  where the legacy battle-start focus still runs. If the intro shots didn't start (the stage wasn't
  visible at the opening) the legacy focus and the first-menu sweep run as before.
- A wild opponent's OAM copy (`SpriteToOAM`) stays hidden while the opponent is drawn from its Gen 5
  stream, so the shots go on. If the copy shows (a mon without a stream, or `NO_SPRITE_STREAM`), the
  send-out shot is dropped: the camera eases home before the copy and the player sends out at home
  (`BattleStage_IntroSpriteToOAM`).
- `cinematicsSeen` gets the new bit 6 (`BATTLE_STAGE_CINEMATIC_INTRO`) and, except in a Totem
  battle, bit 0 (the critic's `camera` scenario checks the opening as the sweep; `totem_battle`
  checks that bit 0 stays clear).
- Safety caps: the send-out shot releases itself after 720 screen frames; a player-side healthbar
  waits for its mon at most 240 task frames.

## 2D OBJs follow the camera (Bug 9)

The trainers and the Poke Balls they throw are 2D OBJs. Off home each is drawn with its side's mean
similarity (`p' = now + s * (p - home)`, the same model as the stage sprites) as an affine
double-size OBJ, scaled by `s` (capped at 2x; past that it is off screen), then put back after the
draw so the game's own position checks never see it (`BattleStage_FollowIntroSprite`).

- Trainers: `OffsetTrainerSprites` (`ov16_0223B140.c`), which used to translate only. The player's
  trainer no longer stays full size with a slice at the bottom left while the camera is pushed in.
- Balls: the ball's task draws it itself, so `ov12_02235E94.c` calls a draw hook around its
  `SpriteSystem_DrawSprites` (`BallRotation_SetDrawHook`, set by the stage camera, NULL outside
  battles). The hook ignores a target that isn't a battler (a capture ball's target is 20000+).
- This is what lets the player's throw happen off home: it no longer waits for the camera to get
  home (`BattleStage_IsIntroThrowReady`), except under the legacy focus.
- The bottom screen (bw2vis:dblfix, `KeepIntroSpriteOffSubScreen`): the battle renderer draws an OBJ
  on each screen whose view rect its bounds reach, and the bottom screen's starts 80 px below the
  top screen (`SetSubScreenViewRect(.., 192 + 80)`). A followed OBJ whose scaled bounds would reach
  it parks if it is wholly below the top screen, else draws 256 px higher: OAM Y is 8 bits, so its
  OAMs are the same. Before, the player's 2x trainer under the foes' send-out shot (28 px lower in
  doubles, with the layout's side offset) drew on the bottom screen too. A trainer is a
  VRAM-transfer cell with no bottom-screen place, so its frame went to the unset sub address (-1)
  and overwrote the bottom screen's OBJ characters from 0, which is the command menu's party ball
  row: QA's doubles ball-row bug.

## Script order (both paths)

- **Ball trays (Bug 3).** `subscript_start_encounter.s`, trainer battles: only the opponent's tray
  with "You are challenged by"; the player's tray comes in after the opponent's healthbar, then
  "Go!" (BW2, `btlv_scu.c:766-804`). It used to come in with the opponent's and stayed screen-fixed
  over the camera's push in on the opponent. Recorded battles keep Platinum's order (they open at
  home).
- **Doubles gauges (item 5).** A player-side healthbar of the intro waits until its mon is out (full
  size in the send-out task, `ov16_0225EA80`): Platinum's fixed `WaitTime 96` brought them in before
  the balls opened in a double battle. BW2 shows them after 0x234 (`btlv_scu.c:1594-1598`). The intro
  throws are tracked from the trainer's throw (`ov16_0225D360`, intro only) and cleared at the first
  command menu.

## Budget

No polygons, VRAM or palettes are added. Up to 4 trainer OBJs and 2 balls use affine double-size
OBJs while off home (affine parameter slots from the OAM manager's 32; the ball already used one).
The camera work per frame is the same projections as before plus one similarity per drawn OBJ.

## Verification

`tools/battle_stage/emu/intro_capture.py` records the intro of a wild battle, a Totem, Aroma Lady
Taylor (single), the Twins (double) and the Arc 2 2.5 tag battle from the owner saves, and the
classic path with the stage switched off. Evidence of the bw2vis build: `/tmp/bw2vis/intro/`.
