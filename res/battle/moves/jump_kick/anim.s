#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "twoshot" (moves.md, "Templates"): both mons for the whole move, a punch on the hit.
L_0:
    LoadParticleResource 0, jump_kick_spa
    CamTplTwoShotOpen
    Func_MoveBattlerX2 3, 24, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    CreateEmitter 0, 2, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 6, 1, 4096, 0
    SetExtraParams 3, 0, 0, 0, 0
    WaitForAnimTasks
    Func_MoveBattlerX2 3, -24, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    PlaySoundEffectR SEQ_SE_DP_131
    WaitForAnimTasks
    Delay 20
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    PlaySoundEffectR SEQ_SE_DP_030
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
