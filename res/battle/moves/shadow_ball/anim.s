#include "macros/btlanimcmd.inc"

// Gen 5 camera (moves.md, "Per-move camera"): the camera frames both mons while the ball charges and
// flies, a punch on the hit, then home.
// bw2vis:camera-core (BUG 4): the charge forms between the mons, off the attacker, so an attacker close-up
// pushed it to the top-right edge of the frame (the particles follow one similarity, moves.md). Framing the
// pair (BETWEEN) keeps it near the middle in both directions. BW2's curve: a constant-speed slide with a
// half-speed tail.
L_0:
    LoadParticleResource 0, shadow_ball_spa
    StageCameraMove STAGE_CAMERA_FOCUS_BETWEEN, 88, 0, 0, 10 | STAGE_CAMERA_BRAKE(7)
    CreateEmitter 0, 4, EMITTER_CB_NONE
    CreateEmitter 0, 0, EMITTER_CB_NONE
    CreateEmitter 0, 1, EMITTER_CB_NONE
    PlayLoopedSoundEffectC SEQ_SE_DP_W028, 2, 12
    Delay 55
    StageCameraMove STAGE_CAMERA_FOCUS_BETWEEN, 96, 0, 0, 8
    CreateEmitter 0, 2, EMITTER_CB_NONE
    Func_MoveEmitterA2BLinear 0, 0, 0, 0, 8, 255, EMITTER_ANIMATION_MODE_ATK_TO_DEF, SKIP_F(4)
    StageCameraShake 3, 8
    CreateEmitter 0, 3, EMITTER_CB_SET_POS_TO_DEFENDER
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 1, BATTLE_COLOR_DARK_PURPLE, 14, 0
    PlaySoundEffectR SEQ_SE_DP_480
    WaitForAllEmitters
    UnloadParticleSystem 0
    StageCameraHome 12 | STAGE_CAMERA_BRAKE(9)
    StageCameraWait
    End
