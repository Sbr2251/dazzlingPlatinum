#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "self" (moves.md, "Templates"): a close shot of the attacker with a slow orbit.
L_0:
    CamTplSelfOpen
    Func_Growth
    PlaySoundEffectL SEQ_SE_DP_W036
    WaitForAnimTasks
    CamTplClose
    End
