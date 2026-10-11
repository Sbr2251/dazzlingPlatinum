#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 6
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// Arc 2 (s-eterna): the Haven lobby scene runs on entry at VAR_ARC2_PROGRESS 33 and sets 34.
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 33, 4
    InitScriptFrameTableEnd

    InitScriptEnd
