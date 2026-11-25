#include "macros/scrcmd.inc"
#include "res/text/bank/solaceon_sanctuary.h"
#include "res/field/maps/locals/solaceon_sanctuary.h"

// MAP_HEADER_SOLACEON_SANCTUARY, the Sanctuary hall (town-scripts; screenplay.md Part 3, docs/solaceon_redesign/
// scripts.md). Tiles, NPC spots and sign tiles: tools/solaceon_town/interior/layout.py and interior.md.
// The band is picked as in Solaceon Town (SolaceonSanctuary_GetBand -> VAR_MAP_LOCAL_0x04):
//   A  VAR_ARC2_PROGRESS < 54    B  54-85    C  86-98    D  99 and VAR_SOLACEON_PROGRESS < 20 (shut: nobody inside;
//   the town door is locked, so the hall is exit-only)    R  20-49 (Looker in the office until 40)    E  50 (seized)
//   F  FLAG_GAME_COMPLETED.
// Map-local hide flags: HIDE_OBSTACLE_1 speaker  2 hall attendant  3 testimony A (and the last believer, E)
//   4 testimony B  5 testimony C  6 records clerk (the reading keeper, F)  7 hall grunt (stands on the office doorway
//   (19,13): the office is shut in B and C)  8 back door grunt  9 Looker  10/11 IP officers hall/office.

    ScriptEntry SolaceonSanctuary_OnTransition
    ScriptEntry SolaceonSanctuary_Speaker
    ScriptEntry SolaceonSanctuary_HallAttendant
    ScriptEntry SolaceonSanctuary_TestimonyA
    ScriptEntry SolaceonSanctuary_TestimonyB
    ScriptEntry SolaceonSanctuary_TestimonyC
    ScriptEntry SolaceonSanctuary_RecordsClerk
    ScriptEntry SolaceonSanctuary_HallGrunt
    ScriptEntry SolaceonSanctuary_BackDoorGrunt
    ScriptEntry SolaceonSanctuary_Looker
    ScriptEntry SolaceonSanctuary_IpOfficerHall
    ScriptEntry SolaceonSanctuary_IpOfficerOffice
    ScriptEntry SolaceonSanctuary_Lectern
    ScriptEntry SolaceonSanctuary_NoticeBoard
    ScriptEntry SolaceonSanctuary_FilingDrawers
    ScriptEntry SolaceonSanctuary_Ledger
    ScriptEntry SolaceonSanctuary_IndrasDesk
    ScriptEntry SolaceonSanctuary_BackDoor
    ScriptEntryEnd

#define BAND_A 1
#define BAND_B 2
#define BAND_C 3
#define BAND_D 4
#define BAND_R 5
#define BAND_E 6
#define BAND_F 7

SolaceonSanctuary_OnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_1
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_2
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_3
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_4
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_5
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_6
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_7
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_8
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_9
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_10
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_11
    Call SolaceonSanctuary_GetBand
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_A, SolaceonSanctuary_ShowA
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonSanctuary_ShowB
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonSanctuary_ShowC
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonSanctuary_ShowR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonSanctuary_ShowE
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonSanctuary_ShowF
    End

// A: the speaker at the lectern, the attendant by the door, three testimonies on the benches, the clerk in the office.
SolaceonSanctuary_ShowA:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_1
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_2
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_3
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_4
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_5
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_6
    End

// B: a grunt on the office doorway (the office is shut; the clerk is inside, unreachable), one at the back door.
SolaceonSanctuary_ShowB:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_1
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_3
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_5
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_6
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_7
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_8
    End

// C: testimony A gone; testimony B back, on her feet near the door, about to leave.
SolaceonSanctuary_ShowC:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_1
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_4
    SetObjectEventPos LOCALID_TESTIMONY_B, 12, 18
    SetObjectEventDir LOCALID_TESTIMONY_B, DIR_SOUTH
    SetObjectEventMovementType LOCALID_TESTIMONY_B, MOVEMENT_TYPE_LOOK_SOUTH
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_5
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_6
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_7
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_8
    End

// R: the hall is empty; Looker reads at Indra's desk until he goes down to the vault (40).
SolaceonSanctuary_ShowR:
    GoToIfGe VAR_SOLACEON_PROGRESS, 40, SolaceonSanctuary_ShowDone
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_9
    End

// E: the International Police; the last believer on the front bench (testimony A's man).
SolaceonSanctuary_ShowE:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_3
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_10
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_11
    End

// F: the reading keeper (the clerk) in the office; nobody at the lectern.
SolaceonSanctuary_ShowF:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_6
    SetObjectEventDir LOCALID_RECORDS_CLERK, DIR_SOUTH
    SetObjectEventMovementType LOCALID_RECORDS_CLERK, MOVEMENT_TYPE_LOOK_SOUTH
SolaceonSanctuary_ShowDone:
    End

SolaceonSanctuary_GetBand:
    SetVar VAR_MAP_LOCAL_0x04, BAND_F
    GoToIfSet FLAG_GAME_COMPLETED, SolaceonSanctuary_GetBandDone
    SetVar VAR_MAP_LOCAL_0x04, BAND_E
    GoToIfGe VAR_SOLACEON_PROGRESS, 50, SolaceonSanctuary_GetBandDone
    SetVar VAR_MAP_LOCAL_0x04, BAND_R
    GoToIfGe VAR_SOLACEON_PROGRESS, 20, SolaceonSanctuary_GetBandDone
    SetVar VAR_MAP_LOCAL_0x04, BAND_D
    GoToIfGe VAR_ARC2_PROGRESS, 99, SolaceonSanctuary_GetBandDone
    SetVar VAR_MAP_LOCAL_0x04, BAND_C
    GoToIfGe VAR_ARC2_PROGRESS, 86, SolaceonSanctuary_GetBandDone
    SetVar VAR_MAP_LOCAL_0x04, BAND_B
    GoToIfGe VAR_ARC2_PROGRESS, 54, SolaceonSanctuary_GetBandDone
    SetVar VAR_MAP_LOCAL_0x04, BAND_A
SolaceonSanctuary_GetBandDone:
    Return

SolaceonSanctuary_TalkStart:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Call SolaceonSanctuary_GetBand
    Return

SolaceonSanctuary_TalkEnd:
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonSanctuary_SignStart:
    LockAll
    Call SolaceonSanctuary_GetBand
    Return

SolaceonSanctuary_SignEnd:
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

// ------------------------------------------------------------------------------- people (screenplay Part 3)
SolaceonSanctuary_Speaker:
    Call SolaceonSanctuary_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonSanctuary_Speaker_B
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonSanctuary_Speaker_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonSanctuary_Speaker_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonSanctuary_Speaker_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonSanctuary_Speaker_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonSanctuary_Speaker_CDREF
SolaceonSanctuary_Speaker_A:
    Message SolaceonSanctuary_Text_SpeakerA
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_Speaker_B:
    Message SolaceonSanctuary_Text_SpeakerB
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_Speaker_CDREF:
    Message SolaceonSanctuary_Text_SpeakerC
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_HallAttendant:
    Call SolaceonSanctuary_TalkStart
SolaceonSanctuary_HallAttendant_ABCDREF:
    Message SolaceonSanctuary_Text_HallAttendantA
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_TestimonyA:
    Call SolaceonSanctuary_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonSanctuary_TestimonyA_BCDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonSanctuary_TestimonyA_BCDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonSanctuary_TestimonyA_BCDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonSanctuary_TestimonyA_BCDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonSanctuary_TestimonyA_EF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonSanctuary_TestimonyA_EF
SolaceonSanctuary_TestimonyA_A:
    Message SolaceonSanctuary_Text_TestimonyAA
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_TestimonyA_BCDR:
    Message SolaceonSanctuary_Text_TestimonyAB
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_TestimonyA_EF:
    Message SolaceonSanctuary_Text_LastBelieverE
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_TestimonyB:
    Call SolaceonSanctuary_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonSanctuary_TestimonyB_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonSanctuary_TestimonyB_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonSanctuary_TestimonyB_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonSanctuary_TestimonyB_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonSanctuary_TestimonyB_CDREF
SolaceonSanctuary_TestimonyB_AB:
    Message SolaceonSanctuary_Text_TestimonyBA
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_TestimonyB_CDREF:
    Message SolaceonSanctuary_Text_TestimonyBC
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_TestimonyC:
    Call SolaceonSanctuary_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonSanctuary_TestimonyC_B
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonSanctuary_TestimonyC_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonSanctuary_TestimonyC_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonSanctuary_TestimonyC_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonSanctuary_TestimonyC_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonSanctuary_TestimonyC_CDREF
SolaceonSanctuary_TestimonyC_A:
    Message SolaceonSanctuary_Text_TestimonyCA
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_TestimonyC_B:
    Message SolaceonSanctuary_Text_TestimonyCB
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_TestimonyC_CDREF:
    Message SolaceonSanctuary_Text_TestimonyCC
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_RecordsClerk:
    Call SolaceonSanctuary_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonSanctuary_RecordsClerk_F
SolaceonSanctuary_RecordsClerk_ABCDRE:
    Message SolaceonSanctuary_Text_RecordsClerkA
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_RecordsClerk_F:
    Message SolaceonSanctuary_Text_ReadingKeeperF
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_HallGrunt:
    Call SolaceonSanctuary_TalkStart
SolaceonSanctuary_HallGrunt_ABCDREF:
    Message SolaceonSanctuary_Text_HallGruntB
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_BackDoorGrunt:
    Call SolaceonSanctuary_TalkStart
SolaceonSanctuary_BackDoorGrunt_ABCDREF:
    Message SolaceonSanctuary_Text_BackDoorGruntB
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_Looker:
    Call SolaceonSanctuary_TalkStart
SolaceonSanctuary_Looker_ABCDREF:
    Message SolaceonSanctuary_Text_LookerR_1
    WaitABPadPress
    Message SolaceonSanctuary_Text_LookerR_2
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_IpOfficerHall:
    Call SolaceonSanctuary_TalkStart
SolaceonSanctuary_IpOfficerHall_ABCDREF:
    Message SolaceonSanctuary_Text_IpOfficerHallE
    GoTo SolaceonSanctuary_TalkEnd

SolaceonSanctuary_IpOfficerOffice:
    Call SolaceonSanctuary_TalkStart
SolaceonSanctuary_IpOfficerOffice_ABCDREF:
    Message SolaceonSanctuary_Text_IpOfficerOfficeE
    GoTo SolaceonSanctuary_TalkEnd

// ----------------------------------------------------------------- signs (screenplay Part 3; nearest earlier band)
// The lectern is a TABLE tile: with the speaker behind it (A-C) she is talked to from the front, so the lectern is
// also read from its sides. The ledger: in R, Looker is reading the records at the desk beside it.
SolaceonSanctuary_Lectern:
    Call SolaceonSanctuary_SignStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonSanctuary_Lectern_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonSanctuary_Lectern_F
SolaceonSanctuary_Lectern_ABCDR:
    Message SolaceonSanctuary_Text_LecternABC
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_Lectern_E:
    Message SolaceonSanctuary_Text_LecternE
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_Lectern_F:
    Message SolaceonSanctuary_Text_LecternF
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_NoticeBoard:
    Call SolaceonSanctuary_SignStart
SolaceonSanctuary_NoticeBoard_ABCDREF:
    Message SolaceonSanctuary_Text_NoticeBoardABC
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_FilingDrawers:
    Call SolaceonSanctuary_SignStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonSanctuary_FilingDrawers_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonSanctuary_FilingDrawers_F
SolaceonSanctuary_FilingDrawers_ABCDR:
    Message SolaceonSanctuary_Text_FilingDrawersA
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_FilingDrawers_E:
    Message SolaceonSanctuary_Text_FilingDrawersE
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_FilingDrawers_F:
    Message SolaceonSanctuary_Text_FilingDrawersF
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_Ledger:
    Call SolaceonSanctuary_SignStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonSanctuary_Ledger_R
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonSanctuary_Ledger_EF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonSanctuary_Ledger_EF
SolaceonSanctuary_Ledger_ABCD:
    Message SolaceonSanctuary_Text_TheLedgerA
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_Ledger_R:
    Message SolaceonSanctuary_Text_LookerR_1
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_Ledger_EF:
    Message SolaceonSanctuary_Text_IndrasDeskE
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_IndrasDesk:
    Call SolaceonSanctuary_SignStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonSanctuary_IndrasDesk_EF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonSanctuary_IndrasDesk_EF
SolaceonSanctuary_IndrasDesk_ABCDR:
    Message SolaceonSanctuary_Text_IndrasDeskA
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_IndrasDesk_EF:
    Message SolaceonSanctuary_Text_IndrasDeskE
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_BackDoor:
    Call SolaceonSanctuary_SignStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonSanctuary_BackDoor_BCDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonSanctuary_BackDoor_BCDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonSanctuary_BackDoor_BCDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonSanctuary_BackDoor_BCDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonSanctuary_BackDoor_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonSanctuary_BackDoor_F
SolaceonSanctuary_BackDoor_A:
    Message SolaceonSanctuary_Text_BackDoorA
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_BackDoor_BCDR:
    Message SolaceonSanctuary_Text_BackDoorBCDR
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_BackDoor_E:
    Message SolaceonSanctuary_Text_BackDoorE
    GoTo SolaceonSanctuary_SignEnd

SolaceonSanctuary_BackDoor_F:
    Message SolaceonSanctuary_Text_BackDoorF
    GoTo SolaceonSanctuary_SignEnd
