#include "macros/scrcmd.inc"
#include "res/text/bank/eterna_forest.h"
#include "res/field/maps/locals/eterna_forest.h"
#include "constants/totem_battle.h"

#define FLAG_ARC2_FLOAROMA_SILENCE_SEEN FLAG_ARC2_FLOAROMA_B

    ScriptEntry EternaForest_CoordEvent_CherylStartFollowing
    ScriptEntry EternaForest_CoordEvent_PlayerLeaveCheryl
    ScriptEntry EternaForest_CoordEvent_CherylLeavePlayer
    ScriptEntry EternaForest_Dummy4
    ScriptEntry EternaForest_Dummy5
    ScriptEntry EternaForest_BugCatcher
    ScriptEntry EternaForest_Gardenia
    ScriptEntry EternaForest_SignboardEternaForest
    ScriptEntry EternaForest_TrainerTipsSignpost
    ScriptEntry EternaForest_MossRock
    ScriptEntry EternaForest_OnTransition
    ScriptEntry EternaForest_OnFrame_CherylOldChateauCutscene
    ScriptEntry EternaForest_Arc2Ruth
    ScriptEntry EternaForest_Arc2Cyrus
    ScriptEntry EternaForest_Arc2Rift
    ScriptEntry EternaForest_Arc2Silence
    ScriptEntry EternaForest_Arc2Aftermath
    ScriptEntryEnd

EternaForest_OnTransition:
    Call EternaForest_Arc2SetObjects
    GoToIfUnset FLAG_TRAVELED_WITH_CHERYL, EternaForest_ResetFollowerCherylState
    End

EternaForest_ResetFollowerCherylState:
    SetVar VAR_ETERNA_FOREST_FOLLOWER_CHERYL_STATE, 0
    End

EternaForest_CoordEvent_CherylStartFollowing:
    LockAll
    SetPlayerBike FALSE
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8004, 28, EternaForest_CherylNoticeAndWalkToPlayerX28
    GoToIfEq VAR_0x8004, 29, EternaForest_CherylNoticeAndWalkToPlayerX29
    End

EternaForest_CherylNoticeAndWalkToPlayerX28:
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylNoticeAndWalkToPlayerX28
    WaitMovement
    GoTo EternaForest_CherylStartFollowing

EternaForest_CherylNoticeAndWalkToPlayerX29:
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylNoticeAndWalkToPlayerX29
    WaitMovement
    GoTo EternaForest_CherylStartFollowing

EternaForest_CherylStartFollowing:
    CallIfUnset FLAG_TALKED_TO_ETERNA_FOREST_CHERYL, EternaForest_MayIGoWithYou
    CallIfSet FLAG_TALKED_TO_ETERNA_FOREST_CHERYL, EternaForest_LetsGetThroughForestTogether
    BufferPlayerName 0
    PlayFanfare SEQ_GONIN_sseq
    Message EternaForest_Text_PlayerDecidedToGoWithCheryl
    WaitFanfare
    GoTo FLAG_TALKED_TO_ETERNA_FOREST_CHERYL
    SetVar VAR_ETERNA_FOREST_FOLLOWER_CHERYL_STATE, 1
    Message EternaForest_Text_IllKeepPokemonHealthy
    WaitButton
    CloseMessage
    SetVar VAR_PARTNER_TRAINER_ID, TRAINER_CHERYL_ETERNA_FOREST
    SetHasPartner
    SetMovementType LOCALID_CHERYL, MOVEMENT_TYPE_FOLLOW_PLAYER
    SetObjectFlagIsPersistent LOCALID_CHERYL, TRUE
    ReleaseAll
    End

EternaForest_MayIGoWithYou:
    BufferPlayerName 0
    Message EternaForest_Text_MayIGoWithYou
    Return

EternaForest_LetsGetThroughForestTogether:
    BufferPlayerName 0
    Message EternaForest_Text_LetsGetThroughForestTogether
    Return

    .balign 4, 0
EternaForest_Movement_CherylNoticeAndWalkToPlayerX28:
    MoveAction_153
    WalkNormalSouth
    EndMovement

    .balign 4, 0
EternaForest_Movement_CherylNoticeAndWalkToPlayerX29:
    MoveAction_153
    WalkNormalSouth
    WalkNormalEast
    WalkOnSpotNormalSouth
    EndMovement

EternaForest_CoordEvent_PlayerLeaveCheryl:
    LockAll
    ClearHasPartner
    SetMovementType LOCALID_CHERYL, MOVEMENT_TYPE_LOOK_SOUTH
    SetObjectFlagIsPersistent LOCALID_CHERYL, FALSE
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylWalkOnSpotSouth
    WaitMovement
    Message EternaForest_Text_IllWaitHereForYouThen
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8004, 28, EternaForest_CherylWalkBackToOriginalPositionX28
    GoToIfEq VAR_0x8004, 29, EternaForest_CherylWalkBackToOriginalPositionX29
    End

EternaForest_CherylWalkBackToOriginalPositionX28:
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylWalkBackToOriginalPositionX28
    WaitMovement
    GoTo EternaForest_ResetFollowerCherylStateAndRelease

EternaForest_CherylWalkBackToOriginalPositionX29:
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylWalkBackToOriginalPositionX29
    WaitMovement
    GoTo EternaForest_ResetFollowerCherylStateAndRelease

EternaForest_ResetFollowerCherylStateAndRelease:
    SetVar VAR_ETERNA_FOREST_FOLLOWER_CHERYL_STATE, 0
    ReleaseAll
    End

    .balign 4, 0
EternaForest_Movement_CherylWalkBackToOriginalPositionX28:
    WalkNormalNorth 2
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
EternaForest_Movement_CherylWalkBackToOriginalPositionX29:
    WalkNormalNorth 2
    WalkNormalWest
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
EternaForest_Movement_CherylWalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

EternaForest_CoordEvent_CherylLeavePlayer:
    LockAll
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylExclamationMark
    ApplyMovement LOCALID_PLAYER, EternaForest_Movement_PlayerWalkOnSpotWest
    WaitMovement
    BufferPlayerName 0
    Message EternaForest_Text_ThankYouSoMuch
    SetVar VAR_0x8004, ITEM_SOOTHE_BELL
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, EternaForest_CherylWalkToExit
    GoTo EternaForest_GiveSootheBell
    End

EternaForest_GiveSootheBell:
    Message EternaForest_Text_TokenOfAppreciation
    CallCommonScript CommonScript_AddItemQuantityNoLineFeed
    GoTo EternaForest_CherylWalkToExit
    End

EternaForest_CherylWalkToExit:
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 34, EternaForest_CherylWalkToExitX34
    GoToIfEq VAR_0x8005, 35, EternaForest_CherylWalkToExitX35
    GoToIfEq VAR_0x8005, 36, EternaForest_CherylWalkToExitX36
    GoToIfEq VAR_0x8005, 37, EternaForest_CherylWalkToExitX37
    GoToIfEq VAR_0x8005, 38, EternaForest_CherylWalkToExitX38
    GoTo EternaForest_CherylWalkToExitX39
    End

EternaForest_CherylWalkToExitX34:
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylWalkToExitX34
    ApplyMovement LOCALID_PLAYER, EternaForest_Movement_PlayerWatchCherylWalkToExitX34
    WaitMovement
    GoTo EternaForest_CherylLeave

EternaForest_CherylWalkToExitX35:
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylWalkToExitX35
    ApplyMovement LOCALID_PLAYER, EternaForest_Movement_PlayerWatchCherylWalkToExitX35
    WaitMovement
    GoTo EternaForest_CherylLeave

EternaForest_CherylWalkToExitX36:
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylWalkToExitX36
    ApplyMovement LOCALID_PLAYER, EternaForest_Movement_PlayerWatchCherylWalkToExitX36
    WaitMovement
    GoTo EternaForest_CherylLeave

EternaForest_CherylWalkToExitX37:
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylWalkToExitX37
    ApplyMovement LOCALID_PLAYER, EternaForest_Movement_PlayerWatchCherylWalkToExitX37
    WaitMovement
    GoTo EternaForest_CherylLeave

EternaForest_CherylWalkToExitX38:
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylWalkToExitX38
    ApplyMovement LOCALID_PLAYER, EternaForest_Movement_PlayerWatchCherylWalkToExitX38
    WaitMovement
    GoTo EternaForest_CherylLeave

EternaForest_CherylWalkToExitX39:
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylWalkToExitX39
    ApplyMovement LOCALID_PLAYER, EternaForest_Movement_PlayerWatchCherylWalkToExitX39
    WaitMovement
    GoTo EternaForest_CherylLeave

EternaForest_CherylLeave:
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylWalkOnSpotWest
    WaitMovement
    Message EternaForest_Text_ImSureWellMeetAgain
    CloseMessage
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylLeave
    WaitMovement
    PlaySE SEQ_SE_DP_KAIDAN2_sseq
    ClearHasPartner
    RemoveObject LOCALID_CHERYL
    WaitSE SEQ_SE_DP_KAIDAN2_sseq
    SetFlag FLAG_TRAVELED_WITH_CHERYL
    SetVar VAR_ETERNA_FOREST_FOLLOWER_CHERYL_STATE, 2
    ReleaseAll
    End

    .balign 4, 0
EternaForest_Movement_CherylExclamationMark:
    WalkOnSpotNormalEast
    MoveAction_153
    EndMovement

    .balign 4, 0
EternaForest_Movement_CherylWalkToExitX34:
    WalkNormalSouth 2
    WalkNormalEast 5
    EndMovement

    .balign 4, 0
EternaForest_Movement_CherylWalkToExitX35:
    WalkNormalSouth
    WalkNormalEast 5
    EndMovement

    .balign 4, 0
EternaForest_Movement_CherylWalkToExitX36:
    WalkNormalSouth
    WalkNormalEast 5
    EndMovement

    .balign 4, 0
EternaForest_Movement_CherylWalkToExitX37:
    WalkNormalNorth
    WalkNormalEast 5
    EndMovement

    .balign 4, 0
EternaForest_Movement_CherylWalkToExitX38:
    WalkNormalNorth
    WalkNormalEast 5
    EndMovement

    .balign 4, 0
EternaForest_Movement_CherylWalkToExitX39:
    WalkNormalNorth 2
    WalkNormalEast 5
    EndMovement

    .balign 4, 0
EternaForest_Movement_CherylWalkOnSpotWest:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
EternaForest_Movement_CherylLeave:
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
EternaForest_Movement_PlayerWalkOnSpotWest:
    Delay8 3
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
EternaForest_Movement_PlayerWatchCherylWalkToExitX34:
    Delay8 2
    WalkOnSpotNormalSouth
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
EternaForest_Movement_PlayerWatchCherylWalkToExitX35:
    Delay8
    WalkOnSpotNormalSouth
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
EternaForest_Movement_PlayerWatchCherylWalkToExitX36:
    Delay8
    WalkOnSpotNormalSouth
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
EternaForest_Movement_PlayerWatchCherylWalkToExitX37:
    Delay8
    WalkOnSpotNormalNorth
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
EternaForest_Movement_PlayerWatchCherylWalkToExitX38:
    Delay8
    WalkOnSpotNormalNorth
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
EternaForest_Movement_PlayerWatchCherylWalkToExitX39:
    Delay8 2
    WalkOnSpotNormalNorth
    Delay8
    WalkOnSpotNormalEast
    EndMovement

EternaForest_Dummy4:
    LockAll
    BufferPlayerName 0
    ReleaseAll
    End

EternaForest_Dummy5:
    LockAll
    BufferPlayerName 0
    ReleaseAll
    End

EternaForest_BugCatcher:
    NPCMessage EternaForest_Text_ImSearchingForBugPokemon
    End

EternaForest_Gardenia:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message EternaForest_Text_WereYouIngriguedByRumors
    CloseMessage
    ApplyMovement LOCALID_GARDENIA, EternaForest_Movement_GardeniaWalkOnSpotNorth
    WaitMovement
    Message EternaForest_Text_GhostPokemonOfOldChateau
    FacePlayer
    Message EternaForest_Text_GoodLuckWithInvestigation
    CloseMessage
    GetPlayerDir VAR_RESULT
    GoToIfEq VAR_RESULT, DIR_NORTH, EternaForest_GardeniaLeaveNorth
    GoToIfEq VAR_RESULT, DIR_SOUTH, EternaForest_GardeniaLeaveSouth
    GoToIfEq VAR_RESULT, DIR_WEST, EternaForest_GardeniaLeaveWest
    GoToIfEq VAR_RESULT, DIR_EAST, EternaForest_GardeniaLeaveEast
    End

EternaForest_GardeniaLeaveNorth:
    ApplyMovement LOCALID_GARDENIA, EternaForest_Movement_GardeniaLeaveNorth
    WaitMovement
    GoTo EternaForest_RemoveGardenia
    End

EternaForest_GardeniaLeaveSouth:
    ApplyMovement LOCALID_GARDENIA, EternaForest_Movement_GardeniaLeaveSouthWestEast
    WaitMovement
    GoTo EternaForest_RemoveGardenia
    End

EternaForest_GardeniaLeaveWest:
    ApplyMovement LOCALID_GARDENIA, EternaForest_Movement_GardeniaLeaveSouthWestEast
    WaitMovement
    GoTo EternaForest_RemoveGardenia
    End

EternaForest_GardeniaLeaveEast:
    ApplyMovement LOCALID_GARDENIA, EternaForest_Movement_GardeniaLeaveSouthWestEast
    WaitMovement
    GoTo EternaForest_RemoveGardenia
    End

EternaForest_RemoveGardenia:
    RemoveObject LOCALID_GARDENIA
    ReleaseAll
    End

    .balign 4, 0
EternaForest_Movement_GardeniaWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
EternaForest_Movement_GardeniaLeaveSouthWestEast:
    WalkNormalSouth 2
    WalkNormalEast 9
    EndMovement

    .balign 4, 0
EternaForest_Movement_GardeniaLeaveNorth:
    WalkNormalWest
    WalkNormalSouth 2
    WalkNormalEast 10
    EndMovement

EternaForest_SignboardEternaForest:
    ShowLandmarkSign EternaForest_Text_SignEternaForest
    End

EternaForest_TrainerTipsSignpost:
    ShowScrollingSign EternaForest_Text_TrainerTipsItemsOnGround
    End

EternaForest_MossRock:
    EventMessage EternaForest_Text_RockIsCoveredInMoss
    End

EternaForest_OnFrame_CherylOldChateauCutscene:
    LockAll
    SetVar VAR_ETERNA_FOREST_CHERYL_OLD_CHATEAU_CUTSCENE_STATE, 2
    ApplyMovement LOCALID_CHERYL, EternaForest_Movement_CherylWalkOnSpotNorth
    WaitMovement
    Message EternaForest_Text_OldChateauAhead
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
EternaForest_Movement_CherylWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

EternaForest_Arc2SetObjects:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    GoToIfLt VAR_ARC2_PROGRESS, 22, EternaForest_Arc2SetObjectsEnd
    GoToIfGe VAR_ARC2_PROGRESS, 27, EternaForest_Arc2SetObjectsEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    GoToIfGe VAR_ARC2_PROGRESS, 26, EternaForest_Arc2SetObjectsEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    GoToIfNe VAR_ARC2_PROGRESS, 22, EternaForest_Arc2SetObjectsEnd
    GoToIfSet FLAG_ARC2_FLOAROMA_SILENCE_SEEN, EternaForest_Arc2SetObjectsEnd
    SetVar VAR_MAP_LOCAL_0x01, 1
EternaForest_Arc2SetObjectsEnd:
    Return

// Frame table, first entry at 22: the silence.
EternaForest_Arc2Silence:
    LockAll
    SetVar VAR_MAP_LOCAL_0x01, 0
    SetFlag FLAG_ARC2_FLOAROMA_SILENCE_SEEN
    WaitTime 20, VAR_RESULT
    Message EternaForest_Text_Arc2Silence
    WaitButton
    CloseMessage
    ReleaseAll
    End

EternaForest_Arc2Ruth:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Call EternaForest_Arc2RuthLine
    ReleaseAll
    End

EternaForest_Arc2RuthLine:
    Message EternaForest_Text_Arc2RuthSameSignature
    WaitButton
    CloseMessage
    CallIfEq VAR_ARC2_PROGRESS, 22, EternaForest_Arc2SetRiftSeen
    Return

EternaForest_Arc2SetRiftSeen:
    SetVar VAR_ARC2_PROGRESS, 23
    Return

EternaForest_Arc2Cyrus:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message EternaForest_Text_Arc2CyrusEllipsis
    WaitButton
    CloseMessage
    ReleaseAll
    End

// The rift (22-25). At 22 Ruth speaks first (sets 23). Entering sets 24 and warps into the DW map's entry.
EternaForest_Arc2Rift:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    CallIfEq VAR_ARC2_PROGRESS, 22, EternaForest_Arc2RuthLine
    Message EternaForest_Text_Arc2RiftStepInside
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, EternaForest_Arc2RiftStayOut
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA_sseq
    FadeScreenOut
    WaitFadeScreen
    DoDWWarp
    ReturnToField
    SetVar VAR_ARC2_PROGRESS, 24
    Warp MAP_HEADER_DW_ETERNA_FOREST, 20, 12, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    End

EternaForest_Arc2RiftStayOut:
    CloseMessage
    ReleaseAll
    End

// Frame table at 26: back from the DW at (84,37) facing south, the rift gone. Ruth checks the Resonator.
EternaForest_Arc2Aftermath:
    LockAll
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_ARC2_RUTH, EternaForest_Movement_Arc2RuthToPlayer
    WaitMovement
    ApplyMovement LOCALID_PLAYER, EternaForest_Movement_Arc2FaceEast
    WaitMovement
    Message EternaForest_Text_Arc2RuthWontAnswer
    WaitButton
    CloseMessage
    WaitTime 15, VAR_RESULT
    Message EternaForest_Text_Arc2RuthGardenia
    WaitButton
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 29
    // Ruth and Cyrus walk on toward Eterna (the east exit)
    ApplyMovement LOCALID_ARC2_RUTH, EternaForest_Movement_Arc2RuthLeave
    ApplyMovement LOCALID_ARC2_CYRUS, EternaForest_Movement_Arc2CyrusLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_RUTH
    RemoveObject LOCALID_ARC2_CYRUS
    ReleaseAll
    End

    .balign 4, 0
EternaForest_Movement_Arc2RuthToPlayer:
    EmoteExclamationMark
    WalkNormalNorth 2
    FaceWest
    EndMovement

    .balign 4, 0
EternaForest_Movement_Arc2FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
EternaForest_Movement_Arc2RuthLeave:
    WalkNormalEast
    SetInvisible
    EndMovement

    .balign 4, 0
EternaForest_Movement_Arc2CyrusLeave:
    Delay8 2
    WalkNormalNorth 3
    WalkNormalEast 3
    SetInvisible
    EndMovement
