#include "macros/scrcmd.inc"
#include "res/text/bank/lake_valor_drained.h"
#include "res/field/events/events_lake_valor_drained.h"

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 2, workstream s-pastoria: screenplay 2.20, the Valor Basin (D12: this header is the
// Basin, always drained; Valor Lakefront leads here while FLAG_GALACTIC_LEFT_LAKE_VALOR is unset, and nothing in
// Arc 2 sets it). The stock Galactic grunts (three trainers, three talkers) and the Magikarp are deleted. A fence
// (sign + post) closes the corridor at x=46, so the basin floor and Valor Cavern (stock Saturn, which would set
// the lake's music flag) stay out of reach.
//   VAR_ARC2_PROGRESS 72: Garius at the fence. First talk sets 73. Second talk (once, FLAG_ARC2_PASTORIA_A):
//   the night question; Yes adds 2 to VAR_ARC2_CHOICES (bit 1); No, or never asking, leaves the bit clear.
//   He stays until the player leaves the map (OnTransition hides him at any state but 72).
// Map-local: FLAG_UNK_0x0030 = Garius hidden.

    ScriptEntry LakeValorDrained_Arc2FenceSign
    ScriptEntry LakeValorDrained_Arc2Garius
    ScriptEntry LakeValorDrained_Arc2OnTransition
    ScriptEntryEnd

LakeValorDrained_Arc2OnTransition:
    SetFlag FLAG_UNK_0x0030
    GoToIfNe VAR_ARC2_PROGRESS, 72, LakeValorDrained_Arc2OnTransitionEnd
    ClearFlag FLAG_UNK_0x0030
LakeValorDrained_Arc2OnTransitionEnd:
    End

LakeValorDrained_Arc2FenceSign:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message LakeValorDrained_Text_Arc2FenceSign
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

LakeValorDrained_Arc2Garius:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    BufferRivalName 0
    GoToIfGe VAR_ARC2_PROGRESS, 73, LakeValorDrained_Arc2GariusSecond
    // First talk: he doesn't turn at first
    Message LakeValorDrained_Text_Arc2GariusDont
    WaitABXPadPress
    FacePlayer
    BufferRivalName 0
    Message LakeValorDrained_Text_Arc2GariusLooker
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 73
    ApplyMovement LOCALID_ARC2_GARIUS, LakeValorDrained_Arc2Movement_FaceFence
    WaitMovement
    ReleaseAll
    End

LakeValorDrained_Arc2GariusSecond:
    GoToIfSet FLAG_ARC2_PASTORIA_A, LakeValorDrained_Arc2GariusAfter
    SetFlag FLAG_ARC2_PASTORIA_A
    // Polish #2: the rowboat memory before the question (warmth beat)
    Message LakeValorDrained_Text_Arc2GariusDad
    WaitABXPadPress
    BufferRivalName 0
    Message LakeValorDrained_Text_Arc2GariusQuestion
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, LakeValorDrained_Arc2GariusYes
    BufferRivalName 0
    Message LakeValorDrained_Text_Arc2GariusNo
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

LakeValorDrained_Arc2GariusYes:
    AddVar VAR_ARC2_CHOICES, 2
    BufferRivalName 0
    Message LakeValorDrained_Text_Arc2GariusYes
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

LakeValorDrained_Arc2GariusAfter:
    Message LakeValorDrained_Text_Arc2GariusAfter
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
LakeValorDrained_Arc2Movement_FaceFence:
    FaceWest
    EndMovement
