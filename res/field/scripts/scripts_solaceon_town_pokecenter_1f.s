#include "macros/scrcmd.inc"
#include "res/text/bank/solaceon_town_pokecenter_1f.h"

// Arc 2 quests (R3, S10): the old man (local 1) saw Rowan's interview: from VAR_ARC2_PROGRESS 44 he talks about
// it, and from 86 about the retraction. His stock Day-Care line stays before 44 and from 100.


    ScriptEntry _0012
    ScriptEntry _001E
    ScriptEntry _0031
    ScriptEntry _0044
    ScriptEntryEnd

_0012:
    CallPokecenterNurse 0
    End

_001E:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfGe VAR_ARC2_PROGRESS, 44, SolaceonTownPokecenter1F_QuestsOldManTV
SolaceonTownPokecenter1F_OldManStock:
    Message 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0031:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0044:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 2
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0

SolaceonTownPokecenter1F_QuestsOldManTV:
    GoToIfGe VAR_ARC2_PROGRESS, 100, SolaceonTownPokecenter1F_OldManStock
    GoToIfGe VAR_ARC2_PROGRESS, 86, SolaceonTownPokecenter1F_QuestsOldManRetraction
    Message SolaceonTownPokecenter1F_Text_QuestsOldManSawRowan
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonTownPokecenter1F_QuestsOldManRetraction:
    Message SolaceonTownPokecenter1F_Text_QuestsOldManRetraction
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End
