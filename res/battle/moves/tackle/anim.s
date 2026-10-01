#include "macros/btlanimcmd.inc"

// Gen 5 camera (moves.md, "Per-move camera"): a push in on the attacker for the wind-up,
// a cut to the target as it lunges, a punch on the hit, then home.
L_0:
    LoadParticleResource 0, tackle_spa
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 85, 6, 0, 8
    Delay 8
    PlaySoundEffectR SEQ_SE_DP_050
    StageCameraMove STAGE_CAMERA_FOCUS_DEFENDER, 85, -6, 0, 6
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
    StageCameraWait
    End
