#ifndef FX_WEATHER_H
#define FX_WEATHER_H
#include <nitro/types.h>
// fx_weather lane: tells the simulator the active field weather/mood on
// map change so the GPU backend can run its weather/water post passes.
void FxWeather_OnMapChange(int mapHeaderID, u16 weather);
BOOL FxWeather_WeatherFxEnabled(void);
BOOL FxWeather_WaterReflectionsEnabled(void);
#endif
