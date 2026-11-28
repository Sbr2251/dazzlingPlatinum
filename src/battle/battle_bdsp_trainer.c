#include "battle/battle_bdsp_trainer.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "constants/battle.h"
#include "generated/genders.h"
#include "generated/trainer_classes.h"

#include "battle/battle_bdsp_cam.h"
#include "battle/battle_context.h"
#include "battle/battle_system.h"
#include "battle_anim/ov12_02235E94.h"
#include "sprite_system.h"
#include "struct_defs/battler_data.h"
#include "struct_defs/trainer.h"

#define BDSP_TRAINER_DT                 (1.0f / 60.0f)
#define BDSP_TRAINER_HOME_X             (-4.05f)
#define BDSP_TRAINER_HOME_Y             0.0f
#define BDSP_TRAINER_HOME_Z             4.10f
#define BDSP_TRAINER_SCALE              1.18f
#define BDSP_TRAINER_SETTLE_X           68
#define BDSP_TRAINER_THROW_X            60

#define BDSP_OPP_HOME_X                 4.00f
#define BDSP_OPP_HOME_Y                 0.0f
#define BDSP_OPP_HOME_Z                 (-3.75f)
#define BDSP_OPP_SCALE                  1.32f
#define BDSP_OPP_SETTLE_X               192
#define BDSP_OPP_THROW_START_X          197
#define BDSP_OPP_ADVENT_POSE_DUR        1.20f
#define BDSP_OPP_THROW_DUR              0.85f
#define BDSP_OPP_THROW_MIN_ON_MON       0.55f
#define BDSP_OPP_EXIT_DUR               0.42f

// BDSP pc0001_00 (Lucas) & pc0002_00 (Dawn) throw clip (advent03_b) metrics:
// Both trainers throw with LHand (boneKind=2, ee400 _locators[75]=LItem1);
// exact forward whip release occurs on integer frame 21 (21/60s = 0.350s).
#define BDSP_THROW_HAND_BONE            2
#define BDSP_BALL_RELEASE_TICK          21
#define BDSP_BALL_FLIGHT_TICKS          24
#define BDSP_BALL_EARLY_FINISH_TICKS    4
#define BDSP_BALL_ARC_PEAK              0.55f
#define BDSP_BALL_SCALE_HELD            0.68f
#define BDSP_BALL_SCALE_FLIGHT          0.76f
#define BDSP_BURST_DUR                  0.360f
#define BDSP_BURST_RADIUS               0.88f
#define BDSP_BURST_CENTER_Y             0.68f
#define BDSP_MAT_DUR                    0.440f
#define BDSP_TRAINER_FOLLOWTHROUGH_END  0.750f
#define BDSP_TRAINER_EXIT_DUR           0.300f

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
    int playerSlot2;
    BOOL introNotified;
    BOOL throwNotified;
    BOOL ballReleased;
    BOOL ballActive;
    BOOL ballDone;
    BOOL hasHandPos;
    BOOL burstTriggered;
    BOOL burstActive;
    BOOL matArmed[2];
    BOOL matActive[2];
    BOOL matDone[2];
    int throwTicks;
    int flightTicks;
    int flightDurTicks;
    float animTime;
    float phaseTime;
    float throwTime;
    float fadeTime;
    float burstTime;
    float matTime[2];
    int animNonce;
    float trainerX;
    float trainerZ;
    float trainerYawDeg;
    float targetMonX;
    float targetMonZ;
    float targetMon2X;
    float targetMon2Z;
    float lastHandPos[3];
    float ballStartX;
    float ballStartY;
    float ballStartZ;
    ManagedSprite *hidden2dSpr;
    ManagedSprite *hiddenBallSpr[2];
    u32 tickCount;
} BdspTrainerState;

typedef struct BdspOppTrainerState {
    int phase;
    int trainerModelId;
    int enemySlot;
    BOOL decided2d;
    ManagedSprite *hidden2dSpr;
    s16 settledSprX;
    float animTime;
    float phaseTime;
    float throwTime;
    float fadeTime;
    int animNonce;
    float posX;
    float posZ;
    float yawDeg;
} BdspOppTrainerState;

static BdspTrainerState sTrainer;
static BdspOppTrainerState sOppTrainer;

static int MapTrainerClassToBdspModel(int trainerClass)
{
    switch (trainerClass) {
    case TRAINER_CLASS_YOUNGSTER:               return 28;
    case TRAINER_CLASS_LASS:                    return 29;
    case TRAINER_CLASS_CAMPER:                  return 1004;
    case TRAINER_CLASS_PICNICKER:               return 1005;
    case TRAINER_CLASS_BUG_CATCHER:             return 1006;
    case TRAINER_CLASS_AROMA_LADY:              return 1007;
    case TRAINER_CLASS_TWINS:                   return 1008;
    case TRAINER_CLASS_HIKER:                   return 49;
    case TRAINER_CLASS_BATTLE_GIRL:             return 1010;
    case TRAINER_CLASS_FISHERMAN:               return 48;
    case TRAINER_CLASS_CYCLIST_MALE:            return 1012;
    case TRAINER_CLASS_CYCLIST_FEMALE:          return 1013;
    case TRAINER_CLASS_BLACK_BELT:              return 50;
    case TRAINER_CLASS_ARTIST:                  return 44;
    case TRAINER_CLASS_BREEDER_MALE:            return 42;
    case TRAINER_CLASS_BREEDER_FEMALE:          return 43;
    case TRAINER_CLASS_COWGIRL:                 return 18;
    case TRAINER_CLASS_JOGGER:                  return 1019;
    case TRAINER_CLASS_POKEFAN_MALE:            return 1020;
    case TRAINER_CLASS_POKEFAN_FEMALE:          return 1021;
    case TRAINER_CLASS_POKE_KID:                return 27;
    case TRAINER_CLASS_YOUNG_COUPLE:            return 1023;
    case TRAINER_CLASS_ACE_TRAINER_MALE:        return 1024;
    case TRAINER_CLASS_ACE_TRAINER_FEMALE:      return 1025;
    case TRAINER_CLASS_WAITRESS:                return 1026;
    case TRAINER_CLASS_VETERAN:                 return 1027;
    case TRAINER_CLASS_NINJA_BOY:               return 1028;
    case TRAINER_CLASS_DRAGON_TAMER:            return 1029;
    case TRAINER_CLASS_BIRD_KEEPER:             return 1030;
    case TRAINER_CLASS_DOUBLE_TEAM:             return 1024;
    case TRAINER_CLASS_RICH_BOY:                return 1032;
    case TRAINER_CLASS_LADY:                    return 1033;
    case TRAINER_CLASS_GENTLEMAN:               return 46;
    case TRAINER_CLASS_SOCIALITE:               return 47;
    case TRAINER_CLASS_BEAUTY:                  return 51;
    case TRAINER_CLASS_COLLECTOR:               return 1037;
    case TRAINER_CLASS_POLICEMAN:               return 39;
    case TRAINER_CLASS_RANGER_MALE:             return 1039;
    case TRAINER_CLASS_RANGER_FEMALE:           return 1040;
    case TRAINER_CLASS_SCIENTIST:               return 1041;
    case TRAINER_CLASS_SWIMMER_MALE:            return 53;
    case TRAINER_CLASS_SWIMMER_FEMALE:          return 54;
    case TRAINER_CLASS_TUBER_MALE:              return 1044;
    case TRAINER_CLASS_TUBER_FEMALE:            return 1045;
    case TRAINER_CLASS_SAILOR:                  return 1046;
    case TRAINER_CLASS_SIS_AND_BRO:             return 2018;
    case TRAINER_CLASS_RUIN_MANIAC:             return 1048;
    case TRAINER_CLASS_PSYCHIC_MALE:            return 1049;
    case TRAINER_CLASS_PSYCHIC_FEMALE:          return 1050;
    case TRAINER_CLASS_PI:                      return 1051;
    case TRAINER_CLASS_GUITARIST:               return 1052;
    case TRAINER_CLASS_ACE_TRAINER_SNOW_MALE:   return 1053;
    case TRAINER_CLASS_ACE_TRAINER_SNOW_FEMALE: return 1054;
    case TRAINER_CLASS_SKIER_MALE:              return 1055;
    case TRAINER_CLASS_SKIER_FEMALE:            return 1056;
    case TRAINER_CLASS_ROUGHNECK:               return 1057;
    case TRAINER_CLASS_CLOWN:                   return 1058;
    case TRAINER_CLASS_WORKER:                  return 40;
    case TRAINER_CLASS_SCHOOL_KID_MALE:         return 30;
    case TRAINER_CLASS_SCHOOL_KID_FEMALE:       return 31;
    case TRAINER_CLASS_LEADER_ROARK:            return 1062;
    case TRAINER_CLASS_RIVAL:                   return 2;
    case TRAINER_CLASS_LEADER_BYRON:            return 1064;
    case TRAINER_CLASS_ELITE_FOUR_AARON:        return 1065;
    case TRAINER_CLASS_ELITE_FOUR_BERTHA:       return 1066;
    case TRAINER_CLASS_ELITE_FOUR_FLINT:        return 1067;
    case TRAINER_CLASS_ELITE_FOUR_LUCIAN:       return 1068;
    case TRAINER_CLASS_CHAMPION_CYNTHIA:        return 1;
    case TRAINER_CLASS_BELLE_AND_PA:            return 1071;
    case TRAINER_CLASS_RANCHER:                 return 1071;
    case TRAINER_CLASS_COMMANDER_MARS:          return 1072;
    case TRAINER_CLASS_GALACTIC_GRUNT_MALE:     return 1073;
    case TRAINER_CLASS_LEADER_GARDENIA:         return 1074;
    case TRAINER_CLASS_LEADER_WAKE:             return 1075;
    case TRAINER_CLASS_LEADER_MAYLENE:          return 1076;
    case TRAINER_CLASS_LEADER_FANTINA:          return 1077;
    case TRAINER_CLASS_LEADER_CANDICE:          return 1078;
    case TRAINER_CLASS_LEADER_VOLKNER:          return 1079;
    case TRAINER_CLASS_PARASOL_LADY:            return 1080;
    case TRAINER_CLASS_WAITER:                  return 1081;
    case TRAINER_CLASS_INTERVIEWERS:            return 61;
    case TRAINER_CLASS_CAMERAMAN:               return 62;
    case TRAINER_CLASS_REPORTER:                return 61;
    case TRAINER_CLASS_IDOL:                    return 1085;
    case TRAINER_CLASS_GALACTIC_BOSS:           return 1086;
    case TRAINER_CLASS_COMMANDER_JUPITER:       return 1087;
    case TRAINER_CLASS_COMMANDER_SATURN:        return 1088;
    case TRAINER_CLASS_GALACTIC_GRUNT_FEMALE:   return 1089;
    case TRAINER_CLASS_TRAINER_CHERYL:          return 2007;
    case TRAINER_CLASS_TRAINER_RILEY:           return 2009;
    case TRAINER_CLASS_TRAINER_MARLEY:          return 2010;
    case TRAINER_CLASS_TRAINER_BUCK:            return 2011;
    case TRAINER_CLASS_TRAINER_MIRA:            return 2008;
    case TRAINER_CLASS_TOWER_TYCOON:            return 1097;
    default:                                    return 0;
    }
}

static int FindEnemySlot(BattleSystem *battleSys)
{
    int maxBattlers = BattleSystem_GetMaxBattlers(battleSys);
    int i;

    if (maxBattlers > SIM_BATTLE3D_MAX_BATTLERS) {
        maxBattlers = SIM_BATTLE3D_MAX_BATTLERS;
    }

    for (i = 0; i < maxBattlers; i++) {
        if (BattleSystem_GetBattlerData(battleSys, i) == NULL) {
            continue;
        }
        int btype = BattleSystem_GetBattlerType(battleSys, i);
        if (btype == BATTLER_TYPE_SOLO_ENEMY || btype == BATTLER_TYPE_ENEMY_SIDE_SLOT_1) {
            return i;
        }
    }

    return -1;
}

static void GetTrainerPalmOffset(int trainerKind, float outOff[3])
{
    // Exact held LItem1 local offsets in LHand bone space from throw_analysis.json
    if (trainerKind == SIM_BATTLE3D_ACTOR_TRAINER_DAWN) {
        outOff[0] = 0.0692f;
        outOff[1] = -0.0497f;
        outOff[2] = 0.0080f;
    } else {
        outOff[0] = 0.0627f;
        outOff[1] = -0.0562f;
        outOff[2] = 0.0061f;
    }
}

#ifdef SDK_PORT
static FILE *sTrainerDumpFile;
static int sTrainerDumpPrevPhase = -1;
static int sTrainerDumpPrevBall = -1;
static int sTrainerDumpPrevBurst = -1;

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
    sTrainerDumpPrevBurst = -1;
}

static void TrainerDumpMaybeLog(const SIM_Battle3DFrame *frame, s16 sprX, BOOL hasSpr, BOOL hasBallRot, BOOL monVis)
{
    const char *path;
    BOOL changed;
    int ballState;
    int burstState;

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

    ballState = sTrainer.ballActive ? 2 : (frame->actors[1].visible ? 1 : 0);
    burstState = frame->burst.active ? 1 : 0;
    changed = (sTrainerDumpPrevPhase != sTrainer.phase)
        || (sTrainerDumpPrevBall != ballState)
        || (sTrainerDumpPrevBurst != burstState);
    if (changed
        || ((sTrainer.phase == BDSP_TRAINER_PHASE_THROWING || sTrainer.phase == BDSP_TRAINER_PHASE_FADING || sTrainer.burstActive || sTrainer.matActive[0])
            && (sTrainer.tickCount % 4 == 0))) {
        const SIM_Battle3DActor *ta = &frame->actors[0];
        const SIM_Battle3DActor *ba = &frame->actors[1];
        float monScale = (sTrainer.playerSlot >= 0 && sTrainer.playerSlot < SIM_BATTLE3D_MAX_BATTLERS)
            ? frame->battlers[sTrainer.playerSlot].modelScale
            : 0.0f;
        float monFlash = (sTrainer.playerSlot >= 0 && sTrainer.playerSlot < SIM_BATTLE3D_MAX_BATTLERS)
            ? frame->battlers[sTrainer.playerSlot].flashAmount
            : 0.0f;
        fprintf(sTrainerDumpFile,
            "tick=%u phase=%s tTick=%d fTick=%d/%d spr=%d sprX=%d ballRot=%d monVis=%d trainer=(vis=%d kind=%d pos=%.2f,%.2f,%.2f anim=%d t=%.3f a=%.2f) ball=(vis=%d attach=%d pos=%.3f,%.3f,%.3f) burst=(act=%d p=%.2f) mon=(sc=%.2f fl=%.2f)\n",
            (unsigned)sTrainer.tickCount,
            PhaseName(sTrainer.phase),
            sTrainer.throwTicks,
            sTrainer.flightTicks,
            sTrainer.flightDurTicks,
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
            ba->attachBoneKind,
            ba->worldX,
            ba->worldY,
            ba->worldZ,
            frame->burst.active,
            frame->burst.progress,
            monScale,
            monFlash);
        fflush(sTrainerDumpFile);
        sTrainerDumpPrevPhase = sTrainer.phase;
        sTrainerDumpPrevBall = ballState;
        sTrainerDumpPrevBurst = burstState;
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

static float ComputeNormalizedPlayerScale(BattleSystem *battleSys, int slot, int btype)
{
    BOOL isSolo = (btype == BATTLER_TYPE_SOLO_PLAYER || btype == BATTLER_TYPE_SOLO_ENEMY);
    float baseScale = isSolo ? 1.40f : 1.25f;
    BattleContext *ctx = BattleSystem_GetBattleContext(battleSys);
    float bmin[3], bmax[3];
    float h, rx, rz, r;
    float minH = isSolo ? 0.65f : 0.55f;
    float maxH = isSolo ? 2.45f : 1.95f;
    float maxR = isSolo ? 2.05f : 1.55f;
    float scale = baseScale;

    if (ctx == NULL || slot < 0 || slot >= SIM_BATTLE3D_MAX_BATTLERS) {
        return baseScale;
    }
    if (!SIM_Battle3D_GetModelBBox(ctx->battleMons[slot].species,
            ctx->battleMons[slot].formNum,
            ctx->battleMons[slot].isShiny,
            bmin, bmax)) {
        return baseScale;
    }

    h = bmax[1] - bmin[1];
    rx = (bmax[0] - bmin[0]) * 0.5f;
    rz = (bmax[2] - bmin[2]) * 0.5f;
    r = (rx > rz) ? rx : rz;
    if (h > 0.01f) {
        float effH = h * scale;
        if (effH < minH) {
            scale = minH / h;
        } else if (effH > maxH) {
            scale = maxH / h;
        }
    }
    if (r > 0.01f && (r * scale) > maxR) {
        scale = maxR / r;
    }
    return ClampFloat(scale, 0.15f, 3.5f);
}

static int FindPlayerSlot(BattleSystem *battleSys)
{
    int maxBattlers = BattleSystem_GetMaxBattlers(battleSys);
    int i;

    if (maxBattlers > SIM_BATTLE3D_MAX_BATTLERS) {
        maxBattlers = SIM_BATTLE3D_MAX_BATTLERS;
    }

    for (i = 0; i < maxBattlers; i++) {
        if (BattleSystem_GetBattlerData(battleSys, i) == NULL) {
            continue;
        }
        int btype = BattleSystem_GetBattlerType(battleSys, i);
        if (btype == BATTLER_TYPE_SOLO_PLAYER || btype == BATTLER_TYPE_PLAYER_SIDE_SLOT_1) {
            return i;
        }
    }

    return -1;
}

static int FindPlayerSlot2(BattleSystem *battleSys)
{
    int maxBattlers = BattleSystem_GetMaxBattlers(battleSys);
    int i;

    if (maxBattlers > SIM_BATTLE3D_MAX_BATTLERS) {
        maxBattlers = SIM_BATTLE3D_MAX_BATTLERS;
    }

    for (i = 0; i < maxBattlers; i++) {
        if (BattleSystem_GetBattlerData(battleSys, i) == NULL) {
            continue;
        }
        if (BattleSystem_GetBattlerType(battleSys, i) == BATTLER_TYPE_PLAYER_SIDE_SLOT_2) {
            return i;
        }
    }

    return -1;
}

static void ComputeFallbackReleasePos(float outPos[3])
{
    float oppX = 2.35f;
    float oppZ = -2.15f;
    float fwdX = oppX - sTrainer.trainerX;
    float fwdZ = oppZ - sTrainer.trainerZ;
    float len = sqrtf(fwdX * fwdX + fwdZ * fwdZ);
    float leftX, leftZ;

    if (len > 0.001f) {
        fwdX /= len;
        fwdZ /= len;
    } else {
        fwdX = 0.707f;
        fwdZ = -0.707f;
    }
    // Left-hand side in RH Y-up: left = cross(up, fwd) = (fwdZ, 0, -fwdX)
    leftX = fwdZ;
    leftZ = -fwdX;

    outPos[0] = sTrainer.trainerX + fwdX * 0.36f + leftX * 0.32f;
    outPos[1] = 1.50f;
    outPos[2] = sTrainer.trainerZ + fwdZ * 0.36f + leftZ * 0.32f;
}

static void TriggerBurstAndMaterialize(void)
{
    int s;

    if (!sTrainer.burstTriggered) {
        sTrainer.burstTriggered = TRUE;
        sTrainer.burstActive = TRUE;
        sTrainer.burstTime = 0.0f;
    }
    for (s = 0; s < 2; s++) {
        if (!sTrainer.matDone[s]) {
            sTrainer.matArmed[s] = TRUE;
        }
    }
}

static void ReleaseBallFromHand(const float palmOffset[3])
{
    float socketPos[3];
    float minAnimT = (float)(BDSP_BALL_RELEASE_TICK - 1) * BDSP_TRAINER_DT;

    sTrainer.ballReleased = TRUE;
    sTrainer.ballActive = TRUE;
    sTrainer.flightTicks = 0;
    sTrainer.flightDurTicks = BDSP_BALL_FLIGHT_TICKS;

    // Sample the exact versioned transformed palm center (boneWorld * perRigPalmOffset)
    // from the active throw nonce so flight u=0 matches the final held frame seamlessly.
    if (SIM_Battle3D_GetActorSocketWorldPos(0, BDSP_THROW_HAND_BONE, sTrainer.animNonce,
            minAnimT, palmOffset, socketPos)) {
        sTrainer.lastHandPos[0] = socketPos[0];
        sTrainer.lastHandPos[1] = socketPos[1];
        sTrainer.lastHandPos[2] = socketPos[2];
        sTrainer.hasHandPos = TRUE;
    } else if (SIM_Battle3D_GetActorHandPos(0, BDSP_THROW_HAND_BONE, socketPos)) {
        sTrainer.lastHandPos[0] = socketPos[0];
        sTrainer.lastHandPos[1] = socketPos[1];
        sTrainer.lastHandPos[2] = socketPos[2];
        sTrainer.hasHandPos = TRUE;
    } else if (sTrainer.hasHandPos) {
        socketPos[0] = sTrainer.lastHandPos[0];
        socketPos[1] = sTrainer.lastHandPos[1];
        socketPos[2] = sTrainer.lastHandPos[2];
    } else {
        ComputeFallbackReleasePos(socketPos);
    }

    sTrainer.ballStartX = socketPos[0];
    sTrainer.ballStartY = socketPos[1];
    sTrainer.ballStartZ = socketPos[2];
}

static void BeginThrow(BattleSystem *battleSys, const SIM_Battle3DFrame *frame, int playerSlot, int playerSlot2)
{
    sTrainer.phase = BDSP_TRAINER_PHASE_THROWING;
    sTrainer.throwTicks = 0;
    sTrainer.flightTicks = 0;
    sTrainer.flightDurTicks = BDSP_BALL_FLIGHT_TICKS;
    sTrainer.animTime = 0.0f;
    sTrainer.phaseTime = 0.0f;
    sTrainer.throwTime = 0.0f;
    sTrainer.fadeTime = 0.0f;
    sTrainer.animNonce++;
    sTrainer.ballReleased = FALSE;
    sTrainer.ballActive = FALSE;
    sTrainer.ballDone = FALSE;
    sTrainer.burstTriggered = FALSE;
    sTrainer.burstActive = FALSE;
    sTrainer.burstTime = 0.0f;
    sTrainer.matArmed[0] = FALSE;
    sTrainer.matArmed[1] = FALSE;
    sTrainer.matActive[0] = FALSE;
    sTrainer.matActive[1] = FALSE;
    sTrainer.matDone[0] = FALSE;
    sTrainer.matDone[1] = FALSE;
    sTrainer.matTime[0] = 0.0f;
    sTrainer.matTime[1] = 0.0f;

    // Target the player's solo/slot-1 Pokemon landing spot
    if (playerSlot >= 0 && playerSlot < SIM_BATTLE3D_MAX_BATTLERS
        && (fabsf(frame->battlers[playerSlot].worldX) > 0.01f || fabsf(frame->battlers[playerSlot].worldZ) > 0.01f)) {
        sTrainer.targetMonX = frame->battlers[playerSlot].worldX;
        sTrainer.targetMonZ = frame->battlers[playerSlot].worldZ;
    } else if (playerSlot2 >= 0) {
        sTrainer.targetMonX = -2.75f;
        sTrainer.targetMonZ = 1.75f;
    } else {
        sTrainer.targetMonX = -2.15f;
        sTrainer.targetMonZ = 2.25f;
    }

    // Optional doubles partner landing spot (slot 2)
    if (playerSlot2 >= 0 && playerSlot2 < SIM_BATTLE3D_MAX_BATTLERS
        && (fabsf(frame->battlers[playerSlot2].worldX) > 0.01f || fabsf(frame->battlers[playerSlot2].worldZ) > 0.01f)) {
        sTrainer.targetMon2X = frame->battlers[playerSlot2].worldX;
        sTrainer.targetMon2Z = frame->battlers[playerSlot2].worldZ;
    } else {
        sTrainer.targetMon2X = -1.55f;
        sTrainer.targetMon2Z = 2.65f;
    }

    ComputeFallbackReleasePos(sTrainer.lastHandPos);
    sTrainer.ballStartX = sTrainer.lastHandPos[0];
    sTrainer.ballStartY = sTrainer.lastHandPos[1];
    sTrainer.ballStartZ = sTrainer.lastHandPos[2];

    if (!sTrainer.throwNotified) {
        sTrainer.throwNotified = TRUE;
        BattleBdspCam_NotifyTrainerThrow();
    }

    (void)battleSys;
}

static void SetOwnedSpriteHidden(ManagedSprite **trackedSlot, ManagedSprite *liveSpr, BOOL hide)
{
    if (liveSpr == NULL) {
        *trackedSlot = NULL;
        return;
    }
    if (hide) {
        ManagedSprite_SetDrawFlag(liveSpr, FALSE);
        *trackedSlot = liveSpr;
    } else {
        if (*trackedSlot == liveSpr) {
            ManagedSprite_SetDrawFlag(liveSpr, TRUE);
        }
        *trackedSlot = NULL;
    }
}

static void SuppressLegacyBallSprite(BattleSystem *battleSys, int slot, int ballIdx)
{
    BattlerData *bd;
    ManagedSprite *ballSpr;

    if (slot < 0 || ballIdx < 0 || ballIdx >= 2) {
        return;
    }
    bd = BattleSystem_GetBattlerData(battleSys, slot);
    if (bd == NULL || bd->ballRotation == NULL) {
        sTrainer.hiddenBallSpr[ballIdx] = NULL;
        return;
    }
    ballSpr = BallRotation_GetSprite(bd->ballRotation);
    if (ballSpr != NULL) {
        ManagedSprite_SetDrawFlag(ballSpr, FALSE);
        ManagedSprite_SetExplicitOamMode(ballSpr, GX_OAM_MODE_OBJWND);
        sTrainer.hiddenBallSpr[ballIdx] = ballSpr;
    } else {
        sTrainer.hiddenBallSpr[ballIdx] = NULL;
    }
}

static void RestoreOwnedBallSprite(BattleSystem *battleSys, int slot, int ballIdx)
{
    BattlerData *bd;
    ManagedSprite *ballSpr;

    if (ballIdx < 0 || ballIdx >= 2) {
        return;
    }
    if (slot < 0 || sTrainer.hiddenBallSpr[ballIdx] == NULL) {
        sTrainer.hiddenBallSpr[ballIdx] = NULL;
        return;
    }
    bd = BattleSystem_GetBattlerData(battleSys, slot);
    ballSpr = (bd != NULL && bd->ballRotation != NULL) ? BallRotation_GetSprite(bd->ballRotation) : NULL;
    if (ballSpr != NULL && ballSpr == sTrainer.hiddenBallSpr[ballIdx]) {
        ManagedSprite_SetDrawFlag(ballSpr, TRUE);
        ManagedSprite_SetExplicitOamMode(ballSpr, GX_OAM_MODE_NORMAL);
    }
    sTrainer.hiddenBallSpr[ballIdx] = NULL;
}

void BattleBdspTrainer_Prefetch(BattleSystem *battleSys)
{
    u32 battleType;
    int enemySlot;
    Trainer *trainer;
    int trId;

    if (battleSys == NULL || !SIM_Battle3D_ModelsEnabled()) {
        return;
    }
    if (sOppTrainer.decided2d || sOppTrainer.phase == BDSP_TRAINER_PHASE_DONE) {
        return;
    }

    battleType = BattleSystem_GetBattleType(battleSys);
    if ((battleType & BATTLE_TYPE_TRAINER) == 0) {
        return;
    }
    if (battleType & (BATTLE_TYPE_SAFARI | BATTLE_TYPE_PAL_PARK | BATTLE_TYPE_CATCH_TUTORIAL
                      | BATTLE_TYPE_TAG | BATTLE_TYPE_2vs2)) {
        return;
    }

    enemySlot = FindEnemySlot(battleSys);
    if (enemySlot < 0) {
        enemySlot = BATTLER_ENEMY_1;
    }

    trainer = BattleSystem_GetTrainer(battleSys, enemySlot);
    trId = (trainer != NULL) ? MapTrainerClassToBdspModel(trainer->header.trainerType) : 0;
    if (trId > 0) {
        (void)SIM_Battle3D_HasOpponentTrainerReady(trId);
    }
}

void BattleBdspTrainer_Reset(void)
{
    memset(&sTrainer, 0, sizeof(sTrainer));
    sTrainer.playerSlot = -1;
    sTrainer.playerSlot2 = -1;
    sTrainer.trainerX = BDSP_TRAINER_HOME_X;
    sTrainer.trainerZ = BDSP_TRAINER_HOME_Z;
    sTrainer.trainerYawDeg = 136.0f;
    sTrainer.targetMonX = -2.15f;
    sTrainer.targetMonZ = 2.25f;
    sTrainer.targetMon2X = -1.55f;
    sTrainer.targetMon2Z = 2.65f;

    memset(&sOppTrainer, 0, sizeof(sOppTrainer));
    sOppTrainer.enemySlot = -1;
    sOppTrainer.posX = BDSP_OPP_HOME_X;
    sOppTrainer.posZ = BDSP_OPP_HOME_Z;
    sOppTrainer.yawDeg = -45.0f;
#ifdef SDK_PORT
    TrainerDumpClose();
#endif
}

BOOL BattleBdspTrainer_IsIntroActive(void)
{
    BOOL playerActive = (sTrainer.phase == BDSP_TRAINER_PHASE_ENTERING
        || sTrainer.phase == BDSP_TRAINER_PHASE_STANDING
        || sTrainer.phase == BDSP_TRAINER_PHASE_THROWING
        || sTrainer.phase == BDSP_TRAINER_PHASE_FADING)
        ? TRUE
        : FALSE;
    BOOL oppActive = (sOppTrainer.phase == BDSP_TRAINER_PHASE_ENTERING
        || sOppTrainer.phase == BDSP_TRAINER_PHASE_STANDING
        || sOppTrainer.phase == BDSP_TRAINER_PHASE_THROWING
        || sOppTrainer.phase == BDSP_TRAINER_PHASE_FADING)
        ? TRUE
        : FALSE;
    return (playerActive || oppActive) ? TRUE : FALSE;
}

static void UpdateOpponentTrainer(BattleSystem *battleSys, SIM_Battle3DFrame *frame, u32 battleType)
{
    int enemySlot;
    Trainer *trainer;
    int trId;
    BattlerData *enemyBd;
    ManagedSprite *enemySpr;
    BOOL hasOpp3d;
    BOOL enemyMonVisible = FALSE;
    s16 sprX = 192;
    s16 sprY = 64;

    if ((battleType & BATTLE_TYPE_TRAINER) == 0) {
        return;
    }

    enemySlot = FindEnemySlot(battleSys);
    if (enemySlot < 0) {
        return;
    }

    enemyBd = BattleSystem_GetBattlerData(battleSys, enemySlot);
    enemySpr = (enemyBd != NULL) ? enemyBd->managedSprite : NULL;

    // Two-trainer doubles (TAG / 2vs2) use distinct enemy sprites at X=216 and slot 2:
    // keep both enemy trainers cleanly on the legacy 2D path.
    if (battleType & (BATTLE_TYPE_TAG | BATTLE_TYPE_2vs2)) {
        SetOwnedSpriteHidden(&sOppTrainer.hidden2dSpr, enemySpr, FALSE);
        sOppTrainer.decided2d = TRUE;
        sOppTrainer.phase = BDSP_TRAINER_PHASE_DONE;
        return;
    }

    if (sOppTrainer.decided2d || sOppTrainer.phase == BDSP_TRAINER_PHASE_DONE) {
        SetOwnedSpriteHidden(&sOppTrainer.hidden2dSpr, enemySpr, FALSE);
        return;
    }

    if (enemySlot < SIM_BATTLE3D_MAX_BATTLERS && frame->battlers[enemySlot].visible) {
        enemyMonVisible = TRUE;
    }

    trainer = BattleSystem_GetTrainer(battleSys, enemySlot);
    trId = (trainer != NULL) ? MapTrainerClassToBdspModel(trainer->header.trainerType) : 0;
    hasOpp3d = (trId > 0) ? SIM_Battle3D_HasOpponentTrainerReady(trId) : FALSE;

    // Latch one opponent-trainer decision per battle so a late-loaded model never pops in
    // mid-intro or hijacks the victory outro slide-in.
    if (sOppTrainer.phase == BDSP_TRAINER_PHASE_IDLE) {
        if (enemyMonVisible || (enemySpr != NULL && !hasOpp3d)) {
            SetOwnedSpriteHidden(&sOppTrainer.hidden2dSpr, enemySpr, FALSE);
            sOppTrainer.decided2d = TRUE;
            sOppTrainer.phase = BDSP_TRAINER_PHASE_DONE;
            return;
        }
        if (!hasOpp3d) {
            return;
        }
    } else if (!hasOpp3d) {
        SetOwnedSpriteHidden(&sOppTrainer.hidden2dSpr, enemySpr, FALSE);
        sOppTrainer.decided2d = TRUE;
        sOppTrainer.phase = BDSP_TRAINER_PHASE_DONE;
        return;
    }

    if (enemySpr != NULL) {
        ManagedSprite_GetPositionXY(enemySpr, &sprX, &sprY);
    }

    sOppTrainer.enemySlot = enemySlot;
    sOppTrainer.trainerModelId = trId;
    sOppTrainer.yawDeg = atan2f(BDSP_TRAINER_HOME_X - BDSP_OPP_HOME_X,
                                BDSP_TRAINER_HOME_Z - BDSP_OPP_HOME_Z) * (180.0f / 3.14159265f);

    switch (sOppTrainer.phase) {
    case BDSP_TRAINER_PHASE_IDLE:
        if (enemySpr != NULL && !enemyMonVisible) {
            sOppTrainer.phase = (sprX < BDSP_OPP_SETTLE_X)
                ? BDSP_TRAINER_PHASE_ENTERING
                : BDSP_TRAINER_PHASE_STANDING;
            sOppTrainer.settledSprX = sprX;
            sOppTrainer.animTime = 0.0f;
            sOppTrainer.phaseTime = 0.0f;
            sOppTrainer.throwTime = 0.0f;
            sOppTrainer.fadeTime = 0.0f;
            sOppTrainer.animNonce++;
            sOppTrainer.posX = BDSP_OPP_HOME_X;
            sOppTrainer.posZ = BDSP_OPP_HOME_Z;
        }
        break;

    case BDSP_TRAINER_PHASE_ENTERING:
        if (enemySpr == NULL) {
            if (!enemyMonVisible) {
                sOppTrainer.phase = BDSP_TRAINER_PHASE_THROWING;
                sOppTrainer.animTime = 0.0f;
                sOppTrainer.throwTime = 0.0f;
                sOppTrainer.animNonce++;
            } else {
                sOppTrainer.phase = BDSP_TRAINER_PHASE_DONE;
            }
        } else {
            float slideFrac = ClampFloat((float)(192 - sprX) / 160.0f, 0.0f, 1.0f);
            sOppTrainer.posX = BDSP_OPP_HOME_X - slideFrac * 1.45f;
            sOppTrainer.posZ = BDSP_OPP_HOME_Z - slideFrac * 0.45f;
            sOppTrainer.animTime += BDSP_TRAINER_DT;
            sOppTrainer.phaseTime += BDSP_TRAINER_DT;
            if (sprX >= BDSP_OPP_SETTLE_X) {
                sOppTrainer.phase = BDSP_TRAINER_PHASE_STANDING;
                sOppTrainer.settledSprX = sprX;
                sOppTrainer.animTime = 0.0f;
                sOppTrainer.phaseTime = 0.0f;
                sOppTrainer.posX = BDSP_OPP_HOME_X;
                sOppTrainer.posZ = BDSP_OPP_HOME_Z;
            }
        }
        break;

    case BDSP_TRAINER_PHASE_STANDING:
        sOppTrainer.posX = BDSP_OPP_HOME_X;
        sOppTrainer.posZ = BDSP_OPP_HOME_Z;
        if (enemySpr == NULL || sprX >= BDSP_OPP_THROW_START_X || enemyMonVisible) {
            sOppTrainer.phase = BDSP_TRAINER_PHASE_THROWING;
            sOppTrainer.animTime = 0.0f;
            sOppTrainer.phaseTime = 0.0f;
            sOppTrainer.throwTime = 0.0f;
            sOppTrainer.animNonce++;
        } else {
            sOppTrainer.animTime += BDSP_TRAINER_DT;
            sOppTrainer.phaseTime += BDSP_TRAINER_DT;
        }
        break;

    case BDSP_TRAINER_PHASE_THROWING:
        sOppTrainer.posX = BDSP_OPP_HOME_X;
        sOppTrainer.posZ = BDSP_OPP_HOME_Z;
        sOppTrainer.throwTime += BDSP_TRAINER_DT;
        sOppTrainer.animTime = sOppTrainer.throwTime;
        if (sOppTrainer.throwTime >= BDSP_OPP_THROW_DUR
            || (enemyMonVisible && sOppTrainer.throwTime >= BDSP_OPP_THROW_MIN_ON_MON)) {
            sOppTrainer.phase = BDSP_TRAINER_PHASE_FADING;
            sOppTrainer.fadeTime = 0.0f;
        }
        break;

    case BDSP_TRAINER_PHASE_FADING:
        sOppTrainer.fadeTime += BDSP_TRAINER_DT;
        sOppTrainer.animTime += BDSP_TRAINER_DT;
        if (sOppTrainer.fadeTime >= BDSP_OPP_EXIT_DUR) {
            sOppTrainer.phase = BDSP_TRAINER_PHASE_DONE;
        }
        break;

    case BDSP_TRAINER_PHASE_DONE:
    default:
        break;
    }

    // Hide the 2D opponent trainer OBJ sprite ONLY while our 3D opponent trainer is active & ready,
    // and only restore a sprite pointer that WE hid.
    {
        BOOL hide2d = (sOppTrainer.phase == BDSP_TRAINER_PHASE_ENTERING
            || sOppTrainer.phase == BDSP_TRAINER_PHASE_STANDING
            || sOppTrainer.phase == BDSP_TRAINER_PHASE_THROWING
            || sOppTrainer.phase == BDSP_TRAINER_PHASE_FADING);
        SetOwnedSpriteHidden(&sOppTrainer.hidden2dSpr, enemySpr, hide2d);
    }

    if (sOppTrainer.phase == BDSP_TRAINER_PHASE_ENTERING
        || sOppTrainer.phase == BDSP_TRAINER_PHASE_STANDING
        || sOppTrainer.phase == BDSP_TRAINER_PHASE_THROWING
        || sOppTrainer.phase == BDSP_TRAINER_PHASE_FADING) {
        SIM_Battle3DActor *oa = &frame->actors[3];
        float alpha = 1.0f;
        float exitShift = 0.0f;
        int animState = SIM_BATTLE3D_TRANIM_WAIT;
        float animTime = sOppTrainer.animTime;

        if (sOppTrainer.phase == BDSP_TRAINER_PHASE_STANDING
            && sOppTrainer.phaseTime < BDSP_OPP_ADVENT_POSE_DUR) {
            animState = SIM_BATTLE3D_TRANIM_ADVENT;
            animTime = sOppTrainer.phaseTime;
        } else if (sOppTrainer.phase == BDSP_TRAINER_PHASE_THROWING
            || sOppTrainer.phase == BDSP_TRAINER_PHASE_FADING) {
            animState = SIM_BATTLE3D_TRANIM_THROW;
            animTime = sOppTrainer.animTime;
        }

        if (sOppTrainer.phase == BDSP_TRAINER_PHASE_FADING) {
            float u = ClampFloat(sOppTrainer.fadeTime / BDSP_OPP_EXIT_DUR, 0.0f, 1.0f);
            float sm = u * u * (3.0f - 2.0f * u);
            alpha = 1.0f - sm;
            exitShift = sm * 1.15f;
        }

        oa->visible = 1;
        oa->kind = SIM_BATTLE3D_ACTOR_OPPONENT_TRAINER;
        oa->trainerId = sOppTrainer.trainerModelId;
        oa->ballVariant = 0;
        oa->worldX = sOppTrainer.posX + exitShift * 0.85f;
        oa->worldY = BDSP_OPP_HOME_Y;
        oa->worldZ = sOppTrainer.posZ - exitShift * 0.70f;
        oa->yawDeg = sOppTrainer.yawDeg;
        oa->pitchDeg = 0.0f;
        oa->rollDeg = 0.0f;
        oa->scale = BDSP_OPP_SCALE;
        oa->alpha = alpha;
        oa->animState = animState;
        oa->animTime = animTime;
        oa->animNonce = sOppTrainer.animNonce;
        oa->attachActorIdx = 0;
        oa->attachBoneKind = 0;
        oa->attachOffset[0] = 0.0f;
        oa->attachOffset[1] = 0.0f;
        oa->attachOffset[2] = 0.0f;
    }
}

void BattleBdspTrainer_Update(BattleSystem *battleSys, SIM_Battle3DFrame *frame)
{
    int playerSlot;
    int playerSlot2;
    u32 battleType;
    BattlerData *battlerData;
    ManagedSprite *trainerSpr;
    u32 gender;
    int trainerKind;
    BOOL hasTrainer3d;
    BOOL hasBall3d;
    BOOL monVisible = FALSE;
    BOOL mon2Visible = FALSE;
    BOOL hasBallRot = FALSE;
    BOOL ballAttachedToHand = FALSE;
    s16 sprX = 64;
    s16 sprY = 128;
    float oppX = 2.35f;
    float oppZ = -2.15f;
    float palmOffset[3];
    float liveSocket[3];
    int slots[2];
    BOOL slotVis[2];
    int si;

    if (battleSys == NULL || frame == NULL || !SIM_Battle3D_ModelsEnabled()) {
        return;
    }

    // Opus B1: Safari Zone, Pal Park, and Catch Tutorial keep the player's 2D trainer
    // for the whole battle (no Pokemon send-out); never hide it or run a 3D throw.
    battleType = BattleSystem_GetBattleType(battleSys);
    if (battleType & (BATTLE_TYPE_SAFARI | BATTLE_TYPE_PAL_PARK | BATTLE_TYPE_CATCH_TUTORIAL)) {
        return;
    }

    // Prefetch opponent trainer early, even before the 3D stage has faded in (frame->alpha <= 0.01).
    BattleBdspTrainer_Prefetch(battleSys);

    if (frame->alpha <= 0.01f) {
        int pSlot = FindPlayerSlot(battleSys);
        int pSlot2 = FindPlayerSlot2(battleSys);
        int eSlot = FindEnemySlot(battleSys);
        if (pSlot >= 0) {
            BattlerData *pBd = BattleSystem_GetBattlerData(battleSys, pSlot);
            SetOwnedSpriteHidden(&sTrainer.hidden2dSpr, (pBd != NULL) ? pBd->managedSprite : NULL, FALSE);
            RestoreOwnedBallSprite(battleSys, pSlot, 0);
        }
        if (pSlot2 >= 0) {
            RestoreOwnedBallSprite(battleSys, pSlot2, 1);
        }
        if (eSlot >= 0) {
            BattlerData *eBd = BattleSystem_GetBattlerData(battleSys, eSlot);
            SetOwnedSpriteHidden(&sOppTrainer.hidden2dSpr, (eBd != NULL) ? eBd->managedSprite : NULL, FALSE);
        }
        return;
    }

    UpdateOpponentTrainer(battleSys, frame, battleType);

    playerSlot = FindPlayerSlot(battleSys);
    if (playerSlot < 0) {
        return;
    }
    playerSlot2 = FindPlayerSlot2(battleSys);
    // Opus B9: In 2vs2 multi/AI-partner doubles, slot 2 belongs to the partner trainer
    // (who has their own send-out); never let 3D Lucas/Dawn throw the partner's ball.
    if (playerSlot2 >= 0 && (battleType & BATTLE_TYPE_2vs2)) {
        playerSlot2 = -1;
    }

    gender = BattleSystem_GetTrainerGender(battleSys, playerSlot);
    trainerKind = (gender == GENDER_FEMALE)
        ? SIM_BATTLE3D_ACTOR_TRAINER_DAWN
        : SIM_BATTLE3D_ACTOR_TRAINER_LUCAS;

    hasTrainer3d = SIM_Battle3D_HasActorLoaded(trainerKind);
    if (!hasTrainer3d) {
        BattlerData *bdRestore = BattleSystem_GetBattlerData(battleSys, playerSlot);
        SetOwnedSpriteHidden(&sTrainer.hidden2dSpr, (bdRestore != NULL) ? bdRestore->managedSprite : NULL, FALSE);
        RestoreOwnedBallSprite(battleSys, playerSlot, 0);
        if (playerSlot2 >= 0) {
            RestoreOwnedBallSprite(battleSys, playerSlot2, 1);
        }
        return;
    }

    hasBall3d = SIM_Battle3D_HasActorLoaded(SIM_BATTLE3D_ACTOR_POKEBALL);
    GetTrainerPalmOffset(trainerKind, palmOffset);

    battlerData = BattleSystem_GetBattlerData(battleSys, playerSlot);
    trainerSpr = (battlerData != NULL) ? battlerData->managedSprite : NULL;
    hasBallRot = (battlerData != NULL && battlerData->ballRotation != NULL) ? TRUE : FALSE;

    if (playerSlot < SIM_BATTLE3D_MAX_BATTLERS && frame->battlers[playerSlot].visible) {
        monVisible = TRUE;
    }
    if (playerSlot2 >= 0 && playerSlot2 < SIM_BATTLE3D_MAX_BATTLERS && frame->battlers[playerSlot2].visible) {
        mon2Visible = TRUE;
    }

    if (trainerSpr != NULL) {
        ManagedSprite_GetPositionXY(trainerSpr, &sprX, &sprY);
    }

    // Suppress the 2D OAM send-out ball sprite(s) only while our intro 3D Poke Ball(s) own the send-out.
    if (hasBall3d && sTrainer.phase != BDSP_TRAINER_PHASE_DONE) {
        SuppressLegacyBallSprite(battleSys, playerSlot, 0);
        if (playerSlot2 >= 0) {
            SuppressLegacyBallSprite(battleSys, playerSlot2, 1);
        }
    } else {
        RestoreOwnedBallSprite(battleSys, playerSlot, 0);
        if (playerSlot2 >= 0) {
            RestoreOwnedBallSprite(battleSys, playerSlot2, 1);
        }
    }

    // Track live evaluated throwing palm socket world position whenever fresh for current nonce.
    if (SIM_Battle3D_GetActorSocketWorldPos(0, BDSP_THROW_HAND_BONE, sTrainer.animNonce,
            0.0f, palmOffset, liveSocket)) {
        sTrainer.lastHandPos[0] = liveSocket[0];
        sTrainer.lastHandPos[1] = liveSocket[1];
        sTrainer.lastHandPos[2] = liveSocket[2];
        sTrainer.hasHandPos = TRUE;
    }

    sTrainer.trainerKind = trainerKind;
    sTrainer.playerSlot = playerSlot;
    sTrainer.playerSlot2 = playerSlot2;
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
                BeginThrow(battleSys, frame, playerSlot, playerSlot2);
            } else {
                sTrainer.phase = BDSP_TRAINER_PHASE_DONE;
            }
        } else {
            float slideFrac = ClampFloat((float)(sprX - 64) / 160.0f, 0.0f, 1.0f);
            sTrainer.trainerX = BDSP_TRAINER_HOME_X - slideFrac * 0.55f;
            sTrainer.trainerZ = BDSP_TRAINER_HOME_Z + slideFrac * 0.35f;
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
                BeginThrow(battleSys, frame, playerSlot, playerSlot2);
            } else {
                sTrainer.phase = BDSP_TRAINER_PHASE_DONE;
            }
        } else if (sprX < BDSP_TRAINER_THROW_X
            || ManagedSprite_IsAnimated(trainerSpr)
            || ManagedSprite_GetAnimationFrame(trainerSpr) > 0) {
            BeginThrow(battleSys, frame, playerSlot, playerSlot2);
        } else {
            sTrainer.animTime += BDSP_TRAINER_DT;
            sTrainer.phaseTime += BDSP_TRAINER_DT;
        }
        break;

    case BDSP_TRAINER_PHASE_THROWING:
        sTrainer.throwTicks++;
        sTrainer.throwTime = (float)sTrainer.throwTicks * BDSP_TRAINER_DT;
        sTrainer.animTime = sTrainer.throwTime;

        // Wind-up -> exact tick 21 hand release -> parabolic flight to landing spot -> burst VFX
        if (!sTrainer.ballDone) {
            if (!sTrainer.ballReleased) {
                if (sTrainer.throwTicks >= BDSP_BALL_RELEASE_TICK) {
                    ReleaseBallFromHand(palmOffset);
                } else if (monVisible) {
                    // Safety fallback if mon appeared before release tick.
                    sTrainer.ballReleased = TRUE;
                    sTrainer.ballActive = FALSE;
                    sTrainer.ballDone = TRUE;
                    TriggerBurstAndMaterialize();
                }
            } else if (sTrainer.ballActive) {
                // If mon appeared earlier than nominal landing, retime remaining arc to reach
                // the landing spot cleanly within a few frames rather than popping mid-air!
                if (monVisible && (sTrainer.flightDurTicks - sTrainer.flightTicks) > BDSP_BALL_EARLY_FINISH_TICKS) {
                    sTrainer.flightDurTicks = sTrainer.flightTicks + BDSP_BALL_EARLY_FINISH_TICKS;
                }
                if (sTrainer.flightTicks >= sTrainer.flightDurTicks) {
                    sTrainer.ballActive = FALSE;
                    sTrainer.ballDone = TRUE;
                    TriggerBurstAndMaterialize();
                }
            }
        }

        // Hold Lucas/Dawn solid through the entire follow-through swing before smooth exit!
        if (sTrainer.ballDone && sTrainer.throwTime >= BDSP_TRAINER_FOLLOWTHROUGH_END) {
            sTrainer.phase = BDSP_TRAINER_PHASE_FADING;
            sTrainer.fadeTime = 0.0f;
        } else if (sTrainer.throwTime >= BDSP_TRAINER_FOLLOWTHROUGH_END + 0.55f) {
            sTrainer.phase = BDSP_TRAINER_PHASE_FADING;
            sTrainer.fadeTime = 0.0f;
            sTrainer.ballActive = FALSE;
            sTrainer.ballDone = TRUE;
        }
        break;

    case BDSP_TRAINER_PHASE_FADING:
        sTrainer.fadeTime += BDSP_TRAINER_DT;
        sTrainer.animTime += BDSP_TRAINER_DT;
        if (sTrainer.fadeTime >= BDSP_TRAINER_EXIT_DUR) {
            sTrainer.phase = BDSP_TRAINER_PHASE_DONE;
        }
        break;

    case BDSP_TRAINER_PHASE_DONE:
    default:
        break;
    }

    // Opus B1 / Codex P2-4: Only hide the 2D player trainer back OBJ while 3D Lucas/Dawn is actively
    // rendered (ENTERING/STANDING/THROWING/FADING), and only restore a sprite pointer WE hid.
    {
        BOOL hide2d = (sTrainer.phase == BDSP_TRAINER_PHASE_ENTERING
            || sTrainer.phase == BDSP_TRAINER_PHASE_STANDING
            || sTrainer.phase == BDSP_TRAINER_PHASE_THROWING
            || sTrainer.phase == BDSP_TRAINER_PHASE_FADING);
        SetOwnedSpriteHidden(&sTrainer.hidden2dSpr, trainerSpr, hide2d);
    }

    // Advance 3D Poke Ball open light-burst VFX independently so it always completes cleanly.
    if (sTrainer.burstActive) {
        float p = ClampFloat(sTrainer.burstTime / BDSP_BURST_DUR, 0.0f, 1.0f);
        float bx = (playerSlot2 >= 0) ? 0.5f * (sTrainer.targetMonX + sTrainer.targetMon2X) : sTrainer.targetMonX;
        float bz = (playerSlot2 >= 0) ? 0.5f * (sTrainer.targetMonZ + sTrainer.targetMon2Z) : sTrainer.targetMonZ;
        frame->burst.active = 1;
        frame->burst.worldX = bx;
        frame->burst.worldY = BDSP_BURST_CENTER_Y;
        frame->burst.worldZ = bz;
        frame->burst.progress = p;
        frame->burst.radius = (playerSlot2 >= 0) ? (BDSP_BURST_RADIUS * 1.25f) : BDSP_BURST_RADIUS;
        frame->burst.color[0] = 1.00f;
        frame->burst.color[1] = 0.62f;
        frame->burst.color[2] = 0.66f;

        sTrainer.burstTime += BDSP_TRAINER_DT;
        if (sTrainer.burstTime >= BDSP_BURST_DUR) {
            sTrainer.burstActive = FALSE;
        }
    }

    // Smooth Pokemon scale-in (0.08 -> 1.07 -> 1.0) & warm-white/crimson flashAmount fade (1 -> 0)
    // for player slot 1 (and slot 2 in doubles!).
    slots[0] = playerSlot;
    slots[1] = playerSlot2;
    slotVis[0] = monVisible;
    slotVis[1] = mon2Visible;
    for (si = 0; si < 2; si++) {
        int sl = slots[si];
        if (sl < 0 || sl >= SIM_BATTLE3D_MAX_BATTLERS) {
            continue;
        }
        if (sTrainer.matArmed[si] && !sTrainer.matActive[si] && !sTrainer.matDone[si] && slotVis[si]) {
            sTrainer.matActive[si] = TRUE;
            sTrainer.matTime[si] = 0.0f;
            if (si == 0 && !sTrainer.burstActive && sTrainer.burstTime >= BDSP_BURST_DUR * 0.75f) {
                sTrainer.burstActive = TRUE;
                sTrainer.burstTime = 0.0f;
            }
        }
        if (sTrainer.matActive[si] && slotVis[si]) {
            float u = ClampFloat(sTrainer.matTime[si] / BDSP_MAT_DUR, 0.0f, 1.0f);
            float inv = 1.0f - u;
            float easeOut = 1.0f - inv * inv * inv;
            float overshoot = 0.09f * sinf(u * 3.14159265f) * (1.0f - u * 0.45f);
            float matScale = (u >= 0.999f) ? 1.0f : (0.08f + 0.92f * easeOut + overshoot);
            float flash = (u >= 0.999f) ? 0.0f : powf(inv, 1.55f);
            int btype = BattleSystem_GetBattlerType(battleSys, sl);
            float fullScale = ComputeNormalizedPlayerScale(battleSys, sl, btype);

            frame->battlers[sl].modelScale = fullScale * matScale;
            frame->battlers[sl].flashAmount = ClampFloat(flash, 0.0f, 1.0f);

            sTrainer.matTime[si] += BDSP_TRAINER_DT;
            if (sTrainer.matTime[si] >= BDSP_MAT_DUR) {
                sTrainer.matActive[si] = FALSE;
                sTrainer.matDone[si] = TRUE;
            }
        }
    }

    // Populate frame->actors[0] (3D Lucas / Dawn)
    if (sTrainer.phase == BDSP_TRAINER_PHASE_ENTERING
        || sTrainer.phase == BDSP_TRAINER_PHASE_STANDING
        || sTrainer.phase == BDSP_TRAINER_PHASE_THROWING
        || sTrainer.phase == BDSP_TRAINER_PHASE_FADING) {
        SIM_Battle3DActor *ta = &frame->actors[0];
        float alpha = 1.0f;
        float exitShift = 0.0f;

        if (sTrainer.phase == BDSP_TRAINER_PHASE_FADING) {
            float u = ClampFloat(sTrainer.fadeTime / BDSP_TRAINER_EXIT_DUR, 0.0f, 1.0f);
            float sm = u * u * (3.0f - 2.0f * u);
            alpha = 1.0f - sm;
            exitShift = sm * 1.15f;
        }

        ta->visible = 1;
        ta->kind = sTrainer.trainerKind;
        ta->worldX = sTrainer.trainerX - exitShift * 0.85f;
        ta->worldY = BDSP_TRAINER_HOME_Y;
        ta->worldZ = sTrainer.trainerZ + exitShift * 0.70f;
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
        ta->attachActorIdx = 0;
        ta->attachBoneKind = 0;
        ta->attachOffset[0] = 0.0f;
        ta->attachOffset[1] = 0.0f;
        ta->attachOffset[2] = 0.0f;
    }

    // Populate frame->actors[1] (and actors[2] in doubles) for 3D Poke Ball(s):
    // Locked directly to trainer's LHand via per-rig LItem1 palm offset during wind-up,
    // then detaches at exact tick 21 with u=0.0 from the exact transformed palm point.
    ballAttachedToHand = (sTrainer.phase == BDSP_TRAINER_PHASE_ENTERING
        || sTrainer.phase == BDSP_TRAINER_PHASE_STANDING
        || (sTrainer.phase == BDSP_TRAINER_PHASE_THROWING && !sTrainer.ballReleased && !sTrainer.ballDone));

    if (hasBall3d && ballAttachedToHand) {
        SIM_Battle3DActor *ba = &frame->actors[1];
        ba->visible = 1;
        ba->kind = SIM_BATTLE3D_ACTOR_POKEBALL;
        ba->worldX = sTrainer.hasHandPos ? sTrainer.lastHandPos[0] : sTrainer.trainerX;
        ba->worldY = sTrainer.hasHandPos ? sTrainer.lastHandPos[1] : 1.15f;
        ba->worldZ = sTrainer.hasHandPos ? sTrainer.lastHandPos[2] : sTrainer.trainerZ;
        ba->yawDeg = sTrainer.trainerYawDeg;
        ba->pitchDeg = 0.0f;
        ba->rollDeg = 0.0f;
        ba->scale = BDSP_BALL_SCALE_HELD;
        ba->alpha = 1.0f;
        ba->animState = 0;
        ba->animTime = 0.0f;
        ba->animNonce = sTrainer.animNonce;
        ba->attachActorIdx = 0;
        ba->attachBoneKind = BDSP_THROW_HAND_BONE;
        ba->attachOffset[0] = palmOffset[0];
        ba->attachOffset[1] = palmOffset[1];
        ba->attachOffset[2] = palmOffset[2];
    } else if (hasBall3d && sTrainer.ballActive) {
        float denom = (sTrainer.flightDurTicks > 0) ? (float)sTrainer.flightDurTicks : (float)BDSP_BALL_FLIGHT_TICKS;
        float u = ClampFloat((float)sTrainer.flightTicks / denom, 0.0f, 1.0f);
        float scale = BDSP_BALL_SCALE_HELD + (BDSP_BALL_SCALE_FLIGHT - BDSP_BALL_SCALE_HELD) * ClampFloat(u * 2.5f, 0.0f, 1.0f);
        SIM_Battle3DActor *ba = &frame->actors[1];

        ba->visible = 1;
        ba->kind = SIM_BATTLE3D_ACTOR_POKEBALL;
        ba->worldX = sTrainer.ballStartX + (sTrainer.targetMonX - sTrainer.ballStartX) * u;
        ba->worldY = sTrainer.ballStartY + (0.32f - sTrainer.ballStartY) * u
            + 4.0f * BDSP_BALL_ARC_PEAK * u * (1.0f - u);
        ba->worldZ = sTrainer.ballStartZ + (sTrainer.targetMonZ - sTrainer.ballStartZ) * u;
        ba->yawDeg = sTrainer.trainerYawDeg;
        ba->pitchDeg = u * 720.0f;
        ba->rollDeg = u * 210.0f;
        ba->scale = scale;
        ba->alpha = 1.0f;
        ba->animState = 0;
        ba->animTime = 0.0f;
        ba->animNonce = sTrainer.animNonce;
        ba->attachActorIdx = 0;
        ba->attachBoneKind = 0;
        ba->attachOffset[0] = 0.0f;
        ba->attachOffset[1] = 0.0f;
        ba->attachOffset[2] = 0.0f;

        if (playerSlot2 >= 0) {
            SIM_Battle3DActor *ba2 = &frame->actors[2];
            ba2->visible = 1;
            ba2->kind = SIM_BATTLE3D_ACTOR_POKEBALL;
            ba2->worldX = sTrainer.ballStartX + (sTrainer.targetMon2X - sTrainer.ballStartX) * u;
            ba2->worldY = sTrainer.ballStartY + (0.32f - sTrainer.ballStartY) * u
                + 4.0f * (BDSP_BALL_ARC_PEAK * 0.92f) * u * (1.0f - u);
            ba2->worldZ = sTrainer.ballStartZ + (sTrainer.targetMon2Z - sTrainer.ballStartZ) * u;
            ba2->yawDeg = sTrainer.trainerYawDeg;
            ba2->pitchDeg = u * 720.0f;
            ba2->rollDeg = -u * 210.0f;
            ba2->scale = scale;
            ba2->alpha = 1.0f;
            ba2->animState = 0;
            ba2->animTime = 0.0f;
            ba2->animNonce = sTrainer.animNonce;
            ba2->attachActorIdx = 0;
            ba2->attachBoneKind = 0;
            ba2->attachOffset[0] = 0.0f;
            ba2->attachOffset[1] = 0.0f;
            ba2->attachOffset[2] = 0.0f;
        }

        sTrainer.flightTicks++;
    }

#ifdef SDK_PORT
    TrainerDumpMaybeLog(frame, sprX, trainerSpr != NULL, hasBallRot, monVisible);
#endif
    sTrainer.tickCount++;
}
