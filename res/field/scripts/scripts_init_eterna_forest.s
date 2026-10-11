#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 11
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_UNK_0x40CD, 1, 12
    InitScriptGoToIfEqual VAR_MAP_LOCAL_1, 1, 16
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 26, 17
    InitScriptFrameTableEnd

    InitScriptEnd
