#ifndef POKEPLATINUM_FX_PARTICLES_H
#define POKEPLATINUM_FX_PARTICLES_H

#include <nitro.h>

// Lane particles: GPU particle-density boost for move effects (v2).
// Live SPL parents spawn persistent embers into their manager's store:
// small (1-2 px at DS scale) square dots, sampled from the centre of
// the parent texture and brightened, that drift by element type (Fire
// embers rise and fade, Electric sparks arc out, Ice/Mega shards
// glitter) and briefly outlive their parent. Large / ring / flash
// parents never clone, so the Mega emblem rings stay single. Deterministic:
// every random choice is a hash of (seed, frame, life), never the wall
// clock. Zero change when off (density 0, GL backend, or headless
// without SIM_FX_PARTICLES=1).
//
// Presentation only: nothing here changes battle mechanics, RNG-visible
// state or save data.

// Feature gate: sim_config_prj.ini [General] ParticleBoost (on by
// default in the app) and ParticleBoostDensity (0-8, default 3).
BOOL FxParticles_Enabled(void);
int FxParticles_Density(void);

// Call once per drawn frame, before the particle draw, to decay the
// move/burst windows and push the resolved parameters to the SPL pass.
void FxParticles_Tick(void);

// The move whose animation just started: applies the signature-move
// tuning table (denser / longer trails) for the window below. Pass
// MOVE_NONE (0) to clear the move boost.
void FxParticles_SetMove(int move);

// Mega Evolution burst: dense, wide, bright sparkles for the burst beat.
void FxParticles_SetMegaBurst(void);

#endif // POKEPLATINUM_FX_PARTICLES_H
