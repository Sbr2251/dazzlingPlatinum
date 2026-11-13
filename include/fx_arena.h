#ifndef POKEPLATINUM_FX_ARENA_H
#define POKEPLATINUM_FX_ARENA_H

#include <nitro.h>

#include "constants/battle.h"
#include "constants/overworld_weather.h"

// Lane arena: the battle takes the overworld's time of day (exact, not the
// 3-palette bucket), weather and terrain as arena lighting/tint parameters;
// lightning in thunderstorm weather.
//
// Presentation only: nothing here changes battle mechanics, RNG-visible
// state or save data. Every feature is off under SIM_HEADLESS unless its
// SIM_FX_* env var enables it, so existing golden screenshots stay
// byte-identical.

// Feature gates: sim_config_prj.ini [General] ArenaContext /
// WeatherLightning (all on by default in the app).
BOOL FxArena_ArenaContextEnabled(void);
BOOL FxArena_WeatherLightningEnabled(void);

// Combined arena tint multiplier per channel, in 1/256 (256 = unchanged),
// from the exact clock time, the field weather, and the battle's terrain
// and background. At the day centre, clear weather, on plain terrain it is
// exactly 256, 256, 256, so a day battle is unchanged by the tint alone.
void FxArena_ArenaTint(int hour, int minute, int weather, enum BattleTerrain terrain, enum BattleBackground background, int *outR, int *outG, int *outB);

// TRUE for the weather that carries lightning (thunderstorm only).
BOOL FxArena_IsThunderWeather(int weather);

// Deterministic lightning scheduler. Reset once when a scene starts (a
// battle, a map load), then call Update once per drawn/field frame with the
// current weather; it returns this frame's flash strength, 0..256
// (0 = no flash). The sequence is a fixed LCRNG stream from the seed, so
// the same seed and frame count give the same flashes under lockstep.
void FxArena_LightningReset(u32 seed);
int FxArena_LightningUpdate(int weather);
// Overworld lightning: call once per field frame with the current field
// weather. It resets its scheduler when the weather changes and issues the
// PostFX flash itself, so the caller needs no state.
void FxArena_FieldLightningUpdate(int weather);

#endif // POKEPLATINUM_FX_ARENA_H
