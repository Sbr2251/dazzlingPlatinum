#include "macros/scrcmd.inc"
#include "res/text/bank/route_209_lost_tower_1f.h"
#include "res/field/maps/locals/route_209_lost_tower_1f.h"
// Generated events headers share one include guard, so 5F's can't be included beside 1F's: Saros is 5F's
// object 2 (ROUTE_209_LOST_TOWER_5F_SAROS in events_route_209_lost_tower_5f.json).
#define LOSTTOWER5F_SAROS 2

// Dazzling Platinum Arc 2, s-hearthome (screenplay 2.24-2.26, overworld). Flags owned by s-hearthome:
//   FLAG_ARC2_HEARTHOME_A = FLAG_ARC2_HEARTHOME_A  2.24 Saros cutaway (Lost Tower 5F) seen
//   FLAG_ARC2_HEARTHOME_B = FLAG_ARC2_HEARTHOME_B  hide the Lost Tower 2F rift (set = hidden; shown at progress 92-94)
//   FLAG_ARC2_HEARTHOME_C = FLAG_ARC2_HEARTHOME_C  hide the 2F Eclipse grunts and crates (shown at progress 93)
//   FLAG_ARC2_HEARTHOME_D = FLAG_ARC2_HEARTHOME_D  hide Rowan on 2F (shown at progress 94)
//   FLAG_ARC2_HEARTHOME_E = FLAG_ARC2_HEARTHOME_E  Saros cutaway staging in progress (read by 5F's OnTransition)
//   FLAG_ARC2_HEARTHOME_F/0x095F (F, G)           spare
// Map-local here: FLAG_MAP_LOCAL_HIDE_OBSTACLE_16 hides vigil Fantina (Fen Badge); VAR_MAP_LOCAL_0x01 = 1 opens the stairs;
// VAR_MAP_LOCAL_0x02 = 1 runs the Saros cutaway (OnFrame). Lost Tower 2F has no init script (its header uses
// scripts_init_empty), so this OnTransition sets 2F's hide flags: 1F is the only way into 2F.
// VAR_ARC2_PROGRESS (block 90-99): 91 Relic Badge at 89+, 92 Garius battle 2, 93 vein call, 94 grunts beaten,
// 95 Spiritomb calm (rift-b), 99 END OF ARC 2.

    ScriptEntry LostTower1F_OnTransition
    ScriptEntry Route209LostTower1F_PokemonBreederF1
    ScriptEntry Route209LostTower1F_PokemonBreederF2
    ScriptEntry LostTower1F_Fantina
    ScriptEntry LostTower1F_FantinaBlocksStairs
    ScriptEntry LostTower1F_SarosCutaway
    ScriptEntryEnd

LostTower1F_OnTransition:
    SetFlag FLAG_FIRST_ARRIVAL_LOST_TOWER
    CheckBadgeAcquired BADGE_ID_FEN, VAR_MAP_LOCAL_0x00
    CallIfEq VAR_MAP_LOCAL_0x00, TRUE, LostTower1F_VigilOver
    Call LostTower1F_Set2FFlags
    SetVar VAR_MAP_LOCAL_0x02, 0
    GoToIfNe VAR_ARC2_PROGRESS, 92, LostTower1F_OnTransitionEnd
    GoToIfSet FLAG_ARC2_HEARTHOME_A, LostTower1F_OnTransitionEnd
    SetVar VAR_MAP_LOCAL_0x02, 1
LostTower1F_OnTransitionEnd:
    End

LostTower1F_VigilOver:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetVar VAR_MAP_LOCAL_0x01, 1
    Return

LostTower1F_Set2FFlags:
    SetFlag FLAG_ARC2_HEARTHOME_B
    SetFlag FLAG_ARC2_HEARTHOME_C
    SetFlag FLAG_ARC2_HEARTHOME_D
    GoToIfLt VAR_ARC2_PROGRESS, 92, LostTower1F_Set2FFlagsEnd
    GoToIfGe VAR_ARC2_PROGRESS, 95, LostTower1F_Set2FFlagsEnd
    ClearFlag FLAG_ARC2_HEARTHOME_B
    CallIfEq VAR_ARC2_PROGRESS, 93, LostTower1F_ShowGrunts
    CallIfEq VAR_ARC2_PROGRESS, 94, LostTower1F_ShowRowan
LostTower1F_Set2FFlagsEnd:
    Return

LostTower1F_ShowGrunts:
    ClearFlag FLAG_ARC2_HEARTHOME_C
    Return

LostTower1F_ShowRowan:
    ClearFlag FLAG_ARC2_HEARTHOME_D
    Return

Route209LostTower1F_PokemonBreederF1:
    NPCMessage Route209LostTower1F_Text_ThisIsWhereSpiritsRest
    End

Route209LostTower1F_PokemonBreederF2:
    NPCMessage Route209LostTower1F_Text_ThisIsTheLostTower
    End

// 2.24 the vigil: Fantina sits by the stairs until the Fen Badge.
LostTower1F_Fantina:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message LostTower1F_Text_FantinaNotYet
    WaitABPadPress
    Message LostTower1F_Text_FantinaTheyCry
    WaitABPadPress
    Message LostTower1F_Text_FantinaSadMan
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

// The west side of the stairs (3,3) is open too: stepping there before the Fen Badge turns the player back.
LostTower1F_FantinaBlocksStairs:
    LockAll
    ApplyMovement LOCALID_FANTINA, LostTower1F_Movement_FaceWest
    WaitMovement
    Message LostTower1F_Text_FantinaNotYet
    WaitABPadPress
    CloseMessage
    GetPlayerDir VAR_0x8004
    CallIfEq VAR_0x8004, DIR_EAST, LostTower1F_StepBackWest
    CallIfNe VAR_0x8004, DIR_EAST, LostTower1F_StepBackSouth
    ApplyMovement LOCALID_FANTINA, LostTower1F_Movement_FaceSouth
    WaitMovement
    ReleaseAll
    End

LostTower1F_StepBackWest:
    ApplyMovement LOCALID_PLAYER, LostTower1F_Movement_StepWest
    WaitMovement
    Return

LostTower1F_StepBackSouth:
    ApplyMovement LOCALID_PLAYER, LostTower1F_Movement_StepSouth
    WaitMovement
    Return

// 2.24 cutaway: Saros at Mira's grave on 5F, shown to the player only. The player is parked out of sight on 5F
// (invisible) and brought back to the 1F door. Messages come from this script's bank (1F), so 5F's lines live here.
LostTower1F_SarosCutaway:
    LockAll
    SetVar VAR_MAP_LOCAL_0x02, 0
    SetFlag FLAG_ARC2_HEARTHOME_A
    SetFlag FLAG_ARC2_HEARTHOME_E
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_ROUTE_209_LOST_TOWER_5F, 7, 13, DIR_NORTH
    ApplyMovement LOCALID_PLAYER, LostTower1F_Movement_Invisible
    WaitMovement
    FadeScreenIn
    WaitFadeScreen
    WaitTime 30, VAR_RESULT
    Message LostTower1F_Text_SarosBirthday
    WaitABPadPress
    CloseMessage
    WaitTime 30, VAR_RESULT
    Message LostTower1F_Text_SarosOneMorning
    WaitABPadPress
    CloseMessage
    ApplyMovement LOSTTOWER5F_SAROS, LostTower1F_Movement_SarosStands
    WaitMovement
    ApplyMovement LOSTTOWER5F_SAROS, LostTower1F_Movement_SarosLeaves
    WaitMovement
    RemoveObject LOSTTOWER5F_SAROS
    WaitTime 20, VAR_RESULT
    FadeScreenOut
    WaitFadeScreen
    ClearFlag FLAG_ARC2_HEARTHOME_E
    Warp MAP_HEADER_ROUTE_209_LOST_TOWER_1F, 7, 13, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
LostTower1F_Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
LostTower1F_Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
LostTower1F_Movement_StepSouth:
    WalkNormalSouth
    EndMovement

    .balign 4, 0
LostTower1F_Movement_StepWest:
    WalkNormalWest
    EndMovement

    .balign 4, 0
LostTower1F_Movement_Invisible:
    SetInvisible
    EndMovement

    .balign 4, 0
LostTower1F_Movement_SarosStands:
    Delay16
    FaceNorth
    Delay16 2
    FaceEast
    Delay16 2
    EndMovement

    .balign 4, 0
LostTower1F_Movement_SarosLeaves:
    WalkNormalEast
    WalkNormalNorth 4
    WalkNormalWest
    WalkNormalNorth 2
    WalkNormalEast 3
    WalkNormalNorth 2
    EndMovement

    .balign 4, 0
