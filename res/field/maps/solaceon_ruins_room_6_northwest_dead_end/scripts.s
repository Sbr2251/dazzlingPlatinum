#include "macros/scrcmd.inc"
#include "res/text/bank/solaceon_ruins_room_6_northwest_dead_end.h"
#include "res/field/maps/locals/solaceon_ruins_room_6_northwest_dead_end.h"

// Solaceon raid, generator C (Room 6 northwest dead end; screenplay.md scene 3.4a part 4, raid_maps.md "The generators").
// The "on" generator and its lit rack hide with FLAG_SOL_RAID_C; the "off" twins on the same tiles hide with the
// map-local FLAG_MAP_LOCAL_HIDE_OBSTACLE_16, which OnTransition clears only while the generator is off and the
// raid is not over (progress <= 49). Progress 31-33 counts the generators that are off, in any order; the third
// one drops the barrier in Room 7 (FLAG_SOL_RAID_D).

    ScriptEntry SolaceonRuinsRoom6NorthwestDeadEnd_OnTransition
    ScriptEntry SolaceonRuinsRoom6NorthwestDeadEnd_Generator
    ScriptEntryEnd

SolaceonRuinsRoom6NorthwestDeadEnd_OnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    GoToIfGe VAR_SOLACEON_PROGRESS, 50, SolaceonRuinsRoom6NorthwestDeadEnd_OnTransitionEnd
    GoToIfUnset FLAG_SOL_RAID_C, SolaceonRuinsRoom6NorthwestDeadEnd_OnTransitionEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
SolaceonRuinsRoom6NorthwestDeadEnd_OnTransitionEnd:
    End

// The generator and its rack (both carry this script)
SolaceonRuinsRoom6NorthwestDeadEnd_Generator:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfSet FLAG_SOL_RAID_C, SolaceonRuinsRoom6NorthwestDeadEnd_GeneratorIsOff
    GoToIfLt VAR_SOLACEON_PROGRESS, 30, SolaceonRuinsRoom6NorthwestDeadEnd_GeneratorIsOff
    GoToIfGe VAR_SOLACEON_PROGRESS, 40, SolaceonRuinsRoom6NorthwestDeadEnd_GeneratorIsOff
    Message SolaceonRuinsRoom6NorthwestDeadEnd_Text_GeneratorOn
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, SolaceonRuinsRoom6NorthwestDeadEnd_GeneratorKeepOn
    BufferPlayerName 0
    SetFlag FLAG_SOL_RAID_C
    PlaySE SEQ_SE_DP_PC_LOGOFF_sseq
    RemoveObject LOCALID_GEN_C_ON
    RemoveObject LOCALID_GEN_C_RACK_ON
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    AddObject LOCALID_GEN_C_OFF
    AddObject LOCALID_GEN_C_RACK_OFF
    WaitSE SEQ_SE_DP_PC_LOGOFF_sseq
    Message SolaceonRuinsRoom6NorthwestDeadEnd_Text_GeneratorSwitchedOff
    WaitABPadPress
    CloseMessage
    // 30 + the number of generators that are off (the order is free)
    SetVar VAR_SOLACEON_PROGRESS, 30
    CallIfSet FLAG_SOL_RAID_A, SolaceonRuinsRoom6NorthwestDeadEnd_CountOne
    CallIfSet FLAG_SOL_RAID_B, SolaceonRuinsRoom6NorthwestDeadEnd_CountOne
    CallIfSet FLAG_SOL_RAID_C, SolaceonRuinsRoom6NorthwestDeadEnd_CountOne
    CallIfEq VAR_SOLACEON_PROGRESS, 33, SolaceonRuinsRoom6NorthwestDeadEnd_DropBarrier
    PlaySE SEQ_SE_DP_BEEP_sseq
    WaitSE SEQ_SE_DP_BEEP_sseq
    PlaySE SEQ_SE_DP_BEEP_sseq
    WaitSE SEQ_SE_DP_BEEP_sseq
    Message SolaceonRuinsRoom6NorthwestDeadEnd_Text_PoketchBuzzes
    WaitABPadPress
    GoToIfEq VAR_SOLACEON_PROGRESS, 31, SolaceonRuinsRoom6NorthwestDeadEnd_Ruth31
    GoToIfEq VAR_SOLACEON_PROGRESS, 32, SolaceonRuinsRoom6NorthwestDeadEnd_Ruth32
    Message SolaceonRuinsRoom6NorthwestDeadEnd_Text_Ruth33
    GoTo SolaceonRuinsRoom6NorthwestDeadEnd_RuthDone
    End

SolaceonRuinsRoom6NorthwestDeadEnd_Ruth31:
    Message SolaceonRuinsRoom6NorthwestDeadEnd_Text_Ruth31
    GoTo SolaceonRuinsRoom6NorthwestDeadEnd_RuthDone
    End

SolaceonRuinsRoom6NorthwestDeadEnd_Ruth32:
    Message SolaceonRuinsRoom6NorthwestDeadEnd_Text_Ruth32
    GoTo SolaceonRuinsRoom6NorthwestDeadEnd_RuthDone
    End

SolaceonRuinsRoom6NorthwestDeadEnd_RuthDone:
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom6NorthwestDeadEnd_CountOne:
    AddVar VAR_SOLACEON_PROGRESS, 1
    Return

SolaceonRuinsRoom6NorthwestDeadEnd_DropBarrier:
    SetFlag FLAG_SOL_RAID_D
    Return

SolaceonRuinsRoom6NorthwestDeadEnd_GeneratorKeepOn:
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom6NorthwestDeadEnd_GeneratorIsOff:
    Message SolaceonRuinsRoom6NorthwestDeadEnd_Text_GeneratorOff
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End
