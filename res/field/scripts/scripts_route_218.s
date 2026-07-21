#include "macros/scrcmd.inc"
#include "res/text/bank/route_218.h"


    ScriptEntry _CanalaveArrowSign
    ScriptEntry _JubilifeArrowSign
    ScriptEntry _GuitaristDialogue
    ScriptEntry _FishermanDialogue
    ScriptEntry _ClefairyFirstCry
    ScriptEntry _ClefairySecondCry
    ScriptEntry _PikachuCry
    ScriptEntry _EverspringRivalScene
    ScriptEntry _EverspringRivalTalk
    ScriptEntry _RiftRelic
    ScriptEntryEnd

_CanalaveArrowSign:
    ShowArrowSign 5
    End

_JubilifeArrowSign:
    ShowArrowSign 6
    End

_GuitaristDialogue:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_FishermanDialogue:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message 4
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_ClefairyFirstCry:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_CLEFAIRY
    Message 1
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_ClefairySecondCry:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_CLEFAIRY
    Message 2
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_PikachuCry:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_PIKACHU
    Message 3
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_EverspringRivalScene:
    LockAll
    ApplyMovement 21, _RivalNoticesPlayer
    WaitMovement
    SetRivalBGM
    Message 7
    WaitABXPadPress
    CloseMessage
    Message 8
    WaitABXPadPress
    CloseMessage
    Message 9
    WaitABXPadPress
    CloseMessage
    Message 10
    WaitABXPadPress
    CloseMessage
    Message 11
    WaitABXPadPress
    CloseMessage
    RemoveObject 21
    SetFlag FLAG_HIDE_EVERSPRING_RIVAL
    SetVar VAR_EVERSPRING_RIVAL_SCENE_STATE, 1
    ReleaseAll
    End

_EverspringRivalTalk:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 7
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_RiftRelic:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message 12
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
_RivalNoticesPlayer:
    EmoteExclamationMark
    Delay8
    FaceSouth
    EndMovement
