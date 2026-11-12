#include "macros/scrcmd.inc"
#include "res/text/bank/eterna_city.h"
#include "res/text/bank/special_met_location_names.h"
#include "res/field/maps/locals/eterna_city.h"


    ScriptEntry EternaCity_CoordEvent_CynthiaGiveCut
    ScriptEntry EternaCity_GruntM1
    ScriptEntry EternaCity_GruntM2
    ScriptEntry EternaCity_GruntM3
    ScriptEntry EternaCity_PokemonBreederM
    ScriptEntry EternaCity_PokemonBreederF1
    ScriptEntry EternaCity_RatherFetching_Unused
    ScriptEntry EternaCity_BugCatcher1
    ScriptEntry EternaCity_AceTrainerF
    ScriptEntry EternaCity_ExpertM
    ScriptEntry EternaCity_NinjaBoy
    ScriptEntry EternaCity_MapSignpost
    ScriptEntry EternaCity_GymSignpost
    ScriptEntry EternaCity_SignboardRadRickshawsCycleShop
    ScriptEntry EternaCity_SignboardTeamGalacticEternaBuilding
    ScriptEntry EternaCity_SignboardUndergroundMansHouse
    ScriptEntry EternaCity_SignboardEternaCondominiums
    ScriptEntry EternaCity_Statue
    ScriptEntry EternaCity_PokemonBreederF2
    ScriptEntry EternaCity_CoordEvent_BlockExitSouth
    ScriptEntry EternaCity_OnTransition
    ScriptEntry EternaCity_BugCatcher2
    ScriptEntry EternaCity_CoordEvent_BlockExitWest
    ScriptEntry EternaCity_Gardenia
    ScriptEntry EternaCity_CoordEvent_Rival
    ScriptEntry EternaCity_CoordEvent_CynthiaTryGiveEgg
    ScriptEntry EternaCity_CoordEvent_CynthiaBlockBikeShop
    ScriptEntry EternaCity_Cynthia
    ScriptEntry EternaCity_Arc2RuthTalk
    ScriptEntry EternaCity_Arc2CyrusTalk
    ScriptEntry EternaCity_Arc2GariusScene
    ScriptEntry EternaCity_Arc2HavenArrival
    ScriptEntry EternaCity_Arc2GardeniaHavenTalk
    ScriptEntry EternaCity_CineCityEntry
    ScriptEntryEnd

EternaCity_OnTransition:
    SetVar VAR_CINE_CITY_PENDING, 1
    Call EternaCity_Arc2SetObjects
    CallIfEq VAR_ETERNA_CITY_STATE, 4, EternaCity_SetCynthiaPositionForGiveEgg
    CheckItem ITEM_BICYCLE, 1, VAR_MAP_LOCAL_0x00
    GoToIfEq VAR_MAP_LOCAL_0x00, TRUE, EternaCity_CheckShouldBlockExits
    End

EternaCity_CheckShouldBlockExits:
    CheckItem ITEM_EXPLORER_KIT, 1, VAR_MAP_LOCAL_0x00
    GoToIfEq VAR_MAP_LOCAL_0x00, TRUE, EternaCity_SetVarDontBlockExits
    End

EternaCity_SetVarDontBlockExits:
    SetVar VAR_ETERNA_CITY_BLOCK_EXITS_STATE, 0
    End

EternaCity_SetCynthiaPositionForGiveEgg:
    SetObjectEventPos LOCALID_CYNTHIA, 307, 541
    Return

EternaCity_PokemonBreederM:
    NPCMessage EternaCity_Text_GetYourselfABicycle
    End

EternaCity_RatherFetching_Unused:
    NPCMessage EternaCity_Text_PokemonAreRatherFetching
    End

EternaCity_PokemonBreederF1:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_TEAM_GALACTIC_LEFT_ETERNA_BUILDING, EternaCity_WhatWillHappenToGalacticBuilding
    Message EternaCity_Text_AtmosphereHasGottenCreepy
    WaitButton
    CloseMessage
    ReleaseAll
    End

EternaCity_WhatWillHappenToGalacticBuilding:
    Message EternaCity_Text_WhatWillHappenToGalacticBuilding
    WaitButton
    CloseMessage
    ReleaseAll
    End

EternaCity_BugCatcher1:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_TEAM_GALACTIC_LEFT_ETERNA_BUILDING, EternaCity_DoYouUseKickstand
    Message EternaCity_Text_GalacticTookFavoritePokemon
    WaitButton
    CloseMessage
    ReleaseAll
    End

EternaCity_DoYouUseKickstand:
    Message EternaCity_Text_DoYouUseKickstand
    WaitButton
    CloseMessage
    ReleaseAll
    End

EternaCity_MapSignpost:
    ShowMapSign EternaCity_Text_EternaCityHistoryLiving
    End

EternaCity_GymSignpost:
    ShowScrollingSign EternaCity_Text_SignPokemonGym
    End

EternaCity_SignboardRadRickshawsCycleShop:
    ShowLandmarkSign EternaCity_Text_SignRadRickshawsCycleShop
    End

EternaCity_SignboardTeamGalacticEternaBuilding:
    GoToIfLt VAR_ARC2_PROGRESS, 29, EternaCity_HavenSignPlain
    GoToIfGe VAR_ARC2_PROGRESS, 35, EternaCity_HavenSignPlain
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, EternaCity_HavenSignPlain
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message EternaCity_Text_SignTeamGalacticEternaBuilding
    WaitButton
    Message EternaCity_Text_Arc2HavenBuzz
    WaitButton
    CloseMessage
    ReleaseAll
    End

EternaCity_SignboardUndergroundMansHouse:
    ShowLandmarkSign EternaCity_Text_SignUndergroundMansHouse
    End

EternaCity_SignboardEternaCondominiums:
    ShowLandmarkSign EternaCity_Text_SignEternaCondominiums
    End

EternaCity_CoordEvent_CynthiaGiveCut:
    // Stock: Cynthia gives HM01 at the Galactic building trees. Removed for Arc 2 (plan D11): field moves are
    // Resonator-only. The entry slot stays so the script numbering doesn't move.
    End

EternaCity_SetCynthiaPositionForGiveCutZ522:
    GoToIfEq VAR_0x8004, 304, EternaCity_SetCynthiaPositionForGiveCutX304
    GoToIfEq VAR_0x8004, 305, EternaCity_SetCynthiaPositionForGiveCutX305
    GoToIfEq VAR_0x8004, 306, EternaCity_SetCynthiaPositionForGiveCutX306
    End

EternaCity_SetCynthiaPositionForGiveCutX304:
    SetObjectEventPos LOCALID_CYNTHIA, 313, 524
    GoTo EternaCity_CynthiaGiveCut
    End

EternaCity_SetCynthiaPositionForGiveCutX305:
    SetObjectEventPos LOCALID_CYNTHIA, 314, 524
    GoTo EternaCity_CynthiaGiveCut
    End

EternaCity_SetCynthiaPositionForGiveCutX306:
    SetObjectEventPos LOCALID_CYNTHIA, 315, 524
    GoTo EternaCity_CynthiaGiveCut
    End

EternaCity_SetCynthiaPositionForGiveCutZ523:
    SetObjectEventPos LOCALID_CYNTHIA, 313, 523
    GoTo EternaCity_CynthiaGiveCut
    End

EternaCity_SetCynthiaPositionForGiveCutZ524:
    SetObjectEventPos LOCALID_CYNTHIA, 313, 524
    GoTo EternaCity_CynthiaGiveCut
    End

EternaCity_SetCynthiaPositionForGiveCutZ525:
    SetObjectEventPos LOCALID_CYNTHIA, 313, 525
    GoTo EternaCity_CynthiaGiveCut
    End

EternaCity_CynthiaGiveCut:
    ClearFlag FLAG_HIDE_ETERNA_CITY_CYNTHIA
    AddObject LOCALID_CYNTHIA
    LockObject LOCALID_CYNTHIA
    CallIfEq VAR_0x8005, 522, EternaCity_EnterCynthiaForGiveCutZ522
    CallIfNe VAR_0x8005, 522, EternaCity_EnterCynthiaForGiveCutNotZ522
    BufferPlayerName 0
    Message EternaCity_Text_OhYouHaveAPokedex
    CloseMessage
    CallIfEq VAR_0x8005, 522, EternaCity_CynthiaWalkOnSpotEastNorth
    CallIfNe VAR_0x8005, 522, EternaCity_CynthiaWalkOnSpotEastWest
    Message EternaCity_Text_TryUsingThis
    SetVar VAR_0x8004, ITEM_HM01
    SetVar VAR_0x8005, 1
    CallCommonScript CommonScript_AddItemQuantity
    Message EternaCity_Text_CutCanBeUsedInField
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 522, EternaCity_CynthiaLeaveAfterCutZ522
    GoToIfEq VAR_0x8005, 523, EternaCity_CynthiaLeaveAfterCutZ523
    GoToIfEq VAR_0x8005, 524, EternaCity_CynthiaLeaveAfterCutZ524
    GoToIfEq VAR_0x8005, 525, EternaCity_CynthiaLeaveAfterCutZ525
    End

EternaCity_CynthiaLeaveAfterCutZ522:
    GoToIfEq VAR_0x8004, 304, EternaCity_CynthiaLeaveAfterCutX304
    GoToIfEq VAR_0x8004, 305, EternaCity_CynthiaLeaveAfterCutX305
    GoToIfEq VAR_0x8004, 306, EternaCity_CynthiaLeaveAfterCutX306
    End

EternaCity_EnterCynthiaForGiveCutZ522:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaNoticeAndWalkUpToPlayerZ522
    WaitMovement
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWalkOnSpotSouth
    WaitMovement
    Return

EternaCity_EnterCynthiaForGiveCutNotZ522:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaNoticeAndWalkUpToPlayerNotZ522
    WaitMovement
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWalkOnSpotEast
    WaitMovement
    Return

EternaCity_CynthiaWalkOnSpotEastNorth:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaWalkOnSpotEastNorth
    WaitMovement
    Return

EternaCity_CynthiaWalkOnSpotEastWest:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaWalkOnSpotEastWest
    WaitMovement
    Return

EternaCity_CynthiaLeaveAfterCutX304:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaLeaveAfterCutX304
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWatchCynthiaLeaveAfterCutZ522
    WaitMovement
    GoTo EternaCity_CynthiaGiveCutEnd
    End

EternaCity_CynthiaLeaveAfterCutX305:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaLeaveAfterCutX305
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWatchCynthiaLeaveAfterCutZ522
    WaitMovement
    GoTo EternaCity_CynthiaGiveCutEnd
    End

EternaCity_CynthiaLeaveAfterCutX306:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaLeaveAfterCutX306
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWatchCynthiaLeaveAfterCutZ522
    WaitMovement
    GoTo EternaCity_CynthiaGiveCutEnd
    End

EternaCity_CynthiaLeaveAfterCutZ523:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaLeaveAfterCutZ523
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWatchCynthiaLeaveAfterCutNotZ522
    WaitMovement
    GoTo EternaCity_CynthiaGiveCutEnd
    End

EternaCity_CynthiaLeaveAfterCutZ524:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaLeaveAfterCutZ524
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWatchCynthiaLeaveAfterCutNotZ522
    WaitMovement
    GoTo EternaCity_CynthiaGiveCutEnd
    End

EternaCity_CynthiaLeaveAfterCutZ525:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaLeaveAfterCutZ525
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWatchCynthiaLeaveAfterCutNotZ522
    WaitMovement
    GoTo EternaCity_CynthiaGiveCutEnd
    End

EternaCity_CynthiaGiveCutEnd:
    RemoveObject LOCALID_CYNTHIA
    SetVar VAR_ETERNA_CITY_STATE, 2
    ReleaseAll
    End

    .balign 4, 0
EternaCity_Movement_CynthiaNoticeAndWalkUpToPlayerZ522:
    WalkNormalWest 4
    EmoteExclamationMark
    WalkNormalWest 5
    WalkNormalNorth
    EndMovement

    .balign 4, 0
EternaCity_Movement_CynthiaNoticeAndWalkUpToPlayerNotZ522:
    WalkNormalWest 4
    EmoteExclamationMark
    WalkNormalWest 4
    EndMovement

    .balign 4, 0
EternaCity_Movement_CynthiaWalkOnSpotEastNorth:
    WalkOnSpotNormalEast
    Delay8 2
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
EternaCity_Movement_CynthiaWalkOnSpotEastWest:
    WalkOnSpotNormalEast
    Delay8 2
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_CynthiaLeaveAfterCutX304:
    WalkNormalWest 5
    WalkNormalSouth 10
    EndMovement

    .balign 4, 0
EternaCity_Movement_CynthiaLeaveAfterCutX305:
    WalkNormalWest 6
    WalkNormalSouth 10
    EndMovement

    .balign 4, 0
EternaCity_Movement_CynthiaLeaveAfterCutX306:
    WalkNormalWest 7
    WalkNormalSouth 10
    EndMovement

    .balign 4, 0
EternaCity_Movement_CynthiaLeaveAfterCutZ523:
    WalkNormalSouth
    WalkNormalWest 6
    WalkNormalSouth 10
    EndMovement

    .balign 4, 0
EternaCity_Movement_CynthiaLeaveAfterCutZ524:
    WalkNormalSouth
    WalkNormalWest 6
    WalkNormalSouth 10
    EndMovement

    .balign 4, 0
EternaCity_Movement_CynthiaLeaveAfterCutZ525:
    WalkNormalNorth
    WalkNormalWest 6
    WalkNormalSouth 11
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWatchCynthiaLeaveAfterCutZ522:
    Delay8
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWatchCynthiaLeaveAfterCutNotZ522:
    Delay8 2
    WalkOnSpotNormalWest
    EndMovement

EternaCity_GruntM1:
    NPCMessage EternaCity_Text_StayAwayFromStatue
    End

EternaCity_GruntM2:
    NPCMessage EternaCity_Text_IllLetYouKeepPokemon
    End

EternaCity_GruntM3:
    NPCMessage EternaCity_Text_HaveYouSeenOurBuilding
    End

EternaCity_AceTrainerF:
    NPCMessage EternaCity_Text_TheySayThisIsAnOldCity
    End

EternaCity_ExpertM:
    NPCMessage EternaCity_Text_EternaCitysNotLikeBefore
    End

EternaCity_NinjaBoy:
    NPCMessage EternaCity_Text_AwesomePokemonFromLongAgo
    End

EternaCity_Statue:
    EventMessage EternaCity_Text_ItsEternaCitysPokemonStatue
    End

EternaCity_PokemonBreederF2:
    GoToIfSet FLAG_RECEIVED_EXPLORER_KIT, EternaCity_GoingUndergroundIsABlast
    NPCMessage EternaCity_Text_YouDontHaveExplorerKit
    End

EternaCity_GoingUndergroundIsABlast:
    NPCMessage EternaCity_Text_GoingUndergroundIsABlast
    End

EternaCity_CoordEvent_BlockExitSouth:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 303, EternaCity_PokemonBreederFBlockExitSouthX303
    CallIfEq VAR_0x8004, 304, EternaCity_PokemonBreederFBlockExitSouthX304
    CallIfEq VAR_0x8004, 305, EternaCity_PokemonBreederFBlockExitSouthX305
    CallIfEq VAR_0x8004, 306, EternaCity_PokemonBreederFBlockExitSouthX306
    CallIfEq VAR_0x8004, 307, EternaCity_PokemonBreederFBlockExitSouthX307
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWalkOnSpotWestToFacePokemonBreederF
    WaitMovement
    Message EternaCity_Text_YouDontHaveExplorerKit_ArrowPrompt
    CloseMessage
    CallIfEq VAR_0x8004, 303, EternaCity_PokemonBreederFMoveBackX303
    CallIfEq VAR_0x8004, 304, EternaCity_PokemonBreederFMoveBackX304
    CallIfEq VAR_0x8004, 305, EternaCity_PokemonBreederFMoveBackX305
    CallIfEq VAR_0x8004, 306, EternaCity_PokemonBreederFMoveBackX306
    CallIfEq VAR_0x8004, 307, EternaCity_PokemonBreederFMoveBackX307
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWalkNorth
    WaitMovement
    ReleaseAll
    End

EternaCity_PokemonBreederFBlockExitSouthX303:
    ApplyMovement LOCALID_POKEMON_BREEDER_F_2, EternaCity_Movement_PokemonBreederFBlockExitSouthX303
    WaitMovement
    Return

EternaCity_PokemonBreederFBlockExitSouthX304:
    ApplyMovement LOCALID_POKEMON_BREEDER_F_2, EternaCity_Movement_PokemonBreederFBlockExitSouthX304
    WaitMovement
    Return

EternaCity_PokemonBreederFBlockExitSouthX305:
    ApplyMovement LOCALID_POKEMON_BREEDER_F_2, EternaCity_Movement_PokemonBreederFBlockExitSouthX305
    WaitMovement
    Return

EternaCity_PokemonBreederFBlockExitSouthX306:
    ApplyMovement LOCALID_POKEMON_BREEDER_F_2, EternaCity_Movement_PokemonBreederFBlockExitSouthX306
    WaitMovement
    Return

EternaCity_PokemonBreederFBlockExitSouthX307:
    ApplyMovement LOCALID_POKEMON_BREEDER_F_2, EternaCity_Movement_PokemonBreederFBlockExitSouthX307
    WaitMovement
    Return

EternaCity_PokemonBreederFMoveBackX303:
    Return

EternaCity_PokemonBreederFMoveBackX304:
    ApplyMovement LOCALID_POKEMON_BREEDER_F_2, EternaCity_Movement_PokemonBreederFMoveBackX304
    WaitMovement
    Return

EternaCity_PokemonBreederFMoveBackX305:
    ApplyMovement LOCALID_POKEMON_BREEDER_F_2, EternaCity_Movement_PokemonBreederFMoveBackX305
    WaitMovement
    Return

EternaCity_PokemonBreederFMoveBackX306:
    ApplyMovement LOCALID_POKEMON_BREEDER_F_2, EternaCity_Movement_PokemonBreederFMoveBackX306
    WaitMovement
    Return

EternaCity_PokemonBreederFMoveBackX307:
    ApplyMovement LOCALID_POKEMON_BREEDER_F_2, EternaCity_Movement_PokemonBreederFMoveBackX307
    WaitMovement
    Return

    .balign 4, 0
EternaCity_Movement_PokemonBreederFBlockExitSouthX303:
    WalkOnSpotFastEast
    EmoteExclamationMark
    Delay4
    EndMovement

    .balign 4, 0
EternaCity_Movement_PokemonBreederFBlockExitSouthX304:
    WalkOnSpotFastEast
    EmoteExclamationMark
    Delay4
    WalkNormalEast
    EndMovement

    .balign 4, 0
EternaCity_Movement_PokemonBreederFBlockExitSouthX305:
    WalkOnSpotFastEast
    EmoteExclamationMark
    Delay4
    WalkNormalEast 2
    EndMovement

    .balign 4, 0
EternaCity_Movement_PokemonBreederFBlockExitSouthX306:
    WalkOnSpotFastEast
    EmoteExclamationMark
    Delay4
    WalkNormalEast 3
    EndMovement

    .balign 4, 0
EternaCity_Movement_PokemonBreederFBlockExitSouthX307:
    WalkOnSpotFastEast
    EmoteExclamationMark
    Delay4
    WalkNormalEast 4
    EndMovement

EternaCity_Movement_Unused:
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
EternaCity_Movement_PokemonBreederFMoveBackX304:
    WalkNormalWest
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
EternaCity_Movement_PokemonBreederFMoveBackX305:
    WalkNormalWest 2
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
EternaCity_Movement_PokemonBreederFMoveBackX306:
    WalkNormalWest 3
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
EternaCity_Movement_PokemonBreederFMoveBackX307:
    WalkNormalWest 4
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWalkOnSpotWestToFacePokemonBreederF:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWalkNorth:
    WalkNormalNorth
    EndMovement

EternaCity_BugCatcher2:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfUnset FLAG_RECEIVED_BICYCLE, EternaCity_FeelsGreatRidingABike
    GoToIfGe VAR_ROUTE_207_COUNTERPART_TRIGGER_STATE, 1, EternaCity_FeelsGreatRidingABike
    Message EternaCity_Text_YouGotABicycle
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_BUG_CATCHER_2, EternaCity_Movement_BugCatcher2FaceSouth
    WaitMovement
    ReleaseAll
    End

EternaCity_FeelsGreatRidingABike:
    Message EternaCity_Text_FeelsGreatRidingABike
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_BUG_CATCHER_2, EternaCity_Movement_BugCatcher2FaceSouth
    WaitMovement
    ReleaseAll
    End

EternaCity_CoordEvent_BlockExitWest:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8005, 532, EternaCity_BugCatcher2BlockExitWestZ532
    CallIfEq VAR_0x8005, 533, EternaCity_BugCatcher2BlockExitWestZ533
    CallIfEq VAR_0x8005, 534, EternaCity_BugCatcher2BlockExitWestZ534
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerFaceNorth
    WaitMovement
    Message EternaCity_Text_YouGotABicycle_ArrowPrompt
    CloseMessage
    CallIfEq VAR_0x8005, 532, EternaCity_PushBackPlayerZ532
    CallIfEq VAR_0x8005, 533, EternaCity_PushBackPlayerZ533
    CallIfEq VAR_0x8005, 534, EternaCity_PushBackPlayerZ534
    ReleaseAll
    End

EternaCity_BugCatcher2BlockExitWestZ532:
    ApplyMovement LOCALID_BUG_CATCHER_2, EternaCity_Movement_BugCatcher2BlockExitWestZ532
    WaitMovement
    Return

EternaCity_BugCatcher2BlockExitWestZ533:
    ApplyMovement LOCALID_BUG_CATCHER_2, EternaCity_Movement_BugCatcher2BlockExitWestZ533
    WaitMovement
    Return

EternaCity_BugCatcher2BlockExitWestZ534:
    ApplyMovement LOCALID_BUG_CATCHER_2, EternaCity_Movement_BugCatcher2BlockExitWestZ534
    WaitMovement
    Return

EternaCity_PushBackPlayerZ532:
    ApplyMovement LOCALID_BUG_CATCHER_2, EternaCity_Movement_BugCatcher2PushPlayerAndMoveBackZ532
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerGetPushedBack
    WaitMovement
    Return

EternaCity_PushBackPlayerZ533:
    ApplyMovement LOCALID_BUG_CATCHER_2, EternaCity_Movement_BugCatcher2PushPlayerAndMoveBackZ533
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerGetPushedBack
    WaitMovement
    Return

EternaCity_PushBackPlayerZ534:
    ApplyMovement LOCALID_BUG_CATCHER_2, EternaCity_Movement_BugCatcher2PushPlayerAndMoveBackZ534
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerGetPushedBack
    WaitMovement
    Return

    .balign 4, 0
EternaCity_Movement_PlayerGetPushedBack:
    WalkNormalEast
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerFaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
EternaCity_Movement_BugCatcher2FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
EternaCity_Movement_BugCatcher2BlockExitWestZ532:
    FaceSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
EternaCity_Movement_BugCatcher2BlockExitWestZ533:
    FaceSouth
    EmoteExclamationMark
    WalkNormalSouth
    EndMovement

    .balign 4, 0
EternaCity_Movement_BugCatcher2BlockExitWestZ534:
    FaceSouth
    EmoteExclamationMark
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
EternaCity_Movement_BugCatcher2PushPlayerAndMoveBackZ532:
    WalkNormalSouth
    WalkNormalNorth
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
EternaCity_Movement_BugCatcher2PushPlayerAndMoveBackZ533:
    WalkNormalSouth
    WalkNormalNorth 2
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
EternaCity_Movement_BugCatcher2PushPlayerAndMoveBackZ534:
    WalkNormalSouth
    WalkNormalNorth 3
    WalkOnSpotNormalSouth
    EndMovement

EternaCity_Gardenia:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    BufferRivalName 0
    Message EternaCity_Text_ImThisTownsGymLeader
    CloseMessage
    ApplyMovement LOCALID_GARDENIA, EternaCity_Movement_GardeniaWalkOnSpotNorth
    WaitMovement
    LoadDoorAnimation 9, 17, 24, 18, ANIMATION_TAG_DOOR_1
    PlayDoorOpenAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement LOCALID_GARDENIA, EternaCity_Movement_GardeniaEnterGym
    WaitMovement
    RemoveObject LOCALID_GARDENIA
    PlayDoorCloseAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    UnloadAnimation ANIMATION_TAG_DOOR_1
    ReleaseAll
    End

    .balign 4, 0
EternaCity_Movement_GardeniaWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
EternaCity_Movement_GardeniaEnterGym:
    WalkNormalNorth
    EndMovement

EternaCity_CoordEvent_Rival:
    // Stock: Barry runs in and Galactic boss Cyrus speaks at the statue. Removed for Arc 2 (Cyrus travels with
    // the player). Its coord event is gone; the entry slot stays.
    End

EternaCity_RivalRunIntoPlayerZ523:
    ApplyMovement LOCALID_GARIUS, EternaCity_Movement_RivalRunIntoPlayerZ523
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerGetPushedByRivalZ523
    WaitMovement
    GoTo EternaCity_YouCameToSeeStatue
    End

EternaCity_RivalRunIntoPlayerZ524:
    ApplyMovement LOCALID_GARIUS, EternaCity_Movement_RivalRunIntoPlayerZ524
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerGetPushedByRivalZ524
    WaitMovement
    GoTo EternaCity_YouCameToSeeStatue
    End

EternaCity_RivalRunIntoPlayerZ525:
    ApplyMovement LOCALID_GARIUS, EternaCity_Movement_RivalRunIntoPlayerZ525
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerGetPushedByRivalZ525
    WaitMovement
    GoTo EternaCity_YouCameToSeeStatue
    End

EternaCity_YouCameToSeeStatue:
    PlaySE SEQ_SE_DP_WALL_HIT2_sseq
    Message EternaCity_Text_BigThud
    CloseMessage
    CallCommonScript CommonScript_SetRivalBGM
    BufferRivalName 0
    BufferPlayerName 1
    Message EternaCity_Text_YouCameToSeeStatue
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 523, EternaCity_WalkToStatueZ523
    GoToIfEq VAR_0x8005, 524, EternaCity_WalkToStatueZ524
    GoToIfEq VAR_0x8005, 525, EternaCity_WalkToStatueZ525
    End

EternaCity_WalkToStatueZ523:
    ApplyMovement LOCALID_GARIUS, EternaCity_Movement_RivalWalkInFrontOfPlayerZ523
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerFaceRivalZ523
    WaitMovement
    ApplyMovement LOCALID_GARIUS, EternaCity_Movement_RivalWalkToStatueZ523Or525
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWalkToStatueZ523
    WaitMovement
    GoTo EternaCity_Cyrus
    End

EternaCity_WalkToStatueZ524:
    ApplyMovement LOCALID_GARIUS, EternaCity_Movement_RivalWalkInFrontOfPlayerZ524
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerFaceRivalZ524
    WaitMovement
    ApplyMovement LOCALID_GARIUS, EternaCity_Movement_RivalWalkToStatueZ524
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWalkToStatueZ524
    WaitMovement
    GoTo EternaCity_Cyrus
    End

EternaCity_WalkToStatueZ525:
    ApplyMovement LOCALID_GARIUS, EternaCity_Movement_RivalWalkInFrontOfPlayerZ525
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerFaceRivalZ525
    WaitMovement
    ApplyMovement LOCALID_GARIUS, EternaCity_Movement_RivalWalkToStatueZ523Or525
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWalkToStatueZ525
    WaitMovement
    GoTo EternaCity_Cyrus
    End

EternaCity_Cyrus:
    BufferRivalName 0
    Message EternaCity_Text_WhatThe
    CloseMessage
    CallCommonScript CommonScript_FadeToDefaultMusic_2
    ScrCmd_32E
    ScrCmd_332
    AddFreeCamera 323, 524
    ApplyFreeCameraMovement EternaCity_Movement_CameraPanEast
    WaitMovement
    Message EternaCity_Text_SoThisIsEternasStatue
    CloseMessage
    WaitTime 15, VAR_RESULT
    ApplyMovement LOCALID_CYRUS, EternaCity_Movement_CyrusWalkToPlayer
    ApplyFreeCameraMovement EternaCity_Movement_CameraPanWest
    WaitMovement
    RestoreCamera
    Message EternaCity_Text_PardonMeStandAside
    CloseMessage
    ApplyMovement LOCALID_CYRUS, EternaCity_Movement_CyrusLeave
    ApplyMovement LOCALID_GARIUS, EternaCity_Movement_RivalWatchCyrusLeave
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerMoveAsideAndWatchCyrusLeave
    WaitMovement
    RemoveObject LOCALID_CYRUS
    WaitTime 35, VAR_RESULT
    ApplyMovement LOCALID_GARIUS, EternaCity_Movement_RivalFacePlayer
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerFaceRival
    WaitMovement
    BufferRivalName 0
    Message EternaCity_Text_GoCheckOutStatueSeeYou
    CloseMessage
    ApplyMovement LOCALID_GARIUS, EternaCity_Movement_RivalLeave
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWatchRivalLeave
    WaitMovement
    RemoveObject LOCALID_GARIUS
    SetVar VAR_ETERNA_CITY_STATE, 1
    ReleaseAll
    End

    .balign 4, 0
EternaCity_Movement_RivalRunIntoPlayerZ523:
    WalkFastNorth 10
    WalkFastEast 4
    EndMovement

    .balign 4, 0
EternaCity_Movement_RivalRunIntoPlayerZ524:
    WalkFastNorth 9
    WalkFastEast 4
    EndMovement

    .balign 4, 0
EternaCity_Movement_RivalRunIntoPlayerZ525:
    WalkFastNorth 8
    WalkFastEast 4
    EndMovement

    .balign 4, 0
EternaCity_Movement_RivalWalkInFrontOfPlayerZ523:
    WalkNormalSouth
    WalkNormalEast
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
EternaCity_Movement_RivalWalkInFrontOfPlayerZ524:
    WalkNormalSouth
    WalkNormalEast 2
    WalkNormalNorth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_RivalWalkInFrontOfPlayerZ525:
    WalkNormalNorth
    WalkNormalEast
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
EternaCity_Movement_RivalWalkToStatueZ523Or525:
    WalkNormalEast 19
    EndMovement

    .balign 4, 0
EternaCity_Movement_RivalWalkToStatueZ524:
    WalkNormalEast 18
    EndMovement

    .balign 4, 0
EternaCity_Movement_RivalWatchCyrusLeave:
    Delay8 3
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_RivalLeave:
    WalkFastWest 12
    EndMovement

    .balign 4, 0
EternaCity_Movement_RivalFacePlayer:
    WalkFastSouth
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerGetPushedByRivalZ523:
    Delay4 10
    Delay2
    Delay1
    LockDir
    WalkFastEast
    UnlockDir
    FaceWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerGetPushedByRivalZ524:
    Delay4 9
    Delay2
    Delay1
    LockDir
    WalkFastEast
    UnlockDir
    FaceWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerGetPushedByRivalZ525:
    Delay4 8
    Delay2
    Delay1
    LockDir
    WalkFastEast
    UnlockDir
    FaceWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerFaceRivalZ523:
    Delay8
    Delay4
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerFaceRivalZ524:
    Delay8
    Delay4
    WalkOnSpotNormalSouth
    Delay4
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerFaceRivalZ525:
    Delay8
    Delay4
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWalkToStatueZ523:
    WalkNormalSouth
    WalkNormalEast 18
    WalkNormalSouth
    WalkNormalEast
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWalkToStatueZ524:
    WalkNormalEast 18
    WalkNormalSouth
    WalkNormalEast
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWalkToStatueZ525:
    WalkNormalNorth
    WalkNormalEast 18
    WalkNormalSouth
    WalkNormalEast
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerMoveAsideAndWatchCyrusLeave:
    WalkNormalSouth
    WalkOnSpotNormalEast
    Delay8 2
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerFaceRival:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWatchRivalLeave:
    Delay8
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_CameraPanEast:
    WalkNormalEast 4
    EndMovement

    .balign 4, 0
EternaCity_Movement_CameraPanWest:
    WalkNormalWest 4
    EndMovement

    .balign 4, 0
EternaCity_Movement_CyrusWalkToPlayer:
    WalkNormalWest 3
    WalkNormalNorth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_CyrusLeave:
    Delay8 2
    WalkNormalWest 14
    EndMovement

EternaCity_CoordEvent_CynthiaTryGiveEgg:
    LockAll
    SetObjectEventDir LOCALID_CYNTHIA, DIR_EAST
    SetObjectEventMovementType LOCALID_CYNTHIA, MOVEMENT_TYPE_LOOK_EAST
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 540, EternaCity_SetCynthiaPositionForGiveEggZ540
    GoToIfEq VAR_0x8005, 541, EternaCity_SetCynthiaPositionForGiveEggZ541
    GoToIfEq VAR_0x8005, 542, EternaCity_SetCynthiaPositionForGiveEggZ542
    GoToIfEq VAR_0x8005, 543, EternaCity_SetCynthiaPositionForGiveEggZ543
    GoToIfEq VAR_0x8005, 544, EternaCity_SetCynthiaPositionForGiveEggZ544
    GoToIfEq VAR_0x8005, 545, EternaCity_SetCynthiaPositionForGiveEggZ545
    End

EternaCity_SetCynthiaPositionForGiveEggZ540:
    SetObjectEventPos LOCALID_CYNTHIA, 304, 548
    Call EternaCity_ShowCynthia
    GoTo EternaCity_CynthiaTryGiveEgg
    End

EternaCity_SetCynthiaPositionForGiveEggZ541:
    SetObjectEventPos LOCALID_CYNTHIA, 304, 549
    Call EternaCity_ShowCynthia
    GoTo EternaCity_CynthiaTryGiveEgg
    End

EternaCity_SetCynthiaPositionForGiveEggZ542:
    SetObjectEventPos LOCALID_CYNTHIA, 304, 550
    Call EternaCity_ShowCynthia
    GoTo EternaCity_CynthiaTryGiveEgg
    End

EternaCity_SetCynthiaPositionForGiveEggZ543:
    SetObjectEventPos LOCALID_CYNTHIA, 304, 551
    Call EternaCity_ShowCynthia
    GoTo EternaCity_CynthiaTryGiveEgg
    End

EternaCity_SetCynthiaPositionForGiveEggZ544:
    SetObjectEventPos LOCALID_CYNTHIA, 304, 552
    Call EternaCity_ShowCynthia
    GoTo EternaCity_CynthiaTryGiveEgg
    End

EternaCity_SetCynthiaPositionForGiveEggZ545:
    SetObjectEventPos LOCALID_CYNTHIA, 304, 553
    Call EternaCity_ShowCynthia
    GoTo EternaCity_CynthiaTryGiveEgg
    End

EternaCity_ShowCynthia:
    ClearFlag FLAG_HIDE_ETERNA_CITY_CYNTHIA
    AddObject LOCALID_CYNTHIA
    LockObject LOCALID_CYNTHIA
    Return

EternaCity_CynthiaTryGiveEgg:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaNoticeAndWalkUpToPlayer
    WaitMovement
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWalkOnSpotWestToFaceCynthia
    WaitMovement
    Message EternaCity_Text_WillYouAcceptEgg
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, EternaCity_RefusedEgg
    GetPartyCount VAR_RESULT
    GoToIfGe VAR_RESULT, 6, EternaCity_PartyIsFull
    Call EternaCity_GiveTogepiEgg
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaLeaveAfterEgg
    WaitMovement
    RemoveObject LOCALID_CYNTHIA
    GoTo EternaCity_CynthiaTryGiveEggEnd
    End

EternaCity_GiveTogepiEgg:
    PlayFanfare SEQ_FANFA4_sseq
    WaitFanfare
    Message EternaCity_Text_ThatsWonderful
    Message EternaCity_Text_KeepEggInYourParty
    CloseMessage
    GiveEgg SPECIES_TOGEPI, SPECIAL_METLOC_NAME_CYNTHIA
    SetVar VAR_ETERNA_CITY_STATE, 5
    Return

EternaCity_PartyIsFull:
    Call EternaCity_NoRoomForEgg
    GoTo EternaCity_CynthiaTryGiveEggEnd
    End

EternaCity_RefusedEgg:
    Call EternaCity_DontFeelObligated
    GoTo EternaCity_CynthiaTryGiveEggEnd
    End

EternaCity_CynthiaTryGiveEggEnd:
    ReleaseAll
    End

    .balign 4, 0
EternaCity_Movement_CynthiaNoticeAndWalkUpToPlayer:
    WalkNormalNorth 3
    EmoteExclamationMark
    WalkNormalNorth 5
    WalkNormalEast 2
    WalkNormalEast
    EndMovement

    .balign 4, 0
EternaCity_Movement_CynthiaLeaveAfterEgg:
    WalkNormalWest 3
    WalkNormalSouth 9
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWalkOnSpotWestToFaceCynthia:
    WalkOnSpotNormalWest
    EndMovement

EternaCity_Cynthia:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfEq VAR_ETERNA_CITY_STATE, 4, EternaCity_CynthiaTryAgainGiveEgg
    ReleaseAll
    End

EternaCity_CynthiaTryAgainGiveEgg:
    Message EternaCity_Text_WillYouAcceptThisEgg
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, EternaCity_RefusedEggAgain
    GetPartyCount VAR_RESULT
    GoToIfGe VAR_RESULT, 6, EternaCity_PartyIsFullAgain
    Call EternaCity_GiveTogepiEgg
    GetPlayerDir VAR_RESULT
    GoToIfEq VAR_RESULT, DIR_NORTH, EternaCity_CynthiaLeaveAfterEggNorth
    GoToIfEq VAR_RESULT, DIR_SOUTH, EternaCity_CynthiaLeaveAfterEggSouth
    GoToIfEq VAR_RESULT, DIR_WEST, EternaCity_CynthiaLeaveAfterEggWest
    GoToIfEq VAR_RESULT, DIR_EAST, EternaCity_CynthiaLeaveAfterEggEast
    End

EternaCity_CynthiaLeaveAfterEggNorth:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaLeaveNorthSouthWest
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWatchCynthiaLeaveNorthSouth
    WaitMovement
    GoTo EternaCity_RemoveCynthia
    End

EternaCity_CynthiaLeaveAfterEggSouth:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaLeaveNorthSouthWest
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWatchCynthiaLeaveNorthSouth
    WaitMovement
    GoTo EternaCity_RemoveCynthia
    End

EternaCity_CynthiaLeaveAfterEggWest:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaLeaveNorthSouthWest
    WaitMovement
    GoTo EternaCity_RemoveCynthia
    End

EternaCity_CynthiaLeaveAfterEggEast:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaLeaveNorthSouthEast
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWatchCynthiaLeaveEast
    WaitMovement
    GoTo EternaCity_RemoveCynthia
    End

EternaCity_RemoveCynthia:
    RemoveObject LOCALID_CYNTHIA
    GoTo EternaCity_CynthiaTryAgainGiveEggEnd
    End

EternaCity_PartyIsFullAgain:
    Call EternaCity_NoRoomForEgg
    GoTo EternaCity_CynthiaTryAgainGiveEggEnd
    End

EternaCity_RefusedEggAgain:
    Call EternaCity_DontFeelObligated
    GoTo EternaCity_CynthiaTryAgainGiveEggEnd
    End

EternaCity_CynthiaTryAgainGiveEggEnd:
    ReleaseAll
    End

EternaCity_NoRoomForEgg:
    SetVar VAR_ETERNA_CITY_STATE, 4
    Message EternaCity_Text_NoRoomForEgg
    WaitButton
    CloseMessage
    Return

EternaCity_DontFeelObligated:
    Message EternaCity_Text_DontFeelObligated
    WaitButton
    CloseMessage
    SetVar VAR_ETERNA_CITY_STATE, 4
    Return

EternaCity_CoordEvent_CynthiaBlockBikeShop:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 540, EternaCity_CynthiaWalkOnSpotEastZ540
    GoToIfEq VAR_0x8005, 541, EternaCity_CynthiaWalkOnSpotEastZ541
    GoToIfEq VAR_0x8005, 542, EternaCity_CynthiaWalkOnSpotEastZ542
    GoToIfEq VAR_0x8005, 543, EternaCity_CynthiaWalkOnSpotEastZ543
    GoToIfEq VAR_0x8005, 544, EternaCity_CynthiaWalkOnSpotEastZ544
    GoToIfEq VAR_0x8005, 545, EternaCity_CynthiaWalkOnSpotEastZ545
    End

EternaCity_CynthiaWalkOnSpotEastZ540:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaWalkOnSpotEast
    WaitMovement
    GoTo EternaCity_DontLeaveWithoutEgg
    End

EternaCity_CynthiaWalkOnSpotEastZ541:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaWalkOnSpotEast
    WaitMovement
    GoTo EternaCity_DontLeaveWithoutEgg
    End

EternaCity_CynthiaWalkOnSpotEastZ542:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaWalkOnSpotEast
    WaitMovement
    GoTo EternaCity_DontLeaveWithoutEgg
    End

EternaCity_CynthiaWalkOnSpotEastZ543:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaWalkOnSpotEast
    WaitMovement
    GoTo EternaCity_DontLeaveWithoutEgg
    End

EternaCity_CynthiaWalkOnSpotEastZ544:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaWalkOnSpotEast
    WaitMovement
    GoTo EternaCity_DontLeaveWithoutEgg
    End

EternaCity_CynthiaWalkOnSpotEastZ545:
    ApplyMovement LOCALID_CYNTHIA, EternaCity_Movement_CynthiaWalkOnSpotEast
    WaitMovement
    GoTo EternaCity_DontLeaveWithoutEgg
    End

EternaCity_DontLeaveWithoutEgg:
    Message EternaCity_Text_DontLeaveWithoutEgg
    CloseMessage
    ApplyMovement LOCALID_PLAYER, EternaCity_Movement_PlayerWalkNormalWest
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
EternaCity_Movement_CynthiaWalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
EternaCity_Movement_CynthiaLeaveNorthSouthWest:
    WalkNormalWest 3
    WalkNormalSouth 9
    EndMovement

    .balign 4, 0
EternaCity_Movement_CynthiaLeaveNorthSouthEast:
    WalkNormalSouth
    WalkNormalWest 3
    WalkNormalSouth 8
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWalkNormalWest:
    WalkNormalWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWatchCynthiaLeaveNorthSouth:
    Delay8
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
EternaCity_Movement_PlayerWatchCynthiaLeaveEast:
    Delay8 2
    Delay4
    WalkOnSpotNormalWest
    EndMovement

EternaCity_HavenSignPlain:
    ShowLandmarkSign 39
    End

EternaCity_Arc2SetObjects:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (Arc 1 D1) */
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_20
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_21
    GoToIfLt VAR_ARC2_PROGRESS, 29, EternaCity_Arc2Return
    // From 34 on, the middle Haven tree (305,521) stays cut, so leaving the Haven never shuts the player in.
    CallIfGe VAR_ARC2_PROGRESS, 34, EternaCity_Arc2KeepHavenTreeCut
    GoToIfGe VAR_ARC2_PROGRESS, 34, EternaCity_Arc2SetObjectsHaven
    GoToIfEq VAR_ARC2_PROGRESS, 33, EternaCity_Arc2SetObjectsTrees
    // 29-32: Ruth and Cyrus wait by the Gym; Garius is there at 31
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    CallIfEq VAR_ARC2_PROGRESS, 31, EternaCity_Arc2ShowGarius
    Return

EternaCity_Arc2KeepHavenTreeCut:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_2
    Return

EternaCity_Arc2ShowGarius:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_20
    Return

// 33: Gardenia and Ruth by the Haven trees, Cyrus a little apart. The arrival line runs from the frame table.
EternaCity_Arc2SetObjectsTrees:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_21
    SetObjectEventPos LOCALID_RUTH, 306, 523
    SetObjectEventDir LOCALID_RUTH, DIR_NORTH
    SetObjectEventMovementType LOCALID_RUTH, MOVEMENT_TYPE_LOOK_NORTH
    SetObjectEventPos LOCALID_CYRUS, 308, 522
    SetObjectEventDir LOCALID_CYRUS, DIR_WEST
    SetObjectEventMovementType LOCALID_CYRUS, MOVEMENT_TYPE_LOOK_WEST
    SetVar VAR_MAP_LOCAL_0x02, 1
    Return

// 34: Gardenia and Ruth are inside; Cyrus waits outside by the trees. 35+: the party has moved on.
EternaCity_Arc2SetObjectsHaven:
    GoToIfGe VAR_ARC2_PROGRESS, 35, EternaCity_Arc2Return
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    SetObjectEventPos LOCALID_CYRUS, 308, 522
    SetObjectEventDir LOCALID_CYRUS, DIR_WEST
    SetObjectEventMovementType LOCALID_CYRUS, MOVEMENT_TYPE_LOOK_WEST
EternaCity_Arc2Return:
    Return

EternaCity_Arc2RuthTalk:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfGe VAR_ARC2_PROGRESS, 33, EternaCity_Arc2RuthTalkHaven
    Message EternaCity_Text_Arc2RuthBeforeGym
    WaitButton
    CloseMessage
    ReleaseAll
    End

EternaCity_Arc2RuthTalkHaven:
    Message EternaCity_Text_Arc2RuthAtHaven
    WaitButton
    CloseMessage
    ReleaseAll
    End

EternaCity_Arc2CyrusTalk:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfGe VAR_ARC2_PROGRESS, 33, EternaCity_Arc2CyrusTalkHaven
    Message EternaCity_Text_Arc2CyrusBeforeGym
    WaitButton
    CloseMessage
    ReleaseAll
    End

EternaCity_Arc2CyrusTalkHaven:
    Message EternaCity_Text_Arc2CyrusWaitHere
    WaitButton
    CloseMessage
    ReleaseAll
    End

EternaCity_Arc2GardeniaHavenTalk:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message EternaCity_Text_Arc2GardeniaTrees
    WaitButton
    CloseMessage
    ReleaseAll
    End

// ---------------------------------------------------------------------------------------------------------------
// 2.11: Garius by the Gym door (frame trigger at progress 31; the player has just walked out of the Gym onto
// (312,563)). Garius battle 1, then Gardenia comes out (2.12 start), then the walk to the Haven.
// ---------------------------------------------------------------------------------------------------------------
EternaCity_Arc2GariusScene:
    LockAll
    ApplyMovement LOCALID_GARIUS, EternaCity_Arc2Movement_GariusWalkUp
    WaitMovement
    ApplyMovement LOCALID_PLAYER, EternaCity_Arc2Movement_FaceEast
    WaitMovement
    BufferRivalName 0
    Message EternaCity_Text_Arc2GariusTookYouLongEnough
    BufferRivalName 0
    Message EternaCity_Text_Arc2GariusStillFollowing
    BufferRivalName 0
    Message EternaCity_Text_Arc2GariusBattleMe
    CloseMessage
    GetPlayerStarterSpecies VAR_RESULT
    GoToIfEq VAR_RESULT, SPECIES_TURTWIG, EternaCity_Arc2GariusBattleTurtwig
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, EternaCity_Arc2GariusBattleChimchar
    StartTrainerBattle TRAINER_GARIUS_ARC2_ETERNA_PIPLUP
    GoTo EternaCity_Arc2GariusAfterBattle

EternaCity_Arc2GariusBattleTurtwig:
    StartTrainerBattle TRAINER_GARIUS_ARC2_ETERNA_TURTWIG
    GoTo EternaCity_Arc2GariusAfterBattle

EternaCity_Arc2GariusBattleChimchar:
    StartTrainerBattle TRAINER_GARIUS_ARC2_ETERNA_CHIMCHAR
    GoTo EternaCity_Arc2GariusAfterBattle

// The screenplay sets 32 whatever the result: a loss heals the party and the scene goes on (no blackout).
EternaCity_Arc2GariusAfterBattle:
    CheckWonBattle VAR_RESULT
    CallIfEq VAR_RESULT, FALSE, EternaCity_Arc2HealAfterLoss
    SetVar VAR_ARC2_PROGRESS, 32
    BufferRivalName 0
    Message EternaCity_Text_Arc2GariusYoureGood
    BufferRivalName 0
    Message EternaCity_Text_Arc2GariusRowanCalled
    CloseMessage
    ApplyMovement LOCALID_GARIUS, EternaCity_Arc2Movement_GariusLeave
    WaitMovement
    RemoveObject LOCALID_GARIUS
    GoTo EternaCity_Arc2GardeniaComesOut

// A lost scripted battle leaves the field unloaded (COMMON hazards): reload it, then heal.
EternaCity_Arc2HealAfterLoss:
    ReturnToField
    FadeScreenIn
    WaitFadeScreen
    HealParty
    Return

// 2.12 start: Gardenia steps out of the Gym door (312,562) behind the player.
EternaCity_Arc2GardeniaComesOut:
    WaitTime 15, VAR_RESULT
    LoadDoorAnimation 9, 17, 24, 18, ANIMATION_TAG_DOOR_1
    PlayDoorOpenAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    ClearFlag FLAG_HIDE_ETERNA_CITY_GARDENIA
    SetObjectEventPos LOCALID_GARDENIA, 312, 562
    SetObjectEventDir LOCALID_GARDENIA, DIR_SOUTH
    SetObjectEventMovementType LOCALID_GARDENIA, MOVEMENT_TYPE_LOOK_SOUTH
    AddObject LOCALID_GARDENIA
    PlayDoorCloseAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    UnloadAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement LOCALID_PLAYER, EternaCity_Arc2Movement_FaceNorth
    WaitMovement
    Message EternaCity_Text_Arc2GardeniaOffTheRecord
    WaitButton
    Message EternaCity_Text_Arc2GardeniaShelter
    WaitButton
    Message EternaCity_Text_Arc2GardeniaSomethingsWrong
    WaitButton
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 33
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_GARDENIA
    Warp MAP_HEADER_ETERNA_CITY, 305, 522, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

// 33, after the warp to the Haven trees (frame trigger on VAR_MAP_LOCAL_0x02, which OnTransition sets at 33).
// Runs only when the map loaded with the player at the trees spot, i.e. right after the walk.
EternaCity_Arc2HavenArrival:
    SetVar VAR_MAP_LOCAL_0x02, 0
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8004, 305, EternaCity_Arc2HavenArrivalEnd
    GoToIfNe VAR_0x8005, 522, EternaCity_Arc2HavenArrivalEnd
    LockAll
    ApplyMovement LOCALID_CYRUS, EternaCity_Arc2Movement_FaceWest
    WaitMovement
    Message EternaCity_Text_Arc2CyrusWaitHere
    WaitButton
    CloseMessage
    ReleaseAll
EternaCity_Arc2HavenArrivalEnd:
    End

    .balign 4, 0
EternaCity_Arc2Movement_GariusWalkUp:
    WalkNormalWest 2
    EndMovement

    .balign 4, 0
EternaCity_Arc2Movement_GariusLeave:
    WalkNormalSouth
    WalkNormalWest 6
    WalkNormalNorth 8
    EndMovement

    .balign 4, 0
EternaCity_Arc2Movement_FaceEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
EternaCity_Arc2Movement_FaceNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
EternaCity_Arc2Movement_FaceWest:
    WalkOnSpotNormalWest
    EndMovement

// City-entry cinematic (lane cine): on the first entry per save, a short
// pull-back and slow return while player input waits (LockAll). No-ops
// when OverworldCinematics is off.
EternaCity_CineCityEntry:
    SetVar VAR_CINE_CITY_PENDING, 0
    GoToIfSet FLAG_CINE_VISITED_ETERNA, EternaCity_CineCityEntryDone
    SetFlag FLAG_CINE_VISITED_ETERNA
    LockAll
    CineCamTo 0, 0, 1000, 42, 0, 13, 80, 1
    CineWaitCamera
    CineCamReturn 70, 1
    CineWaitCamera
    ReleaseAll
EternaCity_CineCityEntryDone:
    End
