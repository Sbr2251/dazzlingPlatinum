#include "macros/scrcmd.inc"
#include "res/text/bank/dw_lost_tower.h"
#include "constants/totem_battle.h"

// Arc 2 rift 2.25-2.26, inside: MAP_HEADER_DW_LOST_TOWER, alone (owner rift-b; docs/arc2/rift_contract.md and the
// orchestrator's Lost Tower ruling of 2026-10-11 00:45).
//   entry   Lost Tower 2F rift (6,8), at 92-94: Warp MAP_HEADER_DW_LOST_TOWER, 0, 20, 12, DIR_WEST
//   exit 1  first visit (VAR_ARC2_PROGRESS 92-93): the vein, then the wall of shadow, then
//           Warp MAP_HEADER_ROUTE_209_LOST_TOWER_2F, 0, 7, 8, DIR_EAST (progress unchanged, FLAG_ARC2_RIFTB_E set)
//   exit 2  second visit (94): the wall parts, Cyrus, the Spiritomb; VAR_ARC2_PROGRESS 95, then
//           Warp MAP_HEADER_ROUTE_209, 0, 568, 681, DIR_SOUTH
//
// Phase 0 floor: the Arc 1 seams floor (a DW B1F clone; tools/distortion_world/lost_tower.json, build_rift_b_maps.py),
// with no Cyrus. The seam is the arc1 one on the west wall x=11: on from the ledge (12..15,14), along the bottom
// under the trees, a dead-end corner up the wall at z 19-22 (the scar), off at (12,23) onto the vein room
// (12..15,23). The wall of shadow (overlay object at (16,23)) closes the way deeper until it parts at 94. Deeper:
// Cyrus on his knees at (18,22), his starter fainted at (17,21), the Spiritomb at (20,22).
// Falls: coord events on the chasm lips put the player back at the entry, as in Arc 1.
//
// rift-b flags (see scripts_dw_route_214.s): FLAG_ARC2_RIFTB_C = first-seam memory shown, FLAG_ARC2_RIFTB_D = the
// shadow has parted, FLAG_ARC2_RIFTB_E (0x092F) = the vein found (s-hearthome reads it for the 2.25 call).
// Map-local: VAR_MAP_LOCAL_2 memory coord done, VAR_MAP_LOCAL_3 always 0 (fall lips), VAR_MAP_LOCAL_4 vein coord
// done, VAR_MAP_LOCAL_5 shadow coord done (each this load).

#define LOCALID_SHADOW    0x84
#define LOCALID_CYRUS     0x85
#define LOCALID_SPIRITOMB 0x86
#define LOCALID_EMPOLEON  0x87
#define LOCALID_TORTERRA  0x88
#define LOCALID_INFERNAPE 0x89

#define ENTRY_X 20
#define ENTRY_Z 12

    ScriptEntry DWLostTower_OnTransition
    ScriptEntry DWLostTower_Fall
    ScriptEntry DWLostTower_Memory
    ScriptEntry DWLostTower_Vein
    ScriptEntry DWLostTower_ShadowWall
    ScriptEntry DWLostTower_TalkCyrus
    ScriptEntryEnd

DWLostTower_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

DWLostTower_End:
    End

// Coord events on the chasm lips: the void sends the player back to the entry.
DWLostTower_Fall:
    LockAll
    ApplyMovement LOCALID_PLAYER, DWLostTower_Movement_PlayerFall
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ApplyMovement LOCALID_PLAYER, DWLostTower_Movement_SetVisible
    WaitMovement
    ResetDistortionWorldPersistedCameraAngles
    Warp MAP_HEADER_DW_LOST_TOWER, 0, ENTRY_X, ENTRY_Z, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

// Coord event on the ledge in front of the seam: Cyrus's words from 2.6 come back (no speaker; a memory). Once.
DWLostTower_Memory:
    SetVar VAR_MAP_LOCAL_2, 1
    GoToIfSet FLAG_ARC2_RIFTB_C, DWLostTower_End
    LockAll
    SetFlag FLAG_ARC2_RIFTB_C
    WaitTime 10, VAR_RESULT
    Message DWLostTower_Text_FollowTheSeam
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// Coord event one step into the vein room (13,23): the violet crystals. Sets the vein flag the 2.25 call reads.
DWLostTower_Vein:
    SetVar VAR_MAP_LOCAL_4, 1
    GoToIfSet FLAG_ARC2_RIFTB_E, DWLostTower_End
    LockAll
    PlayFanfare SEQ_SE_DP_KIRAKIRA
    Message DWLostTower_Text_VioletCrystals
    WaitFanfare SEQ_SE_DP_KIRAKIRA
    WaitABXPadPress
    CloseMessage
    SetFlag FLAG_ARC2_RIFTB_E
    ReleaseAll
    End

// Coord event in front of the wall of shadow (15,23), or A on it. Below 94 it won't move and the player goes back
// to 2F; from 94 on it parts, and Cyrus is deeper, beside the Spiritomb.
DWLostTower_ShadowWall:
    SetVar VAR_MAP_LOCAL_5, 1
    LockAll
    GoToIfGe VAR_ARC2_PROGRESS, 94, DWLostTower_FindCyrus
    ApplyMovement LOCALID_PLAYER, DWLostTower_Movement_FaceEast
    WaitMovement
    Message DWLostTower_Text_WallOfShadow
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    Warp MAP_HEADER_ROUTE_209_LOST_TOWER_2F, 0, 7, 8, DIR_EAST
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

DWLostTower_FindCyrus:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8004, 15, DWLostTower_FindCyrusEnd
    GoToIfNe VAR_0x8005, 23, DWLostTower_FindCyrusEnd
    ApplyMovement LOCALID_PLAYER, DWLostTower_Movement_FaceEast
    WaitMovement
    GoToIfSet FLAG_ARC2_RIFTB_D, DWLostTower_ShadowGone
    // Giratina's shadow passes below (the Arc 1 fly-by, same floor), and the wall of shadow parts. No text.
    WaitTime 20, VAR_RESULT
    ScrCmd_321 3
    WaitTime 42, VAR_RESULT
    ScrCmd_322
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_SHADOW
    SetFlag FLAG_ARC2_RIFTB_D
    WaitTime 20, VAR_RESULT
DWLostTower_ShadowGone:
    // Cyrus's starter, fainted at his side: the one weak to the player's (trainers-story's Cyrus 3 teams)
    GetPlayerStarterSpecies VAR_0x8006
    CallIfEq VAR_0x8006, SPECIES_TURTWIG, DWLostTower_ShowEmpoleon
    CallIfEq VAR_0x8006, SPECIES_CHIMCHAR, DWLostTower_ShowTorterra
    CallIfEq VAR_0x8006, SPECIES_PIPLUP, DWLostTower_ShowInfernape
    ApplyMovement LOCALID_PLAYER, DWLostTower_Movement_PlayerToCyrus
    WaitMovement
    WaitTime 30, VAR_RESULT
    ApplyMovement LOCALID_CYRUS, DWLostTower_Movement_CyrusLooksUp
    WaitMovement
    Message DWLostTower_Text_CyrusYouCame
    WaitABXPadPress
    Message DWLostTower_Text_CyrusHundredVoices
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, DWLostTower_Movement_FaceEast
    WaitMovement
    PlayCry SPECIES_SPIRITOMB
    WaitCry
    PlayBattleMusic SEQ_BATTLE_TOTEM
    StartTotemBattle TOTEM_ENCOUNTER_SPIRITOMB
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, DWLostTower_TotemLost
    SetFlag FLAG_TOTEM_SPIRITOMB_DEFEATED
    SetFlag FLAG_HIDE_TOTEM_SPIRITOMB
    // The aura drains and it sinks into the floor
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_SPIRITOMB
    WaitTime 20, VAR_RESULT
    // A sound effect, not PlaySound SEQ_FANFA4 (that pauses the music and the exit Warp then hangs)
    BufferPlayerName 0
    PlayFanfare SEQ_SE_DP_KIRAKIRA
    Message DWLostTower_Text_GotCalmShard
    WaitFanfare SEQ_SE_DP_KIRAKIRA
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 95
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    Warp MAP_HEADER_ROUTE_209, 0, 568, 681, DIR_SOUTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

DWLostTower_FindCyrusEnd:
    ReleaseAll
    End

DWLostTower_TotemLost:
    BlackOutFromBattle
    ReleaseAll
    End

DWLostTower_ShowEmpoleon:
    ScrCmd_311 LOCALID_EMPOLEON
    Return

DWLostTower_ShowTorterra:
    ScrCmd_311 LOCALID_TORTERRA
    Return

DWLostTower_ShowInfernape:
    ScrCmd_311 LOCALID_INFERNAPE
    Return

DWLostTower_TalkCyrus:
    LockAll
    Message DWLostTower_Text_CyrusYouCame
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
DWLostTower_Movement_PlayerFall:
    JumpOnSpotFastSouth
    SetInvisible
    EndMovement

    .balign 4, 0
DWLostTower_Movement_SetVisible:
    SetVisible
    EndMovement

    .balign 4, 0
DWLostTower_Movement_FaceEast:
    FaceEast
    EndMovement

// (15,23) -> (17,23) -> (17,22), beside Cyrus (18,22); his starter lies at (17,21)
    .balign 4, 0
DWLostTower_Movement_PlayerToCyrus:
    WalkNormalEast 2
    WalkNormalNorth
    FaceEast
    EndMovement

    .balign 4, 0
DWLostTower_Movement_CyrusLooksUp:
    FaceWest
    EndMovement
