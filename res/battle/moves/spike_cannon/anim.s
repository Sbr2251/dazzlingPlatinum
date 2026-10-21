#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "twoshot" (moves.md, "Templates"): both mons for the whole move, a punch on the hit.
L_0:
    LoadParticleResource 0, spike_cannon_spa
    CamTplTwoShotOpen
    Func_MoveBattlerX2 2, -8, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    WaitForAnimTasks
    CreateEmitter 0, 1, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 6, 1, 16, 0
    SetExtraParams 3, 0, 0, 0, 0
    PlayLoopedSoundEffectR SEQ_SE_DP_W013, 2, 8
    Func_MoveBattlerX2 2, 8, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    Delay 10
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 6, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
