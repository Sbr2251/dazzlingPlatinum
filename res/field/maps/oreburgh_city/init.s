#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 26
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// Arc 1: VAR_ARC1_PROGRESS 15 (Coal Badge won) runs the tunnel scene (script 25) on leaving the Gym
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_ARC1_PROGRESS, 15, 25
    InitScriptGoToIfEqual VAR_CINE_CITY_PENDING, 1, 36
    InitScriptFrameTableEnd

    InitScriptEnd
