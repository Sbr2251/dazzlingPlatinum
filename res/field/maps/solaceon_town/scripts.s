#include "macros/scrcmd.inc"
#include "res/text/bank/solaceon_town.h"
#include "res/field/maps/locals/solaceon_town.h"


    ScriptEntry SolaceonTown_Rancher1
    ScriptEntry SolaceonTown_Cowgirl1
    ScriptEntry SolaceonTown_Twin
    ScriptEntry SolaceonTown_Cowgirl2
    ScriptEntry SolaceonTown_Rancher2
    ScriptEntry SolaceonTown_RuinManiac
    ScriptEntry SolaceonTown_MapSignpost
    ScriptEntry SolaceonTown_SignboardPokemonDayCare
    ScriptEntry SolaceonTown_SignboardPokemonNewsPress
    ScriptEntry SolaceonTown_OnTransition
    ScriptEntry SolaceonTown_OnResume
    ScriptEntry SolaceonTown_CoordEvent_Rival
    ScriptEntry SolaceonTown_Arc2WallPhotos
    ScriptEntry SolaceonTown_Arc2WallPonyta
    ScriptEntry SolaceonTown_Arc2WallElias
    ScriptEntry SolaceonTown_Arc2WallBanner
    ScriptEntry SolaceonTown_Arc2WallTeo
    ScriptEntry SolaceonTown_Arc2IndraCutaway
    ScriptEntry SolaceonTown_QuestsRowanBanner
    ScriptEntry SolaceonTown_CineCityEntry
    ScriptEntryEnd

// Arc 2 (s-celestic), 2.16a: the memorial wall (P1: sign events on the fence west of the main road,
// x 556, z 652-656, read from the road facing west; the wall art is P2) and the Indra cutaway.
// The cutaway plays the first time the player comes down the road from Route 210 at state 44 (coord row at
// the town's north edge): 47 at the start, 49 at the end. Map-local hide flag: FLAG_MAP_LOCAL_HIDE_OBSTACLE_16 = Indra.
// The stock Barry run-in at the south exit (VAR_SOLACEON_TOWN_STATE) is switched off from Arc 2 on.
#define LOCALID_ARC2_INDRA 21
// Arc 2 quests (R3, S10): from VAR_ARC2_PROGRESS 47 two Eclipse banners quote Rowan, at the north road (557,642)
// and the south road (557,666). Map-local hide flag: FLAG_MAP_LOCAL_HIDE_OBSTACLE_17 = both banners.

SolaceonTown_OnResume:
    End

SolaceonTown_OnTransition:
    SetVar VAR_CINE_CITY_PENDING, 1
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    Call SolaceonTown_QuestsOnTransition
    CallIfGe VAR_ARC2_PROGRESS, 1, SolaceonTown_Arc2NoBarry
    CheckDaycareHasEgg VAR_MAP_LOCAL_0x00
    GoToIfNe VAR_MAP_LOCAL_0x00, FALSE, SolaceonTown_SetDayCareManDirEast
    End

SolaceonTown_SetDayCareManDirEast:
    SetObjectEventDir LOCALID_DAY_CARE_MAN, DIR_EAST
    End

SolaceonTown_Arc2NoBarry:
    SetVar VAR_SOLACEON_TOWN_STATE, 1
    Return

SolaceonTown_Arc2WallPhotos:
    GoToIfLt VAR_ARC2_PROGRESS, 44, SolaceonTown_Arc2WallEnd
    LockAll
    Message SolaceonTown_Text_Arc2WallPhotos
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_Arc2WallPonyta:
    GoToIfLt VAR_ARC2_PROGRESS, 44, SolaceonTown_Arc2WallEnd
    LockAll
    Message SolaceonTown_Text_Arc2WallPonyta
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_Arc2WallElias:
    GoToIfLt VAR_ARC2_PROGRESS, 44, SolaceonTown_Arc2WallEnd
    LockAll
    Message SolaceonTown_Text_Arc2WallElias
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_Arc2WallBanner:
    GoToIfLt VAR_ARC2_PROGRESS, 44, SolaceonTown_Arc2WallEnd
    LockAll
    Message SolaceonTown_Text_Arc2WallBanner
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_Arc2WallTeo:
    GoToIfLt VAR_ARC2_PROGRESS, 49, SolaceonTown_Arc2WallEnd
    LockAll
    Message SolaceonTown_Text_Arc2WallTeo
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_Arc2WallClose:
    WaitABPadPress
    CloseMessage
    ReleaseAll
SolaceonTown_Arc2WallEnd:
    End

// 2.16a: shown to the player only. The player is put at the wall and hidden; Indra pins up Teo's card.
SolaceonTown_Arc2IndraCutaway:
    LockAll
    SetVar VAR_ARC2_PROGRESS, 47
    FadeScreenOut
    WaitFadeScreen
    SetPosition LOCALID_PLAYER, 558, 0, 654, DIR_WEST
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Arc2Movement_Hide
    WaitMovement
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    AddObject LOCALID_ARC2_INDRA
    LockObject LOCALID_ARC2_INDRA
    WaitTime 15, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_ARC2_INDRA, SolaceonTown_Arc2Movement_PinCard
    WaitMovement
    PlaySE SEQ_SE_DP_KON_sseq
    WaitTime 20, VAR_RESULT
    Message SolaceonTown_Text_Arc2IndraAnotherName
    Message SolaceonTown_Text_Arc2IndraSomebodyHasTo
    Message SolaceonTown_Text_Arc2IndraMorningDoor
    Message SolaceonTown_Text_Arc2IndraHandsShake
    Message SolaceonTown_Text_Arc2IndraKeepTheDoor
    CloseMessage
    ApplyMovement LOCALID_ARC2_INDRA, SolaceonTown_Arc2Movement_IndraLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_INDRA
    WaitTime 20, VAR_RESULT
    FadeScreenOut
    WaitFadeScreen
    SetPosition LOCALID_PLAYER, 557, 0, 654, DIR_WEST
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Arc2Movement_Show
    WaitMovement
    FadeScreenIn
    WaitFadeScreen
    SetVar VAR_ARC2_PROGRESS, 49
    Message SolaceonTown_Text_Arc2WallTeo
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
SolaceonTown_Arc2Movement_Hide:
    SetInvisible
    EndMovement

    .balign 4, 0
SolaceonTown_Arc2Movement_Show:
    SetVisible
    FaceWest
    EndMovement

    .balign 4, 0
SolaceonTown_Arc2Movement_PinCard:
    FaceWest
    Delay8
    WalkOnSpotSlowWest
    EndMovement

    .balign 4, 0
SolaceonTown_Arc2Movement_IndraLeave:
    Delay8 2
    WalkNormalSouth 2
    WalkNormalEast 3
    WalkNormalSouth 4
    EndMovement

SolaceonTown_Rancher1:
    NPCMessage SolaceonTown_Text_BreathingInRefreshingAir
    End

SolaceonTown_Cowgirl1:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfBadgeAcquired BADGE_ID_RELIC, SolaceonTown_TakeATour
    Message SolaceonTown_Text_TakeItEasy
    WaitButton
    CloseMessage
    ReleaseAll
    End

SolaceonTown_TakeATour:
    Message SolaceonTown_Text_TakeATour
    WaitButton
    CloseMessage
    ReleaseAll
    End

SolaceonTown_Twin:
    NPCMessage SolaceonTown_Text_ImTooLittle
    End

SolaceonTown_Cowgirl2:
    NPCMessage SolaceonTown_Text_IVisitTheLostTower
    End

SolaceonTown_Rancher2:
    NPCMessage SolaceonTown_Text_UsedToBeNothing
    End

SolaceonTown_RuinManiac:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    CheckPoketchAppRegistered POKETCH_APPID_POKEMONHISTORY, VAR_RESULT
    GoToIfEq VAR_RESULT, TRUE, SolaceonTown_EachPokemonOwnHistory
    GetLocalDexSeenCount VAR_RESULT
    GoToIfLt VAR_RESULT, 50, SolaceonTown_IfCompetentMetFiftyPokemon
    Message SolaceonTown_Text_PoketchAppPokemonHistory
    SetVar VAR_0x8004, POKETCH_APPID_POKEMONHISTORY
    CallCommonScript CommonScript_ObtainPoketchApp
    WaitButton
    CloseMessage
    ReleaseAll
    End

SolaceonTown_IfCompetentMetFiftyPokemon:
    Message SolaceonTown_Text_IfCompetentMetFiftyPokemon
    WaitButton
    CloseMessage
    ReleaseAll
    End

SolaceonTown_EachPokemonOwnHistory:
    Message SolaceonTown_Text_EachPokemonOwnHistory
    WaitButton
    CloseMessage
    ReleaseAll
    End

SolaceonTown_MapSignpost:
    ShowMapSign SolaceonTown_Text_MapSign
    End

SolaceonTown_SignboardPokemonDayCare:
    ShowLandmarkSign SolaceonTown_Text_SignPokemonDayCare
    End

SolaceonTown_SignboardPokemonNewsPress:
    ShowLandmarkSign SolaceonTown_Text_SignPokemonNewsPress
    End

SolaceonTown_CoordEvent_Rival:
    LockAll
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Movement_PlayerNoticeRival
    WaitMovement
    CallCommonScript CommonScript_SetRivalBGM
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    SetObjectEventPos LOCALID_RIVAL, VAR_0x8004, 661
    ClearFlag FLAG_HIDE_SOLACEON_TOWN_RIVAL
    AddObject LOCALID_RIVAL
    LockObject LOCALID_RIVAL
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Movement_PlayerFaceNorth
    ApplyMovement LOCALID_RIVAL, SolaceonTown_Movement_RivalWalkSouth
    WaitMovement
    Message SolaceonTown_Text_Yahoo
    CloseMessage
    ApplyMovement LOCALID_RIVAL, SolaceonTown_Movement_RivalLookAround
    WaitMovement
    BufferRivalName 0
    BufferPlayerName 1
    Message SolaceonTown_Text_IGotSomethingCool
    ApplyMovement LOCALID_RIVAL, SolaceonTown_Movement_RivalExclamationMark
    WaitMovement
    Message SolaceonTown_Text_CheckOutTheRuins
    CloseMessage
    ApplyMovement LOCALID_RIVAL, SolaceonTown_Movement_RivalLeave
    WaitMovement
    RemoveObject LOCALID_RIVAL
    CallCommonScript CommonScript_FadeToDefaultMusic_2
    SetVar VAR_SOLACEON_TOWN_STATE, 1
    ReleaseAll
    End

    .balign 4, 0
SolaceonTown_Movement_RivalWalkSouth:
    WalkFastSouth 7
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_RivalLookAround:
    WalkOnSpotFastWest
    Delay8
    WalkOnSpotFastEast
    Delay8
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_RivalExclamationMark:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_RivalLeave:
    WalkFastNorth 7
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_PlayerNoticeRival:
    Delay8
    EmoteExclamationMark
    Delay8 3
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_PlayerFaceNorth:
    FaceNorth
    EndMovement

SolaceonTown_QuestsOnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    GoToIfLt VAR_ARC2_PROGRESS, 47, SolaceonTown_QuestsReturn
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
SolaceonTown_QuestsReturn:
    Return

SolaceonTown_QuestsRowanBanner:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message SolaceonTown_Text_QuestsRowanBanner
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

// City-entry cinematic (lane cine): on the first entry per save, a short
// pull-back and slow return while player input waits (LockAll). No-ops
// when OverworldCinematics is off.
SolaceonTown_CineCityEntry:
    SetVar VAR_CINE_CITY_PENDING, 0
    GoToIfSet FLAG_CINE_VISITED_SOLACEON, SolaceonTown_CineCityEntryDone
    SetFlag FLAG_CINE_VISITED_SOLACEON
    LockAll
    CineCamTo 0, 0, 1000, 42, 0, 13, 80, 1
    CineWaitCamera
    CineCamReturn 70, 1
    CineWaitCamera
    ReleaseAll
SolaceonTown_CineCityEntryDone:
    End
