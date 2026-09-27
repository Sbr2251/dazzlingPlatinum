#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnLoad 2
    InitScriptEntry_OnResume 14
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_ARC1_PROGRESS, 1, 10
    InitScriptGoToIfEqual VAR_ARC1_PROGRESS, 3, 13
    InitScriptGoToIfEqual VAR_MAP_LOCAL_1, 1, 5
    InitScriptFrameTableEnd

    InitScriptEnd
