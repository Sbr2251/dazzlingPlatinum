#include "macros/scrcmd.inc"
#include "res/text/bank/pastoria_city_pokecenter_1f.h"
#include "res/field/maps/locals/pastoria_city_pokecenter_1f.h"


    ScriptEntry PastoriaCityPokecenter1F_Nurse
    ScriptEntry PastoriaCityPokecenter1F_BlackBelt
    ScriptEntry PastoriaCityPokecenter1F_SchoolKidF
    ScriptEntry PastoriaPC_Arc2Quiet
    ScriptEntry PastoriaPC_Arc2RowanTalk
    ScriptEntry PastoriaPC_Arc2LookerTalk
    ScriptEntry PastoriaPC_Arc2Quiet2
    ScriptEntry PastoriaPC_Arc2Photos
    ScriptEntry PastoriaPC_Arc2Briefing
    ScriptEntry PastoriaPC_Arc2Proof
    ScriptEntryEnd

PastoriaCityPokecenter1F_Nurse:
    SetVar VAR_0x8007, LOCALID_PASTORIA_NURSE
    CallCommonScript CommonScript_PokecenterNurse
    End

PastoriaCityPokecenter1F_BlackBelt:
    NPCMessage PastoriaCityPokecenter1F_Text_GreatMarshIsVast
    End

PastoriaCityPokecenter1F_SchoolKidF:
    NPCMessage PastoriaCityPokecenter1F_Text_GreatMarshWasSea
    End

PastoriaPC_Arc2Quiet:
PastoriaPC_Arc2Quiet2:
    End

PastoriaPC_Arc2RowanTalk:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message PastoriaPC_Text_Arc2RowanLab
    WaitButton
    CloseMessage
    ReleaseAll
    End

PastoriaPC_Arc2LookerTalk:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message PastoriaPC_Text_Arc2LookerAfter
    WaitButton
    CloseMessage
    ReleaseAll
    End

PastoriaPC_Arc2Photos:
    End

// Bring the player to (8,8), facing the table: walk from the door mat, or (blackout, other entries) fade there.
PastoriaPC_Arc2PlayerToTable:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8004, 8, PastoriaPC_Arc2PlayerFade
    GoToIfEq VAR_0x8005, 12, PastoriaPC_Arc2PlayerWalk4
    GoToIfEq VAR_0x8005, 11, PastoriaPC_Arc2PlayerWalk3
PastoriaPC_Arc2PlayerFade:
    FadeScreenOut
    WaitFadeScreen
    SetPosition LOCALID_PLAYER, 8, 0, 8, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    Return

PastoriaPC_Arc2PlayerWalk4:
    ApplyMovement LOCALID_PLAYER, PastoriaPC_Arc2Movement_North4
    WaitMovement
    Return

PastoriaPC_Arc2PlayerWalk3:
    ApplyMovement LOCALID_PLAYER, PastoriaPC_Arc2Movement_North3
    WaitMovement
    Return

// 2.21a, on-frame at 73
PastoriaPC_Arc2Briefing:
    LockAll
    GoToIfUnset FLAG_ARC2_PASTORIA_B, PastoriaPC_Arc2BriefingShown
    ClearFlag FLAG_ARC2_PASTORIA_B
    AddObject LOCALID_ARC2_BRIEF_LOOKER
    AddObject LOCALID_ARC2_BRIEF_CYRUS
    AddObject LOCALID_ARC2_BRIEF_RUTH
    AddObject LOCALID_ARC2_BRIEF_GARIUS
PastoriaPC_Arc2BriefingShown:
    Call PastoriaPC_Arc2PlayerToTable
    Message PastoriaPC_Text_Arc2BriefLookerSite
    WaitButton
    Message PastoriaPC_Text_Arc2BriefLookerTwo
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC2_BRIEF_LOOKER, PastoriaPC_Arc2Movement_FaceEast
    WaitMovement
    Message PastoriaPC_Text_Arc2BriefRuth
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC2_BRIEF_RUTH, PastoriaPC_Arc2Movement_FaceEast
    ApplyMovement LOCALID_ARC2_BRIEF_CYRUS, PastoriaPC_Arc2Movement_FaceEast
    ApplyMovement LOCALID_PLAYER, PastoriaPC_Arc2Movement_FaceEast
    WaitMovement
    BufferRivalName 0
    Message PastoriaPC_Text_Arc2BriefGarius
    WaitButton
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    HealParty
    SetVar VAR_ARC2_PROGRESS, 75
    SetFlag FLAG_ARC2_PASTORIA_B
    Warp MAP_HEADER_ROUTE_213, 687, 832, DIR_EAST
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

// 2.22, on-frame at 84 (s-raid's warp) or 85 (re-entry before it finished)
PastoriaPC_Arc2Proof:
    LockAll
    SetVar VAR_ARC2_PROGRESS, 85
    GoToIfUnset FLAG_ARC2_PASTORIA_C, PastoriaPC_Arc2ProofShown
    ClearFlag FLAG_ARC2_PASTORIA_C
    AddObject LOCALID_ARC2_ROWAN
    AddObject LOCALID_ARC2_PROOF_LOOKER
    AddObject LOCALID_ARC2_PROOF_RUTH
    AddObject LOCALID_ARC2_PROOF_CYRUS
PastoriaPC_Arc2ProofShown:
    Call PastoriaPC_Arc2PlayerToTable
    // The photographs on the table (the screenplay's 'sign'), read as the scene opens
    Message PastoriaPC_Text_Arc2Photos
    WaitButton
    Message PastoriaPC_Text_Arc2RowanSilence
    WaitButton
    Message PastoriaPC_Text_Arc2RowanBelieved
    WaitButton
    Message PastoriaPC_Text_Arc2RowanNotLikeThis
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC2_ROWAN, PastoriaPC_Arc2Movement_FaceWest
    WaitMovement
    Message PastoriaPC_Text_Arc2RowanLab
    WaitButton
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 86
    // Cyrus walks out toward Route 213; Ruth follows him
    ApplyMovement LOCALID_PLAYER, PastoriaPC_Arc2Movement_FaceSouth
    ApplyMovement LOCALID_ARC2_PROOF_CYRUS, PastoriaPC_Arc2Movement_CyrusOut
    WaitMovement
    RemoveObject LOCALID_ARC2_PROOF_CYRUS
    PlayFanfare SEQ_SE_DP_KAIDAN2_sseq
    WaitFanfare
    ApplyMovement LOCALID_ARC2_PROOF_RUTH, PastoriaPC_Arc2Movement_RuthOut
    WaitMovement
    RemoveObject LOCALID_ARC2_PROOF_RUTH
    PlayFanfare SEQ_SE_DP_KAIDAN2_sseq
    WaitFanfare
    // Polish #3: with Cyrus gone, Rowan's doubt, then the Calm Shard in the Resonator turns him
    ApplyMovement LOCALID_ARC2_ROWAN, PastoriaPC_Arc2Movement_FaceSouth
    ApplyMovement LOCALID_PLAYER, PastoriaPC_Arc2Movement_FaceNorth
    WaitMovement
    Message PastoriaPC_Text_Arc2RowanFile
    WaitButton
    Message PastoriaPC_Text_Arc2RowanKeepEye
    WaitButton
    Message PastoriaPC_Text_Arc2RowanResonator
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
PastoriaPC_Arc2Movement_North4:
    WalkNormalNorth 4
    EndMovement

    .balign 4, 0
PastoriaPC_Arc2Movement_North3:
    WalkNormalNorth 3
    EndMovement

    .balign 4, 0
PastoriaPC_Arc2Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
PastoriaPC_Arc2Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
PastoriaPC_Arc2Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
PastoriaPC_Arc2Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
PastoriaPC_Arc2Movement_CyrusOut:
    WalkNormalSouth 3
    WalkNormalWest 2
    WalkNormalSouth
    EndMovement

    .balign 4, 0
PastoriaPC_Arc2Movement_RuthOut:
    WalkNormalSouth 3
    WalkNormalEast 2
    WalkNormalSouth
    EndMovement
