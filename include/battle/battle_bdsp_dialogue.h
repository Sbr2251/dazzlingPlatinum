#ifndef POKEPLATINUM_BATTLE_BDSP_DIALOGUE_H
#define POKEPLATINUM_BATTLE_BDSP_DIALOGUE_H

#include "battle/battle_system.h"
#include "bg_window.h"
#include "port/sim_hud_hd.h"
#include "string_gf.h"

// BDSP HD Battle Dialogue Box controller (owned by Lane 1: dialogue).
// Captures BattleMessage_Print text, syncs live typewriter/page/wait state to
// the real TextPrinter, suppresses ONLY the battle message window when HD BDSP
// mode is active, and fills frame->dialogue every battle frame.
void BattleBdspDialogue_Reset(void);
void BattleBdspDialogue_Suspend(void);
void BattleBdspDialogue_Resume(void);
void BattleBdspDialogue_OnMessagePrint(BattleSystem *battleSys, const String *msg, u8 printerId, int textSpeed);
void BattleBdspDialogue_FillFrame(BattleSystem *battleSys, SIM_HudHD_Frame *frame);
BOOL BattleBdspDialogue_IsActive(void);
BOOL BattleBdspDialogue_ShouldSuppressWindow(const Window *window);

#endif // POKEPLATINUM_BATTLE_BDSP_DIALOGUE_H
