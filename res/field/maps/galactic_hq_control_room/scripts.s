#include "macros/scrcmd.inc"
#include "res/text/bank/galactic_hq_control_room.h"
#include "res/field/maps/locals/galactic_hq_control_room.h"


    ScriptEntry GalacticHQControlRoom_OnTransition
    ScriptEntry GalacticHQControlRoom_OnResume
    ScriptEntry GalacticHQControlRoom_Saturn
    ScriptEntry GalacticHQControlRoom_MachineUxie
    ScriptEntry GalacticHQControlRoom_MachineMesprit
    ScriptEntry GalacticHQControlRoom_MachineAzelf
    ScriptEntry GalacticHQControlRoom_Dummy7
    ScriptEntry GalacticHQControlRoom_Dummy8
    ScriptEntry GalacticHQControlRoom_Dummy9
    ScriptEntry GalacticHQControlRoom_Button
    ScriptEntry GalacticHQControlRoom_Uxie
    ScriptEntry GalacticHQControlRoom_Mesprit
    ScriptEntry GalacticHQControlRoom_Azelf
    ScriptEntry GalacticHQControlRoom_CoordEvent_Saturn
    ScriptEntry GalacticHQControlRoom_Charon
    ScriptEntry GalacticHQControlRoom_Arc2Cutaway24
    ScriptEntry GalacticHQControlRoom_Arc2Cutaway213
    ScriptEntry GalacticHQControlRoom_Arc2CutawayVein
    ScriptEntryEnd

GalacticHQControlRoom_OnTransition:
    Call GalacticHQControlRoom_Arc2OnTransition
    GoToIfSet FLAG_FREED_GALACTIC_HQ_POKEMON, GalacticHQControlRoom_SetSaturnPositionEastOfButton
    End

GalacticHQControlRoom_SetSaturnPositionEastOfButton:
    SetObjectEventPos LOCALID_SATURN, 9, 6
    End

GalacticHQControlRoom_OnResume:
    CallIfEq VAR_ARC2_PROGRESS, 5, GalacticHQControlRoom_Arc2HidePlayer
    CallIfEq VAR_ARC2_PROGRESS, 35, GalacticHQControlRoom_Arc2HidePlayer
    CallIfEq VAR_ARC2_PROGRESS, 98, GalacticHQControlRoom_Arc2HidePlayer
    InitLakeGuardianContainmentUnits
    End

GalacticHQControlRoom_Saturn:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_FREED_GALACTIC_HQ_POKEMON, GalacticHQControlRoom_BossCraftedRedChain
    GoToIfSet FLAG_DEFEATED_GALACTIC_HQ_CONTROL_ROOM_SATURN, GalacticHQControlRoom_PressButtonAndFreePokemon
    Message GalacticHQControlRoom_Text_SaturnIntro
    CloseMessage
    StartTrainerBattle TRAINER_COMMANDER_SATURN_GALACTIC_HQ
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, GalacticHQControlRoom_BlackOut
    SetFlag FLAG_DEFEATED_GALACTIC_HQ_CONTROL_ROOM_SATURN
    SetVar VAR_GALACTIC_HQ_CONTROL_ROOM_STATE, 1
    Message GalacticHQControlRoom_Text_WhatMakesYouSoTough
    CloseMessage
    GetPlayerDir VAR_0x8004
    SetVar VAR_MAP_LOCAL_0x02, VAR_0x8004
    GoToIfEq VAR_0x8004, DIR_NORTH, GalacticHQControlRoom_SaturnMoveAsideNorth
    GoToIfEq VAR_0x8004, DIR_WEST, GalacticHQControlRoom_SaturnMoveAsideWest
    GoToIfEq VAR_0x8004, DIR_EAST, GalacticHQControlRoom_SaturnMoveAsideEast
    End

GalacticHQControlRoom_SaturnMoveAsideNorth:
    ApplyMovement LOCALID_SATURN, GalacticHQControlRoom_Movement_SaturnWalkEastOnSpotSouth
    WaitMovement
    GoTo GalacticHQControlRoom_SaturnEnd

GalacticHQControlRoom_SaturnMoveAsideWest:
    ApplyMovement LOCALID_SATURN, GalacticHQControlRoom_Movement_SaturnWalkSouthOnSpotNorth
    WaitMovement
    GoTo GalacticHQControlRoom_SaturnEnd

GalacticHQControlRoom_SaturnMoveAsideEast:
    ApplyMovement LOCALID_SATURN, GalacticHQControlRoom_Movement_SaturnWalkEastOnSpotWest
    WaitMovement
    GoTo GalacticHQControlRoom_SaturnEnd

GalacticHQControlRoom_SaturnEnd:
    ReleaseAll
    End

GalacticHQControlRoom_BossCraftedRedChain:
    Message GalacticHQControlRoom_Text_BossCraftedRedChain
    WaitButton
    CloseMessage
    ReleaseAll
    End

GalacticHQControlRoom_PressButtonAndFreePokemon:
    Message GalacticHQControlRoom_Text_PressButtonAndFreePokemon
    WaitButton
    CloseMessage
    ReleaseAll
    End

GalacticHQControlRoom_BlackOut:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
GalacticHQControlRoom_Movement_SaturnWalkEastOnSpotSouth:
    WalkNormalEast
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
GalacticHQControlRoom_Movement_SaturnWalkSouthOnSpotNorth:
    WalkNormalSouth
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
GalacticHQControlRoom_Movement_SaturnWalkEastOnSpotWest:
    WalkNormalEast
    WalkOnSpotNormalWest
    EndMovement

GalacticHQControlRoom_MachineUxie:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfSet FLAG_FREED_GALACTIC_HQ_POKEMON, GalacticHQControlRoom_UxieWasSealedInside
    Message GalacticHQControlRoom_Text_UxieIsSealedInside
    WaitButton
    CloseMessage
    ReleaseAll
    End

GalacticHQControlRoom_UxieWasSealedInside:
    Message GalacticHQControlRoom_Text_UxieWasSealedInside
    WaitButton
    CloseMessage
    ReleaseAll
    End

GalacticHQControlRoom_MachineMesprit:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfSet FLAG_FREED_GALACTIC_HQ_POKEMON, GalacticHQControlRoom_MespritWasSealedInside
    Message GalacticHQControlRoom_Text_MespritIsSealedInside
    WaitButton
    CloseMessage
    ReleaseAll
    End

GalacticHQControlRoom_MespritWasSealedInside:
    Message GalacticHQControlRoom_Text_MespritWasSealedInside
    WaitButton
    CloseMessage
    ReleaseAll
    End

GalacticHQControlRoom_MachineAzelf:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfSet FLAG_FREED_GALACTIC_HQ_POKEMON, GalacticHQControlRoom_AzelfWasSealedInside
    Message GalacticHQControlRoom_Text_AzelfIsSealedInside
    WaitButton
    CloseMessage
    ReleaseAll
    End

GalacticHQControlRoom_AzelfWasSealedInside:
    Message GalacticHQControlRoom_Text_AzelfWasSealedInside
    WaitButton
    CloseMessage
    ReleaseAll
    End

GalacticHQControlRoom_Dummy7:
    End

GalacticHQControlRoom_Dummy8:
    End

GalacticHQControlRoom_Dummy9:
    End

GalacticHQControlRoom_Button:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfSet FLAG_FREED_GALACTIC_HQ_POKEMON, GalacticHQControlRoom_AlreadyPressedButton
    Message GalacticHQControlRoom_Text_AskPressButton
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, GalacticHQControlRoom_FreePokemon
    GoToIfEq VAR_RESULT, MENU_NO, GalacticHQControlRoom_DontPressButton
    End

GalacticHQControlRoom_FreePokemon:
    SetVar VAR_GALACTIC_HQ_CONTROL_ROOM_STATE, 0
    PlaySE SEQ_SE_DP_BUTTON3_sseq
    BufferPlayerName 0
    Message GalacticHQControlRoom_Text_PlayerPressedButton
    CloseMessage
    ClearFlag FLAG_HIDE_MT_CORONET_1F_NORTH_ROOM_1_GRUNT_F
    SetFlag FLAG_FREED_GALACTIC_HQ_POKEMON
    DeactivateLakeGuardianContainmentUnits
    WaitTime 30, VAR_RESULT
    ApplyMovement LOCALID_MESPRIT, GalacticHQControlRoom_Movement_MespritMoveSouth
    ApplyMovement LOCALID_AZELF, GalacticHQControlRoom_Movement_AzelfMoveSouth
    ApplyMovement LOCALID_UXIE, GalacticHQControlRoom_Movement_UxieMoveSouth
    WaitMovement
    SetObjectEventPos LOCALID_MESPRIT, 2, 6
    SetObjectEventPos LOCALID_AZELF, 14, 6
    SetObjectEventPos LOCALID_UXIE, 8, 12
    Call GalacticHQControlRoom_FlickerLakeGuardians
    Call GalacticHQControlRoom_FlickerLakeGuardians
    Call GalacticHQControlRoom_FlickerLakeGuardians
    RemoveObject LOCALID_MESPRIT
    RemoveObject LOCALID_AZELF
    RemoveObject LOCALID_UXIE
    GoToIfEq VAR_MAP_LOCAL_0x02, DIR_NORTH, GalacticHQControlRoom_SaturnPlayerFaceEachOtherNorth
    GoToIfEq VAR_MAP_LOCAL_0x02, DIR_WEST, GalacticHQControlRoom_SaturnPlayerFaceEachOtherWest
    GoToIfEq VAR_MAP_LOCAL_0x02, DIR_EAST, GalacticHQControlRoom_SaturnPlayerFaceEachOtherEast
    End

GalacticHQControlRoom_FlickerLakeGuardians:
    RemoveObject LOCALID_MESPRIT
    RemoveObject LOCALID_AZELF
    RemoveObject LOCALID_UXIE
    WaitTime 2, VAR_RESULT
    ClearFlag FLAG_HIDE_GALACTIC_HQ_CONTROL_ROOM_LAKE_GUARDIANS
    AddObject LOCALID_MESPRIT
    AddObject LOCALID_AZELF
    AddObject LOCALID_UXIE
    WaitTime 2, VAR_RESULT
    Return

GalacticHQControlRoom_SaturnPlayerFaceEachOtherNorth:
    ApplyMovement LOCALID_SATURN, GalacticHQControlRoom_Movement_SaturnFacePlayerWest
    ApplyMovement LOCALID_PLAYER, GalacticHQControlRoom_Movement_PlayerWalkOnSpotEast
    WaitMovement
    GoTo GalacticHQControlRoom_RemoveSaturn
    End

GalacticHQControlRoom_SaturnPlayerFaceEachOtherWest:
    ApplyMovement LOCALID_SATURN, GalacticHQControlRoom_Movement_SaturnFacePlayerNorth
    ApplyMovement LOCALID_PLAYER, GalacticHQControlRoom_Movement_PlayerWalkOnSpotSouth
    WaitMovement
    GoTo GalacticHQControlRoom_RemoveSaturn
    End

GalacticHQControlRoom_SaturnPlayerFaceEachOtherEast:
    ApplyMovement LOCALID_SATURN, GalacticHQControlRoom_Movement_SaturnFacePlayerWest
    ApplyMovement LOCALID_PLAYER, GalacticHQControlRoom_Movement_PlayerWalkOnSpotEast
    WaitMovement
    GoTo GalacticHQControlRoom_RemoveSaturn
    End

GalacticHQControlRoom_RemoveSaturn:
    Message GalacticHQControlRoom_Text_BossCraftedRedChain
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_SATURN
    FadeScreenIn
    WaitFadeScreen
    SetFlag FLAG_HIDE_MT_CORONET_2F_CAVE_PAINTING
    ClearFlag FLAG_HIDE_MT_CORONET_2F_CAVE_PAINTING_SHARDS
    SetVar VAR_MT_CORONET_2F_STATE, 1
    ReleaseAll
    End

GalacticHQControlRoom_DontPressButton:
    CloseMessage
    ReleaseAll
    End

GalacticHQControlRoom_AlreadyPressedButton:
    Message GalacticHQControlRoom_Text_AlreadyPressedButton
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
GalacticHQControlRoom_Movement_SaturnFacePlayerWest:
    Delay8
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
GalacticHQControlRoom_Movement_SaturnFacePlayerNorth:
    Delay8
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
GalacticHQControlRoom_Movement_MespritMoveSouth:
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
GalacticHQControlRoom_Movement_AzelfMoveSouth:
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
GalacticHQControlRoom_Movement_UxieMoveSouth:
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
GalacticHQControlRoom_Movement_PlayerWalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
GalacticHQControlRoom_Movement_PlayerWalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

GalacticHQControlRoom_CoordEvent_Saturn:
    LockAll
    ApplyMovement LOCALID_SATURN, GalacticHQControlRoom_Movement_SaturnWalkOnSpotSouth
    WaitMovement
    Message GalacticHQControlRoom_Text_PressButtonAndFreePokemon2
    CloseMessage
    ApplyMovement LOCALID_PLAYER, GalacticHQControlRoom_Movement_PlayerWalkNorth
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
GalacticHQControlRoom_Movement_PlayerWalkNorth:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
GalacticHQControlRoom_Movement_SaturnWalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

GalacticHQControlRoom_Uxie:
    NPCMessage GalacticHQControlRoom_Text_UxieIsSealedInside
    End

GalacticHQControlRoom_Mesprit:
    NPCMessage GalacticHQControlRoom_Text_MespritIsSealedInside
    End

GalacticHQControlRoom_Azelf:
    NPCMessage GalacticHQControlRoom_Text_AzelfIsSealedInside
    End

GalacticHQControlRoom_Charon:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfSet FLAG_DEFEATED_GALACTIC_HQ_CONTROL_ROOM_SATURN, GalacticHQControlRoom_PerhapsAnotherOption
    ApplyMovement LOCALID_CHARON, GalacticHQControlRoom_Movement_CharonWalkOnSpotNorth
    WaitMovement
    Message GalacticHQControlRoom_Text_WhereWouldTheyGo
    CloseMessage
    ApplyMovement LOCALID_SATURN, GalacticHQControlRoom_Movement_SaturnWalkOnSpotWest
    WaitMovement
    WaitTime 20, VAR_RESULT
    Message GalacticHQControlRoom_Text_WhatAreYouSaying
    Message GalacticHQControlRoom_Text_ILookForwardToPlan
    CloseMessage
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_SATURN, GalacticHQControlRoom_Movement_SaturnWalkOnSpotNorth
    WaitMovement
    Message GalacticHQControlRoom_Text_BossCanDoWithoutSupport
    WaitButton
    CloseMessage
    ReleaseAll
    End

GalacticHQControlRoom_PerhapsAnotherOption:
    FacePlayer
    Message GalacticHQControlRoom_Text_PerhapsAnotherOption
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
GalacticHQControlRoom_Movement_SaturnWalkOnSpotWest:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
GalacticHQControlRoom_Movement_SaturnWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
GalacticHQControlRoom_Movement_CharonWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

GalacticHQControlRoom_Arc2OnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    GoToIfEq VAR_ARC2_PROGRESS, 5, GalacticHQControlRoom_Arc2SetUp24
    GoToIfEq VAR_ARC2_PROGRESS, 35, GalacticHQControlRoom_Arc2SetUp213
    GoToIfEq VAR_ARC2_PROGRESS, 98, GalacticHQControlRoom_Arc2SetUp213
    Return

GalacticHQControlRoom_Arc2SetUp24:
    Call GalacticHQControlRoom_Arc2HideStock
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    Return

GalacticHQControlRoom_Arc2SetUp213:
    Call GalacticHQControlRoom_Arc2HideStock
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    Return

GalacticHQControlRoom_Arc2HideStock:
    SetVar VAR_MAP_LOCAL_0x05, 0
    SetVar VAR_MAP_LOCAL_0x06, 0
    SetVar VAR_MAP_LOCAL_0x07, 0
    CallIfSet FLAG_HIDE_GALACTIC_HQ_CONTROL_ROOM_LAKE_GUARDIANS, GalacticHQControlRoom_Arc2Keep0236
    CallIfSet FLAG_HIDE_GALACTIC_HQ_TEAM_GALACTIC, GalacticHQControlRoom_Arc2Keep0237
    CallIfSet FLAG_HIDE_GALACTIC_HQ_CONTROL_ROOM_CHARON, GalacticHQControlRoom_Arc2Keep029E
    SetFlag FLAG_HIDE_GALACTIC_HQ_CONTROL_ROOM_LAKE_GUARDIANS
    SetFlag FLAG_HIDE_GALACTIC_HQ_TEAM_GALACTIC
    SetFlag FLAG_HIDE_GALACTIC_HQ_CONTROL_ROOM_CHARON
    Return

GalacticHQControlRoom_Arc2Keep0236:
    SetVar VAR_MAP_LOCAL_0x05, 1
    Return

GalacticHQControlRoom_Arc2Keep0237:
    SetVar VAR_MAP_LOCAL_0x06, 1
    Return

GalacticHQControlRoom_Arc2Keep029E:
    SetVar VAR_MAP_LOCAL_0x07, 1
    Return

GalacticHQControlRoom_Arc2RestoreStock:
    CallIfEq VAR_MAP_LOCAL_0x05, 0, GalacticHQControlRoom_Arc2Clear0236
    CallIfEq VAR_MAP_LOCAL_0x06, 0, GalacticHQControlRoom_Arc2Clear0237
    CallIfEq VAR_MAP_LOCAL_0x07, 0, GalacticHQControlRoom_Arc2Clear029E
    Return

GalacticHQControlRoom_Arc2Clear0236:
    ClearFlag FLAG_HIDE_GALACTIC_HQ_CONTROL_ROOM_LAKE_GUARDIANS
    Return

GalacticHQControlRoom_Arc2Clear0237:
    ClearFlag FLAG_HIDE_GALACTIC_HQ_TEAM_GALACTIC
    Return

GalacticHQControlRoom_Arc2Clear029E:
    ClearFlag FLAG_HIDE_GALACTIC_HQ_CONTROL_ROOM_CHARON
    Return

// OnResume (every field load, before the screen is shown): the player is in the room but not in the scene
GalacticHQControlRoom_Arc2HidePlayer:
    HideObject LOCALID_PLAYER
    Return

// Lift the caller's black screen
GalacticHQControlRoom_Arc2EnterScene:
    FadeScreenIn
    WaitFadeScreen
    WaitTime 20, VAR_RESULT
    // The Eclipse Shard on the console pulses
    PlayFanfare SEQ_SE_PL_SYUWA_sseq
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitTime 20, VAR_RESULT
    Return

GalacticHQControlRoom_Arc2LeaveScene:
    WaitTime 30, VAR_RESULT
    FadeScreenOut
    WaitFadeScreen
    Call GalacticHQControlRoom_Arc2RestoreStock
    Return

// 2.4 Cutaway: Team Eclipse (Kahn, Indra). Never show who sent the message.
GalacticHQControlRoom_Arc2Cutaway24:
    LockAll
    Call GalacticHQControlRoom_Arc2EnterScene
    Message GalacticHQControlRoom_Text_Arc2KahnWordFromOurNewFriend
    Message GalacticHQControlRoom_Text_Arc2KahnAManWhoWalkedOut
    Message GalacticHQControlRoom_Text_Arc2IndraOutOfIt
    Message GalacticHQControlRoom_Text_Arc2KahnSomethingStoppedHim
    Message GalacticHQControlRoom_Text_Arc2IndraFindOutWhat
    Message GalacticHQControlRoom_Text_Arc2KahnFirstLight
    Message GalacticHQControlRoom_Text_Arc2IndraBeThereFirst
    WaitButton
    CloseMessage
    // Indra turns away from the table
    ApplyMovement LOCALID_ARC2_INDRA, GalacticHQControlRoom_Arc2Movement_TurnAway
    WaitMovement
    Call GalacticHQControlRoom_Arc2LeaveScene
    SetVar VAR_ARC2_PROGRESS, 9
    Warp MAP_HEADER_JUBILIFE_CITY, 168, 777, DIR_SOUTH
    GoTo GalacticHQControlRoom_Arc2Returned
    End

// 2.13 Cutaway: Team Eclipse (Saros, Kahn). Never show who the friend is.
GalacticHQControlRoom_Arc2Cutaway213:
    LockAll
    Call GalacticHQControlRoom_Arc2EnterScene
    Message GalacticHQControlRoom_Text_Arc2SarosTheHavenIsGone
    Message GalacticHQControlRoom_Text_Arc2KahnOtherWaysToFillTheCrates
    Message GalacticHQControlRoom_Text_Arc2KahnEverySiteThatChildCloses
    Message GalacticHQControlRoom_Text_Arc2SarosAnotherSource
    Message GalacticHQControlRoom_Text_Arc2SarosWeDidntSeeItComing
    Message GalacticHQControlRoom_Text_Arc2KahnOurFriendWasntTold
    Message GalacticHQControlRoom_Text_Arc2SarosIllGoMyself
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC2_SAROS, GalacticHQControlRoom_Arc2Movement_TurnAway
    WaitMovement
    Call GalacticHQControlRoom_Arc2LeaveScene
    SetVar VAR_ARC2_PROGRESS, 39
    Warp MAP_HEADER_ETERNA_CITY, 305, 520, DIR_SOUTH
    GoTo GalacticHQControlRoom_Arc2Returned
    End

// Final cutaway (critic item 4): Team Eclipse on the vein (Kahn, Saros), after the Route 209 aftermath. The vein is
// told, not shown: the room is the same violet room. No informant is named.
GalacticHQControlRoom_Arc2CutawayVein:
    LockAll
    Call GalacticHQControlRoom_Arc2EnterScene
    Message GalacticHQControlRoom_Text_Arc2KahnWholeVeins
    Message GalacticHQControlRoom_Text_Arc2SarosDontNeedTheCrates
    WaitButton
    CloseMessage
    // Saros turns away from the table before the last line
    ApplyMovement LOCALID_ARC2_SAROS, GalacticHQControlRoom_Arc2Movement_TurnAway
    WaitMovement
    WaitTime 45, VAR_RESULT
    Message GalacticHQControlRoom_Text_Arc2SarosOneMorningMira
    WaitButton
    CloseMessage
    Call GalacticHQControlRoom_Arc2LeaveScene
    SetVar VAR_ARC2_PROGRESS, 99
    Warp MAP_HEADER_ROUTE_209, 568, 681, DIR_SOUTH
    // Route 209 at 99 has no Arc 2 cast: the end card plays over the empty tower front. Text drawn during a
    // brightness fade is black too, so fade in first.
    WaitTime 30, VAR_RESULT
    FadeScreenIn FADE_SCREEN_SPEED_SLOW
    WaitFadeScreen
    Message GalacticHQControlRoom_Text_Arc2EndOfArc2
    WaitButton
    Message GalacticHQControlRoom_Text_Arc2ToBeContinued
    WaitButton
    CloseMessage
    ReleaseAll
    End

// After the Warp the script runs on in the caller's map (the player object is new, so visible again): fade in
GalacticHQControlRoom_Arc2Returned:
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
GalacticHQControlRoom_Arc2Movement_TurnAway:
    WalkOnSpotNormalSouth
    EndMovement
