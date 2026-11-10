#include "macros/scrcmd.inc"
#include "res/field/maps/locals/iron_island_b3f.h"
#include "constants/totem_battle.h"


    ScriptEntry IronIslandB3F_OnTransition
    ScriptEntry IronIslandB3F_CoordEvent_PlatformLift
    ScriptEntry IronIslandB3F_Dummy3
    ScriptEntry IronIslandB3F_OnLoad
    ScriptEntry TotemAggron_Encounter
    ScriptEntryEnd

IronIslandB3F_OnLoad:
    CheckPartyHasFatefulEncounterRegigigas VAR_MAP_LOCAL_0x04
    GoToIfEq VAR_MAP_LOCAL_0x04, FALSE, IronIslandB3F_RemoveWarpIronRuinsWithRegisteel
    GoToIfEq VAR_MAP_LOCAL_0x04, TRUE, IronIslandB3F_RemoveWarpIronRuinsWithoutRegisteel
    End

IronIslandB3F_OnTransition:
    Call TotemAggron_UpdateVisibility
    InitPersistedMapFeaturesForPlatformLift
    CallIfNe VAR_IRON_RUINS_STATE, RUINS_STATE_CAUGHT_REGI, IronIslandB3F_ResetIronRuinsState
    CheckPartyHasFatefulEncounterRegigigas VAR_MAP_LOCAL_0x04
    GoToIfEq VAR_MAP_LOCAL_0x04, FALSE, IronIslandB3F_RemoveWarpIronRuinsWithRegisteel
    GoToIfEq VAR_MAP_LOCAL_0x04, TRUE, IronIslandB3F_RemoveWarpIronRuinsWithoutRegisteel
    End

IronIslandB3F_RemoveWarpIronRuinsWithRegisteel:
    SetWarpEventPos WARP_IRON_RUINS, 17, 1
    End

IronIslandB3F_RemoveWarpIronRuinsWithoutRegisteel:
    SetWarpEventPos WARP_IRON_ISLAND_IRON_RUINS, 17, 1
    End

IronIslandB3F_CoordEvent_PlatformLift:
    TriggerPlatformLift
    End

IronIslandB3F_ResetIronRuinsState:
    SetVar VAR_IRON_RUINS_STATE, 0
    Return

IronIslandB3F_Dummy3:
    End

    .balign 4, 0

TotemAggron_Encounter:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    WaitSE SE_CONFIRM_sseq_3
    PlayBattleMusic BATTLE_WILD_POKEMON_sseq
    PlayCry SPECIES_AGGRON
    WaitCry
    SetFlag FLAG_MAP_LOCAL_REMOVE_OBJECT
    StartTotemBattle TOTEM_ENCOUNTER_AGGRON
    ClearFlag FLAG_MAP_LOCAL_REMOVE_OBJECT
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, TotemAggron_Encounter_LostBattle
    SetFlag FLAG_TOTEM_AGGRON_DEFEATED
    SetFlag FLAG_HIDE_TOTEM_AGGRON
    RemoveObject VAR_LAST_TALKED
    ReleaseAll
    End

TotemAggron_Encounter_LostBattle:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0

TotemAggron_UpdateVisibility:
    GoToIfUnset FLAG_RECEIVED_RIOLU_EGG_FROM_RILEY, TotemAggron_Hide
    GoToIfSet FLAG_TOTEM_AGGRON_DEFEATED, TotemAggron_Hide
    ClearFlag FLAG_HIDE_TOTEM_AGGRON
    Return

TotemAggron_Hide:
    SetFlag FLAG_HIDE_TOTEM_AGGRON
    Return

    .balign 4, 0
