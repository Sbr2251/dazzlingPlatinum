#ifndef POKEPLATINUM_STRUCT_OV16_0225DA44_H
#define POKEPLATINUM_STRUCT_OV16_0225DA44_H

#include "struct_decls/battle_system.h"

#include "pokemon_sprite.h"

typedef struct {
    BattleSystem *unk_00;
    PokemonSprite *unk_04;
    u8 unk_08;
    u8 unk_09;
    u8 unk_0A;
    u8 unk_0B;
    u16 flashColor; // bw2vis:idle: the hit flash's colour (BattleStage_HitFlashColor)
    u8 hiddenAtStart; // bw2vis:idle: hidden when the hit came (Fly, Dig): no flash, as in B/W
} UnkStruct_ov16_0225DA44;

#endif // POKEPLATINUM_STRUCT_OV16_0225DA44_H
