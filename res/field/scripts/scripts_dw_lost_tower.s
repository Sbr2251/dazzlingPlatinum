#include "macros/scrcmd.inc"
#include "generated/text_banks.h"
#include "res/text/bank/dw_lost_tower.h"
#include "res/text/bank/arc2_common.h"
#include "constants/totem_battle.h"

// Arc 2 rift 2.25-2.26, inside: MAP_HEADER_DW_LOST_TOWER, alone (owner rift-b, then set-tower for S7;
// docs/arc2/rift_contract.md and the orchestrator's Lost Tower ruling of 2026-10-11 00:45).
//   entry   Lost Tower 2F rift (6,8), at 92-94: Warp MAP_HEADER_DW_LOST_TOWER, 0, 20, 12, DIR_WEST
//   exit 1  first visit (VAR_ARC2_PROGRESS 92-93): the vein, then the wall of shadow, then
//           Warp MAP_HEADER_ROUTE_209_LOST_TOWER_2F, 0, 7, 8, DIR_EAST (progress unchanged, FLAG_ARC2_RIFTB_E set)
//   exit 2  second visit (94): the wall parts, Cyrus, the Spiritomb; VAR_ARC2_PROGRESS 95, then
//           Warp MAP_HEADER_ROUTE_209, 0, 568, 681, DIR_SOUTH
//
// Phase 0 floor: the Arc 1 seams floor (a DW B1F clone; tools/distortion_world/lost_tower.json, build_rift_b_maps.py).
// The seam is the arc1 one on the west wall x=11: on from the ledge (12..15,14), along the bottom under the trees,
// off at (12,23) onto the vein room (12..15,23). The wall of shadow (overlay object at (16,23)) closes the way deeper
// until it parts at 94. Falls: coord events on the chasm lips put the player back at the entry, as in Arc 1.
//
// S7, the ghost acts (set-tower; the step and frame hooks are Arc2DwLostTower_* in src/overlay009/ov9_02249960.c).
// In this first DW without Cyrus the totems the player calmed are the guides. At each seam the Resonator glows (its
// cut-in, with the totem's ghost) and a ghost totem acts; each act needs its FLAG_TOTEM_*, and without it a plain
// line plays and the way opens anyway.
//   1 Hitmonlee kicks shut the scar on the seam's second tile (11,y2,z14)  first visit (and any visit before the vein)
//   2 Vespiquen lights the true seam over the false one at the fork (z19)  first visit
//   3 Lapras lifts the sunk stepping stones east of the deeper ledge       second visit, past the wall of shadow
//   4 Skarmory carries the player from the last stone (32,22) over the gap to Cyrus's island (37..41, 21..23)
// Once the vein is found the wall's work stays done (the scar shut, the seam lit). Litwick candles burn at the seams.
//
// rift-b flags (see scripts_dw_route_214.s): FLAG_ARC2_RIFTB_C = first-seam memory shown, FLAG_ARC2_RIFTB_D = the
// shadow has parted, FLAG_ARC2_RIFTB_E (0x092F) = the vein found (s-hearthome reads it for the 2.25 call).
// set-tower adds no flags. fix2-lost (owner playtest round 2, "A fall in the Lost Tower replays the ghost acts"):
// each act plays once per save. A fall warps back to the entry and clears the map-locals below, so the acts used
// to replay; now each act also sets a persistent flag, and the step/frame hooks count an act as done if either its
// map-local or its flag says so. Flags (docs/arc2/registry.md, unused letters of finished blocks; lead: rename at
// merge):
//   FLAG_ARC2_RESONATOR_B (0x0925) = Hitmonlee's act (or its fallback line) done   (FLAG_ARC2_LOST_TOWER_ACT_HITMONLEE)
//   FLAG_ARC2_CELESTIC_B  (0x0943) = Vespiquen's act (or its fallback) done          (FLAG_ARC2_LOST_TOWER_ACT_VESPIQUEN)
//   FLAG_ARC2_CELESTIC_C  (0x0944) = Lapras's act (or its fallback) done: the stones stay up (..._ACT_LAPRAS)
//   FLAG_ARC2_CELESTIC_D  (0x0945) = the island reached once: Skarmory's act and Cyrus's two lines played. After a
//                                    blackout Skarmory (or the leap) still carries the player over the gap, the only
//                                    way to the island, but with no surge, cut-in or lines, and Cyrus goes straight
//                                    to the battle (FLAG_ARC2_LOST_TOWER_ISLAND_REACHED)
// Map-local (each load): VAR_MAP_LOCAL_1 wall acts done (1 Hitmonlee, 2 Vespiquen),
// VAR_MAP_LOCAL_2 memory coord done, VAR_MAP_LOCAL_3 always 0 (fall lips), VAR_MAP_LOCAL_4 vein coord done,
// VAR_MAP_LOCAL_5 shadow coord done, VAR_MAP_LOCAL_6 the ghosts' opacity (0-31, the frame hook fades toward it),
// VAR_MAP_LOCAL_7 deeper acts done (1 Lapras, 2 Skarmory).
// Phase 2 (dwp:rift-lt, docs/distortion_world/lost_tower.md): the puzzle tables live in
// src/overlay009/dw_puzzle_lost_tower.c (visit 1: fall lips + entry checkpoint, no groups; visit 2: groups,
// sigils, rune, checkpoints + the engine-b actor table: 4 pads + the shadow lane). The false seam is not a
// VOID tile in the tables: the step hook calls DwPuzzle_NotifyFall before its fall script. Pad prompts run from
// DWLostTower_PadPrompt (the step hook starts it on DW_ACTOR_EVENT_PAD_READY); the Skarmory carry reuses the
// Act 4 movements and calls DwActorsConfirmCarryDone. VAR_MAP_LOCAL_8 hint stage (1 first hint, 2 second),
// VAR_MAP_LOCAL_9 hint pending (the frame hook arms it, the init frame table starts the hint script).

#define LOCALID_SHADOW           0x84
#define LOCALID_CYRUS            0x85
#define LOCALID_SPIRITOMB        0x86
#define LOCALID_EMPOLEON         0x87
#define LOCALID_TORTERRA         0x88
#define LOCALID_INFERNAPE        0x89
#define LOCALID_GHOST_HITMONLEE  0x8A
#define LOCALID_GHOST_VESPIQUEN  0x8B
#define LOCALID_GHOST_SKARMORY   0x8C
#define LOCALID_GHOST_LAPRAS     0x8D

#define ENTRY_X 20
#define ENTRY_Z 12

// The Resonator cut-in's stand-in party slots, RESONATOR_SLOT(FIELD_MOVE_*) in include/field_move_tasks.h:
// Vespiquen (Cut), Skarmory (Fly), Lapras (Surf), Hitmonlee (Rock Smash).
#define RESONATOR_SLOT_VESPIQUEN 0xF0
#define RESONATOR_SLOT_SKARMORY  0xF1
#define RESONATOR_SLOT_LAPRAS    0xF2
#define RESONATOR_SLOT_HITMONLEE 0xF5

#define GHOST_OPACITY 26

    ScriptEntry DWLostTower_OnTransition
    ScriptEntry DWLostTower_Fall
    ScriptEntry DWLostTower_Memory
    ScriptEntry DWLostTower_Vein
    ScriptEntry DWLostTower_ShadowWall
    ScriptEntry DWLostTower_TalkCyrus
    ScriptEntry DWLostTower_ActHitmonlee
    ScriptEntry DWLostTower_ActVespiquen
    ScriptEntry DWLostTower_ActLapras
    ScriptEntry DWLostTower_ActSkarmory
    ScriptEntry DWLostTower_TalkLitwick
    ScriptEntry DWLostTower_PadPrompt
    ScriptEntry DWLostTower_FindCyrusV2
    ScriptEntry DWLostTower_Hint
    ScriptEntryEnd

DWLostTower_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

DWLostTower_End:
    End

// Coord events on the chasm lips, and the false seam (the step hook): the void sends the player back to the entry.
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

// The Resonator glows: its chime, the totem's surge line (TEXT_BANK_ARC2_COMMON, in VAR_0x8007) and the cut-in with
// the totem's ghost (VAR_0x8004 = its RESONATOR_SLOT).
DWLostTower_ResonatorGlows:
    PlayFanfare SEQ_SE_PL_KIRAKIRA
    WaitFanfare SEQ_SE_PL_KIRAKIRA
    MessageFromBank TEXT_BANK_ARC2_COMMON, VAR_0x8007
    WaitABXPadPress
    CloseMessage
    ScrCmd_0C5 VAR_0x8004
    Return

DWLostTower_GhostFadeIn:
    SetVar VAR_MAP_LOCAL_6, GHOST_OPACITY
    WaitTime 20, VAR_RESULT
    Return

DWLostTower_GhostFadeOut:
    SetVar VAR_MAP_LOCAL_6, 0
    WaitTime 20, VAR_RESULT
    Return

DWLostTower_ResonatorSilent:
    Message DWLostTower_Text_ResonatorSilent
    WaitABXPadPress
    Return

// Act 1 (step hook, on the scar, (11,y2,z14); it cracks underfoot): ghost Hitmonlee kicks the scar shut.
DWLostTower_ActHitmonlee:
    LockAll
    SetVar VAR_MAP_LOCAL_6, 0
    WaitTime 8, VAR_RESULT
    GoToIfUnset FLAG_TOTEM_HITMONLEE_DEFEATED, DWLostTower_NoHitmonlee
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeHitmonlee
    SetVar VAR_0x8004, RESONATOR_SLOT_HITMONLEE
    Call DWLostTower_ResonatorGlows
    ScrCmd_311 LOCALID_GHOST_HITMONLEE
    Call DWLostTower_GhostFadeIn
    PlayCry SPECIES_HITMONLEE
    WaitCry
    ApplyMovement LOCALID_GHOST_HITMONLEE, DWLostTower_Movement_HitmonleeLeap
    WaitMovement
    PlayFanfare SEQ_SE_DP_WALL_HIT2
    SetVar VAR_MAP_LOCAL_1, 1
    SetFlag FLAG_ARC2_RESONATOR_B
    ShakeCamera 12, 3
    ApplyMovement LOCALID_GHOST_HITMONLEE, DWLostTower_Movement_HitmonleeBack
    WaitMovement
    Message DWLostTower_Text_HitmonleeKicked
    WaitABXPadPress
    CloseMessage
    Call DWLostTower_GhostFadeOut
    ScrCmd_312 LOCALID_GHOST_HITMONLEE
    ReleaseAll
    End

DWLostTower_NoHitmonlee:
    Call DWLostTower_ResonatorSilent
    Message DWLostTower_Text_ScarHolds
    WaitABXPadPress
    CloseMessage
    SetVar VAR_MAP_LOCAL_1, 1
    SetFlag FLAG_ARC2_RESONATOR_B
    ReleaseAll
    End

// Act 2 (step hook, the fork (11,z19), after act 1): ghost Vespiquen lights the true seam over the false one.
DWLostTower_ActVespiquen:
    LockAll
    SetVar VAR_MAP_LOCAL_6, 0
    WaitTime 8, VAR_RESULT
    GoToIfUnset FLAG_TOTEM_VESPIQUEN_DEFEATED, DWLostTower_NoVespiquen
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeVespiquen
    SetVar VAR_0x8004, RESONATOR_SLOT_VESPIQUEN
    Call DWLostTower_ResonatorGlows
    ScrCmd_311 LOCALID_GHOST_VESPIQUEN
    Call DWLostTower_GhostFadeIn
    PlayCry SPECIES_VESPIQUEN
    WaitCry
    PlayFanfare SEQ_SE_DP_KIRAKIRA
    SetVar VAR_MAP_LOCAL_1, 2
    SetFlag FLAG_ARC2_CELESTIC_B
    ApplyMovement LOCALID_GHOST_VESPIQUEN, DWLostTower_Movement_VespiquenAlongSeam
    WaitMovement
    WaitFanfare SEQ_SE_DP_KIRAKIRA
    Message DWLostTower_Text_VespiquenLit
    WaitABXPadPress
    CloseMessage
    Call DWLostTower_GhostFadeOut
    ScrCmd_312 LOCALID_GHOST_VESPIQUEN
    ReleaseAll
    End

DWLostTower_NoVespiquen:
    Call DWLostTower_ResonatorSilent
    Message DWLostTower_Text_SeamAlone
    WaitABXPadPress
    CloseMessage
    SetVar VAR_MAP_LOCAL_1, 2
    SetFlag FLAG_ARC2_CELESTIC_B
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
// to 2F; from 94 on it parts, and the way deeper is open (Cyrus is beyond the stones and the gap).
DWLostTower_ShadowWall:
    SetVar VAR_MAP_LOCAL_5, 1
    LockAll
    GoToIfGe VAR_ARC2_PROGRESS, 94, DWLostTower_ShadowParts
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

DWLostTower_ShadowParts:
    GoToIfSet FLAG_ARC2_RIFTB_D, DWLostTower_ShadowPartsEnd
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8004, 15, DWLostTower_ShadowPartsEnd
    GoToIfNe VAR_0x8005, 23, DWLostTower_ShadowPartsEnd
    ApplyMovement LOCALID_PLAYER, DWLostTower_Movement_FaceEast
    WaitMovement
    // Giratina's shadow passes below (the Arc 1 fly-by, same floor), and the wall of shadow parts. No text.
    WaitTime 20, VAR_RESULT
    ScrCmd_321 3
    WaitTime 42, VAR_RESULT
    ScrCmd_322
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_SHADOW
    SetFlag FLAG_ARC2_RIFTB_D
    WaitTime 20, VAR_RESULT
DWLostTower_ShadowPartsEnd:
    ReleaseAll
    End

// Act 3 (step hook, the deeper ledge's east end (20,22), from 94): ghost Lapras sings the sunk stones up out of the
// mist. They hop from there (B1F's jump-twice tiles).
DWLostTower_ActLapras:
    LockAll
    SetVar VAR_MAP_LOCAL_6, 0
    ApplyMovement LOCALID_PLAYER, DWLostTower_Movement_FaceEast
    WaitMovement
    GoToIfUnset FLAG_TOTEM_LAPRAS_DEFEATED, DWLostTower_NoLapras
    Message DWLostTower_Text_StonesSunk
    WaitABXPadPress
    CloseMessage
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeLapras
    SetVar VAR_0x8004, RESONATOR_SLOT_LAPRAS
    Call DWLostTower_ResonatorGlows
    ScrCmd_311 LOCALID_GHOST_LAPRAS
    Call DWLostTower_GhostFadeIn
    ApplyMovement LOCALID_GHOST_LAPRAS, DWLostTower_Movement_LaprasRise
    WaitMovement
    PlayCry SPECIES_LAPRAS
    WaitCry
    PlayFanfare SEQ_SE_DP_NAMI
    SetVar VAR_MAP_LOCAL_7, 1
    SetFlag FLAG_ARC2_CELESTIC_C
    WaitTime 40, VAR_RESULT
    WaitFanfare SEQ_SE_DP_NAMI
    Message DWLostTower_Text_LaprasSang
    WaitABXPadPress
    CloseMessage
    Call DWLostTower_GhostFadeOut
    ScrCmd_312 LOCALID_GHOST_LAPRAS
    ReleaseAll
    End

DWLostTower_NoLapras:
    Message DWLostTower_Text_StonesSunk
    WaitABXPadPress
    Call DWLostTower_ResonatorSilent
    Message DWLostTower_Text_StonesDrift
    WaitABXPadPress
    CloseMessage
    SetVar VAR_MAP_LOCAL_7, 1
    SetFlag FLAG_ARC2_CELESTIC_C
    WaitTime 40, VAR_RESULT
    ReleaseAll
    End

// Act 4 (step hook, the last stone (32,22), after act 3): ghost Skarmory carries the player over the gap to the
// island, where Cyrus kneels beside the Spiritomb. Then 2.26's finding-Cyrus scene and the totem battle.
DWLostTower_ActSkarmory:
    LockAll
    SetVar VAR_MAP_LOCAL_6, 0
    ApplyMovement LOCALID_PLAYER, DWLostTower_Movement_FaceEast
    WaitMovement
    GoToIfUnset FLAG_TOTEM_SKARMORY_DEFEATED, DWLostTower_NoSkarmory
    // Back after a blackout: the ghost carries the player over again, with no surge, cut-in or lines
    GoToIfSet FLAG_ARC2_CELESTIC_D, DWLostTower_SkarmoryCarry
    Message DWLostTower_Text_GapTooWide
    WaitABXPadPress
    CloseMessage
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeSkarmory
    SetVar VAR_0x8004, RESONATOR_SLOT_SKARMORY
    Call DWLostTower_ResonatorGlows
DWLostTower_SkarmoryCarry:
    ScrCmd_311 LOCALID_GHOST_SKARMORY
    Call DWLostTower_GhostFadeIn
    PlayCry SPECIES_SKARMORY
    ApplyMovement LOCALID_GHOST_SKARMORY, DWLostTower_Movement_SkarmorySwoop
    WaitMovement
    WaitCry
    // Skarmory takes hold from above; the player is lifted and carried east over the void (5 tiles) to (37,22).
    PlayFanfare SEQ_SE_DP_PYUU2
    ApplyMovement LOCALID_PLAYER, DWLostTower_Movement_PlayerCarried
    ApplyMovement LOCALID_GHOST_SKARMORY, DWLostTower_Movement_SkarmoryCarry
    WaitMovement
    SetVar VAR_MAP_LOCAL_7, 2
    ApplyMovement LOCALID_GHOST_SKARMORY, DWLostTower_Movement_SkarmoryAway
    Call DWLostTower_GhostFadeOut
    WaitMovement
    ScrCmd_312 LOCALID_GHOST_SKARMORY
    GoToIfSet FLAG_ARC2_CELESTIC_D, DWLostTower_FindCyrus
    Message DWLostTower_Text_SkarmoryCarried
    WaitABXPadPress
    CloseMessage
    GoTo DWLostTower_FindCyrus
    End

DWLostTower_NoSkarmory:
    GoToIfSet FLAG_ARC2_CELESTIC_D, DWLostTower_NoSkarmoryLeap
    Message DWLostTower_Text_GapTooWide
    WaitABXPadPress
    Call DWLostTower_ResonatorSilent
    Message DWLostTower_Text_YouLeap
    WaitABXPadPress
    CloseMessage
DWLostTower_NoSkarmoryLeap:
    ApplyMovement LOCALID_PLAYER, DWLostTower_Movement_PlayerLeaps
    WaitMovement
    SetVar VAR_MAP_LOCAL_7, 2
    GoTo DWLostTower_FindCyrus
    End

// On the island, (37,22): Cyrus on his knees at (39,22), his starter fainted at (38,21), the Spiritomb at (41,22).
DWLostTower_FindCyrus:
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
    // His two lines once per save (FLAG_ARC2_CELESTIC_D): after a blackout he only looks up, and the battle starts
    GoToIfSet FLAG_ARC2_CELESTIC_D, DWLostTower_FindCyrusBattle
    SetFlag FLAG_ARC2_CELESTIC_D
    Message DWLostTower_Text_CyrusYouCame
    WaitABXPadPress
    Message DWLostTower_Text_CyrusHundredVoices
    WaitABXPadPress
    CloseMessage
DWLostTower_FindCyrusBattle:
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
    // Polish #6: Cyrus pays off 'I'll find it' (route_213 beach)
    Message DWLostTower_Text_CyrusProof
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

// Visit 2: the totem-echo pad prompt (step hook starts it on DW_ACTOR_EVENT_PAD_READY; the generic glue
// already suppressed the pad sigil's auto-fire). One entry for all four pads: the pad index comes from the
// player's tile (VAR_0x8006: 0 Hitmonlee (16,22), 1 Vespiquen (11,20), 2 Lapras (16,24), 3 Skarmory (32,22)).
// Yes calls DwActorsResolvePad: NONE = No (nothing more) or Yes-denied (the totem has not been calmed);
// CUTIN = play the Resonator ghost cut-in + the totem's cry + its effect line; CARRY_REQUESTED = Skarmory,
// play the cut-in, then the Act 4 carry, then DwActorsConfirmCarryDone. A denied pad is not marked used, so
// stepping on it again re-prompts.
DWLostTower_PadPrompt:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8004, 11, DWLostTower_PadPromptVespiquen
    GoToIfEq VAR_0x8004, 32, DWLostTower_PadPromptSkarmory
    GoToIfEq VAR_0x8005, 24, DWLostTower_PadPromptLapras
    GoTo DWLostTower_PadPromptHitmonlee
    End

DWLostTower_PadPromptHitmonlee:
    SetVar VAR_0x8006, 0
    Message DWLostTower_Text_PadPromptHitmonlee
    GoTo DWLostTower_PadAsk
    End

DWLostTower_PadPromptVespiquen:
    SetVar VAR_0x8006, 1
    Message DWLostTower_Text_PadPromptVespiquen
    GoTo DWLostTower_PadAsk
    End

DWLostTower_PadPromptLapras:
    SetVar VAR_0x8006, 2
    Message DWLostTower_Text_PadPromptLapras
    GoTo DWLostTower_PadAsk
    End

DWLostTower_PadPromptSkarmory:
    SetVar VAR_0x8006, 3
    Message DWLostTower_Text_PadPromptSkarmory
    GoTo DWLostTower_PadAsk
    End

DWLostTower_PadAsk:
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, DWLostTower_PadNo
    SetVar VAR_0x8007, 1
    CloseMessage
    GoTo DWLostTower_PadResolve
    End

DWLostTower_PadNo:
    SetVar VAR_0x8007, 0
    CloseMessage
    GoTo DWLostTower_PadResolve
    End

DWLostTower_PadResolve:
    DwActorsResolvePad VAR_0x8006, VAR_0x8007, VAR_0x8008
    GoToIfEq VAR_0x8008, 3, DWLostTower_PadCutin
    GoToIfEq VAR_0x8008, 4, DWLostTower_PadCarry
    GoToIfEq VAR_0x8007, 0, DWLostTower_PadEnd
    Message DWLostTower_Text_PadDenied
    WaitABXPadPress
    CloseMessage
    GoTo DWLostTower_PadEnd
    End

DWLostTower_PadCutin:
    DwActorsTakePendingCutin VAR_0x8009
    GoToIfEq VAR_0x8009, 0, DWLostTower_PadCutinHitmonlee
    GoToIfEq VAR_0x8009, 1, DWLostTower_PadCutinVespiquen
    GoToIfEq VAR_0x8009, 2, DWLostTower_PadCutinLapras
    GoTo DWLostTower_PadEnd
    End

DWLostTower_PadCutinHitmonlee:
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeHitmonlee
    SetVar VAR_0x8004, RESONATOR_SLOT_HITMONLEE
    Call DWLostTower_ResonatorGlows
    PlayCry SPECIES_HITMONLEE
    WaitCry
    Message DWLostTower_Text_PadEffectHitmonlee
    WaitABXPadPress
    CloseMessage
    GoTo DWLostTower_PadEnd
    End

DWLostTower_PadCutinVespiquen:
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeVespiquen
    SetVar VAR_0x8004, RESONATOR_SLOT_VESPIQUEN
    Call DWLostTower_ResonatorGlows
    PlayCry SPECIES_VESPIQUEN
    WaitCry
    Message DWLostTower_Text_PadEffectVespiquen
    WaitABXPadPress
    CloseMessage
    GoTo DWLostTower_PadEnd
    End

DWLostTower_PadCutinLapras:
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeLapras
    SetVar VAR_0x8004, RESONATOR_SLOT_LAPRAS
    Call DWLostTower_ResonatorGlows
    PlayCry SPECIES_LAPRAS
    WaitCry
    Message DWLostTower_Text_LaprasSang
    WaitABXPadPress
    CloseMessage
    GoTo DWLostTower_PadEnd
    End

// Skarmory: the cut-in (as in Act 4), then the carry with the Act 4
// movements. The carry never chains to Find Cyrus here: the gate is
// still closed at the landing (37,22). ConfirmCarryDone clears the
// actor's carryPending; the shadow cannot catch during the carry.
DWLostTower_PadCarry:
    DwActorsTakePendingCutin VAR_0x8009
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeSkarmory
    SetVar VAR_0x8004, RESONATOR_SLOT_SKARMORY
    Call DWLostTower_ResonatorGlows
    ScrCmd_311 LOCALID_GHOST_SKARMORY
    Call DWLostTower_GhostFadeIn
    PlayCry SPECIES_SKARMORY
    ApplyMovement LOCALID_GHOST_SKARMORY, DWLostTower_Movement_SkarmorySwoop
    WaitMovement
    WaitCry
    PlayFanfare SEQ_SE_DP_PYUU2
    ApplyMovement LOCALID_PLAYER, DWLostTower_Movement_PlayerCarried
    ApplyMovement LOCALID_GHOST_SKARMORY, DWLostTower_Movement_SkarmoryCarry
    WaitMovement
    ApplyMovement LOCALID_GHOST_SKARMORY, DWLostTower_Movement_SkarmoryAway
    Call DWLostTower_GhostFadeOut
    WaitMovement
    ScrCmd_312 LOCALID_GHOST_SKARMORY
    DwActorsConfirmCarryDone
    Message DWLostTower_Text_SkarmoryCarried
    WaitABXPadPress
    CloseMessage
    GoTo DWLostTower_PadEnd
    End

DWLostTower_PadEnd:
    ReleaseAll
    End

// Visit 2: Find Cyrus, starting from (38,22) (step hook). The initial
// PlayerToCyrus movement is gone: the player is already at (38,22),
// and moving east would walk into Cyrus at (39,22). Starter reveal,
// Cyrus's two lines (once per save) and the battle are as in Phase 0:
// jump into DWLostTower_FindCyrusBattle once the scene is set.
DWLostTower_FindCyrusV2:
    LockAll
    GetPlayerStarterSpecies VAR_0x8006
    CallIfEq VAR_0x8006, SPECIES_TURTWIG, DWLostTower_ShowEmpoleon
    CallIfEq VAR_0x8006, SPECIES_CHIMCHAR, DWLostTower_ShowTorterra
    CallIfEq VAR_0x8006, SPECIES_PIPLUP, DWLostTower_ShowInfernape
    WaitTime 30, VAR_RESULT
    ApplyMovement LOCALID_CYRUS, DWLostTower_Movement_CyrusLooksUp
    WaitMovement
    GoToIfSet FLAG_ARC2_CELESTIC_D, DWLostTower_FindCyrusBattle
    SetFlag FLAG_ARC2_CELESTIC_D
    Message DWLostTower_Text_CyrusYouCame
    WaitABXPadPress
    Message DWLostTower_Text_CyrusHundredVoices
    WaitABXPadPress
    CloseMessage
    GoTo DWLostTower_FindCyrusBattle
    End

// Cyrus's hint after two falls (Ruth's voice in the Resonator; the
// frame hook arms VAR_MAP_LOCAL_9, the init frame table starts this).
// Clear the pending flag first (the HoneyFall pattern): the fall
// counter lives in the engine, this var is only the trigger.
DWLostTower_Hint:
    SetVar VAR_MAP_LOCAL_9, 0
    LockAll
    GoToIfEq VAR_MAP_LOCAL_8, 2, DWLostTower_HintRune
    GoToIfGe VAR_ARC2_PROGRESS, 94, DWLostTower_HintDeeper
    Message DWLostTower_Text_HintWall
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

DWLostTower_HintDeeper:
    Message DWLostTower_Text_HintDeeper
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

DWLostTower_HintRune:
    Message DWLostTower_Text_HintRune
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// A on a Litwick candle (decor objects; a stand-in sprite until a Litwick overworld sprite exists).
DWLostTower_TalkLitwick:
    LockAll
    PlayCry SPECIES_LITWICK
    Message DWLostTower_Text_Litwick
    WaitCry
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

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

// Hitmonlee, on the wall just above the scar (11,y3,z14): a wind-up hop, then the kick (a second, sharper hop and
// the thud); then it hops back up.
    .balign 4, 0
DWLostTower_Movement_HitmonleeLeap:
    JumpOnSpotSlowSouth
    JumpOnSpotFastSouth
    EndMovement

    .balign 4, 0
DWLostTower_Movement_HitmonleeBack:
    JumpOnSpotFastSouth
    EndMovement

// Vespiquen, over the fork on the true seam (11,y3,z20), flies along it to where it comes down (z22).
    .balign 4, 0
DWLostTower_Movement_VespiquenAlongSeam:
    WalkSlowSouth
    WalkSlowSouth
    FaceNorth
    EndMovement

// Lapras rises from the mist in front of the first sunk stone: (22,21) -> (22,22).
    .balign 4, 0
DWLostTower_Movement_LaprasRise:
    WalkSlowSouth
    FaceWest
    EndMovement

// Skarmory swoops from (33,21) to above the player, (32,21).
    .balign 4, 0
DWLostTower_Movement_SkarmorySwoop:
    LockDir
    WalkFastWest
    UnlockDir
    FaceEast
    EndMovement

    .balign 4, 0
DWLostTower_Movement_SkarmoryCarry:
    JumpOnSpotFastEast
    WalkNormalEast 5
    EndMovement

    .balign 4, 0
DWLostTower_Movement_SkarmoryAway:
    WalkFastNorth 3
    EndMovement

// The player hangs from Skarmory's talons: no walking cycle while carried east to (37,22).
    .balign 4, 0
DWLostTower_Movement_PlayerCarried:
    JumpOnSpotFastEast
    PauseAnimation
    WalkNormalEast 5
    ResumeAnimation
    EndMovement

// No Skarmory: a long leap over the gap, (32,22) -> (37,22).
    .balign 4, 0
DWLostTower_Movement_PlayerLeaps:
    JumpFarEast
    JumpNearFastEast
    JumpNearFastEast
    JumpNearFastEast
    EndMovement

// (37,22) -> (38,22), beside Cyrus (39,22); his starter lies at (38,21)
    .balign 4, 0
DWLostTower_Movement_PlayerToCyrus:
    WalkNormalEast
    FaceEast
    EndMovement

    .balign 4, 0
DWLostTower_Movement_CyrusLooksUp:
    FaceWest
    EndMovement
