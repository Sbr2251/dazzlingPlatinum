#include "macros/scrcmd.inc"
#include "res/text/bank/oreburgh_mine_b2f.h"
#include "res/field/maps/locals/oreburgh_mine_b2f.h"


#define FLAG_HUM_STARTED FLAG_UNK_0x0958 // talked to the miner in Oreburgh City
#define FLAG_HUM_CALMED  FLAG_UNK_0x0959 // his Machop calmed in the side tunnel

    ScriptEntry OreburghMineB2F_Roark
    ScriptEntry OreburghMineB2F_Machop1
    ScriptEntry OreburghMineB2F_Machop3
    ScriptEntry OreburghMineB2F_Machop2
    ScriptEntry OreburghMineB2F_Worker
    ScriptEntry OreburghMineB2F_OnTransition
    ScriptEntry OreburghMineB2F_Arc1OnFrameRift
    ScriptEntry OreburghMineB2F_Arc1SealedTunnel
    ScriptEntry OreburghMineB2F_HumCrates
    ScriptEntry OreburghMineB2F_HumBuzzFaint
    ScriptEntry OreburghMineB2F_HumBuzzLoud
    ScriptEntry OreburghMineB2F_HumBuzzCrack
    ScriptEntryEnd

OreburghMineB2F_Roark:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoTo OreburghMineB2F_RoarkTurnBackEast

OreburghMineB2F_Unused:
    ApplyMovement LOCALID_ROARK, OreburghMineB2F_Movement_Unused2
    WaitMovement
    GoTo OreburghMineB2F_RoarkUseRockSmash

OreburghMineB2F_RoarkTurnBackEast:
    ApplyMovement LOCALID_ROARK, OreburghMineB2F_Movement_RoarkTurnBackEast
    WaitMovement
    GoTo OreburghMineB2F_RoarkUseRockSmash

OreburghMineB2F_RoarkUseRockSmash:
    Message OreburghMineB2F_Text_StandBackAndWatch
    CloseMessage
    StartDestroyObstacleAnimation 2, VAR_0x8005
    WaitTime 10, VAR_RESULT
    RemoveObject LOCALID_ROCK_SMASH_1
OreburghMineB2F_WaitRockSmash:
    WaitTime 1, VAR_RESULT
    GoToIfEq VAR_0x8005, 0, OreburghMineB2F_WaitRockSmash
    FacePlayer
    Message OreburghMineB2F_Text_BouldersNeedToBeSmashed
    CloseMessage
    GoTo OreburghMineB2F_RoarkLeave

OreburghMineB2F_Unused2:
    ApplyMovement LOCALID_ROARK, OreburghMineB2F_Movement_Unused
    ApplyMovement LOCALID_PLAYER, OreburghMineB2F_Movement_Unused3
    WaitMovement
    GoTo OreburghMineB2F_RemoveRoark

OreburghMineB2F_RoarkLeave:
    ApplyMovement LOCALID_ROARK, OreburghMineB2F_Movement_RoarkLeave
    WaitMovement
    GoTo OreburghMineB2F_RemoveRoark

OreburghMineB2F_RemoveRoark:
    RemoveObject LOCALID_ROARK
    SetFlag FLAG_ROARK_RETURNED_TO_OREBURGH_GYM
    SetFlag FLAG_HIDE_OREBURGH_CITY_RIVAL
    ReleaseAll
    End

    .balign 4, 0
OreburghMineB2F_Movement_Unused:
    WalkNormalNorth
    WalkNormalEast 10
    EndMovement

    .balign 4, 0
OreburghMineB2F_Movement_RoarkLeave:
    WalkNormalEast 10
    EndMovement

OreburghMineB2F_Movement_Unused2:
    Delay8 2
    WalkOnSpotNormalNorth
    Delay8 4
    EndMovement

    .balign 4, 0
OreburghMineB2F_Movement_RoarkTurnBackEast:
    Delay8 2
    WalkOnSpotNormalEast
    Delay8 4
    EndMovement

OreburghMineB2F_Movement_Unused3:
    Delay8
    WalkOnSpotNormalNorth
    Delay8 2
    WalkOnSpotNormalEast
    EndMovement

OreburghMineB2F_Machop1:
    PokemonCryAndMessage SPECIES_MACHOP, OreburghMineB2F_Text_MachopCryMaaacho
    End

OreburghMineB2F_Machop3:
    PokemonCryAndMessage SPECIES_MACHOP, OreburghMineB2F_Text_MachopCryChopChop
    End

OreburghMineB2F_Machop2:
    PokemonCryAndMessage SPECIES_MACHOP, OreburghMineB2F_Text_MachopCryChopmacho
    End

OreburghMineB2F_Worker:
    NPCMessage OreburghMineB2F_Text_IMetMachopOnRoute207
    End

OreburghMineB2F_OnTransition:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    // Arc 1 r3 (hum): the Portal Reader buzz coords (VAR_MAP_LOCAL_0x00) are live while the Machop is missing
    SetVar VAR_MAP_LOCAL_0x00, 0
    CallIfSet FLAG_HUM_STARTED, OreburghMineB2F_HumArmBuzz
    SetFlag FLAG_HIDE_ARC1_MINE_SILHOUETTE
    GoToIfGe VAR_ARC1_PROGRESS, 16, OreburghMineB2F_Arc1SetStateDone
    GoToIfEq VAR_ARC1_PROGRESS, 15, OreburghMineB2F_Arc1SetStateRift
    ClearFlag FLAG_HIDE_ARC1_MINE_SEAL
    SetFlag FLAG_HIDE_ARC1_MINE_CAST
    SetFlag FLAG_HIDE_ARC1_MINE_RIFT
    End

OreburghMineB2F_Arc1SetStateRift:
    SetFlag FLAG_HIDE_OREBURGH_MINE_B2F_ROARK
    SetFlag FLAG_HIDE_ARC1_MINE_SEAL
    ClearFlag FLAG_HIDE_ARC1_MINE_CAST
    ClearFlag FLAG_HIDE_ARC1_MINE_RIFT
    End

OreburghMineB2F_Arc1SetStateDone:
    SetFlag FLAG_HIDE_OREBURGH_MINE_B2F_ROARK
    SetFlag FLAG_HIDE_ARC1_MINE_SEAL
    SetFlag FLAG_HIDE_ARC1_MINE_CAST
    SetFlag FLAG_HIDE_ARC1_MINE_RIFT
    End

// Frame script at VAR_ARC1_PROGRESS 15. The player arrives at (12,17) facing west; Garius is at (9,16) facing
// the rift at (9,15). Rowan (15,9) and Ruth (15,8) start off screen up the north shaft and come down it in single
// file to (13,16) and (14,16).
// Roark (local 0) follows later to (13,17), behind the player. Ends at 16 with Ruth's line toward Jubilife (fix2:
// the END OF ARC 1 card is gone); the player stays at (12,17) and walks out normally.
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
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC1_RIVAL, OreburghMineB2F_Movement_Arc1FaceNorth
    ApplyMovement LOCALID_PLAYER, OreburghMineB2F_Movement_Arc1FaceWest
    WaitMovement
    WaitTime 20, VAR_RESULT
    // Through the rift, a huge violet Hitmonlee rears up and roars. Then it's gone in a flash.
    // (Arc 1 r2: the 1-frame black "Giratina shadow" blip is cut; the Distortion World seam fly-by carries
    // that plant now.)
    ClearFlag FLAG_HIDE_ARC1_MINE_SILHOUETTE
    AddObject LOCALID_ARC1_SILHOUETTE
    PlayCry SPECIES_HITMONLEE
    ShakeCamera 16, 4
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
    WaitButton
    CloseMessage
    // Rowan explains totems
    ApplyMovement LOCALID_ARC1_RIVAL, OreburghMineB2F_Movement_Arc1FaceEast
    ApplyMovement LOCALID_PLAYER, OreburghMineB2F_Movement_Arc1FaceEast
    WaitMovement
    Message OreburghMineB2F_Text_Arc1RowanTheShard
    WaitButton
    CloseMessage
    Message OreburghMineB2F_Text_Arc1RowanTheMawile
    WaitButton
    CloseMessage
    Message OreburghMineB2F_Text_Arc1RowanATotem
    WaitButton
    CloseMessage
    BufferCounterpartName 2
    Message OreburghMineB2F_Text_Arc1RuthPullItOut
    WaitButton
    CloseMessage
    Message OreburghMineB2F_Text_Arc1RowanNotFromThisSide
    WaitButton
    CloseMessage
    BufferRivalName 0
    Message OreburghMineB2F_Text_Arc1GariusEasy
    WaitButton
    CloseMessage
    Message OreburghMineB2F_Text_Arc1RowanWithoutAGuide
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, OreburghMineB2F_Movement_Arc1FaceWest
    WaitMovement
    Message OreburghMineB2F_Text_Arc1RowanWhyThisRift
    WaitButton
    CloseMessage
    // The rift shudders and shrinks to nothing
    ApplyMovement LOCALID_ARC1_RIVAL, OreburghMineB2F_Movement_Arc1FaceNorth
    ApplyMovement LOCALID_PLAYER, OreburghMineB2F_Movement_Arc1FaceWest
    WaitMovement
    PlayFanfare SEQ_SE_DP_WALL_HIT2_sseq
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
    WaitButton
    CloseMessage
    Message OreburghMineB2F_Text_Arc1RowanItsWaiting
    WaitButton
    CloseMessage
    // Roark has followed everyone down
    ClearFlag FLAG_HIDE_OREBURGH_MINE_B2F_ROARK
    SetObjectEventPos LOCALID_ROARK, 15, 9
    SetObjectEventMovementType LOCALID_ROARK, MOVEMENT_TYPE_LOOK_SOUTH
    SetObjectEventDir LOCALID_ROARK, DIR_SOUTH
    AddObject LOCALID_ROARK
    ApplyMovement LOCALID_ROARK, OreburghMineB2F_Movement_Arc1RoarkArrive
    WaitMovement
    ApplyMovement LOCALID_PLAYER, OreburghMineB2F_Movement_Arc1FaceEast
    ApplyMovement LOCALID_ARC1_RIVAL, OreburghMineB2F_Movement_Arc1FaceEast
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, OreburghMineB2F_Movement_Arc1FaceSouth
    ApplyMovement LOCALID_ARC1_COUNTERPART, OreburghMineB2F_Movement_Arc1FaceSouth
    WaitMovement
    // fix2: Roark (13,17) turns to whoever he talks to or listens to: Rowan is right above him (13,16), the
    // player (12,17) and Garius (9,16) are to his west.
    ApplyMovement LOCALID_ROARK, OreburghMineB2F_Movement_Arc1FaceNorth
    WaitMovement
    Message OreburghMineB2F_Text_Arc1RoarkCrying
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ROARK, OreburghMineB2F_Movement_Arc1FaceWest
    WaitMovement
    Message OreburghMineB2F_Text_Arc1RoarkVouches
    WaitButton
    CloseMessage
    // Rowan's charge
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, OreburghMineB2F_Movement_Arc1FaceWest
    ApplyMovement LOCALID_ARC1_COUNTERPART, OreburghMineB2F_Movement_Arc1FaceWest
    ApplyMovement LOCALID_ROARK, OreburghMineB2F_Movement_Arc1FaceNorth
    WaitMovement
    Message OreburghMineB2F_Text_Arc1RowanOneMan
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ROARK, OreburghMineB2F_Movement_Arc1FaceWest
    WaitMovement
    BufferRivalName 0
    Message OreburghMineB2F_Text_Arc1GariusSpacesuitGuy
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ROARK, OreburghMineB2F_Movement_Arc1FaceNorth
    WaitMovement
    Message OreburghMineB2F_Text_Arc1RowanFindHim
    WaitButton
    CloseMessage
    // fix2: Arc 2 is in the game, so no END OF ARC 1 card. Ruth points the way (Arc 2's 2.1 starts on the walk
    // into Jubilife at VAR_ARC1_PROGRESS 16, VAR_ARC2_PROGRESS 0), the cast leaves, and the player has control.
    BufferCounterpartName 2
    Message OreburghMineB2F_Text_Arc1RuthJubilifeNext
    WaitButton
    CloseMessage
    WaitTime 15, VAR_RESULT
    FadeScreenOut FADE_SCREEN_SPEED_SLOW
    WaitFadeScreen
    RemoveObject LOCALID_ARC1_RIVAL
    RemoveObject LOCALID_ARC1_PROF_ROWAN
    RemoveObject LOCALID_ARC1_COUNTERPART
    RemoveObject LOCALID_ROARK
    ApplyMovement LOCALID_PLAYER, OreburghMineB2F_Movement_Arc1FaceWest
    WaitMovement
    SetVar VAR_ARC1_PROGRESS, 16
    WaitTime 30, VAR_RESULT
    FadeScreenIn FADE_SCREEN_SPEED_SLOW
    WaitFadeScreen
    ReleaseAll
    End

// The rubble over the north-west bay (objects 11-13), before the Coal Badge
OreburghMineB2F_Arc1SealedTunnel:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message OreburghMineB2F_Text_Arc1SealedTunnel
    WaitButton
    // Arc 1 r3 (hum): Ruth's reader (from the lab) is louder here than anywhere in town
    CheckItem ITEM_PORTAL_READER, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, OreburghMineB2F_Arc1SealedTunnelEnd
    PlaySE SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    GoTo SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    Message OreburghMineB2F_Text_HumSealReaderBuzz
    WaitButton
OreburghMineB2F_Arc1SealedTunnelEnd:
    CloseMessage
    ReleaseAll
    End

// Arc 1 r3 (hum), "The shard hums": the old crates in the north-west nook (object 19 at (2,17), drawn behind the
// map's crate model) hide a crack into
// the side tunnel (MAP_HEADER_OREBURGH_MINE_SIDE_TUNNEL). The way in is always open; the tunnel's exit lands on
// warp 1, (2,18). While the miner's Machop is missing, VAR_MAP_LOCAL_0x00 runs the reader's buzz coords:
// 1 armed, 2 faint (north shaft row 12), 3 loud (west of the sealed bay), 4 at the crates (row 18).
OreburghMineB2F_HumArmBuzz:
    CallIfUnset FLAG_HUM_CALMED, OreburghMineB2F_HumSetBuzz1
    Return

OreburghMineB2F_HumSetBuzz1:
    SetVar VAR_MAP_LOCAL_0x00, 1
    Return

OreburghMineB2F_HumCrates:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message OreburghMineB2F_Text_HumCrates
    GoToIfNe VAR_MAP_LOCAL_0x00, 0, OreburghMineB2F_HumCratesBuzz
OreburghMineB2F_HumCratesAsk:
    Message OreburghMineB2F_Text_HumSqueezeThrough
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, OreburghMineB2F_HumCratesNo
    BufferPlayerName 0
    Message OreburghMineB2F_Text_HumSqueezedPastCrates
    WaitButton
    CloseMessage
    PlayFanfare SEQ_SE_DP_KAIDAN2_sseq
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_OREBURGH_MINE_SIDE_TUNNEL, 59, 7, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

OreburghMineB2F_HumCratesBuzz:
    PlaySE SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    GoTo SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    Message OreburghMineB2F_Text_HumCratesBuzz
    GoTo OreburghMineB2F_HumCratesAsk

OreburghMineB2F_HumCratesNo:
    CloseMessage
    ReleaseAll
    End

OreburghMineB2F_HumBuzzFaint:
    LockAll
    SetVar VAR_MAP_LOCAL_0x00, 2
    PlaySE SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    Message OreburghMineB2F_Text_HumBuzzFaint
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghMineB2F_HumBuzzLoud:
    LockAll
    SetVar VAR_MAP_LOCAL_0x00, 3
    PlaySE SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    GoTo SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    Message OreburghMineB2F_Text_HumBuzzLoud
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghMineB2F_HumBuzzCrack:
    LockAll
    SetVar VAR_MAP_LOCAL_0x00, 4
    PlaySE SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    GoTo SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    GoTo SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    Message OreburghMineB2F_Text_HumBuzzCrack
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
OreburghMineB2F_Movement_Arc1RowanArrive:
    WalkNormalSouth 7
    WalkNormalWest 2
    FaceWest
    EndMovement

    .balign 4, 0
OreburghMineB2F_Movement_Arc1RuthArrive:
    WalkNormalSouth 8
    WalkNormalWest
    FaceWest
    EndMovement

    .balign 4, 0
OreburghMineB2F_Movement_Arc1RoarkArrive:
    WalkNormalSouth 8
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
