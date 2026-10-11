#include "macros/scrcmd.inc"
#include "generated/text_banks.h"
#include "res/text/bank/route_209_lost_tower_1f.h"
#include "res/field/events/events_route_209_lost_tower_2f.h"

// Dazzling Platinum Arc 2, s-hearthome (2.25-2.26). Lost Tower 2F: the rift into MAP_HEADER_DW_LOST_TOWER, the
// Eclipse grunts at the vein, and Rowan's "...It wasn't him." The stock overworld Spiritomb totem is gone (D15: it
// is fought inside DW_LOST_TOWER). This map has no text bank of its own (its header points at Jubilife's) and no
// init script, so text comes from Lost Tower 1F's bank via MessageFromBank, and the hide flags
// (FLAG_ARC2_HEARTHOME_B rift, _C grunts and crates, _D Rowan) are set by Lost Tower 1F's OnTransition.
// Rift: shown at progress 92-94. 92-93 first visit (rift-b returns the player here, 7,8 facing east);
// 94 second visit (rift-b sets 95 on the Spiritomb calm and exits to Route 209).

    ScriptEntry LostTower2F_Rift
    ScriptEntry LostTower2F_GruntsTrigger
    ScriptEntry LostTower2F_Rowan
    ScriptEntry LostTower2F_Grunt
    ScriptEntryEnd

LostTower2F_Rift:
    LockAll
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    Warp MAP_HEADER_DW_LOST_TOWER, 0, 20, 12, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    End

// Talking to a grunt before the coord trigger fires (e.g. a save made at 93 next to them) runs the same scene.
LostTower2F_Grunt:
    GoTo LostTower2F_GruntsTrigger
    End

// 2.26: progress 93, the player comes down the only corridor (11,7) toward the rift.
LostTower2F_GruntsTrigger:
    LockAll
    ApplyMovement ROUTE_209_LOST_TOWER_2F_ECLIPSE_GRUNT_1, LostTower2F_Movement_GruntNotice
    ApplyMovement ROUTE_209_LOST_TOWER_2F_ECLIPSE_GRUNT_2, LostTower2F_Movement_FaceEast
    WaitMovement
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8005, 7, LostTower2F_PlayerToCorridor
    CallIfEq VAR_0x8004, 10, LostTower2F_PlayerBackEast
    ApplyMovement LOCALID_PLAYER, LostTower2F_Movement_FaceWest
    WaitMovement
    ApplyMovement ROUTE_209_LOST_TOWER_2F_ECLIPSE_GRUNT_1, LostTower2F_Movement_GruntStepUp
    WaitMovement
    MessageFromBank TEXT_BANK_ROUTE_209_LOST_TOWER_1F, LostTower2F_Text_GruntVein
    WaitABXPadPress
    CloseMessage
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_ARC2_13
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, LostTower2F_LostBattle
    ApplyMovement ROUTE_209_LOST_TOWER_2F_ECLIPSE_GRUNT_2, LostTower2F_Movement_GruntStepUp
    WaitMovement
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_ARC2_14
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, LostTower2F_LostBattle
    // They flee downstairs: the player steps aside into the alcove south of the corridor.
    ApplyMovement LOCALID_PLAYER, LostTower2F_Movement_PlayerStepAside
    WaitMovement
    ApplyMovement ROUTE_209_LOST_TOWER_2F_ECLIPSE_GRUNT_1, LostTower2F_Movement_Grunt1Flee
    ApplyMovement ROUTE_209_LOST_TOWER_2F_ECLIPSE_GRUNT_2, LostTower2F_Movement_Grunt2Flee
    WaitMovement
    PlayFanfare SEQ_SE_DP_KAIDAN2
    RemoveObject ROUTE_209_LOST_TOWER_2F_ECLIPSE_GRUNT_1
    RemoveObject ROUTE_209_LOST_TOWER_2F_ECLIPSE_GRUNT_2
    WaitFanfare SEQ_SE_DP_KAIDAN2
    SetVar VAR_ARC2_PROGRESS, 94
    WaitTime 30, VAR_RESULT
    // Rowan runs up the stairs, out of breath.
    PlayFanfare SEQ_SE_DP_KAIDAN2
    ClearFlag FLAG_ARC2_HEARTHOME_D
    SetObjectEventPos ROUTE_209_LOST_TOWER_2F_ROWAN, 11, 4
    AddObject ROUTE_209_LOST_TOWER_2F_ROWAN
    WaitFanfare SEQ_SE_DP_KAIDAN2
    ApplyMovement ROUTE_209_LOST_TOWER_2F_ROWAN, LostTower2F_Movement_RowanRunsIn
    WaitMovement
    ApplyMovement LOCALID_PLAYER, LostTower2F_Movement_PlayerToRowan
    WaitMovement
    MessageFromBank TEXT_BANK_ROUTE_209_LOST_TOWER_1F, LostTower2F_Text_RowanFast
    WaitABXPadPress
    MessageFromBank TEXT_BANK_ROUTE_209_LOST_TOWER_1F, LostTower2F_Text_RowanOnlyThree
    WaitABXPadPress
    CloseMessage
    ApplyMovement ROUTE_209_LOST_TOWER_2F_ROWAN, LostTower2F_Movement_RowanRealizes
    WaitMovement
    MessageFromBank TEXT_BANK_ROUTE_209_LOST_TOWER_1F, LostTower2F_Text_RowanWasntHim
    WaitABXPadPress
    CloseMessage
    WaitTime 20, VAR_RESULT
    MessageFromBank TEXT_BANK_ROUTE_209_LOST_TOWER_1F, LostTower2F_Text_RowanGo
    WaitABXPadPress
    CloseMessage
    ApplyMovement ROUTE_209_LOST_TOWER_2F_ROWAN, LostTower2F_Movement_RowanStepsAside
    WaitMovement
    ReleaseAll
    End

LostTower2F_PlayerToCorridor:
    ApplyMovement LOCALID_PLAYER, LostTower2F_Movement_WalkSouth
    WaitMovement
    Return

LostTower2F_PlayerBackEast:
    ApplyMovement LOCALID_PLAYER, LostTower2F_Movement_StepBackEast
    WaitMovement
    Return

LostTower2F_LostBattle:
    BlackOutFromBattle
    ReleaseAll
    End

LostTower2F_Rowan:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    MessageFromBank TEXT_BANK_ROUTE_209_LOST_TOWER_1F, LostTower2F_Text_RowanGo
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
LostTower2F_Movement_GruntNotice:
    FaceEast
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
LostTower2F_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
LostTower2F_Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
LostTower2F_Movement_WalkSouth:
    WalkNormalSouth
    EndMovement

    .balign 4, 0
LostTower2F_Movement_StepBackEast:
    FaceWest
    WalkNormalEast
    EndMovement

    .balign 4, 0
LostTower2F_Movement_GruntStepUp:
    WalkNormalEast
    EndMovement

    .balign 4, 0
LostTower2F_Movement_PlayerStepAside:
    WalkNormalSouth
    FaceNorth
    EndMovement

    .balign 4, 0
LostTower2F_Movement_Grunt1Flee:
    WalkFastEast
    WalkFastNorth 4
    EndMovement

    .balign 4, 0
LostTower2F_Movement_Grunt2Flee:
    Delay8
    WalkFastEast 2
    WalkFastNorth 4
    EndMovement

    .balign 4, 0
LostTower2F_Movement_RowanRunsIn:
    WalkFastSouth 3
    WalkOnSpotFastSouth 2
    EndMovement

    .balign 4, 0
LostTower2F_Movement_PlayerToRowan:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
LostTower2F_Movement_RowanRealizes:
    Delay16
    FaceWest
    Delay16 2
    FaceSouth
    EndMovement

    .balign 4, 0
LostTower2F_Movement_RowanStepsAside:
    WalkNormalNorth
    WalkNormalEast
    FaceSouth
    EndMovement
