#include "macros/scrcmd.inc"
#include "res/text/bank/verity_lakefront.h"


    ScriptEntry VerityLakefront_OnLoad
    ScriptEntry VerityLakefront_OnTransition
    ScriptEntry VerityLakefront_TriggerWereAtTheLake
    ScriptEntry VerityLakefront_TrainerTipsSignpost
    ScriptEntryEnd

// The castle map (MAP_HEADER_LAKE_VERITY) is used for every visit, so the stock story switch
// (MAP_HEADER_LAKE_VERITY_LOW_WATER until Saturn is defeated in Valor Cavern) is gone: warps 0 and 1
// (stock LOW_WATER pair) are always moved away and warps 2 and 3 (LAKE_VERITY pair) are always used.
VerityLakefront_OnLoad:
    GoTo VerityLakefront_SetWarpsLakeVerity
    End

VerityLakefront_SetWarpsLakeVerity:
    SetWarpEventPos 1, 80, 0x348
    SetWarpEventPos 0, 81, 0x348
    End

VerityLakefront_OnTransition:
    GoTo VerityLakefront_SetWarpsLakeVerity
    End

VerityLakefront_TriggerWereAtTheLake:
    LockAll
    ApplyMovement LOCALID_FOLLOWER, VerityLakefront_Movement_RivalWalkOnSpotNorth
    ApplyMovement LOCALID_PLAYER, VerityLakefront_Movement_PlayerFaceRival
    WaitMovement
    BufferRivalName 0
    Message VerityLakefront_Text_WereAtTheLake
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfInRange VAR_0x8004, 80, 85, VerityLakefront_WalkToLakeValor
    End

VerityLakefront_WalkToLakeValor:
    ApplyMovement LOCALID_PLAYER, VerityLakefront_Movement_PlayerEnterLakeValor
    ApplyMovement LOCALID_FOLLOWER, VerityLakefront_Movement_RivalEnterLakeValor
    WaitMovement
    GoTo VerityLakefront_WarpToLakeValor

VerityLakefront_WarpToLakeValor:
    SetVar VAR_UNK_0x4082, 1
    ReleaseAll
    PlayFanfare SEQ_SE_DP_KAIDAN2
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_LAKE_VERITY, 0, 46, 54, 0
    FadeScreenIn
    WaitFadeScreen
    End

    .balign 4, 0
VerityLakefront_Movement_RivalWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
VerityLakefront_Movement_RivalEnterLakeValor:
    WalkNormalNorth 2
    SetInvisible
    EndMovement

    .balign 4, 0
VerityLakefront_Movement_PlayerEnterLakeValor:
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
