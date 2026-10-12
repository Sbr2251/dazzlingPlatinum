#include "macros/scrcmd.inc"
#include "res/text/bank/dw_route_213.h"
#include "constants/totem_battle.h"

// Arc 2 rift 2.21, inside: MAP_HEADER_DW_ROUTE_213, the Drowned Lake (owner rift-b; docs/arc2/rift_contract.md).
//   entry   the Route 213 cave rift sets VAR_ARC2_PROGRESS 83, then Warp MAP_HEADER_DW_ROUTE_213, 0, 20, 12, DIR_WEST
//   exit    Warp MAP_HEADER_ROUTE_213, 0, 715, 831, DIR_SOUTH, after the calm (VAR_ARC2_PROGRESS 84)
//
// Floor: the DW B4F clone (tools/distortion_world/route_213.json), dressed by set-lake (build_dw_route_213.py).
// The swallowed Lake Valor: its old bed is the floor, with what it swallowed still lying there: a rowboat beside
// the path down to the first hop (19-21, 16-19), the lakefront sign at the lip (24,22), on the ledge past the hop
// (31-32, 20-23) the rusted frame (31,20) and the worn Trainer Card (32,20), and the jetty from the pool to the
// east wall (38-47, 22-23). What is left of the water lies in the pool; the lake itself hangs overhead as the
// ceiling. The way on: hop the chasm and the pool, cross the jetty, climb the east wall (x=49) and walk the
// causeway on the ceiling (y=10) under the hanging water, to its one island (x 45-48, z 44-47), where the Lapras
// waits. Stepping onto z >= 45 there starts the fight (step hook Arc2DwRoute213_HandleStep runs entry 4).
//
// rift-b flags: see scripts_dw_route_214.s. Here: FLAG_UNK_0x092E = FLAG_ARC2_ELIAS_CARD (the card picked up).
// fix2-lost: FLAG_ARC2_RAID_B (0x0952, unused in s-raid's block; docs/arc2/registry.md) = Cyrus's lake line at the
// entry was played. Persistent, so walking back in through the cave rift after a blackout (the rift still warps in
// at 83) doesn't replay it; the map-local VAR_MAP_LOCAL_1 alone reset on every load. Lead: rename at merge
// (suggested FLAG_ARC2_DW_ROUTE_213_LAKE_LINE).
// Map-local: VAR_MAP_LOCAL_1 entry line played this load (not VAR_MAP_LOCAL_0: see scripts_dw_route_214.s).
// DW overlay objects (src/overlay009 sArc2DwRoute213Objects): 0x80 Cyrus at the entry, 0x81 the rusted frame,
// 0x82 the card, 0x83 the Lapras (on the island of the hanging lake), 0x84 the lakefront sign.
// set-lake dressing (docs/arc2/PLAN.md S6, D6): the debris on the old lakebed is examinable (entries 6-9); the
// rowboat, the jetty and the hanging lake are terrain (map_data_675/676, tools/distortion_world/build_dw_route_213.py).

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
    ScriptEntry DWRoute213_LakeSign
    ScriptEntry DWRoute213_RustedFrame
    ScriptEntry DWRoute213_Rowboat
    ScriptEntry DWRoute213_MooringPost
    ScriptEntryEnd

DWRoute213_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

// First frame of every load (init script, VAR_MAP_LOCAL_1 == 0): Cyrus's line, only on the entry tile, once per save
// (FLAG_ARC2_RAID_B); later entries only step out of the trees beside him.
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
    GoToIfSet FLAG_ARC2_RAID_B, DWRoute213_EntryEnd
    SetFlag FLAG_ARC2_RAID_B
    Message DWRoute213_Text_CyrusThereWasALake
    WaitABXPadPress
    CloseMessage
DWRoute213_EntryEnd:
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
    // polish-c (critic #10): the player keeps it, as the Worn Trainer Card key item (Key Items never fill up).
    // No Warp follows in this script, so the obtain jingle (PlaySound) is safe here.
    SetVar VAR_0x8004, ITEM_WORN_TRAINER_CARD
    SetVar VAR_0x8005, 1
    GiveItemQuantity
    WaitABXPadPress
    CloseMessage
    SetFlag FLAG_ARC2_ELIAS_CARD
    ScrCmd_312 LOCALID_CARD
    ReleaseAll
    End

// Step hook: the island at the far end of the ceiling causeway. The Lapras rears up to meet the player, and the
// battle starts.
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
    // The battle reload put it back on the island: the aura drains and it slips into the hanging lake
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

// set-lake: what the lake swallowed. Examine text for each piece of debris on the old lakebed (the floor).
// 6: the lakefront sign (DW object 0x84), 7: the rusted frame (0x81), 8: the rowboat (terrain in map_data_675, a bg
// event on the tiles beside the path), 9: the jetty's mooring posts (terrain in map_data_676, bg events on the tiles
// beyond the deck's edges; tools/distortion_world/build_dw_route_213.py).
DWRoute213_LakeSign:
    LockAll
    Message DWRoute213_Text_LakeSign
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

DWRoute213_RustedFrame:
    LockAll
    Message DWRoute213_Text_RustedFrame
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

DWRoute213_Rowboat:
    LockAll
    Message DWRoute213_Text_Rowboat
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

DWRoute213_MooringPost:
    LockAll
    Message DWRoute213_Text_MooringPost
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
