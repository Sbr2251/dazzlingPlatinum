#include "macros/btlanimcmd.inc"

.data

// Totem aura flare-up (~3.5 s at 60 fps, ~210 script frames). The persistent aura that keeps
// burning afterwards comes from src/battle/totem_aura.c, which also drives the dim/vignette/
// shockwave fallback FX and the A/B skip on the same frame count; keep the Delays here in
// step with TOTEM_FLARE_FRAMES there.
//  0.0-0.4 s  battle opens dim, Totem silhouette darkens, camera pushes in
//  0.4-1.0 s  ground-glow ring ignites under the Totem (emitter 0)
//  1.0-2.2 s  aura flames spiral up (emitter 1), lightning crackles on the outline (emitter 2)
//  2.2-2.5 s  burst: bass pulse, heavy shake, white-hot flare (emitter 3), silhouette flashes
//  2.5-3.5 s  settle: camera eases home over the stat-boost message that follows
L_0:
    LoadParticleResource 0, 485 // totem_aura_spa
    // The stage camera pushes in on the Totem and stays there through the aura message,
    // easing home at the first command menu (BattleStage_HoldCameraAfterScript).
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 72, 0, -4, 16
    Func_FadeBattlerSprite BATTLE_ANIM_ATTACKER, 1, 2, BATTLE_COLOR_BLACK, 12, 4
    Func_ScaleBattlerSprite BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, 100, 118, 100, 118, 100, 1, 327685
    Delay 20
    // Ground-glow ring ignites
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    PlayPannedSoundEffect SEQ_SE_DP_W082_sseq, BATTLE_SOUND_PAN_RIGHT
    Delay 36
    // Flames spiral up; crackles race along the outline
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    CreateEmitter 0, 2, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_FadeBattlerSprite BATTLE_ANIM_ATTACKER, 1, 2, 0x023F, 12, 8
    Delay 60
    Func_Shake 1, 0, 1, 6, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    Delay 14
    // Burst: heavy bass pulse and shake, the one-shot flare blows out
    StageCameraShake 5, 14
    PlayPannedSoundEffect SEQ_SE_DP_W082B_sseq, BATTLE_SOUND_PAN_RIGHT
    CreateEmitter 0, 3, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_FadeBattlerSprite BATTLE_ANIM_ATTACKER, 1, 1, BATTLE_COLOR_WHITE, 14, 6
    Func_Shake 2, 1, 1, 8, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    Delay 20
    // Settle: sprite eases back, flames fall to the persistent aura's level
    // while the banner shows.
    // No WaitForAllEmitters: emitters 0-2 never expire, so unloading ends them.
    Func_ScaleBattlerSprite BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, 118, 100, 118, 100, 100, 1, 327685
    WaitForAnimTasks
    Delay 40
    UnloadParticleSystem 0
    StageCameraWait
    End
