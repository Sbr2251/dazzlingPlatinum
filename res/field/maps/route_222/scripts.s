#include "macros/scrcmd.inc"
#include "res/text/bank/route_222.h"
#include "res/field/maps/locals/route_222.h"

// Dazzling Platinum Arc 2 (s-cutaways): 2.19, Kahn's cliff (docs/arc2/cutaways.md is the caller contract).
// Route 222 is unreachable in Arc 2; the cutaway state is VAR_ARC2_PROGRESS 63 (rift-b's Skarmory calm value).
// The caller (s-route214) fades to black and does `Warp MAP_HEADER_ROUTE_222, 742, 796, DIR_NORTH` WITHOUT fading
// back in (742,796 is the camera anchor on the beach below Kahn's cliff edge at 742,794). OnResume (entry 10) hides
// the player; the on-frame scene (entry 9) fades in, plays, sets 69 and returns to Route 214 726,665 facing south.
// Night is not forced (the RTC decides); the scene is a cutaway, so it plays at any time of day.
// Flags: map-local FLAG_MAP_LOCAL_HIDE_OBSTACLE_16 = hide LOCALID_ARC2_KAHN (set again on every load, cleared only at 63).


    ScriptEntry Route222_Fisherman
    ScriptEntry Route222_RichBoy
    ScriptEntry Route222_ArrowSignpostHotelGrandLake
    ScriptEntry Route222_ArrowSignpostSunyshoreCity
    ScriptEntry Route222_SignboardPikachuFanClub
    ScriptEntry Route222_SignboardPokemonSizeContest
    ScriptEntry Route222_PolicemanThomas
    ScriptEntry Route222_OnTransition
    ScriptEntry Route222_Arc2KahnCliff
    ScriptEntry Route222_Arc2OnResume
    ScriptEntryEnd

Route222_OnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    CallIfEq VAR_ARC2_PROGRESS, 63, Route222_Arc2ShowKahn
    GetTimeOfDay VAR_MAP_LOCAL_0x00
    GoToIfInRange VAR_MAP_LOCAL_0x00, TIMEOFDAY_MORNING, TIMEOFDAY_TWILIGHT, Route222_SetPolicemanThomasNoBattle
    GoToIfInRange VAR_MAP_LOCAL_0x00, TIMEOFDAY_NIGHT, TIMEOFDAY_LATE_NIGHT, Route222_SetPolicemanThomasBattle
    End

Route222_SetPolicemanThomasNoBattle:
    ClearFlag FLAG_HIDE_ROUTE_222_POLICEMAN_THOMAS_NO_BATTLE
    SetFlag FLAG_HIDE_ROUTE_222_POLICEMAN_THOMAS
    End

Route222_SetPolicemanThomasBattle:
    ClearFlag FLAG_HIDE_ROUTE_222_POLICEMAN_THOMAS
    SetFlag FLAG_HIDE_ROUTE_222_POLICEMAN_THOMAS_NO_BATTLE
    End

Route222_RichBoy:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_RECEIVED_ROUTE_222_TM56, Route222_ExplainFling
    Message Route222_Text_IGiveTMFling
    SetVar VAR_0x8004, ITEM_TM56
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, Route222_BagIsFull
    CallCommonScript CommonScript_AddItemQuantity
    SetFlag FLAG_RECEIVED_ROUTE_222_TM56
    GoTo Route222_ExplainFling

Route222_ExplainFling:
    Message Route222_Text_ExplainFling
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route222_BagIsFull:
    CallCommonScript CommonScript_BagIsFull
    CloseMessage
    ReleaseAll
    End

Route222_Fisherman:
    NPCMessage Route222_Text_CatchingMadeMeHappy
    End

Route222_ArrowSignpostHotelGrandLake:
    ShowArrowSign Route222_Text_SignHotelGrandLake
    End

Route222_ArrowSignpostSunyshoreCity:
    ShowArrowSign Route222_Text_SignSunyshoreCity
    End

Route222_SignboardPikachuFanClub:
    ShowLandmarkSign Route222_Text_SignPikachuFanClub
    End

Route222_SignboardPokemonSizeContest:
    ShowLandmarkSign Route222_Text_SignPokemonSizeContest
    End

Route222_PolicemanThomas:
    NPCMessage Route222_Text_MoreAgitatedAtNight
    End

    .balign 4, 0

Route222_Arc2ShowKahn:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
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
    PlaySE SEQ_SE_DP_NAMI_sseq
    WaitTime 30, VAR_RESULT
    Message Route222_Text_Arc2KahnSevenYearsToday
    WaitABPadPress
    Message Route222_Text_Arc2KahnEveryoneSays
    WaitABPadPress
    Message Route222_Text_Arc2KahnThereIs
    WaitABPadPress
    Message Route222_Text_Arc2KahnPalkiaCanTakeMeThere
    WaitABPadPress
    CloseMessage
    // Kahn closes his hand over the ball
    ApplyMovement LOCALID_ARC2_KAHN, Route222_Arc2Movement_KahnCloseHand
    WaitMovement
    PlaySE SEQ_SE_DP_NAMI_sseq
    WaitTime 30, VAR_RESULT
    FadeScreenOut
    WaitFadeScreen
    SetVar VAR_ARC2_PROGRESS, 69
    Warp MAP_HEADER_ROUTE_214, 726, 665, DIR_SOUTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
Route222_Arc2Movement_KahnCloseHand:
    Delay8
    WalkOnSpotSlowSouth
    EndMovement
