#include "macros/scrcmd.inc"
#include "constants/totem_battle.h"


    ScriptEntry _0006
    ScriptEntry TotemHitmonlee_Encounter
    ScriptEntryEnd

_0006:
    SetFlag FLAG_FIRST_ARRIVAL_RAVAGED_PATH
    End

RavagedPath_Unused:
    End

    .balign 4, 0

TotemHitmonlee_Encounter:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    PlayCry SPECIES_HITMONLEE
    WaitCry
    SetFlag FLAG_MAP_LOCAL
    StartTotemBattle TOTEM_ENCOUNTER_HITMONLEE
    ClearFlag FLAG_MAP_LOCAL
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, TotemHitmonlee_Encounter_LostBattle
    SetFlag FLAG_TOTEM_HITMONLEE_DEFEATED
    SetFlag FLAG_HIDE_TOTEM_HITMONLEE
    RemoveObject VAR_LAST_TALKED
    ReleaseAll
    End

TotemHitmonlee_Encounter_LostBattle:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
