#include "battle/battle_bdsp_dialogue.h"

void BattleBdspDialogue_Reset(void)
{
}

void BattleBdspDialogue_OnMessagePrint(BattleSystem *battleSys, const String *msg, u8 printerId, int textSpeed)
{
    (void)battleSys;
    (void)msg;
    (void)printerId;
    (void)textSpeed;
}

void BattleBdspDialogue_FillFrame(BattleSystem *battleSys, SIM_HudHD_Frame *frame)
{
    (void)battleSys;
    (void)frame;
}

BOOL BattleBdspDialogue_IsActive(void)
{
    return FALSE;
}
