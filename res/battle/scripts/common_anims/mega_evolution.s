#include "macros/btlanimcmd.inc"

.data

// Places a mega_evolution.spa emitter on the Pokemon, offset (in FX32 units) from its battle anim position
// towards the middle of its sprite: that position sits at the feet of a back sprite.
    .macro MegaEmitter emitter:req, x:req, y:req
    CreateEmitter 0, \emitter, EMITTER_CB_GENERIC
    GenericEmitterCbParams EMITTER_PRIORITY_MODE_NONE, EMITTER_TARGET_MODE_ATTACKER, EMITTER_POS_NORMAL_OFFSET_END, EMITTER_AXIS_NONE, EMITTER_BHV_FLAG_NONE, EMITTER_CAMERA_MODE_FIXED_ANGLE_0
    EmitterOffsetPosParams BATTLE_PTCL_FLIP_DISABLE, \x, \y, 0
    .endm

    .macro MegaBurst x:req, y:req, symbolY:req
    MegaEmitter 5, \x, \y
    MegaEmitter 6, \x, \y
    MegaEmitter 7, \x, \y
    MegaEmitter 8, \x, \y
    MegaEmitter 9, \x, \y
    MegaEmitter 10, \x, \y
    MegaEmitter 11, \x, \symbolY
    MegaEmitter 12, \x, \symbolY
    MegaEmitter 13, \x, \symbolY
    .endm

// Mega Evolution burst, played alongside the second AffinePulse in subscript_mega_evolution.s:
// the cocoon shatters in a flash and shock rings, then the Mega symbol appears above the Pokemon.
L_0:
    LoadParticleResource 0, 486 // mega_evolution_spa
    JumpIfBattlerSide BATTLER_ROLE_ATTACKER, L_enemy, L_player

L_player:
    MegaBurst 614, 4506, 4506 // (0.15, 1.1)
    Jump L_blend

L_enemy:
    // An enemy's head sits higher above this point, so the symbol (emitters 11-13) is raised to clear it
    MegaBurst 0, 819, 3686 // (0, 0.2), symbol (0, 0.9)

L_blend:
    // The pulse turns blending off when it finishes, which would draw the particles (and a Totem's aura) opaque
    // for the rest of this animation. Put the default blend back if that happens. The particles outlast this.
    Func_KeepTranslucent 40
    WaitForAllEmitters
    UnloadParticleSystem 0
    End
