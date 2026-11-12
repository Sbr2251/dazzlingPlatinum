#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_CELESTIC_TOWN_STATE, 1, 5
    InitScriptGoToIfEqual VAR_CINE_CITY_PENDING, 1, 14
    InitScriptFrameTableEnd

    InitScriptEnd
