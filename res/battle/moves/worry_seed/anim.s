#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, worry_seed_spa
    CamTplPushOpen
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    Func_MoveEmitterA2BParabolic 0, 0, 0, 0, 19, 64
    PlayMovingSoundEffectAtkDef SEQ_SE_DP_001, BATTLE_SOUND_PAN_LEFT, BATTLE_SOUND_PAN_RIGHT, 4, 2
    Delay 15
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 2, 0, 0, 0
    CamTplPushImpact
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    PlaySoundEffectR SEQ_SE_DP_112
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
