#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, fling_spa
    CamTplPushOpen
    PlayMovingSoundEffectAtkDef SEQ_SE_DP_W374, BATTLE_SOUND_PAN_LEFT, BATTLE_SOUND_PAN_RIGHT, 4, 2
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BParabolic 0, 0, 0, 0, 14, 64
    Delay 13
    PlaySoundEffectR SEQ_SE_DP_186
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 2, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplPushImpact
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
