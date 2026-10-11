#include "macros/scrcmd.inc"
#include "res/text/bank/route_222.h"
#include "res/field/events/events_route_222.h"

// Dazzling Platinum Arc 2 (s-cutaways): 2.19, Kahn's cliff (docs/arc2/cutaways.md is the caller contract).
// Route 222 is unreachable in Arc 2; the cutaway state is VAR_ARC2_PROGRESS 63 (rift-b's Skarmory calm value).
// The caller (s-route214) fades to black and does `Warp MAP_HEADER_ROUTE_222, 0, 742, 796, DIR_NORTH` WITHOUT fading
// back in (742,796 is the camera anchor on the beach below Kahn's cliff edge at 742,794). OnResume (entry 10) hides
// the player; the on-frame scene (entry 9) fades in, plays, sets 69 and returns to Route 214 726,665 facing south.
// Night is not forced (the RTC decides); the scene is a cutaway, so it plays at any time of day.
// Flags: map-local FLAG_UNK_0x0030 = hide LOCALID_ARC2_KAHN (set again on every load, cleared only at 63).


    ScriptEntry _00D7
    ScriptEntry _007D
    ScriptEntry _00EA
    ScriptEntry _0101
    ScriptEntry _0118
    ScriptEntry _012F
    ScriptEntry _0146
    ScriptEntry _0022
    ScriptEntry Route222_Arc2KahnCliff
    ScriptEntry Route222_Arc2OnResume
    ScriptEntryEnd

_0022:
    SetFlag FLAG_UNK_0x0030
    CallIfEq VAR_ARC2_PROGRESS, 63, Route222_Arc2ShowKahn
    GetTimeOfDay VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, 0, _0069
    GoToIfEq VAR_MAP_LOCAL_0, 1, _0069
    GoToIfEq VAR_MAP_LOCAL_0, 2, _0069
    GoToIfEq VAR_MAP_LOCAL_0, 3, _0073
    GoToIfEq VAR_MAP_LOCAL_0, 4, _0073
    End

_0069:
    ClearFlag FLAG_UNK_0x026A
    SetFlag FLAG_UNK_0x026B
    End

_0073:
    ClearFlag FLAG_UNK_0x026B
    SetFlag FLAG_UNK_0x026A
    End

_007D:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x00CE, _00C2
    Message 0
    SetVar VAR_0x8004, ITEM_TM56
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, _00CD
    GiveItemQuantity
    SetFlag FLAG_UNK_0x00CE
    GoTo _00C2

_00C2:
    Message 1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00CD:
    MessageBagIsFull
    CloseMessage
    ReleaseAll
    End

_00D7:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 2
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00EA:
    ShowArrowSign 4
    End

_0101:
    ShowArrowSign 5
    End

_0118:
    ShowLandmarkSign 6
    End

_012F:
    ShowLandmarkSign 7
    End

_0146:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 3
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0

Route222_Arc2ShowKahn:
    ClearFlag FLAG_UNK_0x0030
    Return

// OnResume (every field load, before the screen is shown): the player is not in the scene
Route222_Arc2OnResume:
    GoToIfEq VAR_ARC2_PROGRESS, 63, Route222_Arc2HidePlayer
    End

Route222_Arc2HidePlayer:
    HideObject LOCALID_PLAYER
    End

// 2.19 Cutaway: Kahn, alone at the cliff edge with an empty Poke Ball
Route222_Arc2KahnCliff:
    LockAll
    FadeScreenIn
    WaitFadeScreen
    PlayFanfare SEQ_SE_DP_NAMI
    WaitTime 30, VAR_RESULT
    Message Route222_Text_Arc2KahnSevenYearsToday
    Message Route222_Text_Arc2KahnEveryoneSays
    Message Route222_Text_Arc2KahnThereIs
    Message Route222_Text_Arc2KahnPalkiaCanTakeMeThere
    WaitABXPadPress
    CloseMessage
    // Kahn closes his hand over the ball
    ApplyMovement LOCALID_ARC2_KAHN, Route222_Arc2Movement_KahnCloseHand
    WaitMovement
    PlayFanfare SEQ_SE_DP_NAMI
    WaitTime 30, VAR_RESULT
    FadeScreenOut
    WaitFadeScreen
    SetVar VAR_ARC2_PROGRESS, 69
    Warp MAP_HEADER_ROUTE_214, 0, 726, 665, DIR_SOUTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
Route222_Arc2Movement_KahnCloseHand:
    Delay8
    WalkOnSpotSlowSouth
    EndMovement
