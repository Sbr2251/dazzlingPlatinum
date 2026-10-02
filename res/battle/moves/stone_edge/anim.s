#include "macros/btlanimcmd.inc"

// Gen 5 camera (moves.md, "Per-move camera"): a short push in on the attacker, a low shot of
// the target as the stones rise, a heavy punch as they strike, then home.
// Each close-up picks its distance by the side of the mon it frames (moves.md, "Distance by side").
L_0:
    LoadParticleResource 0, stone_edge_spa
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
    StageCameraMove STAGE_CAMERA_FOCUS_DEFENDER, 48, -8, -3, 10
    Jump L_6
L_5:
    StageCameraMove STAGE_CAMERA_FOCUS_DEFENDER, 85, -8, -3, 10
L_6:
    CreateEmitter 0, 2, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 3, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    PlayLoopedSoundEffectR SEQ_SE_DP_W088, 2, 4
    Delay 25
    StageCameraShake 4, 12
    Func_Shake 2, 0, 1, 6, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    PlaySoundEffectR SEQ_SE_DP_W082
    PlayLoopedSoundEffectR SEQ_SE_DP_W088, 6, 3
    WaitForAllEmitters
    UnloadParticleSystem 0
    StageCameraHome 12
    StageCameraWait
    End
