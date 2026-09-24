#include "macros/btlanimcmd.inc"

.data

// Totem aura: the Totem glows orange-gold while gold streaks (Focus Energy) and
// orange flames (Fire Spin) rise around it
L_0:
    LoadParticleResource 0, 142 // focus_energy_spa
    LoadParticleResource 1, 113 // fire_spin_spa
    PlayPannedSoundEffect SEQ_SE_DP_W082, BATTLE_SOUND_PAN_RIGHT
    CreateEmitter 1, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    CreateEmitter 0, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    CreateEmitter 0, 1, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_FadeBattlerSprite BATTLE_ANIM_ATTACKER, 1, 2, 0x023F, 12, 8
    Func_Shake 1, 0, 1, 6, BATTLE_ANIM_BATTLER_SPRITE_ATTACKER
    WaitForAnimTasks
    WaitForAllEmitters
    UnloadParticleSystem 0
    UnloadParticleSystem 1
    End
