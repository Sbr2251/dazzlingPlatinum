#include "macros/btlanimcmd.inc"

// Gen 5 camera (moves.md, "Per-move camera"): a push in on the attacker for the wind-up,
// a cut to the target as it lunges, a punch on the hit, then home. A mon on the player's side
// stands nearer the camera than the home focus, so its close-ups use 48% instead of 85%.
// Tackle keeps the healthbars in the classic look; on the stage they would cover the close-up,
// so they hide until the camera is halfway home.
L_0:
    LoadParticleResource 0, tackle_spa
    StageHealthbars FALSE
    JumpIfBattlerSide BATTLER_ROLE_ATTACKER, L_1, L_2
L_1:
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 48, 6, 0, 8
    Jump L_3
L_2:
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 85, 6, 0, 8
L_3:
    Delay 8
    PlaySoundEffectR SEQ_SE_DP_050
    JumpIfBattlerSide BATTLER_ROLE_DEFENDER, L_4, L_5
L_4:
    StageCameraMove STAGE_CAMERA_FOCUS_DEFENDER, 48, -6, 0, 6
    Jump L_6
L_5:
    StageCameraMove STAGE_CAMERA_FOCUS_DEFENDER, 85, -6, 0, 6
L_6:
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, 14, -8, 2
    WaitForAnimTasks
    StageCameraShake 2, 6
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, -14, 8, 2
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    StageCameraHome 12
    Delay 6
    StageHealthbars TRUE
    StageCameraWait
    End
