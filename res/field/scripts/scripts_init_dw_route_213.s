#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_MAP_LOCAL_1, 0, 2
    // dwp:rift-213: puzzle frame fall (ground gone under a standing player): the engine raises VAR_MAP_LOCAL_3.
    InitScriptGoToIfEqual VAR_MAP_LOCAL_3, 1, 10
    InitScriptFrameTableEnd

    InitScriptEnd
