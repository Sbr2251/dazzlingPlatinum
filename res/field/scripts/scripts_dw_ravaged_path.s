#include "macros/scrcmd.inc"
#include "res/text/bank/dw_ravaged_path.h"
#include "constants/totem_battle.h"

// Arc 2 rift: MAP_HEADER_DW_RAVAGED_PATH (rift-a; screenplay 2.6-2.7). Phase 0: the Arc 1 seams floor (a DW B1F clone).
//   entry   the overworld (s-route204, at VAR_ARC2_PROGRESS 13 -> 14) warps here: Warp MAP_HEADER_DW_RAVAGED_PATH, 0, 20, 12, DIR_WEST
//   exit    Warp MAP_HEADER_RAVAGED_PATH, 0, 19, 46, DIR_SOUTH (in front of the closed rift)
//   calm    the Hitmonlee totem calmed: FLAG_TOTEM_HITMONLEE_DEFEATED, FLAG_HIDE_TOTEM_HITMONLEE, VAR_ARC2_PROGRESS = 15
//
// Route: the entry walkway, the jump-on ledge (12,14), onto the west wall x=11 at z=13, along the bottom row under the
// wall trees, the FORK at z=19 (the bottom row on is a scar; the seam goes up), over the top of the scar (GIRATINA's
// shadow passes below at y4 z20), down at z=22, hop off to (12,23), the totem at the far end of the platform.
// SCARS (the new verb) are wall tiles that hold you for one step and crumble one step after you leave them; the step
// hook in src/overlay009/ov9_02249960.c (Arc2DwRavagedPath_HandleStep) tracks them and starts the fall script. The
// chasm lips of the floors fall too (coord events, as in Arc 1). A fall resets you at the entry and heals the wall.
//
// Flags (rift-a block 0x0926-0x0929; the lead names them at merge):
//   FLAG_ARC2_RIFTA_A (0x0926)  Ravaged Path: the player has fallen once (Cyrus's retry line played)
//   FLAG_ARC2_RIFTA_B (0x0927)  Ravaged Path: the halfway point reached (fork hint stops, GIRATINA's shadow seen)
//   FLAG_ARC2_RESONATOR_A (0x0924, unused block; fix2-dwrp) Ravaged Path: Cyrus's fork line played. Set by the step
//                               hook (FLAG_ARC2_RAVAGED_PATH_FORK_SEEN in ov9). Persistent, so a fall and return
//                               doesn't replay it; talking to Cyrus repeats the scar hint instead.
//   FLAG_UNK_0x0030 (map-local) Cyrus has crossed to the totem platform (hides him at the entry, kept through the battle)
//   FLAG_UNK_0x0031 (map-local) the violet totem object stays hidden after the battle reload
// VAR_MAP_LOCAL_1 (map-local): 0 until the map-load script has run (cleared by every warp, including a fall). Not
// VAR_MAP_LOCAL_0: its id 0x4000 has a zero low byte, which ends an init frame table (script_manager.c).

#define LOCALID_CYRUS_ENTRY 0x80
#define LOCALID_CYRUS_TOTEM 0x81
#define LOCALID_TOTEM       0x82
#define LOCALID_TOTEM_CALM  0x83

#define ENTRY_X 20
#define ENTRY_Z 12

    ScriptEntry DWRavagedPath_OnTransition
    ScriptEntry DWRavagedPath_Fall
    ScriptEntry DWRavagedPath_MapLoad
    ScriptEntry DWRavagedPath_Fork
    ScriptEntry DWRavagedPath_Halfway
    ScriptEntry DWRavagedPath_Totem
    ScriptEntry DWRavagedPath_TalkCyrus
    ScriptEntryEnd

DWRavagedPath_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

// Init frame table, once per map load: Cyrus's entry line, the first time in (before any fall or the halfway point).
DWRavagedPath_MapLoad:
    SetVar VAR_MAP_LOCAL_1, 1
    GoToIfNe VAR_ARC2_PROGRESS, 14, DWRavagedPath_End
    GoToIfSet FLAG_ARC2_RIFTA_A, DWRavagedPath_End
    GoToIfSet FLAG_ARC2_RIFTA_B, DWRavagedPath_End
    LockAll
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, DWRavagedPath_Movement_FaceEast
    WaitMovement
    Message DWRavagedPath_Text_CyrusFrightened
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, DWRavagedPath_Movement_FaceWest
    WaitMovement
    ReleaseAll
    End

DWRavagedPath_End:
    End

// The Arc 1 fall script: from a scar (the step hook) or a chasm lip (coord events). The void sends the player back to
// the entry; Cyrus's retry line plays after the first fall only.
DWRavagedPath_Fall:
    LockAll
    ApplyMovement LOCALID_PLAYER, DWRavagedPath_Movement_PlayerFall
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ApplyMovement LOCALID_PLAYER, DWRavagedPath_Movement_SetVisible
    WaitMovement
    ResetDistortionWorldPersistedCameraAngles
    Warp MAP_HEADER_DW_RAVAGED_PATH, 0, ENTRY_X, ENTRY_Z, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    GoToIfSet FLAG_ARC2_RIFTA_A, DWRavagedPath_FallEnd
    SetFlag FLAG_ARC2_RIFTA_A
    ApplyMovement LOCALID_PLAYER, DWRavagedPath_Movement_FaceEast
    WaitMovement
    Message DWRavagedPath_Text_CyrusAgainSlower
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, DWRavagedPath_Movement_FaceWest
    WaitMovement
DWRavagedPath_FallEnd:
    ReleaseAll
    End

// Step hook: the first step onto the fork column (z=19) on the wall, once (FLAG_ARC2_RESONATOR_A, set by the hook),
// and never after the halfway point. Cyrus calls it from the entry; the bottom row on is the scar.
DWRavagedPath_Fork:
    LockAll
    Message DWRavagedPath_Text_CyrusFollowTheSeam
    WaitABXPadPress
    Message DWRavagedPath_Text_CyrusScarHoldsYouOnce
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// Step hook: on top of the seam (y4 z20), once. A huge shadow passes far below the platforms (the Arc 1 fly-by model,
// ov9 fly-by entry 4), then is gone. No text.
DWRavagedPath_Halfway:
    LockAll
    SetFlag FLAG_ARC2_RIFTA_B
    WaitTime 10, VAR_RESULT
    ScrCmd_321 4
    WaitTime 98, VAR_RESULT
    ScrCmd_322
    WaitTime 8, VAR_RESULT
    ReleaseAll
    End

// Coord event (14,23), two steps onto the briefcase platform: the totem.
DWRavagedPath_Totem:
    LockAll
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    ApplyMovement LOCALID_PLAYER, DWRavagedPath_Movement_FaceEast
    WaitMovement
    // Cyrus folds the space between and steps out beside the player, as in Arc 1
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_CYRUS_ENTRY
    ScrCmd_311 LOCALID_CYRUS_TOTEM
    WaitTime 20, VAR_RESULT
    // It screams when it sees them
    PlayCry SPECIES_HITMONLEE
    ApplyMovement LOCALID_TOTEM, DWRavagedPath_Movement_TotemScream
    ShakeCamera 16, 4
    WaitMovement
    WaitCry
    Message DWRavagedPath_Text_CyrusThereTheShard
    WaitABXPadPress
    CloseMessage
    PlayBattleMusic SEQ_BATTLE_TOTEM
    SetFlag FLAG_MAP_LOCAL
    StartTotemBattle TOTEM_ENCOUNTER_HITMONLEE
    ClearFlag FLAG_MAP_LOCAL
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, DWRavagedPath_TotemLost
    // The overlay objects persist through the battle: the violet totem fades out and the calm one fades in (the aura
    // drains). FLAG_UNK_0x0031 keeps the violet one away if the map is ever rebuilt instead.
    ScrCmd_311 LOCALID_CYRUS_TOTEM
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_TOTEM
    ScrCmd_311 LOCALID_TOTEM_CALM
    WaitTime 30, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, DWRavagedPath_Movement_FaceEast
    WaitMovement
    Message DWRavagedPath_Text_CyrusItsCalm
    WaitABXPadPress
    CloseMessage
    // Hitmonlee nudges the clear shard toward the player
    ApplyMovement LOCALID_TOTEM_CALM, DWRavagedPath_Movement_TotemNudge
    WaitMovement
    BufferPlayerName 0
    PlayFanfare SEQ_SE_PL_KIRAKIRA
    Message DWRavagedPath_Text_GotCalmShard
    WaitFanfare SEQ_SE_PL_KIRAKIRA
    WaitABXPadPress
    CloseMessage
    // It bows and bounds off into the dark
    ApplyMovement LOCALID_TOTEM_CALM, DWRavagedPath_Movement_TotemBowAndGo
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_TOTEM_CALM
    WaitTime 30, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, DWRavagedPath_Movement_FaceNorth
    WaitMovement
    Message DWRavagedPath_Text_CyrusITook
    WaitABXPadPress
    Message DWRavagedPath_Text_CyrusComeTheRift
    WaitABXPadPress
    CloseMessage
    SetFlag FLAG_TOTEM_HITMONLEE_DEFEATED
    SetFlag FLAG_HIDE_TOTEM_HITMONLEE
    SetVar VAR_ARC2_PROGRESS, 15
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    Warp MAP_HEADER_RAVAGED_PATH, 0, 19, 46, DIR_SOUTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

DWRavagedPath_TotemLost:
    BlackOutFromBattle
    ReleaseAll
    End

DWRavagedPath_TalkCyrus:
    LockAll
    FacePlayer
    GoToIfSet FLAG_ARC2_RIFTA_A, DWRavagedPath_TalkCyrusScar
    GoToIfSet FLAG_ARC2_RIFTA_B, DWRavagedPath_TalkCyrusScar
    GoToIfSet FLAG_ARC2_RESONATOR_A, DWRavagedPath_TalkCyrusScar
    Message DWRavagedPath_Text_CyrusFrightened
    GoTo DWRavagedPath_TalkEnd

DWRavagedPath_TalkCyrusScar:
    Message DWRavagedPath_Text_CyrusScarHoldsYouOnce
DWRavagedPath_TalkEnd:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
DWRavagedPath_Movement_PlayerFall:
    JumpOnSpotFastSouth
    SetInvisible
    EndMovement

    .balign 4, 0
DWRavagedPath_Movement_SetVisible:
    SetVisible
    EndMovement

    .balign 4, 0
DWRavagedPath_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
DWRavagedPath_Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
DWRavagedPath_Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
DWRavagedPath_Movement_TotemScream:
    FaceWest
    JumpOnSpotFastWest 2
    EndMovement

    .balign 4, 0
DWRavagedPath_Movement_TotemNudge:
    FaceWest
    WalkOnSpotSlowWest
    Delay8
    EndMovement

    .balign 4, 0
DWRavagedPath_Movement_TotemBowAndGo:
    FaceSouth
    Delay16
    FaceWest
    Delay8
    JumpOnSpotFastNorth
    EndMovement
