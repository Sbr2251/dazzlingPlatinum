#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnResume 2
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// Arc 2 cutaways (s-cutaways): each scene sets the next progress value, so it runs once
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 5, 16
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 35, 17
    InitScriptFrameTableEnd

    InitScriptEnd
