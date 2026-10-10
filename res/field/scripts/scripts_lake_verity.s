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
    ScriptEntry LakeVerity_Arc1Briefing
    ScriptEntry LakeVerity_Arc1StairsBlocked
    ScriptEntry LakeVerity_Arc1Rowan
    ScriptEntry LakeVerity_Arc1Counterpart
    ScriptEntry LakeVerity_Arc1OnFrameReturn
    ScriptEntry LakeVerity_Arc1GrassGuard
    ScriptEntry LakeVerity_Arc1ExitGuard
    ScriptEntry LakeVerity_Arc1DoorGuard
    ScriptEntry LakeVerity_Arc1PlaceCast
    ScriptEntry LakeVerity_Arc1StairFoot
    ScriptEntryEnd

// This map is used for every visit (the stock early-story map MAP_HEADER_LAKE_VERITY_LOW_WATER is no longer
// reachable). Until Saturn is defeated in Valor Cavern the stock game used LOW_WATER here, so the Team Galactic
// scene is hidden and the early scene (Rowan and the counterpart after Canalave) is shown.
// The Arc 1 scenes (VAR_ARC1_PROGRESS 1, 3, 4 and 7) use their own objects, gated by two stock hide flags whose
// LOW_WATER objects are unreachable: FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL hides Barry and Cyrus, and
// FLAG_HIDE_LAKE_VERITY_LOW_WATER_CYRUS hides the Arc 1 Rowan and counterpart. Both are set on every entry and
// cleared per story state by the LakeVerity_Arc1SetState* routines (see the Arc 1 section below).
LakeVerity_OnTransition:
    CallIfUnset FLAG_DEFEATED_COMMANDER_SATURN_VALOR_CAVERN, LakeVerity_SetEarlyState
    CallIfSet FLAG_DEFEATED_COMMANDER_SATURN_VALOR_CAVERN, LakeVerity_SetTeamGalacticState
    CallIfSet FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY, LakeVerity_SetPositionsAfterTeamGalactic
    CallIfUnset FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY, LakeVerity_SetPositionsDuringTeamGalactic
    CallIfEq VAR_LAKE_VERITY_PROF_ROWAN_STATE, 0, LakeVerity_SetProfRowanStartPosition
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_CYRUS
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL
    CallIfEq VAR_ARC1_PROGRESS, 1, LakeVerity_Arc1SetStateRoofLanding
    CallIfEq VAR_ARC1_PROGRESS, 3, LakeVerity_Arc1SetStateCastleTop
    CallIfEq VAR_ARC1_PROGRESS, 4, LakeVerity_Arc1SetStatePortalOpen
    CallIfEq VAR_ARC1_PROGRESS, 7, LakeVerity_Arc1SetStateReturn
    // The counterpart is Ruth for both player genders.
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
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
// Inert while the portal is hidden (it closes during the Arc 1 return scene, state 7). In Arc 1 state 4 it asks to
// step in and warps to the Distortion World (LakeVerity_Arc1LaunchpadStepIn).
LakeVerity_Launchpad:
    GoToIfSet FLAG_LAKE_VERITY_PORTAL_HIDDEN, LakeVerity_LaunchpadHidden
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfEq VAR_ARC1_PROGRESS, 4, LakeVerity_Arc1LaunchpadStepIn
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

// Dazzling Platinum Arc 1 (docs/arc1/revision/spec.md, PLAN.md scenes 3, 8, 9, 12-14).
//
// VAR_ARC1_PROGRESS 1: the player arrives from the Distortion World flashback at (32,31), hidden (see
// LakeVerity_OnResume), and watches Cyrus land beside the portal and wander to the parapet. Hands off to the
// bedroom (state 2).
//
// VAR_ARC1_PROGRESS 3: the player arrives from the Verity Lakefront with Barry. A sound from the castle top, Barry
// says they have to go see but to stay out of the tall grass, then follows the player on the walk to the castle;
// at the foot of the stairs he runs up to the terrace, where Rowan and the assistant study the portal and Cyrus
// sits apart, and the player follows on foot. At the top of the stairs a coord event runs the briefing, which ends
// with Barry and Cyrus going into the portal and state 4. The portal stays open.
//
// VAR_ARC1_PROGRESS 4: Rowan and the assistant stay by the portal, the stairs down are blocked by a coord event,
// and the portal edge (LakeVerity_Launchpad) asks to step in: state 5 and the warp to the Distortion World.
//
// VAR_ARC1_PROGRESS 7: the Distortion World warps the player back to (32,31) facing north. The return scene:
// the briefcase goes back to Rowan, the assistant closes the portal, Rowan and the assistant leave, Cyrus gives
// the player a parting gift and leaves, then Barry leaves. Ends in state 8.
//
// Hide flags: Barry and Cyrus use FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL (they are on the terrace in states 3
// and 7 and gone in state 4), Rowan and the assistant use FLAG_HIDE_LAKE_VERITY_LOW_WATER_CYRUS (states 3, 4
// and 7). Terrace (h4) walkable tiles and the portal footprint are in tools/lake_verity/layout.py: the terrace
// is x26..38, z23..32 around the portal (z24 x30..34, z25..28 x29..35, z29 x30..34); the stair landing is
// x23..25, z29..30 and the stairs are x23..24, z31..36.
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
    // Cyrus's event position is (28,24) for the castle-top scene; OnTransition moved it to (32,30)
    ClearFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL
    AddObject LOCALID_CYRUS
    FadeScreenIn FADE_SCREEN_SPEED_SLOW, COLOR_WHITE
    WaitFadeScreen
    WaitTime 45, VAR_RESULT
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1CyrusLookAround
    WaitMovement
    Message LakeVerity_Text_Arc1CyrusWhereAmI
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1CyrusWander
    WaitMovement
    Message LakeVerity_Text_Arc1CyrusThereWasNeverACastle
    Message LakeVerity_Text_Arc1CyrusTheFall
    Message LakeVerity_Text_Arc1CyrusWasIWrong
    WaitABXPadPress
    CloseMessage
    WaitTime 30, VAR_RESULT
    FadeScreenOut FADE_SCREEN_SPEED_SLOW
    WaitFadeScreen
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL
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

// Called from LakeVerity_OnTransition (before the objects are created)
LakeVerity_Arc1SetStateRoofLanding:
    SetObjectEventPos LOCALID_CYRUS, 32, 30
    Return

// State 3. Objects created here on the terrace while the field is loaded around the entrance start at the ground
// height (the terrace chunks aren't loaded yet; the old arrival saw them undrawn until they first moved).
// LakeVerity_Arc1PlaceCast, a coord event on the bridge (45,36..37), places or refreshes them once the terrace is
// loaded but still off screen. VAR_MAP_LOCAL_3 tracks this visit:
//   1  arrival walk, Barry following, cast not placed yet    2  arrival walk, cast placed
//   3  a later state-3 visit (Barry and the cast on the terrace), heights not refreshed yet    4  refreshed
// The first entry (from the Lakefront, VAR_VISITED_LAKE_VERITY_WITH_RIVAL 0) arms the arrival scene with Barry at
// the entrance; the cast is added on the bridge. Cyrus shares Barry's hide flag, so he is created too and the
// arrival removes him.
LakeVerity_Arc1SetStateCastleTop:
    ClearFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL
    GoToIfEq VAR_VISITED_LAKE_VERITY_WITH_RIVAL, 0, LakeVerity_Arc1ArmArrival
    ClearFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_CYRUS
    SetObjectEventPos LOCALID_RIVAL, 27, 31
    SetObjectEventMovementType LOCALID_RIVAL, MOVEMENT_TYPE_LOOK_WEST
    SetObjectEventDir LOCALID_RIVAL, DIR_WEST
    SetVar VAR_MAP_LOCAL_3, 3
    Return

LakeVerity_Arc1ArmArrival:
    SetVar VAR_MAP_LOCAL_2, 1
    Return

// State 4: Barry and Cyrus are in the Distortion World; Rowan and the assistant stay by the portal
LakeVerity_Arc1SetStatePortalOpen:
    ClearFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_CYRUS
    Return

// State 7: everyone is on the terrace around the player at (32,31)
LakeVerity_Arc1SetStateReturn:
    ClearFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL
    ClearFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_CYRUS
    SetObjectEventPos LOCALID_RIVAL, 31, 31
    SetObjectEventMovementType LOCALID_RIVAL, MOVEMENT_TYPE_LOOK_NORTH
    SetObjectEventDir LOCALID_RIVAL, DIR_NORTH
    SetObjectEventPos LOCALID_CYRUS, 34, 31
    SetObjectEventMovementType LOCALID_CYRUS, MOVEMENT_TYPE_LOOK_WEST
    SetObjectEventDir LOCALID_CYRUS, DIR_WEST
    SetObjectEventPos LOCALID_ARC1_PROF_ROWAN, 30, 32
    SetObjectEventPos LOCALID_ARC1_COUNTERPART, 36, 30
    SetObjectEventMovementType LOCALID_ARC1_COUNTERPART, MOVEMENT_TYPE_LOOK_WEST
    SetObjectEventDir LOCALID_ARC1_COUNTERPART, DIR_WEST
    Return

// Arc 1 arrival (state 3, first entry). The player arrives on the exit tile (46,54), Barry waits at (47,52).
// Something sounds from the castle top; Barry says they have to go see, but to stay out of the tall grass. Then he
// follows the player (the stock partner follower, as on Route 201) and the player walks to the castle. On the way:
// LakeVerity_Arc1GrassGuard (the tall grass edges), LakeVerity_Arc1ExitGuard (the exit), LakeVerity_Arc1DoorGuard
// (the castle door), LakeVerity_Arc1PlaceCast (the bridge) and LakeVerity_Arc1StairFoot, which hands over to the
// stair scene. No camera pan and no teleport: the walk is about 50 tiles.
LakeVerity_Arc1OnFrameArrival:
    LockAll
    SetVar VAR_MAP_LOCAL_2, 0
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_PROF_ROWAN
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_COUNTERPART
    // Cyrus was created on the terrace at the ground height (see LakeVerity_Arc1SetStateCastleTop): remove him,
    // LakeVerity_Arc1PlaceCast adds him back with Rowan and the assistant.
    RemoveObject LOCALID_CYRUS
    ClearFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL
    WaitTime 30, VAR_RESULT
    // A sound from the castle top
    PlayFanfare SEQ_SE_PL_SYUWA
    WaitTime 12, VAR_RESULT
    PlayFanfare SEQ_SE_DP_WALL_HIT2
    ShakeCamera 20, 2
    WaitTime 8, VAR_RESULT
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1ExclamationMark
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1ExclamationMark
    WaitMovement
    WaitTime 20, VAR_RESULT
    // Barry hops down beside the player: player (46,53) facing east, Barry (47,53) facing west
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1RivalToPlayer
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerToRival
    WaitMovement
    BufferRivalName 0
    Message LakeVerity_Text_Arc1BarryDidYouHearThat
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceNorth
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceNorth
    WaitMovement
    SetVar VAR_MAP_LOCAL_3, 1
    Call LakeVerity_Arc1StartFollowing
    ReleaseAll
    End

LakeVerity_Arc1StartFollowing:
    SetHasPartner
    SetMovementType LOCALID_RIVAL, MOVEMENT_TYPE_FOLLOW_PLAYER
    Return

LakeVerity_Arc1StopFollowing:
    ClearHasPartner
    SetMovementType LOCALID_RIVAL, MOVEMENT_TYPE_LOOK_NORTH
    Return

// Coord events on every tall grass tile next to the path, state 3 (the only reachable grass is the patch at
// x47-51, z40-46 by the entrance path). During the walk Barry turns the player back; on a later state-3 visit
// (Barry waits on the terrace) the player stops by themselves. Coord events run before the wild encounter check.
LakeVerity_Arc1GrassGuard:
    LockAll
    GoToIfEq VAR_MAP_LOCAL_3, 1, LakeVerity_Arc1GrassGuardBarry
    GoToIfEq VAR_MAP_LOCAL_3, 2, LakeVerity_Arc1GrassGuardBarry
    Message LakeVerity_Text_Arc1NoPokemonNoGrass
    WaitABXPadPress
    CloseMessage
    GetPlayerDir VAR_0x8006
    Call LakeVerity_Arc1PlayerStepBack
    ReleaseAll
    End

LakeVerity_Arc1GrassGuardBarry:
    Call LakeVerity_Arc1BarryStopsPlayer
    BufferRivalName 0
    Message LakeVerity_Text_Arc1BarryNoPokemonNoGrass
    WaitABXPadPress
    CloseMessage
    Call LakeVerity_Arc1BarryWalksPlayerBack
    ReleaseAll
    End

// Coord events on the exit tiles (46..47,54) during the walk (VAR_MAP_LOCAL_3 1 or 2)
LakeVerity_Arc1ExitGuard:
    LockAll
    Call LakeVerity_Arc1BarryStopsPlayer
    BufferRivalName 0
    Message LakeVerity_Text_Arc1BarryWhereAreYouGoing
    WaitABXPadPress
    CloseMessage
    Call LakeVerity_Arc1BarryWalksPlayerBack
    ReleaseAll
    End

// Coord event on the castle door (32,33) during the walk (VAR_MAP_LOCAL_3 2); it runs before the door warp
LakeVerity_Arc1DoorGuard:
    LockAll
    Call LakeVerity_Arc1BarryStopsPlayer
    BufferRivalName 0
    Message LakeVerity_Text_Arc1BarryNotInThere
    WaitABXPadPress
    CloseMessage
    Call LakeVerity_Arc1BarryWalksPlayerBack
    ReleaseAll
    End

// The player has just stepped onto a guarded tile in direction VAR_0x8006, and Barry (following) normally stands on
// the tile they came from, VAR_0x8007/8008 is his position. Barry jumps with an exclamation, the player turns to him.
LakeVerity_Arc1BarryStopsPlayer:
    Call LakeVerity_Arc1StopFollowing
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GetPlayerDir VAR_0x8006
    ScrCmd_Unused_06A LOCALID_RIVAL, VAR_0x8007, VAR_0x8008
    // VAR_0x8009 = 1 if Barry is right behind the player
    SetVar VAR_0x8009, 0
    SetVar VAR_0x800A, VAR_0x8004
    SetVar VAR_0x800B, VAR_0x8005
    CallIfEq VAR_0x8006, DIR_NORTH, LakeVerity_Arc1BehindNorth
    CallIfEq VAR_0x8006, DIR_SOUTH, LakeVerity_Arc1BehindSouth
    CallIfEq VAR_0x8006, DIR_WEST, LakeVerity_Arc1BehindWest
    CallIfEq VAR_0x8006, DIR_EAST, LakeVerity_Arc1BehindEast
    GoToIfNe VAR_0x8007, VAR_0x800A, LakeVerity_Arc1BarryStopsPlayerTurn
    GoToIfNe VAR_0x8008, VAR_0x800B, LakeVerity_Arc1BarryStopsPlayerTurn
    SetVar VAR_0x8009, 1
LakeVerity_Arc1BarryStopsPlayerTurn:
    CallIfEq VAR_0x8006, DIR_NORTH, LakeVerity_Arc1TurnToEachOtherNS
    CallIfEq VAR_0x8006, DIR_SOUTH, LakeVerity_Arc1TurnToEachOtherSN
    CallIfEq VAR_0x8006, DIR_WEST, LakeVerity_Arc1TurnToEachOtherWE
    CallIfEq VAR_0x8006, DIR_EAST, LakeVerity_Arc1TurnToEachOtherEW
    WaitMovement
    Return

// The player moved north: Barry (south of them) faces north, the player turns south
LakeVerity_Arc1TurnToEachOtherNS:
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1BarryNoticeNorth
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerTurnSouth
    Return

LakeVerity_Arc1TurnToEachOtherSN:
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1BarryNoticeSouth
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerTurnNorth
    Return

LakeVerity_Arc1TurnToEachOtherWE:
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1BarryNoticeWest
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerTurnEast
    Return

LakeVerity_Arc1TurnToEachOtherEW:
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1BarryNoticeEast
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerTurnWest
    Return

LakeVerity_Arc1BehindNorth:
    AddVar VAR_0x800B, 1
    Return

LakeVerity_Arc1BehindSouth:
    SubVar VAR_0x800B, 1
    Return

LakeVerity_Arc1BehindWest:
    AddVar VAR_0x800A, 1
    Return

LakeVerity_Arc1BehindEast:
    SubVar VAR_0x800A, 1
    Return

LakeVerity_Arc1PlayerTurnSouth:
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerTurnSouth
    Return

LakeVerity_Arc1PlayerTurnNorth:
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerTurnNorth
    Return

LakeVerity_Arc1PlayerTurnEast:
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerTurnEast
    Return

LakeVerity_Arc1PlayerTurnWest:
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerTurnWest
    Return

// Barry backs off one tile (still facing the player) to make room, the player walks back one tile, and Barry follows
// again. On the grass edge at x47, z44-45 the tile behind Barry is water, so there he steps south instead.
LakeVerity_Arc1BarryWalksPlayerBack:
    GoToIfEq VAR_0x8009, 0, LakeVerity_Arc1BarryWalksPlayerBackStep
    GoToIfNe VAR_0x8006, DIR_EAST, LakeVerity_Arc1BarryBacksOff
    GoToIfNe VAR_0x8007, 46, LakeVerity_Arc1BarryBacksOff
    GoToIfInRange VAR_0x8008, 44, 45, LakeVerity_Arc1BarryStepsAside
LakeVerity_Arc1BarryBacksOff:
    CallIfEq VAR_0x8006, DIR_NORTH, LakeVerity_Arc1BarryBackOffSouth
    CallIfEq VAR_0x8006, DIR_SOUTH, LakeVerity_Arc1BarryBackOffNorth
    CallIfEq VAR_0x8006, DIR_WEST, LakeVerity_Arc1BarryBackOffEast
    CallIfEq VAR_0x8006, DIR_EAST, LakeVerity_Arc1BarryBackOffWest
    GoTo LakeVerity_Arc1BarryWalksPlayerBackStep

LakeVerity_Arc1BarryStepsAside:
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1BarryStepAsideSouth
LakeVerity_Arc1BarryWalksPlayerBackStep:
    Call LakeVerity_Arc1PlayerStepBack
    Call LakeVerity_Arc1StartFollowing
    Return

LakeVerity_Arc1BarryBackOffSouth:
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1BarryBackOffSouth
    Return

LakeVerity_Arc1BarryBackOffNorth:
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1BarryBackOffNorth
    Return

LakeVerity_Arc1BarryBackOffEast:
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1BarryBackOffEast
    Return

LakeVerity_Arc1BarryBackOffWest:
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1BarryBackOffWest
    Return

// The player walks one tile back, against direction VAR_0x8006, then waits for any running movement
LakeVerity_Arc1PlayerStepBack:
    CallIfEq VAR_0x8006, DIR_NORTH, LakeVerity_Arc1PlayerStepBackSouth
    CallIfEq VAR_0x8006, DIR_SOUTH, LakeVerity_Arc1PlayerStepBackNorth
    CallIfEq VAR_0x8006, DIR_WEST, LakeVerity_Arc1PlayerStepBackEast
    CallIfEq VAR_0x8006, DIR_EAST, LakeVerity_Arc1PlayerStepBackWest
    WaitMovement
    Return

LakeVerity_Arc1PlayerStepBackSouth:
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerStepBackSouth
    Return

LakeVerity_Arc1PlayerStepBackNorth:
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerStepBackNorth
    Return

LakeVerity_Arc1PlayerStepBackEast:
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerStepBackEast
    Return

LakeVerity_Arc1PlayerStepBackWest:
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerStepBackWest
    Return

// Coord event on the bridge (45,36..37), VAR_MAP_LOCAL_3 1 (arrival walk) or 3 (re-entry). The terrace chunks are
// loaded here, so the objects get the terrace height, and the terrace (x26-38) is still well off screen. No
// LockAll: the player only pauses for the frame the script runs.
LakeVerity_Arc1PlaceCast:
    GoToIfEq VAR_MAP_LOCAL_3, 3, LakeVerity_Arc1PlaceCastReentry
    SetVar VAR_MAP_LOCAL_3, 2
    GoTo LakeVerity_Arc1PlaceCastCommon

LakeVerity_Arc1PlaceCastCommon:
    AddObject LOCALID_CYRUS
    ClearFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_CYRUS
    AddObject LOCALID_ARC1_PROF_ROWAN
    AddObject LOCALID_ARC1_COUNTERPART
    End

// A later state-3 visit: the objects exist, set them again on their own tiles so their height is recalculated
LakeVerity_Arc1PlaceCastReentry:
    SetVar VAR_MAP_LOCAL_3, 4
    SetPosition LOCALID_RIVAL, 27, 10, 31, DIR_WEST
    SetPosition LOCALID_CYRUS, 28, 10, 24, DIR_SOUTH
    SetPosition LOCALID_ARC1_PROF_ROWAN, 31, 10, 31, DIR_NORTH
    SetPosition LOCALID_ARC1_COUNTERPART, 33, 10, 30, DIR_NORTH
    End

// Coord event on the foot of the stairs (23..24,37) at the end of the walk (VAR_MAP_LOCAL_3 2). The player can only
// step onto (24,37) first (from the east or the south), with Barry right behind. The player steps west to (23,37),
// Barry takes (24,37), and he runs up the stairs to (27,31) on the terrace, where the briefing expects him.
LakeVerity_Arc1StairFoot:
    LockAll
    SetVar VAR_MAP_LOCAL_3, 0
    Call LakeVerity_Arc1StopFollowing
    ScrCmd_Unused_06A LOCALID_RIVAL, VAR_0x8007, VAR_0x8008
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerMakeRoom
    CallIfEq VAR_0x8008, 38, LakeVerity_Arc1RivalToStairFootFromSouth
    CallIfNe VAR_0x8008, 38, LakeVerity_Arc1RivalToStairFootFromEast
    WaitMovement
    BufferRivalName 0
    Message LakeVerity_Text_Arc1BarryUpThoseStairs
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1RivalRunUpStairs
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerWatchRivalRunUp
    WaitMovement
    SetVar VAR_VISITED_LAKE_VERITY_WITH_RIVAL, 1
    ReleaseAll
    End

LakeVerity_Arc1RivalToStairFootFromSouth:
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1RivalStairFootFromSouth
    Return

LakeVerity_Arc1RivalToStairFootFromEast:
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1RivalStairFootFromEast
    Return

// Coord event on the top of the stairs (23..24,30) in state 3
LakeVerity_Arc1Briefing:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 23, LakeVerity_Arc1PlayerOntoTerraceFrom23
    CallIfEq VAR_0x8004, 24, LakeVerity_Arc1PlayerOntoTerraceFrom24
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceEast
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1NoticeWest
    WaitMovement
    BufferRivalName 0
    Message LakeVerity_Text_Arc1RowanChildren
    Message LakeVerity_Text_Arc1BarryWeCameToHelp
    WaitABXPadPress
    CloseMessage
    // The assistant's readings
    ApplyMovement LOCALID_ARC1_COUNTERPART, LakeVerity_Movement_Arc1FaceWest
    WaitMovement
    BufferCounterpartName 2
    Message LakeVerity_Text_Arc1CounterpartTheReadings
    Message LakeVerity_Text_Arc1RowanMyBriefcase
    WaitABXPadPress
    CloseMessage
    // Rowan turns to Cyrus, who is sitting apart in the north-west corner
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1FaceNorth
    ApplyMovement LOCALID_ARC1_COUNTERPART, LakeVerity_Movement_Arc1FaceNorth
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceNorth
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceNorth
    WaitMovement
    Message LakeVerity_Text_Arc1RowanHaveWeMet
    WaitABXPadPress
    CloseMessage
    WaitTime 20, VAR_RESULT
    Message LakeVerity_Text_Arc1CyrusHeDoesntKnowMe
    WaitABXPadPress
    CloseMessage
    // Barry's plan, Rowan's warning
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceEast
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1FaceWest
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceEast
    WaitMovement
    BufferRivalName 0
    Message LakeVerity_Text_Arc1BarryWeGoIn
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1RowanStartled
    WaitMovement
    Message LakeVerity_Text_Arc1RowanIForbidIt
    WaitABXPadPress
    CloseMessage
    // Cyrus stands and comes over to (28,29)
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1CyrusApproach
    WaitMovement
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1FaceNorth
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceNorth
    WaitMovement
    Message LakeVerity_Text_Arc1CyrusIWillGuideThem
    WaitABXPadPress
    CloseMessage
    // Barry runs into the portal before anyone can stop him
    BufferRivalName 0
    Message LakeVerity_Text_Arc1BarryLetsGo
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1RivalRunIntoPortal
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerWatchRivalRunIn
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1RowanStartledLate
    WaitMovement
    Call LakeVerity_Arc1PortalSwallow
    RemoveObject LOCALID_RIVAL
    Message LakeVerity_Text_Arc1RowanComeBack
    WaitABXPadPress
    CloseMessage
    // Cyrus follows him in
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1FaceEast
    WaitMovement
    Message LakeVerity_Text_Arc1CyrusNoTimeToLose
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1CyrusWalkIntoPortal
    WaitMovement
    Call LakeVerity_Arc1PortalSwallow
    // Cyrus's hide flag is Barry's, which RemoveObject LOCALID_RIVAL already set
    RemoveObject LOCALID_CYRUS
    ApplyMovement LOCALID_ARC1_COUNTERPART, LakeVerity_Movement_Arc1ExclamationMark
    WaitMovement
    BufferCounterpartName 2
    Message LakeVerity_Text_Arc1CounterpartTheyreInside
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1FaceWest
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceEast
    WaitMovement
    Message LakeVerity_Text_Arc1RowanDontFollowThem
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC1_PROGRESS, 4
    ReleaseAll
    End

// (23,30) -> (26,30)
LakeVerity_Arc1PlayerOntoTerraceFrom23:
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerOntoTerrace3
    WaitMovement
    Return

// (24,30) -> (26,30)
LakeVerity_Arc1PlayerOntoTerraceFrom24:
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerOntoTerrace2
    WaitMovement
    Return

// Someone steps into the portal: the swirl sound and a quick white flash
LakeVerity_Arc1PortalSwallow:
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    Return

// Coord event on the top of the stairs (23..24,30) in state 4: the player can't leave without a starter
LakeVerity_Arc1StairsBlocked:
    LockAll
    ApplyMovement LOCALID_ARC1_COUNTERPART, LakeVerity_Movement_Arc1ExclamationMark
    WaitMovement
    BufferCounterpartName 2
    BufferRivalName 0
    Message LakeVerity_Text_Arc1CounterpartTheBriefcaseIsInThere
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerStepBackNorth
    WaitMovement
    ReleaseAll
    End

LakeVerity_Arc1Rowan:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message LakeVerity_Text_Arc1RowanThatWorldIsNoPlace
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

LakeVerity_Arc1Counterpart:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    BufferCounterpartName 2
    Message LakeVerity_Text_Arc1CounterpartReadingsHolding
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// State 4, from LakeVerity_Launchpad (the portal edge bg events)
LakeVerity_Arc1LaunchpadStepIn:
    Message LakeVerity_Text_Arc1StepIntoThePortal
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, LakeVerity_LaunchpadStayBehind
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    SetVar VAR_ARC1_PROGRESS, 5
    // The Distortion World workstream's Arc 1 puzzle map entry
    Warp MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS, 0, 20, 12, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    End

// State 7: back from the Distortion World at (32,31) facing north. Barry (31,31), Cyrus (34,31),
// Rowan (30,32) and the assistant (36,30) were placed by LakeVerity_Arc1SetStateReturn.
LakeVerity_Arc1OnFrameReturn:
    LockAll
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_PROF_ROWAN
    SetFlag FLAG_HIDE_LAKE_VERITY_LOW_WATER_COUNTERPART
    WaitTime 30, VAR_RESULT
    // Rowan hurries over, the briefcase goes back to him
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1ExclamationMark
    WaitMovement
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1RowanStepToPlayer
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceSouthLate
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceSouthLate
    WaitMovement
    Message LakeVerity_Text_Arc1RowanYoureBack
    WaitABXPadPress
    CloseMessage
    BufferPlayerName 1
    PlayFanfare SEQ_SE_CONFIRM
    Message LakeVerity_Text_Arc1HandedTheBriefcase
    WaitABXPadPress
    Message LakeVerity_Text_Arc1RowanADealIsADeal
    WaitABXPadPress
    CloseMessage
    // The assistant closes the portal
    ApplyMovement LOCALID_ARC1_COUNTERPART, LakeVerity_Movement_Arc1ExclamationMark
    WaitMovement
    BufferCounterpartName 2
    Message LakeVerity_Text_Arc1CounterpartItsClosing
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceNorth
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceNorth
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1FaceNorth
    ApplyMovement LOCALID_ARC1_COUNTERPART, LakeVerity_Movement_Arc1FaceNorth
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1FaceNorth
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    SetLakeVerityPortalHidden 1
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitTime 30, VAR_RESULT
    // Rowan and the assistant leave
    BufferCounterpartName 2
    Message LakeVerity_Text_Arc1RowanItsGone
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC1_PROF_ROWAN, LakeVerity_Movement_Arc1RowanLeave
    ApplyMovement LOCALID_ARC1_COUNTERPART, LakeVerity_Movement_Arc1CounterpartLeave
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerWatchRowanLeave
    WaitMovement
    RemoveObject LOCALID_ARC1_PROF_ROWAN
    RemoveObject LOCALID_ARC1_COUNTERPART
    // Cyrus's parting gift
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1CyrusStepToPlayer
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceEastLate
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceEastLate
    WaitMovement
    Message LakeVerity_Text_Arc1CyrusYouRemindMe
    Message LakeVerity_Text_Arc1CyrusTakeItToRowan
    SetVar VAR_0x8004, ITEM_ECLIPSE_SHARD
    SetVar VAR_0x8005, 1
    GiveItemQuantity
    CloseMessage
    ApplyMovement LOCALID_CYRUS, LakeVerity_Movement_Arc1CyrusLeave
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1PlayerWatchCyrusLeave
    WaitMovement
    RemoveObject LOCALID_CYRUS
    // Barry's closing line
    ApplyMovement LOCALID_RIVAL, LakeVerity_Movement_Arc1FaceEast
    ApplyMovement LOCALID_PLAYER, LakeVerity_Movement_Arc1FaceWest
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
    SetVar VAR_ARC1_PROGRESS, 8
    SetVar VAR_VISITED_LAKE_VERITY_WITH_RIVAL, 1
    SetVar VAR_FOLLOWER_RIVAL_STATE, 4
    ReleaseAll
    End

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

// (32,30) -> (30,30), a look at the portal, then over to the south parapet (33,32)
    .balign 4, 0
LakeVerity_Movement_Arc1CyrusWander:
    WalkSlowWest 2
    Delay16
    FaceNorth
    Delay32
    Delay16
    WalkSlowEast 3
    Delay8
    WalkSlowSouth 2
    Delay32
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
LakeVerity_Movement_Arc1FaceSouthLate:
    Delay16
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1FaceEastLate:
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1ExclamationMark:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1NoticeWest:
    WalkOnSpotNormalWest
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1RowanStartled:
    EmoteExclamationMark
    JumpOnSpotFastNorth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1RowanStartledLate:
    Delay32
    WalkOnSpotFastWest
    EmoteExclamationMark
    EndMovement

// (47,52) -> (47,53), facing the player
    .balign 4, 0
LakeVerity_Movement_Arc1RivalToPlayer:
    WalkOnSpotFastSouth
    WalkFastSouth
    WalkOnSpotFastWest
    EndMovement

// (46,54) -> (46,53), facing Barry
    .balign 4, 0
LakeVerity_Movement_Arc1PlayerToRival:
    Delay8
    WalkNormalNorth
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1BarryNoticeNorth:
    WalkOnSpotFastNorth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1BarryNoticeSouth:
    WalkOnSpotFastSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1BarryNoticeWest:
    WalkOnSpotFastWest
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1BarryNoticeEast:
    WalkOnSpotFastEast
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerTurnSouth:
    Delay8
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerTurnNorth:
    Delay8
    WalkOnSpotFastNorth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerTurnEast:
    Delay8
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerTurnWest:
    Delay8
    WalkOnSpotFastWest
    EndMovement

// Barry backs off one tile, still facing the player
    .balign 4, 0
LakeVerity_Movement_Arc1BarryBackOffSouth:
    FaceNorth
    LockDir
    WalkNormalSouth
    UnlockDir
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1BarryBackOffNorth:
    FaceSouth
    LockDir
    WalkNormalNorth
    UnlockDir
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1BarryBackOffEast:
    FaceWest
    LockDir
    WalkNormalEast
    UnlockDir
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1BarryBackOffWest:
    FaceEast
    LockDir
    WalkNormalWest
    UnlockDir
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1BarryStepAsideSouth:
    WalkNormalSouth
    FaceNorth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerStepBackSouth:
    Delay4
    WalkNormalSouth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerStepBackEast:
    Delay4
    WalkNormalEast
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerStepBackWest:
    Delay4
    WalkNormalWest
    EndMovement

// (24,37) -> (23,37), looking up the stairs
    .balign 4, 0
LakeVerity_Movement_Arc1PlayerMakeRoom:
    WalkNormalWest
    WalkOnSpotNormalNorth
    EndMovement

// (25,37) -> (24,37)
    .balign 4, 0
LakeVerity_Movement_Arc1RivalStairFootFromEast:
    Delay8
    WalkNormalWest
    WalkOnSpotNormalNorth
    EndMovement

// (24,38) -> (24,37)
    .balign 4, 0
LakeVerity_Movement_Arc1RivalStairFootFromSouth:
    Delay8
    WalkNormalNorth
    EndMovement

// (24,37) -> up the stairs -> (27,31), waiting on the terrace
    .balign 4, 0
LakeVerity_Movement_Arc1RivalRunUpStairs:
    WalkFastNorth 7
    WalkFastEast 3
    WalkFastSouth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerWatchRivalRunUp:
    Delay8
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerOntoTerrace3:
    WalkNormalEast 3
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerOntoTerrace2:
    WalkNormalEast 2
    EndMovement

// (28,24) -> (28,29)
    .balign 4, 0
LakeVerity_Movement_Arc1CyrusApproach:
    WalkOnSpotSlowSouth
    Delay16
    WalkSlowSouth 5
    WalkOnSpotNormalWest
    EndMovement

// (27,31) -> (29,31) -> (29,28), the portal's west edge
    .balign 4, 0
LakeVerity_Movement_Arc1RivalRunIntoPortal:
    WalkOnSpotFastEast
    WalkFasterEast 2
    WalkFasterNorth 3
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerWatchRivalRunIn:
    Delay16
    WalkOnSpotFastEast
    Delay8
    WalkOnSpotFastNorth
    EndMovement

// (28,29) -> (29,29) -> (29,28)
    .balign 4, 0
LakeVerity_Movement_Arc1CyrusWalkIntoPortal:
    WalkNormalEast
    WalkNormalNorth
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerStepBackNorth:
    WalkNormalNorth
    EndMovement

// (30,32) -> (32,32), behind the player
    .balign 4, 0
LakeVerity_Movement_Arc1RowanStepToPlayer:
    WalkFastEast 2
    WalkOnSpotNormalNorth
    EndMovement

// (32,32) -> along z32 -> landing -> down the stairs (24,37)
    .balign 4, 0
LakeVerity_Movement_Arc1RowanLeave:
    WalkNormalWest 6
    WalkNormalNorth 2
    WalkNormalWest 2
    WalkNormalSouth 7
    EndMovement

// (36,30) -> (36,32) -> along z32 behind Rowan -> (24,36)
    .balign 4, 0
LakeVerity_Movement_Arc1CounterpartLeave:
    WalkNormalSouth 2
    WalkNormalWest 10
    WalkNormalNorth 2
    WalkNormalWest 2
    WalkNormalSouth 6
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerWatchRowanLeave:
    Delay16
    WalkOnSpotNormalSouth
    Delay32
    WalkOnSpotNormalWest
    EndMovement

// (34,31) -> (33,31), beside the player
    .balign 4, 0
LakeVerity_Movement_Arc1CyrusStepToPlayer:
    WalkSlowWest
    EndMovement

// (33,31) -> (33,32) -> along z32 -> landing -> down the stairs (24,37)
    .balign 4, 0
LakeVerity_Movement_Arc1CyrusLeave:
    WalkNormalSouth
    WalkNormalWest 7
    WalkNormalNorth 2
    WalkNormalWest 2
    WalkNormalSouth 7
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerWatchCyrusLeave:
    Delay8
    WalkOnSpotNormalSouth
    Delay32
    Delay16
    WalkOnSpotNormalWest
    EndMovement

// (31,31) -> (31,32) -> along z32 -> landing -> down the stairs (24,37)
    .balign 4, 0
LakeVerity_Movement_Arc1RivalLeave:
    WalkFastSouth
    WalkFastWest 5
    WalkFastNorth 2
    WalkFastWest 2
    WalkFastSouth 7
    EndMovement

    .balign 4, 0
LakeVerity_Movement_Arc1PlayerWatchRivalLeave:
    Delay4
    WalkOnSpotFastSouth
    Delay16
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
