#include "macros/scrcmd.inc"
#include "res/text/bank/route_215.h"
#include "res/field/maps/locals/route_215.h"


    ScriptEntry Route215_Dummy1
    ScriptEntry Route215_BlackBelt
    ScriptEntry Route215_ArrowSignpostWest
    ScriptEntry Route215_ArrowSignpostVeilstoneCity
    ScriptEntry Route215_JoggerScott
    ScriptEntry Route215_JoggerCraig
    ScriptEntry Route215_OnTransition
    ScriptEntry Route215_TrainerTipsSignpost
    ScriptEntry Route215_Arc2Crate
    ScriptEntry Route215_Arc2CrateSign
    ScriptEntry Route215_Arc2CyrusTalk
    ScriptEntryEnd

Route215_OnTransition:
    Call Route215_Arc2OnTransition
    GetTimeOfDay VAR_MAP_LOCAL_0x00
    GoToIfEq VAR_MAP_LOCAL_0x00, TIMEOFDAY_MORNING, Route215_SetJoggersBattle
    GoToIfInRange VAR_MAP_LOCAL_0x00, TIMEOFDAY_DAY, TIMEOFDAY_LATE_NIGHT, Route215_SetJoggersNoBattle
    End

Route215_SetJoggersBattle:
    ClearFlag FLAG_HIDE_ROUTE_215_JOGGER_SCOTT
    ClearFlag FLAG_HIDE_ROUTE_215_JOGGER_CRAIG
    SetFlag FLAG_HIDE_ROUTE_215_JOGGER_SCOTT_NO_BATTLE
    SetFlag FLAG_HIDE_ROUTE_215_JOGGER_CRAIG_NO_BATTLE
    End

Route215_SetJoggersNoBattle:
    ClearFlag FLAG_HIDE_ROUTE_215_JOGGER_SCOTT_NO_BATTLE
    ClearFlag FLAG_HIDE_ROUTE_215_JOGGER_CRAIG_NO_BATTLE
    SetFlag FLAG_HIDE_ROUTE_215_JOGGER_SCOTT
    SetFlag FLAG_HIDE_ROUTE_215_JOGGER_CRAIG
    End

Route215_Dummy1:
    NPCMessage Route215_Text_Dummy0
    End

Route215_BlackBelt:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_RECEIVED_ROUTE_215_TM66, Route215_PaybackIsHarsh
    Message Route215_Text_YupItsPayback
    SetVar VAR_0x8004, ITEM_TM66
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, Route215_BagIsFull
    CallCommonScript CommonScript_AddItemQuantity
    SetFlag FLAG_RECEIVED_ROUTE_215_TM66
    GoTo Route215_PaybackIsHarsh

Route215_PaybackIsHarsh:
    Message Route215_Text_PaybackIsHarsh
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route215_BagIsFull:
    CallCommonScript CommonScript_BagIsFull
    CloseMessage
    ReleaseAll
    End

Route215_ArrowSignpostWest:
    ShowArrowSign Route215_Text_SignCelesticTownSolaceonTown
    End

Route215_ArrowSignpostVeilstoneCity:
    ShowArrowSign Route215_Text_SignVeilstoneCity
    End

Route215_TrainerTipsSignpost:
    ShowScrollingSign Route215_Text_TrainerTipsPhysicalSpecial
    End

Route215_JoggerScott:
    NPCMessage Route215_Text_DontOverdoIt
    End

Route215_JoggerCraig:
    NPCMessage Route215_Text_ImOnlyHuman
    End

    .balign 4, 0

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 2, workstream s-veilstone: 2.17c, the opened crate (optional, night, VAR_ARC2_PROGRESS
// 49-59). Cyrus crouches by a pried-open Eclipse crate beside the path near the Veilstone gate (663-664, 595);
// a Buneary bolts off into the rocks as the player comes near (coord columns x667 from the gate, x659 from the west).
// (East of Ace Trainers Dennis and Maya, whose x648 sight line would otherwise start a battle mid-scene.)
// Seeing it adds 8 to VAR_ARC2_CHOICES (bit 3), once: FLAG_ARC2_VEILSTONE_B (0x0947). The empty crate stays
// (49-59) after that, any time of day.
// Map-local: hide flags 0x0030 Cyrus, 0x0031 crate, 0x0032 Buneary; VAR_MAP_LOCAL_0x01 = 1 arms the coords,
// VAR_MAP_LOCAL_0x02 time of day (scratch).

Route215_Arc2OnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    SetVar VAR_MAP_LOCAL_0x01, 0
    GoToIfLt VAR_ARC2_PROGRESS, 49, Route215_Arc2OnTransitionEnd
    GoToIfGt VAR_ARC2_PROGRESS, 59, Route215_Arc2OnTransitionEnd
    GoToIfSet FLAG_ARC2_VEILSTONE_B, Route215_Arc2ShowCrateOnly
    GetTimeOfDay VAR_MAP_LOCAL_0x02
    GoToIfLt VAR_MAP_LOCAL_0x02, 3, Route215_Arc2OnTransitionEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    SetVar VAR_MAP_LOCAL_0x01, 1
    Return

Route215_Arc2ShowCrateOnly:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
Route215_Arc2OnTransitionEnd:
    Return

Route215_Arc2CyrusTalk:
    PlaySE SE_CONFIRM_sseq_3
    GoTo Route215_Arc2Crate
    End

Route215_Arc2Crate:
    LockAll
    SetVar VAR_MAP_LOCAL_0x01, 0
    // The Buneary bolts out of the crate into the grass
    ApplyMovement LOCALID_ARC2_BUNEARY, Route215_Arc2Movement_BunearyBolt
    WaitMovement
    RemoveObject LOCALID_ARC2_BUNEARY
    ApplyMovement LOCALID_ARC2_CYRUS, Route215_Arc2Movement_CyrusStands
    WaitMovement
    // He turns to the player
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfGe VAR_0x8004, 664, Route215_Arc2CyrusFaceEast
    CallIfLt VAR_0x8004, 664, Route215_Arc2CyrusFaceWest
    Message Route215_Text_Arc2CyrusDots
    WaitABPadPress
    Message Route215_Text_Arc2CyrusExplain
    WaitABPadPress
    CloseMessage
    // He walks off into the dark, away from the player
    CallIfGe VAR_0x8004, 664, Route215_Arc2CyrusLeaveWest
    CallIfLt VAR_0x8004, 664, Route215_Arc2CyrusLeaveEast
    RemoveObject LOCALID_ARC2_CYRUS
    GoToIfSet FLAG_ARC2_VEILSTONE_B, Route215_Arc2CrateDone
    SetFlag FLAG_ARC2_VEILSTONE_B
    AddVar VAR_ARC2_CHOICES, 8
Route215_Arc2CrateDone:
    ReleaseAll
    End

Route215_Arc2CyrusFaceEast:
    ApplyMovement LOCALID_ARC2_CYRUS, Route215_Arc2Movement_FaceEast
    WaitMovement
    Return

Route215_Arc2CyrusFaceWest:
    ApplyMovement LOCALID_ARC2_CYRUS, Route215_Arc2Movement_FaceWest
    WaitMovement
    Return

Route215_Arc2CyrusLeaveWest:
    ApplyMovement LOCALID_ARC2_CYRUS, Route215_Arc2Movement_LeaveWest
    WaitMovement
    Return

Route215_Arc2CyrusLeaveEast:
    ApplyMovement LOCALID_ARC2_CYRUS, Route215_Arc2Movement_LeaveEast
    WaitMovement
    Return

Route215_Arc2CrateSign:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message Route215_Text_Arc2CrateEmpty
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
Route215_Arc2Movement_BunearyBolt:
    WalkFastWest
    WalkFastNorth
    EndMovement

    .balign 4, 0
Route215_Arc2Movement_CyrusStands:
    EmoteExclamationMark
    Delay8
    EndMovement

    .balign 4, 0
Route215_Arc2Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
Route215_Arc2Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
Route215_Arc2Movement_LeaveWest:
    WalkNormalSouth 2
    WalkNormalWest 7
    EndMovement

    .balign 4, 0
Route215_Arc2Movement_LeaveEast:
    WalkNormalEast 2
    WalkNormalSouth 3
    WalkNormalEast 4
    EndMovement
