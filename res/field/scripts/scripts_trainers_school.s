#include "macros/scrcmd.inc"
#include "res/text/bank/trainers_school.h"
#include "res/field/events/events_trainers_school.h"

// Dazzling Platinum Arc 2 (s-jubilife), scene 2.2: the confession, after hours (VAR_ARC2_PROGRESS 1, sets 3).
// Map-local temporary flags (the engine clears flags 0-63 on every map change; set on every load):
//   FLAG_UNK_0x0030 = hide the stock teacher and students (night)   FLAG_UNK_0x0031 = hide the Arc 2 cast
//   FLAG_UNK_0x0032 = hide the Poke Ball on the table (Rowan's case)


    ScriptEntry _0032
    ScriptEntry _0154
    ScriptEntry _0167
    ScriptEntry _0169
    ScriptEntry _017C
    ScriptEntry _018F
    ScriptEntry _01A2
    ScriptEntry _01A4
    ScriptEntry _01A6
    ScriptEntry _02E4
    ScriptEntry _03D9
    ScriptEntry _049C
    ScriptEntry TrainersSchool_Arc2Cast
    ScriptEntry TrainersSchool_Arc2OnTransition
    ScriptEntry TrainersSchool_Arc2Confession
    ScriptEntryEnd

_0032:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    BufferPlayerName 0
    BufferRivalName 1
    Message 0
    PlaySound SEQ_FANFA4
    BufferPlayerName 0
    Message 1
    WaitSound
    RemoveItem ITEM_PARCEL, 1, VAR_RESULT
    BufferPlayerName 0
    BufferRivalName 1
    Message 2
    SetVar VAR_0x8004, ITEM_TOWN_MAP
    SetVar VAR_0x8005, 1
    GiveItemQuantity
    BufferRivalName 1
    Message 3
    CloseMessage
    GetPlayerDir VAR_RESULT
    SetVar VAR_0x8008, VAR_RESULT
    GoToIfEq VAR_0x8008, 0, _00A4
    GoToIfEq VAR_0x8008, 2, _00BE
    GoTo _00D8
    End

_00A4:
    ApplyMovement 1, _0114
    ApplyMovement LOCALID_PLAYER, _0138
    WaitMovement
    GoTo _00F2
    End

_00BE:
    ApplyMovement 1, _0124
    ApplyMovement LOCALID_PLAYER, _0148
    WaitMovement
    GoTo _00F2
    End

_00D8:
    ApplyMovement 1, _0124
    ApplyMovement LOCALID_PLAYER, _0148
    WaitMovement
    GoTo _00F2
    End

_00F2:
    PlayFanfare SEQ_SE_DP_KAIDAN2
    RemoveObject 1
    WaitFanfare SEQ_SE_DP_KAIDAN2
    SetVar VAR_UNK_0x40E7, 1
    SetFlag FLAG_UNK_0x00F1
    ClearFlag FLAG_UNK_0x01F6
    ClearFlag FLAG_UNK_0x01F5
    ReleaseAll
    End

    .balign 4, 0
_0114:
    WalkFastEast
    WalkFastSouth 8
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
_0124:
    WalkFastSouth 4
    WalkFastEast
    WalkFastSouth 4
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
_0138:
    Delay8
    WalkOnSpotNormalEast
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0148:
    Delay8
    WalkOnSpotNormalSouth
    EndMovement

_0154:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 4
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0167:
    End

_0169:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 6
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_017C:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 8
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_018F:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 7
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_01A2:
    End

_01A4:
    End

_01A6:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x0112, _02A8
    GoToIfSet FLAG_UNK_0x010C, _02BD
    Message 9
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _01E7
    GoToIfEq VAR_RESULT, MENU_NO, _02D3
    End

_01E7:
    Message 10
    CloseMessage
    GetPlayerStarterSpecies VAR_RESULT
    GoToIfEq VAR_RESULT, SPECIES_TURTWIG, _0220
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, _022E
    GoTo _0212
    End

_0212:
    StartTrainerBattle TRAINER_SCHOOL_KID_HARRISON
    GoTo _023C
    End

_0220:
    StartTrainerBattle TRAINER_SCHOOL_KID_HARRISON
    GoTo _023C
    End

_022E:
    StartTrainerBattle TRAINER_SCHOOL_KID_HARRISON
    GoTo _023C
    End

_023C:
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _02DE
    SetFlag FLAG_UNK_0x010C
    GoToIfSet FLAG_UNK_0x010D, _0274
    GoToIfUnset FLAG_UNK_0x010D, _0269
    End

_0269:
    Message 12
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0274:
    Message 13
    SetVar VAR_0x8004, ITEM_POTION
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, _02B3
    GiveItemQuantity
    SetFlag FLAG_UNK_0x0112
    GoTo _02A8
    End

_02A8:
    Message 14
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_02B3:
    MessageBagIsFull
    CloseMessage
    ReleaseAll
    End

_02BD:
    GoToIfSet FLAG_UNK_0x010D, _0274
    Message 12
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_02D3:
    Message 11
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_02DE:
    BlackOutFromBattle
    ReleaseAll
    End

_02E4:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x010D, _039C
    Message 15
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _031A
    GoToIfEq VAR_RESULT, MENU_NO, _03A7
    End

_031A:
    Message 16
    CloseMessage
    GetPlayerStarterSpecies VAR_RESULT
    GoToIfEq VAR_RESULT, SPECIES_TURTWIG, _0353
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, _0361
    GoTo _0345
    End

_0345:
    StartTrainerBattle TRAINER_SCHOOL_KID_CHRISTINE
    GoTo _036F
    End

_0353:
    StartTrainerBattle TRAINER_SCHOOL_KID_CHRISTINE
    GoTo _036F
    End

_0361:
    StartTrainerBattle TRAINER_SCHOOL_KID_CHRISTINE
    GoTo _036F
    End

_036F:
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _03D3
    SetFlag FLAG_UNK_0x010D
    GoToIfSet FLAG_UNK_0x010C, _03BD
    GoToIfUnset FLAG_UNK_0x010C, _03B2
    End

_039C:
    Message 18
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_03A7:
    Message 17
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_03B2:
    Message 18
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_03BD:
    GoToIfSet FLAG_UNK_0x0112, _03B2
    Message 19
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_03D3:
    BlackOutFromBattle
    ReleaseAll
    End

_03D9:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message 20
    GoTo _03EA
    End

_03EA:
    Message 21
    InitGlobalTextMenu 7, 2, 0, VAR_RESULT
    AddMenuEntryImm 0, 0
    AddMenuEntryImm 1, 1
    AddMenuEntryImm 2, 2
    AddMenuEntryImm 3, 3
    AddMenuEntryImm 4, 4
    AddMenuEntryImm 5, 5
    ShowMenuMultiColumn 2
    SetVar VAR_0x8008, VAR_RESULT
    GoToIfEq VAR_0x8008, 0, _045F
    GoToIfEq VAR_0x8008, 1, _046A
    GoToIfEq VAR_0x8008, 2, _0475
    GoToIfEq VAR_0x8008, 3, _0480
    GoToIfEq VAR_0x8008, 4, _048B
    GoTo _0496
    End

_045F:
    Message 22
    GoTo _03EA
    End

_046A:
    Message 23
    GoTo _03EA
    End

_0475:
    Message 24
    GoTo _03EA
    End

_0480:
    Message 25
    GoTo _03EA
    End

_048B:
    Message 26
    GoTo _03EA
    End

_0496:
    CloseMessage
    ReleaseAll
    End

_049C:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message 27
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0

// ------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 2 (s-jubilife): 2.2, the confession. Seats around the table: Rowan (2,8), the player
// (2,9), Ruth (5,8), Garius (5,9); Cyrus stands at the front (4,6). The table's 3D model hides any object on its
// tiles (3-4, 8-9), so Rowan's case opens at the foot of the table: the Poke Ball appears on the floor at (3,10).

TrainersSchool_Arc2OnTransition:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    SetFlag FLAG_UNK_0x0031
    SetFlag FLAG_UNK_0x0032
    GoToIfNe VAR_ARC2_PROGRESS, 1, TrainersSchool_Arc2OnTransitionEnd
    SetFlag FLAG_UNK_0x0030
    ClearFlag FLAG_UNK_0x0031
TrainersSchool_Arc2OnTransitionEnd:
    End

// The cast is only here during the scene (the player is locked)
TrainersSchool_Arc2Cast:
    End

// On frame at VAR_ARC2_PROGRESS 1 (scripts_init_trainers_school.s)
TrainersSchool_Arc2Confession:
    LockAll
    WaitTime 30, VAR_RESULT
    Message TrainersSchool_Text_Arc2RowanReadings
    WaitABXPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2RuthTotem
    WaitABXPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2CyrusNotAsAStranger
    WaitABXPadPress
    CloseMessage
    WaitTime 20, VAR_RESULT
    Message TrainersSchool_Text_Arc2CyrusMyName
    WaitABXPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2CyrusSpirit
    WaitABXPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2CyrusChained
    WaitABXPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2RuthLakeGuardians
    WaitABXPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2CyrusABoy
    WaitABXPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2CyrusHowLong
    WaitABXPadPress
    CloseMessage
    // Rowan stands, slowly (pays off his lab line "...Nobody.")
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_ARC2_ROWAN, TrainersSchool_Arc2Movement_RowanStand
    WaitMovement
    Message TrainersSchool_Text_Arc2RowanNobody
    WaitABXPadPress
    CloseMessage
    // Garius is on his feet so fast his chair scrapes
    PlayFanfare SEQ_SE_DP_WALL_HIT2
    ApplyMovement LOCALID_ARC2_GARIUS, TrainersSchool_Arc2Movement_Jump
    ApplyMovement LOCALID_ARC2_RUTH, TrainersSchool_Arc2Movement_Exclaim
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Arc2Movement_FaceEast
    WaitMovement
    WaitFanfare SEQ_SE_DP_WALL_HIT2
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2GariusChained
    WaitABXPadPress
    CloseMessage
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2GariusSomeOfUs
    WaitABXPadPress
    CloseMessage
    WaitTime 30, VAR_RESULT
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2GariusForgetIt
    WaitABXPadPress
    CloseMessage
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2RowanSitDown
    WaitABXPadPress
    CloseMessage
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2GariusHeShouldGo
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Arc2Movement_FaceNorth
    WaitMovement
    Message TrainersSchool_Text_Arc2CyrusRightToBeAngry
    WaitABXPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2RowanNotAsking
    WaitABXPadPress
    CloseMessage
    // Rowan sits back down, sets his case down at the foot of the table and opens it: one Poke Ball
    ApplyMovement LOCALID_ARC2_ROWAN, TrainersSchool_Arc2Movement_RowanSitAndFaceTable
    WaitMovement
    PlayFanfare SEQ_SE_DP_BOX03
    ClearFlag FLAG_UNK_0x0032
    AddObject LOCALID_ARC2_BALL
    WaitFanfare SEQ_SE_DP_BOX03
    WaitTime 15, VAR_RESULT
    Message TrainersSchool_Text_Arc2RowanThisOne
    WaitABXPadPress
    CloseMessage
    // Cyrus comes around the table, slowly, and stands over the ball
    ApplyMovement LOCALID_ARC2_CYRUS, TrainersSchool_Arc2Movement_CyrusToTable
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Arc2Movement_PlayerWatchCyrusToTable
    WaitMovement
    Message TrainersSchool_Text_Arc2RowanNewStart
    WaitABXPadPress
    CloseMessage
    WaitTime 45, VAR_RESULT
    // He takes it (the starter weak to the player's: his battle 1 team, outside)
    RemoveObject LOCALID_ARC2_BALL
    WaitTime 15, VAR_RESULT
    Message TrainersSchool_Text_Arc2CyrusNotHeld
    WaitABXPadPress
    CloseMessage
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2GariusCountMeOut
    WaitABXPadPress
    CloseMessage
    // Garius walks out; Ruth steps after him
    ApplyMovement LOCALID_ARC2_GARIUS, TrainersSchool_Arc2Movement_GariusLeave
    ApplyMovement LOCALID_PLAYER, TrainersSchool_Arc2Movement_PlayerWatchGarius
    WaitMovement
    PlayFanfare SEQ_SE_DP_KAIDAN2
    RemoveObject LOCALID_ARC2_GARIUS
    WaitFanfare SEQ_SE_DP_KAIDAN2
    ApplyMovement LOCALID_ARC2_RUTH, TrainersSchool_Arc2Movement_RuthStep
    WaitMovement
    BufferRivalName 0
    Message TrainersSchool_Text_Arc2RuthWait
    WaitABXPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2RowanLetHimGo
    WaitABXPadPress
    CloseMessage
    Message TrainersSchool_Text_Arc2RowanMorning
    WaitABXPadPress
    CloseMessage
    // Cyrus walks outside (2.3 waits by the door, in Jubilife)
    ApplyMovement LOCALID_ARC2_CYRUS, TrainersSchool_Arc2Movement_CyrusLeave
    WaitMovement
    PlayFanfare SEQ_SE_DP_KAIDAN2
    RemoveObject LOCALID_ARC2_CYRUS
    WaitFanfare SEQ_SE_DP_KAIDAN2
    WaitTime 20, VAR_RESULT
    // Rowan and Ruth follow him out
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_ARC2_ROWAN
    RemoveObject LOCALID_ARC2_RUTH
    SetVar VAR_ARC2_PROGRESS, 3
    WaitTime 15, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
TrainersSchool_Arc2Movement_RowanStand:
    WalkSlowNorth
    FaceEast
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_RowanSitAndFaceTable:
    WalkSlowSouth
    FaceEast
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_Jump:
    JumpOnSpotFastNorth
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_Exclaim:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_FaceNorth:
    FaceNorth
    EndMovement

    // From the front (4,6) around the east side (column 6) to beside the ball (4,10), facing it
    .balign 4, 0
TrainersSchool_Arc2Movement_CyrusToTable:
    WalkNormalSouth
    WalkNormalEast 2
    WalkNormalSouth 3
    WalkNormalWest 2
    FaceWest
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_PlayerWatchCyrusToTable:
    FaceEast
    Delay16 6
    FaceSouth
    EndMovement

    // From (5,9): south, east along row 10 to the door column, out through the door (7,11)
    .balign 4, 0
TrainersSchool_Arc2Movement_GariusLeave:
    WalkFastSouth
    WalkFastEast 2
    WalkFastSouth
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_PlayerWatchGarius:
    Delay8
    FaceSouth
    EndMovement

    .balign 4, 0
TrainersSchool_Arc2Movement_RuthStep:
    WalkNormalSouth
    EndMovement

    // From (4,10): east along row 10 to the door column, out (7,11)
    .balign 4, 0
TrainersSchool_Arc2Movement_CyrusLeave:
    WalkNormalEast 3
    WalkNormalSouth
    EndMovement
