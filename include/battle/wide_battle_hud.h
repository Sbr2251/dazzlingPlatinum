#ifndef POKEPLATINUM_BATTLE_WIDE_BATTLE_HUD_H
#define POKEPLATINUM_BATTLE_WIDE_BATTLE_HUD_H

#include <nitro/types.h>

#include "struct_decls/battle_system.h"
#include "battle/battle_subscreen.h"

#ifdef __cplusplus
extern "C" {
#endif

enum SIM_WideBattleMenu {
    SIM_WIDEBATTLE_MENU_IDLE = 0,
    SIM_WIDEBATTLE_MENU_ACTION = 1,
    SIM_WIDEBATTLE_MENU_MOVE = 2,
    SIM_WIDEBATTLE_MENU_TARGET = 3,
    SIM_WIDEBATTLE_MENU_YESNO = 4,
};

enum SIM_WideBattleCategory {
    SIM_WIDEBATTLE_CAT_PHYSICAL = 0,
    SIM_WIDEBATTLE_CAT_SPECIAL = 1,
    SIM_WIDEBATTLE_CAT_STATUS = 2,
};

typedef struct SIM_WideBattleBattler {
    int present;
    int battlerIndex;
    int isEnemy;
    int isActive;
    int isAllySlot2;
    char name[32];
    int level;
    int gender;
    int curHP;
    int maxHP;
    float expFrac;
    char status[8];
    int caught;
    int megaEvolved;
    int type1;
    int type2;
    signed char stages[7];
} SIM_WideBattleBattler;

typedef struct SIM_WideBattleMove {
    int moveId;
    char name[32];
    int type;
    int category;
    int power;
    int accuracy;
    int curPP;
    int maxPP;
    int effectiveness;
    int rangeMask;
    int hitsAlly;
} SIM_WideBattleMove;

typedef struct SIM_WideBattleTargetSlot {
    int valid;
    int battlerIndex;
    int isEnemy;
    int isHitBySpread;
    int effectiveness;
    char name[32];
    int curHP;
    int maxHP;
} SIM_WideBattleTargetSlot;

typedef struct SIM_WideBattleState {
    int active;
    int isDoubles;
    int menu;
    int cursorX;
    int cursorY;
    int activeBattler;
    int isPartnerTurn;
    int isSafari;
    int isPalPark;
    int megaAvailable;
    int megaArmed;
    char prompt[128];
    char actionLabels[4][24];
    SIM_WideBattleBattler battlers[4];
    SIM_WideBattleMove moves[4];
    SIM_WideBattleTargetSlot targets[4];
    int selectedTargetMask;
} SIM_WideBattleState;

typedef struct SIM_WideBattleEvent {
    int buttonIndex;
} SIM_WideBattleEvent;

/* Strong definitions are supplied by libntr when the simulator lane lands. */
extern int SIM_WideBattle_IsEnabled(void) __attribute__((weak));
extern int SIM_WideBattle_IsActive(void) __attribute__((weak));
extern void SIM_WideBattle_SetState(const SIM_WideBattleState *state) __attribute__((weak));
extern void SIM_WideBattle_Clear(void) __attribute__((weak));
extern int SIM_WideBattle_PollEvent(SIM_WideBattleEvent *out) __attribute__((weak));

BOOL WideBattleHud_IsActive(void);
void WideBattleHud_SyncFrame(BattleSystem *battleSys, BattleSubscreen *btlSubscreen);
int WideBattleHud_PollTouch(void);
void WideBattleHud_Clear(void);

#ifdef __cplusplus
}
#endif

#endif // POKEPLATINUM_BATTLE_WIDE_BATTLE_HUD_H
