#include "macros/scrcmd.inc"
#include "res/text/bank/celestic_town.h"
#include "res/field/maps/locals/celestic_town.h"


    ScriptEntry CelesticTown_OnTransition
    ScriptEntry CelesticTown_Elder
    ScriptEntry CelesticTown_CoordEvent_Elder
    ScriptEntry CelesticTown_GruntM
    ScriptEntry CelesticTown_OnFrame_Cynthia
    ScriptEntry CelesticTown_Cynthia
    ScriptEntry CelesticTown_ExpertM
    ScriptEntry CelesticTown_AceTrainerF
    ScriptEntry CelesticTown_NinjaBoy
    ScriptEntry CelesticTown_MapSignpost
    ScriptEntry CelesticTown_EtchingDialga
    ScriptEntry CelesticTown_EtchingPalkia
    ScriptEntry CelesticTown_Arc2CyrusBattle
    ScriptEntry CelesticTown_CineCityEntry
    ScriptEntryEnd

CelesticTown_OnTransition:
    SetVar VAR_CINE_CITY_PENDING, 1
    SetFlag FLAG_UNLOCKED_VS_SEEKER_LVL_2
    SetFlag FLAG_HIDE_CELESTIC_TOWN_GRUNT_M
    SetFlag FLAG_HIDE_CELESTIC_TOWN_ELDER
    SetVar VAR_CELESTIC_TOWN_ELDER_STATE, 1
    GoToIfLt VAR_ARC2_PROGRESS, 42, CelesticTown_HideArc2Cyrus
    GoToIfGe VAR_ARC2_PROGRESS, 44, CelesticTown_HideArc2Cyrus
    End

CelesticTown_GruntM:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message CelesticTown_Text_WillYouMessWithMe
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, CelesticTown_GruntMBattle
    GoToIfEq VAR_RESULT, MENU_NO, CelesticTown_VerySmart
    End

CelesticTown_VerySmart:
    Message CelesticTown_Text_VerySmart
    WaitButton
    CloseMessage
    ReleaseAll
    End

CelesticTown_GruntMBattle:
    Message CelesticTown_Text_YouDareOpposeUs
    CloseMessage
    StartTrainerBattle TRAINER_GALACTIC_GRUNT_CELESTIC_TOWN
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, CelesticTown_BlackOut
    Message CelesticTown_Text_TooMuchToHandle
    CloseMessage
    GetPlayerDir VAR_RESULT
    GoToIfEq VAR_RESULT, DIR_NORTH, CelesticTown_GruntMLeaveElderEnterNorth
    GoToIfEq VAR_RESULT, DIR_WEST, CelesticTown_GruntMLeaveElderEnterWest
    GoToIfEq VAR_RESULT, DIR_EAST, CelesticTown_GruntMLeaveElderEnterEast
    End

CelesticTown_GruntMLeaveElderEnterNorth:
    ApplyMovement LOCALID_GRUNT_M, CelesticTown_Movement_GruntMLeaveNorthWest
    ApplyMovement LOCALID_PLAYER, CelesticTown_Movement_PlayerWatchGruntMLeaveNorth
    WaitMovement
    Call CelesticTown_RemoveGruntMAddElder
    ApplyMovement LOCALID_ELDER, CelesticTown_Movement_ElderEnterNorth
    ApplyMovement LOCALID_PLAYER, CelesticTown_Movement_PlayerWatchElderEnterNorth
    WaitMovement
    GoTo CelesticTown_GiveOldCharm

CelesticTown_GruntMLeaveElderEnterWest:
    ApplyMovement LOCALID_GRUNT_M, CelesticTown_Movement_GruntMLeaveNorthWest
    ApplyMovement LOCALID_PLAYER, CelesticTown_Movement_PlayerWatchGruntMLeaveWest
    WaitMovement
    Call CelesticTown_RemoveGruntMAddElder
    ApplyMovement LOCALID_ELDER, CelesticTown_Movement_ElderEnterWest
    WaitMovement
    GoTo CelesticTown_GiveOldCharm

CelesticTown_GruntMLeaveElderEnterEast:
    ApplyMovement LOCALID_GRUNT_M, CelesticTown_Movement_GruntMLeaveEast
    ApplyMovement LOCALID_PLAYER, CelesticTown_Movement_PlayerWatchGruntMLeaveEast
    WaitMovement
    Call CelesticTown_RemoveGruntMAddElder
    ApplyMovement LOCALID_ELDER, CelesticTown_Movement_ElderEnterEast
    WaitMovement
    GoTo CelesticTown_GiveOldCharm

CelesticTown_RemoveGruntMAddElder:
    RemoveObject LOCALID_GRUNT_M
    RemoveObject LOCALID_ELDER
    SetObjectEventPos LOCALID_ELDER, 466, 531
    SetObjectEventDir LOCALID_ELDER, DIR_NORTH
    SetObjectEventMovementType LOCALID_ELDER, MOVEMENT_TYPE_LOOK_NORTH
    ClearFlag FLAG_HIDE_CELESTIC_TOWN_ELDER
    AddObject LOCALID_ELDER
    LockObject LOCALID_ELDER
    Return

CelesticTown_GiveOldCharm:
    Message CelesticTown_Text_ThatOldCharm
    BufferPlayerName 0
    BufferItemName 1, ITEM_OLD_CHARM
    PlayFanfare SEQ_FANFA4_sseq
    Message CelesticTown_Text_PlayerHandedOverCharm
    WaitFanfare
    RemoveItem ITEM_OLD_CHARM, 1, VAR_RESULT
    SetFlag FLAG_DELIVERED_OLD_CHARM
    Message CelesticTown_Text_LookAroundRuins
    WaitButton
    CloseMessage
    ReleaseAll
    End

CelesticTown_BlackOut:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
CelesticTown_Movement_GruntMLeaveNorthWest:
    WalkFastWest 3
    WalkFastSouth 9
    EndMovement

    .balign 4, 0
CelesticTown_Movement_GruntMLeaveEast:
    WalkFastSouth 2
    WalkFastWest 3
    WalkFastSouth 7
    EndMovement

    .balign 4, 0
CelesticTown_Movement_ElderEnterNorth:
    WalkNormalNorth 8
    WalkNormalWest 2
    EndMovement

    .balign 4, 0
CelesticTown_Movement_ElderEnterWest:
    WalkNormalNorth 8
    WalkNormalWest 2
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
CelesticTown_Movement_ElderEnterEast:
    WalkNormalNorth 8
    WalkNormalWest 4
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
CelesticTown_Movement_PlayerWatchGruntMLeaveNorth:
    WalkOnSpotNormalWest
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
CelesticTown_Movement_PlayerWatchGruntMLeaveWest:
    Delay8 3
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
CelesticTown_Movement_PlayerWatchGruntMLeaveEast:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
CelesticTown_Movement_PlayerWatchElderEnterNorth:
    Delay8 8
    Delay4
    WalkOnSpotNormalEast
    EndMovement

CelesticTown_Movement_Unused:
    Delay8 8
    WalkOnSpotNormalSouth
    EndMovement

CelesticTown_Movement_Unused2:
    Delay8 9
    WalkOnSpotNormalSouth
    EndMovement

CelesticTown_CoordEvent_Elder:
    LockAll
    ApplyMovement LOCALID_PLAYER, CelesticTown_Movement_PlayerFaceWest
    ApplyMovement LOCALID_ELDER, CelesticTown_Movement_ElderWalkOnSpotEast
    WaitMovement
    Call CelesticTown_OddSpaceman
    ReleaseAll
    End

CelesticTown_OddSpaceman:
    SetVar VAR_CELESTIC_TOWN_ELDER_STATE, 1
    Message CelesticTown_Text_OddSpaceman
    WaitButton
    CloseMessage
    Return

    .balign 4, 0
CelesticTown_Movement_ElderWalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
CelesticTown_Movement_PlayerFaceWest:
    FaceWest
    EndMovement

CelesticTown_Elder:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_DELIVERED_OLD_CHARM, CelesticTown_ExamineRuins
    Call CelesticTown_OddSpaceman
    ReleaseAll
    End

CelesticTown_ExamineRuins:
    Message CelesticTown_Text_ExamineRuins
    WaitButton
    CloseMessage
    ReleaseAll
    End

CelesticTown_OnFrame_Cynthia:
    LockAll
    ApplyMovement LOCALID_PLAYER, CelesticTown_Movement_PlayerWalkOnSpotEast
    ApplyMovement LOCALID_CYNTHIA, CelesticTown_Movement_CynthiaNoticePlayer
    WaitMovement
    Message CelesticTown_Text_WasEverythingAllRight
    ApplyMovement LOCALID_CYNTHIA, CelesticTown_Movement_CynthiaWalkOnSpotNorth
    WaitMovement
    Message CelesticTown_Text_ThoughtGalacticWasHarmless
    CloseMessage
    ApplyMovement LOCALID_CYNTHIA, CelesticTown_Movement_CynthiaWalkOnSpotWest
    WaitMovement
    SetVar VAR_CELESTIC_TOWN_STATE, 2
    SetFlag FLAG_HIDE_ROUTE_218_BLOCKADE
    WaitTime 12, VAR_RESULT
    Message CelesticTown_Text_LibraryInCanalave
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
CelesticTown_Movement_PlayerWalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
CelesticTown_Movement_CynthiaNoticePlayer:
    EmoteExclamationMark
    WalkNormalWest 2
    EndMovement

    .balign 4, 0
CelesticTown_Movement_CynthiaWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
CelesticTown_Movement_CynthiaWalkOnSpotWest:
    WalkOnSpotNormalWest
    EndMovement

CelesticTown_Cynthia:
    NPCMessage CelesticTown_Text_LibraryInCanalave
    End

CelesticTown_ExpertM:
    NPCMessage CelesticTown_Text_StudyingLocalHistory
    End

CelesticTown_AceTrainerF:
    NPCMessage CelesticTown_Text_NoPokemonMart
    End

CelesticTown_NinjaBoy:
    NPCMessage CelesticTown_Text_APokemonCreatedSinnoh
    End

CelesticTown_MapSignpost:
    ShowMapSign CelesticTown_Text_MapSign
    End

CelesticTown_EtchingDialga:
    EventMessage CelesticTown_Text_EtchingDialga
    End

CelesticTown_EtchingPalkia:
    EventMessage CelesticTown_Text_EtchingPalkia
    End

    .balign 4, 0

CelesticTown_HideArc2Cyrus:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    End

// Talking to Cyrus, or the coord trigger a few steps west of him (state 42).
CelesticTown_Arc2CyrusBattle:
    LockAll
    ApplyMovement LOCALID_PLAYER, CelesticTown_Arc2Movement_FaceEast
    WaitMovement
    Message CelesticTown_Text_Arc2CyrusFourth
    ApplyMovement LOCALID_ARC2_CYRUS, CelesticTown_Arc2Movement_FaceWest
    WaitMovement
    Message CelesticTown_Text_Arc2CyrusBattleMe
    CloseMessage
    Call CelesticTown_SetArc2CyrusTrainer
    StartTrainerBattle VAR_0x8004
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, CelesticTown_Arc2CyrusLost
    GoTo CelesticTown_Arc2CyrusAfter
    End

// No blackout (like the first rival battle): back to the field, healed, and the scene goes on.
CelesticTown_Arc2CyrusLost:
    ReturnToField
    FadeScreenIn
    WaitFadeScreen
    HealParty
    GoTo CelesticTown_Arc2CyrusAfter
    End

CelesticTown_Arc2CyrusAfter:
    Message CelesticTown_Text_Arc2CyrusGladToLose
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 44
    // The Route 210 Psyduck blockade is cleared from the north side.
    SetFlag FLAG_HIDE_ROUTE_210_SOUTH_PSYDUCK
    ApplyMovement LOCALID_ARC2_CYRUS, CelesticTown_Arc2Movement_CyrusLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_CYRUS
    ReleaseAll
    End

// The suffix is the PLAYER's starter (Cyrus holds the one weak to it).
CelesticTown_SetArc2CyrusTrainer:
    GetPlayerStarterSpecies VAR_RESULT
    SetVar VAR_0x8004, TRAINER_CYRUS_ARC2_2_CHIMCHAR
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, CelesticTown_Arc2Return
    SetVar VAR_0x8004, TRAINER_CYRUS_ARC2_2_PIPLUP
    GoToIfEq VAR_RESULT, SPECIES_PIPLUP, CelesticTown_Arc2Return
    SetVar VAR_0x8004, TRAINER_CYRUS_ARC2_2_TURTWIG
    Return

CelesticTown_Arc2Return:
    Return

    .balign 4, 0
CelesticTown_Arc2Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
CelesticTown_Arc2Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
CelesticTown_Arc2Movement_CyrusLeave:
    FaceEast
    Delay8 2
    WalkNormalEast 4
    EndMovement


// City-entry cinematic (lane cine): on the first entry per save, a short
// pull-back and slow return while player input waits (LockAll). No-ops
// when OverworldCinematics is off.
CelesticTown_CineCityEntry:
    SetVar VAR_CINE_CITY_PENDING, 0
    GoToIfSet FLAG_CINE_VISITED_CELESTIC, CelesticTown_CineCityEntryDone
    SetFlag FLAG_CINE_VISITED_CELESTIC
    LockAll
    CineCamTo 0, 0, 1000, 42, 0, 13, 80, 1
    CineWaitCamera
    CineCamReturn 70, 1
    CineWaitCamera
    ReleaseAll
CelesticTown_CineCityEntryDone:
    End
