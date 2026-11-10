#include "macros/scrcmd.inc"
#include "generated/hidden_locations.h"
#include "res/text/bank/distortion_world_giratina_room.h"

    ScriptEntry DistortionWorldGiratinaRoom_OnTransition
    ScriptEntry DistortionWorldGiratinaRoom_OnLoad
    ScriptEntry DistortionWorldGiratinaRoom_Portal
    ScriptEntry DistortionWorldGiratinaRoom_CoordEvent_WarpToB7F
    ScriptEntry DistortionWorldGiratinaRoom_Giratina
    ScriptEntry DistortionWorldGiratinaRoom_Cynthia
    ScriptEntry DistortionWorldGiratinaRoom_CoordEvent_FirstShadow
    ScriptEntry DistortionWorldGiratinaRoom_CoordEvent_GiratinaArrival
    ScriptEntry DistortionWorldGiratinaRoom_Arc1Flashback
    ScriptEntryEnd

DistortionWorldGiratinaRoom_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

DistortionWorldGiratinaRoom_OnLoad:
    GoToIfEq VAR_ARC1_PROGRESS, 0, DistortionWorldGiratinaRoom_Arc1HidePlayer
    GoToIfSet FLAG_MAP_LOCAL_REMOVE_OBJECT, DistortionWorldGiratinaRoom_RemoveGiratina
    End

// Arc 1 flashback: the player is only a camera anchor; the hero is a Lucas NPC (local 133, from the overlay 9
// object table). He can't be spawned here (the Distortion World system isn't up yet on the first load and the
// game hangs), so the flashback script spawns him on its first frame.

DistortionWorldGiratinaRoom_RemoveGiratina:
    ResetDistortionWorldPersistedCameraAngles
    SetVar VAR_DISTORTION_WORLD_PROGRESS, DIST_WORLD_PROGRESS_BATTLED_GIRATINA
    RemoveObject DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_GIRATINA
    End

DistortionWorldGiratinaRoom_Portal:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message DistortionWorldGiratinaRoom_Text_LeapIntoPortal
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, DistortionWorldGiratinaRoom_GoToSendoffSpring
    CloseMessage
    ReleaseAll
    End

DistortionWorldGiratinaRoom_GoToSendoffSpring:
    BufferPlayerName 0
    Message DistortionWorldGiratinaRoom_Text_PlayerLeaptIntoPortal
    CloseMessage
    EnableHiddenLocation HIDDEN_LOCATION_SPRING_PATH
    SetVar VAR_EXITED_DISTORTION_WORLD_STATE, 1
    PlaySE SEQ_SE_PL_SYUWA_sseq
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_SENDOFF_SPRING, 32, 17, DIR_SOUTH
    FadeScreenIn
    WaitFadeScreen
    End

DistortionWorldGiratinaRoom_CoordEvent_WarpToB7F:
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_DISTORTION_WORLD_B7F, 89, 57, DIR_SOUTH
    FadeScreenIn
    WaitFadeScreen
    End

DistortionWorldGiratinaRoom_Giratina:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    PlayCry SPECIES_GIRATINA
    Message DistortionWorldGiratinaRoom_Text_GiratinaCryGiygogagohgwooh
    WaitCry
    CloseMessage
    SetFlag FLAG_MAP_LOCAL_REMOVE_OBJECT
    StartGiratinaOriginBattle SPECIES_GIRATINA, 47
    ClearFlag FLAG_MAP_LOCAL_REMOVE_OBJECT
    CheckWonBattle VAR_RESULT
    GetBattleResult VAR_RESULT
    GoToIfEq VAR_RESULT, BATTLE_RESULT_LOSE, DistortionWorldGiratinaRoom_BlackOut
    GoToIfEq VAR_RESULT, BATTLE_RESULT_DRAW, DistortionWorldGiratinaRoom_BlackOut
    GoToIfEq VAR_RESULT, BATTLE_RESULT_PLAYER_FLED, DistortionWorldGiratinaRoom_PlayerRan
    GoToIfEq VAR_RESULT, BATTLE_RESULT_ENEMY_FLED, DistortionWorldGiratinaRoom_PlayerRan
    GoToIfEq VAR_RESULT, BATTLE_RESULT_CAPTURED_MON, DistortionWorldGiratinaRoom_CaughtGiratina
    AddDistortionWorldMapObject DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYRUS
    AddDistortionWorldMapObject DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYNTHIA
    ApplyMovement DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYNTHIA, DistortionWorldGiratinaRoom_Movement_CynthiaJumpNorth
    WaitMovement
    Message DistortionWorldGiratinaRoom_Text_GiratinaUnderstoodUs
    CloseMessage
    Message DistortionWorldGiratinaRoom_Text_ThatPokemonWasDefeated
    GoTo DistortionWorldGiratinaRoom_PostBattle

DistortionWorldGiratinaRoom_PlayerRan:
    AddDistortionWorldMapObject DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYRUS
    AddDistortionWorldMapObject DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYNTHIA
    ApplyMovement DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYNTHIA, DistortionWorldGiratinaRoom_Movement_CynthiaJumpNorth
    WaitMovement
    Message DistortionWorldGiratinaRoom_Text_GiratinaUnderstoodUs
    CloseMessage
    Message DistortionWorldGiratinaRoom_Text_YouRefusedToBattle
    GoTo DistortionWorldGiratinaRoom_PostBattle

DistortionWorldGiratinaRoom_CaughtGiratina:
    SetFlag FLAG_CAUGHT_GIRATINA
    SetFlag FLAG_HIDE_TURNBACK_CAVE_GIRATINA_ROOM_GIRATINA
    ClearFlag FLAG_HIDE_TURNBACK_CAVE_GIRATINA_ROOM_ITEM
    AddDistortionWorldMapObject DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYRUS
    AddDistortionWorldMapObject DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYNTHIA
    ApplyMovement DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYNTHIA, DistortionWorldGiratinaRoom_Movement_CynthiaJumpNorth
    WaitMovement
    Message DistortionWorldGiratinaRoom_Text_GiratinaUnderstoodUs
    CloseMessage
    Message DistortionWorldGiratinaRoom_Text_ThatPokemonWasCaptured
DistortionWorldGiratinaRoom_PostBattle:
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    AddFreeCamera VAR_0x8004, VAR_0x8005
    ApplyFreeCameraMovement DistortionWorldGiratinaRoom_Movement_CameraMoveSouth
    ApplyMovement DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYRUS, DistortionWorldGiratinaRoom_Movement_CyrusEnter
    ApplyMovement DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYNTHIA, DistortionWorldGiratinaRoom_Movement_CynthiaNoticeCyrus
    ApplyMovement LOCALID_PLAYER, DistortionWorldGiratinaRoom_Movement_PlayerNoticeCyrus
    WaitMovement
    Message DistortionWorldGiratinaRoom_Text_NewWorldCantBeMade
    Message DistortionWorldGiratinaRoom_Text_PokemonUniteUs
    Message DistortionWorldGiratinaRoom_Text_BigSilence
    Message DistortionWorldGiratinaRoom_Text_EnoughBlathering
    CloseMessage
    ApplyMovement DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYRUS, DistortionWorldGiratinaRoom_Movement_CyrusLeave
    WaitMovement
    DeleteDistortionWorldMapObject DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYRUS
    ApplyFreeCameraMovement DistortionWorldGiratinaRoom_Movement_CameraMoveNorth
    WaitMovement
    RestoreCamera
    Message DistortionWorldGiratinaRoom_Text_WeCanFeelJoy
    ApplyMovement DIST_WORLD_MAP_OBJECT_GIRATINA_ROOM_CYNTHIA, DistortionWorldGiratinaRoom_Movement_CynthiaWalkOnSpotNorth
    WaitMovement
    Message DistortionWorldGiratinaRoom_Text_LetsGoBackHome
    WaitButton
    CloseMessage
    ReleaseAll
    End

DistortionWorldGiratinaRoom_BlackOut:
    BlackOutFromBattle
    ReleaseAll
    End

DistortionWorldGiratinaRoom_Cynthia:
    NPCMessage DistortionWorldGiratinaRoom_Text_LetsGoBackHome
    End

DistortionWorldGiratinaRoom_CoordEvent_FirstShadow:
    LockAll
    PlayCry SPECIES_GIRATINA
    Message DistortionWorldGiratinaRoom_Text_GiratinaCryGiygogagogwoh
    WaitCry
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

DistortionWorldGiratinaRoom_CoordEvent_GiratinaArrival:
    LockAll
    BufferPlayerName 0
    Message DistortionWorldGiratinaRoom_Text_GiratinaIsEyeingPlayer
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
DistortionWorldGiratinaRoom_Movement_PlayerNoticeCyrus:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
DistortionWorldGiratinaRoom_Movement_CynthiaJumpNorth:
    JumpDistortionWorldNorth 2
    EndMovement

    .balign 4, 0
DistortionWorldGiratinaRoom_Movement_CynthiaNoticeCyrus:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
DistortionWorldGiratinaRoom_Movement_CynthiaWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
DistortionWorldGiratinaRoom_Movement_CyrusEnter:
    JumpDistortionWorldNorth
    EndMovement

    .balign 4, 0
DistortionWorldGiratinaRoom_Movement_CyrusLeave:
    JumpDistortionWorldSouth
    WalkNormalSouth 5
    EndMovement

    .balign 4, 0
DistortionWorldGiratinaRoom_Movement_CameraMoveSouth:
    WalkNormalSouth 5
    EndMovement

    .balign 4, 0
DistortionWorldGiratinaRoom_Movement_CameraMoveNorth:
    WalkNormalNorth 5
    EndMovement

DistortionWorldGiratinaRoom_Arc1HidePlayer:
    HideObject LOCALID_PLAYER
    End

DistortionWorldGiratinaRoom_Arc1Flashback:
    LockAll
    AddDistortionWorldMapObject 133
    HideObject LOCALID_PLAYER
    WaitTime 18, VAR_RESULT
    AddDistortionWorldMapObject 130
    AddDistortionWorldMapObject 129
    ApplyMovement 129, DistortionWorldGiratinaRoom_Movement_CynthiaJumpNorth
    WaitMovement
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    AddFreeCamera VAR_0x8004, VAR_0x8005
    ApplyFreeCameraMovement DistortionWorldGiratinaRoom_Movement_CameraMoveSouth
    ApplyMovement 130, DistortionWorldGiratinaRoom_Movement_CyrusEnter
    ApplyMovement 129, DistortionWorldGiratinaRoom_Movement_CynthiaNoticeCyrus
    ApplyMovement 133, DistortionWorldGiratinaRoom_Movement_PlayerNoticeCyrus
    WaitMovement
    Message DistortionWorldGiratinaRoom_Text_CyrusWorldWillRemain
    Message DistortionWorldGiratinaRoom_Text_PokemonUniteUs
    Message DistortionWorldGiratinaRoom_Text_BigSilence
    Message DistortionWorldGiratinaRoom_Text_EnoughBlathering
    CloseMessage
    ApplyMovement 130, DistortionWorldGiratinaRoom_Arc1CyrusLeave
    ApplyFreeCameraMovement DistortionWorldGiratinaRoom_Arc1CameraFollowCyrus
    WaitMovement
    WaitTime 18, VAR_RESULT
    /* GIRATINA's shadow (the stock 1F fly-by model) sweeps over Cyrus, then swoops back, strikes him and
     * throws him through a rift. */
    StartDistortionWorldGiratinaShadowEvent 1
    WaitTime 7, VAR_RESULT
    ApplyMovement 130, DistortionWorldGiratinaRoom_Arc1CyrusNotice
    WaitMovement
    WaitTime 12, VAR_RESULT
    FinishDistortionWorldGiratinaShadowEvent
    Message DistortionWorldGiratinaRoom_Text_CyrusGiratinaNotDefeated
    CloseMessage
    StartDistortionWorldGiratinaShadowEvent 2
    WaitTime 2, VAR_RESULT
    PlayFanfare SEQ_SE_DP_WALL_HIT2_sseq
    ApplyMovement 130, DistortionWorldGiratinaRoom_Arc1CyrusKnockedBack
    ShakeCamera 16, 4
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA_sseq
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    DeleteDistortionWorldMapObject 130
    WaitTime 6, VAR_RESULT
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitTime 12, VAR_RESULT
    FinishDistortionWorldGiratinaShadowEvent
    WaitTime 18, VAR_RESULT
    ApplyFreeCameraMovement DistortionWorldGiratinaRoom_Arc1CameraBack
    WaitMovement
    RestoreCamera
    ApplyMovement 129, DistortionWorldGiratinaRoom_Movement_CynthiaNoticeCyrus
    WaitMovement
    Message DistortionWorldGiratinaRoom_Text_CynthiaThrewHimThroughRift
    CloseMessage
    WaitTime 18, VAR_RESULT
    FadeScreenOut
    WaitFadeScreen
    SetVar VAR_ARC1_PROGRESS, 1
    Warp MAP_HEADER_LAKE_VERITY, 32, 31, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
DistortionWorldGiratinaRoom_Arc1CyrusLeave:
    JumpDistortionWorldSouth
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
