#include "battle/battle_stage.h"

#include <nitro.h>

#include "config/battle_stage.h"

typedef struct BattleStage {
    BattleSystem *battleSys;
    BOOL enabled;
} BattleStage;

static BattleStage sBattleStage;

void BattleStage_Init(BattleSystem *battleSys)
{
    sBattleStage.battleSys = battleSys;
    sBattleStage.enabled = BATTLE_STAGE_3D;
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
