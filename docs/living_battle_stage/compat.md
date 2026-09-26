# 3D battle stage: compatibility hooks

The arena is drawn on BG0, the 3D layer, at priority 1. The classic backdrop is BG3
(256 colours, priority 3). The move animation "base" layer is BG2 (16 colours). At equal
priority the lower BG number wins, so BG0 covers both BG2 and BG3.

Anything that replaces or animates the backdrop, or draws on BG2 under BG0, would be hidden
behind the arena. For those effects the arena is suppressed through
`BattleStage_Suppress(reason, TRUE/FALSE)` (include/battle/battle_stage.h). While it is
suppressed, the classic BG3 backdrop and the OBJ platforms show instead. At the home pose the
arena matches the classic backdrop, so the swap is nearly invisible.

`BattleStage_Init` clears every reason at the start of each battle. A reason that is left set
can therefore only last until the end of the current battle.

## Hooks

Line numbers are for commit `compat: suppression hooks` on this branch.

### BG_SWITCH and BG2_EFFECT: one central evaluator for move animations

All of this is in `src/battle_anim/battle_anim_system.c`.
`BattleAnimSystem_UpdateStageSuppress` (line 452) recomputes both bits from the current state.
It never counts calls, so a missed "clear" cannot leak: the next evaluation fixes it.

In contests it returns early (line 454), because the battle overlay, and with it
battle_stage.c, is not loaded there. `BattleAnimSystem_Delete` checks for contests in the same
way.

**BG_SWITCH** (line 471) is set while any of these is true:

- `bgSwitchState != NONE`: a SwitchBg, SwitchBgEx or RestoreBg fade task is running. This also
  covers a restore fade that outlives the script's `End`.
- While a move is active:
  - `stageBgDirty` is set, because the script used `SetBg`. No shipped script uses it.
  - `bgAnim != NULL`, meaning a BG3 scroll or wobble task (Psychic, and others) exists. The
    pointer stays set until `End`, so this is conservative.
  - BG3 is not in its normal battle mode: it is hidden, not 256-colour, or its char base has
    moved away from 0x10000. `BattleAnimSystem_IsEffectBgNormal` (line 383) checks this. It
    catches the special backgrounds (Night Shade, Dark Pulse, Psychic and others) for as long
    as they are loaded, including when a script leaves them up until `End`.
  - BG3 has a non-zero X or Y offset (line 466). Earthquake, Magnitude and the generic shake
    func (script_funcs_0.c, lines 1949 and 2209; script_funcs_3.c, line 849) move BG3 directly,
    without a `bgAnim` task. The offset passes through 0 during a shake, so the arena may
    come back for single frames. At the home pose both looks are the same there.

**BG2_EFFECT** (line 472) is set while a move is active and BG2 would be covered by BG0.
`BattleAnimSystem_IsBaseBgUnderStage` (line 402) checks this. All of these must hold:

- BG2 is visible.
- BG2's priority is not above BG0's.
- If windows are on, BG0 and BG2 are both enabled in at least one window region (outside,
  W0, W1 or the OBJ window).
- BG2's tilemap buffer has a non-zero entry.

This covers the effects that copy a battler onto BG2: Acid Armor, the fog of Haze and Mist,
Minimize, Substitute's swap, and others.

The evaluator is called from these places:

| where | line | why |
|---|---|---|
| `BattleAnimSystem_ExecuteScript` | 639 | Every frame of a move, after the script function has run. This catches BG3 mode changes and BG2 tilemap writes. When `End` runs, `moveActive` goes FALSE, so the move-only conditions drop on that same frame. |
| `BattleAnimSystem_CreateBgSwitch` | 2504 | A SwitchBg, SwitchBgEx or RestoreBg task starts. The arena hides on the same frame the fade begins. |
| `BattleBgSwitchTask_Start`, completion | 3038 | A switch or restore task finishes, possibly after `End`. The bit clears once the fade is done. |
| `BattleAnimScriptCmd_SetBg` | 3139 | Sets `stageBgDirty`. |

The flag is reset elsewhere:

- `BattleAnimSystem_StartMove` (line 617) resets `stageBgDirty`.
- `BattleAnimSystem_Delete` (line 488) clears both bits. This is the release point when the
  animation system goes away at the end of the battle. It also runs for the short-lived second
  animation system in `battle_display.c` (line 1918). That system runs alone, and the main
  system re-evaluates every frame while it is active.

`stageBgDirty` is the old unused `u8 unk_17B` in `BattleAnimSystem`
(include/battle_anim/battle_anim_system.h, line 218). The struct layout is unchanged.

### BRIGHTNESS: the Mega Evolution affine pulse

This is in `src/battle/battle_display.c`.

- **Set**: `AffinePulse_Charge`, first frame (line 5488). The pulse darkens BG2, BG3, OBJ and
  the backdrop with the 2D brightness blend. BG0 is left out, so the orb particles stay bright.
  Without suppression, the arena on BG0 would stay fully lit over the darkened scene.
- **Clear**: `AffinePulseTask`, `if (done)` block (line 5606), where the task deletes itself.
  The task always reaches this block. It has no early exit.

### MENU: after a capture

This is in `src/battle/ov16_0223B140.c`.

- **Set**: at the start of `ov16_0223B53C` (line 365). This function is called only from the
  capture sequence (`battle_script.c`, lines 10865 and 10921). The Pokedex entry screen takes
  over BG0 and VRAM, and then the classic platforms stay hidden (`ov16_022686BC(..., 0)`).
- **Clear**: deliberately not cleared in `ov16_0223B578`. After a capture the battle only shows
  its end messages, and the classic look has no platforms from then on either.
  `BattleStage_Init` clears it at the next battle.

## Cases that need no hook

| case | why it is fine |
|---|---|
| Palette fades (`PaletteData_StartFade`, BlendPalette, the move palette tints) | The arena takes its colours from the same palette or fades with the screen. The brief exempts palette effects. |
| Master brightness (screen fades in and out, battle end, the flash on a KO) | Master brightness covers the whole screen, BG0 included. |
| The anim `BrightnessController` (script brightness commands) | Its plane mask includes BG0, so the arena darkens with everything else. |
| Alpha blends on sprites (`G2_SetBlendAlpha` with BG0 as a second-target plane) | The arena is a valid blend target like the old BG3. |
| Window effects on W0 (spotlights, wipes) | The window masks BG0 like the other planes. `IsBaseBgUnderStage` looks at the window masks, so a window that hides BG2 does not trigger a suppression. |
| Bag, party and move-info screens | They use the bottom screen (sub engine, VRAM bank C/D) and leave the main BG0/BG3 and the 3D engine alone. The `bag_party` scenario checks that the top screen is the same before and after. |
| Sub-screen BG loads during a battle (touch panel pages) | Bottom screen only. |
| The level-up stat box | Drawn on BG2 at priority 0, which is above BG0, so it is not covered. The evaluator also skips it for this reason, and only checks while a move is active. |
| The nickname / naming screen after a capture | It runs as its own application after the battle overlay has stopped drawing. `BattleStage_Draw` does not run. |
| Evolution | Happens after the battle has ended. |
| The ball throw, catch shakes and sparkles | These are OBJ and particles above BG0. |
| The Totem aura | Particles and a palette pulse on the sprite. No BG change. |
| The move tester (battle_debug.c) | It plays moves through the normal `BattleAnimSystem`, so the central hooks cover it. |
| Contests | Suppress is never called. The battle overlay is not loaded there. |

## Scenarios

The emulator critic (tools/battle_stage/emu/README.md) has one scenario for each part:

- `stage_ab`: toggles the stage OFF and ON and diffs the home pose.
- `switchbg_moves`: plays Night Shade, Psychic, Dark Pulse and Acid Armor with the stage on.
- `bag_party`: opens the bag and the party screen, returns, and compares the top screen.
- `debug_views`: checks the L+R+B camera views.

## Risks and follow-ups

- **Mega pulse.** The renderer could apply the BLDCNT brightness to the arena itself and
  drop the BRIGHTNESS suppression.
- **BG2 effects.** A renderer path that composites BG2 over the arena would let
  fog and Acid Armor play without falling back to the classic look.
- **`bgAnim` is only checked as a pointer.** A cancelled scroll task leaves the pointer set
  until `End`. This can only suppress longer than needed, never shorter.
- **A script that ends without restoring BG3.** BG_SWITCH clears at `End`, even if BG3 still
  holds a special background, and the arena then covers it. No shipped script ends that way.
- **Order at battle end.** `BattleStage_Free` runs before `BattleAnimSystem_Delete`
  (ov16_0223B140.c, lines 767 and 773), so the Delete hook calls `BattleStage_Suppress` after
  `BattleStage_Free`. This is harmless while the stage state is a static struct. The
  renderer must keep `BattleStage_Suppress` safe to call after `BattleStage_Free`.
- **BG3 offsets.** The offset check assumes BG3 sits at (0, 0) whenever no move is shaking it,
  as it does after `Bg_InitFromTemplate` (ov16_0223B140.c, line 431). A renderer that follows
  the BG3 offset could drop this condition.
- **Camera off the home pose.** In the debug views, and in later chunks, the swap to the
  classic look during a suppression will show as a jump.
