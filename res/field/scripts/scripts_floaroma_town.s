#include "macros/scrcmd.inc"
#include "res/text/bank/floaroma_town.h"

// Arc 2 (s-floaroma), scene 2.9 evening: VAR_ARC2_PROGRESS 19 -> 20, then warp to Valley Windworks.
// Flags: FLAG_UNK_0x0030 (map-local temp) hides Ruth + Cyrus, FLAG_UNK_0x0031 (map-local temp) hides Garius;
// both are cleared by the engine on every map change, so OnTransition sets them and shows the trio only at 19.
// FLAG_UNK_0x01A1 (stock) hides the Galactic grunts at the meadow gate for good.
// s-floaroma block flags (named here, renamed by the lead): FLAG_UNK_0x093A = FLAG_ARC2_FLOAROMA_A (Minun fled,
// valley_windworks_building), FLAG_UNK_0x093B = FLAG_ARC2_FLOAROMA_B (Eterna Forest silence seen).
#define LOCALID_ARC2_RUTH   13
#define LOCALID_ARC2_CYRUS  14
#define LOCALID_ARC2_GARIUS 15


    ScriptEntry _002E
    ScriptEntry _0030
    ScriptEntry _006C
    ScriptEntry _00B0
    ScriptEntry _00C3
    ScriptEntry _00D6
    ScriptEntry _00E9
    ScriptEntry _00FC
    ScriptEntry _0113
    ScriptEntry _012A
    ScriptEntry _0141
    ScriptEntry FloaromaTown_Arc2EveningScene
    ScriptEntryEnd

_002E:
    SetFlag FLAG_UNK_0x01A1
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    GoToIfNe VAR_ARC2_PROGRESS, 19, FloaromaTown_Arc2TransitionEnd
    ClearFlag FLAG_UNK_0x0030
    ClearFlag FLAG_UNK_0x0031
FloaromaTown_Arc2TransitionEnd:
    End

_0030:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    ApplyMovement 7, _005C
    WaitMovement
    Message 0
    CloseMessage
    ApplyMovement 8, _0064
    WaitMovement
    Message 1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
_005C:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_0064:
    WalkOnSpotNormalWest
    EndMovement

_006C:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    // Arc 2: the stock Galactic meadow lines (2, 3) are gone; she always says her flower line.
    GoTo _0099
    End

_0099:
    Message 4
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
_00A4:
    FaceNorth
    Delay8 3
    EndMovement

_00B0:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 5
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00C3:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 6
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00D6:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 7
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00E9:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 8
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00FC:
    ShowMapSign 12
    End

_0113:
    ShowLandmarkSign 13
    End

_012A:
    ShowLandmarkSign 14
    End

_0141:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    FindPartySlotWithFatefulEncounterSpecies VAR_RESULT, SPECIES_SHAYMIN
    GoToIfEq VAR_RESULT, 0xFF, _019D
    CheckPartyHasSpecies VAR_RESULT, SPECIES_SHAYMIN
    GoToIfEq VAR_RESULT, 0, _019D
    CheckItem ITEM_GRACIDEA, 1, VAR_RESULT
    GoToIfNe VAR_RESULT, 0, _01A8
    Message 9
    SetVar VAR_0x8004, 0x1D2
    SetVar VAR_0x8005, 1
    GiveItemQuantityNoLineFeed
    CloseMessage
    ReleaseAll
    End

_019D:
    Message 11
    GoTo _01B3
    End

_01A8:
    Message 10
    GoTo _01B3
    End

_01B3:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0

// Scene 2.9, evening. The coord row z669 (x168-173) is the only way in from Route 204.
// Ruth (174,668) and Cyrus (175,667) wait outside the Pokemon Center; Garius stands at the flower shop (180,652).
FloaromaTown_Arc2EveningScene:
    LockAll
    // walk the player to (173,668), beside Ruth (the tree row at z670 hides anyone standing on z669)
    ApplyMovement LOCALID_PLAYER, FloaromaTown_Movement_Arc2StepNorth
    WaitMovement
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
FloaromaTown_Arc2WalkEastLoop:
    GoToIfGe VAR_0x8004, 173, FloaromaTown_Arc2AtRuth
    ApplyMovement LOCALID_PLAYER, FloaromaTown_Movement_Arc2StepEast
    WaitMovement
    AddVar VAR_0x8004, 1
    GoTo FloaromaTown_Arc2WalkEastLoop

FloaromaTown_Arc2AtRuth:
    ApplyMovement LOCALID_PLAYER, FloaromaTown_Movement_Arc2FaceEast
    ApplyMovement LOCALID_ARC2_RUTH, FloaromaTown_Movement_Arc2FaceWest
    WaitMovement
    Message FloaromaTown_Text_Arc2RuthSomethingAtWindworks
    WaitABXPadPress
    CloseMessage
    // Garius walks over from the shop, a jar of honey under his arm
    ApplyMovement LOCALID_ARC2_GARIUS, FloaromaTown_Movement_Arc2GariusWalkOver
    WaitMovement
    ApplyMovement LOCALID_PLAYER, FloaromaTown_Movement_Arc2FaceEast
    ApplyMovement LOCALID_ARC2_RUTH, FloaromaTown_Movement_Arc2FaceEast
    ApplyMovement LOCALID_ARC2_CYRUS, FloaromaTown_Movement_Arc2FaceEast
    WaitMovement
    BufferRivalName 0
    Message FloaromaTown_Text_Arc2GariusThroughTheForest
    WaitABXPadPress
    CloseMessage
    // he leaves north toward Eterna Forest (out the east road, Route 205)
    ApplyMovement LOCALID_ARC2_GARIUS, FloaromaTown_Movement_Arc2GariusLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_GARIUS
    ApplyMovement LOCALID_ARC2_CYRUS, FloaromaTown_Movement_Arc2FaceWest
    ApplyMovement LOCALID_ARC2_RUTH, FloaromaTown_Movement_Arc2FaceEast
    WaitMovement
    Message FloaromaTown_Text_Arc2CyrusScoutTheRoad
    WaitABXPadPress
    CloseMessage
    // Cyrus walks off east into the dark; Ruth watches him go
    ApplyMovement LOCALID_ARC2_CYRUS, FloaromaTown_Movement_Arc2CyrusLeave
    ApplyMovement LOCALID_ARC2_RUTH, FloaromaTown_Movement_Arc2FaceEast
    WaitMovement
    RemoveObject LOCALID_ARC2_CYRUS
    WaitTime 30, VAR_RESULT
    ApplyMovement LOCALID_ARC2_RUTH, FloaromaTown_Movement_Arc2FaceWest
    WaitMovement
    Message FloaromaTown_Text_Arc2RuthGetSomeSleep
    WaitABXPadPress
    CloseMessage
    // night passes: heal, then morning at the Windworks gate (valley_windworks_outside runs the 20 scene)
    FadeScreenOut
    WaitFadeScreen
    HealParty
    SetVar VAR_ARC2_PROGRESS, 20
    Warp MAP_HEADER_VALLEY_WINDWORKS_OUTSIDE, 0, 245, 658, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
FloaromaTown_Movement_Arc2StepNorth:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2StepEast:
    WalkNormalEast
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2GariusWalkOver:
    WalkNormalSouth 15
    WalkNormalWest 3
    FaceWest
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2GariusLeave:
    WalkNormalEast 3
    WalkNormalNorth 6
    WalkNormalEast 9
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2CyrusLeave:
    WalkNormalEast 9
    EndMovement
