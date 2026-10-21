#include "battle/battle_stage_camera.h"

#include <nitro.h>
#include <string.h>

#include "config/battle_stage.h"
#include "constants/battle.h"
#include "constants/battle/battle_anim.h"

#include "battle/battle_display.h"
#include "battle/battle_stage.h"
#include "battle/battle_stage_layout.h"
#include "battle/battle_stage_sprites.h"
#include "battle/battle_textbox.h"
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
// The debug flags that keep the command menu camera off (and snap it home when set while it runs)
#define IDLE_OFF_FLAGS (BATTLE_STAGE_DEBUG_NO_CINEMATICS | BATTLE_STAGE_DEBUG_NO_IDLE_CAMERA)

// bw2vis:camera-core. The motion runs on BW2's clock, 60 Hz screen frames: an ease or a shake is a
// function of the screen frames since it started, and each Advance (one BattleStage_Draw, so two
// screen frames at the battle's 30 Hz) moves that clock by STEP_FRAMES. BW2's frame counts are used
// as they are; a script's drawn frames are doubled.
#define STEP_FRAMES 2
// The command menu camera (BW2: btlv_input.c, btlv_effect.c). Every prompt eases onto the battler
// choosing as BtlvEffect_ZoomCamera does (MoveTo, 10 frames, brake 8); 900 frames (15 s) after the
// prompt the idle shots start; the commands in, it eases home.
#define PROMPT_FRAMES 10
#define PROMPT_BRAKE 8
#define IDLE_WAIT_FRAMES 900
#define MENU_HOME_FRAMES 10
#define MENU_HOME_BRAKE 8
// The beats after the first prompt (switches, the catch, the end of a trainer battle): an ease in,
// then a hold, then an ease home
#define BEAT_IN_FRAMES 16
#define BEAT_IN_BRAKE 12
#define BEAT_HOME_FRAMES 20
#define BEAT_HOME_BRAKE 14
#define BEAT_SENDOUT_HOLD 24 // after the sent-out battler's healthbar shows
#define BEAT_RECALL_MAX 300 // a recall with no send-in after it gives up
#define BEAT_HOLD_FOREVER -1

// Shake periods in steps for the old decaying shake, different in x and y so the path isn't a line
#define SHAKE_PERIOD_X 4
#define SHAKE_PERIOD_Y 3
// BW2's shake: a quarter swing of this many screen frames unless the command says otherwise. Two
// steps, so even at 30 Hz the shake is seen to start from rest (half the amplitude, then all of it)
#define SHAKE_QUARTER_FRAMES (2 * STEP_FRAMES)

// The cut-line guard (cut_guard.md). Off home the limit is the battle textbox's top edge while
// any of the box shows, the screen bottom once it has faded (battle_textbox.c); a change of
// limit eases over 8 screen frames.
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
    SEQUENCE_IDLE, // the command menu's idle shots, after the prompt's wait, until ended
    SEQUENCE_PROMPT, // the command prompt: on the battler choosing, until the idle shots or the end
    SEQUENCE_SELECT, // move and target select in a double battle: the wide shot, then the idle shots
    SEQUENCE_BEAT, // a beat after the first prompt: there until released (beatHold), then home
};

enum CameraCurve {
    CURVE_LINEAR = 0, // BW2's MoveTo: constant speed on the chord, an optional half-speed tail
    CURVE_SMOOTH, // smoothstep on each pose component (an arc for a turn)
};

enum ShakeMode {
    SHAKE_TRIANGLE_Y = 0, // BW2: a triangle wave on world up, constant amplitude, whole swings
    SHAKE_TRIANGLE_X, // the same sideways (camera right, on the ground)
    SHAKE_DECAY, // the old shake: decaying sines on both screen axes
};

enum CameraBeat {
    BEAT_NONE = 0,
    BEAT_RECALL,
    BEAT_SENDOUT,
    BEAT_CATCH,
    BEAT_END,
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
    // Motion (bw2vis:camera-core: on the 60 Hz clock, see STEP_FRAMES)
    CameraPose cur;
    CameraPose from;
    CameraPose goal;
    VecFx32 fromPos; // the camera positions of from and goal: CURVE_LINEAR moves on the line between
    VecFx32 goalPos;
    int curve;
    int easeT; // screen frames into the ease
    int easeLen; // BW2's frames: the length at full speed
    int easeBrake; // BW2's brakeFrames: the speed halves after easeBrake - 1 frames; 0 never
    int easeEnd; // screen frames until it ends (a brake makes it longer than easeLen)
    int shakeMode;
    int shakeT; // screen frames into the shake
    int shakeEnd;
    int shakeQuarter; // screen frames per quarter swing (the triangle)
    int shakeAmp; // pixels
    // The BG3 shake of a move, mirrored (BattleStage_SetBackdropShake); pixels, BG scroll sign
    int backdropDx;
    int backdropDy;
    int sequence;
    int holdFrames;
    int homeFrames; // the ease home at the end of the sequence, in drawn frames
    int homeCurve; // and its curve and brake (bw2vis:camera-core)
    int homeBrake;
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
    int idlePose; // the idle shot playing, or -1 (bw2vis:camera-core)
    BOOL idleHoming; // easing home from the idle drift
    // The command menu camera and the beats (bw2vis:camera-core)
    BOOL promptSeen; // the first command prompt of the battle has opened: the beats may play
    int promptBattler;
    int idleTimer; // screen frames since the last prompt (or double battle move select)
    int idleLast; // the last idle shot, never played twice in a row
    int idleHold; // screen frames the idle shot holds at its end pose
    u32 idleRandom; // the idle shots' own random state (the battle's RNG is never touched)
    int beat;
    int beatBattler;
    int beatHold; // screen frames still to hold; BEAT_HOLD_FOREVER until the battle ends
    // Home offset of the camera in angle form, for poses built from a camera position
    u16 homeAzimuth;
    u16 homeElevation;
    fx32 homeLength;
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
static void BallDrawHook(ManagedSprite *sprite, int target, int sign);
static BOOL IntroFocusHidesHealthbars(void);
static void ReleaseHealthbars(void);
static void ShowScriptHealthbars(void);

static StageCamera sStageCamera;

// bw2vis:camera-core. The camera's state for the critic and the capture scripts, read from RAM through
// the xMAP (camera.md, "Debug block"). The force* fields are a test hook: with forcePose set, the
// camera shows that pose (relative to home) instead, like a debug view.
typedef struct StageCameraDebug {
    u32 magic; // CAMERA_DEBUG_MAGIC once the camera is set up
    s32 sequence; // enum CameraSequence
    s32 curve; // enum CameraCurve of the ease
    s32 brake; // its BW2 brakeFrames
    s32 easeT; // screen frames into the ease
    s32 easeEnd; // its length in screen frames, 0 when not easing
    s32 shakeMode; // enum ShakeMode
    s32 shakeAmp; // pixels
    s32 shakeT;
    s32 shakeEnd; // 0 when not shaking
    s32 promptBattler; // the battler the last prompt framed, -1 before the first
    s32 idleShot; // the idle shot playing, -1 for none
    s32 idleTimer; // screen frames since the prompt
    s32 beat; // enum CameraBeat
    s32 flags; // bit 0: the first prompt has opened
    s32 yaw; // the current pose: fx32 degrees, fx32 distance, focus relative to the home target
    s32 pitch;
    s32 distance;
    s32 focusX;
    s32 focusY;
    s32 focusZ;
    s32 progress; // fx32 0..1 of the ease
    s32 advanceTicks; // OS ticks of the last Advance, and the most of any this battle
    s32 advanceTicksMax;
    s32 forcePose;
    s32 forceFocusX;
    s32 forceFocusY;
    s32 forceFocusZ;
    s32 forceYaw; // fx32 degrees
    s32 forcePitch;
    s32 forceDistance; // fx32, 0 = home
} StageCameraDebug;

#define CAMERA_DEBUG_MAGIC 0x4D414343

StageCameraDebug sStageCameraDebug;

// Classic home x of each battler type (BATTLER_TYPE_*)
static const int sHomeX[BATTLER_TYPE_MAX] = { 64, 192, 40, 216, 80, 176 };

// bw2vis:camera-core. BW2's preset shot of each battler slot (btlv_effvm.c:468-505, CmdCameraMovePreset
// types 0-5): the home camera trucked onto the mon with no turn. The mon's size against home, as the ratio
// of its distances to the two cameras: 0.91x for a single battle's own mon, 1.50x for the opponent; in a
// double battle 1.19x / 1.06x for the left / right mon and 1.47x / 1.49x for the right / left foe.
static const fx32 sPresetScale[BATTLER_TYPE_MAX] = {
    FX32_CONST(0.91), FX32_CONST(1.50), FX32_CONST(1.19), FX32_CONST(1.47), FX32_CONST(1.06), FX32_CONST(1.49)
};
// The screen row of the mon's feet in BW2's preset shot of each slot (projected with BW2's camera), as the
// same share of our scene, which ends at the text box (row 144) where BW2's ends at the screen's bottom
static const s16 sPresetRow[BATTLER_TYPE_MAX] = { 124, 113, 125, 111, 139, 104 };
// And the column. BW2 has its mons near the middle (your side at 113-123, the foe's at 133-135); ours
// stand a little further out to each side, where the bigger Platinum healthbar boxes (yours at x 136
// and up, the foe's at x 128 and down) leave them clear.
#define PRESET_COL_PLAYER 96
#define PRESET_COL_ENEMY 152
// BW2's wide doubles shot (preset 14, which also shrinks every sprite): the own mons at about 0.68x
#define WIDE_PLAYER_SCALE FX32_CONST(0.68)
// The camera's reach: every one of the 30 arenas still covers the whole scene from 1.6x the home distance
// (BG0 renders, camera.md "Camera range"); the wide shot needs about 1.4x
#define CAMERA_MAX_DISTANCE FX32_CONST(1.45)
// The beats close in on the battler along the ray through its feet, so the 2D Poke Ball and trainer
// OBJs, which only move with the side, keep their place (camera.md, "Beats")
#define BEAT_ENEMY_SCALE FX32_CONST(1.35)
#define BEAT_PLAYER_SCALE FX32_CONST(1.12)

// The idle shots (BW2 picks one of 6 idle effect scripts at random, never the same twice in a row; their
// camera data is in the ROM's archive 66, which isn't extracted). Each is a cut to a start pose and a slow
// move at constant speed to an end pose, built like BW2's from its presets: a slide (no turn) onto a mon
// at its preset size, a turn about a point (CameraRotate), and a truck of the home pose (preset 18).
enum IdleFocus {
    IDLE_FOCUS_HOME = 0, // the home target, moved towardPct of the way to a side
    IDLE_FOCUS_ENEMY, // the opponents' preset (the first opponent, or both)
    IDLE_FOCUS_PLAYER, // the battler whose command is being picked, at its preset
};

typedef struct IdleShotPose {
    u8 focus; // enum IdleFocus
    s8 towardPct; // IDLE_FOCUS_HOME: toward the opponents (+) or the player's side (-)
    u8 scalePct; // battler focus: the mon's size against home; 0 = its preset size
    s8 yawDeg;
    s8 pitchDeg;
} IdleShotPose;

typedef struct IdleShot {
    IdleShotPose start;
    IdleShotPose end;
    u16 moveFrames; // screen frames, constant speed
    u16 holdFrames;
} IdleShot;

static const IdleShot sIdleShots[] = {
    // 0x235-like: the foe, a slow push to its preset size
    { { IDLE_FOCUS_ENEMY, 0, 125, 0, 0 }, { IDLE_FOCUS_ENEMY, 0, 0, 0, 0 }, 240, 60 },
    // your mon at its preset size, sliding a little toward the foe
    { { IDLE_FOCUS_PLAYER, 0, 0, 0, 0 }, { IDLE_FOCUS_HOME, -45, 0, 0, 0 }, 240, 60 },
    // a slow turn across the field about the home target
    { { IDLE_FOCUS_HOME, 0, 0, -16, 0 }, { IDLE_FOCUS_HOME, 0, 0, 16, 0 }, 300, 45 },
    // a low turn about the foe
    { { IDLE_FOCUS_ENEMY, 0, 120, 10, -3 }, { IDLE_FOCUS_ENEMY, 0, 120, -10, -3 }, 240, 45 },
    // preset 18: the home pose trucked across, from the foe's side to yours
    { { IDLE_FOCUS_HOME, 30, 0, 0, 0 }, { IDLE_FOCUS_HOME, -30, 0, 0, 0 }, 300, 45 },
    // over the field from your side to a high look at the foe
    { { IDLE_FOCUS_HOME, -20, 0, 8, 2 }, { IDLE_FOCUS_HOME, 40, 0, -6, 4 }, 240, 60 },
};

#define IDLE_SHOT_COUNT NELEMS(sIdleShots)

static BOOL PoseEquals(const CameraPose *a, const CameraPose *b)
{
    return a->focus.x == b->focus.x && a->focus.y == b->focus.y && a->focus.z == b->focus.z
        && a->yaw == b->yaw && a->pitch == b->pitch && a->distance == b->distance && a->fov == b->fov;
}

static BOOL IsEasing(void)
{
    return sStageCamera.easeEnd > 0 && sStageCamera.easeT < sStageCamera.easeEnd;
}

static BOOL IsShaking(void)
{
    return sStageCamera.shakeEnd > 0 && sStageCamera.shakeT < sStageCamera.shakeEnd;
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
    sStageCamera.easeT = 0;
    sStageCamera.easeEnd = 0;
    sStageCamera.shakeT = 0;
    sStageCamera.shakeEnd = 0;
    sStageCamera.backdropDx = 0;
    sStageCamera.backdropDy = 0;
    sStageCamera.sequence = SEQUENCE_NONE;
    sStageCamera.beat = BEAT_NONE;
    sStageCamera.idlePose = -1;
}

static void PoseCamera(const CameraPose *pose, VecFx32 *camPos, VecFx32 *offsetOut);

// bw2vis:camera-core. Ease from wherever the camera is now over frames screen frames (BW2's frames); 0
// snaps. CURVE_LINEAR is BW2's MoveTo (btlv_camera.c:92-111, :185-204): the camera position and the
// target move in a straight line at constant speed, and brake (BW2's brakeFrames, 0 for none) halves the
// speed after brake - 1 frames. CURVE_SMOOTH eases each pose component in and out.
static void EaseToCurve(const CameraPose *goal, int frames, int brake, int curve)
{
    VecFx32 offset;

    sStageCamera.from = sStageCamera.cur;
    sStageCamera.goal = *goal;
    sStageCamera.easeT = 0;
    sStageCamera.curve = curve;
    sStageCamera.easeLen = frames;
    sStageCamera.easeBrake = curve == CURVE_LINEAR ? brake : 0;

    if (frames <= 0) {
        sStageCamera.cur = *goal;
        sStageCamera.easeEnd = 0;
        return;
    }

    if (sStageCamera.easeBrake > 0 && sStageCamera.easeBrake <= frames) {
        sStageCamera.easeEnd = 2 * frames - (sStageCamera.easeBrake - 1);
    } else {
        sStageCamera.easeEnd = frames;
    }

    if (curve == CURVE_LINEAR) {
        PoseCamera(&sStageCamera.from, &sStageCamera.fromPos, &offset);
        PoseCamera(&sStageCamera.goal, &sStageCamera.goalPos, &offset);
    }
}

// The ease the chunk 4 cinematics use: smoothstep over a number of drawn frames (steps)
static void EaseTo(const CameraPose *goal, int frames)
{
    EaseToCurve(goal, frames * STEP_FRAMES, 0, CURVE_SMOOTH);
}

// The share of the way the ease has come, 0..FX32_ONE
static fx32 EaseProgress(void)
{
    int t = sStageCamera.easeT;
    int n = sStageCamera.easeLen;
    int full;
    fx32 x;

    if (n <= 0) {
        return FX32_ONE;
    }

    if (sStageCamera.curve == CURVE_SMOOTH) {
        x = t * FX32_ONE / n;
        return FX_Mul(FX_Mul(x, x), 3 * FX32_ONE - 2 * x);
    }

    full = sStageCamera.easeBrake > 0 && sStageCamera.easeBrake <= n ? sStageCamera.easeBrake - 1 : n;

    if (t <= full) {
        x = t * FX32_ONE / n;
    } else {
        x = (2 * full + (t - full)) * FX32_ONE / (2 * n);
    }

    return x > FX32_ONE ? FX32_ONE : x;
}

// BW2's shake (btlv_camera.c:114-138, btlv_effect.c:1441-1490): a triangle wave of the full amplitude on
// one axis, count whole swings of 4 quarters of quarter screen frames each, starting and ending at rest
static void StartShakeBW2(int mode, int amplitudePx, int quarter, int count)
{
    if (amplitudePx <= 0 || count <= 0) {
        sStageCamera.shakeEnd = 0;
        sStageCamera.shakeT = 0;
        return;
    }

    if (quarter <= 0) {
        quarter = SHAKE_QUARTER_FRAMES;
    }

    sStageCamera.shakeMode = mode;
    sStageCamera.shakeAmp = amplitudePx;
    sStageCamera.shakeQuarter = quarter;
    sStageCamera.shakeT = 0;
    sStageCamera.shakeEnd = 4 * quarter * count;
}

// A shake lasting about frames drawn frames: whole swings of BW2's triangle, at least one
static void StartShake(int amplitudePx, int frames)
{
    int quarter = SHAKE_QUARTER_FRAMES;

    if (frames <= 0) {
        StartShakeBW2(SHAKE_TRIANGLE_Y, 0, quarter, 0);
        return;
    }

    StartShakeBW2(SHAKE_TRIANGLE_Y, amplitudePx, quarter, (frames * STEP_FRAMES + 4 * quarter - 1) / (4 * quarter));
}

static fx32 Lerp(fx32 a, fx32 b, fx32 t)
{
    return a + FX_Mul(b - a, t);
}

// fx32 degrees of an angle index difference
static fx32 IdxToDeg(int idx)
{
    return (s16)idx * 45 / 2;
}

// The yaw, pitch and distance of a pose whose camera sits at offset from its focus: the inverse of
// PoseCamera (the pitch lifts the home offset's elevation, the yaw turns its azimuth)
static void PoseAnglesFromOffset(const VecFx32 *offset, CameraPose *pose)
{
    fx32 horizontal = FX_Sqrt(FX_Mul(offset->x, offset->x) + FX_Mul(offset->z, offset->z));
    u16 azimuth = FX_Atan2Idx(offset->x, offset->z);
    u16 elevation = FX_Atan2Idx(offset->y, horizontal);

    pose->yaw = IdxToDeg((u16)(azimuth - sStageCamera.homeAzimuth));
    pose->pitch = IdxToDeg((u16)(elevation - sStageCamera.homeElevation));
    pose->distance = FX_Div(VEC_Mag(offset), sStageCamera.homeLength);
}

static void AdvanceEase(int frames)
{
    CameraPose *from = &sStageCamera.from;
    CameraPose *goal = &sStageCamera.goal;
    CameraPose *cur = &sStageCamera.cur;
    fx32 s;

    if (!IsEasing()) {
        return;
    }

    sStageCamera.easeT += frames;

    if (sStageCamera.easeT >= sStageCamera.easeEnd) {
        *cur = *goal;
        sStageCamera.easeEnd = 0;
        sStageCamera.easeT = 0;
        return;
    }

    s = EaseProgress();

    cur->focus.x = Lerp(from->focus.x, goal->focus.x, s);
    cur->focus.y = Lerp(from->focus.y, goal->focus.y, s);
    cur->focus.z = Lerp(from->focus.z, goal->focus.z, s);
    cur->fov = Lerp(from->fov, goal->fov, s);

    if (sStageCamera.curve == CURVE_LINEAR) {
        VecFx32 pos, offset;

        // The camera on the straight line between the two positions (a turn takes the chord)
        pos.x = Lerp(sStageCamera.fromPos.x, sStageCamera.goalPos.x, s);
        pos.y = Lerp(sStageCamera.fromPos.y, sStageCamera.goalPos.y, s);
        pos.z = Lerp(sStageCamera.fromPos.z, sStageCamera.goalPos.z, s);
        VEC_Subtract(&pos, &cur->focus, &offset);
        PoseAnglesFromOffset(&offset, cur);
    } else {
        cur->yaw = Lerp(from->yaw, goal->yaw, s);
        cur->pitch = Lerp(from->pitch, goal->pitch, s);
        cur->distance = Lerp(from->distance, goal->distance, s);
    }
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

// The shake offset in pixels for this frame, along camera-right and camera-up: the old decaying
// sines (now from rest on both axes: the vertical one started at full amplitude, a one-frame jump),
// plus the mirrored BG3 shake. BG3 scrolled by (dx, dy) shows its picture moved by (-dx, -dy), so the
// camera moves by dx right and dy down. BW2's triangle is ShakeTriangle's, along a world axis.
static void ShakePixels(int *dx, int *dy)
{
    int k = sStageCamera.shakeT / STEP_FRAMES;
    int n = sStageCamera.shakeEnd / STEP_FRAMES;
    int amp = sStageCamera.shakeAmp;

    *dx = sStageCamera.backdropDx;
    *dy = -sStageCamera.backdropDy;

    if (IsShaking() && sStageCamera.shakeMode == SHAKE_DECAY && n > 0) {
        *dx += amp * FX_SinIdx((u16)(k * 0x10000 / SHAKE_PERIOD_X)) * (n - k) / n / FX32_ONE;
        *dy += amp * FX_SinIdx((u16)(k * 0x10000 / SHAKE_PERIOD_Y)) * (n - k) / n / FX32_ONE;
    }
}

// BW2's triangle in pixels at this frame (EffTool_Move type 3): up to +amp over the first quarter, down
// through 0 to -amp, back to 0, so it never jumps and ends exactly at rest. fx32 pixels.
static fx32 ShakeTriangle(void)
{
    int q = sStageCamera.shakeQuarter;
    int j;

    if (!IsShaking() || sStageCamera.shakeMode == SHAKE_DECAY || q <= 0) {
        return 0;
    }

    j = sStageCamera.shakeT % (4 * q);

    if (j <= q) {
        return sStageCamera.shakeAmp * FX32_ONE * j / q;
    } else if (j <= 3 * q) {
        return sStageCamera.shakeAmp * FX32_ONE * (2 * q - j) / q;
    }

    return sStageCamera.shakeAmp * FX32_ONE * (j - 4 * q) / q;
}

static void BuildView(const CameraPose *pose)
{
    VecFx32 up = { 0, FX32_ONE, 0 };
    VecFx32 camPos, offset, target;
    fx32 triangle = ShakeTriangle();

    PoseCamera(pose, &camPos, &offset);
    target = pose->focus;

    if (IsShaking() || IsBackdropShaking() || sStageCamera.guardPan != 0) {
        VecFx32 back, right, camUp, shift;
        fx32 depth, perPixel, sx, sy, w;
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

        shift.x = FX_Mul(right.x, sx) + FX_Mul(camUp.x, sy);
        shift.y = FX_Mul(right.y, sx) + FX_Mul(camUp.y, sy);
        shift.z = FX_Mul(right.z, sx) + FX_Mul(camUp.z, sy);

        // BW2's shake moves the position and the target together along a world axis: up, or sideways
        // along the ground (camera right has no height, as the camera never rolls)
        if (triangle != 0) {
            w = FX_Mul(perPixel, triangle);

            if (sStageCamera.shakeMode == SHAKE_TRIANGLE_X) {
                shift.x += FX_Mul(right.x, w);
                shift.z += FX_Mul(right.z, w);
            } else {
                shift.y += w;
            }
        }

        VEC_Add(&camPos, &shift, &camPos);
        VEC_Add(&target, &shift, &target);
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

    // bw2vis:layout - the foot at the battler's BW2 place (battle_stage_layout.c)
    {
        int dx, dy;

        if (BattleStageLayout_Offset(battler, &dx, &dy)) {
            *homeX += dx;
            *homeY += dy;
            return BattleStageSprites_GroundPointAt(*homeX, *homeY, foot);
        }
    }

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
    // bw2vis:layout - the text box fades out for animations (battle_textbox.c)
    int limit = BattleTextbox_IsClear() ? CUT_LIMIT_SCREEN : CUT_LIMIT_TEXTBOX;
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

static void StartNextIdleShot(void);
static void IdleTestHook(void);
static void AdvanceBeat(void);
static void AdvanceIntro(void);

// The command menu camera is off: a debug flag (the critic's frame comparisons at the menu want home)
static BOOL MenuCameraOff(void)
{
    return sStageCamera.debugFlags != NULL && (*sStageCamera.debugFlags & IDLE_OFF_FLAGS);
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
            EaseToCurve(&sStageCamera.homePose, sStageCamera.homeFrames * STEP_FRAMES, sStageCamera.homeBrake, sStageCamera.homeCurve);
            sStageCamera.sequence = SEQUENCE_NONE;
        }
        break;
    case SEQUENCE_INTRO:
        AdvanceIntro();
        break;
    // bw2vis:camera-core. The command menu: the prompt (or the wide select shot) holds until 900 frames
    // after the prompt, then the idle shots follow one another (BtlvEffect_UpdateIdleEffect)
    case SEQUENCE_PROMPT:
    case SEQUENCE_SELECT:
        if (MenuCameraOff()) {
            SnapHome();
            break;
        }

        sStageCamera.idleTimer += STEP_FRAMES;
        IdleTestHook();

        if (sStageCamera.sequence != SEQUENCE_IDLE && sStageCamera.idleTimer >= IDLE_WAIT_FRAMES && !IsEasing()) {
            sStageCamera.sequence = SEQUENCE_IDLE;
            StartNextIdleShot();
        }
        break;
    case SEQUENCE_IDLE:
        if (MenuCameraOff()) {
            SnapHome();
            break;
        }

        sStageCamera.idleTimer += STEP_FRAMES;
        IdleTestHook();

        if (IsEasing()) {
            break;
        }

        if (sStageCamera.idleHold > 0) {
            sStageCamera.idleHold -= STEP_FRAMES;
            break;
        }

        StartNextIdleShot();
        break;
    case SEQUENCE_BEAT:
        AdvanceBeat();
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

    // bw2vis:camera-core: the home offset in angle form (PoseAnglesFromOffset), the menu camera's state
    // and the debug block
    {
        VecFx32 offset;
        fx32 horizontal;

        VEC_Subtract(&home->camPos, &home->camTarget, &offset);
        horizontal = FX_Sqrt(FX_Mul(offset.x, offset.x) + FX_Mul(offset.z, offset.z));
        sStageCamera.homeAzimuth = FX_Atan2Idx(offset.x, offset.z);
        sStageCamera.homeElevation = FX_Atan2Idx(offset.y, horizontal);
        sStageCamera.homeLength = VEC_Mag(&offset);
    }

    sStageCamera.promptBattler = -1;
    sStageCamera.idleLast = -1;
    sStageCamera.idleRandom = (u32)OS_GetTick() | 1;
    memset(&sStageCameraDebug, 0, sizeof(sStageCameraDebug));
    sStageCameraDebug.magic = CAMERA_DEBUG_MAGIC;

    ParticleSystem_SetProjectionHook(ParticleProjectionHook);
    BallRotation_SetDrawHook(BallDrawHook); // bw2vis:intro
}

void BattleStageCamera_Free(void)
{
    if (sStageCamera.hasHome) {
        ParticleSystem_SetProjectionHook(NULL);
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

// bw2vis:camera-core: the debug block, after the frame's pose is known
static void UpdateDebugBlock(const CameraPose *pose, OSTick startTick)
{
    StageCameraDebug *dbg = &sStageCameraDebug;
    s32 ticks = (s32)(OS_GetTick() - startTick);

    dbg->sequence = sStageCamera.sequence;
    dbg->curve = sStageCamera.curve;
    dbg->brake = sStageCamera.easeBrake;
    dbg->easeT = IsEasing() ? sStageCamera.easeT : 0;
    dbg->easeEnd = IsEasing() ? sStageCamera.easeEnd : 0;
    dbg->shakeMode = sStageCamera.shakeMode;
    dbg->shakeAmp = sStageCamera.shakeAmp;
    dbg->shakeT = IsShaking() ? sStageCamera.shakeT : 0;
    dbg->shakeEnd = IsShaking() ? sStageCamera.shakeEnd : 0;
    dbg->promptBattler = sStageCamera.promptBattler;
    dbg->idleShot = sStageCamera.sequence == SEQUENCE_IDLE ? sStageCamera.idlePose : -1;
    dbg->idleTimer = sStageCamera.idleTimer;
    dbg->beat = sStageCamera.beat;
    dbg->flags = sStageCamera.promptSeen ? 1 : 0;
    dbg->yaw = pose->yaw;
    dbg->pitch = pose->pitch;
    dbg->distance = pose->distance;
    dbg->focusX = pose->focus.x - sStageCamera.home.camTarget.x;
    dbg->focusY = pose->focus.y - sStageCamera.home.camTarget.y;
    dbg->focusZ = pose->focus.z - sStageCamera.home.camTarget.z;
    dbg->progress = IsEasing() ? EaseProgress() : 0;
    dbg->advanceTicks = ticks;

    if (ticks > dbg->advanceTicksMax) {
        dbg->advanceTicksMax = ticks;
    }
}

void BattleStageCamera_Advance(BOOL visible, int debugView)
{
    BattleStageCameraFields *fields = sStageCamera.fields;
    CameraPose pose;
    BOOL poseHome;
    BOOL forced;
    OSTick startTick;
    u32 flags;

    if (!sStageCamera.hasHome || fields == NULL) {
        return;
    }

    startTick = OS_GetTick();

    // The classic path never sees an off-home camera (SnapHome also drops the backdrop shake)
    if (!visible) {
        SnapHome();
    } else {
        AdvanceEase(STEP_FRAMES);

        if (IsShaking()) {
            sStageCamera.shakeT += STEP_FRAMES;

            if (sStageCamera.shakeT >= sStageCamera.shakeEnd) {
                sStageCamera.shakeEnd = 0;
                sStageCamera.shakeT = 0;
            }
        }

        AdvanceSequence();
    }

    if (sStageCamera.introHidesHealthbars && !IntroFocusHidesHealthbars()) {
        ReleaseHealthbars();
    }

    forced = visible && sStageCameraDebug.forcePose == 1;
    poseHome = PoseEquals(&sStageCamera.cur, &sStageCamera.homePose) && !IsEasing() && !IsShaking() && debugView == 0 && !forced;
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
        if (forced) {
            // bw2vis:camera-core: the test hook's pose (the harness writes it)
            pose = sStageCamera.homePose;
            pose.focus.x += sStageCameraDebug.forceFocusX;
            pose.focus.y += sStageCameraDebug.forceFocusY;
            pose.focus.z += sStageCameraDebug.forceFocusZ;
            pose.yaw = sStageCameraDebug.forceYaw;
            pose.pitch = sStageCameraDebug.forcePitch;
            pose.distance = sStageCameraDebug.forceDistance > 0 ? sStageCameraDebug.forceDistance : FX32_ONE;
        } else if (debugView != 0) {
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
    UpdateDebugBlock(&pose, startTick);
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

// bw2vis:camera-core. A command's frames word: drawn frames in the low byte, BW2's brake and the curve
// above it (constants/battle/battle_anim.h). Eases from the current pose to goal.
static void CommandEase(const CameraPose *goal, int framesWord)
{
    int frames = (framesWord & STAGE_CAMERA_FRAMES_MASK) * STEP_FRAMES;
    int brake = ((framesWord >> 8) & 0xFF) * STEP_FRAMES;

    EaseToCurve(goal, frames, brake, (framesWord & STAGE_CAMERA_SMOOTH) ? CURVE_SMOOTH : CURVE_LINEAR);
}

// The pose's projection of a world point, without touching the frame's view
static BOOL ProjectPose(const VecFx32 *point, const CameraPose *pose, fx32 *sx, fx32 *sy, fx32 *depth)
{
    VecFx32 up = { 0, FX32_ONE, 0 };
    VecFx32 camPos, offset;
    MtxFx43 view;

    PoseCamera(pose, &camPos, &offset);
    MTX_LookAt(&camPos, &up, &pose->focus, &view);
    return Project(point, &view, sStageCamera.home.projection, sx, sy, depth);
}

// The pose that frames the world point foot at scale (its size against home) with the camera trucked
// over it and not turned: BW2's presets. foot is on screen column col and, unless row is negative, on
// screen row row. FALSE if foot isn't in front of the home camera.
static BOOL TruckGoal(const VecFx32 *foot, fx32 scale, int row, int col, CameraPose *goal)
{
    VecFx32 back, rel, focus;
    fx32 sx, sy, homeDepth, depth, distance, perPixel;
    int pass;

    if (scale <= 0 || !Project(foot, sStageCamera.home.view, sStageCamera.home.projection, &sx, &sy, &homeDepth)) {
        return FALSE;
    }

    VEC_Subtract(&sStageCamera.home.camPos, &sStageCamera.home.camTarget, &back);
    VEC_Normalize(&back, &back);
    focus = *foot;
    focus.y = sStageCamera.home.camTarget.y;

    for (pass = 0; pass < 3; pass++) {
        // The camera sits at focus + back * homeLength * distance, so the depth of foot is
        // homeLength * distance - (foot - focus) . back; solve that for homeDepth / scale
        VEC_Subtract(foot, &focus, &rel);
        distance = FX_Div(FX_Div(homeDepth, scale) + VEC_DotProduct(&rel, &back), sStageCamera.homeLength);

        if (distance < CAMERA_MIN_DEPTH) {
            distance = CAMERA_MIN_DEPTH;
        } else if (distance > CAMERA_MAX_DISTANCE) {
            distance = CAMERA_MAX_DISTANCE;
        }

        *goal = sStageCamera.homePose;
        goal->focus = focus;
        goal->distance = distance;

        if (!ProjectPose(foot, goal, &sx, &sy, &depth)) {
            break;
        }

        // Raising the camera and its focus together moves the point down the screen by about
        // height / (world units per pixel at its depth); moving them left moves it right (the camera
        // isn't turned, so its right is world x)
        perPixel = FX_Mul(depth, FX_Div(sStageCamera.home.fovySin, sStageCamera.home.fovyCos)) / 96;
        focus.x += FX_Mul(sx - col * FX32_ONE, perPixel);

        if (row >= 0) {
            focus.y += FX_Mul(row * FX32_ONE - sy, perPixel);
        }
    }

    return TRUE;
}

// A battler's BW2 preset shot: its slot's size and where on the screen it stands, a slide with no turn
static BOOL PresetGoal(int battler, fx32 scale, CameraPose *goal)
{
    VecFx32 foot;
    int homeX, homeY, slot;

    if (battler < 0 || battler >= MaxBattlers() || !BattlerFoot(battler, &homeX, &homeY, &foot)) {
        return FALSE;
    }

    slot = BattleSystem_BattlerSlot(sStageCamera.battleSys, battler);

    if (scale <= 0) {
        scale = sPresetScale[slot];
    }

    return TruckGoal(&foot, scale, sPresetRow[slot], (slot & 1) ? PRESET_COL_ENEMY : PRESET_COL_PLAYER, goal);
}

void BattleStage_CameraMove(int focus, int attacker, int defender, int distancePct, int yawDeg, int pitchDeg, int frames)
{
    CameraPose goal;
    VecFx32 a, b;
    BOOL freeFraming = (focus & STAGE_CAMERA_FREE) != 0;

    if (!ScriptCommand()) {
        return;
    }

    focus &= ~STAGE_CAMERA_FREE;
    goal = sStageCamera.cur;
    goal.fov = sStageCamera.goal.fov; // a StageCameraZoom still easing keeps its target
    goal.focus = sStageCamera.home.camTarget;
    sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;

    switch (focus) {
    case STAGE_CAMERA_FOCUS_ATTACKER:
    case STAGE_CAMERA_FOCUS_DEFENDER: {
        int battler = focus == STAGE_CAMERA_FOCUS_ATTACKER ? attacker : defender;

        // bw2vis:camera-core: BW2's attacker / defender preset (types 9-12 resolve to the battler's slot
        // preset): a slide with no turn, at the slot's size. The player's own mon pulls back a little
        // (0.91x) where the old free framing pushed in to 1.46x and turned.
        if (!freeFraming && PresetGoal(battler, 0, &goal)) {
            goal.fov = sStageCamera.goal.fov;
            sStageCamera.particleFocus = PARTICLE_FOCUS_BATTLER;
            sStageCamera.particleBattlers[0] = battler;
            CommandEase(&goal, frames);
            return;
        }

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

    CommandEase(&goal, frames);
}

// bw2vis:camera-core: with BW2's curve (the default) the camera turns along the chord, as
// CmdCameraRotate's MoveTo does, so it dips toward the focus mid-turn; STAGE_CAMERA_SMOOTH keeps the arc
void BattleStage_CameraOrbit(int yawDeltaDeg, int frames)
{
    CameraPose goal;

    if (!ScriptCommand()) {
        return;
    }

    goal = sStageCamera.goal;
    goal.yaw += yawDeltaDeg * FX32_ONE;
    CommandEase(&goal, frames);
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

    CommandEase(&goal, frames);
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

// bw2vis:camera-core: BW2's shake by default (constants/battle/battle_anim.h has the options)
void BattleStage_CameraShake(int amplitudePx, int frames)
{
    int amp = amplitudePx & 0xFF;
    int length = (frames & STAGE_CAMERA_FRAMES_MASK) * STEP_FRAMES;
    int quarter = ((frames >> 8) & 0xFF) * STEP_FRAMES;

    if (!ScriptCommand()) {
        return;
    }

    if (quarter <= 0) {
        quarter = SHAKE_QUARTER_FRAMES;
    }

    if (amplitudePx & STAGE_CAMERA_SHAKE_DECAY) {
        StartShakeBW2(SHAKE_DECAY, amp, quarter, 1);
        sStageCamera.shakeEnd = length;
        return;
    }

    StartShakeBW2((amplitudePx & STAGE_CAMERA_SHAKE_X) ? SHAKE_TRIANGLE_X : SHAKE_TRIANGLE_Y, amp, quarter, length > 0 ? (length + 4 * quarter - 1) / (4 * quarter) : 0);
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

    CommandEase(&sStageCamera.homePose, frames);
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

    // The menu camera (prompt, select shot, idle shots) and the beats are expected to be cut short;
    // anything else off home is counted
    if (!PoseEquals(&sStageCamera.cur, &sStageCamera.homePose) || IsEasing() || IsShaking() || sStageCamera.sequence != SEQUENCE_NONE) {
        if (sStageCamera.sequence != SEQUENCE_IDLE && sStageCamera.sequence != SEQUENCE_PROMPT
            && sStageCamera.sequence != SEQUENCE_SELECT && sStageCamera.sequence != SEQUENCE_BEAT
            && !sStageCamera.idleHoming) {
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
    sStageCamera.homeCurve = CURVE_SMOOTH;
    sStageCamera.homeBrake = 0;
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
    int layoutX, layoutY;

    // bw2vis:layout - the side's platform stands at its battlers' BW2 places (battle_stage_layout.c).
    // Off home the anchors' home is that place already, so an OBJ at its classic place p maps to
    // now + s * (p + d - home): the home taken back by d. At home it is the translation d alone.
    BOOL moved = BattleStageLayout_SideOffset(side, &layoutX, &layoutY);

    if (!sStageCamera.hasHome || sStageCamera.atHome || sStageCamera.battleSys == NULL) {
        if (!moved) {
            return FALSE;
        }

        similarity->homeX = 0;
        similarity->homeY = 0;
        similarity->nowX = layoutX * FX32_ONE;
        similarity->nowY = layoutY * FX32_ONE;
        similarity->scale = FX32_ONE;
        return TRUE;
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

    similarity->homeX = homeX / count - layoutX;
    similarity->homeY = homeY / count - layoutY;
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

    // bw2vis:layout - a translation alone (the layout's rest offset at home) leaves the OBJ unscaled
    if (similarity.scale != FX32_ONE) {
        sprite->affineScale.x = FX_Mul(save->scale.x, s);
        sprite->affineScale.y = FX_Mul(save->scale.y, s);
        sprite->affineOverwriteMode = AFFINE_OVERWRITE_MODE_DOUBLE;
    }
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

    // The menu camera runs under the menu (the next battler's menu in a double battle re-aims it)
    if (sStageCamera.sequence == SEQUENCE_IDLE || sStageCamera.sequence == SEQUENCE_PROMPT || sStageCamera.sequence == SEQUENCE_SELECT) {
        sStageCamera.menuWait = 0;
        return TRUE;
    }

    // bw2vis:camera-core: a beat still holding (a send-out's, a catch's) goes home for the menu
    if (sStageCamera.sequence == SEQUENCE_BEAT) {
        EaseToCurve(&sStageCamera.homePose, BEAT_HOME_FRAMES, BEAT_HOME_BRAKE, CURVE_LINEAR);
        sStageCamera.sequence = SEQUENCE_NONE;
        sStageCamera.beat = BEAT_NONE;
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

// bw2vis:camera-core. The command menu camera (BW2: btlv_input.c:888-890, :947-951, :3376-3379;
// btlv_effect.c:840-888, :1087-1112, :1322-1366).

// The idle shots' random numbers: a private LCG, so the battle's own RNG (and so a recorded or linked
// battle) never sees the camera
static int IdleRandom(int range)
{
    sStageCamera.idleRandom = sStageCamera.idleRandom * 1103515245 + 12345;
    return (int)((sStageCamera.idleRandom >> 16) % (u32)range);
}

// The mean foot point of a side's battlers
static BOOL SideFoot(int side, VecFx32 *foot)
{
    VecFx32 sum, point;
    int count = 0;
    int max, i, homeX, homeY;

    sum.x = sum.y = sum.z = 0;
    max = MaxBattlers();

    for (i = 0; i < max; i++) {
        if ((BattleSystem_BattlerSlot(sStageCamera.battleSys, i) & 1) == side && BattlerFoot(i, &homeX, &homeY, &point)) {
            sum.x += point.x;
            sum.y += point.y;
            sum.z += point.z;
            count++;
        }
    }

    if (count == 0) {
        return FALSE;
    }

    foot->x = sum.x / count;
    foot->y = sum.y / count;
    foot->z = sum.z / count;
    return TRUE;
}

// The battler of a side, the first one there
static int SideBattler(int side)
{
    int max = MaxBattlers();
    int i;

    for (i = 0; i < max; i++) {
        if ((BattleSystem_BattlerSlot(sStageCamera.battleSys, i) & 1) == side) {
            return i;
        }
    }

    return -1;
}

static BOOL IsDoubles(void)
{
    return MaxBattlers() > 2;
}

// BW2's wide doubles shot (preset 14): from the home target, pulled back until the player's mons are at
// about 0.68x (as far as the arenas cover)
static void WideGoal(CameraPose *goal)
{
    VecFx32 back, rel, foot;
    fx32 sx, sy, homeDepth, sum = 0;
    int count = 0;
    int max = MaxBattlers();
    int i, homeX, homeY;

    *goal = sStageCamera.homePose;
    VEC_Subtract(&sStageCamera.home.camPos, &sStageCamera.home.camTarget, &back);
    VEC_Normalize(&back, &back);

    for (i = 0; i < max; i++) {
        if ((BattleSystem_BattlerSlot(sStageCamera.battleSys, i) & 1) == 0 && BattlerFoot(i, &homeX, &homeY, &foot)
            && Project(&foot, sStageCamera.home.view, sStageCamera.home.projection, &sx, &sy, &homeDepth)) {
            VEC_Subtract(&foot, &sStageCamera.home.camTarget, &rel);
            sum += FX_Div(FX_Div(homeDepth, WIDE_PLAYER_SCALE) + VEC_DotProduct(&rel, &back), sStageCamera.homeLength);
            count++;
        }
    }

    if (count > 0) {
        goal->distance = sum / count;
    }

    if (goal->distance > CAMERA_MAX_DISTANCE) {
        goal->distance = CAMERA_MAX_DISTANCE;
    } else if (goal->distance < FX32_ONE) {
        goal->distance = FX32_ONE;
    }
}

// The prompt's shot of the battler choosing: BW2 runs effect 0x23f (doubles: 0x240 / 0x241) on it,
// whose camera data isn't extracted; this is its slot's preset, the shot BW2's own camera tables have
// for that mon (0.91x in a single battle, 1.19x / 1.06x for the left / right mon of a double)
static BOOL PromptGoal(int battler, CameraPose *goal)
{
    return PresetGoal(battler, 0, goal);
}

static BOOL IdleShotGoal(const IdleShotPose *shot, CameraPose *goal)
{
    VecFx32 focus, foot;
    fx32 toward;
    int battler;

    switch (shot->focus) {
    case IDLE_FOCUS_ENEMY:
        if (!SideFoot(1, &foot)) {
            return FALSE;
        }

        // Both foes in a double battle: their preset size would cut them at the sides
        if (!TruckGoal(&foot, shot->scalePct ? shot->scalePct * FX32_ONE / 100 : (IsDoubles() ? FX32_CONST(1.25) : sPresetScale[1]), sPresetRow[1], PRESET_COL_ENEMY, goal)) {
            return FALSE;
        }
        break;
    case IDLE_FOCUS_PLAYER:
        battler = sStageCamera.promptBattler >= 0 ? sStageCamera.promptBattler : SideBattler(0);

        if (!PresetGoal(battler, shot->scalePct * FX32_ONE / 100, goal)) {
            return FALSE;
        }
        break;
    default:
        *goal = sStageCamera.homePose;

        if (shot->towardPct != 0) {
            if (!SideFocus(shot->towardPct > 0 ? 1 : 0, &focus)) {
                return FALSE;
            }

            toward = (shot->towardPct > 0 ? shot->towardPct : -shot->towardPct) * FX32_ONE / 100;
            goal->focus.x += FX_Mul(focus.x - goal->focus.x, toward);
            goal->focus.y += FX_Mul(focus.y - goal->focus.y, toward);
            goal->focus.z += FX_Mul(focus.z - goal->focus.z, toward);
        }
        break;
    }

    goal->yaw = shot->yawDeg * FX32_ONE;
    goal->pitch = shot->pitchDeg * FX32_ONE;
    return TRUE;
}

// Idle shot pick: a cut to its start, then a slow move at constant speed to its end (atEnd: a cut
// straight to the end, the test hook's way to check a pose)
static BOOL StartIdleShot(int pick, BOOL atEnd)
{
    CameraPose start, end;

    if (!IdleShotGoal(&sIdleShots[pick].start, &start) || !IdleShotGoal(&sIdleShots[pick].end, &end)) {
        return FALSE;
    }

    sStageCamera.idleLast = pick;
    sStageCamera.idlePose = pick;
    sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;
    sStageCamera.sequence = SEQUENCE_IDLE;
    EaseToCurve(atEnd ? &end : &start, 0, 0, CURVE_LINEAR);

    if (!atEnd) {
        EaseToCurve(&end, sIdleShots[pick].moveFrames, 0, CURVE_LINEAR);
    }

    sStageCamera.idleHold = sIdleShots[pick].holdFrames;
    return TRUE;
}

// A new idle shot, never the last one again
static void StartNextIdleShot(void)
{
    int tries, pick;

    for (tries = 0; tries < 8; tries++) {
        do {
            pick = IdleRandom(IDLE_SHOT_COUNT);
        } while (pick == sStageCamera.idleLast);

        sStageCamera.idleLast = pick;

        if (StartIdleShot(pick, FALSE)) {
            return;
        }
    }

    sStageCamera.idleHold = IDLE_WAIT_FRAMES;
}

// The test hook (StageCameraDebug.forcePose): 0x100 + n starts idle shot n now, 0x200 + n cuts to its end
static void IdleTestHook(void)
{
    int request = sStageCameraDebug.forcePose;

    if (request >= 0x100 && request < 0x300 && (request & 0xFF) < (int)IDLE_SHOT_COUNT) {
        sStageCameraDebug.forcePose = 0;
        StartIdleShot(request & 0xFF, request >= 0x200);
    }
}

void BattleStage_StartIdleCamera(int battler)
{
    CameraPose goal;

    // The prompt framed the battler choosing: the beats may play from here on (the battle start is the intro's)
    sStageCamera.promptSeen = TRUE;

    if (!CanRunCamera() || sStageCamera.scriptActive || MenuCameraOff()) {
        return;
    }

    // From home, or from the previous battler's prompt in a double battle (re-aimed); not over a
    // cinematic or a shake
    if (sStageCamera.sequence != SEQUENCE_PROMPT && sStageCamera.sequence != SEQUENCE_SELECT && sStageCamera.sequence != SEQUENCE_IDLE
        && (sStageCamera.sequence != SEQUENCE_NONE || IsShaking() || (!PoseEquals(&sStageCamera.cur, &sStageCamera.homePose) && !sStageCamera.idleHoming))) {
        return;
    }

    if (!PromptGoal(battler, &goal)) {
        return;
    }

    sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;
    sStageCamera.promptBattler = battler;
    sStageCamera.idlePose = -1;
    sStageCamera.idleHoming = FALSE;
    sStageCamera.idleTimer = 0;
    sStageCamera.sequence = SEQUENCE_PROMPT;
    EaseToCurve(&goal, PROMPT_FRAMES, PROMPT_BRAKE, CURVE_LINEAR);
}

// Move select in a double battle: BW2 restarts the idle wait and plays effect 0x244 (its camera data isn't
// extracted); the shot here is BW2's wide doubles preset, which shows every mon to pick from. Target
// select keeps it. A single battle's move list keeps the prompt shot and its wait, as in BW2.
static void SelectCamera(int battler, BOOL restartWait)
{
    CameraPose goal;

    if (!IsDoubles() || !CanRunCamera() || sStageCamera.scriptActive || MenuCameraOff()) {
        return;
    }

    if (sStageCamera.sequence != SEQUENCE_PROMPT && sStageCamera.sequence != SEQUENCE_SELECT && sStageCamera.sequence != SEQUENCE_IDLE) {
        return;
    }

    if (restartWait) {
        sStageCamera.idleTimer = 0;
    }

    if (sStageCamera.sequence == SEQUENCE_SELECT) {
        return;
    }

    WideGoal(&goal);
    sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;
    sStageCamera.promptBattler = battler;
    sStageCamera.idlePose = -1;
    sStageCamera.sequence = SEQUENCE_SELECT;
    EaseToCurve(&goal, PROMPT_FRAMES, PROMPT_BRAKE, CURVE_LINEAR);
}

void BattleStage_MoveSelectCamera(int battler)
{
    SelectCamera(battler, TRUE);
}

void BattleStage_TargetSelectCamera(int battler)
{
    SelectCamera(battler, FALSE);
}

void BattleStage_EndIdleCamera(void)
{
    if (sStageCamera.sequence != SEQUENCE_IDLE && sStageCamera.sequence != SEQUENCE_PROMPT && sStageCamera.sequence != SEQUENCE_SELECT) {
        return;
    }

    // BW2's StopIdleEffect plays the return effect 0x236 (not extracted): an ease home at the prompt's speed
    sStageCamera.sequence = SEQUENCE_NONE;
    sStageCamera.holdFrames = 0;
    sStageCamera.idlePose = -1;

    if (!PoseEquals(&sStageCamera.cur, &sStageCamera.homePose) || IsEasing()) {
        EaseToCurve(&sStageCamera.homePose, MENU_HOME_FRAMES, MENU_HOME_BRAKE, CURVE_LINEAR);
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

// bw2vis:camera-core. A kick on BW2's motion: a push at constant speed over inFrames screen frames with
// BW2's shake (count swings of 4 quarters of 4 frames) from the start, then home over homeFrames (BW2's
// frames and brake)
static void StartKick(const CameraPose *goal, int inFrames, int shakePx, int shakeCount, int homeFrames, int homeBrake)
{
    EaseToCurve(goal, inFrames, 0, CURVE_LINEAR);
    StartShakeBW2(SHAKE_TRIANGLE_Y, shakePx, SHAKE_QUARTER_FRAMES, shakeCount);
    sStageCamera.holdFrames = 0;
    sStageCamera.homeFrames = homeFrames / STEP_FRAMES;
    sStageCamera.homeCurve = CURVE_LINEAR;
    sStageCamera.homeBrake = homeBrake;
    sStageCamera.sequence = SEQUENCE_TO;
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

    // Push 4 with a 3 px shake of 1 swing (16) from the start, then home over 8: 24 screen frames
    goal.distance = FX32_CONST(0.92);
    sStageCamera.fields->cinematicsSeen |= BATTLE_STAGE_CINEMATIC_CRIT;
    StartKick(&goal, 4, 3, 1, 8, 0);
}

void BattleStage_FaintKick(int battler)
{
    CameraPose goal;

    if (!CanKick() || !KickGoal(battler, FX32_CONST(0.1), &goal)) {
        return;
    }

    // Dip 6 with a 2 px shake of 1 swing (16) from the start, then home over 12 with a tail from frame 8
    // (17): 33 screen frames
    goal.pitch = FX32_CONST(-3);
    sStageCamera.fields->cinematicsSeen |= BATTLE_STAGE_CINEMATIC_FAINT;
    StartKick(&goal, 6, 2, 1, 12, 8);
}

// bw2vis:camera-core. The beats after the first prompt (BW2: the recall 0x26C and send-in 0x26D of
// BtlvScu_StartMemberOut / MemberIn, the ball effect 0x23a, the trainer's return 0x270; their camera data
// isn't extracted). The Poke Balls and trainers are 2D OBJs that only move with their side
// (BattleStage_GetSideOffset), so a beat that frames them keeps their place on screen: the switch and
// catch beats close in along the ray through the battler's feet (the battler stays where it stands, and
// the ball lands on it), and the trainer's return trucks over at home size (the trainer keeps its size).

static BOOL CanBeat(void)
{
    return sStageCamera.promptSeen && CanKick() && sStageCamera.sequence != SEQUENCE_TO && sStageCamera.sequence != SEQUENCE_HOLD
        && sStageCamera.sequence != SEQUENCE_INTRO;
}

// Closer in on a battler along the ray from the home camera through its feet: its feet keep their
// screen point and its size grows to scale
static BOOL DollyGoal(int battler, fx32 scale, CameraPose *goal)
{
    VecFx32 foot, rel, offset;
    int homeX, homeY;

    if (battler < 0 || battler >= MaxBattlers() || !BattlerFoot(battler, &homeX, &homeY, &foot) || scale <= 0) {
        return FALSE;
    }

    VEC_Subtract(&sStageCamera.home.camPos, &foot, &rel);
    VEC_Subtract(&sStageCamera.home.camPos, &sStageCamera.home.camTarget, &offset);
    *goal = sStageCamera.homePose;
    goal->focus.x = foot.x + FX_Div(rel.x, scale) - offset.x;
    goal->focus.y = foot.y + FX_Div(rel.y, scale) - offset.y;
    goal->focus.z = foot.z + FX_Div(rel.z, scale) - offset.z;
    return TRUE;
}

static void StartBeat(int beat, int battler, const CameraPose *goal, int hold)
{
    sStageCamera.beat = beat;
    sStageCamera.beatBattler = battler;
    sStageCamera.beatHold = hold;
    sStageCamera.holdFrames = 0;
    sStageCamera.idlePose = -1;
    sStageCamera.particleFocus = PARTICLE_FOCUS_BATTLER;
    sStageCamera.particleBattlers[0] = battler;
    sStageCamera.sequence = SEQUENCE_BEAT;
    EaseToCurve(goal, BEAT_IN_FRAMES, BEAT_IN_BRAKE, CURVE_LINEAR);
}

static void EndBeat(void)
{
    sStageCamera.beat = BEAT_NONE;
    sStageCamera.sequence = SEQUENCE_NONE;
    EaseToCurve(&sStageCamera.homePose, BEAT_HOME_FRAMES, BEAT_HOME_BRAKE, CURVE_LINEAR);
}

// The battler's healthbar is in (a send-out's last step)
static BOOL HealthbarIn(int battler)
{
    Healthbar *healthbar;

    if (battler < 0 || battler >= MaxBattlers()) {
        return TRUE;
    }

    healthbar = ov16_02263B08(BattleSystem_BattlerData(sStageCamera.battleSys, battler));
    return healthbar->mainSprite != NULL && ManagedSprite_GetDrawFlag(healthbar->mainSprite) && healthbar->doneScrolling;
}

static void AdvanceBeat(void)
{
    if (sStageCamera.debugFlags != NULL && (*sStageCamera.debugFlags & BATTLE_STAGE_DEBUG_NO_CINEMATICS)) {
        SnapHome();
        return;
    }

    if (IsEasing()) {
        return;
    }

    // A send-out holds until the new battler's healthbar is in (at most BEAT_RECALL_MAX), then a moment more
    if (sStageCamera.beat == BEAT_SENDOUT && sStageCamera.beatHold == BEAT_HOLD_FOREVER) {
        sStageCamera.holdFrames += STEP_FRAMES;

        if (HealthbarIn(sStageCamera.beatBattler) || sStageCamera.holdFrames >= BEAT_RECALL_MAX) {
            sStageCamera.beatHold = BEAT_SENDOUT_HOLD;
        }
        return;
    }

    if (sStageCamera.beatHold == BEAT_HOLD_FOREVER) {
        return;
    }

    sStageCamera.beatHold -= STEP_FRAMES;

    if (sStageCamera.beatHold <= 0) {
        EndBeat();
    }
}

static fx32 BeatScale(int battler)
{
    return (BattleSystem_BattlerSlot(sStageCamera.battleSys, battler) & 1) ? BEAT_ENEMY_SCALE : BEAT_PLAYER_SCALE;
}

void BattleStage_RecallCamera(int battler)
{
    CameraPose goal;

    if (!CanBeat() || !DollyGoal(battler, BeatScale(battler), &goal)) {
        return;
    }

    StartBeat(BEAT_RECALL, battler, &goal, BEAT_RECALL_MAX);
}

void BattleStage_SendOutCamera(int battler)
{
    CameraPose goal;

    // The Totem's summoned ally has its own entrance
    if (TotemBattle_IsActive(sStageCamera.battleSys) && battler == BATTLER_ENEMY_2) {
        return;
    }

    if (!CanBeat() || !DollyGoal(battler, BeatScale(battler), &goal)) {
        return;
    }

    // From the recall of the same slot (or a broken-free catch) the camera is already there
    if (sStageCamera.sequence == SEQUENCE_BEAT && sStageCamera.beatBattler == battler) {
        sStageCamera.beat = BEAT_SENDOUT;
        sStageCamera.beatHold = BEAT_HOLD_FOREVER;
        sStageCamera.holdFrames = 0;
        return;
    }

    StartBeat(BEAT_SENDOUT, battler, &goal, BEAT_HOLD_FOREVER);
    sStageCamera.holdFrames = 0;
}

void BattleStage_CatchCamera(int battler)
{
    CameraPose goal;

    if (!CanBeat() || !DollyGoal(battler, BEAT_ENEMY_SCALE, &goal)) {
        return;
    }

    // Held through the shakes: a break-free sends the Pokemon out again (SendOutCamera takes over and
    // lets go), a catch holds until the battle ends
    StartBeat(BEAT_CATCH, battler, &goal, BEAT_HOLD_FOREVER);
}

void BattleStage_EndBattleCamera(int battler)
{
    CameraPose goal;
    VecFx32 foot;

    // The defeated trainer comes back: truck over to the opponents' side at home size and stay
    if (!CanBeat() || !SideFoot(BattleSystem_BattlerSlot(sStageCamera.battleSys, battler) & 1, &foot) || !TruckGoal(&foot, FX32_ONE, sPresetRow[1], PRESET_COL_ENEMY, &goal)) {
        return;
    }

    StartBeat(BEAT_END, battler, &goal, BEAT_HOLD_FOREVER);
    sStageCamera.particleFocus = PARTICLE_FOCUS_CENTER;
}
