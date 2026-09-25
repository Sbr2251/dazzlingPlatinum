#ifndef POKEPLATINUM_BATTLE_BATTLE_DEBUG_H
#define POKEPLATINUM_BATTLE_BATTLE_DEBUG_H

#include "struct_decls/battle_system.h"

#include "battle/struct_ov16_0225BFFC_decl.h"

// In-battle debug tools (DEBUG_BATTLE_TOOLS only). At the Fight/Bag/Pokemon/Run menu, hold L+R and press:
//   LEFT/RIGHT  move ID -1/+1        UP/DOWN  move ID +10/-10
//   A           play the move's animation, player -> enemy (the move is not used)
//   Y           play it enemy -> player
//   SELECT      toggle the 3D battle stage
// Called every frame the command menu waits for input. Returns TRUE when the tools used this
// frame (L+R held or a test animation playing); the menu must then ignore input.
void BattleDebug_Init(void);
void BattleDebug_Free(void);
BOOL BattleDebug_UpdateCommandMenu(BattleSystem *battleSys, BattlerData *commandBattler);

#endif // POKEPLATINUM_BATTLE_BATTLE_DEBUG_H
