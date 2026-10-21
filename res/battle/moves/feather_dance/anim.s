#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, feather_dance_spa
    CamTplPushOpen
    PlaySoundEffectR SEQ_SE_DP_W080
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 3, BATTLE_COLOR_GRAY, 14, 0
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
