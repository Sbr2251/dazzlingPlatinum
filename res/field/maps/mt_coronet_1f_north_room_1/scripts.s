#include "macros/scrcmd.inc"
#include "res/text/bank/mt_coronet_1f_north_room_1.h"
#include "res/field/maps/locals/mt_coronet_1f_north_room_1.h"


    ScriptEntry MtCoronet1FNorthRoom1_GruntF
    ScriptEntry MtCoronet1FNorthRoom1_GruntM
    ScriptEntry MtCoronet1FNorthRoom1_Arc2Scene
    ScriptEntry MtCoronet1FNorthRoom1_Arc2Grate
    ScriptEntry MtCoronet1FNorthRoom1_OnTransition
    ScriptEntryEnd

MtCoronet1FNorthRoom1_GruntF:
    NPCMessage MtCoronet1FNorthRoom1_Text_NoWayToPeakFromThisSide
    End

MtCoronet1FNorthRoom1_GruntM:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    ApplyMovement LOCALID_GRUNT_M_1, MtCoronet1FNorthRoom1_Movement_GruntM1WalkOnSpotSouth
    WaitMovement
    Message MtCoronet1FNorthRoom1_Text_FogIsSoThick
    ApplyMovement LOCALID_GRUNT_M_2, MtCoronet1FNorthRoom1_Movement_GruntM2WalkOnSpotNorth
    WaitMovement
    Message MtCoronet1FNorthRoom1_Text_MyPokemonCantUseDefog
    CloseMessage
    ApplyMovement LOCALID_GRUNT_M_1, MtCoronet1FNorthRoom1_Movement_GruntMWalkOnSpotWest
    ApplyMovement LOCALID_GRUNT_M_2, MtCoronet1FNorthRoom1_Movement_GruntMWalkOnSpotWest
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
MtCoronet1FNorthRoom1_Movement_GruntM1WalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
MtCoronet1FNorthRoom1_Movement_GruntM2WalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
MtCoronet1FNorthRoom1_Movement_GruntMWalkOnSpotWest:
    WalkOnSpotNormalWest
    EndMovement

MtCoronet1FNorthRoom1_OnTransition:
    // Stock Galactic grunts by the B1F stairs (14,10)/(14,11): their stock hide flag is set at Lake Verity,
    // which Arc 1 no longer does, so they stay hidden here.
    SetFlag FLAG_HIDE_MT_CORONET_1F_NORTH_ROOM_1_GRUNTS_M
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    GoToIfEq VAR_ARC2_PROGRESS, 39, MtCoronet1FNorthRoom1_OnTransitionEnd
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
MtCoronet1FNorthRoom1_OnTransitionEnd:
    End

MtCoronet1FNorthRoom1_Arc2Grate:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message MtCoronet1FNorthRoom1_Text_Arc2Grate
    WaitButton
    CloseMessage
    ReleaseAll
    End

// 2.14: runs from the frame table as soon as the player comes in from Route 211 West at state 39.
MtCoronet1FNorthRoom1_Arc2Scene:
    LockAll
    ApplyMovement LOCALID_PLAYER, MtCoronet1FNorthRoom1_Arc2Movement_FaceEast
    ApplyMovement LOCALID_ARC2_RUTH, MtCoronet1FNorthRoom1_Arc2Movement_FaceWest
    WaitMovement
    Message MtCoronet1FNorthRoom1_Text_Arc2RuthHot
    ApplyMovement LOCALID_ARC2_GARIUS, MtCoronet1FNorthRoom1_Arc2Movement_FaceNorth
    WaitMovement
    BufferRivalName 0
    Message MtCoronet1FNorthRoom1_Text_Arc2GariusBroken
    CloseMessage
    ApplyMovement LOCALID_ARC2_CYRUS, MtCoronet1FNorthRoom1_Arc2Movement_FaceEast
    WaitMovement
    WaitTime 60, VAR_RESULT
    ApplyMovement LOCALID_ARC2_RUTH, MtCoronet1FNorthRoom1_Arc2Movement_FaceEast
    WaitMovement
    Message MtCoronet1FNorthRoom1_Text_Arc2RuthCyrus
    ApplyMovement LOCALID_ARC2_CYRUS, MtCoronet1FNorthRoom1_Arc2Movement_FaceWest
    WaitMovement
    Message MtCoronet1FNorthRoom1_Text_Arc2CyrusNothing
    CloseMessage
    ApplyMovement LOCALID_ARC2_RUTH, MtCoronet1FNorthRoom1_Arc2Movement_WalkAway
    ApplyMovement LOCALID_ARC2_CYRUS, MtCoronet1FNorthRoom1_Arc2Movement_WalkAway
    WaitMovement
    // Only the player sees it: something violet-black, deep under the grate, for a moment.
    ApplyMovement LOCALID_PLAYER, MtCoronet1FNorthRoom1_Arc2Movement_FaceSouth
    WaitMovement
    WaitTime 20, VAR_RESULT
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    AddObject LOCALID_ARC2_GRATE_FLASH
    WaitTime 4, VAR_RESULT
    RemoveObject LOCALID_ARC2_GRATE_FLASH
    WaitTime 30, VAR_RESULT
    SetVar VAR_ARC2_PROGRESS, 40
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_ARC2_RUTH
    RemoveObject LOCALID_ARC2_CYRUS
    RemoveObject LOCALID_ARC2_GARIUS
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
MtCoronet1FNorthRoom1_Arc2Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
MtCoronet1FNorthRoom1_Arc2Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
MtCoronet1FNorthRoom1_Arc2Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
MtCoronet1FNorthRoom1_Arc2Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
MtCoronet1FNorthRoom1_Arc2Movement_WalkAway:
    WalkNormalNorth
    EndMovement

