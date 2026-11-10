#include "macros/scrcmd.inc"
#include "res/text/bank/celestic_town_cave.h"
#include "res/field/maps/locals/celestic_town_cave.h"


    ScriptEntry CelesticTownCave_Painting
    ScriptEntry CelesticTownCave_Cyrus
    ScriptEntry CelesticTownCave_Elder
    ScriptEntry CelesticTownCave_OnTransition
    ScriptEntry CelesticTownCave_Arc2Stories
    ScriptEntry CelesticTownCave_Arc2Elder
    ScriptEntry CelesticTownCave_Arc2Rowan
    ScriptEntryEnd

CelesticTownCave_Painting:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfGe VAR_ARC2_PROGRESS, 1, CelesticTownCave_Arc2Mural
    GoToIfSet FLAG_ARRESTED_CHARON_STARK_MOUNTAIN, CelesticTownCave_PaintingCynthia
    GoTo CelesticTownCave_ExaminePainting
    End

CelesticTownCave_ExaminePainting:
    GoToIfUnset FLAG_EXAMINED_CELESTIC_TOWN_CAVE_PAINTING, CelesticTownCave_EnterCyrus
    BufferPlayerName 0
    Message CelesticTownCave_Text_PlayerExaminedPainting
    WaitButton
    CloseMessage
    ReleaseAll
    End

CelesticTownCave_EnterCyrus:
    BufferPlayerName 0
    Message CelesticTownCave_Text_WhatsThisAbout
    CloseMessage
    SetFlag FLAG_EXAMINED_CELESTIC_TOWN_CAVE_PAINTING
    ClearFlag FLAG_HIDE_CELESTIC_TOWN_CAVE_ELDER
    SetObjectEventPos LOCALID_ELDER, 4, 11
    SetObjectEventDir LOCALID_ELDER, DIR_NORTH
    SetObjectEventMovementType LOCALID_ELDER, MOVEMENT_TYPE_LOOK_NORTH
    AddObject LOCALID_ELDER
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 9, CelesticTownCave_ElderEnterX9
    CallIfEq VAR_0x8004, 10, CelesticTownCave_ElderEnterX10
    Message CelesticTownCave_Text_AncientLegendOfSinnoh
    Message CelesticTownCave_Text_IdLikeToKnowMore
    CloseMessage
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderWalkOnSpotSouth
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWalkOnSpotSouth
    WaitMovement
    Message CelesticTownCave_Text_WhoMightYouBe
    CloseMessage
    SetFlag FLAG_HIDE_CELESTIC_TOWN_ELDER
    ClearFlag FLAG_HIDE_CELESTIC_TOWN_CAVE_CYRUS
    SetObjectEventPos LOCALID_CYRUS, 4, 11
    SetObjectEventDir LOCALID_CYRUS, DIR_NORTH
    SetObjectEventMovementType LOCALID_CYRUS, MOVEMENT_TYPE_LOOK_NORTH
    AddObject LOCALID_CYRUS
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 9, CelesticTownCave_CyrusEnterX9
    CallIfEq VAR_0x8004, 10, CelesticTownCave_CyrusEnterX10
    Message CelesticTownCave_Text_MyNameIsCyrus
    Message CelesticTownCave_Text_NotInterested
    Message CelesticTownCave_Text_ChallengeMe
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, CelesticTownCave_BattleCyrus
    GoToIfEq VAR_RESULT, MENU_NO, CelesticTownCave_DontBattleNow
    End

CelesticTownCave_ElderEnterX9:
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderEnterX9
    WaitMovement
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWalkOnSpotEast
    WaitMovement
    Return

CelesticTownCave_ElderEnterX10:
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderEnterX10
    WaitMovement
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWalkOnSpotWest
    WaitMovement
    Return

CelesticTownCave_DontBattleNow:
    Message CelesticTownCave_Text_YouChoseCoward2
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 9, CelesticTownCave_CyrusPushPlayerX9
    CallIfEq VAR_0x8004, 10, CelesticTownCave_CyrusPushPlayerX10
    ReleaseAll
    End

CelesticTownCave_CyrusPushPlayerX9:
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderWatchCyrusPushPlayerX9
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerGetPushedX9
    ApplyMovement LOCALID_CYRUS, CelesticTownCave_Movement_CyrusPushPlayerX9
    WaitMovement
    Return

CelesticTownCave_CyrusPushPlayerX10:
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderWatchCyrusPushPlayerX10
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerGetPushedX10
    ApplyMovement LOCALID_CYRUS, CelesticTownCave_Movement_CyrusPushPlayerX10
    WaitMovement
    Return

CelesticTownCave_BattleCyrus:
    Message CelesticTownCave_Text_ErrorOfYourWays
    CloseMessage
    StartTrainerBattle TRAINER_GALACTIC_BOSS_CYRUS_CELESTIC_TOWN_RUINS
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, CelesticTownCave_Blackout
    Call CelesticTownCave_DefeatedCyrus
    ReleaseAll
    End

CelesticTownCave_DefeatedCyrus:
    ClearFlag FLAG_HIDE_CELESTIC_TOWN_CYNTHIA
    SetVar VAR_CELESTIC_TOWN_STATE, 1
    Message CelesticTownCave_Text_Remarkable
    CloseMessage
    WaitTime 15, VAR_RESULT
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_CYRUS
    FadeScreenIn
    WaitFadeScreen
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 8, CelesticTownCave_PlayerElderFaceEachOtherX8
    CallIfEq VAR_0x8004, 9, CelesticTownCave_PlayerElderFaceEachOtherX9
    CallIfEq VAR_0x8004, 10, CelesticTownCave_PlayerElderFaceEachOtherX10
    CallIfEq VAR_0x8004, 11, CelesticTownCave_PlayerElderFaceEachOtherX11
    // Arc 2 (D11): the elder's HM03 (Surf) give is removed; this stock scene is also unreachable from Arc 2 on.
    SetFlag FLAG_HIDE_CELESTIC_TOWN_ELDER
    ClearFlag FLAG_HIDE_CELESTIC_TOWN_NORTH_HOUSE_ELDER
    SetFlag FLAG_DUMMY_0x098D
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 9, CelesticTownCave_ElderLeaveX9
    CallIfEq VAR_0x8004, 10, CelesticTownCave_ElderLeaveX10
    CallIfEq VAR_0x8004, 11, CelesticTownCave_ElderLeaveX11
    RemoveObject LOCALID_ELDER
    Return

CelesticTownCave_CyrusEnterX9:
    ApplyMovement LOCALID_CYRUS, CelesticTownCave_Movement_CyrusEnterX9
    WaitMovement
    Return

CelesticTownCave_CyrusEnterX10:
    ApplyMovement LOCALID_CYRUS, CelesticTownCave_Movement_CyrusEnterX10
    WaitMovement
    Return

CelesticTownCave_PlayerElderFaceEachOtherX8:
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWalkEast
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderWalkOnSpotWest
    WaitMovement
    Return

CelesticTownCave_PlayerElderFaceEachOtherX9:
    GoToIfEq VAR_0x8005, 4, CelesticTownCave_PlayerElderFaceEachOtherX9South
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWalkOnSpotEast2
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderWalkOnSpotWest
    WaitMovement
    Return

CelesticTownCave_PlayerElderFaceEachOtherX9South:
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWalkNorthOnSpotEast
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderWalkOnSpotWest
    WaitMovement
    Return

CelesticTownCave_Unused:
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_Unused
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderWalkOnSpotWest
    WaitMovement
    Return

CelesticTownCave_PlayerElderFaceEachOtherX10:
    GoToIfEq VAR_0x8005, 4, CelesticTownCave_PlayerElderFaceEachOtherX10South
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWalkOnSpotWest2
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderWalkOnSpotEast
    WaitMovement
    Return

CelesticTownCave_PlayerElderFaceEachOtherX10South:
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWalkNorthOnSpotWest
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderWalkOnSpotEast
    WaitMovement
    Return

CelesticTownCave_Unused2:
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_Unused2
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderWalkOnSpotWest
    WaitMovement
    Return

CelesticTownCave_PlayerElderFaceEachOtherX11:
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWalkWest
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderWalkOnSpotEast2
    WaitMovement
    Return

CelesticTownCave_ElderLeaveX9:
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWatchElderLeave
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderLeaveX9
    WaitMovement
    Return

CelesticTownCave_ElderLeaveX10:
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWatchElderLeave
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderLeaveX10
    WaitMovement
    Return

CelesticTownCave_ElderLeaveX11:
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWatchElderLeave
    ApplyMovement LOCALID_ELDER, CelesticTownCave_Movement_ElderLeaveX11
    WaitMovement
    Return

CelesticTownCave_Blackout:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
CelesticTownCave_Movement_CyrusEnterX9:
    WalkNormalNorth 6
    WalkNormalEast
    WalkNormalNorth
    WalkNormalEast 5
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_CyrusEnterX10:
    WalkNormalNorth 6
    WalkNormalEast
    WalkNormalNorth
    WalkNormalEast 4
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_CyrusPushPlayerX9:
    WalkNormalWest
    WalkNormalNorth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_CyrusPushPlayerX10:
    WalkNormalEast
    WalkNormalNorth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWalkOnSpotWest:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerGetPushedX9:
    Delay8
    FaceEast
    LockDir
    WalkFastWest
    UnlockDir
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerGetPushedX10:
    Delay8
    FaceWest
    LockDir
    WalkFastEast
    UnlockDir
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWalkEast:
    WalkNormalEast
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWalkOnSpotEast2:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWalkNorthOnSpotEast:
    WalkNormalNorth
    WalkOnSpotNormalEast
    EndMovement

CelesticTownCave_Movement_Unused:
    WalkNormalNorth 2
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWalkOnSpotWest2:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWalkNorthOnSpotWest:
    WalkNormalNorth
    WalkOnSpotNormalWest
    EndMovement

CelesticTownCave_Movement_Unused2:
    WalkNormalNorth 2
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWalkWest:
    WalkNormalWest
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWatchElderLeave:
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_ElderEnterX9:
    WalkNormalNorth 6
    WalkNormalEast
    WalkNormalNorth
    WalkNormalEast 5
    WalkNormalNorth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_ElderEnterX10:
    WalkNormalNorth 6
    WalkNormalEast
    WalkNormalNorth
    WalkNormalEast 4
    WalkNormalNorth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_ElderWalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_ElderWatchCyrusPushPlayerX9:
    Delay8
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_ElderWatchCyrusPushPlayerX10:
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_ElderWalkOnSpotWest:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_ElderWalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_ElderWalkOnSpotEast2:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_ElderLeaveX9:
    WalkNormalSouth
    WalkNormalWest 5
    WalkNormalSouth
    WalkNormalWest
    WalkNormalSouth 6
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_ElderLeaveX10:
    WalkNormalSouth
    WalkNormalWest 4
    WalkNormalSouth
    WalkNormalWest
    WalkNormalSouth 6
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_ElderLeaveX11:
    WalkNormalSouth
    WalkNormalWest 5
    WalkNormalSouth
    WalkNormalWest
    WalkNormalSouth 6
    EndMovement

CelesticTownCave_Cyrus:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message CelesticTownCave_Text_WellChallengeMe
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, CelesticTownCave_YouChoseCoward
    Message CelesticTownCave_Text_ErrorOfYourWays
    CloseMessage
    StartTrainerBattle TRAINER_GALACTIC_BOSS_CYRUS_CELESTIC_TOWN_RUINS
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, CelesticTownCave_Blackout
    Call CelesticTownCave_DefeatedCyrus
    ReleaseAll
    End

CelesticTownCave_YouChoseCoward:
    Message CelesticTownCave_Text_YouChoseCoward
    WaitButton
    CloseMessage
    ReleaseAll
    End

CelesticTownCave_Elder:
    EventMessage CelesticTownCave_Text_WeValueMemories
    End

CelesticTownCave_PaintingCynthia:
    GoToIfSet FLAG_TALKED_TO_CELESTIC_TOWN_CAVE_CYNTHIA, CelesticTownCave_ExaminePainting
    SetFlag FLAG_TALKED_TO_CELESTIC_TOWN_CAVE_CYNTHIA
    ClearFlag FLAG_HIDE_CELESTIC_TOWN_CAVE_CYNTHIA
    SetObjectEventPos LOCALID_CYNTHIA, 4, 11
    AddObject LOCALID_CYNTHIA
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 9, CelesticTownCave_CynthiaEnterX9
    CallIfEq VAR_0x8004, 10, CelesticTownCave_CynthiaEnterX10
    Message CelesticTownCave_Text_PaintingDescribedThisWay
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 9, CelesticTownCave_CynthiaWalkOnSpotWest
    CallIfEq VAR_0x8004, 10, CelesticTownCave_CynthiaWalkOnSpotEast
    Message CelesticTownCave_Text_MayIContinue
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, CelesticTownCave_IGotCarriedAway
    CloseMessage
    ApplyMovement LOCALID_CYNTHIA, CelesticTownCave_Movement_CynthiaWalkOnSpotNorth
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerDelayWalkOnSpotNorth
    WaitMovement
    WaitTime 15, VAR_RESULT
    Message CelesticTownCave_Text_OtherInterpretationContinueLonger
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 9, CelesticTownCave_CynthiaWalkOnSpotWest
    CallIfEq VAR_0x8004, 10, CelesticTownCave_CynthiaWalkOnSpotEast
    CallIfEq VAR_0x8004, 9, CelesticTownCave_PlayerWalkOnSpotEast
    CallIfEq VAR_0x8004, 10, CelesticTownCave_PlayerWalkOnSpotWest
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, CelesticTownCave_IGotCarriedAway
    Message CelesticTownCave_Text_ThanksForListening
    CloseMessage
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWatchCynthiaWalkSouth
    ApplyMovement LOCALID_CYNTHIA, CelesticTownCave_Movement_CynthiaWalkSouth
    WaitMovement
    Message CelesticTownCave_Text_NotSureHowGiratinaFits
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 9, CelesticTownCave_CynthiaWalkBackToPlayerX9
    CallIfEq VAR_0x8004, 10, CelesticTownCave_CynthiaWalkBackToPlayerX10
    Message CelesticTownCave_Text_MayISayLastBit
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, CelesticTownCave_IGotCarriedAway
    Message CelesticTownCave_Text_ThatsWhatIBelieve
    GoTo CelesticTownCave_CynthiaLeave
    End

CelesticTownCave_CynthiaEnterX9:
    ApplyMovement LOCALID_CYNTHIA, CelesticTownCave_Movement_CynthiaEnterX9
    WaitMovement
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWalkOnSpotEast3
    WaitMovement
    Return

CelesticTownCave_CynthiaEnterX10:
    ApplyMovement LOCALID_CYNTHIA, CelesticTownCave_Movement_CynthiaEnterX10
    WaitMovement
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWalkOnSpotWest3
    WaitMovement
    Return

CelesticTownCave_PlayerWalkOnSpotEast:
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWalkOnSpotEast3
    WaitMovement
    Return

CelesticTownCave_PlayerWalkOnSpotWest:
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWalkOnSpotWest3
    WaitMovement
    Return

CelesticTownCave_CynthiaWalkOnSpotWest:
    ApplyMovement LOCALID_CYNTHIA, CelesticTownCave_Movement_CynthiaWalkOnSpotWest
    WaitMovement
    Return

CelesticTownCave_CynthiaWalkOnSpotEast:
    ApplyMovement LOCALID_CYNTHIA, CelesticTownCave_Movement_CynthiaWalkOnSpotEast
    WaitMovement
    Return

CelesticTownCave_CynthiaWalkBackToPlayerX9:
    ApplyMovement LOCALID_CYNTHIA, CelesticTownCave_Movement_CynthiaWalkBackToPlayerX9
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWatchCynthiaWalkBackX9
    WaitMovement
    Return

CelesticTownCave_CynthiaWalkBackToPlayerX10:
    ApplyMovement LOCALID_CYNTHIA, CelesticTownCave_Movement_CynthiaWalkBackToPlayerX10
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWatchCynthiaWalkBackX10
    WaitMovement
    Return

CelesticTownCave_IGotCarriedAway:
    Message CelesticTownCave_Text_IGotCarriedAway
    GoTo CelesticTownCave_CynthiaLeave
    End

CelesticTownCave_CynthiaLeave:
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 9, CelesticTownCave_CynthiaLeaveX9
    CallIfEq VAR_0x8004, 10, CelesticTownCave_CynthiaLeaveX10
    RemoveObject LOCALID_CYNTHIA
    ReleaseAll
    End

CelesticTownCave_CynthiaLeaveX9:
    ApplyMovement LOCALID_CYNTHIA, CelesticTownCave_Movement_CynthiaLeaveX9
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWatchCynthiaLeave
    WaitMovement
    Return

CelesticTownCave_CynthiaLeaveX10:
    ApplyMovement LOCALID_CYNTHIA, CelesticTownCave_Movement_CynthiaLeaveX10
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Movement_PlayerWatchCynthiaLeave
    WaitMovement
    Return

    .balign 4, 0
CelesticTownCave_Movement_CynthiaEnterX9:
    WalkNormalNorth 6
    WalkNormalEast
    WalkNormalNorth
    WalkNormalEast 5
    WalkNormalNorth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_CynthiaEnterX10:
    WalkNormalNorth 6
    WalkNormalEast
    WalkNormalNorth
    WalkNormalEast 4
    WalkNormalNorth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_CynthiaWalkOnSpotWest:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_CynthiaWalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_CynthiaWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_CynthiaWalkSouth:
    WalkNormalSouth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_CynthiaWalkBackToPlayerX9:
    WalkNormalNorth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_CynthiaWalkBackToPlayerX10:
    WalkNormalNorth
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_CynthiaLeaveX9:
    WalkNormalSouth
    WalkNormalWest 5
    WalkNormalSouth
    WalkNormalWest
    WalkNormalSouth 6
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_CynthiaLeaveX10:
    WalkNormalSouth
    WalkNormalWest 4
    WalkNormalSouth
    WalkNormalWest
    WalkNormalSouth 6
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWalkOnSpotEast3:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWalkOnSpotWest3:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerDelayWalkOnSpotNorth:
    Delay8
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWatchCynthiaWalkSouth:
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWatchCynthiaWalkBackX9:
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWatchCynthiaWalkBackX10:
    Delay8
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
CelesticTownCave_Movement_PlayerWatchCynthiaLeave:
    Delay8 2
    FaceWest
    EndMovement

CelesticTownCave_OnTransition:
    GoToIfGe VAR_ARC2_PROGRESS, 40, CelesticTownCave_OnTransitionArc2
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    End

CelesticTownCave_OnTransitionArc2:
    CallIfNe VAR_ARC2_PROGRESS, 40, CelesticTownCave_HideGroup
    CallIfGe VAR_ARC2_PROGRESS, 44, CelesticTownCave_HideRowan
    End

CelesticTownCave_HideGroup:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    Return

CelesticTownCave_HideRowan:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    Return

CelesticTownCave_Arc2Mural:
    BufferPlayerName 0
    Message CelesticTownCave_Text_PlayerExaminedPainting
    WaitButton
    CloseMessage
    ReleaseAll
    End

CelesticTownCave_Arc2Elder:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message CelesticTownCave_Text_Arc2ElderBeneathRepeat
    WaitButton
    CloseMessage
    ReleaseAll
    End

CelesticTownCave_Arc2Rowan:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message CelesticTownCave_Text_Arc2RowanGoOnRepeat
    WaitButton
    CloseMessage
    ReleaseAll
    End

// 2.15 + 2.16 (shrine part): runs from the frame table when the player walks in at state 40.
CelesticTownCave_Arc2Stories:
    LockAll
    ApplyMovement LOCALID_PLAYER, CelesticTownCave_Arc2Movement_PlayerWalkIn
    WaitMovement
    ApplyMovement LOCALID_ARC2_ROWAN, CelesticTownCave_Arc2Movement_FaceWest
    WaitMovement
    Message CelesticTownCave_Text_Arc2RowanThanks
    Message CelesticTownCave_Text_Arc2ElderChildren
    Message CelesticTownCave_Text_Arc2ElderSit
    // Polish #8: the preamble (old msgs 27-29) is one box
    Message CelesticTownCave_Text_Arc2ElderThree
    Message CelesticTownCave_Text_Arc2ElderListen
    CloseMessage
    // the king (Saros)
    ApplyMovement LOCALID_ARC2_ELDER, CelesticTownCave_Arc2Movement_FaceNorth
    WaitMovement
    Message CelesticTownCave_Text_Arc2ElderKing
    CloseMessage
    ApplyMovement LOCALID_ARC2_SAROS, CelesticTownCave_Arc2Movement_FaceWest
    WaitMovement
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_ARC2_SAROS, CelesticTownCave_Arc2Movement_FaceEast
    WaitMovement
    // the sailor (Kahn), the sister (Indra), the shared ending.
    // Polish #8: she faces the mural for each story and turns back to the room between them.
    ApplyMovement LOCALID_ARC2_ELDER, CelesticTownCave_Arc2Movement_FaceSouth
    WaitMovement
    WaitTime 15, VAR_RESULT
    ApplyMovement LOCALID_ARC2_ELDER, CelesticTownCave_Arc2Movement_FaceNorth
    WaitMovement
    Message CelesticTownCave_Text_Arc2ElderSailor
    CloseMessage
    ApplyMovement LOCALID_ARC2_ELDER, CelesticTownCave_Arc2Movement_FaceSouth
    WaitMovement
    WaitTime 15, VAR_RESULT
    ApplyMovement LOCALID_ARC2_ELDER, CelesticTownCave_Arc2Movement_FaceNorth
    WaitMovement
    Message CelesticTownCave_Text_Arc2ElderSister
    CloseMessage
    ApplyMovement LOCALID_ARC2_ELDER, CelesticTownCave_Arc2Movement_FaceSouth
    WaitMovement
    WaitTime 15, VAR_RESULT
    Message CelesticTownCave_Text_Arc2ElderBeneath
    CloseMessage
    WaitTime 30, VAR_RESULT
    Message CelesticTownCave_Text_Arc2CyrusEveryTime
    Message CelesticTownCave_Text_Arc2ElderEveryTimeIKnow
    Message CelesticTownCave_Text_Arc2SarosRespect
    ApplyMovement LOCALID_ARC2_GARIUS, CelesticTownCave_Arc2Movement_FaceWest
    WaitMovement
    BufferRivalName 0
    Message CelesticTownCave_Text_Arc2GariusOldStories
    ApplyMovement LOCALID_ARC2_ELDER, CelesticTownCave_Arc2Movement_FaceEast
    WaitMovement
    Message CelesticTownCave_Text_Arc2ElderWhatLost
    BufferRivalName 0
    Message CelesticTownCave_Text_Arc2GariusNothing
    CloseMessage
    ApplyMovement LOCALID_ARC2_SAROS, CelesticTownCave_Arc2Movement_FaceEast
    WaitMovement
    Message CelesticTownCave_Text_Arc2SarosSharp
    BufferRivalName 0
    Message CelesticTownCave_Text_Arc2GariusNotInterested
    CloseMessage
    // Saros bows to the elder and walks out.
    ApplyMovement LOCALID_ARC2_SAROS, CelesticTownCave_Arc2Movement_Bow
    WaitMovement
    ApplyMovement LOCALID_ARC2_SAROS, CelesticTownCave_Arc2Movement_SarosLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_SAROS
    SetVar VAR_ARC2_PROGRESS, 42
    // Polish #5: the room reacts to Saros
    ApplyMovement LOCALID_ARC2_RUTH, CelesticTownCave_Arc2Movement_FaceWest
    WaitMovement
    Message CelesticTownCave_Text_Arc2RuthWhoWasThat
    Message CelesticTownCave_Text_Arc2ElderYesterday
    ApplyMovement LOCALID_ARC2_ROWAN, CelesticTownCave_Arc2Movement_FaceEast
    WaitMovement
    Message CelesticTownCave_Text_Arc2RowanEclipse
    CloseMessage
    // 2.16: Rowan's question
    ApplyMovement LOCALID_ARC2_ELDER, CelesticTownCave_Arc2Movement_FaceEast
    ApplyMovement LOCALID_ARC2_ROWAN, CelesticTownCave_Arc2Movement_FaceWest
    WaitMovement
    Message CelesticTownCave_Text_Arc2RowanQuestion
    Message CelesticTownCave_Text_Arc2ElderCost
    Message CelesticTownCave_Text_Arc2RowanSayingNo
    BufferRivalName 0
    Message CelesticTownCave_Text_Arc2GariusHuh
    BufferRivalName 0
    Message CelesticTownCave_Text_Arc2GariusVeilstone
    CloseMessage
    ApplyMovement LOCALID_ARC2_GARIUS, CelesticTownCave_Arc2Movement_GariusLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_GARIUS
    ApplyMovement LOCALID_ARC2_RUTH, CelesticTownCave_Arc2Movement_FaceWest
    WaitMovement
    Message CelesticTownCave_Text_Arc2RuthVeilstone
    ApplyMovement LOCALID_ARC2_ROWAN, CelesticTownCave_Arc2Movement_FaceSouth
    WaitMovement
    Message CelesticTownCave_Text_Arc2RowanGoOn
    CloseMessage
    ApplyMovement LOCALID_ARC2_RUTH, CelesticTownCave_Arc2Movement_RuthLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_RUTH
    // Cyrus goes out without a word (he waits outside, 2.16).
    ApplyMovement LOCALID_ARC2_CYRUS, CelesticTownCave_Arc2Movement_CyrusLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_CYRUS
    ApplyMovement LOCALID_ARC2_ROWAN, CelesticTownCave_Arc2Movement_FaceWest
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
CelesticTownCave_Arc2Movement_PlayerWalkIn:
    WalkNormalNorth 8
    WalkNormalWest 6
    WalkNormalNorth 7
    WalkNormalEast
    WalkNormalNorth
    WalkNormalEast 5
    FaceNorth
    EndMovement

    .balign 4, 0
CelesticTownCave_Arc2Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
CelesticTownCave_Arc2Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
CelesticTownCave_Arc2Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
CelesticTownCave_Arc2Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
CelesticTownCave_Arc2Movement_Bow:
    WalkOnSpotNormalEast
    Delay8
    EndMovement

    .balign 4, 0
CelesticTownCave_Arc2Movement_SarosLeave:
    WalkNormalSouth
    WalkNormalWest 2
    WalkNormalSouth
    WalkNormalWest
    WalkNormalSouth 6
    EndMovement

    .balign 4, 0
CelesticTownCave_Arc2Movement_GariusLeave:
    WalkNormalEast
    WalkNormalSouth 5
    EndMovement

    .balign 4, 0
CelesticTownCave_Arc2Movement_RuthLeave:
    WalkNormalEast 2
    WalkNormalSouth 6
    EndMovement

    .balign 4, 0
CelesticTownCave_Arc2Movement_CyrusLeave:
    WalkNormalWest 2
    WalkNormalSouth
    WalkNormalWest 2
    WalkNormalSouth
    WalkNormalWest
    WalkNormalSouth 6
    EndMovement

