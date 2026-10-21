#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "twoshot" (moves.md, "Templates"): both mons for the whole move, a punch on the hit.
L_0:
    LoadParticleResource 0, slam_spa
    CamTplTwoShotOpen
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_DEFENDER
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, 14, 4, 2
    Delay 1
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_DEFENDER, -14, -4, 2
    WaitForAnimTasks
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, -14, -4, 2
    Func_MoveBattler BATTLE_ANIM_BATTLER_SPRITE_DEFENDER, 14, 4, 4
    PlaySoundEffectR SEQ_SE_DP_W025B
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
