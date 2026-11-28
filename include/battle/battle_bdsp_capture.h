#ifndef POKEPLATINUM_BATTLE_BDSP_CAPTURE_H
#define POKEPLATINUM_BATTLE_BDSP_CAPTURE_H

#include "battle/battle_system.h"
#include "port/sim_battle3d.h"

void BattleBdspCapture_Reset(void);
void BattleBdspCapture_Start(BattleSystem *battleSys, int targetBattler, int ballItemId, int shakes, BOOL caught);
void BattleBdspCapture_End(void);
BOOL BattleBdspCapture_IsActive(void);
void BattleBdspCapture_Update(BattleSystem *battleSys, SIM_Battle3DFrame *frame);

#endif // POKEPLATINUM_BATTLE_BDSP_CAPTURE_H
