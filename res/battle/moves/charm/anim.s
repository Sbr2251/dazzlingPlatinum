#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, charm_spa
    CamTplPushOpen
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_PlayfulHops
    BeginLoop 3
    PlaySoundEffectL SEQ_SE_DP_W204
    Delay 8
    EndLoop
    PlaySoundEffectL SEQ_SE_DP_W204
    WaitForAllEmitters
    UnloadParticleSystem 0
    WaitForAnimTasks
    CamTplClose
    End
