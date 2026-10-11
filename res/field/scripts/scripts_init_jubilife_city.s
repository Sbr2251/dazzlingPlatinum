#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// Arc 2 (s-jubilife): the on-transition script arms VAR_MAP_LOCAL_2. 1 runs 2.1 (finding Cyrus, script 48),
// 3 runs 2.3 (Cyrus battle 1 outside the Trainers' School, script 49).
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_MAP_LOCAL_2, 1, 48
    InitScriptGoToIfEqual VAR_MAP_LOCAL_2, 3, 49
    InitScriptFrameTableEnd

    InitScriptEnd
