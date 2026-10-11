#include "macros/scrcmd.inc"
#include "res/text/bank/pastoria_city_gym.h"

// Arc 2 polish-c (critic #9): Wake gives the Gyaradosite after Gym 4.
//   Flag: FLAG_UNK_0x053E = FLAG_ARC2_GOT_GYARADOSITE (a Route 206 Mega Stone test-ball flag freed by 9a33d828c6)
#define FLAG_ARC2_GOT_GYARADOSITE FLAG_UNK_0x053E


    ScriptEntry PastoriaGym_Init
    ScriptEntry PastoriaGym_BlueButton
    ScriptEntry PastoriaGym_GreenButton
    ScriptEntry PastoriaGym_YellowButton
    ScriptEntry PastoriaGym_Wake
    ScriptEntry PastoriaGym_GymGuide
    ScriptEntry PastoriaGym_GymStatue
    ScriptEntryEnd

PastoriaGym_Init:
    SetVar VAR_MAP_LOCAL_1, 0
    SetVar VAR_MAP_LOCAL_2, 1
    SetVar VAR_MAP_LOCAL_3, 0
    InitPersistedMapFeaturesForPastoriaGym
    End

PastoriaGym_BlueButton:
    PressPastoriaGymButton
    SetVar VAR_MAP_LOCAL_1, 1
    SetVar VAR_MAP_LOCAL_2, 0
    SetVar VAR_MAP_LOCAL_3, 0
    End

PastoriaGym_GreenButton:
    PressPastoriaGymButton
    SetVar VAR_MAP_LOCAL_1, 0
    SetVar VAR_MAP_LOCAL_2, 1
    SetVar VAR_MAP_LOCAL_3, 0
    End

PastoriaGym_YellowButton:
    PressPastoriaGymButton
    SetVar VAR_MAP_LOCAL_1, 0
    SetVar VAR_MAP_LOCAL_2, 0
    SetVar VAR_MAP_LOCAL_3, 1
    End

PastoriaGym_Wake:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfBadgeAcquired BADGE_ID_FEN, PastoriaGym_WakeAlreadyHaveFenBadge
    CreateJournalEvent LOCATION_EVENT_GYM_WAS_TOO_TOUGH, 122, 0, 0, 0
    Message PastoriaGym_Text_WakeIntro
    CloseMessage
    StartTrainerBattle TRAINER_LEADER_WAKE
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, PastoriaGym_LostBattle
    Message PastoriaGym_Text_BeatWake
    BufferPlayerName 0
    Message PastoriaGym_Text_WakeReveiveFenBadge
    PlaySound SEQ_BADGE
    WaitSound
    GiveBadge BADGE_ID_FEN
    IncrementTrainerScore2 TRAINER_SCORE_EVENT_BADGE_EARNED
    SetTrainerFlag TRAINER_FISHERMAN_ERICK
    SetTrainerFlag TRAINER_SAILOR_DAMIAN
    SetTrainerFlag TRAINER_FISHERMAN_WALTER
    SetTrainerFlag TRAINER_SAILOR_SAMSON
    SetTrainerFlag TRAINER_TUBER_JACKY
    SetTrainerFlag TRAINER_TUBER_CAITLYN
    // Arc 2 (s-pastoria): the stock Wake/Barry/grunt scene after the badge (VAR_PASTORIA_STATE 3) is cut
    SetFlag FLAG_UNK_0x020C
    SetFlag FLAG_UNK_0x0156
    CreateJournalEvent LOCATION_EVENT_BEAT_GYM_LEADER, 122, TRAINER_LEADER_WAKE, 0, 0
    Message PastoriaGym_Text_WakeExplainFenBadge
    GoTo PastoriaGym_WakeTryGiveTm55
    End

PastoriaGym_WakeTryGiveTm55:
    SetVar VAR_0x8004, ITEM_TM55
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, PastoriaGym_WakeCannotGiveTm55
    GiveItemQuantity
    SetFlag FLAG_OBTAINED_WAKE_TM55
    BufferItemName 0, VAR_0x8004
    BufferTMHMMoveName 1, VAR_0x8004
    Message PastoriaGym_Text_WakeExplainTM55
    WaitABXPadPress
    Call PastoriaGym_Arc2TryGiveGyaradosite
    GoTo PastoriaGym_Arc2WakeRoute213
    End

PastoriaGym_WakeCannotGiveTm55:
    MessageBagIsFull
    Call PastoriaGym_Arc2TryGiveGyaradosite
    GoTo PastoriaGym_Arc2WakeRoute213
    End

// Arc 2 polish-c: the Gyaradosite, once (FLAG_ARC2_GOT_GYARADOSITE). Leaves the message box open.
PastoriaGym_Arc2TryGiveGyaradosite:
    GoToIfSet FLAG_ARC2_GOT_GYARADOSITE, PastoriaGym_Arc2GyaradositeEnd
    Message PastoriaGym_Text_Arc2WakeGyaradosite
    SetVar VAR_0x8004, ITEM_GYARADOSITE
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, PastoriaGym_Arc2GyaradositeFull
    GiveItemQuantity
    SetFlag FLAG_ARC2_GOT_GYARADOSITE
    Message PastoriaGym_Text_Arc2WakeGyaradositeBond
    WaitABXPadPress
PastoriaGym_Arc2GyaradositeEnd:
    Return

PastoriaGym_Arc2GyaradositeFull:
    MessageBagIsFull
    Return

// Arc 2 (s-pastoria), 2.20: Wake points at Route 213 after the badge. Sets VAR_ARC2_PROGRESS 71 (Fen Badge) when
// the arc has reached Pastoria (69-70); an early badge is picked up by Pastoria City's OnTransition instead.
PastoriaGym_Arc2WakeRoute213:
    Message PastoriaGym_Text_Arc2WakeRoute213
    WaitABXPadPress
    CloseMessage
    GoToIfLt VAR_ARC2_PROGRESS, 69, PastoriaGym_Arc2WakeEnd
    GoToIfGe VAR_ARC2_PROGRESS, 71, PastoriaGym_Arc2WakeEnd
    SetVar VAR_ARC2_PROGRESS, 71
PastoriaGym_Arc2WakeEnd:
    ReleaseAll
    End

PastoriaGym_WakeAlreadyHaveFenBadge:
    GoToIfUnset FLAG_OBTAINED_WAKE_TM55, PastoriaGym_WakeTryGiveTm55
    Call PastoriaGym_Arc2TryGiveGyaradosite
    Message PastoriaGym_Text_WakeAfterbadge
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

PastoriaGym_LostBattle:
    BlackOutFromBattle
    ReleaseAll
    End

PastoriaGym_GymGuide:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfBadgeAcquired BADGE_ID_FEN, PastoriaGym_GymGuideAfterBadge
    Message PastoriaGym_Text_GymGuideBeforebadge
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

PastoriaGym_GymGuideAfterBadge:
    BufferPlayerName 0
    Message PastoriaGym_Text_GymGuideAfterbadge
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

PastoriaGym_GymStatue:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfBadgeAcquired BADGE_ID_FEN, PastoriaGym_GymStatueAfterBadge
    BufferRivalName 0
    BufferRivalName 1
    Message PastoriaGym_Text_GymStatueBeforeBadge
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

PastoriaGym_GymStatueAfterBadge:
    BufferRivalName 0
    BufferPlayerName 1
    BufferRivalName 2
    Message PastoriaGym_Text_GymStatueAfterBadge
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
