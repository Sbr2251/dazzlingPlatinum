#include "totem_battle.h"

#include "constants/battle.h"
#include "constants/pokemon.h"
#include "generated/species.h"

#include "battle/battle_context.h"
#include "battle/ov16_0223DF00.h"

static const TotemEncounterConfig sTotemEncounterTable[TOTEM_ENCOUNTER_COUNT] = {
    [TOTEM_ENCOUNTER_HITMONLEE] = {
        .party = {
            { SPECIES_HITMONLEE, 20, 0 },
            { SPECIES_MEDITITE, 18, 0 },
            { SPECIES_MACHOP, 18, 0 },
        },
    },
    [TOTEM_ENCOUNTER_VESPIQUEN] = {
        .party = {
            { SPECIES_VESPIQUEN, 25, 0 },
            { SPECIES_COMBEE, 23, 0 },
            { SPECIES_BEAUTIFLY, 23, 0 },
        },
    },
    [TOTEM_ENCOUNTER_SPIRITOMB] = {
        .party = {
            { SPECIES_SPIRITOMB, 30, 0 },
            { SPECIES_MISDREAVUS, 28, 0 },
            { SPECIES_HAUNTER, 28, 0 },
        },
    },
    [TOTEM_ENCOUNTER_SKARMORY] = {
        .party = {
            { SPECIES_SKARMORY, 35, 0 },
            { SPECIES_GLIGAR, 33, 0 },
            { SPECIES_MAGNETON, 33, 0 },
        },
    },
    [TOTEM_ENCOUNTER_LAPRAS] = {
        .party = {
            { SPECIES_LAPRAS, 36, 0 },
            { SPECIES_MANTYKE, 34, 0 },
            { SPECIES_SHELLOS, 34, 0 },
        },
    },
    [TOTEM_ENCOUNTER_AGGRON] = {
        .party = {
            { SPECIES_AGGRON, 42, 0 },
            { SPECIES_LAIRON, 40, 0 },
            { SPECIES_GRAVELER, 40, 0 },
        },
    },
    [TOTEM_ENCOUNTER_MAMOSWINE] = {
        .party = {
            { SPECIES_MAMOSWINE, 44, 0 },
            { SPECIES_SNOVER, 42, 0 },
            { SPECIES_SNEASEL, 42, 0 },
        },
    },
    [TOTEM_ENCOUNTER_KINGDRA] = {
        .party = {
            { SPECIES_KINGDRA, 50, 0 },
            { SPECIES_SEADRA, 48, 0 },
            { SPECIES_LANTURN, 48, 0 },
        },
    },
};

const TotemEncounterConfig *TotemBattle_GetEncounterConfig(u8 encounterID)
{
    if (encounterID >= TOTEM_ENCOUNTER_COUNT) {
        return NULL;
    }

    return &sTotemEncounterTable[encounterID];
}

BOOL TotemBattle_IsActive(BattleSystem *battleSys)
{
    return (BattleSystem_BattleStatus(battleSys) & BATTLE_STATUS_TOTEM) != 0;
}

BOOL TotemBattle_IsPermanentlyInactiveBattler(BattleSystem *battleSys, int battler)
{
    return TotemBattle_IsActive(battleSys) && battler == BATTLER_PLAYER_2;
}

BOOL TotemBattle_IsInactiveBattler(BattleSystem *battleSys, BattleContext *battleCtx, int battler)
{
    if (TotemBattle_IsPermanentlyInactiveBattler(battleSys, battler)) {
        return TRUE;
    }

    return TotemBattle_IsActive(battleSys)
        && battler == BATTLER_ENEMY_2
        && battleCtx->selectedPartySlot[battler] == MAX_PARTY_SIZE;
}
