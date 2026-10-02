#include "macros/btlanimcmd.inc"

// Gen 5 camera (moves.md, "Per-move camera"): in on the attacker while the ball charges,
// out to frame both mons as it flies, a punch on the hit, then home.
// Each close-up picks its distance by the side of the mon it frames (moves.md, "Distance by side").
L_0:
    LoadParticleResource 0, shadow_ball_spa
    JumpIfBattlerSide BATTLER_ROLE_ATTACKER, L_1, L_2
L_1:
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 48, 8, 0, 10
    Jump L_3
L_2:
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 85, 8, 0, 10
L_3:
    CreateEmitter 0, 4, EMITTER_CB_NONE
    CreateEmitter 0, 0, EMITTER_CB_NONE
    CreateEmitter 0, 1, EMITTER_CB_NONE
    PlayLoopedSoundEffectC SEQ_SE_DP_W028, 2, 12
    Delay 55
    StageCameraMove STAGE_CAMERA_FOCUS_BETWEEN, 95, -4, 0, 8
    CreateEmitter 0, 2, EMITTER_CB_NONE
    Func_MoveEmitterA2BLinear 0, 0, 0, 0, 8, 255, EMITTER_ANIMATION_MODE_ATK_TO_DEF, SKIP_F(4)
    StageCameraShake 3, 8
    CreateEmitter 0, 3, EMITTER_CB_SET_POS_TO_DEFENDER
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 1, BATTLE_COLOR_DARK_PURPLE, 14, 0
    PlaySoundEffectR SEQ_SE_DP_480
    WaitForAllEmitters
    UnloadParticleSystem 0
    StageCameraHome 12
    StageCameraWait
    End
