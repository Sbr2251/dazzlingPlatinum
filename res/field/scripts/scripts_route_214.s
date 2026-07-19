#include "macros/scrcmd.inc"
#include "constants/totem_battle.h"


    ScriptEntry _00A2
    ScriptEntry _00B9
    ScriptEntry _0075
    ScriptEntry _0012
    ScriptEntry TotemSkarmory_Encounter
    ScriptEntryEnd

_0012:
    GetUnownFormsSeenCount VAR_MAP_LOCAL_0
    GoToIfGe VAR_MAP_LOCAL_0, 26, _003F
    GoToIfGe VAR_MAP_LOCAL_0, 10, _0051
    GoToIfLt VAR_MAP_LOCAL_0, 10, _0063
    End

_003F:
    SetWarpEventPos 2, 0x2C6, 0x29E
    SetWarpEventPos 3, 0x2C6, 0x29E
    End

_0051:
    SetWarpEventPos 2, 0x2C6, 0x29E
    SetWarpEventPos 4, 0x2C6, 0x29E
    End

_0063:
    SetWarpEventPos 3, 0x2C6, 0x29E
    SetWarpEventPos 4, 0x2C6, 0x29E
    End

_0075:
    GetUnownFormsSeenCount VAR_MAP_LOCAL_0
    GoToIfGe VAR_MAP_LOCAL_0, 26, _003F
    GoToIfGe VAR_MAP_LOCAL_0, 10, _0051
    GoToIfLt VAR_MAP_LOCAL_0, 10, _0063
    End

_00A2:
    ShowArrowSign 0
    End

_00B9:
    ShowArrowSign 1
    End

TotemSkarmory_Encounter:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    PlayCry SPECIES_SKARMORY
    WaitCry
    SetFlag FLAG_MAP_LOCAL
    StartTotemBattle TOTEM_ENCOUNTER_SKARMORY
    ClearFlag FLAG_MAP_LOCAL
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, TotemSkarmory_Encounter_LostBattle
    SetFlag FLAG_TOTEM_SKARMORY_DEFEATED
    SetFlag FLAG_HIDE_TOTEM_SKARMORY
    RemoveObject VAR_LAST_TALKED
    ReleaseAll
    End

TotemSkarmory_Encounter_LostBattle:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
