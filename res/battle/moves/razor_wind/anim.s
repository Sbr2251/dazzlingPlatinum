#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "wide" (moves.md, "Templates"): a pull-back over the whole field.
L_0:
    CamTplWideOpen
    BtlAnimCmd_013 L_1, L_2
    CamTplClose
    End

L_1:
    LoadParticleResource 0, razor_wind_spa
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    Delay 10
    PlaySoundEffectL SEQ_SE_DP_060
    Delay 10
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End

L_2:
    LoadParticleResource 0, razor_wind_spa
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER_SIDE
    PlayDelayedSoundEffectR SEQ_SE_DP_146, 5
    Delay 10
    CamTplImpact 3, 8
    Func_Shake 3, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_Shake 3, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER_PARTNER
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
