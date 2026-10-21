#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "contact" (moves.md, "Templates"): the attacker for the wind-up, then a cut to the defender, a punch on the hit.
L_0:
    LoadParticleResource 0, vine_whip_spa
    CamTplContactOpen
    Func_MoveBattlerX2 3, 24, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    WaitForAnimTasks
    Func_MoveBattlerX2 3, -24, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 2, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    PlaySoundEffectR SEQ_SE_DP_MUCHI
    Delay 5
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    PlaySoundEffectR SEQ_SE_DP_PASA2
    WaitForAllEmitters
    UnloadParticleSystem 0
    WaitForAnimTasks
    CamTplClose
    End
