#include "macros/btlanimcmd.inc"

.data

// Totem aura flare-up (~3.5 s at 60 fps, ~210 script frames). The persistent aura in
// src/battle/totem_aura.c starts with this animation and provides the ground ring and
// spiralling flames (type-tinted, behind the sprite), so this script stays lean: it
// owns the silhouette, the camera and the single burst. Keep the Delays here in step
// with TOTEM_FLARE_FRAMES there.
//  0.0-0.4 s  battle opens dim, Totem silhouette darkens, camera pushes in
//  0.4-2.2 s  ring and spiral flames climb around the visible silhouette
//  2.2-2.5 s  burst: bass pulse, shake, one short white flash
//  2.5-3.5 s  settle: camera eases home over the stat-boost banner
L_0:
    LoadParticleResource 0, 485 // totem_aura_spa
    // The stage camera pushes in on the Totem and stays there through the aura message,
    // easing home at the first command menu (BattleStage_HoldCameraAfterScript).
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 72, 0, -4, 16
    Func_FadeBattlerSprite BATTLE_ANIM_ATTACKER, 1, 2, BATTLE_COLOR_BLACK, 12, 4
    Func_ScaleBattlerSprite BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, 100, 118, 100, 118, 100, 1, 327685
    Delay 20
    PlayPannedSoundEffect SEQ_SE_DP_W082_sseq, BATTLE_SOUND_PAN_RIGHT
    // The silhouette holds while the persistent aura's flames climb around it
    Delay 96
    Func_FadeBattlerSprite BATTLE_ANIM_ATTACKER, 1, 2, 0x023F, 8, 4
    Delay 14
    Func_Shake 1, 0, 1, 6, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    Delay 14
    // Burst: heavy bass pulse and shake, one short white flash
    StageCameraShake 5, 14
    PlayPannedSoundEffect SEQ_SE_DP_W082B_sseq, BATTLE_SOUND_PAN_RIGHT
    CreateEmitter 0, 3, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_FadeBattlerSprite BATTLE_ANIM_ATTACKER, 1, 1, BATTLE_COLOR_WHITE, 10, 2
    Func_Shake 2, 1, 1, 8, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    Delay 20
    // Settle: sprite eases back while the banner shows
    Func_ScaleBattlerSprite BATTLE_ANIM_BATTLER_SPRITE_ATTACKER, 118, 100, 118, 100, 100, 1, 327685
    WaitForAnimTasks
    Delay 40
    WaitForAllEmitters
    UnloadParticleSystem 0
    StageCameraWait
    End
