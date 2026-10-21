#include "macros/scrcmd.inc"
#include "res/text/bank/route_215.h"
#include "res/field/events/events_route_215.h"


    ScriptEntry _008D
    ScriptEntry _00A0
    ScriptEntry _00FA
    ScriptEntry _0111
    ScriptEntry _013D
    ScriptEntry _0150
    ScriptEntry _0022
    ScriptEntry _0128
    ScriptEntry Route215_Arc2Crate
    ScriptEntry Route215_Arc2CrateSign
    ScriptEntry Route215_Arc2CyrusTalk
    ScriptEntryEnd

_0022:
    Call Route215_Arc2OnTransition
    GetTimeOfDay VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, 0, _0069
    GoToIfEq VAR_MAP_LOCAL_0, 1, _007B
    GoToIfEq VAR_MAP_LOCAL_0, 2, _007B
    GoToIfEq VAR_MAP_LOCAL_0, 3, _007B
    GoToIfEq VAR_MAP_LOCAL_0, 4, _007B
    End

_0069:
    ClearFlag FLAG_UNK_0x0273
    ClearFlag FLAG_UNK_0x0275
    SetFlag FLAG_UNK_0x0272
    SetFlag FLAG_UNK_0x0274
    End

_007B:
    ClearFlag FLAG_UNK_0x0272
    ClearFlag FLAG_UNK_0x0274
    SetFlag FLAG_UNK_0x0273
    SetFlag FLAG_UNK_0x0275
    End

_008D:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00A0:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x00CD, _00E5
    Message 1
    SetVar VAR_0x8004, ITEM_TM66
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, _00F0
    GiveItemQuantity
    SetFlag FLAG_UNK_0x00CD
    GoTo _00E5

_00E5:
    Message 2
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00F0:
    MessageBagIsFull
    CloseMessage
    ReleaseAll
    End

_00FA:
    ShowArrowSign 5
    End

_0111:
    ShowArrowSign 6
    End

_0128:
    ShowScrollingSign 7
    End

_013D:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 3
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0150:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 4
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 2, workstream s-veilstone: 2.17c, the opened crate (optional, night, VAR_ARC2_PROGRESS
// 49-59). Cyrus crouches by a pried-open Eclipse crate beside the path near the Veilstone gate (663-664, 595);
// a Buneary bolts off into the rocks as the player comes near (coord columns x667 from the gate, x659 from the west).
// (East of Ace Trainers Dennis and Maya, whose x648 sight line would otherwise start a battle mid-scene.)
// Seeing it adds 8 to VAR_ARC2_CHOICES (bit 3), once: FLAG_ARC2_VEILSTONE_B (0x0947). The empty crate stays
// (49-59) after that, any time of day.
// Map-local: hide flags 0x0030 Cyrus, 0x0031 crate, 0x0032 Buneary; VAR_MAP_LOCAL_1 = 1 arms the coords,
// VAR_MAP_LOCAL_2 time of day (scratch).

Route215_Arc2OnTransition:
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    SetFlag FLAG_UNK_0x0032
    SetVar VAR_MAP_LOCAL_1, 0
    GoToIfLt VAR_ARC2_PROGRESS, 49, Route215_Arc2OnTransitionEnd
    GoToIfGt VAR_ARC2_PROGRESS, 59, Route215_Arc2OnTransitionEnd
    GoToIfSet FLAG_ARC2_VEILSTONE_B, Route215_Arc2ShowCrateOnly
    GetTimeOfDay VAR_MAP_LOCAL_2
    GoToIfLt VAR_MAP_LOCAL_2, 3, Route215_Arc2OnTransitionEnd
    ClearFlag FLAG_UNK_0x0030
    ClearFlag FLAG_UNK_0x0031
    ClearFlag FLAG_UNK_0x0032
    SetVar VAR_MAP_LOCAL_1, 1
    Return

Route215_Arc2ShowCrateOnly:
    ClearFlag FLAG_UNK_0x0031
Route215_Arc2OnTransitionEnd:
    Return

Route215_Arc2CyrusTalk:
    PlayFanfare SEQ_SE_CONFIRM
    GoTo Route215_Arc2Crate
    End

Route215_Arc2Crate:
    LockAll
    SetVar VAR_MAP_LOCAL_1, 0
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
    WaitABXPadPress
    Message Route215_Text_Arc2CyrusExplain
    WaitABXPadPress
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
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message Route215_Text_Arc2CrateEmpty
    WaitABXPadPress
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
