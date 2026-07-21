#include "macros/scrcmd.inc"
#include "res/text/bank/mt_coronet_1f_south.h"


    ScriptEntry _0006
    ScriptEntry _RivalEncounter
    ScriptEntry _RivalEncounter
    ScriptEntryEnd

_0006:
    LockAll
    ApplyMovement LOCALID_PLAYER, _008C
    ApplyMovement 6, _0064
    WaitMovement
    Message 0
    CloseMessage
    ApplyMovement 6, _0070
    ApplyMovement LOCALID_PLAYER, _009C
    WaitMovement
    Message 1
    ApplyMovement 6, _0078
    WaitMovement
    Message 2
    CloseMessage
    ApplyMovement LOCALID_PLAYER, _00B0
    ApplyMovement 6, _0080
    WaitMovement
    RemoveObject 6
    SetFlag FLAG_UNK_0x01AB
    SetVar VAR_CINDER_RIFT_CYRUS_SCENE_STATE, 1
    SetVar VAR_CINDER_RIFT_UPPER_RIVAL_SCENE_STATE, 1
    SetVar VAR_UNK_0x4096, 1
    ReleaseAll
    End

_RivalEncounter:
    LockAll
    SetRivalBGM
    BufferRivalName 0
    ApplyMovement 7, _RivalNoticesPlayer
    WaitMovement
    Message 3
    WaitABXPadPress
    CloseMessage
    Message 4
    WaitABXPadPress
    CloseMessage
    Message 5
    WaitABXPadPress
    CloseMessage
    GetPlayerStarterSpecies VAR_RESULT
    GoToIfEq VAR_RESULT, SPECIES_GIBLE, _RivalBattleGible
    GoToIfEq VAR_RESULT, SPECIES_BAGON, _RivalBattleBagon
    StartTrainerBattle TRAINER_RIVAL_ROUTE_209_DRATINI
    GoTo _RivalBattleResult
    End

_RivalBattleGible:
    StartTrainerBattle TRAINER_RIVAL_ROUTE_209_GIBLE
    GoTo _RivalBattleResult
    End

_RivalBattleBagon:
    StartTrainerBattle TRAINER_RIVAL_ROUTE_209_BAGON
    GoTo _RivalBattleResult
    End

_RivalBattleResult:
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _RivalBattleLoss
    BufferRivalName 0
    Message 6
    WaitABXPadPress
    CloseMessage
    ApplyMovement 7, _RivalLeaves
    WaitMovement
    RemoveObject 7
    SetFlag FLAG_HIDE_CINDER_RIFT_UPPER_RIVAL
    SetVar VAR_CINDER_RIFT_UPPER_RIVAL_SCENE_STATE, 2
    SetVar VAR_UNK_0x4096, 2
    ReleaseAll
    End

_RivalBattleLoss:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
_RivalNoticesPlayer:
    EmoteExclamationMark
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_RivalLeaves:
    WalkNormalNorth 2
    EndMovement

    .balign 4, 0
_0064:
    WalkNormalSouth 6
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0070:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0078:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0080:
    Delay8 3
    WalkNormalWest 10
    EndMovement

    .balign 4, 0
_008C:
    WalkOnSpotNormalNorth
    Delay8 4
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_009C:
    Delay8 3
    WalkOnSpotNormalNorth
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_00B0:
    WalkNormalSouth
    WalkOnSpotNormalNorth
    Delay8 2
    WalkOnSpotNormalWest
    EndMovement
