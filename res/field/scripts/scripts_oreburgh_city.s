#include "macros/scrcmd.inc"
#include "res/text/bank/oreburgh_city.h"
#include "res/field/events/events_oreburgh_city.h"

// Arc 1 r3 (hum), "The shard hums" side quest. Quest flags (unreferenced stock flags claimed for it):
#define FLAG_HUM_STARTED           FLAG_UNK_0x0958 // talked to the miner (object 31)
#define FLAG_HUM_CALMED            FLAG_UNK_0x0959 // his Machop calmed in the Mine side tunnel
#define FLAG_HUM_DONE              FLAG_UNK_0x095A // Machop returned, reward given
#define FLAG_HUM_HIDE_CITY_MACHOP  FLAG_UNK_0x095B // object 32: hidden until the Machop is calmed


    ScriptEntry _005A
    ScriptEntry _0090
    ScriptEntry _03F8
    ScriptEntry _00D7
    ScriptEntry _0350
    ScriptEntry _0363
    ScriptEntry _0376
    ScriptEntry _03D2
    ScriptEntry _03E5
    ScriptEntry _0634
    ScriptEntry _0647
    ScriptEntry _0670
    ScriptEntry _0683
    ScriptEntry _0696
    ScriptEntry _06A9
    ScriptEntry _06C0
    ScriptEntry _06D5
    ScriptEntry _06EC
    ScriptEntry _0703
    ScriptEntry _0722
    ScriptEntry _0735
    ScriptEntry _0754
    ScriptEntry OreburghCity_Arc1MinerDeepShaft
    ScriptEntry OreburghCity_Arc1MinerDarkCoats
    ScriptEntry OreburghCity_Arc1OnFrameTunnelGlowing
    ScriptEntry OreburghCity_OnTransition
    ScriptEntry OreburghCity_HumMiner
    ScriptEntry OreburghCity_HumMachop
    ScriptEntry OreburghCity_HumKid
    ScriptEntry OreburghCity_HumYardFaint
    ScriptEntry OreburghCity_HumYardLoud
    ScriptEntry OreburghCity_HumYardFound
    ScriptEntry OreburghCity_HumAlleyFaint
    ScriptEntry OreburghCity_HumAlleyLoud
    ScriptEntry OreburghCity_HumAlleyFound
    ScriptEntryEnd

_005A:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x008A, _0082
    BufferRivalName 0
    BufferPlayerName 1
    Message 0
    WaitABXPadPress
    SetFlag FLAG_UNK_0x008A
    CloseMessage
    ReleaseAll
    End

_0082:
    BufferRivalName 0
    Message 1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0090:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfBadgeAcquired BADGE_ID_COAL, _00C1
    GoToIfSet FLAG_UNK_0x007A, _00CC
    Message 8
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00C1:
    Message 10
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00CC:
    Message 9
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00D7:
    LockAll
    ClearFlag FLAG_UNK_0x017C
    SetObjectEventMovementType 3, MOVEMENT_TYPE_LOOK_WEST
    SetObjectEventDir 3, DIR_WEST
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 0x2EC, _011E
    GoToIfEq VAR_0x8005, 0x2ED, _0144
    GoToIfEq VAR_0x8005, 0x2EE, _016A
    GoTo _0190
    End

_011E:
    SetObjectEventPos 3, 0x10F, 0x2EC
    AddObject 3
    ApplyMovement LOCALID_PLAYER, _02A0
    ApplyMovement 3, _02B8
    WaitMovement
    GoTo _01B6
    End

_0144:
    SetObjectEventPos 3, 0x10F, 0x2ED
    AddObject 3
    ApplyMovement LOCALID_PLAYER, _02A0
    ApplyMovement 3, _02B8
    WaitMovement
    GoTo _01B6
    End

_016A:
    SetObjectEventPos 3, 0x10F, 0x2EE
    AddObject 3
    ApplyMovement LOCALID_PLAYER, _02A0
    ApplyMovement 3, _02B8
    WaitMovement
    GoTo _01B6
    End

_0190:
    SetObjectEventPos 3, 0x10F, 0x2EF
    AddObject 3
    ApplyMovement LOCALID_PLAYER, _02A0
    ApplyMovement 3, _02B8
    WaitMovement
    GoTo _01B6
    End

_01B6:
    PlayFanfare SEQ_SE_DP_WALL_HIT2
    Message 2
    CloseMessage
    SetRivalBGM
    BufferRivalName 0
    BufferPlayerName 1
    Message 3
    CloseMessage
    ApplyMovement 3, _0340
    WaitMovement
    Message 4
    ApplyMovement 3, _0348
    WaitMovement
    Message 5
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 0x2EC, _021F
    GoToIfEq VAR_0x8005, 0x2ED, _0239
    GoToIfEq VAR_0x8005, 0x2EE, _0253
    GoTo _026D
    End

_021F:
    ApplyMovement LOCALID_PLAYER, _0310
    ApplyMovement 3, _02C0
    WaitMovement
    GoTo _0287
    End

_0239:
    ApplyMovement LOCALID_PLAYER, _031C
    ApplyMovement 3, _02D0
    WaitMovement
    GoTo _0287
    End

_0253:
    ApplyMovement LOCALID_PLAYER, _0328
    ApplyMovement 3, _02E8
    WaitMovement
    GoTo _0287
    End

_026D:
    ApplyMovement LOCALID_PLAYER, _0334
    ApplyMovement 3, _02F8
    WaitMovement
    GoTo _0287
    End

_0287:
    PlayFanfare SEQ_SE_DP_KAIDAN2
    RemoveObject 3
    FadeToDefaultMusic2
    SetVar VAR_OREBURGH_STATE, 3
    ReleaseAll
    End

    .balign 4, 0
_02A0:
    Delay4 7
    LockDir
    WalkFastWest
    UnlockDir
    FaceEast
    EndMovement

    .balign 4, 0
_02B8:
    WalkFastWest 9
    EndMovement

    .balign 4, 0
_02C0:
    WalkFastSouth
    WalkFastWest 4
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
_02D0:
    WalkFastSouth
    WalkFastWest 3
    WalkFastNorth
    WalkFastWest
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
_02E8:
    WalkFastNorth
    WalkFastWest 4
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
_02F8:
    WalkFastNorth
    WalkFastWest 3
    WalkFastNorth
    WalkFastWest
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
_0310:
    WalkOnSpotNormalSouth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_031C:
    WalkOnSpotNormalSouth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0328:
    WalkOnSpotNormalNorth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0334:
    WalkOnSpotNormalNorth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0340:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0348:
    WalkOnSpotNormalWest
    EndMovement

_0350:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 14
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0363:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 16
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0376:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x0109, _03BD
    Message 17
    SetVar VAR_0x8004, ITEM_SUPER_POTION
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, _03C8
    GiveItemQuantity
    SetFlag FLAG_UNK_0x0109
    GoTo _03BD
    End

_03BD:
    Message 18
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_03C8:
    MessageBagIsFull
    CloseMessage
    ReleaseAll
    End

_03D2:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 19
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_03E5:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 20
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_03F8:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 0x2EC, _042F
    GoToIfEq VAR_0x8005, 0x2ED, _0449
    GoToIfEq VAR_0x8005, 0x2EE, _0463
    GoTo _047D
    End

_042F:
    ApplyMovement LOCALID_PLAYER, _055C
    ApplyMovement 4, _0604
    WaitMovement
    GoTo _0497
    End

_0449:
    ApplyMovement LOCALID_PLAYER, _055C
    ApplyMovement 4, _0610
    WaitMovement
    GoTo _0497
    End

_0463:
    ApplyMovement LOCALID_PLAYER, _055C
    ApplyMovement 4, _061C
    WaitMovement
    GoTo _0497
    End

_047D:
    ApplyMovement LOCALID_PLAYER, _055C
    ApplyMovement 4, _0628
    WaitMovement
    GoTo _0497
    End

_0497:
    Message 6
    CloseMessage
    SetFollowMeBGM
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 0x2EC, _04DC
    GoToIfEq VAR_0x8005, 0x2ED, _04F6
    GoToIfEq VAR_0x8005, 0x2EE, _0510
    GoToIfEq VAR_0x8005, 0x2EF, _052A
    End

_04DC:
    ApplyMovement LOCALID_PLAYER, _0564
    ApplyMovement 4, _05B4
    WaitMovement
    GoTo _0544
    End

_04F6:
    ApplyMovement LOCALID_PLAYER, _0578
    ApplyMovement 4, _05C8
    WaitMovement
    GoTo _0544
    End

_0510:
    ApplyMovement LOCALID_PLAYER, _058C
    ApplyMovement 4, _05DC
    WaitMovement
    GoTo _0544
    End

_052A:
    ApplyMovement LOCALID_PLAYER, _05A0
    ApplyMovement 4, _05F0
    WaitMovement
    GoTo _0544
    End

_0544:
    Message 7
    WaitABXPadPress
    CloseMessage
    FadeToDefaultMusic3
    SetVar VAR_OREBURGH_STATE, 1
    ReleaseAll
    End

    .balign 4, 0
_055C:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0564:
    WalkNormalSouth
    WalkNormalEast
    WalkNormalSouth 10
    WalkNormalEast 12
    EndMovement

    .balign 4, 0
_0578:
    WalkNormalSouth
    WalkNormalEast
    WalkNormalSouth 9
    WalkNormalEast 12
    EndMovement

    .balign 4, 0
_058C:
    WalkNormalSouth
    WalkNormalEast
    WalkNormalSouth 8
    WalkNormalEast 12
    EndMovement

    .balign 4, 0
_05A0:
    WalkNormalSouth
    WalkNormalEast
    WalkNormalSouth 7
    WalkNormalEast 12
    EndMovement

    .balign 4, 0
_05B4:
    WalkNormalEast
    WalkNormalSouth 10
    WalkNormalEast 13
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_05C8:
    WalkNormalEast
    WalkNormalSouth 9
    WalkNormalEast 13
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_05DC:
    WalkNormalEast
    WalkNormalSouth 8
    WalkNormalEast 13
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_05F0:
    WalkNormalEast
    WalkNormalSouth 7
    WalkNormalEast 13
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0604:
    EmoteExclamationMark
    WalkNormalNorth 3
    EndMovement

    .balign 4, 0
_0610:
    EmoteExclamationMark
    WalkNormalNorth 2
    EndMovement

    .balign 4, 0
_061C:
    EmoteExclamationMark
    WalkNormalNorth
    EndMovement

    .balign 4, 0
_0628:
    EmoteExclamationMark
    WalkOnSpotNormalNorth
    EndMovement

_0634:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 21
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0647:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x007A, _0665
    Message 11
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0665:
    Message 12
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0670:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 15
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0683:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 13
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0696:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 22
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_06A9:
    ShowMapSign 27
    End

_06C0:
    ShowScrollingSign 28
    End

_06D5:
    ShowLandmarkSign 29
    End

_06EC:
    ShowLandmarkSign 30
    End

_0703:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_MACHOP
    Message 24
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0722:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 23
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0735:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_MACHOP
    Message 25
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0754:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_MACHOP
    Message 26
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0

// Arc 1 scene 13: the two miners at the mine entrance (objects 28 and 29)
OreburghCity_Arc1MinerDeepShaft:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message OreburghCity_Text_Arc1MinerDeepShaft
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghCity_Arc1MinerDarkCoats:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message OreburghCity_Text_Arc1MinerDarkCoats
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// Arc 1 scene 14: frame script while VAR_ARC1_PROGRESS is 15 (Coal Badge won), so it runs as soon as the
// player steps out of the Gym door at (282,757), or on any later load of the city in that state.
// The ground shakes, a miner runs up from the east, and the scene cuts to Mine B2F, where
// OreburghMineB2F_Arc1OnFrameRift runs. VAR_OREBURGH_STATE 3 makes the stock post-badge rival scene
// (coord event 1, _00D7, state 2) inert.
OreburghCity_Arc1OnFrameTunnelGlowing:
    LockAll
    WaitTime 15, VAR_RESULT
    PlayFanfare SEQ_SE_DP_WALL_HIT2
    ShakeCamera 24, 4
    WaitTime 20, VAR_RESULT
    // The runner only runs up when the player is at the Gym door; arriving any other way at 15 (Pokemon Center,
    // Oreburgh Gate), his shout comes from off screen.
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8004, 282, OreburghCity_Arc1TunnelGlowingOffScreen
    GoToIfNe VAR_0x8005, 757, OreburghCity_Arc1TunnelGlowingOffScreen
    ClearFlag FLAG_HIDE_ARC1_OREBURGH_RUNNER
    SetObjectEventPos LOCALID_ARC1_RUNNER, 291, 757
    AddObject LOCALID_ARC1_RUNNER
    ApplyMovement LOCALID_ARC1_RUNNER, OreburghCity_Movement_Arc1RunnerRunWest
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_Arc1PlayerNoticeRunner
    WaitMovement
    Message OreburghCity_Text_Arc1MinerTunnelGlowing
    WaitABXPadPress
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_ARC1_RUNNER
    GoTo OreburghCity_Arc1TunnelGlowingWarp
    End

OreburghCity_Arc1TunnelGlowingOffScreen:
    Message OreburghCity_Text_Arc1MinerTunnelGlowing
    WaitABXPadPress
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
OreburghCity_Arc1TunnelGlowingWarp:
    SetVar VAR_OREBURGH_STATE, 3
    Warp MAP_HEADER_OREBURGH_MINE_B2F, 0, 12, 17, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
OreburghCity_Movement_Arc1RunnerRunWest:
    WalkFastWest 8
    EndMovement

    .balign 4, 0
OreburghCity_Movement_Arc1PlayerNoticeRunner:
    Delay8 2
    FaceEast
    EndMovement

// Arc 1: the runner miner (object 30) only exists during the scene 14 frame script, which clears this flag and
// adds him itself. Keep him hidden on every load (his hide flag starts clear in every save).
OreburghCity_OnTransition:
    SetFlag FLAG_HIDE_ARC1_OREBURGH_RUNNER
    // Arc 1 r3 (hum): the miner's Machop is home once it's calmed; the reader's buzz coords are live while
    // it's missing (VAR_MAP_LOCAL_0: coal-tower yard, VAR_MAP_LOCAL_1: back street; 1 armed, 2 faint,
    // 3 loud, 4 found)
    SetFlag FLAG_HUM_HIDE_CITY_MACHOP
    CallIfSet FLAG_HUM_CALMED, OreburghCity_HumShowMachop
    SetVar VAR_MAP_LOCAL_0, 0
    SetVar VAR_MAP_LOCAL_1, 0
    CallIfSet FLAG_HUM_STARTED, OreburghCity_HumArmBuzz
    End

OreburghCity_HumShowMachop:
    ClearFlag FLAG_HUM_HIDE_CITY_MACHOP
    Return

OreburghCity_HumArmBuzz:
    CallIfUnset FLAG_HUM_CALMED, OreburghCity_HumSetBuzz1
    Return

OreburghCity_HumSetBuzz1:
    SetVar VAR_MAP_LOCAL_0, 1
    SetVar VAR_MAP_LOCAL_1, 1
    Return

// Arc 1 r3 (hum): the miner by the road down to the mine (object 31). Open from VAR_ARC1_PROGRESS 14 on (the
// player can't reach Oreburgh earlier) and never touches it, so Gym 1 and the mine rift scene are unaffected.
OreburghCity_HumMiner:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_HUM_DONE, OreburghCity_HumMinerAfter
    GoToIfSet FLAG_HUM_CALMED, OreburghCity_HumMinerReunion
    GoToIfSet FLAG_HUM_STARTED, OreburghCity_HumMinerWaiting
    Message OreburghCity_Text_HumMinerMissing
    WaitABXPadPress
    CloseMessage
    SetFlag FLAG_HUM_STARTED
    SetVar VAR_MAP_LOCAL_0, 1
    SetVar VAR_MAP_LOCAL_1, 1
    WaitTime 10, VAR_RESULT
    PlayFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    WaitFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    Message OreburghCity_Text_HumReaderFirstBuzz
    WaitABXPadPress
    Message OreburghCity_Text_HumMinerWhatsThatRacket
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghCity_HumMinerWaiting:
    Message OreburghCity_Text_HumMinerWaiting
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghCity_HumMinerReunion:
    CallIfUnset FLAG_HUM_STARTED, OreburghCity_HumMinerDidntAsk
    ApplyMovement LOCALID_HUM_MINER, OreburghCity_Movement_HumFaceSouth
    WaitMovement
    Message OreburghCity_Text_HumMinerBigLug
    WaitABXPadPress
    CloseMessage
    PlayCry SPECIES_MACHOP
    ApplyMovement LOCALID_HUM_MACHOP, OreburghCity_Movement_HumMachopHop
    WaitMovement
    WaitCry
    Message OreburghCity_Text_HumMinerMarkOnHisArm
    WaitABXPadPress
    CloseMessage
    FacePlayer
    Message OreburghCity_Text_HumMinerTwoDays
    WaitABXPadPress
    Message OreburghCity_Text_HumMinerAWeek
    WaitABXPadPress
    GoToIfCannotFitItem ITEM_BLACK_BELT, 1, VAR_RESULT, OreburghCity_HumMinerBagFull
    Message OreburghCity_Text_HumMinerTakeThis
    SetVar VAR_0x8004, ITEM_BLACK_BELT
    SetVar VAR_0x8005, 1
    GiveItemQuantity
    CloseMessage
    SetFlag FLAG_HUM_DONE
    ReleaseAll
    End

OreburghCity_HumMinerDidntAsk:
    Message OreburghCity_Text_HumMinerDidntAsk
    WaitABXPadPress
    Return

OreburghCity_HumMinerBagFull:
    Message OreburghCity_Text_HumMinerBagFull
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghCity_HumMinerAfter:
    Message OreburghCity_Text_HumMinerAfter
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// Object 32: the miner's Machop, home once it's calmed
OreburghCity_HumMachop:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_MACHOP
    Message OreburghCity_Text_HumMachop
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// Object 33: the kid in the back street (the west alley)
OreburghCity_HumKid:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_HUM_CALMED, OreburghCity_HumKidAfter
    GoToIfSet FLAG_HUM_STARTED, OreburghCity_HumKidSawMachop
    Message OreburghCity_Text_HumKidHideout
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghCity_HumKidSawMachop:
    Message OreburghCity_Text_HumKidSawMachop
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghCity_HumKidAfter:
    Message OreburghCity_Text_HumKidAfter
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// Spot 1: the coal-tower yard east of the road down to the mine
OreburghCity_HumYardFaint:
    LockAll
    SetVar VAR_MAP_LOCAL_0, 2
    Call OreburghCity_HumBeep1
    Message OreburghCity_Text_HumBuzzFaint
    GoTo OreburghCity_HumBuzzEnd

OreburghCity_HumYardLoud:
    LockAll
    SetVar VAR_MAP_LOCAL_0, 3
    Call OreburghCity_HumBeep2
    Message OreburghCity_Text_HumBuzzLoud
    GoTo OreburghCity_HumBuzzEnd

OreburghCity_HumYardFound:
    LockAll
    SetVar VAR_MAP_LOCAL_0, 4
    Call OreburghCity_HumBeep3
    Message OreburghCity_Text_HumBuzzWild
    WaitABXPadPress
    Message OreburghCity_Text_HumYardFlecks
    GoTo OreburghCity_HumBuzzEnd

// Spot 2: the back street (the west alley behind the houses)
OreburghCity_HumAlleyFaint:
    LockAll
    SetVar VAR_MAP_LOCAL_1, 2
    Call OreburghCity_HumBeep1
    Message OreburghCity_Text_HumBuzzFaint
    GoTo OreburghCity_HumBuzzEnd

OreburghCity_HumAlleyLoud:
    LockAll
    SetVar VAR_MAP_LOCAL_1, 3
    Call OreburghCity_HumBeep2
    Message OreburghCity_Text_HumBuzzLoud
    GoTo OreburghCity_HumBuzzEnd

OreburghCity_HumAlleyFound:
    LockAll
    SetVar VAR_MAP_LOCAL_1, 4
    Call OreburghCity_HumBeep3
    Message OreburghCity_Text_HumBuzzWild
    WaitABXPadPress
    Message OreburghCity_Text_HumAlleyFlecks
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_HUM_KID, OreburghCity_Movement_HumExclamation
    WaitMovement
    Message OreburghCity_Text_HumKidSawMachop
    GoTo OreburghCity_HumBuzzEnd

OreburghCity_HumBuzzEnd:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghCity_HumBeep1:
    PlayFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    WaitFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    Return

OreburghCity_HumBeep2:
    PlayFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    WaitFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    PlayFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    WaitFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    Return

OreburghCity_HumBeep3:
    PlayFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    WaitFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    PlayFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    WaitFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    PlayFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    WaitFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    Return

    .balign 4, 0
OreburghCity_Movement_HumFaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
OreburghCity_Movement_HumMachopHop:
    JumpOnSpotFastNorth
    JumpOnSpotFastNorth
    EndMovement

    .balign 4, 0
OreburghCity_Movement_HumExclamation:
    EmoteExclamationMark
    EndMovement
