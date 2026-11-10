#include "macros/scrcmd.inc"
#include "res/text/bank/jubilife_city.h"
#include "res/text/bank/menu_entries.h"
#include "res/field/maps/locals/jubilife_city.h"


#define FLAG_QUESTS_DUCHESS_CARRIED FLAG_ARC2_LEAD_B
#define FLAG_QUESTS_DUCHESS_HOME    FLAG_ARC2_LEAD_C
#define FLAG_QUESTS_MOON_STONE      FLAG_ARC2_LEAD_D

    ScriptEntry JubilifeCity_OnTransition
    ScriptEntry JubilifeCity_CoordEvent_FirstArrival
    ScriptEntry JubilifeCity_CoordEvent_LookerBlockRoute203
    ScriptEntry JubilifeCity_CoordEvent_TeamGalactic
    ScriptEntry JubilifeCity_Looker
    ScriptEntry JubilifeCity_SchoolKidM1
    ScriptEntry JubilifeCity_Twin
    ScriptEntry JubilifeCity_AceTrainerF
    ScriptEntry JubilifeCity_SchoolKidM2
    ScriptEntry JubilifeCity_AceTrainerM1
    ScriptEntry JubilifeCity_ExpertM1
    ScriptEntry JubilifeCity_ExpertM2
    ScriptEntry JubilifeCity_AceTrainerM3
    ScriptEntry JubilifeCity_Clown1
    ScriptEntry JubilifeCity_Clown2
    ScriptEntry JubilifeCity_Clown3
    ScriptEntry JubilifeCity_CoordEvent_PoketchCampaign
    ScriptEntry JubilifeCity_PoketchCoPresident
    ScriptEntry JubilifeCity_CoordEvent_GTSGreeterBlockPlayer
    ScriptEntry JubilifeCity_KidWithNDS1
    ScriptEntry JubilifeCity_KidWithNDS2
    ScriptEntry JubilifeCity_MapSignpost
    ScriptEntry JubilifeCity_SignboardJubilifeCondominiums
    ScriptEntry JubilifeCity_SignboardPoketchCompany
    ScriptEntry JubilifeCity_SignboardTrainersSchool
    ScriptEntry JubilifeCity_SignboardJubilifeTV
    ScriptEntry JubilifeCity_SignboardGlobalTerminal
    ScriptEntry JubilifeCity_CoordEvent_LookerPalPad
    ScriptEntry JubilifeCity_Arc1Garius
    ScriptEntry JubilifeCity_Arc1TriggerRally
    ScriptEntry JubilifeCity_Arc1TriggerEastExit
    ScriptEntry JubilifeCity_Arc1TriggerToBeContinued
    ScriptEntry JubilifeCity_Arc1EclipseGruntFlyer
    ScriptEntry JubilifeCity_Arc1EclipseGruntF
    ScriptEntry JubilifeCity_Arc1Cyrus
    ScriptEntry JubilifeCity_Arc1CrowdNeverCameHome
    ScriptEntry JubilifeCity_Arc1CrowdGrandpasPokemon
    ScriptEntry JubilifeCity_Arc1CrowdOneMoreDay
    ScriptEntry JubilifeCity_Arc1CrowdBestFriend
    ScriptEntry JubilifeCity_Arc1CrowdGransDoor
    ScriptEntry JubilifeCity_Arc1CrowdMomAskedMe
    ScriptEntry JubilifeCity_Arc1CrateLooker
    ScriptEntry JubilifeCity_Arc1CrateGrunt
    ScriptEntry JubilifeCity_Arc1CrateBox
    ScriptEntry JubilifeCity_Arc1CrateReceiver
    ScriptEntry JubilifeCity_Arc1CrateTriggerPsst
    ScriptEntry JubilifeCity_Arc1CrateTriggerStep
    ScriptEntry JubilifeCity_Arc2FindCyrus
    ScriptEntry JubilifeCity_Arc2OutsideSchool
    ScriptEntry JubilifeCity_Arc2Cast
    ScriptEntry JubilifeCity_QuestsOldMan
    ScriptEntry JubilifeCity_QuestsDuchess
    ScriptEntryEnd

JubilifeCity_OnTransition:
    // Dazzling Platinum Arc 1: object LOCALID_ARC1_SAROS is never shown (Saros is only a voice on the TV,
    // playtest bug 11). Its events slot is kept so the crowd's local IDs (and saves made in Jubilife) don't
    // shift, and its hide flag is set at every load because a new game starts with it clear. The rally cast and
    // crowd follow VAR_ARC1_PROGRESS. From 12 on, the stock state 0/1 chain is skipped before the stock checks.
    SetFlag FLAG_HIDE_ARC1_JUBILIFE_SAROS
    Call JubilifeCity_Arc1CrateOnTransition
    CallIfLt VAR_ARC1_PROGRESS, 12, JubilifeCity_Arc1HideRally
    CallIfGe VAR_ARC1_PROGRESS, 12, JubilifeCity_Arc1OnTransition
    Call JubilifeCity_Arc2OnTransition
    Call JubilifeCity_QuestsOnTransition
    CallIfEq VAR_JUBILIFE_CITY_STATE, 0, JubilifeCity_SetLookerPositionFirstArrival
    CallIfGe VAR_JUBILIFE_CITY_STATE, 3, JubilifeCity_SetCounterpartPositionTeamGalactic
    GetPlayerGender VAR_MAP_LOCAL_0x00
    GoToIfEq VAR_MAP_LOCAL_0x00, GENDER_MALE, JubilifeCity_SetCounterpartGraphicsDawn
    GoToIfEq VAR_MAP_LOCAL_0x00, GENDER_FEMALE, JubilifeCity_SetCounterpartGraphicsLucas
    End

JubilifeCity_SetLookerPositionFirstArrival:
    SetObjectEventPos LOCALID_LOOKER, 177, 774
    SetObjectEventDir LOCALID_LOOKER, DIR_SOUTH
    SetObjectEventMovementType LOCALID_LOOKER, MOVEMENT_TYPE_LOOK_SOUTH
    Return

JubilifeCity_SetCounterpartPositionTeamGalactic:
    SetObjectEventPos LOCALID_COUNTERPART, 176, 739
    SetObjectEventDir LOCALID_COUNTERPART, DIR_WEST
    SetObjectEventMovementType LOCALID_COUNTERPART, MOVEMENT_TYPE_LOOK_WEST
    Return

JubilifeCity_SetCounterpartGraphicsDawn:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    End

JubilifeCity_SetCounterpartGraphicsLucas:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    End

JubilifeCity_CoordEvent_FirstArrival:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8004, 173, JubilifeCity_FirstArrivalX173
    GoToIfEq VAR_0x8004, 174, JubilifeCity_FirstArrivalX174
    GoToIfEq VAR_0x8004, 175, JubilifeCity_FirstArrivalX175
    End

JubilifeCity_FirstArrivalX173:
    SetObjectEventPos LOCALID_COUNTERPART, 173, 788
    GoTo JubilifeCity_CounterpartWalkToPlayerFirstArrival
    End

JubilifeCity_FirstArrivalX174:
    SetObjectEventPos LOCALID_COUNTERPART, 174, 788
    GoTo JubilifeCity_CounterpartWalkToPlayerFirstArrival
    End

JubilifeCity_FirstArrivalX175:
    SetObjectEventPos LOCALID_COUNTERPART, 175, 788
    GoTo JubilifeCity_CounterpartWalkToPlayerFirstArrival
    End

JubilifeCity_CounterpartWalkToPlayerFirstArrival:
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_COUNTERPART
    AddObject LOCALID_COUNTERPART
    LockObject LOCALID_COUNTERPART
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartNoticePlayer
    WaitMovement
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartWalkToPlayerFirstArrival
    WaitMovement
    CallCommonScript CommonScript_SetCounterpartBGM
    GetPlayerGender VAR_RESULT
    GoToIfEq VAR_RESULT, GENDER_MALE, JubilifeCity_MeetLookerWithDawn
    GoToIfEq VAR_RESULT, GENDER_FEMALE, JubilifeCity_MeetLookerWithLucas
    End

JubilifeCity_MeetLookerWithDawn:
    BufferCounterpartName 0
    BufferPlayerName 1
    Message JubilifeCity_Text_DawnAreYouCatchingPokemon
    GetPartyCount VAR_RESULT
    BufferNumber 0, VAR_RESULT
    CallIfGe VAR_RESULT, 4, JubilifeCity_DawnAtLeastFourPokemon
    CallIfLe VAR_RESULT, 3, JubilifeCity_DawnLessThanFourPokemon
    BufferPlayerName 0
    BufferRivalName 1
    Message JubilifeCity_Text_DawnFollowMe
    Call JubilifeCity_PlayerAndCounterpartWalkNorth
    Message JubilifeCity_Text_DawnWhatIsHeDoing
    CloseMessage
    Call JubilifeCity_LookerWalkAround
    Message JubilifeCity_Text_DawnUm
    Call JubilifeCity_LookerNoticePlayerAndCounterpart
    Message JubilifeCity_Text_DawnJustMakingConversation
    Call JubilifeCity_IsSayingFamiliarToYou
    Call JubilifeCity_LookerGiveVSRecorderAndLeave
    Message JubilifeCity_Text_DawnInternationPoliceMustBeHard
    CloseMessage
    WaitTime 30, VAR_RESULT
    BufferPlayerName 0
    Call JubilifeCity_CounterpartWalkToTrainersSchool
    Message JubilifeCity_Text_DawnHereIsTheTrainersSchool
    CloseMessage
    BufferRivalName 1
    Call JubilifeCity_CounterpartWalkBackFromTrainersSchool
    Message JubilifeCity_Text_DawnRivalWentInEarlier
    CloseMessage
    GoTo JubilifeCity_CounterpartLeave
    End

JubilifeCity_DawnAtLeastFourPokemon:
    Message JubilifeCity_Text_DawnWowAlreadyGotXPokemon
    Return

JubilifeCity_DawnLessThanFourPokemon:
    Message JubilifeCity_Text_DawnSaferIfYouCatchMore
    Return

JubilifeCity_MeetLookerWithLucas:
    BufferCounterpartName 0
    BufferPlayerName 1
    Message JubilifeCity_Text_LucasHowManyPokemon
    GetPartyCount VAR_RESULT
    BufferNumber 0, VAR_RESULT
    CallIfGe VAR_RESULT, 4, JubilifeCity_LucasAtLeastFourPokemon
    CallIfLe VAR_RESULT, 3, JubilifeCity_LucasLessThanFourPokemon
    BufferPlayerName 0
    BufferRivalName 1
    Message JubilifeCity_Text_LucasFollowMe
    Call JubilifeCity_PlayerAndCounterpartWalkNorth
    Message JubilifeCity_Text_LucasWhatsHeDoing
    CloseMessage
    Call JubilifeCity_LookerWalkAround
    Message JubilifeCity_Text_LucasUhExcuse
    Call JubilifeCity_LookerNoticePlayerAndCounterpart
    Message JubilifeCity_Text_LucasJustMakingSmallTalk
    Call JubilifeCity_IsSayingFamiliarToYou
    Call JubilifeCity_LookerGiveVSRecorderAndLeave
    Message JubilifeCity_Text_LucasInternationPoliceSoundsHard
    CloseMessage
    WaitTime 15, VAR_RESULT
    BufferPlayerName 0
    Call JubilifeCity_CounterpartWalkToTrainersSchool
    Message JubilifeCity_Text_LucasThisIsTheTrainersSchool
    CloseMessage
    BufferRivalName 1
    Call JubilifeCity_CounterpartWalkBackFromTrainersSchool
    Message JubilifeCity_Text_LucasRivalWentInEarier
    CloseMessage
    GoTo JubilifeCity_CounterpartLeave
    End

JubilifeCity_LucasAtLeastFourPokemon:
    Message JubilifeCity_Text_LucasYouAlreadyHaveXPokemon
    Return

JubilifeCity_LucasLessThanFourPokemon:
    Message JubilifeCity_Text_LucasYouShouldCatchMore
    Return

JubilifeCity_CounterpartLeave:
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartLeaveFirstArrival
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWatchCounterpartLeave
    WaitMovement
    RemoveObject LOCALID_COUNTERPART
    SetVar VAR_JUBILIFE_CITY_STATE, 1
    ReleaseAll
    End

JubilifeCity_PlayerAndCounterpartWalkNorth:
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8004, 173, JubilifeCity_PlayerAndCounterpartWalkNorthX173
    GoToIfEq VAR_0x8004, 174, JubilifeCity_PlayerAndCounterpartWalkNorthX174
    GoToIfEq VAR_0x8004, 175, JubilifeCity_PlayerAndCounterpartWalkNorthX175
    End

JubilifeCity_PlayerAndCounterpartWalkNorthX173:
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartWalkNorthX173
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWalkNorthX173
    WaitMovement
    Return

JubilifeCity_PlayerAndCounterpartWalkNorthX174:
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartWalkNorthX174
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWalkNorthX174
    WaitMovement
    Return

JubilifeCity_PlayerAndCounterpartWalkNorthX175:
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartWalkNorthX175
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWalkNorthX175
    WaitMovement
    Return

JubilifeCity_LookerWalkAround:
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkAround
    WaitMovement
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkEast
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartWalkToLooker
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWalkToLooker
    WaitMovement
    Return

JubilifeCity_LookerNoticePlayerAndCounterpart:
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerNoticePlayerAndCounterpart
    WaitMovement
    CallCommonScript CommonScript_SetLookerBGM
    Message JubilifeCity_Text_WHAAAT
    Message JubilifeCity_Text_HowDidYouUnmaskMe
    CloseMessage
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartWalkOnSpotNorth
    WaitMovement
    Return

JubilifeCity_IsSayingFamiliarToYou:
    Message JubilifeCity_Text_IKnowBetter
    Message JubilifeCity_Text_IsSayingFamiliarToYou
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, JubilifeCity_TakingFromOthersIsWrong
    GoToIfEq VAR_RESULT, MENU_NO, JubilifeCity_YouClaimToNotKnowIt
    End

JubilifeCity_TakingFromOthersIsWrong:
    Message JubilifeCity_Text_TakingFromOthersIsWrong
    Return

JubilifeCity_YouClaimToNotKnowIt:
    Message JubilifeCity_Text_YouClaimToNotKnowIt
    Return

JubilifeCity_LookerGiveVSRecorderAndLeave:
    Message JubilifeCity_Text_PerhapsYouCanUseThis
    SetVar VAR_0x8004, ITEM_VS_RECORDER
    SetVar VAR_0x8005, 1
    CallCommonScript CommonScript_AddItemQuantity
    Message JubilifeCity_Text_DeviceForRecordingAMatch
    CloseMessage
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkWestEastSouth
    WaitMovement
    Message JubilifeCity_Text_InformMeOfAnyHappenings
    CloseMessage
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartWatchLookerLeave
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWatchLookerLeave
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerLeaveFistArrival
    WaitMovement
    SetPosition LOCALID_LOOKER, 186, 0, 756, DIR_SOUTH
    SetObjectEventPos LOCALID_LOOKER, 186, 756
    CallCommonScript CommonScript_FadeToDefaultMusic_4
    Return

JubilifeCity_CounterpartWalkToTrainersSchool:
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartWalkToTrainersSchool
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWatchCounterpartWalkToTrainersSchool
    WaitMovement
    Return

JubilifeCity_CounterpartWalkBackFromTrainersSchool:
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartWalkBackFromTrainersSchool
    WaitMovement
    Return

    .balign 4, 0
JubilifeCity_Movement_CounterpartNoticePlayer:
    WalkNormalSouth 4
    EmoteExclamationMark
    Delay16
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartWalkToPlayerFirstArrival:
    WalkNormalSouth 3
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartWalkNorthX173:
    WalkNormalEast
    WalkNormalNorth 18
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartWalkNorthX175:
    WalkNormalWest
    WalkNormalNorth 18
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartWalkNorthX174:
    WalkNormalNorth 18
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartLeaveFirstArrival:
    WalkNormalSouth 9
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartWalkToLooker:
    WalkNormalNorth 2
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartWalkToTrainersSchool:
    WalkNormalSouth
    WalkNormalWest 2
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartWalkBackFromTrainersSchool:
    WalkNormalNorth
    WalkNormalEast 2
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartWatchLookerLeave:
    WalkOnSpotNormalEast
    Delay8 4
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWalkNorthX173:
    WalkNormalNorth
    WalkNormalEast
    WalkNormalNorth 17
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWalkNorthX175:
    WalkNormalNorth
    WalkNormalWest
    WalkNormalNorth 17
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWalkNorthX174:
    WalkNormalNorth 18
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWalkToLooker:
    WalkNormalNorth 2
    WalkNormalEast
    WalkNormalNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWatchCounterpartWalkToTrainersSchool:
    Delay4
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWatchCounterpartLeave:
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWatchLookerLeave:
    Delay8
    WalkOnSpotNormalEast
    Delay8 3
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkAround:
    WalkOnSpotFastWest
    Delay8 2
    WalkOnSpotFastSouth
    Delay8
    WalkSlowWest
    WalkFastWest 5
    WalkOnSpotFastEast
    Delay8
    WalkOnSpotFastNorth
    Delay8
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkEast:
    WalkSlowEast
    WalkFastEast 2
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerNoticePlayerAndCounterpart:
    WalkOnSpotFastSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkWestEastSouth:
    WalkOnSpotFastWest
    Delay8
    WalkOnSpotFastEast
    Delay8 2
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerLeaveFistArrival:
    WalkFastEast 3
    WalkOnSpotFastWest
    Delay8
    WalkSlowNorth
    WalkFastNorth 7
    EndMovement

JubilifeCity_ExpertM2:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfBadgeAcquired BADGE_ID_COAL, JubilifeCity_HaveYouVisitedTVStation
    Message JubilifeCity_Text_CarvedOutOfAMountain
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_HaveYouVisitedTVStation:
    Message JubilifeCity_Text_HaveYouVisitedTVStation
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_AceTrainerM3:
    NPCMessage JubilifeCity_Text_PastHereIsGlobalTerminal
    End

JubilifeCity_CoordEvent_GTSGreeterBlockPlayer:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 779, JubilifeCity_GTSGreeterBlockPlayerZ779
    GoToIfEq VAR_0x8005, 780, JubilifeCity_GTSGreeterBlockPlayerZ780
    GoToIfEq VAR_0x8005, 781, JubilifeCity_GTSGreeterBlockPlayerZ781
    End

JubilifeCity_GTSGreeterBlockPlayerZ779:
    ApplyMovement LOCALID_ACE_TRAINER_M_3, JubilifeCity_Movement_GTSGreeterNoticePlayerZ779
    WaitMovement
    Message JubilifeCity_Text_OffLimitsIfNoGymBadge
    CloseMessage
    ApplyMovement LOCALID_ACE_TRAINER_M_3, JubilifeCity_Movement_GTSGreeterWalkBackZ779
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerStepBackEast
    WaitMovement
    GoTo JubilifeCity_GTSGreeterBlockPlayerRelease
    End

JubilifeCity_GTSGreeterBlockPlayerZ780:
    ApplyMovement LOCALID_ACE_TRAINER_M_3, JubilifeCity_Movement_GTSGreeterNoticePlayerZ780
    WaitMovement
    Message JubilifeCity_Text_OffLimitsIfNoGymBadge
    CloseMessage
    ApplyMovement LOCALID_ACE_TRAINER_M_3, JubilifeCity_Movement_GTSGreeterWalkBackZ780
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerStepBackEast
    WaitMovement
    GoTo JubilifeCity_GTSGreeterBlockPlayerRelease
    End

JubilifeCity_GTSGreeterBlockPlayerZ781:
    ApplyMovement LOCALID_ACE_TRAINER_M_3, JubilifeCity_Movement_GTSGreeterNoticePlayerZ781
    WaitMovement
    Message JubilifeCity_Text_OffLimitsIfNoGymBadge
    CloseMessage
    ApplyMovement LOCALID_ACE_TRAINER_M_3, JubilifeCity_Movement_GTSGreeterWalkBackZ781
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerStepBackEast
    WaitMovement
    GoTo JubilifeCity_GTSGreeterBlockPlayerRelease
    End

JubilifeCity_GTSGreeterBlockPlayerRelease:
    ReleaseAll
    End

    .balign 4, 0
JubilifeCity_Movement_GTSGreeterNoticePlayerZ779:
    EmoteExclamationMark
    WalkNormalSouth
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_GTSGreeterNoticePlayerZ780:
    EmoteExclamationMark
    WalkNormalSouth 2
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_GTSGreeterNoticePlayerZ781:
    EmoteExclamationMark
    WalkNormalSouth 3
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_GTSGreeterWalkBackZ779:
    WalkNormalEast
    Delay8 2
    WalkNormalWest
    WalkNormalNorth
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_GTSGreeterWalkBackZ780:
    WalkNormalEast
    Delay8 2
    WalkNormalWest
    WalkNormalNorth 2
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_GTSGreeterWalkBackZ781:
    WalkNormalEast
    Delay8 2
    WalkNormalWest
    WalkNormalNorth 3
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerStepBackEast:
    WalkNormalEast
    EndMovement

JubilifeCity_CoordEvent_LookerBlockRoute203:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 757, JubilifeCity_LookerWalkToPlayerZ757
    GoToIfEq VAR_0x8005, 758, JubilifeCity_LookerWalkToPlayerZ758
    GoToIfEq VAR_0x8005, 759, JubilifeCity_LookerWalkToPlayerZ759
    GoToIfEq VAR_0x8005, 760, JubilifeCity_LookerWalkToPlayerZ760
    End

JubilifeCity_LookerWalkToPlayerZ757:
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWalkOnSpotWest
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkToPlayerZ757
    WaitMovement
    GoTo JubilifeCity_LookerBlockPlayer
    End

JubilifeCity_LookerWalkToPlayerZ758:
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWalkOnSpotWest
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkToPlayerZ758
    WaitMovement
    GoTo JubilifeCity_LookerBlockPlayer
    End

JubilifeCity_LookerWalkToPlayerZ759:
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWalkOnSpotWest
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkToPlayerZ759
    WaitMovement
    GoTo JubilifeCity_LookerBlockPlayer
    End

JubilifeCity_LookerWalkToPlayerZ760:
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWalkOnSpotWest
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkToPlayerZ760
    WaitMovement
    GoTo JubilifeCity_LookerBlockPlayer
    End

JubilifeCity_LookerBlockPlayer:
    Call JubilifeCity_LookerBlockPlayerMessage
    CloseMessage
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWalkWestWithLooker
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkWestWithPlayer
    WaitMovement
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 757, JubilifeCity_LookerWalkBackZ757
    GoToIfEq VAR_0x8005, 758, JubilifeCity_LookerWalkBackZ758
    GoToIfEq VAR_0x8005, 759, JubilifeCity_LookerWalkBackZ759
    GoToIfEq VAR_0x8005, 760, JubilifeCity_LookerWalkBackZ760
    End

JubilifeCity_LookerBlockPlayerMessage:
    GoToIfUnset FLAG_TALKED_TO_TRAINERS_SCHOOL_RIVAL, JubilifeCity_HelloHaveYouVisitedTrainersSchool
    GoToIfUnset FLAG_RECEIVED_POKETCH, JubilifeCity_TellMeHaveYouNotObtainedAPoketch
    Message JubilifeCity_Text_HaveYouNotObtainedAGymBadge
    Return

JubilifeCity_HelloHaveYouVisitedTrainersSchool:
    Message JubilifeCity_Text_HelloHaveYouVisitedTrainersSchool
    Return

JubilifeCity_TellMeHaveYouNotObtainedAPoketch:
    Message JubilifeCity_Text_TellMeHaveYouNotObtainedAPoketch
    Return

JubilifeCity_LookerMessageDidntObtainPoketch:
    GoToIfUnset FLAG_TALKED_TO_TRAINERS_SCHOOL_RIVAL, JubilifeCity_ItIsYouHaveYouVisitedTrainersSchool
    GoToIfUnset FLAG_RECEIVED_POKETCH, JubilifeCity_ItIsYouHaveYouNotObtainedAPoketch
    Message JubilifeCity_Text_HaveYouNotObtainedAGymBadge
    Return

JubilifeCity_ItIsYouHaveYouVisitedTrainersSchool:
    Message JubilifeCity_Text_ItIsYouHaveYouVisitedTrainersSchool
    Return

JubilifeCity_ItIsYouHaveYouNotObtainedAPoketch:
    Message JubilifeCity_Text_ItIsYouHaveYouNotObtainedAPoketch
    Return

JubilifeCity_LookerWalkBackZ757:
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkBackZ757
    WaitMovement
    GoTo JubilifeCity_LookerEnd
    End

JubilifeCity_LookerWalkBackZ758:
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkBackZ758
    WaitMovement
    GoTo JubilifeCity_LookerEnd
    End

JubilifeCity_LookerWalkBackZ759:
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkBackZ759
    WaitMovement
    GoTo JubilifeCity_LookerEnd
    End

JubilifeCity_LookerWalkBackZ760:
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkBackZ760
    WaitMovement
    GoTo JubilifeCity_LookerEnd
    End

JubilifeCity_LookerEnd:
    ReleaseAll
    End

    .balign 4, 0
JubilifeCity_Movement_PlayerWalkOnSpotWest:
    Delay8 5
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerFaceWest:
    Delay8 5
    FaceWest
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWalkWestWithLooker:
    WalkNormalWest
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkToPlayerZ757:
    FaceSouth
    EmoteExclamationMark
    Delay16
    WalkNormalSouth
    WalkNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkToPlayerZ758:
    FaceSouth
    EmoteExclamationMark
    Delay16
    WalkNormalSouth 2
    WalkNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkToPlayerZ759:
    FaceSouth
    EmoteExclamationMark
    Delay16
    WalkNormalSouth 3
    WalkNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkToPlayerZ760:
    FaceSouth
    EmoteExclamationMark
    Delay16
    WalkNormalSouth 4
    WalkNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkWestWithPlayer:
    LockDir
    WalkNormalWest
    UnlockDir
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkBackZ757:
    WalkNormalNorth
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkBackZ758:
    WalkNormalNorth 2
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkBackZ759:
    WalkNormalNorth 3
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkBackZ760:
    WalkNormalNorth 4
    WalkOnSpotNormalSouth
    EndMovement

JubilifeCity_Looker:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfInRange VAR_ARC1_PROGRESS, 12, 13, JubilifeCity_Arc1TrenchCoat
    GoToIfSet FLAG_RECEIVED_POKETCH, JubilifeCity_HaveYouNotObtainedAGymBadge
    Call JubilifeCity_LookerMessageDidntObtainPoketch
    WaitABPress
    CloseMessage
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerFaceSouth
    WaitMovement
    ReleaseAll
    End

JubilifeCity_HaveYouNotObtainedAGymBadge:
    Message JubilifeCity_Text_HaveYouNotObtainedAGymBadge
    WaitABPress
    CloseMessage
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerFaceSouth
    WaitMovement
    ReleaseAll
    End

JubilifeCity_CheckPalPad:
    CheckItem ITEM_PAL_PAD, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, TRUE, JubilifeCity_YouObtainedPalPad
    Message JubilifeCity_Text_HaveYouNotObtainedAPalPad
    CloseMessage
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkOnSpotWestEast
    WaitMovement
    Message JubilifeCity_Text_TakeInvestigationElsewhere
    Return

JubilifeCity_YouObtainedPalPad:
    Message JubilifeCity_Text_YouObtainedPalPad
    CloseMessage
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkOnSpotWestEast
    WaitMovement
    Message JubilifeCity_Text_TakeInvestigationElsewhere
    Return

    .balign 4, 0
JubilifeCity_Movement_LookerFaceSouth:
    FaceSouth
    EndMovement

JubilifeCity_CoordEvent_TeamGalactic:
    LockAll
    ApplyMovement LOCALID_GRUNT_M_2, JubilifeCity_Movement_GruntWalkOnSpotEast
    WaitMovement
    Message JubilifeCity_Text_HandOverResearchFindings
    CloseMessage
    GetPlayerMapPos VAR_0x8000, VAR_0x8001
    GoToIfEq VAR_0x8000, 173, JubilifeCity_PlayerWalkToProfRowanX173
    GoToIfEq VAR_0x8000, 174, JubilifeCity_PlayerWalkToProfRowanX174
    GoToIfEq VAR_0x8000, 175, JubilifeCity_PlayerWalkToProfRowanX175
    End

JubilifeCity_PlayerWalkToProfRowanX173:
    ApplyMovement LOCALID_PROF_ROWAN, JubilifeCity_Movement_ProfRowanNoticePlayer
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWalkToProfRowanX173
    WaitMovement
    GoTo JubilifeCity_TeamGalacticBanter
    End

JubilifeCity_PlayerWalkToProfRowanX174:
    ApplyMovement LOCALID_PROF_ROWAN, JubilifeCity_Movement_ProfRowanNoticePlayer
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWalkToProfRowanX174
    WaitMovement
    GoTo JubilifeCity_TeamGalacticBanter
    End

JubilifeCity_PlayerWalkToProfRowanX175:
    ApplyMovement LOCALID_PROF_ROWAN, JubilifeCity_Movement_ProfRowanNoticePlayer
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWalkToProfRowanX175
    WaitMovement
    GoTo JubilifeCity_TeamGalacticBanter
    End

JubilifeCity_TeamGalacticBanter:
    BufferPlayerName 0
    BufferCounterpartName 1
    Message JubilifeCity_Text_ThatsOreburghsGymBadge
    ApplyMovement LOCALID_GRUNT_M_2, JubilifeCity_Movement_GruntWalkOnSpotEast
    WaitMovement
    Message JubilifeCity_Text_MustYouBeSoDifficult
    ApplyMovement LOCALID_PROF_ROWAN, JubilifeCity_Movement_ProfRowanWalkOnSpotWest
    WaitMovement
    Message JubilifeCity_Text_WhyMustYouBeSuchANuisance
    ApplyMovement LOCALID_PROF_ROWAN, JubilifeCity_Movement_ProfRowanWalkOnSpotSouth
    WaitMovement
    Message JubilifeCity_Text_YouCallYourselvesAdults
    ApplyMovement LOCALID_GRUNT_M_1, JubilifeCity_Movement_GruntWalkOnSpotFastEast
    ApplyMovement LOCALID_GRUNT_M_2, JubilifeCity_Movement_GruntWalkOnSpotFastEast
    WaitMovement
    Message JubilifeCity_Text_RegretInsultingTeamGalactic
    Message JubilifeCity_Text_GiveThugsALessonInCivility
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartWalkOnSpotSouth
    WaitMovement
    GetPlayerGender VAR_RESULT
    GoToIfEq VAR_RESULT, GENDER_MALE, JubilifeCity_DawnPlayerLetsBattleTogether
    GoToIfEq VAR_RESULT, GENDER_FEMALE, JubilifeCity_LucasPlayerJoinMeAndBattleTheseGuys
    End

JubilifeCity_DawnPlayerLetsBattleTogether:
    BufferCounterpartName 0
    BufferPlayerName 1
    Message JubilifeCity_Text_DawnPlayerLetsBattleTogether
    GoTo JubilifeCity_TeamGalacticBattle
    End

JubilifeCity_LucasPlayerJoinMeAndBattleTheseGuys:
    BufferCounterpartName 0
    BufferPlayerName 1
    Message JubilifeCity_Text_LucasPlayerJoinMeAndBattleTheseGuys
    GoTo JubilifeCity_TeamGalacticBattle
    End

JubilifeCity_TeamGalacticBattle:
    CloseMessage
    ApplyMovement LOCALID_PROF_ROWAN, JubilifeCity_Movement_ProfRowanWalkOnSpotWest2
    WaitMovement
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartWalkToGrunt
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWalkToGrunt
    WaitMovement
    Call JubilifeCity_SetPlayerCounterpartPartnerTeam
    StartTagBattle VAR_0x8004, TRAINER_GALACTIC_GRUNT_JUBILIFE_CITY_1, TRAINER_GALACTIC_GRUNT_JUBILIFE_CITY_2
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, JubilifeCity_BlackOut
    ApplyMovement LOCALID_GRUNT_M_2, JubilifeCity_Movement_GruntWalkOnSpotEast2
    WaitMovement
    Message JubilifeCity_Text_WeWillRetreatForNow
    CloseMessage
    ApplyMovement LOCALID_GRUNT_M_1, JubilifeCity_Movement_Grunt1Leave
    ApplyMovement LOCALID_GRUNT_M_2, JubilifeCity_Movement_Grunt2Leave
    WaitMovement
    RemoveObject LOCALID_GRUNT_M_1
    RemoveObject LOCALID_GRUNT_M_2
    SetFlag FLAG_HIDE_JUBILIFE_GALACTIC_GRUNTS
    ApplyMovement LOCALID_PROF_ROWAN, JubilifeCity_Movement_ProfRowanWalkOnSpotSouth2
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartWalkToPlayerAfterGalacticBattle
    WaitMovement
    BufferPlayerName 0
    Message JubilifeCity_Text_CalledThemselvesTeamGalactic
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartWalkOnSpotSouth2
    WaitMovement
    GetPlayerGender VAR_RESULT
    GoToIfEq VAR_RESULT, GENDER_MALE, JubilifeCity_DawnProfessorStudiesEvolutionOfPokemon
    GoToIfEq VAR_RESULT, GENDER_FEMALE, JubilifeCity_LucasProfessorStudiesEvolutionOfPokemon
    End

JubilifeCity_SetPlayerCounterpartPartnerTeam:
    GetPlayerGender VAR_RESULT
    GoToIfEq VAR_RESULT, GENDER_MALE, JubilifeCity_SetDawnPartnerTeam
    GoToIfEq VAR_RESULT, GENDER_FEMALE, JubilifeCity_SetLucasPartnerTeam
    End

JubilifeCity_SetDawnPartnerTeam:
    GetPlayerStarterSpecies VAR_RESULT
    SetVar VAR_0x8004, TRAINER_DAWN_JUBILIFE_CITY_CHIMCHAR
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, JubilifeCity_Return
    SetVar VAR_0x8004, TRAINER_DAWN_JUBILIFE_CITY_PIPLUP
    GoToIfEq VAR_RESULT, SPECIES_PIPLUP, JubilifeCity_Return
    SetVar VAR_0x8004, TRAINER_DAWN_JUBILIFE_CITY_TURTWIG
    Return

JubilifeCity_SetLucasPartnerTeam:
    GetPlayerStarterSpecies VAR_RESULT
    SetVar VAR_0x8004, TRAINER_LUCAS_JUBILIFE_CITY_CHIMCHAR
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, JubilifeCity_Return
    SetVar VAR_0x8004, TRAINER_LUCAS_JUBILIFE_CITY_PIPLUP
    GoToIfEq VAR_RESULT, SPECIES_PIPLUP, JubilifeCity_Return
    SetVar VAR_0x8004, TRAINER_LUCAS_JUBILIFE_CITY_TURTWIG
    Return

JubilifeCity_Return:
    Return

JubilifeCity_DawnProfessorStudiesEvolutionOfPokemon:
    BufferCounterpartName 0
    BufferPlayerName 1
    Message JubilifeCity_Text_DawnProfessorStudiesEvolutionOfPokemon
    GoTo JubilifeCity_CounterpartAndProfRowanLeave
    End

JubilifeCity_LucasProfessorStudiesEvolutionOfPokemon:
    BufferCounterpartName 0
    BufferPlayerName 1
    Message JubilifeCity_Text_LucasProfessorStudiesEvolutionOfPokemon
    GoTo JubilifeCity_CounterpartAndProfRowanLeave
    End

JubilifeCity_CounterpartAndProfRowanLeave:
    BufferPlayerName 0
    Message JubilifeCity_Text_CollectAllGymBadges
    CloseMessage
    ApplyMovement LOCALID_COUNTERPART, JubilifeCity_Movement_CounterpartLeaveAfterGalacticBattle
    ApplyMovement LOCALID_PROF_ROWAN, JubilifeCity_Movement_ProfRowanLeave
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWatchCounterpartAndProfRowanLeave
    WaitMovement
    GoTo JubilifeCity_CollectorJubilifeTV
    End

JubilifeCity_CollectorJubilifeTV:
    RemoveObject LOCALID_COUNTERPART
    RemoveObject LOCALID_PROF_ROWAN
    ClearFlag FLAG_HIDE_SANDGEM_TOWN_LAB_PROF_ROWAN
    SetVar VAR_JUBILIFE_CITY_STATE, 4
    SetVar VAR_JUBILIFE_LOOKER_PAL_PAD_STATE, 2
    SetVar VAR_OREBURGH_CITY_STATE, 3
    RemoveObject LOCALID_CLOWN_1
    RemoveObject LOCALID_CLOWN_2
    RemoveObject LOCALID_CLOWN_3
    SetObjectEventPos LOCALID_COLLECTOR, 174, 750
    SetObjectEventMovementType LOCALID_COLLECTOR, MOVEMENT_TYPE_LOOK_NORTH
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_COLLECTOR
    AddObject LOCALID_COLLECTOR
    LockObject LOCALID_COLLECTOR
    ApplyMovement LOCALID_COLLECTOR, JubilifeCity_Movement_CollectorWalkToPlayer
    WaitMovement
    Message JubilifeCity_Text_OhThatWasVeryGood
    Call JubilifeCity_GiveFashionCaseAndAccessories
    Message JubilifeCity_Text_DressUpYourPokemon
    CloseMessage
    WaitTime 15, VAR_RESULT
    ApplyMovement LOCALID_COLLECTOR, JubilifeCity_Movement_CollectorLeave
    WaitMovement
    RemoveObject LOCALID_COLLECTOR
    ReleaseAll
    End

JubilifeCity_GiveFashionCaseAndAccessories:
    SetVar VAR_0x8004, ITEM_FASHION_CASE
    SetVar VAR_0x8005, 1
    CallCommonScript CommonScript_AddItemQuantity
    SetFlag FLAG_RECEIVED_FASHION_CASE
    Call JubilifeCity_GiveRandomAccessoryFluff
    Call JubilifeCity_GiveRandomAccessoryFluff
    Call JubilifeCity_GiveRandomAccessoryFluff
    Call JubilifeCity_GiveRandomAccessoryFluff
    Call JubilifeCity_GiveRandomAccessoryFluff
    Call JubilifeCity_GiveRandomAccessoryFeatherOrMustache
    Call JubilifeCity_GiveRandomAccessoryFeatherOrMustache
    Call JubilifeCity_GiveRandomAccessoryFeatherOrMustache
    Call JubilifeCity_GiveRandomAccessoryFeatherOrMustache
    Call JubilifeCity_GiveRandomAccessoryFeatherOrMustache
    AddContestBackdrop 0
    SetVar VAR_MAP_LOCAL_0x01, 9999
    Call JubilifeCity_GiveRandomContestBackdrop
    Call JubilifeCity_GiveRandomContestBackdrop
    Return

JubilifeCity_GiveRandomAccessoryFluff:
    GetRandom VAR_RESULT, 6
    SetVar VAR_0x8004, ACCESSORY_WHITE_FLUFF
    AddVar VAR_0x8004, VAR_RESULT
    AddAccessory VAR_0x8004, 1
    Return

JubilifeCity_GiveRandomAccessoryFeatherOrMustache:
    GetRandom VAR_RESULT, 6
    SetVar VAR_0x8004, ACCESSORY_BLUE_FEATHER
    AddVar VAR_0x8004, VAR_RESULT
    AddAccessory VAR_0x8004, 1
    Return

JubilifeCity_GiveRandomContestBackdrop:
    GetRandom VAR_RESULT, 8
    GoToIfEq VAR_MAP_LOCAL_0x01, VAR_RESULT, JubilifeCity_GiveRandomContestBackdrop
    SetVar VAR_MAP_LOCAL_0x01, VAR_RESULT
    SetVar VAR_0x8004, 1
    AddVar VAR_0x8004, VAR_RESULT
    AddContestBackdrop VAR_0x8004
    Return

JubilifeCity_BlackOut:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
JubilifeCity_Movement_CollectorWalkToPlayer:
    WalkNormalNorth 8
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CollectorLeave:
    WalkNormalSouth 8
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWalkToProfRowanX173:
    Delay8 2
    WalkNormalNorth
    WalkNormalEast 2
    WalkNormalNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWalkToProfRowanX174:
    Delay8 2
    WalkNormalNorth
    WalkNormalEast
    WalkNormalNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWalkToProfRowanX175:
    Delay8 2
    WalkNormalNorth 2
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWatchCounterpartAndProfRowanLeave:
    Delay8
    WalkOnSpotNormalEast
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

JubilifeCity_Movement_Unused:
    Delay8
    WalkOnSpotNormalEast
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

JubilifeCity_Movement_Unused2:
    Delay8
    WalkOnSpotNormalWest
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartWalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartWalkToGrunt:
    WalkNormalWest
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartWalkToPlayerAfterGalacticBattle:
    WalkNormalWest
    WalkNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartWalkOnSpotSouth2:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_CounterpartLeaveAfterGalacticBattle:
    WalkNormalEast
    WalkNormalSouth 9
    EndMovement

JubilifeCity_Movement_Unused3:
    WalkNormalEast
    WalkNormalSouth 9
    EndMovement

JubilifeCity_Movement_Unused4:
    WalkNormalWest
    WalkOnSpotNormalEast
    WalkNormalEast
    WalkNormalSouth 9
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_GruntWalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_GruntWalkOnSpotFastEast:
    WalkOnSpotFastEast 2
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_Grunt1Leave:
    WalkFastNorth 9
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_Grunt2Leave:
    WalkFastNorth 10
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_GruntWalkOnSpotEast2:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_ProfRowanNoticePlayer:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_ProfRowanWalkOnSpotWest:
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_ProfRowanWalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_ProfRowanLeave:
    WalkNormalSouth 9
    EndMovement

JubilifeCity_Movement_Unused5:
    WalkNormalSouth 9
    EndMovement

JubilifeCity_Movement_Unused6:
    WalkOnSpotNormalWest
    WalkNormalWest
    WalkNormalSouth 9
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_ProfRowanWalkOnSpotSouth2:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_ProfRowanWalkOnSpotWest2:
    WalkOnSpotNormalWest
    EndMovement

JubilifeCity_Movement_Unused7:
    WalkOnSpotNormalWest
    EndMovement

JubilifeCity_Movement_Unused8:
    WalkOnSpotNormalWest
    EndMovement

JubilifeCity_Movement_Unused9:
    WalkOnSpotNormalWest
    EndMovement

JubilifeCity_Movement_Unused10:
    WalkOnSpotNormalWest
    EndMovement

JubilifeCity_Movement_Unused11:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWalkToGrunt:
    WalkNormalWest
    WalkOnSpotNormalNorth
    EndMovement

JubilifeCity_SchoolKidM1:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message JubilifeCity_Text_CanYouTellTypePreference
    InitGlobalTextListMenu 29, 11, 0, VAR_RESULT, NO_EXIT_ON_B
    SetMenuXOriginToRight
    AddListMenuEntry MenuEntries_Text_TypePreferenceFire, 0
    AddListMenuEntry MenuEntries_Text_TypePreferenceWater, 1
    AddListMenuEntry MenuEntries_Text_TypePreferenceGrass, 2
    ShowListMenu
    SetVar VAR_0x8008, VAR_RESULT
    GoToIfEq VAR_0x8008, 0, JubilifeCity_FireMustHaveFieryPersonality
    GoToIfEq VAR_0x8008, 1, JubilifeCity_WaterMustBeCool
    Message JubilifeCity_Text_GrassNoWonderYouLookCalm
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_FireMustHaveFieryPersonality:
    Message JubilifeCity_Text_FireMustHaveFieryPersonality
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_WaterMustBeCool:
    Message JubilifeCity_Text_WaterMustBeCool
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Twin:
    NPCMessage JubilifeCity_Text_DidYouSeeMeOnTV
    End

JubilifeCity_AceTrainerM1:
    NPCMessage JubilifeCity_Text_WheredYouComeFrom
    End

JubilifeCity_AceTrainerF:
    NPCMessage JubilifeCity_Text_GraduallyGrowFriendlier
    End

JubilifeCity_ExpertM1:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfInRange VAR_ARC2_PROGRESS, 9, 19, JubilifeCity_Arc2TeachingAfterHours
    Message JubilifeCity_Text_DoYouKnowMuchAboutPokemon
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, JubilifeCity_YouAreKnowledgeable
    GoToIfEq VAR_RESULT, MENU_NO, JubilifeCity_YoureNotKnowledgeable
    End

JubilifeCity_YouAreKnowledgeable:
    Message JubilifeCity_Text_YouAreKnowledgeable
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_YoureNotKnowledgeable:
    Message JubilifeCity_Text_YoureNotKnowledgeable
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_SchoolKidM2:
    NPCMessage JubilifeCity_Text_AtMostSixPokemonWithYou
    End

JubilifeCity_MapSignpost:
    ShowMapSign JubilifeCity_Text_MapSign
    End

JubilifeCity_SignboardJubilifeCondominiums:
    ShowLandmarkSign JubilifeCity_Text_SignJubilifeCondominiums
    End

JubilifeCity_SignboardPoketchCompany:
    ShowLandmarkSign JubilifeCity_Text_SignPoketchCompany
    End

JubilifeCity_SignboardTrainersSchool:
    ShowLandmarkSign JubilifeCity_Text_SignTrainersSchool
    End

JubilifeCity_SignboardJubilifeTV:
    GoToIfInRange VAR_ARC1_PROGRESS, 12, 13, JubilifeCity_Arc1Banner
    ShowLandmarkSign JubilifeCity_Text_SignJubilifeTV
    End

JubilifeCity_SignboardGlobalTerminal:
    ShowLandmarkSign JubilifeCity_Text_SignGlobalTerminal
    End

JubilifeCity_CoordEvent_PoketchCampaign:
    LockAll
    ApplyMovement LOCALID_POKETCH_CO_PRESIDENT, JubilifeCity_Movement_PoketchCoPresidentNoticePlayer
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerFaceNorthPoketchCoPresident
    WaitMovement
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 172, JubilifeCity_PoketchCoPresidentWalkToPlayerX172
    CallIfEq VAR_0x8004, 173, JubilifeCity_PoketchCoPresidentWalkToPlayerX173
    CallIfEq VAR_0x8004, 174, JubilifeCity_PoketchCoPresidentWalkToPlayerX174
    CallIfEq VAR_0x8004, 175, JubilifeCity_PoketchCoPresidentWalkToPlayerX175
    CallIfEq VAR_0x8004, 176, JubilifeCity_PoketchCoPresidentWalkToPlayerX176
    Message JubilifeCity_Text_YouHaveNoPoketch
    SetVar VAR_POKETCH_CAMPAIGN_STATE, 2
    Message JubilifeCity_Text_FindThreeClowns
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_PoketchCoPresidentWalkToPlayerX172:
    ApplyMovement LOCALID_POKETCH_CO_PRESIDENT, JubilifeCity_Movement_PoketchCoPresidentWalkToPlayerX172
    WaitMovement
    Return

JubilifeCity_PoketchCoPresidentWalkToPlayerX173:
    ApplyMovement LOCALID_POKETCH_CO_PRESIDENT, JubilifeCity_Movement_PoketchCoPresidentWalkToPlayerX173
    WaitMovement
    Return

JubilifeCity_PoketchCoPresidentWalkToPlayerX174:
    ApplyMovement LOCALID_POKETCH_CO_PRESIDENT, JubilifeCity_Movement_PoketchCoPresidentWalkToPlayerX174
    WaitMovement
    Return

JubilifeCity_PoketchCoPresidentWalkToPlayerX175:
    ApplyMovement LOCALID_POKETCH_CO_PRESIDENT, JubilifeCity_Movement_PoketchCoPresidentWalkToPlayerX175
    WaitMovement
    Return

JubilifeCity_PoketchCoPresidentWalkToPlayerX176:
    ApplyMovement LOCALID_POKETCH_CO_PRESIDENT, JubilifeCity_Movement_PoketchCoPresidentWalkToPlayerX176
    WaitMovement
    Return

    .balign 4, 0
JubilifeCity_Movement_PlayerFaceNorthPoketchCoPresident:
    FaceNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PoketchCoPresidentNoticePlayer:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PoketchCoPresidentWalkToPlayerX172:
    WalkNormalSouth 2
    WalkNormalWest 2
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PoketchCoPresidentWalkToPlayerX173:
    WalkNormalSouth 2
    WalkNormalWest
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PoketchCoPresidentWalkToPlayerX174:
    WalkNormalSouth 4
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PoketchCoPresidentWalkToPlayerX175:
    WalkNormalSouth 2
    WalkNormalEast
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PoketchCoPresidentWalkToPlayerX176:
    WalkNormalSouth 2
    WalkNormalEast 2
    WalkNormalSouth 2
    EndMovement

JubilifeCity_PoketchCoPresident:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x091C, JubilifeCity_PoketchCaseReturned
    GoToIfGe VAR_ARC1_PROGRESS, 16, JubilifeCity_PoketchFallback
    Message JubilifeCity_Text_PoketchPresidentNoCase
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_SetObtainedCouponsCount:
    CallIfSet FLAG_RECEIVED_COUPON_1, JubilifeCity_IncreaseObtainedCouponsCount
    CallIfSet FLAG_RECEIVED_COUPON_2, JubilifeCity_IncreaseObtainedCouponsCount
    CallIfSet FLAG_RECEIVED_COUPON_3, JubilifeCity_IncreaseObtainedCouponsCount
    Return

JubilifeCity_IncreaseObtainedCouponsCount:
    AddVar VAR_0x8004, 1
    Return

JubilifeCity_GivePoketch:
    Message JubilifeCity_Text_PokemonWatchInReturnForCoupons
    RemoveItem ITEM_COUPON_1, 1, VAR_RESULT
    RemoveItem ITEM_COUPON_2, 1, VAR_RESULT
    RemoveItem ITEM_COUPON_3, 1, VAR_RESULT
    EnablePoketch
    SetVar VAR_JUBILIFE_CITY_STATE, 2
    RegisterPoketchApp POKETCH_APPID_DIGITALWATCH
    RegisterPoketchApp POKETCH_APPID_CALCULATOR
    RegisterPoketchApp POKETCH_APPID_PEDOMETER
    RegisterPoketchApp POKETCH_APPID_PARTYSTATUS
    BufferPlayerName 0
    Message JubilifeCity_Text_PlayerReceivedAPoketch
    PlayFanfare SEQ_FANFA4_sseq
    WaitFanfare
    Message JubilifeCity_Text_AddAppsToPoketch
    CloseMessage
    GetPlayerDir VAR_RESULT
    GoToIfEq VAR_RESULT, DIR_NORTH, JubilifeCity_PoketchCoPresidentLeaveNorthWestEast
    GoToIfEq VAR_RESULT, DIR_SOUTH, JubilifeCity_PoketchCoPresidentLeaveSouth
    GoToIfEq VAR_RESULT, DIR_WEST, JubilifeCity_PoketchCoPresidentLeaveNorthWestEast
    GoToIfEq VAR_RESULT, DIR_EAST, JubilifeCity_PoketchCoPresidentLeaveNorthWestEast
    End

JubilifeCity_PoketchCoPresidentLeaveNorthWestEast:
    ApplyMovement LOCALID_POKETCH_CO_PRESIDENT, JubilifeCity_Movement_PoketchCoPresidentLeaveNorthWestEast
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWatchPoketchCoPresidentLeaveNorthWestEast
    WaitMovement
    GoTo JubilifeCity_RemovePoketchCoPresident
    End

JubilifeCity_PoketchCoPresidentLeaveSouth:
    ApplyMovement LOCALID_POKETCH_CO_PRESIDENT, JubilifeCity_Movement_PoketchCoPresidentLeaveSouth
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerWatchPoketchCoPresidentLeaveSouth
    WaitMovement
    GoTo JubilifeCity_RemovePoketchCoPresident
    End

JubilifeCity_RemovePoketchCoPresident:
    RemoveObject LOCALID_POKETCH_CO_PRESIDENT
    SetFlag FLAG_RECEIVED_POKETCH
    ClearFlag FLAG_HIDE_POKETCH_CO_1F_POKETCH_CO_PRESIDENT
    // Arc 1 already hides Looker after the rally: only remove him if he's still here
    CallIfUnset FLAG_HIDE_JUBILIFE_CITY_LOOKER, JubilifeCity_Arc1RemoveLooker
    SetFlag FLAG_HIDE_JUBILIFE_CITY_LOOKER
    ReleaseAll
    End

    .balign 4, 0
JubilifeCity_Movement_PoketchCoPresidentLeaveSouth:
    WalkNormalWest
    WalkNormalNorth 9
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PoketchCoPresidentLeaveNorthWestEast:
    WalkNormalNorth 9
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWatchPoketchCoPresidentLeaveSouth:
    Delay8
    WalkOnSpotNormalWest
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_PlayerWatchPoketchCoPresidentLeaveNorthWestEast:
    Delay8
    WalkOnSpotNormalNorth
    EndMovement

JubilifeCity_Clown1:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_RECEIVED_POKETCH, JubilifeCity_PoketchClown1After
    Call JubilifeCity_PoketchClownState
    GoToIfEq VAR_0x8004, 1, JubilifeCity_PoketchClownCaseInHand
    GoToIfEq VAR_0x8004, 2, JubilifeCity_PoketchClownFallback
    Message JubilifeCity_Text_PoketchClown1
    GoTo JubilifeCity_PoketchClownEnd
    End

JubilifeCity_Clown1CorrectAnswer:
    PlaySE SEQ_SE_DP_PINPON_sseq
    Message JubilifeCity_Text_AbsolutelyCorrect1
    Message JubilifeCity_Text_GrowStrongerByDefeatingOthers
    Message JubilifeCity_Text_HeresPoketchCoupon1
    SetVar VAR_0x8004, ITEM_COUPON_1
    SetVar VAR_0x8005, 1
    SetFlag FLAG_RECEIVED_COUPON_1
    CallCommonScript CommonScript_AddItemQuantityNoLineFeed
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Clown1WrongAnswer:
    PlaySE SEQ_SE_DP_BOX03_sseq
    Message JubilifeCity_Text_WrongAnswer1
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Clown1ObtainedCoupon:
    Message JubilifeCity_Text_PokemonGrowStrongerThroughBattling
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Clown2:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_RECEIVED_POKETCH, JubilifeCity_PoketchClown2After
    Call JubilifeCity_PoketchClownState
    GoToIfEq VAR_0x8004, 1, JubilifeCity_PoketchClownCaseInHand
    GoToIfEq VAR_0x8004, 2, JubilifeCity_PoketchClownFallback
    Message JubilifeCity_Text_PoketchClown2
    GoTo JubilifeCity_PoketchClownEnd
    End

JubilifeCity_Clown2CorrectAnswer:
    PlaySE SEQ_SE_DP_PINPON_sseq
    Message JubilifeCity_Text_AbsolutelyCorrect2
    Message JubilifeCity_Text_IfPokemonMatchTypeMoveMorePowerful
    Message JubilifeCity_Text_HeresPoketchCoupon2
    SetVar VAR_0x8004, ITEM_COUPON_2
    SetVar VAR_0x8005, 1
    SetFlag FLAG_RECEIVED_COUPON_2
    CallCommonScript CommonScript_AddItemQuantityNoLineFeed
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Clown2WrongAnswer:
    PlaySE SEQ_SE_DP_BOX03_sseq
    Message JubilifeCity_Text_WrongAnswer2
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Clown2ObtainedCoupon:
    Message JubilifeCity_Text_IfPokemonMatchTypeMoveMorePowerful2
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Clown3:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_RECEIVED_POKETCH, JubilifeCity_PoketchClown3After
    Call JubilifeCity_PoketchClownState
    GoToIfEq VAR_0x8004, 1, JubilifeCity_PoketchClownCaseInHand
    GoToIfEq VAR_0x8004, 2, JubilifeCity_PoketchClownFallback
    Message JubilifeCity_Text_PoketchClown3
    GoTo JubilifeCity_PoketchClownEnd
    End

JubilifeCity_Clown3CorrectAnswer:
    PlaySE SEQ_SE_DP_PINPON_sseq
    Message JubilifeCity_Text_AbsolutelyCorrect3
    Message JubilifeCity_Text_PokemonMayHoldSingleItem
    Message JubilifeCity_Text_HeresPoketchCoupon3
    SetPosition LOCALID_POKETCH_CO_PRESIDENT, 174, 1, 771, DIR_SOUTH
    SetVar VAR_0x8004, ITEM_COUPON_3
    SetVar VAR_0x8005, 1
    SetFlag FLAG_RECEIVED_COUPON_3
    CallCommonScript CommonScript_AddItemQuantityNoLineFeed
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Clown3WrongAnswer:
    PlaySE SEQ_SE_DP_BOX03_sseq
    Message JubilifeCity_Text_WrongAnswer3
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Clown3ObtainedCoupon:
    Message JubilifeCity_Text_PokemonMayHoldSingleItem2
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_YouShouldStickAround:
    Message JubilifeCity_Text_YouShouldStickAround
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_KidWithNDS1:
    NPCMessage JubilifeCity_Text_ImTradingPokemon
    End

JubilifeCity_KidWithNDS2:
    NPCMessage JubilifeCity_Text_IMadePokemonHoldItem
    End

JubilifeCity_CoordEvent_LookerPalPad:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    SetObjectEventPos LOCALID_LOOKER, 179, VAR_0x8005
    SetObjectEventDir LOCALID_LOOKER, DIR_EAST
    SetObjectEventMovementType LOCALID_LOOKER, MOVEMENT_TYPE_LOOK_EAST
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_LOOKER
    AddObject LOCALID_LOOKER
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerNoticePlayer
    WaitMovement
    CallCommonScript CommonScript_SetLookerBGM
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerWalkToPlayer
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Movement_PlayerFaceWest
    WaitMovement
    Call JubilifeCity_CheckPalPad
    CloseMessage
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Movement_LookerLeavePalPad
    WaitMovement
    RemoveObject LOCALID_LOOKER
    CallCommonScript CommonScript_FadeToDefaultMusic_4
    SetVar VAR_JUBILIFE_LOOKER_PAL_PAD_STATE, 2
    ReleaseAll
    End

    .balign 4, 0
JubilifeCity_Movement_LookerNoticePlayer:
    WalkSlowEast 2
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkToPlayer:
    WalkFastEast 6
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerLeavePalPad:
    WalkSlowWest
    WalkFastWest 8
    EndMovement

    .balign 4, 0
JubilifeCity_Movement_LookerWalkOnSpotWestEast:
    WalkOnSpotNormalWest
    Delay8 2
    WalkOnSpotNormalEast
    EndMovement

JubilifeCity_PoketchFallback:
    Message JubilifeCity_Text_PoketchPresidentFallback
    GoTo JubilifeCity_PoketchGive
    End

JubilifeCity_PoketchCaseReturned:
    Message JubilifeCity_Text_PoketchPresidentReturned
JubilifeCity_PoketchGive:
    // Saves from before this change may still hold stock Coupons: take them back (no-op when absent)
    RemoveItem ITEM_COUPON_1, 1, VAR_RESULT
    RemoveItem ITEM_COUPON_2, 1, VAR_RESULT
    RemoveItem ITEM_COUPON_3, 1, VAR_RESULT
    EnablePoketch
    SetVar VAR_JUBILIFE_CITY_STATE, 2
    RegisterPoketchApp POKETCH_APPID_DIGITALWATCH
    RegisterPoketchApp POKETCH_APPID_CALCULATOR
    RegisterPoketchApp POKETCH_APPID_PEDOMETER
    RegisterPoketchApp POKETCH_APPID_PARTYSTATUS
    BufferPlayerName 0
    Message JubilifeCity_Text_PlayerReceivedAPoketch
    PlayFanfare SEQ_FANFA4_sseq
    WaitFanfare
    Message JubilifeCity_Text_AddAppsToPoketch
    // Bonus app: the Coin Toss. Its only other giver (Route 213 house) checks for it first; the Dot Artist
    // would break the Sunyshore Calendar -> Dot Artist -> Roulette chain (it skips the Calendar).
    Message JubilifeCity_Text_PoketchPresidentThanksApp
    SetVar VAR_0x8004, POKETCH_APPID_COINTOSS
    CallCommonScript CommonScript_ObtainPoketchApp
    WaitButton
    Message JubilifeCity_Text_PoketchPresidentHint
    WaitButton
    CloseMessage
    GetPlayerDir VAR_RESULT
    GoToIfEq VAR_RESULT, 0, JubilifeCity_PoketchCoPresidentLeaveNorthWestEast
    GoToIfEq VAR_RESULT, 1, JubilifeCity_PoketchCoPresidentLeaveSouth
    GoToIfEq VAR_RESULT, 2, JubilifeCity_PoketchCoPresidentLeaveNorthWestEast
    GoToIfEq VAR_RESULT, 3, JubilifeCity_PoketchCoPresidentLeaveNorthWestEast
    End

JubilifeCity_PoketchClown1After:
    Message JubilifeCity_Text_PoketchClown1After
    GoTo JubilifeCity_PoketchClownEnd
    End

JubilifeCity_PoketchClown2After:
    Message JubilifeCity_Text_PoketchClown2After
    GoTo JubilifeCity_PoketchClownEnd
    End

JubilifeCity_PoketchClown3After:
    Message JubilifeCity_Text_PoketchClown3After
    GoTo JubilifeCity_PoketchClownEnd
    End

// VAR_0x8004: 0 = case still missing (tail on offer), 1 = case in hand, 2 = Arc 2 fallback (see the president)
JubilifeCity_PoketchClownState:
    SetVar VAR_0x8004, 0
    GoToIfSet FLAG_UNK_0x091C, JubilifeCity_PoketchClownStateCase
    GoToIfGe VAR_ARC1_PROGRESS, 16, JubilifeCity_PoketchClownStateFallback
    Return

JubilifeCity_PoketchClownStateCase:
    SetVar VAR_0x8004, 1
    Return

JubilifeCity_PoketchClownStateFallback:
    SetVar VAR_0x8004, 2
    Return

JubilifeCity_PoketchClownCaseInHand:
    Message JubilifeCity_Text_PoketchClownCaseInHand
    GoTo JubilifeCity_PoketchClownEnd
    End

JubilifeCity_PoketchClownFallback:
    Message JubilifeCity_Text_PoketchClownFallback
JubilifeCity_PoketchClownEnd:
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1HideRally:
    SetFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY
    SetFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY_CAST
    Return

JubilifeCity_Arc1OnTransition:
    CallIfLt VAR_JUBILIFE_CITY_STATE, 2, JubilifeCity_Arc1SkipStockIntro
    CallIfEq VAR_ARC1_PROGRESS, 12, JubilifeCity_Arc1SetUpRally
    CallIfEq VAR_ARC1_PROGRESS, 13, JubilifeCity_Arc1AfterRally
    CallIfGe VAR_ARC1_PROGRESS, 14, JubilifeCity_Arc1RallyOver
    CallIfUnset FLAG_RECEIVED_POKETCH, JubilifeCity_PoketchOnTransition
    Return

// Until the Pokétch is given, keep the president and the clowns out from 14 on, and in Arc 2 once its Jubilife
// scenes are over (VAR_ARC2_PROGRESS 9+), so the fallback is always reachable. (13 is AfterRally's; Arc 2 0-8 are
// left alone for scenes 2.1-2.4.)
JubilifeCity_PoketchOnTransition:
    GoToIfLt VAR_ARC1_PROGRESS, 14, JubilifeCity_PoketchOnTransitionEnd
    GoToIfLt VAR_ARC1_PROGRESS, 16, JubilifeCity_Arc1RestorePoketchCampaign
    GoToIfGe VAR_ARC2_PROGRESS, 9, JubilifeCity_Arc1RestorePoketchCampaign
JubilifeCity_PoketchOnTransitionEnd:
    Return

// The stock first visit (counterpart escort, Looker and the VS Recorder, Barry and the Parcel in the Trainers'
// School, Looker blocking the east exit) never happens in Arc 1. State 2 makes coord events 0 and 2 and JubilifeCity_SetLookerPositionFirstArrival
// inert. The Pokétch is earned through the crate tail (see JubilifeCity_PoketchCoPresident), without the forced president intro (coord 4).
JubilifeCity_Arc1SkipStockIntro:
    SetVar VAR_JUBILIFE_CITY_STATE, 2
    SetFlag FLAG_TALKED_TO_TRAINERS_SCHOOL_RIVAL
    SetFlag FLAG_HIDE_TRAINERS_SCHOOL_RIVAL
    SetVar VAR_POKETCH_CAMPAIGN_STATE, 2
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_POKETCH_CO_PRESIDENT
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_CLOWNS_1_AND_2
    Return

JubilifeCity_Arc1SetUpRally:
    ClearFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY
    ClearFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY_CAST
    // Clear the plaza: the clown leaves the TV door and the Twin plays on the avenue instead
    SetFlag FLAG_HIDE_JUBILIFE_CITY_CLOWN_3
    // The Pokétch president and his two clowns sit the rally out. This also keeps the rally cast within the
    // field's dynamic object texture slots (the crowd reuses Jubilife's preloaded move-model gfx).
    SetFlag FLAG_HIDE_JUBILIFE_CITY_CLOWNS_1_AND_2
    SetFlag FLAG_HIDE_JUBILIFE_CITY_POKETCH_CO_PRESIDENT
    SetObjectEventPos LOCALID_TWIN, 152, 759
    // Looker, the "Man in a Trench Coat", at the east end of the crowd, watching the screen (D4). The rally's
    // camera pan stops on him on its way to Cyrus (Arc 1 r2, critic #6).
    SetObjectEventPos LOCALID_LOOKER, 172, 756
    SetObjectEventDir LOCALID_LOOKER, DIR_NORTH
    SetObjectEventMovementType LOCALID_LOOKER, MOVEMENT_TYPE_LOOK_NORTH
    Return

JubilifeCity_Arc1AfterRally:
    ClearFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY
    SetFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY_CAST
    // Normally already done in-session by the rally (RestorePlaza, RemoveObject of Looker); kept as a guard
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_CLOWN_3
    SetFlag FLAG_HIDE_JUBILIFE_CITY_LOOKER
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_CLOWNS_1_AND_2
    CallIfUnset FLAG_RECEIVED_POKETCH, JubilifeCity_Arc1RestorePoketchCampaign
    Return

// Only the Arc 1 rally objects are touched from 14 on. The stock flags SetUpRally changed at 12 (0x0238, 0x01F5,
// 0x01F6) are restored by the rally itself (JubilifeCity_Arc1RestorePlaza), and the rally's RemoveObject of
// Looker sets FLAG_HIDE_JUBILIFE_CITY_LOOKER, so later stock scenes (post-Gym RemoveObject 24/25/27, the Pal Pad scene's
// ClearFlag FLAG_HIDE_JUBILIFE_CITY_LOOKER) keep working in Arc 2.
JubilifeCity_Arc1RallyOver:
    SetFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY
    SetFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY_CAST
    Return

// Until the Pokétch is obtained (FLAG_RECEIVED_POKETCH), the president is back after the rally
JubilifeCity_Arc1RestorePoketchCampaign:
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_CLOWNS_1_AND_2
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_POKETCH_CO_PRESIDENT
    Return

// End of the rally, while the camera is on Cyrus: undo SetUpRally's plaza changes in-session. Cyrus and
// Looker are already removed, which leaves room for the clown gfx (all three clowns are off screen here).
JubilifeCity_Arc1RestorePlaza:
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_CLOWN_3
    AddObject LOCALID_CLOWN_3
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_CLOWNS_1_AND_2
    AddObject LOCALID_CLOWN_1
    AddObject LOCALID_CLOWN_2
    // The Pokétch president (until he has handed out the Pokétch; stock JubilifeCity_RemovePoketchCoPresident removes him for good) is only
    // un-hidden here and appears on the next Jubilife load. Adding him in-session draws a black square: his gfx
    // does not fit in the field's dynamic object texture slots next to the grunts and the clowns.
    CallIfUnset FLAG_RECEIVED_POKETCH, JubilifeCity_Arc1UnhidePresident
    Return

JubilifeCity_Arc1UnhidePresident:
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_POKETCH_CO_PRESIDENT
    Return

JubilifeCity_Arc1RemoveLooker:
    RemoveObject LOCALID_LOOKER
    Return

// Talk to Garius (object script)
JubilifeCity_Arc1Garius:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8004, 164, JubilifeCity_Arc1MovePlayerBehindGarius
    GoToIfNe VAR_0x8005, 754, JubilifeCity_Arc1MovePlayerBehindGarius
    GoTo JubilifeCity_Arc1Rally
    End

// Talked to from the side or from the stage: put the player in the aisle behind Garius first
JubilifeCity_Arc1MovePlayerBehindGarius:
    FadeScreenOut
    WaitFadeScreen
    SetPosition LOCALID_PLAYER, 164, 0, 754, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    GoTo JubilifeCity_Arc1Rally
    End

// Coord event in the aisle right behind Garius (164,754), state 12
JubilifeCity_Arc1TriggerRally:
    LockAll
    GoTo JubilifeCity_Arc1Rally
    End

JubilifeCity_Arc1Rally:
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc1Movement_FaceNorth
    ApplyMovement LOCALID_ARC1_GARIUS, JubilifeCity_Arc1Movement_GariusNoticePlayer
    WaitMovement
    // Tilt up to the Jubilife TV facade: the big screen switches on (D2). Saros is only a voice on the screen,
    // "Saros (on screen):"; no overworld object stands in for him (playtest bug 11).
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    AddFreeCamera VAR_0x8004, VAR_0x8005
    ApplyFreeCameraMovement JubilifeCity_Arc1Movement_CameraUpToScreen
    WaitMovement
    StopMusic
    PlayFanfare SEQ_SE_DP_TV_NOISE_sseq
    WaitFanfare
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitTime 10, VAR_RESULT
    PlayMusic SEQ_TV_HOUSOU_sseq
    WaitTime 20, VAR_RESULT
    Message JubilifeCity_Text_Arc1SarosEveryoneHasLostSomeone
    Message JubilifeCity_Text_Arc1SarosTheyTellYouToAcceptIt
    Message JubilifeCity_Text_Arc1SarosWeWillBringThemBack
    WaitButton
    CloseMessage
    // The broadcast cuts out
    StopMusic
    PlayFanfare SEQ_SE_DP_TV_NOISE_sseq
    WaitTime 6, VAR_RESULT
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitFanfare
    GoTo JubilifeCity_Arc1Movement_CameraDownToCrowd
    WaitMovement
    // The crowd murmurs
    ApplyMovement LOCALID_ARC1_CROWD_0, JubilifeCity_Arc1Movement_TurnEast
    ApplyMovement LOCALID_ARC1_CROWD_2, JubilifeCity_Arc1Movement_TurnWest
    ApplyMovement LOCALID_ARC1_CROWD_3, JubilifeCity_Arc1Movement_TurnEast
    ApplyMovement LOCALID_ARC1_CROWD_6, JubilifeCity_Arc1Movement_TurnEast
    ApplyMovement LOCALID_ARC1_CROWD_7, JubilifeCity_Arc1Movement_TurnWest
    ApplyMovement LOCALID_ARC1_CROWD_8, JubilifeCity_Arc1Movement_TurnSouth
    WaitMovement
    Message JubilifeCity_Text_Arc1CrowdMurmurs
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC1_CROWD_0, JubilifeCity_Arc1Movement_TurnNorthLater
    ApplyMovement LOCALID_ARC1_CROWD_2, JubilifeCity_Arc1Movement_TurnNorthLater
    ApplyMovement LOCALID_ARC1_CROWD_3, JubilifeCity_Arc1Movement_TurnNorthLater
    ApplyMovement LOCALID_ARC1_CROWD_6, JubilifeCity_Arc1Movement_TurnNorthLater
    ApplyMovement LOCALID_ARC1_CROWD_7, JubilifeCity_Arc1Movement_TurnNorthLater
    ApplyMovement LOCALID_ARC1_CROWD_8, JubilifeCity_Arc1Movement_TurnNorthLater
    // A grunt pushes a flyer into Garius's hands
    ApplyMovement LOCALID_ARC1_GRUNT_FLYER, JubilifeCity_Arc1Movement_GruntToGarius
    WaitMovement
    Message JubilifeCity_Text_Arc1GruntEverybodysLostSomebody
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC1_GRUNT_FLYER, JubilifeCity_Arc1Movement_GruntBackToStage
    ApplyMovement LOCALID_ARC1_GARIUS, JubilifeCity_Arc1Movement_GariusLookAtFlyer
    WaitMovement
    // Garius stares at the flyer, folds it and pockets it: no narration, the pause carries it (critic #8)
    WaitTime 80, VAR_RESULT
    BufferRivalName 0
    Message JubilifeCity_Text_Arc1GariusJustAFlyer
    WaitButton
    CloseMessage
    // Pan away from the kids toward the edge of the crowd. It stops on the trench coat man at the east end of
    // the crowd: he glances east, at Cyrus (Arc 1 r2, critic #6).
    ApplyFreeCameraMovement JubilifeCity_Arc1Movement_CameraToLooker
    WaitMovement
    WaitTime 10, VAR_RESULT
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Arc1Movement_TurnEast
    WaitMovement
    WaitTime 20, VAR_RESULT
    Message JubilifeCity_Text_Arc1LookerThatSuit
    WaitButton
    CloseMessage
    // The pan finishes on Cyrus, alone, watching the screen. The trench coat man slips away south, out of
    // frame, and is removed once he's off screen (D4: RemoveObject sets FLAG_HIDE_JUBILIFE_CITY_LOOKER)
    ApplyFreeCameraMovement JubilifeCity_Arc1Movement_CameraLookerToCyrus
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Arc1Movement_LookerSlipAway
    WaitMovement
    RemoveObject LOCALID_LOOKER
    WaitTime 20, VAR_RESULT
    Message JubilifeCity_Text_Arc1CyrusIKnowThatVoice
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC1_CYRUS, JubilifeCity_Arc1Movement_CyrusLeave
    WaitMovement
    RemoveObject LOCALID_ARC1_CYRUS
    WaitTime 15, VAR_RESULT
    // Still off camera: the TV door clown and the two Pokétch campaign clowns come back for the rest of this visit
    Call JubilifeCity_Arc1RestorePlaza
    ApplyFreeCameraMovement JubilifeCity_Arc1Movement_CameraBackToPlayer
    WaitMovement
    RestoreCamera
    // Garius heads for Route 203 (he waits there for scene 12)
    ApplyMovement LOCALID_ARC1_GARIUS, JubilifeCity_Arc1Movement_GariusRunToRoute203
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc1Movement_PlayerWatchGariusLeave
    WaitMovement
    RemoveObject LOCALID_ARC1_GARIUS
    CallCommonScript CommonScript_FadeToDefaultMusic
    SetVar VAR_ARC1_PROGRESS, 13 /* rally done */
    // Looker and the crate grunt (round 3 tail) arrive for the rest of this visit
    Call JubilifeCity_Arc1CrateSetUpAfterRally
    ReleaseAll
    End

// Coord event at the east exit (x188, z757-760), state 12: the rally comes first
JubilifeCity_Arc1TriggerEastExit:
    LockAll
    BufferRivalName 0
    Message JubilifeCity_Text_Arc1GariusOverHere
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc1Movement_StepWest
    WaitMovement
    ReleaseAll
    End

// Arc 1's "To be continued..." gate on the north exit (state 16, D13) was removed for Arc 2: its coord event is
// gone from the events file. The script slot stays so the script ids after it don't shift.
JubilifeCity_Arc1TriggerToBeContinued:
    End

JubilifeCity_Arc1TrenchCoat:
    Message JubilifeCity_Text_Arc1TrenchCoat
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_LOOKER, JubilifeCity_Arc1Movement_FaceNorth
    WaitMovement
    ReleaseAll
    End

JubilifeCity_Arc1Banner:
    ShowLandmarkSign JubilifeCity_Text_Arc1BannerWhoDidYouLose
    End

JubilifeCity_Arc1EclipseGruntFlyer:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1GruntTakeAFlyer
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1EclipseGruntF:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1GruntYouDontHaveToAcceptIt
    WaitButton
    CloseMessage
    ReleaseAll
    End

// Talk to Cyrus before the rally. He keeps his eyes on the TV and doesn't turn around: in the rally the player
// never sees him (scene 11), and the kids only find him in Jubilife at the start of Arc 2.
JubilifeCity_Arc1Cyrus:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message JubilifeCity_Text_Arc1CyrusWhoDidYouLose
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1CrowdNeverCameHome:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1CrowdNeverCameHome
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1CrowdGrandpasPokemon:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1CrowdGrandpasPokemon
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1CrowdOneMoreDay:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1CrowdOneMoreDay
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1CrowdBestFriend:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1CrowdBestFriend
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1CrowdGransDoor:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1CrowdGransDoor
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1CrowdMomAskedMe:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1CrowdMomAskedMe
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
JubilifeCity_Arc1Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_GariusNoticePlayer:
    FaceSouth
    Delay16
    Delay8
    FaceNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_CameraUpToScreen:
    WalkSlowNorth 3
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_CameraDownToCrowd:
    WalkNormalSouth 3
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_TurnEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_TurnWest:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_TurnSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_TurnNorthLater:
    Delay16
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_GruntToGarius:
    Delay16
    WalkNormalEast 2
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_GruntBackToStage:
    WalkNormalWest 2
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_GariusLookAtFlyer:
    Delay16
    WalkOnSpotSlowSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_CameraToLooker:
    WalkNormalEast 8
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_CameraLookerToCyrus:
    WalkNormalEast 3
    WalkNormalNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_LookerSlipAway:
    Delay8
    WalkNormalSouth 6
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_CyrusLeave:
    WalkOnSpotSlowEast
    Delay16
    WalkNormalNorth 8
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_CameraBackToPlayer:
    WalkFastSouth
    WalkFastWest 11
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_GariusRunToRoute203:
    WalkFastEast
    WalkFastSouth 5
    WalkFastEast 15
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_PlayerWatchGariusLeave:
    Delay8 2
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_StepWest:
    WalkNormalWest
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1Movement_StepSouth:
    WalkNormalSouth
    EndMovement

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 1 round 3: "Follow the crate", Looker's stealth tail (VAR_ARC1_PROGRESS 13-15).
//
// Looker (still the "Man in a Trench Coat") waits at the east exit and asks the player to tail an Eclipse
// grunt who drags a crate from the Pokémon Center to the Route 204 mouth, where a second grunt takes it.
// fix2-poketch: the crate (a case) holds Pokétch Company prototypes. At the handoff the two grunts argue over
// who carries it, Looker steps in, they bolt and leave it, and Looker gives it to the player, who returns it to
// the Pokétch president for the Pokétch (JubilifeCity_PoketchCoPresident). No Great Balls any more: the Pokétch is the reward.
// The engine can't move an NPC while the player walks, and scripts can't read an NPC's live facing, so the
// tail is stepped: a coord event covering the east half of the city runs on every player step while the
// tail is on, and each step is one beat of the grunt's look cycle at his current stop.
//   beats 1-2 forward, 3-4 a nervous glance left and right (the warning), 5-7 looking back, 8-0 forward.
// Each beat checks the cone he's facing (1 tile at range 1, 3 wide at 2-3, 5 wide at 4-6) and the four
// tiles next to him. Seen: "Huh? ...Kid, scram.", a fade, and the player is put back at that stop's
// checkpoint. Close behind him (Chebyshev 3, or 2 at stop 3) on a beat he isn't looking back: he walks on.
// Stop 4 is the handoff at the Route 204 mouth: reaching the top rows of the city (z<=737) off the receiver's
// line (x174) plays the overheard scene and Looker's payoff.
//
// Flags: FLAG_UNK_0x091C tail done (persistent); 0x091D Looker, 0x091E grunt + crate, 0x091F receiver
// (hide flags, recomputed on every load). Map-local vars (reset on every map load, so leaving the city
// abandons the tail and Looker offers it again): VAR_MAP_LOCAL_0x03 declined once, _4 the call-over coord is
// armed, _5 tail on (the step coord), _6 stop 1-4, _7 beat, _8-_B scratch for the sight check.

JubilifeCity_Arc1CrateOnTransition:
    SetFlag FLAG_UNK_0x091D
    SetFlag FLAG_UNK_0x091E
    SetFlag FLAG_UNK_0x091F
    GoToIfSet FLAG_UNK_0x091C, JubilifeCity_Arc1CrateOnTransitionEnd
    GoToIfLt VAR_ARC1_PROGRESS, 13, JubilifeCity_Arc1CrateOnTransitionEnd
    GoToIfGt VAR_ARC1_PROGRESS, 15, JubilifeCity_Arc1CrateOnTransitionEnd
    ClearFlag FLAG_UNK_0x091D
    ClearFlag FLAG_UNK_0x091E
    SetVar VAR_MAP_LOCAL_0x04, 1
    // The wandering Ace Trainer on the avenue moves out of the grunt's path (x175) while the tail is on offer
    SetObjectEventPos LOCALID_ACE_TRAINER_M_1, 167, 759
JubilifeCity_Arc1CrateOnTransitionEnd:
    Return

// End of the rally (13 is set in-session, so OnTransition hasn't placed them yet): both are off screen here
JubilifeCity_Arc1CrateSetUpAfterRally:
    ClearFlag FLAG_UNK_0x091D
    ClearFlag FLAG_UNK_0x091E
    AddObject LOCALID_ARC1_CRATE_LOOKER
    AddObject LOCALID_ARC1_CRATE_GRUNT
    AddObject LOCALID_ARC1_CRATE
    SetVar VAR_MAP_LOCAL_0x04, 1
    Return

// Coord event at x186, z757-762 (every way to the east exit), armed once per visit: Looker calls the player over
JubilifeCity_Arc1CrateTriggerPsst:
    LockAll
    SetVar VAR_MAP_LOCAL_0x04, 0
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_FaceSouth
    WaitMovement
    Message JubilifeCity_Text_Arc1CratePsst
    WaitButton
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
JubilifeCity_Arc1CrateWalkToLooker:
    GoToIfLe VAR_0x8005, 757, JubilifeCity_Arc1CrateAtLooker
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc1CrateMovement_WalkNorth
    WaitMovement
    SubVar VAR_0x8005, 1
    GoTo JubilifeCity_Arc1CrateWalkToLooker
    End

JubilifeCity_Arc1CrateAtLooker:
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc1CrateMovement_FaceNorth
    WaitMovement
    Message JubilifeCity_Text_Arc1CrateOffer
    GoTo JubilifeCity_Arc1CrateAsk
    End

// Talk to Looker (he's only here while the tail is on offer)
JubilifeCity_Arc1CrateLooker:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    SetVar VAR_MAP_LOCAL_0x04, 0
    GoToIfEq VAR_MAP_LOCAL_0x03, 1, JubilifeCity_Arc1CrateReoffer
    Message JubilifeCity_Text_Arc1CrateOffer
    GoTo JubilifeCity_Arc1CrateAsk
    End

JubilifeCity_Arc1CrateReoffer:
    Message JubilifeCity_Text_Arc1CrateReoffer
    GoTo JubilifeCity_Arc1CrateAsk
    End

JubilifeCity_Arc1CrateAsk:
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, JubilifeCity_Arc1CrateAccept
    Message JubilifeCity_Text_Arc1CrateDeclined
    WaitButton
    CloseMessage
    SetVar VAR_MAP_LOCAL_0x03, 1
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_FaceSouth
    WaitMovement
    ReleaseAll
    End

// The player is at (186,757) facing Looker. The camera pans to the avenue crossing (x175) while the grunt
// pushes the crate up from the Pokémon Center and stops at the first stop (175,759).
JubilifeCity_Arc1CrateAccept:
    Message JubilifeCity_Text_Arc1CrateAccepted
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_FaceNorth
    WaitMovement
    // Off screen: the wandering Ace Trainer stands clear of the grunt's path (x175) for the rest of this visit
    SetPosition LOCALID_ACE_TRAINER_M_1, 167, 0, 759, DIR_EAST
    SetMovementType LOCALID_ACE_TRAINER_M_1, MOVEMENT_TYPE_LOOK_AROUND
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    AddFreeCamera VAR_0x8004, VAR_0x8005
    ApplyFreeCameraMovement JubilifeCity_Arc1CrateMovement_CameraToCrossing
    ApplyMovement LOCALID_ARC1_CRATE, JubilifeCity_Arc1CrateMovement_CrateIntro
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_GruntIntro
    WaitMovement
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_Glance
    WaitMovement
    WaitTime 20, VAR_RESULT
    ApplyFreeCameraMovement JubilifeCity_Arc1CrateMovement_CameraBack
    WaitMovement
    RestoreCamera
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_FaceSouth
    WaitMovement
    Message JubilifeCity_Text_Arc1CrateGo
    WaitButton
    CloseMessage
    // He slips away into the alcove behind him, out of sight
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_LookerSlipAway
    WaitMovement
    RemoveObject LOCALID_ARC1_CRATE_LOOKER
    SetVar VAR_MAP_LOCAL_0x06, 1
    SetVar VAR_MAP_LOCAL_0x07, 0
    SetVar VAR_MAP_LOCAL_0x05, 1
    ReleaseAll
    End

// Coord event over the east half of the city (x158-191, z736-781) while the tail is on: one beat per step
JubilifeCity_Arc1CrateTriggerStep:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_MAP_LOCAL_0x06, 4, JubilifeCity_Arc1CrateHandoffStep
    AddVar VAR_MAP_LOCAL_0x07, 1
    CallIfGe VAR_MAP_LOCAL_0x07, 9, JubilifeCity_Arc1CrateResetBeat
    Call JubilifeCity_Arc1CrateStopParams
    CallIfEq VAR_MAP_LOCAL_0x07, 3, JubilifeCity_Arc1CrateGlance
    CallIfEq VAR_MAP_LOCAL_0x07, 4, JubilifeCity_Arc1CrateGlance
    CallIfEq VAR_MAP_LOCAL_0x07, 5, JubilifeCity_Arc1CrateLookBack
    CallIfEq VAR_MAP_LOCAL_0x07, 8, JubilifeCity_Arc1CrateLookForward
    // Facing for this beat: forward (north), or back during beats 5-7
    SetVar VAR_0x8008, DIR_NORTH
    CallIfEq VAR_MAP_LOCAL_0x07, 5, JubilifeCity_Arc1CrateUseBackDir
    CallIfEq VAR_MAP_LOCAL_0x07, 6, JubilifeCity_Arc1CrateUseBackDir
    CallIfEq VAR_MAP_LOCAL_0x07, 7, JubilifeCity_Arc1CrateUseBackDir
    Call JubilifeCity_Arc1CrateCheckSight
    GoToIfEq VAR_RESULT, 1, JubilifeCity_Arc1CrateCaught
    GoToIfInRange VAR_MAP_LOCAL_0x07, 5, 7, JubilifeCity_Arc1CrateStepEnd
    // Close behind him while he isn't looking: he moves on
    GoToIfGt VAR_0x8009, VAR_0x800B, JubilifeCity_Arc1CrateStepEnd
    GoToIfGt VAR_0x800A, VAR_0x800B, JubilifeCity_Arc1CrateStepEnd
    GoTo JubilifeCity_Arc1CrateAdvance
    End

JubilifeCity_Arc1CrateStepEnd:
    End

JubilifeCity_Arc1CrateResetBeat:
    SetVar VAR_MAP_LOCAL_0x07, 0
    Return

JubilifeCity_Arc1CrateUseBackDir:
    SetVar VAR_0x8008, VAR_MAP_LOCAL_0x0A
    Return

// The grunt's stop: VAR_0x8006/0x8007 his tile, VAR_MAP_LOCAL_0x0A the way he looks back, VAR_0x800B the
// "close behind him" distance
JubilifeCity_Arc1CrateStopParams:
    GoToIfEq VAR_MAP_LOCAL_0x06, 2, JubilifeCity_Arc1CrateStopParams2
    GoToIfEq VAR_MAP_LOCAL_0x06, 3, JubilifeCity_Arc1CrateStopParams3
    // Stop 1: the avenue crossing. He checks back east, the way the player comes from.
    SetVar VAR_0x8006, 175
    SetVar VAR_0x8007, 759
    SetVar VAR_MAP_LOCAL_0x0A, DIR_EAST
    SetVar VAR_0x800B, 3
    Return

JubilifeCity_Arc1CrateStopParams2:
    // Stop 2: halfway up the north corridor, beside the rally crowd
    SetVar VAR_0x8006, 175
    SetVar VAR_0x8007, 749
    SetVar VAR_MAP_LOCAL_0x0A, DIR_SOUTH
    SetVar VAR_0x800B, 3
    Return

JubilifeCity_Arc1CrateStopParams3:
    // Stop 3: just past the narrow gap at z743
    SetVar VAR_0x8006, 175
    SetVar VAR_0x8007, 741
    SetVar VAR_MAP_LOCAL_0x0A, DIR_SOUTH
    SetVar VAR_0x800B, 2
    Return

JubilifeCity_Arc1CrateGlance:
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_Glance
    WaitMovement
    Return

JubilifeCity_Arc1CrateLookBack:
    GoToIfEq VAR_MAP_LOCAL_0x0A, DIR_EAST, JubilifeCity_Arc1CrateLookBackEast
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_FaceSouth
    WaitMovement
    Return

JubilifeCity_Arc1CrateLookBackEast:
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_FaceEast
    WaitMovement
    Return

JubilifeCity_Arc1CrateLookForward:
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_FaceNorth
    WaitMovement
    Return

// In: VAR_0x8004/0x8005 player, VAR_0x8006/0x8007 grunt, VAR_0x8008 his facing.
// Out: VAR_RESULT 1 if he sees the player; VAR_0x8009/0x800A = |dx|/|dz| (used for "close").
// VAR_MAP_LOCAL_0x08/_9 = sign of dx/dz (0 player west/north of him, 1 same, 2 east/south).
JubilifeCity_Arc1CrateCheckSight:
    SetVar VAR_RESULT, 0
    SetVar VAR_MAP_LOCAL_0x08, 1
    SetVar VAR_0x8009, 0
    GoToIfEq VAR_0x8004, VAR_0x8006, JubilifeCity_Arc1CrateSightDZ
    GoToIfLt VAR_0x8004, VAR_0x8006, JubilifeCity_Arc1CrateSightWest
    SetVar VAR_MAP_LOCAL_0x08, 2
    SetVar VAR_0x8009, VAR_0x8004
    SubVar VAR_0x8009, VAR_0x8006
    GoTo JubilifeCity_Arc1CrateSightDZ
    End

JubilifeCity_Arc1CrateSightWest:
    SetVar VAR_MAP_LOCAL_0x08, 0
    SetVar VAR_0x8009, VAR_0x8006
    SubVar VAR_0x8009, VAR_0x8004
    GoTo JubilifeCity_Arc1CrateSightDZ
    End

JubilifeCity_Arc1CrateSightDZ:
    SetVar VAR_MAP_LOCAL_0x09, 1
    SetVar VAR_0x800A, 0
    GoToIfEq VAR_0x8005, VAR_0x8007, JubilifeCity_Arc1CrateSightAdjacent
    GoToIfLt VAR_0x8005, VAR_0x8007, JubilifeCity_Arc1CrateSightNorth
    SetVar VAR_MAP_LOCAL_0x09, 2
    SetVar VAR_0x800A, VAR_0x8005
    SubVar VAR_0x800A, VAR_0x8007
    GoTo JubilifeCity_Arc1CrateSightAdjacent
    End

JubilifeCity_Arc1CrateSightNorth:
    SetVar VAR_MAP_LOCAL_0x09, 0
    SetVar VAR_0x800A, VAR_0x8007
    SubVar VAR_0x800A, VAR_0x8005
    GoTo JubilifeCity_Arc1CrateSightAdjacent
    End

// Right next to him: he notices whichever way he faces
JubilifeCity_Arc1CrateSightAdjacent:
    SetVar VAR_MAP_LOCAL_0x0B, VAR_0x8009
    AddVar VAR_MAP_LOCAL_0x0B, VAR_0x800A
    GoToIfLe VAR_MAP_LOCAL_0x0B, 1, JubilifeCity_Arc1CrateSeen
    GoToIfEq VAR_0x8008, DIR_NORTH, JubilifeCity_Arc1CrateSightFaceNorth
    GoToIfEq VAR_0x8008, DIR_SOUTH, JubilifeCity_Arc1CrateSightFaceSouth
    GoToIfEq VAR_0x8008, DIR_WEST, JubilifeCity_Arc1CrateSightFaceWest
    GoTo JubilifeCity_Arc1CrateSightFaceEast
    End

JubilifeCity_Arc1CrateSightFaceNorth:
    GoToIfNe VAR_MAP_LOCAL_0x09, 0, JubilifeCity_Arc1CrateSightEnd
    GoTo JubilifeCity_Arc1CrateSightAlongZ
    End

JubilifeCity_Arc1CrateSightFaceSouth:
    GoToIfNe VAR_MAP_LOCAL_0x09, 2, JubilifeCity_Arc1CrateSightEnd
    GoTo JubilifeCity_Arc1CrateSightAlongZ
    End

JubilifeCity_Arc1CrateSightFaceWest:
    GoToIfNe VAR_MAP_LOCAL_0x08, 0, JubilifeCity_Arc1CrateSightEnd
    GoTo JubilifeCity_Arc1CrateSightAlongX
    End

JubilifeCity_Arc1CrateSightFaceEast:
    GoToIfNe VAR_MAP_LOCAL_0x08, 2, JubilifeCity_Arc1CrateSightEnd
    GoTo JubilifeCity_Arc1CrateSightAlongX
    End

// VAR_MAP_LOCAL_0x0A is reused here: along = distance ahead of him, VAR_MAP_LOCAL_0x0B = distance to the side
JubilifeCity_Arc1CrateSightAlongZ:
    SetVar VAR_MAP_LOCAL_0x0A, VAR_0x800A
    SetVar VAR_MAP_LOCAL_0x0B, VAR_0x8009
    GoTo JubilifeCity_Arc1CrateSightCone
    End

JubilifeCity_Arc1CrateSightAlongX:
    SetVar VAR_MAP_LOCAL_0x0A, VAR_0x8009
    SetVar VAR_MAP_LOCAL_0x0B, VAR_0x800A
    GoTo JubilifeCity_Arc1CrateSightCone
    End

JubilifeCity_Arc1CrateSightCone:
    GoToIfGt VAR_MAP_LOCAL_0x0A, 6, JubilifeCity_Arc1CrateSightEnd
    GoToIfEq VAR_MAP_LOCAL_0x0A, 1, JubilifeCity_Arc1CrateSightWidth0
    GoToIfLe VAR_MAP_LOCAL_0x0A, 3, JubilifeCity_Arc1CrateSightWidth1
    GoToIfLe VAR_MAP_LOCAL_0x0B, 2, JubilifeCity_Arc1CrateSeen
    GoTo JubilifeCity_Arc1CrateSightEnd
    End

JubilifeCity_Arc1CrateSightWidth0:
    GoToIfEq VAR_MAP_LOCAL_0x0B, 0, JubilifeCity_Arc1CrateSeen
    GoTo JubilifeCity_Arc1CrateSightEnd
    End

JubilifeCity_Arc1CrateSightWidth1:
    GoToIfLe VAR_MAP_LOCAL_0x0B, 1, JubilifeCity_Arc1CrateSeen
    GoTo JubilifeCity_Arc1CrateSightEnd
    End

JubilifeCity_Arc1CrateSeen:
    SetVar VAR_RESULT, 1
JubilifeCity_Arc1CrateSightEnd:
    Return

// He walks on to the next stop, dragging the crate a tile behind him
JubilifeCity_Arc1CrateAdvance:
    LockAll
    GoToIfEq VAR_MAP_LOCAL_0x06, 2, JubilifeCity_Arc1CrateAdvanceFrom2
    GoToIfEq VAR_MAP_LOCAL_0x06, 3, JubilifeCity_Arc1CrateAdvanceFrom3
    ApplyMovement LOCALID_ARC1_CRATE, JubilifeCity_Arc1CrateMovement_North10
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_North10
    WaitMovement
    GoTo JubilifeCity_Arc1CrateAdvanceDone
    End

JubilifeCity_Arc1CrateAdvanceFrom2:
    ApplyMovement LOCALID_ARC1_CRATE, JubilifeCity_Arc1CrateMovement_North8
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_North8
    WaitMovement
    GoTo JubilifeCity_Arc1CrateAdvanceDone
    End

// Last leg: into the Route 204 mouth, where the receiver walks down to meet him
JubilifeCity_Arc1CrateAdvanceFrom3:
    ClearFlag FLAG_UNK_0x091F
    AddObject LOCALID_ARC1_CRATE_RECEIVER
    ApplyMovement LOCALID_ARC1_CRATE, JubilifeCity_Arc1CrateMovement_CrateToHandoff
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_GruntToHandoff
    ApplyMovement LOCALID_ARC1_CRATE_RECEIVER, JubilifeCity_Arc1CrateMovement_ReceiverArrive
    WaitMovement
    GoTo JubilifeCity_Arc1CrateAdvanceDone
    End

JubilifeCity_Arc1CrateAdvanceDone:
    AddVar VAR_MAP_LOCAL_0x06, 1
    SetVar VAR_MAP_LOCAL_0x07, 0
    ReleaseAll
    End

// Seen (or talked to him mid-tail): back to the stop's checkpoint, out of his sight
JubilifeCity_Arc1CrateCaught:
    LockAll
    GoToIfEq VAR_MAP_LOCAL_0x06, 4, JubilifeCity_Arc1CrateCaughtByReceiver
    // He turns to face the player (the sight check also leaves the offsets and their signs behind)
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    Call JubilifeCity_Arc1CrateStopParams
    SetVar VAR_0x8008, DIR_NORTH
    Call JubilifeCity_Arc1CrateCheckSight
    Call JubilifeCity_Arc1CrateFacePlayer
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_Notice
    WaitMovement
    GoTo JubilifeCity_Arc1CrateCaughtMessage
    End

JubilifeCity_Arc1CrateFacePlayer:
    GoToIfLt VAR_0x8009, VAR_0x800A, JubilifeCity_Arc1CrateFacePlayerZ
    GoToIfEq VAR_MAP_LOCAL_0x08, 0, JubilifeCity_Arc1CrateFacePlayerWest
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_FaceEast
    WaitMovement
    Return

JubilifeCity_Arc1CrateFacePlayerWest:
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_FaceWest
    WaitMovement
    Return

JubilifeCity_Arc1CrateFacePlayerZ:
    GoToIfEq VAR_MAP_LOCAL_0x09, 0, JubilifeCity_Arc1CrateFacePlayerNorth
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_FaceSouth
    WaitMovement
    Return

JubilifeCity_Arc1CrateFacePlayerNorth:
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_FaceNorth
    WaitMovement
    Return

JubilifeCity_Arc1CrateCaughtByReceiver:
    ApplyMovement LOCALID_ARC1_CRATE_RECEIVER, JubilifeCity_Arc1CrateMovement_Notice
    WaitMovement
JubilifeCity_Arc1CrateCaughtMessage:
    Message JubilifeCity_Text_Arc1CrateCaught
    WaitButton
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    CallIfEq VAR_MAP_LOCAL_0x06, 1, JubilifeCity_Arc1CrateCheckpoint1
    CallIfEq VAR_MAP_LOCAL_0x06, 2, JubilifeCity_Arc1CrateCheckpoint2
    CallIfEq VAR_MAP_LOCAL_0x06, 3, JubilifeCity_Arc1CrateCheckpoint3
    CallIfEq VAR_MAP_LOCAL_0x06, 4, JubilifeCity_Arc1CrateCheckpoint4
    CallIfNe VAR_MAP_LOCAL_0x06, 4, JubilifeCity_Arc1CrateLookForward
    SetVar VAR_MAP_LOCAL_0x07, 0
    WaitTime 10, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

JubilifeCity_Arc1CrateCheckpoint1:
    SetPosition LOCALID_PLAYER, 183, 0, 758, DIR_WEST
    Return

JubilifeCity_Arc1CrateCheckpoint2:
    SetPosition LOCALID_PLAYER, 179, 0, 759, DIR_WEST
    Return

JubilifeCity_Arc1CrateCheckpoint3:
    SetPosition LOCALID_PLAYER, 170, 0, 749, DIR_NORTH
    Return

JubilifeCity_Arc1CrateCheckpoint4:
    SetPosition LOCALID_PLAYER, 170, 0, 746, DIR_NORTH
    Return

// Stop 4: the grunts meet at the Route 204 mouth (receiver at 174,731 looking down x174, the grunt at 174,732
// with the crate behind him at 174,733). The top rows of the
// city (z<=737) are the listening spot; up the receiver's line, he sees the player.
JubilifeCity_Arc1CrateHandoffStep:
    GoToIfGt VAR_0x8005, 737, JubilifeCity_Arc1CrateStepEnd
    GoToIfEq VAR_0x8004, 174, JubilifeCity_Arc1CrateCaught
    GoTo JubilifeCity_Arc1CrateHandoff
    End

JubilifeCity_Arc1CrateHandoff:
    LockAll
    SetVar VAR_MAP_LOCAL_0x05, 0
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc1CrateMovement_FaceNorth
    WaitMovement
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    AddFreeCamera VAR_0x8004, VAR_0x8005
    ApplyFreeCameraMovement JubilifeCity_Arc1CrateMovement_CameraUp
    WaitMovement
    Message JubilifeCity_Text_Arc1CrateYoureLate
    WaitButton
    CloseMessage
    Message JubilifeCity_Text_Arc1CrateAnotherOne
    WaitButton
    CloseMessage
    // He steps aside and the receiver comes down to the crate
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_GruntStepAside
    WaitMovement
    ApplyMovement LOCALID_ARC1_CRATE_RECEIVER, JubilifeCity_Arc1CrateMovement_LookAtCrate
    WaitMovement
    Message JubilifeCity_Text_Arc1CrateBeeping
    WaitButton
    CloseMessage
    Message JubilifeCity_Text_Arc1CrateDontAsk
    WaitButton
    CloseMessage
    // fix2-poketch: they argue over who carries it, Looker steps in, they bolt and leave the case behind
    Message JubilifeCity_Text_Arc1CrateArgueHaulIt
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_Stomp
    WaitMovement
    Message JubilifeCity_Text_Arc1CrateArgueYourTurn
    WaitButton
    CloseMessage
    // Looker walks up the x174 line (the player is never on it here), then round to the case's east side (175,733)
    SetObjectEventPos LOCALID_ARC1_CRATE_LOOKER, 174, 745
    SetObjectEventDir LOCALID_ARC1_CRATE_LOOKER, DIR_NORTH
    SetObjectEventMovementType LOCALID_ARC1_CRATE_LOOKER, MOVEMENT_TYPE_LOOK_NORTH
    ClearFlag FLAG_UNK_0x091D
    AddObject LOCALID_ARC1_CRATE_LOOKER
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_LookerCatchUp
    WaitMovement
    Message JubilifeCity_Text_Arc1CrateLookerStepsIn
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_FaceSouthNotice
    ApplyMovement LOCALID_ARC1_CRATE_RECEIVER, JubilifeCity_Arc1CrateMovement_Notice
    WaitMovement
    Message JubilifeCity_Text_Arc1CrateScram
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC1_CRATE_RECEIVER, JubilifeCity_Arc1CrateMovement_Flee
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_Flee
    WaitMovement
    RemoveObject LOCALID_ARC1_CRATE_RECEIVER
    RemoveObject LOCALID_ARC1_CRATE_GRUNT
    ApplyFreeCameraMovement JubilifeCity_Arc1CrateMovement_CameraDown
    WaitMovement
    RestoreCamera
    // He opens the case
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_Inspect
    WaitMovement
    Message JubilifeCity_Text_Arc1CrateLookerEnd
    WaitButton
    Message JubilifeCity_Text_Arc1CratePrototypes
    WaitButton
    CloseMessage
    RemoveObject LOCALID_ARC1_CRATE
    // ...and brings it to the player: back to (174,736), then along row 736 next to (z736) or above (z737) the player
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_LookerToRow736
    WaitMovement
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    SetVar VAR_0x8008, 174
    SetVar VAR_0x8009, VAR_0x8004
    CallIfEq VAR_0x8005, 736, JubilifeCity_Arc1CrateBesidePlayer
    Call JubilifeCity_Arc1CrateLookerWalkX
    Call JubilifeCity_Arc1CrateFaceEachOther
    BufferPlayerName 0
    Message JubilifeCity_Text_Arc1CrateGotCase
    PlayFanfare SEQ_FANFA4_sseq
    WaitFanfare
    Message JubilifeCity_Text_Arc1CrateWellDone
    WaitButton
    Message JubilifeCity_Text_Arc1CrateNeverSawMe
    WaitButton
    CloseMessage
    // He follows the grunts up Route 204: back along row 736 to x174, then north
    SetVar VAR_0x8009, 174
    Call JubilifeCity_Arc1CrateLookerWalkX
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_LookerLeave
    WaitMovement
    RemoveObject LOCALID_ARC1_CRATE_LOOKER
    SetFlag FLAG_UNK_0x091C
    ReleaseAll
    End

// Player on row 736 (x != 174): Looker stops on the tile next to the player on the x174 side
JubilifeCity_Arc1CrateBesidePlayer:
    GoToIfGt VAR_0x8004, 174, JubilifeCity_Arc1CrateBesidePlayerEast
    AddVar VAR_0x8009, 1
    Return

JubilifeCity_Arc1CrateBesidePlayerEast:
    SubVar VAR_0x8009, 1
    Return

// Looker walks along row 736 from x VAR_0x8008 to x VAR_0x8009
JubilifeCity_Arc1CrateLookerWalkX:
    GoToIfEq VAR_0x8008, VAR_0x8009, JubilifeCity_Arc1CrateLookerWalkXDone
    GoToIfLt VAR_0x8008, VAR_0x8009, JubilifeCity_Arc1CrateLookerStepEast
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_WalkWest
    WaitMovement
    SubVar VAR_0x8008, 1
    GoTo JubilifeCity_Arc1CrateLookerWalkX
    End

JubilifeCity_Arc1CrateLookerStepEast:
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_WalkEast
    WaitMovement
    AddVar VAR_0x8008, 1
    GoTo JubilifeCity_Arc1CrateLookerWalkX
    End

JubilifeCity_Arc1CrateLookerWalkXDone:
    Return

JubilifeCity_Arc1CrateFaceEachOther:
    GoToIfEq VAR_0x8005, 736, JubilifeCity_Arc1CrateFaceEachOtherSide
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_FaceSouth
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc1CrateMovement_FaceNorth
    WaitMovement
    Return

JubilifeCity_Arc1CrateFaceEachOtherSide:
    GoToIfGt VAR_0x8004, 174, JubilifeCity_Arc1CrateFaceEachOtherEast
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_FaceWest
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc1CrateMovement_FaceEast
    WaitMovement
    Return

JubilifeCity_Arc1CrateFaceEachOtherEast:
    ApplyMovement LOCALID_ARC1_CRATE_LOOKER, JubilifeCity_Arc1CrateMovement_FaceEast
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc1CrateMovement_FaceWest
    WaitMovement
    Return

// Talk to the grunt: before the tail he brushes the player off; during it, the player has been seen
JubilifeCity_Arc1CrateGrunt:
    GoToIfEq VAR_MAP_LOCAL_0x05, 1, JubilifeCity_Arc1CrateCaught
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1CrateGruntIdle
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC1_CRATE_GRUNT, JubilifeCity_Arc1CrateMovement_FaceWest
    WaitMovement
    ReleaseAll
    End

JubilifeCity_Arc1CrateReceiver:
    GoToIfEq VAR_MAP_LOCAL_0x05, 1, JubilifeCity_Arc1CrateCaught
    End

JubilifeCity_Arc1CrateBox:
    GoToIfEq VAR_MAP_LOCAL_0x05, 1, JubilifeCity_Arc1CrateCaught
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message JubilifeCity_Text_Arc1CrateBox
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_WalkNorth:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_Glance:
    FaceWest
    Delay8 2
    FaceEast
    Delay8 2
    FaceNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_Notice:
    EmoteExclamationMark
    Delay8
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_CameraToCrossing:
    WalkFastWest 11
    WalkFastSouth 4
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_CameraBack:
    WalkFastNorth 4
    WalkFastEast 11
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_CrateIntro:
    WalkNormalWest 2
    WalkNormalNorth 17
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_GruntIntro:
    WalkNormalWest
    WalkNormalNorth 18
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_LookerSlipAway:
    WalkNormalNorth 3
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_North10:
    WalkNormalNorth 10
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_North8:
    WalkNormalNorth 8
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_CrateToHandoff:
    WalkNormalNorth 5
    WalkNormalWest
    WalkNormalNorth 4
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_GruntToHandoff:
    WalkNormalNorth 4
    WalkNormalWest
    WalkNormalNorth 5
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_ReceiverArrive:
    Delay16 4
    WalkNormalSouth 3
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_CameraUp:
    WalkSlowNorth 2
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_CameraDown:
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_GruntStepAside:
    WalkNormalWest
    FaceEast
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_LookAtCrate:
    WalkNormalSouth
    WalkOnSpotSlowSouth
    Delay8 2
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_Stomp:
    WalkOnSpotFastEast
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_FaceSouthNotice:
    FaceSouth
    EmoteExclamationMark
    Delay8
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_Flee:
    WalkFastNorth 10
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_LookerCatchUp:
    WalkNormalNorth 10
    WalkNormalEast
    WalkNormalNorth 2
    FaceWest
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_Inspect:
    FaceWest
    Delay8 2
    WalkOnSpotSlowWest
    Delay8 2
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_LookerToRow736:
    WalkNormalSouth 2
    WalkNormalWest
    WalkNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_WalkWest:
    WalkNormalWest
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_WalkEast:
    WalkNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_Arc1CrateMovement_LookerLeave:
    FaceNorth
    Delay8
    WalkNormalNorth 14
    EndMovement

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 2 (s-jubilife): 2.1 finding Cyrus, 2.3 Cyrus battle 1 (see the header comment).

// 1 once s-cutaways (2.4 in the violet room) is merged; 0 skips the cutaway (stub)
#define ARC2_CUTAWAY_2_4_WIRED 1

JubilifeCity_Arc2OnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_20
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_21
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_22
    GoToIfLt VAR_ARC1_PROGRESS, 16, JubilifeCity_Arc2OnTransitionEnd
    CallIfEq VAR_ARC2_PROGRESS, 0, JubilifeCity_Arc2SetUpFindCyrus
    CallIfEq VAR_ARC2_PROGRESS, 3, JubilifeCity_Arc2SetUpOutsideSchool
JubilifeCity_Arc2OnTransitionEnd:
    Return

// Cyrus stands alone in front of the dark Jubilife TV screen, his back to the plaza; Garius waits a few steps behind
// him (163,756), watching him. Walking into the plaza runs 2.1 (coord event on VAR_MAP_LOCAL_0x02 1, any entrance), so
// both are already on screen when it fires. The plaza is emptied for this load only (stock NPCs moved aside).
JubilifeCity_Arc2SetUpFindCyrus:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_20
    SetObjectEventPos LOCALID_ARC2_CYRUS, 164, 753
    SetObjectEventDir LOCALID_ARC2_CYRUS, DIR_NORTH
    SetObjectEventMovementType LOCALID_ARC2_CYRUS, MOVEMENT_TYPE_LOOK_NORTH
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    SetObjectEventPos LOCALID_ARC2_GARIUS, 163, 756
    SetObjectEventDir LOCALID_ARC2_GARIUS, DIR_NORTH
    SetObjectEventMovementType LOCALID_ARC2_GARIUS, MOVEMENT_TYPE_LOOK_NORTH
    SetObjectEventPos LOCALID_TWIN, 150, 761
    SetObjectEventPos LOCALID_ACE_TRAINER_M_1, 181, 760
    SetObjectEventPos LOCALID_ACE_TRAINER_M_2, 152, 768
    SetObjectEventPos LOCALID_CLOWN_3, 153, 760
    SetVar VAR_MAP_LOCAL_0x02, 1
    Return

// Cyrus waits by the school door with his new Poke Ball; Rowan and Ruth stand on either side
JubilifeCity_Arc2SetUpOutsideSchool:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_20
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_21
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_22
    SetObjectEventPos LOCALID_ARC2_CYRUS, 168, 779
    SetObjectEventDir LOCALID_ARC2_CYRUS, DIR_NORTH
    SetObjectEventMovementType LOCALID_ARC2_CYRUS, MOVEMENT_TYPE_LOOK_NORTH
    SetObjectEventPos LOCALID_ARC2_ROWAN, 166, 778
    SetObjectEventDir LOCALID_ARC2_ROWAN, DIR_EAST
    SetObjectEventMovementType LOCALID_ARC2_ROWAN, MOVEMENT_TYPE_LOOK_EAST
    SetObjectEventPos LOCALID_ARC2_RUTH, 170, 778
    SetObjectEventDir LOCALID_ARC2_RUTH, DIR_WEST
    SetObjectEventMovementType LOCALID_ARC2_RUTH, MOVEMENT_TYPE_LOOK_WEST
    SetVar VAR_MAP_LOCAL_0x02, 3
    Return

// The cast is only on screen during the scenes (the player is locked), so talking to them is never possible
JubilifeCity_Arc2Cast:
    End

// 2.1 (coord event, VAR_MAP_LOCAL_0x02 1): the player walks into the plaza. Garius spots them, the player is walked up
// beside him (165,756), and Cyrus, then Garius, walk off east and south toward the Trainers' School. No warp: the
// player keeps control at 1 and walks to the school, where 2.2 runs on entering.
JubilifeCity_Arc2FindCyrus:
    LockAll
    SetVar VAR_MAP_LOCAL_0x02, 0
    ClearFlag FLAG_ARC2_JUBILIFE_A
    ApplyMovement LOCALID_ARC2_GARIUS, JubilifeCity_Arc2Movement_Exclaim
    WaitMovement
    Call JubilifeCity_Arc2WalkUp
    ApplyMovement LOCALID_ARC2_GARIUS, JubilifeCity_Arc2Movement_TurnEast
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc2Movement_TurnWest
    WaitMovement
    BufferRivalName 0
    Message JubilifeCity_Text_Arc2GariusThereHeIs
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC2_GARIUS, JubilifeCity_Arc2Movement_TurnNorth
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc2Movement_TurnNorth
    WaitMovement
    WaitTime 20, VAR_RESULT
    Message JubilifeCity_Text_Arc2CyrusRowanSentYou
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC2_CYRUS, JubilifeCity_Arc2Movement_TurnSouth
    WaitMovement
    BufferRivalName 0
    Message JubilifeCity_Text_Arc2GariusLuckyUs
    WaitButton
    CloseMessage
    Message JubilifeCity_Text_Arc2CyrusRiftOpened
    WaitButton
    CloseMessage
    // Cyrus walks off the way the streets go to the Trainers' School: east along the plaza, then south
    ApplyMovement LOCALID_ARC2_CYRUS, JubilifeCity_Arc2Movement_CyrusLeavePlaza
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc2Movement_WatchCyrusLeavePlaza
    ApplyMovement LOCALID_ARC2_GARIUS, JubilifeCity_Arc2Movement_WatchCyrusLeavePlaza
    WaitMovement
    RemoveObject LOCALID_ARC2_CYRUS
    WaitTime 15, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc2Movement_TurnWest
    WaitMovement
    BufferRivalName 0
    Message JubilifeCity_Text_Arc2GariusGetProfessor
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC2_GARIUS, JubilifeCity_Arc2Movement_GariusLeavePlaza
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc2Movement_WatchGariusLeavePlaza
    WaitMovement
    RemoveObject LOCALID_ARC2_GARIUS
    SetVar VAR_ARC2_PROGRESS, 1
    ReleaseAll
    End

// Walks the player, one step at a time, from wherever they entered the plaza to (165,756), beside Garius (163,756)
// and three steps below Cyrus (164,753). South of row 756: along the row, then north. Row 756 east side: west. North
// of it: south first, stepping east out of the Cyrus/Garius columns (163-165) when in them.
JubilifeCity_Arc2WalkUp:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfGe VAR_0x8005, 757, JubilifeCity_Arc2WalkUpSouthSide
    GoToIfEq VAR_0x8005, 756, JubilifeCity_Arc2WalkUpRow
JubilifeCity_Arc2WalkUpNorthSide:
    GoToIfLt VAR_0x8004, 163, JubilifeCity_Arc2WalkUpStepSouth
    GoToIfGt VAR_0x8004, 165, JubilifeCity_Arc2WalkUpStepSouth
    GoTo JubilifeCity_Arc2WalkUpStepEast
JubilifeCity_Arc2WalkUpRow:
    GoToIfEq VAR_0x8004, 165, JubilifeCity_Arc2WalkUpDone
    GoToIfGt VAR_0x8004, 165, JubilifeCity_Arc2WalkUpStepWest
    GoToIfEq VAR_0x8004, 164, JubilifeCity_Arc2WalkUpStepEast
    GoTo JubilifeCity_Arc2WalkUpStepSouth
JubilifeCity_Arc2WalkUpSouthSide:
    GoToIfLt VAR_0x8004, 165, JubilifeCity_Arc2WalkUpStepEast
    GoToIfGt VAR_0x8004, 165, JubilifeCity_Arc2WalkUpStepWest
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc2Movement_StepNorth
    WaitMovement
    GoTo JubilifeCity_Arc2WalkUp
JubilifeCity_Arc2WalkUpStepSouth:
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc2Movement_StepSouth
    WaitMovement
    GoTo JubilifeCity_Arc2WalkUp
JubilifeCity_Arc2WalkUpStepEast:
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc2Movement_StepEast
    WaitMovement
    GoTo JubilifeCity_Arc2WalkUp
JubilifeCity_Arc2WalkUpStepWest:
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc2Movement_StepWest
    WaitMovement
    GoTo JubilifeCity_Arc2WalkUp
JubilifeCity_Arc2WalkUpDone:
    Return

// 2.3 (on frame, VAR_MAP_LOCAL_0x02 3): the player steps out of the school
JubilifeCity_Arc2OutsideSchool:
    LockAll
    SetVar VAR_MAP_LOCAL_0x02, 0
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc2Movement_TurnSouth
    WaitMovement
    Message JubilifeCity_Text_Arc2CyrusLongTime
    WaitButton
    CloseMessage
    // Cyrus holds the starter weak to the player's (the TRAINER_CYRUS_ARC2_1_* suffix is the player's starter).
    // StartFirstBattle: losing doesn't white out, as with Arc 1's first rival battle.
    GetPlayerStarterSpecies VAR_RESULT
    GoToIfEq VAR_RESULT, SPECIES_TURTWIG, JubilifeCity_Arc2CyrusBattleTurtwig
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, JubilifeCity_Arc2CyrusBattleChimchar
    GoTo JubilifeCity_Arc2CyrusBattlePiplup
    End

JubilifeCity_Arc2CyrusBattleTurtwig:
    StartFirstBattle TRAINER_CYRUS_ARC2_1_TURTWIG
    GoTo JubilifeCity_Arc2CyrusBattleEnd
    End

JubilifeCity_Arc2CyrusBattleChimchar:
    StartFirstBattle TRAINER_CYRUS_ARC2_1_CHIMCHAR
    GoTo JubilifeCity_Arc2CyrusBattleEnd
    End

JubilifeCity_Arc2CyrusBattlePiplup:
    StartFirstBattle TRAINER_CYRUS_ARC2_1_PIPLUP
    GoTo JubilifeCity_Arc2CyrusBattleEnd
    End

JubilifeCity_Arc2CyrusBattleEnd:
    CheckWonBattle VAR_RESULT
    CallIfEq VAR_RESULT, FALSE, JubilifeCity_Arc2CyrusBattleLost
    SetVar VAR_ARC2_PROGRESS, 5
    Message JubilifeCity_Text_Arc2CyrusItListened
    WaitButton
    CloseMessage
    WaitTime 15, VAR_RESULT
    Message JubilifeCity_Text_Arc2CyrusMeetYouThere
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_ARC2_CYRUS, JubilifeCity_Arc2Movement_CyrusLeaveSchool
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc2Movement_PlayerWatchCyrusEast
    WaitMovement
    RemoveObject LOCALID_ARC2_CYRUS
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc2Movement_TurnWest
    ApplyMovement LOCALID_ARC2_RUTH, JubilifeCity_Arc2Movement_TurnWest
    WaitMovement
    Message JubilifeCity_Text_Arc2RowanRuthWillGo
    WaitButton
    CloseMessage
    GoTo JubilifeCity_Arc2GoToCutaway
    End

// A loss: the field comes back by itself, as after Arc 1's first rival battle
JubilifeCity_Arc2CyrusBattleLost:
    ReturnToField
    FadeScreenIn
    WaitFadeScreen
    HealParty
    Return

// Hand-off to the 2.4 cutaway (lead's caller contract): progress is already 5; fade to black, warp into the violet room
// (MAP_HEADER_GALACTIC_HQ_CONTROL_ROOM, 8, 9, north), ReleaseAll/End with no FadeScreenIn. s-cutaways plays 2.4,
// sets 9 and returns the player here: Jubilife (168,777), outside the school, facing south.
// ARC2_CUTAWAY_2_4_WIRED (top of this section) stays 0 until s-cutaways is merged: the cutaway is then skipped
// (fade, set 9, the player stays put). The lead sets it to 1 at merge.
JubilifeCity_Arc2GoToCutaway:
    FadeScreenOut
    WaitFadeScreen
#if ARC2_CUTAWAY_2_4_WIRED
    Warp MAP_HEADER_GALACTIC_HQ_CONTROL_ROOM, 8, 9, DIR_NORTH
    ReleaseAll
    End
#else
    RemoveObject LOCALID_ARC2_ROWAN
    RemoveObject LOCALID_ARC2_RUTH
    SetVar VAR_ARC2_PROGRESS, 9
    SetPosition LOCALID_PLAYER, 168, 0, 777, DIR_SOUTH
    WaitTime 30, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End
#endif

// 9-19: the Expert near the school (stock JubilifeCity_ExpertM1) noticed the night class
JubilifeCity_Arc2TeachingAfterHours:
    Message JubilifeCity_Text_Arc2TeachingAfterHours
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
JubilifeCity_Arc2Movement_WalkNorth3:
    WalkNormalNorth 3
    EndMovement

    .balign 4, 0
JubilifeCity_Arc2Movement_Exclaim:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
JubilifeCity_Arc2Movement_TurnSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc2Movement_TurnWest:
    FaceWest
    EndMovement

    .balign 4, 0
JubilifeCity_Arc2Movement_TurnEast:
    FaceEast
    EndMovement

    .balign 4, 0
JubilifeCity_Arc2Movement_TurnNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc2Movement_StepNorth:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc2Movement_StepSouth:
    WalkNormalSouth
    EndMovement

    .balign 4, 0
JubilifeCity_Arc2Movement_StepEast:
    WalkNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_Arc2Movement_StepWest:
    WalkNormalWest
    EndMovement

    // From the TV screen (164,753): east along row 753 to the avenue (172), then south down it toward the Trainers'
    // School (door 168,776), out of sight at (172,763). Row 753 and column 172 are open street.
    .balign 4, 0
JubilifeCity_Arc2Movement_CyrusLeavePlaza:
    WalkNormalEast 8
    WalkNormalSouth 10
    EndMovement

    .balign 4, 0
JubilifeCity_Arc2Movement_WatchCyrusLeavePlaza:
    Delay16 3
    FaceEast
    EndMovement

    // Garius (163,756) follows: south one, east along row 757 (under the player at 165,756), then down the avenue
    .balign 4, 0
JubilifeCity_Arc2Movement_GariusLeavePlaza:
    WalkNormalSouth
    WalkNormalEast 9
    WalkNormalSouth 6
    EndMovement

    .balign 4, 0
JubilifeCity_Arc2Movement_WatchGariusLeavePlaza:
    Delay8
    FaceSouth
    Delay16 2
    FaceEast
    EndMovement

    // From (168,779): east along row 779 (south of Ruth at 170,778) to the avenue, then north up it toward Route 204.
    // Column 172 is open street all the way up; the old path went up column 171 and through the street lamp at the
    // school's corner (171,775, a blocked tile).
    .balign 4, 0
JubilifeCity_Arc2Movement_CyrusLeaveSchool:
    WalkNormalEast 4
    WalkNormalNorth 12
    EndMovement

    .balign 4, 0
JubilifeCity_Arc2Movement_PlayerWatchCyrusEast:
    Delay16 2
    FaceEast
    Delay16 5
    FaceNorth
    EndMovement

JubilifeCity_QuestsOnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_23
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_24
    GoToIfLt VAR_ARC1_PROGRESS, 16, JubilifeCity_QuestsReturn
    GoToIfLt VAR_ARC2_PROGRESS, 9, JubilifeCity_QuestsReturn
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_23
    GoToIfUnset FLAG_QUESTS_DUCHESS_HOME, JubilifeCity_QuestsReturn
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_24
JubilifeCity_QuestsReturn:
    Return

JubilifeCity_QuestsOldMan:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_QUESTS_DUCHESS_HOME, JubilifeCity_QuestsOldManAfter
    GoToIfSet FLAG_QUESTS_DUCHESS_CARRIED, JubilifeCity_QuestsReunion
    Message JubilifeCity_Text_QuestsOldManHaven
    WaitButton
    CloseMessage
    ReleaseAll
    End

// Duchess comes out from behind the player and runs to the old man's free side: west of him (157,758), or east
// (159,758) when the player stands on the west tile.
JubilifeCity_QuestsReunion:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    SetVar VAR_0x8006, 157
    GoToIfNe VAR_0x8004, 157, JubilifeCity_QuestsReunionPlace
    SetVar VAR_0x8006, 159
JubilifeCity_QuestsReunionPlace:
    SetObjectEventPos LOCALID_QUESTS_DUCHESS, VAR_0x8006, 758
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_24
    AddObject LOCALID_QUESTS_DUCHESS
    PlayCry SPECIES_CLEFAIRY
    Message JubilifeCity_Text_QuestsOldManDuchess
    WaitCry
    WaitButton
    CloseMessage
    CallIfEq VAR_0x8006, 157, JubilifeCity_QuestsOldManFaceWest
    CallIfEq VAR_0x8006, 159, JubilifeCity_QuestsOldManFaceEast
    Message JubilifeCity_Text_QuestsDuchessCry
    WaitButton
    Message JubilifeCity_Text_QuestsOldManTheyTold
    WaitButton
    Message JubilifeCity_Text_QuestsOldManNeverAsked
    WaitButton
    Message JubilifeCity_Text_QuestsOldManComeHome
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_QUESTS_DUCHESS, JubilifeCity_QuestsMovement_DuchessHop
    WaitMovement
    PlayCry SPECIES_CLEFAIRY
    Message JubilifeCity_Text_QuestsDuchessYes
    WaitCry
    WaitButton
    SetFlag FLAG_QUESTS_DUCHESS_HOME
    ApplyMovement LOCALID_QUESTS_OLD_MAN, JubilifeCity_QuestsMovement_FacePlayerSouth
    WaitMovement
    FacePlayer
    Message JubilifeCity_Text_QuestsOldManThankYou
    WaitButton
    GoTo JubilifeCity_QuestsGiveMoonStone
    End

JubilifeCity_QuestsOldManFaceWest:
    ApplyMovement LOCALID_QUESTS_OLD_MAN, JubilifeCity_QuestsMovement_FaceWest
    ApplyMovement LOCALID_QUESTS_DUCHESS, JubilifeCity_QuestsMovement_FaceEast
    WaitMovement
    Return

JubilifeCity_QuestsOldManFaceEast:
    ApplyMovement LOCALID_QUESTS_OLD_MAN, JubilifeCity_QuestsMovement_FaceEast
    ApplyMovement LOCALID_QUESTS_DUCHESS, JubilifeCity_QuestsMovement_FaceWest
    WaitMovement
    Return

JubilifeCity_QuestsGiveMoonStone:
    Message JubilifeCity_Text_QuestsOldManMoonStone
    SetVar VAR_0x8004, ITEM_MOON_STONE
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, JubilifeCity_QuestsBagFull
    SetFlag FLAG_QUESTS_MOON_STONE
    CallCommonScript CommonScript_AddItemQuantityNoLineFeed
    CloseMessage
    ReleaseAll
    End

JubilifeCity_QuestsBagFull:
    Message JubilifeCity_Text_QuestsOldManBagFull
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_QuestsOldManAfter:
    GoToIfUnset FLAG_QUESTS_MOON_STONE, JubilifeCity_QuestsGiveMoonStone
    Message JubilifeCity_Text_QuestsOldManBeside
    WaitButton
    CloseMessage
    ReleaseAll
    End

JubilifeCity_QuestsDuchess:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    PlayCry SPECIES_CLEFAIRY
    Message JubilifeCity_Text_QuestsDuchessStays
    WaitCry
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
JubilifeCity_QuestsMovement_FaceWest:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
JubilifeCity_QuestsMovement_FaceEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
JubilifeCity_QuestsMovement_FacePlayerSouth:
    Delay8
    EndMovement

    .balign 4, 0
JubilifeCity_QuestsMovement_DuchessHop:
    JumpOnSpotFastNorth
    JumpOnSpotFastNorth
    EndMovement
