#include "macros/scrcmd.inc"
#include "res/text/bank/route_209.h"
#include "res/field/events/events_route_209.h"


    ScriptEntry _0091
    ScriptEntry _00A4
    ScriptEntry _0270
    ScriptEntry _0287
    ScriptEntry _01C7
    ScriptEntry _02B3
    ScriptEntry _02C6
    ScriptEntry _0026
    ScriptEntry _029E
    ScriptEntry Route209_OnTransition
    ScriptEntry Route209_Arc2Aftermath
    ScriptEntryEnd

// Dazzling Platinum Arc 2, s-hearthome (2.26 aftermath, END OF ARC 2). rift-b's second-visit exit from
// DW_LOST_TOWER lands outside the Lost Tower door (568,681 facing south) with progress 95 (Spiritomb calm).
// Map-local: FLAG_UNK_0x0030 hides Rowan and Cyrus (shown at 95 only), FLAG_UNK_0x0031 hides Looker and Garius
// (added by the scene). Sets 99. Cyrus's extra line plays only if VAR_ARC2_CHOICES bit 3 (2.17c crate seen) is set.
Route209_OnTransition:
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    CallIfEq VAR_ARC2_PROGRESS, 95, Route209_ShowAftermath
    GoTo _0026
    End

Route209_ShowAftermath:
    ClearFlag FLAG_UNK_0x0030
    Return

Route209_Arc2Aftermath:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8005, 681, Route209_PlayerStepsOut
    ApplyMovement LOCALID_PLAYER, Route209_Movement_FaceSouth
    WaitMovement
    WaitTime 30, VAR_RESULT
    ApplyMovement ROUTE_209_PROF_ROWAN, Route209_Movement_FaceEast
    WaitMovement
    Message Route209_Text_RowanDoubted
    WaitABXPadPress
    CloseMessage
    ApplyMovement ROUTE_209_CYRUS, Route209_Movement_FaceWest
    WaitMovement
    Message Route209_Text_CyrusRightTo
    WaitABXPadPress
    CloseMessage
    // Looker steps out from behind the tower.
    ClearFlag FLAG_UNK_0x0031
    AddObject ROUTE_209_LOOKER
    ApplyMovement ROUTE_209_LOOKER, Route209_Movement_LookerWalksIn
    WaitMovement
    ApplyMovement ROUTE_209_PROF_ROWAN, Route209_Movement_FaceEast
    ApplyMovement ROUTE_209_CYRUS, Route209_Movement_FaceEast
    WaitMovement
    Message Route209_Text_LookerNeverHere
    WaitABXPadPress
    Message Route209_Text_LookerCrates
    WaitABXPadPress
    CloseMessage
    ApplyMovement ROUTE_209_LOOKER, Route209_Movement_FaceNorthWest
    WaitMovement
    Message Route209_Text_LookerKnowWho
    WaitABXPadPress
    CloseMessage
    SetVarFromVar VAR_0x8008, VAR_ARC2_CHOICES
    GoToIfLt VAR_0x8008, 32768, Route209_Bit3_32768
    SubVar VAR_0x8008, 32768
Route209_Bit3_32768:
    GoToIfLt VAR_0x8008, 16384, Route209_Bit3_16384
    SubVar VAR_0x8008, 16384
Route209_Bit3_16384:
    GoToIfLt VAR_0x8008, 8192, Route209_Bit3_8192
    SubVar VAR_0x8008, 8192
Route209_Bit3_8192:
    GoToIfLt VAR_0x8008, 4096, Route209_Bit3_4096
    SubVar VAR_0x8008, 4096
Route209_Bit3_4096:
    GoToIfLt VAR_0x8008, 2048, Route209_Bit3_2048
    SubVar VAR_0x8008, 2048
Route209_Bit3_2048:
    GoToIfLt VAR_0x8008, 1024, Route209_Bit3_1024
    SubVar VAR_0x8008, 1024
Route209_Bit3_1024:
    GoToIfLt VAR_0x8008, 512, Route209_Bit3_512
    SubVar VAR_0x8008, 512
Route209_Bit3_512:
    GoToIfLt VAR_0x8008, 256, Route209_Bit3_256
    SubVar VAR_0x8008, 256
Route209_Bit3_256:
    GoToIfLt VAR_0x8008, 128, Route209_Bit3_128
    SubVar VAR_0x8008, 128
Route209_Bit3_128:
    GoToIfLt VAR_0x8008, 64, Route209_Bit3_64
    SubVar VAR_0x8008, 64
Route209_Bit3_64:
    GoToIfLt VAR_0x8008, 32, Route209_Bit3_32
    SubVar VAR_0x8008, 32
Route209_Bit3_32:
    GoToIfLt VAR_0x8008, 16, Route209_Bit3_16
    SubVar VAR_0x8008, 16
Route209_Bit3_16:
    GoToIfLt VAR_0x8008, 8, Route209_LookerLeaves
    Message Route209_Text_CyrusToldYou
    WaitABXPadPress
    CloseMessage
Route209_LookerLeaves:
    ApplyMovement ROUTE_209_LOOKER, Route209_Movement_LookerLeaves
    WaitMovement
    RemoveObject ROUTE_209_LOOKER
    // Garius walks up from the Hearthome side, looks at Cyrus, and gives nothing away.
    BufferRivalName 0
    ClearFlag FLAG_UNK_0x0031
    AddObject ROUTE_209_RIVAL_GARIUS
    ApplyMovement ROUTE_209_RIVAL_GARIUS, Route209_Movement_GariusWalksIn
    WaitMovement
    ApplyMovement ROUTE_209_PROF_ROWAN, Route209_Movement_FaceWest
    ApplyMovement ROUTE_209_CYRUS, Route209_Movement_FaceWest
    ApplyMovement LOCALID_PLAYER, Route209_Movement_FaceWest
    WaitMovement
    WaitTime 60, VAR_RESULT
    Message Route209_Text_GariusGuess
    WaitABXPadPress
    CloseMessage
    ApplyMovement ROUTE_209_RIVAL_GARIUS, Route209_Movement_GariusLeaves
    WaitMovement
    RemoveObject ROUTE_209_RIVAL_GARIUS
    WaitTime 30, VAR_RESULT
    FadeScreenOut FADE_SCREEN_SPEED_SLOW
    WaitFadeScreen
    SetVar VAR_ARC2_PROGRESS, 99
    RemoveObject ROUTE_209_PROF_ROWAN
    RemoveObject ROUTE_209_CYRUS
    WaitTime 30, VAR_RESULT
    // Text drawn during a brightness fade is black too, so the end card plays over the emptied tower front.
    FadeScreenIn FADE_SCREEN_SPEED_SLOW
    WaitFadeScreen
    Message Route209_Text_EndOfArc2
    WaitABXPadPress
    Message Route209_Text_ToBeContinued
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Route209_PlayerStepsOut:
    ApplyMovement LOCALID_PLAYER, Route209_Movement_StepSouth
    WaitMovement
    Return

    .balign 4, 0
Route209_Movement_StepSouth:
    WalkNormalSouth
    EndMovement

    .balign 4, 0
Route209_Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
Route209_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
Route209_Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
Route209_Movement_FaceNorthWest:
    FaceNorth
    Delay8
    FaceWest
    EndMovement

    .balign 4, 0
Route209_Movement_LookerWalksIn:
    WalkNormalWest 2
    EndMovement

    .balign 4, 0
Route209_Movement_LookerLeaves:
    WalkFastEast 4
    EndMovement

    .balign 4, 0
Route209_Movement_GariusWalksIn:
    WalkNormalEast 3
    EndMovement

    .balign 4, 0
Route209_Movement_GariusLeaves:
    WalkNormalWest 6
    EndMovement

_0026:
    GetTimeOfDay VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, 0, _006D
    GoToIfEq VAR_MAP_LOCAL_0, 1, _007F
    GoToIfEq VAR_MAP_LOCAL_0, 2, _007F
    GoToIfEq VAR_MAP_LOCAL_0, 3, _007F
    GoToIfEq VAR_MAP_LOCAL_0, 4, _007F
    End

_006D:
    ClearFlag FLAG_UNK_0x026D
    ClearFlag FLAG_UNK_0x026F
    SetFlag FLAG_UNK_0x026C
    SetFlag FLAG_UNK_0x026E
    End

_007F:
    ClearFlag FLAG_UNK_0x026C
    ClearFlag FLAG_UNK_0x026E
    SetFlag FLAG_UNK_0x026D
    SetFlag FLAG_UNK_0x026F
    End

_0091:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00A4:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfEq VAR_UNK_0x408A, 1, _0102
    CheckItem ITEM_ODD_KEYSTONE, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _01BC
    Message 2
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _00E6
    CloseMessage
    ReleaseAll
    End

_00E6:
    BufferPlayerName 0
    Message 3
    WaitABXPadPress
    RemoveItem ITEM_ODD_KEYSTONE, 1, VAR_RESULT
    SetVar VAR_UNK_0x408A, 1
    CloseMessage
    ReleaseAll
    End

_0102:
    GetSpiritombCounter VAR_RESULT
    GoToIfGe VAR_RESULT, 32, _014D
    GoToIfGe VAR_RESULT, 29, _01B1
    GoToIfGe VAR_RESULT, 22, _01A6
    GoToIfGe VAR_RESULT, 15, _019B
    GoToIfGe VAR_RESULT, 8, _0190
    GoTo _0185

_014D:
    WaitFanfare SEQ_SE_CONFIRM
    PlayCry SPECIES_SPIRITOMB
    Message 9
    WaitCry
    CloseMessage
    StartWildBattle SPECIES_SPIRITOMB, 25
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _017F
    SetVar VAR_UNK_0x408A, 0
    ClearSpiritombCounter
    End

_017F:
    BlackOutFromBattle
    ReleaseAll
    End

_0185:
    Message 4
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0190:
    Message 5
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_019B:
    Message 6
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_01A6:
    Message 7
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_01B1:
    Message 8
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_01BC:
    Message 1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_01C7:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    SetVar VAR_0x8004, ITEM_GOOD_ROD
    BufferItemNameWithArticle 0, VAR_0x8004
    CapitalizeFirstLetter 0
    GoToIfSet FLAG_GOOD_ROD_OBTAINED, _020B
    Message 10
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, AcceptGoodRod
    GoToIfEq VAR_RESULT, MENU_NO, RefuseGoodRod
    End

_020B:
    BufferItemName 0, VAR_0x8004
    Message 12
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _0233
    GoToIfEq VAR_RESULT, MENU_NO, _023E
    End

_0233:
    Message 14
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_023E:
    Message 15
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

RefuseGoodRod:
    Message 13
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

AcceptGoodRod:
    BufferItemName 0, VAR_0x8004
    Message 11
    SetVar VAR_0x8005, 1
    GiveItemQuantity
    SetFlag FLAG_GOOD_ROD_OBTAINED
    GoTo _020B

_0270:
    ShowArrowSign 18
    End

_0287:
    ShowArrowSign 19
    End

_029E:
    ShowScrollingSign 20
    End

_02B3:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 16
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_02C6:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 17
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
