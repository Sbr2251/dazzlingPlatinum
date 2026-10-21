#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, sleep_powder_spa
    CamTplPushOpen
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    PlayLoopedSoundEffectR SEQ_SE_DP_W077B, 4, 6
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 2, BATTLE_COLOR_LIGHT_GREEN, 10, 10
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
