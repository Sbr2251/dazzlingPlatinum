#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "wide" (moves.md, "Templates"): a pull-back over the whole field.
L_0:
    CamTplWideOpen
    BeginLoop 2
    PlaySoundEffectL SEQ_SE_DP_112
    Func_RevolveBattler BATTLE_ANIM_ATTACKER, 1, 12
    WaitForAnimTasks
    EndLoop
    CamTplClose
    End
