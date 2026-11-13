#ifndef SPL_BOOST_H
#define SPL_BOOST_H

#include <nitro/gx/gxcommon.h>
#include <nitro/types.h>

// GPU particle-density boost (lane particles, v2).
//
// The boost is a persistent ember layer, not same-frame copies: each
// frame, live SPL parents spawn ember records into their manager's
// store; embers drift by element type, fade, and die after a short life,
// so they briefly outlive their parent. The SPL draw (spl_emitter.c)
// spawns from parents and draws the store's live embers as tiny square
// dots (1-2 px at DS scale) sampled from the centre texel window of the
// parent texture, brightened for an additive feel on dark backgrounds.
// The fixed G3 blend (src*srcAlpha + dst*(1-srcAlpha)) cannot do true
// additive blending, so the dots are bright with a moderate alpha.
//
// Deterministic: every random choice is SPLBoost_Hash of (seed, frame,
// life). No wall clock, no pointers. Large / ring / flash parents are
// excluded at spawn (by texture size and effective scale), so the Mega
// emblem rings never clone into ghost rings.

#define SPL_BOOST_MAX_EMBERS 512

typedef enum SPLBoostType {
    SPL_BOOST_TYPE_GENERIC = 0,
    SPL_BOOST_TYPE_FIRE,
    SPL_BOOST_TYPE_ELECTRIC,
    SPL_BOOST_TYPE_ICE,
    SPL_BOOST_TYPE_MEGA
} SPLBoostType;

// Per-frame parameters, pushed by the game side (src/fx_particles.c)
// once per drawn frame. density: spawn budget 0-8; a parent spawns an
// ember in a frame with probability budget/8, so at default density the
// steady-state population is about density * ember life / 8 per parent.
// frame: monotonically increasing drawn-frame counter (spawn seed).
typedef struct SPLBoostParams {
    int enabled;
    int density;
    int type;
    int frame;
    int spread256; // jitter radius around the parent, 256 = 1x parent scale
    int brighten256; // how far the ember colour moves toward white
} SPLBoostParams;

typedef struct SPLBoostEmber {
    VecFx32 pos; // world position, same space as its parent particle
    VecFx32 vel; // world velocity, fx32 per frame
    VecFx32 basePos; // emitter base position, for useViewSpace draws
    int useViewSpace;
    int texIndex; // parent texture index in the manager
    fx16 texS; // parent texture repeat (for the centre sampling window)
    fx16 texT;
    int r, g, b; // colour, 0-31 per channel, already brightened
    int life; // frames left
    int maxLife;
    int sizeFx; // quad size in world units (fx32)
    int type;
    u32 seed;
} SPLBoostEmber;

typedef struct SPLBoostStore {
    SPLBoostEmber embers[SPL_BOOST_MAX_EMBERS];
    int count;
    int next; // ring-write index when the store is full
} SPLBoostStore;

void SPLBoost_SetParams(const SPLBoostParams *params);
void SPLBoost_GetParams(SPLBoostParams *params);

// Insert an ember into the store (ring overwrite when full).
void SPLBoost_SpawnEmber(SPLBoostStore *store, const SPLBoostEmber *ember);

// Age every ember one frame, integrate its type behaviour, cull the dead.
void SPLBoost_Update(SPLBoostStore *store);

// Deterministic 32-bit hash (splitmix32): the same seed always gives the
// same child offsets, independent of wall clock, pointers and backend.
u32 SPLBoost_Hash(u32 seed);

// One jitter sample in [-range, range] from a hash state advanced in place.
int SPLBoost_Jitter(u32 *state, int range);

#endif // SPL_BOOST_H
