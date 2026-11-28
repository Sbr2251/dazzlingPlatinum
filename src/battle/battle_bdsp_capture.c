#include "battle/battle_bdsp_capture.h"

#include <math.h>
#include <string.h>

#include "constants/battle.h"
#include "generated/items.h"

#include "battle/battle_context.h"
#include "battle_anim/ov12_02235E94.h"
#include "sprite_system.h"
#include "struct_defs/battle_system.h"

#define BDSP_CAP_DT               (1.0f / 60.0f)
#define BDSP_CAP_PI               3.14159265f
#define BDSP_CAP_THROW_DUR        0.45f
#define BDSP_CAP_ABSORB_DUR       0.30f
#define BDSP_CAP_DROP_DUR         0.58f
#define BDSP_CAP_WOBBLE_DUR       0.52f
#define BDSP_CAP_WOBBLE_PERIOD    0.72f
#define BDSP_CAP_STARS_DUR        0.90f
#define BDSP_CAP_BREAKOUT_DUR     0.46f
#define BDSP_CAP_GROUND_Y         0.18f
#define BDSP_CAP_HOVER_Y          1.45f
#define BDSP_CAP_BALL_SCALE       1.85f
#define BDSP_CAP_ARC_PEAK         1.65f

// Mirror of BattleScript_CatchMonTask's CatchMonTaskState values (battle_script.c).
enum BdspCatchSeqMirror {
    CAP_SEQ_START = 0,
    CAP_SEQ_CHECK_BATTLE_TYPE = 1,
    CAP_SEQ_CALC_SHAKES = 2,
    CAP_SEQ_WAIT_BALL_LAND = 3,
    CAP_SEQ_WAIT_BALL_OPEN = 4,
    CAP_SEQ_DO_SHAKES = 5,
    CAP_SEQ_DECREMENT_REMAINING_SHAKES = 6,
    CAP_SEQ_WAIT_SHAKES_FINISH = 7,
    CAP_SEQ_SET_POKEDEX_DATA = 12,
    CAP_SEQ_TRAINER_BLOCKED = 25,
    CAP_SEQ_POKEMON_BREAK_FREE = 28,
    CAP_SEQ_WAIT_SHOW_POKEMON = 29,
    CAP_SEQ_PRINT_BROKE_FREE = 30,
};

enum BdspCapturePhase {
    BDSP_CAP_PHASE_IDLE = 0,
    BDSP_CAP_PHASE_THROW,
    BDSP_CAP_PHASE_ABSORB,
    BDSP_CAP_PHASE_DROP,
    BDSP_CAP_PHASE_SHAKES,
    BDSP_CAP_PHASE_CAUGHT,
    BDSP_CAP_PHASE_BREAKOUT,
};

typedef struct BdspCaptureState {
    BOOL active;
    BOOL decided2d;
    BOOL syncedToTask;
    BOOL hasBallsThrownInit;
    u16 lastBallsThrown;
    int phase;
    int targetBattler;
    int ballItemId;
    int ballVariant;
    int shakes;
    BOOL caught;
    BOOL hasMonSnapshot;
    float monX;
    float monY;
    float monZ;
    float monFullScale;
    float phaseTime;
    float wobbleTime;
    BOOL wobbleActive;
    int lastSeqNum;
    int lastRemainingShakes;
    int shakesDone;
    int wobbleDir;
} BdspCaptureState;

static BdspCaptureState sCap;

static float ClampF(float v, float lo, float hi)
{
    if (v < lo) {
        return lo;
    }
    if (v > hi) {
        return hi;
    }
    return v;
}

static int ItemToBallVariant(int itemId)
{
    switch (itemId) {
    case ITEM_POKE_BALL:    return 0;
    case ITEM_GREAT_BALL:   return 1;
    case ITEM_ULTRA_BALL:   return 2;
    case ITEM_MASTER_BALL:  return 3;
    case ITEM_SAFARI_BALL:  return 4;
    case ITEM_QUICK_BALL:   return 5;
    case ITEM_DUSK_BALL:    return 6;
    case ITEM_PREMIER_BALL: return 7;
    case ITEM_NET_BALL:
    case ITEM_DIVE_BALL:    return 1;
    case ITEM_TIMER_BALL:
    case ITEM_LUXURY_BALL:  return 2;
    case ITEM_HEAL_BALL:
    case ITEM_CHERISH_BALL: return 3;
    case ITEM_NEST_BALL:    return 4;
    default:                return 0;
    }
}

static void SuppressLegacyCaptureBall(BattleContext *ctx)
{
    BattleScriptTaskData *td;
    ManagedSprite *ballSpr;

    if (ctx == NULL || ctx->taskData == NULL) {
        return;
    }
    td = ctx->taskData;
    // ballRotation is guaranteed alive only during seqNum [1..11] (before ov12_0223783C frees it).
    if (td->seqNum < CAP_SEQ_CHECK_BATTLE_TYPE || td->seqNum >= CAP_SEQ_SET_POKEDEX_DATA) {
        return;
    }
    if (td->ballRotation == NULL) {
        return;
    }
    ballSpr = BallRotation_GetSprite(td->ballRotation);
    if (ballSpr != NULL) {
        ManagedSprite_SetDrawFlag(ballSpr, FALSE);
        ManagedSprite_SetExplicitOamMode(ballSpr, GX_OAM_MODE_OBJWND);
    }
}

static BOOL IsUnsupportedCaptureBattle(u32 battleType)
{
    return (battleType & (BATTLE_TYPE_TRAINER | BATTLE_TYPE_SAFARI | BATTLE_TYPE_PAL_PARK)) != 0;
}

static void EnterPhase(int newPhase)
{
    sCap.phase = newPhase;
    sCap.phaseTime = 0.0f;
}

void BattleBdspCapture_Reset(void)
{
    memset(&sCap, 0, sizeof(sCap));
    sCap.targetBattler = -1;
    sCap.monX = 2.35f;
    sCap.monY = 0.0f;
    sCap.monZ = -2.15f;
    sCap.monFullScale = 1.40f;
    sCap.wobbleDir = 1;
}

void BattleBdspCapture_Start(BattleSystem *battleSys, int targetBattler, int ballItemId, int shakes, BOOL caught)
{
    u16 prevThrown = sCap.lastBallsThrown;
    BOOL hadInit = sCap.hasBallsThrownInit;

    if (!SIM_Battle3D_ModelsEnabled() || !SIM_Battle3D_HasActorLoaded(SIM_BATTLE3D_ACTOR_POKEBALL)) {
        return;
    }
    if (battleSys != NULL && IsUnsupportedCaptureBattle(BattleSystem_GetBattleType(battleSys))) {
        return;
    }

    memset(&sCap, 0, sizeof(sCap));
    sCap.hasBallsThrownInit = hadInit;
    sCap.lastBallsThrown = prevThrown;
    if (battleSys != NULL) {
        sCap.hasBallsThrownInit = TRUE;
        sCap.lastBallsThrown = battleSys->ballsThrown;
    }

    sCap.active = TRUE;
    sCap.decided2d = FALSE;
    sCap.syncedToTask = FALSE;
    sCap.phase = BDSP_CAP_PHASE_THROW;
    sCap.targetBattler = targetBattler;
    sCap.ballItemId = ballItemId;
    sCap.ballVariant = ItemToBallVariant(ballItemId);
    sCap.shakes = (shakes < 0) ? 0 : (shakes > 3 ? 3 : shakes);
    sCap.caught = caught ? TRUE : FALSE;
    sCap.monX = 2.35f;
    sCap.monY = 0.0f;
    sCap.monZ = -2.15f;
    sCap.monFullScale = 1.40f;
    sCap.lastSeqNum = -1;
    sCap.lastRemainingShakes = -1;
    sCap.wobbleDir = 1;
}

void BattleBdspCapture_NotifyOpen(BattleSystem *battleSys, int targetBattler, int ballItemId)
{
    BattleContext *ctx;

    if (!SIM_Battle3D_ModelsEnabled()) {
        return;
    }
    if (battleSys != NULL && IsUnsupportedCaptureBattle(BattleSystem_GetBattleType(battleSys))) {
        return;
    }
    if (sCap.decided2d) {
        return;
    }
    if (!SIM_Battle3D_HasActorLoaded(SIM_BATTLE3D_ACTOR_POKEBALL)) {
        sCap.decided2d = TRUE;
        return;
    }

    ctx = (battleSys != NULL) ? BattleSystem_GetBattleContext(battleSys) : NULL;
    if (!sCap.active) {
        // Never take over mid-throw if a live CatchMonTask was already started on the 2D path.
        if (ctx != NULL && ctx->taskData != NULL) {
            sCap.decided2d = TRUE;
            return;
        }
        BattleBdspCapture_Start(battleSys, targetBattler, ballItemId, 0, FALSE);
    }

    if (sCap.active && sCap.phase == BDSP_CAP_PHASE_THROW) {
        sCap.targetBattler = targetBattler;
        if (ballItemId > 0) {
            sCap.ballItemId = ballItemId;
            sCap.ballVariant = ItemToBallVariant(ballItemId);
        }
        EnterPhase(BDSP_CAP_PHASE_ABSORB);
    }
}

void BattleBdspCapture_End(void)
{
    u16 prevThrown = sCap.lastBallsThrown;
    BOOL hadInit = sCap.hasBallsThrownInit;

    memset(&sCap, 0, sizeof(sCap));
    sCap.hasBallsThrownInit = hadInit;
    sCap.lastBallsThrown = prevThrown;
    sCap.targetBattler = -1;
    sCap.wobbleDir = 1;
}

BOOL BattleBdspCapture_IsActive(void)
{
    return sCap.active ? TRUE : FALSE;
}

BOOL BattleBdspCapture_OwnsBreakout(int battler)
{
    if (!sCap.active) {
        return FALSE;
    }
    if (sCap.targetBattler >= 0 && sCap.targetBattler != battler) {
        return FALSE;
    }
    return (sCap.phase == BDSP_CAP_PHASE_DROP
            || sCap.phase == BDSP_CAP_PHASE_SHAKES
            || sCap.phase == BDSP_CAP_PHASE_BREAKOUT)
        ? TRUE
        : FALSE;
}

void BattleBdspCapture_Update(BattleSystem *battleSys, SIM_Battle3DFrame *frame)
{
    BattleContext *ctx;
    u32 battleType;
    BOOL hasBall3d;
    SIM_Battle3DActor *ball;
    SIM_Battle3DVfx *vfx;
    int tgt;

    if (battleSys == NULL || frame == NULL || !SIM_Battle3D_ModelsEnabled()) {
        return;
    }

    battleType = BattleSystem_GetBattleType(battleSys);
    ctx = BattleSystem_GetBattleContext(battleSys);
    hasBall3d = SIM_Battle3D_HasActorLoaded(SIM_BATTLE3D_ACTOR_POKEBALL);

    if (!sCap.hasBallsThrownInit) {
        sCap.hasBallsThrownInit = TRUE;
        sCap.lastBallsThrown = battleSys->ballsThrown;
    }

    if (sCap.decided2d && (ctx == NULL || ctx->taskData == NULL)) {
        sCap.decided2d = FALSE;
    }

    // Auto-detect wild Poke Ball throw start on the exact frame BattleScript_CatchMonTask launches it.
    // Latch one visual owner per throw: if the 3D ball is not ready yet, stay 2D for the entire throw.
    if (battleSys->ballsThrown > sCap.lastBallsThrown) {
        sCap.lastBallsThrown = battleSys->ballsThrown;
        sCap.decided2d = FALSE;
        if (!IsUnsupportedCaptureBattle(battleType)
            && ctx != NULL
            && ctx->taskData != NULL) {
            if (hasBall3d) {
                int targetBattler = BATTLER_ENEMY_1;
                if (ctx->battlersSwitchingMask & (1u << BATTLER_ENEMY_1)) {
                    targetBattler = BATTLER_ENEMY_2;
                }
                BattleBdspCapture_Start(battleSys, targetBattler, ctx->taskData->ball, 0, FALSE);
                sCap.syncedToTask = TRUE;
            } else {
                sCap.decided2d = TRUE;
            }
        }
    }

    if (!hasBall3d) {
        if (sCap.active) {
            BattleBdspCapture_End();
            sCap.decided2d = TRUE;
        }
        return;
    }

    if (!sCap.active) {
        return;
    }

    // Snapshot wild Pokemon anchor and full 3D scale while it is still visible on field.
    tgt = sCap.targetBattler;
    if (!sCap.hasMonSnapshot && tgt >= 0 && tgt < SIM_BATTLE3D_MAX_BATTLERS) {
        const SIM_Battle3DBattler *tb = &frame->battlers[tgt];
        if (tb->visible && (fabsf(tb->worldX) > 0.01f || fabsf(tb->worldZ) > 0.01f)) {
            sCap.monX = tb->worldX;
            sCap.monY = tb->worldY;
            sCap.monZ = tb->worldZ;
            if (tb->modelScale > 0.05f) {
                sCap.monFullScale = tb->modelScale;
            }
            sCap.hasMonSnapshot = TRUE;
        }
    }

    // Sync state transitions with BattleScript_CatchMonTask when active.
    if (sCap.syncedToTask) {
        if (ctx == NULL || ctx->taskData == NULL) {
            if (sCap.phase != BDSP_CAP_PHASE_BREAKOUT || sCap.phaseTime >= BDSP_CAP_BREAKOUT_DUR) {
                BattleBdspCapture_End();
                return;
            }
        } else {
            BattleScriptTaskData *td = ctx->taskData;
            int seq = td->seqNum;

            // Suppress 2D OAM ball sprite ONLY while our 3D ball owns the capture sequence.
            SuppressLegacyCaptureBall(ctx);

            // Once BattleScript_CalcCatchShakes has run (seq >= 3), latch exact shakes & caught flag.
            if (seq >= CAP_SEQ_WAIT_BALL_LAND) {
                int totalShakes = td->tmpData[2]; // CATCH_MON_TOTAL_SHAKES
                sCap.caught = (totalShakes >= 4) ? TRUE : FALSE;
                sCap.shakes = (totalShakes >= 4) ? 3 : ((totalShakes < 0) ? 0 : totalShakes);
            }

            if (seq >= CAP_SEQ_TRAINER_BLOCKED && seq < CAP_SEQ_POKEMON_BREAK_FREE) {
                BattleBdspCapture_End();
                return;
            }

            // Hold THROW at its landed/hover pose until BattleBdspCapture_NotifyOpen fires;
            // only fall back to DROP if the task already advanced past open (seq >= 4).
            if ((sCap.phase == BDSP_CAP_PHASE_ABSORB || sCap.phase == BDSP_CAP_PHASE_THROW)
                && seq >= CAP_SEQ_WAIT_BALL_OPEN) {
                EnterPhase(BDSP_CAP_PHASE_DROP);
            } else if (sCap.phase == BDSP_CAP_PHASE_DROP && seq >= CAP_SEQ_DO_SHAKES) {
                EnterPhase(BDSP_CAP_PHASE_SHAKES);
                sCap.lastRemainingShakes = td->tmpData[3];
            } else if (sCap.phase == BDSP_CAP_PHASE_SHAKES) {
                int rem = td->tmpData[3]; // CATCH_MON_REMAINING_SHAKES
                if (seq == CAP_SEQ_DECREMENT_REMAINING_SHAKES
                    && (sCap.lastSeqNum != CAP_SEQ_DECREMENT_REMAINING_SHAKES || rem != sCap.lastRemainingShakes)) {
                    sCap.wobbleActive = TRUE;
                    sCap.wobbleTime = 0.0f;
                    sCap.wobbleDir = -sCap.wobbleDir;
                    sCap.lastRemainingShakes = rem;
                }
                if (seq >= CAP_SEQ_WAIT_SHAKES_FINISH && seq < CAP_SEQ_SET_POKEDEX_DATA) {
                    EnterPhase(BDSP_CAP_PHASE_CAUGHT);
                } else if (seq >= CAP_SEQ_POKEMON_BREAK_FREE) {
                    EnterPhase(BDSP_CAP_PHASE_BREAKOUT);
                }
            } else if (sCap.phase == BDSP_CAP_PHASE_CAUGHT && seq >= CAP_SEQ_SET_POKEDEX_DATA) {
                BattleBdspCapture_End();
                return;
            }

            sCap.lastSeqNum = seq;
        }
    }

    ball = &frame->actors[2];
    vfx = &frame->vfx[3];

    switch (sCap.phase) {
    case BDSP_CAP_PHASE_THROW: {
        float u = ClampF(sCap.phaseTime / BDSP_CAP_THROW_DUR, 0.0f, 1.0f);
        float startX = -2.05f;
        float startY = 1.35f;
        float startZ = 2.50f;
        float endX = sCap.monX;
        float endY = sCap.monY + BDSP_CAP_HOVER_Y;
        float endZ = sCap.monZ;
        BOOL arrived = (u >= 1.0f) || (sCap.syncedToTask && sCap.lastSeqNum >= CAP_SEQ_CALC_SHAKES);

        ball->visible = 1;
        ball->kind = SIM_BATTLE3D_ACTOR_POKEBALL;
        ball->trainerId = 0;
        ball->ballVariant = sCap.ballVariant;
        if (arrived) {
            // Hold cleanly at the landed/hover pose until NotifyOpen starts the absorb beam & shrink.
            ball->worldX = endX;
            ball->worldY = endY;
            ball->worldZ = endZ;
            ball->yawDeg = -45.0f;
            ball->pitchDeg = 0.0f;
            ball->rollDeg = 0.0f;
            ball->scale = BDSP_CAP_BALL_SCALE;
        } else {
            ball->worldX = startX + (endX - startX) * u;
            ball->worldY = startY + (endY - startY) * u + 4.0f * BDSP_CAP_ARC_PEAK * u * (1.0f - u);
            ball->worldZ = startZ + (endZ - startZ) * u;
            ball->yawDeg = 135.0f;
            ball->pitchDeg = u * 900.0f;
            ball->rollDeg = u * 270.0f;
            ball->scale = 1.55f + 0.35f * sinf(u * BDSP_CAP_PI);
        }
        ball->alpha = 1.0f;
        ball->attachActorIdx = 0;
        ball->attachBoneKind = 0;

        if (!sCap.syncedToTask && sCap.phaseTime >= BDSP_CAP_THROW_DUR) {
            EnterPhase(BDSP_CAP_PHASE_ABSORB);
        }
        break;
    }

    case BDSP_CAP_PHASE_ABSORB: {
        float p = ClampF(sCap.phaseTime / BDSP_CAP_ABSORB_DUR, 0.0f, 1.0f);
        float hoverY = sCap.monY + BDSP_CAP_HOVER_Y;

        ball->visible = 1;
        ball->kind = SIM_BATTLE3D_ACTOR_POKEBALL;
        ball->trainerId = 0;
        ball->ballVariant = sCap.ballVariant;
        ball->worldX = sCap.monX;
        ball->worldY = hoverY + 0.06f * sinf(p * BDSP_CAP_PI);
        ball->worldZ = sCap.monZ;
        ball->yawDeg = -45.0f;
        ball->pitchDeg = 22.0f * sinf(p * BDSP_CAP_PI);
        ball->rollDeg = 0.0f;
        ball->scale = BDSP_CAP_BALL_SCALE * (1.0f + 0.10f * sinf(p * BDSP_CAP_PI));
        ball->alpha = 1.0f;
        ball->attachActorIdx = 0;
        ball->attachBoneKind = 0;

        // Crimson absorb beam pulling the wild Pokemon into the open Poke Ball.
        vfx->active = 1;
        vfx->kind = SIM_BATTLE3D_VFX_ABSORB_BEAM;
        vfx->moveType = 0;
        vfx->progress = p;
        vfx->src[0] = sCap.monX;
        vfx->src[1] = sCap.monY + 0.65f;
        vfx->src[2] = sCap.monZ;
        vfx->dst[0] = sCap.monX;
        vfx->dst[1] = hoverY;
        vfx->dst[2] = sCap.monZ;
        vfx->color[0] = 1.00f;
        vfx->color[1] = 0.22f;
        vfx->color[2] = 0.26f;
        vfx->scale = 1.25f;

        if (tgt >= 0 && tgt < SIM_BATTLE3D_MAX_BATTLERS) {
            SIM_Battle3DBattler *tb = &frame->battlers[tgt];
            if (tb->use3dModel && tb->species > 0) {
                if (p < 0.85f) {
                    float shrinkU = ClampF(p / 0.85f, 0.0f, 1.0f);
                    float scaleFrac = 1.0f - 0.95f * (shrinkU * shrinkU);
                    tb->visible = 1;
                    tb->worldX = sCap.monX;
                    tb->worldY = sCap.monY + 0.65f * shrinkU * shrinkU;
                    tb->worldZ = sCap.monZ;
                    tb->alpha = 1.0f;
                    tb->modelScale = sCap.monFullScale * scaleFrac;
                    tb->flashAmount = ClampF(0.25f + shrinkU * 0.95f, 0.0f, 1.0f);
                } else {
                    tb->visible = 0;
                }
            }
        }

        if (!sCap.syncedToTask && sCap.phaseTime >= BDSP_CAP_ABSORB_DUR + 0.06f) {
            EnterPhase(BDSP_CAP_PHASE_DROP);
        }
        break;
    }

    case BDSP_CAP_PHASE_DROP: {
        float u = ClampF(sCap.phaseTime / BDSP_CAP_DROP_DUR, 0.0f, 1.0f);
        float y = BDSP_CAP_GROUND_Y;
        float hoverY = sCap.monY + BDSP_CAP_HOVER_Y;

        if (u < 0.42f) {
            float t = u / 0.42f;
            y = hoverY - (hoverY - BDSP_CAP_GROUND_Y) * (t * t);
        } else if (u < 0.74f) {
            float t = (u - 0.42f) / 0.32f;
            y = BDSP_CAP_GROUND_Y + 0.42f * sinf(t * BDSP_CAP_PI);
        } else {
            float t = (u - 0.74f) / 0.26f;
            y = BDSP_CAP_GROUND_Y + 0.14f * sinf(t * BDSP_CAP_PI);
        }

        if (tgt >= 0 && tgt < SIM_BATTLE3D_MAX_BATTLERS) {
            frame->battlers[tgt].visible = 0;
        }

        ball->visible = 1;
        ball->kind = SIM_BATTLE3D_ACTOR_POKEBALL;
        ball->trainerId = 0;
        ball->ballVariant = sCap.ballVariant;
        ball->worldX = sCap.monX;
        ball->worldY = y;
        ball->worldZ = sCap.monZ;
        ball->yawDeg = -45.0f;
        ball->pitchDeg = 0.0f;
        ball->rollDeg = 0.0f;
        ball->scale = BDSP_CAP_BALL_SCALE;
        ball->alpha = 1.0f;
        ball->attachActorIdx = 0;
        ball->attachBoneKind = 0;

        if (!sCap.syncedToTask && sCap.phaseTime >= BDSP_CAP_DROP_DUR) {
            EnterPhase(BDSP_CAP_PHASE_SHAKES);
        }
        break;
    }

    case BDSP_CAP_PHASE_SHAKES: {
        float rollDeg = 0.0f;
        float rollRad;
        float dx = 0.0f;
        float dy = 0.0f;

        if (tgt >= 0 && tgt < SIM_BATTLE3D_MAX_BATTLERS) {
            frame->battlers[tgt].visible = 0;
        }

        if (!sCap.syncedToTask) {
            if (sCap.shakesDone >= sCap.shakes) {
                EnterPhase(sCap.caught ? BDSP_CAP_PHASE_CAUGHT : BDSP_CAP_PHASE_BREAKOUT);
                break;
            }
            if (!sCap.wobbleActive && sCap.phaseTime >= (float)sCap.shakesDone * BDSP_CAP_WOBBLE_PERIOD) {
                sCap.wobbleActive = TRUE;
                sCap.wobbleTime = 0.0f;
                sCap.wobbleDir = -sCap.wobbleDir;
            }
        }

        if (sCap.wobbleActive) {
            float w = ClampF(sCap.wobbleTime / BDSP_CAP_WOBBLE_DUR, 0.0f, 1.0f);
            float env = powf(1.0f - w, 0.55f);
            rollDeg = (float)sCap.wobbleDir * 42.0f * sinf(w * 2.0f * BDSP_CAP_PI) * env;
            rollRad = rollDeg * (BDSP_CAP_PI / 180.0f);
            dx = sinf(rollRad) * 0.16f;
            dy = fabsf(sinf(rollRad)) * 0.06f;
            sCap.wobbleTime += BDSP_CAP_DT;
            if (sCap.wobbleTime >= BDSP_CAP_WOBBLE_DUR) {
                sCap.wobbleActive = FALSE;
                sCap.shakesDone++;
            }
        }

        ball->visible = 1;
        ball->kind = SIM_BATTLE3D_ACTOR_POKEBALL;
        ball->trainerId = 0;
        ball->ballVariant = sCap.ballVariant;
        ball->worldX = sCap.monX + dx;
        ball->worldY = BDSP_CAP_GROUND_Y + dy;
        ball->worldZ = sCap.monZ;
        ball->yawDeg = -45.0f;
        ball->pitchDeg = 0.0f;
        ball->rollDeg = rollDeg;
        ball->scale = BDSP_CAP_BALL_SCALE;
        ball->alpha = 1.0f;
        ball->attachActorIdx = 0;
        ball->attachBoneKind = 0;
        break;
    }

    case BDSP_CAP_PHASE_CAUGHT: {
        if (tgt >= 0 && tgt < SIM_BATTLE3D_MAX_BATTLERS) {
            frame->battlers[tgt].visible = 0;
        }

        ball->visible = 1;
        ball->kind = SIM_BATTLE3D_ACTOR_POKEBALL;
        ball->trainerId = 0;
        ball->ballVariant = sCap.ballVariant;
        ball->worldX = sCap.monX;
        ball->worldY = BDSP_CAP_GROUND_Y;
        ball->worldZ = sCap.monZ;
        ball->yawDeg = -45.0f;
        ball->pitchDeg = 0.0f;
        ball->rollDeg = 0.0f;
        ball->scale = BDSP_CAP_BALL_SCALE;
        ball->alpha = 1.0f;
        ball->attachActorIdx = 0;
        ball->attachBoneKind = 0;

        if (sCap.phaseTime < BDSP_CAP_STARS_DUR) {
            vfx->active = 1;
            vfx->kind = SIM_BATTLE3D_VFX_CATCH_STARS;
            vfx->moveType = 0;
            vfx->progress = ClampF(sCap.phaseTime / BDSP_CAP_STARS_DUR, 0.0f, 1.0f);
            vfx->src[0] = sCap.monX;
            vfx->src[1] = BDSP_CAP_GROUND_Y + 0.18f;
            vfx->src[2] = sCap.monZ;
            vfx->dst[0] = sCap.monX;
            vfx->dst[1] = BDSP_CAP_GROUND_Y + 0.18f;
            vfx->dst[2] = sCap.monZ;
            vfx->color[0] = 1.00f;
            vfx->color[1] = 0.86f;
            vfx->color[2] = 0.24f;
            vfx->scale = 1.25f;
        }
        break;
    }

    case BDSP_CAP_PHASE_BREAKOUT: {
        float p = ClampF(sCap.phaseTime / BDSP_CAP_BREAKOUT_DUR, 0.0f, 1.0f);

        ball->visible = 0;

        // Break-out light burst VFX
        if (p < 0.99f) {
            frame->burst.active = 1;
            frame->burst.worldX = sCap.monX;
            frame->burst.worldY = sCap.monY + 0.85f;
            frame->burst.worldZ = sCap.monZ;
            frame->burst.progress = p;
            frame->burst.radius = 1.60f;
            frame->burst.color[0] = 1.00f;
            frame->burst.color[1] = 0.70f;
            frame->burst.color[2] = 0.66f;
        }

        // Smoothly pop wild Pokemon back in with white/crimson flash fade
        if (tgt >= 0 && tgt < SIM_BATTLE3D_MAX_BATTLERS) {
            SIM_Battle3DBattler *tb = &frame->battlers[tgt];
            if (tb->use3dModel && tb->species > 0) {
                float inv = 1.0f - p;
                float easeOut = 1.0f - inv * inv * inv;
                float overshoot = 0.08f * sinf(p * BDSP_CAP_PI) * (1.0f - p * 0.45f);
                float scaleFrac = (p >= 0.99f) ? 1.0f : (0.10f + 0.90f * easeOut + overshoot);
                tb->visible = 1;
                tb->alpha = 1.0f;
                tb->modelScale = sCap.monFullScale * scaleFrac;
                tb->flashAmount = (p >= 0.99f) ? 0.0f : powf(inv, 1.50f);
            }
        }

        if (sCap.phaseTime >= BDSP_CAP_BREAKOUT_DUR) {
            BattleBdspCapture_End();
            return;
        }
        break;
    }

    case BDSP_CAP_PHASE_IDLE:
    default:
        BattleBdspCapture_End();
        return;
    }

    sCap.phaseTime += BDSP_CAP_DT;
}
