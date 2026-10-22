#include "battle/battle_stage_particles.h"

#include <nitro.h>
#include <string.h>

#include "constants/battle.h"

#include "battle/battle_stage_camera.h"

#include "particle_system.h"
#include "system.h"

// The battle plane's clip-to-clip map is built scaled by this, so its small 1/depth terms keep
// their bits in fx32; the final projection is scaled back
#define MAP_SCALE_SHIFT 8
#define MAP_SCALE       (1 << MAP_SCALE_SHIFT)
// A plane this close to the home camera (world units) is degenerate
#define PLANE_MIN_DISTANCE FX32_CONST(0.5)

// The particle field: each particle takes the similarity of the battlers around it, weighted by
// 1 / (d^2 + r^2)^3 from its home screen position to each battler's body point (the foot anchor
// raised by BODY_LIFT px); a battler whose (d^2 + r^2) is SNAP_RATIO times the nearest one's or
// more counts for nothing. The cube keeps a far mon's pull under a pixel near a mon even when
// that mon's similarity is far off (a close-up on the other side).
#define BODY_LIFT   24
#define SOFT_RADIUS 16
#define SNAP_RATIO  32
// The mons share one similarity when each one's own is within SHARED_TOLERANCE px of their mean at
// its body point, a scale difference counting over SHARED_REACH px: a camera shake or pan moves the
// arena and every mon together, up to the parallax between them (Draco Meteor's mirrored 4 px shake
// leaves them about 2 px apart, 1.1 px from the mean). Then a particle system takes that similarity
// in its projection, as the classic 2D hook did, with no work per particle.
#define SHARED_TOLERANCE FX32_CONST(1.5)
#define SHARED_REACH     128
// Otherwise every particle off home costs a few instructions (the hook runs for each one, and the
// heaviest moves draw 100-200 a frame):
// - Within RIGID_RADIUS px of the point it was emitted from (a square) it moves rigidly with that
//   point, which takes the field there once: a ball or burst holds together between the mons, a
//   projectile carries its trail.
// - From FREE_RADIUS px on it takes the field at its own place: a mon's own similarity where the
//   field is within half a pixel of it (NearBattler, integer only), else the field at its
//   CELL_STEP px cell, once per cell and frame (a small cache; the field varies over the distance
//   between the mons, much more than a cell).
// - In between the two blend, so a beam bends instead of breaking where it leaves the square.
// Similarities are rounded (QUANT_*), so a burst, a cell or a mon's surroundings share one
// projection and the projection is reloaded only when it changes.
#define RIGID_RADIUS 80
#define FREE_RADIUS  96
#define MIX_SHIFT    4 // log2(FREE_RADIUS - RIGID_RADIUS)
#define CELL_SHIFT   4
#define CELL_X0      (-64)
#define CELL_Y0      (-64)
#define CELL_COLS    24 // x -64..320
#define CELL_ROWS    20 // y -64..256
#define CACHE_SIZE   64
// 1/1024 scale and 1/2 px: under 0.6 px anywhere on screen
#define QUANT_SCALE 4
#define QUANT_TRANS (FX32_ONE / 2)

// A screen similarity: p' = scale * p + trans, px
typedef struct FieldMap {
    fx32 scale;
    fx32 transX;
    fx32 transY;
} FieldMap;

// A cell's similarity this frame
typedef struct FieldCacheEntry {
    u32 key;
    u16 tag;
    FieldMap map;
} FieldCacheEntry;

typedef struct FieldBattler {
    fx32 bodyX; // home body point, px
    fx32 bodyY;
    FieldMap map; // the mon's own similarity
    FieldMap mapQ; // the same, rounded as the cells are
    s32 logGap[MAX_BATTLERS]; // log2 (Log2x16) of how far each other battler's similarity puts a point from this one's, half px
} FieldBattler;

typedef struct StageParticles {
    BOOL active;
    const u32 *debugFlags;
    BattleSystem *battleSys;
    MtxFx43 homeView;
    MtxFx43 homeViewInverse;
    MtxFx44 homeProjection;
    // The battle plane: its map was built for this view, projection and feet
    BOOL cached;
    MtxFx43 keyView;
    MtxFx44 keyProjection;
    VecFx32 keyFeet[2];
    MtxFx44 map; // home clip -> stage clip, times MAP_SCALE
    // This frame's battlers, rebuilt when gSystem.vblankCounter moves on; frameTag marks this
    // frame's grid entries
    BOOL frameValid;
    u32 frameStamp;
    u16 frameTag;
    int numBattlers;
    FieldBattler battlers[MAX_BATTLERS];
    BOOL shared; // they share one similarity: sharedMap
    FieldMap sharedMap;
    FieldCacheEntry cache[CACHE_SIZE];
    // The particle system being drawn: its own projection, and when that is a plain orthographic
    // one (w = 1, no shear), px = x * kx + ox and py = y * ky + oy for a view-space point, and the
    // projection loaded per particle is a 4x3 (work) with four entries changed
    MtxFx44 base;
    BOOL plainOrtho;
    fx32 kx;
    fx32 ox;
    fx32 ky;
    fx32 oy;
    MtxFx43 work;
    fx32 rigidX; // RIGID_RADIUS and FREE_RADIUS px in view units (plain orthographic only)
    fx32 rigidY;
    fx32 freeX;
    fx32 freeY;
    // The last particle's emission point (view space), its home screen point and its field
    BOOL anchorValid;
    BOOL anchorMapValid;
    VecFx32 anchorView;
    fx32 anchorX;
    fx32 anchorY;
    FieldMap anchorMap;
    BOOL loaded; // a similarity is loaded in this system's draw: loadedMap
    BOOL loadedIsAnchor; // ... and it is anchorMap
    FieldMap loadedMap;
} StageParticles;

static StageParticles sStageParticles;

void BattleStageParticles_Init(BattleSystem *battleSys, const BattleStageCameraHome *home, const u32 *debugFlags)
{
    memset(&sStageParticles, 0, sizeof(sStageParticles));
    sStageParticles.debugFlags = debugFlags;

    if (home == NULL || home->view == NULL || home->projection == NULL) {
        return;
    }

    sStageParticles.battleSys = battleSys;
    sStageParticles.homeView = *home->view;
    sStageParticles.homeProjection = *home->projection;

    if (MTX_Inverse43(&sStageParticles.homeView, &sStageParticles.homeViewInverse) != 0) {
        return;
    }

    sStageParticles.active = TRUE;
    ParticleSystem_SetParticleHook(BattleStageParticles_DrawParticle);
}

void BattleStageParticles_Free(void)
{
    if (sStageParticles.active) {
        ParticleSystem_SetParticleHook(NULL);
    }

    sStageParticles.active = FALSE;
    sStageParticles.cached = FALSE;
    sStageParticles.battleSys = NULL;
    sStageParticles.debugFlags = NULL;
}

BOOL BattleStageParticles_KeepDebugViewInMoves(void)
{
    return sStageParticles.active && sStageParticles.debugFlags != NULL
        && (*sStageParticles.debugFlags & BATTLE_STAGE_DEBUG_KEEP_VIEW_IN_MOVES);
}

// The battle plane (BATTLE_STAGE_DEBUG_PARTICLES_PLANE)

// ab = a * b (row vectors, as NNS), summed in 64 bits; the result is shifted right by shift
static void Mul44(const MtxFx44 *a, const MtxFx44 *b, MtxFx44 *ab, int shift)
{
    s64 round = (s64)1 << (shift - 1);
    int r, c, j;

    for (r = 0; r < 4; r++) {
        for (c = 0; c < 4; c++) {
            s64 sum = 0;

            for (j = 0; j < 4; j++) {
                sum += (s64)a->m[r][j] * b->m[j][c];
            }

            ab->m[r][c] = (fx32)((sum + round) >> shift);
        }
    }
}

// The mean foot point of each side's battlers (world); FALSE unless both sides have one
static BOOL SideFeet(VecFx32 *feet)
{
    VecFx32 sum[2];
    int count[2] = { 0, 0 };
    int battler, side;

    sum[0].x = sum[0].y = sum[0].z = 0;
    sum[1] = sum[0];

    for (battler = 0; battler < MAX_BATTLERS; battler++) {
        VecFx32 foot;

        if (BattleStageCamera_BattlerFoot(battler, &side, &foot)) {
            VEC_Add(&sum[side], &foot, &sum[side]);
            count[side]++;
        }
    }

    if (count[0] == 0 || count[1] == 0) {
        return FALSE;
    }

    for (side = 0; side < 2; side++) {
        feet[side].x = sum[side].x / count[side];
        feet[side].y = sum[side].y / count[side];
        feet[side].z = sum[side].z / count[side];
    }

    return TRUE;
}

// The map from a particle system's clip space (the classic picture: the home screen) to the
// stage camera's clip space, times MAP_SCALE.
//
// A home-screen point (x, y, w) in clip space is a ray of the home camera; it lies on the battle
// plane n.X = k (home view space) at the homogeneous home view point
//     Q = (x / H00, y / H11, w / H23, (n.Q.xyz) / k),
// which the home projection H takes back to (x, y, ., w). Q then goes to the world and into the
// current view (G = homeView^-1 * view) and through the current projection P.
static BOOL BuildMap(const VecFx32 *feet, const MtxFx43 *view, const MtxFx44 *projection, MtxFx44 *map)
{
    const MtxFx44 *home = &sStageParticles.homeProjection;
    VecFx32 a, b, up, along, n;
    MtxFx43 g;
    MtxFx44 t, tg;
    fx32 k;
    int r, c;

    if (home->_00 == 0 || home->_11 == 0 || home->_23 == 0) {
        return FALSE;
    }

    // The battle plane in home view space: upright (it holds the world's up), through both sides' feet
    MTX_MultVec43(&feet[0], &sStageParticles.homeView, &a);
    MTX_MultVec43(&feet[1], &sStageParticles.homeView, &b);
    up.x = sStageParticles.homeView._10;
    up.y = sStageParticles.homeView._11;
    up.z = sStageParticles.homeView._12;
    VEC_Subtract(&b, &a, &along);
    VEC_CrossProduct(&along, &up, &n);

    if (n.x == 0 && n.y == 0 && n.z == 0) {
        return FALSE;
    }

    VEC_Normalize(&n, &n);
    k = VEC_DotProduct(&n, &a);

    if (k < 0) {
        k = -k;
        n.x = -n.x;
        n.y = -n.y;
        n.z = -n.z;
    }

    if (k < PLANE_MIN_DISTANCE) {
        return FALSE;
    }

    // t: clip (x, y, z, w) -> Q, times MAP_SCALE. The particle depth (clip z) is not used.
    MI_CpuClear32(&t, sizeof(t));
    t.m[0][0] = FX_Div(MAP_SCALE * FX32_ONE, home->_00);
    t.m[1][1] = FX_Div(MAP_SCALE * FX32_ONE, home->_11);
    t.m[3][2] = FX_Div(MAP_SCALE * FX32_ONE, home->_23);
    t.m[0][3] = FX_Div(FX_Mul(t.m[0][0], n.x), k);
    t.m[1][3] = FX_Div(FX_Mul(t.m[1][1], n.y), k);
    t.m[3][3] = FX_Div(FX_Mul(t.m[3][2], n.z), k);

    // tg = t * G: rows of Q.xyz through G's rotation, plus Q.w times its translation
    MTX_Concat43(&sStageParticles.homeViewInverse, view, &g);

    for (r = 0; r < 4; r++) {
        for (c = 0; c < 3; c++) {
            s64 sum = (s64)t.m[r][0] * g.m[0][c] + (s64)t.m[r][1] * g.m[1][c] + (s64)t.m[r][2] * g.m[2][c]
                + (s64)t.m[r][3] * g.m[3][c];

            tg.m[r][c] = (fx32)((sum + (1 << (FX32_SHIFT - 1))) >> FX32_SHIFT);
        }

        tg.m[r][3] = t.m[r][3];
    }

    Mul44(&tg, projection, map, FX32_SHIFT);
    return TRUE;
}

BOOL BattleStageParticles_ProjectOnPlane(MtxFx44 *projection)
{
    const MtxFx43 *view = BattleStageCamera_View();
    const MtxFx44 *stageProjection = BattleStageCamera_Projection();
    VecFx32 feet[2];
    MtxFx44 out;
    int r;

    if (!sStageParticles.active || view == NULL || stageProjection == NULL || !SideFeet(feet)) {
        return FALSE;
    }

    if (!sStageParticles.cached
        || memcmp(&sStageParticles.keyView, view, sizeof(*view)) != 0
        || memcmp(&sStageParticles.keyProjection, stageProjection, sizeof(*stageProjection)) != 0
        || memcmp(sStageParticles.keyFeet, feet, sizeof(feet)) != 0) {
        sStageParticles.cached = FALSE;

        if (!BuildMap(feet, view, stageProjection, &sStageParticles.map)) {
            return FALSE;
        }

        sStageParticles.keyView = *view;
        sStageParticles.keyProjection = *stageProjection;
        sStageParticles.keyFeet[0] = feet[0];
        sStageParticles.keyFeet[1] = feet[1];
        sStageParticles.cached = TRUE;
    }

    Mul44(projection, &sStageParticles.map, &out, FX32_SHIFT + MAP_SCALE_SHIFT);

    // Depth: the particle system's own NDC depth (near -1, in front of the arena and the mons), as
    // z' = -w' + (z + w); at home w' = w and this is z. Off home z'/w' = -1 + (z/w + 1) * w / w', so
    // the particles keep their order and stay inside the near plane.
    for (r = 0; r < 4; r++) {
        out.m[r][2] = projection->m[r][2] + projection->m[r][3] - out.m[r][3];
    }

    *projection = out;
    return TRUE;
}

// The particle field (the default)

// The per-particle path runs for every particle off home: ARM code, so FX_Mul is inline (the battle
// code is Thumb, where it is a call)
#include <nitro/code32.h>

static inline fx32 Quantize(fx32 v, fx32 step)
{
    return (v + step / 2) & ~(step - 1);
}

// (d^2 + r^2) from a home-screen point to a battler's body point, whole px^2
static inline u32 Spread(const FieldBattler *b, fx32 px, fx32 py)
{
    s32 dx = (px - b->bodyX) >> FX32_SHIFT;
    s32 dy = (py - b->bodyY) >> FX32_SHIFT;

    dx = dx < -1024 ? -1024 : (dx > 1024 ? 1024 : dx);
    dy = dy < -1024 ? -1024 : (dy > 1024 ? 1024 : dy);
    return (u32)(dx * dx + dy * dy + SOFT_RADIUS * SOFT_RADIUS);
}

// The exact field at a home-screen point: weights (nearest / spread)^3 to the mons, a mon SNAP_RATIO
// times as far as the nearest counting for nothing. A similarity at a point is linear in its scale
// and translation, so the blend of the mons' images is the blend of their maps.
static void Field(fx32 px, fx32 py, FieldMap *out)
{
    const StageParticles *sp = &sStageParticles;
    u32 spread[MAX_BATTLERS];
    fx32 weight[MAX_BATTLERS];
    u32 nearest = 0xFFFFFFFF;
    fx32 sum = 0;
    int i, near = 0;

    for (i = 0; i < sp->numBattlers; i++) {
        spread[i] = Spread(&sp->battlers[i], px, py);

        if (spread[i] < nearest) {
            nearest = spread[i];
            near = i;
        }
    }

    for (i = 0; i < sp->numBattlers; i++) {
        fx32 ratio;

        if (i != near && spread[i] >= nearest * SNAP_RATIO) {
            weight[i] = 0;
            continue;
        }

        // FX_Div of two px^2 counts is their ratio in fx32, through the hardware divider
        ratio = i == near ? FX32_ONE : FX_Div((fx32)nearest, (fx32)spread[i]);
        weight[i] = FX_Mul(FX_Mul(ratio, ratio), ratio);
        sum += weight[i];
    }

    if (sum == FX32_ONE) {
        *out = sp->battlers[near].map;
        return;
    }

    sum = FX_Inv(sum);
    out->scale = 0;
    out->transX = 0;
    out->transY = 0;

    for (i = 0; i < sp->numBattlers; i++) {
        const FieldMap *map = &sp->battlers[i].map;
        fx32 w;

        if (weight[i] == 0) {
            continue;
        }

        w = FX_Mul(weight[i], sum);
        out->scale += FX_Mul(w, map->scale);
        out->transX += FX_Mul(w, map->transX);
        out->transY += FX_Mul(w, map->transY);
    }
}

// log2(x) in 1/16ths (x > 0), from the leading one and a table of the next four bits
static const u8 sLog2Frac[16] = { 0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 12, 13, 14, 15 }; // floor(16 log2(1 + f / 16))

static inline s32 Log2x16(u32 x)
{
    u32 n = 31 - MATH_CountLeadingZeros(x);

    return (s32)(n * 16 + sLog2Frac[((x << (31 - n)) >> 27) & 15]);
}

// The battler whose own similarity the field at this point is within about half a pixel of, or -1:
// the nearest one k, when every other battler j has (s_k / s_j)^3 * gap_kj <= 1 half px, s being
// (d^2 + r^2) (j's weight in the field is at most that ratio cubed). In log2, integer only.
static int NearBattler(fx32 px, fx32 py)
{
    const StageParticles *sp = &sStageParticles;
    s32 lg[MAX_BATTLERS];
    s32 nearest = 0x7FFFFFFF;
    int i, near = 0;

    for (i = 0; i < sp->numBattlers; i++) {
        lg[i] = Log2x16(Spread(&sp->battlers[i], px, py));

        if (lg[i] < nearest) {
            nearest = lg[i];
            near = i;
        }
    }

    for (i = 0; i < sp->numBattlers; i++) {
        if (i != near && 3 * (nearest - lg[i]) + sp->battlers[near].logGap[i] > 0) {
            return -1;
        }
    }

    return near;
}

static void BuildFrame(void)
{
    StageParticles *sp = &sStageParticles;
    BattleStageCameraSimilarity sim;
    FieldMap mean = { 0, 0, 0 };
    int battler, side, i;
    VecFx32 foot;

    sp->numBattlers = 0;
    sp->shared = FALSE;

    if (++sp->frameTag == 0) {
        MI_CpuClear32(sp->cache, sizeof(sp->cache));
        sp->frameTag = 1;
    }

    for (battler = 0; battler < MAX_BATTLERS; battler++) {
        FieldBattler *b = &sp->battlers[sp->numBattlers];

        if (!BattleStageCamera_BattlerFoot(battler, &side, &foot) || !BattleStageCamera_GetSimilarity(battler, &sim)) {
            continue;
        }

        b->bodyX = sim.homeX * FX32_ONE;
        b->bodyY = (sim.homeY - BODY_LIFT) * FX32_ONE;
        b->map.scale = sim.scale;
        b->map.transX = sim.nowX - FX_Mul(sim.scale, sim.homeX * FX32_ONE);
        b->map.transY = sim.nowY - FX_Mul(sim.scale, sim.homeY * FX32_ONE);
        mean.scale += b->map.scale;
        mean.transX += b->map.transX;
        mean.transY += b->map.transY;
        sp->numBattlers++;
    }

    if (sp->numBattlers == 0) {
        return;
    }

    for (i = 0; i < sp->numBattlers; i++) {
        FieldBattler *b = &sp->battlers[i];
        int j;

        b->mapQ.scale = Quantize(b->map.scale, QUANT_SCALE);
        b->mapQ.transX = Quantize(b->map.transX, QUANT_TRANS);
        b->mapQ.transY = Quantize(b->map.transY, QUANT_TRANS);

        // Anywhere in the cells' range (|p| < 320 px)
        for (j = 0; j < sp->numBattlers; j++) {
            const FieldMap *o = &sp->battlers[j].map;
            fx32 ds = MATH_IAbs(o->scale - b->map.scale);
            fx32 dt = MATH_IAbs(o->transX - b->map.transX) > MATH_IAbs(o->transY - b->map.transY)
                ? MATH_IAbs(o->transX - b->map.transX)
                : MATH_IAbs(o->transY - b->map.transY);
            u32 gap = (u32)((dt + ds * 320) >> (FX32_SHIFT - 1)) + 1;

            b->logGap[j] = Log2x16(gap > 4096 ? 4096 : gap) + 2; // + 2: the table rounds down
        }
    }

    mean.scale /= sp->numBattlers;
    mean.transX /= sp->numBattlers;
    mean.transY /= sp->numBattlers;
    sp->sharedMap = mean;
    sp->shared = TRUE;

    for (i = 0; i < sp->numBattlers; i++) {
        const FieldBattler *b = &sp->battlers[i];
        fx32 ds = b->map.scale - mean.scale;
        fx32 devX = FX_Mul(ds, b->bodyX) + b->map.transX - mean.transX;
        fx32 devY = FX_Mul(ds, b->bodyY) + b->map.transY - mean.transY;
        fx32 dev = MATH_IAbs(devX) > MATH_IAbs(devY) ? MATH_IAbs(devX) : MATH_IAbs(devY);

        if (dev + MATH_IAbs(ds) * SHARED_REACH > SHARED_TOLERANCE) {
            sp->shared = FALSE;
            break;
        }
    }
}


// out = in followed by the similarity, in clip space: x_ndc = x / 128 - 1, y_ndc = 1 - y / 96, the
// translation scaled by w, so it holds for any particle camera. out may be in.
static void ApplyMap(const MtxFx44 *in, const FieldMap *map, MtxFx44 *out)
{
    fx32 s = map->scale;
    fx32 tx = s - FX32_ONE + map->transX / 128;
    fx32 ty = FX32_ONE - s - map->transY / 96;
    int r;

    for (r = 0; r < 4; r++) {
        fx32 c0 = in->m[r][0], c1 = in->m[r][1], c3 = in->m[r][3];

        out->m[r][0] = FX_Mul(c0, s) + FX_Mul(c3, tx);
        out->m[r][1] = FX_Mul(c1, s) + FX_Mul(c3, ty);
        out->m[r][2] = in->m[r][2];
        out->m[r][3] = c3;
    }
}

int BattleStageParticles_BeginSystem(MtxFx44 *projection)
{
    StageParticles *sp = &sStageParticles;
    const MtxFx44 *base = projection;
    int r;

    if (!sp->active) {
        return BATTLE_STAGE_PARTICLES_NONE;
    }

    if (!sp->frameValid || sp->frameStamp != gSystem.vblankCounter) {
        BuildFrame();
        sp->frameStamp = gSystem.vblankCounter;
        sp->frameValid = TRUE;
    }

    if (sp->numBattlers == 0) {
        return BATTLE_STAGE_PARTICLES_NONE;
    }

    if (sp->shared) {
        ApplyMap(projection, &sp->sharedMap, projection);
        return BATTLE_STAGE_PARTICLES_SHARED;
    }

    sp->base = *projection;
    sp->plainOrtho = base->_01 == 0 && base->_03 == 0 && base->_10 == 0 && base->_13 == 0 && base->_20 == 0
        && base->_21 == 0 && base->_23 == 0 && base->_33 == FX32_ONE;
    sp->kx = 128 * base->_00;
    sp->ox = 128 * (FX32_ONE + base->_30);
    sp->ky = -96 * base->_11;
    sp->oy = 96 * (FX32_ONE - base->_31);

    for (r = 0; r < 4; r++) {
        sp->work.m[r][0] = base->m[r][0];
        sp->work.m[r][1] = base->m[r][1];
        sp->work.m[r][2] = base->m[r][2];
    }

    sp->rigidX = sp->plainOrtho && sp->kx != 0 ? MATH_IAbs(FX_Div(RIGID_RADIUS * FX32_ONE, sp->kx)) : 0;
    sp->rigidY = sp->plainOrtho && sp->ky != 0 ? MATH_IAbs(FX_Div(RIGID_RADIUS * FX32_ONE, sp->ky)) : 0;
    sp->freeX = sp->plainOrtho && sp->kx != 0 ? MATH_IAbs(FX_Div(FREE_RADIUS * FX32_ONE, sp->kx)) : 0;
    sp->freeY = sp->plainOrtho && sp->ky != 0 ? MATH_IAbs(FX_Div(FREE_RADIUS * FX32_ONE, sp->ky)) : 0;
    sp->loaded = FALSE;
    sp->loadedIsAnchor = FALSE;
    sp->anchorValid = FALSE;
    return BATTLE_STAGE_PARTICLES_FIELD;
}

// Where the system's own camera puts a view-space point on the home screen, px. FALSE behind it.
static BOOL HomeScreen(const VecFx32 *viewPos, fx32 *px, fx32 *py)
{
    const StageParticles *sp = &sStageParticles;
    const MtxFx44 *base = &sp->base;
    fx32 cx, cy, cw;

    if (sp->plainOrtho) {
        *px = FX_Mul(viewPos->x, sp->kx) + sp->ox;
        *py = FX_Mul(viewPos->y, sp->ky) + sp->oy;
        return TRUE;
    }

    cx = FX_Mul(viewPos->x, base->_00) + FX_Mul(viewPos->y, base->_10) + FX_Mul(viewPos->z, base->_20) + base->_30;
    cy = FX_Mul(viewPos->x, base->_01) + FX_Mul(viewPos->y, base->_11) + FX_Mul(viewPos->z, base->_21) + base->_31;
    cw = FX_Mul(viewPos->x, base->_03) + FX_Mul(viewPos->y, base->_13) + FX_Mul(viewPos->z, base->_23) + base->_33;

    if (cw <= 0) {
        return FALSE;
    }

    if (cw == FX32_ONE) {
        *px = 128 * FX32_ONE + 128 * cx;
        *py = 96 * FX32_ONE - 96 * cy;
        return TRUE;
    }

    *px = 128 * FX32_ONE + 128 * FX_Div(cx, cw);
    *py = 96 * FX32_ONE - 96 * FX_Div(cy, cw);
    return TRUE;
}

// The system's projection followed by the similarity; nothing when it is the one loaded last
static void LoadMap(const FieldMap *map)
{
    StageParticles *sp = &sStageParticles;
    MtxFx44 m;

    if (sp->loaded && map->scale == sp->loadedMap.scale && map->transX == sp->loadedMap.transX
        && map->transY == sp->loadedMap.transY) {
        return;
    }

    G3_MtxMode(GX_MTXMODE_PROJECTION);

    if (sp->plainOrtho) {
        // As ApplyMap with a w column of (0, 0, 0, 1) and no shear: four entries change, and the
        // matrix loads as a 4x3
        fx32 s = map->scale;

        sp->work.m[0][0] = FX_Mul(sp->base.m[0][0], s);
        sp->work.m[1][1] = FX_Mul(sp->base.m[1][1], s);
        sp->work.m[3][0] = FX_Mul(sp->base.m[3][0], s) + s - FX32_ONE + map->transX / 128;
        sp->work.m[3][1] = FX_Mul(sp->base.m[3][1], s) + FX32_ONE - s - map->transY / 96;
        G3_LoadMtx43(&sp->work);
    } else {
        ApplyMap(&sp->base, map, &m);
        G3_LoadMtx44(&m);
    }

    G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
    sp->loaded = TRUE;
    sp->loadedMap = *map;
}

static void LoadAnchorMap(void)
{
    StageParticles *sp = &sStageParticles;

    if (!sp->loadedIsAnchor) {
        LoadMap(&sp->anchorMap);
        sp->loadedIsAnchor = TRUE;
    }
}

// The emission point's similarity: a mon's own when the field there is within half a pixel of it
static void AnchorMap(void)
{
    StageParticles *sp = &sStageParticles;
    int k = NearBattler(sp->anchorX, sp->anchorY);

    if (k >= 0) {
        sp->anchorMap = sp->battlers[k].mapQ;
    } else {
        Field(sp->anchorX, sp->anchorY, &sp->anchorMap);
        sp->anchorMap.scale = Quantize(sp->anchorMap.scale, QUANT_SCALE);
        sp->anchorMap.transX = Quantize(sp->anchorMap.transX, QUANT_TRANS);
        sp->anchorMap.transY = Quantize(sp->anchorMap.transY, QUANT_TRANS);
    }

    sp->anchorMapValid = TRUE;
    sp->loadedIsAnchor = FALSE;
}

// The field at a particle's place: near a mon its own similarity, shared by everything near it;
// else its cell's
static const FieldMap *FieldAt(fx32 px, fx32 py)
{
    StageParticles *sp = &sStageParticles;
    FieldCacheEntry *entry;
    s32 cx, cy;
    u32 key;
    int k;

    if ((k = NearBattler(px, py)) >= 0) {
        return &sp->battlers[k].mapQ;
    }

    cx = ((px >> FX32_SHIFT) - CELL_X0) >> CELL_SHIFT;
    cy = ((py >> FX32_SHIFT) - CELL_Y0) >> CELL_SHIFT;
    cx = cx < 0 ? 0 : (cx >= CELL_COLS ? CELL_COLS - 1 : cx);
    cy = cy < 0 ? 0 : (cy >= CELL_ROWS ? CELL_ROWS - 1 : cy);
    key = (u32)(cy * CELL_COLS + cx);
    entry = &sp->cache[(key ^ (key >> 6)) & (CACHE_SIZE - 1)];

    if (entry->tag != sp->frameTag || entry->key != key) {
        Field((CELL_X0 * FX32_ONE) + (cx << (CELL_SHIFT + FX32_SHIFT)) + (FX32_ONE << (CELL_SHIFT - 1)),
            (CELL_Y0 * FX32_ONE) + (cy << (CELL_SHIFT + FX32_SHIFT)) + (FX32_ONE << (CELL_SHIFT - 1)), &entry->map);
        entry->map.scale = Quantize(entry->map.scale, QUANT_SCALE);
        entry->map.transX = Quantize(entry->map.transX, QUANT_TRANS);
        entry->map.transY = Quantize(entry->map.transY, QUANT_TRANS);
        entry->key = key;
        entry->tag = sp->frameTag;
    }

    return &entry->map;
}

void BattleStageParticles_DrawParticle(const VecFx32 *viewPos, const VecFx32 *anchorViewPos)
{
    StageParticles *sp = &sStageParticles;
    const FieldMap *own;
    FieldMap mix;
    fx32 px, py, d, t;

    if (sp->numBattlers == 0) {
        return;
    }

    // The emission point; the particles of one burst share it, so it is kept from the last particle
    if (!sp->anchorValid || anchorViewPos->x != sp->anchorView.x || anchorViewPos->y != sp->anchorView.y
        || anchorViewPos->z != sp->anchorView.z) {
        sp->anchorView = *anchorViewPos;
        sp->anchorValid = TRUE;
        sp->anchorMapValid = FALSE;
        sp->loadedIsAnchor = FALSE;

        if (!HomeScreen(anchorViewPos, &sp->anchorX, &sp->anchorY)) {
            sp->anchorX = sp->battlers[0].bodyX;
            sp->anchorY = sp->battlers[0].bodyY;
        }
    }

    // Distance from it, px (the larger axis); with a plain orthographic camera the rigid test is
    // done in view units, before the particle's screen position is needed
    if (sp->plainOrtho) {
        fx32 vx = MATH_IAbs(viewPos->x - anchorViewPos->x);
        fx32 vy = MATH_IAbs(viewPos->y - anchorViewPos->y);

        if (vx < sp->rigidX && vy < sp->rigidY) {
            d = 0;
        } else if (vx < sp->freeX && vy < sp->freeY) {
            fx32 dx = FX_Mul(vx, MATH_IAbs(sp->kx)), dy = FX_Mul(vy, MATH_IAbs(sp->ky));

            d = dx > dy ? dx : dy;
        } else {
            d = FREE_RADIUS * FX32_ONE;
        }

        if (d < RIGID_RADIUS * FX32_ONE) {
            if (!sp->anchorMapValid) {
                AnchorMap();
            }

            LoadAnchorMap();
            return;
        }

        px = FX_Mul(viewPos->x, sp->kx) + sp->ox;
        py = FX_Mul(viewPos->y, sp->ky) + sp->oy;
    } else {
        fx32 dx, dy;

        if (!HomeScreen(viewPos, &px, &py)) {
            px = sp->battlers[0].bodyX;
            py = sp->battlers[0].bodyY;
        }

        dx = MATH_IAbs(px - sp->anchorX);
        dy = MATH_IAbs(py - sp->anchorY);
        d = dx > dy ? dx : dy;

        if (d < RIGID_RADIUS * FX32_ONE) {
            if (!sp->anchorMapValid) {
                AnchorMap();
            }

            LoadAnchorMap();
            return;
        }
    }

    sp->loadedIsAnchor = FALSE;
    own = FieldAt(px, py);

    if (d >= FREE_RADIUS * FX32_ONE) {
        LoadMap(own);
        return;
    }

    if (!sp->anchorMapValid) {
        AnchorMap();
        sp->loadedIsAnchor = FALSE;
    }

    // Where the two agree (both a mon's own, or a flat field) there is nothing to blend
    if (own->scale == sp->anchorMap.scale && own->transX == sp->anchorMap.transX && own->transY == sp->anchorMap.transY) {
        LoadMap(own);
        return;
    }

    t = (d - RIGID_RADIUS * FX32_ONE) >> MIX_SHIFT;
    mix.scale = Quantize(sp->anchorMap.scale + FX_Mul(t, own->scale - sp->anchorMap.scale), QUANT_SCALE);
    mix.transX = Quantize(sp->anchorMap.transX + FX_Mul(t, own->transX - sp->anchorMap.transX), QUANT_TRANS);
    mix.transY = Quantize(sp->anchorMap.transY + FX_Mul(t, own->transY - sp->anchorMap.transY), QUANT_TRANS);
    LoadMap(&mix);
}

#include <nitro/codereset.h>
