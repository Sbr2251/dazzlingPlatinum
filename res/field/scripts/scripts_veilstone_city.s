#include "macros/scrcmd.inc"
#include "res/text/bank/veilstone_city.h"
#include "res/field/events/events_veilstone_city.h"


    ScriptEntry _0082
    ScriptEntry _0C18
    ScriptEntry _0C2B
    ScriptEntry _0C3E
    ScriptEntry _0C51
    ScriptEntry _0C64
    ScriptEntry _0C77
    ScriptEntry _0CD1
    ScriptEntry _0CE4
    ScriptEntry VeilstoneCity_GalacticGruntWarehouseGuard
    ScriptEntry _0D5C
    ScriptEntry _0D8D
    ScriptEntry _0DBE
    ScriptEntry _0FF0
    ScriptEntry _00F6
    ScriptEntry VeilstoneCity_Counterpart
    ScriptEntry _1003
    ScriptEntry _101A
    ScriptEntry _102F
    ScriptEntry _1046
    ScriptEntry _105D
    ScriptEntry _1074
    ScriptEntry _108B
    ScriptEntry _10A2
    ScriptEntry VeilstoneCity_DeoxysMeteoriteSpeed
    ScriptEntry VeilstoneCity_DeoxysMeteoriteDefense
    ScriptEntry VeilstoneCity_DeoxysMeteoriteAttack
    ScriptEntry VeilstoneCity_DeoxysMeteoriteNormal
    ScriptEntry _1184
    ScriptEntry _0FB0
    ScriptEntry _1204
    ScriptEntry _123E
    ScriptEntry VeilstoneCity_Arc2LookerCheck
    ScriptEntry VeilstoneCity_Arc2LookerTalk
    ScriptEntry VeilstoneCity_Arc2Maylene
    ScriptEntry VeilstoneCity_Arc2Cyrus
    ScriptEntry VeilstoneCity_Arc2StoneBox
    ScriptEntryEnd

_0082:
    Call VeilstoneCity_Arc2OnTransition
    CallIfSet FLAG_UNK_0x0155, _00E0
    CallIfGe VAR_VEILSTONE_STATE, 2, _00BA
    GetPlayerGender VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, GENDER_MALE, _00D0
    GoToIfEq VAR_MAP_LOCAL_0, GENDER_FEMALE, _00D8
    End

_00BA:
    SetObjectEventPos 6, 0x2B8, 0x254
    SetObjectEventMovementType 6, MOVEMENT_TYPE_LOOK_EAST
    SetObjectEventDir 6, DIR_EAST
    Return

_00D0:
    SetVar VAR_OBJ_GFX_ID_0, 97
    End

_00D8:
    SetVar VAR_OBJ_GFX_ID_0, 0
    End

_00E0:
    SetObjectEventPos 26, 0x2CD, 0x251
    SetObjectEventMovementType 26, MOVEMENT_TYPE_LOOK_NORTH
    SetObjectEventDir 26, DIR_NORTH
    Return

_00F6:
    LockAll
    ApplyMovement 6, _0444
    WaitMovement
    SetCounterpartBGM
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 0x2A9, _02E1
    CallIfEq VAR_0x8004, 0x2AA, _02ED
    CallIfEq VAR_0x8004, 0x2AB, _02F9
    CallIfEq VAR_0x8004, 0x2AC, _0305
    GetPlayerGender VAR_0x8004
    CallIfEq VAR_0x8004, GENDER_MALE, _0297
    CallIfEq VAR_0x8004, GENDER_FEMALE, _029F
    CloseMessage
    FadeToDefaultMusic
    LoadDoorAnimation 21, 19, 12, 3, ANIMATION_TAG_DOOR_1
    PlayDoorOpenAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    ClearFlag FLAG_UNK_0x0191
    AddObject 25
    ApplyMovement 25, _0564
    WaitMovement
    PlayDoorCloseAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    UnloadAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement 6, _0484
    WaitMovement
    Message 4
    CloseMessage
    ApplyMovement 25, _056C
    WaitMovement
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 0x2A9, _0311
    CallIfEq VAR_0x8004, 0x2AA, _032D
    CallIfEq VAR_0x8004, 0x2AB, _0349
    CallIfEq VAR_0x8004, 0x2AC, _0365
    Message 5
    Message 6
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 0x2A9, _0381
    CallIfEq VAR_0x8004, 0x2AA, _039D
    CallIfEq VAR_0x8004, 0x2AB, _03B9
    CallIfEq VAR_0x8004, 0x2AC, _03D5
    RemoveObject 25
    WaitTime 20, VAR_RESULT
    GetPlayerGender VAR_0x8004
    CallIfEq VAR_0x8004, GENDER_MALE, _02A7
    CallIfEq VAR_0x8004, GENDER_FEMALE, _02C4
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 0x2A9, _03F1
    CallIfEq VAR_0x8004, 0x2AA, _0405
    CallIfEq VAR_0x8004, 0x2AB, _0419
    CallIfEq VAR_0x8004, 0x2AC, _042D
    RemoveObject 6
    SetVar VAR_UNK_0x40F5, 1
    ReleaseAll
    End

_0297:
    BufferPlayerName 0
    Message 2
    Return

_029F:
    BufferPlayerName 0
    Message 3
    Return

_02A7:
    BufferPlayerName 0
    Message 7
    CloseMessage
    WaitTime 15, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, _052C
    WaitMovement
    Message 8
    Return

_02C4:
    BufferPlayerName 0
    Message 9
    CloseMessage
    WaitTime 15, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, _052C
    WaitMovement
    Message 10
    Return

_02E1:
    ApplyMovement 6, _0458
    WaitMovement
    Return

_02ED:
    ApplyMovement 6, _0464
    WaitMovement
    Return

_02F9:
    ApplyMovement 6, _046C
    WaitMovement
    Return

_0305:
    ApplyMovement 6, _0478
    WaitMovement
    Return

_0311:
    ApplyMovement 25, _0574
    ApplyMovement 6, _048C
    ApplyMovement LOCALID_PLAYER, _04EC
    WaitMovement
    Return

_032D:
    ApplyMovement 25, _0580
    ApplyMovement 6, _0498
    ApplyMovement LOCALID_PLAYER, _04FC
    WaitMovement
    Return

_0349:
    ApplyMovement 25, _058C
    ApplyMovement 6, _04A4
    ApplyMovement LOCALID_PLAYER, _050C
    WaitMovement
    Return

_0365:
    ApplyMovement 25, _0598
    ApplyMovement 6, _04B0
    ApplyMovement LOCALID_PLAYER, _051C
    WaitMovement
    Return

_0381:
    ApplyMovement 25, _05AC
    ApplyMovement 6, _04D4
    ApplyMovement LOCALID_PLAYER, _0554
    WaitMovement
    Return

_039D:
    ApplyMovement 25, _05B4
    ApplyMovement 6, _04D4
    ApplyMovement LOCALID_PLAYER, _0554
    WaitMovement
    Return

_03B9:
    ApplyMovement 25, _05BC
    ApplyMovement 6, _04D4
    ApplyMovement LOCALID_PLAYER, _0554
    WaitMovement
    Return

_03D5:
    ApplyMovement 25, _05C4
    ApplyMovement 6, _04D4
    ApplyMovement LOCALID_PLAYER, _0554
    WaitMovement
    Return

_03F1:
    ApplyMovement 6, _04BC
    ApplyMovement LOCALID_PLAYER, _0534
    WaitMovement
    Return

_0405:
    ApplyMovement 6, _04BC
    ApplyMovement LOCALID_PLAYER, _0534
    WaitMovement
    Return

_0419:
    ApplyMovement 6, _04C8
    ApplyMovement LOCALID_PLAYER, _0544
    WaitMovement
    Return

_042D:
    ApplyMovement 6, _04C8
    ApplyMovement LOCALID_PLAYER, _0544
    WaitMovement
    Return

    .balign 4, 0
_0444:
    Delay8
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    Delay8
    EndMovement

    .balign 4, 0
_0458:
    WalkNormalWest
    WalkNormalSouth
    EndMovement

    .balign 4, 0
_0464:
    WalkNormalSouth
    EndMovement

    .balign 4, 0
_046C:
    WalkNormalEast
    WalkNormalSouth
    EndMovement

    .balign 4, 0
_0478:
    WalkNormalEast 2
    WalkNormalSouth
    EndMovement

    .balign 4, 0
_0484:
    WalkOnSpotFastNorth
    EndMovement

    .balign 4, 0
_048C:
    Delay8 4
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0498:
    Delay8 3
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_04A4:
    Delay8 2
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_04B0:
    Delay8 4
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_04BC:
    WalkNormalEast
    WalkNormalSouth 9
    EndMovement

    .balign 4, 0
_04C8:
    WalkNormalWest
    WalkNormalSouth 9
    EndMovement

    .balign 4, 0
_04D4:
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

VeilstoneCity_UnusedMovement:
    Delay8
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_04EC:
    Delay8 4
    Delay4
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_04FC:
    Delay8 3
    Delay4
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_050C:
    Delay8 2
    Delay4
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_051C:
    Delay8 4
    Delay4
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_052C:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0534:
    Delay8 2
    WalkOnSpotNormalEast
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0544:
    Delay8 2
    WalkOnSpotNormalWest
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0554:
    Delay8
    Delay4
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0564:
    WalkNormalSouth
    EndMovement

    .balign 4, 0
_056C:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_0574:
    WalkNormalSouth 4
    WalkNormalWest 2
    EndMovement

    .balign 4, 0
_0580:
    WalkNormalSouth 4
    WalkNormalWest
    EndMovement

    .balign 4, 0
_058C:
    WalkNormalSouth 4
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0598:
    WalkNormalSouth
    WalkNormalWest
    WalkNormalSouth 3
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_05AC:
    WalkNormalSouth 8
    EndMovement

    .balign 4, 0
_05B4:
    WalkNormalSouth 8
    EndMovement

    .balign 4, 0
_05BC:
    WalkNormalSouth 8
    EndMovement

    .balign 4, 0
_05C4:
    WalkNormalSouth 8
    EndMovement

VeilstoneCity_Counterpart:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GetPlayerGender VAR_0x8004
    GoToIfEq VAR_0x8004, GENDER_MALE, VeilstoneCity_Dawn
    GoToIfEq VAR_0x8004, GENDER_FEMALE, VeilstoneCity_Lucas
    End

VeilstoneCity_Dawn:
    BufferPlayerName 0
    Message VeilstoneCity_Text_DawnAskForHelp
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, VeilstoneCity_DawnAcceptTeamUp
    GoTo VeilstoneCity_DawnDeclineTeamUp

VeilstoneCity_DawnAcceptTeamUp:
    Message VeilstoneCity_Text_DawnTeamUp
    GoTo _0656

VeilstoneCity_DawnDeclineTeamUp:
    Message VeilstoneCity_Text_DawnIllBeWaiting
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

VeilstoneCity_Lucas:
    BufferPlayerName 0
    Message VeilstoneCity_Text_LucasAskForHelp
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, VeilstoneCity_LucasAcceptTeamUp
    GoTo VeilstoneCity_LucasDeclineTeamUp

VeilstoneCity_LucasAcceptTeamUp:
    Message VeilstoneCity_Text_LucasTeamUp
    GoTo _0656

VeilstoneCity_LucasDeclineTeamUp:
    Message VeilstoneCity_Text_LucasIllBeWaiting
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0656:
    CloseMessage
    GetPlayerDir VAR_RESULT
    CallIfEq VAR_RESULT, 3, _099F
    CallIfEq VAR_RESULT, 1, _09B3
    CallIfEq VAR_RESULT, 0, _09C7
    Call VeilstoneCity_SetPlayerCounterpartPartnerTeam
    StartTagBattle VAR_0x8004, TRAINER_GALACTIC_GRUNT_VEILSTONE_CITY_1, TRAINER_GALACTIC_GRUNT_VEILSTONE_CITY_2
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _0A73
    Message 16
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8005, 0x253, _09DB
    CallIfEq VAR_0x8005, 0x255, _09E7
    Message 17
    CloseMessage
    WaitTime 15, VAR_RESULT
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8005, 0x253, _09F3
    CallIfEq VAR_0x8005, 0x255, _09FF
    RemoveObject 7
    Message 18
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8005, 0x253, _0A0B
    CallIfEq VAR_0x8005, 0x255, _0A17
    RemoveObject 20
    GetPlayerGender VAR_0x8004
    CallIfEq VAR_0x8004, GENDER_MALE, _0A23
    CallIfEq VAR_0x8004, GENDER_FEMALE, _0A28
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8005, 0x253, _0A4B
    CallIfEq VAR_0x8005, 0x255, _0A5F
    WaitTime 10, VAR_RESULT
    BufferPlayerName 0
    GetPlayerGender VAR_0x8004
    CallIfEq VAR_0x8004, GENDER_MALE, _0A2D
    CallIfEq VAR_0x8004, GENDER_FEMALE, _0A32
    CloseMessage
    WaitTime 15, VAR_RESULT
    ClearFlag FLAG_UNK_0x028A
    SetObjectEventPos 26, 0x2B4, 0x25E
    AddObject 26
    SetLookerBGM
    ApplyMovement 26, _0A7C
    WaitMovement
    Message 29
    CloseMessage
    ApplyMovement 6, _0B3C
    ApplyMovement LOCALID_PLAYER, _0B9C
    WaitMovement
    GetPlayerGender VAR_0x8004
    CallIfEq VAR_0x8004, GENDER_MALE, _0A37
    CallIfEq VAR_0x8004, GENDER_FEMALE, _0A3C
    Message 32
    GetPlayerGender VAR_0x8004
    CallIfEq VAR_0x8004, GENDER_MALE, _0A41
    CallIfEq VAR_0x8004, GENDER_FEMALE, _0A46
    CloseMessage
    ApplyMovement 6, _0B44
    ApplyMovement 26, _0A88
    WaitMovement
    RemoveObject 6
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 0x253, _083A
    GoToIfEq VAR_0x8005, 0x255, _0854
    End

_083A:
    ApplyMovement LOCALID_PLAYER, _0BB0
    ApplyMovement 26, _0A94
    WaitMovement
    GoTo _086E
    End

_0854:
    ApplyMovement LOCALID_PLAYER, _0BBC
    ApplyMovement 26, _0AA0
    WaitMovement
    GoTo _086E
    End

_086E:
    Message 35
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 0x253, _08A9
    GoToIfEq VAR_0x8005, 0x255, _08C3
    End

VeilstoneCity_Unused:
    SetObjectEventPos 26, 692, 603
    Return

VeilstoneCity_Unused2:
    SetObjectEventPos 26, 692, 605
    Return

_08A9:
    ApplyMovement 26, _0AAC
    ApplyMovement LOCALID_PLAYER, _0BC8
    WaitMovement
    GoTo _08DD
    End

_08C3:
    ApplyMovement 26, _0AAC
    ApplyMovement LOCALID_PLAYER, _0BDC
    WaitMovement
    GoTo _08DD
    End

_08DD:
    SetFlag FLAG_UNK_0x01A9
    SetFlag FLAG_UNK_0x028A
    ClearFlag FLAG_UNK_0x020D
    SetVar VAR_UNK_0x411F, 1
    PlayFanfare SEQ_SE_DP_KAIDAN2
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_VEILSTONE_CITY_GALACTIC_WAREHOUSE, 0, 8, 11, 0
    FadeScreenIn
    WaitFadeScreen
    End

VeilstoneCity_SetPlayerCounterpartPartnerTeam:
    GetPlayerGender VAR_RESULT
    GoToIfEq VAR_RESULT, GENDER_MALE, VeilstoneCity_SetDawnPartnerTeam
    GoToIfEq VAR_RESULT, GENDER_FEMALE, VeilstoneCity_SetLucasPartnerTeam
    End

VeilstoneCity_SetDawnPartnerTeam:
    GetPlayerStarterSpecies VAR_RESULT
    SetVar VAR_0x8004, TRAINER_DAWN_VEILSTONE_CITY_CHIMCHAR
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, _099D
    SetVar VAR_0x8004, TRAINER_DAWN_VEILSTONE_CITY_PIPLUP
    GoToIfEq VAR_RESULT, SPECIES_PIPLUP, _099D
    SetVar VAR_0x8004, TRAINER_DAWN_VEILSTONE_CITY_TURTWIG
    Return

VeilstoneCity_SetLucasPartnerTeam:
    GetPlayerStarterSpecies VAR_RESULT
    SetVar VAR_0x8004, TRAINER_LUCAS_VEILSTONE_CITY_CHIMCHAR
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, _099D
    SetVar VAR_0x8004, TRAINER_LUCAS_VEILSTONE_CITY_PIPLUP
    GoToIfEq VAR_RESULT, SPECIES_PIPLUP, _099D
    SetVar VAR_0x8004, TRAINER_LUCAS_VEILSTONE_CITY_TURTWIG
    Return

_099D:
    Return

_099F:
    ApplyMovement 6, _0ABC
    ApplyMovement LOCALID_PLAYER, _0B50
    WaitMovement
    Return

_09B3:
    ApplyMovement 6, _0AC8
    ApplyMovement LOCALID_PLAYER, _0B5C
    WaitMovement
    Return

_09C7:
    ApplyMovement 6, _0AD4
    ApplyMovement LOCALID_PLAYER, _0B64
    WaitMovement
    Return

_09DB:
    ApplyMovement 20, _0BF0
    WaitMovement
    Return

_09E7:
    ApplyMovement 7, _0BF0
    WaitMovement
    Return

_09F3:
    ApplyMovement 7, _0BF8
    WaitMovement
    Return

_09FF:
    ApplyMovement 7, _0BF8
    WaitMovement
    Return

_0A0B:
    ApplyMovement 20, _0C08
    WaitMovement
    Return

_0A17:
    ApplyMovement 20, _0C08
    WaitMovement
    Return

_0A23:
    Message 22
    Return

_0A28:
    Message 27
    Return

_0A2D:
    Message 23
    Return

_0A32:
    Message 28
    Return

_0A37:
    Message 30
    Return

_0A3C:
    Message 31
    Return

_0A41:
    Message 33
    Return

_0A46:
    Message 34
    Return

_0A4B:
    ApplyMovement 6, _0B2C
    ApplyMovement LOCALID_PLAYER, _0B8C
    WaitMovement
    Return

_0A5F:
    ApplyMovement 6, _0B34
    ApplyMovement LOCALID_PLAYER, _0B94
    WaitMovement
    Return

_0A73:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
_0A7C:
    WalkFastNorth 10
    WalkFastEast 3
    EndMovement

    .balign 4, 0
_0A88:
    Delay8 2
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0A94:
    WalkNormalEast
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0AA0:
    WalkNormalEast
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0AAC:
    WalkNormalEast 5
    WalkNormalNorth 4
    SetInvisible
    EndMovement

    .balign 4, 0
_0ABC:
    WalkNormalSouth
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0AC8:
    WalkNormalSouth
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0AD4:
    WalkNormalNorth
    WalkOnSpotNormalEast
    EndMovement

VeilstoneCity_UnusedMovement2:
    Delay4
    WalkOnSpotNormalWest
    EmoteExclamationMark
    Delay8
    EndMovement

VeilstoneCity_UnusedMovement3:
    WalkNormalWest 4
    EndMovement

VeilstoneCity_UnusedMovement4:
    WalkNormalSouth 2
    WalkNormalWest 2
    WalkNormalSouth 6
    EndMovement

VeilstoneCity_UnusedMovement5:
    Delay8
    WalkOnSpotNormalNorth
    WalkOnSpotNormalWest
    EndMovement

VeilstoneCity_UnusedMovement6:
    Delay8
    WalkOnSpotNormalSouth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0B2C:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0B34:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0B3C:
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
_0B44:
    WalkNormalWest 3
    WalkNormalSouth 10
    EndMovement

    .balign 4, 0
_0B50:
    WalkNormalNorth
    WalkNormalEast
    EndMovement

    .balign 4, 0
_0B5C:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0B64:
    WalkOnSpotNormalEast
    EndMovement

VeilstoneCity_UnusedMovement7:
    Delay8
    WalkOnSpotNormalSouth
    WalkOnSpotNormalWest
    EndMovement

VeilstoneCity_UnusedMovement8:
    Delay8
    WalkOnSpotNormalNorth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0B8C:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0B94:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0B9C:
    WalkOnSpotNormalWest
    EndMovement

VeilstoneCity_UnusedMovement9:
    Delay8
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0BB0:
    Delay8
    FaceSouth
    EndMovement

    .balign 4, 0
_0BBC:
    Delay8
    FaceNorth
    EndMovement

    .balign 4, 0
_0BC8:
    WalkNormalSouth
    WalkNormalEast 5
    WalkNormalNorth 5
    SetInvisible
    EndMovement

    .balign 4, 0
_0BDC:
    WalkNormalNorth
    WalkNormalEast 5
    WalkNormalNorth 5
    SetInvisible
    EndMovement

    .balign 4, 0
_0BF0:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0BF8:
    WalkFastEast 4
    WalkFastNorth 4
    WalkOnSpotFastNorth
    EndMovement

    .balign 4, 0
_0C08:
    WalkFastEast 4
    WalkFastNorth 6
    WalkOnSpotFastNorth
    EndMovement

_0C18:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 43
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0C2B:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 49
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0C3E:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 44
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0C51:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 45
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0C64:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 46
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0C77:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x00CC, _0CBC
    Message 50
    SetVar VAR_0x8004, ITEM_TM63
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, _0CC7
    GiveItemQuantity
    SetFlag FLAG_UNK_0x00CC
    GoTo _0CBC

_0CBC:
    Message 51
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0CC7:
    MessageBagIsFull
    CloseMessage
    ReleaseAll
    End

_0CD1:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 47
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0CE4:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 48
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

VeilstoneCity_GalacticGruntWarehouseGuard:
    LockAll
    ApplyMovement VEILSTONE_CITY_GRUNT_M_7, VeilstoneCity_Grunt_FaceSouth
    ApplyMovement LOCALID_PLAYER, VeilstoneCity_Player_FaceNorth
    WaitMovement
    Message VeilstoneCity_Text_Arc2DepotGuard
    WaitABXPadPress
    CloseMessage
    ApplyMovement VEILSTONE_CITY_GRUNT_M_7, VeilstoneCity_Grunt_PushPlayerBack
    ApplyMovement LOCALID_PLAYER, VeilstoneCity_Player_GetPushed
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
VeilstoneCity_Player_FaceNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
VeilstoneCity_Grunt_FaceSouth:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
VeilstoneCity_Grunt_PushPlayerBack:
    WalkFastSouth
    WalkOnSpotNormalWest
    Delay8 2
    WalkNormalNorth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
VeilstoneCity_Player_GetPushed:
    WalkNormalWest
    EndMovement

_0D5C:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message VeilstoneCity_Text_Arc2DepotGuard
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End
    GoToIfBadgeAcquired BADGE_ID_COBBLE, _0D82
    Message VeilstoneCity_Text_ThisIsGalacticWarehouse1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0D82:
    Message 14
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0D8D:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message VeilstoneCity_Text_Arc2DepotGuard
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End
    GoToIfBadgeAcquired BADGE_ID_COBBLE, _0DB3
    Message 13
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0DB3:
    Message 15
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0DBE:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message 36
    CloseMessage
    FacePlayer
    ApplyMovement 23, _0F1C
    WaitMovement
    Message 37
    CloseMessage
    SetFlag FLAG_UNK_0x0155
    SetObjectEventPos 26, 0x2D3, 0x259
    SetObjectEventMovementType 26, MOVEMENT_TYPE_LOOK_NORTH
    SetObjectEventDir 26, DIR_NORTH
    ClearFlag FLAG_UNK_0x028A
    AddObject 26
    GetPlayerDir VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _0E34
    GoToIfEq VAR_RESULT, 1, _0E5C
    GoToIfEq VAR_RESULT, 2, _0EA4
    GoToIfEq VAR_RESULT, 3, _0E7C
    End

_0E34:
    ApplyMovement LOCALID_PLAYER, _0F48
    ApplyMovement 23, _0F24
    WaitMovement
    SetLookerBGM
    ApplyMovement 26, _0F80
    WaitMovement
    GoTo _0ECC
    End

_0E5C:
    ApplyMovement 23, _0F24
    WaitMovement
    SetLookerBGM
    ApplyMovement 26, _0F70
    WaitMovement
    GoTo _0ECC
    End

_0E7C:
    ApplyMovement LOCALID_PLAYER, _0F58
    ApplyMovement 23, _0F24
    WaitMovement
    SetLookerBGM
    ApplyMovement 26, _0F90
    WaitMovement
    GoTo _0ECC
    End

_0EA4:
    ApplyMovement LOCALID_PLAYER, _0F64
    ApplyMovement 23, _0F38
    WaitMovement
    SetLookerBGM
    ApplyMovement 26, _0FA0
    WaitMovement
    GoTo _0ECC
    End

_0ECC:
    RemoveObject 23
    GoTo _0ED8
    End

_0ED8:
    Message 38
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _0EF4
    GoTo _0F0B
    End

_0EF4:
    SetVar VAR_UNK_0x411F, 3
    SetFlag FLAG_UNK_0x009B
    Message 39
    CloseMessage
    FadeToDefaultMusic4
    ReleaseAll
    End

_0F0B:
    Message 40
    WaitABXPadPress
    CloseMessage
    FadeToDefaultMusic4
    ReleaseAll
    End

    .balign 4, 0
_0F1C:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_0F24:
    WalkFastEast
    WalkFastSouth 2
    WalkFastEast
    WalkFastSouth 9
    EndMovement

    .balign 4, 0
_0F38:
    WalkFastSouth 2
    WalkFastEast 2
    WalkFastSouth 9
    EndMovement

    .balign 4, 0
_0F48:
    Delay8
    WalkOnSpotNormalEast
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0F58:
    Delay8 2
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0F64:
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0F70:
    WalkNormalNorth 6
    WalkNormalWest 2
    WalkNormalNorth 2
    EndMovement

    .balign 4, 0
_0F80:
    WalkNormalNorth 6
    WalkNormalWest 2
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0F90:
    WalkNormalNorth 6
    WalkNormalWest 3
    WalkNormalNorth
    EndMovement

    .balign 4, 0
_0FA0:
    WalkNormalNorth 6
    WalkNormalWest
    WalkNormalNorth
    EndMovement

_0FB0:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    ApplyMovement 26, _0FE0
    WaitMovement
    BufferPlayerName 0
    Message 41
    SetLookerBGM
    GoToIfSet FLAG_UNK_0x009B, _0EF4
    GoTo _0ED8
    End

    .balign 4, 0
_0FE0:
    Delay8
    EmoteExclamationMark
    Delay8
    EndMovement

_0FF0:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 42
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_1003:
    ShowMapSign 61
    End

_101A:
    ShowScrollingSign 62
    End

_102F:
    ShowLandmarkSign 63
    End

_1046:
    ShowLandmarkSign 64
    End

_105D:
    ShowLandmarkSign 65
    End

_1074:
    ShowLandmarkSign 66
    End

_108B:
    ShowLandmarkSign 67
    End

_10A2:
    ShowLandmarkSign 68
    End

VeilstoneCity_DeoxysMeteoriteSpeed:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    CheckPartyHasSpecies2 SPECIES_DEOXYS, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, VeilstoneCity_MeteoriteFromTheStars
    ChangeDeoxysForm DEOXYS_FORM_SPEED
    PlayCry SPECIES_DEOXYS
    Message VeilstoneCity_Text_MeteoriteSpeed
    WaitABXPadPress
    WaitCry
    CloseMessage
    ReleaseAll
    End

VeilstoneCity_DeoxysMeteoriteDefense:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    CheckPartyHasSpecies2 SPECIES_DEOXYS, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, VeilstoneCity_MeteoriteFromTheStars
    ChangeDeoxysForm DEOXYS_FORM_DEFENSE
    PlayCry SPECIES_DEOXYS
    Message VeilstoneCity_Text_MeteoriteDefense
    WaitABXPadPress
    WaitCry
    CloseMessage
    ReleaseAll
    End

VeilstoneCity_DeoxysMeteoriteAttack:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    CheckPartyHasSpecies2 SPECIES_DEOXYS, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, VeilstoneCity_MeteoriteFromTheStars
    ChangeDeoxysForm DEOXYS_FORM_ATTACK
    PlayCry SPECIES_DEOXYS
    Message VeilstoneCity_Text_MeteoriteAttack
    WaitABXPadPress
    WaitCry
    CloseMessage
    ReleaseAll
    End

VeilstoneCity_DeoxysMeteoriteNormal:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    CheckPartyHasSpecies2 SPECIES_DEOXYS, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, VeilstoneCity_MeteoriteFromTheStars
    ChangeDeoxysForm DEOXYS_FORM_NORMAL
    PlayCry SPECIES_DEOXYS
    Message VeilstoneCity_Text_MeteoriteNormal
    WaitABXPadPress
    WaitCry
    CloseMessage
    ReleaseAll
    End

VeilstoneCity_MeteoriteFromTheStars:
    Message VeilstoneCity_Text_MeteoriteFromTheStars
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_1184:
    LockAll
    ApplyMovement VEILSTONE_CITY_COUNTERPART, _11E8
    WaitMovement
    GetPlayerGender VAR_0x8004
    CallIfEq VAR_0x8004, GENDER_MALE, _11D6
    CallIfEq VAR_0x8004, GENDER_FEMALE, _11DE
    CloseMessage
    ApplyMovement VEILSTONE_CITY_COUNTERPART, _11FC
    WaitMovement
    RemoveObject VEILSTONE_CITY_COUNTERPART
    Call _00BA
    ClearFlag FLAG_HIDE_VEILSTONE_COUNTERPART
    AddObject VEILSTONE_CITY_COUNTERPART
    SetVar VAR_VEILSTONE_STATE, 2
    ReleaseAll
    End

_11D6:
    BufferPlayerName 0
    Message 0
    Return

_11DE:
    BufferPlayerName 0
    Message 1
    Return

    .balign 4, 0
_11E8:
    WalkOnSpotNormalNorth
    EmoteExclamationMark
    WalkNormalEast 2
    WalkNormalNorth
    EndMovement

    .balign 4, 0
_11FC:
    WalkNormalSouth 9
    EndMovement

_1204:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 52
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, _122B
    Message 53
    GoTo _1236
    End

_122B:
    Message 54
    GoTo _1236
    End

_1236:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_123E:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 55
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 2, workstream s-veilstone: 2.17 (Looker's check) and 2.17b (Maylene's trial, Key Stone).
//
// Flags (s-veilstone allocation 0x0946-0x094A, registered in R0 as FLAG_ARC2_VEILSTONE_A-E):
//   FLAG_ARC2_VEILSTONE_A (0x0946) depot manifest copied (2.17a; heist past the stealth part)
//   FLAG_ARC2_VEILSTONE_B (0x0947) Route 215 crate seen (2.17c; guards the bit-3 add)
//   FLAG_ARC2_VEILSTONE_C (0x0948) Pokemon Center: Ruth + Cyrus hidden (clear only at 57)
//   FLAG_ARC2_VEILSTONE_D (0x0949) Pokemon Center: Garius hidden (shown only in the 2.17d scene)
//   FLAG_ARC2_VEILSTONE_E (0x094A) spare
// Map-local hide flags (cleared on every map load, recomputed in VeilstoneCity_Arc2OnTransition):
//   0x0030 Looker (newspaper), 0x0031 Maylene, 0x0032 Cyrus, 0x0033 stone box, 0x0034 depot front guards,
//   0x0035 stock objects that never show in Arc 2 (Dawn, the 'HM02 in the warehouse' grunt)
// Map-local vars: VAR_MAP_LOCAL_1 = 1 arms the Looker coord (681-684, 616); VAR_MAP_LOCAL_2 = 1 disarms the
//   depot guards' push-back coord (697, 596).
// VAR_ARC2_PROGRESS: 49 + Cobble Badge -> Looker; sets 51. 54 -> Maylene's trial; sets 57.
// VAR_ARC2_CHOICES bit 0 (+1): the player said Yes to "Do you trust him?" (the only write to bit 0).

VeilstoneCity_Arc2OnTransition:
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    SetFlag FLAG_UNK_0x0032
    SetFlag FLAG_UNK_0x0033
    SetFlag FLAG_UNK_0x0035
    SetVar VAR_MAP_LOCAL_1, 0
    SetVar VAR_MAP_LOCAL_2, 0
    // Pokemon Center 2.17d cast (that map keeps its stock OnTransition): Ruth + Cyrus only at 57, Garius never
    SetFlag FLAG_ARC2_VEILSTONE_C
    SetFlag FLAG_ARC2_VEILSTONE_D
    CallIfEq VAR_ARC2_PROGRESS, 57, VeilstoneCity_Arc2ShowPCTable
    // Depot front guards stand until Looker's favor (51); then the night shift lets the side door be
    CallIfGe VAR_ARC2_PROGRESS, 51, VeilstoneCity_Arc2HideDepotGuards
    CallIfEq VAR_ARC2_PROGRESS, 49, VeilstoneCity_Arc2TryArmLooker
    CallIfGe VAR_ARC2_PROGRESS, 54, VeilstoneCity_Arc2TryShowShrine
    Return

VeilstoneCity_Arc2TryShowShrine:
    GoToIfLe VAR_ARC2_PROGRESS, 56, VeilstoneCity_Arc2ShowShrine
    Return

VeilstoneCity_Arc2ShowPCTable:
    ClearFlag FLAG_ARC2_VEILSTONE_C
    Return

VeilstoneCity_Arc2HideDepotGuards:
    SetFlag FLAG_UNK_0x0034
    SetVar VAR_MAP_LOCAL_2, 1
    Return

VeilstoneCity_Arc2TryArmLooker:
    CheckBadgeAcquired BADGE_ID_COBBLE, VAR_MAP_LOCAL_3
    CallIfEq VAR_MAP_LOCAL_3, TRUE, VeilstoneCity_Arc2ArmLooker
    Return

VeilstoneCity_Arc2ArmLooker:
    ClearFlag FLAG_UNK_0x0030
    SetVar VAR_MAP_LOCAL_1, 1
    Return

VeilstoneCity_Arc2ShowShrine:
    ClearFlag FLAG_UNK_0x0031
    ClearFlag FLAG_UNK_0x0032
    ClearFlag FLAG_UNK_0x0033
    Return

// 2.17: the player crosses the row below the Gym (x681-684, z616). Looker (681,617) lowers the newspaper and
// steps over to stand right below the player.
VeilstoneCity_Arc2LookerCheck:
    LockAll
    SetVar VAR_MAP_LOCAL_1, 0
    ApplyMovement LOCALID_ARC2_LOOKER, VeilstoneCity_Arc2Movement_Notice
    WaitMovement
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 682, VeilstoneCity_Arc2LookerStepEast1
    CallIfEq VAR_0x8004, 683, VeilstoneCity_Arc2LookerStepEast2
    CallIfEq VAR_0x8004, 684, VeilstoneCity_Arc2LookerStepEast3
    ApplyMovement LOCALID_ARC2_LOOKER, VeilstoneCity_Arc2Movement_FaceNorth
    ApplyMovement LOCALID_PLAYER, VeilstoneCity_Arc2Movement_FaceSouth
    WaitMovement
    GoTo VeilstoneCity_Arc2LookerScene
    End

VeilstoneCity_Arc2LookerStepEast1:
    ApplyMovement LOCALID_ARC2_LOOKER, VeilstoneCity_Arc2Movement_East1
    WaitMovement
    Return

VeilstoneCity_Arc2LookerStepEast2:
    ApplyMovement LOCALID_ARC2_LOOKER, VeilstoneCity_Arc2Movement_East2
    WaitMovement
    Return

VeilstoneCity_Arc2LookerStepEast3:
    ApplyMovement LOCALID_ARC2_LOOKER, VeilstoneCity_Arc2Movement_East3
    WaitMovement
    Return

// Talking to him first (from beside him) runs the same scene
VeilstoneCity_Arc2LookerTalk:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    SetVar VAR_MAP_LOCAL_1, 0
    FacePlayer
    GoTo VeilstoneCity_Arc2LookerScene
    End

VeilstoneCity_Arc2LookerScene:
    SetLookerBGM
    Message VeilstoneCity_Text_Arc2LookerDisguise
    WaitABXPadPress
    Message VeilstoneCity_Text_Arc2LookerRanName
    WaitABXPadPress
    Message VeilstoneCity_Text_Arc2LookerNoRecord
    WaitABXPadPress
    Message VeilstoneCity_Text_Arc2LookerNotExist
    WaitABXPadPress
    Message VeilstoneCity_Text_Arc2LookerTrust
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, VeilstoneCity_Arc2LookerTrustYes
    Message VeilstoneCity_Text_Arc2LookerTrustNo
    WaitABXPadPress
    GoTo VeilstoneCity_Arc2LookerFavor
    End

VeilstoneCity_Arc2LookerTrustYes:
    AddVar VAR_ARC2_CHOICES, 1
    Message VeilstoneCity_Text_Arc2LookerTrustYes
    WaitABXPadPress
    GoTo VeilstoneCity_Arc2LookerFavor
    End

VeilstoneCity_Arc2LookerFavor:
    Message VeilstoneCity_Text_Arc2LookerFavor
    WaitABXPadPress
    Message VeilstoneCity_Text_Arc2LookerSideDoor
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 51
    // Newspaper up again (upside down), and off he goes
    ApplyMovement LOCALID_ARC2_LOOKER, VeilstoneCity_Arc2Movement_LookerLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_LOOKER
    FadeToDefaultMusic
    ReleaseAll
    End

// 2.17b: Maylene at the meteorite garden (stock meteorites = the Meteor Shrine), Cyrus at the far edge
VeilstoneCity_Arc2Maylene:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message VeilstoneCity_Text_Arc2MayleneBond
    WaitABXPadPress
    Message VeilstoneCity_Text_Arc2MayleneStar
    WaitABXPadPress
    Message VeilstoneCity_Text_Arc2MayleneMega
    WaitABXPadPress
    Message VeilstoneCity_Text_Arc2MayleneForced
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC2_CYRUS, VeilstoneCity_Arc2Movement_FaceWest
    WaitMovement
    Message VeilstoneCity_Text_Arc2CyrusRocks
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC2_CYRUS, VeilstoneCity_Arc2Movement_FaceEast
    WaitMovement
    Message VeilstoneCity_Text_Arc2MayleneShowMe
    WaitABXPadPress
    CloseMessage
    StartTrainerBattle TRAINER_LEADER_MAYLENE_METEOR_TRIAL
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, VeilstoneCity_Arc2MayleneLost
    Message VeilstoneCity_Text_Arc2MayleneThatsIt
    WaitABXPadPress
    AddItem ITEM_KEY_STONE, 1, VAR_RESULT
    BufferPlayerName 0
    PlaySound SEQ_FANFA3
    Message VeilstoneCity_Text_Arc2GotKeyStone
    WaitSound
    WaitABXPadPress
    CloseMessage
    // The stone box: three Mega Stones glow
    ApplyMovement LOCALID_ARC2_MAYLENE, VeilstoneCity_Arc2Movement_FaceEast
    WaitMovement
    PlayFanfare SEQ_SE_DP_KIRAKIRA
    WaitFanfare SEQ_SE_DP_KIRAKIRA
    WaitTime 15, VAR_RESULT
    Message VeilstoneCity_Text_Arc2MayleneBox
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC2_MAYLENE, VeilstoneCity_Arc2Movement_FaceWest
    WaitMovement
    Message VeilstoneCity_Text_Arc2MayleneYours
    WaitABXPadPress
    // The Mega Stone for the player's starter line
    GetPlayerStarterSpecies VAR_RESULT
    SetVar VAR_0x8004, ITEM_TORTERRITE
    CallIfEq VAR_RESULT, SPECIES_CHIMCHAR, VeilstoneCity_Arc2StoneInfernapite
    CallIfEq VAR_RESULT, SPECIES_PIPLUP, VeilstoneCity_Arc2StoneEmpoleonite
    AddItem VAR_0x8004, 1, VAR_RESULT
    BufferPlayerName 0
    BufferItemName 1, VAR_0x8004
    PlaySound SEQ_FANFA4
    Message VeilstoneCity_Text_Arc2GotMegaStone
    WaitSound
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 57
    ClearFlag FLAG_ARC2_VEILSTONE_C
    // Time passes toward evening (2.17d is at the Pokemon Center)
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_ARC2_MAYLENE
    RemoveObject LOCALID_ARC2_CYRUS
    RemoveObject LOCALID_ARC2_STONE_BOX
    WaitTime 20, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

VeilstoneCity_Arc2StoneInfernapite:
    SetVar VAR_0x8004, ITEM_INFERNAPITE
    Return

VeilstoneCity_Arc2StoneEmpoleonite:
    SetVar VAR_0x8004, ITEM_EMPOLEONITE
    Return

VeilstoneCity_Arc2MayleneLost:
    BlackOutFromBattle
    ReleaseAll
    End

VeilstoneCity_Arc2Cyrus:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message VeilstoneCity_Text_Arc2CyrusRocks
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC2_CYRUS, VeilstoneCity_Arc2Movement_FaceEast
    WaitMovement
    ReleaseAll
    End

VeilstoneCity_Arc2StoneBox:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message VeilstoneCity_Text_Arc2StoneBox
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
VeilstoneCity_Arc2Movement_Notice:
    EmoteExclamationMark
    Delay8
    EndMovement

    .balign 4, 0
VeilstoneCity_Arc2Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
VeilstoneCity_Arc2Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
VeilstoneCity_Arc2Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
VeilstoneCity_Arc2Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
VeilstoneCity_Arc2Movement_East1:
    WalkNormalEast
    EndMovement

    .balign 4, 0
VeilstoneCity_Arc2Movement_East2:
    WalkNormalEast 2
    EndMovement

    .balign 4, 0
VeilstoneCity_Arc2Movement_East3:
    WalkNormalEast 3
    EndMovement

    .balign 4, 0
VeilstoneCity_Arc2Movement_LookerLeave:
    FaceSouth
    Delay8
    WalkNormalSouth 6
    EndMovement
