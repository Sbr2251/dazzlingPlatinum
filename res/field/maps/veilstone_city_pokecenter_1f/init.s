#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 0x28A0
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 57, 6
    InitScriptFrameTableEnd

    InitScriptEnd
