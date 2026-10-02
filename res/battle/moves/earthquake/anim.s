#include "macros/btlanimcmd.inc"

// Gen 5 camera (moves.md, "Per-move camera"): a low push toward the target frames the quake.
// The BG3 shake is mirrored onto the stage camera (moves.md, category A) on top of the pose.
// Each close-up picks its distance by the side of the mon it frames (moves.md, "Distance by side").
L_0:
    LoadParticleResource 0, earthquake_spa
    JumpIfBattlerSide BATTLER_ROLE_DEFENDER, L_1, L_2
L_1:
    StageCameraMove STAGE_CAMERA_FOCUS_DEFENDER, 48, -8, -3, 10
    Jump L_3
L_2:
    StageCameraMove STAGE_CAMERA_FOCUS_DEFENDER, 88, -8, -3, 10
L_3:
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
