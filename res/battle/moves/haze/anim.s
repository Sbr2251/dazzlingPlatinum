#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "wide" (moves.md, "Templates"): a pull-back over the whole field.
L_0:
    LoadParticleResource 0, haze_spa
    CamTplWideOpen
    CreateEmitter 0, 0, EMITTER_CB_NONE
    PlaySoundEffectC SEQ_SE_DP_W114
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
