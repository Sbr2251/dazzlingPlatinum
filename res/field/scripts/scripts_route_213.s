#include "macros/scrcmd.inc"
#include "constants/totem_battle.h"
#include "res/text/bank/route_213.h"
#include "res/field/events/events_route_213.h"


    ScriptEntry _0022
    ScriptEntry _0078
    ScriptEntry _0422
    ScriptEntry _03FC
    ScriptEntry _040F
    ScriptEntry _0435
    ScriptEntry _044C
    ScriptEntry _0463
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

_0022:
    // Arc 2: the stock Galactic grunt / Looker chain (Fen Badge) is retired; FLAG_UNK_0x021A and 0x01E8 stay set
    // from the new-game script, so both stock objects stay hidden.
    Call Route213_Arc2OnTransition
    End

_002F:
    CheckBadgeAcquired BADGE_ID_FEN, VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, 1, _0044
    End

_0044:
    GoToIfSet FLAG_UNK_0x0103, _0051
    End

_0051:
    CallIfUnset FLAG_UNK_0x0118, _0062
    ClearFlag FLAG_UNK_0x021A
    End

_0062:
    SetObjectEventPos 30, 0x28E, 0x32C
    SetObjectEventDir 30, DIR_EAST
    SetObjectEventMovementType 30, MOVEMENT_TYPE_LOOK_EAST
    Return

_0078:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfSet FLAG_UNK_0x0118, _0133
    Message 0
    CloseMessage
    FacePlayer
    ApplyMovement 30, _0388
    WaitMovement
    Message 1
    CloseMessage
    GetPlayerDir VAR_0x8004
    GoToIfEq VAR_0x8004, 2, _00F1
    GoToIfEq VAR_0x8004, 3, _00DF
    GoTo _00C5
    End

_00C5:
    ApplyMovement 30, _0390
    ApplyMovement LOCALID_PLAYER, _03F0
    WaitMovement
    GoTo _010B
    End

_00DF:
    ApplyMovement 30, _0390
    WaitMovement
    GoTo _010B
    End

_00F1:
    ApplyMovement 30, _0398
    ApplyMovement LOCALID_PLAYER, _03F0
    WaitMovement
    GoTo _010B
    End

_010B:
    SetFlag FLAG_UNK_0x0118
    RemoveObject 30
    SetObjectEventPos 30, 0x2AB, 0x341
    SetObjectEventDir 30, DIR_EAST
    SetObjectEventMovementType 30, MOVEMENT_TYPE_LOOK_EAST
    ClearFlag FLAG_UNK_0x021A
    AddObject 30
    ReleaseAll
    End

_0133:
    GetPlayerDir VAR_0x8004
    Message 2
    CloseMessage
    FacePlayer
    ApplyMovement 30, _0388
    WaitMovement
    Message 3
    CloseMessage
    GetPlayerDir VAR_0x8004
    GoToIfEq VAR_0x8004, 2, _0180
    GoTo _0166
    End

_0166:
    ApplyMovement LOCALID_PLAYER, _03C0
    ApplyMovement 30, _03A4
    WaitMovement
    GoTo _019A
    End

_0180:
    ApplyMovement LOCALID_PLAYER, _03C0
    ApplyMovement 30, _03B4
    WaitMovement
    GoTo _019A
    End

_019A:
    RemoveObject 30
    SetFlag FLAG_UNK_0x0104
    ClearFlag FLAG_UNK_0x01E8
    AddObject 33
    SetLookerBGM
    ScrCmd_315 VAR_RESULT
    CallIfEq VAR_RESULT, 2, _0261
    CallIfEq VAR_0x8004, 2, _0267
    CallIfEq VAR_0x8004, 3, _027B
    CallIfEq VAR_0x8004, 0, _028F
    CallIfEq VAR_0x8004, 1, _02A3
    Message 4
    ApplyMovement 33, _0348
    WaitMovement
    Message 5
    Message 6
    CloseMessage
    CallIfEq VAR_0x8004, 2, _02B7
    CallIfEq VAR_0x8004, 3, _02CB
    CallIfEq VAR_0x8004, 0, _02DF
    CallIfEq VAR_0x8004, 1, _02F3
    RemoveObject 33
    FadeToDefaultMusic4
    ScrCmd_315 VAR_RESULT
    CallIfEq VAR_RESULT, 2, _0261
    ClearFlag FLAG_UNK_0x0211
    ClearFlag FLAG_UNK_0x021B
    ReleaseAll
    End

_0261:
    PlayFanfare SEQ_SE_DP_T_AME
    Return

_0267:
    ApplyMovement 33, _0318
    ApplyMovement LOCALID_PLAYER, _03CC
    WaitMovement
    Return

_027B:
    ApplyMovement 33, _0308
    ApplyMovement LOCALID_PLAYER, _03CC
    WaitMovement
    Return

_028F:
    ApplyMovement 33, _0338
    ApplyMovement LOCALID_PLAYER, _03CC
    WaitMovement
    Return

_02A3:
    ApplyMovement 33, _0328
    ApplyMovement LOCALID_PLAYER, _03D8
    WaitMovement
    Return

_02B7:
    ApplyMovement 33, _035C
    ApplyMovement LOCALID_PLAYER, _03E4
    WaitMovement
    Return

_02CB:
    ApplyMovement 33, _0350
    ApplyMovement LOCALID_PLAYER, _03E4
    WaitMovement
    Return

_02DF:
    ApplyMovement 33, _037C
    ApplyMovement LOCALID_PLAYER, _03E4
    WaitMovement
    Return

_02F3:
    ApplyMovement 33, _0368
    ApplyMovement LOCALID_PLAYER, _03E4
    WaitMovement
    Return

    .balign 4, 0
_0308:
    WalkFastEast 10
    WalkFastNorth 2
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
_0318:
    WalkFastEast 10
    WalkFastNorth 2
    WalkFastEast 2
    EndMovement

    .balign 4, 0
_0328:
    WalkFastEast 10
    WalkFastNorth 3
    WalkFastEast
    EndMovement

    .balign 4, 0
_0338:
    WalkFastEast 10
    WalkFastNorth
    WalkFastEast
    EndMovement

    .balign 4, 0
_0348:
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
_0350:
    WalkFastNorth
    WalkFastEast 10
    EndMovement

    .balign 4, 0
_035C:
    WalkFastNorth
    WalkFastEast 10
    EndMovement

    .balign 4, 0
_0368:
    WalkFastSouth
    WalkFastEast 4
    WalkFastNorth
    WalkFastEast 6
    EndMovement

    .balign 4, 0
_037C:
    WalkFastNorth 2
    WalkFastEast 10
    EndMovement

    .balign 4, 0
_0388:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_0390:
    WalkFastEast 10
    EndMovement

    .balign 4, 0
_0398:
    WalkFastSouth 2
    WalkFastEast 9
    EndMovement

    .balign 4, 0
_03A4:
    WalkFastEast 4
    WalkFastNorth
    WalkFastEast 6
    EndMovement

    .balign 4, 0
_03B4:
    WalkFastNorth
    WalkFastEast 10
    EndMovement

    .balign 4, 0
_03C0:
    Delay8
    FaceEast
    EndMovement

    .balign 4, 0
_03CC:
    Delay4 10
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_03D8:
    Delay4 11
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_03E4:
    Delay4 3
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_03F0:
    Delay8
    WalkOnSpotNormalEast
    EndMovement

_03FC:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 8
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_040F:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 9
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0422:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 7
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0435:
    ShowArrowSign 10
    End

_044C:
    ShowLandmarkSign 11
    End

_0463:
    ShowLandmarkSign 12
    End

    .balign 4, 0

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 2, workstream s-raid: screenplay 2.21 (the night raid, leak L3) and 2.23 (the beach,
// Cyrus battle 3). VAR_ARC2_PROGRESS block 80-84 and 87-89 (rift-b sets 84 on the Lapras calm; s-pastoria owns
// 85-86, its 2.21a briefing sets 75 and warps here).
//
//   75        arrival: Warp MAP_HEADER_ROUTE_213, 0, 687, 832, DIR_EAST (the beach mouth). Sets 80.
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
//   FLAG_UNK_0x0030 stock beach trainers (Tuber Jared, Tuber Chelsea) during 75-88
//   FLAG_UNK_0x0031 Looker            FLAG_UNK_0x0032 Ruth             FLAG_UNK_0x0033 Cyrus
//   FLAG_UNK_0x0034 Garius            FLAG_UNK_0x0035 the two patrols  FLAG_UNK_0x0036 the empty frame
//   FLAG_UNK_0x0037 Psyduck           FLAG_UNK_0x0038 the Lapras rift  FLAG_UNK_0x0039 Eclipse crates (705-707,823: block the stairs gap)
// Map-local vars: _4 intro armed (coord), _5 raid on (step coord), _6 checkpoint, _7 beat, _8-_B sight scratch,
//   _C steps used, _D steps at checkpoint, _E halfway warned, _F which patrol, _10/_11 patrol A/B facing.

#define RAID_BUDGET 44
#define RAID_HALF   22
#define RAID_A_X    704
#define RAID_A_Z    829
#define RAID_B_X    710
#define RAID_B_Z    826

Route213_Arc2OnTransition:
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    SetFlag FLAG_UNK_0x0032
    SetFlag FLAG_UNK_0x0033
    SetFlag FLAG_UNK_0x0034
    SetFlag FLAG_UNK_0x0035
    SetFlag FLAG_UNK_0x0036
    SetFlag FLAG_UNK_0x0037
    SetFlag FLAG_UNK_0x0038
    SetFlag FLAG_UNK_0x0039
    GoToIfLt VAR_ARC2_PROGRESS, 75, Route213_Arc2OnTransitionStockTrainers
    GoToIfGt VAR_ARC2_PROGRESS, 88, Route213_Arc2OnTransitionStockTrainers
    // Raid and beach states: the beach is Eclipse's (stock trainers off, crates in the north gap)
    ClearFlag FLAG_UNK_0x0039
    ClearFlag FLAG_UNK_0x0036
    GoToIfLe VAR_ARC2_PROGRESS, 81, Route213_Arc2SetUpRaid
    GoToIfLe VAR_ARC2_PROGRESS, 83, Route213_Arc2SetUpRiftOpen
    GoToIfEq VAR_ARC2_PROGRESS, 84, Route213_Arc2SetUpCalm
    GoToIfGe VAR_ARC2_PROGRESS, 86, Route213_Arc2SetUpBeach
    Return

Route213_Arc2OnTransitionStockTrainers:
    ClearFlag FLAG_UNK_0x0030
    Return

// 75-81: Looker in the corridor, Ruth and Cyrus at the mouth, the patrols, the frame, Psyduck and the rift
Route213_Arc2SetUpRaid:
    ClearFlag FLAG_UNK_0x0031
    ClearFlag FLAG_UNK_0x0032
    ClearFlag FLAG_UNK_0x0033
    ClearFlag FLAG_UNK_0x0035
    ClearFlag FLAG_UNK_0x0037
    ClearFlag FLAG_UNK_0x0038
    SetObjectEventPos ROUTE_213_ARC2_LOOKER, 689, 832
    SetObjectEventDir ROUTE_213_ARC2_LOOKER, DIR_WEST
    SetObjectEventMovementType ROUTE_213_ARC2_LOOKER, MOVEMENT_TYPE_LOOK_WEST
    SetObjectEventPos ROUTE_213_ARC2_RUTH, 684, 833
    SetObjectEventDir ROUTE_213_ARC2_RUTH, DIR_EAST
    SetObjectEventMovementType ROUTE_213_ARC2_RUTH, MOVEMENT_TYPE_LOOK_EAST
    SetObjectEventPos ROUTE_213_ARC2_CYRUS, 685, 833
    SetObjectEventDir ROUTE_213_ARC2_CYRUS, DIR_EAST
    SetObjectEventMovementType ROUTE_213_ARC2_CYRUS, MOVEMENT_TYPE_LOOK_EAST
    SetVar VAR_MAP_LOCAL_4, 1
    SetVar VAR_MAP_LOCAL_5, 0
    SetVar VAR_MAP_LOCAL_10, DIR_WEST
    SetVar VAR_MAP_LOCAL_11, DIR_SOUTH
    Return

// 82-83: the patrols are gone; everyone stands by the frames, the Lapras rift is open
Route213_Arc2SetUpRiftOpen:
    ClearFlag FLAG_UNK_0x0031
    ClearFlag FLAG_UNK_0x0032
    ClearFlag FLAG_UNK_0x0033
    ClearFlag FLAG_UNK_0x0037
    ClearFlag FLAG_UNK_0x0038
    SetObjectEventPos ROUTE_213_ARC2_LOOKER, 714, 827
    SetObjectEventDir ROUTE_213_ARC2_LOOKER, DIR_SOUTH
    SetObjectEventMovementType ROUTE_213_ARC2_LOOKER, MOVEMENT_TYPE_LOOK_SOUTH
    SetObjectEventPos ROUTE_213_ARC2_RUTH, 712, 831
    SetObjectEventDir ROUTE_213_ARC2_RUTH, DIR_EAST
    SetObjectEventMovementType ROUTE_213_ARC2_RUTH, MOVEMENT_TYPE_LOOK_EAST
    SetObjectEventPos ROUTE_213_ARC2_CYRUS, 711, 831
    SetObjectEventDir ROUTE_213_ARC2_CYRUS, DIR_EAST
    SetObjectEventMovementType ROUTE_213_ARC2_CYRUS, MOVEMENT_TYPE_LOOK_EAST
    SetObjectEventPos ROUTE_213_ARC2_PSYDUCK, 715, 829
    Return

// 84: back from the rift (it closed behind the player); Looker waits beside the frames
Route213_Arc2SetUpCalm:
    ClearFlag FLAG_UNK_0x0031
    SetObjectEventPos ROUTE_213_ARC2_LOOKER, 713, 831
    SetObjectEventDir ROUTE_213_ARC2_LOOKER, DIR_EAST
    SetObjectEventMovementType ROUTE_213_ARC2_LOOKER, MOVEMENT_TYPE_LOOK_EAST
    Return

// 86-88: Cyrus alone at the waterline
Route213_Arc2SetUpBeach:
    ClearFlag FLAG_UNK_0x0033
    SetObjectEventPos ROUTE_213_ARC2_CYRUS, 713, 829
    SetObjectEventDir ROUTE_213_ARC2_CYRUS, DIR_EAST
    SetObjectEventMovementType ROUTE_213_ARC2_CYRUS, MOVEMENT_TYPE_LOOK_EAST
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

// Coord (VAR_MAP_LOCAL_4 = 1): the mouth (688,832-833), or anywhere on the east beach (arrived by Surf)
Route213_Arc2RaidIntroTrigger:
    GoTo Route213_Arc2RaidIntro
    End

Route213_Arc2RaidIntro:
    LockAll
    SetVar VAR_MAP_LOCAL_4, 0
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
    ApplyMovement ROUTE_213_ARC2_LOOKER, Route213_Arc2Movement_FaceWest
    WaitMovement
    Message Route213_Text_Arc2RaidPatrols
    WaitABXPadPress
    CloseMessage
    // He slips ahead into the dark; from here he moves on his own
    ApplyMovement ROUTE_213_ARC2_LOOKER, Route213_Arc2Movement_LookerSlipAhead
    WaitMovement
    RemoveObject ROUTE_213_ARC2_LOOKER
    Call Route213_Arc2RaidReset
    SetVar VAR_MAP_LOCAL_6, 0
    SetVar VAR_MAP_LOCAL_C, 0
    SetVar VAR_MAP_LOCAL_D, 0
    SetVar VAR_MAP_LOCAL_E, 0
    SetVar VAR_MAP_LOCAL_5, 1
    ReleaseAll
    End

// Patrols back to beat 0 (A west, B south)
Route213_Arc2RaidReset:
    SetVar VAR_MAP_LOCAL_7, 0
    ApplyMovement ROUTE_213_ARC2_GRUNT_A, Route213_Arc2Movement_FaceWest
    ApplyMovement ROUTE_213_ARC2_GRUNT_B, Route213_Arc2Movement_FaceSouth
    WaitMovement
    SetVar VAR_MAP_LOCAL_10, DIR_WEST
    SetVar VAR_MAP_LOCAL_11, DIR_SOUTH
    Return

// Coord over x689-715, z823-832 while the raid is on: one beat per step
Route213_Arc2RaidStep:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    AddVar VAR_MAP_LOCAL_C, 1
    GoToIfGt VAR_MAP_LOCAL_C, RAID_BUDGET, Route213_Arc2RaidTooSlow
    CallIfEq VAR_MAP_LOCAL_C, RAID_HALF, Route213_Arc2RaidHalfway
    AddVar VAR_MAP_LOCAL_7, 1
    CallIfGe VAR_MAP_LOCAL_7, 9, Route213_Arc2RaidWrapBeat
    Call Route213_Arc2RaidTurnPatrols
    // Patrol A
    SetVar VAR_MAP_LOCAL_F, 1
    SetVar VAR_0x8006, RAID_A_X
    SetVar VAR_0x8007, RAID_A_Z
    SetVar VAR_0x8008, VAR_MAP_LOCAL_10
    Call Route213_Arc2CheckSight
    GoToIfEq VAR_RESULT, 1, Route213_Arc2RaidCaught
    // Patrol B
    SetVar VAR_MAP_LOCAL_F, 2
    SetVar VAR_0x8006, RAID_B_X
    SetVar VAR_0x8007, RAID_B_Z
    SetVar VAR_0x8008, VAR_MAP_LOCAL_11
    Call Route213_Arc2CheckSight
    GoToIfEq VAR_RESULT, 1, Route213_Arc2RaidCaught
    // The frames
    GoToIfLt VAR_0x8004, 713, Route213_Arc2RaidStepCheckpoint
    GoToIfInRange VAR_0x8005, 828, 831, Route213_Arc2Frames
Route213_Arc2RaidStepCheckpoint:
    GoToIfNe VAR_MAP_LOCAL_6, 0, Route213_Arc2RaidStepEnd
    GoToIfNe VAR_0x8005, 832, Route213_Arc2RaidStepEnd
    GoToIfInRange VAR_0x8004, 706, 707, Route213_Arc2RaidCheckpoint1
Route213_Arc2RaidStepEnd:
    End

Route213_Arc2RaidCheckpoint1:
    SetVar VAR_MAP_LOCAL_6, 1
    SetVar VAR_MAP_LOCAL_D, VAR_MAP_LOCAL_C
    End

Route213_Arc2RaidWrapBeat:
    SetVar VAR_MAP_LOCAL_7, 1
    Return

Route213_Arc2RaidHalfway:
    GoToIfNe VAR_MAP_LOCAL_E, 0, Route213_Arc2Return
    SetVar VAR_MAP_LOCAL_E, 1
    LockAll
    Message Route213_Text_Arc2RaidHalfway
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    Return

Route213_Arc2Return:
    Return

// A: beats 1-4 west, 5-8 south. B: beats 1-3 south, 4-8 east. Each turns only when its facing changes.
Route213_Arc2RaidTurnPatrols:
    SetVar VAR_0x8008, DIR_WEST
    CallIfGe VAR_MAP_LOCAL_7, 5, Route213_Arc2Set8008South
    CallIfNe VAR_MAP_LOCAL_10, VAR_0x8008, Route213_Arc2TurnA
    SetVar VAR_0x8008, DIR_SOUTH
    CallIfGe VAR_MAP_LOCAL_7, 4, Route213_Arc2Set8008East
    CallIfNe VAR_MAP_LOCAL_11, VAR_0x8008, Route213_Arc2TurnB
    Return

Route213_Arc2Set8008South:
    SetVar VAR_0x8008, DIR_SOUTH
    Return

Route213_Arc2Set8008East:
    SetVar VAR_0x8008, DIR_EAST
    Return

Route213_Arc2TurnA:
    SetVar VAR_MAP_LOCAL_10, VAR_0x8008
    GoToIfEq VAR_0x8008, DIR_SOUTH, Route213_Arc2TurnASouth
    ApplyMovement ROUTE_213_ARC2_GRUNT_A, Route213_Arc2Movement_FaceWest
    WaitMovement
    Return

Route213_Arc2TurnASouth:
    ApplyMovement ROUTE_213_ARC2_GRUNT_A, Route213_Arc2Movement_FaceSouth
    WaitMovement
    Return

Route213_Arc2TurnB:
    SetVar VAR_MAP_LOCAL_11, VAR_0x8008
    GoToIfEq VAR_0x8008, DIR_EAST, Route213_Arc2TurnBEast
    ApplyMovement ROUTE_213_ARC2_GRUNT_B, Route213_Arc2Movement_FaceSouth
    WaitMovement
    Return

Route213_Arc2TurnBEast:
    ApplyMovement ROUTE_213_ARC2_GRUNT_B, Route213_Arc2Movement_FaceEast
    WaitMovement
    Return

// In: VAR_0x8004/0x8005 player, VAR_0x8006/0x8007 guard, VAR_0x8008 his facing. Out: VAR_RESULT 1 if seen;
// VAR_0x8009/0x800A = |dx|/|dz|; VAR_MAP_LOCAL_8/_9 = sign of dx/dz (0 west/north of him, 1 same, 2 east/south).
// Same cone as the Arc 1 crate tail.
Route213_Arc2CheckSight:
    SetVar VAR_RESULT, 0
    SetVar VAR_MAP_LOCAL_8, 1
    SetVar VAR_0x8009, 0
    GoToIfEq VAR_0x8004, VAR_0x8006, Route213_Arc2SightDZ
    GoToIfLt VAR_0x8004, VAR_0x8006, Route213_Arc2SightWest
    SetVar VAR_MAP_LOCAL_8, 2
    SetVar VAR_0x8009, VAR_0x8004
    SubVar VAR_0x8009, VAR_0x8006
    GoTo Route213_Arc2SightDZ
    End

Route213_Arc2SightWest:
    SetVar VAR_MAP_LOCAL_8, 0
    SetVar VAR_0x8009, VAR_0x8006
    SubVar VAR_0x8009, VAR_0x8004
    GoTo Route213_Arc2SightDZ
    End

Route213_Arc2SightDZ:
    SetVar VAR_MAP_LOCAL_9, 1
    SetVar VAR_0x800A, 0
    GoToIfEq VAR_0x8005, VAR_0x8007, Route213_Arc2SightAdjacent
    GoToIfLt VAR_0x8005, VAR_0x8007, Route213_Arc2SightNorth
    SetVar VAR_MAP_LOCAL_9, 2
    SetVar VAR_0x800A, VAR_0x8005
    SubVar VAR_0x800A, VAR_0x8007
    GoTo Route213_Arc2SightAdjacent
    End

Route213_Arc2SightNorth:
    SetVar VAR_MAP_LOCAL_9, 0
    SetVar VAR_0x800A, VAR_0x8007
    SubVar VAR_0x800A, VAR_0x8005
    GoTo Route213_Arc2SightAdjacent
    End

Route213_Arc2SightAdjacent:
    SetVar VAR_MAP_LOCAL_B, VAR_0x8009
    AddVar VAR_MAP_LOCAL_B, VAR_0x800A
    GoToIfLe VAR_MAP_LOCAL_B, 1, Route213_Arc2SightSeen
    GoToIfEq VAR_0x8008, DIR_NORTH, Route213_Arc2SightFaceNorth
    GoToIfEq VAR_0x8008, DIR_SOUTH, Route213_Arc2SightFaceSouth
    GoToIfEq VAR_0x8008, DIR_WEST, Route213_Arc2SightFaceWest
    GoTo Route213_Arc2SightFaceEast
    End

Route213_Arc2SightFaceNorth:
    GoToIfNe VAR_MAP_LOCAL_9, 0, Route213_Arc2SightEnd
    GoTo Route213_Arc2SightAlongZ
    End

Route213_Arc2SightFaceSouth:
    GoToIfNe VAR_MAP_LOCAL_9, 2, Route213_Arc2SightEnd
    GoTo Route213_Arc2SightAlongZ
    End

Route213_Arc2SightFaceWest:
    GoToIfNe VAR_MAP_LOCAL_8, 0, Route213_Arc2SightEnd
    GoTo Route213_Arc2SightAlongX
    End

Route213_Arc2SightFaceEast:
    GoToIfNe VAR_MAP_LOCAL_8, 2, Route213_Arc2SightEnd
    GoTo Route213_Arc2SightAlongX
    End

Route213_Arc2SightAlongZ:
    SetVar VAR_MAP_LOCAL_A, VAR_0x800A
    SetVar VAR_MAP_LOCAL_B, VAR_0x8009
    GoTo Route213_Arc2SightCone
    End

Route213_Arc2SightAlongX:
    SetVar VAR_MAP_LOCAL_A, VAR_0x8009
    SetVar VAR_MAP_LOCAL_B, VAR_0x800A
    GoTo Route213_Arc2SightCone
    End

Route213_Arc2SightCone:
    GoToIfGt VAR_MAP_LOCAL_A, 6, Route213_Arc2SightEnd
    GoToIfEq VAR_MAP_LOCAL_A, 1, Route213_Arc2SightWidth0
    GoToIfLe VAR_MAP_LOCAL_A, 3, Route213_Arc2SightWidth1
    GoToIfLe VAR_MAP_LOCAL_B, 2, Route213_Arc2SightSeen
    GoTo Route213_Arc2SightEnd
    End

Route213_Arc2SightWidth0:
    GoToIfEq VAR_MAP_LOCAL_B, 0, Route213_Arc2SightSeen
    GoTo Route213_Arc2SightEnd
    End

Route213_Arc2SightWidth1:
    GoToIfLe VAR_MAP_LOCAL_B, 1, Route213_Arc2SightSeen
    GoTo Route213_Arc2SightEnd
    End

Route213_Arc2SightSeen:
    SetVar VAR_RESULT, 1
Route213_Arc2SightEnd:
    Return

// Spotted: the patrol turns to the player, then back to the last checkpoint (no fail state)
Route213_Arc2RaidCaught:
    LockAll
    GoToIfEq VAR_MAP_LOCAL_F, 2, Route213_Arc2RaidCaughtB
    Call Route213_Arc2FacePlayerA
    ApplyMovement ROUTE_213_ARC2_GRUNT_A, Route213_Arc2Movement_Notice
    WaitMovement
    GoTo Route213_Arc2RaidCaughtMessage
    End

Route213_Arc2RaidCaughtB:
    Call Route213_Arc2FacePlayerB
    ApplyMovement ROUTE_213_ARC2_GRUNT_B, Route213_Arc2Movement_Notice
    WaitMovement
Route213_Arc2RaidCaughtMessage:
    Message Route213_Text_Arc2RaidSpotted
    WaitABXPadPress
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    CallIfEq VAR_MAP_LOCAL_6, 0, Route213_Arc2Checkpoint0
    CallIfEq VAR_MAP_LOCAL_6, 1, Route213_Arc2Checkpoint1
    SetVar VAR_MAP_LOCAL_C, VAR_MAP_LOCAL_D
    Call Route213_Arc2RaidReset
    WaitTime 10, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    Message Route213_Text_Arc2RaidAgain
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// Out of steps: Looker calls it, back to the mouth with the whole budget
Route213_Arc2RaidTooSlow:
    LockAll
    Message Route213_Text_Arc2RaidTooSlow
    WaitABXPadPress
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    Call Route213_Arc2Checkpoint0
    SetVar VAR_MAP_LOCAL_6, 0
    SetVar VAR_MAP_LOCAL_C, 0
    SetVar VAR_MAP_LOCAL_D, 0
    SetVar VAR_MAP_LOCAL_E, 0
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
    GoToIfEq VAR_MAP_LOCAL_8, 0, Route213_Arc2FacePlayerAWest
    ApplyMovement ROUTE_213_ARC2_GRUNT_A, Route213_Arc2Movement_FaceEast
    WaitMovement
    Return

Route213_Arc2FacePlayerAWest:
    ApplyMovement ROUTE_213_ARC2_GRUNT_A, Route213_Arc2Movement_FaceWest
    WaitMovement
    Return

Route213_Arc2FacePlayerAZ:
    GoToIfEq VAR_MAP_LOCAL_9, 0, Route213_Arc2FacePlayerANorth
    ApplyMovement ROUTE_213_ARC2_GRUNT_A, Route213_Arc2Movement_FaceSouth
    WaitMovement
    Return

Route213_Arc2FacePlayerANorth:
    ApplyMovement ROUTE_213_ARC2_GRUNT_A, Route213_Arc2Movement_FaceNorth
    WaitMovement
    Return

Route213_Arc2FacePlayerB:
    GoToIfLt VAR_0x8009, VAR_0x800A, Route213_Arc2FacePlayerBZ
    GoToIfEq VAR_MAP_LOCAL_8, 0, Route213_Arc2FacePlayerBWest
    ApplyMovement ROUTE_213_ARC2_GRUNT_B, Route213_Arc2Movement_FaceEast
    WaitMovement
    Return

Route213_Arc2FacePlayerBWest:
    ApplyMovement ROUTE_213_ARC2_GRUNT_B, Route213_Arc2Movement_FaceWest
    WaitMovement
    Return

Route213_Arc2FacePlayerBZ:
    GoToIfEq VAR_MAP_LOCAL_9, 0, Route213_Arc2FacePlayerBNorth
    ApplyMovement ROUTE_213_ARC2_GRUNT_B, Route213_Arc2Movement_FaceSouth
    WaitMovement
    Return

Route213_Arc2FacePlayerBNorth:
    ApplyMovement ROUTE_213_ARC2_GRUNT_B, Route213_Arc2Movement_FaceNorth
    WaitMovement
    Return

// The frames: Psyduck hangs in one, the other is already a rift. Ruth and Cyrus run in; the patrols turn.
Route213_Arc2Frames:
    LockAll
    SetVar VAR_MAP_LOCAL_5, 0
    FadeScreenOut
    WaitFadeScreen
    SetPosition LOCALID_PLAYER, 714, 0, 828, DIR_EAST
    SetObjectEventPos ROUTE_213_ARC2_LOOKER, 714, 827
    SetObjectEventDir ROUTE_213_ARC2_LOOKER, DIR_EAST
    SetObjectEventMovementType ROUTE_213_ARC2_LOOKER, MOVEMENT_TYPE_LOOK_EAST
    ClearFlag FLAG_UNK_0x0031
    AddObject ROUTE_213_ARC2_LOOKER
    // Ruth and Cyrus come from the mouth
    RemoveObject ROUTE_213_ARC2_RUTH
    RemoveObject ROUTE_213_ARC2_CYRUS
    SetObjectEventPos ROUTE_213_ARC2_RUTH, 700, 832
    SetObjectEventDir ROUTE_213_ARC2_RUTH, DIR_EAST
    SetObjectEventPos ROUTE_213_ARC2_CYRUS, 699, 832
    SetObjectEventDir ROUTE_213_ARC2_CYRUS, DIR_EAST
    SetVar VAR_MAP_LOCAL_10, DIR_WEST
    ApplyMovement ROUTE_213_ARC2_GRUNT_A, Route213_Arc2Movement_FaceWest
    ApplyMovement ROUTE_213_ARC2_GRUNT_B, Route213_Arc2Movement_FaceSouth
    WaitMovement
    WaitTime 4, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    // The empty frame screams
    PlayCry SPECIES_LAPRAS
    ApplyMovement ROUTE_213_ARC2_RIFT, Route213_Arc2Movement_Shudder
    WaitMovement
    WaitCry
    PlayCry SPECIES_PSYDUCK
    WaitCry
    ClearFlag FLAG_UNK_0x0032
    ClearFlag FLAG_UNK_0x0033
    AddObject ROUTE_213_ARC2_RUTH
    AddObject ROUTE_213_ARC2_CYRUS
    ApplyMovement ROUTE_213_ARC2_RUTH, Route213_Arc2Movement_RuthRunIn
    ApplyMovement ROUTE_213_ARC2_CYRUS, Route213_Arc2Movement_CyrusRunIn
    WaitMovement
    Message Route213_Text_Arc2RaidTearing
    WaitABXPadPress
    CloseMessage
    // Two guards turn
    ApplyMovement ROUTE_213_ARC2_GRUNT_B, Route213_Arc2Movement_Notice
    WaitMovement
    ApplyMovement ROUTE_213_ARC2_GRUNT_B, Route213_Arc2Movement_GruntBApproach
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceWest
    WaitMovement
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_ARC2_11
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route213_Arc2LostBattle
    ApplyMovement ROUTE_213_ARC2_GRUNT_B, Route213_Arc2Movement_GruntFlee
    WaitMovement
    RemoveObject ROUTE_213_ARC2_GRUNT_B
    ApplyMovement ROUTE_213_ARC2_GRUNT_A, Route213_Arc2Movement_Notice
    WaitMovement
    ApplyMovement ROUTE_213_ARC2_GRUNT_A, Route213_Arc2Movement_GruntAApproach
    WaitMovement
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_ARC2_12
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route213_Arc2LostBattle
    ApplyMovement ROUTE_213_ARC2_GRUNT_A, Route213_Arc2Movement_GruntFlee
    WaitMovement
    RemoveObject ROUTE_213_ARC2_GRUNT_A
    // Looker and the player cut the Psyduck free as the air around it snaps shut
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceEast
    ApplyMovement ROUTE_213_ARC2_LOOKER, Route213_Arc2Movement_FaceEast
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    ApplyMovement ROUTE_213_ARC2_PSYDUCK, Route213_Arc2Movement_PsyduckDrop
    WaitMovement
    PlayCry SPECIES_PSYDUCK
    WaitCry
    // The other rift stays open; something huge moves on the far side
    WaitTime 20, VAR_RESULT
    PlayCry SPECIES_LAPRAS
    ApplyMovement ROUTE_213_ARC2_RIFT, Route213_Arc2Movement_Shudder
    WaitMovement
    WaitCry
    ApplyMovement ROUTE_213_ARC2_LOOKER, Route213_Arc2Movement_FaceWest
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceNorth
    WaitMovement
    Message Route213_Text_Arc2RaidTheyKnew
    WaitABXPadPress
    CloseMessage
    Message Route213_Text_Arc2RaidSomeoneTold
    WaitABXPadPress
    CloseMessage
    // Silence. Nobody looks at anybody.
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceSouth
    ApplyMovement ROUTE_213_ARC2_LOOKER, Route213_Arc2Movement_FaceSouth
    ApplyMovement ROUTE_213_ARC2_RUTH, Route213_Arc2Movement_FaceSouth
    ApplyMovement ROUTE_213_ARC2_CYRUS, Route213_Arc2Movement_FaceSouth
    WaitMovement
    WaitTime 60, VAR_RESULT
    Message Route213_Text_Arc2RaidUnderstand
    WaitABXPadPress
    CloseMessage
    // Ledger L3: Looker's own prompt, the shared menu, one neutral reaction each
    ApplyMovement ROUTE_213_ARC2_LOOKER, Route213_Arc2Movement_FaceSouth
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
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 82
    ApplyMovement ROUTE_213_ARC2_CYRUS, Route213_Arc2Movement_FaceEast
    WaitMovement
    Message Route213_Text_Arc2RaidCyrusGoNow
    WaitABXPadPress
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
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    Warp MAP_HEADER_DW_ROUTE_213, 0, 20, 12, DIR_WEST
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
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message Route213_Text_Arc2RaidLookerWait
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Route213_Arc2Ruth:
    PlayFanfare SEQ_SE_CONFIRM
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
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfGe VAR_ARC2_PROGRESS, 82, Route213_Arc2CyrusRift
    Message Route213_Text_Arc2RaidMouthCyrus
    GoTo Route213_Arc2TalkEnd
    End

Route213_Arc2CyrusRift:
    Message Route213_Text_Arc2RaidCyrusGoNow
    GoTo Route213_Arc2TalkEnd
    End

Route213_Arc2TalkEnd:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Route213_Arc2Psyduck:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    PlayCry SPECIES_PSYDUCK
    WaitCry
    ReleaseAll
    End

// On-frame (VAR_ARC2_PROGRESS 84): back from the Drowned Lake, Looker has his proof. Then the Pastoria Center (2.22).
Route213_Arc2Calm:
    LockAll
    ApplyMovement ROUTE_213_ARC2_LOOKER, Route213_Arc2Movement_LookerStepEast
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Route213_Arc2Movement_FaceWest
    WaitMovement
    Message Route213_Text_Arc2RaidPhotos
    WaitABXPadPress
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_PASTORIA_CITY_POKECENTER_1F, 0, 8, 11, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

// 2.23 (the beach): next commit
Route213_Arc2BeachTriggerMouth:
Route213_Arc2BeachTriggerOther:
    End

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








