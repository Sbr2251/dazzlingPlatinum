#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "wide" (moves.md, "Templates"): a pull-back over the whole field.
L_0:
    LoadParticleResource 0, sandstorm_spa
    SetParticleScreenSpace 0 // camera template: full-screen
    CamTplWideOpen
    CreateEmitter 0, 0, EMITTER_CB_NONE
    CreateEmitter 0, 1, EMITTER_CB_NONE
    PlaySoundEffectC SEQ_SE_DP_W201
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
