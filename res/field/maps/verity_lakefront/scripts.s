#include "macros/scrcmd.inc"
#include "res/text/bank/verity_lakefront.h"
#include "res/field/maps/locals/verity_lakefront.h"


    ScriptEntry VerityLakefront_OnLoad
    ScriptEntry VerityLakefront_OnTransition
    ScriptEntry VerityLakefront_CoordEvent_WereAtTheLake
    ScriptEntry VerityLakefront_TrainerTipsSignpost
    ScriptEntryEnd

// The castle map (MAP_HEADER_LAKE_VERITY) is used for every visit, so the stock story switch
// (MAP_HEADER_LAKE_VERITY_LOW_WATER until Saturn is defeated in Valor Cavern) is gone: warps 0 and 1
// (stock LOW_WATER pair) are always moved away and warps 2 and 3 (LAKE_VERITY pair) are always used.
VerityLakefront_SetWarpsLakeVerity:
    GoTo VerityLakefront_RemoveWarpsLakeVerityLowWater

VerityLakefront_OnLoad:
    GoTo VerityLakefront_SetWarpsLakeVerity
    End

VerityLakefront_RemoveWarpsLakeVerityNormal:
    SetWarpEventPos WARP_LAKE_VERITY_1, 80, 840
    SetWarpEventPos WARP_LAKE_VERITY_2, 81, 840
    End

VerityLakefront_RemoveWarpsLakeVerityLowWater:
    SetWarpEventPos WARP_LAKE_VERITY_LOW_WATER_2, 80, 840
    SetWarpEventPos WARP_LAKE_VERITY_LOW_WATER_1, 81, 840
    End

VerityLakefront_OnTransition:
    GoTo VerityLakefront_SetWarpsLakeVerity
    End

VerityLakefront_CoordEvent_WereAtTheLake:
    LockAll
    ApplyMovement LOCALID_FOLLOWER, VerityLakefront_Movement_RivalWalkOnSpotNorth
    ApplyMovement LOCALID_PLAYER, VerityLakefront_Movement_PlayerFaceRival
    WaitMovement
    BufferRivalName 0
    Message VerityLakefront_Text_WereAtTheLake
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfInRange VAR_0x8004, 80, 85, VerityLakefront_WalkToLakeVerity
    End

VerityLakefront_WalkToLakeVerity:
    ApplyMovement LOCALID_PLAYER, VerityLakefront_Movement_PlayerEnterLakeVerity
    ApplyMovement LOCALID_FOLLOWER, VerityLakefront_Movement_RivalEnterLakeVerity
    WaitMovement
    GoTo VerityLakefront_WarpToLakeVerity

VerityLakefront_WarpToLakeVerity:
    SetVar VAR_VERITY_LAKEFRONT_STATE, 1
    ReleaseAll
    PlaySE SEQ_SE_DP_KAIDAN2_sseq
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_LAKE_VERITY_LOW_WATER, 46, 54, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    End

    .balign 4, 0
VerityLakefront_Movement_RivalWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
VerityLakefront_Movement_RivalEnterLakeVerity:
    WalkNormalNorth 2
    SetInvisible
    EndMovement

    .balign 4, 0
VerityLakefront_Movement_PlayerEnterLakeVerity:
    WalkNormalNorth
    SetInvisible
    EndMovement

    .balign 4, 0
VerityLakefront_Movement_PlayerFaceRival:
    WalkOnSpotNormalSouth
    EndMovement

VerityLakefront_TrainerTipsSignpost:
    ShowScrollingSign VerityLakefront_Text_LakeVerityAhead
    End

    .balign 4, 0
