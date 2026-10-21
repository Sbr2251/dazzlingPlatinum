#include "macros/scrcmd.inc"
#include "res/text/bank/team_galactic_eterna_building_2f.h"
#include "res/field/events/events_team_galactic_eterna_building_2f.h"

// Dazzling Platinum Arc 2 (s-eterna, screenplay 2.12): Eclipse Haven 2F, the kennels. Every kennel is empty.
// Gardenia and Ruth wait past the first three kennels at VAR_ARC2_PROGRESS 34 (until the 3F battle is won);
// walking past them runs Gardenia's line once (FLAG_ARC2_ETERNA_B (0x093F)).
// Map-local: hide flags 0x30 Gardenia, 0x31 Ruth; VAR_MAP_LOCAL_0 = 0 arms the kennel coord.
// Arc 2 quests (R3, S11): Duchess. From VAR_ARC2_PROGRESS 35 (the Haven shut) a Clefairy, Duchess, sits in front
// of her kennel (20,12) until the player takes her (FLAG_UNK_0x0921 = FLAG_ARC2_LEAD_B, lead's block); the old man
// in Jubilife (scripts_jubilife_city.s) takes her home. Map-local hide flag: 0x32 Duchess.
#define FLAG_QUESTS_DUCHESS_CARRIED FLAG_ARC2_LEAD_B
#define LOCALID_QUESTS_DUCHESS HAVEN_2F_QUESTS_DUCHESS

    ScriptEntry Haven2F_Gardenia
    ScriptEntry Haven2F_Ruth
    ScriptEntry Haven2F_Sign
    ScriptEntry Haven2F_KennelBramble
    ScriptEntry Haven2F_KennelPip
    ScriptEntry Haven2F_KennelClover
    ScriptEntry Haven2F_KennelDuchess
    ScriptEntry Haven2F_KennelEmpty
    ScriptEntry Haven2F_KennelScene
    ScriptEntry Haven2F_OnTransition
    ScriptEntry Haven2F_QuestsDuchess
    ScriptEntryEnd

Haven2F_OnTransition:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (Arc 1 D1) */
    Call Haven2F_QuestsOnTransition
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    SetVar VAR_MAP_LOCAL_0, 1
    GoToIfNe VAR_ARC2_PROGRESS, 34, Haven2F_OnTransitionEnd
    GoToIfSet FLAG_ARC2_ETERNA_A, Haven2F_OnTransitionEnd
    ClearFlag FLAG_UNK_0x0030
    ClearFlag FLAG_UNK_0x0031
    GoToIfSet FLAG_ARC2_ETERNA_B, Haven2F_OnTransitionEnd
    SetVar VAR_MAP_LOCAL_0, 0
Haven2F_OnTransitionEnd:
    End

Haven2F_Gardenia:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message Haven2F_Text_GardeniaTalk
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Haven2F_Ruth:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message Haven2F_Text_RuthTalk
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Haven2F_Sign:
    SetVar VAR_0x8004, Haven2F_Text_Sign
    GoTo Haven2F_ShowSign

Haven2F_KennelBramble:
    SetVar VAR_0x8004, Haven2F_Text_KennelBramble
    GoTo Haven2F_ShowSign

Haven2F_KennelPip:
    SetVar VAR_0x8004, Haven2F_Text_KennelPip
    GoTo Haven2F_ShowSign

Haven2F_KennelClover:
    SetVar VAR_0x8004, Haven2F_Text_KennelClover
    GoTo Haven2F_ShowSign

Haven2F_KennelDuchess:
    SetVar VAR_0x8004, Haven2F_Text_KennelDuchess
    GoTo Haven2F_ShowSign

Haven2F_KennelEmpty:
    SetVar VAR_0x8004, Haven2F_Text_KennelEmpty
    GoTo Haven2F_ShowSign

Haven2F_ShowSign:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    MessageVar VAR_0x8004
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// The player steps onto (13,12), past BRAMBLE, PIP and CLOVER. Gardenia (14,11) steps down beside them.
Haven2F_KennelScene:
    LockAll
    ApplyMovement HAVEN_2F_GARDENIA, Haven2F_Movement_GardeniaStepDown
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Haven2F_Movement_FaceEast
    WaitMovement
    Message Haven2F_Text_GardeniaTheseAreMine
    WaitABXPadPress
    CloseMessage
    ApplyMovement HAVEN_2F_GARDENIA, Haven2F_Movement_GardeniaStepBack
    WaitMovement
    SetFlag FLAG_ARC2_ETERNA_B
    SetVar VAR_MAP_LOCAL_0, 1
    ReleaseAll
    End

    .balign 4, 0
Haven2F_Movement_GardeniaStepDown:
    WalkNormalSouth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
Haven2F_Movement_GardeniaStepBack:
    WalkNormalNorth
    FaceSouth
    EndMovement

    .balign 4, 0
Haven2F_Movement_FaceEast:
    WalkOnSpotNormalEast
    EndMovement

Haven2F_QuestsOnTransition:
    SetFlag FLAG_UNK_0x0032
    GoToIfLt VAR_ARC2_PROGRESS, 35, Haven2F_QuestsReturn
    GoToIfSet FLAG_QUESTS_DUCHESS_CARRIED, Haven2F_QuestsReturn
    ClearFlag FLAG_UNK_0x0032
Haven2F_QuestsReturn:
    Return

Haven2F_QuestsDuchess:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message Haven2F_Text_QuestsDuchessCurled
    WaitABXPadPress
    PlayCry SPECIES_CLEFAIRY
    Message Haven2F_Text_QuestsDuchessCry
    WaitCry
    WaitABXPadPress
    Message Haven2F_Text_QuestsDuchessLakeValor
    WaitABXPadPress
    Message Haven2F_Text_QuestsTakeDuchess
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, Haven2F_QuestsDuchessStays
    SetFlag FLAG_QUESTS_DUCHESS_CARRIED
    Message Haven2F_Text_QuestsDuchessFollows
    WaitABXPadPress
    CloseMessage
    RemoveObject LOCALID_QUESTS_DUCHESS
    SetFlag FLAG_UNK_0x0032
    ReleaseAll
    End

Haven2F_QuestsDuchessStays:
    Message Haven2F_Text_QuestsDuchessStays
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End
