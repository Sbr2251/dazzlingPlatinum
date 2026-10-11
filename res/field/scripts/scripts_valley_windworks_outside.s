#include "macros/scrcmd.inc"
#include "res/text/bank/valley_windworks_outside.h"

// Arc 2 (s-floaroma), scene 2.9 morning. Stock Galactic content is gone: the door guard (local 0) is hidden
// for good by FLAG_UNK_0x003F (map-local temp, set every load), the door is never locked (no Works Key),
// and the stock Looker scene (VAR_UNK_0x411E) is never armed. Ruth (local 8) and Cyrus (local 9) are shown at
// progress 20 only (FLAG_UNK_0x0030, map-local temp): the frame script walks them in and sets 21.
#define LOCALID_ARC2_RUTH  8
#define LOCALID_ARC2_CYRUS 9


    ScriptEntry _0024
    ScriptEntry _008A
    ScriptEntry _00CF
    ScriptEntry _0150
    ScriptEntry _01A8
    ScriptEntry _01BF
    ScriptEntry _0022
    ScriptEntry _0201
    ScriptEntry ValleyWindworksOutside_Arc2Morning
    ScriptEntryEnd

_0022:
    End

_0024:
    Call ValleyWindworksOutside_Arc2SetObjects
    CallIfEq VAR_UNK_0x40CF, 2, _0082
    // Arc 2: the door is open (the stock Works Key lock is gone) and Drifloon visits from the cold site on.
    GoToIfLt VAR_ARC2_PROGRESS, 22, _007C
    GoToIfSet FLAG_UNK_0x0AA8, _007C
    GetDayOfWeek VAR_MAP_LOCAL_0
    GoToIfNe VAR_MAP_LOCAL_0, 5, _007C
    GoTo _0076

_0076:
    ClearFlag FLAG_UNK_0x020B
    End

_007C:
    SetFlag FLAG_UNK_0x020B
    End

_0082:
    SetVar VAR_UNK_0x40CF, 3
    Return

_008A:
    GoToIfSet FLAG_MAP_LOCAL, _00AD
    End

_00AD:
    SetFlag FLAG_UNK_0x020B
    RemoveObject 4
    ClearFlag FLAG_MAP_LOCAL
    End

_00BB:
    ScrCmd_18B 1, 243, 0x28A
    Return

_00C5:
    SetWarpEventPos 0, 243, 0x28A
    Return

_00CF:
    // Arc 2: unreachable (the Galactic door guard is always hidden)
    End
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 0
    CloseMessage
    StartTrainerBattle TRAINER_GALACTIC_GRUNT_VALLEY_WINDWORKS_1
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _0133
    Message 1
    CloseMessage
    ApplyMovement 0, _013C
    WaitMovement
    LoadDoorAnimation 7, 20, 19, 14, ANIMATION_TAG_DOOR_1
    PlayDoorOpenAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement 0, _0144
    WaitMovement
    PlayDoorCloseAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    UnloadAnimation ANIMATION_TAG_DOOR_1
    Message 4
    RemoveObject 0
    CloseMessage
    ReleaseAll
    End

_0133:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
_013C:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0144:
    WalkNormalNorth
    SetInvisible
    EndMovement

_0150:
    // Arc 2: the locked-door bg event is gone from the events file; kept inert
    End
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfSet FLAG_UNK_0x009F, _016C
    Message 5
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_016C:
    BufferItemName 0, 0x1B6
    Message 6
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, _01A2
    SetFlag FLAG_UNK_0x010F
    Call _00BB
    SetWarpEventPos 0, 243, 0x28E
    Message 7
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_01A2:
    CloseMessage
    ReleaseAll
    End

_01A8:
    ShowLandmarkSign 9
    End

_01BF:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    PlayCry SPECIES_DRIFLOON
    Message 8
    CloseMessage
    WaitCry
    SetFlag FLAG_MAP_LOCAL
    StartLegendaryBattle SPECIES_DRIFLOON, 15
    ClearFlag FLAG_MAP_LOCAL
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _01FB
    SetFlag FLAG_UNK_0x0AA8
    ReleaseAll
    End

_01FB:
    BlackOutFromBattle
    ReleaseAll
    End

_0201:
    LockAll
    ApplyMovement 6, _02D8
    ApplyMovement LOCALID_PLAYER, _02AC
    WaitMovement
    Message 2
    CloseMessage
    ApplyMovement LOCALID_PLAYER, _02BC
    ApplyMovement 6, _02EC
    WaitMovement
    LoadDoorAnimation 7, 20, 19, 14, ANIMATION_TAG_DOOR_1
    PlayDoorOpenAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement 6, _0300
    WaitMovement
    PlayDoorCloseAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    UnloadAnimation ANIMATION_TAG_DOOR_1
    WaitTime 120, VAR_RESULT
    LoadDoorAnimation 7, 20, 19, 14, ANIMATION_TAG_DOOR_1
    PlayDoorOpenAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement 6, _0310
    WaitMovement
    PlayDoorCloseAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    UnloadAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement 6, _031C
    WaitMovement
    Message 3
    CloseMessage
    ApplyMovement LOCALID_PLAYER, _02C8
    ApplyMovement 6, _0324
    WaitMovement
    RemoveObject 6
    SetVar VAR_UNK_0x411E, 2
    ReleaseAll
    End

    .balign 4, 0
_02AC:
    Delay8 5
    Delay4
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_02BC:
    WalkNormalSouth
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_02C8:
    Delay8
    WalkOnSpotNormalWest
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_02D8:
    EmoteExclamationMark
    Delay8
    WalkFastNorth 4
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
_02EC:
    Delay8
    Delay4
    WalkNormalEast
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0300:
    WalkNormalNorth
    SetInvisible
    FaceSouth
    EndMovement

    .balign 4, 0
_0310:
    SetVisible
    WalkFastSouth
    EndMovement

    .balign 4, 0
_031C:
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
_0324:
    WalkFastWest
    WalkFastSouth
    WalkFastSouth 6
    WalkFastWest 9
    EndMovement

ValleyWindworksOutside_Arc2SetObjects:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    SetFlag FLAG_UNK_0x003F
    SetFlag FLAG_UNK_0x0030
    GoToIfNe VAR_ARC2_PROGRESS, 20, ValleyWindworksOutside_Arc2SetObjectsEnd
    ClearFlag FLAG_UNK_0x0030
ValleyWindworksOutside_Arc2SetObjectsEnd:
    Return

// Progress 20 (frame table): morning. The player was warped to (245,658) facing north; Ruth (243,656) and
// Cyrus (244,656) stand at the gate, then walk into the building.
ValleyWindworksOutside_Arc2Morning:
    LockAll
    Message ValleyWindworksOutside_Text_Arc2NextMorning
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC2_RUTH, ValleyWindworksOutside_Movement_Arc2RuthWalkIn
    ApplyMovement LOCALID_ARC2_CYRUS, ValleyWindworksOutside_Movement_Arc2CyrusWalkIn
    WaitMovement
    RemoveObject LOCALID_ARC2_RUTH
    RemoveObject LOCALID_ARC2_CYRUS
    SetVar VAR_ARC2_PROGRESS, 21
    ReleaseAll
    End

    .balign 4, 0
ValleyWindworksOutside_Movement_Arc2RuthWalkIn:
    FaceSouth
    Delay8 2
    FaceNorth
    WalkNormalNorth 2
    SetInvisible
    EndMovement

    .balign 4, 0
ValleyWindworksOutside_Movement_Arc2CyrusWalkIn:
    Delay8 6
    WalkNormalWest
    WalkNormalNorth 2
    SetInvisible
    EndMovement
