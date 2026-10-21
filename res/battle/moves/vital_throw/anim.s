#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "twoshot" (moves.md, "Templates"): both mons for the whole move, a punch on the hit.
L_0:
    LoadParticleResource 0, vital_throw_spa
    CamTplTwoShotOpen
    Func_VitalThrow
    PlayLoopedSoundEffectL SEQ_SE_DP_W233, 22, 3
    Delay 66
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    PlaySoundEffectR SEQ_SE_DP_030
    WaitForAllEmitters
    UnloadParticleSystem 0
    WaitForAnimTasks
    CamTplClose
    End
