#ifndef POKEPLATINUM_BATTLE_TOTEM_AURA_H
#define POKEPLATINUM_BATTLE_TOTEM_AURA_H

#include "struct_decls/battle_system.h"

// Wreathes the Totem (enemy slot 1) in flames that last until it faints or the battle ends.
// The flare-up cinematic (~3.5 s, skippable with A/B after the first beat) is driven from
// here together with res/battle/scripts/common_anims/totem_aura.s; the persistent aura is a
// layered, breathing particle wreath whose intensity follows the Totem's HP and flares
// briefly when the Totem is hit or uses a move. Summoned allies (enemy slot 2) get a
// smaller, shorter version of the same treatment.
void TotemAura_Start(BattleSystem *battleSys);
void TotemAura_StartForBattler(BattleSystem *battleSys, int battler);
void TotemAura_Stop(void);
void TotemAura_StopForBattler(int battler);
BOOL TotemAura_IsActive(void);
BOOL TotemAura_IsActiveForBattler(int battler);
// Brief intensity flare for a battler's aura (hit taken / move used). Safe to call when no
// aura is running for that battler.
void TotemAura_NotifyHit(int battler);
void TotemAura_NotifyMove(int battler);

#endif // POKEPLATINUM_BATTLE_TOTEM_AURA_H
