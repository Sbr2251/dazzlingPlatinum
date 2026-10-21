#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "contact" (moves.md, "Templates"): the attacker for the wind-up, then a cut to the defender, a punch on the hit.
L_0:
    LoadParticleResource 0, peck_spa
    CamTplContactOpen
    Func_RotateMon DEG_TO_IDX(360), DEG_TO_IDX(350), 2
    Delay 2
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    PlaySoundEffectR SEQ_SE_DP_W030
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    WaitForAnimTasks
    CamTplClose
    End
