#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "self" (moves.md, "Templates"): a close shot of the attacker with a slow orbit.
L_0:
    LoadParticleResource 0, endure_spa
    CamTplSelfOpen
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_FadeBattlerSprite BATTLE_ANIM_ATTACKER, 0, 2, BATTLE_COLOR_RED, 10, 0
    PlayLoopedSoundEffectL SEQ_SE_DP_W082, 3, 4
    WaitForAllEmitters
    UnloadParticleSystem 0
    WaitForAnimTasks
    CamTplClose
    End
