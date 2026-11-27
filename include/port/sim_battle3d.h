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
enum SIM_Battle3DAnimState {
    SIM_BATTLE3D_ANIM_IDLE = 0,
    SIM_BATTLE3D_ANIM_ATTACK_PHYS = 1,
    SIM_BATTLE3D_ANIM_ATTACK_SPEC = 2,
    SIM_BATTLE3D_ANIM_HIT = 3,
    SIM_BATTLE3D_ANIM_FAINT = 4,
    SIM_BATTLE3D_ANIM_CRY = 5
};
typedef struct SIM_Battle3DBattler {
    int visible;
    int isPlayer;
    float worldX;
    float worldY;
    float worldZ;
    float shadowRadius;
    float alpha;
    int species;
    int form;
    int isShiny;
    float yawDeg;
    float modelScale;
    int animState;
    float animTime;
    int animNonce;
    int use3dModel;
    float flashAmount;
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
    struct SIM_Battle3DActor {
        int visible;
        int kind;
        float worldX;
        float worldY;
        float worldZ;
        float yawDeg;
        float pitchDeg;
        float rollDeg;
        float scale;
        float alpha;
        int animState;
        float animTime;
        int animNonce;
        int attachActorIdx;
        int attachBoneKind;
        float attachOffset[3];
    } actors[4];
    struct SIM_Battle3DBurst {
        int active;
        float worldX;
        float worldY;
        float worldZ;
        float progress;
        float radius;
        float color[3];
    } burst;
} SIM_Battle3DFrame;
#define SIM_BATTLE3D_MAX_ACTORS 4
typedef struct SIM_Battle3DActor SIM_Battle3DActor;
enum SIM_Battle3DActorKind {
    SIM_BATTLE3D_ACTOR_NONE = 0,
    SIM_BATTLE3D_ACTOR_TRAINER_LUCAS = 1,
    SIM_BATTLE3D_ACTOR_TRAINER_DAWN = 2,
    SIM_BATTLE3D_ACTOR_POKEBALL = 3
};
enum SIM_Battle3DTrainerAnim {
    SIM_BATTLE3D_TRANIM_WAIT = 0,
    SIM_BATTLE3D_TRANIM_THROW = 1,
    SIM_BATTLE3D_TRANIM_ADVENT = 2,
    SIM_BATTLE3D_TRANIM_LOSE = 3
};
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

// TRUE when extracted BDSP 3D Pokemon models/arenas are allowed to render
// (app default ON when SIM_Battle3D_IsEnabled(); headless OFF unless SIM_FX_BDSP_MODELS=1).
BOOL SIM_Battle3D_ModelsEnabled(void);

// TRUE when a 3D .glb model is available for this species/form/shiny and models are enabled.
BOOL SIM_Battle3D_HasModelLoaded(int species, int form, int isShiny);

// TRUE when an extracted 3D .glb arena is available for this biome and models are enabled.
BOOL SIM_Battle3D_HasArenaLoaded(int biome);

// TRUE when an extracted 3D trainer/ball actor .glb is available and models are enabled.
BOOL SIM_Battle3D_HasActorLoaded(int kind);
BOOL SIM_Battle3D_GetActorHandPos(int actorIdx, int boneKind, float outPos[3]);

#ifdef __cplusplus
}
#endif

#endif // PORT_SIM_BATTLE3D_H
