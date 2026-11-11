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
// Seed override for deterministic battles (engine-sim start_battle spec seed):
// when set, BattleMain seeds the battle LCRNG (seedRandNext/seedDTO) from it
// instead of the field-supplied dto->seed. 0 = no override (use SIM_BATTLE_SEED env or 0).
void BattleEvents_SetSeedOverride(unsigned int seed);
unsigned int BattleEvents_GetSeedOverride(void);
// --- Decision queue (scripted/replay decisions for player battlers) ---
enum BattleDecisionAction { BATTLE_DECISION_MOVE = 0, BATTLE_DECISION_SWITCH = 1, BATTLE_DECISION_ITEM = 2, BATTLE_DECISION_RUN = 3 };
typedef struct BattleDecision {
    int battler; int action; int moveId; int moveSlot; int target; int partySlot; int itemId; int itemTarget; int mega;
} BattleDecision;
void BattleDecisions_Push(const BattleDecision *d);
int BattleDecisions_Peek(int battler, BattleDecision *out); // 1 if a decision is queued
void BattleDecisions_Complete(int battler); // pop after the action is fully entered
int BattleDecisions_Count(int battler);
#endif
