#include "macros/scrcmd.inc"
#include "res/text/bank/solaceon_ruins_room_1.h"
#include "res/field/maps/locals/solaceon_ruins_room_1.h"

// Solaceon raid (screenplay.md scene 3.4a part 3; docs/solaceon_redesign/raid_maps.md). VAR_SOLACEON_PROGRESS:
//   < 20  the rope blocks the stair to Room 2 (6,3); Room 1 and its two dead ends are open (stock)
//   20    first entry: Cyrus at the wall, Ruth on the Poketch (init frame table), sets 30
//   20-49 the raid crew: grunt SOL_01 on the stair, two crates
//   >= 50 open and empty (the excavation terrain stays)
// Map-local hide flags (recomputed on every load in SolaceonRuinsRoom1_OnTransition):
//   FLAG_MAP_LOCAL_HIDE_OBSTACLE_16 raid crew   _17 rope   _18 Cyrus

    ScriptEntry SolaceonRuinsRoom1_OnTransition
    ScriptEntry SolaceonRuinsRoom1_Inscription
    ScriptEntry SolaceonRuinsRoom1_RaidRope
    ScriptEntry SolaceonRuinsRoom1_RaidCyrus
    ScriptEntry SolaceonRuinsRoom1_RaidEntry
    ScriptEntryEnd

SolaceonRuinsRoom1_OnTransition:
    SetFlag FLAG_FIRST_ARRIVAL_SOLACEON_RUINS
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    GoToIfLt VAR_SOLACEON_PROGRESS, 20, SolaceonRuinsRoom1_OnTransitionEnd
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    GoToIfGe VAR_SOLACEON_PROGRESS, 50, SolaceonRuinsRoom1_OnTransitionEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    GoToIfNe VAR_SOLACEON_PROGRESS, 20, SolaceonRuinsRoom1_OnTransitionEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
SolaceonRuinsRoom1_OnTransitionEnd:
    End

SolaceonRuinsRoom1_Inscription:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    MessageUnown SolaceonRuinsRoom1_Text_Directions
    WaitButton
    CloseMessage
    ReleaseAll
    End

// The rope on the stair down to Room 2 (progress < 20)
SolaceonRuinsRoom1_RaidRope:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message SolaceonRuinsRoom1_Text_RaidRopeSign
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

// Cyrus only stands here during the entry scene; talking to him repeats his last line
SolaceonRuinsRoom1_RaidCyrus:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message SolaceonRuinsRoom1_Text_RaidCyrusGoAhead
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

// First entry at 20 (init frame table): the player walks up beside Cyrus (4,7), he reads the lines, Ruth calls,
// he goes ahead. Sets 30.
SolaceonRuinsRoom1_RaidEntry:
    LockAll
    SetVar VAR_SOLACEON_PROGRESS, 30
SolaceonRuinsRoom1_RaidWalkIn:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfLe VAR_0x8005, 7, SolaceonRuinsRoom1_RaidBesideCyrus
    ApplyMovement LOCALID_PLAYER, SolaceonRuinsRoom1_Movement_North1
    WaitMovement
    GoTo SolaceonRuinsRoom1_RaidWalkIn
    End

SolaceonRuinsRoom1_RaidBesideCyrus:
    ApplyMovement LOCALID_PLAYER, SolaceonRuinsRoom1_Movement_FaceWest
    WaitMovement
    Message SolaceonRuinsRoom1_Text_RaidCyrusHum
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_R1_CYRUS, SolaceonRuinsRoom1_Movement_FaceEast
    WaitMovement
    Message SolaceonRuinsRoom1_Text_RaidCyrusThreeLines
    WaitABPadPress
    Message SolaceonRuinsRoom1_Text_RaidCyrusGoAhead
    WaitABPadPress
    CloseMessage
    PlaySE SEQ_SE_DP_BEEP_sseq
    WaitSE SEQ_SE_DP_BEEP_sseq
    PlaySE SEQ_SE_DP_BEEP_sseq
    WaitSE SEQ_SE_DP_BEEP_sseq
    Message SolaceonRuinsRoom1_Text_RaidPoketchBuzzes
    WaitABPadPress
    Message SolaceonRuinsRoom1_Text_RaidRuthReadings
    WaitABPadPress
    CloseMessage
    // Cyrus goes on ahead, past the stair (he waits at the barrier in Room 7)
    ApplyMovement LOCALID_R1_CYRUS, SolaceonRuinsRoom1_Movement_CyrusAhead
    ApplyMovement LOCALID_PLAYER, SolaceonRuinsRoom1_Movement_WatchCyrus
    WaitMovement
    RemoveObject LOCALID_R1_CYRUS
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    ReleaseAll
    End

    .balign 4, 0
SolaceonRuinsRoom1_Movement_North1:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom1_Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom1_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom1_Movement_CyrusAhead:
    WalkNormalNorth 3
    WalkNormalEast
    WalkNormalNorth
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom1_Movement_WatchCyrus:
    Delay8 2
    FaceNorth
    EndMovement
