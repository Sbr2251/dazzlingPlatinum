#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "contact" (moves.md, "Templates"): the attacker for the wind-up, then a cut to the defender, a punch on the hit.
L_0:
    LoadParticleResource 0, false_swipe_spa
    CamTplContactOpen
    PlaySoundEffectR SEQ_SE_DP_W104
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Delay 3
    PlaySoundEffectR SEQ_SE_DP_BRADE
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
