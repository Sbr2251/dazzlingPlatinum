#include "battle/battle_stage_camera.h"

#include <nitro.h>
#include <string.h>

#include "config/battle_stage.h"
#include "constants/battle.h"
#include "constants/battle/battle_anim.h"

#include "battle/battle_display.h"
#include "battle/battle_stage.h"
#include "battle/battle_stage_sprites.h"
#include "battle/healthbar.h"
#include "battle/ov16_0223DF00.h"

#include "particle_system.h"
#include "totem_battle.h"

// Clamps of the sprite scale and of the view depth it comes from
#define CAMERA_MIN_DEPTH FX32_CONST(0.25)
#define CAMERA_MAX_SCALE (FX32_ONE * 4)
#define CAMERA_MIN_SCALE (FX32_ONE / 16)
// The range of StageCameraZoom's vertical fov (home is 40 degrees)
#define CAMERA_MIN_FOV_DEG 10
#define CAMERA_MAX_FOV_DEG 60

// The contract's own timings (sweep, kicks, guard, menu cap) are in 60 Hz screen frames. The
// game logic, and so BattleStage_Draw and the script's Delay, runs at 30 Hz: one camera step
// is two screen frames. Script command lengths count steps, as Delay does.
#define SCREEN_FRAMES(n) (((n) + 1) / 2)

// The script-end ease home, when a script leaves the camera off home
#define SCRIPT_END_HOME_FRAMES SCREEN_FRAMES(12)
// The command menu waits for the camera at most this long, then snaps it home
#define MENU_WAIT_MAX_FRAMES SCREEN_FRAMES(90)
// The battle-start focus on the opponents: the push in, the least time it holds once there,
// the ease home once released, and the longest a send-out waits for it before a snap
#define INTRO_TO_FRAMES SCREEN_FRAMES(28)
#define INTRO_MIN_HOLD_FRAMES SCREEN_FRAMES(30)
#define INTRO_HOME_FRAMES SCREEN_FRAMES(20)
#define INTRO_WAIT_MAX_FRAMES SCREEN_FRAMES(120)
// The idle drift at the command menu: home for a moment, then a slow loop of poses (each an
// ease and a hold), and a quick ease home once the commands are in
#define IDLE_START_FRAMES SCREEN_FRAMES(60)
#define IDLE_MOVE_FRAMES SCREEN_FRAMES(180)
#define IDLE_HOLD_FRAMES SCREEN_FRAMES(50)
#define IDLE_END_FRAMES SCREEN_FRAMES(16)
// The debug flags that keep the drift off (and snap it home when set while it runs)
#define IDLE_OFF_FLAGS (BATTLE_STAGE_DEBUG_NO_CINEMATICS | BATTLE_STAGE_DEBUG_NO_IDLE_CAMERA)

// Shake periods in steps, different in x and y so the path isn't a line
#define SHAKE_PERIOD_X 4
#define SHAKE_PERIOD_Y 3

// The cut-line guard (cut_guard.md). The top screen's battle textbox is up for the whole
// battle, so off home the limit is its top edge; a change of limit eases over 8 screen frames.
#define CUT_EDGE_NONE 0x7FFF
#define CUT_LIMIT_TEXTBOX 144
#define CUT_LIMIT_SCREEN 192
#define CUT_LIMIT_STEP ((CUT_LIMIT_SCREEN - CUT_LIMIT_TEXTBOX) / SCREEN_FRAMES(8))
#define CUT_GUARD_MARGIN 1
#define CUT_GUARD_PASSES 2

enum CameraSequence {
    SEQUENCE_NONE = 0,
    SEQUENCE_TO, // easing to the goal
    SEQUENCE_HOLD, // holding there (and until the shake ends)
    SEQUENCE_INTRO, // the battle-start focus: there until released, at least holdFrames
    SEQUENCE_IDLE, // the command menu's drift: through sIdlePoses until ended
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
    BattleStageCutGuardFields *cutGuard;
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
    // The BG3 shake of a move, mirrored (BattleStage_SetBackdropShake); pixels, BG scroll sign
    int backdropDx;
    int backdropDy;
    int sequence;
    int holdFrames;
    int homeFrames; // the ease home at the end of the sequence
    // Script and cinematics
    BOOL scriptActive;
    BOOL sweepDone;
    int menuWait;
    BOOL introOver; // the focus started, or the player's side already sent out
    BOOL introRelease; // the player's send-out asked for the ease home
    BOOL introHoming; // easing home from the focus
    int introWait;
    BOOL introHidesHealthbars; // the battle-start focus keeps the opponents' healthbars hidden
    u8 heldHealthbars; // battlers whose healthbar slides in once the focus is home
    u8 scriptHidHealthbars; // battlers whose healthbar command 91 hid; shown again by the script end at the latest
    BOOL holdAfterScript; // the script's end pose becomes a held focus (the Totem aura)
    int idlePose; // the next of sIdlePoses
    BOOL idleHoming; // easing home from the idle drift
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
    int guardPan; // the cut guard's downward pan, px, added to the shake
} StageCamera;

static void ParticleProjectionHook(MtxFx44 *projection);
static BOOL IntroFocusHidesHealthbars(void);
static void ReleaseHealthbars(void);
static void ShowScriptHealthbars(void);

static StageCamera sStageCamera;

// Classic home x of each battler type (BATTLER_TYPE_*)
static const int sHomeX[BATTLER_TYPE_MAX] = { 64, 192, 40, 216, 80, 176 };

#define IDLE_SIDE_NONE -1

// The idle drift's loop. The focus moves towardPct of the way from the home target toward a
// side's mons; the poses stay inside the checked range (yaw +/-20, no farther than home).
typedef struct IdlePose {
    s8 side; // IDLE_SIDE_NONE, or 0 (the player's) / 1 (the opponent's)
    u8 towardPct;
    s8 yawDeg;
    s8 pitchDeg;
    u8 distancePct;
} IdlePose;

static const IdlePose sIdlePoses[] = {
    { IDLE_SIDE_NONE, 0, 10, 2, 100 }, // the wide shot, turned a little
    { 1, 35, -14, -2, 86 }, // in on the opponent
    { 0, 15, 12, 1, 100 }, // over toward the player's mon
    { IDLE_SIDE_NONE, 0, -6, 0, 100 }, // back through near home
};

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

static BOOL IsBackdropShaking(void)
{
    return sStageCamera.backdropDx != 0 || sStageCamera.backdropDy != 0;
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
    sStageCamera.backdropDx = 0;
    sStageCamera.backdropDy = 0;
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

// The shake offset in pixels for this frame, along camera-right and camera-up: a decaying
// sine, the same every time, plus the mirrored BG3 shake. BG3 scrolled by (dx, dy) shows its
// picture moved by (-dx, -dy), so the camera moves by dx right and dy down.
static void ShakePixels(int *dx, int *dy)
{
    int k = sStageCamera.shakeFrame;
    int n = sStageCamera.shakeFrames;
    int amp = sStageCamera.shakeAmp;

    *dx = sStageCamera.backdropDx;
    *dy = -sStageCamera.backdropDy;

    if (IsShaking()) {
        *dx += amp * FX_SinIdx((u16)(k * 0x10000 / SHAKE_PERIOD_X)) * (n - k) / n / FX32_ONE;
        *dy += amp * FX_SinIdx((u16)(k * 0x10000 / SHAKE_PERIOD_Y + 0x4000)) * (n - k) / n / FX32_ONE;
    }
}

static void BuildView(const CameraPose *pose)
{
    VecFx32 up = { 0, FX32_ONE, 0 };
    VecFx32 camPos, offset, target;

    PoseCamera(pose, &camPos, &offset);
    target = pose->focus;

    if (IsShaking() || IsBackdropShaking() || sStageCamera.guardPan != 0) {
        VecFx32 back, right, camUp;
        fx32 depth, perPixel, sx, sy;
        int dx, dy;

        // The camera going up moves the picture down
        ShakePixels(&dx, &dy);
        dy += sStageCamera.guardPan;
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
    *homeX = sHomeX[type] + TotemBattle_HomeOffsetX(type);
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

// The screen y (fx32) of a guarded battler's cut edge: a player-side battler whose sprite is cut
static BOOL CutEdgeY(int battler, fx32 *edgeY)
{
    const CameraAnchor *anchor = &sStageCamera.anchors[battler];
    int homeY;

    if (!anchor->valid
        || (BattleSystem_BattlerSlot(sStageCamera.battleSys, battler) & 1) != 0
        || !BattleStageSprites_CutHomeY(battler, &homeY)) {
        return FALSE;
    }

    *edgeY = anchor->nowY + anchor->scale * (homeY - anchor->homeY);
    return TRUE;
}

// Whole pixels the picture still has to move down for every cut edge to be a margin below the limit
static int CutShortfall(int limit)
{
    int max = MaxBattlers();
    int need = 0;
    int i;

    for (i = 0; i < max; i++) {
        fx32 edgeY;
        int n;

        if (CutEdgeY(i, &edgeY)) {
            n = ((limit + CUT_GUARD_MARGIN) * FX32_ONE - edgeY + FX32_ONE - 1) >> FX32_SHIFT;

            if (n > need) {
                need = n;
            }
        }
    }

    return need;
}

// After the view and anchors of the frame. Off home, pans the picture down until no cut edge
// is above the limit (the pan is exact at the focus depth only, so a second pass tops it up),
// then rebuilds the view and anchors. At home it only clears the fields.
static void UpdateCutGuard(BOOL visible, const CameraPose *pose)
{
    BattleStageCutGuardFields *guard = sStageCamera.cutGuard;
    int limit = CUT_LIMIT_TEXTBOX;
    BOOL violation = FALSE;
    int max, pass, need, i;

    if (guard == NULL) {
        return;
    }

    for (i = 0; i < MAX_BATTLERS; i++) {
        guard->cutEdgeY[i] = CUT_EDGE_NONE;
    }

    guard->guardPanPx = 0;

    if (sStageCamera.atHome || !visible) {
        guard->cutLimit = limit;
        return;
    }

    if (guard->cutLimit < limit) {
        guard->cutLimit = guard->cutLimit + CUT_LIMIT_STEP < limit ? guard->cutLimit + CUT_LIMIT_STEP : limit;
    } else if (guard->cutLimit > limit) {
        guard->cutLimit = guard->cutLimit - CUT_LIMIT_STEP > limit ? guard->cutLimit - CUT_LIMIT_STEP : limit;
    }

    for (pass = 0; pass < CUT_GUARD_PASSES; pass++) {
        need = CutShortfall(guard->cutLimit);

        if (need <= 0) {
            break;
        }

        sStageCamera.guardPan += need;
        BuildView(pose);
        UpdateAnchors(pose);
    }

    max = MaxBattlers();

    for (i = 0; i < max; i++) {
        fx32 edgeY;

        if (CutEdgeY(i, &edgeY)) {
            guard->cutEdgeY[i] = (s16)(edgeY >> FX32_SHIFT);

            if (guard->cutEdgeY[i] < guard->cutLimit - 1) {
                violation = TRUE;
            }
        }
    }

    guard->guardPanPx = (u16)sStageCamera.guardPan;

    if (sStageCamera.guardPan > 0) {
        guard->guardFrames++;
    }

    if (violation) {
        guard->cutViolations++;
    }
}

static BOOL IdleGoal(int index, CameraPose *goal);

static void AdvanceSequence(void)
{
    CameraPose goal;

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
    case SEQUENCE_INTRO:
        if (IsEasing()) {
            break;
        }

        if (sStageCamera.holdFrames > 0) {
            sStageCamera.holdFrames--;
        }

        if (sStageCamera.holdFrames <= 0 && sStageCamera.introRelease) {
            EaseTo(&sStageCamera.homePose, INTRO_HOME_FRAMES);
            sStageCamera.sequence = SEQUENCE_NONE;
            sStageCamera.introHoming = TRUE;
        }
        break;
    case SEQUENCE_IDLE:
        if (sStageCamera.debugFlags != NULL && (*sStageCamera.debugFlags & IDLE_OFF_FLAGS)) {
            SnapHome();
            break;
        }

        if (IsEasing()) {
            break;
        }

        if (sStageCamera.holdFrames > 0) {
            sStageCamera.holdFrames--;
            break;
        }

        if (IdleGoal(sStageCamera.idlePose, &goal)) {
            EaseTo(&goal, IDLE_MOVE_FRAMES);
        }

        sStageCamera.holdFrames = IDLE_HOLD_FRAMES;
        sStageCamera.idlePose = (sStageCamera.idlePose + 1) % NELEMS(sIdlePoses);
        break;
    default:
        if (sStageCamera.introHoming && !IsEasing()) {
            sStageCamera.introHoming = FALSE;
        }

        if (sStageCamera.idleHoming && !IsEasing()) {
            sStageCamera.idleHoming = FALSE;
        }
        break;
    }
}

void BattleStageCamera_Init(BattleSystem *battleSys, BattleStageCameraFields *fields, BattleStageCutGuardFields *cutGuard, const BattleStageCameraHome *home, const u32 *debugFlags)
{
    int i;

    memset(&sStageCamera, 0, sizeof(sStageCamera));
    memset(fields, 0, sizeof(*fields));
    memset(cutGuard, 0, sizeof(*cutGuard));

    for (i = 0; i < MAX_BATTLERS; i++) {
        cutGuard->cutEdgeY[i] = CUT_EDGE_NONE;
    }

    cutGuard->cutLimit = CUT_LIMIT_TEXTBOX;

    sStageCamera.battleSys = battleSys;
    sStageCamera.fields = fields;
    sStageCamera.cutGuard = cutGuard;
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
    sStageCamera.introHidesHealthbars = FALSE;
    sStageCamera.heldHealthbars = 0;
    sStageCamera.fields = NULL;
    sStageCamera.cutGuard = NULL;
    sStageCamera.battleSys = NULL;
}

void BattleStageCamera_Advance(BOOL visible, int debugView)
{
    BattleStageCameraFields *fields = sStageCamera.fields;
    CameraPose pose;
    BOOL poseHome;
    u32 flags;

    if (!sStageCamera.hasHome || fields == NULL) {
        return;
    }

    // The classic path never sees an off-home camera (SnapHome also drops the backdrop shake)
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

    if (sStageCamera.introHidesHealthbars && !IntroFocusHidesHealthbars()) {
        ReleaseHealthbars();
    }

    poseHome = PoseEquals(&sStageCamera.cur, &sStageCamera.homePose) && !IsEasing() && !IsShaking() && debugView == 0;
    // A mirrored BG3 shake rebuilds the view, but it is the move's own backdrop moving, not
    // the camera leaving home: the off-home counters skip it
    sStageCamera.atHome = poseHome && !IsBackdropShaking();

    flags = fields->camFlags & BATTLE_STAGE_CAMERA_SCRIPT;

    if (sStageCamera.atHome) {
        flags |= BATTLE_STAGE_CAMERA_AT_HOME;
    }

    if (IsEasing()) {
        flags |= BATTLE_STAGE_CAMERA_EASING;
    }

    if (IsShaking() || IsBackdropShaking()) {
        flags |= BATTLE_STAGE_CAMERA_SHAKING;
    }

    fields->camFlags = flags;

    if (!poseHome) {
        fields->offHomeFrames++;

        if (sStageCamera.scriptActive && !(flags & BATTLE_STAGE_CAMERA_SCRIPT)) {
            fields->offHomeMoveFrames++;
        }
    }

    pose = sStageCamera.cur;
    sStageCamera.guardPan = 0;

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

    UpdateCutGuard(visible, &pose);
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

    if (wasActive && !active) {
        ShowScriptHealthbars();
    }

    if (!sStageCamera.hasHome) {
        return;
    }

    if (!wasActive || active) {
        return;
    }

    // Script end: a held script pose stays until the next command menu request
    if (sStageCamera.holdAfterScript && !PoseEquals(&sStageCamera.goal, &sStageCamera.homePose)) {
        sStageCamera.holdAfterScript = FALSE;
        sStageCamera.introRelease = FALSE;
        sStageCamera.introWait = 0;
        sStageCamera.holdFrames = 0;
        sStageCamera.sequence = SEQUENCE_INTRO;
        return;
    }

    sStageCamera.holdAfterScript = FALSE;

    // Otherwise a script that left the camera off home gets it back
    if (!PoseEquals(&sStageCamera.goal, &sStageCamera.homePose)) {
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

// The battle-start focus is pushed in or easing home (not the Totem aura's held pose)
static BOOL IntroFocusHidesHealthbars(void)
{
    return sStageCamera.introHidesHealthbars && CanRunCamera()
        && (sStageCamera.sequence == SEQUENCE_INTRO || (sStageCamera.introHoming && IsEasing()));
}

// The held healthbars slide in as they would have at the send-out
static void ReleaseHealthbars(void)
{
    Healthbar *healthbar;
    int i;

    for (i = 0; i < MAX_BATTLERS; i++) {
        if (!(sStageCamera.heldHealthbars & (1 << i))) {
            continue;
        }

        healthbar = ov16_02263B08(BattleSystem_BattlerData(sStageCamera.battleSys, i));

        if (healthbar->mainSprite == NULL) {
            sStageCamera.heldHealthbars &= ~(1 << i);
            continue;
        }

        // Its own slide-in is still running (the bar is only hidden): wait for it
        if (!healthbar->doneScrolling) {
            continue;
        }

        Healthbar_Scroll(healthbar, HEALTHBAR_SCROLL_IN);
        Healthbar_Enable(healthbar, TRUE);
        sStageCamera.heldHealthbars &= ~(1 << i);
    }

    if (sStageCamera.heldHealthbars == 0) {
        sStageCamera.introHidesHealthbars = FALSE;
    }
}

// The healthbars command 91 hid come back
static void ShowScriptHealthbars(void)
{
    int i;

    if (sStageCamera.battleSys == NULL) {
        sStageCamera.scriptHidHealthbars = 0;
        return;
    }

    for (i = 0; i < MAX_BATTLERS && sStageCamera.scriptHidHealthbars; i++) {
        if (sStageCamera.scriptHidHealthbars & (1 << i)) {
            Healthbar_Enable(ov16_02263B08(BattleSystem_BattlerData(sStageCamera.battleSys, i)), TRUE);
            sStageCamera.scriptHidHealthbars &= ~(1 << i);
        }
    }
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
    goal.fov = sStageCamera.goal.fov; // a StageCameraZoom still easing keeps its target
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

// The vertical field of view in degrees, as pose.fov: the ratio of its half-angle tangent to
// the home one's (the projection scales fovySin by it). 0 is the home fov.
void BattleStage_CameraZoom(int fovDeg, int frames)
{
    CameraPose goal;
    fx32 sinA, cosA;

    if (!ScriptCommand()) {
        return;
    }

    goal = sStageCamera.goal;

    if (fovDeg <= 0) {
        goal.fov = FX32_ONE;
    } else {
        if (fovDeg < CAMERA_MIN_FOV_DEG) {
            fovDeg = CAMERA_MIN_FOV_DEG;
        } else if (fovDeg > CAMERA_MAX_FOV_DEG) {
            fovDeg = CAMERA_MAX_FOV_DEG;
        }

        SinCosDeg(fovDeg * FX32_ONE / 2, &sinA, &cosA);
        goal.fov = FX_Div(FX_Mul(sinA, sStageCamera.home.fovyCos), FX_Mul(cosA, sStageCamera.home.fovySin));
    }

    EaseTo(&goal, frames);
}

void BattleStage_ScriptHealthbars(BOOL visible)
{
    Healthbar *healthbar;
    int i;

    if (visible) {
        ShowScriptHealthbars();
        return;
    }

    if (!ScriptCommand()) {
        return;
    }

    for (i = 0; i < MaxBattlers(); i++) {
        healthbar = ov16_02263B08(BattleSystem_BattlerData(sStageCamera.battleSys, i));

        if (healthbar->mainSprite != NULL && ManagedSprite_GetDrawFlag(healthbar->mainSprite)) {
            Healthbar_Enable(healthbar, FALSE);
            sStageCamera.scriptHidHealthbars |= 1 << i;
        }
    }
}

void BattleStage_CameraShake(int amplitudePx, int frames)
{
    if (!ScriptCommand()) {
        return;
    }

    StartShake(amplitudePx, frames);
}

void BattleStage_SetBackdropShake(int dx, int dy)
{
    // Only while the arena shows; the next hidden frame drops it anyway (SnapHome)
    if (!sStageCamera.hasHome || sStageCamera.fields == NULL || !BattleStage_IsVisible()) {
        dx = 0;
        dy = 0;
    }

    sStageCamera.backdropDx = dx;
    sStageCamera.backdropDy = dy;
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

    // The idle drift is expected to be cut short; anything else off home is counted
    if (!PoseEquals(&sStageCamera.cur, &sStageCamera.homePose) || IsEasing() || IsShaking() || sStageCamera.sequence != SEQUENCE_NONE) {
        if (sStageCamera.sequence != SEQUENCE_IDLE && !sStageCamera.idleHoming) {
            sStageCamera.fields->guardSnaps++;
        }

        SnapHome();
    }

    sStageCamera.idleHoming = FALSE;
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

void BattleStage_HoldCameraAfterScript(void)
{
    if (sStageCamera.scriptActive && CanRunCamera()) {
        sStageCamera.holdAfterScript = TRUE;
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

// The mean focus point of a side's mons (0 the player's, 1 the opponent's)
static BOOL SideFocus(int side, VecFx32 *focus)
{
    VecFx32 sum, point;
    int count = 0;
    int max, i;

    sum.x = sum.y = sum.z = 0;
    max = MaxBattlers();

    for (i = 0; i < max; i++) {
        if ((BattleSystem_BattlerSlot(sStageCamera.battleSys, i) & 1) == side && BattlerFocus(i, &point)) {
            sum.x += point.x;
            sum.y += point.y;
            sum.z += point.z;
            count++;
        }
    }

    if (count == 0) {
        return FALSE;
    }

    focus->x = sum.x / count;
    focus->y = sum.y / count;
    focus->z = sum.z / count;
    return TRUE;
}

// The pose that looks at the opponents: pushed in and turned a little
static BOOL OpponentsGoal(CameraPose *goal)
{
    VecFx32 focus;

    if (!SideFocus(1, &focus)) {
        return FALSE;
    }

    *goal = sStageCamera.homePose;
    goal->focus = focus;
    goal->yaw = FX32_CONST(-20);
    goal->pitch = FX32_CONST(-3);
    goal->distance = FX32_CONST(0.7);
    return TRUE;
}

void BattleStage_StartBattleSweep(void)
{
    CameraPose goal;

    // The battle-start focus (Safari, Pal Park: nobody sends out) and the Totem aura's held
    // pose end at the first menu
    if (sStageCamera.sequence == SEQUENCE_INTRO) {
        sStageCamera.introRelease = TRUE;
        return;
    }

    if (sStageCamera.sweepDone || !CanRunCamera()) {
        return;
    }

    sStageCamera.sweepDone = TRUE;

    if (TotemBattle_IsActive(sStageCamera.battleSys) || sStageCamera.scriptActive || !OpponentsGoal(&goal)) {
        return;
    }

    sStageCamera.fields->cinematicsSeen |= BATTLE_STAGE_CINEMATIC_SWEEP;
    sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;
    sStageCamera.menuWait = 0;
    StartSequence(&goal, SCREEN_FRAMES(28), 0, 0, SCREEN_FRAMES(10), SCREEN_FRAMES(20));
}

void BattleStage_StartIntroFocus(void)
{
    CameraPose goal;

    if (sStageCamera.introOver || sStageCamera.sweepDone || !CanRunCamera()
        || TotemBattle_IsActive(sStageCamera.battleSys) || sStageCamera.scriptActive || !OpponentsGoal(&goal)) {
        return;
    }

    // It stands in for the first-menu sweep
    sStageCamera.introOver = TRUE;
    sStageCamera.sweepDone = TRUE;
    sStageCamera.introRelease = FALSE;
    sStageCamera.introWait = 0;
    sStageCamera.introHidesHealthbars = TRUE;
    sStageCamera.fields->cinematicsSeen |= BATTLE_STAGE_CINEMATIC_SWEEP;
    sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;
    EaseTo(&goal, INTRO_TO_FRAMES);
    sStageCamera.holdFrames = INTRO_MIN_HOLD_FRAMES;
    sStageCamera.sequence = SEQUENCE_INTRO;
}

void BattleStage_EndIntroFocus(void)
{
    sStageCamera.introOver = TRUE;

    if (sStageCamera.sequence == SEQUENCE_INTRO) {
        sStageCamera.introRelease = TRUE;
    }
}

BOOL BattleStage_HoldIntroHealthbar(int battler)
{
    if ((BattleSystem_BattlerSlot(sStageCamera.battleSys, battler) & 1) == 0 || !IntroFocusHidesHealthbars()) {
        return FALSE;
    }

    sStageCamera.heldHealthbars |= 1 << battler;
    return TRUE;
}

BOOL BattleStage_IsIntroFocusDone(void)
{
    if (!CanRunCamera() || (sStageCamera.sequence != SEQUENCE_INTRO && !(sStageCamera.introHoming && IsEasing()))) {
        sStageCamera.introWait = 0;
        return TRUE;
    }

    if (++sStageCamera.introWait > INTRO_WAIT_MAX_FRAMES) {
        SnapHome();
        sStageCamera.introHoming = FALSE;
        sStageCamera.introWait = 0;
        return TRUE;
    }

    return FALSE;
}

BOOL BattleStage_GetSideOffset(int side, int *dx, int *dy)
{
    fx32 sumX = 0, sumY = 0;
    int count = 0;
    int max, i;

    *dx = 0;
    *dy = 0;

    if (!sStageCamera.hasHome || sStageCamera.atHome || sStageCamera.battleSys == NULL) {
        return FALSE;
    }

    max = MaxBattlers();

    for (i = 0; i < max; i++) {
        const CameraAnchor *anchor = &sStageCamera.anchors[i];

        if (anchor->valid && (BattleSystem_BattlerSlot(sStageCamera.battleSys, i) & 1) == side) {
            sumX += anchor->nowX - anchor->homeX * FX32_ONE;
            sumY += anchor->nowY - anchor->homeY * FX32_ONE;
            count++;
        }
    }

    if (count == 0) {
        return FALSE;
    }

    *dx = (sumX / count + FX32_HALF) >> FX32_SHIFT;
    *dy = (sumY / count + FX32_HALF) >> FX32_SHIFT;
    return TRUE;
}

BOOL BattleStage_IsCameraReadyForMenu(void)
{
    BOOL busy;

    if (!sStageCamera.hasHome || sStageCamera.fields == NULL) {
        return TRUE;
    }

    // The idle drift runs under the menu (the next battler's menu in a double battle)
    if (sStageCamera.sequence == SEQUENCE_IDLE) {
        sStageCamera.menuWait = 0;
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

static BOOL IdleGoal(int index, CameraPose *goal)
{
    const IdlePose *idle = &sIdlePoses[index];
    VecFx32 focus;
    fx32 toward = idle->towardPct * FX32_ONE / 100;

    *goal = sStageCamera.homePose;

    if (idle->side != IDLE_SIDE_NONE) {
        if (!SideFocus(idle->side, &focus)) {
            return FALSE;
        }

        goal->focus.x += FX_Mul(focus.x - goal->focus.x, toward);
        goal->focus.y += FX_Mul(focus.y - goal->focus.y, toward);
        goal->focus.z += FX_Mul(focus.z - goal->focus.z, toward);
    }

    goal->yaw = idle->yawDeg * FX32_ONE;
    goal->pitch = idle->pitchDeg * FX32_ONE;
    goal->distance = idle->distancePct * FX32_ONE / 100;
    return TRUE;
}

void BattleStage_StartIdleCamera(void)
{
    if (sStageCamera.sequence == SEQUENCE_IDLE || !CanRunCamera() || sStageCamera.scriptActive
        || sStageCamera.sequence != SEQUENCE_NONE || IsEasing() || IsShaking()
        || !PoseEquals(&sStageCamera.cur, &sStageCamera.homePose)
        || (sStageCamera.debugFlags != NULL && (*sStageCamera.debugFlags & IDLE_OFF_FLAGS))) {
        return;
    }

    sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;
    sStageCamera.idlePose = 0;
    sStageCamera.idleHoming = FALSE;
    sStageCamera.holdFrames = IDLE_START_FRAMES;
    sStageCamera.sequence = SEQUENCE_IDLE;
}

void BattleStage_EndIdleCamera(void)
{
    if (sStageCamera.sequence != SEQUENCE_IDLE) {
        return;
    }

    sStageCamera.sequence = SEQUENCE_NONE;
    sStageCamera.holdFrames = 0;

    if (!PoseEquals(&sStageCamera.cur, &sStageCamera.homePose) || IsEasing()) {
        EaseTo(&sStageCamera.homePose, IDLE_END_FRAMES);
        sStageCamera.idleHoming = TRUE;
    }
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

    // Push 4, shake 12 from the start, then home over 10: 22 screen frames
    goal.distance = FX32_CONST(0.92);
    sStageCamera.fields->cinematicsSeen |= BATTLE_STAGE_CINEMATIC_CRIT;
    StartSequence(&goal, SCREEN_FRAMES(4), 3, SCREEN_FRAMES(12), 0, SCREEN_FRAMES(10));
}

void BattleStage_FaintKick(int battler)
{
    CameraPose goal;

    if (!CanKick() || !KickGoal(battler, FX32_CONST(0.1), &goal)) {
        return;
    }

    // Dip 6, shake 10 from the start, then home over 12: 22 screen frames
    goal.pitch = FX32_CONST(-3);
    sStageCamera.fields->cinematicsSeen |= BATTLE_STAGE_CINEMATIC_FAINT;
    StartSequence(&goal, SCREEN_FRAMES(6), 2, SCREEN_FRAMES(10), 0, SCREEN_FRAMES(12));
}
