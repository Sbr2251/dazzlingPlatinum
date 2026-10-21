# Battle events (BW2 visual parity: battle-events workstream)

Four Gen 5 battle events with no BW2 effect script behind them. Reference: pokebw2 @ df7fa79a0 (read-only).

| event | code | BW2 reference |
|---|---|---|
| Ability pop-up banner | `src/battle/ability_popup.c`, hook in `BattleDisplay_PrintMessage` (`battle_display.c`) | `BtlvScuAbilityWin`, `src/ov167/btlv_scu.c:2472-2683`; shown by `btl_client.c:5960, 6003, 6154` |
| Critical capture | `BattleEvents_RollCriticalCapture` (`src/battle/battle_events.c`), `BattleScript_CalcCatchShakes` and `BattleScript_CatchMonTask` (`battle_script.c`) | `CheckBallCapture` / `CheckCriticalCapture`, `src/ov167/btl_server_flow_sub.c:899-952, 1045-1072` |
| Gym Leader "last Pokemon" music | `BattleEvents_OnTrainerMessage` (`battle_events.c`), hook in `BtlCmd_PrintBufferedTrainerMessage` | `BattleClient_ActionTrainerHint`, `src/ov167/btl_client.c:2243-2279` |
| Low-HP beep vs the low-HP music layer | `BattleEvents_SuppressLowHPBeep`, `SoundLayers_IsActive` (`src/sound_layers.c`), the beep task `ov16_0223CF8C` (`ov16_0223B140.c`) | `btlv_gauge.c:1459-1501` (pinch BGM, no beep) |

`gBattleEventsDebug` (`include/battle/battle_events.h`) is a debug block in the battle overlay's `.data` (magic `BEVT`)
that the headless checks read; `forceCriticalCapture` is the only field anything writes (the harness, in battle).
`BattleEvents_Shutdown` ends the banners, the capture flash and a pending music switch before the battle frees its
systems (`ov16_0223B140.c`, just before `ov16_0223BCB4`).

## Ability pop-up banner

**BW2.** Each side has an 18x4-character banner: the player's on BG2 at screen (0,112), the foe's on BG3 at (120,48)
(screens 0x1E5/0x1E6, characters 0x1E3, BG palette 1). On an ability activation the server sends "pop-up in": the
banner scrolls in from its own screen edge, 144 px in 8 updates (18 px each) with SE_SHOOTER; then "<Pokemon>'s" and
"<Ability>" (message 0x67) appear one character column per update; then a white palette flash with SE_DECIDE6. The
activation's messages print with the banner up, and "pop-up out" (sent after them) hides it at once. A pop-up for
another Pokemon on the same side replaces the shown one. The text: line 1 from the left, line 2 ending 12 px before the
right edge, the two overlapping by at least 12 px.

**Here.** BG2 (move effects) and BG3 (classic backdrop) are taken, so the banner is OBJs: a FontOAM (`unk_02012744.c`)
built from a Window holding BW2's banner art with the text composited on it. Platinum's scripts have no pop-up in/out
commands, so the trigger is the message path:

- `AbilityPopup_OnBattleMessage` reads every message `PrintMessage` / `PrintBufferedMessage` print. A message whose tags
  pair a battler's name with an ability (`TAG_NICKNAME_ABILITY*`, `TAG_ABILITY_NICKNAME`, both pairs of
  `TAG_NICKNAME_ABILITY_NICKNAME_ABILITY`) shows that battler's banner; so do Trace (`TAG_NICKNAME_NICKNAME_ABILITY`,
  message 00679, shows Trace) and Frisk (`TAG_NICKNAME_ITEM`, message 01118). This covers Intimidate (the stat
  message's `TAG_NICKNAME_ABILITY_NICKNAME_STAT`), Drought/Drizzle/Sand Stream/Snow Warning, Pressure, Mold Breaker,
  Levitate, Forewarn, Anticipation, Slow Start, contact abilities, Synchronize, the Totem's "exerting its" line, and so
  on. An ability whose message names no ability (Truant's "loafing around") gets no banner.
- **The text is kept**: the banner starts with the message (BW2 shows it 25 updates before), so nothing is shown twice
  in a different order. A second message about the same activation (Intimidate on two foes) keeps the banner up.
- Timing in battle updates (the battle's tasks run at 30 Hz, like the healthbar drain): slide in 8 x 18 px with
  `SEQ_SE_DP_SLIDEIN`; reveal one column per update (18); flash: the banner palette from white back over 8 updates
  with `SEQ_SE_DP_DECIDE`; hold while the message's printer runs plus 45 updates (Platinum follows ability lines with a
  30-60 frame `WaitButtonABTime`); slide back out 8 x 18 px (BW2 jumps out; the brief asked for a slide).
- Hardware: 2.25 KB of OBJ VRAM (144x32 at 4bpp) (`CharTransfer_AllocRange`, from the end) and one OBJ palette (`PlttTransfer`,
  resource 0xAB10 + side) per banner, taken when it shows and given back when it leaves, so nothing is held between
  activations; at most 3 OBJs per banner (64x32, 64x32, 16x32). If VRAM or a palette cannot be had, the banner is
  skipped (`popupSkipped`) and the text still prints. The Mega button is a sub-screen BG, so it shares nothing. No
  polygons. Heap: about 6 KB while a banner shows (window, composed copy, FontOAM cell banks).
- Placement is BW2's: the player's banner over the player's back sprite at y 112, the foe's at the right edge at
  y 48. OBJ BG priority 0 and list priority 0: over the healthbars. It works the same with the stage off.
- Text: "<nickname>'s" (the healthbar's nickname template plus ' and s) and the ability name, in the system font,
  white with a dark shadow (banner colours 1 and 2), at y 0 and 13 (Platinum's 16-row cell centres the ability in the
  banner's dark bar, rows 13-26).
- Battle overlay: +8 KB (259,904 -> 268,096 bytes in `battle.sbin`), 4.6 KB of it the two banners' characters.

Assets: `res/battle/ability_popup/bw2_ability_banner_483.png` and `bw2_ability_banner_484.pal` are pokebw2's
`res/graphics/btlv/483.png` / `484.pal` (BW2 a/0/1/1 files 0x1E3/0x1E4). `tools/battle_events/make_ability_banner.py`
turns them into `src/battle/ability_popup_banner.h`.

## Critical capture

**Mechanic (BW2).** After the modified catch rate `a` is known (and before the shake checks), a critical capture is
rolled: with `n` species caught (National Dex), ratio = 0 (n <= 30), 0.5 (> 30), 1 (> 150), 1.5 (> 300), 2 (> 450),
2.5 (> 600); critical if `Random(256) < min(a, 255) * ratio / 6`. A critical capture makes **one** shake check instead
of the usual ones; it shows one shake and the click, or breaks out with no shake (BW2's shake count 0). The Master Ball
never rolls one.

**Here.** `BattleScript_CalcCatchShakes` keeps Platinum's catch rate and shake formula (4 checks) and adds the roll on
the same `a`, with BW2's thresholds unchanged. This hack's dex is smaller than BW2's 649, so the 2.5x tier cannot be
reached; and under 31 species caught there is no chance at all, as in BW2. A critical success shows one shake
(`REMAINING_SHAKES = 1`), a critical failure breaks out at once. The catching tutorial and `BATTLE_TYPE_ALWAYS_CATCH`
return before the roll.

**Visual (approximation).** BW2's own critical-capture visual lives in its capture effect script (0x23a, archive
a/0/6/6, not extracted in pokebw2), so it is approximated with what the battle has: when the ball has landed, before its
one shake, the main screen's 2D brightness goes to white in 3 steps and back in 10 (`BrightnessController`, as the
battle's own white flash in `ov16_022646C8`; the 3D arena follows the 2D brightness; the text box is left out), with
`SEQ_SE_DP_KIRAN` (a gleam, in `BANK_SE_BATTLE` so it is loaded in battle; BW2's own capture SE is not used).

## Gym Leader "last Pokemon" music

**BW2.** When a Gym Leader class shows trainer hint 19 or 20 (last Pokemon / last Pokemon at half HP), the battle theme
fades out over 8 frames and BGM 0x47B starts, once per battle (`unk1BA_0`); with the pinch BGM up it is only reserved.

**Here.** `BtlCmd_PrintBufferedTrainerMessage` calls `BattleEvents_OnTrainerMessage`. On `TRMSG_LAST_BATTLER` or
`TRMSG_LAST_BATTLER_HALF_HP` from a `TRAINER_CLASS_LEADER_*` trainer, while `SEQ_BATTLE_GYM_LEADER` is on the BGM
player, the theme fades out over 8 frames and **`SEQ_BATTLE_FRONTIER_BRAIN`** starts. It is a BGM swap, not a layer:
the Gym Leader theme has no layer tracks (`sound_layers.c` has a table entry only for the wild theme), and authoring
some would mean editing the sequence.

Why `SEQ_BATTLE_FRONTIER_BRAIN` (Platinum's Frontier Brain battle theme, already in the SDAT; no BW2 audio):

- it is the step up from the Gym Leader theme in the same register: a boss-battle arrangement from the same game and
  sound set, faster and denser;
- it has no story meaning a player of Arcs 1-2 knows: the Battle Frontier is post-game, while the Elite Four,
  Champion, Galactic Commander and Cyrus themes all belong to story moments (Cyrus's Arc 2 battles already borrow the
  Gym Leader theme);
- it is a full battle loop, so it carries the rest of the fight, and the victory jingle (`SEQ_VICTORY_GYM_LEADER`,
  chosen by trainer class) is unchanged.

It covers every leader in Arcs 1-2: Roark, Gardenia, Maylene, Wake and Fantina all carry `TRMSG_LAST_BATTLER` and
`TRMSG_LAST_BATTLER_HALF_HP` lines and fight single battles. Maylene's one-Pokemon Meteor trial has no last-Pokemon
line, so it keeps its music (BW2 also needs more than one Pokemon in the party). Double battles have no trainer
messages in Platinum, so a double leader battle keeps its music too. The swap happens once: the half-HP line that
follows finds the new theme playing.

Debug: L+R+Y in the field (`src/debug_quick_battle.c`, `DEBUG_BATTLE_TOOLS`) battles Roark, Gardenia, Maylene, Wake and
Fantina in turn (the panel's second line shows the next one).

## Low-HP beep vs the low-HP music layer

BW2 has no low-HP beep: red HP on a player Pokemon pushes a pinch BGM instead. The hack's `BGM_LAYER_LOW_HP` plays that
part, so while it plays Platinum's looping `SEQ_SE_DP_HINSI` is held off (and stopped if it was on).
`SoundLayers_IsActive(BGM_LAYER_LOW_HP)` is TRUE when the layer is on **and** the song on the BGM player has tracks
for it; the beep task (`ov16_0223CF8C`) asks every frame. A theme without the layer (every theme but
`SEQ_BATTLE_WILD_POKEMON` today, the Gym Leader and trainer themes included) keeps the beep, and the beep comes back
if the song changes to one without the layer.

## Verification

`tools/battle_events/be_verify.py` (with `belib.py`) runs the headless checks: offline-edited copies of the critic's
save (the lead's species, ability, stats and HP are changed in the .sav before boot, never in live RAM), the L+R
launcher, per-frame reads of `gBattleEventsDebug` and of the NitroSystem sequence players (`sSeqPlayer`, so the BGM
and SEs playing can be read on any build). Evidence: `/tmp/bw2vis/battle-events/README.md`.
