#include "macros/scrcmd.inc"
#include "res/text/bank/lake_verity.h"
#include "res/field/events/events_lake_verity.h"


    ScriptEntry LakeVerity_OnTransition
    ScriptEntry LakeVerity_OnLoad
    ScriptEntry LakeVerity_ProfRowan
    ScriptEntry LakeVerity_Counterpart
    ScriptEntry LakeVerity_OnFrameProfRowanNoticePlayer
    ScriptEntry LakeVerity_Mars
    ScriptEntry LakeVerity_GruntM
    ScriptEntry LakeVerity_Launchpad
    ScriptEntry LakeVerity_DrawbridgeSign
    ScriptEntry LakeVerity_Arc1OnFrameRoofLanding
    ScriptEntry LakeVerity_EarlyProfRowan
    ScriptEntry LakeVerity_EarlyCounterpart
    ScriptEntry LakeVerity_Arc1OnFrameArrival
    ScriptEntry LakeVerity_OnResume
    ScriptEntryEnd

// This map is used for every visit (the stock early-story map MAP_HEADER_LAKE_VERITY_LOW_WATER is no longer
// reachable). Until Saturn is defeated in Valor Cavern the stock game used LOW_WATER here, so the Team Galactic
// scene is hidden and the early scene (Rowan and the counterpart after Canalave) is shown.
// The Arc 1 scenes (VAR_ARC1_PROGRESS 1 and 3) use their own objects, gated by two stock hide flags whose
// LOW_WATER objects are unreachable: FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL hides Barry, who is on the map
// from the start of the arrival scene, and FLAG_HIDE_LAKE_VERITY_LOW_WATER_CYRUS hides the objects the scenes
// add with AddObject (Cyrus, Rowan, the counterpart, the two Mawile and the briefcase). Both are set on every
// entry and Barry's flag is cleared only for the arrival scene.
LakeVerity_OnTransition:
    CallIfUnset FLAG_DEFEATED_COMMANDER_SATURN_VALOR_CAVERN, LakeVerity_SetEarlyState
    CallIfSet FLAG_DEFEATED_COMMANDER_SATURN_VALOR_CAVERN, LakeVerity_SetTeamGalacticState
    CallIfSet FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY, LakeVerity_SetPositionsAfterTeamGalactic
    CallIfUnset FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY, LakeVerity_SetPositionsDuringTeamGalactic
    CallIfEq VAR_LAKE_VERITY_PROF_ROWAN_STATE, 0, LakeVerity_SetProfRowanStartPosition
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_CYRUS
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL
    CallIfEq VAR_ARC1_PROGRESS, 3, LakeVerity_Arc1ShowArrivalCast
    GetPlayerGender VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, GENDER_MALE, LakeVerity_SetCounterpartGraphicsDawn
    GoToIfEq VAR_MAP_LOCAL_0, GENDER_FEMALE, LakeVerity_SetCounterpartGraphicsLucas
    End

LakeVerity_SetCounterpartGraphicsDawn:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_PLAYER_F
    End

LakeVerity_SetCounterpartGraphicsLucas:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_PLAYER_M
    End

LakeVerity_SetEarlyState:
    SetFlag FLAG_HIDE_LAKE_VERITY_TEAM_GALACTIC
    SetFlag FLAG_HIDE_LAKE_VERITY_PROF_ROWAN
    SetFlag FLAG_HIDE_LAKE_VERITY_COUNTERPART
    Return

LakeVerity_SetTeamGalacticState:
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_PROF_ROWAN
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_COUNTERPART
    CallIfUnset FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY, LakeVerity_ShowTeamGalactic
    CallIfEq VAR_LAKE_VERITY_PROF_ROWAN_STATE, 0, LakeVerity_ArmProfRowanNoticePlayer
    Return

LakeVerity_ShowTeamGalactic:
    ClearFlag FLAG_HIDE_LAKE_VERITY_TEAM_GALACTIC
    ClearFlag FLAG_HIDE_LAKE_VERITY_PROF_ROWAN
    ClearFlag FLAG_HIDE_LAKE_VERITY_COUNTERPART
    Return

LakeVerity_Arc1ShowArrivalCast:
    ClearFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL
    Return

// VAR_MAP_LOCAL_1 gates the frame script, so Rowan only notices the player on the Team Galactic visit
LakeVerity_ArmProfRowanNoticePlayer:
    SetVar VAR_MAP_LOCAL_1, 1
    Return

LakeVerity_SetProfRowanStartPosition:
    SetObjectEventPos LOCALID_PROF_ROWAN, 46, 50
    SetObjectEventMovementType LOCALID_PROF_ROWAN, MOVEMENT_TYPE_LOOK_NORTH
    SetObjectEventDir LOCALID_PROF_ROWAN, DIR_NORTH
    Return

LakeVerity_SetPositionsDuringTeamGalactic:
    SetObjectEventPos LOCALID_PROF_ROWAN, 46, 51
    SetObjectEventMovementType LOCALID_PROF_ROWAN, MOVEMENT_TYPE_LOOK_SOUTH
    SetObjectEventDir LOCALID_PROF_ROWAN, DIR_SOUTH
    Return

LakeVerity_SetPositionsAfterTeamGalactic:
    SetObjectEventPos LOCALID_PROF_ROWAN, 51, 37
    SetObjectEventMovementType LOCALID_PROF_ROWAN, MOVEMENT_TYPE_LOOK_WEST
    SetObjectEventDir LOCALID_PROF_ROWAN, DIR_WEST
    SetObjectEventPos LOCALID_COUNTERPART, 50, 39
    SetObjectEventMovementType LOCALID_COUNTERPART, MOVEMENT_TYPE_LOOK_WEST
    SetObjectEventDir LOCALID_COUNTERPART, DIR_WEST
    Return

LakeVerity_OnLoad:
    End

LakeVerity_Unused:
    End

LakeVerity_ProfRowan:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfSet FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY, LakeVerity_INeedYouToGoToLakeAcuity
    ApplyMovement LOCALID_PROF_ROWAN, LakeVerity_Movement_RowanWalkOnSpotEast
    WaitMovement
    Message LakeVerity_Text_HowDareYouMisguidedThugs
    FacePlayer
    GetPlayerGender VAR_RESULT
    GoToIfEq VAR_RESULT, GENDER_MALE, LakeVerity_DawnNeedsYourHelp
    GoTo LakeVerity_LucasNeedsYourHelp
    End

LakeVerity_DawnNeedsYourHelp:
    BufferPlayerName 0
    Message LakeVerity_Text_DawnNeedsYourHelp
    GoTo LakeVerity_CloseMessageCounterpartNeedsYourHelp
    End

LakeVerity_LucasNeedsYourHelp:
    BufferPlayerName 0
    Message LakeVerity_Text_LucasNeedsYourHelp
    GoTo LakeVerity_CloseMessageCounterpartNeedsYourHelp
    End

LakeVerity_CloseMessageCounterpartNeedsYourHelp:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

LakeVerity_INeedYouToGoToLakeAcuity:
    FacePlayer
    BufferPlayerName 0
    BufferRivalName 1
    Message LakeVerity_Text_INeedYouToGoToLakeAcuity
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

LakeVerity_Counterpart:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY, LakeVerity_CounterpartWhatsTeamGalacticUpTo
    GetPlayerGender VAR_RESULT
    GoToIfEq VAR_RESULT, GENDER_MALE, LakeVerity_DawnICouldntBeatThisPerson
    GoTo LakeVerity_LucasILostToHerButJustBarely
    End

LakeVerity_DawnICouldntBeatThisPerson:
    BufferPlayerName 0
    Message LakeVerity_Text_DawnICouldntBeatThisPerson
    GoTo LakeVerity_CloseMessageCounterpartLostToMars
    End

LakeVerity_LucasILostToHerButJustBarely:
    BufferPlayerName 0
    Message LakeVerity_Text_LucasILostToHerButJustBarely
    GoTo LakeVerity_CloseMessageCounterpartLostToMars
    End

LakeVerity_CloseMessageCounterpartLostToMars:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

LakeVerity_CounterpartWhatsTeamGalacticUpTo:
    GetPlayerGender VAR_RESULT
    GoToIfEq VAR_RESULT, GENDER_MALE, LakeVerity_DawnWhatIsTeamGalacticUpTo
    GoTo LakeVerity_LucasWhatsTeamGalacticUpTo
    End

LakeVerity_DawnWhatIsTeamGalacticUpTo:
    BufferPlayerName 0
    Message LakeVerity_Text_DawnWhatIsTeamGalacticUpTo
    GoTo LakeVerity_CloseMessageWhatsTeamGalacticUpTo
    End

LakeVerity_LucasWhatsTeamGalacticUpTo:
    BufferPlayerName 0
    Message LakeVerity_Text_LucasWhatsTeamGalacticUpTo
    GoTo LakeVerity_CloseMessageWhatsTeamGalacticUpTo
    End

LakeVerity_CloseMessageWhatsTeamGalacticUpTo:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
LakeVerity_Movement_RowanWalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

LakeVerity_OnFrameProfRowanNoticePlayer:
    LockAll
    ApplyMovement LOCALID_PROF_ROWAN, LakeVerity_Movement_RowanNoticePlayer
    WaitMovement
    GetPlayerGender VAR_RESULT
    GoToIfEq VAR_RESULT, GENDER_MALE, LakeVerity_WhatTimingYouveGotToHelpDawn
    GoTo LakeVerity_WhatTimingYouveGotToHelpLucas
    End

LakeVerity_WhatTimingYouveGotToHelpDawn:
    BufferPlayerName 0
    Message LakeVerity_Text_WhatTimingYouveGotToHelpDawn
    GoTo LakeVerity_CloseMessageYouveGotToHelpCounterpart
    End

LakeVerity_WhatTimingYouveGotToHelpLucas:
    BufferPlayerName 0
    Message LakeVerity_Text_WhatTimingYouveGotToHelpLucas
    GoTo LakeVerity_CloseMessageYouveGotToHelpCounterpart
    End

LakeVerity_CloseMessageYouveGotToHelpCounterpart:
    SetVar VAR_LAKE_VERITY_PROF_ROWAN_STATE, 1
    SetVar VAR_MAP_LOCAL_1, 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
LakeVerity_Movement_RowanNoticePlayer:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    WalkNormalSouth
    EndMovement

LakeVerity_Mars:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    ApplyMovement LOCALID_COUNTERPART, LakeVerity_Movement_CounterpartWalkOnSpotEast
    WaitMovement
    Message LakeVerity_Text_MarsIntro
    CloseMessage
    StartTrainerBattle TRAINER_COMMANDER_MARS_LAKE_VERITY
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, LakeVerity_BlackOut
    Message LakeVerity_Text_MarsDefeat
    Message LakeVerity_Text_WerePullingOut
    Message LakeVerity_Text_NowWeveGotAllLakePokemon
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_MARS
    RemoveObject LOCALID_GRUNT_M
    RemoveObject LOCALID_GALACTIC_GRUNT_1
    RemoveObject LOCALID_GALACTIC_GRUNT_3
    RemoveObject LOCALID_GALACTIC_GRUNT_2
    RemoveObject LOCALID_GALACTIC_GRUNT_4
    SetFlag FLAG_ALT_MUSIC_LAKE_VERITY
    ApplyMovement LOCALID_COUNTERPART, LakeVerity_Movement_CounterpartFaceSouth
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_PlayerFaceWest
    WaitMovement
    SetPosition LOCALID_PROF_ROWAN, 53, 1, 39, DIR_EAST
    FadeScreenIn
    WaitFadeScreen
    SetFlag FLAG_UNK_0x029A
    SetFlag FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY
    ClearFlag FLAG_HIDE_LAKE_ACUITY_JUPITER
    SetVar VAR_LAKE_ACUITY_STATE, 1
    BufferRivalName 0
    Message LakeVerity_Text_WhatIsHappeningAtLakeAcuity
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

LakeVerity_BlackOut:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
LakeVerity_UnusedMovement:
    WalkOnSpotNormalNorth
    EndMovement

LakeVerity_UnusedMovement2:
    WalkNormalNorth 3
    EndMovement

    .balign 4, 0
LakeVerity_Movement_CounterpartWalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
LakeVerity_Movement_CounterpartFaceSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_PlayerFaceWest:
    WalkOnSpotNormalWest
    EndMovement

LakeVerity_GruntM:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message LakeVerity_Text_OuchWhatsWithThisOldTimer
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0

// bg events on the 18 edge tiles of the stock Distortion World portal (map prop 581), centred on LAUNCHPAD (32,27)
// in the middle of the castle's open roof terrace (h4). While the portal is open its footprint is blocked, so the
// player faces it from a neighbouring tile; see PORTAL_TILES / PORTAL_EDGE in tools/lake_verity/layout.py
// Inert while the portal is hidden (it closes during the Arc 1 arrival scene); the footprint is walkable then.
LakeVerity_Launchpad:
    GoToIfSet FLAG_LAKE_VERITY_PORTAL_HIDDEN, LakeVerity_LaunchpadHidden
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfSet FLAG_LAKE_VERITY_PORTAL_OPEN, LakeVerity_LaunchpadPortalOpen
    Message LakeVerity_Text_LaunchpadDormant
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

LakeVerity_LaunchpadPortalOpen:
    Message LakeVerity_Text_LaunchpadPortalOpen
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, LakeVerity_LaunchpadStayBehind
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    SetPartyGiratinaForm GIRATINA_FORM_ORIGIN
    Warp MAP_HEADER_DISTORTION_WORLD_1F, 0, 55, 40, 1
    FadeScreenIn
    WaitFadeScreen
    End

LakeVerity_LaunchpadStayBehind:
    CloseMessage
    ReleaseAll
    End

LakeVerity_LaunchpadHidden:
    End

LakeVerity_DrawbridgeSign:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message LakeVerity_Text_DrawbridgeSign
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// Dazzling Platinum Arc 1 (docs/arc1/screenplay.md, scenes 2 and 6).
//
// VAR_ARC1_PROGRESS 1: the player arrives from the Distortion World flashback at (32,31), hidden (see
// LakeVerity_OnResume), and watches Cyrus land beside the portal. Hands off to the bedroom (state 2).
//
// VAR_ARC1_PROGRESS 3: the player arrives from the Verity Lakefront with Barry (the scene spawns its own Barry).
// The camera pans to the castle terrace, where Rowan and the counterpart find Cyrus, two Mawile come out of the
// portal, the portal closes and the chase starts. Barry and the player come up the stairs, pick starters from
// Rowan's briefcase and fight the Mawile, then Cyrus and Barry leave. Ends in state 4 (free roam).
//
// Terrace (h4) walkable tiles and the portal footprint are in tools/lake_verity/layout.py. The chase runs round
// the ring x28/x36, z23/z30 (30 tiles). The chasers form a snake heading west on z30 at x29..33 (index k 0..4),
// and one lap for index k is West 1+k, North 7, East 8, South 7, West 7-k.
LakeVerity_Arc1OnFrameRoofLanding:
    LockAll
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_PROF_ROWAN
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_COUNTERPART
    WaitTime 30, VAR_RESULT
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitTime 10, VAR_RESULT
    PlayFanfare SEQ_SE_DP_WALL_HIT2
    ShakeCamera 24, 4
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    ClearFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_CYRUS
    AddObject LOCALID_CYRUS
    FadeScreenIn FADE_SCREEN_SPEED_SLOW, COLOR_WHITE
    WaitFadeScreen
    WaitTime 45, VAR_RESULT
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1CyrusLookAround
    WaitMovement
    Message LakeVerity_Text_Arc1CyrusWhereAmI
    Message LakeVerity_Text_Arc1CyrusTheFall
    Message LakeVerity_Text_Arc1CyrusWasIWrong
    WaitABXPadPress
    CloseMessage
    WaitTime 30, VAR_RESULT
    FadeScreenOut FADE_SCREEN_SPEED_SLOW
    WaitFadeScreen
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_CYRUS
    SetVar VAR_ARC1_PROGRESS, 2
    Warp MAP_HEADER_TWINLEAF_TOWN_PLAYER_HOUSE_2F, 0, 4, 6, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

// Runs on every field (re)load. The player is only a camera anchor for the roof landing.
LakeVerity_OnResume:
    GoToIfEq VAR_ARC1_PROGRESS, 1, LakeVerity_Arc1HidePlayer
    End

LakeVerity_Arc1HidePlayer:
    HideObject LOCALID_PLAYER
    End

LakeVerity_Arc1OnFrameArrival:
    LockAll
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_PROF_ROWAN
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_COUNTERPART
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceSouth
    WaitMovement
    BufferRivalName 0
    Message LakeVerity_Text_Arc1BarryWhatsOnTheCastle
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceNorth
    WaitMovement
    // Pan from the entrance to the terrace (32,28), then move Barry and the player to the foot of the stairs
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    AddFreeCamera VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 47, LakeVerity_Arc1CameraStepWest
    ApplyFreeCameraMovement LakeVerity_Movement_Arc1CameraPanNorth
    WaitMovement
    // The entrance is off screen now
    SetPosition LOCALID_RIVAL, 23, 0, 37, DIR_NORTH
    SetPosition LOCALID_PLAYER, 24, 0, 37, DIR_NORTH
    ApplyFreeCameraMovement LakeVerity_Movement_Arc1CameraPanToTerrace
    WaitMovement
    // The terrace cast is added only now: objects created on the terrace while the field was
    // loaded around the entrance aren't drawn until they first move.
    ClearFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_CYRUS
    AddObject LOCALID_CYRUS
    AddObject LOCALID_ARC1_PROF_ROWAN
    AddObject LOCALID_ARC1_COUNTERPART
    WaitTime 20, VAR_RESULT
    BufferCounterpartName 2
    Message LakeVerity_Text_Arc1RowanDidYouComeOutOfThePortal
    Message LakeVerity_Text_Arc1CounterpartDidYouFallOut
    Message LakeVerity_Text_Arc1CyrusI
    WaitTime 20, VAR_RESULT
    CloseMessage
    // The first Mawile
    PlayFanfare SEQ_SE_PL_SYUWA
    AddObject LOCALID_MAWILE_1
    PlayCry SPECIES_MAWILE
    ApplyMovement LOCALID_MAWILE_1, LakeVerity_Movement_Arc1MawileJumpOut
    WaitMovement
    WaitCry
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1RowanStartled
    ApplyMovement LOCALID_ARC1_COUNTERPART, LakeVerity_Movement_Arc1ExclamationMark
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1CyrusTurnToMawile
    WaitMovement
    Message LakeVerity_Text_Arc1RowanAPokemonCameOut
    WaitABXPadPress
    CloseMessage
    // The second Mawile
    PlayFanfare SEQ_SE_PL_SYUWA
    AddObject LOCALID_MAWILE_2
    PlayCry SPECIES_MAWILE
    ApplyMovement LOCALID_MAWILE_2, LakeVerity_Movement_Arc1MawileJumpOut
    WaitMovement
    WaitCry
    ApplyMovement LOCALID_ARC1_COUNTERPART, LakeVerity_Movement_Arc1ExclamationMark
    WaitMovement
    Message LakeVerity_Text_Arc1CounterpartAnotherOne
    WaitABXPadPress
    CloseMessage
    // The portal closes
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    SetLakeVerityPortalHidden 1
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1RowanStartled
    WaitMovement
    Message LakeVerity_Text_Arc1RowanGetBack
    WaitABXPadPress
    CloseMessage
    // The chase: scatter into a snake heading west on z30, then one lap
    PlayCry SPECIES_MAWILE
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1RowanScatter
    ApplyMovement LOCALID_ARC1_COUNTERPART, LakeVerity_Movement_Arc1CounterpartScatter
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1ChaserScatter
    ApplyMovement LOCALID_MAWILE_1, LakeVerity_Movement_Arc1ChaserScatter
    ApplyMovement LOCALID_MAWILE_2, LakeVerity_Movement_Arc1ChaserScatter
    WaitMovement
    Call LakeVerity_Arc1ChaseLap
    WaitMovement
    // Rowan drops his briefcase
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1RowanStartled
    WaitMovement
    PlayFanfare SEQ_SE_DP_WALL_HIT2
    AddObject LOCALID_BRIEFCASE
    Message LakeVerity_Text_Arc1RowanMyBriefcase
    WaitABXPadPress
    CloseMessage
    // Another lap while Barry and the player come up the stairs
    ApplyFreeCameraMovement LakeVerity_Movement_Arc1CameraPanToStairs
    Call LakeVerity_Arc1ChaseLap
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1ClimbStairs
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1ClimbStairs
    WaitMovement
    // Rowan and the counterpart run past them and down the stairs
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1RunToLanding
    ApplyMovement LOCALID_ARC1_COUNTERPART, LakeVerity_Movement_Arc1RunToLanding
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1RunToLanding
    ApplyMovement LOCALID_MAWILE_1, LakeVerity_Movement_Arc1RunToLanding
    ApplyMovement LOCALID_MAWILE_2, LakeVerity_Movement_Arc1RunToLanding
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceEastStartled
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceEastStartled
    WaitMovement
    Message LakeVerity_Text_Arc1RowanOutOfTheWay
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1RowanRunDownstairs
    ApplyMovement LOCALID_ARC1_COUNTERPART, LakeVerity_Movement_Arc1CounterpartRunDownstairs
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1CyrusLapFromLanding
    ApplyMovement LOCALID_MAWILE_1, LakeVerity_Movement_Arc1Mawile1LapFromLanding
    ApplyMovement LOCALID_MAWILE_2, LakeVerity_Movement_Arc1Mawile2LapFromLanding
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1WatchRowanRunDownstairs
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1WatchRowanRunDownstairs
    WaitMovement
    RemoveObject LOCALID_ARC1_PROF_ROWAN
    RemoveObject LOCALID_ARC1_COUNTERPART
    // Barry sees Cyrus being chased in circles
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceEast
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceEast
    WaitMovement
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1ChaseLapK2
    ApplyMovement LOCALID_MAWILE_1, LakeVerity_Movement_Arc1ChaseLapK3
    ApplyMovement LOCALID_MAWILE_2, LakeVerity_Movement_Arc1ChaseLapK4
    BufferRivalName 0
    Message LakeVerity_Text_Arc1BarryThatGuysBeingChased
    WaitABXPadPress
    CloseMessage
    WaitMovement
    // They walk to the briefcase while the Mawile corner Cyrus in the west corner
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerWalkToBriefcase
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1RivalWalkToBriefcase
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1CyrusCornered
    ApplyMovement LOCALID_MAWILE_1, LakeVerity_Movement_Arc1Mawile1Corner
    ApplyMovement LOCALID_MAWILE_2, LakeVerity_Movement_Arc1Mawile2Corner
    ApplyFreeCameraMovement LakeVerity_Movement_Arc1CameraPanToBriefcase
    WaitMovement
    RestoreCamera
    BufferRivalName 0
    Message LakeVerity_Text_Arc1BarryLetsUseAPokemon
    WaitABXPadPress
    CloseMessage
    // Starter select (as the stock Route 201 briefcase)
    FadeScreenOut
    WaitFadeScreen
    StartChooseStarterScene
    SaveChosenStarter
    ReturnToField
    FadeScreenIn
    WaitFadeScreen
    GetPlayerStarterSpecies VAR_0x8000
    GivePokemon VAR_0x8000, 5, ITEM_NONE, VAR_RESULT
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceWest
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceEast
    WaitMovement
    BufferRivalName 0
    BufferRivalStarterSpeciesName 2
    Message LakeVerity_Text_Arc1BarryIllTakeThisOne
    WaitABXPadPress
    CloseMessage
    // The Mawile turn on them
    ApplyMovement LOCALID_MAWILE_2, LakeVerity_Movement_Arc1Mawile2ChargePlayer
    ApplyMovement LOCALID_MAWILE_1, LakeVerity_Movement_Arc1Mawile1ChargeRival
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceNorthStartled
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceNorthStartledLate
    WaitMovement
    PlayCry SPECIES_MAWILE
    WaitCry
    StartArc1MawileBattle
    HealParty
    // Both Mawile run off down the stairs
    ApplyMovement LOCALID_MAWILE_2, LakeVerity_Movement_Arc1Mawile2Flee
    ApplyMovement LOCALID_MAWILE_1, LakeVerity_Movement_Arc1Mawile1Flee
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerWatchMawileFlee
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1RivalWatchMawileFlee
    WaitMovement
    RemoveObject LOCALID_MAWILE_1
    RemoveObject LOCALID_MAWILE_2
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceWest
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceEast
    WaitMovement
    BufferRivalName 0
    Message LakeVerity_Text_Arc1BarryMawileRanOff
    WaitABXPadPress
    CloseMessage
    // Cyrus slowly turns toward them and comes over
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1CyrusApproach
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceNorthLate
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceNorthLate
    WaitMovement
    Message LakeVerity_Text_Arc1CyrusYouRemindMeOfSomeone
    Message LakeVerity_Text_Arc1CyrusICalledThatAFlaw
    Message LakeVerity_Text_Arc1CyrusThankYou
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1CyrusStepToBriefcase
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceEastLate
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceWestLate
    WaitMovement
    Message LakeVerity_Text_Arc1CyrusTheProfessorRan
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_CONFIRM
    RemoveObject LOCALID_BRIEFCASE
    WaitTime 15, VAR_RESULT
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1CyrusLeave
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerWatchCyrusLeave
    WaitMovement
    RemoveObject LOCALID_CYRUS
    // Barry's closing line
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1RivalStepToPlayer
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceEast
    WaitMovement
    BufferRivalName 0
    Message LakeVerity_Text_Arc1BarryPerfectTiming
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1RivalLeave
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerWatchRivalLeave
    WaitMovement
    RemoveObject LOCALID_RIVAL
    PlayFanfare SEQ_SE_DP_KAIDAN2
    SetVar VAR_ARC1_PROGRESS, 4
    SetVar VAR_VISITED_LAKE_VERITY_WITH_RIVAL, 1
    SetVar VAR_FOLLOWER_RIVAL_STATE, 4
    ReleaseAll
    End

LakeVerity_Arc1CameraStepWest:
    ApplyFreeCameraMovement LakeVerity_Movement_Arc1CameraStepWest
    WaitMovement
    Return

// Starts one lap of the chase for the five objects in the snake (no WaitMovement)
LakeVerity_Arc1ChaseLap:
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1ChaseLapK0
    ApplyMovement LOCALID_ARC1_COUNTERPART, LakeVerity_Movement_Arc1ChaseLapK1
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1ChaseLapK2
    ApplyMovement LOCALID_MAWILE_1, LakeVerity_Movement_Arc1ChaseLapK3
    ApplyMovement LOCALID_MAWILE_2, LakeVerity_Movement_Arc1ChaseLapK4
    Return

    .balign 4, 0
LakeVerity_Movement_Arc1CyrusLookAround:
    Delay16
    FaceWest
    Delay32
    Delay8
    FaceEast
    Delay32
    Delay8
    FaceSouth
    Delay16
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1FaceSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1FaceNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1FaceEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1FaceWest:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1FaceNorthLate:
    Delay32
    Delay32
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1FaceEastLate:
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1FaceWestLate:
    Delay8
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1CameraStepWest:
    WalkFastWest
    EndMovement

// (46,54) -> (46,38) -> (32,28)
    .balign 4, 0
LakeVerity_Movement_Arc1CameraPanNorth:
    WalkFastNorth 16
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1CameraPanToTerrace:
    WalkFastWest 14
    WalkFastNorth 10
    EndMovement

// (32,28) -> (28,30)
    .balign 4, 0
LakeVerity_Movement_Arc1CameraPanToStairs:
    WalkNormalWest 4
    WalkNormalSouth 2
    EndMovement

// (28,30) -> (28,31), the player's tile at the briefcase
    .balign 4, 0
LakeVerity_Movement_Arc1CameraPanToBriefcase:
    Delay16
    WalkNormalSouth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1MawileJumpOut:
    JumpFarSouth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1RowanStartled:
    EmoteExclamationMark
    JumpOnSpotFastNorth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1ExclamationMark:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1CyrusTurnToMawile:
    WalkOnSpotFastEast
    EndMovement

// (32,31) -> (29,30)
    .balign 4, 0
LakeVerity_Movement_Arc1RowanScatter:
    WalkFastWest 3
    WalkFastNorth
    EndMovement

// (33,31) -> (30,30)
    .balign 4, 0
LakeVerity_Movement_Arc1CounterpartScatter:
    WalkFastWest 3
    WalkFastNorth
    EndMovement

// Cyrus (32,30), Mawile (33,30) and (34,30): one step west, in time with Rowan
    .balign 4, 0
LakeVerity_Movement_Arc1ChaserScatter:
    WalkOnSpotFastWest 3
    WalkFastWest
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1ChaseLapK0:
    WalkFastWest
    WalkFastNorth 7
    WalkFastEast 8
    WalkFastSouth 7
    WalkFastWest 7
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1ChaseLapK1:
    WalkFastWest 2
    WalkFastNorth 7
    WalkFastEast 8
    WalkFastSouth 7
    WalkFastWest 6
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1ChaseLapK2:
    WalkFastWest 3
    WalkFastNorth 7
    WalkFastEast 8
    WalkFastSouth 7
    WalkFastWest 5
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1ChaseLapK3:
    WalkFastWest 4
    WalkFastNorth 7
    WalkFastEast 8
    WalkFastSouth 7
    WalkFastWest 4
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1ChaseLapK4:
    WalkFastWest 5
    WalkFastNorth 7
    WalkFastEast 8
    WalkFastSouth 7
    WalkFastWest 3
    EndMovement

// (23|24,37) -> (23|24,29), timed to arrive as the lap ends (120 frames)
    .balign 4, 0
LakeVerity_Movement_Arc1ClimbStairs:
    Delay32
    Delay16
    Delay8
    WalkNormalNorth 8
    EndMovement

// The snake moves 3 tiles west: Rowan to (26,30), the counterpart to (27,30), Cyrus to the corner (28,30)
    .balign 4, 0
LakeVerity_Movement_Arc1RunToLanding:
    WalkFastWest 3
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1FaceEastStartled:
    WalkOnSpotFastEast
    EmoteExclamationMark
    EndMovement

// (26,30) -> (24,38)
    .balign 4, 0
LakeVerity_Movement_Arc1RowanRunDownstairs:
    WalkFastWest 2
    WalkFastSouth 8
    EndMovement

// (27,30) -> (24,37)
    .balign 4, 0
LakeVerity_Movement_Arc1CounterpartRunDownstairs:
    WalkFastWest 3
    WalkFastSouth 7
    EndMovement

// Back into the snake at (31,30), (32,30) and (33,30)
    .balign 4, 0
LakeVerity_Movement_Arc1CyrusLapFromLanding:
    WalkFastNorth 7
    WalkFastEast 8
    WalkFastSouth 7
    WalkFastWest 5
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1Mawile1LapFromLanding:
    WalkFastWest
    WalkFastNorth 7
    WalkFastEast 8
    WalkFastSouth 7
    WalkFastWest 4
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1Mawile2LapFromLanding:
    WalkFastWest 2
    WalkFastNorth 7
    WalkFastEast 8
    WalkFastSouth 7
    WalkFastWest 3
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1WatchRowanRunDownstairs:
    Delay8
    WalkOnSpotFastSouth
    EndMovement

// (24,29) -> (28,31), facing the briefcase at (29,31)
    .balign 4, 0
LakeVerity_Movement_Arc1PlayerWalkToBriefcase:
    WalkNormalEast 2
    WalkNormalSouth 2
    WalkNormalEast 2
    WalkOnSpotNormalEast
    EndMovement

// (23,29) -> (30,31), the other side of the briefcase
    .balign 4, 0
LakeVerity_Movement_Arc1RivalWalkToBriefcase:
    WalkNormalEast 3
    WalkNormalSouth 2
    WalkNormalEast
    WalkNormalSouth
    WalkNormalEast 3
    WalkNormalNorth
    WalkOnSpotNormalWest
    EndMovement

// Part of a lap, ending in the west column: Cyrus (28,24), Mawile (28,25) and (28,26)
    .balign 4, 0
LakeVerity_Movement_Arc1CyrusCornered:
    WalkFastWest 3
    WalkFastNorth 6
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1Mawile1Corner:
    WalkFastWest 4
    WalkFastNorth 5
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1Mawile2Corner:
    WalkFastWest 5
    WalkFastNorth 4
    EndMovement

// (28,26) -> (28,30), in front of the player
    .balign 4, 0
LakeVerity_Movement_Arc1Mawile2ChargePlayer:
    WalkOnSpotFastSouth
    EmoteExclamationMark
    WalkFastSouth 3
    JumpNearFastSouth
    EndMovement

// (28,25) -> (30,30), in front of Barry
    .balign 4, 0
LakeVerity_Movement_Arc1Mawile1ChargeRival:
    Delay32
    Delay32
    WalkOnSpotFastSouth
    WalkFastSouth 4
    WalkFastEast
    WalkFastSouth
    JumpNearFastEast
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1FaceNorthStartled:
    Delay16
    WalkOnSpotFastNorth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1FaceNorthStartledLate:
    Delay32
    Delay16
    WalkOnSpotFastNorth
    EmoteExclamationMark
    EndMovement

// (28,30) -> (24,38)
    .balign 4, 0
LakeVerity_Movement_Arc1Mawile2Flee:
    WalkFasterWest 4
    WalkFasterSouth 8
    EndMovement

// (30,30) -> (24,38)
    .balign 4, 0
LakeVerity_Movement_Arc1Mawile1Flee:
    Delay8
    WalkFasterWest 6
    WalkFasterSouth 8
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerWatchMawileFlee:
    Delay8
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1RivalWatchMawileFlee:
    Delay16
    WalkOnSpotFastWest
    EndMovement

// (28,24) -> (28,30), in front of the player
    .balign 4, 0
LakeVerity_Movement_Arc1CyrusApproach:
    Delay16
    WalkOnSpotSlowSouth
    Delay16
    WalkSlowSouth 6
    EndMovement

// (28,30) -> (29,30), over the briefcase at (29,31)
    .balign 4, 0
LakeVerity_Movement_Arc1CyrusStepToBriefcase:
    WalkNormalEast
    WalkOnSpotNormalSouth
    EndMovement

// (29,30) -> (24,38)
    .balign 4, 0
LakeVerity_Movement_Arc1CyrusLeave:
    WalkNormalWest 5
    WalkNormalSouth 8
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerWatchCyrusLeave:
    Delay8
    WalkOnSpotNormalNorth
    Delay16
    WalkOnSpotNormalWest
    EndMovement

// (30,31) -> (29,31), where the briefcase was
    .balign 4, 0
LakeVerity_Movement_Arc1RivalStepToPlayer:
    WalkNormalWest
    EndMovement

// (29,31) -> (24,38)
    .balign 4, 0
LakeVerity_Movement_Arc1RivalLeave:
    WalkFastNorth
    WalkFastWest 5
    WalkFastSouth 8
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerWatchRivalLeave:
    Delay4
    WalkOnSpotFastNorth
    Delay8
    WalkOnSpotFastWest
    EndMovement

LakeVerity_EarlyProfRowan:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_TALKED_TO_LAKE_VERITY_LOW_WATER_PROF_ROWAN, LakeVerity_RowanHowWasLakeValor
    SetFlag FLAG_TALKED_TO_LAKE_VERITY_LOW_WATER_PROF_ROWAN
    BufferPlayerName 0
    Message LakeVerity_Text_RowanNoLegendaryPokemonHowWasLakeValor
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

LakeVerity_RowanHowWasLakeValor:
    BufferPlayerName 0
    Message LakeVerity_Text_RowanHowWasLakeValor
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

LakeVerity_EarlyCounterpart:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GetPlayerGender VAR_RESULT
    GoToIfEq VAR_RESULT, GENDER_MALE, LakeVerity_DawnHowWasLakeValor
    GoTo LakeVerity_LucasHowsLakeValor

LakeVerity_DawnHowWasLakeValor:
    BufferPlayerName 0
    Message LakeVerity_Text_DawnHowHasLakeValor
    GoTo LakeVerity_CloseMessageHowWasLakeValor

LakeVerity_LucasHowsLakeValor:
    BufferPlayerName 0
    Message LakeVerity_Text_LucasHowsLakeValor
    GoTo LakeVerity_CloseMessageHowWasLakeValor

LakeVerity_CloseMessageHowWasLakeValor:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
