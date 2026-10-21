#include "macros/scrcmd.inc"
#include "res/text/bank/tv_programs.h"


    ScriptEntry TVBroadcast_Interact
    ScriptEntryEnd

// Arc 2 quests (R3, S10): Rowan's public turn. Every TV shows his Sinnoh Now interview from VAR_ARC2_PROGRESS 44
// to 85, and the station's correction from 86 (2.22, Rowan calls the station back) to 99. Stock programs otherwise.
TVBroadcast_Interact:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfGe VAR_ARC2_PROGRESS, 44, TVBroadcast_QuestsRowan
TVBroadcast_Stock:
    IncrementGameRecord RECORD_WATCHED_TV
    CheckBroadcastStatus VAR_RESULT
    TVBroadcastDummy VAR_RESULT
    SetVar VAR_0x8008, VAR_RESULT
    GoToIfEq VAR_0x8008, TV_BROADCAST_STATUS_FINISHED, TVBroadcast_PlayCommercial
    GoToIfEq VAR_0x8008, TV_BROADCAST_STATUS_FINISH, TVBroadcast_FinishProgram
    GoToIfEq VAR_0x8008, TV_BROADCAST_STATUS_BEGIN, TVBroadcast_BeginProgram
    GoToIfEq VAR_0x8008, TV_BROADCAST_STATUS_CONTINUE, TVBroadcast_ContinueProgram
    GoTo TVBroadcast_PlayCommercial
    End

TVBroadcast_PlayCommercial:
    LoadTVCommercial VAR_0x8004, VAR_0x8005
    MessageFromBank VAR_0x8004, VAR_0x8005
    WaitABXPadPress
    GoTo TVBroadcast_End
    End

TVBroadcast_FinishProgram:
    LoadTVFarewell VAR_0x8004, VAR_0x8005
    MessageFromBank VAR_0x8004, VAR_0x8005
    WaitABXPadPress
    FinishTVProgram
    GoTo TVBroadcast_End
    End

TVBroadcast_BeginProgram:
    LoadTVGreeting VAR_0x8004, VAR_0x8005
    MessageFromBank VAR_0x8004, VAR_0x8005
    GoTo TVBroadcast_ContinueProgram
    End

TVBroadcast_ContinueProgram:
    GetNextTVSegmentID VAR_0x8006
    GoToIfNe VAR_0x8006, 0, TVBroadcast_PlaySegment
    GoTo TVBroadcast_FinishProgram_Early
    End

TVBroadcast_FinishProgram_Early:
    LoadTVFarewellExtended VAR_0x8004, VAR_0x8005
    TVBroadcastDummy VAR_0x8004, VAR_0x8005
    MessageFromBank VAR_0x8004, VAR_0x8005
    FinishTVProgram
    WaitABXPadPress
    GoTo TVBroadcast_End
    End

TVBroadcast_PlaySegment:
    LoadTVSegmentIntro VAR_0x8004, VAR_0x8005
    TVBroadcastDummy VAR_0x8004, VAR_0x8005
    MessageFromBank VAR_0x8004, VAR_0x8005
    LoadTVSegment VAR_0x8006, VAR_0x8004, VAR_0x8005
    TVBroadcastDummy VAR_0x8006, VAR_0x8004, VAR_0x8005
    MessageFromBank VAR_0x8004, VAR_0x8005
    WaitABXPadPress
    GoTo TVBroadcast_End
    End

TVBroadcast_End:
    CloseMessage
    ReleaseAll
    End

TVBroadcast_QuestsRowan:
    GoToIfGe VAR_ARC2_PROGRESS, 100, TVBroadcast_Stock
    IncrementGameRecord RECORD_WATCHED_TV
    GoToIfGe VAR_ARC2_PROGRESS, 86, TVBroadcast_QuestsRowanCorrection
    Message TVBroadcast_Text_QuestsRowanInterview
    WaitABXPadPress
    GoTo TVBroadcast_End
    End

TVBroadcast_QuestsRowanCorrection:
    Message TVBroadcast_Text_QuestsRowanCorrection
    WaitABXPadPress
    GoTo TVBroadcast_End
    End

    .balign 4, 0
