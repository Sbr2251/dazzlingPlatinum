# 3D battle stage: move compatibility (chunk 5)

This is the contract for chunk 5 between the move audit, the engine fixes and the emulator
critic (`tools/battle_stage/emu/critic.py`). PLAN.md, chunk 5, has the goals.

## Where things stand

Move animations always run with the stage camera at home (camera.md). When a move does
something that the 3D arena on BG0 would hide or break, `BattleAnimSystem_UpdateStageSuppress`
(battle_anim_system.c) hides the arena for as long as it lasts:

- `BATTLE_STAGE_SUPPRESS_BG_SWITCH`: `SwitchBg`, a bgAnim task, a changed effect BG or a
  scrolled BG3.
- `BATTLE_STAGE_SUPPRESS_BG2_EFFECT`: BG2 shows something under the 3D layer.

The classic BG3 backdrop and OBJ platforms then come back, and the stage sprites go
classic. Nothing breaks this way, but the swap is a hard pop. At day, at home, it is nearly
invisible. At twilight and night, and on backgrounds with haze, the arena's lighting and
fog vanish in one frame, and the mons lose their tint.

Chunk 5 keeps the arena on screen for the common cases and replaces the remaining pops
with fades. **Every fix must leave day at home, with no effect running, byte-identical**
(the `stage_ab` check), and it must never leave the arena or the sprites in a state the
move didn't intend once the script ends.

## 1. The move audit (no emulator)

`tools/battle_stage/move_audit.py` statically scans every move animation script
(`res/battle/moves/*/anim.s`), follows its `Call`/`Jump`s and the common subscripts, and
tags each move with the mechanisms it uses. It writes two files:

- `docs/living_battle_stage/move_audit.json`, which the critic and chunk 6 read.
- `docs/living_battle_stage/move_audit.md`, which is for people: a summary by mechanism,
  then one row per move.

The JSON is a list of objects, one per move:

```json
{"id": 91, "name": "DIG", "dir": "dig",
 "mechanisms": ["partial_draw", "switch_bg"],
 "suppress": ["bg_switch"],
 "fix": ["F6"],
 "risk": "high",
 "notes": "short, optional"}
```

`mechanisms` uses these tags:

| tag | what the script does |
|---|---|
| `sprite_xy` | writes a mon's x/y/offset directly (script funcs, `MON_SPRITE_*`) |
| `sprite_scale_rot` | writes scale or rotation |
| `partial_draw` | clips the sprite (drawX/Y/Width/Height) |
| `bg2_copy` | `LoadPokemonSpriteIntoBg`: the mon copied onto BG2 |
| `oam_copy` | `AddPokemonSprite`: the mon copied into OAM (Double Team, Agility, ...) |
| `hblank_wave` | per-line scroll (HBlank/buffer manager) of any layer |
| `window` | window masks (WIN0/WIN1/OBJ window) |
| `sprite_bg_blend` | `SetSpriteBgBlending` or other alpha blends between layers |
| `brightness` | 2D brightness blends |
| `switch_bg` | `SwitchBg`/`RestoreBg`, bgAnim tasks, BG3 palette or scroll changes |
| `bg2_effect` | draws a picture or tiles on BG2 other than a mon copy |
| `particles` | emitters (all of them follow the camera, so this is low risk) |
| `sprite_fade_tint` | palette fades or tints of a mon |

`suppress` predicts which of today's suppression reasons fire (`bg_switch`, `bg2_effect`).
`fix` lists which generic fix below should cover the move. `risk` is:

- `high`: a pop today, or something visibly wrong with the arena visible.
- `medium`: probably fine, but unverified.
- `low`: particles and sprite moves only.

The audit also keeps a short list of the moves chunk 6 should redo by hand.

The scanner does the tagging. Judgement (risk, fix, notes) goes in a small overrides table
inside the script, so a rerun gives the same files.

## 2. Generic fixes

### F1: BG2 mon copies over the arena

`LoadPokemonSpriteIntoBg` copies a mon onto BG2 and hides the sprite (Acid Armor,
Extrasensory, Spite, Camouflage and others). BG2 sits under the 3D layer, so the arena
covers the copy and today the stage is suppressed.

While the arena shows and BG2 holds only the mon copy, lift BG2's priority above BG0 for
as long as the copy lives. Restore the old priority afterwards, and at the latest when the
script ends. Tint the copy's palette with the arena's sprite tint (F2), so it looks like
the lit mesh it replaces.

`BattleAnimSystem_IsBaseBgUnderStage` then no longer reports it, because BG2 is above BG0,
and the arena stays up. If BG2 also carries an effect picture, keep today's suppression.

Count lifted frames in `liftedBg2Frames` and tinted copies in `tintedCopies`.

### F2: the arena's sprite tint for 2D copies

Add `BOOL BattleStage_GetSpriteTint(u16 *tintR, u16 *tintG, u16 *tintB)` to battle_stage.h,
implemented in battle_stage_sprites.c. It returns the per-channel factor, in 1/256, that
the lit mesh applies to a camera-facing texel at the current time of day:

- the diffuse + ambient + emission of `SetLight` and the material in sprites.md, clamped to 31, over 31.
- 256 in every channel at day, where the mesh saturates.

It returns FALSE, meaning leave the colors alone, when the stage isn't visible, the
sprites are classic (`CLASSIC_SPRITES`) or every channel is 256.

Then:

- BG2 copies (F1) and OAM copies (`AddPokemonSprite`) get their palette multiplied by the
  tint when they are made. Anything that later fades or tints the copy starts from the
  tinted palette.
- At day nothing changes, byte for byte.

### F3: window masks

A window that hides BG0 somewhere to cut the mons also cuts the arena, which shows BG3
through the hole. A window that shows BG2 under 3D is already caught by
`BattleAnimSystem_IsBaseBgUnderStage`.

Find the window users (the audit lists them) and handle them so the arena is not cut:

- **Option a:** include BG0 in the window regions while the arena shows, when the mask
  only exists to confine a BG2/OBJ effect.
- **Option b:** keep suppressing, with the F6 fade instead of a pop.

Pick per case and document it in move_audit.md.

### F4: `SetSpriteBgBlending` and alpha targets

`BattleAnimUtil_SetSpriteBgBlending` and similar calls make BG0 a blend target. Opaque 3D
pixels then blend with EVA/EVB, so the arena turns see-through over BG3.

Where the blend is meant for the mon only, leave the arena opaque and give the effect to
the mon instead. With the arena at alpha 31 and the stage sprite drawn with the sprite
alpha the move asked for, BG0 must not be the 1st target with plain EVA/EVB.

Where you can't separate the two, keep today's look; at home it matches BG3 anyway.

### F5: HBlank waves

Per-line scroll of BG3 is invisible under the arena, and per-line scroll of BG0 waves the
arena and the mons together.

Detect a per-line BG3 effect: the HBlank/buffer manager in battle_anim_helpers.c or its
callers targets BG3. Treat it as `BG_SWITCH`, so the arena fades out (F6) and the wave
shows.

Leave BG0 waves as they are, and note which moves use them in the audit; they are chunk 6
material.

### F6: fades instead of pops

When a suppression reason starts during a move animation, fade the arena out instead of
hiding it at once:

- Drop the arena polygons' alpha from 31 to 0 over `SCREEN_FRAMES(8)` drawn frames.
  Use `SCREEN_FRAMES` from battle_stage_camera.c; the timings count 60 Hz frames and the
  logic steps at 30 Hz.
- Keep BG3, now showing the move background, visible under it.
- When the reason ends, fade back in over the same time.

While fading:

- The sprites stay on the stage path, so there is no tint pop.
- The arena uses translucent polygons. Keep the polygon IDs and sort order such that the
  blobs, the particles and the sprites still draw correctly over it.
- Fog, lighting and the depth remap are unchanged.

`BattleStage_IsVisible()` stays TRUE until the fade reaches 0. The classic OBJ platforms
fade in with BG3 via their OBJ alpha, or appear at alpha 0 of the arena if they can't.

A reason that starts and ends within the fade time reverses the fade from where it is.

**Suppressions that must still be instant:**

- `BATTLE_STAGE_SUPPRESS_MENU`: the bag and party screens own VRAM.
- The debug A/B toggle.
- Anything outside a move animation.

These count as `hardPops` only when they happen during a move animation. The script end
must leave the arena at alpha 31, or hidden with a reason still active.

Keep `arenaAlpha` current, increment `fades` on each fade-out, and increment `hardPops`
on each visible-to-hidden transition that skipped the fade. Count `hiddenFrames` on every
drawn frame in which the arena is loaded and enabled but hidden.

### Out of scope

Per-move rewrites and stage upgrades (Earthquake shaking the camera, Dig opening the
ground, and so on) are chunk 6. Contests never touch the stage: keep the
`BattleAnimSystem_IsContest` guards.

## 3. Stat changes on the live sprite

The stat change effects (`Func_StatChangeUp`, `Down`, `Heal`, `Metal`, in
`script_funcs_stat_change.c`: the `stat_boost` and `stat_drop` common animations,
`restore_hp`, Harden, Iron Defense, Metal Claw, Iron Tail, Present) scroll a pattern on BG2
(BG `BATTLE_BG_BASE`, pl_batt_bg members 0x36-0x3D) and show it only inside an OBJ window
cut by an `AddPokemonSprite` copy of the mon, blended 12/16 over a second, visible copy. BG0
is hidden inside the window. The copies are the classic 80x80 frame at the battler's classic
place. On the stage the mon is a mesh drawing its Gen 5 stream: other frames, a canvas wider
than 80x80, a back sunk by up to 40 px. The effect then landed on what looked like a frozen
clone of the mon, with the live sprite's edges showing around it (Arc 1 playtest bug 5:
Fake Tears on the player's Chimchar).

While the stage draws the battler, the stage draws the effect instead:

- `BattleStage_StartStatEffect` (battle_stage_sprites.c), called when the effect starts,
  takes it over when the battler was drawn as a mesh or as a flat stream in the last frame
  (`meshMask`, `streamedMask`) and `CLASSIC_SPRITES` is off. It builds the pattern from the
  same BG members: the top-left 64x64 px of the tilemap as a 64x64 4bpp texture (the four
  patterns repeat every 32 or 64 px in the 256 columns the screen shows), the first 16
  colours of the palette, both queued on the VramTransfer list. Texture and palette VRAM
  (2 KB and 32 bytes, in bank B) are taken once per battle in `BattleStageSprites_Init`.
  When it returns FALSE (a classic sprite, no VRAM, no arena) the 2D effect runs as before,
  which matches a classic quad.
- The task then skips its BG, window, blend and copies (all three copies are hidden), and
  every frame passes the BG's Y scroll and EVA to `BattleStage_SetStatEffect`; the end of
  the task, and the anim system's End and Delete, call `BattleStage_EndStatEffect`. The
  timing is unchanged.
- The draw hook draws the mesh a second time, vertex for vertex, after the mon: the pattern
  texture (repeat on) at the screen pixel each vertex lands on plus the scroll, as BG2
  would show it there, unlit white, polygon alpha EVA * 31 / 16 (12/16 over 4/16 of the mon
  is 23/31), polygon ID 60, and the depth test set to equal
  (`GX_POLYGON_ATTR_MISC_DEPTHTEST_DECAL`). Identical vertices give identical depths, so the
  pattern lands on exactly the pixels the mon drew: its current stream frame, its scale, its
  sink and breathing, nothing around it. A flat stream (arena hidden, texture VRAM kept)
  draws its quad twice the same way.
- A translucent mon writes no depth, so the overlay skips a mon whose alpha is under 31.
  The pattern is not lit or tinted, as BG2 isn't. Particles in front of the mon (Harden's)
  stay visible, where the 2D effect hid BG0 inside the window.

`sStatFx` (battle_stage_sprites.c, in the xMAP) counts `starts` (effects the stage drew) and
`drawnFrames` (overlay passes) per battle, for the harness. move_audit.md still lists these
moves with the window and OAM copy mechanisms, since that is what their scripts do; the
`stat change` notes there describe the 2D path only.

## Critic checks (new scenario `move_audit`, plus changes to others)

- The critic reads the compat fields when the xMAP says sBattleStage is at least 120 bytes.
- `move_audit` plays the audit's `risk: high` moves from the move tester on a Plain battle.
  - At day, and again at night, for a capped list of about 25 moves. The cap takes the
    first moves of each mechanism so every mechanism is covered; `--moves` overrides it.
  - Per move:
    - The animation finishes, and the normal look is restored 90 frames later, as in
      move_tester.
    - `hardPops` does not rise during the move.
    - `arenaAlpha` is 31 after the move.
    - No CPU exceptions.
  - For moves the audit tags `bg2_copy`: `liftedBg2Frames` rises, the arena stays visible
    (`hiddenFrames` does not rise), and at night the copy is tinted: the copy's pixels
    differ from the day copy in the same way the mesh does.
  - For moves the audit tags `switch_bg`: `fades` rises, and the frames in the middle of
    the fade show both the arena and the move background (a mixed frame, not a pop). A
    contact sheet `sheet_fade` shows a few of them frame by frame.
- `stage_ab`, `move_tester`, `switchbg_moves`, `sprite_life`, `camera`, `mega` and
  `totem_battle` still pass. `switchbg_moves` expects fades instead of instant hides.
