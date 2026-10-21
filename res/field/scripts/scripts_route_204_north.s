#include "macros/scrcmd.inc"
#include "res/text/bank/route_204_north.h"
#include "res/field/events/events_route_204_north.h"


    ScriptEntry _000E
    ScriptEntry _0021
    ScriptEntry _007B
    ScriptEntry Route204North_Arc2OnFrameResonator
    ScriptEntry Route204North_Arc2Ruth
    ScriptEntry Route204North_Arc2Cyrus
    ScriptEntry Route204North_Arc2Garius
    ScriptEntry Route204North_Arc2Boulder
    ScriptEntry Route204North_Arc2RockSmashed
    ScriptEntry Route204North_OnTransition
    ScriptEntryEnd

_000E:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0021:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x00C5, _0066
    Message 1
    SetVar VAR_0x8004, ITEM_TM78
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, _0071
    GiveItemQuantity
    SetFlag FLAG_UNK_0x00C5
    GoTo _0066

_0066:
    Message 2
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0071:
    MessageBagIsFull
    CloseMessage
    ReleaseAll
    End

_007B:
    ShowArrowSign 3
    End

// ================================================================================================================
// Arc 2, workstream s-route204: the Route 204 North half of screenplay 2.8 (the Resonator, Garius back from the
// north with the Poketch line, S3).
//
// Flags (s-route204 block 0x0936-0x0939): none needed on this map. Map-local temporaries, set every load in
// Route204North_OnTransition (0x20 is the stock cut tree):
//   FLAG_UNK_0x0030 = hide Ruth      FLAG_UNK_0x0031 = hide Cyrus     FLAG_UNK_0x0032 = hide Garius
//   FLAG_UNK_0x0033 = hide the cracked rock (171,675)                 FLAG_UNK_0x0034 = hide the two boulders
//
// VAR_ARC2_PROGRESS on this map:
//   <16    stock route (none of the Arc 2 objects).
//   16     Ravaged Path's 2.8 script warps the player to (171,678) facing north; Ruth (170,678) and Cyrus (172,678)
//          flank them. The cracked rock (171,675) sits between two boulders (170,675) (172,675) across the 3-wide
//          path north. The frame script gives the Resonator (ITEM_PORTAL_READER was removed at Ravaged Path) and
//          sets 17.
//   17     the rock is the stock field-move rock (script 10001: the resonator workstream's Resonator path).
//          Stepping onto its tile once it's smashed runs the coord event: 18, Ruth's lines, Garius walks down from
//          Floaroma's side, then Garius, Ruth and Cyrus leave north. Sets 19.
//   19+    the boulders stay; the rock, Ruth, Cyrus and Garius are gone.

Route204North_OnTransition:
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    SetFlag FLAG_UNK_0x0032
    SetFlag FLAG_UNK_0x0033
    SetFlag FLAG_UNK_0x0034
    GoToIfLt VAR_ARC2_PROGRESS, 16, Route204North_OnTransitionEnd
    ClearFlag FLAG_UNK_0x0034
    GoToIfGe VAR_ARC2_PROGRESS, 19, Route204North_OnTransitionEnd
    ClearFlag FLAG_UNK_0x0030
    ClearFlag FLAG_UNK_0x0031
    GoToIfGe VAR_ARC2_PROGRESS, 18, Route204North_OnTransitionEnd
    ClearFlag FLAG_UNK_0x0033
Route204North_OnTransitionEnd:
    End

// 16: morning, at the rock. Ruth hands over the Resonator.
Route204North_Arc2OnFrameResonator:
    LockAll
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, Route204North_Movement_FaceWest
    ApplyMovement ROUTE_204_NORTH_ARC2_RUTH, Route204North_Movement_FaceEast
    WaitMovement
    Message Route204North_Text_Arc2RuthResonator
    WaitABXPadPress
    Message Route204North_Text_Arc2RuthHoldsShard
    WaitABXPadPress
    CloseMessage
    SetVar VAR_0x8004, ITEM_RESONATOR
    SetVar VAR_0x8005, 1
    GiveItemQuantity
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 17
    ApplyMovement LOCALID_PLAYER, Route204North_Movement_FaceNorth
    WaitMovement
    ReleaseAll
    End

Route204North_Arc2Ruth:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message Route204North_Text_Arc2RuthHoldsShard
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Route204North_Arc2Cyrus:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message Route204North_Text_Arc2CyrusEllipsis
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Route204North_Arc2Garius:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    BufferRivalName 1
    Message Route204North_Text_Arc2GariusFineGood
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Route204North_Arc2Boulder:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message Route204North_Text_Arc2Boulder
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// 17, the player steps onto the smashed rock's tile (171,675).
Route204North_Arc2RockSmashed:
    LockAll
    SetVar VAR_ARC2_PROGRESS, 18
    ApplyMovement ROUTE_204_NORTH_ARC2_RUTH, Route204North_Movement_RuthStepUp
    ApplyMovement ROUTE_204_NORTH_ARC2_CYRUS, Route204North_Movement_CyrusStepUp
    ApplyMovement LOCALID_PLAYER, Route204North_Movement_FaceSouth
    WaitMovement
    Message Route204North_Text_Arc2RuthItWorks
    WaitABXPadPress
    CloseMessage
    // Garius walks down from the north (Floaroma's side), looking at his Poketch
    ClearFlag FLAG_UNK_0x0032
    AddObject ROUTE_204_NORTH_ARC2_GARIUS
    ApplyMovement ROUTE_204_NORTH_ARC2_GARIUS, Route204North_Movement_GariusWalkDown
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Route204North_Movement_FaceNorth
    ApplyMovement ROUTE_204_NORTH_ARC2_RUTH, Route204North_Movement_FaceNorth
    ApplyMovement ROUTE_204_NORTH_ARC2_CYRUS, Route204North_Movement_FaceNorth
    WaitMovement
    BufferRivalName 1
    Message Route204North_Text_Arc2GariusMissedCalls
    WaitABXPadPress
    CloseMessage
    ApplyMovement ROUTE_204_NORTH_ARC2_GARIUS, Route204North_Movement_GariusLookUp
    WaitMovement
    Message Route204North_Text_Arc2GariusCooledOff
    WaitABXPadPress
    Message Route204North_Text_Arc2GariusFineGood
    WaitABXPadPress
    CloseMessage
    ApplyMovement ROUTE_204_NORTH_ARC2_GARIUS, Route204North_Movement_GariusLeave
    WaitMovement
    RemoveObject ROUTE_204_NORTH_ARC2_GARIUS
    SetFlag FLAG_UNK_0x0032
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, Route204North_Movement_FaceSouth
    ApplyMovement ROUTE_204_NORTH_ARC2_CYRUS, Route204North_Movement_FaceWest
    WaitMovement
    Message Route204North_Text_Arc2CyrusDistance
    WaitABXPadPress
    CloseMessage
    ApplyMovement ROUTE_204_NORTH_ARC2_RUTH, Route204North_Movement_FaceEast
    WaitMovement
    Message Route204North_Text_Arc2RuthFloaroma
    WaitABXPadPress
    CloseMessage
    // The player steps aside to (170,674); Ruth, then Cyrus, go north through the gap
    ApplyMovement LOCALID_PLAYER, Route204North_Movement_PlayerStepAside
    WaitMovement
    ApplyMovement ROUTE_204_NORTH_ARC2_RUTH, Route204North_Movement_RuthLeave
    WaitMovement
    RemoveObject ROUTE_204_NORTH_ARC2_RUTH
    SetFlag FLAG_UNK_0x0030
    ApplyMovement ROUTE_204_NORTH_ARC2_CYRUS, Route204North_Movement_CyrusLeave
    WaitMovement
    RemoveObject ROUTE_204_NORTH_ARC2_CYRUS
    SetFlag FLAG_UNK_0x0031
    SetVar VAR_ARC2_PROGRESS, 19
    ReleaseAll
    End

    .balign 4, 0
Route204North_Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
Route204North_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
Route204North_Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
Route204North_Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
Route204North_Movement_RuthStepUp:
    WalkNormalNorth 2
    FaceEast
    EndMovement

    .balign 4, 0
Route204North_Movement_CyrusStepUp:
    WalkNormalNorth 2
    FaceWest
    EndMovement

    .balign 4, 0
Route204North_Movement_GariusWalkDown:
    WalkSlowSouth 2
    FaceSouth
    EndMovement

    .balign 4, 0
Route204North_Movement_GariusLookUp:
    Delay8
    FaceSouth
    EndMovement

    .balign 4, 0
Route204North_Movement_GariusLeave:
    FaceNorth
    WalkNormalNorth 2
    EndMovement

    .balign 4, 0
Route204North_Movement_PlayerStepAside:
    WalkNormalNorth
    WalkNormalWest
    FaceEast
    EndMovement

    .balign 4, 0
Route204North_Movement_RuthLeave:
    WalkNormalEast
    WalkNormalNorth 4
    EndMovement

    .balign 4, 0
Route204North_Movement_CyrusLeave:
    WalkNormalWest
    WalkNormalNorth 4
    EndMovement
