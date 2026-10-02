#include "macros/btlanimcmd.inc"

// Gen 5 camera (moves.md, "Per-move camera"): a short push in on the attacker, a cut to the
// target for the slashes, a punch on the hit, then home.
// Each close-up picks its distance by the side of the mon it frames (moves.md, "Distance by side").
L_0:
    LoadParticleResource 0, x_scissor_spa
    JumpIfBattlerSide BATTLER_ROLE_ATTACKER, L_1, L_2
L_1:
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 48, 6, 0, 8
    Jump L_3
L_2:
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 85, 6, 0, 8
L_3:
    Delay 8
    JumpIfBattlerSide BATTLER_ROLE_DEFENDER, L_4, L_5
L_4:
    StageCameraMove STAGE_CAMERA_FOCUS_DEFENDER, 48, -8, 0, 6
    Jump L_6
L_5:
    StageCameraMove STAGE_CAMERA_FOCUS_DEFENDER, 82, -8, 0, 6
L_6:
    PlaySoundEffectR SEQ_SE_DP_W015
    CreateEmitter 0, 2, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 2, 0, 0, 0
    CreateEmitter 0, 3, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 2, 0, 0, 0
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 2, 0, 0, 0
    CreateEmitter 0, 1, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 2, 0, 0, 0
    Delay 5
    StageCameraShake 2, 6
    PlaySoundEffectR SEQ_SE_DP_208
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAllEmitters
    UnloadParticleSystem 0
    StageCameraHome 12
    StageCameraWait
    End
