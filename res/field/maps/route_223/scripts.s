#include "macros/scrcmd.inc"
#include "constants/totem_battle.h"
#include "res/text/bank/route_223.h"


    ScriptEntry TotemKingdra_Encounter
    ScriptEntry Route223_KingdraRift
    ScriptEntry Route223_SummitPillar
    ScriptEntry Route223_SummitTerrace
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

Route223_KingdraRift:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message Route223_Text_KingdraRift
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

Route223_SummitPillar:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message Route223_Text_SummitPillar
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

Route223_SummitTerrace:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message Route223_Text_SummitTerrace
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
