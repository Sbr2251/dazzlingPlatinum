#include "battle/battle_stage_camera.h"

#include <nitro.h>
#include <string.h>

#include "config/battle_stage.h"
#include "constants/battle.h"
#include "constants/battle/battle_anim.h"

#include "battle/battle_display.h"
#include "battle/battle_stage.h"
#include "battle/battle_stage_particles.h"
#include "battle/battle_stage_sprites.h"
#include "battle/healthbar.h"
#include "battle/ov16_0223DF00.h"

#include "battle_anim/ov12_02235E94.h"
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
// The BW2 intro shots (intro.md; btlv_scu.c's 0x231/0x237-0x239/0x232/0x234).
// Wild: open close on the wild mon with the fade-in and pull out to home before the
// opponent's healthbar. Trainer: open on the opponent's trainer, ease out a little through
// "You are challenged by", tighten on the throw. Then the player's send-out shot: a pan to the
// player's side with a slight pull back, held until every mon thrown is out, then home.
#define INTRO_OPEN_FRAMES SCREEN_FRAMES(120)
#define INTRO_FOE_OPEN_FRAMES SCREEN_FRAMES(150)
#define INTRO_FOE_THROW_FRAMES SCREEN_FRAMES(40)
#define INTRO_SENDOUT_TO_FRAMES SCREEN_FRAMES(36)
#define INTRO_SENDOUT_SETTLE_FRAMES SCREEN_FRAMES(16)
#define INTRO_SENDOUT_HOME_FRAMES SCREEN_FRAMES(30)
// A send-out shot that is never released (no mon came out) gives up after this long
#define INTRO_SENDOUT_MAX_FRAMES SCREEN_FRAMES(720)
// The 2D trainer and ball OBJs follow the camera up to this scale (an affine double-size OBJ)
#define INTRO_OBJ_MAX_SCALE (FX32_ONE * 2)
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

// The BW2 intro shots (bw2vis:intro)
enum IntroShot {
    INTRO_SHOT_NONE = 0, // the legacy battle-start focus, or the Totem aura's held pose
    INTRO_SHOT_OPEN, // wild: pulling out from the wild mon to home
    INTRO_SHOT_FOE, // trainer: on the opponent's side until its healthbar
    INTRO_SHOT_SENDOUT, // the player's side sends out
    INTRO_SHOT_HOMING, // easing home from the send-out shot (outside SEQUENCE_INTRO)
};

enum IntroPoseID {
    INTRO_POSE_WILD_OPEN = 0,
    INTRO_POSE_FOE_OPEN,
    INTRO_POSE_FOE_HOLD,
    INTRO_POSE_FOE_MON,
    INTRO_POSE_SENDOUT,
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
    u8 throwWaiting; // player battlers whose trainer throw is waiting for the focus to get home
    u8 throwLate[MAX_BATTLERS]; // task frames that throw waited, owed by its healthbar's slide-in
    int introShot; // enum IntroShot: the BW2 intro shot on screen (SEQUENCE_INTRO) or easing home
    BOOL introShotsPlayed; // the intro opened with a shot (the legacy battle-start focus stays off)
    BOOL introTrainer; // a trainer battle's intro: the send-out shot starts at the opponent's healthbar
    BOOL introNoSendOutShot; // an opponent's OAM copy can't follow the camera: the player sends out at home
    int introShotFrames; // frames the send-out shot has held
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

static BOOL ParticleProjectionHook(MtxFx44 *projection);
static void BallDrawHook(ManagedSprite *sprite, int target, int sign);
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
static void AdvanceIntro(void);

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
        AdvanceIntro();
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
    BattleStageParticles_Init(battleSys, home, debugFlags); // bw2vis:particles-3d
    BallRotation_SetDrawHook(BallDrawHook); // bw2vis:intro
}

void BattleStageCamera_Free(void)
{
    if (sStageCamera.hasHome) {
        ParticleSystem_SetProjectionHook(NULL);
        BattleStageParticles_Free(); // bw2vis:particles-3d
        BallRotation_SetDrawHook(NULL); // bw2vis:intro
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
        sStageCamera.introShot = INTRO_SHOT_NONE; // bw2vis:intro: a held pose, not an intro shot
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

// bw2vis:particles-3d. Off home every particle follows the mons around it, each by that mon's
// own similarity (battle_stage_particles.c, the particle hook). The single similarity below is
// the fallback (no battler anchors) and the A/B debug path (BATTLE_STAGE_DEBUG_PARTICLES_2D);
// BATTLE_STAGE_DEBUG_PARTICLES_PLANE draws them on the 3D battle plane instead.
// p' = now + s * (p - home) in pixels, as clip space: x_ndc = x / 128 - 1, y_ndc = 1 - y / 96.
// The translation is scaled by w, so it holds for any particle camera.
static BOOL ParticleProjectionHook(MtxFx44 *projection)
{
    const CameraAnchor *anchor = &sStageCamera.particle;
    u32 debugFlags = sStageCamera.debugFlags != NULL ? *sStageCamera.debugFlags : 0;
    fx32 s, tx, ty;
    int r;

    // A debug view stays off home while the stage hides; the classic picture never follows it
    if (sStageCamera.atHome || !sStageCamera.hasHome || !BattleStage_IsVisible()) {
        return FALSE;
    }

    if (!(debugFlags & BATTLE_STAGE_DEBUG_PARTICLES_2D)) {
        if (debugFlags & BATTLE_STAGE_DEBUG_PARTICLES_PLANE) {
            if (BattleStageParticles_ProjectOnPlane(projection)) {
                return FALSE;
            }
        } else if (BattleStageParticles_BeginSystem(projection)) {
            return TRUE;
        }
    }

    if (!anchor->valid) {
        return FALSE;
    }

    s = anchor->scale;
    tx = s - FX32_ONE + (anchor->nowX - s * anchor->homeX) / 128;
    ty = FX32_ONE - s + (s * anchor->homeY - anchor->nowY) / 96;

    for (r = 0; r < 4; r++) {
        projection->m[r][0] = FX_Mul(projection->m[r][0], s) + FX_Mul(projection->m[r][3], tx);
        projection->m[r][1] = FX_Mul(projection->m[r][1], s) + FX_Mul(projection->m[r][3], ty);
    }

    return FALSE;
}

// bw2vis:particles-3d. A battler's world foot point and its side (0 the player's, 1 the opponent's)
BOOL BattleStageCamera_BattlerFoot(int battler, int *side, VecFx32 *foot)
{
    int homeX, homeY;

    if (!sStageCamera.hasHome || sStageCamera.battleSys == NULL || battler < 0 || battler >= MaxBattlers()
        || !BattlerFoot(battler, &homeX, &homeY, foot)) {
        return FALSE;
    }

    *side = BattleSystem_BattlerSlot(sStageCamera.battleSys, battler) & 1;
    return TRUE;
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
    // bw2vis:intro: only the wild opening's pull out and the legacy focus hold them; the trainer
    // and send-out shots show the opponent's healthbar as BW2 does
    if (sStageCamera.introShot != INTRO_SHOT_OPEN && sStageCamera.introShot != INTRO_SHOT_NONE) {
        return FALSE;
    }

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

// ---- The battle intro (bw2vis:intro; docs/living_battle_stage/intro.md) ----

typedef struct IntroPose {
    s8 side; // 0 the player's, 1 the opponent's
    u8 towardPct; // how far the focus moves from the home target toward the side's mons
    u8 distancePct;
    s8 yawDeg;
    s8 pitchDeg;
} IntroPose;

// The opponent close-ups keep the legacy focus's angle (it swung yaw -20; these turn less so a
// trainer OBJ, a flat 2D sprite, reads as standing there). BW2's own presets frame the opponent
// at 1.50x and the player's mon at 0.91x, a pan with a slight pull back (btlv_effvm.c:468-505):
// the send-out shot is that player preset, about 0.92x, panned only 40% of the way so the
// platform stays bottom left and the player's ball tray, which is screen-fixed, beside it.
static const IntroPose sIntroPoses[] = {
    [INTRO_POSE_WILD_OPEN] = { 1, 100, 62, -14, -3 },
    [INTRO_POSE_FOE_OPEN] = { 1, 100, 80, -12, -2 },
    [INTRO_POSE_FOE_HOLD] = { 1, 100, 92, -8, -1 },
    [INTRO_POSE_FOE_MON] = { 1, 100, 82, -14, -2 },
    [INTRO_POSE_SENDOUT] = { 0, 40, 94, 0, 3 },
};

static BOOL IntroGoal(int pose, CameraPose *goal)
{
    const IntroPose *intro = &sIntroPoses[pose];
    VecFx32 focus;

    if (!SideFocus(intro->side, &focus)) {
        return FALSE;
    }

    *goal = sStageCamera.homePose;
    goal->focus.x += FX_Mul(focus.x - goal->focus.x, intro->towardPct * FX32_ONE / 100);
    goal->focus.y += FX_Mul(focus.y - goal->focus.y, intro->towardPct * FX32_ONE / 100);
    goal->focus.z += FX_Mul(focus.z - goal->focus.z, intro->towardPct * FX32_ONE / 100);
    goal->yaw = intro->yawDeg * FX32_ONE;
    goal->pitch = intro->pitchDeg * FX32_ONE;
    goal->distance = intro->distancePct * FX32_ONE / 100;
    return TRUE;
}

// The particles (a ball's burst, the Platinum entry effects) follow a side's mons
static void IntroParticleFocus(int side)
{
    int battlers[2];
    int max = MaxBattlers();
    int count = 0;
    int i;

    for (i = 0; i < max && count < 2; i++) {
        if ((BattleSystem_BattlerSlot(sStageCamera.battleSys, i) & 1) == side) {
            battlers[count++] = i;
        }
    }

    if (count == 0) {
        sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;
    } else if (count == 1) {
        sStageCamera.particleFocus = PARTICLE_FOCUS_BATTLER;
        sStageCamera.particleBattlers[0] = battlers[0];
    } else {
        sStageCamera.particleFocus = PARTICLE_FOCUS_BETWEEN;
        sStageCamera.particleBattlers[0] = battlers[0];
        sStageCamera.particleBattlers[1] = battlers[1];
    }
}

// The intro shot on screen now: INTRO_SHOT_NONE when none (or only the legacy focus)
static int ActiveIntroShot(void)
{
    if (!CanRunCamera()) {
        return INTRO_SHOT_NONE;
    }

    if (sStageCamera.sequence == SEQUENCE_INTRO) {
        return sStageCamera.introShot;
    }

    if (sStageCamera.introShot == INTRO_SHOT_HOMING) {
        if (sStageCamera.introHoming && IsEasing()) {
            return INTRO_SHOT_HOMING;
        }

        sStageCamera.introShot = INTRO_SHOT_NONE;
    }

    return INTRO_SHOT_NONE;
}

static BOOL StartIntroShot(int shot, int pose, int frames)
{
    CameraPose goal;

    if (!IntroGoal(pose, &goal)) {
        return FALSE;
    }

    EaseTo(&goal, frames);
    sStageCamera.introShot = shot;
    sStageCamera.introRelease = FALSE;
    sStageCamera.introWait = 0;
    sStageCamera.introShotFrames = 0;
    sStageCamera.holdFrames = 0;
    sStageCamera.sequence = SEQUENCE_INTRO;
    return TRUE;
}

static void StartSendOutShot(void)
{
    int shot = ActiveIntroShot();

    if (!sStageCamera.introShotsPlayed || sStageCamera.introNoSendOutShot
        || shot == INTRO_SHOT_SENDOUT || shot == INTRO_SHOT_HOMING || sStageCamera.scriptActive) {
        return;
    }

    if (StartIntroShot(INTRO_SHOT_SENDOUT, INTRO_POSE_SENDOUT, INTRO_SENDOUT_TO_FRAMES)) {
        IntroParticleFocus(0);
    }
}

// SEQUENCE_INTRO, from AdvanceSequence
static void AdvanceIntro(void)
{
    switch (sStageCamera.introShot) {
    case INTRO_SHOT_OPEN:
        // Home: the pull out is over, the opponent's healthbar may come in
        if (!IsEasing()) {
            sStageCamera.sequence = SEQUENCE_NONE;
            sStageCamera.introShot = INTRO_SHOT_NONE;
        }
        return;
    case INTRO_SHOT_FOE:
        // Held until the opponent's healthbar (StartIntroFocus) or the player's throw
        return;
    case INTRO_SHOT_SENDOUT:
        if (++sStageCamera.introShotFrames > INTRO_SENDOUT_MAX_FRAMES) {
            sStageCamera.introRelease = TRUE;
        }

        if (IsEasing() || !sStageCamera.introRelease) {
            return;
        }

        if (sStageCamera.holdFrames > 0) {
            sStageCamera.holdFrames--;
            return;
        }

        EaseTo(&sStageCamera.homePose, INTRO_SENDOUT_HOME_FRAMES);
        sStageCamera.sequence = SEQUENCE_NONE;
        sStageCamera.introShot = INTRO_SHOT_HOMING;
        sStageCamera.introHoming = TRUE;
        return;
    default:
        break;
    }

    // The legacy focus and the Totem aura's held pose: there until released, at least holdFrames
    if (IsEasing()) {
        return;
    }

    if (sStageCamera.holdFrames > 0) {
        sStageCamera.holdFrames--;
    }

    if (sStageCamera.holdFrames <= 0 && sStageCamera.introRelease) {
        EaseTo(&sStageCamera.homePose, INTRO_HOME_FRAMES);
        sStageCamera.sequence = SEQUENCE_NONE;
        sStageCamera.introHoming = TRUE;
    }
}

void BattleStage_StartIntroOpen(void)
{
    u32 battleType, battleStatus;
    BOOL totem;
    int pose;

    if (sStageCamera.introOver || sStageCamera.introShotsPlayed || !CanRunCamera() || sStageCamera.scriptActive) {
        return;
    }

    battleType = BattleSystem_BattleType(sStageCamera.battleSys);
    battleStatus = BattleSystem_BattleStatus(sStageCamera.battleSys);

    // A recorded battle sends the player's side out first: it opens at home. Giratina keeps its
    // own entrance (it drops in from above, the platforms slide): the legacy focus follows it.
    if (battleStatus & (BATTLE_STATUS_RECORDED | BATTLE_STATUS_GIRATINA)) {
        return;
    }

    totem = TotemBattle_IsActive(sStageCamera.battleSys);
    sStageCamera.introTrainer = (battleType & BATTLE_TYPE_TRAINER) != 0;
    pose = sStageCamera.introTrainer ? INTRO_POSE_FOE_OPEN : INTRO_POSE_WILD_OPEN;

    if (!StartIntroShot(INTRO_SHOT_NONE, pose, 0)) {
        return;
    }

    sStageCamera.introShotsPlayed = TRUE;
    sStageCamera.introOver = TRUE;
    sStageCamera.sweepDone = TRUE;
    sStageCamera.introNoSendOutShot = FALSE;
    sStageCamera.fields->cinematicsSeen |= BATTLE_STAGE_CINEMATIC_INTRO;

    // The Totem's own push in is the aura script's; the critic tells the two apart by bit 0
    if (!totem) {
        sStageCamera.fields->cinematicsSeen |= BATTLE_STAGE_CINEMATIC_SWEEP;
    }

    IntroParticleFocus(1);

    if (sStageCamera.introTrainer) {
        StartIntroShot(INTRO_SHOT_FOE, INTRO_POSE_FOE_HOLD, INTRO_FOE_OPEN_FRAMES);
    } else {
        EaseTo(&sStageCamera.homePose, INTRO_OPEN_FRAMES);
        sStageCamera.introShot = INTRO_SHOT_OPEN;
        sStageCamera.introHidesHealthbars = TRUE;
    }
}

void BattleStage_IntroEnemyThrow(int battler)
{
    (void)battler;

    if (ActiveIntroShot() != INTRO_SHOT_FOE) {
        return;
    }

    StartIntroShot(INTRO_SHOT_FOE, INTRO_POSE_FOE_MON, INTRO_FOE_THROW_FRAMES);
    IntroParticleFocus(1);
}

void BattleStage_IntroPlayerSendOut(void)
{
    StartSendOutShot();
    BattleStage_EndIntroFocus();
}

void BattleStage_IntroMonOut(int battler, BOOL lastOut)
{
    (void)battler;

    if (lastOut && ActiveIntroShot() == INTRO_SHOT_SENDOUT && !sStageCamera.introRelease) {
        sStageCamera.introRelease = TRUE;
        sStageCamera.holdFrames = INTRO_SENDOUT_SETTLE_FRAMES;
    }
}

BOOL BattleStage_IntroSpriteToOAM(int battler)
{
    // A streamed opponent's OAM copy stays hidden (BattleStage_IsSpriteStreamed): the stage
    // sprite, which follows the camera, is what shows
    if (sStageCamera.introShotsPlayed && BattleStage_IsSpriteStreamed(battler)) {
        return TRUE;
    }

    // A copy that shows can't follow the camera: the player's side sends out at home
    if (sStageCamera.introShotsPlayed && !sStageCamera.introNoSendOutShot) {
        sStageCamera.introNoSendOutShot = TRUE;

        if (ActiveIntroShot() == INTRO_SHOT_SENDOUT) {
            sStageCamera.introRelease = TRUE;
            sStageCamera.holdFrames = 0;
        }
    }

    BattleStage_EndIntroFocus();
    return BattleStage_IsIntroFocusDone();
}

void BattleStage_StartIntroFocus(void)
{
    CameraPose goal;

    // A trainer's intro: the opponent is out, its healthbar comes in and the camera turns to
    // the player's side (BW2 shows the foe's gauge as 0x232 starts, btlv_scu.c:807-811)
    if (sStageCamera.introShotsPlayed) {
        if (sStageCamera.introTrainer && ActiveIntroShot() == INTRO_SHOT_FOE) {
            StartSendOutShot();
        }
        return;
    }

    // The legacy focus, when the intro didn't open with a shot (the stage wasn't visible then)
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
    sStageCamera.introShot = INTRO_SHOT_NONE;
    sStageCamera.fields->cinematicsSeen |= BATTLE_STAGE_CINEMATIC_SWEEP;
    sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;
    EaseTo(&goal, INTRO_TO_FRAMES);
    sStageCamera.holdFrames = INTRO_MIN_HOLD_FRAMES;
    sStageCamera.sequence = SEQUENCE_INTRO;
}

void BattleStage_EndIntroFocus(void)
{
    sStageCamera.introOver = TRUE;

    // Only the legacy focus; the intro shots end on their own beats
    if (sStageCamera.sequence == SEQUENCE_INTRO && sStageCamera.introShot == INTRO_SHOT_NONE) {
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

// The player's trainer throw. The trainer and the ball are 2D OBJs, but they follow the
// camera (BattleStage_FollowIntroSprite), so during the intro shots they throw at once: from
// the opponent's shot the camera turns to the send-out shot as the throw starts. Only the
// legacy focus (an OBJ that couldn't follow) still makes the throw wait for home; the frames
// it waited are owed by the healthbar (HoldSendOutHealthbar), so the bar comes in after the
// Pokemon, as long after the throw as without the stage.
BOOL BattleStage_IsIntroThrowReady(int battler)
{
    int shot = ActiveIntroShot();

    if (sStageCamera.introShotsPlayed && !sStageCamera.introNoSendOutShot) {
        if (shot != INTRO_SHOT_SENDOUT && shot != INTRO_SHOT_HOMING) {
            StartSendOutShot();
        }

        return TRUE;
    }

    if (battler < 0 || battler >= MAX_BATTLERS) {
        return BattleStage_IsIntroFocusDone();
    }

    if (BattleStage_IsIntroFocusDone()) {
        sStageCamera.throwWaiting &= ~(1 << battler);
        return TRUE;
    }

    sStageCamera.throwWaiting |= 1 << battler;

    if (sStageCamera.throwLate[battler] < 255) {
        sStageCamera.throwLate[battler]++;
    }

    return FALSE;
}

// The player's healthbar comes in once the send-out shot is home (BW2 shows the player's
// gauge after 0x234 ends, btlv_scu.c:838-842)
BOOL BattleStage_HoldSendOutHealthbar(int battler)
{
    int shot;

    if (battler < 0 || battler >= MAX_BATTLERS) {
        return FALSE;
    }

    shot = ActiveIntroShot();

    if ((shot == INTRO_SHOT_SENDOUT || shot == INTRO_SHOT_HOMING)
        && (BattleSystem_BattlerSlot(sStageCamera.battleSys, battler) & 1) == 0) {
        return TRUE;
    }

    if (sStageCamera.throwWaiting & (1 << battler)) {
        return TRUE;
    }

    if (sStageCamera.throwLate[battler] > 0) {
        sStageCamera.throwLate[battler]--;
        return TRUE;
    }

    return FALSE;
}

// The mean similarity of a side's anchors, for the 2D trainer and ball OBJs
static BOOL GetSideSimilarity(int side, BattleStageCameraSimilarity *similarity)
{
    fx32 homeX = 0, homeY = 0, nowX = 0, nowY = 0, scale = 0;
    int count = 0;
    int max, i;

    if (!sStageCamera.hasHome || sStageCamera.atHome || sStageCamera.battleSys == NULL) {
        return FALSE;
    }

    max = MaxBattlers();

    for (i = 0; i < max; i++) {
        const CameraAnchor *anchor = &sStageCamera.anchors[i];

        if (anchor->valid && (BattleSystem_BattlerSlot(sStageCamera.battleSys, i) & 1) == side) {
            homeX += anchor->homeX;
            homeY += anchor->homeY;
            nowX += anchor->nowX;
            nowY += anchor->nowY;
            scale += anchor->scale;
            count++;
        }
    }

    if (count == 0) {
        return FALSE;
    }

    similarity->homeX = homeX / count;
    similarity->homeY = homeY / count;
    similarity->nowX = nowX / count;
    similarity->nowY = nowY / count;
    similarity->scale = scale / count;
    return TRUE;
}

// Moves (sign 1) and scales a 2D OBJ with its side's similarity for one draw, and puts it back
// (sign -1). The scale is capped where an affine double-size OBJ still fits; past it the OBJ
// is well off screen anyway.
void BattleStage_FollowIntroSprite(ManagedSprite *managedSprite, int side, int sign, BattleStageIntroSpriteSave *save)
{
    BattleStageCameraSimilarity similarity;
    Sprite *sprite;
    fx32 s, x, y;

    if (managedSprite == NULL || managedSprite->sprite == NULL) {
        return;
    }

    sprite = managedSprite->sprite;

    if (sign < 0) {
        if (save->moved) {
            sprite->position = save->position;
            sprite->affineScale = save->scale;
            sprite->affineOverwriteMode = save->mode;
            save->moved = FALSE;
        }
        return;
    }

    save->moved = FALSE;

    if (!GetSideSimilarity(side, &similarity)) {
        return;
    }

    save->position = sprite->position;
    save->scale = sprite->affineScale;
    save->mode = sprite->affineOverwriteMode;
    save->moved = TRUE;

    s = similarity.scale > INTRO_OBJ_MAX_SCALE ? INTRO_OBJ_MAX_SCALE : similarity.scale;
    x = similarity.nowX + FX_Mul(similarity.scale, sprite->position.x - similarity.homeX * FX32_ONE);
    y = similarity.nowY + FX_Mul(similarity.scale, sprite->position.y - similarity.homeY * FX32_ONE);

    // Far off screen the OBJ position would wrap: park it out of view
    if (x < -128 * FX32_ONE || x > 384 * FX32_ONE || y < -128 * FX32_ONE || y > 320 * FX32_ONE) {
        x = -128 * FX32_ONE;
        y = -128 * FX32_ONE;
    }

    sprite->position.x = x;
    sprite->position.y = y;
    sprite->affineScale.x = FX_Mul(save->scale.x, s);
    sprite->affineScale.y = FX_Mul(save->scale.y, s);
    sprite->affineOverwriteMode = AFFINE_OVERWRITE_MODE_DOUBLE;
}

// The ball OBJ of a throw (its own task draws it): it follows its target's side
static BattleStageIntroSpriteSave sBallSpriteSave;

static void BallDrawHook(ManagedSprite *sprite, int target, int sign)
{
    if (sStageCamera.battleSys == NULL || target < 0 || target >= MaxBattlers()) {
        sBallSpriteSave.moved = FALSE;
        return;
    }

    BattleStage_FollowIntroSprite(sprite, BattleSystem_BattlerSlot(sStageCamera.battleSys, target) & 1, sign, &sBallSpriteSave);
}

// The old translate-only follow, kept for callers outside the intro
BOOL BattleStage_GetSideOffset(int side, int *dx, int *dy)
{
    BattleStageCameraSimilarity similarity;

    *dx = 0;
    *dy = 0;

    if (!GetSideSimilarity(side, &similarity)) {
        return FALSE;
    }

    *dx = ((similarity.nowX - similarity.homeX * FX32_ONE) + FX32_HALF) >> FX32_SHIFT;
    *dy = ((similarity.nowY - similarity.homeY * FX32_ONE) + FX32_HALF) >> FX32_SHIFT;
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
