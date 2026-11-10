#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_MAP_LOCAL_0x01, 0, 2
    // dwp:rift-213: puzzle frame fall (ground gone under a standing player): the engine raises VAR_MAP_LOCAL_0x03.
    InitScriptGoToIfEqual VAR_MAP_LOCAL_0x03, 1, 10
    InitScriptFrameTableEnd

    InitScriptEnd
