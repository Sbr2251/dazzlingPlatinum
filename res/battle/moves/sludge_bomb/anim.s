#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, sludge_bomb_spa
    CamTplPushOpen
    CreateEmitterEx 0, 1, 2, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BParabolic 1, 0, 0, 0, 14, 64
    PlayLoopedSoundEffectC SEQ_SE_DP_W145B, 2, 4
    Delay 10
    PlayLoopedSoundEffectR SEQ_SE_DP_W092D, 2, 12
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    Delay 5
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 2, BATTLE_COLOR_PURPLE, 14, 0
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
