#include "macros/scrcmd.inc"
#include "res/text/bank/trainers_school.h"
#include "res/text/bank/menu_entries.h"
#include "res/field/maps/locals/trainers_school.h"


    ScriptEntry TrainersSchool_Rival
    ScriptEntry TrainersSchool_AceTrainerF
    ScriptEntry TrainersSchool_Dummy3
    ScriptEntry TrainersSchool_Youngster1
    ScriptEntry TrainersSchool_Youngster2
    ScriptEntry TrainersSchool_Lass
    ScriptEntry TrainersSchool_Dummy7
    ScriptEntry TrainersSchool_Dummy8
    ScriptEntry TrainersSchool_SchoolKidHarrison
    ScriptEntry TrainersSchool_SchoolKidChristine
    ScriptEntry TrainersSchool_Blackboard
    ScriptEntry TrainersSchool_Book
    ScriptEntry TrainersSchool_Arc2Cast
    ScriptEntry TrainersSchool_Arc2OnTransition
    ScriptEntry TrainersSchool_Arc2Confession
    ScriptEntryEnd

TrainersSchool_Rival:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    BufferPlayerName 0
    BufferRivalName 1
    Message TrainersSchool_Text_GotSomethingForMe
    PlayFanfare SEQ_FANFA4_sseq
    BufferPlayerName 0
    Message TrainersSchool_Text_PlayerDeliveredTheParcel
    WaitFanfare
    RemoveItem ITEM_PARCEL, 1, VAR_RESULT
    BufferPlayerName 0
    BufferRivalName 1
    Message TrainersSchool_Text_TakeTownMap
    SetVar VAR_0x8004, ITEM_TOWN_MAP
    SetVar VAR_0x8005, 1
    CallCommonScript CommonScript_AddItemQuantity
    BufferRivalName 1
    Message TrainersSchool_Text_OreburghCityNext
    CloseMessage
    GetPlayerDir VAR_RESULT
    SetVar VAR_0x8008, VAR_RESULT
    GoToIfEq VAR_0x8008, DIR_NORTH, TrainersSchool_RivalLeaveNorth
    GoToIfEq VAR_0x8008, DIR_WEST, TrainersSchool_RivalLeaveWest
    GoTo TrainersSchool_RivalLeaveEast
    End

TrainersSchool_RivalLeaveNorth:
    ApplyMovement LOCALID_RIVAL, TrainersSchool_Movement_RivalLeaveNorth
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Movement_PlayerWatchRivalLeaveNorth
    WaitMovement
    GoTo TrainersSchool_RivalEnd
    End

TrainersSchool_RivalLeaveWest:
    ApplyMovement LOCALID_RIVAL, TrainersSchool_Movement_RivalLeaveWestEast
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Movement_PlayerWatchRivalLeaveWestEast
    WaitMovement
    GoTo TrainersSchool_RivalEnd
    End

TrainersSchool_RivalLeaveEast:
    ApplyMovement LOCALID_RIVAL, TrainersSchool_Movement_RivalLeaveWestEast
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Movement_PlayerWatchRivalLeaveWestEast
    WaitMovement
    GoTo TrainersSchool_RivalEnd
    End

TrainersSchool_RivalEnd:
    PlaySE SEQ_SE_DP_KAIDAN2_sseq
    RemoveObject LOCALID_RIVAL
    WaitSE SEQ_SE_DP_KAIDAN2_sseq
    SetVar VAR_POKETCH_CAMPAIGN_STATE, 1
    SetFlag FLAG_TALKED_TO_TRAINERS_SCHOOL_RIVAL
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_POKETCH_CO_PRESIDENT
    ClearFlag FLAG_HIDE_JUBILIFE_CITY_CLOWNS_1_AND_2
    ReleaseAll
    End

    .balign 4, 0
TrainersSchool_Movement_RivalLeaveNorth:
    WalkFastEast
    WalkFastSouth 8
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
TrainersSchool_Movement_RivalLeaveWestEast:
    WalkFastSouth 4
    WalkFastEast
    WalkFastSouth 4
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
TrainersSchool_Movement_PlayerWatchRivalLeaveNorth:
    Delay8
    WalkOnSpotNormalEast
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
TrainersSchool_Movement_PlayerWatchRivalLeaveWestEast:
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

TrainersSchool_AceTrainerF:
    NPCMessage TrainersSchool_Text_DevelopAtOwnPace
    End

TrainersSchool_Dummy3:
    End

TrainersSchool_Youngster1:
    NPCMessage TrainersSchool_Text_LearnedAboutPokemonTypes
    End

TrainersSchool_Youngster2:
    NPCMessage TrainersSchool_Text_WroteAnEssay
    End

TrainersSchool_Lass:
    NPCMessage TrainersSchool_Text_PokemonUseItems
    End

TrainersSchool_Dummy7:
    End

TrainersSchool_Dummy8:
    End

TrainersSchool_SchoolKidHarrison:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_RECEIVED_TRAINERS_SCHOOL_POTION, TrainersSchool_PotionRestoresHP
    GoToIfSet FLAG_DEFEATED_TRAINERS_SCHOOL_SCHOOL_KID_HARRISON, TrainersSchool_TryGivePotion
    Message TrainersSchool_Text_CanWeBattleYou
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, TrainersSchool_BattleSchoolKidHarrison
    GoToIfEq VAR_RESULT, MENU_NO, TrainersSchool_ButBattlingIsTheBest
    End

TrainersSchool_BattleSchoolKidHarrison:
    Message TrainersSchool_Text_GoMyPokemonGo
    CloseMessage
    GetPlayerStarterSpecies VAR_RESULT
    GoToIfEq VAR_RESULT, SPECIES_TURTWIG, TrainersSchool_BattleHarrisonTurtwig
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, TrainersSchool_BattleHarrisonChimchar
    GoTo TrainersSchool_BattleHarrisonPiplup
    End

TrainersSchool_BattleHarrisonPiplup:
    StartTrainerBattle TRAINER_SCHOOL_KID_HARRISON
    GoTo TrainersSchool_CheckWonBattleHarrison
    End

TrainersSchool_BattleHarrisonTurtwig:
    StartTrainerBattle TRAINER_SCHOOL_KID_HARRISON
    GoTo TrainersSchool_CheckWonBattleHarrison
    End

TrainersSchool_BattleHarrisonChimchar:
    StartTrainerBattle TRAINER_SCHOOL_KID_HARRISON
    GoTo TrainersSchool_CheckWonBattleHarrison
    End

TrainersSchool_CheckWonBattleHarrison:
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, TrainersSchool_LostBattleHarrison
    SetFlag FLAG_DEFEATED_TRAINERS_SCHOOL_SCHOOL_KID_HARRISON
    GoToIfSet FLAG_DEFEATED_TRAINERS_SCHOOL_SCHOOL_KID_CHRISTINE, TrainersSchool_GivePotion
    GoToIfUnset FLAG_DEFEATED_TRAINERS_SCHOOL_SCHOOL_KID_CHRISTINE, TrainersSchool_HardToWin
    End

TrainersSchool_HardToWin:
    Message TrainersSchool_Text_HardToWin
    WaitButton
    CloseMessage
    ReleaseAll
    End

TrainersSchool_GivePotion:
    Message TrainersSchool_Text_UseThisPotion
    SetVar VAR_0x8004, ITEM_POTION
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, TrainersSchool_BagIsFull
    CallCommonScript CommonScript_AddItemQuantity
    SetFlag FLAG_RECEIVED_TRAINERS_SCHOOL_POTION
    GoTo TrainersSchool_PotionRestoresHP
    End

TrainersSchool_PotionRestoresHP:
    Message TrainersSchool_Text_PotionRestoresHP
    WaitButton
    CloseMessage
    ReleaseAll
    End

TrainersSchool_BagIsFull:
    CallCommonScript CommonScript_BagIsFull
    CloseMessage
    ReleaseAll
    End

TrainersSchool_TryGivePotion:
    GoToIfSet FLAG_DEFEATED_TRAINERS_SCHOOL_SCHOOL_KID_CHRISTINE, TrainersSchool_GivePotion
    Message TrainersSchool_Text_HardToWin
    WaitButton
    CloseMessage
    ReleaseAll
    End

TrainersSchool_ButBattlingIsTheBest:
    Message TrainersSchool_Text_ButBattlingIsTheBest
    WaitButton
    CloseMessage
    ReleaseAll
    End

TrainersSchool_LostBattleHarrison:
    BlackOutFromBattle
    ReleaseAll
    End

TrainersSchool_SchoolKidChristine:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_DEFEATED_TRAINERS_SCHOOL_SCHOOL_KID_CHRISTINE, TrainersSchool_PostBattleChristine
    Message TrainersSchool_Text_MayWeBattle
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, TrainersSchool_BattleSchoolKidChristine
    GoToIfEq VAR_RESULT, MENU_NO, TrainersSchool_DontBeShy
    End

TrainersSchool_BattleSchoolKidChristine:
    Message TrainersSchool_Text_TryThingsILearned
    CloseMessage
    GetPlayerStarterSpecies VAR_RESULT
    GoToIfEq VAR_RESULT, SPECIES_TURTWIG, TrainersSchool_BattleChristineTurtwig
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, TrainersSchool_BattleChristineChimchar
    GoTo TrainersSchool_BattleChristinePiplup
    End

TrainersSchool_BattleChristinePiplup:
    StartTrainerBattle TRAINER_SCHOOL_KID_CHRISTINE
    GoTo TrainersSchool_CheckWonBattleChristine
    End

TrainersSchool_BattleChristineTurtwig:
    StartTrainerBattle TRAINER_SCHOOL_KID_CHRISTINE
    GoTo TrainersSchool_CheckWonBattleChristine
    End

TrainersSchool_BattleChristineChimchar:
    StartTrainerBattle TRAINER_SCHOOL_KID_CHRISTINE
    GoTo TrainersSchool_CheckWonBattleChristine
    End

TrainersSchool_CheckWonBattleChristine:
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, TrainersSchool_LostBattleChristine
    SetFlag FLAG_DEFEATED_TRAINERS_SCHOOL_SCHOOL_KID_CHRISTINE
    GoToIfSet FLAG_DEFEATED_TRAINERS_SCHOOL_SCHOOL_KID_HARRISON, TrainersSchool_DefeatedChristineAndHarrison
    GoToIfUnset FLAG_DEFEATED_TRAINERS_SCHOOL_SCHOOL_KID_HARRISON, TrainersSchool_CouldHaveDoneBetter
    End

TrainersSchool_PostBattleChristine:
    Message TrainersSchool_Text_CouldHaveDoneBetter
    WaitButton
    CloseMessage
    ReleaseAll
    End

TrainersSchool_DontBeShy:
    Message TrainersSchool_Text_DontBeShy
    WaitButton
    CloseMessage
    ReleaseAll
    End

TrainersSchool_CouldHaveDoneBetter:
    Message TrainersSchool_Text_CouldHaveDoneBetter
    WaitButton
    CloseMessage
    ReleaseAll
    End

TrainersSchool_DefeatedChristineAndHarrison:
    GoToIfSet FLAG_RECEIVED_TRAINERS_SCHOOL_POTION, TrainersSchool_CouldHaveDoneBetter
    Message TrainersSchool_Text_TalkToMyFriend
    WaitButton
    CloseMessage
    ReleaseAll
    End

TrainersSchool_LostBattleChristine:
    BlackOutFromBattle
    ReleaseAll
    End

TrainersSchool_Blackboard:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message TrainersSchool_Text_BlackboardListsStatusChanges
    GoTo TrainersSchool_StatusMenu
    End

TrainersSchool_StatusMenu:
    Message TrainersSchool_Text_ReadAboutWhichStatus
    InitGlobalTextMenu 7, 2, 0, VAR_RESULT
    AddMenuEntryImm MenuEntries_Text_Status_Poisoned, 0
    AddMenuEntryImm MenuEntries_Text_Status_Paralyzed, 1
    AddMenuEntryImm MenuEntries_Text_Status_Asleep, 2
    AddMenuEntryImm MenuEntries_Text_Status_Burned, 3
    AddMenuEntryImm MenuEntries_Text_Status_Frozen, 4
    AddMenuEntryImm MenuEntries_Text_Exit, 5
    ShowMenuMultiColumn 2
    SetVar VAR_0x8008, VAR_RESULT
    GoToIfEq VAR_0x8008, 0, TrainersSchool_StatusPoisoned
    GoToIfEq VAR_0x8008, 1, TrainersSchool_StatusParalyzed
    GoToIfEq VAR_0x8008, 2, TrainersSchool_StatusAsleep
    GoToIfEq VAR_0x8008, 3, TrainersSchool_StatusBurned
    GoToIfEq VAR_0x8008, 4, TrainersSchool_StatusFrozen
    GoTo TrainersSchool_BlackboardEnd
    End

TrainersSchool_StatusPoisoned:
    Message TrainersSchool_Text_StatusPoisoned
    GoTo TrainersSchool_StatusMenu
    End

TrainersSchool_StatusParalyzed:
    Message TrainersSchool_Text_StatusParalyzed
    GoTo TrainersSchool_StatusMenu
    End

TrainersSchool_StatusAsleep:
    Message TrainersSchool_Text_StatusAsleep
    GoTo TrainersSchool_StatusMenu
    End

TrainersSchool_StatusBurned:
    Message TrainersSchool_Text_StatusBurned
    GoTo TrainersSchool_StatusMenu
    End

TrainersSchool_StatusFrozen:
    Message TrainersSchool_Text_StatusFrozen
    GoTo TrainersSchool_StatusMenu
    End

TrainersSchool_BlackboardEnd:
    CloseMessage
    ReleaseAll
    End

TrainersSchool_Book:
    EventMessage TrainersSchool_Text_NotebookFilledWithWriting
    End

    .balign 4, 0

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 2 (s-jubilife): 2.2, the confession. Seats around the table: Rowan (2,8), the player
// (2,9), Ruth (5,8), Garius (5,9); Cyrus stands at the front (4,6). The table's 3D model hides any object on its
// tiles (3-4, 8-9), so Rowan's case opens at the foot of the table: the Poke Ball appears on the floor at (3,10).

TrainersSchool_Arc2OnTransition:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    GoToIfNe VAR_ARC2_PROGRESS, 1, TrainersSchool_Arc2OnTransitionEnd
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
TrainersSchool_Arc2OnTransitionEnd:
    End

// The cast is only here during the scene (the player is locked)
TrainersSchool_Arc2Cast:
    End

// On frame at VAR_ARC2_PROGRESS 1 (scripts_init_trainers_school.s). The player has walked here from the plaza (2.1
// no longer warps in): from the door mat (7,11) they walk to their seat at the table (2,9), below Rowan.
TrainersSchool_Arc2Confession:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8004, 7, TrainersSchool_Arc2ConfessionSeated
    GoToIfNe VAR_0x8005, 11, TrainersSchool_Arc2ConfessionSeated
    WaitTime 15, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Arc2Movement_PlayerToSeat
    WaitMovement
TrainersSchool_Arc2ConfessionSeated:
    WaitTime 30, VAR_RESULT
    Message TrainersSchool_Text_Arc2RowanReadings
    WaitABPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2RuthTotem
    WaitABPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2CyrusNotAsAStranger
    WaitABPadPress
    CloseMessage
    WaitTime 20, VAR_RESULT
    Message TrainersSchool_Text_Arc2CyrusMyName
    WaitABPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2CyrusSpirit
    WaitABPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2CyrusChained
    WaitABPadPress
    CloseMessage
    // Garius cuts in the moment he hears it, so the confession becomes an argument (critic item 8). He is on his
    // feet so fast his chair scrapes.
    PlaySE SEQ_SE_DP_WALL_HIT2_sseq
    ApplyMovement LOCALID_ARC2_GARIUS, TrainersSchool_Arc2Movement_Jump
    ApplyMovement LOCALID_ARC2_RUTH, TrainersSchool_Arc2Movement_Exclaim
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Arc2Movement_FaceEast
    WaitMovement
    WaitSE SEQ_SE_DP_WALL_HIT2_sseq
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2GariusChained
    WaitABPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2RuthLakeGuardians
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Arc2Movement_FaceNorth
    WaitMovement
    Message TrainersSchool_Text_Arc2CyrusABoy
    WaitABPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2CyrusHowLong
    WaitABPadPress
    CloseMessage
    // Rowan stands, slowly (pays off his lab line "...Nobody.")
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_ARC2_ROWAN, TrainersSchool_Arc2Movement_RowanStand
    WaitMovement
    Message TrainersSchool_Text_Arc2RowanNobody
    WaitABPadPress
    CloseMessage
    // Garius, still standing, rounds on Cyrus again
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Arc2Movement_FaceEast
    WaitMovement
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2GariusSomeOfUs
    WaitABPadPress
    CloseMessage
    WaitTime 30, VAR_RESULT
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2GariusForgetIt
    WaitABPadPress
    CloseMessage
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2RowanSitDown
    WaitABPadPress
    CloseMessage
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2GariusHeShouldGo
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Arc2Movement_FaceNorth
    WaitMovement
    Message TrainersSchool_Text_Arc2CyrusRightToBeAngry
    WaitABPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2RowanNotAsking
    WaitABPadPress
    CloseMessage
    // Rowan sits back down, sets his case down at the foot of the table and opens it: one Poke Ball
    ApplyMovement LOCALID_ARC2_ROWAN, TrainersSchool_Arc2Movement_RowanSitAndFaceTable
    WaitMovement
    PlaySE SEQ_SE_DP_BOX03_sseq
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    AddObject LOCALID_ARC2_BALL
    WaitSE SEQ_SE_DP_BOX03_sseq
    WaitTime 15, VAR_RESULT
    Message TrainersSchool_Text_Arc2RowanThisOne
    WaitABPadPress
    CloseMessage
    // Cyrus comes around the table, slowly, and stands over the ball
    ApplyMovement LOCALID_ARC2_CYRUS, TrainersSchool_Arc2Movement_CyrusToTable
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Arc2Movement_PlayerWatchCyrusToTable
    WaitMovement
    Message TrainersSchool_Text_Arc2RowanNewStart
    WaitABPadPress
    CloseMessage
    WaitTime 45, VAR_RESULT
    // He takes it (the starter weak to the player's: his battle 1 team, outside)
    RemoveObject LOCALID_ARC2_BALL
    WaitTime 15, VAR_RESULT
    Message TrainersSchool_Text_Arc2CyrusNotHeld
    WaitABPadPress
    CloseMessage
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2GariusCountMeOut
    WaitABPadPress
    CloseMessage
    // Garius walks out; Ruth steps after him
    ApplyMovement LOCALID_ARC2_GARIUS, TrainersSchool_Arc2Movement_GariusLeave
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Arc2Movement_PlayerWatchGarius
    WaitMovement
    PlaySE SEQ_SE_DP_KAIDAN2_sseq
    RemoveObject LOCALID_ARC2_GARIUS
    WaitSE SEQ_SE_DP_KAIDAN2_sseq
    ApplyMovement LOCALID_ARC2_RUTH, TrainersSchool_Arc2Movement_RuthStep
    WaitMovement
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2RuthWait
    WaitABPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2RowanLetHimGo
    WaitABPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2RowanMorning
    WaitABPadPress
    CloseMessage
    // Cyrus walks outside (2.3 waits by the door, in Jubilife)
    ApplyMovement LOCALID_ARC2_CYRUS, TrainersSchool_Arc2Movement_CyrusLeave
    WaitMovement
    PlaySE SEQ_SE_DP_KAIDAN2_sseq
    RemoveObject LOCALID_ARC2_CYRUS
    WaitSE SEQ_SE_DP_KAIDAN2_sseq
    WaitTime 20, VAR_RESULT
    // Rowan and Ruth follow him out the door (no fade: the player watches them go, then walks out too)
    ApplyMovement LOCALID_ARC2_RUTH, TrainersSchool_Arc2Movement_RuthLeave
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Arc2Movement_FaceEast
    WaitMovement
    PlaySE SEQ_SE_DP_KAIDAN2_sseq
    RemoveObject LOCALID_ARC2_RUTH
    WaitSE SEQ_SE_DP_KAIDAN2_sseq
    ApplyMovement LOCALID_ARC2_ROWAN, TrainersSchool_Arc2Movement_RowanLeave
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Arc2Movement_PlayerWatchRowanLeave
    WaitMovement
    PlaySE SEQ_SE_DP_KAIDAN2_sseq
    RemoveObject LOCALID_ARC2_ROWAN
    WaitSE SEQ_SE_DP_KAIDAN2_sseq
    SetVar VAR_ARC2_PROGRESS, 3
    ReleaseAll
    End

    .balign 4, 0
TrainersSchool_Arc2Movement_RowanStand:
    WalkSlowNorth
    FaceEast
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_RowanSitAndFaceTable:
    WalkSlowSouth
    FaceEast
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_Jump:
    JumpOnSpotFastNorth
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_Exclaim:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_FaceNorth:
    FaceNorth
    EndMovement

    // From the front (4,6) around the east side (column 6) to beside the ball (4,10), facing it
    .balign 4, 0
TrainersSchool_Arc2Movement_CyrusToTable:
    WalkNormalSouth
    WalkNormalEast 2
    WalkNormalSouth 3
    WalkNormalWest 2
    FaceWest
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_PlayerWatchCyrusToTable:
    FaceEast
    Delay16 6
    FaceSouth
    EndMovement

    // From (5,9): south, east along row 10 to the door column, out through the door (7,11)
    .balign 4, 0
TrainersSchool_Arc2Movement_GariusLeave:
    WalkFastSouth
    WalkFastEast 2
    WalkFastSouth
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_PlayerWatchGarius:
    Delay8
    FaceSouth
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_RuthStep:
    WalkNormalSouth
    EndMovement

    // From (4,10): east along row 10 to the door column, out (7,11)
    .balign 4, 0
TrainersSchool_Arc2Movement_CyrusLeave:
    WalkNormalEast 3
    WalkNormalSouth
    EndMovement

    // From the door mat (7,11): north, west along row 10 (the open floor below the table), north into the seat (2,9)
    .balign 4, 0
TrainersSchool_Arc2Movement_PlayerToSeat:
    WalkNormalNorth
    WalkNormalWest 5
    WalkNormalNorth
    FaceNorth
    EndMovement

    // Ruth (5,9, after her step): south, east along row 10, out the door (7,11)
    .balign 4, 0
TrainersSchool_Arc2Movement_RuthLeave:
    WalkNormalSouth
    WalkNormalEast 2
    WalkNormalSouth
    EndMovement

    // Rowan (2,8, north of the player): around the west end of the table (column 1), east along row 10, out (7,11)
    .balign 4, 0
TrainersSchool_Arc2Movement_RowanLeave:
    WalkNormalWest
    WalkNormalSouth 2
    WalkNormalEast 6
    WalkNormalSouth
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_PlayerWatchRowanLeave:
    FaceWest
    Delay16 2
    FaceSouth
    Delay16 3
    FaceEast
    EndMovement
