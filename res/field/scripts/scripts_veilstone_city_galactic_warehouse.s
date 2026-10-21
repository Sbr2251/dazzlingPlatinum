#include "macros/scrcmd.inc"
#include "res/text/bank/veilstone_city_galactic_warehouse.h"
#include "res/field/events/events_veilstone_city_galactic_warehouse.h"

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 2, workstream s-veilstone: 2.17a, the Eclipse depot heist (stock Galactic warehouse).
//
// The stock Galactic content is gone: the HQ doors, the HM02 (Fly) ball (D11), Looker's storage-key scene; the
// stairs at (13,3) now lead out to the street instead of Galactic HQ B2F.
//
// Flow (VAR_ARC2_PROGRESS reads 51, sets 52 on entry and 54 at the end):
//   1. The player comes in by the side door (8,11). Looker (9,11) explains the sentries.
//   2. Stealth, stepped like the Arc 1 crate tail (scripts_jubilife_city.s): a coord event over the hall and the
//      corridor (x1-15, z5-11) runs on every step while VAR_MAP_LOCAL_5 = 1, and each step is one beat (0-7) of the
//      two sentries' look cycle:
//        sentry 07 at (14,10): beats 0-3 looks west down the hall, 4-7 looks east at the wall
//        sentry 08 at (4,8):   beats 0-2 looks east up the corridor mouth, 3-7 looks west at the store room
//        both glance (a quick look north) on beat 7, the step before they turn back in.
//      Cone: 1 tile at range 1, 3 wide at 2-3, 5 wide at 4-6, plus the four tiles next to him.
//      Seen: "Scram, kid!", Looker's "Again. Quieter.", a fade, back to the side door at beat 6.
//   3. The office (z4 at the corridor top) ends the stealth. Looker follows up. The manifest (a book on the desk,
//      7,3): Route 213. FLAG_ARC2_VEILSTONE_A is set; leaving now keeps that (the stealth is not repeated).
//   4. The trucks (east alcove): guards 05 and 06 battle in turn, Indra walks in from the side door, the trucks
//      go, Indra battles (TRAINER_INDRA_DEPOT), leaves; Looker comes down from the office. Set 54.
//
// Flags: FLAG_ARC2_VEILSTONE_A (0x0946) manifest copied. Map-local hide flags (recomputed on load):
//   0x0030 Looker, 0x0031 sentries, 0x0032 truck guards, 0x0033 manifest book, 0x0034 Indra.
// Map-local vars: _1 run the entry scene (frame table; _0 cannot be used there: its low byte 0x00 ends the table), _5 stealth on, _7 beat, _8-_B sight scratch,
//   _9 truck trigger armed, _C Looker-stays-at-the-desk trigger armed (after the manifest).

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
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    SetFlag FLAG_UNK_0x0032
    SetFlag FLAG_UNK_0x0033
    SetFlag FLAG_UNK_0x0034
    GoToIfLt VAR_ARC2_PROGRESS, 51, DepotArc2_OnTransitionEnd
    GoToIfGe VAR_ARC2_PROGRESS, 54, DepotArc2_OnTransitionEnd
    ClearFlag FLAG_UNK_0x0031
    ClearFlag FLAG_UNK_0x0032
    ClearFlag FLAG_UNK_0x0033
    GoToIfSet FLAG_ARC2_VEILSTONE_A, DepotArc2_OnTransitionCopied
    // Before the manifest: Looker at the side door, the entry scene runs once the map is up
    ClearFlag FLAG_UNK_0x0030
    SetVar VAR_MAP_LOCAL_1, 1
    GoTo DepotArc2_OnTransitionEnd
    End

// Back after the manifest: Looker is still up in the office (unseen), the sentries look away, the trucks wait
DepotArc2_OnTransitionCopied:
    SetObjectEventDir LOCALID_DEPOT_SENTRY_07, DIR_EAST
    SetObjectEventDir LOCALID_DEPOT_SENTRY_08, DIR_WEST
    SetVar VAR_MAP_LOCAL_9, 1
DepotArc2_OnTransitionEnd:
    End

DepotArc2_Entry:
    LockAll
    SetVar VAR_MAP_LOCAL_1, 0
    SetVar VAR_ARC2_PROGRESS, 52
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_FaceWest
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceEast
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2LookerSentries
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceNorth
    WaitMovement
    Call DepotArc2_StartStealth
    ReleaseAll
    End

DepotArc2_StartStealth:
    SetVar VAR_MAP_LOCAL_7, 6
    Call DepotArc2_FaceForBeat
    SetVar VAR_MAP_LOCAL_5, 1
    Return

// Talk to Looker: at the side door he repeats the plan; after the manifest (same visit) he waves you off
DepotArc2_Looker:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfEq VAR_MAP_LOCAL_C, 1, DepotArc2_LookerNoise
    Message VeilstoneWarehouse_Text_Arc2LookerSentries
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

DepotArc2_LookerNoise:
    Message VeilstoneWarehouse_Text_Arc2LookerNoise
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_FaceWest
    WaitMovement
    ReleaseAll
    End

// Walking up to a sentry while the stealth is on is getting caught; afterwards they ignore you
DepotArc2_SentryTalk:
    GoToIfEq VAR_MAP_LOCAL_5, 1, DepotArc2_CaughtTalk
    LockAll
    ReleaseAll
    End

// ---------------------------------------------------------------------------------------------- the stealth
DepotArc2_Step:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    AddVar VAR_MAP_LOCAL_7, 1
    CallIfGe VAR_MAP_LOCAL_7, 8, DepotArc2_ResetBeat
    Call DepotArc2_FaceForBeat
    // Sentry 07 at (14,10): in = west (beats 0-3), away = east
    SetVar VAR_0x8006, 14
    SetVar VAR_0x8007, 10
    SetVar VAR_0x8008, DIR_EAST
    CallIfLt VAR_MAP_LOCAL_7, 4, DepotArc2_UseWest
    Call DepotArc2_CheckSight
    GoToIfEq VAR_RESULT, 1, DepotArc2_Caught07
    // Sentry 08 at (4,8): in = east (beats 0-2), away = west
    SetVar VAR_0x8006, 4
    SetVar VAR_0x8007, 8
    SetVar VAR_0x8008, DIR_WEST
    CallIfLt VAR_MAP_LOCAL_7, 3, DepotArc2_UseEast
    Call DepotArc2_CheckSight
    GoToIfEq VAR_RESULT, 1, DepotArc2_Caught08
    End

DepotArc2_ResetBeat:
    SetVar VAR_MAP_LOCAL_7, 0
    Return

DepotArc2_UseWest:
    SetVar VAR_0x8008, DIR_WEST
    Return

DepotArc2_UseEast:
    SetVar VAR_0x8008, DIR_EAST
    Return

// Turn the sentries for the current beat (only on the beats where something changes)
DepotArc2_FaceForBeat:
    CallIfEq VAR_MAP_LOCAL_7, 0, DepotArc2_BothIn
    CallIfEq VAR_MAP_LOCAL_7, 3, DepotArc2_08Away
    CallIfEq VAR_MAP_LOCAL_7, 4, DepotArc2_07Away
    CallIfEq VAR_MAP_LOCAL_7, 6, DepotArc2_BothAway
    CallIfEq VAR_MAP_LOCAL_7, 7, DepotArc2_BothGlance
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
// VAR_MAP_LOCAL_8/_9 = sign of dx/dz (0 player west/north of him, 1 same, 2 east/south), _A/_B along/across.
// (Same cone as the Arc 1 crate tail.)
DepotArc2_CheckSight:
    SetVar VAR_RESULT, 0
    SetVar VAR_MAP_LOCAL_8, 1
    SetVar VAR_0x8009, 0
    GoToIfEq VAR_0x8004, VAR_0x8006, DepotArc2_SightDZ
    GoToIfLt VAR_0x8004, VAR_0x8006, DepotArc2_SightWest
    SetVar VAR_MAP_LOCAL_8, 2
    SetVar VAR_0x8009, VAR_0x8004
    SubVar VAR_0x8009, VAR_0x8006
    GoTo DepotArc2_SightDZ
    End

DepotArc2_SightWest:
    SetVar VAR_MAP_LOCAL_8, 0
    SetVar VAR_0x8009, VAR_0x8006
    SubVar VAR_0x8009, VAR_0x8004
    GoTo DepotArc2_SightDZ
    End

DepotArc2_SightDZ:
    SetVar VAR_MAP_LOCAL_9, 1
    SetVar VAR_0x800A, 0
    GoToIfEq VAR_0x8005, VAR_0x8007, DepotArc2_SightAdjacent
    GoToIfLt VAR_0x8005, VAR_0x8007, DepotArc2_SightNorth
    SetVar VAR_MAP_LOCAL_9, 2
    SetVar VAR_0x800A, VAR_0x8005
    SubVar VAR_0x800A, VAR_0x8007
    GoTo DepotArc2_SightAdjacent
    End

DepotArc2_SightNorth:
    SetVar VAR_MAP_LOCAL_9, 0
    SetVar VAR_0x800A, VAR_0x8007
    SubVar VAR_0x800A, VAR_0x8005
    GoTo DepotArc2_SightAdjacent
    End

DepotArc2_SightAdjacent:
    SetVar VAR_MAP_LOCAL_B, VAR_0x8009
    AddVar VAR_MAP_LOCAL_B, VAR_0x800A
    GoToIfLe VAR_MAP_LOCAL_B, 1, DepotArc2_Seen
    GoToIfEq VAR_0x8008, DIR_NORTH, DepotArc2_SightFaceNorth
    GoToIfEq VAR_0x8008, DIR_SOUTH, DepotArc2_SightFaceSouth
    GoToIfEq VAR_0x8008, DIR_WEST, DepotArc2_SightFaceWest
    GoTo DepotArc2_SightFaceEast
    End

DepotArc2_SightFaceNorth:
    GoToIfNe VAR_MAP_LOCAL_9, 0, DepotArc2_SightEnd
    GoTo DepotArc2_SightAlongZ
    End

DepotArc2_SightFaceSouth:
    GoToIfNe VAR_MAP_LOCAL_9, 2, DepotArc2_SightEnd
    GoTo DepotArc2_SightAlongZ
    End

DepotArc2_SightFaceWest:
    GoToIfNe VAR_MAP_LOCAL_8, 0, DepotArc2_SightEnd
    GoTo DepotArc2_SightAlongX
    End

DepotArc2_SightFaceEast:
    GoToIfNe VAR_MAP_LOCAL_8, 2, DepotArc2_SightEnd
    GoTo DepotArc2_SightAlongX
    End

DepotArc2_SightAlongZ:
    SetVar VAR_MAP_LOCAL_A, VAR_0x800A
    SetVar VAR_MAP_LOCAL_B, VAR_0x8009
    GoTo DepotArc2_SightCone
    End

DepotArc2_SightAlongX:
    SetVar VAR_MAP_LOCAL_A, VAR_0x8009
    SetVar VAR_MAP_LOCAL_B, VAR_0x800A
    GoTo DepotArc2_SightCone
    End

DepotArc2_SightCone:
    GoToIfGt VAR_MAP_LOCAL_A, 6, DepotArc2_SightEnd
    GoToIfEq VAR_MAP_LOCAL_A, 1, DepotArc2_SightWidth0
    GoToIfLe VAR_MAP_LOCAL_A, 3, DepotArc2_SightWidth1
    GoToIfLe VAR_MAP_LOCAL_B, 2, DepotArc2_Seen
    GoTo DepotArc2_SightEnd
    End

DepotArc2_SightWidth0:
    GoToIfEq VAR_MAP_LOCAL_B, 0, DepotArc2_Seen
    GoTo DepotArc2_SightEnd
    End

DepotArc2_SightWidth1:
    GoToIfLe VAR_MAP_LOCAL_B, 1, DepotArc2_Seen
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
    WaitABXPadPress
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    SetPosition LOCALID_PLAYER, 8, 0, 11, DIR_NORTH
    SetVar VAR_MAP_LOCAL_7, 6
    Call DepotArc2_FaceForBeat
    WaitTime 10, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_FaceWest
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceEast
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2LookerAgain
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceNorth
    WaitMovement
    ReleaseAll
    End

// ------------------------------------------------------------------------------------------------ the office
// The corridor top (8-9, 4): the stealth is over. Looker slips up the corridor behind the player.
DepotArc2_Office:
    LockAll
    SetVar VAR_MAP_LOCAL_5, 0
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_LookerUpCorridor
    WaitMovement
    ReleaseAll
    End

DepotArc2_Manifest:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfSet FLAG_ARC2_VEILSTONE_A, DepotArc2_ManifestAgain
    Message VeilstoneWarehouse_Text_Arc2Manifest
    WaitABXPadPress
    CloseMessage
    // Looker reads over the player's shoulder (the player reads from 8,3; Looker waits at 9,5)
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_LookerToDesk
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2LookerThereItIs
    WaitABXPadPress
    CloseMessage
    SetFlag FLAG_ARC2_VEILSTONE_A
    // The sentries go back to watching the walls; the trucks are the next stop
    ApplyMovement LOCALID_DEPOT_SENTRY_07, DepotArc2_Movement_FaceEast
    ApplyMovement LOCALID_DEPOT_SENTRY_08, DepotArc2_Movement_FaceWest
    WaitMovement
    SetVar VAR_MAP_LOCAL_9, 1
    SetVar VAR_MAP_LOCAL_C, 1
    ReleaseAll
    End

DepotArc2_ManifestAgain:
    Message VeilstoneWarehouse_Text_Arc2Manifest
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// Leaving the office: Looker stays at the desk, out of the scene until the end
DepotArc2_LookerStays:
    SetVar VAR_MAP_LOCAL_C, 0
    RemoveObject LOCALID_DEPOT_LOOKER
    End

// ------------------------------------------------------------------------------------------------ the trucks
DepotArc2_Trucks:
    GoToIfNe VAR_MAP_LOCAL_9, 1, DepotArc2_CaughtTalkTrucks
    LockAll
    SetVar VAR_MAP_LOCAL_9, 0
    // The player squares up at (12,10), under guard 05
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 13, DepotArc2_PlayerStepWest
    CallIfEq VAR_0x8005, 11, DepotArc2_PlayerStepNorth
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceNorth
    ApplyMovement LOCALID_DEPOT_GUARD_05, DepotArc2_Movement_NoticeSouth
    ApplyMovement LOCALID_DEPOT_GUARD_06, DepotArc2_Movement_NoticeSouth
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2GuardKid
    WaitABXPadPress
    CloseMessage
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_ARC2_05
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, DepotArc2_Lost
    Message VeilstoneWarehouse_Text_Arc2GuardSecond
    WaitABXPadPress
    CloseMessage
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_ARC2_06
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, DepotArc2_Lost
    // Indra walks in by the side door; the grunts back off toward the trucks
    ClearFlag FLAG_UNK_0x0034
    AddObject LOCALID_DEPOT_INDRA
    ApplyMovement LOCALID_DEPOT_INDRA, DepotArc2_Movement_IndraIn
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2IndraEnough
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_DEPOT_GUARD_05, DepotArc2_Movement_BackOff
    ApplyMovement LOCALID_DEPOT_GUARD_06, DepotArc2_Movement_BackOff
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceWest
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2IndraRowans
    WaitABXPadPress
    CloseMessage
    // The trucks pull out; the bay door shuts
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_DEPOT_GUARD_05
    RemoveObject LOCALID_DEPOT_GUARD_06
    RemoveObject LOCALID_DEPOT_SENTRY_07
    RemoveObject LOCALID_DEPOT_SENTRY_08
    PlayFanfare SEQ_SE_DP_DODON
    WaitFanfare SEQ_SE_DP_DODON
    PlayFanfare SEQ_SE_DP_DOOR10
    WaitFanfare SEQ_SE_DP_DOOR10
    FadeScreenIn
    WaitFadeScreen
    StartTrainerBattle TRAINER_INDRA_DEPOT
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, DepotArc2_Lost
    Message VeilstoneWarehouse_Text_Arc2IndraAfter
    WaitABXPadPress
    Message VeilstoneWarehouse_Text_Arc2IndraGoHome
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_DEPOT_INDRA, DepotArc2_Movement_IndraOut
    WaitMovement
    RemoveObject LOCALID_DEPOT_INDRA
    PlayFanfare SEQ_SE_DP_DOOR_OPEN
    WaitFanfare SEQ_SE_DP_DOOR_OPEN
    // Looker comes down from the office
    ClearFlag FLAG_UNK_0x0030
    SetObjectEventPos LOCALID_DEPOT_LOOKER, 8, 5
    AddObject LOCALID_DEPOT_LOOKER
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_LookerDown
    WaitMovement
    ApplyMovement LOCALID_PLAYER, DepotArc2_Movement_FaceWest
    WaitMovement
    Message VeilstoneWarehouse_Text_Arc2LookerEveryPage
    WaitABXPadPress
    Message VeilstoneWarehouse_Text_Arc2LookerFree
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 54
    SetFlag FLAG_UNK_0x0032
    SetFlag FLAG_UNK_0x0031
    ApplyMovement LOCALID_DEPOT_LOOKER, DepotArc2_Movement_LookerOut
    WaitMovement
    RemoveObject LOCALID_DEPOT_LOOKER
    PlayFanfare SEQ_SE_DP_DOOR_OPEN
    WaitFanfare SEQ_SE_DP_DOOR_OPEN
    ReleaseAll
    End

// Talking to a truck guard before the manifest: caught like a sentry; after the fight nothing
DepotArc2_CaughtTalkTrucks:
    GoToIfEq VAR_MAP_LOCAL_5, 1, DepotArc2_CaughtTalk
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
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message VeilstoneWarehouse_Text_Arc2Empty
    WaitABXPadPress
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
