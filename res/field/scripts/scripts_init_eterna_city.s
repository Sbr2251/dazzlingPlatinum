#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 21
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// Arc 2 (s-eterna): 31 = Garius waits at the Gym door; VAR_MAP_LOCAL_2 = 1 = just walked to the Haven trees (33).
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 31, 31
    InitScriptGoToIfEqual VAR_MAP_LOCAL_2, 1, 32
    InitScriptFrameTableEnd

    InitScriptEnd
