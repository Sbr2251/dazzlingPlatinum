#include "macros/btlanimcmd.inc"

L_0:
    LoadParticleResource 0, moonblast_spa
    SetVar BATTLE_ANIM_VAR_BG_FADE_TYPE, 0
    SetVar BATTLE_ANIM_VAR_BG_MOVE_STEP_X, 0
    SetVar BATTLE_ANIM_VAR_BG_MOVE_STEP_Y, 1
    SwitchBg 42, BATTLE_BG_SWITCH_MODE_FADE | BATTLE_BG_SWITCH_FLAG_MOVE
    WaitForBgSwitch
    // Blender-rendered moon (tools/moonblast_sprite) rises above the user:
    // grows in, pulses for ~36 frames, flares, then collapses as it fires.
    // The sprite animation is 60 frames long.
    InitSpriteManager 0, 1, 1, 1, 1, 1, 0, 0
    LoadCharResObj 0, moonblast_NCGR_lz
    LoadPlttRes 0, moonblast_NCLR, 1
    LoadCellResObj 0, moonblast_cell_NCER_lz
    LoadAnimResObj 0, moonblast_anim_NANR_lz
    PlaySoundEffectL SEQ_SE_DP_W236
    AddSpriteWithFunc 0, 33, moonblast_NCGR_lz, moonblast_NCLR, moonblast_cell_NCER_lz, moonblast_anim_NANR_lz, 0, 0, 0, -36
    Delay 14
    PlayLoopedSoundEffectL SEQ_SE_DP_W082, 3, 10
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    CreateEmitter 0, 2, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_FadeBattlerSprite BATTLE_ANIM_ATTACKER, 0, 1, BATTLE_COLOR_LIGHT_RED, 10, 30
    Delay 42
    PlayLoopedSoundEffectR SEQ_SE_DP_161, 2, 2
    CreateEmitter 0, 3, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BLinear 0, 0, 0, 0, 10, 64
    Delay 10
    PlaySoundEffectR SEQ_SE_DP_W461
    CreateEmitter 0, 5, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 4, EMITTER_CB_SET_POS_TO_DEFENDER
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 1, BATTLE_COLOR_LIGHT_RED, 14, 8
    Func_Shake 3, 0, 1, 4, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAllEmitters
    UnloadParticleSystem 0
    WaitForAnimTasks
    FreeSpriteManager 0
    SetVar BATTLE_ANIM_VAR_BG_FADE_TYPE, 0
    SetVar BATTLE_ANIM_VAR_BG_MOVE_STEP_X, 0
    SetVar BATTLE_ANIM_VAR_BG_MOVE_STEP_Y, 1
    SetVar BATTLE_ANIM_VAR_BG_FADE_TYPE, 1
    RestoreBg 42, BATTLE_BG_SWITCH_MODE_FADE | BATTLE_BG_SWITCH_FLAG_STOP
    WaitForBgSwitch
    End
