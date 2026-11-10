#include "macros/scrcmd.inc"
#include "res/text/bank/lake_valor_drained.h"
#include "res/field/maps/locals/lake_valor_drained.h"


    ScriptEntry LakeValorDrained_GruntM1
    ScriptEntry LakeValorDrained_GruntF
    ScriptEntry LakeValorDrained_GruntM2
    ScriptEntry LakeValorDrained_Magikarp
    ScriptEntry LakeValorDrained_Arc2FenceSign
    ScriptEntry LakeValorDrained_Arc2Garius
    ScriptEntry LakeValorDrained_Arc2OnTransition
    ScriptEntryEnd

LakeValorDrained_GruntM1:
    NPCMessage LakeValorDrained_Text_WhatYouDoWant
    End

LakeValorDrained_GruntF:
    NPCMessage LakeValorDrained_Text_MagikarpWorthless
    End

LakeValorDrained_GruntM2:
    NPCMessage LakeValorDrained_Text_NextStopLakeVerity
    End

LakeValorDrained_Magikarp:
    PokemonCryAndMessage SPECIES_MAGIKARP, LakeValorDrained_Text_MagikarpIsFlopping, 11
    End

    .balign 4, 0

LakeValorDrained_Arc2OnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    GoToIfNe VAR_ARC2_PROGRESS, 72, LakeValorDrained_Arc2OnTransitionEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
LakeValorDrained_Arc2OnTransitionEnd:
    End

LakeValorDrained_Arc2FenceSign:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message LakeValorDrained_Text_Arc2FenceSign
    WaitButton
    CloseMessage
    ReleaseAll
    End

LakeValorDrained_Arc2Garius:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    BufferRivalName 0
    GoToIfGe VAR_ARC2_PROGRESS, 73, LakeValorDrained_Arc2GariusSecond
    // First talk: he doesn't turn at first
    Message LakeValorDrained_Text_Arc2GariusDont
    WaitButton
    FacePlayer
    BufferRivalName 0
    Message LakeValorDrained_Text_Arc2GariusLooker
    WaitButton
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
    WaitButton
    BufferRivalName 0
    Message LakeValorDrained_Text_Arc2GariusQuestion
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, LakeValorDrained_Arc2GariusYes
    BufferRivalName 0
    Message LakeValorDrained_Text_Arc2GariusNo
    WaitButton
    CloseMessage
    ReleaseAll
    End

LakeValorDrained_Arc2GariusYes:
    AddVar VAR_ARC2_CHOICES, 2
    BufferRivalName 0
    Message LakeValorDrained_Text_Arc2GariusYes
    WaitButton
    CloseMessage
    ReleaseAll
    End

LakeValorDrained_Arc2GariusAfter:
    Message LakeValorDrained_Text_Arc2GariusAfter
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
LakeValorDrained_Arc2Movement_FaceFence:
    FaceWest
    EndMovement
