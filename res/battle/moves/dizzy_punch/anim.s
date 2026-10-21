#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "contact" (moves.md, "Templates"): the attacker for the wind-up, then a cut to the defender, a punch on the hit.
L_0:
    LoadParticleResource 0, dizzy_punch_spa
    CamTplContactOpen
    BeginLoop 2
    Delay 6
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, 24, 0, 3
    WaitForAnimTasks
    PlaySoundEffectR SEQ_SE_DP_W004
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 3, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, -24, 0, 3
    WaitForAnimTasks
    PlaySoundEffectR SEQ_SE_DP_W146
    PlayLoopedSoundEffectR SEQ_SE_DP_W146, 4, 4
    EndLoop
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
