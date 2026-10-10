#include "macros/scrcmd.inc"
#include "res/text/bank/oreburgh_mine_side_tunnel.h"
#include "res/field/events/events_oreburgh_mine_side_tunnel.h"

// Arc 1 r3 (hum), "The shard hums": the Oreburgh Mine side tunnel, entered through the crack behind the old crates in Mine B2F's
// north-west nook. Gen 5 mine Pokemon live here. The miner's missing Machop is huddled at the far (west) end
// until it is calmed. Quest flags (unreferenced stock flags, claimed for this quest):
#define FLAG_HUM_STARTED FLAG_UNK_0x0958 // talked to the miner in Oreburgh City
#define FLAG_HUM_CALMED  FLAG_UNK_0x0959 // Machop calmed in this tunnel (also the tunnel Machop's hide flag)
// VAR_MAP_LOCAL_0 drives the reader's buzz coords: 0 inert (Machop already calmed), 1 just arrived,
// 2 buzzing louder (x31), 3 going wild (x14), 4 calming scene running (x8).

    ScriptEntry OreburghMineSideTunnel_OnTransition
    ScriptEntry OreburghMineSideTunnel_BuzzLouder
    ScriptEntry OreburghMineSideTunnel_BuzzWild
    ScriptEntry OreburghMineSideTunnel_CalmMachop
    ScriptEntryEnd

OreburghMineSideTunnel_OnTransition:
    SetVar VAR_MAP_LOCAL_0, 0
    GoToIfSet FLAG_HUM_CALMED, OreburghMineSideTunnel_OnTransitionEnd
    SetVar VAR_MAP_LOCAL_0, 1
OreburghMineSideTunnel_OnTransitionEnd:
    End

OreburghMineSideTunnel_BuzzLouder:
    LockAll
    SetVar VAR_MAP_LOCAL_0, 2
    PlayFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    WaitFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    PlayFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    WaitFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    Message OreburghMineSideTunnel_Text_BuzzLouder
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghMineSideTunnel_BuzzWild:
    LockAll
    SetVar VAR_MAP_LOCAL_0, 3
    Call OreburghMineSideTunnel_BuzzThrice
    Message OreburghMineSideTunnel_Text_BuzzWild
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

OreburghMineSideTunnel_BuzzThrice:
    PlayFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    WaitFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    PlayFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    WaitFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    PlayFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    WaitFanfare SEQ_SE_DP_VS_SEEKER_BEEP
    Return

// Coord x8 (rows 6-8) or talking to the Machop. Scripted calming beat (no battle, so the miner's Machop can't
// be caught): the Machop lunges, the player stands their ground or backs off, it calms, the sliver crumbles.
OreburghMineSideTunnel_CalmMachop:
    LockAll
    SetVar VAR_MAP_LOCAL_0, 4
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8005, 6, OreburghMineSideTunnel_PlayerToRow7FromNorth
    CallIfEq VAR_0x8005, 8, OreburghMineSideTunnel_PlayerToRow7FromSouth
    ApplyMovement LOCALID_PLAYER, OreburghMineSideTunnel_Movement_FaceWest
    WaitMovement
    Call OreburghMineSideTunnel_BuzzThrice
    Message OreburghMineSideTunnel_Text_BuzzLoudest
    CloseMessage
    ApplyMovement LOCALID_HUM_MACHOP, OreburghMineSideTunnel_Movement_Exclamation
    WaitMovement
    PlayCry SPECIES_MACHOP
    WaitCry
    Message OreburghMineSideTunnel_Text_MachopHuddled
    CloseMessage
    ApplyMovement LOCALID_HUM_MACHOP, OreburghMineSideTunnel_Movement_MachopLunge
    WaitMovement
    PlayFanfare SEQ_SE_DP_WALL_HIT2
    ShakeCamera 10, 2
    PlayCry SPECIES_MACHOP
    WaitCry
    BufferPlayerName 0
    Message OreburghMineSideTunnel_Text_MachopSwung
    Message OreburghMineSideTunnel_Text_StandYourGround
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, OreburghMineSideTunnel_BackOff
    BufferPlayerName 0
    Message OreburghMineSideTunnel_Text_StoodStill
    CloseMessage
    ApplyMovement LOCALID_HUM_MACHOP, OreburghMineSideTunnel_Movement_MachopApproach1
    WaitMovement
    GoTo OreburghMineSideTunnel_Calmed

OreburghMineSideTunnel_BackOff:
    CloseMessage
    ApplyMovement LOCALID_PLAYER, OreburghMineSideTunnel_Movement_PlayerBackOff
    WaitMovement
    ApplyMovement LOCALID_HUM_MACHOP, OreburghMineSideTunnel_Movement_MachopFlail
    WaitMovement
    BufferPlayerName 0
    Message OreburghMineSideTunnel_Text_BackedOff
    CloseMessage
    ApplyMovement LOCALID_HUM_MACHOP, OreburghMineSideTunnel_Movement_MachopApproach2
    WaitMovement
OreburghMineSideTunnel_Calmed:
    BufferPlayerName 0
    Message OreburghMineSideTunnel_Text_LeanedIn
    CloseMessage
    WaitTime 20, VAR_RESULT
    PlayFanfare SEQ_SE_DP_KIRAKIRA
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_MEDIUM, COLOR_WHITE
    WaitFadeScreen
    Message OreburghMineSideTunnel_Text_SliverCrumbled
    Message OreburghMineSideTunnel_Text_ReaderQuiet
    CloseMessage
    PlayCry SPECIES_MACHOP
    ApplyMovement LOCALID_HUM_MACHOP, OreburghMineSideTunnel_Movement_MachopHappy
    WaitMovement
    WaitCry
    Message OreburghMineSideTunnel_Text_MachopDashedOff
    CloseMessage
    ApplyMovement LOCALID_PLAYER, OreburghMineSideTunnel_Movement_PlayerStepAside
    WaitMovement
    ApplyMovement LOCALID_HUM_MACHOP, OreburghMineSideTunnel_Movement_MachopRunOut
    WaitMovement
    RemoveObject LOCALID_HUM_MACHOP
    SetFlag FLAG_HUM_CALMED
    SetVar VAR_MAP_LOCAL_0, 0
    BufferPlayerName 0
    Message OreburghMineSideTunnel_Text_FollowedOut
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_OREBURGH_MINE_B2F, 0, 3, 18, DIR_EAST
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

OreburghMineSideTunnel_PlayerToRow7FromNorth:
    ApplyMovement LOCALID_PLAYER, OreburghMineSideTunnel_Movement_StepSouth
    WaitMovement
    Return

OreburghMineSideTunnel_PlayerToRow7FromSouth:
    ApplyMovement LOCALID_PLAYER, OreburghMineSideTunnel_Movement_StepNorth
    WaitMovement
    Return

    .balign 4, 0
OreburghMineSideTunnel_Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
OreburghMineSideTunnel_Movement_StepSouth:
    WalkNormalSouth
    EndMovement

    .balign 4, 0
OreburghMineSideTunnel_Movement_StepNorth:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
OreburghMineSideTunnel_Movement_Exclamation:
    FaceEast
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
// Machop starts at (3,7); the player stands at (8,7)
OreburghMineSideTunnel_Movement_MachopLunge:
    WalkFastEast 3
    JumpOnSpotFastEast
    EndMovement

    .balign 4, 0
OreburghMineSideTunnel_Movement_MachopApproach1:
    Delay16
    WalkSlowEast
    EndMovement

    .balign 4, 0
OreburghMineSideTunnel_Movement_PlayerBackOff:
    LockDir
    WalkSlowEast
    UnlockDir
    EndMovement

    .balign 4, 0
OreburghMineSideTunnel_Movement_MachopFlail:
    JumpOnSpotFastEast
    JumpOnSpotFastEast
    Delay16
    WalkOnSpotSlowEast
    EndMovement

    .balign 4, 0
OreburghMineSideTunnel_Movement_MachopApproach2:
    Delay16
    WalkSlowEast 2
    EndMovement

    .balign 4, 0
OreburghMineSideTunnel_Movement_MachopHappy:
    JumpOnSpotFastEast
    JumpOnSpotFastEast
    EndMovement

    .balign 4, 0
OreburghMineSideTunnel_Movement_PlayerStepAside:
    WalkNormalSouth
    FaceNorth
    EndMovement

    .balign 4, 0
OreburghMineSideTunnel_Movement_MachopRunOut:
    WalkFastEast 9
    EndMovement
