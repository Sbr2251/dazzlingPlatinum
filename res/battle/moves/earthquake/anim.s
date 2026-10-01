#include "macros/btlanimcmd.inc"

// Gen 5 camera (moves.md, "Per-move camera"): a low push toward the target frames the quake.
// The BG3 shake is mirrored onto the stage camera (moves.md, category A) on top of the pose.
L_0:
    LoadParticleResource 0, earthquake_spa
    StageCameraMove STAGE_CAMERA_FOCUS_DEFENDER, 88, -8, -3, 10
    Func_Earthquake 0
    Delay 2
    PlaySoundEffectC SEQ_SE_DP_W089
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    StageCameraHome 12
    StageCameraWait
    End
