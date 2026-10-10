#include "macros/scrcmd.inc"
#include "res/text/bank/oreburgh_city_gym.h"
#include "res/field/events/events_oreburgh_city_gym.h"

// Rock-slide puzzle (Arc 1 round 3). Two Machop winch crews each work a rock chute that slides its rubble
// between two gates: chute 1 (west winch, VAR_MAP_LOCAL_0) between the lower stairs C and the east path
// E (9,12); chute 2 (east winch, VAR_MAP_LOCAL_1) between the upper stairs M (5,9) and C. C is a pile of three
// boulders down the lower stairs, (5,12) top step + (5,13) + (5,14): the stair foot (5,15) is hidden behind the
// railing, and object collision ignores a height gap of 16 units or more, so a boulder on a slope tile only
// blocks from one side. (5,12) blocks from above, (5,14) from below, (5,13) is for looks.
// Value 0/1 = which gate the pile is on, 2 = cleared. Map-local flags 0x30-0x33 hide the four piles; map-local
// flags and vars are cleared on every map change, so OreburghGym_Init re-arms the puzzle on entry.
#define FLAG_GYM_RUBBLE_1C FLAG_UNK_0x0030
#define FLAG_GYM_RUBBLE_1E FLAG_UNK_0x0031
#define FLAG_GYM_RUBBLE_2M FLAG_UNK_0x0032
#define FLAG_GYM_RUBBLE_2C FLAG_UNK_0x0033
#define VAR_GYM_CHUTE_1    VAR_MAP_LOCAL_0
#define VAR_GYM_CHUTE_2    VAR_MAP_LOCAL_1


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
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfBadgeAcquired BADGE_ID_COAL, OreburghGym_AlreadyHaveCoalBadge
    CreateJournalEvent LOCATION_EVENT_GYM_WAS_TOO_TOUGH, 47, 0, 0, 0
    Message OreburghGym_Text_RoarkIntro
    CloseMessage
    StartTrainerBattle TRAINER_LEADER_ROARK
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, OreburghGym_LostBattle
    Message OreburghGym_Text_BeatRoark
    BufferPlayerName 0
    Message OreburghGym_Text_RoarkReceiveCoalBadge
    PlaySound SEQ_BADGE
    WaitSound
    SetTrainerFlag TRAINER_YOUNGSTER_JONATHON
    SetTrainerFlag TRAINER_YOUNGSTER_DARIUS
    GiveBadge BADGE_ID_COAL
    IncrementTrainerScore2 TRAINER_SCORE_EVENT_BADGE_EARNED
    SetTrainerFlag TRAINER_YOUNGSTER_JONATHON
    SetTrainerFlag TRAINER_YOUNGSTER_DARIUS
    SetFlag FLAG_HIDE_BLOCK_POKECENTER_BASEMENT
    SetVar VAR_GTS_HAS_BADGES_CHECK_TEST, TRUE
    SetVar VAR_OREBURGH_STATE, 2
    // Arc 1: 15 = Coal Badge won; the Oreburgh City frame script runs the mine rift scene on leaving.
    // The stock Pal Pad Looker (VAR_JUBILIFE_LOOKER_PALPAD) and Jubilife Galactic tag battle
    // (VAR_JUBILIFE_STATE 3 and the FLAG_HIDE_JUBILIFE_* clears) are gone in Arc 1.
    SetVar VAR_ARC1_PROGRESS, 15
    CreateJournalEvent LOCATION_EVENT_BEAT_GYM_LEADER, 47, TRAINER_LEADER_ROARK, 0, 0
    SetFlag FLAG_UNK_0x0198
    // Puzzle: clear the rock chutes (off screen from the dais) so the way out is open.
    Call OreburghGym_ClearRubble
    Message OreburghGym_Text_RoarkExplainCoalBadge
    GoTo OreburghGym_RoarkGiveTM76
    End

OreburghGym_RoarkGiveTM76:
    SetVar VAR_0x8004, ITEM_TM76
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, OreburghGym_RoarkGiveTM76BagFull
    GiveItemQuantity
    SetFlag FLAG_OBTAINED_ROARK_TM76
    BufferItemName 0, VAR_0x8004
    BufferTMHMMoveName 1, VAR_0x8004
    Message OreburghGym_Text_RoarkExplainStealthRock
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghGym_RoarkGiveTM76BagFull:
    MessageBagIsFull
    CloseMessage
    ReleaseAll
    End

OreburghGym_AlreadyHaveCoalBadge:
    GoToIfUnset FLAG_OBTAINED_ROARK_TM76, OreburghGym_RoarkGiveTM76
    Message OreburghGym_Text_RoarkGymBeaten
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghGym_LostBattle:
    BlackOutFromBattle
    ReleaseAll
    End

OreburghGym_GymGuide:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfBadgeAcquired BADGE_ID_COAL, OreburghGym_GymGuideAfterBadge
    Message OreburghGym_Text_GymGuideBeforeBadge
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghGym_GymGuideAfterBadge:
    BufferPlayerName 0
    Message OreburghGym_Text_GymGuideAfterBadge
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghGym_GymStatue:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfBadgeAcquired BADGE_ID_COAL, OreburghGym_GymStatueAfterBadge
    BufferRivalName 0
    BufferRivalName 1
    Message OreburghGym_Text_GymStatueBeforeBadge
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghGym_GymStatueAfterBadge:
    BufferRivalName 0
    BufferPlayerName 1
    BufferRivalName 2
    Message OreburghGym_Text_GymStatueAfterBadge
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// ---------------------------------------------------------------------------------------------------------
// Rock-slide puzzle

OreburghGym_Init:
    // a saved var, not VAR_RESULT: the special vars aren't safe on every map-load path
    CheckBadgeAcquired BADGE_ID_COAL, VAR_MAP_LOCAL_2
    GoToIfEq VAR_MAP_LOCAL_2, TRUE, OreburghGym_InitCleared
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
    PlayFanfare SEQ_SE_CONFIRM
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
    PlayFanfare SEQ_SE_CONFIRM
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
    PlayFanfare SEQ_SE_DP_KI_GASYAN
    WaitFanfare SEQ_SE_DP_KI_GASYAN
    Return

OreburghGym_RockfallFx:
    PlayFanfare SEQ_SE_DP_WALL_HIT2
    ShakeCamera 16, 3
    Return

OreburghGym_WinchJam:
    Message OreburghGym_Text_WinchJammed
    GoTo OreburghGym_WinchDone
    End

OreburghGym_WinchDone:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghGym_WinchCancel:
    CloseMessage
    ReleaseAll
    End

OreburghGym_WinchIdle:
    Message OreburghGym_Text_WinchIdle
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghGym_Rubble:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message OreburghGym_Text_Rubble
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghGym_LooseRock:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message OreburghGym_Text_LooseRock
    WaitABXPadPress
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
