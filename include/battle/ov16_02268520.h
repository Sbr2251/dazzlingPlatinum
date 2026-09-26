#ifndef POKEPLATINUM_OV16_02268520_H
#define POKEPLATINUM_OV16_02268520_H

#include "struct_decls/battle_system.h"

#include "battle/struct_ov16_02268520.h"

void ov16_02268520(UnkStruct_ov16_02268520 *param0);
void ov16_0226862C(UnkStruct_ov16_02268520 *param0);
void ov16_02268660(UnkStruct_ov16_02268520 *param0);
void ov16_02268674(UnkStruct_ov16_02268520 *param0);
void ov16_022686BC(UnkStruct_ov16_02268520 *param0, int param1);
void ov16_022686CC(UnkStruct_ov16_02268520 *param0, BattleSystem *battleSys, u16 param2, int param3);
void ov16_02268700(UnkStruct_ov16_02268520 *param0);
// Screen x offset of the platform OBJ from its resting position; 0 once the OBJ is gone
int BattlePlatform_GetOffsetX(UnkStruct_ov16_02268520 *platform);
// OBJ palette row used by the platform, or -1 once the OBJ is gone
int BattlePlatform_GetPaletteRow(UnkStruct_ov16_02268520 *platform);

#endif // POKEPLATINUM_OV16_02268520_H
