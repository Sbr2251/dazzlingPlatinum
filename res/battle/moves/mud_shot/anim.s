#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "twoshot" (moves.md, "Templates"): both mons for the whole move, a punch on the hit.
L_0:
    LoadParticleResource 0, mud_shot_spa
    CamTplTwoShotOpen
    JumpIfFriendlyFire L_1
    JumpIfContest L_2
    PlayMovingSoundEffectAtkDef SEQ_SE_DP_W250, BATTLE_SOUND_PAN_LEFT, BATTLE_SOUND_PAN_RIGHT, 4, 2
    CreateEmitterForMove 0, 0, 3, 6, 7, 8, 9, 18
    Delay 10
    CreateEmitter 0, 14, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 6, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 2, BATTLE_COLOR_DARK_RED1, 14, 0
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End

L_1:
    PlayMovingSoundEffectAtkDef SEQ_SE_DP_W250, BATTLE_SOUND_PAN_LEFT, BATTLE_SOUND_PAN_RIGHT, 4, 2
    CreateEmitterForFriendlyFire 0, 11, 12, 11, 12, 3
    Delay 10
    CreateEmitter 0, 14, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 6, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End

L_2:
    PlayMovingSoundEffectAtkDef SEQ_SE_DP_W250, BATTLE_SOUND_PAN_LEFT, BATTLE_SOUND_PAN_RIGHT, 4, 2
    CreateEmitter 0, 10, EMITTER_CB_GENERIC
    SetExtraParams 0, 1, 5, 0, 0, 0
    SetExtraParams 0, 11008, -8256, 0
    Delay 10
    CreateEmitter 0, 14, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 6, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
