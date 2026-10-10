#include "macros/scrcmd.inc"
#include "res/text/bank/jubilife_city.h"
#include "res/field/events/events_jubilife_city.h"


    ScriptEntry _0072
    ScriptEntry JubilifeCity_Counterpart
    ScriptEntry _0700
    ScriptEntry _09DC
    ScriptEntry _0954
    ScriptEntry _0F3C
    ScriptEntry _0FAD
    ScriptEntry _0FD3
    ScriptEntry _1027
    ScriptEntry _0FC0
    ScriptEntry _0FE6
    ScriptEntry _058C
    ScriptEntry _05BD
    ScriptEntry _1320
    ScriptEntry _1397
    ScriptEntry _140E
    ScriptEntry _10C4
    ScriptEntry _11CC
    ScriptEntry JubilifeCity_GTSGreeter_HasNoBadges
    ScriptEntry _14A9
    ScriptEntry _14BC
    ScriptEntry _103A
    ScriptEntry _1051
    ScriptEntry _1068
    ScriptEntry _107F
    ScriptEntry _1096
    ScriptEntry _10AD
    ScriptEntry JubilifeCity_Looker_AfterOneBadgeObtained
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
    ScriptEntry JubilifeCity_Arc1CrowdEveryWeek
    ScriptEntry JubilifeCity_Arc1CrowdMomAskedMe
    ScriptEntryEnd

_0072:
    // Dazzling Platinum Arc 1: object LOCALID_ARC1_SAROS is never shown (Saros is only a voice on the TV,
    // playtest bug 11). Its events slot is kept so the crowd's local IDs (and saves made in Jubilife) don't
    // shift, and its hide flag is set at every load because a new game starts with it clear. The rally cast and
    // crowd follow VAR_ARC1_PROGRESS. From 12 on, the stock state 0/1 chain is skipped before the stock checks.
    SetFlag FLAG_HIDE_ARC1_JUBILIFE_SAROS
    CallIfLt VAR_ARC1_PROGRESS, 12, JubilifeCity_Arc1HideRally
    CallIfGe VAR_ARC1_PROGRESS, 12, JubilifeCity_Arc1OnTransition
    CallIfEq VAR_JUBILIFE_STATE, 0, _00AC
    CallIfGe VAR_JUBILIFE_STATE, 3, _00C2
    GetPlayerGender VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, GENDER_MALE, _00D8
    GoToIfEq VAR_MAP_LOCAL_0, GENDER_FEMALE, _00E0
    End

_00AC:
    SetObjectEventPos 31, 177, 0x306
    SetObjectEventDir 31, DIR_SOUTH
    SetObjectEventMovementType 31, MOVEMENT_TYPE_LOOK_SOUTH
    Return

_00C2:
    SetObjectEventPos 7, 176, 0x2E3
    SetObjectEventDir 7, DIR_WEST
    SetObjectEventMovementType 7, MOVEMENT_TYPE_LOOK_WEST
    Return

_00D8:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    End

_00E0:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    End

JubilifeCity_Counterpart:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8004, 173, JubilifeCity_Counterpart_Left
    GoToIfEq VAR_0x8004, 174, JubilifeCity_Counterpart_Middle
    GoToIfEq VAR_0x8004, 175, JubilifeCity_Counterpart_Right
    End

JubilifeCity_Counterpart_Left:
    SetObjectEventPos JUBILIFE_CITY_COUNTERPART, 173, 0x314
    GoTo JubilifeCity_Counterpart_Init
    End

JubilifeCity_Counterpart_Middle:
    SetObjectEventPos JUBILIFE_CITY_COUNTERPART, 174, 0x314
    GoTo JubilifeCity_Counterpart_Init
    End

JubilifeCity_Counterpart_Right:
    SetObjectEventPos JUBILIFE_CITY_COUNTERPART, 175, 0x314
    GoTo JubilifeCity_Counterpart_Init
    End

JubilifeCity_Counterpart_Init:
    ClearFlag FLAG_HIDE_JUBILIFE_COUNTERPART
    AddObject JUBILIFE_CITY_COUNTERPART
    LockObject JUBILIFE_CITY_COUNTERPART
    ApplyMovement JUBILIFE_CITY_COUNTERPART, _043C
    WaitMovement
    ApplyMovement JUBILIFE_CITY_COUNTERPART, _044C
    WaitMovement
    SetCounterpartBGM
    GetPlayerGender VAR_RESULT
    GoToIfEq VAR_RESULT, GENDER_MALE, JubilifeCity_Dawn
    GoToIfEq VAR_RESULT, GENDER_FEMALE, JubilifeCity_Lucas
    End

JubilifeCity_Dawn:
    BufferCounterpartName 0
    BufferPlayerName 1
    Message 0
    GetPartyCount VAR_RESULT
    BufferNumber 0, VAR_RESULT
    CallIfGe VAR_RESULT, 4, JubilifeCity_Dawn_AtLeast4Mon
    CallIfLe VAR_RESULT, 3, JubilifeCity_Dawn_LessThan4Mon
    BufferPlayerName 0
    BufferRivalName 1
    Message 3
    Call _02DB
    Message 8
    CloseMessage
    Call _0348
    Message 9
    Call _036E
    Message 14
    Call _0390
    Call _03C0
    Message 23
    CloseMessage
    WaitTime 30, VAR_RESULT
    BufferPlayerName 0
    Call _041B
    Message 24
    CloseMessage
    BufferRivalName 1
    Call _042F
    Message 25
    CloseMessage
    GoTo _02BB
    End

JubilifeCity_Dawn_AtLeast4Mon:
    Message 1
    Return

JubilifeCity_Dawn_LessThan4Mon:
    Message 2
    Return

JubilifeCity_Lucas:
    BufferCounterpartName 0
    BufferPlayerName 1
    Message 4
    GetPartyCount VAR_RESULT
    BufferNumber 0, VAR_RESULT
    CallIfGe VAR_RESULT, 4, JubilifeCity_Lucas_AtLeast4Mon
    CallIfLe VAR_RESULT, 3, JubilifeCity_Lucas_LessThan4Mon
    BufferPlayerName 0
    BufferRivalName 1
    Message 7
    Call _02DB
    Message 10
    CloseMessage
    Call _0348
    Message 11
    Call _036E
    Message 15
    Call _0390
    Call _03C0
    Message 26
    CloseMessage
    WaitTime 15, VAR_RESULT
    BufferPlayerName 0
    Call _041B
    Message 27
    CloseMessage
    BufferRivalName 1
    Call _042F
    Message 28
    CloseMessage
    GoTo _02BB
    End

JubilifeCity_Lucas_AtLeast4Mon:
    Message 5
    Return

JubilifeCity_Lucas_LessThan4Mon:
    Message 6
    Return

_02BB:
    ApplyMovement 7, _0474
    ApplyMovement LOCALID_PLAYER, _04F8
    WaitMovement
    RemoveObject 7
    SetVar VAR_JUBILIFE_STATE, 1
    ReleaseAll
    End

_02DB:
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8004, 173, _030C
    GoToIfEq VAR_0x8004, 174, _0320
    GoToIfEq VAR_0x8004, 175, _0334
    End

_030C:
    ApplyMovement 7, _0454
    ApplyMovement LOCALID_PLAYER, _04B4
    WaitMovement
    Return

_0320:
    ApplyMovement 7, _046C
    ApplyMovement LOCALID_PLAYER, _04D4
    WaitMovement
    Return

_0334:
    ApplyMovement 7, _0460
    ApplyMovement LOCALID_PLAYER, _04C4
    WaitMovement
    Return

_0348:
    ApplyMovement 31, _0518
    WaitMovement
    ApplyMovement 31, _0544
    ApplyMovement 7, _047C
    ApplyMovement LOCALID_PLAYER, _04DC
    WaitMovement
    Return

_036E:
    ApplyMovement 31, _0550
    WaitMovement
    SetLookerBGM
    Message 12
    Message 13
    CloseMessage
    ApplyMovement 7, _0484
    WaitMovement
    Return

_0390:
    Message 16
    Message 17
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _03B6
    GoToIfEq VAR_RESULT, MENU_NO, _03BB
    End

_03B6:
    Message 18
    Return

_03BB:
    Message 19
    Return

_03C0:
    Message 20
    SetVar VAR_0x8004, ITEM_VS_RECORDER
    SetVar VAR_0x8005, 1
    GiveItemQuantity
    Message 21
    CloseMessage
    ApplyMovement 31, _055C
    WaitMovement
    Message 22
    CloseMessage
    ApplyMovement 7, _04A4
    ApplyMovement LOCALID_PLAYER, _0504
    ApplyMovement 31, _0574
    WaitMovement
    SetPosition 31, 186, 0, 0x2F4, 1
    SetObjectEventPos 31, 186, 0x2F4
    FadeToDefaultMusic4
    Return

_041B:
    ApplyMovement 7, _048C
    ApplyMovement LOCALID_PLAYER, _04EC
    WaitMovement
    Return

_042F:
    ApplyMovement 7, _0498
    WaitMovement
    Return

    .balign 4, 0
_043C:
    WalkNormalSouth 4
    EmoteExclamationMark
    Delay16
    EndMovement

    .balign 4, 0
_044C:
    WalkNormalSouth 3
    EndMovement

    .balign 4, 0
_0454:
    WalkNormalEast
    WalkNormalNorth 18
    EndMovement

    .balign 4, 0
_0460:
    WalkNormalWest
    WalkNormalNorth 18
    EndMovement

    .balign 4, 0
_046C:
    WalkNormalNorth 18
    EndMovement

    .balign 4, 0
_0474:
    WalkNormalSouth 9
    EndMovement

    .balign 4, 0
_047C:
    WalkNormalNorth 2
    EndMovement

    .balign 4, 0
_0484:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_048C:
    WalkNormalSouth
    WalkNormalWest 2
    EndMovement

    .balign 4, 0
_0498:
    WalkNormalNorth
    WalkNormalEast 2
    EndMovement

    .balign 4, 0
_04A4:
    WalkOnSpotNormalEast
    Delay8 4
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_04B4:
    WalkNormalNorth
    WalkNormalEast
    WalkNormalNorth 17
    EndMovement

    .balign 4, 0
_04C4:
    WalkNormalNorth
    WalkNormalWest
    WalkNormalNorth 17
    EndMovement

    .balign 4, 0
_04D4:
    WalkNormalNorth 18
    EndMovement

    .balign 4, 0
_04DC:
    WalkNormalNorth 2
    WalkNormalEast
    WalkNormalNorth
    EndMovement

    .balign 4, 0
_04EC:
    Delay4
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_04F8:
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0504:
    Delay8
    WalkOnSpotNormalEast
    Delay8 3
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0518:
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
_0544:
    WalkSlowEast
    WalkFastEast 2
    EndMovement

    .balign 4, 0
_0550:
    WalkOnSpotFastSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_055C:
    WalkOnSpotFastWest
    Delay8
    WalkOnSpotFastEast
    Delay8 2
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
_0574:
    WalkFastEast 3
    WalkOnSpotFastWest
    Delay8
    WalkSlowNorth
    WalkFastNorth 7
    EndMovement

_058C:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfBadgeAcquired BADGE_ID_COAL, _05B2
    Message 29
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_05B2:
    Message 30
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_05BD:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 92
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

JubilifeCity_GTSGreeter_HasNoBadges:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 779, _0601
    GoToIfEq VAR_0x8005, 780, _062A
    GoToIfEq VAR_0x8005, 781, _0653
    End

_0601:
    ApplyMovement 26, _0680
    WaitMovement
    Message 91
    CloseMessage
    ApplyMovement 26, _06B0
    ApplyMovement LOCALID_PLAYER, _06F8
    WaitMovement
    GoTo _067C
    End

_062A:
    ApplyMovement 26, _0690
    WaitMovement
    Message 91
    CloseMessage
    ApplyMovement 26, _06C8
    ApplyMovement LOCALID_PLAYER, _06F8
    WaitMovement
    GoTo _067C
    End

_0653:
    ApplyMovement 26, _06A0
    WaitMovement
    Message 91
    CloseMessage
    ApplyMovement 26, _06E0
    ApplyMovement LOCALID_PLAYER, _06F8
    WaitMovement
    GoTo _067C
    End

_067C:
    ReleaseAll
    End

    .balign 4, 0
_0680:
    EmoteExclamationMark
    WalkNormalSouth
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0690:
    EmoteExclamationMark
    WalkNormalSouth 2
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_06A0:
    EmoteExclamationMark
    WalkNormalSouth 3
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_06B0:
    WalkNormalEast
    Delay8 2
    WalkNormalWest
    WalkNormalNorth
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_06C8:
    WalkNormalEast
    Delay8 2
    WalkNormalWest
    WalkNormalNorth 2
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_06E0:
    WalkNormalEast
    Delay8 2
    WalkNormalWest
    WalkNormalNorth 3
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_06F8:
    WalkNormalEast
    EndMovement

_0700:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 0x2F5, _073E
    GoToIfEq VAR_0x8005, 0x2F6, _0758
    GoToIfEq VAR_0x8005, 0x2F7, _0772
    GoToIfEq VAR_0x8005, 0x2F8, _078C
    End

_073E:
    ApplyMovement LOCALID_PLAYER, _0894
    ApplyMovement 31, _08B4
    WaitMovement
    GoTo _07A6
    End

_0758:
    ApplyMovement LOCALID_PLAYER, _0894
    ApplyMovement 31, _08CC
    WaitMovement
    GoTo _07A6
    End

_0772:
    ApplyMovement LOCALID_PLAYER, _0894
    ApplyMovement 31, _08E4
    WaitMovement
    GoTo _07A6
    End

_078C:
    ApplyMovement LOCALID_PLAYER, _0894
    ApplyMovement 31, _08FC
    WaitMovement
    GoTo _07A6
    End

_07A6:
    Call _07FC
    CloseMessage
    ApplyMovement LOCALID_PLAYER, _08AC
    ApplyMovement 31, _0914
    WaitMovement
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 0x2F5, _0846
    GoToIfEq VAR_0x8005, 0x2F6, _0858
    GoToIfEq VAR_0x8005, 0x2F7, _086A
    GoToIfEq VAR_0x8005, 0x2F8, _087C
    End

_07FC:
    GoToIfUnset FLAG_UNK_0x00F1, _0817
    GoToIfUnset FLAG_UNK_0x00F3, _081C
    Message 35
    Return

_0817:
    Message 32
    Return

_081C:
    Message 34
    Return

_0821:
    GoToIfUnset FLAG_UNK_0x00F1, _083C
    GoToIfUnset FLAG_UNK_0x00F3, _0841
    Message 35
    Return

_083C:
    Message 31
    Return

_0841:
    Message 33
    Return

_0846:
    ApplyMovement 31, _0924
    WaitMovement
    GoTo _088E
    End

_0858:
    ApplyMovement 31, _0930
    WaitMovement
    GoTo _088E
    End

_086A:
    ApplyMovement 31, _093C
    WaitMovement
    GoTo _088E
    End

_087C:
    ApplyMovement 31, _0948
    WaitMovement
    GoTo _088E
    End

_088E:
    ReleaseAll
    End

    .balign 4, 0
_0894:
    Delay8 5
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_08A0:
    Delay8 5
    FaceWest
    EndMovement

    .balign 4, 0
_08AC:
    WalkNormalWest
    EndMovement

    .balign 4, 0
_08B4:
    FaceSouth
    EmoteExclamationMark
    Delay16
    WalkNormalSouth
    WalkNormalEast
    EndMovement

    .balign 4, 0
_08CC:
    FaceSouth
    EmoteExclamationMark
    Delay16
    WalkNormalSouth 2
    WalkNormalEast
    EndMovement

    .balign 4, 0
_08E4:
    FaceSouth
    EmoteExclamationMark
    Delay16
    WalkNormalSouth 3
    WalkNormalEast
    EndMovement

    .balign 4, 0
_08FC:
    FaceSouth
    EmoteExclamationMark
    Delay16
    WalkNormalSouth 4
    WalkNormalEast
    EndMovement

    .balign 4, 0
_0914:
    LockDir
    WalkNormalWest
    UnlockDir
    EndMovement

    .balign 4, 0
_0924:
    WalkNormalNorth
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0930:
    WalkNormalNorth 2
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_093C:
    WalkNormalNorth 3
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0948:
    WalkNormalNorth 4
    WalkOnSpotNormalSouth
    EndMovement

_0954:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfInRange VAR_ARC1_PROGRESS, 12, 13, JubilifeCity_Arc1TrenchCoat
    GoToIfSet FLAG_UNK_0x00F3, _097F
    Call _0821
    WaitABPress
    CloseMessage
    ApplyMovement 31, _09D4
    WaitMovement
    ReleaseAll
    End

_097F:
    Message 35
    WaitABPress
    CloseMessage
    ApplyMovement 31, _09D4
    WaitMovement
    ReleaseAll
    End

JubilifeCity_Looker_PalPadCheck:
    CheckItem ITEM_PAL_PAD, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, 1, _09BD
    Message 36
    CloseMessage
    ApplyMovement 31, _1558
    WaitMovement
    Message 38
    Return

_09BD:
    Message 37
    CloseMessage
    ApplyMovement 31, _1558
    WaitMovement
    Message 38
    Return

    .balign 4, 0
_09D4:
    FaceSouth
    EndMovement

_09DC:
    LockAll
    ApplyMovement 18, _0E94
    WaitMovement
    Message 64
    CloseMessage
    GetPlayerMapPos VAR_0x8000, VAR_0x8001
    GoToIfEq VAR_0x8000, 173, _0A1C
    GoToIfEq VAR_0x8000, 174, _0A36
    GoToIfEq VAR_0x8000, 175, _0A50
    End

_0A1C:
    ApplyMovement 16, _0EBC
    ApplyMovement LOCALID_PLAYER, _0DD0
    WaitMovement
    GoTo _0A6A
    End

_0A36:
    ApplyMovement 16, _0EBC
    ApplyMovement LOCALID_PLAYER, _0DE4
    WaitMovement
    GoTo _0A6A
    End

_0A50:
    ApplyMovement 16, _0EBC
    ApplyMovement LOCALID_PLAYER, _0DF8
    WaitMovement
    GoTo _0A6A
    End

_0A6A:
    BufferPlayerName 0
    BufferCounterpartName 1
    Message 65
    ApplyMovement 18, _0E94
    WaitMovement
    Message 66
    ApplyMovement 16, _0EC8
    WaitMovement
    Message 67
    ApplyMovement 16, _0ED0
    WaitMovement
    Message 68
    ApplyMovement 17, _0E9C
    ApplyMovement 18, _0E9C
    WaitMovement
    Message 69
    Message 70
    ApplyMovement 7, _0E44
    WaitMovement
    GetPlayerGender VAR_RESULT
    GoToIfEq VAR_RESULT, GENDER_MALE, _0ADC
    GoToIfEq VAR_RESULT, GENDER_FEMALE, _0AED
    End

_0ADC:
    BufferCounterpartName 0
    BufferPlayerName 1
    Message 71
    GoTo _0AFE
    End

_0AED:
    BufferCounterpartName 0
    BufferPlayerName 1
    Message 72
    GoTo _0AFE
    End

_0AFE:
    CloseMessage
    ApplyMovement 16, _0F00
    WaitMovement
    ApplyMovement 7, _0E4C
    ApplyMovement LOCALID_PLAYER, _0F30
    WaitMovement
    Call JubilifeCity_SetPlayerCounterpartPartnerTeam
    StartTagBattle VAR_0x8004, TRAINER_GALACTIC_GRUNT_JUBILIFE_CITY_1, TRAINER_GALACTIC_GRUNT_JUBILIFE_CITY_2
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _0DB7
    ApplyMovement 18, _0EB4
    WaitMovement
    Message 73
    CloseMessage
    ApplyMovement 17, _0EA4
    ApplyMovement 18, _0EAC
    WaitMovement
    RemoveObject 17
    RemoveObject 18
    SetFlag FLAG_HIDE_JUBILIFE_GALACTIC_GRUNTS
    ApplyMovement 16, _0EF8
    ApplyMovement 7, _0E54
    WaitMovement
    BufferPlayerName 0
    Message 74
    ApplyMovement 7, _0E60
    WaitMovement
    GetPlayerGender VAR_RESULT
    GoToIfEq VAR_RESULT, GENDER_MALE, _0C30
    GoToIfEq VAR_RESULT, GENDER_FEMALE, _0C41
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

_0C30:
    BufferCounterpartName 0
    BufferPlayerName 1
    Message 75
    GoTo _0C52
    End

_0C41:
    BufferCounterpartName 0
    BufferPlayerName 1
    Message 76
    GoTo _0C52
    End

_0C52:
    BufferPlayerName 0
    Message 77
    CloseMessage
    ApplyMovement 7, _0E68
    ApplyMovement 16, _0ED8
    ApplyMovement LOCALID_PLAYER, _0E08
    WaitMovement
    GoTo _0C7C
    End

_0C7C:
    RemoveObject 7
    RemoveObject 16
    ClearFlag FLAG_UNK_0x0198
    SetVar VAR_JUBILIFE_STATE, 4
    SetVar VAR_JUBILIFE_LOOKER_PALPAD, 2
    SetVar VAR_OREBURGH_STATE, 3
    RemoveObject 24
    RemoveObject 25
    RemoveObject 27
    SetObjectEventPos 30, 174, 0x2EE
    SetObjectEventMovementType 30, MOVEMENT_TYPE_LOOK_NORTH
    ClearFlag FLAG_UNK_0x018B
    AddObject 30
    LockObject 30
    ApplyMovement 30, _0DC0
    WaitMovement
    Message 78
    Call _0CF0
    Message 79
    CloseMessage
    WaitTime 15, VAR_RESULT
    ApplyMovement 30, _0DC8
    WaitMovement
    RemoveObject 30
    ReleaseAll
    End

_0CF0:
    SetVar VAR_0x8004, ITEM_FASHION_CASE
    SetVar VAR_0x8005, 1
    GiveItemQuantity
    SetFlag FLAG_UNK_0x00F2
    Call _0D58
    Call _0D58
    Call _0D58
    Call _0D58
    Call _0D58
    Call _0D72
    Call _0D72
    Call _0D72
    Call _0D72
    Call _0D72
    AddContestBackdrop 0
    SetVar VAR_MAP_LOCAL_1, 0x270F
    Call _0D8C
    Call _0D8C
    Return

_0D58:
    GetRandom VAR_RESULT, 6
    SetVar VAR_0x8004, 0
    AddVar VAR_0x8004, VAR_RESULT
    AddAccessory VAR_0x8004, 1
    Return

_0D72:
    GetRandom VAR_RESULT, 6
    SetVar VAR_0x8004, 18
    AddVar VAR_0x8004, VAR_RESULT
    AddAccessory VAR_0x8004, 1
    Return

_0D8C:
    GetRandom VAR_RESULT, 8
    GoToIfEq VAR_MAP_LOCAL_1, VAR_RESULT, _0D8C
    SetVar VAR_MAP_LOCAL_1, VAR_RESULT
    SetVar VAR_0x8004, 1
    AddVar VAR_0x8004, VAR_RESULT
    AddContestBackdrop VAR_0x8004
    Return

_0DB7:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
_0DC0:
    WalkNormalNorth 8
    EndMovement

    .balign 4, 0
_0DC8:
    WalkNormalSouth 8
    EndMovement

    .balign 4, 0
_0DD0:
    Delay8 2
    WalkNormalNorth
    WalkNormalEast 2
    WalkNormalNorth
    EndMovement

    .balign 4, 0
_0DE4:
    Delay8 2
    WalkNormalNorth
    WalkNormalEast
    WalkNormalNorth
    EndMovement

    .balign 4, 0
_0DF8:
    Delay8 2
    WalkNormalNorth 2
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0E08:
    Delay8
    WalkOnSpotNormalEast
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

JubilifeCity_UnusedMovement:
    Delay8
    WalkOnSpotNormalEast
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

JubilifeCity_UnusedMovement2:
    Delay8
    WalkOnSpotNormalWest
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0E44:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0E4C:
    WalkNormalWest
    EndMovement

    .balign 4, 0
_0E54:
    WalkNormalWest
    WalkNormalSouth
    EndMovement

    .balign 4, 0
_0E60:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0E68:
    WalkNormalEast
    WalkNormalSouth 9
    EndMovement

JubilifeCity_UnusedMovement3:
    WalkNormalEast
    WalkNormalSouth 9
    EndMovement

JubilifeCity_UnusedMovement4:
    WalkNormalWest
    WalkOnSpotNormalEast
    WalkNormalEast
    WalkNormalSouth 9
    EndMovement

    .balign 4, 0
_0E94:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0E9C:
    WalkOnSpotFastEast 2
    EndMovement

    .balign 4, 0
_0EA4:
    WalkFastNorth 9
    EndMovement

    .balign 4, 0
_0EAC:
    WalkFastNorth 10
    EndMovement

    .balign 4, 0
_0EB4:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0EBC:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_0EC8:
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
_0ED0:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0ED8:
    WalkNormalSouth 9
    EndMovement

JubilifeCity_UnusedMovement5:
    WalkNormalSouth 9
    EndMovement

JubilifeCity_UnusedMovement6:
    WalkOnSpotNormalWest
    WalkNormalWest
    WalkNormalSouth 9
    EndMovement

    .balign 4, 0
_0EF8:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0F00:
    WalkOnSpotNormalWest
    EndMovement

JubilifeCity_UnusedMovement7:
    WalkOnSpotNormalWest
    EndMovement

JubilifeCity_UnusedMovement8:
    WalkOnSpotNormalWest
    EndMovement

JubilifeCity_UnusedMovement9:
    WalkOnSpotNormalWest
    EndMovement

JubilifeCity_UnusedMovement10:
    WalkOnSpotNormalWest
    EndMovement
    
JubilifeCity_UnusedMovement11:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0F30:
    WalkNormalWest
    WalkOnSpotNormalNorth
    EndMovement

_0F3C:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 80
    InitGlobalTextListMenu 29, 11, 0, VAR_RESULT, NO_EXIT_ON_B
    SetMenuXOriginToRight
    AddListMenuEntry 45, 0
    AddListMenuEntry 46, 1
    AddListMenuEntry 47, 2
    ShowListMenu
    SetVar VAR_0x8008, VAR_RESULT
    GoToIfEq VAR_0x8008, 0, _0F97
    GoToIfEq VAR_0x8008, 1, _0FA2
    Message 83
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0F97:
    Message 81
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0FA2:
    Message 82
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0FAD:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 84
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0FC0:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 87
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0FD3:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 85
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0FE6:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 88
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _1011
    GoToIfEq VAR_RESULT, MENU_NO, _101C
    End

_1011:
    Message 89
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_101C:
    Message 90
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_1027:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 86
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_103A:
    ShowMapSign 95
    End

_1051:
    ShowLandmarkSign 96
    End

_1068:
    ShowLandmarkSign 97
    End

_107F:
    ShowLandmarkSign 98
    End

_1096:
    GoToIfInRange VAR_ARC1_PROGRESS, 12, 13, JubilifeCity_Arc1Banner
    ShowLandmarkSign 99
    End

_10AD:
    ShowLandmarkSign 100
    End

_10C4:
    LockAll
    ApplyMovement 23, _1178
    ApplyMovement LOCALID_PLAYER, _1170
    WaitMovement
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 172, _1133
    CallIfEq VAR_0x8004, 173, _113F
    CallIfEq VAR_0x8004, 174, _114B
    CallIfEq VAR_0x8004, 175, _1157
    CallIfEq VAR_0x8004, 176, _1163
    Message 39
    SetVar VAR_UNK_0x40E7, 2
    Message 40
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_1133:
    ApplyMovement 23, _1184
    WaitMovement
    Return

_113F:
    ApplyMovement 23, _1194
    WaitMovement
    Return

_114B:
    ApplyMovement 23, _11A4
    WaitMovement
    Return

_1157:
    ApplyMovement 23, _11AC
    WaitMovement
    Return

_1163:
    ApplyMovement 23, _11BC
    WaitMovement
    Return

    .balign 4, 0
_1170:
    FaceNorth
    EndMovement

    .balign 4, 0
_1178:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_1184:
    WalkNormalSouth 2
    WalkNormalWest 2
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
_1194:
    WalkNormalSouth 2
    WalkNormalWest
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
_11A4:
    WalkNormalSouth 4
    EndMovement

    .balign 4, 0
_11AC:
    WalkNormalSouth 2
    WalkNormalEast
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
_11BC:
    WalkNormalSouth 2
    WalkNormalEast 2
    WalkNormalSouth 2
    EndMovement

_11CC:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    SetVar VAR_0x8004, 0
    Call _11F8
    GoToIfEq VAR_0x8004, 3, _1223
    Message 41
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_11F8:
    CallIfSet FLAG_OBTAINED_COUPON_1, _121B
    CallIfSet FLAG_OBTAINED_COUPON_2, _121B
    CallIfSet FLAG_OBTAINED_COUPON_3, _121B
    Return

_121B:
    AddVar VAR_0x8004, 1
    Return

_1223:
    Message 42
    RemoveItem ITEM_COUPON_1, 1, VAR_RESULT
    RemoveItem ITEM_COUPON_2, 1, VAR_RESULT
    RemoveItem ITEM_COUPON_3, 1, VAR_RESULT
    ScrCmd_131
    SetVar VAR_JUBILIFE_STATE, 2
    RegisterPoketchApp POKETCH_APPID_DIGITALWATCH
    RegisterPoketchApp POKETCH_APPID_CALCULATOR
    RegisterPoketchApp POKETCH_APPID_PEDOMETER
    RegisterPoketchApp POKETCH_APPID_PARTYSTATUS
    BufferPlayerName 0
    Message 43
    PlaySound SEQ_FANFA4
    WaitSound
    Message 44
    CloseMessage
    GetPlayerDir VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _12A1
    GoToIfEq VAR_RESULT, 1, _12BB
    GoToIfEq VAR_RESULT, 2, _12A1
    GoToIfEq VAR_RESULT, 3, _12A1
    End

_12A1:
    ApplyMovement 23, _12FC
    ApplyMovement LOCALID_PLAYER, _1314
    WaitMovement
    GoTo _12D5
    End

_12BB:
    ApplyMovement 23, _12F0
    ApplyMovement LOCALID_PLAYER, _1304
    WaitMovement
    GoTo _12D5
    End

_12D5:
    RemoveObject 23
    SetFlag FLAG_UNK_0x00F3
    ClearFlag FLAG_UNK_0x01F7
    // Arc 1 already hides Looker after the rally: only remove him if he's still here
    CallIfUnset FLAG_UNK_0x0181, JubilifeCity_Arc1RemoveLooker
    SetFlag FLAG_UNK_0x0181
    ReleaseAll
    End

    .balign 4, 0
_12F0:
    WalkNormalWest
    WalkNormalNorth 9
    EndMovement

    .balign 4, 0
_12FC:
    WalkNormalNorth 9
    EndMovement

    .balign 4, 0
_1304:
    Delay8
    WalkOnSpotNormalWest
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_1314:
    Delay8
    WalkOnSpotNormalNorth
    EndMovement

_1320:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_OBTAINED_COUPON_1, _138C
    Message 45
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _1356
    GoToIfEq VAR_RESULT, MENU_NO, _137D
    End

_1356:
    PlayFanfare SEQ_SE_DP_PINPON
    Message 46
    Message 48
    Message 49
    SetVar VAR_0x8004, ITEM_COUPON_1
    SetVar VAR_0x8005, 1
    SetFlag FLAG_OBTAINED_COUPON_1
    GiveItemQuantityNoLineFeed
    CloseMessage
    ReleaseAll
    End

_137D:
    PlayFanfare SEQ_SE_DP_BOX03
    Message 47
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_138C:
    Message 50
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_1397:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_OBTAINED_COUPON_2, _1403
    Message 51
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _13CD
    GoToIfEq VAR_RESULT, MENU_NO, _13F4
    End

_13CD:
    PlayFanfare SEQ_SE_DP_PINPON
    Message 52
    Message 54
    Message 55
    SetVar VAR_0x8004, ITEM_COUPON_2
    SetVar VAR_0x8005, 1
    SetFlag FLAG_OBTAINED_COUPON_2
    GiveItemQuantityNoLineFeed
    CloseMessage
    ReleaseAll
    End

_13F4:
    PlayFanfare SEQ_SE_DP_BOX03
    Message 53
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_1403:
    Message 56
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_140E:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfLt VAR_UNK_0x40E7, 2, _149E
    GoToIfSet FLAG_OBTAINED_COUPON_3, _1493
    Message 57
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _1451
    GoToIfEq VAR_RESULT, MENU_NO, _1484
    End

_1451:
    PlayFanfare SEQ_SE_DP_PINPON
    Message 58
    Message 60
    Message 61
    // Arc 1: from state 12 the president never walks (no forced intro) and may not be loaded at all (the rally
    // only un-hides him), so don't SetPosition him: on a missing object it writes through a NULL MapObject.
    CallIfLt VAR_ARC1_PROGRESS, 12, JubilifeCity_Arc1ResetPresidentPos
    SetVar VAR_0x8004, ITEM_COUPON_3
    SetVar VAR_0x8005, 1
    SetFlag FLAG_OBTAINED_COUPON_3
    GiveItemQuantityNoLineFeed
    CloseMessage
    ReleaseAll
    End

_1484:
    PlayFanfare SEQ_SE_DP_BOX03
    Message 59
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_1493:
    Message 63
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_149E:
    Message 62
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_14A9:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 93
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_14BC:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 94
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Looker_AfterOneBadgeObtained:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    SetObjectEventPos 31, 179, VAR_0x8005
    SetObjectEventDir 31, DIR_EAST
    SetObjectEventMovementType 31, MOVEMENT_TYPE_LOOK_EAST
    ClearFlag FLAG_UNK_0x0181
    AddObject 31
    ApplyMovement 31, _1538
    WaitMovement
    SetLookerBGM
    ApplyMovement 31, _1544
    ApplyMovement LOCALID_PLAYER, _08A0
    WaitMovement
    Call JubilifeCity_Looker_PalPadCheck
    CloseMessage
    ApplyMovement 31, _154C
    WaitMovement
    RemoveObject 31
    FadeToDefaultMusic4
    SetVar VAR_JUBILIFE_LOOKER_PALPAD, 2
    ReleaseAll
    End

    .balign 4, 0
_1538:
    WalkSlowEast 2
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_1544:
    WalkFastEast 6
    EndMovement

    .balign 4, 0
_154C:
    WalkSlowWest
    WalkFastWest 8
    EndMovement

    .balign 4, 0
_1558:
    WalkOnSpotNormalWest
    Delay8 2
    WalkOnSpotNormalEast
    EndMovement

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 1 (scene 11): the Team Eclipse rally in front of Jubilife TV.
//   VAR_ARC1_PROGRESS 12: rally cast + crowd visible, the east exit sends the player back to the plaza.
//                        Talking to Garius (or walking up behind him) runs the rally and sets 13.
//   13: crowd and grunts stay, Garius/Cyrus/Looker are gone, the east exit is open (Route 203, scene 12).
//   14+: the plaza is back to normal.  16: "To be continued..." at the north exit (D13).

JubilifeCity_Arc1HideRally:
    SetFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY
    SetFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY_CAST
    Return

JubilifeCity_Arc1OnTransition:
    CallIfLt VAR_JUBILIFE_STATE, 2, JubilifeCity_Arc1SkipStockIntro
    CallIfEq VAR_ARC1_PROGRESS, 12, JubilifeCity_Arc1SetUpRally
    CallIfEq VAR_ARC1_PROGRESS, 13, JubilifeCity_Arc1AfterRally
    CallIfGe VAR_ARC1_PROGRESS, 14, JubilifeCity_Arc1RallyOver
    Return

// The stock first visit (counterpart escort, Looker and the VS Recorder, Barry and the Parcel in the Trainers'
// School, Looker blocking the east exit) never happens in Arc 1. State 2 makes coord events 0 and 2 and _00AC
// inert. The Pokétch campaign stays as optional side content, without the forced president intro (coord 4).
JubilifeCity_Arc1SkipStockIntro:
    SetVar VAR_JUBILIFE_STATE, 2
    SetFlag FLAG_UNK_0x00F1
    SetFlag FLAG_UNK_0x01F4
    SetVar VAR_UNK_0x40E7, 2
    ClearFlag FLAG_UNK_0x01F6
    ClearFlag FLAG_UNK_0x01F5
    Return

JubilifeCity_Arc1SetUpRally:
    ClearFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY
    ClearFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY_CAST
    // Clear the plaza: the clown leaves the TV door and the Twin plays on the avenue instead
    SetFlag FLAG_UNK_0x0238
    // The Pokétch president and his two clowns sit the rally out. This also keeps the rally cast within the
    // field's dynamic object texture slots (the crowd reuses Jubilife's preloaded move-model gfx).
    SetFlag FLAG_UNK_0x01F5
    SetFlag FLAG_UNK_0x01F6
    SetObjectEventPos JUBILIFE_CITY_TWIN_3, 152, 759
    // Looker, the "Man in a Trench Coat", at the east end of the crowd, watching the screen (D4). The rally's
    // camera pan stops on him on its way to Cyrus (Arc 1 r2, critic #6).
    SetObjectEventPos JUBILIFE_CITY_LOOKER_31, 172, 756
    SetObjectEventDir JUBILIFE_CITY_LOOKER_31, DIR_NORTH
    SetObjectEventMovementType JUBILIFE_CITY_LOOKER_31, MOVEMENT_TYPE_LOOK_NORTH
    Return

JubilifeCity_Arc1AfterRally:
    ClearFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY
    SetFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY_CAST
    // Normally already done in-session by the rally (RestorePlaza, RemoveObject of Looker); kept as a guard
    ClearFlag FLAG_UNK_0x0238
    SetFlag FLAG_UNK_0x0181
    ClearFlag FLAG_UNK_0x01F5
    CallIfUnset FLAG_UNK_0x00F3, JubilifeCity_Arc1RestorePoketchCampaign
    Return

// Only the Arc 1 rally objects are touched from 14 on. The stock flags SetUpRally changed at 12 (0x0238, 0x01F5,
// 0x01F6) are restored by the rally itself (JubilifeCity_Arc1RestorePlaza), and the rally's RemoveObject of
// Looker sets FLAG_UNK_0x0181, so later stock scenes (post-Gym RemoveObject 24/25/27, the Pal Pad scene's
// ClearFlag FLAG_UNK_0x0181) keep working in Arc 2.
JubilifeCity_Arc1RallyOver:
    SetFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY
    SetFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY_CAST
    Return

// Until the Pokétch is obtained (FLAG_UNK_0x00F3), the president is back after the rally
JubilifeCity_Arc1RestorePoketchCampaign:
    ClearFlag FLAG_UNK_0x01F5
    ClearFlag FLAG_UNK_0x01F6
    Return

// End of the rally, while the camera is on Cyrus: undo SetUpRally's plaza changes in-session. Cyrus and
// Looker are already removed, which leaves room for the clown gfx (all three clowns are off screen here).
JubilifeCity_Arc1RestorePlaza:
    ClearFlag FLAG_UNK_0x0238
    AddObject JUBILIFE_CITY_CLOWN_27
    ClearFlag FLAG_UNK_0x01F5
    AddObject JUBILIFE_CITY_CLOWN_24
    AddObject JUBILIFE_CITY_CLOWN_25
    // The Pokétch president (until he has handed out the Pokétch; stock _12D5 removes him for good) is only
    // un-hidden here and appears on the next Jubilife load. Adding him in-session draws a black square: his gfx
    // does not fit in the field's dynamic object texture slots next to the grunts and the clowns.
    CallIfUnset FLAG_UNK_0x00F3, JubilifeCity_Arc1UnhidePresident
    Return

JubilifeCity_Arc1UnhidePresident:
    ClearFlag FLAG_UNK_0x01F6
    Return

JubilifeCity_Arc1RemoveLooker:
    RemoveObject JUBILIFE_CITY_LOOKER_31
    Return

// Stock _1451: put the president back at his post after his (stock-only) walk-up intro
JubilifeCity_Arc1ResetPresidentPos:
    SetPosition 23, 174, 1, 0x303, 1
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
    StopMusic 0
    PlayFanfare SEQ_SE_DP_TV_NOISE
    WaitFanfare SEQ_SE_DP_TV_NOISE
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitTime 10, VAR_RESULT
    PlayMusic SEQ_TV_HOUSOU
    WaitTime 20, VAR_RESULT
    Message JubilifeCity_Text_Arc1SarosEveryoneHasLostSomeone
    Message JubilifeCity_Text_Arc1SarosTheyTellYouToAcceptIt
    Message JubilifeCity_Text_Arc1SarosWeWillBringThemBack
    WaitABXPadPress
    CloseMessage
    // The broadcast cuts out
    StopMusic 0
    PlayFanfare SEQ_SE_DP_TV_NOISE
    WaitTime 6, VAR_RESULT
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitFanfare SEQ_SE_DP_TV_NOISE
    ApplyFreeCameraMovement JubilifeCity_Arc1Movement_CameraDownToCrowd
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
    WaitABXPadPress
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
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC1_GRUNT_FLYER, JubilifeCity_Arc1Movement_GruntBackToStage
    ApplyMovement LOCALID_ARC1_GARIUS, JubilifeCity_Arc1Movement_GariusLookAtFlyer
    WaitMovement
    // Garius stares at the flyer, folds it and pockets it: no narration, the pause carries it (critic #8)
    WaitTime 80, VAR_RESULT
    BufferRivalName 0
    Message JubilifeCity_Text_Arc1GariusJustAFlyer
    WaitABXPadPress
    CloseMessage
    // Pan away from the kids toward the edge of the crowd. It stops on the trench coat man at the east end of
    // the crowd: he glances east, at Cyrus (Arc 1 r2, critic #6).
    ApplyFreeCameraMovement JubilifeCity_Arc1Movement_CameraToLooker
    WaitMovement
    WaitTime 10, VAR_RESULT
    ApplyMovement JUBILIFE_CITY_LOOKER_31, JubilifeCity_Arc1Movement_TurnEast
    WaitMovement
    WaitTime 20, VAR_RESULT
    Message JubilifeCity_Text_Arc1LookerThatSuit
    WaitABXPadPress
    CloseMessage
    // The pan finishes on Cyrus, alone, watching the screen. The trench coat man slips away south, out of
    // frame, and is removed once he's off screen (D4: RemoveObject sets FLAG_UNK_0x0181)
    ApplyFreeCameraMovement JubilifeCity_Arc1Movement_CameraLookerToCyrus
    ApplyMovement JUBILIFE_CITY_LOOKER_31, JubilifeCity_Arc1Movement_LookerSlipAway
    WaitMovement
    RemoveObject JUBILIFE_CITY_LOOKER_31
    WaitTime 20, VAR_RESULT
    Message JubilifeCity_Text_Arc1CyrusIKnowThatVoice
    WaitABXPadPress
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
    FadeToDefaultMusic
    SetVar VAR_ARC1_PROGRESS, 13 /* rally done */
    ReleaseAll
    End

// Coord event at the east exit (x188, z757-760), state 12: the rally comes first
JubilifeCity_Arc1TriggerEastExit:
    LockAll
    BufferRivalName 0
    Message JubilifeCity_Text_Arc1GariusOverHere
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc1Movement_StepWest
    WaitMovement
    ReleaseAll
    End

// Coord event on the north exit row (x172-177, z743), state 16: end of Arc 1 (D13)
JubilifeCity_Arc1TriggerToBeContinued:
    LockAll
    Message JubilifeCity_Text_Arc1ToBeContinued
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, JubilifeCity_Arc1Movement_StepSouth
    WaitMovement
    ReleaseAll
    End

JubilifeCity_Arc1TrenchCoat:
    Message JubilifeCity_Text_Arc1TrenchCoat
    WaitABXPadPress
    CloseMessage
    ApplyMovement JUBILIFE_CITY_LOOKER_31, JubilifeCity_Arc1Movement_FaceNorth
    WaitMovement
    ReleaseAll
    End

JubilifeCity_Arc1Banner:
    ShowLandmarkSign JubilifeCity_Text_Arc1BannerWhoDidYouLose
    End

JubilifeCity_Arc1EclipseGruntFlyer:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1GruntTakeAFlyer
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1EclipseGruntF:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1GruntYouDontHaveToAcceptIt
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// Talk to Cyrus before the rally. He keeps his eyes on the TV and doesn't turn around: in the rally the player
// never sees him (scene 11), and the kids only find him in Jubilife at the start of Arc 2.
JubilifeCity_Arc1Cyrus:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message JubilifeCity_Text_Arc1CyrusWhoDidYouLose
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1CrowdNeverCameHome:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1CrowdNeverCameHome
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1CrowdGrandpasPokemon:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1CrowdGrandpasPokemon
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1CrowdOneMoreDay:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1CrowdOneMoreDay
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1CrowdBestFriend:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1CrowdBestFriend
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1CrowdEveryWeek:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1CrowdEveryWeek
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

JubilifeCity_Arc1CrowdMomAskedMe:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message JubilifeCity_Text_Arc1CrowdMomAskedMe
    WaitABXPadPress
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
