#ifndef SPL_BOOST_H
#define SPL_BOOST_H

#include <nitro/types.h>

// GPU particle-density boost (lane particles): per-frame parameters for
// the child-sparkle pass in spl_emitter.c. The game side (src/fx_particles.c)
// owns the config, the move tuning table and the decay timers and pushes
// the resolved parameters here once per drawn frame; the SPL draw only
// reads them, so an unset (zero) state draws nothing.
//
// density: child sparkles per live parent particle, 0-8 (0 = off).
// trail256: trail length behind a moving particle, 256 = 1x.
// spread256: jitter radius around the parent, 256 = 1x.
// brighten256: how far the child colour moves toward white, 256 = full white.

typedef struct SPLBoostParams {
    int enabled;
    int density;
    int trail256;
    int spread256;
    int brighten256;
} SPLBoostParams;

void SPLBoost_SetParams(const SPLBoostParams *params);
void SPLBoost_GetParams(SPLBoostParams *params);

// Deterministic 32-bit hash (splitmix32): the same seed always gives the
// same child offsets, independent of wall clock, pointers and backend.
u32 SPLBoost_Hash(u32 seed);

// One jitter sample in [-range, range] from a hash state advanced in place.
int SPLBoost_Jitter(u32 *state, int range);

#endif // SPL_BOOST_H
