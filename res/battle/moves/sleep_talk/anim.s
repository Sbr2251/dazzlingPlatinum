#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, sleep_talk_spa
    CamTplPushOpen
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 1, 1, 0, 0
    CreateEmitter 0, 1, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 1, 1, 0, 0
    PlayLoopedSoundEffectL SEQ_SE_DP_W173B, 8, 2
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
