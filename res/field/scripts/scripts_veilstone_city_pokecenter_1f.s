#include "macros/scrcmd.inc"
#include "res/text/bank/veilstone_city_pokecenter_1f.h"
#include "res/field/events/events_veilstone_city_pokecenter_1f.h"


    ScriptEntry _000E
    ScriptEntry _001A
    ScriptEntry _0032
    ScriptEntry VeilstonePC_Arc2Ruth
    ScriptEntry VeilstonePC_Arc2Cyrus
    ScriptEntry VeilstonePC_Arc2DawnPlan
    ScriptEntryEnd

_000E:
    CallPokecenterNurse 0
    End

_001A:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    BufferTMHMMoveName 0, ITEM_HM03
    Message 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0032:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 2, workstream s-veilstone: 2.17d, the dawn plan (VAR_ARC2_PROGRESS reads 57, sets 59).
// Evening: Ruth and Cyrus at the table; Garius heals, passes through and turns down Route 214. Fade, heal,
// morning, and the three head out (s-route214's 2.18 has Ruth and Cyrus come up behind the player at 59).
// The scene runs from the init frame table (VAR_ARC2_PROGRESS == 57; it ends at 59). The map keeps its stock
// OnTransition (the daily-trainers script 10400), so the hide flags are persistent and set in Veilstone City:
//   FLAG_ARC2_VEILSTONE_C (0x0948) Ruth + Cyrus hidden (clear only at 57)
//   FLAG_ARC2_VEILSTONE_D (0x0949) Garius hidden (shown only during the scene)
// Ruth uses the D1 placeholder sprite (OBJ_EVENT_GFX_DP_PLAYER_F) directly.
// The stock HM03 line of the school kid is kept (Surf is still Gym 4's badge).

VeilstonePC_Arc2Ruth:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message VeilstonePC_Text_Arc2RuthTalk
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

VeilstonePC_Arc2Cyrus:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message VeilstonePC_Text_Arc2CyrusTalk
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// The player came in at the door (8,12): walk to the table, below Ruth
VeilstonePC_Arc2DawnPlan:
    LockAll
    ApplyMovement LOCALID_PLAYER, VeilstonePC_Arc2Movement_PlayerToTable
    WaitMovement
    ApplyMovement LOCALID_ARC2_RUTH, VeilstonePC_Arc2Movement_FaceSouth
    ApplyMovement LOCALID_ARC2_CYRUS, VeilstonePC_Arc2Movement_FaceSouth
    WaitMovement
    Message VeilstonePC_Text_Arc2RuthDawn
    WaitABXPadPress
    CloseMessage
    // Garius comes in, heals at the counter, and walks past the table
    ClearFlag FLAG_ARC2_VEILSTONE_D
    AddObject LOCALID_ARC2_GARIUS
    ApplyMovement LOCALID_ARC2_GARIUS, VeilstonePC_Arc2Movement_GariusToCounter
    WaitMovement
    PlaySound SEQ_ASA
    WaitSound
    ApplyMovement LOCALID_ARC2_GARIUS, VeilstonePC_Arc2Movement_GariusPastTable
    ApplyMovement LOCALID_ARC2_RUTH, VeilstonePC_Arc2Movement_FaceWest
    ApplyMovement LOCALID_PLAYER, VeilstonePC_Arc2Movement_FaceWest
    WaitMovement
    BufferRivalName 0
    Message VeilstonePC_Text_Arc2GariusPassing
    WaitABXPadPress
    BufferRivalName 0
    Message VeilstonePC_Text_Arc2RuthInvite
    WaitABXPadPress
    BufferRivalName 0
    Message VeilstonePC_Text_Arc2GariusPass
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC2_CYRUS, VeilstonePC_Arc2Movement_FaceWest
    WaitMovement
    Message VeilstonePC_Text_Arc2CyrusHere
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC2_GARIUS, VeilstonePC_Arc2Movement_GariusOut
    WaitMovement
    RemoveObject LOCALID_ARC2_GARIUS
    PlayFanfare SEQ_SE_DP_DOOR_OPEN
    WaitFanfare SEQ_SE_DP_DOOR_OPEN
    // Night passes
    FadeScreenOut
    WaitFadeScreen
    HealParty
    SetVar VAR_ARC2_PROGRESS, 59
    SetPosition LOCALID_PLAYER, 8, 0, 6, DIR_NORTH
    SetPosition LOCALID_ARC2_RUTH, 9, 0, 7, DIR_WEST
    SetPosition LOCALID_ARC2_CYRUS, 10, 0, 7, DIR_WEST
    WaitTime 30, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    ApplyMovement LOCALID_PLAYER, VeilstonePC_Arc2Movement_FaceSouth
    WaitMovement
    Message VeilstonePC_Text_Arc2RuthMorning
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC2_RUTH, VeilstonePC_Arc2Movement_RuthOut
    ApplyMovement LOCALID_ARC2_CYRUS, VeilstonePC_Arc2Movement_CyrusOut
    WaitMovement
    RemoveObject LOCALID_ARC2_RUTH
    RemoveObject LOCALID_ARC2_CYRUS
    PlayFanfare SEQ_SE_DP_DOOR_OPEN
    WaitFanfare SEQ_SE_DP_DOOR_OPEN
    ReleaseAll
    End

    .balign 4, 0
VeilstonePC_Arc2Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
VeilstonePC_Arc2Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
VeilstonePC_Arc2Movement_PlayerToTable:
    WalkNormalNorth 4
    WalkNormalEast 3
    FaceNorth
    EndMovement

    .balign 4, 0
VeilstonePC_Arc2Movement_GariusToCounter:
    WalkNormalNorth 6
    FaceNorth
    EndMovement

    .balign 4, 0
VeilstonePC_Arc2Movement_GariusPastTable:
    WalkNormalEast 2
    WalkNormalSouth
    FaceEast
    EndMovement

    .balign 4, 0
VeilstonePC_Arc2Movement_GariusOut:
    WalkNormalWest 2
    WalkNormalSouth 5
    EndMovement

    .balign 4, 0
VeilstonePC_Arc2Movement_RuthOut:
    WalkNormalSouth
    WalkNormalWest
    WalkNormalSouth 5
    EndMovement

    .balign 4, 0
VeilstonePC_Arc2Movement_CyrusOut:
    Delay8
    WalkNormalSouth
    WalkNormalWest 2
    WalkNormalSouth 5
    EndMovement
