#include "macros/scrcmd.inc"
#include "res/text/bank/route_210_north.h"


    ScriptEntry Route210North_BlackBelt
    ScriptEntry Route210North_ArrowSignpostCelesticTown
    ScriptEntry Route210North_SignboardGrandmaWilmasHouse
    ScriptEntry Route210North_OnTransition
    ScriptEntry Route210North_OnResume
    ScriptEntry Route210North_Arc2RiftMist
    ScriptEntryEnd

// Arc 2: Route 210 North uses the violet rift mist (OVERWORLD_WEATHER_RIFT_MIST, world-art), which blocks nothing,
// so no Defog workaround is needed here or in Celestic / Route 210 South.
// FLAG_ARC2_CELESTIC_A = the rift-mist line has been shown (text-only S11 mist, at the Celestic edge).

Route210North_OnTransition:
    End

Route210North_OnResume:
    End

Route210North_Arc2RiftMist:
    GoToIfSet FLAG_ARC2_CELESTIC_A, Route210North_Arc2RiftMistEnd
    LockAll
    SetFlag FLAG_ARC2_CELESTIC_A
    Message Route210North_Text_Arc2RiftMist
    WaitABPadPress
    CloseMessage
    ReleaseAll
Route210North_Arc2RiftMistEnd:
    End

Route210North_BlackBelt:
    NPCMessage Route210North_Text_HowDoesDefogWork
    End

Route210North_ArrowSignpostCelesticTown:
    ShowArrowSign Route210North_Text_SignCelesticTown
    End

Route210North_SignboardGrandmaWilmasHouse:
    ShowLandmarkSign Route210North_Text_SignGrandmaWilmasHouse
    End

    .balign 4, 0
