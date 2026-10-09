#include "macros/scrcmd.inc"
#include "res/text/bank/distortion_world_arc1_seams.h"

// Arc 1 "Distortion World Puzzle 1 - Wall Walk" (Phase 0, cloned from DW B1F; see docs/arc1/revision/spec.md).
// Entry from Lake Verity at (20,12) facing west (state 5). The seam runs on the west wall x=11, z 13-22: step on from
// the jump-on ledge (12,14), pass under the two wall trees along the bottom row, fork at z=19 (a dead-end corner up
// the wall, the way on goes along the bottom), drop off at (12,23) onto the briefcase platform. Falls: coord events on the chasm lips. Cyrus and Barry are DW overlay objects
// (src/overlay009 sArc1SeamsObjects), spawned by VAR_ARC1_DW_HINTS:
//   VAR_ARC1_DW_HINTS  0 nothing shown, 1 seam hint given, 2 fork reached, 3 briefcase reached,
//                      4 starter chosen, 5 Mawile fought
//   VAR_ARC1_DW_FALLS  0 entry scene (Barry's demo fall) not played yet, then 1 + the player's falls

#define LOCALID_CYRUS_ENTRY     0x80
#define LOCALID_BARRY_ENTRY     0x81
#define LOCALID_MAWILE_GLIMPSE  0x82
#define LOCALID_MAWILE          0x83
#define LOCALID_BRIEFCASE       0x84
#define LOCALID_CYRUS_CASE      0x85
#define LOCALID_BARRY_CASE      0x86

#define ENTRY_X 20
#define ENTRY_Z 12

    ScriptEntry DistortionWorldArc1Seams_OnTransition
    ScriptEntry DistortionWorldArc1Seams_Fall
    ScriptEntry DistortionWorldArc1Seams_EntryScene
    ScriptEntry DistortionWorldArc1Seams_SeamHint
    ScriptEntry DistortionWorldArc1Seams_Fork
    ScriptEntry DistortionWorldArc1Seams_Briefcase
    ScriptEntry DistortionWorldArc1Seams_TalkCyrus
    ScriptEntry DistortionWorldArc1Seams_TalkBarry
    ScriptEntryEnd

DistortionWorldArc1Seams_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

// Coord events on the chasm lips (VAR_ARC1_PROGRESS 5): the player drops into the void and the world puts them
// back at the entry. Cyrus's retry line plays once (the first fall); the seam hint follows if not given yet.
DistortionWorldArc1Seams_Fall:
    LockAll
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_PlayerFall
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_SetVisible
    WaitMovement
    ResetDistortionWorldPersistedCameraAngles
    AddVar VAR_ARC1_DW_FALLS, 1
    CallIfGt VAR_ARC1_DW_FALLS, 99, DistortionWorldArc1Seams_CapFalls
    Warp MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS, 0, ENTRY_X, ENTRY_Z, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    CallIfEq VAR_ARC1_DW_FALLS, 2, DistortionWorldArc1Seams_RetryLine
    GoToIfEq VAR_ARC1_DW_HINTS, 0, DistortionWorldArc1Seams_SeamHintLocked
    ReleaseAll
    End

DistortionWorldArc1Seams_CapFalls:
    SetVar VAR_ARC1_DW_FALLS, 99
    Return

DistortionWorldArc1Seams_RetryLine:
    Message DistortionWorldArc1Seams_Text_CyrusBackWhereWeStarted
    WaitABXPadPress
    CloseMessage
    Return

// First frame at state 5: Cyrus's entry line, then Barry's demo fall.
DistortionWorldArc1Seams_EntryScene:
    LockAll
    GoToIfNe VAR_ARC1_PROGRESS, 5, DistortionWorldArc1Seams_EntrySkip
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceEast
    WaitMovement
    Message DistortionWorldArc1Seams_Text_CyrusStayClose
    WaitABXPadPress
    CloseMessage
    BufferRivalName 0
    ApplyMovement LOCALID_BARRY_ENTRY, DistortionWorldArc1Seams_Movement_BarryExcited
    WaitMovement
    Message DistortionWorldArc1Seams_Text_BarryIllJustJumpIt
    CloseMessage
    ApplyMovement LOCALID_BARRY_ENTRY, DistortionWorldArc1Seams_Movement_BarryJump
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_PlayerWatchBarry
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_BARRY_ENTRY
    WaitTime 50, VAR_RESULT
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_311 LOCALID_BARRY_ENTRY
    ApplyMovement LOCALID_BARRY_ENTRY, DistortionWorldArc1Seams_Movement_BarryDazed
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceEast
    WaitMovement
    BufferRivalName 0
    Message DistortionWorldArc1Seams_Text_BarryIMeantToDoThat
    Message DistortionWorldArc1Seams_Text_CyrusTheVoidSendsItBack
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceWest
    WaitMovement
DistortionWorldArc1Seams_EntrySkip:
    SetVar VAR_ARC1_DW_FALLS, 1
    ReleaseAll
    End

// Show, then hint: from the step hook (20 idle steps on the floors) or after a fall.
DistortionWorldArc1Seams_SeamHint:
    GoToIfNe VAR_ARC1_DW_HINTS, 0, DistortionWorldArc1Seams_End
    LockAll
DistortionWorldArc1Seams_SeamHintLocked:
    Message DistortionWorldArc1Seams_Text_CyrusWalkTheSeam
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC1_DW_HINTS, 1
    ReleaseAll
    End

// Step hook at the fork on the wall (x=11, z=19, any row): Cyrus calls out, and the Mawile shows itself on the platform below.
DistortionWorldArc1Seams_Fork:
    GoToIfGe VAR_ARC1_DW_HINTS, 2, DistortionWorldArc1Seams_End
    LockAll
    SetVar VAR_ARC1_DW_HINTS, 2
    Message DistortionWorldArc1Seams_Text_CyrusTheSeamSplits
    WaitABXPadPress
    CloseMessage
    WaitTime 10, VAR_RESULT
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_311 LOCALID_MAWILE_GLIMPSE
    WaitTime 30, VAR_RESULT
    PlayCry SPECIES_MAWILE
    ApplyMovement LOCALID_MAWILE_GLIMPSE, DistortionWorldArc1Seams_Movement_MawileGlimpse
    WaitMovement
    WaitCry
    Message DistortionWorldArc1Seams_Text_SomethingMovedBelow
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_MAWILE_GLIMPSE
    WaitTime 15, VAR_RESULT
    ReleaseAll
    End

DistortionWorldArc1Seams_End:
    End

// Coord event at (14,23) on the briefcase platform (or A on the case).
DistortionWorldArc1Seams_Briefcase:
    GoToIfGe VAR_ARC1_DW_HINTS, 3, DistortionWorldArc1Seams_End
    LockAll
    SetVar VAR_ARC1_DW_HINTS, 3
    // Cyrus folds space: he steps through a rift at the entry and out beside the briefcase, then pulls Barry after
    Message DistortionWorldArc1Seams_Text_CyrusTheWorldFolds
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_CYRUS_ENTRY
    ScrCmd_311 LOCALID_CYRUS_CASE
    WaitTime 20, VAR_RESULT
    BufferRivalName 0
    Message DistortionWorldArc1Seams_Text_BarryHeyWaitUp
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_BARRY_ENTRY
    ScrCmd_311 LOCALID_BARRY_CASE
    WaitTime 20, VAR_RESULT
    BufferRivalName 0
    Message DistortionWorldArc1Seams_Text_BarryHowDidWeDoThat
    WaitABXPadPress
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfLt VAR_0x8004, 15, DistortionWorldArc1Seams_StepToCase
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceEast
    WaitMovement
    Message DistortionWorldArc1Seams_Text_CyrusThereRowansCase
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceSouth
    WaitMovement
    BufferRivalName 0
    Message DistortionWorldArc1Seams_Text_BarryPickOne
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceEast
    WaitMovement
    // Starter select (the block moved here from the Lake Verity terrace)
    FadeScreenOut
    WaitFadeScreen
    StartChooseStarterScene
    SaveChosenStarter
    ReturnToField
    FadeScreenIn
    WaitFadeScreen
    GetPlayerStarterSpecies VAR_0x8000
    GivePokemon VAR_0x8000, 5, ITEM_NONE, VAR_RESULT
    SetVar VAR_ARC1_DW_HINTS, 4
    PlayFanfare SEQ_SE_CONFIRM
    ScrCmd_312 LOCALID_BRIEFCASE
    WaitFanfare SEQ_SE_CONFIRM
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceSouth
    ApplyMovement LOCALID_BARRY_CASE, DistortionWorldArc1Seams_Movement_FaceNorth
    WaitMovement
    BufferRivalName 0
    BufferRivalStarterSpeciesName 2
    Message DistortionWorldArc1Seams_Text_BarryIllTakeThisOne
    WaitABXPadPress
    CloseMessage
    // One Mawile lunges out of the dark
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_311 LOCALID_MAWILE
    ApplyMovement LOCALID_MAWILE, DistortionWorldArc1Seams_Movement_MawileLunge
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_PlayerStartled
    ApplyMovement LOCALID_BARRY_CASE, DistortionWorldArc1Seams_Movement_FaceEast
    ApplyMovement LOCALID_CYRUS_CASE, DistortionWorldArc1Seams_Movement_FaceEast
    WaitMovement
    PlayCry SPECIES_MAWILE
    WaitCry
    StartArc1MawileBattle
    HealParty
    // The Mawile drops a shard and fades into the dark; Cyrus picks it up
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceEast
    WaitMovement
    Message DistortionWorldArc1Seams_Text_MawileDroppedSomething
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_MAWILE
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_CYRUS_CASE, DistortionWorldArc1Seams_Movement_CyrusPickUpShard
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_PlayerWatchCyrus
    WaitMovement
    PlayFanfare SEQ_SE_CONFIRM
    WaitFanfare SEQ_SE_CONFIRM
    Message DistortionWorldArc1Seams_Text_CyrusHarvesting
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC1_DW_HINTS, 5
    SetVar VAR_ARC1_PROGRESS, 6
    // The exit rift opens beside the briefcase spot
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    ApplyMovement LOCALID_CYRUS_CASE, DistortionWorldArc1Seams_Movement_FaceWest
    WaitMovement
    Message DistortionWorldArc1Seams_Text_CyrusTheWorldIsClosing
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    SetVar VAR_ARC1_PROGRESS, 7
    Warp MAP_HEADER_LAKE_VERITY, 0, 32, 31, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

DistortionWorldArc1Seams_StepToCase:
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_PlayerStepToCase
    WaitMovement
    Return

DistortionWorldArc1Seams_TalkCyrus:
    LockAll
    FacePlayer
    GoToIfGe VAR_ARC1_DW_HINTS, 3, DistortionWorldArc1Seams_TalkCyrusCase
    GoToIfGe VAR_ARC1_DW_HINTS, 1, DistortionWorldArc1Seams_TalkCyrusHinted
    Message DistortionWorldArc1Seams_Text_CyrusWatchAndListen
    GoTo DistortionWorldArc1Seams_TalkEnd

DistortionWorldArc1Seams_TalkCyrusHinted:
    Message DistortionWorldArc1Seams_Text_CyrusTheWallWillHoldYou
    GoTo DistortionWorldArc1Seams_TalkEnd

DistortionWorldArc1Seams_TalkCyrusCase:
    Message DistortionWorldArc1Seams_Text_CyrusStayNearMe
    GoTo DistortionWorldArc1Seams_TalkEnd

DistortionWorldArc1Seams_TalkBarry:
    LockAll
    FacePlayer
    BufferRivalName 0
    Message DistortionWorldArc1Seams_Text_BarryHurryUp
DistortionWorldArc1Seams_TalkEnd:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
DistortionWorldArc1Seams_Movement_PlayerFall:
    JumpOnSpotFastSouth
    SetInvisible
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_SetVisible:
    SetVisible
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_BarryExcited:
    FaceSouth
    JumpOnSpotFastSouth 2
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_BarryJump:
    WalkFastSouth
    JumpFarSouth
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_PlayerWatchBarry:
    Delay8
    FaceSouth
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_BarryDazed:
    FaceWest
    Delay8
    FaceNorth
    Delay8
    FaceWest
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_MawileGlimpse:
    FaceWest
    Delay16
    FaceNorth
    Delay16
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_PlayerStepToCase:
    WalkNormalEast
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_MawileLunge:
    FaceWest
    JumpOnSpotFastWest
    WalkFastWest
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_PlayerStartled:
    FaceEast
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_CyrusPickUpShard:
    WalkNormalEast
    FaceSouth
    Delay16
    FaceWest
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_PlayerWatchCyrus:
    Delay16
    FaceNorth
    EndMovement
