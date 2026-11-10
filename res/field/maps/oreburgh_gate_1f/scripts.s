#include "macros/scrcmd.inc"
#include "res/text/bank/oreburgh_gate_1f.h"
#include "res/field/maps/locals/oreburgh_gate_1f.h"


    ScriptEntry OreburghGate1F_OnTransition
    ScriptEntry OreburghGate1F_Hiker
    ScriptEntry OreburghGate1F_CoordEvent_Hiker
    ScriptEntryEnd

OreburghGate1F_OnTransition:
    SetFlag FLAG_FIRST_ARRIVAL_OREBURGH_GATE
    End

OreburghGate1F_Hiker:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    // Arc 1: no HMs (bible; backlog 2 replaces them with the Resonator). The hiker keeps HM06
    // and its Rock Smash / Badge lines to himself until Arc 2.
    GoToIfLt VAR_ARC1_PROGRESS, 17, OreburghGate1F_Arc1HikerTalk
    CheckBadgeAcquired BADGE_ID_COAL, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, OreburghGate1F_HikerGiveHM
    Message OreburghGate1F_Text_NowYouCanUseRockSmash
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghGate1F_HikerGiveHM:
    GoToIfSet FLAG_RECEIVED_HM06, OreburghGate1F_ThatHMContainsRockSmash
    Message OreburghGate1F_Text_MakeAGiftOfThisHM
    SetVar VAR_0x8004, ITEM_HM06
    SetVar VAR_0x8005, 1
    CallCommonScript CommonScript_AddItemQuantity
    Call OreburghGate1F_SetFlagReceivedHM06
    GoTo OreburghGate1F_ThatHMContainsRockSmash

OreburghGate1F_ThatHMContainsRockSmash:
    Message OreburghGate1F_Text_ThatHMContainsRockSmash
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghGate1F_SetFlagReceivedHM06:
    SetFlag FLAG_RECEIVED_HM06
    SetVar VAR_OREBURGH_GATE_1F_HIKER_STATE, 2
    Return

OreburghGate1F_CoordEvent_Hiker:
    // Arc 1: the HM06 hand-out coord stays inert (no HMs in Arc 1; stock again from 17).
    GoToIfLt VAR_ARC1_PROGRESS, 17, OreburghGate1F_Arc1HikerCoordEnd
    LockAll
    ApplyMovement LOCALID_HIKER, OreburghGate1F_Movement_HikerWalkToPlayer
    ApplyMovement LOCALID_PLAYER, OreburghGate1F_Movement_PlayerFaceHiker
    WaitMovement
    Message OreburghGate1F_Text_MakeAGiftOfThisHM
    SetVar VAR_0x8004, ITEM_HM06
    SetVar VAR_0x8005, 1
    CallCommonScript CommonScript_AddItemQuantity
    Call OreburghGate1F_SetFlagReceivedHM06
    Message OreburghGate1F_Text_ThatHMContainsRockSmash
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
OreburghGate1F_Movement_PlayerFaceHiker:
    Delay8
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
OreburghGate1F_Movement_HikerWalkToPlayer:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    WalkNormalSouth
    EndMovement

OreburghGate1F_Arc1HikerTalk:
    Message OreburghGate1F_Text_Arc1Hiker
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghGate1F_Arc1HikerCoordEnd:
    End
