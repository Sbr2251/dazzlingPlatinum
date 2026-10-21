#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, spit_up_spa
    CamTplPushOpen
    PlaySoundEffectL SEQ_SE_DP_W036
    Func_ShakeAndScaleAttacker 70, 120, 10, 5, 15
    Delay 25
    PlayLoopedSoundEffectL SEQ_SE_DP_W255E, 5, 2
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    WaitForAnimTasks
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    Delay 15
    PlayLoopedSoundEffectR SEQ_SE_DP_W025B, 2, 3
    CamTplPushImpact
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 4, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
