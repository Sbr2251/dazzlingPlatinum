#ifndef POKEPLATINUM_BATTLE_BATTLE_TEXTBOX_H
#define POKEPLATINUM_BATTLE_BATTLE_TEXTBOX_H

#include <nitro.h>

#include "struct_decls/battle_system.h"

// The battle message box (BG1, the top screen's bottom 48 rows) fades out before animations
// and back in when text prints, as Black 2/White 2's BtlvScuWinFade does (pokebw2
// src/ov167/btlv_scu.c:2290-2357): an alpha blend with BG1 as the first target over 6 screen
// frames. docs/living_battle_stage/textbox.md has the rules.
//
// Only while the 3D stage is the scene: the classic BG3 leaves rows 160..191 black, so on
// the classic path (stage off, no arena) the box never hides. Text always wins: the box never
// hides while a message prints, nor until it has shown for a moment after.

// At battle start, after BattleStage_Init: the box starts hidden when the stage is visible
// (it is empty; the first message fades it in)
void BattleTextbox_Init(BattleSystem *battleSys);
// Once per frame of the battle's draw task: steps the fade by the vblanks since the last call
// (6 vblanks for a whole fade, as BW2's 6 frames at 60 Hz) and writes the blend registers and
// the BG1 layer bit
void BattleTextbox_Update(void);
// A message started printing in the box (printerID from Text_AddPrinter*): shows the box now
void BattleTextbox_NotePrint(u8 printerID);
// Fade the box out once the text in it has been read (a pending hide; a print cancels it)
void BattleTextbox_RequestHide(void);
// TRUE once a requested hide is done, or when the box stays up instead (no stage, a cut
// back sprite, or the text is still being read after waitFrames logic frames)
BOOL BattleTextbox_IsReadyForAnim(int waitFrames);
// TRUE when no part of the box shows (hidden, or fading out): the cut guard's limit is the
// screen bottom then
BOOL BattleTextbox_IsClear(void);
// The box is hidden and BG1 is off because of it (debug, the critic)
BOOL BattleTextbox_IsHidden(void);
// BG1 is about to be freed or taken by another screen (the Pokedex entry after a capture):
// forget the fade without touching the registers; Resume when the battle's BG1 is back
void BattleTextbox_Suspend(void);
void BattleTextbox_Resume(void);

// Read by the critic (sBattleTextbox in the xMAP)
typedef struct BattleTextboxStats {
    u8 state; // TEXTBOX_STATE_*
    u8 level; // 0 (hidden) .. TEXTBOX_FADE_FRAMES (shown)
    u8 hidePending;
    u8 suspended;
    u32 hides; // fades out started
    u32 shows; // fades in started
    u32 snaps; // fades done at once (the blend registers were busy)
    u32 keptUp; // hide requests the box ignored (no stage, a cut back, text still read)
    u32 hiddenVBlanks; // vblanks with the box fully hidden
    u32 printsWhileHidden; // prints that found the box hidden or fading out (each shows it)
    u32 readHoldVBlanks; // the longest wait between a hide request and its fade, in vblanks
} BattleTextboxStats;

#endif // POKEPLATINUM_BATTLE_BATTLE_TEXTBOX_H
