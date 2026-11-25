#include "macros/scrcmd.inc"
#include "res/text/bank/solaceon_town.h"
#include "res/field/maps/locals/solaceon_town.h"


    ScriptEntry SolaceonTown_Rancher
    ScriptEntry SolaceonTown_KennelKeeper
    ScriptEntry SolaceonTown_DaycareKid
    ScriptEntry SolaceonTown_SundayMan
    ScriptEntry SolaceonTown_LanternMan
    ScriptEntry SolaceonTown_PoketchMan
    ScriptEntry SolaceonTown_MapSignpost
    ScriptEntry SolaceonTown_SignboardPokemonDayCare
    ScriptEntry SolaceonTown_SignboardPokemonNewsPress
    ScriptEntry SolaceonTown_OnTransition
    ScriptEntry SolaceonTown_OnResume
    ScriptEntry SolaceonTown_CoordEvent_Rival
    ScriptEntry SolaceonTown_Arc2WallPhotos
    ScriptEntry SolaceonTown_Arc2WallPonyta
    ScriptEntry SolaceonTown_Arc2WallElias
    ScriptEntry SolaceonTown_Arc2WallBanner
    ScriptEntry SolaceonTown_Arc2WallTeo
    ScriptEntry SolaceonTown_Arc2IndraCutaway
    ScriptEntry SolaceonTown_QuestsRowanBanner
    ScriptEntry SolaceonTown_CineCityEntry
    ScriptEntry SolaceonTown_Seizure
    ScriptEntry SolaceonTown_TentClerk
    ScriptEntry SolaceonTown_PilgrimFather
    ScriptEntry SolaceonTown_PilgrimSailor
    ScriptEntry SolaceonTown_PilgrimSister
    ScriptEntry SolaceonTown_PilgrimSon
    ScriptEntry SolaceonTown_RoadGreeter
    ScriptEntry SolaceonTown_WallWidow
    ScriptEntry SolaceonTown_GardenGirl
    ScriptEntry SolaceonTown_BelieverMother
    ScriptEntry SolaceonTown_Looker
    ScriptEntry SolaceonTown_Cyrus
    ScriptEntry SolaceonTown_GateGreeter
    ScriptEntry SolaceonTown_GateGruntL
    ScriptEntry SolaceonTown_GateGruntR
    ScriptEntry SolaceonTown_ForecourtSweeper
    ScriptEntry SolaceonTown_IpOfficerGate
    ScriptEntry SolaceonTown_IpOfficerCourt
    ScriptEntry SolaceonTown_DigWorker
    ScriptEntry SolaceonTown_ExcavationGruntM
    ScriptEntry SolaceonTown_ExcavationGruntF
    ScriptEntry SolaceonTown_RuinManiac
    ScriptEntry SolaceonTown_IpOfficerDig
    ScriptEntry SolaceonTown_KennelMon1
    ScriptEntry SolaceonTown_KennelMon2
    ScriptEntry SolaceonTown_KennelMon3
    ScriptEntry SolaceonTown_KennelMon4
    ScriptEntry SolaceonTown_LoadingGrunt
    ScriptEntry SolaceonTown_Doubter
    ScriptEntry SolaceonTown_IndraWall
    ScriptEntry SolaceonTown_GatePlaque
    ScriptEntry SolaceonTown_TentSign
    ScriptEntry SolaceonTown_DigSign
    ScriptEntry SolaceonTown_KennelSign
    ScriptEntry SolaceonTown_MemorialPlaque
    ScriptEntry SolaceonTown_BannerPost
    ScriptEntry SolaceonTown_HallDoor
    ScriptEntry SolaceonTown_FenceTrigger
    ScriptEntryEnd

// Arc 2 (s-celestic), 2.16a: the memorial wall (sign events on the wall x 556, z 652-656, read from x 557 facing
// west) and the Indra cutaway. The cutaway plays the first time the player comes down the road from Route 210 at
// state 44 (coord row at the town's north edge): 47 at the start, 49 at the end. Map-local hide flag:
// FLAG_MAP_LOCAL_HIDE_OBSTACLE_16 = Indra (also Indra at the wall in the postgame, band F).
// The stock Barry run-in at the south exit (VAR_SOLACEON_TOWN_STATE) is switched off from Arc 2 on.
// Arc 2 quests (R3, S10): from VAR_ARC2_PROGRESS 47 two Eclipse banners quote Rowan, at the north road (557,642)
// and the south road (557,666). Map-local hide flag: FLAG_MAP_LOCAL_HIDE_OBSTACLE_17 = both banners.
//
// Solaceon redesign (town-scripts; docs/solaceon_redesign/scripts.md, screenplay.md Parts 1, 2 and 4). The town has
// one state band per map load, picked by SolaceonTown_GetBand into VAR_MAP_LOCAL_0x04 (a map-local var:
// init scripts have no script manager, so the special vars 0x8000+ cannot be used there):
//   A  VAR_ARC2_PROGRESS < 54 (pilgrim season)        B  54-85 (security)        C  86-98 (the town splits)
//   D  99 and VAR_SOLACEON_PROGRESS < 20 (the Return; Looker and Cyrus at the wall from 10)
//   R  VAR_SOLACEON_PROGRESS 20-49 (the raid)         E  50 (seized)             F  FLAG_GAME_COMPLETED (garden)
// OnTransition hides every band object (map-local flags; HideAll) and shows the band's set (ShowA..ShowF), moving
// the objects that stand somewhere else in a band. Map-local hide flags (cleared on every map load):
//   HIDE_OBSTACLE_1 tent clerk   2 pilgrim father   3 sailor   4 sister   5 son   6 road greeter   7 garden girl
//   8 Looker   9 Cyrus   10 gate greeter   11/12 gate grunts L/R   13 forecourt sweeper   14/15 IP officers gate/court
//   16 Indra   17 Rowan banners   18 dig worker   19/20 excavation grunts M/F   21 ruin maniac   22 IP officer dig
//   23/24 kennel Pokemon 1/2   25 kennel Pokemon 3+4   26 loading grunt   27 doubter   28/29 crates 1/2
//   30 crates 3+4   FLAG_MAP_LOCAL_0x10 crates 5+6
// Map-local vars: VAR_MAP_LOCAL_0x04 = the band; VAR_MAP_LOCAL_0x02 = 1 plays the seizure (scene 3.4a part 7) from the frame table, once
// (FLAG_SOL_TOWN_A); VAR_MAP_LOCAL_0x03 = 1 arms the fence coord trigger (scene 3.4a part 2).
// Persistent: FLAG_SOL_TOWN_A seizure seen, FLAG_SOL_TOWN_B postgame Indra at the wall done.
#define BAND_A 1
#define BAND_B 2
#define BAND_C 3
#define BAND_D 4
#define BAND_R 5
#define BAND_E 6
#define BAND_F 7

SolaceonTown_OnResume:
    End

SolaceonTown_OnTransition:
    SetVar VAR_CINE_CITY_PENDING, 1
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    Call SolaceonTown_QuestsOnTransition
    CallIfGe VAR_ARC2_PROGRESS, 1, SolaceonTown_Arc2NoBarry
    Call SolaceonTown_SolOnTransition
    CheckDaycareHasEgg VAR_MAP_LOCAL_0x00
    GoToIfNe VAR_MAP_LOCAL_0x00, FALSE, SolaceonTown_SetDayCareManDirEast
    End

SolaceonTown_SetDayCareManDirEast:
    SetObjectEventDir LOCALID_DAY_CARE_MAN, DIR_EAST
    End

SolaceonTown_Arc2NoBarry:
    SetVar VAR_SOLACEON_TOWN_STATE, 1
    Return

// ---------------------------------------------------------------------------------------------- the state band
SolaceonTown_GetBand:
    SetVar VAR_MAP_LOCAL_0x04, BAND_F
    GoToIfSet FLAG_GAME_COMPLETED, SolaceonTown_GetBandDone
    SetVar VAR_MAP_LOCAL_0x04, BAND_E
    GoToIfGe VAR_SOLACEON_PROGRESS, 50, SolaceonTown_GetBandDone
    SetVar VAR_MAP_LOCAL_0x04, BAND_R
    GoToIfGe VAR_SOLACEON_PROGRESS, 20, SolaceonTown_GetBandDone
    SetVar VAR_MAP_LOCAL_0x04, BAND_D
    GoToIfGe VAR_ARC2_PROGRESS, 99, SolaceonTown_GetBandDone
    SetVar VAR_MAP_LOCAL_0x04, BAND_C
    GoToIfGe VAR_ARC2_PROGRESS, 86, SolaceonTown_GetBandDone
    SetVar VAR_MAP_LOCAL_0x04, BAND_B
    GoToIfGe VAR_ARC2_PROGRESS, 54, SolaceonTown_GetBandDone
    SetVar VAR_MAP_LOCAL_0x04, BAND_A
SolaceonTown_GetBandDone:
    Return

SolaceonTown_SolOnTransition:
    Call SolaceonTown_HideAll
    Call SolaceonTown_GetBand
    CallIfEq VAR_MAP_LOCAL_0x04, BAND_A, SolaceonTown_ShowA
    CallIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonTown_ShowB
    CallIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_ShowC
    CallIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_ShowD
    CallIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_ShowR
    CallIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_ShowE
    CallIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_ShowF
    Return

SolaceonTown_HideAll:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_1
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_2
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_3
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_4
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_5
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_6
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_7
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_8
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_9
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_10
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_11
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_12
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_13
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_14
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_15
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_20
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_21
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_22
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_23
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_24
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_25
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_26
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_27
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_28
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_29
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_30
    SetFlag FLAG_MAP_LOCAL_0x10
    Return

// A: pilgrim season. The tent queue, the greeters, the dig worker and the ruin maniac, the full kennel; the loading
// yard is empty (A is the busiest band: it stays under the field's 29 dynamic sprite slots, see scripts.md).
SolaceonTown_ShowA:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_1
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_2
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_3
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_4
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_5
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_6
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_7
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_10
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_13
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_21
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_23
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_24
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_25
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_27
    Return

// B: security. Gate and fence grunts, the loading grunt, kennel down to 2, 4 crates; the father stays at the wall.
SolaceonTown_ShowB:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_1
    Call SolaceonTown_FatherAtWall
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_11
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_12
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_13
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_20
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_23
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_24
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_26
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_27
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_28
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_29
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_30
    Return

// C: the town splits. The sister leaves by the north road, the girl is back, one kennel Pokemon, the truck is out.
SolaceonTown_ShowC:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_1
    Call SolaceonTown_FatherAtWall
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_4
    SetObjectEventPos LOCALID_PILGRIM_SISTER, 561, 641
    SetObjectEventDir LOCALID_PILGRIM_SISTER, DIR_NORTH
    SetObjectEventMovementType LOCALID_PILGRIM_SISTER, MOVEMENT_TYPE_LOOK_NORTH
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_7
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_11
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_12
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_13
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_20
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_23
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_27
    Return

// D: the Return. The gate is shut (the left grunt steps onto the gate's front tile), the hall door's warp is parked
// inside the hall (the door gives the locked message instead), the loading grunt at a full truck, the kennel empty.
// From VAR_SOLACEON_PROGRESS 10, Looker and Cyrus wait at the south end of the wall (scene 3.4a part 1).
SolaceonTown_ShowD:
    Call SolaceonTown_ShowDR
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_11
    SetObjectEventPos LOCALID_GATE_GRUNT_L, 580, 659
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_12
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_26
    SetWarpEventPos WARP_SOLACEON_TOWN_POKEMON_NEWS_PRESS, 580, 650
    GoToIfLt VAR_SOLACEON_PROGRESS, 10, SolaceonTown_ShowDDone
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_8
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_9
SolaceonTown_ShowDDone:
    Return

// D and R share the townspeople: the clerk at the closed tent, the son beside it, the father at the wall, the fence
// pair and all 6 crates.
SolaceonTown_ShowDR:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_1
    Call SolaceonTown_FatherAtWall
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_5
    SetObjectEventPos LOCALID_PILGRIM_SON, 567, 645
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_19
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_20
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_28
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_29
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_30
    ClearFlag FLAG_MAP_LOCAL_0x10
    Return

// R: the raid. The gate guards are at lunch and the loading grunt is gone. Until the fence pair is beaten, Cyrus
// waits by the fence and the coord trigger in front of the dig is armed; after, the pair stand aside.
// Losing the second fence battle resets the pair (screenplay: "the pair reset").
SolaceonTown_ShowR:
    Call SolaceonTown_ShowDR
    GoToIfDefeated TRAINER_ECLIPSE_GRUNT_SOL_08, SolaceonTown_ShowRFenceDone
    GoToIfNotDefeated TRAINER_ECLIPSE_GRUNT_SOL_07, SolaceonTown_ShowRFenceArmed
    ClearTrainerFlag TRAINER_ECLIPSE_GRUNT_SOL_07
SolaceonTown_ShowRFenceArmed:
    SetObjectEventPos LOCALID_CYRUS, 597, 662
    SetObjectEventDir LOCALID_CYRUS, DIR_WEST
    SetObjectEventMovementType LOCALID_CYRUS, MOVEMENT_TYPE_LOOK_WEST
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_9
    SetVar VAR_MAP_LOCAL_0x03, 1
    Return

SolaceonTown_ShowRFenceDone:
    SetObjectEventPos LOCALID_EXCAVATION_GRUNT_M, 596, 661
    SetObjectEventDir LOCALID_EXCAVATION_GRUNT_M, DIR_WEST
    SetObjectEventMovementType LOCALID_EXCAVATION_GRUNT_M, MOVEMENT_TYPE_LOOK_WEST
    SetObjectEventPos LOCALID_EXCAVATION_GRUNT_F, 597, 660
    Return

// E: seized. International Police at the gate, in the forecourt and at the fence; the Skitty is back in the kennel;
// the ruin maniac, the girl and the doubter are back. The first load at 50 plays the seizure (3.4a part 7).
SolaceonTown_ShowE:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_1
    Call SolaceonTown_FatherAtWall
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_7
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_14
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_15
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_21
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_22
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_23
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_27
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_28
    GoToIfSet FLAG_SOL_TOWN_A, SolaceonTown_ShowEDone
    SetVar VAR_MAP_LOCAL_0x02, 1
SolaceonTown_ShowEDone:
    Return

// F: the memorial garden. The clerk is the garden keeper and the pilgrims are in the garden of names; the Rowan
// banners are gone; four new rescues in the kennel. Indra at the wall, once (FLAG_SOL_TOWN_B).
SolaceonTown_ShowF:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_1
    SetObjectEventPos LOCALID_TENT_CLERK, 567, 651
    SetObjectEventDir LOCALID_TENT_CLERK, DIR_WEST
    SetObjectEventMovementType LOCALID_TENT_CLERK, MOVEMENT_TYPE_LOOK_WEST
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_2
    SetObjectEventPos LOCALID_PILGRIM_FATHER, 565, 650
    SetObjectEventDir LOCALID_PILGRIM_FATHER, DIR_SOUTH
    SetObjectEventMovementType LOCALID_PILGRIM_FATHER, MOVEMENT_TYPE_LOOK_SOUTH
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_3
    SetObjectEventPos LOCALID_PILGRIM_SAILOR, 567, 650
    SetObjectEventDir LOCALID_PILGRIM_SAILOR, DIR_SOUTH
    SetObjectEventMovementType LOCALID_PILGRIM_SAILOR, MOVEMENT_TYPE_LOOK_SOUTH
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_4
    SetObjectEventPos LOCALID_PILGRIM_SISTER, 565, 652
    SetObjectEventDir LOCALID_PILGRIM_SISTER, DIR_WEST
    SetObjectEventMovementType LOCALID_PILGRIM_SISTER, MOVEMENT_TYPE_LOOK_WEST
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_7
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_21
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_23
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_24
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_25
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_27
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    GoToIfSet FLAG_SOL_TOWN_B, SolaceonTown_ShowFDone
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
SolaceonTown_ShowFDone:
    Return

SolaceonTown_FatherAtWall:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_2
    SetObjectEventPos LOCALID_PILGRIM_FATHER, 558, 653
    SetObjectEventDir LOCALID_PILGRIM_FATHER, DIR_WEST
    SetObjectEventMovementType LOCALID_PILGRIM_FATHER, MOVEMENT_TYPE_LOOK_WEST
    Return

// ----------------------------------------------------------------------------------------- shared talk/sign ends
SolaceonTown_TalkStart:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Call SolaceonTown_GetBand
    Return

SolaceonTown_TalkEnd:
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonTown_SignStart:
    LockAll
    Call SolaceonTown_GetBand
    Return

SolaceonTown_SignEnd:
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonTown_SignNothing:
    ReleaseAll
    End

// ------------------------------------------------------------------------------------------------- 2.16a: the wall
SolaceonTown_Arc2WallPhotos:
    GoToIfLt VAR_ARC2_PROGRESS, 44, SolaceonTown_Arc2WallEnd
    LockAll
    Message SolaceonTown_Text_Arc2WallPhotos
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_Arc2WallPonyta:
    GoToIfLt VAR_ARC2_PROGRESS, 44, SolaceonTown_Arc2WallEnd
    LockAll
    Message SolaceonTown_Text_Arc2WallPonyta
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_Arc2WallElias:
    GoToIfLt VAR_ARC2_PROGRESS, 44, SolaceonTown_Arc2WallEnd
    LockAll
    Message SolaceonTown_Text_Arc2WallElias
    GoTo SolaceonTown_Arc2WallClose
    End

// The banner comes down after the raid (E: folded by the wall; F: flowers where it hung).
SolaceonTown_Arc2WallBanner:
    GoToIfLt VAR_ARC2_PROGRESS, 44, SolaceonTown_Arc2WallEnd
    LockAll
    Call SolaceonTown_GetBand
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_WallBannerE
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_WallBannerF
    Message SolaceonTown_Text_Arc2WallBanner
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_WallBannerE:
    Message SolaceonTown_Text_SolWallBannerE
    GoTo SolaceonTown_Arc2WallClose

SolaceonTown_WallBannerF:
    Message SolaceonTown_Text_SolWallBannerF
    GoTo SolaceonTown_Arc2WallClose

// TEO; after the postgame Indra scene, her card is pinned beside it.
SolaceonTown_Arc2WallTeo:
    GoToIfLt VAR_ARC2_PROGRESS, 49, SolaceonTown_Arc2WallEnd
    LockAll
    GoToIfSet FLAG_SOL_TOWN_B, SolaceonTown_WallTeoIndra
    Message SolaceonTown_Text_Arc2WallTeo
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_WallTeoIndra:
    Message SolaceonTown_Text_SolWallTeoIndra
    GoTo SolaceonTown_Arc2WallClose

SolaceonTown_Arc2WallClose:
    WaitABPadPress
    CloseMessage
    ReleaseAll
SolaceonTown_Arc2WallEnd:
    End

// 2.16a: shown to the player only. The player is put at the wall and hidden; Indra pins up Teo's card.
// Every teleport of the player in this file goes AddFreeCamera (at the target) / SetPosition / RestoreCamera:
// RestoreCamera re-tracks the player in the map loader, which otherwise asserts on a jump in x and z at once
// (land_data.c, LandDataManager_Tick).
SolaceonTown_Arc2IndraCutaway:
    LockAll
    SetVar VAR_ARC2_PROGRESS, 47
    FadeScreenOut
    WaitFadeScreen
    AddFreeCamera 558, 654
    SetPosition LOCALID_PLAYER, 558, 0, 654, DIR_WEST
    RestoreCamera
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Arc2Movement_Hide
    WaitMovement
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    AddObject LOCALID_ARC2_INDRA
    LockObject LOCALID_ARC2_INDRA
    WaitTime 15, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_ARC2_INDRA, SolaceonTown_Arc2Movement_PinCard
    WaitMovement
    PlaySE SEQ_SE_DP_KON_sseq
    WaitTime 20, VAR_RESULT
    Message SolaceonTown_Text_Arc2IndraAnotherName
    Message SolaceonTown_Text_Arc2IndraSomebodyHasTo
    Message SolaceonTown_Text_Arc2IndraMorningDoor
    Message SolaceonTown_Text_Arc2IndraHandsShake
    Message SolaceonTown_Text_Arc2IndraKeepTheDoor
    CloseMessage
    ApplyMovement LOCALID_ARC2_INDRA, SolaceonTown_Arc2Movement_IndraLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_INDRA
    WaitTime 20, VAR_RESULT
    FadeScreenOut
    WaitFadeScreen
    AddFreeCamera 557, 654
    SetPosition LOCALID_PLAYER, 557, 0, 654, DIR_WEST
    RestoreCamera
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Arc2Movement_Show
    WaitMovement
    FadeScreenIn
    WaitFadeScreen
    SetVar VAR_ARC2_PROGRESS, 49
    Message SolaceonTown_Text_Arc2WallTeo
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
SolaceonTown_Arc2Movement_Hide:
    SetInvisible
    EndMovement

    .balign 4, 0
SolaceonTown_Arc2Movement_Show:
    SetVisible
    FaceWest
    EndMovement

    .balign 4, 0
SolaceonTown_Arc2Movement_PinCard:
    FaceWest
    Delay8
    WalkOnSpotSlowWest
    EndMovement

    .balign 4, 0
SolaceonTown_Arc2Movement_IndraLeave:
    Delay8 2
    WalkNormalSouth 2
    WalkNormalEast 3
    WalkNormalSouth 4
    EndMovement

// Band F, once: Indra at the wall, coat off. She pins a card beside TEO's and leaves by the south road.
SolaceonTown_IndraWall:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message SolaceonTown_Text_SolIndraF_1
    WaitABPadPress
    Message SolaceonTown_Text_SolIndraF_2
    WaitABPadPress
    Message SolaceonTown_Text_SolIndraF_3
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_ARC2_INDRA, SolaceonTown_Arc2Movement_PinCard
    WaitMovement
    PlaySE SEQ_SE_DP_KON_sseq
    WaitTime 20, VAR_RESULT
    SetFlag FLAG_SOL_TOWN_B
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 655, SolaceonTown_IndraWallLeaveAround
    ApplyMovement LOCALID_ARC2_INDRA, SolaceonTown_Arc2Movement_IndraLeave
    WaitMovement
    GoTo SolaceonTown_IndraWallGone

SolaceonTown_IndraWallLeaveAround:
    ApplyMovement LOCALID_ARC2_INDRA, SolaceonTown_Movement_IndraLeaveAround
    WaitMovement
SolaceonTown_IndraWallGone:
    RemoveObject LOCALID_ARC2_INDRA
    ReleaseAll
    End

    .balign 4, 0
SolaceonTown_Movement_IndraLeaveAround:
    Delay8 2
    WalkNormalEast
    WalkNormalSouth 2
    WalkNormalEast 2
    WalkNormalSouth 4
    EndMovement

// ------------------------------------------------------------------------------------------- stock, kept as stock
SolaceonTown_DaycareKid:
    NPCMessage SolaceonTown_Text_ImTooLittle
    End

// The stock Pokemon History app giver (was the wandering Ruin Maniac; now POKETCH_MAN, east of the Northeast House).
SolaceonTown_PoketchMan:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    CheckPoketchAppRegistered POKETCH_APPID_POKEMONHISTORY, VAR_RESULT
    GoToIfEq VAR_RESULT, TRUE, SolaceonTown_EachPokemonOwnHistory
    GetLocalDexSeenCount VAR_RESULT
    GoToIfLt VAR_RESULT, 50, SolaceonTown_IfCompetentMetFiftyPokemon
    Message SolaceonTown_Text_PoketchAppPokemonHistory
    SetVar VAR_0x8004, POKETCH_APPID_POKEMONHISTORY
    CallCommonScript CommonScript_ObtainPoketchApp
    WaitButton
    CloseMessage
    ReleaseAll
    End

SolaceonTown_IfCompetentMetFiftyPokemon:
    Message SolaceonTown_Text_IfCompetentMetFiftyPokemon
    WaitButton
    CloseMessage
    ReleaseAll
    End

SolaceonTown_EachPokemonOwnHistory:
    Message SolaceonTown_Text_EachPokemonOwnHistory
    WaitButton
    CloseMessage
    ReleaseAll
    End

SolaceonTown_MapSignpost:
    ShowMapSign SolaceonTown_Text_MapSign
    End

SolaceonTown_SignboardPokemonDayCare:
    ShowLandmarkSign SolaceonTown_Text_SignPokemonDayCare
    End

// No object uses this any more (the News Press is gone; its door is the Sanctuary's). Kept so the script ids stay.
SolaceonTown_SignboardPokemonNewsPress:
    ShowLandmarkSign SolaceonTown_Text_SignPokemonNewsPress
    End

SolaceonTown_CoordEvent_Rival:
    LockAll
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Movement_PlayerNoticeRival
    WaitMovement
    CallCommonScript CommonScript_SetRivalBGM
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    SetObjectEventPos LOCALID_RIVAL, VAR_0x8004, 661
    ClearFlag FLAG_HIDE_SOLACEON_TOWN_RIVAL
    AddObject LOCALID_RIVAL
    LockObject LOCALID_RIVAL
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Movement_PlayerFaceNorth
    ApplyMovement LOCALID_RIVAL, SolaceonTown_Movement_RivalWalkSouth
    WaitMovement
    Message SolaceonTown_Text_Yahoo
    CloseMessage
    ApplyMovement LOCALID_RIVAL, SolaceonTown_Movement_RivalLookAround
    WaitMovement
    BufferRivalName 0
    BufferPlayerName 1
    Message SolaceonTown_Text_IGotSomethingCool
    ApplyMovement LOCALID_RIVAL, SolaceonTown_Movement_RivalExclamationMark
    WaitMovement
    Message SolaceonTown_Text_CheckOutTheRuins
    CloseMessage
    ApplyMovement LOCALID_RIVAL, SolaceonTown_Movement_RivalLeave
    WaitMovement
    RemoveObject LOCALID_RIVAL
    CallCommonScript CommonScript_FadeToDefaultMusic_2
    SetVar VAR_SOLACEON_TOWN_STATE, 1
    ReleaseAll
    End

    .balign 4, 0
SolaceonTown_Movement_RivalWalkSouth:
    WalkFastSouth 7
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_RivalLookAround:
    WalkOnSpotFastWest
    Delay8
    WalkOnSpotFastEast
    Delay8
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_RivalExclamationMark:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_RivalLeave:
    WalkFastNorth 7
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_PlayerNoticeRival:
    Delay8
    EmoteExclamationMark
    Delay8 3
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_PlayerFaceNorth:
    FaceNorth
    EndMovement

// -------------------------------------------------------------------------------- Arc 2 quests: the Rowan banners
SolaceonTown_QuestsOnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    GoToIfLt VAR_ARC2_PROGRESS, 47, SolaceonTown_QuestsReturn
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
SolaceonTown_QuestsReturn:
    Return

// The two Rowan banner signboards and the four banner posts on the pilgrim road: the Rowan quote from 47 (A, B),
// torn down to one word from 86 (C, D, R, E), gone in the garden (F).
SolaceonTown_QuestsRowanBanner:
    PlaySE SE_CONFIRM_sseq_3
SolaceonTown_BannerPost:
    Call SolaceonTown_SignStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_SignNothing
    GoToIfGe VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_BannerTorn
    GoToIfLt VAR_ARC2_PROGRESS, 47, SolaceonTown_SignNothing
    Message SolaceonTown_Text_QuestsRowanBanner
    GoTo SolaceonTown_SignEnd

SolaceonTown_BannerTorn:
    Message SolaceonTown_Text_SolTornBanner
    GoTo SolaceonTown_SignEnd

// City-entry cinematic (lane cine): on the first entry per save, a short
// pull-back and slow return while player input waits (LockAll). No-ops
// when OverworldCinematics is off.
SolaceonTown_CineCityEntry:
    SetVar VAR_CINE_CITY_PENDING, 0
    GoToIfSet FLAG_CINE_VISITED_SOLACEON, SolaceonTown_CineCityEntryDone
    SetFlag FLAG_CINE_VISITED_SOLACEON
    LockAll
    CineCamTo 0, 0, 700, 53, 0, 11, 80, 1
    CineWaitCamera
    CineCamReturn 70, 1
    CineWaitCamera
    ReleaseAll
SolaceonTown_CineCityEntryDone:
    End

// ------------------------------------------------------------------------------------------------------ signs
// Postgame memorial plaque (the plaque post at the head of the plaza; band F only).
SolaceonTown_MemorialPlaque:
    Call SolaceonTown_SignStart
    GoToIfNe VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_SignNothing
    Message SolaceonTown_Text_SolMemorialPlaque
    GoTo SolaceonTown_SignEnd

// The Sanctuary hall door (band D: its warp is parked, see ShowD).
SolaceonTown_HallDoor:
    Call SolaceonTown_SignStart
    GoToIfNe VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_SignNothing
    Message SolaceonTown_Text_SolHallDoorLocked
    GoTo SolaceonTown_SignEnd

// --------------------------------------------------------------------------------------- the kennel Pokemon (cry)
SolaceonTown_KennelMon1:
    LockAll
    FacePlayer
    PlayCry SPECIES_SKITTY
    WaitCry
    ReleaseAll
    End

SolaceonTown_KennelMon2:
    LockAll
    FacePlayer
    PlayCry SPECIES_PSYDUCK
    WaitCry
    ReleaseAll
    End

SolaceonTown_KennelMon3:
    LockAll
    FacePlayer
    PlayCry SPECIES_BUNEARY
    WaitCry
    ReleaseAll
    End

SolaceonTown_KennelMon4:
    LockAll
    FacePlayer
    PlayCry SPECIES_PACHIRISU
    WaitCry
    ReleaseAll
    End

// ------------------------------------------------------------------------------------------------ the gate pair
// Band D: the left grunt blocks the gate's front tile. A player who is inside the compound anyway (left the hall
// in band D) is let out: he steps aside after his line.
SolaceonTown_GateGruntL:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Call SolaceonTown_GetBand
    GoToIfNe VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_GateGruntLLines
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfGe VAR_0x8005, 659, SolaceonTown_GateGruntLLines
    Message SolaceonTown_Text_SolGateGruntLD
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_GATE_GRUNT_L, SolaceonTown_Movement_GateGruntAside
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
SolaceonTown_Movement_GateGruntAside:
    WalkNormalWest
    FaceEast
    EndMovement

// ------------------------------------------------------------------------- scene 3.4a part 1: Looker's briefing
SolaceonTown_Looker:
    GoTo SolaceonTown_Briefing
    End

// Cyrus: the briefing at the wall (D); by the fence before the pair is beaten (R).
SolaceonTown_Cyrus:
    Call SolaceonTown_GetBand
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_CyrusFence
    GoTo SolaceonTown_Briefing
    End

SolaceonTown_CyrusFence:
    Call SolaceonTown_TalkStart
    Message SolaceonTown_Text_SolBriefing_6
    GoTo SolaceonTown_TalkEnd

SolaceonTown_Briefing:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfLt VAR_0x8005, 657, SolaceonTown_BriefingFaceNorth
    CallIfGt VAR_0x8005, 657, SolaceonTown_BriefingFaceSouth
    CallIfEq VAR_0x8005, 657, SolaceonTown_BriefingFaceEast
    Message SolaceonTown_Text_SolBriefing_1
    WaitABPadPress
    Message SolaceonTown_Text_SolBriefing_2
    WaitABPadPress
    Message SolaceonTown_Text_SolBriefing_3
    WaitABPadPress
    Message SolaceonTown_Text_SolBriefing_4
    WaitABPadPress
    Message SolaceonTown_Text_SolBriefing_5
    WaitABPadPress
    Message SolaceonTown_Text_SolBriefing_6
    WaitABPadPress
    Message SolaceonTown_Text_SolBriefing_7
    WaitABPadPress
    Message SolaceonTown_Text_SolBriefing_8
    WaitABPadPress
    Message SolaceonTown_Text_SolBriefing_9
    WaitABPadPress
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    HealParty
    SetVar VAR_SOLACEON_PROGRESS, 20
    RemoveObject LOCALID_LOOKER
    RemoveObject LOCALID_CYRUS
    RemoveObject LOCALID_GATE_GRUNT_L
    RemoveObject LOCALID_GATE_GRUNT_R
    RemoveObject LOCALID_LOADING_GRUNT
    SetWarpEventPos WARP_SOLACEON_TOWN_POKEMON_NEWS_PRESS, 580, 652
    SetObjectEventPos LOCALID_CYRUS, 597, 662
    SetObjectEventDir LOCALID_CYRUS, DIR_WEST
    SetObjectEventMovementType LOCALID_CYRUS, MOVEMENT_TYPE_LOOK_WEST
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_9
    AddObject LOCALID_CYRUS
    SetVar VAR_MAP_LOCAL_0x03, 1
    WaitTime 15, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

SolaceonTown_BriefingFaceNorth:
    ApplyMovement LOCALID_LOOKER, SolaceonTown_Movement_FaceNorth
    ApplyMovement LOCALID_CYRUS, SolaceonTown_Movement_FaceNorth
    WaitMovement
    Return

SolaceonTown_BriefingFaceSouth:
    ApplyMovement LOCALID_LOOKER, SolaceonTown_Movement_FaceSouth
    ApplyMovement LOCALID_CYRUS, SolaceonTown_Movement_FaceSouth
    WaitMovement
    Return

SolaceonTown_BriefingFaceEast:
    ApplyMovement LOCALID_LOOKER, SolaceonTown_Movement_FaceEast
    ApplyMovement LOCALID_CYRUS, SolaceonTown_Movement_FaceEast
    WaitMovement
    Return

    .balign 4, 0
SolaceonTown_Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_FaceWest:
    FaceWest
    EndMovement

// ---------------------------------------------------------------- scene 3.4a part 2: the dig fence (SOL_07, SOL_08)
// The pair: M on the gap (595,659) facing south, F beside it (596,660) facing west. The trigger is the only way into
// the dig dirt (x 592, z 660-661, armed by ShowR / the briefing); talking to either runs the same scene. The player
// is brought to (594,660); Cyrus walks up beside (594,661). After both battles F steps east (597,660) and M steps
// down and aside (596,661), and Cyrus goes through the gap into the Room 1 entrance.
SolaceonTown_ExcavationGruntM:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Call SolaceonTown_GetBand
    GoToIfNe VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_ExcavationGruntMLines
    GoToIfNotDefeated TRAINER_ECLIPSE_GRUNT_SOL_08, SolaceonTown_FenceTalk
    Message SolaceonTown_Text_SolFenceGruntMPost
    GoTo SolaceonTown_TalkEnd

SolaceonTown_ExcavationGruntF:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Call SolaceonTown_GetBand
    GoToIfNe VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_ExcavationGruntFLines
    GoToIfNotDefeated TRAINER_ECLIPSE_GRUNT_SOL_08, SolaceonTown_FenceTalk
    Message SolaceonTown_Text_SolFenceGruntFPost
    GoTo SolaceonTown_TalkEnd

SolaceonTown_FenceTalk:
    SetVar VAR_MAP_LOCAL_0x03, 0
    FadeScreenOut
    WaitFadeScreen
    AddFreeCamera 594, 660
    SetPosition LOCALID_PLAYER, 594, 0, 660, DIR_EAST
    RestoreCamera
    FadeScreenIn
    WaitFadeScreen
    GoTo SolaceonTown_FenceScene
    End

SolaceonTown_FenceTrigger:
    LockAll
    SetVar VAR_MAP_LOCAL_0x03, 0
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8005, 661, SolaceonTown_FencePlayerUp
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Movement_FencePlayerIn
    WaitMovement
    GoTo SolaceonTown_FenceScene
    End

SolaceonTown_FencePlayerUp:
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Movement_StepNorth
    WaitMovement
    Return

SolaceonTown_FenceScene:
    ApplyMovement LOCALID_EXCAVATION_GRUNT_F, SolaceonTown_Movement_FaceWest
    ApplyMovement LOCALID_EXCAVATION_GRUNT_M, SolaceonTown_Movement_NoticeSouth
    WaitMovement
    Message SolaceonTown_Text_SolFence_1
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_CYRUS, SolaceonTown_Movement_CyrusToPlayer
    WaitMovement
    ApplyMovement LOCALID_EXCAVATION_GRUNT_F, SolaceonTown_Movement_Exclamation
    WaitMovement
    Message SolaceonTown_Text_SolFence_2
    WaitABPadPress
    Message SolaceonTown_Text_SolFence_3
    WaitABPadPress
    CloseMessage
    GoToIfDefeated TRAINER_ECLIPSE_GRUNT_SOL_07, SolaceonTown_FenceBattleF
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_SOL_07
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, SolaceonTown_FenceLost
    SetTrainerFlag TRAINER_ECLIPSE_GRUNT_SOL_07
SolaceonTown_FenceBattleF:
    StartTrainerBattle TRAINER_ECLIPSE_GRUNT_SOL_08
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, SolaceonTown_FenceLost
    SetTrainerFlag TRAINER_ECLIPSE_GRUNT_SOL_08
    ApplyMovement LOCALID_EXCAVATION_GRUNT_F, SolaceonTown_Movement_GruntFAside
    WaitMovement
    ApplyMovement LOCALID_EXCAVATION_GRUNT_M, SolaceonTown_Movement_GruntMAside
    WaitMovement
    ApplyMovement LOCALID_CYRUS, SolaceonTown_Movement_FaceNorth
    WaitMovement
    Message SolaceonTown_Text_SolFenceCyrus_1
    WaitABPadPress
    Message SolaceonTown_Text_SolFenceCyrus_2
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_CYRUS, SolaceonTown_Movement_CyrusIntoRuins
    WaitMovement
    RemoveObject LOCALID_CYRUS
    ReleaseAll
    End

SolaceonTown_FenceLost:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
SolaceonTown_Movement_FencePlayerIn:
    WalkNormalEast 2
    FaceEast
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_StepNorth:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_NoticeSouth:
    FaceSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_Exclamation:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_CyrusToPlayer:
    WalkNormalWest 3
    WalkNormalNorth
    FaceEast
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_GruntFAside:
    WalkNormalEast
    FaceWest
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_GruntMAside:
    WalkNormalSouth 2
    WalkNormalEast
    FaceWest
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_CyrusIntoRuins:
    WalkNormalEast
    WalkNormalNorth 5
    EndMovement

// ----------------------------------------------------------------- scene 3.4a part 7: the seizure (band E, once)
// Raid-scripts warps the player here with 50 set (Room 7); the frame table runs this on the first load at 50. The
// player stands south of the gate (580,660) facing north, Looker in front of the gate, Cyrus beside the player.
SolaceonTown_Seizure:
    LockAll
    SetVar VAR_MAP_LOCAL_0x02, 0
    SetFlag FLAG_SOL_TOWN_A
    FadeScreenOut
    WaitFadeScreen
    AddFreeCamera 580, 660
    SetPosition LOCALID_PLAYER, 580, 0, 660, DIR_NORTH
    RestoreCamera
    SetObjectEventPos LOCALID_LOOKER, 580, 659
    SetObjectEventDir LOCALID_LOOKER, DIR_SOUTH
    SetObjectEventMovementType LOCALID_LOOKER, MOVEMENT_TYPE_LOOK_SOUTH
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_8
    AddObject LOCALID_LOOKER
    SetObjectEventPos LOCALID_CYRUS, 579, 660
    SetObjectEventDir LOCALID_CYRUS, DIR_EAST
    SetObjectEventMovementType LOCALID_CYRUS, MOVEMENT_TYPE_LOOK_EAST
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_9
    AddObject LOCALID_CYRUS
    WaitTime 15, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    Message SolaceonTown_Text_SolSeizure_1
    WaitABPadPress
    Message SolaceonTown_Text_SolSeizure_2
    WaitABPadPress
    SetVar VAR_0x8004, ITEM_DUSK_STONE
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, SolaceonTown_SeizureNoRoom
    CallCommonScript CommonScript_AddItemQuantityNoLineFeed
SolaceonTown_SeizureNoRoom:
    Message SolaceonTown_Text_SolSeizure_3
    WaitABPadPress
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Movement_FaceWest
    WaitMovement
    Message SolaceonTown_Text_SolSeizure_4
    WaitABPadPress
    CloseMessage
    PlayFanfare SEQ_SE_DP_BEEP_sseq
    WaitFanfare
    Message SolaceonTown_Text_SolSeizure_5
    WaitABPadPress
    Message SolaceonTown_Text_SolSeizure_6
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_LOOKER, SolaceonTown_Movement_LookerIntoCompound
    WaitMovement
    RemoveObject LOCALID_LOOKER
    ApplyMovement LOCALID_CYRUS, SolaceonTown_Movement_CyrusSouthRoad
    WaitMovement
    RemoveObject LOCALID_CYRUS
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Movement_FaceNorth
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
SolaceonTown_Movement_LookerIntoCompound:
    WalkNormalNorth 3
    EndMovement

    .balign 4, 0
SolaceonTown_Movement_CyrusSouthRoad:
    WalkNormalWest 8
    EndMovement

// ------------------------------------------------------------------- NPC lines per band (screenplay Part 2)

SolaceonTown_TentClerk:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonTown_TentClerk_B
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_TentClerk_C
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_TentClerk_D
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_TentClerk_R
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_TentClerk_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_TentClerk_F
SolaceonTown_TentClerk_A:
    Message SolaceonTown_Text_SolTentClerkA_1
    WaitABPadPress
    Message SolaceonTown_Text_SolTentClerkA_2
    GoTo SolaceonTown_TalkEnd

SolaceonTown_TentClerk_B:
    Message SolaceonTown_Text_SolTentClerkB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_TentClerk_C:
    Message SolaceonTown_Text_SolTentClerkC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_TentClerk_D:
    Message SolaceonTown_Text_SolTentClerkD
    GoTo SolaceonTown_TalkEnd

SolaceonTown_TentClerk_R:
    Message SolaceonTown_Text_SolTentClerkR
    GoTo SolaceonTown_TalkEnd

SolaceonTown_TentClerk_E:
    Message SolaceonTown_Text_SolTentClerkE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_TentClerk_F:
    Message SolaceonTown_Text_SolGardenKeeperF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_PilgrimFather:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonTown_PilgrimFather_B
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_PilgrimFather_C
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_PilgrimFather_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_PilgrimFather_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_PilgrimFather_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_PilgrimFather_F
SolaceonTown_PilgrimFather_A:
    Message SolaceonTown_Text_SolPilgrimFatherA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_PilgrimFather_B:
    Message SolaceonTown_Text_SolPilgrimFatherB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_PilgrimFather_C:
    Message SolaceonTown_Text_SolPilgrimFatherC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_PilgrimFather_DR:
    Message SolaceonTown_Text_SolPilgrimFatherD
    GoTo SolaceonTown_TalkEnd

SolaceonTown_PilgrimFather_E:
    Message SolaceonTown_Text_SolPilgrimFatherE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_PilgrimFather_F:
    Message SolaceonTown_Text_SolPilgrimFatherF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_PilgrimSailor:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_PilgrimSailor_F
SolaceonTown_PilgrimSailor_ABCDRE:
    Message SolaceonTown_Text_SolPilgrimSailorA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_PilgrimSailor_F:
    Message SolaceonTown_Text_SolPilgrimSailorF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_PilgrimSister:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_PilgrimSister_CDRE
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_PilgrimSister_CDRE
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_PilgrimSister_CDRE
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_PilgrimSister_CDRE
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_PilgrimSister_F
SolaceonTown_PilgrimSister_AB:
    Message SolaceonTown_Text_SolPilgrimSisterA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_PilgrimSister_CDRE:
    Message SolaceonTown_Text_SolPilgrimSisterC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_PilgrimSister_F:
    Message SolaceonTown_Text_SolPilgrimSisterF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_PilgrimSon:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_PilgrimSon_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_PilgrimSon_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_PilgrimSon_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_PilgrimSon_DREF
SolaceonTown_PilgrimSon_ABC:
    Message SolaceonTown_Text_SolPilgrimSonA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_PilgrimSon_DREF:
    Message SolaceonTown_Text_SolPilgrimSonD
    GoTo SolaceonTown_TalkEnd

SolaceonTown_RoadGreeter:
    Call SolaceonTown_TalkStart
SolaceonTown_RoadGreeter_ABCDREF:
    Message SolaceonTown_Text_SolRoadGreeterA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_WallWidow:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonTown_WallWidow_B
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_WallWidow_C
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_WallWidow_D
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_WallWidow_R
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_WallWidow_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_WallWidow_F
SolaceonTown_WallWidow_A:
    Message SolaceonTown_Text_SolWallWidowA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_WallWidow_B:
    Message SolaceonTown_Text_SolWallWidowB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_WallWidow_C:
    Message SolaceonTown_Text_SolWallWidowC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_WallWidow_D:
    Message SolaceonTown_Text_SolWallWidowD
    GoTo SolaceonTown_TalkEnd

SolaceonTown_WallWidow_R:
    Message SolaceonTown_Text_SolWallWidowR
    GoTo SolaceonTown_TalkEnd

SolaceonTown_WallWidow_E:
    Message SolaceonTown_Text_SolWallWidowE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_WallWidow_F:
    Message SolaceonTown_Text_SolWallWidowF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_GardenGirl:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_GardenGirl_CDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_GardenGirl_CDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_GardenGirl_CDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_GardenGirl_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_GardenGirl_F
SolaceonTown_GardenGirl_AB:
    Message SolaceonTown_Text_SolGardenGirlA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_GardenGirl_CDR:
    Message SolaceonTown_Text_SolGardenGirlC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_GardenGirl_E:
    Message SolaceonTown_Text_SolGardenGirlE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_GardenGirl_F:
    Message SolaceonTown_Text_SolGardenGirlF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_LanternMan:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonTown_LanternMan_B
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_LanternMan_C
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_LanternMan_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_LanternMan_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_LanternMan_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_LanternMan_F
SolaceonTown_LanternMan_A:
    Message SolaceonTown_Text_UsedToBeNothing
    WaitABPadPress
    Message SolaceonTown_Text_SolLanternManA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_LanternMan_B:
    Message SolaceonTown_Text_UsedToBeNothing
    WaitABPadPress
    Message SolaceonTown_Text_SolLanternManB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_LanternMan_C:
    Message SolaceonTown_Text_UsedToBeNothing
    WaitABPadPress
    Message SolaceonTown_Text_SolLanternManC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_LanternMan_DR:
    Message SolaceonTown_Text_UsedToBeNothing
    WaitABPadPress
    Message SolaceonTown_Text_SolLanternManD
    GoTo SolaceonTown_TalkEnd

SolaceonTown_LanternMan_E:
    Message SolaceonTown_Text_UsedToBeNothing
    WaitABPadPress
    Message SolaceonTown_Text_SolLanternManE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_LanternMan_F:
    Message SolaceonTown_Text_UsedToBeNothing
    WaitABPadPress
    Message SolaceonTown_Text_SolLanternManF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_BelieverMother:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonTown_BelieverMother_B
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_BelieverMother_C
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_BelieverMother_D
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_BelieverMother_R
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_BelieverMother_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_BelieverMother_F
SolaceonTown_BelieverMother_A:
    Message SolaceonTown_Text_SolBelieverMotherA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_BelieverMother_B:
    Message SolaceonTown_Text_SolBelieverMotherB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_BelieverMother_C:
    Message SolaceonTown_Text_SolBelieverMotherC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_BelieverMother_D:
    Message SolaceonTown_Text_SolBelieverMotherD
    GoTo SolaceonTown_TalkEnd

SolaceonTown_BelieverMother_R:
    Message SolaceonTown_Text_SolBelieverMotherR
    GoTo SolaceonTown_TalkEnd

SolaceonTown_BelieverMother_E:
    Message SolaceonTown_Text_SolBelieverMotherE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_BelieverMother_F:
    Message SolaceonTown_Text_SolBelieverMotherF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_GateGreeter:
    Call SolaceonTown_TalkStart
SolaceonTown_GateGreeter_ABCDREF:
    Message SolaceonTown_Text_SolGateGreeterA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_ForecourtSweeper:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonTown_ForecourtSweeper_B
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_ForecourtSweeper_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_ForecourtSweeper_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_ForecourtSweeper_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_ForecourtSweeper_CDREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_ForecourtSweeper_CDREF
SolaceonTown_ForecourtSweeper_A:
    Message SolaceonTown_Text_SolForecourtSweeperA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_ForecourtSweeper_B:
    Message SolaceonTown_Text_SolForecourtSweeperB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_ForecourtSweeper_CDREF:
    Message SolaceonTown_Text_SolForecourtSweeperC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_IpOfficerGate:
    Call SolaceonTown_TalkStart
SolaceonTown_IpOfficerGate_ABCDREF:
    Message SolaceonTown_Text_SolIpOfficerGateE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_IpOfficerCourt:
    Call SolaceonTown_TalkStart
SolaceonTown_IpOfficerCourt_ABCDREF:
    Message SolaceonTown_Text_SolIpOfficerCourtE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_IpOfficerDig:
    Call SolaceonTown_TalkStart
SolaceonTown_IpOfficerDig_ABCDREF:
    Message SolaceonTown_Text_SolIpOfficerDigE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_DigWorker:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_DigWorker_F
SolaceonTown_DigWorker_ABCDRE:
    Message SolaceonTown_Text_SolDigWorkerA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_DigWorker_F:
    Message SolaceonTown_Text_SolDigWorkerF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_RuinManiac:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_RuinManiac_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_RuinManiac_F
SolaceonTown_RuinManiac_ABCDR:
    Message SolaceonTown_Text_SolRuinManiacA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_RuinManiac_E:
    Message SolaceonTown_Text_SolRuinManiacE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_RuinManiac_F:
    Message SolaceonTown_Text_SolRuinManiacF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_KennelKeeper:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonTown_KennelKeeper_B
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_KennelKeeper_C
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_KennelKeeper_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_KennelKeeper_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_KennelKeeper_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_KennelKeeper_F
SolaceonTown_KennelKeeper_A:
    Message SolaceonTown_Text_SolKennelKeeperA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_KennelKeeper_B:
    Message SolaceonTown_Text_SolKennelKeeperB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_KennelKeeper_C:
    Message SolaceonTown_Text_SolKennelKeeperC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_KennelKeeper_DR:
    Message SolaceonTown_Text_SolKennelKeeperD
    GoTo SolaceonTown_TalkEnd

SolaceonTown_KennelKeeper_E:
    Message SolaceonTown_Text_SolKennelKeeperE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_KennelKeeper_F:
    Message SolaceonTown_Text_SolKennelKeeperF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_LoadingGrunt:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_LoadingGrunt_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_LoadingGrunt_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_LoadingGrunt_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_LoadingGrunt_DREF
SolaceonTown_LoadingGrunt_ABC:
    Message SolaceonTown_Text_SolLoadingGruntB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_LoadingGrunt_DREF:
    Message SolaceonTown_Text_SolLoadingGruntD
    GoTo SolaceonTown_TalkEnd

SolaceonTown_Rancher:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonTown_Rancher_B
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_Rancher_C
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_Rancher_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_Rancher_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_Rancher_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_Rancher_F
SolaceonTown_Rancher_A:
    Message SolaceonTown_Text_SolRancherA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_Rancher_B:
    Message SolaceonTown_Text_SolRancherB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_Rancher_C:
    Message SolaceonTown_Text_SolRancherC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_Rancher_DR:
    Message SolaceonTown_Text_SolRancherD
    GoTo SolaceonTown_TalkEnd

SolaceonTown_Rancher_E:
    Message SolaceonTown_Text_SolRancherE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_Rancher_F:
    Message SolaceonTown_Text_SolRancherF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_SundayMan:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_SundayMan_C
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_SundayMan_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_SundayMan_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_SundayMan_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_SundayMan_F
SolaceonTown_SundayMan_AB:
    Message SolaceonTown_Text_IVisitTheLostTower
    WaitABPadPress
    Message SolaceonTown_Text_SolSundayManA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_SundayMan_C:
    Message SolaceonTown_Text_IVisitTheLostTower
    WaitABPadPress
    Message SolaceonTown_Text_SolSundayManC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_SundayMan_DR:
    Message SolaceonTown_Text_IVisitTheLostTower
    WaitABPadPress
    Message SolaceonTown_Text_SolSundayManD
    GoTo SolaceonTown_TalkEnd

SolaceonTown_SundayMan_E:
    Message SolaceonTown_Text_IVisitTheLostTower
    WaitABPadPress
    Message SolaceonTown_Text_SolSundayManE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_SundayMan_F:
    Message SolaceonTown_Text_SolSundayManF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_Doubter:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonTown_Doubter_B
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_Doubter_CDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_Doubter_CDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_Doubter_CDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_Doubter_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_Doubter_F
SolaceonTown_Doubter_A:
    Message SolaceonTown_Text_SolDoubterA
    GoTo SolaceonTown_TalkEnd

SolaceonTown_Doubter_B:
    Message SolaceonTown_Text_SolDoubterB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_Doubter_CDR:
    Message SolaceonTown_Text_SolDoubterC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_Doubter_E:
    Message SolaceonTown_Text_SolDoubterE
    GoTo SolaceonTown_TalkEnd

SolaceonTown_Doubter_F:
    Message SolaceonTown_Text_SolDoubterF
    GoTo SolaceonTown_TalkEnd

SolaceonTown_GateGruntR:
    Call SolaceonTown_TalkStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_GateGruntR_C
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_GateGruntR_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_GateGruntR_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_GateGruntR_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_GateGruntR_DREF
SolaceonTown_GateGruntR_AB:
    Message SolaceonTown_Text_SolGateGruntRB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_GateGruntR_C:
    Message SolaceonTown_Text_SolGateGruntRC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_GateGruntR_DREF:
    Message SolaceonTown_Text_SolGateGruntRD
    GoTo SolaceonTown_TalkEnd

SolaceonTown_ExcavationGruntMLines:
    Call SolaceonTown_GetBand
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_ExcavationGruntMLines_C
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_ExcavationGruntMLines_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_ExcavationGruntMLines_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_ExcavationGruntMLines_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_ExcavationGruntMLines_DREF
SolaceonTown_ExcavationGruntMLines_AB:
    Message SolaceonTown_Text_SolExcavationGruntMB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_ExcavationGruntMLines_C:
    Message SolaceonTown_Text_SolExcavationGruntMC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_ExcavationGruntMLines_DREF:
    Message SolaceonTown_Text_SolExcavationGruntMD
    GoTo SolaceonTown_TalkEnd

SolaceonTown_ExcavationGruntFLines:
    Call SolaceonTown_GetBand
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_ExcavationGruntFLines_C
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_ExcavationGruntFLines_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_ExcavationGruntFLines_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_ExcavationGruntFLines_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_ExcavationGruntFLines_DREF
SolaceonTown_ExcavationGruntFLines_AB:
    Message SolaceonTown_Text_SolExcavationGruntFB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_ExcavationGruntFLines_C:
    Message SolaceonTown_Text_SolExcavationGruntFC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_ExcavationGruntFLines_DREF:
    Message SolaceonTown_Text_SolExcavationGruntFD
    GoTo SolaceonTown_TalkEnd

SolaceonTown_GateGruntLLines:
    Call SolaceonTown_GetBand
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_GateGruntLLines_C
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_GateGruntLLines_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_GateGruntLLines_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_GateGruntLLines_DREF
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_GateGruntLLines_DREF
SolaceonTown_GateGruntLLines_AB:
    Message SolaceonTown_Text_SolGateGruntLB
    GoTo SolaceonTown_TalkEnd

SolaceonTown_GateGruntLLines_C:
    Message SolaceonTown_Text_SolGateGruntLC
    GoTo SolaceonTown_TalkEnd

SolaceonTown_GateGruntLLines_DREF:
    Message SolaceonTown_Text_SolGateGruntLD
    GoTo SolaceonTown_TalkEnd


// ---------------------------------------------------------------- signs per band (screenplay Part 1)
SolaceonTown_GatePlaque:
    Call SolaceonTown_SignStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonTown_GatePlaque_BC
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_GatePlaque_BC
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_GatePlaque_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_GatePlaque_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_GatePlaque_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_GatePlaque_F
SolaceonTown_GatePlaque_A:
    Message SolaceonTown_Text_SolGatePlaqueA
    GoTo SolaceonTown_SignEnd

SolaceonTown_GatePlaque_BC:
    Message SolaceonTown_Text_SolGatePlaqueBC
    GoTo SolaceonTown_SignEnd

SolaceonTown_GatePlaque_DR:
    Message SolaceonTown_Text_SolGatePlaqueDR
    GoTo SolaceonTown_SignEnd

SolaceonTown_GatePlaque_E:
    Message SolaceonTown_Text_SolGatePlaqueE
    GoTo SolaceonTown_SignEnd

SolaceonTown_GatePlaque_F:
    Message SolaceonTown_Text_SolGatePlaqueF
    GoTo SolaceonTown_SignEnd

SolaceonTown_TentSign:
    Call SolaceonTown_SignStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_TentSign_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_TentSign_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_TentSign_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_TentSign_F
SolaceonTown_TentSign_ABC:
    Message SolaceonTown_Text_SolTentSignABC
    GoTo SolaceonTown_SignEnd

SolaceonTown_TentSign_DR:
    Message SolaceonTown_Text_SolTentSignDR
    GoTo SolaceonTown_SignEnd

SolaceonTown_TentSign_E:
    Message SolaceonTown_Text_SolTentSignE
    GoTo SolaceonTown_SignEnd

SolaceonTown_TentSign_F:
    Message SolaceonTown_Text_SolTentSignF
    GoTo SolaceonTown_SignEnd

SolaceonTown_DigSign:
    Call SolaceonTown_SignStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonTown_DigSign_BCDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_DigSign_BCDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_DigSign_BCDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_DigSign_BCDR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_DigSign_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_DigSign_F
SolaceonTown_DigSign_A:
    Message SolaceonTown_Text_SolDigSignA
    GoTo SolaceonTown_SignEnd

SolaceonTown_DigSign_BCDR:
    Message SolaceonTown_Text_SolDigSignBCDR
    GoTo SolaceonTown_SignEnd

SolaceonTown_DigSign_E:
    Message SolaceonTown_Text_SolDigSignE
    GoTo SolaceonTown_SignEnd

SolaceonTown_DigSign_F:
    Message SolaceonTown_Text_SolDigSignF
    GoTo SolaceonTown_SignEnd

SolaceonTown_KennelSign:
    Call SolaceonTown_SignStart
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_B, SolaceonTown_KennelSign_BC
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_C, SolaceonTown_KennelSign_BC
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_D, SolaceonTown_KennelSign_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_R, SolaceonTown_KennelSign_DR
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_E, SolaceonTown_KennelSign_E
    GoToIfEq VAR_MAP_LOCAL_0x04, BAND_F, SolaceonTown_KennelSign_F
SolaceonTown_KennelSign_A:
    Message SolaceonTown_Text_SolKennelSignA
    GoTo SolaceonTown_SignEnd

SolaceonTown_KennelSign_BC:
    Message SolaceonTown_Text_SolKennelSignBC
    GoTo SolaceonTown_SignEnd

SolaceonTown_KennelSign_DR:
    Message SolaceonTown_Text_SolKennelSignDR
    GoTo SolaceonTown_SignEnd

SolaceonTown_KennelSign_E:
    Message SolaceonTown_Text_SolKennelSignE
    GoTo SolaceonTown_SignEnd

SolaceonTown_KennelSign_F:
    Message SolaceonTown_Text_SolKennelSignF
    GoTo SolaceonTown_SignEnd
