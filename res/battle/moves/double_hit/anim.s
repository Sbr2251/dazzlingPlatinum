#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "twoshot" (moves.md, "Templates"): both mons for the whole move, a punch on the hit.
L_0:
    LoadParticleResource 0, double_hit_spa
    CamTplTwoShotOpen
    PlaySoundEffectR SEQ_SE_DP_030
    CreateEmitter 0, 2, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, 2752, 1376, 0
    CreateEmitter 0, 4, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, 2752, 1376, 0
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, 2752, 1376, 0
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Delay 15
    PlaySoundEffectR SEQ_SE_DP_030
    CreateEmitter 0, 3, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, -2752, 1376, 0
    CreateEmitter 0, 5, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, -2752, 1376, 0
    CreateEmitter 0, 1, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, -2752, 1376, 0
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
