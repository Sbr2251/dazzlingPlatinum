#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// Arc 2 (s-jubilife): the on-transition script arms VAR_MAP_LOCAL_2. 3 runs 2.3 (Cyrus battle 1 outside the
// Trainers' School, script 49). 1 arms 2.1 (script 48), a coord event in the plaza, not on frame.
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_MAP_LOCAL_2, 3, 49
    InitScriptFrameTableEnd

    InitScriptEnd
