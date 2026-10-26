#include "macros/scrcmd.inc"
#include "res/text/bank/distortion_world_arc1_seams.h"

// Arc 1 "Distortion World Puzzle 1 - Wall Walk" (Phase 0, cloned from DW B1F; see docs/arc1/revision/spec.md).
// Entry from Lake Verity at (20,12) facing west (state 5). The seam runs on the west wall x=11, z 13-22: step on from
// the jump-on ledge (12,14), pass under the two wall trees along the bottom row, fork at z=19 (a dead-end corner up
// the wall, the way on goes along the bottom), drop off at (12,23) onto the briefcase platform. Falls: coord events on the chasm lips. Cyrus and Barry are DW overlay objects
// (src/overlay009 sArc1SeamsObjects), spawned by VAR_ARC1_DW_HINTS:
//   VAR_ARC1_DW_HINTS  0 nothing shown, 1 seam hint given, 2 fork reached, 3 briefcase reached (scene re-runs),
//                      4 starter chosen (battle-only re-entry), 5 Mawile fought
//   VAR_ARC1_DW_FALLS  0 entry scene (Barry's demo fall) not played yet, then 1 + the player's falls

#define LOCALID_CYRUS_ENTRY     0x80
#define LOCALID_BARRY_ENTRY     0x81
#define LOCALID_MAWILE_GLIMPSE  0x82 // unused since the fork shows GIRATINA's shadow instead (overlay entry kept)
#define LOCALID_MAWILE          0x83
#define LOCALID_BRIEFCASE       0x84
#define LOCALID_CYRUS_CASE      0x85
#define LOCALID_BARRY_CASE      0x86

#define ENTRY_X 20
#define ENTRY_Z 12

    ScriptEntry DistortionWorldArc1Seams_OnTransition
    ScriptEntry DistortionWorldArc1Seams_Fall
    ScriptEntry DistortionWorldArc1Seams_EntryScene
    ScriptEntry DistortionWorldArc1Seams_SeamHint
    ScriptEntry DistortionWorldArc1Seams_Fork
    ScriptEntry DistortionWorldArc1Seams_Briefcase
    ScriptEntry DistortionWorldArc1Seams_TalkCyrus
    ScriptEntry DistortionWorldArc1Seams_TalkBarry
    ScriptEntryEnd

DistortionWorldArc1Seams_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

// Coord events on the chasm lips (VAR_ARC1_PROGRESS 5): the player drops into the void and the world puts them
// back at the entry. Cyrus's retry line plays once (the first fall); the seam hint follows if not given yet.
DistortionWorldArc1Seams_Fall:
    LockAll
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_PlayerFall
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_SetVisible
    WaitMovement
    ResetDistortionWorldPersistedCameraAngles
    AddVar VAR_ARC1_DW_FALLS, 1
    CallIfGt VAR_ARC1_DW_FALLS, 99, DistortionWorldArc1Seams_CapFalls
    Warp MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS, 0, ENTRY_X, ENTRY_Z, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    CallIfEq VAR_ARC1_DW_FALLS, 2, DistortionWorldArc1Seams_RetryLine
    GoToIfEq VAR_ARC1_DW_HINTS, 0, DistortionWorldArc1Seams_SeamHintLocked
    ReleaseAll
    End

DistortionWorldArc1Seams_CapFalls:
    SetVar VAR_ARC1_DW_FALLS, 99
    Return

DistortionWorldArc1Seams_RetryLine:
    Message DistortionWorldArc1Seams_Text_CyrusBackWhereWeStarted
    WaitABXPadPress
    CloseMessage
    Return

// First frame at state 5: Cyrus's entry line, then Barry's demo fall.
DistortionWorldArc1Seams_EntryScene:
    LockAll
    GoToIfNe VAR_ARC1_PROGRESS, 5, DistortionWorldArc1Seams_EntrySkip
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceEast
    WaitMovement
    Message DistortionWorldArc1Seams_Text_CyrusStayClose
    WaitABXPadPress
    CloseMessage
    BufferRivalName 0
    ApplyMovement LOCALID_BARRY_ENTRY, DistortionWorldArc1Seams_Movement_BarryExcited
    WaitMovement
    Message DistortionWorldArc1Seams_Text_BarryIllJustJumpIt
    CloseMessage
    ApplyMovement LOCALID_BARRY_ENTRY, DistortionWorldArc1Seams_Movement_BarryJump
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_PlayerWatchBarry
    WaitMovement
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_BARRY_ENTRY
    WaitTime 50, VAR_RESULT
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_311 LOCALID_BARRY_ENTRY
    ApplyMovement LOCALID_BARRY_ENTRY, DistortionWorldArc1Seams_Movement_BarryDazed
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceEast
    WaitMovement
    BufferRivalName 0
    Message DistortionWorldArc1Seams_Text_BarryIMeantToDoThat
    WaitABXPadPress
    Message DistortionWorldArc1Seams_Text_CyrusTheVoidSendsItBack
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceWest
    WaitMovement
DistortionWorldArc1Seams_EntrySkip:
    SetVar VAR_ARC1_DW_FALLS, 1
    ReleaseAll
    End

// Show, then hint: from the step hook (20 idle steps on the floors) or after a fall.
DistortionWorldArc1Seams_SeamHint:
    GoToIfNe VAR_ARC1_DW_HINTS, 0, DistortionWorldArc1Seams_End
    LockAll
DistortionWorldArc1Seams_SeamHintLocked:
    Message DistortionWorldArc1Seams_Text_CyrusWalkTheSeam
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC1_DW_HINTS, 1
    ReleaseAll
    End

// Step hook at the fork on the wall (x=11, z=19, any row): Cyrus calls out, then GIRATINA's shadow (the stock DW
// fly-by model, ov9 fly-by entry 3) passes once through the void below the briefcase platform. Only the player
// notices it: the narration is theirs, and nobody comments. The Mawile stays hidden until it lunges at the case.
DistortionWorldArc1Seams_Fork:
    GoToIfGe VAR_ARC1_DW_HINTS, 2, DistortionWorldArc1Seams_End
    LockAll
    SetVar VAR_ARC1_DW_HINTS, 2
    Message DistortionWorldArc1Seams_Text_CyrusTheSeamSplits
    WaitABXPadPress
    CloseMessage
    WaitTime 10, VAR_RESULT
    ScrCmd_321 3
    WaitTime 42, VAR_RESULT
    ScrCmd_322
    WaitTime 8, VAR_RESULT
    Message DistortionWorldArc1Seams_Text_SomethingMovedBelow
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

DistortionWorldArc1Seams_End:
    End

// Coord event at (14,23) on the briefcase platform (or A on the case).
// New order (Mawile-first, Platinum Starly beat): the Mawile charges the player, Cyrus orders the player
// to grab a Pokemon from the case, the starter select runs, Barry grabs his in the scramble, and the battle
// starts at once. The whole scene runs locked in this one script, so no fall can interrupt it mid-way.
// Re-entry: HINTS 3 (briefcase reached, starter not yet chosen) re-runs the whole scene; HINTS 4 (starter
// chosen, Mawile not yet fought) skips to the battle. Both states are only reachable from a crafted save
// or a battle reload in normal play, but neither soft-locks.
DistortionWorldArc1Seams_Briefcase:
    GoToIfGe VAR_ARC1_DW_HINTS, 5, DistortionWorldArc1Seams_End
    GoToIfEq VAR_ARC1_DW_HINTS, 4, DistortionWorldArc1Seams_BriefcaseMawileOnly
    GoToIfEq VAR_ARC1_DW_HINTS, 3, DistortionWorldArc1Seams_BriefcaseResetActors
    LockAll
    SetVar VAR_ARC1_DW_HINTS, 3
DistortionWorldArc1Seams_BriefcaseScene:
    // Cyrus folds space: he steps through a rift at the entry and out beside the briefcase, then pulls Barry after
    Message DistortionWorldArc1Seams_Text_CyrusTheWorldFolds
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_CYRUS_ENTRY
    ScrCmd_311 LOCALID_CYRUS_CASE
    WaitTime 20, VAR_RESULT
    BufferRivalName 0
    Message DistortionWorldArc1Seams_Text_BarryHeyWaitUp
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_BARRY_ENTRY
    ScrCmd_311 LOCALID_BARRY_CASE
    WaitTime 20, VAR_RESULT
    BufferRivalName 0
    Message DistortionWorldArc1Seams_Text_BarryHowDidWeDoThat
    WaitABXPadPress
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfLt VAR_0x8004, 15, DistortionWorldArc1Seams_StepToCase
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceEast
    WaitMovement
    Message DistortionWorldArc1Seams_Text_CyrusThereRowansCase
    WaitABXPadPress
    CloseMessage
    // A short beat, then the Mawile charges out of the dark straight at the player, along the player's
    // row: it appears at (18,23), runs west to (17,23) while the player stumbles back, then vaults the
    // briefcase with a far jump and lands at (15,23), right in front of the player, facing them.
    // Cyrus and Barry are on the rows either side (22 and 24) and out of its path.
    WaitTime 24, VAR_RESULT
    PlayFanfare SEQ_SE_PL_SYUWA
    // The Mawile is script-only (overlay condition 6): it spawns on no map load, so it stays hidden until
    // this ScrCmd_311, at any HINTS value. Never gate it on HINTS == 4 again: that condition auto-spawns it
    // on a HINTS 4 map load, visible before the lunge.
    ScrCmd_311 LOCALID_MAWILE
    ApplyMovement LOCALID_MAWILE, DistortionWorldArc1Seams_Movement_MawileChargeApproach
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_PlayerKnockedBack
    ApplyMovement LOCALID_BARRY_CASE, DistortionWorldArc1Seams_Movement_BarryStartled
    ApplyMovement LOCALID_CYRUS_CASE, DistortionWorldArc1Seams_Movement_FaceEast
    WaitMovement
    ApplyMovement LOCALID_MAWILE, DistortionWorldArc1Seams_Movement_MawileChargeVault
    WaitMovement
    PlayCry SPECIES_MAWILE
    WaitCry
    // Forced pick: Cyrus came with no Pokemon, so it has to be the player. Barry panics.
    Message DistortionWorldArc1Seams_Text_CyrusTakeOneFromTheCase
    WaitABXPadPress
    CloseMessage
    BufferRivalName 0
    Message DistortionWorldArc1Seams_Text_BarryGrabOneQuick
    WaitABXPadPress
    CloseMessage
    // Starter select (the block moved here from the Lake Verity terrace)
    FadeScreenOut
    WaitFadeScreen
    StartChooseStarterScene
    SaveChosenStarter
    ReturnToField
    FadeScreenIn
    WaitFadeScreen
    GetPlayerStarterSpecies VAR_0x8000
    GivePokemon VAR_0x8000, 5, ITEM_NONE, VAR_RESULT
    SetVar VAR_ARC1_DW_HINTS, 4
    PlayFanfare SEQ_SE_CONFIRM
    ScrCmd_312 LOCALID_BRIEFCASE
    WaitFanfare SEQ_SE_CONFIRM
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceSouth
    ApplyMovement LOCALID_BARRY_CASE, DistortionWorldArc1Seams_Movement_FaceNorth
    WaitMovement
    BufferRivalName 0
    BufferRivalStarterSpeciesName 2
    Message DistortionWorldArc1Seams_Text_BarryIllTakeThisOne
    WaitABXPadPress
    CloseMessage
    // The Mawile already lunged and is waiting: straight into the battle, no second lunge.
    StartArc1MawileBattle
DistortionWorldArc1Seams_AfterMawileBattle:
    HealParty
    // The Mawile drops a shard and fades into the dark; Cyrus picks it up. Win, loss or running away (the battle
    // allows it, and running always works) all lead here; running only changes the narration line.
    GetBattleResult VAR_0x8004
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_FaceEast
    WaitMovement
    CallIfEq VAR_0x8004, BATTLE_RESULT_PLAYER_FLED, DistortionWorldArc1Seams_MawileFledLine
    CallIfNe VAR_0x8004, BATTLE_RESULT_PLAYER_FLED, DistortionWorldArc1Seams_MawileDroppedLine
    PlayFanfare SEQ_SE_PL_SYUWA
    // Re-show the Mawile before hiding it: if the battle reloaded the map, the script-only Mawile did not
    // respawn, and ScrCmd_312 on a missing object asserts. The 311 is a no-op (same frame, not rendered)
    // if the Mawile was retained through the battle.
    ScrCmd_311 LOCALID_MAWILE
    ScrCmd_312 LOCALID_MAWILE
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_CYRUS_CASE, DistortionWorldArc1Seams_Movement_CyrusPickUpShard
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_PlayerWatchCyrus
    WaitMovement
    PlayFanfare SEQ_SE_CONFIRM
    WaitFanfare SEQ_SE_CONFIRM
    Message DistortionWorldArc1Seams_Text_CyrusIKnowThisHum
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC1_DW_HINTS, 5
    SetVar VAR_ARC1_PROGRESS, 6
    // The exit rift opens beside the briefcase spot
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    ApplyMovement LOCALID_CYRUS_CASE, DistortionWorldArc1Seams_Movement_FaceWest
    WaitMovement
    Message DistortionWorldArc1Seams_Text_CyrusTheWorldIsClosing
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    SetVar VAR_ARC1_PROGRESS, 7
    Warp MAP_HEADER_LAKE_VERITY, 0, 32, 31, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

// Recovery for HINTS 4 (starter chosen, Mawile not yet fought): ScrCmd_311 spawns the Mawile from its
// configured tile, it charges again, then straight into the shared battle / post-battle flow. No starter
// select: the player already has their starter.
DistortionWorldArc1Seams_BriefcaseMawileOnly:
    LockAll
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_311 LOCALID_MAWILE
    ApplyMovement LOCALID_MAWILE, DistortionWorldArc1Seams_Movement_MawileChargeApproach
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_PlayerKnockedBack
    ApplyMovement LOCALID_BARRY_CASE, DistortionWorldArc1Seams_Movement_BarryStartled
    ApplyMovement LOCALID_CYRUS_CASE, DistortionWorldArc1Seams_Movement_FaceEast
    WaitMovement
    ApplyMovement LOCALID_MAWILE, DistortionWorldArc1Seams_Movement_MawileChargeVault
    WaitMovement
    PlayCry SPECIES_MAWILE
    WaitCry
    Message DistortionWorldArc1Seams_Text_CyrusItStillStands
    WaitABXPadPress
    CloseMessage
    StartArc1MawileBattle
    GoTo DistortionWorldArc1Seams_AfterMawileBattle

// Re-entry at HINTS 3: a fresh map load already spawned Cyrus and Barry at the case and left the entry
// actors unspawned, so the fold below would narrate them crossing while they stand at the case. Put the
// actors back at the entry first (hide the case actors, briefly drop HINTS to 2 so the entry actors'
// condition, HINTS < 3, passes their ScrCmd_311, then restore HINTS 3) and join the shared scene.
DistortionWorldArc1Seams_BriefcaseResetActors:
    LockAll
    ScrCmd_312 LOCALID_CYRUS_CASE
    ScrCmd_312 LOCALID_BARRY_CASE
    SetVar VAR_ARC1_DW_HINTS, 2
    ScrCmd_311 LOCALID_CYRUS_ENTRY
    ScrCmd_311 LOCALID_BARRY_ENTRY
    SetVar VAR_ARC1_DW_HINTS, 3
    GoTo DistortionWorldArc1Seams_BriefcaseScene

DistortionWorldArc1Seams_MawileDroppedLine:
    Message DistortionWorldArc1Seams_Text_MawileDroppedSomething
    WaitABXPadPress
    CloseMessage
    Return

DistortionWorldArc1Seams_MawileFledLine:
    Message DistortionWorldArc1Seams_Text_MawileFledIntoTheDark
    WaitABXPadPress
    CloseMessage
    Return

DistortionWorldArc1Seams_StepToCase:
    ApplyMovement LOCALID_PLAYER, DistortionWorldArc1Seams_Movement_PlayerStepToCase
    WaitMovement
    Return

DistortionWorldArc1Seams_TalkCyrus:
    LockAll
    FacePlayer
    GoToIfGe VAR_ARC1_DW_HINTS, 3, DistortionWorldArc1Seams_TalkCyrusCase
    GoToIfGe VAR_ARC1_DW_HINTS, 1, DistortionWorldArc1Seams_TalkCyrusHinted
    Message DistortionWorldArc1Seams_Text_CyrusWatchAndListen
    GoTo DistortionWorldArc1Seams_TalkEnd

DistortionWorldArc1Seams_TalkCyrusHinted:
    Message DistortionWorldArc1Seams_Text_CyrusTheWallWillHoldYou
    GoTo DistortionWorldArc1Seams_TalkEnd

DistortionWorldArc1Seams_TalkCyrusCase:
    Message DistortionWorldArc1Seams_Text_CyrusStayNearMe
    GoTo DistortionWorldArc1Seams_TalkEnd

DistortionWorldArc1Seams_TalkBarry:
    LockAll
    FacePlayer
    BufferRivalName 0
    Message DistortionWorldArc1Seams_Text_BarryHurryUp
DistortionWorldArc1Seams_TalkEnd:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
DistortionWorldArc1Seams_Movement_PlayerFall:
    JumpOnSpotFastSouth
    SetInvisible
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_SetVisible:
    SetVisible
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_BarryExcited:
    FaceSouth
    JumpOnSpotFastSouth 2
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_BarryJump:
    WalkFastSouth
    JumpFarSouth
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_PlayerWatchBarry:
    Delay8
    FaceSouth
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_BarryDazed:
    FaceWest
    Delay8
    FaceNorth
    Delay8
    FaceWest
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_PlayerStepToCase:
    WalkNormalEast
    EndMovement

// The Mawile charges straight at the player along row 23. Approach: from its spawn at (18,23) west to
// (17,23), east of the briefcase, while the player stumbles back. Vault: a far jump over the briefcase
// at (16,23) to land at (15,23), right in front of the player, facing them. Cyrus (row 22) and Barry
// (row 24) are out of its path. Split into two movements so the vault only fires once the player has
// left (15,23): the Mawile must never land on the player's tile.
    .balign 4, 0
DistortionWorldArc1Seams_Movement_MawileChargeApproach:
    FaceWest
    WalkFastWest 1
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_MawileChargeVault:
    JumpFarWest
    FaceWest
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_PlayerKnockedBack:
    EmoteExclamationMark
    LockDir
    JumpNearFastWest
    UnlockDir
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_BarryStartled:
    FaceEast
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
DistortionWorldArc1Seams_Movement_CyrusPickUpShard:
    WalkNormalEast
    FaceSouth
    Delay16
    FaceWest
    EndMovement

// Cyrus picks the shard up from the briefcase spot (16,23) standing on (16,22). Both are on the player's east side
// (15,23), and this map's camera draws an east-facing sprite turned toward Cyrus; FaceNorth was drawn with the
// player's back to him for the whole exchange. Keep the player facing east (the shard spot and Cyrus).
    .balign 4, 0
DistortionWorldArc1Seams_Movement_PlayerWatchCyrus:
    Delay16
    FaceEast
    EndMovement
