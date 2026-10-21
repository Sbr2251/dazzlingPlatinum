#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, seed_bomb_spa
    CamTplPushOpen
    PlaySoundEffectC SEQ_SE_DP_HURU2
    CreateEmitterEx 0, 0, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BParabolic 0, 0, 0, 0, 18, 64
    Delay 2
    PlaySoundEffectC SEQ_SE_DP_HURU2
    CreateEmitterEx 0, 1, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BParabolic 1, 0, 0, 0, 18, 64
    Delay 2
    PlaySoundEffectC SEQ_SE_DP_HURU2
    CreateEmitterEx 0, 2, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BParabolic 2, 0, 0, 0, 18, 64
    Delay 2
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 2, 0, 0, 0
    PlaySoundEffectC SEQ_SE_DP_HURU2
    CreateEmitterEx 0, 3, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BParabolic 3, 0, 0, 0, 18, 64
    Delay 2
    CamTplPushImpact
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 12, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    PlaySoundEffectC SEQ_SE_DP_HURU2
    CreateEmitterEx 0, 4, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BParabolic 4, 0, 0, 0, 18, 64
    PlayDelayedSoundEffectR SEQ_SE_DP_W120, 10
    PlayDelayedSoundEffectR SEQ_SE_DP_W120, 20
    PlayDelayedSoundEffectR SEQ_SE_DP_W120, 30
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
