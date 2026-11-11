#include "macros/scrcmd.inc"
#include "res/field/maps/locals/ravaged_path.h"
#include "res/text/bank/route_204_south.h"
#include "res/text/bank/arc2_common.h"
#include "generated/text_banks.h"


#define RAVAGED_PATH_RUTH    LOCALID_ARC2_RUTH
#define RAVAGED_PATH_CYRUS   LOCALID_ARC2_CYRUS
#define RAVAGED_PATH_GRUNT_M LOCALID_ARC2_GRUNT_M
#define RAVAGED_PATH_GRUNT_F LOCALID_ARC2_GRUNT_F
#define RAVAGED_PATH_RIFT    LOCALID_ARC2_RIFT
#define FLAG_ARC2_ECHO_RAVAGED_PATH FLAG_ARC1_SPARE_A
#define RAVAGED_PATH_ECHO_CRATE     LOCALID_ECHO_GHOST_CRATE
#define RAVAGED_PATH_ECHO_GRUNT_M   LOCALID_ECHO_GHOST_GRUNT_M
#define RAVAGED_PATH_ECHO_GRUNT_F   LOCALID_ECHO_GHOST_GRUNT_F
#define RAVAGED_PATH_ECHO_HITMONLEE LOCALID_ECHO_GHOST_HITMONLEE
#define RAVAGED_PATH_ECHO_TEAR      LOCALID_ECHO_GHOST_TEAR
#define RAVAGED_PATH_ECHO_OPACITY   18

    ScriptEntry RavagedPath_OnTransitionStock
    ScriptEntry RavagedPath_OnTransition
    ScriptEntry RavagedPath_Arc2Ruth
    ScriptEntry RavagedPath_Arc2Cyrus
    ScriptEntry RavagedPath_Arc2Grunt
    ScriptEntry RavagedPath_Arc2Rift
    ScriptEntry RavagedPath_Arc2Frame
    ScriptEntry RavagedPath_Arc2SceneL0
    ScriptEntry RavagedPath_Arc2OnFrameBack
    ScriptEntryEnd

RavagedPath_OnTransitionStock:
    SetFlag FLAG_FIRST_ARRIVAL_RAVAGED_PATH
    End

RavagedPath_Unused:
    End

    .balign 4, 0

RavagedPath_OnTransition:
    SetFlag FLAG_FIRST_ARRIVAL_RAVAGED_PATH
    SetFlag FLAG_MAP_LOCAL_0x18
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_28
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_29
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_30
    SetFlag FLAG_MAP_LOCAL_0x3E
    SetFlag FLAG_MAP_LOCAL_0x3F
    GoToIfLt VAR_ARC2_PROGRESS, 9, RavagedPath_OnTransitionEnd
    ClearFlag FLAG_MAP_LOCAL_0x3F
    GoToIfGe VAR_ARC2_PROGRESS, 16, RavagedPath_OnTransitionEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_28
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_29
    GoToIfEq VAR_ARC2_PROGRESS, 15, RavagedPath_OnTransitionBack
    ClearFlag FLAG_MAP_LOCAL_0x3E
    GoToIfGe VAR_ARC2_PROGRESS, 11, RavagedPath_OnTransitionRiftOpen
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_30
    End

RavagedPath_OnTransitionRiftOpen:
    SetObjectEventPos RAVAGED_PATH_CYRUS, 20, 46
    SetObjectEventDir RAVAGED_PATH_CYRUS, DIR_NORTH
    SetObjectEventMovementType RAVAGED_PATH_CYRUS, MOVEMENT_TYPE_LOOK_NORTH
    End

RavagedPath_OnTransitionBack:
    SetObjectEventPos RAVAGED_PATH_CYRUS, 18, 46
    SetObjectEventDir RAVAGED_PATH_CYRUS, DIR_SOUTH
    SetObjectEventMovementType RAVAGED_PATH_CYRUS, MOVEMENT_TYPE_LOOK_SOUTH
RavagedPath_OnTransitionEnd:
    End

// ------------------------------------------------------------------------------------------------ talk scripts
RavagedPath_Arc2Ruth:
    GoToIfLt VAR_ARC2_PROGRESS, 11, RavagedPath_Arc2SceneL0
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message RavagedPath_Text_Arc2RuthWatch
    WaitButton
    CloseMessage
    ReleaseAll
    End

RavagedPath_Arc2Cyrus:
    GoToIfLt VAR_ARC2_PROGRESS, 11, RavagedPath_Arc2SceneL0
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message RavagedPath_Text_Arc2CyrusGoThrough
    WaitButton
    CloseMessage
    ReleaseAll
    End

RavagedPath_Arc2Grunt:
    GoTo RavagedPath_Arc2SceneL0
    End

// The rift (19,45) and the frame (20,45) sit at the top of the stairs (height 5) and are faced from the stairs
// (height 3): object talk needs equal heights, so each also has a bg event on its tile (facing north) that runs
// the same script. Both scripts check the state themselves.
RavagedPath_Arc2Frame:
    GoToIfLt VAR_ARC2_PROGRESS, 9, RavagedPath_End
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message RavagedPath_Text_Arc2Frame
    WaitButton
    CloseMessage
    Call RavagedPath_Echo
    ReleaseAll
    End

// Touching the open rift (13-14): into the Distortion World (rift-a's map). Contract: Warp ..., 0, 20, 12, DIR_WEST.
RavagedPath_Arc2Rift:
    GoToIfLt VAR_ARC2_PROGRESS, 13, RavagedPath_End
    GoToIfGe VAR_ARC2_PROGRESS, 15, RavagedPath_End
    LockAll
    SetVar VAR_ARC2_PROGRESS, 14
    PlayFanfare SEQ_SE_PL_SYUWA_sseq
    FadeScreenOut
    WaitFadeScreen
    DoDWWarp
    ReturnToField
    Warp MAP_HEADER_DW_RAVAGED_PATH, 20, 12, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    End

RavagedPath_End:
    End

// ------------------------------------------------------------------------------------------------ 2.5
// The coord events on row 49 (x 18-20, one step in from the entrance) start it; the player is first walked to
// (19,48), between Ruth (18,48) and Cyrus (20,48).
RavagedPath_Arc2SceneL0:
    LockAll
    SetVar VAR_ARC2_PROGRESS, 10
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8005, 49, RavagedPath_Arc2SceneL0Placed
    GoToIfEq VAR_0x8004, 18, RavagedPath_Arc2SceneL0FromWest
    GoToIfEq VAR_0x8004, 20, RavagedPath_Arc2SceneL0FromEast
    ApplyMovement LOCALID_PLAYER, RavagedPath_Movement_PlayerWalkUp1
    WaitMovement
    GoTo RavagedPath_Arc2SceneL0Placed
    End

RavagedPath_Arc2SceneL0FromWest:
    ApplyMovement LOCALID_PLAYER, RavagedPath_Movement_PlayerInFromWest
    WaitMovement
    GoTo RavagedPath_Arc2SceneL0Placed
    End

RavagedPath_Arc2SceneL0FromEast:
    ApplyMovement LOCALID_PLAYER, RavagedPath_Movement_PlayerInFromEast
    WaitMovement
RavagedPath_Arc2SceneL0Placed:
    ApplyMovement LOCALID_PLAYER, RavagedPath_Movement_FaceWest
    ApplyMovement RAVAGED_PATH_RUTH, RavagedPath_Movement_FaceEast
    WaitMovement
    Message RavagedPath_Text_Arc2RuthReadings
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_PLAYER, RavagedPath_Movement_FaceEast
    ApplyMovement RAVAGED_PATH_CYRUS, RavagedPath_Movement_FaceWest
    WaitMovement
    Message RavagedPath_Text_Arc2CyrusStayClose
    WaitButton
    CloseMessage
    // Player to (19,46) in front of the rift, Cyrus to (20,47)
    ApplyMovement LOCALID_PLAYER, RavagedPath_Movement_PlayerWalkUp2
    ApplyMovement RAVAGED_PATH_CYRUS, RavagedPath_Movement_CyrusWalkUp1
    WaitMovement
    ApplyMovement RAVAGED_PATH_GRUNT_M, RavagedPath_Movement_GruntNotice
    ApplyMovement RAVAGED_PATH_GRUNT_F, RavagedPath_Movement_GruntNotice
    WaitMovement
    Message RavagedPath_Text_Arc2GruntRightOnTime
    WaitButton
    Message RavagedPath_Text_Arc2GruntWalkedOut
    WaitButton
    CloseMessage
RavagedPath_Arc2TagBattle:
    Call RavagedPath_SetCyrusPartner
    StartTagBattle VAR_0x8004, TRAINER_ECLIPSE_GRUNT_ARC2_01, TRAINER_ECLIPSE_GRUNT_ARC2_02
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, RavagedPath_Arc2LostBattle
    SetVar VAR_ARC2_PROGRESS, 12
    Message RavagedPath_Text_Arc2GruntDoesntMatter
    WaitButton
    CloseMessage
    // The grunts run north, deeper in, toward the north exit and Floaroma
    ApplyMovement RAVAGED_PATH_GRUNT_M, RavagedPath_Movement_GruntRunNorth
    ApplyMovement RAVAGED_PATH_GRUNT_F, RavagedPath_Movement_GruntRunNorth
    WaitMovement
    RemoveObject RAVAGED_PATH_GRUNT_M
    RemoveObject RAVAGED_PATH_GRUNT_F
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_30
    WaitTime 15, VAR_RESULT
    // Cyrus steps up to the frame at (20,45)
    ApplyMovement RAVAGED_PATH_CYRUS, RavagedPath_Movement_CyrusToFrame
    WaitMovement
    WaitTime 20, VAR_RESULT
    Message RavagedPath_Text_Arc2CyrusEllipsis
    WaitButton
    CloseMessage
    WaitTime 15, VAR_RESULT
    Message RavagedPath_Text_Arc2CyrusSeenMachine
    WaitButton
    CloseMessage
    // Ruth runs in from the entrance to (18,46)
    ApplyMovement RAVAGED_PATH_RUTH, RavagedPath_Movement_RuthRunIn
    WaitMovement
    ApplyMovement LOCALID_PLAYER, RavagedPath_Movement_FaceWest
    WaitMovement
    Message RavagedPath_Text_Arc2RuthHowDidTheyKnow
    WaitButton
    CloseMessage
    ApplyMovement RAVAGED_PATH_CYRUS, RavagedPath_Movement_FaceWest
    WaitMovement
    Message RavagedPath_Text_Arc2CyrusHowThatLooks
    WaitButton
    CloseMessage
    Call RavagedPath_LedgerL0
    Message RavagedPath_Text_Arc2RuthEyesOpen
    WaitButton
    CloseMessage
    // The rift wakes
    SetVar VAR_ARC2_PROGRESS, 13
    ApplyMovement LOCALID_PLAYER, RavagedPath_Movement_FaceNorth
    ApplyMovement RAVAGED_PATH_CYRUS, RavagedPath_Movement_FaceNorth
    ApplyMovement RAVAGED_PATH_RUTH, RavagedPath_Movement_FaceNorth
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA_sseq
    ShakeCamera 16, 2
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitFanfare
    ApplyMovement RAVAGED_PATH_CYRUS, RavagedPath_Movement_FaceWest
    WaitMovement
    Message RavagedPath_Text_Arc2CyrusGoThrough
    WaitButton
    CloseMessage
    // Ruth goes back to her readings at (18,48); Cyrus waits by the rift at (20,46)
    ApplyMovement RAVAGED_PATH_RUTH, RavagedPath_Movement_RuthBackToReadings
    WaitMovement
    ApplyMovement RAVAGED_PATH_CYRUS, RavagedPath_Movement_FaceNorth
    WaitMovement
    SetObjectEventMovementType RAVAGED_PATH_CYRUS, MOVEMENT_TYPE_LOOK_NORTH
    SetObjectEventMovementType RAVAGED_PATH_RUTH, MOVEMENT_TYPE_LOOK_EAST
    ReleaseAll
    End

// A lost tag battle is no game over (lead hazard: the field must be brought back by the script): back to the
// field, the party is healed, and the grunts go again.
RavagedPath_Arc2LostBattle:
    ReturnToField
    FadeScreenIn FADE_SCREEN_SPEED_MEDIUM
    WaitFadeScreen
    HealParty
    WaitTime 20, VAR_RESULT
    GoTo RavagedPath_Arc2TagBattle
    End

// Cyrus fights with the starter weak to the player's (trainers-story); the id suffix is the PLAYER's starter.
RavagedPath_SetCyrusPartner:
    GetPlayerStarterSpecies VAR_RESULT
    SetVar VAR_0x8004, TRAINER_CYRUS_ARC2_1_CHIMCHAR
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, RavagedPath_Return
    SetVar VAR_0x8004, TRAINER_CYRUS_ARC2_1_PIPLUP
    GoToIfEq VAR_RESULT, SPECIES_PIPLUP, RavagedPath_Return
    SetVar VAR_0x8004, TRAINER_CYRUS_ARC2_1_TURTWIG
RavagedPath_Return:
    Return

// Ledger L0 (screenplay "The suspect ledger"): prompt from arc2_common, 4-way menu, B = Bad luck.
// VAR_ARC2_SUSPECT += pick (0 Cyrus, 1 Garius, 2 Ruth, 3 Bad luck) + 256 (L0 answered). Runs once: skipped if the
// L0 answered bit is already set. One neutral reaction box per pick.
RavagedPath_LedgerL0:
    BufferRivalName 1
    MessageFromBank TEXT_BANK_ARC2_COMMON, Arc2Common_Text_LedgerWhoKnew
    InitLocalTextMenu 31, 9, 0, VAR_RESULT
    SetMenuXOriginToRight
    AddMenuEntryImm RavagedPath_Text_Arc2LedgerCyrus, 0
    AddMenuEntryImm RavagedPath_Text_Arc2LedgerGarius, 1
    AddMenuEntryImm RavagedPath_Text_Arc2LedgerRuth, 2
    AddMenuEntryImm RavagedPath_Text_Arc2LedgerBadLuck, 3
    ShowMenu
    SetVar VAR_0x8008, VAR_RESULT
    GoToIfEq VAR_0x8008, 0, RavagedPath_LedgerL0Cyrus
    GoToIfEq VAR_0x8008, 1, RavagedPath_LedgerL0Garius
    GoToIfEq VAR_0x8008, 2, RavagedPath_LedgerL0Ruth
    GoTo RavagedPath_LedgerL0BadLuck
    End

RavagedPath_LedgerL0Cyrus:
    SetVar VAR_0x8009, 256
    Message RavagedPath_Text_Arc2ReactCyrus
    GoTo RavagedPath_LedgerL0Store
    End

RavagedPath_LedgerL0Garius:
    SetVar VAR_0x8009, 257
    BufferRivalName 1
    Message RavagedPath_Text_Arc2ReactGarius
    GoTo RavagedPath_LedgerL0Store
    End

RavagedPath_LedgerL0Ruth:
    SetVar VAR_0x8009, 258
    Message RavagedPath_Text_Arc2ReactRuth
    GoTo RavagedPath_LedgerL0Store
    End

RavagedPath_LedgerL0BadLuck:
    SetVar VAR_0x8009, 259
    Message RavagedPath_Text_Arc2ReactBadLuck
    GoTo RavagedPath_LedgerL0Store
    End

RavagedPath_LedgerL0Store:
    WaitButton
    CloseMessage
    GoToIfGe VAR_ARC2_SUSPECT, 256, RavagedPath_Return
    AddVar VAR_ARC2_SUSPECT, VAR_0x8009
    Return

// ------------------------------------------------------------------------------------------------ 2.8 (first half)
// Back from the DW at 15: the player at (19,46) facing south, Cyrus at (18,46), Ruth at her readings (18,48).
RavagedPath_Arc2OnFrameBack:
    LockAll
    WaitTime 20, VAR_RESULT
    ApplyMovement RAVAGED_PATH_RUTH, RavagedPath_Movement_ExclamationMark
    WaitMovement
    ApplyMovement RAVAGED_PATH_RUTH, RavagedPath_Movement_RuthRunToPlayer
    WaitMovement
    Message RavagedPath_Text_Arc2RuthReadingsDropped
    WaitButton
    CloseMessage
    WaitTime 15, VAR_RESULT
    Message RavagedPath_Text_Arc2RuthItsClear
    WaitButton
    Message RavagedPath_Text_Arc2RuthOneNight
    WaitButton
    CloseMessage
    RemoveItem ITEM_PORTAL_READER, 1, VAR_RESULT
    BufferPlayerName 0
    Message RavagedPath_Text_Arc2HandedReader
    WaitButton
    CloseMessage
    // One night passes. Morning: Route 204 North, at the boulder (Route 204 North's frame script takes over at 16).
    FadeScreenOut FADE_SCREEN_SPEED_MEDIUM
    WaitFadeScreen
    HealParty
    SetVar VAR_ARC2_PROGRESS, 16
    WaitTime 30, VAR_RESULT
    Warp MAP_HEADER_ROUTE_204_NORTH, 171, 678, DIR_NORTH
    FadeScreenIn FADE_SCREEN_SPEED_MEDIUM
    WaitFadeScreen
    ReleaseAll
    End

// ------------------------------------------------------------------------------------------------ echo (S8)
// Called from the frame script after its line, with the player on the stairs below the frame (20,46) facing north.
RavagedPath_Echo:
    GoToIfGe VAR_ARC2_PROGRESS, 16, RavagedPath_EchoCheck
    Return

RavagedPath_EchoCheck:
    GoToIfUnset FLAG_TOTEM_VESPIQUEN_DEFEATED, RavagedPath_Return
    GoToIfSet FLAG_ARC2_ECHO_RAVAGED_PATH, RavagedPath_Return
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, RavagedPath_Return
    Message RavagedPath_Text_EchoHum
    WaitButton
    CloseMessage
    // The echo starts: a white flash, then the ghosts fade in
    PlayFanfare SEQ_SE_PL_SYUWA_sseq
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    SetVar VAR_MAP_LOCAL_0x05, 1
    ClearFlag FLAG_MAP_LOCAL_0x18
    AddObject RAVAGED_PATH_ECHO_CRATE
    AddObject RAVAGED_PATH_ECHO_GRUNT_M
    AddObject RAVAGED_PATH_ECHO_GRUNT_F
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitFanfare
    Call RavagedPath_EchoFadeIn
    WaitTime 20, VAR_RESULT
    // The crate is pried open
    ApplyMovement RAVAGED_PATH_ECHO_GRUNT_M, RavagedPath_Movement_EchoFaceEast
    ApplyMovement RAVAGED_PATH_ECHO_GRUNT_F, RavagedPath_Movement_EchoFaceWest
    WaitMovement
    PlayFanfare SEQ_SE_DP_BOX03_sseq
    ShakeCamera 4, 1
    WaitFanfare
    Message RavagedPath_Text_EchoCrate
    WaitButton
    CloseMessage
    // The Hitmonlee is hauled out and into the frame (20,45); the grunts close in behind it
    AddObject RAVAGED_PATH_ECHO_HITMONLEE
    WaitTime 10, VAR_RESULT
    ApplyMovement RAVAGED_PATH_ECHO_HITMONLEE, RavagedPath_Movement_EchoHitmonleeToFrame
    ApplyMovement RAVAGED_PATH_ECHO_GRUNT_M, RavagedPath_Movement_EchoGruntMWatch
    ApplyMovement RAVAGED_PATH_ECHO_GRUNT_F, RavagedPath_Movement_EchoGruntFWatch
    WaitMovement
    PlayFanfare SEQ_SE_PL_KUSARI_sseq
    WaitFanfare
    Message RavagedPath_Text_EchoStrapped
    WaitButton
    CloseMessage
    // It fights the straps
    PlayCry SPECIES_HITMONLEE
    ApplyMovement RAVAGED_PATH_ECHO_HITMONLEE, RavagedPath_Movement_EchoKick
    WaitMovement
    WaitCry
    Message RavagedPath_Text_EchoHitmonlee
    WaitButton
    CloseMessage
    // The air tears beside it (the rift's tile)
    AddObject RAVAGED_PATH_ECHO_TEAR
    PlayFanfare SEQ_SE_PL_SYUWA_sseq
    ShakeCamera 16, 2
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitFanfare
    Message RavagedPath_Text_EchoTear
    WaitButton
    CloseMessage
    // It fades; the ghosts go and the opacity is back to 0 before the player moves again
    Call RavagedPath_EchoFadeOut
    RemoveObject RAVAGED_PATH_ECHO_CRATE
    RemoveObject RAVAGED_PATH_ECHO_GRUNT_M
    RemoveObject RAVAGED_PATH_ECHO_GRUNT_F
    RemoveObject RAVAGED_PATH_ECHO_HITMONLEE
    RemoveObject RAVAGED_PATH_ECHO_TEAR
    SetFlag FLAG_MAP_LOCAL_0x18
    SetVar VAR_MAP_LOCAL_0x05, 0
    WaitTime 2, VAR_RESULT
    SetFlag FLAG_ARC2_ECHO_RAVAGED_PATH
    Message RavagedPath_Text_EchoFade
    WaitButton
    CloseMessage
    Return

RavagedPath_EchoFadeIn:
    AddVar VAR_MAP_LOCAL_0x05, 1
    WaitTime 1, VAR_RESULT
    GoToIfLt VAR_MAP_LOCAL_0x05, RAVAGED_PATH_ECHO_OPACITY, RavagedPath_EchoFadeIn
    Return

RavagedPath_EchoFadeOut:
    SubVar VAR_MAP_LOCAL_0x05, 1
    WaitTime 1, VAR_RESULT
    GoToIfGt VAR_MAP_LOCAL_0x05, 1, RavagedPath_EchoFadeOut
    Return

// ------------------------------------------------------------------------------------------------ movements
    .balign 4, 0
RavagedPath_Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
RavagedPath_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
RavagedPath_Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
RavagedPath_Movement_PlayerWalkUp2:
    WalkNormalNorth 2
    EndMovement

    .balign 4, 0
RavagedPath_Movement_PlayerWalkUp1:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
RavagedPath_Movement_PlayerInFromWest:
    WalkNormalEast
    WalkNormalNorth
    EndMovement

    .balign 4, 0
RavagedPath_Movement_PlayerInFromEast:
    WalkNormalWest
    WalkNormalNorth
    EndMovement

    .balign 4, 0
RavagedPath_Movement_CyrusWalkUp1:
    Delay8
    WalkNormalNorth
    FaceNorth
    EndMovement

    .balign 4, 0
RavagedPath_Movement_GruntNotice:
    FaceSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
RavagedPath_Movement_GruntRunNorth:
    FaceNorth
    WalkFastNorth 4
    EndMovement

    .balign 4, 0
RavagedPath_Movement_CyrusToFrame:
    WalkSlowNorth
    FaceNorth
    EndMovement

    .balign 4, 0
RavagedPath_Movement_RuthRunIn:
    WalkFastNorth 2
    FaceEast
    EndMovement

    .balign 4, 0
RavagedPath_Movement_RuthBackToReadings:
    WalkNormalSouth 2
    FaceEast
    EndMovement

    .balign 4, 0
RavagedPath_Movement_ExclamationMark:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
RavagedPath_Movement_RuthRunToPlayer:
    WalkFastEast
    WalkFastNorth
    FaceNorth
    EndMovement

    .balign 4, 0
RavagedPath_Movement_EchoFaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
RavagedPath_Movement_EchoFaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
RavagedPath_Movement_EchoHitmonleeToFrame:
    WalkSlowEast
    WalkSlowSouth
    EndMovement

    .balign 4, 0
RavagedPath_Movement_EchoGruntMWatch:
    Delay16
    Delay8
    FaceSouth
    EndMovement

    .balign 4, 0
RavagedPath_Movement_EchoGruntFWatch:
    Delay16
    Delay8
    FaceSouth
    EndMovement

    .balign 4, 0
RavagedPath_Movement_EchoKick:
    JumpOnSpotFastSouth
    JumpOnSpotFastSouth
    Delay8
    JumpOnSpotFastSouth
    EndMovement
