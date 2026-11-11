#ifndef POKEPLATINUM_BATTLE_BATTLE_EVENTS_H
#define POKEPLATINUM_BATTLE_BATTLE_EVENTS_H
#include "struct_decls/battle_system.h"
#include "battle/battle_context.h"
void BattleEvents_Poll(BattleSystem *battleSys);
void BattleEvents_OnMoveUsed(BattleSystem *battleSys, BattleContext *ctx);
void BattleEvents_OnSelectedMove(BattleSystem *battleSys, int battler, int command);
void BattleEvents_OnSelectedCommand(BattleSystem *battleSys, int battler, int command);
void BattleEvents_OnBagItem(BattleSystem *battleSys, int battler, int itemId);
void BattleEvents_OnPartyResult(BattleSystem *battleSys, int battler, int command);
int BattleEvents_FastEnabled(void);
int BattleEvents_TakePending(char *out, unsigned long cap);
void BattleEvents_Reset(void);
#endif
