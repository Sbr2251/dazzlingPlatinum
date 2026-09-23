#include "overlay005/area_light.h"

#include <nitro.h>
#include <string.h>

#include "constants/graphics.h"
#include "constants/heap.h"
#include "constants/narc.h"

#include "overlay005/model_attributes.h"

#include "ascii_util.h"
#include "graphics.h"
#include "heap.h"
#include "math_util.h"
#include "rtc.h"

#define AREA_LIGHT_FILE_COUNT 5
#define SCRATCH_BUFFER_SIZE   256
#define INVALID_LIGHT_COLOR   0xFFFF

// Mt. Coronet 1F South's lava light flickers like firelight: two layered sines, 0.7 s and 1.9 s
#define AREA_LIGHT_LAVA          4
#define FLICKER_PERIOD_FAST      42
#define FLICKER_PERIOD_SLOW      114
#define FLICKER_LIGHT_RED        2
#define FLICKER_LIGHT_GREEN      1
#define FLICKER_EMISSION_RED     1

static void AreaLightManager_ApplyActiveTemplateToAreaModelAttrs(AreaLightManager *areaLightMan);
static void AreaLightManager_Flicker(AreaLightManager *areaLightMan);
static u32 AreaLightTemplate_New(u32 archiveID, AreaLightTemplate **templates);
static void AreaLightTemplate_Free(AreaLightTemplate **template);
static char *AreaLightTemplate_ParseLightAttrs(char *fileIter, GXRgb *lightColor, VecFx16 *lightVector);
static char *AreaLightTemplate_ParseColor(char *fileIter, GXRgb *color);

AreaLightManager *AreaLightManager_New(ModelAttributes *areaModelAttrs, const u8 archiveID)
{
    GF_ASSERT(archiveID < AREA_LIGHT_FILE_COUNT);

    AreaLightManager *areaLightMan = Heap_Alloc(HEAP_ID_FIELD1, sizeof(AreaLightManager));

    areaLightMan->areaModelAttrs = areaModelAttrs;
    areaLightMan->templateCount = AreaLightTemplate_New(archiveID, &areaLightMan->templates);
    areaLightMan->activeTemplateIndex = 0;
    areaLightMan->flicker = archiveID == AREA_LIGHT_LAVA;
    areaLightMan->flickerFrame = 0;

    int currentTime = GetSecondsSinceMidnight() / 2;

    for (int i = 0; i < areaLightMan->templateCount; i++) {
        if (areaLightMan->templates[i].endTime > currentTime) {
            areaLightMan->activeTemplateIndex = i;
            break;
        }
    }

    areaLightMan->applyToAreaModelAttrs = TRUE;
    AreaLightManager_ApplyActiveTemplateToAreaModelAttrs(areaLightMan);

    return areaLightMan;
}

void AreaLightManager_Free(AreaLightManager **areaLightMan)
{
    GF_ASSERT(areaLightMan);

    AreaLightTemplate_Free(&(*areaLightMan)->templates);
    Heap_FreeExplicit(HEAP_ID_FIELD1, *areaLightMan);

    *areaLightMan = NULL;
}

void AreaLightManager_UpdateActiveTemplate(AreaLightManager *areaLightMan)
{
    GF_ASSERT(areaLightMan);

    int currentTime = GetSecondsSinceMidnight() / 2;

    if (areaLightMan->templateCount > 1) {
        int previousEndTime = areaLightMan->activeTemplateIndex - 1 >= 0
            ? areaLightMan->templates[areaLightMan->activeTemplateIndex - 1].endTime
            : 0;

        int activeEndTime = areaLightMan->templates[areaLightMan->activeTemplateIndex].endTime;

        if (currentTime >= activeEndTime || currentTime < previousEndTime) {
            areaLightMan->activeTemplateIndex++;

            if (areaLightMan->activeTemplateIndex >= areaLightMan->templateCount) {
                areaLightMan->activeTemplateIndex = 0;
            }

            if (areaLightMan->applyToAreaModelAttrs) {
                AreaLightManager_ApplyActiveTemplateToAreaModelAttrs(areaLightMan);
            }
        }
    }

    if (areaLightMan->flicker && areaLightMan->applyToAreaModelAttrs) {
        AreaLightManager_Flicker(areaLightMan);
    }
}

static GXRgb ShiftColor(GXRgb color, fx32 wave, int redAmplitude, int greenAmplitude)
{
    int r = ((color >> GX_RGB_R_SHIFT) & 31) + ((wave * redAmplitude + FX32_ONE / 2) >> FX32_SHIFT);
    int g = ((color >> GX_RGB_G_SHIFT) & 31) + ((wave * greenAmplitude + FX32_ONE / 2) >> FX32_SHIFT);
    int b = (color >> GX_RGB_B_SHIFT) & 31;

    return GX_RGB(MATH_CLAMP(r, 0, 31), MATH_CLAMP(g, 0, 31), b);
}

static void AreaLightManager_Flicker(AreaLightManager *areaLightMan)
{
    const AreaLightTemplate *template = &areaLightMan->templates[areaLightMan->activeTemplateIndex];
    u32 frame = areaLightMan->flickerFrame++;
    fx32 wave = CalcSineDegrees_Wraparound(frame % FLICKER_PERIOD_FAST * 360 / FLICKER_PERIOD_FAST) * 3 / 5
        + CalcSineDegrees_Wraparound(frame % FLICKER_PERIOD_SLOW * 360 / FLICKER_PERIOD_SLOW) * 2 / 5;

    if (template->validLightsMask & 1) {
        ModelAttributes_SetLightColor(areaLightMan->areaModelAttrs, 0, ShiftColor(template->lightColors[0], wave, FLICKER_LIGHT_RED, FLICKER_LIGHT_GREEN));
    }

    ModelAttributes_SetEmissionColor(areaLightMan->areaModelAttrs, ShiftColor(template->emissionColor, wave, FLICKER_EMISSION_RED, 0), TRUE);
}

void AreaLightTemplate_ApplyToModelAttributes(const AreaLightTemplate *template, ModelAttributes *modelAttrs)
{
    for (int i = 0; i < GX_LIGHTS_COUNT; i++) {
        int currentLightMask = (1 << i);

        if ((template->validLightsMask & currentLightMask) != 0) {
            ModelAttributes_SetLightVector(modelAttrs, i, template->lightVectors[i].x, template->lightVectors[i].y, template->lightVectors[i].z);
            ModelAttributes_SetLightColor(modelAttrs, i, template->lightColors[i]);
        } else {
            ModelAttributes_SetLightVector(modelAttrs, i, 0, 0, 0);
            ModelAttributes_SetLightColor(modelAttrs, i, GX_RGB(0, 0, 0));
        }
    }

    ModelAttributes_SetDiffuseReflection(modelAttrs, template->diffuseReflectColor, FALSE, FALSE);
    ModelAttributes_SetAmbientReflection(modelAttrs, template->ambientReflectColor, TRUE);
    ModelAttributes_SetSpecularReflection(modelAttrs, template->specularReflectColor, FALSE, FALSE);
    ModelAttributes_SetEmissionColor(modelAttrs, template->emissionColor, TRUE);
}

static void AreaLightManager_ApplyActiveTemplateToAreaModelAttrs(AreaLightManager *areaLightMan)
{
    AreaLightTemplate *activeTemplate = &areaLightMan->templates[areaLightMan->activeTemplateIndex];
    AreaLightTemplate_ApplyToModelAttributes(activeTemplate, areaLightMan->areaModelAttrs);
}

void AreaLight_UseGlobalModelAttributes(NNSG3dResMdl *model)
{
    NNS_G3dMdlUseGlbDiff(model);
    NNS_G3dMdlUseGlbAmb(model);
    NNS_G3dMdlUseGlbSpec(model);
    NNS_G3dMdlUseGlbEmi(model);
}

static u32 AreaLightTemplate_New(u32 archiveID, AreaLightTemplate **templates)
{
    int i, j;
    char lineBuffer[SCRATCH_BUFFER_SIZE];
    char endTimeBuffer[SCRATCH_BUFFER_SIZE];

    void *fileBuffer = LoadMemberFromNARC(NARC_INDEX_DATA__AREALIGHT, archiveID, FALSE, HEAP_ID_FIELD1, FALSE);
    void *fileIter = fileBuffer;
    int templateCount = 0;

    do {
        fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');

        if (!(lineBuffer[0] == 'E' && lineBuffer[1] == 'O' && lineBuffer[2] == 'F')) {
            fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');
            fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');
            fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');
            fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');
            fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');
            fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');
            fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');
            fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');
            fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');
            templateCount++;
        }
    } while (!(lineBuffer[0] == 'E' && lineBuffer[1] == 'O' && lineBuffer[2] == 'F'));

    *templates = Heap_Alloc(HEAP_ID_FIELD1, sizeof(AreaLightTemplate) * templateCount);
    MI_CpuClear8(*templates, sizeof(AreaLightTemplate) * templateCount);
    fileIter = fileBuffer;

    for (i = 0; i < templateCount; i++) {
        AreaLightTemplate *template = &(*templates)[i];
        fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');
        char *iter = lineBuffer;
        iter = Ascii_CopyToTerminator(iter, endTimeBuffer, ',');
        template->endTime = Ascii_ConvertToInt(endTimeBuffer);

        for (j = 0; j < GX_LIGHTS_COUNT; j++) {
            fileIter = AreaLightTemplate_ParseLightAttrs(fileIter, &template->lightColors[j], &template->lightVectors[j]);

            if (template->lightColors[j] != INVALID_LIGHT_COLOR) {
                template->validLightsMask |= 1 << j;
            } else {
                template->lightColors[j] = GX_RGB(0, 0, 0);
            }
        }

        fileIter = AreaLightTemplate_ParseColor(fileIter, &template->diffuseReflectColor);
        fileIter = AreaLightTemplate_ParseColor(fileIter, &template->ambientReflectColor);
        fileIter = AreaLightTemplate_ParseColor(fileIter, &template->specularReflectColor);
        fileIter = AreaLightTemplate_ParseColor(fileIter, &template->emissionColor);
        fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');
    }

    Heap_FreeExplicit(HEAP_ID_FIELD1, fileBuffer);

    return templateCount;
}

static void AreaLightTemplate_Free(AreaLightTemplate **template)
{
    Heap_FreeExplicit(HEAP_ID_FIELD1, *template);
    *template = NULL;
}

static char *AreaLightTemplate_ParseLightAttrs(char *fileIter, GXRgb *lightColor, VecFx16 *lightVector)
{
    char lineBuffer[SCRATCH_BUFFER_SIZE];
    char partBuffer[SCRATCH_BUFFER_SIZE];

    fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');

    char *iter = lineBuffer;
    iter = Ascii_CopyToTerminator(iter, partBuffer, ',');
    u32 lightValid = Ascii_ConvertToInt(partBuffer);

    if (lightValid == TRUE) {
        int i;
        u16 lightColorParts[GX_COLOR_DIMS];
        s32 lightVectorParts[GX_VEC_FX_DIMS];

        for (i = 0; i < GX_COLOR_DIMS; i++) {
            iter = Ascii_CopyToTerminator(iter, partBuffer, ',');
            lightColorParts[i] = Ascii_ConvertToInt(partBuffer);
        }

        *lightColor = GX_RGB(lightColorParts[0], lightColorParts[1], lightColorParts[2]);

        for (i = 0; i < GX_VEC_FX_DIMS; i++) {
            iter = Ascii_CopyToTerminator(iter, partBuffer, ',');
            lightVectorParts[i] = Ascii_ConvertToInt(partBuffer);
        }

        lightVector->x = lightVectorParts[0];
        lightVector->y = lightVectorParts[1];
        lightVector->z = lightVectorParts[2];

        if (lightVector->x > FX16_ONE) {
            lightVector->x = FX16_ONE;
        }

        if (lightVector->x < -FX16_ONE) {
            lightVector->x = -FX16_ONE;
        }

        if (lightVector->y > FX16_ONE) {
            lightVector->y = FX16_ONE;
        }

        if (lightVector->y < -FX16_ONE) {
            lightVector->y = -FX16_ONE;
        }

        if (lightVector->z > FX16_ONE) {
            lightVector->z = FX16_ONE;
        }

        if (lightVector->z < -FX16_ONE) {
            lightVector->z = -FX16_ONE;
        }
    } else {
        *lightColor = INVALID_LIGHT_COLOR;
    }

    return fileIter;
}

static char *AreaLightTemplate_ParseColor(char *fileIter, GXRgb *color)
{
    char lineBuffer[SCRATCH_BUFFER_SIZE];
    char partBuffer[SCRATCH_BUFFER_SIZE];
    u16 colorParts[GX_COLOR_DIMS];

    fileIter = Ascii_CopyToTerminator(fileIter, lineBuffer, '\r');
    char *iter = lineBuffer;

    for (int i = 0; i < GX_COLOR_DIMS; i++) {
        iter = Ascii_CopyToTerminator(iter, partBuffer, ',');
        colorParts[i] = Ascii_ConvertToInt(partBuffer);
    }

    *color = GX_RGB(colorParts[0], colorParts[1], colorParts[2]);

    return fileIter;
}
