#ifndef POKEPLATINUM_TOTEM_BATTLE_H
#define POKEPLATINUM_TOTEM_BATTLE_H

#include "constants/totem_battle.h"

#include "struct_decls/battle_system.h"

typedef struct BattleContext BattleContext;

typedef struct TotemPokemonConfig {
    u16 species;
    u8 level;
    u8 padding;
} TotemPokemonConfig;

typedef struct TotemEncounterConfig {
    TotemPokemonConfig party[TOTEM_PARTY_SIZE];
} TotemEncounterConfig;

const TotemEncounterConfig *TotemBattle_GetEncounterConfig(u8 encounterID);
BOOL TotemBattle_IsActive(BattleSystem *battleSys);
BOOL TotemBattle_IsPermanentlyInactiveBattler(BattleSystem *battleSys, int battler);
BOOL TotemBattle_IsInactiveBattler(BattleSystem *battleSys, BattleContext *battleCtx, int battler);

#endif // POKEPLATINUM_TOTEM_BATTLE_H
