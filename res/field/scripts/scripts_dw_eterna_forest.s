#include "macros/scrcmd.inc"
#include "res/text/bank/dw_eterna_forest.h"
#include "constants/totem_battle.h"

// Arc 2 rift: MAP_HEADER_DW_ETERNA_FOREST (rift-a; screenplay 2.10, inside). Phase 0 hybrid: the Arc 1 seams entry
// walkway (chunk 0,0, map_data_671) and DW B4F's east wall and ceiling (chunks 613/614/615, tw_arc record shifted).
//   entry   the overworld (s-floaroma, at VAR_ARC2_PROGRESS 23 -> 24) warps here: Warp MAP_HEADER_DW_ETERNA_FOREST, 0, 20, 12, DIR_WEST
//   exit    Warp MAP_HEADER_ETERNA_FOREST, 0, 84, 37, DIR_SOUTH (in front of the rift spot)
//   calm    the Vespiquen totem calmed: FLAG_TOTEM_VESPIQUEN_DEFEATED, FLAG_HIDE_TOTEM_VESPIQUEN, VAR_ARC2_PROGRESS = 26
//
// Route (puzzle: docs/distortion_world/eterna_forest.md, table src/overlay009/dw_puzzle_eterna_forest.c): the entry
// walkway west to the seam at (17,12), which folds the player into the hive: B4F's floor strip at (40,22). East to
// (48,22), onto the east wall x=49 (the y2 rune gate blocks every climb past y1), east along y1 to RUNE A (49,1,25),
// which flips wall -> ceiling. Along the ceiling to the HONEYCOMB corridor (x44-45, z33-36), which is there for a
// while, fades, is gone, and comes back (a frame timer in src/overlay009/ov9_02249960.c,
// Arc2DwEternaForest_HandleFrame). Past it, RUNE B (45,10,37) flips ceiling -> floor onto the two-tile platform;
// the SIGIL at (46,1,37) latches the bridge over the gap (x44-47, z39-40); back up, across the bridge, z41: the
// Vespiquen totem. A honeycomb fall respawns at the last checkpoint (engine snapshot), not the hive start.
// The walkway's chasm lips fall too (engine VOID tiles in the table, fall script DWEternaForest_Fall, back to the
// entry checkpoint).
//
// Flags (rift-a block 0x0926-0x0929; the lead names them at merge):
//   FLAG_ARC2_RIFTA_C (0x0928)  Eterna Forest: the honeycomb has dropped the player once (Cyrus's line played)
//   FLAG_ARC2_RIFTA_D (0x0929)  Eterna Forest: the hive reached once (Cyrus's ceiling line played)
// VAR_MAP_LOCAL_2 (map-local): set to 1 by the frame timer when the honeycomb goes with the player on it; the init
// frame table then runs the fall script.
// VAR_MAP_LOCAL_4 (map-local, this map only): honeycomb falls this visit; the hint plays on fall 2.

#define LOCALID_CYRUS_ENTRY 0x80
#define LOCALID_CYRUS_HIVE  0x81
#define LOCALID_TOTEM       0x82

#define ENTRY_X 20
#define ENTRY_Z 12
#define HIVE_X  40
#define HIVE_Z  22

    ScriptEntry DWEternaForest_OnTransition
    ScriptEntry DWEternaForest_Fall
    ScriptEntry DWEternaForest_Unused
    ScriptEntry DWEternaForest_Fold
    ScriptEntry DWEternaForest_HoneyFall
    ScriptEntry DWEternaForest_Totem
    ScriptEntry DWEternaForest_TalkCyrus
    ScriptEntryEnd

DWEternaForest_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

DWEternaForest_Unused:
    End

// The walkway's chasm lips: from the engine (VOID tiles in the table), back to the entry checkpoint.
// The engine respawns at the checkpoint after the warp; the warp here lands on the same tile.
DWEternaForest_Fall:
    LockAll
    ApplyMovement LOCALID_PLAYER, DWEternaForest_Movement_PlayerFall
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ApplyMovement LOCALID_PLAYER, DWEternaForest_Movement_SetVisible
    WaitMovement
    ResetDistortionWorldPersistedCameraAngles
    Warp MAP_HEADER_DW_ETERNA_FOREST, 0, ENTRY_X, ENTRY_Z, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

// Coord event (17,12): the seam folds the player (and Cyrus) into the hive. Cyrus's ceiling line the first time.
DWEternaForest_Fold:
    LockAll
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    ResetDistortionWorldPersistedCameraAngles
    Warp MAP_HEADER_DW_ETERNA_FOREST, 0, HIVE_X, HIVE_Z, DIR_EAST
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    GoToIfSet FLAG_ARC2_RIFTA_D, DWEternaForest_FoldEnd
    SetFlag FLAG_ARC2_RIFTA_D
    WaitTime 10, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, DWEternaForest_Movement_FaceSouth
    WaitMovement
    Message DWEternaForest_Text_CyrusHiveGrewIntoTheCeiling
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, DWEternaForest_Movement_FaceEast
    WaitMovement
DWEternaForest_FoldEnd:
    ReleaseAll
    End

// The honeycomb is gone under the player: from the step hook, or from the init frame table once the frame timer has
// raised VAR_MAP_LOCAL_2 (it was standing there when it went). The engine (DwPuzzle_NotifyFall, called at fall
// detection on both paths) respawns at the last checkpoint with its snapshot after this script's warp; the warp
// itself lands on the hive, while faded out, so the respawn is invisible. Cyrus's lines are voice-over: he is not
// on the ceiling, so no Face movements after the warp. Fall 1: the once-only "Wait for it" line. Fall 2: the
// rune/sigil hint (two messages). Later falls: no lines.
DWEternaForest_HoneyFall:
    LockAll
    SetVar VAR_MAP_LOCAL_2, 0
    AddVar VAR_MAP_LOCAL_4, 1
    ApplyMovement LOCALID_PLAYER, DWEternaForest_Movement_PlayerFall
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ApplyMovement LOCALID_PLAYER, DWEternaForest_Movement_SetVisible
    WaitMovement
    ResetDistortionWorldPersistedCameraAngles
    Warp MAP_HEADER_DW_ETERNA_FOREST, 0, HIVE_X, HIVE_Z, DIR_EAST
    FadeScreenIn
    WaitFadeScreen
    GoToIfEq VAR_MAP_LOCAL_4, 2, DWEternaForest_HoneyFallHint
    GoToIfSet FLAG_ARC2_RIFTA_C, DWEternaForest_HoneyFallEnd
    SetFlag FLAG_ARC2_RIFTA_C
    Message DWEternaForest_Text_CyrusWaitForIt
    WaitABXPadPress
    CloseMessage
    GoTo DWEternaForest_HoneyFallEnd
DWEternaForest_HoneyFallHint:
    Message DWEternaForest_Text_CyrusRuneHint
    WaitABXPadPress
    CloseMessage
    Message DWEternaForest_Text_CyrusSigilHint
    WaitABXPadPress
    CloseMessage
DWEternaForest_HoneyFallEnd:
    ReleaseAll
    End

// From the step hook: the first step at z >= 41 on the ceiling. The Vespiquen totem.
DWEternaForest_Totem:
    LockAll
    PlayCry SPECIES_VESPIQUEN
    ShakeCamera 16, 4
    WaitCry
    PlayBattleMusic SEQ_BATTLE_TOTEM
    SetFlag FLAG_MAP_LOCAL
    StartTotemBattle TOTEM_ENCOUNTER_VESPIQUEN
    ClearFlag FLAG_MAP_LOCAL
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, DWEternaForest_TotemLost
    // The aura drains; it hovers in front of the player, then flies off
    WaitTime 30, VAR_RESULT
    ApplyMovement LOCALID_TOTEM, DWEternaForest_Movement_TotemHover
    WaitMovement
    BufferPlayerName 0
    PlayFanfare SEQ_SE_PL_KIRAKIRA
    Message DWEternaForest_Text_GotCalmShard
    WaitFanfare SEQ_SE_PL_KIRAKIRA
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_TOTEM
    WaitTime 40, VAR_RESULT
    // Cyrus, below, looks at the empty space where it hung
    Message DWEternaForest_Text_CyrusWhoeverDidThis
    WaitABXPadPress
    Message DWEternaForest_Text_CyrusSoDidIOnce
    WaitABXPadPress
    CloseMessage
    SetFlag FLAG_TOTEM_VESPIQUEN_DEFEATED
    SetFlag FLAG_HIDE_TOTEM_VESPIQUEN
    SetVar VAR_ARC2_PROGRESS, 26
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    Warp MAP_HEADER_ETERNA_FOREST, 0, 84, 37, DIR_SOUTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

DWEternaForest_TotemLost:
    BlackOutFromBattle
    ReleaseAll
    End

DWEternaForest_TalkCyrus:
    LockAll
    FacePlayer
    GoToIfSet FLAG_ARC2_RIFTA_C, DWEternaForest_TalkCyrusWait
    Message DWEternaForest_Text_CyrusHiveGrewIntoTheCeiling
    GoTo DWEternaForest_TalkEnd

DWEternaForest_TalkCyrusWait:
    Message DWEternaForest_Text_CyrusWaitForIt
DWEternaForest_TalkEnd:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
DWEternaForest_Movement_PlayerFall:
    JumpOnSpotFastSouth
    SetInvisible
    EndMovement

    .balign 4, 0
DWEternaForest_Movement_SetVisible:
    SetVisible
    EndMovement

    .balign 4, 0
DWEternaForest_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
DWEternaForest_Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
DWEternaForest_Movement_TotemHover:
    WalkOnSpotSlowSouth
    Delay8
    WalkOnSpotSlowSouth
    EndMovement
