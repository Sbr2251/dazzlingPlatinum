#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable LostTower1F_FrameTable
    InitScriptEntryEnd

LostTower1F_FrameTable:
    InitScriptGoToIfEqual VAR_MAP_LOCAL_2, 1, 6
    InitScriptFrameTableEnd

    InitScriptEnd
