#include "battle/battle_bdsp_overlay.h"

void BattleBdspOverlay_Reset(void)
{
}

BOOL BattleBdspOverlay_ShouldUse(BattleSystem *battleSys)
{
    (void)battleSys;
    return FALSE;
}

void BattleBdspOverlay_StartBag(BattleBagContext *ctx)
{
    (void)ctx;
}

void BattleBdspOverlay_StartParty(BattlePartyContext *ctx)
{
    (void)ctx;
}

BOOL BattleBdspOverlay_IsActive(void)
{
    return FALSE;
}

void BattleBdspOverlay_TickAndFillFrame(BattleSystem *battleSys, SIM_HudHD_Frame *frame)
{
    (void)battleSys;
    (void)frame;
}
