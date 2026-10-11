#include "macros/scrcmd.inc"
#include "res/text/bank/dw_route_213.h"
#include "constants/totem_battle.h"

// Arc 2 rift 2.21, inside: MAP_HEADER_DW_ROUTE_213, the Drowned Lake (owner rift-b; docs/arc2/rift_contract.md).
//   entry   the Route 213 cave rift sets VAR_ARC2_PROGRESS 83, then Warp MAP_HEADER_DW_ROUTE_213, 0, 20, 12, DIR_WEST
//   exit    Warp MAP_HEADER_ROUTE_213, 0, 715, 831, DIR_SOUTH, after the calm (VAR_ARC2_PROGRESS 84)
//
// Phase 0 floor: the DW B4F clone (tools/distortion_world/route_213.json, build_rift_b_maps.py), as on Route 214.
// The swallowed Lake Valor: what is left of the water lies in the pool; the ledge beside it (31-32, 20-23, past
// the first hop) holds the rusted frame (31,20) and the worn Trainer Card (32,20); the lake itself hangs overhead
// as the ceiling. The way on: hop the chasm and
// the pool, climb the east wall (x=49) and walk the ceiling (y=10, the stock B4F ceiling grid) under the "lake".
// The Lapras rises at the far end of the ceiling (z >= 45; step hook Arc2DwRoute213_HandleStep runs entry 4).
//
// rift-b flags: see scripts_dw_route_214.s. Here: FLAG_UNK_0x092E = FLAG_ARC2_ELIAS_CARD (the card picked up).
// Map-local: VAR_MAP_LOCAL_1 entry line played this load (not VAR_MAP_LOCAL_0: see scripts_dw_route_214.s).
// DW overlay objects (src/overlay009 sArc2DwRoute213Objects): 0x80 Cyrus at the entry, 0x81 the rusted frame,
// 0x82 the card, 0x83 the Lapras in the pool.

#define LOCALID_CYRUS  0x80
#define LOCALID_FRAME  0x81
#define LOCALID_CARD   0x82
#define LOCALID_LAPRAS 0x83

#define ENTRY_X 20
#define ENTRY_Z 12

    ScriptEntry DWRoute213_OnTransition
    ScriptEntry DWRoute213_EntryScene
    ScriptEntry DWRoute213_Card
    ScriptEntry DWRoute213_Totem
    ScriptEntry DWRoute213_TalkCyrus
    ScriptEntryEnd

DWRoute213_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

// First frame of every load (init script, VAR_MAP_LOCAL_1 == 0): Cyrus's line, only on the entry tile.
DWRoute213_EntryScene:
    SetVar VAR_MAP_LOCAL_1, 1
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8004, ENTRY_X, DWRoute213_End
    GoToIfNe VAR_0x8005, ENTRY_Z, DWRoute213_End
    GoToIfSet FLAG_TOTEM_LAPRAS_DEFEATED, DWRoute213_End
    LockAll
    // The rift drops the player among the trees at (20,12); step out to (17,12), beside Cyrus (16,12)
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_PLAYER, DWRoute213_Movement_StepOutOfTrees
    WaitMovement
    Message DWRoute213_Text_CyrusThereWasALake
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

DWRoute213_End:
    End

// A on the card beside the rusted frame. Nobody comments: Cyrus is back at the entry, out of earshot.
DWRoute213_Card:
    LockAll
    PlayFanfare SEQ_SE_CONFIRM
    WaitFanfare SEQ_SE_CONFIRM
    Message DWRoute213_Text_OldTrainerCard
    WaitABXPadPress
    CloseMessage
    SetFlag FLAG_ARC2_ELIAS_CARD
    ScrCmd_312 LOCALID_CARD
    ReleaseAll
    End

// Step hook: the far end of the ceiling, under the hanging lake. The Lapras rises out of the pool below to meet the
// player, and the battle starts.
DWRoute213_Totem:
    GoToIfSet FLAG_TOTEM_LAPRAS_DEFEATED, DWRoute213_End
    LockAll
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_LAPRAS
    PlayCry SPECIES_LAPRAS
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitCry
    PlayBattleMusic SEQ_BATTLE_TOTEM
    StartTotemBattle TOTEM_ENCOUNTER_LAPRAS
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, DWRoute213_TotemLost
    SetFlag FLAG_TOTEM_LAPRAS_DEFEATED
    SetFlag FLAG_HIDE_TOTEM_LAPRAS
    // The battle reload put it back in the pool: the aura drains and it swims up into the hanging lake
    PlayFanfare SEQ_SE_PL_SYUWA
    ScrCmd_312 LOCALID_LAPRAS
    WaitTime 20, VAR_RESULT
    // A sound effect, not PlaySound SEQ_FANFA4 (that pauses the music and the exit Warp then hangs)
    BufferPlayerName 0
    PlayFanfare SEQ_SE_DP_KIRAKIRA
    Message DWRoute213_Text_GotCalmShard
    WaitFanfare SEQ_SE_DP_KIRAKIRA
    WaitABXPadPress
    Message DWRoute213_Text_CyrusYouFixedItAnyway
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 84
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    Warp MAP_HEADER_ROUTE_213, 0, 715, 831, DIR_SOUTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

DWRoute213_TotemLost:
    BlackOutFromBattle
    ReleaseAll
    End

DWRoute213_TalkCyrus:
    LockAll
    FacePlayer
    Message DWRoute213_Text_CyrusItsStillInThere
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
DWRoute213_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
DWRoute213_Movement_StepOutOfTrees:
    WalkNormalWest 3
    FaceWest
    EndMovement
