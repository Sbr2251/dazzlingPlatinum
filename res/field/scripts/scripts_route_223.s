#include "macros/scrcmd.inc"
#include "constants/totem_battle.h"


    ScriptEntry TotemKingdra_Encounter
    ScriptEntryEnd

TotemKingdra_Encounter:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    PlayCry SPECIES_KINGDRA
    WaitCry
    SetFlag FLAG_MAP_LOCAL
    StartTotemBattle TOTEM_ENCOUNTER_KINGDRA
    ClearFlag FLAG_MAP_LOCAL
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, TotemKingdra_Encounter_LostBattle
    SetFlag FLAG_TOTEM_KINGDRA_DEFEATED
    SetFlag FLAG_HIDE_TOTEM_KINGDRA
    RemoveObject VAR_LAST_TALKED
    ReleaseAll
    End

TotemKingdra_Encounter_LostBattle:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
