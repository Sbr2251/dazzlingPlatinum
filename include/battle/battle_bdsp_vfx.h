#ifndef POKEPLATINUM_BATTLE_BDSP_VFX_H
#define POKEPLATINUM_BATTLE_BDSP_VFX_H

#include "battle/battle_system.h"
#include "port/sim_battle3d.h"

void BattleBdspVfx_Reset(void);
void BattleBdspVfx_NotifyAttack(int attacker, int defender, u16 move);
void BattleBdspVfx_NotifyHit(int defender);
void BattleBdspVfx_NotifyShiny(int battler);
void BattleBdspVfx_Update(BattleSystem *battleSys, SIM_Battle3DFrame *frame);

#endif // POKEPLATINUM_BATTLE_BDSP_VFX_H
