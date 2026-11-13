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

void SPLBoost_SpawnEmber(SPLBoostStore *store, const SPLBoostEmber *ember)
{
    int slot;

    if (store == NULL || ember == NULL) {
        return;
    }

    if (store->count < SPL_BOOST_MAX_EMBERS) {
        slot = store->count++;
    } else {
        slot = store->next;
        store->next = (store->next + 1) % SPL_BOOST_MAX_EMBERS;
    }

    store->embers[slot] = *ember;
}

void SPLBoost_Update(SPLBoostStore *store)
{
    int i;

    if (store == NULL) {
        return;
    }

    for (i = 0; i < store->count; i++) {
        SPLBoostEmber *ember = &store->embers[i];
        u32 flicker;

        ember->life--;

        if (ember->life <= 0) {
            continue;
        }

        switch (ember->type) {
        case SPL_BOOST_TYPE_FIRE:
            // Embers drift up and slow: buoyant rise, drag on x/z.
            ember->vel.y += 32;
            ember->vel.x -= ember->vel.x >> 6;
            ember->vel.z -= ember->vel.z >> 6;
            break;
        case SPL_BOOST_TYPE_ELECTRIC:
            // Sparks arc out and fall: gravity, light drag, flicker.
            ember->vel.y -= 20;
            ember->vel.x -= ember->vel.x >> 7;
            ember->vel.y -= ember->vel.y >> 7;
            ember->vel.z -= ember->vel.z >> 7;
            flicker = SPLBoost_Hash(ember->seed ^ (u32)ember->life);
            ember->pos.x += (int)(flicker % 193) - 96;
            ember->pos.y += (int)((flicker >> 8) % 193) - 96;
            break;
        case SPL_BOOST_TYPE_ICE:
            // Shards fall slowly, almost no drag.
            ember->vel.y -= 8;
            ember->vel.x -= ember->vel.x >> 6;
            ember->vel.z -= ember->vel.z >> 6;
            break;
        case SPL_BOOST_TYPE_MEGA:
            // Glitter rises slowly and hangs.
            ember->vel.y += 10;
            ember->vel.x -= ember->vel.x >> 6;
            ember->vel.z -= ember->vel.z >> 6;
            break;
        default:
            ember->vel.y -= 10;
            ember->vel.x -= ember->vel.x >> 6;
            ember->vel.z -= ember->vel.z >> 6;
            break;
        }

        ember->pos.x += ember->vel.x;
        ember->pos.y += ember->vel.y;
        ember->pos.z += ember->vel.z;
    }

    // Compact: swap-with-last culls the dead. The order changes, but the
    // sequence of inputs is deterministic, so the result is too.
    for (i = 0; i < store->count;) {
        if (store->embers[i].life <= 0) {
            store->count--;
            if (i != store->count) {
                store->embers[i] = store->embers[store->count];
            }
        } else {
            i++;
        }
    }

    if (store->next >= store->count && store->count > 0) {
        store->next = 0;
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
