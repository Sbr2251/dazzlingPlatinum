#include "battle/totem_aura.h"

#include <nitro.h>

#include "constants/battle.h"
#include "constants/heap.h"

#include "battle/battle_lib.h"
#include "battle/ov16_0223DF00.h"
#include "battle/struct_ov16_0225BFFC_t.h"
#include "battle_anim/battle_anim_system.h"
#include "battle_anim/battle_anim_util.h"
#include "battle_anim/battle_particle_util.h"

#include "camera.h"
#include "heap.h"
#include "particle_system.h"
#include "pokemon_sprite.h"
#include "spl.h"
#include "sys_task.h"
#include "sys_task_manager.h"

#include "res/battle/particles/battle_particles.naix.h"

// Emitters 0-2 of totem_aura.spa never expire; emitter 3 is the one-shot flare played by the aura animation
#define TOTEM_AURA_EMITTERS 3

// The particle camera's orthographic view is 8 world units tall across the 192-pixel screen
#define TOTEM_AURA_PIXEL (FX32_ONE / 24)

// After the Totem is knocked out, how long the last flames get to burn out before the system is freed
#define TOTEM_AURA_FADE_FRAMES 40

typedef struct TotemAura {
    BattleSystem *battleSys;
    PokemonSprite *sprite;
    ParticleSystem *particleSystem;
    SPLEmitter *emitters[TOTEM_AURA_EMITTERS];
    VecFx32 basePos;
    s16 baseSpriteX;
    s16 baseSpriteY;
    u8 fadeTimer;
} TotemAura;

static SysTask *sTotemAuraTask = NULL;

// Between moves the battle turns 2D blending off entirely, and without 2nd targets the 3D layer drops per-pixel
// alpha, so the soft flames render as solid blocks. Keep the same targets a move animation uses while idle; with
// no 1st target selected this only affects translucent 3D pixels.
static void TotemAura_KeepTranslucent(TotemAura *aura)
{
    if (reg_G2_BLDCNT == 0 && BattleAnimSystem_IsMoveActive(ov16_0223E008(aura->battleSys)) == FALSE) {
        G2_SetBlendAlpha(GX_BLEND_PLANEMASK_NONE, BATTLE_BG_BLENDMASK_ALL | GX_BLEND_PLANEMASK_OBJ | GX_BLEND_PLANEMASK_BD, 8, 8);
    }
}

static void TotemAura_SetEmitting(TotemAura *aura, BOOL emitting, BOOL visible)
{
    for (int i = 0; i < TOTEM_AURA_EMITTERS; i++) {
        if (aura->emitters[i] == NULL) {
            continue;
        }

        aura->emitters[i]->state.emissionPaused = !emitting;
        aura->emitters[i]->state.renderingDisabled = !visible;
    }
}

// Move animations shift and shake the Totem's sprite, so keep the aura centred on wherever it is now
static void TotemAura_FollowSprite(TotemAura *aura)
{
    s16 dx = PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_X_CENTER)
        + PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_X_OFFSET) - aura->baseSpriteX;
    s16 dy = PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_Y_CENTER)
        + PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_Y_OFFSET) - aura->baseSpriteY;

    for (int i = 0; i < TOTEM_AURA_EMITTERS; i++) {
        if (aura->emitters[i] == NULL) {
            continue;
        }

        SPLEmitter_SetPosX(aura->emitters[i], aura->basePos.x + dx * TOTEM_AURA_PIXEL);
        SPLEmitter_SetPosY(aura->emitters[i], aura->basePos.y - dy * TOTEM_AURA_PIXEL);
    }
}

static void TotemAura_Task(SysTask *task, void *data)
{
    TotemAura *aura = data;
    BattlerData *battlerData = BattleSystem_BattlerData(aura->battleSys, BATTLER_ENEMY_1);

    if (aura->fadeTimer == 0
        && BattleMon_Get(BattleSystem_Context(aura->battleSys), BATTLER_ENEMY_1, BATTLEMON_CUR_HP, NULL) == 0) {
        aura->fadeTimer = 1;
    }

    if (battlerData->unk_20 != aura->sprite
        || PokemonSprite_IsActive(aura->sprite) == FALSE
        || aura->fadeTimer > TOTEM_AURA_FADE_FRAMES) {
        TotemAura_Stop();
        return;
    }

    TotemAura_KeepTranslucent(aura);
    TotemAura_FollowSprite(aura);

    if (aura->fadeTimer > 0) {
        aura->fadeTimer++;
        TotemAura_SetEmitting(aura, FALSE, TRUE);
    } else if (PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_HIDE)) {
        TotemAura_SetEmitting(aura, FALSE, FALSE);
    } else {
        TotemAura_SetEmitting(aura, TRUE, TRUE);
    }
}

void TotemAura_Start(BattleSystem *battleSys)
{
    if (sTotemAuraTask != NULL) {
        return;
    }

    BattlerData *battlerData = BattleSystem_BattlerData(battleSys, BATTLER_ENEMY_1);

    if (battlerData->unk_20 == NULL) {
        return;
    }

    TotemAura *aura = Heap_Alloc(HEAP_ID_BATTLE, sizeof(TotemAura));
    aura->battleSys = battleSys;
    aura->sprite = battlerData->unk_20;
    aura->fadeTimer = 0;
    aura->particleSystem = BattleParticleUtil_CreateParticleSystem(HEAP_ID_BATTLE, totem_aura_spa, TRUE);
    ParticleSystem_SetCameraProjection(aura->particleSystem, CAMERA_PROJECTION_ORTHOGRAPHIC);

    BattleAnimUtil_GetBattlerTypeWorldPos_Normal(battlerData->battlerType, &aura->basePos, FALSE, CAMERA_PROJECTION_ORTHOGRAPHIC);
    aura->baseSpriteX = PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_X_CENTER)
        + PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_X_OFFSET);
    aura->baseSpriteY = PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_Y_CENTER)
        + PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_Y_OFFSET);

    for (int i = 0; i < TOTEM_AURA_EMITTERS; i++) {
        aura->emitters[i] = ParticleSystem_CreateEmitter(aura->particleSystem, i, &aura->basePos);
    }

    sTotemAuraTask = SysTask_Start(TotemAura_Task, aura, 1000);
}

void TotemAura_Stop(void)
{
    if (sTotemAuraTask == NULL) {
        return;
    }

    TotemAura *aura = SysTask_GetParam(sTotemAuraTask);

    BattleParticleUtil_FreeParticleSystem(aura->particleSystem);
    Heap_Free(aura);
    SysTask_Done(sTotemAuraTask);
    sTotemAuraTask = NULL;
}
