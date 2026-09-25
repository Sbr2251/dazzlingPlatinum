#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_H

#include "struct_decls/battle_system.h"

// The 3D arena drawn behind the battle sprites. With BATTLE_STAGE_3D off, every function does nothing.
void BattleStage_Init(BattleSystem *battleSys);
void BattleStage_Free(void);

// Called from the battle draw task, before particles and sprites
void BattleStage_Draw(void);

// Live on/off switch (the debug A/B toggle); the stage starts enabled
void BattleStage_SetEnabled(BOOL enabled);
BOOL BattleStage_IsEnabled(void);

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_H
