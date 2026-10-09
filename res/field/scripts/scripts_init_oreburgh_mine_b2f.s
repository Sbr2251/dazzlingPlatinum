#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 6
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// Arc 1: VAR_ARC1_PROGRESS 15 (Coal Badge won, sent here by the Oreburgh City frame script) runs the rift scene
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_ARC1_PROGRESS, 15, 7
    InitScriptFrameTableEnd

    InitScriptEnd
