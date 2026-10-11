#include "macros/scrcmd.inc"
#include "res/text/bank/oreburgh_gate_1f.h"


    ScriptEntry _000E
    ScriptEntry _0014
    ScriptEntry _007B
    ScriptEntryEnd

_000E:
    SetFlag FLAG_FIRST_ARRIVAL_OREBURGH_GATE
    End

_0014:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    // Arc 1: no HMs (bible; backlog 2 replaces them with the Resonator). The hiker keeps HM06
    // and its Rock Smash / Badge lines to himself until Arc 2.
    GoToIfLt VAR_ARC1_PROGRESS, 17, OreburghGate1F_Arc1HikerTalk
    CheckBadgeAcquired BADGE_ID_COAL, VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _003A
    Message 2
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_003A:
    GoToIfSet FLAG_UNK_0x0093, _0064
    Message 0
    SetVar VAR_0x8004, ITEM_HM06
    SetVar VAR_0x8005, 1
    GiveItemQuantity
    Call _006F
    GoTo _0064

_0064:
    Message 1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_006F:
    SetFlag FLAG_UNK_0x0093
    SetVar VAR_UNK_0x4093, 2
    Return

_007B:
    // Arc 1: the HM06 hand-out coord stays inert (no HMs in Arc 1; stock again from 17).
    GoToIfLt VAR_ARC1_PROGRESS, 17, OreburghGate1F_Arc1HikerCoordEnd
    LockAll
    ApplyMovement 10, _00C0
    ApplyMovement LOCALID_PLAYER, _00B4
    WaitMovement
    Message 0
    SetVar VAR_0x8004, ITEM_HM06
    SetVar VAR_0x8005, 1
    GiveItemQuantity
    Call _006F
    Message 1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
_00B4:
    Delay8
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_00C0:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    WalkNormalSouth
    EndMovement

OreburghGate1F_Arc1HikerTalk:
    Message OreburghGate1F_Text_Arc1Hiker
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghGate1F_Arc1HikerCoordEnd:
    End
