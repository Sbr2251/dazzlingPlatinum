#include "macros/scrcmd.inc"
#include "res/text/bank/route_214.h"
#include "res/text/bank/arc2_common.h"
#include "generated/text_banks.h"
#include "res/field/events/events_route_214.h"

// Arc 2, workstream s-route214: screenplay 2.18 (overworld part: the dawn grunts, ledger L2), the rift into
// MAP_HEADER_DW_ROUTE_214 (docs/arc2/rift_contract.md), and the hand-off to the 2.19 Kahn cutaway after the calm.
//
// Flags (s-route214 block 0x094B-0x094C, FLAG_ARC2_ROUTE214_A/B): none needed. Map-local temporaries (the stock
// rock smash rocks use 0x20/0x21), set every load in Route214_Arc2OnTransition:
//   FLAG_UNK_0x0030 = hide the rift        FLAG_UNK_0x0031 = hide the grunts' machine
//   FLAG_UNK_0x0032 = hide both grunts     FLAG_UNK_0x0033 = hide Ruth          FLAG_UNK_0x0034 = hide Cyrus
//
// VAR_ARC2_PROGRESS on this map (block 60-69; rift-b sets 63):
//   < 59   the rift at (726,664) only (closed: touching it shows one line).
//   59     + the machine (726,663) and grunts (725,663) (725,664). Any step into the clearing in front of the rift
//          (coord events: row 660 x716-720 from the north, x716-731 z661-665) runs 2.18: sets 60, the player is
//          walked to (724,664), two battles (TRAINER_ECLIPSE_GRUNT_ARC2_09 then _10), ledger L2, sets 61.
//          Losing either battle puts it back to 59 (the scene replays from the start).
//   61-62  rift open: touching it sets 62 and warps to DW_ROUTE_214 (20,12) west. Ruth (723,663), Cyrus (723,665).
//   63     back from the DW at (726,665) facing south (rift-b's exit). The on-frame script (entry 11) fades to
//          black and warps into the 2.19 cutaway (s-cutaways: Route 222 742,796 north, no fade in). The cutaway
//          sets 69 and returns the player to (726,665) facing south.
//   >= 63  nothing Arc 2 is left on this map.
// D15: the overworld Skarmory totem object and its StartTotemBattle script are gone (the totem lives in the DW).
//
// ROUTE214_KAHN_CUTAWAY_STUB: define it to 1 to skip the cutaway warp (fade, set 69, stay here) when building
// without s-cutaways' Route 222 scene.
#ifndef ROUTE214_KAHN_CUTAWAY_STUB
#define ROUTE214_KAHN_CUTAWAY_STUB 0
#endif

#define ROUTE214_RIFT    ROUTE_214_ARC2_RIFT
#define ROUTE214_MACHINE ROUTE_214_ARC2_MACHINE
#define ROUTE214_GRUNT_M ROUTE_214_ARC2_GRUNT_M
#define ROUTE214_GRUNT_F ROUTE_214_ARC2_GRUNT_F
#define ROUTE214_RUTH    ROUTE_214_ARC2_RUTH
#define ROUTE214_CYRUS   ROUTE_214_ARC2_CYRUS

// Arc 2, workstream echo (R3): the Resonator echo at the boost machine's site (S8 Echo stage). From 64 on (after the
// calm and the 2.19 cutaway) a bg event on the rift's old tile (726,664, faced from the south) shows the burned grass.
// From the second calmed totem on (FLAG_TOTEM_VESPIQUEN_DEFEATED) and with the Resonator, it then replays the site
// once, as ghosts (src/field_move_tasks.c, FieldMoves_EchoGhostDraw): the machine's crate pried open, the air tearing
// in front of it, the Skarmory screaming on the other side. No one comments; it's what the player sees, and the last
// line ties the cry to the rift. Nothing else changes, so it never blocks progress.
//   Flag: FLAG_ARC2_ECHO_ROUTE214 = FLAG_ARC1_SPARE_D (P2 pool), set when the echo has played.
//   Map-local: FLAG_UNK_0x0018 hides the ghost actors (set every load, cleared only while the echo plays: AddObject
//   checks it); VAR_MAP_LOCAL_5 is their opacity (0 = off).
//   Ghost actors (object events with fixed local IDs 0xC0-0xC4, script-only), where 2.18 had them: the machine's
//   crate (726,663), the grunts (725,663) (725,664), the tear (726,664) and the Skarmory inside it.
#define FLAG_ARC2_ECHO_ROUTE214 FLAG_ARC1_SPARE_D
#define ROUTE214_ECHO_CRATE     0xC0
#define ROUTE214_ECHO_GRUNT_M   0xC1
#define ROUTE214_ECHO_GRUNT_F   0xC2
#define ROUTE214_ECHO_TEAR      0xC3
#define ROUTE214_ECHO_SKARMORY  0xC4
#define ROUTE214_ECHO_OPACITY   18

    ScriptEntry _00A2
    ScriptEntry _00B9
    ScriptEntry _0075
    ScriptEntry _0012
    ScriptEntry Route214_Arc2Rift
    ScriptEntry Route214_Arc2Machine
    ScriptEntry Route214_Arc2Grunt
    ScriptEntry Route214_Arc2Ruth
    ScriptEntry Route214_Arc2Cyrus
    ScriptEntry Route214_Arc2SceneL2
    ScriptEntry Route214_Arc2AfterCalm
    ScriptEntry Route214_EchoSite
    ScriptEntryEnd

_0012:
    GetUnownFormsSeenCount VAR_MAP_LOCAL_0
    GoToIfGe VAR_MAP_LOCAL_0, 26, _003F
    GoToIfGe VAR_MAP_LOCAL_0, 10, _0051
    GoToIfLt VAR_MAP_LOCAL_0, 10, _0063
    End

_003F:
    SetWarpEventPos 2, 0x2C6, 0x29E
    SetWarpEventPos 3, 0x2C6, 0x29E
    End

_0051:
    SetWarpEventPos 2, 0x2C6, 0x29E
    SetWarpEventPos 4, 0x2C6, 0x29E
    End

_0063:
    SetWarpEventPos 3, 0x2C6, 0x29E
    SetWarpEventPos 4, 0x2C6, 0x29E
    End

_0075:
    Call Route214_Arc2OnTransition
    GetUnownFormsSeenCount VAR_MAP_LOCAL_0
    GoToIfGe VAR_MAP_LOCAL_0, 26, _003F
    GoToIfGe VAR_MAP_LOCAL_0, 10, _0051
    GoToIfLt VAR_MAP_LOCAL_0, 10, _0063
    End

_00A2:
    ShowArrowSign 0
    End

_00B9:
    ShowArrowSign 1
    End

// ------------------------------------------------------------------------------------------------ on transition
Route214_Arc2OnTransition:
    SetFlag FLAG_UNK_0x0018
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    SetFlag FLAG_UNK_0x0032
    SetFlag FLAG_UNK_0x0033
    SetFlag FLAG_UNK_0x0034
    GoToIfGe VAR_ARC2_PROGRESS, 63, Route214_Return
    ClearFlag FLAG_UNK_0x0030
    GoToIfGe VAR_ARC2_PROGRESS, 61, Route214_Arc2OnTransitionRiftOpen
    GoToIfLt VAR_ARC2_PROGRESS, 59, Route214_Return
    ClearFlag FLAG_UNK_0x0031
    ClearFlag FLAG_UNK_0x0032
    Return

Route214_Arc2OnTransitionRiftOpen:
    ClearFlag FLAG_UNK_0x0033
    ClearFlag FLAG_UNK_0x0034
Route214_Return:
    Return

// ------------------------------------------------------------------------------------------------ talk scripts
// The rift (726,664). Open at 61-62: into the Distortion World (rift-b's map), per the rift contract.
Route214_Arc2Rift:
    LockAll
    GoToIfLt VAR_ARC2_PROGRESS, 61, Route214_Arc2RiftClosed
    GoToIfGe VAR_ARC2_PROGRESS, 63, Route214_Arc2Release
    SetVar VAR_ARC2_PROGRESS, 62
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    Warp MAP_HEADER_DW_ROUTE_214, 0, 20, 12, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    End

Route214_Arc2RiftClosed:
    PlayFanfare SEQ_SE_CONFIRM
    Message Route214_Text_Arc2RiftClosed
    WaitABXPadPress
    CloseMessage
Route214_Arc2Release:
    ReleaseAll
    End

// The machine and the grunts are only out at 59, inside the coord events' area; talking to them starts the scene.
Route214_Arc2Machine:
    GoTo Route214_Arc2SceneL2
    End

Route214_Arc2Grunt:
    GoTo Route214_Arc2SceneL2
    End

Route214_Arc2Ruth:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message Route214_Text_Arc2RuthGo
    WaitABXPadPress
    CloseMessage
    ApplyMovement ROUTE214_RUTH, Route214_Movement_FaceEast
    WaitMovement
    ReleaseAll
    End

Route214_Arc2Cyrus:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message Route214_Text_Arc2CyrusReady
    WaitABXPadPress
    CloseMessage
    ApplyMovement ROUTE214_CYRUS, Route214_Movement_FaceEast
    WaitMovement
    ReleaseAll
    End

// ------------------------------------------------------------------------------------------------ 2.18 (overworld)
Route214_Arc2SceneL2:
    LockAll
    SetVar VAR_ARC2_PROGRESS, 60
    Call Route214_Arc2StagePlayer
    ApplyMovement LOCALID_PLAYER, Route214_Movement_FaceEast
    WaitMovement
    WaitTime 15, VAR_RESULT
    // Ruth and Cyrus come up behind the player: (716,663) -> (723,663), (716,665) -> (723,665)
    SetObjectEventPos ROUTE214_RUTH, 716, 663
    SetObjectEventPos ROUTE214_CYRUS, 716, 665
    ClearFlag FLAG_UNK_0x0033
    ClearFlag FLAG_UNK_0x0034
    AddObject ROUTE214_RUTH
    AddObject ROUTE214_CYRUS
    ApplyMovement ROUTE214_RUTH, Route214_Movement_CompanionWalkIn
    ApplyMovement ROUTE214_CYRUS, Route214_Movement_CompanionWalkIn
    WaitMovement
    // The grunts turn from their machine
    ApplyMovement ROUTE214_GRUNT_M, Route214_Movement_GruntNotice
    ApplyMovement ROUTE214_GRUNT_F, Route214_Movement_GruntNotice
    WaitMovement
    Message Route214_Text_Arc2GruntTooLate
    WaitABXPadPress
    CloseMessage
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_ARC2_09
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route214_Arc2LostBattle
    Message Route214_Text_Arc2GruntSaysHi
    WaitABXPadPress
    CloseMessage
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_ARC2_10
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route214_Arc2LostBattle
    // They grab the machine and flee south
    RemoveObject ROUTE214_MACHINE
    SetFlag FLAG_UNK_0x0031
    ApplyMovement ROUTE214_GRUNT_F, Route214_Movement_GruntFleeSouthF
    ApplyMovement ROUTE214_GRUNT_M, Route214_Movement_GruntFleeSouthM
    WaitMovement
    RemoveObject ROUTE214_GRUNT_M
    RemoveObject ROUTE214_GRUNT_F
    SetFlag FLAG_UNK_0x0032
    WaitTime 15, VAR_RESULT
    // Ruth faces the rift, not Cyrus
    ApplyMovement ROUTE214_RUTH, Route214_Movement_FaceEast
    ApplyMovement ROUTE214_CYRUS, Route214_Movement_FaceEast
    WaitMovement
    Message Route214_Text_Arc2RuthKnewDawn
    WaitABXPadPress
    CloseMessage
    Call Route214_LedgerL2
    Message Route214_Text_Arc2RuthGo
    WaitABXPadPress
    CloseMessage
    // The rift opens
    SetVar VAR_ARC2_PROGRESS, 61
    ApplyMovement LOCALID_PLAYER, Route214_Movement_FaceEast
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA
    ShakeCamera 16, 2
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitFanfare SEQ_SE_PL_SYUWA
    SetObjectEventMovementType ROUTE214_RUTH, MOVEMENT_TYPE_LOOK_EAST
    SetObjectEventMovementType ROUTE214_CYRUS, MOVEMENT_TYPE_LOOK_EAST
    ReleaseAll
    End

Route214_Arc2LostBattle:
    SetVar VAR_ARC2_PROGRESS, 59
    BlackOutFromBattle
    ReleaseAll
    End

// Walks the player to (724,664), one tile west of grunt F, from wherever the coord events caught them.
//   x <= 724: z first (to 664), then x.   x 725-726: x first, then z.   x >= 727: down to 665, west, then up.
// Nothing Arc 2 stands on row 665, on column 724, or on row 664 west of 725, so the paths are clear.
Route214_Arc2StagePlayer:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfGe VAR_0x8004, 727, Route214_Arc2StageFarEast
    GoToIfGe VAR_0x8004, 725, Route214_Arc2StageXFirst
    SetVar VAR_0x8006, 664
    Call Route214_AlignZ
    Call Route214_AlignX
    Return

Route214_Arc2StageXFirst:
    Call Route214_AlignX
    SetVar VAR_0x8006, 664
    Call Route214_AlignZ
    Return

Route214_Arc2StageFarEast:
    SetVar VAR_0x8006, 665
    Call Route214_AlignZ
    Call Route214_AlignX
    SetVar VAR_0x8006, 664
    Call Route214_AlignZ
    Return

Route214_AlignX:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8004, 724, Route214_Return
    GoToIfLt VAR_0x8004, 724, Route214_AlignXEast
    ApplyMovement LOCALID_PLAYER, Route214_Movement_StepWest
    WaitMovement
    GoTo Route214_AlignX
    End

Route214_AlignXEast:
    ApplyMovement LOCALID_PLAYER, Route214_Movement_StepEast
    WaitMovement
    GoTo Route214_AlignX
    End

Route214_AlignZ:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, VAR_0x8006, Route214_Return
    GoToIfLt VAR_0x8005, VAR_0x8006, Route214_AlignZSouth
    ApplyMovement LOCALID_PLAYER, Route214_Movement_StepNorth
    WaitMovement
    GoTo Route214_AlignZ
    End

Route214_AlignZSouth:
    ApplyMovement LOCALID_PLAYER, Route214_Movement_StepSouth
    WaitMovement
    GoTo Route214_AlignZ
    End

// Ledger L2 (screenplay "The suspect ledger"): prompt from arc2_common, 4-way menu, B = Bad luck.
// VAR_ARC2_SUSPECT += pick (0 Cyrus, 16 Garius, 32 Ruth, 48 Bad luck) + 1024 (L2 answered). Runs once: the add is
// skipped if the L2 answered bit is already set (L3's 2048 can't be set yet at this point in the story).
Route214_LedgerL2:
    BufferRivalName 1
    MessageFromBank TEXT_BANK_ARC2_COMMON, Arc2Common_Text_LedgerWhoKnew
    InitLocalTextMenu 31, 9, 0, VAR_RESULT
    SetMenuXOriginToRight
    AddMenuEntryImm Route214_Text_Arc2LedgerCyrus, 0
    AddMenuEntryImm Route214_Text_Arc2LedgerGarius, 1
    AddMenuEntryImm Route214_Text_Arc2LedgerRuth, 2
    AddMenuEntryImm Route214_Text_Arc2LedgerBadLuck, 3
    ShowMenu
    SetVar VAR_0x8008, VAR_RESULT
    GoToIfEq VAR_0x8008, 0, Route214_LedgerL2Cyrus
    GoToIfEq VAR_0x8008, 1, Route214_LedgerL2Garius
    GoToIfEq VAR_0x8008, 2, Route214_LedgerL2Ruth
    GoTo Route214_LedgerL2BadLuck
    End

Route214_LedgerL2Cyrus:
    SetVar VAR_0x8009, 1024
    Message Route214_Text_Arc2ReactCyrus
    GoTo Route214_LedgerL2Store
    End

Route214_LedgerL2Garius:
    SetVar VAR_0x8009, 1040
    BufferRivalName 1
    Message Route214_Text_Arc2ReactGarius
    GoTo Route214_LedgerL2Store
    End

Route214_LedgerL2Ruth:
    SetVar VAR_0x8009, 1056
    Message Route214_Text_Arc2ReactRuth
    GoTo Route214_LedgerL2Store
    End

Route214_LedgerL2BadLuck:
    SetVar VAR_0x8009, 1072
    Message Route214_Text_Arc2ReactBadLuck
    GoTo Route214_LedgerL2Store
    End

Route214_LedgerL2Store:
    WaitABXPadPress
    CloseMessage
    GoToIfGe VAR_ARC2_SUSPECT, 1024, Route214_Return
    AddVar VAR_ARC2_SUSPECT, VAR_0x8009
    Return

// ------------------------------------------------------------------------------------------------ after the calm
// 63 (rift-b's Skarmory calm, exit at 726,665 facing south): the 2.19 Kahn cutaway. Caller contract (s-cutaways,
// COMMON.md hazards): progress already 63, fade to black, Warp to Route 222 742,796 north, no FadeScreenIn. The
// cutaway sets 69 and brings the player back here, so this on-frame entry does not fire again.
Route214_Arc2AfterCalm:
    LockAll
    WaitTime 20, VAR_RESULT
#if ROUTE214_KAHN_CUTAWAY_STUB
    FadeScreenOut
    WaitFadeScreen
    SetVar VAR_ARC2_PROGRESS, 69
    WaitTime 30, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End
#else
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_ROUTE_222, 0, 742, 796, DIR_NORTH
    ReleaseAll
    End
#endif

// ------------------------------------------------------------------------------------------------ echo (S8)
// The rift's old tile (726,664), faced from (726,665): script 12 (bg event, facing north).
Route214_EchoSite:
    GoToIfLt VAR_ARC2_PROGRESS, 64, Route214_EchoSiteEnd
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message Route214_Text_EchoSite
    WaitABXPadPress
    CloseMessage
    Call Route214_Echo
    ReleaseAll
Route214_EchoSiteEnd:
    End

Route214_Echo:
    GoToIfUnset FLAG_TOTEM_VESPIQUEN_DEFEATED, Route214_Return
    GoToIfSet FLAG_ARC2_ECHO_ROUTE214, Route214_Return
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route214_Return
    Message Route214_Text_EchoHum
    WaitABXPadPress
    CloseMessage
    // The echo starts: a white flash, then the crate and the grunts fade in
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    SetVar VAR_MAP_LOCAL_5, 1
    ClearFlag FLAG_UNK_0x0018
    AddObject ROUTE214_ECHO_CRATE
    AddObject ROUTE214_ECHO_GRUNT_M
    AddObject ROUTE214_ECHO_GRUNT_F
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitFanfare SEQ_SE_PL_SYUWA
    Call Route214_EchoFadeIn
    WaitTime 20, VAR_RESULT
    // The crate is pried open
    PlayFanfare SEQ_SE_DP_BOX03
    ShakeCamera 4, 1
    WaitFanfare SEQ_SE_DP_BOX03
    Message Route214_Text_EchoCrate
    WaitABXPadPress
    CloseMessage
    // The machine hums, and the air in front of it tears open
    AddObject ROUTE214_ECHO_TEAR
    PlayFanfare SEQ_SE_PL_SYUWA
    ShakeCamera 16, 2
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitFanfare SEQ_SE_PL_SYUWA
    Message Route214_Text_EchoTear
    WaitABXPadPress
    CloseMessage
    // The Skarmory, far inside it
    AddObject ROUTE214_ECHO_SKARMORY
    PlayCry SPECIES_SKARMORY
    ApplyMovement ROUTE214_ECHO_SKARMORY, Route214_Movement_EchoThrash
    ShakeCamera 8, 1
    WaitMovement
    WaitCry
    Message Route214_Text_EchoSkarmory
    WaitABXPadPress
    CloseMessage
    PlayCry SPECIES_SKARMORY
    ApplyMovement ROUTE214_ECHO_SKARMORY, Route214_Movement_EchoThrash
    WaitMovement
    WaitCry
    Message Route214_Text_EchoKnown
    WaitABXPadPress
    CloseMessage
    // It fades; the ghosts go and the opacity is back to 0 before the player moves again
    Call Route214_EchoFadeOut
    RemoveObject ROUTE214_ECHO_CRATE
    RemoveObject ROUTE214_ECHO_GRUNT_M
    RemoveObject ROUTE214_ECHO_GRUNT_F
    RemoveObject ROUTE214_ECHO_TEAR
    RemoveObject ROUTE214_ECHO_SKARMORY
    SetFlag FLAG_UNK_0x0018
    SetVar VAR_MAP_LOCAL_5, 0
    WaitTime 2, VAR_RESULT
    SetFlag FLAG_ARC2_ECHO_ROUTE214
    Message Route214_Text_EchoFade
    WaitABXPadPress
    CloseMessage
    Return

Route214_EchoFadeIn:
    AddVar VAR_MAP_LOCAL_5, 1
    WaitTime 1, VAR_RESULT
    GoToIfLt VAR_MAP_LOCAL_5, ROUTE214_ECHO_OPACITY, Route214_EchoFadeIn
    Return

Route214_EchoFadeOut:
    SubVar VAR_MAP_LOCAL_5, 1
    WaitTime 1, VAR_RESULT
    GoToIfGt VAR_MAP_LOCAL_5, 1, Route214_EchoFadeOut
    Return

// ------------------------------------------------------------------------------------------------ movements
    .balign 4, 0
Route214_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
Route214_Movement_StepEast:
    WalkNormalEast
    EndMovement

    .balign 4, 0
Route214_Movement_StepWest:
    WalkNormalWest
    EndMovement

    .balign 4, 0
Route214_Movement_StepNorth:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
Route214_Movement_StepSouth:
    WalkNormalSouth
    EndMovement

    .balign 4, 0
Route214_Movement_CompanionWalkIn:
    WalkNormalEast 7
    FaceEast
    EndMovement

    .balign 4, 0
Route214_Movement_GruntNotice:
    FaceWest
    EmoteExclamationMark
    Delay8
    EndMovement

    .balign 4, 0
Route214_Movement_GruntFleeSouthF:
    WalkFastSouth 9
    EndMovement

    .balign 4, 0
Route214_Movement_GruntFleeSouthM:
    Delay8
    WalkFastSouth 10
    EndMovement

    .balign 4, 0
Route214_Movement_EchoThrash:
    JumpOnSpotFastSouth
    Delay4
    JumpOnSpotFastSouth
    EndMovement
