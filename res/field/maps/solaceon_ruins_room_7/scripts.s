#include "macros/scrcmd.inc"
#include "res/text/bank/solaceon_ruins_room_7.h"
#include "res/field/maps/locals/solaceon_ruins_room_7.h"

// Solaceon raid: the vault (screenplay.md scene 3.4a parts 5-6; raid_maps.md "Room 7: the vault").
// VAR_SOLACEON_PROGRESS here:
//   30-32  the barrier is up (row z 5, FLAG_SOL_RAID_D hides it); Cyrus waits at it; walking up to it says so
//   33     the barrier is down; Cyrus stands aside; the first step past the barrier line (row z 6) starts the vault
//   40     the vault scene: Indra, the battle (losing whites out; the scene replays from the start at 40)
//   45     Indra beaten and gone (FLAG_SOL_RAID_G), the cave-in, Looker and the ledger, the switch is free
//          (FLAG_SOL_RAID_E when turned: lit racks hide, the dark twins show)
//   50     set with FLAG_SOL_RAID_F before the warp to town: the vault is scorched and empty
// Map-local hide flags (recomputed in SolaceonRuinsRoom7_OnTransition):
//   FLAG_MAP_LOCAL_HIDE_OBSTACLE_16 Looker (shown 45-49)   _17 the dark racks (shown 45-49 with E)
//   _18 the cave-in rubble (shown from 45)
// Map-local vars: _01 the vault trigger is armed (33, 40), _02 the barrier warning is armed (30-32)

#define SOL_RAID_TOWN_X 580     // back in town: south of the Sanctuary gate, where the seizure (3.4a part 7) plays
#define SOL_RAID_TOWN_Z 660

    ScriptEntry SolaceonRuinsRoom7_Inscription
    ScriptEntry SolaceonRuinsRoom7_OnTransition
    ScriptEntry SolaceonRuinsRoom7_RaidBarrier
    ScriptEntry SolaceonRuinsRoom7_RaidBarrierStep
    ScriptEntry SolaceonRuinsRoom7_RaidCyrus
    ScriptEntry SolaceonRuinsRoom7_RaidLooker
    ScriptEntry SolaceonRuinsRoom7_RaidVault
    ScriptEntry SolaceonRuinsRoom7_RaidSwitch
    ScriptEntry SolaceonRuinsRoom7_RaidRackLit
    ScriptEntry SolaceonRuinsRoom7_RaidRackDark
    ScriptEntry SolaceonRuinsRoom7_RaidRubble
    ScriptEntryEnd

SolaceonRuinsRoom7_Inscription:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    MessageUnown SolaceonRuinsRoom7_Text_AllLivesTouchOtherLives
    WaitButton
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom7_OnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    SetVar VAR_MAP_LOCAL_0x01, 0
    SetVar VAR_MAP_LOCAL_0x02, 0
    GoToIfLt VAR_SOLACEON_PROGRESS, 30, SolaceonRuinsRoom7_OnTransitionEnd
    GoToIfGe VAR_SOLACEON_PROGRESS, 50, SolaceonRuinsRoom7_OnTransitionAfter
    GoToIfGe VAR_SOLACEON_PROGRESS, 33, SolaceonRuinsRoom7_OnTransitionOpen
    SetVar VAR_MAP_LOCAL_0x02, 1
    GoTo SolaceonRuinsRoom7_OnTransitionEnd
    End

SolaceonRuinsRoom7_OnTransitionOpen:
    SetObjectEventPos LOCALID_R7_CYRUS, 6, 4
    GoToIfGe VAR_SOLACEON_PROGRESS, 45, SolaceonRuinsRoom7_OnTransitionIndraGone
    GoToIfEq VAR_SOLACEON_PROGRESS, 33, SolaceonRuinsRoom7_OnTransitionArmVault
    GoToIfEq VAR_SOLACEON_PROGRESS, 40, SolaceonRuinsRoom7_OnTransitionArmVault
    GoTo SolaceonRuinsRoom7_OnTransitionEnd
    End

SolaceonRuinsRoom7_OnTransitionArmVault:
    SetVar VAR_MAP_LOCAL_0x01, 1
    GoTo SolaceonRuinsRoom7_OnTransitionEnd
    End

SolaceonRuinsRoom7_OnTransitionIndraGone:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    GoToIfUnset FLAG_SOL_RAID_E, SolaceonRuinsRoom7_OnTransitionEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    GoTo SolaceonRuinsRoom7_OnTransitionEnd
    End

SolaceonRuinsRoom7_OnTransitionAfter:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
SolaceonRuinsRoom7_OnTransitionEnd:
    End

// ------------------------------------------------------------------------------------------------- the barrier
SolaceonRuinsRoom7_RaidBarrier:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message SolaceonRuinsRoom7_Text_RaidBarrier
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

// Walking up to the barrier (row z 4) while it is up: once per visit
SolaceonRuinsRoom7_RaidBarrierStep:
    LockAll
    SetVar VAR_MAP_LOCAL_0x02, 0
    ApplyMovement LOCALID_PLAYER, SolaceonRuinsRoom7_Movement_FaceSouth
    WaitMovement
    Message SolaceonRuinsRoom7_Text_RaidBarrier
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom7_RaidCyrus:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfLt VAR_SOLACEON_PROGRESS, 33, SolaceonRuinsRoom7_RaidCyrusNotYet
    GoToIfLt VAR_SOLACEON_PROGRESS, 45, SolaceonRuinsRoom7_RaidCyrusItsDown
    GoToIfSet FLAG_SOL_RAID_E, SolaceonRuinsRoom7_RaidCyrusEnd
    BufferPlayerName 0
    Message SolaceonRuinsRoom7_Text_RaidCyrusSwitchYours
    GoTo SolaceonRuinsRoom7_RaidCyrusEnd
    End

SolaceonRuinsRoom7_RaidCyrusNotYet:
    Message SolaceonRuinsRoom7_Text_RaidCyrusNotYet
    GoTo SolaceonRuinsRoom7_RaidCyrusEnd
    End

SolaceonRuinsRoom7_RaidCyrusItsDown:
    Message SolaceonRuinsRoom7_Text_RaidCyrusItsDown
SolaceonRuinsRoom7_RaidCyrusEnd:
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom7_RaidLooker:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message SolaceonRuinsRoom7_Text_RaidLookerSwitch
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

// --------------------------------------------------------------------------------------------- the vault (40)
// The first step past the barrier line at 33, or again at 40 after losing to Indra.
SolaceonRuinsRoom7_RaidVault:
    LockAll
    SetVar VAR_MAP_LOCAL_0x01, 0
    SetVar VAR_SOLACEON_PROGRESS, 40
    // the player walks into the middle aisle and down to (5,8), two tiles from Indra's back
SolaceonRuinsRoom7_RaidVaultAisle:
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8004, 5, SolaceonRuinsRoom7_RaidVaultDown
    CallIfLt VAR_0x8004, 5, SolaceonRuinsRoom7_RaidStepEast
    CallIfGt VAR_0x8004, 5, SolaceonRuinsRoom7_RaidStepWest
    GoTo SolaceonRuinsRoom7_RaidVaultAisle
    End

SolaceonRuinsRoom7_RaidVaultDown:
    ApplyMovement LOCALID_PLAYER, SolaceonRuinsRoom7_Movement_PlayerDown
    WaitMovement
    // Cyrus walks in behind
    ApplyMovement LOCALID_R7_CYRUS, SolaceonRuinsRoom7_Movement_CyrusIn
    WaitMovement
    Message SolaceonRuinsRoom7_Text_RaidIndraAllThree
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_R7_INDRA, SolaceonRuinsRoom7_Movement_FaceNorth
    WaitMovement
    Message SolaceonRuinsRoom7_Text_RaidIndraRowansKid
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidIndraManWhoWalkedOut
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidCyrusSilent
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidIndraLate
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidIndraSaros
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidIndraKeepTheDoor
    WaitABPadPress
    CloseMessage
    StartTrainerBattle TRAINER_INDRA_SANCTUARY
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, SolaceonRuinsRoom7_RaidLost
    SetVar VAR_SOLACEON_PROGRESS, 45
    Message SolaceonRuinsRoom7_Text_RaidIndraHm
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidIndraWhatStoppedYou
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidCyrusSilent
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidIndraKeepIt
    WaitABPadPress
    CloseMessage
    // she walks to the fresh tunnel in the west wall and stops at the edge
    ApplyMovement LOCALID_R7_INDRA, SolaceonRuinsRoom7_Movement_IndraToTunnel
    ApplyMovement LOCALID_PLAYER, SolaceonRuinsRoom7_Movement_WatchWest
    WaitMovement
    Message SolaceonRuinsRoom7_Text_RaidIndraDontFollow
    WaitABPadPress
    CloseMessage
    RemoveObject LOCALID_R7_INDRA
    SetFlag FLAG_SOL_RAID_G
    // the roof comes down behind her
    PlaySE SEQ_SE_DP_DODON_sseq
    ShakeCamera 24, 4
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    AddObject LOCALID_R7_RUBBLE
    PlaySE SEQ_SE_DP_WALL_HIT2_sseq
    WaitTime 8, VAR_RESULT
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitSE SEQ_SE_DP_WALL_HIT2_sseq
    ApplyMovement LOCALID_R7_CYRUS, SolaceonRuinsRoom7_Movement_FaceWest
    WaitMovement
    Message SolaceonRuinsRoom7_Text_RaidCyrusLetHerGo
    WaitABPadPress
    CloseMessage
    // part 6: Looker runs in from the barrier side with the ledger
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    AddObject LOCALID_R7_LOOKER
    ApplyMovement LOCALID_R7_LOOKER, SolaceonRuinsRoom7_Movement_LookerRunIn
    WaitMovement
    ApplyMovement LOCALID_PLAYER, SolaceonRuinsRoom7_Movement_FaceEast
    ApplyMovement LOCALID_R7_CYRUS, SolaceonRuinsRoom7_Movement_FaceEast
    WaitMovement
    Message SolaceonRuinsRoom7_Text_RaidLookerGone
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidLookerRegistry
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidLookerLeftBehind
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidLookerFamilies
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, SolaceonRuinsRoom7_Movement_FaceSouth
    ApplyMovement LOCALID_R7_CYRUS, SolaceonRuinsRoom7_Movement_FaceSouth
    ApplyMovement LOCALID_R7_LOOKER, SolaceonRuinsRoom7_Movement_FaceSouth
    WaitMovement
    WaitTime 60, VAR_RESULT
    Message SolaceonRuinsRoom7_Text_RaidLookerDestroyed
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, SolaceonRuinsRoom7_Movement_FaceNorth
    WaitMovement
    Message SolaceonRuinsRoom7_Text_RaidCyrusRacks
    WaitABPadPress
    BufferPlayerName 0
    Message SolaceonRuinsRoom7_Text_RaidCyrusSwitchYours
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, SolaceonRuinsRoom7_Movement_FaceSouth
    WaitMovement
    ReleaseAll
    End

SolaceonRuinsRoom7_RaidStepEast:
    ApplyMovement LOCALID_PLAYER, SolaceonRuinsRoom7_Movement_East1
    WaitMovement
    Return

SolaceonRuinsRoom7_RaidStepWest:
    ApplyMovement LOCALID_PLAYER, SolaceonRuinsRoom7_Movement_West1
    WaitMovement
    Return

// Losing to Indra: stock whiteout; progress stays 40 and the scene replays from the start
SolaceonRuinsRoom7_RaidLost:
    BlackOutFromBattle
    ReleaseAll
    End

// --------------------------------------------------------------------------------------------- the switch (45)
// A bg event on the plinth (5,11), read from (5,10) facing south: Indra's tile until she leaves.
SolaceonRuinsRoom7_RaidSwitch:
    GoToIfLt VAR_SOLACEON_PROGRESS, 45, SolaceonRuinsRoom7_RaidSwitchNothing
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfSet FLAG_SOL_RAID_E, SolaceonRuinsRoom7_RaidSwitchTurned
    GoToIfGe VAR_SOLACEON_PROGRESS, 50, SolaceonRuinsRoom7_RaidSwitchTurned
    Message SolaceonRuinsRoom7_Text_RaidSwitch
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, SolaceonRuinsRoom7_RaidSwitchNo
    CloseMessage
    PlaySE SEQ_SE_DP_KI_GASYAN_sseq
    WaitSE SEQ_SE_DP_KI_GASYAN_sseq
    // every rack flares, then the light drains out of them
    PlaySE SEQ_SE_PL_SYUWA_sseq
    ShakeCamera 24, 4
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    SetFlag FLAG_SOL_RAID_E
    RemoveObject LOCALID_R7_RACK_0_LIT
    RemoveObject LOCALID_R7_RACK_1_LIT
    RemoveObject LOCALID_R7_RACK_2_LIT
    RemoveObject LOCALID_R7_RACK_3_LIT
    RemoveObject LOCALID_R7_RACK_4_LIT
    RemoveObject LOCALID_R7_RACK_5_LIT
    RemoveObject LOCALID_R7_CRYSTAL_LIT
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    AddObject LOCALID_R7_RACK_0_DARK
    AddObject LOCALID_R7_RACK_1_DARK
    AddObject LOCALID_R7_RACK_2_DARK
    AddObject LOCALID_R7_RACK_3_DARK
    AddObject LOCALID_R7_RACK_4_DARK
    AddObject LOCALID_R7_RACK_5_DARK
    AddObject LOCALID_R7_CRYSTAL_DARK
    WaitTime 10, VAR_RESULT
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitSE SEQ_SE_PL_SYUWA_sseq
    Message SolaceonRuinsRoom7_Text_RaidDrained
    WaitABPadPress
    CloseMessage
    PlaySE SEQ_SE_DP_BEEP_sseq
    WaitSE SEQ_SE_DP_BEEP_sseq
    PlaySE SEQ_SE_DP_BEEP_sseq
    WaitSE SEQ_SE_DP_BEEP_sseq
    Message SolaceonRuinsRoom7_Text_RaidPoketchBuzzes
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidRuthGone
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidLookerKahnHasEnough
    WaitABPadPress
    // Looker opens the ledger again; the player reads over his shoulder
    Message SolaceonRuinsRoom7_Text_RaidLedgerElias
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidLedgerTeo
    WaitABPadPress
    Message SolaceonRuinsRoom7_Text_RaidLookerPolice
    WaitABPadPress
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    // set before the warp so the town loads in band E (part 7 is town-scripts')
    SetVar VAR_SOLACEON_PROGRESS, 50
    SetFlag FLAG_SOL_RAID_F
    Warp MAP_HEADER_SOLACEON_TOWN, SOL_RAID_TOWN_X, SOL_RAID_TOWN_Z, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

SolaceonRuinsRoom7_RaidSwitchNo:
    CloseMessage
    Message SolaceonRuinsRoom7_Text_RaidCyrusTakeYourTime
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom7_RaidSwitchTurned:
    Message SolaceonRuinsRoom7_Text_RaidSwitchTurned
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom7_RaidSwitchNothing:
    End

// ------------------------------------------------------------------------------------------------ the objects
SolaceonRuinsRoom7_RaidRackLit:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message SolaceonRuinsRoom7_Text_RaidRackLit
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom7_RaidRackDark:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message SolaceonRuinsRoom7_Text_RaidRackDark
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

SolaceonRuinsRoom7_RaidRubble:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message SolaceonRuinsRoom7_Text_RaidRubble
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
SolaceonRuinsRoom7_Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom7_Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom7_Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom7_Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom7_Movement_East1:
    WalkNormalEast
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom7_Movement_West1:
    WalkNormalWest
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom7_Movement_PlayerDown:
    WalkNormalSouth 2
    FaceSouth
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom7_Movement_CyrusIn:
    WalkNormalSouth 2
    WalkNormalWest
    WalkNormalSouth
    FaceSouth
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom7_Movement_IndraToTunnel:
    WalkNormalWest 3
    FaceWest
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom7_Movement_WatchWest:
    Delay8 2
    FaceWest
    EndMovement

    .balign 4, 0
SolaceonRuinsRoom7_Movement_LookerRunIn:
    WalkFastWest
    WalkFastSouth 4
    WalkFastWest
    FaceWest
    EndMovement
