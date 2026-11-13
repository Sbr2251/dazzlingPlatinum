#include "fx_particles.h"

#include <nitro.h>
#include <stdlib.h>
#include <string.h>

#include "constants/moves.h"
#include "port/sim_config_prj.h"
#include "spl_boost.h"

// Simulator gate (libntr render_gpu/fx_particles.cpp): weak until
// libntr provides it, so this tree builds on its own; a missing
// definition means the boost stays off.
extern int SIM_Particles_IsGpu(void) __attribute__((weak));

#define FX_PARTICLES_MOVE_FRAMES 240
#define FX_PARTICLES_BURST_FRAMES 150
#define FX_PARTICLES_MAX_DENSITY 8

typedef struct FxParticlesMoveTuning {
    int move;
    int extraDensity;
    int trail256;
    int spread256;
} FxParticlesMoveTuning;

// Signature-move tuning: denser and longer trails than the base density.
// Fire Blast / Thunder / Blizzard / Draco Meteor get the strongest boost;
// the golden moves Flamethrower / Thunderbolt get a clear but smaller one.
static const FxParticlesMoveTuning sMoveTuning[] = {
    { MOVE_FIRE_BLAST, 3, 384, 320 },
    { MOVE_THUNDER, 3, 256, 384 },
    { MOVE_BLIZZARD, 2, 320, 384 },
    { MOVE_DRACO_METEOR, 3, 384, 384 },
    { MOVE_FLAMETHROWER, 2, 320, 256 },
    { MOVE_THUNDERBOLT, 2, 256, 320 },
};

static int sMoveRemaining = 0;
static int sMoveExtraDensity = 0;
static int sMoveTrail256 = 256;
static int sMoveSpread256 = 256;
static int sBurstRemaining = 0;

static int EnvFlag(const char *name)
{
    const char *env = getenv(name);

    if (env == NULL || env[0] == 0) {
        return -1;
    }

    return env[0] != '0' ? 1 : 0;
}

static int ClampDensity(int density)
{
    if (density < 0) {
        return 0;
    }

    if (density > FX_PARTICLES_MAX_DENSITY) {
        return FX_PARTICLES_MAX_DENSITY;
    }

    return density;
}

BOOL FxParticles_Enabled(void)
{
    static int sHeadless = -1;
    int env;

    if (sHeadless < 0) {
        const char *headless = getenv("SIM_HEADLESS");
        sHeadless = (headless != NULL && headless[0] != 0 && headless[0] != '0') ? 1 : 0;
    }

    env = EnvFlag("SIM_FX_PARTICLES");

    if (sHeadless) {
        return env == 1 ? TRUE : FALSE;
    }

    if (env >= 0) {
        return env == 1 ? TRUE : FALSE;
    }

    return SIM_Config_prj_GetConfig()->particleBoost ? TRUE : FALSE;
}

int FxParticles_Density(void)
{
    const char *env = getenv("SIM_FX_PARTICLES_DENSITY");

    if (env != NULL && env[0] != 0) {
        return ClampDensity(atoi(env));
    }

    return ClampDensity(SIM_Config_prj_GetConfig()->particleBoostDensity);
}

void FxParticles_Tick(void)
{
    SPLBoostParams params;
    int gpu;

    if (sMoveRemaining > 0) {
        sMoveRemaining--;
        if (sMoveRemaining == 0) {
            sMoveExtraDensity = 0;
            sMoveTrail256 = 256;
            sMoveSpread256 = 256;
        }
    }

    if (sBurstRemaining > 0) {
        sBurstRemaining--;
    }

    gpu = (SIM_Particles_IsGpu != NULL) ? SIM_Particles_IsGpu() : 0;
    memset(&params, 0, sizeof(params));
    params.enabled = (FxParticles_Enabled() && gpu) ? 1 : 0;

    if (sBurstRemaining > 0) {
        params.density = FX_PARTICLES_MAX_DENSITY;
        params.trail256 = 512;
        params.spread256 = 512;
        params.brighten256 = 224;
    } else {
        params.density = ClampDensity(FxParticles_Density() + sMoveExtraDensity);
        params.trail256 = sMoveTrail256;
        params.spread256 = sMoveSpread256;
        params.brighten256 = 128;
    }

    if (!params.enabled) {
        params.density = 0;
    }

    SPLBoost_SetParams(&params);
}

void FxParticles_SetMove(int move)
{
    int i;

    sMoveRemaining = 0;
    sMoveExtraDensity = 0;
    sMoveTrail256 = 256;
    sMoveSpread256 = 256;

    if (move == MOVE_NONE) {
        return;
    }

    for (i = 0; i < (int)(sizeof(sMoveTuning) / sizeof(sMoveTuning[0])); i++) {
        if (sMoveTuning[i].move == move) {
            sMoveExtraDensity = sMoveTuning[i].extraDensity;
            sMoveTrail256 = sMoveTuning[i].trail256;
            sMoveSpread256 = sMoveTuning[i].spread256;
            break;
        }
    }

    sMoveRemaining = FX_PARTICLES_MOVE_FRAMES;
}

void FxParticles_SetMegaBurst(void)
{
    sBurstRemaining = FX_PARTICLES_BURST_FRAMES;
}
