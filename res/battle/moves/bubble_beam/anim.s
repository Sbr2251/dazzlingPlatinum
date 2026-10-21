#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "twoshot" (moves.md, "Templates"): both mons for the whole move, a punch on the hit.
L_0:
    LoadParticleResource 0, bubble_beam_spa
    CamTplTwoShotOpen
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 6, 1, 4096, 0
    SetExtraParams 4, 0, 2, 5, 0
    PlayLoopedSoundEffectC SEQ_SE_DP_AWA, 4, 8
    BeginLoop 2
    PlayLoopedSoundEffectR SEQ_SE_DP_W145, 2, 2
    Func_MoveBattlerX2 8, 8, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Delay 8
    Func_MoveBattlerX2 16, -16, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Delay 16
    Func_MoveBattlerX2 8, 8, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Delay 8
    EndLoop
    PlayLoopedSoundEffectR SEQ_SE_DP_W202B, 4, 6
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
