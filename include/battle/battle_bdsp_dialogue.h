#ifndef POKEPLATINUM_BATTLE_BDSP_DIALOGUE_H
#define POKEPLATINUM_BATTLE_BDSP_DIALOGUE_H

#include "battle/battle_system.h"
#include "port/sim_hud_hd.h"
#include "string_gf.h"

// BDSP HD Battle Dialogue Box controller (owned by Lane 1: dialogue).
// Captures BattleMessage_Print text & live typewriter progress, suppresses the
// old pixel-art BG_LAYER_MAIN_1 battle text box when HD BDSP mode is active,
// and fills frame->dialogue every battle frame.
void BattleBdspDialogue_Reset(void);
void BattleBdspDialogue_OnMessagePrint(BattleSystem *battleSys, const String *msg, u8 printerId, int textSpeed);
void BattleBdspDialogue_FillFrame(BattleSystem *battleSys, SIM_HudHD_Frame *frame);
BOOL BattleBdspDialogue_IsActive(void);

#endif // POKEPLATINUM_BATTLE_BDSP_DIALOGUE_H
