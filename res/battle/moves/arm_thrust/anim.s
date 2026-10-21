#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "contact" (moves.md, "Templates"): the attacker for the wind-up, then a cut to the defender, a punch on the hit.
L_0:
    LoadParticleResource 0, arm_thrust_spa
    CamTplContactOpen
    JumpIfBattlerSide BATTLER_ROLE_ATTACKER, L_1, L_2
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End

L_1:
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    Delay 5
    PlayDelayedSoundEffectR SEQ_SE_DP_030, 3
    CreateEmitter 0, 3, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    Delay 10
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    CamTplClose
    End

L_2:
    CreateEmitter 0, 2, EMITTER_CB_SET_POS_TO_DEFENDER
    Delay 5
    PlayDelayedSoundEffectR SEQ_SE_DP_030, 3
    CreateEmitter 0, 3, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    Delay 10
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    CamTplClose
    End
