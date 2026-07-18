#include "macros/scrcmd.inc"


    ScriptEntry TotemSpiritomb_Encounter
    ScriptEntryEnd

TotemSpiritomb_Encounter:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    PlayCry SPECIES_SPIRITOMB
    WaitCry
    SetFlag FLAG_MAP_LOCAL
    StartLegendaryBattle SPECIES_SPIRITOMB, 30
    ClearFlag FLAG_MAP_LOCAL
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, TotemSpiritomb_Encounter_LostBattle
    SetFlag FLAG_TOTEM_SPIRITOMB_DEFEATED
    SetFlag FLAG_HIDE_TOTEM_SPIRITOMB
    RemoveObject VAR_LAST_TALKED
    ReleaseAll
    End

TotemSpiritomb_Encounter_LostBattle:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
