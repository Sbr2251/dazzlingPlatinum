#include "macros/scrcmd.inc"
#include "res/text/bank/oreburgh_city.h"
#include "res/field/maps/locals/oreburgh_city.h"

#define FLAG_HUM_STARTED           FLAG_UNK_0x0958 // talked to the miner (object 31)
#define FLAG_HUM_CALMED            FLAG_UNK_0x0959 // his Machop calmed in the Mine side tunnel
#define FLAG_HUM_DONE              FLAG_UNK_0x095A // Machop returned, reward given
#define FLAG_HUM_HIDE_CITY_MACHOP  FLAG_UNK_0x095B // object 32: hidden until the Machop is calmed

    ScriptEntry OreburghCity_Rival
    ScriptEntry OreburghCity_Youngster
    ScriptEntry OreburghCity_CoordEvent_Youngster
    ScriptEntry OreburghCity_CoordEvent_Rival
    ScriptEntry OreburghCity_Hiker
    ScriptEntry OreburghCity_Worker1
    ScriptEntry OreburghCity_Worker2
    ScriptEntry OreburghCity_Worker3
    ScriptEntry OreburghCity_Worker4
    ScriptEntry OreburghCity_BattleGirl1
    ScriptEntry OreburghCity_SchoolKidF
    ScriptEntry OreburghCity_Guitarist
    ScriptEntry OreburghCity_PokefanF
    ScriptEntry OreburghCity_Camper
    ScriptEntry OreburghCity_MapSignpost
    ScriptEntry OreburghCity_GymSignpost
    ScriptEntry OreburghCity_SignboardOreburghMiningMuseum
    ScriptEntry OreburghCity_SignboardOreburghMine
    ScriptEntry OreburghCity_Machop1
    ScriptEntry OreburghCity_BattleGirl2
    ScriptEntry OreburghCity_Machop3
    ScriptEntry OreburghCity_Machop2
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
    ScriptEntry OreburghCity_CineCityEntry
    ScriptEntryEnd

OreburghCity_Rival:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_TALKED_TO_OREBURGH_CITY_RIVAL, OreburghCity_GymLeaderWentDownToTheMine
    BufferRivalName 0
    BufferPlayerName 1
    Message OreburghCity_Text_GymLeadersGoneOffToTheMine
    WaitButton
    SetFlag FLAG_TALKED_TO_OREBURGH_CITY_RIVAL
    CloseMessage
    ReleaseAll
    End

OreburghCity_GymLeaderWentDownToTheMine:
    BufferRivalName 0
    Message OreburghCity_Text_GymLeaderWentDownToTheMine
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_Youngster:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfBadgeAcquired BADGE_ID_COAL, OreburghCity_CanISeeYourTrainerCase
    GoToIfSet FLAG_ROARK_RETURNED_TO_OREBURGH_GYM, OreburghCity_TheGymLeadersWaitingForYou
    Message OreburghCity_Text_IsThatGuyYourFriend
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_CanISeeYourTrainerCase:
    Message OreburghCity_Text_CanISeeYourTrainerCase
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_TheGymLeadersWaitingForYou:
    Message OreburghCity_Text_TheGymLeadersWaitingForYou
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_CoordEvent_Rival:
    LockAll
    ClearFlag FLAG_HIDE_OREBURGH_CITY_RIVAL
    SetObjectEventMovementType LOCALID_RIVAL, MOVEMENT_TYPE_LOOK_WEST
    SetObjectEventDir LOCALID_RIVAL, DIR_WEST
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 748, OreburghCity_RivalRunIntoPlayerZ748
    GoToIfEq VAR_0x8005, 749, OreburghCity_RivalRunIntoPlayerZ749
    GoToIfEq VAR_0x8005, 750, OreburghCity_RivalRunIntoPlayerZ750
    GoTo OreburghCity_RivalRunIntoPlayerZ751
    End

OreburghCity_RivalRunIntoPlayerZ748:
    SetObjectEventPos LOCALID_RIVAL, 271, 748
    AddObject LOCALID_RIVAL
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerGetPushedByRival
    ApplyMovement LOCALID_RIVAL, OreburghCity_Movement_RivalRunIntoPlayer
    WaitMovement
    GoTo OreburghCity_NextStopTheEternaGymBadge
    End

OreburghCity_RivalRunIntoPlayerZ749:
    SetObjectEventPos LOCALID_RIVAL, 271, 749
    AddObject LOCALID_RIVAL
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerGetPushedByRival
    ApplyMovement LOCALID_RIVAL, OreburghCity_Movement_RivalRunIntoPlayer
    WaitMovement
    GoTo OreburghCity_NextStopTheEternaGymBadge
    End

OreburghCity_RivalRunIntoPlayerZ750:
    SetObjectEventPos LOCALID_RIVAL, 271, 750
    AddObject LOCALID_RIVAL
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerGetPushedByRival
    ApplyMovement LOCALID_RIVAL, OreburghCity_Movement_RivalRunIntoPlayer
    WaitMovement
    GoTo OreburghCity_NextStopTheEternaGymBadge
    End

OreburghCity_RivalRunIntoPlayerZ751:
    SetObjectEventPos LOCALID_RIVAL, 271, 751
    AddObject LOCALID_RIVAL
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerGetPushedByRival
    ApplyMovement LOCALID_RIVAL, OreburghCity_Movement_RivalRunIntoPlayer
    WaitMovement
    GoTo OreburghCity_NextStopTheEternaGymBadge
    End

OreburghCity_NextStopTheEternaGymBadge:
    PlaySE SEQ_SE_DP_WALL_HIT2_sseq
    Message OreburghCity_Text_BigThud
    CloseMessage
    CallCommonScript CommonScript_SetRivalBGM
    BufferRivalName 0
    BufferPlayerName 1
    Message OreburghCity_Text_EternaCityNextPlaceWithAGym
    CloseMessage
    ApplyMovement LOCALID_RIVAL, OreburghCity_Movement_RivalWalkOnSpotEast
    WaitMovement
    Message OreburghCity_Text_CantGoToRoute207WithoutBicycle
    ApplyMovement LOCALID_RIVAL, OreburghCity_Movement_RivalWalkOnSpotWest
    WaitMovement
    Message OreburghCity_Text_NextStopTheEternaGymBadge
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 748, OreburghCity_RivalLeaveZ748
    GoToIfEq VAR_0x8005, 749, OreburghCity_RivalLeaveZ749
    GoToIfEq VAR_0x8005, 750, OreburghCity_RivalLeaveZ750
    GoTo OreburghCity_RivalLeaveZ751
    End

OreburghCity_RivalLeaveZ748:
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerWatchRivalLeaveZ748
    ApplyMovement LOCALID_RIVAL, OreburghCity_Movement_RivalLeaveZ748
    WaitMovement
    GoTo OreburghCity_RemoveRival
    End

OreburghCity_RivalLeaveZ749:
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerWatchRivalLeaveZ749
    ApplyMovement LOCALID_RIVAL, OreburghCity_Movement_RivalLeaveZ749
    WaitMovement
    GoTo OreburghCity_RemoveRival
    End

OreburghCity_RivalLeaveZ750:
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerWatchRivalLeaveZ750
    ApplyMovement LOCALID_RIVAL, OreburghCity_Movement_RivalLeaveZ750
    WaitMovement
    GoTo OreburghCity_RemoveRival
    End

OreburghCity_RivalLeaveZ751:
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerWatchRivalLeaveZ751
    ApplyMovement LOCALID_RIVAL, OreburghCity_Movement_RivalLeaveZ751
    WaitMovement
    GoTo OreburghCity_RemoveRival
    End

OreburghCity_RemoveRival:
    PlaySE SEQ_SE_DP_KAIDAN2_sseq
    RemoveObject LOCALID_RIVAL
    CallCommonScript CommonScript_FadeToDefaultMusic_2
    SetVar VAR_OREBURGH_CITY_STATE, 3
    ReleaseAll
    End

    .balign 4, 0
OreburghCity_Movement_PlayerGetPushedByRival:
    Delay4 7
    LockDir
    WalkFastWest
    UnlockDir
    FaceEast
    EndMovement

    .balign 4, 0
OreburghCity_Movement_RivalRunIntoPlayer:
    WalkFastWest 9
    EndMovement

    .balign 4, 0
OreburghCity_Movement_RivalLeaveZ748:
    WalkFastSouth
    WalkFastWest 4
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
OreburghCity_Movement_RivalLeaveZ749:
    WalkFastSouth
    WalkFastWest 3
    WalkFastNorth
    WalkFastWest
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
OreburghCity_Movement_RivalLeaveZ750:
    WalkFastNorth
    WalkFastWest 4
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
OreburghCity_Movement_RivalLeaveZ751:
    WalkFastNorth
    WalkFastWest 3
    WalkFastNorth
    WalkFastWest
    WalkOnSpotFastWest
    EndMovement

    .balign 4, 0
OreburghCity_Movement_PlayerWatchRivalLeaveZ748:
    WalkOnSpotNormalSouth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
OreburghCity_Movement_PlayerWatchRivalLeaveZ749:
    WalkOnSpotNormalSouth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
OreburghCity_Movement_PlayerWatchRivalLeaveZ750:
    WalkOnSpotNormalNorth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
OreburghCity_Movement_PlayerWatchRivalLeaveZ751:
    WalkOnSpotNormalNorth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
OreburghCity_Movement_RivalWalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
OreburghCity_Movement_RivalWalkOnSpotWest:
    WalkOnSpotNormalWest
    EndMovement

OreburghCity_Hiker:
    NPCMessage OreburghCity_Text_UpAheadTheresAHugeMountain
    End

OreburghCity_Worker1:
    NPCMessage OreburghCity_Text_TheseVentsExchangeAirDownBelow
    End

OreburghCity_Worker2:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_RECEIVED_OREBURGH_CITY_SUPER_POTION, OreburghCity_PutsASmileOnMyFace
    Message OreburghCity_Text_HereTakeOneOfThese
    SetVar VAR_0x8004, ITEM_SUPER_POTION
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, OreburghCity_BagIsFull
    CallCommonScript CommonScript_AddItemQuantity
    SetFlag FLAG_RECEIVED_OREBURGH_CITY_SUPER_POTION
    GoTo OreburghCity_PutsASmileOnMyFace
    End

OreburghCity_PutsASmileOnMyFace:
    Message OreburghCity_Text_PutsASmileOnMyFace
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_BagIsFull:
    CallCommonScript CommonScript_BagIsFull
    CloseMessage
    ReleaseAll
    End

OreburghCity_Worker3:
    NPCMessage OreburghCity_Text_ThisPileIsCalledASlagHeap
    End

OreburghCity_Worker4:
    NPCMessage OreburghCity_Text_ChopChopAwayOnRocks
    End

OreburghCity_CoordEvent_Youngster:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 748, OreburghCity_YoungsterWalkToPlayerZ748
    GoToIfEq VAR_0x8005, 749, OreburghCity_YoungsterWalkToPlayerZ749
    GoToIfEq VAR_0x8005, 750, OreburghCity_YoungsterWalkToPlayerZ750
    GoTo OreburghCity_YoungsterWalkToPlayerZ751
    End

OreburghCity_YoungsterWalkToPlayerZ748:
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerWalkOnSpotSouth
    ApplyMovement LOCALID_YOUNGSTER, OreburghCity_Movement_YoungsterWalkToPlayerZ748
    WaitMovement
    GoTo OreburghCity_IllTakeYouToTheGym
    End

OreburghCity_YoungsterWalkToPlayerZ749:
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerWalkOnSpotSouth
    ApplyMovement LOCALID_YOUNGSTER, OreburghCity_Movement_YoungsterWalkToPlayerZ749
    WaitMovement
    GoTo OreburghCity_IllTakeYouToTheGym
    End

OreburghCity_YoungsterWalkToPlayerZ750:
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerWalkOnSpotSouth
    ApplyMovement LOCALID_YOUNGSTER, OreburghCity_Movement_YoungsterWalkToPlayerZ750
    WaitMovement
    GoTo OreburghCity_IllTakeYouToTheGym
    End

OreburghCity_YoungsterWalkToPlayerZ751:
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerWalkOnSpotSouth
    ApplyMovement LOCALID_YOUNGSTER, OreburghCity_Movement_YoungsterWalkToPlayerZ751
    WaitMovement
    GoTo OreburghCity_IllTakeYouToTheGym
    End

OreburghCity_IllTakeYouToTheGym:
    Message OreburghCity_Text_IllTakeYouToTheGym
    CloseMessage
    CallCommonScript CommonScript_SetFollowMeBGM
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 748, OreburghCity_WalkWithYoungsterToTheGymZ748
    GoToIfEq VAR_0x8005, 749, OreburghCity_WalkWithYoungsterToTheGymZ749
    GoToIfEq VAR_0x8005, 750, OreburghCity_WalkWithYoungsterToTheGymZ750
    GoToIfEq VAR_0x8005, 751, OreburghCity_WalkWithYoungsterToTheGymZ751
    End

OreburghCity_WalkWithYoungsterToTheGymZ748:
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerWalkToTheGymZ748
    ApplyMovement LOCALID_YOUNGSTER, OreburghCity_Movement_YoungsterWalkToTheGymZ748
    WaitMovement
    GoTo OreburghCity_HuhTheresSomeoneThere
    End

OreburghCity_WalkWithYoungsterToTheGymZ749:
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerWalkToTheGymZ749
    ApplyMovement LOCALID_YOUNGSTER, OreburghCity_Movement_YoungsterWalkToTheGymZ749
    WaitMovement
    GoTo OreburghCity_HuhTheresSomeoneThere
    End

OreburghCity_WalkWithYoungsterToTheGymZ750:
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerWalkToTheGymZ750
    ApplyMovement LOCALID_YOUNGSTER, OreburghCity_Movement_YoungsterWalkToTheGymZ750
    WaitMovement
    GoTo OreburghCity_HuhTheresSomeoneThere
    End

OreburghCity_WalkWithYoungsterToTheGymZ751:
    ApplyMovement LOCALID_PLAYER, OreburghCity_Movement_PlayerWalkToTheGymZ751
    ApplyMovement LOCALID_YOUNGSTER, OreburghCity_Movement_YoungsterWalkToTheGymZ751
    WaitMovement
    GoTo OreburghCity_HuhTheresSomeoneThere
    End

OreburghCity_HuhTheresSomeoneThere:
    Message OreburghCity_Text_HuhTheresSomeoneThere
    WaitButton
    CloseMessage
    CallCommonScript CommonScript_FadeToDefaultMusic_3
    SetVar VAR_OREBURGH_CITY_STATE, 1
    ReleaseAll
    End

    .balign 4, 0
OreburghCity_Movement_PlayerWalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
OreburghCity_Movement_PlayerWalkToTheGymZ748:
    WalkNormalSouth
    WalkNormalEast
    WalkNormalSouth 10
    WalkNormalEast 12
    EndMovement

    .balign 4, 0
OreburghCity_Movement_PlayerWalkToTheGymZ749:
    WalkNormalSouth
    WalkNormalEast
    WalkNormalSouth 9
    WalkNormalEast 12
    EndMovement

    .balign 4, 0
OreburghCity_Movement_PlayerWalkToTheGymZ750:
    WalkNormalSouth
    WalkNormalEast
    WalkNormalSouth 8
    WalkNormalEast 12
    EndMovement

    .balign 4, 0
OreburghCity_Movement_PlayerWalkToTheGymZ751:
    WalkNormalSouth
    WalkNormalEast
    WalkNormalSouth 7
    WalkNormalEast 12
    EndMovement

    .balign 4, 0
OreburghCity_Movement_YoungsterWalkToTheGymZ748:
    WalkNormalEast
    WalkNormalSouth 10
    WalkNormalEast 13
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
OreburghCity_Movement_YoungsterWalkToTheGymZ749:
    WalkNormalEast
    WalkNormalSouth 9
    WalkNormalEast 13
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
OreburghCity_Movement_YoungsterWalkToTheGymZ750:
    WalkNormalEast
    WalkNormalSouth 8
    WalkNormalEast 13
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
OreburghCity_Movement_YoungsterWalkToTheGymZ751:
    WalkNormalEast
    WalkNormalSouth 7
    WalkNormalEast 13
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
OreburghCity_Movement_YoungsterWalkToPlayerZ748:
    EmoteExclamationMark
    WalkNormalNorth 3
    EndMovement

    .balign 4, 0
OreburghCity_Movement_YoungsterWalkToPlayerZ749:
    EmoteExclamationMark
    WalkNormalNorth 2
    EndMovement

    .balign 4, 0
OreburghCity_Movement_YoungsterWalkToPlayerZ750:
    EmoteExclamationMark
    WalkNormalNorth
    EndMovement

    .balign 4, 0
OreburghCity_Movement_YoungsterWalkToPlayerZ751:
    EmoteExclamationMark
    WalkOnSpotNormalNorth
    EndMovement

OreburghCity_BattleGirl1:
    NPCMessage OreburghCity_Text_TMsSingleUseHMsOverAndOver
    End

OreburghCity_SchoolKidF:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_ROARK_RETURNED_TO_OREBURGH_GYM, OreburghCity_GymLeaderIsSafetySupervisor
    Message OreburghCity_Text_GymLeaderWentOffToWork
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_GymLeaderIsSafetySupervisor:
    Message OreburghCity_Text_GymLeaderIsSafetySupervisor
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_Guitarist:
    NPCMessage OreburghCity_Text_HaveYouSeenTheVents
    End

OreburghCity_PokefanF:
    NPCMessage OreburghCity_Text_EveryonesProudOfTheMine
    End

OreburghCity_Camper:
    NPCMessage OreburghCity_Text_ImTheCenterOfAttention
    End

OreburghCity_MapSignpost:
    ShowMapSign OreburghCity_Text_MapSign
    End

OreburghCity_GymSignpost:
    ShowScrollingSign OreburghCity_Text_SignPokemonGym
    End

OreburghCity_SignboardOreburghMiningMuseum:
    ShowLandmarkSign OreburghCity_Text_SignOreburghMiningMuseum
    End

OreburghCity_SignboardOreburghMine:
    ShowLandmarkSign OreburghCity_Text_SignOreburghMine
    End

OreburghCity_Machop1:
    PokemonCryAndMessage SPECIES_MACHOP, OreburghCity_Text_MachopCryMachoChopo
    End

OreburghCity_BattleGirl2:
    NPCMessage OreburghCity_Text_ThatsWhatFossilsAre
    End

OreburghCity_Machop3:
    PokemonCryAndMessage SPECIES_MACHOP, OreburghCity_Text_MachopCryPigyooh
    End

OreburghCity_Machop2:
    PokemonCryAndMessage SPECIES_MACHOP, OreburghCity_Text_MachopCryGwoohGogogooh
    End

    .balign 4, 0

OreburghCity_Arc1MinerDeepShaft:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message OreburghCity_Text_Arc1MinerDeepShaft
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_Arc1MinerDarkCoats:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message OreburghCity_Text_Arc1MinerDarkCoats
    WaitButton
    CloseMessage
    ReleaseAll
    End

// Arc 1 scene 14: frame script while VAR_ARC1_PROGRESS is 15 (Coal Badge won), so it runs as soon as the
// player steps out of the Gym door at (282,757), or on any later load of the city in that state.
// The ground shakes, a miner runs up from the east, and the scene cuts to Mine B2F, where
// OreburghMineB2F_Arc1OnFrameRift runs. VAR_OREBURGH_CITY_STATE 3 makes the stock post-badge rival scene
// (coord event 1, OreburghCity_CoordEvent_Rival, state 2) inert.
OreburghCity_Arc1OnFrameTunnelGlowing:
    LockAll
    WaitTime 15, VAR_RESULT
    PlayFanfare SEQ_SE_DP_WALL_HIT2_sseq
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
    WaitButton
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_ARC1_RUNNER
    GoTo OreburghCity_Arc1TunnelGlowingWarp
    End

OreburghCity_Arc1TunnelGlowingOffScreen:
    Message OreburghCity_Text_Arc1MinerTunnelGlowing
    WaitButton
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
OreburghCity_Arc1TunnelGlowingWarp:
    SetVar VAR_OREBURGH_CITY_STATE, 3
    Warp MAP_HEADER_OREBURGH_MINE_B2F, 12, 17, DIR_WEST
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
    SetVar VAR_CINE_CITY_PENDING, 1
    SetFlag FLAG_HIDE_ARC1_OREBURGH_RUNNER
    // Arc 1 r3 (hum): the miner's Machop is home once it's calmed; the reader's buzz coords are live while
    // it's missing (VAR_MAP_LOCAL_0x00: coal-tower yard, VAR_MAP_LOCAL_0x01: back street; 1 armed, 2 faint,
    // 3 loud, 4 found)
    SetFlag FLAG_HUM_HIDE_CITY_MACHOP
    CallIfSet FLAG_HUM_CALMED, OreburghCity_HumShowMachop
    SetVar VAR_MAP_LOCAL_0x00, 0
    SetVar VAR_MAP_LOCAL_0x01, 0
    CallIfSet FLAG_HUM_STARTED, OreburghCity_HumArmBuzz
    // fix2: Garius (local 3, stock FLAG_HIDE_OREBURGH_CITY_RIVAL) waits at the Gym door only until the player meets Roark in
    // Mine B2F. Once the Coal Badge is won he is gone for good, even if the save never played the mine meeting
    // (the owner's A1-07 save). The badge check goes into a map-local var: VAR_RESULT in OnTransition hangs.
    CheckBadgeAcquired BADGE_ID_COAL, VAR_MAP_LOCAL_0x02
    CallIfEq VAR_MAP_LOCAL_0x02, TRUE, OreburghCity_HideGymDoorRival
    CallIfGe VAR_ARC1_PROGRESS, 15, OreburghCity_HideGymDoorRival
    End

OreburghCity_HideGymDoorRival:
    SetFlag FLAG_HIDE_OREBURGH_CITY_RIVAL
    Return

OreburghCity_HumShowMachop:
    ClearFlag FLAG_HUM_HIDE_CITY_MACHOP
    Return

OreburghCity_HumArmBuzz:
    CallIfUnset FLAG_HUM_CALMED, OreburghCity_HumSetBuzz1
    Return

OreburghCity_HumSetBuzz1:
    SetVar VAR_MAP_LOCAL_0x00, 1
    SetVar VAR_MAP_LOCAL_0x01, 1
    Return

// Arc 1 r3 (hum): the miner by the road down to the mine (object 31). Open from VAR_ARC1_PROGRESS 14 on (the
// player can't reach Oreburgh earlier) and never touches it, so Gym 1 and the mine rift scene are unaffected.
OreburghCity_HumMiner:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_HUM_DONE, OreburghCity_HumMinerAfter
    GoToIfSet FLAG_HUM_CALMED, OreburghCity_HumMinerReunion
    GoToIfSet FLAG_HUM_STARTED, OreburghCity_HumMinerWaiting
    Message OreburghCity_Text_HumMinerMissing
    WaitButton
    CloseMessage
    SetFlag FLAG_HUM_STARTED
    SetVar VAR_MAP_LOCAL_0x00, 1
    SetVar VAR_MAP_LOCAL_0x01, 1
    WaitTime 10, VAR_RESULT
    PlayFanfare SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    Message OreburghCity_Text_HumReaderFirstBuzz
    WaitButton
    Message OreburghCity_Text_HumMinerWhatsThatRacket
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_HumMinerWaiting:
    Message OreburghCity_Text_HumMinerWaiting
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_HumMinerReunion:
    CallIfUnset FLAG_HUM_STARTED, OreburghCity_HumMinerDidntAsk
    ApplyMovement LOCALID_HUM_MINER, OreburghCity_Movement_HumFaceSouth
    WaitMovement
    Message OreburghCity_Text_HumMinerBigLug
    WaitButton
    CloseMessage
    PlayCry SPECIES_MACHOP
    ApplyMovement LOCALID_HUM_MACHOP, OreburghCity_Movement_HumMachopHop
    WaitMovement
    WaitCry
    Message OreburghCity_Text_HumMinerMarkOnHisArm
    WaitButton
    CloseMessage
    FacePlayer
    Message OreburghCity_Text_HumMinerTwoDays
    WaitButton
    Message OreburghCity_Text_HumMinerAWeek
    WaitButton
    GoToIfCannotFitItem ITEM_BLACK_BELT, 1, VAR_RESULT, OreburghCity_HumMinerBagFull
    Message OreburghCity_Text_HumMinerTakeThis
    SetVar VAR_0x8004, ITEM_BLACK_BELT
    SetVar VAR_0x8005, 1
    CallCommonScript CommonScript_AddItemQuantity
    CloseMessage
    SetFlag FLAG_HUM_DONE
    ReleaseAll
    End

OreburghCity_HumMinerDidntAsk:
    Message OreburghCity_Text_HumMinerDidntAsk
    WaitButton
    Return

OreburghCity_HumMinerBagFull:
    Message OreburghCity_Text_HumMinerBagFull
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_HumMinerAfter:
    Message OreburghCity_Text_HumMinerAfter
    WaitButton
    CloseMessage
    ReleaseAll
    End

// Object 32: the miner's Machop, home once it's calmed
OreburghCity_HumMachop:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    WaitSE SE_CONFIRM_sseq_3
    PlayCry SPECIES_MACHOP
    Message OreburghCity_Text_HumMachop
    WaitCry
    WaitButton
    CloseMessage
    ReleaseAll
    End

// Object 33: the kid in the back street (the west alley)
OreburghCity_HumKid:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_HUM_CALMED, OreburghCity_HumKidAfter
    GoToIfSet FLAG_HUM_STARTED, OreburghCity_HumKidSawMachop
    Message OreburghCity_Text_HumKidHideout
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_HumKidSawMachop:
    Message OreburghCity_Text_HumKidSawMachop
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_HumKidAfter:
    Message OreburghCity_Text_HumKidAfter
    WaitButton
    CloseMessage
    ReleaseAll
    End

// Spot 1: the coal-tower yard east of the road down to the mine
OreburghCity_HumYardFaint:
    LockAll
    SetVar VAR_MAP_LOCAL_0x00, 2
    Call OreburghCity_HumBeep1
    Message OreburghCity_Text_HumBuzzFaint
    GoTo OreburghCity_HumBuzzEnd

OreburghCity_HumYardLoud:
    LockAll
    SetVar VAR_MAP_LOCAL_0x00, 3
    Call OreburghCity_HumBeep2
    Message OreburghCity_Text_HumBuzzLoud
    GoTo OreburghCity_HumBuzzEnd

OreburghCity_HumYardFound:
    LockAll
    SetVar VAR_MAP_LOCAL_0x00, 4
    Call OreburghCity_HumBeep3
    Message OreburghCity_Text_HumBuzzWild
    WaitButton
    Message OreburghCity_Text_HumYardFlecks
    GoTo OreburghCity_HumBuzzEnd

// Spot 2: the back street (the west alley behind the houses)
OreburghCity_HumAlleyFaint:
    LockAll
    SetVar VAR_MAP_LOCAL_0x01, 2
    Call OreburghCity_HumBeep1
    Message OreburghCity_Text_HumBuzzFaint
    GoTo OreburghCity_HumBuzzEnd

OreburghCity_HumAlleyLoud:
    LockAll
    SetVar VAR_MAP_LOCAL_0x01, 3
    Call OreburghCity_HumBeep2
    Message OreburghCity_Text_HumBuzzLoud
    GoTo OreburghCity_HumBuzzEnd

OreburghCity_HumAlleyFound:
    LockAll
    SetVar VAR_MAP_LOCAL_0x01, 4
    Call OreburghCity_HumBeep3
    Message OreburghCity_Text_HumBuzzWild
    WaitButton
    Message OreburghCity_Text_HumAlleyFlecks
    WaitButton
    CloseMessage
    ApplyMovement LOCALID_HUM_KID, OreburghCity_Movement_HumExclamation
    WaitMovement
    Message OreburghCity_Text_HumKidSawMachop
    GoTo OreburghCity_HumBuzzEnd

OreburghCity_HumBuzzEnd:
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghCity_HumBeep1:
    PlayFanfare SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    Return

OreburghCity_HumBeep2:
    PlayFanfare SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    PlayFanfare SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    Return

OreburghCity_HumBeep3:
    PlayFanfare SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    PlayFanfare SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    PlayFanfare SEQ_SE_DP_BEEP_sseq
    WaitFanfare
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

// City-entry cinematic (lane cine): on the first entry per save, a short
// pull-back and slow return while player input waits (LockAll). No-ops
// when OverworldCinematics is off.
OreburghCity_CineCityEntry:
    SetVar VAR_CINE_CITY_PENDING, 0
    GoToIfSet FLAG_CINE_VISITED_OREBURGH, OreburghCity_CineCityEntryDone
    SetFlag FLAG_CINE_VISITED_OREBURGH
    LockAll
    CineCamTo 0, 0, 700, 53, 0, 11, 80, 1
    CineWaitCamera
    CineCamReturn 70, 1
    CineWaitCamera
    ReleaseAll
OreburghCity_CineCityEntryDone:
    End
