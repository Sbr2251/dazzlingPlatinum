#ifndef POKEPLATINUM_STRUCT_DEFS_POKEMON_MEGA_DATA_H
#define POKEPLATINUM_STRUCT_DEFS_POKEMON_MEGA_DATA_H

#include "global.h"

typedef struct {
    u16 baseSpecies;      // Base Pokémon species ID
    u16 megaForm;         // Mega form ID
    u16 requiredItem;     // Mega stone item ID
    u8  baseStats[6];     // HP, Atk, Def, SpAtk, SpDef, Speed
    u8  ability;          // Mega form ability
    u8  type1;            // Primary type
    u8  type2;            // Secondary type
} MegaEvolutionData;

#endif // POKEPLATINUM_STRUCT_DEFS_POKEMON_MEGA_DATA_H
