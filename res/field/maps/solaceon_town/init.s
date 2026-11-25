#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 10
    InitScriptEntry_OnResume 11
    InitScriptEntry_OnFrameTable InitScriptFrameTable
    InitScriptEntryEnd

// 21 = SolaceonTown_Seizure (scene 3.4a part 7, armed by OnTransition on the first load at progress 50), before the
// city-entry cinematic (20).
InitScriptFrameTable:
    InitScriptGoToIfEqual VAR_MAP_LOCAL_0x02, 1, 21
    InitScriptGoToIfEqual VAR_CINE_CITY_PENDING, 1, 20
    InitScriptFrameTableEnd

    InitScriptEnd
