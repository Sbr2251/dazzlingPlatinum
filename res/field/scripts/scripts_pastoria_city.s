#include "macros/scrcmd.inc"
#include "res/text/bank/pastoria_city.h"
#include "res/field/events/events_pastoria_city.h"


    ScriptEntry _005E
    ScriptEntry _00B2
    ScriptEntry _00C5
    ScriptEntry _00D8
    ScriptEntry _00EB
    ScriptEntry _00FE
    ScriptEntry _01D2
    ScriptEntry _01E5
    ScriptEntry PastoriaGity_GalacticGrunt
    ScriptEntry _012F
    ScriptEntry _01AC
    ScriptEntry _01BF
    ScriptEntry _03E4
    ScriptEntry _03FB
    ScriptEntry _0410
    ScriptEntry _0427
    ScriptEntry _043E
    ScriptEntry _04C8
    ScriptEntry _05E0
    ScriptEntry _09A8
    ScriptEntry _07F8
    ScriptEntry _0B90
    ScriptEntry _0BF0
    ScriptEntry PastoriaCity_Arc2LookerFrame
    ScriptEntry PastoriaCity_Arc2LookerTalk
    ScriptEntryEnd

_005E:
    Call PastoriaCity_Arc2Transition
    SetVar VAR_UNK_0x40C7, 0
    SetFlag FLAG_UNK_0x017E
    CallIfEq VAR_PASTORIA_STATE, 5, _074D
    CallIfEq VAR_PASTORIA_STATE, 4, _0721
    CallIfEq VAR_PASTORIA_STATE, 4, _0737
    GoToIfSet FLAG_UNK_0x0102, _009C
    End

_009C:
    SetObjectEventPos PASTORIA_CITY_GRUNT_M, 0x27D, 0x32C
    SetObjectEventDir PASTORIA_CITY_GRUNT_M, DIR_EAST
    SetObjectEventMovementType PASTORIA_CITY_GRUNT_M, MOVEMENT_TYPE_LOOK_EAST
    End

_00B2:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 29
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00C5:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 30
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00D8:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 31
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00EB:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 32
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00FE:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfBadgeAcquired BADGE_ID_FEN, _0124
    Message 33
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0124:
    Message 34
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_012F:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x0128, _0189
    GetPlayerStarterSpecies VAR_RESULT
    CallIfEq VAR_RESULT, SPECIES_TURTWIG, _0194
    CallIfEq VAR_RESULT, SPECIES_CHIMCHAR, _019C
    CallIfEq VAR_RESULT, SPECIES_PIPLUP, _01A4
    BufferAccessoryName 0, VAR_0x8004
    Message 37
    SetVar VAR_0x8005, 1
    GiveAccessoryWaitForConfirm
    SetFlag FLAG_UNK_0x0128
    CloseMessage
    ReleaseAll
    End

_0189:
    Message 38
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0194:
    SetVar VAR_0x8004, ACCESSORY_CHIMCHAR_MASK
    Return

_019C:
    SetVar VAR_0x8004, ACCESSORY_PIPLUP_MASK
    Return

_01A4:
    SetVar VAR_0x8004, ACCESSORY_TURTWIG_MASK
    Return

_01AC:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 39
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_01BF:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 40
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_01D2:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 35
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_01E5:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_CLEFAIRY
    Message 36
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

PastoriaGity_GalacticGrunt:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfSet FLAG_UNK_0x0102, _0220
    Message PastoriaCity_Text_GalacticGruntPackageHasntArrived
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0220:
    FacePlayer
    Message 28
    CloseMessage
    GetPlayerDir VAR_RESULT
    GoToIfEq VAR_RESULT, 2, _025A
    GoToIfEq VAR_RESULT, 3, _027A
    GoToIfEq VAR_RESULT, 0, _0292
    GoTo _02B2
    End

_025A:
    SetVar VAR_0x8007, 2
    ApplyMovement PASTORIA_CITY_GRUNT_M, _0388
    ApplyMovement LOCALID_PLAYER, _02EC
    WaitMovement
    GoTo _02D2
    End

_027A:
    SetVar VAR_0x8007, 3
    ApplyMovement PASTORIA_CITY_GRUNT_M, _0398
    WaitMovement
    GoTo _02D2
    End

_0292:
    SetVar VAR_0x8007, 0
    ApplyMovement PASTORIA_CITY_GRUNT_M, _0398
    ApplyMovement LOCALID_PLAYER, _030C
    WaitMovement
    GoTo _02D2
    End

_02B2:
    SetVar VAR_0x8007, 1
    ApplyMovement PASTORIA_CITY_GRUNT_M, _0398
    ApplyMovement LOCALID_PLAYER, _0304
    WaitMovement
    GoTo _02D2
    End

_02D2:
    PlayFanfare SEQ_SE_DP_KAIDAN2
    RemoveObject PASTORIA_CITY_GRUNT_M
    SetFlag FLAG_UNK_0x0103
    ReleaseAll
    End

    .balign 4, 0
PastoriaCity_UnusedMovement:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_02EC:
    WalkOnSpotNormalSouth
    WalkOnSpotNormalEast
    EndMovement

PastoriaCity_UnusedMovement2:
    WalkOnSpotNormalNorth
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0304:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_030C:
    WalkOnSpotNormalEast
    EndMovement

PastoriaCity_UnusedMovement3:
    WalkOnSpotNormalSouth
    WalkOnSpotNormalEast
    EndMovement

PastoriaCity_UnusedMovement4:
    WalkOnSpotNormalSouth
    WalkOnSpotNormalEast
    EndMovement

PastoriaCity_UnusedMovement5:
    WalkOnSpotNormalNorth
    WalkOnSpotNormalEast
    EndMovement

PastoriaCity_UnusedMovement6:
    WalkOnSpotNormalSouth
    WalkOnSpotNormalEast
    EndMovement

PastoriaCity_UnusedMovement7:
    WalkFastEast 9
    EndMovement

PastoriaCity_UnusedMovement8:
    WalkFastEast 7
    EndMovement

PastoriaCity_UnusedMovement9:
    WalkFastSouth
    WalkFastEast 8
    EndMovement

PastoriaCity_UnusedMovement10:
    WalkFastNorth
    WalkFastEast 8
    EndMovement

PastoriaCity_UnusedMovement11:
    EmoteExclamationMark
    EndMovement

PastoriaCity_UnusedMovement12:
    WalkFastSouth
    WalkFastEast 10
    EndMovement

PastoriaCity_UnusedMovement13:
    WalkFastEast 10
    EndMovement

    .balign 4, 0
_0388:
    WalkFastSouth
    WalkFastEast 2
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
_0398:
    WalkFastEast 2
    WalkOnSpotFastEast
    EndMovement

PastoriaCity_UnusedMovement14:
    WalkFastSouth
    WalkFastEast 2
    WalkOnSpotFastEast
    EndMovement

PastoriaCity_UnusedMovement15:
    WalkFastSouth
    WalkFastEast 4
    WalkOnSpotFastEast
    EndMovement

PastoriaCity_UnusedMovement16:
    WalkFastNorth
    WalkFastEast 3
    WalkOnSpotFastEast
    EndMovement

PastoriaCity_UnusedMovement17:
    WalkFastSouth
    WalkFastEast 3
    WalkOnSpotFastEast
    EndMovement

_03E4:
    ShowMapSign 41
    End

_03FB:
    ShowScrollingSign 42
    End

_0410:
    ShowLandmarkSign 43
    End

_0427:
    ShowLandmarkSign 44
    End

_043E:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfGe VAR_PASTORIA_STATE, 5, _04AE
    GoToIfGe VAR_PASTORIA_STATE, 4, _0471
    BufferRivalName 0
    BufferPlayerName 1
    Message 4
    GoTo _04A6
    End

_0471:
    GetPlayerDir VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _0498
    BufferRivalName 0
    Message 16
    CloseMessage
    ApplyMovement PASTORIA_CITY_RIVAL, _04C0
    WaitMovement
    ReleaseAll
    End

_0498:
    BufferRivalName 0
    Message 15
    GoTo _04A6
    End

_04A6:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_04AE:
    BufferRivalName 0
    BufferPlayerName 1
    Message 27
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
_04C0:
    WalkOnSpotNormalSouth
    EndMovement

_04C8:
    LockAll
    ClearFlag FLAG_UNK_0x01A9
    SetObjectEventPos PASTORIA_CITY_RIVAL, 0x253, 0x333
    SetObjectEventMovementType PASTORIA_CITY_RIVAL, MOVEMENT_TYPE_LOOK_WEST
    SetObjectEventDir PASTORIA_CITY_RIVAL, DIR_WEST
    AddObject PASTORIA_CITY_RIVAL
    ApplyMovement PASTORIA_CITY_RIVAL, _05B0
    WaitMovement
    SetRivalBGM
    ApplyMovement PASTORIA_CITY_RIVAL, _05C0
    ApplyMovement LOCALID_PLAYER, _05A4
    WaitMovement
    BufferRivalName 0
    BufferPlayerName 1
    Message 5
    CloseMessage
    ApplyMovement PASTORIA_CITY_RIVAL, _05CC
    WaitMovement
    GetPlayerStarterSpecies VAR_RESULT
    GoToIfEq VAR_RESULT, SPECIES_TURTWIG, _054B
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, _0557
    GoTo _053F

_053F:
    StartTrainerBattle TRAINER_RIVAL_PASTORIA_CITY_PIPLUP
    GoTo _0563

_054B:
    StartTrainerBattle TRAINER_RIVAL_PASTORIA_CITY_TURTWIG
    GoTo _0563

_0557:
    StartTrainerBattle TRAINER_RIVAL_PASTORIA_CITY_CHIMCHAR
    GoTo _0563

_0563:
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _0597
    BufferRivalName 0
    BufferPlayerName 1
    Message 6
    CloseMessage
    ApplyMovement PASTORIA_CITY_RIVAL, _05D4
    WaitMovement
    RemoveObject PASTORIA_CITY_RIVAL
    SetVar VAR_PASTORIA_STATE, 2
    ReleaseAll
    End

_0597:
    SetFlag FLAG_UNK_0x01A9
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
_05A4:
    Delay4 13
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_05B0:
    WalkFastSouth 9
    WalkOnSpotFastWest
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_05C0:
    WalkFastWest 4
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
_05CC:
    WalkNormalWest
    EndMovement

    .balign 4, 0
_05D4:
    WalkFastEast 5
    WalkFastNorth 9
    EndMovement

_05E0:
    LockAll
    ClearFlag FLAG_UNK_0x01A9
    SetObjectEventPos PASTORIA_CITY_RIVAL, 0x253, 0x333
    SetObjectEventMovementType PASTORIA_CITY_RIVAL, MOVEMENT_TYPE_LOOK_SOUTH
    SetObjectEventDir PASTORIA_CITY_RIVAL, DIR_SOUTH
    AddObject PASTORIA_CITY_RIVAL
    LockObject PASTORIA_CITY_RIVAL
    ApplyMovement PASTORIA_CITY_RIVAL, _0798
    ApplyMovement LOCALID_PLAYER, _07CC
    WaitMovement
    BufferRivalName 0
    BufferPlayerName 1
    Message 7
    CloseMessage
    LoadDoorAnimation 18, 25, 13, 27, ANIMATION_TAG_DOOR_1
    PlayDoorOpenAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement LOCALID_PLAYER, _07D8
    WaitMovement
    ClearFlag FLAG_UNK_0x01FB
    SetObjectEventPos PASTORIA_CITY_CRASHER_WAKE, 0x24D, 0x33B
    SetObjectEventDir PASTORIA_CITY_CRASHER_WAKE, DIR_NORTH
    SetObjectEventMovementType PASTORIA_CITY_CRASHER_WAKE, MOVEMENT_TYPE_LOOK_NORTH
    AddObject PASTORIA_CITY_CRASHER_WAKE
    LockObject PASTORIA_CITY_CRASHER_WAKE
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _0764
    WaitMovement
    PlayDoorCloseAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    UnloadAnimation ANIMATION_TAG_DOOR_1
    SetFlag FLAG_UNK_0x020F
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _076C
    WaitMovement
    Message 8
    CloseMessage
    ApplyMovement PASTORIA_CITY_RIVAL, _07A4
    WaitMovement
    BufferRivalName 0
    Message 9
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _077C
    WaitMovement
    Message 10
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _0784
    WaitMovement
    Message 11
    BufferRivalName 0
    Message 12
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _077C
    WaitMovement
    Message 13
    CloseMessage
    ApplyMovement LOCALID_PLAYER, _07EC
    ApplyMovement PASTORIA_CITY_RIVAL, _07AC
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _078C
    WaitMovement
    BufferRivalName 0
    Message 14
    CloseMessage
    ApplyMovement PASTORIA_CITY_RIVAL, _07C0
    WaitMovement
    Call _0737
    ClearFlag FLAG_UNK_0x01FB
    SetPosition PASTORIA_CITY_CRASHER_WAKE, 0x263, 0, 0x32A, 0
    Call _0721
    ClearFlag FLAG_UNK_0x01A9
    SetPosition PASTORIA_CITY_RIVAL, 0x260, 0, 0x32E, 1
    SetVar VAR_PASTORIA_STATE, 4
    ReleaseAll
    End

_0721:
    SetObjectEventPos PASTORIA_CITY_RIVAL, 0x260, 0x32E
    SetObjectEventDir PASTORIA_CITY_RIVAL, DIR_SOUTH
    SetObjectEventMovementType PASTORIA_CITY_RIVAL, MOVEMENT_TYPE_LOOK_SOUTH
    Return

_0737:
    SetObjectEventPos PASTORIA_CITY_CRASHER_WAKE, 0x263, 0x32A
    SetObjectEventDir PASTORIA_CITY_CRASHER_WAKE, DIR_NORTH
    SetObjectEventMovementType PASTORIA_CITY_CRASHER_WAKE, MOVEMENT_TYPE_LOOK_NORTH
    Return

_074D:
    SetObjectEventPos PASTORIA_CITY_RIVAL, 0x263, 0x32A
    SetObjectEventDir PASTORIA_CITY_RIVAL, DIR_NORTH
    SetObjectEventMovementType PASTORIA_CITY_RIVAL, MOVEMENT_TYPE_LOOK_NORTH
    Return

    .balign 4, 0
_0764:
    WalkNormalSouth
    EndMovement

    .balign 4, 0
_076C:
    WalkOnSpotNormalEast
    Delay8 2
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_077C:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0784:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_078C:
    WalkFastEast 6
    WalkFastNorth 8
    EndMovement

    .balign 4, 0
_0798:
    WalkFastSouth 9
    WalkFastWest 5
    EndMovement

    .balign 4, 0
_07A4:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_07AC:
    LockDir
    WalkFastSouth
    UnlockDir
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
_07C0:
    WalkFastEast 5
    WalkFastNorth 8
    EndMovement

    .balign 4, 0
_07CC:
    Delay4 11
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_07D8:
    WalkOnSpotNormalNorth
    Delay8 2
    WalkNormalSouth
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_07EC:
    Delay8
    WalkOnSpotNormalEast
    EndMovement

_07F8:
    LockAll
    Call _086F
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _0B6C
    ApplyMovement PASTORIA_CITY_RIVAL, _0B08
    ApplyMovement LOCALID_PLAYER, _0AAC
    ApplyMovement PASTORIA_CITY_GRUNT_M, _0B44
    WaitMovement
    Call _08D9
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _0B74
    ApplyMovement PASTORIA_CITY_RIVAL, _0B3C
    ApplyMovement LOCALID_PLAYER, _0AC8
    ApplyMovement PASTORIA_CITY_GRUNT_M, _0B54
    WaitMovement
    Call _08FA
    Message 23
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _0B80
    ApplyMovement LOCALID_PLAYER, _0AD4
    WaitMovement
    Call _091C
    ReleaseAll
    End

_086F:
    ApplyMovement PASTORIA_CITY_RIVAL, _0AE4
    WaitMovement
    BufferRivalName 0
    Message 17
    CloseMessage
    ApplyMovement LOCALID_PLAYER, _0AA4
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _0B5C
    WaitMovement
    Message 18
    ApplyMovement PASTORIA_CITY_RIVAL, _0AF0
    WaitMovement
    PlayFanfare SEQ_SE_DP_FW291
    WaitTime 4, VAR_RESULT
    Message 19
    WaitFanfare SEQ_SE_CONFIRM
    ScrCmd_29F 1
    CloseMessage
    ClearFlag FLAG_UNK_0x020C
    SetObjectEventPos PASTORIA_CITY_GRUNT_M, 0x262, 0x328
    SetObjectEventDir PASTORIA_CITY_GRUNT_M, DIR_EAST
    SetObjectEventMovementType PASTORIA_CITY_GRUNT_M, MOVEMENT_TYPE_LOOK_EAST
    AddObject PASTORIA_CITY_GRUNT_M
    LockObject PASTORIA_CITY_GRUNT_M
    Return

_08D9:
    Message 20
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _0B6C
    WaitMovement
    Message 21
    ApplyMovement PASTORIA_CITY_GRUNT_M, _0B4C
    WaitMovement
    Message 22
    CloseMessage
    Return

_08FA:
    RemoveObject PASTORIA_CITY_GRUNT_M
    ClearFlag FLAG_UNK_0x020C
    SetObjectEventPos PASTORIA_CITY_GRUNT_M, 0x27D, 0x32C
    SetObjectEventMovementType PASTORIA_CITY_GRUNT_M, MOVEMENT_TYPE_LOOK_EAST
    SetObjectEventDir PASTORIA_CITY_GRUNT_M, DIR_EAST
    AddObject PASTORIA_CITY_GRUNT_M
    Return

_091C:
    Message 24
    CloseMessage
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _0B88
    ApplyMovement LOCALID_PLAYER, _099C
    WaitMovement
    RemoveObject PASTORIA_CITY_CRASHER_WAKE
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 0x261, _0981
    CallIfEq VAR_0x8004, 0x263, _098D
    CallIfEq VAR_0x8004, 0x264, _0981
    SetFlag FLAG_UNK_0x020D
    SetVar VAR_PASTORIA_STATE, 5
    SetFlag FLAG_UNK_0x0102
    BufferRivalName 0
    BufferPlayerName 1
    Message 25
    WaitABXPadPress
    CloseMessage
    Return

_0981:
    ApplyMovement PASTORIA_CITY_RIVAL, _0B1C
    WaitMovement
    Return

_098D:
    ApplyMovement PASTORIA_CITY_RIVAL, _0B28
    WaitMovement
    Return

    .balign 4, 0
_099C:
    Delay8
    FaceNorth
    EndMovement

_09A8:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Call _086F
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 0x263, _0A31
    CallIfEq VAR_0x8004, 0x264, _0A55
    Call _08D9
    ApplyMovement LOCALID_PLAYER, _0AC8
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _0B74
    ApplyMovement PASTORIA_CITY_RIVAL, _0B3C
    ApplyMovement PASTORIA_CITY_GRUNT_M, _0B54
    WaitMovement
    Call _08FA
    Message 23
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 0x263, _0A79
    CallIfEq VAR_0x8004, 0x264, _0A8D
    Call _091C
    ReleaseAll
    End

_0A31:
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _0B6C
    ApplyMovement LOCALID_PLAYER, _0ABC
    ApplyMovement PASTORIA_CITY_RIVAL, _0B10
    ApplyMovement PASTORIA_CITY_GRUNT_M, _0B44
    WaitMovement
    Return

_0A55:
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _0B6C
    ApplyMovement LOCALID_PLAYER, _0ABC
    ApplyMovement PASTORIA_CITY_RIVAL, _0B10
    ApplyMovement PASTORIA_CITY_GRUNT_M, _0B44
    WaitMovement
    Return

_0A79:
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _0B80
    ApplyMovement LOCALID_PLAYER, _0AD4
    WaitMovement
    Return

_0A8D:
    ApplyMovement PASTORIA_CITY_CRASHER_WAKE, _0B80
    ApplyMovement LOCALID_PLAYER, _0ADC
    WaitMovement
    Return

    .balign 4, 0
_0AA4:
    FaceNorth
    EndMovement

    .balign 4, 0
_0AAC:
    WalkFastSouth
    WalkFastEast
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
_0ABC:
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0AC8:
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0AD4:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0ADC:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0AE4:
    WalkFastNorth 3
    WalkFastEast
    EndMovement

    .balign 4, 0
_0AF0:
    WalkOnSpotFastNorth
    EndMovement

PastoriaCity_UnusedMovement18:
    WalkFastSouth 3
    EndMovement

PastoriaCity_UnusedMovement19:
    WalkOnSpotFastNorth
    EndMovement

    .balign 4, 0
_0B08:
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
_0B10:
    Delay8
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
_0B1C:
    WalkFastEast 2
    WalkFastNorth
    EndMovement

    .balign 4, 0
_0B28:
    WalkFastEast
    WalkFastNorth
    WalkFastEast
    WalkOnSpotFastNorth
    EndMovement

    .balign 4, 0
_0B3C:
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
_0B44:
    WalkFastSouth 4
    EndMovement

    .balign 4, 0
_0B4C:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0B54:
    WalkFastEast 12
    EndMovement

    .balign 4, 0
_0B5C:
    WalkOnSpotNormalNorth
    EndMovement

PastoriaCity_UnusedMovement20:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0B6C:
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
_0B74:
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0B80:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0B88:
    WalkNormalNorth 2
    EndMovement

_0B90:
    LockAll
    ApplyMovement LOCALID_PLAYER, _0BC8
    ApplyMovement PASTORIA_CITY_RIVAL, _0BD8
    WaitMovement
    BufferRivalName 0
    BufferPlayerName 1
    Message 26
    CloseMessage
    ApplyMovement LOCALID_PLAYER, _0BD0
    ApplyMovement PASTORIA_CITY_RIVAL, _0BE0
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
_0BC8:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0BD0:
    WalkNormalSouth
    EndMovement

    .balign 4, 0
_0BD8:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0BE0:
    WalkNormalWest
    WalkNormalEast
    WalkOnSpotNormalNorth
    EndMovement

_0BF0:
    LockAll
    GoToIfSet FLAG_UNK_0x0156, _0C1E
    SetVar VAR_UNK_0x40C7, 1
    GetRandom VAR_RESULT, 100
    GoToIfGe VAR_RESULT, 90, _0C22
    GoTo _0C1E
    End

_0C1E:
    ReleaseAll
    End

_0C22:
    ClearFlag FLAG_UNK_0x029D
    AddObject 28
    ApplyMovement LOCALID_PLAYER, _0C78
    ApplyMovement 28, _0C64
    WaitMovement
    PlayCry SPECIES_CROAGUNK
    WaitCry
    WaitTime 30, VAR_RESULT
    ApplyMovement 28, _0C70
    WaitMovement
    PlayFanfare SEQ_SE_DP_KAIDAN2
    RemoveObject 28
    WaitFanfare SEQ_SE_DP_KAIDAN2
    ReleaseAll
    End

    .balign 4, 0
_0C64:
    WalkNormalNorth 7
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0C70:
    WalkNormalNorth 5
    EndMovement

    .balign 4, 0
_0C78:
    WalkOnSpotNormalSouth
    EndMovement

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 2, workstream s-pastoria: screenplay 2.20 (Gym 4, Looker's request, the Valor Basin),
// 2.21a (Looker's briefing, Pastoria Pokemon Center) and 2.22 (Rowan sees the proof, same Center).
// VAR_ARC2_PROGRESS block 70-79 plus 85-86:
//   71  Fen Badge (Pastoria Gym; or this OnTransition, if the badge came before the arc reached 69)
//   72  Looker's request heard (outside the Gym, this map)
//   73  Garius found at the Basin fence (lake_valor_drained); the night question is asked at 73
//   75  Looker's briefing done (Center); warps to Route 213 (687,832) for s-raid
//   85  2.22 started (Center, after s-raid warps in at 84)   86  2.22 done
// Flags (FLAG_ARC2_PASTORIA_A..D, 0x094D-0x0950):
//   FLAG_ARC2_PASTORIA_A (0x094D) = the Basin question has been asked (answer in VAR_ARC2_CHOICES bit 1)
//   FLAG_ARC2_PASTORIA_B (0x094E) = Center briefing group hidden (Looker, Ruth, Cyrus, Garius; shown only at 73)
//   FLAG_ARC2_PASTORIA_C (0x094F) = Center 2.22 group hidden (Rowan, Looker, Ruth, Cyrus; shown only at 84-85)
//   FLAG_ARC2_PASTORIA_D (0x0950) = unused (free for the lead)
// The Center keeps its stock OnTransition (common script 10400), so its hide flags are persistent and are
// recomputed here on every Pastoria City load; the Center scenes also re-show their group themselves.
// Map-local: FLAG_UNK_0x0030 = Looker (outside the Gym) hidden; VAR_MAP_LOCAL_1 = 1 arms the on-frame check (not _0: the frame-table reader stops at a var whose low byte is 0).
// Great Marsh grunt/bomb plot cut: the stock rival, Wake and grunt objects stay hidden and VAR_PASTORIA_STATE
// is parked at 6 (the stock "plot over" value), so none of its coord events or the state-3 frame script run.
// Never set FLAG_GALACTIC_LEFT_LAKE_VALOR (it would flip Valor Lakefront to the full lake; rift contract).

PastoriaCity_Arc2Transition:
    SetFlag FLAG_UNK_0x01A9
    SetFlag FLAG_UNK_0x020C
    SetFlag FLAG_UNK_0x01FB
    GoToIfGe VAR_PASTORIA_STATE, 6, PastoriaCity_Arc2TransitionBadge
    SetVar VAR_PASTORIA_STATE, 6
PastoriaCity_Arc2TransitionBadge:
    GoToIfLt VAR_ARC2_PROGRESS, 69, PastoriaCity_Arc2TransitionLooker
    GoToIfGe VAR_ARC2_PROGRESS, 71, PastoriaCity_Arc2TransitionLooker
    // Not GoToIfBadgeAcquired: VAR_RESULT is script-local memory, which hangs the OnTransition run at load.
    CheckBadgeAcquired BADGE_ID_FEN, VAR_MAP_LOCAL_2
    GoToIfEq VAR_MAP_LOCAL_2, TRUE, PastoriaCity_Arc2TransitionSet71
    GoTo PastoriaCity_Arc2TransitionLooker

PastoriaCity_Arc2TransitionSet71:
    SetVar VAR_ARC2_PROGRESS, 71
PastoriaCity_Arc2TransitionLooker:
    SetFlag FLAG_UNK_0x0030
    GoToIfNe VAR_ARC2_PROGRESS, 71, PastoriaCity_Arc2TransitionCenter
    ClearFlag FLAG_UNK_0x0030
    SetVar VAR_MAP_LOCAL_1, 1
PastoriaCity_Arc2TransitionCenter:
    SetFlag FLAG_ARC2_PASTORIA_B
    GoToIfNe VAR_ARC2_PROGRESS, 73, PastoriaCity_Arc2TransitionRowan
    ClearFlag FLAG_ARC2_PASTORIA_B
PastoriaCity_Arc2TransitionRowan:
    SetFlag FLAG_ARC2_PASTORIA_C
    GoToIfLt VAR_ARC2_PROGRESS, 84, PastoriaCity_Arc2TransitionEnd
    GoToIfGt VAR_ARC2_PROGRESS, 85, PastoriaCity_Arc2TransitionEnd
    ClearFlag FLAG_ARC2_PASTORIA_C
PastoriaCity_Arc2TransitionEnd:
    Return

// On-frame (VAR_MAP_LOCAL_1 == 1, armed at 71): stepping out of the Gym, Looker comes over from the lamppost.
// Anywhere else (Fly, the Route 213 gate) he just waits by the Gym to be talked to.
PastoriaCity_Arc2LookerFrame:
    SetVar VAR_MAP_LOCAL_1, 0
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8004, 589, PastoriaCity_Arc2LookerFrameEnd
    GoToIfNe VAR_0x8005, 828, PastoriaCity_Arc2LookerFrameEnd
    LockAll
    ApplyMovement LOCALID_ARC2_LOOKER, PastoriaCity_Arc2Movement_LookerToGym
    WaitMovement
    ApplyMovement LOCALID_PLAYER, PastoriaCity_Arc2Movement_FaceEast
    WaitMovement
    GoTo PastoriaCity_Arc2LookerScene
    End

PastoriaCity_Arc2LookerFrameEnd:
    End

PastoriaCity_Arc2LookerTalk:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfEq VAR_ARC2_PROGRESS, 71, PastoriaCity_Arc2LookerScene
    Message PastoriaCity_Text_Arc2LookerEveryEye
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

PastoriaCity_Arc2LookerScene:
    Message PastoriaCity_Text_Arc2LookerHello
    WaitABXPadPress
    Message PastoriaCity_Text_Arc2LookerManifest
    WaitABXPadPress
    Message PastoriaCity_Text_Arc2LookerEveryEye
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 72
    ReleaseAll
    End

    .balign 4, 0
PastoriaCity_Arc2Movement_LookerToGym:
    WalkNormalWest
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
PastoriaCity_Arc2Movement_FaceEast:
    FaceEast
    EndMovement
