#include "macros/scrcmd.inc"
#include "res/text/bank/valley_windworks_building.h"

// Arc 2 (s-floaroma), scene 2.9: the cold site and leak L1. Reads VAR_ARC2_PROGRESS 21, sets 22.
// Stock Mars, Charon, the grunts and the twin are hidden for good (FLAG_UNK_0x003F, map-local temp, set every
// load); the Mars coord event and the fleeing-grunt frame script are gone. The scientist (local 2) is the
// "Windworks Worker" by the turbines.
// Locals added: 8 Ruth, 9 Cyrus (shown at 21, FLAG_UNK_0x0030 map-local temp), 10 Minun (PIKACHU sprite as a
// stand-in; shown from 21 until it flees: FLAG_UNK_0x0031 map-local temp, FLAG_UNK_0x093A = FLAG_ARC2_FLOAROMA_A
// once it fled), 11 the cage (ECLIPSE_CRATE placeholder).
// Ledger L1 writes VAR_ARC2_SUSPECT: Cyrus +0, Garius +4, Ruth +8, Bad luck (or B) +12, answered +512.
#define LOCALID_WORKER     2
#define LOCALID_ARC2_RUTH  8
#define LOCALID_ARC2_CYRUS 9
#define LOCALID_ARC2_MINUN 10
#define FLAG_ARC2_FLOAROMA_MINUN_FLED FLAG_ARC2_FLOAROMA_A

// Arc 2, workstream echo (R3): the Resonator echo at the cold site (S8 Echo stage). From the second calmed totem on
// (FLAG_TOTEM_VESPIQUEN_DEFEATED) and with the Resonator, examining the bolt holes replays the site once, as ghosts
// (src/field_move_tasks.c, FieldMoves_EchoGhostDraw): the Plusle strapped into a frame over the bolts, its sparks
// drawn off; the hurried packing; the Plusle carried out of the loading door while the Minun calls from the cage.
// No one comments; it's what the player sees. Nothing else changes, so it never blocks progress.
//   Flag: FLAG_ARC2_ECHO_WINDWORKS = FLAG_ARC1_SPARE_B (P2 pool), set when the echo has played.
//   Map-local: FLAG_UNK_0x0018 hides the ghost actors (set every load, cleared only while the echo plays: AddObject
//   checks it); VAR_MAP_LOCAL_5 is their opacity (0 = off).
//   Ghost actors (object events with fixed local IDs 0xC0-0xC4, script-only): the frame and the Plusle on the bolt
//   holes (13,8), a grunt beside them (14,8, or 12,8 when the player stands at 14,8), then in the corridor the grunt
//   (15,15) and the Plusle (16,15) heading for the loading door (12,16), and the Minun at the cage (17,15, in front of it); a free
//   camera drops to the corridor for that part (the text box would hide it) and comes back up at the end.
#define FLAG_ARC2_ECHO_WINDWORKS FLAG_ARC1_SPARE_B
#define LOCALID_ECHO_FRAME  0xC0
#define LOCALID_ECHO_PLUSLE 0xC1
#define LOCALID_ECHO_GRUNT  0xC2
#define LOCALID_ECHO_MINUN  0xC3
#define ECHO_OPACITY        18


    ScriptEntry _0022
    ScriptEntry _005F
    ScriptEntry _00AC
    ScriptEntry _00BF
    ScriptEntry _037C
    ScriptEntry _03A7
    ScriptEntry _03D2
    ScriptEntry _03DA
    ScriptEntry ValleyWindworksBuilding_Arc2Ruth
    ScriptEntry ValleyWindworksBuilding_Arc2Cyrus
    ScriptEntry ValleyWindworksBuilding_Arc2Minun
    ScriptEntry ValleyWindworksBuilding_Arc2Cage
    ScriptEntry ValleyWindworksBuilding_Arc2BoltHoles
    ScriptEntry ValleyWindworksBuilding_Arc2Generator
    ScriptEntry ValleyWindworksBuilding_Arc2DragMarks
    ScriptEntryEnd

_0022:
    SetFlag FLAG_FIRST_ARRIVAL_VALLEY_WINDWORKS
    SetFlag FLAG_UNK_0x0018
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    SetFlag FLAG_UNK_0x003F
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    CallIfEq VAR_ARC2_PROGRESS, 21, ValleyWindworksBuilding_Arc2ShowRuthCyrus
    GoToIfLt VAR_ARC2_PROGRESS, 21, ValleyWindworksBuilding_Arc2TransitionEnd
    GoToIfSet FLAG_ARC2_FLOAROMA_MINUN_FLED, ValleyWindworksBuilding_Arc2TransitionEnd
    ClearFlag FLAG_UNK_0x0031
ValleyWindworksBuilding_Arc2TransitionEnd:
    End

ValleyWindworksBuilding_Arc2ShowRuthCyrus:
    ClearFlag FLAG_UNK_0x0030
    Return

_0035:
    SetObjectEventPos 5, 21, 5
    SetObjectEventDir 5, DIR_WEST
    SetObjectEventMovementType 5, MOVEMENT_TYPE_LOOK_WEST
    SetObjectEventPos 2, 18, 4
    SetObjectEventDir 2, DIR_SOUTH
    SetObjectEventMovementType 2, MOVEMENT_TYPE_LOOK_SOUTH
    End

_005F:
    LockAll
    ApplyMovement 0, _0090
    WaitMovement
    Message 0
    CloseMessage
    ApplyMovement 0, _0098
    ApplyMovement LOCALID_PLAYER, _00A0
    WaitMovement
    RemoveObject 0
    SetVar VAR_UNK_0x40CF, 1
    ReleaseAll
    End

    .balign 4, 0
_0090:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_0098:
    WalkFastWest 9
    EndMovement

    .balign 4, 0
_00A0:
    Delay8
    WalkOnSpotNormalWest
    EndMovement

_00AC:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00BF:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 6, _00E3
    GoToIfEq VAR_0x8005, 7, _00F5
    End

_00E3:
    ApplyMovement 1, _0348
    WaitMovement
    GoTo _0107
    End

_00F5:
    ApplyMovement 1, _0358
    WaitMovement
    GoTo _0107
    End

_0107:
    Message 2
    CloseMessage
    StartTrainerBattle TRAINER_COMMANDER_MARS_VALLEY_WINDWORKS
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _02B9
    Message 3
    CloseMessage
    ApplyMovement 7, _0374
    WaitMovement
    WaitTime 15, VAR_RESULT
    Message 4
    ApplyMovement 1, _0364
    WaitMovement
    Message 5
    ApplyMovement 1, _036C
    WaitMovement
    Message 6
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    RemoveObject 1
    RemoveObject 7
    RemoveObject 6
    RemoveObject 3
    RemoveObject 4
    SetFlag FLAG_UNK_0x01A2
    ClearFlag FLAG_UNK_0x017F
    SetVar VAR_UNK_0x4089, 2
    SetFlag FLAG_UNK_0x0AA8
    FadeScreenIn
    WaitFadeScreen
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 6, _01B7
    GoToIfEq VAR_0x8005, 7, _01C9
    End

_01B7:
    ApplyMovement 2, _02E8
    WaitMovement
    GoTo _01DB
    End

_01C9:
    ApplyMovement 2, _02F4
    WaitMovement
    GoTo _01DB
    End

_01DB:
    Message 7
    CloseMessage
    SetFlag FLAG_UNK_0x01F8
    ClearFlag FLAG_UNK_0x01F9
    SetObjectEventMovementType 5, MOVEMENT_TYPE_LOOK_WEST
    AddObject 5
    LockObject 5
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 6, _0218
    GoToIfEq VAR_0x8005, 7, _0232
    End

_0218:
    ApplyMovement 5, _02C0
    ApplyMovement 2, _0300
    WaitMovement
    GoTo _024C
    End

_0232:
    ApplyMovement 5, _02D4
    ApplyMovement 2, _030C
    WaitMovement
    GoTo _024C
    End

_024C:
    Message 8
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 6, _0273
    GoToIfEq VAR_0x8005, 7, _0285
    End

_0273:
    ApplyMovement 2, _0318
    WaitMovement
    GoTo _0297
    End

_0285:
    ApplyMovement 2, _0330
    WaitMovement
    GoTo _0297
    End

_0297:
    Message 9
    Message 10
    WaitABXPadPress
    CloseMessage
    SetVar VAR_UNK_0x411E, 1
    ClearFlag FLAG_UNK_0x01FA
    SetVar VAR_UNK_0x40CF, 2
    SetFlag FLAG_ALT_MUSIC_VALLEY_WINDWORKS_BUILDING
    ReleaseAll
    End

_02B9:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
_02C0:
    WalkFastEast 4
    WalkFastNorth
    WalkFastEast 6
    WalkOnSpotFastNorth
    EndMovement

    .balign 4, 0
_02D4:
    WalkFastEast 4
    WalkFastNorth 2
    WalkFastEast 6
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
_02E8:
    WalkNormalSouth 3
    WalkNormalWest
    EndMovement

    .balign 4, 0
_02F4:
    WalkNormalSouth 4
    WalkNormalWest
    EndMovement

    .balign 4, 0
_0300:
    Delay8 6
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_030C:
    Delay8 6
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0318:
    FaceEast
    Delay8 2
    FaceWest
    Delay8 2
    FaceSouth
    EndMovement

    .balign 4, 0
_0330:
    FaceEast
    Delay8 2
    FaceWest
    Delay8 2
    FaceNorth
    EndMovement

    .balign 4, 0
_0348:
    EmoteExclamationMark
    WalkNormalNorth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0358:
    EmoteExclamationMark
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0364:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_036C:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0374:
    WalkOnSpotNormalSouth
    EndMovement

_037C:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfEq VAR_ARC2_PROGRESS, 21, ValleyWindworksBuilding_Arc2Worker
    GoTo _039C
    Message 11
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_039C:
    Message 12
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_03A7:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfGe VAR_UNK_0x40CF, 3, _03C7
    Message 10
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_03C7:
    Message 13
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_03D2:
    GoTo _03E2
    End

_03DA:
    GoTo _03E2
    End

_03E2:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    // Arc 2: the stock Galactic orders (14) are gone; the screen just shows numbers.
    GoTo _0400
    Message 14
    GoTo _040B
    End

_0400:
    Message 15
    GoTo _040B
    End

_040B:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0

ValleyWindworksBuilding_Arc2Worker:
    Message ValleyWindworksBuilding_Text_Arc2WorkerDarkCoats
    WaitABXPadPress
    CloseMessage
    Message ValleyWindworksBuilding_Text_Arc2RuthACall
    WaitABXPadPress
    CloseMessage
    // Ruth looks at Cyrus
    ApplyMovement LOCALID_ARC2_RUTH, ValleyWindworksBuilding_Movement_Arc2FaceEast
    ApplyMovement LOCALID_ARC2_CYRUS, ValleyWindworksBuilding_Movement_Arc2FaceWest
    WaitMovement
    WaitTime 15, VAR_RESULT
    Message ValleyWindworksBuilding_Text_Arc2CyrusSawLights
    WaitABXPadPress
    CloseMessage
    Message ValleyWindworksBuilding_Text_Arc2RuthCouldHaveWokenUs
    WaitABXPadPress
    CloseMessage
    // ledger L1
    ApplyMovement LOCALID_ARC2_RUTH, ValleyWindworksBuilding_Movement_Arc2FaceNorth
    ApplyMovement LOCALID_PLAYER, ValleyWindworksBuilding_Movement_Arc2FaceWest
    WaitMovement
    Message ValleyWindworksBuilding_Text_Arc2RuthWhoToldThem
    InitLocalTextMenu 31, 9, 0, VAR_RESULT
    SetMenuXOriginToRight
    AddMenuEntryImm ValleyWindworksBuilding_Text_Arc2LedgerCyrus, 0
    AddMenuEntryImm ValleyWindworksBuilding_Text_Arc2LedgerGarius, 1
    AddMenuEntryImm ValleyWindworksBuilding_Text_Arc2LedgerRuth, 2
    AddMenuEntryImm ValleyWindworksBuilding_Text_Arc2LedgerBadLuck, 3
    ShowMenu
    SetVar VAR_0x8008, VAR_RESULT
    AddVar VAR_ARC2_SUSPECT, 512
    GoToIfEq VAR_0x8008, 0, ValleyWindworksBuilding_Arc2PickCyrus
    GoToIfEq VAR_0x8008, 1, ValleyWindworksBuilding_Arc2PickGarius
    GoToIfEq VAR_0x8008, 2, ValleyWindworksBuilding_Arc2PickRuth
    GoTo ValleyWindworksBuilding_Arc2PickBadLuck
    End

ValleyWindworksBuilding_Arc2PickCyrus:
    Message ValleyWindworksBuilding_Text_Arc2ReactCyrus
    GoTo ValleyWindworksBuilding_Arc2LedgerDone
    End

ValleyWindworksBuilding_Arc2PickGarius:
    AddVar VAR_ARC2_SUSPECT, 4
    BufferRivalName 0
    Message ValleyWindworksBuilding_Text_Arc2ReactGarius
    GoTo ValleyWindworksBuilding_Arc2LedgerDone
    End

ValleyWindworksBuilding_Arc2PickRuth:
    AddVar VAR_ARC2_SUSPECT, 8
    Message ValleyWindworksBuilding_Text_Arc2ReactRuth
    GoTo ValleyWindworksBuilding_Arc2LedgerDone
    End

ValleyWindworksBuilding_Arc2PickBadLuck:
    AddVar VAR_ARC2_SUSPECT, 12
    Message ValleyWindworksBuilding_Text_Arc2ReactBadLuck
    GoTo ValleyWindworksBuilding_Arc2LedgerDone
    End

ValleyWindworksBuilding_Arc2LedgerDone:
    WaitABXPadPress
    CloseMessage
    Message ValleyWindworksBuilding_Text_Arc2RuthEternaForestNext
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 22
    // stock bookkeeping: the Windworks trouble is over (Floaroma NPCs move on to their later lines)
    SetVar VAR_UNK_0x40CF, 3
    // Ruth and Cyrus head out toward Eterna Forest
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_ARC2_RUTH
    RemoveObject LOCALID_ARC2_CYRUS
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

ValleyWindworksBuilding_Arc2Ruth:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message ValleyWindworksBuilding_Text_Arc2RuthLookAround
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

ValleyWindworksBuilding_Arc2Cyrus:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message ValleyWindworksBuilding_Text_Arc2CyrusEllipsis
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// The Minun (local 10, at 16,14) beside its cage (local 11, at 17,14). It bolts for the loading door (12,16).
ValleyWindworksBuilding_Arc2Minun:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfSet FLAG_ARC2_FLOAROMA_MINUN_FLED, ValleyWindworksBuilding_Arc2CageEmpty
    Message ValleyWindworksBuilding_Text_Arc2Cage
    WaitABXPadPress
    CloseMessage
    PlayCry SPECIES_MINUN
    ApplyMovement LOCALID_ARC2_MINUN, ValleyWindworksBuilding_Movement_Arc2MinunStartle
    WaitMovement
    Message ValleyWindworksBuilding_Text_Arc2MinunCry
    WaitCry
    WaitABXPadPress
    CloseMessage
    GetPlayerDir VAR_RESULT
    GoToIfEq VAR_RESULT, DIR_EAST, ValleyWindworksBuilding_Arc2MinunRunSouth
    ApplyMovement LOCALID_ARC2_MINUN, ValleyWindworksBuilding_Movement_Arc2MinunRunWest
    WaitMovement
    GoTo ValleyWindworksBuilding_Arc2MinunGone
    End

ValleyWindworksBuilding_Arc2MinunRunSouth:
    ApplyMovement LOCALID_ARC2_MINUN, ValleyWindworksBuilding_Movement_Arc2MinunRunSouth
    WaitMovement
ValleyWindworksBuilding_Arc2MinunGone:
    RemoveObject LOCALID_ARC2_MINUN
    SetFlag FLAG_ARC2_FLOAROMA_MINUN_FLED
    Message ValleyWindworksBuilding_Text_Arc2MinunRanOut
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

ValleyWindworksBuilding_Arc2Cage:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfUnset FLAG_ARC2_FLOAROMA_MINUN_FLED, ValleyWindworksBuilding_Arc2CageWithMinun
ValleyWindworksBuilding_Arc2CageEmpty:
    Message ValleyWindworksBuilding_Text_Arc2CageEmpty
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

ValleyWindworksBuilding_Arc2CageWithMinun:
    GoToIfLt VAR_ARC2_PROGRESS, 21, ValleyWindworksBuilding_Arc2CageEmpty
    GoTo ValleyWindworksBuilding_Arc2Minun
    End

ValleyWindworksBuilding_Arc2BoltHoles:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message ValleyWindworksBuilding_Text_Arc2BoltHoles
    WaitABXPadPress
    CloseMessage
    Call ValleyWindworksBuilding_Echo
    ReleaseAll
    End

ValleyWindworksBuilding_Arc2Generator:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message ValleyWindworksBuilding_Text_Arc2Generator
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

ValleyWindworksBuilding_Arc2DragMarks:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message ValleyWindworksBuilding_Text_Arc2DragMarks
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
ValleyWindworksBuilding_Movement_Arc2FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_Arc2FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_Arc2FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_Arc2MinunStartle:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_Arc2MinunRunWest:
    WalkFastWest 4
    WalkFastSouth 2
    SetInvisible
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_Arc2MinunRunSouth:
    WalkFastSouth
    WalkFastWest 4
    WalkFastSouth
    SetInvisible
    EndMovement

// ------------------------------------------------------------------------------------------------ echo (S8)
// Called from the bolt holes (13,8) after their line; the player is beside them (any side).
ValleyWindworksBuilding_Echo:
    GoToIfUnset FLAG_TOTEM_VESPIQUEN_DEFEATED, ValleyWindworksBuilding_EchoReturn
    GoToIfSet FLAG_ARC2_ECHO_WINDWORKS, ValleyWindworksBuilding_EchoReturn
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, ValleyWindworksBuilding_EchoReturn
    Message ValleyWindworksBuilding_Text_EchoHum
    WaitABXPadPress
    CloseMessage
    // The grunt stands on the side away from the player
    SetObjectEventPos LOCALID_ECHO_GRUNT, 14, 8
    SetObjectEventDir LOCALID_ECHO_GRUNT, DIR_WEST
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 14, ValleyWindworksBuilding_EchoGruntWest
    // The echo starts: a white flash, then the frame, the Plusle and the grunt fade in
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    SetVar VAR_MAP_LOCAL_5, 1
    ClearFlag FLAG_UNK_0x0018
    AddObject LOCALID_ECHO_FRAME
    AddObject LOCALID_ECHO_PLUSLE
    AddObject LOCALID_ECHO_GRUNT
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitFanfare SEQ_SE_PL_SYUWA
    Call ValleyWindworksBuilding_EchoFadeIn
    WaitTime 15, VAR_RESULT
    Call ValleyWindworksBuilding_EchoSpark
    Message ValleyWindworksBuilding_Text_EchoFrame
    WaitABXPadPress
    CloseMessage
    Call ValleyWindworksBuilding_EchoSpark
    Message ValleyWindworksBuilding_Text_EchoSparks
    WaitABXPadPress
    CloseMessage
    // The grunt hurries
    ApplyMovement LOCALID_ECHO_GRUNT, ValleyWindworksBuilding_Movement_EchoHurry
    WaitMovement
    Message ValleyWindworksBuilding_Text_EchoPacking
    WaitABXPadPress
    CloseMessage
    // The echo skips: the frame is gone; the grunt and the Plusle are in the corridor, the Minun in the cage
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    RemoveObject LOCALID_ECHO_FRAME
    RemoveObject LOCALID_ECHO_PLUSLE
    RemoveObject LOCALID_ECHO_GRUNT
    // The camera drops to the corridor (z 13), above the text box
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    SetVar VAR_0x8006, VAR_0x8005
    AddFreeCamera VAR_0x8004, VAR_0x8005
    Call ValleyWindworksBuilding_EchoCameraDown
    WaitTime 2, VAR_RESULT
    ClearFlag FLAG_UNK_0x0018 // RemoveObject set it again
    SetObjectEventPos LOCALID_ECHO_GRUNT, 15, 15
    SetObjectEventDir LOCALID_ECHO_GRUNT, DIR_WEST
    SetObjectEventPos LOCALID_ECHO_PLUSLE, 16, 15
    SetObjectEventDir LOCALID_ECHO_PLUSLE, DIR_WEST
    AddObject LOCALID_ECHO_GRUNT
    AddObject LOCALID_ECHO_PLUSLE
    AddObject LOCALID_ECHO_MINUN
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitFanfare SEQ_SE_PL_SYUWA
    Message ValleyWindworksBuilding_Text_EchoCarried
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ECHO_GRUNT, ValleyWindworksBuilding_Movement_EchoGruntOut
    ApplyMovement LOCALID_ECHO_PLUSLE, ValleyWindworksBuilding_Movement_EchoPlusleOut
    WaitMovement
    PlayCry SPECIES_MINUN
    ApplyMovement LOCALID_ECHO_MINUN, ValleyWindworksBuilding_Movement_EchoMinunCalls
    WaitMovement
    WaitCry
    Message ValleyWindworksBuilding_Text_EchoMinun
    WaitABXPadPress
    CloseMessage
    // It fades; the ghosts go, the camera comes back up to the player, and the opacity is back to 0 before the
    // player moves again
    Call ValleyWindworksBuilding_EchoFadeOut
    RemoveObject LOCALID_ECHO_GRUNT
    RemoveObject LOCALID_ECHO_PLUSLE
    RemoveObject LOCALID_ECHO_MINUN
    Call ValleyWindworksBuilding_EchoCameraUp
    RestoreCamera
    SetFlag FLAG_UNK_0x0018
    SetVar VAR_MAP_LOCAL_5, 0
    WaitTime 2, VAR_RESULT
    SetFlag FLAG_ARC2_ECHO_WINDWORKS
    Message ValleyWindworksBuilding_Text_EchoFade
    WaitABXPadPress
    CloseMessage
ValleyWindworksBuilding_EchoReturn:
    Return

// The free camera steps south until it is at z 13 (VAR_0x8005 tracks it), then back north to the player's row
// (VAR_0x8006).
ValleyWindworksBuilding_EchoCameraDown:
    GoToIfGe VAR_0x8005, 13, ValleyWindworksBuilding_EchoReturn
    ApplyFreeCameraMovement ValleyWindworksBuilding_Movement_EchoCameraSouth
    WaitMovement
    AddVar VAR_0x8005, 1
    GoTo ValleyWindworksBuilding_EchoCameraDown
    End

ValleyWindworksBuilding_EchoCameraUp:
    GoToIfLe VAR_0x8005, VAR_0x8006, ValleyWindworksBuilding_EchoReturn
    ApplyFreeCameraMovement ValleyWindworksBuilding_Movement_EchoCameraNorth
    WaitMovement
    SubVar VAR_0x8005, 1
    GoTo ValleyWindworksBuilding_EchoCameraUp
    End

ValleyWindworksBuilding_EchoGruntWest:
    SetObjectEventPos LOCALID_ECHO_GRUNT, 12, 8
    SetObjectEventDir LOCALID_ECHO_GRUNT, DIR_EAST
    Return

// The Plusle sparks: its cry, a white flicker, a jolt
ValleyWindworksBuilding_EchoSpark:
    PlayCry SPECIES_PLUSLE
    ApplyMovement LOCALID_ECHO_PLUSLE, ValleyWindworksBuilding_Movement_EchoJolt
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    ShakeCamera 4, 1
    WaitMovement
    WaitCry
    Return

ValleyWindworksBuilding_EchoFadeIn:
    AddVar VAR_MAP_LOCAL_5, 1
    WaitTime 1, VAR_RESULT
    GoToIfLt VAR_MAP_LOCAL_5, ECHO_OPACITY, ValleyWindworksBuilding_EchoFadeIn
    Return

ValleyWindworksBuilding_EchoFadeOut:
    SubVar VAR_MAP_LOCAL_5, 1
    WaitTime 1, VAR_RESULT
    GoToIfGt VAR_MAP_LOCAL_5, 1, ValleyWindworksBuilding_EchoFadeOut
    Return

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoCameraSouth:
    WalkFastSouth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoCameraNorth:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoJolt:
    JumpOnSpotFastSouth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoHurry:
    WalkOnSpotFastSouth
    WalkOnSpotFastNorth
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoGruntOut:
    WalkFastWest 3
    WalkFastSouth
    SetInvisible
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoPlusleOut:
    Delay4
    WalkFastWest 4
    WalkFastSouth
    SetInvisible
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoMinunCalls:
    JumpOnSpotFastSouth
    Delay8
    JumpOnSpotFastSouth
    EndMovement
