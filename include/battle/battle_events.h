#ifndef POKEPLATINUM_BATTLE_BATTLE_EVENTS_H
#define POKEPLATINUM_BATTLE_BATTLE_EVENTS_H
// Forward declarations only: this header is included from C++ GUI code.
typedef struct BattleContext BattleContext;
typedef struct BattleSystem BattleSystem;
#ifdef __cplusplus
extern "C" {
#endif
void BattleEvents_Poll(BattleSystem *battleSys);
void BattleEvents_OnMoveUsed(BattleSystem *battleSys, BattleContext *ctx);
void BattleEvents_OnSelectedMove(BattleSystem *battleSys, int battler, int command);
void BattleEvents_OnSelectedCommand(BattleSystem *battleSys, int battler, int command);
void BattleEvents_OnBagItem(BattleSystem *battleSys, int battler, int itemId);
void BattleEvents_OnPartyResult(BattleSystem *battleSys, int battler, int command);
int BattleEvents_FastEnabled(void);
void BattleEvents_SetFastEnabled(int on);
int BattleEvents_HistoryCount(void);
const char *BattleEvents_HistoryLine(int index);
void BattleEvents_ClearHistory(void);
int BattleEvents_SaveHistory(const char *path);
int BattleEvents_SaveReplay(const char *path);
int BattleEvents_TakePending(char *out, unsigned long cap);
void BattleEvents_Reset(void);
void BattleEvents_SetSeedOverride(unsigned int seed);
unsigned int BattleEvents_GetSeedOverride(void);
enum BattleDecisionAction { BATTLE_DECISION_MOVE = 0, BATTLE_DECISION_SWITCH = 1, BATTLE_DECISION_ITEM = 2, BATTLE_DECISION_RUN = 3 };
typedef struct BattleDecision {
    int battler; int action; int moveId; int moveSlot; int target; int partySlot; int itemId; int itemTarget; int mega; int done;
} BattleDecision;
void BattleDecisions_Push(const BattleDecision *d);
int BattleDecisions_Peek(int battler, BattleDecision *out);
void BattleDecisions_Complete(int battler);
void BattleDecisions_MarkDone(int battler, int action); // mark first pending decision of this action done
int BattleDecisions_Count(int battler);
#ifdef __cplusplus
}
#endif
#endif
