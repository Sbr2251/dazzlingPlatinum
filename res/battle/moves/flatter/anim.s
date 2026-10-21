#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, flatter_spa
    CamTplPushOpen
    PlaySoundEffectC SEQ_SE_DP_W227B
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    JumpIfBattlerSide BATTLER_ROLE_ATTACKER, L_1, L_2
    CamTplClose
    End

L_1:
    Delay 15
    BeginLoop 2
    PlaySoundEffectR SEQ_SE_DP_001
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_DEFENDER, 0, 8, 4
    Delay 4
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_DEFENDER, 0, -8, 4
    Delay 4
    EndLoop
    Delay 30
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End

L_2:
    Delay 15
    BeginLoop 2
    PlaySoundEffectR SEQ_SE_DP_001
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_DEFENDER, 0, -8, 4
    Delay 4
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_DEFENDER, 0, 8, 4
    Delay 4
    EndLoop
    Delay 30
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
