#include "battle/battle_bdsp_vfx.h"

void BattleBdspVfx_Reset(void) {}
void BattleBdspVfx_NotifyAttack(int attacker, int defender, u16 move) { (void)attacker; (void)defender; (void)move; }
void BattleBdspVfx_NotifyHit(int defender) { (void)defender; }
void BattleBdspVfx_NotifyShiny(int battler) { (void)battler; }
void BattleBdspVfx_Update(BattleSystem *battleSys, SIM_Battle3DFrame *frame) { (void)battleSys; (void)frame; }
