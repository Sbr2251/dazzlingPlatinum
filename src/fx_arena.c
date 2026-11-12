#include "fx_arena.h"

#include <nitro.h>
#include <stdlib.h>

#include "port/postfx.h"
#include "port/sim_config_prj.h"

// ---------------------------------------------------------------------------
// Feature gates
// ---------------------------------------------------------------------------
// Under SIM_HEADLESS a feature is off unless its own SIM_FX_* env var is
// "1". Otherwise the sim_config_prj.ini value decides. Env parsing is
// cached, as in HiResText_IsEnabled.

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

BOOL FxArena_ArenaContextEnabled(void)
{
    return FxEnabled(SIM_Config_prj_GetConfig()->arenaContext, "SIM_FX_ARENA");
}

BOOL FxArena_BattleSwoopEnabled(void)
{
    return FxEnabled(SIM_Config_prj_GetConfig()->battleSwoop, "SIM_FX_SWOOP");
}

BOOL FxArena_WeatherLightningEnabled(void)
{
    return FxEnabled(SIM_Config_prj_GetConfig()->weatherLightning, "SIM_FX_LIGHTNING");
}

// ---------------------------------------------------------------------------
// Arena tint: exact time of day x weather x terrain
// ---------------------------------------------------------------------------
// Time tint interpolates linearly between the tints at five day centres on
// a circular 24-hour clock, so 07:00 and 09:00 differ even though both are
// "morning". The day centre is exactly neutral (256), so a noon battle is
// unchanged by the time tint alone.

typedef struct FxTimeTint {
    int minute; // centre of this part of the day, minutes since midnight
    int r, g, b; // tint at the centre, in 1/256
} FxTimeTint;

static const FxTimeTint sTimeTints[] = {
    { 90, 175, 195, 235 }, // late night 01:30: cool and dim
    { 420, 245, 238, 228 }, // morning 07:00: soft warm
    { 780, 256, 256, 256 }, // day 13:00: neutral
    { 1080, 255, 200, 160 }, // twilight 18:00: warm orange
    { 1290, 180, 195, 235 }, // night 21:30: cool and dim
};

static void TimeTint(int hour, int minute, int *outR, int *outG, int *outB)
{
    int now, i, prev, next, span, elapsed;
    int count = (int)(sizeof(sTimeTints) / sizeof(sTimeTints[0]));

    if (hour < 0) {
        hour = 0;
    } else if (hour > 23) {
        hour = 23;
    }

    if (minute < 0) {
        minute = 0;
    } else if (minute > 59) {
        minute = 59;
    }

    now = hour * 60 + minute;

    // Find the surrounding centres on the circular clock. The night centre
    // wraps to the late-night centre of the next day.
    prev = count - 1;
    next = 0;

    for (i = 0; i < count; i++) {
        if (sTimeTints[i].minute <= now) {
            prev = i;
        }
        if (sTimeTints[i].minute > now && next == 0) {
            next = i;
        }
    }

    // now is before the first centre (late night): prev is last, next is 0
    if (now < sTimeTints[0].minute) {
        prev = count - 1;
        next = 0;
    }

    span = sTimeTints[next].minute - sTimeTints[prev].minute;
    if (span <= 0) {
        span += 24 * 60;
    }
    elapsed = now - sTimeTints[prev].minute;
    if (elapsed < 0) {
        elapsed += 24 * 60;
    }

    *outR = sTimeTints[prev].r + (sTimeTints[next].r - sTimeTints[prev].r) * elapsed / span;
    *outG = sTimeTints[prev].g + (sTimeTints[next].g - sTimeTints[prev].g) * elapsed / span;
    *outB = sTimeTints[prev].b + (sTimeTints[next].b - sTimeTints[prev].b) * elapsed / span;
}

static void WeatherTint(int weather, int *outR, int *outG, int *outB)
{
    *outR = 256;
    *outG = 256;
    *outB = 256;

    switch (weather) {
    case OVERWORLD_WEATHER_CLOUDY:
        *outR = 240;
        *outG = 242;
        *outB = 248;
        break;
    case OVERWORLD_WEATHER_RAINING:
        *outR = 225;
        *outG = 232;
        *outB = 245;
        break;
    case OVERWORLD_WEATHER_HEAVY_RAIN:
        *outR = 205;
        *outG = 215;
        *outB = 235;
        break;
    case OVERWORLD_WEATHER_THUNDERSTORM:
        *outR = 190;
        *outG = 200;
        *outB = 230;
        break;
    case OVERWORLD_WEATHER_SNOWING:
        *outR = 245;
        *outG = 248;
        *outB = 255;
        break;
    case OVERWORLD_WEATHER_HEAVY_SNOW:
        *outR = 235;
        *outG = 240;
        *outB = 252;
        break;
    case OVERWORLD_WEATHER_BLIZZARD:
        *outR = 220;
        *outG = 228;
        *outB = 248;
        break;
    case OVERWORLD_WEATHER_SLOW_ASHFALL:
        *outR = 235;
        *outG = 230;
        *outB = 225;
        break;
    case OVERWORLD_WEATHER_SANDSTORM:
        *outR = 250;
        *outG = 225;
        *outB = 175;
        break;
    case OVERWORLD_WEATHER_HAILING:
        *outR = 230;
        *outG = 235;
        *outB = 245;
        break;
    case OVERWORLD_WEATHER_SPIRITS:
        *outR = 200;
        *outG = 190;
        *outB = 230;
        break;
    case OVERWORLD_WEATHER_FOG:
        *outR = 215;
        *outG = 220;
        *outB = 230;
        break;
    case OVERWORLD_WEATHER_DEEP_FOG:
        *outR = 190;
        *outG = 195;
        *outB = 215;
        break;
    case OVERWORLD_WEATHER_DARK_FLASH:
        *outR = 150;
        *outG = 150;
        *outB = 170;
        break;
    case OVERWORLD_WEATHER_RIFT_MIST:
        *outR = 190;
        *outG = 180;
        *outB = 230;
        break;
    case OVERWORLD_WEATHER_HARSH_SUN:
        *outR = 256;
        *outG = 245;
        *outB = 220;
        break;
    case OVERWORLD_WEATHER_TRICK_ROOM:
        *outR = 220;
        *outG = 210;
        *outB = 250;
        break;
    default:
        break;
    }
}

static void TerrainTint(enum BattleTerrain terrain, enum BattleBackground background, int *outR, int *outG, int *outB)
{
    *outR = 256;
    *outG = 256;
    *outB = 256;

    switch (terrain) {
    case TERRAIN_SAND:
        *outR = 250;
        *outG = 235;
        *outB = 200;
        break;
    case TERRAIN_GRASS:
        *outR = 250;
        *outG = 256;
        *outB = 240;
        break;
    case TERRAIN_PUDDLE:
        *outR = 235;
        *outG = 245;
        *outB = 256;
        break;
    case TERRAIN_MOUNTAIN:
        *outR = 240;
        *outG = 240;
        *outB = 248;
        break;
    case TERRAIN_CAVE:
        *outR = 210;
        *outG = 210;
        *outB = 225;
        break;
    case TERRAIN_SNOW:
        *outR = 250;
        *outG = 252;
        *outB = 256;
        break;
    case TERRAIN_WATER:
        *outR = 230;
        *outG = 242;
        *outB = 256;
        break;
    case TERRAIN_ICE:
        *outR = 240;
        *outG = 248;
        *outB = 256;
        break;
    case TERRAIN_BUILDING:
        *outR = 252;
        *outG = 250;
        *outB = 248;
        break;
    case TERRAIN_GREAT_MARSH:
        *outR = 240;
        *outG = 250;
        *outB = 235;
        break;
    default:
        break;
    }

    // Indoor, cave and Distortion World backgrounds are darker rooms, not
    // open sky, whatever the terrain under the player is.
    switch (background) {
    case BACKGROUND_CAVE_1:
    case BACKGROUND_CAVE_2:
    case BACKGROUND_CAVE_3:
        *outR = *outR * 215 / 256;
        *outG = *outG * 215 / 256;
        *outB = *outB * 225 / 256;
        break;
    case BACKGROUND_INDOORS_1:
    case BACKGROUND_INDOORS_2:
    case BACKGROUND_INDOORS_3:
    case BACKGROUND_BATTLE_TOWER:
    case BACKGROUND_BATTLE_FACTORY:
    case BACKGROUND_BATTLE_ARCADE:
    case BACKGROUND_BATTLE_CASTLE:
    case BACKGROUND_BATTLE_HALL:
        *outR = *outR * 250 / 256;
        *outG = *outG * 250 / 256;
        *outB = *outB * 248 / 256;
        break;
    case BACKGROUND_DISTORTION_WORLD:
        *outR = *outR * 200 / 256;
        *outG = *outG * 190 / 256;
        *outB = *outB * 235 / 256;
        break;
    default:
        break;
    }
}

void FxArena_ArenaTint(int hour, int minute, int weather, enum BattleTerrain terrain, enum BattleBackground background, int *outR, int *outG, int *outB)
{
    int timeR, timeG, timeB;
    int weatherR, weatherG, weatherB;
    int terrainR, terrainG, terrainB;

    TimeTint(hour, minute, &timeR, &timeG, &timeB);
    WeatherTint(weather, &weatherR, &weatherG, &weatherB);
    TerrainTint(terrain, background, &terrainR, &terrainG, &terrainB);

    *outR = timeR * weatherR / 256 * terrainR / 256;
    *outG = timeG * weatherG / 256 * terrainG / 256;
    *outB = timeB * weatherB / 256 * terrainB / 256;
}

// ---------------------------------------------------------------------------
// Lightning
// ---------------------------------------------------------------------------

BOOL FxArena_IsThunderWeather(int weather)
{
    return weather == OVERWORLD_WEATHER_THUNDERSTORM ? TRUE : FALSE;
}

// Multi-strike flash envelope, one entry per frame, 0..256. The first entry
// is the strike; the rest are the flickering afterglow.
static const u8 sFlashProfile[] = { 255, 170, 225, 110, 150, 60, 85, 0 };
#define FLASH_FRAMES ((int)(sizeof(sFlashProfile) / sizeof(sFlashProfile[0])))

static u32 sLightningRng;
static int sLightningWaitFrames;
static int sLightningFlashFrame;

static u32 LightningRand(void)
{
    sLightningRng = sLightningRng * 1664525u + 1013904223u;
    return (sLightningRng >> 16) & 0x7FFF;
}

void FxArena_LightningReset(u32 seed)
{
    sLightningRng = seed ^ 0x9E3779B9u;
    if (sLightningRng == 0) {
        sLightningRng = 0x12345678u;
    }
    // First strike 4-9 s in at 30 drawn frames/s (battle) or 2-4.5 s at
    // 60 frames/s (field): the same counter serves both, so the field
    // simply flashes sooner.
    sLightningWaitFrames = 120 + (int)(LightningRand() % 150);
    sLightningFlashFrame = 0;
}

void FxArena_FieldLightningUpdate(int weather)
{
    static int sLastWeather = -1;
    int strength;

    if (!FxArena_WeatherLightningEnabled()) {
        return;
    }

    if (weather != sLastWeather) {
        sLastWeather = weather;

        if (FxArena_IsThunderWeather(weather)) {
            FxArena_LightningReset((u32)weather * 7919u + 0x5EEDu);
        }
    }

    if (!FxArena_IsThunderWeather(weather)) {
        return;
    }

    strength = FxArena_LightningUpdate(weather);

    if (strength > 0) {
        // Bloom on the bright parts plus a white vignette that lifts the
        // whole frame (a glow alone is nearly invisible in a dark storm
        // scene). Both decay in 2 frames; the next flash frame refreshes
        // them, and the vignette colour is only touched while flashing.
        PostFX_Glow((float)strength / 256.0f * 0.9f, 2);
        PostFX_Vignette(1.0f, 1.0f, 1.0f, (float)strength / 256.0f * 0.35f, 2);
    }
}

int FxArena_LightningUpdate(int weather)
{
    int strength;

    if (!FxArena_IsThunderWeather(weather)) {
        sLightningFlashFrame = 0;
        return 0;
    }

    if (sLightningFlashFrame > 0) {
        strength = sFlashProfile[FLASH_FRAMES - sLightningFlashFrame];
        sLightningFlashFrame--;

        if (sLightningFlashFrame == 0) {
            sLightningWaitFrames = 150 + (int)(LightningRand() % 300);
        }

        return strength;
    }

    if (sLightningWaitFrames > 0) {
        sLightningWaitFrames--;
    }

    if (sLightningWaitFrames <= 0) {
        // The first profile entry goes out on this call; the rest follow
        // one per call from the branch above.
        sLightningFlashFrame = FLASH_FRAMES - 1;
        return sFlashProfile[0];
    }

    return 0;
}
