#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 4
    InitScriptEntry_OnFrameTable CelesticTownCave_InitFrameTable
    InitScriptEntryEnd

CelesticTownCave_InitFrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 40, 5
    InitScriptFrameTableEnd

    InitScriptEnd
