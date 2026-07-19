#include "macros/scrcmd.inc"
#include "constants/totem_battle.h"


    ScriptEntry _0032
    ScriptEntry _0075
    ScriptEntry _0081
    ScriptEntry _0012
    ScriptEntry TotemAggron_Encounter
    ScriptEntryEnd

_0012:
    CheckPartyHasFatefulEncounterRegigigas VAR_MAP_LOCAL_4
    GoToIfEq VAR_MAP_LOCAL_4, 0, _0061
    GoToIfEq VAR_MAP_LOCAL_4, 1, _006B
    End

_0032:
    Call TotemAggron_UpdateVisibility
    InitPersistedMapFeaturesForPlatformLift
    CallIfNe VAR_UNK_0x4069, 0x122, _0079
    CheckPartyHasFatefulEncounterRegigigas VAR_MAP_LOCAL_4
    GoToIfEq VAR_MAP_LOCAL_4, 0, _0061
    GoToIfEq VAR_MAP_LOCAL_4, 1, _006B
    End

_0061:
    SetWarpEventPos 3, 17, 1
    End

_006B:
    SetWarpEventPos 2, 17, 1
    End

_0075:
    TriggerPlatformLift
    End

_0079:
    SetVar VAR_UNK_0x4069, 0
    Return

_0081:
    End

    .balign 4, 0

TotemAggron_Encounter:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    PlayCry SPECIES_AGGRON
    WaitCry
    SetFlag FLAG_MAP_LOCAL
    StartTotemBattle TOTEM_ENCOUNTER_AGGRON
    ClearFlag FLAG_MAP_LOCAL
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
    GoToIfUnset FLAG_TRAVELED_WITH_RILEY, TotemAggron_Hide
    GoToIfSet FLAG_TOTEM_AGGRON_DEFEATED, TotemAggron_Hide
    ClearFlag FLAG_HIDE_TOTEM_AGGRON
    Return

TotemAggron_Hide:
    SetFlag FLAG_HIDE_TOTEM_AGGRON
    Return

    .balign 4, 0
