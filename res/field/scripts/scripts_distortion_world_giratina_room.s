#include "macros/scrcmd.inc"
#include "generated/hidden_locations.h"
#include "res/text/bank/distortion_world_giratina_room.h"


    ScriptEntry _0022
    ScriptEntry _0026
    ScriptEntry _0041
    ScriptEntry _009E
    ScriptEntry _00C4
    ScriptEntry _020A
    ScriptEntry _021D
    ScriptEntry _0232
    ScriptEntry DistortionWorldGiratinaRoom_Arc1Flashback
    ScriptEntryEnd

_0022:
    InitPersistedMapFeaturesForDistortionWorld
    End

_0026:
    GoToIfEq VAR_ARC1_PROGRESS, 0, DistortionWorldGiratinaRoom_Arc1HidePlayer
    GoToIfSet FLAG_MAP_LOCAL, _0033
    End

// Arc 1 flashback: the player is only a camera anchor; the hero is a Lucas NPC (local 133, from the overlay 9
// object table). He can't be spawned here (the Distortion World system isn't up yet on the first load and the
// game hangs), so the flashback script spawns him on its first frame.
DistortionWorldGiratinaRoom_Arc1HidePlayer:
    HideObject LOCALID_PLAYER
    End

_0033:
    ResetDistortionWorldPersistedCameraAngles
    SetVar VAR_DISTORTION_WORLD_PROGRESS, 14
    RemoveObject 128
    End

_0041:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message 13
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _0061
    CloseMessage
    ReleaseAll
    End

_0061:
    BufferPlayerName 0
    Message 14
    CloseMessage
    EnableHiddenLocation HIDDEN_LOCATION_SPRING_PATH
    SetVar VAR_EXITED_DISTORTION_WORLD_STATE, 1
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_SENDOFF_SPRING, 0, 32, 17, 1
    FadeScreenIn
    WaitFadeScreen
    End

_009E:
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_DISTORTION_WORLD_B7F, 0, 89, 57, 1
    FadeScreenIn
    WaitFadeScreen
    End

_00C4:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    PlayCry SPECIES_GIRATINA
    Message 2
    WaitCry
    CloseMessage
    SetFlag FLAG_MAP_LOCAL
    StartGiratinaOriginBattle SPECIES_GIRATINA, 47
    ClearFlag FLAG_MAP_LOCAL
    CheckWonBattle VAR_RESULT
    GetBattleResult VAR_RESULT
    GoToIfEq VAR_RESULT, BATTLE_RESULT_LOSE, _0204
    GoToIfEq VAR_RESULT, BATTLE_RESULT_DRAW, _0204
    GoToIfEq VAR_RESULT, BATTLE_RESULT_PLAYER_FLED, _014E
    GoToIfEq VAR_RESULT, BATTLE_RESULT_ENEMY_FLED, _014E
    GoToIfEq VAR_RESULT, BATTLE_RESULT_CAPTURED_MON, _016E
    ScrCmd_311 130
    ScrCmd_311 129
    ApplyMovement 129, _0250
    WaitMovement
    Message 3
    CloseMessage
    Message 4
    GoTo _0194

_014E:
    ScrCmd_311 130
    ScrCmd_311 129
    ApplyMovement 129, _0250
    WaitMovement
    Message 3
    CloseMessage
    Message 6
    GoTo _0194

_016E:
    SetFlag FLAG_CAUGHT_GIRATINA
    SetFlag FLAG_HIDE_TURNBACK_CAVE_GIRATINA_ROOM_GIRATINA
    ClearFlag FLAG_UNK_0x0278
    ScrCmd_311 130
    ScrCmd_311 129
    ApplyMovement 129, _0250
    WaitMovement
    Message 3
    CloseMessage
    Message 5
_0194:
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    AddFreeCamera VAR_0x8004, VAR_0x8005
    ApplyFreeCameraMovement _0280
    ApplyMovement 130, _026C
    ApplyMovement 129, _0258
    ApplyMovement LOCALID_PLAYER, _0244
    WaitMovement
    Message 7
    Message 8
    Message 9
    Message 10
    CloseMessage
    ApplyMovement 130, _0274
    WaitMovement
    ScrCmd_312 130
    ApplyFreeCameraMovement _0288
    WaitMovement
    RestoreCamera
    Message 11
    ApplyMovement 129, _0264
    WaitMovement
    Message 12
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0204:
    BlackOutFromBattle
    ReleaseAll
    End

_020A:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 12
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_021D:
    LockAll
    PlayCry SPECIES_GIRATINA
    Message 0
    WaitCry
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

_0232:
    LockAll
    BufferPlayerName 0
    Message 1
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

/* Arc 1 opening: a new game starts here (src/location.c). The last exchange between Cyrus and
 * Cynthia after GIRATINA. The hero is a Lucas NPC (local 133); the player is hidden and only anchors
 * the camera, because the player is a new character, not the old hero. As Cyrus leaves, GIRATINA (never
 * defeated or caught) swoops down and throws him through a rift. Runs from the init frame table while
 * VAR_ARC1_PROGRESS == 0, then hands off to the Lake Verity roof landing, where Cyrus falls out of the
 * portal. The waits are the original ones scaled by about 1/1.7 (the "1.7x" pacing note). */
DistortionWorldGiratinaRoom_Arc1Flashback:
    LockAll
    ScrCmd_311 133
    HideObject LOCALID_PLAYER
    WaitTime 18, VAR_RESULT
    ScrCmd_311 130
    ScrCmd_311 129
    ApplyMovement 129, _0250
    WaitMovement
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    AddFreeCamera VAR_0x8004, VAR_0x8005
    ApplyFreeCameraMovement _0280
    ApplyMovement 130, _026C
    ApplyMovement 129, _0258
    ApplyMovement 133, _0244
    WaitMovement
    Message 15
    Message 8
    Message 9
    Message 10
    CloseMessage
    ApplyMovement 130, DistortionWorldGiratinaRoom_Arc1CyrusLeave
    ApplyFreeCameraMovement DistortionWorldGiratinaRoom_Arc1CameraFollowCyrus
    WaitMovement
    WaitTime 18, VAR_RESULT
    /* GIRATINA's shadow (the stock 1F fly-by model) sweeps over Cyrus, then swoops back, strikes him and
     * throws him through a rift. */
    ScrCmd_321 1
    WaitTime 7, VAR_RESULT
    ApplyMovement 130, DistortionWorldGiratinaRoom_Arc1CyrusNotice
    WaitMovement
    WaitTime 12, VAR_RESULT
    ScrCmd_322
    Message 17
    CloseMessage
    ScrCmd_321 2
    WaitTime 2, VAR_RESULT
    PlayFanfare SEQ_SE_DP_WALL_HIT2
    ApplyMovement 130, DistortionWorldGiratinaRoom_Arc1CyrusKnockedBack
    ShakeCamera 16, 4
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    ScrCmd_312 130
    WaitTime 6, VAR_RESULT
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitTime 12, VAR_RESULT
    ScrCmd_322
    WaitTime 18, VAR_RESULT
    ApplyFreeCameraMovement DistortionWorldGiratinaRoom_Arc1CameraBack
    WaitMovement
    RestoreCamera
    ApplyMovement 129, _0258
    WaitMovement
    Message 18
    CloseMessage
    WaitTime 18, VAR_RESULT
    FadeScreenOut
    WaitFadeScreen
    SetVar VAR_ARC1_PROGRESS, 1
    Warp MAP_HEADER_LAKE_VERITY, 0, 32, 31, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
_0244:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_0250:
    MoveAction_117 2
    EndMovement

    .balign 4, 0
_0258:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_0264:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_026C:
    MoveAction_117
    EndMovement

    .balign 4, 0
_0274:
    MoveAction_118
    WalkNormalSouth 5
    EndMovement

    .balign 4, 0
_0280:
    WalkNormalSouth 5
    EndMovement

    .balign 4, 0
_0288:
    WalkNormalNorth 5
    EndMovement

    .balign 4, 0
DistortionWorldGiratinaRoom_Arc1CyrusLeave:
    MoveAction_118
    EndMovement

    .balign 4, 0
DistortionWorldGiratinaRoom_Arc1CyrusNotice:
    WalkOnSpotNormalEast
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
DistortionWorldGiratinaRoom_Arc1CameraFollowCyrus:
    WalkFastSouth 3
    EndMovement

    .balign 4, 0
DistortionWorldGiratinaRoom_Arc1CyrusKnockedBack:
    LockDir
    JumpNearFastWest
    UnlockDir
    EndMovement

    .balign 4, 0
DistortionWorldGiratinaRoom_Arc1CameraBack:
    WalkFastNorth 8
    EndMovement
