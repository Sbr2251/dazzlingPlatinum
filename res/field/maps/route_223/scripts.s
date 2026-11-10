#include "macros/scrcmd.inc"
#include "constants/totem_battle.h"


    ScriptEntry TotemKingdra_Encounter
    ScriptEntryEnd

TotemKingdra_Encounter:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    WaitSE SE_CONFIRM_sseq_3
    PlayBattleMusic BATTLE_WILD_POKEMON_sseq
    PlayCry SPECIES_KINGDRA
    WaitCry
    SetFlag FLAG_MAP_LOCAL_REMOVE_OBJECT
    StartTotemBattle TOTEM_ENCOUNTER_KINGDRA
    ClearFlag FLAG_MAP_LOCAL_REMOVE_OBJECT
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
