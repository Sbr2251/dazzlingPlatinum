#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, magnet_bomb_spa
    CamTplPushOpen
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 2, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    PlaySoundEffectR SEQ_SE_DP_290
    Delay 20
    PlaySoundEffectR SEQ_SE_DP_W443B
    Delay 2
    PlaySoundEffectR SEQ_SE_DP_W443B
    Delay 3
    PlaySoundEffectR SEQ_SE_DP_W443B
    Delay 2
    PlaySoundEffectR SEQ_SE_DP_W443B
    Delay 3
    PlaySoundEffectR SEQ_SE_DP_W443B
    Delay 5
    PlaySoundEffectR SEQ_SE_DP_W443B
    Delay 2
    PlaySoundEffectR SEQ_SE_DP_W443B
    Delay 3
    CamTplPushImpact
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 8, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    PlayDelayedSoundEffectR SEQ_SE_DP_161, 5
    PlayDelayedSoundEffectR SEQ_SE_DP_161, 15
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
