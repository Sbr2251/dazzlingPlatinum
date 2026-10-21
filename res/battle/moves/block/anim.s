#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, imprison_spa
    CamTplPushOpen
    PlaySoundEffectR SEQ_SE_DP_050
    CreateEmitter 0, 2, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 3, EMITTER_CB_SET_POS_TO_DEFENDER
    BeginLoop 1
    Delay 12
    PlaySoundEffectR SEQ_SE_DP_W030
    EndLoop
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
