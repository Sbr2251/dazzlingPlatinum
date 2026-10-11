#include "macros/scrcmd.inc"
#include "res/text/bank/route_210_north.h"


    ScriptEntry _000E
    ScriptEntry _0021
    ScriptEntry _0038
    ScriptEntry Route210North_OnTransition
    ScriptEntry Route210North_OnResume
    ScriptEntry Route210North_Arc2RiftMist
    ScriptEntryEnd

// Arc 2 (s-celestic): Route 210 North comes before Defog in the new order, so its fog is off.
// The header's OVERWORLD_WEATHER_FOG is left alone (header edits are the lead's); instead:
//  - Celestic Town, Route 210 South and this map set the Defog-active system flag on transition. It survives
//    seamless walks (it is only cleared by a warp onto a non-cave map), so a walk in from either neighbour
//    computes CLEAR weather at the map change.
//  - Warp entries (out of Grandma Wilma's house, a save loaded here) compute FOG before any script runs, so
//    OnResume (after the field's weather is set up) switches it to CLEAR with the Defog field-move command.
// FLAG_ARC2_CELESTIC_A = the rift-mist line has been shown (text-only S11 mist, at the Celestic edge).

Route210North_OnTransition:
    Defog 1
    End

Route210North_OnResume:
    ScrCmd_0C4
    End

Route210North_Arc2RiftMist:
    GoToIfSet FLAG_ARC2_CELESTIC_A, Route210North_Arc2RiftMistEnd
    LockAll
    SetFlag FLAG_ARC2_CELESTIC_A
    Message Route210North_Text_Arc2RiftMist
    WaitABXPadPress
    CloseMessage
    ReleaseAll
Route210North_Arc2RiftMistEnd:
    End

_000E:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0021:
    ShowArrowSign 1
    End

_0038:
    ShowLandmarkSign 2
    End

    .balign 4, 0
