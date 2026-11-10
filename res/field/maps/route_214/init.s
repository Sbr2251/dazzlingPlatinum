#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 3
    InitScriptEntry_OnLoad 4
    InitScriptEntry_OnFrameTable Route214_InitFrameTable
    InitScriptEntryEnd

// Arc 2: back from DW_ROUTE_214 with the Skarmory totem calmed (rift-b sets 63) warps into the 2.19 cutaway
// (script 11); the cutaway sets 69, so this fires once.
Route214_InitFrameTable:
    InitScriptGoToIfEqual VAR_ARC2_PROGRESS, 63, 11
    InitScriptFrameTableEnd

    InitScriptEnd
