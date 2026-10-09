#include "macros/scrcmd.inc"
#include "res/text/bank/route_203.h"


    ScriptEntry _001A
    ScriptEntry _002D
    ScriptEntry _0044
    ScriptEntry _005B
    ScriptEntry _0070
    ScriptEntry _0085
    ScriptEntryEnd

_001A:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 2
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_002D:
    ShowArrowSign 3
    End

_0044:
    ShowArrowSign 4
    End

_005B:
    ShowScrollingSign 5
    End

_0070:
    ShowScrollingSign 6
    End

_0085:
    LockAll
    ApplyMovement 5, _0268
    WaitMovement
    SetRivalBGM
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 0x2F5, _00D1
    GoToIfEq VAR_0x8005, 0x2F6, _00E1
    GoToIfEq VAR_0x8005, 0x2F7, _00F1
    GoToIfEq VAR_0x8005, 0x2F8, _0101
    End

_00D1:
    ApplyMovement 5, _0230
    WaitMovement
    GoTo _0111

_00E1:
    ApplyMovement 5, _0238
    WaitMovement
    GoTo _0111

_00F1:
    ApplyMovement 5, _0248
    WaitMovement
    GoTo _0111

_0101:
    ApplyMovement 5, _0258
    WaitMovement
    GoTo _0111

_0111:
    BufferRivalName 0
    BufferPlayerName 1
    Message Route203_Text_Arc1RematchRightNow
    WaitABXPadPress
    CloseMessage
    GetPlayerStarterSpecies VAR_RESULT
    GoToIfEq VAR_RESULT, SPECIES_TURTWIG, _014C
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, _0158
    GoTo _0140

_0140:
    StartTrainerBattle TRAINER_RIVAL_ROUTE_203_PIPLUP
    GoTo _0164

_014C:
    StartTrainerBattle TRAINER_RIVAL_ROUTE_203_TURTWIG
    GoTo _0164

_0158:
    StartTrainerBattle TRAINER_RIVAL_ROUTE_203_CHIMCHAR
    GoTo _0164

_0164:
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _0207
    // Dazzling Platinum Arc 1 (scene 12): Garius asks about the Eclipse broadcast. He doesn't really hear
    // either answer.
    BufferRivalName 0
    Message Route203_Text_Arc1ThatEclipseGuy
    ShowYesNoMenu VAR_RESULT
    BufferRivalName 0
    CallIfEq VAR_RESULT, MENU_YES, Route203_Arc1AnswerYes
    CallIfEq VAR_RESULT, MENU_NO, Route203_Arc1AnswerNo
    BufferRivalName 0
    Message Route203_Text_Arc1RaceYouToOreburgh
    WaitABXPadPress
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 0x2F5, _01B9
    GoToIfEq VAR_0x8005, 0x2F6, _01C9
    GoToIfEq VAR_0x8005, 0x2F7, _01D9
    GoToIfEq VAR_0x8005, 0x2F8, _01E9
    End

_01B9:
    ApplyMovement 5, _0210
    WaitMovement
    GoTo _01F9

_01C9:
    ApplyMovement 5, _0218
    WaitMovement
    GoTo _01F9

_01D9:
    ApplyMovement 5, _0220
    WaitMovement
    GoTo _01F9

_01E9:
    ApplyMovement 5, _0228
    WaitMovement
    GoTo _01F9

_01F9:
    RemoveObject 5
    SetVar VAR_UNK_0x4088, 1
    SetVar VAR_ARC1_PROGRESS, 14 /* Route 203 battle done, heading to Oreburgh */
    ReleaseAll
    End

Route203_Arc1AnswerYes:
    Message Route203_Text_Arc1YeahMaybe
    Return

Route203_Arc1AnswerNo:
    Message Route203_Text_Arc1YeahProbablyNot
    Return

_0207:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
_0210:
    WalkFastEast 10
    EndMovement

    .balign 4, 0
_0218:
    WalkFastEast 10
    EndMovement

    .balign 4, 0
_0220:
    WalkFastEast 10
    EndMovement

    .balign 4, 0
_0228:
    WalkFastEast 10
    EndMovement

    .balign 4, 0
_0230:
    WalkFastWest 4
    EndMovement

    .balign 4, 0
_0238:
    WalkFastWest 2
    WalkFastSouth
    WalkFastWest 2
    EndMovement

    .balign 4, 0
_0248:
    WalkFastWest 2
    WalkFastSouth 2
    WalkFastWest 2
    EndMovement

    .balign 4, 0
_0258:
    WalkFastWest 2
    WalkFastSouth 3
    WalkFastWest 2
    EndMovement

    .balign 4, 0
_0268:
    Delay8
    EmoteExclamationMark
    Delay8
    EndMovement
