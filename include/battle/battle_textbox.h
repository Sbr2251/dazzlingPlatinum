#ifndef POKEPLATINUM_BATTLE_BATTLE_TEXTBOX_H
#define POKEPLATINUM_BATTLE_BATTLE_TEXTBOX_H

#include <nitro.h>

#include "struct_decls/battle_system.h"

#include "bg_window.h"
#include "palette.h"

// The battle message box (BG1, the top screen's bottom 48 rows) is a dark, translucent
// box, as in Black 2/White 2 (pokebw2 src/ov167/btlv_scu.c): an alpha blend with
// BG1 the first target and BG0, BG2, BG3, OBJ and the backdrop the second
// (BtlvScuWinFade_Init, btlv_scu.c:2290-2357). BW2 rests at EVA 31 / EVB 7 over a
// black fill; this box uses EVA 22 / EVB 10 over a dark blue-grey fill, so the
// scene shows through at about 60% and the box reads as a panel rather than a
// solid black rectangle. The box itself is always up on main (bw2vis's fade-out
// before animations is not ported); this module only owns the box's rest blend
// and its text palette.
//
// The blend registers are shared: move animations, the Mega pulse, the party gauge's
// arrow, the Totem aura and the stage fade all write BLDCNT/BLDALPHA. Update runs once
// per frame from the battle's draw task and only takes the registers back when they hold
// a known idle blend (blending off, or no first target at the idle 8/8 coefficients), or
// when they hold the box's own blend with its second targets trimmed by the stage fade.
// An effect that owns the blend (a first target other than BG1, a brightness flash, or
// no-first-target coefficients other than the idle 8/8) is left alone; when it ends in
// blending off or the idle blend, the box blend comes back on the next frame.
//
// Only the battle message window changes. Its text palette (BG palette slot 11) is the
// dark palette below; the level-up stat window (windows[1]) reuses that slot, so it
// loads the classic palette while it is up and the dark one again when it closes.

// At battle start, after BattleStage_Init: records the battle system; the box blend is
// written by the next Update
void BattleTextbox_Init(BattleSystem *battleSys);
// Once per frame of the battle's draw task: restores the box's rest blend when the
// registers are idle or hold the box's own blend
void BattleTextbox_Update(void);
// The Pokedex entry after a capture (and battle teardown) takes BG1: stop writing the
// blend until Resume, without touching the registers
void BattleTextbox_Suspend(void);
void BattleTextbox_Resume(void);
// The battle message window's text palette (BG palette slot 11): white text with a
// dark shadow over a dark blue-grey fill
void BattleTextbox_LoadTextPalette(PaletteData *paletteSys);
// The scroll cursor / wait dial palette (BG palette slot 10, the slot the
// frame palette used to own): white arrow, dark shadow, dark fill
void BattleTextbox_LoadCursorPalette(PaletteData *paletteSys);
// The classic text palette (BG palette slot 11), for the level-up stat window
void BattleTextbox_LoadClassicTextPalette(PaletteData *paletteSys);
// The level-up stat window (windows[1]) is up: it shares the message window's
// text palette slot, so Update keeps the classic palette in it while it is up
// (other writers, like the slot-11 palette animator's snapshot, would put the
// dark palette back). Clear when the stat window closes.
void BattleTextbox_StatWindowOpened(void);
void BattleTextbox_StatWindowClosed(void);
// Draws the battle message window: its tiles, no frame, and the scroll cursor
// on a dark background. The frame's thick white border is Platinum's, not
// BW's; the box is a borderless dark panel. The cursor's background tiles (the
// frame's tiles 10/11 on BG1) are overwritten dark, so the two squares at the
// box's right edge stop showing as light frame tiles.
void BattleTextbox_DrawMessageWindow(Window *window);

#endif // POKEPLATINUM_BATTLE_BATTLE_TEXTBOX_H
