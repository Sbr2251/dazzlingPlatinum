#include "macros/btlanimcmd.inc"

.data

// Places a mega_evolution.spa emitter on the Pokemon, offset (in FX32 units) from its battle anim position
// towards the middle of its sprite: that position sits at the feet of a back sprite.
    .macro MegaEmitter emitter:req, x:req, y:req
    CreateEmitter 0, \emitter, EMITTER_CB_GENERIC
    GenericEmitterCbParams EMITTER_PRIORITY_MODE_NONE, EMITTER_TARGET_MODE_ATTACKER, EMITTER_POS_NORMAL_OFFSET_END, EMITTER_AXIS_NONE, EMITTER_BHV_FLAG_NONE, EMITTER_CAMERA_MODE_FIXED_ANGLE_0
    EmitterOffsetPosParams BATTLE_PTCL_FLIP_DISABLE, \x, \y, 0
    .endm

    .macro MegaSequence x:req, y:req, symbolY:req
    // The orb forms round the Pokemon while ribbons of light circle it
    Func_MegaEvolutionCue MEGA_EVOLUTION_CUE_CHARGE
    // The stage camera circles the Pokemon through the charge
    StageCameraOrbit 40, 36
    MegaEmitter 0, \x, \y
    MegaEmitter 1, \x, \y
    MegaEmitter 2, \x, \y
    MegaEmitter 7, \x, \y
    MegaEmitter 5, \x, \y
    MegaEmitter 6, \x, \y
    MegaEmitter 3, \x, \y
    MegaEmitter 4, \x, \y
    // The charge's length; AffinePulse's timings (and SEQ_SE_MEGA_CHARGE) are built round it
    Delay 36
    // The orb bursts and the new form springs out, then the Mega symbol appears above it
    Func_MegaEvolutionCue MEGA_EVOLUTION_CUE_BURST
    // The burst shakes the stage camera, which then eases home while the particles play
    StageCameraShake 4, 12
    StageCameraHome 20
    MegaEmitter 8, \x, \y
    MegaEmitter 9, \x, \y
    MegaEmitter 10, \x, \y
    MegaEmitter 11, \x, \y
    MegaEmitter 12, \x, \y
    MegaEmitter 13, \x, \y
    MegaEmitter 14, \x, \symbolY
    MegaEmitter 15, \x, \symbolY
    MegaEmitter 16, \x, \symbolY
    .endm

// Mega Evolution, played alongside AffinePulse in subscript_mega_evolution.s, in the style of the X and Y games.
// The cues keep the pulse's sprite changes in step with the particles, however long they took to load.
L_0:
    LoadParticleResource 0, 486 // mega_evolution_spa
    // The stage camera pushes in on the Pokemon before the charge
    StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER, 70, 0, -4, 10
    Delay 10
    JumpIfBattlerSide BATTLER_ROLE_ATTACKER, L_enemy, L_player

L_player:
    MegaSequence 614, 4506, 4506 // (0.15, 1.1)
    Jump L_blend

L_enemy:
    // An enemy's head sits higher above this point, so the symbol (emitters 14-16) is raised to clear it
    MegaSequence 0, 819, 3686 // (0, 0.2), symbol (0, 0.9)

L_blend:
    // The pulse turns blending off when it finishes, which would draw the particles (and a Totem's aura) opaque
    // for the rest of this animation. Put the default blend back if that happens. The particles outlast this.
    Func_KeepTranslucent 40
    WaitForAllEmitters
    UnloadParticleSystem 0
    StageCameraWait
    End
