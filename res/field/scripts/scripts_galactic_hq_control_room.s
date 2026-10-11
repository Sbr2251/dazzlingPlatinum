#include "macros/scrcmd.inc"
#include "res/text/bank/galactic_hq_control_room.h"
#include "res/field/events/events_galactic_hq_control_room.h"

// Dazzling Platinum Arc 2 (s-cutaways): this room is the "violet room" for the Team Eclipse cutaways 2.4 and 2.13
// (docs/arc2/cutaways.md is the caller contract). The caller is identified by VAR_ARC2_PROGRESS alone:
//   5  (from s-jubilife, after Cyrus battle 1): 2.4, Kahn and Indra. Sets 9, returns to Jubilife 168,777 facing south.
//   35 (from s-eterna, after the Haven): 2.13, Saros and Kahn. Sets 39, returns to Eterna 305,520 facing south.
// The caller fades to black and does `Warp MAP_HEADER_GALACTIC_HQ_CONTROL_ROOM, 0, 8, 9, DIR_NORTH`, then ReleaseAll and
// End WITHOUT fading back in. OnResume hides the player (before the screen shows); the on-frame scene
// (scripts_init_galactic_hq_control_room.s) fades in, plays, sets the next value, warps back and fades in there.
// Never use PlaySound here: it pauses the music, and the return Warp then never finishes (black screen).
// Flags: none of s-cutaways' FLAG_UNK_0x0934-0x0935 are used. Map-local hide flags (cleared on every map load,
// so OnTransition sets them again): FLAG_UNK_0x0030 = hide LOCALID_ARC2_KAHN, FLAG_UNK_0x0031 = hide
// LOCALID_ARC2_INDRA, FLAG_UNK_0x0032 = hide LOCALID_ARC2_SAROS. In a cutaway state the stock Saturn, Charon and
// lake trio are hidden by setting their stock flags; their old values are kept in VAR_MAP_LOCAL_5-7 and put back
// before the return warp, so the stock Galactic HQ scenes are untouched.


    ScriptEntry _003E
    ScriptEntry _0055
    ScriptEntry _0059
    ScriptEntry _014C
    ScriptEntry _0173
    ScriptEntry _019A
    ScriptEntry _01C1
    ScriptEntry _01C3
    ScriptEntry _01C5
    ScriptEntry _01C7
    ScriptEntry _03C4
    ScriptEntry _03D7
    ScriptEntry _03EA
    ScriptEntry _0394
    ScriptEntry _03FD
    ScriptEntry GalacticHQControlRoom_Arc2Cutaway24
    ScriptEntry GalacticHQControlRoom_Arc2Cutaway213
    ScriptEntryEnd

_003E:
    Call GalacticHQControlRoom_Arc2OnTransition
    GoToIfSet FLAG_FREED_GALACTIC_HQ_POKEMON, _004B
    End

_004B:
    SetObjectEventPos 0, 9, 6
    End

_0055:
    CallIfEq VAR_ARC2_PROGRESS, 5, GalacticHQControlRoom_Arc2HidePlayer
    CallIfEq VAR_ARC2_PROGRESS, 35, GalacticHQControlRoom_Arc2HidePlayer
    ScrCmd_25E
    End

_0059:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_FREED_GALACTIC_HQ_POKEMON, _0109
    GoToIfSet FLAG_UNK_0x00AD, _0114
    Message 0
    CloseMessage
    StartTrainerBattle TRAINER_COMMANDER_SATURN_GALACTIC_HQ
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _011F
    SetFlag FLAG_UNK_0x00AD
    SetVar VAR_UNK_0x410D, 1
    Message 1
    CloseMessage
    GetPlayerDir VAR_0x8004
    SetVar VAR_MAP_LOCAL_2, VAR_0x8004
    GoToIfEq VAR_0x8004, 0, _00D5
    GoToIfEq VAR_0x8004, 2, _00E5
    GoToIfEq VAR_0x8004, 3, _00F5
    End

_00D5:
    ApplyMovement 0, _0128
    WaitMovement
    GoTo _0105

_00E5:
    ApplyMovement 0, _0134
    WaitMovement
    GoTo _0105

_00F5:
    ApplyMovement 0, _0140
    WaitMovement
    GoTo _0105

_0105:
    ReleaseAll
    End

_0109:
    Message 3
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0114:
    Message 2
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_011F:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
_0128:
    WalkNormalEast
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0134:
    WalkNormalSouth
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0140:
    WalkNormalEast
    WalkOnSpotNormalWest
    EndMovement

_014C:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfSet FLAG_FREED_GALACTIC_HQ_POKEMON, _0168
    Message 13
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0168:
    Message 16
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0173:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfSet FLAG_FREED_GALACTIC_HQ_POKEMON, _018F
    Message 14
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_018F:
    Message 17
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_019A:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfSet FLAG_FREED_GALACTIC_HQ_POKEMON, _01B6
    Message 15
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_01B6:
    Message 18
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_01C1:
    End

_01C3:
    End

_01C5:
    End

_01C7:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfSet FLAG_FREED_GALACTIC_HQ_POKEMON, _0347
    Message 10
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _01FB
    GoToIfEq VAR_RESULT, MENU_NO, _0341
    End

_01FB:
    SetVar VAR_UNK_0x410D, 0
    PlayFanfare SEQ_SE_DP_BUTTON3
    BufferPlayerName 0
    Message 11
    CloseMessage
    ClearFlag FLAG_UNK_0x0295
    SetFlag FLAG_FREED_GALACTIC_HQ_POKEMON
    ScrCmd_25F
    WaitTime 30, VAR_RESULT
    ApplyMovement 2, _036C
    ApplyMovement 1, _0374
    ApplyMovement 3, _037C
    WaitMovement
    SetObjectEventPos 2, 2, 6
    SetObjectEventPos 1, 14, 6
    SetObjectEventPos 3, 8, 12
    Call _0296
    Call _0296
    Call _0296
    RemoveObject 2
    RemoveObject 1
    RemoveObject 3
    GoToIfEq VAR_MAP_LOCAL_2, 0, _02C0
    GoToIfEq VAR_MAP_LOCAL_2, 2, _02DA
    GoToIfEq VAR_MAP_LOCAL_2, 3, _02F4
    End

_0296:
    RemoveObject 2
    RemoveObject 1
    RemoveObject 3
    WaitTime 2, VAR_RESULT
    ClearFlag FLAG_UNK_0x0236
    AddObject 2
    AddObject 1
    AddObject 3
    WaitTime 2, VAR_RESULT
    Return

_02C0:
    ApplyMovement 0, _0354
    ApplyMovement LOCALID_PLAYER, _0384
    WaitMovement
    GoTo _030E
    End

_02DA:
    ApplyMovement 0, _0360
    ApplyMovement LOCALID_PLAYER, _038C
    WaitMovement
    GoTo _030E
    End

_02F4:
    ApplyMovement 0, _0354
    ApplyMovement LOCALID_PLAYER, _0384
    WaitMovement
    GoTo _030E
    End

_030E:
    Message 3
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    RemoveObject 0
    FadeScreenIn
    WaitFadeScreen
    SetFlag FLAG_UNK_0x0235
    ClearFlag FLAG_UNK_0x0182
    SetVar VAR_UNK_0x40A9, 1
    ReleaseAll
    End

_0341:
    CloseMessage
    ReleaseAll
    End

_0347:
    Message 12
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
_0354:
    Delay8
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0360:
    Delay8
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_036C:
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
_0374:
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
_037C:
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
_0384:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_038C:
    WalkOnSpotNormalSouth
    EndMovement

_0394:
    LockAll
    ApplyMovement 0, _03BC
    WaitMovement
    Message 4
    CloseMessage
    ApplyMovement LOCALID_PLAYER, _03B4
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
_03B4:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
_03BC:
    WalkOnSpotNormalSouth
    EndMovement

_03C4:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 13
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_03D7:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 14
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_03EA:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 15
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_03FD:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    GoToIfSet FLAG_UNK_0x00AD, _0450
    ApplyMovement 4, _0470
    WaitMovement
    Message 5
    CloseMessage
    ApplyMovement 0, _0460
    WaitMovement
    WaitTime 20, VAR_RESULT
    Message 6
    Message 7
    CloseMessage
    WaitTime 20, VAR_RESULT
    ApplyMovement 0, _0468
    WaitMovement
    Message 8
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0450:
    FacePlayer
    Message 9
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
_0460:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0468:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0470:
    WalkOnSpotNormalNorth
    EndMovement

GalacticHQControlRoom_Arc2OnTransition:
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    SetFlag FLAG_UNK_0x0032
    GoToIfEq VAR_ARC2_PROGRESS, 5, GalacticHQControlRoom_Arc2SetUp24
    GoToIfEq VAR_ARC2_PROGRESS, 35, GalacticHQControlRoom_Arc2SetUp213
    Return

GalacticHQControlRoom_Arc2SetUp24:
    Call GalacticHQControlRoom_Arc2HideStock
    ClearFlag FLAG_UNK_0x0030
    ClearFlag FLAG_UNK_0x0031
    Return

GalacticHQControlRoom_Arc2SetUp213:
    Call GalacticHQControlRoom_Arc2HideStock
    ClearFlag FLAG_UNK_0x0030
    ClearFlag FLAG_UNK_0x0032
    Return

GalacticHQControlRoom_Arc2HideStock:
    SetVar VAR_MAP_LOCAL_5, 0
    SetVar VAR_MAP_LOCAL_6, 0
    SetVar VAR_MAP_LOCAL_7, 0
    CallIfSet FLAG_UNK_0x0236, GalacticHQControlRoom_Arc2Keep0236
    CallIfSet FLAG_UNK_0x0237, GalacticHQControlRoom_Arc2Keep0237
    CallIfSet FLAG_UNK_0x029E, GalacticHQControlRoom_Arc2Keep029E
    SetFlag FLAG_UNK_0x0236
    SetFlag FLAG_UNK_0x0237
    SetFlag FLAG_UNK_0x029E
    Return

GalacticHQControlRoom_Arc2Keep0236:
    SetVar VAR_MAP_LOCAL_5, 1
    Return

GalacticHQControlRoom_Arc2Keep0237:
    SetVar VAR_MAP_LOCAL_6, 1
    Return

GalacticHQControlRoom_Arc2Keep029E:
    SetVar VAR_MAP_LOCAL_7, 1
    Return

GalacticHQControlRoom_Arc2RestoreStock:
    CallIfEq VAR_MAP_LOCAL_5, 0, GalacticHQControlRoom_Arc2Clear0236
    CallIfEq VAR_MAP_LOCAL_6, 0, GalacticHQControlRoom_Arc2Clear0237
    CallIfEq VAR_MAP_LOCAL_7, 0, GalacticHQControlRoom_Arc2Clear029E
    Return

GalacticHQControlRoom_Arc2Clear0236:
    ClearFlag FLAG_UNK_0x0236
    Return

GalacticHQControlRoom_Arc2Clear0237:
    ClearFlag FLAG_UNK_0x0237
    Return

GalacticHQControlRoom_Arc2Clear029E:
    ClearFlag FLAG_UNK_0x029E
    Return

// OnResume (every field load, before the screen is shown): the player is in the room but not in the scene
GalacticHQControlRoom_Arc2HidePlayer:
    HideObject LOCALID_PLAYER
    Return

// Lift the caller's black screen
GalacticHQControlRoom_Arc2EnterScene:
    FadeScreenIn
    WaitFadeScreen
    WaitTime 20, VAR_RESULT
    // The Eclipse Shard on the console pulses
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitTime 20, VAR_RESULT
    Return

GalacticHQControlRoom_Arc2LeaveScene:
    WaitTime 30, VAR_RESULT
    FadeScreenOut
    WaitFadeScreen
    Call GalacticHQControlRoom_Arc2RestoreStock
    Return

// 2.4 Cutaway: Team Eclipse (Kahn, Indra). Never show who sent the message.
GalacticHQControlRoom_Arc2Cutaway24:
    LockAll
    Call GalacticHQControlRoom_Arc2EnterScene
    Message GalacticHQControlRoom_Text_Arc2KahnWordFromOurNewFriend
    Message GalacticHQControlRoom_Text_Arc2KahnAManWhoWalkedOut
    Message GalacticHQControlRoom_Text_Arc2IndraOutOfIt
    Message GalacticHQControlRoom_Text_Arc2KahnSomethingStoppedHim
    Message GalacticHQControlRoom_Text_Arc2IndraFindOutWhat
    Message GalacticHQControlRoom_Text_Arc2KahnFirstLight
    Message GalacticHQControlRoom_Text_Arc2IndraBeThereFirst
    WaitABXPadPress
    CloseMessage
    // Indra turns away from the table
    ApplyMovement LOCALID_ARC2_INDRA, GalacticHQControlRoom_Arc2Movement_TurnAway
    WaitMovement
    Call GalacticHQControlRoom_Arc2LeaveScene
    SetVar VAR_ARC2_PROGRESS, 9
    Warp MAP_HEADER_JUBILIFE_CITY, 0, 168, 777, DIR_SOUTH
    GoTo GalacticHQControlRoom_Arc2Returned
    End

// 2.13 Cutaway: Team Eclipse (Saros, Kahn). Never show who the friend is.
GalacticHQControlRoom_Arc2Cutaway213:
    LockAll
    Call GalacticHQControlRoom_Arc2EnterScene
    Message GalacticHQControlRoom_Text_Arc2SarosTheHavenIsGone
    Message GalacticHQControlRoom_Text_Arc2KahnOtherWaysToFillTheCrates
    Message GalacticHQControlRoom_Text_Arc2SarosWeDidntSeeItComing
    Message GalacticHQControlRoom_Text_Arc2KahnOurFriendWasntTold
    Message GalacticHQControlRoom_Text_Arc2SarosIllGoMyself
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC2_SAROS, GalacticHQControlRoom_Arc2Movement_TurnAway
    WaitMovement
    Call GalacticHQControlRoom_Arc2LeaveScene
    SetVar VAR_ARC2_PROGRESS, 39
    Warp MAP_HEADER_ETERNA_CITY, 0, 305, 520, DIR_SOUTH
    GoTo GalacticHQControlRoom_Arc2Returned
    End

// After the Warp the script runs on in the caller's map (the player object is new, so visible again): fade in
GalacticHQControlRoom_Arc2Returned:
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
GalacticHQControlRoom_Arc2Movement_TurnAway:
    WalkOnSpotNormalSouth
    EndMovement
