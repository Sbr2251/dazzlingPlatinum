#include "macros/scrcmd.inc"
#include "res/text/bank/route_218.h"


    ScriptEntry _Researcher
    ScriptEntry _ClefairyWest
    ScriptEntry _ClefairyEast
    ScriptEntry _RiftShrine
    ScriptEntry _RivalScene
    ScriptEntry _RivalTalk
    ScriptEntry _SanctuarySign
    ScriptEntryEnd

_Researcher:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 5
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_ClefairyWest:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_CLEFAIRY
    Message 7
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_ClefairyEast:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_CLEFAIRY
    Message 7
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_RiftShrine:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message 8
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_RivalScene:
    LockAll
    ApplyMovement 0, _RivalNoticesPlayer
    WaitMovement
    SetRivalBGM
    Message 0
    WaitABXPadPress
    CloseMessage
    Message 1
    WaitABXPadPress
    CloseMessage
    Message 2
    WaitABXPadPress
    CloseMessage
    Message 3
    WaitABXPadPress
    CloseMessage
    Message 4
    WaitABXPadPress
    CloseMessage
    RemoveObject 0
    SetFlag FLAG_HIDE_EVERSPRING_RIVAL
    SetVar VAR_EVERSPRING_RIVAL_SCENE_STATE, 1
    ReleaseAll
    End

_RivalTalk:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_SanctuarySign:
    ShowScrollingSign 6
    End

    .balign 4, 0
_RivalNoticesPlayer:
    EmoteExclamationMark
    Delay8
    FaceSouth
    EndMovement
