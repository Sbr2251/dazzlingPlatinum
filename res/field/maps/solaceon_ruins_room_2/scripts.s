#include "macros/scrcmd.inc"
#include "res/text/bank/solaceon_ruins_room_2.h"
#include "res/field/maps/locals/solaceon_ruins_room_2.h"

// The Hiker wanted HM05 Defog in stock; there are no HMs in this hack and Room 7's HM05 ball is TM30 now
// (screenplay.md Appendix A). He is lost: show him TM30 and he asks the way down, for the same Green Shard.
// Solaceon raid: he is hidden during the raid (progress 20-49; FLAG_MAP_LOCAL_HIDE_OBSTACLE_16, set by
// SolaceonRuinsRoom2_OnTransition). Before 20 the rope in Room 1 keeps everyone out of this room.

    ScriptEntry SolaceonRuinsRoom2_Hiker
    ScriptEntry SolaceonRuinsRoom2_OnTransition
    ScriptEntryEnd

SolaceonRuinsRoom2_OnTransition:
    GoToIfLt VAR_SOLACEON_PROGRESS, 20, SolaceonRuinsRoom2_OnTransitionEnd
    GoToIfGe VAR_SOLACEON_PROGRESS, 50, SolaceonRuinsRoom2_OnTransitionEnd
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
SolaceonRuinsRoom2_OnTransitionEnd:
    End

SolaceonRuinsRoom2_Hiker:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_RECEIVED_SOLACEON_RUINS_ROOM_2_GREEN_SHARD, SolaceonRuinsRoom2_IKnowTheWayDown
    GoToIfSet FLAG_DID_NOT_LOAN_HM_DEFOG, SolaceonRuinsRoom2_AskTheWayDown
    CheckItem ITEM_TM30, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, TRUE, SolaceonRuinsRoom2_PlayerHasTM30
    Message SolaceonRuinsRoom2_Text_TMInRuins
    WaitButton
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom2_PlayerHasTM30:
    Message SolaceonRuinsRoom2_Text_TMInRuins2
    GoTo SolaceonRuinsRoom2_AskTheWayDown
    End

SolaceonRuinsRoom2_AskTheWayDown:
    ApplyMovement LOCALID_HIKER, SolaceonRuinsRoom2_Movement_HikerExclamationMark
    WaitMovement
    Message SolaceonRuinsRoom2_Text_CanYouShowTheWay
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, SolaceonRuinsRoom2_ShowTheWay
    GoToIfEq VAR_RESULT, MENU_NO, SolaceonRuinsRoom2_DontShowTheWay
    End

SolaceonRuinsRoom2_ShowTheWay:
    Message SolaceonRuinsRoom2_Text_ThanksYoureMyRescuer
    SetVar VAR_0x8004, ITEM_GREEN_SHARD
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, SolaceonRuinsRoom2_BagIsFull
    SetFlag FLAG_RECEIVED_SOLACEON_RUINS_ROOM_2_GREEN_SHARD
    CallCommonScript CommonScript_AddItemQuantityNoLineFeed
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom2_BagIsFull:
    CallCommonScript CommonScript_BagIsFull
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom2_DontShowTheWay:
    SetFlag FLAG_DID_NOT_LOAN_HM_DEFOG
    Message SolaceonRuinsRoom2_Text_ItsNotLikeItWearsOut
    WaitButton
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom2_IKnowTheWayDown:
    Message SolaceonRuinsRoom2_Text_IKnowTheWayDown
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
SolaceonRuinsRoom2_Movement_HikerExclamationMark:
    EmoteExclamationMark
    EndMovement
