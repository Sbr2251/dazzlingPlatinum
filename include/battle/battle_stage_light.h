#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_LIGHT_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_LIGHT_H

#include <nitro.h>

#include "struct_decls/battle_system.h"

#include "battle/battle_stage_format.h"

// Arena light and fog picked once at battle start (bw2vis:stage-light). As in BW2
// (btlv_effect.c, field_light_status.c), the light follows the RTC hour and minute and the
// field weather at the start of the battle and does not change during it. See
// docs/living_battle_stage/stage_format.md, "Time of day and weather".

// The lighting and fog the renderer uses for the whole battle
typedef struct BattleStageLight {
    BattleStageFileLighting lighting;
    BOOL fogEnabled;
    u8 fogShift;
    u16 fogOffset;
    u8 fogTable[32];
} BattleStageLight;

enum BattleStageLightClock {
    BATTLE_STAGE_LIGHT_CLOCK_RTC = 0, // the RTC hour and minute
    BATTLE_STAGE_LIGHT_CLOCK_FORCED, // the time of day was forced (launcher): its representative minute
    BATTLE_STAGE_LIGHT_CLOCK_FIXED, // a background without time of day or weather (indoors, caves, ...)
};

#define BATTLE_STAGE_LIGHT_DEBUG_MAGIC 0x544C5342 // "BSLT"

// sBattleStageLightDebug, read by the stage-light probes from RAM through the xMAP. Zeroed
// with the overlay's .bss, written when the arena loads
typedef struct BattleStageLightDebug {
    u32 magic; // +0 BATTLE_STAGE_LIGHT_DEBUG_MAGIC once resolved
    u16 minute; // +4 minute of the day the lighting was taken at (0..1439)
    u8 clock; // +6 enum BattleStageLightClock
    u8 weatherColumn; // +7 enum BattleStageLightingColumn, 0 = no weather
    s32 fieldWeather; // +8 OVERWORLD_WEATHER_* of the battle
    u16 todWeight[BATTLE_STAGE_LIGHTING_TOD_COUNT]; // +12 per time-of-day column, sum 256
    u16 weatherWeight; // +22 0..256
    BattleStageFileLighting lighting; // +24 the result (20 bytes)
    u8 fogShift; // +44
    u8 haze; // +45
    u16 fogOffset; // +46
} BattleStageLightDebug;

void BattleStageLight_Resolve(BattleSystem *battleSys, const BattleStageFileAtmosphere *atmosphere, BattleStageLight *out);

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_LIGHT_H
