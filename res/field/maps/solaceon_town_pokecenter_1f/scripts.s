#include "macros/scrcmd.inc"
#include "res/text/bank/solaceon_town_pokecenter_1f.h"
#include "res/field/maps/locals/solaceon_town_pokecenter_1f.h"

// Arc 2 quests (R3, S10): the old man (local 1) saw Rowan's interview: from VAR_ARC2_PROGRESS 44 he talks about
// it, and from 86 about the retraction. His stock Day-Care line stays before 44 and from 100.


    ScriptEntry SolaceonTownPokecenter1F_Nurse
    ScriptEntry SolaceonTownPokecenter1F_OldMan
    ScriptEntry SolaceonTownPokecenter1F_Lass
    ScriptEntry SolaceonTownPokecenter1F_RuinManiac
    ScriptEntryEnd

SolaceonTownPokecenter1F_Nurse:
    SetVar VAR_0x8007, LOCALID_SOLACEON_NURSE
    CallCommonScript CommonScript_PokecenterNurse
    End

SolaceonTownPokecenter1F_OldMan:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfGe VAR_ARC2_PROGRESS, 44, SolaceonTownPokecenter1F_QuestsOldManTV
SolaceonTownPokecenter1F_OldManStock:
    Message SolaceonTownPokecenter1F_Text_PokemonGrowAtDifferentRates
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonTownPokecenter1F_Lass:
    NPCMessage SolaceonTownPokecenter1F_Text_QuiteFarToVeilstoneCity
    End

SolaceonTownPokecenter1F_RuinManiac:
    NPCMessage SolaceonTownPokecenter1F_Text_HMDefogIsInTheRuins
    End

    .balign 4, 0

SolaceonTownPokecenter1F_QuestsOldManTV:
    GoToIfGe VAR_ARC2_PROGRESS, 100, SolaceonTownPokecenter1F_OldManStock
    GoToIfGe VAR_ARC2_PROGRESS, 86, SolaceonTownPokecenter1F_QuestsOldManRetraction
    Message SolaceonTownPokecenter1F_Text_QuestsOldManSawRowan
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonTownPokecenter1F_QuestsOldManRetraction:
    Message SolaceonTownPokecenter1F_Text_QuestsOldManRetraction
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End
