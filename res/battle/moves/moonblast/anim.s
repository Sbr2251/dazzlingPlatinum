#include "macros/btlanimcmd.inc"

L_0:
    LoadParticleResource 0, flash_cannon_spa
    SetVar BATTLE_ANIM_VAR_BG_FADE_TYPE, 0
    SetVar BATTLE_ANIM_VAR_BG_MOVE_STEP_X, 0
    SetVar BATTLE_ANIM_VAR_BG_MOVE_STEP_Y, 1
    SwitchBg 42, BATTLE_BG_SWITCH_MODE_FADE | BATTLE_BG_SWITCH_FLAG_MOVE
    WaitForBgSwitch
    PlayLoopedSoundEffectL SEQ_SE_DP_W082, 3, 10
    CreateEmitter 0, 5, EMITTER_CB_GENERIC
    SetExtraParams 0, 1, 2, 0, 0, 0
    CreateEmitter 0, 3, EMITTER_CB_GENERIC
    SetExtraParams 0, 1, 2, 0, 0, 0
    CreateEmitter 0, 4, EMITTER_CB_GENERIC
    SetExtraParams 0, 1, 2, 0, 0, 0
    Delay 60
    PlayLoopedSoundEffectR SEQ_SE_DP_161, 2, 2
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BLinear 0, 0, 0, 0, 10, 64
    Delay 10
    PlaySoundEffectR SEQ_SE_DP_400
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 1, BATTLE_COLOR_LIGHT_RED, 14, 0
    WaitForAllEmitters
    UnloadParticleSystem 0
    WaitForAnimTasks
    SetVar BATTLE_ANIM_VAR_BG_FADE_TYPE, 0
    SetVar BATTLE_ANIM_VAR_BG_MOVE_STEP_X, 0
    SetVar BATTLE_ANIM_VAR_BG_MOVE_STEP_Y, 1
    SetVar BATTLE_ANIM_VAR_BG_FADE_TYPE, 1
    RestoreBg 42, BATTLE_BG_SWITCH_MODE_FADE | BATTLE_BG_SWITCH_FLAG_STOP
    WaitForBgSwitch
    End
