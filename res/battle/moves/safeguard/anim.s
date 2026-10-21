#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "self" (moves.md, "Templates"): a close shot of the attacker with a slow orbit.
L_0:
    LoadParticleResource 0, safeguard_spa
    CamTplSelfOpen
    PlayLoopedSoundEffectL SEQ_SE_DP_W208, 4, 4
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_ATTACKER_SIDE
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER_SIDE
    Delay 15
    Func_FadeBattlerSprite BATTLE_ANIM_ATTACKER, 0, 1, BATTLE_COLOR_WHITE, 12
    Func_FadeBattlerSprite BATTLE_ANIM_ATTACKER_PARTNER, 0, 1, BATTLE_COLOR_WHITE, 12
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
