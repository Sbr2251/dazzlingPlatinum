#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "contact" (moves.md, "Templates"): the attacker for the wind-up, then a cut to the defender, a punch on the hit.
L_0:
    LoadParticleResource 0, lick_spa
    CamTplContactOpen
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    PlaySoundEffectR SEQ_SE_DP_W122
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 4, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
