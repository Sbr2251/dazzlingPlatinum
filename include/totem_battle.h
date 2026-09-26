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

// While the Totem is alone it stands centre stage, where a wild single stands, and steps right
// to its doubles spot when it summons an ally. The offset is 0 outside Totem battles.
void TotemBattle_ResetLayout(BattleSystem *battleSys);
int TotemBattle_HomeOffsetX(int battlerType);
void TotemBattle_SetHomeOffsetX(int offset);
void TotemBattle_AdjustAnimTypes(u8 *types);

#endif // POKEPLATINUM_TOTEM_BATTLE_H
