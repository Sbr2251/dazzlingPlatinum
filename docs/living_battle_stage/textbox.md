# The battle message box fades (BW2 parity, workstream "layout")

Black 2/White 2 hide their top-screen message box whenever no message is up. Platinum keeps it up
for the whole battle, where it covers the bottom 48 rows of the top screen through every
animation. The battle now does what BW2 does, on the 3D stage.

Code: `src/battle/battle_textbox.c` (the fade), `src/battle/battle_stage_layout.c` (the
move-animation command's wait). Header: `include/battle/battle_textbox.h`.

## What BW2 does (pokebw2)

- The box is a BmpWin on main BG1, on the top screen: 30x4 tiles at row 19, framed
  (`btlv_scu.c:407, 420`). It is not on the touch screen.
- `BtlvScuWinFade` (`btlv_scu.c:2290-2357`) fades it with an alpha blend. BG1 is the first
  target, and BG0, BG2, BG3, OBJ and the backdrop are the second. The fade runs over 6 frames
  at 60 Hz. EVA goes from 31 to 0 and EVB from 7 to 16, and back for a show.
- It hides before every move effect (`BtlvScu_MoveEffectProc`, `:1941-1960`), before every step
  of the encounter and send-out choreography (`:646-1743`), and when the server starts the
  turn-end checks (command 0x56, `btl_server_flow.c:4993`, `btl_client.c:5489`).
- It shows for every message (`BtlvScu_WaitMsg`, `:1841-1844`). That includes the "What will X
  do?" prompt, which the client prints before the command menu starts (`btl_client.c:2136-2153`).
  So BW2 keeps the box up at the command menu; nothing in btlv hides it there.
- After a message has printed, BW2 waits `wait` frames (80 for every standard message) before
  the next step, or less if A, B or the touch screen is pressed (`:1885-1893`).
- BW2's box rests at EVA 31 / EVB 7 over a black fill (palette index 12 of NCLR 0x165), so it is
  a dark, translucent box that the scene shows through. Ours is Platinum's opaque white box. The
  fade below crossfades it from opaque to gone, because a 7/16 blend over a white box would only
  wash it out.

## What the battle does now

- **Start:** the battle opens with the box hidden when the stage is visible (`BattleTextbox_Init`,
  after `BattleStage_Init`). It is empty until the first message.
- **Show:** every message printed in the box shows it (`BattleTextbox_NotePrint`, called by
  `BattleMessage_Print`, `BattleMessage_PrintToWindow` for window 0, and the trainer message print
  `ov16_0223F9FC`). A hidden box fades in over 6 vblanks, starting on the frame the text starts
  printing; the first letter or two print during the fade.
- **Hide:** the move-animation battle command (`ov16_0225D9A8`, task `ov16_022626C0`) asks for a
  hide and waits before its first script until the box is gone. This covers every move animation, multi-hit hits, and the status,
  weather, stat, item and ability animations, which all come through that command. The box then
  stays hidden until the next message: across all the hits of a multi-hit move, the HP drain, a
  faint, and the turn-end weather animation.
- **Text first:** a hide waits while the message prints, and then for 30 vblanks
  (`TEXTBOX_READ_HOLD`, half a second) after its last letter, unless A or B is held (BW2: 80
  frames, skippable). Platinum plays the move right after "X used Y!", so without the hold the
  box would go the moment the line finished. If the text is still being read after 90 logic
  frames (`TEXTBOX_READY_WAIT_MAX`, 3 s: a message waiting for a key press), the animation plays
  with the box up instead.
- **Kept up:**
  - The Mega Evolution animation (and the Substitute doll stepping aside for it):
    `subscript_mega_evolution.s` keeps "X is reacting to Y's Key Stone!" up through the
    animation on purpose.
  - Anything off the stage. With the stage off or no arena, the classic BG3 leaves rows 160..191
    black, so the box never hides there and the classic path is unchanged.
  - A player-side back sprite that the stage draws from Platinum art with its art running into
    the frame's bottom row (the form species such as Giratina, Spinda, the classic Substitute
    doll). The box keeps hiding the cut, as in Platinum. The Gen 5 streams stand on their feet.
- **The fade:** BG1 is the first target, and BW2's second targets are kept. Each update steps the
  level by the vblanks since the last one (6 for a whole fade), since the battle logic runs at
  30 Hz. At the end of a hide, BG1 is switched off (`GXLayers_EngineAToggleLayers`) before the
  blend registers are given back, and a show writes the blend before BG1 goes on, so the box never
  flashes in whole for a frame. Only a BG1 that the box switched off is switched on again.

## The blend registers are shared

Move animations, the Mega pulse, the party gauge's arrow, the Totem aura and the stage's fade all
write `BLDCNT`/`BLDALPHA`. The fade takes them only when no first target is set, which is the
battle's idle state (`G2_BlendNone`, or `BattleAnimSystem_SetDefaultAlphaBlending`). It saves
them and gives them back at the end if they are still what it wrote. If someone else writes them
mid-fade, the fade ends at once in its end state (`snaps` in the stats). If they are busy when a
fade should start, BG1 just goes off or on. The hide always happens before the script starts, so
it never fights a move's own blend.

## The cut guard

`UpdateCutGuard` reads `BattleTextbox_IsClear()`. The limit is 144 while any of the box shows,
and 192 from the moment it starts to fade out. The existing 8-frame ease of the limit handles
the change (cut_guard.md).

## The command menu (item 2: not done)

The brief asked to hide the box at the command menu "as BW2 does from memory", but only if the
prompt would still show. Both conditions fail:
- BW2 prints the prompt into the top-screen box and fades the box in for it (above). Its box is
  translucent, which is probably why the scene seems to show at the menu.
- Our touch screen has no prompt. It shows the party balls and the FIGHT, BAG, RUN and POKEMON
  buttons, and nothing else (`/tmp/bw2vis/layout/strips/command_menu.png`). Hiding the box
  would hide "What will X do?".

So the box stays up at the command menu. A BW2-style translucent box (the dark fill, white text
and the 31/7 rest blend) would give the look without losing the prompt. That is a reskin of the
message box and its text colours, so it is left as a follow-up.

## Debug fields: `sBattleTextbox` (xMAP)

| offset | field | meaning |
|---|---|---|
| +0 | `u8 state` | 0 shown, 1 hiding, 2 hidden, 3 showing |
| +1 | `u8 level` | 0 (hidden) .. 6 (shown) |
| +2 | `u8 hidePending` | a hide waits for the text to be read |
| +3 | `u8 suspended` | BG1 lent to the Pokedex entry after a capture |
| +4 | `u32 hides`, `shows`, `snaps`, `keptUp` | fades started, fades ended at once, hide requests the box ignored |
| +20 | `u32 hiddenVBlanks` | vblanks fully hidden |
| +24 | `u32 printsWhileHidden` | prints that found the box hidden or fading out |
| +28 | `u32 readHoldVBlanks` | the longest a hide waited for the text |

## Cost

No VRAM, no polygons, no heap. Every move-animation command waits for the fade: 3 to 4 logic
frames (6 to 8 vblanks), plus the read hold after a message that the script didn't already wait
on (only "X used Y!" and a few like it). Measured on the probe turns, a turn is 36 to 82 frames
longer (`/tmp/bw2vis/layout/README.md`).
