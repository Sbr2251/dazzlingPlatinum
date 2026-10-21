#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "self" (moves.md, "Templates"): a close shot of the attacker with a slow orbit.
L_0:
    LoadParticleResource 0, conversion_spa
    CamTplSelfOpen
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    PlayLoopedSoundEffectL SEQ_SE_DP_W112, 2, 4
    PlayDelayedSoundEffectL SEQ_SE_DP_351, 42
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
