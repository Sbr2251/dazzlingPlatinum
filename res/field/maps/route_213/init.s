#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// Arc 2 (s-raid): 75 = arrival from Looker's briefing (Route213_Arc2Arrive, sets 80);
// 84 = back from DW_ROUTE_213 after the Lapras calm (Route213_Arc2Calm, warps to the Pastoria Center)
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 75, 10
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 84, 16
    InitScriptFrameTableEnd

    InitScriptEnd
