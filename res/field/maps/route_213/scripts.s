#include "macros/scrcmd.inc"
#include "constants/totem_battle.h"
#include "res/text/bank/route_213.h"
#include "res/field/maps/locals/route_213.h"


    ScriptEntry Route213_OnTransition
    ScriptEntry Route213_GruntM
    ScriptEntry Route213_Fisherman
    ScriptEntry Route213_Beauty
    ScriptEntry Route213_Collector
    ScriptEntry Route213_ArrowSignpostPastoriaCity
    ScriptEntry Route213_SignboardHotelGrandLake
    ScriptEntry Route213_SignboardDrFootstepsHouse
    ScriptEntry Route213_Arc2Rift
    ScriptEntry Route213_Arc2Arrive
    ScriptEntry Route213_Arc2RaidIntroTrigger
    ScriptEntry Route213_Arc2RaidStep
    ScriptEntry Route213_Arc2Looker
    ScriptEntry Route213_Arc2Ruth
    ScriptEntry Route213_Arc2Cyrus
    ScriptEntry Route213_Arc2Calm
    ScriptEntry Route213_Arc2BeachTriggerMouth
    ScriptEntry Route213_Arc2BeachTriggerOther
    ScriptEntry Route213_Arc2Psyduck
    ScriptEntryEnd

Route213_OnTransition:
    // Arc 2: the stock Galactic grunt / Looker chain (Fen Badge) is retired; FLAG_HIDE_ROUTE_213_GRUNT_M and 0x01E8 stay set
    // from the new-game script, so both stock objects stay hidden.
    Call Route213_Arc2OnTransition
    End

Route213_CheckBadge:
    CheckBadgeAcquired BADGE_ID_FEN, VAR_MAP_LOCAL_0x00
    GoToIfEq VAR_MAP_LOCAL_0x00, TRUE, Route213_CheckShowGruntM
    End

Route213_CheckShowGruntM:
    GoToIfSet FLAG_TALKED_TO_PASTORIA_CITY_GRUNT_M, Route213_ShowGruntM
    End

Route213_ShowGruntM:
    CallIfUnset FLAG_TALKED_TO_ROUTE_213_GRUNT_M, Route213_SetGruntMPositionNearPastoria
    ClearFlag FLAG_HIDE_ROUTE_213_GRUNT_M
    End

Route213_SetGruntMPositionNearPastoria:
    SetObjectEventPos LOCALID_GRUNT_M, 654, 812
    SetObjectEventDir LOCALID_GRUNT_M, DIR_EAST
    SetObjectEventMovementType LOCALID_GRUNT_M, MOVEMENT_TYPE_LOOK_EAST
    Return

Route213_GruntM:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfSet FLAG_TALKED_TO_ROUTE_213_GRUNT_M, Route213_GruntMEast
    Message Route213_Text_WeNeededEnergy
    CloseMessage
    FacePlayer
    ApplyMovement LOCALID_GRUNT_M, Route213_Movement_GruntMExclamationMark
    WaitMovement
    Message Route213_Text_YouWereEavesdropping
    CloseMessage
    GetPlayerDir VAR_0x8004
    GoToIfEq VAR_0x8004, DIR_WEST, Route213_GruntMLeaveWest
    GoToIfEq VAR_0x8004, DIR_EAST, Route213_GruntMLeaveEast
    GoTo Route213_GruntMLeaveNorthSouth
    End

Route213_GruntMLeaveNorthSouth:
    ApplyMovement LOCALID_GRUNT_M, Route213_Movement_GruntMLeaveNorthSouthEast
    ApplyMovement LOCALID_PLAYER, Route213_Movement_WatchGruntMLeave
    WaitMovement
    GoTo Route213_MoveGruntMEast
    End

Route213_GruntMLeaveEast:
    ApplyMovement LOCALID_GRUNT_M, Route213_Movement_GruntMLeaveNorthSouthEast
    WaitMovement
    GoTo Route213_MoveGruntMEast
    End

Route213_GruntMLeaveWest:
    ApplyMovement LOCALID_GRUNT_M, Route213_Movement_GruntMLeaveWest
    ApplyMovement LOCALID_PLAYER, Route213_Movement_WatchGruntMLeave
    WaitMovement
    GoTo Route213_MoveGruntMEast
    End

Route213_MoveGruntMEast:
    SetFlag FLAG_TALKED_TO_ROUTE_213_GRUNT_M
    RemoveObject LOCALID_GRUNT_M
    SetObjectEventPos LOCALID_GRUNT_M, 683, 833
    SetObjectEventDir LOCALID_GRUNT_M, DIR_EAST
    SetObjectEventMovementType LOCALID_GRUNT_M, MOVEMENT_TYPE_LOOK_EAST
    ClearFlag FLAG_HIDE_ROUTE_213_GRUNT_M
    AddObject LOCALID_GRUNT_M
    ReleaseAll
    End

Route213_GruntMEast:
    GetPlayerDir VAR_0x8004
    Message Route213_Text_BombPacksAWallop
    CloseMessage
    FacePlayer
    ApplyMovement LOCALID_GRUNT_M, Route213_Movement_GruntMExclamationMark
    WaitMovement
    Message Route213_Text_YoureAPersistentPest
    CloseMessage
    GetPlayerDir VAR_0x8004
    GoToIfEq VAR_0x8004, DIR_WEST, Route213_GruntMEastLeaveWest
    GoTo Route213_GruntMEastLeaveNorthSouthEast
    End

Route213_GruntMEastLeaveNorthSouthEast:
    ApplyMovement LOCALID_PLAYER, Route213_Movement_PlayerWatchGruntMEastLeave
    ApplyMovement LOCALID_GRUNT_M, Route213_Movement_GruntMEastLeaveNorthSouthEast
    WaitMovement
    GoTo Route213_Looker
    End

Route213_GruntMEastLeaveWest:
    ApplyMovement LOCALID_PLAYER, Route213_Movement_PlayerWatchGruntMEastLeave
    ApplyMovement LOCALID_GRUNT_M, Route213_Movement_GruntMEastLeaveWest
    WaitMovement
    GoTo Route213_Looker
    End

Route213_Looker:
    RemoveObject LOCALID_GRUNT_M
    SetFlag FLAG_ROUTE_213_GRUNT_M_LEFT
    ClearFlag FLAG_HIDE_ROUTE_213_LOOKER
    AddObject LOCALID_LOOKER
    CallCommonScript CommonScript_SetLookerBGM
    GetOverworldWeather VAR_RESULT
    CallIfEq VAR_RESULT, OVERWORLD_WEATHER_RAINING, _0261
    CallIfEq VAR_0x8004, DIR_WEST, Route213_LookerEnterWest
    CallIfEq VAR_0x8004, DIR_EAST, Route213_LookerEnterEast
    CallIfEq VAR_0x8004, DIR_NORTH, Route213_LookerEnterNorth
    CallIfEq VAR_0x8004, DIR_SOUTH, Route213_LookerEnterSouth
    Message Route213_Text_ThatIsTeamGalactic
    ApplyMovement LOCALID_LOOKER, Route213_Movement_LookerWalkOnSpotSouth
    WaitMovement
    Message Route213_Text_HowDidIMissIt
    Message Route213_Text_ThisWillNotDo
    CloseMessage
    CallIfEq VAR_0x8004, DIR_WEST, Route213_LookerLeaveWest
    CallIfEq VAR_0x8004, DIR_EAST, Route213_LookerLeaveEast
    CallIfEq VAR_0x8004, DIR_NORTH, Route213_LookerLeaveNorth
    CallIfEq VAR_0x8004, DIR_SOUTH, Route213_LookerLeaveSouth
    RemoveObject LOCALID_LOOKER
    CallCommonScript CommonScript_FadeToDefaultMusic_4
    GetOverworldWeather VAR_RESULT
    CallIfEq VAR_RESULT, OVERWORLD_WEATHER_RAINING, _0261
    ClearFlag FLAG_HIDE_GRAND_LAKE_ROUTE_213_LOBBY_LOOKER
    ClearFlag FLAG_HIDE_VALOR_LAKEFRONT_GRUNT_M
    ReleaseAll
    End

_0261:
    PlaySE SEQ_SE_DP_T_AME_sseq
    Return

Route213_LookerEnterWest:
    ApplyMovement LOCALID_LOOKER, Route213_Movement_LookerEnterWest
    ApplyMovement LOCALID_PLAYER, Route213_Movement_PlayerWatchLookerEnterNorthWestEast
    WaitMovement
    Return

Route213_LookerEnterEast:
    ApplyMovement LOCALID_LOOKER, Route213_Movement_LookerEnterEast
    ApplyMovement LOCALID_PLAYER, Route213_Movement_PlayerWatchLookerEnterNorthWestEast
    WaitMovement
    Return

Route213_LookerEnterNorth:
    ApplyMovement LOCALID_LOOKER, Route213_Movement_LookerEnterNorth
    ApplyMovement LOCALID_PLAYER, Route213_Movement_PlayerWatchLookerEnterNorthWestEast
    WaitMovement
    Return

Route213_LookerEnterSouth:
    ApplyMovement LOCALID_LOOKER, Route213_Movement_LookerEnterSouth
    ApplyMovement LOCALID_PLAYER, Route213_Movement_PlayerWatchLookerEnterSouth
    WaitMovement
    Return

Route213_LookerLeaveWest:
    ApplyMovement LOCALID_LOOKER, Route213_Movement_LookerLeaveWest
    ApplyMovement LOCALID_PLAYER, Route213_Movement_PlayerWatchLookerLeave
    WaitMovement
    Return

Route213_LookerLeaveEast:
    ApplyMovement LOCALID_LOOKER, Route213_Movement_LookerLeaveEast
    ApplyMovement LOCALID_PLAYER, Route213_Movement_PlayerWatchLookerLeave
    WaitMovement
    Return

Route213_LookerLeaveNorth:
    ApplyMovement LOCALID_LOOKER, Route213_Movement_LookerLeaveNorth
    ApplyMovement LOCALID_PLAYER, Route213_Movement_PlayerWatchLookerLeave
    WaitMovement
    Return

Route213_LookerLeaveSouth:
    ApplyMovement LOCALID_LOOKER, Route213_Movement_LookerLeaveSouth
    ApplyMovement LOCALID_PLAYER, Route213_Movement_PlayerWatchLookerLeave
    WaitMovement
    Return

    .balign 4, 0
Route213_Movement_LookerEnterEast:
    WalkFastEast 10
    WalkFastNorth 2
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
Route213_Movement_LookerEnterWest:
    WalkFastEast 10
    WalkFastNorth 2
    WalkFastEast 2
    EndMovement

    .balign 4, 0
Route213_Movement_LookerEnterSouth:
    WalkFastEast 10
    WalkFastNorth 3
    WalkFastEast
    EndMovement

    .balign 4, 0
Route213_Movement_LookerEnterNorth:
    WalkFastEast 10
    WalkFastNorth
    WalkFastEast
    EndMovement

    .balign 4, 0
Route213_Movement_LookerWalkOnSpotSouth:
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
Route213_Movement_LookerLeaveEast:
    WalkFastNorth
    WalkFastEast 10
    EndMovement

    .balign 4, 0
Route213_Movement_LookerLeaveWest:
    WalkFastNorth
    WalkFastEast 10
    EndMovement

    .balign 4, 0
Route213_Movement_LookerLeaveSouth:
    WalkFastSouth
    WalkFastEast 4
    WalkFastNorth
    WalkFastEast 6
    EndMovement

    .balign 4, 0
Route213_Movement_LookerLeaveNorth:
    WalkFastNorth 2
    WalkFastEast 10
    EndMovement

    .balign 4, 0
Route213_Movement_GruntMExclamationMark:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
Route213_Movement_GruntMLeaveNorthSouthEast:
    WalkFastEast 10
    EndMovement

    .balign 4, 0
Route213_Movement_GruntMLeaveWest:
    WalkFastSouth 2
    WalkFastEast 9
    EndMovement

    .balign 4, 0
Route213_Movement_GruntMEastLeaveNorthSouthEast:
    WalkFastEast 4
    WalkFastNorth
    WalkFastEast 6
    EndMovement

    .balign 4, 0
Route213_Movement_GruntMEastLeaveWest:
    WalkFastNorth
    WalkFastEast 10
    EndMovement

    .balign 4, 0
Route213_Movement_PlayerWatchGruntMEastLeave:
    Delay8
    FaceEast
    EndMovement

    .balign 4, 0
Route213_Movement_PlayerWatchLookerEnterNorthWestEast:
    Delay4 10
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
Route213_Movement_PlayerWatchLookerEnterSouth:
    Delay4 11
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
Route213_Movement_PlayerWatchLookerLeave:
    Delay4 3
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
Route213_Movement_WatchGruntMLeave:
    Delay8
    WalkOnSpotNormalEast
    EndMovement

Route213_Beauty:
    NPCMessage Route213_Text_RatherPoolThanSea
    End

Route213_Collector:
    NPCMessage Route213_Text_SomethingOnBigCliff
    End

Route213_Fisherman:
    NPCMessage Route213_Text_TheresAFancyHotel
    End

Route213_ArrowSignpostPastoriaCity:
    ShowArrowSign Route213_Text_SignPastoriaCity
    End

Route213_SignboardHotelGrandLake:
    ShowLandmarkSign Route213_Text_SignHotelGrandLake
    End

Route213_SignboardDrFootstepsHouse:
    ShowLandmarkSign Route213_Text_SignDrFootstepsHouse
    End

    .balign 4, 0

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 2, workstream s-raid: screenplay 2.21 (the night raid, leak L3) and 2.23 (the beach,
// Cyrus battle 3). VAR_ARC2_PROGRESS block 80-84 and 87-89 (rift-b sets 84 on the Lapras calm; s-pastoria owns
// 85-86, its 2.21a briefing sets 75 and warps here).
//
//   75        arrival: Warp MAP_HEADER_ROUTE_213, 687, 832, DIR_EAST (the beach mouth). Sets 80.
//   80        raid on: Looker blocks the corridor (689,832) until his briefing, then the stepped stealth run.
//   82        Psyduck saved, L3 asked; the Lapras rift (715,830) is open. Touching it sets 83 and warps into
//             MAP_HEADER_DW_ROUTE_213 (20,12 west). 83: the rift still warps in (no change).
//   84        (rift-b, on calm; exit warp lands at 715,831 facing south) Looker's photos line, then warp to the
//             Pastoria Pokemon Center (8,11 north) for s-pastoria's 2.22.
//   86        beach: Cyrus at the waterline; stepping onto the east beach plays 2.23. 88 battle won, 89 Cyrus gone.
//
// The raid is the Arc 1 crate-tail pattern (scripts_jubilife_city.s): the engine can't move NPCs while the player
// walks, so a coord event over the corridor and the east beach (x689-715, z823-832) runs on every player step
// while the raid is on, and each step is one beat of the two patrols' look cycle (8 beats):
//   patrol A (704,829): beats 1-4 west, 5-8 south     patrol B (710,826): beats 1-3 south, 4-8 east
// Each beat checks both cones (1 tile at range 1, 3 wide at 2-3, 5 wide at 4-6, and the 4 tiles next to the
// guard). Step budget RAID_BUDGET steps from the mouth; Looker warns once at RAID_HALF. Checkpoints: 0 = the
// mouth (688,832), 1 = the gap between the patrols (706-707,832), which also records the steps used. Spotted:
// back to the last checkpoint, steps restored to that checkpoint's count. Budget gone: back to the mouth, steps 0.
// No fail state. The frames scene starts on reaching x>=713, z828-831.
//
// Flags: no persistent flags (FLAG_ARC2_RAID_A..D, 0x0951-0x0954, are unused and free for the lead).
// Map-local hide flags (cleared on every load, recomputed in Route213_Arc2OnTransition):
//   FLAG_MAP_LOCAL_HIDE_OBSTACLE_16 stock beach trainers (Tuber Jared, Tuber Chelsea) during 75-88
//   FLAG_MAP_LOCAL_HIDE_OBSTACLE_17 Looker            FLAG_MAP_LOCAL_HIDE_OBSTACLE_18 Ruth             FLAG_MAP_LOCAL_HIDE_OBSTACLE_19 Cyrus
//   FLAG_MAP_LOCAL_HIDE_OBSTACLE_20 Garius            FLAG_MAP_LOCAL_HIDE_OBSTACLE_21 the two patrols  FLAG_MAP_LOCAL_HIDE_OBSTACLE_22 the empty frame
//   FLAG_MAP_LOCAL_HIDE_OBSTACLE_23 Psyduck           FLAG_MAP_LOCAL_HIDE_OBSTACLE_24 the Lapras rift  FLAG_MAP_LOCAL_HIDE_OBSTACLE_25 Eclipse crates (705-707,823: block the stairs gap)
// Map-local vars: _4 intro armed (coord), _5 raid on (step coord), _6 checkpoint, _7 beat, _8-_B sight scratch,
//   _C steps used, _D steps at checkpoint, _E halfway warned, _F which patrol, _10/_11 patrol A/B facing.

#define RAID_BUDGET 44
#define RAID_HALF   22
#define RAID_A_X    704
#define RAID_A_Z    829
#define RAID_B_X    710
#define RAID_B_Z    826

Route213_Arc2OnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_20
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_21
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_22
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_23
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_24
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_25
    GoToIfLt VAR_ARC2_PROGRESS, 75, Route213_Arc2OnTransitionStockTrainers
    GoToIfGt VAR_ARC2_PROGRESS, 88, Route213_Arc2OnTransitionStockTrainers
    // Raid and beach states: the beach is Eclipse's (stock trainers off, crates in the north gap)
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_25
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_22
    GoToIfLe VAR_ARC2_PROGRESS, 81, Route213_Arc2SetUpRaid
    GoToIfLe VAR_ARC2_PROGRESS, 83, Route213_Arc2SetUpRiftOpen
    GoToIfEq VAR_ARC2_PROGRESS, 84, Route213_Arc2SetUpCalm
    GoToIfGe VAR_ARC2_PROGRESS, 86, Route213_Arc2SetUpBeach
    Return

Route213_Arc2OnTransitionStockTrainers:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    Return

// 75-81: Looker in the corridor, Ruth and Cyrus at the mouth, the patrols, the frame, Psyduck and the rift
Route213_Arc2SetUpRaid:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_21
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_23
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_24
    SetObjectEventPos LOCALID_ARC2_LOOKER, 689, 832
    SetObjectEventDir LOCALID_ARC2_LOOKER, DIR_WEST
    SetObjectEventMovementType LOCALID_ARC2_LOOKER, MOVEMENT_TYPE_LOOK_WEST
    SetObjectEventPos LOCALID_ARC2_RUTH, 684, 833
    SetObjectEventDir LOCALID_ARC2_RUTH, DIR_EAST
    SetObjectEventMovementType LOCALID_ARC2_RUTH, MOVEMENT_TYPE_LOOK_EAST
    SetObjectEventPos LOCALID_ARC2_CYRUS, 685, 833
    SetObjectEventDir LOCALID_ARC2_CYRUS, DIR_EAST
    SetObjectEventMovementType LOCALID_ARC2_CYRUS, MOVEMENT_TYPE_LOOK_EAST
    SetVar VAR_MAP_LOCAL_0x04, 1
    SetVar VAR_MAP_LOCAL_0x05, 0
    SetVar VAR_MAP_LOCAL_0x10, DIR_WEST
    SetVar VAR_MAP_LOCAL_0x11, DIR_SOUTH
    Return

// 82-83: the patrols are gone; everyone stands by the frames, the Lapras rift is open
Route213_Arc2SetUpRiftOpen:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_23
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_24
    SetObjectEventPos LOCALID_ARC2_LOOKER, 714, 827
    SetObjectEventDir LOCALID_ARC2_LOOKER, DIR_SOUTH
    SetObjectEventMovementType LOCALID_ARC2_LOOKER, MOVEMENT_TYPE_LOOK_SOUTH
    SetObjectEventPos LOCALID_ARC2_RUTH, 712, 831
    SetObjectEventDir LOCALID_ARC2_RUTH, DIR_EAST
    SetObjectEventMovementType LOCALID_ARC2_RUTH, MOVEMENT_TYPE_LOOK_EAST
    SetObjectEventPos LOCALID_ARC2_CYRUS, 711, 831
    SetObjectEventDir LOCALID_ARC2_CYRUS, DIR_EAST
    SetObjectEventMovementType LOCALID_ARC2_CYRUS, MOVEMENT_TYPE_LOOK_EAST
    SetObjectEventPos LOCALID_ARC2_PSYDUCK, 715, 829
    Return

// 84: back from the rift (it closed behind the player); Looker waits beside the frames
Route213_Arc2SetUpCalm:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    SetObjectEventPos LOCALID_ARC2_LOOKER, 713, 831
    SetObjectEventDir LOCALID_ARC2_LOOKER, DIR_EAST
    SetObjectEventMovementType LOCALID_ARC2_LOOKER, MOVEMENT_TYPE_LOOK_EAST
    Return

// 86-88: Cyrus alone at the waterline
Route213_Arc2SetUpBeach:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    SetObjectEventPos LOCALID_ARC2_CYRUS, 713, 829
    SetObjectEventDir LOCALID_ARC2_CYRUS, DIR_EAST
    SetObjectEventMovementType LOCALID_ARC2_CYRUS, MOVEMENT_TYPE_LOOK_EAST
    Return

// On-frame (VAR_ARC2_PROGRESS 75): the briefing's warp lands at the mouth (687,832). Arriving any other way just
// arms the raid; Looker's coord at the mouth starts it.
Route213_Arc2Arrive:
    SetVar VAR_ARC2_PROGRESS, 80
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8004, 687, Route213_Arc2ArriveEnd
    GoToIfNe VAR_0x8005, 832, Route213_Arc2ArriveEnd
    GoTo Route213_Arc2RaidIntro
    End

Route213_Arc2ArriveEnd:
    End

// Coord (VAR_MAP_LOCAL_0x04 = 1): the mouth (688,832-833), or anywhere on the east beach (arrived by Surf)
Route213_Arc2RaidIntroTrigger:
    GoTo Route213_Arc2RaidIntro
    End

Route213_Arc2RaidIntro:
    LockAll
    SetVar VAR_MAP_LOCAL_0x04, 0
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8004, 688, Route213_Arc2RaidIntroStage
    GoToIfNe VAR_0x8005, 832, Route213_Arc2RaidIntroStage
    GoTo Route213_Arc2RaidIntroTalk
    End

Route213_Arc2RaidIntroStage:
    FadeScreenOut
    WaitFadeScreen
    SetPosition LOCALID_PLAYER, 688, 0, 832, DIR_EAST
    WaitTime 4, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
Route213_Arc2RaidIntroTalk:
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceEast
    ApplyMovement LOCALID_ARC2_LOOKER, Route213_Arc2Movement_FaceWest
    WaitMovement
    Message Route213_Text_Arc2RaidPatrols
    WaitABPadPress
    CloseMessage
    // He slips ahead into the dark; from here he moves on his own
    ApplyMovement LOCALID_ARC2_LOOKER, Route213_Arc2Movement_LookerSlipAhead
    WaitMovement
    RemoveObject LOCALID_ARC2_LOOKER
    Call Route213_Arc2RaidReset
    SetVar VAR_MAP_LOCAL_0x06, 0
    SetVar VAR_MAP_LOCAL_0x0C, 0
    SetVar VAR_MAP_LOCAL_0x0D, 0
    SetVar VAR_MAP_LOCAL_0x0E, 0
    SetVar VAR_MAP_LOCAL_0x05, 1
    ReleaseAll
    End

// Patrols back to beat 0 (A west, B south)
Route213_Arc2RaidReset:
    SetVar VAR_MAP_LOCAL_0x07, 0
    ApplyMovement LOCALID_ARC2_GRUNT_A, Route213_Arc2Movement_FaceWest
    ApplyMovement LOCALID_ARC2_GRUNT_B, Route213_Arc2Movement_FaceSouth
    WaitMovement
    SetVar VAR_MAP_LOCAL_0x10, DIR_WEST
    SetVar VAR_MAP_LOCAL_0x11, DIR_SOUTH
    Return

// Coord over x689-715, z823-832 while the raid is on: one beat per step
Route213_Arc2RaidStep:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    AddVar VAR_MAP_LOCAL_0x0C, 1
    GoToIfGt VAR_MAP_LOCAL_0x0C, RAID_BUDGET, Route213_Arc2RaidTooSlow
    CallIfEq VAR_MAP_LOCAL_0x0C, RAID_HALF, Route213_Arc2RaidHalfway
    AddVar VAR_MAP_LOCAL_0x07, 1
    CallIfGe VAR_MAP_LOCAL_0x07, 9, Route213_Arc2RaidWrapBeat
    Call Route213_Arc2RaidTurnPatrols
    // Patrol A
    SetVar VAR_MAP_LOCAL_0x0F, 1
    SetVar VAR_0x8006, RAID_A_X
    SetVar VAR_0x8007, RAID_A_Z
    SetVar VAR_0x8008, VAR_MAP_LOCAL_0x10
    Call Route213_Arc2CheckSight
    GoToIfEq VAR_RESULT, 1, Route213_Arc2RaidCaught
    // Patrol B
    SetVar VAR_MAP_LOCAL_0x0F, 2
    SetVar VAR_0x8006, RAID_B_X
    SetVar VAR_0x8007, RAID_B_Z
    SetVar VAR_0x8008, VAR_MAP_LOCAL_0x11
    Call Route213_Arc2CheckSight
    GoToIfEq VAR_RESULT, 1, Route213_Arc2RaidCaught
    // The frames
    GoToIfLt VAR_0x8004, 713, Route213_Arc2RaidStepCheckpoint
    GoToIfInRange VAR_0x8005, 828, 831, Route213_Arc2Frames
Route213_Arc2RaidStepCheckpoint:
    GoToIfNe VAR_MAP_LOCAL_0x06, 0, Route213_Arc2RaidStepEnd
    GoToIfNe VAR_0x8005, 832, Route213_Arc2RaidStepEnd
    GoToIfInRange VAR_0x8004, 706, 707, Route213_Arc2RaidCheckpoint1
Route213_Arc2RaidStepEnd:
    End

Route213_Arc2RaidCheckpoint1:
    SetVar VAR_MAP_LOCAL_0x06, 1
    SetVar VAR_MAP_LOCAL_0x0D, VAR_MAP_LOCAL_0x0C
    End

Route213_Arc2RaidWrapBeat:
    SetVar VAR_MAP_LOCAL_0x07, 1
    Return

Route213_Arc2RaidHalfway:
    GoToIfNe VAR_MAP_LOCAL_0x0E, 0, Route213_Arc2Return
    SetVar VAR_MAP_LOCAL_0x0E, 1
    LockAll
    Message Route213_Text_Arc2RaidHalfway
    WaitABPadPress
    CloseMessage
    ReleaseAll
    Return

Route213_Arc2Return:
    Return

// A: beats 1-4 west, 5-8 south. B: beats 1-3 south, 4-8 east. Each turns only when its facing changes.
Route213_Arc2RaidTurnPatrols:
    SetVar VAR_0x8008, DIR_WEST
    CallIfGe VAR_MAP_LOCAL_0x07, 5, Route213_Arc2Set8008South
    CallIfNe VAR_MAP_LOCAL_0x10, VAR_0x8008, Route213_Arc2TurnA
    SetVar VAR_0x8008, DIR_SOUTH
    CallIfGe VAR_MAP_LOCAL_0x07, 4, Route213_Arc2Set8008East
    CallIfNe VAR_MAP_LOCAL_0x11, VAR_0x8008, Route213_Arc2TurnB
    Return

Route213_Arc2Set8008South:
    SetVar VAR_0x8008, DIR_SOUTH
    Return

Route213_Arc2Set8008East:
    SetVar VAR_0x8008, DIR_EAST
    Return

Route213_Arc2TurnA:
    SetVar VAR_MAP_LOCAL_0x10, VAR_0x8008
    GoToIfEq VAR_0x8008, DIR_SOUTH, Route213_Arc2TurnASouth
    ApplyMovement LOCALID_ARC2_GRUNT_A, Route213_Arc2Movement_FaceWest
    WaitMovement
    Return

Route213_Arc2TurnASouth:
    ApplyMovement LOCALID_ARC2_GRUNT_A, Route213_Arc2Movement_FaceSouth
    WaitMovement
    Return

Route213_Arc2TurnB:
    SetVar VAR_MAP_LOCAL_0x11, VAR_0x8008
    GoToIfEq VAR_0x8008, DIR_EAST, Route213_Arc2TurnBEast
    ApplyMovement LOCALID_ARC2_GRUNT_B, Route213_Arc2Movement_FaceSouth
    WaitMovement
    Return

Route213_Arc2TurnBEast:
    ApplyMovement LOCALID_ARC2_GRUNT_B, Route213_Arc2Movement_FaceEast
    WaitMovement
    Return

// In: VAR_0x8004/0x8005 player, VAR_0x8006/0x8007 guard, VAR_0x8008 his facing. Out: VAR_RESULT 1 if seen;
// VAR_0x8009/0x800A = |dx|/|dz|; VAR_MAP_LOCAL_0x08/_9 = sign of dx/dz (0 west/north of him, 1 same, 2 east/south).
// Same cone as the Arc 1 crate tail.
Route213_Arc2CheckSight:
    SetVar VAR_RESULT, 0
    SetVar VAR_MAP_LOCAL_0x08, 1
    SetVar VAR_0x8009, 0
    GoToIfEq VAR_0x8004, VAR_0x8006, Route213_Arc2SightDZ
    GoToIfLt VAR_0x8004, VAR_0x8006, Route213_Arc2SightWest
    SetVar VAR_MAP_LOCAL_0x08, 2
    SetVar VAR_0x8009, VAR_0x8004
    SubVar VAR_0x8009, VAR_0x8006
    GoTo Route213_Arc2SightDZ
    End

Route213_Arc2SightWest:
    SetVar VAR_MAP_LOCAL_0x08, 0
    SetVar VAR_0x8009, VAR_0x8006
    SubVar VAR_0x8009, VAR_0x8004
    GoTo Route213_Arc2SightDZ
    End

Route213_Arc2SightDZ:
    SetVar VAR_MAP_LOCAL_0x09, 1
    SetVar VAR_0x800A, 0
    GoToIfEq VAR_0x8005, VAR_0x8007, Route213_Arc2SightAdjacent
    GoToIfLt VAR_0x8005, VAR_0x8007, Route213_Arc2SightNorth
    SetVar VAR_MAP_LOCAL_0x09, 2
    SetVar VAR_0x800A, VAR_0x8005
    SubVar VAR_0x800A, VAR_0x8007
    GoTo Route213_Arc2SightAdjacent
    End

Route213_Arc2SightNorth:
    SetVar VAR_MAP_LOCAL_0x09, 0
    SetVar VAR_0x800A, VAR_0x8007
    SubVar VAR_0x800A, VAR_0x8005
    GoTo Route213_Arc2SightAdjacent
    End

Route213_Arc2SightAdjacent:
    SetVar VAR_MAP_LOCAL_0x0B, VAR_0x8009
    AddVar VAR_MAP_LOCAL_0x0B, VAR_0x800A
    GoToIfLe VAR_MAP_LOCAL_0x0B, 1, Route213_Arc2SightSeen
    GoToIfEq VAR_0x8008, DIR_NORTH, Route213_Arc2SightFaceNorth
    GoToIfEq VAR_0x8008, DIR_SOUTH, Route213_Arc2SightFaceSouth
    GoToIfEq VAR_0x8008, DIR_WEST, Route213_Arc2SightFaceWest
    GoTo Route213_Arc2SightFaceEast
    End

Route213_Arc2SightFaceNorth:
    GoToIfNe VAR_MAP_LOCAL_0x09, 0, Route213_Arc2SightEnd
    GoTo Route213_Arc2SightAlongZ
    End

Route213_Arc2SightFaceSouth:
    GoToIfNe VAR_MAP_LOCAL_0x09, 2, Route213_Arc2SightEnd
    GoTo Route213_Arc2SightAlongZ
    End

Route213_Arc2SightFaceWest:
    GoToIfNe VAR_MAP_LOCAL_0x08, 0, Route213_Arc2SightEnd
    GoTo Route213_Arc2SightAlongX
    End

Route213_Arc2SightFaceEast:
    GoToIfNe VAR_MAP_LOCAL_0x08, 2, Route213_Arc2SightEnd
    GoTo Route213_Arc2SightAlongX
    End

Route213_Arc2SightAlongZ:
    SetVar VAR_MAP_LOCAL_0x0A, VAR_0x800A
    SetVar VAR_MAP_LOCAL_0x0B, VAR_0x8009
    GoTo Route213_Arc2SightCone
    End

Route213_Arc2SightAlongX:
    SetVar VAR_MAP_LOCAL_0x0A, VAR_0x8009
    SetVar VAR_MAP_LOCAL_0x0B, VAR_0x800A
    GoTo Route213_Arc2SightCone
    End

Route213_Arc2SightCone:
    GoToIfGt VAR_MAP_LOCAL_0x0A, 6, Route213_Arc2SightEnd
    GoToIfEq VAR_MAP_LOCAL_0x0A, 1, Route213_Arc2SightWidth0
    GoToIfLe VAR_MAP_LOCAL_0x0A, 3, Route213_Arc2SightWidth1
    GoToIfLe VAR_MAP_LOCAL_0x0B, 2, Route213_Arc2SightSeen
    GoTo Route213_Arc2SightEnd
    End

Route213_Arc2SightWidth0:
    GoToIfEq VAR_MAP_LOCAL_0x0B, 0, Route213_Arc2SightSeen
    GoTo Route213_Arc2SightEnd
    End

Route213_Arc2SightWidth1:
    GoToIfLe VAR_MAP_LOCAL_0x0B, 1, Route213_Arc2SightSeen
    GoTo Route213_Arc2SightEnd
    End

Route213_Arc2SightSeen:
    SetVar VAR_RESULT, 1
Route213_Arc2SightEnd:
    Return

// Spotted: the patrol turns to the player, then back to the last checkpoint (no fail state)
Route213_Arc2RaidCaught:
    LockAll
    GoToIfEq VAR_MAP_LOCAL_0x0F, 2, Route213_Arc2RaidCaughtB
    Call Route213_Arc2FacePlayerA
    ApplyMovement LOCALID_ARC2_GRUNT_A, Route213_Arc2Movement_Notice
    WaitMovement
    GoTo Route213_Arc2RaidCaughtMessage
    End

Route213_Arc2RaidCaughtB:
    Call Route213_Arc2FacePlayerB
    ApplyMovement LOCALID_ARC2_GRUNT_B, Route213_Arc2Movement_Notice
    WaitMovement
Route213_Arc2RaidCaughtMessage:
    Message Route213_Text_Arc2RaidSpotted
    WaitABPadPress
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    CallIfEq VAR_MAP_LOCAL_0x06, 0, Route213_Arc2Checkpoint0
    CallIfEq VAR_MAP_LOCAL_0x06, 1, Route213_Arc2Checkpoint1
    SetVar VAR_MAP_LOCAL_0x0C, VAR_MAP_LOCAL_0x0D
    Call Route213_Arc2RaidReset
    WaitTime 10, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    Message Route213_Text_Arc2RaidAgain
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

// Out of steps: Looker calls it, back to the mouth with the whole budget
Route213_Arc2RaidTooSlow:
    LockAll
    Message Route213_Text_Arc2RaidTooSlow
    WaitABPadPress
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    Call Route213_Arc2Checkpoint0
    SetVar VAR_MAP_LOCAL_0x06, 0
    SetVar VAR_MAP_LOCAL_0x0C, 0
    SetVar VAR_MAP_LOCAL_0x0D, 0
    SetVar VAR_MAP_LOCAL_0x0E, 0
    Call Route213_Arc2RaidReset
    WaitTime 10, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

Route213_Arc2Checkpoint0:
    SetPosition LOCALID_PLAYER, 688, 0, 832, DIR_EAST
    Return

Route213_Arc2Checkpoint1:
    SetPosition LOCALID_PLAYER, 706, 0, 832, DIR_EAST
    Return

// Uses the offsets the sight check left: the larger axis wins
Route213_Arc2FacePlayerA:
    GoToIfLt VAR_0x8009, VAR_0x800A, Route213_Arc2FacePlayerAZ
    GoToIfEq VAR_MAP_LOCAL_0x08, 0, Route213_Arc2FacePlayerAWest
    ApplyMovement LOCALID_ARC2_GRUNT_A, Route213_Arc2Movement_FaceEast
    WaitMovement
    Return

Route213_Arc2FacePlayerAWest:
    ApplyMovement LOCALID_ARC2_GRUNT_A, Route213_Arc2Movement_FaceWest
    WaitMovement
    Return

Route213_Arc2FacePlayerAZ:
    GoToIfEq VAR_MAP_LOCAL_0x09, 0, Route213_Arc2FacePlayerANorth
    ApplyMovement LOCALID_ARC2_GRUNT_A, Route213_Arc2Movement_FaceSouth
    WaitMovement
    Return

Route213_Arc2FacePlayerANorth:
    ApplyMovement LOCALID_ARC2_GRUNT_A, Route213_Arc2Movement_FaceNorth
    WaitMovement
    Return

Route213_Arc2FacePlayerB:
    GoToIfLt VAR_0x8009, VAR_0x800A, Route213_Arc2FacePlayerBZ
    GoToIfEq VAR_MAP_LOCAL_0x08, 0, Route213_Arc2FacePlayerBWest
    ApplyMovement LOCALID_ARC2_GRUNT_B, Route213_Arc2Movement_FaceEast
    WaitMovement
    Return

Route213_Arc2FacePlayerBWest:
    ApplyMovement LOCALID_ARC2_GRUNT_B, Route213_Arc2Movement_FaceWest
    WaitMovement
    Return

Route213_Arc2FacePlayerBZ:
    GoToIfEq VAR_MAP_LOCAL_0x09, 0, Route213_Arc2FacePlayerBNorth
    ApplyMovement LOCALID_ARC2_GRUNT_B, Route213_Arc2Movement_FaceSouth
    WaitMovement
    Return

Route213_Arc2FacePlayerBNorth:
    ApplyMovement LOCALID_ARC2_GRUNT_B, Route213_Arc2Movement_FaceNorth
    WaitMovement
    Return

// The frames: Psyduck hangs in one, the other is already a rift. Ruth and Cyrus run in; the patrols turn.
Route213_Arc2Frames:
    LockAll
    SetVar VAR_MAP_LOCAL_0x05, 0
    FadeScreenOut
    WaitFadeScreen
    SetPosition LOCALID_PLAYER, 714, 0, 828, DIR_EAST
    SetObjectEventPos LOCALID_ARC2_LOOKER, 714, 827
    SetObjectEventDir LOCALID_ARC2_LOOKER, DIR_EAST
    SetObjectEventMovementType LOCALID_ARC2_LOOKER, MOVEMENT_TYPE_LOOK_EAST
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    AddObject LOCALID_ARC2_LOOKER
    // Ruth and Cyrus come from the mouth
    RemoveObject LOCALID_ARC2_RUTH
    RemoveObject LOCALID_ARC2_CYRUS
    SetObjectEventPos LOCALID_ARC2_RUTH, 700, 832
    SetObjectEventDir LOCALID_ARC2_RUTH, DIR_EAST
    SetObjectEventPos LOCALID_ARC2_CYRUS, 699, 832
    SetObjectEventDir LOCALID_ARC2_CYRUS, DIR_EAST
    SetVar VAR_MAP_LOCAL_0x10, DIR_WEST
    ApplyMovement LOCALID_ARC2_GRUNT_A, Route213_Arc2Movement_FaceWest
    ApplyMovement LOCALID_ARC2_GRUNT_B, Route213_Arc2Movement_FaceSouth
    WaitMovement
    WaitTime 4, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    // The empty frame screams
    PlayCry SPECIES_LAPRAS
    ApplyMovement LOCALID_ARC2_RIFT, Route213_Arc2Movement_Shudder
    WaitMovement
    WaitCry
    PlayCry SPECIES_PSYDUCK
    WaitCry
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    AddObject LOCALID_ARC2_RUTH
    AddObject LOCALID_ARC2_CYRUS
    ApplyMovement LOCALID_ARC2_RUTH, Route213_Arc2Movement_RuthRunIn
    ApplyMovement LOCALID_ARC2_CYRUS, Route213_Arc2Movement_CyrusRunIn
    WaitMovement
    Message Route213_Text_Arc2RaidTearing
    WaitABPadPress
    CloseMessage
    // Two guards turn
    ApplyMovement LOCALID_ARC2_GRUNT_B, Route213_Arc2Movement_Notice
    WaitMovement
    ApplyMovement LOCALID_ARC2_GRUNT_B, Route213_Arc2Movement_GruntBApproach
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceWest
    WaitMovement
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_ARC2_11
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route213_Arc2LostBattle
    ApplyMovement LOCALID_ARC2_GRUNT_B, Route213_Arc2Movement_GruntFlee
    WaitMovement
    RemoveObject LOCALID_ARC2_GRUNT_B
    ApplyMovement LOCALID_ARC2_GRUNT_A, Route213_Arc2Movement_Notice
    WaitMovement
    ApplyMovement LOCALID_ARC2_GRUNT_A, Route213_Arc2Movement_GruntAApproach
    WaitMovement
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_ARC2_12
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route213_Arc2LostBattle
    ApplyMovement LOCALID_ARC2_GRUNT_A, Route213_Arc2Movement_GruntFlee
    WaitMovement
    RemoveObject LOCALID_ARC2_GRUNT_A
    // Looker and the player cut the Psyduck free as the air around it snaps shut
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceEast
    ApplyMovement LOCALID_ARC2_LOOKER, Route213_Arc2Movement_FaceEast
    WaitMovement
    PlaySE SEQ_SE_PL_SYUWA_sseq
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    ApplyMovement LOCALID_ARC2_PSYDUCK, Route213_Arc2Movement_PsyduckDrop
    WaitMovement
    PlayCry SPECIES_PSYDUCK
    WaitCry
    // The other rift stays open; something huge moves on the far side
    WaitTime 20, VAR_RESULT
    PlayCry SPECIES_LAPRAS
    ApplyMovement LOCALID_ARC2_RIFT, Route213_Arc2Movement_Shudder
    WaitMovement
    WaitCry
    ApplyMovement LOCALID_ARC2_LOOKER, Route213_Arc2Movement_FaceWest
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceNorth
    WaitMovement
    Message Route213_Text_Arc2RaidTheyKnew
    WaitABPadPress
    CloseMessage
    Message Route213_Text_Arc2RaidSomeoneTold
    WaitABPadPress
    CloseMessage
    // Silence. Nobody looks at anybody.
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceSouth
    ApplyMovement LOCALID_ARC2_LOOKER, Route213_Arc2Movement_FaceSouth
    ApplyMovement LOCALID_ARC2_RUTH, Route213_Arc2Movement_FaceSouth
    ApplyMovement LOCALID_ARC2_CYRUS, Route213_Arc2Movement_FaceSouth
    WaitMovement
    WaitTime 60, VAR_RESULT
    Message Route213_Text_Arc2RaidUnderstand
    WaitABPadPress
    CloseMessage
    // Ledger L3: Looker's own prompt, the shared menu, one neutral reaction each
    ApplyMovement LOCALID_ARC2_LOOKER, Route213_Arc2Movement_FaceSouth
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceNorth
    WaitMovement
    Message Route213_Text_Arc2RaidLedgerAsk
    InitLocalTextMenu 31, 5, 0, VAR_RESULT
    SetMenuXOriginToRight
    AddMenuEntryImm Route213_Text_Arc2MenuCyrus, 0
    AddMenuEntryImm Route213_Text_Arc2MenuGarius, 1
    AddMenuEntryImm Route213_Text_Arc2MenuRuth, 2
    AddMenuEntryImm Route213_Text_Arc2MenuBadLuck, 3
    ShowMenu
    CloseMessage
    AddVar VAR_ARC2_SUSPECT, 2048
    GoToIfEq VAR_RESULT, 0, Route213_Arc2LedgerCyrus
    GoToIfEq VAR_RESULT, 1, Route213_Arc2LedgerGarius
    GoToIfEq VAR_RESULT, 2, Route213_Arc2LedgerRuth
    // Bad luck, and B
    AddVar VAR_ARC2_SUSPECT, 192
    Message Route213_Text_Arc2RaidPickBadLuck
    GoTo Route213_Arc2LedgerDone
    End

Route213_Arc2LedgerCyrus:
    Message Route213_Text_Arc2RaidPickCyrus
    GoTo Route213_Arc2LedgerDone
    End

Route213_Arc2LedgerGarius:
    AddVar VAR_ARC2_SUSPECT, 64
    Message Route213_Text_Arc2RaidPickGarius
    GoTo Route213_Arc2LedgerDone
    End

Route213_Arc2LedgerRuth:
    AddVar VAR_ARC2_SUSPECT, 128
    Message Route213_Text_Arc2RaidPickRuth
    GoTo Route213_Arc2LedgerDone
    End

Route213_Arc2LedgerDone:
    WaitABPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 82
    ApplyMovement LOCALID_ARC2_CYRUS, Route213_Arc2Movement_FaceEast
    WaitMovement
    Message Route213_Text_Arc2RaidCyrusGoNow
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

Route213_Arc2LostBattle:
    BlackOutFromBattle
    ReleaseAll
    End

// The Lapras rift: open at 82-83 (touching it sets 83 and enters MAP_HEADER_DW_ROUTE_213)
Route213_Arc2Rift:
    LockAll
    GoToIfLt VAR_ARC2_PROGRESS, 82, Route213_Arc2RiftShut
    GoToIfGt VAR_ARC2_PROGRESS, 83, Route213_Arc2RiftShut
    PlayCry SPECIES_LAPRAS
    WaitCry
    SetVar VAR_ARC2_PROGRESS, 83
    PlaySE SEQ_SE_PL_SYUWA_sseq
    FadeScreenOut
    WaitFadeScreen
    DoDWWarp
    ReturnToField
    Warp MAP_HEADER_DW_ROUTE_213, 20, 12, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

// Before the Psyduck is free the rift only screams
Route213_Arc2RiftShut:
    PlayCry SPECIES_LAPRAS
    WaitCry
    ReleaseAll
    End

Route213_Arc2Looker:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message Route213_Text_Arc2RaidLookerWait
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

Route213_Arc2Ruth:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfGe VAR_ARC2_PROGRESS, 82, Route213_Arc2RuthRift
    Message Route213_Text_Arc2RaidMouthRuth
    GoTo Route213_Arc2TalkEnd
    End

Route213_Arc2RuthRift:
    Message Route213_Text_Arc2RaidRuthWait
    GoTo Route213_Arc2TalkEnd
    End

Route213_Arc2Cyrus:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfGe VAR_ARC2_PROGRESS, 86, Route213_Arc2CyrusBeach
    GoToIfGe VAR_ARC2_PROGRESS, 82, Route213_Arc2CyrusRift
    Message Route213_Text_Arc2RaidMouthCyrus
    GoTo Route213_Arc2TalkEnd
    End

Route213_Arc2CyrusRift:
    Message Route213_Text_Arc2RaidCyrusGoNow
    GoTo Route213_Arc2TalkEnd
    End

// (unreachable in play: the beach scene starts before the player can reach him)
Route213_Arc2CyrusBeach:
    Message Route213_Text_Arc2RaidMouthCyrus
    GoTo Route213_Arc2TalkEnd
    End

Route213_Arc2TalkEnd:
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

Route213_Arc2Psyduck:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    PlayCry SPECIES_PSYDUCK
    WaitCry
    ReleaseAll
    End

// On-frame (VAR_ARC2_PROGRESS 84): back from the Drowned Lake, Looker has his proof. Then the Pastoria Center (2.22).
Route213_Arc2Calm:
    LockAll
    ApplyMovement LOCALID_ARC2_LOOKER, Route213_Arc2Movement_LookerStepEast
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceWest
    WaitMovement
    Message Route213_Text_Arc2RaidPhotos
    WaitABPadPress
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_PASTORIA_CITY_POKECENTER_1F, 8, 11, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

// 2.23: coord at the mouth of the east beach (700,832), VAR_ARC2_PROGRESS 86
Route213_Arc2BeachTriggerMouth:
    LockAll
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_StepEast
    WaitMovement
    GoTo Route213_Arc2Beach
    End

// Same scene for a player who reached the beach some other way (Surf): staged at the mouth
Route213_Arc2BeachTriggerOther:
    LockAll
    FadeScreenOut
    WaitFadeScreen
    SetPosition LOCALID_PLAYER, 701, 0, 832, DIR_EAST
    WaitTime 4, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    GoTo Route213_Arc2Beach
    End

Route213_Arc2Beach:
    // Garius walks up beside the player
    SetObjectEventPos LOCALID_ARC2_GARIUS, 691, 832
    SetObjectEventDir LOCALID_ARC2_GARIUS, DIR_EAST
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_20
    AddObject LOCALID_ARC2_GARIUS
    ApplyMovement LOCALID_ARC2_GARIUS, Route213_Arc2Movement_GariusWalkUp
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceNorth
    WaitMovement
    BufferRivalName 1
    Call Route213_Arc2CountLedger
    Call Route213_Arc2GariusOpening
    WaitABPadPress
    CloseMessage
    BufferRivalName 1
    Message Route213_Text_Arc2BeachEveryTime
    WaitABPadPress
    CloseMessage
    Message Route213_Text_Arc2BeachNothing
    WaitABPadPress
    CloseMessage
    Message Route213_Text_Arc2BeachProveIt
    WaitABPadPress
    CloseMessage
    // The player walks to Cyrus; he turns before the player reaches him
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_PlayerToCyrus1
    WaitMovement
    ApplyMovement LOCALID_ARC2_CYRUS, Route213_Arc2Movement_FaceWest
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_PlayerToCyrus2
    WaitMovement
    Message Route213_Text_Arc2BeachCyrusLook
    WaitABPadPress
    CloseMessage
    // Polish #6: the player's call. Yes is recorded in VAR_ARC2_CHOICES bit 4 (+16) only once the battle is won
    // (a loss blacks out and replays the scene, so the bit can't be added twice). VAR_MAP_LOCAL_0x1A holds the answer.
    Message Route213_Text_Arc2BeachBattlePrompt
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, Route213_Arc2BeachBattleYes
    SetVar VAR_MAP_LOCAL_0x1A, 0
    BufferRivalName 1
    Message Route213_Text_Arc2BeachGariusSayIt
    WaitABPadPress
    CloseMessage
    Message Route213_Text_Arc2BeachCyrusJudge
    WaitABPadPress
    CloseMessage
    GoTo Route213_Arc2BeachBattle
    End

Route213_Arc2BeachBattleYes:
    SetVar VAR_MAP_LOCAL_0x1A, 1
    Message Route213_Text_Arc2BeachCyrusDoneWords
    WaitABPadPress
    CloseMessage
Route213_Arc2BeachBattle:
    Call Route213_Arc2SetCyrusTeam
    StartTrainerBattle VAR_0x8004
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route213_Arc2LostBattle
    CallIfEq VAR_MAP_LOCAL_0x1A, 1, Route213_Arc2BeachRecordYes
    SetVar VAR_ARC2_PROGRESS, 88
    Message Route213_Text_Arc2BeachCyrusWait
    WaitABPadPress
    CloseMessage
    Message Route213_Text_Arc2BeachCyrusAlone
    WaitABPadPress
    CloseMessage
    // Cyrus walks off west
    ApplyMovement LOCALID_ARC2_CYRUS, Route213_Arc2Movement_CyrusLeave
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_WatchSouthWest
    WaitMovement
    RemoveObject LOCALID_ARC2_CYRUS
    // Ruth comes down the beach
    SetObjectEventPos LOCALID_ARC2_RUTH, 695, 832
    SetObjectEventDir LOCALID_ARC2_RUTH, DIR_EAST
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    AddObject LOCALID_ARC2_RUTH
    ApplyMovement LOCALID_ARC2_RUTH, Route213_Arc2Movement_RuthComeDown
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceWest
    WaitMovement
    Message Route213_Text_Arc2BeachRuth
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC2_RUTH, Route213_Arc2Movement_RuthLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_RUTH
    // Garius leaves without a word
    ApplyMovement LOCALID_ARC2_GARIUS, Route213_Arc2Movement_GariusLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_GARIUS
    SetVar VAR_ARC2_PROGRESS, 89
    ReleaseAll
    End

Route213_Arc2BeachRecordYes:
    AddVar VAR_ARC2_CHOICES, 16
    Return

// TRAINER_CYRUS_ARC2_3_<player's starter> into VAR_0x8004
Route213_Arc2SetCyrusTeam:
    GetPlayerStarterSpecies VAR_RESULT
    SetVar VAR_0x8004, TRAINER_CYRUS_ARC2_3_CHIMCHAR
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, Route213_Arc2Return
    SetVar VAR_0x8004, TRAINER_CYRUS_ARC2_3_PIPLUP
    GoToIfEq VAR_RESULT, SPECIES_PIPLUP, Route213_Arc2Return
    SetVar VAR_0x8004, TRAINER_CYRUS_ARC2_3_TURTWIG
    Return

// The ledger decode (screenplay_v2 "Reading it"): VAR_ARC2_SUSPECT copied to VAR_0x8008, the answered bits peeled
// off (recorded in VAR_MAP_LOCAL_0x12-15 for L3-L0), then each leak's pick peeled from the top. Picks are counted
// into VAR_0x8004 Cyrus, 0x8005 Garius, 0x8006 Ruth, 0x8007 Bad luck; a leak that was never answered counts for
// nobody. (Normal play answers all four.)
Route213_Arc2CountLedger:
    SetVar VAR_0x8004, 0
    SetVar VAR_0x8005, 0
    SetVar VAR_0x8006, 0
    SetVar VAR_0x8007, 0
    SetVar VAR_0x8008, VAR_ARC2_SUSPECT
    SetVar VAR_MAP_LOCAL_0x12, 0
    SetVar VAR_MAP_LOCAL_0x13, 0
    SetVar VAR_MAP_LOCAL_0x14, 0
    SetVar VAR_MAP_LOCAL_0x15, 0
    CallIfGe VAR_0x8008, 2048, Route213_Arc2Answered3
    CallIfGe VAR_0x8008, 1024, Route213_Arc2Answered2
    CallIfGe VAR_0x8008, 512, Route213_Arc2Answered1
    CallIfGe VAR_0x8008, 256, Route213_Arc2Answered0
    // L3: 64 per step
    SetVar VAR_MAP_LOCAL_0x16, 64
    SetVar VAR_MAP_LOCAL_0x17, VAR_MAP_LOCAL_0x12
    Call Route213_Arc2PeelLeak
    // L2: 16
    SetVar VAR_MAP_LOCAL_0x16, 16
    SetVar VAR_MAP_LOCAL_0x17, VAR_MAP_LOCAL_0x13
    Call Route213_Arc2PeelLeak
    // L1: 4
    SetVar VAR_MAP_LOCAL_0x16, 4
    SetVar VAR_MAP_LOCAL_0x17, VAR_MAP_LOCAL_0x14
    Call Route213_Arc2PeelLeak
    // L0: 1
    SetVar VAR_MAP_LOCAL_0x16, 1
    SetVar VAR_MAP_LOCAL_0x17, VAR_MAP_LOCAL_0x15
    Call Route213_Arc2PeelLeak
    Return

Route213_Arc2Answered3:
    SubVar VAR_0x8008, 2048
    SetVar VAR_MAP_LOCAL_0x12, 1
    Return

Route213_Arc2Answered2:
    SubVar VAR_0x8008, 1024
    SetVar VAR_MAP_LOCAL_0x13, 1
    Return

Route213_Arc2Answered1:
    SubVar VAR_0x8008, 512
    SetVar VAR_MAP_LOCAL_0x14, 1
    Return

Route213_Arc2Answered0:
    SubVar VAR_0x8008, 256
    SetVar VAR_MAP_LOCAL_0x15, 1
    Return

// In: VAR_MAP_LOCAL_0x16 = the leak's unit (64/16/4/1), VAR_MAP_LOCAL_0x17 = answered. Peels 3, 2 or 1 units off
// VAR_0x8008 (Bad luck, Ruth, Garius; none = Cyrus) and counts the pick if the leak was answered.
Route213_Arc2PeelLeak:
    SetVar VAR_MAP_LOCAL_0x18, VAR_MAP_LOCAL_0x16
    AddVar VAR_MAP_LOCAL_0x18, VAR_MAP_LOCAL_0x16
    SetVar VAR_MAP_LOCAL_0x19, VAR_MAP_LOCAL_0x18
    AddVar VAR_MAP_LOCAL_0x19, VAR_MAP_LOCAL_0x16
    // _16 = 1 unit, _18 = 2 units, _19 = 3 units
    GoToIfGe VAR_0x8008, VAR_MAP_LOCAL_0x19, Route213_Arc2PeelBadLuck
    GoToIfGe VAR_0x8008, VAR_MAP_LOCAL_0x18, Route213_Arc2PeelRuth
    GoToIfGe VAR_0x8008, VAR_MAP_LOCAL_0x16, Route213_Arc2PeelGarius
    GoToIfEq VAR_MAP_LOCAL_0x17, 0, Route213_Arc2Return
    AddVar VAR_0x8004, 1
    Return

Route213_Arc2PeelBadLuck:
    SubVar VAR_0x8008, VAR_MAP_LOCAL_0x19
    GoToIfEq VAR_MAP_LOCAL_0x17, 0, Route213_Arc2Return
    AddVar VAR_0x8007, 1
    Return

Route213_Arc2PeelRuth:
    SubVar VAR_0x8008, VAR_MAP_LOCAL_0x18
    GoToIfEq VAR_MAP_LOCAL_0x17, 0, Route213_Arc2Return
    AddVar VAR_0x8006, 1
    Return

Route213_Arc2PeelGarius:
    SubVar VAR_0x8008, VAR_MAP_LOCAL_0x16
    GoToIfEq VAR_MAP_LOCAL_0x17, 0, Route213_Arc2Return
    AddVar VAR_0x8005, 1
    Return

// First match wins: Cyrus 3-4, Bad luck 3-4, Ruth 2+, Garius 2+, anything else
Route213_Arc2GariusOpening:
    GoToIfGe VAR_0x8004, 3, Route213_Arc2OpeningCyrus
    GoToIfGe VAR_0x8007, 3, Route213_Arc2OpeningBadLuck
    GoToIfGe VAR_0x8006, 2, Route213_Arc2OpeningRuth
    GoToIfGe VAR_0x8005, 2, Route213_Arc2OpeningGarius
    Message Route213_Text_Arc2BeachGariusMixed
    Return

Route213_Arc2OpeningCyrus:
    Message Route213_Text_Arc2BeachGariusCyrus
    Return

Route213_Arc2OpeningBadLuck:
    Message Route213_Text_Arc2BeachGariusBadLuck
    Return

Route213_Arc2OpeningRuth:
    Message Route213_Text_Arc2BeachGariusRuth
    Return

Route213_Arc2OpeningGarius:
    Message Route213_Text_Arc2BeachGariusGarius
    Return

    .balign 4, 0
Route213_Arc2Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_StepEast:
    WalkNormalEast
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_Notice:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_Shudder:
    WalkOnSpotFastSouth
    WalkOnSpotFastSouth
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_LookerSlipAhead:
    WalkFastEast 4
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_RuthRunIn:
    WalkFastEast 12
    WalkFastNorth
    FaceEast
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_CyrusRunIn:
    WalkFastEast 12
    WalkFastNorth
    FaceEast
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_GruntBApproach:
    WalkFastEast 3
    WalkFastSouth 2
    FaceEast
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_GruntAApproach:
    WalkFastEast 8
    WalkFastNorth
    WalkFastEast
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_GruntFlee:
    WalkFastWest 6
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_PsyduckDrop:
    WalkNormalSouth
    FaceWest
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_LookerStepEast:
    WalkNormalEast
    FaceEast
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_GariusWalkUp:
    WalkNormalEast 9
    WalkNormalNorth
    WalkNormalEast
    FaceSouth
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_PlayerToCyrus1:
    WalkNormalEast 11
    WalkNormalNorth
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_PlayerToCyrus2:
    WalkNormalNorth 2
    FaceEast
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_CyrusLeave:
    WalkNormalSouth 3
    WalkNormalWest 14
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_WatchSouthWest:
    Delay8
    FaceSouth
    Delay8 4
    FaceWest
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_RuthComeDown:
    WalkNormalEast 16
    WalkNormalNorth 3
    FaceEast
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_RuthLeave:
    WalkNormalSouth 3
    WalkNormalWest 16
    EndMovement

    .balign 4, 0
Route213_Arc2Movement_GariusLeave:
    WalkNormalSouth
    WalkNormalWest 6
    EndMovement
