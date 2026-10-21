#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "push" (moves.md, "Templates"): both mons while it flies, then a push-in on the defender at the hit.
L_0:
    LoadParticleResource 0, psybeam_spa
    CamTplPushOpen
    PlayMovingSoundEffectAtkDef SEQ_SE_DP_W060C, BATTLE_SOUND_PAN_LEFT, BATTLE_SOUND_PAN_RIGHT, 4, 2
    CreateEmitter 0, 0, EMITTER_CB_GENERIC
    SetExtraParams 0, 2, 14, 8, 0, 0
    Func_FadeBattlerSprite BATTLE_ANIM_DEFENDER, 0, 1, BATTLE_COLOR_PURPLE, 8, 10
    BeginLoop 2
    Func_MoveBattlerX2 8, 8, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Delay 8
    Func_MoveBattlerX2 16, -16, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Delay 16
    Func_MoveBattlerX2 8, 8, BATTLE_ANIM_BATTLER_SPRITE_DEFENDER
    Delay 8
    EndLoop
    WaitForAllEmitters
    UnloadParticleSystem 0
    CamTplClose
    End
