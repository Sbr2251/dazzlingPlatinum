#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "wide" (moves.md, "Templates"): a pull-back over the whole field.
L_0:
    LoadParticleResource 0, air_cutter_spa
    CamTplWideOpen
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER_SIDE
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER_SIDE
    Delay 10
    PlayLoopedSoundEffectC SEQ_SE_DP_W104, 2, 6
    Delay 5
    CamTplImpact 2, 6
    Func_Shake 0, 2, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_Shake 0, 2, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER_PARTNER
    PlaySoundEffectR SEQ_SE_DP_W015
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
