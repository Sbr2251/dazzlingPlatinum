#include "macros/scrcmd.inc"
#include "res/text/bank/route_203.h"
#include "res/field/maps/locals/route_203.h"


    ScriptEntry Route203_Lass
    ScriptEntry Route203_ArrowSignpostJubilifeCity
    ScriptEntry Route203_ArrowSignpostOreburghCity
    ScriptEntry Route203_TrainerTipsSignpostEast
    ScriptEntry Route203_TrainerTipsSignpostWest
    ScriptEntry Route203_CoordEvent_Rival
    ScriptEntry Route203_Hiker
    ScriptEntry Route203_Picnicker
    ScriptEntry Route203_StarlyFlee
    ScriptEntry Route203_OnTransition
    ScriptEntryEnd

Route203_Lass:
    NPCMessage Route203_Text_FavoritePokemonAtTheTop
    End

Route203_ArrowSignpostJubilifeCity:
    ShowArrowSign Route203_Text_SignJubilifeCity
    End

Route203_ArrowSignpostOreburghCity:
    ShowArrowSign Route203_Text_SignOreburghCity
    End

Route203_TrainerTipsSignpostEast:
    ShowScrollingSign Route203_Text_TrainerTipsEvolveCanBeStopped
    End

Route203_TrainerTipsSignpostWest:
    ShowScrollingSign Route203_Text_TrainerTipsMovesUsePowerPoints
    End

// Dazzling Platinum Arc 1 (scene 12), round 3: the battle moved to the scar. Garius (local 5) stands at the
// fissure's tip (211,747), looking into it. The coord trigger is the only gap past the scar, x 210 z 744..745
// (tools/route_203/scar_layout.py), so it can't be skipped.
Route203_CoordEvent_Rival:
    LockAll
    ApplyMovement LOCALID_PLAYER, Route203_Movement_PlayerFaceEast
    ApplyMovement LOCALID_RIVAL, Route203_Movement_RivalNoticePlayer
    WaitMovement
    CallCommonScript CommonScript_SetRivalBGM
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 744, Route203_GariusApproachNorthRow
    GoTo Route203_GariusApproachSouthRow
    End

Route203_GariusApproachNorthRow:
    ApplyMovement LOCALID_RIVAL, Route203_Movement_GariusApproachNorthRow
    WaitMovement
    GoTo Route203_GariusAtTheCrack

Route203_GariusApproachSouthRow:
    ApplyMovement LOCALID_RIVAL, Route203_Movement_GariusApproachSouthRow
    WaitMovement
    GoTo Route203_GariusAtTheCrack

Route203_GariusAtTheCrack:
    BufferRivalName 0
    Message Route203_Text_Arc1CheckOutThisCrack
    GoTo Route203_RivalIntro

Route203_RivalIntro:
    BufferRivalName 0
    BufferPlayerName 1
    Message Route203_Text_Arc1RematchRightNow
    WaitABPadPress
    CloseMessage
    GetPlayerStarterSpecies VAR_RESULT
    GoToIfEq VAR_RESULT, SPECIES_TURTWIG, Route203_StartRivalBattleTurtwig
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, Route203_StartRivalBattleChimchar
    GoTo Route203_StartRivalBattlePiplup

Route203_StartRivalBattlePiplup:
    StartTrainerBattle TRAINER_RIVAL_ROUTE_203_PIPLUP
    GoTo Route203_RivalBattleEnd

Route203_StartRivalBattleTurtwig:
    StartTrainerBattle TRAINER_RIVAL_ROUTE_203_TURTWIG
    GoTo Route203_RivalBattleEnd

Route203_StartRivalBattleChimchar:
    StartTrainerBattle TRAINER_RIVAL_ROUTE_203_CHIMCHAR
    GoTo Route203_RivalBattleEnd

Route203_RivalBattleEnd:
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route203_BlackOutRivalBattle
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
    WaitABPadPress
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 744, Route203_RivalLeaveZ757
    GoTo Route203_RivalLeaveZ758
    End

Route203_RivalLeaveZ757:
    ApplyMovement LOCALID_RIVAL, Route203_Movement_RivalLeaveZ757
    WaitMovement
    GoTo Route203_RemoveRival

Route203_RivalLeaveZ758:
    ApplyMovement LOCALID_RIVAL, Route203_Movement_RivalLeaveZ758
    WaitMovement
    GoTo Route203_RemoveRival

Route203_RemoveRival:
    RemoveObject LOCALID_RIVAL
    SetVar VAR_ROUTE_203_RIVAL_STATE, 1
    SetVar VAR_ROUTE_203_RIVAL_STATE, 1
    SetVar VAR_ARC1_PROGRESS, 14 /* Route 203 battle done, heading to Oreburgh */
    ReleaseAll
    End

Route203_Arc1AnswerYes:
    Message Route203_Text_Arc1YeahMaybe
    Return

Route203_Arc1AnswerNo:
    Message Route203_Text_Arc1YeahProbablyNot
    Return

Route203_BlackOutRivalBattle:
    BlackOutFromBattle
    ReleaseAll
    End

// fix2: Garius (local 5, hide flag FLAG_HIDE_ROUTE_203_RIVAL) stands at the scar only until his Route 203 battle. The battle
// hides him with RemoveObject, but a save that reached 14 any other way (the owner's test saves) still had him
// standing there on the walk back. Hide him whenever the battle is done (VAR_ROUTE_203_RIVAL_STATE) or progress is past it.
Route203_OnTransition:
    CallIfNe VAR_ROUTE_203_RIVAL_STATE, 0, Route203_HideGarius
    CallIfGe VAR_ARC1_PROGRESS, 14, Route203_HideGarius
    End

Route203_HideGarius:
    SetFlag FLAG_HIDE_ROUTE_203_RIVAL
    Return

    // Garius runs off: from (211,744) or (211,745), east to x 212, south to the old road (z 757), east up the
    // x 214 stairs and out of sight
    .balign 4, 0
Route203_Movement_RivalLeaveZ757:
    WalkFastEast
    WalkFastSouth 13
    WalkFastEast 4
    EndMovement

    .balign 4, 0
Route203_Movement_RivalLeaveZ758:
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
Route203_Movement_RivalNoticePlayer:
    Delay8
    EmoteExclamationMark
    Delay8
    EndMovement

// The Hiker on the road west of the fallen tree.
Route203_Hiker:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message Route203_Text_HikerOldTree
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

// The Picnicker at the scar's east side.
Route203_Picnicker:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message Route203_Text_PicnickerWontGoNear
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

// Two Starly (locals 17, 18) peck at the scar's west side. The first time the player walks north past z 754 in a
// visit (VAR_MAP_LOCAL_0x00, cleared on every map change), they startle and fly off over the fissure. Their hide flag
// FLAG_MAP_LOCAL_HIDE_OBSTACLE_8 is map-local too, so they are back on the next visit.
Route203_StarlyFlee:
    LockAll
    PlayCry SPECIES_STARLY
    ApplyMovement LOCALID_STARLY_SCAR_1, Route203_Movement_StarlyStartle
    ApplyMovement LOCALID_STARLY_SCAR_2, Route203_Movement_StarlyStartle
    WaitMovement
    ApplyMovement LOCALID_STARLY_SCAR_1, Route203_Movement_Starly1Flee
    ApplyMovement LOCALID_STARLY_SCAR_2, Route203_Movement_Starly2Flee
    WaitMovement
    RemoveObject LOCALID_STARLY_SCAR_1
    RemoveObject LOCALID_STARLY_SCAR_2
    SetVar VAR_MAP_LOCAL_0x00, 1
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
