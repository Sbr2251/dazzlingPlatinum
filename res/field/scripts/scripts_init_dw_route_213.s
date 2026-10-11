#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_MAP_LOCAL_1, 0, 2
    InitScriptFrameTableEnd

    InitScriptEnd
