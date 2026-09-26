#include "battle/battle_stage_camera.h"

#include <nitro.h>
#include <string.h>

#include "config/battle_stage.h"
#include "constants/battle.h"
#include "constants/battle/battle_anim.h"

#include "battle/battle_stage.h"
#include "battle/battle_stage_sprites.h"
#include "battle/ov16_0223DF00.h"

#include "particle_system.h"
#include "totem_battle.h"

// Clamps of the sprite scale and of the view depth it comes from
#define CAMERA_MIN_DEPTH FX32_CONST(0.25)
#define CAMERA_MAX_SCALE (FX32_ONE * 4)
#define CAMERA_MIN_SCALE (FX32_ONE / 16)

// The script-end ease home, when a script leaves the camera off home
#define SCRIPT_END_HOME_FRAMES 12
// The command menu waits for the camera at most this long, then snaps it home
#define MENU_WAIT_MAX_FRAMES 90

// Shake periods in frames, different in x and y so the path isn't a line
#define SHAKE_PERIOD_X 7
#define SHAKE_PERIOD_Y 5

enum CameraSequence {
    SEQUENCE_NONE = 0,
    SEQUENCE_TO, // easing to the goal
    SEQUENCE_HOLD, // holding there (and until the shake ends)
};

enum ParticleFocus {
    PARTICLE_FOCUS_CENTER = 0,
    PARTICLE_FOCUS_BATTLER,
    PARTICLE_FOCUS_BETWEEN,
};

typedef struct CameraPose {
    VecFx32 focus;
    fx32 yaw; // degrees
    fx32 pitch; // degrees
    fx32 distance;
    fx32 fov;
} CameraPose;

typedef struct CameraAnchor {
    BOOL valid;
    int homeX;
    int homeY;
    fx32 nowX;
    fx32 nowY;
    fx32 scale;
} CameraAnchor;

typedef struct StageCamera {
    BattleSystem *battleSys;
    BattleStageCameraFields *fields;
    const u32 *debugFlags;
    BOOL hasHome;
    BattleStageCameraHome home;
    CameraPose homePose;
    // Motion
    CameraPose cur;
    CameraPose from;
    CameraPose goal;
    int easeFrame;
    int easeFrames;
    int shakeFrame;
    int shakeFrames;
    int shakeAmp; // pixels
    int sequence;
    int holdFrames;
    int homeFrames; // the ease home at the end of the sequence
    // Script and cinematics
    BOOL scriptActive;
    BOOL sweepDone;
    int menuWait;
    // Particles
    int particleFocus;
    int particleBattlers[2];
    // This frame, from Advance
    BOOL atHome;
    MtxFx43 view;
    MtxFx44 projection;
    const MtxFx44 *drawProjection;
    CameraAnchor anchors[MAX_BATTLERS];
    CameraAnchor particle;
} StageCamera;

static void ParticleProjectionHook(MtxFx44 *projection);

static StageCamera sStageCamera;

// Classic home x of each battler type (BATTLER_TYPE_*)
static const int sHomeX[BATTLER_TYPE_MAX] = { 64, 192, 40, 216, 80, 176 };

static BOOL PoseEquals(const CameraPose *a, const CameraPose *b)
{
    return a->focus.x == b->focus.x && a->focus.y == b->focus.y && a->focus.z == b->focus.z
        && a->yaw == b->yaw && a->pitch == b->pitch && a->distance == b->distance && a->fov == b->fov;
}

static BOOL IsEasing(void)
{
    return sStageCamera.easeFrames > 0 && sStageCamera.easeFrame < sStageCamera.easeFrames;
}

static BOOL IsShaking(void)
{
    return sStageCamera.shakeFrames > 0 && sStageCamera.shakeFrame < sStageCamera.shakeFrames;
}

static void SnapHome(void)
{
    sStageCamera.cur = sStageCamera.homePose;
    sStageCamera.from = sStageCamera.homePose;
    sStageCamera.goal = sStageCamera.homePose;
    sStageCamera.easeFrame = 0;
    sStageCamera.easeFrames = 0;
    sStageCamera.shakeFrame = 0;
    sStageCamera.shakeFrames = 0;
    sStageCamera.sequence = SEQUENCE_NONE;
}

// Ease from wherever the camera is now; 0 frames snaps
static void EaseTo(const CameraPose *goal, int frames)
{
    sStageCamera.from = sStageCamera.cur;
    sStageCamera.goal = *goal;
    sStageCamera.easeFrame = 0;

    if (frames <= 0) {
        sStageCamera.cur = *goal;
        sStageCamera.easeFrames = 0;
    } else {
        sStageCamera.easeFrames = frames;
    }
}

static void StartShake(int amplitudePx, int frames)
{
    if (frames <= 0 || amplitudePx <= 0) {
        sStageCamera.shakeFrames = 0;
        sStageCamera.shakeFrame = 0;
        return;
    }

    sStageCamera.shakeAmp = amplitudePx;
    sStageCamera.shakeFrames = frames;
    sStageCamera.shakeFrame = 0;
}

static fx32 Lerp(fx32 a, fx32 b, fx32 t)
{
    return a + FX_Mul(b - a, t);
}

static void AdvanceEase(void)
{
    CameraPose *from = &sStageCamera.from;
    CameraPose *goal = &sStageCamera.goal;
    CameraPose *cur = &sStageCamera.cur;
    fx32 t, s;

    if (!IsEasing()) {
        return;
    }

    sStageCamera.easeFrame++;

    if (sStageCamera.easeFrame >= sStageCamera.easeFrames) {
        *cur = *goal;
        sStageCamera.easeFrames = 0;
        sStageCamera.easeFrame = 0;
        return;
    }

    // Smoothstep, 3t^2 - 2t^3
    t = sStageCamera.easeFrame * FX32_ONE / sStageCamera.easeFrames;
    s = FX_Mul(FX_Mul(t, t), 3 * FX32_ONE - 2 * t);

    cur->focus.x = Lerp(from->focus.x, goal->focus.x, s);
    cur->focus.y = Lerp(from->focus.y, goal->focus.y, s);
    cur->focus.z = Lerp(from->focus.z, goal->focus.z, s);
    cur->yaw = Lerp(from->yaw, goal->yaw, s);
    cur->pitch = Lerp(from->pitch, goal->pitch, s);
    cur->distance = Lerp(from->distance, goal->distance, s);
    cur->fov = Lerp(from->fov, goal->fov, s);
}

// Sine and cosine of an angle in fx32 degrees; a negative angle takes the sine of its
// magnitude, negated, as debug view 1 always did
static void SinCosDeg(fx32 deg, fx32 *sinA, fx32 *cosA)
{
    fx32 magnitude = deg < 0 ? -deg : deg;
    u16 index = FX_DEG_TO_IDX(magnitude);

    *sinA = FX_SinIdx(index);
    *cosA = FX_CosIdx(index);

    if (deg < 0) {
        *sinA = -*sinA;
    }
}

// The pose's camera position and target, before the shake. Same math as the old debug views.
static void PoseCamera(const CameraPose *pose, VecFx32 *camPos, VecFx32 *offsetOut)
{
    VecFx32 up = { 0, FX32_ONE, 0 };
    VecFx32 offset;
    fx32 sinA, cosA, x;

    VEC_Subtract(&sStageCamera.home.camPos, &sStageCamera.home.camTarget, &offset);

    if (pose->pitch != 0) {
        VecFx32 right, lift;

        SinCosDeg(pose->pitch, &sinA, &cosA);
        VEC_CrossProduct(&up, &offset, &right);
        VEC_Normalize(&right, &right);
        VEC_CrossProduct(&offset, &right, &lift);

        offset.x = FX_Mul(offset.x, cosA) + FX_Mul(lift.x, sinA);
        offset.y = FX_Mul(offset.y, cosA) + FX_Mul(lift.y, sinA);
        offset.z = FX_Mul(offset.z, cosA) + FX_Mul(lift.z, sinA);
    }

    if (pose->yaw != 0) {
        SinCosDeg(pose->yaw, &sinA, &cosA);
        x = offset.x;
        offset.x = FX_Mul(x, cosA) + FX_Mul(offset.z, sinA);
        offset.z = FX_Mul(offset.z, cosA) - FX_Mul(x, sinA);
    }

    if (pose->distance != FX32_ONE) {
        offset.x = FX_Mul(offset.x, pose->distance);
        offset.y = FX_Mul(offset.y, pose->distance);
        offset.z = FX_Mul(offset.z, pose->distance);
    }

    VEC_Add(&pose->focus, &offset, camPos);
    *offsetOut = offset;
}

// The shake offset in pixels for this frame: a decaying sine, the same every time
static void ShakePixels(int *dx, int *dy)
{
    int k = sStageCamera.shakeFrame;
    int n = sStageCamera.shakeFrames;
    int amp = sStageCamera.shakeAmp;

    *dx = amp * FX_SinIdx((u16)(k * 0x10000 / SHAKE_PERIOD_X)) * (n - k) / n / FX32_ONE;
    *dy = amp * FX_SinIdx((u16)(k * 0x10000 / SHAKE_PERIOD_Y + 0x4000)) * (n - k) / n / FX32_ONE;
}

static void BuildView(const CameraPose *pose)
{
    VecFx32 up = { 0, FX32_ONE, 0 };
    VecFx32 camPos, offset, target;

    PoseCamera(pose, &camPos, &offset);
    target = pose->focus;

    if (IsShaking()) {
        VecFx32 back, right, camUp;
        fx32 depth, perPixel, sx, sy;
        int dx, dy;

        ShakePixels(&dx, &dy);
        depth = VEC_Mag(&offset);
        VEC_Normalize(&offset, &back);
        VEC_CrossProduct(&up, &back, &right);
        VEC_Normalize(&right, &right);
        VEC_CrossProduct(&back, &right, &camUp);

        // World units per pixel at the focus depth: depth * tanY / 96
        perPixel = FX_Mul(depth, FX_Div(sStageCamera.home.fovySin, sStageCamera.home.fovyCos));
        perPixel = FX_Mul(perPixel, pose->fov) / 96;
        sx = perPixel * dx;
        sy = perPixel * dy;

        camPos.x += FX_Mul(right.x, sx) + FX_Mul(camUp.x, sy);
        camPos.y += FX_Mul(right.y, sx) + FX_Mul(camUp.y, sy);
        camPos.z += FX_Mul(right.z, sx) + FX_Mul(camUp.z, sy);
        target.x += FX_Mul(right.x, sx) + FX_Mul(camUp.x, sy);
        target.y += FX_Mul(right.y, sx) + FX_Mul(camUp.y, sy);
        target.z += FX_Mul(right.z, sx) + FX_Mul(camUp.z, sy);
    }

    MTX_LookAt(&camPos, &up, &target, &sStageCamera.view);

    if (pose->fov == FX32_ONE) {
        sStageCamera.drawProjection = sStageCamera.home.projection;
    } else {
        BattleStage_BuildProjection(FX_Mul(sStageCamera.home.fovySin, pose->fov), sStageCamera.home.fovyCos, sStageCamera.home.nearClip, sStageCamera.home.farClip, &sStageCamera.projection);
        sStageCamera.drawProjection = &sStageCamera.projection;
    }
}

// A world point through a view and projection: screen pixels (fx32) and view depth.
// FALSE when it is behind the camera.
static BOOL Project(const VecFx32 *point, const MtxFx43 *view, const MtxFx44 *projection, fx32 *sx, fx32 *sy, fx32 *depth)
{
    VecFx32 v;
    fx32 cx, cy, cw;

    MTX_MultVec43(point, view, &v);
    *depth = -v.z;

    cx = FX_Mul(v.x, projection->_00) + FX_Mul(v.y, projection->_10) + FX_Mul(v.z, projection->_20) + projection->_30;
    cy = FX_Mul(v.x, projection->_01) + FX_Mul(v.y, projection->_11) + FX_Mul(v.z, projection->_21) + projection->_31;
    cw = FX_Mul(v.x, projection->_03) + FX_Mul(v.y, projection->_13) + FX_Mul(v.z, projection->_23) + projection->_33;

    if (cw <= 0) {
        return FALSE;
    }

    *sx = 128 * FX32_ONE + 128 * FX_Div(cx, cw);
    *sy = 96 * FX32_ONE - 96 * FX_Div(cy, cw);
    return TRUE;
}

static fx32 DepthScale(fx32 homeDepth, fx32 nowDepth, fx32 fov)
{
    fx32 s;

    if (nowDepth < CAMERA_MIN_DEPTH) {
        nowDepth = CAMERA_MIN_DEPTH;
    }

    s = FX_Div(homeDepth, nowDepth);

    if (fov != FX32_ONE && fov > 0) {
        s = FX_Div(s, fov);
    }

    if (s > CAMERA_MAX_SCALE) {
        s = CAMERA_MAX_SCALE;
    } else if (s < CAMERA_MIN_SCALE) {
        s = CAMERA_MIN_SCALE;
    }

    return s;
}

static int MaxBattlers(void)
{
    int max = BattleSystem_MaxBattlers(sStageCamera.battleSys);

    return max > MAX_BATTLERS ? MAX_BATTLERS : max;
}

// The world foot point of a battler: the home ray through its home anchor, on the ground
static BOOL BattlerFoot(int battler, int *homeX, int *homeY, VecFx32 *foot)
{
    int type = BattleSystem_BattlerSlot(sStageCamera.battleSys, battler);
    int side;

    if (type < 0 || type >= BATTLER_TYPE_MAX) {
        return FALSE;
    }

    side = type & 1;
    *homeX = sHomeX[type];
    *homeY = BattleStageSprites_BlobRow(side);
    return BattleStageSprites_GroundPoint(side, *homeX, foot);
}

static void UpdateAnchor(CameraAnchor *anchor, int homeX, int homeY, const VecFx32 *point, const CameraPose *pose)
{
    fx32 sx, sy, depth, homeSX, homeSY, homeDepth;

    anchor->homeX = homeX;
    anchor->homeY = homeY;

    if (sStageCamera.atHome
        || !Project(point, sStageCamera.home.view, sStageCamera.home.projection, &homeSX, &homeSY, &homeDepth)
        || !Project(point, &sStageCamera.view, sStageCamera.drawProjection, &sx, &sy, &depth)) {
        anchor->nowX = homeX * FX32_ONE;
        anchor->nowY = homeY * FX32_ONE;
        anchor->scale = FX32_ONE;
        anchor->valid = TRUE;
        return;
    }

    anchor->nowX = sx;
    anchor->nowY = sy;
    anchor->scale = DepthScale(homeDepth, depth, pose->fov);
    anchor->valid = TRUE;
}

static void UpdateAnchors(const CameraPose *pose)
{
    BattleStageCameraFields *fields = sStageCamera.fields;
    int max = MaxBattlers();
    int i;

    for (i = 0; i < MAX_BATTLERS; i++) {
        CameraAnchor *anchor = &sStageCamera.anchors[i];
        VecFx32 foot;
        int homeX, homeY;

        if (i >= max || !BattlerFoot(i, &homeX, &homeY, &foot)) {
            anchor->valid = FALSE;
            fields->anchor[i][0] = 0;
            fields->anchor[i][1] = 0;
            fields->anchorScale[i] = 0;
            continue;
        }

        UpdateAnchor(anchor, homeX, homeY, &foot, pose);
        fields->anchor[i][0] = (s16)(anchor->nowX >> FX32_SHIFT);
        fields->anchor[i][1] = (s16)(anchor->nowY >> FX32_SHIFT);
        fields->anchorScale[i] = (u16)(anchor->scale >> 4);
    }

    // The particles' similarity
    switch (sStageCamera.particleFocus) {
    case PARTICLE_FOCUS_BATTLER:
        if (sStageCamera.anchors[sStageCamera.particleBattlers[0]].valid) {
            sStageCamera.particle = sStageCamera.anchors[sStageCamera.particleBattlers[0]];
            return;
        }
        break;
    case PARTICLE_FOCUS_BETWEEN: {
        const CameraAnchor *a = &sStageCamera.anchors[sStageCamera.particleBattlers[0]];
        const CameraAnchor *b = &sStageCamera.anchors[sStageCamera.particleBattlers[1]];

        if (a->valid && b->valid) {
            sStageCamera.particle.valid = TRUE;
            sStageCamera.particle.homeX = (a->homeX + b->homeX) / 2;
            sStageCamera.particle.homeY = (a->homeY + b->homeY) / 2;
            sStageCamera.particle.nowX = (a->nowX + b->nowX) / 2;
            sStageCamera.particle.nowY = (a->nowY + b->nowY) / 2;
            sStageCamera.particle.scale = (a->scale + b->scale) / 2;
            return;
        }
        break;
    }
    default:
        break;
    }

    // CENTER: the home camTarget, which is at the screen centre at home
    UpdateAnchor(&sStageCamera.particle, 128, 96, &sStageCamera.home.camTarget, pose);
}

static void AdvanceSequence(void)
{
    switch (sStageCamera.sequence) {
    case SEQUENCE_TO:
        if (!IsEasing()) {
            sStageCamera.sequence = SEQUENCE_HOLD;
        }
        break;
    case SEQUENCE_HOLD:
        if (sStageCamera.holdFrames > 0) {
            sStageCamera.holdFrames--;
        }

        if (sStageCamera.holdFrames <= 0 && !IsShaking()) {
            EaseTo(&sStageCamera.homePose, sStageCamera.homeFrames);
            sStageCamera.sequence = SEQUENCE_NONE;
        }
        break;
    default:
        break;
    }
}

void BattleStageCamera_Init(BattleSystem *battleSys, BattleStageCameraFields *fields, const BattleStageCameraHome *home, const u32 *debugFlags)
{
    memset(&sStageCamera, 0, sizeof(sStageCamera));
    memset(fields, 0, sizeof(*fields));

    sStageCamera.battleSys = battleSys;
    sStageCamera.fields = fields;
    sStageCamera.debugFlags = debugFlags;
    sStageCamera.atHome = TRUE;
    fields->camFlags = BATTLE_STAGE_CAMERA_AT_HOME;

    if (home == NULL) {
        return;
    }

    sStageCamera.hasHome = TRUE;
    sStageCamera.home = *home;
    sStageCamera.homePose.focus = home->camTarget;
    sStageCamera.homePose.yaw = 0;
    sStageCamera.homePose.pitch = 0;
    sStageCamera.homePose.distance = FX32_ONE;
    sStageCamera.homePose.fov = FX32_ONE;
    sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;
    sStageCamera.drawProjection = home->projection;
    SnapHome();

    ParticleSystem_SetProjectionHook(ParticleProjectionHook);
}

void BattleStageCamera_Free(void)
{
    if (sStageCamera.hasHome) {
        ParticleSystem_SetProjectionHook(NULL);
        SnapHome();
    }

    sStageCamera.hasHome = FALSE;
    sStageCamera.atHome = TRUE;
    sStageCamera.fields = NULL;
    sStageCamera.battleSys = NULL;
}

void BattleStageCamera_Advance(BOOL visible, int debugView)
{
    BattleStageCameraFields *fields = sStageCamera.fields;
    CameraPose pose;
    u32 flags;

    if (!sStageCamera.hasHome || fields == NULL) {
        return;
    }

    // The classic path never sees an off-home camera
    if (!visible) {
        SnapHome();
    } else {
        AdvanceEase();

        if (IsShaking()) {
            sStageCamera.shakeFrame++;

            if (sStageCamera.shakeFrame >= sStageCamera.shakeFrames) {
                sStageCamera.shakeFrames = 0;
                sStageCamera.shakeFrame = 0;
            }
        }

        AdvanceSequence();
    }

    sStageCamera.atHome = PoseEquals(&sStageCamera.cur, &sStageCamera.homePose) && !IsEasing() && !IsShaking() && debugView == 0;

    flags = fields->camFlags & BATTLE_STAGE_CAMERA_SCRIPT;

    if (sStageCamera.atHome) {
        flags |= BATTLE_STAGE_CAMERA_AT_HOME;
    }

    if (IsEasing()) {
        flags |= BATTLE_STAGE_CAMERA_EASING;
    }

    if (IsShaking()) {
        flags |= BATTLE_STAGE_CAMERA_SHAKING;
    }

    fields->camFlags = flags;

    if (!sStageCamera.atHome) {
        fields->offHomeFrames++;

        if (sStageCamera.scriptActive && !(flags & BATTLE_STAGE_CAMERA_SCRIPT)) {
            fields->offHomeMoveFrames++;
        }
    }

    pose = sStageCamera.cur;

    // Home: the arena draws with its own view and projection, nothing is rebuilt
    if (sStageCamera.atHome) {
        sStageCamera.drawProjection = sStageCamera.home.projection;
    } else {
        // The debug views are fixed poses around the home target
        if (debugView != 0) {
            pose = sStageCamera.homePose;

            if (debugView == 1) {
                pose.yaw = FX32_CONST(-20);
            } else if (debugView == 2) {
                pose.yaw = FX32_CONST(20);
            } else {
                pose.pitch = FX32_CONST(15);
                pose.distance = FX32_CONST(0.8);
            }
        }

        BuildView(&pose);
    }

    if (visible) {
        UpdateAnchors(&pose);
    }
}

BOOL BattleStageCamera_IsHome(void)
{
    return sStageCamera.atHome;
}

const MtxFx43 *BattleStageCamera_View(void)
{
    return &sStageCamera.view;
}

const MtxFx44 *BattleStageCamera_Projection(void)
{
    return sStageCamera.drawProjection;
}

BOOL BattleStageCamera_GetSimilarity(int battler, BattleStageCameraSimilarity *similarity)
{
    const CameraAnchor *anchor;

    if (!sStageCamera.hasHome || sStageCamera.atHome || battler < 0 || battler >= MAX_BATTLERS) {
        return FALSE;
    }

    anchor = &sStageCamera.anchors[battler];

    if (!anchor->valid) {
        return FALSE;
    }

    similarity->homeX = anchor->homeX;
    similarity->homeY = anchor->homeY;
    similarity->nowX = anchor->nowX;
    similarity->nowY = anchor->nowY;
    similarity->scale = anchor->scale;
    return TRUE;
}

void BattleStageCamera_SetScriptActive(BOOL active)
{
    BOOL wasActive = sStageCamera.scriptActive;

    sStageCamera.scriptActive = active;

    if (!sStageCamera.hasHome) {
        return;
    }

    // Script end: a script that left the camera off home gets it back
    if (wasActive && !active && !PoseEquals(&sStageCamera.goal, &sStageCamera.homePose)) {
        sStageCamera.sequence = SEQUENCE_NONE;
        EaseTo(&sStageCamera.homePose, SCRIPT_END_HOME_FRAMES);
    }
}

// p' = now + s * (p - home) in pixels, as clip space: x_ndc = x / 128 - 1, y_ndc = 1 - y / 96.
// The translation is scaled by w, so it holds for any particle camera.
static void ParticleProjectionHook(MtxFx44 *projection)
{
    const CameraAnchor *anchor = &sStageCamera.particle;
    fx32 s, tx, ty;
    int r;

    if (sStageCamera.atHome || !sStageCamera.hasHome || !anchor->valid) {
        return;
    }

    s = anchor->scale;
    tx = s - FX32_ONE + (anchor->nowX - s * anchor->homeX) / 128;
    ty = FX32_ONE - s + (s * anchor->homeY - anchor->nowY) / 96;

    for (r = 0; r < 4; r++) {
        projection->m[r][0] = FX_Mul(projection->m[r][0], s) + FX_Mul(projection->m[r][3], tx);
        projection->m[r][1] = FX_Mul(projection->m[r][1], s) + FX_Mul(projection->m[r][3], ty);
    }
}

// The focus point of a battler: its foot, at the home target's height
static BOOL BattlerFocus(int battler, VecFx32 *point)
{
    int homeX, homeY;

    if (battler < 0 || battler >= MaxBattlers() || !BattlerFoot(battler, &homeX, &homeY, point)) {
        return FALSE;
    }

    point->y = sStageCamera.home.camTarget.y;
    return TRUE;
}

static BOOL CanRunCamera(void)
{
    return sStageCamera.hasHome && sStageCamera.fields != NULL && BattleStage_IsVisible();
}

// Every script command: marks the script and cancels any cinematic under way
static BOOL ScriptCommand(void)
{
    if (sStageCamera.fields == NULL) {
        return FALSE;
    }

    sStageCamera.fields->camFlags |= BATTLE_STAGE_CAMERA_SCRIPT;
    sStageCamera.fields->cinematicsSeen |= BATTLE_STAGE_CINEMATIC_SCRIPT;

    if (!CanRunCamera()) {
        return FALSE;
    }

    sStageCamera.sequence = SEQUENCE_NONE;
    return TRUE;
}

void BattleStage_CameraMove(int focus, int attacker, int defender, int distancePct, int yawDeg, int pitchDeg, int frames)
{
    CameraPose goal;
    VecFx32 a, b;

    if (!ScriptCommand()) {
        return;
    }

    goal = sStageCamera.cur;
    goal.focus = sStageCamera.home.camTarget;
    sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;

    switch (focus) {
    case STAGE_CAMERA_FOCUS_ATTACKER:
    case STAGE_CAMERA_FOCUS_DEFENDER: {
        int battler = focus == STAGE_CAMERA_FOCUS_ATTACKER ? attacker : defender;

        if (BattlerFocus(battler, &a)) {
            goal.focus = a;
            sStageCamera.particleFocus = PARTICLE_FOCUS_BATTLER;
            sStageCamera.particleBattlers[0] = battler;
        }
        break;
    }
    case STAGE_CAMERA_FOCUS_BETWEEN:
        if (BattlerFocus(attacker, &a) && BattlerFocus(defender, &b)) {
            goal.focus.x = (a.x + b.x) / 2;
            goal.focus.y = (a.y + b.y) / 2;
            goal.focus.z = (a.z + b.z) / 2;
            sStageCamera.particleFocus = PARTICLE_FOCUS_BETWEEN;
            sStageCamera.particleBattlers[0] = attacker;
            sStageCamera.particleBattlers[1] = defender;
        }
        break;
    default:
        break;
    }

    goal.distance = distancePct * FX32_ONE / 100;
    goal.yaw = yawDeg * FX32_ONE;
    goal.pitch = pitchDeg * FX32_ONE;

    if (goal.distance <= 0) {
        goal.distance = FX32_ONE;
    }

    EaseTo(&goal, frames);
}

void BattleStage_CameraOrbit(int yawDeltaDeg, int frames)
{
    CameraPose goal;

    if (!ScriptCommand()) {
        return;
    }

    goal = sStageCamera.goal;
    goal.yaw += yawDeltaDeg * FX32_ONE;
    EaseTo(&goal, frames);
}

void BattleStage_CameraShake(int amplitudePx, int frames)
{
    if (!ScriptCommand()) {
        return;
    }

    StartShake(amplitudePx, frames);
}

void BattleStage_CameraHome(int frames)
{
    if (!ScriptCommand()) {
        return;
    }

    EaseTo(&sStageCamera.homePose, frames);
}

BOOL BattleStage_IsCameraMoving(void)
{
    if (!CanRunCamera()) {
        return FALSE;
    }

    return IsEasing() || IsShaking();
}

void BattleStage_CameraScriptStart(void)
{
    if (!sStageCamera.hasHome || sStageCamera.fields == NULL) {
        return;
    }

    if (!PoseEquals(&sStageCamera.cur, &sStageCamera.homePose) || IsEasing() || IsShaking() || sStageCamera.sequence != SEQUENCE_NONE) {
        SnapHome();
        sStageCamera.fields->guardSnaps++;
    }

    sStageCamera.fields->camFlags &= ~BATTLE_STAGE_CAMERA_SCRIPT;
    sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;
    sStageCamera.scriptActive = TRUE;
}

void BattleStage_SetCameraScriptCinematic(u32 cinematic)
{
    if (sStageCamera.fields != NULL && BattleStage_IsVisible()) {
        sStageCamera.fields->cinematicsSeen |= cinematic;
    }
}

// A cinematic: ease to goal, shake, hold, then ease home
static void StartSequence(const CameraPose *goal, int frames, int shakePx, int shakeFrames, int holdFrames, int homeFrames)
{
    EaseTo(goal, frames);
    StartShake(shakePx, shakeFrames);
    sStageCamera.holdFrames = holdFrames;
    sStageCamera.homeFrames = homeFrames;
    sStageCamera.sequence = SEQUENCE_TO;
}

void BattleStage_StartBattleSweep(void)
{
    CameraPose goal;
    VecFx32 sum, point;
    int count = 0;
    int max, i;

    if (sStageCamera.sweepDone || !CanRunCamera()) {
        return;
    }

    sStageCamera.sweepDone = TRUE;

    if (TotemBattle_IsActive(sStageCamera.battleSys) || sStageCamera.scriptActive) {
        return;
    }

    sum.x = sum.y = sum.z = 0;
    max = MaxBattlers();

    for (i = 0; i < max; i++) {
        if ((BattleSystem_BattlerSlot(sStageCamera.battleSys, i) & 1) && BattlerFocus(i, &point)) {
            sum.x += point.x;
            sum.y += point.y;
            sum.z += point.z;
            count++;
        }
    }

    if (count == 0) {
        return;
    }

    goal = sStageCamera.homePose;
    goal.focus.x = sum.x / count;
    goal.focus.y = sum.y / count;
    goal.focus.z = sum.z / count;
    goal.yaw = FX32_CONST(-20);
    goal.pitch = FX32_CONST(-3);
    goal.distance = FX32_CONST(0.7);

    sStageCamera.fields->cinematicsSeen |= BATTLE_STAGE_CINEMATIC_SWEEP;
    sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;
    sStageCamera.menuWait = 0;
    StartSequence(&goal, 28, 0, 0, 10, 20);
}

BOOL BattleStage_IsCameraReadyForMenu(void)
{
    BOOL busy;

    if (!sStageCamera.hasHome || sStageCamera.fields == NULL) {
        return TRUE;
    }

    busy = !PoseEquals(&sStageCamera.cur, &sStageCamera.homePose) || IsEasing() || IsShaking() || sStageCamera.sequence != SEQUENCE_NONE;

    if (!busy) {
        sStageCamera.menuWait = 0;
        return TRUE;
    }

    if (++sStageCamera.menuWait > MENU_WAIT_MAX_FRAMES) {
        SnapHome();
        sStageCamera.menuWait = 0;
        return TRUE;
    }

    return FALSE;
}

static BOOL CanKick(void)
{
    return CanRunCamera()
        && !sStageCamera.scriptActive
        && !(sStageCamera.debugFlags != NULL && (*sStageCamera.debugFlags & BATTLE_STAGE_DEBUG_NO_CINEMATICS));
}

// A goal a fraction of the way from the home target toward a battler
static BOOL KickGoal(int battler, fx32 fraction, CameraPose *goal)
{
    VecFx32 point;

    if (!BattlerFocus(battler, &point)) {
        return FALSE;
    }

    *goal = sStageCamera.homePose;
    goal->focus.x += FX_Mul(point.x - goal->focus.x, fraction);
    goal->focus.y += FX_Mul(point.y - goal->focus.y, fraction);
    goal->focus.z += FX_Mul(point.z - goal->focus.z, fraction);
    sStageCamera.particleFocus = PARTICLE_FOCUS_BATTLER;
    sStageCamera.particleBattlers[0] = battler;
    return TRUE;
}

void BattleStage_CritKick(int battler, BOOL critical)
{
    CameraPose goal;

    if (!critical && !(sStageCamera.debugFlags != NULL && (*sStageCamera.debugFlags & BATTLE_STAGE_DEBUG_CRIT_KICK_ON_HIT))) {
        return;
    }

    if (!CanKick() || !KickGoal(battler, FX32_CONST(0.08), &goal)) {
        return;
    }

    // Push 4, shake 12 from the start, then home over 10: 22 frames
    goal.distance = FX32_CONST(0.92);
    sStageCamera.fields->cinematicsSeen |= BATTLE_STAGE_CINEMATIC_CRIT;
    StartSequence(&goal, 4, 3, 12, 0, 10);
}

void BattleStage_FaintKick(int battler)
{
    CameraPose goal;

    if (!CanKick() || !KickGoal(battler, FX32_CONST(0.1), &goal)) {
        return;
    }

    // Dip 6, shake 10 from the start, then home over 12: 22 frames
    goal.pitch = FX32_CONST(-3);
    sStageCamera.fields->cinematicsSeen |= BATTLE_STAGE_CINEMATIC_FAINT;
    StartSequence(&goal, 6, 2, 10, 0, 12);
}
