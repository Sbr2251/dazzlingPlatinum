#include "overlay005/field_camera_zones.h"

#include <nitro.h>
#include <string.h>

#include "constants/field/map.h"
#include "generated/map_headers.h"

#include "field/field_system.h"

#include "camera.h"
#include "field_task.h"
#include "player_avatar.h"

#define F32_DEG_TO_IDX(__deg) FX_DEG_TO_IDX(FX32_CONST(__deg))

// Each frame the current offset moves 1/EASE_DIVISOR of the way to the target.
#define EASE_DIVISOR 6

enum CameraZoneAxis {
    CAMERA_ZONE_AXIS_X = 0,
    CAMERA_ZONE_AXIS_Z,
};

// A camera zone is an axis-aligned box of absolute map tiles (inclusive) on a
// single map header. Inside the box the zone weight is 1; it falls off
// linearly to 0 over fadeTiles tiles outside the box. The weight is also
// scaled by the player's progress along the given axis, from progressStart
// (weight 0) to progressEnd (weight 1). Both may run in either direction.
//
// At full weight the camera pitch is changed by pitchDelta (angle index units,
// positive = flatter / lower camera) and the distance by distanceDelta.
typedef struct CameraZone {
    u16 mapHeaderID;
    u8 axis;
    u8 fadeTiles;
    s16 x0, z0, x1, z1;
    s16 progressStart;
    s16 progressEnd;
    s32 pitchDelta;
    fx32 distanceDelta;
} CameraZone;

// Stock CAMERA_TYPE_ZOOMED_IN (field_camera.c): pitch -54.657 deg, distance 515.456.
// Top of the Lake Verity open stair: pitch -44.0 deg, distance 460.0.
static const CameraZone sCameraZones[] = {
    {
        // Lake Verity castle open staircase, see tools/lake_verity/layout.py
        // STAIR = (23,31)-(24,36), STAIR_LANDING = (23,29)-(24,30).
        // The box starts at z=37 (the h0 approach tile at the stair foot);
        // progress runs from z=37 (0) to z=30 (1, the landing) so the full
        // tilt is held across the landing and fades out going east through
        // STAIR_WALL_GAP onto the F1 terrace.
        .mapHeaderID = MAP_HEADER_LAKE_VERITY,
        .axis = CAMERA_ZONE_AXIS_Z,
        .fadeTiles = 2,
        .x0 = 23,
        .z0 = 29,
        .x1 = 24,
        .z1 = 37,
        .progressStart = 37,
        .progressEnd = 30,
        .pitchDelta = F32_DEG_TO_IDX(10.656982421875),
        .distanceDelta = FX32_CONST(-55.4560546875),
    },
};

typedef struct CameraZoneState {
    s32 curPitch; // angle index * FX32_ONE
    fx32 curDistance;
    s32 appliedPitch; // angle index
    fx32 appliedDistance;
    BOOL snap;
} CameraZoneState;

static CameraZoneState sZoneState;

// Converts a map object world position to a continuous tile coordinate in
// fx32, with tile centres at whole numbers (inverse of MAP_OBJECT_COORD_TO_FX32).
static fx32 WorldPosToTileCoord(fx32 pos)
{
    return (pos - (MAP_OBJECT_TILE_SIZE >> 1)) / 16;
}

static fx32 BoxAxisWeight(fx32 coord, s16 min, s16 max, u8 fadeTiles)
{
    fx32 outside;

    if (coord < min * FX32_ONE) {
        outside = min * FX32_ONE - coord;
    } else if (coord > max * FX32_ONE) {
        outside = coord - max * FX32_ONE;
    } else {
        return FX32_ONE;
    }

    if (fadeTiles == 0 || outside >= fadeTiles * FX32_ONE) {
        return 0;
    }

    return FX32_ONE - outside / fadeTiles;
}

static fx32 ZoneProgress(fx32 coord, s16 start, s16 end)
{
    fx32 progress;

    if (start == end) {
        return FX32_ONE;
    }

    progress = (coord - start * FX32_ONE) / (end - start);

    if (progress < 0) {
        return 0;
    }

    if (progress > FX32_ONE) {
        return FX32_ONE;
    }

    return progress;
}

static void ComputeTarget(FieldSystem *fieldSystem, s32 *outPitch, fx32 *outDistance)
{
    int i;
    const VecFx32 *pos;
    fx32 tileX, tileZ, weight;

    *outPitch = 0;
    *outDistance = 0;

    if (fieldSystem->playerAvatar == NULL || fieldSystem->location == NULL) {
        return;
    }

    pos = PlayerAvatar_PosVector(fieldSystem->playerAvatar);
    tileX = WorldPosToTileCoord(pos->x);
    tileZ = WorldPosToTileCoord(pos->z);

    for (i = 0; i < NELEMS(sCameraZones); i++) {
        const CameraZone *zone = &sCameraZones[i];

        if (zone->mapHeaderID != fieldSystem->location->mapId) {
            continue;
        }

        weight = FX_Mul(BoxAxisWeight(tileX, zone->x0, zone->x1, zone->fadeTiles), BoxAxisWeight(tileZ, zone->z0, zone->z1, zone->fadeTiles));

        if (weight == 0) {
            continue;
        }

        if (zone->axis == CAMERA_ZONE_AXIS_X) {
            weight = FX_Mul(weight, ZoneProgress(tileX, zone->progressStart, zone->progressEnd));
        } else {
            weight = FX_Mul(weight, ZoneProgress(tileZ, zone->progressStart, zone->progressEnd));
        }

        *outPitch += weight * zone->pitchDelta;
        *outDistance += FX_Mul(weight, zone->distanceDelta);
    }
}

static s32 EaseToward(s32 cur, s32 target)
{
    s32 step = (target - cur) / EASE_DIVISOR;

    if (step == 0) {
        return target;
    }

    return cur + step;
}

void FieldCameraZones_Reset(void)
{
    sZoneState.curPitch = 0;
    sZoneState.curDistance = 0;
    sZoneState.appliedPitch = 0;
    sZoneState.appliedDistance = 0;
    sZoneState.snap = TRUE;
}

void FieldCameraZones_Update(FieldSystem *fieldSystem)
{
    s32 targetPitch, newPitch;
    fx32 targetDistance;

    if (fieldSystem->camera == NULL) {
        return;
    }

    // Hold the camera still while a script, menu or map change is running.
    // The first frame after a camera reset always snaps to the target so that
    // returning from an app or save-load mid-stair does not visibly ease.
    if (sZoneState.snap == FALSE && FieldSystem_IsRunningTask(fieldSystem) == TRUE) {
        return;
    }

    ComputeTarget(fieldSystem, &targetPitch, &targetDistance);

    if (sZoneState.snap == TRUE) {
        sZoneState.curPitch = targetPitch;
        sZoneState.curDistance = targetDistance;
        sZoneState.snap = FALSE;
    } else {
        sZoneState.curPitch = EaseToward(sZoneState.curPitch, targetPitch);
        sZoneState.curDistance = EaseToward(sZoneState.curDistance, targetDistance);
    }

    newPitch = sZoneState.curPitch / FX32_ONE;

    if (newPitch != sZoneState.appliedPitch) {
        CameraAngle delta;

        memset(&delta, 0, sizeof(delta));
        delta.x = (u16)(newPitch - sZoneState.appliedPitch);
        Camera_AdjustAngleAroundTarget(&delta, fieldSystem->camera);
        sZoneState.appliedPitch = newPitch;
    }

    if (sZoneState.curDistance != sZoneState.appliedDistance) {
        Camera_AdjustDistance(sZoneState.curDistance - sZoneState.appliedDistance, fieldSystem->camera);
        sZoneState.appliedDistance = sZoneState.curDistance;
    }
}
