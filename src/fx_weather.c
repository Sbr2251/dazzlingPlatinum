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
        const char *interactiveFx = getenv("SIM_HEADLESS_INTERACTIVE_FX");
        BOOL allowInteractive = (interactiveFx != NULL && interactiveFx[0] != 0 && interactiveFx[0] != '0');
        sHeadless = (!allowInteractive && headless != NULL && headless[0] != 0 && headless[0] != '0') ? 1 : 0;
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
        // clear day, Route 218 (Everspring Sanctuary) gets bioluminescent
        // fairy spores & subtle twilight aura, Routes 222/223 get the violet
        // rift aura (kind 7), Routes 215/216 get light rain / snow motes
        // (kind 8), Route 217 keeps only its stock blizzard, Stark Mountain /
        // ashfall areas get heat haze.
        if (mapHeaderID == MAP_HEADER_ETERNA_FOREST || mapHeaderID == MAP_HEADER_ETERNA_FOREST_OUTSIDE) {
            kind = 4; intensity = 0.8f;
        } else if (mapHeaderID == MAP_HEADER_ROUTE_218) {
            kind = 6; intensity = 0.75f;
        } else if (mapHeaderID == MAP_HEADER_ROUTE_223) {
            // Violet Rift Coast & Sea-Sky Aura: full strength at the rift sea.
            kind = 7; intensity = 0.80f;
        } else if (mapHeaderID == MAP_HEADER_ROUTE_222) {
            // Violet-lit coast: the rift glow cast westward, gentler.
            kind = 7; intensity = 0.55f;
        } else if (mapHeaderID == MAP_HEADER_ROUTE_215) {
            // Flooded lowland: light rain streaks + gentle cool vignette,
            // capped so the lowland stays crisp and moody, never grey-green.
            kind = 8; intensity = 0.30f;
        } else if (mapHeaderID == MAP_HEADER_ROUTE_216) {
            // Teo's Memorial Ridge: very gentle snow motes so the ridge stays
            // razor-sharp by day and night.
            kind = 8; intensity = 0.25f;
        } else if (mapHeaderID == MAP_HEADER_ROUTE_217) {
            // Indra's camp: Platinum's stock heavy blizzard already runs here;
            // stacking kind 8 on top whited the screen out. No SDL3 pass, so
            // the dark-violet tent and lantern cut crisply through the snow.
            kind = 0; intensity = 0.0f;
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
    // Dry / snow routes get no water pass: under night-indigo lighting their
    // snow and grass satisfy the generic blue-dominant water mask and would
    // reflect. Water routes (215, 218, 222, 223) and every other map keep it.
    BOOL dryRoute = mapHeaderID == MAP_HEADER_ROUTE_206 || mapHeaderID == MAP_HEADER_ROUTE_207
        || mapHeaderID == MAP_HEADER_ROUTE_216 || mapHeaderID == MAP_HEADER_ROUTE_217;
    SIM_Water_Set((FxWeather_WaterReflectionsEnabled() && !dryRoute) ? 1 : 0);
}
