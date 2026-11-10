#include "macros/scrcmd.inc"
#include "res/text/bank/route_204_south.h"
#include "res/field/maps/locals/route_204_south.h"

// fix2 (playtest round 2): Route 204 stays shut until the first Gym Leader is beaten. A worker (map-local hide
// flag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16) stands in the 4-wide mouth at the Jubilife end, and a coord trigger on the row in front of
// him (x172-175, z734; VAR_MAP_LOCAL_0x01 == 0) turns the player back. OnTransition writes the Coal Badge check into
// VAR_MAP_LOCAL_0x01 (VAR_RESULT in OnTransition hangs the map load) and hides the worker once the badge is won; the
// trigger script checks the badge again itself. Arc 2 only runs after the badge, so none of its scenes see him.
#define FLAG_HIDE_ROUTE204S_BLOCK_GUARD FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
#define VAR_ROUTE204S_HAS_COAL_BADGE    VAR_MAP_LOCAL_0x01


    ScriptEntry Route204South_Youngster
    ScriptEntry Route204South_ArrowSignpostJubilifeCity
    ScriptEntry Route204South_SignboardRavagedPath
    ScriptEntry Route204South_BlockGuard
    ScriptEntry Route204South_BlockTurnBack
    ScriptEntry Route204South_OnTransition
    ScriptEntryEnd

Route204South_Youngster:
    NPCMessage Route204South_Text_BouldersBlockingInsideCavern
    End

Route204South_ArrowSignpostJubilifeCity:
    ShowArrowSign Route204South_Text_SignJubilifeCity
    End

Route204South_SignboardRavagedPath:
    ShowLandmarkSign Route204South_Text_SignRavagedPath
    End

Route204South_OnTransition:
    CheckBadgeAcquired BADGE_ID_COAL, VAR_ROUTE204S_HAS_COAL_BADGE
    ClearFlag FLAG_HIDE_ROUTE204S_BLOCK_GUARD
    CallIfEq VAR_ROUTE204S_HAS_COAL_BADGE, TRUE, Route204South_HideBlockGuard
    End

Route204South_HideBlockGuard:
    SetFlag FLAG_HIDE_ROUTE204S_BLOCK_GUARD
    Return

Route204South_BlockGuard:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message Route204South_Text_BlockGuard
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

Route204South_BlockTurnBack:
    LockAll
    GoToIfBadgeAcquired BADGE_ID_COAL, Route204South_BlockOpen
    ApplyMovement LOCALID_ROUTE204S_BLOCK_GUARD, Route204South_Movement_GuardNotice
    WaitMovement
    Message Route204South_Text_BlockGuard
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, Route204South_Movement_PlayerTurnBack
    WaitMovement
    ReleaseAll
    End

Route204South_BlockOpen:
    SetVar VAR_ROUTE204S_HAS_COAL_BADGE, TRUE
    ReleaseAll
    End

    .balign 4, 0
Route204South_Movement_GuardNotice:
    FaceSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
Route204South_Movement_PlayerTurnBack:
    WalkNormalSouth
    FaceNorth
    EndMovement
