#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// Solaceon raid: the first entry at 20 plays the Cyrus scene (SolaceonRuinsRoom1_RaidEntry), which sets 30
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_SOLACEON_PROGRESS, 20, 5
    InitScriptFrameTableEnd

    InitScriptEnd
