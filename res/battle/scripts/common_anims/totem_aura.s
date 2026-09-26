#include "macros/btlanimcmd.inc"

.data

// Totem aura: the Totem flashes orange-gold as a ring of flames bursts out of it.
// The flames that keep burning around it afterwards come from src/battle/totem_aura.c.
L_0:
    LoadParticleResource 0, 485 // totem_aura_spa
    // The stage camera pushes in on the Totem, shakes at the flare and eases home
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 72, 0, -4, 16
    Delay 16
    StageCameraShake 3, 10
    PlayPannedSoundEffect SEQ_SE_DP_W082, BATTLE_SOUND_PAN_RIGHT
    CreateEmitter 0, 3, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_FadeBattlerSprite BATTLE_ANIM_ATTACKER, 1, 2, 0x023F, 12, 8
    Func_Shake 1, 0, 1, 6, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    WaitForAnimTasks
    StageCameraHome 16
    WaitForAllEmitters
    UnloadParticleSystem 0
    StageCameraWait
    End
