#include "battle/battle_stage_idle.h"

#include <nitro.h>
#include <string.h>

#include "config/battle_stage.h"
#include "constants/battle.h"
#include "generated/move_classes.h"
#include "generated/moves.h"

#include "battle/battle_context.h"
#include "battle/battle_stage_sprites.h"
#include "battle/battle_stage_stream.h"
#include "battle/ov16_0223DF00.h"

#include "pokemon_anim.h"
#include "pokemon_sprite.h"

// bw2vis:idle. Gen 5 motion (docs/living_battle_stage/sprites.md, "Gen 5 motion"). The B/W
// behaviour is read from the pokebw2 decomp (src/ov168/btlv_mcss.c, btlv_effect.c).

// B/W's hit flash colours (btlv_effect.c BtlvEffect_StartDamage)
#define HIT_FLASH_PHYSICAL GX_RGB(2, 2, 2)
#define HIT_FLASH_SPECIAL  GX_RGB(24, 24, 24)

// B/W's special idle: the chance at a loop end is 1 in idleCount, which counts down from 3 to
// 1 and goes back to 3 after an idle; the idle holds for one of these waits, in 60 Hz frames
// (vblanks) (btlv_mcss.c OnAnimationEnd, data_ov168_021f4184)
#define IDLE_COUNT_START 3
static const u8 sIdleWaits[] = { 48, 56, 64 };

BattleStageGen5MotionStats sGen5MotionStats;

// The special idle's own generator, so the battle's RNG (and a link battle's) is never touched
static u32 sIdleSeed;

static u32 IdleRandom(void)
{
    if (sIdleSeed == 0) {
        sIdleSeed = OS_GetVBlankCount() | 1;
    }

    sIdleSeed = sIdleSeed * 1103515245 + 12345;
    return sIdleSeed >> 16;
}

void BattleStage_Gen5MotionInit(void)
{
    int i;

    memset(&sGen5MotionStats, 0, sizeof(sGen5MotionStats));

    for (i = 0; i < MAX_MON_SPRITES; i++) {
        sGen5MotionStats.idleCount[i] = IDLE_COUNT_START;
    }
}

BOOL BattleStage_UsesGen5Motion(int battler)
{
    if (!BATTLE_STAGE_3D || battler < 0 || battler >= MAX_MON_SPRITES) {
        return FALSE;
    }

    if (BattleStageSprites_DebugFlags() & (BATTLE_STAGE_DEBUG_CLASSIC_SPRITES | BATTLE_STAGE_DEBUG_NO_SPRITE_STREAM)) {
        return FALSE;
    }

    return BattleStageSprites_StreamsLive() && BattleStageStream_HasStream(battler);
}

// The battler of a battle sprite: the battle creates each battler's at its own index
// (ov16_02263B30, PokemonSpriteManager_CreateSpriteAtIndex)
static int SpriteBattler(PokemonSprite *sprite)
{
    BattleSystem *battleSys = BattleStageSprites_BattleSystem();
    PokemonSpriteManager *monSpriteMan;

    if (battleSys == NULL || sprite == NULL) {
        return -1;
    }

    monSpriteMan = BattleSystem_GetPokemonSpriteManager(battleSys);

    if (sprite < &monSpriteMan->sprites[0] || sprite >= &monSpriteMan->sprites[MAX_MON_SPRITES]) {
        return -1;
    }

    return sprite - &monSpriteMan->sprites[0];
}

void BattleStage_InitEntryAnim(PokemonSprite *sprite, int dummy)
{
    if (BattleStage_UsesGen5Motion(SpriteBattler(sprite))) {
        // No frame swaps, so no x offset either: the stream is the animation
        PokemonSprite_SetAttribute(sprite, MON_SPRITE_X_OFFSET, 0);
        return;
    }

    PokemonSprite_InitAnim(sprite, dummy);
}

void BattleStage_LoadEntryAnim(NARC *narc, PokemonAnimManager *monAnimMan, PokemonSprite *sprite, u16 species, int face, int flipSprite, int frame)
{
    PokemonSprite_LoadAnim(narc, monAnimMan, sprite, species, face, flipSprite, frame);

    if (BattleStage_UsesGen5Motion(SpriteBattler(sprite))) {
        // The script's task hasn't run a command yet: deleting it leaves the sprite as it is
        // and marks the slot complete
        PokemonAnimManager_DeleteAnim(monAnimMan, frame);
        sGen5MotionStats.entryAnimsSkipped++;
    } else {
        sGen5MotionStats.entryAnimsPlayed++;
    }
}

BOOL BattleStage_SuppressMenuBob(int battler)
{
    if (!BATTLE_STAGE_3D || (BattleStageSprites_DebugFlags() & BATTLE_STAGE_DEBUG_CLASSIC_SPRITES)) {
        return FALSE;
    }

    if (BattleStageSprites_DrawsBattler(battler)) {
        sGen5MotionStats.bobSuppressedFrames++;
        return TRUE;
    }

    return FALSE;
}

u16 BattleStage_HitFlashColor(BattleSystem *battleSys)
{
    BattleContext *battleCtx = BattleSystem_Context(battleSys);
    u16 color = HIT_FLASH_SPECIAL;

    if (battleCtx != NULL && battleCtx->moveCur < MAX_MOVES && battleCtx->aiContext.moveTable[battleCtx->moveCur].class == CLASS_PHYSICAL) {
        color = HIT_FLASH_PHYSICAL;
    }

    sGen5MotionStats.hitFlashes++;
    sGen5MotionStats.hitFlashColor = color;
    return color;
}

void BattleStage_StreamSpecialIdleReset(int battler)
{
    if (battler >= 0 && battler < MAX_MON_SPRITES) {
        sGen5MotionStats.idleCount[battler] = IDLE_COUNT_START;
        sGen5MotionStats.idleActiveMask &= ~(1 << battler);
    }
}

BOOL BattleStage_StreamSpecialIdleStart(int battler, const u8 *idleSteps, u32 *waitVBlanks)
{
    u32 count;

    *waitVBlanks = 0;

    if (battler < 0 || battler >= MAX_MON_SPRITES) {
        return FALSE;
    }

    // As B/W: never while an effect script runs; FREEZE_IDLE keeps the critic's frames still
    if (BattleStageSprites_MoveAnimActive() || (BattleStageSprites_DebugFlags() & BATTLE_STAGE_DEBUG_FREEZE_IDLE)) {
        return FALSE;
    }

    count = sGen5MotionStats.idleCount[battler];

    if (count == 0 || count > IDLE_COUNT_START) {
        count = IDLE_COUNT_START;
    }

    sGen5MotionStats.idleRolls++;
    sGen5MotionStats.idleCount[battler] = count - 1;

    if (IdleRandom() % count != 0) {
        return FALSE;
    }

    sGen5MotionStats.idleCount[battler] = IDLE_COUNT_START;
    *waitVBlanks = sIdleWaits[IdleRandom() % NELEMS(sIdleWaits)];
    sGen5MotionStats.idleStarts[battler]++;
    sGen5MotionStats.idleActiveMask |= 1 << battler;
    sGen5MotionStats.lastIdleWait = *waitVBlanks;

    if (idleSteps == NULL) {
        sGen5MotionStats.idleApproxStarts++;
    }

    return TRUE;
}

BOOL BattleStage_StreamSpecialIdleAbort(int battler)
{
    return BattleStageSprites_MoveAnimActive();
}

void BattleStage_StreamSpecialIdleEnd(int battler, BOOL aborted)
{
    if (battler >= 0 && battler < MAX_MON_SPRITES) {
        sGen5MotionStats.idleActiveMask &= ~(1 << battler);
    }

    if (aborted) {
        sGen5MotionStats.idleAborts++;
    }
}
