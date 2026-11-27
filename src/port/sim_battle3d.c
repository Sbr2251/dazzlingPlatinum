// Game-side bridge to the Metal BDSP HD-2D 3D battle arena renderer.
// See include/port/sim_battle3d.h and subprojects/libntr/include/simulator/sim_battle3d.h.

#include "port/sim_battle3d.h"

#include <stdlib.h>

#ifdef SDK_PORT
#include <simulator/sim_headless.h>
#endif

#include "constants/battle/backgrounds.h"

#include "battle/battle_hud.h"
#include "port/sim_config_prj.h"
#include "port/sim_wide.h"

#ifdef SDK_PORT
extern void SIM_Battle3D_SetFrame(const SIM_Battle3DFrame *frame) __attribute__((weak));
extern void SIM_Battle3D_Clear(void) __attribute__((weak));
extern int SIM_Battle3D_IsSupported(void) __attribute__((weak));
__attribute__((weak)) int SIM_Battle3D_HasModel(int species, int form, int isShiny)
{
    (void)species;
    (void)form;
    (void)isShiny;
    return 0;
}
__attribute__((weak)) int SIM_Battle3D_HasArena(int biome)
{
    (void)biome;
    return 0;
}
__attribute__((weak)) int SIM_Battle3D_HasActor(int kind)
{
    (void)kind;
    return 0;
}
#endif

BOOL SIM_Battle3D_IsEnabled(void)
{
#ifdef SDK_PORT
    if (!SIM_Wide_IsWideLayout() || !BattleHud_IsEnabled()) {
        return FALSE;
    }

    if (SIM_Battle3D_IsSupported == NULL || !SIM_Battle3D_IsSupported()) {
        return FALSE;
    }

    if (!SIM_Headless_Enabled()) {
        const char *env = getenv("SIM_FX_BDSP_BATTLE");
        if (env != NULL && env[0] == '0') {
            return FALSE;
        }
        return TRUE;
    }

    {
        const char *bdsp = getenv("SIM_FX_BDSP_BATTLE");
        const char *interactive = getenv("SIM_HEADLESS_INTERACTIVE_FX");

        if (bdsp != NULL && bdsp[0] == '0') {
            return FALSE;
        }
        if ((bdsp != NULL && bdsp[0] == '1') || (interactive != NULL && interactive[0] == '1')) {
            return TRUE;
        }
    }

    return FALSE;
#else
    return FALSE;
#endif
}

void SIM_Battle3D_SubmitFrame(const SIM_Battle3DFrame *frame)
{
#ifdef SDK_PORT
    if (frame == NULL || !SIM_Battle3D_IsEnabled()) {
        return;
    }
    if (SIM_Battle3D_SetFrame != NULL) {
        SIM_Battle3D_SetFrame(frame);
    }
#else
    (void)frame;
#endif
}

void SIM_Battle3D_Reset(void)
{
#ifdef SDK_PORT
    if (SIM_Battle3D_Clear != NULL) {
        SIM_Battle3D_Clear();
    }
#endif
}

int SIM_Battle3D_BiomeFromBackground(int background)
{
    switch (background) {
    case BACKGROUND_PLAIN:
        return SIM_BATTLE3D_BIOME_PLAIN;
    case BACKGROUND_FOREST:
        return SIM_BATTLE3D_BIOME_FOREST;
    case BACKGROUND_WATER:
        return SIM_BATTLE3D_BIOME_WATER;
    case BACKGROUND_MOUNTAIN:
    case BACKGROUND_CAVE_1:
    case BACKGROUND_CAVE_2:
    case BACKGROUND_CAVE_3:
        return SIM_BATTLE3D_BIOME_CAVE;
    case BACKGROUND_SNOW:
        return SIM_BATTLE3D_BIOME_SNOW;
    case BACKGROUND_CITY:
        return SIM_BATTLE3D_BIOME_CITY;
    case BACKGROUND_INDOORS_1:
    case BACKGROUND_INDOORS_2:
    case BACKGROUND_INDOORS_3:
    case BACKGROUND_AARON:
    case BACKGROUND_BERTHA:
    case BACKGROUND_FLINT:
    case BACKGROUND_LUCIAN:
    case BACKGROUND_CYNTHIA:
    case BACKGROUND_BATTLE_TOWER:
    case BACKGROUND_BATTLE_FACTORY:
    case BACKGROUND_BATTLE_ARCADE:
    case BACKGROUND_BATTLE_CASTLE:
    case BACKGROUND_BATTLE_HALL:
        return SIM_BATTLE3D_BIOME_INDOORS;
    case BACKGROUND_DISTORTION_WORLD:
        return SIM_BATTLE3D_BIOME_DISTORTION;
    default:
        return SIM_BATTLE3D_BIOME_PLAIN;
    }
}

BOOL SIM_Battle3D_ModelsEnabled(void)
{
#ifdef SDK_PORT
    if (!SIM_Battle3D_IsEnabled()) {
        return FALSE;
    }
    {
        const char *env = getenv("SIM_FX_BDSP_MODELS");
        if (env != NULL) {
            if (env[0] == '0') {
                return FALSE;
            }
            if (env[0] == '1') {
                return TRUE;
            }
        }
        if (SIM_Headless_Enabled()) {
            return FALSE;
        }
        {
            SIM_Config_prj_type *cfg = SIM_Config_prj_GetConfig();
            return (cfg != NULL) ? cfg->battleModels3d : TRUE;
        }
    }
#else
    return FALSE;
#endif
}

BOOL SIM_Battle3D_HasModelLoaded(int species, int form, int isShiny)
{
#ifdef SDK_PORT
    if (!SIM_Battle3D_ModelsEnabled() || species <= 0) {
        return FALSE;
    }
    return SIM_Battle3D_HasModel(species, form, isShiny) ? TRUE : FALSE;
#else
    (void)species;
    (void)form;
    (void)isShiny;
    return FALSE;
#endif
}

BOOL SIM_Battle3D_HasArenaLoaded(int biome)
{
#ifdef SDK_PORT
    if (!SIM_Battle3D_ModelsEnabled()) {
        return FALSE;
    }
    return SIM_Battle3D_HasArena(biome) ? TRUE : FALSE;
#else
    (void)biome;
    return FALSE;
#endif
}

BOOL SIM_Battle3D_HasActorLoaded(int kind)
{
#ifdef SDK_PORT
    if (!SIM_Battle3D_ModelsEnabled() || kind <= 0) {
        return FALSE;
    }
    return SIM_Battle3D_HasActor(kind) ? TRUE : FALSE;
#else
    (void)kind;
    return FALSE;
#endif
}
