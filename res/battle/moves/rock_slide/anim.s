#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "wide" (moves.md, "Templates"): a pull-back over the whole field.
L_0:
    LoadParticleResource 0, rock_slide_spa
    CamTplWideOpen
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER_SIDE
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER_SIDE
    CreateEmitter 0, 2, EMITTER_CB_SET_POS_TO_DEFENDER_SIDE
    Delay 10
    PlayLoopedSoundEffectR SEQ_SE_DP_W088, 1, 20
    Delay 5
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 10, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_Shake 2, 0, 1, 10, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER_PARTNER
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
