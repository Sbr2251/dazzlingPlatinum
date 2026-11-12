#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable HearthomeCity_FrameTable
    InitScriptEntryEnd

HearthomeCity_FrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 91, 34
    InitScriptGoToIfEqual VAR_CINE_CITY_PENDING, 1, 35
    InitScriptFrameTableEnd

    InitScriptEnd
