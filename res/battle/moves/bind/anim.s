#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "contact" (moves.md, "Templates"): the attacker for the wind-up, then a cut to the defender, a punch on the hit.
L_0:
    LoadParticleResource 0, bind_spa
    CamTplContactOpen
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    BeginLoop 2
    Func_MoveBattlerX2 3, 24, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    WaitForAnimTasks
    Func_MoveBattlerX2 3, -24, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    Delay 1
    Func_ScaleBattlerSprite BATTLE_ANIM_BATTLER_SPRITE_DEFENDER, 100, 70, 100, 100, 100, CYCLES(1), SCALE_F(5) | RESTORE_F(5)
    WaitForAnimTasks
    PlaySoundEffectR SEQ_SE_DP_W020B
    EndLoop
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
