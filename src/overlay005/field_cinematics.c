#include "overlay005/field_cinematics.h"

#include <nitro.h>
#include <string.h>

#ifdef SDK_PORT
#include <stdlib.h>

#include "port/sim_config_prj.h"
#include "port/sim_wide.h"
#endif

#include "field/field_system.h"

// One tile is 16 world units (MAP_OBJECT_COORD_TO_FX32 / fx32 tile math in
// field_camera_zones.c); script offsets are in whole tiles.
#define CINE_TILE_SIZE (16 * FX32_ONE)

typedef struct CineCameraState {
    VecFx32 target;
    VecFx32 position;
    VecFx32 prevTargetPos;
    const VecFx32 *targetPos;
    fx32 distance;
    CameraAngle angle;
    u16 fovY;
    BOOL trackTargetX;
    BOOL trackTargetY;
    BOOL trackTargetZ;
} CineCameraState;

typedef struct CineMove {
    CineCameraState from;
    CineCameraState to;
    u16 frames;
    u16 elapsed;
    u8 easing;
    BOOL returning; // on completion, restore the snapshot exactly
} CineMove;

static struct {
    Camera *camera; // camera the snapshot belongs to; a new camera resets state
    CineCameraState snapshot;
    BOOL hasSnapshot;
    BOOL active;
    CineMove move;
} sCine;

static void CineCameraState_Capture(Camera *camera, CineCameraState *out)
{
    out->target = Camera_GetTarget(camera);
    out->position = Camera_GetPosition(camera);
    out->prevTargetPos = camera->prevTargetPos;
    out->targetPos = camera->targetPos;
    out->distance = Camera_GetDistance(camera);
    out->angle = Camera_GetAngle(camera);
    out->fovY = Camera_GetFOV(camera);
    out->trackTargetX = camera->trackTargetX;
    out->trackTargetY = camera->trackTargetY;
    out->trackTargetZ = camera->trackTargetZ;
}

static void CineCameraState_ApplyExact(Camera *camera, const CineCameraState *state)
{
    camera->targetPos = state->targetPos;
    camera->prevTargetPos = state->prevTargetPos;
    camera->trackTargetX = state->trackTargetX;
    camera->trackTargetY = state->trackTargetY;
    camera->trackTargetZ = state->trackTargetZ;
    camera->distance = state->distance;
    camera->angle = state->angle;
    Camera_SetTarget(&state->target, camera);
    Camera_SetPosition(&state->position, camera);
    Camera_SetFOV(state->fovY, camera);
}

// Applies an interpolated state. Position is recomputed from target,
// distance and angle so the view matrix stays consistent; tracking stays
// released for the whole cinematic so the follow logic cannot fight it.
static void CineCameraState_ApplyInterpolated(Camera *camera, const CineCameraState *state)
{
    Camera_SetTarget(&state->target, camera);
    Camera_SetDistance(state->distance, camera);
    Camera_SetAngleAroundTarget(&state->angle, camera);
    Camera_SetFOV(state->fovY, camera);
}

static fx32 CineLerpFx(fx32 from, fx32 to, fx32 t)
{
    return from + (fx32)(((s64)(to - from) * t) / FX32_ONE);
}

static s32 CineLerpAngle(u16 from, u16 to, fx32 t)
{
    s32 diff = (s32)(s16)(to - from); // shortest way around the circle

    return (s32)from + (s32)(((s64)diff * t) / FX32_ONE);
}

// t in fx32 (0..FX32_ONE) mapped through the easing curve, in fx32.
static fx32 CineEase(u8 easing, fx32 t)
{
    s64 t64 = t;

    switch (easing) {
    case CINE_EASE_IN_OUT:
        // smoothstep 3t^2 - 2t^3
        return (fx32)((t64 * t64 * (3 * FX32_ONE - 2 * t) / FX32_ONE) / FX32_ONE);
    case CINE_EASE_OUT:
        // 1 - (1-t)^2
        return (fx32)(FX32_ONE - ((FX32_ONE - t64) * (FX32_ONE - t64)) / FX32_ONE);
    case CINE_EASE_IN:
        // t^2
        return (fx32)((t64 * t64) / FX32_ONE);
    case CINE_EASE_LINEAR:
    default:
        return t;
    }
}

static void CineInterpolate(const CineCameraState *from, const CineCameraState *to, fx32 t, CineCameraState *out)
{
    out->target.x = CineLerpFx(from->target.x, to->target.x, t);
    out->target.y = CineLerpFx(from->target.y, to->target.y, t);
    out->target.z = CineLerpFx(from->target.z, to->target.z, t);
    out->distance = CineLerpFx(from->distance, to->distance, t);
    out->angle.x = (u16)CineLerpAngle(from->angle.x, to->angle.x, t);
    out->angle.y = (u16)CineLerpAngle(from->angle.y, to->angle.y, t);
    out->angle.z = (u16)CineLerpAngle(from->angle.z, to->angle.z, t);
    out->fovY = (u16)(from->fovY + (s32)(((s64)((s32)(s16)(to->fovY - from->fovY)) * t) / FX32_ONE));
}

BOOL FieldCinematics_IsEnabled(void)
{
#ifdef SDK_PORT
    const char *fxEnv = getenv("SIM_FX_CINE");

    if (fxEnv != NULL && fxEnv[0] != '\0') {
        return fxEnv[0] != '0';
    }

    if (getenv("SIM_HEADLESS") != NULL) {
        return FALSE;
    }

    return SIM_Config_prj_GetConfig()->overworldCinematics;
#else
    return TRUE;
#endif
}

void FieldCinematics_Reset(void)
{
    memset(&sCine, 0, sizeof(sCine));
}

BOOL FieldCinematics_IsActive(void)
{
    return sCine.active;
}

static void CineBeginMove(FieldSystem *fieldSystem, const CineCameraState *dest, u16 frames, u8 easing, BOOL returning)
{
    Camera *camera = fieldSystem->camera;

    if (camera == NULL) {
        return;
    }

    if (sCine.camera != camera) {
        FieldCinematics_Reset();
        sCine.camera = camera;
    }

    if (!sCine.hasSnapshot) {
        CineCameraState_Capture(camera, &sCine.snapshot);
        sCine.hasSnapshot = TRUE;
    }

    CineCameraState_Capture(camera, &sCine.move.from);
    sCine.move.to = *dest;
    sCine.move.frames = (frames == 0) ? 1 : frames;
    sCine.move.elapsed = 0;
    sCine.move.easing = (easing < CINE_EASE_COUNT) ? easing : CINE_EASE_LINEAR;
    sCine.move.returning = returning;
    sCine.active = TRUE;

    // The follow logic must not move the camera while a move runs.
    Camera_ReleaseTarget(camera);
}

void FieldCinematics_StartMove(FieldSystem *fieldSystem, s16 targetOffsetXTiles, s16 targetOffsetZTiles, fx32 distance, s16 pitchDeg, s16 yawDeg, u16 fovDeg, u16 frames, u8 easing)
{
    CineCameraState dest;

    if (fieldSystem->camera == NULL) {
        return;
    }

    CineCameraState_Capture(fieldSystem->camera, &dest);
    dest.target.x += targetOffsetXTiles * CINE_TILE_SIZE;
    dest.target.z += targetOffsetZTiles * CINE_TILE_SIZE;
    dest.distance = distance;
#ifdef SDK_PORT
    // Wide layout (wide-OUT/API.md): the scripted poses were tuned for
    // 4:3 against the DS 2x2 loaded-block window (see fx-OUT/cine). At
    // 16:9 the same vertical FOV shows a third more horizontally, and
    // FieldLoadRadius=3 keeps terrain loaded a block further out, so
    // widen the establishing moves a little instead of showing the
    // narrower 4:3 framing floating in a wider frame: distance x9/8
    // (city pull-backs 700 -> 787, Lake Verity 680 -> 765) and +1 degree
    // of vertical FOV. The snapshot/return path is untouched, so the
    // restore stays exact; when the layout is not wide the destinations
    // are exactly the scripted ones.
    if (SIM_Wide_IsWideLayout()) {
        dest.distance = distance + distance / 8;
        fovDeg = (u16)(fovDeg + 1);
    }
#endif
    dest.angle.x = (u16)-FX_DEG_TO_IDX(pitchDeg * FX32_ONE);
    dest.angle.y = (u16)FX_DEG_TO_IDX(yawDeg * FX32_ONE);
    dest.angle.z = 0;
    dest.fovY = (u16)FX_DEG_TO_IDX(fovDeg * FX32_ONE);

    CineBeginMove(fieldSystem, &dest, frames, easing, FALSE);
}

void FieldCinematics_ReturnMove(FieldSystem *fieldSystem, u16 frames, u8 easing)
{
    if (fieldSystem->camera == NULL || !sCine.hasSnapshot) {
        return;
    }

    CineBeginMove(fieldSystem, &sCine.snapshot, frames, easing, TRUE);
}

void FieldCinematics_Update(FieldSystem *fieldSystem)
{
    Camera *camera;
    CineCameraState cur;
    fx32 t;

    if (!sCine.active || fieldSystem == NULL) {
        return;
    }

    camera = fieldSystem->camera;

    if (camera == NULL || camera != sCine.camera) {
        // The camera went away mid-cinematic (map change); drop the move.
        FieldCinematics_Reset();
        return;
    }

    sCine.move.elapsed++;

    if (sCine.move.elapsed >= sCine.move.frames) {
        if (sCine.move.returning) {
            CineCameraState_ApplyExact(camera, &sCine.snapshot);
            sCine.hasSnapshot = FALSE;
        } else {
            CineCameraState_ApplyInterpolated(camera, &sCine.move.to);
        }

        sCine.active = FALSE;
        return;
    }

    t = CineEase(sCine.move.easing, (sCine.move.elapsed << 12) / sCine.move.frames);
    CineInterpolate(&sCine.move.from, &sCine.move.to, t, &cur);
    CineCameraState_ApplyInterpolated(camera, &cur);
}
