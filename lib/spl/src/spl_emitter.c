#include "spl_emitter.h"

#include <nitro/fx/fx.h>
#include <nitro/fx/fx_const.h>
#include <nitro/fx/fx_mtx33.h>
#include <nitro/fx/fx_mtx43.h>
#include <nitro/fx/fx_trig.h>
#include <nitro/gx/g3.h>
#include <nitro/gx/g3imm.h>

#include "spl_boost.h"
#include "spl_internal.h"

#include <stdio.h>
#include <stdlib.h>
#include "spl_manager.h"
#include "spl_particle.h"
#include "spl_resource.h"
#include "spl_texture.h"

#ifndef SDK_BUILD_ARM
#include <nitro/fx/fx_vec.h>
#endif

#define ANIM_FUNC_NO_LOOP 0
#define ANIM_FUNC_LOOP    1

typedef void (*DrawFunc)(SPLManager *mgr, SPLParticle *ptcl);
typedef void (*SetTexFunc)(SPLTexture *tex);

typedef struct FieldFunc {
    void (*func)(SPLParticle *, SPLResource *, int);
    BOOL loop;
} AnimFunc;

typedef struct FieldFunc8 {
    void (*func)(SPLParticle *, SPLResource *, u8);
    BOOL loop;
} FieldFunc8;

static void SPLUtil_SetTexture(SPLTexture *tex);
static void SPLUtil_SetTexture_Stub(SPLTexture *tex);
static void SPLManager_DrawParticles(SPLManager *mgr);
static void SPLManager_DrawChildParticles(SPLManager *mgr);
static void SPLManager_SpawnBoostEmbers(SPLManager *mgr);

static void SPLUtil_SetTexture(SPLTexture *tex)
{
    SPLTextureParam param = tex->param;

    G3_TexImageParam(
        param.format,
        GX_TEXGEN_TEXCOORD,
        param.s,
        param.t,
        param.repeat,
        param.flip,
        param.palColor0,
        tex->texAddr);

    G3_TexPlttBase(tex->palAddr, param.format);
    G3_MtxMode(GX_MTXMODE_TEXTURE);
    G3_Identity();
    G3_Scale(tex->width * FX32_ONE, tex->height * FX32_ONE, 0);
    G3_MtxMode(GX_MTXMODE_POSITION);
}

static void SPLUtil_SetTexture_Stub(SPLTexture *tex)
{
}

void SPLEmitter_Init(SPLEmitter *emtr, SPLResource *res, const VecFx32 *pos)
{
    emtr->resource = res;
    emtr->state.all = 0;

    emtr->position.x = pos->x + emtr->resource->header->emitterBasePos.x;
    emtr->position.y = pos->y + emtr->resource->header->emitterBasePos.y;
    emtr->position.z = pos->z + emtr->resource->header->emitterBasePos.z;

    emtr->particleInitVelocity.x = 0;
    emtr->particleInitVelocity.y = 0;
    emtr->particleInitVelocity.z = 0;
    emtr->velocity.x = emtr->velocity.y = emtr->velocity.z = 0;

    emtr->age = 0;
    emtr->emissionCountFractional = 0;

    emtr->axis = emtr->resource->header->axis;
    emtr->initAngle = emtr->resource->header->initAngle;
    emtr->emissionCount = emtr->resource->header->emissionCount;
    emtr->radius = emtr->resource->header->radius;
    emtr->length = emtr->resource->header->length;
    emtr->initVelPositionAmplifier = emtr->resource->header->initVelPosAmplifier;
    emtr->initVelAxisAmplifier = emtr->resource->header->initVelAxisAmplifier;
    emtr->baseScale = emtr->resource->header->baseScale;
    emtr->particleLifeTime = emtr->resource->header->particleLifeTime;

    emtr->color = GX_RGB(31, 31, 31);
    emtr->misc.emissionInterval = emtr->resource->header->misc.emissionInterval;
    emtr->misc.baseAlpha = emtr->resource->header->misc.baseAlpha;
    emtr->misc.updateCycle = 0;
    emtr->misc.reserved = 0;
    emtr->collisionPlaneHeight = FX32_MIN;
    emtr->textureS = FX32_ONE << emtr->resource->header->misc.textureTileCountS;
    emtr->textureT = FX32_ONE << emtr->resource->header->misc.textureTileCountT;

    if (emtr->resource->header->misc.flipTextureS) {
        emtr->textureS *= -1;
    }

    if (emtr->resource->header->misc.flipTextureT) {
        emtr->textureT *= -1;
    }

    if (emtr->resource->header->flags.hasChildResource) {
        emtr->childTextureS = FX32_ONE << emtr->resource->childResource->misc.textureTileCountS;
        emtr->childTextureT = FX32_ONE << emtr->resource->childResource->misc.textureTileCountT;

        if (emtr->resource->childResource->misc.flipTextureS) {
            emtr->childTextureS *= -1;
        }

        if (emtr->resource->childResource->misc.flipTextureT) {
            emtr->childTextureT *= -1;
        }
    }

    emtr->next = emtr->prev = NULL;
    emtr->particles.first = emtr->childParticles.first = NULL;
    emtr->particles.count = emtr->childParticles.count = 0;
    emtr->updateCallback = NULL;
    emtr->userDataPtr = NULL;
    emtr->userData.u32 = 0;
}

void SPLEmitter_Update(SPLManager *mgr, SPLEmitter *emtr)
{
    SPLParticle *ptcl;
    SPLParticle *next;
    SPLResource *res;
    SPLResourceHeader *header;
    SPLChildResource *child;
    SPLResourceFlags resFlags;
    AnimFunc animFuncs[4];
    AnimFunc childAnimFuncs[4];
    int i, animCount, behaviorCount;
    int airResistance;
    u8 lifeRates[2];
    VecFx32 acc;

    res = emtr->resource;
    child = res->childResource;
    animCount = 0;
    header = res->header;
    resFlags = header->flags;
    behaviorCount = res->behaviorCount;
    airResistance = header->misc.airResistance + FX32_CONST(0.09375);

    if (emtr->updateCallback) {
        emtr->updateCallback(emtr, SPL_CALLBACK_PRE_UPDATE);
    }

    if (header->emitterLifeTime == 0 || emtr->age < header->emitterLifeTime) {
        if (emtr->age % emtr->misc.emissionInterval == 0) {
            if (!emtr->state.terminate && !emtr->state.emissionPaused && emtr->state.started) {
                SPLEmitter_EmitParticles(emtr, &mgr->inactiveParticles);
            }
        }
    }

    if (resFlags.hasScaleAnim) {
        animFuncs[animCount].func = SPLAnim_Scale;
        animFuncs[animCount++].loop = res->scaleAnim->flags.loop;
    }

    if (resFlags.hasColorAnim && !res->colorAnim->flags.randomStartColor) {
        animFuncs[animCount].func = SPLAnim_Color;
        animFuncs[animCount++].loop = res->colorAnim->flags.loop;
    }

    if (resFlags.hasAlphaAnim) {
        animFuncs[animCount].func = SPLAnim_Alpha;
        animFuncs[animCount++].loop = res->alphaAnim->flags.loop;
    }

    if (resFlags.hasTexAnim && !res->texAnim->param.randomizeInit) {
        animFuncs[animCount].func = SPLAnim_Texture;
        animFuncs[animCount++].loop = res->texAnim->param.loop;
    }

    for (ptcl = emtr->particles.first; ptcl != NULL; ptcl = next) {
        next = ptcl->next;

        // For non-looping particles, "life rate" is a fraction of the particle's lifetime, represented as a u8.
        // where 0 is the start of the particle's life and 255 is the end
        // For looping particles, it's a fraction of the number of frames in the loop
        // See the SPLParticle struct for more info
        lifeRates[ANIM_FUNC_NO_LOOP] = (ptcl->lifeTimeFactor * ptcl->age) >> 8;
        lifeRates[ANIM_FUNC_LOOP] = ptcl->lifeRateOffset + ((ptcl->loopTimeFactor * ptcl->age) >> 8);

        for (i = 0; i < animCount; i++) {
            animFuncs[i].func(ptcl, res, lifeRates[animFuncs[i].loop]);
        }

        acc.x = acc.y = acc.z = 0;

        if (resFlags.followEmitter) {
            ptcl->emitterPos = emtr->position;
        }

        for (i = 0; i < behaviorCount; i++) {
            res->behaviors[i].applyFunc(res->behaviors[i].object, ptcl, &acc, emtr);
        }

        ptcl->rotation += ptcl->angularVelocity;

        ptcl->velocity.x = ptcl->velocity.x * airResistance >> 9;
        ptcl->velocity.y = ptcl->velocity.y * airResistance >> 9;
        ptcl->velocity.z = ptcl->velocity.z * airResistance >> 9;

        ptcl->velocity.x += acc.x;
        ptcl->velocity.y += acc.y;
        ptcl->velocity.z += acc.z;

        ptcl->position.x += ptcl->velocity.x + emtr->velocity.x;
        ptcl->position.y += ptcl->velocity.y + emtr->velocity.y;
        ptcl->position.z += ptcl->velocity.z + emtr->velocity.z;

        if (resFlags.hasChildResource) {
            fx32 emissionDelay = FX_MUL((fx32)ptcl->lifeTime << FX32_SHIFT, (fx32)child->misc.emissionDelay << FX32_SHIFT);

            // The >> 8 here is a division by 256 because emissionDelay is a fraction of the particle's lifetime represented as a u8
            fx32 diff = ((fx32)ptcl->age * FX32_ONE) - (emissionDelay >> 8);

            if (diff >= 0 && ((diff >> FX32_SHIFT) % child->misc.emissionInterval == 0)) {
                SPLEmitter_EmitChildren(ptcl, emtr, &mgr->inactiveParticles);
            }
        }

        if (emtr->resource->header->flags.hasFixedPolygonID) {
            ptcl->visibility.currentPolygonID = mgr->polygonID.fix;
        } else {
            ptcl->visibility.currentPolygonID = mgr->polygonID.current;
            mgr->polygonID.current += 1;

            if (mgr->polygonID.current > mgr->polygonID.max) {
                mgr->polygonID.current = mgr->polygonID.min;
            }
        }

        ptcl->age += 1;

        if (ptcl->age > ptcl->lifeTime) {
            SPLParticle *erased = SPLParticleList_Erase(&emtr->particles, ptcl);
            SPLParticleList_PushFront(&mgr->inactiveParticles, erased);
        }
    }

    if (resFlags.hasChildResource) {
        animCount = 0;
        if (child->flags.hasScaleAnim) {
            childAnimFuncs[animCount].func = SPLAnim_ChildScale;
            childAnimFuncs[animCount++].loop = FALSE;
        }

        if (child->flags.hasAlphaAnim) {
            childAnimFuncs[animCount].func = SPLAnim_ChildAlpha;
            childAnimFuncs[animCount++].loop = FALSE;
        }

        if (!child->flags.usesBehaviors) {
            behaviorCount = 0;
        }

        for (ptcl = emtr->childParticles.first; ptcl != NULL; ptcl = next) {
            next = ptcl->next;

            // "life rate" is a fraction of the particle's lifetime, represented as a u8
            // where 0 is the start of the particle's life and 255 is the end
            lifeRates[0] = (ptcl->age << 8) / ptcl->lifeTime;
            for (i = 0; i < animCount; i++) {
                childAnimFuncs[i].func(ptcl, res, lifeRates[0]);
            }

            acc.x = acc.y = acc.z = 0;

            if (child->flags.followEmitter) {
                ptcl->emitterPos = emtr->position;
            }

            for (i = 0; i < behaviorCount; i++) {
                res->behaviors[i].applyFunc(res->behaviors[i].object, ptcl, &acc, emtr);
            }

            ptcl->rotation += ptcl->angularVelocity;

            ptcl->velocity.x = ptcl->velocity.x * airResistance >> 9;
            ptcl->velocity.y = ptcl->velocity.y * airResistance >> 9;
            ptcl->velocity.z = ptcl->velocity.z * airResistance >> 9;

            ptcl->velocity.x += acc.x;
            ptcl->velocity.y += acc.y;
            ptcl->velocity.z += acc.z;

            ptcl->position.x += ptcl->velocity.x + emtr->velocity.x;
            ptcl->position.y += ptcl->velocity.y + emtr->velocity.y;
            ptcl->position.z += ptcl->velocity.z + emtr->velocity.z;

            if (emtr->resource->header->flags.childHasFixedPolygonID) {
                ptcl->visibility.currentPolygonID = mgr->polygonID.fix;
            } else {
                ptcl->visibility.currentPolygonID = mgr->polygonID.current;
                mgr->polygonID.current += 1;

                if (mgr->polygonID.current > mgr->polygonID.max) {
                    mgr->polygonID.current = mgr->polygonID.min;
                }
            }

            ptcl->age += 1;

            if (ptcl->age > ptcl->lifeTime) {
                SPLParticle *erased = SPLParticleList_Erase(&emtr->childParticles, ptcl);
                SPLParticleList_PushFront(&mgr->inactiveParticles, erased);
            }
        }
    }

    emtr->age += 1;

    if (emtr->updateCallback) {
        emtr->updateCallback(emtr, SPL_CALLBACK_POST_UPDATE);
    }
}

static void SPLManager_DrawParticles(SPLManager *mgr)
{
    SPLEmitter *emtr = mgr->renderState.emitter;
    SPLResourceHeader *header = emtr->resource->header;
    DrawFunc drawFunc = NULL;

    SPLUtil_SetTexture(mgr->textures + header->misc.textureIndex);

    switch (header->flags.drawType) {
    case SPL_DRAW_TYPE_BILLBOARD:
        drawFunc = SPLDraw_Billboard;
        break;
    case SPL_DRAW_TYPE_DIRECTIONAL_BILLBOARD:
        drawFunc = SPLDraw_DirectionalBillboard;
        break;
    case SPL_DRAW_TYPE_POLYGON:
        drawFunc = SPLDraw_Polygon;
        break;
    case SPL_DRAW_TYPE_DIRECTIONAL_POLYGON:
        drawFunc = SPLDraw_DirectionalPolygon;
        break;
    case SPL_DRAW_TYPE_DIRECTIONAL_POLYGON_CENTER:
        drawFunc = SPLDraw_DirectionalPolygon;
        break;
    }

    SetTexFunc setTexFunc = header->flags.hasTexAnim ? SPLUtil_SetTexture : SPLUtil_SetTexture_Stub;

    for (SPLParticle *ptcl = emtr->particles.first; ptcl != NULL; ptcl = ptcl->next) {
        setTexFunc(mgr->textures + ptcl->texture);
        drawFunc(mgr, ptcl);
    }
}

static void SPLManager_DrawChildParticles(SPLManager *mgr)
{
    SPLEmitter *emtr = mgr->renderState.emitter;
    SPLResource *res = emtr->resource;
    DrawFunc drawFunc = NULL;

    if (!res->header->flags.hasChildResource) {
        return;
    }

    SPLUtil_SetTexture(mgr->textures + res->childResource->misc.texture);

    switch (res->childResource->flags.drawType) {
    case SPL_DRAW_TYPE_BILLBOARD:
        drawFunc = SPLDraw_Child_Billboard;
        break;
    case SPL_DRAW_TYPE_DIRECTIONAL_BILLBOARD:
        drawFunc = SPLDraw_Child_DirectionalBillboard;
        break;
    case SPL_DRAW_TYPE_POLYGON:
        drawFunc = SPLDraw_Child_Polygon;
        break;
    case SPL_DRAW_TYPE_DIRECTIONAL_POLYGON:
        drawFunc = SPLDraw_Child_DirectionalPolygon;
        break;
    case SPL_DRAW_TYPE_DIRECTIONAL_POLYGON_CENTER:
        drawFunc = SPLDraw_Child_DirectionalPolygon;
        break;
    }

    for (SPLParticle *ptcl = emtr->childParticles.first; ptcl != NULL; ptcl = ptcl->next) {
        drawFunc(mgr, ptcl);
    }
}

void SPLManager_DoDraw(SPLManager *mgr)
{
    SPLResourceHeader *header = mgr->renderState.emitter->resource->header;

    if (header->flags.drawChildrenFirst) {
        SPLManager_DrawChildParticles(mgr);

        if (!header->flags.hideParent) {
            SPLManager_DrawParticles(mgr);
        }
    } else {
        if (!header->flags.hideParent) {
            SPLManager_DrawParticles(mgr);
        }

        SPLManager_DrawChildParticles(mgr);
    }

    // fx_particles hook (v2): spawn embers from this emitter's parents.
    // The persistent ember store is drawn once per manager in
    // SPLManager_Draw (see SPLManager_DrawBoostEmbers below), so the
    // embers briefly outlive their parent instead of dying with the frame.
    if (!header->flags.hideParent) {
        SPLManager_SpawnBoostEmbers(mgr);
    }
}

// Lane particles (v2): spawn one ember per live parent, with probability
// budget/8. Large / ring / flash parents are excluded: a parent whose
// effective scale is over the cap, or whose texture is over 64 texels,
// never spawns (that is what kept the Mega emblem rings from cloning
// into ghost rings in v1). The ember inherits the parent colour and
// texture, a share of its velocity, and the element behaviour for its
// type; it then lives on its own in the manager's store.
static void SPLManager_SpawnBoostEmbers(SPLManager *mgr)
{
    SPLEmitter *emtr = mgr->renderState.emitter;
    SPLResourceHeader *header = emtr->resource->header;
    SPLBoostParams params;
    const MtxFx43 *cmr = mgr->renderState.viewMatrix;
    int budget;
    int spawnedParents = 0;

    SPLBoost_GetParams(&params);

    budget = params.density;
    if (budget > 8) {
        budget = 8;
    }

    if (!params.enabled || budget <= 0 || cmr == NULL || mgr->boostStore == NULL) {
        return;
    }

    for (SPLParticle *ptcl = emtr->particles.first; ptcl != NULL; ptcl = ptcl->next) {
        VecFx32 world;
        fx32 alpha, scl;
        int texIndex;
        SPLTexture *tex;
        u32 seed, state;
        SPLBoostEmber ember;
        int r, g, b;
        int jitterRange;
        int debug;

        if (spawnedParents >= 96) {
            break;
        }

        spawnedParents++;

        alpha = (fx32)(ptcl->visibility.baseAlpha * (ptcl->visibility.animAlpha + 1)) >> 5;
        if (alpha == 0) {
            continue;
        }

        if (header->flags.useViewSpace) {
            world.x = ptcl->position.x + ptcl->emitterPos.x - header->emitterBasePos.x;
            world.y = ptcl->position.y + ptcl->emitterPos.y - header->emitterBasePos.y;
            world.z = ptcl->position.z + ptcl->emitterPos.z - header->emitterBasePos.z;
        } else {
            world.x = ptcl->position.x + ptcl->emitterPos.x;
            world.y = ptcl->position.y + ptcl->emitterPos.y;
            world.z = ptcl->position.z + ptcl->emitterPos.z;
        }

        scl = ptcl->baseScale;
        if (header->misc.scaleAnimDir != SPL_SCALE_ANIM_DIR_X) {
            scl = FX_MUL(scl, ptcl->animScale);
        }

        texIndex = header->flags.hasTexAnim ? ptcl->texture : (int)header->misc.textureIndex;
        tex = &mgr->textures[texIndex];

        // Exclusion: big parents (rings, flashes, emblems) and big
        // textures never clone. Only small sparks/flames/embers do.
        debug = getenv("SIM_PARTICLES_DEBUG") != NULL && (params.frame % 60) == 0 && spawnedParents <= 3;
        if (debug) {
            fprintf(stderr, "[particles-dbg] frame=%d res=%d scl=%d tex=%dx%d excl=%d type=%d\n",
                params.frame, (int)(emtr->resource - mgr->resources), (int)scl,
                (int)tex->width, (int)tex->height,
                (scl > 12288 || tex->width > 64 || tex->height > 64) ? 1 : 0, params.type);
        }
        if (scl > 12288 || tex->width > 64 || tex->height > 64) {
            continue;
        }

        seed = (u32)(world.x ^ (world.y << 1) ^ (world.z >> 4) ^ ((u32)ptcl->age << 16) ^ (u32)(ptcl->position.x >> 8));
        if ((int)(SPLBoost_Hash(seed ^ (u32)params.frame) % 8) >= budget) {
            continue;
        }

        state = SPLBoost_Hash(seed);
        memset(&ember, 0, sizeof(ember));

        jitterRange = (int)FX_MUL(scl, (fx32)params.spread256 * 16);
        ember.pos.x = world.x + SPLBoost_Jitter(&state, jitterRange);
        ember.pos.y = world.y + SPLBoost_Jitter(&state, jitterRange);
        ember.pos.z = world.z + SPLBoost_Jitter(&state, jitterRange >> 2);
        ember.basePos = header->emitterBasePos;
        ember.useViewSpace = header->flags.useViewSpace ? 1 : 0;
        ember.texIndex = texIndex;
        ember.texS = emtr->textureS;
        ember.texT = emtr->textureT;
        ember.type = params.type;
        ember.seed = seed;

        r = GX_RGB_R_(ptcl->color) * GX_RGB_R_(emtr->color) >> 5;
        g = GX_RGB_G_(ptcl->color) * GX_RGB_G_(emtr->color) >> 15;
        b = GX_RGB_B_(ptcl->color) * GX_RGB_B_(emtr->color) >> 25;
        r += (31 - r) * params.brighten256 >> 8;
        g += (31 - g) * params.brighten256 >> 8;
        b += (31 - b) * params.brighten256 >> 8;

        switch (params.type) {
        case SPL_BOOST_TYPE_FIRE:
            ember.vel.x = ptcl->velocity.x / 5 + SPLBoost_Jitter(&state, 328);
            ember.vel.y = ptcl->velocity.y / 5 + 655 + (int)(SPLBoost_Hash(state) % 492);
            ember.vel.z = ptcl->velocity.z / 5 + SPLBoost_Jitter(&state, 328);
            ember.maxLife = 12 + (int)(SPLBoost_Hash(state) % 7);
            r += 6;
            break;
        case SPL_BOOST_TYPE_ELECTRIC:
            ember.vel.x = ptcl->velocity.x / 10 + SPLBoost_Jitter(&state, 2253);
            ember.vel.y = ptcl->velocity.y / 10 + SPLBoost_Jitter(&state, 2253);
            ember.vel.z = ptcl->velocity.z / 10 + SPLBoost_Jitter(&state, 1434);
            ember.maxLife = 10 + (int)(SPLBoost_Hash(state) % 7);
            r += 4;
            g += 4;
            break;
        case SPL_BOOST_TYPE_ICE:
            ember.vel.x = ptcl->velocity.x * 15 / 100 + SPLBoost_Jitter(&state, 410);
            ember.vel.y = ptcl->velocity.y * 15 / 100 - 82 - (int)(SPLBoost_Hash(state) % 164);
            ember.vel.z = ptcl->velocity.z * 15 / 100 + SPLBoost_Jitter(&state, 410);
            ember.maxLife = 12 + (int)(SPLBoost_Hash(state) % 9);
            r += 2;
            g += 2;
            b += 6;
            break;
        case SPL_BOOST_TYPE_MEGA:
            ember.vel.x = ptcl->velocity.x / 10 + SPLBoost_Jitter(&state, 1024);
            ember.vel.y = ptcl->velocity.y / 10 + 205 + (int)(SPLBoost_Hash(state) % 410);
            ember.vel.z = ptcl->velocity.z / 10 + SPLBoost_Jitter(&state, 1024);
            ember.maxLife = 14 + (int)(SPLBoost_Hash(state) % 9);
            r += 4;
            g += 4;
            b += 4;
            break;
        default:
            ember.vel.x = ptcl->velocity.x / 4 + SPLBoost_Jitter(&state, 492);
            ember.vel.y = ptcl->velocity.y / 4 + SPLBoost_Jitter(&state, 492);
            ember.vel.z = ptcl->velocity.z / 4 + SPLBoost_Jitter(&state, 328);
            ember.maxLife = 10 + (int)(SPLBoost_Hash(state) % 7);
            break;
        }

        if (r > 31) {
            r = 31;
        }
        if (g > 31) {
            g = 31;
        }
        if (b > 31) {
            b = 31;
        }
        ember.r = r;
        ember.g = g;
        ember.b = b;
        ember.life = ember.maxLife;
        ember.sizeFx = (fx32)(7 + SPLBoost_Hash(state) % 7) * FX32_ONE / 100;

        SPLBoost_SpawnEmber(mgr->boostStore, &ember);
    }
}

// Lane particles (v2): age and draw this manager's ember store. Called
// once per manager per drawn frame from SPLManager_Draw. The dots are
// tiny squares (1-2 px at DS scale) sampling the centre texel window of
// the parent texture, so they read as pixel-styled sparks, not smooth
// blobs. Polygon ID 63 keeps them out of the parents' translucency
// grouping; they sit in the 3D layer, under the 2D text and healthboxes.
void SPLManager_DrawBoostEmbers(SPLManager *mgr)
{
    SPLBoostParams params;
    const MtxFx43 *cmr = mgr->renderState.viewMatrix;
    int i;

    SPLBoost_GetParams(&params);

    if (!params.enabled) {
        if (mgr->boostStore != NULL) {
            mgr->boostStore->count = 0;
            mgr->boostStore->next = 0;
        }
        return;
    }

    if (cmr == NULL || mgr->boostStore == NULL) {
        return;
    }

    SPLBoost_Update(mgr->boostStore);

    for (i = 0; i < mgr->boostStore->count; i++) {
        SPLBoostEmber *ember = &mgr->boostStore->embers[i];
        VecFx32 trs;
        MtxFx43 load;
        fx32 sin, cos;
        int alpha;

        if (ember->life <= 0 || ember->maxLife <= 0) {
            continue;
        }

        alpha = 6 + 22 * ember->life / ember->maxLife;
        if ((ember->type == SPL_BOOST_TYPE_ICE || ember->type == SPL_BOOST_TYPE_MEGA)
            && ((ember->seed + (u32)ember->life) & 3) == 0) {
            alpha /= 2; // glitter twinkle
        }
        if (alpha < 1) {
            alpha = 1;
        } else if (alpha > 31) {
            alpha = 31;
        }

        MTX_MultVec43(&ember->pos, cmr, &trs);

        sin = FX_SinIdx((u16)(ember->seed & 0xFFFF));
        cos = FX_CosIdx((u16)(ember->seed & 0xFFFF));

        load.m[0][0] = FX_MUL(cos, ember->sizeFx);
        load.m[0][1] = FX_MUL(sin, ember->sizeFx);
        load.m[0][2] = 0;
        load.m[1][0] = FX_MUL(-sin, ember->sizeFx);
        load.m[1][1] = FX_MUL(cos, ember->sizeFx);
        load.m[1][2] = 0;
        load.m[2][0] = 0;
        load.m[2][1] = 0;
        load.m[2][2] = FX32_ONE;
        load.m[3][0] = trs.x;
        load.m[3][1] = trs.y;
        load.m[3][2] = trs.z;

        SPLUtil_SetTexture(mgr->textures + ember->texIndex);

        G3_PolygonAttr(
            GX_LIGHTMASK_NONE,
            GX_POLYGONMODE_MODULATE,
            GX_CULL_NONE,
            63,
            (u32)alpha,
            mgr->miscPolygonAttr);

        reg_G3_POLYGON_ATTR;

        G3_Color(GX_RGB(ember->r, ember->g, ember->b));

        G3_Identity();
        if (ember->useViewSpace) {
            G3_Translate(ember->basePos.x, ember->basePos.y, ember->basePos.z);
        }
        G3_MultMtx43(&load);

        G3_Begin(GX_BEGIN_QUADS);
        G3_TexCoord(ember->texS * 45 / 100, ember->texT * 45 / 100);
        G3_Vtx10(0 - FX32_ONE, 0 + FX32_ONE, 0);
        G3_TexCoord(ember->texS * 55 / 100, ember->texT * 45 / 100);
        G3_Vtx10(0 + FX32_ONE, 0 + FX32_ONE, 0);
        G3_TexCoord(ember->texS * 55 / 100, ember->texT * 55 / 100);
        G3_Vtx10(0 + FX32_ONE, 0 - FX32_ONE, 0);
        G3_TexCoord(ember->texS * 45 / 100, ember->texT * 55 / 100);
        G3_Vtx10(0 - FX32_ONE, 0 - FX32_ONE, 0);
        G3_End();
    }
}

void SPLEmitter_Emit(SPLEmitter *emtr, SPLParticleList *list)
{
    SPLEmitter_EmitParticles(emtr, list);
}

void SPLUtil_SetCylinderEmitterDir(SPLEmitter *emtr, VecFx32 *p1, VecFx32 *p2)
{
    VecFx32 vex;

    if (emtr->resource->header->flags.emissionType == 6 || emtr->resource->header->flags.emissionType == 7) {
        emtr->position.x = (p2->x + p1->x) / 2;
        emtr->position.y = (p2->y + p1->y) / 2;
        emtr->position.z = (p2->z + p1->z) / 2;
        emtr->length = VEC_Distance(p1, p2) / 2;

        vex.x = p2->x - p1->x;
        vex.y = p2->y - p1->y;
        vex.z = p2->z - p1->z;
        VEC_Normalize(&vex, &vex);

        emtr->axis.x = (fx16)vex.x;
        emtr->axis.y = (fx16)vex.y;
        emtr->axis.z = (fx16)vex.z;
    }
}
