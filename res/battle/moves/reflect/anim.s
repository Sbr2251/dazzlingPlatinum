#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "self" (moves.md, "Templates"): a close shot of the attacker with a slow orbit.
L_0:
    LoadParticleResource 0, reflect_spa
    CamTplSelfOpen
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_ATTACKER_SIDE
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER_SIDE
    PlaySoundEffectL SEQ_SE_DP_W115
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
