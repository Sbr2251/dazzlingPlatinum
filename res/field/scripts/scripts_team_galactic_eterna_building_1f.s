#include "macros/scrcmd.inc"
#include "generated/distribution_events.h"
#include "res/text/bank/team_galactic_eterna_building_1f.h"
#include "res/field/events/events_team_galactic_eterna_building_1f.h"

// Dazzling Platinum Arc 2 (s-eterna, screenplay 2.12): the stock Galactic Eterna building is the Eclipse Haven.
// 1F lobby. At VAR_ARC2_PROGRESS 33 the lobby scene runs on entry (receptionist, Looker the janitor) and sets 34.
// The main route up is the east stairs; Gardenia and Ruth wait on 2F. Stock Galactic grunts, trainers and the
// stock Looker door scene (VAR_UNK_0x411D) are removed. The Rotom room wall (Secret Key) is stock.
// Map-local hide flags: 0x30 receptionist, 0x31 Looker, 0x32 Gardenia, 0x33 Ruth (all only at 33).
// Flags and the progress ladder: see the header of scripts_eterna_city.s.

    ScriptEntry Haven1F_Receptionist
    ScriptEntry Haven1F_Looker
    ScriptEntry Haven1F_Sign
    ScriptEntry Haven1F_LobbyScene
    ScriptEntry Haven1F_RotomWall
    ScriptEntry Haven1F_OnTransition
    ScriptEntryEnd

Haven1F_OnTransition:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (Arc 1 D1) */
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    SetFlag FLAG_UNK_0x0032
    SetFlag FLAG_UNK_0x0033
    GoToIfNe VAR_ARC2_PROGRESS, 33, Haven1F_OnTransitionEnd
    ClearFlag FLAG_UNK_0x0030
    ClearFlag FLAG_UNK_0x0031
    ClearFlag FLAG_UNK_0x0032
    ClearFlag FLAG_UNK_0x0033
Haven1F_OnTransitionEnd:
    End

Haven1F_Receptionist:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message Haven1F_Text_ReceptionistAfter
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Haven1F_Looker:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message Haven1F_Text_LookerServiceDoor
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Haven1F_Sign:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message Haven1F_Text_Sign
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// 33: the player has just come in the front door (11,15).
Haven1F_LobbyScene:
    LockAll
    ApplyMovement LOCALID_PLAYER, Haven1F_Movement_FaceNorth
    WaitMovement
    Message Haven1F_Text_ReceptionistNoVisitors
    Message Haven1F_Text_GardeniaAlwaysResting
    CloseMessage
    WaitTime 20, VAR_RESULT
    ApplyMovement HAVEN_1F_LOOKER, Haven1F_Movement_LookerEdgeOver
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Haven1F_Movement_FaceWest
    WaitMovement
    GoToIfSet FLAG_UNK_0x091C, Haven1F_LookerRemembers
    Message Haven1F_Text_JanitorPokedex
    GoTo Haven1F_LookerIntroduces

Haven1F_LookerRemembers:
    Message Haven1F_Text_JanitorCrates
Haven1F_LookerIntroduces:
    Message Haven1F_Text_JanitorIAmLooker
    Message Haven1F_Text_LookerServiceDoor
    WaitABXPadPress
    CloseMessage
    ApplyMovement HAVEN_1F_LOOKER, Haven1F_Movement_LookerLeave
    WaitMovement
    RemoveObject HAVEN_1F_LOOKER
    WaitTime 15, VAR_RESULT
    // Five minutes later: the receptionist has stepped away; Gardenia and Ruth slip upstairs ahead (2F).
    FadeScreenOut
    WaitFadeScreen
    RemoveObject HAVEN_1F_RECEPTIONIST
    RemoveObject HAVEN_1F_GARDENIA
    RemoveObject HAVEN_1F_RUTH
    SetVar VAR_ARC2_PROGRESS, 34
    WaitTime 30, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
Haven1F_Movement_FaceNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
Haven1F_Movement_FaceWest:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
Haven1F_Movement_LookerEdgeOver:
    WalkSlowEast 3
    EndMovement

    .balign 4, 0
Haven1F_Movement_LookerLeave:
    WalkNormalWest 4
    WalkNormalNorth 2
    EndMovement

Haven1F_RotomWall:
    CheckItem ITEM_SECRET_KEY, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Haven1F_RotomWallEnd
    CheckDistributionEvent DISTRIBUTION_EVENT_ROTOM, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Haven1F_RotomWallEnd
    GoToIfUnset FLAG_UNK_0x0081, Haven1F_RotomWallEnd
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    BufferPlayerName 0
    BufferItemName 1, 0x1D3
    Message Haven1F_Text_UsedSecretKey
    CloseMessage
    PlayFanfare SEQ_SE_DP_W062
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    RemoveObject HAVEN_1F_WALL_BLOCKING_ROTOMS_ROOM
    WaitFanfare SEQ_SE_DP_W062
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    Message Haven1F_Text_SecretRoom
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Haven1F_RotomWallEnd:
    End
