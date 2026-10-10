#include "macros/scrcmd.inc"
#include "res/text/bank/route_203.h"


    ScriptEntry _001A
    ScriptEntry _002D
    ScriptEntry _0044
    ScriptEntry _005B
    ScriptEntry _0070
    ScriptEntry _0085
    ScriptEntry Route203_Hiker
    ScriptEntry Route203_Picnicker
    ScriptEntry Route203_StarlyFlee
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

// Dazzling Platinum Arc 1 (scene 12), round 3: the battle moved to the scar. Garius (local 5) stands at the
// fissure's tip (211,747), looking into it. The coord trigger is the only gap past the scar, x 210 z 744..745
// (tools/route_203/scar_layout.py), so it can't be skipped.
_0085:
    LockAll
    ApplyMovement LOCALID_PLAYER, Route203_Movement_PlayerFaceEast
    ApplyMovement 5, _0268
    WaitMovement
    SetRivalBGM
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 744, Route203_GariusApproachNorthRow
    GoTo Route203_GariusApproachSouthRow
    End

Route203_GariusApproachNorthRow:
    ApplyMovement 5, Route203_Movement_GariusApproachNorthRow
    WaitMovement
    GoTo Route203_GariusAtTheCrack

Route203_GariusApproachSouthRow:
    ApplyMovement 5, Route203_Movement_GariusApproachSouthRow
    WaitMovement
    GoTo Route203_GariusAtTheCrack

Route203_GariusAtTheCrack:
    BufferRivalName 0
    Message Route203_Text_Arc1CheckOutThisCrack
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
    GoToIfEq VAR_0x8005, 744, _01B9
    GoTo _01C9
    End

_01B9:
    ApplyMovement 5, _0210
    WaitMovement
    GoTo _01F9

_01C9:
    ApplyMovement 5, _0218
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

    // Garius runs off: from (211,744) or (211,745), east to x 212, south to the old road (z 757), east up the
    // x 214 stairs and out of sight
    .balign 4, 0
_0210:
    WalkFastEast
    WalkFastSouth 13
    WalkFastEast 4
    EndMovement

    .balign 4, 0
_0218:
    WalkFastEast
    WalkFastSouth 12
    WalkFastEast 4
    EndMovement

    // Garius walks from the fissure's tip (211,747) up to the player at the gap (210,744 or 210,745)
    .balign 4, 0
Route203_Movement_GariusApproachNorthRow:
    WalkNormalNorth 3
    FaceWest
    EndMovement

    .balign 4, 0
Route203_Movement_GariusApproachSouthRow:
    WalkNormalNorth 2
    FaceWest
    EndMovement

    .balign 4, 0
Route203_Movement_PlayerFaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
_0268:
    Delay8
    EmoteExclamationMark
    Delay8
    EndMovement

// The Hiker on the road west of the fallen tree.
Route203_Hiker:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message Route203_Text_HikerOldTree
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// The Picnicker at the scar's east side.
Route203_Picnicker:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message Route203_Text_PicnickerWontGoNear
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// Two Starly (locals 17, 18) peck at the scar's west side. The first time the player walks north past z 754 in a
// visit (VAR_MAP_LOCAL_0, cleared on every map change), they startle and fly off over the fissure. Their hide flag
// FLAG_UNK_0x0028 is map-local too, so they are back on the next visit.
Route203_StarlyFlee:
    LockAll
    PlayCry SPECIES_STARLY
    ApplyMovement 17, Route203_Movement_StarlyStartle
    ApplyMovement 18, Route203_Movement_StarlyStartle
    WaitMovement
    ApplyMovement 17, Route203_Movement_Starly1Flee
    ApplyMovement 18, Route203_Movement_Starly2Flee
    WaitMovement
    RemoveObject 17
    RemoveObject 18
    SetVar VAR_MAP_LOCAL_0, 1
    ReleaseAll
    End

    .balign 4, 0
Route203_Movement_StarlyStartle:
    EmoteExclamationMark
    JumpOnSpotFastSouth
    EndMovement

    .balign 4, 0
Route203_Movement_Starly1Flee:
    WalkFastestNorth 2
    WalkFastestEast 3
    WalkFastestNorth 7
    EndMovement

    .balign 4, 0
Route203_Movement_Starly2Flee:
    WalkFastestEast 3
    WalkFastestNorth 3
    WalkFastestEast 2
    WalkFastestNorth 6
    EndMovement
