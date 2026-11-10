#include "macros/scrcmd.inc"
#include "res/text/bank/valley_windworks_outside.h"
#include "res/field/maps/locals/valley_windworks_outside.h"

// Arc 2 (s-floaroma), scene 2.9 morning. Stock Galactic content is gone: the door guard (local 0) is hidden
// for good by FLAG_MAP_LOCAL_0x3E (map-local temp, set every load), the door is never locked (no Works Key),
// and the stock Looker scene (VAR_UNK_0x411E) is never armed. Ruth (local 8) and Cyrus (local 9) are shown at
// progress 20 only (FLAG_MAP_LOCAL_HIDE_OBSTACLE_16, map-local temp): the frame script walks them in and sets 21.
#define LOCALID_ARC2_RUTH  8
#define LOCALID_ARC2_CYRUS 9


    ScriptEntry ValleyWindworksOutside_OnTransition
    ScriptEntry ValleyWindworksOutside_OnLoad
    ScriptEntry ValleyWindworksOutside_GruntM
    ScriptEntry ValleyWindworksOutside_Door
    ScriptEntry ValleyWindworksOutside_SignboardValleyWindworks
    ScriptEntry ValleyWindworksOutside_Drifloon
    ScriptEntry ValleyWindworksOutside_OnResume
    ScriptEntry ValleyWindworksOutside_OnFrame_Looker
    ScriptEntry ValleyWindworksOutside_Arc2Morning
    ScriptEntryEnd

ValleyWindworksOutside_OnResume:
    End

ValleyWindworksOutside_OnTransition:
    Call ValleyWindworksOutside_Arc2SetObjects
    CallIfEq VAR_VALLEY_WINDWORKS_TEAM_GALACTIC_STATE, 2, ValleyWindworksOutside_IncreaseTeamGalacticValleyWindworksState
    // Arc 2: the door is open (the stock Works Key lock is gone) and Drifloon visits from the cold site on.
    GoToIfLt VAR_ARC2_PROGRESS, 22, ValleyWindworksOutside_HideDrifloon
    GoToIfSet FLAG_DAILY_VISIT_TOMORROW_SUNYSHORE_CITY_NORTHEAST_HOUSE, ValleyWindworksOutside_HideDrifloon
    GetDayOfWeek VAR_MAP_LOCAL_0x00
    GoToIfNe VAR_MAP_LOCAL_0x00, 5, ValleyWindworksOutside_HideDrifloon
    GoTo ValleyWindworksOutside_ShowDrifloon

ValleyWindworksOutside_ShowDrifloon:
    ClearFlag FLAG_HIDE_VALLEY_WINDWORKS_OUTSIDE_DRIFLOON
    End

ValleyWindworksOutside_HideDrifloon:
    SetFlag FLAG_HIDE_VALLEY_WINDWORKS_OUTSIDE_DRIFLOON
    End

ValleyWindworksOutside_IncreaseTeamGalacticValleyWindworksState:
    SetVar VAR_VALLEY_WINDWORKS_TEAM_GALACTIC_STATE, 3
    Return

ValleyWindworksOutside_OnLoad:
    GoToIfSet FLAG_MAP_LOCAL_REMOVE_OBJECT, ValleyWindworksOutside_RemoveDrifloon
    End

ValleyWindworksOutside_RemoveDrifloon:
    SetFlag FLAG_HIDE_VALLEY_WINDWORKS_OUTSIDE_DRIFLOON
    RemoveObject LOCALID_DRIFLOON
    ClearFlag FLAG_MAP_LOCAL_REMOVE_OBJECT
    End

ValleyWindworksOutside_RemoveBgEventDoor:
    SetBgEventPos 1, 243, 650
    Return

ValleyWindworksOutside_RemoveWarpValleyWindworksBuilding:
    SetWarpEventPos WARP_VALLEY_WINDWORKS_BUILDING, 243, 650
    Return

ValleyWindworksOutside_GruntM:
    // Arc 2: unreachable (the Galactic door guard is always hidden)
    End
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message ValleyWindworksOutside_Text_BattleMeForIt
    CloseMessage
    StartTrainerBattle TRAINER_GALACTIC_GRUNT_VALLEY_WINDWORKS_1
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, ValleyWindworksOutside_BlackOutGrunt
    Message ValleyWindworksOutside_Text_GettingOwnedBySomeKid
    CloseMessage
    ApplyMovement LOCALID_GRUNT_M, ValleyWindworksOutside_Movement_GruntMWalkOnSpotNorth
    WaitMovement
    LoadDoorAnimation 7, 20, 19, 14, ANIMATION_TAG_DOOR_1
    PlayDoorOpenAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement LOCALID_GRUNT_M, ValleyWindworksOutside_Movement_GruntMEnterBuilding
    WaitMovement
    PlayDoorCloseAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    UnloadAnimation ANIMATION_TAG_DOOR_1
    Message ValleyWindworksOutside_Text_Kerchunk
    RemoveObject LOCALID_GRUNT_M
    CloseMessage
    ReleaseAll
    End

ValleyWindworksOutside_BlackOutGrunt:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
ValleyWindworksOutside_Movement_GruntMWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
ValleyWindworksOutside_Movement_GruntMEnterBuilding:
    WalkNormalNorth
    SetInvisible
    EndMovement

ValleyWindworksOutside_Door:
    // Arc 2: the locked-door bg event is gone from the events file; kept inert
    End
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfSet FLAG_OBTAINED_FLOAROMA_MEADOW_WORKS_KEY, ValleyWindworksOutside_AskOpenDoor
    Message ValleyWindworksOutside_Text_ItsLockedFromInside
    WaitButton
    CloseMessage
    ReleaseAll
    End

ValleyWindworksOutside_AskOpenDoor:
    BufferItemName 0, ITEM_WORKS_KEY
    Message ValleyWindworksOutside_Text_UseTheWorksKey
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, ValleyWindworksOutside_AskOpenDoorEnd
    SetFlag FLAG_UNLOCKED_VALLEY_WINDWORKS_DOOR
    Call ValleyWindworksOutside_RemoveBgEventDoor
    SetWarpEventPos WARP_VALLEY_WINDWORKS_BUILDING, 243, 654
    Message ValleyWindworksOutside_Text_KerchunkTheDoorOpened
    WaitButton
    CloseMessage
    ReleaseAll
    End

ValleyWindworksOutside_AskOpenDoorEnd:
    CloseMessage
    ReleaseAll
    End

ValleyWindworksOutside_SignboardValleyWindworks:
    ShowLandmarkSign ValleyWindworksOutside_Text_SignValleyWindworks
    End

ValleyWindworksOutside_Drifloon:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    PlayCry SPECIES_DRIFLOON
    Message ValleyWindworksOutside_Text_DrifloonCry
    CloseMessage
    WaitCry
    SetFlag FLAG_MAP_LOCAL_REMOVE_OBJECT
    StartLegendaryBattle SPECIES_DRIFLOON, 15
    ClearFlag FLAG_MAP_LOCAL_REMOVE_OBJECT
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, ValleyWindworksOutside_BlackOutDrifloon
    SetFlag FLAG_DAILY_WON_AGAINST_VALLEY_WINDWORKS_OUTSIDE_DRIFLOON
    ReleaseAll
    End

ValleyWindworksOutside_BlackOutDrifloon:
    BlackOutFromBattle
    ReleaseAll
    End

ValleyWindworksOutside_OnFrame_Looker:
    LockAll
    ApplyMovement LOCALID_LOOKER, ValleyWindworksOutside_Movement_LookerNoticeAndWalkToPlayer
    ApplyMovement LOCALID_PLAYER, ValleyWindworksOutside_Movement_PlayerFaceLookerWest
    WaitMovement
    Message ValleyWindworksOutside_Text_IShallInvestigateInside
    CloseMessage
    ApplyMovement LOCALID_PLAYER, ValleyWindworksOutside_Movement_PlayerMoveAwayFromDoor
    ApplyMovement LOCALID_LOOKER, ValleyWindworksOutside_Movement_LookerWalkToDoor
    WaitMovement
    LoadDoorAnimation 7, 20, 19, 14, ANIMATION_TAG_DOOR_1
    PlayDoorOpenAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement LOCALID_LOOKER, ValleyWindworksOutside_Movement_LookerEnterBuilding
    WaitMovement
    PlayDoorCloseAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    UnloadAnimation ANIMATION_TAG_DOOR_1
    WaitTime 120, VAR_RESULT
    LoadDoorAnimation 7, 20, 19, 14, ANIMATION_TAG_DOOR_1
    PlayDoorOpenAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement LOCALID_LOOKER, ValleyWindworksOutside_Movement_LookerExitBuilding
    WaitMovement
    PlayDoorCloseAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    UnloadAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement LOCALID_LOOKER, ValleyWindworksOutside_Movement_LookerWalkOnSpotSouth
    WaitMovement
    Message ValleyWindworksOutside_Text_HideoutIsInEternaCity
    CloseMessage
    ApplyMovement LOCALID_PLAYER, ValleyWindworksOutside_Movement_PlayerWatchLookerLeave
    ApplyMovement LOCALID_LOOKER, ValleyWindworksOutside_Movement_LookerLeave
    WaitMovement
    RemoveObject LOCALID_LOOKER
    SetVar VAR_VALLEY_WINDWORKS_LOOKER_STATE, 2
    ReleaseAll
    End

    .balign 4, 0
ValleyWindworksOutside_Movement_PlayerFaceLookerWest:
    Delay8 5
    Delay4
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
ValleyWindworksOutside_Movement_PlayerMoveAwayFromDoor:
    WalkNormalSouth
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
ValleyWindworksOutside_Movement_PlayerWatchLookerLeave:
    Delay8
    WalkOnSpotNormalWest
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
ValleyWindworksOutside_Movement_LookerNoticeAndWalkToPlayer:
    EmoteExclamationMark
    Delay8
    WalkFastNorth 4
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
ValleyWindworksOutside_Movement_LookerWalkToDoor:
    Delay8
    Delay4
    WalkNormalEast
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
ValleyWindworksOutside_Movement_LookerEnterBuilding:
    WalkNormalNorth
    SetInvisible
    FaceSouth
    EndMovement

    .balign 4, 0
ValleyWindworksOutside_Movement_LookerExitBuilding:
    SetVisible
    WalkFastSouth
    EndMovement

    .balign 4, 0
ValleyWindworksOutside_Movement_LookerWalkOnSpotSouth:
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
ValleyWindworksOutside_Movement_LookerLeave:
    WalkFastWest
    WalkFastSouth
    WalkFastSouth 6
    WalkFastWest 9
    EndMovement

ValleyWindworksOutside_Arc2SetObjects:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    SetFlag FLAG_MAP_LOCAL_0x3E
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    GoToIfNe VAR_ARC2_PROGRESS, 20, ValleyWindworksOutside_Arc2SetObjectsEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
ValleyWindworksOutside_Arc2SetObjectsEnd:
    Return

// Progress 20 (frame table): morning. The player was warped to (245,658) facing north; Ruth (243,656) and
// Cyrus (244,656) stand at the gate, then walk into the building.
ValleyWindworksOutside_Arc2Morning:
    LockAll
    Message ValleyWindworksOutside_Text_Arc2NextMorning
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC2_RUTH, ValleyWindworksOutside_Movement_Arc2RuthWalkIn
    ApplyMovement LOCALID_ARC2_CYRUS, ValleyWindworksOutside_Movement_Arc2CyrusWalkIn
    WaitMovement
    RemoveObject LOCALID_ARC2_RUTH
    RemoveObject LOCALID_ARC2_CYRUS
    SetVar VAR_ARC2_PROGRESS, 21
    ReleaseAll
    End

    .balign 4, 0
ValleyWindworksOutside_Movement_Arc2RuthWalkIn:
    FaceSouth
    Delay8 2
    FaceNorth
    WalkNormalNorth 2
    SetInvisible
    EndMovement

    .balign 4, 0
ValleyWindworksOutside_Movement_Arc2CyrusWalkIn:
    Delay8 6
    WalkNormalWest
    WalkNormalNorth 2
    SetInvisible
    EndMovement
