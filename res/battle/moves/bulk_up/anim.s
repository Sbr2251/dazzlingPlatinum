#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "self" (moves.md, "Templates"): a close shot of the attacker with a slow orbit.
L_0:
    CamTplSelfOpen
    PlaySoundEffectL SEQ_SE_DP_W207
    PlayDelayedSoundEffectL SEQ_SE_DP_W207D, 20
    Func_BulkUp 0
    WaitForAnimTasks
    CamTplClose
    End
