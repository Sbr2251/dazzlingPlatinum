#ifndef POKEPLATINUM_FX_LIGHTING_H
#define POKEPLATINUM_FX_LIGHTING_H

#include <nitro.h>

// Lane lighting: scene lights + sprite rim lighting + move lights.
//
// Presentation only: nothing here changes battle mechanics, RNG-visible
// state or save data. Every feature is off under SIM_HEADLESS unless its
// SIM_FX_* env var enables it, so existing golden screenshots stay
// byte-identical. The GPU G3 shader does the work; under Renderer=gl
// the SIM_Lights state is ignored, so this is a no-op there too.

// Feature gates: sim_config_prj.ini [General] SceneLights /
// SpriteRimLight (both on by default in the app).
BOOL FxLighting_SceneLightsEnabled(void);
BOOL FxLighting_SpriteRimLightEnabled(void);

// A move animation started: drive the light track for this move until
// FxLighting_EndMove. attacker/defender are battler indices (0..3).
void FxLighting_StartMove(int move, int attacker, int defender);
// The move animation ended: drop the move lights, keep the rim.
void FxLighting_EndMove(void);
// Once per battle-anim frame (called from BattleAnimSystem_ExecuteScript):
// advances the flicker envelope and pushes the current SIM_LightsState.
// With no move active it pushes the rim-only state, so battle-start
// frames already show the sprite rim.
void FxLighting_Update(void);
// Battle is over / leaving battle: drop every light and the rim.
void FxLighting_Clear(void);

#endif // POKEPLATINUM_FX_LIGHTING_H
