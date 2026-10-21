#include "battle/battle_stage_particles.h"

#include <nitro.h>
#include <string.h>

#include "constants/battle.h"

#include "battle/battle_stage_camera.h"

#include "particle_system.h"

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
// A particle within RIGID_RADIUS px of the point it was emitted from moves rigidly with that point
// (so the particles of one ball keep together); from FREE_RADIUS on, it takes the field at its own
// place (a beam's far end lands on the defender)
#define RIGID_RADIUS 32
#define FREE_RADIUS  96

typedef struct FieldBattler {
    fx32 bodyX; // home body point, px
    fx32 bodyY;
    fx32 homeX; // home foot anchor, px
    fx32 homeY;
    fx32 nowX; // foot anchor now, px
    fx32 nowY;
    fx32 scale;
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
    // The particle field of the system being drawn
    MtxFx44 base; // the system's own projection
    int numBattlers;
    FieldBattler battlers[MAX_BATTLERS];
    BOOL loaded; // a similarity is loaded in this system's draw: the one below
    fx32 loadedTx;
    fx32 loadedTy;
    fx32 loadedScale;
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

BOOL BattleStageParticles_BeginSystem(const MtxFx44 *projection)
{
    BattleStageCameraSimilarity sim;
    int battler, side;
    VecFx32 foot;

    if (!sStageParticles.active) {
        return FALSE;
    }

    sStageParticles.numBattlers = 0;

    for (battler = 0; battler < MAX_BATTLERS; battler++) {
        FieldBattler *b = &sStageParticles.battlers[sStageParticles.numBattlers];

        if (!BattleStageCamera_BattlerFoot(battler, &side, &foot) || !BattleStageCamera_GetSimilarity(battler, &sim)) {
            continue;
        }

        b->homeX = sim.homeX * FX32_ONE;
        b->homeY = sim.homeY * FX32_ONE;
        b->bodyX = b->homeX;
        b->bodyY = b->homeY - BODY_LIFT * FX32_ONE;
        b->nowX = sim.nowX;
        b->nowY = sim.nowY;
        b->scale = sim.scale;
        sStageParticles.numBattlers++;
    }

    if (sStageParticles.numBattlers == 0) {
        return FALSE;
    }

    sStageParticles.base = *projection;
    sStageParticles.loaded = FALSE;
    return TRUE;
}

// Where the system's own camera puts a view-space point on the home screen, px. FALSE behind it.
static BOOL HomeScreen(const VecFx32 *viewPos, fx32 *px, fx32 *py)
{
    const MtxFx44 *base = &sStageParticles.base;
    fx32 cx, cy, cw;

    cx = FX_Mul(viewPos->x, base->_00) + FX_Mul(viewPos->y, base->_10) + FX_Mul(viewPos->z, base->_20) + base->_30;
    cy = FX_Mul(viewPos->x, base->_01) + FX_Mul(viewPos->y, base->_11) + FX_Mul(viewPos->z, base->_21) + base->_31;
    cw = FX_Mul(viewPos->x, base->_03) + FX_Mul(viewPos->y, base->_13) + FX_Mul(viewPos->z, base->_23) + base->_33;

    if (cw <= 0) {
        return FALSE;
    }

    *px = 128 * FX32_ONE + 128 * FX_Div(cx, cw);
    *py = 96 * FX32_ONE - 96 * FX_Div(cy, cw);
    return TRUE;
}

// The field at a home-screen point: where it lands now and its scale
static void Field(fx32 px, fx32 py, fx32 *nowX, fx32 *nowY, fx32 *scale)
{
    const FieldBattler *b;
    u32 spread[MAX_BATTLERS];
    fx32 weight[MAX_BATTLERS];
    u32 nearest = 0xFFFFFFFF;
    fx32 sum;
    int i, near = 0, count = 0;

    // (d^2 + r^2) to each body point, in whole px^2
    for (i = 0; i < sStageParticles.numBattlers; i++) {
        s32 dx = (px - sStageParticles.battlers[i].bodyX) >> FX32_SHIFT;
        s32 dy = (py - sStageParticles.battlers[i].bodyY) >> FX32_SHIFT;

        dx = dx < -1024 ? -1024 : (dx > 1024 ? 1024 : dx);
        dy = dy < -1024 ? -1024 : (dy > 1024 ? 1024 : dy);
        spread[i] = (u32)(dx * dx + dy * dy + SOFT_RADIUS * SOFT_RADIUS);

        if (spread[i] < nearest) {
            nearest = spread[i];
            near = i;
        }
    }

    for (i = 0; i < sStageParticles.numBattlers; i++) {
        if (i != near && spread[i] < nearest * SNAP_RATIO) {
            count++;
        }
    }

    // One battler: its own similarity, as the mons have
    if (count == 0) {
        b = &sStageParticles.battlers[near];
        *nowX = b->nowX + FX_Mul(b->scale, px - b->homeX);
        *nowY = b->nowY + FX_Mul(b->scale, py - b->homeY);
        *scale = b->scale;
        return;
    }

    // A blend: weights (nearest / spread)^3, which sum to at least 1
    sum = 0;

    for (i = 0; i < sStageParticles.numBattlers; i++) {
        fx32 ratio;

        if (i != near && spread[i] >= nearest * SNAP_RATIO) {
            weight[i] = 0;
            continue;
        }

        ratio = (fx32)(((u64)nearest << FX32_SHIFT) / spread[i]);
        weight[i] = FX_Mul(FX_Mul(ratio, ratio), ratio);
        sum += weight[i];
    }

    *nowX = 0;
    *nowY = 0;
    *scale = 0;

    for (i = 0; i < sStageParticles.numBattlers; i++) {
        fx32 w;

        if (weight[i] == 0) {
            continue;
        }

        b = &sStageParticles.battlers[i];
        w = FX_Div(weight[i], sum);
        *nowX += FX_Mul(w, b->nowX + FX_Mul(b->scale, px - b->homeX));
        *nowY += FX_Mul(w, b->nowY + FX_Mul(b->scale, py - b->homeY));
        *scale += FX_Mul(w, b->scale);
    }
}

// The base projection followed by p' = now + s * (p - home) in pixels (as the 2D similarity hook);
// skipped when it is the one loaded last
static void LoadSimilarity(fx32 homeX, fx32 homeY, fx32 nowX, fx32 nowY, fx32 s)
{
    const MtxFx44 *base = &sStageParticles.base;
    MtxFx44 m = *base;
    fx32 tx = s - FX32_ONE + (nowX - FX_Mul(s, homeX)) / 128;
    fx32 ty = FX32_ONE - s + (FX_Mul(s, homeY) - nowY) / 96;
    int r;

    if (sStageParticles.loaded && tx == sStageParticles.loadedTx && ty == sStageParticles.loadedTy
        && s == sStageParticles.loadedScale) {
        return;
    }

    for (r = 0; r < 4; r++) {
        m.m[r][0] = FX_Mul(base->m[r][0], s) + FX_Mul(base->m[r][3], tx);
        m.m[r][1] = FX_Mul(base->m[r][1], s) + FX_Mul(base->m[r][3], ty);
    }

    G3_MtxMode(GX_MTXMODE_PROJECTION);
    G3_LoadMtx44(&m);
    G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);

    sStageParticles.loaded = TRUE;
    sStageParticles.loadedTx = tx;
    sStageParticles.loadedTy = ty;
    sStageParticles.loadedScale = s;
}

void BattleStageParticles_DrawParticle(const VecFx32 *viewPos, const VecFx32 *anchorViewPos)
{
    fx32 px, py, ax, ay, anchorNowX, anchorNowY, anchorScale, nowX, nowY, s, t;
    s32 dx, dy;
    u32 d2;

    if (sStageParticles.numBattlers == 0) {
        return;
    }

    if (!HomeScreen(viewPos, &px, &py)) {
        px = sStageParticles.battlers[0].homeX;
        py = sStageParticles.battlers[0].homeY;
    }

    if (!HomeScreen(anchorViewPos, &ax, &ay)) {
        ax = px;
        ay = py;
    }

    // The particle's emission point takes the field; a particle near it moves rigidly with it, so
    // a ball made of several particles holds together between the mons
    Field(ax, ay, &anchorNowX, &anchorNowY, &anchorScale);

    dx = (px - ax) >> FX32_SHIFT;
    dy = (py - ay) >> FX32_SHIFT;
    dx = dx < -1024 ? -1024 : (dx > 1024 ? 1024 : dx);
    dy = dy < -1024 ? -1024 : (dy > 1024 ? 1024 : dy);
    d2 = (u32)(dx * dx + dy * dy);

    if (d2 <= RIGID_RADIUS * RIGID_RADIUS) {
        LoadSimilarity(ax, ay, anchorNowX, anchorNowY, anchorScale);
        return;
    }

    // Farther out (a beam streaming from the attacker) it takes the field at its own place,
    // reached smoothly by FREE_RADIUS
    Field(px, py, &nowX, &nowY, &s);

    if (d2 < FREE_RADIUS * FREE_RADIUS) {
        t = (fx32)((d2 - RIGID_RADIUS * RIGID_RADIUS) * FX32_ONE / (FREE_RADIUS * FREE_RADIUS - RIGID_RADIUS * RIGID_RADIUS));
        nowX = anchorNowX + FX_Mul(anchorScale, px - ax) + FX_Mul(t, nowX - anchorNowX - FX_Mul(anchorScale, px - ax));
        nowY = anchorNowY + FX_Mul(anchorScale, py - ay) + FX_Mul(t, nowY - anchorNowY - FX_Mul(anchorScale, py - ay));
        s = anchorScale + FX_Mul(t, s - anchorScale);
    }

    LoadSimilarity(px, py, nowX, nowY, s);
}
