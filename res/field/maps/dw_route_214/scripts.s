#include "macros/scrcmd.inc"
#include "res/text/bank/dw_route_214.h"
#include "res/field/maps/locals/dw_route_214.h"
#include "constants/totem_battle.h"

// Arc 2 rift 2.18, inside: MAP_HEADER_DW_ROUTE_214 (owner rift-b; docs/arc2/rift_contract.md).
//   entry   the overworld rift sets VAR_ARC2_PROGRESS 62, then Warp MAP_HEADER_DW_ROUTE_214, 20, 12, DIR_WEST
//   exit    Warp MAP_HEADER_ROUTE_214, 726, 665, DIR_SOUTH, after the calm (VAR_ARC2_PROGRESS 63)
//
// Phase 0 floor: a clone of DW B4F (tools/distortion_world/route_214.json, build_rift_b_maps.py). The verb is the hop:
// from the entry island across the chasm (25 -> 31, z 22-23), across the pool (32 -> 38), then the corridor to the
// east wall (x=49): floor -> wall -> ceiling (y=10). Skarmory dives from the dark at the far end of the ceiling
// (z >= 45; the step hook Arc2DwRoute214_HandleStep in src/overlay009/ov9_02249960.c runs entry 4).
// Before the wall, the boost choice at the frame (coord event x=44, z 22-23): Cyrus folds space to the frame.
//
// rift-b flags (0x092A-0x092F; the lead renames them at merge):
//   FLAG_ARC2_RIFTB_A = FLAG_ARC2_RIFTB_A   Route 214: the boost choice was made (Cyrus stands at the frame)
//   FLAG_ARC2_RIFTB_B = FLAG_ARC2_RIFTB_B   Route 214: Cyrus pulled the shard (the frame is dark; = VAR_ARC2_CHOICES bit 2)
//   FLAG_ARC2_RIFTB_C = FLAG_ARC2_RIFTB_C   Lost Tower: the first-seam memory text was shown
//   FLAG_ARC2_RIFTB_D = FLAG_ARC2_RIFTB_D   Lost Tower: the shadow wall has parted (second visit)
//   FLAG_ARC2_ELIAS_CARD = FLAG_ARC2_ELIAS_CARD  Route 213: the worn Trainer Card was picked up
//   FLAG_ARC2_RIFTB_E = FLAG_ARC2_RIFTB_E   Lost Tower: the vein was found (s-hearthome reads it for the call)
// Map-local: VAR_MAP_LOCAL_0x01 entry line played this load, VAR_MAP_LOCAL_0x02 frame coord event done this load
// (not VAR_MAP_LOCAL_0x00: init frame tables stop at a var id whose low byte is 0, and 0x4000 is one).
// DW overlay objects (src/overlay009 sArc2DwRoute214Objects): 0x80 Cyrus at the entry (until the choice),
// 0x81 Cyrus at the frame (after it), 0x82 the shard frame (until the shard is pulled).

#define LOCALID_CYRUS_ENTRY 0x80
#define LOCALID_CYRUS_FRAME 0x81
#define LOCALID_FRAME       0x82

#define ENTRY_X 20
#define ENTRY_Z 12

    ScriptEntry DWRoute214_OnTransition
    ScriptEntry DWRoute214_EntryScene
    ScriptEntry DWRoute214_Frame
    ScriptEntry DWRoute214_Totem
    ScriptEntry DWRoute214_TalkCyrus
    ScriptEntry DWRoute214_Fall
    ScriptEntryEnd

DWRoute214_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

// First frame of every load (init script, VAR_MAP_LOCAL_0x01 == 0): Cyrus's guide line, only on the entry tile.
DWRoute214_EntryScene:
    SetVar VAR_MAP_LOCAL_0x01, 1
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8004, ENTRY_X, DWRoute214_End
    GoToIfNe VAR_0x8005, ENTRY_Z, DWRoute214_End
    GoToIfSet FLAG_TOTEM_SKARMORY_DEFEATED, DWRoute214_End
    LockAll
    // The rift drops the player among the trees at (20,12); step out to (17,12), beside Cyrus (16,12)
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, DWRoute214_Movement_StepOutOfTrees
    WaitMovement
    // Back in after a blackout with the choice made: Cyrus already stands at the frame, so no line here
    GoToIfSet FLAG_ARC2_RIFTB_A, DWRoute214_EntryEnd
    Message DWRoute214_Text_CyrusNoFloor
    WaitButton
    CloseMessage
DWRoute214_EntryEnd:
    ReleaseAll
    End

DWRoute214_End:
    End

// Coord event on the corridor (x=44, z 22-23), two tiles before the frame: the boost choice. Once per save
// (FLAG_ARC2_RIFTB_A); after a blackout the choice stands and the frame stays as it was left.
DWRoute214_Frame:
    SetVar VAR_MAP_LOCAL_0x02, 1
    GoToIfSet FLAG_ARC2_RIFTB_A, DWRoute214_End
    LockAll
    PlayFanfare SEQ_SE_PL_SYUWA_sseq
    DeleteDistortionWorldMapObject LOCALID_CYRUS_ENTRY
    SetFlag FLAG_ARC2_RIFTB_A
    AddDistortionWorldMapObject LOCALID_CYRUS_FRAME
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, DWRoute214_Movement_FaceEast
    WaitMovement
    Message DWRoute214_Text_CyrusShardInFrame
    WaitButton
    Message DWRoute214_Text_CyrusICanPullIt
    WaitButton
    Message DWRoute214_Text_CyrusShouldI
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, DWRoute214_FrameLeave
    CloseMessage
    ApplyMovement LOCALID_CYRUS_FRAME, DWRoute214_Movement_CyrusPull
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA_sseq
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    DeleteDistortionWorldMapObject LOCALID_FRAME
    SetFlag FLAG_ARC2_RIFTB_B
    // VAR_ARC2_CHOICES bit 2: the Skarmory boost was pulled (AddVar once: FLAG_ARC2_RIFTB_A gates this script)
    AddVar VAR_ARC2_CHOICES, 4
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    ApplyMovement LOCALID_CYRUS_FRAME, DWRoute214_Movement_CyrusKneel
    WaitMovement
    Message DWRoute214_Text_CyrusEllipsis
    WaitButton
    ApplyMovement LOCALID_CYRUS_FRAME, DWRoute214_Movement_CyrusStand
    WaitMovement
    Message DWRoute214_Text_CyrusItsOut
    WaitButton
    CloseMessage
    ReleaseAll
    End

DWRoute214_FrameLeave:
    Message DWRoute214_Text_CyrusFullStrength
    WaitButton
    CloseMessage
    ReleaseAll
    End

// Step hook: the far end of the ceiling. Skarmory dives out of the dark; boosted unless the shard was pulled.
DWRoute214_Totem:
    GoToIfSet FLAG_TOTEM_SKARMORY_DEFEATED, DWRoute214_End
    LockAll
    PlayCry SPECIES_SKARMORY
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitCry
    PlayBattleMusic BATTLE_WILD_POKEMON_sseq
    SetVar VAR_0x8004, TOTEM_ENCOUNTER_SKARMORY_BOOSTED
    GoToIfUnset FLAG_ARC2_RIFTB_B, DWRoute214_TotemBattle
    SetVar VAR_0x8004, TOTEM_ENCOUNTER_SKARMORY
DWRoute214_TotemBattle:
    StartTotemBattle VAR_0x8004
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, DWRoute214_TotemLost
    SetFlag FLAG_TOTEM_SKARMORY_DEFEATED
    SetFlag FLAG_HIDE_TOTEM_SKARMORY
    // The Calm Shard: a sound effect, not PlayFanfare SEQ_FANFA4_sseq (that pauses the music and the exit Warp then hangs)
    BufferPlayerName 0
    PlayFanfare SEQ_SE_DP_KIRAKIRA_sseq
    Message DWRoute214_Text_GotCalmShard
    WaitFanfare
    Message DWRoute214_Text_CyrusItsFree
    WaitButton
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 63
    PlayFanfare SEQ_SE_PL_SYUWA_sseq
    FadeScreenOut
    WaitFadeScreen
    DoDWWarp
    ReturnToField
    Warp MAP_HEADER_ROUTE_214, 726, 665, DIR_SOUTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

DWRoute214_TotemLost:
    BlackOutFromBattle
    ReleaseAll
    End

// Puzzle fall script (entry 6; the table's fallScriptId in dw_puzzle_route_214.c,
// started by the engine on a VOID step fall -- two production VOID edge lips,
// (49,34) and (44,42), section 9 of the design doc -- and by the init frame
// table when the engine raises VAR_MAP_LOCAL_0x03 for a frame-detected fall,
// ground gone under a standing player). It plays the fall, warps to the map
// entry, and the engine restores the last checkpoint snapshot and respawns
// at the checkpoint after the warp. Cyrus's hint plays on the second fall
// (FLAG_DW_214_A fell once, FLAG_DW_214_B hint shown).
DWRoute214_Fall:
    // dwp:rift-214: clear the puzzle frame-fall var (raised by the engine
    // when the ground goes from under a standing player); normally 0, so
    // this is a no-op for non-puzzle falls.
    SetVar VAR_MAP_LOCAL_0x03, 0
    LockAll
    ApplyMovement LOCALID_PLAYER, DWRoute214_Movement_PlayerFall
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA_sseq
    FadeScreenOut
    WaitFadeScreen
    ApplyMovement LOCALID_PLAYER, DWRoute214_Movement_SetVisible
    WaitMovement
    ResetDistortionWorldPersistedCameraAngles
    Warp MAP_HEADER_DW_ROUTE_214, ENTRY_X, ENTRY_Z, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    GoToIfSet FLAG_DW_214_B, DWRoute214_FallEnd
    GoToIfUnset FLAG_DW_214_A, DWRoute214_FallFirst
    SetFlag FLAG_DW_214_B
    Message DWRoute214_Text_CyrusDriftHint
    WaitButton
    CloseMessage
    GoTo DWRoute214_FallEnd
DWRoute214_FallFirst:
    SetFlag FLAG_DW_214_A
DWRoute214_FallEnd:
    ReleaseAll
    End

DWRoute214_TalkCyrus:
    LockAll
    FacePlayer
    GoToIfSet FLAG_ARC2_RIFTB_B, DWRoute214_TalkCyrusPulled
    GoToIfSet FLAG_ARC2_RIFTB_A, DWRoute214_TalkCyrusLeft
    Message DWRoute214_Text_CyrusNoFloor
    GoTo DWRoute214_TalkEnd

DWRoute214_TalkCyrusPulled:
    Message DWRoute214_Text_CyrusMyHandWillMend
    GoTo DWRoute214_TalkEnd

DWRoute214_TalkCyrusLeft:
    Message DWRoute214_Text_CyrusFullStrength
DWRoute214_TalkEnd:
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
DWRoute214_Movement_PlayerFall:
    JumpOnSpotFastSouth
    SetInvisible
    EndMovement

    .balign 4, 0
DWRoute214_Movement_SetVisible:
    SetVisible
    EndMovement

    .balign 4, 0
DWRoute214_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
DWRoute214_Movement_StepOutOfTrees:
    WalkNormalWest 3
    FaceWest
    EndMovement

    .balign 4, 0
DWRoute214_Movement_CyrusPull:
    FaceEast
    Delay8
    JumpOnSpotFastEast
    EndMovement

    .balign 4, 0
DWRoute214_Movement_CyrusKneel:
    FaceSouth
    Delay16
    EndMovement

    .balign 4, 0
DWRoute214_Movement_CyrusStand:
    FaceWest
    EndMovement
