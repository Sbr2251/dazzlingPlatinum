#include "macros/scrcmd.inc"
#include "res/text/bank/team_galactic_eterna_building_4f.h"
#include "res/field/events/events_team_galactic_eterna_building_4f.h"

// Dazzling Platinum Arc 2 (s-eterna, screenplay 2.12): Eclipse Haven 4F, the loading bay. After the 3F battle
// (FLAG_ARC2_ETERNA_A (0x093E)), stepping into the bay (coord, row 10) runs the end of the Haven: Gardenia
// finds Pip in a crate (no Budew field sprite yet: the crate shakes and Budew cries), Looker calls it in and asks
// Cyrus's name. Then VAR_ARC2_PROGRESS 35, the stock "building cleared" flags, and the warp to the 2.13 cutaway.
// Stock Jupiter, the Clefairy/Buneary owner scene and the Galactic signs are removed.
// Map-local: hide flags 0x30 Looker, 0x31 Gardenia, 0x32 Ruth, 0x34 crates (hidden at 35+);
// VAR_MAP_LOCAL_0 = 0 arms the coord.

    ScriptEntry _001A
    ScriptEntry Haven4F_LoadingBayScene
    ScriptEntry Haven4F_PipCrate
    ScriptEntry Haven4F_Crate
    ScriptEntry Haven4F_Sign
    ScriptEntry Haven4F_OnTransition
    ScriptEntryEnd

_001A:
    ScrCmd_2CD
    End

Haven4F_OnTransition:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (Arc 1 D1) */
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    SetFlag FLAG_UNK_0x0032
    SetFlag FLAG_UNK_0x0034
    SetVar VAR_MAP_LOCAL_0, 1
    GoToIfGe VAR_ARC2_PROGRESS, 35, Haven4F_OnTransitionEnd
    ClearFlag FLAG_UNK_0x0034
    GoToIfNe VAR_ARC2_PROGRESS, 34, Haven4F_OnTransitionEnd
    GoToIfUnset FLAG_ARC2_ETERNA_A, Haven4F_OnTransitionEnd
    SetVar VAR_MAP_LOCAL_0, 0
Haven4F_OnTransitionEnd:
    End

Haven4F_PipCrate:
Haven4F_Crate:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message Haven4F_Text_Crate
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

Haven4F_Sign:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message Haven4F_Text_Sign
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// The player steps onto row 10 (x 13-15) below the loading bay. They walk up to (14,8).
Haven4F_LoadingBayScene:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 13, Haven4F_WalkInFrom13
    CallIfEq VAR_0x8004, 14, Haven4F_WalkInFrom14
    CallIfEq VAR_0x8004, 15, Haven4F_WalkInFrom15
    // Gardenia runs past to the crate at (18,5)
    ClearFlag FLAG_UNK_0x0031
    SetObjectEventPos HAVEN_4F_GARDENIA, 13, 11
    AddObject HAVEN_4F_GARDENIA
    ApplyMovement HAVEN_4F_GARDENIA, Haven4F_Movement_GardeniaRunToCrate
    WaitMovement
    Message Haven4F_Text_GardeniaPip
    CloseMessage
    ApplyMovement HAVEN_4F_PIP_CRATE, Haven4F_Movement_CrateShake
    WaitMovement
    PlayCry SPECIES_BUDEW
    Message Haven4F_Text_BudewCry
    WaitCry
    Message Haven4F_Text_GardeniaAlreadySent
    CloseMessage
    // Looker and Ruth come up behind the player
    ClearFlag FLAG_UNK_0x0030
    ClearFlag FLAG_UNK_0x0032
    SetObjectEventPos HAVEN_4F_LOOKER, 13, 11
    SetObjectEventPos HAVEN_4F_RUTH, 14, 11
    AddObject HAVEN_4F_LOOKER
    AddObject HAVEN_4F_RUTH
    ApplyMovement HAVEN_4F_LOOKER, Haven4F_Movement_LookerComeUp
    ApplyMovement HAVEN_4F_RUTH, Haven4F_Movement_RuthComeUp
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Haven4F_Movement_FaceWest
    WaitMovement
    // he talks into his collar
    ApplyMovement HAVEN_4F_LOOKER, Haven4F_Movement_FaceNorth
    WaitMovement
    Message Haven4F_Text_LookerBiggerThanOneBuilding
    CloseMessage
    ApplyMovement HAVEN_4F_LOOKER, Haven4F_Movement_FaceEast
    WaitMovement
    Message Haven4F_Text_LookerWhatIsHisName
    WaitABXPadPress
    Message Haven4F_Text_RuthCyrus
    WaitABXPadPress
    Message Haven4F_Text_LookerCyrusHm
    CloseMessage
    // he writes it down
    ApplyMovement HAVEN_4F_LOOKER, Haven4F_Movement_FaceNorth
    WaitMovement
    WaitTime 30, VAR_RESULT
    ApplyMovement HAVEN_4F_LOOKER, Haven4F_Movement_FaceEast
    WaitMovement
    Message Haven4F_Text_LookerYouHaveNotSeenMe
    WaitABXPadPress
    CloseMessage
    // The Haven is shut. Stock "Galactic building cleared" state: Cycle Shop, Pokemon Center Buneary, Rotom room.
    SetVar VAR_ARC2_PROGRESS, 35
    SetFlag FLAG_UNK_0x01FD
    SetFlag FLAG_UNK_0x01BB
    SetFlag FLAG_UNK_0x01C2
    SetFlag FLAG_UNK_0x0081
    ClearFlag FLAG_UNK_0x0192
    ClearFlag FLAG_UNK_0x0200
    ClearFlag FLAG_UNK_0x01FE
    SetFlag FLAG_ALT_MUSIC_GALACTIC_ETERNA_BUILDING
    FadeScreenOut
    WaitFadeScreen
    GoTo Haven4F_GoToCutaway213

// Handoff to the 2.13 cutaway, s-cutaways' contract: progress 35 set, screen faded to black, warp into the violet
// room with no FadeScreenIn. The cutaway sets 39 and returns the player to Eterna (305,520), facing south.
Haven4F_GoToCutaway213:
    Warp MAP_HEADER_GALACTIC_HQ_CONTROL_ROOM, 0, 8, 9, DIR_NORTH
    ReleaseAll
    End

Haven4F_WalkInFrom13:
    ApplyMovement LOCALID_PLAYER, Haven4F_Movement_InFrom13
    WaitMovement
    Return

Haven4F_WalkInFrom14:
    ApplyMovement LOCALID_PLAYER, Haven4F_Movement_InFrom14
    WaitMovement
    Return

Haven4F_WalkInFrom15:
    ApplyMovement LOCALID_PLAYER, Haven4F_Movement_InFrom15
    WaitMovement
    Return

    .balign 4, 0
Haven4F_Movement_InFrom13:
    WalkNormalNorth
    WalkNormalEast
    WalkNormalNorth
    EndMovement

    .balign 4, 0
Haven4F_Movement_InFrom14:
    WalkNormalNorth 2
    EndMovement

    .balign 4, 0
Haven4F_Movement_InFrom15:
    WalkNormalNorth
    WalkNormalWest
    WalkNormalNorth
    EndMovement

    .balign 4, 0
Haven4F_Movement_GardeniaRunToCrate:
    WalkFastNorth 4
    WalkFastEast 5
    WalkFastNorth
    EndMovement

    .balign 4, 0
Haven4F_Movement_CrateShake:
    JumpOnSpotFastSouth
    JumpOnSpotFastSouth
    EndMovement

    .balign 4, 0
Haven4F_Movement_LookerComeUp:
    WalkNormalNorth 3
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
Haven4F_Movement_RuthComeUp:
    WalkNormalNorth 2
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
Haven4F_Movement_FaceWest:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
Haven4F_Movement_FaceNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
Haven4F_Movement_FaceEast:
    WalkOnSpotNormalEast
    EndMovement
