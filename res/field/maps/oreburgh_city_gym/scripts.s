#include "macros/scrcmd.inc"
#include "res/text/bank/oreburgh_city_gym.h"
#include "res/field/maps/locals/oreburgh_city_gym.h"


#define FLAG_GYM_RUBBLE_1C FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
#define FLAG_GYM_RUBBLE_1E FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
#define FLAG_GYM_RUBBLE_2M FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
#define FLAG_GYM_RUBBLE_2C FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
#define VAR_GYM_CHUTE_1    VAR_MAP_LOCAL_0x00
#define VAR_GYM_CHUTE_2    VAR_MAP_LOCAL_0x01

    ScriptEntry OreburghGym_Roark
    ScriptEntry OreburghGym_GymGuide
    ScriptEntry OreburghGym_GymStatue
    ScriptEntry OreburghGym_Init
    ScriptEntry OreburghGym_WinchWest
    ScriptEntry OreburghGym_WinchEast
    ScriptEntry OreburghGym_Rubble
    ScriptEntry OreburghGym_LooseRock
    ScriptEntryEnd

OreburghGym_Roark:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfBadgeAcquired BADGE_ID_COAL, OreburghGym_AlreadyHaveCoalBadge
    CreateJournalEvent LOCATION_EVENT_GYM_WAS_TOO_TOUGH, MAP_HEADER_OREBURGH_CITY_GYM
    Message OreburghGym_Text_RoarkIntro
    CloseMessage
    StartTrainerBattle TRAINER_LEADER_ROARK
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, OreburghGym_LostBattle
    Message OreburghGym_Text_BeatRoark
    BufferPlayerName 0
    Message OreburghGym_Text_RoarkReceiveCoalBadge
    PlayFanfare SEQ_BADGE_sseq
    WaitFanfare
    GoTo TRAINER_YOUNGSTER_JONATHON
    SetTrainerFlag TRAINER_YOUNGSTER_DARIUS
    GiveBadge BADGE_ID_COAL
    IncrementTrainerScore2 TRAINER_SCORE_EVENT_BADGE_EARNED
    SetTrainerFlag TRAINER_YOUNGSTER_JONATHON
    SetTrainerFlag TRAINER_YOUNGSTER_DARIUS
    SetFlag FLAG_HIDE_POKECENTER_BASEMENT_BLOCKADE
    SetVar VAR_GTS_ACCESS_STATE, TRUE
    SetVar VAR_OREBURGH_CITY_STATE, 2
    // Arc 1: 15 = Coal Badge won; the Oreburgh City frame script runs the mine rift scene on leaving.
    // The stock Pal Pad Looker (VAR_JUBILIFE_LOOKER_PAL_PAD_STATE) and Jubilife Galactic tag battle
    // (VAR_JUBILIFE_CITY_STATE 3 and the FLAG_HIDE_JUBILIFE_* clears) are gone in Arc 1.
    SetVar VAR_ARC1_PROGRESS, 15
    CreateJournalEvent LOCATION_EVENT_BEAT_GYM_LEADER, MAP_HEADER_OREBURGH_CITY_GYM, TRAINER_LEADER_ROARK
    SetFlag FLAG_HIDE_SANDGEM_TOWN_LAB_PROF_ROWAN
    // Puzzle: clear the rock chutes (off screen from the dais) so the way out is open.
    Call OreburghGym_ClearRubble
    Message OreburghGym_Text_RoarkExplainCoalBadge
    GoTo OreburghGym_RoarkGiveTM76
    End

OreburghGym_RoarkGiveTM76:
    SetVar VAR_0x8004, ITEM_TM76
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, OreburghGym_RoarkGiveTM76BagFull
    CallCommonScript CommonScript_AddItemQuantity
    SetFlag FLAG_RECEIVED_ROARK_TM76
    BufferItemName 0, VAR_0x8004
    BufferTMHMMoveName 1, VAR_0x8004
    Message OreburghGym_Text_RoarkExplainStealthRock
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghGym_RoarkGiveTM76BagFull:
    CallCommonScript CommonScript_BagIsFull
    CloseMessage
    ReleaseAll
    End

OreburghGym_AlreadyHaveCoalBadge:
    GoToIfUnset FLAG_RECEIVED_ROARK_TM76, OreburghGym_RoarkGiveTM76
    Message OreburghGym_Text_RoarkGymBeaten
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghGym_LostBattle:
    BlackOutFromBattle
    ReleaseAll
    End

OreburghGym_GymGuide:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfBadgeAcquired BADGE_ID_COAL, OreburghGym_GymGuideAfterBadge
    Message OreburghGym_Text_GymGuideBeforeBadge
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghGym_GymGuideAfterBadge:
    BufferPlayerName 0
    Message OreburghGym_Text_GymGuideAfterBadge
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghGym_GymStatue:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfBadgeAcquired BADGE_ID_COAL, OreburghGym_GymStatueAfterBadge
    BufferRivalName 0
    BufferRivalName 1
    Message OreburghGym_Text_GymStatueBeforeBadge
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghGym_GymStatueAfterBadge:
    BufferRivalName 0
    BufferPlayerName 1
    BufferRivalName 2
    Message OreburghGym_Text_GymStatueAfterBadge
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0

OreburghGym_Init:
    // a saved var, not VAR_RESULT: the special vars aren't safe on every map-load path
    CheckBadgeAcquired BADGE_ID_COAL, VAR_MAP_LOCAL_0x02
    GoToIfEq VAR_MAP_LOCAL_0x02, TRUE, OreburghGym_InitCleared
    // Darius stands past both winches: beating him means the puzzle was solved (e.g. re-entry after a blackout)
    GoToIfDefeated TRAINER_YOUNGSTER_DARIUS, OreburghGym_InitCleared
    SetVar VAR_GYM_CHUTE_1, 0
    SetVar VAR_GYM_CHUTE_2, 0
    ClearFlag FLAG_GYM_RUBBLE_1C
    SetFlag FLAG_GYM_RUBBLE_1E
    ClearFlag FLAG_GYM_RUBBLE_2M
    SetFlag FLAG_GYM_RUBBLE_2C
    End

OreburghGym_InitCleared:
    SetVar VAR_GYM_CHUTE_1, 2
    SetVar VAR_GYM_CHUTE_2, 2
    SetFlag FLAG_GYM_RUBBLE_1C
    SetFlag FLAG_GYM_RUBBLE_1E
    SetFlag FLAG_GYM_RUBBLE_2M
    SetFlag FLAG_GYM_RUBBLE_2C
    End

// Removes whichever piles are out and marks both chutes cleared. Called from Roark's win.
OreburghGym_ClearRubble:
    CallIfUnset FLAG_GYM_RUBBLE_1C, OreburghGym_RemoveRubble1C
    CallIfUnset FLAG_GYM_RUBBLE_1E, OreburghGym_RemoveRubble1E
    CallIfUnset FLAG_GYM_RUBBLE_2M, OreburghGym_RemoveRubble2M
    CallIfUnset FLAG_GYM_RUBBLE_2C, OreburghGym_RemoveRubble2C
    SetVar VAR_GYM_CHUTE_1, 2
    SetVar VAR_GYM_CHUTE_2, 2
    Return

OreburghGym_RemoveRubble1C:
    SetFlag FLAG_GYM_RUBBLE_1C
    RemoveObject LOCALID_RUBBLE_1C_UPPER
    RemoveObject LOCALID_RUBBLE_1C_MID
    RemoveObject LOCALID_RUBBLE_1C_LOWER
    Return

OreburghGym_RemoveRubble1E:
    SetFlag FLAG_GYM_RUBBLE_1E
    RemoveObject LOCALID_RUBBLE_1E
    Return

OreburghGym_RemoveRubble2M:
    SetFlag FLAG_GYM_RUBBLE_2M
    RemoveObject LOCALID_RUBBLE_2M
    Return

OreburghGym_RemoveRubble2C:
    SetFlag FLAG_GYM_RUBBLE_2C
    RemoveObject LOCALID_RUBBLE_2C_UPPER
    RemoveObject LOCALID_RUBBLE_2C_MID
    RemoveObject LOCALID_RUBBLE_2C_LOWER
    Return

// West winch (west ledge, by the entrance): chute 1, C <-> E
OreburghGym_WinchWest:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfGe VAR_GYM_CHUTE_1, 2, OreburghGym_WinchIdle
    Message OreburghGym_Text_WinchPrompt
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, OreburghGym_WinchCancel
    ApplyMovement LOCALID_WINCH_WEST, OreburghGym_Movement_MachopHeave
    Call OreburghGym_WinchHeave
    GoToIfEq VAR_GYM_CHUTE_1, 1, OreburghGym_Chute1EToC
    // C -> E
    ApplyMovement LOCALID_RUBBLE_1C_UPPER, OreburghGym_Movement_RubbleLoosen
    ApplyMovement LOCALID_RUBBLE_1C_MID, OreburghGym_Movement_RubbleLoosen
    ApplyMovement LOCALID_RUBBLE_1C_LOWER, OreburghGym_Movement_RubbleLoosen
    WaitMovement
    Call OreburghGym_RemoveRubble1C
    Call OreburghGym_RockfallFx
    ClearFlag FLAG_GYM_RUBBLE_1E
    AddObject LOCALID_RUBBLE_1E
    ApplyMovement LOCALID_RUBBLE_1E, OreburghGym_Movement_RubbleLand
    WaitMovement
    SetVar VAR_GYM_CHUTE_1, 1
    Message OreburghGym_Text_SlideLowerToEast
    GoTo OreburghGym_WinchDone
    End

OreburghGym_Chute1EToC:
    // the lower stairs already hold chute 2's pile (not reachable in play; kept safe)
    GoToIfEq VAR_GYM_CHUTE_2, 1, OreburghGym_WinchJam
    ApplyMovement LOCALID_RUBBLE_1E, OreburghGym_Movement_RubbleLoosen
    WaitMovement
    Call OreburghGym_RemoveRubble1E
    Call OreburghGym_RockfallFx
    ClearFlag FLAG_GYM_RUBBLE_1C
    AddObject LOCALID_RUBBLE_1C_UPPER
    AddObject LOCALID_RUBBLE_1C_MID
    AddObject LOCALID_RUBBLE_1C_LOWER
    ApplyMovement LOCALID_RUBBLE_1C_UPPER, OreburghGym_Movement_RubbleLand
    ApplyMovement LOCALID_RUBBLE_1C_MID, OreburghGym_Movement_RubbleLand
    ApplyMovement LOCALID_RUBBLE_1C_LOWER, OreburghGym_Movement_RubbleLand
    WaitMovement
    SetVar VAR_GYM_CHUTE_1, 0
    Message OreburghGym_Text_SlideEastToLower
    GoTo OreburghGym_WinchDone
    End

// East winch (east ledge, upper floor): chute 2, M <-> C
OreburghGym_WinchEast:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfGe VAR_GYM_CHUTE_2, 2, OreburghGym_WinchIdle
    Message OreburghGym_Text_WinchPrompt
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, OreburghGym_WinchCancel
    ApplyMovement LOCALID_WINCH_EAST, OreburghGym_Movement_MachopHeave
    Call OreburghGym_WinchHeave
    GoToIfEq VAR_GYM_CHUTE_2, 1, OreburghGym_Chute2CToM
    // M -> C: jams if chute 1's pile is still on the lower stairs (not reachable in play)
    GoToIfEq VAR_GYM_CHUTE_1, 0, OreburghGym_WinchJam
    ApplyMovement LOCALID_RUBBLE_2M, OreburghGym_Movement_RubbleLoosen
    WaitMovement
    Call OreburghGym_RemoveRubble2M
    Call OreburghGym_RockfallFx
    ClearFlag FLAG_GYM_RUBBLE_2C
    AddObject LOCALID_RUBBLE_2C_UPPER
    AddObject LOCALID_RUBBLE_2C_MID
    AddObject LOCALID_RUBBLE_2C_LOWER
    ApplyMovement LOCALID_RUBBLE_2C_UPPER, OreburghGym_Movement_RubbleLand
    ApplyMovement LOCALID_RUBBLE_2C_MID, OreburghGym_Movement_RubbleLand
    ApplyMovement LOCALID_RUBBLE_2C_LOWER, OreburghGym_Movement_RubbleLand
    WaitMovement
    SetVar VAR_GYM_CHUTE_2, 1
    Message OreburghGym_Text_SlideUpperToLower
    GoTo OreburghGym_WinchDone
    End

OreburghGym_Chute2CToM:
    ApplyMovement LOCALID_RUBBLE_2C_UPPER, OreburghGym_Movement_RubbleLoosen
    ApplyMovement LOCALID_RUBBLE_2C_MID, OreburghGym_Movement_RubbleLoosen
    ApplyMovement LOCALID_RUBBLE_2C_LOWER, OreburghGym_Movement_RubbleLoosen
    WaitMovement
    Call OreburghGym_RemoveRubble2C
    Call OreburghGym_RockfallFx
    ClearFlag FLAG_GYM_RUBBLE_2M
    AddObject LOCALID_RUBBLE_2M
    ApplyMovement LOCALID_RUBBLE_2M, OreburghGym_Movement_RubbleLand
    WaitMovement
    SetVar VAR_GYM_CHUTE_2, 0
    Message OreburghGym_Text_SlideLowerToUpper
    GoTo OreburghGym_WinchDone
    End

// Machop's cry and the winch clank; the caller has started the Machop's heave movement.
OreburghGym_WinchHeave:
    CloseMessage
    PlayCry SPECIES_MACHOP
    WaitMovement
    WaitCry
    PlayFanfare SEQ_SE_DP_KI_GASYAN_sseq
    WaitFanfare

OreburghGym_RockfallFx:
    PlayFanfare SEQ_SE_DP_WALL_HIT2_sseq
    ShakeCamera 16, 3
    Return

OreburghGym_WinchJam:
    Message OreburghGym_Text_WinchJammed
    GoTo OreburghGym_WinchDone
    End

OreburghGym_WinchDone:
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghGym_WinchCancel:
    CloseMessage
    ReleaseAll
    End

OreburghGym_WinchIdle:
    Message OreburghGym_Text_WinchIdle
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghGym_Rubble:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message OreburghGym_Text_Rubble
    WaitButton
    CloseMessage
    ReleaseAll
    End

OreburghGym_LooseRock:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message OreburghGym_Text_LooseRock
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
OreburghGym_Movement_MachopHeave:
    LockDir
    JumpOnSpotFastSouth 2
    UnlockDir
    EndMovement

    .balign 4, 0
OreburghGym_Movement_RubbleLoosen:
    LockDir
    JumpOnSpotFastNorth 2
    SetInvisible
    EndMovement

    .balign 4, 0
OreburghGym_Movement_RubbleLand:
    LockDir
    JumpOnSpotSlowNorth
    EndMovement

    .balign 4, 0
