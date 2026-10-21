#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "twoshot" (moves.md, "Templates"): both mons for the whole move, a punch on the hit.
L_0:
    LoadParticleResource 0, rapid_spin_spa
    CamTplTwoShotOpen
    PlaySoundEffectL SEQ_SE_DP_207
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    CreateEmitter 0, 2, EMITTER_CB_SET_POS_TO_ATTACKER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 8, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    PlayLoopedSoundEffectR SEQ_SE_DP_143, 6, 3
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
