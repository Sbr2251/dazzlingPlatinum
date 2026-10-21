#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, payback_spa
    CamTplPushOpen
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 1, 0, 0, 0
    PlayLoopedSoundEffectL SEQ_SE_DP_W185, 4, 6
    CreateEmitter 0, 1, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 1, 0, 0, 0
    CreateEmitter 0, 2, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 1, 0, 0, 0
    CreateEmitter 0, 3, EMITTER_CB_SET_POS_TO_DEFENDER
    Delay 35
    PlaySoundEffectL SEQ_SE_DP_182
    Delay 40
    PlayLoopedSoundEffectR SEQ_SE_DP_030, 3, 4
    CamTplPushImpact
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 6, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
