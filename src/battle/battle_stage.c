#include "battle/battle_stage.h"

#include <nitro.h>

#include "config/battle_stage.h"

typedef struct BattleStage {
    BattleSystem *battleSys;
    BOOL enabled;
    u32 suppressed;
    int debugView;
} BattleStage;

static BattleStage sBattleStage;

void BattleStage_Init(BattleSystem *battleSys)
{
    sBattleStage.battleSys = battleSys;
    sBattleStage.enabled = BATTLE_STAGE_3D;
    sBattleStage.suppressed = 0;
    sBattleStage.debugView = 0;
}

void BattleStage_Free(void)
{
    sBattleStage.battleSys = NULL;
}

void BattleStage_Draw(void)
{
#if BATTLE_STAGE_3D
    if (sBattleStage.battleSys == NULL || sBattleStage.enabled == FALSE) {
        return;
    }

    // Chunk 1 draws the arena here
#endif
}

void BattleStage_SetEnabled(BOOL enabled)
{
    sBattleStage.enabled = BATTLE_STAGE_3D && enabled;
}

BOOL BattleStage_IsEnabled(void)
{
    return sBattleStage.enabled;
}

void BattleStage_Suppress(u32 reasons, BOOL suppress)
{
    if (suppress) {
        sBattleStage.suppressed |= reasons;
    } else {
        sBattleStage.suppressed &= ~reasons;
    }
}

BOOL BattleStage_IsVisible(void)
{
    // Chunk 1 also requires the arena to be loaded for this battle
    return sBattleStage.battleSys != NULL && sBattleStage.enabled && sBattleStage.suppressed == 0;
}

void BattleStage_SetDebugView(int view)
{
    sBattleStage.debugView = view;
}

int BattleStage_GetDebugView(void)
{
    return sBattleStage.debugView;
}
