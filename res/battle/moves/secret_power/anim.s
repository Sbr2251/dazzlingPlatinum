#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "contact" (moves.md, "Templates"): the attacker for the wind-up, then a cut to the defender, a punch on the hit.
L_0:
    LoadParticleResource 0, hit_1_spa
    CamTplContactOpen
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    PlaySoundEffectR SEQ_SE_DP_BASI
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
