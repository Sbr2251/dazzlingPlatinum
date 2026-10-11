#include "macros/scrcmd.inc"
#include "constants/totem_battle.h"
#include "res/text/bank/eterna_forest.h"

// Arc 2 (s-floaroma), scene 2.10 overworld side. Reads VAR_ARC2_PROGRESS 22; sets 23 (Ruth), 24 (rift entered);
// rift-a sets 26 in MAP_HEADER_DW_ETERNA_FOREST and exits to (84,37) facing south; the aftermath here sets 29.
// The stock overworld Vespiquen totem object is deleted (the totem is fought in the DW, D15).
// Locals added: 25 Ruth (85,39), 26 Cyrus (83,39): shown at 22-26 (FLAG_UNK_0x0030, map-local temp);
// 27 the rift (84,38), "off the main path between two trees": shown at 22-25 (FLAG_UNK_0x0031, map-local temp).
// The silence beat runs once on the first entry at 22 (VAR_MAP_LOCAL_1 arms it; FLAG_UNK_0x093B =
// FLAG_ARC2_FLOAROMA_B records it). Cheryl's partner walk is untouched: her farewell coord column (x82, z34-39)
// spans the clearing, so she always says goodbye before the player reaches the rift, and nothing here stands on
// her exit rows (z36-37).
#define LOCALID_ARC2_RUTH  25
#define LOCALID_ARC2_CYRUS 26
#define LOCALID_ARC2_RIFT  27
#define FLAG_ARC2_FLOAROMA_SILENCE_SEEN FLAG_ARC2_FLOAROMA_B


    ScriptEntry _0047
    ScriptEntry _0108
    ScriptEntry _0198
    ScriptEntry _03EC
    ScriptEntry _03F5
    ScriptEntry _03FE
    ScriptEntry _0411
    ScriptEntry _04E0
    ScriptEntry _04F7
    ScriptEntry _050C
    ScriptEntry _0032
    ScriptEntry _051D
    ScriptEntry EternaForest_Arc2Ruth
    ScriptEntry EternaForest_Arc2Cyrus
    ScriptEntry EternaForest_Arc2Rift
    ScriptEntry EternaForest_Arc2Silence
    ScriptEntry EternaForest_Arc2Aftermath
    ScriptEntryEnd

_0032:
    Call EternaForest_Arc2SetObjects
    GoToIfUnset FLAG_TRAVELED_WITH_CHERYL, _003F
    End

_003F:
    SetVar VAR_UNK_0x40B1, 0
    End

_0047:
    LockAll
    SetPlayerBike FALSE
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8004, 28, _006E
    GoToIfEq VAR_0x8004, 29, _007E
    End

_006E:
    ApplyMovement 0, _00E8
    WaitMovement
    GoTo _008E

_007E:
    ApplyMovement 0, _00F4
    WaitMovement
    GoTo _008E

_008E:
    CallIfUnset FLAG_UNK_0x008B, _00D8
    CallIfSet FLAG_UNK_0x008B, _00E0
    BufferPlayerName 0
    PlaySound SEQ_GONIN
    Message 1
    WaitSound
    SetFlag FLAG_UNK_0x008B
    SetVar VAR_UNK_0x40B1, 1
    Message 2
    WaitABXPadPress
    CloseMessage
    SetVar VAR_PARTNER_TRAINER_ID, TRAINER_CHERYL_ETERNA_FOREST
    SetHasPartner
    SetMovementType 0, 48
    SetObjectFlagIsPersistent 0, TRUE
    ReleaseAll
    End

_00D8:
    BufferPlayerName 0
    Message 0
    Return

_00E0:
    BufferPlayerName 0
    Message 3
    Return

    .balign 4, 0
_00E8:
    MoveAction_153
    WalkNormalSouth
    EndMovement

    .balign 4, 0
_00F4:
    MoveAction_153
    WalkNormalSouth
    WalkNormalEast
    WalkOnSpotNormalSouth
    EndMovement

_0108:
    LockAll
    ClearHasPartner
    SetMovementType 0, 15
    SetObjectFlagIsPersistent 0, FALSE
    ApplyMovement 0, _0190
    WaitMovement
    Message 4
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8004, 28, _0148
    GoToIfEq VAR_0x8004, 29, _0158
    End

_0148:
    ApplyMovement 0, _0174
    WaitMovement
    GoTo _0168

_0158:
    ApplyMovement 0, _0180
    WaitMovement
    GoTo _0168

_0168:
    SetVar VAR_UNK_0x40B1, 0
    ReleaseAll
    End

    .balign 4, 0
_0174:
    WalkNormalNorth 2
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0180:
    WalkNormalNorth 2
    WalkNormalWest
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0190:
    WalkOnSpotNormalSouth
    EndMovement

_0198:
    LockAll
    ApplyMovement 0, _0300
    ApplyMovement LOCALID_PLAYER, _0368
    WaitMovement
    BufferPlayerName 0
    Message 5
    SetVar VAR_0x8004, ITEM_SOOTHE_BELL
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, _01EA
    GoTo _01DB
    End

_01DB:
    Message 6
    GiveItemQuantityNoLineFeed
    GoTo _01EA
    End

_01EA:
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 34, _023B
    GoToIfEq VAR_0x8005, 35, _0253
    GoToIfEq VAR_0x8005, 36, _026B
    GoToIfEq VAR_0x8005, 37, _0283
    GoToIfEq VAR_0x8005, 38, _029B
    GoTo _02B3
    End

_023B:
    ApplyMovement 0, _030C
    ApplyMovement LOCALID_PLAYER, _0374
    WaitMovement
    GoTo _02CB

_0253:
    ApplyMovement 0, _0318
    ApplyMovement LOCALID_PLAYER, _0388
    WaitMovement
    GoTo _02CB

_026B:
    ApplyMovement 0, _0324
    ApplyMovement LOCALID_PLAYER, _039C
    WaitMovement
    GoTo _02CB

_0283:
    ApplyMovement 0, _0330
    ApplyMovement LOCALID_PLAYER, _03B0
    WaitMovement
    GoTo _02CB

_029B:
    ApplyMovement 0, _033C
    ApplyMovement LOCALID_PLAYER, _03C4
    WaitMovement
    GoTo _02CB

_02B3:
    ApplyMovement 0, _0348
    ApplyMovement LOCALID_PLAYER, _03D8
    WaitMovement
    GoTo _02CB

_02CB:
    ApplyMovement 0, _0354
    WaitMovement
    Message 7
    CloseMessage
    ApplyMovement 0, _035C
    WaitMovement
    PlayFanfare SEQ_SE_DP_KAIDAN2
    ClearHasPartner
    RemoveObject 0
    WaitFanfare SEQ_SE_DP_KAIDAN2
    SetFlag FLAG_TRAVELED_WITH_CHERYL
    SetVar VAR_UNK_0x40B1, 2
    ReleaseAll
    End

    .balign 4, 0
_0300:
    WalkOnSpotNormalEast
    MoveAction_153
    EndMovement

    .balign 4, 0
_030C:
    WalkNormalSouth 2
    WalkNormalEast 5
    EndMovement

    .balign 4, 0
_0318:
    WalkNormalSouth
    WalkNormalEast 5
    EndMovement

    .balign 4, 0
_0324:
    WalkNormalSouth
    WalkNormalEast 5
    EndMovement

    .balign 4, 0
_0330:
    WalkNormalNorth
    WalkNormalEast 5
    EndMovement

    .balign 4, 0
_033C:
    WalkNormalNorth
    WalkNormalEast 5
    EndMovement

    .balign 4, 0
_0348:
    WalkNormalNorth 2
    WalkNormalEast 5
    EndMovement

    .balign 4, 0
_0354:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_035C:
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0368:
    Delay8 3
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0374:
    Delay8 2
    WalkOnSpotNormalSouth
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0388:
    Delay8
    WalkOnSpotNormalSouth
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_039C:
    Delay8
    WalkOnSpotNormalSouth
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_03B0:
    Delay8
    WalkOnSpotNormalNorth
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_03C4:
    Delay8
    WalkOnSpotNormalNorth
    Delay8
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_03D8:
    Delay8 2
    WalkOnSpotNormalNorth
    Delay8
    WalkOnSpotNormalEast
    EndMovement

_03EC:
    LockAll
    BufferPlayerName 0
    ReleaseAll
    End

_03F5:
    LockAll
    BufferPlayerName 0
    ReleaseAll
    End

_03FE:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 9
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0411:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 11
    CloseMessage
    ApplyMovement 24, _04BC
    WaitMovement
    Message 12
    FacePlayer
    Message 13
    CloseMessage
    GetPlayerDir VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _046C
    GoToIfEq VAR_RESULT, 1, _047E
    GoToIfEq VAR_RESULT, 2, _0490
    GoToIfEq VAR_RESULT, 3, _04A2
    End

_046C:
    ApplyMovement 24, _04D0
    WaitMovement
    GoTo _04B4
    End

_047E:
    ApplyMovement 24, _04C4
    WaitMovement
    GoTo _04B4
    End

_0490:
    ApplyMovement 24, _04C4
    WaitMovement
    GoTo _04B4
    End

_04A2:
    ApplyMovement 24, _04C4
    WaitMovement
    GoTo _04B4
    End

_04B4:
    RemoveObject 24
    ReleaseAll
    End

    .balign 4, 0
_04BC:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_04C4:
    WalkNormalSouth 2
    WalkNormalEast 9
    EndMovement

    .balign 4, 0
_04D0:
    WalkNormalWest
    WalkNormalSouth 2
    WalkNormalEast 10
    EndMovement

_04E0:
    ShowLandmarkSign 14
    End

_04F7:
    ShowScrollingSign 15
    End

_050C:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message 10
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_051D:
    LockAll
    SetVar VAR_UNK_0x40CD, 2
    ApplyMovement 0, _053C
    WaitMovement
    Message 8
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
_053C:
    WalkOnSpotNormalNorth
    EndMovement

EternaForest_Arc2SetObjects:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    GoToIfLt VAR_ARC2_PROGRESS, 22, EternaForest_Arc2SetObjectsEnd
    GoToIfGe VAR_ARC2_PROGRESS, 27, EternaForest_Arc2SetObjectsEnd
    ClearFlag FLAG_UNK_0x0030
    GoToIfGe VAR_ARC2_PROGRESS, 26, EternaForest_Arc2SetObjectsEnd
    ClearFlag FLAG_UNK_0x0031
    GoToIfNe VAR_ARC2_PROGRESS, 22, EternaForest_Arc2SetObjectsEnd
    GoToIfSet FLAG_ARC2_FLOAROMA_SILENCE_SEEN, EternaForest_Arc2SetObjectsEnd
    SetVar VAR_MAP_LOCAL_1, 1
EternaForest_Arc2SetObjectsEnd:
    Return

// Frame table, first entry at 22: the silence.
EternaForest_Arc2Silence:
    LockAll
    SetVar VAR_MAP_LOCAL_1, 0
    SetFlag FLAG_ARC2_FLOAROMA_SILENCE_SEEN
    WaitTime 20, VAR_RESULT
    Message EternaForest_Text_Arc2Silence
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

EternaForest_Arc2Ruth:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Call EternaForest_Arc2RuthLine
    ReleaseAll
    End

EternaForest_Arc2RuthLine:
    Message EternaForest_Text_Arc2RuthSameSignature
    WaitABXPadPress
    CloseMessage
    CallIfEq VAR_ARC2_PROGRESS, 22, EternaForest_Arc2SetRiftSeen
    Return

EternaForest_Arc2SetRiftSeen:
    SetVar VAR_ARC2_PROGRESS, 23
    Return

EternaForest_Arc2Cyrus:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message EternaForest_Text_Arc2CyrusEllipsis
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// The rift (22-25). At 22 Ruth speaks first (sets 23). Entering sets 24 and warps into the DW map's entry.
EternaForest_Arc2Rift:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    CallIfEq VAR_ARC2_PROGRESS, 22, EternaForest_Arc2RuthLine
    Message EternaForest_Text_Arc2RiftStepInside
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, EternaForest_Arc2RiftStayOut
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    SetVar VAR_ARC2_PROGRESS, 24
    Warp MAP_HEADER_DW_ETERNA_FOREST, 0, 20, 12, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    End

EternaForest_Arc2RiftStayOut:
    CloseMessage
    ReleaseAll
    End

// Frame table at 26: back from the DW at (84,37) facing south, the rift gone. Ruth checks the Resonator.
EternaForest_Arc2Aftermath:
    LockAll
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_ARC2_RUTH, EternaForest_Movement_Arc2RuthToPlayer
    WaitMovement
    ApplyMovement LOCALID_PLAYER, EternaForest_Movement_Arc2FaceEast
    WaitMovement
    Message EternaForest_Text_Arc2RuthWontAnswer
    WaitABXPadPress
    CloseMessage
    WaitTime 15, VAR_RESULT
    Message EternaForest_Text_Arc2RuthGardenia
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 29
    // Ruth and Cyrus walk on toward Eterna (the east exit)
    ApplyMovement LOCALID_ARC2_RUTH, EternaForest_Movement_Arc2RuthLeave
    ApplyMovement LOCALID_ARC2_CYRUS, EternaForest_Movement_Arc2CyrusLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_RUTH
    RemoveObject LOCALID_ARC2_CYRUS
    ReleaseAll
    End

    .balign 4, 0
EternaForest_Movement_Arc2RuthToPlayer:
    EmoteExclamationMark
    WalkNormalNorth 2
    FaceWest
    EndMovement

    .balign 4, 0
EternaForest_Movement_Arc2FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
EternaForest_Movement_Arc2RuthLeave:
    WalkNormalEast
    SetInvisible
    EndMovement

    .balign 4, 0
EternaForest_Movement_Arc2CyrusLeave:
    Delay8 2
    WalkNormalNorth 3
    WalkNormalEast 3
    SetInvisible
    EndMovement
