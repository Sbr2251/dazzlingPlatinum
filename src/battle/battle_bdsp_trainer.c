#include "battle/battle_bdsp_trainer.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "constants/battle.h"
#include "generated/genders.h"

#include "battle/battle_bdsp_cam.h"
#include "battle/battle_system.h"
#include "battle_anim/ov12_02235E94.h"
#include "sprite_system.h"
#include "struct_defs/battler_data.h"

#define BDSP_TRAINER_DT          (1.0f / 60.0f)
#define BDSP_TRAINER_HOME_X      (-2.65f)
#define BDSP_TRAINER_HOME_Y      0.0f
#define BDSP_TRAINER_HOME_Z      3.35f
#define BDSP_TRAINER_SCALE       1.22f
#define BDSP_TRAINER_SETTLE_X    68
#define BDSP_TRAINER_THROW_X     60

// Timing (deterministic seconds at 60 Hz)
#define BDSP_BALL_RELEASE_TIME   0.12f
#define BDSP_BALL_FLIGHT_DUR     0.60f
#define BDSP_BALL_ARC_PEAK       1.15f
#define BDSP_BALL_SCALE          1.45f
#define BDSP_TRAINER_HOLD_AFTER  0.62f
#define BDSP_TRAINER_FADE_DUR    0.28f

enum BdspTrainerPhase {
    BDSP_TRAINER_PHASE_IDLE = 0,
    BDSP_TRAINER_PHASE_ENTERING,
    BDSP_TRAINER_PHASE_STANDING,
    BDSP_TRAINER_PHASE_THROWING,
    BDSP_TRAINER_PHASE_FADING,
    BDSP_TRAINER_PHASE_DONE
};

typedef struct BdspTrainerState {
    int phase;
    int trainerKind;
    int playerSlot;
    BOOL introNotified;
    BOOL throwNotified;
    BOOL ballActive;
    BOOL ballDone;
    float animTime;
    float phaseTime;
    float throwTime;
    float fadeTime;
    int animNonce;
    float trainerX;
    float trainerZ;
    float trainerYawDeg;
    float targetMonX;
    float targetMonZ;
    float ballStartX;
    float ballStartY;
    float ballStartZ;
    u32 tickCount;
} BdspTrainerState;

static BdspTrainerState sTrainer;

#ifdef SDK_PORT
static FILE *sTrainerDumpFile;
static int sTrainerDumpPrevPhase = -1;
static int sTrainerDumpPrevBall = -1;

static const char *PhaseName(int phase)
{
    switch (phase) {
    case BDSP_TRAINER_PHASE_IDLE:
        return "IDLE";
    case BDSP_TRAINER_PHASE_ENTERING:
        return "ENTERING";
    case BDSP_TRAINER_PHASE_STANDING:
        return "STANDING";
    case BDSP_TRAINER_PHASE_THROWING:
        return "THROWING";
    case BDSP_TRAINER_PHASE_FADING:
        return "FADING";
    case BDSP_TRAINER_PHASE_DONE:
        return "DONE";
    default:
        return "UNKNOWN";
    }
}

static void TrainerDumpClose(void)
{
    if (sTrainerDumpFile != NULL) {
        fclose(sTrainerDumpFile);
        sTrainerDumpFile = NULL;
    }
    sTrainerDumpPrevPhase = -1;
    sTrainerDumpPrevBall = -1;
}

static void TrainerDumpMaybeLog(const SIM_Battle3DFrame *frame, s16 sprX, BOOL hasSpr, BOOL hasBallRot, BOOL monVis)
{
    const char *path;
    BOOL changed;

    if (sTrainerDumpFile == NULL) {
        path = getenv("SIM_BDSP_TRAINER_DUMP");
        if (path == NULL || path[0] == '\0') {
            return;
        }
        sTrainerDumpFile = fopen(path, "w");
        if (sTrainerDumpFile == NULL) {
            return;
        }
    }

    changed = (sTrainerDumpPrevPhase != sTrainer.phase) || (sTrainerDumpPrevBall != (sTrainer.ballActive ? 1 : 0));
    if (changed || (sTrainer.phase == BDSP_TRAINER_PHASE_THROWING && (sTrainer.tickCount % 5 == 0))) {
        const SIM_Battle3DActor *ta = &frame->actors[0];
        const SIM_Battle3DActor *ba = &frame->actors[1];
        fprintf(sTrainerDumpFile,
            "tick=%u phase=%s spr=%d sprX=%d ballRot=%d monVis=%d trainer=(vis=%d kind=%d pos=%.2f,%.2f,%.2f anim=%d t=%.3f a=%.2f) ball=(vis=%d pos=%.2f,%.2f,%.2f pitch=%.1f)\n",
            (unsigned)sTrainer.tickCount,
            PhaseName(sTrainer.phase),
            hasSpr ? 1 : 0,
            (int)sprX,
            hasBallRot ? 1 : 0,
            monVis ? 1 : 0,
            ta->visible,
            ta->kind,
            ta->worldX,
            ta->worldY,
            ta->worldZ,
            ta->animState,
            ta->animTime,
            ta->alpha,
            ba->visible,
            ba->worldX,
            ba->worldY,
            ba->worldZ,
            ba->pitchDeg);
        fflush(sTrainerDumpFile);
        sTrainerDumpPrevPhase = sTrainer.phase;
        sTrainerDumpPrevBall = sTrainer.ballActive ? 1 : 0;
    }
}
#endif

static float ClampFloat(float v, float lo, float hi)
{
    if (v < lo) {
        return lo;
    }
    if (v > hi) {
        return hi;
    }
    return v;
}

static int FindPlayerSlot(BattleSystem *battleSys)
{
    int maxBattlers = BattleSystem_GetMaxBattlers(battleSys);
    int i;

    if (maxBattlers > SIM_BATTLE3D_MAX_BATTLERS) {
        maxBattlers = SIM_BATTLE3D_MAX_BATTLERS;
    }

    for (i = 0; i < maxBattlers; i++) {
        int btype = BattleSystem_GetBattlerType(battleSys, i);
        if (btype == BATTLER_TYPE_SOLO_PLAYER || btype == BATTLER_TYPE_PLAYER_SIDE_SLOT_1) {
            return i;
        }
    }

    return -1;
}

static void BeginThrow(BattleSystem *battleSys, const SIM_Battle3DFrame *frame, int playerSlot)
{
    float oppX = 2.35f;
    float oppZ = -2.15f;
    float fwdX, fwdZ, len;
    float rightX, rightZ;

    sTrainer.phase = BDSP_TRAINER_PHASE_THROWING;
    sTrainer.animTime = 0.0f;
    sTrainer.phaseTime = 0.0f;
    sTrainer.throwTime = 0.0f;
    sTrainer.fadeTime = 0.0f;
    sTrainer.animNonce++;
    sTrainer.ballActive = FALSE;
    sTrainer.ballDone = FALSE;

    // Target the player's solo/slot-1 Pokemon landing spot
    if (playerSlot >= 0 && playerSlot < SIM_BATTLE3D_MAX_BATTLERS
        && (fabsf(frame->battlers[playerSlot].worldX) > 0.01f || fabsf(frame->battlers[playerSlot].worldZ) > 0.01f)) {
        sTrainer.targetMonX = frame->battlers[playerSlot].worldX;
        sTrainer.targetMonZ = frame->battlers[playerSlot].worldZ;
    } else {
        sTrainer.targetMonX = -2.15f;
        sTrainer.targetMonZ = 2.25f;
    }

    // Compute world-space launch origin near the trainer's throwing right hand
    fwdX = oppX - sTrainer.trainerX;
    fwdZ = oppZ - sTrainer.trainerZ;
    len = sqrtf(fwdX * fwdX + fwdZ * fwdZ);
    if (len > 0.001f) {
        fwdX /= len;
        fwdZ /= len;
    } else {
        fwdX = 0.707f;
        fwdZ = -0.707f;
    }
    // Right-hand side in RH Y-up: right = cross(fwd, up) = (-fwdZ, 0, fwdX)
    rightX = -fwdZ;
    rightZ = fwdX;

    sTrainer.ballStartX = sTrainer.trainerX + fwdX * 0.45f + rightX * 0.25f;
    sTrainer.ballStartY = 1.48f;
    sTrainer.ballStartZ = sTrainer.trainerZ + fwdZ * 0.45f + rightZ * 0.25f;

    if (!sTrainer.throwNotified) {
        sTrainer.throwNotified = TRUE;
        BattleBdspCam_NotifyTrainerThrow();
    }

    (void)battleSys;
}

void BattleBdspTrainer_Reset(void)
{
    memset(&sTrainer, 0, sizeof(sTrainer));
    sTrainer.playerSlot = -1;
    sTrainer.trainerX = BDSP_TRAINER_HOME_X;
    sTrainer.trainerZ = BDSP_TRAINER_HOME_Z;
    sTrainer.trainerYawDeg = 136.0f;
    sTrainer.targetMonX = -2.15f;
    sTrainer.targetMonZ = 2.25f;
#ifdef SDK_PORT
    TrainerDumpClose();
#endif
}

BOOL BattleBdspTrainer_IsIntroActive(void)
{
    return (sTrainer.phase == BDSP_TRAINER_PHASE_ENTERING
        || sTrainer.phase == BDSP_TRAINER_PHASE_STANDING
        || sTrainer.phase == BDSP_TRAINER_PHASE_THROWING
        || sTrainer.phase == BDSP_TRAINER_PHASE_FADING)
        ? TRUE
        : FALSE;
}

void BattleBdspTrainer_Update(BattleSystem *battleSys, SIM_Battle3DFrame *frame)
{
    int playerSlot;
    BattlerData *battlerData;
    ManagedSprite *trainerSpr;
    u32 gender;
    int trainerKind;
    BOOL hasTrainer3d;
    BOOL hasBall3d;
    BOOL monVisible = FALSE;
    BOOL hasBallRot = FALSE;
    s16 sprX = 64;
    s16 sprY = 128;
    float oppX = 2.35f;
    float oppZ = -2.15f;

    if (battleSys == NULL || frame == NULL || !SIM_Battle3D_ModelsEnabled()) {
        return;
    }

    if (frame->alpha <= 0.01f) {
        return;
    }

    playerSlot = FindPlayerSlot(battleSys);
    if (playerSlot < 0) {
        return;
    }

    gender = BattleSystem_GetTrainerGender(battleSys, playerSlot);
    trainerKind = (gender == GENDER_FEMALE)
        ? SIM_BATTLE3D_ACTOR_TRAINER_DAWN
        : SIM_BATTLE3D_ACTOR_TRAINER_LUCAS;

    hasTrainer3d = SIM_Battle3D_HasActorLoaded(trainerKind);
    if (!hasTrainer3d) {
        return;
    }

    hasBall3d = SIM_Battle3D_HasActorLoaded(SIM_BATTLE3D_ACTOR_POKEBALL);

    battlerData = BattleSystem_GetBattlerData(battleSys, playerSlot);
    trainerSpr = (battlerData != NULL) ? battlerData->managedSprite : NULL;
    hasBallRot = (battlerData != NULL && battlerData->ballRotation != NULL) ? TRUE : FALSE;

    if (playerSlot < SIM_BATTLE3D_MAX_BATTLERS && frame->battlers[playerSlot].visible) {
        monVisible = TRUE;
    }

    if (trainerSpr != NULL) {
        ManagedSprite_GetPositionXY(trainerSpr, &sprX, &sprY);
        // Hide the 2D player trainer back OBJ whenever 3D Lucas/Dawn is active so they never overlap.
        ManagedSprite_SetDrawFlag(trainerSpr, FALSE);
    }

    // Also suppress the 2D OAM send-out ball sprite whenever 3D Pokeball is available during intro throw.
    if (hasBall3d && hasBallRot && battlerData->ballRotation != NULL
        && sTrainer.phase != BDSP_TRAINER_PHASE_DONE) {
        ManagedSprite *ballSpr = BallRotation_GetSprite(battlerData->ballRotation);
        if (ballSpr != NULL) {
            ManagedSprite_SetDrawFlag(ballSpr, FALSE);
            ManagedSprite_SetExplicitOamMode(ballSpr, GX_OAM_MODE_OBJWND);
        }
    }

    sTrainer.trainerKind = trainerKind;
    sTrainer.playerSlot = playerSlot;
    sTrainer.trainerYawDeg = atan2f(oppX - BDSP_TRAINER_HOME_X, oppZ - BDSP_TRAINER_HOME_Z) * (180.0f / 3.14159265f);

    // State machine transitions
    switch (sTrainer.phase) {
    case BDSP_TRAINER_PHASE_IDLE:
        if (trainerSpr != NULL && !monVisible) {
            if (!sTrainer.introNotified) {
                BOOL isTrainerBattle = (BattleSystem_GetBattleType(battleSys) & BATTLE_TYPE_TRAINER) ? TRUE : FALSE;
                sTrainer.introNotified = TRUE;
                BattleBdspCam_NotifyIntroStart(isTrainerBattle);
            }
            sTrainer.phase = (sprX > BDSP_TRAINER_SETTLE_X) ? BDSP_TRAINER_PHASE_ENTERING : BDSP_TRAINER_PHASE_STANDING;
            sTrainer.animTime = 0.0f;
            sTrainer.phaseTime = 0.0f;
            sTrainer.trainerX = BDSP_TRAINER_HOME_X;
            sTrainer.trainerZ = BDSP_TRAINER_HOME_Z;
        }
        break;

    case BDSP_TRAINER_PHASE_ENTERING:
        if (trainerSpr == NULL) {
            if (!monVisible) {
                BeginThrow(battleSys, frame, playerSlot);
            } else {
                sTrainer.phase = BDSP_TRAINER_PHASE_DONE;
            }
        } else {
            float slideFrac = ClampFloat((float)(sprX - 64) / 160.0f, 0.0f, 1.0f);
            // Smooth intro glide from slightly right/back into standing spot
            sTrainer.trainerX = BDSP_TRAINER_HOME_X + slideFrac * 1.45f;
            sTrainer.trainerZ = BDSP_TRAINER_HOME_Z + slideFrac * 0.45f;
            sTrainer.animTime += BDSP_TRAINER_DT;
            sTrainer.phaseTime += BDSP_TRAINER_DT;
            if (sprX <= BDSP_TRAINER_SETTLE_X) {
                sTrainer.phase = BDSP_TRAINER_PHASE_STANDING;
                sTrainer.phaseTime = 0.0f;
                sTrainer.trainerX = BDSP_TRAINER_HOME_X;
                sTrainer.trainerZ = BDSP_TRAINER_HOME_Z;
            }
        }
        break;

    case BDSP_TRAINER_PHASE_STANDING:
        sTrainer.trainerX = BDSP_TRAINER_HOME_X;
        sTrainer.trainerZ = BDSP_TRAINER_HOME_Z;
        if (trainerSpr == NULL) {
            if (!monVisible) {
                BeginThrow(battleSys, frame, playerSlot);
            } else {
                sTrainer.phase = BDSP_TRAINER_PHASE_DONE;
            }
        } else if (sprX < BDSP_TRAINER_THROW_X
            || ManagedSprite_IsAnimated(trainerSpr)
            || ManagedSprite_GetAnimationFrame(trainerSpr) > 0) {
            BeginThrow(battleSys, frame, playerSlot);
        } else {
            sTrainer.animTime += BDSP_TRAINER_DT;
            sTrainer.phaseTime += BDSP_TRAINER_DT;
        }
        break;

    case BDSP_TRAINER_PHASE_THROWING:
        sTrainer.throwTime += BDSP_TRAINER_DT;
        sTrainer.animTime = sTrainer.throwTime;

        if (!sTrainer.ballDone) {
            if (monVisible) {
                sTrainer.ballActive = FALSE;
                sTrainer.ballDone = TRUE;
            } else if (sTrainer.throwTime >= BDSP_BALL_RELEASE_TIME) {
                float flightT = sTrainer.throwTime - BDSP_BALL_RELEASE_TIME;
                if (flightT < BDSP_BALL_FLIGHT_DUR) {
                    sTrainer.ballActive = TRUE;
                } else {
                    sTrainer.ballActive = FALSE;
                    sTrainer.ballDone = TRUE;
                }
            }
        }

        // Hide the 2D OAM Pokeball sprite during player send-out while 3D Pokeball is active
        if (hasBall3d && hasBallRot && battlerData->ballRotation != NULL) {
            ManagedSprite *ballSpr = BallRotation_GetSprite(battlerData->ballRotation);
            if (ballSpr != NULL) {
                ManagedSprite_SetDrawFlag(ballSpr, FALSE);
                ManagedSprite_SetExplicitOamMode(ballSpr, GX_OAM_MODE_OBJWND);
            }
        }

        if ((monVisible && sTrainer.throwTime >= 0.40f) || sTrainer.throwTime >= BDSP_TRAINER_HOLD_AFTER + BDSP_BALL_FLIGHT_DUR) {
            sTrainer.phase = BDSP_TRAINER_PHASE_FADING;
            sTrainer.fadeTime = 0.0f;
            sTrainer.ballActive = FALSE;
            sTrainer.ballDone = TRUE;
        }
        break;

    case BDSP_TRAINER_PHASE_FADING:
        sTrainer.fadeTime += BDSP_TRAINER_DT;
        sTrainer.animTime += BDSP_TRAINER_DT;
        if (sTrainer.fadeTime >= BDSP_TRAINER_FADE_DUR) {
            sTrainer.phase = BDSP_TRAINER_PHASE_DONE;
        }
        break;

    case BDSP_TRAINER_PHASE_DONE:
    default:
        break;
    }

    // Populate frame->actors[0] (3D Lucas / Dawn) and frame->actors[1] (3D Poke Ball)
    if (sTrainer.phase == BDSP_TRAINER_PHASE_ENTERING
        || sTrainer.phase == BDSP_TRAINER_PHASE_STANDING
        || sTrainer.phase == BDSP_TRAINER_PHASE_THROWING
        || sTrainer.phase == BDSP_TRAINER_PHASE_FADING) {
        SIM_Battle3DActor *ta = &frame->actors[0];
        float alpha = 1.0f;
        float exitShift = 0.0f;

        if (sTrainer.phase == BDSP_TRAINER_PHASE_FADING) {
            float u = ClampFloat(sTrainer.fadeTime / BDSP_TRAINER_FADE_DUR, 0.0f, 1.0f);
            alpha = 1.0f - u;
            exitShift = u * 0.75f;
        }

        ta->visible = 1;
        ta->kind = sTrainer.trainerKind;
        ta->worldX = sTrainer.trainerX - exitShift * 0.7f;
        ta->worldY = BDSP_TRAINER_HOME_Y;
        ta->worldZ = sTrainer.trainerZ + exitShift * 0.7f;
        ta->yawDeg = sTrainer.trainerYawDeg;
        ta->pitchDeg = 0.0f;
        ta->rollDeg = 0.0f;
        ta->scale = BDSP_TRAINER_SCALE;
        ta->alpha = alpha;
        ta->animState = (sTrainer.phase == BDSP_TRAINER_PHASE_THROWING || sTrainer.phase == BDSP_TRAINER_PHASE_FADING)
            ? SIM_BATTLE3D_TRANIM_THROW
            : SIM_BATTLE3D_TRANIM_WAIT;
        ta->animTime = sTrainer.animTime;
        ta->animNonce = sTrainer.animNonce;
    }

    if (sTrainer.ballActive && hasBall3d) {
        SIM_Battle3DActor *ba = &frame->actors[1];
        float u = ClampFloat((sTrainer.throwTime - BDSP_BALL_RELEASE_TIME) / BDSP_BALL_FLIGHT_DUR, 0.0f, 1.0f);
        float bx = sTrainer.ballStartX + (sTrainer.targetMonX - sTrainer.ballStartX) * u;
        float bz = sTrainer.ballStartZ + (sTrainer.targetMonZ - sTrainer.ballStartZ) * u;
        float by = sTrainer.ballStartY + (0.35f - sTrainer.ballStartY) * u
            + 4.0f * BDSP_BALL_ARC_PEAK * u * (1.0f - u);

        ba->visible = 1;
        ba->kind = SIM_BATTLE3D_ACTOR_POKEBALL;
        ba->worldX = bx;
        ba->worldY = by;
        ba->worldZ = bz;
        ba->yawDeg = sTrainer.trainerYawDeg;
        ba->pitchDeg = u * 720.0f;
        ba->rollDeg = u * 180.0f;
        ba->scale = BDSP_BALL_SCALE;
        ba->alpha = 1.0f;
        ba->animState = 0;
        ba->animTime = 0.0f;
        ba->animNonce = sTrainer.animNonce;
    }

#ifdef SDK_PORT
    TrainerDumpMaybeLog(frame, sprX, trainerSpr != NULL, hasBallRot, monVisible);
#endif
    sTrainer.tickCount++;
}
