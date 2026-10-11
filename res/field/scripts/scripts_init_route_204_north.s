#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 10
    InitScriptEntry_OnFrameTable Route204North_InitFrameTable
    InitScriptEntryEnd

// Arc 2: 16 (warped here from Ravaged Path, the morning after) runs the Resonator give (script 4)
Route204North_InitFrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 16, 4
    InitScriptFrameTableEnd

    InitScriptEnd
