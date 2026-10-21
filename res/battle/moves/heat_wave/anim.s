#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "wide" (moves.md, "Templates"): a pull-back over the whole field.
L_0:
    LoadParticleResource 0, heat_wave_spa
    CamTplWideOpen
    JumpIfContest L_1
    JumpIfBattlerSide BATTLER_ROLE_ATTACKER, L_2, L_3
    CamTplClose
    End

L_1:
    CreateEmitter 0, 0, EMITTER_CB_NONE
    PlayMovingSoundEffectAtkDef SEQ_SE_DP_W257, BATTLE_SOUND_PAN_LEFT, BATTLE_SOUND_PAN_RIGHT, 4, 2
    WaitForAnimTasks
    Delay 35
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End

L_2:
    CreateEmitter 0, 0, EMITTER_CB_NONE
    PlayMovingSoundEffectAtkDef SEQ_SE_DP_W257, BATTLE_SOUND_PAN_LEFT, BATTLE_SOUND_PAN_RIGHT, 4, 2
    CamTplImpact 3, 8
    Func_Shake 3, 0, 1, 3, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_Shake 3, 0, 1, 3, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER_PARTNER
    WaitForAnimTasks
    Func_MoveBattlerX2 4, -20, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_MoveBattlerX2 4, -20, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER_PARTNER
    WaitForAnimTasks
    Delay 35
    Func_MoveBattlerX2 5, 20, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_MoveBattlerX2 5, 20, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER_PARTNER
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End

L_3:
    CreateEmitter 0, 1, EMITTER_CB_NONE
    PlayMovingSoundEffectAtkDef SEQ_SE_DP_W257, BATTLE_SOUND_PAN_LEFT, BATTLE_SOUND_PAN_RIGHT, 4, 2
    CamTplImpact 3, 8
    Func_Shake 3, 0, 1, 3, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_Shake 3, 0, 1, 3, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER_PARTNER
    WaitForAnimTasks
    Func_MoveBattlerX2 4, -20, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_MoveBattlerX2 4, -20, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER_PARTNER
    WaitForAnimTasks
    Delay 35
    Func_MoveBattlerX2 5, 20, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_MoveBattlerX2 5, 20, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER_PARTNER
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
