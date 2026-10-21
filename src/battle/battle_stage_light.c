#include "battle/battle_stage_light.h"

#include <nitro.h>
#include <stddef.h>
#include <string.h>

#include "config/battle_stage.h"
#include "constants/rtc.h"
#include "generated/battle_backgrounds.h"

#include "battle/ov16_0223DF00.h"

#include "field_battle_data_transfer.h"
#include "rtc.h"

// bw2vis:stage-light. BW2 lights its battle stage with the colour the field light of the zone
// has at the battle's hour and minute (15 settings a day, res/lighting/battle/*.json of
// pokebw2); it reads it once, in BtlvEffect_Init (pokebw2 src/ov168/btlv_effect.c:289-300,
// src/system/field_light_status.c). Here the clock blends the atmosphere's lighting columns
// with a keyframed schedule over the day (the minute times follow BW2's spring table:
// morning 5:00, day 10:00, evening 17:00, night 20:00). Only the six outdoor backgrounds that have
// time-of-day palettes (ov16_0223EC04) take part; indoor, cave, Distortion World and facility
// backgrounds keep column 0, as BW2's indoor bgTypes have no zone light.

#define WEIGHT_ONE        256
#define MINUTES_PER_DAY   (24 * 60)
#define TOD_COUNT         BATTLE_STAGE_LIGHTING_TOD_COUNT
#define HM(hour, minute)  ((hour) * 60 + (minute))

enum {
    D = BATTLE_STAGE_LIGHTING_DAY,
    T = BATTLE_STAGE_LIGHTING_TWILIGHT,
    N = BATTLE_STAGE_LIGHTING_NIGHT,
    M = BATTLE_STAGE_LIGHTING_MORNING,
    K = BATTLE_STAGE_LIGHTING_DUSK,
};

// A key of the day: the weight (of WEIGHT_ONE) of each time-of-day column at that minute.
// Between keys the weights are linear. The classic BG palettes step at 4:00 (night -> day),
// 17:00 (twilight) and 20:00 (night); the keys at those minutes land on the column made for
// that palette, so each palette stretch blends smoothly and the steps stay where they were.
typedef struct LightKey {
    u16 minute;
    u16 weight[TOD_COUNT]; // D, T, N, M, K
} LightKey;

static const LightKey sLightKeys[] = {
    { HM(0, 0), { 0, 0, 256, 0, 0 } },
    { HM(4, 0), { 0, 0, 256, 0, 0 } }, // BW2 night until 5:00 (11,11,16)
    { HM(6, 0), { 0, 0, 0, 256, 0 } }, // dawn blue, BW2 6:00 (12,12,22)
    { HM(9, 0), { 0, 0, 0, 256, 0 } }, // morning blue, BW2 9:00 (15,15,22)
    { HM(12, 0), { 256, 0, 0, 0, 0 } }, // day, BW2 12:00 (22,22,20)
    { HM(15, 30), { 256, 0, 0, 0, 0 } }, // noon, BW2 15:30 (24,24,20)
    { HM(17, 0), { 0, 256, 0, 0, 0 } }, // twilight palette from here, BW2 17:00 (20,18,16)
    { HM(18, 30), { 0, 0, 0, 0, 256 } }, // dusk orange, BW2 18:30 (17,13,10)
    { HM(20, 0), { 0, 0, 128, 0, 128 } }, // night palette from here, BW2 20:00 (16,13,10)
    { HM(21, 0), { 0, 0, 256, 0, 0 } }, // BW2 21:00 (11,12,15)
    { HM(24, 0), { 0, 0, 256, 0, 0 } },
};

BattleStageLightDebug sBattleStageLightDebug;

// The representative minute of a time of day forced by the launcher: a pure column, so the
// forced battles light exactly as before (stage_ab, all_backgrounds)
static int ForcedMinute(enum TimeOfDay timeOfDay)
{
    switch (timeOfDay) {
    case TIMEOFDAY_MORNING:
        return HM(9, 0);
    case TIMEOFDAY_DAY:
        return HM(12, 0);
    case TIMEOFDAY_TWILIGHT:
        return HM(17, 0);
    default:
        return HM(23, 0);
    }
}

static BOOL HasTimeOfDay(enum BattleBackground background)
{
    switch (background) {
    case BACKGROUND_PLAIN:
    case BACKGROUND_WATER:
    case BACKGROUND_CITY:
    case BACKGROUND_FOREST:
    case BACKGROUND_MOUNTAIN:
    case BACKGROUND_SNOW:
        return TRUE;
    default:
        return FALSE;
    }
}

// Weights of the time-of-day columns at a minute of the day; they sum to WEIGHT_ONE
static void ScheduleWeights(int minute, u16 *weight)
{
    const LightKey *a = &sLightKeys[0], *b = &sLightKeys[1];
    int i, t, total, largest;

    for (i = 1; i < (int)NELEMS(sLightKeys); i++) {
        a = &sLightKeys[i - 1];
        b = &sLightKeys[i];

        if (minute < b->minute) {
            break;
        }
    }

    t = (minute - a->minute) * WEIGHT_ONE / (b->minute - a->minute);
    total = 0;
    largest = 0;

    for (i = 0; i < TOD_COUNT; i++) {
        weight[i] = (a->weight[i] * (WEIGHT_ONE - t) + b->weight[i] * t + WEIGHT_ONE / 2) / WEIGHT_ONE;
        total += weight[i];

        if (weight[i] > weight[largest]) {
            largest = i;
        }
    }

    weight[largest] += WEIGHT_ONE - total;
}

static int Channel(u16 color, int shift)
{
    return (color >> shift) & 31;
}

static u16 BlendColors(const BattleStageFileLighting *columns, const u16 *weight, int offset)
{
    int c, i, value;
    u16 result = 0;

    for (c = 0; c < 3; c++) {
        value = 0;

        for (i = 0; i < TOD_COUNT; i++) {
            value += weight[i] * Channel(*(const u16 *)((const u8 *)&columns[i] + offset), c * 5);
        }

        result |= ((value + WEIGHT_ONE / 2) / WEIGHT_ONE) << (c * 5);
    }

    return result;
}

#define LIGHTING_COLOR_OFFSET(field) offsetof(BattleStageFileLighting, field)

void BattleStageLight_Resolve(BattleSystem *battleSys, const BattleStageFileAtmosphere *atmosphere, BattleStageLight *out)
{
    BattleStageLightDebug *debug = &sBattleStageLightDebug;
    BattleStageFileLighting lighting;
    enum BattleBackground background = BattleSystem_Background(battleSys);
    enum TimeOfDay timeOfDay = BattleSystem_Time(battleSys);
    int fieldWeather = BattleSystem_FieldWeather(battleSys);
    u16 weight[TOD_COUNT];
    int minute, clock, i;

    memset(debug, 0, sizeof(*debug));
    memset(weight, 0, sizeof(weight));

    if (HasTimeOfDay(background)) {
        RTCTime time;
        BOOL forced = FALSE;

        RTC_GetCurrentTime(&time);
#if DEBUG_BATTLE_TOOLS
        forced = FieldBattleDTO_DebugTimeOfDayForced();
#endif
        // A time of day that does not match the clock's hour came from elsewhere (the
        // launcher, or a battle set up from the saved game time): its representative minute
        if (forced || TimeOfDayForHour(time.hour) != timeOfDay) {
            minute = ForcedMinute(timeOfDay);
            clock = BATTLE_STAGE_LIGHT_CLOCK_FORCED;
        } else {
            minute = HM(time.hour, time.minute);
            clock = BATTLE_STAGE_LIGHT_CLOCK_RTC;
        }

        ScheduleWeights(minute, weight);
    } else {
        minute = 0;
        clock = BATTLE_STAGE_LIGHT_CLOCK_FIXED;
        weight[BATTLE_STAGE_LIGHTING_DAY] = WEIGHT_ONE;
    }

    // Light 0's direction is the same in every column
    lighting = atmosphere->lighting[BATTLE_STAGE_LIGHTING_DAY];
    lighting.lightColor = BlendColors(atmosphere->lighting, weight, LIGHTING_COLOR_OFFSET(lightColor));
    lighting.diffuse = BlendColors(atmosphere->lighting, weight, LIGHTING_COLOR_OFFSET(diffuse));
    lighting.ambient = BlendColors(atmosphere->lighting, weight, LIGHTING_COLOR_OFFSET(ambient));
    lighting.emission = BlendColors(atmosphere->lighting, weight, LIGHTING_COLOR_OFFSET(emission));
    // The fog colour blends with the same weights, so fog and light stay in step
    lighting.fogColor = BlendColors(atmosphere->lighting, weight, LIGHTING_COLOR_OFFSET(fogColor));

    {
        int alpha = 0;

        for (i = 0; i < TOD_COUNT; i++) {
            alpha += weight[i] * atmosphere->lighting[i].fogAlpha;
        }

        lighting.fogAlpha = (alpha + WEIGHT_ONE / 2) / WEIGHT_ONE;
    }

    out->lighting = lighting;
    out->fogEnabled = atmosphere->fogEnabled;

    out->fogShift = atmosphere->fogShift;
    out->fogOffset = atmosphere->fogOffset;
    memcpy(out->fogTable, atmosphere->fogTable, sizeof(out->fogTable));

    debug->minute = minute;
    debug->clock = clock;
    debug->fieldWeather = fieldWeather;
    memcpy(debug->todWeight, weight, sizeof(weight));
    debug->lighting = lighting;
    debug->fogShift = out->fogShift;
    debug->fogOffset = out->fogOffset;
    debug->magic = BATTLE_STAGE_LIGHT_DEBUG_MAGIC;
}
