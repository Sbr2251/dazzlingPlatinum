#ifndef POKEPLATINUM_STRUCT_OV16_022674C4_H
#define POKEPLATINUM_STRUCT_OV16_022674C4_H

#include "struct_decls/battle_system.h"

#include "bg_window.h"
#include "sprite.h"
#include "sys_task_manager.h"

typedef struct {
    u8 state;
    ManagedSprite *mainSprite;
    ManagedSprite *arrowSprite;
    BattleSystem *battleSys;
    SysTask *unk_10;
    Window unk_14;
    u8 battler;
    u8 type;
    u8 selectedPartySlot;
    u8 unk_27;
    s32 curHP;
    s32 maxHP;
    s32 damage;
    s32 hpTemp;
    s32 curExp;
    s32 maxExp;
    s32 expReward;
    s32 expTemp;
    u8 unk_48;
    u8 unk_49;
    u8 status;
    u8 unk_4B;
    u8 unk_4C;
    u8 unk_4D;
    u8 unk_4E;
    u8 scrollDirection : 1;
    u8 doneScrolling : 1;
    u8 unk_4F_2 : 1;
    u8 numberMode : 1;
    u8 : 4;
    SysTask *unk_50;
    u16 unk_54;
    SysTask *scrollTask; // bw2vis:hud-gauges: the running slide-in, so a hide can stop it
    SysTask *lossTask; // bw2vis:hud-gauges: the lost-HP segment's blink and the red flash
    u8 ghostEndPx; // the HP bar's pixels before the hit, the lost-HP segment's end; 0 for none
    u8 ghostBlink; // the segment's blink updates left once the drain ends
    u8 ghostHidden; // the segment is in a blink's off phase
} Healthbar;

#endif // POKEPLATINUM_STRUCT_OV16_022674C4_H
