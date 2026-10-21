#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, flail_spa
    CamTplPushOpen
    PlayLoopedSoundEffectL SEQ_SE_DP_050, 3, 6
    Func_Flail FLAIL_MODE_ATTACKER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    WaitForAnimTasks
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    PlaySoundEffectR SEQ_SE_DP_W025B
    Func_Flail FLAIL_MODE_DEFENDER, 2, 0, 0, 5
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
