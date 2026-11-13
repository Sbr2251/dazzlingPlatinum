#ifndef SIM_CONFIG_PRJ_H
#define SIM_CONFIG_PRJ_H

#include <nitro/types.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    BOOL enable60fps; // When true, unlock the framerate to 60fps
    BOOL enable60fpsSpeedFix; // When enabled, fixes things in the game that run at double speed due to being at 60fps
	BOOL enableAsserts; //Should asserts cause a communication error?
    BOOL breakDebuggerOnGfAssert; // When true, break the debugger when a GF_ASSERT fails
    BOOL megaCinematicShort; // Mega cinematic: false = full (~4.5s), true = short
    BOOL hiResText; // Hi-res dialogue text overlay prototype (hiresui); false = DS text only
    BOOL overworldCinematics; // Overworld cinematics (lane cine): scripted field-camera moves; true = on

	// Cheats section
	BOOL walkThroughWalls; // When enabled, allows the player to walk through walls
    BOOL disableRandomEncounters; // When enabled, all random encounters are turned off
    BOOL runFromTrainerBattles; // When enabled, allows running away from trainer battles
    BOOL battleInstantAnimations; // Battle Engine fast mode: skip text/gauge/move-animation waits (docs/battle_engine.md)
    BOOL fieldFastRebuild; // fieldkeep: collapse already-ready FieldMap Init/Exit states into one frame (same teardown/rebuild, fewer idle frames)
    BOOL arenaContext; // Lane arena: battle arena takes the overworld time of day, weather and terrain as lighting/tint
    BOOL particleBoost; // Lane particles: GPU child sparkles for live SPL particles
    int particleBoostDensity; // Lane particles: child sparkles per live particle, 0-8
    BOOL realPlaceArena; // Lane arena2: battle backdrop is a capture of the real overworld around the player
    BOOL battleSwoop; // Lane arena: camera dive into battle (field) + high/far settle to home (battle)
    BOOL weatherLightning; // Lane arena: lightning flashes in thunderstorm weather, field and battle
    BOOL sceneLights; // Lane lighting: per-pixel point lights in the G3 shader (move lights, ambient/key)
    BOOL spriteRimLight; // Lane lighting: thin bright edge on battle sprites from the key light
    int fieldLoadRadius; // fx-wide: loaded land-block window width (2 = DS 2x2, 3 = 3x3); app default 3
    BOOL debugWideCamera; // fx-wide: 16:9 aspect, zoomed-out field camera so the extra loaded blocks are visible
    BOOL battleHud; // battlehud: battle menus mirrored on the top screen; app default on, headless off unless SIM_FX_BATTLEHUD=1
    BOOL weatherFx; // Lane weather: fog/shafts/heat/rain/lightning post effects (GPU only)
    BOOL waterReflections; // Lane weather: pixelated water reflections + shoreline foam (GPU only)
} SIM_Config_prj_type;

// True when the game runs logic at 60 Hz AND time-based quantities must be
// halved to keep real-time speed identical to 30 Hz logic (fps60 lane).
// This is the single predicate every 60 fps speed fix uses, so the two
// config flags are never re-checked ad-hoc at call sites.
BOOL SIM_Config_prj_DoubleStep(void);
// fx-wide: effective values after the headless rule (under SIM_HEADLESS the
// load radius stays 2 and the wide camera stays off unless SIM_FX_WIDE=1 /
// SIM_FX_WIDE_CAMERA=1 is set, so existing golden screenshots stay identical).
int SIM_Config_prj_FieldLoadRadius(void);
BOOL SIM_Config_prj_DebugWideCamera(void);
void SIM_Config_prj_LoadDefaults(SIM_Config_prj_type * aConfig);
BOOL SIM_Config_prj_LoadConfigFile(SIM_Config_prj_type * aConfig);
void SIM_Config_prj_SaveConfigFile(SIM_Config_prj_type * aConfig);
void SIM_Config_prj_init();
SIM_Config_prj_type * SIM_Config_prj_GetConfig();

#ifdef __cplusplus
}
#endif

#endif