#include "macros/scrcmd.inc"
#include "res/text/bank/route_209.h"
#include "res/field/maps/locals/route_209.h"


    ScriptEntry Route209_PokefanM
    ScriptEntry Route209_HallowedTower
    ScriptEntry Route209_ArrowSignpostHearthomeCity
    ScriptEntry Route209_ArrowSignpostSolaceonTown
    ScriptEntry Route209_Fisherman
    ScriptEntry Route209_JoggerRichard
    ScriptEntry Route209_JoggerRaul
    ScriptEntry Route209_OnTransitionStock
    ScriptEntry Route209_TrainerTipsSignpost
    ScriptEntry Route209_OnTransition
    ScriptEntry Route209_Arc2Aftermath
    ScriptEntryEnd

// Dazzling Platinum Arc 2, s-hearthome (2.26 aftermath, END OF ARC 2). rift-b's second-visit exit from
// DW_LOST_TOWER lands outside the Lost Tower door (568,681 facing south) with progress 95 (Spiritomb calm).
// Map-local: FLAG_MAP_LOCAL_HIDE_OBSTACLE_16 hides Rowan and Cyrus (shown at 95 only), FLAG_MAP_LOCAL_HIDE_OBSTACLE_17 hides Looker and Garius
// (added by the scene). Cyrus's extra line plays only if VAR_ARC2_CHOICES bit 3 (2.17c crate seen) is set.
// The scene ends on the final Team Eclipse cutaway (polish-b, critic item 4; docs/arc2/cutaways.md caller contract):
// it sets 98, fades to black and warps to the violet room. The cutaway sets 99, warps back here (568,681 facing
// south) and shows END OF ARC 2 / To be continued over the empty tower front.
Route209_OnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    CallIfEq VAR_ARC2_PROGRESS, 95, Route209_ShowAftermath
    GoTo Route209_OnTransition
    End

Route209_ShowAftermath:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    Return

Route209_Arc2Aftermath:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8005, 681, Route209_PlayerStepsOut
    ApplyMovement LOCALID_PLAYER, Route209_Movement_FaceSouth
    WaitMovement
    WaitTime 30, VAR_RESULT
    ApplyMovement LOCALID_PROF_ROWAN, Route209_Movement_FaceEast
    WaitMovement
    Message Route209_Text_RowanDoubted
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_CYRUS, Route209_Movement_FaceWest
    WaitMovement
    Message Route209_Text_CyrusRightTo
    WaitABPadPress
    CloseMessage
    // Looker steps out from behind the tower.
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    AddObject LOCALID_LOOKER
    ApplyMovement LOCALID_LOOKER, Route209_Movement_LookerWalksIn
    WaitMovement
    ApplyMovement LOCALID_PROF_ROWAN, Route209_Movement_FaceEast
    ApplyMovement LOCALID_CYRUS, Route209_Movement_FaceEast
    WaitMovement
    Message Route209_Text_LookerNeverHere
    WaitABPadPress
    Message Route209_Text_LookerCrates
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_LOOKER, Route209_Movement_FaceNorthWest
    WaitMovement
    Message Route209_Text_LookerKnowWho
    WaitABPadPress
    CloseMessage
    SetVarFromVar VAR_0x8008, VAR_ARC2_CHOICES
    GoToIfLt VAR_0x8008, 32768, Route209_Bit3_32768
    SubVar VAR_0x8008, 32768
Route209_Bit3_32768:
    GoToIfLt VAR_0x8008, 16384, Route209_Bit3_16384
    SubVar VAR_0x8008, 16384
Route209_Bit3_16384:
    GoToIfLt VAR_0x8008, 8192, Route209_Bit3_8192
    SubVar VAR_0x8008, 8192
Route209_Bit3_8192:
    GoToIfLt VAR_0x8008, 4096, Route209_Bit3_4096
    SubVar VAR_0x8008, 4096
Route209_Bit3_4096:
    GoToIfLt VAR_0x8008, 2048, Route209_Bit3_2048
    SubVar VAR_0x8008, 2048
Route209_Bit3_2048:
    GoToIfLt VAR_0x8008, 1024, Route209_Bit3_1024
    SubVar VAR_0x8008, 1024
Route209_Bit3_1024:
    GoToIfLt VAR_0x8008, 512, Route209_Bit3_512
    SubVar VAR_0x8008, 512
Route209_Bit3_512:
    GoToIfLt VAR_0x8008, 256, Route209_Bit3_256
    SubVar VAR_0x8008, 256
Route209_Bit3_256:
    GoToIfLt VAR_0x8008, 128, Route209_Bit3_128
    SubVar VAR_0x8008, 128
Route209_Bit3_128:
    GoToIfLt VAR_0x8008, 64, Route209_Bit3_64
    SubVar VAR_0x8008, 64
Route209_Bit3_64:
    GoToIfLt VAR_0x8008, 32, Route209_Bit3_32
    SubVar VAR_0x8008, 32
Route209_Bit3_32:
    GoToIfLt VAR_0x8008, 16, Route209_Bit3_16
    SubVar VAR_0x8008, 16
Route209_Bit3_16:
    GoToIfLt VAR_0x8008, 8, Route209_LookerLeaves
    Message Route209_Text_CyrusToldYou
    WaitABPadPress
    CloseMessage
Route209_LookerLeaves:
    ApplyMovement LOCALID_LOOKER, Route209_Movement_LookerLeaves
    WaitMovement
    RemoveObject LOCALID_LOOKER
    // Garius walks up from the Hearthome side, looks at Cyrus, and gives nothing away.
    BufferRivalName 0
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    AddObject LOCALID_RIVAL_GARIUS
    ApplyMovement LOCALID_RIVAL_GARIUS, Route209_Movement_GariusWalksIn
    WaitMovement
    ApplyMovement LOCALID_PROF_ROWAN, Route209_Movement_FaceWest
    ApplyMovement LOCALID_CYRUS, Route209_Movement_FaceWest
    ApplyMovement LOCALID_PLAYER, Route209_Movement_FaceWest
    WaitMovement
    WaitTime 60, VAR_RESULT
    Message Route209_Text_GariusGuess
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_RIVAL_GARIUS, Route209_Movement_GariusLeaves
    WaitMovement
    RemoveObject LOCALID_RIVAL_GARIUS
    WaitTime 30, VAR_RESULT
    // Final cutaway: no FadeScreenIn after the Warp (the cutaway lifts the black screen itself)
    SetVar VAR_ARC2_PROGRESS, 98
    FadeScreenOut FADE_SCREEN_SPEED_SLOW
    WaitFadeScreen
    Warp MAP_HEADER_GALACTIC_HQ_CONTROL_ROOM, 8, 9, DIR_NORTH
    ReleaseAll
    End

Route209_PlayerStepsOut:
    ApplyMovement LOCALID_PLAYER, Route209_Movement_StepSouth
    WaitMovement
    Return

    .balign 4, 0
Route209_Movement_StepSouth:
    WalkNormalSouth
    EndMovement

    .balign 4, 0
Route209_Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
Route209_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
Route209_Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
Route209_Movement_FaceNorthWest:
    FaceNorth
    Delay8
    FaceWest
    EndMovement

    .balign 4, 0
Route209_Movement_LookerWalksIn:
    WalkNormalWest 2
    EndMovement

    .balign 4, 0
Route209_Movement_LookerLeaves:
    WalkFastEast 4
    EndMovement

    .balign 4, 0
Route209_Movement_GariusWalksIn:
    WalkNormalEast 3
    EndMovement

    .balign 4, 0
Route209_Movement_GariusLeaves:
    WalkNormalWest 6
    EndMovement

Route209_OnTransitionStock:
    GetTimeOfDay VAR_MAP_LOCAL_0x00
    GoToIfEq VAR_MAP_LOCAL_0x00, TIMEOFDAY_MORNING, Route209_SetJoggersBattle
    GoToIfInRange VAR_MAP_LOCAL_0x00, TIMEOFDAY_DAY, TIMEOFDAY_LATE_NIGHT, Route209_SetJoggersNoBattle
    End

Route209_SetJoggersBattle:
    ClearFlag FLAG_HIDE_ROUTE_209_JOGGER_RICHARD
    ClearFlag FLAG_HIDE_ROUTE_209_JOGGER_RAUL
    SetFlag FLAG_HIDE_ROUTE_209_JOGGER_RICHARD_NO_BATTLE
    SetFlag FLAG_HIDE_ROUTE_209_JOGGER_RAUL_NO_BATTLE
    End

Route209_SetJoggersNoBattle:
    ClearFlag FLAG_HIDE_ROUTE_209_JOGGER_RICHARD_NO_BATTLE
    ClearFlag FLAG_HIDE_ROUTE_209_JOGGER_RAUL_NO_BATTLE
    SetFlag FLAG_HIDE_ROUTE_209_JOGGER_RICHARD
    SetFlag FLAG_HIDE_ROUTE_209_JOGGER_RAUL
    End

Route209_PokefanM:
    NPCMessage Route209_Text_ThisIsTheLostTower
    End

Route209_HallowedTower:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfEq VAR_HALLOWED_TOWER_STATE, 1, Route209_CheckSpiritombCounter
    CheckItem ITEM_ODD_KEYSTONE, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route209_ThereIsABrokenTower
    Message Route209_Text_UseTheOddKeystone
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, Route209_UseOddKeystone
    CloseMessage
    ReleaseAll
    End

Route209_UseOddKeystone:
    BufferPlayerName 0
    Message Route209_Text_PlayerUsedTheOddKeystone
    WaitButton
    RemoveItem ITEM_ODD_KEYSTONE, 1, VAR_RESULT
    SetVar VAR_HALLOWED_TOWER_STATE, 1
    CloseMessage
    ReleaseAll
    End

Route209_CheckSpiritombCounter:
    GetSpiritombCounter VAR_RESULT
    GoToIfGe VAR_RESULT, 32, Route209_EncounterSpiritomb
    GoToIfGe VAR_RESULT, 29, Route209_SomeSortOfPresence
    GoToIfGe VAR_RESULT, 22, Route209_IsThatTowerShaking
    GoToIfGe VAR_RESULT, 15, Route209_CryingComingFromInside
    GoToIfGe VAR_RESULT, 8, Route209_StonesAppearToHaveShifted
    GoTo Route209_BuiltManyYearsAgo

Route209_EncounterSpiritomb:
    WaitSE SE_CONFIRM_sseq_3
    PlayCry SPECIES_SPIRITOMB
    Message Route209_Text_SpiritombCry
    WaitCry
    CloseMessage
    StartWildBattle SPECIES_SPIRITOMB, 25
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route209_BlackOut
    SetVar VAR_HALLOWED_TOWER_STATE, 0
    ClearSpiritombCounter
    End

Route209_BlackOut:
    BlackOutFromBattle
    ReleaseAll
    End

Route209_BuiltManyYearsAgo:
    Message Route209_Text_BuiltManyYearsAgo
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route209_StonesAppearToHaveShifted:
    Message Route209_Text_StonesAppearToHaveShifted
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route209_CryingComingFromInside:
    Message Route209_Text_CryingComingFromInside
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route209_IsThatTowerShaking:
    Message Route209_Text_IsTheTowerShaking
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route209_SomeSortOfPresence:
    Message Route209_Text_SomeSortOfPresence
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route209_ThereIsABrokenTower:
    Message Route209_Text_ThereIsABrokenTower
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route209_Fisherman:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    SetVar VAR_0x8004, ITEM_GOOD_ROD
    BufferItemNameWithArticle 0, VAR_0x8004
    CapitalizeFirstLetter 0
    GoToIfSet FLAG_RECEIVED_GOOD_ROD, Route209_AskExplainHowToFish
    Message Route209_Text_GoodRodIsReallyGood
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, Route209_AcceptGoodRod
    GoToIfEq VAR_RESULT, MENU_NO, Route209_RefuseGoodRod
    End

Route209_AskExplainHowToFish:
    BufferItemName 0, VAR_0x8004
    Message Route209_Text_DoINeedToExplain
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, Route209_ExplainHowToFish
    GoToIfEq VAR_RESULT, MENU_NO, Route209_WhenYouReelYouBattle
    End

Route209_ExplainHowToFish:
    Message Route209_Text_ExplainHowToFish
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route209_WhenYouReelYouBattle:
    Message Route209_Text_WhenYouReelYouBattle
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route209_RefuseGoodRod:
    Message Route209_Text_YouDontLikeToFish
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route209_AcceptGoodRod:
    BufferItemName 0, VAR_0x8004
    Message Route209_Text_TakeThisGoodRod
    SetVar VAR_0x8005, 1
    CallCommonScript CommonScript_AddItemQuantity
    SetFlag FLAG_RECEIVED_GOOD_ROD
    GoTo Route209_AskExplainHowToFish

Route209_ArrowSignpostHearthomeCity:
    ShowArrowSign Route209_Text_SignHearthomeCity
    End

Route209_ArrowSignpostSolaceonTown:
    ShowArrowSign Route209_Text_SignSolaceonTown
    End

Route209_TrainerTipsSignpost:
    ShowScrollingSign Route209_Text_TrainerTipsRegisterKeyItems
    End

Route209_JoggerRichard:
    NPCMessage Route209_Text_DoYouJogEveryMorning
    End

Route209_JoggerRaul:
    NPCMessage Route209_Text_PokemonChasedAfterMe
    End

    .balign 4, 0
