#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, bounce_spa
    CamTplPushOpen
    BtlAnimCmd_013 L_1, L_2
    CamTplClose
    End

L_1:
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    CreateEmitter 0, 3, EMITTER_CB_SET_POS_TO_ATTACKER
    Delay 8
    PlaySoundEffectL SEQ_SE_DP_W100
    Func_HideBattler BATTLE_ANIM_ATTACKER, TRUE
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End

L_2:
    CreateEmitter 0, 2, EMITTER_CB_SET_POS_TO_DEFENDER
    Delay 10
    PlaySoundEffectR SEQ_SE_DP_W029
    Delay 10
    PlaySoundEffectR SEQ_SE_DP_143
    CamTplPushImpact
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_HideBattler BATTLE_ANIM_ATTACKER, FALSE
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
