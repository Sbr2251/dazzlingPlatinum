#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_PASTORIA_CITY_STATE, 3, 19
    InitScriptGoToIfEqual VAR_MAP_LOCAL_0x01, 1, 24
    InitScriptFrameTableEnd

    InitScriptEnd
