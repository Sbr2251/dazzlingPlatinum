#ifndef POKEPLATINUM_OV12_022380BC_H
#define POKEPLATINUM_OV12_022380BC_H

#include "battle_anim/struct_ov12_022380DC.h"

#include "res/pokemon/pl_otherpoke.naix.h"

// The Substitute doll (back, front, palette) sits just before the shadows at the end of pl_otherpoke;
// new form sprites are inserted ahead of it, so its members are not the vanilla 248-250.
#define SUBSTITUTE_BACK_NCGR  (pokemon_shadows_NCGR - 3)
#define SUBSTITUTE_FRONT_NCGR (pokemon_shadows_NCGR - 2)
#define SUBSTITUTE_NCLR       (pokemon_shadows_NCGR - 1)

void ov12_022380BC(UnkStruct_ov12_022380DC *param0, enum HeapID heapID);
void ov12_022380CC(UnkStruct_ov12_022380DC *param0, enum HeapID heapID);
void ov12_022382BC(UnkStruct_ov12_022380DC *param0, enum HeapID heapID);
void ov12_02238390(UnkStruct_ov12_022380DC *param0, enum HeapID heapID);
s16 ov12_022384CC(int param0, int param1);

#endif // POKEPLATINUM_OV12_022380BC_H
