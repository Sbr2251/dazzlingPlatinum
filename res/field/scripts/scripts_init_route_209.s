#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 10
    InitScriptEntry_OnFrameTable Route209_FrameTable
    InitScriptEntryEnd

Route209_FrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 95, 11
    InitScriptFrameTableEnd

    InitScriptEnd
