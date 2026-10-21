# BW2 battler scale and placement on the 3D stage (workstream "layout")

Code: `src/battle/battle_stage_layout.c` (header `include/battle/battle_stage_layout.h`), with
small hooks marked `bw2vis:layout` in `battle_stage.c`, `battle_stage_sprites.c`,
`battle_stage_camera.c`, `battle_stage_stream.c` and `battle_display.c`.

## Back sprites at 2x

BW2 draws backs at 2x and fronts at 1x, pixel for pixel, in its default flat mode
(`BtlvMcss_GetDefaultScaleImpl`, `btlv_mcss.c:2200-2205`: 32 and 16 in 1/16). This holds for
every position in singles and doubles. The streams keep storing backs at the 1.75x baseline
(scale 14 in eighths; Megas 14 to 16, matched to their base form). In battle they are drawn at
`stored * 16 / 14`: 16 for a back (2x), and 16, 17 or 18 for a Mega back. Fronts (8) are
unchanged. `BattleStageLayout_StreamScale` does this for every battle path: the stage mesh, the
flat stream, the move copies (`BattleStageStream_GetScale`) and the sink. The other screens are
unchanged. Workstream sprite-source keeps the baseline in its re-render (index version 3 changes
the header, not the scale meaning). If it ever stores absolute scales, it will bump the index to 4
and this mapping must check that.

## The sink, revisited

The 40 px sink had been justified by B/W's text box being on the touch screen. It isn't: it is on
the top screen, as ours is (textbox.md). What BW2 really does is stand the player's feet about 20
px below the screen (foot point (62, 212)) and let its translucent box show the scene through.
Our box is opaque, so:
- **Short backs** keep the classic foot row (148), where they show whole above the box at the
  command menu.
- **Tall backs** (taller than 100 frame px at 2x) sink by the excess so the head clears the
  opponent's healthbar, as before. The cap is now 64 (was 40), which is BW2's foot row: Steelix,
  Wailord and Garchomp now stand where BW2 stands them. With the box gone during animations, their
  bodies run off the screen's bottom edge as in BW2.
- **Backs with a flat-cut bottom.** The stream's first frame has a run of at least 16 opaque
  texels on the ground row: the Mega stills, which are Platinum-style art. These sink at least 44
  so the cut is at the screen's edge when the box fades. Feet are narrower than the run, so B/W
  backs aren't affected.

## Placement

At rest (the command menu and messages) each battler moves from its classic place toward its BW2
place. While an animation runs, and until the text box shows again, everything is back at the
classic places. Platinum's move animations aim their OBJs, BG effects, windows and hand-tuned
particle positions (`battle_anim_util.c`) there, so the animations look exactly as before apart
from the 2x backs.

BW2's foot points come from projecting its positions (`btlv_mcss.c:184-195`) through its default
camera (`btlv_camera.c:41-52`). The classic feet are the bottom of the 80x80 frame at
`BATTLER_POS_*`. The offsets are `sRestOffset`:

| slot | classic foot | BW2 foot | offset used | why not all of BW2's |
|---|---|---|---|---|
| singles player | (64, 152) | (62, 212) | (-2, 0) | the row: under an opaque box, small backs would vanish at the menu (tall ones sink toward it) |
| singles enemy | (192, 88) | (184, 98) | (-8, 0) | the row: the feet and blob would go behind our player healthbar (from y 95 at x >= 150; BW2's gauge is smaller and lower, `btlv_gauge.c:662`) |
| doubles player 1 | (40, 152) | (16, 192) | (-24, +20) | the row halfway: at the classic row the two 2x backs filled the middle of the screen, over the foes' platform; at BW2's they'd be all but gone behind our opaque box and the ability banner |
| doubles player 2 | (80, 160) | (113, 234) | (+20, +37) | the row halfway, as slot 1; x: at BW2's x its body goes under the player gauges (x >= 136) |
| doubles enemy 1 | (216, 90) | (216, 100) | (0, 0) | the row: behind the doubles player gauges (from y 88) |
| doubles enemy 2 | (176, 82) | (156, 91) | (-20, 0) | the row: as enemy 1 |

If workstream hud-gauges moves the player gauges to BW2's spot, the enemy rows can take BW2's +10
(and doubles player 2 its x 113) by editing that table alone.

A battler moved down (the doubles backs) is a real move on the ground: its foot, blob, silhouette,
camera anchor and platform go to the exact ground point under the new row
(`BattleStageSprites_GroundPointAt`, the home camera's ray), so the prompt shot (camera.md) frames
it there. A tall back's sink counts from the classic row, so the move down takes the sink's place
instead of adding to it (`BackSink` in `battle_stage_stream.c`): Wailord or Steelix stand where they
did, short backs go down to the new row.

At the prompt shot camera-core scales the framed back by its preset size (1.19x / 1.06x in doubles),
on top of the 2x. BW2's flat mode (`mcss.c:353-376`) keeps a sprite's size whatever the camera does,
unless an effect script switches it to perspective; whether its prompt effects (0x23f-0x241, not
extracted) do is unknown, so the prompt's sprite size is left to camera-core.

What follows the offset:
- **Sprites:** `DrawHook` takes `BattleStageLayout_Similarity`. That is the camera's similarity
  with the anchors at the layout place, or a translation at home. Whatever a script does to the
  sprite rides along, and so do the classic shadow and the stat overlay.
- **Platforms:** the platform meshes in `DrawArena` move by the ground shift of their side's mean
  offset, from the side's mean classic foot point to the moved one (`BattleStageSprites_GroundPointAt`).
- **Blobs and silhouettes:** `GroundQuadAxes` puts the blob, and Dig's hole, on the ground under
  the moved foot, and the silhouette (`battle_stage_shadow.c`, `DrawSilhouette`) does the same.
- **Camera anchors:** `BattlerFoot` (camera) puts each anchor at the layout place, so the idle
  drift, the intro focus and the cinematics frame the battlers where they stand.
- **Trainers:** `BattleStage_GetSideOffset` adds the side's mean offset, so the intro trainers
  stand with their platforms.
- **The cut guard:** `CutHomeY` adds the layout dy and, for a streamed battler, its sink.

The ease takes 5 drawn frames with smoothstep. It goes to the classic places when a move-animation
command starts (the command waits for it, see textbox.md) or any script starts. It goes back after
2 frames once no script runs and the box is up again. So it moves with the box fade, not between
the hits of a multi-hit move.

Off, with every offset 0, when: there is no arena, the stage isn't visible, the battle is a Totem
battle (`TotemBattle_HomeOffsetX` has its own layout), or the debug flags `CLASSIC_SPRITES` or
`PLATINUM_LAYOUT` are set.

## `PLATINUM_LAYOUT` (debugFlags bit 12) and the critic

The bit restores the classic places, the 1.75x baseline, the old sink cap of 40 and no cut-back
sink. The critic's `StageRam.set_flags` adds it unless `layout=True`, the same way it adds
`NO_IDLE_CAMERA`. So `stage_ab`, `all_backgrounds`, `sprite_life` and the other home-versus-classic
comparisons still check that the arena lines up with the classic screen, and are not measuring
this deliberate move. A ROM without the bit ignores it. The probes in `/tmp/bw2vis/layout/work`
pass `layout=True`.

## Debug fields: `sBattleStageLayout` (xMAP)

`s8 offset[4][2]` (this frame, px), `u8 ease` (0 classic .. 5 BW2), `u8 on`, `u8 sequences`,
`u8 scriptActive`, `u32 animWaitFrames`, `u32 animWaitMax` (logic frames the move-animation
command waited, in total and at most once).

## Cost

One `G3_Translate` per platform mesh, a few multiplies per battler per frame, 20 bytes of stats.
No VRAM, polygons or heap. The 2x backs cover more pixels than at 1.75x (the fill rate is the same
hardware path).
