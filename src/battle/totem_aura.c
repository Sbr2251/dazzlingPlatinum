#include "battle/totem_aura.h"

#include <nitro.h>

#include "constants/battle.h"
#include "constants/heap.h"
#include "generated/battle_mon_params.h"
#include "generated/pokemon_types.h"

#include "battle/battle_lib.h"
#include "battle/battle_stage.h"
#include "battle/battle_system.h"
#include "struct_defs/battle_system.h"
#include "battle_anim/battle_anim_system.h"
#include "battle_anim/battle_anim_util.h"
#include "overlay011/particle_helper.h"

#include "port/postfx.h"

#include "camera.h"
#include "heap.h"
#include "totem_battle.h"
#include "narc.h"
#include "particle_system.h"
#include "pokemon_sprite.h"
#include "spl.h"
#include "sys_task.h"
#include "sys_task_manager.h"
#include "system.h"

#include "res/graphics/battle/particles/battle_particles.naix"

// Emitters 0-2 of totem_aura.spa never expire; emitter 3 is the one-shot flare played by the aura animation
#define TOTEM_AURA_EMITTERS 3

// The particle camera's orthographic view is 8 world units tall across the 192-pixel screen
#define TOTEM_AURA_PIXEL (FX32_ONE / 24)

// After the Totem is knocked out, how long the last flames get to burn out before the system is freed
#define TOTEM_AURA_FADE_FRAMES 40

// Flare-up cinematic length in rendered frames at 60 fps: ~3.5 s for the Totem, ~1.7 s for an ally.
// Skippable with A/B once TOTEM_FLARE_SKIP_FRAME has passed.
#define TOTEM_FLARE_FRAMES      210
#define TOTEM_FLARE_ALLY_FRAMES 100
#define TOTEM_FLARE_SKIP_FRAME  30

// How long a hit/move intensity flare lasts, and the dissipating burst on faint
#define TOTEM_HIT_FLARE_FRAMES 24
#define TOTEM_FAINT_BURST_FRAMES 12

// Breath cycle of the persistent aura (frames for one slow inhale/exhale)
#define TOTEM_BREATH_FRAMES 240

typedef struct TotemAura {
    BattleSystem *battleSys;
    int battler;
    PokemonSprite *sprite;
    ParticleSystem *particleSystem;
    SPLEmitter *emitters[TOTEM_AURA_EMITTERS];
    VecFx32 basePos;
    s16 baseSpriteX;
    s16 baseSpriteY;
    u8 fadeTimer;
    BOOL isAlly;
    BOOL fxActive; // this aura currently owns the BattleStage brightness/fade fallback FX
    u16 frame; // frames since the aura started
    u16 flareFrame; // frames since the flare started; flareDuration once the flare is over
    u16 flareDuration;
    u16 hitFlareTimer; // >0 while a hit/move intensity flare is running (counts down)
    int prevHP;
    int maxHP;
    BOOL prevMoveActive;
    BOOL faintBurstDone;
    fx32 baseEmission[TOTEM_AURA_EMITTERS];
    fx32 baseScale[TOTEM_AURA_EMITTERS];
    GXRgb auraColor; // type-tinted flame colour (blended towards white, see AuraColorForType)
} TotemAura;

static SysTask *sTotemAuraTasks[MAX_BATTLERS];
static TotemAura *sTotemAuras[MAX_BATTLERS];

// ---------------------------------------------------------------------------
// Screen FX, through mega-cine's PostFX API (include/port/postfx.h, game commit
// 81e63c60be + libntr fe200d0, cherry-picked). PostFX coordinates cover the
// combined display (top screen y 0-191); the Totem sits near (185, 55) there.
// PostFX has no plain brightness, so the dim beat keeps the BattleStage
// brightness fallback alongside the PostFX vignette tint.
// ---------------------------------------------------------------------------

// Radial shockwave + heat haze + shake at the Totem on the burst beat.
static void TotemFX_Shockwave(TotemAura *aura, int strength, int frames)
{
    (void)aura;
    PostFX_Shockwave(185, 55, strength * 0.12f, frames);
    PostFX_ZoomBlur(185, 55, 0.22f, frames); // heat haze
    PostFX_Glow(0.45f, frames);
    PostFX_Shake(strength * 0.15f, frames > 12 ? 12 : frames);
    BattleStage_CameraShake(strength, frames);
}

static void TotemFX_Vignette(TotemAura *aura, u16 color, int amount)
{
    float r = (float)((color >> 10) & 0x1F) / 31.0f;
    float g = (float)((color >> 5) & 0x1F) / 31.0f;
    float b = (float)(color & 0x1F) / 31.0f;

    (void)aura;
    // Refreshed every flare frame with a short tail, so the tint holds while
    // the driver calls this and decays on its own once it stops.
    PostFX_Vignette(r, g, b, amount / 16.0f * 0.85f, 4);
    BattleStage_SetBackdropFade(color, amount);
}

static void TotemFX_Dim(TotemAura *aura, int brightness)
{
    (void)aura;
    BattleStage_SetBrightness(brightness);
}

static void TotemFX_Clear(TotemAura *aura)
{
    if (!aura->fxActive) {
        return;
    }

    aura->fxActive = FALSE;
    PostFX_Clear();
    BattleStage_SetBrightness(0);
    BattleStage_SetBackdropFade(0, 0);
    BattleStage_SetBackdropShake(0, 0);
}

// Map a Pokemon type to a flame colour. The SPA's flames are already orange-gold, and the
// emitter colour multiplies the particle colour, so pure saturated tints go muddy (orange x
// blue); blending 50% towards white keeps every Totem's hue readable over the same art.
static GXRgb TotemAura_ColorForType(int type)
{
    int r = 31, g = 22, b = 8; // Totem gold (default / unknown)

    switch (type) {
    case TYPE_NORMAL: r = 31; g = 28; b = 20; break;
    case TYPE_FIGHTING: r = 31; g = 12; b = 6; break;
    case TYPE_FLYING: r = 18; g = 24; b = 31; break;
    case TYPE_POISON: r = 24; g = 8; b = 28; break;
    case TYPE_GROUND: r = 28; g = 20; b = 10; break;
    case TYPE_ROCK: r = 24; g = 18; b = 10; break;
    case TYPE_BUG: r = 14; g = 28; b = 8; break;
    case TYPE_GHOST: r = 18; g = 12; b = 30; break;
    case TYPE_STEEL: r = 26; g = 28; b = 30; break;
    case TYPE_FIRE: r = 31; g = 14; b = 4; break;
    case TYPE_WATER: r = 6; g = 16; b = 31; break;
    case TYPE_GRASS: r = 10; g = 28; b = 10; break;
    case TYPE_ELECTRIC: r = 31; g = 28; b = 6; break;
    case TYPE_PSYCHIC: r = 31; g = 12; b = 22; break;
    case TYPE_ICE: r = 16; g = 28; b = 31; break;
    case TYPE_DRAGON: r = 14; g = 10; b = 31; break;
    case TYPE_DARK: r = 12; g = 10; b = 16; break;
    case TYPE_FAIRY: r = 31; g = 20; b = 26; break;
    default: break;
    }

    return GX_RGB((r + 31) / 2, (g + 31) / 2, (b + 31) / 2);
}

// Between moves the battle turns 2D blending off entirely, and without 2nd targets the 3D layer drops per-pixel
// alpha, so the soft flames render as solid blocks. Keep the same targets a move animation uses while idle; with
// no 1st target selected this only affects translucent 3D pixels.
// This task keeps running while the trainer AI or the party/bag menus sit where the battle_anim overlay's code
// lives, so it must never call into that overlay: read the anim system's flag directly instead.
static void TotemAura_KeepTranslucent(TotemAura *aura)
{
    if (reg_G2_BLDCNT == 0 && BattleSystem_GetBattleAnimSystem(aura->battleSys)->moveActive == FALSE) {
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

// 0..256 breath wave (256 = full inhale) over TOTEM_BREATH_FRAMES, triangle-shaped so no
// floating point or trig tables are needed.
static int TotemAura_Breath(TotemAura *aura)
{
    int phase = aura->frame % TOTEM_BREATH_FRAMES;
    int half = TOTEM_BREATH_FRAMES / 2;

    if (phase < half) {
        return phase * 256 / half;
    }

    return (TOTEM_BREATH_FRAMES - phase) * 256 / half;
}

// Per-frame layered modulation of the persistent aura. All adjustments are relative to the
// emitter values captured at creation, scaled by 256ths, so the particle budget stays bounded
// (worst case below is ~2.6x the authored emission of three emitters, still one SPA system).
//  emitter 0: slow outer flame licks - follows the breath, swells when enraged
//  emitter 1: inner glow - scale pulses with the breath
//  emitter 2: rising embers - sparse at rest, dense when enraged or flaring
static void TotemAura_Modulate(TotemAura *aura)
{
    BattleContext *battleCtx = BattleSystem_GetBattleContext(aura->battleSys);
    int curHP = BattleMon_Get(battleCtx, aura->battler, BATTLEMON_CUR_HP, NULL);
    int breath = TotemAura_Breath(aura); // 0..256
    // Enrage: 256 at full HP, up to 512 at 0 HP; the slope steepens below 50% HP.
    int enrage = 256;

    if (aura->maxHP > 0 && curHP >= 0) {
        int hpPct = curHP * 100 / aura->maxHP;

        if (hpPct < 50) {
            enrage = 256 + (50 - hpPct) * 256 / 50;
        }
    }

    // Hit/move flare envelope: 256 at the trigger frame decaying to 0.
    int flare = 0;

    if (aura->hitFlareTimer > 0) {
        flare = aura->hitFlareTimer * 256 / TOTEM_HIT_FLARE_FRAMES;
    }

    // Dissipating burst on faint: one bright spike, then the flames starve.
    int burst = 256;

    if (aura->fadeTimer > 0) {
        burst = (aura->fadeTimer <= TOTEM_FAINT_BURST_FRAMES)
            ? 256 + (TOTEM_FAINT_BURST_FRAMES - aura->fadeTimer) * 32
            : 64;
    }

    int allyScale = aura->isAlly ? 160 : 256; // allies burn at ~60% intensity

    for (int i = 0; i < TOTEM_AURA_EMITTERS; i++) {
        SPLEmitter *emitter = aura->emitters[i];

        if (emitter == NULL) {
            continue;
        }

        int mult = 256;

        switch (i) {
        case 0: mult = (192 + breath / 4) * enrage / 256; break;
        case 1: mult = 256 + breath / 8; break;
        default: mult = (128 + breath / 8) * enrage / 256; break;
        }

        mult = mult * (256 + flare) / 256;
        mult = mult * burst / 256;
        mult = mult * allyScale / 256;

        emitter->emissionCount = aura->baseEmission[i] * mult / 256;
        emitter->color = aura->auraColor;

        // Only the inner glow breathes in scale; the ally's whole wreath is smaller.
        if (i == 1) {
            emitter->baseScale = aura->baseScale[i] * (230 + breath / 4) / 256 * allyScale / 256;
        } else if (aura->isAlly) {
            emitter->baseScale = aura->baseScale[i] * allyScale / 256;
        }
    }
}

// The flare-up cinematic driver. The anim script (totem_aura.s) owns the camera, sprite
// fades, sounds and the one-shot burst emitter; this driver owns the dim/vignette/shake
// fallback FX and the skip, keyed to the same frame count so the two stay in step.
//  Totem: 0-24 dim-in, 24-130 ignite+spiral (script emitters), 130-150 burst, 150-210 settle
//  Ally:  the same beats compressed into TOTEM_FLARE_ALLY_FRAMES, at half strength.
static void TotemAura_DriveFlare(TotemAura *aura)
{
    if (aura->flareFrame >= aura->flareDuration) {
        return;
    }

    // Skippable with A/B after the first beat.
    if (aura->flareFrame >= TOTEM_FLARE_SKIP_FRAME
        && (gSystem.pressedKeys & (PAD_BUTTON_A | PAD_BUTTON_B)) != 0) {
        aura->flareFrame = aura->flareDuration;
        TotemFX_Clear(aura);
        TotemBattle_ShowHealthbars(aura->battleSys);
        return;
    }

    aura->fxActive = TRUE;

    int t = aura->flareFrame;
    int dur = aura->flareDuration;
    // Beat boundaries scale with the (possibly ally-shortened) duration.
    int dimEnd = dur * 24 / TOTEM_FLARE_FRAMES;
    int burstAt = dur * 130 / TOTEM_FLARE_FRAMES;
    int burstEnd = dur * 150 / TOTEM_FLARE_FRAMES;
    int strength = aura->isAlly ? 2 : 4;

    if (t < dimEnd) {
        // Battle opens dim: brightness sinks, a whisper of the aura colour in the vignette.
        TotemFX_Dim(aura, -10 * t / (dimEnd > 0 ? dimEnd : 1));
        TotemFX_Vignette(aura, aura->auraColor, 6 * t / (dimEnd > 0 ? dimEnd : 1));
    } else if (t < burstAt) {
        // Ignite + spiral: hold the dim with a low vignette while the flames climb.
        TotemFX_Dim(aura, aura->isAlly ? -5 : -8);
        TotemFX_Vignette(aura, aura->auraColor, 5);
    } else if (t < burstEnd) {
        // Burst beat: one shockwave/shake on the first burst frame, white-hot flash decaying.
        if (t == burstAt) {
            TotemFX_Shockwave(aura, strength, 12);
        }

        int left = burstEnd - t;
        int span = burstEnd - burstAt > 0 ? burstEnd - burstAt : 1;
        TotemFX_Dim(aura, 12 * left / span);
        TotemFX_Vignette(aura, aura->auraColor, 8 * left / span);
    } else {
        // Settle: ease the dim/vignette home; the stat-boost message plays over this beat.
        int span = dur - burstEnd > 0 ? dur - burstEnd : 1;
        int left = dur - t;
        TotemFX_Dim(aura, -4 * left / span);
        TotemFX_Vignette(aura, aura->auraColor, 3 * left / span);
    }

    aura->flareFrame++;

    if (aura->flareFrame >= aura->flareDuration) {
        TotemFX_Clear(aura);
        BattleStage_SetBackdropShake(0, 0);
        // The flare hid the healthboxes for its close-up; bring them back as
        // the stat-boost message plays (the first-menu show beat runs earlier).
        TotemBattle_ShowHealthbars(aura->battleSys);
    }
}

static void TotemAura_Task(SysTask *task, void *data);

static void TotemAura_FreeAura(TotemAura *aura)
{
    int battler = aura->battler;

    TotemFX_Clear(aura);
    ParticleHelper_FreeParticleSystem(aura->particleSystem);
    Heap_Free(aura);

    if (battler >= 0 && battler < MAX_BATTLERS) {
        sTotemAuras[battler] = NULL;
        if (sTotemAuraTasks[battler] != NULL) {
            SysTask *task = sTotemAuraTasks[battler];
            sTotemAuraTasks[battler] = NULL;
            SysTask_Done(task);
        }
    }
}

static void TotemAura_Task(SysTask *task, void *data)
{
    (void)task;
    TotemAura *aura = data;
    BattlerData *battlerData = BattleSystem_GetBattlerData(aura->battleSys, aura->battler);
    BattleContext *battleCtx = BattleSystem_GetBattleContext(aura->battleSys);
    int curHP = BattleMon_Get(battleCtx, aura->battler, BATTLEMON_CUR_HP, NULL);
    BOOL moveActive = BattleSystem_GetBattleAnimSystem(aura->battleSys)->moveActive;

    aura->frame++;

    if (aura->fadeTimer == 0 && curHP == 0) {
        aura->fadeTimer = 1;
        aura->faintBurstDone = FALSE;
    }

    if (battlerData->monSprite != aura->sprite
        || PokemonSprite_IsActive(aura->sprite) == FALSE
        || aura->fadeTimer > TOTEM_AURA_FADE_FRAMES) {
        TotemAura_FreeAura(aura);
        return;
    }

    // Hit flare: HP dropped since last frame. Move flare: a move animation just started
    // while this battler is on the field (its own moves included - the aura surges as the
    // Totem acts, which reads correctly for the opponent's moves hitting it too via HP).
    if (aura->prevHP > 0 && curHP < aura->prevHP && curHP > 0) {
        aura->hitFlareTimer = TOTEM_HIT_FLARE_FRAMES;
    } else if (moveActive && !aura->prevMoveActive) {
        // Small surge only; the big flare is reserved for taking a hit.
        if (aura->hitFlareTimer < TOTEM_HIT_FLARE_FRAMES / 2) {
            aura->hitFlareTimer = TOTEM_HIT_FLARE_FRAMES / 2;
        }
    }

    aura->prevHP = curHP;
    aura->prevMoveActive = moveActive;

    if (aura->hitFlareTimer > 0) {
        aura->hitFlareTimer--;
    }

    // A summoned ally appears mid-battle: once the Totem is running, watch for enemy slot 2
    // taking the field and give it the smaller aura (short flare included).
    if (!aura->isAlly && aura->battler == BATTLER_ENEMY_1
        && sTotemAuras[BATTLER_ENEMY_2] == NULL
        && battleCtx->selectedPartySlot[BATTLER_ENEMY_2] != MAX_PARTY_SIZE
        && BattleMon_Get(battleCtx, BATTLER_ENEMY_2, BATTLEMON_CUR_HP, NULL) > 0) {
        BattlerData *allyData = BattleSystem_GetBattlerData(aura->battleSys, BATTLER_ENEMY_2);

        if (allyData->monSprite != NULL && PokemonSprite_IsActive(allyData->monSprite)) {
            TotemAura_StartForBattler(aura->battleSys, BATTLER_ENEMY_2);
        }
    }

    TotemAura_KeepTranslucent(aura);
    TotemAura_FollowSprite(aura);
    TotemAura_DriveFlare(aura);
    TotemAura_Modulate(aura);

    if (aura->fadeTimer > 0) {
        aura->fadeTimer++;

        if (aura->fadeTimer > TOTEM_FAINT_BURST_FRAMES) {
            TotemAura_SetEmitting(aura, FALSE, TRUE);
        } else {
            TotemAura_SetEmitting(aura, TRUE, TRUE);
        }
    } else if (PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_HIDE)) {
        TotemAura_SetEmitting(aura, FALSE, FALSE);
    } else {
        TotemAura_SetEmitting(aura, TRUE, TRUE);
    }
}

void TotemAura_StartForBattler(BattleSystem *battleSys, int battler)
{
    if (battler < 0 || battler >= MAX_BATTLERS || sTotemAuraTasks[battler] != NULL) {
        return;
    }

    BattlerData *battlerData = BattleSystem_GetBattlerData(battleSys, battler);

    if (battlerData->monSprite == NULL) {
        return;
    }

    BattleContext *battleCtx = BattleSystem_GetBattleContext(battleSys);
    TotemAura *aura = Heap_Alloc(HEAP_ID_BATTLE, sizeof(TotemAura));
    aura->battleSys = battleSys;
    aura->battler = battler;
    aura->sprite = battlerData->monSprite;
    aura->fadeTimer = 0;
    aura->isAlly = (battler == BATTLER_ENEMY_2);
    aura->fxActive = FALSE;
    aura->frame = 0;
    aura->flareFrame = 0;
    aura->flareDuration = aura->isAlly ? TOTEM_FLARE_ALLY_FRAMES : TOTEM_FLARE_FRAMES;
    aura->hitFlareTimer = 0;
    aura->prevHP = BattleMon_Get(battleCtx, battler, BATTLEMON_CUR_HP, NULL);
    aura->maxHP = BattleMon_Get(battleCtx, battler, BATTLEMON_MAX_HP, NULL);
    aura->prevMoveActive = FALSE;
    aura->faintBurstDone = FALSE;
    aura->auraColor = TotemAura_ColorForType(BattleMon_Get(battleCtx, battler, BATTLEMON_TYPE_1, NULL));
    aura->particleSystem = ParticleHelper_CreateParticleSystem(HEAP_ID_BATTLE);
    ParticleSystem_SetResource(aura->particleSystem,
        ParticleSystem_LoadResourceFromNARC(NARC_INDEX_WAZAEFFECT__EFFECTDATA__WAZA_PARTICLE, totem_aura_spa, HEAP_ID_BATTLE),
        VRAM_AUTO_RELEASE_TEXTURE_LNK | VRAM_AUTO_RELEASE_PALETTE_LNK,
        TRUE);
    ParticleSystem_SetCameraProjection(aura->particleSystem, CAMERA_PROJECTION_ORTHOGRAPHIC);

    BattleAnimUtil_GetBattlerTypeWorldPos_Normal(battlerData->battlerType, &aura->basePos, FALSE, CAMERA_PROJECTION_ORTHOGRAPHIC);
    aura->baseSpriteX = PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_X_CENTER)
        + PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_X_OFFSET);
    aura->baseSpriteY = PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_Y_CENTER)
        + PokemonSprite_GetAttribute(aura->sprite, MON_SPRITE_Y_OFFSET);

    for (int i = 0; i < TOTEM_AURA_EMITTERS; i++) {
        aura->emitters[i] = ParticleSystem_CreateEmitter(aura->particleSystem, i, &aura->basePos);
        aura->baseEmission[i] = aura->emitters[i] != NULL ? aura->emitters[i]->emissionCount : FX32_ONE;
        aura->baseScale[i] = aura->emitters[i] != NULL ? aura->emitters[i]->baseScale : FX32_ONE;

        if (aura->baseEmission[i] == 0) {
            aura->baseEmission[i] = FX32_ONE;
        }

        if (aura->baseScale[i] == 0) {
            aura->baseScale[i] = FX32_ONE;
        }
    }

    sTotemAuras[battler] = aura;
    sTotemAuraTasks[battler] = SysTask_Start(TotemAura_Task, aura, 1000);
}

void TotemAura_Start(BattleSystem *battleSys)
{
    TotemAura_StartForBattler(battleSys, BATTLER_ENEMY_1);
}

void TotemAura_StopForBattler(int battler)
{
    if (battler < 0 || battler >= MAX_BATTLERS || sTotemAuraTasks[battler] == NULL) {
        return;
    }

    TotemAura *aura = sTotemAuras[battler];
    SysTask *task = sTotemAuraTasks[battler];
    sTotemAuras[battler] = NULL;
    sTotemAuraTasks[battler] = NULL;

    TotemFX_Clear(aura);
    ParticleHelper_FreeParticleSystem(aura->particleSystem);
    Heap_Free(aura);
    SysTask_Done(task);
}

void TotemAura_Stop(void)
{
    for (int i = 0; i < MAX_BATTLERS; i++) {
        TotemAura_StopForBattler(i);
    }
}

BOOL TotemAura_IsActiveForBattler(int battler)
{
    if (battler < 0 || battler >= MAX_BATTLERS) {
        return FALSE;
    }

    return sTotemAuraTasks[battler] != NULL;
}

BOOL TotemAura_IsActive(void)
{
    for (int i = 0; i < MAX_BATTLERS; i++) {
        if (sTotemAuraTasks[i] != NULL) {
            return TRUE;
        }
    }

    return FALSE;
}

void TotemAura_NotifyHit(int battler)
{
    if (battler < 0 || battler >= MAX_BATTLERS || sTotemAuras[battler] == NULL) {
        return;
    }

    sTotemAuras[battler]->hitFlareTimer = TOTEM_HIT_FLARE_FRAMES;
}

void TotemAura_NotifyMove(int battler)
{
    if (battler < 0 || battler >= MAX_BATTLERS || sTotemAuras[battler] == NULL) {
        return;
    }

    if (sTotemAuras[battler]->hitFlareTimer < TOTEM_HIT_FLARE_FRAMES / 2) {
        sTotemAuras[battler]->hitFlareTimer = TOTEM_HIT_FLARE_FRAMES / 2;
    }
}
