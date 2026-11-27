#ifndef PORT_SIM_BATTLE3D_H
#define PORT_SIM_BATTLE3D_H

#include <nitro/types.h>
#include <stdint.h>

#ifdef SDK_PORT
#include <simulator/sim_battle3d.h>
#else
enum SIM_Battle3DBiome {
    SIM_BATTLE3D_BIOME_PLAIN = 0,
    SIM_BATTLE3D_BIOME_FOREST = 1,
    SIM_BATTLE3D_BIOME_WATER = 2,
    SIM_BATTLE3D_BIOME_CAVE = 3,
    SIM_BATTLE3D_BIOME_SNOW = 4,
    SIM_BATTLE3D_BIOME_CITY = 5,
    SIM_BATTLE3D_BIOME_INDOORS = 6,
    SIM_BATTLE3D_BIOME_DISTORTION = 7,
    SIM_BATTLE3D_BIOME_COUNT = 8
};
enum SIM_Battle3DTimeOfDay {
    SIM_BATTLE3D_TOD_MORNING = 0,
    SIM_BATTLE3D_TOD_DAY = 1,
    SIM_BATTLE3D_TOD_EVENING = 2,
    SIM_BATTLE3D_TOD_NIGHT = 3
};
enum SIM_Battle3DWeather {
    SIM_BATTLE3D_WEATHER_CLEAR = 0,
    SIM_BATTLE3D_WEATHER_RAIN = 1,
    SIM_BATTLE3D_WEATHER_SUN = 2,
    SIM_BATTLE3D_WEATHER_HAIL = 3,
    SIM_BATTLE3D_WEATHER_SAND = 4,
    SIM_BATTLE3D_WEATHER_FOG = 5
};
#define SIM_BATTLE3D_MAX_BATTLERS 4
typedef struct SIM_Battle3DBattler {
    int visible;
    int isPlayer;
    float worldX;
    float worldY;
    float worldZ;
    float shadowRadius;
    float alpha;
} SIM_Battle3DBattler;
typedef struct SIM_Battle3DFrame {
    int active;
    int biome;
    int timeOfDay;
    int weather;
    float alpha;
    float timeSec;
    float brightness;
    float camEye[3];
    float camTarget[3];
    float camFovDeg;
    float camAspect;
    SIM_Battle3DBattler battlers[SIM_BATTLE3D_MAX_BATTLERS];
} SIM_Battle3DFrame;
#endif

#ifdef __cplusplus
extern "C" {
#endif

// TRUE when the BDSP HD-2D 3D battle scene is active (GPU wide layout,
// interactive run OR headless opt-in via SIM_FX_BDSP_BATTLE=1 or
// SIM_HEADLESS_INTERACTIVE_FX=1). Existing goldens stay byte-identical.
BOOL SIM_Battle3D_IsEnabled(void);

// Forward frame parameters to the Metal 3D battle arena renderer (no-op if disabled).
void SIM_Battle3D_SubmitFrame(const SIM_Battle3DFrame *frame);

// Clear the active 3D battle frame (call on battle teardown / sub-menu entry).
void SIM_Battle3D_Reset(void);

// Map Platinum BACKGROUND_* enum to enum SIM_Battle3DBiome.
int SIM_Battle3D_BiomeFromBackground(int background);

#ifdef __cplusplus
}
#endif

#endif // PORT_SIM_BATTLE3D_H
