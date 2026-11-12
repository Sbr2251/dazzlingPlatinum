#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 10
    InitScriptEntry_OnResume 11
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_CINE_CITY_PENDING, 1, 20
    InitScriptFrameTableEnd

    InitScriptEnd
