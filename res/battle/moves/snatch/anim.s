#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    CamTplPushOpen
    BtlAnimCmd_013 L_1, L_2
    CamTplClose
    End

L_1:
    PlaySoundEffectL SEQ_SE_DP_W036
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, -8, 4, 4
    WaitForAnimTasks
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, -8, -4, 4
    WaitForAnimTasks
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, 16, 0, 4
    WaitForAnimTasks
    CamTplClose
    End

L_2:
    Func_Snatch BATTLE_ANIM_ATTACKER
    PlaySoundEffectL SEQ_SE_DP_W054
    PlayDelayedSoundEffectR SEQ_SE_DP_210, 15
    PlayDelayedSoundEffectL SEQ_SE_DP_W054, 30
    Delay 20
    CamTplPushImpact
    CamTplImpact 2, 6
    Func_Shake 1, 0, 1, 2, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    WaitForAnimTasks
    CamTplClose
    End
