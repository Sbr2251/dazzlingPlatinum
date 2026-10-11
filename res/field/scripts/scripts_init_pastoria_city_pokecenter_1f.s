#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 0x28A0
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// Arc 2 (s-pastoria): 2.21a at VAR_ARC2_PROGRESS 73 (entry 9), 2.22 at 84/85 (entry 10)
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 73, 9
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 84, 10
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 85, 10
    InitScriptFrameTableEnd

    InitScriptEnd
