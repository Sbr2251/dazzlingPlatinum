#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "wide" (moves.md, "Templates"): a pull-back over the whole field.
L_0:
    LoadParticleResource 0, bubble_spa
    LoadParticleResource 1, bubble_spa
    CamTplWideOpen
    JumpIfContest L_1
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 31, 24, 0, 4
    PlayLoopedSoundEffectC SEQ_SE_DP_W145, 2, 5
    Delay 10
    CreateEmitter 1, 1, EMITTER_CB_SET_POS_TO_DEFENDER_SIDE
    Delay 10
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER_PARTNER
    PlayLoopedSoundEffectR SEQ_SE_DP_W145C, 2, 2
    Delay 10
    WaitForAllEmitters
    UnloadParticleSystem 0
    UnloadParticleSystem 1
    CamTplClose
    End

L_1:
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 0, 28, 22, 0, 4
    PlayLoopedSoundEffectC SEQ_SE_DP_W145, 2, 5
    Delay 10
    CreateEmitter 1, 1, EMITTER_CB_SET_POS_TO_DEFENDER_SIDE
    Delay 10
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER_PARTNER
    PlayLoopedSoundEffectR SEQ_SE_DP_W145C, 2, 2
    Delay 10
    WaitForAllEmitters
    UnloadParticleSystem 0
    UnloadParticleSystem 1
    CamTplClose
    End
