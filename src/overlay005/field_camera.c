#include "overlay005/field_camera.h"

#include <nitro.h>

#include "field/field_system.h"
#include "overlay005/field_camera_zones.h"
#include "overlay005/field_cinematics.h"

#include "camera.h"
#include "math_util.h"

#ifdef SDK_PORT
#include "port/sim_config_prj.h"
#include "port/sim_wide.h"
#endif

// History size must be greater than the delay, so we add 1 to the delay to get the minimum acceptable size.
#define FIELD_CAMERA_DELAY        6
#define FIELD_CAMERA_HISTORY_SIZE (FIELD_CAMERA_DELAY + 1)

typedef struct {
    fx32 distance;
    CameraAngle cameraAngle;
    u8 projection;
    u16 verticalFov;
    fx32 nearPlaneDist;
    fx32 farPlaneDist;
} CameraSettings;

static const CameraSettings sCameraTypes[] = {
    [CAMERA_TYPE_DEFAULT] = {
        .distance = FX32_CONST(666.922119140625),
        .cameraAngle = { -F32_DEG_TO_IDX(59.051513671875), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(8.0914306640625),
        .nearPlaneDist = CAMERA_DEFAULT_NEAR_CLIP,
        .farPlaneDist = CAMERA_DEFAULT_FAR_CLIP,
    },
    [CAMERA_TYPE_PASTORIA_GYM] = {
        .distance = FX32_CONST(666.922119140625),
        .cameraAngle = { -F32_DEG_TO_IDX(68.367919921875), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(8.0914306640625),
        .nearPlaneDist = CAMERA_DEFAULT_NEAR_CLIP,
        .farPlaneDist = CAMERA_DEFAULT_FAR_CLIP,
    },
    [CAMERA_TYPE_ZOOMED_IN] = {
        .distance = FX32_CONST(515.4560546875),
        .cameraAngle = { -F32_DEG_TO_IDX(54.656982421875), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(10.458984375),
        .nearPlaneDist = CAMERA_DEFAULT_NEAR_CLIP,
        .farPlaneDist = CAMERA_DEFAULT_FAR_CLIP,
    },
    [CAMERA_TYPE_CANALAVE_GYM] = {
        .distance = FX32_CONST(666.922119140625),
        .cameraAngle = { -F32_DEG_TO_IDX(59.051513671875), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(8.0914306640625),
        .nearPlaneDist = CAMERA_DEFAULT_NEAR_CLIP,
        .farPlaneDist = CAMERA_DEFAULT_FAR_CLIP,
    },
    [CAMERA_TYPE_INTERIOR_ORTHOGRAPHIC] = {
        .distance = FX32_CONST(1563.537841796875),
        .cameraAngle = { -F32_DEG_TO_IDX(50.086669921875), 0, 0 },
        .projection = CAMERA_PROJECTION_ORTHOGRAPHIC,
        .verticalFov = F32_DEG_TO_IDX(3.5211181640625),
        .nearPlaneDist = CAMERA_DEFAULT_NEAR_CLIP,
        .farPlaneDist = FX32_ONE * 1735,
    },
    [CAMERA_TYPE_SPEAR_PILLAR] = {
        .distance = FX32_CONST(316.501220703125),
        .cameraAngle = { -F32_DEG_TO_IDX(59.0460205078125), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(16.8804931640625),
        .nearPlaneDist = FX32_ONE * 10,
        .farPlaneDist = FX32_ONE * 1008,
    },
    [CAMERA_TYPE_MT_CORONET_EXT_SOUTH] = {
        .distance = FX32_CONST(866.554443359375),
        .cameraAngle = { -F32_DEG_TO_IDX(73.1085205078125), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(6.3336181640625),
        .nearPlaneDist = FX32_ONE * 115,
        .farPlaneDist = FX32_ONE * 1221,
    },
    [CAMERA_TYPE_MT_CORONET_EXT_NORTH] = {
        .distance = FX32_CONST(666.922119140625),
        .cameraAngle = { -F32_DEG_TO_IDX(59.0460205078125), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(8.0914306640625),
        .nearPlaneDist = FX32_ONE * 153,
        .farPlaneDist = FX32_ONE * 1031,
    },
    [CAMERA_TYPE_STARK_MOUNTAIN_ROOM_2] = {
        .distance = FX32_CONST(662.922119140625),
        .cameraAngle = { -F32_DEG_TO_IDX(70.4718017578125), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(9.8492431640625),
        .nearPlaneDist = CAMERA_DEFAULT_NEAR_CLIP,
        .farPlaneDist = FX32_ONE * 1034,
    },
    [CAMERA_TYPE_OREBURGH_GYM] = {
        .distance = FX32_CONST(357.6044921875),
        .cameraAngle = { -F32_DEG_TO_IDX(40.5889892578125), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(15.029296875),
        .nearPlaneDist = CAMERA_DEFAULT_NEAR_CLIP,
        .farPlaneDist = CAMERA_DEFAULT_FAR_CLIP,
    },
    [CAMERA_TYPE_VEILSTONE_GYM] = {
        .distance = FX32_CONST(1202.355712890625),
        .cameraAngle = { -F32_DEG_TO_IDX(60.8038330078125), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(4.5758056640625),
        .nearPlaneDist = CAMERA_DEFAULT_NEAR_CLIP,
        .farPlaneDist = FX32_ONE * 1746,
    },
    [CAMERA_TYPE_SLIGHTLY_ZOOMED_OUT] = {
        .distance = FX32_CONST(675.833251953125),
        .cameraAngle = { -F32_DEG_TO_IDX(57.8155517578125), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(8.0914306640625),
        .nearPlaneDist = FX32_ONE * 230,
        .farPlaneDist = FX32_ONE * 1127,
    },
    [CAMERA_TYPE_CAVE] = {
        .distance = FX32_CONST(574.577880859375),
        .cameraAngle = { -F32_DEG_TO_IDX(63.2647705078125), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(9.4976806640625),
        .nearPlaneDist = CAMERA_DEFAULT_NEAR_CLIP,
        .farPlaneDist = CAMERA_DEFAULT_FAR_CLIP,
    },
    [CAMERA_TYPE_IRON_ISLAND_CAVE] = {
        .distance = FX32_CONST(515.4560546875),
        .cameraAngle = { -F32_DEG_TO_IDX(47.7960205078125), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(10.458984375),
        .nearPlaneDist = CAMERA_DEFAULT_NEAR_CLIP,
        .farPlaneDist = CAMERA_DEFAULT_FAR_CLIP,
    },
    [CAMERA_TYPE_HALL_OF_ORIGIN] = {
        .distance = FX32_CONST(169.462158203125),
        .cameraAngle = { -F32_DEG_TO_IDX(78.37646484375), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(29.5367431640625),
        .nearPlaneDist = FX32_ONE * 10,
        .farPlaneDist = FX32_ONE * 1008,
    },
    [CAMERA_TYPE_LAKE_ACUITY] = {
        .distance = FX32_CONST(653.929443359375),
        .cameraAngle = { -F32_DEG_TO_IDX(54.656982421875), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(8.349609375),
        .nearPlaneDist = CAMERA_DEFAULT_NEAR_CLIP,
        .farPlaneDist = CAMERA_DEFAULT_FAR_CLIP,
    },
    [CAMERA_TYPE_UNUSED_16] = {
        .distance = FX32_CONST(330.921875),
        .cameraAngle = { -F32_DEG_TO_IDX(59.051513671875), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(15.4742431640625),
        .nearPlaneDist = CAMERA_DEFAULT_NEAR_CLIP,
        .farPlaneDist = CAMERA_DEFAULT_FAR_CLIP,
    },
};

void FieldCamera_Create(const VecFx32 *_target, FieldSystem *fieldSystem, enum CameraType configID, BOOL withHistory)
{
    const VecFx32 *target = _target;
    const CameraSettings *config = &sCameraTypes[configID];

    GF_ASSERT(configID < NELEMS(sCameraTypes));

    fieldSystem->camera = Camera_Alloc(HEAP_ID_FIELD1);

    fx32 distance = config->distance;
    fx32 farPlaneDist = config->farPlaneDist;

#ifdef SDK_PORT
    if (SIM_Config_prj_DebugWideCamera()) {
        // Debug wide view: 16:9 aspect, pulled back and with a farther clip
        // plane, so the land blocks loaded around the DS 2x2 window (see
        // FieldLoadRadius) are visible on the current screen.
        distance = distance + distance;
        // Near 100 / far 1700 stays inside fx32 range in MTX_PerspectiveW
        // (2 * near * far) while keeping the pulled-back target in range.
        farPlaneDist = FX32_ONE * 1700;
    }
#endif

    Camera_InitWithTarget(target, distance, &config->cameraAngle, config->verticalFov, config->projection, TRUE, fieldSystem->camera);
    Camera_SetAsActive(fieldSystem->camera);
    {
        fx32 nearPlaneDist = config->nearPlaneDist;
#ifdef SDK_PORT
        if (SIM_Config_prj_DebugWideCamera()) {
            nearPlaneDist = FX32_ONE * 100;
        }
#endif
        Camera_SetClipping(nearPlaneDist, farPlaneDist, fieldSystem->camera);
    }

#ifdef SDK_PORT
    if (SIM_Config_prj_DebugWideCamera()) {
        Camera_SetAspectRatio(FX32_ONE * 16 / 9, fieldSystem->camera);
    }

    // Wide layout (wide-OUT/API.md): render the field at the wide aspect
    // so the simulator's 16:9 composite has correct proportions. The
    // renderer's frustum cull follows this projection, and NPCs are
    // map-header objects with no game-side draw range, so this (with
    // FieldLoadRadius=3 terrain) is the whole wider-frustum fix: nothing
    // pops at the old 4:3 edges. DebugWideCamera above already sets the
    // same aspect, plus its pulled-back distance/clip for debugging.
    if (SIM_Wide_IsWideLayout()) {
        Camera_SetAspectRatio(SIM_Wide_AspectRatio(), fieldSystem->camera);
    }
#endif

    if (withHistory) {
        Camera_InitHistory(FIELD_CAMERA_HISTORY_SIZE, FIELD_CAMERA_DELAY, CAMERA_DELAY_Y, HEAP_ID_FIELD1, fieldSystem->camera);
    }

    FieldCameraZones_Reset();
    FieldCinematics_Reset();
}

void FieldCamera_Delete(FieldSystem *fieldSystem)
{
    Camera_ClearActive();
    Camera_DeleteHistory(fieldSystem->camera);
    Camera_Delete(fieldSystem->camera);
}
