#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "self" (moves.md, "Templates"): a close shot of the attacker with a slow orbit.
L_0:
    LoadParticleResource 0, dragon_dance_spa
    CamTplSelfOpen
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_FadeBattlerSprite BATTLE_ANIM_ATTACKER, 0, 3, BATTLE_COLOR_RED, 10, 10
    Func_Shake 2, 0, 1, 16, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    PlayLoopedSoundEffectL SEQ_SE_DP_W379, 4, 5
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
