#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_PASTORIA_STATE, 3, 19
    InitScriptGoToIfEqual VAR_MAP_LOCAL_1, 1, 24
    InitScriptFrameTableEnd

    InitScriptEnd
