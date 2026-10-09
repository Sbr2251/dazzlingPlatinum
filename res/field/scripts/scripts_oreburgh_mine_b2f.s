#include "macros/scrcmd.inc"
#include "res/text/bank/oreburgh_mine_b2f.h"
#include "res/field/events/events_oreburgh_mine_b2f.h"


    ScriptEntry _0016
    ScriptEntry _00FC
    ScriptEntry _011B
    ScriptEntry _013A
    ScriptEntry _0159
    ScriptEntry OreburghMineB2F_OnTransition
    ScriptEntry OreburghMineB2F_Arc1OnFrameRift
    ScriptEntry OreburghMineB2F_Arc1SealedTunnel
    ScriptEntryEnd

_0016:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoTo _0034

OreburghMineB2F_Unused:
    ApplyMovement 0, OreburghMineB2F_UnusedMovement2
    WaitMovement
    GoTo _0044

_0034:
    ApplyMovement 0, _00D8
    WaitMovement
    GoTo _0044

_0044:
    Message 0
    CloseMessage
    ScrCmd_29E 2, VAR_0x8005
    WaitTime 10, VAR_RESULT
    RemoveObject 1
_0059:
    WaitTime 1, VAR_RESULT
    GoToIfEq VAR_0x8005, 0, _0059
    FacePlayer
    Message 1
    CloseMessage
    GoTo _0091

OreburghMineB2F_Unused2:
    ApplyMovement 0, OreburghMineB2F_UnusedMovement
    ApplyMovement LOCALID_PLAYER, OreburghMineB2F_UnusedMovement3
    WaitMovement
    GoTo _00A1

_0091:
    ApplyMovement 0, _00C0
    WaitMovement
    GoTo _00A1

_00A1:
    RemoveObject 0
    SetFlag FLAG_UNK_0x007A
    SetFlag FLAG_UNK_0x017C
    ReleaseAll
    End

    .balign 4, 0
OreburghMineB2F_UnusedMovement:
    WalkNormalNorth
    WalkNormalEast 10
    EndMovement

    .balign 4, 0
_00C0:
    WalkNormalEast 10
    EndMovement

OreburghMineB2F_UnusedMovement2:
    Delay8 2
    WalkOnSpotNormalNorth
    Delay8 4
    EndMovement

    .balign 4, 0
_00D8:
    Delay8 2
    WalkOnSpotNormalEast
    Delay8 4
    EndMovement

OreburghMineB2F_UnusedMovement3:
    Delay8
    WalkOnSpotNormalNorth
    Delay8 2
    WalkOnSpotNormalEast
    EndMovement

_00FC:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_MACHOP
    Message 2
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_011B:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_MACHOP
    Message 3
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_013A:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_MACHOP
    Message 4
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0159:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 5
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// Arc 1 (scenes 13-14). The rubble seal over the north-west bay (8..10,15) is shown before the Coal Badge.
// At VAR_ARC1_PROGRESS 15 the seal is gone and the rift, Garius, Rowan and Ruth are in place for the rift
// scene (Rowan and Ruth wait up the north shaft, out of view). From 16 on, all of it is hidden.
// Roark (local 0) has always been met by 15, so he stays hidden here until the scene brings him back.
OreburghMineB2F_OnTransition:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    SetFlag FLAG_HIDE_ARC1_MINE_SILHOUETTE
    GoToIfGe VAR_ARC1_PROGRESS, 16, OreburghMineB2F_Arc1SetStateDone
    GoToIfEq VAR_ARC1_PROGRESS, 15, OreburghMineB2F_Arc1SetStateRift
    ClearFlag FLAG_HIDE_ARC1_MINE_SEAL
    SetFlag FLAG_HIDE_ARC1_MINE_CAST
    SetFlag FLAG_HIDE_ARC1_MINE_RIFT
    End

OreburghMineB2F_Arc1SetStateRift:
    SetFlag FLAG_UNK_0x018A
    SetFlag FLAG_HIDE_ARC1_MINE_SEAL
    ClearFlag FLAG_HIDE_ARC1_MINE_CAST
    ClearFlag FLAG_HIDE_ARC1_MINE_RIFT
    End

OreburghMineB2F_Arc1SetStateDone:
    SetFlag FLAG_UNK_0x018A
    SetFlag FLAG_HIDE_ARC1_MINE_SEAL
    SetFlag FLAG_HIDE_ARC1_MINE_CAST
    SetFlag FLAG_HIDE_ARC1_MINE_RIFT
    End

// Frame script at VAR_ARC1_PROGRESS 15. The player arrives at (12,17) facing west; Garius is at (9,16) facing
// the rift at (9,15). Rowan (15,11) and Ruth (16,11) come down the north shaft to (13,16) and (14,16).
// Roark (local 0) follows later to (13,17), behind the player. Ends at 16 with the END OF ARC 1 card; the
// player stays at (12,17) and walks out normally.
OreburghMineB2F_Arc1OnFrameRift:
    LockAll
    WaitTime 10, VAR_RESULT
    // Rowan and Ruth arrive
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, OreburghMineB2F_Movement_Arc1RowanArrive
    ApplyMovement LOCALID_ARC1_COUNTERPART, OreburghMineB2F_Movement_Arc1RuthArrive
    WaitMovement
    ApplyMovement LOCALID_ARC1_RIVAL, OreburghMineB2F_Movement_Arc1FaceEast
    ApplyMovement LOCALID_PLAYER, OreburghMineB2F_Movement_Arc1FaceEast
    WaitMovement
    Message OreburghMineB2F_Text_Arc1RowanAnotherOne
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC1_RIVAL, OreburghMineB2F_Movement_Arc1FaceNorth
    ApplyMovement LOCALID_PLAYER, OreburghMineB2F_Movement_Arc1FaceWest
    WaitMovement
    WaitTime 20, VAR_RESULT
    // Through the rift, a huge violet Hitmonlee rears up and roars, and for a moment a far larger shadow
    // passes behind it (Giratina; a 2-4 frame black blip that nobody reacts to). Then it's gone in a flash.
    ClearFlag FLAG_HIDE_ARC1_MINE_SILHOUETTE
    AddObject LOCALID_ARC1_SILHOUETTE
    PlayCry SPECIES_HITMONLEE
    ShakeCamera 16, 4
    FadeScreen 1, 1, FADE_TYPE_BRIGHTNESS_OUT, COLOR_BLACK
    WaitFadeScreen
    FadeScreen 1, 1, FADE_TYPE_BRIGHTNESS_IN, COLOR_BLACK
    WaitFadeScreen
    ShakeCamera 12, 2
    WaitCry
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    RemoveObject LOCALID_ARC1_SILHOUETTE
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_ARC1_RIVAL, OreburghMineB2F_Movement_Arc1ExclamationMark
    WaitMovement
    BufferRivalName 0
    Message OreburghMineB2F_Text_Arc1GariusGiantHitmonlee
    WaitABXPadPress
    CloseMessage
    // Rowan explains totems
    ApplyMovement LOCALID_ARC1_RIVAL, OreburghMineB2F_Movement_Arc1FaceEast
    ApplyMovement LOCALID_PLAYER, OreburghMineB2F_Movement_Arc1FaceEast
    WaitMovement
    Message OreburghMineB2F_Text_Arc1RowanTheShard
    WaitABXPadPress
    CloseMessage
    Message OreburghMineB2F_Text_Arc1RowanTheMawile
    WaitABXPadPress
    CloseMessage
    Message OreburghMineB2F_Text_Arc1RowanATotem
    WaitABXPadPress
    CloseMessage
    BufferCounterpartName 2
    Message OreburghMineB2F_Text_Arc1RuthPullItOut
    WaitABXPadPress
    CloseMessage
    Message OreburghMineB2F_Text_Arc1RowanNotFromThisSide
    WaitABXPadPress
    CloseMessage
    BufferRivalName 0
    Message OreburghMineB2F_Text_Arc1GariusEasy
    WaitABXPadPress
    CloseMessage
    Message OreburghMineB2F_Text_Arc1RowanWithoutAGuide
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, OreburghMineB2F_Movement_Arc1FaceWest
    WaitMovement
    Message OreburghMineB2F_Text_Arc1RowanWhyThisRift
    WaitABXPadPress
    CloseMessage
    // The rift shudders and shrinks to nothing
    ApplyMovement LOCALID_ARC1_RIVAL, OreburghMineB2F_Movement_Arc1FaceNorth
    ApplyMovement LOCALID_PLAYER, OreburghMineB2F_Movement_Arc1FaceWest
    WaitMovement
    PlayFanfare SEQ_SE_DP_WALL_HIT2
    ShakeCamera 12, 2
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    RemoveObject LOCALID_ARC1_RIFT
    FadeScreenIn FADE_SCREEN_SPEED_MEDIUM, COLOR_WHITE
    WaitFadeScreen
    WaitTime 15, VAR_RESULT
    ApplyMovement LOCALID_ARC1_COUNTERPART, OreburghMineB2F_Movement_Arc1ExclamationMark
    WaitMovement
    BufferCounterpartName 2
    Message OreburghMineB2F_Text_Arc1RuthRoute204
    WaitABXPadPress
    CloseMessage
    Message OreburghMineB2F_Text_Arc1RowanItsWaiting
    WaitABXPadPress
    CloseMessage
    // Roark has followed everyone down
    ClearFlag FLAG_UNK_0x018A
    SetObjectEventPos OREBURGH_MINE_B2F_ROARK_0, 15, 11
    SetObjectEventMovementType OREBURGH_MINE_B2F_ROARK_0, MOVEMENT_TYPE_LOOK_SOUTH
    SetObjectEventDir OREBURGH_MINE_B2F_ROARK_0, DIR_SOUTH
    AddObject OREBURGH_MINE_B2F_ROARK_0
    ApplyMovement OREBURGH_MINE_B2F_ROARK_0, OreburghMineB2F_Movement_Arc1RoarkArrive
    WaitMovement
    ApplyMovement LOCALID_PLAYER, OreburghMineB2F_Movement_Arc1FaceEast
    ApplyMovement LOCALID_ARC1_RIVAL, OreburghMineB2F_Movement_Arc1FaceEast
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, OreburghMineB2F_Movement_Arc1FaceSouth
    ApplyMovement LOCALID_ARC1_COUNTERPART, OreburghMineB2F_Movement_Arc1FaceSouth
    WaitMovement
    Message OreburghMineB2F_Text_Arc1RoarkCrying
    WaitABXPadPress
    CloseMessage
    Message OreburghMineB2F_Text_Arc1RoarkVouches
    WaitABXPadPress
    CloseMessage
    // Rowan's charge
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, OreburghMineB2F_Movement_Arc1FaceWest
    ApplyMovement LOCALID_ARC1_COUNTERPART, OreburghMineB2F_Movement_Arc1FaceWest
    WaitMovement
    Message OreburghMineB2F_Text_Arc1RowanOnePerson
    WaitABXPadPress
    CloseMessage
    BufferRivalName 0
    Message OreburghMineB2F_Text_Arc1GariusSpacesuitGuy
    WaitABXPadPress
    CloseMessage
    Message OreburghMineB2F_Text_Arc1RowanFindHim
    WaitABXPadPress
    CloseMessage
    // Fade out. END OF ARC 1.
    WaitTime 15, VAR_RESULT
    FadeScreenOut FADE_SCREEN_SPEED_SLOW
    WaitFadeScreen
    RemoveObject LOCALID_ARC1_RIVAL
    RemoveObject LOCALID_ARC1_PROF_ROWAN
    RemoveObject LOCALID_ARC1_COUNTERPART
    RemoveObject OREBURGH_MINE_B2F_ROARK_0
    ApplyMovement LOCALID_PLAYER, OreburghMineB2F_Movement_Arc1FaceWest
    WaitMovement
    SetVar VAR_ARC1_PROGRESS, 16
    WaitTime 30, VAR_RESULT
    FadeScreenIn FADE_SCREEN_SPEED_SLOW
    WaitFadeScreen
    Message OreburghMineB2F_Text_Arc1EndOfArc1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// The rubble over the north-west bay (objects 11-13), before the Coal Badge
OreburghMineB2F_Arc1SealedTunnel:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message OreburghMineB2F_Text_Arc1SealedTunnel
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
OreburghMineB2F_Movement_Arc1RowanArrive:
    WalkNormalSouth 5
    WalkNormalWest 2
    FaceWest
    EndMovement

    .balign 4, 0
OreburghMineB2F_Movement_Arc1RuthArrive:
    WalkNormalWest
    WalkNormalSouth 5
    WalkNormalWest
    FaceWest
    EndMovement

    .balign 4, 0
OreburghMineB2F_Movement_Arc1RoarkArrive:
    WalkNormalSouth 6
    WalkNormalWest 2
    FaceWest
    EndMovement

    .balign 4, 0
OreburghMineB2F_Movement_Arc1FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
OreburghMineB2F_Movement_Arc1FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
OreburghMineB2F_Movement_Arc1FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
OreburghMineB2F_Movement_Arc1FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
OreburghMineB2F_Movement_Arc1ExclamationMark:
    EmoteExclamationMark
    EndMovement
