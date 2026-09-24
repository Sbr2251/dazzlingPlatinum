#include "macros/btlanimcmd.inc"

.data

// Places a mega_evolution.spa emitter on the Pokemon, offset (in FX32 units) from its battle anim position
// towards the middle of its sprite: that position sits at the feet of a back sprite.
    .macro MegaEmitter emitter:req, x:req, y:req
    CreateEmitter 0, \emitter, EMITTER_CB_GENERIC
    GenericEmitterCbParams EMITTER_PRIORITY_MODE_NONE, EMITTER_TARGET_MODE_ATTACKER, EMITTER_POS_NORMAL_OFFSET_END, EMITTER_AXIS_NONE, EMITTER_BHV_FLAG_NONE, EMITTER_CAMERA_MODE_FIXED_ANGLE_0
    EmitterOffsetPosParams BATTLE_PTCL_FLIP_DISABLE, \x, \y, 0
    .endm

// Mega Evolution charge, played alongside the first AffinePulse in subscript_mega_evolution.s:
// rainbow streaks spiral in and wind into a glowing sphere that collapses with the squeezed sprite.
// Everything ends before the pulse's last dim tick, since End turns blending off.
L_0:
    LoadParticleResource 0, 486 // mega_evolution_spa
    JumpIfBattlerSide BATTLER_ROLE_ATTACKER, L_enemy, L_player

L_player:
    MegaEmitter 0, 614, 4506 // (0.15, 1.1)
    MegaEmitter 1, 614, 4506
    MegaEmitter 2, 614, 4506
    MegaEmitter 3, 614, 4506
    MegaEmitter 4, 614, 4506
    Jump L_wait

L_enemy:
    MegaEmitter 0, 0, 819 // (0, 0.2)
    MegaEmitter 1, 0, 819
    MegaEmitter 2, 0, 819
    MegaEmitter 3, 0, 819
    MegaEmitter 4, 0, 819

L_wait:
    WaitForAllEmitters
    UnloadParticleSystem 0
    // The charge sound plays on past this animation; waiting for it would hold the concealed sprite longer
    Func_SkipSoundEffectWait
    End
