#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "twoshot" (moves.md, "Templates"): both mons for the whole move, a punch on the hit.
L_0:
    LoadParticleResource 0, take_down_spa
    CamTplTwoShotOpen
    PlaySoundEffectL SEQ_SE_DP_W029
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, -16, 8, 4
    WaitForAnimTasks
    Delay 15
    PlaySoundEffectR SEQ_SE_DP_140
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, 32, -16, 4
    WaitForAnimTasks
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 2, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplImpact 3, 8
    Func_Shake 4, 0, 1, 4, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, -16, 8, 4
    WaitForAnimTasks
    CamTplClose
    End
