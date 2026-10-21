#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "twoshot" (moves.md, "Templates"): both mons for the whole move, a punch on the hit.
L_0:
    LoadParticleResource 0, pain_split_spa
    CamTplTwoShotOpen
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    CamTplImpact 2, 6
    Func_Shake 2, 0, 1, 8, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Func_Shake 2, 0, 1, 8, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    PlayDelayedSoundEffectL SEQ_SE_DP_W025B, 1
    PlayDelayedSoundEffectR SEQ_SE_DP_W025B, 5
    PlayDelayedSoundEffectL SEQ_SE_DP_W025B, 10
    PlayDelayedSoundEffectR SEQ_SE_DP_W025B, 15
    PlayDelayedSoundEffectL SEQ_SE_DP_W025B, 20
    PlayDelayedSoundEffectR SEQ_SE_DP_W025B, 25
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
