#include "totem_battle.h"

#include "constants/battle.h"
#include "constants/pokemon.h"
#include "generated/species.h"

#include "battle/battle_context.h"
#include "battle/ov16_0223DF00.h"

// The lone Totem's x offset from its doubles home: 192 (the wild single spot) against 216
#define TOTEM_ALONE_OFFSET_X (192 - 216)

static int sTotemHomeOffsetX;
static BOOL sHealthbarsHidden;

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
            { SPECIES_SPIRITOMB, 40, 0 }, // Arc 2 D14: 40 (end of Arc 2, after Fantina), allies 2 below
            { SPECIES_MISDREAVUS, 38, 0 },
            { SPECIES_HAUNTER, 38, 0 },
        },
    },
    [TOTEM_ENCOUNTER_SKARMORY] = {
        .party = {
            { SPECIES_SKARMORY, 32, 0 }, // Arc 2 D14: 32 (Maylene's ace is 31), allies 2 below
            { SPECIES_GLIGAR, 30, 0 },
            { SPECIES_MAGNETON, 30, 0 },
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

void TotemBattle_ResetLayout(BattleSystem *battleSys)
{
    sTotemHomeOffsetX = (battleSys != NULL && TotemBattle_IsActive(battleSys)) ? TOTEM_ALONE_OFFSET_X : 0;
    sHealthbarsHidden = FALSE;
}

int TotemBattle_HomeOffsetX(int battlerType)
{
    return battlerType == BATTLER_TYPE_ENEMY_SIDE_SLOT_1 ? sTotemHomeOffsetX : 0;
}

void TotemBattle_SetHomeOffsetX(int offset)
{
    sTotemHomeOffsetX = offset;
}

// Move animations aim at the lone Totem as if it were a wild single, so they land centre stage
void TotemBattle_AdjustAnimTypes(u8 *types)
{
    if (sTotemHomeOffsetX != 0 && types[BATTLER_ENEMY_1] == BATTLER_TYPE_ENEMY_SIDE_SLOT_1) {
        types[BATTLER_ENEMY_1] = BATTLER_TYPE_SOLO_ENEMY;
    }
}

void TotemBattle_HideHealthbars(BattleSystem *battleSys)
{
    sHealthbarsHidden = TRUE;
    ov16_0223F3EC(battleSys);
}

void TotemBattle_ShowHealthbars(BattleSystem *battleSys)
{
    if (!sHealthbarsHidden) {
        return;
    }

    sHealthbarsHidden = FALSE;
    ov16_0223F3BC(battleSys);
}

BOOL TotemBattle_AreHealthbarsHidden(void)
{
    return sHealthbarsHidden;
}
