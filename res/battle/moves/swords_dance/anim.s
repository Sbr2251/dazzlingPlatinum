#include "macros/btlanimcmd.inc"

// Gen 5 camera (moves.md, "Per-move camera"): in on the attacker, then a slow orbit round it
// while the swords circle, then home.
// Each close-up picks its distance by the side of the mon it frames (moves.md, "Distance by side").
// Swords Dance keeps the healthbars in the classic look; on the stage they would cover the
// close-up, so they hide until the camera is halfway home.
L_0:
    LoadParticleResource 0, swords_dance_spa
    StageHealthbars FALSE
    JumpIfBattlerSide BATTLER_ROLE_ATTACKER, L_1, L_2
L_1:
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 48, -12, 2, 8
    Jump L_3
L_2:
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 82, -12, 2, 8
L_3:
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    PlaySoundEffectL SEQ_SE_DP_SHUSHU
    Delay 8
    StageCameraOrbit 24, 30
    WaitForAllEmitters
    UnloadParticleSystem 0
    StageCameraHome 12
    Delay 6
    StageHealthbars TRUE
    StageCameraWait
    End
