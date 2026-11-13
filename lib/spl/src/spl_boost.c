#include "spl_boost.h"

#include <string.h>

static SPLBoostParams sBoostParams;

void SPLBoost_SetParams(const SPLBoostParams *params)
{
    if (params != NULL) {
        sBoostParams = *params;
    }
}

void SPLBoost_GetParams(SPLBoostParams *params)
{
    if (params != NULL) {
        *params = sBoostParams;
    }
}

u32 SPLBoost_Hash(u32 seed)
{
    u32 z = seed + 0x9E3779B9u;
    z = (z ^ (z >> 16)) * 0x85EBCA6Bu;
    z = (z ^ (z >> 13)) * 0xC2B2AE35u;
    return z ^ (z >> 16);
}

int SPLBoost_Jitter(u32 *state, int range)
{
    u32 h;
    int span;

    if (state == NULL || range <= 0) {
        return 0;
    }

    h = SPLBoost_Hash(*state);
    *state = h;
    span = range * 2 + 1;
    return (int)(h % (u32)span) - range;
}
