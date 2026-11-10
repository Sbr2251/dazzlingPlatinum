#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

InitScriptFrameTable:
    // dwp:rift-lt: Cyrus's hint (the frame hook arms VAR_MAP_LOCAL_0x09
    // at fall count >= 2 / >= 4; the hint script clears it first).
    InitScriptGoToIfEqual VAR_MAP_LOCAL_0x09, 1, 14
    InitScriptFrameTableEnd

    InitScriptEnd
