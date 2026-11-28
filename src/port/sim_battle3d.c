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
__attribute__((weak)) int SIM_Battle3D_GetActorBonePos(int actorIdx, int boneKind, float outPos[3])
{
    (void)actorIdx;
    (void)boneKind;
    (void)outPos;
    return 0;
}
__attribute__((weak)) int SIM_Battle3D_GetModelBounds(int species, int form, int isShiny, float outMin[3], float outMax[3])
{
    (void)species;
    (void)form;
    (void)isShiny;
    (void)outMin;
    (void)outMax;
    return 0;
}
__attribute__((weak)) int SIM_Battle3D_IsModelReady(int species, int form, int isShiny)
{
    return SIM_Battle3D_HasModel(species, form, isShiny);
}
__attribute__((weak)) int SIM_Battle3D_GetActorSocketPos(int actorIdx, int boneKind, int expectedNonce,
    float minAnimTime, const float localOffset[3], float outPos[3])
{
    (void)actorIdx;
    (void)boneKind;
    (void)expectedNonce;
    (void)minAnimTime;
    (void)localOffset;
    (void)outPos;
    return 0;
}
__attribute__((weak)) float SIM_Battle3D_GetClipDuration(int species, int form, int isShiny, int animState)
{
    (void)species;
    (void)form;
    (void)isShiny;
    (void)animState;
    return 0.0f;
}
#endif

#ifdef SDK_PORT
static BOOL sEnvCacheValid = FALSE;
static BOOL sEnvHeadless = FALSE;
static BOOL sEnvBattleAllowed = FALSE;
static int sEnvModelsOverride = -1; // -1 = unset, 0 = forced off, 1 = forced on

static void RefreshEnvCache(void)
{
    const char *bdsp = getenv("SIM_FX_BDSP_BATTLE");
    const char *interactive = getenv("SIM_HEADLESS_INTERACTIVE_FX");
    const char *models = getenv("SIM_FX_BDSP_MODELS");

    sEnvHeadless = SIM_Headless_Enabled() ? TRUE : FALSE;
    if (!sEnvHeadless) {
        sEnvBattleAllowed = (bdsp != NULL && bdsp[0] == '0') ? FALSE : TRUE;
    } else if (bdsp != NULL && bdsp[0] == '0') {
        sEnvBattleAllowed = FALSE;
    } else if ((bdsp != NULL && bdsp[0] == '1') || (interactive != NULL && interactive[0] == '1')) {
        sEnvBattleAllowed = TRUE;
    } else {
        sEnvBattleAllowed = FALSE;
    }

    if (models != NULL) {
        if (models[0] == '0') {
            sEnvModelsOverride = 0;
        } else if (models[0] == '1') {
            sEnvModelsOverride = 1;
        } else {
            sEnvModelsOverride = -1;
        }
    } else {
        sEnvModelsOverride = -1;
    }

    sEnvCacheValid = TRUE;
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

    if (!sEnvCacheValid) {
        RefreshEnvCache();
    }
    return sEnvBattleAllowed;
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
    sEnvCacheValid = FALSE;
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
    if (!sEnvCacheValid) {
        RefreshEnvCache();
    }
    if (sEnvModelsOverride == 0) {
        return FALSE;
    }
    if (sEnvModelsOverride == 1) {
        return TRUE;
    }
    if (sEnvHeadless) {
        return FALSE;
    }
    {
        SIM_Config_prj_type *cfg = SIM_Config_prj_GetConfig();
        return (cfg != NULL) ? cfg->battleModels3d : TRUE;
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
    return SIM_Battle3D_HasModel(species, SIM_Battle3D_NormalizeForm(species, form), isShiny) ? TRUE : FALSE;
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

BOOL SIM_Battle3D_GetActorHandPos(int actorIdx, int boneKind, float outPos[3])
{
#ifdef SDK_PORT
    if (!SIM_Battle3D_ModelsEnabled() || outPos == NULL) {
        return FALSE;
    }
    return SIM_Battle3D_GetActorBonePos(actorIdx, boneKind, outPos) ? TRUE : FALSE;
#else
    (void)actorIdx;
    (void)boneKind;
    (void)outPos;
    return FALSE;
#endif
}

BOOL SIM_Battle3D_GetActorSocketWorldPos(int actorIdx, int boneKind, int expectedNonce,
    float minAnimTime, const float localOffset[3], float outPos[3])
{
#ifdef SDK_PORT
    if (!SIM_Battle3D_ModelsEnabled() || outPos == NULL) {
        return FALSE;
    }
    return SIM_Battle3D_GetActorSocketPos(actorIdx, boneKind, expectedNonce, minAnimTime, localOffset, outPos) ? TRUE : FALSE;
#else
    (void)actorIdx;
    (void)boneKind;
    (void)expectedNonce;
    (void)minAnimTime;
    (void)localOffset;
    (void)outPos;
    return FALSE;
#endif
}

float SIM_Battle3D_GetModelClipDuration(int species, int form, int isShiny, int animState)
{
#ifdef SDK_PORT
    if (!SIM_Battle3D_ModelsEnabled() || species <= 0) {
        return 0.0f;
    }
    return SIM_Battle3D_GetClipDuration(species, SIM_Battle3D_NormalizeForm(species, form), isShiny, animState);
#else
    (void)species;
    (void)form;
    (void)isShiny;
    (void)animState;
    return 0.0f;
#endif
}

int SIM_Battle3D_NormalizeForm(int species, int form)
{
    // Opus B4: Platinum uses TYPE_* for Arceus (493) where TYPE_MYSTERY = 9 shifts
    // Fire..Dark to 10..17, whereas BDSP stores national order (0=Normal, 9=Fire..17=Fairy).
    if (species == 493) {
        if (form == 9) {
            return 0;
        }
        if (form > 9) {
            return form - 1;
        }
    }
    return form;
}

BOOL SIM_Battle3D_GetModelBBox(int species, int form, int isShiny, float outMin[3], float outMax[3])
{
#ifdef SDK_PORT
    if (!SIM_Battle3D_ModelsEnabled() || species <= 0 || outMin == NULL || outMax == NULL) {
        return FALSE;
    }
    return SIM_Battle3D_GetModelBounds(species, SIM_Battle3D_NormalizeForm(species, form), isShiny, outMin, outMax) ? TRUE : FALSE;
#else
    (void)species; (void)form; (void)isShiny; (void)outMin; (void)outMax;
    return FALSE;
#endif
}

BOOL SIM_Battle3D_IsModelRenderReady(int species, int form, int isShiny)
{
#ifdef SDK_PORT
    if (!SIM_Battle3D_ModelsEnabled() || species <= 0) {
        return FALSE;
    }
    return SIM_Battle3D_IsModelReady(species, SIM_Battle3D_NormalizeForm(species, form), isShiny) ? TRUE : FALSE;
#else
    (void)species; (void)form; (void)isShiny;
    return FALSE;
#endif
}
