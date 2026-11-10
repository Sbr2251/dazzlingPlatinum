#include "macros/scrcmd.inc"
#include "res/text/bank/veilstone_city_galactic_warehouse.h"
#include "res/field/maps/locals/veilstone_city_galactic_warehouse.h"

    ScriptEntry DepotArc2_OnTransition
    ScriptEntry DepotArc2_Entry
    ScriptEntry DepotArc2_Looker
    ScriptEntry DepotArc2_SentryTalk
    ScriptEntry DepotArc2_Step
    ScriptEntry DepotArc2_Office
    ScriptEntry DepotArc2_Manifest
    ScriptEntry DepotArc2_Trucks
    ScriptEntry DepotArc2_LookerStays
    ScriptEntry DepotArc2_TruckSign
    ScriptEntryEnd


DepotArc2_OnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_20
    GoToIfLt VAR_ARC2_PROGRESS, 51, DepotArc2_OnTransitionEnd
    GoToIfGe VAR_ARC2_PROGRESS, 54, DepotArc2_OnTransitionEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    GoToIfSet FLAG_ARC2_VEILSTONE_A, DepotArc2_OnTransitionCopied
    // Before the manifest: Looker at the side door, the entry scene runs once the map is up
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetVar VAR_MAP_LOCAL_0x01, 1
    GoTo DepotArc2_OnTransitionEnd
    End

// Back after the manifest: Looker is still up in the office (unseen), the sentries look away, the trucks wait
DepotArc2_OnTransitionCopied:
    SetObjectEventDir LOCALID_DEPOT_SENTRY_07, DIR_EAST
    SetObjectEventDir LOCALID_DEPOT_SENTRY_08, DIR_WEST
    SetVar VAR_MAP_LOCAL_0x09, 1
DepotArc2_OnTransitionEnd:
    End

DepotArc2_Entry:
    LockAll
    SetVar VAR_MAP_LOCAL_0x01, 0
    SetVar VAR_ARC2_PROGRESS, 52
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_FaceWest
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceEast
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2LookerSentries
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceNorth
    WaitMovement
    Call DepotArc2_StartStealth
    ReleaseAll
    End

DepotArc2_StartStealth:
    SetVar VAR_MAP_LOCAL_0x07, 6
    Call DepotArc2_FaceForBeat
    SetVar VAR_MAP_LOCAL_0x05, 1
    Return

// Talk to Looker: at the side door he repeats the plan; after the manifest (same visit) he waves you off
DepotArc2_Looker:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfEq VAR_MAP_LOCAL_0x0C, 1, DepotArc2_LookerNoise
    Message VeilstoneWarehouse_Text_Arc2LookerSentries
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

DepotArc2_LookerNoise:
    Message VeilstoneWarehouse_Text_Arc2LookerNoise
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_FaceWest
    WaitMovement
    ReleaseAll
    End

// Walking up to a sentry while the stealth is on is getting caught; afterwards they ignore you
DepotArc2_SentryTalk:
    GoToIfEq VAR_MAP_LOCAL_0x05, 1, DepotArc2_CaughtTalk
    LockAll
    ReleaseAll
    End

// ---------------------------------------------------------------------------------------------- the stealth
DepotArc2_Step:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    AddVar VAR_MAP_LOCAL_0x07, 1
    CallIfGe VAR_MAP_LOCAL_0x07, 8, DepotArc2_ResetBeat
    Call DepotArc2_FaceForBeat
    // Sentry 07 at (14,10): in = west (beats 0-3), away = east
    SetVar VAR_0x8006, 14
    SetVar VAR_0x8007, 10
    SetVar VAR_0x8008, DIR_EAST
    CallIfLt VAR_MAP_LOCAL_0x07, 4, DepotArc2_UseWest
    Call DepotArc2_CheckSight
    GoToIfEq VAR_RESULT, 1, DepotArc2_Caught07
    // Sentry 08 at (4,8): in = east (beats 0-2), away = west
    SetVar VAR_0x8006, 4
    SetVar VAR_0x8007, 8
    SetVar VAR_0x8008, DIR_WEST
    CallIfLt VAR_MAP_LOCAL_0x07, 3, DepotArc2_UseEast
    Call DepotArc2_CheckSight
    GoToIfEq VAR_RESULT, 1, DepotArc2_Caught08
    End

DepotArc2_ResetBeat:
    SetVar VAR_MAP_LOCAL_0x07, 0
    Return

DepotArc2_UseWest:
    SetVar VAR_0x8008, DIR_WEST
    Return

DepotArc2_UseEast:
    SetVar VAR_0x8008, DIR_EAST
    Return

// Turn the sentries for the current beat (only on the beats where something changes)
DepotArc2_FaceForBeat:
    CallIfEq VAR_MAP_LOCAL_0x07, 0, DepotArc2_BothIn
    CallIfEq VAR_MAP_LOCAL_0x07, 3, DepotArc2_08Away
    CallIfEq VAR_MAP_LOCAL_0x07, 4, DepotArc2_07Away
    CallIfEq VAR_MAP_LOCAL_0x07, 6, DepotArc2_BothAway
    CallIfEq VAR_MAP_LOCAL_0x07, 7, DepotArc2_BothGlance
    Return

DepotArc2_BothIn:
    ApplyMovement LOCALID_DEPOT_SENTRY_07, DepotArc2_Movement_FaceWest
    ApplyMovement LOCALID_DEPOT_SENTRY_08, DepotArc2_Movement_FaceEast
    WaitMovement
    Return

DepotArc2_08Away:
    ApplyMovement LOCALID_DEPOT_SENTRY_08, DepotArc2_Movement_FaceWest
    WaitMovement
    Return

DepotArc2_07Away:
    ApplyMovement LOCALID_DEPOT_SENTRY_07, DepotArc2_Movement_FaceEast
    WaitMovement
    Return

// (beat 6 is also the reset beat, so it re-asserts both 'away' facings)
DepotArc2_BothAway:
    ApplyMovement LOCALID_DEPOT_SENTRY_07, DepotArc2_Movement_FaceEast
    ApplyMovement LOCALID_DEPOT_SENTRY_08, DepotArc2_Movement_FaceWest
    WaitMovement
    Return

DepotArc2_BothGlance:
    ApplyMovement LOCALID_DEPOT_SENTRY_07, DepotArc2_Movement_GlanceFromEast
    ApplyMovement LOCALID_DEPOT_SENTRY_08, DepotArc2_Movement_GlanceFromWest
    WaitMovement
    Return

// In: VAR_0x8004/0x8005 player, VAR_0x8006/0x8007 sentry, VAR_0x8008 his facing.
// Out: VAR_RESULT 1 if he sees the player. Scratch: VAR_0x8009/0x800A = |dx|/|dz|,
// VAR_MAP_LOCAL_0x08/_9 = sign of dx/dz (0 player west/north of him, 1 same, 2 east/south), _A/_B along/across.
// (Same cone as the Arc 1 crate tail.)
DepotArc2_CheckSight:
    SetVar VAR_RESULT, 0
    SetVar VAR_MAP_LOCAL_0x08, 1
    SetVar VAR_0x8009, 0
    GoToIfEq VAR_0x8004, VAR_0x8006, DepotArc2_SightDZ
    GoToIfLt VAR_0x8004, VAR_0x8006, DepotArc2_SightWest
    SetVar VAR_MAP_LOCAL_0x08, 2
    SetVar VAR_0x8009, VAR_0x8004
    SubVar VAR_0x8009, VAR_0x8006
    GoTo DepotArc2_SightDZ
    End

DepotArc2_SightWest:
    SetVar VAR_MAP_LOCAL_0x08, 0
    SetVar VAR_0x8009, VAR_0x8006
    SubVar VAR_0x8009, VAR_0x8004
    GoTo DepotArc2_SightDZ
    End

DepotArc2_SightDZ:
    SetVar VAR_MAP_LOCAL_0x09, 1
    SetVar VAR_0x800A, 0
    GoToIfEq VAR_0x8005, VAR_0x8007, DepotArc2_SightAdjacent
    GoToIfLt VAR_0x8005, VAR_0x8007, DepotArc2_SightNorth
    SetVar VAR_MAP_LOCAL_0x09, 2
    SetVar VAR_0x800A, VAR_0x8005
    SubVar VAR_0x800A, VAR_0x8007
    GoTo DepotArc2_SightAdjacent
    End

DepotArc2_SightNorth:
    SetVar VAR_MAP_LOCAL_0x09, 0
    SetVar VAR_0x800A, VAR_0x8007
    SubVar VAR_0x800A, VAR_0x8005
    GoTo DepotArc2_SightAdjacent
    End

DepotArc2_SightAdjacent:
    SetVar VAR_MAP_LOCAL_0x0B, VAR_0x8009
    AddVar VAR_MAP_LOCAL_0x0B, VAR_0x800A
    GoToIfLe VAR_MAP_LOCAL_0x0B, 1, DepotArc2_Seen
    GoToIfEq VAR_0x8008, DIR_NORTH, DepotArc2_SightFaceNorth
    GoToIfEq VAR_0x8008, DIR_SOUTH, DepotArc2_SightFaceSouth
    GoToIfEq VAR_0x8008, DIR_WEST, DepotArc2_SightFaceWest
    GoTo DepotArc2_SightFaceEast
    End

DepotArc2_SightFaceNorth:
    GoToIfNe VAR_MAP_LOCAL_0x09, 0, DepotArc2_SightEnd
    GoTo DepotArc2_SightAlongZ
    End

DepotArc2_SightFaceSouth:
    GoToIfNe VAR_MAP_LOCAL_0x09, 2, DepotArc2_SightEnd
    GoTo DepotArc2_SightAlongZ
    End

DepotArc2_SightFaceWest:
    GoToIfNe VAR_MAP_LOCAL_0x08, 0, DepotArc2_SightEnd
    GoTo DepotArc2_SightAlongX
    End

DepotArc2_SightFaceEast:
    GoToIfNe VAR_MAP_LOCAL_0x08, 2, DepotArc2_SightEnd
    GoTo DepotArc2_SightAlongX
    End

DepotArc2_SightAlongZ:
    SetVar VAR_MAP_LOCAL_0x0A, VAR_0x800A
    SetVar VAR_MAP_LOCAL_0x0B, VAR_0x8009
    GoTo DepotArc2_SightCone
    End

DepotArc2_SightAlongX:
    SetVar VAR_MAP_LOCAL_0x0A, VAR_0x8009
    SetVar VAR_MAP_LOCAL_0x0B, VAR_0x800A
    GoTo DepotArc2_SightCone
    End

DepotArc2_SightCone:
    GoToIfGt VAR_MAP_LOCAL_0x0A, 6, DepotArc2_SightEnd
    GoToIfEq VAR_MAP_LOCAL_0x0A, 1, DepotArc2_SightWidth0
    GoToIfLe VAR_MAP_LOCAL_0x0A, 3, DepotArc2_SightWidth1
    GoToIfLe VAR_MAP_LOCAL_0x0B, 2, DepotArc2_Seen
    GoTo DepotArc2_SightEnd
    End

DepotArc2_SightWidth0:
    GoToIfEq VAR_MAP_LOCAL_0x0B, 0, DepotArc2_Seen
    GoTo DepotArc2_SightEnd
    End

DepotArc2_SightWidth1:
    GoToIfLe VAR_MAP_LOCAL_0x0B, 1, DepotArc2_Seen
    GoTo DepotArc2_SightEnd
    End

DepotArc2_Seen:
    SetVar VAR_RESULT, 1
DepotArc2_SightEnd:
    Return

DepotArc2_Caught07:
    LockAll
    ApplyMovement LOCALID_DEPOT_SENTRY_07, DepotArc2_Movement_Notice
    WaitMovement
    GoTo DepotArc2_CaughtMessage
    End

DepotArc2_Caught08:
    LockAll
    ApplyMovement LOCALID_DEPOT_SENTRY_08, DepotArc2_Movement_Notice
    WaitMovement
    GoTo DepotArc2_CaughtMessage
    End

DepotArc2_CaughtTalk:
    LockAll
    FacePlayer
    GoTo DepotArc2_CaughtMessage
    End

DepotArc2_CaughtMessage:
    Message VeilstoneWarehouse_Text_Arc2Spotted
    WaitABPadPress
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    SetPosition LOCALID_PLAYER, 8, 0, 11, DIR_NORTH
    SetVar VAR_MAP_LOCAL_0x07, 6
    Call DepotArc2_FaceForBeat
    WaitTime 10, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_FaceWest
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceEast
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2LookerAgain
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceNorth
    WaitMovement
    ReleaseAll
    End

// ------------------------------------------------------------------------------------------------ the office
// The corridor top (8-9, 4): the stealth is over. Looker slips up the corridor behind the player.
DepotArc2_Office:
    LockAll
    SetVar VAR_MAP_LOCAL_0x05, 0
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_LookerUpCorridor
    WaitMovement
    ReleaseAll
    End

DepotArc2_Manifest:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfSet FLAG_ARC2_VEILSTONE_A, DepotArc2_ManifestAgain
    Message VeilstoneWarehouse_Text_Arc2Manifest
    WaitABPadPress
    CloseMessage
    // Looker reads over the player's shoulder (the player reads from 8,3; Looker waits at 9,5)
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_LookerToDesk
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2LookerThereItIs
    WaitABPadPress
    CloseMessage
    SetFlag FLAG_ARC2_VEILSTONE_A
    // The sentries go back to watching the walls; the trucks are the next stop
    ApplyMovement LOCALID_DEPOT_SENTRY_07, DepotArc2_Movement_FaceEast
    ApplyMovement LOCALID_DEPOT_SENTRY_08, DepotArc2_Movement_FaceWest
    WaitMovement
    SetVar VAR_MAP_LOCAL_0x09, 1
    SetVar VAR_MAP_LOCAL_0x0C, 1
    ReleaseAll
    End

DepotArc2_ManifestAgain:
    Message VeilstoneWarehouse_Text_Arc2Manifest
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

// Leaving the office: Looker stays at the desk, out of the scene until the end
DepotArc2_LookerStays:
    SetVar VAR_MAP_LOCAL_0x0C, 0
    RemoveObject LOCALID_DEPOT_LOOKER
    End

// ------------------------------------------------------------------------------------------------ the trucks
DepotArc2_Trucks:
    GoToIfNe VAR_MAP_LOCAL_0x09, 1, DepotArc2_CaughtTalkTrucks
    LockAll
    SetVar VAR_MAP_LOCAL_0x09, 0
    // The player squares up at (12,10), under guard 05
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 13, DepotArc2_PlayerStepWest
    CallIfEq VAR_0x8005, 11, DepotArc2_PlayerStepNorth
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceNorth
    ApplyMovement LOCALID_DEPOT_GUARD_05, DepotArc2_Movement_NoticeSouth
    ApplyMovement LOCALID_DEPOT_GUARD_06, DepotArc2_Movement_NoticeSouth
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2GuardKid
    WaitABPadPress
    CloseMessage
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_ARC2_05
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, DepotArc2_Lost
    Message VeilstoneWarehouse_Text_Arc2GuardSecond
    WaitABPadPress
    CloseMessage
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_ARC2_06
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, DepotArc2_Lost
    // Indra walks in by the side door; the grunts back off toward the trucks
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_20
    AddObject LOCALID_DEPOT_INDRA
    ApplyMovement LOCALID_DEPOT_INDRA, DepotArc2_Movement_IndraIn
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2IndraEnough
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_DEPOT_GUARD_05, DepotArc2_Movement_BackOff
    ApplyMovement LOCALID_DEPOT_GUARD_06, DepotArc2_Movement_BackOff
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceWest
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2IndraRowans
    WaitABPadPress
    CloseMessage
    // The trucks pull out; the bay door shuts
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_DEPOT_GUARD_05
    RemoveObject LOCALID_DEPOT_GUARD_06
    RemoveObject LOCALID_DEPOT_SENTRY_07
    RemoveObject LOCALID_DEPOT_SENTRY_08
    PlaySE SEQ_SE_DP_DODON_sseq
    WaitSE SEQ_SE_DP_DODON_sseq
    PlaySE SEQ_SE_DP_DOOR10_sseq
    WaitSE SEQ_SE_DP_DOOR10_sseq
    FadeScreenIn
    WaitFadeScreen
    StartTrainerBattle TRAINER_INDRA_DEPOT
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, DepotArc2_Lost
    Message VeilstoneWarehouse_Text_Arc2IndraAfter
    WaitABPadPress
    Message VeilstoneWarehouse_Text_Arc2IndraGoHome
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_DEPOT_INDRA, DepotArc2_Movement_IndraOut
    WaitMovement
    RemoveObject LOCALID_DEPOT_INDRA
    PlayFanfare SEQ_SE_DP_DOOR_OPEN_sseq
    WaitFanfare
    // Looker comes down from the office
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetObjectEventPos LOCALID_DEPOT_LOOKER, 8, 5
    AddObject LOCALID_DEPOT_LOOKER
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_LookerDown
    WaitMovement
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceWest
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2LookerEveryPage
    WaitABPadPress
    Message VeilstoneWarehouse_Text_Arc2LookerFree
    WaitABPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 54
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_LookerOut
    WaitMovement
    RemoveObject LOCALID_DEPOT_LOOKER
    PlayFanfare SEQ_SE_DP_DOOR_OPEN_sseq
    WaitFanfare
    ReleaseAll
    End

// Talking to a truck guard before the manifest: caught like a sentry; after the fight nothing
DepotArc2_CaughtTalkTrucks:
    GoToIfEq VAR_MAP_LOCAL_0x05, 1, DepotArc2_CaughtTalk
    LockAll
    ReleaseAll
    End

DepotArc2_PlayerStepWest:
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_West1
    WaitMovement
    Return

DepotArc2_PlayerStepNorth:
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_North1
    WaitMovement
    Return

DepotArc2_Lost:
    BlackOutFromBattle
    ReleaseAll
    End

DepotArc2_TruckSign:
    GoToIfLt VAR_ARC2_PROGRESS, 54, DepotArc2_TruckSignEnd
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message VeilstoneWarehouse_Text_Arc2Empty
    WaitABPadPress
    CloseMessage
    ReleaseAll
DepotArc2_TruckSignEnd:
    End

    .balign 4, 0
DepotArc2_Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
DepotArc2_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
DepotArc2_Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
DepotArc2_Movement_GlanceFromEast:
    FaceNorth
    Delay4
    FaceEast
    EndMovement

    .balign 4, 0
DepotArc2_Movement_GlanceFromWest:
    FaceNorth
    Delay4
    FaceWest
    EndMovement

    .balign 4, 0
DepotArc2_Movement_Notice:
    EmoteExclamationMark
    Delay8
    EndMovement

    .balign 4, 0
DepotArc2_Movement_NoticeSouth:
    FaceSouth
    EmoteExclamationMark
    Delay8
    EndMovement

    .balign 4, 0
DepotArc2_Movement_LookerUpCorridor:
    WalkNormalNorth 6
    EndMovement

    .balign 4, 0
DepotArc2_Movement_LookerToDesk:
    WalkNormalNorth 2
    FaceWest
    EndMovement

    .balign 4, 0
DepotArc2_Movement_West1:
    WalkNormalWest
    EndMovement

    .balign 4, 0
DepotArc2_Movement_North1:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
DepotArc2_Movement_IndraIn:
    WalkNormalNorth
    WalkNormalEast 3
    EndMovement

    .balign 4, 0
DepotArc2_Movement_BackOff:
    WalkSlowNorth
    FaceSouth
    EndMovement

    .balign 4, 0
DepotArc2_Movement_IndraOut:
    WalkNormalWest 3
    WalkNormalSouth
    EndMovement

    .balign 4, 0
DepotArc2_Movement_LookerDown:
    WalkNormalSouth 5
    WalkNormalEast 3
    FaceEast
    EndMovement

    .balign 4, 0
DepotArc2_Movement_LookerOut:
    WalkNormalWest 3
    WalkNormalSouth
    EndMovement
