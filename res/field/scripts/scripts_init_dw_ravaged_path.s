#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_MAP_LOCAL_1, 0, 3
    // dwp:engine-a: puzzle frame fall (ground gone under a standing player): the engine raises VAR_MAP_LOCAL_3.
    InitScriptGoToIfEqual VAR_MAP_LOCAL_3, 1, 2
    InitScriptFrameTableEnd

    InitScriptEnd
