#include "fx_weather.h"
#include <nitro.h>
#include <stdlib.h>
#include <simulator/sim_weather.h>
#include "constants/fieldmap.h"
#include "constants/overworld_weather.h"
#include "port/sim_config_prj.h"

// Feature gates follow the arena lane pattern: under SIM_HEADLESS a
// feature is off unless SIM_FX_WEATHER / SIM_FX_WATER is "1"; otherwise
// the sim_config_prj.ini value decides.
static int EnvFlag(const char *name)
{
    const char *env = getenv(name);
    if (env == NULL || env[0] == 0) {
        return -1;
    }
    return env[0] != '0' ? 1 : 0;
}
static BOOL FxEnabled(int configValue, const char *envName)
{
    static int sHeadless = -1;
    int env;
    if (sHeadless < 0) {
        const char *headless = getenv("SIM_HEADLESS");
        sHeadless = (headless != NULL && headless[0] != 0 && headless[0] != '0') ? 1 : 0;
    }
    env = EnvFlag(envName);
    if (sHeadless) {
        return env == 1 ? TRUE : FALSE;
    }
    if (env >= 0) {
        return env == 1 ? TRUE : FALSE;
    }
    return configValue ? TRUE : FALSE;
}
BOOL FxWeather_WeatherFxEnabled(void)
{
    return FxEnabled(SIM_Config_prj_GetConfig()->weatherFx, "SIM_FX_WEATHER");
}
BOOL FxWeather_WaterReflectionsEnabled(void)
{
    return FxEnabled(SIM_Config_prj_GetConfig()->waterReflections, "SIM_FX_WATER");
}

void FxWeather_OnMapChange(int mapHeaderID, u16 weather)
{
    int kind = 0;
    float intensity = 0.0f;
    if (FxWeather_WeatherFxEnabled()) {
        // Map mood first: Eterna Forest gets canopy light shafts on a
        // clear day, Stark Mountain / ashfall areas get heat haze.
        if (mapHeaderID == MAP_HEADER_ETERNA_FOREST || mapHeaderID == MAP_HEADER_ETERNA_FOREST_OUTSIDE) {
            kind = 4; intensity = 0.8f;
        } else if (mapHeaderID == MAP_HEADER_STARK_MOUNTAIN_OUTSIDE || mapHeaderID == MAP_HEADER_STARK_MOUNTAIN_ROOM_1
            || mapHeaderID == MAP_HEADER_STARK_MOUNTAIN_ROOM_2 || mapHeaderID == MAP_HEADER_STARK_MOUNTAIN_ROOM_3
            || weather == OVERWORLD_WEATHER_SLOW_ASHFALL) {
            kind = 5; intensity = 0.75f;
        } else if (weather == OVERWORLD_WEATHER_THUNDERSTORM) {
            kind = 3; intensity = 0.9f;
        } else if (weather == OVERWORLD_WEATHER_RAINING || weather == OVERWORLD_WEATHER_HEAVY_RAIN) {
            kind = 2; intensity = weather == OVERWORLD_WEATHER_HEAVY_RAIN ? 0.9f : 0.65f;
        } else if (weather == OVERWORLD_WEATHER_FOG || weather == OVERWORLD_WEATHER_DEEP_FOG) {
            kind = 1; intensity = weather == OVERWORLD_WEATHER_DEEP_FOG ? 0.9f : 0.6f;
        } else if (weather == OVERWORLD_WEATHER_CLOUDY) {
            kind = 1; intensity = 0.3f;
        }
    }
    SIM_Weather_Set(kind, intensity);
    SIM_Water_Set(FxWeather_WaterReflectionsEnabled() ? 1 : 0);
}
