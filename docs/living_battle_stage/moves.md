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
