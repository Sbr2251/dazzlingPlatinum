#include "macros/scrcmd.inc"
#include "res/text/bank/team_galactic_eterna_building_3f.h"
#include "res/field/events/events_team_galactic_eterna_building_3f.h"

// Dazzling Platinum Arc 2 (s-eterna, screenplay 2.12): Eclipse Haven 3F, the office. Looker at the filing cabinet,
// the shipping manifests on the desk, then two caretakers block the door: double battle, the player and Gardenia
// (partner) against TRAINER_ECLIPSE_GRUNT_ARC2_03 + _04. Entering the office (coord, row 9) starts the scene,
// so the 4F stairs can't be reached before it. A loss blacks out; the scene re-arms on the next visit.
// Flags: FLAG_ARC2_ETERNA_A (0x093E) (caretakers beaten), FLAG_ARC2_ETERNA_C (0x0940) (manifests).
// Map-local: hide flags 0x30 Looker, 0x31 Gardenia, 0x32 Ruth, 0x33 caretakers; VAR_MAP_LOCAL_0 = 0 arms the coord.

    ScriptEntry Haven3F_Looker
    ScriptEntry Haven3F_FilingCabinet
    ScriptEntry Haven3F_Manifests
    ScriptEntry Haven3F_OfficeScene
    ScriptEntry Haven3F_OnTransition
    ScriptEntryEnd

Haven3F_OnTransition:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (Arc 1 D1) */
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    SetFlag FLAG_UNK_0x0032
    SetFlag FLAG_UNK_0x0033
    SetVar VAR_MAP_LOCAL_0, 1
    GoToIfNe VAR_ARC2_PROGRESS, 34, Haven3F_OnTransitionEnd
    GoToIfSet FLAG_ARC2_ETERNA_A, Haven3F_OnTransitionEnd
    ClearFlag FLAG_UNK_0x0030
    ClearFlag FLAG_UNK_0x0031
    ClearFlag FLAG_UNK_0x0032
    SetVar VAR_MAP_LOCAL_0, 0
Haven3F_OnTransitionEnd:
    End

Haven3F_Looker:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message Haven3F_Text_LookerTalk
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Haven3F_FilingCabinet:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message Haven3F_Text_FilingCabinet
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Haven3F_Manifests:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message Haven3F_Text_Manifests
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// The player steps onto row 9 (x 12-14), the office doorway.
Haven3F_OfficeScene:
    LockAll
    Message Haven3F_Text_LookerCrates
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 12, Haven3F_WalkToDeskFrom12
    CallIfEq VAR_0x8004, 13, Haven3F_WalkToDeskFrom13
    CallIfEq VAR_0x8004, 14, Haven3F_WalkToDeskFrom14
    Message Haven3F_Text_Manifests
    Message Haven3F_Text_RuthRiftReadings
    ApplyMovement HAVEN_3F_LOOKER, Haven3F_Movement_LookerTurn
    WaitMovement
    Message Haven3F_Text_LookerPokemonGoIn
    CloseMessage
    SetFlag FLAG_ARC2_ETERNA_C
    // Two caretakers come up from the hall and block the door.
    ClearFlag FLAG_UNK_0x0033
    AddObject HAVEN_3F_CARETAKER_1
    AddObject HAVEN_3F_CARETAKER_2
    ApplyMovement HAVEN_3F_CARETAKER_1, Haven3F_Movement_CaretakerBlock
    ApplyMovement HAVEN_3F_CARETAKER_2, Haven3F_Movement_CaretakerBlock
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Haven3F_Movement_FaceSouth
    ApplyMovement HAVEN_3F_GARDENIA, Haven3F_Movement_FaceSouth
    ApplyMovement HAVEN_3F_RUTH, Haven3F_Movement_FaceSouth
    WaitMovement
    ApplyMovement HAVEN_3F_CARETAKER_1, Haven3F_Movement_Exclaim
    ApplyMovement HAVEN_3F_CARETAKER_2, Haven3F_Movement_Exclaim
    WaitMovement
    Message Haven3F_Text_CaretakerStaffOnly
    CloseMessage
    ApplyMovement HAVEN_3F_GARDENIA, Haven3F_Movement_GardeniaJoin
    WaitMovement
    StartTagBattle TRAINER_LEADER_GARDENIA, TRAINER_ECLIPSE_GRUNT_ARC2_03, TRAINER_ECLIPSE_GRUNT_ARC2_04
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Haven3F_LostBattle
    ApplyMovement HAVEN_3F_CARETAKER_1, Haven3F_Movement_CaretakerFlee
    ApplyMovement HAVEN_3F_CARETAKER_2, Haven3F_Movement_CaretakerFlee
    WaitMovement
    RemoveObject HAVEN_3F_CARETAKER_1
    RemoveObject HAVEN_3F_CARETAKER_2
    SetFlag FLAG_ARC2_ETERNA_A
    SetVar VAR_MAP_LOCAL_0, 1
    ReleaseAll
    End

Haven3F_LostBattle:
    BlackOutFromBattle
    ReleaseAll
    End

Haven3F_WalkToDeskFrom12:
    ApplyMovement LOCALID_PLAYER, Haven3F_Movement_DeskFrom12
    WaitMovement
    Return

Haven3F_WalkToDeskFrom13:
    ApplyMovement LOCALID_PLAYER, Haven3F_Movement_DeskFrom13
    WaitMovement
    Return

Haven3F_WalkToDeskFrom14:
    ApplyMovement LOCALID_PLAYER, Haven3F_Movement_DeskFrom14
    WaitMovement
    Return

    .balign 4, 0
Haven3F_Movement_DeskFrom12:
    WalkNormalEast
    WalkNormalNorth 2
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
Haven3F_Movement_DeskFrom13:
    WalkNormalNorth 2
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
Haven3F_Movement_DeskFrom14:
    WalkNormalWest
    WalkNormalNorth 2
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
Haven3F_Movement_LookerTurn:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
Haven3F_Movement_CaretakerBlock:
    WalkFastNorth 2
    EndMovement

    .balign 4, 0
Haven3F_Movement_FaceSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
Haven3F_Movement_Exclaim:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
Haven3F_Movement_GardeniaJoin:
    WalkNormalSouth
    WalkNormalWest
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
Haven3F_Movement_CaretakerFlee:
    WalkFastSouth 3
    EndMovement
