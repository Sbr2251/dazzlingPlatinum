#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 8
    InitScriptEntry_OnResume 10
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// Arc 2 cutaway 2.19 (s-cutaways): the scene sets 69, so it runs once
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 63, 9
    InitScriptFrameTableEnd

    InitScriptEnd
