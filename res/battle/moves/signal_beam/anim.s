#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "twoshot" (moves.md, "Templates"): both mons for the whole move, a punch on the hit.
L_0:
    LoadParticleResource 0, signal_beam_spa
    CamTplTwoShotOpen
    JumpIfFriendlyFire L_1
    JumpIfContest L_2
    CreateEmitterForMove 0, 0, 1, 2, 3, 4, 5, 18
    Func_Shake 1, 0, 0, 15, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    CamTplImpact 2, 6
    Func_Shake 1, 0, 0, 15, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    PlayLoopedSoundEffectC SEQ_SE_DP_W062, 6, 2
    BeginLoop 3
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 1, BATTLE_COLOR_RED, 8, 
    Delay 8
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 1, BATTLE_COLOR_LIGHT_GREEN, 8, 
    Delay 8
    EndLoop
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End

L_1:
    CreateEmitterForFriendlyFire 0, 7, 8, 7, 8, 3
    Func_Shake 1, 0, 0, 15, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    CamTplImpact 2, 6
    Func_Shake 1, 0, 0, 15, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    PlayLoopedSoundEffectC SEQ_SE_DP_W062, 6, 2
    BeginLoop 3
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 1, BATTLE_COLOR_RED, 8, 
    Delay 8
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 1, BATTLE_COLOR_LIGHT_GREEN, 8, 
    Delay 8
    EndLoop
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End

L_2:
    CreateEmitter 0, 6, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_Shake 1, 0, 0, 15, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    CamTplImpact 2, 6
    Func_Shake 1, 0, 0, 15, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    PlayLoopedSoundEffectC SEQ_SE_DP_W062, 6, 2
    BeginLoop 3
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 1, BATTLE_COLOR_RED, 8, 
    Delay 8
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 1, BATTLE_COLOR_LIGHT_GREEN, 8, 
    Delay 8
    EndLoop
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
