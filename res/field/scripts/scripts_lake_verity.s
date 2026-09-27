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
    ScriptEntry LakeVerity_OnFrameCyrus
    ScriptEntry LakeVerity_EarlyProfRowan
    ScriptEntry LakeVerity_EarlyCounterpart
    ScriptEntryEnd

// This map is used for every visit (the stock early-story map MAP_HEADER_LAKE_VERITY_LOW_WATER is no longer
// reachable). Until Saturn is defeated in Valor Cavern the stock game used LOW_WATER here, so the Team Galactic
// scene is hidden and the early scene (Cyrus and rival intro, Rowan and the counterpart after Canalave) is shown.
LakeVerity_OnTransition:
    CallIfUnset FLAG_DEFEATED_COMMANDER_SATURN_VALOR_CAVERN, LakeVerity_SetEarlyState
    CallIfSet FLAG_DEFEATED_COMMANDER_SATURN_VALOR_CAVERN, LakeVerity_SetTeamGalacticState
    CallIfSet FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY, LakeVerity_SetPositionsAfterTeamGalactic
    CallIfUnset FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY, LakeVerity_SetPositionsDuringTeamGalactic
    CallIfEq VAR_LAKE_VERITY_PROF_ROWAN_STATE, 0, LakeVerity_SetProfRowanStartPosition
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
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_CYRUS
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL
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
// in the middle of the castle's open roof terrace (h4). The footprint is blocked, so the player faces the portal
// from a neighbouring tile; see PORTAL_TILES / PORTAL_EDGE in tools/lake_verity/layout.py
LakeVerity_Launchpad:
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

LakeVerity_DrawbridgeSign:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message LakeVerity_Text_DrawbridgeSign
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// Early-story scenes, ported unchanged from scripts_lake_verity_low_water.s (all on the stock south-east shore,
// which the castle redesign does not touch).
LakeVerity_OnFrameCyrus:
    LockAll
    ClearHasPartner
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_RivalEnter
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_PlayerEnter
    WaitMovement
    BufferRivalName 0
    Message LakeVerity_Text_WhatsGoingOn
    CloseMessage
    AddFreeCamera 46, 53
    ApplyFreeCameraMovement LakeVerity_Movement_PanToCyrus
    WaitMovement
    WaitTime 15, VAR_RESULT
    Message LakeVerity_Text_IWillMakeTimeAndSpaceMine
    CloseMessage
    WaitTime 30, VAR_RESULT
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_CyrusWalkToPlayer
    ApplyFreeCameraMovement LakeVerity_Movement_PanBackToPlayer
    WaitMovement
    RestoreCamera
    Message LakeVerity_Text_AllowMeToPass
    CloseMessage
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_RivalMoveAwayForCyrus
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_PlayerWatchRivalMoveAwayForCyrus
    WaitMovement
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_CyrusLeave
    WaitMovement
    PlayFanfare SEQ_SE_DP_KAIDAN2
    RemoveObject LOCALID_CYRUS
    WaitTime 50, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_PlayerLookAtExit
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_RivalWalkToExit
    WaitMovement
    BufferRivalName 0
    Message LakeVerity_Text_WhatWasThatAbout
    CloseMessage
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_RivalFacePlayer
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_PlayerFaceRival
    WaitMovement
    WaitTime 30, VAR_RESULT
    BufferPlayerName 1
    Message LakeVerity_Text_LetsCatchThatLegendaryPokemon
    PlayCry SPECIES_MESPRIT
    Message LakeVerity_Text_LegendaryCry
    WaitCry
    CloseMessage
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_RivalNoticeAndLookForLegendary
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_PlayerWatchRivalLookForLegendary
    WaitMovement
    WaitTime 15, VAR_RESULT
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_RivalWalkOnSpotWest
    WaitMovement
    BufferRivalName 0
    BufferPlayerName 1
    Message LakeVerity_Text_ThatWasTheLegendaryPokemonCrying
    CloseMessage
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_RivalExclamationMark
    WaitMovement
    WaitTime 15, VAR_RESULT
    BufferPlayerName 1
    Message LakeVerity_Text_WaitWeDontHavePokeballs
    CloseMessage
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_RivalLeave
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_PlayerWatchRivalLeave
    WaitMovement
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL
    RemoveObject LOCALID_RIVAL
    PlayFanfare SEQ_SE_DP_KAIDAN2
    GoTo LakeVerity_EndRivalFollower
    End

LakeVerity_EndRivalFollower:
    SetVar VAR_FOLLOWER_RIVAL_STATE, 4
    SetVar VAR_VISITED_LAKE_VERITY_WITH_RIVAL, 1
    ReleaseAll
    End

    .balign 4, 0
LakeVerity_Movement_PanToCyrus:
    Delay8
    WalkNormalNorth 9
    EndMovement

    .balign 4, 0
LakeVerity_Movement_PanBackToPlayer:
    WalkNormalSouth 9
    EndMovement

    .balign 4, 0
LakeVerity_Movement_CyrusWalkToPlayer:
    WalkNormalSouth 5
    WalkNormalWest
    WalkNormalSouth 4
    EndMovement

    .balign 4, 0
LakeVerity_Movement_CyrusLeave:
    WalkNormalSouth 3
    SetInvisible
    EndMovement

    .balign 4, 0
LakeVerity_Movement_RivalEnter:
    WalkFastNorth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_RivalMoveAwayForCyrus:
    WalkNormalEast
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
LakeVerity_Movement_RivalWalkToExit:
    WalkNormalWest
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_RivalFacePlayer:
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
LakeVerity_Movement_RivalNoticeAndLookForLegendary:
    EmoteExclamationMark
    WalkFastNorth 3
    Delay8 3
    WalkOnSpotFastWest
    Delay8
    WalkOnSpotFastNorth
    Delay8 2
    WalkFastSouth 3
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
LakeVerity_Movement_RivalExclamationMark:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
LakeVerity_Movement_RivalWalkOnSpotWest:
    WalkOnSpotFastWest 4
    EndMovement

    .balign 4, 0
LakeVerity_Movement_RivalLeave:
    WalkFastSouth 2
    EndMovement

    .balign 4, 0
LakeVerity_Movement_PlayerEnter:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_PlayerWatchRivalMoveAwayForCyrus:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
LakeVerity_Movement_PlayerLookAtExit:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_PlayerFaceRival:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
LakeVerity_Movement_PlayerWatchRivalLookForLegendary:
    Delay8 4
    WalkOnSpotNormalNorth
    Delay8 9
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
LakeVerity_Movement_PlayerWatchRivalLeave:
    WalkOnSpotNormalSouth
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
