#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable RavagedPath_InitFrameTable
    InitScriptEntryEnd

// Arc 2: back from DW_RAVAGED_PATH with the Hitmonlee totem calmed (rift-a sets 15) runs 2.8's first half (script 8)
RavagedPath_InitFrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 15, 8
    InitScriptFrameTableEnd

    InitScriptEnd
