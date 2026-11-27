#include <nitro.h>
#include <stdlib.h>
#include <simulator/config/ini.h>

#include "port/sim_config_prj.h"
#include <simulator/sim_platform.h> // ios-platform hook

#ifdef SDK_BUILD_PROSPERO
#define SIM_CONFIG_PRJ_FILE_PATH "/app0/sim_config_prj.ini"
#else
#define SIM_CONFIG_PRJ_FILE_PATH SIM_Platform_ConfigPrjPath() // ios-platform hook
#endif

static int IniHandler(void* user, const char* section, const char* name,
                   const char* value);
static const char * BoolToString(BOOL arg);
static BOOL StringToBool(const char * str);
static BOOL SIM_Config_prj_EnvIsSet(const char *name); // perf-game-cache hook

static SIM_Config_prj_type s_SIM_config_prj;

static int IniHandler(void* user, const char* section, const char* name,
                   const char* value)
{
    #define MATCH(s, n) strcmp(section, s) == 0 && strcmp(name, n) == 0

    SIM_Config_prj_type * config = (SIM_Config_prj_type *)user;

    // General section
    if(MATCH("General", "60Fps")) {
        config->enable60fps = StringToBool(value);
    }
    if(MATCH("General", "60FpsSpeedFix")) {
        config->enable60fpsSpeedFix = StringToBool(value);
    }
    if(MATCH("General", "EnableAsserts")) {
        config->enableAsserts = StringToBool(value);
    }
    if(MATCH("General", "MegaCinematicShort")) {
        config->megaCinematicShort = StringToBool(value);
    }
    if(MATCH("General", "HiResText")) {
        config->hiResText = StringToBool(value);
    }
    if(MATCH("General", "ArenaContext")) {
        config->arenaContext = StringToBool(value);
    }
    if(MATCH("General", "WeatherLightning")) {
        config->weatherLightning = StringToBool(value);
    }
    if(MATCH("General", "WeatherFx")) {
        config->weatherFx = StringToBool(value);
    }
    if(MATCH("General", "WaterReflections")) {
        config->waterReflections = StringToBool(value);
    }
    if(MATCH("General", "SceneLights")) {
        config->sceneLights = StringToBool(value);
    }
    if(MATCH("General", "SpriteRimLight")) {
        config->spriteRimLight = StringToBool(value);
    }
    if(MATCH("General", "OverworldCinematics")) {
        config->overworldCinematics = StringToBool(value);
    }
    if(MATCH("General", "ParticleBoost")) {
        config->particleBoost = StringToBool(value);
    }
    if(MATCH("General", "ParticleBoostDensity")) {
        config->particleBoostDensity = atoi(value);
    }

    // Cheats section
    if(MATCH("Cheats", "WalkThroughWalls")) {
        config->walkThroughWalls = StringToBool(value);
    }

    if(MATCH("Cheats", "DisableRandomEncounters")) {
        config->disableRandomEncounters = StringToBool(value);
    }

    if(MATCH("General", "BattleInstantAnimations")) {
        config->battleInstantAnimations = StringToBool(value);
    }
    if(MATCH("General", "BattleFastPacing")) { // perf-game-cache hook
        config->battleFastPacing = StringToBool(value);
    }
    if(MATCH("General", "FieldFastRebuild")) {
        config->fieldFastRebuild = StringToBool(value);
    }
    if(MATCH("General", "FieldLoadRadius")) {
        config->fieldLoadRadius = atoi(value);
    }
    if(MATCH("General", "BattleHud")) {
        config->battleHud = StringToBool(value);
    }
    if(MATCH("General", "BattleHudStyle")) {
        config->battleHudStyleHd = (strcmp(value, "pixel") != 0 && strcmp(value, "PIXEL") != 0) ? TRUE : FALSE;
    }
    if(MATCH("General", "BattleSpriteSizing")) {
        config->battleSpriteSizingHeight = (strcmp(value, "classic") != 0 && strcmp(value, "false") != 0);
    }
    if(MATCH("General", "FollowerEnabled")) {
        config->followerEnabled = StringToBool(value);
    }
    if(MATCH("General", "PhenomenaEnabled")) {
        config->phenomenaEnabled = StringToBool(value);
    }
    if(MATCH("General", "DebugWideCamera")) {
        config->debugWideCamera = StringToBool(value);
    }
    if(MATCH("Cheats", "RunFromTrainerBattles")) {
        config->runFromTrainerBattles = StringToBool(value);
    }
}

static const char * BoolToString(BOOL arg)
{
    const char * ret = "false";
    if(arg) {
        ret = "true";
    }

    return ret;
}

static BOOL StringToBool(const char * str)
{
    BOOL ret = FALSE;

    if(strcmp(str, "false") == 0) {
        ret = FALSE;
    } else if(strcmp(str, "true") == 0) {
        ret = TRUE;
    }
    return ret;
}

// Initialize a SIM_Config_prj_type to default values
void SIM_Config_prj_LoadDefaults(SIM_Config_prj_type * aConfig)
{
  aConfig->enable60fps = TRUE;
  aConfig->enable60fpsSpeedFix = TRUE;
  aConfig->enableAsserts = FALSE;
  aConfig->battleInstantAnimations = FALSE;
  aConfig->battleFastPacing = FALSE; // perf-game-cache hook: preserve classic/headless pacing by default
  aConfig->fieldFastRebuild = TRUE;
  aConfig->breakDebuggerOnGfAssert = FALSE;
  aConfig->megaCinematicShort = FALSE;
  aConfig->hiResText = FALSE;
  aConfig->arenaContext = TRUE;
  aConfig->weatherLightning = TRUE;
  aConfig->sceneLights = TRUE;
  aConfig->spriteRimLight = TRUE;
  aConfig->overworldCinematics = TRUE;
  aConfig->weatherFx = TRUE;
  // Screen-space blue-color water mask false-positives on blue roofs (Poke Mart),
  // player/NPC blue outfits, and night-tinted fences; keep off by default until
  // replaced with a true terrain/material water mask (still opt-in via INI / SIM_FX_WATER=1).
  aConfig->waterReflections = FALSE;
  aConfig->particleBoost = TRUE;
  aConfig->particleBoostDensity = 3;
  aConfig->fieldLoadRadius = 3;
  aConfig->debugWideCamera = FALSE;
  aConfig->battleHud = TRUE;
  aConfig->battleHudStyleHd = TRUE;
  aConfig->battleSpriteSizingHeight = TRUE;
  aConfig->followerEnabled = TRUE;
  aConfig->phenomenaEnabled = TRUE;

  // Cheats section
  aConfig->walkThroughWalls = FALSE;
}

// Loads the configuration file. If it does not exist, return false
BOOL SIM_Config_prj_LoadConfigFile(SIM_Config_prj_type * aConfig)
{
    return (ini_parse(SIM_CONFIG_PRJ_FILE_PATH, IniHandler, aConfig) >= 0);
}

// Save a SIM_Config_prj_type to the configuration file
void SIM_Config_prj_SaveConfigFile(SIM_Config_prj_type * aConfig)
{
    FILE * configFile = fopen(SIM_CONFIG_PRJ_FILE_PATH, "w");
    
    fprintf(configFile, "[General]\n");
    fprintf(configFile, "60Fps=%s\n", BoolToString(aConfig->enable60fps));
    fprintf(configFile, "60FpsSpeedFix=%s\n", BoolToString(aConfig->enable60fpsSpeedFix));
    fprintf(configFile, "EnableAsserts=%s\n", BoolToString(aConfig->enableAsserts));
    fprintf(configFile, "BreakDebuggerOnAssert=%s\n", BoolToString(aConfig->breakDebuggerOnGfAssert));
    fprintf(configFile, "BattleInstantAnimations=%s\n", BoolToString(aConfig->battleInstantAnimations));
    fprintf(configFile, "BattleFastPacing=%s\n", BoolToString(aConfig->battleFastPacing)); // perf-game-cache hook
    fprintf(configFile, "FieldFastRebuild=%s\n", BoolToString(aConfig->fieldFastRebuild));
    fprintf(configFile, "MegaCinematicShort=%s\n", BoolToString(aConfig->megaCinematicShort));
    fprintf(configFile, "HiResText=%s\n", BoolToString(aConfig->hiResText));
    fprintf(configFile, "ArenaContext=%s\n", BoolToString(aConfig->arenaContext));
    fprintf(configFile, "WeatherLightning=%s\n", BoolToString(aConfig->weatherLightning));
    fprintf(configFile, "SceneLights=%s\n", BoolToString(aConfig->sceneLights));
    fprintf(configFile, "SpriteRimLight=%s\n", BoolToString(aConfig->spriteRimLight));
    fprintf(configFile, "OverworldCinematics=%s\n", BoolToString(aConfig->overworldCinematics));
    fprintf(configFile, "WeatherFx=%s\n", BoolToString(aConfig->weatherFx));
    fprintf(configFile, "WaterReflections=%s\n", BoolToString(aConfig->waterReflections));
    fprintf(configFile, "ParticleBoost=%s\n", BoolToString(aConfig->particleBoost));
    fprintf(configFile, "ParticleBoostDensity=%d\n", aConfig->particleBoostDensity);
    fprintf(configFile, "FieldLoadRadius=%d\n", aConfig->fieldLoadRadius);
    fprintf(configFile, "DebugWideCamera=%s\n", BoolToString(aConfig->debugWideCamera));
    fprintf(configFile, "BattleHud=%s\n", BoolToString(aConfig->battleHud));
    fprintf(configFile, "BattleHudStyle=%s\n", aConfig->battleHudStyleHd ? "hd" : "pixel");
    fprintf(configFile, "BattleSpriteSizing=%s\n", aConfig->battleSpriteSizingHeight ? "height" : "classic");
    fprintf(configFile, "FollowerEnabled=%s\n", BoolToString(aConfig->followerEnabled));
    fprintf(configFile, "PhenomenaEnabled=%s\n", BoolToString(aConfig->phenomenaEnabled));
    fprintf(configFile, "\n");

    fprintf(configFile, "[Cheats]\n");
    fprintf(configFile, "WalkThroughWalls=%s\n", BoolToString(aConfig->walkThroughWalls));
    fprintf(configFile, "DisableRandomEncounters=%s\n", BoolToString(aConfig->disableRandomEncounters));
    fprintf(configFile, "RunFromTrainerBattles=%s\n", BoolToString(aConfig->runFromTrainerBattles));

    fclose(configFile);
}

void SIM_Config_prj_init() {
  //Load default config
  SIM_Config_prj_LoadDefaults(&s_SIM_config_prj);
  
  //Load configuration file
  if(!SIM_Config_prj_LoadConfigFile(&s_SIM_config_prj)){
    //Config file does not exist. Save config file with defaults
    SIM_Config_prj_SaveConfigFile(&s_SIM_config_prj);
  }
}

SIM_Config_prj_type * SIM_Config_prj_GetConfig()
{
  return &s_SIM_config_prj;
}

BOOL SIM_Config_prj_DoubleStep(void)
{
  return s_SIM_config_prj.enable60fps && s_SIM_config_prj.enable60fpsSpeedFix;
}

BOOL SIM_Config_prj_BattleFastPacing(void) // perf-game-cache hook
{
    // Automation and replay goldens retain the exact classic frame counts even
    // when a developer's interactive config enables fast pacing.
    if (SIM_Config_prj_EnvIsSet("SIM_HEADLESS") || SIM_Config_prj_EnvIsSet("SIM_CONTROL")) {
        return FALSE;
    }

    return s_SIM_config_prj.battleFastPacing;
}

static BOOL SIM_Config_prj_EnvIsSet(const char *name)
{
    const char *value = getenv(name);
    return value != NULL && value[0] == '1';
}

int SIM_Config_prj_FieldLoadRadius(void)
{
    int radius = s_SIM_config_prj.fieldLoadRadius;

    if (radius < 2) {
        radius = 2;
    }

    if (radius > 3) {
        radius = 3;
    }

    if (SIM_Config_prj_EnvIsSet("SIM_HEADLESS") && !SIM_Config_prj_EnvIsSet("SIM_FX_WIDE")) {
        return 2;
    }

    return radius;
}

BOOL SIM_Config_prj_DebugWideCamera(void)
{
    if (SIM_Config_prj_EnvIsSet("SIM_FX_WIDE_CAMERA")) {
        return TRUE;
    }

    if (SIM_Config_prj_EnvIsSet("SIM_HEADLESS")) {
        return FALSE;
    }

    return s_SIM_config_prj.debugWideCamera;
}

BOOL SIM_Config_prj_FollowerEnabled(void)
{
    const char *env = getenv("SIM_FX_FOLLOWER");
    if (env != NULL) {
        if (env[0] == '0') {
            return FALSE;
        }
        if (env[0] == '1') {
            return s_SIM_config_prj.followerEnabled;
        }
    }

    if (SIM_Config_prj_EnvIsSet("SIM_HEADLESS") || getenv("SIM_CONTROL") != NULL) {
        return FALSE;
    }

    return s_SIM_config_prj.followerEnabled;
}

BOOL SIM_Config_prj_PhenomenaEnabled(void)
{
    const char *env = getenv("SIM_FX_PHENOMENA");
    if (env != NULL) {
        if (env[0] == '0') {
            return FALSE;
        }
        if (env[0] == '1') {
            return s_SIM_config_prj.phenomenaEnabled;
        }
    }

    if (SIM_Config_prj_EnvIsSet("SIM_HEADLESS") || getenv("SIM_CONTROL") != NULL) {
        return FALSE;
    }

    return s_SIM_config_prj.phenomenaEnabled;
}
