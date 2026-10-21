#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "twoshot" (moves.md, "Templates"): both mons for the whole move, a punch on the hit.
L_0:
    CamTplTwoShotOpen
    JumpIfContest L_1
    JumpIfBattlerSide BATTLER_ROLE_ATTACKER, L_2, L_3
    CamTplClose
    End

L_1:
    LoadParticleResource 0, sonic_boom_spa
    LoadParticleResource 1, sonic_boom_spa
    PlayMovingSoundEffectAtkDef SEQ_SE_DP_146, BATTLE_SOUND_PAN_LEFT, BATTLE_SOUND_PAN_RIGHT, 4, 2
    CreateEmitterEx 0, 1, 3, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BLinear 1, 0, 0, 0, 13, 64
    Delay 4
    CreateEmitter 1, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    CreateEmitterEx 0, 2, 3, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BLinear 2, 0, 0, 0, 13, 64
    Delay 4
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    CreateEmitterEx 0, 3, 3, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BLinear 3, 0, 0, 0, 13, 64
    Delay 4
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    UnloadParticleSystem 1
    CamTplClose
    End

L_2:
    LoadParticleResource 0, sonic_boom_spa
    LoadParticleResource 1, sonic_boom_spa
    PlayMovingSoundEffectAtkDef SEQ_SE_DP_146, BATTLE_SOUND_PAN_LEFT, BATTLE_SOUND_PAN_RIGHT, 4, 2
    CreateEmitterEx 0, 1, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BLinear 1, 0, 0, 0, 13, 64
    Delay 4
    CreateEmitter 1, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    CreateEmitterEx 0, 2, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BLinear 2, 0, 0, 0, 13, 64
    Delay 4
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    CreateEmitterEx 0, 3, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BLinear 3, 0, 0, 0, 13, 64
    Delay 4
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    UnloadParticleSystem 1
    CamTplClose
    End

L_3:
    LoadParticleResource 0, sonic_boom_spa
    LoadParticleResource 1, sonic_boom_spa
    PlayMovingSoundEffectAtkDef SEQ_SE_DP_146, BATTLE_SOUND_PAN_LEFT, BATTLE_SOUND_PAN_RIGHT, 4, 2
    CreateEmitterEx 0, 1, 2, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BLinear 1, 0, 0, 0, 13, 64
    Delay 4
    CreateEmitter 1, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    CreateEmitterEx 0, 2, 2, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BLinear 2, 0, 0, 0, 13, 64
    Delay 4
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    CreateEmitterEx 0, 3, 2, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BLinear 3, 0, 0, 0, 13, 64
    Delay 4
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    UnloadParticleSystem 1
    CamTplClose
    End
