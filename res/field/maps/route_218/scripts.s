#include "macros/scrcmd.inc"
#include "res/text/bank/route_218.h"
#include "res/field/maps/locals/route_218.h"


    ScriptEntry Route218_Researcher
    ScriptEntry Route218_ClefairyWest
    ScriptEntry Route218_ClefairyEast
    ScriptEntry Route218_RiftShrine
    ScriptEntry Route218_RivalScene
    ScriptEntry Route218_RivalTalk
    ScriptEntry Route218_SanctuarySign
    ScriptEntryEnd

Route218_Researcher:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message 5
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

Route218_ClefairyWest:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    WaitSE SE_CONFIRM_sseq_3
    PlayCry SPECIES_CLEFAIRY
    Message 7
    WaitCry
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

Route218_ClefairyEast:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    WaitSE SE_CONFIRM_sseq_3
    PlayCry SPECIES_CLEFAIRY
    Message 7
    WaitCry
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route218_RiftShrine:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message 8
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

Route218_RivalScene:
    LockAll
    ApplyMovement LOCALID_EVERSPRING_RIVAL, Route218_Movement_RivalNoticesPlayer
    WaitMovement
    CallCommonScript CommonScript_SetRivalBGM
    Message 0
    WaitABPadPress
    CloseMessage
    Message 1
    WaitABPadPress
    CloseMessage
    Message 2
    WaitABPadPress
    CloseMessage
    Message 3
    WaitABPadPress
    CloseMessage
    Message 4
    WaitABPadPress
    CloseMessage
    RemoveObject LOCALID_EVERSPRING_RIVAL
    SetFlag FLAG_HIDE_EVERSPRING_RIVAL
    SetVar VAR_EVERSPRING_RIVAL_SCENE_STATE, 1
    ReleaseAll
    End

Route218_RivalTalk:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message 0
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

Route218_SanctuarySign:
    ShowScrollingSign 6
    End

    .balign 4, 0
Route218_Movement_RivalNoticesPlayer:
    EmoteExclamationMark
    Delay8
    FaceSouth
    EndMovement
