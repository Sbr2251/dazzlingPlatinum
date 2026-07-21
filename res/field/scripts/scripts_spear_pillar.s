#include "macros/scrcmd.inc"
#include "generated/distribution_events.h"
#include "res/text/bank/spear_pillar.h"
#include "generated/versions.h"


    ScriptEntry _0022
    ScriptEntry _0107
    ScriptEntry _0154
    ScriptEntry _0508
    ScriptEntry _0249
    ScriptEntry _0210
    ScriptEntry _0223
    ScriptEntry _0236
    ScriptEntryEnd

_0022:
    SetFlag FLAG_FIRST_ARRIVAL_SPEAR_PILLAR
    SetFlag FLAG_UNK_0x01C8
    SetFlag FLAG_UNK_0x01C9
    Call _00C7
    Call _0062
    GetPlayerGender VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, GENDER_MALE, _0052
    GoToIfEq VAR_MAP_LOCAL_0, GENDER_FEMALE, _005A
    End

_0052:
    SetVar VAR_OBJ_GFX_ID_0, 97
    End

_005A:
    SetVar VAR_OBJ_GFX_ID_0, 0
    End

_0062:
    CheckGameCompleted VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, 0, _00C5
    GetNationalDexEnabled VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, 0, _00C5
    CheckItem ITEM_AZURE_FLUTE, 1, VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, FALSE, _00C5
    CheckDistributionEvent DISTRIBUTION_EVENT_ARCEUS, VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, FALSE, _00C5
    GoToIfSet FLAG_UNK_0x011E, _00C5
    SetVar VAR_UNK_0x4118, 1
    GoTo _00C5
    End

_00C5:
    Return

_00C7:
    Dummy1F9 VAR_UNK_0x4098
    GoToIfEq VAR_UNK_0x4098, 0, _0101
    GoToIfEq VAR_UNK_0x4098, 1, _0101
    GoToIfEq VAR_UNK_0x4098, 2, _0101
    GoToIfEq VAR_UNK_0x4098, 3, _0101
    Return

_0101:
    SetFlag FLAG_UNK_0x01C5
    Return

_0107:
    End

_0109:
    GetGameVersion VAR_RESULT
    SetVar VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_RESULT, VERSION_DIAMOND, _0133
    GoToIfEq VAR_RESULT, VERSION_PLATINUM, _0133
    SetVar VAR_0x8004, VAR_0x8006
_0133:
    Return

SpearPillar_Unused:
    GetPlayerGender VAR_RESULT
    SetVar VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_RESULT, GENDER_FEMALE, SpearPillar_Unused2
    SetVar VAR_0x8004, VAR_0x8006
SpearPillar_Unused2:
    Return

_0154:
    LockAll
    GoToIfUnset FLAG_TOTEM_HITMONLEE_DEFEATED, _TotemsRemain
    GoToIfUnset FLAG_TOTEM_VESPIQUEN_DEFEATED, _TotemsRemain
    GoToIfUnset FLAG_TOTEM_SKARMORY_DEFEATED, _TotemsRemain
    GoToIfUnset FLAG_TOTEM_LAPRAS_DEFEATED, _TotemsRemain
    GoToIfUnset FLAG_TOTEM_SPIRITOMB_DEFEATED, _TotemsRemain
    GoToIfUnset FLAG_TOTEM_AGGRON_DEFEATED, _TotemsRemain
    GoToIfUnset FLAG_TOTEM_MAMOSWINE_DEFEATED, _TotemsRemain
    GoToIfUnset FLAG_TOTEM_KINGDRA_DEFEATED, _TotemsRemain
    SetVar VAR_SPEAR_PILLAR_PARALLEL_SCENE_STATE, 1
    Message 31
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_TotemsRemain:
    Message 32
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, _0204
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
_01E4:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_01EC:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_01F4:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_01FC:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0204:
    Delay4 5
    WalkNormalSouth
    EndMovement

_0210:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 2
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0223:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 44
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0236:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 43
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0249:
    LockAll
    Call _02DC
    Message 13
    WaitABXPadPress
    CloseMessage
    Message 18
    WaitABXPadPress
    CloseMessage
    Message 20
    WaitABXPadPress
    CloseMessage
    Message 24
    WaitABXPadPress
    CloseMessage
    Message 26
    WaitABXPadPress
    CloseMessage
    Message 27
    WaitABXPadPress
    CloseMessage
    Message 28
    WaitABXPadPress
    CloseMessage
    SetRivalBGM
    Call SpearPillar_SetRivalPartnerTeam
    StartTrainerBattle VAR_0x8004
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _02D0
    Message 29
    WaitABXPadPress
    CloseMessage
    Message 30
    WaitABXPadPress
    CloseMessage
    HealParty
    RemoveObject 5
    SetFlag FLAG_UNK_0x01C5
    SetVar VAR_SPEAR_PILLAR_PARALLEL_SCENE_STATE, 2
    GoTo _0508
    End

_02D0:
    SetVar VAR_SPEAR_PILLAR_PARALLEL_SCENE_STATE, 1
    BlackOutFromBattle
    ReleaseAll
    End

_02DC:
    ClearFlag FLAG_UNK_0x01C5
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    SetVar VAR_0x8008, VAR_0x8004
    GoToIfEq VAR_0x8008, 30, _0315
    GoToIfEq VAR_0x8008, 31, _0333
    GoToIfEq VAR_0x8008, 32, _0351
    Return

_0315:
    SetObjectEventPos 5, 31, 40
    AddObject 5
    ApplyMovement 5, _04F4
    WaitMovement
    ScrCmd_18C 5, 3
    Return

_0333:
    SetObjectEventPos 5, 30, 40
    AddObject 5
    ApplyMovement 5, _04F4
    WaitMovement
    ScrCmd_18C 5, 2
    Return

_0351:
    SetObjectEventPos 5, 31, 40
    AddObject 5
    ApplyMovement 5, _04F4
    WaitMovement
    ScrCmd_18C 5, 2
    Return

_036F:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    SetVar VAR_0x8008, VAR_0x8004
    GoToIfEq VAR_0x8008, 30, _03A4
    GoToIfEq VAR_0x8008, 31, _03BE
    GoToIfEq VAR_0x8008, 32, _03D8
    Return

_03A4:
    ScrCmd_18C 0xFF, 2
    ApplyMovement 4, _03F4
    ApplyMovement 2, _03FC
    WaitMovement
    Return

_03BE:
    ScrCmd_18C 0xFF, 3
    ApplyMovement 4, _0404
    ApplyMovement 2, _040C
    WaitMovement
    Return

_03D8:
    ScrCmd_18C 0xFF, 3
    ApplyMovement 4, _0414
    ApplyMovement 2, _041C
    WaitMovement
    Return

    .balign 4, 0
_03F4:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_03FC:
    WalkNormalWest
    EndMovement

    .balign 4, 0
_0404:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_040C:
    WalkNormalWest
    EndMovement

    .balign 4, 0
_0414:
    WalkNormalEast
    EndMovement

    .balign 4, 0
_041C:
    WalkOnSpotNormalWest
    EndMovement

SpearPillar_SetRivalPartnerTeam:
    GetPlayerStarterSpecies VAR_RESULT
    SetVar VAR_0x8004, TRAINER_RIVAL_SPEAR_PILLAR_BAGON
    GoToIfEq VAR_RESULT, SPECIES_BAGON, SpearPillar_Return
    SetVar VAR_0x8004, TRAINER_RIVAL_SPEAR_PILLAR_GIBLE
    GoToIfEq VAR_RESULT, SPECIES_GIBLE, SpearPillar_Return
    SetVar VAR_0x8004, TRAINER_RIVAL_SPEAR_PILLAR_DRATINI
SpearPillar_Return:
    Return

_0456:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    SetVar VAR_0x8008, VAR_0x8004
    GoToIfEq VAR_0x8008, 30, _048B
    GoToIfEq VAR_0x8008, 31, _0499
    GoToIfEq VAR_0x8008, 32, _04A7
    Return

_048B:
    ScrCmd_18C 0xFF, 3
    ScrCmd_18C 5, 2
    Return

_0499:
    ScrCmd_18C 0xFF, 2
    ScrCmd_18C 5, 3
    Return

_04A7:
    ScrCmd_18C 0xFF, 2
    ScrCmd_18C 5, 3
    Return

SpearPillar_Unused3:
    ApplyMovement 4, SpearPillar_UnusedMovement
    ApplyMovement 2, SpearPillar_UnusedMovement2
    WaitMovement
    Return

    .balign 4, 0
SpearPillar_UnusedMovement:
    FaceEast
    LockDir
    WalkSlowWest
    UnlockDir
    EndMovement

SpearPillar_UnusedMovement2:
    FaceWest
    LockDir
    WalkSlowEast
    UnlockDir
    EndMovement

    .balign 4, 0
_04F4:
    Delay4 2
    WalkFastNorth 8
    EndMovement

    .balign 4, 0
_0500:
    WalkFastSouth 8
    EndMovement

_0508:
    ApplyMovement LOCALID_PLAYER, _05B8
    WaitMovement
    GetPlayerMapPos VAR_0x8000, VAR_0x8001
    AddFreeCamera VAR_0x8000, VAR_0x8001
    Call _05C0
    WaitMovement
    SetVar VAR_0x8005, 13
    SetVar VAR_0x8006, 68
    Call _0109
    MessageVar VAR_0x8004
    CloseMessage
    FadeOutBGM 0, 30
    ScrCmd_20D 0, VAR_RESULT
    WaitTime 10, VAR_RESULT
    PlayFanfare SEQ_SE_PL_KUSARI
    WaitTime 20, VAR_RESULT
    PlayMusic SEQ_THE_EVENT02
    SetSubScene63
    GoTo _0567
    End

_0567:
    ScrCmd_20D 1, VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _0567
    ScrCmd_2FB
    SetFlag FLAG_UNK_0x01C8
    SetFlag FLAG_UNK_0x01C9
    SetFlag FLAG_UNK_0x01CA
    SetVar VAR_UNK_0x4098, 3
    SetVar VAR_SPEAR_PILLAR_PARALLEL_SCENE_STATE, 3
    SetFlag FLAG_UNLOCKED_VS_SEEKER_LVL_3
    ClearFlag FLAG_UNK_0x01C7
    SetFlag FLAG_UNK_0x0132
    SetVar VAR_UNK_0x40C3, 1
    SetSpeciesSeen SPECIES_DIALGA
    SetSpeciesSeen SPECIES_PALKIA
    RestoreCamera
    Warp MAP_HEADER_SPEAR_PILLAR_DISTORTED, 0, 30, 30, 0
    End

    .balign 4, 0
_05B8:
    WalkOnSpotNormalNorth
    EndMovement

_05C0:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    SetVar VAR_0x8008, VAR_0x8004
    GoToIfEq VAR_0x8008, 29, _060F
    GoToIfEq VAR_0x8008, 30, _0619
    GoToIfEq VAR_0x8008, 31, _0623
    GoToIfEq VAR_0x8008, 32, _062D
    GoToIfEq VAR_0x8008, 33, _0637
    Return

_060F:
    ApplyFreeCameraMovement _0644
    Return

_0619:
    ApplyFreeCameraMovement _0654
    Return

_0623:
    ApplyFreeCameraMovement _0664
    Return

_062D:
    ApplyFreeCameraMovement _0670
    Return

_0637:
    ApplyFreeCameraMovement _0680
    Return

    .balign 4, 0
_0644:
    Delay8
    WalkNormalNorth 6
    WalkNormalEast 2
    EndMovement

    .balign 4, 0
_0654:
    Delay8
    WalkNormalNorth 6
    WalkNormalEast
    EndMovement

    .balign 4, 0
_0664:
    Delay8
    WalkNormalNorth 6
    EndMovement

    .balign 4, 0
_0670:
    Delay8
    WalkNormalNorth 6
    WalkNormalWest
    EndMovement

    .balign 4, 0
_0680:
    Delay8
    WalkNormalNorth 6
    WalkNormalWest 2
    EndMovement
