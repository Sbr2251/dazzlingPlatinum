#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnLoad 2
    InitScriptEntry_OnResume 14
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// Arc 1: VAR_MAP_LOCAL_2 is armed by LakeVerity_OnTransition for the first state-3 entry (the arrival scene)
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_ARC1_PROGRESS, 1, 10
    InitScriptGoToIfEqual VAR_MAP_LOCAL_2, 1, 13
    InitScriptGoToIfEqual VAR_ARC1_PROGRESS, 7, 19
    InitScriptGoToIfEqual VAR_MAP_LOCAL_1, 1, 5
    InitScriptFrameTableEnd

    InitScriptEnd
