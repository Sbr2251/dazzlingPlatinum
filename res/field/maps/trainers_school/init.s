#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 14
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// Arc 2 (s-jubilife): VAR_ARC2_PROGRESS 1 runs 2.2, the confession (script 15), on entering the school
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 1, 15
    InitScriptFrameTableEnd

    InitScriptEnd
