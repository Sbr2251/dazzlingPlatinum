#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 5
    InitScriptEntry_OnFrameTable MtCoronet1FNorthRoom1_InitFrameTable
    InitScriptEntryEnd

MtCoronet1FNorthRoom1_InitFrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 39, 3
    InitScriptFrameTableEnd

    InitScriptEnd
