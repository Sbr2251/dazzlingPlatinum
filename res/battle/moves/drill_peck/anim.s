#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "contact" (moves.md, "Templates"): the attacker for the wind-up, then a cut to the defender, a punch on the hit.
L_0:
    LoadParticleResource 0, peck_spa
    CamTplContactOpen
    PlaySoundEffectL SEQ_SE_DP_W029
    Func_DrillPeck
    Delay 18
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 12, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    CreateEmitter 0, 1, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, 0, 4128, 0
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, 0, 4128, 0
    PlaySoundEffectR SEQ_SE_DP_W030
    Delay 2
    CreateEmitter 0, 1, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, 4128, 4128, 0
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, 4128, 4128, 0
    PlaySoundEffectR SEQ_SE_DP_W030
    Delay 2
    CreateEmitter 0, 1, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, 4128, 0, 0
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, 4128, 0, 0
    PlaySoundEffectR SEQ_SE_DP_W030
    Delay 2
    CreateEmitter 0, 1, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, 4128, -4128, 0
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, 4128, -4128, 0
    PlaySoundEffectR SEQ_SE_DP_W030
    Delay 2
    CreateEmitter 0, 1, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, 0, -4128, 0
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, 0, -4128, 0
    PlaySoundEffectR SEQ_SE_DP_W030
    Delay 2
    CreateEmitter 0, 1, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, -4128, -4128, 0
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, -4128, -4128, 0
    PlaySoundEffectR SEQ_SE_DP_W030
    Delay 2
    CreateEmitter 0, 1, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, -4128, 0, 0
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, -4128, 0, 0
    PlaySoundEffectR SEQ_SE_DP_W030
    Delay 2
    CreateEmitter 0, 1, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, -4128, 4128, 0
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 5, 0, 0, 0
    SetExtraParams 1, -4128, 4128, 0
    PlaySoundEffectR SEQ_SE_DP_W030
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
