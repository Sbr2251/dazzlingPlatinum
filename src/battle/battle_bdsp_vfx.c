#include "battle/battle_bdsp_vfx.h"

#include <math.h>
#include <string.h>

#include "constants/battle.h"
#include "constants/battle/condition.h"
#include "constants/battle/moves.h"
#include "constants/moves.h"
#include "generated/move_attributes.h"
#include "generated/move_classes.h"
#include "generated/move_ranges.h"
#include "generated/pokemon_types.h"

#include "battle/battle_bdsp_capture.h"
#include "battle/battle_context.h"
#include "battle/battle_system.h"
#include "move_table.h"

#define BDSP_VFX_DT          (1.0f / 60.0f)
#define BDSP_VFX_PI          3.14159265358979323846f
#define BDSP_VFX_POOL_SIZE   8
#define BDSP_VFX_PENDING_MAX 4

#define BDSP_LUNGE_FRAC      0.22f
#define BDSP_LUNGE_FWD_DUR   0.28f
#define BDSP_LUNGE_HOLD_DUR  0.10f
#define BDSP_LUNGE_BACK_DUR  0.30f
#define BDSP_LUNGE_TOTAL_DUR (BDSP_LUNGE_FWD_DUR + BDSP_LUNGE_HOLD_DUR + BDSP_LUNGE_BACK_DUR)

#define BDSP_KNOCK_OUT_DUR   0.07f
#define BDSP_KNOCK_BACK_DUR  0.21f
#define BDSP_KNOCK_TOTAL_DUR (BDSP_KNOCK_OUT_DUR + BDSP_KNOCK_BACK_DUR)
#define BDSP_KNOCK_DIST      0.34f

#define BDSP_HIT_FLASH_PEAK  0.85f
#define BDSP_HIT_FLASH_DUR   0.28f

// Full 19-type BDSP elemental color palette matching generated/pokemon_types.txt.
static const float sTypeColors[NUM_POKEMON_TYPES][3] = {
    [TYPE_NORMAL]   = { 0.96f, 0.93f, 0.84f }, // warm-white
    [TYPE_FIGHTING] = { 0.92f, 0.24f, 0.20f }, // crimson
    [TYPE_FLYING]   = { 0.72f, 0.88f, 1.00f }, // sky-white
    [TYPE_POISON]   = { 0.72f, 0.28f, 0.86f }, // violet
    [TYPE_GROUND]   = { 0.88f, 0.68f, 0.32f }, // ochre
    [TYPE_ROCK]     = { 0.78f, 0.62f, 0.36f }, // bronze
    [TYPE_BUG]      = { 0.64f, 0.86f, 0.20f }, // lime
    [TYPE_GHOST]    = { 0.48f, 0.34f, 0.78f }, // indigo
    [TYPE_STEEL]    = { 0.72f, 0.80f, 0.90f }, // silver-blue
    [TYPE_MYSTERY]  = { 0.45f, 0.78f, 0.72f }, // mystic teal
    [TYPE_FIRE]     = { 1.00f, 0.48f, 0.12f }, // orange-gold
    [TYPE_WATER]    = { 0.20f, 0.66f, 1.00f }, // cyan-blue
    [TYPE_GRASS]    = { 0.28f, 0.86f, 0.36f }, // emerald
    [TYPE_ELECTRIC] = { 1.00f, 0.88f, 0.16f }, // bright yellow
    [TYPE_PSYCHIC]  = { 1.00f, 0.34f, 0.68f }, // magenta
    [TYPE_ICE]      = { 0.56f, 0.92f, 1.00f }, // frost-blue
    [TYPE_DRAGON]   = { 0.46f, 0.38f, 1.00f }, // royal-violet
    [TYPE_DARK]     = { 0.38f, 0.26f, 0.46f }, // obsidian-purple
    [TYPE_FAIRY]    = { 1.00f, 0.60f, 0.84f }, // fairy pink
};

typedef struct BdspPendingAttack {
    int attacker;
    int defender;
    u16 move;
    u32 moveClass;
    int moveType;
    u32 moveRange;
    u32 moveFlags;
} BdspPendingAttack;

typedef struct BdspVfxItem {
    BOOL active;
    int kind;
    int moveType;
    int targetBattler; // -1 if none
    int trackBattler;  // -1 if static world coords, else follows battler pos
    float trackYOffset;
    float delay;
    float elapsed;
    float duration;
    float src[3];
    float dst[3];
    float color[3];
    float scale;
} BdspVfxItem;

typedef struct BdspBattlerVfxState {
    BOOL lungeActive;
    BOOL isKnockback;
    float lungeTime;
    float lungeVec[3];

    BOOL hitFlashActive;
    float hitFlashTime;

    BOOL pendingHit;
    BOOL pendingShiny;

    BOOL sparkled;
    int sparkledSpecies;
    int sparkledPartySlot;

    int lastAttacker;
    int lastMoveType;
    float sinceImpactSec;
} BdspBattlerVfxState;

typedef struct BdspVfxSystem {
    BdspBattlerVfxState battlers[SIM_BATTLE3D_MAX_BATTLERS];
    BdspVfxItem pool[BDSP_VFX_POOL_SIZE];
    BdspPendingAttack pendingAttacks[BDSP_VFX_PENDING_MAX];
    int pendingAttackCount;
} BdspVfxSystem;

static BdspVfxSystem sVfx;

static void GetTypeColor(int moveType, float outColor[3])
{
    if (moveType < 0 || moveType >= NUM_POKEMON_TYPES) {
        moveType = TYPE_NORMAL;
    }
    outColor[0] = sTypeColors[moveType][0];
    outColor[1] = sTypeColors[moveType][1];
    outColor[2] = sTypeColors[moveType][2];
}

static int MapStatusCondition(u32 status)
{
    if (status & MON_CONDITION_ANY_POISON) {
        return 1; // PSN / TOX
    }
    if (status & MON_CONDITION_BURN) {
        return 2; // BRN
    }
    if (status & MON_CONDITION_PARALYSIS) {
        return 3; // PAR
    }
    if (status & MON_CONDITION_SLEEP) {
        return 4; // SLP
    }
    if (status & MON_CONDITION_FREEZE) {
        return 5; // FRZ
    }
    return 0;
}

static BOOL IsSelfOrAllyRange(u32 range)
{
    switch (range) {
    case RANGE_USER:
    case RANGE_USER_SIDE:
    case RANGE_FIELD:
    case RANGE_ALLY:
    case RANGE_USER_OR_ALLY:
    case RANGE_ALL:
        return TRUE;
    default:
        return FALSE;
    }
}

static int AllocVfxSlot(void)
{
    int i;
    int oldestIdx = 0;
    float bestProgress = -1.0f;

    for (i = 0; i < BDSP_VFX_POOL_SIZE; i++) {
        if (!sVfx.pool[i].active) {
            return i;
        }
    }

    // Pool full: evict the furthest-along non-shiny slot.
    for (i = 0; i < BDSP_VFX_POOL_SIZE; i++) {
        float prog = (sVfx.pool[i].duration > 0.001f)
            ? (sVfx.pool[i].elapsed / sVfx.pool[i].duration)
            : 1.0f;
        if (sVfx.pool[i].kind == SIM_BATTLE3D_VFX_SHINY_SPARKLE) {
            prog -= 2.0f;
        }
        if (prog > bestProgress) {
            bestProgress = prog;
            oldestIdx = i;
        }
    }
    return oldestIdx;
}

static void SpawnVfx(int kind, int moveType, int targetBattler, int trackBattler, float trackYOffset,
                     float delay, float duration, const float src[3], const float dst[3],
                     const float color[3], float scale)
{
    int idx = AllocVfxSlot();
    BdspVfxItem *it = &sVfx.pool[idx];

    if (kind == SIM_BATTLE3D_VFX_IMPACT && targetBattler >= 0 && targetBattler < SIM_BATTLE3D_MAX_BATTLERS) {
        sVfx.battlers[targetBattler].sinceImpactSec = 0.0f;
    }
    memset(it, 0, sizeof(*it));
    it->active = TRUE;
    it->kind = kind;
    it->moveType = moveType;
    it->targetBattler = targetBattler;
    it->trackBattler = trackBattler;
    it->trackYOffset = trackYOffset;
    it->delay = delay;
    it->elapsed = 0.0f;
    it->duration = (duration > BDSP_VFX_DT) ? duration : BDSP_VFX_DT;
    it->src[0] = src[0];
    it->src[1] = src[1];
    it->src[2] = src[2];
    it->dst[0] = dst[0];
    it->dst[1] = dst[1];
    it->dst[2] = dst[2];
    it->color[0] = color[0];
    it->color[1] = color[1];
    it->color[2] = color[2];
    it->scale = (scale > 0.0f) ? scale : 1.0f;
}

static BOOL HasRecentImpactForBattler(int battler)
{
    int i;
    for (i = 0; i < BDSP_VFX_POOL_SIZE; i++) {
        const BdspVfxItem *it = &sVfx.pool[i];
        if (!it->active || it->kind != SIM_BATTLE3D_VFX_IMPACT) {
            continue;
        }
        if (it->targetBattler == battler) {
            if (it->delay <= 0.12f && it->elapsed < it->duration * 0.65f) {
                return TRUE;
            }
        }
    }
    return FALSE;
}

static int ResolveDefender(const SIM_Battle3DFrame *frame, const BattleContext *ctx,
                           int maxBattlers, int attacker, int hintDefender)
{
    int i;

    // Respect explicit self-targets (e.g. Focus Punch tightening focus, Swords Dance, Recover).
    if (hintDefender == attacker) {
        return attacker;
    }

    // Prefer the explicit command defender (MoveAnimation.defender) when valid and visible.
    if (hintDefender >= 0 && hintDefender < maxBattlers
        && frame->battlers[hintDefender].visible) {
        return hintDefender;
    }

    if (ctx != NULL && ctx->attacker == attacker
        && ctx->defender >= 0 && ctx->defender < maxBattlers
        && ctx->defender != attacker && frame->battlers[ctx->defender].visible) {
        return ctx->defender;
    }

    for (i = 0; i < maxBattlers; i++) {
        if (i != attacker && frame->battlers[i].visible
            && frame->battlers[i].isPlayer != frame->battlers[attacker].isPlayer) {
            return i;
        }
    }

    if (hintDefender >= 0 && hintDefender < SIM_BATTLE3D_MAX_BATTLERS) {
        return hintDefender;
    }
    return attacker ^ 1;
}

static void ProcessAttack(const SIM_Battle3DFrame *frame, const BattleContext *ctx,
                          int maxBattlers, const BdspPendingAttack *pa)
{
    int attacker = pa->attacker;
    int defender;
    const SIM_Battle3DBattler *atkB;
    const SIM_Battle3DBattler *defB;
    float color[3];
    float src[3];
    float dst[3];

    if (attacker < 0 || attacker >= maxBattlers) {
        return;
    }

    defender = ResolveDefender(frame, ctx, maxBattlers, attacker, pa->defender);
    if (defender < 0 || defender >= SIM_BATTLE3D_MAX_BATTLERS) {
        return;
    }

    atkB = &frame->battlers[attacker];
    defB = &frame->battlers[defender];
    GetTypeColor(pa->moveType, color);

    // Explicit self-targeted cue (e.g. Focus Punch tightening focus or self-buff):
    // play a rising self-aura on the attacker and never invent an enemy lunge.
    if (defender == attacker) {
        float pos[3] = { atkB->worldX, atkB->worldY, atkB->worldZ };
        SpawnVfx(SIM_BATTLE3D_VFX_STAT_UP, pa->moveType, attacker, attacker, 0.0f,
                 0.0f, 0.80f, pos, pos, color, 1.10f);
        return;
    }

    src[0] = atkB->worldX;
    src[1] = atkB->worldY + 0.90f;
    src[2] = atkB->worldZ;

    dst[0] = defB->worldX;
    dst[1] = defB->worldY + 0.80f;
    dst[2] = defB->worldZ;

    if (pa->moveClass != CLASS_STATUS) {
        sVfx.battlers[defender].lastAttacker = attacker;
        sVfx.battlers[defender].lastMoveType = pa->moveType;
        if (pa->moveRange == RANGE_ADJACENT_OPPONENTS || pa->moveRange == RANGE_ALL_ADJACENT) {
            int j;
            for (j = 0; j < maxBattlers; j++) {
                if (j == attacker || !frame->battlers[j].visible) {
                    continue;
                }
                if (pa->moveRange == RANGE_ADJACENT_OPPONENTS
                    && frame->battlers[j].isPlayer == atkB->isPlayer) {
                    continue;
                }
                sVfx.battlers[j].lastAttacker = attacker;
                sVfx.battlers[j].lastMoveType = pa->moveType;
            }
        }
    }

    if (pa->moveClass == CLASS_PHYSICAL && (pa->moveFlags & MOVE_FLAG_MAKES_CONTACT)) {
        // Contact physical move: toned lunge (~22% of gap so it blends cleanly with 2D dxPx) + impact.
        BdspBattlerVfxState *abs = &sVfx.battlers[attacker];
        abs->lungeActive = TRUE;
        abs->isKnockback = FALSE;
        abs->lungeTime = 0.0f;
        abs->lungeVec[0] = (defB->worldX - atkB->worldX) * BDSP_LUNGE_FRAC;
        abs->lungeVec[1] = 0.0f;
        abs->lungeVec[2] = (defB->worldZ - atkB->worldZ) * BDSP_LUNGE_FRAC;

        // Impact burst timed to lunge arrival at the defender.
        SpawnVfx(SIM_BATTLE3D_VFX_IMPACT, pa->moveType, defender, -1, 0.0f,
                 0.24f, 0.48f, src, dst, color, 1.15f);
    } else if (pa->moveClass == CLASS_PHYSICAL
               && (pa->moveRange == RANGE_ALL_ADJACENT || pa->moveRange == RANGE_ADJACENT_OPPONENTS)) {
        // Non-contact spread physical moves (Earthquake, Rock Slide): impact bursts on targets, no lunge.
        int j;
        BOOL spawnedAny = FALSE;
        for (j = 0; j < maxBattlers; j++) {
            if (j == attacker || !frame->battlers[j].visible) {
                continue;
            }
            if (pa->moveRange == RANGE_ADJACENT_OPPONENTS
                && frame->battlers[j].isPlayer == atkB->isPlayer) {
                continue;
            }
            float tpos[3] = {
                frame->battlers[j].worldX,
                frame->battlers[j].worldY + 0.80f,
                frame->battlers[j].worldZ
            };
            SpawnVfx(SIM_BATTLE3D_VFX_IMPACT, pa->moveType, j, -1, 0.0f,
                     0.18f, 0.48f, tpos, tpos, color, 1.25f);
            spawnedAny = TRUE;
        }
        if (!spawnedAny) {
            SpawnVfx(SIM_BATTLE3D_VFX_IMPACT, pa->moveType, defender, -1, 0.0f,
                     0.18f, 0.48f, dst, dst, color, 1.25f);
        }
    } else if (pa->moveClass == CLASS_PHYSICAL || pa->moveClass == CLASS_SPECIAL) {
        // Non-contact targeted physical moves (Stone Edge, Bullet Seed, etc.) and special moves:
        // elemental projectile orb/bolt flying src -> dst + explosion on arrival (no lunge).
        SpawnVfx(SIM_BATTLE3D_VFX_PROJECTILE, pa->moveType, defender, -1, 0.0f,
                 0.10f, 1.45f, src, dst, color, 1.22f);
        SpawnVfx(SIM_BATTLE3D_VFX_IMPACT, pa->moveType, defender, -1, 0.0f,
                 1.32f, 0.72f, src, dst, color, 1.32f);
    } else {
        // CLASS_STATUS: rising aura rings on self/ally recipient or falling rings on opponent.
        BOOL sameSide = (defB->isPlayer == atkB->isPlayer);
        if (IsSelfOrAllyRange(pa->moveRange) || sameSide) {
            int recipient = (sameSide && defender != attacker) ? defender : attacker;
            const SIM_Battle3DBattler *recB = &frame->battlers[recipient];
            float pos[3] = { recB->worldX, recB->worldY, recB->worldZ };
            SpawnVfx(SIM_BATTLE3D_VFX_STAT_UP, pa->moveType, recipient, recipient, 0.0f,
                     0.0f, 0.80f, pos, pos, color, 1.10f);
        } else {
            float pos[3] = { defB->worldX, defB->worldY, defB->worldZ };
            SpawnVfx(SIM_BATTLE3D_VFX_STAT_DOWN, pa->moveType, defender, defender, 0.0f,
                     0.0f, 0.80f, pos, pos, color, 1.10f);
        }
    }
}

static void ProcessHit(const SIM_Battle3DFrame *frame, int maxBattlers, int defender)
{
    BdspBattlerVfxState *bs;
    const SIM_Battle3DBattler *defB;
    int attacker;
    float dx, dz, len;

    if (defender < 0 || defender >= maxBattlers) {
        return;
    }

    bs = &sVfx.battlers[defender];
    defB = &frame->battlers[defender];

    // Crisp white hit-flash (0.85 -> 0.0 over 0.28s).
    bs->hitFlashActive = TRUE;
    bs->hitFlashTime = 0.0f;

    // Brief crisp knockback jolt away from the attacker.
    attacker = bs->lastAttacker;
    if (attacker < 0 || attacker >= maxBattlers || attacker == defender) {
        attacker = defender ^ 1;
    }
    if (attacker >= 0 && attacker < maxBattlers && attacker != defender) {
        dx = defB->worldX - frame->battlers[attacker].worldX;
        dz = defB->worldZ - frame->battlers[attacker].worldZ;
    } else {
        dx = defB->isPlayer ? -1.0f : 1.0f;
        dz = defB->isPlayer ? 1.0f : -1.0f;
    }
    len = sqrtf(dx * dx + dz * dz);
    if (len > 0.001f) {
        dx /= len;
        dz /= len;
    } else {
        dx = defB->isPlayer ? -0.7071f : 0.7071f;
        dz = defB->isPlayer ? 0.7071f : -0.7071f;
    }

    if (!bs->lungeActive || bs->isKnockback) {
        bs->lungeActive = TRUE;
        bs->isKnockback = TRUE;
        bs->lungeTime = 0.0f;
        bs->lungeVec[0] = dx * BDSP_KNOCK_DIST;
        bs->lungeVec[1] = 0.0f;
        bs->lungeVec[2] = dz * BDSP_KNOCK_DIST;
    }

    // Ensure multi-hit or delayed hits also get a crisp impact flash if no recent impact played.
    if (defB->visible && !HasRecentImpactForBattler(defender) && bs->sinceImpactSec > 2.8f) {
        float color[3];
        float pos[3] = { defB->worldX, defB->worldY + 0.80f, defB->worldZ };
        GetTypeColor(bs->lastMoveType, color);
        SpawnVfx(SIM_BATTLE3D_VFX_IMPACT, bs->lastMoveType, defender, -1, 0.0f,
                 0.0f, 0.42f, pos, pos, color, 1.05f);
    }
}

void BattleBdspVfx_Reset(void)
{
    int i;
    memset(&sVfx, 0, sizeof(sVfx));
    for (i = 0; i < SIM_BATTLE3D_MAX_BATTLERS; i++) {
        sVfx.battlers[i].sparkledPartySlot = -1;
        sVfx.battlers[i].lastAttacker = -1;
        sVfx.battlers[i].lastMoveType = TYPE_NORMAL;
        sVfx.battlers[i].sinceImpactSec = 10.0f;
    }
}

void BattleBdspVfx_DiscardPending(void)
{
    int i;

    sVfx.pendingAttackCount = 0;
    for (i = 0; i < SIM_BATTLE3D_MAX_BATTLERS; i++) {
        BdspBattlerVfxState *bs = &sVfx.battlers[i];
        bs->pendingHit = FALSE;
        if (bs->lungeActive) {
            float totalDur = bs->isKnockback ? BDSP_KNOCK_TOTAL_DUR : BDSP_LUNGE_TOTAL_DUR;
            bs->lungeTime += BDSP_VFX_DT;
            if (bs->lungeTime >= totalDur) {
                bs->lungeActive = FALSE;
            }
        }
        if (bs->sinceImpactSec < 10.0f) {
            bs->sinceImpactSec += BDSP_VFX_DT;
        }
        if (bs->hitFlashActive) {
            bs->hitFlashTime += BDSP_VFX_DT;
            if (bs->hitFlashTime >= BDSP_HIT_FLASH_DUR) {
                bs->hitFlashActive = FALSE;
            }
        }
    }
    for (i = 0; i < BDSP_VFX_POOL_SIZE; i++) {
        BdspVfxItem *it = &sVfx.pool[i];
        if (!it->active) {
            continue;
        }
        if (it->delay > 0.0f) {
            it->delay -= BDSP_VFX_DT;
        } else {
            it->elapsed += BDSP_VFX_DT;
            if (it->elapsed >= it->duration) {
                it->active = FALSE;
            }
        }
    }
}

void BattleBdspVfx_NotifyAttack(int attacker, int defender, u16 move)
{
    BdspPendingAttack *pa;

    if (!SIM_Battle3D_ModelsEnabled()) {
        return;
    }
    if (attacker < 0 || attacker >= SIM_BATTLE3D_MAX_BATTLERS || move == MOVE_NONE) {
        return;
    }
    if (sVfx.pendingAttackCount >= BDSP_VFX_PENDING_MAX) {
        memmove(&sVfx.pendingAttacks[0], &sVfx.pendingAttacks[1],
                sizeof(sVfx.pendingAttacks[0]) * (BDSP_VFX_PENDING_MAX - 1));
        sVfx.pendingAttackCount = BDSP_VFX_PENDING_MAX - 1;
    }

    pa = &sVfx.pendingAttacks[sVfx.pendingAttackCount++];
    pa->attacker = attacker;
    pa->defender = defender;
    pa->move = move;
    pa->moveClass = MoveTable_LoadParam(move, MOVEATTRIBUTE_CLASS);
    pa->moveType = (int)MoveTable_LoadParam(move, MOVEATTRIBUTE_TYPE);
    pa->moveRange = MoveTable_LoadParam(move, MOVEATTRIBUTE_RANGE);
    pa->moveFlags = MoveTable_LoadParam(move, MOVEATTRIBUTE_FLAGS);
}

void BattleBdspVfx_NotifyHit(int defender)
{
    if (!SIM_Battle3D_ModelsEnabled()) {
        return;
    }
    if (defender < 0 || defender >= SIM_BATTLE3D_MAX_BATTLERS) {
        return;
    }
    sVfx.battlers[defender].pendingHit = TRUE;
}

void BattleBdspVfx_NotifyShiny(int battler)
{
    if (!SIM_Battle3D_ModelsEnabled()) {
        return;
    }
    if (battler < 0 || battler >= SIM_BATTLE3D_MAX_BATTLERS) {
        return;
    }
    sVfx.battlers[battler].pendingShiny = TRUE;
}

void BattleBdspVfx_Update(BattleSystem *battleSys, SIM_Battle3DFrame *frame)
{
    BattleContext *ctx;
    int maxBattlers;
    int i;

    if (!SIM_Battle3D_ModelsEnabled()) {
        return;
    }
    if (battleSys == NULL || frame == NULL || !frame->active) {
        return;
    }

    ctx = BattleSystem_GetBattleContext(battleSys);
    maxBattlers = BattleSystem_GetMaxBattlers(battleSys);
    if (maxBattlers < 0) {
        maxBattlers = 0;
    } else if (maxBattlers > SIM_BATTLE3D_MAX_BATTLERS) {
        maxBattlers = SIM_BATTLE3D_MAX_BATTLERS;
    }

    // 1. Drain pending attacks.
    for (i = 0; i < sVfx.pendingAttackCount; i++) {
        ProcessAttack(frame, ctx, maxBattlers, &sVfx.pendingAttacks[i]);
    }
    sVfx.pendingAttackCount = 0;

    // 2. Drain pending hits and trigger shiny sparkles once per (slot, species, selectedPartySlot).
    for (i = 0; i < maxBattlers; i++) {
        BdspBattlerVfxState *bs = &sVfx.battlers[i];
        const SIM_Battle3DBattler *b = &frame->battlers[i];
        BOOL nowVisible = (b->visible != 0 && b->species > 0);
        BOOL nowShiny = (b->isShiny != 0);
        int curPartySlot = (ctx != NULL) ? (int)ctx->selectedPartySlot[i] : -1;
        BOOL suppressShinyEdge;

        if (bs->pendingHit) {
            bs->pendingHit = FALSE;
            ProcessHit(frame, maxBattlers, i);
        }

        if (b->species > 0
            && (b->species != bs->sparkledSpecies
                || (curPartySlot >= 0 && bs->sparkledPartySlot >= 0 && curPartySlot != bs->sparkledPartySlot))) {
            bs->sparkled = FALSE;
            bs->sparkledSpecies = b->species;
            bs->sparkledPartySlot = curPartySlot;
        }

        // Ignore visibility edges during capture (breakout) or hit-flicker so shiny sparkles never replay.
        suppressShinyEdge = BattleBdspCapture_IsActive() || bs->hitFlashActive;
        if (nowVisible && (bs->pendingShiny || (nowShiny && !bs->sparkled && !suppressShinyEdge))) {
            static const float kShinyGold[3] = { 1.00f, 0.88f, 0.30f };
            float pos[3] = { b->worldX, b->worldY + 0.85f, b->worldZ };
            SpawnVfx(SIM_BATTLE3D_VFX_SHINY_SPARKLE, TYPE_ELECTRIC, i, i, 0.85f,
                     0.0f, 1.15f, pos, pos, kShinyGold, 1.20f);
            bs->pendingShiny = FALSE;
            bs->sparkled = TRUE;
            bs->sparkledSpecies = b->species;
            bs->sparkledPartySlot = curPartySlot;
        }
    }

    // 3. Advance per-battler contact lunge, knockback jolt, hit-flash, and live status.
    for (i = 0; i < maxBattlers; i++) {
        BdspBattlerVfxState *bs = &sVfx.battlers[i];
        SIM_Battle3DBattler *b = &frame->battlers[i];

        b->hitFlash = 0.0f;
        b->lungeOffset[0] = 0.0f;
        b->lungeOffset[1] = 0.0f;
        b->lungeOffset[2] = 0.0f;
        b->statusCondition = 0;

        if (!b->visible) {
            bs->lungeActive = FALSE;
            bs->hitFlashActive = FALSE;
            continue;
        }

        if (bs->lungeActive) {
            float t = bs->lungeTime;
            if (!bs->isKnockback) {
                float ease = 0.0f;
                float hop = 0.0f;
                if (t < BDSP_LUNGE_FWD_DUR) {
                    float u = t / BDSP_LUNGE_FWD_DUR;
                    float inv = 1.0f - u;
                    ease = 1.0f - inv * inv * inv;
                    hop = sinf(u * BDSP_VFX_PI) * 0.16f;
                } else if (t < BDSP_LUNGE_FWD_DUR + BDSP_LUNGE_HOLD_DUR) {
                    float u = (t - BDSP_LUNGE_FWD_DUR) / BDSP_LUNGE_HOLD_DUR;
                    // Brief impact hit-stop hold with subtle contact tension.
                    ease = 1.0f - 0.06f * sinf(u * BDSP_VFX_PI);
                    hop = 0.0f;
                } else if (t < BDSP_LUNGE_TOTAL_DUR) {
                    float u = (t - (BDSP_LUNGE_FWD_DUR + BDSP_LUNGE_HOLD_DUR)) / BDSP_LUNGE_BACK_DUR;
                    float inv = 1.0f - u;
                    ease = inv * inv * (3.0f - 2.0f * inv);
                    hop = sinf(u * BDSP_VFX_PI) * 0.06f;
                } else {
                    bs->lungeActive = FALSE;
                }
                if (bs->lungeActive) {
                    b->lungeOffset[0] = bs->lungeVec[0] * ease;
                    b->lungeOffset[1] = hop;
                    b->lungeOffset[2] = bs->lungeVec[2] * ease;
                }
            } else {
                float ease = 0.0f;
                if (t < BDSP_KNOCK_OUT_DUR) {
                    float u = t / BDSP_KNOCK_OUT_DUR;
                    float inv = 1.0f - u;
                    ease = 1.0f - inv * inv;
                } else if (t < BDSP_KNOCK_TOTAL_DUR) {
                    float u = (t - BDSP_KNOCK_OUT_DUR) / BDSP_KNOCK_BACK_DUR;
                    float inv = 1.0f - u;
                    ease = inv * inv;
                } else {
                    bs->lungeActive = FALSE;
                }
                if (bs->lungeActive) {
                    b->lungeOffset[0] = bs->lungeVec[0] * ease;
                    b->lungeOffset[1] = 0.0f;
                    b->lungeOffset[2] = bs->lungeVec[2] * ease;
                }
            }
            bs->lungeTime += BDSP_VFX_DT;
        }

        if (bs->hitFlashActive) {
            float u = bs->hitFlashTime / BDSP_HIT_FLASH_DUR;
            if (u >= 1.0f) {
                bs->hitFlashActive = FALSE;
                b->hitFlash = 0.0f;
            } else {
                float inv = 1.0f - u;
                b->hitFlash = BDSP_HIT_FLASH_PEAK * inv * inv;
                bs->hitFlashTime += BDSP_VFX_DT;
            }
        }

        if (ctx != NULL) {
            b->statusCondition = MapStatusCondition(ctx->battleMons[i].status);
        }
    }

    // 4. Advance VFX pool and pack into available frame->vfx[] slots without
    // overwriting any slot already populated by BattleBdspCapture_Update.
    for (i = 0; i < BDSP_VFX_POOL_SIZE; i++) {
        BdspVfxItem *it = &sVfx.pool[i];
        int slot;
        float prog;

        if (!it->active) {
            continue;
        }

        if (it->delay > 0.0f) {
            it->delay -= BDSP_VFX_DT;
            continue;
        }

        prog = it->elapsed / it->duration;
        if (prog >= 1.0f) {
            it->active = FALSE;
            continue;
        }

        if (it->trackBattler >= 0 && it->trackBattler < maxBattlers
            && frame->battlers[it->trackBattler].visible) {
            const SIM_Battle3DBattler *tb = &frame->battlers[it->trackBattler];
            float tx = tb->worldX + tb->lungeOffset[0];
            float ty = tb->worldY + tb->lungeOffset[1] + it->trackYOffset;
            float tz = tb->worldZ + tb->lungeOffset[2];
            it->src[0] = it->dst[0] = tx;
            it->src[1] = it->dst[1] = ty;
            it->src[2] = it->dst[2] = tz;
        }

        for (slot = 0; slot < SIM_BATTLE3D_MAX_VFX; slot++) {
            if (!frame->vfx[slot].active) {
                SIM_Battle3DVfx *out = &frame->vfx[slot];
                out->active = 1;
                out->kind = it->kind;
                out->moveType = it->moveType;
                out->progress = prog;
                out->src[0] = it->src[0];
                out->src[1] = it->src[1];
                out->src[2] = it->src[2];
                out->dst[0] = it->dst[0];
                out->dst[1] = it->dst[1];
                out->dst[2] = it->dst[2];
                out->color[0] = it->color[0];
                out->color[1] = it->color[1];
                out->color[2] = it->color[2];
                out->scale = it->scale;
                break;
            }
        }

        it->elapsed += BDSP_VFX_DT;
    }
}
