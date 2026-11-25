#include "macros/scrcmd.inc"
#include "res/text/bank/solaceon_ruins_room_2_northeast_dead_end.h"
#include "res/field/maps/locals/solaceon_ruins_room_2_northeast_dead_end.h"

// Solaceon raid, generator A (Room 2 northeast dead end; screenplay.md scene 3.4a part 4, raid_maps.md "The generators").
// The "on" generator and its lit rack hide with FLAG_SOL_RAID_A; the "off" twins on the same tiles hide with the
// map-local FLAG_MAP_LOCAL_HIDE_OBSTACLE_16, which OnTransition clears only while the generator is off and the
// raid is not over (progress <= 49). Progress 31-33 counts the generators that are off, in any order; the third
// one drops the barrier in Room 7 (FLAG_SOL_RAID_D).

    ScriptEntry SolaceonRuinsRoom2NortheastDeadEnd_OnTransition
    ScriptEntry SolaceonRuinsRoom2NortheastDeadEnd_Generator
    ScriptEntryEnd

SolaceonRuinsRoom2NortheastDeadEnd_OnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    GoToIfGe VAR_SOLACEON_PROGRESS, 50, SolaceonRuinsRoom2NortheastDeadEnd_OnTransitionEnd
    GoToIfUnset FLAG_SOL_RAID_A, SolaceonRuinsRoom2NortheastDeadEnd_OnTransitionEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
SolaceonRuinsRoom2NortheastDeadEnd_OnTransitionEnd:
    End

// The generator and its rack (both carry this script)
SolaceonRuinsRoom2NortheastDeadEnd_Generator:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfSet FLAG_SOL_RAID_A, SolaceonRuinsRoom2NortheastDeadEnd_GeneratorIsOff
    GoToIfLt VAR_SOLACEON_PROGRESS, 30, SolaceonRuinsRoom2NortheastDeadEnd_GeneratorIsOff
    GoToIfGe VAR_SOLACEON_PROGRESS, 40, SolaceonRuinsRoom2NortheastDeadEnd_GeneratorIsOff
    Message SolaceonRuinsRoom2NortheastDeadEnd_Text_GeneratorOn
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, SolaceonRuinsRoom2NortheastDeadEnd_GeneratorKeepOn
    BufferPlayerName 0
    SetFlag FLAG_SOL_RAID_A
    PlaySE SEQ_SE_DP_PC_LOGOFF_sseq
    RemoveObject LOCALID_GEN_A_ON
    RemoveObject LOCALID_GEN_A_RACK_ON
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    AddObject LOCALID_GEN_A_OFF
    AddObject LOCALID_GEN_A_RACK_OFF
    WaitSE SEQ_SE_DP_PC_LOGOFF_sseq
    Message SolaceonRuinsRoom2NortheastDeadEnd_Text_GeneratorSwitchedOff
    WaitABPadPress
    CloseMessage
    // 30 + the number of generators that are off (the order is free)
    SetVar VAR_SOLACEON_PROGRESS, 30
    CallIfSet FLAG_SOL_RAID_A, SolaceonRuinsRoom2NortheastDeadEnd_CountOne
    CallIfSet FLAG_SOL_RAID_B, SolaceonRuinsRoom2NortheastDeadEnd_CountOne
    CallIfSet FLAG_SOL_RAID_C, SolaceonRuinsRoom2NortheastDeadEnd_CountOne
    CallIfEq VAR_SOLACEON_PROGRESS, 33, SolaceonRuinsRoom2NortheastDeadEnd_DropBarrier
    PlaySE SEQ_SE_DP_BEEP_sseq
    WaitSE SEQ_SE_DP_BEEP_sseq
    PlaySE SEQ_SE_DP_BEEP_sseq
    WaitSE SEQ_SE_DP_BEEP_sseq
    Message SolaceonRuinsRoom2NortheastDeadEnd_Text_PoketchBuzzes
    WaitABPadPress
    GoToIfEq VAR_SOLACEON_PROGRESS, 31, SolaceonRuinsRoom2NortheastDeadEnd_Ruth31
    GoToIfEq VAR_SOLACEON_PROGRESS, 32, SolaceonRuinsRoom2NortheastDeadEnd_Ruth32
    Message SolaceonRuinsRoom2NortheastDeadEnd_Text_Ruth33
    GoTo SolaceonRuinsRoom2NortheastDeadEnd_RuthDone
    End

SolaceonRuinsRoom2NortheastDeadEnd_Ruth31:
    Message SolaceonRuinsRoom2NortheastDeadEnd_Text_Ruth31
    GoTo SolaceonRuinsRoom2NortheastDeadEnd_RuthDone
    End

SolaceonRuinsRoom2NortheastDeadEnd_Ruth32:
    Message SolaceonRuinsRoom2NortheastDeadEnd_Text_Ruth32
    GoTo SolaceonRuinsRoom2NortheastDeadEnd_RuthDone
    End

SolaceonRuinsRoom2NortheastDeadEnd_RuthDone:
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom2NortheastDeadEnd_CountOne:
    AddVar VAR_SOLACEON_PROGRESS, 1
    Return

SolaceonRuinsRoom2NortheastDeadEnd_DropBarrier:
    SetFlag FLAG_SOL_RAID_D
    Return

SolaceonRuinsRoom2NortheastDeadEnd_GeneratorKeepOn:
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom2NortheastDeadEnd_GeneratorIsOff:
    Message SolaceonRuinsRoom2NortheastDeadEnd_Text_GeneratorOff
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End
