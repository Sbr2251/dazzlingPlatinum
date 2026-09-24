#ifndef POKEPLATINUM_BATTLE_TOTEM_AURA_H
#define POKEPLATINUM_BATTLE_TOTEM_AURA_H

#include "struct_decls/battle_system.h"

// Wreathes the Totem (enemy slot 1) in flames that last until it faints or the battle ends
void TotemAura_Start(BattleSystem *battleSys);
void TotemAura_Stop(void);

#endif // POKEPLATINUM_BATTLE_TOTEM_AURA_H
