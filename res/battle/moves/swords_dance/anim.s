#include "macros/btlanimcmd.inc"

// Gen 5 camera (moves.md, "Per-move camera"): in on the attacker, then a slow orbit round it
// while the swords circle, then home.
L_0:
    LoadParticleResource 0, swords_dance_spa
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 82, -12, 2, 8
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    PlaySoundEffectL SEQ_SE_DP_SHUSHU
    Delay 8
    StageCameraOrbit 24, 30
    WaitForAllEmitters
    UnloadParticleSystem 0
    StageCameraHome 12
    StageCameraWait
    End
