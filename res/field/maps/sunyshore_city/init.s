#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 19
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_SUNYSHORE_CITY_STATE, 0, 1
    InitScriptGoToIfEqual VAR_CINE_CITY_PENDING, 1, 20
    InitScriptFrameTableEnd

    InitScriptEnd
